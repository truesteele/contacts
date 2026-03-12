#!/usr/bin/env python3
"""
Sally's Network — Email Discovery

Three-phase approach:
  Phase 1: Extract emails from existing sally_contact_email_threads participants (fast, no API)
  Phase 2: Search Sally's 3 Gmail accounts for remaining contacts (API-based)
  Phase 3: Scrape LinkedIn contact info via Playwright for remaining contacts

Usage:
  python scripts/intelligence/sally/discover_emails.py --phase 1          # Thread extraction only
  python scripts/intelligence/sally/discover_emails.py --phase 2          # Gmail search only
  python scripts/intelligence/sally/discover_emails.py --phase 3          # LinkedIn scrape only
  python scripts/intelligence/sally/discover_emails.py                    # Phases 1+2 only
  python scripts/intelligence/sally/discover_emails.py --all              # All three phases
  python scripts/intelligence/sally/discover_emails.py --phase 2 -n 50   # First 50 only
  python scripts/intelligence/sally/discover_emails.py --dry-run          # Don't write
"""

import os
import sys
import json
import time
import re
import email.utils
import argparse
import random
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()


# ── Config ────────────────────────────────────────────────────────────

SALLY_GOOGLE_ACCOUNTS = [
    "sally.steele@gmail.com",
    "sally@outdoorithm.com",
    "sally@outdoorithmcollective.org",
]

SALLY_CREDENTIALS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "docs", "credentials", "Sally", "tokens"
)

SALLY_EMAILS = {
    "sally.steele@gmail.com",
    "sally@outdoorithm.com",
    "sally@outdoorithmcollective.org",
}

SKIP_EMAIL_PATTERNS = [
    r"noreply@", r"no-reply@", r"notifications@", r"notify@",
    r"mailer-daemon@", r"postmaster@", r"bounce@", r"donotreply@",
    r".*@googlegroups\.com$", r".*@groups\.google\.com$",
    r".*@calendar\.google\.com$", r".*@docs\.google\.com$",
    r".*@linkedin\.com$", r".*@facebookmail\.com$",
    r".*@vercel\.com$", r".*@github\.com$",
    r".*@mailchimp\.com$", r".*@sendgrid\.net$",
    r".*@paperlesspost\.com$", r".*@evite\.com$", r".*@eventbrite\.com$",
    r".*@punchbowl\.com$", r".*@partiful\.com$", r".*@lu\.ma$",
    r".*@meetup\.com$", r".*@canva\.com$",
]


# ── Pydantic Schema ──────────────────────────────────────────────────

class EmailVerification(BaseModel):
    is_match: bool = Field(description="Is this email likely the contact's actual email?")
    confidence: int = Field(ge=0, le=100, description="0-100 confidence score")
    reasoning: str = Field(description="Brief explanation")
    email_type: str = Field(description="personal | work | unknown")


# ── Helpers ───────────────────────────────────────────────────────────

def get_db_conn():
    return psycopg2.connect(
        host="db.ypqsrejrsocebnldicke.supabase.co",
        port=5432,
        dbname="postgres",
        user="postgres",
        password=os.environ["SUPABASE_DB_PASSWORD"],
    )


def is_skip_email(addr: str) -> bool:
    addr = addr.lower().strip()
    if addr in SALLY_EMAILS:
        return True
    if not addr or "@" not in addr:
        return True
    for pattern in SKIP_EMAIL_PATTERNS:
        if re.match(pattern, addr):
            return True
    return False


def name_in_email(first: str, last: str, addr: str) -> float:
    """Score how well a contact name matches an email address. Returns 0-1."""
    first = first.lower().strip().split()[0] if first else ""
    last = last.lower().strip().split(",")[0].split()[0] if last else ""
    addr_lower = addr.lower()
    local = addr_lower.split("@")[0] if "@" in addr_lower else ""

    if not first or not last:
        return 0.0

    if first in local and last in local:
        return 1.0
    if last in local and first[0] in local:
        return 0.7
    if last in local and len(last) > 4:
        return 0.5
    if first in local and len(first) > 4:
        return 0.3
    return 0.0


