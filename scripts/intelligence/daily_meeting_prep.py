#!/usr/bin/env python3
"""
Daily Meeting Prep — Automated Meeting Memo Generator

Sweeps all Google calendars, identifies external one-off meetings, researches
attendees (contacts DB + Perplexity web search), generates prep memos using
Claude Sonnet 4.6, creates a Google Doc, and attaches it to each calendar event.

Usage:
  python scripts/intelligence/daily_meeting_prep.py                    # Today
  python scripts/intelligence/daily_meeting_prep.py --dry-run          # Preview only
  python scripts/intelligence/daily_meeting_prep.py --date 2026-03-04  # Specific date
  python scripts/intelligence/daily_meeting_prep.py --days-ahead 1     # Tomorrow
  python scripts/intelligence/daily_meeting_prep.py --no-gdoc          # Skip Google Doc

See docs/MEETING_PREP_SYSTEM.md for full documentation.
"""

import argparse
import json
import os
import re
import time
import traceback
from datetime import date, datetime, time as datetime_time, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import psycopg2
import requests
import anthropic
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "meeting_prep_config.json")
CREDENTIALS_DIR = os.path.expanduser("~/.google_workspace_mcp/credentials")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "docs", "meeting_memos")
DEFAULT_TIMEZONE = "America/Los_Angeles"

# ── Config ────────────────────────────────────────────────────────────────────

GOOGLE_ACCOUNTS = [
    {"email": "justinrsteele@gmail.com", "label": "Personal Gmail"},
    {"email": "justin@truesteele.com", "label": "True Steele"},
    {"email": "justin@kindora.co", "label": "Kindora"},
    {"email": "justin@outdoorithm.com", "label": "Outdoorithm"},
    {"email": "justin@outdoorithmcollective.org", "label": "Outdoorithm Collective"},
]

ACCOUNT_LABELS = {a["email"]: a["label"] for a in GOOGLE_ACCOUNTS}

JUSTIN_EMAILS = {a["email"] for a in GOOGLE_ACCOUNTS}
JUSTIN_EMAILS.update({"justin.steele@gmail.com", "justinrichardsteele@gmail.com"})

ENTITY_MAP = {
    "justin@kindora.co": "kindora",
    "justin@outdoorithm.com": "outdoorithm",
    "justin@outdoorithmcollective.org": "outdoorithm",
    "justin@truesteele.com": "truesteele",
    "justinrsteele@gmail.com": "truesteele",
}

ORG_CONTEXT = {
    "kindora": {
        "entity": "Kindora",
        "focus": "New users, distribution, marketing, sales, funding partnerships",
        "pitch": ("AI-powered fundraising intelligence for nonprofits. Grant discovery, "
                  "AI-assisted grant writing, pipeline management, funder intelligence."),
    },
    "outdoorithm": {
        "entity": "Outdoorithm / Outdoorithm Collective",
        "focus": "Fundraising, partnerships, program expansion, donor cultivation",
        "pitch": ("Getting every family outside. AI-powered camping platform + nonprofit "
                  "providing outdoor access for urban families."),
    },
    "truesteele": {
        "entity": "True Steele Labs",
        "focus": "Client acquisition for AI product studio builds",
        "pitch": ("Founder-led AI product studio. Fixed-fee, time-boxed builds for "
                  "mission-driven orgs. $18K-$250K+ depending on scope."),
    },
}

JUSTIN_BIO = """Justin Steele is a tech founder and consultant based in Oakland, CA.
He's the CEO & Co-Founder of Kindora (AI-powered fundraising intelligence for nonprofits),
Co-Founder of Outdoorithm (AI camping platform) and Outdoorithm Collective (nonprofit for
outdoor access for urban families), and founder of True Steele Labs (AI product studio for
social impact). Previously, he led Google.org's philanthropy across the Americas for nearly
a decade, directing $700M+ in strategic investments. He holds a BS in Chemical Engineering
from UVA, an MBA from Harvard Business School, and an MPA from Harvard Kennedy School.
He sits on the San Francisco Foundation board."""

JUSTIN_SCHOOLS = ["University of Virginia", "Harvard Business School", "Harvard Kennedy School"]
JUSTIN_COMPANIES = ["Bain & Company", "The Bridgespan Group", "Year Up", "Google", "Google.org"]

DEFAULT_CONFIG = {
    "excluded_domains": ["flourishfund.org"],
    "excluded_emails": [],
    "internal_emails": [
        "sally@outdoorithmcollective.org",
        "sally.steele@gmail.com",
        "karibu@kindora.co",
    ],
    "skip_recurring": True,
    "skip_declined": True,
    "skip_all_day": True,
    "skip_cancelled": True,
    "skip_keywords": ["wellness session", "group workshop"],
    "add_unknown_contacts": True,
    "contact_pool_for_new": "meeting",
    "google_doc_folder_name": "Meeting Prep Memos",
    "google_doc_account": "justin@truesteele.com",
    "attach_to_calendar": True,
    "reuse_daily_google_doc": True,
    "perplexity_model": "sonar-pro",
    "memo_model": "claude-sonnet-4-6",
    "timezone": DEFAULT_TIMEZONE,
}


def normalize_string_list(values: object) -> List[str]:
    """Normalize a user-provided list of strings to lowercase, stripped strings."""
    if not isinstance(values, list):
        return []
    return [str(v).strip().lower() for v in values if str(v).strip()]


def get_local_timezone(config: Dict) -> ZoneInfo:
    """Return configured timezone with safe fallback."""
    tz_name = str(config.get("timezone") or DEFAULT_TIMEZONE).strip()
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        print(f"[WARN] Invalid timezone '{tz_name}'. Falling back to {DEFAULT_TIMEZONE}.")
        return ZoneInfo(DEFAULT_TIMEZONE)


