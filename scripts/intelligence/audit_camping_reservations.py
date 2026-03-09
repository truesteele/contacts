#!/usr/bin/env python3
"""
Camping Reservation Audit — Complete historical record from Gmail

Searches 3 Gmail accounts for reservation emails from all known camping
providers, parses them via GPT-5 mini, reconciles modifications/cancellations,
and stores canonical trip records in Supabase.

Usage:
  python scripts/intelligence/audit_camping_reservations.py              # Full run
  python scripts/intelligence/audit_camping_reservations.py --test       # Process first 10 emails
  python scripts/intelligence/audit_camping_reservations.py --search-only  # Just search, don't parse
  python scripts/intelligence/audit_camping_reservations.py --dry-run    # Show what would be done
"""

import os
import sys
import json
import time
import base64
import email.utils
import argparse
from datetime import datetime, date, timezone, timedelta
from typing import Optional
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from pydantic import BaseModel, Field
from supabase import create_client, Client
import re
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────

GOOGLE_ACCOUNTS = [
    "justinrsteele@gmail.com",
    "justin@outdoorithm.com",
    "justin@outdoorithmcollective.org",
]

CREDENTIALS_DIR = os.path.expanduser("~/.google_workspace_mcp/credentials")

# Provider search queries — (from_filter, subject_filter)
PROVIDER_SEARCHES = [
    ("from:communications@recreation.gov", ""),
    ("from:noreply@reservecalifornia.com", "subject:(confirmation OR reservation OR cancellation OR cancelled)"),
    ("from:reservecalifornia@parks.ca.gov", "subject:(confirmation OR reservation OR cancellation OR cancelled)"),
    ("from:AutomaticEmail@usedirect.com", "subject:(confirmation OR reservation OR cancellation OR cancelled)"),
    ("from:noreply@reserveamerica.com", "subject:(confirmation OR cancelled)"),
    ("from:reserveamerica@reserveamerica.com", "subject:(confirmation OR cancelled)"),
    ("from:sonomacountyparks@itinio.com", "subject:(reservation OR confirmation)"),
    ("from:hipcamp.com", "subject:(reservation OR booking OR confirmation OR cancelled)"),
    ("from:campspot.com", "subject:(reservation OR booking OR confirmation)"),
    ("from:koa.com", "subject:(reservation OR booking OR confirmation)"),
    ("from:thousandtrails.com", "subject:(reservation OR booking OR confirmation)"),
]


# ── Pydantic Schema for GPT-5 mini ───────────────────────────────────

class EmailType(str, Enum):
    confirmation = "confirmation"
    reminder = "reminder"
    cancellation = "cancellation"
    modification = "modification"
    receipt = "receipt"
    survey = "survey"
    marketing = "marketing"
    drawing = "drawing"
    notification = "notification"
    other = "other"

class Provider(str, Enum):
    recreation_gov = "recreation_gov"
    reserve_california = "reserve_california"
    itinio = "itinio"
    reserve_america = "reserve_america"
    hipcamp = "hipcamp"
    thousand_trails = "thousand_trails"
    koa = "koa"
    campspot = "campspot"
    other = "other"

class ParsedReservationEmail(BaseModel):
    email_type: EmailType = Field(description="Type of email: confirmation, reminder, cancellation, modification, receipt, survey, marketing, drawing, notification, or other")
    is_actual_reservation: bool = Field(description="True if this email is about an actual camping reservation (not marketing, survey, drawing, or general notification)")
    provider: Provider
    reservation_number: str = Field(description="The reservation/order/confirmation number. Recreation.gov uses format like 0893484254-1 or 0893484254. ReserveCalifornia uses #XXXXXXXX. Use the most specific ID available.")
    campground_name: str = Field(default="", description="Name of the campground")
    park_system: str = Field(default="", description="National Forest, National Park, State Park name, etc.")
    site_number: str = Field(default="", description="The specific campsite number/letter")
    check_in_date: str = Field(default="", description="Check-in date in YYYY-MM-DD format")
    check_out_date: str = Field(default="", description="Check-out date in YYYY-MM-DD format")
    num_nights: Optional[int] = Field(default=None)
    primary_occupant: str = Field(default="", description="Name on the reservation")
    num_occupants: Optional[int] = Field(default=None)
    equipment: str = Field(default="", description="tent, trailer, rv, caravan, etc.")
    num_vehicles: Optional[int] = Field(default=None)
    total_cost: Optional[float] = Field(default=None, description="Total cost in dollars. For cancellations, use the Total Paid amount.")
    cancellation_fee: Optional[float] = Field(default=None)
    refund_amount: Optional[float] = Field(default=None)
    original_check_in: str = Field(default="", description="For modifications: the ORIGINAL check-in date before the change, in YYYY-MM-DD")
    original_check_out: str = Field(default="", description="For modifications: the ORIGINAL check-out date before the change, in YYYY-MM-DD")
    modification_description: str = Field(default="", description="For modifications: brief description of what changed")


class DuplicateMatch(BaseModel):
    """GPT-5 mini output for fuzzy campground duplicate detection."""
    is_same_trip: bool = Field(description="True if these two entries are clearly the same camping trip (same campground, same or overlapping dates)")
    confidence: str = Field(description="high, medium, or low")
    reasoning: str = Field(description="Brief explanation of why these are or aren't the same trip")
    preferred_campground_name: str = Field(default="", description="If is_same_trip, the most complete/correct campground name")
    preferred_check_in: str = Field(default="", description="If is_same_trip, the correct check-in date (YYYY-MM-DD)")
    preferred_check_out: str = Field(default="", description="If is_same_trip, the correct check-out date (YYYY-MM-DD)")


class DateConsensus(BaseModel):
    """GPT-5 mini output for resolving conflicting dates across emails for one reservation."""
    correct_check_in: str = Field(description="The correct final check-in date in YYYY-MM-DD")
    correct_check_out: str = Field(description="The correct final check-out date in YYYY-MM-DD")
    reasoning: str = Field(description="Brief explanation of how you determined the correct dates")


class BestCampgroundName(BaseModel):
    """GPT-5 mini output for choosing the best campground name from multiple emails."""
    best_name: str = Field(description="The most specific, human-readable campground name")
    reasoning: str = Field(description="Brief explanation of the choice")


