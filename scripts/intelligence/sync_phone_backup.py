#!/usr/bin/env python3
"""
Daily Phone Backup Sync — SMS + Call Logs from Google Drive

Downloads the latest SMS and call backup XML files from the SMS_Calls_Backup
folder in justinrsteele@gmail.com's Google Drive, processes them incrementally,
matches to contacts, and stores in Supabase. Temp files are deleted after processing.

Usage:
  python scripts/intelligence/sync_phone_backup.py                    # Full sync (SMS + calls)
  python scripts/intelligence/sync_phone_backup.py --calls-only       # Calls only (fast, no 5GB download)
  python scripts/intelligence/sync_phone_backup.py --no-sms           # Same as --calls-only
  python scripts/intelligence/sync_phone_backup.py --sms-only         # SMS only
  python scripts/intelligence/sync_phone_backup.py --test             # 1 SMS conv + 10 calls
  python scripts/intelligence/sync_phone_backup.py --recent-days 7    # Override SMS cutoff
"""

import os
import io
import re
import sys
import json
import time
import tempfile
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Optional
from difflib import SequenceMatcher

from dotenv import load_dotenv
from supabase import create_client, Client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

load_dotenv()

# ── Constants ────────────────────────────────────────────────────────

DRIVE_FOLDER_ID = "1bXb4DsB0wP9D3ZZMtVGRcqYJJgODQ3JM"  # SMS_Calls_Backup
CREDENTIALS_PATH = os.path.expanduser(
    "~/.google_workspace_mcp/credentials/justinrsteele@gmail.com.json"
)

CALL_TYPE_MAP = {"1": "incoming", "2": "outgoing", "3": "missed", "5": "voicemail"}

# Reuse constants from gather_sms_history
SHORT_CODE_MAX_DIGITS = 6
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
OWN_NUMBERS = {"+15103958187"}
PHONE_STRIP_RE = re.compile(r"[^\d+]")
GROUP_TEXT_RE = re.compile(r",\s+")


# ── Phone Helpers (from gather_sms_history.py) ───────────────────────

def normalize_phone(raw: str) -> str:
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


def is_spam_message(body: str) -> bool:
    if not body:
        return False
    for pattern in SPAM_COMPILED:
        if pattern.search(body):
            return True
    return False


# ── Drive Helpers ────────────────────────────────────────────────────

def build_drive_service():
    """Build Google Drive API service using existing OAuth creds."""
    with open(CREDENTIALS_PATH) as f:
        data = json.load(f)

    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def find_latest_file(drive, prefix: str) -> Optional[dict]:
    """Find the most recent file matching prefix in SMS_Calls_Backup folder."""
    results = drive.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and name contains '{prefix}'",
        pageSize=5,
        fields="files(id, name, size, modifiedTime)",
        orderBy="modifiedTime desc",
    ).execute()
    files = results.get("files", [])
    return files[0] if files else None


def download_to_temp(drive, file_id: str, file_name: str) -> str:
    """Download a Drive file to a temp file. Returns temp file path."""
    request = drive.files().get_media(fileId=file_id)
    tmp = tempfile.NamedTemporaryFile(suffix=".xml", delete=False, prefix=f"sync_{file_name}_")
    try:
        downloader = MediaIoBaseDownload(tmp, request, chunksize=50 * 1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"  Download {file_name}: {pct}%", flush=True)
    except Exception:
        tmp.close()
        os.unlink(tmp.name)
        raise
    tmp.close()
    return tmp.name


def download_to_memory(drive, file_id: str) -> bytes:
    """Download a small Drive file into memory."""
    request = drive.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


# ── Main Class ───────────────────────────────────────────────────────

