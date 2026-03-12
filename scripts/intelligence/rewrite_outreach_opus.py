#!/usr/bin/env python3
"""
rewrite_outreach_opus.py
========================
Uses Claude Opus 4.6 to rewrite all List A personal outreach emails
with full campaign context, donor profiles, and communication history.

Usage:
  source .venv/bin/activate
  python -u scripts/intelligence/rewrite_outreach_opus.py --dry-run
  python -u scripts/intelligence/rewrite_outreach_opus.py --contact-id 482 --dry-run
  python -u scripts/intelligence/rewrite_outreach_opus.py              # writes to Supabase
"""

import os
import sys
import json
import argparse
import textwrap
from pathlib import Path
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

MODEL = "claude-opus-4-6"

DOCS = {
    "JUSTIN_EMAIL_PERSONA": ROOT / "docs" / "Justin" / "JUSTIN_EMAIL_PERSONA.md",
    "COME_ALIVE_2026_Campaign": ROOT / "docs" / "Outdoorithm" / "COME_ALIVE_2026_Campaign.md",
}

# Columns to pull from contacts
PROFILE_SELECT = ",".join([
    "id", "first_name", "last_name", "company", "position", "headline", "summary",
    "location_name", "city", "state",
    "email", "personal_email", "work_email",
    # Enriched
    "enrich_current_company", "enrich_current_title", "enrich_employment",
    "enrich_education", "enrich_volunteering", "enrich_board_positions",
    "enrich_volunteer_orgs", "enrich_skills", "enrich_total_experience_years",
    # Donor scoring
    "donor_capacity_score", "donor_propensity_score", "donor_affinity_score",
    "donor_warmth_score", "donor_total_score", "donor_tier",
    "estimated_capacity", "executive_level", "known_donor",
    "past_giving_details", "capacity_indicators",
    # Relationship
    "connection_type", "relationship_notes", "personal_connection_strength",
    "warmth_level", "familiarity_rating",
    # AI analysis
    "ai_tags", "ai_proximity_score", "ai_proximity_tier",
    "ai_capacity_score", "ai_capacity_tier", "ai_outdoorithm_fit",
    # Communication
    "communication_history", "comms_summary", "comms_closeness",
    "comms_momentum", "comms_reasoning",
    "comms_last_date", "comms_thread_count",
    "comms_meeting_count", "comms_last_meeting", "comms_call_count",
    # Campaign
    "campaign_2026",
    # Ask readiness
    "ask_readiness",
    # OC engagement
    "oc_engagement",
    # External
    "fec_donations", "real_estate_data",
    # LinkedIn
    "linkedin_reactions",
])


