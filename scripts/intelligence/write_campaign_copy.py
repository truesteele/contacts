#!/usr/bin/env python3
"""
Come Alive 2026 — Campaign Copy Writer (GPT-5 mini)

Generates personalized text follow-ups, thank-you messages, and pre-email notes
for Lists B-D contacts (~175) using GPT-5 mini structured output. These are the
campaign copy variants that personalize the 3-email sequence for each contact.

Follows the exact pattern of scaffold_campaign.py.

Usage:
  python scripts/intelligence/write_campaign_copy.py --test              # 1 contact
  python scripts/intelligence/write_campaign_copy.py --batch 50          # 50 contacts
  python scripts/intelligence/write_campaign_copy.py --workers 100       # custom concurrency
  python scripts/intelligence/write_campaign_copy.py --force             # re-write already done
  python scripts/intelligence/write_campaign_copy.py --contact-id 1234   # specific contact
  python scripts/intelligence/write_campaign_copy.py                     # full run
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

class ThankYouChannel(str, Enum):
    text = "text"
    email = "email"

class CampaignCopy(BaseModel):
    pre_email_note: Optional[str] = Field(
        default=None,
        description="A brief personal note sent BEFORE the campaign emails, ONLY for prior_donor or lapsed lifecycle stages. Should reference their past gift and what it funded. None/null for new contacts."
    )
    text_followup_opener: str = Field(
        description="Text follow-up for Days 2-5 after Email 1 if they opened but didn't act. Short, casual, in Justin's voice. Under 40 words."
    )
    text_followup_milestone: str = Field(
        description="Text follow-up for Days 10-14 with a progress/milestone update. Mentions campaign progress and match. Under 50 words."
    )
    thank_you_message: str = Field(
        description="Identity-affirming thank-you message sent within 24 hours of their gift. Uses 'You're the kind of person who...' framing, not generic gratitude. Under 60 words."
    )
    thank_you_channel: ThankYouChannel = Field(
        description="Channel for the thank-you: 'text' for believers/close contacts, 'email' for most campaign contacts"
    )
    email_sequence: list[int] = Field(
        description="Which emails in the 3-email sequence this contact receives. [1, 2, 3] for most new contacts. Prior donors may skip Email 2 or 3 if they've already been personally engaged."
    )


# ── System Prompt ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a campaign copy writer for Outdoorithm Collective's Come Alive 2026 fundraising campaign. Your job is to write personalized campaign copy variants — text follow-ups, thank-you messages, and pre-email notes — for each contact.

These contacts are on Lists B-D. They receive the 3-email campaign sequence (not personal outreach). Your copy personalizes the touch points around those emails.

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
- Launch: ~February 26, 2026
- Close: ~March 17, 2026 (before Joshua Tree March 30)

Impact language:
- $500 = one family comes alive
- $1,000 = two families at the campfire
- $2,500 = a quarter of a trip funded
- $5,000 = half a trip — rest, community, grit for 10 families
- $10,000 = a full trip — 10-12 families come alive together

═══════════════════════════════════════════════════════════════
JUSTIN'S VOICE — CRITICAL
═══════════════════════════════════════════════════════════════

Every piece of copy must sound like Justin texting or emailing a friend. NOT a development officer. NOT a nonprofit pitch.

Voice rules:
- Direct, punchy, uses sentence fragments for emphasis
- Em dashes for parenthetical thoughts
- "This keeps happening" as a transition
- "Quick thing" as an opener
- Casual and conversational — sounds like a text from a friend
- Never sounds like a development officer or nonprofit pitch
- 2:1 "you/your" to "we/our" ratio
- Under 200 words for emails, much shorter for texts
- "If you want in" = joining, not saving

BAD examples (too polished/corporate):
- "We are grateful for your consideration of supporting our mission"
- "Your generous contribution will help us make a difference"
- "Thank you for your charitable gift to Outdoorithm Collective"

GOOD examples (Justin's actual voice):
- "Hey — did you see my note about OC? No pressure, just wanted to make sure it landed."
- "Quick update — we're at $X toward $100K. Match is still live."
- "Means the world. Thank you."
- "You're the kind of person who shows up."

═══════════════════════════════════════════════════════════════
THE THREE PERSONAS (determines copy tone)
═══════════════════════════════════════════════════════════════

BELIEVER: "I'm in because Justin asked."
- Close friends, OC engaged. Relationship-first giving.
- Copy tone: Warm, brief, insider language. No selling needed.
- Thank-you: "Means the world. Thank you." — relationship IS the frame.

IMPACT PROFESSIONAL: "This model works. I want to support it."
- Social impact execs, foundation leaders, CSR directors.
- Copy tone: Warm but substantive. Respect their expertise.
- Thank-you: "Your $X is going toward [trip]. [X] families." — impact specifics.

NETWORK PEER: "My people support this. I should too."
- Google colleagues, HBS/HKS classmates, professional network.
- Copy tone: Justin's natural voice — personal, not needy.
- Thank-you: "You're the kind of person who shows up." — identity-affirming.

═══════════════════════════════════════════════════════════════
THANK-YOU FRAME: PERSONA × MOTIVATION FLAG
═══════════════════════════════════════════════════════════════

| Persona | Base Thank-you | + Parental Empathy | + Justice/Equity | + Community |
|--|--|--|--|--|
| Believer | "Means the world. Thank you." | Same — relationship is the frame | Same | Same |
| Impact Pro | "Your $X is going toward [trip]. [X] families." | "…families like yours." | "You're helping build what public lands should have been." | "You're funding a community that will outlast any program." |
| Network Peer | "You're the kind of person who shows up." | "Your gift sends [X] families to the campfire." | "You're funding spaces where every family belongs." | "You just joined something real." |

Use the contact's primary_ask_amount to fill in the $X values. Use impact language:
- $500 = one family
- $1,000 = two families
- $2,500 = a quarter of a trip
- $5,000 = half a trip — 10 families
- $10,000 = a full trip

═══════════════════════════════════════════════════════════════
FOLLOW-UP TIMING & CHANNEL
═══════════════════════════════════════════════════════════════

| | First Follow-up (Days 2-5) | Second Follow-up (Days 10-14) | Thank-you |
|--|--|--|--|
| Believer | Text, 3 days | Text, 7 days | Text within hours |
| Impact Pro | Email, 5-7 days | Text, 10-12 days | Email within 24 hours |
| Network Peer | Text to openers, 3-5 days | Email 2 (automatic) | Email within 24 hours |

═══════════════════════════════════════════════════════════════
TEXT FOLLOW-UP TEMPLATES (adapt, don't copy)
═══════════════════════════════════════════════════════════════

Days 2-5 (opener follow-up):
"Hey [Name] — did you see my note about OC? Happy to chat if you have questions. outdoorithmcollective.org/donate"

Days 10-14 (milestone):
"Quick update — we're at $[X] toward $100K. [X] friends in so far. Match is still live. outdoorithmcollective.org/donate"

Post-gift (if no email reply):
"Hey [Name] — just saw your gift come through. Means the world. Thank you."

Adapt these for each contact — reference their company, title, or specific context where natural. Keep texts SHORT — under 2-3 sentences.

═══════════════════════════════════════════════════════════════
PRE-EMAIL NOTES (PRIOR DONOR / LAPSED ONLY)
═══════════════════════════════════════════════════════════════

ONLY write a pre_email_note if the contact's lifecycle_stage is "prior_donor" or "lapsed". For "new" contacts, this MUST be null.

Prior donor template:
"Hey [Name] — your support last year went straight to [trip/families]. Building on that this season — 10 trips, $100K goal. A friend is matching the first $20K. Wanted you to know before I go wider."

Lapsed template:
"Hey [Name] — been a while. OC is bigger this year — 10 trips planned, $100K goal. Your support back then mattered. Would love to have you in it again."

Adapt with personal context. Keep under 60 words.

═══════════════════════════════════════════════════════════════
EMAIL SEQUENCE ASSIGNMENT
═══════════════════════════════════════════════════════════════

- New contacts: [1, 2, 3] — they get all three campaign emails
- Prior donors: [1, 2, 3] — they still get all three, but with the pre_email_note sent before Email 1
- Lapsed donors: [1, 2, 3] — same as prior donors, pre_email_note sent first

The email sequence is almost always [1, 2, 3]. Only skip emails if there's a strong reason (e.g., a prior donor who's already committed during quiet phase — unlikely for Lists B-D).

═══════════════════════════════════════════════════════════════
DONOR PSYCHOLOGY — IDENTITY-AFFIRMING LANGUAGE
═══════════════════════════════════════════════════════════════

The single most important principle: thank-you messages should affirm WHO THE DONOR IS, not just what they gave.

Identity circuit activation (r=.32 — strongest predictor):
- "You're the kind of person who shows up" > "Thank you for your generous gift"
- "You just funded spaces where every family belongs" > "We appreciate your support"
- "You're helping build what public lands should have been" > "Your donation helps"

The brain's three giving circuits (reward, empathy, identity) cool within hours. Thank-you messages must arrive while the glow is warm.

Warm glow framing — giving as JOINING, not HELPING:
- "You just joined something real" > "Thank you for helping"
- "You're the kind of person who shows up for families" > "Your contribution is valued"

═══════════════════════════════════════════════════════════════
STORY BANK (for enriching follow-ups)
═══════════════════════════════════════════════════════════════

| Story | Key Moment | Best For |
|-------|-----------|----------|
| valencia | Mom from Alabama, first time outdoors. Daughter running barefoot, no fear, just joy. | parental_empathy, universal |
| carl | "Being able to feel safe camping changes the narrative." | justice_equity, mission_alignment |
| 8_year_old | Asked mom to "go home to the campfire." Meant the feeling, not the place. | parental_empathy, community_belonging |
| michelle_latting | "Core aspects of who we are as a family are *made* on these trips." | parental_empathy, community_belonging |
| joy | "This is a community that will never fail me." | community_belonging, relationship |
| dorian | "Something about being outside brings everything back into balance." | peer_identity (burnout/balance) |
| sally_disney | "449 nights at Humboldt for the price of three at Disney." | peer_identity (value/ROI) |

You can weave a brief story reference into the text follow-ups or thank-yous where natural. Don't force it — a short text doesn't need a full story.

═══════════════════════════════════════════════════════════════
OUTPUT INSTRUCTIONS
═══════════════════════════════════════════════════════════════

For each contact, produce a CampaignCopy with ALL fields:

1. pre_email_note — ONLY for prior_donor/lapsed. Must be null for "new" contacts.
2. text_followup_opener — Days 2-5. Short, casual. Reference their name and one personal detail.
3. text_followup_milestone — Days 10-14. Progress update + match. Brief.
4. thank_you_message — Identity-affirming. Uses the persona × motivation flag matrix. Under 60 words.
5. thank_you_channel — "email" for most B-D contacts. "text" only if they have SMS history and are close.
6. email_sequence — Almost always [1, 2, 3].

CRITICAL: Everything must sound like Justin. Casual, direct, personal. NOT like a CRM."""