class PhoneBackupSync:

    def __init__(self, calls_only=False, sms_only=False, test_mode=False,
                 workers=10, recent_days=None):
        self.calls_only = calls_only
        self.sms_only = sms_only
        self.test_mode = test_mode
        self.workers = workers
        self.recent_days_override = recent_days
        self.supabase: Optional[Client] = None
        self.drive = None
        self.phone_index: dict = {}   # normalized_phone -> contact
        self.name_index: dict = {}    # "first last" lower -> [contacts]
        self.existing_sms_phones: set = set()  # phones already in contact_sms_conversations
        self.temp_files: list = []    # for cleanup
        self.stats = {
            "sms_new_messages": 0,
            "sms_conversations_updated": 0,
            "sms_conversations_new": 0,
            "calls_total": 0,
            "calls_new": 0,
            "calls_matched": 0,
            "calls_unmatched": 0,
            "contacts_updated": 0,
            "errors": 0,
        }

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        self.supabase = create_client(url, key)

        try:
            self.drive = build_drive_service()
            print("Connected: Supabase, Google Drive")
        except Exception as e:
            print(f"ERROR: Failed to connect to Google Drive: {e}")
            return False
        return True

    def load_contacts(self):
        """Load contacts for phone/name matching."""
        print("Loading contacts for matching...")
        all_contacts = []
        page_size = 1000
        offset = 0
        cols = "id, first_name, last_name, normalized_phone_number, company, position, headline"

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

        # Build phone index
        for c in all_contacts:
            phone = c.get("normalized_phone_number")
            if phone:
                norm = normalize_phone(phone)
                self.phone_index[norm] = c

        # Build name index
        for c in all_contacts:
            fn = (c.get("first_name") or "").strip()
            ln = (c.get("last_name") or "").strip()
            if fn and ln:
                full = f"{fn} {ln}".lower()
                if full not in self.name_index:
                    self.name_index[full] = []
                self.name_index[full].append(c)

        print(f"  {len(all_contacts)} contacts, {len(self.phone_index)} with phones, "
              f"{len(self.name_index)} unique names")

    def match_by_phone_or_name(self, phone: str, contact_name: str) -> Optional[dict]:
        """Match a phone/name to a contact. Returns {contact, method, confidence} or None."""
        norm = normalize_phone(phone)

        # 1. Phone match
        if norm in self.phone_index:
            return {
                "contact": self.phone_index[norm],
                "method": "phone",
                "confidence": "high",
            }

        if not contact_name or contact_name == "(Unknown)":
            return None

        # Skip group names
        if GROUP_TEXT_RE.search(contact_name):
            return None

        # Skip self
        if contact_name.lower() in ("justin steele", "justin richard steele"):
            return None

        name_lower = contact_name.lower().strip()

        # 2. Exact name match
        if name_lower in self.name_index:
            candidates = self.name_index[name_lower]
            if len(candidates) == 1:
                return {
                    "contact": candidates[0],
                    "method": "exact_name",
                    "confidence": "high",
                }

        # 3. Fuzzy name match (no GPT — too expensive for daily sync)
        best_match = None
        best_ratio = 0.0
        for full_name, contacts in self.name_index.items():
            ratio = SequenceMatcher(None, name_lower, full_name).ratio()
            if ratio >= 0.85 and ratio > best_ratio and len(contacts) == 1:
                best_ratio = ratio
                best_match = contacts[0]

        if best_match:
            return {
                "contact": best_match,
                "method": "exact_name",
                "confidence": "medium",
            }

        return None

    # ── SMS Processing ───────────────────────────────────────────────

    def get_sms_cutoff(self) -> datetime:
        """Get the cutoff date for incremental SMS processing."""
        if self.recent_days_override:
            return datetime.now(timezone.utc) - timedelta(days=self.recent_days_override)

        # Query latest message date from existing SMS data
        try:
            result = self.supabase.rpc(
                "get_max_sms_date", {}
            ).execute()
            # Fallback: direct query
        except Exception:
            pass

        try:
            result = (
                self.supabase.table("contact_sms_conversations")
                .select("last_message_date")
                .order("last_message_date", desc=True)
                .limit(1)
                .execute()
            )
            if result.data and result.data[0].get("last_message_date"):
                last_date = datetime.fromisoformat(result.data[0]["last_message_date"])
                # Go back 1 extra day for safety
                return last_date - timedelta(days=1)
        except Exception as e:
            print(f"  Warning: couldn't query SMS cutoff: {e}")

        # Default: 30 days back
        return datetime.now(timezone.utc) - timedelta(days=30)

    def load_existing_sms_phones(self):
        """Load phone numbers that already have SMS conversation records."""
        offset = 0
        page_size = 1000
        while True:
            page = (
                self.supabase.table("contact_sms_conversations")
                .select("phone_number, contact_id")
                .range(offset, offset + page_size - 1)
                .execute()
            ).data
            if not page:
                break
            for r in page:
                self.existing_sms_phones.add(r["phone_number"])
            if len(page) < page_size:
                break
            offset += page_size
        print(f"  {len(self.existing_sms_phones)} existing SMS conversations in DB")

    def process_sms(self, xml_path: str, cutoff: datetime):
        """Parse SMS XML incrementally, only processing messages after cutoff."""
        print(f"\n--- SMS Processing (cutoff: {cutoff.strftime('%Y-%m-%d')}) ---\n")
        print(f"  File: {xml_path}")
        print(f"  Size: {os.path.getsize(xml_path) / (1024**3):.2f} GB")

        new_conversations = {}  # phone -> {messages, contact_name, sent, received}
        msg_count = 0
        skipped_old = 0
        skipped_spam = 0
        skipped_short = 0

        context = ET.iterparse(xml_path, events=("end",))

        for _, elem in context:
            tag = elem.tag

            if tag == "sms":
                date_ms = elem.get("date", "0")
                try:
                    dt = datetime.fromtimestamp(int(date_ms) / 1000, tz=timezone.utc)
                except (ValueError, OSError):
                    elem.clear()
                    continue

                # Skip old messages
                if dt <= cutoff:
                    skipped_old += 1
                    elem.clear()
                    if skipped_old % 50000 == 0:
                        print(f"  Skipped {skipped_old:,} old messages...", flush=True)
                    continue

                address = elem.get("address", "").strip()
                contact_name = elem.get("contact_name", "").strip()
                body = elem.get("body", "").strip()
                msg_type = int(elem.get("type", "0"))

                if is_short_code(address):
                    skipped_short += 1
                    elem.clear()
                    continue

                phone = normalize_phone(address)
                if not phone or phone in OWN_NUMBERS:
                    elem.clear()
                    continue

                if "+" in phone[1:]:
                    elem.clear()
                    continue

                if is_spam_message(body):
                    skipped_spam += 1
                    elem.clear()
                    continue

                # Add to new conversations
                if phone not in new_conversations:
                    new_conversations[phone] = {
                        "contact_name": contact_name if contact_name and contact_name != "(Unknown)" else "",
                        "phone": phone,
                        "messages": [],
                        "sent_count": 0,
                        "received_count": 0,
                    }

                if contact_name and contact_name != "(Unknown)" and not new_conversations[phone]["contact_name"]:
                    new_conversations[phone]["contact_name"] = contact_name

                new_conversations[phone]["messages"].append({
                    "date": dt,
                    "type": msg_type,
                    "body": body,
                })
                if msg_type == 2:
                    new_conversations[phone]["sent_count"] += 1
                else:
                    new_conversations[phone]["received_count"] += 1

                msg_count += 1
                self.stats["sms_new_messages"] += 1
                elem.clear()

            elif tag == "mms":
                date_ms = elem.get("date", "0")
                try:
                    ts = int(date_ms)
                    dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=timezone.utc)
                except (ValueError, OSError):
                    elem.clear()
                    continue

                if dt <= cutoff:
                    skipped_old += 1
                    elem.clear()
                    continue

                address = elem.get("address", "").strip()
                contact_name = elem.get("contact_name", "").strip()
                msg_type = int(elem.get("msg_box", elem.get("type", "0")))

                if is_short_code(address):
                    elem.clear()
                    continue

                phone = normalize_phone(address)
                if not phone or phone in OWN_NUMBERS:
                    elem.clear()
                    continue

                if "+" in phone[1:] or "~" in address:
                    elem.clear()
                    continue

                # Extract MMS text
                body_parts = []
                for part in elem.findall(".//part"):
                    ct = part.get("ct", "")
                    if ct.startswith("text/"):
                        text = part.get("text", "").strip()
                        if text and text != "null":
                            body_parts.append(text)
                body = " ".join(body_parts)

                if is_spam_message(body):
                    elem.clear()
                    continue

                if body and phone:
                    if phone not in new_conversations:
                        new_conversations[phone] = {
                            "contact_name": contact_name if contact_name and contact_name != "(Unknown)" else "",
                            "phone": phone,
                            "messages": [],
                            "sent_count": 0,
                            "received_count": 0,
                        }

                    if contact_name and contact_name != "(Unknown)" and not new_conversations[phone]["contact_name"]:
                        new_conversations[phone]["contact_name"] = contact_name

                    new_conversations[phone]["messages"].append({
                        "date": dt,
                        "type": 2 if msg_type == 2 else 1,
                        "body": body,
                    })
                    if msg_type == 2:
                        new_conversations[phone]["sent_count"] += 1
                    else:
                        new_conversations[phone]["received_count"] += 1
                    msg_count += 1
                    self.stats["sms_new_messages"] += 1

                elem.clear()

        print(f"\n  Parse complete:")
        print(f"    New messages found: {msg_count:,}")
        print(f"    Conversations with new messages: {len(new_conversations)}")
        print(f"    Skipped old: {skipped_old:,}")
        print(f"    Skipped spam: {skipped_spam:,}")
        print(f"    Skipped short codes: {skipped_short:,}")

        if not new_conversations:
            print("  No new SMS messages to process.")
            return

        # Apply test limit
        if self.test_mode:
            phones = list(new_conversations.keys())[:1]
            new_conversations = {p: new_conversations[p] for p in phones}
            print(f"  Test mode: processing {len(new_conversations)} conversation")

        # Process each conversation
        for phone, conv in new_conversations.items():
            conv["messages"].sort(key=lambda m: m["date"] or datetime.min.replace(tzinfo=timezone.utc))
            self._process_sms_conversation(conv)

    def _process_sms_conversation(self, conv: dict):
        """Process a single SMS conversation — update existing or create new."""
        phone = conv["phone"]
        new_msgs = conv["messages"]
        name = conv["contact_name"] or phone

        if phone in self.existing_sms_phones:
            # Update existing conversation
            try:
                existing = (
                    self.supabase.table("contact_sms_conversations")
                    .select("id, contact_id, message_count, sent_count, received_count, "
                            "last_message_date, sample_messages")
                    .eq("phone_number", phone)
                    .limit(1)
                    .execute()
                ).data

                if existing:
                    row = existing[0]
                    last_msg = new_msgs[-1]
                    last_date = last_msg["date"].isoformat() if last_msg.get("date") else None

                    # Build new sample messages to append
                    new_samples = [
                        {
                            "date": m["date"].isoformat() if m.get("date") else None,
                            "type": "sent" if m["type"] == 2 else "received",
                            "body": (m["body"] or "")[:500],
                        }
                        for m in new_msgs[-20:]  # Last 20 new messages
                    ]

                    # Merge with existing samples (keep last 50 total)
                    old_samples = row.get("sample_messages") or []
                    merged_samples = old_samples + new_samples
                    merged_samples = merged_samples[-50:]

                    self.supabase.table("contact_sms_conversations").update({
                        "message_count": row["message_count"] + len(new_msgs),
                        "sent_count": row["sent_count"] + conv["sent_count"],
                        "received_count": row["received_count"] + conv["received_count"],
                        "last_message_date": last_date,
                        "sample_messages": merged_samples,
                        "gathered_at": datetime.now(timezone.utc).isoformat(),
                    }).eq("id", row["id"]).execute()

                    self.stats["sms_conversations_updated"] += 1
                    print(f"  SMS updated: {name} ({phone}) +{len(new_msgs)} msgs")

                    # Update communication_history dates on the contact
                    self._update_comms_dates(row["contact_id"], last_date)
            except Exception as e:
                print(f"  ERROR updating SMS {name}: {e}")
                self.stats["errors"] += 1
        else:
            # New conversation — needs matching
            match = self.match_by_phone_or_name(phone, conv.get("contact_name", ""))
            if not match:
                print(f"  SMS unmatched: {name} ({phone}, {len(new_msgs)} msgs)")
                return

            contact = match["contact"]
            contact_id = contact["id"]
            db_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

            last_msg = new_msgs[-1]
            first_msg = new_msgs[0]
            last_date = last_msg["date"].isoformat() if last_msg.get("date") else None
            first_date = first_msg["date"].isoformat() if first_msg.get("date") else None

            samples = [
                {
                    "date": m["date"].isoformat() if m.get("date") else None,
                    "type": "sent" if m["type"] == 2 else "received",
                    "body": (m["body"] or "")[:500],
                }
                for m in new_msgs[-50:]
            ]

            try:
                self.supabase.table("contact_sms_conversations").upsert({
                    "contact_id": contact_id,
                    "phone_number": phone,
                    "message_count": len(new_msgs),
                    "sent_count": conv["sent_count"],
                    "received_count": conv["received_count"],
                    "first_message_date": first_date,
                    "last_message_date": last_date,
                    "sms_contact_name": conv.get("contact_name", ""),
                    "match_method": match["method"],
                    "match_confidence": match["confidence"],
                    "sample_messages": samples,
                    "gathered_at": datetime.now(timezone.utc).isoformat(),
                }, on_conflict="contact_id,phone_number").execute()

                self.stats["sms_conversations_new"] += 1
                print(f"  SMS new [{match['method']}]: {name} → {db_name} "
                      f"(ID {contact_id}, {len(new_msgs)} msgs)")

                # Backfill phone number if matched by name
                if match["method"] in ("exact_name",):
                    existing_phone = contact.get("normalized_phone_number") or ""
                    if not existing_phone.startswith("+"):
                        self.supabase.table("contacts").update({
                            "normalized_phone_number": phone,
                        }).eq("id", contact_id).execute()
                        print(f"    Phone backfill: {db_name} → {phone}")

                self._update_comms_dates(contact_id, last_date)
            except Exception as e:
                print(f"  ERROR saving new SMS {name}: {e}")
                self.stats["errors"] += 1

    def _update_comms_dates(self, contact_id: int, last_date: Optional[str]):
        """Update comms_last_date on the contact if this is more recent."""
        if not last_date:
            return
        try:
            current = (
                self.supabase.table("contacts")
                .select("comms_last_date")
                .eq("id", contact_id)
                .single()
                .execute()
            ).data
            current_date = current.get("comms_last_date") or ""
            new_date = last_date[:10]
            if new_date > current_date:
                self.supabase.table("contacts").update({
                    "comms_last_date": new_date,
                }).eq("id", contact_id).execute()
                self.stats["contacts_updated"] += 1
        except Exception:
            pass

    # ── Call Processing ──────────────────────────────────────────────

    def get_call_cutoff(self) -> datetime:
        """Get the cutoff date for incremental call processing."""
        try:
            result = (
                self.supabase.table("contact_call_logs")
                .select("call_date")
                .order("call_date", desc=True)
                .limit(1)
                .execute()
            )
            if result.data and result.data[0].get("call_date"):
                return datetime.fromisoformat(result.data[0]["call_date"])
        except Exception:
            pass
        # Default: process all calls (first run)
        return datetime.min.replace(tzinfo=timezone.utc)

    def process_calls(self, xml_bytes: bytes):
        """Parse call log XML and match to contacts."""
        print(f"\n--- Call Log Processing ---\n")

        cutoff = self.get_call_cutoff()
        if cutoff > datetime.min.replace(tzinfo=timezone.utc):
            print(f"  Cutoff: {cutoff.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"  First run: processing all calls")

        root = ET.fromstring(xml_bytes)
        all_calls = root.findall("call")
        self.stats["calls_total"] = len(all_calls)
        print(f"  Total calls in backup: {len(all_calls)}")

        # Filter to new calls
        new_calls = []
        for call in all_calls:
            date_ms = call.get("date", "0")
            try:
                dt = datetime.fromtimestamp(int(date_ms) / 1000, tz=timezone.utc)
            except (ValueError, OSError):
                continue

            if dt > cutoff:
                new_calls.append((call, dt))

        print(f"  New calls since cutoff: {len(new_calls)}")
        self.stats["calls_new"] = len(new_calls)

        if not new_calls:
            print("  No new calls to process.")
            return

        # Apply test limit
        if self.test_mode:
            new_calls = new_calls[:10]
            print(f"  Test mode: processing {len(new_calls)} calls")

        # Process each call
        matched_contacts = set()
        for call_elem, dt in new_calls:
            number = call_elem.get("number", "").strip()
            contact_name = call_elem.get("contact_name", "").strip()
            call_type_raw = call_elem.get("type", "1")
            duration = int(call_elem.get("duration", "0"))

            if not number:
                continue

            phone = normalize_phone(number)
            if not phone or phone in OWN_NUMBERS or is_short_code(number):
                continue

            call_type = CALL_TYPE_MAP.get(call_type_raw, "incoming")

            # Match to contact
            match = self.match_by_phone_or_name(phone, contact_name)
            if not match:
                self.stats["calls_unmatched"] += 1
                continue

            contact = match["contact"]
            contact_id = contact["id"]

            try:
                self.supabase.table("contact_call_logs").upsert({
                    "contact_id": contact_id,
                    "phone_number": phone,
                    "call_date": dt.isoformat(),
                    "call_type": call_type,
                    "duration_seconds": duration,
                    "contact_name_in_phone": contact_name if contact_name != "(Unknown)" else None,
                    "match_method": match["method"],
                    "match_confidence": match["confidence"],
                    "gathered_at": datetime.now(timezone.utc).isoformat(),
                }, on_conflict="contact_id,phone_number,call_date").execute()

                self.stats["calls_matched"] += 1
                matched_contacts.add(contact_id)

                # Backfill phone if matched by name
                if match["method"] == "exact_name":
                    existing_phone = contact.get("normalized_phone_number") or ""
                    if not existing_phone.startswith("+"):
                        self.supabase.table("contacts").update({
                            "normalized_phone_number": phone,
                        }).eq("id", contact_id).execute()

            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  ERROR saving call {contact_name}: {e}")
                    self.stats["errors"] += 1

        print(f"\n  Calls matched: {self.stats['calls_matched']}")
        print(f"  Calls unmatched: {self.stats['calls_unmatched']}")
        print(f"  Unique contacts: {len(matched_contacts)}")

        # Update contact stats
        if matched_contacts:
            self._update_call_stats(matched_contacts)

    def _update_call_stats(self, contact_ids: set):
        """Update comms_call_count and comms_last_call on contacts."""
        print(f"\n  Updating call stats for {len(contact_ids)} contacts...")
        for cid in contact_ids:
            try:
                result = (
                    self.supabase.table("contact_call_logs")
                    .select("call_date")
                    .eq("contact_id", cid)
                    .order("call_date", desc=True)
                    .execute()
                ).data

                if result:
                    call_count = len(result)
                    last_call = result[0]["call_date"][:10]

                    self.supabase.table("contacts").update({
                        "comms_call_count": call_count,
                        "comms_last_call": last_call,
                    }).eq("id", cid).execute()

                    # Also update comms_last_date if this is more recent
                    self._update_comms_dates(cid, last_call)
            except Exception as e:
                print(f"  ERROR updating call stats for {cid}: {e}")
                self.stats["errors"] += 1

    # ── Main Run ─────────────────────────────────────────────────────

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()
        self.load_contacts()

        sms_temp_path = None
        try:
            # ── Calls ────────────────────────────────────────────
            if not self.sms_only:
                print("\nFinding latest call backup on Drive...")
                calls_file = find_latest_file(self.drive, "calls-")
                if calls_file:
                    print(f"  Found: {calls_file['name']} "
                          f"({int(calls_file.get('size', 0))/1024:.0f} KB)")
                    calls_bytes = download_to_memory(self.drive, calls_file["id"])
                    print(f"  Downloaded: {len(calls_bytes)/1024:.0f} KB")
                    self.process_calls(calls_bytes)
                else:
                    print("  No call backup found in SMS_Calls_Backup folder")

            # ── SMS ──────────────────────────────────────────────
            if not self.calls_only:
                self.load_existing_sms_phones()
                cutoff = self.get_sms_cutoff()

                print(f"\nFinding latest SMS backup on Drive...")
                sms_file = find_latest_file(self.drive, "sms-")
                if sms_file:
                    size_gb = int(sms_file.get("size", 0)) / (1024 ** 3)
                    print(f"  Found: {sms_file['name']} ({size_gb:.1f} GB)")
                    print(f"  Downloading to temp file...")
                    sms_temp_path = download_to_temp(
                        self.drive, sms_file["id"], sms_file["name"]
                    )
                    self.temp_files.append(sms_temp_path)
                    print(f"  Downloaded to: {sms_temp_path}")
                    self.process_sms(sms_temp_path, cutoff)
                else:
                    print("  No SMS backup found in SMS_Calls_Backup folder")

        finally:
            # Clean up temp files
            for path in self.temp_files:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                        print(f"\n  Cleaned up temp file: {path}")
                except OSError as e:
                    print(f"  Warning: couldn't delete temp file {path}: {e}")

        elapsed = time.time() - start_time
        self._print_summary(elapsed)
        return self.stats["errors"] < 10

    def _print_summary(self, elapsed: float):
        s = self.stats
        print(f"\n{'='*60}")
        print(f"PHONE BACKUP SYNC SUMMARY")
        print(f"{'='*60}")
        if not self.calls_only:
            print(f"  SMS new messages:       {s['sms_new_messages']:,}")
            print(f"  SMS convos updated:     {s['sms_conversations_updated']}")
            print(f"  SMS convos new:         {s['sms_conversations_new']}")
        if not self.sms_only:
            print(f"  Calls in backup:        {s['calls_total']:,}")
            print(f"  Calls new:              {s['calls_new']}")
            print(f"  Calls matched:          {s['calls_matched']}")
            print(f"  Calls unmatched:        {s['calls_unmatched']}")
        print(f"  Contacts updated:       {s['contacts_updated']}")
        print(f"  Errors:                 {s['errors']}")
        print(f"  Time elapsed:           {elapsed:.1f}s")
        print(f"{'='*60}")


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    sys.stdout.reconfigure(line_buffering=True)

    parser = argparse.ArgumentParser(
        description="Sync SMS + call backups from Google Drive to contacts DB"
    )
    parser.add_argument("--calls-only", action="store_true",
                        help="Only process call logs (skip SMS download)")
    parser.add_argument("--no-sms", action="store_true",
                        help="Same as --calls-only")
    parser.add_argument("--sms-only", action="store_true",
                        help="Only process SMS (skip calls)")
    parser.add_argument("--test", "-t", action="store_true",
                        help="Test mode: 1 SMS conversation + 10 calls")
    parser.add_argument("--workers", "-w", type=int, default=10,
                        help="Concurrent workers (default: 10)")
    parser.add_argument("--recent-days", type=int, default=None,
                        help="Override SMS cutoff to N days ago")
    args = parser.parse_args()

    calls_only = args.calls_only or args.no_sms

    syncer = PhoneBackupSync(
        calls_only=calls_only,
        sms_only=args.sms_only,
        test_mode=args.test,
        workers=args.workers,
        recent_days=args.recent_days,
    )
    success = syncer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
