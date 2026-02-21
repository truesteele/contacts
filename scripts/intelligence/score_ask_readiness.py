#!/usr/bin/env python3
"""
Network Intelligence — Ask-Readiness Scoring (Donor Psychology)

Uses GPT-5 mini with a deep donor psychology prompt to assess each contact's
ask-readiness for a specific fundraising/outreach goal. Produces per-contact
reasoning that powers the Network Intelligence search and ranking system.

The goal is parameterized — can score for 'outdoorithm_fundraising',
'kindora_sales', etc. Results stack in the ask_readiness JSONB column.

Usage:
  python scripts/intelligence/score_ask_readiness.py --test                         # 1 contact
  python scripts/intelligence/score_ask_readiness.py --batch 50                     # 50 contacts
  python scripts/intelligence/score_ask_readiness.py --start-from 100               # Skip first 100
  python scripts/intelligence/score_ask_readiness.py --goal kindora_sales           # Different goal
  python scripts/intelligence/score_ask_readiness.py --force                        # Re-score already scored
  python scripts/intelligence/score_ask_readiness.py                                # Full run (~2,400)
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

class AskTier(str, Enum):
    ready_now = "ready_now"
    cultivate_first = "cultivate_first"
    long_term = "long_term"
    not_a_fit = "not_a_fit"

class RecommendedApproach(str, Enum):
    personal_email = "personal_email"
    phone_call = "phone_call"
    in_person = "in_person"
    linkedin = "linkedin"
    intro_via_mutual = "intro_via_mutual"

class AskTiming(str, Enum):
    now = "now"
    after_cultivation = "after_cultivation"
    after_reconnection = "after_reconnection"
    not_recommended = "not_recommended"

class AskReadinessResult(BaseModel):
    score: int = Field(ge=0, le=100, description="Overall ask-readiness score 0-100")
    tier: AskTier = Field(description="Ask-readiness tier")
    reasoning: str = Field(description="2-3 sentence explanation citing specific evidence")
    recommended_approach: RecommendedApproach
    ask_timing: AskTiming
    cultivation_needed: str = Field(description="What cultivation is needed, or 'None — ready for direct ask'")
    suggested_ask_range: str = Field(description="Dollar range like '$500-$2,000' or 'volunteer/attend first'")
    personalization_angle: str = Field(description="The single strongest personalization hook")
    risk_factors: list[str] = Field(description="Reasons the ask could backfire or damage the relationship")


# ── Goal Definitions ──────────────────────────────────────────────────

GOAL_CONTEXTS = {
    "outdoorithm_fundraising": """GOAL: Outdoorithm Collective Individual Donor Fundraising
Outdoorithm Collective is a 501(c)(3) outdoor equity nonprofit co-founded by Justin.
Mission: Making outdoor recreation accessible to underserved communities through guided
camping expeditions, gear provision, and nature education.
Current state: 49 donors, $30K raised, startup phase seeking founding donor community.""",

    "kindora_sales": """GOAL: Kindora Enterprise Sales
Kindora is an AI-powered grant matching platform for nonprofits, co-founded by Justin as CEO.
Mission: Helping nonprofits find and apply for grants more efficiently using AI.
Target buyers: Foundation program officers, nonprofit executive directors, grantmaking network leaders.
Current state: Early-stage startup seeking enterprise customers and champions.""",
}


# ── System Prompt (Donor Psychology) ───────────────────────────────────

SYSTEM_PROMPT = """You are an expert fundraising psychologist and major gift strategist. You assess individual donor ask-readiness by reasoning deeply about relationship dynamics, behavioral signals, and donor psychology.

You are evaluating contacts in Justin Steele's professional network for a specific fundraising goal. Your job is to determine: how ready is this person to receive a fundraising ask, and what approach would maximize the probability of a gift?

DONOR PSYCHOLOGY FRAMEWORK:

The three pillars of donor readiness are Capacity, Propensity, and Relationship — but they interact in nuanced ways:

