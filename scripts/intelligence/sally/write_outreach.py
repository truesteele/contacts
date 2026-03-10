#!/usr/bin/env python3
"""
Come Alive 2026 — Personal Outreach Writer for Sally's Network (Claude Opus 4.6)

Uses Claude Opus 4.6 to write high-quality, voice-authentic personal messages
for List A contacts in Sally's network. These are the highest-stakes messages
in the campaign — they must sound like they came from Sally's phone.

Output is saved to the `campaign_2026` JSONB column under `personal_outreach`
in the `sally_contacts` table.

Usage:
  python scripts/intelligence/sally/write_outreach.py --test              # 1 contact
  python scripts/intelligence/sally/write_outreach.py --force             # re-write already written
  python scripts/intelligence/sally/write_outreach.py --contact-id 1234   # specific contact
  python scripts/intelligence/sally/write_outreach.py --workers 5         # custom concurrency
  python scripts/intelligence/sally/write_outreach.py                     # full run
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
import anthropic
from supabase import create_client, Client

load_dotenv()


# ── Output Schema (parsed from JSON in Opus response) ─────────────────

OUTREACH_SCHEMA = {
    "subject_line": "str — email subject line (warm, scene-setting, 3-8 words, sounds like a friend)",
    "message_body": "str — the full message, 100-250 words, Sally's voice",
    "channel": "str — 'email' or 'text' (based on relationship and comms history)",
    "follow_up_text": "str — a natural text follow-up for 3-5 days later if no response",
    "thank_you_message": "str — a thank-you message to send after they give",
    "internal_notes": "str — 1-2 sentences for Sally: key talking points if they call back",
}


# ── System Prompt ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are writing personal fundraising outreach messages as Sally Steele for Outdoorithm Collective's Come Alive 2026 campaign. These messages go to Sally's inner circle — List A contacts who get a personal email or text BEFORE the broader campaign launches.

YOUR #1 JOB: Sound like Sally texting or emailing a friend. NOT a development officer. NOT a nonprofit pitch. NOT an AI-generated message. If the message sounds "crafted" or "polished" in a generic way, you've failed.

═══════════════════════════════════════════════════════════════
SALLY'S VOICE — STUDY THIS CAREFULLY
═══════════════════════════════════════════════════════════════

Sally writes like this:
- Opens with a scene or moment — puts you in a specific place and time
- Uses vivid, cinematic details: rain on redwoods, kids climbing volcanic boulders, raccoons stealing mac and cheese
- Coins mantras and builds around them: "Camp as it comes," "Leave anyway," "Take up space"
- Uses em dashes (—) naturally for asides and emphasis
- Contrast structures: sets up two worlds to make her point
- Longer sentences than Justin (15-30 words average), but punctuated with short punchy truths
- Sentence fragments for emphasis: "None of it was perfect. All of it was transformative."
- Uses "Justin and I" as a natural pairing
- Minister's cadence: story, reflection, invitation
- Community-centered: names people, credits contributions
- "Join us" and "be part of this" framing, not "please donate"
- Uses camper quotes as her most powerful evidence
- Emotionally grounded — shares real struggle but always in service of a larger truth
- Never sounds like a pitch deck or a CRM template
- Words she favors: "belonging," "sacred," "tending," "chosen family," "vessels for transformation"
- Words she NEVER uses: "generous," "charitable," "donation opportunity," "transformative impact"

Here's what a REAL message from Sally sounds like:

---
Hey [Name],

Last month we pulled into a campsite at 11pm — three kids, pitch black, raccoon immediately jumped in our van. Justin chased it into the woods. I laughed until I cried.

The next morning I woke up to rain dripping off redwoods and a stillness I hadn't felt in months. That's what happens when you leave anyway.

We have 8 camping trips planned this season through Outdoorithm Collective. Pinnacles, Yosemite, Lassen, Joshua Tree. Each one brings together families who've never slept in a tent with families who grew up doing it. What happens around the campfire is hard to describe — but a dad told us feeling safe in the woods for the first time "changed the narrative."

Justin and I are reaching out to people we love before the broader campaign launches. Each trip costs about $10K to run. We've raised $45K from grants already, and a supporter is matching the first $20K.

Would love to have you be part of this.

Sally
---

Notice: opens with a scene, not a pitch. Uses a camper quote. The ask is an invitation, not a request. Warm, specific, real.

═══════════════════════════════════════════════════════════════
CAMPAIGN CONTEXT
═══════════════════════════════════════════════════════════════

Outdoorithm Collective is a 501(c)(3) outdoor equity nonprofit co-founded by Sally and Justin Steele.
Mission: Making outdoor recreation accessible to underserved communities through guided camping expeditions.

Come Alive 2026:
- Goal: $120K. 8 camping trips this season plus $40K in shared gear.
- Math: 8 trips. ~$10K each to run. Plus $40K in shared gear. $120K total.
- Already committed: $45K from grants and early supporters
- Gap: $75K from friends and community
- Match: $20K dollar-for-dollar from an early supporter
- Launch: ~March 10, 2026
- Close: ~March 28, 2026 (before Joshua Tree March 30)

Impact language:
- $500 = one family comes alive
- $1,000 = two families at the campfire
- $2,500 = a quarter of a trip funded
- $5,000 = half a trip. Rest, community, grit for 10 families
- $10,000 = a full trip. 10-12 families come alive together

═══════════════════════════════════════════════════════════════
THE THREE CAMPAIGN PERSONAS
═══════════════════════════════════════════════════════════════

PERSONA 1: THE BELIEVER
"I'm in because Sally asked."
- Close friends, family, co-founders, OC trip participants
- Giving is relationship-first. They'd support anything Sally builds
- Channel: Personal text or casual email
- Tone: Warm, scene-setting, insider language. No selling needed.
- Lead frame: A specific moment from a trip or from their shared history. Then: "Would love to have you be part of this."
- Story: Whichever they've personally witnessed, or skip. The relationship IS the story.
- Ask: Anchor to capacity tier. They'll stretch for Sally. Don't underask.
- What NOT to do: Don't over-explain OC's mission to people who already know it.

PERSONA 2: THE IMPACT PROFESSIONAL
"This model works. I want to support it."
- Senior social impact executives, foundation leaders, CSR directors, philanthropy professionals
- They evaluate nonprofits professionally. See OC through model/outcomes lens
- Channel: Personal email
- Tone: Warm but substantive. Respect their expertise.
- Lead frame: A camper's moment of transformation, then the model. "8 trips. ~$10K each."
- Story: Stories showing systemic change. Carl, the "safe in the woods" dad, Joy
- Ask: Mid-to-high. Frame as investment: "Your $5K funds half a trip."
- Match: Lead with it. They understand leverage.

PERSONA 3: THE NETWORK PEER
"My people support this. I should too."
- Sally's professional network, REI Path Ahead community, outdoor industry contacts
- Know Sally, respect her, but relationship is primarily professional
- Channel: Campaign email or personal email
- Tone: Sally's natural voice. Personal, warm, scene-setting
- Lead frame: A campfire moment that captures the magic + social proof
- Story: Human stories anyone connects to — Valencia, the 8-year-old, families arriving as strangers

═══════════════════════════════════════════════════════════════
EXECUTION MATRIX: PERSONA × LIFECYCLE
═══════════════════════════════════════════════════════════════

Opener inserts:

| | New to OC | Prior Donor | Lapsed |
|--|--|--|--|
| Believer | "Something I want to share with you." + scene from recent trip | "Your support last year went straight to [trip]. Meant everything. Here's what's next." | "Been a while since we've talked about OC. It's grown. Would love to catch you up." |
| Impact Pro | "I don't think you've seen what OC has become. If you want in this season, here's what's happening." | "Your gift last year went toward [trip]. [X] families. Building on that with 8 trips." | "You supported OC before. Reaching out personally because we're doing something bigger." |
| Network Peer | "Something I've been building that I want to tell you about." | "Thanks for backing us last year. [Impact]. 8 trips this season." | "You supported OC before. Wanted to reach out personally." |

Thank-you frames:

| Persona | Base Thank-you | + Parental Empathy | + Justice/Equity | + Community |
|--|--|--|--|--|
| Believer | "This means the world to me. Thank you." | Same (relationship is the frame) | Same | Same |
| Impact Pro | "Your $X is going toward [trip]. [X] families." | "...families like yours." | "You're helping build what public lands should have been." | "You're funding a community that will outlast any program." |
| Network Peer | "You showed up. That matters." | "Your gift sends [X] families to the campfire." | "You're funding spaces where every family belongs." | "You just joined something real." |

═══════════════════════════════════════════════════════════════
STORY BANK
═══════════════════════════════════════════════════════════════

| Story | Key Moment | Best For |
|-------|-----------|----------|
| valencia | Mom from Alabama, first time outdoors. Afraid to sleep without locked door → most restorative sleep in years. Daughter running barefoot, no fear, just joy. | parental_empathy, universal. The Come Alive story. |
| carl | "There are very few times as a Black man that I feel comfortable in the woods. Being able to feel safe camping changes the narrative." | justice_equity, mission_alignment. Systemic change. |
| 8_year_old | After first camping trip, asked mom to "go home to the campfire." Didn't mean the campsite. Meant the feeling. | parental_empathy, community_belonging. |
| michelle_latting | "It feels like core aspects of who we are as individuals and as a family are *made* on these trips." | parental_empathy, community_belonging. Family transformation. |
| joy | "This is a community that will never fail me." | community_belonging, relationship. Found community. |
| aftan | "The grief still exists, but it feels a bit lighter." Processing cousin's death on a trip. | community_belonging, mission_alignment. Healing. |
| stuck_van | Campervan got stuck on river bank. Engineer, doctor, social worker, actor — everyone grabbed shovels. Flexed like they'd won the championship. | community, shared_labor. |
| uncle_john | Eliza started calling another dad "uncle" after meeting him 48 hours earlier. He was family. | community_belonging, chosen_family. |
| sally_disney | "449 nights at Humboldt for the price of three at Disney." | peer_identity (value/ROI). |
| skip | No story. The relationship carries the ask. | Believers who know OC deeply. |

═══════════════════════════════════════════════════════════════
DONOR PSYCHOLOGY (use naturally, don't force)
═══════════════════════════════════════════════════════════════

- Identity circuit: "You're the kind of person who..." is 2x more powerful than shared identity alone
- Warm glow: Frame giving as joining something alive, not filling a gap
- Endowed progress: Campaign is already at $45K+. Mention this
- Social proof: "Several friends have already committed" (if true for their cohort)
- Matching: "$20K match means your gift doubles." Leverage framing
- Decision friction: Make it easy. One link, "just reply," "happy to talk"
- Identifiable victim: One family's story > statistics. Always.
- Loss aversion: "Don't miss being part of this founding season" > "Please donate"

═══════════════════════════════════════════════════════════════
ABOUT SALLY STEELE
═══════════════════════════════════════════════════════════════

- Co-founder, Outdoorithm Collective (501c3 outdoor equity nonprofit)
- Co-founder, Outdoorithm (outdoor tech platform: campsite tools, community app)
- REI Path Ahead Ventures fellow
- Louisville Institute grantee
- Minister / community builder
- Based in Northern California (Oakland area)
- Married to Justin Steele (co-founder, handles tech/systems)
- Four daughters
- Designs the OC trip experiences

═══════════════════════════════════════════════════════════════
OUTPUT INSTRUCTIONS
═══════════════════════════════════════════════════════════════

For each contact, produce a JSON object with these fields:

1. subject_line: Email subject line. Warm, scene-setting or relational, 3-8 words. Examples: "something I want to share," "8 trips this year," "the campfire is calling." For texts, use empty string "".

2. message_body: The full outreach message. 100-250 words. In Sally's voice. Must include:
   - A scene-setting opener OR a warm relational moment
   - The campaign context (trips, cost, match), woven into the story, not listed
   - A soft invitation. "Would love to have you be part of this" or similar
   - NO explicit dollar amount in the first touch (unless they're a prior donor and you're referencing their past gift)
   - End with "Sally" (not "Best, Sally" or "Sincerely")
   - If channel is text, keep it under 100 words and more casual
   - Em dashes (—) are fine — they're part of Sally's natural voice

3. channel: "email" or "text". Use "text" only if:
   - The contact has SMS communication history
   - Familiarity >= 3 and the relationship feels text-appropriate
   - Otherwise default to "email"

4. follow_up_text: A text message for 3-5 days later if no response. Under 50 words. Very casual. "Hey, did you see my note about OC? No pressure, just wanted to make sure it landed."

5. thank_you_message: What to send after they give. Under 75 words. Identity-affirming, not generic. Use the thank-you frame matrix.

6. internal_notes: 1-2 sentences for Sally. What to emphasize if they call back, any risks or opportunities, suggested conversation topics.

CRITICAL RULES:
- Output ONLY valid JSON. No markdown, no explanation, no preamble. Just the JSON object.
- The message must sound like it came from Sally's phone, not from a CRM.
- Reference specific shared history from communication_history if available.
- If they're a prior OC donor, acknowledge it and reference the impact.
- If they have kids and the parental_empathy flag is set, lean into family stories.
- Never reference data you shouldn't have (FEC records, home value, etc.).
- Personalize with their work, shared experiences, or recent conversations. Not wealth signals."""


