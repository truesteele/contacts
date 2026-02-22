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
    text_message = "text_message"
    intro_via_mutual = "intro_via_mutual"

class AskTiming(str, Enum):
    now = "now"
    after_cultivation = "after_cultivation"
    after_reconnection = "after_reconnection"
    not_recommended = "not_recommended"

class AskReadinessResult(BaseModel):
    score: int = Field(ge=0, le=100, description="Overall ask-readiness score 0-100")
    tier: AskTier = Field(description="Ask-readiness tier")
    reasoning: str = Field(description="Comprehensive 4-6 sentence prospect summary. Must include: (1) relationship strength and basis, (2) key capacity signals (property, FEC, career level), (3) philanthropic alignment evidence, (4) recommended cultivation path. This is the primary summary a fundraiser will read.")
    recommended_approach: RecommendedApproach
    ask_timing: AskTiming
    cultivation_needed: str = Field(description="Specific, time-bound cultivation steps needed (e.g., '2-3 LinkedIn touchpoints over 4-6 weeks, then personal email — aim for ask in 2-3 months'), or 'None — ready for direct ask'")
    suggested_ask_range: str = Field(description="Dollar range like '$500-$2,000' or 'volunteer/attend first'")
    personalization_angle: str = Field(description="The strongest personalization hook, framed from the RECEIVER's perspective — what about their identity, interests, or overlap with Justin makes this cause resonate for THEM?")
    receiver_frame: str = Field(description="From the contact's perspective: what kind of message would they welcome from Justin, and why? Consider their interests, shared overlap, topics they write about, and what would make them feel like an insider rather than a target.")
    risk_factors: list[str] = Field(description="Specific ways the ask could backfire with THIS person — wrong channel, bad timing, misframing, asking too much/little, or damaging the relationship")


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
   The #1 predictor of individual giving is trust in the person asking. Warm outreach converts at 10x the rate of cold approaches.

   Relationship strength has TWO independent dimensions (based on Granovetter's tie strength theory):

   a) SUBJECTIVE CLOSENESS (familiarity_rating: 0-4)
      Justin's personal assessment of how well he knows this person:
      0=stranger, 1=recognize name, 2=know them, 3=good relationship, 4=close/trusted
      This captures emotional intensity and trust — it does NOT decay with time.
      A close friend you haven't spoken to in 3 years is still rated 4.

   b) BEHAVIORAL COMMUNICATION CLOSENESS (comms_closeness + comms_momentum)
      Data-derived from actual communication patterns across email, LinkedIn DMs, and SMS:
      - active_inner_circle: Frequent, recent, bidirectional communication across intimate channels
      - regular_contact: Consistent communication pattern, reliably in touch
      - occasional: Infrequent communication, scattered threads
      - dormant: Communication history exists but has gone cold (6+ months since last contact)
      - one_way: Predominantly one-directional communication
      - no_history: Zero communication records

      Momentum (temporal trend):
      - growing: Communication frequency is increasing — relationship is warming up
      - stable: Consistent pattern over time
      - fading: Communication was once more active but is declining
      - inactive: No recent communication

   THE 2x2 RELATIONSHIP MAP — USE THIS TO GUIDE YOUR ASSESSMENT:

   | Quadrant | Familiarity | Comms | Fundraising Strategy |
   |----------|------------|-------|----------------------|
   | Active Inner Circle | 3-4 | active/regular | DIRECT ASK. Warm, trusted, in touch. Highest conversion rate. |
   | Dormant Strong Ties | 3-4 | dormant/occasional | HIGHEST LEVERAGE. They trust Justin but aren't in touch. Reactivation ("it's been too long") before ask. These are the hidden gems. |
   | Active Weak Ties | 0-2 | active/regular | CULTIVATE DEEPER. Regular contact but not close. Move from transactional to personal before asking. |
   | Cold Contacts | 0-2 | dormant/none | LOW PRIORITY unless strong profile overlap. Requires cultivation or introduction. |

   MOMENTUM MODIFIERS:
   - Dormant Strong Tie + growing momentum = Relationship is naturally reactivating. STRIKE NOW.
   - Active Inner Circle + fading momentum = RISK of losing an engaged supporter. Check in urgently.
   - Growing momentum on any relationship = Window of opportunity. Act while the relationship is warming.

   Also consider:
   - Do they share formative experiences? People who worked together, went to school together, or served on boards together share identity-level bonds. Temporal overlap amplifies this — being at Google at the SAME TIME creates a fundamentally different bond than both having worked there in different decades
   - Is there reciprocity history? Prior favors, shared projects, mutual support create giving obligations

