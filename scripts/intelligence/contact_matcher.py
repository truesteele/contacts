"""
Reusable contact matching module.
3-pass strategy: exact name → fuzzy (SequenceMatcher) → GPT-5 mini.

Used by:
  - scrape_post_reactions.py (Justin's post reactions)
  - analyze_influencer.py (influencer post reactions)
"""
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from typing import Optional

from openai import OpenAI, RateLimitError, APIError
from pydantic import BaseModel, Field
from supabase import Client

GPT_MODEL = "gpt-5-mini"
GPT_WORKERS = 50

# ── Name normalization ──────────────────────────────────────────────

NAME_SUFFIXES = re.compile(
    r',?\s*(?:'
    r'Ph\.?D\.?|MBA|MPA|MPH|JD|J\.D\.|Ed\.?L\.?D\.?|MSc|M\.?S\.|M\.?A\.|'
    r'PMP|CRISC|CISM|SPHR|SHRM-SCP|CPA|CFP|CFA|ESQ|Esq\.|'
    r'Jr\.?|Sr\.?|III|II|IV'
    r')\.?', re.IGNORECASE
)

EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0000FE00-\U0000FE0F"
    "\U0000200D\U00002600-\U000026FF\U00002B50-\U00002B55"
    "\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
    "\U0000200B"
    "]+", re.UNICODE
)


def normalize_name(name: str) -> str:
    n = name.strip()
    n = EMOJI_RE.sub("", n)
    n = NAME_SUFFIXES.sub("", n)
    n = re.sub(r'[^\w\s\-\'.]', '', n, flags=re.UNICODE)
    n = re.sub(r'\s+', ' ', n).strip()
    return n.lower()


def split_first_last(name: str) -> tuple[str, str]:
    parts = name.split()
    if len(parts) == 0:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[-1])


# ── GPT matching schema ─────────────────────────────────────────────

class NameMatchResult(BaseModel):
    contact_id: Optional[int] = Field(description="ID of the best-matching contact, or null if no good match")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the match (0-1)")
    reasoning: str = Field(description="Brief explanation of the match decision")


GPT_MATCH_PROMPT = """You are a name-matching expert. Given a person's name and headline from a LinkedIn post reaction, determine which contact in the database (if any) is the same person.

MATCHING RULES:
- Names must refer to the same real person. Similar names for DIFFERENT people should NOT match.
- Use the headline as context — it should be consistent with the contact's known role/company.
- Abbreviated last names (e.g., "Mike B.") can match if the first name + first letter match AND the headline is consistent.
- Name suffixes (PhD, MBA, Jr., etc.) should be ignored for matching.
- Be conservative — if you're not confident, return null for contact_id.
- A confidence of 0.9+ means you're very sure. 0.7-0.89 means probable. Below 0.7, return null."""


# ── ContactMatcher class ────────────────────────────────────────────

