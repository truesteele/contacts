#!/usr/bin/env python3
"""
Come Alive 2026 — Campaign Scaffolding

Uses GPT-5 mini structured output to assign campaign personas, capacity tiers,
motivation flags, lifecycle stages, lead stories, and copy building blocks to
each campaign contact. Output is saved to the `campaign_2026` JSONB column.

Follows the exact pattern of score_ask_readiness.py.

Usage:
  python scripts/intelligence/scaffold_campaign.py --test              # 1 contact
  python scripts/intelligence/scaffold_campaign.py --batch 50          # 50 contacts
  python scripts/intelligence/scaffold_campaign.py --workers 100       # custom concurrency
  python scripts/intelligence/scaffold_campaign.py --force             # re-scaffold already done
  python scripts/intelligence/scaffold_campaign.py --contact-id 1234   # specific contact
  python scripts/intelligence/scaffold_campaign.py                     # full run (~200)
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

class Persona(str, Enum):
    believer = "believer"
    impact_professional = "impact_professional"
    network_peer = "network_peer"

class CampaignList(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"

class CapacityTier(str, Enum):
    leadership = "leadership"
    major = "major"
    mid = "mid"
    base = "base"
    community = "community"

class PrimaryAskAmount(int, Enum):
    amt_250 = 250
    amt_500 = 500
    amt_1000 = 1000
    amt_2500 = 2500
    amt_5000 = 5000
    amt_10000 = 10000

class MotivationFlag(str, Enum):
    relationship = "relationship"
    mission_alignment = "mission_alignment"
    peer_identity = "peer_identity"
    parental_empathy = "parental_empathy"
    justice_equity = "justice_equity"
    community_belonging = "community_belonging"

class LifecycleStage(str, Enum):
    new = "new"
    prior_donor = "prior_donor"
    lapsed = "lapsed"

class LeadStory(str, Enum):
    valencia = "valencia"
    carl = "carl"
    eight_year_old = "8_year_old"
    michelle_latting = "michelle_latting"
    joy = "joy"
    aftan = "aftan"
    dorian = "dorian"
    sally_disney = "sally_disney"
    skip = "skip"

class CampaignScaffold(BaseModel):
    persona: Persona = Field(description="Primary campaign persona assignment")
    persona_confidence: int = Field(ge=0, le=100, description="Confidence in persona assignment 0-100")
    persona_reasoning: str = Field(description="2-3 sentence explanation of why this persona was chosen, citing specific data signals")
    campaign_list: CampaignList = Field(description="Campaign list assignment (A/B/C/D) based on ask readiness tier and score")
    capacity_tier: CapacityTier = Field(description="Standardized capacity tier for ask anchoring")
    primary_ask_amount: PrimaryAskAmount = Field(description="The specific dollar amount to anchor the ask")
    motivation_flags: list[MotivationFlag] = Field(description="1-3 motivation flags that apply to this contact, ordered by strength")
    primary_motivation: MotivationFlag = Field(description="The single strongest motivation flag — determines lead frame")
    lifecycle_stage: LifecycleStage = Field(description="Where this contact is in the donor lifecycle")
    lead_story: LeadStory = Field(description="Which story from the bank to lead with (or 'skip' if relationship carries the ask)")
    story_reasoning: str = Field(description="1-2 sentences explaining why this story matches this contact's motivation and values")
    opener_insert: str = Field(description="The specific opener line for this Persona x Lifecycle combination, adapted with any personal context")
    personalization_sentence: str = Field(description="One sentence connecting OC to this specific person's values, work, or shared history with Justin")
    thank_you_variant: str = Field(description="The thank-you message variant for this Persona x Motivation Flag combination")
    text_followup: str = Field(description="A natural text follow-up message for days 3-5 if no response, in Justin's voice")


# ── System Prompt ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a campaign strategist for Outdoorithm Collective's Come Alive 2026 fundraising campaign. Your job is to assign a campaign scaffold to each contact — persona, capacity tier, motivation flags, lifecycle stage, lead story, and personalized copy building blocks.

You are working with Justin Steele's personal network. Every contact has a real relationship with Justin. Your scaffolding decisions will be used to generate personalized outreach messages, so accuracy matters.

═══════════════════════════════════════════════════════════════
CAMPAIGN CONTEXT
═══════════════════════════════════════════════════════════════

Outdoorithm Collective is a 501(c)(3) outdoor equity nonprofit co-founded by Justin and Sally Steele.
Mission: Making outdoor recreation accessible to underserved communities through guided camping expeditions.

Come Alive 2026:
- Goal: $100K — fund 10 camping trips this season
- Math: 10 trips. $10K each. $100K total.
- Already committed: $35K from grants and early supporters
- Gap: $65K from friends and community
- Match: $20K dollar-for-dollar from an early supporter
- Format: 3 plain-text personal emails from Justin's personal email
- Audience: ~200 contacts across Lists A-D
- Launch: ~February 26, 2026

Impact language:
- $500 = one family comes alive
- $1,000 = two families at the campfire
- $2,500 = a quarter of a trip funded
- $5,000 = half a trip — rest, community, grit for 10 families
- $10,000 = a full trip — 10-12 families come alive together

═══════════════════════════════════════════════════════════════
THE THREE CAMPAIGN PERSONAS
═══════════════════════════════════════════════════════════════

PERSONA 1: THE BELIEVER
"I'm in because Justin asked."

Who they are: Close friends, family, co-founders, people who've been on OC trips or deeply involved. Their giving is relationship-first. They'd support almost anything Justin and Sally build because they trust them, have seen the work firsthand, and feel personally invested.

How to identify: Justin decides — this is NOT a data-derived segment. Data can suggest candidates: contacts with OC donor engagement, frequent comms, in_person/text approach, high scores. But the key signal is deep personal relationship.

Motivation: Relationship loyalty + personal identity ("I'm the kind of person who backs my people")
Brain circuits: Identity + Reward
Size: ~15-20 contacts (primarily List A)

Outreach scaffold:
- Channel: Personal text or casual email
- Tone: Warm, brief, insider language. No selling needed.
- Lead frame: "Quick thing. Here's what's happening. Would love to count you in."
- Story: Whichever they've personally witnessed, or skip — the relationship IS the story.
- Ask strategy: Anchor to capacity tier. They'll stretch for Justin. Don't underask.
- What NOT to do: Don't over-explain OC's mission to people who already know it.

PERSONA 2: THE IMPACT PROFESSIONAL
"This model works. I want to support it."

Who they are: Senior social impact executives, foundation leaders, CSR directors, philanthropy professionals, nonprofit CEOs, community development leaders. They evaluate nonprofits professionally. They see OC through a professional lens — model, outcomes, scalability.

Motivation: Mission alignment + professional identity ("I back effective organizations")
Brain circuits: Identity + Empathy
Size: ~35-50 contacts (across Lists A, B, C)

Data signals:
- Title includes "Impact," "Foundation," "Philanthropy," "Social," "CSR," "Community," or they run a nonprofit/social enterprise
- receiver_frame mentions effectiveness, community development, social infrastructure
- Companies: Google.org, foundations, social enterprises, impact investors, nonprofits
- Score 80+

Outreach scaffold:
- Channel: Personal email (List A) or campaign email (Lists B-C)
- Tone: Warm but substantive. Respect their expertise.
- Lead frame: Story first, then the model. "10 trips. $10K each. Families coming alive."
- Story: Stories showing systemic change — Carl, Michelle Latting, Joy
- Ask strategy: Mid-to-high. Frame as investment: "Your $5K funds half a trip."
- Match: Lead with it — they understand leverage.
- What NOT to do: Don't be vague. Don't use jargon they'd see through.

PERSONA 3: THE NETWORK PEER
"My people support this. I should too."

Who they are: Google colleagues, HBS/HKS classmates, Bain/Bridgespan alumni, professional network. They know Justin, respect him, but aren't inner circle. Relationship is primarily professional/alumni-based. Successful, busy, get lots of asks.

This is the LARGEST segment and DEFAULT persona for List D contacts.

Motivation: Peer identity + social proof ("People like me support things like this")
Brain circuits: Identity + Reward
Size: ~80-120 contacts (Lists B, C, D)

Data signals:
- Company = Google, former Google, major tech/consulting/finance
- Education: HBS, HKS, UVA, similar
- recommended_approach = personal_email
- Score 76-88
- No social impact title (those go to Impact Professional)

Outreach scaffold:
- Channel: Campaign email (3-email sequence)
- Tone: Justin's natural voice — personal, warm, not needy
- Lead frame: Valencia's story + social proof. The peer effect is the driver.
- Story: Stories anyone can connect to — Valencia, the 8-year-old. Human stories.
- Ask strategy: $1,000 / $2,500 / $5,000 ascending anchors
- Employer matching: Critical — many at Google, Meta, Salesforce with 1:1 matching.
- What NOT to do: Don't make it feel like a mass blast.

═══════════════════════════════════════════════════════════════
PERSONA DECISION TREE
═══════════════════════════════════════════════════════════════

Apply in this order:

1. Is the contact in Justin's inner circle? (OC engaged + frequent comms + approach=in_person/text + familiarity>=3, OR family, OR co-founder)
   → Believer

2. Does the contact work in social impact, philanthropy, CSR, foundation, or nonprofit leadership?
   → Impact Professional

3. Everyone else in the campaign universe
   → Network Peer

Edge cases:
- Someone with a social impact title who is ALSO inner circle → Believer (relationship trumps professional frame)
- Someone at Google.org who isn't personally close → Impact Professional (professional frame applies)
- List D contacts without ask readiness data → Network Peer (default scaffold)

═══════════════════════════════════════════════════════════════
CAMPAIGN LIST ASSIGNMENT
═══════════════════════════════════════════════════════════════

The contact's list assignment is provided in the context as "Campaign List Assignment." Use exactly what is provided — do NOT override it. The list is determined by the contact's ask readiness tier and score:

- List A: Inner circle, personal outreach before campaign launch (~20 contacts)
- List B: Remaining ready_now with addressable approach (~115 contacts)
- List C: Top cultivate_first (score >= 76) with addressable approach (~25-30 contacts)
- List D: Extended cultivate_first (score 60-75) with addressable approach (~40-60 contacts)

═══════════════════════════════════════════════════════════════
CAPACITY TIERS AND ASK AMOUNTS
═══════════════════════════════════════════════════════════════

Map the contact's suggested_ask_range to a standardized tier:

| Tier       | Ask Range      | Campaign Anchor | Who |
|------------|---------------|-----------------|-----|
| Leadership | $25,000+      | $10,000         | Pre-campaign personal outreach. Anchor gift or match candidate. |
| Major      | $5,000-$25,000| $5,000          | Pre-campaign or Email 1 priority. |
| Mid        | $1,000-$5,000 | $2,500          | Email campaign with specific anchor amounts. |
| Base       | $250-$1,000   | $1,000          | Email campaign. Employer matching emphasis. |
| Community  | Under $250    | $250            | Email campaign. Volume and community participation. |

Ask anchor by Persona x Capacity:

| | Community | Base | Mid | Major | Leadership |
|--|--:|--:|--:|--:|--:|
| Believer       | $250  | $1,000 | $2,500 | $5,000  | $10,000 |
| Impact Pro     | $500  | $1,000 | $2,500 | $5,000  | $10,000 |
| Network Peer   | $250  | $1,000 | $2,500 | $5,000  | $5,000  |

Prior donors: anchor 25-50% above their last gift.
Lapsed donors: match or slightly exceed their original gift.

═══════════════════════════════════════════════════════════════
MOTIVATION FLAGS
═══════════════════════════════════════════════════════════════

Assign 1-3 flags per contact. The primary flag determines the lead frame; secondary flags add reinforcement.

| Flag | What Drives Them | OC Framing | How to Detect |
|------|-----------------|------------|---------------|
| relationship | Loyalty to Justin/Sally personally | "I'm building something. Want you in." | Frequent comms, shared history, OC engaged |
| mission_alignment | OC's work matches their professional values | "Here's what's happening — and why it matters." | Social impact title, receiver_frame mentions effectiveness |
| peer_identity | Being part of what their cohort supports | "[X] friends have backed the season." | Google/HBS/HKS cohort, receiver_frame mentions leadership |
| parental_empathy | They see their family in OC's stories | "Her daughter runs barefoot through camp. No fear. Just joy." | personalization_angle or receiver_frame mentions family/kids |
| justice_equity | They care about who gets access to nature | "Being able to feel safe camping changes the narrative." | receiver_frame mentions equity/justice/access/representation |
| community_belonging | They value connection and shared experience | "A community that will never fail me." | receiver_frame mentions community/connection/belonging |

Most contacts carry 2-3 flags. Read the personalization_angle and receiver_frame carefully — they contain the strongest signals.

═══════════════════════════════════════════════════════════════
LIFECYCLE STAGE
═══════════════════════════════════════════════════════════════

| Stage | Definition | Key Signal |
|-------|-----------|------------|
| new | Never given to OC | No oc_engagement donor status, or oc_engagement shows non-donor role |
| prior_donor | Gave to OC previously (in 2025 or current campaign year) | oc_engagement shows is_oc_donor=true with recent donation |
| lapsed | Gave previously but not in 12+ months | oc_engagement shows donor status but last donation > 12 months ago |

IMPORTANT: Having oc_engagement does NOT mean they're a donor. Only 37% of contacts with oc_engagement are actual donors. Check is_oc_donor and oc_last_donation specifically.

If oc_engagement is absent or shows no donor history → "new"
If is_oc_donor is true and last donation within 12 months → "prior_donor"
If is_oc_donor is true and last donation > 12 months ago → "lapsed"

═══════════════════════════════════════════════════════════════
STORY BANK — MATCH TO MOTIVATION
═══════════════════════════════════════════════════════════════

| Story | Key Quote / Moment | Best For |
|-------|-------------------|----------|
| valencia | Mom from Alabama, first time outdoors. Afraid to sleep without locked door → most restorative sleep in years. Daughter running barefoot, no fear, just joy. | parental_empathy, universal human stories. The Come Alive story in purest form. |
| carl | "There are very few times as a Black man that I feel comfortable in the woods. Being able to feel safe camping changes the narrative." | justice_equity, mission_alignment. Systemic change angle. |
| 8_year_old | After first camping trip, asked mom to "go home to the campfire." Didn't mean the campsite — meant the feeling. | parental_empathy, community_belonging. Coming alive through a child's eyes. |
| michelle_latting | "It feels like core aspects of who we are as individuals and as a family are *made* on these trips." | parental_empathy, community_belonging. Family transformation. |
| joy | "This is a community that will never fail me." | community_belonging, relationship. The power of found community. |
| aftan | "The grief still exists, but it feels a bit lighter." Processing cousin's death on a trip. | community_belonging, mission_alignment. Healing through nature. |
| dorian | "Rejuvenated. Grounded. Rested. Calm. There's something about being outside that brings everything back into balance." | peer_identity (burnout/balance resonance), mission_alignment. |
| sally_disney | "449 nights at Humboldt for the price of three at Disney. One for the magic money could buy. The other for the magic money couldn't touch." | peer_identity (value/ROI framing), parental_empathy. |
| skip | No story — the relationship carries the ask. | Believers who know OC deeply. Don't need convincing. |

RULES:
- Believers with deep OC knowledge → "skip" (the relationship is the story)
- Believers who haven't heard the stories → "valencia" (most universal)
- Impact Professionals with justice/equity flag → "carl"
- Impact Professionals with parental empathy → "michelle_latting"
- Impact Professionals with community focus → "joy"
- Network Peers → default "valencia" (most universally resonant)
- Network Peers with justice/equity flag → "carl"
- Network Peers with parental empathy → "valencia" or "8_year_old"
- Anyone burned out / balance-seeking → "dorian"
- Anyone value-conscious / ROI-minded → "sally_disney"

═══════════════════════════════════════════════════════════════
EXECUTION MATRIX: OPENER INSERTS
═══════════════════════════════════════════════════════════════

Persona × Lifecycle → the opener line for their message:

| | New to OC | Prior Donor | Lapsed |
|--|--|--|--|
| Believer | "Quick thing. [Context]. Would love to count you in." | "Your support last year went to [trip]. Meant the world. Here's what's next." | "Haven't caught up in a while. OC is bigger this year. Would love to have you in it." |
| Impact Pro | "I don't think you've backed OC yet — if you want in this season, here's what's happening." | "Your gift last year went toward [trip] — [X] families. Building on that with 10 trips." | "You supported OC before. Reaching out personally because we're doing something bigger." |
| Network Peer | Campaign emails as-written (designed for new prospects). | Text follow-up: "Thanks for backing us last year. [Impact]. 10 trips this season." | Personal email before campaign: "You supported OC before. Wanted to reach out personally." |

Adapt these with personal context — reference their company, shared history, or specific details from the contact data.

═══════════════════════════════════════════════════════════════
FOLLOW-UP TIMING
═══════════════════════════════════════════════════════════════

| | First Follow-up | Second Follow-up | Thank-you |
|--|--|--|--|
| Believer | Text, 3 days | Text, 7 days | Text within hours |
| Impact Pro | Email, 5-7 days | Text, 10-12 days | Email within 24 hours |
| Network Peer | Text to openers, 3-5 days | Email 2 (automatic) | Email within 24 hours |

═══════════════════════════════════════════════════════════════
THANK-YOU FRAME: PERSONA × MOTIVATION FLAG
═══════════════════════════════════════════════════════════════

| Persona | Base Thank-you | + Parental Empathy | + Justice/Equity | + Community |
|--|--|--|--|--|
| Believer | "Means the world. Thank you." | Same — relationship is the frame | Same | Same |
| Impact Pro | "Your $X is going toward [trip]. [X] families." | "…families like yours." | "You're helping build what public lands should have been." | "You're funding a community that will outlast any program." |
| Network Peer | "You're the kind of person who shows up." | "Your gift sends [X] families to the campfire." | "You're funding spaces where every family belongs." | "You just joined something real." |

═══════════════════════════════════════════════════════════════
JUSTIN'S VOICE (for text follow-ups and openers)
═══════════════════════════════════════════════════════════════

- Direct, punchy, uses sentence fragments for emphasis
- Em dashes for parenthetical thoughts
- "This keeps happening" as a transition
- "Quick thing" as an opener
- Casual and conversational — sounds like a text from a friend
- Never sounds like a development officer or nonprofit pitch
- 2:1 "you/your" to "we/our" ratio
- Under 200 words for emails, shorter for texts
- "If you want in" = joining, not saving

═══════════════════════════════════════════════════════════════
ABOUT JUSTIN STEELE
═══════════════════════════════════════════════════════════════

- Co-founder, Outdoorithm Collective (501c3 outdoor equity nonprofit)
- Co-founder & CEO, Kindora (AI-powered grant matching platform)
- Former: Google (multiple roles), Bain & Company, Bridgespan Group
- Education: Harvard Business School (MBA), Harvard Kennedy School (MPP), UVA (BA)
- Based in Northern California
- Married to Sally Steele (co-founder of OC)
- Active in social impact, outdoor equity, and tech-for-good spaces

═══════════════════════════════════════════════════════════════
OUTPUT INSTRUCTIONS
═══════════════════════════════════════════════════════════════

For each contact, produce a CampaignScaffold with ALL fields populated:

1. persona — Apply the decision tree strictly
2. persona_confidence — How confident are you? 90+ if clear signals, 60-80 if borderline
3. persona_reasoning — Cite specific data signals (title, comms, OC engagement, etc.)
4. campaign_list — Use the list assignment provided in the contact context
5. capacity_tier — Map from suggested_ask_range using the tier table
6. primary_ask_amount — Use the Persona × Capacity anchor table
7. motivation_flags — 1-3 flags, ordered by strength. Read personalization_angle and receiver_frame.
8. primary_motivation — The strongest single flag
9. lifecycle_stage — Check oc_engagement donor status carefully
10. lead_story — Match to primary motivation using the story bank rules
11. story_reasoning — Why this story for this person
12. opener_insert — From the execution matrix, adapted with personal context
13. personalization_sentence — One sentence connecting OC to THIS person's specific values/work/history
14. thank_you_variant — From the thank-you frame matrix
15. text_followup — A natural 1-2 sentence text in Justin's voice for days 3-5

CRITICAL: The opener_insert, personalization_sentence, text_followup, and thank_you_variant must sound like Justin — casual, direct, personal. NOT like a CRM or a development officer."""


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
    "linkedin_reactions, "
    "ask_readiness, campaign_2026"
)


