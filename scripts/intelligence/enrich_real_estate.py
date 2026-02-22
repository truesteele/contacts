#!/usr/bin/env python3
"""
Network Intelligence — Real Estate Holdings Enrichment (Three-Step Pipeline)

Validated pipeline to get real estate data for top contacts:
  Step 1a: Apify one-api/skip-trace — name + city/state → home address ($0.007/result)
  Step 1b: 411.com scraper — name + city/state → multiple candidates (FREE)
  Step 2: Zillow autocomplete API — address → ZPID (free)
  Step 3: Apify maxcopell/zillow-detail-scraper — ZPID → Zestimate + property data (~$0.003)
  Validation: GPT-5 mini verifies each result matches the correct person

Stores results in contacts.real_estate_data JSONB column.

Usage:
  python scripts/intelligence/enrich_real_estate.py --test                    # 1 contact (Apify)
  python scripts/intelligence/enrich_real_estate.py --source 411 --batch 50   # 50 contacts (411.com)
  python scripts/intelligence/enrich_real_estate.py --source 411 --retry-rejected  # Re-try rejected
  python scripts/intelligence/enrich_real_estate.py --start-from 100          # Skip first 100
  python scripts/intelligence/enrich_real_estate.py                           # All eligible contacts
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
from openai import OpenAI

load_dotenv()

from people_search_scraper import Scraper411, validate_candidates, normalize_state, clean_name

# ── Config ────────────────────────────────────────────────────────────

SKIP_TRACE_BATCH_SIZE = 25   # Names per Apify skip-trace run
ZILLOW_DETAIL_BATCH_SIZE = 25  # URLs per Apify Zillow detail run
APIFY_WAIT_TIMEOUT = 300     # Seconds to wait for Apify run
APIFY_POLL_INTERVAL = 5      # Seconds between poll checks
APIFY_POLL_MAX = 60          # Max poll iterations

SELECT_COLS = (
    "id, first_name, last_name, city, state, country, location_name, "
    "company, position, headline, linkedin_url, familiarity_rating, "
    "ai_capacity_tier, enrich_employment, enrich_education, real_estate_data"
)


def backfill_location(contact: dict, openai_client: OpenAI) -> dict:
    """If city/state are null, use GPT-5 mini to extract them from LinkedIn data.

    Uses location_name and enrich_employment to determine the best US city/state.
    Returns the contact dict with city/state populated if possible.
    Sets contact['_no_us_location'] = True if no US location can be determined.
    """
    if contact.get("city") and contact.get("state"):
        return contact

    loc = (contact.get("location_name") or "").strip()
    employment = contact.get("enrich_employment")

    # Build context for GPT
    parts = []
    if loc:
        parts.append(f"LinkedIn Location: {loc}")
    if employment and isinstance(employment, list):
        for emp in employment[:3]:
            if isinstance(emp, dict):
                co = emp.get("company_name", "") or emp.get("companyName", "")
                loc_emp = emp.get("location", "")
                current = emp.get("is_current", False)
                if co or loc_emp:
                    prefix = "[CURRENT] " if current else ""
                    parts.append(f"{prefix}{co}: {loc_emp}")

    if not parts:
        contact["_no_us_location"] = True
        return contact

    profile = "\n".join(parts)
    prompt = f"""Extract the US city and state for this person's current residence from their LinkedIn data.

{profile}

Return JSON:
{{
  "city": "city name or null if unknown",
  "state": "2-letter US state code or null if unknown",
  "is_us_based": true/false,
  "reasoning": "brief explanation"
}}

Rules:
- Convert metro areas to real cities: "San Francisco Bay Area" → city "San Francisco", state "CA"
- Convert "Greater Boston" → "Boston", "MA", etc.
- Use the most recent/current employment location if the LinkedIn location is vague (just "United States")
- If the person is clearly non-US (location is in another country, no US employment), set is_us_based to false
- "District of Columbia" → state "DC"
- If you can determine the state but not the specific city, set city to null but still return the state"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)

        if not result.get("is_us_based"):
            contact["_no_us_location"] = True
            return contact

        if result.get("state"):
            contact["state"] = result["state"]
        if result.get("city"):
            contact["city"] = result["city"]

        if not result.get("state"):
            contact["_no_us_location"] = True

        return contact
    except Exception as e:
        print(f"    GPT backfill error for {contact.get('first_name')} {contact.get('last_name')}: {e}")
        contact["_no_us_location"] = True
        return contact


