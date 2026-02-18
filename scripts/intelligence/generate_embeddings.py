#!/usr/bin/env python3
"""
Network Intelligence — Embedding Generation via text-embedding-3-small

Generates two embeddings per contact:
1. profile_embedding (768 dims) — career, education, skills, volunteering, location
2. interests_embedding (768 dims) — LLM-generated topics + talking points + summary + headline

Uses OpenAI's batch embedding API (up to 100 texts per call) for efficiency.

Usage:
  python scripts/intelligence/generate_embeddings.py --test        # Process 10 contacts
  python scripts/intelligence/generate_embeddings.py --test -n 20  # Process 20 contacts
  python scripts/intelligence/generate_embeddings.py --dry-run     # Build texts, no API calls
  python scripts/intelligence/generate_embeddings.py               # Full run (all contacts)
  python scripts/intelligence/generate_embeddings.py --force       # Re-embed already-embedded contacts
"""

import os
import sys
import json
import time
import argparse
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from supabase import create_client, Client

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 768
BATCH_SIZE = 100  # OpenAI supports up to 2048, but 100 keeps requests manageable
PAGE_SIZE = 1000

SELECT_COLS = (
    "id, first_name, last_name, headline, summary, company, position, "
    "city, state, ai_tags, profile_embedding, interests_embedding, "
    "enrich_employment, enrich_education, enrich_skills_detailed, "
    "enrich_volunteering"
)


def parse_jsonb(val):
    """Parse a JSONB field that may be a string or already parsed."""
    if val is None:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            return val
    return val


def build_profile_text(contact: dict) -> str:
    """Build a profile text document for embedding.

    Format:
      {name} | {headline}
      Currently: {title} at {company}
      Previously: {company1} ({title1}), ...
      Education: {school1} ({degree1}), ...
      Skills: {skill1}, ...
      Volunteering: {org1} ({role1}), ...
      Location: {city}, {state}
      About: {summary}
    """
    parts = []
    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

    # Name | Headline
    headline = contact.get("headline", "")
    if headline:
        parts.append(f"{name} | {headline}")
    else:
        parts.append(name)

    # Current role
    company = contact.get("company", "")
    position = contact.get("position", "")
    if company or position:
        parts.append(f"Currently: {position or '?'} at {company or '?'}")

    # Employment history
    employment = parse_jsonb(contact.get("enrich_employment"))
    if employment and isinstance(employment, list):
        prev = []
        for job in employment:
            if isinstance(job, dict):
                co = job.get("company_name", job.get("company", ""))
                title = job.get("title", "")
                if co:
                    prev.append(f"{co} ({title})" if title else co)
        if prev:
            parts.append(f"Previously: {', '.join(prev[:10])}")

    # Education
    education = parse_jsonb(contact.get("enrich_education"))
    if education and isinstance(education, list):
        schools = []
        for edu in education:
            if isinstance(edu, dict):
                school = edu.get("school_name", edu.get("school", ""))
                degree = edu.get("degree", "")
                field = edu.get("field_of_study", "")
                desc = degree
                if field:
                    desc = f"{degree}, {field}" if degree else field
                if school:
                    schools.append(f"{school} ({desc})" if desc else school)
        if schools:
            parts.append(f"Education: {', '.join(schools)}")

    # Skills
    skills = parse_jsonb(contact.get("enrich_skills_detailed"))
    if skills and isinstance(skills, list):
        skill_names = []
        for s in skills:
            if isinstance(s, dict):
                skill_names.append(s.get("skill_name", ""))
            elif isinstance(s, str):
                skill_names.append(s)
        skill_names = [s for s in skill_names if s]
        if skill_names:
            parts.append(f"Skills: {', '.join(skill_names[:20])}")

    # Volunteering
    volunteering = parse_jsonb(contact.get("enrich_volunteering"))
    if volunteering and isinstance(volunteering, list):
        vol = []
        for v in volunteering:
            if isinstance(v, dict):
                org = v.get("organization", v.get("company_name", ""))
                role = v.get("role", v.get("title", ""))
                if org:
                    vol.append(f"{org} ({role})" if role else org)
        if vol:
            parts.append(f"Volunteering: {', '.join(vol[:10])}")

    # Location
    city = contact.get("city", "")
    state = contact.get("state", "")
    loc = ", ".join(filter(None, [city, state]))
    if loc:
        parts.append(f"Location: {loc}")

    # Summary / About
    summary = contact.get("summary", "")
    if summary:
        # Truncate very long summaries to keep embedding focused
        if len(summary) > 1000:
            summary = summary[:1000] + "..."
        parts.append(f"About: {summary}")

    return "\n".join(parts)