# ── Select columns ────────────────────────────────────────────────────

SELECT_COLS = (
    "id, first_name, last_name, headline, summary, company, position, "
    "connected_on, city, state, familiarity_rating, "
    "ai_tags, shared_institutions, "
    "fec_donations, real_estate_data, "
    "comms_last_date, comms_thread_count, communication_history, "
    "comms_closeness, comms_momentum, comms_summary, "
    "enrich_employment, enrich_education, "
    "known_donor, nonprofit_board_member, "
    "outdoor_environmental_affinity, outdoor_affinity_evidence, "
    "equity_access_focus, equity_focus_evidence, "
    "oc_engagement, "
    "ask_readiness, campaign_2026"
)


# ── Reuse helpers (same as scaffold_campaign.py) ────────────────────────

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


def summarize_comms_brief(contact: dict) -> str:
    """Brief communication summary for campaign copy context."""
    closeness = contact.get("comms_closeness")
    momentum = contact.get("comms_momentum")
    last_date = contact.get("comms_last_date")
    thread_count = contact.get("comms_thread_count", 0)

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
        parts.append(f"Threads: {thread_count}")

    # Check for SMS history (determines thank-you channel)
    cs = parse_jsonb(contact.get("comms_summary"))
    if cs and isinstance(cs, dict):
        channels = cs.get("channels", {})
        sms = channels.get("sms")
        if sms and sms.get("threads", 0) > 0:
            parts.append(f"Has SMS history ({sms['threads']} threads)")

    # Recent thread subjects from communication_history
    comms = parse_jsonb(contact.get("communication_history"))
    if comms and isinstance(comms, dict):
        summary = comms.get("relationship_summary", "")
        if summary:
            parts.append(f"Relationship: {summary}")

    return "\n  ".join(parts)


