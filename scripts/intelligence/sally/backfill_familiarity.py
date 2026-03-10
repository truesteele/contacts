#!/usr/bin/env python3
"""
Sally Pipeline — Familiarity Rating Backfill

Uses comms density + SMS presence as proxy for familiarity_rating (0-4 scale).
Sally can override manually later.

Logic:
  0 = No comms data at all (stranger/unknown)
  1 = Has some email or calendar data but no SMS (recognize name)
  2 = Has SMS conversation (personal enough to text)
  3 = High SMS count (>50 messages) or multiple comms channels active
  4 = Very high SMS (>200) + calendar meetings (close/trusted)

Usage:
  python scripts/intelligence/sally/backfill_familiarity.py --test       # Preview 10 contacts
  python scripts/intelligence/sally/backfill_familiarity.py --dry-run    # Show all without saving
  python scripts/intelligence/sally/backfill_familiarity.py              # Full run
  python scripts/intelligence/sally/backfill_familiarity.py --force      # Re-score already rated
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def compute_familiarity(contact: dict, sms_data: dict) -> int:
    """Compute familiarity rating based on comms signals.

    Args:
        contact: Row from sally_contacts
        sms_data: Dict of contact_id -> SMS conversation data
    Returns:
        Familiarity rating 0-4
    """
    contact_id = contact["id"]
    comms_thread_count = contact.get("comms_thread_count") or 0
    comms_meeting_count = contact.get("comms_meeting_count") or 0
    has_comms = comms_thread_count > 0 or comms_meeting_count > 0

    # Check SMS data
    sms = sms_data.get(contact_id)
    has_sms = sms is not None
    sms_count = sms["message_count"] if sms else 0

    # Rating logic
    if has_sms and sms_count > 200 and comms_meeting_count > 0:
        return 4  # Very high SMS + meetings = close/trusted
    elif has_sms and (sms_count > 50 or (has_comms and comms_meeting_count > 0)):
        return 3  # High SMS or multi-channel active
    elif has_sms:
        return 2  # Has SMS = personal enough to text
    elif has_comms:
        return 1  # Some comms but no SMS = recognize name
    else:
        return 0  # No comms data = unknown


def main():
    parser = argparse.ArgumentParser(
        description="Backfill Sally contact familiarity ratings from comms signals"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Preview 10 contacts without saving")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show all ratings without saving")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-rate contacts that already have a familiarity_rating")
    parser.add_argument("--contact-id", type=int, default=None,
                        help="Process a single contact by ID")
    args = parser.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        sys.exit(1)

    supabase: Client = create_client(url, key)
    print("Connected to Supabase")

    # Fetch all SMS conversations for lookup
    print("Fetching SMS conversations...")
    sms_data = {}
    sms_offset = 0
    sms_page_size = 1000
    while True:
        page = (
            supabase.table("sally_contact_sms_conversations")
            .select("contact_id, message_count, sent_count, received_count")
            .range(sms_offset, sms_offset + sms_page_size - 1)
            .execute()
        ).data
        if not page:
            break
        for row in page:
            cid = row["contact_id"]
            if cid not in sms_data or row["message_count"] > sms_data[cid]["message_count"]:
                sms_data[cid] = row
        if len(page) < sms_page_size:
            break
        sms_offset += sms_page_size
    print(f"  {len(sms_data)} contacts with SMS data")

    # Fetch contacts
    print("Fetching contacts...")
    contacts = []
    offset = 0
    page_size = 1000
    while True:
        query = (
            supabase.table("sally_contacts")
            .select("id, first_name, last_name, familiarity_rating, "
                    "comms_thread_count, comms_meeting_count")
            .order("id")
            .range(offset, offset + page_size - 1)
        )
        if args.contact_id:
            query = (
                supabase.table("sally_contacts")
                .select("id, first_name, last_name, familiarity_rating, "
                        "comms_thread_count, comms_meeting_count")
                .eq("id", args.contact_id)
            )
        page = query.execute().data
        if not page:
            break
        contacts.extend(page)
        if args.contact_id or len(page) < page_size:
            break
        offset += page_size

    # Filter to contacts needing rating
    if not args.force and not args.contact_id:
        contacts = [c for c in contacts if not c.get("familiarity_rating")]

    total = len(contacts)
    if args.test:
        contacts = contacts[:10]

    print(f"Processing {len(contacts)} contacts (of {total} eligible)")

    # Compute and save
    distribution = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    updated = 0

    for c in contacts:
        rating = compute_familiarity(c, sms_data)
        distribution[rating] += 1
        name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
        old_rating = c.get("familiarity_rating") or 0

        if args.dry_run or args.test:
            sms = sms_data.get(c["id"])
            sms_info = f"SMS: {sms['message_count']} msgs" if sms else "No SMS"
            comms_info = f"threads={c.get('comms_thread_count', 0)}, meetings={c.get('comms_meeting_count', 0)}"
            change = f" (was {old_rating})" if old_rating != rating and old_rating else ""
            print(f"  [{c['id']}] {name}: {rating}/4{change} — {sms_info}, {comms_info}")
        else:
            try:
                supabase.table("sally_contacts").update({
                    "familiarity_rating": rating
                }).eq("id", c["id"]).execute()
                updated += 1
            except Exception as e:
                print(f"  ERROR saving [{c['id']}] {name}: {e}")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"FAMILIARITY BACKFILL SUMMARY")
    print(f"{'=' * 50}")
    print(f"  Contacts processed: {len(contacts)}")
    if not args.dry_run and not args.test:
        print(f"  Contacts updated:   {updated}")
    print(f"\n  DISTRIBUTION:")
    labels = {0: "unknown", 1: "recognize", 2: "know them", 3: "good relationship", 4: "close/trusted"}
    for rating in range(5):
        print(f"    {rating} ({labels[rating]}): {distribution[rating]}")
    if args.dry_run:
        print(f"\n  DRY RUN — no changes saved")
    if args.test:
        print(f"\n  TEST MODE — showing first 10 only")


if __name__ == "__main__":
    main()
