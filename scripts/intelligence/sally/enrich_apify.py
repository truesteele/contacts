#!/usr/bin/env python3
"""
Sally Contacts — Apify LinkedIn Enrichment Script

Enriches Sally's contacts with LinkedIn URLs using the Apify
harvestapi/linkedin-profile-scraper actor.

Adapted from scripts/enrichment/enrich_contacts_apify.py for Sally's tables.

Usage:
  python scripts/intelligence/sally/enrich_apify.py --test          # Test with 1 contact
  python scripts/intelligence/sally/enrich_apify.py --batch 50      # Process 50 contacts
  python scripts/intelligence/sally/enrich_apify.py                 # Full run (all contacts)
  python scripts/intelligence/sally/enrich_apify.py --force         # Re-enrich already enriched
  python scripts/intelligence/sally/enrich_apify.py --contact-id 42 # Enrich specific contact
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, date
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote
from dotenv import load_dotenv
from supabase import create_client, Client
from apify_client import ApifyClient

load_dotenv()

# Sally's table
TABLE = "sally_contacts"

# Columns that exist in sally_contacts for enrichment writes
VALID_COLUMNS = {
    "headline", "summary", "company", "position", "linkedin_username",
    "city", "state",
    "enrich_current_company", "enrich_current_title", "enrich_current_since",
    "enrich_years_in_current_role", "enrich_total_experience_years",
    "enrich_follower_count", "enrich_connections",
    "enrich_schools", "enrich_companies_worked", "enrich_titles_held",
    "enrich_skills", "enrich_board_positions", "enrich_volunteer_orgs",
    "enrich_employment", "enrich_education",
    "enriched_at", "enrichment_source",
}


class SallyContactsEnricher:
    PROFILE_ACTOR = "harvestapi/linkedin-profile-scraper"

    def __init__(self, test_mode=False, batch_size=None, start_from=None,
                 force=False, ids=None, contact_id=None):
        self.supabase: Optional[Client] = None
        self.apify: Optional[ApifyClient] = None
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.start_from = start_from
        self.force = force
        self.ids = ids
        self.contact_id = contact_id
        self.stats = {
            "profiles_enriched": 0,
            "profiles_failed": 0,
            "profiles_skipped": 0,
            "apify_errors": 0,
            "db_errors": 0,
        }

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        apify_key = os.environ.get("APIFY_TOKEN") or os.environ.get("APIFY_API_KEY")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        if not apify_key:
            print("ERROR: Missing APIFY_TOKEN or APIFY_API_KEY")
            return False

        self.supabase = create_client(url, key)
        self.apify = ApifyClient(apify_key)
        print("Connected to Supabase and Apify")
        return True

    def get_contacts(self) -> List[Dict]:
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                self.supabase.table(TABLE)
                .select("id, first_name, last_name, linkedin_url, enriched_at, enrichment_source")
                .neq("linkedin_url", "")
                .not_.is_("linkedin_url", "null")
                .order("id")
                .range(offset, offset + page_size - 1)
            )

            if self.contact_id:
                query = query.eq("id", self.contact_id)

            if self.ids:
                query = query.in_("id", self.ids)

            if self.start_from:
                query = query.gte("id", self.start_from)

            if not self.force:
                query = query.or_("enrichment_source.is.null,enrichment_source.neq.apify")

            response = query.execute()
            page = response.data
            if not page:
                break

            all_contacts.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        if self.batch_size:
            all_contacts = all_contacts[:self.batch_size]

        return all_contacts

    # ── URL Normalization ─────────────────────────────────────────────

    def _normalize_linkedin_url(self, url: str) -> str:
        url = url.strip().rstrip("/")
        url = unquote(url)
        if not url.startswith("http"):
            url = "https://" + url
        url = url.replace("://linkedin.com/", "://www.linkedin.com/")
        return url

    # ── Profile Enrichment ──────────────────────────────────────────

    def enrich_profile_batch(self, urls: List[str]) -> Dict[str, Dict]:
        normalized = {u: self._normalize_linkedin_url(u) for u in urls}
        api_urls = list(normalized.values())

        try:
            run_input = {"urls": api_urls}
            run = self.apify.actor(self.PROFILE_ACTOR).call(run_input=run_input)
            items = list(self.apify.dataset(run["defaultDatasetId"]).iterate_items())

            result = {}
            for item in items:
                profile_url = item.get("linkedinUrl") or item.get("url") or ""
                pub_id = item.get("publicIdentifier", "")
                matched_orig = None

                for orig_url in urls:
                    norm_url = normalized[orig_url]
                    if (self._urls_match(orig_url, profile_url)
                            or self._urls_match(norm_url, profile_url)
                            or (pub_id and pub_id in unquote(orig_url))):
                        matched_orig = orig_url
                        break

                if matched_orig:
                    result[matched_orig] = item
            return result
        except Exception as e:
            print(f"    Apify batch error: {e}")
            self.stats["apify_errors"] += 1
            return {}

    def _urls_match(self, url1: str, url2: str) -> bool:
        def extract_username(url):
            url = unquote(url).rstrip("/").lower()
            if "/in/" in url:
                return url.split("/in/")[-1].split("?")[0]
            return url
        return extract_username(url1) == extract_username(url2)

    def _compute_experience_stats(self, employment: List[Dict]) -> Dict:
        if not employment:
            return {}

        stats = {}
        companies = set()
        titles = []
        current_role = None
        earliest_start = None

        for job in employment:
            company = job.get("company_name")
            if company:
                companies.add(company)
            title = job.get("job_title")
            if title:
                titles.append(title)

            if job.get("is_current") and not current_role:
                current_role = job

            start = job.get("start_date")
            if start:
                try:
                    parts = start.split("-")
                    year = int(parts[0])
                    if earliest_start is None or year < earliest_start:
                        earliest_start = year
                except (ValueError, IndexError):
                    pass

        stats["enrich_companies_worked"] = list(companies) if companies else None
        stats["enrich_titles_held"] = titles if titles else None

        if current_role:
            stats["enrich_current_company"] = current_role.get("company_name")
            stats["enrich_current_title"] = current_role.get("job_title")
            start_str = current_role.get("start_date")
            if start_str:
                try:
                    parts = start_str.split("-")
                    year = int(parts[0])
                    month = int(parts[1]) if len(parts) > 1 else 1
                    start_date = date(year, month, 1)
                    stats["enrich_current_since"] = start_date.isoformat()
                    years_in_role = (date.today() - start_date).days / 365.25
                    stats["enrich_years_in_current_role"] = round(years_in_role, 1)
                except (ValueError, IndexError):
                    pass

        if earliest_start:
            stats["enrich_total_experience_years"] = round(
                date.today().year - earliest_start, 1
            )

        return stats

    def map_profile_to_updates(self, raw: Dict) -> Dict:
        updates = {}

        # ── Flat LinkedIn columns ──
        updates["headline"] = raw.get("headline")
        updates["summary"] = raw.get("about")
        updates["linkedin_username"] = raw.get("publicIdentifier")

        follower_count = raw.get("followerCount")
        connections_count = raw.get("connectionsCount")
        if follower_count is not None:
            updates["enrich_follower_count"] = follower_count
        if connections_count is not None:
            updates["enrich_connections"] = connections_count

        # ── Employment (JSONB + flat + summary) ──
        experiences = raw.get("experience") or []
        employment = []
        for exp in experiences:
            date_range = exp.get("dateRange", {})
            start = date_range.get("start", {}) if date_range else {}
            end = date_range.get("end", {}) if date_range else {}
            employment.append({
                "job_title": exp.get("position"),
                "company_name": exp.get("companyName"),
                "company_url": exp.get("companyLinkedinUrl"),
                "location": exp.get("location"),
                "start_date": (
                    f"{start.get('year', '')}-{str(start.get('month', '')).zfill(2)}"
                    if start and start.get("year") else None
                ),
                "end_date": (
                    f"{end.get('year', '')}-{str(end.get('month', '')).zfill(2)}"
                    if end and end.get("year") else None
                ),
                "is_current": end is None or end == {},
                "description": exp.get("description"),
                "employment_type": exp.get("employmentType"),
                "duration": exp.get("duration"),
            })

        if employment:
            updates["enrich_employment"] = json.dumps(employment)
            current = next((e for e in employment if e.get("is_current")), employment[0])
            if current.get("company_name"):
                updates["company"] = current["company_name"]
            if current.get("job_title"):
                updates["position"] = current["job_title"]
            exp_stats = self._compute_experience_stats(employment)
            updates.update(exp_stats)

        # ── Education (JSONB + summary) ──
        edu_list = raw.get("education") or []
        education = []
        for edu in edu_list:
            education.append({
                "school_name": edu.get("schoolName"),
                "degree": edu.get("degree"),
                "field_of_study": edu.get("fieldOfStudy"),
                "description": edu.get("description"),
            })

        if education:
            updates["enrich_education"] = json.dumps(education)
            schools = [e["school_name"] for e in education if e.get("school_name")]
            if schools:
                updates["enrich_schools"] = schools

        # ── Skills (summary array) ──
        skills = raw.get("skills") or []
        if skills:
            skill_names = []
            for s in skills:
                if isinstance(s, str):
                    skill_names.append(s)
                elif isinstance(s, dict):
                    name = s.get("name")
                    if name:
                        skill_names.append(name)
            if skill_names:
                updates["enrich_skills"] = skill_names

        # ── Volunteering → volunteer_orgs + board_positions ──
        volunteer = raw.get("volunteering") or raw.get("volunteerExperience") or []
        if volunteer:
            orgs = []
            board_orgs = []
            board_keywords = {"board", "director", "trustee", "advisor", "advisory"}
            for v in volunteer:
                org = v.get("companyName") or v.get("company") or v.get("organization")
                if org:
                    orgs.append(org)
                role = (v.get("title") or v.get("role") or "").lower()
                if any(kw in role for kw in board_keywords) and org:
                    board_orgs.append(org)
            if orgs:
                updates["enrich_volunteer_orgs"] = orgs
            if board_orgs:
                updates["enrich_board_positions"] = board_orgs

        # ── Enrichment metadata ──
        updates["enriched_at"] = datetime.now(timezone.utc).isoformat()
        updates["enrichment_source"] = "apify"

        # Filter to only valid columns and remove None values
        return {k: v for k, v in updates.items() if v is not None and k in VALID_COLUMNS}

    def save_profile(self, contact_id: int, updates: Dict) -> bool:
        try:
            self.supabase.table(TABLE).update(updates).eq("id", contact_id).execute()
            return True
        except Exception as e:
            print(f"    DB update error: {e}")
            self.stats["db_errors"] += 1
            return False

    # ── Main Runner ─────────────────────────────────────────────────

    APIFY_BATCH_SIZE = 25
    MAX_CONCURRENT_RUNS = 8

    def _process_batch(self, batch_contacts: List[Dict], batch_num: int, total_batches: int) -> None:
        urls = [c["linkedin_url"] for c in batch_contacts]
        url_to_contact = {c["linkedin_url"]: c for c in batch_contacts}

        print(f"\n  Batch {batch_num}/{total_batches}: Sending {len(urls)} URLs to Apify...")
        results = self.enrich_profile_batch(urls)
        print(f"  Batch {batch_num}/{total_batches}: Got {len(results)} profiles back")

        for url, contact in url_to_contact.items():
            name = f"{contact['first_name']} {contact['last_name']}"
            contact_id = contact["id"]
            raw_profile = results.get(url)

            if raw_profile:
                updates = self.map_profile_to_updates(raw_profile)
                if self.save_profile(contact_id, updates):
                    print(f"    [{contact_id}] {name}: {len(updates)} fields | "
                          f"{updates.get('enrich_current_title', '?')[:40]} at "
                          f"{updates.get('enrich_current_company', '?')[:30]}")
                    self.stats["profiles_enriched"] += 1
                else:
                    print(f"    [{contact_id}] {name}: DB SAVE FAILED")
                    self.stats["profiles_failed"] += 1
            else:
                print(f"    [{contact_id}] {name}: No data from Apify")
                self.stats["profiles_failed"] += 1

    def run(self):
        if not self.connect():
            return False

        contacts = self.get_contacts()
        total = len(contacts)
        print(f"Found {total} Sally contacts to enrich")

        if total == 0:
            print("Nothing to do.")
            return True

        if self.test_mode:
            contacts = contacts[:1]
            print("TEST MODE: Processing 1 contact only\n")
            c = contacts[0]
            name = f"{c['first_name']} {c['last_name']}"
            print(f"[1/1] {name} (id={c['id']}, url={c['linkedin_url']})")
            results = self.enrich_profile_batch([c["linkedin_url"]])
            raw = results.get(c["linkedin_url"])
            if raw:
                updates = self.map_profile_to_updates(raw)
                if self.save_profile(c["id"], updates):
                    print(f"  Saved ({len(updates)} fields)")
                    for k, v in updates.items():
                        val = str(v)[:80] if not isinstance(v, list) else f"[{len(v)} items]"
                        print(f"    {k}: {val}")
                    self.stats["profiles_enriched"] += 1
                else:
                    self.stats["profiles_failed"] += 1
            else:
                print("  No data returned")
                self.stats["profiles_failed"] += 1
            self.print_summary()
            return True

        est_cost = len(contacts) * 0.004
        print(f"Estimated cost: ~${est_cost:.2f} ({len(contacts)} x $0.004)")
        print(f"Strategy: {self.APIFY_BATCH_SIZE} URLs/batch, {self.MAX_CONCURRENT_RUNS} concurrent runs\n")

        batches = []
        for i in range(0, len(contacts), self.APIFY_BATCH_SIZE):
            batches.append(contacts[i : i + self.APIFY_BATCH_SIZE])

        total_batches = len(batches)
        print(f"Processing {total} contacts in {total_batches} batches...\n")

        with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT_RUNS) as executor:
            futures = {}
            for batch_num, batch in enumerate(batches, 1):
                future = executor.submit(self._process_batch, batch, batch_num, total_batches)
                futures[future] = batch_num

            for future in as_completed(futures):
                batch_num = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"\n  Batch {batch_num} EXCEPTION: {e}")
                    self.stats["apify_errors"] += 1

                done = self.stats["profiles_enriched"] + self.stats["profiles_failed"]
                print(f"\n--- Progress: {done}/{total} contacts processed "
                      f"({self.stats['profiles_enriched']} enriched, "
                      f"{self.stats['profiles_failed']} failed) ---")

        self.print_summary()
        return True

    def print_summary(self):
        s = self.stats
        print("\n" + "=" * 60)
        print("SALLY ENRICHMENT SUMMARY")
        print("=" * 60)
        print(f"  Profiles enriched:  {s['profiles_enriched']}")
        print(f"  Profiles failed:    {s['profiles_failed']}")
        print(f"  Profiles skipped:   {s['profiles_skipped']}")
        print(f"  Apify errors:       {s['apify_errors']}")
        print(f"  DB errors:          {s['db_errors']}")
        cost = s["profiles_enriched"] * 0.004
        print(f"\n  TOTAL COST:         ~${cost:.2f}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Enrich Sally's contacts via Apify LinkedIn profile scraper"
    )
    parser.add_argument("--test", "-t", action="store_true", help="Test with 1 contact")
    parser.add_argument("--batch", "-b", type=int, help="Limit to N contacts per run")
    parser.add_argument("--start-from", "-s", type=int, help="Start from contact id >= N")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-enrich contacts already enriched by Apify")
    parser.add_argument("--contact-id", type=int, help="Enrich a specific contact by ID")
    parser.add_argument("--ids", type=str, default=None,
                        help="Comma-separated contact IDs to process")
    args = parser.parse_args()

    ids = [int(x.strip()) for x in args.ids.split(",")] if args.ids else None

    enricher = SallyContactsEnricher(
        test_mode=args.test,
        batch_size=args.batch,
        start_from=args.start_from,
        force=args.force or bool(ids) or bool(args.contact_id),
        ids=ids,
        contact_id=args.contact_id,
    )
    success = enricher.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
