#!/usr/bin/env python3
"""
Network Intelligence — LLM Structured Tagging via GPT-5 mini

Processes all contacts through GPT-5 mini structured output to generate:
- Relationship proximity scores (0-100)
- Giving capacity estimates
- Topical affinity tags
- Kindora sales fit scores
- Outreach context and personalization hooks

Usage:
  python scripts/intelligence/tag_contacts_gpt5m.py --test        # Process 10 contacts
  python scripts/intelligence/tag_contacts_gpt5m.py --test -n 5   # Process 5 contacts
  python scripts/intelligence/tag_contacts_gpt5m.py --dry-run     # Assemble prompts only
  python scripts/intelligence/tag_contacts_gpt5m.py               # Full run (all contacts)
  python scripts/intelligence/tag_contacts_gpt5m.py --force       # Re-tag already-tagged contacts
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from pydantic import BaseModel, Field
from supabase import create_client, Client

load_dotenv()

# ── Pydantic Output Schema ─────────────────────────────────────────────

class ProximityTier(str, Enum):
    inner_circle = "inner_circle"
    close = "close"
    warm = "warm"
    familiar = "familiar"
    acquaintance = "acquaintance"
    distant = "distant"

class CapacityTier(str, Enum):
    major_donor = "major_donor"
    mid_level = "mid_level"
    grassroots = "grassroots"
    unknown = "unknown"

class ProspectType(str, Enum):
    enterprise_buyer = "enterprise_buyer"
    champion = "champion"
    influencer = "influencer"
    not_relevant = "not_relevant"

class FitLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"
    none = "none"

class TopicStrength(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class BestApproach(str, Enum):
    personal_email = "personal_email"
    linkedin_message = "linkedin_message"
    intro_via_mutual = "intro_via_mutual"

class SharedEmployer(BaseModel):
    org: str
    overlap_years: str = ""
    relationship: str = ""

class SharedSchool(BaseModel):
    school: str
    overlap: str = ""

class RelationshipProximity(BaseModel):
    score: int = Field(ge=0, le=100)
    tier: ProximityTier
    shared_employers: list[SharedEmployer] = []
    shared_schools: list[SharedSchool] = []
    shared_boards: list[str] = []
    shared_volunteering: list[str] = []
    proximity_signals: list[str] = []
    reasoning: str

class GivingCapacity(BaseModel):
    tier: CapacityTier
    score: int = Field(ge=0, le=100)
    signals: list[str] = []
    estimated_range: str = ""
    reasoning: str

class TopicTag(BaseModel):
    topic: str
    strength: TopicStrength
    evidence: str = ""

class TopicalAffinity(BaseModel):
    topics: list[TopicTag] = []
    primary_interests: list[str] = []
    talking_points: list[str] = []

class SalesFit(BaseModel):
    kindora_prospect: bool
    prospect_type: ProspectType
    score: int = Field(ge=0, le=100)
    reasoning: str
    signals: list[str] = []

class OutreachContext(BaseModel):
    outdoorithm_invite_fit: FitLevel
    kindora_pitch_fit: FitLevel
    best_approach: BestApproach
    personalization_hooks: list[str] = []
    suggested_opener: str = ""

class ContactIntelligence(BaseModel):
    relationship_proximity: RelationshipProximity
    giving_capacity: GivingCapacity
    topical_affinity: TopicalAffinity
    sales_fit: SalesFit
    outreach_context: OutreachContext


# ── Justin's Anchor Profile ────────────────────────────────────────────

ANCHOR_PROFILE = """ANCHOR PERSON (Justin Steele):
- Current roles: Co-Founder & CEO at Kindora (AI-powered grant matching for nonprofits, 2025-present), Founder & Fractional CIO at True Steele LLC (2024-present), Co-Founder & Treasurer at Outdoorithm Collective (outdoor equity nonprofit, 2024-present), Co-Founder & CTO at Outdoorithm (outdoor recreation app, 2023-present)
- Previous employers: Google / Google.org (Director, Americas; Racial Justice Lead, ~6 years), Year Up (Deputy Director, PM, Dir Strategy & Ops, ~5 years), Northern Virginia Community College (Adjunct Professor, ~2 years), The Bridgespan Group (Senior Associate Consultant, ~2 years), Bain and Company (Associate Consultant, ~2 years)
- Schools: Harvard Business School (MBA), Harvard Kennedy School (MPA/MPP), University of Virginia (BS Engineering)
- Boards: San Francisco Foundation (Program Chair, Board of Trustees), Outdoorithm Collective (Treasurer, Board of Directors)
- Key interests/topics: Outdoor equity & nature access, AI for social good & public interest technology, Philanthropy & corporate social responsibility, Nonprofit fundraising & grant matching, Racial justice & equity & DEI, Systems change & social innovation, Education & workforce development, Fatherhood & family camping
- LinkedIn: 2,796 connections, 6,061 followers, connected since 2015
- Location: San Francisco Bay Area"""


SYSTEM_PROMPT = """You are a network intelligence analyst. Given an anchor person's profile and a target contact's LinkedIn data, produce a structured analysis.