def summarize_oc_engagement(oc_data) -> str:
    """Summarize OC engagement for copy context."""
    data = parse_jsonb(oc_data)
    if not data or not isinstance(data, dict):
        return "No OC engagement"
    parts = []
    roles = data.get("crm_roles", [])
    if roles:
        parts.append(f"Roles: {', '.join(roles)}")
    if data.get("is_oc_donor"):
        total = data.get("oc_total_donated", 0)
        last = data.get("oc_last_donation", "")
        parts.append(f"OC Donor: ${total:,.0f} (last: {last})")
    trips = data.get("trips_attended", 0)
    if trips:
        parts.append(f"Trips attended: {trips}")
    return "; ".join(parts) if parts else "No OC engagement"


def summarize_employment_brief(employment_data) -> str:
    """Brief employment summary — just current + 1 prior."""
    data = parse_jsonb(employment_data)
    if not data or not isinstance(data, list):
        return "No employment history"
    positions = []
    for job in data[:3]:
        if not isinstance(job, dict):
            continue
        title = job.get("title", "")
        company = job.get("companyName", job.get("company", ""))
        end = job.get("endDate", "Present")
        line = f"{title} at {company}"
        if end != "Present":
            line += f" (ended {end})"
        positions.append(line)
    return "; ".join(positions) if positions else "No employment history"