# ── Tier 1 (List A) contacts — inner circle for personal outreach ─────

TIER_1_NAMES = {
    "Marcus Steele", "Karibu Nyaggah", "Tiffany Cheng Nyaggah",
    "Roxana Shirkhoda", "Brigitte Hoyer Gosselink", "Tyler Scriven",
    "Erin Teague", "Hector Mujica", "Jason Trimiew", "Adrian Schurr",
    "Austin Swift", "Kevin Brege", "Freada Kapor Klein", "Chris Busselle",
    "Lo Toney", "Patrick Dickinson", "Terry Kramer", "Bryan Breckenridge",
    "Carrie Varoquiers", "Jose Gordon",
    # Extended if bandwidth allows
    "Mitch Kapor", "Rosita Najmi", "Jon Huggett", "Kavell Brown", "Sergio Garcia",
}


# ── Reuse helpers from score_ask_readiness ────────────────────────────

def parse_jsonb(val) -> object:
    """Parse a JSONB field that may be a string or already parsed."""
    if val is None:
        return None
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
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
    if not fec_data:
        return "No FEC records found"
    if fec_data.get("skipped_reason"):
        return "No FEC records (non-US contact)"
    total = fec_data.get("total_amount", 0)
    count = fec_data.get("donation_count", 0)
    max_single = fec_data.get("max_single", 0)
    parts = [f"${total:,.0f} total across {count} donations"]
    if max_single:
        parts.append(f"max single: ${max_single:,.0f}")
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
    if not re_data:
        return "No property records"
    source = re_data.get("source", "")
    if source in ("skip_trace_rejected", "skip_trace_failed"):
        return "No property records"
    if re_data.get("building_level_data"):
        address = re_data.get("address", "")
        if address:
            return f"Resident at {address} (condo/apartment — unit value unknown)"
        return "No reliable property records"
    ownership = re_data.get("ownership_likelihood", "uncertain")
    parts = []
    address = re_data.get("address", "")
    if ownership == "likely_renter":
        return f"Renter at {address}" if address else "Likely renter"
    if address:
        label = {"likely_owner": "Owner", "likely_owner_condo": "Condo owner"}.get(ownership, "Ownership uncertain")
        parts.append(f"Property ({label}): {address}")
    zestimate = re_data.get("zestimate")
    if zestimate:
        parts.append(f"Zestimate: ${zestimate:,.0f}")
    return ". ".join(parts) if parts else "No property records"


