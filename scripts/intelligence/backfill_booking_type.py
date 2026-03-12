#!/usr/bin/env python3
"""
Backfill booking_type and trip_group_id for camping_reservations.

Pulls all reservations, clusters overlapping/adjacent ones, uses GPT-5 mini
to classify each cluster, and updates the DB.

booking_type values:
  - individual: single site, standalone booking
  - group_booking: one of multiple sites booked for the same trip (same dates/area)
  - group_site: a designated group campsite (e.g. "Group Camp", "Group Primitive")
  - multi_stop_trip: one leg of a road trip with sequential stops

trip_group_id: links related reservations (e.g. 'trip-2022-07-emerald-bay')
"""

import os
import sys
import json
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from supabase import create_client

load_dotenv()


class ReservationClassification(BaseModel):
    """Classification for a single reservation."""
    id: int = Field(description="The reservation database ID")
    booking_type: str = Field(description="individual, group_booking, group_site, or multi_stop_trip")
    trip_group_id: str = Field(description="Short slug linking related reservations, format: trip-YYYY-MM-location")


class BookingClassification(BaseModel):
    """GPT-5 mini output for classifying a cluster of reservations."""
    classifications: list[ReservationClassification] = Field(
        description="Classification for each reservation in the cluster"
    )
    reasoning: str = Field(description="Brief explanation of the classification")


