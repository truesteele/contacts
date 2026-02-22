#!/usr/bin/env python3
"""
Network Intelligence — Phase 5: Communication History

Searches Gmail across 5 Google Workspace accounts for email threads with each contact,
stores raw thread data in contact_email_threads, then summarizes with GPT-5 mini.

Usage:
  python scripts/intelligence/gather_comms_history.py --test -n 5      # 5 contacts
  python scripts/intelligence/gather_comms_history.py --collect-only    # Gmail only, no LLM
  python scripts/intelligence/gather_comms_history.py --summarize-only  # LLM only, use existing raw data
  python scripts/intelligence/gather_comms_history.py --min-proximity 40  # Warm+ contacts
  python scripts/intelligence/gather_comms_history.py                   # Full run
  python scripts/intelligence/gather_comms_history.py --force           # Re-collect already gathered
"""

import os
import sys
import json
import time
import base64
import argparse
import email.utils
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from pydantic import BaseModel, Field
from supabase import create_client, Client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

# ── Google Workspace Accounts ─────────────────────────────────────────

GOOGLE_ACCOUNTS = [
    "justinrsteele@gmail.com",
    "justin@truesteele.com",
    "justin@outdoorithm.com",
    "justin@outdoorithmcollective.org",
    "justin@kindora.co",
]

CREDENTIALS_DIR = os.path.expanduser("~/.google_workspace_mcp/credentials")

# ── Pydantic Schemas for LLM Output ──────────────────────────────────

class ThreadSummaryItem(BaseModel):
    date: str = Field(description="Date of last message in thread (YYYY-MM-DD)")
    account: str = Field(description="Google account email")
    subject: str
    direction: str = Field(description="sent | received | bidirectional")
    summary: str = Field(description="1-2 sentence summary of the thread")
    message_count: int

class CommunicationSummary(BaseModel):
    total_threads: int
    first_contact: str = Field(description="Date of earliest thread (YYYY-MM-DD)")
    last_contact: str = Field(description="Date of most recent thread (YYYY-MM-DD)")
    accounts_with_activity: list[str]
    threads: list[ThreadSummaryItem]
    relationship_summary: str = Field(
        description="2-3 sentence summary of the communication relationship"
    )


# ── Gmail Helpers ─────────────────────────────────────────────────────

def load_gmail_credentials(account_email: str) -> Optional[Credentials]:
    """Load OAuth credentials for a Google account."""
    cred_path = os.path.join(CREDENTIALS_DIR, f"{account_email}.json")
    if not os.path.exists(cred_path):
        return None

    with open(cred_path) as f:
        data = json.load(f)

    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )
    return creds


def build_gmail_service(account_email: str):
    """Build a Gmail API service for the given account."""
    creds = load_gmail_credentials(account_email)
    if not creds:
        return None
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def parse_email_header(headers: list[dict], name: str) -> str:
    """Extract a header value from Gmail message headers."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def parse_email_address(raw: str) -> dict:
    """Parse 'Name <email>' into {name, email}."""
    name, addr = email.utils.parseaddr(raw)
    return {"name": name, "email": addr.lower()}


def parse_email_addresses(raw: str) -> list[dict]:
    """Parse comma-separated email addresses."""
    if not raw:
        return []
    addrs = email.utils.getaddresses([raw])
    return [{"name": n, "email": a.lower()} for n, a in addrs if a]


def get_message_body(payload: dict) -> str:
    """Extract plain text body from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        # Recurse into multipart
        if part.get("parts"):
            body = get_message_body(part)
            if body:
                return body

    return ""


def parse_date(internal_date_ms: str) -> Optional[datetime]:
    """Parse Gmail internalDate (ms since epoch) to datetime."""
    try:
        ts = int(internal_date_ms) / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


def determine_direction(messages: list[dict], account_email: str) -> str:
    """Determine if a thread is sent, received, or bidirectional."""
    sent = False
    received = False
    acct = account_email.lower()

    for msg in messages:
        from_addr = msg.get("from", {}).get("email", "").lower()
        if from_addr == acct:
            sent = True
        else:
            received = True

    if sent and received:
        return "bidirectional"
    elif sent:
        return "sent"
    else:
        return "received"


