#!/usr/bin/env python3
"""
Podcast Pitch Generation — Claude Sonnet 4.6

Generates personalized podcast pitch emails using Claude Sonnet 4.6 in the
speaker's authentic voice. Uses writing samples for voice matching and
episode hooks from the fit scoring step.

Usage:
  python scripts/intelligence/generate_podcast_pitches.py --speaker sally --limit 3 --test
  python scripts/intelligence/generate_podcast_pitches.py --speaker justin --tier strong,moderate --limit 20
  python scripts/intelligence/generate_podcast_pitches.py --speaker sally --workers 10
"""

import os
import sys
import json
import re
import time
import argparse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from anthropic import Anthropic, RateLimitError, APIError
from supabase import create_client, Client

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")


# ── Constants ──────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"

AI_WRITING_RULES = """RULES (non-negotiable):
- Zero em dashes in any outreach material. Use commas, periods, or colons instead.
- No significance padding ("underscores the importance", "testament to", "pivotal moment")
- No present-participle pileups ("fostering, enabling, enhancing")
- No vague authority ("experts say", "research shows")
- Simple verbs (is/are/has, not "serves as" or "showcases")
- Vary sentence length. Allow fragments. Use contractions.
- Reference a SPECIFIC recent episode by name
- Suggest 2-3 concrete episode topic ideas
- Keep the pitch body under 200 words
- Sound like a real person, not a pitch template
- No "I hope this email finds you well" or similar cliches
- Leave 1-2 small imperfections for authenticity
- No stacked "not only X but also Y" constructions
- No "in conclusion", "all in all", "it should be noted that"
- No "transformative experience", "shines brightest", "comfortable hiking weather"
- No "without sacrificing", "one of the most underrated"
"""

BANNED_PHRASES = [
    "underscores the importance",
    "testament to",
    "pivotal moment",
    "serves as",
    "showcases",
    "shines brightest",
    "it should be noted",
    "in conclusion",
    "all in all",
    "I hope this email finds you well",
    "I hope this message finds you",
    "transformative experience",
    "without sacrificing",
    "one of the most underrated",
    "experts say",
    "research shows",
    "not only",
]


def build_system_prompt(speaker: dict) -> str:
    """Build the system prompt for pitch generation based on speaker profile."""
    name = speaker["name"]
    bio = speaker["bio"]

    # Voice characteristics per speaker
    if speaker["slug"] == "sally":
        voice_guide = """VOICE GUIDE (Sally Steele):
- Direct, opinionated, specific, occasionally poetic
- Uses fragments for emphasis
- Names real people, places, numbers
- Uses contrast to reveal truth
- Anchored in real scenes and moral tension
- Mix short fragments with longer sentences. The fragments carry the weight.
- Opens with specifics, not overviews
- Closes by circling back or reframing"""
    else:
        voice_guide = """VOICE GUIDE (Justin Steele):
- Direct, punchy, uses sentence fragments for emphasis
- Casual and conversational, sounds like a text from a friend
- Names numbers, dates, specific experiences
- Uses contrast to reveal systemic truths
- Anchored in real experience, not abstract principles
- Varies sentence length. Short punches between longer observations."""

    # Writing samples
    samples = speaker.get("writing_samples") or []
    if isinstance(samples, str):
        samples = json.loads(samples)
    samples_text = ""
    for s in samples:
        samples_text += f"\n---\n{s['text']}\n(Source: {s['source']})\n"

    # Past appearances
    appearances = speaker.get("past_appearances") or []
    if isinstance(appearances, str):
        appearances = json.loads(appearances)
    appearances_text = ""
    if appearances:
        appearances_text = "\n\nPAST PODCAST APPEARANCES (mention if relevant):"
        for a in appearances:
            appearances_text += f"\n- {a['podcast_name']}"
            if a.get("date"):
                appearances_text += f" ({a['date']})"

    return f"""You are writing a podcast pitch email from {name} to a podcast host.

{bio}

{voice_guide}

WRITING SAMPLES (match this voice exactly):
{samples_text}
{appearances_text}

{AI_WRITING_RULES}

OUTPUT FORMAT:
Return a JSON object with exactly these fields:
{{
  "subject_line": "Under 60 chars, specific, not clickbait",
  "subject_line_alt": "Alternative subject line, different angle",
  "pitch_body": "The email body. Under 200 words. In {name}'s voice.",
  "episode_reference": "The specific episode you referenced and why",
  "suggested_topics": ["Topic idea 1", "Topic idea 2", "Topic idea 3"]
}}

Return ONLY the JSON object, no markdown fencing, no explanation."""