def build_interests_text(contact: dict) -> str:
    """Build an interests text document for embedding.

    Uses LLM-generated tags from ai_tags (topical_affinity.topics, talking_points)
    + summary + headline. Falls back to raw enrichment data if ai_tags is missing.
    """
    parts = []

    ai_tags = parse_jsonb(contact.get("ai_tags"))

    if ai_tags and isinstance(ai_tags, dict):
        topical = ai_tags.get("topical_affinity", {})

        # Topics with strength
        topics = topical.get("topics", [])
        if topics:
            topic_strs = []
            for t in topics:
                if isinstance(t, dict):
                    topic_strs.append(t.get("topic", ""))
                elif isinstance(t, str):
                    topic_strs.append(t)
            topic_strs = [t for t in topic_strs if t]
            if topic_strs:
                parts.append(f"Topics: {', '.join(topic_strs)}")

        # Primary interests
        primary = topical.get("primary_interests", [])
        if primary:
            parts.append(f"Primary interests: {', '.join(primary)}")

        # Talking points
        talking = topical.get("talking_points", [])
        if talking:
            parts.append(f"Talking points: {'; '.join(talking)}")

        # Outreach context
        outreach = ai_tags.get("outreach_context", {})
        hooks = outreach.get("personalization_hooks", [])
        if hooks:
            parts.append(f"Context: {'; '.join(hooks[:3])}")

    # Always include headline and summary as baseline signals
    headline = contact.get("headline", "")
    if headline:
        parts.append(f"Headline: {headline}")

    summary = contact.get("summary", "")
    if summary:
        if len(summary) > 500:
            summary = summary[:500] + "..."
        parts.append(f"About: {summary}")

    # Fallback: if no ai_tags, use skills and volunteering for interest signals
    if not ai_tags or not isinstance(ai_tags, dict):
        skills = parse_jsonb(contact.get("enrich_skills_detailed"))
        if skills and isinstance(skills, list):
            skill_names = []
            for s in skills:
                if isinstance(s, dict):
                    skill_names.append(s.get("skill_name", ""))
                elif isinstance(s, str):
                    skill_names.append(s)
            skill_names = [s for s in skill_names if s]
            if skill_names:
                parts.append(f"Skills: {', '.join(skill_names[:15])}")

        volunteering = parse_jsonb(contact.get("enrich_volunteering"))
        if volunteering and isinstance(volunteering, list):
            vol = []
            for v in volunteering:
                if isinstance(v, dict):
                    org = v.get("organization", v.get("company_name", ""))
                    cause = v.get("cause", "")
                    if org:
                        vol.append(f"{org} ({cause})" if cause else org)
            if vol:
                parts.append(f"Volunteering: {', '.join(vol[:10])}")

    return "\n".join(parts) if parts else ""