def parse_event_datetime(event: Dict, tz: ZoneInfo) -> Optional[datetime]:
    """Parse calendar event start datetime into the configured timezone."""
    start = event.get("start", {})
    date_time = start.get("dateTime")
    if not date_time:
        return None
    # Calendar API returns ISO 8601; convert trailing Z for fromisoformat compatibility.
    try:
        parsed = datetime.fromisoformat(date_time.replace("Z", "+00:00"))
        return parsed.astimezone(tz)
    except ValueError:
        print(f"[WARN] Could not parse event datetime '{date_time}'")
        return None


def format_event_time(event: Dict, tz: ZoneInfo) -> str:
    """Format event start time for schedule displays."""
    dt = parse_event_datetime(event, tz)
    if dt:
        return dt.strftime("%H:%M")
    if "date" in event.get("start", {}):
        return "all-day"
    return ""


def clean_cell(text: object) -> str:
    """Sanitize markdown table cell content."""
    val = str(text or "")
    val = val.replace("|", "\\|")
    val = re.sub(r"[\r\n]+", " ", val)
    return val.strip()


def load_config() -> Dict:
    """Load config from meeting_prep_config.json."""
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                config.update(loaded)
            else:
                print(f"[WARN] Ignoring invalid config format in {CONFIG_PATH}; expected object.")
        except Exception as e:
            print(f"[WARN] Failed to read {CONFIG_PATH}: {e}. Using defaults.")

    # Normalize list-like fields to avoid case/whitespace mismatches.
    for key in ("excluded_domains", "excluded_emails", "internal_emails", "skip_keywords"):
        config[key] = normalize_string_list(config.get(key))

    return config


# ── Google Calendar ───────────────────────────────────────────────────────────

def load_credentials(account_email: str) -> Optional[Credentials]:
    """Load OAuth credentials for a Google account."""
    cred_path = os.path.join(CREDENTIALS_DIR, account_email + ".json")
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


def build_service(account_email: str, api: str = "calendar", version: str = "v3"):
    """Build a Google API service client."""
    creds = load_credentials(account_email)
    if not creds:
        return None
    return build(api, version, credentials=creds, cache_discovery=False)


def fetch_events(target_date: date, config: Dict) -> List[Dict]:
    """Fetch calendar events for a given date across all accounts."""
    all_events = []
    local_tz = get_local_timezone(config)
    day_start = datetime.combine(target_date, datetime_time.min, tzinfo=local_tz)
    day_end = datetime.combine(target_date, datetime_time.max.replace(microsecond=0), tzinfo=local_tz)
    time_min = day_start.isoformat()
    time_max = day_end.isoformat()

    for account in GOOGLE_ACCOUNTS:
        email = account["email"]
        service = build_service(email)
        if not service:
            print(f"  [SKIP] No credentials for {email}")
            continue
        try:
            result = service.events().list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                timeZone=local_tz.key,
            ).execute()
            items = result.get("items", [])
            for ev in items:
                ev["_account_email"] = email
                ev["_account_label"] = account["label"]
            all_events.extend(items)
            print(f"  [{account['label']}] {len(items)} events")
        except Exception as e:
            print(f"  [ERROR] {email}: {e}")

    all_events.sort(key=lambda e: parse_event_datetime(e, local_tz) or datetime.max.replace(tzinfo=local_tz))
    return all_events


# ── Filtering ─────────────────────────────────────────────────────────────────

def get_attendee_emails(event: Dict) -> List[str]:
    """Extract attendee email addresses from a calendar event."""
    return [a.get("email", "").lower() for a in event.get("attendees", []) if a.get("email")]


def get_external_attendees(event: Dict, config: Dict) -> List[Dict]:
    """Get external attendees (not Justin, not internal, not excluded)."""
    internal = set(e.lower() for e in config.get("internal_emails", []))
    excluded_emails = set(e.lower() for e in config.get("excluded_emails", []))
    excluded_domains = set(d.lower() for d in config.get("excluded_domains", []))

    external = []
    for a in event.get("attendees", []):
        email = a.get("email", "").lower()
        if not email:
            continue
        if email in JUSTIN_EMAILS:
            continue
        if email in internal:
            continue
        if email in excluded_emails:
            continue
        domain = email.split("@")[1] if "@" in email else ""
        if domain in excluded_domains:
            continue
        external.append({
            "email": email,
            "display_name": a.get("displayName", ""),
            "response_status": a.get("responseStatus", ""),
            "organizer": a.get("organizer", False),
        })
    return external


def should_skip_event(event: Dict, config: Dict) -> Optional[str]:
    """Check if an event should be skipped. Returns reason string, or None if it should be included."""
    # Cancelled events
    if config.get("skip_cancelled", True) and event.get("status") == "cancelled":
        return "cancelled event"

    # All-day events
    if config.get("skip_all_day", True):
        if "date" in event.get("start", {}) and "dateTime" not in event.get("start", {}):
            return "all-day event"

    # Recurring events
    if config.get("skip_recurring", True):
        if event.get("recurringEventId"):
            return "recurring event"

    # Declined events
    if config.get("skip_declined", True):
        for a in event.get("attendees", []):
            if a.get("email", "").lower() in JUSTIN_EMAILS and a.get("responseStatus") == "declined":
                return "declined"

    # Keyword-based skips for predictable non-prep meeting types
    keywords = config.get("skip_keywords", [])
    if keywords:
        haystack = " ".join(
            [
                str(event.get("summary") or ""),
                str(event.get("description") or ""),
            ]
        ).lower()
        for keyword in keywords:
            if keyword and keyword in haystack:
                return f"keyword skip: {keyword}"

    # No external attendees
    external = get_external_attendees(event, config)
    if not external:
        return "no external attendees"

    return None


def classify_events(events: List[Dict], config: Dict) -> tuple:
    """Classify events into meetings that need memos vs skipped."""
    needs_memo = []
    skipped = []
    for ev in events:
        reason = should_skip_event(ev, config)
        if reason:
            skipped.append((ev, reason))
        else:
            needs_memo.append(ev)
    return needs_memo, skipped


# ── Database ──────────────────────────────────────────────────────────────────