# ── Select columns ────────────────────────────────────────────────────

SELECT_COLS = (
    "id, first_name, last_name, headline, summary, company, position, "
    "connected_on, city, state, familiarity_rating, "
    "ai_tags, shared_institutions, "
    "ai_capacity_tier, ai_capacity_score, ai_outdoorithm_fit, "
    "fec_donations, real_estate_data, "
    "comms_last_date, comms_thread_count, communication_history, "
    "comms_closeness, comms_momentum, comms_summary, "
    "comms_meeting_count, comms_last_meeting, "
    "enrich_employment, enrich_education, "
    "oc_engagement, "
    "ask_readiness, campaign_2026"
)


# ── Helpers ────────────────────────────────────────────────────────────

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


def summarize_comms_detailed(contact: dict) -> str:
    """Detailed communication history for personal outreach context."""
    last_date = contact.get("comms_last_date")
    thread_count = contact.get("comms_thread_count", 0)
    closeness = contact.get("comms_closeness")
    momentum = contact.get("comms_momentum")
    meeting_count = contact.get("comms_meeting_count", 0)

    if not last_date and not thread_count and not meeting_count:
        return "No communication history"

    parts = []
    if closeness:
        parts.append(f"Closeness: {closeness}")
    if momentum:
        parts.append(f"Momentum: {momentum}")
    if last_date:
        parts.append(f"Last contact: {last_date}")
    if thread_count:
        parts.append(f"Total threads/events: {thread_count}")

    cs = parse_jsonb(contact.get("comms_summary"))
    if cs and isinstance(cs, dict):
        channels = cs.get("channels", {})
        ch_parts = []
        for ch_name in ["email", "linkedin", "sms", "calendar"]:
            ch = channels.get(ch_name)
            if not ch:
                continue
            ch_threads = ch.get("threads", 0)
            ch_bidir = ch.get("bidirectional", 0)
            ch_last = (ch.get("last_date", "") or "")[:10]
            label = {"email": "email", "linkedin": "LinkedIn", "sms": "SMS",
                     "calendar": "meetings"}.get(ch_name, ch_name)
            if ch_name == "calendar":
                detail = f"{ch_threads} {label}"
                detail += f" (last: {ch_last})" if ch_last else ""
            else:
                detail = f"{ch_threads} {label} ({ch_bidir} bidirectional"
                detail += f", last: {ch_last})" if ch_last else ")"
            ch_parts.append(detail)
        if ch_parts:
            parts.append(f"Channels: {'; '.join(ch_parts)}")

        chrono = cs.get("chronological_summary")
        if chrono:
            parts.append(f"Timeline: {chrono}")

    comms = parse_jsonb(contact.get("communication_history"))
    if comms and isinstance(comms, dict):
        summary = comms.get("relationship_summary", "")
        if summary:
            parts.append(f"Relationship: {summary}")

        # Extract recent thread subjects
        accounts = comms.get("accounts", {})
        recent_threads = []
        for acct_data in (accounts.values() if isinstance(accounts, dict) else []):
            if isinstance(acct_data, dict):
                threads = acct_data.get("threads", [])
                for t in (threads if isinstance(threads, list) else []):
                    if isinstance(t, dict):
                        subject = t.get("subject", "")
                        date = t.get("last_date", t.get("date", ""))
                        channel = t.get("channel", "")
                        if subject:
                            recent_threads.append((date, subject, channel))

        if recent_threads:
            recent_threads.sort(reverse=True)
            top8 = recent_threads[:8]
            thread_strs = [f'"{subj}" ({date}, {ch})' if ch else f'"{subj}" ({date})'
                           for date, subj, ch in top8]
            parts.append(f"Recent threads:\n    " + "\n    ".join(thread_strs))

    return "\n  ".join(parts)


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
        notes = inst.get("notes", "")
        sally_period = inst.get("sally_period", inst.get("justin_period", ""))
        contact_period = inst.get("contact_period", "")
        line = f"{name} ({itype})"
        if sally_period and contact_period:
            line += f" — Sally: {sally_period}, Contact: {contact_period}"
        if temporal:
            line += " [TEMPORAL OVERLAP]"
        if depth:
            line += f" [{depth}]"
        if notes:
            line += f" — {notes}"
        parts.append(f"  - {line}")
    return "\n".join(parts) if parts else "No shared institutions"


