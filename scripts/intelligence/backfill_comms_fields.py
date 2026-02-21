#!/usr/bin/env python3
"""
Network Intelligence — Backfill Comms Summary Fields

Denormalizes communication_history JSONB into comms_last_date and comms_thread_count
columns for fast filtering and sorting.

Usage:
  python scripts/intelligence/backfill_comms_fields.py --test      # Preview 5 contacts
  python scripts/intelligence/backfill_comms_fields.py              # Full run
"""

import os
import sys
import argparse
import time

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def connect() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        sys.exit(1)
    return create_client(url, key)


def fetch_contacts_with_comms(supabase: Client) -> list[dict]:
    """Fetch all contacts that have communication_history JSONB."""
    all_contacts = []
    page_size = 1000
    offset = 0

    while True:
        page = (
            supabase.table("contacts")
            .select("id, first_name, last_name, communication_history")
            .not_.is_("communication_history", "null")
            .range(offset, offset + page_size - 1)
            .execute()
        ).data

        if not page:
            break
        all_contacts.extend(page)
        if len(page) < page_size:
            break
        offset += page_size

    return all_contacts


def backfill(supabase: Client, contacts: list[dict], test_mode: bool = False) -> dict:
    """Extract last_contact and total_threads from communication_history JSONB."""
    stats = {"updated": 0, "skipped": 0, "errors": 0}

    for i, contact in enumerate(contacts):
        cid = contact["id"]
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        ch = contact.get("communication_history") or {}

        last_contact = ch.get("last_contact")  # "YYYY-MM-DD" string
        total_threads = ch.get("total_threads")

        if not last_contact and not total_threads:
            stats["skipped"] += 1
            continue

        # Parse total_threads as int (stored as string or int in JSONB)
        try:
            thread_count = int(total_threads) if total_threads is not None else 0
        except (ValueError, TypeError):
            thread_count = 0

        if test_mode:
            print(f"  [{cid}] {name}: last_contact={last_contact}, threads={thread_count}")
            stats["updated"] += 1
            continue

        try:
            supabase.table("contacts").update({
                "comms_last_date": last_contact,
                "comms_thread_count": thread_count,
            }).eq("id", cid).execute()
            stats["updated"] += 1
        except Exception as e:
            print(f"  ERROR [{cid}] {name}: {e}")
            stats["errors"] += 1

        if (i + 1) % 100 == 0:
            print(f"  Progress: {i + 1}/{len(contacts)} ({stats['updated']} updated)")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Backfill comms_last_date and comms_thread_count from communication_history"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Preview mode — show what would be updated without writing")
    args = parser.parse_args()

    print("Backfill Comms Summary Fields")
    print("=" * 50)

    supabase = connect()
    print("Connected to Supabase")

    contacts = fetch_contacts_with_comms(supabase)
    print(f"Found {len(contacts)} contacts with communication_history")

    if not contacts:
        print("Nothing to backfill.")
        return

    if args.test:
        print(f"\n--- TEST MODE: previewing first 5 contacts ---\n")
        contacts = contacts[:5]

    start = time.time()
    stats = backfill(supabase, contacts, test_mode=args.test)
    elapsed = time.time() - start

    print(f"\n{'=' * 50}")
    print(f"BACKFILL COMPLETE")
    print(f"{'=' * 50}")
    print(f"  Updated:  {stats['updated']}")
    print(f"  Skipped:  {stats['skipped']}")
    print(f"  Errors:   {stats['errors']}")
    print(f"  Time:     {elapsed:.1f}s")
    print(f"{'=' * 50}")

    if stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
