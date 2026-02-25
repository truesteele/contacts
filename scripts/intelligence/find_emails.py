#!/usr/bin/env python3
"""
Network Intelligence — Email Finder Pipeline

Finds email addresses for contacts who have name + company data but no email.
Pipeline: company → domain discovery → email permutations → ZeroBounce verify → GPT validate → save

Usage:
  python scripts/intelligence/find_emails.py --test-domains         # Test domain discovery
  python scripts/intelligence/find_emails.py --test-perms           # Test permutation generator
  python scripts/intelligence/find_emails.py --test-verify          # Test ZeroBounce API
  python scripts/intelligence/find_emails.py --test-validate        # Test GPT validation
  python scripts/intelligence/find_emails.py --dry-run -n 5         # Dry-run 5 contacts
  python scripts/intelligence/find_emails.py -n 50                  # Run on 50 contacts
"""

import os
import sys
import re
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import psycopg2
import psycopg2.extras
import dns.resolver
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()


# ── Pydantic Schema ──────────────────────────────────────────────────

class EmailVerification(BaseModel):
    is_match: bool = Field(description="Is this email likely the contact's actual email?")
    confidence: int = Field(ge=0, le=100, description="0-100 confidence score")
    reasoning: str = Field(description="Brief explanation")
    email_type: str = Field(description="personal | work | unknown")


# ── Config ────────────────────────────────────────────────────────────

# Hardcoded domain map for well-known companies
KNOWN_COMPANY_DOMAINS = {
    "google": "google.com",
    "alphabet": "google.com",
    "amazon": "amazon.com",
    "aws": "amazon.com",
    "meta": "meta.com",
    "facebook": "meta.com",
    "microsoft": "microsoft.com",
    "apple": "apple.com",
    "year up": "yearup.org",
    "year up united": "yearup.org",
    "salesforce": "salesforce.com",
    "deloitte": "deloitte.com",
    "mckinsey": "mckinsey.com",
    "mckinsey & company": "mckinsey.com",
    "goldman sachs": "goldmansachs.com",
    "jpmorgan": "jpmchase.com",
    "jpmorgan chase": "jpmchase.com",
    "jp morgan": "jpmchase.com",
    "cisco": "cisco.com",
    "oracle": "oracle.com",
    "adobe": "adobe.com",
    "linkedin": "linkedin.com",
    "tiktok": "tiktok.com",
    "bytedance": "bytedance.com",
    "netflix": "netflix.com",
    "uber": "uber.com",
    "lyft": "lyft.com",
    "stripe": "stripe.com",
    "bain": "bain.com",
    "bain & company": "bain.com",
    "bcg": "bcg.com",
    "boston consulting group": "bcg.com",
    "bridgespan": "bridgespan.org",
    "the bridgespan group": "bridgespan.org",
    "harvard business school": "hbs.edu",
    "hbs": "hbs.edu",
    "stanford": "stanford.edu",
    "mit": "mit.edu",
    "uva": "virginia.edu",
    "university of virginia": "virginia.edu",
    "duke university": "duke.edu",
    "duke": "duke.edu",
    "twitter": "x.com",
    "x": "x.com",
    "snap": "snap.com",
    "snapchat": "snap.com",
    "airbnb": "airbnb.com",
    "dropbox": "dropbox.com",
    "slack": "slack.com",
    "datadog": "datadoghq.com",
    "xero": "xero.com",
    "guild education": "guildeducation.com",
    "guild": "guildeducation.com",
    "alphasense": "alpha-sense.com",
    "national geospatial-intelligence agency": "nga.mil",
    "nga": "nga.mil",
    "ibm": "ibm.com",
    "accenture": "accenture.com",
    "pwc": "pwc.com",
    "pricewaterhousecoopers": "pwc.com",
    "ernst & young": "ey.com",
    "ey": "ey.com",
    "kpmg": "kpmg.com",
    "morgan stanley": "morganstanley.com",
    "bank of america": "bofa.com",
    "citigroup": "citi.com",
    "citi": "citi.com",
    "wells fargo": "wellsfargo.com",
    "capital one": "capitalone.com",
    "spotify": "spotify.com",
    "pinterest": "pinterest.com",
    "robinhood": "robinhood.com",
    "palantir": "palantir.com",
    "databricks": "databricks.com",
    "snowflake": "snowflake.com",
    "shopify": "shopify.com",
    "square": "squareup.com",
    "block": "block.xyz",
    "doordash": "doordash.com",
    "instacart": "instacart.com",
    "coinbase": "coinbase.com",
    "figma": "figma.com",
    "notion": "notion.so",
    "openai": "openai.com",
    "anthropic": "anthropic.com",
}

