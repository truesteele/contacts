#!/usr/bin/env python3
"""
Network Intelligence — SEC EDGAR Filing Enrichment

Searches SEC EDGAR's full-text search API (EFTS) for contacts appearing in
SEC filings — primarily Form D (private placements) and Forms 3/4/5 (insider
ownership). Uses GPT-5 mini to validate matches against the contact's LinkedIn
profile, eliminating false positives from common names.

EDGAR EFTS is free, no API key needed — just a User-Agent header with contact info.
Only cost is GPT-5 mini validation at ~$0.001/contact.

Usage:
  python enrich_edgar_filings.py --test                    # 1 contact
  python enrich_edgar_filings.py --batch 10                # 10 contacts
  python enrich_edgar_filings.py --segment ready_now       # Only ready_now tier
  python enrich_edgar_filings.py --segment all             # ready_now + top cultivate_first
  python enrich_edgar_filings.py --ids 123,456             # Specific contacts
  python enrich_edgar_filings.py --force                   # Re-search already searched
"""

import os
import json
import time
import argparse
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from supabase import create_client, Client

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────

EDGAR_USER_AGENT = "TrueSteele LLC justin@truesteele.com"
EDGAR_HEADERS = {
    "User-Agent": EDGAR_USER_AGENT,
    "Accept": "application/json",
}
EDGAR_XML_HEADERS = {
    "User-Agent": EDGAR_USER_AGENT,
    "Accept": "application/xml",
}
EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"

EDGAR_SEARCH_DELAY = 0.25  # seconds between EFTS requests
EDGAR_XML_DELAY = 0.15     # seconds between XML fetches
MAX_FILINGS_TO_CHECK = 20  # max filings from EFTS to examine
MAX_XML_FETCHES = 8        # max Form D XMLs to fetch per contact

GPT_MODEL = "gpt-5-mini"

SELECT_COLS = (
    "id, first_name, last_name, company, position, headline, "
    "city, state, familiarity_rating, ai_capacity_tier, "
    "enrich_employment, "
    "ask_readiness, edgar_data"
)


# ── GPT-5 mini Structured Output Schema ──────────────────────────────

class MatchedFiling(BaseModel):
    form_type: str = Field(description="SEC form type: D, D/A, 3, 4, or 5")
    company_name: str = Field(description="Company name from the filing")
    cik: str = Field(description="CIK number")
    file_date: str = Field(description="Filing date YYYY-MM-DD")
    role: str = Field(description="Person's role: Director, Executive Officer, Promoter, 10% Owner, or combination")
    accession: str = Field(description="Accession number of the filing")

class EdgarMatchResult(BaseModel):
    is_match: bool = Field(description="True if ANY of the filings genuinely involve this specific person (not a different person with the same name)")
    match_confidence: str = Field(description="high, medium, or low — how confident this is the same person?")
    match_reasoning: str = Field(description="2-3 sentences explaining the match/no-match decision, citing specific evidence: career overlap, geography, name variations, industry mismatch")
    matched_filings: list[MatchedFiling] = Field(default_factory=list, description="Only filings confirmed to involve this specific person. Empty if no match.")
    investor_signal: str = Field(description="strong, moderate, weak, or none — how strong is the evidence this person is an angel investor or has investment activity?")
    investor_summary: Optional[str] = Field(default=None, description="2-3 sentence summary of their SEC filing activity and what it implies about investment behavior. Only if matched.")