def name_matches_display(first: str, last: str, display: str) -> float:
    """Score how well a contact name matches a display name from email headers."""
    if not display:
        return 0.0
    first = first.lower().strip().split()[0] if first else ""
    last = last.lower().strip().split(",")[0].split()[0] if last else ""
    display = display.lower().strip()

    if not first or not last:
        return 0.0

    full = f"{first} {last}"
    if full == display or f"{last}, {first}" == display or f"{last} {first}" == display:
        return 1.0
    if first in display and last in display:
        return 0.9
    if last in display and display.startswith(first[0]):
        return 0.7
    if last in display and len(last) > 3:
        return 0.4
    return 0.0


def load_gmail_service(account_email: str):
    """Load Gmail API service for a Sally account."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    cred_path = os.path.join(SALLY_CREDENTIALS_DIR, f"{account_email}.json")
    if not os.path.exists(cred_path):
        # Also check the MCP credentials dir
        mcp_path = os.path.expanduser(f"~/.google_workspace_mcp/credentials/{account_email}.json")
        if os.path.exists(mcp_path):
            cred_path = mcp_path
        else:
            print(f"    No credentials for {account_email}")
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
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# ── Phase 1: Extract from existing thread participants ────────────────

def phase1_extract_from_threads(conn, dry_run=False):
    """Extract emails from sally_contact_email_threads participants."""
    print("\n" + "=" * 60)
    print("PHASE 1: Extract emails from existing thread participants")
    print("=" * 60)

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT DISTINCT c.id, c.first_name, c.last_name, c.company, c.headline
        FROM sally_contacts c
        JOIN sally_contact_email_threads t ON t.contact_id = c.id
        WHERE (c.email IS NULL OR c.email = '')
        AND t.channel = 'email'
    """)
    contacts = cur.fetchall()
    print(f"  Found {len(contacts)} contacts with thread data but no email\n")

    found = 0
    skipped = 0

    for contact in contacts:
        cid = contact["id"]
        first = contact["first_name"] or ""
        last = contact["last_name"] or ""
        name = f"{first} {last}".strip()

        cur.execute("""
            SELECT participants, subject, is_group, participant_count
            FROM sally_contact_email_threads
            WHERE contact_id = %s AND channel = 'email'
            ORDER BY participant_count ASC, last_message_date DESC
        """, (cid,))
        threads = cur.fetchall()

        candidates = {}

        for thread in threads:
            participants = thread["participants"] or []
            is_group = thread["is_group"]
            pcount = thread["participant_count"] or 0

            for p in participants:
                addr = ""
                display = ""
                if isinstance(p, dict):
                    addr = p.get("email", "").lower().strip()
                    display = p.get("name", "")
                elif isinstance(p, str):
                    addr = p.lower().strip()

                if not addr or is_skip_email(addr):
                    continue

                email_score = name_in_email(first, last, addr)
                display_score = name_matches_display(first, last, display)
                best_score = max(email_score, display_score)

                if pcount <= 3 and not is_group and best_score >= 0.3:
                    best_score = max(best_score, 0.6)

                if best_score >= 0.3:
                    if addr not in candidates or candidates[addr] < best_score:
                        candidates[addr] = best_score

        if not candidates:
            skipped += 1
            continue

        best_email = max(candidates, key=candidates.get)
        best_score = candidates[best_email]

        if best_score >= 0.5:
            marker = "[DRY-RUN] " if dry_run else ""
            print(f"  {marker}[{cid}] {name}: {best_email} (score={best_score:.1f})")

            if not dry_run:
                cur.execute(
                    "UPDATE sally_contacts SET email = %s WHERE id = %s AND (email IS NULL OR email = '')",
                    (best_email, cid)
                )
                conn.commit()
            found += 1
        else:
            skipped += 1

    print(f"\n  Phase 1 results: {found} emails extracted, {skipped} skipped")
    return found


# ── Phase 2: Gmail search ────────────────────────────────────────────

