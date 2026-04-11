#!/usr/bin/env python3
"""
Conference networking toolkit — Config-driven GPT triage scoring.

Scores conference attendees on partnership relevance using GPT-5 mini
structured output. All conference/org-specific values come from the
YAML config file.

Usage:
  python scripts/conference/triage.py --config conferences/ted-2026/config.yaml
  python scripts/conference/triage.py --config conferences/ted-2026/config.yaml --test
  python scripts/conference/triage.py --config conferences/ted-2026/config.yaml --test -n 5
  python scripts/conference/triage.py --config conferences/ted-2026/config.yaml --workers 50
"""

import os
import json
import argparse
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from pydantic import BaseModel, Field

load_dotenv('/Users/Justin/Code/TrueSteele/contacts/.env')

# Add repo root to path for scripts.conference imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.conference.config import ConferenceConfig


# ── Dynamic Pydantic Schema ──────────────────────────────────────────

def build_partnership_enum(config: ConferenceConfig) -> type[Enum]:
    """Build a PartnershipType enum from config partnership_types keys."""
    members = {k: k for k in config.organization.partnership_types}
    return Enum('PartnershipType', members, type=str)


def build_triage_model(partnership_enum: type[Enum]) -> type[BaseModel]:
    """Build the GPT structured output model with config-driven partnership types."""

    class TriageResult(BaseModel):
        relevance_score: int = Field(ge=0, le=100, description="0-100 score for partnership fit")
        partnership_type: partnership_enum = Field(description="Primary partnership type")
        partnership_types: list[str] = Field(default_factory=list, description="All applicable partnership types")
        reasoning: str = Field(description="1-2 sentence explanation of relevance")
        conversation_hook: str = Field(description="Specific opener for the primary networker to use")
        key_signal: str = Field(default="", description="Strongest signal in their profile")

    return TriageResult


# ── User Prompt Builder ───────────────────────────────────────────────

def build_user_prompt(attendee: dict, config: ConferenceConfig) -> str:
    """Build the user prompt from attendee data, using config for field mapping."""
    parts = []
    prefix = config.conference.field_prefix  # e.g., "ted"

    # Name
    first = attendee.get(f'{prefix}_firstname', '')
    last = attendee.get(f'{prefix}_lastname', '')
    name = f"{first} {last}".strip()
    if not name:
        name = attendee.get(f'{prefix}_name', '')
    parts.append(f"NAME: {name}")

    # Basic fields
    if attendee.get(f'{prefix}_title'):
        parts.append(f"TITLE: {attendee[f'{prefix}_title']}")
    if attendee.get(f'{prefix}_org'):
        parts.append(f"ORGANIZATION: {attendee[f'{prefix}_org']}")

    city = attendee.get(f'{prefix}_city', '')
    country = attendee.get(f'{prefix}_country', '')
    loc = f"{city}, {country}".strip(', ')
    if loc:
        parts.append(f"LOCATION: {loc}")

    # Conference roles from config
    for role_def in config.conference.roles:
        if attendee.get(role_def['field']):
            parts.append(f"ROLE: {role_def['label']}")

    # Bio / extended fields
    if attendee.get(f'{prefix}_about'):
        parts.append(f"BIO: {attendee[f'{prefix}_about']}")
    if attendee.get(f'{prefix}_idea'):
        parts.append(f"IDEA WORTH SPREADING: {attendee[f'{prefix}_idea']}")
    if attendee.get(f'{prefix}_passion'):
        parts.append(f"PASSIONS: {attendee[f'{prefix}_passion']}")
    if attendee.get(f'{prefix}_ask_me_about'):
        parts.append(f"ASK ME ABOUT: {attendee[f'{prefix}_ask_me_about']}")

    # LinkedIn enrichment data (from Apify)
    li = attendee.get('linkedin_enrichment', {})
    if li:
        if li.get('headline'):
            parts.append(f"LINKEDIN HEADLINE: {li['headline']}")
        if li.get('about'):
            parts.append(f"LINKEDIN ABOUT: {li['about'][:500]}")

        # Experience
        exp = li.get('experience', [])
        if exp:
            exp_strs = []
            for e in exp[:5]:
                title = e.get('position', e.get('title', ''))
                company = e.get('companyName', e.get('company', ''))
                if title or company:
                    exp_strs.append(f"{title} at {company}")
            if exp_strs:
                parts.append(f"EXPERIENCE: {' | '.join(exp_strs)}")

        # Volunteer/causes
        vol = li.get('volunteering', [])
        if vol:
            vol_strs = []
            for v in vol[:5]:
                role = v.get('position', v.get('title', ''))
                org = v.get('companyName', v.get('company', ''))
                if role or org:
                    vol_strs.append(f"{role} at {org}")
            if vol_strs:
                parts.append(f"VOLUNTEER: {' | '.join(vol_strs)}")

        causes = li.get('causes', [])
        if causes:
            parts.append(f"CAUSES: {', '.join(causes)}")

        # Skills
        skills = li.get('topSkills', li.get('skills', []))
        if skills:
            skill_names = [s.get('name', s) if isinstance(s, dict) else s for s in skills[:10]]
            parts.append(f"SKILLS: {', '.join(skill_names)}")

        # Education
        edu = li.get('education', [])
        if edu:
            edu_strs = []
            for e in edu[:3]:
                school = e.get('schoolName', e.get('school', ''))
                degree = e.get('degree', e.get('degreeName', ''))
                if school:
                    edu_strs.append(f"{degree} from {school}" if degree else school)
            if edu_strs:
                parts.append(f"EDUCATION: {' | '.join(edu_strs)}")

    # DB enrichment data
    if attendee.get('db_headline'):
        parts.append(f"DB HEADLINE: {attendee['db_headline']}")
    if attendee.get('db_summary') and not li:
        parts.append(f"DB SUMMARY: {attendee['db_summary'][:300]}")
    if attendee.get('db_outdoorithm_fit'):
        parts.append(f"EXISTING FIT SCORE: {attendee['db_outdoorithm_fit']}")

    # Warm lead context — connection fields from config users
    flags = []
    primary_conn = config.users.primary.connection_field or f"{config.users.primary.name.lower()}_connection"
    support_conn = config.users.support.connection_field or f"{config.users.support.name.lower()}_connection"

    if attendee.get(primary_conn):
        flags.append(f"{config.users.primary.name}'s LinkedIn connection")
    if attendee.get(support_conn):
        flags.append(f"{config.users.support.name}'s LinkedIn connection")
    if attendee.get('db_closeness') and attendee['db_closeness'] != 'no_history':
        flags.append(f"Relationship: {attendee['db_closeness']}")
    if flags:
        parts.append(f"WARM LEAD: {', '.join(flags)}")

    return '\n'.join(parts)


