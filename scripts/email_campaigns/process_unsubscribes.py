#!/usr/bin/env python3
"""
Process Unsubscribe Requests

Simple utility to mark contacts as unsubscribed in the database.
Since emails use reply-to: justinrsteele@gmail.com, you'll receive
unsubscribe requests in your Gmail inbox. Use this script to process them.

Usage:
    # Unsubscribe a single email
    python process_unsubscribes.py --email john@example.com

    # Unsubscribe multiple emails from a file (one per line)
    python process_unsubscribes.py --file unsubscribes.txt

    # List all unsubscribed contacts
    python process_unsubscribes.py --list
"""

import os
import sys
import argparse
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = None


def get_supabase_client():
    """Return initialized Supabase client or raise a clear error."""
    if supabase is None:
        raise RuntimeError("Supabase client not initialized. Ensure environment variables are set.")
    return supabase


def unsubscribe_email(email: str, source: str = "manual") -> bool:
    """
    Mark a contact as unsubscribed.

    Args:
        email: Email address to unsubscribe
        source: Source of the unsubscribe request

    Returns:
        True if successful, False otherwise
    """
    client = get_supabase_client()
    email = email.strip().lower()

    # Find contact by any email field
    response = client.table('contacts').select('id, email, personal_email, work_email, first_name, last_name').or_(
        f"email.ilike.{email},personal_email.ilike.{email},work_email.ilike.{email}"
    ).execute()

    if not response.data:
        print(f"  [NOT FOUND] {email} - No matching contact")
        return False

    for contact in response.data:
        contact_id = contact['id']
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

        # Update the contact
        update_response = client.table('contacts').update({
            'unsubscribed': True,
            'unsubscribed_at': datetime.now().isoformat(),
            'unsubscribe_source': source
        }).eq('id', contact_id).execute()

        if update_response.data:
            print(f"  [UNSUBSCRIBED] {email} ({name or 'No name'}) - Contact ID: {contact_id}")
        else:
            print(f"  [ERROR] Failed to update {email}")
            return False

    return True


def unsubscribe_from_file(filepath: str, source: str = "batch_file") -> tuple:
    """
    Process unsubscribes from a file (one email per line).

    Returns:
        Tuple of (success_count, failure_count)
    """
    success = 0
    failure = 0

    with open(filepath, 'r') as f:
        emails = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print(f"\nProcessing {len(emails)} emails from {filepath}...")

    for email in emails:
        if unsubscribe_email(email, source):
            success += 1
        else:
            failure += 1

    return success, failure


def list_unsubscribed():
    """List all unsubscribed contacts."""
    client = get_supabase_client()
    response = client.table('contacts').select(
        'id, first_name, last_name, email, personal_email, work_email, unsubscribed_at, unsubscribe_source'
    ).eq('unsubscribed', True).order('unsubscribed_at', desc=True).execute()

    if not response.data:
        print("\nNo unsubscribed contacts found.")
        return

    print(f"\n{'='*80}")
    print(f"UNSUBSCRIBED CONTACTS ({len(response.data)} total)")
    print(f"{'='*80}")

    for contact in response.data:
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip() or "No name"
        email = contact.get('email') or contact.get('personal_email') or contact.get('work_email') or "No email"
        date = contact.get('unsubscribed_at', 'Unknown date')
        source = contact.get('unsubscribe_source', 'Unknown')

        print(f"  {name} <{email}>")
        print(f"    Unsubscribed: {date} | Source: {source}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Process email unsubscribe requests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python process_unsubscribes.py --email john@example.com
  python process_unsubscribes.py --file unsubscribes.txt
  python process_unsubscribes.py --list
        """
    )

    parser.add_argument('--email', type=str, help='Email address to unsubscribe')
    parser.add_argument('--file', type=str, help='File with emails to unsubscribe (one per line)')
    parser.add_argument('--list', action='store_true', help='List all unsubscribed contacts')
    parser.add_argument('--source', type=str, default='manual',
                        help='Source of unsubscribe (e.g., "email_reply", "manual")')

    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase configuration not found")
        sys.exit(1)

    try:
        global supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"ERROR: Failed to initialize Supabase client: {e}")
        sys.exit(1)

    if args.list:
        list_unsubscribed()
    elif args.email:
        print(f"\nUnsubscribing: {args.email}")
        unsubscribe_email(args.email, args.source)
    elif args.file:
        success, failure = unsubscribe_from_file(args.file, args.source)
        print(f"\nDone. Success: {success}, Failed/Not Found: {failure}")
    else:
        print("ERROR: Must specify --email, --file, or --list")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
