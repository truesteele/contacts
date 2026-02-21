#!/usr/bin/env python3
"""
Network Intelligence — FEC Political Donation Enrichment

Queries the OpenFEC API to find federal campaign contribution records for each
contact, storing results in the fec_donations JSONB column. Federal campaign
contributions ($200+) are public record and serve as the strongest free wealth
indicator available.

Usage:
  python scripts/intelligence/enrich_fec_donations.py --test           # 1 contact
  python scripts/intelligence/enrich_fec_donations.py --batch 50       # 50 contacts
  python scripts/intelligence/enrich_fec_donations.py --start-from 500 # Skip first 500
  python scripts/intelligence/enrich_fec_donations.py                  # Full run (~2,400)
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────

OPENFEC_BASE = "https://api.open.fec.gov/v1"
CYCLES = [2026, 2024, 2022, 2020]
MAX_DONATIONS_STORED = 10  # Keep top N recent donations in JSONB
RATE_LIMIT_DELAY = 3.7     # ~970 req/hr, safely under 1,000/hr limit
SELECT_COLS = "id, first_name, last_name, city, state, fec_donations"


# ── OpenFEC API ───────────────────────────────────────────────────────

def query_fec(api_key: str, first_name: str, last_name: str,
              state: str = None, city: str = None) -> list[dict]:
    """
    Query OpenFEC schedule_a for individual contributions by name.
    Paginates through all results. Returns raw donation records.
    """
    all_results = []
    last_index = None
    last_date = None

    # FEC API expects LAST, FIRST format
    contributor_name = f"{last_name}, {first_name}"

    while True:
        params = {
            "api_key": api_key,
            "contributor_name": contributor_name,
            "two_year_transaction_period": CYCLES,
            "per_page": 100,
            "sort": "-contribution_receipt_date",
            "is_individual": "true",
        }

        # State filter for disambiguation (only if we have it)
        if state:
            # Normalize state to 2-letter code
            state_code = normalize_state(state)
            if state_code:
                params["contributor_state"] = state_code

        # Pagination via last_index
        if last_index:
            params["last_index"] = last_index
            params["last_contribution_receipt_date"] = last_date

        try:
            resp = requests.get(
                f"{OPENFEC_BASE}/schedules/schedule_a/",
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"    FEC API error: {e}")
            break

        results = data.get("results", [])
        all_results.extend(results)

        # Check pagination
        pagination = data.get("pagination", {})
        last_indexes = pagination.get("last_indexes")
        if not last_indexes or len(results) < 100:
            break

        last_index = last_indexes.get("last_index")
        last_date = last_indexes.get("last_contribution_receipt_date")

    return all_results


def normalize_state(state_str: str) -> str:
    """Convert state name to 2-letter code if needed."""
    if not state_str:
        return ""
    state_str = state_str.strip()
    if len(state_str) == 2:
        return state_str.upper()

    # Common state name → code mapping
    STATE_MAP = {
        "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
        "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
        "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
        "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
        "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
        "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
        "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
        "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
        "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
        "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
        "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
        "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
        "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    }
    return STATE_MAP.get(state_str.lower(), "")


def disambiguate_results(results: list[dict], first_name: str, last_name: str,
                         city: str = None, state: str = None) -> list[dict]:
    """
    Filter FEC results to likely matches. The API does fuzzy name matching,
    so we need to verify the results are for the right person.
    Uses city/state when available for common names.
    """
    if not results:
        return []

    filtered = []
    first_lower = first_name.lower().strip()
    last_lower = last_name.lower().strip()
    state_code = normalize_state(state) if state else ""
    city_lower = city.lower().strip() if city else ""

    # For compound last names like "Kapor Klein", split into parts
    last_parts = last_lower.split()

    for r in results:
        # Check name match — FEC splits names differently than LinkedIn
        # e.g., "Kapor Klein" → contributor_last_name="KLEIN", contributor_name="KLEIN, FREADA KAPOR"
        fec_first = (r.get("contributor_first_name") or "").lower().strip()
        fec_last = (r.get("contributor_last_name") or "").lower().strip()
        fec_full_name = (r.get("contributor_name") or "").lower().strip()

        # Last name match: exact, or FEC last equals any part of compound last name
        last_match = (
            fec_last == last_lower or
            fec_last in last_parts or
            last_lower.endswith(fec_last)
        )
        if not last_match:
            continue

        # First name match: exact, prefix, or contained
        first_match = (
            fec_first == first_lower or
            fec_first.startswith(first_lower) or
            first_lower.startswith(fec_first)
        )
        if not first_match:
            continue

        # For compound last names, verify the full contributor_name contains all parts
        if len(last_parts) > 1 and fec_full_name:
            if not all(part in fec_full_name for part in last_parts):
                continue

        # For common names, also check state/city if available
        fec_state = (r.get("contributor_state") or "").upper()
        fec_city = (r.get("contributor_city") or "").lower().strip()

        # If we have state info, prefer matches in the same state
        # but don't exclude (people move)
        r["_state_match"] = (state_code and fec_state == state_code)
        r["_city_match"] = (city_lower and fec_city == city_lower)

        filtered.append(r)

    # If we have state matches and non-state matches, prefer state matches
    # for common names (>10 results)
    if len(filtered) > 10 and state_code:
        state_matches = [r for r in filtered if r["_state_match"]]
        if state_matches:
            filtered = state_matches

    return filtered


def build_fec_summary(results: list[dict]) -> dict:
    """Build the JSONB summary from filtered FEC results."""
    if not results:
        return {
            "total_amount": 0,
            "donation_count": 0,
            "max_single": 0,
            "cycles": [],
            "recent_donations": [],
            "employer_from_fec": None,
            "occupation_from_fec": None,
            "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }

    total_amount = sum(r.get("contribution_receipt_amount", 0) for r in results)
    max_single = max((r.get("contribution_receipt_amount", 0) for r in results), default=0)
    cycles = sorted(set(str(r.get("two_year_transaction_period", "")) for r in results), reverse=True)

    # Build recent donations list (top N by date)
    sorted_results = sorted(
        results,
        key=lambda r: r.get("contribution_receipt_date") or "",
        reverse=True,
    )

    recent_donations = []
    for r in sorted_results[:MAX_DONATIONS_STORED]:
        committee_name = r.get("committee_name") or ""
        if not committee_name and r.get("committee"):
            committee_name = r["committee"].get("name", "")
        recent_donations.append({
            "committee": committee_name,
            "amount": r.get("contribution_receipt_amount", 0),
            "date": r.get("contribution_receipt_date", ""),
        })

    # Get most recent employer/occupation from FEC
    employer = None
    occupation = None
    for r in sorted_results:
        if not employer and r.get("contributor_employer"):
            employer = r["contributor_employer"]
        if not occupation and r.get("contributor_occupation"):
            occupation = r["contributor_occupation"]
        if employer and occupation:
            break

    return {
        "total_amount": round(total_amount, 2),
        "donation_count": len(results),
        "max_single": round(max_single, 2),
        "cycles": cycles,
        "recent_donations": recent_donations,
        "employer_from_fec": employer,
        "occupation_from_fec": occupation,
        "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


# ── Main Enrichment ──────────────────────────────────────────────────

class FECEnricher:
    def __init__(self, test_mode=False, batch_size=None, start_from=0, workers=4):
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.start_from = start_from
        self.workers = workers
        self.supabase: Client = None
        self.api_key: str = ""
        self.stats = {
            "processed": 0,
            "found": 0,
            "no_results": 0,
            "errors": 0,
            "skipped": 0,
            "api_calls": 0,
        }

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        self.api_key = os.environ.get("OPENFEC_API_KEY", "")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        if not self.api_key:
            print("ERROR: Missing OPENFEC_API_KEY")
            return False

        self.supabase = create_client(url, key)
        print("Connected to Supabase + OpenFEC API key loaded")
        return True

    def get_contacts(self) -> list[dict]:
        """Fetch contacts that don't have FEC data yet."""
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            page = (
                self.supabase.table("contacts")
                .select(SELECT_COLS)
                .is_("fec_donations", "null")
                .order("id")
                .range(offset, offset + page_size - 1)
                .execute()
            ).data

            if not page:
                break
            all_contacts.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        # Apply start-from offset
        if self.start_from > 0:
            all_contacts = all_contacts[self.start_from:]

        # Apply batch/test limits
        if self.test_mode:
            all_contacts = all_contacts[:1]
        elif self.batch_size:
            all_contacts = all_contacts[:self.batch_size]

        return all_contacts

    def process_contact(self, contact: dict) -> bool:
        """Query FEC for a single contact and store results."""
        cid = contact["id"]
        first = contact.get("first_name", "").strip()
        last = contact.get("last_name", "").strip()
        city = contact.get("city")
        state = contact.get("state")
        name = f"{first} {last}"

        if not first or not last:
            self.stats["skipped"] += 1
            return False

        # Query FEC
        self.stats["api_calls"] += 1
        raw_results = query_fec(self.api_key, first, last, state, city)

        # Disambiguate
        filtered = disambiguate_results(raw_results, first, last, city, state)

        # Build summary
        summary = build_fec_summary(filtered)

        # Save to Supabase
        try:
            self.supabase.table("contacts").update({
                "fec_donations": summary,
            }).eq("id", cid).execute()
        except Exception as e:
            print(f"  ERROR [{cid}] {name}: DB write failed: {e}")
            self.stats["errors"] += 1
            return False

        self.stats["processed"] += 1
        if summary["donation_count"] > 0:
            self.stats["found"] += 1
            print(f"  [{cid}] {name}: ${summary['total_amount']:,.0f} across "
                  f"{summary['donation_count']} donations "
                  f"(max ${summary['max_single']:,.0f}, "
                  f"cycles: {', '.join(summary['cycles'])})")
        else:
            self.stats["no_results"] += 1

        return True

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()
        contacts = self.get_contacts()
        total = len(contacts)
        print(f"Found {total} contacts to process")

        if total == 0:
            print("Nothing to do — all contacts already have FEC data")
            return True

        mode_str = "TEST" if self.test_mode else f"BATCH {self.batch_size}" if self.batch_size else "FULL"
        print(f"\n--- {mode_str} MODE: Processing {total} contacts ---")
        print(f"    Rate limit: {RATE_LIMIT_DELAY}s between API calls (~{3600/RATE_LIMIT_DELAY:.0f}/hr)")
        print()

        # Sequential processing due to API rate limit (1,000/hr)
        for i, contact in enumerate(contacts):
            self.process_contact(contact)

            # Rate limiting
            if i < total - 1:
                time.sleep(RATE_LIMIT_DELAY)

            # Progress every 50
            if (i + 1) % 50 == 0 or (i + 1) == total:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed * 3600 if elapsed > 0 else 0
                print(f"\n--- Progress: {i + 1}/{total} "
                      f"({self.stats['found']} found, "
                      f"{self.stats['no_results']} no results, "
                      f"{self.stats['errors']} errors) "
                      f"[{rate:.0f} contacts/hr, {elapsed:.0f}s elapsed] ---\n")

        elapsed = time.time() - start_time
        self.print_summary(elapsed)
        return self.stats["errors"] < total * 0.05

    def print_summary(self, elapsed: float):
        s = self.stats
        print("\n" + "=" * 60)
        print("FEC ENRICHMENT SUMMARY")
        print("=" * 60)
        print(f"  Contacts processed: {s['processed']}")
        print(f"  With FEC records:   {s['found']}")
        print(f"  No FEC records:     {s['no_results']}")
        print(f"  Skipped (no name):  {s['skipped']}")
        print(f"  Errors:             {s['errors']}")
        print(f"  API calls:          {s['api_calls']}")
        print(f"  Time elapsed:       {elapsed:.1f}s")
        if s["processed"] > 0:
            pct = s["found"] / s["processed"] * 100
            print(f"  Hit rate:           {pct:.1f}%")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Enrich contacts with FEC political donation data"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only 1 contact for validation")
    parser.add_argument("--batch", "-b", type=int, default=None,
                        help="Process N contacts")
    parser.add_argument("--start-from", "-s", type=int, default=0,
                        help="Skip first N contacts (for resuming)")
    parser.add_argument("--workers", "-w", type=int, default=4,
                        help="Number of workers (unused — sequential due to rate limit)")
    args = parser.parse_args()

    enricher = FECEnricher(
        test_mode=args.test,
        batch_size=args.batch,
        start_from=args.start_from,
        workers=args.workers,
    )
    success = enricher.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
