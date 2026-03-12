#!/usr/bin/env python3
"""
Justin's LinkedIn Email Discovery + Classification

Two modes:
  1. LinkedIn scrape: Find emails for contacts missing them (ranked by ask_readiness score)
  2. Classify: Use GPT-5 mini to classify existing emails as personal vs work

Safety measures (protect Justin's account):
  1. Max 100 profiles per session (--batch-size)
  2. 8-15s random delays between profiles (+ 10% chance of extra 5-20s pause)
  3. 3-8 min session break every 25 profiles
  4. Random scroll/mouse simulation
  5. Cookie persistence (reuse login across sessions)
  6. Auth wall = immediate abort
  7. Circuit breaker (5 consecutive errors = stop)
  8. Anti-detection: webdriver flag removed, real locale/timezone, random viewport
  9. Human-like typing for login (50-150ms per character)
  10. Feed browsing between session breaks

Usage:
  # Scrape LinkedIn for missing emails (batch of 100)
  python discover_emails_justin.py scrape --linkedin-email EMAIL --linkedin-password PASS

  # Classify campaign emails as personal/work
  python discover_emails_justin.py classify

  # Classify only new emails found by scraper
  python discover_emails_justin.py classify --new-only

  # Dry run (no DB writes)
  python discover_emails_justin.py scrape --dry-run

  # Custom batch size
  python discover_emails_justin.py scrape --batch-size 50 --linkedin-email EMAIL --linkedin-password PASS
"""

import os
import sys
import json
import time
import re
import argparse
import random
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()


# ── Config ────────────────────────────────────────────────────────────

JUSTIN_EMAILS = {
    "justinrsteele@gmail.com",
    "justin@truesteele.com",
    "justin@outdoorithm.com",
    "justin@outdoorithmcollective.org",
    "justin@kindora.co",
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

PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "me.com", "aol.com", "comcast.net", "protonmail.com",
    "live.com", "msn.com", "att.net", "sbcglobal.net", "verizon.net",
    "cox.net", "charter.net", "earthlink.net", "mac.com",
}

# Separate cookie file from Sally
LINKEDIN_COOKIE_FILE = os.path.join(
    os.path.dirname(__file__), "..", ".linkedin_cookies_justin.json"
)

# Safety defaults
DEFAULT_BATCH_SIZE = 100
MIN_DELAY = 8
MAX_DELAY = 15
BREAK_EVERY = 25
BREAK_MIN = 180     # 3 min
BREAK_MAX = 480     # 8 min
MAX_CONSECUTIVE_ERRORS = 5
RATE_LIMIT_PAUSE = 300  # 5 min
AUTH_WALL_ABORT = True


# ── Pydantic Schemas ─────────────────────────────────────────────────

class EmailClassification(BaseModel):
    email_type: str = Field(description="personal | work")
    confidence: int = Field(ge=0, le=100, description="0-100 confidence")
    reasoning: str = Field(description="Brief explanation")


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
    if addr in JUSTIN_EMAILS:
        return True
    if not addr or "@" not in addr:
        return True
    for pattern in SKIP_EMAIL_PATTERNS:
        if re.match(pattern, addr):
            return True
    return False


def classify_email_type(addr: str) -> str:
    """Quick heuristic classification before LLM. Returns personal|work|unknown."""
    if not addr or "@" not in addr:
        return "unknown"
    domain = addr.split("@")[1].lower()
    if domain in PERSONAL_DOMAINS:
        return "personal"
    return "unknown"  # needs LLM for work vs personal on custom domains


# ── LinkedIn Scraping (same safety as Sally's) ───────────────────────

def _human_delay(min_s=MIN_DELAY, max_s=MAX_DELAY):
    delay = random.uniform(min_s, max_s)
    if random.random() < 0.10:
        delay += random.uniform(5, 20)
    time.sleep(delay)


