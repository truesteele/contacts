#!/usr/bin/env python3
"""
Import Sally's SMS conversations into sally_contact_sms_conversations.

Reads docs/Sally/sms_parsed.json (1,230 phone numbers, ~1,000 after dedup),
matches contact names to sally_contacts by exact and fuzzy name matching,
and stores matched conversations in sally_contact_sms_conversations.

Usage:
    python scripts/intelligence/sally/import_sms.py
    python scripts/intelligence/sally/import_sms.py --test        # 10 entries only
    python scripts/intelligence/sally/import_sms.py --dry-run     # Preview without inserting
    python scripts/intelligence/sally/import_sms.py --force       # Re-import all (clear existing)
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SMS_JSON_PATH = "docs/Sally/sms_parsed.json"

# Phone numbers to skip (Sally's own numbers)
OWN_NUMBERS = {"+14158440345"}  # Justin's phone — Sally is the sender in this file

PHONE_STRIP_RE = re.compile(r"[^\d+]")
SHORT_CODE_MAX_DIGITS = 6


# ── Phone Helpers ────────────────────────────────────────────────────

def normalize_phone(raw: str) -> str:
    """Normalize phone number to +1XXXXXXXXXX format."""
    digits = PHONE_STRIP_RE.sub("", raw)
    if digits.startswith("+"):
        return digits
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return digits


def is_short_code(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    return len(digits) <= SHORT_CODE_MAX_DIGITS


# ── Name Matching ────────────────────────────────────────────────────

def build_name_index(contacts: list) -> dict:
    """Build lowercase 'first last' → [contacts] index."""
    index = {}
    for c in contacts:
        fn = (c.get("first_name") or "").strip()
        ln = (c.get("last_name") or "").strip()
        if fn and ln:
            full = f"{fn} {ln}".lower()
            if full not in index:
                index[full] = []
            index[full].append(c)
    return index


def match_contact(name: str, name_index: dict) -> dict | None:
    """Match SMS contact_name to sally_contacts by name.

    Returns {contact, method, confidence} or None.
    """
    if not name or name.strip() in ("", "(Unknown)"):
        return None

    # Skip group texts (names with commas)
    if "," in name:
        return None

    name_lower = name.lower().strip()

    # Skip obvious non-person names
    skip_patterns = ["justin steele", "justin richard steele"]
    if name_lower in skip_patterns:
        return None

    # 1. Exact match
    if name_lower in name_index:
        candidates = name_index[name_lower]
        if len(candidates) == 1:
            return {
                "contact": candidates[0],
                "method": "exact_name",
                "confidence": "high",
            }
        # Multiple contacts with same name — skip (ambiguous)
        return None

    # 2. Fuzzy match (SequenceMatcher >= 0.85)
    best_match = None
    best_ratio = 0.0
    for full_name, contacts in name_index.items():
        ratio = SequenceMatcher(None, name_lower, full_name).ratio()
        if ratio >= 0.85 and ratio > best_ratio and len(contacts) == 1:
            best_ratio = ratio
            best_match = contacts[0]

    if best_match:
        return {
            "contact": best_match,
            "method": "fuzzy_name",
            "confidence": "medium",
        }

    return None


# ── SMS Data Processing ─────────────────────────────────────────────

def merge_duplicate_phones(raw_data: dict) -> dict:
    """Merge SMS entries that map to the same normalized phone number."""
    merged = {}

    for raw_phone, entry in raw_data.items():
        norm = normalize_phone(raw_phone)

        if norm not in merged:
            merged[norm] = {
                "contact_name": entry.get("contact_name", ""),
                "phone_number": norm,
                "total_count": entry.get("total_count", 0),
                "sent_count": entry.get("sent_count", 0),
                "received_count": entry.get("received_count", 0),
                "first_date": entry.get("first_date"),
                "last_date": entry.get("last_date"),
                "recent_messages": entry.get("recent_messages", []),
                "sample_messages": entry.get("sample_messages", []),
            }
        else:
            existing = merged[norm]
            existing["total_count"] += entry.get("total_count", 0)
            existing["sent_count"] += entry.get("sent_count", 0)
            existing["received_count"] += entry.get("received_count", 0)

            # Keep earliest first_date
            new_first = entry.get("first_date")
            if new_first and (not existing["first_date"] or new_first < existing["first_date"]):
                existing["first_date"] = new_first

            # Keep latest last_date
            new_last = entry.get("last_date")
            if new_last and (not existing["last_date"] or new_last > existing["last_date"]):
                existing["last_date"] = new_last

            # Merge recent_messages (keep most recent)
            existing["recent_messages"].extend(entry.get("recent_messages", []))
            existing["recent_messages"].sort(
                key=lambda m: m.get("date", ""), reverse=True
            )
            existing["recent_messages"] = existing["recent_messages"][:20]

            # Merge sample_messages
            existing["sample_messages"].extend(entry.get("sample_messages", []))
            existing["sample_messages"] = existing["sample_messages"][-20:]

            # Prefer named contact
            if not existing["contact_name"] and entry.get("contact_name"):
                existing["contact_name"] = entry["contact_name"]

    return merged


def build_sample_messages(entry: dict) -> list:
    """Build sample_messages list from recent_messages, capped at 20."""
    messages = entry.get("recent_messages", [])
    samples = []
    for m in messages[-20:]:
        samples.append({
            "date": m.get("date"),
            "direction": m.get("direction", "received"),
            "body": (m.get("body") or "")[:500],
            "contact_name": m.get("contact_name", ""),
        })
    return samples


# ── Main ─────────────────────────────────────────────────────────────

def main():
    sys.stdout.reconfigure(line_buffering=True)

    parser = argparse.ArgumentParser(description="Import Sally's SMS conversations")
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only 10 named entries")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview matching without inserting")
    parser.add_argument("--force", action="store_true",
                        help="Clear existing SMS data before import")
    args = parser.parse_args()

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )

    # ── Load SMS data ────────────────────────────────────────────
    print(f"Loading SMS data from {SMS_JSON_PATH}...")
    with open(SMS_JSON_PATH, encoding="utf-8") as f:
        raw_data = json.load(f)
    print(f"  Raw phone entries: {len(raw_data)}")

    # Merge duplicate phone formats
    sms_data = merge_duplicate_phones(raw_data)
    print(f"  After dedup: {len(sms_data)} unique phone numbers")

    # Filter out short codes and own numbers
    filtered = {}
    for phone, entry in sms_data.items():
        if is_short_code(phone):
            continue
        if phone in OWN_NUMBERS:
            continue
        if not entry.get("contact_name"):
            continue  # Can't match without a name
        filtered[phone] = entry

    print(f"  With contact names (matchable): {len(filtered)}")

    # ── Load sally_contacts for matching ─────────────────────────
    print("\nLoading sally_contacts...")
    all_contacts = []
    page_size = 1000
    offset = 0
    while True:
        page = (
            supabase.table("sally_contacts")
            .select("id, first_name, last_name")
            .range(offset, offset + page_size - 1)
            .execute()
        ).data
        if not page:
            break
        all_contacts.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    print(f"  {len(all_contacts)} contacts loaded")

    name_index = build_name_index(all_contacts)
    print(f"  {len(name_index)} unique names in index")

    # ── Force mode: clear existing ───────────────────────────────
    if args.force and not args.dry_run:
        print("\n[FORCE] Clearing existing sally_contact_sms_conversations...")
        supabase.table("sally_contact_sms_conversations").delete().neq("id", 0).execute()
        print("  Cleared.")

    # ── Match and import ─────────────────────────────────────────
    entries = list(filtered.items())
    if args.test:
        entries = entries[:10]
        print(f"\n[TEST MODE] Processing {len(entries)} entries only")

    matched = []
    unmatched = []
    skipped_ambiguous = 0

    print(f"\nMatching {len(entries)} SMS entries to contacts...")
    for phone, entry in entries:
        result = match_contact(entry["contact_name"], name_index)
        if result:
            matched.append((phone, entry, result))
        else:
            unmatched.append((phone, entry))

    print(f"  Matched: {len(matched)}")
    print(f"  Unmatched: {len(unmatched)}")

    # Show match breakdown
    high_conf = sum(1 for _, _, m in matched if m["confidence"] == "high")
    med_conf = sum(1 for _, _, m in matched if m["confidence"] == "medium")
    print(f"  High confidence: {high_conf}")
    print(f"  Medium confidence: {med_conf}")

    if args.dry_run:
        print("\n[DRY RUN] Would insert these matches:")
        for phone, entry, result in sorted(matched, key=lambda x: -x[1]["total_count"])[:20]:
            c = result["contact"]
            print(f"  {entry['contact_name']} ({phone}) → "
                  f"{c['first_name']} {c['last_name']} (ID {c['id']}) "
                  f"[{result['method']}/{result['confidence']}] "
                  f"({entry['total_count']} msgs)")
        if len(matched) > 20:
            print(f"  ... and {len(matched) - 20} more")
        print(f"\nUnmatched (top by message count):")
        for phone, entry in sorted(unmatched, key=lambda x: -x[1]["total_count"])[:15]:
            print(f"  {entry['contact_name']} ({phone}) — {entry['total_count']} msgs")
        return

    # ── Insert matched conversations ─────────────────────────────
    print(f"\nInserting {len(matched)} SMS conversations...")
    inserted = 0
    errors = 0
    start_time = time.time()

    for phone, entry, result in matched:
        contact = result["contact"]
        contact_id = contact["id"]

        # Build sample messages from recent_messages
        samples = build_sample_messages(entry)
        # If no recent_messages, fall back to sample_messages from parsed data
        if not samples and entry.get("sample_messages"):
            samples = entry["sample_messages"][:20]

        row = {
            "contact_id": contact_id,
            "phone_number": phone,
            "message_count": entry.get("total_count", 0),
            "sent_count": entry.get("sent_count", 0),
            "received_count": entry.get("received_count", 0),
            "first_message_date": entry.get("first_date"),
            "last_message_date": entry.get("last_date"),
            "sms_contact_name": entry.get("contact_name", ""),
            "match_method": result["method"],
            "match_confidence": result["confidence"],
            "sample_messages": samples,
        }

        try:
            supabase.table("sally_contact_sms_conversations").upsert(
                row, on_conflict="contact_id,phone_number"
            ).execute()
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error for {entry['contact_name']}: {e}")

    elapsed = time.time() - start_time

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"SMS IMPORT SUMMARY")
    print(f"{'='*60}")
    print(f"  Raw phone entries:      {len(raw_data)}")
    print(f"  After dedup:            {len(sms_data)}")
    print(f"  Matchable (with name):  {len(filtered)}")
    print(f"  Matched to contacts:    {len(matched)}")
    print(f"  Unmatched:              {len(unmatched)}")
    print(f"  Inserted:               {inserted}")
    print(f"  Errors:                 {errors}")
    print(f"  Time:                   {elapsed:.1f}s")
    print(f"{'='*60}")

    # Verify
    count_result = (
        supabase.table("sally_contact_sms_conversations")
        .select("id", count="exact")
        .execute()
    )
    print(f"\nVerification: {count_result.count} rows in sally_contact_sms_conversations")


if __name__ == "__main__":
    main()