def get_db_connection():
    """Get a PostgreSQL connection to Supabase."""
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not password:
        raise RuntimeError("SUPABASE_DB_PASSWORD is not set.")

    return psycopg2.connect(
        host=os.environ.get("SUPABASE_DB_HOST", "db.ypqsrejrsocebnldicke.supabase.co"),
        port=int(os.environ.get("SUPABASE_DB_PORT", "5432")),
        dbname=os.environ.get("SUPABASE_DB_NAME", "postgres"),
        user=os.environ.get("SUPABASE_DB_USER", "postgres"),
        password=password,
    )


def lookup_contact_by_email(conn, email: str) -> Optional[Dict]:
    """Look up a contact by email."""
    if conn is None:
        return None

    with conn.cursor() as cur:
        cur.execute("""
        SELECT id, first_name, last_name, normalized_full_name, email, email_2,
               linkedin_url, linkedin_username, position, company, headline, summary,
               location_name, city, state,
               enriched_at IS NOT NULL as is_enriched,
               comms_summary::text, ai_tags::text, comms_closeness, comms_momentum,
               comms_last_date, comms_thread_count, comms_meeting_count,
               comms_last_meeting, comms_call_count, comms_last_call,
               contact_pools, taxonomy_classification,
               enrich_current_company, enrich_current_title,
               enrich_schools, enrich_companies_worked, enrich_volunteer_orgs,
               ask_readiness::text
        FROM contacts
        WHERE lower(email) = lower(%s)
           OR lower(email_2) = lower(%s)
           OR lower(personal_email) = lower(%s)
        LIMIT 1
    """, (email, email, email))
        row = cur.fetchone()
        if not row:
            return None
        cols = [desc[0] for desc in cur.description]

    contact = dict(zip(cols, row))
    for field in ("comms_summary", "ai_tags", "ask_readiness"):
        if contact.get(field) and isinstance(contact[field], str):
            try:
                contact[field] = json.loads(contact[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return contact


def lookup_comms_history(conn, contact_id: int) -> Dict:
    """Get recent email and calendar history for a contact."""
    if conn is None:
        return {"emails": [], "meetings": []}

    with conn.cursor() as cur:
        cur.execute("""
        SELECT subject, last_message_date, direction, message_count, account_email
        FROM contact_email_threads
        WHERE contact_id = %s ORDER BY last_message_date DESC LIMIT 5
    """, (contact_id,))
        emails = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]

        cur.execute("""
        SELECT summary, start_time, duration_minutes, attendee_count, location
        FROM contact_calendar_events
        WHERE contact_id = %s ORDER BY start_time DESC LIMIT 5
    """, (contact_id,))
        meetings = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]

    return {"emails": emails, "meetings": meetings}