# ---------------------------------------------------------------------------
# System prompt — loaded once, shared across all contacts
# ---------------------------------------------------------------------------
def build_system_prompt() -> str:
    docs_text = ""
    for name, path in DOCS.items():
        if path.exists():
            docs_text += f"\n\n{'='*80}\n{name}\n{'='*80}\n\n{path.read_text()}"
        else:
            docs_text += f"\n\n[{name}: file not found at {path}]\n"

    return textwrap.dedent("""\
    You are ghostwriting a personal fundraising outreach email from Justin Steele
    to a specific contact. Justin is co-founder of Outdoorithm Collective (OC),
    a nonprofit that brings diverse urban families together on camping trips.

    YOUR JOB: Write a personalized pre-campaign outreach email (subject line +
    message body) that this specific person would receive from Justin before the
    broader email campaign launches. This is a personal invitation from one friend
    to another.

    ============================================================================
    CAMPAIGN FACTS — MUST APPEAR IN EVERY EMAIL
    ============================================================================
    - 8 trips this season (Joshua Tree, Pinnacles, Yosemite, Lassen, and more)
    - Each trip costs about $10K to run
    - Plus $40K in gear so every family shows up equipped
    - $120K for the full season
    - $45K raised from grants and early supporters
    - A friend is matching the first $20K in donations dollar-for-dollar
    - $75K to go

    Every email MUST mention:
    1. The trip count (8 trips)
    2. The gear ($40K in gear)
    3. The total ($120K for the full season)
    4. What's raised ($45K from grants and early supporters)
    5. The match ($20K dollar-for-dollar from a friend)
    6. The gap ($75K to go)

    ============================================================================
    VOICE RULES — NON-NEGOTIABLE
    ============================================================================
    1. NO EM DASHES (—) in the email. Use periods, commas, or sentence breaks.
       WRONG: "Sally and I have 8 trips planned — Joshua Tree, Pinnacles..."
       RIGHT: "Sally and I have 8 trips planned this season. Joshua Tree, Pinnacles..."

    2. Calls are EARNED, not initiated. Never say "let's jump on a call" or
       "I'd love to get on a call." Instead: "Happy to talk if you want to know
       more" or "Happy to tell you more if you're curious."

    3. Use "Would love to count you in" — NOT "Would mean a lot" or "Would mean
       the world." Justin uses "would love to" constructions.

    4. Under 200 words for the message body. Mobile users dominate. Front-load.

    5. No specific dollar amount ask in the first touch. The amount anchors live
       in the conversation, not the first email.

    6. Story first, then math. Emotion creates the impulse, math gives permission.

    7. "If you want in" / "Would love to count you in" = joining frame.
       Never "Would you consider donating" or "Would you be willing to help."

    8. Lead with feeling, not framework. Don't explain "come alive." Let stories
       carry the frame.

    9. Donor-centric language: "you" and "your" at 2:1 ratio over "we/our."

    10. Plain text. No bullet points, no bold, no formatting. Reads like a
        personal email from a friend.

    11. Sign off with just "Justin" — no "Best," no "Sincerely."

    12. Opening: "Hey [FirstName]," for warm relationships, "Hi [FirstName],"
        for less familiar. Never "Dear" or em-dash greetings like "Hey [Name] —"

    13. Don't use "means the world" or "means a lot" anywhere.

    14. Don't say "outdoor equity nonprofit" or "underserved communities."
        Describe what happens on the trips. Let the reader feel it.

    15. Keep the subject line short and lowercase. Examples: "quick thing",
        "8 trips this year", "before I send the big ask"

    ============================================================================
    PERSONALIZATION APPROACH
    ============================================================================
    You'll receive the contact's full profile including:
    - Their job, company, background, education
    - Their communication history with Justin (email threads, meetings, calls)
    - Their ask readiness score, personalization angle, and receiver frame
    - Their OC engagement (have they been on a trip?)
    - Their campaign scaffold (persona, capacity tier, suggested story)
    - Their current draft message (which you are rewriting/improving)

    USE ALL OF THIS to write a message that:
    - Opens with something specific to this person's relationship with Justin
    - References shared context (mutual experiences, past conversations, etc.)
    - Connects their professional identity or values to what OC does
    - Includes the campaign math naturally (not as a list)
    - Closes with a soft invitation

    The message should feel like Justin sat down and wrote this one email to
    this one person. Not like a template with [PERSONALIZATION] slots filled in.

    ============================================================================
    OUTPUT FORMAT
    ============================================================================
    Return ONLY a JSON object with exactly two fields:
    {
      "subject_line": "the subject line here",
      "message_body": "the full email body here"
    }

    Use \\n for newlines in the message body. No markdown, no explanation,
    no commentary. Just the JSON object.
    """) + docs_text


