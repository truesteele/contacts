#!/usr/bin/env python3
"""
Comprehensive Email Enrichment Script
Uses Tomba API to find emails by name + domain or LinkedIn URL.
Checks found emails against the invalid_emails blocklist before saving.
Tracks attempts to avoid duplicate lookups.

Usage:
  python scripts/enrichment/enrich_all_emails.py --test          # 5 contacts only
  python scripts/enrichment/enrich_all_emails.py --limit 50      # First 50
  python scripts/enrichment/enrich_all_emails.py --dry-run       # Don't write to DB
  python scripts/enrichment/enrich_all_emails.py                 # Full run
"""

import os
import sys
import json
import time
import re
import requests
import argparse
from datetime import datetime
from typing import Dict, List, Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

TOMBA_API_KEY = os.getenv("TOMBA_API_KEY")
TOMBA_SECRET_KEY = os.getenv("TOMBA_SECRET_KEY")

# Regex to strip common company suffixes for domain guessing
COMPANY_SUFFIXES = re.compile(
    r'\b(Inc\.?|LLC|Ltd\.?|Corp\.?|Co\.?|Company|Group|Holdings|International|'
    r'Incorporated|Limited|Corporation|PLC|LP|LLP|GmbH|AG|SA|SAS|BV|NV|Pty)\b\.?,?\s*',
    re.IGNORECASE
)


def get_db_conn():
    """Get a direct PostgreSQL connection for blocklist queries."""
    return psycopg2.connect(
        host="db.ypqsrejrsocebnldicke.supabase.co",
        port=5432,
        dbname="postgres",
        user="postgres",
        password=os.environ["SUPABASE_DB_PASSWORD"],
    )


def load_invalid_emails(conn) -> set:
    """Load all known-invalid emails from the blocklist table."""
    cur = conn.cursor()
    cur.execute("SELECT LOWER(email_address) FROM invalid_emails")
    return {row[0] for row in cur.fetchall()}


def guess_domain(company: str) -> Optional[str]:
    """Guess a company's email domain from its name."""
    if not company:
        return None
    cleaned = COMPANY_SUFFIXES.sub('', company.lower()).strip().rstrip('.,- ')
    if not cleaned:
        return None
    slug = re.sub(r'[^a-z0-9\s]', '', cleaned).strip().replace(' ', '')
    return f"{slug}.com" if slug else None


