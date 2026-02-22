#!/usr/bin/env python3
"""
Import LinkedIn Article Reactions — Parse, store, and match to contacts.

Parses a markdown file of LinkedIn article reactions, stores each reaction
in the linkedin_article_reactions table, then matches reactors to contacts
using exact name matching, fuzzy matching (difflib), and GPT-5 mini for
ambiguous cases.

Usage:
  python scripts/intelligence/import_article_reactions.py --test          # Parse only, no DB
  python scripts/intelligence/import_article_reactions.py                 # Full import + match
  python scripts/intelligence/import_article_reactions.py --match-only    # Re-run matching on existing data
"""

import os
import re
import sys
import json
import time
import argparse
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from pydantic import BaseModel, Field
from supabase import create_client, Client

load_dotenv()

# ── Constants ────────────────────────────────────────────────────────

REACTION_TYPES = {"like", "insightful", "love", "support", "celebrate", "funny", "curious"}

# Suffixes to strip from names for matching
NAME_SUFFIXES = re.compile(
    r',?\s*(?:'
    r'Ph\.?D\.?|MBA|MPA|MPH|JD|J\.D\.|Ed\.?L\.?D\.?|MSc|M\.?S\.|M\.?A\.|'
    r'PMP|CRISC|CISM|SPHR|SHRM-SCP|CPA|CFP|CFA|ESQ|Esq\.|'
    r'Jr\.?|Sr\.?|III|II|IV'
    r')\.?', re.IGNORECASE
)

# Emoji pattern for stripping
EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002700-\U000027BF"  # dingbats
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero-width joiner
    "\U00002600-\U000026FF"  # misc symbols
    "\U00002B50-\U00002B55"  # stars
    "\U0000231A-\U0000231B"  # watch/hourglass
    "\U000023E9-\U000023F3"  # media
    "\U000023F8-\U000023FA"  # media
    "\U00002934-\U00002935"  # arrows
    "\U000025AA-\U000025AB"  # squares
    "\U000025B6\U000025C0"   # play buttons
    "\U000025FB-\U000025FE"  # squares
    "\U00002602-\U00002660"  # misc
    "\U00002702-\U000027B0"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental
    "\U0001FA00-\U0001FA6F"  # chess
    "\U0001FA70-\U0001FAFF"  # extended-A
    "\U00002139"             # info
    "\U0000200B"             # zero-width space
    "\U00002714\U00002716"   # check/cross marks
    "\U0000D83D"             # surrogate
    "✔️"
    "]+", re.UNICODE
)

MD_FILE = "docs/LinkedIn/LinkedIn Article Reactions.md"


# ── GPT Schema ───────────────────────────────────────────────────────

class NameMatchResult(BaseModel):
    contact_id: Optional[int] = Field(description="ID of the best-matching contact, or null if no good match")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the match (0-1)")
    reasoning: str = Field(description="Brief explanation of why this match was chosen or rejected")


GPT_MATCH_PROMPT = """You are a name-matching expert. Given a person's name and headline from a LinkedIn article reaction, determine which contact in the database (if any) is the same person.

MATCHING RULES:
- Names must refer to the same real person. Similar names for DIFFERENT people should NOT match.
- Use the headline as context — it should be consistent with the contact's known role/company.
- Abbreviated last names (e.g., "Mike B.") can match if the first name + first letter match AND the headline is consistent.
- Name suffixes (PhD, MBA, Jr., etc.) should be ignored for matching.
- Be conservative — if you're not confident, return null for contact_id.
- A confidence of 0.9+ means you're very sure. 0.7-0.89 means probable. Below 0.7, return null."""


# ── Parsing ──────────────────────────────────────────────────────────

