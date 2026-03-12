#!/usr/bin/env python3
"""
Network Intelligence — Web Research Enrichment

Uses Perplexity sonar-pro to research contacts who lack LinkedIn profiles
or have thin enrichment data, then structures the results with GPT-5 mini
and saves to the contacts table.

Designed for contacts like Quinn Delaney, Bryan Stevenson, Julián Castro —
high-profile people who don't use LinkedIn but have extensive public profiles.

Usage:
  python enrich_web_research.py --discover --dry-run       # Preview what would be researched
  python enrich_web_research.py --ids 1933                 # Research Bryan Stevenson
  python enrich_web_research.py --discover                 # Research all empty/thin profiles
  python enrich_web_research.py --discover --re-score      # Research + re-run AI scoring
  python enrich_web_research.py --discover --force          # Re-research already web-researched
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

import requests
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI

load_dotenv()


# ── Structured Output Schema ─────────────────────────────────────────

class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class WebResearchProfile(BaseModel):
    """Structured profile extracted from web research."""
    headline: str = Field(description="Professional headline, e.g. 'Founder & Board Chair, Akonadi Foundation | Philanthropist | Attorney'. Keep under 100 chars.")
    summary: str = Field(description="2-4 sentence biographical summary covering career, achievements, and notable affiliations.")
    company: str = Field(description="Current primary organization/employer. Empty string if retired or unclear.")
    position: str = Field(description="Current title/role. Empty string if unclear.")
    city: str = Field(description="City of residence. Empty string if unknown.")
    state: str = Field(description="US state of residence (full name, e.g. 'California'). Empty string if unknown or non-US.")
    confidence: Confidence = Field(description="How confident are you this research is about the correct person?")
    confidence_reasoning: str = Field(description="Brief explanation of confidence level — what signals confirm or cast doubt on identity match.")


# ── Prompts ───────────────────────────────────────────────────────────

STRUCTURING_SYSTEM_PROMPT = """You are extracting structured profile data from web research about a person.

Given the raw web research output and the person's known details, extract a clean structured profile.

Rules:
- headline: Concise professional headline (under 100 chars). Include their most notable current role and 1-2 descriptors. E.g. "Founder, Equal Justice Initiative | Civil Rights Attorney | Author"
- summary: 2-4 sentences covering career arc, key achievements, and notable affiliations. Factual, not promotional.
- company: Their current primary organization. If retired, use their most recent or most notable org.
- position: Their current title. If retired, note it (e.g. "Founder (ret.)" or "Board Chair").
- city/state: Where they live. Use full state name ("California" not "CA").
- confidence: "high" if the research clearly matches the person (unique name, consistent details). "medium" if there's some ambiguity but likely correct. "low" if you can't confirm identity (common name, conflicting info).

If the research found nothing useful or returned info about the wrong person, set confidence to "low" and leave other fields empty."""


def build_perplexity_query(contact: dict) -> str:
    """Build a Perplexity search query for a contact."""
    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

    # Gather any known context to anchor the search
    context_parts = []
    if contact.get("company"):
        context_parts.append(f"associated with {contact['company']}")
    if contact.get("position"):
        context_parts.append(f"role: {contact['position']}")
    if contact.get("headline") and contact["headline"] not in (".", "--", "---"):
        context_parts.append(f"described as: {contact['headline']}")
    if contact.get("city") or contact.get("state"):
        loc = ", ".join(filter(None, [contact.get("city"), contact.get("state")]))
        context_parts.append(f"based in {loc}")

    # Check communication history for clues
    comms = contact.get("communication_history")
    if comms and isinstance(comms, dict):
        summary = comms.get("summary", "")
        if summary and len(summary) > 20:
            context_parts.append(f"known context from email correspondence: {summary[:200]}")

    context = f" ({'; '.join(context_parts)})" if context_parts else ""

    query = f"""Research {name}{context}.