SYSTEM_PROMPT = """You are a camping reservation email parser. Extract structured data from camping reservation emails.

CRITICAL RULES:
1. Set is_actual_reservation=true ONLY for emails about specific CAMPSITE bookings (confirmations, reminders, cancellations, modifications, receipts for campsite stays). Set false for:
   - Marketing, surveys, drawings, general notifications
   - Day-use passes, ticketed entry reservations (e.g. "Yosemite National Park Ticketed Entry", "Peak Hour Reservations")
   - Parking reservations, shuttle reservations
   These are NOT campsite bookings even though they come from recreation.gov.
2. For Recreation.gov, the reservation number is in format XXXXXXXXXX-X (e.g. 0893484254-1). Sometimes shown as just the first part (0893484254). Use the full format with -1 suffix when available.
3. For ReserveCalifornia, the confirmation number is a # followed by digits (e.g. #28168371). Use this as the reservation_number but WITHOUT the # symbol.
4. For modifications, identify BOTH the original dates and the new dates. The new dates go in check_in_date/check_out_date, original dates go in original_check_in/original_check_out.
5. For cancellations, still extract the campground, dates, and financial details.
6. Dates must be in YYYY-MM-DD format.
7. For ReserveCalifornia, distinguish MODIFICATIONS from CANCELLATIONS carefully:
   - MODIFICATION: Has [Original Reservation] AND [New Reservation] blocks, shows "Grand Total" (often negative due to partial refund), has both negative AND positive Quantity lines. email_type = "modification".
   - CANCELLATION: Has "Refund Total" (NOT "Grand Total"), negative quantities only, may say "Status: CANCELLED" or "has been cancelled". email_type = "cancellation".
   - A cancellation of a previously-modified reservation may still show [Original]/[New] blocks, but will have "Refund Total" instead of "Grand Total".
8. For reminders, extract all the reservation details - they contain full booking info.
9. total_cost should be the positive amount originally paid (not refund amounts).
10. Recreation.gov modifications: Recreation.gov does NOT send "modification" emails. Instead, it sends a NEW "Reservation Confirmation" with updated dates + a separate "Refund Confirmation" for the removed nights, both at the same timestamp. The new confirmation contains the CORRECT final dates. If you see multiple Reservation Confirmation emails for the same reservation with different dates, the LATEST confirmation has the correct dates.

CAMPGROUND NAME EXTRACTION:
- Use the ACTUAL campground name, not the loop/area/section name.
- BAD: "D (STANDARD NONELECTRIC)", "Loop C (STANDARD NONELECTRIC)", "Loop 1 (STANDARD NONELECTRIC)", "AREA ROCK CREEK LAKE (STANDARD NONELECTRIC)"
- GOOD: "PINECREST", "PINNACLES CAMPGROUND", "Little Crater Campground", "ROCK CREEK LAKE"
- The campground name is usually in the subject or a prominent header. Loop/section names appear in the site details.
- Strip suffixes like "(STANDARD NONELECTRIC)", "(TENT ONLY NONELECTRIC)", "FS" from campground names.
- Strip prefixes like "AREA " from campground names.

DATE EXTRACTION IS CRITICAL:
- Look VERY carefully for dates in any format: "Mar 28, 2021", "03/28/2021", "2021-03-28", "March 28 - 30", etc.
- Check-in/check-out dates may appear as "Arrival"/"Departure", "Start Date"/"End Date", "Check In"/"Check Out", date ranges like "Jul 28 - Jul 30, 2021"
- Recreation.gov confirmation emails often have dates in the reservation details section
- Order receipts may show dates as "Use Date" or in the item description
- If you see a date range in ANY part of the email, extract it
- NEVER leave check_in_date empty if a date is present anywhere in the email
"""


# ── Gmail Helpers (from gather_comms_history.py) ─────────────────────

def load_gmail_credentials(account_email: str) -> Optional[Credentials]:
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


def build_gmail_service(account_email: str):
    creds = load_gmail_credentials(account_email)
    if not creds:
        return None
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def parse_email_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def html_to_text(html: str) -> str:
    """Convert HTML to readable plain text."""
    soup = BeautifulSoup(html, "html.parser")
    # Remove script/style
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text


def _extract_body_part(payload: dict, mime_type: str) -> str:
    """Recursively extract a body part by MIME type."""
    if payload.get("mimeType") == mime_type and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        result = _extract_body_part(part, mime_type)
        if result:
            return result
    return ""


def get_message_body(payload: dict) -> str:
    """Extract plain text body, fallback to HTML converted to text."""
    # Try plain text first
    text = _extract_body_part(payload, "text/plain")
    if text:
        return text

    # Fallback: extract HTML and convert to text
    html = _extract_body_part(payload, "text/html")
    if html:
        return html_to_text(html)

    return ""


# ── Main Auditor ──────────────────────────────────────────────────────

