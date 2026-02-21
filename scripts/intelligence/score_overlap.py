#!/usr/bin/env python3
"""
Network Intelligence — Structured Institutional Overlap Scoring

Uses GPT-5 mini to analyze institutional overlap between Justin and each contact,
producing structured temporal analysis. Stores results in shared_institutions JSONB.

Only processes contacts that have shared institution signals in ai_tags
(shared_employers, shared_schools, shared_boards, or shared_volunteering).

Usage:
  python scripts/intelligence/score_overlap.py --test           # 1 contact
  python scripts/intelligence/score_overlap.py --batch 50       # 50 contacts
  python scripts/intelligence/score_overlap.py --start-from 100 # Skip first 100
  python scripts/intelligence/score_overlap.py                  # Full run (~1,400)
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

class InstitutionType(str, Enum):
    employer = "employer"
    school = "school"
    board = "board"
    volunteer = "volunteer"
    other = "other"

class OverlapStatus(str, Enum):
    confirmed = "confirmed"
    likely = "likely"
    possible = "possible"
    different_era = "different_era"

class DepthLevel(str, Enum):
    same_team = "same_team"
    same_org = "same_org"
    same_field = "same_field"
    alumni = "alumni"
    adjacent = "adjacent"

class SharedInstitution(BaseModel):
    name: str = Field(description="Institution name (normalized)")
    type: InstitutionType
    overlap: OverlapStatus
    justin_period: str = Field(description="Justin's period there, e.g. '2014-2019'")
    contact_period: str = Field(description="Contact's period there, e.g. '2016-2020' or 'unknown'")
    temporal_overlap: bool = Field(description="True if their periods overlapped")
    depth: DepthLevel
    notes: str = Field(description="Brief note on the relationship context")

class OverlapAnalysis(BaseModel):
    institutions: list[SharedInstitution] = Field(description="All shared institutions found")


# ── Justin's Career Timeline ──────────────────────────────────────────

JUSTIN_TIMELINE = """JUSTIN STEELE'S CAREER TIMELINE (use for temporal overlap analysis):

EMPLOYMENT:
- Bain & Company, Associate Consultant (2006-2008)
- The Bridgespan Group, Senior Associate Consultant (2008-2010)
- Year Up, Deputy Director / Director Strategy & Ops (2010-2012)
- Harvard Business School, MBA student (2012-2014)
- Harvard Kennedy School, MPA student (2012-2014)
- Google.org, Director Americas (2014-2019)
- Outdoorithm, Co-Founder & CTO (2018-present)
- True Steele LLC, Founder & Fractional CIO (2019-present)
- Kindora, Co-Founder & CEO (2020-present)
- Outdoorithm Collective, Co-Founder & Treasurer (2022-present)

EDUCATION:
- University of Virginia, BS Engineering (~2002-2006)
- Harvard Business School, MBA (2012-2014)
- Harvard Kennedy School, MPA/MPP (2012-2014)

BOARDS & VOLUNTEERING:
- San Francisco Foundation, Board of Trustees / Program Chair (2021-present)
- Outdoorithm Collective, Board of Directors / Treasurer (2022-present)"""


SYSTEM_PROMPT = """You are an institutional overlap analyst. Given Justin Steele's career timeline and a contact's employment, education, and volunteering history, identify ALL shared institutions between them.

For each shared institution, determine:
1. The normalized institution name (e.g. "Google" and "Google.org" are the same org family)
2. Type: employer, school, board, or volunteer
3. Justin's period there (from the timeline provided)
4. The contact's period there (extract from their employment/education data; use "unknown" if dates aren't available)
5. Whether their periods temporally overlapped (were they there at the SAME TIME?)
6. Depth: same_team (worked closely), same_org (same company), same_field (same industry/sector), alumni (same school), adjacent (related orgs)
7. A brief note about the connection context