MATCH_SYSTEM_PROMPT = """You are a data matching specialist. Your job is to determine whether SEC EDGAR filings genuinely involve a specific person, or are false positives from a different person with the same name.

MATCHING RULES:
- The CONTACT has a name, company, position, headline, city/state, and employment history from LinkedIn
- The FILINGS have form types, company names, filing dates, and sometimes person details (names, addresses, roles) from Form D XMLs
- A MATCH means the filing genuinely involves the SAME PERSON as the contact
- Cross-reference these signals to validate:

  1. NAME: Does the name match exactly? EDGAR may use middle names (e.g., "Lansing Tyler Scriven" = "Tyler Scriven"). First + last name must match. Middle name differences are OK.

  2. CAREER: Is the filing company compatible with this person's career? A filing for "RoadSync Inc" makes sense for Tyler Scriven (co-founder of Saltbox/RoadSync). A filing for "Bank of America Mortgage Trust" does NOT make sense for John Grossman at "Third Sector Capital Partners".

  3. GEOGRAPHY: Does the filing address (if available from Form D XML) match the contact's city/state? Not a hard requirement — people invest across states — but a mismatch with no career connection is suspicious.

  4. INDUSTRY: Is the filing industry consistent? If the contact works in social impact/nonprofit tech but filings are all commercial mortgage finance, that's a strong negative signal.

  5. TIMING: Do filing dates align with the person's career timeline?

FALSE POSITIVE INDICATORS (reject the match):
- Different industry entirely (contact in nonprofit, filings in commercial mortgage)
- Filings in a geography with no career connection
- Filing company names that don't appear anywhere in the contact's employment history
- The contact works at a large organization and the filing is for a completely unrelated entity

INVESTOR SIGNAL CLASSIFICATION:
- strong: 3+ Form D filings as Director/Promoter across different companies (serial investor or serial entrepreneur)
- moderate: 1-2 Form D filings, or insider filings (Forms 3/4/5) at public companies
- weak: Only appears as Executive Officer at their own company (operator, not investor)
- none: No matched filings

IMPORTANT: When in doubt about identity, err on the side of NO MATCH. False positives are much worse than false negatives — we don't want to attribute investment activity to the wrong person."""


