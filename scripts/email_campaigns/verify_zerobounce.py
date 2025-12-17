#!/usr/bin/env python3
"""
Email verification using ZeroBounce API.

Performs SMTP-level verification to catch:
- Invalid mailboxes
- Catch-all domains
- Spam traps
- Abuse emails
- Role-based emails (info@, support@, etc.)

Usage:
    export ZEROBOUNCE_API_KEY="your_api_key"
    python scripts/email_campaigns/verify_zerobounce.py --campaign-id <id>

Cost: ~$15 for 2000 credits (minimum purchase)
Sign up at: https://www.zerobounce.net/
"""

import os
import time
import argparse
import requests
from typing import Dict, List, Optional
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ZEROBOUNCE_API_KEY = os.getenv("ZEROBOUNCE_API_KEY")

ZEROBOUNCE_API_URL = "https://api.zerobounce.net/v2/validate"

# Rate limit: ZeroBounce allows high volume but be respectful
RATE_LIMIT_DELAY = 0.1  # 100ms between requests


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


def check_credits() -> Optional[int]:
    """Check remaining ZeroBounce credits."""
    try:
        response = requests.get(
            "https://api.zerobounce.net/v2/getcredits",
            params={"api_key": ZEROBOUNCE_API_KEY}
        )
        data = response.json()
        return int(data.get("Credits", 0))
    except Exception as e:
        print(f"Error checking credits: {e}")
        return None


def verify_email_zerobounce(email: str) -> Dict:
    """Verify a single email via ZeroBounce API."""
    try:
        response = requests.get(
            ZEROBOUNCE_API_URL,
            params={
                "api_key": ZEROBOUNCE_API_KEY,
                "email": email
            },
            timeout=30
        )
        return response.json()
    except Exception as e:
        return {"error": str(e), "status": "error"}


def main():
    parser = argparse.ArgumentParser(description='Verify emails via ZeroBounce')
    parser.add_argument('--campaign-id', required=True, help='Campaign ID with failed emails')
    parser.add_argument('--skip-invalid-domains', action='store_true',
                        help='Skip emails with known invalid domains')

    args = parser.parse_args()

    # Check API key
    if not ZEROBOUNCE_API_KEY:
        print("ERROR: ZEROBOUNCE_API_KEY not set")
        print("\nTo use this script:")
        print("1. Sign up at https://www.zerobounce.net/")
        print("2. Get your API key from the dashboard")
        print("3. Run: export ZEROBOUNCE_API_KEY='your_key_here'")
        return

    # Check credits
    credits = check_credits()
    if credits is not None:
        print(f"ZeroBounce credits available: {credits}")
    else:
        print("Warning: Could not check credits")

    # Get emails to verify
    print(f"\nFetching failed emails for campaign: {args.campaign_id}")
    emails = get_failed_emails(args.campaign_id)
    print(f"Found {len(emails)} emails to verify")

    if not emails:
        print("No emails to verify.")
        return

    # Known invalid domains from basic verification
    invalid_domains = {
        'educationintl.org', 'youthoutside.org', 'mcpadvisors.com',
        'socialfinanceus.org', 'annmartin.org', 'rupperts.com'
    }

    if args.skip_invalid_domains:
        emails = [e for e in emails if e['email_address'].split('@')[1].lower() not in invalid_domains]
        print(f"After skipping invalid domains: {len(emails)} emails")

    if credits is not None and credits < len(emails):
        print(f"\nWARNING: Only {credits} credits available for {len(emails)} emails")
        print("Some emails will not be verified. Continue? (y/n)")
        if input().lower() != 'y':
            return

    # Verify emails
    results = {
        'valid': [],
        'invalid': [],
        'catch_all': [],
        'spamtrap': [],
        'abuse': [],
        'do_not_mail': [],
        'unknown': [],
        'error': []
    }

    print("\nVerifying emails via ZeroBounce...")
    print("-" * 60)

    for i, record in enumerate(emails):
        email = record['email_address']
        result = verify_email_zerobounce(email)

        status = result.get('status', 'error').lower()
        sub_status = result.get('sub_status', '')

        # Categorize
        if status == 'valid':
            results['valid'].append({**record, 'result': result})
        elif status == 'invalid':
            results['invalid'].append({**record, 'result': result})
            print(f"  INVALID: {email} ({sub_status})")
        elif status == 'catch-all':
            results['catch_all'].append({**record, 'result': result})
            print(f"  CATCH-ALL: {email}")
        elif status == 'spamtrap':
            results['spamtrap'].append({**record, 'result': result})
            print(f"  SPAMTRAP: {email} - DO NOT SEND!")
        elif status == 'abuse':
            results['abuse'].append({**record, 'result': result})
            print(f"  ABUSE: {email} - Known complainer")
        elif status == 'do_not_mail':
            results['do_not_mail'].append({**record, 'result': result})
            print(f"  DO NOT MAIL: {email} ({sub_status})")
        elif status == 'unknown':
            results['unknown'].append({**record, 'result': result})
            print(f"  UNKNOWN: {email} ({sub_status})")
        else:
            results['error'].append({**record, 'result': result})
            print(f"  ERROR: {email} - {result.get('error', 'Unknown error')}")

        # Progress
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(emails)}...")

        time.sleep(RATE_LIMIT_DELAY)

    # Summary
    print("\n" + "=" * 60)
    print("ZEROBOUNCE VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"  Total verified:  {len(emails)}")
    print(f"  Valid:           {len(results['valid'])} ✓ (safe to send)")
    print(f"  Invalid:         {len(results['invalid'])} ✗ (will bounce)")
    print(f"  Catch-all:       {len(results['catch_all'])} ⚠ (may or may not exist)")
    print(f"  Spam traps:      {len(results['spamtrap'])} 🚫 (DO NOT SEND)")
    print(f"  Abuse:           {len(results['abuse'])} ⚠ (likely to complain)")
    print(f"  Do not mail:     {len(results['do_not_mail'])} ✗ (role-based/risky)")
    print(f"  Unknown:         {len(results['unknown'])} ? (could not verify)")
    print(f"  Errors:          {len(results['error'])}")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Definite bounces - DO NOT SEND
    do_not_send = results['invalid'] + results['spamtrap'] + results['do_not_mail']
    if do_not_send:
        print(f"\n🚫 {len(do_not_send)} EMAILS TO REMOVE (will bounce or cause issues):")
        for record in do_not_send:
            sub_status = record['result'].get('sub_status', '')
            print(f"  - {record['email_address']} ({sub_status})")

    # Safe to send
    safe_count = len(results['valid'])
    risky_count = len(results['catch_all']) + len(results['abuse']) + len(results['unknown'])

    print(f"\n✓ {safe_count} emails are SAFE to send")
    if risky_count > 0:
        print(f"⚠ {risky_count} emails are RISKY (catch-all/abuse/unknown)")
        print("  These might work but have higher bounce/complaint risk")

    # Final recommendation
    print("\n" + "=" * 60)
    print("RECOMMENDATION:")
    if do_not_send:
        print(f"1. Remove {len(do_not_send)} invalid/risky emails from the send list")
        print("2. Update these contacts in your database")
    print(f"3. Send to the {safe_count} verified-valid emails")
    if results['catch_all']:
        print(f"4. Consider sending to {len(results['catch_all'])} catch-all addresses (your choice)")

    return results


if __name__ == "__main__":
    main()
