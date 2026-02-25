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

import psycopg2
import psycopg2.extras
import dns.resolver
from dotenv import load_dotenv

load_dotenv()

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
        print("--test-verify not yet implemented (US-003)")
        return
    if args.test_validate:
        print("--test-validate not yet implemented (US-004)")
        return

    # Main pipeline placeholder
    print("Main pipeline not yet implemented (US-005)")


if __name__ == "__main__":
    main()