class EmbeddingGenerator:

    def __init__(self, test_mode=False, dry_run=False, force=False, test_count=10):
        self.test_mode = test_mode
        self.dry_run = dry_run
        self.force = force
        self.test_count = test_count
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.stats = {
            "processed": 0,
            "skipped_empty": 0,
            "errors": 0,
            "total_tokens": 0,
            "api_calls": 0,
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
        print(f"Connected to Supabase{' and OpenAI' if not self.dry_run else ' (dry-run)'}")
        return True

    def get_contacts(self) -> list[dict]:
        """Fetch contacts that need embeddings."""
        all_contacts = []
        offset = 0

        while True:
            query = (
                self.supabase.table("contacts")
                .select(SELECT_COLS)
                .order("id")
                .range(offset, offset + PAGE_SIZE - 1)
            )

            if not self.force:
                query = query.is_("profile_embedding", "null")

            response = query.execute()
            page = response.data
            if not page:
                break

            all_contacts.extend(page)
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        if self.test_mode:
            all_contacts = all_contacts[:self.test_count]

        return all_contacts

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI embedding API for a batch of texts. Returns list of vectors."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.openai.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts,
                    dimensions=EMBEDDING_DIMS,
                )
                self.stats["api_calls"] += 1
                self.stats["total_tokens"] += response.usage.total_tokens
                return [item.embedding for item in response.data]
            except RateLimitError:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            except APIError as e:
                print(f"  API error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise
        return []

    def save_embeddings(self, contact_id: int,
                        profile_vec: list[float],
                        interests_vec: Optional[list[float]]) -> bool:
        """Save embedding vectors to Supabase."""
        updates = {"profile_embedding": profile_vec}
        if interests_vec is not None:
            updates["interests_embedding"] = interests_vec
        try:
            self.supabase.table("contacts").update(updates).eq("id", contact_id).execute()
            return True
        except Exception as e:
            print(f"  DB error for id={contact_id}: {e}")
            return False

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()
        contacts = self.get_contacts()
        total = len(contacts)
        print(f"Found {total} contacts to embed")

        if total == 0:
            print("Nothing to do — all contacts already have embeddings (use --force to re-embed)")
            return True

        # Build all text documents first
        print(f"Building text documents...")
        profile_texts = {}  # id -> text
        interests_texts = {}  # id -> text
        for c in contacts:
            cid = c["id"]
            profile_texts[cid] = build_profile_text(c)
            interests_texts[cid] = build_interests_text(c)

        if self.dry_run:
            self._dry_run_report(contacts, profile_texts, interests_texts)
            return True

        # Process in batches
        contact_ids = [c["id"] for c in contacts]
        processed = 0

        for batch_start in range(0, len(contact_ids), BATCH_SIZE):
            batch_ids = contact_ids[batch_start:batch_start + BATCH_SIZE]
            batch_profiles = [profile_texts[cid] for cid in batch_ids]
            batch_interests_raw = [interests_texts[cid] for cid in batch_ids]

            # Filter empty interests texts — embed non-empty ones only
            # We still need to track which ids have interests vs not
            interests_with_idx = [
                (i, text) for i, text in enumerate(batch_interests_raw) if text.strip()
            ]

            try:
                # Embed profile texts (all should have content)
                profile_vecs = self.generate_embeddings_batch(batch_profiles)
                if not profile_vecs:
                    print(f"  ERROR: Failed to get profile embeddings for batch at {batch_start}")
                    self.stats["errors"] += len(batch_ids)
                    continue

                # Embed interests texts (only non-empty)
                interests_vecs_map = {}  # local idx -> vector
                if interests_with_idx:
                    interests_texts_only = [t for _, t in interests_with_idx]
                    interests_vecs = self.generate_embeddings_batch(interests_texts_only)
                    if interests_vecs:
                        for vec_idx, (local_idx, _) in enumerate(interests_with_idx):
                            interests_vecs_map[local_idx] = interests_vecs[vec_idx]

                # Save to DB
                for i, cid in enumerate(batch_ids):
                    profile_vec = profile_vecs[i]
                    interests_vec = interests_vecs_map.get(i, None)

                    if self.save_embeddings(cid, profile_vec, interests_vec):
                        self.stats["processed"] += 1
                    else:
                        self.stats["errors"] += 1

                    if not interests_vec and batch_interests_raw[i].strip() == "":
                        self.stats["skipped_empty"] += 1

            except Exception as e:
                print(f"  ERROR in batch at {batch_start}: {e}")
                self.stats["errors"] += len(batch_ids)
                continue

            processed += len(batch_ids)
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            print(f"  Progress: {processed}/{total} ({rate:.1f} contacts/sec, {elapsed:.0f}s elapsed)")

        elapsed = time.time() - start_time
        self._print_summary(elapsed)
        return self.stats["errors"] < total * 0.05

    def _dry_run_report(self, contacts, profile_texts, interests_texts):
        total = len(contacts)
        total_profile_chars = sum(len(t) for t in profile_texts.values())
        total_interests_chars = sum(len(t) for t in interests_texts.values())
        empty_interests = sum(1 for t in interests_texts.values() if not t.strip())
        est_tokens = (total_profile_chars + total_interests_chars) // 4

        print(f"\n--- DRY RUN COMPLETE ---")
        print(f"  Total contacts: {total}")
        print(f"  Profile texts: {total} (avg {total_profile_chars // total} chars each)")
        print(f"  Interests texts: {total - empty_interests} non-empty, {empty_interests} empty")
        print(f"  Est. total tokens: ~{est_tokens:,}")
        print(f"  Est. API calls: ~{(total * 2) // BATCH_SIZE + 2}")
        cost = est_tokens * 0.02 / 1_000_000
        print(f"  Est. cost: ~${cost:.4f}")

        # Show sample texts
        print(f"\n--- Sample Profile Text (first contact) ---")
        first_id = list(profile_texts.keys())[0]
        print(profile_texts[first_id][:500])
        print(f"\n--- Sample Interests Text (first contact) ---")
        print(interests_texts[first_id][:500])

    def _print_summary(self, elapsed: float):
        s = self.stats
        cost = s["total_tokens"] * 0.02 / 1_000_000

        print("\n" + "=" * 60)
        print("EMBEDDING GENERATION SUMMARY")
        print("=" * 60)
        print(f"  Contacts embedded:    {s['processed']}")
        print(f"  Empty interests:      {s['skipped_empty']}")
        print(f"  Errors:               {s['errors']}")
        print(f"  Total tokens:         {s['total_tokens']:,}")
        print(f"  API calls:            {s['api_calls']}")
        print(f"  Cost:                 ${cost:.4f}")
        print(f"  Time elapsed:         {elapsed:.1f}s")
        if s["processed"] > 0:
            print(f"  Avg time/contact:     {elapsed / s['processed']:.3f}s")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate profile and interests embeddings for contacts"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only N contacts for validation (default: 10)")
    parser.add_argument("--count", "-n", type=int, default=10,
                        help="Number of contacts to process in test mode (default: 10)")
    parser.add_argument("--dry-run", "-d", action="store_true",
                        help="Build texts but don't call OpenAI")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-embed contacts that already have embeddings")
    args = parser.parse_args()

    generator = EmbeddingGenerator(
        test_mode=args.test,
        dry_run=args.dry_run,
        force=args.force,
        test_count=args.count,
    )
    success = generator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