def phase2_gmail_search(conn, openai_client, gmail_services, dry_run=False, limit=None):
    """Search Sally's Gmail accounts for emails of contacts missing them."""
    from googleapiclient.errors import HttpError

    print("\n" + "=" * 60)
    print("PHASE 2: Search Sally's Gmail for remaining missing emails")
    print("=" * 60)

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT id, first_name, last_name, company, position, headline, linkedin_url,
               enrich_current_company, enrich_current_title,
               ai_proximity_score, ai_proximity_tier
        FROM sally_contacts
        WHERE (email IS NULL OR email = '')
        AND first_name IS NOT NULL AND first_name != ''
        AND last_name IS NOT NULL AND last_name != ''
        ORDER BY COALESCE(ai_proximity_score, 0) DESC
    """)
    contacts = cur.fetchall()

    if limit:
        contacts = contacts[:limit]

    total = len(contacts)
    print(f"  Found {total} contacts to search\n")

    stats = {"searched": 0, "found": 0, "skipped": 0, "no_candidates": 0, "errors": 0}
    start_time = time.time()

    PERSONAL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                        "icloud.com", "me.com", "aol.com", "comcast.net", "protonmail.com"}

    for i, contact in enumerate(contacts):
        cid = contact["id"]
        first = contact["first_name"] or ""
        last = contact["last_name"] or ""
        name = f"{first} {last}".strip()
        company = contact["company"] or contact["enrich_current_company"] or ""
        prox = contact["ai_proximity_score"] or "?"

        candidates = {}

        for acct, svc in gmail_services.items():
            try:
                _search_gmail_account(svc, acct, first, last, candidates)
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    print(f"    Rate limited on {acct}, waiting 30s...")
                    time.sleep(30)
                else:
                    print(f"    Error on {acct}: {e}")
                    stats["errors"] += 1
            time.sleep(0.05)

        stats["searched"] += 1

        if not candidates:
            stats["no_candidates"] += 1
            if (i + 1) % 100 == 0:
                _print_progress(i + 1, total, stats, start_time)
            continue

        scored = []
        for addr, info in candidates.items():
            score = info["name_score"] * 50
            score += min(info["thread_count"] * 3, 15)
            score += min(len(info["accounts"]) * 5, 15)
            domain = addr.split("@")[1] if "@" in addr else ""
            is_personal = domain in PERSONAL_DOMAINS
            if company:
                comp_lower = company.lower().replace(" ", "").replace(",", "")
                if len(comp_lower) > 3 and comp_lower[:4] in domain:
                    score += 20
                elif not is_personal and domain:
                    score = min(score, 60)
            if is_personal:
                score += 3
            scored.append((addr, score, info))

        scored.sort(key=lambda x: x[1], reverse=True)
        best_email, best_score, best_info = scored[0]

        if best_score < 25:
            stats["no_candidates"] += 1
            if (i + 1) % 100 == 0:
                _print_progress(i + 1, total, stats, start_time)
            continue

        # LLM verification for non-obvious matches
        if best_score < 65:
            verification = _verify_with_llm(openai_client, contact, best_email, best_info)
            if not verification or not verification.is_match or verification.confidence < 70:
                stats["skipped"] += 1
                reason = verification.reasoning if verification else "LLM error"
                print(f"  [{cid}] {name} ({prox}): SKIP {best_email} - {reason}")
                if (i + 1) % 100 == 0:
                    _print_progress(i + 1, total, stats, start_time)
                continue

        marker = "[DRY-RUN] " if dry_run else ""
        print(f"  {marker}[{cid}] {name} ({company}, prox={prox}): FOUND {best_email} "
              f"(score={best_score:.0f}, threads={best_info['thread_count']}, "
              f"accts={len(best_info['accounts'])})")

        if not dry_run:
            cur.execute(
                "UPDATE sally_contacts SET email = %s WHERE id = %s AND (email IS NULL OR email = '')",
                (best_email, cid)
            )
            conn.commit()
        stats["found"] += 1

        if (i + 1) % 50 == 0:
            _print_progress(i + 1, total, stats, start_time)

    _print_progress(total, total, stats, start_time)
    print(f"\n  Phase 2 results: {stats['found']} found, {stats['skipped']} skipped, "
          f"{stats['no_candidates']} no candidates, {stats['errors']} errors")
    return stats["found"]


def _search_gmail_account(service, account_email, first, last, candidates):
    """Search one Gmail account for a contact's name."""
    from googleapiclient.errors import HttpError

    query = f'"{first} {last}"'
    try:
        results = service.users().messages().list(
            userId="me", q=query, maxResults=15
        ).execute()
    except HttpError as e:
        if e.resp.status == 429:
            raise
        return

    if not results.get("messages"):
        return

    for msg_ref in results["messages"][:10]:
        try:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "To", "Cc", "Subject"]
            ).execute()
        except HttpError:
            continue

        headers = msg.get("payload", {}).get("headers", [])

        for hdr in headers:
            hdr_name = hdr.get("name", "").lower()
            if hdr_name in ("from", "to", "cc"):
                addrs = email.utils.getaddresses([hdr.get("value", "")])
                for display_name, addr in addrs:
                    addr = addr.lower().strip()
                    if not addr or is_skip_email(addr):
                        continue

                    score = max(
                        name_in_email(first, last, addr),
                        name_matches_display(first, last, display_name)
                    )
                    if score < 0.3:
                        continue

                    if addr not in candidates:
                        candidates[addr] = {
                            "name_score": score,
                            "display_name": display_name,
                            "thread_count": 0,
                            "accounts": set(),
                        }
                    else:
                        candidates[addr]["name_score"] = max(
                            candidates[addr]["name_score"], score
                        )

                    candidates[addr]["thread_count"] += 1
                    candidates[addr]["accounts"].add(account_email)

        time.sleep(0.02)


