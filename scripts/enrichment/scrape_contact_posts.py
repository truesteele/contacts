#!/usr/bin/env python3
"""
Contacts Database - Apify LinkedIn Post Scraping Script

Scrapes LinkedIn posts for all enriched contacts using the Apify
harvestapi/linkedin-profile-posts actor. Stores posts in contact_linkedin_posts
table with upsert on (linkedin_url, post_url).

Follows Pipeline E concurrent batching pattern: multiple profile URLs per Apify
actor run, with ThreadPoolExecutor for concurrent runs.

Usage:
  python scripts/enrichment/scrape_contact_posts.py --test           # Test with 1 contact
  python scripts/enrichment/scrape_contact_posts.py --batch 50       # Process 50 contacts
  python scripts/enrichment/scrape_contact_posts.py --start-from 500 # Resume from id >= 500
  python scripts/enrichment/scrape_contact_posts.py --months 6       # Posts within last 6 months
  python scripts/enrichment/scrape_contact_posts.py --max-posts 25   # Max posts per contact
  python scripts/enrichment/scrape_contact_posts.py                  # Full run (all enriched contacts)
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote
from dotenv import load_dotenv
from supabase import create_client, Client
from apify_client import ApifyClient

load_dotenv()


class ContactPostScraper:
    POSTS_ACTOR = "harvestapi/linkedin-profile-posts"

    # Posts actor is heavier than profiles - use smaller batches
    BATCH_SIZE = 5       # Profile URLs per Apify actor run
    MAX_CONCURRENT = 8   # Concurrent actor runs

    def __init__(self, test_mode=False, batch_size=None, start_from=None,
                 post_months=6, max_posts=50, force=False):
        self.supabase: Optional[Client] = None
        self.apify: Optional[ApifyClient] = None
        self.test_mode = test_mode
        self.limit = batch_size
        self.start_from = start_from
        self.post_months = post_months
        self.max_posts = max_posts
        self.force = force
        self.cutoff = datetime.now(timezone.utc) - timedelta(days=post_months * 30)
        self.stats = {
            "contacts_processed": 0,
            "contacts_with_posts": 0,
            "contacts_no_posts": 0,
            "posts_found": 0,
            "posts_stored": 0,
            "posts_skipped_old": 0,
            "posts_skipped_empty": 0,
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
        """Fetch enriched contacts that need post scraping."""
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                self.supabase.table("contacts")
                .select("id, first_name, last_name, linkedin_url")
                .eq("enrichment_source", "apify")
                .neq("linkedin_url", "")
                .not_.is_("linkedin_url", "null")
                .order("id")
                .range(offset, offset + page_size - 1)
            )

            if self.start_from:
                query = query.gte("id", self.start_from)

            response = query.execute()
            page = response.data
            if not page:
                break

            all_contacts.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        if not self.force:
            # Filter out contacts that already have posts scraped
            existing = self._get_scraped_contact_ids()
            all_contacts = [c for c in all_contacts if c["id"] not in existing]

        if self.limit:
            all_contacts = all_contacts[:self.limit]

        return all_contacts

    def _get_scraped_contact_ids(self) -> set:
        """Get contact IDs that already have posts in the table."""
        ids = set()
        try:
            # Paginate to get all distinct contact_ids
            page_size = 1000
            offset = 0
            while True:
                resp = self.supabase.table("contact_linkedin_posts").select(
                    "contact_id"
                ).range(offset, offset + page_size - 1).execute()
                if not resp.data:
                    break
                ids.update(r["contact_id"] for r in resp.data if r.get("contact_id"))
                if len(resp.data) < page_size:
                    break
                offset += page_size
        except Exception:
            pass
        return ids

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

    # ── Post Scraping ────────────────────────────────────────────────

    def scrape_posts_batch(self, contacts: List[Dict]) -> Dict[int, List[Dict]]:
        """Scrape posts for multiple contacts in a single Apify actor run.
        Returns dict mapping contact_id -> list of raw post items."""
        urls = []
        url_to_contact = {}

        for c in contacts:
            norm_url = self._normalize_linkedin_url(c["linkedin_url"])
            urls.append(norm_url)
            username = self._extract_username(norm_url)
            url_to_contact[username] = c

        try:
            run_input = {
                "profileUrls": urls,
                "maxPosts": self.max_posts,
                "scrapeReactions": False,
                "scrapeComments": False,
                "includeReposts": False,
                "includeQuotePosts": True,
            }
            run = self.apify.actor(self.POSTS_ACTOR).call(run_input=run_input)
            items = list(self.apify.dataset(run["defaultDatasetId"]).iterate_items())

            # Group posts by profile
            results: Dict[int, List[Dict]] = {}
            unmatched = 0
            for item in items:
                # Extract author identifier from nested author object or query
                author = item.get("author") or {}
                public_id = (author.get("publicIdentifier") or "").strip().lower()
                author_url = (
                    author.get("linkedinUrl")
                    or item.get("authorUrl")
                    or item.get("profileUrl")
                    or ""
                )
                # Also check query.profilePublicIdentifier as fallback
                query = item.get("query") or {}
                query_profile = query.get("profilePublicIdentifier") or ""

                # Try publicIdentifier first (most reliable), then extract from URLs
                author_username = public_id or self._extract_username(author_url)
                if not author_username:
                    author_username = self._extract_username(query_profile)

                matched_contact = None

                # Only attempt matching if we have a non-empty username
                if author_username:
                    matched_contact = url_to_contact.get(author_username)

                    if not matched_contact:
                        for uname, contact in url_to_contact.items():
                            if uname and author_username == uname:
                                matched_contact = contact
                                break

                if matched_contact:
                    cid = matched_contact["id"]
                    if cid not in results:
                        results[cid] = []
                    results[cid].append(item)
                else:
                    unmatched += 1

            if unmatched > 0:
                print(f"    Warning: {unmatched} posts could not be matched to a contact")

            return results
        except Exception as e:
            print(f"    Apify posts batch error: {e}")
            self.stats["apify_errors"] += 1
            return {}

    def _parse_post_date(self, post: Dict) -> Optional[datetime]:
        """Parse post date from Apify's various formats."""
        posted_at = post.get("postedAt") or post.get("postedDate")
        if isinstance(posted_at, dict):
            ts = posted_at.get("timestamp")
            if ts:
                return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            date_str = posted_at.get("date")
            if date_str:
                try:
                    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    pass
        elif isinstance(posted_at, (int, float)):
            return datetime.fromtimestamp(posted_at / 1000, tz=timezone.utc)
        elif isinstance(posted_at, str):
            try:
                return datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
            except ValueError:
                pass
        return None

    def save_posts(self, contact_id: int, linkedin_url: str, raw_posts: List[Dict]) -> int:
        """Save posts to contact_linkedin_posts table. Returns count stored."""
        stored = 0
        norm_url = self._normalize_linkedin_url(linkedin_url)

        for post in raw_posts:
            self.stats["posts_found"] += 1

            post_date = self._parse_post_date(post)

            # Skip posts outside our time window
            if post_date and post_date < self.cutoff:
                self.stats["posts_skipped_old"] += 1
                continue

            post_url = post.get("linkedinUrl") or post.get("postUrl") or post.get("url")
            content = post.get("content") or post.get("text")

            if not post_url or not content:
                self.stats["posts_skipped_empty"] += 1
                continue

            # Engagement metrics
            eng = post.get("engagement") or {}
            likes = eng.get("likes", 0) or 0
            comments = eng.get("comments", 0) or 0
            shares = eng.get("shares", 0) or 0

            row = {
                "contact_id": contact_id,
                "linkedin_url": norm_url,
                "post_url": post_url,
                "post_content": content,
                "post_date": post_date.isoformat() if post_date else None,
                "engagement_likes": likes,
                "engagement_comments": comments,
                "engagement_shares": shares,
                "raw_data": json.dumps(post, default=str),
            }
            for attempt in range(3):
                try:
                    self.supabase.table("contact_linkedin_posts").upsert(
                        row, on_conflict="linkedin_url,post_url",
                    ).execute()
                    stored += 1
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(0.5 * (attempt + 1))
                    else:
                        print(f"    Post save error [{contact_id}]: {e}")
                        self.stats["db_errors"] += 1

        return stored

    # ── Batch Processing ─────────────────────────────────────────────

    def _process_batch(self, batch_contacts: List[Dict], batch_num: int, total_batches: int) -> None:
        """Process a batch of contacts: scrape posts and save."""
        names = ", ".join(f"{c['first_name']} {c['last_name']}" for c in batch_contacts[:3])
        if len(batch_contacts) > 3:
            names += f" +{len(batch_contacts) - 3} more"
        print(f"\n  Batch {batch_num}/{total_batches}: Scraping posts for {len(batch_contacts)} contacts ({names})...")

        results = self.scrape_posts_batch(batch_contacts)

        for c in batch_contacts:
            cid = c["id"]
            name = f"{c['first_name']} {c['last_name']}"
            self.stats["contacts_processed"] += 1

            posts = results.get(cid, [])
            if posts:
                stored = self.save_posts(cid, c["linkedin_url"], posts)
                self.stats["contacts_with_posts"] += 1
                self.stats["posts_stored"] += stored
                print(f"    [{cid}] {name}: {len(posts)} posts found, {stored} stored")
            else:
                self.stats["contacts_no_posts"] += 1
                print(f"    [{cid}] {name}: no posts")

    # ── Main Runner ──────────────────────────────────────────────────

    def run(self):
        if not self.connect():
            return False

        contacts = self.get_contacts()
        total = len(contacts)
        print(f"Found {total} contacts to scrape posts for")
        print(f"Settings: max {self.max_posts} posts/contact, last {self.post_months} months")

        if total == 0:
            print("Nothing to do.")
            return True

        if self.test_mode:
            contacts = contacts[:1]
            total = 1
            print("TEST MODE: Processing 1 contact only\n")

        # Cost estimate (rough: assumes avg 10 posts/contact at $0.002/post)
        est_cost_low = total * 5 * 0.002
        est_cost_high = total * 20 * 0.002
        print(f"Estimated cost: ~${est_cost_low:.2f}-${est_cost_high:.2f} (assuming 5-20 posts/contact at $0.002/post)")
        print(f"Strategy: {self.BATCH_SIZE} profiles/batch, {self.MAX_CONCURRENT} concurrent runs\n")

        # Split into batches
        batches = []
        for i in range(0, len(contacts), self.BATCH_SIZE):
            batches.append(contacts[i:i + self.BATCH_SIZE])

        total_batches = len(batches)
        start_time = time.time()
        print(f"Processing {total} contacts in {total_batches} batches...\n")

        with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
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

                elapsed = time.time() - start_time
                done = self.stats["contacts_processed"]
                rate = done / elapsed if elapsed > 0 else 0
                print(f"\n--- Progress: {done}/{total} contacts ({self.stats['posts_stored']} posts stored) [{rate:.1f} contacts/sec, {elapsed:.0f}s elapsed] ---")

        self.print_summary()
        return True

    def print_summary(self):
        s = self.stats
        print("\n" + "=" * 60)
        print("POST SCRAPING SUMMARY")
        print("=" * 60)
        print(f"  Contacts processed:   {s['contacts_processed']}")
        print(f"  Contacts with posts:  {s['contacts_with_posts']}")
        print(f"  Contacts no posts:    {s['contacts_no_posts']}")
        print(f"  Posts found:          {s['posts_found']}")
        print(f"  Posts stored:         {s['posts_stored']}")
        print(f"  Posts skipped (old):  {s['posts_skipped_old']}")
        print(f"  Posts skipped (empty):{s['posts_skipped_empty']}")
        print(f"  Apify errors:         {s['apify_errors']}")
        print(f"  DB errors:            {s['db_errors']}")
        post_cost = s["posts_found"] * 0.002
        print(f"\n  TOTAL COST:           ~${post_cost:.2f}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape LinkedIn posts for contacts via Apify"
    )
    parser.add_argument("--test", "-t", action="store_true", help="Test with 1 contact")
    parser.add_argument("--batch", "-b", type=int, help="Limit to N contacts")
    parser.add_argument("--start-from", "-s", type=int, help="Start from contact id >= N")
    parser.add_argument("--months", "-m", type=int, default=6, help="Months of posts to keep (default: 6)")
    parser.add_argument("--max-posts", type=int, default=15, help="Max posts per contact (default: 15)")
    parser.add_argument("--force", "-f", action="store_true", help="Re-scrape contacts that already have posts")
    args = parser.parse_args()

    scraper = ContactPostScraper(
        test_mode=args.test,
        batch_size=args.batch,
        start_from=args.start_from,
        post_months=args.months,
        max_posts=args.max_posts,
        force=args.force,
    )
    success = scraper.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
