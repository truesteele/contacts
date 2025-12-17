#!/usr/bin/env python3
"""
MailerLite Unsubscribe Tracker

This script syncs unsubscribe status from MailerLite back to Supabase.
It retrieves unsubscribed contacts from MailerLite and updates their
status in the Supabase database.
"""

import os
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any

import requests
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# MailerLite API configuration
MAILERLITE_API_KEY = os.getenv("MAILERLITE_API_KEY")
MAILERLITE_BASE_URL = os.getenv("MAILERLITE_API_URL", "https://connect.mailerlite.com/api")
MAILERLITE_HEADERS = {
    "Authorization": f"Bearer {MAILERLITE_API_KEY}",
    "Content-Type": "application/json"
}

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def setup_database_columns():
    """
    Ensure the Supabase database has the necessary columns for tracking unsubscribes.
    """
    try:
        # Check if the columns already exist
        response = supabase.table('contacts')\
            .select('unsubscribed, unsubscribed_at')\
            .limit(1)\
            .execute()
        
        # If this didn't error out, the columns exist
        print("Unsubscribe tracking columns already exist in the database")
        return True
    except Exception:
        # Columns don't exist, provide SQL to add them
        print("Adding unsubscribe tracking columns to the database...")
        
        # This requires SQL execution which may require admin privileges
        sql = """
        ALTER TABLE contacts 
        ADD COLUMN IF NOT EXISTS unsubscribed BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS unsubscribed_at TIMESTAMP WITHOUT TIME ZONE,
        ADD COLUMN IF NOT EXISTS unsubscribe_source VARCHAR(50);
        """
        
        print("Please run the following SQL in your Supabase SQL editor:")
        print(sql)
        return False


def get_unsubscribed_contacts_from_mailerlite(batch_size=100):
    """
    Retrieve unsubscribed contacts from MailerLite.
    
    Args:
        batch_size: Number of contacts to retrieve per page
        
    Returns:
        list: List of unsubscribed contact email addresses
    """
    unsubscribed_contacts = []
    page = 1
    
    while True:
        print(f"Fetching unsubscribed contacts page {page}...")
        response = requests.get(
            f"{MAILERLITE_BASE_URL}/subscribers",
            headers=MAILERLITE_HEADERS,
            params={
                "filter[status]": "unsubscribed",
                "limit": batch_size,
                "page": page
            }
        )
        
        if response.status_code != 200:
            print(f"Error fetching unsubscribed contacts: {response.text}")
            break
        
        data = response.json()
        
        for subscriber in data.get("data", []):
            unsubscribed_contacts.append({
                "email": subscriber["email"],
                "unsubscribed_at": subscriber.get("unsubscribed_at")
            })
        
        # Check if there are more pages
        if page >= data.get("meta", {}).get("last_page", 1):
            break
        
        page += 1
        time.sleep(0.5)  # Respect API rate limits
    
    print(f"Found {len(unsubscribed_contacts)} unsubscribed contacts in MailerLite")
    return unsubscribed_contacts


def update_unsubscribed_status_in_supabase(unsubscribed_contacts, dry_run=False):
    """
    Update unsubscribe status in Supabase for contacts that unsubscribed in MailerLite.
    
    Args:
        unsubscribed_contacts: List of unsubscribed contacts from MailerLite
        dry_run: If True, don't actually update the database
        
    Returns:
        dict: Statistics about the update operation
    """
    stats = {
        "total": len(unsubscribed_contacts),
        "updated": 0,
        "already_marked": 0,
        "not_found": 0
    }
    
    for contact in unsubscribed_contacts:
        email = contact["email"]
        unsubscribed_at = contact.get("unsubscribed_at")
        
        # Attempt to find the contact in Supabase
        # We need to check all possible email fields
        response = supabase.table('contacts')\
            .select('id, email, work_email, personal_email, unsubscribed')\
            .or_(f'email.eq.{email},work_email.eq.{email},personal_email.eq.{email}')\
            .execute()
        
        if not response.data:
            print(f"Contact with email {email} not found in Supabase")
            stats["not_found"] += 1
            continue
        
        # Check if already marked as unsubscribed
        contact_record = response.data[0]
        if contact_record.get("unsubscribed"):
            print(f"Contact {email} already marked as unsubscribed in Supabase")
            stats["already_marked"] += 1
            continue
        
        # Update the contact in Supabase
        if not dry_run:
            update_data = {
                "unsubscribed": True,
                "unsubscribe_source": "MailerLite",
                "unsubscribed_at": datetime.now().isoformat() if not unsubscribed_at else unsubscribed_at
            }
            
            update_response = supabase.table('contacts')\
                .update(update_data)\
                .eq('id', contact_record["id"])\
                .execute()
            
            if update_response.data:
                print(f"Updated unsubscribe status for {email}")
                stats["updated"] += 1
            else:
                print(f"Failed to update unsubscribe status for {email}")
        else:
            print(f"[DRY RUN] Would update unsubscribe status for {email}")
            stats["updated"] += 1
    
    return stats


