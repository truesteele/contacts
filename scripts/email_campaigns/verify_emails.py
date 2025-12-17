#!/usr/bin/env python3
"""
Email verification script - checks emails before sending.

Performs:
1. Syntax validation
2. MX record verification (can the domain receive email?)
3. Common typo detection
4. Disposable email detection

Usage:
    python scripts/email_campaigns/verify_emails.py --campaign-id <id>
"""

import os
import re
import dns.resolver
import argparse
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Common typos in email domains
DOMAIN_TYPOS = {
    'gmial.com': 'gmail.com',
    'gmai.com': 'gmail.com',
    'gamil.com': 'gmail.com',
    'gmail.co': 'gmail.com',
    'gnail.com': 'gmail.com',
    'gmal.com': 'gmail.com',
    'gmail.om': 'gmail.com',
    'gmail.con': 'gmail.com',
    'hotmal.com': 'hotmail.com',
    'hotmai.com': 'hotmail.com',
    'hotmail.co': 'hotmail.com',
    'hotmail.con': 'hotmail.com',
    'yahooo.com': 'yahoo.com',
    'yaho.com': 'yahoo.com',
    'yahoo.co': 'yahoo.com',
    'yahoo.con': 'yahoo.com',
    'outlok.com': 'outlook.com',
    'outloo.com': 'outlook.com',
    'outlook.co': 'outlook.com',
    'icloud.co': 'icloud.com',
    'icoud.com': 'icloud.com',
}

# Known disposable email domains (partial list)
DISPOSABLE_DOMAINS = {
    'mailinator.com', 'guerrillamail.com', 'tempmail.com', '10minutemail.com',
    'throwaway.email', 'fakeinbox.com', 'trashmail.com', 'sharklasers.com',
    'yopmail.com', 'temp-mail.org', 'dispostable.com', 'mailnesia.com'
}


def get_supabase_client():
    """Initialize Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_failed_emails(campaign_id: str) -> List[Dict]:
    """Get emails that failed due to API suspension."""
    client = get_supabase_client()
    response = client.table('email_sends').select(
        'id, contact_id, email_address'
    ).eq('campaign_id', campaign_id).eq('status', 'failed').execute()
    return response.data


def validate_syntax(email: str) -> Tuple[bool, Optional[str]]:
    """Check if email has valid syntax."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, None
    return False, "Invalid email syntax"


def check_typo(email: str) -> Tuple[bool, Optional[str]]:
    """Check for common domain typos."""
    domain = email.split('@')[1].lower() if '@' in email else ''
    if domain in DOMAIN_TYPOS:
        return False, f"Possible typo: did you mean {email.split('@')[0]}@{DOMAIN_TYPOS[domain]}?"
    return True, None


def check_disposable(email: str) -> Tuple[bool, Optional[str]]:
    """Check if email is from a disposable domain."""
    domain = email.split('@')[1].lower() if '@' in email else ''
    if domain in DISPOSABLE_DOMAINS:
        return False, "Disposable email domain"
    return True, None


def check_mx_record(domain: str, cache: Dict[str, bool]) -> Tuple[bool, Optional[str]]:
    """Check if domain has MX records (can receive email)."""
    if domain in cache:
        if cache[domain]:
            return True, None
        return False, f"Domain '{domain}' has no MX records"

    try:
        dns.resolver.resolve(domain, 'MX')
        cache[domain] = True
        return True, None
    except dns.resolver.NXDOMAIN:
        cache[domain] = False
        return False, f"Domain '{domain}' does not exist"
    except dns.resolver.NoAnswer:
        cache[domain] = False
        return False, f"Domain '{domain}' has no MX records"
    except dns.resolver.NoNameservers:
        cache[domain] = False
        return False, f"Domain '{domain}' has no nameservers"
    except Exception as e:
        # Don't cache errors - might be temporary
        return True, f"Warning: Could not verify domain '{domain}': {e}"


