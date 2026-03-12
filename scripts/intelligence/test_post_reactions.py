"""
Test scraping LinkedIn post reactions using Apify.
Starts with 2-3 posts to verify data quality before scaling up.
"""
import csv
import json
import os
import sys
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")

api_key = os.getenv("APIFY_API_KEY")
if not api_key:
    raise RuntimeError("APIFY_API_KEY not found in .env")

client = ApifyClient(api_key)

SHARES_CSV = "/Users/Justin/Code/TrueSteele/contacts/docs/LinkedIn/Justin Posts/Shares.csv"


def load_posts(since_date=None):
    """Load posts from LinkedIn Shares.csv export."""
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
            if since_date and dt < since_date:
                continue
            decoded_link = urllib.parse.unquote(link)
            posts.append({
                "date": dt,
                "url": decoded_link,
                "commentary": commentary[:120],
            })
    return sorted(posts, key=lambda x: x["date"], reverse=True)


def test_harvestapi_with_reactions(max_posts=3):
    """
    Test harvestapi/linkedin-profile-posts with scrapeReactions enabled.
    This scrapes posts from the profile and optionally includes who reacted.
    """
    print("=" * 80)
    print("TEST: harvestapi/linkedin-profile-posts with scrapeReactions=true")
    print(f"Limiting to {max_posts} posts to control cost")
    print("=" * 80)

    run_input = {
        "profileUrls": ["https://www.linkedin.com/in/justinrichardsteele/"],
        "maxPosts": max_posts,
        "scrapeReactions": True,
        "maxReactions": 50,  # Cap at 50 per post for testing
    }

    print(f"\nInput: {json.dumps(run_input, indent=2)}")
    print("\nStarting actor run...")

    run = client.actor("harvestapi/linkedin-profile-posts").call(run_input=run_input)
    print(f"Run status: {run.get('status')}")
    print(f"Dataset ID: {run.get('defaultDatasetId')}")

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"\nTotal items returned: {len(items)}")

    # Separate posts from reactions
    posts = [i for i in items if i.get("type") != "reaction"]
    reactions = [i for i in items if i.get("type") == "reaction"]

    print(f"  Posts: {len(posts)}")
    print(f"  Reactions: {len(reactions)}")

    # Show post summaries
    print("\n--- POSTS ---")
    for p in posts:
        text = (p.get("text") or "")[:80]
        likes = p.get("totalReactionCount") or p.get("numLikes") or "?"
        print(f"  [{p.get('postedAt', '?')}] {text}... ({likes} reactions)")

        # Check if reactions are nested in the post
        nested_reactions = p.get("reactions") or p.get("socialContent", {}).get("reactions") or []
        if nested_reactions:
            print(f"    -> {len(nested_reactions)} nested reactions found")
            for r in nested_reactions[:3]:
                print(f"       {r}")

    # Show reaction details
    if reactions:
        print("\n--- REACTION ITEMS (first 10) ---")
        for r in reactions[:10]:
            actor_info = r.get("actor") or {}
            name = actor_info.get("name") or r.get("name") or r.get("fullName") or "?"
            headline = actor_info.get("headline") or r.get("headline") or ""
            rtype = r.get("reactionType") or r.get("type") or "?"
            profile = actor_info.get("url") or r.get("profileUrl") or r.get("linkedinUrl") or "?"
            print(f"  {rtype:15s} | {name:30s} | {headline[:40]:40s} | {profile}")

    # Dump full JSON for inspection
    output_path = "/Users/Justin/Code/TrueSteele/contacts/scripts/intelligence/test_reactions_output.json"
    with open(output_path, "w") as f:
        json.dump(items, f, indent=2, default=str)
    print(f"\nFull output saved to: {output_path}")

    return items


def test_dedicated_reactions_scraper(post_urls):
    """
    Test apimaestro/linkedin-post-reactions on specific post URLs.
    """
    print("\n" + "=" * 80)
    print("TEST: apimaestro/linkedin-post-reactions")
    print(f"Testing with {len(post_urls)} post URL(s)")
    print("=" * 80)

    run_input = {
        "post_urls": post_urls,
        "limit": 50,  # Cap for testing
    }

    print(f"\nInput: {json.dumps(run_input, indent=2)}")
    print("\nStarting actor run...")

    run = client.actor("apimaestro/linkedin-post-reactions").call(run_input=run_input)
    print(f"Run status: {run.get('status')}")
    print(f"Dataset ID: {run.get('defaultDatasetId')}")

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"\nTotal reaction items: {len(items)}")

    if items:
        print("\n--- REACTIONS (first 15) ---")
        for r in items[:15]:
            name = r.get("name") or r.get("fullName") or r.get("actor", {}).get("name") or "?"
            headline = r.get("headline") or r.get("actor", {}).get("headline") or ""
            rtype = r.get("reactionType") or r.get("type") or "?"
            profile = r.get("profileUrl") or r.get("linkedinUrl") or r.get("actor", {}).get("url") or "?"
            print(f"  {rtype:15s} | {name:30s} | {headline[:40]:40s} | {profile}")

        # Show all keys on first item
        print(f"\n--- FIRST ITEM KEYS ---")
        print(json.dumps(items[0], indent=2, default=str))

    output_path = "/Users/Justin/Code/TrueSteele/contacts/scripts/intelligence/test_reactions_dedicated_output.json"
    with open(output_path, "w") as f:
        json.dump(items, f, indent=2, default=str)
    print(f"\nFull output saved to: {output_path}")

    return items


if __name__ == "__main__":
    # Load posts since Nov 2024
    cutoff = datetime(2024, 11, 1)
    posts = load_posts(since_date=cutoff)
    print(f"Found {len(posts)} posts since Nov 2024\n")

    # Pick test posts: most recent + one from mid-range
    test_posts = [posts[0], posts[len(posts) // 2]]
    print("Test posts:")
    for p in test_posts:
        print(f"  {p['date'].date()} | {p['commentary'][:60]}...")
        print(f"  URL: {p['url']}")
    print()

    mode = sys.argv[1] if len(sys.argv) > 1 else "both"

    if mode in ("harvestapi", "both"):
        test_harvestapi_with_reactions(max_posts=3)

    if mode in ("dedicated", "both"):
        test_urls = [p["url"] for p in test_posts]
        test_dedicated_reactions_scraper(test_urls)

    print("\n✓ Tests complete. Review the JSON output files to compare approaches.")
