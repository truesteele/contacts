#!/usr/bin/env python3
"""
Import LinkedIn messages CSV into contact_email_threads table.

Reads the LinkedIn messages export, groups by conversation ID,
matches participants to contacts by LinkedIn URL, and stores
as threads in contact_email_threads with account_email='linkedin'.

Usage:
  python scripts/import_linkedin_messages.py --test          # Preview 5 conversations
  python scripts/import_linkedin_messages.py                 # Full import
  python scripts/import_linkedin_messages.py --clear-first   # Clear existing linkedin rows first
"""

import os
import csv
import json
import argparse
from datetime import datetime, timezone
from collections import defaultdict

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

JUSTIN_PROFILE = "https://www.linkedin.com/in/justinrichardsteele"
CSV_PATH = "docs/LinkedIn/messages.csv"


def normalize_linkedin_url(url: str) -> str:
    """Normalize LinkedIn URL for matching."""
    if not url:
        return ""
    url = url.strip().rstrip("/").lower()
    # Remove trailing query params
    if "?" in url:
        url = url.split("?")[0]
    return url


def load_contact_url_map(supabase) -> dict:
    """Load contact_id -> linkedin_url mapping from contacts table."""
    url_to_id = {}
    page_size = 1000
    offset = 0

    while True:
        resp = (
            supabase.table("contacts")
            .select("id, linkedin_url")
            .not_.is_("linkedin_url", "null")
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        if not resp.data:
            break
        for row in resp.data:
            normalized = normalize_linkedin_url(row["linkedin_url"])
            if normalized:
                url_to_id[normalized] = row["id"]
        if len(resp.data) < page_size:
            break
        offset += page_size

    return url_to_id


def parse_csv(csv_path: str) -> dict:
    """Parse LinkedIn messages CSV, group by conversation ID."""
    conversations = defaultdict(list)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            conv_id = row.get("CONVERSATION ID", "").strip()
            if not conv_id:
                continue

            content = row.get("CONTENT", "").strip()
            # Skip sponsored/empty messages
            if not content:
                continue
            if row.get("CONVERSATION TITLE", "").strip() == "Sponsored Conversation":
                continue
            # Skip HTML spam
            if content.startswith("<p class="):
                continue

            conversations[conv_id].append({
                "from": row.get("FROM", "").strip(),
                "from_url": row.get("SENDER PROFILE URL", "").strip(),
                "to": row.get("TO", "").strip(),
                "to_url": row.get("RECIPIENT PROFILE URLS", "").strip(),
                "date": row.get("DATE", "").strip(),
                "subject": row.get("SUBJECT", "").strip(),
                "content": content,
                "folder": row.get("FOLDER", "").strip(),
            })

    return dict(conversations)


def build_threads(conversations: dict, url_to_contact: dict) -> list:
    """Convert grouped conversations into thread records for DB insertion."""
    threads = []

    for conv_id, messages in conversations.items():
        if not messages:
            continue

        # Sort messages by date ascending
        messages.sort(key=lambda m: m["date"])

        # Identify the non-Justin participant(s)
        contact_urls = set()
        participants = set()
        for msg in messages:
            from_url = normalize_linkedin_url(msg["from_url"])
            to_url = normalize_linkedin_url(msg["to_url"])

            if from_url and from_url != normalize_linkedin_url(JUSTIN_PROFILE):
                contact_urls.add(from_url)
                participants.add(msg["from"])
            if to_url and to_url != normalize_linkedin_url(JUSTIN_PROFILE):
                contact_urls.add(to_url)
                participants.add(msg["to"])

        # Match to contact_id
        contact_id = None
        for url in contact_urls:
            if url in url_to_contact:
                contact_id = url_to_contact[url]
                break

        if contact_id is None:
            continue  # Can't match to a contact

        # Determine direction
        justin_sent = any(
            normalize_linkedin_url(m["from_url"]) == normalize_linkedin_url(JUSTIN_PROFILE)
            for m in messages
        )
        other_sent = any(
            normalize_linkedin_url(m["from_url"]) != normalize_linkedin_url(JUSTIN_PROFILE)
            for m in messages
        )

        if justin_sent and other_sent:
            direction = "bidirectional"
        elif justin_sent:
            direction = "outbound"
        else:
            direction = "inbound"

        # Build subject from first message with a subject, or conversation snippet
        subject = ""
        for msg in messages:
            if msg["subject"]:
                subject = msg["subject"]
                break
        if not subject:
            # Use first message content as snippet
            subject = messages[0]["content"][:80]
            if len(messages[0]["content"]) > 80:
                subject += "..."

        # Build raw_messages array
        raw_msgs = []
        for msg in messages:
            raw_msgs.append({
                "from": msg["from"],
                "from_url": msg["from_url"],
                "to": msg["to"],
                "to_url": msg["to_url"],
                "date": msg["date"],
                "body": msg["content"],
                "subject": msg.get("subject", ""),
            })

        first_date = messages[0]["date"]
        last_date = messages[-1]["date"]

        threads.append({
            "contact_id": contact_id,
            "thread_id": f"linkedin_{conv_id}",
            "account_email": "linkedin",
            "subject": subject,
            "snippet": messages[-1]["content"][:200],
            "message_count": len(messages),
            "first_message_date": first_date,
            "last_message_date": last_date,
            "direction": direction,
            "participants": list(participants),
            "labels": ["linkedin_message"],
            "raw_messages": raw_msgs,
            "summary": None,
            "gathered_at": datetime.now(timezone.utc).isoformat(),
        })

    return threads


def main():
    parser = argparse.ArgumentParser(description="Import LinkedIn messages into contact_email_threads")
    parser.add_argument("--test", "-t", action="store_true", help="Preview 5 conversations without inserting")
    parser.add_argument("--clear-first", action="store_true", help="Delete existing linkedin rows before import")
    args = parser.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        return

    supabase = create_client(url, key)
    print("Connected to Supabase")

    # Load contact URL map
    print("Loading contact LinkedIn URLs...")
    url_to_contact = load_contact_url_map(supabase)
    print(f"  {len(url_to_contact)} contacts with LinkedIn URLs")

    # Parse CSV
    print(f"Parsing {CSV_PATH}...")
    conversations = parse_csv(CSV_PATH)
    print(f"  {len(conversations)} conversations, {sum(len(m) for m in conversations.values())} messages")

    # Build threads
    print("Matching conversations to contacts...")
    threads = build_threads(conversations, url_to_contact)
    print(f"  {len(threads)} conversations matched to contacts")

    unmatched = len(conversations) - len(threads)
    if unmatched > 0:
        print(f"  {unmatched} conversations could not be matched (contact not in DB)")

    # Direction breakdown
    directions = defaultdict(int)
    for t in threads:
        directions[t["direction"]] += 1
    print(f"  Directions: {dict(directions)}")

    if args.test:
        print("\n--- TEST MODE: Preview of 5 threads ---\n")
        for t in threads[:5]:
            print(f"  Contact ID: {t['contact_id']}")
            print(f"  Subject: {t['subject'][:80]}")
            print(f"  Messages: {t['message_count']}")
            print(f"  Direction: {t['direction']}")
            print(f"  Date range: {t['first_message_date']} → {t['last_message_date']}")
            print(f"  Participants: {t['participants']}")
            print()
        return

    # Clear existing if requested
    if args.clear_first:
        print("Clearing existing linkedin rows...")
        supabase.table("contact_email_threads").delete().eq("account_email", "linkedin").execute()
        print("  Cleared.")

    # Insert in batches
    batch_size = 50
    inserted = 0
    errors = 0

    for i in range(0, len(threads), batch_size):
        batch = threads[i : i + batch_size]
        try:
            supabase.table("contact_email_threads").insert(batch).execute()
            inserted += len(batch)
            if inserted % 100 == 0 or inserted == len(threads):
                print(f"  Inserted {inserted}/{len(threads)}")
        except Exception as e:
            print(f"  Error inserting batch at offset {i}: {e}")
            # Try one at a time
            for t in batch:
                try:
                    supabase.table("contact_email_threads").insert(t).execute()
                    inserted += 1
                except Exception as e2:
                    errors += 1
                    print(f"    Failed thread {t['thread_id']}: {e2}")

    print(f"\n=== IMPORT COMPLETE ===")
    print(f"  Inserted: {inserted}")
    print(f"  Errors: {errors}")
    print(f"  Total threads in DB: {inserted} linkedin conversations")


if __name__ == "__main__":
    main()