2. GIVING CAPACITY
   What matters is DISCRETIONARY giving capacity — what someone can realistically write a check for after their obligations. This requires thinking about the full picture, not just impressive-sounding signals.

   Use the employment history to reason about likely career earnings and wealth accumulation:
   - What sector have they spent their career in? Nonprofit/government/education careers pay salaries but don't generate equity wealth. A 20-year nonprofit career, even at the CEO level, means someone earning $300-600K with no stock options or equity upside.
   - For tech careers, LEVEL matters enormously. An IC or manager at Google for 5 years earned good money ($300-500K/yr) but didn't accumulate generational wealth. A VP+ at Google for 10+ years likely has $5-20M+ in vested equity. Read the actual titles and tenures in the employment history.
   - Family offices, wealth management, and advisory roles manage OTHER people's money — don't assume the advisor is personally wealthy.
   - Public company executives and founders have fundamentally different wealth profiles than salaried professionals at the same title level.

   Factor in obligations that consume income:
   - An expensive home (high Zestimate) in a high-COL area is as much an obligation as a wealth signal — a $2M home in the Bay Area means ~$12K/month in mortgage, taxes, and insurance. That's $144K/year before they spend a dollar on anything else.
   - Location context: $500K/year in San Francisco or New York, after housing, taxes, childcare/private school, leaves far less discretionary income than $500K in a lower-cost market.
   - Life stage: someone with young kids likely has major ongoing expenses (childcare, education, activities).

   Hard evidence vs inference:
   - FEC political donations are the strongest signal — they prove both disposable income AND willingness to write checks. Someone who gave $10K+ to political campaigns demonstrably has discretionary cash.
   - Owned real estate with high Zestimate shows asset wealth (but may be illiquid/mortgaged).
   - Prior charitable gifts are direct evidence.
   - Everything else (titles, employer prestige) is inference. Be transparent about what is known vs assumed.

   Real estate nuances:
   - Only count property value for likely owners. If flagged as a renter, the Zestimate is the landlord's asset, not theirs.
   - A high-value home with no FEC donations and a nonprofit career likely means most wealth is tied up in the house, not liquid.

   But capacity WITHOUT relationship is meaningless for individual asks — a billionaire who doesn't know Justin won't give.

3. PHILANTHROPIC PROPENSITY
   Likelihood of giving based on values and identity alignment. Key signals:
   - Do they have a philanthropic identity? (board service, volunteer history, nonprofit work)
   - Do they post/talk about causes, equity, giving back?
   - Values alignment with the specific cause (outdoor equity, youth access, environmental justice)
   - Identity-based giving: "people like me give to causes like this" — shared social circles, similar career arcs, peer effects
   - Have they supported similar organizations?

   CRITICAL — INSTITUTIONAL vs PERSONAL GIVING:
   You are ONLY assessing this person's likelihood of making a PERSONAL gift. Do NOT:
   - Recommend pitching someone for an institutional grant just because they work at a foundation
   - Conflate someone's professional grantmaking role with their personal giving capacity
   - Suggest "apply for a grant from their foundation" — Justin has a separate process for institutional giving
   A program officer at the Ford Foundation may personally give $500 from their own wallet. Assess THAT, not the Ford Foundation's $16B endowment.
   If someone works in institutional philanthropy, note it as a signal of philanthropic values alignment, but score based on their personal capacity (salary, property, FEC donations, etc).