def add_meeting_contact(conn, first_name: str, last_name: str, email: str,
                        company: str = None, position: str = None,
                        linkedin_url: str = None, pool: str = "meeting") -> int:
    """Insert a new meeting contact and return its ID."""
    if conn is None:
        raise RuntimeError("Database connection unavailable; cannot insert contact.")

    existing = lookup_contact_by_email(conn, email)
    if existing:
        return existing["id"]

    linkedin_username = None
    if linkedin_url:
        m = re.search(r'linkedin\.com/in/([^/]+)', linkedin_url)
        if m:
            linkedin_username = m.group(1).rstrip('/')
    first_name = (first_name or "").strip() or "Unknown"
    last_name = (last_name or "").strip()
    normalized_full_name = " ".join(x for x in [first_name, last_name] if x).strip()
    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO contacts (first_name, last_name, normalized_first_name, normalized_last_name,
                              normalized_full_name, email, linkedin_url, linkedin_username,
                              company, position, contact_pools, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ARRAY[%s], NOW())
        RETURNING id
    """, (first_name, last_name, first_name.lower(), last_name.lower(),
          normalized_full_name, email, linkedin_url, linkedin_username,
          company, position, pool))
        new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def find_shared_background(contact: Dict) -> List[str]:
    """Find shared schools, employers, etc. between Justin and a contact."""
    shared = []
    schools = contact.get("enrich_schools") or []
    companies = contact.get("enrich_companies_worked") or []
    for s in schools:
        for js in JUSTIN_SCHOOLS:
            if js.lower() in s.lower() or s.lower() in js.lower():
                shared.append(f"Both attended {s}")
    for c in companies:
        for jc in JUSTIN_COMPANIES:
            if jc.lower() in c.lower() or c.lower() in jc.lower():
                shared.append(f"Both worked at {c}")
    return shared


# ── Perplexity Research ───────────────────────────────────────────────────────

def research_person(name: str, email: str, company: str = None, model: str = "sonar-pro") -> str:
    """Research a person using Perplexity sonar-pro."""
    api_key = os.environ.get("PERPLEXITY_APIKEY")
    if not api_key:
        return "[Perplexity API key not set]"

    domain = email.split("@")[1] if "@" in email else ""
    query = f"Who is {name}"
    if company:
        query += f" at {company}"
    elif domain not in ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"):
        query += f" at {domain}"
    query += "? LinkedIn profile, career background, education, current role, notable achievements."

    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a research assistant. Provide a concise professional profile in 300-500 words."},
                    {"role": "user", "content": query},
                ],
                "max_tokens": 800,
            },
            timeout=45,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Perplexity research failed: {e}]"


def research_organization(name: str, domain: str = "", model: str = "sonar-pro") -> str:
    """Research an organization using Perplexity sonar-pro."""
    api_key = os.environ.get("PERPLEXITY_APIKEY")
    if not api_key:
        return ""

    query = f"What is {name}?"
    if domain:
        query += f" ({domain})"
    query += " Mission, size, key programs, recent news, notable partnerships. Keep to 300 words."

    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a research assistant. Provide a concise organizational profile in under 300 words."},
                    {"role": "user", "content": query},
                ],
                "max_tokens": 600,
            },
            timeout=45,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Org research failed: {e}]"


def search_meeting_origin(conn, attendee_names: List[str], org_name: str = "",
                          org_domain: str = "") -> str:
    """Search DB + Gmail for context about how a meeting originated.

    Returns a text summary of any intro emails, LinkedIn notifications, or
    prior threads that explain how this meeting came about.
    """
    results = []

    # ── Source A: DB search ──────────────────────────────────────────────────
    if conn is not None:
        search_terms = [n for n in attendee_names if n and len(n) > 2]
        if org_name and len(org_name) > 2:
            search_terms.append(org_name)

        for term in search_terms:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT subject, snippet, summary, last_message_date, account_email
                        FROM contact_email_threads
                        WHERE (subject ILIKE %s OR snippet ILIKE %s)
                        ORDER BY last_message_date DESC
                        LIMIT 3
                    """, (f"%{term}%", f"%{term}%"))
                    for row in cur.fetchall():
                        cols = [d[0] for d in cur.description]
                        r = dict(zip(cols, row))
                        results.append(f"[{str(r.get('last_message_date', ''))[:10]}] "
                                       f"{r.get('account_email', '')}: "
                                       f"{r.get('subject', '')} — {r.get('snippet', '')[:200]}")
            except Exception as e:
                print(f"       [WARN] DB origin search failed for '{term}': {e}")

    # ── Source B: Gmail live search (thread-based) ────────────────────────────
    # Fetch threads, not individual messages. The original intro (first message
    # in a thread) contains the introducer's name — the most valuable context.
    search_queries = []
    for name in attendee_names:
        if name and len(name) > 2:
            search_queries.append(f'"{name}"')
    if org_name and len(org_name) > 2:
        search_queries.append(f'"{org_name}"')

    justin_emails_lower = {e.lower() for e in JUSTIN_EMAILS}
    attendee_emails_lower = {n.lower() for n in attendee_names}

    if search_queries:
        gmail_query = " OR ".join(search_queries)
        seen_threads = set()
        for account in GOOGLE_ACCOUNTS:
            acct_email = account["email"]
            try:
                service = build_service(acct_email, "gmail", "v1")
                if not service:
                    continue
                # Search for matching messages, then get their threads
                resp = service.users().messages().list(
                    userId="me", q=gmail_query, maxResults=5
                ).execute()
                msg_list = resp.get("messages", [])

                # Collect unique thread IDs
                thread_ids = []
                for msg_ref in msg_list:
                    tid = msg_ref.get("threadId", msg_ref["id"])
                    if tid not in seen_threads:
                        seen_threads.add(tid)
                        thread_ids.append(tid)

                # Fetch each thread and extract the first (original) message
                for tid in thread_ids[:3]:
                    try:
                        thread = service.users().threads().get(
                            userId="me", id=tid, format="metadata",
                            metadataHeaders=["Subject", "From", "To", "Date"]
                        ).execute()
                        thread_msgs = thread.get("messages", [])
                        if not thread_msgs:
                            continue

                        # First message = original intro / conversation starter
                        first_msg = thread_msgs[0]
                        first_headers = {h["name"]: h["value"]
                                         for h in first_msg.get("payload", {}).get("headers", [])}
                        first_from = first_headers.get("From", "")
                        first_subject = first_headers.get("Subject", "")
                        first_date = first_headers.get("Date", "")[:16]
                        first_snippet = first_msg.get("snippet", "")[:300]

                        # Most recent message for timeline context
                        last_msg = thread_msgs[-1]
                        last_headers = {h["name"]: h["value"]
                                        for h in last_msg.get("payload", {}).get("headers", [])}
                        last_date = last_headers.get("Date", "")[:16]
                        msg_count = len(thread_msgs)

                        # Build a rich origin entry
                        entry = (f"[Thread: {first_subject}] "
                                 f"Started {first_date} by {first_from} — "
                                 f"{first_snippet} "
                                 f"({msg_count} messages, last: {last_date})")
                        results.append(entry)
                    except Exception as e:
                        print(f"       [WARN] Gmail thread fetch failed for {tid}: {e}")
            except Exception as e:
                print(f"       [WARN] Gmail origin search failed for {acct_email}: {e}")

    if not results:
        return ""

    # Deduplicate by thread subject
    seen = set()
    unique = []
    for r in results:
        # Extract subject from "[Thread: SUBJECT]" prefix
        key = r.split("]")[0].lower() if "]" in r else r[:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return "\n".join(unique[:8])


def guess_name_from_email(email: str, display_name: str = "") -> tuple:
    """Try to extract first/last name from display name or email prefix."""
    import re
    def _clean(s: str) -> str:
        """Strip leading/trailing non-alpha chars (digits, underscores, etc.)."""
        return re.sub(r'^[^a-zA-Z]+|[^a-zA-Z]+$', '', s)

    if display_name and " " in display_name:
        parts = display_name.strip().split()
        return _clean(parts[0]) or parts[0], " ".join(_clean(p) or p for p in parts[1:])
    prefix = email.split("@")[0]
    # Try common patterns: first.last, firstlast, first_last
    for sep in (".", "_", "-"):
        if sep in prefix:
            parts = prefix.split(sep, 1)
            first = _clean(parts[0]).title()
            last = _clean(parts[1]).title()
            if first:
                return first, last
    # Single name prefix — use it as first, domain as last placeholder
    cleaned = _clean(prefix)
    return (cleaned or prefix).title(), ""


# ── Attendee Research Pipeline ────────────────────────────────────────────────

def research_attendees(event: Dict, config: Dict, conn) -> tuple:
    """Research all external attendees for a meeting. Returns (profiles, comms_history, origin_context, org_research)."""
    external = get_external_attendees(event, config)
    profiles = []
    all_comms = {"emails": [], "meetings": []}

    for att in external:
        email = att["email"]
        display_name = att.get("display_name", "")
        print(f"     Researching {email}...")

        contact = lookup_contact_by_email(conn, email)
        profile = {"email": email, "display_name": display_name}

        if contact:
            name = contact["normalized_full_name"] or f"{contact['first_name']} {contact['last_name']}"
            print(f"       Found in DB: {name} (id:{contact['id']})")
            profile.update({
                "name": name,
                "in_db": True,
                "contact_id": contact["id"],
                "position": contact.get("enrich_current_title") or contact.get("position") or "",
                "company": contact.get("enrich_current_company") or contact.get("company") or "",
                "headline": contact.get("headline") or "",
                "location": contact.get("location_name") or contact.get("city") or "",
                "linkedin_url": contact.get("linkedin_url") or "",
                "comms_closeness": contact.get("comms_closeness") or "unknown",
                "comms_momentum": contact.get("comms_momentum") or "unknown",
                "comms_last_date": str(contact.get("comms_last_date") or ""),
                "comms_thread_count": contact.get("comms_thread_count") or 0,
                "comms_meeting_count": contact.get("comms_meeting_count") or 0,
                "taxonomy": contact.get("taxonomy_classification") or "",
            })

            # Comms summary
            cs = contact.get("comms_summary")
            if cs and isinstance(cs, dict):
                profile["comms_chronological"] = cs.get("chronological_summary", "")
                profile["total_messages"] = cs.get("total_messages", 0)

            # AI tags
            tags = contact.get("ai_tags")
            if tags and isinstance(tags, dict):
                tp = tags.get("topical_affinity", {})
                if tp:
                    profile["primary_interests"] = tp.get("primary_interests", [])
                    profile["talking_points_from_tags"] = tp.get("talking_points", [])
                rp = tags.get("relationship_proximity", {})
                if rp:
                    profile["relationship_tier"] = rp.get("tier", "")
                    profile["proximity_signals"] = rp.get("proximity_signals", [])
                sf = tags.get("sales_fit", {})
                if sf:
                    profile["kindora_prospect_type"] = sf.get("prospect_type", "")
                    profile["kindora_pitch_fit"] = sf.get("kindora_pitch_fit", "")

            # Ask readiness
            ar = contact.get("ask_readiness")
            if ar and isinstance(ar, dict):
                ofr = ar.get("outdoorithm_fundraising", {})
                if ofr:
                    profile["ask_readiness_tier"] = ofr.get("tier", "")
                    profile["ask_readiness_score"] = ofr.get("score", 0)

            # Shared background
            shared = find_shared_background(contact)
            if shared:
                profile["shared_background"] = shared

            # Pull comms history
            comms = lookup_comms_history(conn, contact["id"])
            all_comms["emails"].extend(comms["emails"])
            all_comms["meetings"].extend(comms["meetings"])
        else:
            # Not in DB — web research
            first, last = guess_name_from_email(email, display_name)
            name = f"{first} {last}".strip() or email.split("@")[0]
            domain = email.split("@")[1] if "@" in email else ""
            company_guess = None
            if domain not in ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"):
                company_guess = domain.split(".")[0].title()

            print(f"       Not in DB. Web research for '{name}'...")
            research = research_person(
                name=name,
                email=email,
                company=company_guess,
                model=str(config.get("perplexity_model") or "sonar-pro"),
            )
            time.sleep(1.5)  # Perplexity rate limit

            profile.update({
                "name": name,
                "in_db": False,
                "web_research": research,
                "company": company_guess or "",
            })

            # Auto-add as meeting contact
            if config.get("add_unknown_contacts", True) and first and conn is not None:
                pool = config.get("contact_pool_for_new", "meeting")
                try:
                    new_id = add_meeting_contact(conn, first, last, email,
                                                 company=company_guess, pool=pool)
                    print(f"       Added as meeting contact (id:{new_id})")
                    profile["contact_id"] = new_id
                except Exception as e:
                    print(f"       Failed to add contact: {e}")
            elif conn is None:
                print("       [WARN] Database unavailable; skipped auto-adding unknown contact.")

        profiles.append(profile)

    # ── Meeting origin context (DB + Gmail) ──────────────────────────────────
    attendee_names = [p.get("name", "") for p in profiles]
    org_names = list({p.get("company", "") for p in profiles if p.get("company")})
    org_domains = list({att["email"].split("@")[1] for att in external
                        if "@" in att["email"]
                        and att["email"].split("@")[1] not in
                        ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com")})
    primary_org = org_names[0] if org_names else ""

    print(f"     Searching for meeting origin context...")
    origin_context = search_meeting_origin(conn, attendee_names, primary_org)

    # ── Organization research (Perplexity) ───────────────────────────────────
    org_research_results = {}
    perplexity_model = str(config.get("perplexity_model") or "sonar-pro")
    for org in org_names:
        if org and org not in org_research_results:
            domain = org_domains[0] if org_domains else ""
            print(f"     Researching organization: {org}...")
            org_research_results[org] = research_organization(org, domain, perplexity_model)
            time.sleep(1.5)  # Perplexity rate limit

    org_research_text = "\n\n".join(
        f"**{org}:** {text}" for org, text in org_research_results.items() if text
    )

    return profiles, all_comms, origin_context, org_research_text


# ── Memo Generation (Claude Sonnet 4.6) ──────────────────────────────────────

def build_memo_prompt(event: Dict, profiles: List[Dict], comms: Dict, entity_key: str,
                      origin_context: str = "", org_research: str = "") -> str:
    """Build the prompt for Claude Sonnet to generate a meeting memo."""
    entity_ctx = ORG_CONTEXT.get(entity_key, ORG_CONTEXT["truesteele"])

    # Event details
    start = event.get("start", {}).get("dateTime", "")
    end = event.get("end", {}).get("dateTime", "")
    summary = event.get("summary", "Untitled Meeting")
    location = event.get("location", "No location")
    description = (event.get("description") or "")[:2000]
    account = event.get("_account_label", "Unknown")

    # Attendee profiles section
    attendee_text = ""
    for p in profiles:
        attendee_text += f"\n**{p.get('name', p['email'])}**\n"
        attendee_text += f"- Email: {p['email']}\n"
        if p.get("position"):
            attendee_text += f"- Title: {p['position']}\n"
        if p.get("company"):
            attendee_text += f"- Company: {p['company']}\n"
        if p.get("headline"):
            attendee_text += f"- Headline: {p['headline']}\n"
        if p.get("location"):
            attendee_text += f"- Location: {p['location']}\n"
        if p.get("linkedin_url"):
            attendee_text += f"- LinkedIn: {p['linkedin_url']}\n"
        if p.get("comms_closeness"):
            attendee_text += f"- Relationship: {p['comms_closeness']} (momentum: {p.get('comms_momentum', '?')})\n"
        if p.get("comms_chronological"):
            attendee_text += f"- Comms history: {p['comms_chronological']}\n"
        if p.get("shared_background"):
            attendee_text += f"- SHARED BACKGROUND: {'; '.join(p['shared_background'])}\n"
        if p.get("primary_interests"):
            attendee_text += f"- Interests: {', '.join(p['primary_interests'][:5])}\n"
        if p.get("talking_points_from_tags"):
            attendee_text += f"- Existing talking points: {'; '.join(p['talking_points_from_tags'][:3])}\n"
        if p.get("kindora_prospect_type"):
            attendee_text += f"- Kindora prospect: {p['kindora_prospect_type']} (fit: {p.get('kindora_pitch_fit', '?')})\n"
        if p.get("ask_readiness_tier"):
            attendee_text += f"- OC ask readiness: {p['ask_readiness_tier']} (score: {p.get('ask_readiness_score', '?')})\n"
        if p.get("taxonomy"):
            attendee_text += f"- Category: {p['taxonomy']}\n"
        if p.get("web_research"):
            attendee_text += f"- Web research:\n{p['web_research'][:1500]}\n"

    # Comms history section
    comms_text = ""
    if comms.get("emails"):
        comms_text += "\nRecent email threads:\n"
        for e in comms["emails"][:5]:
            d = str(e.get("last_message_date", ""))[:10]
            comms_text += f"  - [{d}] {e.get('subject', '')} ({e.get('direction', '')}, {e.get('message_count', 0)} msgs)\n"
    if comms.get("meetings"):
        comms_text += "\nPast calendar meetings:\n"
        for m in comms["meetings"][:5]:
            d = str(m.get("start_time", ""))[:10]
            comms_text += f"  - [{d}] {m.get('summary', '')} ({m.get('duration_minutes', 0)} min)\n"

    return f"""Write a meeting prep memo for Justin Steele. This will be read on mobile in under 2 minutes before the meeting. Every sentence must earn its place.

Follow this EXACT structure:

## [Meeting Title]
**{entity_ctx['entity']}** | [time] | [location/link]

### Attendees
Markdown table: Name | Role | Org | How We Connected

### Who They Are
For each attendee, 2-3 bullets MAX:
- Current role + one-line career arc
- Shared background with Justin (BOLD these — they're conversation gold)
- Relationship temperature (warm/cold/new) with last touchpoint date if known

### Context
In 3-5 sentences, cover:
- Why this meeting is happening (use the origin context and description)
- What their organization does and why it matters (use the org research)
- Any stated agenda or questions from scheduling emails

### Game Plan
One sentence framing which Justin venture this connects to and why.
Then 3 numbered probes — specific questions Justin should ask. Not generic. Each probe should:
- Reference something specific about the attendee or their org
- Surface information Justin needs to decide next steps
- Where relevant, include an inline warning: (AVOID: [thing not to say/do])

### Target Outcome
2 sentences max: Best realistic outcome + specific next step to propose before the call ends.

---

CONTEXT FOR THIS MEMO:

**Justin's Bio:** {JUSTIN_BIO}

**Meeting Details:**
- Title: {summary}
- Time: {start} to {end}
- Location: {location}
- Account: {account}
- Description/Notes: {description}

**Entity Context:**
- Entity: {entity_ctx['entity']}
- Strategic Focus: {entity_ctx['focus']}
- Elevator Pitch: {entity_ctx['pitch']}

**Attendee Profiles:**
{attendee_text}

**Communication History:**
{comms_text if comms_text else "No prior communication history found."}

**Meeting Origin Context (emails, intros, LinkedIn messages that led to this meeting):**
{origin_context if origin_context else "No origin context found — this may be a cold or self-scheduled meeting."}

**Organization Research:**
{org_research if org_research else "No organization research available."}

INSTRUCTIONS:
- Write for a busy founder scanning on mobile. Be direct. No filler.
- Shared background (same school, employer, board) is GOLD — bold it.
- Every talking point must be specific to THIS person. If it could apply to any meeting, cut it.
- Integrate warnings inline in the Game Plan, not as a separate section.
- Use the origin context to explain HOW this meeting came about — who introduced whom, what was said.
- Use the org research to give Justin real intel on the organization, not just the person.
- Total memo should be under 600 words."""


def generate_memo(event: Dict, profiles: List[Dict], comms: Dict, entity_key: str, config: Dict,
                  origin_context: str = "", org_research: str = "") -> str:
    """Generate a meeting memo using Claude Sonnet 4.6."""
    model = config.get("memo_model", "claude-sonnet-4-6")
    client = anthropic.Anthropic()
    prompt = build_memo_prompt(event, profiles, comms, entity_key, origin_context, org_research)

    response = client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ── Google Doc Creation ───────────────────────────────────────────────────────

def escape_drive_query_value(value: str) -> str:
    """Escape single quotes in Drive query values."""
    return value.replace("'", "\\'")


def get_or_create_drive_folder(service, folder_name: str) -> str:
    """Find or create a Drive folder by name. Returns folder ID."""
    folder_name_escaped = escape_drive_query_value(folder_name)
    query = f"name='{folder_name_escaped}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name, createdTime)",
        orderBy="createdTime",
        pageSize=1,
    ).execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def find_existing_daily_doc(service, folder_id: str, title: str) -> Optional[str]:
    """Find an existing daily prep doc in a folder by exact title."""
    title_escaped = escape_drive_query_value(title)
    query = (
        f"name='{title_escaped}' "
        "and mimeType='application/vnd.google-apps.document' "
        f"and '{folder_id}' in parents and trashed=false"
    )
    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name, modifiedTime)",
        orderBy="modifiedTime desc",
        pageSize=1,
    ).execute()
    files = results.get("files", [])
    if not files:
        return None
    return files[0]["id"]