class EdgarEnricher:
    def __init__(self, test_mode=False, batch_size=None, segment="all",
                 force=False, min_score=70, workers=5, ids=None):
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.segment = segment
        self.force = force
        self.min_score = min_score
        self.workers = workers
        self.ids = ids
        self.supabase: Client | None = None
        self.openai: OpenAI | None = None
        self._lock = threading.Lock()
        self._edgar_lock = threading.Lock()  # serialize EDGAR requests
        self.stats = {
            "searched": 0,
            "matched": 0,
            "no_match": 0,
            "no_results": 0,
            "errors": 0,
            "filings_found": 0,
            "xmls_fetched": 0,
            "gpt_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "strong_signals": 0,
            "moderate_signals": 0,
            "weak_signals": 0,
        }

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        openai_key = os.environ.get("OPENAI_APIKEY")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        if not openai_key:
            print("ERROR: Missing OPENAI_APIKEY")
            return False

        self.supabase = create_client(url, key)
        self.openai = OpenAI(api_key=openai_key)
        print("Connected to Supabase and OpenAI")
        return True

    def get_contacts(self) -> list[dict]:
        """Fetch contacts that need EDGAR enrichment."""
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                self.supabase.table("contacts")
                .select(SELECT_COLS)
                .not_.is_("ask_readiness", "null")
                .order("id")
                .range(offset, offset + page_size - 1)
            )
            page = query.execute().data
            if not page:
                break
            all_contacts.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        # If --ids provided, filter to those specific contacts
        if self.ids:
            id_set = set(self.ids)
            filtered = [c for c in all_contacts if c["id"] in id_set]
            if not self.force:
                filtered = [c for c in filtered if not c.get("edgar_data")]
        else:
            filtered = []
            for c in all_contacts:
                ar = c.get("ask_readiness") or {}
                if isinstance(ar, str):
                    ar = json.loads(ar)
                ka = ar.get("kindora_angel_investment") or {}
                tier = ka.get("tier")
                score = ka.get("score", 0)

                if not self.force and c.get("edgar_data"):
                    continue

                if self.segment == "ready_now":
                    if tier == "ready_now":
                        filtered.append(c)
                elif self.segment == "cultivate":
                    if tier == "cultivate_first" and score >= self.min_score:
                        filtered.append(c)
                elif self.segment == "all":
                    if tier == "ready_now" or (tier == "cultivate_first" and score >= self.min_score):
                        filtered.append(c)

        if self.test_mode:
            filtered = filtered[:1]
        elif self.batch_size:
            filtered = filtered[:self.batch_size]

        return filtered

    def search_edgar(self, full_name: str) -> tuple[int, list[dict]]:
        """Search EDGAR EFTS for a person's name.
        Returns (total_count, hits_list). EFTS search-index doesn't support
        form filtering — we filter client-side."""
        with self._edgar_lock:
            time.sleep(EDGAR_SEARCH_DELAY)

        try:
            r = requests.get(
                EFTS_BASE,
                params={"q": f'"{full_name}"'},
                headers=EDGAR_HEADERS,
                timeout=15,
            )
            if r.status_code != 200:
                print(f"    EDGAR search failed: {r.status_code}")
                return 0, []

            data = r.json()
            total = data.get("hits", {}).get("total", {}).get("value", 0)
            hits = data.get("hits", {}).get("hits", [])

            # Filter to investor-relevant form types client-side
            investor_forms = {"D", "D/A", "3", "4", "5"}
            filtered = [h for h in hits if h.get("_source", {}).get("form", "") in investor_forms]

            # Also keep all hits for GPT context (non-investor forms still inform identity)
            # but prioritize investor forms
            non_investor = [h for h in hits if h.get("_source", {}).get("form", "") not in investor_forms]
            all_hits = filtered + non_investor

            return total, all_hits[:MAX_FILINGS_TO_CHECK]

        except Exception as e:
            print(f"    EDGAR search error: {e}")
            return 0, []

    def fetch_form_d_xml(self, cik: str, accession: str) -> list[dict]:
        """Fetch Form D XML and extract related persons.
        Returns list of person dicts with name, address, roles."""
        with self._edgar_lock:
            time.sleep(EDGAR_XML_DELAY)

        # Accession format: "0001234567-18-000001" → "000123456718000001"
        accession_nodash = accession.replace("-", "")
        url = f"{SEC_ARCHIVES}/{cik}/{accession_nodash}/primary_doc.xml"

        try:
            r = requests.get(url, headers=EDGAR_XML_HEADERS, timeout=15)
            if r.status_code != 200:
                return []

            root = ET.fromstring(r.content)

            # Handle XML namespaces — Form D uses various namespaces
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"

            persons = []
            for person_info in root.iter(f"{ns}relatedPersonInfo"):
                name_el = person_info.find(f"{ns}relatedPersonName")
                addr_el = person_info.find(f"{ns}relatedPersonAddress")
                rel_el = person_info.find(f"{ns}relationshipList")

                person = {}
                if name_el is not None:
                    person["firstName"] = (name_el.findtext(f"{ns}firstName") or "").strip()
                    person["middleName"] = (name_el.findtext(f"{ns}middleName") or "").strip()
                    person["lastName"] = (name_el.findtext(f"{ns}lastName") or "").strip()

                if addr_el is not None:
                    person["city"] = (addr_el.findtext(f"{ns}city") or "").strip()
                    person["state"] = (addr_el.findtext(f"{ns}stateOrCountry") or "").strip()

                if rel_el is not None:
                    roles = []
                    if rel_el.findtext(f"{ns}isDirector") == "true":
                        roles.append("Director")
                    if rel_el.findtext(f"{ns}isOfficer") == "true":
                        roles.append("Executive Officer")
                    if rel_el.findtext(f"{ns}isPromoter") == "true":
                        roles.append("Promoter")
                    if rel_el.findtext(f"{ns}isTenPercentOwner") == "true":
                        roles.append("10% Owner")
                    person["roles"] = roles

                if person.get("lastName"):
                    persons.append(person)

            self._update_stat("xmls_fetched")
            return persons

        except Exception as e:
            print(f"    XML fetch error for {url}: {e}")
            return []

    def build_filing_context(self, hits: list[dict], contact: dict) -> str:
        """Build a text summary of EDGAR filings for GPT evaluation.
        Fetches Form D XMLs to get person-level detail."""
        first = contact["first_name"].lower()
        last = contact["last_name"].lower()

        filing_texts = []
        xml_count = 0

        for i, hit in enumerate(hits):
            source = hit.get("_source", {})
            form = source.get("form", "")
            display_names = source.get("display_names", [])
            ciks = source.get("ciks", [])
            file_date = source.get("file_date", "")
            biz_locations = source.get("biz_locations", [])
            accession = source.get("adsh", "")

            company = display_names[0] if display_names else "Unknown"
            cik = ciks[0] if ciks else ""
            location = biz_locations[0] if biz_locations else ""

            filing_text = (
                f"\n--- Filing [{i}] ---\n"
                f"Form: {form}\n"
                f"Company: {company}\n"
                f"CIK: {cik}\n"
                f"Filed: {file_date}\n"
                f"Location: {location}\n"
                f"Accession: {accession}\n"
            )

            # For Form D/D/A, fetch XML to get related persons
            if form in ("D", "D/A") and cik and accession and xml_count < MAX_XML_FETCHES:
                persons = self.fetch_form_d_xml(cik, accession)
                if persons:
                    filing_text += "Related Persons:\n"
                    for p in persons:
                        name = f"{p.get('firstName', '')} {p.get('middleName', '')} {p.get('lastName', '')}".strip()
                        name = " ".join(name.split())  # normalize whitespace
                        city = p.get("city", "")
                        state = p.get("state", "")
                        roles = ", ".join(p.get("roles", []))
                        filing_text += f"  - {name} ({city}, {state}) — {roles}\n"
                xml_count += 1

            filing_texts.append(filing_text)

        return "".join(filing_texts)

    def evaluate_match(self, contact: dict, hits: list[dict]) -> EdgarMatchResult | None:
        """Use GPT-5 mini to evaluate whether EDGAR filings match this contact."""
        # Build contact context
        employment = contact.get("enrich_employment")
        if isinstance(employment, str):
            try:
                employment = json.loads(employment)
            except (json.JSONDecodeError, TypeError):
                employment = None

        emp_summary = ""
        if employment and isinstance(employment, list):
            for job in employment[:5]:
                if isinstance(job, dict):
                    co = job.get("companyName", "")
                    title = job.get("title", "")
                    emp_summary += f"  - {title} at {co}\n"

        contact_info = (
            f"CONTACT: {contact['first_name']} {contact['last_name']}\n"
            f"Company: {contact.get('company') or 'N/A'}\n"
            f"Position: {contact.get('position') or 'N/A'}\n"
            f"Headline: {contact.get('headline') or 'N/A'}\n"
            f"City/State: {contact.get('city') or 'N/A'}, {contact.get('state') or 'N/A'}\n"
        )
        if emp_summary:
            contact_info += f"Employment History:\n{emp_summary}"

        filings_text = self.build_filing_context(hits, contact)

        prompt = (
            f"{contact_info}\n"
            f"SEC EDGAR FILINGS ({len(hits)} results):\n"
            f"{filings_text}"
        )

        try:
            resp = self.openai.responses.parse(
                model=GPT_MODEL,
                instructions=MATCH_SYSTEM_PROMPT,
                input=prompt,
                text_format=EdgarMatchResult,
            )
            self._update_stat("gpt_calls")
            if resp.usage:
                self._update_stat("input_tokens", resp.usage.input_tokens)
                self._update_stat("output_tokens", resp.usage.output_tokens)

            result = resp.output_parsed
            if not result:
                print("    Warning: GPT returned no parsed output")
                return None

            return result

        except Exception as e:
            print(f"    GPT evaluation error: {e}")
            return None

    def build_edgar_data(self, result: EdgarMatchResult) -> dict:
        """Build the JSONB data from GPT match result."""
        filings = []
        for f in result.matched_filings:
            filings.append({
                "form_type": f.form_type,
                "company_name": f.company_name,
                "cik": f.cik,
                "file_date": f.file_date,
                "role": f.role,
                "accession": f.accession,
            })

        signal = result.investor_signal
        if signal == "strong":
            self._update_stat("strong_signals")
        elif signal == "moderate":
            self._update_stat("moderate_signals")
        elif signal == "weak":
            self._update_stat("weak_signals")

        return {
            "status": "matched",
            "searched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "matched_filings_count": len(filings),
            "filings": filings,
            "match_confidence": result.match_confidence,
            "match_reasoning": result.match_reasoning,
            "investor_signal": signal,
            "investor_summary": result.investor_summary,
        }

    def save_result(self, contact_id: int, data: dict):
        """Save edgar_data to Supabase."""
        try:
            self.supabase.table("contacts").update({
                "edgar_data": data,
            }).eq("id", contact_id).execute()
        except Exception as e:
            print(f"    ERROR saving to DB: {e}")
            self._update_stat("errors")

    def _update_stat(self, key: str, delta: int = 1):
        with self._lock:
            self.stats[key] += delta

    def process_contact(self, contact: dict):
        """Search EDGAR for a single contact and save results."""
        name = f"{contact['first_name']} {contact['last_name']}"
        cid = contact["id"]

        with self._lock:
            idx = self.stats["searched"] + self.stats["no_results"] + self.stats["no_match"] + self.stats["errors"] + 1
            print(f"\n  [{idx}] {name} (id={cid})")

        # Search EDGAR by full name
        total, hits = self.search_edgar(name)

        if total == 0:
            with self._lock:
                print(f"    [{name}] No EDGAR filings found")
            self._update_stat("no_results")
            self.save_result(cid, {
                "status": "no_results",
                "searched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })
            return

        self._update_stat("searched")
        self._update_stat("filings_found", total)

        with self._lock:
            print(f"    [{name}] {total} filings found, evaluating top {len(hits)}...")

        # Use GPT-5 mini to validate matches
        result = self.evaluate_match(contact, hits)

        if result is None:
            self._update_stat("errors")
            self.save_result(cid, {
                "status": "error",
                "searched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "error": "GPT evaluation failed",
            })
            return

        if result.is_match and result.matched_filings:
            data = self.build_edgar_data(result)
            with self._lock:
                print(f"    [{name}] MATCH ({result.match_confidence}): "
                      f"{len(result.matched_filings)} filings | "
                      f"Signal: {result.investor_signal}")
                if result.investor_summary:
                    print(f"      {result.investor_summary}")
            self._update_stat("matched")
            self.save_result(cid, data)
        else:
            with self._lock:
                print(f"    [{name}] No match in {len(hits)} filings")
            self._update_stat("no_match")
            self.save_result(cid, {
                "status": "no_match",
                "searched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "total_filings_checked": len(hits),
                "no_match_reasoning": result.match_reasoning,
            })

    def run(self):
        """Main enrichment loop."""
        if not self.connect():
            return

        contacts = self.get_contacts()
        print(f"\nTarget contacts: {len(contacts)} ({self.segment})")

        if not contacts:
            print("No contacts to process.")
            return

        print(f"Cost: FREE (EDGAR) + ~${len(contacts) * 0.001:.2f} GPT validation")
        print(f"Estimated time: ~{len(contacts) * 2 / 60:.1f} minutes")

        start = time.time()

        # Sequential EDGAR requests (polite to SEC), but GPT calls happen within each
        for contact in contacts:
            self.process_contact(contact)

        elapsed = time.time() - start

        # Summary
        print(f"\n{'='*60}")
        print(f"SEC EDGAR Enrichment Complete")
        print(f"{'='*60}")
        print(f"  Contacts processed: {self.stats['searched'] + self.stats['no_results']}")
        print(f"  Had filings:   {self.stats['searched']}")
        print(f"  No filings:    {self.stats['no_results']}")
        print(f"  Matched:       {self.stats['matched']}")
        print(f"  No match (false positive rejected): {self.stats['no_match']}")
        print(f"  Errors:        {self.stats['errors']}")
        print(f"  Total filings found: {self.stats['filings_found']}")
        print(f"  XMLs fetched:  {self.stats['xmls_fetched']}")
        print(f"  GPT calls:     {self.stats['gpt_calls']}")
        print(f"  GPT tokens:    {self.stats['input_tokens']:,} in / {self.stats['output_tokens']:,} out")
        gpt_cost = (self.stats['input_tokens'] * 0.4 + self.stats['output_tokens'] * 1.6) / 1_000_000
        print(f"  Est. cost:     ~${gpt_cost:.2f} (GPT only, EDGAR is free)")
        print(f"  Runtime:       {elapsed:.0f}s ({elapsed/60:.1f}m)")
        print(f"\n  Signal breakdown:")
        print(f"    Strong:   {self.stats['strong_signals']}")
        print(f"    Moderate: {self.stats['moderate_signals']}")
        print(f"    Weak:     {self.stats['weak_signals']}")


def main():
    parser = argparse.ArgumentParser(
        description="Enrich contacts with SEC EDGAR filing data"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only 1 contact for validation")
    parser.add_argument("--batch", "-b", type=int, default=None,
                        help="Process N contacts")
    parser.add_argument("--segment", "-s", type=str, default="all",
                        choices=["ready_now", "cultivate", "all"],
                        help="Which tier to search (default: all)")
    parser.add_argument("--min-score", type=int, default=70,
                        help="Minimum angel score for cultivate_first (default: 70)")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-search contacts that already have edgar_data")
    parser.add_argument("--workers", "-w", type=int, default=5,
                        help="Not used (EDGAR requests are sequential), kept for CLI consistency")
    parser.add_argument("--ids", type=str, default=None,
                        help="Comma-separated contact IDs to search")

    args = parser.parse_args()

    ids = None
    if args.ids:
        ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]

    enricher = EdgarEnricher(
        test_mode=args.test,
        batch_size=args.batch,
        segment=args.segment,
        force=args.force,
        min_score=args.min_score,
        workers=args.workers,
        ids=ids,
    )
    enricher.run()


if __name__ == "__main__":
    main()