def summarize_employment(employment_data) -> str:
    data = parse_jsonb(employment_data)
    if not data or not isinstance(data, list):
        return "No employment history"
    positions = []
    for job in data[:5]:
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


def build_contact_context(contact: dict) -> str:
    """Assemble rich per-contact context for the personal outreach prompt."""
    parts = []

    # Contact basics
    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    parts.append(f"CONTACT: {name}")
    familiarity = contact.get("familiarity_rating", 0) or 0
    parts.append(f"Familiarity Rating: {familiarity}/4 (Sally's personal assessment)")

    if contact.get("position") or contact.get("company"):
        parts.append(f"Current Role: {contact.get('position', '?')} at {contact.get('company', '?')}")
    if contact.get("headline"):
        parts.append(f"Headline: {contact['headline']}")
    if contact.get("city") or contact.get("state"):
        loc = ", ".join(filter(None, [contact.get("city"), contact.get("state")]))
        parts.append(f"Location: {loc}")
    if contact.get("summary"):
        parts.append(f"LinkedIn About: {contact['summary'][:600]}")
    parts.append("")

    # Scaffold data (from campaign_2026)
    c2026 = parse_jsonb(contact.get("campaign_2026")) or {}
    scaffold = c2026.get("scaffold", {})
    if scaffold:
        parts.append("═══ CAMPAIGN SCAFFOLD ═══")
        parts.append(f"Persona: {scaffold.get('persona', '?')}")
        parts.append(f"Campaign List: {scaffold.get('campaign_list', '?')}")
        parts.append(f"Capacity Tier: {scaffold.get('capacity_tier', '?')}")
        parts.append(f"Primary Ask Amount: ${scaffold.get('primary_ask_amount', '?'):,}" if isinstance(scaffold.get('primary_ask_amount'), (int, float)) else f"Primary Ask Amount: {scaffold.get('primary_ask_amount', '?')}")
        parts.append(f"Primary Motivation: {scaffold.get('primary_motivation', '?')}")
        flags = scaffold.get("motivation_flags", [])
        if flags:
            parts.append(f"All Motivation Flags: {', '.join(flags)}")
        parts.append(f"Lifecycle Stage: {scaffold.get('lifecycle_stage', '?')}")
        parts.append(f"Lead Story: {scaffold.get('lead_story', '?')}")
        parts.append(f"Story Reasoning: {scaffold.get('story_reasoning', '?')}")
        parts.append(f"Opener Insert: {scaffold.get('opener_insert', '?')}")
        parts.append(f"Personalization Sentence: {scaffold.get('personalization_sentence', '?')}")
        parts.append(f"Thank-you Variant: {scaffold.get('thank_you_variant', '?')}")
        parts.append(f"Text Follow-up: {scaffold.get('text_followup', '?')}")
        parts.append(f"Persona Reasoning: {scaffold.get('persona_reasoning', '?')}")
    parts.append("")

    # Ask readiness data
    ar = parse_jsonb(contact.get("ask_readiness"))
    if ar and isinstance(ar, dict):
        oc = ar.get("outdoorithm_fundraising", {})
        if oc:
            parts.append("═══ ASK READINESS ═══")
            parts.append(f"Score: {oc.get('score', '?')}/100")
            parts.append(f"Tier: {oc.get('tier', '?')}")
            parts.append(f"Approach: {oc.get('recommended_approach', '?')}")
            parts.append(f"Ask Range: {oc.get('suggested_ask_range', '?')}")
            pa = oc.get("personalization_angle", "")
            if pa:
                parts.append(f"Personalization Angle: {pa}")
            rf = oc.get("receiver_frame", "")
            if rf:
                parts.append(f"Receiver Frame: {rf}")
            reasoning = oc.get("reasoning", "")
            if reasoning:
                parts.append(f"Reasoning: {reasoning}")
    parts.append("")

    # OC engagement
    oc_summary = summarize_oc_engagement(contact.get("oc_engagement"))
    parts.append(f"OC Engagement: {oc_summary}")
    parts.append("")

    # Communication history (DETAILED — critical for personal outreach)
    parts.append("═══ COMMUNICATION HISTORY (use this for personalization) ═══")
    parts.append(f"  {summarize_comms_detailed(contact)}")
    parts.append("")

    # Shared institutions
    institutions = parse_jsonb(contact.get("shared_institutions"))
    parts.append(f"Shared Institutions:\n{summarize_shared_institutions(institutions)}")

    # Employment & education
    parts.append(f"Employment:\n{summarize_employment(contact.get('enrich_employment'))}")
    parts.append(f"Education:\n{summarize_education(contact.get('enrich_education'))}")

    return "\n".join(parts)


