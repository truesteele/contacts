#!/usr/bin/env python3
"""
Network Intelligence — Email Discovery via Gmail Search

For contacts without email addresses, searches Justin's 5 Gmail accounts by name
to discover their email. Uses multi-signal verification to avoid false matches.

Verification signals:
  1. Name match in email headers (From/To display name)
  2. Company domain match (contact's company → email domain)
  3. Thread context (does the email context match this person's role/company?)
  4. LLM verification (GPT-5 mini cross-references candidate email against contact profile)

Only high-confidence matches are stored.

Usage:
  python scripts/intelligence/discover_emails.py --test -n 5        # 5 contacts
  python scripts/intelligence/discover_emails.py --dry-run           # Search only, don't write
  python scripts/intelligence/discover_emails.py --min-confidence 90 # Strict threshold
  python scripts/intelligence/discover_emails.py                     # Full run
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

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from pydantic import BaseModel, Field
from supabase import create_client, Client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────

GOOGLE_ACCOUNTS = [
    "justinrsteele@gmail.com",
    "justin@truesteele.com",
    "justin@outdoorithm.com",
    "justin@outdoorithmcollective.org",
    "justin@kindora.co",
]

CREDENTIALS_DIR = os.path.expanduser("~/.google_workspace_mcp/credentials")

# Justin's own emails — exclude these from candidate discovery
JUSTIN_EMAILS = {
    "justinrsteele@gmail.com",
    "justin@truesteele.com",
    "justin@outdoorithm.com",
    "justin@outdoorithmcollective.org",
    "justin@kindora.co",
    "jsteele@google.com",
    "justinsteele@google.com",
    "justin.steele@google.com",
}

# Skip service/noreply addresses
SKIP_DOMAINS = {
    "noreply", "no-reply", "notifications", "mailer-daemon",
    "postmaster", "bounce", "donotreply", "auto-reply",
}

SKIP_EMAIL_PATTERNS = [
    r"noreply@", r"no-reply@", r"notifications@", r"notify@",
    r"mailer-daemon@", r"postmaster@", r"bounce@",
    r".*@googlegroups\.com$", r".*@groups\.google\.com$",
    r".*@calendar\.google\.com$", r".*@docs\.google\.com$",
    r".*@linkedin\.com$", r".*@facebookmail\.com$",
]

DEFAULT_CONFIDENCE_THRESHOLD = 80

# ── Pydantic Schema for LLM Verification ──────────────────────────────

class EmailVerification(BaseModel):
    is_match: bool = Field(description="Is this email likely the contact's actual email?")
    confidence: int = Field(ge=0, le=100, description="0-100 confidence score")
    reasoning: str = Field(description="Brief explanation of why this is or isn't a match")
    email_type: str = Field(description="personal | work | unknown")


# ── Gmail Helpers ─────────────────────────────────────────────────────

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


def is_skip_email(addr: str) -> bool:
    """Check if an email should be skipped (service, noreply, Justin's own)."""
    addr = addr.lower().strip()
    if addr in JUSTIN_EMAILS:
        return True
    local = addr.split("@")[0] if "@" in addr else ""
    if local in SKIP_DOMAINS:
        return True
    for pattern in SKIP_EMAIL_PATTERNS:
        if re.match(pattern, addr):
            return True
    return False


def extract_domain(email_addr: str) -> str:
    """Extract domain from email address."""
    if "@" in email_addr:
        return email_addr.split("@")[1].lower()
    return ""


def normalize_company_for_domain(company: str) -> list[str]:
    """Generate possible email domain fragments from a company name."""
    if not company:
        return []
    company = company.lower().strip()
    # Remove common suffixes
    for suffix in [", inc.", ", inc", " inc.", " inc", ", llc", " llc",
                   ", ltd", " ltd", " corp", " corporation", " co.",
                   " foundation", " fund", " group", " consulting"]:
        company = company.replace(suffix, "")
    company = company.strip()
    # Generate domain fragments
    fragments = [company.replace(" ", "")]  # "goldman sachs" -> "goldmansachs"
    fragments.append(company.replace(" ", "-"))  # "goldman-sachs"
    parts = company.split()
    if len(parts) > 1:
        fragments.append(parts[0])  # First word: "goldman"
        fragments.append("".join(p[0] for p in parts))  # Initials: "gs"
    return [f for f in fragments if len(f) > 2]


def name_matches_email(first_name: str, last_name: str, display_name: str) -> float:
    """Score how well a contact's name matches an email display name. Returns 0-1."""
    if not display_name:
        return 0.0

    first = first_name.lower().strip()
    last = last_name.lower().strip()
    display = display_name.lower().strip()

    # Exact match
    full = f"{first} {last}"
    if full == display:
        return 1.0

    # Last, First format
    if f"{last}, {first}" == display:
        return 1.0
    if f"{last} {first}" == display:
        return 0.95

    # First name + last name both present
    if first in display and last in display:
        return 0.9

    # Last name + first initial
    if last in display and display.startswith(first[0]):
        return 0.7

    # Just last name (weaker signal)
    if last in display and len(last) > 3:
        return 0.4

    return 0.0


# ── Main Class ────────────────────────────────────────────────────────

class EmailDiscoverer:
    MODEL = "gpt-5-mini"

    SELECT_COLS = (
        "id, first_name, last_name, company, position, headline, "
        "email, work_email, personal_email, email_2, "
        "linkedin_url, ai_proximity_score, ai_proximity_tier, "
        "enrich_employment, enrich_current_company, enrich_current_title"
    )

    def __init__(self, test_mode=False, test_count=5, dry_run=False,
                 min_confidence=DEFAULT_CONFIDENCE_THRESHOLD):
        self.test_mode = test_mode
        self.test_count = test_count
        self.dry_run = dry_run
        self.min_confidence = min_confidence
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.gmail_services: dict = {}
        self.stats = {
            "contacts_searched": 0,
            "emails_found": 0,
            "high_confidence": 0,
            "low_confidence_skipped": 0,
            "no_candidates": 0,
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

        for acct in GOOGLE_ACCOUNTS:
            svc = load_gmail_service(acct)
            if svc:
                self.gmail_services[acct] = svc
                print(f"  Gmail: {acct} OK")
            else:
                print(f"  Gmail: {acct} SKIPPED")

        if not self.gmail_services:
            print("ERROR: No Gmail services available")
            return False

        print(f"Connected: Supabase, {len(self.gmail_services)} Gmail accounts, OpenAI")
        return True

    def get_contacts_without_email(self) -> list[dict]:
        """Fetch contacts that have no email address."""
        all_contacts = []
        page_size = 1000
        offset = 0

        while True:
            # Get contacts where all email fields are null/empty
            result = (
                self.supabase.table("contacts")
                .select(self.SELECT_COLS)
                .or_("email.is.null,email.eq.")
                .or_("work_email.is.null,work_email.eq.")
                .or_("personal_email.is.null,personal_email.eq.")
                .or_("email_2.is.null,email_2.eq.")
                .order("ai_proximity_score", desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
            ).data

            if not result:
                break

            # Double-check: only keep contacts with truly no emails
            for c in result:
                has_email = False
                for field in ("email", "work_email", "personal_email", "email_2"):
                    val = c.get(field)
                    if val and isinstance(val, str) and val.strip() and "@" in val:
                        has_email = True
                        break
                if not has_email:
                    all_contacts.append(c)

            if len(result) < page_size:
                break
            offset += page_size

        if self.test_mode:
            all_contacts = all_contacts[:self.test_count]

        return all_contacts

    def search_for_email(self, contact: dict) -> Optional[dict]:
        """Search Gmail for a contact's email. Returns best candidate or None."""
        first = contact.get("first_name", "").strip()
        last = contact.get("last_name", "").strip()
        company = contact.get("company") or contact.get("enrich_current_company") or ""

        if not first or not last:
            return None

        # Search query: exact name match
        query = f'"{first} {last}"'

        # Collect candidate emails from all accounts
        candidates = {}  # email -> {score, display_name, context, account, thread_count}

        for acct, svc in self.gmail_services.items():
            try:
                self._search_account_for_name(
                    svc, acct, first, last, company, candidates
                )
            except Exception as e:
                print(f"    Error searching {acct}: {e}")
                self.stats["errors"] += 1
            time.sleep(0.05)

        if not candidates:
            return None

        # Score and rank candidates
        company_domains = normalize_company_for_domain(company)
        scored = []

        for addr, info in candidates.items():
            score = info["name_score"] * 50  # Name match: up to 50 points

            # Company domain match: up to 30 points
            domain = extract_domain(addr)
            domain_match = False
            for frag in company_domains:
                if frag in domain:
                    score += 30
                    domain_match = True
                    break

            # Thread count: up to 10 points
            score += min(info["thread_count"] * 2, 10)

            # Multi-account appearance: up to 10 points
            score += min(len(info["accounts"]) * 5, 10)

            scored.append({
                "email": addr,
                "score": score,
                "name_score": info["name_score"],
                "display_name": info["display_name"],
                "domain_match": domain_match,
                "thread_count": info["thread_count"],
                "accounts": info["accounts"],
                "context_snippets": info["context_snippets"][:3],
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[0] if scored else None

    def _search_account_for_name(self, service, account_email: str,
                                  first: str, last: str, company: str,
                                  candidates: dict):
        """Search one Gmail account for messages mentioning the contact by name."""
        query = f'"{first} {last}"'

        try:
            results = service.users().messages().list(
                userId="me", q=query, maxResults=20
            ).execute()
        except HttpError as e:
            if e.resp.status == 429:
                time.sleep(10)
                return
            raise

        if not results.get("messages"):
            return

        for msg_ref in results["messages"][:15]:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="metadata",
                    metadataHeaders=["From", "To", "Cc", "Subject"]
                ).execute()
            except HttpError:
                continue

            headers = msg.get("payload", {}).get("headers", [])
            snippet = msg.get("snippet", "")

            # Extract all email addresses from headers
            for hdr in headers:
                hdr_name = hdr.get("name", "").lower()
                if hdr_name in ("from", "to", "cc"):
                    addrs = email.utils.getaddresses([hdr.get("value", "")])
                    for display_name, addr in addrs:
                        addr = addr.lower().strip()
                        if not addr or is_skip_email(addr):
                            continue

                        name_score = name_matches_email(first, last, display_name)
                        if name_score < 0.4:
                            # Also check if the email local part contains the name
                            local = addr.split("@")[0] if "@" in addr else ""
                            if last.lower() in local and first[0].lower() in local:
                                name_score = max(name_score, 0.5)
                            elif last.lower() in local:
                                name_score = max(name_score, 0.3)

                        if name_score < 0.3:
                            continue

                        if addr not in candidates:
                            candidates[addr] = {
                                "name_score": name_score,
                                "display_name": display_name,
                                "thread_count": 0,
                                "accounts": set(),
                                "context_snippets": [],
                            }
                        else:
                            # Update with higher name score if found
                            candidates[addr]["name_score"] = max(
                                candidates[addr]["name_score"], name_score
                            )
                            if display_name and not candidates[addr]["display_name"]:
                                candidates[addr]["display_name"] = display_name

                        candidates[addr]["thread_count"] += 1
                        candidates[addr]["accounts"].add(account_email)
                        if snippet and len(candidates[addr]["context_snippets"]) < 3:
                            subject = ""
                            for h in headers:
                                if h.get("name", "").lower() == "subject":
                                    subject = h.get("value", "")
                            candidates[addr]["context_snippets"].append(
                                f"Subject: {subject}\nSnippet: {snippet}"
                            )

            time.sleep(0.02)

    def verify_with_llm(self, contact: dict, candidate: dict) -> Optional[EmailVerification]:
        """Use GPT-5 mini to verify if a candidate email matches the contact."""
        first = contact.get("first_name", "")
        last = contact.get("last_name", "")
        name = f"{first} {last}".strip()

        prompt = (
            f"Verify if this email address belongs to this person.\n\n"
            f"PERSON:\n"
            f"  Name: {name}\n"
            f"  Current company: {contact.get('company') or contact.get('enrich_current_company') or '?'}\n"
            f"  Title: {contact.get('position') or contact.get('enrich_current_title') or '?'}\n"
            f"  Headline: {contact.get('headline', '?')}\n"
            f"  LinkedIn: {contact.get('linkedin_url', '?')}\n\n"
            f"CANDIDATE EMAIL: {candidate['email']}\n"
            f"  Display name in email headers: {candidate['display_name']}\n"
            f"  Found in {candidate['thread_count']} email threads\n"
            f"  Found across accounts: {', '.join(candidate['accounts'])}\n"
            f"  Name match score: {candidate['name_score']:.0%}\n"
            f"  Domain matches current company: {candidate.get('domain_match', False)}\n\n"
            f"EMAIL CONTEXT (snippets from threads):\n"
            + "\n---\n".join(candidate.get("context_snippets", ["(no context)"]))
            + "\n\nRULES:\n"
            "1. If the name is distinctive/uncommon AND the display name matches well, "
            "accept it as a match — even personal emails (gmail, yahoo, etc.) are fine.\n"
            "2. If the email is a COMPANY/WORK domain (not gmail/yahoo/outlook/etc), "
            "REJECT it if the domain doesn't match the person's CURRENT company. "
            "Old work emails from former employers are stale and shouldn't be stored.\n"
            "3. Be strict for common names (Michael Walker, David Lee, John Smith, etc.) — "
            "those need domain match, multiple threads, or strong contextual evidence. "
            "A single thread with a common name is NOT enough.\n"
            "4. Personal emails (gmail, yahoo, hotmail, outlook, icloud, protonmail) "
            "are always acceptable if the name match is strong."
        )

        try:
            resp = self.openai.responses.parse(
                model=self.MODEL,
                instructions="You verify email address matches. Accept distinctive names with good display-name matches. Reject company emails from former employers (domain doesn't match current company). Be strict only for very common names.",
                input=prompt,
                text_format=EmailVerification,
            )
            if resp.usage:
                self.stats["input_tokens"] += resp.usage.input_tokens
                self.stats["output_tokens"] += resp.usage.output_tokens
            return resp.output_parsed
        except (RateLimitError, APIError) as e:
            print(f"    LLM error: {e}")
            return None
        except Exception as e:
            print(f"    Unexpected LLM error: {e}")
            return None

    def save_email(self, contact_id: int, email_addr: str, email_type: str,
                   verification: EmailVerification):
        """Save discovered email to the contacts table."""
        if self.dry_run:
            return

        field = "personal_email" if email_type == "personal" else "work_email"
        if email_type == "unknown":
            field = "email"

        # Only write to an empty field
        updates = {
            field: email_addr,
        }

        self.supabase.table("contacts").update(updates).eq("id", contact_id).execute()

    def process_contact(self, contact: dict) -> bool:
        """Search for and verify email for one contact. Returns True if found."""
        contact_id = contact["id"]
        first = contact.get("first_name", "")
        last = contact.get("last_name", "")
        name = f"{first} {last}".strip()
        company = contact.get("company") or contact.get("enrich_current_company") or ""
        prox = contact.get("ai_proximity_score", "?")

        # Search Gmail
        candidate = self.search_for_email(contact)
        self.stats["contacts_searched"] += 1

        if not candidate:
            self.stats["no_candidates"] += 1
            print(f"  [{contact_id}] {name} ({company}, prox={prox}): no candidates found")
            return False

        # Verify with LLM
        verification = self.verify_with_llm(contact, candidate)
        if not verification:
            self.stats["errors"] += 1
            print(f"  [{contact_id}] {name}: LLM verification failed")
            return False

        email_addr = candidate["email"]
        conf = verification.confidence

        if verification.is_match and conf >= self.min_confidence:
            self.save_email(contact_id, email_addr, verification.email_type, verification)
            self.stats["high_confidence"] += 1
            self.stats["emails_found"] += 1
            marker = "[DRY-RUN] " if self.dry_run else ""
            print(f"  {marker}[{contact_id}] {name} ({company}, prox={prox}): "
                  f"FOUND {email_addr} (conf={conf}, type={verification.email_type})")
            print(f"    Reason: {verification.reasoning}")
            return True
        else:
            self.stats["low_confidence_skipped"] += 1
            print(f"  [{contact_id}] {name} ({company}, prox={prox}): "
                  f"SKIPPED {email_addr} (conf={conf}, match={verification.is_match})")
            print(f"    Reason: {verification.reasoning}")
            return False

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()
        contacts = self.get_contacts_without_email()
        total = len(contacts)
        print(f"Found {total} contacts without email addresses")
        print(f"Confidence threshold: {self.min_confidence}%")

        if total == 0:
            print("Nothing to do")
            return True

        print(f"\n--- Searching Gmail for email addresses ---\n")

        for i, contact in enumerate(contacts):
            try:
                self.process_contact(contact)
            except Exception as e:
                name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                print(f"  [{contact['id']}] {name}: ERROR - {e}")
                self.stats["errors"] += 1

            if (i + 1) % 25 == 0 or (i + 1) == total:
                elapsed = time.time() - start_time
                print(f"\n  --- Progress: {i + 1}/{total} "
                      f"(found={self.stats['emails_found']}, "
                      f"skipped={self.stats['low_confidence_skipped']}, "
                      f"none={self.stats['no_candidates']}) "
                      f"[{elapsed:.0f}s] ---\n")

        elapsed = time.time() - start_time
        self._print_summary(elapsed)
        return True

    def _print_summary(self, elapsed: float):
        s = self.stats
        input_cost = s["input_tokens"] * 0.15 / 1_000_000
        output_cost = s["output_tokens"] * 0.60 / 1_000_000

        print("\n" + "=" * 60)
        print("EMAIL DISCOVERY SUMMARY")
        print("=" * 60)
        print(f"  Contacts searched:      {s['contacts_searched']}")
        print(f"  Emails discovered:      {s['emails_found']}")
        print(f"  High confidence:        {s['high_confidence']}")
        print(f"  Low confidence skipped: {s['low_confidence_skipped']}")
        print(f"  No candidates found:    {s['no_candidates']}")
        print(f"  Errors:                 {s['errors']}")
        print(f"  LLM cost:               ${input_cost + output_cost:.2f}")
        print(f"  Time elapsed:           {elapsed:.1f}s")
        print(f"  Confidence threshold:   {self.min_confidence}%")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Discover email addresses for contacts via Gmail search"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process only N contacts (default: 5)")
    parser.add_argument("--count", "-n", type=int, default=5,
                        help="Number of contacts in test mode")
    parser.add_argument("--dry-run", "-d", action="store_true",
                        help="Search and verify but don't write to database")
    parser.add_argument("--min-confidence", type=int,
                        default=DEFAULT_CONFIDENCE_THRESHOLD,
                        help=f"Minimum LLM confidence to accept (default: {DEFAULT_CONFIDENCE_THRESHOLD})")
    args = parser.parse_args()

    discoverer = EmailDiscoverer(
        test_mode=args.test,
        test_count=args.count,
        dry_run=args.dry_run,
        min_confidence=args.min_confidence,
    )
    success = discoverer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