def _simulate_human_behavior(page):
    try:
        scroll_y = random.randint(100, 500)
        page.mouse.wheel(0, scroll_y)
        time.sleep(random.uniform(0.3, 1.0))
        x = random.randint(200, 800)
        y = random.randint(200, 600)
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.2, 0.6))
        if random.random() < 0.3:
            page.mouse.wheel(0, -random.randint(50, 200))
            time.sleep(random.uniform(0.2, 0.5))
    except Exception:
        pass


def _save_cookies(context):
    try:
        cookies = context.cookies()
        with open(LINKEDIN_COOKIE_FILE, "w") as f:
            json.dump(cookies, f)
    except Exception:
        pass


def _load_cookies(context):
    try:
        if os.path.exists(LINKEDIN_COOKIE_FILE):
            with open(LINKEDIN_COOKIE_FILE) as f:
                cookies = json.load(f)
            context.add_cookies(cookies)
            return True
    except Exception:
        pass
    return False


def scrape_linkedin(conn, openai_client, dry_run=False, headless=False,
                    linkedin_email=None, linkedin_password=None,
                    batch_size=DEFAULT_BATCH_SIZE):
    """Scrape LinkedIn contact info for Justin's contacts missing email."""
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("LINKEDIN SCRAPE: Find emails for contacts (ranked by ask_readiness)")
    print("=" * 60)
    print(f"  Safety settings:")
    print(f"    Batch size: {batch_size} profiles max")
    print(f"    Delay: {MIN_DELAY}-{MAX_DELAY}s between profiles")
    print(f"    Break every {BREAK_EVERY} profiles: {BREAK_MIN//60}-{BREAK_MAX//60} min")
    print(f"    Rate limit pause: {RATE_LIMIT_PAUSE}s")
    print(f"    Auth wall: {'abort immediately' if AUTH_WALL_ABORT else 'pause and retry'}")
    print(f"    Circuit breaker: {MAX_CONSECUTIVE_ERRORS} consecutive errors")
    print()

    if not linkedin_email or not linkedin_password:
        print("  ERROR: LinkedIn credentials required")
        print("  Usage: --linkedin-email EMAIL --linkedin-password PASS")
        return 0

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Get contacts missing email, ranked by ask_readiness score
    cur.execute("""
        SELECT c.id, c.first_name, c.last_name, c.linkedin_url,
               c.company, c.position, c.enrich_current_company, c.enrich_current_title,
               c.ask_readiness->'outdoorithm_fundraising'->>'tier' as ar_tier,
               (c.ask_readiness->'outdoorithm_fundraising'->>'score')::int as ar_score
        FROM contacts c
        WHERE (c.email IS NULL AND c.email_2 IS NULL AND c.work_email IS NULL AND c.personal_email IS NULL)
          AND c.linkedin_url IS NOT NULL AND c.linkedin_url != ''
          AND c.ask_readiness IS NOT NULL
          AND c.ask_readiness->'outdoorithm_fundraising' IS NOT NULL
        ORDER BY
          CASE c.ask_readiness->'outdoorithm_fundraising'->>'tier'
            WHEN 'ready_now' THEN 1
            WHEN 'cultivate_first' THEN 2
            WHEN 'long_term' THEN 3
            ELSE 4
          END,
          (c.ask_readiness->'outdoorithm_fundraising'->>'score')::int DESC NULLS LAST
    """)
    contacts = cur.fetchall()

    # Apply batch cap
    effective_limit = min(len(contacts), batch_size)
    contacts = contacts[:effective_limit]
    total = len(contacts)

    print(f"  Found {total} contacts to scrape (batch capped at {effective_limit})")
    if total > 0:
        tiers = {}
        for c in contacts:
            t = c["ar_tier"] or "unknown"
            tiers[t] = tiers.get(t, 0) + 1
        for t, cnt in sorted(tiers.items()):
            print(f"    {t}: {cnt}")
    print()

    if total == 0:
        return 0

    stats = {"found": 0, "no_email": 0, "errors": 0, "rate_limited": 0,
             "consecutive_errors": 0, "classified": 0}
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

        # Anti-detection
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)

        page = context.new_page()

        # Try cookie reuse
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

            # Human-like typing
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

            # Security checkpoint — give user plenty of time
            if "checkpoint" in page.url or "challenge" in page.url:
                print("  !! SECURITY CHECKPOINT detected !!")
                print("  Please complete the verification in the browser window.")
                print("  Waiting up to 5 minutes...")
                for tick in range(60):  # 5 minutes (60 x 5s)
                    time.sleep(5)
                    try:
                        current = page.url
                    except Exception:
                        # Page may be navigating — wait and retry
                        time.sleep(2)
                        try:
                            current = page.url
                        except Exception:
                            continue
                    # Check URL-based success signals (safe, no DOM access)
                    if "/feed" in current or "/mynetwork" in current or "/messaging" in current:
                        print("  Checkpoint resolved — redirected to feed!")
                        break
                    if "checkpoint" not in current and "challenge" not in current and "login" not in current:
                        print(f"  Checkpoint resolved — URL changed to: {current}")
                        break
                    # Try DOM check, but catch navigation errors
                    try:
                        if page.query_selector("nav.global-nav"):
                            print("  Checkpoint resolved — nav detected!")
                            break
                    except Exception:
                        pass  # Page is navigating, that's fine
                    if tick % 6 == 5:
                        print(f"    Still waiting... ({(tick+1)*5}s)")
                else:
                    print("  Checkpoint not resolved after 5 minutes. ABORTING.")
                    browser.close()
                    return 0

            # Wait for page to stabilize after login/checkpoint
            time.sleep(3)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass

            # Final login check
            def _is_logged_in():
                try:
                    url = page.url
                    if "/feed" in url or "/mynetwork" in url or "/messaging" in url:
                        return True
                    return bool(page.query_selector("nav.global-nav"))
                except Exception:
                    return False

            if _is_logged_in():
                print("  Logged in successfully")
                _save_cookies(context)
            else:
                print(f"  Post-login URL: {page.url}")
                print("  Waiting up to 60s for redirect...")
                for _ in range(12):
                    time.sleep(5)
                    if _is_logged_in():
                        print("  Login confirmed!")
                        break
                else:
                    print("  ABORTING — cannot confirm login.")
                    browser.close()
                    return 0
                _save_cookies(context)

        print(f"  Starting scrape of {total} contacts.\n")

        # Browse feed first (look natural)
        _simulate_human_behavior(page)
        time.sleep(random.uniform(3, 6))

        for i, contact in enumerate(contacts):
            cid = contact["id"]
            first = contact["first_name"] or ""
            last = contact["last_name"] or ""
            name = f"{first} {last}".strip()
            ar_tier = contact["ar_tier"] or "?"
            ar_score = contact["ar_score"] or "?"
            linkedin_url = contact["linkedin_url"].rstrip("/")
            contact_info_url = f"{linkedin_url}/overlay/contact-info/"

            # Circuit breaker
            if stats["consecutive_errors"] >= MAX_CONSECUTIVE_ERRORS:
                print(f"\n  !! CIRCUIT BREAKER: {MAX_CONSECUTIVE_ERRORS} consecutive errors !!")
                print(f"  STOPPING to protect Justin's account. Resume later.")
                break

            # Session break
            if i > 0 and i % BREAK_EVERY == 0:
                break_duration = random.uniform(BREAK_MIN, BREAK_MAX)
                elapsed = time.time() - start_time
                print(f"\n  === SESSION BREAK ({break_duration/60:.1f} min) after {i} profiles ===")
                print(f"  Stats: {stats['found']} found, {stats['no_email']} no email, "
                      f"{stats['errors']} errors [{elapsed:.0f}s elapsed]")

                _save_cookies(context)
                time.sleep(break_duration)

                # Post-break: visit feed
                try:
                    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
                    time.sleep(random.uniform(3, 6))
                    _simulate_human_behavior(page)
                    time.sleep(random.uniform(2, 4))
                except Exception:
                    pass

            try:
                page.goto(contact_info_url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(random.uniform(2, 4))
                _simulate_human_behavior(page)

                # Auth wall check
                current_url = page.url
                if "authwall" in current_url or current_url.startswith("https://www.linkedin.com/login"):
                    stats["rate_limited"] += 1
                    if AUTH_WALL_ABORT:
                        print(f"\n  !! AUTH WALL at profile {i+1} — ABORTING !!")
                        _save_cookies(context)
                        break

                # 404 / restricted
                if "/404" in current_url or "unavailable" in (page.title() or "").lower():
                    stats["errors"] += 1
                    stats["consecutive_errors"] += 1
                    continue

                # Extract email
                found_email = None

                # Method 1: mailto links
                mailto_links = page.query_selector_all('a[href^="mailto:"]')
                for link in mailto_links:
                    href = link.get_attribute("href") or ""
                    addr = href.replace("mailto:", "").lower().strip()
                    if addr and "@" in addr and not is_skip_email(addr):
                        found_email = addr
                        break

                # Method 2: email section
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
                    # Classify email type
                    email_type = classify_email_type(found_email)
                    if email_type == "unknown":
                        email_type = _classify_with_llm(openai_client, contact, found_email)

                    marker = "[DRY-RUN] " if dry_run else ""
                    print(f"  {marker}[{cid}] {name} ({ar_tier}/{ar_score}): "
                          f"{found_email} [{email_type}]")

                    if not dry_run:
                        _save_email(cur, conn, cid, found_email, email_type)
                    stats["found"] += 1
                    stats["classified"] += 1
                else:
                    stats["no_email"] += 1

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

            _human_delay()

            # Progress
            if (i + 1) % 10 == 0:
                elapsed = time.time() - start_time
                remaining = total - (i + 1)
                est_remaining = remaining * (elapsed / (i + 1)) if i > 0 else 0
                print(f"\n  --- {i+1}/{total} ({stats['found']} found, "
                      f"{stats['no_email']} none, {stats['errors']} err, "
                      f"{stats['rate_limited']} rl) "
                      f"[{elapsed/60:.0f}min elapsed, ~{est_remaining/60:.0f}min remaining] ---\n")

        _save_cookies(context)
        browser.close()

    elapsed = time.time() - start_time
    profiles_checked = min(i + 1, total) if total > 0 else 0
    print(f"\n  Scrape results ({profiles_checked} profiles):")
    print(f"    Emails found:    {stats['found']}")
    print(f"    No email:        {stats['no_email']}")
    print(f"    Errors:          {stats['errors']}")
    print(f"    Rate limits:     {stats['rate_limited']}")
    print(f"    Time:            {elapsed/60:.1f}min ({elapsed/max(profiles_checked,1):.1f}s/profile)")
    return stats["found"]


# ── Email Classification ─────────────────────────────────────────────

def _classify_with_llm(openai_client, contact, email_addr):
    """Use GPT-5 mini to classify an email as personal or work."""
    first = contact.get("first_name") or contact.get("first_name", "")
    last = contact.get("last_name") or contact.get("last_name", "")
    name = f"{first} {last}".strip()
    company = (contact.get("company") or contact.get("enrich_current_company")
               or contact.get("current_company") or "unknown")
    title = (contact.get("position") or contact.get("enrich_current_title")
             or contact.get("current_title") or "unknown")
    domain = email_addr.split("@")[1] if "@" in email_addr else ""

    prompt = (
        f"Classify this email as personal or work.\n\n"
        f"PERSON: {name}\n"
        f"  Company: {company}\n"
        f"  Title: {title}\n\n"
        f"EMAIL: {email_addr}\n"
        f"  Domain: {domain}\n\n"
        f"RULES:\n"
        f"- gmail.com, yahoo.com, hotmail.com, outlook.com, icloud.com, aol.com, "
        f"comcast.net, me.com, protonmail.com, live.com = PERSONAL\n"
        f"- If domain matches or relates to their company = WORK\n"
        f"- .edu domains = WORK (academic)\n"
        f"- .org domains = usually WORK unless clearly personal\n"
        f"- Custom vanity domains (person's name) = PERSONAL\n"
        f"- When unsure, lean toward WORK for corporate domains, PERSONAL for ISP domains"
    )

    try:
        resp = openai_client.responses.parse(
            model="gpt-5-mini",
            instructions="You classify emails. Be accurate and concise. Return only personal or work.",
            input=prompt,
            text_format=EmailClassification,
        )
        result = resp.output_parsed
        return result.email_type if result else "personal"
    except Exception as e:
        print(f"    LLM classify error: {e}")
        # Fallback: if domain looks corporate, say work
        if domain and domain not in PERSONAL_DOMAINS:
            return "work"
        return "personal"


def _save_email(cur, conn, contact_id, email_addr, email_type):
    """Save email to the right field(s) based on classification."""
    if email_type == "personal":
        cur.execute("""
            UPDATE contacts SET
                personal_email = COALESCE(personal_email, %s),
                email = COALESCE(email, %s)
            WHERE id = %s
        """, (email_addr, email_addr, contact_id))
    elif email_type == "work":
        cur.execute("""
            UPDATE contacts SET
                work_email = COALESCE(work_email, %s),
                email = COALESCE(email, %s)
            WHERE id = %s
        """, (email_addr, email_addr, contact_id))
    else:
        cur.execute("""
            UPDATE contacts SET email = COALESCE(email, %s) WHERE id = %s
        """, (email_addr, contact_id))
    conn.commit()


def classify_campaign_emails(conn, openai_client, dry_run=False, new_only=False):
    """Classify existing campaign emails as personal/work using GPT-5 mini."""
    print("\n" + "=" * 60)
    print("CLASSIFY: Campaign contact emails → personal/work")
    print("=" * 60)

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if new_only:
        # Only contacts that have email but no personal/work classification
        cur.execute("""
            SELECT id, first_name, last_name, email, email_2,
                   company, position, enrich_current_company, enrich_current_title,
                   personal_email, work_email
            FROM contacts
            WHERE campaign_2026 IS NOT NULL
              AND campaign_2026->'scaffold' IS NOT NULL
              AND (email IS NOT NULL OR email_2 IS NOT NULL)
              AND personal_email IS NULL AND work_email IS NULL
        """)
    else:
        # All campaign contacts with any email
        cur.execute("""
            SELECT id, first_name, last_name, email, email_2,
                   company, position, enrich_current_company, enrich_current_title,
                   personal_email, work_email
            FROM contacts
            WHERE campaign_2026 IS NOT NULL
              AND campaign_2026->'scaffold' IS NOT NULL
              AND (email IS NOT NULL OR email_2 IS NOT NULL)
        """)

    contacts = cur.fetchall()
    total = len(contacts)
    print(f"  Found {total} campaign contacts to classify\n")

    if total == 0:
        print("  Nothing to classify.")
        return 0

    stats = {"classified": 0, "already_done": 0, "errors": 0}

    # Prepare batch for concurrent GPT-5 mini calls
    tasks = []
    for contact in contacts:
        cid = contact["id"]
        emails_to_classify = []

        # Collect all emails that need classification
        for field in ["email", "email_2"]:
            addr = contact[field]
            if addr and "@" in addr and not is_skip_email(addr):
                emails_to_classify.append((field, addr))

        if not emails_to_classify:
            continue

        # Check if already fully classified
        has_personal = contact["personal_email"] is not None
        has_work = contact["work_email"] is not None
        if has_personal and has_work:
            stats["already_done"] += 1
            continue

        tasks.append((contact, emails_to_classify))

    print(f"  {len(tasks)} contacts need classification, {stats['already_done']} already done\n")

    def _classify_one(task):
        contact, emails = task
        cid = contact["id"]
        first = contact["first_name"] or ""
        last = contact["last_name"] or ""
        name = f"{first} {last}".strip()
        results = []

        for field, addr in emails:
            # Quick heuristic first
            etype = classify_email_type(addr)
            if etype == "unknown":
                etype = _classify_with_llm(openai_client, dict(contact), addr)
            results.append((field, addr, etype))

        return cid, name, results

    # Run with concurrency (respect GPT-5 mini rate limits)
    classified = 0
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(_classify_one, t): t for t in tasks}

        for future in as_completed(futures):
            try:
                cid, name, results = future.result()

                personal_addr = None
                work_addr = None

                for field, addr, etype in results:
                    if etype == "personal" and not personal_addr:
                        personal_addr = addr
                    elif etype == "work" and not work_addr:
                        work_addr = addr

                marker = "[DRY-RUN] " if dry_run else ""
                parts = []
                if personal_addr:
                    parts.append(f"personal={personal_addr}")
                if work_addr:
                    parts.append(f"work={work_addr}")
                print(f"  {marker}[{cid}] {name}: {', '.join(parts)}")

                if not dry_run:
                    updates = []
                    params = []
                    if personal_addr:
                        updates.append("personal_email = COALESCE(personal_email, %s)")
                        params.append(personal_addr)
                    if work_addr:
                        updates.append("work_email = COALESCE(work_email, %s)")
                        params.append(work_addr)

                    if updates:
                        params.append(cid)
                        cur.execute(
                            f"UPDATE contacts SET {', '.join(updates)} WHERE id = %s",
                            params
                        )
                        conn.commit()

                classified += 1
                stats["classified"] += 1

                if classified % 50 == 0:
                    print(f"\n  --- {classified}/{len(tasks)} classified ---\n")

            except Exception as e:
                stats["errors"] += 1
                if stats["errors"] <= 5:
                    print(f"  Classification error: {e}")

    print(f"\n  Classification results:")
    print(f"    Classified:    {stats['classified']}")
    print(f"    Already done:  {stats['already_done']}")
    print(f"    Errors:        {stats['errors']}")
    return stats["classified"]


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Justin's LinkedIn Email Discovery + Classification")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape LinkedIn for missing emails")
    scrape_parser.add_argument("--linkedin-email", type=str, required=True)
    scrape_parser.add_argument("--linkedin-password", type=str, required=True)
    scrape_parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    scrape_parser.add_argument("--headless", action="store_true")
    scrape_parser.add_argument("--dry-run", "-d", action="store_true")

    # Classify command
    classify_parser = subparsers.add_parser("classify", help="Classify campaign emails as personal/work")
    classify_parser.add_argument("--new-only", action="store_true",
                                  help="Only classify contacts with no personal/work email set")
    classify_parser.add_argument("--dry-run", "-d", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    conn = get_db_conn()
    openai_client = OpenAI(api_key=os.environ["OPENAI_APIKEY"])
    print("Connected to database")

    # Current stats
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM contacts")
    total = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM contacts WHERE email IS NOT NULL")
    has_email = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM contacts WHERE personal_email IS NOT NULL")
    has_personal = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM contacts WHERE work_email IS NOT NULL")
    has_work = cur.fetchone()[0]
    print(f"  Current: {has_email}/{total} have email, "
          f"{has_personal} personal, {has_work} work\n")

    if args.command == "scrape":
        found = scrape_linkedin(
            conn, openai_client,
            dry_run=args.dry_run,
            headless=args.headless,
            linkedin_email=args.linkedin_email,
            linkedin_password=args.linkedin_password,
            batch_size=args.batch_size,
        )

    elif args.command == "classify":
        found = classify_campaign_emails(
            conn, openai_client,
            dry_run=args.dry_run,
            new_only=args.new_only,
        )

    # Final stats
    cur.execute("SELECT count(*) FROM contacts WHERE email IS NOT NULL")
    new_email = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM contacts WHERE personal_email IS NOT NULL")
    new_personal = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM contacts WHERE work_email IS NOT NULL")
    new_work = cur.fetchone()[0]
    print(f"\n{'=' * 60}")
    print(f"FINAL: {new_email}/{total} have email (+{new_email - has_email})")
    print(f"  Personal: {new_personal} (+{new_personal - has_personal})")
    print(f"  Work: {new_work} (+{new_work - has_work})")
    print(f"{'=' * 60}")

    conn.close()


if __name__ == "__main__":
    main()