def summarize_comms(contact: dict) -> str:
    last_date = contact.get("comms_last_date")
    thread_count = contact.get("comms_thread_count", 0)
    closeness = contact.get("comms_closeness")
    momentum = contact.get("comms_momentum")
    if not last_date and not thread_count:
        return "No communication history"
    parts = []
    if closeness:
        parts.append(f"Closeness: {closeness}")
    if momentum:
        parts.append(f"Momentum: {momentum}")
    if last_date:
        parts.append(f"Last contact: {last_date}")
    if thread_count:
        parts.append(f"Total threads: {thread_count}")

    cs = parse_jsonb(contact.get("comms_summary"))
    if cs and isinstance(cs, dict):
        channels = cs.get("channels", {})
        ch_parts = []
        for ch_name in ["email", "linkedin", "sms"]:
            ch = channels.get(ch_name)
            if not ch:
                continue
            ch_threads = ch.get("threads", 0)
            ch_bidir = ch.get("bidirectional", 0)
            ch_last = (ch.get("last_date", "") or "")[:10]
            label = {"email": "email", "linkedin": "LinkedIn", "sms": "SMS"}.get(ch_name, ch_name)
            detail = f"{ch_threads} {label} ({ch_bidir} bidirectional"
            detail += f", last: {ch_last})" if ch_last else ")"
            ch_parts.append(detail)
        if ch_parts:
            parts.append(f"Channels: {'; '.join(ch_parts)}")

    comms = parse_jsonb(contact.get("communication_history"))
    if comms and isinstance(comms, dict):
        summary = comms.get("relationship_summary", "")
        if summary:
            parts.append(f"Relationship: {summary}")
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
    if not institutions or not isinstance(institutions, list):
        return "No shared institutions"
    parts = []
    for inst in institutions:
        if not isinstance(inst, dict):
            continue
        name = inst.get("name", "?")
        itype = inst.get("type", "")
        temporal = inst.get("temporal_overlap", False)
        depth = inst.get("depth", "")
        line = f"{name} ({itype})"
        if temporal:
            line += " [TEMPORAL OVERLAP]"
        if depth:
            line += f" [{depth}]"
        parts.append(f"  - {line}")
    return "\n".join(parts) if parts else "No shared institutions"