class ContactMatcher:
    def __init__(self, sb: Client, openai_client: OpenAI, workers=GPT_WORKERS):
        self.sb = sb
        self.openai = openai_client
        self.workers = workers
        self.contacts_by_name: dict[str, list[dict]] = {}
        self.contacts_by_first: dict[str, list[dict]] = {}
        self.stats = {
            "exact": 0, "fuzzy": 0, "gpt": 0, "unmatched": 0,
            "input_tokens": 0, "output_tokens": 0,
        }

    def load_contacts(self):
        all_contacts = []
        page_size = 1000
        offset = 0
        while True:
            page = (
                self.sb.table("contacts")
                .select("id, first_name, last_name, headline, company, position, linkedin_url")
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

        for c in all_contacts:
            first = (c.get("first_name") or "").strip()
            last = (c.get("last_name") or "").strip()
            if not first:
                continue
            full = normalize_name(f"{first} {last}")
            self.contacts_by_name.setdefault(full, []).append(c)

            first_norm = normalize_name(first)
            self.contacts_by_first.setdefault(first_norm, []).append(c)

        print(f"Loaded {len(all_contacts)} contacts, {len(self.contacts_by_name)} unique names")

    def exact_match(self, reactor_name: str) -> Optional[tuple[int, float]]:
        norm = normalize_name(reactor_name)
        matches = self.contacts_by_name.get(norm)
        if matches and len(matches) == 1:
            return (matches[0]["id"], 1.0)
        return None

    def fuzzy_match(self, reactor_name: str) -> Optional[tuple[int, float]]:
        norm = normalize_name(reactor_name)
        r_first, r_last = split_first_last(norm)

        # Handle abbreviated last names like "Celena G."
        if r_last and len(r_last.rstrip('.')) == 1:
            initial = r_last.rstrip('.')
            candidates = []
            for c in self.contacts_by_first.get(r_first, []):
                c_last = normalize_name(c.get("last_name") or "")
                if c_last and c_last.startswith(initial):
                    candidates.append(c)
            if len(candidates) == 1:
                return (candidates[0]["id"], 0.75)
            return None

        # SequenceMatcher fuzzy
        best_score = 0.0
        best_contact = None
        for cname, contacts in self.contacts_by_name.items():
            score = SequenceMatcher(None, norm, cname).ratio()
            if score > best_score:
                best_score = score
                best_contact = contacts[0] if len(contacts) == 1 else None

        if best_score >= 0.85 and best_contact:
            return (best_contact["id"], best_score)
        return None

    def gpt_match_batch(self, unmatched: list[dict]) -> list[dict]:
        results = []

        def _match_one(item):
            reactor_name = item["reactor_name"]
            headline = item.get("reactor_headline", "") or ""
            norm = normalize_name(reactor_name)
            r_first, _ = split_first_last(norm)

            # Build candidate list
            candidates = []
            seen_ids = set()
            for c in self.contacts_by_first.get(r_first, []):
                candidates.append(c)
                seen_ids.add(c["id"])

            # Add top fuzzy matches
            scored = []
            for cname, contacts in self.contacts_by_name.items():
                score = SequenceMatcher(None, norm, cname).ratio()
                if score >= 0.5:
                    for c in contacts:
                        if c["id"] not in seen_ids:
                            scored.append((score, c))
            scored.sort(key=lambda x: -x[0])
            for _, c in scored[:10]:
                candidates.append(c)
                seen_ids.add(c["id"])

            if not candidates:
                return {**item, "contact_id": None, "confidence": 0.0,
                        "reasoning": "No candidate contacts found"}

            candidate_lines = []
            for c in candidates[:15]:
                cname = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
                cheadline = c.get("headline") or c.get("position") or ""
                candidate_lines.append(f"  ID={c['id']}: {cname} — {cheadline}")

            prompt = (
                f"REACTOR from LinkedIn post:\n"
                f"  Name: {reactor_name}\n"
                f"  Headline: {headline}\n\n"
                f"CANDIDATE CONTACTS in database:\n"
                + "\n".join(candidate_lines)
                + "\n\nWhich contact (if any) is the same person as the reactor?"
            )

            try:
                resp = self.openai.responses.parse(
                    model=GPT_MODEL,
                    instructions=GPT_MATCH_PROMPT,
                    input=prompt,
                    text_format=NameMatchResult,
                )
                if resp.usage:
                    self.stats["input_tokens"] += resp.usage.input_tokens
                    self.stats["output_tokens"] += resp.usage.output_tokens

                if resp.output_parsed:
                    r = resp.output_parsed
                    valid_ids = {c["id"] for c in candidates}
                    if r.contact_id and r.contact_id in valid_ids and r.confidence >= 0.7:
                        return {**item, "contact_id": r.contact_id,
                                "confidence": r.confidence, "reasoning": r.reasoning}
                    return {**item, "contact_id": None, "confidence": 0.0,
                            "reasoning": r.reasoning if r else "Below threshold"}
            except (RateLimitError, APIError) as e:
                print(f"    GPT error for '{reactor_name}': {e}")
            except Exception as e:
                print(f"    Unexpected error for '{reactor_name}': {e}")

            return {**item, "contact_id": None, "confidence": 0.0, "reasoning": "API error"}

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(_match_one, item): item for item in unmatched}
            done = 0
            for future in as_completed(futures):
                done += 1
                try:
                    results.append(future.result())
                except Exception as e:
                    item = futures[future]
                    results.append({**item, "contact_id": None, "confidence": 0.0,
                                    "reasoning": str(e)})
                if done % 50 == 0:
                    print(f"  GPT matching: {done}/{len(unmatched)}...")

        return results

    def match_all(self, reactions: list[dict]) -> list[dict]:
        """3-pass matching. Expects each reaction to have 'reactor' dict with 'name' and 'headline'.
        Returns reactions with _contact_id, _match_method, _match_confidence."""
        unmatched_for_gpt = []

        # Pass 1 & 2: Exact + Fuzzy
        print("\n--- Pass 1-2: Exact + fuzzy name matching ---")
        for r in reactions:
            reactor = r.get("reactor", {})
            name = reactor.get("name", "")
            if not name:
                r["_contact_id"] = None
                r["_match_method"] = "no_name"
                r["_match_confidence"] = 0.0
                self.stats["unmatched"] += 1
                continue

            result = self.exact_match(name)
            if result:
                r["_contact_id"] = result[0]
                r["_match_method"] = "exact"
                r["_match_confidence"] = result[1]
                self.stats["exact"] += 1
                continue

            fuzzy = self.fuzzy_match(name)
            if fuzzy:
                r["_contact_id"] = fuzzy[0]
                r["_match_method"] = "fuzzy"
                r["_match_confidence"] = fuzzy[1]
                self.stats["fuzzy"] += 1
                continue

            # Queue for GPT
            r["_contact_id"] = None
            r["_match_method"] = "pending_gpt"
            r["_match_confidence"] = 0.0
            unmatched_for_gpt.append({
                "reactor_name": name,
                "reactor_headline": reactor.get("headline", ""),
                "idx": reactions.index(r),
            })

        print(f"  Exact: {self.stats['exact']}, Fuzzy: {self.stats['fuzzy']}, "
              f"Need GPT: {len(unmatched_for_gpt)}")

        # Pass 3: GPT
        if unmatched_for_gpt:
            print(f"\n--- Pass 3: GPT matching ({len(unmatched_for_gpt)} reactions) ---")
            gpt_results = self.gpt_match_batch(unmatched_for_gpt)

            for gr in gpt_results:
                idx = gr["idx"]
                if gr["contact_id"]:
                    reactions[idx]["_contact_id"] = gr["contact_id"]
                    reactions[idx]["_match_method"] = "gpt"
                    reactions[idx]["_match_confidence"] = gr["confidence"]
                    self.stats["gpt"] += 1
                else:
                    reactions[idx]["_contact_id"] = None
                    reactions[idx]["_match_method"] = "unmatched"
                    reactions[idx]["_match_confidence"] = 0.0
                    self.stats["unmatched"] += 1

            print(f"  GPT matched: {self.stats['gpt']}, Unmatched: {self.stats['unmatched']}")

        return reactions

    def print_cost(self):
        input_cost = self.stats["input_tokens"] * 0.15 / 1_000_000
        output_cost = self.stats["output_tokens"] * 0.60 / 1_000_000
        if self.stats["input_tokens"] > 0:
            print(f"  GPT tokens: {self.stats['input_tokens']:,} in / {self.stats['output_tokens']:,} out")
            print(f"  GPT cost: ${input_cost + output_cost:.2f}")
