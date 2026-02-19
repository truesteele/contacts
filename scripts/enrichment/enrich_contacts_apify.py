#!/usr/bin/env python3
"""
Contacts Database - Apify LinkedIn Enrichment Script

Enriches all contacts with LinkedIn URLs using the same Apify actors
proven in the Camelback Expert Bench enrichment.

Overwrites stale LinkedIn-sourced data with fresh Apify data.
Populates both structured JSONB columns and summary enrich_* columns.
Preserves non-LinkedIn fields (emails, donor scores, Perplexity data, etc.)

Usage:
  python scripts/enrichment/enrich_contacts_apify.py --test          # Test with 1 contact
  python scripts/enrichment/enrich_contacts_apify.py --batch 50      # Process 50 contacts
  python scripts/enrichment/enrich_contacts_apify.py                 # Full run (all contacts)
  python scripts/enrichment/enrich_contacts_apify.py --start-from 500  # Resume from id >= 500
  python scripts/enrichment/enrich_contacts_apify.py --force         # Re-enrich already enriched
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone, date
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote, urlparse
from dotenv import load_dotenv
from supabase import create_client, Client
from apify_client import ApifyClient

load_dotenv()


class ContactsEnricher:
    PROFILE_ACTOR = "harvestapi/linkedin-profile-scraper"

    def __init__(self, test_mode=False, batch_size=None, start_from=None, force=False):
        self.supabase: Optional[Client] = None
        self.apify: Optional[ApifyClient] = None
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.start_from = start_from
        self.force = force
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
        apify_key = os.environ.get("APIFY_API_KEY")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        if not apify_key:
            print("ERROR: Missing APIFY_API_KEY")
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
                self.supabase.table("contacts")
                .select("id, first_name, last_name, linkedin_url, enriched_at, enrichment_source")
                .neq("linkedin_url", "")
                .not_.is_("linkedin_url", "null")
                .order("id")
                .range(offset, offset + page_size - 1)
            )

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
        """Normalize a LinkedIn URL for Apify consumption."""
        url = url.strip().rstrip("/")
        # Decode percent-encoded characters (é, ñ, etc.)
        url = unquote(url)
        # Ensure https://
        if not url.startswith("http"):
            url = "https://" + url
        # Ensure www. prefix
        url = url.replace("://linkedin.com/", "://www.linkedin.com/")
        return url

    # ── Profile Enrichment ──────────────────────────────────────────

    def enrich_profile_batch(self, urls: List[str]) -> Dict[str, Dict]:
        """Enrich multiple LinkedIn profiles in a single Apify actor run.
        Returns a dict mapping original linkedin_url -> profile data."""
        # Normalize URLs for Apify, but map results back to originals
        normalized = {u: self._normalize_linkedin_url(u) for u in urls}
        norm_to_orig = {v: k for k, v in normalized.items()}
        api_urls = list(normalized.values())

        try:
            run_input = {"urls": api_urls}
            run = self.apify.actor(self.PROFILE_ACTOR).call(run_input=run_input)
            items = list(self.apify.dataset(run["defaultDatasetId"]).iterate_items())
            # Map results back to original URLs
            result = {}
            for item in items:
                profile_url = item.get("linkedinUrl") or item.get("url") or ""
                pub_id = item.get("publicIdentifier", "")
                matched_orig = None

                # Try matching against both original and normalized URLs
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
        """Check if two LinkedIn URLs point to the same profile."""
        def extract_username(url):
            url = unquote(url).rstrip("/").lower()
            if "/in/" in url:
                return url.split("/in/")[-1].split("?")[0]
            return url
        return extract_username(url1) == extract_username(url2)

    def _parse_start_date(self, date_range: Optional[dict]) -> Optional[str]:
        if not date_range:
            return None
        start = date_range.get("start", {})
        if start and start.get("year"):
            month = str(start.get("month", "01")).zfill(2)
            return f"{start['year']}-{month}"
        return None

    def _parse_end_date(self, date_range: Optional[dict]) -> Optional[str]:
        if not date_range:
            return None
        end = date_range.get("end", {})
        if end and end.get("year"):
            month = str(end.get("month", "01")).zfill(2)
            return f"{end['year']}-{month}"
        return None

    def _compute_experience_stats(self, employment: List[Dict]) -> Dict:
        """Compute summary stats from structured employment history."""
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

        stats["enrich_number_of_positions"] = len(employment)
        stats["enrich_number_of_companies"] = len(companies)
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

        # ── Flat LinkedIn columns (overwrite with fresh data) ──
        updates["headline"] = raw.get("headline")
        updates["summary"] = raw.get("about")
        updates["linkedin_username"] = raw.get("publicIdentifier")

        # Profile picture & social metrics
        updates["linkedin_profile"] = raw.get("photo")
        updates["enrich_profile_pic_url"] = raw.get("photo")

        follower_count = raw.get("followerCount")
        connections_count = raw.get("connectionsCount")
        if follower_count is not None:
            updates["num_followers"] = str(follower_count)
            updates["enrich_follower_count"] = follower_count
        if connections_count is not None:
            updates["connections"] = str(connections_count)
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
            # Update current company/position flat columns
            current = next((e for e in employment if e.get("is_current")), employment[0])
            if current.get("company_name"):
                updates["company"] = current["company_name"]
            if current.get("job_title"):
                updates["position"] = current["job_title"]
            # Summary stats
            exp_stats = self._compute_experience_stats(employment)
            updates.update(exp_stats)

        # ── Education (JSONB + flat + summary) ──
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
            # Update flat columns with most recent
            latest = education[0]
            updates["school_name_education"] = latest.get("school_name")
            updates["degree_education"] = latest.get("degree")
            updates["field_of_study_education"] = latest.get("field_of_study")
            # Summary arrays
            schools = [e["school_name"] for e in education if e.get("school_name")]
            fields = [e["field_of_study"] for e in education if e.get("field_of_study")]
            degrees = [e["degree"] for e in education if e.get("degree")]
            if schools:
                updates["enrich_schools"] = schools
            if fields:
                updates["enrich_fields_of_study"] = fields
            if degrees:
                updates["enrich_highest_degree"] = degrees[0]

        # ── Skills (JSONB + summary array) ──
        skills = raw.get("skills") or []
        if skills:
            skill_list = []
            skill_names = []
            for s in skills:
                if isinstance(s, str):
                    skill_list.append({"skill_name": s})
                    skill_names.append(s)
                elif isinstance(s, dict):
                    name = s.get("name")
                    skill_list.append({"skill_name": name})
                    if name:
                        skill_names.append(name)
            updates["enrich_skills_detailed"] = json.dumps(skill_list)
            if skill_names:
                updates["enrich_skills"] = skill_names

        # ── Certifications (JSONB) ──
        certs = raw.get("certifications") or []
        if certs:
            updates["enrich_certifications"] = json.dumps([{
                "name": c.get("name"),
                "organization": c.get("authority") or c.get("organization"),
                "url": c.get("url"),
            } for c in certs])

        # ── Volunteering (JSONB + flat + summary) ──
        volunteer = raw.get("volunteering") or raw.get("volunteerExperience") or []
        if volunteer:
            vol_data = [{
                "organization": v.get("companyName") or v.get("company") or v.get("organization"),
                "role": v.get("title") or v.get("role"),
                "cause": v.get("cause"),
            } for v in volunteer]
            updates["enrich_volunteering"] = json.dumps(vol_data)
            # Flat columns
            roles = [v["role"] for v in vol_data if v.get("role")]
            orgs = [v["organization"] for v in vol_data if v.get("organization")]
            if roles:
                updates["role_volunteering"] = " | ".join(roles)
            if orgs:
                updates["company_name_volunteering"] = " | ".join(orgs)
                updates["enrich_volunteer_orgs"] = orgs

        # ── Publications (JSONB + flat + summary count) ──
        pubs = raw.get("publications") or []
        if pubs:
            pub_data = [{
                "name": p.get("name") or p.get("title"),
                "publisher": p.get("publisher"),
                "url": p.get("url"),
            } for p in pubs]
            updates["enrich_publications"] = json.dumps(pub_data)
            titles = [p["name"] for p in pub_data if p.get("name")]
            if titles:
                updates["title_publications"] = " | ".join(titles)
            updates["enrich_publication_count"] = len(pubs)

        # ── Honors/Awards (JSONB + flat + summary count) ──
        honors = raw.get("honorsAndAwards") or raw.get("honors") or []
        if honors:
            honor_data = [{
                "title": h.get("title") or h.get("name"),
                "issuer": h.get("issuer"),
            } for h in honors]
            updates["enrich_honors_awards"] = json.dumps(honor_data)
            titles = [h["title"] for h in honor_data if h.get("title")]
            issuers = [h["issuer"] for h in honor_data if h.get("issuer")]
            if titles:
                updates["title_awards"] = " | ".join(titles)
            if issuers:
                updates["company_name_awards"] = " | ".join(issuers)
            updates["enrich_award_count"] = len(honors)

        # ── Languages (JSONB) ──
        languages = raw.get("languages") or []
        if languages:
            lang_list = []
            for lang in languages:
                if isinstance(lang, str):
                    lang_list.append({"language": lang})
                elif isinstance(lang, dict):
                    lang_list.append({
                        "language": lang.get("name") or lang.get("language"),
                        "proficiency": lang.get("proficiency"),
                    })
            updates["enrich_languages"] = json.dumps(lang_list)

        # ── Projects (JSONB + flat) ──
        projects = raw.get("projects") or []
        if projects:
            proj_data = [{
                "name": p.get("title") or p.get("name"),
                "description": p.get("description"),
                "url": p.get("url"),
            } for p in projects]
            updates["enrich_projects"] = json.dumps(proj_data)
            titles = [p["name"] for p in proj_data if p.get("name")]
            if titles:
                updates["title_projects"] = " | ".join(titles)

        # ── Board positions from volunteering (best-effort extraction) ──
        board_keywords = {"board", "director", "trustee", "advisor", "advisory"}
        if volunteer:
            board_orgs = []
            for v in volunteer:
                role = (v.get("title") or v.get("role") or "").lower()
                if any(kw in role for kw in board_keywords):
                    org = v.get("companyName") or v.get("company") or v.get("organization")
                    if org:
                        board_orgs.append(org)
            if board_orgs:
                updates["enrich_board_positions"] = board_orgs
                updates["nonprofit_board_member"] = True

        # ── Enrichment metadata ──
        updates["enriched_at"] = datetime.now(timezone.utc).isoformat()
        updates["enrichment_source"] = "apify"
        updates["enrich_person_from_profile"] = json.dumps({
            "enriched_at": datetime.now(timezone.utc).isoformat(),
            "source": "apify",
            "actor": self.PROFILE_ACTOR,
        })

        # Remove None values to avoid overwriting with nulls
        return {k: v for k, v in updates.items() if v is not None}

    def save_profile(self, contact_id: int, updates: Dict) -> bool:
        try:
            self.supabase.table("contacts").update(updates).eq("id", contact_id).execute()
            return True
        except Exception as e:
            print(f"    DB update error: {e}")
            self.stats["db_errors"] += 1
            return False

    # ── Main Runner ─────────────────────────────────────────────────

    APIFY_BATCH_SIZE = 25  # URLs per Apify actor run
    MAX_CONCURRENT_RUNS = 8  # Concurrent actor runs (plan allows 32, stay conservative)

    def _process_batch(self, batch_contacts: List[Dict], batch_num: int, total_batches: int) -> None:
        """Process a batch of contacts through Apify and save results."""
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
                    print(f"    [{contact_id}] {name}: {len(updates)} fields | {updates.get('enrich_current_title', '?')[:40]} at {updates.get('enrich_current_company', '?')[:30]}")
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
        print(f"Found {total} contacts to enrich")

        if total == 0:
            print("Nothing to do.")
            return True

        if self.test_mode:
            contacts = contacts[:1]
            print("TEST MODE: Processing 1 contact only\n")
            # Single profile for test mode
            c = contacts[0]
            name = f"{c['first_name']} {c['last_name']}"
            print(f"[1/1] {name} (id={c['id']})")
            results = self.enrich_profile_batch([c["linkedin_url"]])
            raw = results.get(c["linkedin_url"])
            if raw:
                updates = self.map_profile_to_updates(raw)
                if self.save_profile(c["id"], updates):
                    print(f"  Saved ({len(updates)} fields)")
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

        # Split contacts into batches
        batches = []
        for i in range(0, len(contacts), self.APIFY_BATCH_SIZE):
            batches.append(contacts[i : i + self.APIFY_BATCH_SIZE])

        total_batches = len(batches)
        print(f"Processing {total} contacts in {total_batches} batches...\n")

        # Process batches with concurrent threads
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

                # Progress update
                done = self.stats["profiles_enriched"] + self.stats["profiles_failed"]
                print(f"\n--- Progress: {done}/{total} contacts processed ({self.stats['profiles_enriched']} enriched, {self.stats['profiles_failed']} failed) ---")

        self.print_summary()
        return True

    def print_summary(self):
        s = self.stats
        print("\n" + "=" * 60)
        print("ENRICHMENT SUMMARY")
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
        description="Enrich contacts via Apify LinkedIn profile scraper"
    )
    parser.add_argument("--test", "-t", action="store_true", help="Test with 1 contact")
    parser.add_argument("--batch", "-b", type=int, help="Limit to N contacts per run")
    parser.add_argument("--start-from", "-s", type=int, help="Start from contact id >= N")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-enrich contacts already enriched by Apify")
    args = parser.parse_args()

    enricher = ContactsEnricher(
        test_mode=args.test,
        batch_size=args.batch,
        start_from=args.start_from,
        force=args.force,
    )
    success = enricher.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
