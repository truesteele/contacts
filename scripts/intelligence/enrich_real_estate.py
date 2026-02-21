#!/usr/bin/env python3
"""
Network Intelligence — Real Estate Holdings Enrichment (Three-Step Pipeline)

Validated pipeline to get real estate data for top contacts:
  Step 1: Apify one-api/skip-trace — name + city/state → home address ($0.007/result)
  Step 2: Zillow autocomplete API — address → ZPID (free)
  Step 3: Apify happitap/zillow-detail-scraper — ZPID → Zestimate + property data (~$0.003)
  Validation: GPT-5 mini verifies each skip-trace result matches the correct person

Stores results in contacts.real_estate_data JSONB column.

Usage:
  python scripts/intelligence/enrich_real_estate.py --test           # 1 contact
  python scripts/intelligence/enrich_real_estate.py --batch 50       # 50 contacts
  python scripts/intelligence/enrich_real_estate.py --start-from 100 # Skip first 100
  python scripts/intelligence/enrich_real_estate.py                  # All eligible contacts
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────

SKIP_TRACE_BATCH_SIZE = 25   # Names per Apify skip-trace run
ZILLOW_DETAIL_BATCH_SIZE = 25  # URLs per Apify Zillow detail run
APIFY_WAIT_TIMEOUT = 300     # Seconds to wait for Apify run
APIFY_POLL_INTERVAL = 5      # Seconds between poll checks
APIFY_POLL_MAX = 60          # Max poll iterations

SELECT_COLS = (
    "id, first_name, last_name, city, state, company, position, "
    "headline, linkedin_url, familiarity_rating, ai_capacity_tier, "
    "enrich_employment, enrich_education, real_estate_data"
)


# ── Step 1: Skip Trace (Name → Address) ──────────────────────────────

def skip_trace_batch(contacts: list[dict], apify_key: str) -> list[dict]:
    """Run Apify skip-trace for a batch of contacts.

    Input: {"name": ["FirstName LastName; City, ST", ...]}
    Returns list of results from Apify dataset.
    """
    names = []
    for c in contacts:
        city = c.get("city", "")
        state = c.get("state", "")
        name = f"{c['first_name']} {c['last_name']}"
        if city and state:
            names.append(f"{name}; {city}, {state}")
        elif state:
            names.append(f"{name}; {state}")
        else:
            names.append(name)

    url = "https://api.apify.com/v2/acts/one-api~skip-trace/runs"
    params = {"token": apify_key, "waitForFinish": APIFY_WAIT_TIMEOUT}
    body = {"name": names}

    resp = requests.post(url, json=body, params=params, timeout=APIFY_WAIT_TIMEOUT + 60)
    if resp.status_code != 201:
        print(f"    ERROR starting skip-trace: {resp.status_code} {resp.text[:300]}")
        return []

    run = resp.json().get("data", {})
    status = run.get("status")
    run_id = run.get("id")
    dsid = run.get("defaultDatasetId", "")

    # Poll if not finished
    if status not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
        for _ in range(APIFY_POLL_MAX):
            time.sleep(APIFY_POLL_INTERVAL)
            sr = requests.get(
                f"https://api.apify.com/v2/actor-runs/{run_id}",
                params={"token": apify_key}, timeout=15
            ).json().get("data", {})
            status = sr.get("status")
            dsid = sr.get("defaultDatasetId", dsid)
            if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break

    if status != "SUCCEEDED":
        print(f"    Skip-trace run {status}")
        return []

    items = requests.get(
        f"https://api.apify.com/v2/datasets/{dsid}/items",
        params={"token": apify_key}, timeout=30
    ).json()

    return items


# ── Step 2: Zillow Autocomplete (Address → ZPID) ────────────────────

def get_zillow_zpid(address: str) -> dict | None:
    """Look up a Zillow ZPID via the autocomplete API (free, no key)."""
    url = "https://www.zillowstatic.com/autocomplete/v3/suggestions"
    params = {"q": address, "resultTypes": "allAddress", "resultCount": 3}

    try:
        resp = requests.get(url, params=params, timeout=10)
        results = resp.json().get("results", [])
        if results:
            top = results[0]
            zpid = top.get("metaData", {}).get("zpid")
            display = top.get("display", "")
            if zpid:
                return {"zpid": zpid, "display": display}
    except Exception as e:
        print(f"    Zillow autocomplete error: {e}")

    return None


# ── Step 3: Zillow Detail Scraper (ZPID → Zestimate) ────────────────

def get_zillow_details_batch(zpid_items: list[dict], apify_key: str) -> list[dict]:
    """Run Apify happitap/zillow-detail-scraper for a batch of ZPIDs.

    zpid_items: list of {"zpid": str, "display": str}
    Returns list of Zillow detail results.
    """
    if not zpid_items:
        return []

    urls = []
    for r in zpid_items:
        display = r["display"].replace(" ", "-").replace(",", "").replace(".", "")
        url = f"https://www.zillow.com/homedetails/{display}/{r['zpid']}_zpid/"
        urls.append({"url": url})

    resp = requests.post(
        "https://api.apify.com/v2/acts/happitap~zillow-detail-scraper/runs",
        json={"startUrls": urls},
        params={"token": apify_key, "waitForFinish": APIFY_WAIT_TIMEOUT},
        timeout=APIFY_WAIT_TIMEOUT + 60,
    )

    if resp.status_code != 201:
        print(f"    ERROR starting Zillow scraper: {resp.status_code} {resp.text[:300]}")
        return []

    run = resp.json().get("data", {})
    status = run.get("status")
    run_id = run.get("id")
    dsid = run.get("defaultDatasetId", "")

    if status not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
        for _ in range(APIFY_POLL_MAX):
            time.sleep(APIFY_POLL_INTERVAL)
            sr = requests.get(
                f"https://api.apify.com/v2/actor-runs/{run_id}",
                params={"token": apify_key}, timeout=15
            ).json().get("data", {})
            status = sr.get("status")
            dsid = sr.get("defaultDatasetId", dsid)
            if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break

    if status != "SUCCEEDED":
        print(f"    Zillow scraper run {status}")
        return []

    items = requests.get(
        f"https://api.apify.com/v2/datasets/{dsid}/items",
        params={"token": apify_key}, timeout=30
    ).json()

    return items


# ── GPT-5 mini Address Validation ────────────────────────────────────

def validate_address_match(contact: dict, skip_trace_result: dict,
                           openai_client: OpenAI) -> dict:
    """Use GPT-5 mini to verify the skip-trace address belongs to the right person."""
    contact_profile = (
        f"Name: {contact['first_name']} {contact['last_name']}\n"
        f"Known City: {contact.get('city', 'Unknown')}, State: {contact.get('state', 'Unknown')}\n"
        f"Current Position: {contact.get('position', 'Unknown')} at {contact.get('company', 'Unknown')}\n"
        f"LinkedIn: {contact.get('linkedin_url', 'Unknown')}\n"
    )

    employment = contact.get("enrich_employment")
    if employment and isinstance(employment, list):
        jobs = []
        for emp in employment[:5]:
            if isinstance(emp, dict):
                co = emp.get("companyName", "")
                title = emp.get("title", "")
                jobs.append(f"  - {title} at {co}")
        if jobs:
            contact_profile += "Employment History:\n" + "\n".join(jobs) + "\n"

    education = contact.get("enrich_education")
    if education and isinstance(education, list):
        schools = []
        for edu in education[:3]:
            if isinstance(edu, dict):
                school = edu.get("schoolName", "")
                degree = edu.get("degreeName", "")
                schools.append(f"  - {degree} from {school}")
        if schools:
            contact_profile += "Education:\n" + "\n".join(schools) + "\n"

    st = skip_trace_result
    skip_trace_info = (
        f"Name returned: {st.get('First Name', '')} {st.get('Last Name', '')}\n"
        f"Address: {st.get('Street Address', '')}, {st.get('Address Locality', '')}, "
        f"{st.get('Address Region', '')} {st.get('Postal Code', '')}\n"
        f"Age: {st.get('Age', 'Unknown')}, Born: {st.get('Born', 'Unknown')}\n"
        f"County: {st.get('County Name', 'Unknown')}\n"
    )

    prev = st.get("Previous Addresses", [])
    if prev and isinstance(prev, list):
        skip_trace_info += "Previous Addresses:\n"
        for addr in prev[:3]:
            if isinstance(addr, dict):
                skip_trace_info += (
                    f"  - {addr.get('streetAddress', '')}, {addr.get('addressLocality', '')}, "
                    f"{addr.get('addressRegion', '')} {addr.get('postalCode', '')}\n"
                )

    prompt = f"""You are verifying whether a skip-trace result matches a specific person from our contacts database.

