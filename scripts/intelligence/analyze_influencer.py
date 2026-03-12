"""
Analyze an influencer's LinkedIn posts: scrape posts + reactions, match to contacts DB.

Usage:
  python analyze_influencer.py https://www.linkedin.com/in/kevinlbrown/
  python analyze_influencer.py kevinlbrown --months 6 --max-posts 100
  python analyze_influencer.py kevinlbrown --skip-reactions
  python analyze_influencer.py kevinlbrown --report-only
"""
import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote

from dotenv import load_dotenv
from apify_client import ApifyClient
from openai import OpenAI
from supabase import create_client, Client

from contact_matcher import ContactMatcher

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")

POSTS_ACTOR = "harvestapi/linkedin-profile-posts"
REACTIONS_ACTOR = "apimaestro/linkedin-post-reactions"
REACTIONS_PER_PAGE = 100
REACTIONS_BATCH_SIZE = 15


def normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    url = unquote(url)
    if not url.startswith("http"):
        url = f"https://www.linkedin.com/in/{url}"
    url = url.replace("://linkedin.com/", "://www.linkedin.com/")
    return url


def extract_username(url: str) -> str:
    url = unquote(url).rstrip("/").lower()
    if "/in/" in url:
        return url.split("/in/")[-1].split("?")[0]
    return url


# ── Phase 1: Scrape Posts ───────────────────────────────────────────

def scrape_posts(apify: ApifyClient, influencer_url: str, max_posts: int, months: int):
    print(f"\n{'='*70}")
    print(f"PHASE 1: Scraping posts for {influencer_url}")
    print(f"  Max posts: {max_posts}, Window: last {months} months")
    print(f"{'='*70}")

    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

    run_input = {
        "profileUrls": [influencer_url],
        "maxPosts": max_posts,
        "scrapeReactions": False,
        "scrapeComments": False,
        "includeReposts": False,
        "includeQuotePosts": True,
    }

    print(f"  Starting Apify actor {POSTS_ACTOR}...")
    run = apify.actor(POSTS_ACTOR).call(run_input=run_input)
    print(f"  Run status: {run.get('status')}")

    items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"  Raw items returned: {len(items)}")

    # Extract influencer name from first post
    influencer_name = None
    if items:
        author = items[0].get("author") or {}
        influencer_name = author.get("name") or author.get("firstName", "")

    posts = []
    skipped_old = 0
    skipped_empty = 0

    for item in items:
        post_date = _parse_post_date(item)
        if post_date and post_date < cutoff:
            skipped_old += 1
            continue

        post_url = item.get("linkedinUrl") or item.get("postUrl") or item.get("url")
        content = item.get("content") or item.get("text")
        if not post_url or not content:
            skipped_empty += 1
            continue

        eng = item.get("engagement") or {}
        likes = eng.get("likes", 0) or 0
        comments = eng.get("comments", 0) or 0
        shares = eng.get("shares", 0) or 0

        media_type = _detect_media_type(item)

        posts.append({
            "influencer_url": influencer_url,
            "influencer_name": influencer_name,
            "post_url": post_url,
            "post_content": content,
            "post_date": post_date.isoformat() if post_date else None,
            "engagement_likes": likes,
            "engagement_comments": comments,
            "engagement_shares": shares,
            "media_type": media_type,
            "raw_data": item,
        })

    print(f"  Posts in window: {len(posts)}")
    print(f"  Skipped (old): {skipped_old}, Skipped (empty): {skipped_empty}")

    return posts, influencer_name


def _parse_post_date(post: dict) -> datetime | None:
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


def _detect_media_type(item: dict) -> str:
    content = item.get("content") or item.get("text") or ""
    images = item.get("images") or item.get("image") or []
    video = item.get("video") or item.get("videoUrl")
    article = item.get("article") or item.get("sharedArticle")
    carousel = item.get("document") or item.get("carousel")

    if carousel:
        return "carousel"
    if video:
        return "video"
    if article:
        return "article"
    if images:
        return "image"
    return "text"