def get_unsubscribed_contacts_from_supabase():
    """
    Get contacts marked as unsubscribed in Supabase.
    
    Returns:
        list: List of unsubscribed contact emails from Supabase
    """
    response = supabase.table('contacts')\
        .select('id, email, work_email, personal_email')\
        .eq('unsubscribed', True)\
        .execute()
    
    unsubscribed_emails = []
    
    for contact in response.data:
        # Add all available email addresses
        if contact.get("email"):
            unsubscribed_emails.append(contact["email"])
        if contact.get("work_email"):
            unsubscribed_emails.append(contact["work_email"])
        if contact.get("personal_email"):
            unsubscribed_emails.append(contact["personal_email"])
    
    return list(set(unsubscribed_emails))  # Remove duplicates


def ensure_contacts_unsubscribed_in_mailerlite(emails, dry_run=False):
    """
    Ensure contacts are marked as unsubscribed in MailerLite.
    Used to maintain consistency between Supabase and MailerLite.
    
    Args:
        emails: List of email addresses to ensure are unsubscribed
        dry_run: If True, don't actually make changes
        
    Returns:
        dict: Statistics about the operation
    """
    stats = {
        "total": len(emails),
        "updated": 0,
        "already_unsubscribed": 0,
        "not_found": 0,
        "error": 0
    }
    
    for email in emails:
        # First, check if the subscriber exists and what their status is
        response = requests.get(
            f"{MAILERLITE_BASE_URL}/subscribers/{email}",
            headers=MAILERLITE_HEADERS
        )
        
        if response.status_code == 404:
            print(f"Contact {email} not found in MailerLite")
            stats["not_found"] += 1
            continue
        
        if response.status_code != 200:
            print(f"Error checking subscriber {email}: {response.text}")
            stats["error"] += 1
            continue
        
        subscriber_data = response.json().get("data", {})
        if subscriber_data.get("status") == "unsubscribed":
            print(f"Contact {email} already unsubscribed in MailerLite")
            stats["already_unsubscribed"] += 1
            continue
        
        # Unsubscribe the contact
        if not dry_run:
            unsubscribe_response = requests.post(
                f"{MAILERLITE_BASE_URL}/subscribers/{email}/unsubscribe",
                headers=MAILERLITE_HEADERS
            )
            
            if unsubscribe_response.status_code in [200, 201]:
                print(f"Unsubscribed {email} in MailerLite")
                stats["updated"] += 1
            else:
                print(f"Failed to unsubscribe {email} in MailerLite: {unsubscribe_response.text}")
                stats["error"] += 1
        else:
            print(f"[DRY RUN] Would unsubscribe {email} in MailerLite")
            stats["updated"] += 1
        
        time.sleep(0.5)  # Respect API rate limits
    
    return stats


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Sync unsubscribe status between MailerLite and Supabase')
    parser.add_argument('--direction', choices=['from-mailerlite', 'to-mailerlite', 'both'], 
                        default='from-mailerlite', help='Direction of sync')
    parser.add_argument('--check-columns', action='store_true', help='Check/setup required database columns')
    parser.add_argument('--dry-run', action='store_true', help='Don\'t actually update the database')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for API requests')
    
    args = parser.parse_args()
    
    if not MAILERLITE_API_KEY:
        print("ERROR: MAILERLITE_API_KEY not found in environment variables")
        print("Please add it to your .env file")
        return
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase configuration not found in environment variables")
        print("Please add SUPABASE_URL and SUPABASE_SERVICE_KEY to your .env file")
        return
    
    # Check/setup database columns if requested
    if args.check_columns:
        setup_database_columns()
        return
    
    # Sync from MailerLite to Supabase
    if args.direction in ['from-mailerlite', 'both']:
        print("\n=== Syncing unsubscribes from MailerLite to Supabase ===")
        unsubscribed_contacts = get_unsubscribed_contacts_from_mailerlite(args.batch_size)
        stats = update_unsubscribed_status_in_supabase(unsubscribed_contacts, args.dry_run)
        
        print("\nMailerLite to Supabase sync stats:")
        print(f"Total unsubscribed contacts: {stats['total']}")
        print(f"Updated in Supabase: {stats['updated']}")
        print(f"Already marked unsubscribed: {stats['already_marked']}")
        print(f"Not found in Supabase: {stats['not_found']}")
    
    # Sync from Supabase to MailerLite
    if args.direction in ['to-mailerlite', 'both']:
        print("\n=== Syncing unsubscribes from Supabase to MailerLite ===")
        unsubscribed_emails = get_unsubscribed_contacts_from_supabase()
        stats = ensure_contacts_unsubscribed_in_mailerlite(unsubscribed_emails, args.dry_run)
        
        print("\nSupabase to MailerLite sync stats:")
        print(f"Total unsubscribed contacts: {stats['total']}")
        print(f"Unsubscribed in MailerLite: {stats['updated']}")
        print(f"Already unsubscribed: {stats['already_unsubscribed']}")
        print(f"Not found in MailerLite: {stats['not_found']}")
        print(f"Errors: {stats['error']}")


if __name__ == "__main__":
    main() 