IMPORTANT RULES:
- Only include institutions where BOTH Justin and the contact have a connection
- Be precise about temporal overlap — "likely" if dates are vague but plausible, "different_era" if clearly different times
- Normalize org names (e.g. "Google", "Google.org", "Google LLC" → use "Google / Google.org")
- For schools, consider degree programs — same school but different programs is still "alumni" depth
- Include board and volunteer connections as well as employment and education
- If dates are given as durations (e.g. "2 yrs") without start/end, estimate from context or mark as "unknown"
- Return an empty list if there are genuinely no shared institutions"""


SELECT_COLS = (
    "id, first_name, last_name, headline, company, position, "
    "connected_on, city, state, ai_tags, shared_institutions, "
    "enrich_employment, enrich_education, enrich_volunteering"
)


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


def has_shared_institutions(ai_tags: dict) -> bool:
    """Check if contact has any shared institution signals in ai_tags."""
    if not ai_tags:
        return False
    rp = ai_tags.get("relationship_proximity", {})
    return bool(
        rp.get("shared_employers")
        or rp.get("shared_schools")
        or rp.get("shared_boards")
        or rp.get("shared_volunteering")
    )


def build_contact_context(contact: dict) -> str:
    """Assemble the per-contact context for the LLM."""
    parts = []
    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    parts.append(f"CONTACT: {name}")

    if contact.get("headline"):
        parts.append(f"Headline: {contact['headline']}")
    if contact.get("company") or contact.get("position"):
        parts.append(f"Current: {contact.get('position', '?')} at {contact.get('company', '?')}")
    if contact.get("connected_on"):
        parts.append(f"LinkedIn connected: {contact['connected_on']}")
    if contact.get("city") or contact.get("state"):
        loc = ", ".join(filter(None, [contact.get("city"), contact.get("state")]))
        parts.append(f"Location: {loc}")

    # Employment history
    employment = parse_jsonb(contact.get("enrich_employment"))
    if employment:
        if isinstance(employment, str):
            employment = parse_jsonb(employment)
        if isinstance(employment, list):
            parts.append("\nEMPLOYMENT HISTORY:")
            for job in employment:
                if isinstance(job, dict):
                    title = job.get("job_title", "?")
                    company = job.get("company_name", "?")
                    duration = job.get("duration", "")
                    start = job.get("start_date", "")
                    end = job.get("end_date", "")
                    current = job.get("is_current", False)
                    period = ""
                    if start and end:
                        period = f" ({start} - {end})"
                    elif start:
                        period = f" ({start} - present)" if current else f" ({start})"
                    elif duration:
                        period = f" ({duration})"
                    parts.append(f"  - {title} at {company}{period}")

    # Education
    education = parse_jsonb(contact.get("enrich_education"))
    if education:
        if isinstance(education, str):
            education = parse_jsonb(education)
        if isinstance(education, list):
            parts.append("\nEDUCATION:")
            for edu in education:
                if isinstance(edu, dict):
                    school = edu.get("school_name", "?")
                    degree = edu.get("degree", "")
                    field = edu.get("field_of_study", "")
                    desc = f"{degree}" + (f" in {field}" if field else "")
                    parts.append(f"  - {school}: {desc}" if desc else f"  - {school}")

    # Volunteering
    volunteering = parse_jsonb(contact.get("enrich_volunteering"))
    if volunteering:
        if isinstance(volunteering, str):
            volunteering = parse_jsonb(volunteering)
        if isinstance(volunteering, list):
            parts.append("\nVOLUNTEERING:")
            for vol in volunteering:
                if isinstance(vol, dict):
                    org = vol.get("organization", "Unknown org")
                    role = vol.get("role", "")
                    cause = vol.get("cause", "")
                    line = f"  - {role}" if role else "  -"
                    if org:
                        line += f" at {org}"
                    if cause:
                        line += f" ({cause})"
                    parts.append(line)

    # Existing AI-detected overlap (for reference)
    ai_tags = parse_jsonb(contact.get("ai_tags"))
    if ai_tags:
        rp = ai_tags.get("relationship_proximity", {})
        existing = []
        for emp in (rp.get("shared_employers") or []):
            if isinstance(emp, dict):
                existing.append(f"  - Employer: {emp.get('org', '?')} ({emp.get('overlap_years', 'unknown')})")
        for sch in (rp.get("shared_schools") or []):
            if isinstance(sch, dict):
                existing.append(f"  - School: {sch.get('school', '?')} ({sch.get('overlap', 'unknown')})")
        for board in (rp.get("shared_boards") or []):
            existing.append(f"  - Board: {board}")
        for vol in (rp.get("shared_volunteering") or []):
            existing.append(f"  - Volunteering: {vol}")
        if existing:
            parts.append("\nPREVIOUSLY DETECTED SHARED INSTITUTIONS (verify and add temporal detail):")
            parts.extend(existing)

    return "\n".join(parts)


# ── Main Scorer ──────────────────────────────────────────────────────

class OverlapScorer:
    MODEL = "gpt-5-mini"

    def __init__(self, test_mode=False, batch_size=None, start_from=0, workers=8):
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.start_from = start_from
        self.workers = workers
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.stats = {
            "processed": 0,
            "with_overlap": 0,
            "no_overlap": 0,
            "errors": 0,
            "skipped": 0,
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
        """Fetch contacts that have shared institutions in ai_tags but not yet scored."""
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            page = (
                self.supabase.table("contacts")
                .select(SELECT_COLS)
                .is_("shared_institutions", "null")
                .not_.is_("ai_tags", "null")
                .order("id")
                .range(offset, offset + page_size - 1)
                .execute()
            ).data

            if not page:
                break
            all_contacts.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        # Filter to only contacts with shared institution signals
        filtered = []
        for c in all_contacts:
            ai_tags = parse_jsonb(c.get("ai_tags"))
            if has_shared_institutions(ai_tags):
                filtered.append(c)

        # Apply start-from offset
        if self.start_from > 0:
            filtered = filtered[self.start_from:]

        # Apply batch/test limits
        if self.test_mode:
            filtered = filtered[:1]
        elif self.batch_size:
            filtered = filtered[:self.batch_size]

        return filtered

    def score_contact(self, contact: dict) -> Optional[OverlapAnalysis]:
        """Call GPT-5 mini to analyze institutional overlap for a single contact."""
        contact_context = build_contact_context(contact)
        user_message = f"{JUSTIN_TIMELINE}\n\n{contact_context}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions=SYSTEM_PROMPT,
                    input=user_message,
                    text_format=OverlapAnalysis,
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

    def save_overlap(self, contact_id: int, result: OverlapAnalysis) -> bool:
        """Save the structured overlap to Supabase."""
        institutions_json = [inst.model_dump(mode="json") for inst in result.institutions]

        try:
            self.supabase.table("contacts").update({
                "shared_institutions": institutions_json,
            }).eq("id", contact_id).execute()
            return True
        except Exception as e:
            print(f"    DB error for id={contact_id}: {e}")
            return False

    def process_contact(self, contact: dict) -> bool:
        """Process a single contact: score overlap + save."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        contact_id = contact["id"]

        result = self.score_contact(contact)
        if result is None:
            self.stats["errors"] += 1
            print(f"  ERROR [{contact_id}] {name}: Failed to get overlap analysis")
            return False

        if self.save_overlap(contact_id, result):
            count = len(result.institutions)
            self.stats["processed"] += 1
            if count > 0:
                self.stats["with_overlap"] += 1
                institutions = ", ".join(
                    f"{i.name} ({i.type.value}, {'temporal overlap' if i.temporal_overlap else 'no overlap'})"
                    for i in result.institutions
                )
                print(f"  [{contact_id}] {name}: {count} shared institutions — {institutions}")
            else:
                self.stats["no_overlap"] += 1
                print(f"  [{contact_id}] {name}: no confirmed shared institutions")
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
        print(f"Found {total} contacts with shared institution signals to process")

        if total == 0:
            print("Nothing to do — all eligible contacts already have structured overlap data")
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
                              f"({self.stats['with_overlap']} with overlap, "
                              f"{self.stats['no_overlap']} none, "
                              f"{self.stats['errors']} errors) "
                              f"[{rate:.1f} contacts/sec, {elapsed:.0f}s elapsed] ---\n")

        elapsed = time.time() - start_time
        self.print_summary(elapsed)
        return self.stats["errors"] < total * 0.05

    def print_summary(self, elapsed: float):
        s = self.stats
        input_cost = s["input_tokens"] * 0.15 / 1_000_000
        output_cost = s["output_tokens"] * 0.60 / 1_000_000
        total_cost = input_cost + output_cost

        print("\n" + "=" * 60)
        print("INSTITUTIONAL OVERLAP SCORING SUMMARY")
        print("=" * 60)
        print(f"  Contacts processed:    {s['processed']}")
        print(f"  With shared overlap:   {s['with_overlap']}")
        print(f"  No shared overlap:     {s['no_overlap']}")
        print(f"  Skipped:               {s['skipped']}")
        print(f"  Errors:                {s['errors']}")
        print(f"  Input tokens:          {s['input_tokens']:,}")
        print(f"  Output tokens:         {s['output_tokens']:,}")
        print(f"  Cost:                  ${total_cost:.2f} (input: ${input_cost:.2f}, output: ${output_cost:.2f})")
        print(f"  Time elapsed:          {elapsed:.1f}s")
        if s["processed"] > 0:
            print(f"  Avg time/contact:      {elapsed / s['processed']:.2f}s")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Score institutional overlap between Justin and contacts using GPT-5 mini"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only 1 contact for validation")
    parser.add_argument("--batch", "-b", type=int, default=None,
                        help="Process N contacts")
    parser.add_argument("--start-from", "-s", type=int, default=0,
                        help="Skip first N contacts (for resuming)")
    parser.add_argument("--workers", "-w", type=int, default=8,
                        help="Number of concurrent workers (default: 8)")
    args = parser.parse_args()

    scorer = OverlapScorer(
        test_mode=args.test,
        batch_size=args.batch,
        start_from=args.start_from,
        workers=args.workers,
    )
    success = scorer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