# ── Phase 2: Scrape Reactions ────────────────────────────────────────

def scrape_reactions(apify: ApifyClient, posts: list[dict]):
    print(f"\n{'='*70}")
    print(f"PHASE 2: Scraping reactions for {len(posts)} posts")
    print(f"{'='*70}")

    post_urls = [p["post_url"] for p in posts]
    post_date_map = {p["post_url"]: p["post_date"] for p in posts}

    all_reactions = []

    for batch_start in range(0, len(post_urls), REACTIONS_BATCH_SIZE):
        batch_urls = post_urls[batch_start:batch_start + REACTIONS_BATCH_SIZE]
        batch_num = batch_start // REACTIONS_BATCH_SIZE + 1
        total_batches = (len(post_urls) + REACTIONS_BATCH_SIZE - 1) // REACTIONS_BATCH_SIZE
        print(f"\n  Batch {batch_num}/{total_batches}: {len(batch_urls)} posts")

        run_input = {
            "post_urls": batch_urls,
            "limit": REACTIONS_PER_PAGE,
            "page_number": 1,
            "reaction_type": "ALL",
        }
        run = apify.actor(REACTIONS_ACTOR).call(run_input=run_input)
        if run.get("status") != "SUCCEEDED":
            print(f"  WARNING: Actor run status: {run.get('status')}")
            continue

        items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"  Page 1: {len(items)} reactions")

        # Check pagination needs
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
                    print(f"    Paginating ...{post_url[-30:]} page {page} (total: {total})")
                    page_input = {
                        "post_urls": [post_url],
                        "limit": REACTIONS_PER_PAGE,
                        "page_number": page,
                        "reaction_type": "ALL",
                    }
                    page_run = apify.actor(REACTIONS_ACTOR).call(run_input=page_input)
                    if page_run.get("status") != "SUCCEEDED":
                        break
                    page_items = list(apify.dataset(page_run["defaultDatasetId"]).iterate_items())
                    if not page_items:
                        break
                    all_reactions.extend(page_items)
                    print(f"    Got {len(page_items)} more reactions")
                    if len(page_items) < REACTIONS_PER_PAGE:
                        break
                    page += 1
                    time.sleep(1)

        if batch_start + REACTIONS_BATCH_SIZE < len(post_urls):
            time.sleep(2)

    # Attach post dates
    for item in all_reactions:
        post_url = item.get("_metadata", {}).get("post_url") or item.get("input", "")
        item["_post_date"] = post_date_map.get(post_url)

    print(f"\n  Total reactions scraped: {len(all_reactions)}")
    return all_reactions


# ── Phase 3: Match + Save ────────────────────────────────────────────

def match_and_save(sb: Client, openai_client: OpenAI, influencer_url: str,
                   posts: list[dict], reactions: list[dict], workers: int):
    print(f"\n{'='*70}")
    print(f"PHASE 3: Matching reactors to contacts + saving")
    print(f"{'='*70}")

    # Save posts
    print(f"\n  Saving {len(posts)} posts...")
    saved_posts = 0
    for p in posts:
        row = {
            "influencer_url": p["influencer_url"],
            "influencer_name": p["influencer_name"],
            "post_url": p["post_url"],
            "post_content": p["post_content"],
            "post_date": p["post_date"],
            "engagement_likes": p["engagement_likes"],
            "engagement_comments": p["engagement_comments"],
            "engagement_shares": p["engagement_shares"],
            "media_type": p["media_type"],
            "raw_data": json.dumps(p["raw_data"], default=str),
        }
        try:
            sb.table("influencer_posts").upsert(
                row, on_conflict="influencer_url,post_url"
            ).execute()
            saved_posts += 1
        except Exception as e:
            print(f"    Post save error: {e}")
    print(f"  Posts saved: {saved_posts}")

    if not reactions:
        return None

    # Match reactions to contacts
    matcher = ContactMatcher(sb, openai_client, workers=workers)
    matcher.load_contacts()

    # Normalize reaction format for matcher
    for r in reactions:
        reactor_data = r.get("reactor", {})
        if not reactor_data and r.get("name"):
            r["reactor"] = {
                "name": r.get("name", ""),
                "headline": r.get("headline", ""),
                "urn": r.get("urn", ""),
            }

    reactions = matcher.match_all(reactions)

    # Deduplicate and save reactions
    print(f"\n  Saving reactions...")
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
            "influencer_url": influencer_url,
            "post_url": post_url,
            "post_date": post_date,
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
        sb.table("influencer_post_reactions").upsert(
            batch, on_conflict="post_url,reactor_linkedin_urn"
        ).execute()
        saved += len(batch)
        if saved % 1000 == 0 or saved == len(deduped):
            print(f"  Saved {saved}/{len(deduped)}...")

    print(f"  Reactions saved: {saved}")
    return matcher