def verify_email(email: str, mx_cache: Dict[str, bool]) -> Dict:
    """Run all verification checks on an email."""
    result = {
        'email': email,
        'valid': True,
        'issues': [],
        'warnings': []
    }

    # Syntax check
    valid, error = validate_syntax(email)
    if not valid:
        result['valid'] = False
        result['issues'].append(error)
        return result  # No point checking further

    # Typo check
    valid, error = check_typo(email)
    if not valid:
        result['valid'] = False
        result['issues'].append(error)

    # Disposable check
    valid, error = check_disposable(email)
    if not valid:
        result['valid'] = False
        result['issues'].append(error)

    # MX record check
    domain = email.split('@')[1].lower()
    valid, error = check_mx_record(domain, mx_cache)
    if not valid:
        result['valid'] = False
        result['issues'].append(error)
    elif error:  # Warning
        result['warnings'].append(error)

    return result


def main():
    parser = argparse.ArgumentParser(description='Verify email addresses before sending')
    parser.add_argument('--campaign-id', required=True, help='Campaign ID with failed emails')
    parser.add_argument('--output', help='Output file for results (optional)')

    args = parser.parse_args()

    print(f"Fetching failed emails for campaign: {args.campaign_id}")
    emails = get_failed_emails(args.campaign_id)
    print(f"Found {len(emails)} emails to verify\n")

    if not emails:
        print("No emails to verify.")
        return

    mx_cache = {}  # Cache MX lookups by domain
    results = {
        'valid': [],
        'invalid': [],
        'warnings': []
    }

    # Group by domain for summary
    domain_stats = defaultdict(lambda: {'total': 0, 'valid': 0})

    print("Verifying emails...")
    print("-" * 60)

    for i, record in enumerate(emails):
        email = record['email_address']
        verification = verify_email(email, mx_cache)

        domain = email.split('@')[1].lower() if '@' in email else 'unknown'
        domain_stats[domain]['total'] += 1

        if verification['valid']:
            results['valid'].append(record)
            domain_stats[domain]['valid'] += 1
            if verification['warnings']:
                results['warnings'].append({
                    **record,
                    'warnings': verification['warnings']
                })
        else:
            results['invalid'].append({
                **record,
                'issues': verification['issues']
            })
            print(f"  INVALID: {email}")
            for issue in verification['issues']:
                print(f"           -> {issue}")

        # Progress
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(emails)}...")

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"  Total emails:  {len(emails)}")
    print(f"  Valid:         {len(results['valid'])} ✓")
    print(f"  Invalid:       {len(results['invalid'])} ✗")
    print(f"  With warnings: {len(results['warnings'])} ⚠")

    if results['invalid']:
        print(f"\n{len(results['invalid'])} INVALID EMAILS:")
        for record in results['invalid']:
            print(f"  - {record['email_address']} (contact_id: {record['contact_id']})")
            for issue in record['issues']:
                print(f"      {issue}")

    if results['warnings']:
        print(f"\n{len(results['warnings'])} EMAILS WITH WARNINGS:")
        for record in results['warnings']:
            print(f"  - {record['email_address']}")
            for warning in record['warnings']:
                print(f"      {warning}")

    # Domain summary
    print("\nDOMAIN BREAKDOWN:")
    sorted_domains = sorted(domain_stats.items(), key=lambda x: x[1]['total'], reverse=True)
    for domain, stats in sorted_domains[:20]:  # Top 20 domains
        valid_pct = (stats['valid'] / stats['total'] * 100) if stats['total'] > 0 else 0
        status = "✓" if valid_pct == 100 else "⚠" if valid_pct > 0 else "✗"
        print(f"  {status} {domain}: {stats['valid']}/{stats['total']} valid")

    if len(sorted_domains) > 20:
        print(f"  ... and {len(sorted_domains) - 20} more domains")

    # Recommendation
    print("\n" + "=" * 60)
    if results['invalid']:
        print("RECOMMENDATION: Remove or fix invalid emails before sending.")
        print("Consider using a paid email verification service like ZeroBounce")
        print("or Hunter.io for SMTP-level verification of the valid emails.")
    else:
        print("All emails passed basic verification!")
        print("For 100% confidence, consider SMTP verification via ZeroBounce/Hunter.io")

    return results


if __name__ == "__main__":
    main()