class CampingAuditor:
    MODEL = "gpt-5-mini"

    def __init__(self, test_mode=False, test_count=10, search_only=False, dry_run=False, provider_filter=None):
        self.test_mode = test_mode
        self.test_count = test_count
        self.search_only = search_only
        self.dry_run = dry_run
        self.provider_filter = provider_filter  # e.g. "recreation_gov" to only search rec.gov
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.gmail_services: dict = {}
        self.stats = {
            "emails_found": 0,
            "emails_fetched": 0,
            "emails_parsed": 0,
            "reservations_found": 0,
            "non_reservation": 0,
            "parse_errors": 0,
            "reservations_saved": 0,
            "cancelled": 0,
            "modified": 0,
            "completed": 0,
            "confirmed": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    def connect(self):
        # Supabase
        sb_url = os.environ.get("SUPABASE_URL")
        sb_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
        if not sb_url or not sb_key:
            print("ERROR: SUPABASE_URL and SUPABASE_KEY required")
            sys.exit(1)
        self.supabase = create_client(sb_url, sb_key)

        # OpenAI
        if not self.search_only and not self.dry_run:
            openai_key = os.environ.get("OPENAI_APIKEY")
            if not openai_key:
                print("ERROR: OPENAI_APIKEY required for parsing")
                sys.exit(1)
            self.openai = OpenAI(api_key=openai_key)

        # Gmail
        for acct in GOOGLE_ACCOUNTS:
            svc = build_gmail_service(acct)
            if svc:
                self.gmail_services[acct] = svc
                print(f"  Gmail: {acct} OK")
            else:
                print(f"  Gmail: {acct} SKIPPED (no credentials)")

        if not self.gmail_services:
            print("ERROR: No Gmail accounts connected")
            sys.exit(1)

        print(f"\nConnected: Supabase, {len(self.gmail_services)} Gmail accounts")

    # ── Search Phase ──────────────────────────────────────────────────

    def search_all_accounts(self) -> list[dict]:
        """Search all accounts for reservation emails. Returns deduplicated list of {account, message_id, thread_id}."""
        all_messages = []
        seen_ids = set()  # (account, message_id)

        # Filter searches if --provider is set
        PROVIDER_SEARCH_MAP = {
            "recreation_gov": [("from:communications@recreation.gov", "")],
            "reserve_california": [
                ("from:noreply@reservecalifornia.com", "subject:(confirmation OR reservation OR cancelled)"),
                ("from:reservecalifornia@parks.ca.gov", "subject:(confirmation OR reservation)"),
                ("from:AutomaticEmail@usedirect.com", "subject:(confirmation OR reservation OR cancellation OR cancelled)"),
            ],
            "reserve_america": [
                ("from:noreply@reserveamerica.com", "subject:(confirmation OR cancelled)"),
                ("from:reserveamerica@reserveamerica.com", "subject:(confirmation OR cancelled)"),
            ],
            "itinio": [("from:sonomacountyparks@itinio.com", "subject:(reservation OR confirmation)")],
            "hipcamp": [("from:hipcamp.com", "subject:(reservation OR booking OR confirmation OR cancelled)")],
            "koa": [("from:koa.com", "subject:(reservation OR booking OR confirmation)")],
            "thousand_trails": [("from:thousandtrails.com", "subject:(reservation OR booking OR confirmation)")],
            "campspot": [("from:campspot.com", "subject:(reservation OR booking OR confirmation)")],
        }

        if self.provider_filter:
            searches = PROVIDER_SEARCH_MAP.get(self.provider_filter, [])
            if not searches:
                print(f"  Unknown provider: {self.provider_filter}")
                return []
            print(f"  Filtering to provider: {self.provider_filter}")
        else:
            searches = PROVIDER_SEARCHES

        for acct, svc in self.gmail_services.items():
            print(f"\n  Searching {acct}...")
            acct_count = 0

            for from_filter, subj_filter in searches:
                query = f"{from_filter} {subj_filter}".strip()
                try:
                    page_token = None
                    while True:
                        result = svc.users().messages().list(
                            userId="me",
                            q=query,
                            maxResults=100,
                            pageToken=page_token,
                        ).execute()

                        messages = result.get("messages", [])
                        for msg in messages:
                            key = (acct, msg["id"])
                            if key not in seen_ids:
                                seen_ids.add(key)
                                all_messages.append({
                                    "account": acct,
                                    "message_id": msg["id"],
                                    "thread_id": msg["threadId"],
                                })
                                acct_count += 1

                        page_token = result.get("nextPageToken")
                        if not page_token:
                            break

                except HttpError as e:
                    print(f"    Search error for '{query}': {e}")

            print(f"    Found {acct_count} unique messages")

        self.stats["emails_found"] = len(all_messages)
        print(f"\n  Total unique messages: {len(all_messages)}")
        return all_messages

    # ── Fetch Phase ───────────────────────────────────────────────────

    def fetch_messages(self, messages: list[dict]) -> list[dict]:
        """Fetch full message content for all messages."""
        fetched = []
        total = len(messages)

        # Group by account for efficient batching
        by_account = {}
        for msg in messages:
            by_account.setdefault(msg["account"], []).append(msg)

        for acct, acct_msgs in by_account.items():
            svc = self.gmail_services[acct]
            print(f"\n  Fetching {len(acct_msgs)} messages from {acct}...")

            for i, msg_info in enumerate(acct_msgs):
                try:
                    result = svc.users().messages().get(
                        userId="me",
                        id=msg_info["message_id"],
                        format="full",
                    ).execute()

                    headers = result.get("payload", {}).get("headers", [])
                    subject = parse_email_header(headers, "Subject")
                    from_addr = parse_email_header(headers, "From")
                    date_str = parse_email_header(headers, "Date")
                    body = get_message_body(result.get("payload", {}))

                    fetched.append({
                        "account": msg_info["account"],
                        "message_id": msg_info["message_id"],
                        "subject": subject,
                        "from": from_addr,
                        "date": date_str,
                        "body": body[:8000],  # Truncate very long bodies
                    })

                    if (i + 1) % 50 == 0:
                        print(f"    Fetched {i+1}/{len(acct_msgs)}")

                except HttpError as e:
                    print(f"    Fetch error {msg_info['message_id']}: {e}")

        self.stats["emails_fetched"] = len(fetched)
        print(f"\n  Total fetched: {len(fetched)}")
        return fetched

    # ── Parse Phase ───────────────────────────────────────────────────

    def parse_email(self, email_data: dict) -> Optional[ParsedReservationEmail]:
        """Parse a single email using GPT-5 mini structured output."""
        user_message = f"""Parse this camping reservation email:

FROM: {email_data['from']}
SUBJECT: {email_data['subject']}
DATE: {email_data['date']}
ACCOUNT: {email_data['account']}

BODY:
{email_data['body'][:6000]}"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions=SYSTEM_PROMPT,
                    input=user_message,
                    text_format=ParsedReservationEmail,
                )

                if resp.usage:
                    self.stats["input_tokens"] += resp.usage.input_tokens
                    self.stats["output_tokens"] += resp.usage.output_tokens

                if resp.output_parsed:
                    return resp.output_parsed
                return None

            except RateLimitError:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
            except APIError as e:
                print(f"    API error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return None
            except Exception as e:
                print(f"    Parse error: {e}")
                return None
        return None

    def parse_all_emails(self, fetched: list[dict]) -> list[dict]:
        """Parse all fetched emails in parallel."""
        results = []
        total = len(fetched)
        print(f"\n  Parsing {total} emails with GPT-5 mini...")

        def process_one(idx_email):
            idx, email_data = idx_email
            parsed = self.parse_email(email_data)
            # Post-parse fix: detect ReserveCalifornia cancellations GPT may
            # have misclassified as confirmations.
            # "Refund Total" and explicit cancellation signals take priority
            # over [New Reservation] blocks, since cancellations of modified
            # reservations still show [Original]/[New] context.
            if parsed and parsed.is_actual_reservation and parsed.email_type != EmailType.cancellation:
                body = email_data.get("body", "")
                subj = email_data.get("subject", "")
                body_lower = body.lower()
                if parsed.provider in (Provider.reserve_california, Provider.other):
                    # Strong cancellation signals (override [New Reservation])
                    if ("cancellation" in subj.lower()
                            or "refund total" in body_lower
                            or "has been cancelled" in body_lower
                            or "has been canceled" in body_lower
                            or "status: cancelled" in body_lower):
                        parsed.email_type = EmailType.cancellation
                    # Weak signal: negative quantities only (skip if modification)
                    elif "[new reservation]" not in body_lower:
                        has_neg = bool(re.search(r'Quantity:\s*-\d+', body))
                        has_pos = bool(re.search(r'Quantity:\s+\d+', body))
                        if has_neg and not has_pos:
                            parsed.email_type = EmailType.cancellation
            return idx, email_data, parsed

        with ThreadPoolExecutor(max_workers=150) as executor:
            futures = {executor.submit(process_one, (i, e)): i for i, e in enumerate(fetched)}
            done_count = 0

            for future in as_completed(futures):
                done_count += 1
                idx, email_data, parsed = future.result()

                if parsed:
                    self.stats["emails_parsed"] += 1
                    if parsed.is_actual_reservation:
                        self.stats["reservations_found"] += 1
                        results.append({
                            "account": email_data["account"],
                            "message_id": email_data["message_id"],
                            "subject": email_data["subject"],
                            "date": email_data["date"],
                            "parsed": parsed,
                        })
                    else:
                        self.stats["non_reservation"] += 1
                else:
                    self.stats["parse_errors"] += 1

                if done_count % 25 == 0:
                    print(f"    Parsed {done_count}/{total} ({self.stats['reservations_found']} reservations)")

        print(f"    Done: {self.stats['reservations_found']} reservations, "
              f"{self.stats['non_reservation']} non-reservation, "
              f"{self.stats['parse_errors']} errors")
        return results

    # ── Reconcile Phase ───────────────────────────────────────────────

    @staticmethod
    def _normalize_res_number(res_num: str, provider: str) -> str:
        """Normalize reservation numbers for deduplication.
        Recreation.gov: strip -X suffix (0793336345-1 → 0793336345)
        ReserveCalifornia: strip leading # if present
        """
        res_num = res_num.strip()
        if provider == "recreation_gov":
            # Strip -1, -2, etc. suffix
            res_num = re.sub(r'-\d+$', '', res_num)
        elif provider == "reserve_california":
            res_num = res_num.lstrip('#')
        return res_num

    def reconcile_reservations(self, parsed_emails: list[dict]) -> list[dict]:
        """Group emails by reservation number and build canonical trip records.

        Cancellation detection happens at three levels:
        1. GPT parse: explicit cancellation emails classified as email_type=cancellation
        2. Post-parse fix: ReserveCalifornia body-level signals (Refund Total,
           negative quantities, [New Reservation] for modifications vs cancellations)
        3. Reconciliation: Recreation.gov refund-only pattern — last email is a
           "Refund Confirmation" with no subsequent reservation confirmation

        Known limitation — "silent cancellations":
        Some reservations are cancelled via the provider website or phone without
        any cancellation confirmation email being sent. These will appear as
        "completed" with only a booking confirmation email and no reminders.
        The script cannot detect these automatically. Run fix_reservecalifornia_cancellations.py
        with --reaudit to catch ReserveCalifornia cases, and manually review
        reservations with very few emails (1-2) for potential silent cancellations.
        """
        # Group by (normalized_reservation_number, provider)
        groups = {}
        for email_data in parsed_emails:
            p = email_data["parsed"]
            norm_num = self._normalize_res_number(p.reservation_number, p.provider.value)
            key = (norm_num, p.provider.value)
            if key not in groups:
                groups[key] = []
            groups[key].append(email_data)

        print(f"\n  Reconciling {len(groups)} unique reservations from {len(parsed_emails)} emails...")

        trips = []
        for (res_num, provider), emails in groups.items():
            trip = self._build_trip_record(res_num, provider, emails)
            if trip:
                trips.append(trip)

        # Secondary dedup: merge trips with same campground + same dates but different res numbers
        # (happens when GPT extracts a completely different number from reminder vs confirmation)
        trips = self._merge_duplicate_trips(trips)

        # Stats
        for trip in trips:
            if trip["was_cancelled"]:
                self.stats["cancelled"] += 1
            elif trip["status"] == "completed":
                self.stats["completed"] += 1
            else:
                self.stats["confirmed"] += 1
            if trip["was_modified"]:
                self.stats["modified"] += 1

        print(f"    {len(trips)} canonical trips: "
              f"{self.stats['confirmed']} confirmed, "
              f"{self.stats['completed']} completed, "
              f"{self.stats['cancelled']} cancelled, "
              f"{self.stats['modified']} modified")
        return trips

    def _merge_duplicate_trips(self, trips: list[dict]) -> list[dict]:
        """Merge trips with same provider + campground + dates, then use GPT-5 mini for fuzzy matching."""

        def norm_camp(name: str) -> str:
            return re.sub(r'\s+', ' ', (name or '').strip().upper())

        # ── Pass 1: Exact match merge (provider + campground + dates) ─────
        by_key = {}
        for i, t in enumerate(trips):
            key = (t["provider"], norm_camp(t["campground_name"]), t.get("check_in_date"), t.get("check_out_date"))
            if key[2] and key[3]:  # Only merge if we have actual dates
                by_key.setdefault(key, []).append(i)
            else:
                by_key.setdefault(("no_dates", i), []).append(i)

        exact_merged = []
        for key, indices in by_key.items():
            if len(indices) == 1:
                exact_merged.append(trips[indices[0]])
            else:
                best = max(indices, key=lambda i: len(trips[i].get("gmail_message_ids", [])))
                primary = dict(trips[best])
                for idx in indices:
                    if idx == best:
                        continue
                    self._absorb_trip(primary, trips[idx])
                print(f"    Exact-merged {len(indices)} entries for {primary['campground_name']} ({primary['check_in_date']})")
                exact_merged.append(primary)

        if len(exact_merged) < len(trips):
            print(f"    Exact dedup: {len(trips)} → {len(exact_merged)} trips")

        # ── Pass 2: GPT-5 mini fuzzy match (same provider, overlapping/nearby dates, different name) ──
        if not self.openai:
            return exact_merged

        # Find candidate pairs: same provider, dates within 7 days, different campground name
        candidates = []
        for i in range(len(exact_merged)):
            for j in range(i + 1, len(exact_merged)):
                a, b = exact_merged[i], exact_merged[j]
                if a["provider"] != b["provider"]:
                    continue
                if norm_camp(a["campground_name"]) == norm_camp(b["campground_name"]):
                    continue  # Already handled by exact match
                if not a.get("check_in_date") or not b.get("check_in_date"):
                    continue

                try:
                    a_in = date.fromisoformat(a["check_in_date"])
                    b_in = date.fromisoformat(b["check_in_date"])
                    # Dates must overlap or be within 3 days
                    a_out = date.fromisoformat(a["check_out_date"]) if a.get("check_out_date") else a_in + timedelta(days=1)
                    b_out = date.fromisoformat(b["check_out_date"]) if b.get("check_out_date") else b_in + timedelta(days=1)
                    # Check overlap or proximity
                    dates_overlap = a_in <= b_out and b_in <= a_out
                    dates_close = abs((a_in - b_in).days) <= 3
                    if dates_overlap or dates_close:
                        candidates.append((i, j))
                except (ValueError, TypeError):
                    continue

        if not candidates:
            return exact_merged

        print(f"    Fuzzy dedup: checking {len(candidates)} candidate pairs with GPT-5 mini...")

        # Batch GPT-5 mini calls for all candidate pairs
        merge_pairs = []  # (i, j) pairs confirmed as duplicates

        def check_pair(pair):
            i, j = pair
            a, b = exact_merged[i], exact_merged[j]
            prompt = f"""Are these two camping reservation entries the same trip? They have the same booking provider but different names.

Entry A:
- Campground: {a['campground_name']}
- Park: {a.get('park_system', '')}
- Site: {a.get('site_number', '')}
- Check-in: {a['check_in_date']}
- Check-out: {a.get('check_out_date', '')}
- Reservation #: {a['reservation_number']}
- Status: {a['status']}

Entry B:
- Campground: {b['campground_name']}
- Park: {b.get('park_system', '')}
- Site: {b.get('site_number', '')}
- Check-in: {b['check_in_date']}
- Check-out: {b.get('check_out_date', '')}
- Reservation #: {b['reservation_number']}
- Status: {b['status']}

Common reasons for different names: abbreviation (GERL vs GERLE CREEK), truncation, different emphasis (site name vs campground name vs park name)."""

            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions="You are a camping reservation deduplication expert. Determine if two entries refer to the same camping trip. Return structured JSON.",
                    input=prompt,
                    text_format=DuplicateMatch,
                )
                if resp.usage:
                    self.stats["input_tokens"] += resp.usage.input_tokens
                    self.stats["output_tokens"] += resp.usage.output_tokens
                if resp.output_parsed:
                    return pair, resp.output_parsed
            except Exception as e:
                print(f"      Fuzzy match error: {e}")
            return pair, None

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(check_pair, pair) for pair in candidates]
            for future in as_completed(futures):
                pair, result = future.result()
                if result and result.is_same_trip and result.confidence in ("high", "medium"):
                    merge_pairs.append((pair, result))
                    print(f"      MATCH: '{exact_merged[pair[0]]['campground_name']}' == "
                          f"'{exact_merged[pair[1]]['campground_name']}' ({result.confidence}: {result.reasoning})")

        if not merge_pairs:
            return exact_merged

        # Merge confirmed duplicates
        absorbed = set()
        for (i, j), match in merge_pairs:
            if i in absorbed or j in absorbed:
                continue
            # Keep the trip with more email evidence
            a, b = exact_merged[i], exact_merged[j]
            if len(b.get("gmail_message_ids", [])) > len(a.get("gmail_message_ids", [])):
                i, j = j, i  # swap so i is primary
            primary = exact_merged[i]
            self._absorb_trip(primary, exact_merged[j])
            # Use GPT's preferred values if provided
            if match.preferred_campground_name:
                primary["campground_name"] = match.preferred_campground_name
            if match.preferred_check_in:
                primary["check_in_date"] = match.preferred_check_in
            if match.preferred_check_out:
                primary["check_out_date"] = match.preferred_check_out
                # Recalculate derived fields
                try:
                    ci = date.fromisoformat(primary["check_in_date"])
                    co = date.fromisoformat(primary["check_out_date"])
                    primary["num_nights"] = (co - ci).days
                    primary["day_of_week_checkin"] = ci.strftime("%A")
                    primary["day_of_week_checkout"] = co.strftime("%A")
                except (ValueError, TypeError):
                    pass
            absorbed.add(j)

        result = [t for i, t in enumerate(exact_merged) if i not in absorbed]
        print(f"    Fuzzy dedup: {len(exact_merged)} → {len(result)} trips ({len(absorbed)} merged)")
        return result

    @staticmethod
    def _absorb_trip(primary: dict, other: dict):
        """Absorb another trip's data into the primary trip record."""
        primary["gmail_message_ids"] = list(set(
            primary.get("gmail_message_ids", []) + other.get("gmail_message_ids", [])
        ))
        primary["email_subjects"] = list(set(
            primary.get("email_subjects", []) + other.get("email_subjects", [])
        ))
        if primary.get("raw_parsed") and other.get("raw_parsed"):
            primary["raw_parsed"] = primary["raw_parsed"] + other["raw_parsed"]
        for field in ["total_cost", "num_occupants", "equipment", "num_vehicles", "site_number", "park_system"]:
            if not primary.get(field) and other.get(field):
                primary[field] = other[field]

    def _build_trip_record(self, res_num: str, provider: str, emails: list[dict]) -> Optional[dict]:
        """Build a single canonical trip record from a group of emails."""
        # Sort by email date
        def email_sort_key(e):
            try:
                return email.utils.parsedate_to_datetime(e["date"])
            except Exception:
                return datetime.min.replace(tzinfo=timezone.utc)
        emails.sort(key=email_sort_key)

        # Find the most authoritative email for each type
        confirmations = [e for e in emails if e["parsed"].email_type in (EmailType.confirmation, EmailType.receipt)]
        cancellations = [e for e in emails if e["parsed"].email_type == EmailType.cancellation]
        modifications = [e for e in emails if e["parsed"].email_type == EmailType.modification]
        reminders = [e for e in emails if e["parsed"].email_type == EmailType.reminder]

        # Use the latest confirmation/modification for canonical data
        # Priority: modification > latest confirmation > latest reminder
        canonical = None
        if modifications:
            canonical = modifications[-1]
        elif confirmations:
            canonical = confirmations[-1]
        elif reminders:
            canonical = reminders[-1]
        else:
            # Fallback: use any email with dates
            for e in emails:
                if e["parsed"].check_in_date:
                    canonical = e
                    break

        if not canonical:
            return None

        p = canonical["parsed"]

        # ── Date consensus validation ─────────────────────────────────
        # If multiple emails have dates and they disagree, use GPT-5 mini to resolve
        if len(emails) > 1 and self.openai:
            dates_from_emails = []
            for e in emails:
                ep = e["parsed"]
                if ep.check_in_date:
                    dates_from_emails.append({
                        "email_type": ep.email_type.value,
                        "check_in": ep.check_in_date,
                        "check_out": ep.check_out_date,
                        "subject": e["subject"],
                        "date": e["date"],
                    })
            # Check if there's disagreement
            unique_checkins = set(d["check_in"] for d in dates_from_emails if d["check_in"])
            unique_checkouts = set(d["check_out"] for d in dates_from_emails if d["check_out"])
            has_conflict = len(unique_checkins) > 1 or len(unique_checkouts) > 1
            # Also check if canonical has no dates but others do
            if has_conflict and not (cancellations and not modifications):
                # Don't resolve for simple cancellations — they confirm original dates
                try:
                    prompt = f"""Multiple emails for reservation {res_num} ({provider}) have conflicting dates.
Here are the dates from each email (sorted chronologically):

{json.dumps(dates_from_emails, indent=2)}

Rules:
- CRITICAL: Later confirmation emails ALWAYS supersede earlier ones for the same reservation. The most recent confirmation has the correct final dates.
- Recreation.gov modifications appear as a new Reservation Confirmation + Refund Confirmation at the same time. The new confirmation has the updated (shortened) dates. The refund is for the removed nights.
- Modification emails supersede confirmations (they show the NEW dates after a date change)
- Reminders confirm existing bookings — their dates should match the latest confirmation/modification
- If a confirmation and reminder disagree, the reminder is often more accurate (closer to trip date)
- Cancellation emails show the originally-booked dates

What are the correct FINAL check-in and check-out dates for this reservation?"""
                    resp = self.openai.responses.parse(
                        model=self.MODEL,
                        instructions="You resolve conflicting camping reservation dates. Return the correct final dates.",
                        input=prompt,
                        text_format=DateConsensus,
                    )
                    if resp.usage:
                        self.stats["input_tokens"] += resp.usage.input_tokens
                        self.stats["output_tokens"] += resp.usage.output_tokens
                    if resp.output_parsed:
                        consensus = resp.output_parsed
                        # Override canonical dates with consensus
                        p = p.model_copy(update={
                            "check_in_date": consensus.correct_check_in,
                            "check_out_date": consensus.correct_check_out,
                        })
                        print(f"    Date consensus for {res_num}: {consensus.correct_check_in} → {consensus.correct_check_out} ({consensus.reasoning})")
                except Exception as e:
                    print(f"    Date consensus error for {res_num}: {e}")

        # If the canonical email has no dates, try to fill from any other email that does
        if not p.check_in_date:
            for e in emails:
                if e["parsed"].check_in_date:
                    # Borrow dates from this email
                    p = p.model_copy(update={
                        "check_in_date": e["parsed"].check_in_date,
                        "check_out_date": e["parsed"].check_out_date,
                        "num_nights": e["parsed"].num_nights or p.num_nights,
                    })
                    # Also fill campground if missing
                    if not p.campground_name and e["parsed"].campground_name:
                        p = p.model_copy(update={"campground_name": e["parsed"].campground_name})
                    if not p.park_system and e["parsed"].park_system:
                        p = p.model_copy(update={"park_system": e["parsed"].park_system})
                    if not p.site_number and e["parsed"].site_number:
                        p = p.model_copy(update={"site_number": e["parsed"].site_number})
                    break

        # Determine original dates (from first confirmation or from modification's original fields)
        original_check_in = None
        original_check_out = None
        was_modified = bool(modifications)

        if was_modified:
            # Get original dates from the first confirmation or from modification email
            mod = modifications[0]["parsed"]
            if mod.original_check_in:
                original_check_in = mod.original_check_in
                original_check_out = mod.original_check_out
            elif confirmations:
                first_conf = confirmations[0]["parsed"]
                if first_conf.check_in_date != p.check_in_date:
                    original_check_in = first_conf.check_in_date
                    original_check_out = first_conf.check_out_date

        # Build modification history
        mod_history = []
        if was_modified:
            for mod_email in modifications:
                mp = mod_email["parsed"]
                mod_history.append({
                    "date": mod_email["date"],
                    "from_check_in": mp.original_check_in or "",
                    "from_check_out": mp.original_check_out or "",
                    "to_check_in": mp.check_in_date,
                    "to_check_out": mp.check_out_date,
                    "description": mp.modification_description,
                })

        # Status
        was_cancelled = bool(cancellations)

        # Recreation.gov refund-only cancellation detection:
        # If the chronologically LAST email is a "Refund Confirmation" with no
        # subsequent reservation confirmation, the trip was likely cancelled.
        # Pattern: book → reminder → reminder → refund (no confirmation after)
        # or: book → reminder → modify+refund → refund (no confirmation after 2nd refund)
        #
        # IMPORTANT: Only treat as cancellation if the refund came BEFORE check-in.
        # Mid-trip refunds (after check-in) are usually early departures, not cancellations.
        if not was_cancelled and provider == "recreation_gov":
            sorted_emails = sorted(emails, key=email_sort_key)
            last_email = sorted_emails[-1]
            if "refund" in last_email["subject"].lower():
                refund_time = email_sort_key(last_email)
                has_later_confirmation = any(
                    email_sort_key(e) > refund_time and
                    e["parsed"].email_type in (EmailType.confirmation, EmailType.modification)
                    for e in sorted_emails
                )
                if not has_later_confirmation:
                    # Check timing: only cancel if refund came before check-in date
                    # Mid-trip refunds are likely early departures, not cancellations
                    check_in_dt = None
                    try:
                        check_in_dt = date.fromisoformat(p.check_in_date)
                    except (ValueError, TypeError):
                        pass
                    refund_date = refund_time.date() if refund_time else None
                    is_pre_trip = (not check_in_dt or not refund_date
                                  or refund_date < check_in_dt)
                    if is_pre_trip:
                        was_cancelled = True
                        # Treat last refund email as a pseudo-cancellation for metadata
                        cancellations = [last_email]

        today = date.today()
        check_out = None
        try:
            check_out = date.fromisoformat(p.check_out_date)
        except (ValueError, TypeError):
            pass

        if was_cancelled:
            status = "cancelled"
        elif check_out and check_out < today:
            status = "completed"
        else:
            status = "confirmed"

        # Cancellation details
        cancellation_fee = None
        refund_amount = None
        cancellation_date = None
        if cancellations:
            cp = cancellations[-1]["parsed"]
            cancellation_fee = cp.cancellation_fee
            refund_amount = cp.refund_amount
            try:
                cancellation_date = email.utils.parsedate_to_datetime(cancellations[-1]["date"]).strftime("%Y-%m-%d")
            except Exception:
                pass

        # Financial — get total_cost from the most relevant source
        # For modified reservations, prefer the latest modification/confirmation cost
        total_cost = None
        if modifications:
            # Use cost from latest modification if available
            for mod_email in reversed(modifications):
                if mod_email["parsed"].total_cost:
                    total_cost = mod_email["parsed"].total_cost
                    break
        if not total_cost:
            total_cost = p.total_cost
        if not total_cost and confirmations:
            # For unmodified reservations, use latest confirmation cost
            for conf in reversed(confirmations):
                if conf["parsed"].total_cost:
                    total_cost = conf["parsed"].total_cost
                    break
        if not total_cost and cancellations:
            total_cost = cancellations[-1]["parsed"].total_cost

        # Weekend / Sunday analysis
        check_in_date = None
        check_out_date_obj = None
        includes_sunday = False
        sunday_dates = []
        is_weekend = False
        day_checkin = ""
        day_checkout = ""

        try:
            check_in_date = date.fromisoformat(p.check_in_date)
            check_out_date_obj = date.fromisoformat(p.check_out_date)

            day_checkin = check_in_date.strftime("%A")
            day_checkout = check_out_date_obj.strftime("%A")

            # Nights stayed = each night from check_in to check_out-1
            d = check_in_date
            while d < check_out_date_obj:
                if d.weekday() == 6:  # Sunday
                    includes_sunday = True
                    sunday_dates.append(d.isoformat())
                if d.weekday() in (4, 5):  # Friday or Saturday
                    is_weekend = True
                d += timedelta(days=1)
        except (ValueError, TypeError):
            pass

        # ── Campground name selection ─────────────────────────────────
        # If multiple emails have different campground names, use GPT-5 mini to pick the best one
        # Also catches truncated names like "D (STANDARD NONELECTRIC)" when another email has "PINECREST"
        all_camp_names = list(set(
            e["parsed"].campground_name for e in emails
            if e["parsed"].campground_name
        ))
        if not p.campground_name and all_camp_names:
            p = p.model_copy(update={"campground_name": all_camp_names[0]})
        if len(all_camp_names) > 1 and self.openai:
            try:
                resp = self.openai.responses.parse(
                    model=self.MODEL,
                    instructions="Pick the best campground name from these options. Choose the most specific, human-readable name. Avoid loop/area/section names, suffixes like '(STANDARD NONELECTRIC)' or 'FS', and prefixes like 'AREA'. Prefer the actual campground name over the site type.",
                    input=f"Options: {json.dumps(all_camp_names)}\nPark system: {p.park_system}\nSite: {p.site_number}",
                    text_format=BestCampgroundName,
                )
                if resp.usage:
                    self.stats["input_tokens"] += resp.usage.input_tokens
                    self.stats["output_tokens"] += resp.usage.output_tokens
                if resp.output_parsed and resp.output_parsed.best_name:
                    if resp.output_parsed.best_name != p.campground_name:
                        print(f"    Name fix for {res_num}: '{p.campground_name}' → '{resp.output_parsed.best_name}'")
                    p = p.model_copy(update={"campground_name": resp.output_parsed.best_name})
            except Exception as e:
                print(f"    Name selection error for {res_num}: {e}")

        # ── Infer missing check_out from num_nights ──────────────────
        if p.check_in_date and not p.check_out_date:
            if p.num_nights and p.num_nights > 0:
                try:
                    ci = date.fromisoformat(p.check_in_date)
                    inferred_co = ci + timedelta(days=p.num_nights)
                    p = p.model_copy(update={"check_out_date": inferred_co.isoformat()})
                    print(f"    Inferred check_out for {res_num}: {p.check_in_date} + {p.num_nights} nights → {inferred_co}")
                except (ValueError, TypeError):
                    pass

        # If we still have no dates, use the email date as a proxy year reference
        # Store the earliest email date so we at least know the approximate timeframe
        earliest_email_date = None
        for e in emails:
            try:
                edt = email.utils.parsedate_to_datetime(e["date"])
                if earliest_email_date is None or edt < earliest_email_date:
                    earliest_email_date = edt
            except Exception:
                pass

        # Collect all message IDs and subjects
        all_msg_ids = [e["message_id"] for e in emails]
        all_subjects = list(set(e["subject"] for e in emails))

        # Account — use the account from the canonical email
        account = canonical["account"]

        # Num nights
        num_nights = p.num_nights
        if not num_nights and check_in_date and check_out_date_obj:
            num_nights = (check_out_date_obj - check_in_date).days

        original_num_nights = None
        if original_check_in and original_check_out:
            try:
                oci = date.fromisoformat(original_check_in)
                oco = date.fromisoformat(original_check_out)
                original_num_nights = (oco - oci).days
            except (ValueError, TypeError):
                pass

        # ── Fix: check_in == check_out when num_nights > 0 ───────────
        # Some providers (e.g. ReserveCalifornia cabins) report same-day dates for 1-night stays
        if check_in_date and check_out_date_obj and check_in_date == check_out_date_obj:
            if num_nights and num_nights > 0:
                check_out_date_obj = check_in_date + timedelta(days=num_nights)
                p = p.model_copy(update={"check_out_date": check_out_date_obj.isoformat()})
                day_checkout = check_out_date_obj.strftime("%A")
                print(f"    Fixed check_out for {res_num}: {check_in_date} + {num_nights} nights → {check_out_date_obj}")
            else:
                # Assume 1 night if no num_nights info
                check_out_date_obj = check_in_date + timedelta(days=1)
                p = p.model_copy(update={"check_out_date": check_out_date_obj.isoformat()})
                num_nights = 1
                day_checkout = check_out_date_obj.strftime("%A")
                print(f"    Fixed check_out for {res_num}: same-day → assumed 1 night")

        # ── Guard: skip empty/garbage entries ─────────────────────────
        if not p.campground_name and not p.check_in_date:
            print(f"    Skipping empty entry: res={res_num}, provider={provider}")
            return None

        # ── Fix: refresh status for past confirmed trips ──────────────
        if status == "confirmed" and check_out_date_obj and check_out_date_obj < today:
            status = "completed"

        return {
            "reservation_number": res_num,
            "provider": provider,
            "confirmation_number": p.reservation_number if provider == "reserve_california" else None,
            "campground_name": p.campground_name,
            "park_system": p.park_system,
            "site_number": p.site_number,
            "check_in_date": p.check_in_date or None,
            "check_out_date": p.check_out_date or None,
            "num_nights": num_nights,
            "original_check_in": original_check_in,
            "original_check_out": original_check_out,
            "original_num_nights": original_num_nights,
            "primary_occupant": p.primary_occupant,
            "num_occupants": p.num_occupants,
            "equipment": p.equipment,
            "num_vehicles": p.num_vehicles,
            "total_cost": total_cost,
            "cancellation_fee": cancellation_fee if was_cancelled else None,
            "refund_amount": refund_amount if was_cancelled else None,
            "status": status,
            "was_modified": was_modified,
            "was_cancelled": was_cancelled,
            "cancellation_date": cancellation_date,
            "includes_sunday_night": includes_sunday,
            "sunday_night_dates": sunday_dates if sunday_dates else None,
            "is_weekend_trip": is_weekend,
            "day_of_week_checkin": day_checkin,
            "day_of_week_checkout": day_checkout,
            "account_email": account,
            "gmail_message_ids": all_msg_ids,
            "email_subjects": all_subjects,
            "modification_history": mod_history if mod_history else None,
            "booking_email_date": earliest_email_date.isoformat() if earliest_email_date else None,
            "raw_parsed": [
                {
                    "message_id": e["message_id"],
                    "subject": e["subject"],
                    "date": e["date"],
                    "parsed": e["parsed"].model_dump(),
                }
                for e in emails
            ],
        }

    # ── Save Phase ────────────────────────────────────────────────────

    def save_to_supabase(self, trips: list[dict]):
        """Upsert all trip records to Supabase."""
        print(f"\n  Saving {len(trips)} trips to Supabase...")
        saved = 0
        errors = 0

        for trip in trips:
            try:
                # Clean data for Supabase
                row = {k: v for k, v in trip.items()}

                # Convert raw_parsed to clean JSON
                if row.get("raw_parsed"):
                    row["raw_parsed"] = json.loads(json.dumps(row["raw_parsed"], default=str))
                if row.get("modification_history"):
                    row["modification_history"] = json.loads(json.dumps(row["modification_history"], default=str))

                # Strip null bytes from all string fields
                for k, v in row.items():
                    if isinstance(v, str):
                        row[k] = v.replace("\x00", "")

                self.supabase.table("camping_reservations").upsert(
                    row,
                    on_conflict="reservation_number,provider",
                ).execute()
                saved += 1

            except Exception as e:
                errors += 1
                print(f"    Save error for {trip['reservation_number']}: {e}")

        self.stats["reservations_saved"] = saved
        print(f"    Saved: {saved}, Errors: {errors}")

    # ── Main Run ──────────────────────────────────────────────────────

    def run(self):
        print("=" * 60)
        print("CAMPING RESERVATION AUDIT")
        print("=" * 60)

        self.connect()

        # 1. Search
        print("\n[1/4] SEARCHING for reservation emails...")
        messages = self.search_all_accounts()

        if self.search_only:
            print("\n  --search-only mode, stopping here")
            self._print_stats()
            return

        if self.test_mode:
            messages = messages[:self.test_count]
            print(f"\n  --test mode: limited to {len(messages)} messages")

        # 2. Fetch
        print(f"\n[2/4] FETCHING {len(messages)} message bodies...")
        fetched = self.fetch_messages(messages)

        if self.dry_run:
            print("\n  --dry-run mode, stopping before parse")
            self._print_stats()
            return

        # 3. Parse
        print(f"\n[3/4] PARSING emails with GPT-5 mini...")
        parsed = self.parse_all_emails(fetched)

        # 4. Reconcile & Save
        print(f"\n[4/4] RECONCILING and SAVING...")
        trips = self.reconcile_reservations(parsed)

        if trips:
            self.save_to_supabase(trips)

        self._print_stats()

        # Print summary table
        self._print_summary(trips)

    def _print_stats(self):
        print("\n" + "=" * 60)
        print("STATS")
        print("=" * 60)
        for k, v in self.stats.items():
            print(f"  {k}: {v}")
        if self.stats["input_tokens"]:
            cost = (self.stats["input_tokens"] * 0.15 + self.stats["output_tokens"] * 0.60) / 1_000_000
            print(f"  estimated_cost: ${cost:.3f}")

    def _print_summary(self, trips: list[dict]):
        if not trips:
            return

        print("\n" + "=" * 60)
        print("RESERVATION SUMMARY")
        print("=" * 60)

        # Sort by check-in date, using booking_email_date as fallback
        def sort_key(t):
            try:
                return date.fromisoformat(t["check_in_date"])
            except (ValueError, TypeError):
                # Use email date as proxy for sorting
                if t.get("booking_email_date"):
                    try:
                        return datetime.fromisoformat(t["booking_email_date"]).date()
                    except (ValueError, TypeError):
                        pass
                return date.max
        trips.sort(key=sort_key)

        print(f"\n{'Date Range':<25} {'Campground':<30} {'Nights':>6} {'Status':<12} {'Sun?':>4} {'Mod?':>4} {'Account'}")
        print("-" * 120)
        for t in trips:
            if t['check_in_date']:
                dates = f"{t['check_in_date']} → {t['check_out_date'] or '?'}"
            elif t.get('booking_email_date'):
                # Show email date as proxy with ~ prefix
                try:
                    edate = datetime.fromisoformat(t['booking_email_date']).strftime('%Y-%m')
                except (ValueError, TypeError):
                    edate = '?'
                dates = f"~{edate} (email date)"
            else:
                dates = "? → ?"
            campground = (t['campground_name'] or '?')[:28]
            nights = str(t['num_nights'] or '?')
            status = t['status']
            sun = "Y" if t['includes_sunday_night'] else ""
            mod = "Y" if t['was_modified'] else ""
            acct = t['account_email'].split('@')[0]
            print(f"{dates:<25} {campground:<30} {nights:>6} {status:<12} {sun:>4} {mod:>4} {acct}")


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Audit all camping reservations from Gmail")
    parser.add_argument("--test", action="store_true", help="Process first N emails only")
    parser.add_argument("-n", type=int, default=10, help="Number of emails in test mode")
    parser.add_argument("--search-only", action="store_true", help="Only search, don't fetch/parse")
    parser.add_argument("--dry-run", action="store_true", help="Search and fetch, don't parse")
    parser.add_argument("--provider", type=str, help="Only process one provider (e.g. recreation_gov)")
    args = parser.parse_args()

    auditor = CampingAuditor(
        test_mode=args.test,
        test_count=args.n,
        search_only=args.search_only,
        dry_run=args.dry_run,
        provider_filter=args.provider,
    )
    auditor.run()


if __name__ == "__main__":
    main()