# Suffixes to strip from company names before domain guessing
COMPANY_SUFFIXES = re.compile(
    r',?\s*\b(Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|Foundation|'
    r'Company|Co\.?|Group|Partners|Consulting|Services|Solutions|'
    r'Technologies|International|Global|Worldwide|Holdings|'
    r'Enterprises|Associates|& Co\.?|PLC|LP|LLP|GmbH|AG|SA|'
    r'The|University|School|of|Business)\b\.?',
    re.IGNORECASE
)

# DNS resolver with short timeout
_resolver = dns.resolver.Resolver()
_resolver.timeout = 3
_resolver.lifetime = 5

# Cache for MX lookups to avoid repeated DNS queries
_mx_cache = {}


# ── DB ────────────────────────────────────────────────────────────────

def get_db_conn():
    return psycopg2.connect(
        host="db.ypqsrejrsocebnldicke.supabase.co",
        port=5432,
        dbname="postgres",
        user="postgres",
        password=os.environ["SUPABASE_DB_PASSWORD"],
    )


# ── Domain Discovery ─────────────────────────────────────────────────

def check_mx(domain: str) -> bool:
    """Check if a domain has MX records (can receive email). Results are cached."""
    if domain in _mx_cache:
        return _mx_cache[domain]

    try:
        answers = _resolver.resolve(domain, "MX")
        has_mx = len(answers) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers,
            dns.resolver.LifetimeTimeout, dns.exception.DNSException):
        has_mx = False

    _mx_cache[domain] = has_mx
    return has_mx


def _normalize_company(name: str) -> str:
    """Strip suffixes and clean company name for domain guessing."""
    # Remove common parenthetical descriptions
    name = re.sub(r'\(.*?\)', '', name).strip()
    # Remove leading "The "
    name = re.sub(r'^The\s+', '', name, flags=re.IGNORECASE).strip()
    # Remove suffixes
    name = COMPANY_SUFFIXES.sub('', name).strip()
    # Remove trailing punctuation
    name = name.rstrip('.,- ')
    return name


def company_to_domains(company_name: str) -> list[str]:
    """
    Convert a company name to a list of candidate email domains.
    Returns domains ordered by likelihood, filtered by MX record check.
    """
    if not company_name or not company_name.strip():
        return []

    company_lower = company_name.lower().strip()

    # 1. Check hardcoded map (try full name first, then normalized)
    for key in [company_lower, _normalize_company(company_lower)]:
        if key in KNOWN_COMPANY_DOMAINS:
            domain = KNOWN_COMPANY_DOMAINS[key]
            if check_mx(domain):
                return [domain]
            # Known domain but no MX? Still return it (might be catch-all behind proxy)
            return [domain]

    # 2. Also check if company name starts with or contains a known key
    for key, domain in KNOWN_COMPANY_DOMAINS.items():
        if company_lower.startswith(key + " ") or company_lower.startswith(key + ","):
            if check_mx(domain):
                return [domain]
            return [domain]

    # 3. Generic fallback: guess domains from cleaned company name
    cleaned = _normalize_company(company_name)
    if not cleaned:
        return []

    # Build slug: lowercase, remove special chars, collapse spaces to nothing
    slug = re.sub(r'[^a-z0-9\s]', '', cleaned.lower())
    slug = slug.strip()

    # Try both joined (no spaces) and hyphenated
    slug_joined = slug.replace(' ', '')
    slug_hyphen = slug.replace(' ', '-')

    # Generate candidates in priority order
    candidates = []
    seen = set()

    for s in [slug_joined, slug_hyphen]:
        for tld in ['.com', '.org', '.io', '.co']:
            domain = s + tld
            if domain not in seen:
                seen.add(domain)
                candidates.append(domain)

    # Filter by MX records
    valid = [d for d in candidates if check_mx(d)]

    # If no MX-validated domains, return top 2 .com candidates anyway
    # (some companies use Google Workspace which might not show standard MX)
    if not valid:
        com_candidates = [d for d in candidates if d.endswith('.com')][:2]
        return com_candidates

    return valid