SCORING GUIDELINES:

Relationship Proximity (0-100):
- 80-100 (inner_circle): Worked together directly, personal relationship
- 60-79 (close): Shared institution with temporal overlap, periodic contact
- 40-59 (warm): Shared institution different era, met through context, or strong shared interests
- 20-39 (familiar): LinkedIn connection, some shared interests or industry
- 10-19 (acquaintance): Connected, no meaningful overlap
- 0-9 (distant): No overlap or signals

Key signals for proximity: Shared employers (especially same time period), shared schools (especially same years), shared boards/volunteer orgs, shared industry/community, LinkedIn connection tenure (earlier = potentially closer), shared location.

Giving Capacity (0-100):
- 70-100 (major_donor, $10K+): C-suite, founders, senior leaders at large companies, board seats at foundations
- 40-69 (mid_level, $1K-$10K): Directors, senior managers, experienced professionals
- 15-39 (grassroots, $100-$1K): Individual contributors, early career
- 0-14 (unknown): Insufficient data

Kindora Sales Fit (0-100):
Kindora is an AI-powered grant matching platform for nonprofits. High-fit prospects work at foundations, manage nonprofit networks, lead grantmaking programs, or influence nonprofit technology purchasing.

Topical Affinity:
Use these controlled topic tags when applicable: outdoor_equity, nature_recreation, environmental_justice, philanthropy, grantmaking, nonprofit_leadership, ai_technology, social_impact_tech, public_interest_tech, corporate_social_responsibility, esg, racial_justice, dei, equity, education, workforce_development, family_youth, parenting, social_enterprise, impact_investing, community_development, urban_equity, climate, health_equity, arts_culture

Outreach Context:
- outdoorithm_invite_fit: Would this person attend an Outdoorithm Collective outdoor equity fundraiser?
- kindora_pitch_fit: Is this person relevant for a Kindora enterprise sales conversation?
- personalization_hooks: Specific, actionable hooks for a warm outreach message (reference shared experiences, mutual interests, recent career moves)
- suggested_opener: A natural, brief opening line Justin could use