CONTACT PROFILE (what we know):
{contact_profile}

SKIP-TRACE RESULT (what the people-search returned):
{skip_trace_info}

Determine:
1. Is this the SAME PERSON as our contact? Consider:
   - Does the name match exactly?
   - Is the address location consistent with the known city/state? (Note: people may live in nearby suburbs)
   - Does the age/birth year seem plausible for their career stage?
   - Any red flags (completely different state, name spelling differences)?

2. Confidence level

Respond in JSON:
{{
  "is_match": true/false/null,
  "confidence": "high"/"medium"/"low",
  "reasoning": "1-2 sentence explanation",
  "location_consistent": true/false,
  "name_match_quality": "exact"/"close"/"different"
}}"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": str(e), "is_match": None, "confidence": "error"}


# ── Main Enrichment ──────────────────────────────────────────────────

class RealEstateEnricher:
    def __init__(self, test_mode=False, batch_size=None, start_from=0):
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.start_from = start_from
        self.supabase: Client = None
        self.apify_key: str = ""
        self.openai_client: OpenAI = None
        self.stats = {
            "processed": 0,
            "addresses_found": 0,
            "validated": 0,
            "rejected": 0,
            "zpids_found": 0,
            "zestimates_found": 0,
            "no_address": 0,
            "errors": 0,
            "skipped_no_location": 0,
        }

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        self.apify_key = os.environ.get("APIFY_API_KEY", "")
        openai_key = os.environ.get("OPENAI_APIKEY", "")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        if not self.apify_key:
            print("ERROR: Missing APIFY_API_KEY")
            return False
        if not openai_key:
            print("ERROR: Missing OPENAI_APIKEY")
            return False

        self.supabase = create_client(url, key)
        self.openai_client = OpenAI(api_key=openai_key)
        print("Connected to Supabase + Apify + OpenAI")
        return True

    def get_contacts(self) -> list[dict]:
        """Fetch eligible contacts: familiarity >= 2 OR ai_capacity_tier = 'major_donor',
        excluding those already enriched."""
        all_contacts = []
        page_size = 1000
        offset = 0

        # Fetch contacts with familiarity >= 2
        while True:
            page = (
                self.supabase.table("contacts")
                .select(SELECT_COLS)
                .is_("real_estate_data", "null")
                .gte("familiarity_rating", 2)
                .order("familiarity_rating", desc=True)
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

        fam_ids = {c["id"] for c in all_contacts}

        # Also fetch major_donor tier contacts not already included
        offset = 0
        while True:
            page = (
                self.supabase.table("contacts")
                .select(SELECT_COLS)
                .is_("real_estate_data", "null")
                .eq("ai_capacity_tier", "major_donor")
                .order("id")
                .range(offset, offset + page_size - 1)
                .execute()
            ).data

            if not page:
                break
            for c in page:
                if c["id"] not in fam_ids:
                    all_contacts.append(c)
                    fam_ids.add(c["id"])
            if len(page) < page_size:
                break
            offset += page_size

        # Sort by familiarity desc for priority processing
        all_contacts.sort(
            key=lambda c: (c.get("familiarity_rating") or 0), reverse=True
        )

        # Apply start-from offset
        if self.start_from > 0:
            all_contacts = all_contacts[self.start_from:]

        # Apply batch/test limits
        if self.test_mode:
            all_contacts = all_contacts[:1]
        elif self.batch_size:
            all_contacts = all_contacts[:self.batch_size]

        return all_contacts

    def process_batch(self, contacts: list[dict]):
        """Process a batch of contacts through the full pipeline."""
        batch_size = len(contacts)
        print(f"\n  [Step 1] Skip-tracing {batch_size} contacts...")

        # Step 1: Batch skip-trace
        skip_results = skip_trace_batch(contacts, self.apify_key)

        if not skip_results:
            print(f"    FAILED: No skip-trace results for batch")
            self.stats["errors"] += batch_size
            return

        # Build lookup by input name
        results_by_input = {}
        for sr in skip_results:
            input_given = sr.get("Input Given", "")
            results_by_input[input_given] = sr

        # Step 2: Validate each result and collect ZPIDs
        zpid_items = []  # {"zpid", "display", "contact_idx", "address"}
        contact_results = {}  # contact_idx → partial result dict

        for idx, c in enumerate(contacts):
            name = f"{c['first_name']} {c['last_name']}"
            city = c.get("city", "")
            state = c.get("state", "")
            cid = c["id"]

            # Find matching skip-trace result
            key1 = f"{name}; {city}, {state}"
            key2 = f"{name}; {state}"
            key3 = name
            sr = results_by_input.get(key1) or results_by_input.get(key2) or results_by_input.get(key3)

            if not sr or not sr.get("Street Address"):
                self.stats["no_address"] += 1
                self.stats["processed"] += 1
                # Store a "no_result" marker so we don't re-process
                self._save_no_result(cid)
                continue

            self.stats["addresses_found"] += 1

            street = sr.get("Street Address", "")
            locality = sr.get("Address Locality", "")
            region = sr.get("Address Region", "")
            postal = sr.get("Postal Code", "")
            full_address = f"{street}, {locality}, {region} {postal}"

            # Validate with GPT-5 mini
            validation = validate_address_match(c, sr, self.openai_client)
            is_match = validation.get("is_match")
            confidence = validation.get("confidence", "?")

            match_symbol = "+" if is_match else "X" if is_match is False else "?"
            print(f"    [{match_symbol}] {name}: {full_address} "
                  f"(match={is_match}, conf={confidence})")

            if not is_match:
                self.stats["rejected"] += 1
                self.stats["processed"] += 1
                # Store rejected result with confidence info
                self._save_rejected(cid, full_address, validation)
                continue

            self.stats["validated"] += 1

            # Step 2: Zillow autocomplete
            zpid_info = get_zillow_zpid(full_address)
            if zpid_info:
                self.stats["zpids_found"] += 1
                zpid_items.append({
                    "zpid": zpid_info["zpid"],
                    "display": zpid_info["display"],
                    "contact_idx": idx,
                    "address": full_address,
                })
                contact_results[idx] = {"address": full_address}
            else:
                # Save with address but no Zestimate
                self.stats["processed"] += 1
                self._save_address_only(cid, full_address, validation)

        # Step 3: Batch Zillow detail lookup
        if zpid_items:
            print(f"\n  [Step 3] Fetching Zillow details for {len(zpid_items)} properties...")
            zillow_results = get_zillow_details_batch(zpid_items, self.apify_key)

            # Match results back to contacts
            for j, zr in enumerate(zillow_results):
                if j >= len(zpid_items):
                    break

                zpid_item = zpid_items[j]
                contact_idx = zpid_item["contact_idx"]
                c = contacts[contact_idx]
                cid = c["id"]
                name = f"{c['first_name']} {c['last_name']}"
                address = zpid_item["address"]

                z = zr.get("zestimate")
                rz = zr.get("rentZestimate")
                beds = zr.get("bedrooms")
                baths = zr.get("bathrooms")
                sqft = zr.get("livingArea")
                year = zr.get("yearBuilt")
                home_type = zr.get("homeType")

                if z:
                    self.stats["zestimates_found"] += 1
                    z_str = f"${z:,}" if isinstance(z, (int, float)) else str(z)
                    print(f"    ${name}: Zestimate = {z_str} "
                          f"({beds or '?'}bd/{baths or '?'}ba, {sqft or '?'} sqft)")

                real_estate_data = {
                    "address": address,
                    "zestimate": z,
                    "rent_zestimate": rz,
                    "beds": beds,
                    "baths": baths,
                    "sqft": sqft,
                    "year_built": year,
                    "property_type": home_type,
                    "confidence": "high",
                    "source": "zillow_via_skip_trace",
                    "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                }

                try:
                    self.supabase.table("contacts").update({
                        "real_estate_data": real_estate_data,
                    }).eq("id", cid).execute()
                    self.stats["processed"] += 1
                except Exception as e:
                    print(f"    ERROR saving {name}: {e}")
                    self.stats["errors"] += 1

            # Handle ZPID contacts that didn't get Zillow results back
            # (Zillow scraper sometimes returns fewer results than URLs sent)
            for zpid_item in zpid_items[len(zillow_results):]:
                contact_idx = zpid_item["contact_idx"]
                c = contacts[contact_idx]
                self._save_address_only(c["id"], zpid_item["address"], {"confidence": "high"})
                self.stats["processed"] += 1

    def _save_no_result(self, cid: str):
        """Store marker for contacts with no skip-trace result."""
        data = {
            "confidence": "no_result",
            "source": "skip_trace_failed",
            "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        try:
            self.supabase.table("contacts").update({
                "real_estate_data": data,
            }).eq("id", cid).execute()
        except Exception as e:
            print(f"    ERROR saving no_result for {cid}: {e}")
            self.stats["errors"] += 1

    def _save_rejected(self, cid: str, address: str, validation: dict):
        """Store rejected validation result."""
        data = {
            "address": address,
            "confidence": "rejected",
            "rejection_reason": validation.get("reasoning", ""),
            "source": "skip_trace_rejected",
            "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        try:
            self.supabase.table("contacts").update({
                "real_estate_data": data,
            }).eq("id", cid).execute()
        except Exception as e:
            print(f"    ERROR saving rejected for {cid}: {e}")
            self.stats["errors"] += 1

    def _save_address_only(self, cid: str, address: str, validation: dict):
        """Store address without Zillow data (ZPID not found)."""
        data = {
            "address": address,
            "zestimate": None,
            "rent_zestimate": None,
            "confidence": validation.get("confidence", "medium"),
            "source": "skip_trace_only",
            "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        try:
            self.supabase.table("contacts").update({
                "real_estate_data": data,
            }).eq("id", cid).execute()
        except Exception as e:
            print(f"    ERROR saving address_only for {cid}: {e}")
            self.stats["errors"] += 1

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()
        contacts = self.get_contacts()
        total = len(contacts)
        print(f"Found {total} eligible contacts (familiarity >= 2 OR major_donor, no existing data)")

        if total == 0:
            print("Nothing to do — all eligible contacts already have real estate data")
            return True

        mode_str = "TEST" if self.test_mode else f"BATCH {self.batch_size}" if self.batch_size else "FULL"
        print(f"\n--- {mode_str} MODE: Processing {total} contacts ---")
        print(f"    Skip-trace batch size: {SKIP_TRACE_BATCH_SIZE}")
        print(f"    Zillow detail batch size: {ZILLOW_DETAIL_BATCH_SIZE}")
        est_cost = total * 0.007 + total * 0.5 * 0.003 + total * 0.87 * 0.002
        print(f"    Estimated cost: ~${est_cost:.2f}")
        print()

        # Process in batches
        for batch_start in range(0, total, SKIP_TRACE_BATCH_SIZE):
            batch_end = min(batch_start + SKIP_TRACE_BATCH_SIZE, total)
            batch = contacts[batch_start:batch_end]

            print(f"\n{'─' * 60}")
            print(f"  Batch {batch_start // SKIP_TRACE_BATCH_SIZE + 1}: "
                  f"contacts {batch_start + 1}-{batch_end} of {total}")
            print(f"{'─' * 60}")

            self.process_batch(batch)

            # Progress summary
            s = self.stats
            elapsed = time.time() - start_time
            print(f"\n  Progress: {s['processed']}/{total} processed, "
                  f"{s['validated']} validated, {s['zestimates_found']} zestimates, "
                  f"{s['errors']} errors [{elapsed:.0f}s elapsed]")

        elapsed = time.time() - start_time
        self.print_summary(elapsed, total)
        return self.stats["errors"] < total * 0.1

    def print_summary(self, elapsed: float, total: int):
        s = self.stats
        print("\n" + "=" * 60)
        print("REAL ESTATE ENRICHMENT SUMMARY")
        print("=" * 60)
        print(f"  Contacts processed:  {s['processed']}")
        print(f"  Addresses found:     {s['addresses_found']}/{total} "
              f"({s['addresses_found'] / max(total, 1) * 100:.0f}%)")
        print(f"  Validated matches:   {s['validated']}/{s['addresses_found']} "
              f"({s['validated'] / max(s['addresses_found'], 1) * 100:.0f}%)")
        print(f"  Rejected (wrong):    {s['rejected']}")
        print(f"  No address found:    {s['no_address']}")
        print(f"  ZPIDs found:         {s['zpids_found']}/{s['validated']} "
              f"({s['zpids_found'] / max(s['validated'], 1) * 100:.0f}%)")
        print(f"  Zestimates obtained: {s['zestimates_found']}/{s['zpids_found']} "
              f"({s['zestimates_found'] / max(s['zpids_found'], 1) * 100:.0f}%)")
        print(f"  Skipped (no loc):    {s['skipped_no_location']}")
        print(f"  Errors:              {s['errors']}")
        print(f"  Time elapsed:        {elapsed:.1f}s")
        print()
        skip_cost = total * 0.007
        zillow_cost = s['zpids_found'] * 0.003
        gpt_cost = s['addresses_found'] * 0.002
        total_cost = skip_cost + zillow_cost + gpt_cost
        print(f"  Cost estimate:")
        print(f"    Skip-trace:      {total} x $0.007 = ${skip_cost:.2f}")
        print(f"    Zillow detail:   {s['zpids_found']} x $0.003 = ${zillow_cost:.3f}")
        print(f"    GPT-5 mini:      {s['addresses_found']} x ~$0.002 = ${gpt_cost:.3f}")
        print(f"    Total:           ${total_cost:.2f}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Enrich contacts with real estate data via skip-trace + Zillow pipeline"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only 1 contact for validation")
    parser.add_argument("--batch", "-b", type=int, default=None,
                        help="Process N contacts")
    parser.add_argument("--start-from", "-s", type=int, default=0,
                        help="Skip first N contacts (for resuming)")
    args = parser.parse_args()

    enricher = RealEstateEnricher(
        test_mode=args.test,
        batch_size=args.batch,
        start_from=args.start_from,
    )
    success = enricher.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