# ── Step 1: Skip Trace (Name → Address) ──────────────────────────────

def skip_trace_batch(contacts: list[dict], apify_key: str) -> list[dict]:
    """Run Apify skip-trace for a batch of contacts.

    IMPORTANT: Contacts must have city/state populated before calling this.
    Use backfill_location() with GPT-5 mini first to extract from LinkedIn data.
    Contacts with no city/state are skipped (name-only matches are unreliable).

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
            # No location — skip (name-only matches are unreliable)
            print(f"    SKIP {name}: no city/state — name-only skip-trace too unreliable")
            names.append(None)  # placeholder to keep index alignment

    # Filter out contacts with no location (None placeholders)
    valid_names = [n for n in names if n is not None]
    if not valid_names:
        print("    No contacts with location data in this batch")
        return []

    url = "https://api.apify.com/v2/acts/one-api~skip-trace/runs"
    params = {"token": apify_key, "waitForFinish": APIFY_WAIT_TIMEOUT}
    body = {"name": valid_names}

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


# ── Step 1b: 411.com Scraper (Name → Multiple Candidates → Best Match) ──

N_411_WORKERS = 10  # Concurrent 411.com search workers (each has own session)
N_GPT_WORKERS = 150 # Concurrent GPT calls (Tier 5: 10,000 RPM)


def _search_and_validate_one(
    idx: int,
    contact: dict,
    params: dict,
    openai_client: OpenAI,
) -> tuple:
    """Search 411.com and validate for one contact. Thread-safe.

    Each call creates its own Scraper411 (own session/TLS fingerprint).
    Returns (idx, params, candidates, validation, stats).
    """
    fname = params["first_name"]
    lname = params["last_name"]
    city = params.get("city", "")
    state = params.get("state", "")
    name = f"{fname} {lname}"

    scraper = Scraper411()
    candidates = scraper.search_and_enrich(
        fname, lname, city, state,
        max_results=5,
        enrich_top_n=3,
    )

    validation = None
    if candidates:
        validation = validate_candidates(contact, candidates, openai_client)

    return idx, params, candidates, validation, scraper.stats


def skip_trace_411(contacts: list[dict], openai_client: OpenAI) -> list[dict]:
    """Use 411.com scraper + GPT-5 mini multi-candidate validation.

    Fully concurrent pipeline:
    1. GPT-5 mini prepares clean search params (N_GPT_WORKERS concurrent)
    2. 411.com search + GPT validate (N_411_WORKERS concurrent — each worker
       creates its own Scraper411 with unique session/TLS fingerprint)

    Returns list of dicts in the same format as skip_trace_batch() for
    drop-in compatibility with the rest of the pipeline.
    """
    results = [None] * len(contacts)

    # ── Step 0: GPT prep (high concurrency) ──────────────────────────
    print(f"    Preparing search params via GPT-5 mini ({len(contacts)} contacts)...")
    prepared = {}
    with ThreadPoolExecutor(max_workers=N_GPT_WORKERS) as executor:
        futures = {
            executor.submit(prepare_search_params, c, openai_client): i
            for i, c in enumerate(contacts)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                prepared[idx] = future.result()
            except Exception as e:
                print(f"    GPT prep error for contact {idx}: {e}")
                prepared[idx] = None

    # ── Split into searchable / non-searchable ───────────────────────
    searchable = []
    for i, c in enumerate(contacts):
        params = prepared.get(i)
        raw_name = f"{c.get('first_name', '')} {c.get('last_name', '')}"

        if not params or not params.get("is_searchable"):
            reason = (params or {}).get("skip_reason", "gpt_prep_failed")
            print(f"    {raw_name} → Skip: {reason}")
            results[i] = {
                "Input Given": raw_name,
                "_no_result": True,
                "_skip_reason": reason,
            }
            continue

        fname = params["first_name"]
        lname = params["last_name"]
        city = params.get("city", "")
        state = params.get("state", "")

        if not state and not city:
            results[i] = {
                "Input Given": f"{fname} {lname}",
                "_no_result": True,
                "_skip_reason": "no_us_location",
            }
            continue

        searchable.append((i, c, params))

    skipped = len(contacts) - len(searchable)
    print(f"    GPT prep done: {len(searchable)} searchable, {skipped} skipped\n")

    # ── Step 1+2: 411 search + GPT validate (concurrent) ────────────
    if searchable:
        print(f"    Searching 411.com + validating ({len(searchable)} contacts, "
              f"{N_411_WORKERS} concurrent workers)...")

        total_stats = {
            "searches": 0, "detail_fetches": 0,
            "candidates_found": 0, "errors": 0, "rate_limited": 0,
        }
        done_count = 0

        with ThreadPoolExecutor(max_workers=N_411_WORKERS) as executor:
            futures = {
                executor.submit(
                    _search_and_validate_one, idx, contact, params, openai_client
                ): (idx, contact, params)
                for idx, contact, params in searchable
            }

            for future in as_completed(futures):
                done_count += 1
                try:
                    idx, params, candidates, validation, stats = future.result()
                except Exception as e:
                    idx = futures[future][0]
                    print(f"    [{done_count}/{len(searchable)}] Error: {e}")
                    results[idx] = {"Input Given": "error", "_no_result": True}
                    continue

                for k in total_stats:
                    total_stats[k] += stats.get(k, 0)

                fname = params["first_name"]
                lname = params["last_name"]
                city = params.get("city", "")
                state = params.get("state", "")
                name = f"{fname} {lname}"

                if not candidates:
                    print(f"    [{done_count}/{len(searchable)}] {name}: no candidates")
                    results[idx] = {
                        "Input Given": f"{name}; {city}, {state}",
                        "_no_result": True,
                    }
                    continue

                best_idx = (validation or {}).get("best_candidate_index")
                confidence = (validation or {}).get("confidence", "low")

                if best_idx is not None and 0 <= best_idx < len(candidates):
                    best = candidates[best_idx]
                    addr = best.get("Street Address", "?")
                    loc = best.get("Address Locality", "")
                    print(f"    [{done_count}/{len(searchable)}] {name}: "
                          f"✓ #{best_idx + 1} {best.get('name', '?')} — {addr}, {loc} "
                          f"({confidence})")

                    results[idx] = {
                        "Input Given": f"{name}; {city}, {state}",
                        "First Name": best.get("First Name", best.get("first_name", "")),
                        "Last Name": best.get("Last Name", best.get("last_name", "")),
                        "Street Address": best.get("Street Address", ""),
                        "Address Locality": best.get("Address Locality", ""),
                        "Address Region": best.get("Address Region", ""),
                        "Postal Code": best.get("Postal Code", ""),
                        "Age": best.get("Age", best.get("age", "")),
                        "phones": best.get("phones", []),
                        "relatives": best.get("relatives", []),
                        "_validation": validation,
                        "_source": "411.com",
                        "_candidates_count": len(candidates),
                    }
                else:
                    reason = (validation or {}).get("reasoning", "")
                    print(f"    [{done_count}/{len(searchable)}] {name}: "
                          f"✗ rejected all {len(candidates)} ({reason[:80]})")
                    results[idx] = {
                        "Input Given": f"{name}; {city}, {state}",
                        "_rejected_all": True,
                        "_validation": validation,
                        "_candidates_count": len(candidates),
                    }

        print(f"\n    411.com stats: {total_stats}")

    # Fill any remaining None results
    for i in range(len(results)):
        if results[i] is None:
            raw = f"{contacts[i].get('first_name', '')} {contacts[i].get('last_name', '')}"
            results[i] = {"Input Given": raw, "_no_result": True}

    return results


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
    """Run Apify maxcopell/zillow-detail-scraper for a batch of ZPIDs.

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
        "https://api.apify.com/v2/acts/maxcopell~zillow-detail-scraper/runs",
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
        f"LinkedIn Location: {contact.get('location_name', 'Unknown')}\n"
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