4. PSYCHOLOGICAL READINESS
   Timing and receptivity. Consider:
   - Life stage and transitions (new role = less capacity but possibly more openness; recently retired = more time and philanthropic interest)
   - Recent communication warmth — did the last exchange feel positive, collaborative, friendly?
   - Has Justin already cultivated this relationship, or would the ask come out of nowhere?
   - Would this person feel the ask is authentic coming from Justin, or would it feel transactional?
   - The "warm glow" factor — will giving to this cause make them feel good about themselves?

5. OUTREACH CHANNEL STRATEGY (Evidence-Based)
   DO NOT recommend channels that don't work. Here's what the research says:

   PHONE CALLS — Almost never recommend.
   Cold fundraising calls have a 2.3% success rate and most people experience them as intrusive. Only recommend phone_call when:
   - The contact is active_inner_circle AND familiarity >= 3 (they actually talk on the phone)
   - It's a THANK-YOU call after a gift (not a solicitation)
   - There's existing phone/SMS history showing they communicate by phone
   Phone is for deepening warm relationships, NOT for cold outreach.

   PERSONAL EMAIL — Primary outreach channel ($36-40 ROI per $1 spent).
   Best for: initial cultivation messages, formal asks after cultivation, follow-ups, stewardship.
   Use donor-centric language — frame around THEIR identity, not Justin's need.
   Donor-centric framing increases retention from 27% to 45%.

   LINKEDIN — Best for re-engagement and warm cultivation.
   Highest-converting social channel for nonprofits. 98% of LinkedIn users donate annually.
   Best for: reconnecting with dormant strong ties ("it's been too long"), sharing OC content organically, building visibility pre-ask.
   NOT for: cold transactional asks or generic InMail solicitations.

   TEXT/SMS — Only for people Justin already texts with.
   98% open rate, highest-engagement channel. But ONLY appropriate when:
   - Contact has existing SMS history (comms shows sms channel)
   - Relationship is close enough that texting feels natural (familiarity >= 3)
   Good for: casual check-ins, event invites, quick personal touchpoints.
   NEVER recommend for contacts without existing SMS communication.

   IN-PERSON — Highest conversion for major asks ($5K+).
   Best for: Outdoorithm trips/events, donor cultivation dinners, impact site visits.
   Requires existing warm relationship. Don't recommend cold in-person meetings.

   INTRO VIA MUTUAL — Best for cold high-capacity contacts.
   Warm introductions convert at 14.6% vs 1.7% for cold outreach (8.6x). Recommend when:
   - Contact is distant (familiarity 0-1) but has high capacity or strong alignment
   - Direct outreach would feel presumptuous given the relationship distance

6. RECEIVER PERSONIFICATION FRAMEWORK
   Before writing ANY outreach guidance, PUT YOURSELF IN THE CONTACT'S SHOES.

   Consider:
   a) What does this person care about? (Their Topics of Interest, LinkedIn About, volunteering, career focus, posting activity)
   b) What do they share with Justin? (Shared institutions, temporal overlap, shared causes, mutual connections)
   c) What would make them feel like an INSIDER, not a TARGET?
   d) What kind of message would they be GLAD to receive from Justin?

   Frame ALL outreach guidance from the receiver's perspective:
   - BAD: "Call them and ask for $5K" (Justin-centric, transactional)
   - GOOD: "As a fellow HBS alum working in environmental policy, they'd welcome a personal email about how OC bridges outdoor access gaps — directly connected to their professional focus. An invitation to see impact firsthand would appeal to their hands-on orientation."

   Identity framing is the most powerful tool (r=.32, twice as strong as shared identity alone):
   - "As someone who has dedicated their career to equity..."
   - "Given your deep connection to the outdoors..."
   - "As a fellow [institution] alum who believes in..."

   HNW donors especially want PARTNERSHIP, not transactions. They want impact evidence, involvement opportunities, and to feel like co-creators — not ATMs.