class TombaEmailEnricher:
    def __init__(self, limit: int = None, test_mode: bool = False, dry_run: bool = False):
        self.supabase = None
        self.db_conn = None
        self.invalid_emails = set()
        self.limit = limit
        self.test_mode = test_mode
        self.dry_run = dry_run
        self.stats = {
            'total_processed': 0,
            'emails_found': 0,
            'blocked_invalid': 0,
            'no_emails_found': 0,
            'already_attempted': 0,
            'failed': 0,
        }

        if not TOMBA_API_KEY or not TOMBA_SECRET_KEY:
            raise ValueError("TOMBA_API_KEY and TOMBA_SECRET_KEY must be set in environment")

    def connect(self):
        """Connect to Supabase and load blocklist."""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False

        self.supabase = create_client(url, key)
        print("  Database: connected (Supabase)")

        self.db_conn = get_db_conn()
        self.invalid_emails = load_invalid_emails(self.db_conn)
        print(f"  Invalid emails blocklist: {len(self.invalid_emails)} entries")
        return True

    def find_email_tomba(self, first_name: str, last_name: str, domain: str) -> Optional[str]:
        """Call Tomba email-finder API. Returns email if found with good confidence + name match."""
        headers = {
            "X-Tomba-Key": TOMBA_API_KEY,
            "X-Tomba-Secret": TOMBA_SECRET_KEY,
        }

        try:
            resp = requests.get(
                "https://api.tomba.io/v1/email-finder",
                params={
                    "domain": domain,
                    "first_name": first_name,
                    "last_name": last_name,
                },
                headers=headers,
                timeout=15,
            )

            if resp.status_code == 429:
                print("    Tomba: rate limited / quota exhausted")
                return None
            if resp.status_code != 200:
                return None

            data = resp.json().get("data", {})
            email = data.get("email")
            score = data.get("score", 0)
            tomba_first = (data.get("first_name") or "").lower().strip()
            tomba_last = (data.get("last_name") or "").lower().strip()

            if not email or score < 70:
                return None

            # Name matching guard
            first_lower = first_name.lower().strip()
            last_lower = last_name.lower().strip()
            first_ok = (tomba_first == first_lower
                        or first_lower.startswith(tomba_first)
                        or tomba_first.startswith(first_lower))
            last_ok = (tomba_last == last_lower
                       or last_lower.startswith(tomba_last)
                       or tomba_last.startswith(last_lower))

            if not (first_ok and last_ok):
                if self.test_mode:
                    print(f"    Tomba: name mismatch — got {tomba_first} {tomba_last}")
                return None

            return email

        except requests.RequestException as e:
            if self.test_mode:
                print(f"    Tomba request error: {e}")
            return None

    def get_contacts_without_email(self) -> List[Dict]:
        """Get contacts without email, excluding already-attempted."""
        query = self.supabase.table('contacts').select(
            'id, first_name, last_name, linkedin_url, company, position, '
            'enrich_current_company, email, enrich_person_from_profile'
        ).is_('email', 'null')

        if self.limit:
            query = query.limit(self.limit * 2)

        response = query.execute()
        contacts = response.data

        filtered = []
        for contact in contacts:
            enrich_data = contact.get('enrich_person_from_profile')
            if enrich_data:
                try:
                    data = json.loads(enrich_data) if isinstance(enrich_data, str) else enrich_data
                    if data.get('tomba_lookup_attempted'):
                        self.stats['already_attempted'] += 1
                        continue
                except Exception:
                    pass

            if not contact.get('email'):
                filtered.append(contact)
                if self.limit and len(filtered) >= self.limit:
                    break

        return filtered

    def update_contact(self, contact_id: int, contact: Dict, email: Optional[str]) -> bool:
        """Update contact with found email and track the attempt."""
        if self.dry_run:
            return True

        try:
            updates = {}

            enrich_data = {}
            if contact.get('enrich_person_from_profile'):
                try:
                    enrich_data = (json.loads(contact['enrich_person_from_profile'])
                                   if isinstance(contact['enrich_person_from_profile'], str)
                                   else contact['enrich_person_from_profile'])
                except Exception:
                    pass

            enrich_data['tomba_lookup_attempted'] = True
            enrich_data['tomba_lookup_date'] = datetime.now().isoformat()

            if email:
                updates['email'] = email
                enrich_data['tomba_email_found'] = True
            else:
                enrich_data['tomba_email_found'] = False

            updates['enrich_person_from_profile'] = json.dumps(enrich_data)

            self.supabase.table('contacts').update(updates).eq('id', contact_id).execute()
            return True
        except Exception as e:
            print(f"    ERROR updating contact {contact_id}: {e}")
            return False

    def run(self):
        """Main enrichment loop."""
        if not self.connect():
            return False

        print("\n  Fetching contacts without email...")
        contacts = self.get_contacts_without_email()

        if not contacts:
            print("  No contacts need email enrichment.")
            print(f"  Skipped {self.stats['already_attempted']} with previous Tomba attempts")
            return True

        print(f"  Contacts to process: {len(contacts)}")
        print(f"  Skipped (already attempted): {self.stats['already_attempted']}")
        print(f"  Mode: {'DRY-RUN' if self.dry_run else 'LIVE'}")

        if self.test_mode:
            print("  TEST MODE — processing first 5 only")
            contacts = contacts[:5]

        print("\n" + "=" * 60)
        print("TOMBA EMAIL ENRICHMENT")
        print("=" * 60)

        for i, contact in enumerate(contacts, 1):
            self.stats['total_processed'] += 1
            first = contact.get('first_name') or ''
            last = contact.get('last_name') or ''
            name = f"{first} {last}".strip()
            company = contact.get('company') or contact.get('enrich_current_company') or ''

            print(f"\n  [{i}/{len(contacts)}] {name} | {company}")

            # Need at least a name and company to search
            if not first or not last:
                print("    Skip: missing first or last name")
                self.stats['no_emails_found'] += 1
                self.update_contact(contact['id'], contact, None)
                continue

            domain = guess_domain(company) if company else None
            if not domain:
                print("    Skip: no domain from company name")
                self.stats['no_emails_found'] += 1
                self.update_contact(contact['id'], contact, None)
                continue

            # Tomba lookup
            email = self.find_email_tomba(first, last, domain)

            if email:
                # Check against invalid emails blocklist
                if email.lower() in self.invalid_emails:
                    print(f"    Found {email} but it's in invalid blocklist — skipping")
                    self.stats['blocked_invalid'] += 1
                    email = None
                else:
                    print(f"    Found: {email}")
                    self.stats['emails_found'] += 1
            else:
                self.stats['no_emails_found'] += 1

            if self.update_contact(contact['id'], contact, email):
                if not email:
                    pass  # silent for misses
            else:
                self.stats['failed'] += 1

            # Rate limiting (Tomba free tier)
            time.sleep(1.0)

            # Progress every 25
            if i % 25 == 0 and i < len(contacts):
                print(f"\n  --- Progress: {i}/{len(contacts)} "
                      f"({self.stats['emails_found']} found) ---")

        self.print_summary()

        if self.db_conn:
            self.db_conn.close()
        return True

    def print_summary(self):
        """Print summary."""
        print("\n" + "=" * 60)
        print("TOMBA ENRICHMENT SUMMARY")
        print("=" * 60)
        print(f"  Total processed:      {self.stats['total_processed']}")
        print(f"  Emails found:         {self.stats['emails_found']}")
        print(f"  Blocked (invalid):    {self.stats['blocked_invalid']}")
        print(f"  No email found:       {self.stats['no_emails_found']}")
        print(f"  Previously attempted: {self.stats['already_attempted']}")
        print(f"  Failed to update:     {self.stats['failed']}")
        if self.stats['total_processed'] > 0:
            rate = self.stats['emails_found'] / self.stats['total_processed'] * 100
            print(f"  Hit rate:             {rate:.1f}%")
        if self.dry_run:
            print(f"  Mode:                 DRY-RUN (no DB writes)")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Tomba email enrichment for contacts')
    parser.add_argument('--limit', '-l', type=int, help='Limit number of contacts')
    parser.add_argument('--test', '-t', action='store_true', help='Test mode (5 contacts)')
    parser.add_argument('--dry-run', '-d', action='store_true', help="Don't write to database")
    args = parser.parse_args()

    try:
        enricher = TombaEmailEnricher(limit=args.limit, test_mode=args.test, dry_run=args.dry_run)
        success = enricher.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
