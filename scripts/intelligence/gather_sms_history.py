#!/usr/bin/env python3
"""
Network Intelligence — Pipeline O: SMS Communication History

Parses an Android SMS Backup & Restore XML file, matches conversations to contacts
in the database using phone numbers and GPT-5 mini name matching, then summarizes
with GPT-5 mini and merges into the existing communication_history JSONB field.

Usage:
  python scripts/intelligence/gather_sms_history.py --parse-only        # parse + match, no LLM summarization
  python scripts/intelligence/gather_sms_history.py --test              # 1 conversation end-to-end
  python scripts/intelligence/gather_sms_history.py --batch 20          # 20 conversations
  python scripts/intelligence/gather_sms_history.py                     # full run
"""

import os
import re
import sys
import json
import time
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from pydantic import BaseModel, Field
from supabase import create_client, Client

load_dotenv()

# ── Constants ────────────────────────────────────────────────────────

SMS_BACKUP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "tool-results", "sms-backup.xml"
)

# Spam / automated message filters
SHORT_CODE_MAX_DIGITS = 6  # Phone numbers ≤6 digits are short codes
SPAM_PATTERNS = [
    r"(?i)verification code",
    r"(?i)your code is",
    r"(?i)ADT alert",
    r"(?i)security code",
    r"(?i)one-time (password|code|passcode)",
    r"(?i)2FA code",
    r"(?i)log in with",
    r"(?i)your .* pin is",
    r"(?i)account verification",
]
SPAM_COMPILED = [re.compile(p) for p in SPAM_PATTERNS]

# Skip own numbers (Twilio etc.)
OWN_NUMBERS = {"+15103958187"}  # Justin's Twilio/Outdoorithm number

# Phone normalization
PHONE_STRIP_RE = re.compile(r"[^\d+]")

# Group text detection: contact names with commas indicate multiple participants
GROUP_TEXT_RE = re.compile(r",\s+")


# ── Pydantic Schemas ─────────────────────────────────────────────────

class SMSConversationSummary(BaseModel):
    summary: str = Field(description="2-3 sentence summary of SMS conversation themes and relationship")
    direction: str = Field(description="sent | received | bidirectional")
    key_topics: list[str] = Field(description="Top 3-5 conversation topics")


class NameMatchResult(BaseModel):
    is_match: bool = Field(description="Whether the SMS contact is the same person as the DB contact")
    confidence: str = Field(description="high | medium | low")
    reasoning: str = Field(description="Brief explanation of why this is/isn't a match")


# ── Phone Helpers ────────────────────────────────────────────────────

def normalize_phone(raw: str) -> str:
    """Normalize a phone number to E.164-ish format (digits only, with leading +1 for US)."""
    digits = PHONE_STRIP_RE.sub("", raw)
    if digits.startswith("+"):
        return digits
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return digits


def is_short_code(phone: str) -> bool:
    """Returns True for short codes (≤6 digit numbers)."""
    digits = re.sub(r"\D", "", phone)
    return len(digits) <= SHORT_CODE_MAX_DIGITS


def is_spam_message(body: str) -> bool:
    """Check if a message body looks like automated/spam."""
    if not body:
        return False
    for pattern in SPAM_COMPILED:
        if pattern.search(body):
            return True
    return False


# ── XML Parsing ──────────────────────────────────────────────────────