CRITICAL BEHAVIORAL INSIGHTS:
- Warm outreach converts at 14.6% vs 1.7% for cold (8.6x). ALWAYS prioritize warming the relationship before asking.
- Donors who feel like insiders give more. Shared institutional membership creates insider feeling.
- Identity effect: "I am the kind of person who..." framing (r=.32) is the strongest predictor — twice as powerful as shared identity alone (r=.15).
- Social proof: 48% of donors trust friend/family recommendations. Mention mutual connections who support OC when possible.
- The identifiable victim effect: one person's story > statistics. Contacts who've experienced the outdoors (or have kids who would benefit) empathize more.
- Loss aversion: "Don't miss being part of this founding group" > "Please donate."
- Second-gift psychology: prior givers are 2-3x more likely to give again. First-time donor retention is only 19.4%, but repeat donors retain at 69.2%.
- Monthly giving: 5.4x lifetime value (83% vs 45% retention). Best converted within 30-90 days of first gift.
- 80/20 rule: 80% of communication should be cultivation (sharing impact, building relationship), 20% solicitation. Asking too often poisons the well.
- Cultivation timelines: warm contacts/event participants ask in 30-90 days. Mid-level donors need 2-6 months. Major donors ($10K+) need 12-24 months.

OUTPUT REQUIREMENTS:
Produce a structured assessment with score (0-100), tier, reasoning, recommended_approach, ask_timing, cultivation_needed, suggested_ask_range, personalization_angle, receiver_frame, and risk_factors.

The 'reasoning' field is the most important output — it's the fundraiser's briefing. Include ALL relevant evidence: relationship basis (shared institutions, comms history, familiarity), capacity signals (FEC donation totals, property value if owner, career level), alignment signals (outdoor/equity interests, board service, philanthropic identity), and the key risk or opportunity. Write it as a decision-ready paragraph, not a vague summary.

The 'cultivation_needed' field must be SPECIFIC and TIME-BOUND:
- BAD: "Some cultivation needed"
- GOOD: "2-3 LinkedIn touchpoints over 4-6 weeks (engage with their content, share OC impact stories), then a personal email connecting their environmental work to OC's mission. Aim for ask in 2-3 months."

The 'personalization_angle' should describe the strongest hook FROM THE RECEIVER'S PERSPECTIVE:
- BAD: "They went to HBS with Justin"
- GOOD: "As a fellow HBS alum now in environmental policy, frame OC as the evidence-based outdoor equity work they were trained to build — connects their professional identity to the cause."

The 'receiver_frame' field should articulate what the contact would WANT to hear, from their perspective:
- BAD: "Tell them about OC's mission"
- GOOD: "They post regularly about DEI in outdoor recreation and their kids' hiking. An email connecting OC's youth camping expeditions to their passion for getting diverse families outdoors would feel like a natural, welcome invitation — not a cold solicitation."

The 'risk_factors' should flag specific approaches that could BACKFIRE with THIS person:
- Calling someone you haven't spoken to in years feels intrusive
- A generic fundraising email to someone in philanthropy professionally will feel amateur
- Asking for money before warming the relationship poisons future asks
- A small ask to a HNW contact may feel insulting; a large ask to modest-income contact feels tone-deaf
- Mentioning shared institutions you barely overlapped at can feel presumptuous

SCORING GUIDANCE:
- 80-100 (ready_now): Close relationship + financial capacity + values alignment + recent warm contact. Ready for a personal, well-framed ask.
- 60-79 (cultivate_first): Good relationship foundation but needs 1-3 cultivation touchpoints before asking. Reconnect, share the mission, build warmth — ask in 1-3 months.
- 40-59 (long_term): Has capacity and some alignment, but relationship is too thin for a direct ask. Needs 4-8 cultivation touchpoints over 3-12 months.
- 20-39 (long_term): Distant connection or weak alignment. Only pursue if capacity is very high and a warm intro path exists.
- 0-19 (not_a_fit): No relationship, no alignment, or no capacity. Don't waste effort.

