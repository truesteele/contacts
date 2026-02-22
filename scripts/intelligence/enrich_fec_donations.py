#!/usr/bin/env python3
"""
Network Intelligence — FEC Political Donation Enrichment

Queries the OpenFEC API to find federal campaign contribution records for each
contact, storing results in the fec_donations JSONB column. Federal campaign
contributions ($200+) are public record and serve as the strongest free wealth
indicator available.

Uses GPT-5 mini to verify that FEC records belong to the correct person (not
a same-name collision), matching on employer, occupation, city, and state.

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
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────

OPENFEC_BASE = "https://api.open.fec.gov/v1"
CYCLES = [2026, 2024, 2022, 2020]
MAX_DONATIONS_STORED = 10  # Keep top N recent donations in JSONB
TARGET_REQUESTS_PER_HOUR = 950  # Under 1,000/hr API limit
SELECT_COLS = (
    "id, first_name, last_name, city, state, country, "
    "company, position, headline, enrich_employment, fec_donations"
)

# FEC is US-only — skip contacts in other countries
US_COUNTRY_VALUES = {"united states", "us", "usa", "united states of america", ""}

# State map for extracting state from city strings like "San Francisco, California"
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
STATE_CODES = set(STATE_MAP.values())


class RateLimiter:
    """Thread-safe rate limiter for concurrent API calls."""

    def __init__(self, max_per_hour: int):
        self.min_interval = 3600.0 / max_per_hour
        self.lock = threading.Lock()
        self.last_time = 0.0

    def acquire(self):
        """Block until it's safe to make the next API call."""
        with self.lock:
            now = time.monotonic()
            wait = self.min_interval - (now - self.last_time)
            if wait > 0:
                time.sleep(wait)
            self.last_time = time.monotonic()


# ── State extraction ─────────────────────────────────────────────────

def normalize_state(state_str: str) -> str:
    """Convert state name to 2-letter code if needed."""
    if not state_str:
        return ""
    state_str = state_str.strip()
    if len(state_str) == 2 and state_str.upper() in STATE_CODES:
        return state_str.upper()
    return STATE_MAP.get(state_str.lower(), "")


def extract_state_from_employment(contact: dict) -> str:
    """Try to extract US state from employment data when contact state is missing."""
    employment = contact.get("enrich_employment")
    if not employment or not isinstance(employment, list):
        return ""
    for emp in employment[:3]:  # Check recent jobs
        if not isinstance(emp, dict):
            continue
        location = emp.get("location", "") or emp.get("company_location", "")
        if not location:
            continue
        # Try "City, ST" or "City, State" patterns
        parts = [p.strip() for p in location.split(",")]
        for part in parts:
            code = normalize_state(part)
            if code:
                return code
    return ""


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


def disambiguate_results(results: list[dict], first_name: str, last_name: str,
                         city: str = None, state: str = None) -> list[dict]:
    """
    Filter FEC results to exact name matches only.
    GPT verification handles the actual person-matching downstream.
    """
    if not results:
        return []

    filtered = []
    first_lower = first_name.lower().strip()
    last_lower = last_name.lower().strip()
    state_code = normalize_state(state) if state else ""

    # For compound last names like "Kapor Klein", split into parts
    last_parts = last_lower.split()

    for r in results:
        fec_first = (r.get("contributor_first_name") or "").lower().strip()
        fec_last = (r.get("contributor_last_name") or "").lower().strip()
        fec_full_name = (r.get("contributor_name") or "").lower().strip()

        # Last name: exact match, or FEC last equals any part of compound last name
        last_match = (
            fec_last == last_lower or
            fec_last in last_parts or
            last_lower.endswith(fec_last)
        )
        if not last_match:
            continue

        # First name: EXACT match only (no prefix matching)
        # "Andre" must NOT match "Andrea" or "Andrew"
        first_match = (fec_first == first_lower)
        if not first_match:
            continue

        # For compound last names, verify the full contributor_name contains all parts
        if len(last_parts) > 1 and fec_full_name:
            if not all(part in fec_full_name for part in last_parts):
                continue

        # Tag state/city match for downstream use
        fec_state = (r.get("contributor_state") or "").upper()
        fec_city = (r.get("contributor_city") or "").lower().strip()
        r["_state_match"] = (state_code and fec_state == state_code)
        r["_city_match"] = (city and fec_city == city.lower().strip())

        filtered.append(r)

    # If we have state matches and non-state matches, prefer state matches
    # for common names (>10 results)
    if len(filtered) > 10 and state_code:
        state_matches = [r for r in filtered if r["_state_match"]]
        if state_matches:
            filtered = state_matches

    return filtered


