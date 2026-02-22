#!/usr/bin/env python3
"""
Test API matching for FEC + BatchData enrichment.

Tests:
1. OpenFEC API — search by name, check match quality
2. BatchData API — search by name + state, check match quality
3. GPT-5 mini verification — disambiguate candidates against contact profile

Usage:
  python scripts/intelligence/test_api_matching.py
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
OPENFEC_API_KEY = os.environ["OPENFEC_API_KEY"]
BATCHDATA_API_KEY = os.environ["BATCHDATA_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_APIKEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ── Fetch test contacts ──────────────────────────────────────────────

def get_test_contacts(n=5):
    """Get a mix of contacts: some common names, some unique."""
    resp = (
        supabase.table("contacts")
        .select("id, first_name, last_name, linkedin_url, city, state, position, company, enrich_employment, enrich_education")
        .gte("familiarity_rating", 3)
        .not_.is_("city", "null")
        .not_.is_("state", "null")
        .not_.is_("company", "null")
        .order("familiarity_rating", desc=True)
        .limit(n)
        .execute()
    )
    return resp.data

# ── OpenFEC API ──────────────────────────────────────────────────────

def search_fec(first_name: str, last_name: str, state: str = None, city: str = None):
    """Search OpenFEC Schedule A (individual contributions) by contributor name."""
    url = "https://api.open.fec.gov/v1/schedules/schedule_a/"
    params = {
        "api_key": OPENFEC_API_KEY,
        "contributor_name": f"{first_name} {last_name}",
        "sort": "-contribution_receipt_date",
        "per_page": 20,
        "two_year_transaction_period": [2024, 2022, 2020],
        "is_individual": True,
    }
    if state:
        params["contributor_state"] = state

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        pagination = data.get("pagination", {})
        total = pagination.get("count", 0)
        return {"results": results, "total": total, "error": None}
    except Exception as e:
        return {"results": [], "total": 0, "error": str(e)}


def analyze_fec_results(contact, fec_data):
    """Print FEC results analysis for a contact."""
    name = f"{contact['first_name']} {contact['last_name']}"
    city = contact.get("city", "")
    state = contact.get("state", "")
    company = contact.get("company", "")

    print(f"\n  FEC Results for {name} ({city}, {state} — {company}):")

    if fec_data["error"]:
        print(f"    ERROR: {fec_data['error']}")
        return

    total = fec_data["total"]
    results = fec_data["results"]
    print(f"    Total matching records: {total}")

    if not results:
        print(f"    No FEC donation records found.")
        return

    # Group by unique contributor (name + city + state + employer)
    unique_people = {}
    for r in results:
        key = (
            r.get("contributor_name", "").upper(),
            r.get("contributor_city", "").upper(),
            r.get("contributor_state", "").upper(),
            (r.get("contributor_employer") or "").upper(),
        )
        if key not in unique_people:
            unique_people[key] = {
                "name": r.get("contributor_name"),
                "city": r.get("contributor_city"),
                "state": r.get("contributor_state"),
                "employer": r.get("contributor_employer"),
                "occupation": r.get("contributor_occupation"),
                "total": 0,
                "count": 0,
                "donations": [],
            }
        unique_people[key]["total"] += r.get("contribution_receipt_amount", 0)
        unique_people[key]["count"] += 1
        unique_people[key]["donations"].append({
            "amount": r.get("contribution_receipt_amount"),
            "date": r.get("contribution_receipt_date"),
            "committee": r.get("committee", {}).get("name", "Unknown"),
        })

    print(f"    Unique contributor profiles: {len(unique_people)}")
    print()

    for i, (key, person) in enumerate(unique_people.items(), 1):
        city_match = person["city"] and city and person["city"].upper() == city.upper()
        state_match = person["state"] and state and person["state"].upper() == state.upper()
        employer_match = person["employer"] and company and (
            company.upper() in person["employer"].upper() or
            person["employer"].upper() in company.upper()
        )

        match_signals = []
        if state_match: match_signals.append("STATE")
        if city_match: match_signals.append("CITY")
        if employer_match: match_signals.append("EMPLOYER")

        confidence = "HIGH" if len(match_signals) >= 2 else "MEDIUM" if match_signals else "LOW"

        print(f"    Candidate {i}: {person['name']}")
        print(f"      Location: {person['city']}, {person['state']}")
        print(f"      Employer: {person['employer']}")
        print(f"      Occupation: {person['occupation']}")
        print(f"      Donations: {person['count']} totaling ${person['total']:,.0f}")
        print(f"      Match signals: {match_signals or 'NONE'} → Confidence: {confidence}")

        # Show top 3 donations
        for d in person["donations"][:3]:
            print(f"        ${d['amount']:,.0f} on {d['date']} → {d['committee']}")
        print()

    return unique_people


# ── BatchData API ────────────────────────────────────────────────────

def search_batchdata(first_name: str, last_name: str, state: str = None, city: str = None):
    """Search BatchData property records by owner name."""
    url = "https://api.batchdata.com/api/v1/property/search/owner"
    headers = {
        "Authorization": f"Bearer {BATCHDATA_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "firstName": first_name,
        "lastName": last_name,
    }
    if state:
        body["state"] = state
    if city:
        body["city"] = city

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return {"results": data, "error": None}
    except requests.exceptions.HTTPError as e:
        return {"results": {}, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"results": {}, "error": str(e)}


def analyze_batchdata_results(contact, bd_data):
    """Print BatchData results analysis for a contact."""
    name = f"{contact['first_name']} {contact['last_name']}"
    city = contact.get("city", "")
    state = contact.get("state", "")

    print(f"\n  BatchData Results for {name} ({city}, {state}):")

    if bd_data["error"]:
        print(f"    ERROR: {bd_data['error']}")
        return

    results = bd_data.get("results", {})
    # BatchData response structure varies — let's inspect it
    print(f"    Raw response keys: {list(results.keys()) if isinstance(results, dict) else type(results)}")

    # Try to extract properties
    properties = results.get("results", {}).get("properties", [])
    if not properties:
        properties = results.get("data", [])
    if not properties:
        properties = results.get("properties", [])

    if not properties:
        print(f"    No property records found.")
        print(f"    Full response (truncated): {json.dumps(results, indent=2)[:500]}")
        return

    print(f"    Properties found: {len(properties)}")
    for i, prop in enumerate(properties[:5], 1):
        addr = prop.get("address", {}) if isinstance(prop, dict) else {}
        val = prop.get("assessment", {}) if isinstance(prop, dict) else {}
        sale = prop.get("lastSale", {}) if isinstance(prop, dict) else {}

        print(f"\n    Property {i}:")
        print(f"      Address: {addr}")
        print(f"      Assessment: {val}")
        print(f"      Last Sale: {sale}")
    print()

    return properties


# ── GPT-5 mini Verification ─────────────────────────────────────────

def verify_match_gpt5m(contact, candidates_description: str, source: str) -> dict:
    """Use GPT-5 mini to verify if FEC/BatchData candidates match our contact."""
    contact_profile = (
        f"Name: {contact['first_name']} {contact['last_name']}\n"
        f"City: {contact.get('city', 'Unknown')}, State: {contact.get('state', 'Unknown')}\n"
        f"Current Position: {contact.get('position', 'Unknown')} at {contact.get('company', 'Unknown')}\n"
        f"LinkedIn: {contact.get('linkedin_url', 'Unknown')}\n"
    )

    # Add employment history if available
    employment = contact.get("enrich_employment")
    if employment and isinstance(employment, list):
        jobs = []
        for emp in employment[:5]:
            if isinstance(emp, dict):
                co = emp.get("companyName", "")
                title = emp.get("title", "")
                jobs.append(f"  - {title} at {co}")
        if jobs:
            contact_profile += f"Employment History:\n" + "\n".join(jobs) + "\n"

    education = contact.get("enrich_education")
    if education and isinstance(education, list):
        schools = []
        for edu in education[:3]:
            if isinstance(edu, dict):
                school = edu.get("schoolName", "")
                degree = edu.get("degreeName", "")
                schools.append(f"  - {degree} from {school}")
        if schools:
            contact_profile += f"Education:\n" + "\n".join(schools) + "\n"

    prompt = f"""You are verifying whether public records match a specific person from our contacts database.

