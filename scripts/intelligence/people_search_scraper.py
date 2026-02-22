#!/usr/bin/env python3
"""
Custom People Search Scraper — Multi-Result via 411.com

Replaces Apify one-api/skip-trace ($0.007/result, 1 result only) with a FREE
multi-result scraper using 411.com (Whitepages). Returns 3-10 candidates per
name, enabling GPT-5 mini to pick the correct match.

No browser needed — uses curl_cffi with Chrome TLS impersonation.

Expected improvement: 38% → 55-80% end-to-end validation rate.

Usage:
  python scripts/intelligence/people_search_scraper.py search "Adrian Schurr" "San Francisco, CA"
  python scripts/intelligence/people_search_scraper.py detail /person/3431312d506279506d4c3135353330
  python scripts/intelligence/people_search_scraper.py test              # Known contacts test suite
  python scripts/intelligence/people_search_scraper.py batch input.json  # Batch processing
"""

import asyncio
import json
import os
import random
import re
import sys
import time
import argparse
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from dotenv import load_dotenv

load_dotenv()


# ── Configuration ──────────────────────────────────────────────────────

US_STATE_ABBREV = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}

def normalize_state(state: str) -> str:
    """Convert full state name to 2-letter abbreviation. Returns '' for non-US."""
    if not state:
        return ""
    s = state.strip()
    # Already an abbreviation
    if len(s) == 2 and s.upper() in US_STATE_ABBREV.values():
        return s.upper()
    # Full name lookup
    abbrev = US_STATE_ABBREV.get(s.lower())
    return abbrev or ""

NAME_SUFFIXES = re.compile(
    r",?\s*(?:Ph\.?D\.?|MD|JD|MBA|MPA|MPP|MPH|CPA|CFRE|CFA|CSM|Esq\.?|"
    r"Jr\.?|Sr\.?|III|II|IV|LCSW|LMFT|PMP|RN|BSN|DNP|PE|AIA|FAIA|"
    r"Ed\.?D\.?|Ed\.?L\.?D\.?|M\.?Ed\.?|D\.?Min\.?|M\.?Div\.?)\b\.?",
    re.IGNORECASE,
)

# Parenthetical expressions like (she/her/ella), (He/Him), etc.
PARENS = re.compile(r"\s*\([^)]*\)")

def _strip_accents(s: str) -> str:
    """Remove accents/diacritics from Unicode text (e.g., é→e, ñ→n)."""
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def clean_name(name: str) -> str:
    """Remove common suffixes/credentials and parentheticals from a name."""
    name = PARENS.sub("", name)
    name = NAME_SUFFIXES.sub("", name)
    name = _strip_accents(name)
    return name.strip().rstrip(",")

BROWSER_PROFILES = ["chrome131", "chrome136", "chrome124", "chrome120"]
MIN_DELAY = 1.0   # seconds between requests (tested: 0 rate-limit errors at 10 workers)
MAX_DELAY = 2.0
REQUEST_TIMEOUT = 30
MAX_RESULTS_PER_SEARCH = 10
MAX_DETAIL_PAGES = 5  # enrich top N candidates with detail page data
MAX_CONCURRENT_DETAIL = 3  # concurrent detail page fetches


# ── 411.com Scraper ────────────────────────────────────────────────────

