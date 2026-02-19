#!/usr/bin/env python3
"""
Camelback Expert Bench - LinkedIn Enrichment Script

Uses Apify actors to:
1. Enrich LinkedIn profiles (harvestapi/linkedin-profile-scraper) - $0.004/profile
2. Scrape recent LinkedIn posts (harvestapi/linkedin-profile-posts) - $0.002/post

Usage:
  python scripts/enrichment/enrich_camelback_experts.py --test        # Test with 1 expert
  python scripts/enrichment/enrich_camelback_experts.py               # Full run (all 73)
  python scripts/enrichment/enrich_camelback_experts.py --posts-only  # Only scrape posts
  python scripts/enrichment/enrich_camelback_experts.py --profiles-only  # Only enrich profiles
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from apify_client import ApifyClient

load_dotenv()


class CamelbackEnricher:
    PROFILE_ACTOR = "harvestapi/linkedin-profile-scraper"
    POSTS_ACTOR = "harvestapi/linkedin-profile-posts"

    def __init__(self, test_mode=False, posts_only=False, profiles_only=False, post_months=4):
        self.supabase: Optional[Client] = None
        self.apify: Optional[ApifyClient] = None
        self.test_mode = test_mode
        self.posts_only = posts_only
        self.profiles_only = profiles_only
        self.post_months = post_months
        self.stats = {
            "profiles_enriched": 0,
            "profiles_failed": 0,
            "profiles_skipped": 0,
            "posts_found": 0,
            "posts_stored": 0,
            "posts_failed": 0,
            "experts_with_no_posts": 0,
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

    def get_experts(self) -> List[Dict]:
        response = (
            self.supabase.table("camelback_experts")
            .select("*")
            .order("id")
            .execute()
        )
        return response.data

    # ── Profile Enrichment ──────────────────────────────────────────

    def enrich_profile(self, linkedin_url: str) -> Optional[Dict]:
        try:
            run_input = {"urls": [linkedin_url]}
            run = self.apify.actor(self.PROFILE_ACTOR).call(run_input=run_input)
            items = list(self.apify.dataset(run["defaultDatasetId"]).iterate_items())
            if items:
                return items[0]
            return None
        except Exception as e:
            print(f"    Apify profile error: {e}")
            return None

    def _parse_date_range(self, date_range: dict) -> str:
        if not date_range:
            return None
        start = date_range.get("start", {})
        if start:
            parts = []
            if start.get("year"):
                parts.append(str(start["year"]))
            if start.get("month"):
                parts.append(str(start["month"]).zfill(2))
            return "-".join(parts) if parts else None
        return None

    def map_profile_to_updates(self, raw: Dict) -> Dict:
        updates = {}

        updates["headline"] = raw.get("headline")
        updates["about"] = raw.get("about")
        updates["profile_picture_url"] = raw.get("photo")
        updates["follower_count"] = raw.get("followerCount")
        updates["connections"] = raw.get("connectionsCount")
        updates["linkedin_username"] = raw.get("publicIdentifier")

        # Employment from experience[]
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
                "start_date": f"{start.get('year', '')}-{str(start.get('month', '')).zfill(2)}" if start and start.get("year") else None,
                "end_date": f"{end.get('year', '')}-{str(end.get('month', '')).zfill(2)}" if end and end.get("year") else None,
                "is_current": end is None or end == {},
                "description": exp.get("description"),
                "employment_type": exp.get("employmentType"),
                "duration": exp.get("duration"),
            })
        if employment:
            updates["employment"] = json.dumps(employment)

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
        if education:
            updates["education"] = json.dumps(education)

        # Skills - array of {name: "..."}
        skills = raw.get("skills") or []
        if skills:
            skill_list = []
            for s in skills:
                if isinstance(s, str):
                    skill_list.append({"skill_name": s})
                elif isinstance(s, dict):
                    skill_list.append({"skill_name": s.get("name")})
            updates["skills_enriched"] = json.dumps(skill_list)

        # Certifications
        certs = raw.get("certifications") or []
        if certs:
            updates["certifications"] = json.dumps([{
                "name": c.get("name"),
                "organization": c.get("authority") or c.get("organization"),
                "url": c.get("url"),
            } for c in certs])

        # Volunteering
        volunteer = raw.get("volunteering") or raw.get("volunteerExperience") or []
        if volunteer:
            updates["volunteering"] = json.dumps([{
                "organization": v.get("companyName") or v.get("company") or v.get("organization"),
                "role": v.get("title") or v.get("role"),
                "cause": v.get("cause"),
            } for v in volunteer])

        # Publications
        pubs = raw.get("publications") or []
        if pubs:
            updates["publications"] = json.dumps([{
                "name": p.get("name") or p.get("title"),
                "publisher": p.get("publisher"),
                "url": p.get("url"),
            } for p in pubs])

        # Honors/Awards
        honors = raw.get("honorsAndAwards") or raw.get("honors") or []
        if honors:
            updates["honors_awards"] = json.dumps([{
                "title": h.get("title") or h.get("name"),
                "issuer": h.get("issuer"),
            } for h in honors])

        # Languages
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
            updates["languages"] = json.dumps(lang_list)

        # Projects
        projects = raw.get("projects") or []
        if projects:
            updates["projects"] = json.dumps([{
                "name": p.get("title") or p.get("name"),
                "description": p.get("description"),
                "url": p.get("url"),
            } for p in projects])

        updates["enriched_at"] = datetime.now(timezone.utc).isoformat()
        updates["enrichment_source"] = "apify"

        # Remove None values
        return {k: v for k, v in updates.items() if v is not None}

    def save_profile(self, expert_id: int, updates: Dict) -> bool:
        try:
            self.supabase.table("camelback_experts").update(updates).eq("id", expert_id).execute()
            return True
        except Exception as e:
            print(f"    DB update error: {e}")
            return False

    # ── Post Scraping ───────────────────────────────────────────────

    def scrape_posts(self, linkedin_url: str, max_posts: int = 50) -> List[Dict]:
        try:
            run_input = {
                "profileUrls": [linkedin_url],
                "maxPosts": max_posts,
                "scrapeReactions": False,
                "scrapeComments": False,
                "includeReposts": False,
                "includeQuotePosts": True,
            }
            run = self.apify.actor(self.POSTS_ACTOR).call(run_input=run_input)
            items = list(self.apify.dataset(run["defaultDatasetId"]).iterate_items())
            return items
        except Exception as e:
            print(f"    Apify posts error: {e}")
            return []

    def save_posts(self, expert_id: int, linkedin_url: str, raw_posts: List[Dict]) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.post_months * 30)
        stored = 0

        for post in raw_posts:
            # Parse post date from postedAt.timestamp (ms) or postedAt.date (ISO string)
            post_date = None
            posted_at = post.get("postedAt")
            if isinstance(posted_at, dict):
                ts = posted_at.get("timestamp")
                if ts:
                    post_date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                elif posted_at.get("date"):
                    try:
                        post_date = datetime.fromisoformat(posted_at["date"].replace("Z", "+00:00"))
                    except ValueError:
                        pass
            elif isinstance(posted_at, (int, float)):
                post_date = datetime.fromtimestamp(posted_at / 1000, tz=timezone.utc)

            # Skip posts outside our window
            if post_date and post_date < cutoff:
                continue

            post_url = post.get("linkedinUrl") or post.get("postUrl")
            content = post.get("content") or post.get("text")

            if not post_url or not content:
                continue

            # Engagement is a nested dict: {likes, comments, shares}
            eng = post.get("engagement") or {}
            engagement = {
                "likes": eng.get("likes", 0),
                "comments": eng.get("comments", 0),
                "shares": eng.get("shares", 0),
            }

            try:
                self.supabase.table("camelback_expert_posts").upsert(
                    {
                        "expert_id": expert_id,
                        "linkedin_url": linkedin_url,
                        "post_content": content,
                        "post_date": post_date.isoformat() if post_date else None,
                        "post_url": post_url,
                        "engagement_metrics": json.dumps(engagement),
                    },
                    on_conflict="linkedin_url,post_url",
                ).execute()
                stored += 1
            except Exception as e:
                print(f"    Post save error: {e}")

        return stored

    # ── Main Runner ─────────────────────────────────────────────────

    def run(self):
        if not self.connect():
            return False

        experts = self.get_experts()
        total = len(experts)
        print(f"Found {total} experts in camelback_experts")

        if self.test_mode:
            experts = experts[:1]
            print("TEST MODE: Processing 1 expert only\n")
        else:
            print()

        for i, expert in enumerate(experts, 1):
            name = expert["name"]
            linkedin_url = expert.get("linkedin_url")
            expert_id = expert["id"]

            print(f"[{i}/{len(experts)}] {name}")
            print(f"  {linkedin_url}")

            if not linkedin_url:
                print("  SKIP: No LinkedIn URL")
                self.stats["profiles_skipped"] += 1
                continue

            # ── Profile ──
            if not self.posts_only:
                already_enriched = expert.get("enriched_at") is not None
                if already_enriched and not self.test_mode:
                    print("  Profile: Already enriched, skipping")
                    self.stats["profiles_skipped"] += 1
                else:
                    print("  Profile: Fetching from Apify...")
                    raw_profile = self.enrich_profile(linkedin_url)
                    if raw_profile:
                        updates = self.map_profile_to_updates(raw_profile)
                        if self.save_profile(expert_id, updates):
                            field_count = len(updates)
                            print(f"  Profile: Saved ({field_count} fields)")
                            if updates.get("headline"):
                                print(f"    Headline: {updates['headline'][:80]}")
                            self.stats["profiles_enriched"] += 1
                        else:
                            self.stats["profiles_failed"] += 1
                    else:
                        print("  Profile: No data returned")
                        self.stats["profiles_failed"] += 1

            # ── Posts ──
            if not self.profiles_only:
                print(f"  Posts: Fetching last {self.post_months} months...")
                raw_posts = self.scrape_posts(linkedin_url)
                if raw_posts:
                    stored = self.save_posts(expert_id, linkedin_url, raw_posts)
                    self.stats["posts_found"] += len(raw_posts)
                    self.stats["posts_stored"] += stored
                    print(f"  Posts: {len(raw_posts)} found, {stored} stored (within {self.post_months}mo window)")
                else:
                    print("  Posts: None found")
                    self.stats["experts_with_no_posts"] += 1

            # Small delay between experts to be nice to the API
            if not self.test_mode and i < len(experts):
                time.sleep(1)

        self.print_summary()
        return True

    def print_summary(self):
        s = self.stats
        print("\n" + "=" * 60)
        print("ENRICHMENT SUMMARY")
        print("=" * 60)

        if not self.posts_only:
            print(f"  Profiles enriched:  {s['profiles_enriched']}")
            print(f"  Profiles failed:    {s['profiles_failed']}")
            print(f"  Profiles skipped:   {s['profiles_skipped']}")
            profile_cost = s["profiles_enriched"] * 0.004
            print(f"  Profile cost:       ~${profile_cost:.2f}")

        if not self.profiles_only:
            print(f"  Posts found:        {s['posts_found']}")
            print(f"  Posts stored:       {s['posts_stored']}")
            print(f"  No posts:           {s['experts_with_no_posts']}")
            post_cost = s["posts_found"] * 0.002
            print(f"  Post cost:          ~${post_cost:.2f}")

        total_cost = (
            (s["profiles_enriched"] * 0.004 if not self.posts_only else 0)
            + (s["posts_found"] * 0.002 if not self.profiles_only else 0)
        )
        print(f"\n  TOTAL COST:         ~${total_cost:.2f}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Enrich Camelback experts via Apify")
    parser.add_argument("--test", "-t", action="store_true", help="Test with 1 expert")
    parser.add_argument("--posts-only", action="store_true", help="Only scrape posts")
    parser.add_argument("--profiles-only", action="store_true", help="Only enrich profiles")
    parser.add_argument("--months", type=int, default=4, help="Months of posts to fetch (default: 4)")
    args = parser.parse_args()

    enricher = CamelbackEnricher(
        test_mode=args.test,
        posts_only=args.posts_only,
        profiles_only=args.profiles_only,
        post_months=args.months,
    )
    success = enricher.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