# ── Email Permutation Generator ──────────────────────────────────────

# Name suffixes to strip
NAME_SUFFIXES = re.compile(
    r'\b(Jr\.?|Sr\.?|III|II|IV|V|PhD|Ph\.D\.?|MD|M\.D\.?|Esq\.?|CPA|MBA|'
    r'MPH|MPA|EdD|Ed\.D\.?|DDS|JD|J\.D\.?|RN|PE|CFA|CFP|LCSW)\b\.?,?\s*',
    re.IGNORECASE
)


def _clean_name_part(name: str) -> str:
    """Clean and normalize a single name part (first or last).
    Returns a single lowercase token with no spaces (spaces collapsed out)."""
    if not name:
        return ""
    # Strip suffixes
    name = NAME_SUFFIXES.sub('', name).strip()
    # Remove anything in parentheses
    name = re.sub(r'\(.*?\)', '', name).strip()
    # Remove quotes and apostrophes
    name = name.replace('"', '').replace("'", "").strip()
    # Remove trailing commas/periods
    name = name.rstrip('.,')
    # Lowercase
    name = name.lower().strip()
    # Collapse spaces (multi-word names like "de la Cruz" -> "delacruz")
    name = name.replace(' ', '')
    return name


def _split_hyphenated(name: str) -> list[str]:
    """
    For a hyphenated name like 'Marie-Ange', return variants:
    ['marie-ange', 'marieange', 'marie']
    For non-hyphenated, return [name].
    """
    if '-' not in name:
        return [name]
    parts = name.split('-')
    return [
        name,              # marie-ange
        ''.join(parts),    # marieange
        parts[0],          # marie (first part only)
    ]


def generate_permutations(first_name: str, last_name: str, domain: str) -> list[str]:
    """
    Generate 8-12 candidate email addresses from name + domain.
    Handles hyphenated names, suffixes, and edge cases.
    Returns deduplicated list ordered by corporate likelihood.
    """
    first = _clean_name_part(first_name)
    last = _clean_name_part(last_name)

    if not first or not last or not domain:
        return []

    # Get variants for hyphenated names
    first_variants = _split_hyphenated(first)
    last_variants = _split_hyphenated(last)

    # Use primary variants for all patterns
    f = first_variants[0]  # full first (may include hyphen)
    l = last_variants[0]   # full last (may include hyphen)

    # Safe versions with no hyphens for patterns that don't use them
    f_joined = first_variants[1] if len(first_variants) > 1 else f.replace('-', '')
    l_joined = last_variants[1] if len(last_variants) > 1 else l.replace('-', '')

    # Short first (for hyphenated: first part; else full)
    f_short = first_variants[2] if len(first_variants) > 2 else f_joined

    candidates = []
    seen = set()

    def _add(local: str):
        # Remove any remaining hyphens in local part that aren't intentional
        addr = f"{local}@{domain}"
        if addr not in seen and local:
            seen.add(addr)
            candidates.append(addr)

    # Most common corporate patterns (priority order)
    _add(f"{f_joined}.{l_joined}")      # first.last
    _add(f"{f_joined}{l_joined}")        # firstlast
    _add(f"{f_joined}_{l_joined}")       # first_last
    _add(f"{f_joined[0]}{l_joined}")     # flast
    _add(f"{f_joined}.{l_joined[0]}")    # first.l
    _add(f"{f_joined}{l_joined[0]}")     # firstl
    _add(f"{f_joined[0]}.{l_joined}")    # f.last
    _add(f"{l_joined}.{f_joined}")       # last.first
    _add(f"{l_joined}{f_joined[0]}")     # lastf
    _add(f"{f_joined}")                  # first (founders/small cos)

    # If hyphenated first name, also add short-first variants
    if f_short != f_joined:
        _add(f"{f_short}.{l_joined}")    # marie.dupont (short first)
        _add(f"{f_short}{l_joined}")     # mariedupont
        _add(f"{f_short[0]}{l_joined}")  # mdupont (if different initial)

    # If hyphenated last name, add joined variant
    if l_joined != l.replace('-', ''):
        _add(f"{f_joined}.{l_joined}")
        _add(f"{f_joined}{l_joined}")

    return candidates


# ── ZeroBounce Verification ──────────────────────────────────────────

ZEROBOUNCE_BASE = "https://api.zerobounce.net/v2"