CONTACT PROFILE:
{contact_profile}

{source.upper()} CANDIDATE RECORDS:
{candidates_description}

For each candidate record, determine:
1. Is this the SAME PERSON as our contact? (yes / no / uncertain)
2. What evidence supports or contradicts the match?
3. Confidence level (high / medium / low)

If there are multiple candidates, identify which one (if any) is the correct match.

Respond in JSON format:
{{
  "matches": [
    {{
      "candidate_index": 1,
      "is_match": true/false/null,
      "confidence": "high"/"medium"/"low",
      "reasoning": "brief explanation"
    }}
  ],
  "best_match_index": null or 1-based index,
  "overall_confidence": "high"/"medium"/"low"/"no_match"
}}"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        return {"error": str(e)}


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 70)
    print("  API MATCHING TEST — FEC + BatchData + GPT-5 mini Verification")
    print("=" * 70)

    contacts = get_test_contacts(5)
    print(f"\nFetched {len(contacts)} test contacts (familiarity >= 3)\n")

    for i, c in enumerate(contacts, 1):
        name = f"{c['first_name']} {c['last_name']}"
        print(f"\n{'─' * 70}")
        print(f"  CONTACT {i}: {name}")
        print(f"  {c.get('position', '')} at {c.get('company', '')}")
        print(f"  {c.get('city', '')}, {c.get('state', '')}")
        print(f"{'─' * 70}")

        # ── Test 1: FEC ──
        print(f"\n  [1] OpenFEC API Search...")
        fec_with_state = search_fec(c["first_name"], c["last_name"], state=c.get("state"))
        time.sleep(0.5)  # Rate limit courtesy

        unique_people = analyze_fec_results(c, fec_with_state)

        # If we got candidates, run GPT-5 mini verification
        if unique_people and len(unique_people) > 0:
            candidates_desc = ""
            for j, (key, person) in enumerate(unique_people.items(), 1):
                candidates_desc += (
                    f"Candidate {j}: {person['name']}, {person['city']}, {person['state']}\n"
                    f"  Employer: {person['employer']}, Occupation: {person['occupation']}\n"
                    f"  Total donations: ${person['total']:,.0f} across {person['count']} contributions\n\n"
                )

            print(f"  [GPT-5 mini] Verifying FEC matches...")
            verification = verify_match_gpt5m(c, candidates_desc, "fec")
            print(f"    Verification result: {json.dumps(verification, indent=4)}")

        # ── Test 2: BatchData ──
        print(f"\n  [2] BatchData Property Search...")
        bd_data = search_batchdata(c["first_name"], c["last_name"], state=c.get("state"))
        time.sleep(0.5)

        properties = analyze_batchdata_results(c, bd_data)

        # If we got properties, run GPT-5 mini verification
        if properties and len(properties) > 0:
            prop_desc = ""
            for j, prop in enumerate(properties[:5], 1):
                addr = prop.get("address", {}) if isinstance(prop, dict) else {}
                owner = prop.get("owner", {}) if isinstance(prop, dict) else {}
                prop_desc += (
                    f"Property {j}: {json.dumps(addr, indent=2)[:200]}\n"
                    f"  Owner info: {json.dumps(owner, indent=2)[:200]}\n\n"
                )

            print(f"  [GPT-5 mini] Verifying BatchData matches...")
            verification = verify_match_gpt5m(c, prop_desc, "real_estate")
            print(f"    Verification result: {json.dumps(verification, indent=4)}")

        print()

    print("\n" + "=" * 70)
    print("  TEST COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
