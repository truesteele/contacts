#!/usr/bin/env python3
"""Import LinkedIn Connections.csv into Supabase, skipping duplicates and detecting URL changes."""

import csv
import os
import re
import sys
from datetime import datetime
from urllib.parse import unquote

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
CSV_PATH = "docs/Connections.csv"


def normalize_linkedin_url(url: str) -> str:
    """Normalize LinkedIn URL for comparison."""
    if not url:
        return ""
    url = unquote(url).strip().rstrip("/").lower()
    # Remove query params
    url = url.split("?")[0]
    # Remove trailing slash
    url = url.rstrip("/")
    # Ensure consistent prefix
    url = re.sub(r"^https?://(www\.)?linkedin\.com", "https://www.linkedin.com", url)
    return url


def parse_csv(path: str) -> list[dict]:
    """Parse LinkedIn Connections.csv, skipping the notes header."""
    contacts = []
    with open(path, "r", encoding="utf-8-sig") as f:
        # Find the actual header line (starts with "First Name")
        for line in f:
            if line.strip().startswith("First Name"):
                # Put this line back by creating a reader from remaining lines
                # We need to re-construct with header
                remaining = f.read()
                break
        else:
            print("ERROR: Could not find header line in CSV")
            return []

        # Parse from header onward
        full_csv = line + remaining
        reader = csv.DictReader(full_csv.splitlines())

        for row in reader:
            url = row.get("URL", "").strip()
            if not url:
                continue
            contacts.append({
                "first_name": row.get("First Name", "").strip(),
                "last_name": row.get("Last Name", "").strip(),
                "email": row.get("Email Address", "").strip() or None,
                "linkedin_url": url,
                "company": row.get("Company", "").strip() or None,
                "position": row.get("Position", "").strip() or None,
                "connected_on": row.get("Connected On", "").strip(),
            })
    return contacts


def fetch_existing_contacts() -> list[dict]:
    """Fetch all existing contacts with their LinkedIn URLs and names."""
    all_contacts = []
    page_size = 1000
    offset = 0
    while True:
        resp = supabase.table("contacts").select(
            "id,first_name,last_name,linkedin_url,email"
        ).range(offset, offset + page_size - 1).execute()
        all_contacts.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_contacts


def main():
    print("Parsing CSV...")
    csv_contacts = parse_csv(CSV_PATH)
    print(f"  Found {len(csv_contacts)} contacts in CSV")

    print("Fetching existing contacts from Supabase...")
    existing = fetch_existing_contacts()
    print(f"  Found {len(existing)} existing contacts")

    # Build lookup by normalized LinkedIn URL
    existing_by_url = {}
    for c in existing:
        if c.get("linkedin_url"):
            norm = normalize_linkedin_url(c["linkedin_url"])
            existing_by_url[norm] = c

    # Also build name-based lookup for contacts without LinkedIn
    existing_by_name = {}
    for c in existing:
        key = (c.get("first_name", "").lower().strip(), c.get("last_name", "").lower().strip())
        if key[0] and key[1]:
            existing_by_name[key] = c

    new_contacts = []
    url_changes = []
    name_dupes = []

    for csv_c in csv_contacts:
        norm_url = normalize_linkedin_url(csv_c["linkedin_url"])

        # Check if LinkedIn URL already exists
        if norm_url in existing_by_url:
            # Check if the raw URL differs (potential URL change/redirect)
            db_record = existing_by_url[norm_url]
            db_norm = normalize_linkedin_url(db_record["linkedin_url"])
            # URLs match after normalization - this is a duplicate, skip
            continue

        # Check by name (for contacts that might be in DB without LinkedIn URL or with different URL)
        name_key = (csv_c["first_name"].lower().strip(), csv_c["last_name"].lower().strip())
        if name_key in existing_by_name:
            db_record = existing_by_name[name_key]
            db_url = normalize_linkedin_url(db_record.get("linkedin_url") or "")
            csv_url = norm_url

            if db_url and db_url != csv_url:
                # Different LinkedIn URL - could be URL change
                url_changes.append({
                    "id": db_record["id"],
                    "name": f"{db_record['first_name']} {db_record['last_name']}",
                    "old_url": db_record["linkedin_url"],
                    "new_url": csv_c["linkedin_url"],
                })
            elif not db_url:
                # Contact exists but has no LinkedIn URL - update it
                url_changes.append({
                    "id": db_record["id"],
                    "name": f"{db_record['first_name']} {db_record['last_name']}",
                    "old_url": None,
                    "new_url": csv_c["linkedin_url"],
                })
            else:
                name_dupes.append(name_key)
            continue

        new_contacts.append(csv_c)

    print(f"\n{'='*60}")
    print(f"ANALYSIS")
    print(f"{'='*60}")
    print(f"  New contacts to insert:    {len(new_contacts)}")
    print(f"  LinkedIn URL changes:      {len(url_changes)}")
    print(f"  Duplicates skipped:        {len(csv_contacts) - len(new_contacts) - len(url_changes)}")

    # Show URL changes
    if url_changes:
        print(f"\n--- LinkedIn URL Changes/Additions ---")
        for ch in url_changes:
            old = ch['old_url'] or '(none)'
            print(f"  [{ch['id']}] {ch['name']}: {old} -> {ch['new_url']}")

    # Apply URL changes
    if url_changes:
        print(f"\nApplying {len(url_changes)} URL updates...")
        for ch in url_changes:
            supabase.table("contacts").update({
                "linkedin_url": ch["new_url"]
            }).eq("id", ch["id"]).execute()
        print(f"  Updated {len(url_changes)} LinkedIn URLs")

    # Insert new contacts
    if new_contacts:
        print(f"\nInserting {len(new_contacts)} new contacts...")
        batch_size = 50
        inserted = 0
        for i in range(0, len(new_contacts), batch_size):
            batch = new_contacts[i:i + batch_size]
            rows = []
            for c in batch:
                row = {
                    "first_name": c["first_name"],
                    "last_name": c["last_name"],
                    "linkedin_url": c["linkedin_url"],
                    "connection_type": "Direct",
                    "enrichment_source": "linkedin-csv-2026",
                }
                if c["email"]:
                    row["email"] = c["email"]
                if c["company"]:
                    row["company"] = c["company"]
                if c["position"]:
                    row["position"] = c["position"]
                rows.append(row)
            resp = supabase.table("contacts").insert(rows).execute()
            inserted += len(resp.data)
            print(f"  Batch {i // batch_size + 1}: inserted {len(resp.data)} contacts (total: {inserted})")

        print(f"\n  Total inserted: {inserted}")
    else:
        print("\nNo new contacts to insert.")

    print(f"\n{'='*60}")
    print(f"DONE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
