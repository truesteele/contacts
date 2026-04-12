#!/usr/bin/env python3
"""
Podcast Fit Scoring — Holistic GPT-5.4 mini scoring

GPT receives ALL available information (speaker profile, podcast data, episodes,
embedding similarity, discovery method, activity, podcast_profile research) and
makes a single holistic fit judgment. No hardcoded signal weights.

Saves fit scores to podcast_pitches (fit fields only; pitch copy comes later).

Usage:
  python scripts/intelligence/score_podcast_fit.py --speaker sally --limit 5 --test
  python scripts/intelligence/score_podcast_fit.py --speaker justin --limit 50 --workers 50
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

SYSTEM_PROMPT = """You are a podcast booking expert scoring fit between a speaker and a podcast.

You have access to multiple data signals. Weigh them holistically — use your judgment:
- Topic alignment and audience relevance matter most
- Recent episodes and specific conversation angles matter
- How active and established the podcast is matters
- Embedding similarity provides a semantic overlap signal (0-1, higher = more overlap)
- Discovery method provides provenance context (how this podcast was found)
- Podcast profile research (when available) gives deeper context on hosts, audience, format

Score 0.0-1.0 where:
- 0.8-1.0 = strong fit (pursue immediately — clear topic overlap, right audience, active show)
- 0.5-0.79 = moderate (worth considering with right angle)
- 0.0-0.49 = weak (poor fit, forced connection)

