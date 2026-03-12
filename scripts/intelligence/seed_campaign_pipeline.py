#!/usr/bin/env python3
"""
Seed the OC Come Alive 2026 pipeline with deals from campaign_2026 contacts.

Usage:
    python seed_campaign_pipeline.py --dry-run    # Preview without inserting
    python seed_campaign_pipeline.py              # Create deals
    python seed_campaign_pipeline.py --clear      # Delete existing deals first, then re-seed
"""

import argparse
import json
import os
import sys
from collections import defaultdict

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

PIPELINE_ID = "636a0a58-3a89-48ce-8e86-94400d8ea028"
PIPELINE_SLUG = "oc-come-alive-2026"

# Stage keys (lowercase, underscored — matches how the UI converts stage names)
STAGE_NOT_CONTACTED = "not_contacted"
STAGE_OUTREACH_SENT = "outreach_sent"
STAGE_RESPONDED = "responded"
STAGE_IN_CONVERSATION = "in_conversation"
STAGE_COMMITTED = "committed"
STAGE_DONATED = "donated"
STAGE_LOST = "lost"

# Next action defaults by stage and list
NEXT_ACTIONS = {
    "A": {
        STAGE_NOT_CONTACTED: "Send personal outreach",
        STAGE_OUTREACH_SENT: "Follow up in 3-5 days",
        STAGE_RESPONDED: "Continue conversation",
    },
    "B": {
        STAGE_NOT_CONTACTED: "Send Email 1",
        STAGE_OUTREACH_SENT: "Text follow-up if opened",
        STAGE_RESPONDED: "Reply personally",
    },
    "C": {
        STAGE_NOT_CONTACTED: "Send Email 1",
        STAGE_OUTREACH_SENT: "Text follow-up if opened",
        STAGE_RESPONDED: "Reply personally",
    },
    "D": {
        STAGE_NOT_CONTACTED: "Send Email 1",
        STAGE_OUTREACH_SENT: "Text follow-up if opened",
        STAGE_RESPONDED: "Reply personally",
    },
}


def determine_stage(campaign_data: dict) -> str:
    """Determine the initial kanban stage from campaign_2026 data."""
    # Check donation first
    donation = campaign_data.get("donation")
    if donation and isinstance(donation, dict) and donation.get("amount"):
        return STAGE_DONATED

    # Check responded
    if campaign_data.get("responded_at"):
        return STAGE_RESPONDED

    # Check send status
    send_status = campaign_data.get("send_status")
    if send_status and isinstance(send_status, dict) and len(send_status) > 0:
        return STAGE_OUTREACH_SENT

    return STAGE_NOT_CONTACTED


def build_notes(campaign_data: dict) -> str | None:
    """Build notes from scaffold data."""
    scaffold = campaign_data.get("scaffold", {})
    if not scaffold:
        return None

    parts = []
    persona = scaffold.get("donor_persona")
    if persona:
        parts.append(f"Persona: {persona}")

    motivation = scaffold.get("motivation_flag")
    if motivation:
        parts.append(f"Motivation: {motivation}")

    angle = scaffold.get("personalization_angle")
    if angle:
        parts.append(f"Angle: {angle}")

    return " | ".join(parts) if parts else None