def build_contact_context(contact: dict) -> str:
    """Assemble per-contact context for the campaign copy prompt."""
    parts = []

    # Contact basics
    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    parts.append(f"CONTACT: {name}")
    familiarity = contact.get("familiarity_rating", 0) or 0
    parts.append(f"Familiarity: {familiarity}/4")

    if contact.get("position") or contact.get("company"):
        parts.append(f"Role: {contact.get('position', '?')} at {contact.get('company', '?')}")
    if contact.get("headline"):
        parts.append(f"Headline: {contact['headline']}")
    parts.append("")

    # Scaffold data (the critical context)
    c2026 = parse_jsonb(contact.get("campaign_2026"))
    scaffold = c2026.get("scaffold", {}) if c2026 and isinstance(c2026, dict) else {}

    if scaffold:
        parts.append("CAMPAIGN SCAFFOLD:")
        parts.append(f"  Persona: {scaffold.get('persona', '?')}")
        parts.append(f"  Campaign List: {scaffold.get('campaign_list', '?')}")
        parts.append(f"  Capacity Tier: {scaffold.get('capacity_tier', '?')}")
        parts.append(f"  Ask Amount: ${scaffold.get('primary_ask_amount', '?'):,}" if isinstance(scaffold.get('primary_ask_amount'), (int, float)) else f"  Ask Amount: {scaffold.get('primary_ask_amount', '?')}")
        parts.append(f"  Primary Motivation: {scaffold.get('primary_motivation', '?')}")
        flags = scaffold.get("motivation_flags", [])
        if flags:
            parts.append(f"  Motivation Flags: {', '.join(flags)}")
        parts.append(f"  Lifecycle Stage: {scaffold.get('lifecycle_stage', '?')}")
        parts.append(f"  Lead Story: {scaffold.get('lead_story', '?')}")
        opener = scaffold.get("opener_insert", "")
        if opener:
            parts.append(f"  Opener Insert: {opener}")
        personalization = scaffold.get("personalization_sentence", "")
        if personalization:
            parts.append(f"  Personalization: {personalization}")
        thank_you = scaffold.get("thank_you_variant", "")
        if thank_you:
            parts.append(f"  Thank-you Variant: {thank_you}")
        text_fu = scaffold.get("text_followup", "")
        if text_fu:
            parts.append(f"  Text Follow-up (scaffold): {text_fu}")
    parts.append("")

    # Ask readiness summary
    ar = parse_jsonb(contact.get("ask_readiness"))
    if ar and isinstance(ar, dict):
        oc = ar.get("outdoorithm_fundraising", {})
        if oc:
            parts.append(f"Ask Readiness: Score {oc.get('score', '?')}, Tier: {oc.get('tier', '?')}")
            rf = oc.get("receiver_frame", "")
            if rf:
                parts.append(f"  Receiver Frame: {rf}")
            pa = oc.get("personalization_angle", "")
            if pa:
                parts.append(f"  Personalization Angle: {pa}")
    parts.append("")

    # OC engagement
    parts.append(f"OC Engagement: {summarize_oc_engagement(contact.get('oc_engagement'))}")

    # Comms (brief)
    parts.append(f"Communication: {summarize_comms_brief(contact)}")

    # Employment (brief)
    parts.append(f"Employment: {summarize_employment_brief(contact.get('enrich_employment'))}")

    return "\n".join(parts)