# ── GPT-5 mini verification ──────────────────────────────────────────

def verify_fec_match(contact: dict, fec_summary: dict, openai_client: OpenAI) -> dict:
    """
    Use GPT-5 mini to verify that FEC donation records belong to the contact.
    Returns verification dict with is_match, confidence, reasoning.
    """
    # Build contact profile
    profile_parts = [
        f"Name: {contact.get('first_name', '')} {contact.get('last_name', '')}",
        f"City: {contact.get('city', 'Unknown')}",
        f"State: {contact.get('state', 'Unknown')}",
        f"Current Company: {contact.get('company', 'Unknown')}",
        f"Current Position: {contact.get('position', 'Unknown')}",
        f"Headline: {contact.get('headline', 'Unknown')}",
    ]

    employment = contact.get("enrich_employment")
    if employment and isinstance(employment, list):
        jobs = []
        for emp in employment[:5]:
            if isinstance(emp, dict):
                co = emp.get("company_name", "") or emp.get("companyName", "")
                title = emp.get("job_title", "") or emp.get("title", "")
                loc = emp.get("location", "") or emp.get("company_location", "")
                if co:
                    jobs.append(f"  - {title} at {co} ({loc})" if loc else f"  - {title} at {co}")
        if jobs:
            profile_parts.append("Employment history:\n" + "\n".join(jobs))

    # Build FEC summary for GPT
    fec_parts = [
        f"Total: ${fec_summary.get('total_amount', 0):,.2f} across {fec_summary.get('donation_count', 0)} donations",
        f"Largest single: ${fec_summary.get('max_single', 0):,.2f}",
        f"Cycles: {', '.join(fec_summary.get('cycles', []))}",
        f"Employer from FEC: {fec_summary.get('employer_from_fec', 'N/A')}",
        f"Occupation from FEC: {fec_summary.get('occupation_from_fec', 'N/A')}",
    ]

    # Add unique contributor states and cities from recent donations
    recent = fec_summary.get("recent_donations", [])
    if recent:
        committees = [f"  - {d['committee']}: ${d['amount']:,.0f} ({d['date']})" for d in recent[:5]]
        fec_parts.append("Recent donations:\n" + "\n".join(committees))

    # Include raw contributor locations if available
    fec_parts.append(f"Contributor states in data: {fec_summary.get('_contributor_states', 'N/A')}")
    fec_parts.append(f"Contributor cities in data: {fec_summary.get('_contributor_cities', 'N/A')}")

    prompt = f"""You are verifying whether FEC (Federal Election Commission) political donation records belong to a specific LinkedIn contact, or to a different person with the same name.

LINKEDIN CONTACT PROFILE:
{chr(10).join(profile_parts)}

FEC DONATION RECORDS:
{chr(10).join(fec_parts)}

Determine if these FEC records are from the SAME PERSON as the LinkedIn contact. Consider:
1. Employer match: Does the FEC employer/occupation match ANY of the contact's current or past employers?
2. Location match: Is the FEC contributor in the same state or metro area as the contact?
3. Plausibility: Does the donation pattern make sense for this person's career level?
4. Red flags: Different employer AND different state = almost certainly a different person.

Common false positive patterns to watch for:
- FEC records from a different state with a completely unrelated employer
- "NOT EMPLOYED" or "RETIRED" in FEC when the contact is actively working at a specific company
- Very common names (Chris, David, Michael, etc.) with no employer/location overlap

Respond in JSON:
{{
  "is_match": true or false,
  "confidence": "high" | "medium" | "low",
  "reasoning": "1-2 sentence explanation citing specific evidence"
}}"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"is_match": False, "confidence": "error", "reasoning": f"GPT error: {e}"}


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

    # Collect unique contributor states and cities for GPT verification
    contributor_states = sorted(set(
        (r.get("contributor_state") or "").upper()
        for r in results if r.get("contributor_state")
    ))
    contributor_cities = sorted(set(
        (r.get("contributor_city") or "").title()
        for r in results if r.get("contributor_city")
    ))[:10]  # Cap at 10

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
        "_contributor_states": ", ".join(contributor_states),
        "_contributor_cities": ", ".join(contributor_cities),
    }


# ── Main Enrichment ──────────────────────────────────────────────────

class FECEnricher:
    def __init__(self, test_mode=False, batch_size=None, start_from=0, workers=4):
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.start_from = start_from
        self.workers = workers
        self.rate_limiter = RateLimiter(TARGET_REQUESTS_PER_HOUR)
        self.supabase: Client = None
        self.openai_client: OpenAI = None
        self.api_key: str = ""
        self.stats = {
            "processed": 0,
            "found": 0,
            "verified": 0,
            "rejected_by_gpt": 0,
            "no_results": 0,
            "errors": 0,
            "skipped": 0,
            "api_calls": 0,
        }

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        self.api_key = os.environ.get("OPENFEC_API_KEY", "")
        openai_key = os.environ.get("OPENAI_APIKEY", "")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        if not self.api_key:
            print("ERROR: Missing OPENFEC_API_KEY")
            return False
        if not openai_key:
            print("ERROR: Missing OPENAI_APIKEY (needed for GPT verification)")
            return False

        self.supabase = create_client(url, key)
        self.openai_client = OpenAI(api_key=openai_key)
        print("Connected to Supabase + OpenFEC + OpenAI")
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
        """Query FEC for a single contact, verify with GPT, and store results."""
        cid = contact["id"]
        first = contact.get("first_name", "").strip()
        last = contact.get("last_name", "").strip()
        city = contact.get("city")
        state = contact.get("state")
        name = f"{first} {last}"

        if not first or not last:
            self.stats["skipped"] += 1
            return False

        # FEC is US-only — skip non-US contacts
        country = (contact.get("country") or "").strip().lower()
        if country and country not in US_COUNTRY_VALUES:
            self.stats["skipped"] += 1
            skipped_fec = {
                "total_amount": 0, "donation_count": 0, "max_single": 0,
                "cycles": [], "recent_donations": [],
                "employer_from_fec": None, "occupation_from_fec": None,
                "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "skipped_reason": "non_us_contact",
            }
            try:
                self.supabase.table("contacts").update(
                    {"fec_donations": skipped_fec}
                ).eq("id", cid).execute()
            except Exception:
                pass
            return False

        # Try to extract state from employment if missing
        if not state:
            state = extract_state_from_employment(contact)

        # Rate limit then query FEC
        self.rate_limiter.acquire()
        self.stats["api_calls"] += 1
        raw_results = query_fec(self.api_key, first, last, state, city)

        # Disambiguate (strict exact name matching)
        filtered = disambiguate_results(raw_results, first, last, city, state)

        # Build summary
        summary = build_fec_summary(filtered)

        # GPT verification if we found donations
        verification = None
        if summary["donation_count"] > 0:
            verification = verify_fec_match(contact, summary, self.openai_client)

            if not verification.get("is_match", False):
                # GPT says these records don't belong to this person
                self.stats["rejected_by_gpt"] += 1
                summary = build_fec_summary([])  # Clear the donations
                summary["verification"] = verification
                summary["_raw_count_before_verification"] = len(filtered)
            else:
                self.stats["verified"] += 1
                summary["verification"] = verification

        # Clean up internal fields before saving
        summary.pop("_contributor_states", None)
        summary.pop("_contributor_cities", None)

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
            conf = verification.get("confidence", "?") if verification else "?"
            print(f"  [{cid}] {name}: ${summary['total_amount']:,.0f} across "
                  f"{summary['donation_count']} donations "
                  f"(max ${summary['max_single']:,.0f}, "
                  f"verified={conf})")
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
        print(f"    Rate limit: {TARGET_REQUESTS_PER_HOUR}/hr with {self.workers} concurrent workers")
        print(f"    GPT-5 mini verification: ENABLED")
        print()

        # Concurrent processing with thread-safe rate limiter
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {}
            for contact in contacts:
                future = executor.submit(self.process_contact, contact)
                futures[future] = contact["id"]

            done_count = 0
            for future in as_completed(futures):
                done_count += 1
                try:
                    future.result()
                except Exception as e:
                    cid = futures[future]
                    print(f"  [ERROR] Contact {cid}: {e}")
                    self.stats["errors"] += 1

                if done_count % 50 == 0 or done_count == total:
                    elapsed = time.time() - start_time
                    rate = done_count / elapsed * 3600 if elapsed > 0 else 0
                    s = self.stats
                    print(f"\n--- Progress: {done_count}/{total} "
                          f"(found={s['found']}, verified={s['verified']}, "
                          f"gpt_rejected={s['rejected_by_gpt']}, "
                          f"no_results={s['no_results']}, "
                          f"errors={s['errors']}) "
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
        print(f"  With FEC records:   {s['found']} (GPT-verified)")
        print(f"  GPT rejected:       {s['rejected_by_gpt']} (wrong person)")
        print(f"  No FEC records:     {s['no_results']}")
        print(f"  Skipped (non-US):   {s['skipped']}")
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
                        help="Number of concurrent workers (default: 4, rate-limited to 950/hr)")
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
