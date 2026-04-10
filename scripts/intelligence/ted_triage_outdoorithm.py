#!/usr/bin/env python3
"""
TED 2026 — GPT Triage for Outdoorithm Networking Brief

Scores all TED attendees on Outdoorithm relevance using GPT-5 mini structured output.
Merges LinkedIn enrichment data and DB matches for maximum signal.

Usage:
  python scripts/intelligence/ted_triage_outdoorithm.py             # Full run
  python scripts/intelligence/ted_triage_outdoorithm.py --test      # Test with 10
  python scripts/intelligence/ted_triage_outdoorithm.py --test -n 5 # Test with 5
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from pydantic import BaseModel, Field

load_dotenv('/Users/Justin/Code/TrueSteele/contacts/.env')

# ── Pydantic Output Schema ─────────────────────────────────────────────

class PartnershipType(str, Enum):
    funding = "funding"
    media_storytelling = "media_storytelling"
    programmatic = "programmatic"
    multiple = "multiple"
    unlikely = "unlikely"

class OutdoorithmTriage(BaseModel):
    relevance_score: int = Field(ge=0, le=100, description="0-100 score for Outdoorithm fit")
    partnership_type: PartnershipType = Field(description="Primary partnership type")
    partnership_types: list[str] = Field(default_factory=list, description="All applicable types: funding, media_storytelling, programmatic")
    reasoning: str = Field(description="1-2 sentence explanation of why this person matters (or doesn't) for Outdoorithm")
    conversation_hook: str = Field(description="What Sally should mention when meeting them, based on their profile")
    key_signal: str = Field(default="", description="The strongest signal in their profile for Outdoorithm alignment")

# ── System Prompt ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are scoring TED 2026 attendees for their potential partnership value with Outdoorithm Collective, a nonprofit that transforms access to public lands by creating community-driven camping experiences for diverse urban families.

ABOUT OUTDOORITHM COLLECTIVE:
- Mission: Transform public lands into spaces of belonging for historically excluded communities
- Model: 48-hour guided group camping trips where families across class/race lines build authentic connections
- Theory of change: Cross-class friendships formed in nature are the #1 predictor of economic mobility
- Based in Oakland, CA; serves families throughout California; plans national expansion
- Co-founded by Sally Steele (CEO, nonprofit executive, ordained faith leader, City Hope SF) and Justin Steele (former Google.org Director, HBS/HKS)
- Current: Running "Come Alive 2026" fundraising campaign ($120K goal, $84K raised)
- 94% BIPOC participants; ~100 families served; 107 camping trips as a family
- Key concepts: bridging (john powell), outdoor equity, social cohesion, collective responsibility, belonging

ABOUT SALLY STEELE (who will be networking):
- Co-Founder & CEO of Outdoorithm Collective
- Former Co-Executive Director of City Hope San Francisco ($1.9M budget, faith-based community org)
- Ordained minister with deep roots in ministry, faith-based leadership, and pastoral care
- Black woman, mother of two, Oakland resident
- Passionate about family wellness, nature as healing, racial reconciliation, and belonging
- Background in community organizing, church leadership, women's ministry, and social justice
- Her personal story: discovered camping transformed her own family and wanted other families to have that
- Her faith informs her leadership: she sees the campfire as sacred space, nature as a place where people encounter something bigger than themselves
- At TED as an attendee representing Outdoorithm Collective

SALLY-SPECIFIC CONNECTION SIGNALS (score higher if present):
- Faith leaders, chaplains, ministers, pastors, or anyone working at the intersection of faith and social justice
- Family wellness, parenting, family strengthening, intergenerational healing
- Black women's leadership, Black family wellness, racial healing
- Belonging, loneliness, social isolation, community building
- Nature-based healing, outdoor education, environmental justice, public lands access
- Embodied practices: yoga, meditation, wellness retreats, movement-based healing
- Women of faith who lead organizations

PARTNERSHIP TYPES TO SCORE:
1. FUNDING: Philanthropists, foundation leaders, impact investors, CSR/ESG leaders, family offices, donor-advised fund holders who might fund outdoor equity, youth development, social cohesion, or BIPOC-serving programs
2. MEDIA & STORYTELLING: Filmmakers, journalists, content creators, media executives, authors, podcasters who could amplify the Outdoorithm story — especially those focused on nature, family, equity, belonging, or social impact
3. PROGRAMMATIC: Leaders of outdoor brands, national parks, public lands agencies, youth-serving nonprofits, community organizations, wellness brands, education leaders, or tech companies who could partner on trips, gear, curriculum, or scaling the model

SCORING GUIDANCE:
- 80-100: Strong, direct alignment — their work/passion directly overlaps with outdoor equity, family wellness, social cohesion, BIPOC communities, or nature access. Clear partnership path.
- 60-79: Moderate alignment — adjacent space (e.g., education equity, health equity, community building, environmental justice). Would benefit from an intro but need cultivation.
- 40-59: Loose alignment — general social impact, philanthropy, or nature interest but no direct connection to Outdoorithm's specific work.
- 0-39: Minimal alignment — tech/business focus with no apparent connection to nature, families, equity, or community.

Be generous with scoring — TED attendees tend to be engaged, curious people. If someone shows ANY interest in nature, families, community, equity, wellness, or belonging, score them at least 50. We'd rather include someone who turns out to be a loose fit than miss a gem.

For conversation_hook: Write a specific, natural opener Sally could use. Reference something from their bio/interests. Keep it warm and authentic, not salesy."""

