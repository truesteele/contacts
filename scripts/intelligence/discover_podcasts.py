#!/usr/bin/env python3
"""
Podcast Discovery — Search, Deduplicate, and Save Podcast Targets

Searches Podcast Index and iTunes for podcasts matching Sally and Justin's
topics, deduplicates results using GPT-5 mini, filters out inactive shows,
and saves to podcast_targets.

Usage:
  python scripts/intelligence/discover_podcasts.py --speaker sally --test --limit 10
  python scripts/intelligence/discover_podcasts.py --speaker justin --limit 200
  python scripts/intelligence/discover_podcasts.py --speaker both
  python scripts/intelligence/discover_podcasts.py --speaker sally --search-terms "camping,outdoor family"
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")

# Allow imports from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.intelligence.podcast_api import PodcastIndexClient, search_itunes


# ── Search Terms ───────────────────────────────────────────────────────

SALLY_TERMS = [
    "camping families", "outdoor family", "parenting outdoors",
    "Black motherhood", "outdoor equity", "nature spirituality",
    "faith nature", "women outdoors", "family adventure",
    "camping with kids", "outdoor community", "nature belonging",
    "sacred space nature", "outdoor ministry",
]

JUSTIN_TERMS = [
    "social impact", "philanthropy", "nonprofit technology",
    "AI social good", "corporate responsibility", "tech for good",
    "founder story", "leaving big tech", "AI nonprofits",
    "grantmaking", "social enterprise", "outdoor equity",
    "purpose driven career",
]


# ── Clients ────────────────────────────────────────────────────────────

def get_supabase() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def get_openai() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_APIKEY"])


MODEL = "gpt-5-mini"

# 90 days ago threshold for activity filtering
ACTIVITY_CUTOFF = datetime.now(timezone.utc) - timedelta(days=90)
ACTIVITY_CUTOFF_EPOCH = int(ACTIVITY_CUTOFF.timestamp())


# ── Search ─────────────────────────────────────────────────────────────

def search_all(terms: list[str], limit_per_term: int, pi_client: PodcastIndexClient | None) -> list[dict]:
    """Search both Podcast Index and iTunes for all terms. Returns raw results."""
    all_results = []
    seen_titles_lower = set()  # quick pre-dedup by exact lowercase title

    for i, term in enumerate(terms):
        print(f"  [{i+1}/{len(terms)}] Searching: '{term}'")

        # Podcast Index
        if pi_client:
            try:
                pi_results = pi_client.search_by_term(term, max_results=limit_per_term)
                for p in pi_results:
                    key = p["title"].lower().strip()
                    if key not in seen_titles_lower:
                        seen_titles_lower.add(key)
                        p["_source"] = "podcast_index"
                        p["_search_term"] = term
                        all_results.append(p)
            except Exception as e:
                print(f"    Podcast Index error for '{term}': {e}")

        # iTunes
        try:
            it_results = search_itunes(term, limit=min(limit_per_term, 50))
            for p in it_results:
                key = p["title"].lower().strip()
                if key not in seen_titles_lower:
                    seen_titles_lower.add(key)
                    p["_source"] = "itunes"
                    p["_search_term"] = term
                    all_results.append(p)
        except Exception as e:
            print(f"    iTunes error for '{term}': {e}")

    print(f"\n  Raw results after exact-title dedup: {len(all_results)}")
    return all_results


# ── Language Filter ────────────────────────────────────────────────────

def filter_language(podcasts: list[dict]) -> list[dict]:
    """Keep only English-language podcasts."""
    kept = []
    for p in podcasts:
        lang = (p.get("language") or "en").lower()[:2]
        if lang in ("en", ""):  # empty = assume English
            kept.append(p)
    removed = len(podcasts) - len(kept)
    if removed:
        print(f"  Filtered {removed} non-English podcasts")
    return kept


# ── Activity Filter ────────────────────────────────────────────────────

def filter_inactive(podcasts: list[dict]) -> list[dict]:
    """Remove podcasts with no episode in 90 days (based on last_update_time)."""
    kept = []
    inactive = 0
    for p in podcasts:
        last_update = p.get("last_update_time", 0)
        # iTunes results have last_update_time=0 (unknown), keep them
        if last_update == 0 or last_update >= ACTIVITY_CUTOFF_EPOCH:
            kept.append(p)
        else:
            inactive += 1

    if inactive:
        print(f"  Filtered {inactive} inactive podcasts (no episode in 90 days)")
    return kept


# ── GPT Deduplication ──────────────────────────────────────────────────

def find_duplicate_pairs(podcasts: list[dict]) -> list[tuple[int, int]]:
    """Build candidate pairs for dedup by comparing normalized titles.

    We only send pairs to GPT that are plausibly the same podcast.
    Uses simple heuristics to reduce GPT calls:
    - Shared significant words (3+ chars) in title
    """
    pairs = []
    n = len(podcasts)

    def significant_words(title: str) -> set:
        return {w for w in title.lower().split() if len(w) >= 3}

    for i in range(n):
        words_i = significant_words(podcasts[i]["title"])
        if not words_i:
            continue
        for j in range(i + 1, n):
            words_j = significant_words(podcasts[j]["title"])
            # Need at least 2 shared significant words, or one is substring of other
            shared = words_i & words_j
            title_i = podcasts[i]["title"].lower().strip()
            title_j = podcasts[j]["title"].lower().strip()
            if len(shared) >= 2 or title_i in title_j or title_j in title_i:
                pairs.append((i, j))

    return pairs


def dedup_with_gpt(podcasts: list[dict], oai: OpenAI, workers: int = 20) -> list[dict]:
    """Deduplicate podcasts using GPT-5 mini to compare candidate pairs."""
    if len(podcasts) <= 1:
        return podcasts

    pairs = find_duplicate_pairs(podcasts)
    if not pairs:
        print(f"  No candidate duplicate pairs found")
        return podcasts

    print(f"  Found {len(pairs)} candidate pairs for GPT dedup")

    # Track which indices to remove (keep lower index, remove higher)
    remove_indices = set()

    def check_pair(i: int, j: int) -> tuple[int, int, bool]:
        a = podcasts[i]
        b = podcasts[j]
        prompt = (
            f"Are these the same podcast?\n"
            f"A: \"{a['title']}\" by \"{a.get('author', 'unknown')}\"\n"
            f"B: \"{b['title']}\" by \"{b.get('author', 'unknown')}\"\n\n"
            f"Respond in JSON: {{\"is_duplicate\": true/false, \"confidence\": 0.0-1.0}}"
        )
        try:
            resp = oai.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a podcast deduplication expert. Determine if two podcast listings refer to the same show."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)
            return (i, j, result.get("is_duplicate", False))
        except Exception as e:
            print(f"    GPT dedup error: {e}")
            return (i, j, False)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(check_pair, i, j): (i, j) for i, j in pairs}
        for future in as_completed(futures):
            i, j, is_dup = future.result()
            if is_dup:
                # Keep the one with more info (Podcast Index preferred over iTunes)
                if podcasts[i].get("_source") == "podcast_index":
                    remove_indices.add(j)
                else:
                    remove_indices.add(i)

    kept = [p for idx, p in enumerate(podcasts) if idx not in remove_indices]
    removed = len(podcasts) - len(kept)
    if removed:
        print(f"  GPT dedup removed {removed} duplicates")
    return kept


# ── Save to Database ───────────────────────────────────────────────────

def save_podcasts(podcasts: list[dict], sb: Client) -> int:
    """Upsert podcasts to podcast_targets. Returns count saved."""
    saved = 0
    for p in podcasts:
        row = {
            "title": p["title"],
            "author": p.get("author", ""),
            "description": p.get("description", ""),
            "categories": p.get("categories", []),
            "language": p.get("language", "en") or "en",
            "episode_count": p.get("episode_count", 0),
            "website_url": p.get("website_url", ""),
            "rss_url": p.get("rss_url", ""),
            "image_url": p.get("image_url", ""),
        }

        # Set last_episode_date from epoch timestamp
        last_update = p.get("last_update_time", 0)
        if last_update and last_update > 0:
            row["last_episode_date"] = datetime.fromtimestamp(last_update, tz=timezone.utc).isoformat()

        # Set activity status
        if last_update and last_update > 0:
            row["activity_status"] = "active" if last_update >= ACTIVITY_CUTOFF_EPOCH else "inactive"
        else:
            row["activity_status"] = "unknown"

        # Use podcast_index_id or itunes_id for upsert key
        pi_id = p.get("podcast_index_id")
        it_id = p.get("itunes_id")

        if pi_id:
            row["podcast_index_id"] = pi_id
            if it_id:
                row["itunes_id"] = it_id
            try:
                sb.table("podcast_targets").upsert(row, on_conflict="podcast_index_id").execute()
                saved += 1
            except Exception as e:
                print(f"    Save error ({p['title'][:40]}): {e}")
        elif it_id:
            # iTunes-only podcast: check if already exists by title+author
            row["itunes_id"] = it_id
            existing = sb.table("podcast_targets").select("id").eq(
                "title", p["title"]
            ).execute()
            if existing.data:
                # Update existing
                sb.table("podcast_targets").update(row).eq("id", existing.data[0]["id"]).execute()
            else:
                sb.table("podcast_targets").insert(row).execute()
            saved += 1
        else:
            # No ID, insert by title match
            existing = sb.table("podcast_targets").select("id").eq(
                "title", p["title"]
            ).execute()
            if not existing.data:
                try:
                    sb.table("podcast_targets").insert(row).execute()
                    saved += 1
                except Exception as e:
                    print(f"    Save error ({p['title'][:40]}): {e}")

    return saved


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Discover podcasts for speaker outreach")
    parser.add_argument("--speaker", required=True, choices=["sally", "justin", "both"],
                        help="Which speaker's topics to search for")
    parser.add_argument("--search-terms", type=str, default=None,
                        help="Comma-separated override search terms")
    parser.add_argument("--limit", type=int, default=200,
                        help="Max results per search term (default: 200)")
    parser.add_argument("--test", action="store_true",
                        help="Dry run: print results without saving")
    parser.add_argument("--workers", type=int, default=20,
                        help="Concurrent GPT workers for dedup (default: 20)")
    args = parser.parse_args()

    # Build search terms
    if args.search_terms:
        terms = [t.strip() for t in args.search_terms.split(",") if t.strip()]
    elif args.speaker == "sally":
        terms = SALLY_TERMS
    elif args.speaker == "justin":
        terms = JUSTIN_TERMS
    else:  # both
        terms = list(set(SALLY_TERMS + JUSTIN_TERMS))

    print(f"=== Podcast Discovery ===")
    print(f"Speaker: {args.speaker}")
    print(f"Search terms: {len(terms)}")
    print(f"Limit per term: {args.limit}")
    print(f"Mode: {'TEST (dry run)' if args.test else 'LIVE (will save)'}")
    print()

    # Init clients
    oai = get_openai()

    pi_key = os.environ.get("PODCAST_INDEX_API_KEY")
    pi_secret = os.environ.get("PODCAST_INDEX_API_SECRET")
    pi_client = PodcastIndexClient(pi_key, pi_secret) if pi_key and pi_secret else None
    if not pi_client:
        print("  WARNING: PODCAST_INDEX_API_KEY/SECRET not set, using iTunes only\n")

    # 1. Search
    print("Step 1: Searching APIs...")
    results = search_all(terms, args.limit, pi_client)
    if not results:
        print("No results found. Exiting.")
        return

    # 2. Filter language
    print("\nStep 2: Filtering non-English...")
    results = filter_language(results)

    # 3. Filter inactive
    print("\nStep 3: Filtering inactive shows...")
    results = filter_inactive(results)

    # 4. GPT deduplication
    print("\nStep 4: GPT-powered deduplication...")
    results = dedup_with_gpt(results, oai, workers=args.workers)

    # 5. Summary
    print(f"\n{'='*60}")
    print(f"Final results: {len(results)} podcasts")
    print(f"{'='*60}")

    if args.test:
        # Print top results
        for i, p in enumerate(results[:30]):
            src = p.get("_source", "?")
            eps = p.get("episode_count", 0)
            term = p.get("_search_term", "?")
            print(f"  {i+1}. [{src}] {p['title']}")
            print(f"     by {p.get('author', '?')} | {eps} eps | term: '{term}'")

        if len(results) > 30:
            print(f"  ... and {len(results) - 30} more")
        print(f"\nDRY RUN -- no database changes made")
    else:
        # Save
        print("\nStep 5: Saving to database...")
        sb = get_supabase()
        saved = save_podcasts(results, sb)
        print(f"\nSaved {saved}/{len(results)} podcasts to podcast_targets")

    print("\nDone.")


if __name__ == "__main__":
    main()
