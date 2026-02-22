#!/usr/bin/env python3
"""
Network Intelligence — Communication Closeness Scoring

Uses GPT-5 mini to assess each contact's communication closeness and momentum
based purely on behavioral communication data (email, LinkedIn DM, SMS).

This is the behavioral dimension of relationship strength, complementing the
subjective familiarity_rating. See docs/RELATIONSHIP_DIMENSIONS_FRAMEWORK.md
for the full theoretical framework.

Usage:
  python scripts/intelligence/score_comms_closeness.py --test               # 5 contacts, no write
  python scripts/intelligence/score_comms_closeness.py --workers 150        # Full run, 150 workers
  python scripts/intelligence/score_comms_closeness.py --force              # Re-score already scored
  python scripts/intelligence/score_comms_closeness.py --contact-id 1234    # Single contact
  python scripts/intelligence/score_comms_closeness.py                      # Full run (default 150 workers)
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

class CommsCloseness(str, Enum):
    active_inner_circle = "active_inner_circle"
    regular_contact = "regular_contact"
    occasional = "occasional"
    dormant = "dormant"
    one_way = "one_way"
    no_history = "no_history"

class CommsMomentum(str, Enum):
    growing = "growing"
    stable = "stable"
    fading = "fading"
    inactive = "inactive"

class CommsClosenessResult(BaseModel):
    comms_closeness: CommsCloseness = Field(description="Overall communication closeness label")
    comms_momentum: CommsMomentum = Field(description="Communication momentum/trajectory")
    comms_reasoning: str = Field(description="1-2 sentence explanation citing specific evidence from the data")


# ── System Prompt ─────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are an expert at assessing interpersonal communication patterns. You analyze raw communication metadata to determine how close a relationship is from a behavioral standpoint.

Today's date: {datetime.now().strftime('%Y-%m-%d')}

THEORETICAL FRAMEWORK (Granovetter's Behavioral Dimensions):
You are measuring the behavioral/observable aspects of tie strength:
- **Time invested**: How much communication time is spent in the relationship (frequency, duration)
- **Reciprocity**: The degree to which both parties invest (bidirectional vs one-way)

You are NOT measuring subjective closeness (that's captured separately). Focus ONLY on what the communication data tells you.

CHANNEL SIGNAL QUALITY HIERARCHY:
Different communication channels carry different weight as relationship signals:
1. **SMS** (highest signal) — Most intimate channel. Reserved for people you actually know. Implies phone number exchange, which is a trust signal.
2. **1:1 Email** (high signal) — Direct, intentional communication. Requires knowing someone's email.
3. **LinkedIn DM** (medium signal) — Direct but lower barrier. Platform-mediated. Common for professional networking without deep relationship.
4. **Group Email** (low signal) — Shared context but not necessarily relationship. Being CC'd on a group thread is weak signal.

When assessing closeness, weight SMS and 1:1 email threads much more heavily than group email threads. A contact with 2 SMS conversations and 3 1:1 emails is closer than a contact with 50 group email threads.

CLOSENESS LABELS:

- **active_inner_circle**: Frequent, recent, bidirectional communication across intimate channels (SMS, 1:1 email). This person is in regular active contact. Typically: multiple channels used, high bidirectional rate, last contact within 1-2 months, SMS or frequent 1:1 email present.

- **regular_contact**: Consistent communication pattern. Not daily, but reliably in touch — monthly or quarterly exchanges, mostly bidirectional. Typically: regular cadence over 6+ months, mostly bidirectional, last contact within 3-4 months.

- **occasional**: Some communication exists but it's infrequent. A few threads over a long period, or a burst of activity that hasn't sustained. Typically: scattered threads, long gaps between exchanges, last contact within 6-12 months.

- **dormant**: Communication history exists but has gone cold. Last meaningful exchange was 6+ months ago. The relationship WAS active but isn't currently. Typically: had a period of active communication that has since stopped, last contact 6+ months ago.

- **one_way**: Communication is predominantly one-directional. Either Justin reaches out without response, or the contact reaches out without sustained engagement. Typically: low bidirectional percentage, mostly inbound OR mostly outbound threads.

- **no_history**: Zero communication records across all channels. (Note: contacts with no comms_summary are pre-assigned this label and won't reach you.)

MOMENTUM LABELS:

- **growing**: Communication frequency or depth is increasing. More recent activity than historical average. New channels being used. Look for: accelerating thread frequency, recent activity on new channels, increasing message counts.

- **stable**: Consistent pattern over time. No significant change in frequency or depth. Look for: regular cadence maintained over months/years.

- **fading**: Communication was once more active but is declining. Gaps are lengthening. Look for: earlier period had more threads than recent period, increasing time between exchanges.

- **inactive**: No recent communication. Flat line. Last contact is distant past with no sign of resumption.

ASSESSMENT RULES:
1. Assess ONLY based on the communication data provided. Do NOT use personal knowledge.
2. Weight channels by signal quality: SMS > 1:1 email > LinkedIn DM > group email.
3. Consider recency heavily — recent communication (last 3 months) is much more significant than old threads.
4. Bidirectional communication is a much stronger signal than one-way.
5. A small number of SMS or 1:1 email threads can outweigh many group email threads.
6. For momentum, compare the chronological pattern — is activity increasing, steady, or declining?
7. The reasoning should cite specific numbers from the data (e.g., "14 bidirectional email threads over 18 months, last contact 2 weeks ago").

OUTPUT: Return comms_closeness, comms_momentum, and comms_reasoning."""