# ── Ownership Likelihood Classification ──────────────────────────────

import re

_UNIT_PATTERN = re.compile(r"#|Apt |Unit |Ste |Suite |Floor ", re.IGNORECASE)


def classify_ownership(address: str | None, property_type: str | None,
                       zestimate: float | int | None) -> str:
    """Classify ownership likelihood based on property type, address, and Zestimate.

    Returns one of: likely_owner, likely_owner_condo, likely_renter, uncertain
    """
    has_unit = bool(address and _UNIT_PATTERN.search(address))
    has_zest = zestimate is not None

    if property_type == "APARTMENT":
        return "likely_renter" if not has_zest else "uncertain"
    if property_type == "SINGLE_FAMILY":
        if not has_unit:
            return "likely_owner"
        return "likely_owner_condo" if has_zest else "likely_renter"
    if property_type == "CONDO":
        return "likely_owner_condo" if has_zest else "uncertain"
    if property_type in ("TOWNHOUSE", "MULTI_FAMILY", "MANUFACTURED"):
        return "likely_owner"
    if property_type == "HOME_TYPE_UNKNOWN":
        return "uncertain"
    # property_type is None
    if has_unit and not has_zest:
        return "likely_renter"
    if has_unit and has_zest:
        return "uncertain"
    return "uncertain"


