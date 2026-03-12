"""
Scrape LinkedIn post reactions using Apify and save to Supabase.
Matches reactors to contacts using 3-pass strategy: exact → fuzzy → GPT-5 mini.

Usage:
  python scrape_post_reactions.py                    # All posts since Nov 2024
  python scrape_post_reactions.py --limit 5          # Test with 5 posts
  python scrape_post_reactions.py --since 2025-06-01 # Custom date cutoff
  python scrape_post_reactions.py --dry-run           # Show what would be scraped
  python scrape_post_reactions.py --match-only        # Re-run matching on existing data
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone

from dotenv import load_dotenv
from apify_client import ApifyClient
from openai import OpenAI
from supabase import create_client, Client

from contact_matcher import ContactMatcher, normalize_name, split_first_last

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")

APIFY_KEY = os.getenv("APIFY_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_KEY = os.getenv("OPENAI_APIKEY")
SHARES_CSV = "/Users/Justin/Code/TrueSteele/contacts/docs/LinkedIn/Justin Posts/Shares.csv"

REACTIONS_ACTOR = "apimaestro/linkedin-post-reactions"
REACTIONS_PER_PAGE = 100
BATCH_SIZE = 15
GPT_WORKERS = 50


# ── CSV loading ──────────────────────────────────────────────────────

def load_posts(since_date):
    posts = []
    with open(SHARES_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row.get("Date", "").strip()
            link = row.get("ShareLink", "").strip()
            commentary = row.get("ShareCommentary", "").strip()
            if not date_str or not link:
                continue
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            if dt < since_date:
                continue
            decoded_link = urllib.parse.unquote(link)
            snippet = commentary.replace('"', '').replace('\n', ' ')[:150]
            posts.append({"date": dt, "url": decoded_link, "snippet": snippet})
    return sorted(posts, key=lambda x: x["date"], reverse=True)


# ── Apify scraping ──────────────────────────────────────────────────

def scrape_reactions_batch(client, post_urls, page_number=1):
    run_input = {
        "post_urls": post_urls,
        "limit": REACTIONS_PER_PAGE,
        "page_number": page_number,
        "reaction_type": "ALL",
    }
    run = client.actor(REACTIONS_ACTOR).call(run_input=run_input)
    if run.get("status") != "SUCCEEDED":
        print(f"  WARNING: Actor run status: {run.get('status')}")
        return []
    return list(client.dataset(run["defaultDatasetId"]).iterate_items())


def scrape_all_reactions(client, posts):
    all_reactions = []
    post_urls = [p["url"] for p in posts]
    post_date_map = {p["url"]: p["date"] for p in posts}
    post_snippet_map = {p["url"]: p["snippet"] for p in posts}

    for batch_start in range(0, len(post_urls), BATCH_SIZE):
        batch_urls = post_urls[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(post_urls) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n--- Batch {batch_num}/{total_batches}: {len(batch_urls)} posts ---")

        items = scrape_reactions_batch(client, batch_urls, page_number=1)
        print(f"  Page 1: {len(items)} reactions")

        # Check which posts need pagination
        posts_needing_more = {}
        for item in items:
            meta = item.get("_metadata", {})
            post_url = meta.get("post_url", "")
            total_reactions = meta.get("total_reactions", 0)
            if total_reactions > REACTIONS_PER_PAGE:
                posts_needing_more[post_url] = total_reactions

        all_reactions.extend(items)

        if posts_needing_more:
            print(f"  {len(posts_needing_more)} posts need pagination (>100 reactions)")
            for post_url, total in posts_needing_more.items():
                page = 2
                while True:
                    print(f"  Paginating ...{post_url[-30:]} page {page} (total: {total})")
                    page_items = scrape_reactions_batch(client, [post_url], page_number=page)
                    if not page_items:
                        break
                    all_reactions.extend(page_items)
                    print(f"    Got {len(page_items)} more reactions")
                    if len(page_items) < REACTIONS_PER_PAGE:
                        break
                    page += 1
                    time.sleep(1)

        if batch_start + BATCH_SIZE < len(post_urls):
            time.sleep(2)

    # Attach metadata
    for item in all_reactions:
        post_url = item.get("_metadata", {}).get("post_url") or item.get("input", "")
        item["_post_date"] = post_date_map.get(post_url)
        item["_post_snippet"] = post_snippet_map.get(post_url, "")

    return all_reactions



# ContactMatcher imported from contact_matcher.py


# ── Supabase save ────────────────────────────────────────────────────

def save_reactions(sb: Client, reactions: list[dict]):
    print(f"\nSaving {len(reactions)} reactions to Supabase...")

    # Deduplicate by (post_url, reactor_linkedin_urn) — pagination can cause overlaps
    seen = set()
    deduped = []
    for r in reactions:
        reactor = r.get("reactor", {})
        post_url = r.get("_metadata", {}).get("post_url") or r.get("input", "")
        reactor_urn = reactor.get("urn", "")

        if not reactor.get("name") or not post_url or not reactor_urn:
            continue

        key = (post_url, reactor_urn)
        if key in seen:
            continue
        seen.add(key)

        post_date = r.get("_post_date")
        if isinstance(post_date, datetime):
            post_date = post_date.isoformat()

        deduped.append({
            "post_url": post_url,
            "post_date": post_date,
            "post_snippet": (r.get("_post_snippet") or "")[:150],
            "reactor_name": reactor.get("name", ""),
            "reactor_headline": (reactor.get("headline") or "")[:500] or None,
            "reactor_linkedin_urn": reactor_urn,
            "reaction_type": r.get("reaction_type", "LIKE"),
            "contact_id": r.get("_contact_id"),
            "match_method": r.get("_match_method"),
            "match_confidence": r.get("_match_confidence"),
        })

    print(f"  Deduplicated: {len(reactions)} -> {len(deduped)} unique reactions")

    saved = 0
    batch_size = 200
    for i in range(0, len(deduped), batch_size):
        batch = deduped[i:i + batch_size]
        sb.table("post_reactions").upsert(
            batch, on_conflict="post_url,reactor_linkedin_urn"
        ).execute()
        saved += len(batch)
        if saved % 1000 == 0 or saved == len(deduped):
            print(f"  Saved {saved}/{len(deduped)}...")

    print(f"  Total saved: {saved}")
    return saved


# ── Summary ──────────────────────────────────────────────────────────

def print_summary(reactions: list[dict], matcher: ContactMatcher):
    print("\n" + "=" * 80)
    print("POST REACTIONS SCRAPE — SUMMARY")
    print("=" * 80)

    by_post = defaultdict(list)
    for r in reactions:
        post_url = r.get("_metadata", {}).get("post_url") or r.get("input", "")
        by_post[post_url].append(r)

    print(f"\nPosts scraped: {len(by_post)}")
    print(f"Total reactions: {len(reactions)}")

    types = Counter(r.get("reaction_type", "?") for r in reactions)
    print(f"Reaction types: {dict(types)}")

    # Top posts
    print(f"\nTop 10 posts by reactions:")
    sorted_posts = sorted(by_post.items(), key=lambda x: len(x[1]), reverse=True)
    for post_url, post_reactions in sorted_posts[:10]:
        total = post_reactions[0].get("_metadata", {}).get("total_reactions", len(post_reactions))
        snippet = (post_reactions[0].get("_post_snippet") or "")[:55]
        date = post_reactions[0].get("_post_date", "")
        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")
        print(f"  {total:4d} | {str(date):10s} | {snippet}...")

    # Matching stats
    total_matched = matcher.stats["exact"] + matcher.stats["fuzzy"] + matcher.stats["gpt"]
    total_processed = total_matched + matcher.stats["unmatched"]
    pct = (total_matched / total_processed * 100) if total_processed else 0

    print(f"\nMATCHING:")
    print(f"  Exact:     {matcher.stats['exact']}")
    print(f"  Fuzzy:     {matcher.stats['fuzzy']}")
    print(f"  GPT:       {matcher.stats['gpt']}")
    print(f"  Unmatched: {matcher.stats['unmatched']}")
    print(f"  Total:     {total_matched}/{total_processed} ({pct:.1f}%)")
    matcher.print_cost()

    # Most engaged contacts
    contact_engagement = Counter()
    contact_names = {}
    for r in reactions:
        cid = r.get("_contact_id")
        if cid:
            contact_engagement[cid] += 1
            contact_names[cid] = r.get("reactor", {}).get("name", "?")

    print(f"\nTop 20 most engaged contacts:")
    for cid, count in contact_engagement.most_common(20):
        print(f"  {count:2d} reactions | {contact_names[cid]}")

    # Top unmatched (new connection opportunities)
    unmatched_names = []
    for r in reactions:
        if not r.get("_contact_id"):
            reactor = r.get("reactor", {})
            name = reactor.get("name", "")
            if name:
                unmatched_names.append((name, reactor.get("headline", "")[:50]))

    unmatched_counts = Counter(n for n, _ in unmatched_names)
    print(f"\nTop 20 unmatched reactors (potential new connections):")
    # Get headline for each
    name_headlines = {}
    for n, h in unmatched_names:
        if n not in name_headlines:
            name_headlines[n] = h
    for name, count in unmatched_counts.most_common(20):
        print(f"  {count:2d}x | {name:30s} | {name_headlines.get(name, '')}")

    print("=" * 80)


# ── Re-match existing data ───────────────────────────────────────────

def rematch_existing(sb: Client, openai_client: OpenAI):
    """Re-run matching on reactions already in DB."""
    print("Loading existing reactions from DB...")
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        page = (
            sb.table("post_reactions")
            .select("id, reactor_name, reactor_headline, reactor_linkedin_urn, contact_id")
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        ).data
        if not page:
            break
        all_rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size

    print(f"Loaded {len(all_rows)} reactions")

    # Convert to the format matcher expects
    reactions = []
    for row in all_rows:
        reactions.append({
            "reactor": {
                "name": row["reactor_name"],
                "headline": row.get("reactor_headline", ""),
                "urn": row.get("reactor_linkedin_urn", ""),
            },
            "_db_id": row["id"],
        })

    matcher = ContactMatcher(sb, openai_client)
    matcher.load_contacts()
    reactions = matcher.match_all(reactions)

    # Update DB
    print("\nUpdating matches in DB...")
    updated = 0
    for r in reactions:
        db_id = r.get("_db_id")
        if not db_id:
            continue
        try:
            sb.table("post_reactions").update({
                "contact_id": r.get("_contact_id"),
                "match_method": r.get("_match_method"),
                "match_confidence": r.get("_match_confidence"),
            }).eq("id", db_id).execute()
            updated += 1
        except Exception as e:
            print(f"  Update error for id {db_id}: {e}")

    print(f"Updated {updated} reactions")

    total_matched = matcher.stats["exact"] + matcher.stats["fuzzy"] + matcher.stats["gpt"]
    total_processed = total_matched + matcher.stats["unmatched"]
    pct = (total_matched / total_processed * 100) if total_processed else 0
    print(f"\nMatching: {total_matched}/{total_processed} ({pct:.1f}%)")
    print(f"  Exact: {matcher.stats['exact']}, Fuzzy: {matcher.stats['fuzzy']}, "
          f"GPT: {matcher.stats['gpt']}, Unmatched: {matcher.stats['unmatched']}")
    matcher.print_cost()


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scrape LinkedIn post reactions")
    parser.add_argument("--since", default="2024-11-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, help="Limit number of posts")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be scraped")
    parser.add_argument("--match-only", action="store_true", help="Re-run matching on existing data")
    parser.add_argument("--json-output", help="Save raw reactions to JSON")
    parser.add_argument("--workers", type=int, default=GPT_WORKERS, help="GPT workers")
    args = parser.parse_args()

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    openai_client = OpenAI(api_key=OPENAI_KEY)

    if args.match_only:
        rematch_existing(sb, openai_client)
        return

    since_date = datetime.strptime(args.since, "%Y-%m-%d")
    posts = load_posts(since_date)
    print(f"Found {len(posts)} posts since {args.since}")

    if args.limit:
        posts = posts[:args.limit]
        print(f"Limited to {args.limit} posts")

    if args.dry_run:
        print("\n--- DRY RUN ---")
        for p in posts:
            print(f"  {p['date'].date()} | {p['snippet'][:60]}...")
        return

    if not posts:
        print("No posts to scrape.")
        return

    if not APIFY_KEY:
        raise RuntimeError("APIFY_API_KEY not found in .env")
    apify = ApifyClient(APIFY_KEY)

    # Scrape
    print(f"\nScraping reactions for {len(posts)} posts...")
    reactions = scrape_all_reactions(apify, posts)

    if not reactions:
        print("No reactions found!")
        return

    print(f"\nScraped {len(reactions)} total reactions")

    # Match
    matcher = ContactMatcher(sb, openai_client, workers=args.workers)
    matcher.load_contacts()
    reactions = matcher.match_all(reactions)

    # Save
    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(reactions, f, indent=2, default=str)
        print(f"Raw JSON saved to {args.json_output}")

    save_reactions(sb, reactions)

    # Summary
    print_summary(reactions, matcher)
    print("\nDone!")


if __name__ == "__main__":
    main()
