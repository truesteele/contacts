#!/usr/bin/env python3
"""
Test Trestle Find Person API: name + city/state → home address.

Usage:
  python scripts/intelligence/test_trestle.py
"""

import os
import json
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

TRESTLE_API_KEY = os.environ["TRESTLE_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def find_person(first_name: str, last_name: str, city: str = None, state: str = None):
    """Call Trestle Find Person API."""
    url = "https://api.trestleiq.com/3.1/person"
    headers = {
        "x-api-key": TRESTLE_API_KEY,
    }
    params = {
        "name": f"{first_name} {last_name}",
    }
    if city:
        params["address.city"] = city
    if state:
        params["address.region"] = state

    resp = requests.get(url, headers=headers, params=params, timeout=15)
    return resp.status_code, resp.json() if resp.status_code == 200 else resp.text


def get_test_contacts(n=5):
    """Get familiar contacts with known cities for testing."""
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


def main():
    print("\n" + "=" * 70)
    print("  TRESTLE FIND PERSON API TEST")
    print("=" * 70)

    contacts = get_test_contacts(5)
    print(f"\nTesting with {len(contacts)} contacts (familiarity >= 3)\n")

    for i, c in enumerate(contacts, 1):
        name = f"{c['first_name']} {c['last_name']}"
        city = c.get("city", "")
        state = c.get("state", "")

        print(f"\n{'─' * 70}")
        print(f"  CONTACT {i}: {name}")
        print(f"  {c.get('position', '')} at {c.get('company', '')}")
        print(f"  Known location: {city}, {state}")
        print(f"{'─' * 70}")

        status, data = find_person(c["first_name"], c["last_name"], city, state)
        print(f"  HTTP Status: {status}")

        if status != 200:
            print(f"  ERROR: {str(data)[:500]}")
            continue

        # Print response structure
        if isinstance(data, dict):
            print(f"  Response keys: {list(data.keys())}")

            # Check for person results
            persons = data.get("person", data.get("persons", data.get("results", [])))
            if isinstance(persons, list):
                print(f"  Persons found: {len(persons)}")
                for j, person in enumerate(persons[:3], 1):
                    print(f"\n  Person {j}:")
                    if isinstance(person, dict):
                        # Name
                        pname = person.get("name", person.get("names", "N/A"))
                        print(f"    Name: {pname}")

                        # Addresses
                        addrs = person.get("addresses", person.get("address", []))
                        if isinstance(addrs, list):
                            for k, addr in enumerate(addrs[:3], 1):
                                if isinstance(addr, dict):
                                    street = addr.get("street_line_1", addr.get("street", addr.get("streetLine1", "")))
                                    city_r = addr.get("city", "")
                                    state_r = addr.get("state_code", addr.get("state", ""))
                                    zip_r = addr.get("postal_code", addr.get("zip", ""))
                                    is_current = addr.get("is_current", addr.get("isCurrent", ""))
                                    print(f"    Address {k}: {street}, {city_r}, {state_r} {zip_r} (current: {is_current})")
                                else:
                                    print(f"    Address {k}: {addr}")
                        elif isinstance(addrs, dict):
                            print(f"    Address: {addrs}")

                        # Phone
                        phones = person.get("phones", person.get("phone_numbers", []))
                        if isinstance(phones, list) and phones:
                            print(f"    Phones: {len(phones)}")

                        # Print all top-level keys for schema understanding
                        print(f"    All keys: {list(person.keys()) if isinstance(person, dict) else 'N/A'}")
            elif isinstance(persons, dict):
                print(f"  Single person result:")
                print(f"    Keys: {list(persons.keys())}")
            else:
                print(f"  Persons field type: {type(persons)}")

            # Print full first result for schema understanding (truncated)
            print(f"\n  Full response (truncated):")
            print(json.dumps(data, indent=2)[:1500])
        else:
            print(f"  Raw response: {str(data)[:500]}")

    print("\n" + "=" * 70)
    print("  TEST COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
