#!/usr/bin/env python3
"""
Network Intelligence — Email Discovery v2

Two-phase approach:
  Phase 1: Extract emails from existing contact_email_threads participants (fast, no API)
  Phase 2: Search Gmail across 5 accounts for remaining contacts (slower, API-based)
  Phase 3: Re-check bounced emails (email_verified = false)

Usage:
  python scripts/intelligence/discover_emails_v2.py --phase 1          # Thread extraction only
  python scripts/intelligence/discover_emails_v2.py --phase 2          # Gmail search only
  python scripts/intelligence/discover_emails_v2.py --phase 3          # Bounced email check
  python scripts/intelligence/discover_emails_v2.py                    # All phases
  python scripts/intelligence/discover_emails_v2.py --dry-run          # Don't write
  python scripts/intelligence/discover_emails_v2.py --phase 2 -n 50   # First 50 only
"""

import os
import sys
import json
import time
import re
import email.utils
import argparse
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from pydantic import BaseModel, Field
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────

GOOGLE_ACCOUNTS = [
    "justinrsteele@gmail.com",
    "justin@truesteele.com",
    "justin@kindora.co",
    "justin@outdoorithmcollective.org",
    "justin@outdoorithm.com",
]

CREDENTIALS_DIR = os.path.expanduser("~/.google_workspace_mcp/credentials")

JUSTIN_EMAILS = {
    "justinrsteele@gmail.com",
    "justin@truesteele.com",
    "justin@outdoorithm.com",
    "justin@outdoorithmcollective.org",
    "justin@kindora.co",
    "jsteele@google.com",
    "justinsteele@google.com",
    "justin.steele@google.com",
    "jsteele@mba2009.hbs.edu",
    "jsteele@mba2010.hbs.edu",
}

