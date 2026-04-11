#!/usr/bin/env python3
"""
Podcast Fit Scoring — GPT-5.4 mini structured output

Scores how well each discovered podcast fits a speaker's topic pillars.
Saves fit scores to podcast_pitches (fit fields only; pitch copy comes later).

Usage:
  python scripts/intelligence/score_podcast_fit.py --speaker sally --limit 5 --test
  python scripts/intelligence/score_podcast_fit.py --speaker justin --limit 50 --workers 50
  python scripts/intelligence/score_podcast_fit.py --speaker sally --min-episodes 3
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from supabase import create_client, Client

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")


# ── Constants ──────────────────────────────────────────────────────────

MODEL = "gpt-5.4-mini"

SYSTEM_PROMPT = """You are a podcast booking expert evaluating whether a podcast is a good
fit for a speaker. Score the fit based on topic alignment, audience
relevance, and how naturally the speaker's expertise connects to the
podcast's content. Consider recent episodes to identify specific
conversation angles.

Score 0.0-1.0 where:
- 0.8-1.0 = strong (clear topic overlap, audience match)
- 0.5-0.79 = moderate (some overlap, could work with right angle)
- 0.0-0.49 = weak (poor fit, forced connection)"""

FIT_SCORE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "podcast_fit_score",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "fit_tier": {"type": "string", "enum": ["strong", "moderate", "weak"]},
                "fit_score": {"type": "number"},
                "fit_rationale": {"type": "string"},
                "matching_pillars": {"type": "array", "items": {"type": "string"}},
                "episode_hooks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "episode_title": {"type": "string"},
                            "angle": {"type": "string"}
                        },
                        "required": ["episode_title", "angle"],
                        "additionalProperties": False
                    }
                },
                "suggested_episode_ideas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["title", "description"],
                        "additionalProperties": False
                    }
                }
            },
            "required": [
                "fit_tier", "fit_score", "fit_rationale",
                "matching_pillars", "episode_hooks", "suggested_episode_ideas"
            ],
            "additionalProperties": False
        }
    }
}


# ── Clients ────────────────────────────────────────────────────────────

def get_supabase() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def get_openai() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_APIKEY"])


# ── Data Loading ───────────────────────────────────────────────────────

def load_speaker(sb: Client, slug: str) -> dict:
    """Load a speaker profile by slug."""
    result = sb.table("speaker_profiles").select("*").eq("slug", slug).execute()
    if not result.data:
        print(f"ERROR: No speaker profile found for slug '{slug}'")
        sys.exit(1)
    return result.data[0]


def load_unscored_podcasts(sb: Client, speaker_id: int, limit: int, min_episodes: int) -> list[dict]:
    """Load podcasts that haven't been scored for this speaker yet.

    Gets IDs already scored, then uses server-side .not_.in_() filter
    so pagination works correctly regardless of how many are already scored.
    """
    # Get IDs already scored for this speaker
    scored = sb.table("podcast_pitches") \
        .select("podcast_target_id") \
        .eq("speaker_profile_id", speaker_id) \
        .execute()
    scored_ids = [r["podcast_target_id"] for r in scored.data]

    # Get enriched podcasts not yet scored — server-side exclusion
    query = sb.table("podcast_targets") \
        .select("*") \
        .not_.is_("enriched_at", "null") \
        .order("id") \
        .limit(limit)

    if scored_ids:
        query = query.not_.in_("id", scored_ids)

    result = query.execute()
    return result.data


def load_episodes(sb: Client, podcast_id: int) -> list[dict]:
    """Load recent episodes for a podcast."""
    result = sb.table("podcast_episodes") \
        .select("title, description, published_at, duration_seconds") \
        .eq("podcast_target_id", podcast_id) \
        .order("published_at", desc=True) \
        .limit(5) \
        .execute()
    return result.data


# ── Prompt Building ────────────────────────────────────────────────────

def build_speaker_context(speaker: dict) -> str:
    """Build speaker context string from profile data."""
    parts = [
        f"SPEAKER: {speaker['name']}",
        f"Bio: {speaker['bio']}",
        f"Headline: {speaker['headline']}",
        "",
        "TOPIC PILLARS:",
    ]

    pillars = speaker.get("topic_pillars") or []
    if isinstance(pillars, str):
        pillars = json.loads(pillars)

    for p in pillars:
        parts.append(f"- {p['name']}: {p['description']}")
        if p.get("talking_points"):
            for tp in p["talking_points"]:
                parts.append(f"  * {tp}")

    return "\n".join(parts)


def build_podcast_context(podcast: dict, episodes: list[dict]) -> str:
    """Build podcast context string including recent episodes."""
    parts = [
        f"PODCAST: {podcast['title']}",
        f"Author/Host: {podcast.get('author') or 'Unknown'}",
        f"Description: {podcast.get('description') or 'No description'}",
    ]

    categories = podcast.get("categories")
    if categories:
        if isinstance(categories, str):
            categories = json.loads(categories)
        if isinstance(categories, list):
            parts.append(f"Categories: {', '.join(categories)}")

    parts.append(f"Activity: {podcast.get('activity_status', 'unknown')}")

    if episodes:
        parts.append("")
        parts.append(f"RECENT EPISODES ({len(episodes)}):")
        for ep in episodes:
            title = ep.get("title", "Untitled")
            desc = ep.get("description", "")
            # Truncate long descriptions
            if desc and len(desc) > 300:
                desc = desc[:300] + "..."
            date = ep.get("published_at", "")
            if date:
                date = date[:10]  # Just the date portion
            duration = ep.get("duration_seconds")
            dur_str = f" ({duration // 60}min)" if duration else ""
            parts.append(f"- [{date}]{dur_str} {title}")
            if desc:
                parts.append(f"  {desc}")

    return "\n".join(parts)


# ── Scoring ────────────────────────────────────────────────────────────

def score_podcast(oai: OpenAI, speaker_context: str, podcast: dict, episodes: list[dict]) -> dict | None:
    """Score a single podcast's fit with GPT-5.4 mini structured output."""
    podcast_context = build_podcast_context(podcast, episodes)

    user_message = (
        f"{speaker_context}\n\n---\n\n{podcast_context}\n\n"
        "Score how well this podcast fits this speaker. "
        "Identify which topic pillars match, suggest angles from recent episodes, "
        "and propose 2-3 episode topic ideas."
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = oai.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format=FIT_SCORE_SCHEMA,
            )
            content = resp.choices[0].message.content
            return json.loads(content)
        except RateLimitError:
            wait = 2 ** (attempt + 1)
            print(f"    Rate limited, waiting {wait}s...")
            time.sleep(wait)
        except APIError as e:
            print(f"    API error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None
        except (json.JSONDecodeError, KeyError) as e:
            print(f"    Parse error: {e}")
            return None
        except Exception as e:
            print(f"    Unexpected error: {e}")
            return None

    return None


# ── Save ───────────────────────────────────────────────────────────────

def save_score(sb: Client, podcast_id: int, speaker_id: int, score: dict) -> bool:
    """Save fit score to podcast_pitches table."""
    row = {
        "podcast_target_id": podcast_id,
        "speaker_profile_id": speaker_id,
        "fit_tier": score["fit_tier"],
        "fit_score": score["fit_score"],
        "fit_rationale": score["fit_rationale"],
        "topic_match": score.get("matching_pillars", []),
        "episode_hooks": score.get("episode_hooks", []),
        "suggested_topics": score.get("suggested_episode_ideas", []),
        "model_used": MODEL,
        "pitch_status": "unscored",  # fit scored, no pitch yet
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        sb.table("podcast_pitches").insert(row).execute()
        return True
    except Exception as e:
        print(f"    DB error saving score for podcast {podcast_id}: {e}")
        return False


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Score podcast fit for speakers using GPT-5.4 mini"
    )
    parser.add_argument("--speaker", required=True, choices=["sally", "justin"],
                        help="Speaker slug to score for")
    parser.add_argument("--limit", type=int, default=50,
                        help="Max podcasts to score (default: 50)")
    parser.add_argument("--workers", type=int, default=50,
                        help="Concurrent GPT workers (default: 50)")
    parser.add_argument("--min-episodes", type=int, default=0,
                        help="Skip podcasts with fewer episodes (default: 0)")
    parser.add_argument("--test", action="store_true",
                        help="Dry run: print scores without saving")
    args = parser.parse_args()

    # Init clients
    sb = get_supabase()
    oai = get_openai()
    print(f"Connected to Supabase and OpenAI")

    # Load speaker
    speaker = load_speaker(sb, args.speaker)
    speaker_context = build_speaker_context(speaker)
    print(f"Speaker: {speaker['name']} (id={speaker['id']})")
    print(f"Topic pillars: {len(speaker.get('topic_pillars') or [])}")

    # Load unscored podcasts
    podcasts = load_unscored_podcasts(sb, speaker["id"], args.limit, args.min_episodes)
    print(f"Podcasts to score: {len(podcasts)}")

    if not podcasts:
        print("No unscored podcasts found. Done.")
        return

    # Load episodes for each podcast and filter by min-episodes
    podcast_episodes = {}
    filtered = []
    for p in podcasts:
        eps = load_episodes(sb, p["id"])
        if len(eps) < args.min_episodes:
            print(f"  Skipping '{p['title']}' — only {len(eps)} episodes (min: {args.min_episodes})")
            continue
        podcast_episodes[p["id"]] = eps
        filtered.append(p)

    podcasts = filtered
    print(f"After min-episodes filter: {len(podcasts)}")

    if not podcasts:
        print("No podcasts pass the min-episodes filter. Done.")
        return

    # Score podcasts concurrently
    results = []
    stats = {"scored": 0, "strong": 0, "moderate": 0, "weak": 0, "errors": 0, "saved": 0}

    def score_one(podcast: dict) -> tuple[dict, dict | None]:
        eps = podcast_episodes.get(podcast["id"], [])
        score = score_podcast(oai, speaker_context, podcast, eps)
        return (podcast, score)

    print(f"\nScoring {len(podcasts)} podcasts with {args.workers} workers...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(score_one, p): p for p in podcasts}
        for future in as_completed(futures):
            podcast, score = future.result()
            title = podcast["title"][:50]

            if score is None:
                stats["errors"] += 1
                print(f"  ERROR: '{title}'")
                continue

            stats["scored"] += 1
            tier = score["fit_tier"]
            stats[tier] += 1

            pillars = ", ".join(score.get("matching_pillars", [])[:3])
            print(f"  {tier.upper():8s} ({score['fit_score']:.2f}) '{title}' — {pillars}")

            if args.test:
                # Print details in test mode
                print(f"           Rationale: {score['fit_rationale'][:100]}")
                for hook in score.get("episode_hooks", [])[:2]:
                    print(f"           Hook: {hook['episode_title'][:40]} -> {hook['angle'][:60]}")
                for idea in score.get("suggested_episode_ideas", [])[:2]:
                    print(f"           Idea: {idea['title']}")
            else:
                if save_score(sb, podcast["id"], speaker["id"], score):
                    stats["saved"] += 1

            results.append((podcast, score))

    # Summary
    print(f"\n{'='*60}")
    print(f"Scoring complete for {speaker['name']}")
    print(f"  Scored: {stats['scored']}")
    print(f"  Strong: {stats['strong']}")
    print(f"  Moderate: {stats['moderate']}")
    print(f"  Weak: {stats['weak']}")
    print(f"  Errors: {stats['errors']}")
    if not args.test:
        print(f"  Saved: {stats['saved']}")
    else:
        print("  DRY RUN — no database changes made")


if __name__ == "__main__":
    main()
