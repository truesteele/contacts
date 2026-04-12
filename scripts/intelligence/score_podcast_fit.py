#!/usr/bin/env python3
"""
Podcast Fit Scoring — GPT-5.4 mini structured output + composite multi-signal scoring

Scores how well each discovered podcast fits a speaker's topic pillars.
Composite mode (default) combines 5 signals: GPT fit, embedding similarity,
similar-speaker boost, activity recency, and episode count.

Saves fit scores to podcast_pitches (fit fields only; pitch copy comes later).

Usage:
  python scripts/intelligence/score_podcast_fit.py --speaker sally --limit 5 --test
  python scripts/intelligence/score_podcast_fit.py --speaker justin --limit 50 --workers 50
  python scripts/intelligence/score_podcast_fit.py --speaker sally --no-composite
"""

import os
import sys
import json
import math
import time
import argparse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from supabase import create_client, Client

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")


# -- Constants ---------------------------------------------------------------

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


# -- Clients -----------------------------------------------------------------

def get_supabase() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def get_openai() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_APIKEY"])


def get_pg_conn():
    """Direct PostgreSQL connection for pgvector queries."""
    return psycopg2.connect(
        host="db.ypqsrejrsocebnldicke.supabase.co",
        port=5432,
        dbname="postgres",
        user="postgres",
        password=os.environ["SUPABASE_DB_PASSWORD"],
    )


# -- Data Loading ------------------------------------------------------------

def load_speaker(sb: Client, slug: str) -> dict:
    """Load a speaker profile by slug."""
    result = sb.table("speaker_profiles").select("*").eq("slug", slug).execute()
    if not result.data:
        print(f"ERROR: No speaker profile found for slug '{slug}'")
        sys.exit(1)
    return result.data[0]


def load_speaker_embedding(conn, speaker_id: int) -> list[float] | None:
    """Load speaker's profile_embedding via psycopg2."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT profile_embedding::text FROM speaker_profiles WHERE id = %s",
            (speaker_id,),
        )
        row = cur.fetchone()
        if row and row[0]:
            return _parse_pg_vector(row[0])
    return None


def load_podcast_embeddings(conn, podcast_ids: list[int]) -> dict[int, list[float]]:
    """Load description_embedding for a batch of podcast IDs."""
    if not podcast_ids:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, description_embedding::text FROM podcast_targets WHERE id = ANY(%s)",
            (podcast_ids,),
        )
        result = {}
        for row in cur.fetchall():
            if row[1]:
                result[row[0]] = _parse_pg_vector(row[1])
        return result


def load_podcast_discovery_methods(conn, podcast_ids: list[int]) -> dict[int, list[str]]:
    """Load discovery_methods for a batch of podcast IDs."""
    if not podcast_ids:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, discovery_methods FROM podcast_targets WHERE id = ANY(%s)",
            (podcast_ids,),
        )
        result = {}
        for row in cur.fetchall():
            result[row[0]] = row[1] or []
        return result


def load_existing_pitches(sb: Client, speaker_id: int) -> dict[int, dict]:
    """Load existing pitch rows keyed by podcast_target_id for a speaker."""
    result = (
        sb.table("podcast_pitches")
        .select("id, podcast_target_id, fit_score, pitch_status")
        .eq("speaker_profile_id", speaker_id)
        .execute()
    )
    return {
        row["podcast_target_id"]: row
        for row in (result.data or [])
        if row.get("podcast_target_id") is not None
    }


def _parse_pg_vector(vec_str: str) -> list[float]:
    """Parse pgvector text representation '[0.1,0.2,...]' into list of floats."""
    return [float(x) for x in vec_str.strip("[]").split(",")]


def load_unscored_podcasts(
    sb: Client,
    speaker_id: int,
    limit: int,
    min_episodes: int,
    existing_pitches: dict[int, dict] | None = None,
) -> list[dict]:
    """Load podcasts that haven't been scored for this speaker yet."""
    pitch_rows = existing_pitches or load_existing_pitches(sb, speaker_id)
    scored_ids = [
        podcast_id
        for podcast_id, row in pitch_rows.items()
        if row.get("fit_score") is not None
    ]

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


# -- Prompt Building ---------------------------------------------------------

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
            if desc and len(desc) > 300:
                desc = desc[:300] + "..."
            date = ep.get("published_at", "")
            if date:
                date = date[:10]
            duration = ep.get("duration_seconds")
            dur_str = f" ({duration // 60}min)" if duration else ""
            parts.append(f"- [{date}]{dur_str} {title}")
            if desc:
                parts.append(f"  {desc}")

    return "\n".join(parts)


# -- Composite Signal Functions ----------------------------------------------

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Pure Python (no numpy needed)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def compute_embedding_similarity(
    speaker_embedding: list[float] | None,
    podcast_embedding: list[float] | None,
) -> float:
    """Cosine similarity between speaker and podcast embeddings. Returns 0-1."""
    if speaker_embedding is None or podcast_embedding is None:
        return 0.3  # neutral default for missing embeddings
    return max(0.0, cosine_similarity(speaker_embedding, podcast_embedding))