Be realistic with scores. Not everyone is a close contact — most LinkedIn connections are acquaintances or distant. Be generous with topical tags and outreach hooks — even distant contacts deserve useful personalization."""


def parse_jsonb(val) -> object:
    """Parse a JSONB field that may be a string or already parsed."""
    if val is None:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            return val
    return val


def build_contact_context(contact: dict) -> str:
    """Assemble the per-contact context document for the LLM."""
    parts = []
    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    parts.append(f"TARGET CONTACT: {name}")

    if contact.get("headline"):
        parts.append(f"Headline: {contact['headline']}")
    if contact.get("company") or contact.get("position"):
        parts.append(f"Current: {contact.get('position', '?')} at {contact.get('company', '?')}")
    if contact.get("summary"):
        parts.append(f"Summary: {contact['summary']}")
    if contact.get("connected_on"):
        parts.append(f"LinkedIn connected: {contact['connected_on']}")
    if contact.get("city") or contact.get("state"):
        loc = ", ".join(filter(None, [contact.get("city"), contact.get("state")]))
        parts.append(f"Location: {loc}")

    # JSONB enrichment fields
    employment = parse_jsonb(contact.get("enrich_employment"))
    if employment:
        parts.append(f"Employment History: {json.dumps(employment)}")

    education = parse_jsonb(contact.get("enrich_education"))
    if education:
        parts.append(f"Education: {json.dumps(education)}")

    skills = parse_jsonb(contact.get("enrich_skills_detailed"))
    if skills:
        skill_names = []
        for s in (skills if isinstance(skills, list) else []):
            if isinstance(s, dict):
                skill_names.append(s.get("skill_name", ""))
            elif isinstance(s, str):
                skill_names.append(s)
        if skill_names:
            parts.append(f"Skills: {', '.join(skill_names[:30])}")

    volunteering = parse_jsonb(contact.get("enrich_volunteering"))
    if volunteering:
        parts.append(f"Volunteering: {json.dumps(volunteering)}")

    certifications = parse_jsonb(contact.get("enrich_certifications"))
    if certifications:
        # Filter out empty certifications
        certs = [c for c in certifications if isinstance(c, dict) and c.get("name")]
        if certs:
            parts.append(f"Certifications: {json.dumps(certs)}")

    publications = parse_jsonb(contact.get("enrich_publications"))
    if publications:
        parts.append(f"Publications: {json.dumps(publications)}")

    honors = parse_jsonb(contact.get("enrich_honors_awards"))
    if honors:
        parts.append(f"Awards: {json.dumps(honors)}")

    return "\n".join(parts)


# ── Main Tagger Class ──────────────────────────────────────────────────

class ContactTagger:
    MODEL = "gpt-5-mini"
    SELECT_COLS = (
        "id, first_name, last_name, headline, summary, company, position, "
        "connected_on, city, state, ai_tags, "
        "enrich_employment, enrich_education, enrich_skills_detailed, "
        "enrich_volunteering, enrich_certifications, enrich_publications, "
        "enrich_honors_awards"
    )

    def __init__(self, test_mode=False, dry_run=False, force=False, workers=10, test_count=10):
        self.test_mode = test_mode
        self.dry_run = dry_run
        self.force = force
        self.workers = workers
        self.test_count = test_count
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.stats = {
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        openai_key = os.environ.get("OPENAI_APIKEY")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        if not openai_key and not self.dry_run:
            print("ERROR: Missing OPENAI_APIKEY")
            return False

        self.supabase = create_client(url, key)
        if not self.dry_run:
            self.openai = OpenAI(api_key=openai_key)
        print(f"Connected to Supabase{' and OpenAI' if not self.dry_run else ' (dry-run, no OpenAI)'}")
        return True

    def get_contacts(self) -> list[dict]:
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                self.supabase.table("contacts")
                .select(self.SELECT_COLS)
                .order("id")
                .range(offset, offset + page_size - 1)
            )

            if not self.force:
                query = query.is_("ai_tags", "null")

            response = query.execute()
            page = response.data
            if not page:
                break

            all_contacts.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        if self.test_mode:
            all_contacts = all_contacts[:self.test_count]

        return all_contacts

    def tag_contact(self, contact: dict) -> Optional[ContactIntelligence]:
        """Call GPT-5 mini to tag a single contact. Returns parsed output or None on error."""
        contact_context = build_contact_context(contact)
        user_message = f"{ANCHOR_PROFILE}\n\n{contact_context}"

        if self.dry_run:
            name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
            token_est = len(user_message) // 4
            print(f"  [DRY-RUN] {name}: ~{token_est} input tokens")
            return None

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions=SYSTEM_PROMPT,
                    input=user_message,
                    text_format=ContactIntelligence,
                )

                # Track token usage
                if resp.usage:
                    self.stats["input_tokens"] += resp.usage.input_tokens
                    self.stats["output_tokens"] += resp.usage.output_tokens

                if resp.output_parsed:
                    return resp.output_parsed

                print(f"    Warning: No parsed output, refusal={getattr(resp, 'refusal', None)}")
                return None

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
            except Exception as e:
                print(f"    Unexpected error: {e}")
                return None

        return None

    def save_tags(self, contact_id: int, result: ContactIntelligence) -> bool:
        """Save the LLM output to Supabase."""
        tags_json = result.model_dump(mode="json")
        updates = {
            "ai_tags": tags_json,
            "ai_tags_generated_at": datetime.now(timezone.utc).isoformat(),
            "ai_tags_model": self.MODEL,
            # Denormalized scores
            "ai_proximity_score": result.relationship_proximity.score,
            "ai_proximity_tier": result.relationship_proximity.tier.value,
            "ai_capacity_score": result.giving_capacity.score,
            "ai_capacity_tier": result.giving_capacity.tier.value,
            "ai_kindora_prospect_score": result.sales_fit.score,
            "ai_kindora_prospect_type": result.sales_fit.prospect_type.value,
            "ai_outdoorithm_fit": result.outreach_context.outdoorithm_invite_fit.value,
        }

        try:
            self.supabase.table("contacts").update(updates).eq("id", contact_id).execute()
            return True
        except Exception as e:
            print(f"    DB error for id={contact_id}: {e}")
            return False

    def process_contact(self, contact: dict) -> bool:
        """Process a single contact: tag + save. Returns True on success."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        contact_id = contact["id"]

        result = self.tag_contact(contact)
        if result is None:
            if not self.dry_run:
                self.stats["errors"] += 1
            return False

        if self.save_tags(contact_id, result):
            prox = result.relationship_proximity
            cap = result.giving_capacity
            print(f"  [{contact_id}] {name}: proximity={prox.score} ({prox.tier.value}), "
                  f"capacity={cap.score} ({cap.tier.value}), "
                  f"kindora={result.sales_fit.score}")
            self.stats["processed"] += 1
            return True
        else:
            self.stats["errors"] += 1
            return False

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()
        contacts = self.get_contacts()
        total = len(contacts)
        print(f"Found {total} contacts to process")

        if total == 0:
            print("Nothing to do — all contacts already tagged (use --force to re-tag)")
            return True

        if self.dry_run:
            print(f"\n--- DRY RUN: Assembling prompts for {total} contacts ---\n")
            total_tokens = 0
            for c in contacts:
                ctx = build_contact_context(c)
                user_msg = f"{ANCHOR_PROFILE}\n\n{ctx}"
                tokens = len(user_msg) // 4
                total_tokens += tokens
                name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
                print(f"  [{c['id']}] {name}: ~{tokens} input tokens")
            print(f"\n--- DRY RUN COMPLETE ---")
            print(f"  Total contacts: {total}")
            print(f"  Est. input tokens: ~{total_tokens:,}")
            print(f"  Est. output tokens: ~{total * 800:,}")
            input_cost = total_tokens * 0.15 / 1_000_000
            output_cost = total * 800 * 0.60 / 1_000_000
            print(f"  Est. cost: ~${input_cost + output_cost:.2f} "
                  f"(input: ${input_cost:.2f}, output: ${output_cost:.2f})")
            return True

        if self.test_mode:
            print(f"\n--- TEST MODE: Processing {total} contacts sequentially ---\n")
            for c in contacts:
                self.process_contact(c)
        else:
            print(f"\n--- Processing {total} contacts with {self.workers} workers ---\n")
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = {}
                for c in contacts:
                    future = executor.submit(self.process_contact, c)
                    futures[future] = c["id"]

                done_count = 0
                for future in as_completed(futures):
                    done_count += 1
                    try:
                        future.result()
                    except Exception as e:
                        cid = futures[future]
                        print(f"  [ERROR] Contact {cid}: {e}")
                        self.stats["errors"] += 1

                    if done_count % 50 == 0 or done_count == total:
                        elapsed = time.time() - start_time
                        rate = done_count / elapsed if elapsed > 0 else 0
                        print(f"\n--- Progress: {done_count}/{total} "
                              f"({self.stats['processed']} tagged, {self.stats['errors']} errors) "
                              f"[{rate:.1f} contacts/sec, {elapsed:.0f}s elapsed] ---\n")

        elapsed = time.time() - start_time
        self.print_summary(elapsed)
        return self.stats["errors"] < total * 0.05  # Success if <5% errors

    def print_summary(self, elapsed: float):
        s = self.stats
        input_cost = s["input_tokens"] * 0.15 / 1_000_000
        output_cost = s["output_tokens"] * 0.60 / 1_000_000
        total_cost = input_cost + output_cost

        print("\n" + "=" * 60)
        print("TAGGING SUMMARY")
        print("=" * 60)
        print(f"  Contacts tagged:    {s['processed']}")
        print(f"  Contacts skipped:   {s['skipped']}")
        print(f"  Errors:             {s['errors']}")
        print(f"  Input tokens:       {s['input_tokens']:,}")
        print(f"  Output tokens:      {s['output_tokens']:,}")
        print(f"  Cost:               ${total_cost:.2f} (input: ${input_cost:.2f}, output: ${output_cost:.2f})")
        print(f"  Time elapsed:       {elapsed:.1f}s")
        if s["processed"] > 0:
            print(f"  Avg time/contact:   {elapsed / s['processed']:.2f}s")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Tag contacts with GPT-5 mini structured output"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only N contacts for validation (default: 10)")
    parser.add_argument("--count", "-n", type=int, default=10,
                        help="Number of contacts to process in test mode (default: 10)")
    parser.add_argument("--dry-run", "-d", action="store_true",
                        help="Assemble prompts but don't call OpenAI")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-tag contacts that already have ai_tags")
    parser.add_argument("--workers", "-w", type=int, default=10,
                        help="Number of concurrent workers (default: 10)")
    args = parser.parse_args()

    tagger = ContactTagger(
        test_mode=args.test,
        dry_run=args.dry_run,
        force=args.force,
        workers=args.workers,
        test_count=args.count,
    )
    success = tagger.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
