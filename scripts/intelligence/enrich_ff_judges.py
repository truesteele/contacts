#!/usr/bin/env python3
"""
Flourish Fund Innovation Challenge — Judge LinkedIn Enrichment

Two-phase pipeline:
  Phase 1: Discover LinkedIn URLs for judges who don't have them (Google search)
  Phase 2: Enrich all judges with LinkedIn URLs via Apify profile scraper + posts scraper

Stores enrichment data in ff_ic_judges.research_profile JSONB and adds new
columns for structured LinkedIn data.

Usage:
  python scripts/intelligence/enrich_ff_judges.py --discover        # Phase 1: find LinkedIn URLs
  python scripts/intelligence/enrich_ff_judges.py --enrich          # Phase 2: Apify profile enrichment
  python scripts/intelligence/enrich_ff_judges.py --posts           # Phase 3: Apify post scraping
  python scripts/intelligence/enrich_ff_judges.py --all             # All phases
  python scripts/intelligence/enrich_ff_judges.py --test            # Test with 1 judge
  python scripts/intelligence/enrich_ff_judges.py --name "Tim Tebow"  # Specific judge
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from urllib.parse import unquote
from dotenv import load_dotenv
from supabase import create_client, Client
from apify_client import ApifyClient

load_dotenv()


class JudgeEnricher:
    PROFILE_ACTOR = "harvestapi/linkedin-profile-scraper"
    POSTS_ACTOR = "harvestapi/linkedin-profile-posts"

    def __init__(self, test_mode=False, name=None, force=False):
        self.supabase: Optional[Client] = None
        self.apify: Optional[ApifyClient] = None
        self.test_mode = test_mode
        self.name_filter = name
        self.force = force
        self.stats = {
            "urls_discovered": 0,
            "urls_not_found": 0,
            "profiles_enriched": 0,
            "profiles_failed": 0,
            "posts_found": 0,
            "posts_stored": 0,
            "apify_errors": 0,
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

    # ── URL Normalization (same pattern as enrich_contacts_apify.py) ──

    def _normalize_linkedin_url(self, url: str) -> str:
        url = url.strip().rstrip("/")
        url = unquote(url)
        if not url.startswith("http"):
            url = "https://" + url
        url = url.replace("://linkedin.com/", "://www.linkedin.com/")
        return url

    def _extract_username(self, url: str) -> str:
        url = unquote(url).rstrip("/").lower()
        if "/in/" in url:
            return url.split("/in/")[-1].split("?")[0]
        return url

    # ── Phase 1: Discover LinkedIn URLs ──────────────────────────────

    def discover_urls(self):
        """Find LinkedIn URLs for judges who don't have them using Google search via Apify."""
        judges = self._get_judges(needs_url=True)
        print(f"\nPhase 1: Discovering LinkedIn URLs for {len(judges)} judges")

        if not judges:
            print("All judges already have LinkedIn URLs!")
            return

        for judge in judges:
            name = judge["name"]
            org = judge.get("organization") or ""
            role = judge.get("role_title") or ""

            # Build search query
            search_query = f'site:linkedin.com/in/ "{name}"'
            if org:
                search_query += f' "{org}"'

            print(f"\n  Searching: {name} ({org or 'no org'})...")

            try:
                run_input = {
                    "queries": search_query,
                    "maxPagesPerQuery": 1,
                    "resultsPerPage": 5,
                }
                run = self.apify.actor("apify/google-search-scraper").call(run_input=run_input)
                items = list(self.apify.dataset(run["defaultDatasetId"]).iterate_items())

                linkedin_url = None
                for item in items:
                    organic = item.get("organicResults") or []
                    for result in organic:
                        url = result.get("url", "")
                        title = (result.get("title") or "").lower()
                        if "linkedin.com/in/" in url:
                            # Basic name matching
                            name_parts = name.lower().split()
                            if any(part in title for part in name_parts):
                                linkedin_url = url
                                break
                    if linkedin_url:
                        break

                if linkedin_url:
                    linkedin_url = self._normalize_linkedin_url(linkedin_url)
                    self.supabase.table("ff_ic_judges").update({
                        "linkedin_url": linkedin_url,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }).eq("id", judge["id"]).execute()
                    print(f"    Found: {linkedin_url}")
                    self.stats["urls_discovered"] += 1
                else:
                    print(f"    Not found")
                    self.stats["urls_not_found"] += 1

                time.sleep(1)  # Politeness delay

            except Exception as e:
                print(f"    Search error: {e}")
                self.stats["apify_errors"] += 1

        print(f"\n  URLs discovered: {self.stats['urls_discovered']}")
        print(f"  Not found: {self.stats['urls_not_found']}")

    # ── Phase 2: Enrich Profiles ─────────────────────────────────────

    def enrich_profiles(self):
        """Enrich all judges with LinkedIn URLs via Apify profile scraper."""
        judges = self._get_judges(needs_url=False, has_url=True)
        print(f"\nPhase 2: Enriching {len(judges)} judge profiles via Apify")

        if not judges:
            print("No judges with LinkedIn URLs to enrich!")
            return

        est_cost = len(judges) * 0.004
        print(f"Estimated cost: ~${est_cost:.2f} ({len(judges)} x $0.004)")

        # Process in batches of 10 (small set, no need for large batches)
        batch_size = 10
        for i in range(0, len(judges), batch_size):
            batch = judges[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(judges) + batch_size - 1) // batch_size

            urls = [j["linkedin_url"] for j in batch]
            url_to_judge = {j["linkedin_url"]: j for j in batch}

            print(f"\n  Batch {batch_num}/{total_batches}: {len(urls)} profiles...")
            results = self._scrape_profiles(urls)
            print(f"  Got {len(results)} profiles back")

            for url, judge in url_to_judge.items():
                raw = results.get(url)
                if raw:
                    enrichment = self._extract_enrichment(raw)
                    self._save_enrichment(judge, enrichment, raw)
                    print(f"    + {judge['name']}: {enrichment.get('headline', '?')[:60]}")
                    self.stats["profiles_enriched"] += 1
                else:
                    print(f"    - {judge['name']}: No data from Apify")
                    self.stats["profiles_failed"] += 1

        print(f"\n  Profiles enriched: {self.stats['profiles_enriched']}")
        print(f"  Profiles failed: {self.stats['profiles_failed']}")

    def _scrape_profiles(self, urls: List[str]) -> Dict[str, Dict]:
        """Send URLs to Apify and return dict of url -> raw profile data."""
        normalized = {u: self._normalize_linkedin_url(u) for u in urls}

        try:
            api_urls = list(normalized.values())
            run_input = {"urls": api_urls}
            run = self.apify.actor(self.PROFILE_ACTOR).call(run_input=run_input)
            items = list(self.apify.dataset(run["defaultDatasetId"]).iterate_items())

            result = {}
            for item in items:
                profile_url = item.get("linkedinUrl") or item.get("url") or ""
                pub_id = item.get("publicIdentifier", "")

                for orig_url in urls:
                    norm_url = normalized[orig_url]
                    if (self._urls_match(orig_url, profile_url)
                            or self._urls_match(norm_url, profile_url)
                            or (pub_id and pub_id in unquote(orig_url))):
                        result[orig_url] = item
                        break

            return result
        except Exception as e:
            print(f"    Apify batch error: {e}")
            self.stats["apify_errors"] += 1
            return {}

    def _urls_match(self, url1: str, url2: str) -> bool:
        def extract(url):
            url = unquote(url).rstrip("/").lower()
            if "/in/" in url:
                return url.split("/in/")[-1].split("?")[0]
            return url
        return extract(url1) == extract(url2)

    def _extract_enrichment(self, raw: Dict) -> Dict:
        """Extract structured enrichment from raw Apify profile data."""
        enrichment = {}

        enrichment["headline"] = raw.get("headline")
        enrichment["about"] = raw.get("about")
        enrichment["public_identifier"] = raw.get("publicIdentifier")
        enrichment["photo"] = raw.get("photo")
        enrichment["follower_count"] = raw.get("followerCount")
        enrichment["connections_count"] = raw.get("connectionsCount")
        enrichment["location"] = raw.get("location")

        # Employment
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
                "duration": exp.get("duration"),
            })
        enrichment["employment"] = employment

        # Current role
        if employment:
            current = next((e for e in employment if e.get("is_current")), employment[0])
            enrichment["current_company"] = current.get("company_name")
            enrichment["current_title"] = current.get("job_title")

        # Education
        edu_list = raw.get("education") or []
        education = []
        for edu in edu_list:
            education.append({
                "school_name": edu.get("schoolName"),
                "degree": edu.get("degree"),
                "field_of_study": edu.get("fieldOfStudy"),
                "description": edu.get("description"),
            })
        enrichment["education"] = education

        # Skills
        skills = raw.get("skills") or []
        skill_names = []
        for s in skills:
            if isinstance(s, str):
                skill_names.append(s)
            elif isinstance(s, dict):
                name = s.get("name")
                if name:
                    skill_names.append(name)
        enrichment["skills"] = skill_names

        # Volunteering / board positions
        volunteer = raw.get("volunteering") or raw.get("volunteerExperience") or []
        vol_data = []
        for v in volunteer:
            vol_data.append({
                "organization": v.get("companyName") or v.get("company") or v.get("organization"),
                "role": v.get("title") or v.get("role"),
                "cause": v.get("cause"),
            })
        enrichment["volunteering"] = vol_data

        # Certifications
        certs = raw.get("certifications") or []
        enrichment["certifications"] = [{
            "name": c.get("name"),
            "organization": c.get("authority") or c.get("organization"),
        } for c in certs] if certs else []

        # Publications
        pubs = raw.get("publications") or []
        enrichment["publications"] = [{
            "name": p.get("name") or p.get("title"),
            "publisher": p.get("publisher"),
        } for p in pubs] if pubs else []

        # Awards
        honors = raw.get("honorsAndAwards") or raw.get("honors") or []
        enrichment["awards"] = [{
            "title": h.get("title") or h.get("name"),
            "issuer": h.get("issuer"),
        } for h in honors] if honors else []

        return {k: v for k, v in enrichment.items() if v is not None}

    def _save_enrichment(self, judge: Dict, enrichment: Dict, raw: Dict):
        """Save enrichment data to ff_ic_judges table."""
        # Merge enrichment into existing research_profile
        existing_profile = judge.get("research_profile") or {}
        if isinstance(existing_profile, str):
            existing_profile = json.loads(existing_profile)

        existing_profile["linkedin_enrichment"] = enrichment
        existing_profile["linkedin_raw"] = {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "actor": self.PROFILE_ACTOR,
            "public_identifier": raw.get("publicIdentifier"),
        }

        # Update role_title from LinkedIn if available
        updates = {
            "research_profile": json.dumps(existing_profile),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if enrichment.get("current_title") and enrichment.get("current_company"):
            updates["role_title"] = f"{enrichment['current_title']}, {enrichment['current_company']}"

        try:
            self.supabase.table("ff_ic_judges").update(updates).eq("id", judge["id"]).execute()
        except Exception as e:
            print(f"    DB error saving {judge['name']}: {e}")

    # ── Phase 3: Scrape Posts ────────────────────────────────────────

    def scrape_posts(self):
        """Scrape LinkedIn posts for all enriched judges."""
        judges = self._get_judges(needs_url=False, has_url=True)
        print(f"\nPhase 3: Scraping posts for {len(judges)} judges")

        if not judges:
            print("No judges with LinkedIn URLs!")
            return

        est_cost = len(judges) * 0.05  # rough estimate for posts
        print(f"Estimated cost: ~${est_cost:.2f}")

        # Process in small batches
        batch_size = 5
        for i in range(0, len(judges), batch_size):
            batch = judges[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(judges) + batch_size - 1) // batch_size

            urls = [self._normalize_linkedin_url(j["linkedin_url"]) for j in batch]
            username_to_judge = {}
            for j in batch:
                username = self._extract_username(j["linkedin_url"])
                username_to_judge[username] = j

            print(f"\n  Batch {batch_num}/{total_batches}: {len(urls)} profiles...")

            try:
                run_input = {
                    "profileUrls": urls,
                    "maxPosts": 25,
                    "scrapeReactions": False,
                    "scrapeComments": False,
                    "includeReposts": False,
                    "includeQuotePosts": True,
                }
                run = self.apify.actor(self.POSTS_ACTOR).call(run_input=run_input)
                items = list(self.apify.dataset(run["defaultDatasetId"]).iterate_items())

                # Group posts by judge
                posts_by_judge: Dict[int, List[Dict]] = {}
                for item in items:
                    author = item.get("author") or {}
                    pub_id = (author.get("publicIdentifier") or "").strip().lower()
                    author_url = author.get("linkedinUrl") or item.get("authorUrl") or ""
                    query = item.get("query") or {}
                    query_profile = query.get("profilePublicIdentifier") or ""

                    author_username = pub_id or self._extract_username(author_url)
                    if not author_username:
                        author_username = self._extract_username(query_profile)

                    matched = username_to_judge.get(author_username) if author_username else None
                    if matched:
                        jid = matched["id"]
                        if jid not in posts_by_judge:
                            posts_by_judge[jid] = []
                        posts_by_judge[jid].append(item)

                # Save posts to research_profile
                for judge in batch:
                    jid = judge["id"]
                    raw_posts = posts_by_judge.get(jid, [])

                    posts_data = []
                    for post in raw_posts:
                        content = post.get("content") or post.get("text")
                        if not content:
                            continue

                        post_url = post.get("linkedinUrl") or post.get("postUrl") or post.get("url")
                        posted_at = post.get("postedAt") or post.get("postedDate")
                        post_date = None
                        if isinstance(posted_at, dict):
                            ts = posted_at.get("timestamp")
                            if ts:
                                post_date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
                        elif isinstance(posted_at, (int, float)):
                            post_date = datetime.fromtimestamp(posted_at / 1000, tz=timezone.utc).isoformat()
                        elif isinstance(posted_at, str):
                            post_date = posted_at

                        eng = post.get("engagement") or {}
                        posts_data.append({
                            "url": post_url,
                            "content": content[:2000],  # Truncate long posts
                            "date": post_date,
                            "likes": eng.get("likes", 0) or 0,
                            "comments": eng.get("comments", 0) or 0,
                            "shares": eng.get("shares", 0) or 0,
                        })
                        self.stats["posts_found"] += 1

                    if posts_data:
                        # Merge into research_profile
                        existing = judge.get("research_profile") or {}
                        if isinstance(existing, str):
                            existing = json.loads(existing)
                        existing["linkedin_posts"] = posts_data
                        existing["posts_scraped_at"] = datetime.now(timezone.utc).isoformat()

                        self.supabase.table("ff_ic_judges").update({
                            "research_profile": json.dumps(existing),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }).eq("id", jid).execute()

                        print(f"    + {judge['name']}: {len(posts_data)} posts")
                        self.stats["posts_stored"] += len(posts_data)
                    else:
                        print(f"    - {judge['name']}: no posts found")

            except Exception as e:
                print(f"    Apify posts error: {e}")
                self.stats["apify_errors"] += 1

        print(f"\n  Posts found: {self.stats['posts_found']}")
        print(f"  Posts stored: {self.stats['posts_stored']}")

    # ── Helpers ──────────────────────────────────────────────────────

    def _get_judges(self, needs_url=False, has_url=False) -> List[Dict]:
        """Fetch judges from ff_ic_judges table."""
        query = self.supabase.table("ff_ic_judges").select("*").order("id")

        if self.name_filter:
            query = query.eq("name", self.name_filter)

        response = query.execute()
        judges = response.data

        if needs_url:
            judges = [j for j in judges if not j.get("linkedin_url")]

        if has_url:
            judges = [j for j in judges if j.get("linkedin_url")]
            if not self.force:
                # Skip already enriched
                judges = [j for j in judges if not self._is_enriched(j)]

        if self.test_mode:
            judges = judges[:1]

        return judges

    def _is_enriched(self, judge: Dict) -> bool:
        """Check if a judge already has LinkedIn enrichment."""
        profile = judge.get("research_profile")
        if not profile:
            return False
        if isinstance(profile, str):
            profile = json.loads(profile)
        return "linkedin_enrichment" in profile

    def print_summary(self):
        s = self.stats
        print("\n" + "=" * 60)
        print("JUDGE ENRICHMENT SUMMARY")
        print("=" * 60)
        print(f"  URLs discovered:     {s['urls_discovered']}")
        print(f"  URLs not found:      {s['urls_not_found']}")
        print(f"  Profiles enriched:   {s['profiles_enriched']}")
        print(f"  Profiles failed:     {s['profiles_failed']}")
        print(f"  Posts found:         {s['posts_found']}")
        print(f"  Posts stored:        {s['posts_stored']}")
        print(f"  Apify errors:        {s['apify_errors']}")
        cost = (s["profiles_enriched"] * 0.004) + (s["posts_stored"] * 0.002)
        print(f"\n  ESTIMATED COST:      ~${cost:.2f}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Enrich Flourish Fund IC judges via LinkedIn"
    )
    parser.add_argument("--discover", action="store_true", help="Phase 1: Find LinkedIn URLs")
    parser.add_argument("--enrich", action="store_true", help="Phase 2: Apify profile enrichment")
    parser.add_argument("--posts", action="store_true", help="Phase 3: Apify post scraping")
    parser.add_argument("--all", action="store_true", help="Run all phases")
    parser.add_argument("--test", "-t", action="store_true", help="Test with 1 judge")
    parser.add_argument("--name", "-n", type=str, help="Process specific judge by name")
    parser.add_argument("--force", "-f", action="store_true", help="Re-enrich already enriched judges")

    args = parser.parse_args()

    if not any([args.discover, args.enrich, args.posts, args.all]):
        parser.print_help()
        sys.exit(1)

    enricher = JudgeEnricher(
        test_mode=args.test,
        name=args.name,
        force=args.force,
    )

    if not enricher.connect():
        sys.exit(1)

    if args.all or args.discover:
        enricher.discover_urls()

    if args.all or args.enrich:
        enricher.enrich_profiles()

    if args.all or args.posts:
        enricher.scrape_posts()

    enricher.print_summary()


if __name__ == "__main__":
    main()