def build_user_prompt(podcast: dict, episodes: list[dict], fit_data: dict) -> str:
    """Build the user prompt with podcast context and fit data."""
    parts = [
        f"PODCAST: {podcast['title']}",
        f"Host: {podcast.get('host_name') or podcast.get('author') or 'Unknown'}",
    ]

    if podcast.get("description"):
        desc = podcast["description"]
        if len(desc) > 500:
            desc = desc[:500] + "..."
        parts.append(f"Description: {desc}")

    categories = podcast.get("categories")
    if categories:
        if isinstance(categories, str):
            categories = json.loads(categories)
        if isinstance(categories, list):
            parts.append(f"Categories: {', '.join(categories)}")

    if podcast.get("website_url"):
        parts.append(f"Website: {podcast['website_url']}")

    # Recent episodes
    if episodes:
        parts.append(f"\nRECENT EPISODES ({len(episodes)}):")
        for ep in episodes:
            title = ep.get("title", "Untitled")
            desc = ep.get("description", "")
            if desc and len(desc) > 200:
                desc = desc[:200] + "..."
            date = ep.get("published_at", "")
            if date:
                date = date[:10]
            duration = ep.get("duration_seconds")
            dur_str = f" ({duration // 60}min)" if duration else ""
            parts.append(f"- [{date}]{dur_str} {title}")
            if desc:
                parts.append(f"  {desc}")

    # Fit scoring context
    parts.append(f"\nFIT ANALYSIS:")
    parts.append(f"Fit tier: {fit_data.get('fit_tier', 'unknown')}")
    parts.append(f"Fit score: {fit_data.get('fit_score', 0):.2f}")
    parts.append(f"Rationale: {fit_data.get('fit_rationale', '')}")

    matching = fit_data.get("topic_match") or []
    if isinstance(matching, str):
        matching = json.loads(matching)
    if matching:
        parts.append(f"Matching pillars: {', '.join(matching)}")

    hooks = fit_data.get("episode_hooks") or []
    if isinstance(hooks, str):
        hooks = json.loads(hooks)
    if hooks:
        parts.append("\nEPISODE HOOKS (use these to personalize):")
        for h in hooks:
            if isinstance(h, dict):
                parts.append(f"- {h.get('episode_title', '')}: {h.get('angle', '')}")

    suggested = fit_data.get("suggested_topics") or []
    if isinstance(suggested, str):
        suggested = json.loads(suggested)
    if suggested:
        parts.append("\nSUGGESTED TOPICS FROM FIT SCORING:")
        for s in suggested:
            if isinstance(s, dict):
                parts.append(f"- {s.get('title', '')}: {s.get('description', '')}")
            elif isinstance(s, str):
                parts.append(f"- {s}")

    parts.append("\nWrite the pitch email. Make it specific to THIS podcast and reference a real recent episode by name.")

    return "\n".join(parts)


# ── Clients ────────────────────────────────────────────────────────────

def get_supabase() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def get_anthropic() -> Anthropic:
    return Anthropic()  # uses ANTHROPIC_API_KEY env var


# ── Data Loading ───────────────────────────────────────────────────────

def load_speaker(sb: Client, slug: str) -> dict:
    """Load a speaker profile by slug."""
    result = sb.table("speaker_profiles").select("*").eq("slug", slug).execute()
    if not result.data:
        print(f"ERROR: No speaker profile found for slug '{slug}'")
        sys.exit(1)
    return result.data[0]


def load_ungenerated_pitches(sb: Client, speaker_id: int, tiers: list[str], limit: int) -> list[dict]:
    """Load podcast_pitches rows that have fit scores but no pitch body."""
    query = sb.table("podcast_pitches") \
        .select("*") \
        .eq("speaker_profile_id", speaker_id) \
        .is_("pitch_body", "null") \
        .order("fit_score", desc=True) \
        .limit(limit)

    # Apply tier filter at DB level
    if tiers:
        query = query.in_("fit_tier", tiers)

    result = query.execute()
    return result.data