def _verify_with_llm(openai_client, contact, email_addr, info):
    """Use GPT-5 mini to verify borderline email matches."""
    first = contact["first_name"] or ""
    last = contact["last_name"] or ""
    name = f"{first} {last}".strip()

    current_company = contact.get('company') or contact.get('enrich_current_company') or '?'
    domain = email_addr.split("@")[1] if "@" in email_addr else ""

    prompt = (
        f"Verify if this email belongs to this person and is still usable.\n\n"
        f"PERSON: {name}\n"
        f"  Current company: {current_company}\n"
        f"  Title: {contact.get('position') or contact.get('enrich_current_title') or '?'}\n"
        f"  LinkedIn: {contact.get('linkedin_url', '?')}\n\n"
        f"CANDIDATE: {email_addr}\n"
        f"  Display name: {info['display_name']}\n"
        f"  Found in {info['thread_count']} threads across {len(info['accounts'])} accounts\n"
        f"  Name match score: {info['name_score']:.0%}\n\n"
        f"RULES:\n"
        f"- REJECT service/relay emails even if display name matches\n"
        f"- REJECT corporate emails if the person no longer works there\n"
        f"- ACCEPT personal emails with good name match even if old\n"
        f"- For common names require 3+ threads or multiple accounts\n"
        f"- When in doubt, reject"
    )

    try:
        resp = openai_client.responses.parse(
            model="gpt-5-mini",
            instructions="You verify email matches. Be accurate and concise.",
            input=prompt,
            text_format=EmailVerification,
        )
        return resp.output_parsed
    except Exception as e:
        print(f"    LLM error: {e}")
        return None


def _print_progress(current, total, stats, start_time):
    elapsed = time.time() - start_time
    rate = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / rate if rate > 0 else 0
    print(f"\n  --- {current}/{total} ({stats['found']} found, "
          f"{stats['no_candidates']} none, {stats['skipped']} skipped) "
          f"[{elapsed:.0f}s elapsed, ~{eta:.0f}s remaining] ---\n")