# ── Main Copy Writer ──────────────────────────────────────────────────

class CampaignCopyWriter:
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
            "by_tier": {"leadership": 0, "major": 0, "mid": 0, "base": 0, "community": 0},
            "by_lifecycle": {"new": 0, "prior_donor": 0, "lapsed": 0},
            "pre_email_notes": 0,
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
        """Fetch Lists B-D contacts that have scaffold data."""
        # Specific contact ID
        if self.contact_id:
            page = (
                self.supabase.table("contacts")
                .select(SELECT_COLS)
                .eq("id", self.contact_id)
                .execute()
            ).data
            return page or []

        # Fetch all contacts with campaign_2026 data
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                self.supabase.table("contacts")
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

        # Filter to Lists B-D (not A — those got personal outreach)
        campaign_contacts = []
        for c in all_contacts:
            c2026 = parse_jsonb(c.get("campaign_2026"))
            if not c2026 or not isinstance(c2026, dict):
                continue
            scaffold = c2026.get("scaffold")
            if not scaffold or not isinstance(scaffold, dict):
                continue
            campaign_list = scaffold.get("campaign_list", "")
            if campaign_list in ("B", "C", "D"):
                campaign_contacts.append(c)

        # Filter out already-written (unless --force)
        if not self.force:
            filtered = []
            for c in campaign_contacts:
                c2026 = parse_jsonb(c.get("campaign_2026"))
                if not c2026 or not isinstance(c2026, dict) or "campaign_copy" not in c2026:
                    filtered.append(c)
            campaign_contacts = filtered

        # Apply limits
        if self.test_mode:
            campaign_contacts = campaign_contacts[:1]
        elif self.batch_size:
            campaign_contacts = campaign_contacts[:self.batch_size]

        return campaign_contacts

    def write_copy(self, contact: dict) -> Optional[CampaignCopy]:
        """Call GPT-5 mini to generate campaign copy for a contact."""
        context = build_contact_context(contact)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions=SYSTEM_PROMPT,
                    input=context,
                    text_format=CampaignCopy,
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
            return {k: CampaignCopyWriter._strip_null_bytes(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [CampaignCopyWriter._strip_null_bytes(v) for v in obj]
        return obj

    def save_copy(self, contact_id: int, existing_c2026: object,
                  result: CampaignCopy) -> bool:
        """Save campaign copy to campaign_2026 JSONB, preserving other keys."""
        copy_data = result.model_dump(mode="json")

        # Merge with existing campaign_2026 (preserve scaffold, personal_outreach, etc.)
        c2026 = {}
        if existing_c2026 and isinstance(existing_c2026, dict):
            c2026 = dict(existing_c2026)
        c2026["campaign_copy"] = self._strip_null_bytes(copy_data)
        c2026["copy_written_at"] = datetime.now(timezone.utc).isoformat()

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
        """Process a single contact: write copy + save."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        contact_id = contact["id"]

        result = self.write_copy(contact)
        if result is None:
            self.stats["errors"] += 1
            print(f"  ERROR [{contact_id}] {name}: Failed to write copy")
            return False

        existing_c2026 = parse_jsonb(contact.get("campaign_2026"))
        if self.save_copy(contact_id, existing_c2026, result):
            # Update stats
            self.stats["processed"] += 1
            scaffold = {}
            if existing_c2026 and isinstance(existing_c2026, dict):
                scaffold = existing_c2026.get("scaffold", {})
            persona = scaffold.get("persona", "network_peer")
            capacity = scaffold.get("capacity_tier", "base")
            lifecycle = scaffold.get("lifecycle_stage", "new")

            if persona in self.stats["by_persona"]:
                self.stats["by_persona"][persona] += 1
            if capacity in self.stats["by_tier"]:
                self.stats["by_tier"][capacity] += 1
            if lifecycle in self.stats["by_lifecycle"]:
                self.stats["by_lifecycle"][lifecycle] += 1
            if result.pre_email_note:
                self.stats["pre_email_notes"] += 1

            # Color-coded display
            persona_colors = {
                "believer": "\033[92m",
                "impact_professional": "\033[93m",
                "network_peer": "\033[96m",
            }
            reset = "\033[0m"
            color = persona_colors.get(persona, "")

            pre_note = " [pre-email note]" if result.pre_email_note else ""
            print(f"  [{contact_id}] {name}: {color}{persona}{reset} | "
                  f"{capacity} | {lifecycle} | "
                  f"seq={result.email_sequence}{pre_note}")
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
        print(f"Found {total} Lists B-D contacts to write campaign copy")

        if total == 0:
            print("Nothing to do — all contacts already have campaign copy (use --force to re-write)")
            return True

        mode_str = "TEST" if self.test_mode else f"BATCH {self.batch_size}" if self.batch_size else "FULL"
        print(f"\n--- {mode_str} MODE: Writing copy for {total} contacts with {self.workers} workers ---\n")

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
        print("COME ALIVE 2026 — CAMPAIGN COPY SUMMARY")
        print("=" * 60)
        print(f"  Contacts written:      {s['processed']}")
        print(f"  Errors:                {s['errors']}")
        print(f"  Pre-email notes:       {s['pre_email_notes']}")
        print()
        print("  PERSONA DISTRIBUTION:")
        print(f"    Believer:            {s['by_persona']['believer']}")
        print(f"    Impact Professional: {s['by_persona']['impact_professional']}")
        print(f"    Network Peer:        {s['by_persona']['network_peer']}")
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
        description="Write campaign copy variants for Come Alive 2026 Lists B-D (GPT-5 mini)"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only 1 contact for validation")
    parser.add_argument("--batch", "-b", type=int, default=None,
                        help="Process N contacts")
    parser.add_argument("--workers", "-w", type=int, default=150,
                        help="Number of concurrent workers (default: 150)")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-write contacts that already have campaign copy")
    parser.add_argument("--contact-id", type=int, default=None,
                        help="Write copy for a specific contact by ID")
    args = parser.parse_args()

    writer = CampaignCopyWriter(
        test_mode=args.test,
        batch_size=args.batch,
        workers=args.workers,
        force=args.force,
        contact_id=args.contact_id,
    )
    success = writer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
