#!/usr/bin/env python3
"""
Podcast Discovery — Search, Deduplicate, and Save Podcast Targets

Searches Podcast Index and iTunes for podcasts matching speaker topics,
deduplicates results using GPT-5.4 mini, filters out inactive shows,
and saves to podcast_targets.

Discovery methods:
  keyword          — search hardcoded terms (default)
  expanded         — keyword + AI-generated expanded terms from speaker profile
  similar-speaker  — find podcasts via contacts with similar interests (pgvector)
  all              — all discovery methods

Usage:
  python scripts/intelligence/discover_podcasts.py --speaker sally --test --limit 10
  python scripts/intelligence/discover_podcasts.py --speaker justin --limit 200
  python scripts/intelligence/discover_podcasts.py --speaker both
  python scripts/intelligence/discover_podcasts.py --speaker sally --search-terms "camping,outdoor family"
  python scripts/intelligence/discover_podcasts.py --speaker sally --method expanded --limit 100
  python scripts/intelligence/discover_podcasts.py --speaker sally --method similar-speaker --test --limit 10
  python scripts/intelligence/discover_podcasts.py --speaker sally --method all
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
import psycopg2

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


MODEL = "gpt-5.4-mini"

# 90 days ago threshold for activity filtering
ACTIVITY_CUTOFF = datetime.now(timezone.utc) - timedelta(days=90)
ACTIVITY_CUTOFF_EPOCH = int(ACTIVITY_CUTOFF.timestamp())


# ── Search ─────────────────────────────────────────────────────────────

def search_all(terms: list[str], limit_per_term: int, pi_client: PodcastIndexClient | None,
               discovery_method: str = "keyword_search") -> list[dict]:
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
                        p["_discovery_method"] = discovery_method
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
                    p["_discovery_method"] = discovery_method
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
    """Upsert podcasts to podcast_targets. Returns count saved.

    Handles discovery_methods: appends new methods to existing arrays
    without overwriting (so a podcast found by multiple methods accumulates tags).
    """
    saved = 0
    for p in podcasts:
        discovery_method = p.get("_discovery_method", "keyword_search")

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

        def _merge_discovery_methods(existing_row: dict | None) -> list[str]:
            """Merge new discovery method into existing methods array."""
            existing_methods = []
            if existing_row:
                existing_methods = existing_row.get("discovery_methods") or []
            if discovery_method not in existing_methods:
                existing_methods.append(discovery_method)
            return existing_methods

        if pi_id:
            row["podcast_index_id"] = pi_id
            if it_id:
                row["itunes_id"] = it_id
            try:
                # Check if exists to merge discovery_methods
                existing = sb.table("podcast_targets").select("id, discovery_methods").eq(
                    "podcast_index_id", pi_id
                ).execute()
                row["discovery_methods"] = _merge_discovery_methods(
                    existing.data[0] if existing.data else None
                )
                sb.table("podcast_targets").upsert(row, on_conflict="podcast_index_id").execute()
                saved += 1
            except Exception as e:
                print(f"    Save error ({p['title'][:40]}): {e}")
        elif it_id:
            # iTunes-only podcast: check if already exists by title
            row["itunes_id"] = it_id
            existing = sb.table("podcast_targets").select("id, discovery_methods").eq(
                "title", p["title"]
            ).execute()
            if existing.data:
                row["discovery_methods"] = _merge_discovery_methods(existing.data[0])
                sb.table("podcast_targets").update(row).eq("id", existing.data[0]["id"]).execute()
            else:
                row["discovery_methods"] = [discovery_method]
                sb.table("podcast_targets").insert(row).execute()
            saved += 1
        else:
            # No ID, insert by title match
            existing = sb.table("podcast_targets").select("id, discovery_methods").eq(
                "title", p["title"]
            ).execute()
            if existing.data:
                # Exists — update discovery_methods
                row["discovery_methods"] = _merge_discovery_methods(existing.data[0])
                sb.table("podcast_targets").update(row).eq("id", existing.data[0]["id"]).execute()
                saved += 1
            else:
                row["discovery_methods"] = [discovery_method]
                try:
                    sb.table("podcast_targets").insert(row).execute()
                    saved += 1
                except Exception as e:
                    print(f"    Save error ({p['title'][:40]}): {e}")

    return saved


# ── Speaker Profile Loading ───────────────────────────────────────────

def load_speaker(sb: Client, slug: str) -> dict:
    """Load a speaker profile by slug from speaker_profiles table."""
    result = sb.table("speaker_profiles").select("*").eq("slug", slug).execute()
    if not result.data:
        print(f"ERROR: No speaker profile found for slug '{slug}'")
        sys.exit(1)
    speaker = result.data[0]
    # Parse topic_pillars if stored as JSON string
    if isinstance(speaker.get("topic_pillars"), str):
        speaker["topic_pillars"] = json.loads(speaker["topic_pillars"])
    return speaker


# ── Expanded Keyword Generation ──────────────────────────────────────

def generate_expanded_terms(speaker: dict, oai: OpenAI, existing_terms: list[str]) -> list[str]:
    """Use GPT-5.4 mini to generate additional search terms from speaker's topic pillars."""
    pillars = speaker.get("topic_pillars") or []
    pillars_text = "\n".join(
        f"- {p['name']}: {p['description']}"
        for p in pillars
    )

    prompt = f"""Generate 25 additional podcast search terms for this speaker.

Speaker: {speaker['name']}
Headline: {speaker['headline']}
Topic Pillars:
{pillars_text}

Already searching for: {', '.join(existing_terms)}

Generate terms that:
- Cover adjacent topics a podcast booking agent would search
- Include niche audience-specific phrases
- Include common podcast category names that match
- Avoid duplicating the existing terms

Return a JSON object with key "terms" containing an array of strings."""

    try:
        resp = oai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a podcast booking expert generating search terms to find relevant podcasts for a speaker."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        result = json.loads(resp.choices[0].message.content)
        terms = result.get("terms", [])
        # Filter out any that duplicate existing terms (case-insensitive)
        existing_lower = {t.lower() for t in existing_terms}
        new_terms = [t for t in terms if t.lower() not in existing_lower]
        return new_terms
    except Exception as e:
        print(f"  ERROR generating expanded terms: {e}")
        return []


