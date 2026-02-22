#!/usr/bin/env python3
"""
Test the real estate enrichment flow:
  Step 1: Name → Home Address (people search API)
  Step 2: Address → Home Value (Apify Zillow scraper)

Usage:
  python scripts/intelligence/test_real_estate_flow.py
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
APIFY_API_KEY = os.environ["APIFY_API_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Step 2 Test: Apify Zillow Scraper (address → Zestimate) ──────────

def test_zillow_scraper(addresses: list[str]):
    """Test the Apify Bulk Zillow Scraper with known addresses."""
    print(f"\n{'='*60}")
    print(f"  STEP 2 TEST: Apify Bulk Zillow Scraper")
    print(f"  Actor: aknahin/zillow-property-info-scraper")
    print(f"  Addresses: {len(addresses)}")
    print(f"{'='*60}\n")

    # Start the actor run
    actor_id = "aknahin~zillow-property-info-scraper"
    url = f"https://api.apify.com/v2/acts/{actor_id}/runs"

    # The actor accepts addresses as newline-separated text
    input_data = {
        "addresses": "\n".join(addresses),
    }

    headers = {
        "Content-Type": "application/json",
    }
    params = {
        "token": APIFY_API_KEY,
    }

    print(f"  Starting Apify actor run...")
    resp = requests.post(url, json=input_data, headers=headers, params=params, timeout=30)
    print(f"  Status: {resp.status_code}")

    if resp.status_code != 201:
        print(f"  ERROR: {resp.text[:500]}")
        return None

    run_data = resp.json()["data"]
    run_id = run_data["id"]
    print(f"  Run ID: {run_id}")
    print(f"  Status: {run_data['status']}")

    # Poll for completion
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
    max_wait = 120  # 2 minutes
    waited = 0

    while waited < max_wait:
        time.sleep(5)
        waited += 5
        status_resp = requests.get(status_url, params=params, timeout=15)
        status_data = status_resp.json()["data"]
        status = status_data["status"]
        print(f"  [{waited}s] Status: {status}")

        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break

    if status != "SUCCEEDED":
        print(f"  ERROR: Run ended with status {status}")
        return None

    # Get results from default dataset
    dataset_id = status_data["defaultDatasetId"]
    results_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
    results_resp = requests.get(results_url, params=params, timeout=30)
    results = results_resp.json()

    print(f"\n  Results: {len(results)} items")
    for i, item in enumerate(results):
        print(f"\n  Property {i+1}:")
        print(f"    Address: {item.get('address', 'N/A')}")
        print(f"    Zestimate: ${item.get('zestimate', 'N/A'):,}" if isinstance(item.get('zestimate'), (int, float)) else f"    Zestimate: {item.get('zestimate', 'N/A')}")
        print(f"    Beds: {item.get('bedrooms', 'N/A')}")
        print(f"    Baths: {item.get('bathrooms', 'N/A')}")
        print(f"    Sqft: {item.get('livingArea', item.get('sqft', 'N/A'))}")
        print(f"    Year Built: {item.get('yearBuilt', 'N/A')}")
        print(f"    Property Type: {item.get('homeType', item.get('propertyType', 'N/A'))}")
        # Print all keys so we can see the full response structure
        print(f"    All keys: {list(item.keys())}")

    # Print one full result for schema understanding
    if results:
        print(f"\n  Full first result (JSON):")
        print(json.dumps(results[0], indent=2)[:1000])

    return results


# ── Get test contacts with known cities ───────────────────────────────

def get_test_contacts(n=3):
    """Get contacts we know well for testing."""
    resp = (
        supabase.table("contacts")
        .select("id, first_name, last_name, city, state, company, position, familiarity_rating")
        .gte("familiarity_rating", 3)
        .not_.is_("city", "null")
        .not_.is_("state", "null")
        .order("familiarity_rating", desc=True)
        .limit(n)
        .execute()
    )
    return resp.data


# ── Main ──────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  REAL ESTATE ENRICHMENT FLOW — API TEST")
    print("=" * 60)

    # Test Step 2 first with known addresses (no API key needed for address lookup)
    test_addresses = [
        "1600 Amphitheatre Parkway, Mountain View, CA 94043",  # Google HQ
        "1 Hacker Way, Menlo Park, CA 94025",                  # Meta HQ
        "350 5th Avenue, New York, NY 10118",                   # Empire State Building
    ]

    print("\n--- Testing with well-known addresses first ---")
    results = test_zillow_scraper(test_addresses)

    if results:
        print(f"\n  SUCCESS: Zillow scraper returned {len(results)} results")
    else:
        print(f"\n  FAILED: No results from Zillow scraper")

    # Show test contacts we'd want to look up
    print(f"\n\n{'='*60}")
    print(f"  TEST CONTACTS (would need address lookup for Step 1)")
    print(f"{'='*60}")

    contacts = get_test_contacts(5)
    for i, c in enumerate(contacts, 1):
        print(f"\n  {i}. {c['first_name']} {c['last_name']}")
        print(f"     {c.get('position', '')} at {c.get('company', '')}")
        print(f"     {c.get('city', '')}, {c.get('state', '')} | Familiarity: {c.get('familiarity_rating', 'N/A')}")

    print(f"\n  These contacts need Step 1 (name → address) before we can get Zestimates.")
    print(f"  Options: EnformionGO (100 free/mo), Open People Search ($0.05/lookup)")

    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