def summarize_employment(employment_data) -> str:
    data = parse_jsonb(employment_data)
    if not data or not isinstance(data, list):
        return "No employment history"
    positions = []
    for job in data[:6]:
        if not isinstance(job, dict):
            continue
        title = job.get("title", "")
        company = job.get("companyName", job.get("company", ""))
        start = job.get("startDate", "")
        end = job.get("endDate", "Present")
        line = f"  - {title} at {company}"
        if start:
            line += f" ({start} – {end})"
        positions.append(line)
    return "\n".join(positions) if positions else "No employment history"


def summarize_education(education_data) -> str:
    data = parse_jsonb(education_data)
    if not data or not isinstance(data, list):
        return "No education history"
    schools = []
    for edu in data:
        if not isinstance(edu, dict):
            continue
        school = edu.get("schoolName", edu.get("school", ""))
        degree = edu.get("degreeName", edu.get("degree", ""))
        field = edu.get("fieldOfStudy", edu.get("field", ""))
        line = f"  - {school}"
        if degree:
            line += f", {degree}"
        if field:
            line += f" in {field}"
        schools.append(line)
    return "\n".join(schools) if schools else "No education history"


def summarize_oc_engagement(oc_data) -> str:
    data = parse_jsonb(oc_data)
    if not data or not isinstance(data, dict):
        return "No OC engagement"
    parts = []
    roles = data.get("crm_roles", [])
    if roles:
        parts.append(f"CRM Roles: {', '.join(roles)}")
    if data.get("is_oc_donor"):
        total = data.get("oc_total_donated", 0)
        count = data.get("oc_donation_count", 0)
        last = data.get("oc_last_donation", "")
        parts.append(f"OC Donor: ${total:,.0f} total, {count} donations (last: {last})")
    trips_attended = data.get("trips_attended", 0)
    trips_registered = data.get("trips_registered", 0)
    if trips_attended or trips_registered:
        parts.append(f"Trips: {trips_attended} attended, {trips_registered} registered")
    return "\n  ".join(parts) if parts else "No OC engagement"