# ── Phase 3: LinkedIn contact info scraping via Playwright ────────────
#
# SAFETY MEASURES (protect Sally's account at all costs):
# 1. Max 100 profiles per session (--batch-size, default 100)
# 2. Long human-like delays: 8-15s between profiles
# 3. Session breaks: 3-8 min pause every 25 profiles
# 4. Random scroll/mouse behavior to mimic human browsing
# 5. Cookie persistence between sessions (reuse login)
# 6. Rate limit detection with aggressive backoff (5 min)
# 7. Auth wall detection → immediate session abort
# 8. Consecutive error circuit breaker (5 errors = stop)
# 9. Non-headless by default (headless is easier to detect)
# 10. Real viewport, timezone, locale, webGL fingerprint

LINKEDIN_COOKIE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", ".linkedin_cookies.json"
)

# Safety defaults
DEFAULT_BATCH_SIZE = 100
MIN_DELAY = 8       # seconds between profiles
MAX_DELAY = 15
BREAK_EVERY = 25    # profiles before a longer break
BREAK_MIN = 180     # 3 min break
BREAK_MAX = 480     # 8 min break
MAX_CONSECUTIVE_ERRORS = 5
RATE_LIMIT_PAUSE = 300  # 5 min on rate limit
AUTH_WALL_ABORT = True  # immediately stop if auth wall detected


def _human_delay(min_s=MIN_DELAY, max_s=MAX_DELAY):
    """Sleep for a random human-like duration."""
    delay = random.uniform(min_s, max_s)
    # Occasionally take a longer "distraction" pause (10% chance)
    if random.random() < 0.10:
        delay += random.uniform(5, 20)
    time.sleep(delay)


def _simulate_human_behavior(page):
    """Random scrolls and mouse movements to look human."""
    try:
        # Random scroll
        scroll_y = random.randint(100, 500)
        page.mouse.wheel(0, scroll_y)
        time.sleep(random.uniform(0.3, 1.0))

        # Random mouse move
        x = random.randint(200, 800)
        y = random.randint(200, 600)
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.2, 0.6))

        # Sometimes scroll back up
        if random.random() < 0.3:
            page.mouse.wheel(0, -random.randint(50, 200))
            time.sleep(random.uniform(0.2, 0.5))
    except Exception:
        pass  # Non-critical


def _save_cookies(context):
    """Save browser cookies for session reuse."""
    try:
        cookies = context.cookies()
        with open(LINKEDIN_COOKIE_FILE, "w") as f:
            json.dump(cookies, f)
    except Exception:
        pass


def _load_cookies(context):
    """Load saved cookies to resume session."""
    try:
        if os.path.exists(LINKEDIN_COOKIE_FILE):
            with open(LINKEDIN_COOKIE_FILE) as f:
                cookies = json.load(f)
            context.add_cookies(cookies)
            return True
    except Exception:
        pass
    return False