# ── Main Scorer ──────────────────────────────────────────────────────

class CommsClosenessScorer:
    MODEL = "gpt-5-mini"

    def __init__(self, test_mode=False, workers=150, force=False, contact_id=None):
        self.test_mode = test_mode
        self.workers = workers
        self.force = force
        self.contact_id = contact_id
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.stats = {
            "processed": 0,
            "skipped_no_history": 0,
            "by_closeness": {
                "active_inner_circle": 0, "regular_contact": 0,
                "occasional": 0, "dormant": 0,
                "one_way": 0, "no_history": 0,
            },
            "by_momentum": {
                "growing": 0, "stable": 0, "fading": 0, "inactive": 0,
            },
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
        """Fetch contacts that need comms closeness scoring."""
        select_cols = "id, comms_summary, comms_closeness"
        all_contacts = []
        page_size = 1000
        offset = 0

        if self.contact_id:
            result = (
                self.supabase.table("contacts")
                .select(select_cols)
                .eq("id", self.contact_id)
                .execute()
            )
            return result.data if result.data else []

        while True:
            query = (
                self.supabase.table("contacts")
                .select(select_cols)
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

        # Filter out already-scored contacts (unless --force)
        if not self.force:
            all_contacts = [c for c in all_contacts if not c.get("comms_closeness")]

        # Apply test limit
        if self.test_mode:
            all_contacts = all_contacts[:5]

        return all_contacts

    def build_contact_input(self, contact: dict) -> str:
        """Build the input string for GPT from comms_summary JSONB."""
        comms = contact.get("comms_summary")
        if isinstance(comms, str):
            try:
                comms = json.loads(comms)
            except (json.JSONDecodeError, ValueError):
                pass

        if not comms or not isinstance(comms, dict):
            return ""

        parts = []
        parts.append(f"Total threads: {comms.get('total_threads', 0)}")
        parts.append(f"Total messages: {comms.get('total_messages', 0)}")
        parts.append(f"Overall first contact: {comms.get('overall_first_date', 'unknown')}")
        parts.append(f"Overall last contact: {comms.get('overall_last_date', 'unknown')}")
        parts.append(f"Most recent channel: {comms.get('most_recent_channel', 'unknown')}")
        parts.append(f"Bidirectional thread %: {comms.get('bidirectional_pct', 0):.1f}%")
        parts.append(f"Group thread % (email only): {comms.get('group_thread_pct', 0):.1f}%")
        parts.append("")

        # Per-channel breakdown
        channels = comms.get("channels", {})
        for ch_name in ["sms", "email", "linkedin"]:
            ch = channels.get(ch_name)
            if not ch:
                continue
            parts.append(f"--- {ch_name.upper()} ---")
            parts.append(f"  Threads: {ch.get('threads', 0)}")
            parts.append(f"  Messages: {ch.get('messages', 0)}")
            parts.append(f"  First: {ch.get('first_date', 'unknown')}")
            parts.append(f"  Last: {ch.get('last_date', 'unknown')}")
            parts.append(f"  Bidirectional: {ch.get('bidirectional', 0)}")
            parts.append(f"  Inbound only: {ch.get('inbound', 0)}")
            parts.append(f"  Outbound only: {ch.get('outbound', 0)}")
            if ch_name == "email":
                parts.append(f"  Group threads: {ch.get('group_threads', 0)}")
            parts.append("")

        # Chronological summary
        chrono = comms.get("chronological_summary", "")
        if chrono:
            parts.append(f"Chronological summary: {chrono}")

        return "\n".join(parts)

    def score_contact(self, contact: dict) -> Optional[CommsClosenessResult]:
        """Call GPT-5 mini to score communication closeness for a single contact."""
        contact_input = self.build_contact_input(contact)

        if not contact_input:
            # No comms data — assign no_history without GPT call
            return CommsClosenessResult(
                comms_closeness=CommsCloseness.no_history,
                comms_momentum=CommsMomentum.inactive,
                comms_reasoning="No communication records found across any channel.",
            )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions=SYSTEM_PROMPT,
                    input=contact_input,
                    text_format=CommsClosenessResult,
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
            return {k: CommsClosenessScorer._strip_null_bytes(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [CommsClosenessScorer._strip_null_bytes(v) for v in obj]
        return obj

    def save_score(self, contact_id: int, result: CommsClosenessResult) -> bool:
        """Save the comms closeness score to Supabase."""
        try:
            self.supabase.table("contacts").update({
                "comms_closeness": self._strip_null_bytes(result.comms_closeness.value),
                "comms_momentum": self._strip_null_bytes(result.comms_momentum.value),
                "comms_reasoning": self._strip_null_bytes(result.comms_reasoning),
            }).eq("id", contact_id).execute()
            return True
        except Exception as e:
            print(f"    DB error for id={contact_id}: {e}")
            return False

    def process_contact(self, contact: dict) -> bool:
        """Process a single contact: score + save."""
        contact_id = contact["id"]

        result = self.score_contact(contact)
        if result is None:
            self.stats["errors"] += 1
            print(f"  ERROR [{contact_id}]: Failed to get comms closeness score")
            return False

        # Track no_history skips
        if result.comms_closeness == CommsCloseness.no_history:
            self.stats["skipped_no_history"] += 1

        if not self.test_mode:
            if not self.save_score(contact_id, result):
                self.stats["errors"] += 1
                return False

        self.stats["processed"] += 1
        self.stats["by_closeness"][result.comms_closeness.value] += 1
        self.stats["by_momentum"][result.comms_momentum.value] += 1

        # Color-coded display
        closeness_colors = {
            "active_inner_circle": "\033[92m",  # green
            "regular_contact": "\033[94m",       # blue
            "occasional": "\033[93m",            # yellow
            "dormant": "\033[33m",               # orange
            "one_way": "\033[95m",               # purple
            "no_history": "\033[90m",            # gray
        }
        momentum_icons = {
            "growing": "\033[92m↑",     # green up
            "stable": "\033[94m→",      # blue right
            "fading": "\033[33m↓",      # orange down
            "inactive": "\033[90m×",    # gray x
        }
        reset = "\033[0m"
        color = closeness_colors.get(result.comms_closeness.value, "")
        icon = momentum_icons.get(result.comms_momentum.value, "")

        print(f"  [{contact_id}] {color}{result.comms_closeness.value}{reset} "
              f"{icon}{reset} — {result.comms_reasoning[:120]}")
        return True

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()
        contacts = self.get_contacts()
        total = len(contacts)
        print(f"Found {total} contacts to score")

        if total == 0:
            print("Nothing to do — all contacts already scored (use --force to re-score)")
            return True

        mode_str = "TEST" if self.test_mode else "FULL"
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

                    if done_count % 100 == 0 or done_count == total:
                        elapsed = time.time() - start_time
                        rate = done_count / elapsed if elapsed > 0 else 0
                        s = self.stats
                        print(f"\n--- Progress: {done_count}/{total} "
                              f"(inner={s['by_closeness']['active_inner_circle']}, "
                              f"regular={s['by_closeness']['regular_contact']}, "
                              f"occasional={s['by_closeness']['occasional']}, "
                              f"dormant={s['by_closeness']['dormant']}, "
                              f"one_way={s['by_closeness']['one_way']}, "
                              f"no_history={s['by_closeness']['no_history']}, "
                              f"errors={s['errors']}) "
                              f"[{rate:.1f}/sec, {elapsed:.0f}s] ---\n")

        elapsed = time.time() - start_time
        self.print_summary(elapsed)
        return self.stats["errors"] < max(total * 0.05, 1)

    def print_summary(self, elapsed: float):
        s = self.stats
        input_cost = s["input_tokens"] * 0.15 / 1_000_000
        output_cost = s["output_tokens"] * 0.60 / 1_000_000
        total_cost = input_cost + output_cost

        print("\n" + "=" * 60)
        print("COMMUNICATION CLOSENESS SCORING SUMMARY")
        print("=" * 60)
        print(f"  Contacts scored:       {s['processed']}")
        print(f"  No-history (no GPT):   {s['skipped_no_history']}")
        print(f"  Errors:                {s['errors']}")
        print()
        print("  CLOSENESS DISTRIBUTION:")
        for label, count in s["by_closeness"].items():
            print(f"    {label:25s} {count}")
        print()
        print("  MOMENTUM DISTRIBUTION:")
        for label, count in s["by_momentum"].items():
            print(f"    {label:25s} {count}")
        print()
        print(f"  Input tokens:          {s['input_tokens']:,}")
        print(f"  Output tokens:         {s['output_tokens']:,}")
        print(f"  Cost:                  ${total_cost:.2f} (input: ${input_cost:.2f}, output: ${output_cost:.2f})")
        print(f"  Time elapsed:          {elapsed:.1f}s")
        if s["processed"] > 0:
            print(f"  Avg time/contact:      {elapsed / s['processed']:.2f}s")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Score contacts for communication closeness using GPT-5 mini"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process 5 contacts, print results, don't write to DB")
    parser.add_argument("--workers", "-w", type=int, default=150,
                        help="Number of concurrent workers (default: 150)")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-score contacts that already have comms_closeness")
    parser.add_argument("--contact-id", type=int, default=None,
                        help="Score a single contact by ID")
    args = parser.parse_args()

    scorer = CommsClosenessScorer(
        test_mode=args.test,
        workers=args.workers,
        force=args.force,
        contact_id=args.contact_id,
    )
    success = scorer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