def parse_reactions_file(filepath: str) -> list[dict]:
    """Parse the LinkedIn article reactions markdown file.

    Returns a list of dicts with keys:
        article_title, reaction_type, reactor_name, reactor_headline, connection_degree
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    reactions = []
    current_article = None
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # Skip blank lines
        if not line.strip():
            i += 1
            continue

        # Check if this line is a reaction type
        stripped = line.strip()
        if stripped in REACTION_TYPES:
            reaction_type = stripped

            # Next non-blank line should be the name
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i >= len(lines):
                break

            reactor_name = lines[i].strip()

            # Next line: "View {name}'s profile ..."
            i += 1
            connection_degree = None
            if i < len(lines) and lines[i].strip().startswith("View "):
                view_line = lines[i].strip()
                if "1st degree" in view_line:
                    connection_degree = "1st"
                elif "2nd degree" in view_line:
                    connection_degree = "2nd"
                elif "3rd degree" in view_line or "3rd+" in view_line:
                    connection_degree = "3rd+"
                i += 1

            # Next line: "· 1st" or "· 2nd" etc.
            if i < len(lines) and lines[i].strip().startswith("·"):
                degree_line = lines[i].strip()
                if not connection_degree:
                    if "1st" in degree_line:
                        connection_degree = "1st"
                    elif "2nd" in degree_line:
                        connection_degree = "2nd"
                    elif "3rd" in degree_line:
                        connection_degree = "3rd+"
                i += 1

            # Next non-blank line: headline
            reactor_headline = None
            if i < len(lines) and lines[i].strip() and not lines[i].strip() in REACTION_TYPES:
                # Check it's not the start of a new reaction or article
                candidate = lines[i].strip()
                if not candidate.startswith("View ") and not candidate.startswith("·"):
                    reactor_headline = candidate
                    i += 1

            if current_article and reactor_name:
                reactions.append({
                    "article_title": current_article,
                    "reaction_type": reaction_type,
                    "reactor_name": reactor_name,
                    "reactor_headline": reactor_headline,
                    "connection_degree": connection_degree,
                })
            continue

        # Check if this is a "View..." or "·" line (orphaned, skip)
        if stripped.startswith("View ") or stripped.startswith("·"):
            i += 1
            continue

        # Otherwise, this is an article title
        current_article = stripped
        i += 1

    return reactions


# ── Name Normalization ───────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """Normalize a name for matching: strip suffixes, emoji, extra whitespace, lowercase."""
    n = name.strip()
    # Remove emoji
    n = EMOJI_RE.sub("", n)
    # Remove suffixes
    n = NAME_SUFFIXES.sub("", n)
    # Remove special unicode chars (keep letters, spaces, hyphens, apostrophes, periods)
    n = re.sub(r'[^\w\s\-\'.]', '', n, flags=re.UNICODE)
    # Collapse whitespace
    n = re.sub(r'\s+', ' ', n).strip()
    return n.lower()


def split_first_last(name: str) -> tuple[str, str]:
    """Split a normalized name into (first, last). Handles multi-word names."""
    parts = name.split()
    if len(parts) == 0:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[-1])


# ── Matching ─────────────────────────────────────────────────────────

class ReactionImporter:
    MODEL = "gpt-5-mini"

    def __init__(self, test_mode=False, match_only=False, workers=50):
        self.test_mode = test_mode
        self.match_only = match_only
        self.workers = workers
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.contacts_by_name: dict[str, list[dict]] = {}  # normalized_name -> [contacts]
        self.all_contact_names: list[str] = []  # for fuzzy matching
        self.stats = {
            "parsed": 0, "inserted": 0,
            "exact": 0, "fuzzy": 0, "gpt": 0, "unmatched": 0,
            "input_tokens": 0, "output_tokens": 0,
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

    def load_contacts(self):
        """Load all contacts and build name lookup index."""
        all_contacts = []
        page_size = 1000
        offset = 0
        while True:
            page = (
                self.supabase.table("contacts")
                .select("id, first_name, last_name, headline, company, position")
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

        # Build lookup index: normalized "first last" -> list of contacts
        for c in all_contacts:
            first = (c.get("first_name") or "").strip()
            last = (c.get("last_name") or "").strip()
            if not first:
                continue
            full = normalize_name(f"{first} {last}")
            if full not in self.contacts_by_name:
                self.contacts_by_name[full] = []
            self.contacts_by_name[full].append(c)
            self.all_contact_names.append(full)

        # Also build first-name-only and first+last-initial indexes
        self.contacts_by_first = {}
        for c in all_contacts:
            first = normalize_name(c.get("first_name") or "")
            last = normalize_name(c.get("last_name") or "")
            if first:
                key = first
                if key not in self.contacts_by_first:
                    self.contacts_by_first[key] = []
                self.contacts_by_first[key].append(c)

        print(f"Loaded {len(all_contacts)} contacts, {len(self.contacts_by_name)} unique normalized names")

    def exact_match(self, reactor_name: str) -> Optional[tuple[int, float]]:
        """Try exact match on normalized name. Returns (contact_id, confidence) or None."""
        norm = normalize_name(reactor_name)
        matches = self.contacts_by_name.get(norm)
        if matches and len(matches) == 1:
            return (matches[0]["id"], 1.0)
        if matches and len(matches) > 1:
            # Multiple contacts with same name — can't resolve without GPT
            return None
        return None

    def fuzzy_match(self, reactor_name: str) -> Optional[tuple[int, float, str]]:
        """Try fuzzy match. Returns (contact_id, confidence, method) or None."""
        norm = normalize_name(reactor_name)
        r_first, r_last = split_first_last(norm)

        # Handle abbreviated last names like "Mike B." or "Faybra J."
        if r_last and len(r_last.rstrip('.')) == 1:
            initial = r_last.rstrip('.')
            candidates = []
            for c in self.contacts_by_first.get(r_first, []):
                c_last = normalize_name(c.get("last_name") or "")
                if c_last and c_last.startswith(initial):
                    candidates.append(c)
            if len(candidates) == 1:
                return (candidates[0]["id"], 0.75, "fuzzy")
            elif len(candidates) > 1:
                return None  # Need GPT
            return None

        # Standard fuzzy match using SequenceMatcher
        best_score = 0.0
        best_contact = None
        best_name = None

        for cname, contacts in self.contacts_by_name.items():
            score = SequenceMatcher(None, norm, cname).ratio()
            if score > best_score:
                best_score = score
                best_contact = contacts[0] if len(contacts) == 1 else None
                best_name = cname

        if best_score >= 0.85 and best_contact:
            return (best_contact["id"], best_score, "fuzzy")

        return None

    def gpt_match_batch(self, unmatched: list[dict]) -> list[dict]:
        """Use GPT-5 mini to match a batch of unmatched reactors to contacts.

        Each item in unmatched has: reactor_name, reactor_headline, reaction_id,
            and optionally 'candidates' (list of potential contact matches).
        """
        results = []

        def _match_one(item):
            reactor_name = item["reactor_name"]
            headline = item.get("reactor_headline", "") or ""
            norm = normalize_name(reactor_name)
            r_first, r_last = split_first_last(norm)

            # Build candidate list from contacts
            candidates = item.get("candidates", [])
            if not candidates:
                # Find candidates by first name or fuzzy
                for c in self.contacts_by_first.get(r_first, []):
                    candidates.append(c)

                # Also add top fuzzy matches
                scored = []
                for cname, contacts in self.contacts_by_name.items():
                    score = SequenceMatcher(None, norm, cname).ratio()
                    if score >= 0.5:
                        for c in contacts:
                            scored.append((score, c))
                scored.sort(key=lambda x: -x[0])
                for score, c in scored[:10]:
                    if c["id"] not in {x["id"] for x in candidates}:
                        candidates.append(c)

            if not candidates:
                return {"reaction_id": item["reaction_id"], "contact_id": None,
                        "confidence": 0.0, "reasoning": "No candidate contacts found"}

            # Build GPT input
            candidate_lines = []
            for c in candidates[:15]:  # Cap at 15
                cname = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
                cheadline = c.get("headline") or c.get("position") or ""
                candidate_lines.append(f"  ID={c['id']}: {cname} — {cheadline}")

            prompt = (
                f"REACTOR from LinkedIn article:\n"
                f"  Name: {reactor_name}\n"
                f"  Headline: {headline}\n\n"
                f"CANDIDATE CONTACTS in database:\n"
                + "\n".join(candidate_lines)
                + "\n\nWhich contact (if any) is the same person as the reactor?"
            )

            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions=GPT_MATCH_PROMPT,
                    input=prompt,
                    text_format=NameMatchResult,
                )
                if resp.usage:
                    self.stats["input_tokens"] += resp.usage.input_tokens
                    self.stats["output_tokens"] += resp.usage.output_tokens

                if resp.output_parsed:
                    r = resp.output_parsed
                    # Validate the returned ID is actually in our candidates
                    valid_ids = {c["id"] for c in candidates}
                    if r.contact_id and r.contact_id in valid_ids and r.confidence >= 0.7:
                        return {"reaction_id": item["reaction_id"],
                                "contact_id": r.contact_id,
                                "confidence": r.confidence,
                                "reasoning": r.reasoning}
                    return {"reaction_id": item["reaction_id"],
                            "contact_id": None, "confidence": 0.0,
                            "reasoning": r.reasoning if r else "No match above threshold"}
            except (RateLimitError, APIError) as e:
                print(f"    GPT error for '{reactor_name}': {e}")
                return {"reaction_id": item["reaction_id"], "contact_id": None,
                        "confidence": 0.0, "reasoning": f"API error: {e}"}
            except Exception as e:
                print(f"    Unexpected error for '{reactor_name}': {e}")
                return {"reaction_id": item["reaction_id"], "contact_id": None,
                        "confidence": 0.0, "reasoning": str(e)}

            return {"reaction_id": item["reaction_id"], "contact_id": None,
                    "confidence": 0.0, "reasoning": "No parsed output"}

        # Run GPT calls concurrently
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(_match_one, item): item for item in unmatched}
            done = 0
            for future in as_completed(futures):
                done += 1
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    item = futures[future]
                    print(f"  GPT error: {e}")
                    results.append({"reaction_id": item["reaction_id"],
                                    "contact_id": None, "confidence": 0.0,
                                    "reasoning": str(e)})
                if done % 50 == 0:
                    print(f"  GPT matching: {done}/{len(unmatched)}...")

        return results

    def insert_reactions(self, reactions: list[dict]) -> list[dict]:
        """Insert parsed reactions into the DB. Returns list with IDs."""
        inserted = []
        batch_size = 100

        for i in range(0, len(reactions), batch_size):
            batch = reactions[i:i+batch_size]
            rows = [{
                "article_title": r["article_title"],
                "reaction_type": r["reaction_type"],
                "reactor_name": r["reactor_name"],
                "reactor_headline": r.get("reactor_headline"),
                "connection_degree": r.get("connection_degree"),
            } for r in batch]

            try:
                result = self.supabase.table("linkedin_article_reactions").insert(rows).execute()
                if result.data:
                    inserted.extend(result.data)
                    self.stats["inserted"] += len(result.data)
            except Exception as e:
                print(f"  Insert error at batch {i}: {e}")

        print(f"Inserted {self.stats['inserted']} reactions")
        return inserted

    def match_reactions(self, reactions: list[dict]):
        """Match reactions to contacts using 3-pass strategy."""
        unmatched_for_gpt = []
        updates = []  # (reaction_id, contact_id, method, confidence)

        # Pass 1: Exact match
        print("\n--- Pass 1: Exact name matching ---")
        for r in reactions:
            result = self.exact_match(r["reactor_name"])
            if result:
                contact_id, confidence = result
                updates.append((r["id"], contact_id, "exact", confidence))
                self.stats["exact"] += 1
            else:
                # Pass 2: Fuzzy match
                fuzzy = self.fuzzy_match(r["reactor_name"])
                if fuzzy:
                    contact_id, confidence, method = fuzzy
                    updates.append((r["id"], contact_id, "fuzzy", confidence))
                    self.stats["fuzzy"] += 1
                else:
                    unmatched_for_gpt.append({
                        "reaction_id": r["id"],
                        "reactor_name": r["reactor_name"],
                        "reactor_headline": r.get("reactor_headline"),
                    })

        print(f"  Exact: {self.stats['exact']}, Fuzzy: {self.stats['fuzzy']}, "
              f"Need GPT: {len(unmatched_for_gpt)}")

        # Save exact + fuzzy matches
        self._save_matches(updates)

        # Pass 3: GPT for remaining
        if unmatched_for_gpt:
            print(f"\n--- Pass 3: GPT matching ({len(unmatched_for_gpt)} reactions) ---")
            gpt_results = self.gpt_match_batch(unmatched_for_gpt)

            gpt_updates = []
            for gr in gpt_results:
                if gr["contact_id"]:
                    gpt_updates.append((gr["reaction_id"], gr["contact_id"], "gpt", gr["confidence"]))
                    self.stats["gpt"] += 1
                else:
                    gpt_updates.append((gr["reaction_id"], None, "unmatched", 0.0))
                    self.stats["unmatched"] += 1

            self._save_matches(gpt_updates)
            print(f"  GPT matched: {self.stats['gpt']}, Unmatched: {self.stats['unmatched']}")

    def _save_matches(self, updates: list[tuple]):
        """Save match results to DB."""
        for reaction_id, contact_id, method, confidence in updates:
            try:
                self.supabase.table("linkedin_article_reactions").update({
                    "contact_id": contact_id,
                    "match_method": method,
                    "match_confidence": confidence,
                }).eq("id", reaction_id).execute()
            except Exception as e:
                print(f"  Update error for reaction {reaction_id}: {e}")

    def build_contact_summaries(self):
        """Build linkedin_reactions JSONB summary for each matched contact."""
        print("\n--- Building contact reaction summaries ---")

        # Fetch all matched reactions
        all_reactions = []
        page_size = 1000
        offset = 0
        while True:
            page = (
                self.supabase.table("linkedin_article_reactions")
                .select("contact_id, article_title, reaction_type")
                .not_.is_("contact_id", "null")
                .order("id")
                .range(offset, offset + page_size - 1)
                .execute()
            ).data
            if not page:
                break
            all_reactions.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        # Group by contact_id
        by_contact: dict[int, list[dict]] = {}
        for r in all_reactions:
            cid = r["contact_id"]
            if cid not in by_contact:
                by_contact[cid] = []
            by_contact[cid].append(r)

        # Build and save summaries
        updated = 0
        for contact_id, rlist in by_contact.items():
            reaction_types = {}
            articles = set()
            for r in rlist:
                rtype = r["reaction_type"]
                reaction_types[rtype] = reaction_types.get(rtype, 0) + 1
                articles.add(r["article_title"])

            summary = {
                "total_reactions": len(rlist),
                "reaction_types": reaction_types,
                "articles_reacted_to": sorted(articles),
                "article_count": len(articles),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            try:
                self.supabase.table("contacts").update({
                    "linkedin_reactions": summary,
                }).eq("id", contact_id).execute()
                updated += 1
            except Exception as e:
                print(f"  Summary error for contact {contact_id}: {e}")

        print(f"Updated linkedin_reactions for {updated} contacts")

    def run(self):
        if not self.connect():
            return False

        self.load_contacts()

        if self.match_only:
            # Re-run matching on existing data
            print("Re-matching existing reactions...")
            all_reactions = []
            offset = 0
            while True:
                page = (
                    self.supabase.table("linkedin_article_reactions")
                    .select("id, reactor_name, reactor_headline, connection_degree")
                    .order("id")
                    .range(offset, offset + 999)
                    .execute()
                ).data
                if not page:
                    break
                all_reactions.extend(page)
                if len(page) < 1000:
                    break
                offset += 1000

            print(f"Loaded {len(all_reactions)} existing reactions to re-match")
            self.match_reactions(all_reactions)
            self.build_contact_summaries()
            self.print_summary()
            return True

        # Parse the file
        filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), MD_FILE)
        if not os.path.exists(filepath):
            # Try from CWD
            filepath = MD_FILE
        print(f"Parsing {filepath}...")
        reactions = parse_reactions_file(filepath)
        self.stats["parsed"] = len(reactions)
        print(f"Parsed {len(reactions)} reactions across "
              f"{len(set(r['article_title'] for r in reactions))} articles")

        # Show article summary
        article_counts = {}
        for r in reactions:
            article_counts[r["article_title"]] = article_counts.get(r["article_title"], 0) + 1
        print("\nArticles:")
        for title, count in sorted(article_counts.items(), key=lambda x: -x[1]):
            print(f"  {count:4d} reactions — {title[:80]}")

        if self.test_mode:
            print("\n--- TEST MODE: Skipping DB operations ---")
            # Show sample
            for r in reactions[:10]:
                print(f"  {r['reaction_type']:12s} | {r['reactor_name']:30s} | {r['article_title'][:40]}")
            return True

        # Clear existing data (fresh import)
        print("\nClearing existing reactions...")
        self.supabase.table("linkedin_article_reactions").delete().neq("id", 0).execute()

        # Insert
        print("Inserting reactions...")
        inserted = self.insert_reactions(reactions)

        # Match
        self.match_reactions(inserted)

        # Build summaries
        self.build_contact_summaries()

        self.print_summary()
        return True

    def print_summary(self):
        input_cost = self.stats["input_tokens"] * 0.15 / 1_000_000
        output_cost = self.stats["output_tokens"] * 0.60 / 1_000_000
        total_cost = input_cost + output_cost

        total_matched = self.stats["exact"] + self.stats["fuzzy"] + self.stats["gpt"]
        total_processed = total_matched + self.stats["unmatched"]

        print("\n" + "=" * 60)
        print("LINKEDIN ARTICLE REACTIONS — IMPORT SUMMARY")
        print("=" * 60)
        print(f"  Reactions parsed:      {self.stats['parsed']}")
        print(f"  Reactions inserted:    {self.stats['inserted']}")
        print()
        print("  MATCHING:")
        print(f"    Exact match:         {self.stats['exact']}")
        print(f"    Fuzzy match:         {self.stats['fuzzy']}")
        print(f"    GPT match:           {self.stats['gpt']}")
        print(f"    Unmatched:           {self.stats['unmatched']}")
        print(f"    ─────────────────────────────")
        print(f"    Total matched:       {total_matched}/{total_processed} "
              f"({100*total_matched/total_processed:.1f}%)" if total_processed > 0 else "")
        print()
        if self.stats["input_tokens"] > 0:
            print(f"  GPT tokens:            {self.stats['input_tokens']:,} in / {self.stats['output_tokens']:,} out")
            print(f"  GPT cost:              ${total_cost:.2f}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Import LinkedIn article reactions and match to contacts")
    parser.add_argument("--test", "-t", action="store_true", help="Parse only, no DB operations")
    parser.add_argument("--match-only", action="store_true", help="Re-run matching on existing data")
    parser.add_argument("--workers", "-w", type=int, default=50, help="GPT workers (default: 50)")
    args = parser.parse_args()

    importer = ReactionImporter(
        test_mode=args.test,
        match_only=args.match_only,
        workers=args.workers,
    )
    success = importer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