def parse_sms_backup(xml_path: str) -> dict:
    """
    Stream-parse the SMS backup XML. Returns dict keyed by phone number:
    {
        phone: {
            "contact_name": str,
            "phone": str,
            "messages": [{"date": datetime, "type": int, "body": str}, ...],
            "sent_count": int,
            "received_count": int,
        }
    }
    """
    conversations = {}
    msg_count = 0
    skipped_spam = 0
    skipped_short = 0
    skipped_own = 0
    skipped_group = 0

    print(f"Parsing SMS backup: {xml_path}")
    print(f"File size: {os.path.getsize(xml_path) / (1024**3):.2f} GB")

    context = ET.iterparse(xml_path, events=("end",))

    for event, elem in context:
        tag = elem.tag

        if tag == "sms":
            address = elem.get("address", "").strip()
            contact_name = elem.get("contact_name", "").strip()
            body = elem.get("body", "").strip()
            msg_type = int(elem.get("type", "0"))  # 1=received, 2=sent
            date_ms = elem.get("date", "0")

            # Skip short codes
            if is_short_code(address):
                skipped_short += 1
                elem.clear()
                continue

            phone = normalize_phone(address)
            if not phone:
                elem.clear()
                continue

            # Skip own numbers
            if phone in OWN_NUMBERS:
                skipped_own += 1
                elem.clear()
                continue

            # Skip group texts (multiple phone numbers concatenated)
            if "+" in phone[1:]:  # Multiple + signs = group text
                skipped_group += 1
                elem.clear()
                continue

            # Skip spam
            if is_spam_message(body):
                skipped_spam += 1
                elem.clear()
                continue

            # Parse date
            try:
                dt = datetime.fromtimestamp(int(date_ms) / 1000, tz=timezone.utc)
            except (ValueError, OSError):
                dt = None

            if phone not in conversations:
                conversations[phone] = {
                    "contact_name": contact_name if contact_name and contact_name != "(Unknown)" else "",
                    "phone": phone,
                    "messages": [],
                    "sent_count": 0,
                    "received_count": 0,
                }

            # Update contact name if we have a better one
            if contact_name and contact_name != "(Unknown)" and not conversations[phone]["contact_name"]:
                conversations[phone]["contact_name"] = contact_name

            conversations[phone]["messages"].append({
                "date": dt,
                "type": msg_type,
                "body": body,
            })

            if msg_type == 2:
                conversations[phone]["sent_count"] += 1
            else:
                conversations[phone]["received_count"] += 1

            msg_count += 1
            if msg_count % 10000 == 0:
                print(f"  Parsed {msg_count:,} messages, {len(conversations)} conversations...")

            elem.clear()

        elif tag == "mms":
            # Extract MMS text parts
            address = elem.get("address", "").strip()
            contact_name = elem.get("contact_name", "").strip()
            msg_type = int(elem.get("msg_box", elem.get("type", "0")))
            date_ms = elem.get("date", "0")

            if is_short_code(address):
                skipped_short += 1
                elem.clear()
                continue

            phone = normalize_phone(address)
            if not phone:
                elem.clear()
                continue

            # Skip own numbers
            if phone in OWN_NUMBERS:
                skipped_own += 1
                elem.clear()
                continue

            # Skip group texts (multiple phone numbers concatenated or with tildes)
            if "+" in phone[1:] or "~" in address:
                skipped_group += 1
                elem.clear()
                continue

            # MMS date might be in seconds, not ms
            try:
                ts = int(date_ms)
                if ts < 1e12:  # seconds
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                else:  # milliseconds
                    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            except (ValueError, OSError):
                dt = None

            # Extract text from MMS parts
            body_parts = []
            for part in elem.findall(".//part"):
                ct = part.get("ct", "")
                if ct.startswith("text/"):
                    text = part.get("text", "").strip()
                    if text and text != "null":
                        body_parts.append(text)

            body = " ".join(body_parts)

            if is_spam_message(body):
                skipped_spam += 1
                elem.clear()
                continue

            if phone not in conversations:
                conversations[phone] = {
                    "contact_name": contact_name if contact_name and contact_name != "(Unknown)" else "",
                    "phone": phone,
                    "messages": [],
                    "sent_count": 0,
                    "received_count": 0,
                }

            if contact_name and contact_name != "(Unknown)" and not conversations[phone]["contact_name"]:
                conversations[phone]["contact_name"] = contact_name

            # Only add if there's text content
            if body:
                conversations[phone]["messages"].append({
                    "date": dt,
                    "type": 2 if msg_type == 2 else 1,  # normalize MMS type
                    "body": body,
                })

                if msg_type == 2:
                    conversations[phone]["sent_count"] += 1
                else:
                    conversations[phone]["received_count"] += 1

            msg_count += 1
            if msg_count % 10000 == 0:
                print(f"  Parsed {msg_count:,} messages, {len(conversations)} conversations...")

            elem.clear()

    # Sort messages by date within each conversation
    for conv in conversations.values():
        conv["messages"].sort(key=lambda m: m["date"] or datetime.min.replace(tzinfo=timezone.utc))

    print(f"\nParsing complete:")
    print(f"  Total messages parsed: {msg_count:,}")
    print(f"  Conversations: {len(conversations)}")
    print(f"  Skipped short codes: {skipped_short:,}")
    print(f"  Skipped own numbers: {skipped_own:,}")
    print(f"  Skipped group texts: {skipped_group:,}")
    print(f"  Skipped spam: {skipped_spam:,}")

    # Filter to named conversations with >0 messages
    named = {k: v for k, v in conversations.items()
             if v["contact_name"] and len(v["messages"]) > 0}
    print(f"  Named conversations (with messages): {len(named)}")

    return named