def main():
    parser = argparse.ArgumentParser(description="Seed OC Come Alive 2026 pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Preview without inserting")
    parser.add_argument("--clear", action="store_true", help="Delete existing deals before seeding")
    args = parser.parse_args()

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Optionally clear existing deals
    if args.clear and not args.dry_run:
        print(f"Clearing existing deals for pipeline {PIPELINE_SLUG}...")
        sb.table("deals").delete().eq("pipeline_id", PIPELINE_ID).execute()
        print("Cleared.")

    # Fetch all contacts with campaign_2026 data
    print("Fetching campaign contacts...")
    all_contacts = []
    page_size = 1000
    offset = 0

    while True:
        resp = (
            sb.table("contacts")
            .select("id, first_name, last_name, company, campaign_2026")
            .not_.is_("campaign_2026", "null")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        if not resp.data:
            break
        all_contacts.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size

    print(f"Found {len(all_contacts)} contacts with campaign_2026 data")

    # Check for existing deals to avoid duplicates
    existing_contact_ids = set()
    if not args.clear:
        offset = 0
        while True:
            resp = (
                sb.table("deals")
                .select("contact_id")
                .eq("pipeline_id", PIPELINE_ID)
                .not_.is_("contact_id", "null")
                .range(offset, offset + page_size - 1)
                .execute()
            )
            if not resp.data:
                break
            existing_contact_ids.update(d["contact_id"] for d in resp.data)
            if len(resp.data) < page_size:
                break
            offset += page_size

        if existing_contact_ids:
            print(f"Skipping {len(existing_contact_ids)} contacts already in pipeline")

    # Build deals
    deals_by_stage = defaultdict(list)
    skipped_sidelined = 0

    for contact in all_contacts:
        if contact["id"] in existing_contact_ids:
            continue

        c2026 = contact.get("campaign_2026") or {}
        scaffold = c2026.get("scaffold", {})
        campaign_list = scaffold.get("campaign_list", "")

        # Skip sidelined contacts
        if campaign_list == "sidelined":
            skipped_sidelined += 1
            continue

        stage = determine_stage(c2026)
        name = f"{contact['first_name'] or ''} {contact['last_name'] or ''}".strip()
        ask_amount = scaffold.get("primary_ask_amount")
        notes = build_notes(c2026)

        # Determine next action
        list_actions = NEXT_ACTIONS.get(campaign_list, NEXT_ACTIONS["B"])
        next_action = list_actions.get(stage)

        deal = {
            "pipeline_id": PIPELINE_ID,
            "contact_id": contact["id"],
            "title": name or f"Contact #{contact['id']}",
            "stage": stage,
            "amount": int(ask_amount) if ask_amount else None,
            "source": f"List {campaign_list}" if campaign_list else None,
            "notes": notes,
            "next_action": next_action,
        }

        deals_by_stage[stage].append((ask_amount or 0, deal))

    # Assign positions within each stage (highest ask amount first)
    all_deals = []
    for stage, deals in deals_by_stage.items():
        deals.sort(key=lambda x: x[0], reverse=True)
        for position, (_, deal) in enumerate(deals):
            deal["position"] = position
            all_deals.append(deal)

    # Summary
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Pipeline: OC Come Alive 2026")
    print(f"Total deals to create: {len(all_deals)}")
    print(f"Sidelined (skipped): {skipped_sidelined}")
    print()

    for stage_name in [
        STAGE_NOT_CONTACTED,
        STAGE_OUTREACH_SENT,
        STAGE_RESPONDED,
        STAGE_IN_CONVERSATION,
        STAGE_COMMITTED,
        STAGE_DONATED,
        STAGE_LOST,
    ]:
        count = sum(1 for d in all_deals if d["stage"] == stage_name)
        total_value = sum(d["amount"] or 0 for d in all_deals if d["stage"] == stage_name)
        if count > 0:
            print(f"  {stage_name:20s}  {count:4d} deals  ${total_value:>10,}")

    if args.dry_run:
        # Show sample deals
        print("\nSample deals (first 5):")
        for deal in all_deals[:5]:
            print(f"  {deal['title']:30s}  stage={deal['stage']:20s}  amount=${deal['amount'] or 0:>8,}  source={deal['source']}")
        print(f"\nRun without --dry-run to create {len(all_deals)} deals.")
        return

    # Insert deals in batches
    BATCH_SIZE = 100
    created = 0

    for i in range(0, len(all_deals), BATCH_SIZE):
        batch = all_deals[i : i + BATCH_SIZE]
        resp = sb.table("deals").insert(batch).execute()
        created += len(resp.data)
        print(f"  Inserted batch {i // BATCH_SIZE + 1}: {len(resp.data)} deals")

    print(f"\nDone. Created {created} deals in pipeline '{PIPELINE_SLUG}'.")
    print(f"View at: /tools/pipeline?pipeline={PIPELINE_SLUG}")


if __name__ == "__main__":
    main()