def phase3_linkedin_scrape(conn, dry_run=False, limit=None, headless=False,
                            linkedin_email=None, linkedin_password=None,
                            batch_size=DEFAULT_BATCH_SIZE):
    """Scrape LinkedIn contact info pages with maximum account safety."""
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("PHASE 3: Scrape LinkedIn contact info via Playwright")
    print("=" * 60)
    print(f"  Safety settings:")
    print(f"    Batch size: {batch_size} profiles max")
    print(f"    Delay between profiles: {MIN_DELAY}-{MAX_DELAY}s")
    print(f"    Session break every {BREAK_EVERY} profiles: {BREAK_MIN//60}-{BREAK_MAX//60} min")
    print(f"    Rate limit pause: {RATE_LIMIT_PAUSE}s")
    print(f"    Auth wall: {'abort immediately' if AUTH_WALL_ABORT else 'pause and retry'}")
    print(f"    Max consecutive errors: {MAX_CONSECUTIVE_ERRORS}")
    print()

    if not linkedin_email or not linkedin_password:
        print("  ERROR: LinkedIn credentials required for phase 3")
        print("  Usage: --linkedin-email EMAIL --linkedin-password PASS")
        return 0

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT id, first_name, last_name, linkedin_url, company, position
        FROM sally_contacts
        WHERE (email IS NULL OR email = '')
        AND linkedin_url IS NOT NULL AND linkedin_url != ''
        AND first_name IS NOT NULL AND first_name != ''
        ORDER BY COALESCE(ai_proximity_score, 0) DESC
    """)
    contacts = cur.fetchall()

    # Apply batch size limit (safety cap)
    effective_limit = min(limit or batch_size, batch_size)
    contacts = contacts[:effective_limit]

    total = len(contacts)
    print(f"  Found {total} contacts to scrape (batch capped at {effective_limit})\n")

    if total == 0:
        return 0

    stats = {"found": 0, "no_email": 0, "errors": 0, "rate_limited": 0, "consecutive_errors": 0}
    start_time = time.time()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        context = browser.new_context(
            viewport={"width": random.randint(1260, 1380), "height": random.randint(850, 950)},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.205 Safari/537.36",
            locale="en-US",
            timezone_id="America/Los_Angeles",
            color_scheme="light",
        )

        # Remove navigator.webdriver flag
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)

        page = context.new_page()

        # Try to reuse existing session via cookies
        has_cookies = _load_cookies(context)
        logged_in = False

        if has_cookies:
            print("  Loaded saved cookies, checking session...")
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
            time.sleep(3)
            if "/feed" in page.url or page.query_selector("nav.global-nav"):
                logged_in = True
                print("  Reused existing session (no fresh login needed)")

        if not logged_in:
            print("  Logging into LinkedIn...")
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 4))

            # Type slowly like a human
            page.click("#username")
            for char in linkedin_email:
                page.keyboard.type(char, delay=random.randint(50, 150))
            time.sleep(random.uniform(0.5, 1.5))

            page.click("#password")
            for char in linkedin_password:
                page.keyboard.type(char, delay=random.randint(50, 150))
            time.sleep(random.uniform(0.5, 1.5))

            page.click('button[type="submit"]')
            time.sleep(random.uniform(5, 8))

            # Check for security challenges
            if "checkpoint" in page.url or "challenge" in page.url:
                print("  !! SECURITY CHECKPOINT detected !!")
                print("  Please complete the verification in the browser window.")
                print("  Waiting up to 120 seconds...")
                for _ in range(24):
                    time.sleep(5)
                    if "checkpoint" not in page.url and "challenge" not in page.url:
                        break
                else:
                    print("  Checkpoint not resolved. ABORTING to protect account.")
                    browser.close()
                    return 0

            if "/feed" in page.url or page.query_selector("nav.global-nav"):
                print("  Logged in successfully")
                _save_cookies(context)
            else:
                print(f"  Login may have failed. URL: {page.url}")
                print("  Waiting 30s for manual intervention...")
                time.sleep(30)
                if "/feed" not in page.url and not page.query_selector("nav.global-nav"):
                    print("  ABORTING — cannot confirm login. Protecting account.")
                    browser.close()
                    return 0
                _save_cookies(context)

        print(f"  Starting scrape of {total} contacts.\n")

        # Browse the feed briefly first (look natural)
        _simulate_human_behavior(page)
        time.sleep(random.uniform(3, 6))

        for i, contact in enumerate(contacts):
            cid = contact["id"]
            first = contact["first_name"] or ""
            last = contact["last_name"] or ""
            name = f"{first} {last}".strip()
            linkedin_url = contact["linkedin_url"].rstrip("/")
            contact_info_url = f"{linkedin_url}/overlay/contact-info/"

            # Circuit breaker: too many consecutive errors = stop
            if stats["consecutive_errors"] >= MAX_CONSECUTIVE_ERRORS:
                print(f"\n  !! CIRCUIT BREAKER: {MAX_CONSECUTIVE_ERRORS} consecutive errors !!")
                print(f"  STOPPING to protect Sally's account. Resume later.")
                break

            # Session break every N profiles
            if i > 0 and i % BREAK_EVERY == 0:
                break_duration = random.uniform(BREAK_MIN, BREAK_MAX)
                elapsed = time.time() - start_time
                print(f"\n  === SESSION BREAK ({break_duration/60:.1f} min) after {i} profiles ===")
                print(f"  Stats so far: {stats['found']} found, {stats['no_email']} no email, "
                      f"{stats['errors']} errors [{elapsed:.0f}s elapsed]")
                print(f"  Resuming at ~{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC + {break_duration/60:.0f}min\n")

                # Save cookies before break
                _save_cookies(context)
                time.sleep(break_duration)

                # After break, visit feed to look natural
                try:
                    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
                    time.sleep(random.uniform(3, 6))
                    _simulate_human_behavior(page)
                    time.sleep(random.uniform(2, 4))
                except Exception:
                    pass

            try:
                # Navigate to contact info
                page.goto(contact_info_url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(random.uniform(2, 4))

                # Simulate reading the page
                _simulate_human_behavior(page)

                # AUTH WALL CHECK — most critical safety check
                current_url = page.url
                if "authwall" in current_url or current_url.startswith("https://www.linkedin.com/login"):
                    stats["rate_limited"] += 1
                    if AUTH_WALL_ABORT:
                        print(f"\n  !! AUTH WALL at profile {i+1} — ABORTING to protect account !!")
                        print(f"  Last successful URL: {contact_info_url}")
                        _save_cookies(context)
                        break
                    else:
                        print(f"  [{cid}] {name}: AUTH WALL — pausing {RATE_LIMIT_PAUSE}s")
                        time.sleep(RATE_LIMIT_PAUSE)
                        page.goto(contact_info_url, wait_until="domcontentloaded", timeout=15000)
                        time.sleep(3)

                # "Page not found" or restricted profile check
                if "/404" in current_url or "unavailable" in (page.title() or "").lower():
                    stats["errors"] += 1
                    stats["consecutive_errors"] += 1
                    continue

                # Extract email from contact info overlay
                found_email = None

                # Method 1: mailto links
                mailto_links = page.query_selector_all('a[href^="mailto:"]')
                for link in mailto_links:
                    href = link.get_attribute("href") or ""
                    addr = href.replace("mailto:", "").lower().strip()
                    if addr and "@" in addr and not is_skip_email(addr):
                        found_email = addr
                        break

                # Method 2: email section with header
                if not found_email:
                    sections = page.query_selector_all("section")
                    for section in sections:
                        header = section.query_selector("h3")
                        if header and "email" in (header.inner_text() or "").lower():
                            links = section.query_selector_all("a")
                            for link in links:
                                text = (link.inner_text() or "").strip().lower()
                                if "@" in text and "." in text and not is_skip_email(text):
                                    found_email = text
                                    break
                            if not found_email:
                                spans = section.query_selector_all("span, div")
                                for span in spans:
                                    text = (span.inner_text() or "").strip().lower()
                                    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text):
                                        if not is_skip_email(text):
                                            found_email = text
                                            break

                if found_email:
                    marker = "[DRY-RUN] " if dry_run else ""
                    print(f"  {marker}[{cid}] {name}: {found_email}")
                    if not dry_run:
                        cur.execute(
                            "UPDATE sally_contacts SET email = %s WHERE id = %s AND (email IS NULL OR email = '')",
                            (found_email, cid)
                        )
                        conn.commit()
                    stats["found"] += 1
                else:
                    stats["no_email"] += 1

                # Reset consecutive error counter on success
                stats["consecutive_errors"] = 0

            except Exception as e:
                error_msg = str(e)
                stats["consecutive_errors"] += 1

                if "timeout" in error_msg.lower():
                    stats["errors"] += 1
                elif "429" in error_msg or "rate" in error_msg.lower():
                    stats["rate_limited"] += 1
                    print(f"  [{cid}] {name}: Rate limited — pausing {RATE_LIMIT_PAUSE}s")
                    time.sleep(RATE_LIMIT_PAUSE)
                else:
                    stats["errors"] += 1
                    if stats["errors"] <= 5:
                        print(f"  [{cid}] {name}: Error — {error_msg[:100]}")

            # Human-like delay between profiles
            _human_delay()

            # Progress report
            if (i + 1) % 10 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed * 3600 if elapsed > 0 else 0
                remaining = total - (i + 1)
                # Estimate with delays + breaks
                est_remaining = remaining * (elapsed / (i + 1)) if i > 0 else 0
                print(f"\n  --- {i+1}/{total} ({stats['found']} found, "
                      f"{stats['no_email']} no email, {stats['errors']} err, "
                      f"{stats['rate_limited']} rl) "
                      f"[{elapsed/60:.0f}min elapsed, ~{est_remaining/60:.0f}min remaining] ---\n")

        # Save cookies at end of session
        _save_cookies(context)
        browser.close()

    elapsed = time.time() - start_time
    profiles_checked = min(i + 1, total) if total > 0 else 0
    print(f"\n  Phase 3 results ({profiles_checked} profiles checked):")
    print(f"    Emails found:       {stats['found']}")
    print(f"    No email on profile:{stats['no_email']}")
    print(f"    Errors:             {stats['errors']}")
    print(f"    Rate limits:        {stats['rate_limited']}")
    print(f"    Time:               {elapsed/60:.1f}min ({elapsed/max(profiles_checked,1):.1f}s/profile)")
    return stats["found"]


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sally Email Discovery")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3],
                        help="Run specific phase only (default: 1+2)")
    parser.add_argument("--all", action="store_true",
                        help="Run all three phases including LinkedIn scrape")
    parser.add_argument("--dry-run", "-d", action="store_true")
    parser.add_argument("--limit", "-n", type=int, default=None,
                        help="Limit contacts to process")
    parser.add_argument("--linkedin-email", type=str, default=None,
                        help="LinkedIn login email for phase 3")
    parser.add_argument("--linkedin-password", type=str, default=None,
                        help="LinkedIn login password for phase 3")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser in headless mode (phase 3) — NOT recommended")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"Max profiles per LinkedIn session (default: {DEFAULT_BATCH_SIZE})")
    args = parser.parse_args()

    conn = get_db_conn()
    print("Connected to database")

    # Count current state
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM sally_contacts")
    total = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM sally_contacts WHERE email IS NOT NULL AND email != ''")
    has_email = cur.fetchone()[0]
    print(f"  Current state: {has_email}/{total} contacts have email ({has_email/total*100:.1f}%)\n")

    total_found = 0

    if args.phase == 1 or (args.phase is None):
        total_found += phase1_extract_from_threads(conn, dry_run=args.dry_run)

    if args.phase == 2 or (args.phase is None):
        openai_client = OpenAI(api_key=os.environ["OPENAI_APIKEY"])
        gmail_services = {}
        for acct in SALLY_GOOGLE_ACCOUNTS:
            svc = load_gmail_service(acct)
            if svc:
                gmail_services[acct] = svc
                print(f"  Loaded Gmail: {acct}")
            else:
                print(f"  MISSING Gmail: {acct}")

        if gmail_services:
            total_found += phase2_gmail_search(conn, openai_client, gmail_services,
                                                dry_run=args.dry_run, limit=args.limit)
        else:
            print("  No Gmail services available, skipping phase 2")

    if args.phase == 3 or args.all:
        total_found += phase3_linkedin_scrape(
            conn, dry_run=args.dry_run, limit=args.limit,
            headless=args.headless,
            linkedin_email=args.linkedin_email,
            linkedin_password=args.linkedin_password,
            batch_size=args.batch_size,
        )

    # Final stats
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM sally_contacts WHERE email IS NOT NULL AND email != ''")
    new_has_email = cur.fetchone()[0]
    print(f"\n{'=' * 60}")
    print(f"FINAL: {new_has_email}/{total} contacts have email ({new_has_email/total*100:.1f}%)")
    print(f"  New emails found this run: {total_found}")
    print(f"  Coverage improvement: {has_email/total*100:.1f}% → {new_has_email/total*100:.1f}%")
    print(f"{'=' * 60}")

    conn.close()


if __name__ == "__main__":
    main()