# ── Phase 4: Analysis Report ─────────────────────────────────────────

def print_report(sb: Client, influencer_url: str, influencer_name: str = None):
    print(f"\n{'='*70}")
    print(f"INFLUENCER ANALYSIS REPORT")
    if influencer_name:
        print(f"  {influencer_name} ({influencer_url})")
    else:
        print(f"  {influencer_url}")
    print(f"{'='*70}")

    # Load posts from DB
    posts = []
    offset = 0
    while True:
        page = sb.table("influencer_posts").select("*") \
            .eq("influencer_url", influencer_url) \
            .order("post_date", desc=True) \
            .range(offset, offset + 999).execute().data
        if not page:
            break
        posts.extend(page)
        if len(page) < 1000:
            break
        offset += 1000

    if not posts:
        print("\n  No posts found in DB for this influencer.")
        return

    # Load reactions from DB
    reactions = []
    offset = 0
    while True:
        page = sb.table("influencer_post_reactions").select("*") \
            .eq("influencer_url", influencer_url) \
            .range(offset, offset + 999).execute().data
        if not page:
            break
        reactions.extend(page)
        if len(page) < 1000:
            break
        offset += 1000

    # ── Post Performance ──
    print(f"\n--- POST PERFORMANCE ({len(posts)} posts) ---")
    total_likes = sum(p.get("engagement_likes", 0) or 0 for p in posts)
    total_comments = sum(p.get("engagement_comments", 0) or 0 for p in posts)
    total_shares = sum(p.get("engagement_shares", 0) or 0 for p in posts)
    total_eng = total_likes + total_comments + total_shares

    print(f"  Total engagement: {total_eng:,} ({total_likes:,} likes, {total_comments:,} comments, {total_shares:,} shares)")
    print(f"  Avg per post: {total_eng / len(posts):.0f} total ({total_likes / len(posts):.0f} likes, {total_comments / len(posts):.0f} comments)")

    # Top posts
    sorted_posts = sorted(posts, key=lambda p: (p.get("engagement_likes", 0) or 0) + (p.get("engagement_comments", 0) or 0) + (p.get("engagement_shares", 0) or 0), reverse=True)

    print(f"\n  Top 10 posts by engagement:")
    for p in sorted_posts[:10]:
        eng = (p.get("engagement_likes", 0) or 0) + (p.get("engagement_comments", 0) or 0) + (p.get("engagement_shares", 0) or 0)
        likes = p.get("engagement_likes", 0) or 0
        comments = p.get("engagement_comments", 0) or 0
        date = (p.get("post_date") or "")[:10]
        snippet = (p.get("post_content") or "")[:60].replace("\n", " ")
        media = p.get("media_type") or "?"
        print(f"    {eng:4d} ({likes}L/{comments}C) | {date} | [{media:7s}] {snippet}...")

    # ── Content Patterns ──
    print(f"\n--- CONTENT PATTERNS ---")
    by_media = defaultdict(list)
    for p in posts:
        media = p.get("media_type") or "text"
        eng = (p.get("engagement_likes", 0) or 0) + (p.get("engagement_comments", 0) or 0) + (p.get("engagement_shares", 0) or 0)
        by_media[media].append(eng)

    print(f"  Engagement by media type:")
    for media, engs in sorted(by_media.items(), key=lambda x: -sum(x[1]) / len(x[1])):
        avg = sum(engs) / len(engs)
        print(f"    {media:10s}: {len(engs):3d} posts, avg {avg:.0f} engagement, total {sum(engs):,}")

    # Post length analysis
    lengths = [(len(p.get("post_content") or ""), (p.get("engagement_likes", 0) or 0) + (p.get("engagement_comments", 0) or 0) + (p.get("engagement_shares", 0) or 0)) for p in posts]
    short = [(l, e) for l, e in lengths if l < 500]
    medium = [(l, e) for l, e in lengths if 500 <= l < 1500]
    long = [(l, e) for l, e in lengths if l >= 1500]

    print(f"\n  Engagement by post length:")
    if short:
        print(f"    Short (<500 chars):   {len(short):3d} posts, avg {sum(e for _, e in short) / len(short):.0f} engagement")
    if medium:
        print(f"    Medium (500-1500):    {len(medium):3d} posts, avg {sum(e for _, e in medium) / len(medium):.0f} engagement")
    if long:
        print(f"    Long (1500+):         {len(long):3d} posts, avg {sum(e for _, e in long) / len(long):.0f} engagement")

    # Posting frequency
    dates = [p.get("post_date") for p in posts if p.get("post_date")]
    if len(dates) >= 2:
        dates_sorted = sorted(dates)
        first = datetime.fromisoformat(dates_sorted[0].replace("Z", "+00:00")) if isinstance(dates_sorted[0], str) else dates_sorted[0]
        last = datetime.fromisoformat(dates_sorted[-1].replace("Z", "+00:00")) if isinstance(dates_sorted[-1], str) else dates_sorted[-1]
        span_days = max((last - first).days, 1)
        freq = len(posts) / (span_days / 7)
        print(f"\n  Posting frequency: {freq:.1f} posts/week over {span_days} days")

    # ── Reactor Analysis ──
    if reactions:
        print(f"\n--- REACTOR ANALYSIS ({len(reactions)} reactions) ---")

        unique_reactors = len(set(r["reactor_linkedin_urn"] for r in reactions))
        print(f"  Unique reactors: {unique_reactors:,}")

        # Reaction types
        types = Counter(r.get("reaction_type", "?") for r in reactions)
        print(f"  Reaction types: {dict(types)}")

        # Top reactors
        reactor_counts = Counter()
        reactor_info = {}
        for r in reactions:
            urn = r["reactor_linkedin_urn"]
            reactor_counts[urn] += 1
            if urn not in reactor_info:
                reactor_info[urn] = {
                    "name": r["reactor_name"],
                    "headline": r.get("reactor_headline") or "",
                    "contact_id": r.get("contact_id"),
                }

        print(f"\n  Top 25 most engaged reactors:")
        for urn, count in reactor_counts.most_common(25):
            info = reactor_info[urn]
            in_db = f" [contact #{info['contact_id']}]" if info["contact_id"] else ""
            headline = (info["headline"] or "")[:45]
            print(f"    {count:3d}x | {info['name']:30s} | {headline}{in_db}")

        # ── Contacts Overlap ──
        matched = [r for r in reactions if r.get("contact_id")]
        matched_contacts = set(r["contact_id"] for r in matched)
        print(f"\n--- CONTACTS DB OVERLAP ---")
        print(f"  Reactions from known contacts: {len(matched)}/{len(reactions)} ({len(matched)/len(reactions)*100:.1f}%)")
        print(f"  Unique contacts engaging: {len(matched_contacts)}")

        if matched_contacts:
            # Get contact details
            contact_reaction_counts = Counter()
            for r in matched:
                contact_reaction_counts[r["contact_id"]] += 1

            # Fetch contact names
            contact_ids = list(matched_contacts)
            contact_names = {}
            for i in range(0, len(contact_ids), 50):
                batch = contact_ids[i:i+50]
                rows = sb.table("contacts").select("id, first_name, last_name, headline, ai_proximity_tier, ai_capacity_tier") \
                    .in_("id", batch).execute().data
                for row in rows:
                    contact_names[row["id"]] = row

            print(f"\n  Contacts engaging with this influencer (warm intro potential):")
            for cid, count in contact_reaction_counts.most_common(30):
                c = contact_names.get(cid, {})
                name = f"{c.get('first_name', '?')} {c.get('last_name', '')}".strip()
                prox = c.get("ai_proximity_tier") or "?"
                cap = c.get("ai_capacity_tier") or "?"
                print(f"    {count:2d}x | {name:30s} | prox={prox:8s} cap={cap}")

        # Engagement concentration
        top_10_pct = max(1, unique_reactors // 10)
        top_reactor_urns = [urn for urn, _ in reactor_counts.most_common(top_10_pct)]
        top_reaction_count = sum(reactor_counts[urn] for urn in top_reactor_urns)
        print(f"\n  Engagement concentration:")
        print(f"    Top 10% of reactors ({top_10_pct}) account for {top_reaction_count}/{len(reactions)} reactions ({top_reaction_count/len(reactions)*100:.1f}%)")

    print(f"\n{'='*70}")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Analyze influencer LinkedIn posts")
    parser.add_argument("influencer", help="LinkedIn URL or username")
    parser.add_argument("--months", type=int, default=6, help="Months of posts (default: 6)")
    parser.add_argument("--max-posts", type=int, default=100, help="Max posts to scrape (default: 100)")
    parser.add_argument("--skip-reactions", action="store_true", help="Skip reaction scraping")
    parser.add_argument("--report-only", action="store_true", help="Report from DB only, no scraping")
    parser.add_argument("--workers", type=int, default=50, help="GPT matching workers (default: 50)")
    args = parser.parse_args()

    influencer_url = normalize_url(args.influencer)
    username = extract_username(influencer_url)
    print(f"Influencer: {username} ({influencer_url})")

    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    if args.report_only:
        print_report(sb, influencer_url)
        return

    apify = ApifyClient(os.environ["APIFY_API_KEY"])
    openai_client = OpenAI(api_key=os.environ["OPENAI_APIKEY"])

    # Phase 1: Scrape posts
    posts, influencer_name = scrape_posts(apify, influencer_url, args.max_posts, args.months)

    if not posts:
        print("No posts found. Exiting.")
        return

    # Phase 2: Scrape reactions
    reactions = []
    if not args.skip_reactions:
        reactions = scrape_reactions(apify, posts)

    # Phase 3: Match + Save
    matcher = match_and_save(sb, openai_client, influencer_url, posts, reactions, args.workers)

    # Phase 4: Report
    print_report(sb, influencer_url, influencer_name)

    # Cost summary
    print(f"\nCOST SUMMARY:")
    post_cost = len(posts) * 0.002
    reaction_batches = (len(posts) + REACTIONS_BATCH_SIZE - 1) // REACTIONS_BATCH_SIZE if not args.skip_reactions else 0
    reaction_cost = reaction_batches * 0.01
    print(f"  Posts scrape: ~${post_cost:.2f} (Apify)")
    print(f"  Reactions scrape: ~${reaction_cost:.2f} (Apify, {reaction_batches} batches)")
    if matcher:
        matcher.print_cost()
    print(f"  Estimated total: ~${post_cost + reaction_cost:.2f} + GPT matching")


if __name__ == "__main__":
    main()