def main():
    sb_url = os.environ["SUPABASE_URL"]
    sb_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    supabase = create_client(sb_url, sb_key)
    openai = OpenAI(api_key=os.environ["OPENAI_APIKEY"])

    # Pull all reservations
    print("Fetching reservations...")
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = supabase.table("camping_reservations") \
            .select("id, reservation_number, campground_name, site_number, check_in_date, check_out_date, num_nights, status, provider, primary_occupant, total_cost") \
            .not_.is_("check_in_date", "null") \
            .not_.is_("check_out_date", "null") \
            .order("check_in_date") \
            .range(offset, offset + page_size - 1) \
            .execute()
        all_rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size

    print(f"  {len(all_rows)} reservations with dates")

    # ── Step 1: Tag obvious group_site from campground name ──────────
    group_site_ids = set()
    for r in all_rows:
        name = (r["campground_name"] or "").lower()
        if "group camp" in name or "group primitive" in name or "group site" in name:
            group_site_ids.add(r["id"])
    print(f"  {len(group_site_ids)} group sites by name")

    # ── Step 2: Cluster overlapping/adjacent reservations ────────────
    # Two reservations overlap if their date ranges intersect or are adjacent (within 1 day)
    def dates_overlap_or_adjacent(a, b):
        a_in = date.fromisoformat(a["check_in_date"])
        a_out = date.fromisoformat(a["check_out_date"])
        b_in = date.fromisoformat(b["check_in_date"])
        b_out = date.fromisoformat(b["check_out_date"])
        # Overlap: a_in <= b_out AND b_in <= a_out
        # Adjacent: a_out == b_in or b_out == a_in (sequential legs)
        return a_in <= b_out + timedelta(days=1) and b_in <= a_out + timedelta(days=1)

    # Build clusters using union-find
    parent = {r["id"]: r["id"] for r in all_rows}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Compare all pairs — O(n^2) but n=357 so it's fine
    for i in range(len(all_rows)):
        for j in range(i + 1, len(all_rows)):
            a, b = all_rows[i], all_rows[j]
            # Only cluster if same status category (both completed, or both cancelled)
            # Cancelled alternatives for the same trip period should cluster together
            if dates_overlap_or_adjacent(a, b):
                union(a["id"], b["id"])

    # Group by cluster root
    clusters = {}
    for r in all_rows:
        root = find(r["id"])
        clusters.setdefault(root, []).append(r)

    singles = sum(1 for c in clusters.values() if len(c) == 1)
    multi = sum(1 for c in clusters.values() if len(c) > 1)
    print(f"  {singles} standalone, {multi} multi-reservation clusters")

    # ── Step 3: Classify clusters with GPT-5 mini ────────────────────
    updates = []  # (id, booking_type, trip_group_id)
    stats = {"input_tokens": 0, "output_tokens": 0}

    # Singles are easy — individual or group_site
    for root, members in clusters.items():
        if len(members) == 1:
            r = members[0]
            if r["id"] in group_site_ids:
                updates.append((r["id"], "group_site", None))
            else:
                updates.append((r["id"], "individual", None))

    # Multi-member clusters need GPT-5 mini
    multi_clusters = [(root, members) for root, members in clusters.items() if len(members) > 1]
    print(f"\n  Classifying {len(multi_clusters)} clusters with GPT-5 mini...")

    def classify_cluster(cluster_data):
        root, members = cluster_data
        # Sort by check_in
        members.sort(key=lambda r: r["check_in_date"])

        summary = []
        for r in members:
            summary.append({
                "id": r["id"],
                "campground": r["campground_name"],
                "site": r["site_number"],
                "check_in": r["check_in_date"],
                "check_out": r["check_out_date"],
                "nights": r["num_nights"],
                "status": r["status"],
                "res_number": r["reservation_number"],
                "cost": float(r["total_cost"]) if r["total_cost"] else None,
                "occupant": r["primary_occupant"],
            })

        prompt = f"""Classify these {len(members)} camping reservations that overlap or are adjacent in time:

{json.dumps(summary, indent=2)}

For EACH reservation, assign:
1. booking_type: one of:
   - "individual": standalone single-site booking, not part of a group
   - "group_booking": one of multiple sites booked for the same group trip (same/similar dates, same area, often sequential reservation numbers)
   - "group_site": a designated group campsite (name contains "Group Camp" etc.)
   - "multi_stop_trip": one leg of a road trip — different campgrounds on sequential dates

2. trip_group_id: a short slug linking related reservations. Format: "trip-YYYY-MM-location"
   - group_booking members share the same trip_group_id
   - multi_stop_trip legs share the same trip_group_id
   - individual reservations that just happen to overlap with cancelled alternatives: give each a DIFFERENT trip_group_id
   - cancelled alternatives for a trip that was eventually booked: give same trip_group_id as the completed booking

Key patterns:
- Sequential reservation numbers (e.g. 2-19456679, 2-19456680) at the same campground = group_booking
- Same campground, same dates, different sites = group_booking
- Different campgrounds on back-to-back dates = multi_stop_trip
- One completed + several cancelled at different campgrounds on same dates = the cancelled ones are alternatives that were explored, NOT group bookings. Mark each as individual with different trip_group_ids unless you're confident they're alternatives for the same trip.
- Cancelled reservations at different campgrounds on the same dates are often "shopping around" — mark as individual unless they share a clear trip plan.

Return classifications for ALL {len(members)} reservations."""

        try:
            resp = openai.responses.parse(
                model="gpt-5-mini",
                instructions="You classify camping reservations into booking types. Return a classification for every reservation ID provided.",
                input=prompt,
                text_format=BookingClassification,
            )
            if resp.usage:
                stats["input_tokens"] += resp.usage.input_tokens
                stats["output_tokens"] += resp.usage.output_tokens
            if resp.output_parsed:
                return resp.output_parsed
        except Exception as e:
            print(f"    Error classifying cluster: {e}")
        return None

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(classify_cluster, (root, members)): (root, members)
                   for root, members in multi_clusters}
        done = 0
        for future in as_completed(futures):
            done += 1
            result = future.result()
            if result:
                for c in result.classifications:
                    updates.append((c.id, c.booking_type, c.trip_group_id))
                if done % 10 == 0:
                    print(f"    Classified {done}/{len(multi_clusters)} clusters")

    print(f"    Done: {len(updates)} total classifications")

    # ── Step 4: Update DB ────────────────────────────────────────────
    print(f"\n  Updating {len(updates)} reservations...")
    saved = 0
    errors = 0
    for rid, btype, tgid in updates:
        try:
            row = {"booking_type": btype}
            if tgid:
                row["trip_group_id"] = tgid
            supabase.table("camping_reservations").update(row).eq("id", rid).execute()
            saved += 1
        except Exception as e:
            errors += 1
            print(f"    Error updating {rid}: {e}")

    # Stats
    print(f"\n  Saved: {saved}, Errors: {errors}")
    cost = (stats["input_tokens"] * 0.15 + stats["output_tokens"] * 0.60) / 1_000_000
    print(f"  Tokens: {stats['input_tokens']:,} in / {stats['output_tokens']:,} out (${cost:.3f})")

    # Summary
    print("\n  Verifying...")
    for btype in ["individual", "group_booking", "group_site", "multi_stop_trip"]:
        resp = supabase.table("camping_reservations") \
            .select("id", count="exact") \
            .eq("booking_type", btype) \
            .execute()
        print(f"    {btype}: {resp.count}")


if __name__ == "__main__":
    main()
