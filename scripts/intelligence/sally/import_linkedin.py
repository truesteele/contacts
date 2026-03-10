#!/usr/bin/env python3
"""
Import Sally's LinkedIn connections into sally_contacts table.

Reads docs/Sally/linkedin_connections.csv (849 connections) and cross-references
docs/Sally/sally_network_contacts.csv to pull calendar_email where available (~56).

Usage:
    python scripts/intelligence/sally/import_linkedin.py
    python scripts/intelligence/sally/import_linkedin.py --dry-run
"""

import argparse
import csv
import os
import re
from datetime import datetime
from urllib.parse import unquote

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

LINKEDIN_CSV = "docs/Sally/linkedin_connections.csv"
NETWORK_CSV = "docs/Sally/sally_network_contacts.csv"


def normalize_linkedin_url(url: str) -> str | None:
    """Normalize LinkedIn URL: lowercase, strip trailing slash, ensure www prefix."""
    if not url or not url.strip():
        return None
    url = unquote(url.strip()).lower().rstrip("/")
    # Ensure www prefix
    url = url.replace("://linkedin.com/", "://www.linkedin.com/")
    url = url.replace("://www.linkedin.com/", "://www.linkedin.com/")  # no-op if already there
    if not url.startswith("http"):
        url = "https://www.linkedin.com/" + url.lstrip("/")
    return url


def extract_username(url: str) -> str | None:
    """Extract LinkedIn username from URL."""
    if not url:
        return None
    match = re.search(r"linkedin\.com/in/([^/?#]+)", url)
    return match.group(1) if match else None


def parse_connection_date(date_str: str) -> str | None:
    """Parse 'March 6, 2026' → '2026-03-06'."""
    if not date_str or not date_str.strip():
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%B %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def load_email_map(network_csv: str) -> dict[str, str]:
    """Load LinkedIn URL → calendar_email mapping from network CSV."""
    email_map = {}
    with open(network_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get("calendar_email", "").strip()
            url = row.get("linkedin_url", "").strip()
            if email and url:
                normalized = normalize_linkedin_url(url)
                if normalized:
                    email_map[normalized] = email
    return email_map


def main():
    parser = argparse.ArgumentParser(description="Import Sally's LinkedIn connections")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be imported without inserting")
    args = parser.parse_args()

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    # Load email cross-reference
    email_map = load_email_map(NETWORK_CSV)
    print(f"Loaded {len(email_map)} email mappings from network CSV")

    # Read LinkedIn connections
    contacts = []
    with open(LINKEDIN_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            first_name = row.get("First Name", "").strip()
            last_name = row.get("Last Name", "").strip()
            linkedin_url = row.get("LinkedIn URL", "").strip()
            title = row.get("Title", "").strip()
            connection_date = row.get("Connection Date", "").strip()

            if not linkedin_url:
                continue

            normalized_url = normalize_linkedin_url(linkedin_url)
            username = extract_username(normalized_url) if normalized_url else None
            normalized_name = f"{first_name} {last_name}".lower().strip()
            parsed_date = parse_connection_date(connection_date)

            # Cross-reference email
            email = email_map.get(normalized_url) if normalized_url else None

            contact = {
                "first_name": first_name or None,
                "last_name": last_name or None,
                "normalized_full_name": normalized_name or None,
                "linkedin_url": normalized_url,
                "linkedin_username": username,
                "position": title if title and title != "--" else None,
                "headline": title if title and title != "--" else None,
                "email": email,
            }
            if parsed_date:
                contact["connected_on"] = parsed_date

            contacts.append(contact)

    print(f"Parsed {len(contacts)} contacts from LinkedIn CSV")
    emails_found = sum(1 for c in contacts if c.get("email"))
    print(f"  {emails_found} have email from network CSV cross-reference")

    if args.dry_run:
        print("\n[DRY RUN] Would insert/upsert the following:")
        for c in contacts[:5]:
            print(f"  {c['first_name']} {c['last_name']} — {c['linkedin_url']}"
                  + (f" — {c['email']}" if c.get('email') else ""))
        print(f"  ... and {len(contacts) - 5} more")
        return

    # Upsert into sally_contacts in batches
    batch_size = 100
    inserted = 0
    updated = 0
    errors = 0

    for i in range(0, len(contacts), batch_size):
        batch = contacts[i : i + batch_size]
        for contact in batch:
            try:
                # Check if contact exists by linkedin_url
                existing = (
                    supabase.table("sally_contacts")
                    .select("id")
                    .eq("linkedin_url", contact["linkedin_url"])
                    .execute()
                )
                if existing.data:
                    # Update existing
                    supabase.table("sally_contacts").update(contact).eq(
                        "linkedin_url", contact["linkedin_url"]
                    ).execute()
                    updated += 1
                else:
                    # Insert new
                    supabase.table("sally_contacts").insert(contact).execute()
                    inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"  Error for {contact.get('first_name')} {contact.get('last_name')}: {e}")

        print(f"  Processed {min(i + batch_size, len(contacts))}/{len(contacts)}")

    print(f"\nDone! Inserted: {inserted}, Updated: {updated}, Errors: {errors}")

    # Verify
    count_result = supabase.table("sally_contacts").select("id", count="exact").execute()
    email_count = (
        supabase.table("sally_contacts")
        .select("id", count="exact")
        .neq("email", "null")
        .execute()
    )
    print(f"Total sally_contacts: {count_result.count}")
    print(f"With email: {email_count.count}")


if __name__ == "__main__":
    main()
