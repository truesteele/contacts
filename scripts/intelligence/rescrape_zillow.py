#!/usr/bin/env python3
"""Re-scrape Zillow details for all contacts with existing real_estate_data.

Fixes the batch data bug where results were matched by index instead of zpid,
causing property data to be assigned to the wrong contacts.

Usage:
    python scripts/intelligence/rescrape_zillow.py [--batch-size 25] [--test]
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from supabase import create_client

# ── Config ────────────────────────────────────────────────────────────

APIFY_WAIT_TIMEOUT = 300  # seconds
APIFY_POLL_INTERVAL = 10
APIFY_POLL_MAX = 60
ZILLOW_BATCH_SIZE = 25  # URLs per Apify run

UNIT_PATTERN_IMPORT = None  # Will reuse from enrich_real_estate


def classify_ownership(address, property_type, zestimate):
    """Classify ownership likelihood based on property type and address."""
    import re
    has_unit = bool(address and re.search(
        r'\b(apt|unit|ste|suite|#|no\.?)\s*\w+', address, re.IGNORECASE))
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
    if has_unit and not has_zest:
        return "likely_renter"
    return "uncertain" if not has_zest else "likely_owner"


def get_zillow_zpid(address: str) -> dict | None:
    """Look up a Zillow ZPID via the autocomplete API (free)."""
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
        print(f"    Zillow autocomplete error for '{address}': {e}")
    return None


def get_zillow_details_batch(zpid_items: list[dict], apify_key: str) -> dict:
    """Run Apify scraper for a batch of ZPIDs. Returns dict keyed by zpid."""
    if not zpid_items:
        return {}

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
        return {}

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
        return {}

    items = requests.get(
        f"https://api.apify.com/v2/datasets/{dsid}/items",
        params={"token": apify_key}, timeout=30
    ).json()

    # Key by zpid for correct matching
    result = {}
    for item in items:
        zpid = item.get("zpid")
        if zpid:
            result[int(zpid)] = item
    return result


def main():
    parser = argparse.ArgumentParser(description="Re-scrape Zillow details")
    parser.add_argument("--batch-size", type=int, default=ZILLOW_BATCH_SIZE,
                        help=f"URLs per Apify run (default {ZILLOW_BATCH_SIZE})")
    parser.add_argument("--test", action="store_true",
                        help="Only process first 5 contacts")
    parser.add_argument("--zpid-workers", type=int, default=5,
                        help="Concurrent workers for ZPID lookups (default 5)")
    args = parser.parse_args()

    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    apify_key = os.getenv("APIFY_API_KEY")

    if not all([supabase_url, supabase_key, apify_key]):
        print("Missing env vars: SUPABASE_URL, SUPABASE_SERVICE_KEY, APIFY_API_KEY")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)

    # Fetch all contacts with real_estate_data that have addresses
    print("Fetching contacts with real_estate_data...")
    contacts = []
    page_size = 1000
    offset = 0
    while True:
        page = (
            supabase.table("contacts")
            .select("id, first_name, last_name, real_estate_data")
            .not_.is_("real_estate_data", "null")
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        contacts.extend(page.data)
        if len(page.data) < page_size:
            break
        offset += page_size

    # Filter to those with addresses
    contacts_with_addr = []
    for c in contacts:
        rd = c.get("real_estate_data", {})
        addr = rd.get("address") if isinstance(rd, dict) else None
        if addr:
            contacts_with_addr.append(c)

    print(f"Found {len(contacts_with_addr)} contacts with addresses")

    if args.test:
        contacts_with_addr = contacts_with_addr[:5]
        print(f"TEST MODE: processing {len(contacts_with_addr)} contacts")

    # Step 1: Look up zpids concurrently
    print(f"\n[Step 1] Looking up ZPIDs for {len(contacts_with_addr)} addresses...")
    zpid_map = {}  # contact_id -> {zpid, display, address}

    with ThreadPoolExecutor(max_workers=args.zpid_workers) as executor:
        futures = {}
        for c in contacts_with_addr:
            addr = c["real_estate_data"]["address"]
            future = executor.submit(get_zillow_zpid, addr)
            futures[future] = c

        done = 0
        for future in as_completed(futures):
            c = futures[future]
            done += 1
            try:
                result = future.result()
                if result:
                    zpid_map[c["id"]] = {
                        "zpid": result["zpid"],
                        "display": result["display"],
                        "address": c["real_estate_data"]["address"],
                        "contact": c,
                    }
            except Exception as e:
                print(f"  Error for {c['first_name']} {c['last_name']}: {e}")

            if done % 100 == 0:
                print(f"  Progress: {done}/{len(contacts_with_addr)} zpid lookups")

    print(f"  Found {len(zpid_map)} ZPIDs out of {len(contacts_with_addr)} addresses")

    # Step 2: Batch scrape Zillow details
    zpid_list = list(zpid_map.values())
    total_batches = (len(zpid_list) + args.batch_size - 1) // args.batch_size
    print(f"\n[Step 2] Scraping Zillow details in {total_batches} batches "
          f"of {args.batch_size}...")

    stats = {"updated": 0, "no_result": 0, "errors": 0}
    start_time = time.time()

    for batch_idx in range(total_batches):
        batch_start = batch_idx * args.batch_size
        batch_end = min(batch_start + args.batch_size, len(zpid_list))
        batch = zpid_list[batch_start:batch_end]

        print(f"\n  Batch {batch_idx + 1}/{total_batches} "
              f"({len(batch)} properties)...")

        # Apify scrape
        zpid_items = [{"zpid": b["zpid"], "display": b["display"]} for b in batch]
        results_by_zpid = get_zillow_details_batch(zpid_items, apify_key)

        print(f"    Got {len(results_by_zpid)} results from Apify")

        # Match and update
        for item in batch:
            cid = item["contact"]["id"]
            name = f"{item['contact']['first_name']} {item['contact']['last_name']}"
            address = item["address"]
            zpid = int(item["zpid"])

            zr = results_by_zpid.get(zpid)
            if not zr:
                stats["no_result"] += 1
                continue

            z = zr.get("zestimate")
            rz = zr.get("rentZestimate")
            beds = zr.get("bedrooms")
            baths = zr.get("bathrooms")
            sqft = zr.get("livingArea")
            year = zr.get("yearBuilt")
            home_type = zr.get("homeType")
            tax_val = zr.get("taxAssessedValue")
            tax_year = zr.get("taxAssessedYear")
            lot_size = zr.get("lotSize")

            real_estate_data = {
                "address": address,
                "zestimate": z,
                "rent_zestimate": rz,
                "beds": beds,
                "baths": baths,
                "sqft": sqft,
                "year_built": year,
                "lot_size": lot_size,
                "property_type": home_type,
                "ownership_likelihood": classify_ownership(address, home_type, z),
                "confidence": "high",
                "source": "zillow_rescrape",
                "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
            if tax_val:
                real_estate_data["tax_assessed_value"] = tax_val
            if tax_year:
                real_estate_data["tax_assessed_year"] = tax_year

            try:
                supabase.table("contacts").update({
                    "real_estate_data": real_estate_data,
                }).eq("id", cid).execute()
                stats["updated"] += 1

                if z:
                    z_str = f"${z:,}" if isinstance(z, (int, float)) else str(z)
                    print(f"    {name}: {z_str} "
                          f"({beds or '?'}bd/{baths or '?'}ba, "
                          f"{sqft or '?'} sqft, {home_type or '?'})")
            except Exception as e:
                print(f"    ERROR saving {name}: {e}")
                stats["errors"] += 1

        elapsed = time.time() - start_time
        total_done = stats["updated"] + stats["no_result"] + stats["errors"]
        print(f"  Progress: {total_done}/{len(zpid_list)} "
              f"({stats['updated']} updated, {stats['no_result']} no result, "
              f"{stats['errors']} errors) [{elapsed:.0f}s elapsed]")

    # Summary
    elapsed = time.time() - start_time
    cost = len(zpid_list) * 0.003
    print(f"\n{'=' * 60}")
    print(f"ZILLOW RE-SCRAPE SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Contacts with addresses:  {len(contacts_with_addr)}")
    print(f"  ZPIDs found:              {len(zpid_map)}")
    print(f"  Updated:                  {stats['updated']}")
    print(f"  No Zillow result:         {stats['no_result']}")
    print(f"  Errors:                   {stats['errors']}")
    print(f"  Time elapsed:             {elapsed:.0f}s")
    print(f"  Estimated Apify cost:     ${cost:.2f}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
