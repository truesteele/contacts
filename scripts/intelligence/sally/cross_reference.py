#!/usr/bin/env python3
"""
Cross-reference Sally's contacts against Justin's to find shared connections.

Matches by normalized LinkedIn URL and populates sally_contacts.justin_contact_id
for shared connections. Prints summary stats and top shared contacts.

Usage:
    python scripts/intelligence/sally/cross_reference.py
    python scripts/intelligence/sally/cross_reference.py --dry-run
    python scripts/intelligence/sally/cross_reference.py --clear   # reset all justin_contact_id values
"""

import argparse
import os
from urllib.parse import unquote

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def normalize_linkedin_url(url: str) -> str | None:
    """Normalize LinkedIn URL: lowercase, strip trailing slash, ensure www prefix."""
    if not url or not url.strip():
        return None
    url = unquote(url.strip()).lower().rstrip("/")
    url = url.replace("://linkedin.com/", "://www.linkedin.com/")
    if not url.startswith("http"):
        url = "https://www.linkedin.com/" + url.lstrip("/")
    return url


def main():
    parser = argparse.ArgumentParser(description="Cross-reference Sally's contacts with Justin's by LinkedIn URL")
    parser.add_argument("--dry-run", action="store_true", help="Show matches without updating DB")
    parser.add_argument("--clear", action="store_true", help="Clear all justin_contact_id values first")
    args = parser.parse_args()

    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"],
    )

    # Optionally clear existing cross-references
    if args.clear:
        print("Clearing all justin_contact_id values...")
        sb.table("sally_contacts").update({"justin_contact_id": None}).neq("justin_contact_id", 0).execute()
        print("Done.\n")

    # Fetch all Sally contacts with LinkedIn URLs
    print("Fetching Sally's contacts...")
    sally_contacts = []
    page_size = 1000
    offset = 0
    while True:
        resp = sb.table("sally_contacts").select("id, first_name, last_name, linkedin_url").not_.is_("linkedin_url", "null").range(offset, offset + page_size - 1).execute()
        sally_contacts.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    print(f"  {len(sally_contacts)} Sally contacts with LinkedIn URLs")

    # Fetch all Justin contacts with LinkedIn URLs
    print("Fetching Justin's contacts...")
    justin_contacts = []
    offset = 0
    while True:
        resp = sb.table("contacts").select("id, first_name, last_name, linkedin_url, ask_readiness, ai_proximity_score, ai_capacity_score, comms_closeness").not_.is_("linkedin_url", "null").range(offset, offset + page_size - 1).execute()
        justin_contacts.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    print(f"  {len(justin_contacts)} Justin contacts with LinkedIn URLs")

    # Build Justin lookup by normalized LinkedIn URL
    justin_by_url: dict[str, dict] = {}
    for jc in justin_contacts:
        norm = normalize_linkedin_url(jc["linkedin_url"])
        if norm:
            justin_by_url[norm] = jc

    # Match Sally → Justin
    matches = []
    for sc in sally_contacts:
        norm = normalize_linkedin_url(sc["linkedin_url"])
        if norm and norm in justin_by_url:
            jc = justin_by_url[norm]
            matches.append({
                "sally_id": sc["id"],
                "sally_name": f"{sc['first_name'] or ''} {sc['last_name'] or ''}".strip(),
                "justin_id": jc["id"],
                "justin_name": f"{jc['first_name'] or ''} {jc['last_name'] or ''}".strip(),
                "ask_readiness": jc.get("ask_readiness"),
                "ai_proximity_score": jc.get("ai_proximity_score"),
                "ai_capacity_score": jc.get("ai_capacity_score"),
                "comms_closeness": jc.get("comms_closeness"),
            })

    print(f"\n{'='*60}")
    print(f"CROSS-REFERENCE RESULTS")
    print(f"{'='*60}")
    print(f"Sally contacts with LinkedIn:  {len(sally_contacts)}")
    print(f"Justin contacts with LinkedIn: {len(justin_contacts)}")
    print(f"Shared connections:            {len(matches)}")
    print(f"Sally-only contacts:           {len(sally_contacts) - len(matches)}")
    print(f"Overlap rate:                  {len(matches)/len(sally_contacts)*100:.1f}%")

    if not matches:
        print("\nNo shared connections found.")
        return

    # Update sally_contacts.justin_contact_id
    if not args.dry_run:
        print(f"\nUpdating sally_contacts.justin_contact_id for {len(matches)} matches...")
        updated = 0
        for m in matches:
            try:
                sb.table("sally_contacts").update(
                    {"justin_contact_id": m["justin_id"]}
                ).eq("id", m["sally_id"]).execute()
                updated += 1
            except Exception as e:
                print(f"  Error updating sally_id={m['sally_id']}: {e}")
        print(f"  Updated {updated}/{len(matches)} contacts")
    else:
        print("\n[DRY RUN] Would update sally_contacts.justin_contact_id for these matches.")

    # Sort by Justin's ask_readiness score (descending)
    def get_ar_score(m):
        ar = m.get("ask_readiness")
        if ar and isinstance(ar, dict):
            goal = ar.get("outdoorithm_fundraising", {})
            if isinstance(goal, dict):
                try:
                    return int(goal.get("score", 0))
                except (ValueError, TypeError):
                    return 0
        return 0

    matches.sort(key=get_ar_score, reverse=True)

    # Print top 20
    print(f"\n{'='*60}")
    print(f"TOP 20 SHARED CONNECTIONS (by Justin's ask-readiness score)")
    print(f"{'='*60}")
    print(f"{'#':<4} {'Name':<30} {'AR Score':<10} {'AR Tier':<18} {'Proximity':<10} {'Closeness':<12}")
    print(f"{'-'*4} {'-'*30} {'-'*10} {'-'*18} {'-'*10} {'-'*12}")

    for i, m in enumerate(matches[:20], 1):
        ar = m.get("ask_readiness") or {}
        goal = ar.get("outdoorithm_fundraising", {}) if isinstance(ar, dict) else {}
        if not isinstance(goal, dict):
            goal = {}
        score = goal.get("score", "—")
        tier = goal.get("tier", "—")
        prox = m.get("ai_proximity_score") or "—"
        close = m.get("comms_closeness") or "—"
        print(f"{i:<4} {m['justin_name']:<30} {str(score):<10} {str(tier):<18} {str(prox):<10} {str(close):<12}")

    # Tier breakdown of shared connections
    tier_counts: dict[str, int] = {}
    for m in matches:
        ar = m.get("ask_readiness") or {}
        goal = ar.get("outdoorithm_fundraising", {}) if isinstance(ar, dict) else {}
        tier = goal.get("tier", "unscored") if isinstance(goal, dict) else "unscored"
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    print(f"\nASK-READINESS TIER BREAKDOWN (shared contacts only):")
    for tier in ["ready_now", "cultivate_first", "long_term", "not_a_fit", "unscored"]:
        if tier in tier_counts:
            print(f"  {tier:<20} {tier_counts[tier]:>4}")

    # Closeness breakdown
    close_counts: dict[str, int] = {}
    for m in matches:
        close = m.get("comms_closeness") or "none"
        close_counts[close] = close_counts.get(close, 0) + 1

    print(f"\nCOMMS CLOSENESS BREAKDOWN (shared contacts, Justin's data):")
    for level in ["inner_circle", "close", "warm", "familiar", "distant", "no_contact", "none"]:
        if level in close_counts:
            print(f"  {level:<20} {close_counts[level]:>4}")


if __name__ == "__main__":
    main()