def summarize_linkedin_reactions(reactions_data) -> str:
    data = parse_jsonb(reactions_data)
    if not data or not isinstance(data, dict):
        return ""
    total = data.get("total_reactions", 0)
    if total == 0:
        return ""
    article_count = data.get("article_count", 0)
    articles = data.get("articles_reacted_to", [])
    parts = [f"Reacted to {article_count} of Justin's 9 LinkedIn articles ({total} total reactions)"]
    if articles:
        parts.append(f"Articles: {'; '.join(articles[:5])}")
    return "\n  ".join(parts)


def get_ask_readiness_summary(ar_data) -> str:
    """Summarize the ask readiness scoring for campaign context."""
    if not ar_data or not isinstance(ar_data, dict):
        return "No ask readiness data"
    oc = ar_data.get("outdoorithm_fundraising", {})
    if not oc:
        return "No OC fundraising readiness score"
    parts = []
    parts.append(f"Score: {oc.get('score', '?')}/100")
    parts.append(f"Tier: {oc.get('tier', '?')}")
    parts.append(f"Approach: {oc.get('recommended_approach', '?')}")
    parts.append(f"Ask Range: {oc.get('suggested_ask_range', '?')}")
    parts.append(f"Timing: {oc.get('ask_timing', '?')}")
    pa = oc.get("personalization_angle", "")
    if pa:
        parts.append(f"Personalization Angle: {pa}")
    rf = oc.get("receiver_frame", "")
    if rf:
        parts.append(f"Receiver Frame: {rf}")
    reasoning = oc.get("reasoning", "")
    if reasoning:
        parts.append(f"Reasoning: {reasoning}")
    return "\n  ".join(parts)