def build_doc_text(target_date: date, memos: List[Dict], tz: ZoneInfo) -> str:
    """Build text payload for Google Doc body."""
    content_parts = []
    content_parts.append(f"Meeting Prep Memos\n{target_date.strftime('%A, %B %d, %Y')}\n\n")
    content_parts.append("TODAY'S SCHEDULE\n\n")
    for m in memos:
        event = m["event"]
        time_str = format_event_time(event, tz)
        summary = event.get("summary", "Untitled")
        content_parts.append(f"  {time_str}  {summary}\n")
    content_parts.append("\n" + "=" * 60 + "\n\n")

    for m in memos:
        content_parts.append(m["memo_text"])
        content_parts.append("\n\n" + "=" * 60 + "\n\n")

    return "".join(content_parts)


def replace_google_doc_text(docs_service, doc_id: str, text: str):
    """Replace full Google Doc body with provided plain text."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    body = doc.get("body", {}).get("content", [])
    end_index = body[-1].get("endIndex", 1) if body else 1

    requests_body = []
    if end_index > 2:
        requests_body.append(
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": end_index - 1,
                    }
                }
            }
        )
    requests_body.append({"insertText": {"location": {"index": 1}, "text": text}})
    docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests_body}).execute()


def create_google_doc(config: Dict, target_date: date, memos: List[Dict]) -> Optional[Dict]:
    """Create or update a Google Doc with all meeting memos. Returns {doc_id, doc_url}."""
    account = config.get("google_doc_account", "justin@truesteele.com")
    folder_name = config.get("google_doc_folder_name", "Meeting Prep Memos")
    reuse_daily = bool(config.get("reuse_daily_google_doc", True))
    local_tz = get_local_timezone(config)

    docs_service = build_service(account, "docs", "v1")
    drive_service = build_service(account, "drive", "v3")
    if not docs_service or not drive_service:
        print(f"  [ERROR] Cannot build Google API services for {account}")
        return None

    folder_id = get_or_create_drive_folder(drive_service, folder_name)
    print(f"  Drive folder: {folder_name} ({folder_id})")

    title = f"Meeting Prep — {target_date.strftime('%A, %B %d, %Y')}"
    doc_id = None
    created = False
    if reuse_daily:
        doc_id = find_existing_daily_doc(drive_service, folder_id, title)
        if doc_id:
            print("  Reusing existing daily Google Doc")

    if not doc_id:
        doc = docs_service.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]
        created = True
        file_meta = drive_service.files().get(fileId=doc_id, fields="parents").execute()
        parents = file_meta.get("parents", [])
        remove_parents = ",".join(parents) if parents else None

        update_kwargs = {
            "fileId": doc_id,
            "addParents": folder_id,
            "fields": "id, parents",
        }
        if remove_parents:
            update_kwargs["removeParents"] = remove_parents
        drive_service.files().update(**update_kwargs).execute()

    full_content = build_doc_text(target_date, memos, local_tz)
    replace_google_doc_text(docs_service, doc_id, full_content)

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    verb = "Created" if created else "Updated"
    print(f"  {verb} Google Doc: {doc_url}")
    return {"doc_id": doc_id, "doc_url": doc_url}


# ── Calendar Attachment ───────────────────────────────────────────────────────

def attach_doc_to_events(memos: List[Dict], doc_info: Dict):
    """Attach the Google Doc to each calendar event that got a memo."""
    doc_url = doc_info["doc_url"]
    doc_prefix = f"https://docs.google.com/document/d/{doc_info['doc_id']}"

    for m in memos:
        event = m["event"]
        account = event["_account_email"]
        event_id = event.get("id")
        if not event_id:
            continue

        service = build_service(account)
        if not service:
            continue

        try:
            current_event = service.events().get(calendarId="primary", eventId=event_id).execute()
            existing = current_event.get("attachments", [])
            # Check if doc is already attached
            if any(a.get("fileUrl", "").startswith(doc_prefix) for a in existing):
                print(f"    [SKIP] Doc already attached to {event.get('summary', '')}")
                continue

            new_attachment = {
                "fileUrl": doc_url,
                "mimeType": "application/vnd.google-apps.document",
                "title": f"Meeting Prep — {event.get('summary', 'Meeting')}",
            }
            attachments = existing + [new_attachment]

            service.events().patch(
                calendarId="primary",
                eventId=event_id,
                supportsAttachments=True,
                body={"attachments": attachments},
            ).execute()
            print(f"    Attached to: {event.get('summary', 'Unknown')}")
        except Exception as e:
            print(f"    [ERROR] Attaching to {event.get('summary', '')}: {e}")


# ── Local Markdown Output ─────────────────────────────────────────────────────

def write_local_markdown(target_date: date, all_events: List[Dict], memos: List[Dict],
                         skipped: List[tuple], doc_info: Optional[Dict], config: Dict):
    """Write local markdown backup of memos."""
    local_tz = get_local_timezone(config)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{target_date.isoformat()}_daily_prep.md")

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Daily Meeting Prep Memos\n")
        f.write(f"## {target_date.strftime('%A, %B %d, %Y')}\n\n")
        if doc_info:
            f.write(f"**Google Doc:** [{doc_info['doc_url']}]({doc_info['doc_url']})\n\n")
        f.write("---\n\n")

        # Schedule
        f.write("## Today's Schedule\n\n")
        f.write("| Time | Meeting | Account | Status |\n")
        f.write("|------|---------|---------|--------|\n")
        for ev in all_events:
            time_str = format_event_time(ev, local_tz)
            label = clean_cell(ev.get("_account_label", ""))
            # Check if this event got a memo
            got_memo = any(m["event"].get("id") == ev.get("id") for m in memos)
            status = "MEMO" if got_memo else "skipped"
            summary = clean_cell(ev.get("summary", "Untitled"))
            f.write(f"| {time_str} | {summary} | {label} | {status} |\n")
        f.write("\n---\n\n")

        # Skipped events
        if skipped:
            f.write("## Skipped Events\n\n")
            for ev, reason in skipped:
                summary = clean_cell(ev.get("summary", "Untitled"))
                f.write(f"- {summary}: {reason}\n")
            f.write("\n---\n\n")

        # Memos
        for i, m in enumerate(memos):
            f.write(f"# MEMO {i + 1}\n\n")
            f.write(m["memo_text"])
            f.write("\n\n---\n\n")

        generated_at = datetime.now(local_tz).strftime("%Y-%m-%d %H:%M %Z")
        f.write(f"\n*Generated: {generated_at} by daily_meeting_prep.py*\n")

    print(f"  Local markdown: {path}")
    return path


# ── Main Pipeline ─────────────────────────────────────────────────────────────

def validate_runtime_requirements(dry_run: bool):
    """Fail early for required credentials in active run mode."""
    if dry_run:
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is required for memo generation.")


def run(target_date: date, dry_run: bool = False, no_gdoc: bool = False):
    """Main pipeline."""
    config = load_config()
    validate_runtime_requirements(dry_run=dry_run)

    print(f"\n{'=' * 60}")
    print(f"  Daily Meeting Prep — {target_date.strftime('%A, %B %d, %Y')}")
    if dry_run:
        print("  MODE: DRY RUN (read-only preview; no writes)")
    print(f"{'=' * 60}\n")

    # 1. Fetch calendar events
    print("1. Fetching calendar events...")
    all_events = fetch_events(target_date, config)
    print(f"   Total: {len(all_events)} events\n")

    if not all_events:
        print("No events found. Nothing to prep.")
        if not dry_run:
            write_local_markdown(target_date, [], [], [], None, config)
        return

    # 2. Filter
    print("2. Filtering events...")
    needs_memo, skipped = classify_events(all_events, config)
    for ev, reason in skipped:
        print(f"   [SKIP] {ev.get('summary', 'Untitled')}: {reason}")
    print(f"\n   {len(needs_memo)} meetings need prep memos")
    for ev in needs_memo:
        ext = get_external_attendees(ev, config)
        print(f"   [MEMO] {ev.get('summary', 'Untitled')} ({len(ext)} external attendees)")

    if not needs_memo:
        print("\nNo external meetings to prep. Enjoy your day!")
        if not dry_run:
            write_local_markdown(target_date, all_events, [], skipped, None, config)
        return

    if dry_run:
        print("\n--- DRY RUN COMPLETE ---")
        print(f"Would generate {len(needs_memo)} memos.")
        for ev in needs_memo:
            ext = get_external_attendees(ev, config)
            emails = [a["email"] for a in ext]
            print(f"  {ev.get('summary', '')}: {', '.join(emails)}")
        return

    # 3. Research attendees
    print(f"\n3. Researching attendees...")
    memos = []
    doc_info = None
    conn = None
    try:
        try:
            conn = get_db_connection()
        except Exception as e:
            print(f"   [WARN] DB unavailable, continuing without contact/comms lookups: {e}")

        meeting_data = []
        for ev in needs_memo:
            print(f"   Meeting: {ev.get('summary', 'Untitled')}")
            profiles, comms, origin_context, org_research = research_attendees(ev, config, conn)
            entity_key = ENTITY_MAP.get(ev["_account_email"], "truesteele")
            meeting_data.append({
                "event": ev,
                "profiles": profiles,
                "comms": comms,
                "entity_key": entity_key,
                "origin_context": origin_context,
                "org_research": org_research,
            })

        # 4. Generate memos
        print(f"\n4. Generating memos with Claude Sonnet 4.6...")
        for md in meeting_data:
            print(f"   Writing: {md['event'].get('summary', 'Untitled')}...")
            try:
                memo_text = generate_memo(
                    md["event"],
                    md["profiles"],
                    md["comms"],
                    md["entity_key"],
                    config,
                    origin_context=md.get("origin_context", ""),
                    org_research=md.get("org_research", ""),
                )
                memos.append({"event": md["event"], "memo_text": memo_text})
                time.sleep(1)
            except Exception as e:
                print(f"   [ERROR] Memo generation failed: {e}")
                traceback.print_exc()
                memos.append({"event": md["event"], "memo_text": f"[Memo generation failed: {e}]"})

        # 5. Create Google Doc
        if not no_gdoc:
            print(f"\n5. Creating Google Doc...")
            try:
                doc_info = create_google_doc(config, target_date, memos)
            except Exception as e:
                print(f"   [ERROR] Google Doc creation failed: {e}")
                traceback.print_exc()
        else:
            print("\n5. Google Doc creation skipped (--no-gdoc)")

        # 6. Attach to calendar events
        if doc_info and config.get("attach_to_calendar", True):
            print(f"\n6. Attaching doc to calendar events...")
            attach_doc_to_events(memos, doc_info)
        else:
            print("\n6. Calendar attachment skipped")

        # 7. Write local markdown
        print(f"\n7. Writing local markdown backup...")
        write_local_markdown(target_date, all_events, memos, skipped, doc_info, config)

    finally:
        if conn:
            conn.close()

    print(f"\n{'=' * 60}")
    print(f"  Done! {len(memos)} memos generated.")
    if doc_info:
        print(f"  Google Doc: {doc_info['doc_url']}")
    print(f"{'=' * 60}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Daily Meeting Prep Memo Generator")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD)")
    parser.add_argument("--days-ahead", type=int, default=0, help="Days ahead (0=today)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; no DB writes, docs, or calendar patches")
    parser.add_argument("--no-gdoc", action="store_true", help="Skip Google Doc creation")
    args = parser.parse_args()

    if args.days_ahead < 0:
        raise ValueError("--days-ahead must be >= 0")

    config = load_config()
    local_tz = get_local_timezone(config)

    if args.date:
        try:
            target = date.fromisoformat(args.date)
        except ValueError as exc:
            raise ValueError(f"Invalid --date '{args.date}'. Expected YYYY-MM-DD.") from exc
    else:
        target = datetime.now(local_tz).date() + timedelta(days=args.days_ahead)

    run(target, dry_run=args.dry_run, no_gdoc=args.no_gdoc)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}")
        raise