class Scraper411:
    """Scrapes 411.com (Whitepages) for multi-result people search.

    Uses curl_cffi with Chrome TLS impersonation — no browser needed.
    Returns multiple candidates per name with full address, phone, age, relatives.
    """

    BASE_URL = "https://www.411.com"

    def __init__(self, proxy: str | None = None):
        self.proxy = proxy
        self._session = cffi_requests.Session(impersonate=random.choice(BROWSER_PROFILES))
        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}
        self.stats = {
            "searches": 0,
            "detail_fetches": 0,
            "candidates_found": 0,
            "errors": 0,
            "rate_limited": 0,
        }

    def _delay(self):
        """Random delay between requests."""
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    def _get(self, url: str) -> cffi_requests.Response | None:
        """Make a GET request with error handling and impersonation rotation."""
        try:
            profile = random.choice(BROWSER_PROFILES)
            resp = self._session.get(url, impersonate=profile, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                self.stats["rate_limited"] += 1
                print(f"    Rate limited, waiting 30s...")
                time.sleep(30)
                return self._session.get(url, impersonate=profile, timeout=REQUEST_TIMEOUT)
            return resp
        except Exception as e:
            print(f"    Request error: {e}")
            self.stats["errors"] += 1
            return None

    # ── Search ───────────────────────────────────────────────────────

    def search(
        self,
        first_name: str,
        last_name: str,
        city: str = "",
        state: str = "",
        max_results: int = MAX_RESULTS_PER_SEARCH,
    ) -> list[dict]:
        """Search 411.com for a person. Returns list of candidates.

        Each candidate dict contains:
          - name, first_name, last_name
          - age (e.g., "30s")
          - city, state
          - detail_url (path to full profile)
          - candidate_rank (1-based)

        Use fetch_detail() on the detail_url to get full address, phones, relatives.
        """
        self.stats["searches"] += 1

        # Clean name suffixes (PhD, CFRE, etc.)
        first_name = clean_name(first_name)
        last_name = clean_name(last_name)
        name = f"{first_name} {last_name}"

        # Normalize state to 2-letter abbreviation
        state = normalize_state(state)

        # Build URL: /name/First-Last/City-ST
        name_slug = f"{first_name}-{last_name}".replace(" ", "-")
        if city and state:
            location_slug = f"/{city}-{state}".replace(" ", "-").replace(",", "")
        elif state:
            location_slug = f"/{state}"
        else:
            location_slug = ""

        url = f"{self.BASE_URL}/name/{name_slug}{location_slug}"

        self._delay()
        resp = self._get(url)
        if not resp or resp.status_code >= 500:
            print(f"    Failed to search for {name}: HTTP {resp.status_code if resp else 'None'}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        candidates = self._parse_search_results(soup, max_results)

        self.stats["candidates_found"] += len(candidates)
        return candidates

    def _parse_search_results(self, soup: BeautifulSoup, max_results: int) -> list[dict]:
        """Parse 411.com search results page.

        Structure (411.com uses Tailwind CSS):
          div.serp-card = card container
            H2 = person name
            H3 = city, state
            A[href="/person/..."] = detail link
          Each person appears twice (mobile + desktop layout) — dedupe by href.
        """
        candidates = []
        seen_urls = set()

        # Find all person detail links
        detail_links = soup.find_all("a", href=re.compile(r"^/person/"))

        for link in detail_links:
            if len(candidates) >= max_results:
                break

            href = link.get("href", "")
            if href in seen_urls:
                continue
            seen_urls.add(href)

            candidate = {
                "detail_url": href,
                "candidate_rank": len(candidates) + 1,
                "source": "411.com",
            }

            # Walk up to find the serp-card container (or any meaningful parent)
            card = link.find_parent("div", class_=re.compile(r"serp-card"))
            if not card:
                # Fallback: walk up through parent divs until we find one with H2
                container = link.parent
                for _ in range(10):
                    if not container or not hasattr(container, "find"):
                        break
                    if container.find("h2"):
                        card = container
                        break
                    container = container.parent

            if not card:
                card = link.parent

            # Find the name (H2 in the card)
            h2 = card.find("h2") if card else None
            if h2:
                full_name = h2.get_text(strip=True)
                candidate["name"] = full_name
                parts = full_name.split()
                if len(parts) >= 2:
                    candidate["first_name"] = parts[0]
                    candidate["last_name"] = " ".join(parts[1:])

            # Find the location (H3 in the card)
            h3 = card.find("h3") if card else None
            if h3:
                location_text = h3.get_text(strip=True)
                loc_parts = location_text.split(",")
                if len(loc_parts) >= 2:
                    candidate["city"] = loc_parts[0].strip()
                    candidate["state"] = loc_parts[1].strip()
                else:
                    candidate["city"] = location_text

            # Age from card text
            if card:
                card_text = card.get_text()
                age_match = re.search(r"Age\s*(\d{1,2}0?s?)", card_text)
                if age_match:
                    candidate["age"] = age_match.group(1)

            if candidate.get("name"):
                candidates.append(candidate)

        return candidates

    # ── Detail Page ──────────────────────────────────────────────────

    def fetch_detail(self, detail_url: str) -> dict:
        """Fetch a person's detail page for full address, phones, relatives.

        Args:
            detail_url: Path like "/person/3431312d506279506d4c3135353330"

        Returns dict with:
          - name, first_name, last_name, age
          - Street Address, Address Locality, Address Region, Postal Code
          - phones (list of landline numbers)
          - relatives (list of {name, age, city, state} dicts)
          - previous_addresses (list of partial address strings)
        """
        self.stats["detail_fetches"] += 1

        if detail_url.startswith("/"):
            url = f"{self.BASE_URL}{detail_url}"
        else:
            url = detail_url

        self._delay()
        resp = self._get(url)
        if resp and resp.status_code == 403:
            # Retry with a fresh session + longer delay (likely rate-limited)
            time.sleep(random.uniform(5, 10))
            self._session = cffi_requests.Session(
                impersonate=random.choice(BROWSER_PROFILES)
            )
            if self.proxy:
                self._session.proxies = {"http": self.proxy, "https": self.proxy}
            resp = self._get(url)
        if not resp or resp.status_code >= 400:
            return {"error": f"HTTP {resp.status_code if resp else 'None'}"}

        soup = BeautifulSoup(resp.text, "html.parser")
        return self._parse_detail_page(soup)

    def _parse_detail_page(self, soup: BeautifulSoup) -> dict:
        """Parse 411.com person detail page.

        Structure:
          H1: "{Full Name} from {City}, {ST}"
          H3 "Current Address": street + city, ST ZIP
          H3 "Landlines": phone numbers
          H3 "Relatives & Associates": name, age, city
        """
        result = {}

        # Name from H1 — has two <span> children: name + "from City, ST"
        h1 = soup.find("h1")
        if h1:
            spans = h1.find_all("span")
            if spans:
                full_name = spans[0].get_text(strip=True)
            else:
                # Fallback: parse combined text
                h1_text = h1.get_text(separator=" ", strip=True)
                match = re.match(r"^(.+)\s+(?:from|in)\s+(.+,\s*[A-Z]{2}.*)$", h1_text)
                full_name = match.group(1).strip() if match else h1_text

            result["name"] = full_name
            parts = full_name.split()
            if len(parts) >= 2:
                result["First Name"] = parts[0]
                result["Last Name"] = " ".join(parts[1:])

        # Parse sections by H3 headings
        sections = {}
        for h3 in soup.find_all("h3"):
            heading = h3.get_text(strip=True).lower()
            # Get content after this heading
            content = []
            for sib in h3.next_siblings:
                if hasattr(sib, "name") and sib.name in ("h2", "h3"):
                    break
                if hasattr(sib, "get_text"):
                    text = sib.get_text(separator="\n", strip=True)
                    if text:
                        content.append(text)
            sections[heading] = "\n".join(content)

        # Age
        page_text = soup.get_text()
        age_match = re.search(r"Age\s*(\d{1,2}0?s?)", page_text)
        if age_match:
            result["Age"] = age_match.group(1)

        # Current address
        addr_content = sections.get("current address", "")
        if addr_content:
            lines = [l.strip() for l in addr_content.split("\n") if l.strip()]
            if lines:
                # First line is typically the street address
                street = lines[0]
                # Filter out "View full address" etc.
                if not any(skip in street.lower() for skip in ["view ", "unlock", "powered"]):
                    result["Street Address"] = street

                # Look for city, state ZIP pattern in subsequent lines
                for line in lines[1:]:
                    csz_match = re.match(
                        r"^([A-Za-z\s]+),?\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?",
                        line,
                    )
                    if csz_match:
                        result["Address Locality"] = csz_match.group(1).strip()
                        result["Address Region"] = csz_match.group(2)
                        if csz_match.group(3):
                            result["Postal Code"] = csz_match.group(3)
                        break

                # Also try combined pattern in first lines
                if "Address Locality" not in result:
                    combined = " ".join(lines[:3])
                    csz_match = re.search(
                        r"([A-Za-z\s]+),\s*([A-Z]{2})\s+(\d{5})", combined
                    )
                    if csz_match:
                        result["Address Locality"] = csz_match.group(1).strip()
                        result["Address Region"] = csz_match.group(2)
                        result["Postal Code"] = csz_match.group(3)

        # Phones (landlines)
        phone_content = sections.get("landlines", "")
        phones = re.findall(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", phone_content)
        if phones:
            result["phones"] = phones

        # Relatives — format: "Name\nAge XXs\nin City, ST\n..." repeating
        relatives_content = sections.get("relatives & associates", "")
        if relatives_content:
            relatives = []
            # Split into lines and group them: name, age, location
            lines = [l.strip() for l in relatives_content.split("\n") if l.strip()]
            i = 0
            while i < len(lines):
                line = lines[i]
                # Skip "View" / "Unlock" UI text
                if any(skip in line.lower() for skip in ["view ", "unlock", "powered"]):
                    i += 1
                    continue
                # A name line: starts with a capital letter, no "Age" or "in "
                if re.match(r"^[A-Z][a-z]", line) and not line.startswith("Age") and not line.startswith("in "):
                    rel = {"name": line}
                    # Check for age on next line
                    if i + 1 < len(lines) and lines[i + 1].startswith("Age"):
                        age_match = re.search(r"(\d{1,2}0?s?)", lines[i + 1])
                        if age_match:
                            rel["age"] = age_match.group(1)
                        i += 1
                    # Check for location on next line
                    if i + 1 < len(lines) and lines[i + 1].startswith("in "):
                        loc = lines[i + 1][3:].strip()
                        loc_match = re.match(r"(.+),\s*([A-Z]{2})", loc)
                        if loc_match:
                            rel["city"] = loc_match.group(1).strip()
                            rel["state"] = loc_match.group(2)
                        i += 1
                    relatives.append(rel)
                i += 1
            if relatives:
                result["relatives"] = relatives

        # Previous addresses
        prev_content = sections.get("previous addresses", "")
        if prev_content:
            prev_addrs = []
            for line in prev_content.split("\n"):
                line = line.strip()
                # Filter out masked/empty entries and UI text
                if any(skip in line.lower() for skip in [
                    "noshow", "view ", "unlock", "full address"
                ]):
                    continue
                if re.search(r"[A-Z]{2}", line) and len(line) > 5:
                    prev_addrs.append(line)
            if prev_addrs:
                result["Previous Addresses"] = prev_addrs

        return result

    # ── High-Level Search + Enrich ───────────────────────────────────

    def search_and_enrich(
        self,
        first_name: str,
        last_name: str,
        city: str = "",
        state: str = "",
        max_results: int = MAX_RESULTS_PER_SEARCH,
        enrich_top_n: int = MAX_DETAIL_PAGES,
    ) -> list[dict]:
        """Search for candidates and enrich top N with detail page data.

        This is the main entry point — equivalent to skip_trace_batch()
        but returning multiple enriched candidates.

        Returns list of candidate dicts with full address, phone, age, relatives.
        """
        name = f"{first_name} {last_name}"
        print(f"    Searching 411.com for: {name}" + (f" ({city}, {state})" if city else ""))

        # Step 1: Get list of candidates from search page
        candidates = self.search(first_name, last_name, city, state, max_results)

        if not candidates:
            print(f"    No candidates found for {name}")
            return []

        print(f"    Found {len(candidates)} candidates")

        # Step 2: Enrich top N candidates with detail page data
        enriched = []
        for i, candidate in enumerate(candidates[:enrich_top_n]):
            detail_url = candidate.get("detail_url")
            if not detail_url:
                enriched.append(candidate)
                continue

            detail = self.fetch_detail(detail_url)

            if "error" in detail:
                print(f"      Candidate {i + 1}: detail page error: {detail['error']}")
                enriched.append(candidate)
                continue

            # Merge detail into candidate (detail takes precedence for richer data)
            merged = {**candidate, **detail}
            # Preserve candidate_rank from search
            merged["candidate_rank"] = candidate["candidate_rank"]

            addr = merged.get("Street Address", "")
            city_r = merged.get("Address Locality", "")
            state_r = merged.get("Address Region", "")
            age = merged.get("Age", "?")
            print(f"      #{i + 1}: {merged.get('name', '?')}, Age {age}, "
                  f"{addr}, {city_r}, {state_r}")
            enriched.append(merged)

        # Append remaining candidates without enrichment
        for candidate in candidates[enrich_top_n:]:
            enriched.append(candidate)

        return enriched


# ── Batch Processing ─────────────────────────────────────────────────

def search_batch(
    contacts: list[dict],
    proxy: str | None = None,
    max_results: int = MAX_RESULTS_PER_SEARCH,
    enrich_top_n: int = MAX_DETAIL_PAGES,
) -> dict[int, list[dict]]:
    """Search for multiple contacts sequentially.

    Args:
        contacts: list of dicts with first_name, last_name, city, state, id
        proxy: optional proxy URL
        max_results: max candidates per search
        enrich_top_n: enrich top N candidates with detail page data

    Returns:
        dict mapping contact_id -> list of candidates
    """
    results = {}
    scraper = Scraper411(proxy=proxy)

    for i, contact in enumerate(contacts):
        cid = contact.get("id", i)
        fname = contact.get("first_name", "")
        lname = contact.get("last_name", "")
        city = contact.get("city", "")
        state = contact.get("state", "")

        print(f"\n  [{i + 1}/{len(contacts)}] {fname} {lname} (id={cid})")

        candidates = scraper.search_and_enrich(
            fname, lname, city, state,
            max_results=max_results,
            enrich_top_n=enrich_top_n,
        )

        results[cid] = candidates
        print(f"    → {len(candidates)} candidates returned")

    print(f"\n  Scraper stats: {scraper.stats}")
    return results


# ── GPT-5 Mini Multi-Candidate Validation ─────────────────────────────

def validate_candidates(
    contact: dict,
    candidates: list[dict],
    openai_client,
) -> dict:
    """Use GPT-5 mini to pick the best candidate from the 411.com results.

    Args:
        contact: dict with first_name, last_name, city, state, company, etc.
        candidates: list of enriched candidate dicts from 411.com
        openai_client: OpenAI client instance

    Returns:
        dict with:
          - best_candidate_index (0-based, or null if none match)
          - confidence: high/medium/low
          - reasoning: explanation
    """
    if not candidates:
        return {"best_candidate_index": None, "confidence": "no_results", "reasoning": "No candidates found"}

    # Build contact profile
    contact_profile = (
        f"Name: {contact.get('first_name', '')} {contact.get('last_name', '')}\n"
        f"Known City: {contact.get('city', 'Unknown')}, State: {contact.get('state', 'Unknown')}\n"
        f"Current Position: {contact.get('position', 'Unknown')} at {contact.get('company', 'Unknown')}\n"
    )

    # Add employment history if available
    employment = contact.get("enrich_employment")
    if employment and isinstance(employment, list):
        jobs = []
        for emp in employment[:5]:
            if isinstance(emp, dict):
                co = emp.get("company_name", "") or emp.get("companyName", "")
                title = emp.get("job_title", "") or emp.get("title", "")
                if co or title:
                    jobs.append(f"  - {title} at {co}")
        if jobs:
            contact_profile += "Employment:\n" + "\n".join(jobs) + "\n"

    education = contact.get("enrich_education")
    if education and isinstance(education, list):
        schools = []
        for edu in education[:3]:
            if isinstance(edu, dict):
                school = edu.get("school_name", "") or edu.get("schoolName", "")
                if school:
                    schools.append(f"  - {school}")
        if schools:
            contact_profile += "Education:\n" + "\n".join(schools) + "\n"

    # Build candidates description
    candidates_text = ""
    for i, c in enumerate(candidates):
        addr = ", ".join(filter(None, [
            c.get("Street Address", ""),
            c.get("Address Locality", ""),
            c.get("Address Region", ""),
            c.get("Postal Code", ""),
        ]))
        phones = ", ".join(c.get("phones", [])[:3]) if c.get("phones") else "N/A"

        candidates_text += f"\nCandidate {i + 1}: {c.get('name', '?')}"
        candidates_text += f"\n  Age: {c.get('Age', c.get('age', '?'))}"
        candidates_text += f"\n  Address: {addr or 'N/A'}"
        candidates_text += f"\n  City from search: {c.get('city', '?')}, {c.get('state', '?')}"
        candidates_text += f"\n  Phones: {phones}"

        if c.get("relatives"):
            rel_strs = [f"{r['name']} ({r.get('age', '?')}, {r.get('city', '?')} {r.get('state', '?')})"
                        for r in c["relatives"][:5]]
            candidates_text += f"\n  Relatives: {'; '.join(rel_strs)}"
        candidates_text += "\n"

    prompt = f"""You are verifying people-search results against a LinkedIn contact profile.

CONTACT PROFILE (what we know):
{contact_profile}

CANDIDATES FROM 411.COM ({len(candidates)} found):
{candidates_text}

Determine which candidate (if any) is the CORRECT person matching our contact. Consider:
1. Name match: exact match, middle name present, nickname, maiden name
2. Location: Is their address in or near the contact's known city? Bay Area suburbs are consistent with SF.
3. Age: Does the age bracket match their career stage? (e.g., 30s for early career, 50s for senior)
4. Red flags: completely wrong state, implausible age, different name spelling

Respond in JSON:
{{
  "best_candidate_index": <1-based index, or null if none match>,
  "confidence": "high" | "medium" | "low",
  "reasoning": "1-2 sentence explanation"
}}"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)

        # Convert 1-based index to 0-based
        idx = result.get("best_candidate_index")
        if idx is not None and isinstance(idx, int):
            result["best_candidate_index"] = idx - 1  # Convert to 0-based

        return result
    except Exception as e:
        return {"error": str(e), "best_candidate_index": None, "confidence": "error"}


# ── CLI ──────────────────────────────────────────────────────────────

def cmd_search(name: str, location: str):
    """Search 411.com and display enriched candidates."""
    parts = name.strip().split(None, 1)
    first = parts[0] if parts else ""
    last = parts[1] if len(parts) > 1 else ""

    loc_parts = [p.strip() for p in location.split(",")]
    city = loc_parts[0] if loc_parts else ""
    state = loc_parts[1].strip() if len(loc_parts) > 1 else ""

    scraper = Scraper411()
    candidates = scraper.search_and_enrich(first, last, city, state)

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {first} {last}" + (f" ({city}, {state})" if city else ""))
    print(f"{'=' * 60}")
    print(f"Found {len(candidates)} candidates\n")

    for c in candidates:
        addr = ", ".join(filter(None, [
            c.get("Street Address", ""),
            c.get("Address Locality", ""),
            c.get("Address Region", ""),
            c.get("Postal Code", ""),
        ]))
        print(f"  #{c.get('candidate_rank', '?')}: {c.get('name', '?')}")
        print(f"     Age: {c.get('Age', c.get('age', '?'))}")
        print(f"     Address: {addr or 'N/A'}")
        if c.get("phones"):
            print(f"     Phones: {', '.join(c['phones'][:3])}")
        if c.get("relatives"):
            for r in c["relatives"][:3]:
                print(f"     Relative: {r['name']}, {r.get('age', '?')}, "
                      f"{r.get('city', '?')} {r.get('state', '?')}")
        print()

    # JSON output
    print("\n--- JSON ---")
    print(json.dumps(candidates, indent=2, default=str))

    return candidates


def cmd_detail(detail_path: str):
    """Fetch a specific person detail page."""
    scraper = Scraper411()
    detail = scraper.fetch_detail(detail_path)
    print(json.dumps(detail, indent=2, default=str))
    return detail


def cmd_test():
    """Test with known contacts from the real estate batch."""
    test_contacts = [
        {"id": 1, "first_name": "Adrian", "last_name": "Schurr",
         "city": "San Francisco", "state": "CA"},
        {"id": 2, "first_name": "Taj", "last_name": "James",
         "city": "Oakland", "state": "CA"},
        {"id": 3, "first_name": "Rob", "last_name": "Gitin",
         "city": "San Francisco", "state": "CA"},
        {"id": 4, "first_name": "Jeff", "last_name": "Kositsky",
         "city": "Denver", "state": "CO"},
        {"id": 5, "first_name": "Trina", "last_name": "Villanueva",
         "city": "Oakland", "state": "CA"},
    ]

    # Known correct answers from the validated real estate batch
    known_addresses = {
        1: "1873 Wayne Ave, San Leandro, CA",    # Adrian Schurr
        2: "4347 Leach Ave, Oakland, CA",          # Taj James
        3: "177 Granada Ave, San Francisco, CA",   # Rob Gitin
        4: "749 S Grant St, Denver, CO",           # Jeff Kositsky
        5: "4629 Mountain Blvd, Oakland, CA",      # Trina Villanueva
    }

    print("=" * 60)
    print("PEOPLE SEARCH SCRAPER — TEST SUITE (411.com)")
    print(f"Testing {len(test_contacts)} contacts with known addresses")
    print("=" * 60)

    results = search_batch(
        test_contacts,
        max_results=5,
        enrich_top_n=3,
    )

    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    matches = 0
    for cid, candidates in results.items():
        contact = next(c for c in test_contacts if c["id"] == cid)
        name = f"{contact['first_name']} {contact['last_name']}"
        known = known_addresses.get(cid, "")

        found_match = False
        for c in candidates:
            addr = c.get("Street Address", "")
            if addr and known and addr.lower() in known.lower():
                found_match = True
                break

        status = "MATCH" if found_match else "NO MATCH"
        if found_match:
            matches += 1

        print(f"\n  {name}: {len(candidates)} candidates — {status}")
        print(f"    Known: {known}")
        for c in candidates[:3]:
            addr = ", ".join(filter(None, [
                c.get("Street Address", ""),
                c.get("Address Locality", ""),
                c.get("Address Region", ""),
            ]))
            age = c.get("Age", c.get("age", "?"))
            print(f"    #{c.get('candidate_rank')}: {c.get('name', '?')}, "
                  f"Age {age}, {addr}")

    print(f"\n  Overall: {matches}/{len(test_contacts)} address matches found")
    print(f"  Match rate: {matches / len(test_contacts) * 100:.0f}%")

    # Save full results
    outfile = "/tmp/411_scraper_test_results.json"
    with open(outfile, "w") as f:
        json.dump({str(k): v for k, v in results.items()}, f, indent=2, default=str)
    print(f"\n  Full results saved to: {outfile}")


def main():
    parser = argparse.ArgumentParser(
        description="Custom People Search Scraper — multi-result via 411.com"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Search
    s = subparsers.add_parser("search", help="Search and enrich candidates")
    s.add_argument("name", help='Full name, e.g. "Adrian Schurr"')
    s.add_argument("location", nargs="?", default="",
                   help='City, ST, e.g. "San Francisco, CA"')

    # Detail
    d = subparsers.add_parser("detail", help="Fetch a person detail page")
    d.add_argument("path", help='Detail URL path, e.g. /person/3431312d...')

    # Test
    subparsers.add_parser("test", help="Run test suite with known contacts")

    # Batch
    b = subparsers.add_parser("batch", help="Batch process contacts from JSON")
    b.add_argument("file", help="JSON file with contacts array")
    b.add_argument("--max-results", type=int, default=10)
    b.add_argument("--enrich-top", type=int, default=5)

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args.name, args.location)
    elif args.command == "detail":
        cmd_detail(args.path)
    elif args.command == "test":
        cmd_test()
    elif args.command == "batch":
        with open(args.file) as f:
            contacts = json.load(f)
        results = search_batch(
            contacts,
            max_results=args.max_results,
            enrich_top_n=args.enrich_top,
        )
        print(json.dumps({str(k): v for k, v in results.items()}, indent=2, default=str))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