# ── Similar-Speaker Discovery ──────────────────────────────────────────

def discover_by_similar_speakers(
    speaker_slug: str,
    pi_client: PodcastIndexClient | None,
    limit_per_term: int,
    similar_speaker_limit: int = 50,
    test: bool = False,
) -> list[dict]:
    """Find podcasts by searching for similar contacts' podcast appearances.

    Pipeline:
    1. Load speaker's profile_embedding from speaker_profiles
    2. Query contacts for top N most similar by interests_embedding (pgvector)
    3. Search Podcast Index for each similar contact by name
    4. Filter: only keep podcasts where the contact's name appears in title/description
    5. Tag results with discovery_method = 'similar_speaker'
    """
    if not pi_client:
        print("  WARNING: Podcast Index client required for similar-speaker discovery (need name search)")
        print("  Set PODCAST_INDEX_API_KEY and PODCAST_INDEX_API_SECRET in .env")
        return []

    # Connect via psycopg2 for vector queries
    conn = psycopg2.connect(
        host="db.ypqsrejrsocebnldicke.supabase.co",
        port=5432,
        dbname="postgres",
        user="postgres",
        password=os.environ["SUPABASE_DB_PASSWORD"],
    )

    try:
        with conn.cursor() as cur:
            # 1. Get speaker's profile_embedding
            cur.execute(
                "SELECT id, name, profile_embedding FROM speaker_profiles WHERE slug = %s",
                (speaker_slug,),
            )
            row = cur.fetchone()
            if not row or row[2] is None:
                print(f"  WARNING: No profile embedding for speaker '{speaker_slug}'. Run embed_podcasts.py first.")
                return []

            speaker_name = row[1]
            speaker_embedding_str = row[2]  # pgvector returns as string

            # 2. Query contacts for most similar by interests_embedding
            cur.execute(
                """
                SELECT id, first_name, last_name, headline, company,
                       1 - (interests_embedding <=> %s::vector) as similarity
                FROM contacts
                WHERE interests_embedding IS NOT NULL
                ORDER BY interests_embedding <=> %s::vector
                LIMIT %s
                """,
                (speaker_embedding_str, speaker_embedding_str, similar_speaker_limit),
            )
            similar_contacts = cur.fetchall()
    finally:
        conn.close()

    # 3. Filter by similarity threshold
    contacts_to_search = [
        {"id": c[0], "first_name": c[1], "last_name": c[2],
         "headline": c[3], "company": c[4], "similarity": float(c[5])}
        for c in similar_contacts if float(c[5]) > 0.5
    ]

    print(f"  Speaker: {speaker_name}")
    print(f"  Found {len(contacts_to_search)} similar contacts (similarity > 0.5) out of top {similar_speaker_limit}")
    if contacts_to_search:
        print(f"  Top 5 similar:")
        for c in contacts_to_search[:5]:
            print(f"    - {c['first_name']} {c['last_name']} ({c.get('headline', '')[:50]}) — sim: {c['similarity']:.3f}")

    # 4. Search Podcast Index for each similar contact by name
    all_results = []
    seen_titles = set()
    contacts_with_hits = 0

    for i, contact in enumerate(contacts_to_search):
        name = f"{contact['first_name']} {contact['last_name']}"
        name_lower = name.lower()
        first_lower = contact["first_name"].lower()
        last_lower = contact["last_name"].lower()

        if test and i >= 10:
            print(f"  (test mode: stopping after 10 contacts)")
            break

        try:
            pi_results = pi_client.search_by_term(name, max_results=limit_per_term)
        except Exception as e:
            print(f"    PI search error for '{name}': {e}")
            continue

        # Filter: only keep podcasts where the contact appears to be a guest
        contact_hits = 0
        for p in pi_results:
            title_lower = p["title"].lower()
            desc_lower = (p.get("description") or "").lower()

            # Check if the person's name appears in title or description
            name_in_content = (
                name_lower in title_lower
                or name_lower in desc_lower
                or (first_lower in desc_lower and last_lower in desc_lower)
            )

            if name_in_content:
                key = p["title"].lower().strip()
                if key not in seen_titles:
                    seen_titles.add(key)
                    p["_source"] = "podcast_index"
                    p["_search_term"] = name
                    p["_discovery_method"] = "similar_speaker"
                    all_results.append(p)
                    contact_hits += 1
                    print(f"    Found '{p['title'][:60]}' via {name} (sim: {contact['similarity']:.3f})")

        if contact_hits > 0:
            contacts_with_hits += 1

        # Small delay to avoid hammering PI API
        time.sleep(0.2)

    print(f"\n  Similar-speaker results: {len(all_results)} podcasts from {contacts_with_hits} contacts")
    return all_results


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
    parser.add_argument("--method", type=str, default="keyword",
                        choices=["keyword", "expanded", "similar-speaker", "all"],
                        help="Discovery method: keyword (default), expanded (keyword + AI terms), similar-speaker, all")
    parser.add_argument("--similar-speaker-limit", type=int, default=50,
                        help="How many similar contacts to check for similar-speaker discovery (default: 50)")
    args = parser.parse_args()

    # Init clients
    oai = get_openai()
    sb = get_supabase()

    pi_key = os.environ.get("PODCAST_INDEX_API_KEY")
    pi_secret = os.environ.get("PODCAST_INDEX_API_SECRET")
    pi_client = PodcastIndexClient(pi_key, pi_secret) if pi_key and pi_secret else None
    if not pi_client:
        print("  WARNING: PODCAST_INDEX_API_KEY/SECRET not set, using iTunes only\n")

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
    print(f"Method: {args.method}")
    print(f"Base search terms: {len(terms)}")
    print(f"Limit per term: {args.limit}")
    print(f"Mode: {'TEST (dry run)' if args.test else 'LIVE (will save)'}")
    print()

    all_results = []
    step = 1

    # ── Keyword search (runs for keyword/expanded/all) ──
    if args.method in ("keyword", "expanded", "all"):
        print(f"Step {step}: Keyword search...")
        keyword_results = search_all(terms, args.limit, pi_client, discovery_method="keyword_search")
        all_results.extend(keyword_results)
        step += 1

    # ── Expanded keyword search ──
    if args.method in ("expanded", "all"):
        print(f"\nStep {step}: Generating expanded search terms...")
        step += 1
        # Load speaker profile for expanded terms
        speakers_to_expand = []
        if args.speaker in ("sally", "both"):
            speakers_to_expand.append("sally")
        if args.speaker in ("justin", "both"):
            speakers_to_expand.append("justin")

        for slug in speakers_to_expand:
            speaker = load_speaker(sb, slug)
            print(f"  Speaker: {speaker['name']}")
            expanded = generate_expanded_terms(speaker, oai, terms)
            print(f"  Generated {len(expanded)} expanded terms")
            if expanded:
                for t in expanded[:10]:
                    print(f"    - {t}")
                if len(expanded) > 10:
                    print(f"    ... and {len(expanded) - 10} more")

                print(f"\n  Searching expanded terms...")
                # Track seen titles from keyword results to avoid redundant searching
                seen_titles = {r["title"].lower().strip() for r in all_results}
                expanded_results = search_all(expanded, args.limit, pi_client,
                                              discovery_method="expanded_keywords")
                # Filter out titles already found in keyword search
                new_expanded = [r for r in expanded_results
                                if r["title"].lower().strip() not in seen_titles]
                print(f"  New podcasts from expanded terms: {len(new_expanded)}")
                all_results.extend(new_expanded)

    # ── Similar-speaker discovery ──
    if args.method in ("similar-speaker", "all"):
        print(f"\nStep {step}: Similar-speaker discovery...")
        step += 1
        speakers_to_search = []
        if args.speaker in ("sally", "both"):
            speakers_to_search.append("sally")
        if args.speaker in ("justin", "both"):
            speakers_to_search.append("justin")

        seen_titles = {r["title"].lower().strip() for r in all_results}

        for slug in speakers_to_search:
            similar_results = discover_by_similar_speakers(
                speaker_slug=slug,
                pi_client=pi_client,
                limit_per_term=min(args.limit, 20),  # cap at 20 per contact name search
                similar_speaker_limit=args.similar_speaker_limit,
                test=args.test,
            )
            # Filter out titles already found by other methods
            new_similar = [r for r in similar_results
                           if r["title"].lower().strip() not in seen_titles]
            for r in new_similar:
                seen_titles.add(r["title"].lower().strip())
            print(f"  New podcasts from similar speakers: {len(new_similar)}")
            all_results.extend(new_similar)

    if not all_results:
        print("No results found. Exiting.")
        return

    # Filter and dedup
    print(f"\nTotal raw results: {len(all_results)}")

    print(f"\nStep {step}: Filtering non-English...")
    all_results = filter_language(all_results)
    step += 1

    print(f"\nStep {step}: Filtering inactive shows...")
    all_results = filter_inactive(all_results)
    step += 1

    print(f"\nStep {step}: GPT-powered deduplication...")
    all_results = dedup_with_gpt(all_results, oai, workers=args.workers)
    step += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Final results: {len(all_results)} podcasts")

    # Count by discovery method
    method_counts = {}
    for r in all_results:
        m = r.get("_discovery_method", "keyword_search")
        method_counts[m] = method_counts.get(m, 0) + 1
    for m, c in sorted(method_counts.items()):
        print(f"  {m}: {c}")
    print(f"{'='*60}")

    if args.test:
        # Print top results
        for i, p in enumerate(all_results[:30]):
            src = p.get("_source", "?")
            eps = p.get("episode_count", 0)
            term = p.get("_search_term", "?")
            method = p.get("_discovery_method", "?")
            print(f"  {i+1}. [{src}|{method}] {p['title']}")
            print(f"     by {p.get('author', '?')} | {eps} eps | term: '{term}'")

        if len(all_results) > 30:
            print(f"  ... and {len(all_results) - 30} more")
        print(f"\nDRY RUN -- no database changes made")
    else:
        # Save
        print(f"\nStep {step}: Saving to database...")
        saved = save_podcasts(all_results, sb)
        print(f"\nSaved {saved}/{len(all_results)} podcasts to podcast_targets")

    print("\nDone.")


if __name__ == "__main__":
    main()