# ---------------------------------------------------------------------------
# Build per-contact user prompt
# ---------------------------------------------------------------------------
def build_contact_prompt(contact: dict) -> str:
    c = contact
    campaign = c.get("campaign_2026") or {}
    scaffold = campaign.get("scaffold") or {}
    outreach = campaign.get("personal_outreach") or {}
    ask = c.get("ask_readiness") or {}
    oc = c.get("oc_engagement") or {}
    comms = c.get("communication_history") or {}
    comms_sum = c.get("comms_summary") or {}

    # Format communication threads
    threads_text = ""
    for t in (comms.get("threads") or []):
        threads_text += (
            f"  - [{t.get('date','')}] {t.get('subject','(no subject)')}\n"
            f"    Direction: {t.get('direction','')}, Messages: {t.get('message_count','')}\n"
            f"    Summary: {t.get('summary','')}\n\n"
        )
    if not threads_text:
        threads_text = "  (No email threads on record)\n"

    # Format ask readiness
    ask_oc = ask.get("outdoorithm_fundraising") or {}

    sections = []

    sections.append(f"""
============================================================
CONTACT: {c.get('first_name','')} {c.get('last_name','')} (ID: {c.get('id','')})
============================================================

BASIC INFO
  Name: {c.get('first_name','')} {c.get('last_name','')}
  Company: {c.get('company','')}
  Position: {c.get('position','')}
  Headline: {c.get('headline','')}
  Location: {c.get('city','')}, {c.get('state','')} ({c.get('location_name','')})
  Total experience: {c.get('enrich_total_experience_years','')} years

RELATIONSHIP WITH JUSTIN
  Connection type: {c.get('connection_type','')}
  Warmth level: {c.get('warmth_level','')}
  Familiarity rating: {c.get('familiarity_rating','')}/4
  Personal connection strength: {c.get('personal_connection_strength','')}
  Relationship notes: {c.get('relationship_notes','(none)')}

COMMUNICATION HISTORY
  Closeness: {c.get('comms_closeness','')}
  Momentum: {c.get('comms_momentum','')}
  Reasoning: {c.get('comms_reasoning','')}
  Last contact: {c.get('comms_last_date','')}
  Total threads: {c.get('comms_thread_count','')}
  Meetings: {c.get('comms_meeting_count','')}, Last meeting: {c.get('comms_last_meeting','')}
  Calls: {c.get('comms_call_count','')}
  Relationship summary: {comms.get('relationship_summary','')}

  Email/message threads:
{threads_text}
  Channel summary: {json.dumps(comms_sum.get('channels',''), indent=2, default=str)}
  Chronological: {comms_sum.get('chronological_summary','')}
""")

    sections.append(f"""
DONOR PROFILE
  Capacity score: {c.get('donor_capacity_score','')}
  Propensity score: {c.get('donor_propensity_score','')}
  Affinity score: {c.get('donor_affinity_score','')}
  Warmth score: {c.get('donor_warmth_score','')}
  Total score: {c.get('donor_total_score','')}
  Tier: {c.get('donor_tier','')}
  Estimated capacity: {c.get('estimated_capacity','')}
  Executive level: {c.get('executive_level','')}
  Known donor: {c.get('known_donor','')}
  Past giving: {json.dumps(c.get('past_giving_details',''), default=str)}
  Capacity indicators: {json.dumps(c.get('capacity_indicators',''), default=str)}

AI ANALYSIS
  Tags: {json.dumps(c.get('ai_tags',''), indent=2, default=str)}
  Proximity: {c.get('ai_proximity_score','')} ({c.get('ai_proximity_tier','')})
  Capacity: {c.get('ai_capacity_score','')} ({c.get('ai_capacity_tier','')})
  OC fit: {c.get('ai_outdoorithm_fit','')}
""")

    # Employment history
    emp = c.get("enrich_employment")
    if emp:
        sections.append(f"EMPLOYMENT HISTORY\n{json.dumps(emp, indent=2, default=str)}\n")

    # Education
    edu = c.get("enrich_education")
    if edu:
        sections.append(f"EDUCATION\n{json.dumps(edu, indent=2, default=str)}\n")

    # Board positions & volunteering
    boards = c.get("enrich_board_positions")
    if boards:
        sections.append(f"BOARD POSITIONS\n{json.dumps(boards, indent=2, default=str)}\n")
    vol = c.get("enrich_volunteering")
    if vol:
        sections.append(f"VOLUNTEERING\n{json.dumps(vol, indent=2, default=str)}\n")

    # FEC donations
    fec = c.get("fec_donations")
    if fec:
        sections.append(f"FEC POLITICAL DONATIONS\n{json.dumps(fec, indent=2, default=str)}\n")

    # Real estate
    re_data = c.get("real_estate_data")
    if re_data:
        sections.append(f"REAL ESTATE\n{json.dumps(re_data, indent=2, default=str)}\n")

    # OC engagement
    if oc:
        sections.append(f"OC ENGAGEMENT\n{json.dumps(oc, indent=2, default=str)}\n")

    # LinkedIn reactions
    lr = c.get("linkedin_reactions")
    if lr:
        sections.append(f"LINKEDIN REACTIONS\n{json.dumps(lr, indent=2, default=str)}\n")

    # Ask readiness
    if ask_oc:
        sections.append(f"""
ASK READINESS (Outdoorithm Fundraising)
  Score: {ask_oc.get('score','')}
  Tier: {ask_oc.get('tier','')}
  Ask timing: {ask_oc.get('ask_timing','')}
  Suggested ask range: {ask_oc.get('suggested_ask_range','')}
  Recommended approach: {ask_oc.get('recommended_approach','')}
  Personalization angle: {ask_oc.get('personalization_angle','')}
  Receiver frame: {ask_oc.get('receiver_frame','')}
  Cultivation needed: {ask_oc.get('cultivation_needed','')}
  Risk factors: {json.dumps(ask_oc.get('risk_factors',''), indent=2, default=str)}
  Reasoning: {ask_oc.get('reasoning','')}
""")

    # Campaign scaffold
    sections.append(f"""
CAMPAIGN SCAFFOLD
  Persona: {scaffold.get('persona','')}
  Capacity tier: {scaffold.get('capacity_tier','')}
  Lifecycle: {scaffold.get('lifecycle_stage','')}
  Primary ask amount: {scaffold.get('primary_ask_amount','')}
  Primary motivation: {scaffold.get('primary_motivation','')}
  Motivation flags: {json.dumps(scaffold.get('motivation_flags',''), default=str)}
  Lead story: {scaffold.get('lead_story','')}
  Story reasoning: {scaffold.get('story_reasoning','')}
  Personalization sentence: {scaffold.get('personalization_sentence','')}
  Opener insert: {scaffold.get('opener_insert','')}
  Persona reasoning: {scaffold.get('persona_reasoning','')}
""")

    # Current outreach (the one we're rewriting)
    sections.append(f"""
CURRENT OUTREACH MESSAGE (REWRITE THIS)
  Channel: {outreach.get('channel','')}
  Subject line: {outreach.get('subject_line','')}
  Internal notes: {outreach.get('internal_notes','')}

  Message body:
{outreach.get('message_body','(no message yet)')}

============================================================
INSTRUCTIONS: Rewrite the above outreach message. Keep what works,
fix what doesn't. The rewrite MUST include:
- 8 trips, $40K gear, $120K total, $45K raised, $20K match, $75K to go
- No em dashes
- Under 200 words
- Justin's authentic voice
- Personalization specific to THIS person
- A story or feeling (not framework explanation)
============================================================
""")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Call Opus 4.6
# ---------------------------------------------------------------------------
def rewrite_with_opus(
    client: anthropic.Anthropic,
    system_prompt: str,
    contact_prompt: str,
    contact_name: str,
) -> dict:
    print(f"  Calling Opus 4.6 for {contact_name}...")

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": contact_prompt}],
    )

    text = response.content[0].text.strip()

    # Parse JSON from response (handle markdown code blocks)
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()

    result = json.loads(text)

    if "subject_line" not in result or "message_body" not in result:
        raise ValueError(f"Missing fields in response: {list(result.keys())}")

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Rewrite outreach with Opus 4.6")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't write to DB")
    parser.add_argument("--contact-id", type=int, help="Rewrite for a single contact ID")
    args = parser.parse_args()

    # Init clients
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Build system prompt once
    print("Loading campaign docs and building system prompt...")
    system_prompt = build_system_prompt()
    print(f"  System prompt: {len(system_prompt):,} chars")

    # Fetch contacts
    print("\nFetching List A contacts from Supabase...")
    query = supabase.table("contacts").select(PROFILE_SELECT)

    if args.contact_id:
        query = query.eq("id", args.contact_id)
    else:
        # All List A contacts with personal outreach
        query = query.not_.is_("campaign_2026", "null")

    result = query.execute()
    contacts = result.data or []

    # Filter to List A with personal outreach in Python
    contacts = [
        c for c in contacts
        if c.get("campaign_2026", {}).get("scaffold", {}).get("campaign_list") == "A"
        and c.get("campaign_2026", {}).get("personal_outreach")
    ]

    print(f"  Found {len(contacts)} List A contacts with personal outreach")

    if not contacts:
        print("No contacts to process. Exiting.")
        return

    # Process each contact
    results = []
    for i, contact in enumerate(contacts, 1):
        name = f"{contact.get('first_name','')} {contact.get('last_name','')}".strip()
        cid = contact["id"]
        print(f"\n[{i}/{len(contacts)}] {name} (ID: {cid})")

        try:
            contact_prompt = build_contact_prompt(contact)
            print(f"  Contact prompt: {len(contact_prompt):,} chars")

            rewritten = rewrite_with_opus(client, system_prompt, contact_prompt, name)

            old_subject = (contact.get("campaign_2026", {}).get("personal_outreach", {})
                           .get("subject_line", ""))
            old_body = (contact.get("campaign_2026", {}).get("personal_outreach", {})
                        .get("message_body", ""))
            new_subject = rewritten["subject_line"]
            new_body = rewritten["message_body"]

            # Word count check
            word_count = len(new_body.split())
            has_gear = "gear" in new_body.lower()
            has_120k = "120" in new_body
            has_8_trips = "8 trip" in new_body.lower()
            has_em_dash = "\u2014" in new_body

            print(f"  Subject: {old_subject!r} -> {new_subject!r}")
            print(f"  Words: {word_count}, Gear: {has_gear}, $120K: {has_120k}, "
                  f"8 trips: {has_8_trips}, Em dash: {has_em_dash}")

            if has_em_dash:
                print(f"  WARNING: Em dash detected! Needs manual fix.")

            if not has_gear or not has_120k:
                print(f"  WARNING: Missing gear or $120K mention!")

            if word_count > 220:
                print(f"  WARNING: Over 200 words ({word_count})")

            # Show diff preview
            print(f"\n  --- NEW MESSAGE ---")
            for line in new_body.split("\n"):
                print(f"  | {line}")
            print(f"  --- END ---\n")

            results.append({
                "id": cid,
                "name": name,
                "subject_line": new_subject,
                "message_body": new_body,
                "word_count": word_count,
                "checks": {
                    "has_gear": has_gear,
                    "has_120k": has_120k,
                    "has_8_trips": has_8_trips,
                    "has_em_dash": has_em_dash,
                },
            })

            # Write to Supabase if not dry run
            if not args.dry_run:
                campaign = dict(contact.get("campaign_2026", {}))
                po = dict(campaign.get("personal_outreach", {}))
                po["subject_line"] = new_subject
                po["message_body"] = new_body
                campaign["personal_outreach"] = po
                campaign["outreach_rewritten_at"] = datetime.now(timezone.utc).isoformat()

                supabase.table("contacts").update(
                    {"campaign_2026": campaign}
                ).eq("id", cid).execute()
                print(f"  SAVED to Supabase")
            else:
                print(f"  (dry run, not saved)")

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"id": cid, "name": name, "error": str(e)})

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    successes = [r for r in results if "error" not in r]
    failures = [r for r in results if "error" in r]
    print(f"  Processed: {len(results)}")
    print(f"  Success: {len(successes)}")
    print(f"  Failed: {len(failures)}")

    if failures:
        print("\n  Failures:")
        for f in failures:
            print(f"    - {f['name']} (ID {f['id']}): {f['error']}")

    warnings = [r for r in successes if r["checks"].get("has_em_dash")
                or not r["checks"].get("has_gear")
                or not r["checks"].get("has_120k")]
    if warnings:
        print("\n  Warnings:")
        for w in warnings:
            issues = []
            if w["checks"].get("has_em_dash"):
                issues.append("em dash")
            if not w["checks"].get("has_gear"):
                issues.append("missing gear")
            if not w["checks"].get("has_120k"):
                issues.append("missing $120K")
            print(f"    - {w['name']}: {', '.join(issues)}")

    if args.dry_run:
        print("\n  DRY RUN: No changes written to Supabase.")
        print("  Run without --dry-run to save.")


if __name__ == "__main__":
    main()
