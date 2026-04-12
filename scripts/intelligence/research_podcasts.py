#!/usr/bin/env python3
"""
Deep research podcasts using Perplexity sonar-pro + GPT-5.4 mini structured output.

Researches podcast details (about, hosts, audience, platforms, notable guests, format,
social media) and saves structured profiles to podcast_targets.podcast_profile.

Usage:
  python scripts/intelligence/research_podcasts.py --speaker sally --limit 10 --test
  python scripts/intelligence/research_podcasts.py --speaker sally --limit 200
  python scripts/intelligence/research_podcasts.py --limit 50  # no speaker filter
  python scripts/intelligence/research_podcasts.py --ids 42,99,103 --force
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")

# -- Constants ---------------------------------------------------------------

PERPLEXITY_MODEL = "sonar-pro"
GPT_MODEL = "gpt-5.4-mini"

PODCAST_PROFILE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "podcast_profile",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "about": {
                    "type": "string",
                    "description": "Full podcast description/mission (2-4 sentences)",
                },
                "hosts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "bio": {"type": "string"},
                            "social_links": {
                                "type": "object",
                                "properties": {
                                    "twitter": {"type": "string"},
                                    "linkedin": {"type": "string"},
                                    "instagram": {"type": "string"},
                                    "website": {"type": "string"},
                                },
                                "required": ["twitter", "linkedin", "instagram", "website"],
                                "additionalProperties": False,
                            },
                        },
                        "required": ["name", "bio", "social_links"],
                        "additionalProperties": False,
                    },
                },
                "audience": {
                    "type": "object",
                    "properties": {
                        "size_estimate": {"type": "string"},
                        "demographic": {"type": "string"},
                    },
                    "required": ["size_estimate", "demographic"],
                    "additionalProperties": False,
                },
                "platforms": {
                    "type": "object",
                    "properties": {
                        "apple_url": {"type": "string"},
                        "spotify_url": {"type": "string"},
                        "youtube_url": {"type": "string"},
                        "website_url": {"type": "string"},
                    },
                    "required": ["apple_url", "spotify_url", "youtube_url", "website_url"],
                    "additionalProperties": False,
                },
                "notable_guests": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "format": {
                    "type": "object",
                    "properties": {
                        "style": {"type": "string"},
                        "length_minutes": {"type": "integer"},
                        "frequency": {"type": "string"},
                    },
                    "required": ["style", "length_minutes", "frequency"],
                    "additionalProperties": False,
                },
                "social_media": {
                    "type": "object",
                    "properties": {
                        "twitter": {"type": "string"},
                        "instagram": {"type": "string"},
                        "facebook": {"type": "string"},
                        "tiktok": {"type": "string"},
                    },
                    "required": ["twitter", "instagram", "facebook", "tiktok"],
                    "additionalProperties": False,
                },
                "awards_recognition": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "about", "hosts", "audience", "platforms",
                "notable_guests", "format", "social_media", "awards_recognition",
            ],
            "additionalProperties": False,
        },
    },
}


# -- Clients -----------------------------------------------------------------

def get_supabase() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def get_openai() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_APIKEY"])


# -- Data Loading ------------------------------------------------------------

def load_podcasts_to_research(
    sb: Client,
    limit: int,
    speaker_slug: str | None = None,
    force: bool = False,
    podcast_ids: list[int] | None = None,
) -> list[dict]:
    """Load podcasts that need research, optionally prioritized by speaker fit."""

    if podcast_ids:
        result = sb.table("podcast_targets").select("*").in_("id", podcast_ids).execute()
        podcasts = result.data or []
        if not force:
            podcasts = [p for p in podcasts if not p.get("researched_at")]
        return podcasts

    if speaker_slug:
        # Get speaker ID
        sp = sb.table("speaker_profiles").select("id").eq("slug", speaker_slug).single().execute()
        if not sp.data:
            print(f"ERROR: Speaker '{speaker_slug}' not found")
            sys.exit(1)
        speaker_id = sp.data["id"]

        # Get podcast IDs ordered by fit score (strong first)
        pitches_query = (
            sb.table("podcast_pitches")
            .select("podcast_target_id, fit_score, fit_tier")
            .eq("speaker_profile_id", speaker_id)
            .not_.is_("fit_score", "null")
            .order("fit_score", desc=True)
        )
        pitch_rows = []
        page_size = 1000
        offset = 0
        while True:
            page = pitches_query.range(offset, offset + page_size - 1).execute()
            rows = page.data or []
            pitch_rows.extend(rows)
            if len(rows) < page_size:
                break
            offset += page_size

        podcast_ids_ordered = [r["podcast_target_id"] for r in pitch_rows]

        if not podcast_ids_ordered:
            print("No scored podcasts found for this speaker")
            return []

        # Load podcast targets
        all_podcasts = {}
        for i in range(0, len(podcast_ids_ordered), 500):
            batch = podcast_ids_ordered[i : i + 500]
            result = sb.table("podcast_targets").select("*").in_("id", batch).execute()
            for p in result.data or []:
                all_podcasts[p["id"]] = p

        # Filter unresearched (unless --force), maintain fit-score ordering
        podcasts = []
        for pid in podcast_ids_ordered:
            p = all_podcasts.get(pid)
            if not p:
                continue
            if not force and p.get("researched_at"):
                continue
            podcasts.append(p)
            if len(podcasts) >= limit:
                break

        return podcasts

    # No speaker — just get unresearched podcasts
    query = sb.table("podcast_targets").select("*")
    if not force:
        query = query.is_("researched_at", "null")
    query = query.not_.is_("enriched_at", "null").order("id").limit(limit)
    result = query.execute()
    return result.data or []


# -- Perplexity Research -----------------------------------------------------

def build_perplexity_query(podcast: dict) -> str:
    """Build a Perplexity search query for a podcast."""
    title = podcast.get("title", "")
    host = podcast.get("host_name") or podcast.get("author") or ""
    website = podcast.get("website_url") or ""

    query = f'Research the podcast "{title}"'
    if host:
        query += f" hosted by {host}"
    if website:
        query += f". Website: {website}"

    query += """