# ── GPT Call ────────────────────────────────────────────────────────────

client = OpenAI(api_key=os.environ['OPENAI_APIKEY'])

def build_user_prompt(attendee: dict) -> str:
    """Build the user prompt from all available attendee data."""
    parts = []

    name = f"{attendee.get('ted_firstname', '')} {attendee.get('ted_lastname', '')}".strip()
    parts.append(f"NAME: {name}")

    if attendee.get('ted_title'):
        parts.append(f"TITLE: {attendee['ted_title']}")
    if attendee.get('ted_org'):
        parts.append(f"ORGANIZATION: {attendee['ted_org']}")
    if attendee.get('ted_city') or attendee.get('ted_country'):
        loc = f"{attendee.get('ted_city', '')}, {attendee.get('ted_country', '')}".strip(', ')
        parts.append(f"LOCATION: {loc}")

    if attendee.get('ted_is_speaker'):
        parts.append("ROLE: TED Speaker")
    if attendee.get('ted_is_fellow'):
        parts.append("ROLE: TED Fellow")

    if attendee.get('ted_about'):
        parts.append(f"BIO: {attendee['ted_about']}")
    if attendee.get('ted_idea'):
        parts.append(f"IDEA WORTH SPREADING: {attendee['ted_idea']}")
    if attendee.get('ted_passion'):
        parts.append(f"PASSIONS: {attendee['ted_passion']}")
    if attendee.get('ted_ask_me_about'):
        parts.append(f"ASK ME ABOUT: {attendee['ted_ask_me_about']}")

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

    # DB enrichment data (from existing contacts)
    if attendee.get('db_headline'):
        parts.append(f"DB HEADLINE: {attendee['db_headline']}")
    if attendee.get('db_summary') and not li:
        parts.append(f"DB SUMMARY: {attendee['db_summary'][:300]}")
    if attendee.get('db_outdoorithm_fit'):
        parts.append(f"EXISTING OUTDOORITHM FIT SCORE: {attendee['db_outdoorithm_fit']}")

    # Warm lead context
    flags = []
    if attendee.get('justin_connection'):
        flags.append("Justin's LinkedIn connection")
    if attendee.get('sally_connection'):
        flags.append("Sally's LinkedIn connection")
    if attendee.get('db_closeness') and attendee['db_closeness'] != 'no_history':
        flags.append(f"Relationship: {attendee['db_closeness']}")
    if flags:
        parts.append(f"WARM LEAD: {', '.join(flags)}")

    return '\n'.join(parts)


