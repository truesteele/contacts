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

    # Placeholder for future test modes
    if args.test_perms:
        print("--test-perms not yet implemented (US-002)")
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