Provide:
1. What the podcast is about (mission, focus areas, typical topics)
2. Host bio(s) — background, credentials, other work
3. Audience size estimate (downloads per episode, total downloads, social media followers) and demographic
4. Where to listen — Apple Podcasts URL, Spotify URL, YouTube URL
5. Notable past guests (names and why they were notable)
6. Format: interview vs solo vs panel, typical episode length, release frequency
7. Social media accounts (podcast's own accounts, not host personal)
8. Any awards, recognition, or press coverage"""

    return query


def research_podcast(podcast: dict, perplexity_key: str) -> dict | None:
    """Call Perplexity to research a podcast. Returns raw response or None."""
    query = build_perplexity_query(podcast)

    headers = {
        "Authorization": f"Bearer {perplexity_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": PERPLEXITY_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert podcast industry researcher. Provide detailed, "
                    "factual information about podcasts including host backgrounds, "
                    "audience metrics, distribution platforms, and notable guests. "
                    "Be specific with URLs and numbers when available."
                ),
            },
            {"role": "user", "content": query},
        ],
        "return_citations": True,
        "return_related_questions": False,
    }

    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", [])
        usage = data.get("usage", {})

        return {
            "content": content,
            "citations": citations,
            "usage": usage,
        }

    except requests.exceptions.RequestException as e:
        print(f"    Perplexity error for '{podcast.get('title', '')}': {e}")
        return None


# -- GPT Structuring --------------------------------------------------------

def structure_profile(
    oai: OpenAI, podcast: dict, raw_research: str
) -> dict | None:
    """Use GPT-5.4 mini to structure raw research into podcast_profile JSON."""
    known_parts = [
        f"Podcast title: {podcast.get('title', '')}",
        f"Author: {podcast.get('author', '')}",
        f"Host name (from RSS): {podcast.get('host_name', '')}",
        f"Website: {podcast.get('website_url', '')}",
        f"RSS URL: {podcast.get('rss_url', '')}",
        f"Episode count: {podcast.get('episode_count', '')}",
        f"Activity status: {podcast.get('activity_status', '')}",
    ]
    if podcast.get("categories"):
        cats = podcast["categories"]
        if isinstance(cats, str):
            cats = json.loads(cats)
        if isinstance(cats, list):
            known_parts.append(f"Categories: {', '.join(cats)}")

    known_context = "\n".join(known_parts)

    user_message = f"""{known_context}

--- RAW WEB RESEARCH ---
{raw_research}
--- END RESEARCH ---

Extract a structured podcast profile from the research above. For any fields where
information is not available, use empty strings or empty arrays. Provide URLs only
if they appear in the research — do not guess or fabricate URLs."""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = oai.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You extract structured podcast profile data from raw web research. "
                            "Be precise — only include information that is explicitly stated in the research. "
                            "For missing data, use empty strings or empty arrays. Never fabricate URLs."
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                response_format=PODCAST_PROFILE_SCHEMA,
            )
            content = resp.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
                continue
            print(f"    GPT structuring error for '{podcast.get('title', '')}': {e}")
            return None


# -- Save --------------------------------------------------------------------

def _strip_null_bytes(obj):
    """Recursively strip null bytes from strings in a dict/list."""
    if isinstance(obj, str):
        return obj.replace("\x00", "")
    if isinstance(obj, dict):
        return {k: _strip_null_bytes(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_null_bytes(v) for v in obj]
    return obj


def save_profile(sb: Client, podcast_id: int, profile: dict) -> bool:
    """Save podcast_profile and researched_at to podcast_targets."""
    try:
        sb.table("podcast_targets").update({
            "podcast_profile": _strip_null_bytes(profile),
            "researched_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", podcast_id).execute()
        return True
    except Exception as e:
        print(f"    DB error saving profile for podcast {podcast_id}: {e}")
        return False


def update_description_if_empty(sb: Client, podcast_id: int, about: str) -> bool:
    """If the podcast has no description, fill it from the research 'about' field."""
    if not about:
        return False
    try:
        current = (
            sb.table("podcast_targets")
            .select("description")
            .eq("id", podcast_id)
            .single()
            .execute()
        )
        if not (current.data.get("description") or "").strip():
            sb.table("podcast_targets").update({
                "description": about,
            }).eq("id", podcast_id).execute()
            return True
    except Exception:
        pass
    return False


# -- Main --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Deep research podcasts with Perplexity + GPT-5.4 mini"
    )
    parser.add_argument("--speaker", choices=["sally", "justin"],
                        help="Prioritize podcasts scored for this speaker (strong fit first)")
    parser.add_argument("--limit", type=int, default=50,
                        help="Max podcasts to research (default: 50)")
    parser.add_argument("--ids", type=str, default="",
                        help="Comma-separated podcast IDs to research")
    parser.add_argument("--force", action="store_true",
                        help="Re-research already-researched podcasts")
    parser.add_argument("--test", action="store_true",
                        help="Dry run: print results without saving")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Delay between Perplexity calls in seconds (default: 1.5)")
    args = parser.parse_args()

    sb = get_supabase()
    oai = get_openai()
    perplexity_key = os.environ.get("PERPLEXITY_APIKEY")
    if not perplexity_key:
        print("ERROR: PERPLEXITY_APIKEY not set")
        sys.exit(1)

    print(f"Connected to Supabase and OpenAI")
    print(f"Perplexity model: {PERPLEXITY_MODEL}")
    print(f"GPT model: {GPT_MODEL}")

    # Parse podcast IDs if provided
    podcast_ids = None
    if args.ids:
        podcast_ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]

    # Load podcasts
    podcasts = load_podcasts_to_research(
        sb,
        args.limit,
        speaker_slug=args.speaker,
        force=args.force,
        podcast_ids=podcast_ids,
    )
    print(f"Podcasts to research: {len(podcasts)}")

    if not podcasts:
        print("No podcasts need research. Done.")
        return

    stats = {
        "researched": 0,
        "structured": 0,
        "saved": 0,
        "descriptions_filled": 0,
        "errors": 0,
        "perplexity_tokens": 0,
    }

    for i, podcast in enumerate(podcasts, 1):
        title = podcast["title"][:60]
        host = podcast.get("host_name") or podcast.get("author") or "Unknown"
        print(f"\n[{i}/{len(podcasts)}] {title} (by {host})")

        # Step 1: Perplexity research
        raw = research_podcast(podcast, perplexity_key)
        if not raw:
            stats["errors"] += 1
            continue

        stats["researched"] += 1
        stats["perplexity_tokens"] += raw["usage"].get("total_tokens", 0)
        print(f"  Research: {len(raw['content'])} chars, {len(raw['citations'])} citations")

        # Step 2: GPT structuring
        profile = structure_profile(oai, podcast, raw["content"])
        if not profile:
            stats["errors"] += 1
            continue

        stats["structured"] += 1

        # Show summary
        about_preview = (profile.get("about") or "")[:100]
        hosts = [h["name"] for h in profile.get("hosts", [])]
        audience = profile.get("audience", {}).get("size_estimate", "unknown")
        platforms_count = sum(
            1 for v in profile.get("platforms", {}).values() if v
        )
        guests_count = len(profile.get("notable_guests", []))
        print(f"  About: {about_preview}...")
        print(f"  Hosts: {', '.join(hosts) or 'none found'}")
        print(f"  Audience: {audience}")
        print(f"  Platforms: {platforms_count} links, Notable guests: {guests_count}")

        if args.test:
            print(f"  [DRY RUN — not saving]")
        else:
            # Step 3: Save
            if save_profile(sb, podcast["id"], profile):
                stats["saved"] += 1

                # Bonus: fill empty descriptions
                if update_description_if_empty(sb, podcast["id"], profile.get("about", "")):
                    stats["descriptions_filled"] += 1
                    print(f"  Filled empty description from research")

        # Rate limit delay
        if i < len(podcasts):
            time.sleep(args.delay)

    # Summary
    print(f"\n{'='*60}")
    print(f"Research complete")
    print(f"  Perplexity researched: {stats['researched']}")
    print(f"  GPT structured: {stats['structured']}")
    if not args.test:
        print(f"  Saved to DB: {stats['saved']}")
        print(f"  Descriptions filled: {stats['descriptions_filled']}")
    else:
        print(f"  DRY RUN — no database changes made")
    print(f"  Errors: {stats['errors']}")
    print(f"  Perplexity tokens: {stats['perplexity_tokens']:,}")

    # Cost estimate
    pplx_cost = stats["perplexity_tokens"] * 0.000003  # rough sonar-pro pricing
    print(f"  Est. Perplexity cost: ${pplx_cost:.2f}")


if __name__ == "__main__":
    main()