# ── Main Writer ──────────────────────────────────────────────────────

class PersonalOutreachWriter:
    MODEL = "claude-opus-4-6"

    def __init__(self, test_mode=False, force=False, contact_id=None, workers=3):
        self.test_mode = test_mode
        self.force = force
        self.contact_id = contact_id
        self.workers = workers
        self.supabase: Optional[Client] = None
        self.anthropic: Optional[anthropic.Anthropic] = None
        self.written_ids: list[int] = []
        self.stats = {
            "processed": 0,
            "by_channel": {"email": 0, "text": 0},
            "errors": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        if not anthropic_key:
            print("ERROR: Missing ANTHROPIC_API_KEY")
            return False

        self.supabase = create_client(url, key)
        self.anthropic = anthropic.Anthropic(api_key=anthropic_key)
        print("Connected to Supabase and Anthropic")
        return True

    def get_contacts(self) -> list[dict]:
        """Fetch List A contacts from sally_contacts that have been scaffolded."""
        # Specific contact ID
        if self.contact_id:
            page = (
                self.supabase.table("sally_contacts")
                .select(SELECT_COLS)
                .eq("id", self.contact_id)
                .execute()
            ).data
            return page or []

        # Fetch all contacts with campaign_2026 scaffold data
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                self.supabase.table("sally_contacts")
                .select(SELECT_COLS)
                .not_.is_("campaign_2026", "null")
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

        # Filter to List A contacts only
        list_a_contacts = []
        for c in all_contacts:
            c2026 = parse_jsonb(c.get("campaign_2026"))
            if not c2026 or not isinstance(c2026, dict):
                continue
            scaffold = c2026.get("scaffold", {})
            if not scaffold:
                continue
            if scaffold.get("campaign_list") == "A":
                list_a_contacts.append(c)

        # Filter out already written (unless --force)
        if not self.force:
            filtered = []
            for c in list_a_contacts:
                c2026 = parse_jsonb(c.get("campaign_2026"))
                if not c2026 or not isinstance(c2026, dict) or "personal_outreach" not in c2026:
                    filtered.append(c)
            list_a_contacts = filtered

        # Apply test limit
        if self.test_mode:
            list_a_contacts = list_a_contacts[:1]

        return list_a_contacts

    def write_outreach(self, contact: dict) -> Optional[dict]:
        """Call Claude Opus 4.6 to write personal outreach for a single contact."""
        context = build_contact_context(contact)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.anthropic.messages.create(
                    model=self.MODEL,
                    max_tokens=2048,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": context}],
                )

                # Track tokens
                if response.usage:
                    self.stats["input_tokens"] += response.usage.input_tokens
                    self.stats["output_tokens"] += response.usage.output_tokens

                # Extract text content
                text = ""
                for block in response.content:
                    if block.type == "text":
                        text += block.text

                if not text.strip():
                    print(f"    Warning: Empty response from Opus")
                    return None

                # Parse JSON from response — strip any markdown fencing
                cleaned = text.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.split("\n")
                    start = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith("```"):
                            start = i + 1
                            break
                    end = len(lines)
                    for i in range(len(lines) - 1, start - 1, -1):
                        if lines[i].strip().startswith("```"):
                            end = i
                            break
                    cleaned = "\n".join(lines[start:end])

                result = json.loads(cleaned)

                # Validate required fields
                required = ["subject_line", "message_body", "channel",
                            "follow_up_text", "thank_you_message", "internal_notes"]
                for field in required:
                    if field not in result:
                        print(f"    Warning: Missing field '{field}' in response")
                        return None

                # Validate channel
                if result["channel"] not in ("email", "text"):
                    result["channel"] = "email"

                return result

            except json.JSONDecodeError as e:
                print(f"    JSON parse error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"    Raw response: {text[:500]}...")
                    return None
            except anthropic.RateLimitError:
                wait = 2 ** (attempt + 2)  # 4, 8, 16 seconds
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            except anthropic.APIError as e:
                print(f"    API error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
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
            return {k: PersonalOutreachWriter._strip_null_bytes(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [PersonalOutreachWriter._strip_null_bytes(v) for v in obj]
        return obj

    def save_outreach(self, contact_id: int, existing_c2026: object,
                      result: dict) -> bool:
        """Save the personal outreach to campaign_2026 JSONB, preserving other keys."""
        c2026 = {}
        if existing_c2026 and isinstance(existing_c2026, dict):
            c2026 = dict(existing_c2026)
        c2026["personal_outreach"] = self._strip_null_bytes(result)
        c2026["outreach_written_at"] = datetime.now(timezone.utc).isoformat()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.supabase.table("sally_contacts").update({
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
        """Process a single contact: write outreach + save."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        contact_id = contact["id"]

        result = self.write_outreach(contact)
        if result is None:
            self.stats["errors"] += 1
            print(f"  ERROR [{contact_id}] {name}: Failed to write outreach")
            return False

        existing_c2026 = parse_jsonb(contact.get("campaign_2026"))
        if self.save_outreach(contact_id, existing_c2026, result):
            self.stats["processed"] += 1
            self.written_ids.append(contact_id)
            channel = result.get("channel", "email")
            if channel in self.stats["by_channel"]:
                self.stats["by_channel"][channel] += 1

            # Display
            scaffold = (existing_c2026 or {}).get("scaffold", {})
            persona = scaffold.get("persona", "?")
            ask_amt = scaffold.get("primary_ask_amount", "?")

            # Color-coded channel
            channel_colors = {"email": "\033[94m", "text": "\033[92m"}
            reset = "\033[0m"
            color = channel_colors.get(channel, "")

            print(f"  [{contact_id}] {name}: {color}{channel}{reset} | "
                  f"{persona} | ${ask_amt:,}" if isinstance(ask_amt, (int, float)) else
                  f"  [{contact_id}] {name}: {color}{channel}{reset} | {persona} | {ask_amt}")
            print(f"    Subject: {result.get('subject_line', '')}")
            print(f"    Body ({len(result.get('message_body', '').split())} words): "
                  f"{result.get('message_body', '')[:120]}...")
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
        print(f"Found {total} List A contacts for personal outreach (Sally's network)")

        if total == 0:
            print("Nothing to do — all List A contacts already have personal outreach (use --force to re-write)")
            return True

        mode_str = "TEST" if self.test_mode else "FULL"
        print(f"\n--- {mode_str} MODE: Writing outreach for {total} contacts with {self.workers} workers ---\n")

        if self.test_mode or total <= 3:
            # Sequential for test mode or very small batches
            for c in contacts:
                self.process_contact(c)
        else:
            # Concurrent with low workers (quality calls)
            failed = []
            contact_by_future = {}

            with ThreadPoolExecutor(max_workers=self.workers) as executor:
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

                    if done_count % 5 == 0 or done_count == total:
                        elapsed = time.time() - start_time
                        print(f"\n--- Progress: {self.stats['processed']}/{total} "
                              f"(email={self.stats['by_channel']['email']}, "
                              f"text={self.stats['by_channel']['text']}, "
                              f"err={self.stats['errors']}) "
                              f"[{elapsed:.0f}s] ---\n")

            # Retry failed contacts sequentially
            if failed:
                print(f"\n--- RETRY: {len(failed)} failed contacts sequentially ---\n")
                self.stats["errors"] = 0
                time.sleep(3)
                for c in failed:
                    self.process_contact(c)

        elapsed = time.time() - start_time
        self.print_summary(elapsed)

        # Print all messages for review
        if not self.test_mode:
            self.print_all_messages()

        return self.stats["errors"] < max(total * 0.1, 1)

    def print_all_messages(self):
        """Print all written messages for review."""
        print("\n" + "=" * 80)
        print("ALL PERSONAL OUTREACH MESSAGES (SALLY'S NETWORK)")
        print("=" * 80)

        all_contacts = []
        page_size = 1000
        offset = 0
        while True:
            query = (
                self.supabase.table("sally_contacts")
                .select("id, first_name, last_name, campaign_2026")
                .not_.is_("campaign_2026", "null")
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

        count = 0
        for c in all_contacts:
            c2026 = parse_jsonb(c.get("campaign_2026"))
            if not c2026 or not isinstance(c2026, dict):
                continue
            scaffold = c2026.get("scaffold", {})
            outreach = c2026.get("personal_outreach", {})
            if not outreach or scaffold.get("campaign_list") != "A":
                continue

            count += 1
            name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()

            print(f"\n{'─' * 60}")
            print(f"  {count}. {name}")
            print(f"  Channel: {outreach.get('channel', '?')} | "
                  f"Persona: {scaffold.get('persona', '?')} | "
                  f"Ask: ${scaffold.get('primary_ask_amount', '?'):,}" if isinstance(scaffold.get('primary_ask_amount'), (int, float)) else
                  f"  Channel: {outreach.get('channel', '?')} | "
                  f"Persona: {scaffold.get('persona', '?')} | "
                  f"Ask: {scaffold.get('primary_ask_amount', '?')}")
            print(f"{'─' * 60}")

            if outreach.get("subject_line"):
                print(f"  Subject: {outreach['subject_line']}")
            print(f"\n{outreach.get('message_body', '[No message body]')}")
            print(f"\n  --- Follow-up text (3-5 days) ---")
            print(f"  {outreach.get('follow_up_text', '[None]')}")
            print(f"\n  --- Thank-you ---")
            print(f"  {outreach.get('thank_you_message', '[None]')}")
            print(f"\n  --- Internal notes ---")
            print(f"  {outreach.get('internal_notes', '[None]')}")

        print(f"\n{'=' * 80}")
        print(f"Total messages: {count}")
        print(f"{'=' * 80}")

    def print_summary(self, elapsed: float):
        s = self.stats
        # Anthropic pricing: Opus 4.6 — $15/M input, $75/M output
        input_cost = s["input_tokens"] * 15.0 / 1_000_000
        output_cost = s["output_tokens"] * 75.0 / 1_000_000
        total_cost = input_cost + output_cost

        print("\n" + "=" * 60)
        print("COME ALIVE 2026 — PERSONAL OUTREACH SUMMARY (SALLY'S NETWORK)")
        print("=" * 60)
        print(f"  Messages written:      {s['processed']}")
        print(f"  Errors:                {s['errors']}")
        print()
        print("  CHANNEL:")
        print(f"    Email:               {s['by_channel']['email']}")
        print(f"    Text:                {s['by_channel']['text']}")
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
        description="Write personal outreach messages for Sally's List A contacts using Claude Opus 4.6"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only 1 contact for validation")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-write contacts that already have outreach")
    parser.add_argument("--contact-id", type=int, default=None,
                        help="Write outreach for a specific contact by ID")
    parser.add_argument("--workers", "-w", type=int, default=3,
                        help="Number of concurrent workers (default: 3)")
    args = parser.parse_args()

    writer = PersonalOutreachWriter(
        test_mode=args.test,
        force=args.force,
        contact_id=args.contact_id,
        workers=args.workers,
    )
    success = writer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