Provide a comprehensive biographical profile including:
1. Current role and organization
2. Career history (major positions, companies, approximate dates)
3. Education (schools, degrees)
4. Location (city, state)
5. Board memberships and advisory roles
6. Notable achievements, awards, honors
7. Philanthropic activity, foundation involvement, and causes supported
8. Public profile and media presence

Focus on the correct person matching the details above. If multiple people share this name, identify the most likely match based on the context provided. If you cannot determine the correct person with reasonable confidence, state that clearly.

Provide specific, verifiable facts. Do not speculate."""

    return query


# ── Main Enricher Class ──────────────────────────────────────────────

class WebResearchEnricher:
    PERPLEXITY_MODEL = "sonar-pro"
    GPT_MODEL = "gpt-5-mini"
    SELECT_COLS = (
        "id, first_name, last_name, headline, summary, company, position, "
        "city, state, enrichment_source, enriched_at, "
        "enrich_employment, enrich_education, "
        "communication_history, connected_on"
    )

    def __init__(self, discover=False, ids=None, force=False, test_mode=False,
                 batch_size=None, re_score=False, dry_run=False):
        self.discover = discover
        self.ids = ids
        self.force = force
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.re_score = re_score
        self.dry_run = dry_run
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.perplexity_key: Optional[str] = None
        self.stats = {
            "researched": 0,
            "saved": 0,
            "skipped_low_confidence": 0,
            "errors": 0,
            "perplexity_tokens": 0,
            "gpt_input_tokens": 0,
            "gpt_output_tokens": 0,
        }
        self.enriched_ids = []  # Track successfully enriched IDs for re-scoring

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        openai_key = os.environ.get("OPENAI_APIKEY")
        perplexity_key = os.environ.get("PERPLEXITY_APIKEY")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        if not self.dry_run:
            if not openai_key:
                print("ERROR: Missing OPENAI_APIKEY")
                return False
            if not perplexity_key:
                print("ERROR: Missing PERPLEXITY_APIKEY")
                return False

        self.supabase = create_client(url, key)
        if not self.dry_run:
            self.openai = OpenAI(api_key=openai_key)
            self.perplexity_key = perplexity_key
        print(f"Connected to Supabase{' and APIs' if not self.dry_run else ' (dry-run, no API calls)'}")
        return True

    def get_contacts(self) -> list[dict]:
        """Fetch contacts to research."""
        if self.ids:
            response = (
                self.supabase.table("contacts")
                .select(self.SELECT_COLS)
                .in_("id", self.ids)
                .execute()
            )
            return response.data

        if self.discover:
            return self._discover_contacts()

        print("ERROR: Must specify --ids or --discover")
        return []

    def _discover_contacts(self) -> list[dict]:
        """Find contacts that would benefit from web research."""
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
            response = query.execute()
            page = response.data
            if not page:
                break
            all_contacts.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        # Filter to contacts needing research
        candidates = []
        for c in all_contacts:
            # Skip already web-researched unless --force
            if not self.force and c.get("enrichment_source") in ("web_research", "manual_web_research"):
                continue

            headline = (c.get("headline") or "").strip()
            summary = (c.get("summary") or "").strip()
            employment = c.get("enrich_employment")
            education = c.get("enrich_education")

            # Heuristic 1: Completely empty profile (no headline AND no summary)
            is_empty = not headline and not summary

            # Heuristic 2: Thin profile — has headline but no employment, education, or summary
            emp_empty = not employment or (isinstance(employment, list) and len(employment) == 0)
            edu_empty = not education or (isinstance(education, list) and len(education) == 0)
            is_thin = not summary and emp_empty and edu_empty

            # Skip placeholder headlines
            if headline in (".", "--", "---"):
                is_empty = True

            if is_empty or is_thin:
                candidates.append(c)

        if self.test_mode:
            candidates = candidates[:1]
        elif self.batch_size:
            candidates = candidates[:self.batch_size]

        return candidates

    def research_contact(self, contact: dict) -> Optional[dict]:
        """Call Perplexity to research a contact. Returns raw response dict or None."""
        query = build_perplexity_query(contact)
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.PERPLEXITY_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert researcher. Provide detailed, factual biographical information with specific dates, organizations, and roles. Be precise and cite verifiable facts."
                },
                {
                    "role": "user",
                    "content": query,
                },
            ],
            "return_citations": True,
            "return_related_questions": False,
        }

        try:
            resp = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]
            citations = data.get("citations", [])
            usage = data.get("usage", {})
            self.stats["perplexity_tokens"] += usage.get("total_tokens", 0)

            return {
                "content": content,
                "citations": citations,
                "usage": usage,
            }

        except requests.exceptions.RequestException as e:
            print(f"    Perplexity error for {name}: {e}")
            return None

    def structure_research(self, contact: dict, raw_research: str) -> Optional[WebResearchProfile]:
        """Use GPT-5 mini to extract structured fields from raw research."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

        # Build context about what we already know
        known_parts = [f"Contact name in our database: {name}"]
        if contact.get("company"):
            known_parts.append(f"Known company: {contact['company']}")
        if contact.get("position"):
            known_parts.append(f"Known position: {contact['position']}")
        if contact.get("headline") and contact["headline"] not in (".", "--", "---"):
            known_parts.append(f"Known headline: {contact['headline']}")
        if contact.get("city") or contact.get("state"):
            loc = ", ".join(filter(None, [contact.get("city"), contact.get("state")]))
            known_parts.append(f"Known location: {loc}")
        if contact.get("connected_on"):
            known_parts.append(f"Connected on LinkedIn: {contact['connected_on']}")

        known_context = "\n".join(known_parts)

        user_message = f"""{known_context}

--- RAW WEB RESEARCH ---
{raw_research}
--- END RESEARCH ---

Extract a structured profile from the research above. Match it to the contact in our database."""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.openai.responses.parse(
                    model=self.GPT_MODEL,
                    instructions=STRUCTURING_SYSTEM_PROMPT,
                    input=user_message,
                    text_format=WebResearchProfile,
                )

                # Track tokens
                if hasattr(resp, "usage") and resp.usage:
                    self.stats["gpt_input_tokens"] += getattr(resp.usage, "input_tokens", 0)
                    self.stats["gpt_output_tokens"] += getattr(resp.usage, "output_tokens", 0)

                return resp.output_parsed

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                print(f"    GPT structuring error for {name}: {e}")
                return None

    def save_enrichment(self, contact_id: int, profile: WebResearchProfile,
                        raw_research: str, citations: list) -> bool:
        """Save structured research to the contacts table."""
        # Only update fields that are currently empty
        updates = {
            "enrichment_source": "web_research",
            "enriched_at": datetime.now(timezone.utc).isoformat(),
            "perplexity_enriched_at": datetime.now(timezone.utc).isoformat(),
            "perplexity_research_data": _strip_null_bytes({
                "structured": profile.model_dump(mode="json"),
                "raw_content": raw_research,
                "model": self.PERPLEXITY_MODEL,
                "researched_at": datetime.now(timezone.utc).isoformat(),
            }),
            "perplexity_sources": citations,
        }

        # Fetch current values to avoid overwriting existing data
        current = (
            self.supabase.table("contacts")
            .select("headline, summary, company, position, city, state")
            .eq("id", contact_id)
            .execute()
        ).data[0]

        if not (current.get("headline") or "").strip() and profile.headline:
            updates["headline"] = profile.headline
        if not (current.get("summary") or "").strip() and profile.summary:
            updates["summary"] = profile.summary
        if not (current.get("company") or "").strip() and profile.company:
            updates["company"] = profile.company
        if not (current.get("position") or "").strip() and profile.position:
            updates["position"] = profile.position
        if not (current.get("city") or "").strip() and profile.city:
            updates["city"] = profile.city
        if not (current.get("state") or "").strip() and profile.state:
            updates["state"] = profile.state

        try:
            self.supabase.table("contacts").update(updates).eq("id", contact_id).execute()
            return True
        except Exception as e:
            print(f"    DB error for id={contact_id}: {e}")
            return False

    def process_contact(self, contact: dict) -> bool:
        """Full pipeline for one contact: research → structure → save."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        contact_id = contact["id"]

        # Step 1: Perplexity research
        result = self.research_contact(contact)
        if not result:
            self.stats["errors"] += 1
            return False

        self.stats["researched"] += 1
        raw_content = result["content"]
        citations = result.get("citations", [])

        # Step 2: GPT structuring
        profile = self.structure_research(contact, raw_content)
        if not profile:
            self.stats["errors"] += 1
            return False

        # Step 3: Confidence check
        if profile.confidence == Confidence.low:
            print(f"  [{contact_id}] {name}: SKIPPED (low confidence — {profile.confidence_reasoning})")
            self.stats["skipped_low_confidence"] += 1
            # Still save the raw research for manual review
            try:
                self.supabase.table("contacts").update({
                    "perplexity_research_data": _strip_null_bytes({
                        "structured": profile.model_dump(mode="json"),
                        "raw_content": raw_content,
                        "model": self.PERPLEXITY_MODEL,
                        "researched_at": datetime.now(timezone.utc).isoformat(),
                        "status": "low_confidence_skipped",
                    }),
                    "perplexity_enriched_at": datetime.now(timezone.utc).isoformat(),
                    "perplexity_sources": citations,
                }).eq("id", contact_id).execute()
            except Exception:
                pass
            return False

        # Step 4: Save
        if self.save_enrichment(contact_id, profile, raw_content, citations):
            conf_marker = "" if profile.confidence == Confidence.high else " [medium confidence]"
            print(f"  [{contact_id}] {name}: {profile.headline[:60]}{conf_marker}")
            self.stats["saved"] += 1
            self.enriched_ids.append(contact_id)
            return True
        else:
            self.stats["errors"] += 1
            return False

    def run_re_scoring(self):
        """Re-run AI tagging and ask-readiness for enriched contacts."""
        if not self.enriched_ids:
            print("\nNo contacts to re-score.")
            return

        ids_str = ",".join(str(i) for i in self.enriched_ids)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        python = sys.executable

        print(f"\n--- Re-scoring {len(self.enriched_ids)} contacts ---\n")

        # Re-run tagging
        print("Running AI tagging...")
        tag_cmd = [python, "-u", os.path.join(script_dir, "tag_contacts_gpt5m.py"),
                   "--ids", ids_str, "--force"]
        subprocess.run(tag_cmd, cwd=script_dir)

        # Re-run ask-readiness
        print("\nRunning ask-readiness scoring...")
        score_cmd = [python, "-u", os.path.join(script_dir, "score_ask_readiness.py"),
                     "--ids", ids_str, "--force"]
        subprocess.run(score_cmd, cwd=script_dir)

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()
        contacts = self.get_contacts()
        total = len(contacts)
        print(f"Found {total} contacts to research")

        if total == 0:
            print("Nothing to do.")
            return True

        if self.dry_run:
            print(f"\n--- DRY RUN: Would research {total} contacts ---\n")
            for c in contacts:
                name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
                headline = (c.get("headline") or "").strip()
                company = (c.get("company") or "").strip()
                source = c.get("enrichment_source") or "none"
                status = "empty" if not headline else "thin"
                print(f"  [{c['id']}] {name} — {status}, enrichment: {source}"
                      + (f", headline: {headline[:50]}" if headline else "")
                      + (f", company: {company}" if company else ""))

            est_cost = total * 0.0085  # ~$0.0075 perplexity + ~$0.001 GPT
            print(f"\n--- DRY RUN COMPLETE ---")
            print(f"  Contacts to research: {total}")
            print(f"  Est. cost: ~${est_cost:.2f}")
            return True

        print(f"\n--- Researching {total} contacts (sequential Perplexity, ~2s delay) ---\n")

        for i, contact in enumerate(contacts, 1):
            self.process_contact(contact)

            # Rate limit: 1.5s delay between Perplexity calls
            if i < total:
                time.sleep(1.5)

            # Progress every 5 contacts
            if i % 5 == 0 or i == total:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"\n--- Progress: {i}/{total} "
                      f"(saved={self.stats['saved']}, skipped={self.stats['skipped_low_confidence']}, "
                      f"errors={self.stats['errors']}) "
                      f"[{rate:.2f}/sec, {elapsed:.0f}s elapsed] ---\n")

        elapsed = time.time() - start_time
        self.print_summary(elapsed)

        # Re-score if requested
        if self.re_score:
            self.run_re_scoring()

        return self.stats["errors"] < max(total * 0.2, 1)

    def print_summary(self, elapsed: float):
        s = self.stats
        pplx_cost = s["perplexity_tokens"] * 3.0 / 1_000_000  # sonar-pro ~$3/1M
        gpt_input_cost = s["gpt_input_tokens"] * 0.15 / 1_000_000
        gpt_output_cost = s["gpt_output_tokens"] * 0.60 / 1_000_000
        total_cost = pplx_cost + gpt_input_cost + gpt_output_cost

        print("\n" + "=" * 60)
        print("WEB RESEARCH ENRICHMENT SUMMARY")
        print("=" * 60)
        print(f"  Contacts researched: {s['researched']}")
        print(f"  Profiles saved:      {s['saved']}")
        print(f"  Low confidence skip: {s['skipped_low_confidence']}")
        print(f"  Errors:              {s['errors']}")
        print(f"  Perplexity tokens:   {s['perplexity_tokens']:,}")
        print(f"  GPT tokens (in/out): {s['gpt_input_tokens']:,} / {s['gpt_output_tokens']:,}")
        print(f"  Est. cost:           ${total_cost:.2f}")
        print(f"  Time elapsed:        {elapsed:.1f}s")
        if s["researched"] > 0:
            print(f"  Avg time/contact:    {elapsed / s['researched']:.1f}s")
        print("=" * 60)


def _strip_null_bytes(obj):
    """Recursively strip null bytes from strings in a dict/list for PostgreSQL JSONB compatibility."""
    if isinstance(obj, str):
        return obj.replace("\x00", "")
    if isinstance(obj, dict):
        return {k: _strip_null_bytes(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_null_bytes(item) for item in obj]
    return obj


def main():
    parser = argparse.ArgumentParser(
        description="Enrich contacts with web research via Perplexity + GPT-5 mini"
    )
    parser.add_argument("--discover", "-d", action="store_true",
                        help="Auto-discover contacts needing web research")
    parser.add_argument("--ids", type=str, default=None,
                        help="Comma-separated list of contact IDs (e.g., '1933,1958,2641')")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-research contacts already web-researched")
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only 1 contact for validation")
    parser.add_argument("--batch", "-b", type=int, default=None,
                        help="Process N contacts")
    parser.add_argument("--re-score", "-r", action="store_true",
                        help="After enrichment, re-run AI tagging and ask-readiness scoring")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be researched without calling APIs")
    args = parser.parse_args()

    ids_list = None
    if args.ids:
        ids_list = [int(x.strip()) for x in args.ids.split(",") if x.strip()]

    if not args.ids and not args.discover:
        print("ERROR: Must specify --ids or --discover")
        sys.exit(1)

    enricher = WebResearchEnricher(
        discover=args.discover,
        ids=ids_list,
        force=args.force,
        test_mode=args.test,
        batch_size=args.batch,
        re_score=args.re_score,
        dry_run=args.dry_run,
    )
    success = enricher.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