# Sub-statuses that indicate transient errors (worth retrying)
TRANSIENT_SUBSTATUSES = {
    "greylisted", "mail_server_temporary_error", "forcible_disconnect",
    "timeout_exceeded",
}

# Domains known to be catch-all (every address "accepts" but may not deliver)
CATCH_ALL_DOMAINS = {
    "google.com", "amazon.com", "meta.com", "microsoft.com", "apple.com",
    "linkedin.com", "netflix.com", "uber.com", "stripe.com", "airbnb.com",
}

# Track credit usage across the session
_credits_used = 0


def check_zerobounce_credits() -> int:
    """Check remaining ZeroBounce credit balance."""
    api_key = os.environ.get("ZEROBOUNCE_API_KEY", "")
    if not api_key:
        raise ValueError("ZEROBOUNCE_API_KEY not set in environment")

    resp = requests.get(f"{ZEROBOUNCE_BASE}/getcredits", params={"api_key": api_key}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return int(data.get("Credits", 0))


def verify_email(email_addr: str, max_retries: int = 2) -> dict | None:
    """
    Verify a single email via ZeroBounce API.

    Returns dict with keys: address, status, sub_status, free_email,
    active_in_days, smtp_provider, mx_record, domain_age_days, firstname, lastname.
    Returns None on unrecoverable error.
    """
    global _credits_used
    api_key = os.environ.get("ZEROBOUNCE_API_KEY", "")

    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(
                f"{ZEROBOUNCE_BASE}/validate",
                params={"api_key": api_key, "email": email_addr, "ip_address": ""},
                timeout=30,
            )

            # Rate limit: ZeroBounce returns 429 if >80K/10sec, triggers 1-min block
            if resp.status_code == 429:
                wait = 65  # 1-min block + buffer
                print(f"    ZeroBounce rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()

            # Track credits (unknown results are free)
            status = data.get("status", "").lower()
            if status != "unknown":
                _credits_used += 1

            # Check for transient sub-status — retry with backoff
            sub_status = (data.get("sub_status") or "").lower()
            if status == "unknown" and sub_status in TRANSIENT_SUBSTATUSES and attempt < max_retries:
                wait = 2 ** attempt * 2  # 2s, 4s
                time.sleep(wait)
                continue

            return {
                "address": data.get("address", email_addr),
                "status": status,
                "sub_status": sub_status,
                "free_email": data.get("free_email", False),
                "active_in_days": data.get("active_in_days"),
                "smtp_provider": data.get("smtp_provider", ""),
                "mx_record": data.get("mx_record", ""),
                "domain_age_days": data.get("domain_age_days"),
                "firstname": data.get("firstname", ""),
                "lastname": data.get("lastname", ""),
            }

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                time.sleep(2 ** attempt * 2)
                continue
            print(f"    Timeout verifying {email_addr} after {max_retries + 1} attempts")
            return None
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                time.sleep(2 ** attempt * 2)
                continue
            print(f"    Error verifying {email_addr}: {e}")
            return None

    return None


def verify_emails_batch(emails: list[str], max_workers: int = 50) -> dict[str, dict]:
    """
    Verify multiple emails concurrently via ZeroBounce.
    Returns dict mapping email -> ZeroBounce result.
    Stops early if a 'valid' result is found (for efficiency).
    """
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_email = {pool.submit(verify_email, addr): addr for addr in emails}
        for future in as_completed(future_to_email):
            addr = future_to_email[future]
            try:
                result = future.result()
                if result:
                    results[addr] = result
            except Exception as e:
                print(f"    Unexpected error for {addr}: {e}")

    return results


def pick_best_result(results: dict[str, dict]) -> tuple[str, dict] | None:
    """
    From a set of ZeroBounce results, pick the best email.
    Priority: valid > catch-all (with recent activity) > catch-all (stale).
    Returns (email, result) or None.
    """
    if not results:
        return None

    valid = []
    catch_all = []

    for addr, r in results.items():
        status = r.get("status", "")
        if status == "valid":
            valid.append((addr, r))
        elif status == "catch-all":
            catch_all.append((addr, r))

    # Prefer valid results, sorted by activity recency
    if valid:
        valid.sort(key=lambda x: _activity_score(x[1]), reverse=True)
        return valid[0]

    # Fall back to catch-all with best activity
    if catch_all:
        catch_all.sort(key=lambda x: _activity_score(x[1]), reverse=True)
        return catch_all[0]

    return None


def _activity_score(result: dict) -> float:
    """Score a ZeroBounce result by how recently the email was active."""
    active_in_days = result.get("active_in_days")
    if active_in_days is None or active_in_days == "":
        return 0.0
    try:
        days = int(active_in_days)
        # More recent = higher score. 0 days = 1000, 365 days = 635, etc.
        return max(1000 - days, 0)
    except (ValueError, TypeError):
        return 0.0


def get_credits_used() -> int:
    """Return total ZeroBounce credits used this session."""
    return _credits_used


# ── GPT-5 Mini Validation ────────────────────────────────────────────

PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "me.com", "aol.com", "comcast.net", "protonmail.com", "live.com",
    "msn.com", "att.net", "verizon.net", "sbcglobal.net", "mac.com",
}


def is_obvious_match(contact: dict, email: str, zb_result: dict) -> bool:
    """
    Check if this is an obvious match that can skip LLM validation.
    Criteria: full name appears in email local part AND domain matches current company.
    """
    first = (contact.get("first_name") or "").lower().strip()
    last = (contact.get("last_name") or "").lower().strip()
    if not first or not last:
        return False

    local = email.split("@")[0].lower() if "@" in email else ""
    domain = email.split("@")[1].lower() if "@" in email else ""

    # Name must be in the local part
    has_first = first in local
    has_last = last in local
    if not (has_first and has_last):
        return False

    # Status must be valid (not catch-all)
    status = zb_result.get("status", "")
    if status != "valid":
        return False

    # Domain must match current company OR be a personal domain
    company = (contact.get("company") or contact.get("enrich_current_company") or "").lower()
    if domain in PERSONAL_DOMAINS:
        return True

    # Check if company name appears in domain
    if company:
        company_slug = re.sub(r'[^a-z0-9]', '', company)
        domain_slug = re.sub(r'[^a-z0-9]', '', domain.split('.')[0])
        if company_slug and domain_slug and (
            company_slug in domain_slug or domain_slug in company_slug
        ):
            return True

    return False


def validate_with_llm(
    openai_client: OpenAI,
    contact: dict,
    email: str,
    zb_result: dict,
    max_retries: int = 2,
) -> EmailVerification | None:
    """
    Use GPT-5 mini to validate a candidate email for a contact.
    Returns EmailVerification or None on error.
    """
    first = contact.get("first_name") or ""
    last = contact.get("last_name") or ""
    name = f"{first} {last}".strip()
    company = contact.get("company") or contact.get("enrich_current_company") or "unknown"
    title = contact.get("enrich_current_title") or contact.get("position") or "unknown"
    linkedin = contact.get("linkedin_url") or "none"

    domain = email.split("@")[1] if "@" in email else ""
    status = zb_result.get("status", "unknown")
    sub_status = zb_result.get("sub_status", "")
    free_email = zb_result.get("free_email", False)
    active_in_days = zb_result.get("active_in_days")
    smtp_provider = zb_result.get("smtp_provider", "")

    prompt = (
        f"Determine if this email address belongs to this person and is usable.\n\n"
        f"PERSON:\n"
        f"  Name: {name}\n"
        f"  Current company: {company}\n"
        f"  Title: {title}\n"
        f"  LinkedIn: {linkedin}\n\n"
        f"CANDIDATE EMAIL: {email}\n"
        f"  ZeroBounce status: {status}\n"
        f"  Sub-status: {sub_status or 'none'}\n"
        f"  Free email: {free_email}\n"
        f"  Active in days: {active_in_days if active_in_days is not None else 'unknown'}\n"
        f"  SMTP provider: {smtp_provider or 'unknown'}\n"
        f"  Domain: {domain}\n\n"
        f"RULES:\n"
        f"- ACCEPT valid personal emails (gmail, yahoo, etc.) if name matches the local part well\n"
        f"- ACCEPT valid corporate emails if the domain matches their CURRENT company\n"
        f"- REJECT corporate emails where the domain is for a DIFFERENT company than their current one\n"
        f"  (they likely left that job and the email is stale)\n"
        f"- For catch-all domains (Google, Amazon, Meta, etc.), be SKEPTICAL — catch-all means\n"
        f"  the server accepts all addresses, so ZeroBounce can't confirm the mailbox exists.\n"
        f"  Only accept if the name is distinctive or the permutation pattern is very standard.\n"
        f"- For common first names (John, Michael, David, James, Robert, Maria, Jennifer, Sarah),\n"
        f"  require STRONGER evidence (full name in email, matching company domain)\n"
        f"- If status is 'invalid', REJECT regardless\n"
        f"- Set confidence based on overall evidence strength (0-100)\n"
        f"- Set email_type to 'personal' for free email domains, 'work' for corporate, 'unknown' if unclear"
    )

    for attempt in range(max_retries + 1):
        try:
            resp = openai_client.responses.parse(
                model="gpt-5-mini",
                instructions="You verify email matches. Be accurate and concise.",
                input=prompt,
                text_format=EmailVerification,
            )
            return resp.output_parsed
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            print(f"    LLM error for {email}: {e}")
            return None


def validate_emails_batch(
    openai_client: OpenAI,
    tasks: list[tuple[dict, str, dict]],
    max_workers: int = 150,
) -> list[tuple[dict, str, dict, EmailVerification | None]]:
    """
    Validate multiple (contact, email, zb_result) tuples concurrently with LLM.
    Returns list of (contact, email, zb_result, verification).
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_task = {
            pool.submit(validate_with_llm, openai_client, c, e, z): (c, e, z)
            for c, e, z in tasks
        }
        for future in as_completed(future_to_task):
            contact, email_addr, zb = future_to_task[future]
            try:
                verification = future.result()
            except Exception as exc:
                print(f"    Unexpected LLM error: {exc}")
                verification = None
            results.append((contact, email_addr, zb, verification))

    return results


# ── Test CLI ──────────────────────────────────────────────────────────

def test_domains():
    """Test domain discovery on 10 sample contacts from the database."""
    print("\n" + "=" * 60)
    print("TEST: Domain Discovery")
    print("=" * 60)

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT id, first_name, last_name, company, enrich_current_company
        FROM contacts
        WHERE (email IS NULL OR email = '')
        AND first_name IS NOT NULL AND first_name != ''
        AND last_name IS NOT NULL AND last_name != ''
        ORDER BY COALESCE(ai_proximity_score, 0) DESC
        LIMIT 10
    """)
    contacts = cur.fetchall()
    print(f"  Testing {len(contacts)} contacts\n")

    total_domains = 0
    total_with_mx = 0
    start = time.time()

    for c in contacts:
        company = c['company'] or c['enrich_current_company'] or ''
        name = f"{c['first_name']} {c['last_name']}"
        domains = company_to_domains(company)
        total_domains += len(domains)
        if domains:
            total_with_mx += 1

        status = ", ".join(domains) if domains else "(no domains found)"
        print(f"  [{c['id']}] {name:30s} | {company:35s} -> {status}")

    elapsed = time.time() - start
    print(f"\n  Results: {total_with_mx}/{len(contacts)} contacts got domains, "
          f"{total_domains} total domains, {elapsed:.1f}s")
    print(f"  MX cache size: {len(_mx_cache)} domains checked")

    conn.close()