def score_attendee(attendee: dict, idx: int, total: int) -> dict:
    """Score a single attendee with GPT-5 mini."""
    user_prompt = build_user_prompt(attendee)

    for attempt in range(3):
        try:
            response = client.beta.chat.completions.parse(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=OutdoorithmTriage,
            )
            result = response.choices[0].message.parsed
            if (idx + 1) % 100 == 0 or idx < 5:
                print(f"  [{idx+1}/{total}] {attendee.get('ted_firstname','')} {attendee.get('ted_lastname','')}: "
                      f"score={result.relevance_score}, type={result.partnership_type.value}")

            return {
                'ted_id': attendee['ted_id'],
                'ted_name': attendee.get('ted_name', ''),
                'relevance_score': result.relevance_score,
                'partnership_type': result.partnership_type.value,
                'partnership_types': result.partnership_types,
                'reasoning': result.reasoning,
                'conversation_hook': result.conversation_hook,
                'key_signal': result.key_signal,
            }
        except RateLimitError:
            import time
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == 2:
                print(f"  ERROR [{idx+1}/{total}] {attendee.get('ted_name','')}: {e}")
                return {
                    'ted_id': attendee['ted_id'],
                    'ted_name': attendee.get('ted_name', ''),
                    'relevance_score': 0,
                    'partnership_type': 'unlikely',
                    'partnership_types': [],
                    'reasoning': f'Error: {str(e)[:100]}',
                    'conversation_hook': '',
                    'key_signal': '',
                    'error': True,
                }
            import time
            time.sleep(1)

    return {'ted_id': attendee['ted_id'], 'relevance_score': 0, 'error': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true')
    parser.add_argument('-n', type=int, default=10)
    parser.add_argument('--workers', type=int, default=150)
    args = parser.parse_args()

    # Load warm lead data
    print("Loading attendee data...")
    attendees = json.load(open('/tmp/ted_warm_leads.json'))

    # Filter out Sally Steele herself
    attendees = [a for a in attendees if not (
        a.get('ted_firstname', '').lower() == 'sally' and
        a.get('ted_lastname', '').lower() == 'steele'
    )]
    print(f"  {len(attendees)} attendees (excluding Sally)")

    # Load LinkedIn profiles and merge
    print("Loading LinkedIn enrichment data...")
    try:
        li_profiles = json.load(open('/tmp/ted_linkedin_profiles.json'))
        print(f"  {len(li_profiles)} LinkedIn profiles loaded")

        # Build lookup by LinkedIn username
        li_lookup = {}
        for p in li_profiles:
            li_url = p.get('linkedinUrl', p.get('url', ''))
            if li_url:
                # Extract username from URL
                username = li_url.rstrip('/').split('/')[-1].lower()
                li_lookup[username] = p

        # Merge into attendees
        merged = 0
        for a in attendees:
            ted_li = a.get('ted_linkedin', '').strip().lower().rstrip('/')
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
    print(f"\nRunning GPT triage with {args.workers} workers...")
    results = []
    total = len(attendees)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(score_attendee, a, i, total): a
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
    from collections import Counter
    types = Counter(r['partnership_type'] for r in scored)
    for t, c in types.most_common():
        print(f"  {t}: {c}")

    # Top 20
    print(f"\nTop 20 by relevance:")
    for r in scored[:20]:
        print(f"  {r['relevance_score']:3d} | {r['ted_name']:30s} | {r['partnership_type']:20s} | {r['reasoning'][:60]}")

    # Save
    with open('/tmp/ted_triage_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} results to /tmp/ted_triage_results.json")


if __name__ == '__main__':
    main()
