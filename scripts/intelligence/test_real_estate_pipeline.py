#!/usr/bin/env python3
"""
Test the full real estate enrichment pipeline at scale with address validation:
  Step 1: Name + City/State → Home Address (Apify skip-trace)
  Step 2: Address → Zillow ZPID (Zillow autocomplete API, free)
  Step 3: ZPID → Zestimate + property data (Apify happitap/zillow-detail-scraper)
  Validation: GPT-5 mini verifies skip-trace result matches the correct person

Usage:
  python scripts/intelligence/test_real_estate_pipeline.py            # 10 contacts
  python scripts/intelligence/test_real_estate_pipeline.py --count 20 # 20 contacts
  python scripts/intelligence/test_real_estate_pipeline.py --skip-zillow  # skip trace only
"""

import os
import sys
import json
import time
import argparse
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
APIFY_API_KEY = os.environ["APIFY_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_APIKEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)


# ── Step 1: Skip Trace (Name → Address) ─────────────────────────────

def skip_trace_batch(contacts: list[dict]) -> list[dict]:
    """Run Apify skip-trace for a batch of contacts.

    Input format: {"name": ["FirstName LastName; City, ST", ...]}
    Returns list of results aligned with input contacts.
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

    print(f"\n  [Step 1] Skip-tracing {len(names)} contacts...")

    url = f"https://api.apify.com/v2/acts/one-api~skip-trace/runs"
    params = {"token": APIFY_API_KEY, "waitForFinish": 300}
    body = {"name": names}

    resp = requests.post(url, json=body, params=params, timeout=360)
    if resp.status_code != 201:
        print(f"  ERROR starting skip-trace: {resp.status_code} {resp.text[:300]}")
        return []

    run = resp.json().get("data", {})
    status = run.get("status")
    run_id = run.get("id")
    dsid = run.get("defaultDatasetId", "")

    # Poll if not finished
    if status not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
        print(f"  Run {run_id} status: {status}, polling...")
        for _ in range(60):
            time.sleep(5)
            sr = requests.get(
                f"https://api.apify.com/v2/actor-runs/{run_id}",
                params={"token": APIFY_API_KEY}, timeout=15
            ).json().get("data", {})
            status = sr.get("status")
            dsid = sr.get("defaultDatasetId", dsid)
            if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break

    if status != "SUCCEEDED":
        print(f"  Skip-trace run {status}")
        return []

    # Fetch results
    items = requests.get(
        f"https://api.apify.com/v2/datasets/{dsid}/items",
        params={"token": APIFY_API_KEY}, timeout=30
    ).json()

    print(f"  Got {len(items)} skip-trace results")
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

def get_zillow_details(zpid_results: list[dict]) -> list[dict]:
    """Run Apify happitap/zillow-detail-scraper for a batch of ZPIDs."""
    if not zpid_results:
        return []

    urls = []
    for r in zpid_results:
        display = r["display"].replace(" ", "-").replace(",", "").replace(".", "")
        url = f"https://www.zillow.com/homedetails/{display}/{r['zpid']}_zpid/"
        urls.append({"url": url})

    print(f"\n  [Step 3] Fetching Zillow details for {len(urls)} properties...")

    resp = requests.post(
        f"https://api.apify.com/v2/acts/happitap~zillow-detail-scraper/runs",
        json={"startUrls": urls},
        params={"token": APIFY_API_KEY, "waitForFinish": 300},
        timeout=360
    )

    if resp.status_code != 201:
        print(f"  ERROR starting Zillow scraper: {resp.status_code} {resp.text[:300]}")
        return []

    run = resp.json().get("data", {})
    status = run.get("status")
    run_id = run.get("id")
    dsid = run.get("defaultDatasetId", "")

    if status not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
        print(f"  Run {run_id} status: {status}, polling...")
        for _ in range(60):
            time.sleep(5)
            sr = requests.get(
                f"https://api.apify.com/v2/actor-runs/{run_id}",
                params={"token": APIFY_API_KEY}, timeout=15
            ).json().get("data", {})
            status = sr.get("status")
            dsid = sr.get("defaultDatasetId", dsid)
            if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break

    if status != "SUCCEEDED":
        print(f"  Zillow scraper run {status}")
        return []

    items = requests.get(
        f"https://api.apify.com/v2/datasets/{dsid}/items",
        params={"token": APIFY_API_KEY}, timeout=30
    ).json()

    print(f"  Got {len(items)} Zillow detail results")
    return items


# ── GPT-5 mini Address Validation ────────────────────────────────────

def validate_address_match(contact: dict, skip_trace_result: dict) -> dict:
    """Use GPT-5 mini to verify the skip-trace address belongs to the right person."""
    contact_profile = (
        f"Name: {contact['first_name']} {contact['last_name']}\n"
        f"Known City: {contact.get('city', 'Unknown')}, State: {contact.get('state', 'Unknown')}\n"
        f"Current Position: {contact.get('position', 'Unknown')} at {contact.get('company', 'Unknown')}\n"
        f"LinkedIn: {contact.get('linkedin_url', 'Unknown')}\n"
    )

    # Add employment history for better matching
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

    # Add previous addresses for context
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
   - Is the address location consistent with the known city/state? (Note: people may live in nearby suburbs — San Leandro is near San Francisco, etc.)
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


# ── Fetch test contacts ──────────────────────────────────────────────

def get_test_contacts(n=10):
    """Get contacts with known cities for testing, mix of familiarity levels."""
    resp = (
        supabase.table("contacts")
        .select(
            "id, first_name, last_name, city, state, company, position, "
            "familiarity_rating, linkedin_url, enrich_employment, enrich_education"
        )
        .gte("familiarity_rating", 2)
        .not_.is_("city", "null")
        .not_.is_("state", "null")
        .order("familiarity_rating", desc=True)
        .limit(n)
        .execute()
    )
    return resp.data


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10, help="Number of contacts to test")
    parser.add_argument("--skip-zillow", action="store_true", help="Only run skip-trace, skip Zillow")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  REAL ESTATE PIPELINE — SCALED TEST")
    print("  Step 1: Apify skip-trace (name → address)")
    print("  Step 2: Zillow autocomplete (address → ZPID)")
    print("  Step 3: Apify Zillow detail (ZPID → Zestimate)")
    print("  Validation: GPT-5 mini address verification")
    print("=" * 70)

    # Fetch contacts
    contacts = get_test_contacts(args.count)
    print(f"\nFetched {len(contacts)} contacts (familiarity >= 2)")
    for i, c in enumerate(contacts, 1):
        print(f"  {i}. {c['first_name']} {c['last_name']} — {c.get('city')}, {c.get('state')} "
              f"(fam={c.get('familiarity_rating')}, {c.get('company', '?')})")

    # Step 1: Skip trace
    skip_results = skip_trace_batch(contacts)

    if not skip_results:
        print("\n  FAILED: No skip-trace results")
        return

    # Match skip-trace results back to contacts by input name
    results_by_input = {}
    for sr in skip_results:
        input_given = sr.get("Input Given", "")
        results_by_input[input_given] = sr

    # Process each contact
    pipeline_results = []
    validated_count = 0
    address_found_count = 0
    zpid_found_count = 0
    zestimate_found_count = 0

    print(f"\n{'─' * 70}")
    print(f"  RESULTS")
    print(f"{'─' * 70}")

    zpid_batch = []  # Collect ZPIDs for batch Zillow lookup

    for i, c in enumerate(contacts, 1):
        name = f"{c['first_name']} {c['last_name']}"
        city = c.get("city", "")
        state = c.get("state", "")

        # Find matching skip-trace result
        key1 = f"{name}; {city}, {state}"
        key2 = f"{name}; {state}"
        sr = results_by_input.get(key1) or results_by_input.get(key2)

        result = {
            "contact": f"{name}",
            "known_location": f"{city}, {state}",
            "company": c.get("company", ""),
            "familiarity": c.get("familiarity_rating"),
        }

        if not sr or not sr.get("Street Address"):
            print(f"\n  {i}. {name} ({city}, {state})")
            print(f"     ❌ No address found in skip-trace")
            result["skip_trace"] = "no_result"
            pipeline_results.append(result)
            continue

        address_found_count += 1
        street = sr.get("Street Address", "")
        locality = sr.get("Address Locality", "")
        region = sr.get("Address Region", "")
        postal = sr.get("Postal Code", "")
        full_address = f"{street}, {locality}, {region} {postal}"

        result["address"] = full_address
        result["age"] = sr.get("Age", "")

        print(f"\n  {i}. {name} ({city}, {state})")
        print(f"     📍 {full_address}")
        print(f"     Age: {sr.get('Age', '?')}, Born: {sr.get('Born', '?')}")

        # Validate with GPT-5 mini
        print(f"     🤖 Validating match...")
        validation = validate_address_match(c, sr)
        result["validation"] = validation

        is_match = validation.get("is_match")
        confidence = validation.get("confidence", "?")
        reasoning = validation.get("reasoning", "")

        match_symbol = "✅" if is_match else "❌" if is_match is False else "❓"
        print(f"     {match_symbol} Match: {is_match} (confidence: {confidence})")
        print(f"     💬 {reasoning}")

        if is_match:
            validated_count += 1

        # Step 2: Zillow autocomplete
        if not args.skip_zillow and is_match:
            zpid_info = get_zillow_zpid(full_address)
            if zpid_info:
                zpid_found_count += 1
                result["zpid"] = zpid_info["zpid"]
                zpid_batch.append({
                    "contact_index": i - 1,
                    "zpid": zpid_info["zpid"],
                    "display": zpid_info["display"],
                })
                print(f"     🏠 ZPID: {zpid_info['zpid']}")
            else:
                print(f"     🏠 No Zillow ZPID found")

        pipeline_results.append(result)

    # Step 3: Batch Zillow detail lookup
    if zpid_batch and not args.skip_zillow:
        zillow_results = get_zillow_details(zpid_batch)

        # Match Zillow results back (by order, since we sent them in order)
        for j, zr in enumerate(zillow_results):
            if j < len(zpid_batch):
                idx = zpid_batch[j]["contact_index"]
                z = zr.get("zestimate")
                rz = zr.get("rentZestimate")
                beds = zr.get("bedrooms", "?")
                baths = zr.get("bathrooms", "?")
                sqft = zr.get("livingArea", "?")
                year = zr.get("yearBuilt", "?")
                home_type = zr.get("homeType", "?")

                pipeline_results[idx]["zestimate"] = z
                pipeline_results[idx]["rent_zestimate"] = rz
                pipeline_results[idx]["property"] = f"{beds}bd/{baths}ba, {sqft} sqft, {year}, {home_type}"

                if z:
                    zestimate_found_count += 1

                c_name = pipeline_results[idx]["contact"]
                z_str = f"${z:,}" if isinstance(z, (int, float)) else str(z)
                print(f"\n  💰 {c_name}: Zestimate = {z_str} ({beds}bd/{baths}ba, {sqft} sqft)")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  PIPELINE SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Contacts tested:     {len(contacts)}")
    print(f"  Addresses found:     {address_found_count}/{len(contacts)} ({address_found_count/len(contacts)*100:.0f}%)")
    print(f"  Validated matches:   {validated_count}/{address_found_count} ({validated_count/max(address_found_count,1)*100:.0f}%)")
    if not args.skip_zillow:
        print(f"  ZPIDs found:         {zpid_found_count}/{validated_count} ({zpid_found_count/max(validated_count,1)*100:.0f}%)")
        print(f"  Zestimates obtained: {zestimate_found_count}/{zpid_found_count} ({zestimate_found_count/max(zpid_found_count,1)*100:.0f}%)")
    print(f"\n  Cost estimate:")
    print(f"    Skip-trace: {len(contacts)} × $0.007 = ${len(contacts) * 0.007:.2f}")
    print(f"    Zillow detail: {zpid_found_count} × $0.003 = ${zpid_found_count * 0.003:.3f}")
    print(f"    GPT-5 mini validation: {address_found_count} × ~$0.002 = ${address_found_count * 0.002:.3f}")
    total = len(contacts) * 0.007 + zpid_found_count * 0.003 + address_found_count * 0.002
    print(f"    Total: ${total:.3f}")

    # Dump full results
    print(f"\n  Full results saved to: /tmp/real_estate_pipeline_results.json")
    with open("/tmp/real_estate_pipeline_results.json", "w") as f:
        json.dump(pipeline_results, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("  TEST COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