def determine_campaign_list(contact: dict) -> str:
    """Determine campaign list assignment based on ask readiness data and Tier 1 status."""
    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

    # List A: Tier 1 inner circle
    if name in TIER_1_NAMES:
        return "A"

    ar = parse_jsonb(contact.get("ask_readiness"))
    if not ar or not isinstance(ar, dict):
        return "D"  # No ask readiness data → List D default
    oc = ar.get("outdoorithm_fundraising", {})
    if not oc:
        return "D"

    tier = oc.get("tier", "")
    score = oc.get("score", 0)
    if isinstance(score, str):
        try:
            score = int(score)
        except (ValueError, TypeError):
            score = 0

    approach = oc.get("recommended_approach", "")
    addressable = approach in ("personal_email", "in_person", "text_message")

    if tier == "ready_now" and addressable:
        return "B"
    elif tier == "cultivate_first" and score >= 76 and addressable:
        return "C"
    elif tier == "cultivate_first" and 60 <= score <= 75 and addressable:
        return "D"

    return "D"


def build_contact_context(contact: dict) -> str:
    """Assemble the full per-contact context for the scaffolding prompt."""
    parts = []

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
    if contact.get("summary"):
        parts.append(f"LinkedIn About: {contact['summary'][:500]}")
    parts.append("")

    # Campaign list assignment (pre-computed)
    campaign_list = determine_campaign_list(contact)
    parts.append(f"Campaign List Assignment: {campaign_list}")

    # Is this contact in Tier 1 (inner circle)?
    if name in TIER_1_NAMES:
        parts.append("** THIS CONTACT IS IN TIER 1 (INNER CIRCLE) — personal outreach before campaign launch **")
    parts.append("")

    # Ask readiness summary
    ar = parse_jsonb(contact.get("ask_readiness"))
    parts.append(f"Ask Readiness:\n  {get_ask_readiness_summary(ar)}")
    parts.append("")

    # OC engagement
    oc_summary = summarize_oc_engagement(contact.get("oc_engagement"))
    parts.append(f"OC Engagement: {oc_summary}")

    # Communication history
    parts.append(f"Communication History:\n  {summarize_comms(contact)}")
    parts.append("")

    # Shared institutions
    institutions = parse_jsonb(contact.get("shared_institutions"))
    parts.append(f"Shared Institutions:\n{summarize_shared_institutions(institutions)}")

    # Employment & education
    parts.append(f"Employment:\n{summarize_employment(contact.get('enrich_employment'))}")
    parts.append(f"Education:\n{summarize_education(contact.get('enrich_education'))}")
    parts.append("")

    # Wealth signals
    fec = parse_jsonb(contact.get("fec_donations"))
    parts.append(f"FEC Donations: {summarize_fec(fec)}")
    re_data = parse_jsonb(contact.get("real_estate_data"))
    parts.append(f"Real Estate: {summarize_real_estate(re_data)}")

    # AI tags
    ai_tags = parse_jsonb(contact.get("ai_tags")) or {}
    ta = ai_tags.get("topical_affinity", {})
    topics = ta.get("topics", [])
    if topics:
        topic_strs = []
        for t in topics:
            if isinstance(t, dict):
                topic_strs.append(f"{t.get('topic', '?')} ({t.get('strength', '?')})")
        if topic_strs:
            parts.append(f"Topics of Interest: {', '.join(topic_strs)}")

    # Mission alignment flags
    alignment_flags = []
    if contact.get("outdoor_environmental_affinity"):
        evidence = contact.get("outdoor_affinity_evidence") or []
        alignment_flags.append(f"Outdoor/environmental: YES" +
                               (f" — {'; '.join(evidence[:3])}" if evidence else ""))
    if contact.get("equity_access_focus"):
        evidence = contact.get("equity_focus_evidence") or []
        alignment_flags.append(f"Equity/access: YES" +
                               (f" — {'; '.join(evidence[:3])}" if evidence else ""))
    if contact.get("nonprofit_board_member"):
        alignment_flags.append("Nonprofit board member: YES")
    if contact.get("known_donor"):
        alignment_flags.append("Known donor: YES")
    if alignment_flags:
        parts.append("Alignment Flags: " + "; ".join(alignment_flags))

    # LinkedIn reactions
    reactions = summarize_linkedin_reactions(contact.get("linkedin_reactions"))
    if reactions:
        parts.append(f"LinkedIn Engagement:\n  {reactions}")

    return "\n".join(parts)