# ── GPT Scoring ───────────────────────────────────────────────────────

def score_attendee(attendee: dict, idx: int, total: int,
                   client: OpenAI, system_prompt: str,
                   triage_model: type[BaseModel],
                   config: ConferenceConfig) -> dict:
    """Score a single attendee with GPT-5 mini structured output."""
    prefix = config.conference.field_prefix
    user_prompt = build_user_prompt(attendee, config)

    att_id = attendee.get(f'{prefix}_id', attendee.get('id', ''))
    att_name = attendee.get(f'{prefix}_name', '')
    if not att_name:
        att_name = f"{attendee.get(f'{prefix}_firstname', '')} {attendee.get(f'{prefix}_lastname', '')}".strip()

    for attempt in range(3):
        try:
            response = client.beta.chat.completions.parse(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=triage_model,
            )
            result = response.choices[0].message.parsed
            if (idx + 1) % 100 == 0 or idx < 5:
                print(f"  [{idx+1}/{total}] {att_name}: "
                      f"score={result.relevance_score}, type={result.partnership_type.value}")

            return {
                f'{prefix}_id': att_id,
                f'{prefix}_name': att_name,
                'relevance_score': result.relevance_score,
                'partnership_type': result.partnership_type.value,
                'partnership_types': result.partnership_types,
                'reasoning': result.reasoning,
                'conversation_hook': result.conversation_hook,
                'key_signal': result.key_signal,
            }
        except RateLimitError:
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == 2:
                print(f"  ERROR [{idx+1}/{total}] {att_name}: {e}")
                return {
                    f'{prefix}_id': att_id,
                    f'{prefix}_name': att_name,
                    'relevance_score': 0,
                    'partnership_type': 'unlikely',
                    'partnership_types': [],
                    'reasoning': f'Error: {str(e)[:100]}',
                    'conversation_hook': '',
                    'key_signal': '',
                    'error': True,
                }
            time.sleep(1)

    return {f'{prefix}_id': att_id, 'relevance_score': 0, 'error': True}


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Config-driven conference attendee triage scoring")
    parser.add_argument('--config', required=True, help="Path to conference config YAML")
    parser.add_argument('--test', action='store_true', help="Test mode: process first N attendees only")
    parser.add_argument('-n', type=int, default=3, help="Number of attendees in test mode (default: 3)")
    parser.add_argument('--workers', type=int, default=150, help="Number of concurrent GPT workers")
    args = parser.parse_args()

    # Load config
    config = ConferenceConfig(args.config)
    print(f"Conference: {config.conference.name}")
    print(f"Organization: {config.organization.name}")

    # Load scoring prompt
    system_prompt = config.load_scoring_prompt()
    print(f"Scoring prompt: {len(system_prompt)} chars")

    # Build dynamic Pydantic model from config partnership types
    partnership_enum = build_partnership_enum(config)
    triage_model = build_triage_model(partnership_enum)

    # Load attendee data
    print(f"\nLoading attendee data from {config.data_paths.warm_leads}...")
    with open(config.data_paths.warm_leads) as f:
        attendees = json.load(f)

    # Filter out primary user (don't score yourself)
    prefix = config.conference.field_prefix
    primary_first = config.users.primary.name.lower()
    primary_last = config.users.primary.full_name.split()[-1].lower() if config.users.primary.full_name else ""
    attendees = [a for a in attendees if not (
        a.get(f'{prefix}_firstname', '').lower() == primary_first and
        a.get(f'{prefix}_lastname', '').lower() == primary_last
    )]
    print(f"  {len(attendees)} attendees (excluding {config.users.primary.full_name})")

    # Merge LinkedIn profiles if available
    if config.data_paths.linkedin_profiles:
        print("Loading LinkedIn enrichment data...")
        try:
            with open(config.data_paths.linkedin_profiles) as f:
                li_profiles = json.load(f)
            print(f"  {len(li_profiles)} LinkedIn profiles loaded")

            li_lookup = {}
            for p in li_profiles:
                li_url = p.get('linkedinUrl', p.get('url', ''))
                if li_url:
                    username = li_url.rstrip('/').split('/')[-1].lower()
                    li_lookup[username] = p

            merged = 0
            for a in attendees:
                ted_li = a.get(f'{prefix}_linkedin', '').strip().lower().rstrip('/')
                if ted_li and ted_li in li_lookup:
                    a['linkedin_enrichment'] = li_lookup[ted_li]
                    merged += 1
            print(f"  Merged {merged} LinkedIn profiles into attendee data")
        except FileNotFoundError:
            print("  No LinkedIn profiles file found, proceeding without")

    if args.test:
        attendees = attendees[:args.n]
        print(f"  TEST MODE: {len(attendees)} attendees")

    # Run GPT triage
    client = OpenAI(api_key=os.environ['OPENAI_APIKEY'])
    print(f"\nRunning GPT triage with {args.workers} workers...")
    results = []
    total = len(attendees)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                score_attendee, a, i, total,
                client, system_prompt, triage_model, config
            ): a
            for i, a in enumerate(attendees)
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    # Sort by score descending
    results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

    # Stats
    errors = sum(1 for r in results if r.get('error'))
    scored = [r for r in results if not r.get('error')]

    print(f"\n=== Triage Results ===")
    print(f"Total scored: {len(scored)}, Errors: {errors}")

    # Distribution
    bins = [(80, 100, "Strong (80-100)"), (60, 79, "Moderate (60-79)"),
            (40, 59, "Loose (40-59)"), (0, 39, "Minimal (0-39)")]
    for lo, hi, label in bins:
        count = sum(1 for r in scored if lo <= r['relevance_score'] <= hi)
        print(f"  {label}: {count}")

    # Partnership type distribution
    print("\nPartnership types:")
    types = Counter(r['partnership_type'] for r in scored)
    for t, c in types.most_common():
        print(f"  {t}: {c}")

    # Top results
    show = min(20, len(scored))
    if show:
        print(f"\nTop {show} by relevance:")
        for r in scored[:show]:
            print(f"  {r['relevance_score']:3d} | {r.get(f'{prefix}_name', ''):30s} | "
                  f"{r['partnership_type']:20s} | {r['reasoning'][:60]}")

    # Save
    output_path = config.data_paths.triage_results
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} results to {output_path}")


if __name__ == '__main__':
    main()