def load_podcast(sb: Client, podcast_id: int) -> dict | None:
    """Load a podcast target by ID."""
    result = sb.table("podcast_targets").select("*").eq("id", podcast_id).execute()
    return result.data[0] if result.data else None


def load_episodes(sb: Client, podcast_id: int) -> list[dict]:
    """Load recent episodes for a podcast."""
    result = sb.table("podcast_episodes") \
        .select("title, description, published_at, duration_seconds") \
        .eq("podcast_target_id", podcast_id) \
        .order("published_at", desc=True) \
        .limit(5) \
        .execute()
    return result.data


# ── Pitch Generation ──────────────────────────────────────────────────

def generate_pitch(client: Anthropic, system_prompt: str, user_prompt: str) -> dict | None:
    """Generate a single pitch using Claude Sonnet 4.6."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = message.content[0].text

            # Strip markdown fencing if present
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*\n?", "", content)
                content = re.sub(r"\n?```\s*$", "", content)

            parsed = json.loads(content)

            # Validate required fields
            required = ["subject_line", "subject_line_alt", "pitch_body",
                        "episode_reference", "suggested_topics"]
            for field in required:
                if field not in parsed:
                    print(f"    Missing field: {field}")
                    return None

            return parsed

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
        except json.JSONDecodeError as e:
            print(f"    JSON parse error: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                return None
        except Exception as e:
            print(f"    Unexpected error: {e}")
            return None

    return None


# ── AI-Tell Audit ─────────────────────────────────────────────────────

def audit_pitch(pitch: dict) -> list[str]:
    """Check a pitch for AI writing tells. Returns list of issues found."""
    issues = []
    body = pitch.get("pitch_body", "")
    subject = pitch.get("subject_line", "")
    subject_alt = pitch.get("subject_line_alt", "")
    all_text = f"{subject} {subject_alt} {body}"

    # Check for em dashes
    if "\u2014" in all_text or " -- " in all_text:
        issues.append("Contains em dash(es)")

    # Check for banned phrases
    lower_text = all_text.lower()
    for phrase in BANNED_PHRASES:
        if phrase.lower() in lower_text:
            issues.append(f"Banned phrase: '{phrase}'")

    # Check word count
    word_count = len(body.split())
    if word_count > 200:
        issues.append(f"Pitch body too long: {word_count} words (max 200)")

    # Check subject line length
    if len(subject) > 60:
        issues.append(f"Subject line too long: {len(subject)} chars (max 60)")

    # Check for present-participle pileups (3+ -ing words in a row)
    ing_pattern = r'\b\w+ing\b(?:,\s*\b\w+ing\b){2,}'
    if re.search(ing_pattern, all_text):
        issues.append("Present-participle pileup detected")

    return issues


def fix_em_dashes(text: str) -> str:
    """Replace em dashes with commas or periods."""
    # Replace em dash surrounded by spaces with comma
    text = text.replace(" \u2014 ", ", ")
    # Replace em dash at start of clause with period
    text = text.replace("\u2014", ",")
    # Replace double hyphens
    text = text.replace(" -- ", ", ")
    return text


# ── Save ───────────────────────────────────────────────────────────────

def save_pitch(sb: Client, pitch_id: int, pitch_data: dict) -> bool:
    """Update podcast_pitches row with generated pitch content."""
    suggested = pitch_data.get("suggested_topics", [])
    if isinstance(suggested, list) and all(isinstance(s, str) for s in suggested):
        suggested = [{"title": s, "description": ""} for s in suggested]

    row = {
        "subject_line": pitch_data["subject_line"],
        "subject_line_alt": pitch_data["subject_line_alt"],
        "pitch_body": pitch_data["pitch_body"],
        "episode_reference": pitch_data.get("episode_reference", ""),
        "suggested_topics": suggested,
        "pitch_status": "draft",
        "model_used": MODEL,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        sb.table("podcast_pitches").update(row).eq("id", pitch_id).execute()
        return True
    except Exception as e:
        print(f"    DB error saving pitch {pitch_id}: {e}")
        return False


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate podcast pitch emails using Claude Sonnet 4.6"
    )
    parser.add_argument("--speaker", required=True, choices=["sally", "justin"],
                        help="Speaker slug to generate pitches for")
    parser.add_argument("--tier", default="strong,moderate",
                        help="Comma-separated fit tiers to generate for (default: strong,moderate)")
    parser.add_argument("--limit", type=int, default=20,
                        help="Max pitches to generate (default: 20)")
    parser.add_argument("--workers", type=int, default=10,
                        help="Concurrent Claude workers (default: 10)")
    parser.add_argument("--test", action="store_true",
                        help="Dry run: print pitches without saving")
    args = parser.parse_args()

    tiers = [t.strip() for t in args.tier.split(",")]

    # Validate API key upfront
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set in environment")
        sys.exit(1)

    # Init clients
    sb = get_supabase()
    anthropic_client = get_anthropic()
    print(f"Connected to Supabase and Anthropic")

    # Load speaker
    speaker = load_speaker(sb, args.speaker)
    system_prompt = build_system_prompt(speaker)
    print(f"Speaker: {speaker['name']} (id={speaker['id']})")
    print(f"Tiers: {', '.join(tiers)}")

    # Load ungenerated pitches
    pitches = load_ungenerated_pitches(sb, speaker["id"], tiers, args.limit)
    print(f"Pitches to generate: {len(pitches)}")

    if not pitches:
        print("No ungenerated pitches found. Done.")
        return

    # Stats
    stats = {"generated": 0, "saved": 0, "errors": 0, "audit_issues": 0,
             "em_dashes_fixed": 0, "by_tier": {"strong": 0, "moderate": 0, "weak": 0}}

    def process_one(pitch_row: dict) -> tuple[dict, dict | None, list[str]]:
        podcast_id = pitch_row["podcast_target_id"]
        podcast = load_podcast(sb, podcast_id)
        if not podcast:
            return (pitch_row, None, ["Podcast not found"])

        episodes = load_episodes(sb, podcast_id)
        user_prompt = build_user_prompt(podcast, episodes, pitch_row)
        result = generate_pitch(anthropic_client, system_prompt, user_prompt)

        if result is None:
            return (pitch_row, None, ["Generation failed"])

        # Fix em dashes automatically
        for field in ["pitch_body", "subject_line", "subject_line_alt"]:
            if field in result and result[field]:
                result[field] = fix_em_dashes(result[field])

        issues = audit_pitch(result)
        return (pitch_row, result, issues)

    print(f"\nGenerating {len(pitches)} pitches with {args.workers} workers...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_one, p): p for p in pitches}
        for future in as_completed(futures):
            pitch_row, result, issues = future.result()
            podcast_id = pitch_row["podcast_target_id"]
            tier = pitch_row.get("fit_tier", "unknown")

            if result is None:
                stats["errors"] += 1
                print(f"  ERROR podcast_id={podcast_id}: {'; '.join(issues)}")
                continue

            stats["generated"] += 1
            if tier in stats["by_tier"]:
                stats["by_tier"][tier] += 1

            word_count = len(result["pitch_body"].split())

            # Check for remaining em dashes after fix
            if "\u2014" in result.get("pitch_body", ""):
                stats["em_dashes_fixed"] += 1

            # Print result
            print(f"\n  [{tier.upper()}] {result['subject_line']}")
            print(f"    Alt: {result['subject_line_alt']}")
            print(f"    Words: {word_count}")
            print(f"    Episode ref: {result['episode_reference'][:80]}")
            topics = result.get("suggested_topics", [])
            if topics:
                topic_strs = []
                for t in topics[:3]:
                    if isinstance(t, dict):
                        topic_strs.append(t.get("title", str(t)))
                    else:
                        topic_strs.append(str(t))
                print(f"    Topics: {'; '.join(topic_strs)}")

            if issues:
                stats["audit_issues"] += len(issues)
                for issue in issues:
                    print(f"    AUDIT: {issue}")

            if args.test:
                print(f"    --- PITCH BODY ---")
                print(f"    {result['pitch_body']}")
                print(f"    --- END ---")
            else:
                if save_pitch(sb, pitch_row["id"], result):
                    stats["saved"] += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Pitch generation complete for {speaker['name']}")
    print(f"  Generated: {stats['generated']}")
    print(f"  Strong: {stats['by_tier']['strong']}")
    print(f"  Moderate: {stats['by_tier']['moderate']}")
    print(f"  Weak: {stats['by_tier']['weak']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Audit issues: {stats['audit_issues']}")
    if not args.test:
        print(f"  Saved: {stats['saved']}")
    else:
        print("  DRY RUN - no database changes made")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