# ── Main Scaffolder ──────────────────────────────────────────────────

class CampaignScaffolder:
    MODEL = "gpt-5-mini"

    def __init__(self, test_mode=False, batch_size=None, workers=150,
                 force=False, contact_id=None):
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.workers = workers
        self.force = force
        self.contact_id = contact_id
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.stats = {
            "processed": 0,
            "by_persona": {"believer": 0, "impact_professional": 0, "network_peer": 0},
            "by_list": {"A": 0, "B": 0, "C": 0, "D": 0},
            "by_tier": {"leadership": 0, "major": 0, "mid": 0, "base": 0, "community": 0},
            "by_lifecycle": {"new": 0, "prior_donor": 0, "lapsed": 0},
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
        print("Connected to Supabase and OpenAI")
        return True

    def get_contacts(self) -> list[dict]:
        """Fetch campaign contacts based on ask readiness tiers."""
        # Specific contact ID
        if self.contact_id:
            page = (
                self.supabase.table("contacts")
                .select(SELECT_COLS)
                .eq("id", self.contact_id)
                .execute()
            ).data
            return page or []

        # Fetch all contacts with ask_readiness data
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                self.supabase.table("contacts")
                .select(SELECT_COLS)
                .not_.is_("ask_readiness", "null")
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

        # Filter to campaign universe: ready_now (addressable) + cultivate_first >= 60 (addressable)
        campaign_contacts = []
        for c in all_contacts:
            ar = parse_jsonb(c.get("ask_readiness"))
            if not ar or not isinstance(ar, dict):
                continue
            oc = ar.get("outdoorithm_fundraising", {})
            if not oc:
                continue

            tier = oc.get("tier", "")
            score = oc.get("score", 0)
            if isinstance(score, str):
                try:
                    score = int(score)
                except (ValueError, TypeError):
                    score = 0
            approach = oc.get("recommended_approach", "")
            addressable = approach in ("personal_email", "in_person", "text_message")

            # Include: ready_now + addressable, or cultivate_first >= 60 + addressable
            if tier == "ready_now" and addressable:
                campaign_contacts.append(c)
            elif tier == "cultivate_first" and score >= 60 and addressable:
                campaign_contacts.append(c)

        # Also include Tier 1 contacts not already in the list
        tier1_ids = {c["id"] for c in campaign_contacts}
        for c in all_contacts:
            name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
            if name in TIER_1_NAMES and c["id"] not in tier1_ids:
                campaign_contacts.append(c)

        # Filter out already scaffolded (unless --force)
        if not self.force:
            filtered = []
            for c in campaign_contacts:
                c2026 = parse_jsonb(c.get("campaign_2026"))
                if not c2026 or not isinstance(c2026, dict) or "scaffold" not in c2026:
                    filtered.append(c)
            campaign_contacts = filtered

        # Apply limits
        if self.test_mode:
            campaign_contacts = campaign_contacts[:1]
        elif self.batch_size:
            campaign_contacts = campaign_contacts[:self.batch_size]

        return campaign_contacts

    def scaffold_contact(self, contact: dict) -> Optional[CampaignScaffold]:
        """Call GPT-5 mini to generate the campaign scaffold for a contact."""
        context = build_contact_context(contact)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions=SYSTEM_PROMPT,
                    input=context,
                    text_format=CampaignScaffold,
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
            return {k: CampaignScaffolder._strip_null_bytes(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [CampaignScaffolder._strip_null_bytes(v) for v in obj]
        return obj

    def save_scaffold(self, contact_id: int, existing_c2026: object,
                      result: CampaignScaffold) -> bool:
        """Save the scaffold to campaign_2026 JSONB, preserving other keys."""
        scaffold_data = result.model_dump(mode="json")

        # Merge with existing campaign_2026 (preserve personal_outreach, campaign_copy, etc.)
        c2026 = {}
        if existing_c2026 and isinstance(existing_c2026, dict):
            c2026 = dict(existing_c2026)
        c2026["scaffold"] = self._strip_null_bytes(scaffold_data)
        c2026["scaffolded_at"] = datetime.now(timezone.utc).isoformat()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.supabase.table("contacts").update({
                    "campaign_2026": c2026,
                }).eq("id", contact_id).execute()
                return True
            except Exception as e:
                err_str = str(e)
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
        """Process a single contact: scaffold + save."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        contact_id = contact["id"]

        result = self.scaffold_contact(contact)
        if result is None:
            self.stats["errors"] += 1
            print(f"  ERROR [{contact_id}] {name}: Failed to scaffold")
            return False

        existing_c2026 = parse_jsonb(contact.get("campaign_2026"))
        if self.save_scaffold(contact_id, existing_c2026, result):
            self.stats["processed"] += 1
            self.stats["by_persona"][result.persona.value] += 1
            self.stats["by_list"][result.campaign_list.value] += 1
            self.stats["by_tier"][result.capacity_tier.value] += 1
            self.stats["by_lifecycle"][result.lifecycle_stage.value] += 1

            # Color-coded persona display
            persona_colors = {
                "believer": "\033[92m",           # green
                "impact_professional": "\033[93m",  # yellow
                "network_peer": "\033[96m",         # cyan
            }
            reset = "\033[0m"
            color = persona_colors.get(result.persona.value, "")

            print(f"  [{contact_id}] {name}: {color}{result.persona.value}{reset} | "
                  f"List {result.campaign_list.value} | {result.capacity_tier.value} | "
                  f"${result.primary_ask_amount.value:,} | {result.primary_motivation.value} | "
                  f"{result.lifecycle_stage.value}")
            return True
        else:
            self.stats["errors"] += 1
            return False

    def _run_batch(self, contacts: list[dict], start_time: float,
                   total_label: int, workers: int) -> list[dict]:
        """Run a batch concurrently. Returns failed contacts."""
        failed = []
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

                if done_count % 25 == 0 or done_count == len(contacts):
                    elapsed = time.time() - start_time
                    rate = self.stats["processed"] / elapsed if elapsed > 0 else 0
                    print(f"\n--- Progress: {self.stats['processed']}/{total_label} "
                          f"(B={self.stats['by_persona']['believer']}, "
                          f"IP={self.stats['by_persona']['impact_professional']}, "
                          f"NP={self.stats['by_persona']['network_peer']}, "
                          f"err={self.stats['errors']}) "
                          f"[{rate:.1f}/sec, {elapsed:.0f}s] ---\n")

        return failed

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()
        contacts = self.get_contacts()
        total = len(contacts)
        print(f"Found {total} campaign contacts to scaffold")

        if total == 0:
            print("Nothing to do — all contacts already scaffolded (use --force to re-scaffold)")
            return True

        mode_str = "TEST" if self.test_mode else f"BATCH {self.batch_size}" if self.batch_size else "FULL"
        print(f"\n--- {mode_str} MODE: Scaffolding {total} contacts with {self.workers} workers ---\n")

        if self.test_mode:
            for c in contacts:
                self.process_contact(c)
        else:
            failed = self._run_batch(contacts, start_time, total, self.workers)

            if failed:
                retry_workers = min(4, len(failed))
                print(f"\n--- RETRY: {len(failed)} failed contacts with {retry_workers} workers ---\n")
                self.stats["errors"] = 0
                time.sleep(3)
                still_failed = self._run_batch(failed, start_time, total, retry_workers)
                if still_failed:
                    failed_ids = [c["id"] for c in still_failed]
                    print(f"\n  {len(still_failed)} contacts still failed: {failed_ids}")

        elapsed = time.time() - start_time
        self.print_summary(elapsed)
        return self.stats["errors"] < max(total * 0.05, 1)

    def print_summary(self, elapsed: float):
        s = self.stats
        input_cost = s["input_tokens"] * 0.15 / 1_000_000
        output_cost = s["output_tokens"] * 0.60 / 1_000_000
        total_cost = input_cost + output_cost

        print("\n" + "=" * 60)
        print("COME ALIVE 2026 — CAMPAIGN SCAFFOLDING SUMMARY")
        print("=" * 60)
        print(f"  Contacts scaffolded:   {s['processed']}")
        print(f"  Errors:                {s['errors']}")
        print()
        print("  PERSONA DISTRIBUTION:")
        print(f"    Believer:            {s['by_persona']['believer']}")
        print(f"    Impact Professional: {s['by_persona']['impact_professional']}")
        print(f"    Network Peer:        {s['by_persona']['network_peer']}")
        print()
        print("  CAMPAIGN LIST:")
        print(f"    A (Personal):        {s['by_list']['A']}")
        print(f"    B (Primary):         {s['by_list']['B']}")
        print(f"    C (Secondary):       {s['by_list']['C']}")
        print(f"    D (Extended):        {s['by_list']['D']}")
        print()
        print("  CAPACITY TIER:")
        print(f"    Leadership:          {s['by_tier']['leadership']}")
        print(f"    Major:               {s['by_tier']['major']}")
        print(f"    Mid:                 {s['by_tier']['mid']}")
        print(f"    Base:                {s['by_tier']['base']}")
        print(f"    Community:           {s['by_tier']['community']}")
        print()
        print("  LIFECYCLE:")
        print(f"    New:                 {s['by_lifecycle']['new']}")
        print(f"    Prior Donor:         {s['by_lifecycle']['prior_donor']}")
        print(f"    Lapsed:              {s['by_lifecycle']['lapsed']}")
        print()
        print(f"  Input tokens:          {s['input_tokens']:,}")
        print(f"  Output tokens:         {s['output_tokens']:,}")
        print(f"  Cost:                  ${total_cost:.2f} (in: ${input_cost:.2f}, out: ${output_cost:.2f})")
        print(f"  Time elapsed:          {elapsed:.1f}s")
        if s["processed"] > 0:
            print(f"  Avg time/contact:      {elapsed / s['processed']:.2f}s")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold campaign personas and copy building blocks for Come Alive 2026"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only 1 contact for validation")
    parser.add_argument("--batch", "-b", type=int, default=None,
                        help="Process N contacts")
    parser.add_argument("--workers", "-w", type=int, default=150,
                        help="Number of concurrent workers (default: 150)")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-scaffold contacts already scaffolded")
    parser.add_argument("--contact-id", type=int, default=None,
                        help="Scaffold a specific contact by ID")
    args = parser.parse_args()

    scaffolder = CampaignScaffolder(
        test_mode=args.test,
        batch_size=args.batch,
        workers=args.workers,
        force=args.force,
        contact_id=args.contact_id,
    )
    success = scaffolder.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
