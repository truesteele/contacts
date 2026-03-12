#!/usr/bin/env python3
"""
Network Intelligence — Calendar Meeting History

Pulls calendar events from 5 Google accounts, matches attendee emails to contacts,
and stores meeting data in contact_calendar_events table.

Event-centric approach: pull ALL events per calendar, then batch-match against contacts.
Much more efficient than searching per-contact (5 API pulls vs 14,700).

Usage:
  python scripts/intelligence/gather_calendar_meetings.py --test              # 1 account, first 100 events
  python scripts/intelligence/gather_calendar_meetings.py --collect-only      # All accounts, no summarization
  python scripts/intelligence/gather_calendar_meetings.py --summarize-only    # LLM summary using existing data
  python scripts/intelligence/gather_calendar_meetings.py                     # Full run
  python scripts/intelligence/gather_calendar_meetings.py --force             # Re-collect everything
  python scripts/intelligence/gather_calendar_meetings.py --recent-days 7    # Only events from last 7 days
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone, timedelta
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

# Justin's own email addresses (to skip as "attendees")
JUSTIN_EMAILS = {e.lower() for e in GOOGLE_ACCOUNTS}

DESC_TRUNCATE = 500  # Truncate long event descriptions


# ── Pydantic Schemas for LLM Output ──────────────────────────────────

class MeetingSummaryItem(BaseModel):
    date: str = Field(description="Meeting date (YYYY-MM-DD)")
    account: str = Field(description="Google account email")
    summary: str = Field(description="Event title/summary")
    duration_minutes: int
    attendee_count: int
    context: str = Field(description="1-sentence description of the meeting purpose")

class MeetingHistorySummary(BaseModel):
    total_meetings: int
    first_meeting: str = Field(description="Date of earliest meeting (YYYY-MM-DD)")
    last_meeting: str = Field(description="Date of most recent meeting (YYYY-MM-DD)")
    accounts_with_meetings: list[str]
    meetings: list[MeetingSummaryItem]
    relationship_summary: str = Field(
        description="2-3 sentence summary of the meeting relationship pattern"
    )


# ── Calendar Helpers ──────────────────────────────────────────────────

def load_credentials(account_email: str) -> Optional[Credentials]:
    """Load OAuth credentials for a Google account."""
    cred_path = os.path.join(CREDENTIALS_DIR, f"{account_email}.json")
    if not os.path.exists(cred_path):
        return None

    with open(cred_path) as f:
        data = json.load(f)

    return Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )


def build_calendar_service(account_email: str):
    """Build a Google Calendar API service for the given account."""
    creds = load_credentials(account_email)
    if not creds:
        return None
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def parse_event_time(event: dict, key: str) -> Optional[datetime]:
    """Parse start/end time from a calendar event."""
    time_obj = event.get(key, {})
    dt_str = time_obj.get("dateTime") or time_obj.get("date")
    if not dt_str:
        return None
    try:
        # dateTime format: 2024-01-15T10:00:00-08:00
        if "T" in dt_str:
            return datetime.fromisoformat(dt_str)
        else:
            # All-day event: 2024-01-15
            return datetime.strptime(dt_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def is_all_day(event: dict) -> bool:
    """Check if event is an all-day event."""
    return "date" in event.get("start", {}) and "dateTime" not in event.get("start", {})


def detect_conference_type(event: dict) -> Optional[str]:
    """Detect video conference type from event data."""
    conf = event.get("conferenceData", {})
    if conf:
        solution = conf.get("conferenceSolution", {}).get("name", "").lower()
        if "meet" in solution:
            return "meet"
        if "zoom" in solution:
            return "zoom"
        if "teams" in solution:
            return "teams"
        if "webex" in solution:
            return "webex"
        return solution or None

    # Check description/location for zoom/teams links
    desc = (event.get("description") or "").lower()
    loc = (event.get("location") or "").lower()
    combined = desc + " " + loc
    if "zoom.us" in combined:
        return "zoom"
    if "teams.microsoft" in combined:
        return "teams"
    if "meet.google" in combined:
        return "meet"
    return None


def classify_event_type(event: dict) -> str:
    """Classify event type based on signals."""
    summary = (event.get("summary") or "").lower()
    conf = detect_conference_type(event)

    if any(w in summary for w in ["interview", "panel"]):
        return "interview"
    if any(w in summary for w in ["conference", "summit", "convention", "bbcon"]):
        return "conference"
    if any(w in summary for w in ["lunch", "dinner", "coffee", "drinks", "happy hour"]):
        return "social"
    if any(w in summary for w in ["call", "phone", "check-in", "check in", "standup", "stand-up"]):
        return "call"
    if any(w in summary for w in ["demo", "presentation", "pitch"]):
        return "demo"
    if any(w in summary for w in ["board meeting", "board call"]):
        return "board"
    if any(w in summary for w in ["1:1", "1-1", "one on one", "1 on 1"]):
        return "one_on_one"
    if conf:
        return "video_call"
    return "meeting"


# ── Main Class ────────────────────────────────────────────────────────

class CalendarMeetingGatherer:
    MODEL = "gpt-5-mini"
    MAX_EVENTS_PER_ACCOUNT = 10000  # Safety limit per calendar

    def __init__(self, test_mode=False, force=False,
                 collect_only=False, summarize_only=False,
                 workers=50, accounts=None, recent_days=None, ids=None):
        self.test_mode = test_mode
        self.force = force
        self.collect_only = collect_only
        self.summarize_only = summarize_only
        self.workers = workers
        self.target_accounts = accounts  # None = all accounts
        self.recent_days = recent_days  # None = all time
        self.ids = ids
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.calendar_services: dict = {}
        self.email_to_contacts: dict = {}  # email -> [contact_ids]
        self.stats = {
            "accounts_processed": 0,
            "events_scanned": 0,
            "events_with_contacts": 0,
            "events_stored": 0,
            "contacts_matched": set(),
            "contacts_summarized": 0,
            "errors": 0,
            "skipped_no_attendees": 0,
            "skipped_all_day": 0,
            "skipped_declined": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    def connect(self) -> bool:
        """Initialize Supabase, OpenAI, and Calendar connections."""
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

        # Build Calendar services
        accounts = self.target_accounts or GOOGLE_ACCOUNTS
        for acct in accounts:
            svc = build_calendar_service(acct)
            if svc:
                self.calendar_services[acct] = svc
                print(f"  Calendar: {acct} OK")
            else:
                print(f"  Calendar: {acct} SKIPPED (no credentials)")

        if not self.calendar_services:
            print("ERROR: No Calendar services available")
            return False

        print(f"Connected: Supabase, {len(self.calendar_services)} Calendar accounts"
              f"{', OpenAI' if self.openai else ''}")
        return True

    # ── Email Lookup Table ────────────────────────────────────────────

    def build_email_lookup(self):
        """Build a mapping of email -> list of contact_ids from the contacts table."""
        print("\nBuilding email → contact lookup...")
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                self.supabase.table("contacts")
                .select("id, email, work_email, personal_email, email_2")
                .range(offset, offset + page_size - 1)
            )
            if self.ids:
                query = query.in_("id", self.ids)
            page = query.execute().data

            if not page:
                break
            all_contacts.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        # Build lookup
        for c in all_contacts:
            for field in ("email", "work_email", "personal_email", "email_2"):
                val = c.get(field)
                if val and isinstance(val, str) and "@" in val:
                    email_lower = val.strip().lower()
                    if email_lower not in JUSTIN_EMAILS:
                        if email_lower not in self.email_to_contacts:
                            self.email_to_contacts[email_lower] = []
                        if c["id"] not in self.email_to_contacts[email_lower]:
                            self.email_to_contacts[email_lower].append(c["id"])

        print(f"  {len(self.email_to_contacts)} unique emails mapped to contacts")

    # ── Calendar Collection (Phase A) ─────────────────────────────────

    def collect_all(self):
        """Pull events from all calendars and match to contacts."""
        print(f"\n--- Phase A: Collecting calendar events ---\n")

        for acct, svc in self.calendar_services.items():
            print(f"\n  === {acct} ===")
            try:
                self._collect_account(acct, svc)
            except Exception as e:
                print(f"  ERROR processing {acct}: {e}")
                self.stats["errors"] += 1
            self.stats["accounts_processed"] += 1

    def _collect_account(self, account_email: str, service):
        """Pull all events from one calendar account and match to contacts."""
        now = datetime.now(timezone.utc).isoformat()
        events_scanned = 0
        events_matched = 0
        page_token = None

        while True:
            try:
                request_kwargs = {
                    "calendarId": "primary",
                    "singleEvents": True,
                    "orderBy": "startTime",
                    "maxResults": 2500,
                    "timeMax": now,
                }
                if self.recent_days:
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=self.recent_days)).isoformat()
                    request_kwargs["timeMin"] = cutoff
                if page_token:
                    request_kwargs["pageToken"] = page_token

                result = service.events().list(**request_kwargs).execute()

            except HttpError as e:
                if e.resp.status == 429:
                    print(f"    Rate limited, sleeping 30s...")
                    time.sleep(30)
                    continue
                else:
                    print(f"    API error: {e}")
                    self.stats["errors"] += 1
                    break

            items = result.get("items", [])
            if not items:
                break

            for event in items:
                events_scanned += 1
                matched = self._process_event(event, account_email)
                if matched:
                    events_matched += matched

                if self.test_mode and events_scanned >= 500:
                    print(f"    Test mode: stopping at {events_scanned} events")
                    break

            self.stats["events_scanned"] += len(items)

            if self.test_mode and events_scanned >= 500:
                break

            page_token = result.get("nextPageToken")
            if not page_token:
                break

            # Progress update
            if events_scanned % 1000 == 0:
                print(f"    Scanned {events_scanned} events, {events_matched} matched to contacts...")

            if events_scanned >= self.MAX_EVENTS_PER_ACCOUNT:
                print(f"    Safety limit: stopping at {events_scanned} events")
                break

        print(f"    Done: {events_scanned} events scanned, {events_matched} matched to contacts")

    def _process_event(self, event: dict, account_email: str) -> int:
        """Process a single event. Returns number of contact matches."""
        # Skip cancelled events
        if event.get("status") == "cancelled":
            return 0

        # Get attendees
        attendees = event.get("attendees", [])
        if not attendees:
            self.stats["skipped_no_attendees"] += 1
            return 0

        # Skip all-day events without meaningful attendees (holidays, OOO blocks)
        if is_all_day(event) and len(attendees) <= 1:
            self.stats["skipped_all_day"] += 1
            return 0

        # Check Justin's response status — skip if he declined
        acct_lower = account_email.lower()
        for att in attendees:
            if att.get("email", "").lower() in JUSTIN_EMAILS:
                if att.get("responseStatus") == "declined":
                    self.stats["skipped_declined"] += 1
                    return 0
                break

        # Find which attendee emails match contacts
        matched_contacts = set()
        for att in attendees:
            att_email = att.get("email", "").lower()
            if att_email in self.email_to_contacts:
                for cid in self.email_to_contacts[att_email]:
                    matched_contacts.add(cid)

        if not matched_contacts:
            return 0

        # Parse event data
        start_dt = parse_event_time(event, "start")
        end_dt = parse_event_time(event, "end")
        if not start_dt:
            return 0

        duration = None
        if start_dt and end_dt:
            duration = int((end_dt - start_dt).total_seconds() / 60)

        # Determine if Justin organized
        organizer = event.get("organizer", {})
        organizer_email = organizer.get("email", "").lower()
        is_organizer = organizer_email in JUSTIN_EMAILS

        # Justin's response status
        response_status = None
        for att in attendees:
            if att.get("email", "").lower() in JUSTIN_EMAILS:
                response_status = att.get("responseStatus", "needsAction")
                break

        # Truncate description
        description = event.get("description", "")
        if description and len(description) > DESC_TRUNCATE:
            description = description[:DESC_TRUNCATE] + "..."

        # Build attendee list
        attendee_list = []
        for att in attendees:
            attendee_list.append({
                "email": att.get("email", ""),
                "name": att.get("displayName", ""),
                "response_status": att.get("responseStatus", "needsAction"),
                "organizer": att.get("organizer", False),
            })

        # Store for each matched contact
        stored = 0
        for contact_id in matched_contacts:
            try:
                self._save_event(contact_id, account_email, event, {
                    "start_time": start_dt,
                    "end_time": end_dt,
                    "duration_minutes": duration,
                    "description": description,
                    "attendee_list": attendee_list,
                    "attendee_count": len(attendees),
                    "organizer_email": organizer_email,
                    "is_organizer": is_organizer,
                    "response_status": response_status,
                })
                stored += 1
                self.stats["contacts_matched"].add(contact_id)
            except Exception as e:
                print(f"    Error saving event for contact {contact_id}: {e}")
                self.stats["errors"] += 1

        self.stats["events_with_contacts"] += 1
        self.stats["events_stored"] += stored
        return stored

    def _save_event(self, contact_id: int, account_email: str,
                    event: dict, parsed: dict):
        """Upsert an event into contact_calendar_events."""
        row = {
            "contact_id": contact_id,
            "event_id": event.get("id", ""),
            "ical_uid": event.get("iCalUID"),
            "account_email": account_email,
            "summary": event.get("summary", "(no title)"),
            "description": parsed["description"],
            "start_time": parsed["start_time"].isoformat(),
            "end_time": parsed["end_time"].isoformat() if parsed["end_time"] else None,
            "duration_minutes": parsed["duration_minutes"],
            "location": event.get("location"),
            "event_type": classify_event_type(event),
            "attendee_count": parsed["attendee_count"],
            "attendees": parsed["attendee_list"],
            "organizer_email": parsed["organizer_email"],
            "is_organizer": parsed["is_organizer"],
            "response_status": parsed["response_status"],
            "recurring": event.get("recurringEventId") is not None,
            "conference_type": detect_conference_type(event),
            "gathered_at": datetime.now(timezone.utc).isoformat(),
        }

        self.supabase.table("contact_calendar_events").upsert(
            row, on_conflict="contact_id,event_id,account_email"
        ).execute()

    # ── Contact Stats Update ──────────────────────────────────────────

    def update_contact_stats(self):
        """Update comms_meeting_count and comms_last_meeting on contacts."""
        print("\n--- Updating contact meeting stats ---\n")

        # Get meeting counts and last meeting dates per contact
        # Process in batches to avoid huge queries
        contact_ids = list(self.stats["contacts_matched"])
        if not contact_ids:
            # If running --summarize-only, get contact IDs from the table
            page = (
                self.supabase.table("contact_calendar_events")
                .select("contact_id")
                .limit(5000)
            ).execute().data
            contact_ids = list({r["contact_id"] for r in page})

        updated = 0
        for cid in contact_ids:
            try:
                events = (
                    self.supabase.table("contact_calendar_events")
                    .select("start_time, ical_uid")
                    .eq("contact_id", cid)
                    .order("start_time", desc=True)
                ).execute().data

                if not events:
                    continue

                # Dedup by ical_uid for counting
                seen_uids = set()
                unique_count = 0
                for e in events:
                    uid = e.get("ical_uid")
                    if uid and uid in seen_uids:
                        continue
                    if uid:
                        seen_uids.add(uid)
                    unique_count += 1

                last_meeting = events[0]["start_time"][:10] if events else None

                self.supabase.table("contacts").update({
                    "comms_meeting_count": unique_count,
                    "comms_last_meeting": last_meeting,
                    "meetings_last_gathered_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", cid).execute()

                updated += 1
            except Exception as e:
                print(f"  Error updating contact {cid}: {e}")
                self.stats["errors"] += 1

        print(f"  Updated {updated} contacts with meeting stats")

    # ── LLM Summarization (Phase B) ───────────────────────────────────

    def summarize_contacts(self):
        """Summarize meeting history for each contact using GPT-5 mini."""
        # Get contacts with calendar events
        contacts_with_events = self._get_contacts_with_events()
        total = len(contacts_with_events)
        if total == 0:
            print("No contacts with calendar events to summarize.")
            return

        print(f"\n--- Phase B: Summarizing meetings for {total} contacts "
              f"({self.workers} concurrent workers) ---\n")

        start_time = time.time()
        done_count = 0

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {}
            for c in contacts_with_events:
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
                          f"({self.stats['contacts_summarized']} done, "
                          f"{self.stats['errors']} errors) "
                          f"[{rate:.1f}/sec, {elapsed:.0f}s] ---\n")

    def _get_contacts_with_events(self) -> list[dict]:
        """Get contacts that have entries in contact_calendar_events."""
        # Get distinct contact IDs
        all_ids = set()
        page_size = 1000
        offset = 0
        while True:
            page = (
                self.supabase.table("contact_calendar_events")
                .select("contact_id")
                .range(offset, offset + page_size - 1)
            ).execute().data
            if not page:
                break
            for r in page:
                all_ids.add(r["contact_id"])
            if len(page) < page_size:
                break
            offset += page_size

        if not all_ids:
            return []

        # Fetch contact info
        contacts = []
        id_list = list(all_ids)
        for i in range(0, len(id_list), 100):
            batch = id_list[i:i + 100]
            result = (
                self.supabase.table("contacts")
                .select("id, first_name, last_name, company, position")
                .in_("id", batch)
            ).execute().data
            contacts.extend(result)

        return contacts

    def _summarize_one_contact(self, contact: dict) -> bool:
        """Summarize a single contact's meetings. Returns True on success."""
        contact_id = contact["id"]
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

        # Fetch events from DB
        events = (
            self.supabase.table("contact_calendar_events")
            .select("summary, start_time, end_time, duration_minutes, "
                    "attendee_count, event_type, account_email, conference_type, "
                    "is_organizer, location, ical_uid")
            .eq("contact_id", contact_id)
            .order("start_time", desc=True)
            .limit(100)
        ).execute().data

        if not events:
            return False

        # Dedup by ical_uid
        seen_uids = set()
        unique_events = []
        for e in events:
            uid = e.get("ical_uid")
            if uid and uid in seen_uids:
                continue
            if uid:
                seen_uids.add(uid)
            unique_events.append(e)

        summary = self._call_llm_summary(contact, unique_events)
        if summary:
            self._save_meeting_summary(contact_id, summary)
            print(f"  [{contact_id}] {name}: {summary.total_meetings} meetings, "
                  f"last: {summary.last_meeting}")
            self.stats["contacts_summarized"] += 1
            return True
        return False

    def _call_llm_summary(self, contact: dict, events: list[dict]) -> Optional[MeetingHistorySummary]:
        """Use GPT-5 mini to summarize meeting history."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

        event_lines = []
        for e in events[:50]:  # Limit for token budget
            date = (e.get("start_time") or "")[:10]
            dur = e.get("duration_minutes", "?")
            etype = e.get("event_type", "meeting")
            acct = e.get("account_email", "?")
            conf = e.get("conference_type") or "in-person/unknown"
            att_count = e.get("attendee_count", "?")
            org = "Justin organized" if e.get("is_organizer") else "invited"
            loc = e.get("location", "")
            event_lines.append(
                f"  [{date}] \"{e.get('summary', '(no title)')}\" "
                f"({dur}min, {etype}, {conf}, {att_count} attendees, {org})"
                + (f" @ {loc}" if loc else "")
            )

        prompt = (
            f"Summarize Justin Steele's calendar meeting history with {name} "
            f"({contact.get('position', '?')} at {contact.get('company', '?')}).\n\n"
            f"There are {len(events)} meetings total:\n\n"
            + "\n".join(event_lines)
        )

        system = (
            "You are summarizing calendar meeting history between Justin Steele and a contact. "
            "For each meeting, provide a concise 1-sentence context about the likely purpose. "
            "For the relationship_summary, describe the meeting pattern: how often they meet, "
            "over what time period, what types of meetings (1:1, group, calls, in-person), "
            "and what the meetings suggest about the relationship. Keep it factual and brief."
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions=system,
                    input=prompt,
                    text_format=MeetingHistorySummary,
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

    def _save_meeting_summary(self, contact_id: int, summary: MeetingHistorySummary):
        """Save meeting summary into comms_summary JSONB."""
        # Read existing comms_summary
        existing = (
            self.supabase.table("contacts")
            .select("comms_summary")
            .eq("id", contact_id)
            .single()
        ).execute().data

        comms_summary = existing.get("comms_summary") or {}

        # Add/update meeting data
        comms_summary["meetings"] = {
            "total": summary.total_meetings,
            "first_meeting": summary.first_meeting,
            "last_meeting": summary.last_meeting,
            "accounts": summary.accounts_with_meetings,
            "relationship_summary": summary.relationship_summary,
            "recent_meetings": [m.model_dump(mode="json") for m in summary.meetings[:20]],
            "last_gathered": datetime.now(timezone.utc).isoformat(),
        }

        self.supabase.table("contacts").update({
            "comms_summary": comms_summary,
        }).eq("id", contact_id).execute()

    # ── Main Run Loop ─────────────────────────────────────────────────

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()

        # Phase A: Collection
        if not self.summarize_only:
            self.build_email_lookup()
            self.collect_all()
            self.update_contact_stats()

        # Phase B: Summarization
        if not self.collect_only:
            self.summarize_contacts()

        elapsed = time.time() - start_time
        self._print_summary(elapsed)
        return True

    def _print_summary(self, elapsed: float):
        """Print final stats."""
        contacts_matched = len(self.stats["contacts_matched"]) if isinstance(self.stats["contacts_matched"], set) else self.stats["contacts_matched"]
        print(f"\n{'='*60}")
        print(f"Calendar Meeting Gathering Complete")
        print(f"{'='*60}")
        print(f"  Accounts processed:    {self.stats['accounts_processed']}")
        print(f"  Events scanned:        {self.stats['events_scanned']}")
        print(f"  Events with contacts:  {self.stats['events_with_contacts']}")
        print(f"  Events stored:         {self.stats['events_stored']}")
        print(f"  Contacts matched:      {contacts_matched}")
        print(f"  Contacts summarized:   {self.stats['contacts_summarized']}")
        print(f"  Skipped (no attendees):{self.stats['skipped_no_attendees']}")
        print(f"  Skipped (all-day):     {self.stats['skipped_all_day']}")
        print(f"  Skipped (declined):    {self.stats['skipped_declined']}")
        print(f"  Errors:                {self.stats['errors']}")
        if self.stats["input_tokens"]:
            cost = (self.stats["input_tokens"] * 0.4 + self.stats["output_tokens"] * 1.6) / 1_000_000
            print(f"  Tokens (in/out):       {self.stats['input_tokens']:,} / {self.stats['output_tokens']:,}")
            print(f"  Estimated cost:        ${cost:.2f}")
        print(f"  Elapsed:               {elapsed:.0f}s ({elapsed/60:.1f}m)")
        print(f"{'='*60}\n")


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Gather calendar meeting history for contacts")
    parser.add_argument("--test", action="store_true", help="Test mode (limit events per account)")
    parser.add_argument("--force", action="store_true", help="Re-collect already gathered data")
    parser.add_argument("--collect-only", action="store_true", help="Only collect, no LLM summarization")
    parser.add_argument("--summarize-only", action="store_true", help="Only summarize, use existing data")
    parser.add_argument("--workers", type=int, default=50, help="Concurrent workers for summarization")
    parser.add_argument("--account", type=str, help="Process only this Google account")
    parser.add_argument("--recent-days", type=int, default=None,
                        help="Only pull events from the last N days (default: all time)")
    parser.add_argument("--ids", type=str, default=None,
                        help="Comma-separated contact IDs to process")

    args = parser.parse_args()

    accounts = None
    if args.account:
        if args.account not in GOOGLE_ACCOUNTS:
            print(f"Unknown account: {args.account}")
            print(f"Available: {', '.join(GOOGLE_ACCOUNTS)}")
            sys.exit(1)
        accounts = [args.account]

    ids = [int(x.strip()) for x in args.ids.split(",")] if args.ids else None

    gatherer = CalendarMeetingGatherer(
        test_mode=args.test,
        force=args.force or bool(ids),
        collect_only=args.collect_only,
        summarize_only=args.summarize_only,
        workers=args.workers,
        accounts=accounts,
        recent_days=args.recent_days,
        ids=ids,
    )

    success = gatherer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