def compute_activity_recency(last_episode_date: str | None) -> float:
    """0-1 score based on how recently the podcast published."""
    if not last_episode_date:
        return 0.3  # unknown = moderate
    try:
        if isinstance(last_episode_date, str):
            # Handle ISO format with or without timezone
            date_str = last_episode_date.replace("Z", "+00:00")
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str)
            else:
                dt = datetime.fromisoformat(date_str + "T00:00:00+00:00")
        else:
            dt = last_episode_date
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days_ago = (datetime.now(timezone.utc) - dt).days
    except (ValueError, TypeError):
        return 0.3
    if days_ago <= 7:
        return 1.0
    if days_ago <= 30:
        return 0.8
    if days_ago <= 60:
        return 0.5
    if days_ago <= 90:
        return 0.3
    return 0.1


def compute_episode_count_signal(count: int | None) -> float:
    """0-1 normalized. More episodes = more established."""
    if not count:
        return 0.1
    if count >= 200:
        return 1.0
    if count >= 100:
        return 0.8
    if count >= 50:
        return 0.6
    if count >= 20:
        return 0.4
    if count >= 10:
        return 0.2
    return 0.1


def compute_composite_score(
    gpt_fit_score: float,
    embedding_similarity: float,
    similar_speaker_boost: float,
    activity_recency: float,
    episode_count_signal: float,
) -> tuple[float, str]:
    """
    Compute composite score from 4 base signals + similar-speaker bonus.

    Base score uses 4 signals normalized to sum to 1.0:
      GPT fit (0.41) + Embedding (0.35) + Recency (0.12) + Episodes (0.12)
    Similar-speaker is a bonus (0.10) added on top, capped at 1.0.
    This prevents non-similar-speaker podcasts from being penalized.
    """
    base = (
        0.41 * gpt_fit_score
        + 0.35 * embedding_similarity
        + 0.12 * activity_recency
        + 0.12 * episode_count_signal
    )
    bonus = 0.10 if similar_speaker_boost > 0 else 0.0
    composite = min(1.0, base + bonus)

    if composite >= 0.70:
        tier = "strong"
    elif composite >= 0.45:
        tier = "moderate"
    else:
        tier = "weak"

    return round(composite, 4), tier


# -- GPT Scoring -------------------------------------------------------------

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


# -- Save --------------------------------------------------------------------

def save_score(
    sb: Client,
    podcast_id: int,
    speaker_id: int,
    score: dict,
    existing_pitch_id: int | None = None,
) -> bool:
    """Save fit score to podcast_pitches table."""
    timestamp = datetime.now(timezone.utc).isoformat()
    fit_fields = {
        "fit_tier": score["fit_tier"],
        "fit_score": score["fit_score"],
        "fit_rationale": score["fit_rationale"],
        "topic_match": score.get("topic_match", score.get("matching_pillars", [])),
        "episode_hooks": score.get("episode_hooks", []),
        "suggested_topics": score.get("suggested_episode_ideas", []),
        "model_used": MODEL,
        "updated_at": timestamp,
    }

    try:
        if existing_pitch_id:
            sb.table("podcast_pitches").update(fit_fields).eq("id", existing_pitch_id).execute()
        else:
            row = {
                "podcast_target_id": podcast_id,
                "speaker_profile_id": speaker_id,
                "pitch_status": "unscored",
                "generated_at": timestamp,
                **fit_fields,
            }
            sb.table("podcast_pitches").insert(row).execute()
        return True
    except Exception as e:
        print(f"    DB error saving score for podcast {podcast_id}: {e}")
        return False