# ── Main Class ────────────────────────────────────────────────────────

class CommsHistoryGatherer:
    MODEL = "gpt-5-mini"
    MAX_THREADS_PER_CONTACT = 50
    MAX_MESSAGES_PER_THREAD = 20
    BODY_TRUNCATE_CHARS = 3000  # Truncate long email bodies

    SELECT_COLS = (
        "id, first_name, last_name, email, work_email, personal_email, email_2, "
        "ai_proximity_score, ai_proximity_tier, company, position, "
        "comms_last_gathered_at"
    )

    def __init__(self, test_mode=False, test_count=5, force=False,
                 collect_only=False, summarize_only=False,
                 min_proximity=0, workers=10, ids_file=None):
        self.test_mode = test_mode
        self.test_count = test_count
        self.force = force
        self.collect_only = collect_only
        self.summarize_only = summarize_only
        self.min_proximity = min_proximity
        self.workers = workers
        self.ids_file = ids_file
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.gmail_services: dict = {}
        self.stats = {
            "contacts_processed": 0,
            "contacts_with_threads": 0,
            "threads_collected": 0,
            "threads_summarized": 0,
            "accounts_searched": 0,
            "errors": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    def connect(self) -> bool:
        """Initialize Supabase, OpenAI, and Gmail connections."""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        openai_key = os.environ.get("OPENAI_APIKEY")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False

        self.supabase = create_client(url, key)

        if not self.collect_only:
            if not openai_key:
                print("ERROR: Missing OPENAI_APIKEY (needed for summarization)")
                return False
            self.openai = OpenAI(api_key=openai_key)

        # Build Gmail services
        for acct in GOOGLE_ACCOUNTS:
            svc = build_gmail_service(acct)
            if svc:
                self.gmail_services[acct] = svc
                print(f"  Gmail: {acct} OK")
            else:
                print(f"  Gmail: {acct} SKIPPED (no credentials)")

        if not self.gmail_services:
            print("ERROR: No Gmail services available")
            return False

        print(f"Connected: Supabase, {len(self.gmail_services)} Gmail accounts"
              f"{', OpenAI' if self.openai else ''}")
        return True

    # ── Contact Fetching ──────────────────────────────────────────────

    def get_contacts(self) -> list[dict]:
        """Fetch contacts with email addresses, ordered by proximity score."""
        # If --ids-file is provided, only fetch those specific contacts
        if self.ids_file:
            import json as _json
            with open(self.ids_file) as f:
                target_ids = _json.load(f)
            all_contacts = []
            for i in range(0, len(target_ids), 100):
                batch = target_ids[i:i + 100]
                result = (
                    self.supabase.table("contacts")
                    .select(self.SELECT_COLS)
                    .in_("id", batch)
                    .order("ai_proximity_score", desc=True)
                    .execute()
                ).data
                all_contacts.extend(result)
            # Filter to contacts with at least one email
            all_contacts = [c for c in all_contacts if self._get_contact_emails(c)]
            if self.test_mode:
                all_contacts = all_contacts[:self.test_count]
            return all_contacts

        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                self.supabase.table("contacts")
                .select(self.SELECT_COLS)
                .order("ai_proximity_score", desc=True)
                .range(offset, offset + page_size - 1)
            )

            if self.min_proximity > 0:
                query = query.gte("ai_proximity_score", self.min_proximity)

            if not self.force and not self.summarize_only:
                query = query.is_("comms_last_gathered_at", "null")

            response = query.execute()
            page = response.data
            if not page:
                break

            # Filter to contacts with at least one email
            for c in page:
                emails = self._get_contact_emails(c)
                if emails:
                    all_contacts.append(c)

            if len(page) < page_size:
                break
            offset += page_size

        if self.test_mode:
            all_contacts = all_contacts[:self.test_count]

        return all_contacts

    def _get_contact_emails(self, contact: dict) -> list[str]:
        """Collect all non-empty email addresses for a contact."""
        emails = set()
        for field in ("email", "work_email", "personal_email", "email_2"):
            val = contact.get(field)
            if val and isinstance(val, str) and val.strip() and "@" in val:
                emails.add(val.strip().lower())
        return list(emails)

    # ── Gmail Collection (Phase A) ────────────────────────────────────

    def collect_for_contact(self, contact: dict) -> int:
        """Search Gmail across all accounts for a contact's emails. Returns thread count."""
        contact_id = contact["id"]
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        emails = self._get_contact_emails(contact)

        all_threads = {}  # (thread_id, account) -> thread_data

        for acct, svc in self.gmail_services.items():
            try:
                threads = self._search_account(svc, acct, emails)
                for t in threads:
                    key = (t["thread_id"], acct)
                    if key not in all_threads:
                        all_threads[key] = t
                self.stats["accounts_searched"] += 1
            except Exception as e:
                print(f"    Error searching {acct} for {name}: {e}")
                self.stats["errors"] += 1

        if not all_threads:
            return 0

        # Save to database
        saved = 0
        for (tid, acct), thread_data in all_threads.items():
            try:
                self._save_thread(contact_id, acct, thread_data)
                saved += 1
            except Exception as e:
                print(f"    Error saving thread {tid}: {e}")
                self.stats["errors"] += 1

        self.stats["threads_collected"] += saved
        return saved

    def _search_account(self, service, account_email: str, contact_emails: list[str]) -> list[dict]:
        """Search a single Gmail account for threads involving the contact's emails."""
        # Build query: (from:a@b OR to:a@b) OR (from:c@d OR to:c@d)
        email_queries = []
        for em in contact_emails:
            email_queries.append(f"from:{em} OR to:{em}")
        query = " OR ".join(f"({q})" for q in email_queries)

        threads = []
        try:
            results = service.users().messages().list(
                userId="me", q=query, maxResults=200
            ).execute()

            if not results.get("messages"):
                return []

            # Collect unique thread IDs
            thread_ids = set()
            for msg in results.get("messages", []):
                thread_ids.add(msg["threadId"])

            # Limit threads
            thread_ids = list(thread_ids)[:self.MAX_THREADS_PER_CONTACT]

            # Fetch each thread
            for tid in thread_ids:
                thread_data = self._fetch_thread(service, account_email, tid)
                if thread_data:
                    threads.append(thread_data)
                time.sleep(0.05)  # Gentle rate limiting

        except HttpError as e:
            if e.resp.status == 429:
                print(f"    Rate limited on {account_email}, sleeping 10s...")
                time.sleep(10)
            else:
                raise

        return threads

    def _fetch_thread(self, service, account_email: str, thread_id: str) -> Optional[dict]:
        """Fetch a full thread and parse it into our storage format."""
        try:
            thread = service.users().threads().get(
                userId="me", id=thread_id, format="full"
            ).execute()
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise

        messages_raw = thread.get("messages", [])
        if not messages_raw:
            return None

        parsed_messages = []
        all_participants = set()
        dates = []
        subject = ""
        labels_set = set()

        for msg in messages_raw[:self.MAX_MESSAGES_PER_THREAD]:
            headers = msg.get("payload", {}).get("headers", [])
            from_raw = parse_email_header(headers, "From")
            to_raw = parse_email_header(headers, "To")
            cc_raw = parse_email_header(headers, "Cc")
            subj = parse_email_header(headers, "Subject")
            if subj and not subject:
                subject = subj

            from_parsed = parse_email_address(from_raw)
            to_parsed = parse_email_addresses(to_raw)
            cc_parsed = parse_email_addresses(cc_raw)

            # Track participants
            if from_parsed.get("email"):
                all_participants.add(from_parsed["email"])
            for p in to_parsed + cc_parsed:
                if p.get("email"):
                    all_participants.add(p["email"])

            # Parse date
            msg_date = parse_date(msg.get("internalDate", ""))
            if msg_date:
                dates.append(msg_date)

            # Get body
            body = get_message_body(msg.get("payload", {}))
            if len(body) > self.BODY_TRUNCATE_CHARS:
                body = body[:self.BODY_TRUNCATE_CHARS] + "\n[... truncated]"

            # Labels
            for lbl in msg.get("labelIds", []):
                labels_set.add(lbl)

            parsed_messages.append({
                "message_id": msg.get("id", ""),
                "date": msg_date.isoformat() if msg_date else None,
                "from": from_parsed,
                "to": to_parsed,
                "cc": cc_parsed,
                "subject": subj,
                "body_text": body,
                "labels": msg.get("labelIds", []),
            })

        direction = determine_direction(parsed_messages, account_email)

        return {
            "thread_id": thread_id,
            "subject": subject,
            "snippet": thread.get("snippet", ""),
            "message_count": len(parsed_messages),
            "first_message_date": min(dates).isoformat() if dates else None,
            "last_message_date": max(dates).isoformat() if dates else None,
            "direction": direction,
            "participants": [{"email": e} for e in sorted(all_participants)],
            "labels": sorted(labels_set),
            "raw_messages": parsed_messages,
        }

    def _save_thread(self, contact_id: int, account_email: str, thread_data: dict):
        """Upsert a thread into contact_email_threads."""
        row = {
            "contact_id": contact_id,
            "thread_id": thread_data["thread_id"],
            "account_email": account_email,
            "subject": thread_data.get("subject", ""),
            "snippet": thread_data.get("snippet", ""),
            "message_count": thread_data.get("message_count", 0),
            "first_message_date": thread_data.get("first_message_date"),
            "last_message_date": thread_data.get("last_message_date"),
            "direction": thread_data.get("direction"),
            "participants": thread_data.get("participants"),
            "labels": thread_data.get("labels"),
            "raw_messages": thread_data.get("raw_messages"),
            "gathered_at": datetime.now(timezone.utc).isoformat(),
        }

        self.supabase.table("contact_email_threads").upsert(
            row, on_conflict="contact_id,thread_id,account_email"
        ).execute()

    # ── LLM Summarization (Phase B) ──────────────────────────────────

    def _summarize_one_contact(self, contact: dict) -> bool:
        """Summarize a single contact's threads. Returns True on success."""
        contact_id = contact["id"]
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

        # Fetch threads from DB
        threads = (
            self.supabase.table("contact_email_threads")
            .select("*")
            .eq("contact_id", contact_id)
            .order("last_message_date", desc=True)
            .limit(50)
            .execute()
        ).data

        if not threads:
            return False

        summary = self._summarize_contact_threads(contact, threads)
        if summary:
            self._save_summary(contact_id, threads, summary)
            thread_count = summary.total_threads
            print(f"  [{contact_id}] {name}: {thread_count} threads, "
                  f"last contact: {summary.last_contact}")
            self.stats["threads_summarized"] += thread_count
            self.stats["contacts_with_threads"] += 1
            return True
        return False

    def summarize_contacts(self, contacts: list[dict]):
        """Summarize communication history for contacts using GPT-5 mini."""
        total = len(contacts)
        print(f"\n--- Phase B: Summarizing threads for {total} contacts "
              f"({self.workers} concurrent workers) ---\n")

        start_time = time.time()
        done_count = 0

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {}
            for c in contacts:
                future = executor.submit(self._summarize_one_contact, c)
                futures[future] = c["id"]

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
                    print(f"\n  --- Summarized {done_count}/{total} "
                          f"({self.stats['contacts_with_threads']} with history, "
                          f"{self.stats['errors']} errors) "
                          f"[{rate:.1f}/sec, {elapsed:.0f}s] ---\n")

    def _summarize_contact_threads(self, contact: dict, threads: list[dict]) -> Optional[CommunicationSummary]:
        """Use GPT-5 mini to summarize all threads for a contact."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

        # Build context from threads
        thread_summaries = []
        for t in threads[:30]:  # Limit input threads for token budget
            messages = t.get("raw_messages", [])
            # Build a condensed view of the thread
            msg_previews = []
            for msg in (messages or [])[:5]:  # First 5 messages per thread
                from_name = msg.get("from", {}).get("name") or msg.get("from", {}).get("email", "?")
                body_preview = (msg.get("body_text") or "")[:500]
                date = msg.get("date", "")[:10]
                msg_previews.append(f"  [{date}] {from_name}: {body_preview}")

            thread_summaries.append(
                f"Thread: {t.get('subject', '(no subject)')}\n"
                f"Account: {t.get('account_email', '?')}\n"
                f"Messages: {t.get('message_count', 0)}, "
                f"Date range: {(t.get('first_message_date') or '')[:10]} to {(t.get('last_message_date') or '')[:10]}\n"
                f"Direction: {t.get('direction', '?')}\n"
                + "\n".join(msg_previews)
            )

        prompt = (
            f"Summarize Justin Steele's email communication history with {name} "
            f"({contact.get('position', '?')} at {contact.get('company', '?')}).\n\n"
            f"There are {len(threads)} total email threads across these Google accounts.\n\n"
            + "\n---\n".join(thread_summaries)
        )

        system = (
            "You are summarizing email communication history between Justin Steele and a contact. "
            "For each thread, provide a concise 1-2 sentence summary of what was discussed. "
            "For the relationship_summary, describe the overall communication pattern: "
            "how long they've been in touch, how frequently, what topics dominate, "
            "and the nature of the relationship (professional, personal, both). "
            "Keep summaries factual and brief."
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions=system,
                    input=prompt,
                    text_format=CommunicationSummary,
                )

                if resp.usage:
                    self.stats["input_tokens"] += resp.usage.input_tokens
                    self.stats["output_tokens"] += resp.usage.output_tokens

                return resp.output_parsed

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
                print(f"    Unexpected error in summarization: {e}")
                return None

        return None

    def _save_summary(self, contact_id: int, threads: list[dict], summary: CommunicationSummary):
        """Save per-thread summaries and aggregate communication_history."""
        # Update per-thread summaries in contact_email_threads
        for ts in summary.threads:
            # Match by subject + account
            matching = [
                t for t in threads
                if t.get("account_email") == ts.account
                and (t.get("subject") or "").strip() == ts.subject.strip()
            ]
            if matching:
                self.supabase.table("contact_email_threads").update({
                    "summary": ts.summary
                }).eq("id", matching[0]["id"]).execute()

        # Build aggregate communication_history JSONB
        comm_history = {
            "last_gathered": datetime.now(timezone.utc).isoformat(),
            "total_threads": summary.total_threads,
            "first_contact": summary.first_contact,
            "last_contact": summary.last_contact,
            "accounts_with_activity": summary.accounts_with_activity,
            "threads": [t.model_dump(mode="json") for t in summary.threads],
            "relationship_summary": summary.relationship_summary,
        }

        self.supabase.table("contacts").update({
            "communication_history": comm_history,
            "comms_last_gathered_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", contact_id).execute()

    # ── Main Run Loop ─────────────────────────────────────────────────

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()
        contacts = self.get_contacts()
        total = len(contacts)
        print(f"Found {total} contacts to process")

        if total == 0:
            print("Nothing to do (use --force to re-collect)")
            return True

        # Phase A: Gmail Collection
        if not self.summarize_only:
            print(f"\n--- Phase A: Collecting Gmail threads for {total} contacts ---\n")
            for i, contact in enumerate(contacts):
                name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                prox = contact.get("ai_proximity_score", 0)

                thread_count = self.collect_for_contact(contact)
                self.stats["contacts_processed"] += 1

                if thread_count > 0:
                    self.stats["contacts_with_threads"] += 1
                    print(f"  [{contact['id']}] {name} (prox={prox}): {thread_count} threads")
                else:
                    print(f"  [{contact['id']}] {name} (prox={prox}): no threads")

                if (i + 1) % 25 == 0 or (i + 1) == total:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    print(f"\n--- Progress: {i + 1}/{total} "
                          f"({self.stats['threads_collected']} threads, "
                          f"{self.stats['contacts_with_threads']} with history) "
                          f"[{rate:.1f}/sec, {elapsed:.0f}s] ---\n")

            # Mark collection timestamp for contacts that were processed
            if not self.collect_only:
                # Reset stats for Phase B counting
                self.stats["contacts_with_threads"] = 0

        # Phase B: LLM Summarization
        if not self.collect_only:
            # For summarize_only, re-fetch contacts that have threads
            if self.summarize_only:
                contacts_to_summarize = self._get_contacts_with_threads()
            else:
                contacts_to_summarize = contacts

            self.summarize_contacts(contacts_to_summarize)

        elapsed = time.time() - start_time
        self._print_summary(elapsed)
        return self.stats["errors"] < max(total * 0.1, 5)

    def _get_contacts_with_threads(self) -> list[dict]:
        """Get contacts that have threads in contact_email_threads.

        Skips contacts already summarized (comms_last_gathered_at set) unless --force.
        """
        # Fetch distinct contact IDs from threads table (paginated)
        all_thread_contacts = []
        page_size = 1000
        offset = 0
        while True:
            page = (
                self.supabase.table("contact_email_threads")
                .select("contact_id")
                .range(offset, offset + page_size - 1)
                .execute()
            ).data
            if not page:
                break
            all_thread_contacts.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        thread_contacts = all_thread_contacts

        if not thread_contacts:
            return []

        contact_ids = list(set(t["contact_id"] for t in thread_contacts))

        # Fetch those contacts
        all_contacts = []
        # Batch fetch in groups of 100
        for i in range(0, len(contact_ids), 100):
            batch = contact_ids[i:i + 100]
            query = (
                self.supabase.table("contacts")
                .select(self.SELECT_COLS)
                .in_("id", batch)
                .order("ai_proximity_score", desc=True)
            )
            # Skip already-summarized contacts unless --force
            if not self.force:
                query = query.is_("comms_last_gathered_at", "null")
            result = query.execute().data
            all_contacts.extend(result)

        if self.test_mode:
            all_contacts = all_contacts[:self.test_count]

        return all_contacts

    def _print_summary(self, elapsed: float):
        s = self.stats
        input_cost = s["input_tokens"] * 0.15 / 1_000_000
        output_cost = s["output_tokens"] * 0.60 / 1_000_000
        total_cost = input_cost + output_cost

        print("\n" + "=" * 60)
        print("COMMUNICATION HISTORY SUMMARY")
        print("=" * 60)
        print(f"  Contacts processed:     {s['contacts_processed']}")
        print(f"  Contacts with threads:  {s['contacts_with_threads']}")
        print(f"  Threads collected:      {s['threads_collected']}")
        print(f"  Threads summarized:     {s['threads_summarized']}")
        print(f"  Accounts searched:      {s['accounts_searched']}")
        print(f"  Errors:                 {s['errors']}")
        if s["input_tokens"] > 0:
            print(f"  LLM input tokens:       {s['input_tokens']:,}")
            print(f"  LLM output tokens:      {s['output_tokens']:,}")
            print(f"  LLM cost:               ${total_cost:.2f}")
        print(f"  Time elapsed:           {elapsed:.1f}s")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Gather communication history from Gmail for contacts"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only N contacts (default: 5)")
    parser.add_argument("--count", "-n", type=int, default=5,
                        help="Number of contacts in test mode (default: 5)")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-collect contacts already gathered")
    parser.add_argument("--collect-only", action="store_true",
                        help="Only collect Gmail threads, skip summarization")
    parser.add_argument("--summarize-only", action="store_true",
                        help="Only summarize existing threads, skip Gmail collection")
    parser.add_argument("--min-proximity", type=int, default=0,
                        help="Minimum ai_proximity_score to process (default: 0)")
    parser.add_argument("--workers", "-w", type=int, default=10,
                        help="Concurrent workers (default: 10)")
    parser.add_argument("--ids-file", type=str, default=None,
                        help="JSON file with list of contact IDs to process")
    args = parser.parse_args()

    gatherer = CommsHistoryGatherer(
        test_mode=args.test,
        test_count=args.count,
        force=args.force,
        collect_only=args.collect_only,
        summarize_only=args.summarize_only,
        min_proximity=args.min_proximity,
        workers=args.workers,
        ids_file=args.ids_file,
    )
    success = gatherer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