Be honest and realistic. Most LinkedIn connections are NOT ready for a fundraising ask. A 2,400-person network might yield 50-100 genuinely ready, 200-300 worth cultivating, and the rest are too distant."""


# ── Select columns ────────────────────────────────────────────────────

SELECT_COLS = (
    "id, first_name, last_name, headline, summary, company, position, "
    "connected_on, city, state, familiarity_rating, "
    "ai_tags, shared_institutions, "
    "ai_capacity_tier, ai_capacity_score, ai_outdoorithm_fit, "
    "fec_donations, real_estate_data, "
    "comms_last_date, comms_thread_count, communication_history, "
    "comms_closeness, comms_momentum, comms_summary, "
    "enrich_employment, enrich_education, enrich_volunteering, "
    "known_donor, nonprofit_board_member, "
    "outdoor_environmental_affinity, outdoor_affinity_evidence, "
    "equity_access_focus, equity_focus_evidence, "
    "joshua_tree_invited, oc_engagement, "
    "ask_readiness"
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
    if fec_data.get("skipped_reason"):
        return "No FEC records (non-US contact — FEC is US-only)"
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
    """Summarize real estate data into a readable string.

    Uses ownership_likelihood to contextualize property data:
    - Owners: full Zestimate as wealth signal
    - Renters: suppress Zestimate (it's the landlord's asset)
    - Uncertain: include data but note uncertainty
    """
    if not re_data:
        return "No property records found"
    source = re_data.get("source", "")
    if source in ("skip_trace_rejected", "skip_trace_failed"):
        return "No property records found"

    # Building-level records (e.g., entire condo building, not a unit) — suppress misleading values
    if re_data.get("building_level_data"):
        address = re_data.get("address", "")
        if address:
            return f"Resident at {address} (condo/apartment building — unit-level value unknown)"
        return "No reliable property records"

    ownership = re_data.get("ownership_likelihood", "uncertain")
    parts = []

    address = re_data.get("address", "")

    if ownership == "likely_renter":
        # Renter: suppress Zestimate — it's the landlord's wealth, not theirs
        if address:
            parts.append(f"Renter at {address}")
        else:
            parts.append("Likely renter (no property ownership)")
        return ". ".join(parts)

    # Owner or uncertain — include property details
    if address:
        if ownership in ("likely_owner", "likely_owner_condo"):
            label = "Owner" if ownership == "likely_owner" else "Condo owner"
            parts.append(f"Property ({label}): {address}")
        else:
            parts.append(f"Property (ownership uncertain): {address}")

    zestimate = re_data.get("zestimate")
    if zestimate:
        parts.append(f"Zestimate: ${zestimate:,.0f}")

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
    closeness = contact.get("comms_closeness")
    momentum = contact.get("comms_momentum")

    if not last_date and not thread_count:
        return "No communication history (email, LinkedIn, or SMS)"

    parts = []

    # Communication closeness and momentum (behavioral/data-derived signals)
    if closeness:
        parts.append(f"Communication Closeness (behavioral): {closeness}")
    if momentum:
        parts.append(f"Communication Momentum: {momentum}")

    if last_date:
        parts.append(f"Last contact: {last_date}")
    if thread_count:
        parts.append(f"Total threads (email + LinkedIn DMs + SMS): {thread_count}")

    # Rich channel-level data from comms_summary JSONB
    cs = parse_jsonb(contact.get("comms_summary"))
    if cs and isinstance(cs, dict):
        channels = cs.get("channels", {})
        # Channel breakdown
        ch_parts = []
        for ch_name in ["email", "linkedin", "sms"]:
            ch = channels.get(ch_name)
            if not ch:
                continue
            ch_threads = ch.get("threads", 0)
            ch_bidir = ch.get("bidirectional", 0)
            ch_group = ch.get("group_threads", 0)
            ch_last = ch.get("last_date", "")
            if ch_last:
                ch_last = ch_last[:10]  # date only
            label = {"email": "email", "linkedin": "LinkedIn DM", "sms": "SMS"}.get(ch_name, ch_name)
            detail = f"{ch_threads} {label} threads ({ch_bidir} bidirectional"
            if ch_name == "email" and ch_group:
                detail += f", {ch_group} group"
            detail += f", last: {ch_last})" if ch_last else ")"
            ch_parts.append(detail)
        if ch_parts:
            parts.append(f"Channel breakdown: {'; '.join(ch_parts)}")

        bidir_pct = cs.get("bidirectional_pct", 0)
        parts.append(f"Overall bidirectional rate: {bidir_pct:.0f}%")

        most_recent = cs.get("most_recent_channel")
        if most_recent:
            parts.append(f"Most recent channel: {most_recent}")

        chrono = cs.get("chronological_summary")
        if chrono:
            parts.append(f"Activity timeline: {chrono}")

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


def summarize_employment(employment_data) -> str:
    """Summarize LinkedIn employment history into readable text."""
    data = parse_jsonb(employment_data)
    if not data or not isinstance(data, list):
        return "No employment history available"
    positions = []
    for job in data[:8]:  # Cap at 8 most recent positions
        if not isinstance(job, dict):
            continue
        title = job.get("title", "")
        company = job.get("companyName", job.get("company", ""))
        start = job.get("startDate", "")
        end = job.get("endDate", "Present")
        desc = job.get("description", "")
        line = f"  - {title} at {company}"
        if start:
            line += f" ({start} – {end})"
        if desc:
            # Truncate long descriptions
            desc_short = desc[:200] + "..." if len(desc) > 200 else desc
            line += f"\n    {desc_short}"
        positions.append(line)
    return "\n".join(positions) if positions else "No employment history available"


def summarize_education(education_data) -> str:
    """Summarize LinkedIn education history into readable text."""
    data = parse_jsonb(education_data)
    if not data or not isinstance(data, list):
        return "No education history available"
    schools = []
    for edu in data:
        if not isinstance(edu, dict):
            continue
        school = edu.get("schoolName", edu.get("school", ""))
        degree = edu.get("degreeName", edu.get("degree", ""))
        field = edu.get("fieldOfStudy", edu.get("field", ""))
        start = edu.get("startDate", "")
        end = edu.get("endDate", "")
        line = f"  - {school}"
        if degree:
            line += f", {degree}"
        if field:
            line += f" in {field}"
        if start or end:
            line += f" ({start}–{end})"
        schools.append(line)
    return "\n".join(schools) if schools else "No education history available"


def summarize_volunteering_data(volunteering_data) -> str:
    """Summarize LinkedIn volunteering into readable text."""
    data = parse_jsonb(volunteering_data)
    if not data or not isinstance(data, list):
        return "No volunteering history"
    items = []
    for vol in data:
        if not isinstance(vol, dict):
            continue
        role = vol.get("role", vol.get("title", ""))
        org = vol.get("companyName", vol.get("organization", ""))
        cause = vol.get("cause", "")
        line = f"  - {role} at {org}"
        if cause:
            line += f" (cause: {cause})"
        items.append(line)
    return "\n".join(items) if items else "No volunteering history"


def summarize_oc_engagement(oc_data) -> str:
    """Summarize Outdoorithm Collective CRM engagement into readable text."""
    data = parse_jsonb(oc_data)
    if not data or not isinstance(data, dict):
        return ""
    parts = []
    roles = data.get("crm_roles", [])
    if roles:
        parts.append(f"CRM Roles: {', '.join(roles)}")
    if data.get("is_oc_donor"):
        total = data.get("oc_total_donated", 0)
        count = data.get("oc_donation_count", 0)
        last = data.get("oc_last_donation", "")
        parts.append(f"OC Donor: ${total:,.0f} total across {count} donations (last: {last})")
    trips_attended = data.get("trips_attended", 0)
    trips_registered = data.get("trips_registered", 0)
    if trips_attended or trips_registered:
        parts.append(f"Trip participation: {trips_attended} attended, {trips_registered} registered")
    return "\n  ".join(parts)


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

    # LinkedIn About/Summary — rich self-description of values and identity
    if contact.get("summary"):
        parts.append(f"LinkedIn About: {contact['summary']}")
    parts.append("")

    # Prior fundraising signals
    prior_signals = []
    if contact.get("known_donor"):
        prior_signals.append("KNOWN DONOR (has given before)")
    if contact.get("joshua_tree_invited"):
        prior_signals.append("Previously invited to Outdoorithm Joshua Tree trip")
    if prior_signals:
        parts.append(f"Prior Fundraising History: {'; '.join(prior_signals)}")

    # Outdoorithm Collective CRM engagement (direct organizational involvement)
    oc_summary = summarize_oc_engagement(contact.get("oc_engagement"))
    if oc_summary:
        parts.append(f"Outdoorithm Collective Engagement:\n  {oc_summary}")

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

    parts.append(f"AI Capacity Estimate (rough, title-based — use employment history above to form your own judgment): {contact.get('ai_capacity_tier', 'unknown')} (score: {contact.get('ai_capacity_score', '?')})")
    parts.append(f"AI Outdoorithm Fit: {contact.get('ai_outdoorithm_fit', 'unknown')}")

    # Mission alignment flags
    alignment_flags = []
    if contact.get("outdoor_environmental_affinity"):
        evidence = contact.get("outdoor_affinity_evidence") or []
        alignment_flags.append(f"Outdoor/environmental affinity: YES" +
                               (f" — {'; '.join(evidence[:3])}" if evidence else ""))
    if contact.get("equity_access_focus"):
        evidence = contact.get("equity_focus_evidence") or []
        alignment_flags.append(f"Equity/access focus: YES" +
                               (f" — {'; '.join(evidence[:3])}" if evidence else ""))
    if contact.get("nonprofit_board_member"):
        alignment_flags.append("Nonprofit board member: YES")
    if alignment_flags:
        parts.append("Mission Alignment Flags:\n  " + "\n  ".join(alignment_flags))

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

    # Raw LinkedIn career data
    parts.append(f"Employment History:\n{summarize_employment(contact.get('enrich_employment'))}")
    parts.append(f"Education:\n{summarize_education(contact.get('enrich_education'))}")
    vol_summary = summarize_volunteering_data(contact.get("enrich_volunteering"))
    if vol_summary != "No volunteering history":
        parts.append(f"Volunteering:\n{vol_summary}")
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
                 batch_size=None, start_from=0, workers=8, force=False, ids=None):
        self.goal = goal
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.start_from = start_from
        self.workers = workers
        self.force = force
        self.ids = ids  # list of specific contact IDs to score
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
        # If specific IDs requested, fetch just those
        if self.ids:
            all_contacts = []
            # Supabase .in_() supports batches; fetch in chunks of 100
            for i in range(0, len(self.ids), 100):
                chunk = self.ids[i:i+100]
                page = (
                    self.supabase.table("contacts")
                    .select(SELECT_COLS)
                    .in_("id", chunk)
                    .order("id")
                    .execute()
                ).data
                if page:
                    all_contacts.extend(page)
            return all_contacts

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

    @staticmethod
    def _strip_null_bytes(obj):
        """Recursively strip \\u0000 null bytes that PostgreSQL JSONB rejects."""
        if isinstance(obj, str):
            return obj.replace("\u0000", "")
        if isinstance(obj, dict):
            return {k: AskReadinessScorer._strip_null_bytes(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [AskReadinessScorer._strip_null_bytes(v) for v in obj]
        return obj

    def save_score(self, contact_id: int, existing_ar: object, result: AskReadinessResult) -> bool:
        """Save the ask-readiness score to Supabase, preserving other goal scores."""
        score_data = result.model_dump(mode="json")
        score_data["scored_at"] = datetime.now(timezone.utc).isoformat()

        # Merge with existing ask_readiness (preserve other goals)
        ar = {}
        if existing_ar and isinstance(existing_ar, dict):
            ar = dict(existing_ar)
        ar[self.goal] = self._strip_null_bytes(score_data)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.supabase.table("contacts").update({
                    "ask_readiness": ar,
                }).eq("id", contact_id).execute()
                return True
            except Exception as e:
                err_str = str(e)
                # Transient errors: SSL EOF, connection terminated — retry with backoff
                if any(kw in err_str for kw in ("EOF occurred", "ConnectionTerminated", "ConnectionReset", "BrokenPipe")):
                    if attempt < max_retries - 1:
                        wait = 2 ** (attempt + 1)
                        print(f"    DB transient error for id={contact_id}, retrying in {wait}s...")
                        time.sleep(wait)
                        continue
                print(f"    DB error for id={contact_id}: {e}")
                return False
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

    def _run_batch(self, contacts: list[dict], start_time: float,
                   total_label: int, workers: int) -> list[dict]:
        """Run a batch of contacts concurrently. Returns list of failed contacts."""
        failed = []
        # Map futures to full contact dicts (needed for retry)
        contact_by_future = {}

        with ThreadPoolExecutor(max_workers=workers) as executor:
            for c in contacts:
                future = executor.submit(self.process_contact, c)
                contact_by_future[future] = c

            done_count = 0
            for future in as_completed(contact_by_future):
                done_count += 1
                contact = contact_by_future[future]
                try:
                    success = future.result()
                    if not success:
                        failed.append(contact)
                except Exception as e:
                    cid = contact["id"]
                    print(f"  [ERROR] Contact {cid}: {e}")
                    self.stats["errors"] += 1
                    failed.append(contact)

                if done_count % 50 == 0 or done_count == len(contacts):
                    elapsed = time.time() - start_time
                    rate = (self.stats["processed"]) / elapsed if elapsed > 0 else 0
                    print(f"\n--- Progress: {self.stats['processed']}/{total_label} "
                          f"(ready={self.stats['by_tier']['ready_now']}, "
                          f"cultivate={self.stats['by_tier']['cultivate_first']}, "
                          f"long_term={self.stats['by_tier']['long_term']}, "
                          f"not_fit={self.stats['by_tier']['not_a_fit']}, "
                          f"errors={self.stats['errors']}) "
                          f"[{rate:.1f}/sec, {elapsed:.0f}s] ---\n")

        return failed

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
            # Main concurrent pass
            failed = self._run_batch(contacts, start_time, total, self.workers)

            # Auto-retry failed contacts sequentially with delays
            if failed:
                retry_workers = min(4, len(failed))
                print(f"\n--- RETRY PASS: {len(failed)} failed contacts with {retry_workers} workers ---\n")
                # Reset error count — retries get a fresh chance
                self.stats["errors"] = 0
                time.sleep(3)  # Brief pause to let connections recover
                still_failed = self._run_batch(failed, start_time, total, retry_workers)

                if still_failed:
                    failed_ids = [c["id"] for c in still_failed]
                    print(f"\n  {len(still_failed)} contacts still failed after retry: {failed_ids}")
                    print(f"  Re-run with: --ids {','.join(str(i) for i in failed_ids)}")

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
    parser.add_argument("--workers", "-w", type=int, default=150,
                        help="Number of concurrent workers (default: 50)")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-score contacts already scored for this goal")
    parser.add_argument("--ids", type=str, default=None,
                        help="Comma-separated list of contact IDs to score (e.g., '1264,1972,2070')")
    args = parser.parse_args()

    ids_list = None
    if args.ids:
        ids_list = [int(x.strip()) for x in args.ids.split(",") if x.strip()]

    scorer = AskReadinessScorer(
        goal=args.goal,
        test_mode=args.test,
        batch_size=args.batch,
        start_from=args.start_from,
        workers=args.workers,
        force=args.force,
        ids=ids_list,
    )
    success = scorer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