# ── Main Class ───────────────────────────────────────────────────────

class SMSHistoryGatherer:
    MODEL = "gpt-5-mini"
    MAX_SAMPLE_MESSAGES = 50  # Sample messages stored for context
    MAX_SUMMARY_MESSAGES = 100  # Messages sent to LLM for summarization

    def __init__(self, xml_path=SMS_BACKUP_PATH, test_mode=False, batch_size=0,
                 parse_only=False, summarize_only=False, force=False, workers=10):
        self.xml_path = xml_path
        self.test_mode = test_mode
        self.batch_size = batch_size
        self.parse_only = parse_only
        self.summarize_only = summarize_only
        self.force = force
        self.workers = workers
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.db_contacts: list[dict] = []
        self.phone_index: dict = {}  # normalized_phone -> contact
        self.name_index: dict = {}   # "first last" lower -> [contacts]
        self.stats = {
            "conversations_parsed": 0,
            "phone_matched": 0,
            "name_matched_exact": 0,
            "name_matched_fuzzy": 0,
            "unmatched": 0,
            "summaries_generated": 0,
            "phone_numbers_backfilled": 0,
            "comms_histories_updated": 0,
            "errors": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    def connect(self) -> bool:
        """Initialize Supabase and OpenAI connections."""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        openai_key = os.environ.get("OPENAI_APIKEY")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False

        self.supabase = create_client(url, key)

        if not self.parse_only:
            if not openai_key:
                print("ERROR: Missing OPENAI_APIKEY (needed for matching/summarization)")
                return False
            self.openai = OpenAI(api_key=openai_key)

        # Verify table exists (skip in parse-only mode)
        if not self.parse_only:
            try:
                self.supabase.table("contact_sms_conversations").select("id").limit(1).execute()
            except Exception as e:
                if "PGRST205" in str(e) or "could not find" in str(e).lower():
                    print("ERROR: Table 'contact_sms_conversations' does not exist.")
                    print("Please run the migration SQL in the Supabase SQL Editor:")
                    print(f"  File: supabase/migrations/20260222_add_contact_sms_conversations.sql")
                    return False
                raise

        print(f"Connected: Supabase{', OpenAI' if self.openai else ''}")
        return True

    def load_contacts(self):
        """Load all contacts from DB for matching."""
        print("Loading contacts from database...")
        all_contacts = []
        page_size = 1000
        offset = 0

        cols = (
            "id, first_name, last_name, company, position, headline, "
            "normalized_phone_number, email, communication_history, "
            "comms_last_date, comms_thread_count"
        )

        while True:
            page = (
                self.supabase.table("contacts")
                .select(cols)
                .range(offset, offset + page_size - 1)
                .execute()
            ).data
            if not page:
                break
            all_contacts.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        self.db_contacts = all_contacts
        print(f"  Loaded {len(all_contacts)} contacts")

        # Build phone index
        for c in all_contacts:
            phone = c.get("normalized_phone_number")
            if phone:
                norm = normalize_phone(phone)
                self.phone_index[norm] = c

        print(f"  Phone index: {len(self.phone_index)} contacts with phone numbers")

        # Build name index (lowercase full name -> list of contacts)
        for c in all_contacts:
            fn = (c.get("first_name") or "").strip()
            ln = (c.get("last_name") or "").strip()
            if fn and ln:
                full = f"{fn} {ln}".lower()
                if full not in self.name_index:
                    self.name_index[full] = []
                self.name_index[full].append(c)

        print(f"  Name index: {len(self.name_index)} unique names")

    # ── Matching ─────────────────────────────────────────────────────

    def match_conversation(self, conv: dict) -> Optional[dict]:
        """
        Match an SMS conversation to a DB contact. Returns:
        {"contact": dict, "method": str, "confidence": str} or None.
        """
        phone = conv["phone"]
        contact_name = conv["contact_name"]

        # Skip group text contact names (multiple people comma-separated)
        if GROUP_TEXT_RE.search(contact_name):
            return None

        # Skip self-texts
        if contact_name.lower() in ("justin steele", "justin richard steele"):
            return None

        # 1. Phone number match (highest confidence)
        if phone in self.phone_index:
            return {
                "contact": self.phone_index[phone],
                "method": "phone",
                "confidence": "high",
            }

        if not contact_name:
            return None

        name_lower = contact_name.lower().strip()

        # 2. Exact name match → confirm with GPT-5 mini
        if name_lower in self.name_index:
            candidates = self.name_index[name_lower]
            if len(candidates) == 1:
                if self.parse_only:
                    return {
                        "contact": candidates[0],
                        "method": "exact_name",
                        "confidence": "high",
                    }
                # GPT confirmation
                result = self._gpt_confirm_match(conv, candidates[0])
                if result and result.is_match:
                    return {
                        "contact": candidates[0],
                        "method": "exact_name",
                        "confidence": result.confidence,
                    }

        # 3. Fuzzy name match → candidate generation + GPT confirmation
        candidates = self._find_fuzzy_candidates(contact_name)
        if candidates and not self.parse_only:
            for candidate in candidates[:3]:  # Check top 3
                result = self._gpt_confirm_match(conv, candidate)
                if result and result.is_match and result.confidence in ("high", "medium"):
                    return {
                        "contact": candidate,
                        "method": "fuzzy_name_gpt",
                        "confidence": result.confidence,
                    }
        elif candidates and self.parse_only:
            # In parse-only mode, report fuzzy candidates but don't confirm
            return {
                "contact": candidates[0],
                "method": "fuzzy_name_candidate",
                "confidence": "unconfirmed",
            }

        return None

    def _find_fuzzy_candidates(self, sms_name: str) -> list[dict]:
        """Find potential name matches using string similarity."""
        sms_lower = sms_name.lower().strip()
        sms_parts = sms_lower.split()

        candidates = []
        for full_name, contacts in self.name_index.items():
            # Check substring/prefix match
            if sms_lower in full_name or full_name in sms_lower:
                candidates.extend(contacts)
                continue

            # Check first name + similar last name
            name_parts = full_name.split()
            if len(sms_parts) >= 2 and len(name_parts) >= 2:
                # First name must match closely
                fn_ratio = SequenceMatcher(None, sms_parts[0], name_parts[0]).ratio()
                if fn_ratio >= 0.8:
                    # Last name should be similar
                    ln_ratio = SequenceMatcher(None, sms_parts[-1], name_parts[-1]).ratio()
                    if ln_ratio >= 0.7:
                        candidates.extend(contacts)
                        continue

            # Overall similarity
            ratio = SequenceMatcher(None, sms_lower, full_name).ratio()
            if ratio >= 0.75:
                candidates.extend(contacts)

        # Deduplicate and sort by name similarity
        seen = set()
        unique = []
        for c in candidates:
            if c["id"] not in seen:
                seen.add(c["id"])
                unique.append(c)

        # Sort by similarity score descending
        unique.sort(
            key=lambda c: SequenceMatcher(
                None, sms_lower,
                f"{c.get('first_name', '')} {c.get('last_name', '')}".lower()
            ).ratio(),
            reverse=True
        )

        return unique

    def _gpt_confirm_match(self, conv: dict, candidate: dict) -> Optional[NameMatchResult]:
        """Use GPT-5 mini to confirm whether SMS contact matches DB contact."""
        if not self.openai:
            return None

        sms_name = conv["contact_name"]
        phone = conv["phone"]
        msg_count = len(conv["messages"])

        # Sample some recent messages for context
        recent_msgs = conv["messages"][-5:]
        msg_samples = []
        for m in recent_msgs:
            direction = "Justin sent" if m["type"] == 2 else "Received"
            date_str = m["date"].strftime("%Y-%m-%d") if m["date"] else "?"
            body = (m["body"] or "")[:200]
            msg_samples.append(f"  [{date_str}] {direction}: {body}")

        db_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
        db_company = candidate.get("company") or "unknown"
        db_position = candidate.get("position") or "unknown"
        db_headline = candidate.get("headline") or ""

        prompt = f"""Determine if this SMS contact is the same person as the database contact.

SMS Contact:
- Name in phone: "{sms_name}"
- Phone number: {phone}
- Total messages: {msg_count}
- Recent messages:
{chr(10).join(msg_samples)}

Database Contact:
- Name: {db_name}
- Company: {db_company}
- Position: {db_position}
- Headline: {db_headline}

Consider: name variations (nicknames, maiden names, hyphenation), message context clues.
If the names are very different people (e.g., completely different first names), say no."""

        system = (
            "You are matching SMS contacts to a professional network database. "
            "Be strict: only confirm matches where you are confident it's the same person. "
            "Common variations to accept: Dave/David, Mike/Michael, hyphenated/unhyphenated last names, "
            "minor spelling differences. Reject if first names are completely different."
        )

        try:
            resp = self.openai.responses.parse(
                model=self.MODEL,
                instructions=system,
                input=prompt,
                text_format=NameMatchResult,
            )
            if resp.usage:
                self.stats["input_tokens"] += resp.usage.input_tokens
                self.stats["output_tokens"] += resp.usage.output_tokens
            return resp.output_parsed
        except (RateLimitError, APIError) as e:
            print(f"    GPT match error for '{sms_name}': {e}")
            self.stats["errors"] += 1
            return None
        except Exception as e:
            print(f"    Unexpected GPT error for '{sms_name}': {e}")
            self.stats["errors"] += 1
            return None

    # ── Summarization ────────────────────────────────────────────────

    def _summarize_conversation(self, conv: dict, contact: dict) -> Optional[SMSConversationSummary]:
        """Use GPT-5 mini to summarize an SMS conversation."""
        if not self.openai:
            return None

        contact_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        messages = conv["messages"]

        # Sample messages evenly across the conversation
        if len(messages) > self.MAX_SUMMARY_MESSAGES:
            step = len(messages) / self.MAX_SUMMARY_MESSAGES
            indices = [int(i * step) for i in range(self.MAX_SUMMARY_MESSAGES)]
            sampled = [messages[i] for i in indices]
        else:
            sampled = messages

        msg_text = []
        for m in sampled:
            direction = "Justin" if m["type"] == 2 else contact_name
            date_str = m["date"].strftime("%Y-%m-%d") if m["date"] else "?"
            body = (m["body"] or "")[:300]
            if body:
                msg_text.append(f"[{date_str}] {direction}: {body}")

        first_date = messages[0]["date"].strftime("%Y-%m-%d") if messages[0].get("date") else "?"
        last_date = messages[-1]["date"].strftime("%Y-%m-%d") if messages[-1].get("date") else "?"

        prompt = (
            f"Summarize Justin Steele's SMS conversation with {contact_name} "
            f"({contact.get('position', '?')} at {contact.get('company', '?')}).\n\n"
            f"Date range: {first_date} to {last_date}\n"
            f"Total messages: {len(messages)} ({conv['sent_count']} sent, {conv['received_count']} received)\n\n"
            f"Sample messages:\n" + "\n".join(msg_text[:80])
        )

        system = (
            "You are summarizing an SMS conversation between Justin Steele and a contact. "
            "Describe the relationship dynamic, communication frequency, and main topics. "
            "Keep the summary factual and concise (2-3 sentences). "
            "Identify the top 3-5 conversation topics as brief labels."
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions=system,
                    input=prompt,
                    text_format=SMSConversationSummary,
                )
                if resp.usage:
                    self.stats["input_tokens"] += resp.usage.input_tokens
                    self.stats["output_tokens"] += resp.usage.output_tokens
                return resp.output_parsed
            except RateLimitError:
                wait = 2 ** (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            except (APIError, Exception) as e:
                print(f"    Summarization error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    self.stats["errors"] += 1
                    return None

        return None

    # ── Database Operations ──────────────────────────────────────────

    def _get_sample_messages(self, conv: dict) -> list[dict]:
        """Get up to MAX_SAMPLE_MESSAGES representative messages for storage."""
        messages = conv["messages"]
        if len(messages) <= self.MAX_SAMPLE_MESSAGES:
            sampled = messages
        else:
            step = len(messages) / self.MAX_SAMPLE_MESSAGES
            indices = [int(i * step) for i in range(self.MAX_SAMPLE_MESSAGES)]
            sampled = [messages[i] for i in indices]

        return [
            {
                "date": m["date"].isoformat() if m.get("date") else None,
                "type": "sent" if m["type"] == 2 else "received",
                "body": (m["body"] or "")[:500],
            }
            for m in sampled
        ]

    def save_conversation(self, conv: dict, match: dict, summary: Optional[SMSConversationSummary]):
        """Save a matched conversation to the database."""
        contact = match["contact"]
        contact_id = contact["id"]
        messages = conv["messages"]

        first_date = messages[0]["date"] if messages[0].get("date") else None
        last_date = messages[-1]["date"] if messages[-1].get("date") else None

        row = {
            "contact_id": contact_id,
            "phone_number": conv["phone"],
            "message_count": len(messages),
            "sent_count": conv["sent_count"],
            "received_count": conv["received_count"],
            "first_message_date": first_date.isoformat() if first_date else None,
            "last_message_date": last_date.isoformat() if last_date else None,
            "sms_contact_name": conv["contact_name"],
            "match_method": match["method"],
            "match_confidence": match["confidence"],
            "sample_messages": self._get_sample_messages(conv),
            "summary": summary.summary if summary else None,
            "gathered_at": datetime.now(timezone.utc).isoformat(),
        }

        self.supabase.table("contact_sms_conversations").upsert(
            row, on_conflict="contact_id,phone_number"
        ).execute()

    def backfill_phone_number(self, contact: dict, phone: str, method: str):
        """Update normalized_phone_number for contacts matched by name."""
        existing = contact.get("normalized_phone_number") or ""
        if existing.startswith("+") and len(existing) >= 10:
            return  # Already has a valid phone number

        contact_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        self.supabase.table("contacts").update({
            "normalized_phone_number": phone,
        }).eq("id", contact["id"]).execute()

        print(f"    Phone backfill: {contact_name} → {phone} (via {method})")
        self.stats["phone_numbers_backfilled"] += 1

    def merge_comms_history(self, contact: dict, conv: dict, summary: Optional[SMSConversationSummary]):
        """Merge SMS data into the existing communication_history JSONB."""
        contact_id = contact["id"]
        messages = conv["messages"]

        first_date = messages[0]["date"].strftime("%Y-%m-%d") if messages[0].get("date") else None
        last_date = messages[-1]["date"].strftime("%Y-%m-%d") if messages[-1].get("date") else None

        # Fetch current communication_history
        existing = contact.get("communication_history") or {}

        # Determine direction
        if conv["sent_count"] > 0 and conv["received_count"] > 0:
            direction = "bidirectional"
        elif conv["sent_count"] > 0:
            direction = "sent"
        else:
            direction = "received"

        # Build SMS thread entry
        sms_thread = {
            "date": last_date,
            "source": "sms",
            "phone": conv["phone"],
            "direction": direction,
            "summary": summary.summary if summary else f"SMS conversation with {conv['contact_name']} ({len(messages)} messages)",
            "message_count": len(messages),
        }

        # Merge into existing threads
        threads = existing.get("threads", [])

        # Remove any existing SMS thread for this phone number
        threads = [t for t in threads if not (t.get("source") == "sms" and t.get("phone") == conv["phone"])]

        # Add new SMS thread
        threads.append(sms_thread)

        # Sort by date descending
        threads.sort(key=lambda t: t.get("date") or "", reverse=True)

        # Update date ranges
        all_dates = [t.get("date") for t in threads if t.get("date")]
        new_first = min(all_dates) if all_dates else existing.get("first_contact")
        new_last = max(all_dates) if all_dates else existing.get("last_contact")

        # Update accounts with activity
        accounts = set(existing.get("accounts_with_activity", []))
        accounts.add(f"sms:{conv['phone']}")

        # Count email vs SMS
        email_threads = [t for t in threads if t.get("source") != "sms"]
        sms_convos = [t for t in threads if t.get("source") == "sms"]

        # Build updated relationship summary
        rel_summary = existing.get("relationship_summary", "")
        if summary:
            if rel_summary:
                rel_summary = f"{rel_summary} SMS: {summary.summary}"
            else:
                rel_summary = summary.summary

        updated_history = {
            "last_gathered": datetime.now(timezone.utc).isoformat(),
            "total_threads": len(email_threads),
            "total_sms_conversations": len(sms_convos),
            "first_contact": new_first,
            "last_contact": new_last,
            "accounts_with_activity": sorted(accounts),
            "threads": threads,
            "relationship_summary": rel_summary,
        }

        # Compute updated denormalized fields
        comms_last_date = new_last
        comms_thread_count = len(threads)

        self.supabase.table("contacts").update({
            "communication_history": updated_history,
            "comms_last_date": comms_last_date,
            "comms_thread_count": comms_thread_count,
        }).eq("id", contact_id).execute()

        self.stats["comms_histories_updated"] += 1

    # ── Process One Conversation ─────────────────────────────────────

    def _match_one(self, conv: dict) -> tuple:
        """Match a single conversation. Returns (conv, match_result_or_None)."""
        match = self.match_conversation(conv)
        return (conv, match)

    def _summarize_and_save_one(self, conv: dict, match: dict) -> bool:
        """Summarize and save a single matched conversation. Thread-safe."""
        contact = match["contact"]
        method = match["method"]
        db_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        name = conv["contact_name"]
        msg_count = len(conv["messages"])

        # Summarize
        summary = self._summarize_conversation(conv, contact)
        if summary:
            self.stats["summaries_generated"] += 1

        # Save to contact_sms_conversations table
        self.save_conversation(conv, match, summary)

        # Backfill phone number for name-matched contacts
        if method in ("exact_name", "fuzzy_name_gpt"):
            self.backfill_phone_number(contact, conv["phone"], method)

        # Merge into communication_history — re-fetch fresh data to avoid stale reads
        fresh = (
            self.supabase.table("contacts")
            .select("id, communication_history, comms_last_date, comms_thread_count")
            .eq("id", contact["id"])
            .single()
            .execute()
        ).data
        self.merge_comms_history(fresh, conv, summary)

        print(f"  SAVED [{method}/{match['confidence']}]: {name} → {db_name} "
              f"(ID {contact['id']}, {msg_count} msgs"
              f"{', summary: ' + summary.summary[:60] + '...' if summary else ''})",
              flush=True)

        return True

    # ── Main Run ─────────────────────────────────────────────────────

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()

        # Load contacts for matching
        self.load_contacts()

        # Parse XML
        conversations = parse_sms_backup(self.xml_path)
        self.stats["conversations_parsed"] = len(conversations)

        # Sort by message count descending (process most active first)
        conv_list = sorted(conversations.values(), key=lambda c: len(c["messages"]), reverse=True)

        # Apply limits
        if self.test_mode:
            conv_list = conv_list[:1]
            print(f"\n--- TEST MODE: Processing 1 conversation ---\n")
        elif self.batch_size > 0:
            conv_list = conv_list[:self.batch_size]
            print(f"\n--- BATCH MODE: Processing {len(conv_list)} conversations ---\n")
        else:
            print(f"\n--- FULL RUN: Processing {len(conv_list)} conversations ---\n")

        # ── Phase A: Match all conversations (concurrent GPT calls) ──
        print(f"Phase A: Matching {len(conv_list)} conversations ({self.workers} workers)...", flush=True)
        matched_pairs = []  # (conv, match)

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self._match_one, conv): conv for conv in conv_list}
            done = 0
            for future in as_completed(futures):
                done += 1
                try:
                    conv, match = future.result()
                    name = conv["contact_name"]
                    phone = conv["phone"]
                    msg_count = len(conv["messages"])

                    if not match:
                        self.stats["unmatched"] += 1
                        print(f"  UNMATCHED: {name} ({phone}, {msg_count} msgs)", flush=True)
                    else:
                        contact = match["contact"]
                        method = match["method"]
                        confidence = match["confidence"]
                        db_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

                        if method == "phone":
                            self.stats["phone_matched"] += 1
                        elif method == "exact_name":
                            self.stats["name_matched_exact"] += 1
                        elif method == "fuzzy_name_gpt":
                            self.stats["name_matched_fuzzy"] += 1

                        if self.parse_only:
                            print(f"  MATCH [{method}/{confidence}]: {name} → {db_name} "
                                  f"(ID {contact['id']}, {msg_count} msgs)", flush=True)
                        else:
                            matched_pairs.append((conv, match))
                            print(f"  MATCHED [{method}/{confidence}]: {name} → {db_name} "
                                  f"(ID {contact['id']}, {msg_count} msgs)", flush=True)

                except Exception as e:
                    self.stats["errors"] += 1
                    print(f"  ERROR matching: {e}", flush=True)

                if done % 25 == 0 or done == len(conv_list):
                    elapsed = time.time() - start_time
                    total_matched = (self.stats["phone_matched"] +
                                   self.stats["name_matched_exact"] +
                                   self.stats["name_matched_fuzzy"])
                    print(f"\n  --- Match progress: {done}/{len(conv_list)} "
                          f"({total_matched} matched, {self.stats['unmatched']} unmatched) "
                          f"[{elapsed:.0f}s] ---\n", flush=True)

        if self.parse_only:
            elapsed = time.time() - start_time
            self._print_summary(elapsed)
            return True

        # ── Phase B: Summarize + save matched conversations (concurrent) ──
        total_matched = len(matched_pairs)
        print(f"\nPhase B: Summarizing + saving {total_matched} matched conversations "
              f"({self.workers} workers)...", flush=True)

        done_count = 0
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self._summarize_and_save_one, conv, match): (conv, match)
                for conv, match in matched_pairs
            }
            for future in as_completed(futures):
                done_count += 1
                try:
                    future.result()
                except Exception as e:
                    conv, match = futures[future]
                    self.stats["errors"] += 1
                    print(f"  ERROR saving {conv['contact_name']}: {e}", flush=True)

                if done_count % 25 == 0 or done_count == total_matched:
                    elapsed = time.time() - start_time
                    print(f"\n  --- Save progress: {done_count}/{total_matched} "
                          f"({self.stats['summaries_generated']} summaries, "
                          f"{self.stats['phone_numbers_backfilled']} phones backfilled) "
                          f"[{elapsed:.0f}s] ---\n", flush=True)

        elapsed = time.time() - start_time
        self._print_summary(elapsed)
        return True

    def _print_summary(self, elapsed: float):
        s = self.stats
        input_cost = s["input_tokens"] * 0.15 / 1_000_000
        output_cost = s["output_tokens"] * 0.60 / 1_000_000
        total_cost = input_cost + output_cost
        total_matched = s["phone_matched"] + s["name_matched_exact"] + s["name_matched_fuzzy"]

        print("\n" + "=" * 60)
        print("SMS COMMUNICATION HISTORY SUMMARY")
        print("=" * 60)
        print(f"  Conversations parsed:   {s['conversations_parsed']}")
        print(f"  Phone matched:          {s['phone_matched']}")
        print(f"  Exact name matched:     {s['name_matched_exact']}")
        print(f"  Fuzzy name matched:     {s['name_matched_fuzzy']}")
        print(f"  Total matched:          {total_matched}")
        print(f"  Unmatched:              {s['unmatched']}")
        print(f"  Summaries generated:    {s['summaries_generated']}")
        print(f"  Phone numbers backfilled: {s['phone_numbers_backfilled']}")
        print(f"  Comms histories updated: {s['comms_histories_updated']}")
        print(f"  Errors:                 {s['errors']}")
        if s["input_tokens"] > 0:
            print(f"  LLM input tokens:       {s['input_tokens']:,}")
            print(f"  LLM output tokens:      {s['output_tokens']:,}")
            print(f"  LLM cost:               ${total_cost:.4f}")
        print(f"  Time elapsed:           {elapsed:.1f}s")
        print("=" * 60)


def main():
    # Unbuffered output for background/pipe mode
    sys.stdout.reconfigure(line_buffering=True)

    parser = argparse.ArgumentParser(
        description="Parse SMS backup and enrich contacts with SMS communication history"
    )
    parser.add_argument("--xml", type=str, default=SMS_BACKUP_PATH,
                        help=f"Path to SMS backup XML (default: {SMS_BACKUP_PATH})")
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only 1 conversation (end-to-end test)")
    parser.add_argument("--batch", "-b", type=int, default=0,
                        help="Process N conversations (0 = all)")
    parser.add_argument("--parse-only", action="store_true",
                        help="Only parse and match, skip LLM summarization")
    parser.add_argument("--summarize-only", action="store_true",
                        help="Only summarize existing matched conversations")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-process already gathered conversations")
    parser.add_argument("--workers", "-w", type=int, default=10,
                        help="Concurrent workers for summarization (default: 10)")
    args = parser.parse_args()

    gatherer = SMSHistoryGatherer(
        xml_path=args.xml,
        test_mode=args.test,
        batch_size=args.batch,
        parse_only=args.parse_only,
        summarize_only=args.summarize_only,
        force=args.force,
        workers=args.workers,
    )
    success = gatherer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