1. RELATIONSHIP DEPTH (most important for individual fundraising)
   The #1 predictor of individual giving is trust in the person asking. Warm outreach converts at 10x the rate of cold approaches. Assess:
   - How well does Justin actually know this person? (familiarity_rating: 0=stranger, 1=recognize name, 2=know them, 3=good relationship, 4=close/trusted)
   - Have they communicated recently? Recency and frequency of email contact signals active relationship vs dormant connection
   - Do they share formative experiences? People who worked together, went to school together, or served on boards together share identity-level bonds. Temporal overlap amplifies this — being at Google at the SAME TIME creates a fundamentally different bond than both having worked there in different decades
   - Is there reciprocity history? Prior favors, shared projects, mutual support create giving obligations

2. GIVING CAPACITY
   Financial ability to give. Assess from:
   - Career level and trajectory (C-suite, VP, director, IC)
   - Company size and type (tech exec vs nonprofit staff)
   - Board positions (signal wealth and philanthropic identity)
   - FEC political donations: If someone donated $5,000+ to political campaigns, they demonstrably have disposable income AND willingness to write checks. This is the strongest behavioral signal of capacity — it's not estimated, it's proven.
   - Real estate holdings: Property ownership is a factual wealth indicator. Someone with $2M+ in assessed property value has fundamentally different capacity than a renter. Multiple properties (vacation home, investment properties) signal significant wealth.
   - But capacity WITHOUT relationship is meaningless for individual asks — a billionaire who doesn't know Justin won't give

3. PHILANTHROPIC PROPENSITY
   Likelihood of giving based on values and identity alignment. Key signals:
   - Do they have a philanthropic identity? (board service, volunteer history, nonprofit work)
   - Do they post/talk about causes, equity, giving back?
   - Values alignment with the specific cause (outdoor equity, youth access, environmental justice)
   - Identity-based giving: "people like me give to causes like this" — shared social circles, similar career arcs, peer effects
   - Have they supported similar organizations?

4. PSYCHOLOGICAL READINESS
   Timing and receptivity. Consider:
   - Life stage and transitions (new role = less capacity but possibly more openness; recently retired = more time and philanthropic interest)
   - Recent communication warmth — did the last exchange feel positive, collaborative, friendly?
   - Has Justin already cultivated this relationship, or would the ask come out of nowhere?
   - Would this person feel the ask is authentic coming from Justin, or would it feel transactional?
   - The "warm glow" factor — will giving to this cause make them feel good about themselves?

CRITICAL BEHAVIORAL INSIGHTS:
- Donors who feel like insiders give more. Shared institutional membership creates insider feeling.
- The identifiable victim effect: donors respond to individual stories, not statistics. Contacts who've experienced the outdoors themselves (or have kids) are more likely to empathize.
- Social proof: contacts who know OTHER supporters in Justin's network are more likely to give. Peer clusters matter.
- Loss aversion: framing matters. "Don't miss being part of this founding group" > "Please donate."
- Second-gift psychology: if someone has already given to Outdoorithm or supported Justin's other ventures, they're 2-3x more likely to give again.
- Monthly giving converts best within 30-90 days of first gift or engagement.
- Major donors need 12-18 months of cultivation before a large ask. Mid-level donors need 2-4 touchpoints.

OUTPUT REQUIREMENTS:
Produce a structured assessment with score (0-100), tier, reasoning (citing specific evidence), recommended approach, ask timing, cultivation needed, suggested ask range, personalization angle, and risk factors.

SCORING GUIDANCE:
- 80-100 (ready_now): Close relationship + financial capacity + values alignment + recent positive contact. Justin could call today.
- 60-79 (cultivate_first): Good relationship foundation but needs a touchpoint before asking. Maybe reconnect first, share the mission, then ask.
- 40-59 (long_term): Has capacity and some alignment, but relationship is too thin for a direct ask. Needs multiple cultivation touchpoints.
- 20-39 (long_term): Distant connection or misaligned values. Only worth pursuing if capacity is very high.
- 0-19 (not_a_fit): No relationship, no alignment, or no capacity. Don't waste effort.