SKIP_EMAIL_PATTERNS = [
    r"noreply@", r"no-reply@", r"notifications@", r"notify@",
    r"mailer-daemon@", r"postmaster@", r"bounce@", r"donotreply@",
    r".*@googlegroups\.com$", r".*@groups\.google\.com$",
    r".*@calendar\.google\.com$", r".*@docs\.google\.com$",
    r".*@linkedin\.com$", r".*@facebookmail\.com$",
    r".*@vercel\.com$", r".*@github\.com$",
    r".*@mailchimp\.com$", r".*@sendgrid\.net$",
    # Service emails that relay with the sender's display name
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
    if addr in JUSTIN_EMAILS:
        return True
    if not addr or "@" not in addr:
        return True
    for pattern in SKIP_EMAIL_PATTERNS:
        if re.match(pattern, addr):
            return True
    return False


def name_in_email(first: str, last: str, addr: str) -> float:
    """Score how well a contact name matches an email address. Returns 0-1."""
    first = first.lower().strip().split()[0] if first else ""  # first word only
    last = last.lower().strip().split(",")[0].split()[0] if last else ""  # clean suffixes
    addr_lower = addr.lower()
    local = addr_lower.split("@")[0] if "@" in addr_lower else ""

    if not first or not last:
        return 0.0

    # Full name in local part: jsteele, steelej, justin.steele, etc
    if first in local and last in local:
        return 1.0
    # Last name + first initial
    if last in local and first[0] in local:
        return 0.7
    # Just last name (if distinctive enough)
    if last in local and len(last) > 4:
        return 0.5
    # First name only (weak)
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
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# ── Phase 1: Extract from existing thread participants ────────────────

def phase1_extract_from_threads(conn, dry_run=False):
    """Extract emails from contact_email_threads participants for contacts missing email."""
    print("\n" + "=" * 60)
    print("PHASE 1: Extract emails from existing thread participants")
    print("=" * 60)

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Get contacts missing email that have email threads
    cur.execute("""
        SELECT DISTINCT c.id, c.first_name, c.last_name, c.company, c.headline
        FROM contacts c
        JOIN contact_email_threads t ON t.contact_id = c.id
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

        # Get all participants from this contact's non-group threads
        cur.execute("""
            SELECT participants, subject, is_group, participant_count
            FROM contact_email_threads
            WHERE contact_id = %s AND channel = 'email'
            ORDER BY participant_count ASC, last_message_date DESC
        """, (cid,))
        threads = cur.fetchall()

        # Collect candidate emails across all threads
        candidates = {}  # email -> score

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

                # Score this candidate
                email_score = name_in_email(first, last, addr)
                display_score = name_matches_display(first, last, display)
                best_score = max(email_score, display_score)

                # For small threads (1:1 or 3-way), boost non-Justin emails
                if pcount <= 3 and not is_group and best_score >= 0.3:
                    best_score = max(best_score, 0.6)

                if best_score >= 0.3:
                    if addr not in candidates or candidates[addr] < best_score:
                        candidates[addr] = best_score

        if not candidates:
            skipped += 1
            continue

        # Pick the best candidate
        best_email = max(candidates, key=candidates.get)
        best_score = candidates[best_email]

        if best_score >= 0.5:
            marker = "[DRY-RUN] " if dry_run else ""
            print(f"  {marker}[{cid}] {name}: {best_email} (score={best_score:.1f})")

            if not dry_run:
                cur.execute(
                    "UPDATE contacts SET email = %s WHERE id = %s AND (email IS NULL OR email = '')",
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
    """Search Gmail for emails of contacts still missing them."""
    print("\n" + "=" * 60)
    print("PHASE 2: Search Gmail for remaining missing emails")
    print("=" * 60)

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Get contacts still missing email, ordered by proximity score
    cur.execute("""
        SELECT id, first_name, last_name, company, position, headline, linkedin_url,
               enrich_current_company, enrich_current_title,
               ai_proximity_score, ai_proximity_tier
        FROM contacts
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

    for i, contact in enumerate(contacts):
        cid = contact["id"]
        first = contact["first_name"] or ""
        last = contact["last_name"] or ""
        name = f"{first} {last}".strip()
        company = contact["company"] or contact["enrich_current_company"] or ""
        prox = contact["ai_proximity_score"] or "?"

        # Search across all Gmail accounts
        candidates = {}
        query = f'"{first} {last}"'

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

        # Pick best candidate by score
        PERSONAL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                            "icloud.com", "me.com", "aol.com", "comcast.net", "protonmail.com"}
        scored = []
        for addr, info in candidates.items():
            score = info["name_score"] * 50
            score += min(info["thread_count"] * 3, 15)
            score += min(len(info["accounts"]) * 5, 15)
            domain = addr.split("@")[1] if "@" in addr else ""
            is_personal = domain in PERSONAL_DOMAINS
            # Company domain bonus
            if company:
                comp_lower = company.lower().replace(" ", "").replace(",", "")
                if len(comp_lower) > 3 and comp_lower[:4] in domain:
                    score += 20
                elif not is_personal and domain:
                    # Corporate email that doesn't match current company = likely stale
                    # Force LLM review by capping score below auto-accept
                    score = min(score, 60)
            # Personal email domains get a slight boost (more durable)
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

        # LLM verification for non-obvious matches (score < 65)
        if best_score < 65:
            verification = _verify_with_llm(openai_client, contact, best_email, best_info)
            if not verification or not verification.is_match or verification.confidence < 70:
                stats["skipped"] += 1
                reason = verification.reasoning if verification else "LLM error"
                print(f"  [{cid}] {name} ({prox}): SKIP {best_email} - {reason}")
                if (i + 1) % 100 == 0:
                    _print_progress(i + 1, total, stats, start_time)
                continue

        # Save it
        marker = "[DRY-RUN] " if dry_run else ""
        print(f"  {marker}[{cid}] {name} ({company}, prox={prox}): FOUND {best_email} "
              f"(score={best_score:.0f}, threads={best_info['thread_count']}, "
              f"accts={len(best_info['accounts'])})")

        if not dry_run:
            cur.execute(
                "UPDATE contacts SET email = %s WHERE id = %s AND (email IS NULL OR email = '')",
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
        f"- REJECT service/relay emails (paperlesspost, evite, eventbrite, etc.) even if display name matches\n"
        f"- REJECT corporate emails (@company.com) if the person no longer works there\n"
        f"  (e.g. @google.com for someone now at a different company)\n"
        f"- ACCEPT personal emails (gmail, yahoo, etc.) with good name match even if old\n"
        f"- For common names (John, Michael, David, etc.) require 3+ threads or multiple accounts\n"
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


# ── Phase 3: Re-check bounced emails ─────────────────────────────────

def phase3_check_bounced(conn, gmail_services, dry_run=False):
    """Re-check contacts with email_verified=false by searching Gmail."""
    print("\n" + "=" * 60)
    print("PHASE 3: Re-check bounced/unverified emails")
    print("=" * 60)

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT id, first_name, last_name, email, company, position, headline,
               email_verification_source, enrich_current_company
        FROM contacts
        WHERE email_verified = false
        ORDER BY last_name
    """)
    contacts = cur.fetchall()
    print(f"  Found {len(contacts)} contacts with bounced emails\n")

    found_alt = 0

    for contact in contacts:
        cid = contact["id"]
        first = contact["first_name"] or ""
        last = contact["last_name"] or ""
        name = f"{first} {last}".strip()
        old_email = contact["email"] or "(none)"

        # Search Gmail for alternative emails
        candidates = {}
        for acct, svc in gmail_services.items():
            try:
                _search_gmail_account(svc, acct, first, last, candidates)
            except Exception as e:
                continue
            time.sleep(0.05)

        # Filter out the known-bad email
        if old_email.lower() in candidates:
            del candidates[old_email.lower()]

        if not candidates:
            print(f"  [{cid}] {name}: bounced={old_email}, no alternatives found")
            continue

        # Pick best alternative
        scored = []
        for addr, info in candidates.items():
            score = info["name_score"] * 50 + min(info["thread_count"] * 3, 15)
            scored.append((addr, score, info))
        scored.sort(key=lambda x: x[1], reverse=True)

        best_email, best_score, best_info = scored[0]
        if best_score >= 35:
            marker = "[DRY-RUN] " if dry_run else ""
            print(f"  {marker}[{cid}] {name}: bounced={old_email} -> NEW {best_email} "
                  f"(score={best_score:.0f})")

            if not dry_run:
                cur.execute(
                    "UPDATE contacts SET email = %s, email_verified = NULL WHERE id = %s",
                    (best_email, cid)
                )
                conn.commit()
            found_alt += 1
        else:
            print(f"  [{cid}] {name}: bounced={old_email}, best alt={best_email} "
                  f"(score={best_score:.0f}, too low)")

    print(f"\n  Phase 3 results: {found_alt} bounced emails replaced")
    return found_alt


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Email Discovery v2")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3],
                        help="Run specific phase only (default: all)")
    parser.add_argument("--dry-run", "-d", action="store_true")
    parser.add_argument("--limit", "-n", type=int, default=None,
                        help="Limit contacts to process (phase 2)")
    args = parser.parse_args()

    run_phase1 = args.phase is None or args.phase == 1
    run_phase2 = args.phase is None or args.phase == 2
    run_phase3 = args.phase is None or args.phase == 3

    conn = get_db_conn()
    print("Connected to Supabase")

    # Load Gmail services
    gmail_services = {}
    for acct in GOOGLE_ACCOUNTS:
        svc = load_gmail_service(acct)
        if svc:
            gmail_services[acct] = svc
            print(f"  Gmail: {acct} OK")
        else:
            print(f"  Gmail: {acct} SKIPPED")

    openai_client = None
    if run_phase2:
        openai_client = OpenAI(api_key=os.environ["OPENAI_APIKEY"])
        print("  OpenAI: connected")

    total_found = 0
    start = time.time()

    if run_phase1:
        total_found += phase1_extract_from_threads(conn, dry_run=args.dry_run)

    if run_phase2:
        if not gmail_services:
            print("ERROR: No Gmail services for phase 2")
        else:
            total_found += phase2_gmail_search(
                conn, openai_client, gmail_services,
                dry_run=args.dry_run, limit=args.limit
            )

    if run_phase3:
        if not gmail_services:
            print("ERROR: No Gmail services for phase 3")
        else:
            total_found += phase3_check_bounced(conn, gmail_services, dry_run=args.dry_run)

    # Final count
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM contacts WHERE email IS NULL OR email = ''")
    remaining = cur.fetchone()[0]

    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"  Emails discovered this run:  {total_found}")
    print(f"  Still missing email:         {remaining}")
    print(f"  Total time:                  {elapsed:.0f}s")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