# ── GPT-5 Mini Search Param Preparation ──────────────────────────────

def prepare_search_params(contact: dict, openai_client: OpenAI) -> dict:
    """Use GPT-5 mini to extract clean name and US location for 411.com search.

    Handles: dirty names (credentials, pronouns), missing/metro cities,
    and extracts best US location from employment data when profile city is missing.
    """
    profile_parts = [
        f"First Name field: {contact.get('first_name', '')}",
        f"Last Name field: {contact.get('last_name', '')}",
        f"City field: {contact.get('city', '')}",
        f"State field: {contact.get('state', '')}",
        f"Company: {contact.get('company', '')}",
        f"Position: {contact.get('position', '')}",
        f"Headline: {contact.get('headline', '')}",
    ]

    employment = contact.get("enrich_employment")
    if employment and isinstance(employment, list):
        jobs = []
        for emp in employment[:5]:
            if isinstance(emp, dict):
                co = emp.get("company_name", "") or emp.get("companyName", "")
                title = emp.get("job_title", "") or emp.get("title", "")
                loc = emp.get("location", "")
                if co or title:
                    jobs.append(f"  {title} at {co}" + (f" | {loc}" if loc else ""))
        if jobs:
            profile_parts.append("Recent Employment:\n" + "\n".join(jobs))

    education = contact.get("enrich_education")
    if education and isinstance(education, list):
        schools = []
        for edu in education[:3]:
            if isinstance(edu, dict):
                school = edu.get("school_name", "") or edu.get("schoolName", "")
                loc = edu.get("location", "")
                if school:
                    schools.append(f"  {school}" + (f" | {loc}" if loc else ""))
        if schools:
            profile_parts.append("Education:\n" + "\n".join(schools))

    profile = "\n".join(profile_parts)

    prompt = f"""Extract clean search parameters for a US people-search (411.com) from this contact profile.

PROFILE:
{profile}

Return JSON:
{{
  "first_name": "clean first name only — no middle names, no suffixes, no pronouns",
  "last_name": "clean last name only — no credentials (PhD, MBA, CPA, CFRE, JD, Ed.D., MPA), no pronouns (she/her/ella)",
  "city": "best US city to search — convert metro areas to real city names, use employment location if profile city is missing",
  "state": "2-letter US state code",
  "is_searchable": true or false,
  "skip_reason": null or "brief reason this contact cannot be searched"
}}

Rules:
- Strip ALL credentials, degrees, and parentheticals from names. Examples: "Yusuf, Ed.D., MPA" → "Yusuf". "Khalili (she/her)" → "Khalili". "Zwart (she/her/ella)" → "Zwart"
- Convert metro areas to actual cities: "San Diego Metropolitan Area" → "San Diego". "Greater New York City Area" → "New York". "San Francisco Bay Area" → "San Francisco"
- Convert full state names to 2-letter codes: "California" → "CA". "District of Columbia" → "DC"
- If the profile city/state are missing or empty, use the MOST RECENT current employment location
- If the person appears to be entirely non-US (all jobs international, no US locations ever), set is_searchable to false with skip_reason
- Prefer the primary/legal first name over nicknames"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        # Fallback to regex-based cleaning
        return {
            "first_name": clean_name(contact.get("first_name", "")),
            "last_name": clean_name(contact.get("last_name", "")),
            "city": contact.get("city", "") or "",
            "state": normalize_state(contact.get("state", "") or ""),
            "is_searchable": bool(contact.get("city") or contact.get("state")),
            "skip_reason": f"gpt_error: {e}",
        }


# ── Main Enrichment ──────────────────────────────────────────────────

class RealEstateEnricher:
    def __init__(self, test_mode=False, batch_size=None, start_from=0,
                 source="apify", retry_rejected=False):
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.start_from = start_from
        self.source = source  # "apify" or "411"
        self.retry_rejected = retry_rejected
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
        if self.source == "apify" and not self.apify_key:
            print("ERROR: Missing APIFY_API_KEY (required for apify source)")
            return False
        if not openai_key:
            print("ERROR: Missing OPENAI_APIKEY")
            return False

        self.supabase = create_client(url, key)
        self.openai_client = OpenAI(api_key=openai_key)
        source_str = "411.com" if self.source == "411" else "Apify"
        apify_str = " + Apify" if self.apify_key else ""
        print(f"Connected to Supabase{apify_str} + OpenAI (source: {source_str})")
        return True

    def get_contacts(self) -> list[dict]:
        """Fetch eligible contacts: familiarity >= 2 OR ai_capacity_tier = 'major_donor',
        excluding those already enriched.

        With --retry-rejected: fetch contacts whose real_estate_data has
        confidence='rejected' or confidence='no_result' for re-processing.
        """
        all_contacts = []
        page_size = 1000
        offset = 0

        if self.retry_rejected:
            # Fetch previously rejected/failed contacts for re-processing.
            # Two queries: familiarity >= 2, then major_donor tier (same
            # pattern as the standard path to catch all eligible contacts).
            seen_ids = set()

            # Query 1: familiarity >= 2
            while True:
                page = (
                    self.supabase.table("contacts")
                    .select(SELECT_COLS)
                    .not_.is_("real_estate_data", "null")
                    .gte("familiarity_rating", 2)
                    .order("familiarity_rating", desc=True)
                    .order("id")
                    .range(offset, offset + page_size - 1)
                    .execute()
                ).data

                if not page:
                    break
                for c in page:
                    red = c.get("real_estate_data")
                    if isinstance(red, dict) and red.get("confidence") in (
                        "rejected", "no_result"
                    ):
                        all_contacts.append(c)
                        seen_ids.add(c["id"])
                if len(page) < page_size:
                    break
                offset += page_size

            # Query 2: major_donor tier (may have familiarity < 2)
            offset = 0
            while True:
                page = (
                    self.supabase.table("contacts")
                    .select(SELECT_COLS)
                    .not_.is_("real_estate_data", "null")
                    .eq("ai_capacity_tier", "major_donor")
                    .order("id")
                    .range(offset, offset + page_size - 1)
                    .execute()
                ).data

                if not page:
                    break
                for c in page:
                    if c["id"] not in seen_ids:
                        red = c.get("real_estate_data")
                        if isinstance(red, dict) and red.get("confidence") in (
                            "rejected", "no_result"
                        ):
                            all_contacts.append(c)
                            seen_ids.add(c["id"])
                if len(page) < page_size:
                    break
                offset += page_size

            print(f"Found {len(all_contacts)} previously rejected/failed contacts to retry")
        else:
            # Standard: fetch contacts with no real_estate_data
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

    def _backfill_locations(self, contacts: list[dict]):
        """Use GPT-5 mini to backfill city/state from LinkedIn data for contacts missing them."""
        need_backfill = [c for c in contacts if not (c.get("city") and c.get("state"))]
        if not need_backfill:
            return

        print(f"  [Step 0] Backfilling city/state from LinkedIn for {len(need_backfill)} contacts...")
        with ThreadPoolExecutor(max_workers=min(len(need_backfill), 50)) as executor:
            futures = {
                executor.submit(backfill_location, c, self.openai_client): c
                for c in need_backfill
            }
            filled = 0
            skipped = 0
            for future in as_completed(futures):
                c = futures[future]
                try:
                    future.result()
                except Exception as e:
                    c["_no_us_location"] = True
                if c.get("_no_us_location"):
                    skipped += 1
                elif c.get("city") or c.get("state"):
                    filled += 1
            print(f"    Backfilled {filled} locations, {skipped} skipped (no US location)\n")

    def process_batch(self, contacts: list[dict]):
        """Process a batch of contacts through the full pipeline with concurrent phases."""
        batch_size = len(contacts)

        if self.source == "411":
            return self._process_batch_411(contacts)

        # Step 0: Backfill city/state from LinkedIn data via GPT-5 mini
        self._backfill_locations(contacts)

        # Filter out contacts with no US location
        skipped = [c for c in contacts if c.get("_no_us_location")]
        for c in skipped:
            name = f"{c['first_name']} {c['last_name']}"
            print(f"    SKIP {name}: no US location found")
            self._save_no_result(c["id"], skip_reason="no_us_location")
            self.stats["skipped_no_location"] += 1
            self.stats["processed"] += 1

        contacts = [c for c in contacts if not c.get("_no_us_location")]
        if not contacts:
            print("    No contacts with US location in this batch")
            return

        print(f"\n  [Step 1] Skip-tracing {len(contacts)} contacts (Apify)...")

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

        # Match skip-trace results to contacts
        to_validate = []  # (idx, contact, skip_result, full_address)
        for idx, c in enumerate(contacts):
            name = f"{c['first_name']} {c['last_name']}"
            city = c.get("city", "")
            state = c.get("state", "")
            cid = c["id"]

            key1 = f"{name}; {city}, {state}"
            key2 = f"{name}; {state}"
            key3 = name
            sr = results_by_input.get(key1) or results_by_input.get(key2) or results_by_input.get(key3)

            if not sr or not sr.get("Street Address"):
                self.stats["no_address"] += 1
                self.stats["processed"] += 1
                self._save_no_result(cid)
                continue

            self.stats["addresses_found"] += 1
            street = sr.get("Street Address", "")
            locality = sr.get("Address Locality", "")
            region = sr.get("Address Region", "")
            postal = sr.get("Postal Code", "")
            full_address = f"{street}, {locality}, {region} {postal}"
            to_validate.append((idx, c, sr, full_address))

        # Step 2: Validate ALL addresses concurrently with GPT-5 mini
        if not to_validate:
            return

        print(f"  [Step 2] Validating {len(to_validate)} addresses with GPT-5 mini (concurrent)...")
        validated = []  # (idx, contact, full_address, validation)

        with ThreadPoolExecutor(max_workers=min(len(to_validate), 20)) as executor:
            futures = {}
            for idx, c, sr, full_address in to_validate:
                future = executor.submit(validate_address_match, c, sr, self.openai_client)
                futures[future] = (idx, c, sr, full_address)

            for future in as_completed(futures):
                idx, c, sr, full_address = futures[future]
                cid = c["id"]
                name = f"{c['first_name']} {c['last_name']}"

                try:
                    validation = future.result()
                except Exception as e:
                    print(f"    [!] {name}: Validation error: {e}")
                    self.stats["errors"] += 1
                    continue

                is_match = validation.get("is_match")
                confidence = validation.get("confidence", "?")

                match_symbol = "+" if is_match else "X" if is_match is False else "?"
                print(f"    [{match_symbol}] {name}: {full_address} "
                      f"(match={is_match}, conf={confidence})")

                if not is_match:
                    self.stats["rejected"] += 1
                    self.stats["processed"] += 1
                    self._save_rejected(cid, full_address, validation)
                    continue

                self.stats["validated"] += 1
                validated.append((idx, c, full_address, validation))

        # Step 3: Zillow autocomplete ALL concurrently
        if not validated:
            return

        print(f"  [Step 3] Getting ZPIDs for {len(validated)} validated addresses (concurrent)...")
        zpid_items = []

        with ThreadPoolExecutor(max_workers=min(len(validated), 5)) as executor:
            futures = {}
            for idx, c, full_address, validation in validated:
                future = executor.submit(get_zillow_zpid, full_address)
                futures[future] = (idx, c, full_address, validation)

            for future in as_completed(futures):
                idx, c, full_address, validation = futures[future]
                cid = c["id"]

                try:
                    zpid_info = future.result()
                except Exception as e:
                    print(f"    Zillow error for {full_address}: {e}")
                    self.stats["processed"] += 1
                    self._save_address_only(cid, full_address, validation)
                    continue

                if zpid_info:
                    self.stats["zpids_found"] += 1
                    zpid_items.append({
                        "zpid": zpid_info["zpid"],
                        "display": zpid_info["display"],
                        "contact_idx": idx,
                        "address": full_address,
                    })
                else:
                    self.stats["processed"] += 1
                    self._save_address_only(cid, full_address, validation)

        # Step 4: Batch Zillow detail lookup
        if zpid_items:
            print(f"\n  [Step 4] Fetching Zillow details for {len(zpid_items)} properties...")
            zillow_results = get_zillow_details_batch(zpid_items, self.apify_key)

            # Build lookup by zpid — results may come back in any order
            zr_by_zpid = {}
            for zr in zillow_results:
                zr_zpid = zr.get("zpid")
                if zr_zpid:
                    zr_by_zpid[int(zr_zpid)] = zr

            matched = 0
            for zpid_item in zpid_items:
                contact_idx = zpid_item["contact_idx"]
                c = contacts[contact_idx]
                cid = c["id"]
                name = f"{c['first_name']} {c['last_name']}"
                address = zpid_item["address"]
                target_zpid = int(zpid_item["zpid"])

                zr = zr_by_zpid.get(target_zpid)
                if not zr:
                    print(f"    {name}: no Zillow result for zpid {target_zpid}")
                    self._save_address_only(cid, address, {"confidence": "high"})
                    self.stats["processed"] += 1
                    continue

                matched += 1
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
                    print(f"    {name}: Zestimate = {z_str} "
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
                    "ownership_likelihood": classify_ownership(address, home_type, z),
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

            print(f"    Matched {matched}/{len(zpid_items)} by zpid")

    def _process_batch_411(self, contacts: list[dict]):
        """Process contacts using 411.com scraper with multi-candidate validation.

        The 411.com scraper handles search + GPT-5 mini candidate selection in one step,
        then we continue with the Zillow pipeline for address → Zestimate.
        """
        # Step 0: Backfill city/state from LinkedIn data
        self._backfill_locations(contacts)

        # Filter out no-location contacts
        skipped = [c for c in contacts if c.get("_no_us_location")]
        for c in skipped:
            name = f"{c['first_name']} {c['last_name']}"
            print(f"    SKIP {name}: no US location found")
            self._save_no_result(c["id"], skip_reason="no_us_location")
            self.stats["skipped_no_location"] += 1
            self.stats["processed"] += 1
        contacts = [c for c in contacts if not c.get("_no_us_location")]
        if not contacts:
            print("    No contacts with US location in this batch")
            return

        batch_size = len(contacts)
        print(f"\n  [Step 1] Searching 411.com for {batch_size} contacts (FREE)...")

        # Step 1: 411.com search + GPT-5 mini candidate selection
        skip_results = skip_trace_411(contacts, self.openai_client)

        if not skip_results:
            print(f"    FAILED: No results from 411.com")
            self.stats["errors"] += batch_size
            return

        # Process results — already validated by GPT-5 mini
        validated = []
        for idx, sr in enumerate(skip_results):
            c = contacts[idx]
            cid = c["id"]
            name = f"{c['first_name']} {c['last_name']}"

            if sr.get("_no_result"):
                self.stats["no_address"] += 1
                self.stats["processed"] += 1
                self._save_no_result(cid, skip_reason=sr.get("_skip_reason"))
                continue

            if sr.get("_rejected_all"):
                self.stats["rejected"] += 1
                self.stats["processed"] += 1
                validation = sr.get("_validation", {})
                self._save_rejected(cid, "no candidates matched", validation)
                continue

            street = sr.get("Street Address", "")
            if not street:
                self.stats["no_address"] += 1
                self.stats["processed"] += 1
                self._save_no_result(cid)
                continue

            self.stats["addresses_found"] += 1
            self.stats["validated"] += 1

            locality = sr.get("Address Locality", "")
            region = sr.get("Address Region", "")
            postal = sr.get("Postal Code", "")
            full_address = f"{street}, {locality}, {region} {postal}"

            validation = sr.get("_validation", {"confidence": "high"})
            print(f"    [+] {name}: {full_address} "
                  f"(411.com, {sr.get('_candidates_count', '?')} candidates)")
            validated.append((idx, c, full_address, validation))

        # Step 2: Zillow autocomplete for all validated
        if not validated:
            return

        print(f"\n  [Step 2] Getting ZPIDs for {len(validated)} validated addresses (concurrent)...")
        zpid_items = []

        with ThreadPoolExecutor(max_workers=min(len(validated), 5)) as executor:
            futures = {}
            for idx, c, full_address, validation in validated:
                future = executor.submit(get_zillow_zpid, full_address)
                futures[future] = (idx, c, full_address, validation)

            for future in as_completed(futures):
                idx, c, full_address, validation = futures[future]
                cid = c["id"]

                try:
                    zpid_info = future.result()
                except Exception as e:
                    print(f"    Zillow error for {full_address}: {e}")
                    self.stats["processed"] += 1
                    self._save_address_only(cid, full_address, validation)
                    continue

                if zpid_info:
                    self.stats["zpids_found"] += 1
                    zpid_items.append({
                        "zpid": zpid_info["zpid"],
                        "display": zpid_info["display"],
                        "contact_idx": idx,
                        "address": full_address,
                    })
                else:
                    self.stats["processed"] += 1
                    self._save_address_only(cid, full_address, validation)

        # Step 3: Batch Zillow detail lookup
        if zpid_items:
            if not self.apify_key:
                # Save addresses without Zillow data when Apify isn't configured
                for zpid_item in zpid_items:
                    contact_idx = zpid_item["contact_idx"]
                    c = contacts[contact_idx]
                    self._save_address_only(c["id"], zpid_item["address"],
                                            {"confidence": "high"})
                    self.stats["processed"] += 1
                print(f"\n  [Step 3] Skipped Zillow details (no APIFY_API_KEY)")
                return

            print(f"\n  [Step 3] Fetching Zillow details for {len(zpid_items)} properties...")
            zillow_results = get_zillow_details_batch(zpid_items, self.apify_key)

            # Build lookup by zpid — results may come back in any order
            zr_by_zpid = {}
            for zr in zillow_results:
                zr_zpid = zr.get("zpid")
                if zr_zpid:
                    zr_by_zpid[int(zr_zpid)] = zr

            matched = 0
            for zpid_item in zpid_items:
                contact_idx = zpid_item["contact_idx"]
                c = contacts[contact_idx]
                cid = c["id"]
                name = f"{c['first_name']} {c['last_name']}"
                address = zpid_item["address"]
                target_zpid = int(zpid_item["zpid"])

                zr = zr_by_zpid.get(target_zpid)
                if not zr:
                    print(f"    {name}: no Zillow result for zpid {target_zpid}")
                    self._save_address_only(cid, address, {"confidence": "high"})
                    self.stats["processed"] += 1
                    continue

                matched += 1
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
                    print(f"    {name}: Zestimate = {z_str} "
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
                    "ownership_likelihood": classify_ownership(address, home_type, z),
                    "confidence": "high",
                    "source": "411_scraper",
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

            print(f"    Matched {matched}/{len(zpid_items)} by zpid")

    def _save_no_result(self, cid: str, skip_reason: str = None):
        """Store marker for contacts with no skip-trace result."""
        data = {
            "confidence": "no_result",
            "source": "skip_trace_failed",
            "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        if skip_reason:
            data["skip_reason"] = skip_reason
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
            "ownership_likelihood": classify_ownership(address, None, None),
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
        source_str = "411.com (FREE)" if self.source == "411" else "Apify ($0.007/ea)"
        retry_str = " [RETRY REJECTED]" if self.retry_rejected else ""
        print(f"\n--- {mode_str} MODE: Processing {total} contacts{retry_str} ---")
        print(f"    Source: {source_str}")
        print(f"    Batch size: {SKIP_TRACE_BATCH_SIZE}")
        if self.source == "411":
            est_cost = total * 0.005 + total * 0.5 * 0.003  # GPT validation only
            print(f"    Estimated cost: ~${est_cost:.2f} (GPT validation + Zillow only)")
        else:
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
    parser.add_argument("--source", choices=["apify", "411"], default="apify",
                        help="People search source: apify (paid) or 411 (free, multi-candidate)")
    parser.add_argument("--retry-rejected", action="store_true",
                        help="Re-process previously rejected/failed contacts")
    args = parser.parse_args()

    enricher = RealEstateEnricher(
        test_mode=args.test,
        batch_size=args.batch,
        start_from=args.start_from,
        source=args.source,
        retry_rejected=args.retry_rejected,
    )
    success = enricher.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