Be honest and realistic. Most LinkedIn connections are NOT ready for a fundraising ask. A 2,400-person network might yield 50-100 people who are genuinely ready, 200-300 worth cultivating, and the rest are too distant."""


# ── Select columns ────────────────────────────────────────────────────

SELECT_COLS = (
    "id, first_name, last_name, headline, summary, company, position, "
    "connected_on, city, state, familiarity_rating, "
    "ai_tags, shared_institutions, "
    "ai_capacity_tier, ai_capacity_score, ai_outdoorithm_fit, "
    "fec_donations, real_estate_data, "
    "comms_last_date, comms_thread_count, communication_history, "
    "enrich_employment, enrich_education, enrich_volunteering"
)


def parse_jsonb(val) -> object:
    """Parse a JSONB field that may be a string or already parsed."""
    if val is None:
        return None
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            # Handle double-encoded JSON
            if isinstance(parsed, str):
                try:
                    return json.loads(parsed)
                except (json.JSONDecodeError, ValueError):
                    return parsed
            return parsed
        except (json.JSONDecodeError, ValueError):
            return val
    return val


def summarize_fec(fec_data: dict) -> str:
    """Summarize FEC donations into a readable string."""
    if not fec_data:
        return "No FEC records found"
    total = fec_data.get("total_amount", 0)
    count = fec_data.get("donation_count", 0)
    max_single = fec_data.get("max_single", 0)
    cycles = fec_data.get("cycles", [])
    employer = fec_data.get("employer_from_fec", "")
    occupation = fec_data.get("occupation_from_fec", "")

    parts = [f"${total:,.0f} total across {count} donations"]
    if max_single:
        parts.append(f"max single donation: ${max_single:,.0f}")
    if cycles:
        parts.append(f"active cycles: {', '.join(str(c) for c in cycles)}")
    if employer:
        parts.append(f"employer (FEC): {employer}")
    if occupation:
        parts.append(f"occupation (FEC): {occupation}")

    # Top recent donations
    recent = fec_data.get("recent_donations", [])
    if recent:
        top3 = recent[:3]
        donation_strs = [
            f"${d.get('amount', 0):,.0f} to {d.get('committee', '?')} ({d.get('date', '?')})"
            for d in top3
        ]
        parts.append(f"recent: {'; '.join(donation_strs)}")

    return ". ".join(parts)


def summarize_real_estate(re_data: dict) -> str:
    """Summarize real estate data into a readable string."""
    if not re_data:
        return "No property records found"
    source = re_data.get("source", "")
    if source in ("skip_trace_rejected", "skip_trace_failed"):
        return "No property records found"

    parts = []
    address = re_data.get("address", "")
    if address:
        parts.append(f"Property: {address}")
    zestimate = re_data.get("zestimate")
    if zestimate:
        parts.append(f"Zestimate: ${zestimate:,.0f}")
    rent = re_data.get("rent_zestimate")
    if rent:
        parts.append(f"Rent Zestimate: ${rent:,.0f}/mo")
    ptype = re_data.get("property_type", "")
    beds = re_data.get("beds")
    baths = re_data.get("baths")
    sqft = re_data.get("sqft")
    year = re_data.get("year_built")
    details = []
    if ptype:
        details.append(ptype)
    if beds and baths:
        details.append(f"{beds}bd/{baths}ba")
    if sqft:
        details.append(f"{sqft:,} sqft")
    if year:
        details.append(f"built {year}")
    if details:
        parts.append(", ".join(details))

    return ". ".join(parts)


def summarize_comms(contact: dict) -> str:
    """Summarize communication history into a readable string."""
    last_date = contact.get("comms_last_date")
    thread_count = contact.get("comms_thread_count", 0)

    if not last_date and not thread_count:
        return "No email history"

    parts = []
    if last_date:
        parts.append(f"Last contact: {last_date}")
    if thread_count:
        parts.append(f"Total threads: {thread_count}")

    # Extract relationship summary and recent threads from communication_history
    comms = parse_jsonb(contact.get("communication_history"))
    if comms and isinstance(comms, dict):
        summary = comms.get("relationship_summary", "")
        if summary:
            parts.append(f"Relationship summary: {summary}")

        # Recent thread subjects
        accounts = comms.get("accounts", {})
        recent_threads = []
        for acct_data in (accounts.values() if isinstance(accounts, dict) else []):
            if isinstance(acct_data, dict):
                threads = acct_data.get("threads", [])
                for t in (threads if isinstance(threads, list) else []):
                    if isinstance(t, dict):
                        subject = t.get("subject", "")
                        date = t.get("last_date", t.get("date", ""))
                        if subject:
                            recent_threads.append((date, subject))

        if recent_threads:
            recent_threads.sort(reverse=True)
            top3 = recent_threads[:3]
            thread_strs = [f'"{subj}" ({date})' for date, subj in top3]
            parts.append(f"Recent threads: {'; '.join(thread_strs)}")

    return "\n  ".join(parts)


def summarize_shared_institutions(institutions) -> str:
    """Summarize structured institutional overlap."""
    if not institutions:
        return "No structured overlap data"
    if not isinstance(institutions, list):
        return "No structured overlap data"

    parts = []
    for inst in institutions:
        if not isinstance(inst, dict):
            continue
        name = inst.get("name", "?")
        itype = inst.get("type", "")
        overlap = inst.get("overlap", "")
        temporal = inst.get("temporal_overlap", False)
        depth = inst.get("depth", "")
        justin_period = inst.get("justin_period", "")
        contact_period = inst.get("contact_period", "")
        notes = inst.get("notes", "")

        line = f"{name} ({itype})"
        if justin_period and contact_period:
            line += f" — Justin: {justin_period}, Contact: {contact_period}"
        if temporal:
            line += " [TEMPORAL OVERLAP]"
        if depth:
            line += f" [{depth}]"
        if notes:
            line += f" — {notes}"
        parts.append(f"  - {line}")

    return "\n".join(parts) if parts else "No structured overlap data"


def get_topics_and_philanthropy(ai_tags: dict) -> tuple[str, str]:
    """Extract topics of interest and philanthropic signals from ai_tags."""
    topics_str = "None identified"
    philanthropy_str = "None identified"

    if not ai_tags:
        return topics_str, philanthropy_str

    # Topics
    ta = ai_tags.get("topical_affinity", {})
    topics = ta.get("topics", [])
    if topics:
        topic_strs = []
        for t in topics:
            if isinstance(t, dict):
                topic_strs.append(f"{t.get('topic', '?')} ({t.get('strength', '?')})")
            elif isinstance(t, str):
                topic_strs.append(t)
        if topic_strs:
            topics_str = ", ".join(topic_strs)

    # Philanthropic signals from outreach context + volunteering
    signals = []
    oc = ai_tags.get("outreach_context", {})
    if oc.get("outdoorithm_invite_fit") in ("high", "medium"):
        signals.append(f"Outdoorithm invite fit: {oc['outdoorithm_invite_fit']}")

    rp = ai_tags.get("relationship_proximity", {})
    boards = rp.get("shared_boards", [])
    if boards:
        signals.append(f"Shared boards: {', '.join(boards)}")
    volunteering = rp.get("shared_volunteering", [])
    if volunteering:
        signals.append(f"Shared volunteering: {', '.join(volunteering)}")

    gc = ai_tags.get("giving_capacity", {})
    cap_signals = gc.get("signals", [])
    philanthropic_signals = [s for s in cap_signals if any(
        kw in s.lower() for kw in ["board", "philanthrop", "nonprofit", "foundation", "donor", "volunteer"]
    )]
    if philanthropic_signals:
        signals.extend(philanthropic_signals)

    if signals:
        philanthropy_str = "; ".join(signals)

    return topics_str, philanthropy_str


def build_contact_context(contact: dict, goal: str) -> str:
    """Assemble the full per-contact context for the donor psychology prompt."""
    parts = []

    # Goal context
    goal_context = GOAL_CONTEXTS.get(goal, f"GOAL: {goal}")
    parts.append(goal_context)
    parts.append("")

    # Contact basics
    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    parts.append(f"CONTACT: {name}")
    familiarity = contact.get("familiarity_rating", 0) or 0
    parts.append(f"Familiarity Rating: {familiarity}/4 (Justin's personal assessment)")

    if contact.get("position") or contact.get("company"):
        parts.append(f"Current Role: {contact.get('position', '?')} at {contact.get('company', '?')}")
    if contact.get("headline"):
        parts.append(f"Headline: {contact['headline']}")
    if contact.get("city") or contact.get("state"):
        loc = ", ".join(filter(None, [contact.get("city"), contact.get("state")]))
        parts.append(f"Location: {loc}")
    parts.append("")

    # Shared institutions (structured)
    institutions = parse_jsonb(contact.get("shared_institutions"))
    inst_summary = summarize_shared_institutions(institutions)
    parts.append(f"Shared Institutions:\n{inst_summary}")

    # AI tags context
    ai_tags = parse_jsonb(contact.get("ai_tags")) or {}

    # If no structured overlap, fall back to ai_tags overlap
    if not institutions or not isinstance(institutions, list) or len(institutions) == 0:
        rp = ai_tags.get("relationship_proximity", {})
        fallback_parts = []
        for emp in (rp.get("shared_employers") or []):
            if isinstance(emp, dict):
                fallback_parts.append(f"  - Employer: {emp.get('org', '?')} ({emp.get('overlap_years', 'unknown')})")
        for sch in (rp.get("shared_schools") or []):
            if isinstance(sch, dict):
                fallback_parts.append(f"  - School: {sch.get('school', '?')} ({sch.get('overlap', 'unknown')})")
        for board in (rp.get("shared_boards") or []):
            fallback_parts.append(f"  - Board: {board}")
        if fallback_parts:
            parts.append(f"AI-Detected Overlap (unstructured):\n" + "\n".join(fallback_parts))

    parts.append(f"AI Capacity Tier: {contact.get('ai_capacity_tier', 'unknown')} (score: {contact.get('ai_capacity_score', '?')})")
    parts.append(f"AI Outdoorithm Fit: {contact.get('ai_outdoorithm_fit', 'unknown')}")

    # Wealth signals
    fec = parse_jsonb(contact.get("fec_donations"))
    parts.append(f"FEC Political Donations: {summarize_fec(fec)}")

    re_data = parse_jsonb(contact.get("real_estate_data"))
    parts.append(f"Real Estate Holdings: {summarize_real_estate(re_data)}")

    # Topics and philanthropy
    topics_str, philanthropy_str = get_topics_and_philanthropy(ai_tags)
    parts.append(f"Topics of Interest: {topics_str}")
    parts.append(f"Philanthropic Signals: {philanthropy_str}")
    parts.append("")

    # Communication history
    parts.append(f"Communication History:")
    parts.append(f"  {summarize_comms(contact)}")
    parts.append("")

    # LinkedIn connection date
    if contact.get("connected_on"):
        parts.append(f"LinkedIn Connection Since: {contact['connected_on']}")

    return "\n".join(parts)


# ── Main Scorer ──────────────────────────────────────────────────────

class AskReadinessScorer:
    MODEL = "gpt-5-mini"

    def __init__(self, goal="outdoorithm_fundraising", test_mode=False,
                 batch_size=None, start_from=0, workers=8, force=False):
        self.goal = goal
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.start_from = start_from
        self.workers = workers
        self.force = force
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.stats = {
            "processed": 0,
            "by_tier": {"ready_now": 0, "cultivate_first": 0, "long_term": 0, "not_a_fit": 0},
            "score_sum": 0,
            "score_min": 100,
            "score_max": 0,
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
        if not openai_key:
            print("ERROR: Missing OPENAI_APIKEY")
            return False

        self.supabase = create_client(url, key)
        self.openai = OpenAI(api_key=openai_key)
        print(f"Connected to Supabase and OpenAI")
        print(f"Goal: {self.goal}")
        return True

    def get_contacts(self) -> list[dict]:
        """Fetch contacts that need ask-readiness scoring for this goal."""
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                self.supabase.table("contacts")
                .select(SELECT_COLS)
                .not_.is_("ai_tags", "null")
                .order("id")
                .range(offset, offset + page_size - 1)
            )
            page = query.execute().data
            if not page:
                break
            all_contacts.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        # Filter out already-scored contacts (unless --force)
        if not self.force:
            filtered = []
            for c in all_contacts:
                ar = parse_jsonb(c.get("ask_readiness"))
                if not ar or not isinstance(ar, dict) or self.goal not in ar:
                    filtered.append(c)
            all_contacts = filtered

        # Apply start-from offset
        if self.start_from > 0:
            all_contacts = all_contacts[self.start_from:]

        # Apply batch/test limits
        if self.test_mode:
            all_contacts = all_contacts[:1]
        elif self.batch_size:
            all_contacts = all_contacts[:self.batch_size]

        return all_contacts

    def score_contact(self, contact: dict) -> Optional[AskReadinessResult]:
        """Call GPT-5 mini with donor psychology prompt for a single contact."""
        contact_context = build_contact_context(contact, self.goal)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions=SYSTEM_PROMPT,
                    input=contact_context,
                    text_format=AskReadinessResult,
                )

                if resp.usage:
                    self.stats["input_tokens"] += resp.usage.input_tokens
                    self.stats["output_tokens"] += resp.usage.output_tokens

                if resp.output_parsed:
                    return resp.output_parsed

                print(f"    Warning: No parsed output")
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

    def save_score(self, contact_id: int, existing_ar: object, result: AskReadinessResult) -> bool:
        """Save the ask-readiness score to Supabase, preserving other goal scores."""
        score_data = result.model_dump(mode="json")
        score_data["scored_at"] = datetime.now(timezone.utc).isoformat()

        # Merge with existing ask_readiness (preserve other goals)
        ar = {}
        if existing_ar and isinstance(existing_ar, dict):
            ar = dict(existing_ar)
        ar[self.goal] = score_data

        try:
            self.supabase.table("contacts").update({
                "ask_readiness": ar,
            }).eq("id", contact_id).execute()
            return True
        except Exception as e:
            print(f"    DB error for id={contact_id}: {e}")
            return False

    def process_contact(self, contact: dict) -> bool:
        """Process a single contact: score + save."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        contact_id = contact["id"]

        result = self.score_contact(contact)
        if result is None:
            self.stats["errors"] += 1
            print(f"  ERROR [{contact_id}] {name}: Failed to get ask-readiness score")
            return False

        existing_ar = parse_jsonb(contact.get("ask_readiness"))
        if self.save_score(contact_id, existing_ar, result):
            self.stats["processed"] += 1
            self.stats["by_tier"][result.tier.value] += 1
            self.stats["score_sum"] += result.score
            self.stats["score_min"] = min(self.stats["score_min"], result.score)
            self.stats["score_max"] = max(self.stats["score_max"], result.score)

            # Color-coded tier display
            tier_colors = {
                "ready_now": "\033[92m",       # green
                "cultivate_first": "\033[93m",  # yellow
                "long_term": "\033[90m",        # gray
                "not_a_fit": "\033[91m",        # red
            }
            reset = "\033[0m"
            color = tier_colors.get(result.tier.value, "")

            print(f"  [{contact_id}] {name}: {color}{result.score} ({result.tier.value}){reset} — "
                  f"{result.reasoning[:100]}...")
            return True
        else:
            self.stats["errors"] += 1
            return False

    def run(self):
        if not self.connect():
            return False

        if self.goal not in GOAL_CONTEXTS:
            print(f"WARNING: Goal '{self.goal}' has no predefined context. "
                  f"Available: {', '.join(GOAL_CONTEXTS.keys())}")
            print("Proceeding with generic goal context...")

        start_time = time.time()
        contacts = self.get_contacts()
        total = len(contacts)
        print(f"Found {total} contacts to score for '{self.goal}'")

        if total == 0:
            print("Nothing to do — all contacts already scored (use --force to re-score)")
            return True

        mode_str = "TEST" if self.test_mode else f"BATCH {self.batch_size}" if self.batch_size else "FULL"
        print(f"\n--- {mode_str} MODE: Processing {total} contacts with {self.workers} workers ---\n")

        if self.test_mode:
            # Sequential for test mode
            for c in contacts:
                self.process_contact(c)
        else:
            # Concurrent processing
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
                              f"(ready={self.stats['by_tier']['ready_now']}, "
                              f"cultivate={self.stats['by_tier']['cultivate_first']}, "
                              f"long_term={self.stats['by_tier']['long_term']}, "
                              f"not_fit={self.stats['by_tier']['not_a_fit']}, "
                              f"errors={self.stats['errors']}) "
                              f"[{rate:.1f}/sec, {elapsed:.0f}s] ---\n")

        elapsed = time.time() - start_time
        self.print_summary(elapsed)
        return self.stats["errors"] < total * 0.05

    def print_summary(self, elapsed: float):
        s = self.stats
        input_cost = s["input_tokens"] * 0.15 / 1_000_000
        output_cost = s["output_tokens"] * 0.60 / 1_000_000
        total_cost = input_cost + output_cost

        avg_score = s["score_sum"] / s["processed"] if s["processed"] > 0 else 0

        print("\n" + "=" * 60)
        print(f"ASK-READINESS SCORING SUMMARY — {self.goal}")
        print("=" * 60)
        print(f"  Contacts scored:       {s['processed']}")
        print(f"  Errors:                {s['errors']}")
        print()
        print("  TIER DISTRIBUTION:")
        print(f"    ready_now:           {s['by_tier']['ready_now']}")
        print(f"    cultivate_first:     {s['by_tier']['cultivate_first']}")
        print(f"    long_term:           {s['by_tier']['long_term']}")
        print(f"    not_a_fit:           {s['by_tier']['not_a_fit']}")
        print()
        print("  SCORE DISTRIBUTION:")
        print(f"    Average:             {avg_score:.1f}")
        if s["processed"] > 0:
            print(f"    Min:                 {s['score_min']}")
            print(f"    Max:                 {s['score_max']}")
        print()
        print(f"  Input tokens:          {s['input_tokens']:,}")
        print(f"  Output tokens:         {s['output_tokens']:,}")
        print(f"  Cost:                  ${total_cost:.2f} (input: ${input_cost:.2f}, output: ${output_cost:.2f})")
        print(f"  Time elapsed:          {elapsed:.1f}s")
        if s["processed"] > 0:
            print(f"  Avg time/contact:      {elapsed / s['processed']:.2f}s")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Score contacts for ask-readiness using donor psychology (GPT-5 mini)"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only 1 contact for validation")
    parser.add_argument("--batch", "-b", type=int, default=None,
                        help="Process N contacts")
    parser.add_argument("--start-from", "-s", type=int, default=0,
                        help="Skip first N contacts (for resuming)")
    parser.add_argument("--goal", "-g", type=str, default="outdoorithm_fundraising",
                        help="Goal to score for (default: outdoorithm_fundraising)")
    parser.add_argument("--workers", "-w", type=int, default=8,
                        help="Number of concurrent workers (default: 8)")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-score contacts already scored for this goal")
    args = parser.parse_args()

    scorer = AskReadinessScorer(
        goal=args.goal,
        test_mode=args.test,
        batch_size=args.batch,
        start_from=args.start_from,
        workers=args.workers,
        force=args.force,
    )
    success = scorer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