# -- Main --------------------------------------------------------------------

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
    parser.add_argument("--no-composite", action="store_true",
                        help="Disable composite scoring, use GPT-only (backward compat)")
    args = parser.parse_args()

    use_composite = not args.no_composite

    # Init clients
    sb = get_supabase()
    oai = get_openai()
    print(f"Connected to Supabase and OpenAI")
    print(f"Scoring mode: {'composite (5 signals)' if use_composite else 'GPT-only'}")

    # Load speaker
    speaker = load_speaker(sb, args.speaker)
    speaker_context = build_speaker_context(speaker)
    print(f"Speaker: {speaker['name']} (id={speaker['id']})")
    print(f"Topic pillars: {len(speaker.get('topic_pillars') or [])}")

    existing_pitches = load_existing_pitches(sb, speaker["id"])
    existing_pending = sum(1 for row in existing_pitches.values() if row.get("fit_score") is None)
    existing_scored = len(existing_pitches) - existing_pending
    print(f"Existing pitch rows: {len(existing_pitches)} ({existing_scored} scored, {existing_pending} pending)")

    # Load speaker embedding for composite scoring
    speaker_embedding = None
    if use_composite:
        conn = get_pg_conn()
        speaker_embedding = load_speaker_embedding(conn, speaker["id"])
        if speaker_embedding:
            print(f"Speaker embedding: loaded ({len(speaker_embedding)} dims)")
        else:
            print(f"Speaker embedding: not found (will use neutral default 0.3)")

    # Load unscored podcasts
    podcasts = load_unscored_podcasts(
        sb,
        speaker["id"],
        args.limit,
        args.min_episodes,
        existing_pitches=existing_pitches,
    )
    print(f"Podcasts to score: {len(podcasts)}")

    if not podcasts:
        print("No unscored podcasts found. Done.")
        return

    # Load podcast embeddings and discovery methods in bulk for composite
    podcast_embeddings = {}
    discovery_methods_map = {}
    if use_composite:
        podcast_ids = [p["id"] for p in podcasts]
        podcast_embeddings = load_podcast_embeddings(conn, podcast_ids)
        discovery_methods_map = load_podcast_discovery_methods(conn, podcast_ids)
        conn.close()
        print(f"Podcast embeddings loaded: {len(podcast_embeddings)}/{len(podcast_ids)}")

    # Load episodes for each podcast and filter by min-episodes
    podcast_episodes = {}
    filtered = []
    for p in podcasts:
        eps = load_episodes(sb, p["id"])
        if len(eps) < args.min_episodes:
            print(f"  Skipping '{p['title']}' -- only {len(eps)} episodes (min: {args.min_episodes})")
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
        gpt_score = score_podcast(oai, speaker_context, podcast, eps)
        if gpt_score is None:
            return (podcast, None)

        if not use_composite:
            return (podcast, gpt_score)

        # Compute composite signals
        gpt_fit = gpt_score["fit_score"]
        emb_sim = compute_embedding_similarity(
            speaker_embedding, podcast_embeddings.get(podcast["id"])
        )
        disc_methods = discovery_methods_map.get(podcast["id"], [])
        ss_boost = 1.0 if "similar_speaker" in disc_methods else 0.0
        recency = compute_activity_recency(podcast.get("last_episode_date"))
        ep_count = compute_episode_count_signal(podcast.get("episode_count"))

        composite, tier = compute_composite_score(
            gpt_fit, emb_sim, ss_boost, recency, ep_count
        )

        # Build enriched score dict
        signals = {
            "gpt_fit_score": round(gpt_fit, 4),
            "embedding_similarity": round(emb_sim, 4),
            "similar_speaker_boost": round(ss_boost, 4),
            "activity_recency": round(recency, 4),
            "episode_count_signal": round(ep_count, 4),
        }

        gpt_score["fit_tier"] = tier
        gpt_score["fit_score"] = composite
        gpt_score["topic_match"] = {
            "composite_score": composite,
            "signals": signals,
            "matching_pillars": gpt_score.get("matching_pillars", []),
            "discovery_methods": disc_methods,
        }
        gpt_score["_signals"] = signals  # for display

        return (podcast, gpt_score)

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
            print(f"  {tier.upper():8s} ({score['fit_score']:.2f}) '{title}' -- {pillars}")

            if args.test:
                print(f"           Rationale: {score['fit_rationale'][:100]}")
                if use_composite and "_signals" in score:
                    s = score["_signals"]
                    print(
                        f"           Signals: GPT={s['gpt_fit_score']:.2f} "
                        f"Emb={s['embedding_similarity']:.2f} "
                        f"Speaker={s['similar_speaker_boost']:.2f} "
                        f"Recency={s['activity_recency']:.2f} "
                        f"Episodes={s['episode_count_signal']:.2f}"
                    )
                for hook in score.get("episode_hooks", [])[:2]:
                    print(f"           Hook: {hook['episode_title'][:40]} -> {hook['angle'][:60]}")
                for idea in score.get("suggested_episode_ideas", [])[:2]:
                    print(f"           Idea: {idea['title']}")
            else:
                existing_pitch_id = existing_pitches.get(podcast["id"], {}).get("id")
                if save_score(
                    sb,
                    podcast["id"],
                    speaker["id"],
                    score,
                    existing_pitch_id=existing_pitch_id,
                ):
                    stats["saved"] += 1

            results.append((podcast, score))

    # Summary
    print(f"\n{'='*60}")
    print(f"Scoring complete for {speaker['name']}")
    print(f"  Mode: {'composite (5 signals)' if use_composite else 'GPT-only'}")
    print(f"  Scored: {stats['scored']}")
    print(f"  Strong: {stats['strong']}")
    print(f"  Moderate: {stats['moderate']}")
    print(f"  Weak: {stats['weak']}")
    print(f"  Errors: {stats['errors']}")
    if not args.test:
        print(f"  Saved: {stats['saved']}")
    else:
        print("  DRY RUN -- no database changes made")


if __name__ == "__main__":
    main()