def test_perms():
    """Test permutation generation on 5 sample contacts from the database."""
    print("\n" + "=" * 60)
    print("TEST: Email Permutation Generator")
    print("=" * 60)

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT id, first_name, last_name, company, enrich_current_company
        FROM contacts
        WHERE (email IS NULL OR email = '')
        AND first_name IS NOT NULL AND first_name != ''
        AND last_name IS NOT NULL AND last_name != ''
        ORDER BY COALESCE(ai_proximity_score, 0) DESC
        LIMIT 5
    """)
    contacts = cur.fetchall()
    conn.close()

    print(f"  Testing {len(contacts)} contacts from DB\n")

    for c in contacts:
        company = c['company'] or c['enrich_current_company'] or ''
        name = f"{c['first_name']} {c['last_name']}"
        domains = company_to_domains(company)
        domain = domains[0] if domains else "example.com"

        perms = generate_permutations(c['first_name'], c['last_name'], domain)
        print(f"  [{c['id']}] {name} @ {domain}")
        for p in perms:
            print(f"    {p}")
        print(f"    ({len(perms)} permutations)\n")

    # Also test edge cases
    print("  --- Edge Cases ---\n")

    edge_cases = [
        ("Marie-Ange", "Dupont", "company.com", "Hyphenated first name"),
        ("Robert", "Smith III", "bigcorp.com", "Name with suffix"),
        ("Jean-Pierre", "de la Cruz", "startup.io", "Hyphenated + multi-word last"),
        ("Jen", "O'Brien", "firm.com", "Apostrophe in last name"),
        ("A.", "Johnson Jr.", "co.com", "Single initial + suffix"),
    ]

    for first, last, domain, label in edge_cases:
        perms = generate_permutations(first, last, domain)
        print(f"  {label}: {first} {last} @ {domain}")
        for p in perms:
            print(f"    {p}")
        print(f"    ({len(perms)} permutations)\n")


def test_verify():
    """Test ZeroBounce verification on 3 known emails (uses real API credits)."""
    print("\n" + "=" * 60)
    print("TEST: ZeroBounce Email Verification")
    print("=" * 60)

    # Check API key
    api_key = os.environ.get("ZEROBOUNCE_API_KEY", "")
    if not api_key:
        print("  ERROR: ZEROBOUNCE_API_KEY not set in environment")
        return

    # Check credit balance
    try:
        credits = check_zerobounce_credits()
        print(f"  ZeroBounce credits available: {credits}")
    except Exception as e:
        print(f"  ERROR checking credits: {e}")
        return

    if credits < 3:
        print("  ERROR: Need at least 3 credits for test (have {credits})")
        return

    # Test 3 emails: one likely valid, one invalid, one catch-all domain
    test_emails = [
        ("justinrsteele@gmail.com", "valid personal email"),
        ("definitelynotarealemailaddress99999@gmail.com", "invalid email"),
        ("test@google.com", "catch-all domain"),
    ]

    print(f"\n  Testing {len(test_emails)} emails...\n")
    start = time.time()

    for addr, description in test_emails:
        print(f"  [{description}] {addr}")
        result = verify_email(addr)
        if result:
            print(f"    status:         {result['status']}")
            print(f"    sub_status:     {result['sub_status']}")
            print(f"    free_email:     {result['free_email']}")
            print(f"    active_in_days: {result['active_in_days']}")
            print(f"    smtp_provider:  {result['smtp_provider']}")
            print(f"    mx_record:      {result['mx_record']}")
            print(f"    domain_age:     {result['domain_age_days']} days")
            print(f"    firstname:      {result['firstname']}")
            print(f"    lastname:       {result['lastname']}")
        else:
            print(f"    ERROR: no result returned")
        print()

    elapsed = time.time() - start
    print(f"  Credits used this session: {get_credits_used()}")
    print(f"  Remaining credits: {check_zerobounce_credits()}")
    print(f"  Time: {elapsed:.1f}s")

    # Also test batch verification with pick_best_result
    print("\n  --- Batch + Pick Best Test ---\n")

    batch_emails = [
        "definitelynotreal12345@example.com",
        "justinrsteele@gmail.com",
        "alsonotreal67890@example.com",
    ]
    print(f"  Verifying {len(batch_emails)} emails concurrently...")
    batch_results = verify_emails_batch(batch_emails, max_workers=3)
    print(f"  Got {len(batch_results)} results:")
    for addr, r in batch_results.items():
        print(f"    {addr}: {r['status']} ({r['sub_status']})")

    best = pick_best_result(batch_results)
    if best:
        print(f"\n  Best pick: {best[0]} (status={best[1]['status']})")
    else:
        print(f"\n  No valid/catch-all result found")

    print(f"\n  Total credits used: {get_credits_used()}")


def test_validate():
    """Test GPT-5 mini validation on 3 mock scenarios (uses OpenAI API, no ZeroBounce)."""
    print("\n" + "=" * 60)
    print("TEST: GPT-5 Mini Email Validation")
    print("=" * 60)

    api_key = os.environ.get("OPENAI_APIKEY", "")
    if not api_key:
        print("  ERROR: OPENAI_APIKEY not set in environment")
        return

    client = OpenAI(api_key=api_key)
    print("  OpenAI: connected\n")

    # 3 mock scenarios with expected outcomes
    scenarios = [
        {
            "label": "Obvious match — name in email + domain matches company",
            "contact": {
                "first_name": "Sarah",
                "last_name": "Chen",
                "company": "Stripe",
                "enrich_current_company": "Stripe",
                "enrich_current_title": "Senior Engineer",
                "linkedin_url": "https://linkedin.com/in/sarahchen",
            },
            "email": "sarah.chen@stripe.com",
            "zb_result": {
                "status": "valid", "sub_status": "", "free_email": False,
                "active_in_days": 30, "smtp_provider": "google", "mx_record": "stripe-com.mail.protection.outlook.com",
            },
            "expect_match": True,
            "expect_obvious": True,
        },
        {
            "label": "Stale employer — person left Google, email is @google.com",
            "contact": {
                "first_name": "Marcus",
                "last_name": "Johnson",
                "company": "Anthropic",
                "enrich_current_company": "Anthropic",
                "enrich_current_title": "Product Manager",
                "linkedin_url": "https://linkedin.com/in/marcusjohnson",
            },
            "email": "marcus.johnson@google.com",
            "zb_result": {
                "status": "catch-all", "sub_status": "", "free_email": False,
                "active_in_days": None, "smtp_provider": "google", "mx_record": "aspmx.l.google.com",
            },
            "expect_match": False,
            "expect_obvious": False,
        },
        {
            "label": "Personal email — valid gmail with good name match",
            "contact": {
                "first_name": "Elena",
                "last_name": "Rodriguez",
                "company": "McKinsey & Company",
                "enrich_current_company": "McKinsey & Company",
                "enrich_current_title": "Associate Partner",
                "linkedin_url": "https://linkedin.com/in/elenarodriguez",
            },
            "email": "elena.rodriguez@gmail.com",
            "zb_result": {
                "status": "valid", "sub_status": "", "free_email": True,
                "active_in_days": 15, "smtp_provider": "google", "mx_record": "gmail-smtp-in.l.google.com",
            },
            "expect_match": True,
            "expect_obvious": True,
        },
    ]

    start = time.time()
    passed = 0

    for i, s in enumerate(scenarios, 1):
        print(f"  Scenario {i}: {s['label']}")
        print(f"    Contact: {s['contact']['first_name']} {s['contact']['last_name']} @ {s['contact']['company']}")
        print(f"    Email:   {s['email']}")
        print(f"    ZB:      status={s['zb_result']['status']}, free={s['zb_result']['free_email']}")

        # Test is_obvious_match
        obvious = is_obvious_match(s["contact"], s["email"], s["zb_result"])
        obvious_ok = obvious == s["expect_obvious"]
        print(f"    Obvious: {obvious} (expected {s['expect_obvious']}) {'OK' if obvious_ok else 'MISMATCH'}")

        # Test LLM validation (skip if obvious match in real pipeline, but test it anyway)
        verification = validate_with_llm(client, s["contact"], s["email"], s["zb_result"])
        if verification:
            match_ok = verification.is_match == s["expect_match"]
            print(f"    LLM:     is_match={verification.is_match} (expected {s['expect_match']}) "
                  f"{'OK' if match_ok else 'MISMATCH'}")
            print(f"    Conf:    {verification.confidence}")
            print(f"    Type:    {verification.email_type}")
            print(f"    Reason:  {verification.reasoning}")
            if match_ok:
                passed += 1
        else:
            print(f"    LLM:     ERROR - no response")
        print()

    elapsed = time.time() - start
    print(f"  Results: {passed}/{len(scenarios)} LLM validations matched expected outcome")
    print(f"  Time: {elapsed:.1f}s")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Email Finder Pipeline")
    parser.add_argument("--test-domains", action="store_true",
                        help="Test domain discovery on 10 sample contacts")
    parser.add_argument("--test-perms", action="store_true",
                        help="Test permutation generation on 5 sample contacts")
    parser.add_argument("--test-verify", action="store_true",
                        help="Test ZeroBounce verification on 3 known emails")
    parser.add_argument("--test-validate", action="store_true",
                        help="Test GPT validation on 3 mock scenarios")
    parser.add_argument("--dry-run", "-d", action="store_true",
                        help="Don't write to database")
    parser.add_argument("--limit", "-n", type=int, default=None,
                        help="Limit number of contacts to process")
    parser.add_argument("--min-confidence", type=int, default=70,
                        help="Minimum confidence to accept (default: 70)")
    parser.add_argument("--workers", type=int, default=50,
                        help="ZeroBounce concurrent workers (default: 50)")
    args = parser.parse_args()

    if args.test_domains:
        test_domains()
        return

    if args.test_perms:
        test_perms()
        return
    if args.test_verify:
        test_verify()
        return
    if args.test_validate:
        test_validate()
        return

    # Main pipeline placeholder
    print("Main pipeline not yet implemented (US-005)")


if __name__ == "__main__":
    main()