Be calibrated: a 0.9 should be a near-perfect match. Use the full range."""

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
    pitches: dict[int, dict] = {}
    page_size = 1000
    offset = 0
    while True:
        result = (
            sb.table("podcast_pitches")
            .select("id, podcast_target_id, fit_score, pitch_status")
            .eq("speaker_profile_id", speaker_id)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = result.data or []
        for row in rows:
            if row.get("podcast_target_id") is not None:
                pitches[row["podcast_target_id"]] = row
        if len(rows) < page_size:
            break
        offset += page_size
    return pitches


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


def build_podcast_context(
    podcast: dict,
    episodes: list[dict],
    embedding_sim: float | None = None,
    discovery_methods: list[str] | None = None,
    podcast_profile: dict | None = None,
) -> str:
    """Build full podcast context including all available signals."""
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
    ep_count = podcast.get("episode_count")
    if ep_count:
        parts.append(f"Total episodes: {ep_count}")
    last_ep = podcast.get("last_episode_date")
    if last_ep:
        parts.append(f"Last episode date: {str(last_ep)[:10]}")

    # Podcast profile research (from Perplexity)
    if podcast_profile:
        parts.append("")
        parts.append("RESEARCH PROFILE:")
        about = podcast_profile.get("about", "")
        if about:
            parts.append(f"About: {about}")
        hosts = podcast_profile.get("hosts", [])
        for h in hosts:
            bio = h.get("bio", "")
            if bio:
                parts.append(f"Host — {h.get('name', 'Unknown')}: {bio}")
        audience = podcast_profile.get("audience", {})
        size = audience.get("size_estimate", "")
        demo = audience.get("demographic", "")
        if size or demo:
            parts.append(f"Audience: {size}. {demo}".strip())
        guests = podcast_profile.get("notable_guests", [])
        if guests:
            parts.append(f"Notable guests: {', '.join(guests[:10])}")
        fmt = podcast_profile.get("format", {})
        if fmt.get("style"):
            parts.append(f"Format: {fmt['style']}, ~{fmt.get('length_minutes', '?')}min, {fmt.get('frequency', '?')}")

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

    # Additional signals section
    parts.append("")
    parts.append("ADDITIONAL CONTEXT:")
    if embedding_sim is not None:
        parts.append(f"- Embedding similarity: {embedding_sim:.3f} (semantic overlap between speaker profile and podcast description, 0-1 scale)")
    if discovery_methods:
        parts.append(f"- Discovery method: {', '.join(discovery_methods)} (how this podcast was found)")
    if ep_count:
        parts.append(f"- Established: {ep_count} total episodes")
    if last_ep:
        parts.append(f"- Last published: {str(last_ep)[:10]}")

    return "\n".join(parts)


# -- Helpers -----------------------------------------------------------------

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Pure Python (no numpy needed)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def load_podcast_profiles(sb: Client, podcast_ids: list[int]) -> dict[int, dict]:
    """Load podcast_profile JSONB for a batch of podcast IDs."""
    if not podcast_ids:
        return {}
    result_map = {}
    for i in range(0, len(podcast_ids), 500):
        batch = podcast_ids[i : i + 500]
        result = (
            sb.table("podcast_targets")
            .select("id, podcast_profile")
            .in_("id", batch)
            .not_.is_("podcast_profile", "null")
            .execute()
        )
        for row in result.data or []:
            result_map[row["id"]] = row["podcast_profile"]
    return result_map


# -- GPT Scoring -------------------------------------------------------------

def score_podcast(
    oai: OpenAI,
    speaker_context: str,
    podcast: dict,
    episodes: list[dict],
    embedding_sim: float | None = None,
    discovery_methods: list[str] | None = None,
    podcast_profile: dict | None = None,
) -> dict | None:
    """Score a single podcast's fit with GPT-5.4 mini holistic scoring."""
    podcast_context = build_podcast_context(
        podcast, episodes,
        embedding_sim=embedding_sim,
        discovery_methods=discovery_methods,
        podcast_profile=podcast_profile,
    )

    user_message = (
        f"{speaker_context}\n\n---\n\n{podcast_context}\n\n"
        "Score how well this podcast fits this speaker. Consider all the information above holistically. "
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
        "topic_match": {
            "matching_pillars": score.get("matching_pillars", []),
            "discovery_methods": score.get("_discovery_methods", []),
        },
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
    args = parser.parse_args()

    # Init clients
    sb = get_supabase()
    oai = get_openai()
    print(f"Connected to Supabase and OpenAI")
    print(f"Scoring mode: holistic (GPT-5.4 mini with all context)")

    # Load speaker
    speaker = load_speaker(sb, args.speaker)
    speaker_context = build_speaker_context(speaker)
    print(f"Speaker: {speaker['name']} (id={speaker['id']})")
    print(f"Topic pillars: {len(speaker.get('topic_pillars') or [])}")

    existing_pitches = load_existing_pitches(sb, speaker["id"])
    existing_pending = sum(1 for row in existing_pitches.values() if row.get("fit_score") is None)
    existing_scored = len(existing_pitches) - existing_pending
    print(f"Existing pitch rows: {len(existing_pitches)} ({existing_scored} scored, {existing_pending} pending)")

    # Load speaker embedding
    conn = get_pg_conn()
    speaker_embedding = load_speaker_embedding(conn, speaker["id"])
    if speaker_embedding:
        print(f"Speaker embedding: loaded ({len(speaker_embedding)} dims)")
    else:
        print(f"Speaker embedding: not found (embedding similarity will be omitted)")

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
        conn.close()
        return

    # Load all contextual data in bulk
    podcast_ids = [p["id"] for p in podcasts]
    podcast_embeddings = load_podcast_embeddings(conn, podcast_ids)
    discovery_methods_map = load_podcast_discovery_methods(conn, podcast_ids)
    conn.close()
    podcast_profiles = load_podcast_profiles(sb, podcast_ids)
    print(f"Podcast embeddings loaded: {len(podcast_embeddings)}/{len(podcast_ids)}")
    print(f"Podcast profiles loaded: {len(podcast_profiles)}/{len(podcast_ids)}")

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
        disc_methods = discovery_methods_map.get(podcast["id"], [])
        profile = podcast_profiles.get(podcast["id"])

        # Compute embedding similarity as a context signal for GPT
        emb_sim = None
        pod_emb = podcast_embeddings.get(podcast["id"])
        if speaker_embedding and pod_emb:
            emb_sim = max(0.0, cosine_similarity(speaker_embedding, pod_emb))

        gpt_score = score_podcast(
            oai, speaker_context, podcast, eps,
            embedding_sim=emb_sim,
            discovery_methods=disc_methods,
            podcast_profile=profile,
        )
        if gpt_score is None:
            return (podcast, None)

        # Stash discovery methods for save
        gpt_score["_discovery_methods"] = disc_methods

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
                print(f"           Rationale: {score['fit_rationale'][:120]}")
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
    print(f"  Mode: holistic GPT-5.4 mini")
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
