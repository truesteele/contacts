#!/usr/bin/env python3
"""
Check delivery status of sent emails and update database with bounces, complaints, etc.

Usage:
    python scripts/email_campaigns/check_delivery_status.py --campaign-id <id>
    python scripts/email_campaigns/check_delivery_status.py --campaign-id <id> --limit 100
"""

import os
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import resend
from supabase import create_client, Client

# Configuration
# Use full-access API key for reading email status (send-only key can't retrieve)
RESEND_API_KEY = os.getenv("RESEND_ALLACCESS_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Rate limit: 2 requests/second for Resend API
RATE_LIMIT_DELAY = 0.6  # 600ms between requests to stay under 2/sec limit


def get_supabase_client() -> Client:
    """Initialize Supabase client."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_sent_emails(campaign_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all sent emails with message IDs for a campaign."""
    client = get_supabase_client()

    # Query for emails with status 'sent' that have a message ID
    query = client.table('email_sends').select(
        'id, contact_id, email_address, resend_message_id, status'
    ).eq('campaign_id', campaign_id).not_.is_('resend_message_id', 'null')

    # Only check emails that haven't been updated to a final status
    # (exclude bounced, complained, opened, clicked as these are already final)
    query = query.in_('status', ['sent', 'delivered', 'delivery_delayed'])

    if limit:
        query = query.limit(limit)

    response = query.execute()
    return response.data


def check_email_status(message_id: str) -> Optional[Dict[str, Any]]:
    """Check the delivery status of a single email via Resend API."""
    try:
        result = resend.Emails.get(message_id)
        if isinstance(result, dict):
            return result
        return None
    except Exception as e:
        print(f"  Error checking {message_id}: {e}")
        return None


def update_email_status(send_id: int, new_status: str, details: Optional[str] = None):
    """Update the email status in the database."""
    client = get_supabase_client()
    now = datetime.utcnow().isoformat()

    update_data = {'status': new_status}

    # Set appropriate timestamp based on status
    if new_status == 'delivered':
        update_data['delivered_at'] = now
    elif new_status == 'bounced':
        update_data['bounced_at'] = now
    elif new_status == 'opened':
        update_data['opened_at'] = now
    elif new_status == 'clicked':
        update_data['clicked_at'] = now
        # clicked implies opened
        update_data['opened_at'] = now

    if details:
        update_data['error_message'] = details

    client.table('email_sends').update(update_data).eq('id', send_id).execute()


def mark_contact_email_invalid(contact_id: int, email_address: str, reason: str):
    """Mark the specific email as invalid on the contact record."""
    client = get_supabase_client()

    # Get current contact record
    contact = client.table('contacts').select(
        'email, personal_email, work_email'
    ).eq('id', contact_id).single().execute()

    if not contact.data:
        return

    data = contact.data
    update_data = {}

    # Determine which email field matches and clear it or mark as invalid
    # We'll add a note to track invalid emails
    notes_update = f"Bounced email ({reason}): {email_address}"

    # Get existing notes
    notes_response = client.table('contacts').select('notes').eq('id', contact_id).single().execute()
    existing_notes = notes_response.data.get('notes', '') if notes_response.data else ''

    if existing_notes:
        update_data['notes'] = f"{existing_notes}\n{notes_update}"
    else:
        update_data['notes'] = notes_update

    client.table('contacts').update(update_data).eq('id', contact_id).execute()


def mark_contact_unsubscribed(contact_id: int, source: str = 'spam_complaint'):
    """Mark a contact as unsubscribed (e.g., after spam complaint)."""
    client = get_supabase_client()

    client.table('contacts').update({
        'unsubscribed': True,
        'unsubscribed_at': datetime.utcnow().isoformat(),
        'unsubscribe_source': source
    }).eq('id', contact_id).execute()


def main():
    parser = argparse.ArgumentParser(description='Check delivery status of sent emails')
    parser.add_argument('--campaign-id', required=True, help='Campaign ID to check')
    parser.add_argument('--limit', type=int, help='Limit number of emails to check')
    parser.add_argument('--dry-run', action='store_true', help='Only show what would be updated')

    args = parser.parse_args()

    # Validate configuration
    if not RESEND_API_KEY:
        print("ERROR: RESEND_API_KEY not configured")
        sys.exit(1)

    resend.api_key = RESEND_API_KEY

    # Get emails to check
    print(f"Fetching sent emails for campaign: {args.campaign_id}")
    emails = get_sent_emails(args.campaign_id, args.limit)
    print(f"Found {len(emails)} emails to check")

    if not emails:
        print("No emails to check.")
        return

    # Track status changes
    status_counts = {
        'sent': 0,
        'delivered': 0,
        'bounced': 0,
        'complained': 0,
        'opened': 0,
        'clicked': 0,
        'delivery_delayed': 0,
        'failed': 0,
        'error': 0,
        'unchanged': 0
    }

    bounced_emails = []
    complained_emails = []

    print("\nChecking delivery status...")
    for i, email in enumerate(emails):
        message_id = email['resend_message_id']
        current_status = email['status']
        email_address = email['email_address']
        send_id = email['id']

        # Check status via API
        result = check_email_status(message_id)

        if result:
            # Map Resend event names to our status values
            last_event = result.get('last_event', 'unknown')

            # Normalize status (remove 'email.' prefix if present)
            if last_event.startswith('email.'):
                last_event = last_event.replace('email.', '')

            if last_event != current_status:
                print(f"  [{i+1}/{len(emails)}] {email_address}: {current_status} -> {last_event}")

                if not args.dry_run:
                    update_email_status(send_id, last_event)

                status_counts[last_event] = status_counts.get(last_event, 0) + 1

                # Track bounces and complaints
                if last_event == 'bounced':
                    bounced_emails.append({
                        'email': email_address,
                        'contact_id': email['contact_id']
                    })
                    if not args.dry_run:
                        mark_contact_email_invalid(
                            email['contact_id'],
                            email_address,
                            'hard_bounce'
                        )
                elif last_event == 'complained':
                    complained_emails.append({
                        'email': email_address,
                        'contact_id': email['contact_id']
                    })
                    if not args.dry_run:
                        mark_contact_unsubscribed(
                            email['contact_id'],
                            'spam_complaint'
                        )
            else:
                status_counts['unchanged'] += 1
        else:
            status_counts['error'] += 1

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(emails)} emails...")

    # Summary
    print("\n" + "=" * 50)
    print("DELIVERY STATUS SUMMARY")
    print("=" * 50)

    for status, count in sorted(status_counts.items()):
        if count > 0:
            print(f"  {status}: {count}")

    if bounced_emails:
        print(f"\n{len(bounced_emails)} BOUNCED EMAILS:")
        for entry in bounced_emails:
            print(f"  - {entry['email']} (contact_id: {entry['contact_id']})")

    if complained_emails:
        print(f"\n{len(complained_emails)} SPAM COMPLAINTS:")
        for entry in complained_emails:
            print(f"  - {entry['email']} (contact_id: {entry['contact_id']})")

    if args.dry_run:
        print("\n[DRY RUN - no changes were made]")

    # Suggest next steps
    if bounced_emails:
        print("\nNOTE: Consider marking these contacts as invalid in your database")
        print("to prevent sending to them in future campaigns.")


if __name__ == "__main__":
    main()
