#!/usr/bin/env python3
"""
Supabase to MailerLite Sync Script

This script synchronizes contacts from a Supabase database to MailerLite,
placing them in appropriate groups based on their taxonomy classification.

Key features:
- Maps taxonomy classifications to MailerLite groups
- Only syncs verified email addresses
- Respects unsubscribe status
- Handles both new contacts and updates to existing contacts
- Tracks sync status in Supabase
"""

import os
import time
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any

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

# Mapping of taxonomy categories to MailerLite group IDs
# This will be populated by fetch_mailerlite_groups()
GROUP_ID_MAP = {}


def fetch_mailerlite_groups() -> Dict[str, str]:
    """
    Fetch all groups from MailerLite and create a mapping of group names to IDs.
    
    Returns:
        Dict[str, str]: A dictionary mapping group names to their MailerLite IDs
    """
    groups = {}
    page = 1
    limit = 100
    
    while True:
        response = requests.get(
            f"{MAILERLITE_BASE_URL}/groups",
            headers=MAILERLITE_HEADERS,
            params={"page": page, "limit": limit}
        )
        
        if response.status_code != 200:
            print(f"Error fetching MailerLite groups: {response.text}")
            break
        
        data = response.json()
        
        for group in data.get("data", []):
            # Store group name -> ID mapping
            groups[group["name"]] = group["id"]
        
        # Check if there are more pages
        if page >= data.get("meta", {}).get("last_page", 1):
            break
        
        page += 1
    
    return groups


def create_mailerlite_group(name: str) -> Optional[str]:
    """
    Create a new group in MailerLite.
    
    Args:
        name: Name of the group to create
        
    Returns:
        str: ID of the newly created group, or None if creation failed
    """
    response = requests.post(
        f"{MAILERLITE_BASE_URL}/groups",
        headers=MAILERLITE_HEADERS,
        json={"name": name}
    )
    
    if response.status_code in [200, 201]:
        return response.json()["data"]["id"]
    else:
        print(f"Failed to create group '{name}': {response.text}")
        return None


def get_or_create_group(taxonomy_category: str) -> Optional[str]:
    """
    Get the MailerLite group ID for a taxonomy category, creating it if needed.
    
    Args:
        taxonomy_category: The taxonomy category to map to a MailerLite group
        
    Returns:
        str: The MailerLite group ID, or None if group couldn't be created
    """
    # Normalize the taxonomy category name for MailerLite
    # Remove any special characters that might cause issues
    group_name = taxonomy_category
    
    # Check if we already have the group ID
    if group_name in GROUP_ID_MAP:
        return GROUP_ID_MAP[group_name]
    
    # Try to create the group
    group_id = create_mailerlite_group(group_name)
    if group_id:
        GROUP_ID_MAP[group_name] = group_id
        return group_id
    
    return None


def parse_taxonomy(taxonomy: str) -> tuple:
    """
    Parse the taxonomy string into main category and subcategory.
    
    Args:
        taxonomy: The taxonomy classification string (e.g. "Strategic Business Prospects: Corporate Impact Leaders")
        
    Returns:
        tuple: (main_category, full_category) where main_category is the part before the colon
    """
    if not taxonomy:
        return None, None
    
    parts = taxonomy.split(":", 1)
    main_category = parts[0].strip()
    full_category = taxonomy.strip()
    
    return main_category, full_category


def get_verified_contacts(batch_size: int = 100, last_id: int = 0, only_unsent: bool = True) -> List[Dict[str, Any]]:
    """
    Fetch verified contacts from Supabase using cursor-based pagination.
    Only returns contacts with verified emails (email_verified = TRUE).
    
    Args:
        batch_size: Number of contacts to fetch per batch
        last_id: ID of the last contact processed (used for pagination)
        only_unsent: If True, only fetch contacts that haven't been synced to MailerLite
        
    Returns:
        List[Dict[str, Any]]: List of contact records
    """
    query = supabase.table('vw_contacts_for_mailerlite')\
        .select('id, first_name, last_name, best_email, email, work_email, personal_email, company, position, taxonomy_classification, email_verified, synced_to_mailerlite')
    
    # Only sync contacts with verified emails
    query = query.eq('email_verified', True)
    
    # Apply filters
    if only_unsent:
        query = query.eq('synced_to_mailerlite', False)
    
    # Add cursor-based pagination - get records with ID greater than last processed ID
    if last_id > 0:
        query = query.gt('id', last_id)
    
    # Order by ID to ensure consistent pagination
    query = query.order('id', desc=False).limit(batch_size)
    
    response = query.execute()
    
    return response.data


def get_best_email(contact: Dict[str, Any]) -> Optional[str]:
    """
    Determine the best email to use for a contact.
    Uses the best_email from the view if available, otherwise falls back to prioritization.
    
    Args:
        contact: Contact record from Supabase
        
    Returns:
        str: The best email to use, or None if no valid email found
    """
    if contact.get('best_email'):
        return contact['best_email']
    elif contact.get('work_email'):
        return contact['work_email']
    elif contact.get('email'):
        return contact['email']
    elif contact.get('personal_email'):
        return contact['personal_email']
    else:
        return None


def sync_contact_to_mailerlite(contact: Dict[str, Any]) -> bool:
    """
    Sync a single contact to MailerLite.
    
    Args:
        contact: Contact record from Supabase
        
    Returns:
        bool: True if sync was successful, False otherwise
    """
    email = get_best_email(contact)
    if not email:
        print(f"Skipping contact ID {contact['id']}: No valid email found")
        return False
    
    # Parse taxonomy to get main category and full category
    main_category, full_category = parse_taxonomy(contact.get('taxonomy_classification', ''))
    
    # Prepare subscriber data
    subscriber_data = {
        "email": email,
        "fields": {
            "name": f"{contact.get('first_name', '') or ''} {contact.get('last_name', '') or ''}".strip(),
            "company": contact.get('company', '') or '',
            "position": contact.get('position', '') or '',
            "taxonomy": full_category or '',
            "source": "True Steele Contact Management Suite"
        }
    }
    
    # Check if we need to assign to a group
    if main_category:
        group_id = get_or_create_group(main_category)
        if group_id:
            subscriber_data["groups"] = [group_id]
    
    # Create/update subscriber
    response = requests.post(
        f"{MAILERLITE_BASE_URL}/subscribers",
        headers=MAILERLITE_HEADERS,
        json=subscriber_data
    )
    
    if response.status_code in [200, 201]:
        # Extract the subscriber ID from the response
        response_data = response.json()
        subscriber_id = response_data.get('data', {}).get('id')
        subscriber_groups = [group['id'] for group in response_data.get('data', {}).get('groups', [])]
        subscriber_status = response_data.get('data', {}).get('status')
        
        # Update Supabase with sync status and subscriber ID
        update_data = {
            'synced_to_mailerlite': True,
            'mailerlite_sync_date': datetime.now().isoformat()
        }
        
        # Only add these fields if they're not None
        if subscriber_id:
            update_data['mailerlite_subscriber_id'] = subscriber_id
        
        if subscriber_groups:
            update_data['mailerlite_groups'] = subscriber_groups
            
        if subscriber_status:
            update_data['mailerlite_status'] = subscriber_status
        
        update_response = supabase.table('contacts')\
            .update(update_data)\
            .eq('id', contact['id'])\
            .execute()
        
        if update_response.data:
            print(f"Successfully synced and updated contact: {email} (MailerLite ID: {subscriber_id})")
            return True
        else:
            print(f"Synced to MailerLite but failed to update Supabase for contact: {email}")
            return False
    else:
        print(f"Failed to sync contact {email} to MailerLite: {response.text}")
        return False


def batch_sync_contacts(batch_size: int = 100, max_contacts: int = None, 
                       only_unsent: bool = True, delay: float = 0.5):
    """
    Sync contacts from Supabase to MailerLite in batches.
    
    Args:
        batch_size: Number of contacts to process in each batch
        max_contacts: Maximum number of contacts to sync (None for all)
        only_unsent: If True, only sync contacts that haven't been synced before
        delay: Delay between API calls in seconds to respect rate limits
    """
    last_id = 0
    total_processed = 0
    total_success = 0
    
    # Fetch MailerLite groups to populate GROUP_ID_MAP
    global GROUP_ID_MAP
    GROUP_ID_MAP = fetch_mailerlite_groups()
    print(f"Found {len(GROUP_ID_MAP)} existing MailerLite groups")
    
    while True:
        print(f"Fetching contacts batch with IDs greater than {last_id}")
        contacts = get_verified_contacts(batch_size, last_id, only_unsent)
        
        if not contacts:
            print("No more contacts to process")
            break
        
        print(f"Processing batch of {len(contacts)} contacts")
        
        for contact in contacts:
            success = sync_contact_to_mailerlite(contact)
            if success:
                total_success += 1
            
            # Update the last ID processed for cursor-based pagination
            last_id = max(last_id, contact['id'])
            
            total_processed += 1
            time.sleep(delay)  # Respect API rate limits
            
            if max_contacts and total_processed >= max_contacts:
                print(f"Reached maximum contacts limit ({max_contacts})")
                return total_processed, total_success
    
    return total_processed, total_success


def setup_database_columns():
    """
    Add necessary columns to the Supabase contacts table for tracking sync status.
    """
    try:
        # Check if the columns already exist
        response = supabase.table('contacts')\
            .select('synced_to_mailerlite, mailerlite_sync_date')\
            .limit(1)\
            .execute()
        
        # If this didn't error out, the columns exist
        print("MailerLite sync columns already exist in the database")
        return True
    except Exception:
        # Columns don't exist, add them
        print("Adding MailerLite sync columns to the database...")
        
        # This requires SQL execution which may require admin privileges
        sql = """
        ALTER TABLE contacts 
        ADD COLUMN IF NOT EXISTS synced_to_mailerlite BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS mailerlite_sync_date TIMESTAMP WITHOUT TIME ZONE;
        """
        
        print("Please run the following SQL in your Supabase SQL editor:")
        print(sql)
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Sync contacts from Supabase to MailerLite')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing contacts')
    parser.add_argument('--max-contacts', type=int, default=None, help='Maximum number of contacts to process')
    parser.add_argument('--all', action='store_true', help='Process all contacts, not just previously unsent ones')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between API calls in seconds')
    parser.add_argument('--check-columns', action='store_true', help='Check/setup required database columns')
    parser.add_argument('--skip-verification', action='store_true', help='Skip email verification check (use with caution)')
    
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
    
    # Run the sync process
    print(f"Starting Supabase to MailerLite sync...")
    print(f"Batch size: {args.batch_size}")
    if args.max_contacts:
        print(f"Maximum contacts: {args.max_contacts}")
    print(f"Processing {'all' if args.all else 'only unsent'} contacts")
    print(f"Email verification check: {'DISABLED' if args.skip_verification else 'ENABLED'}")
    
    # If skip verification is enabled, we need to modify the get_verified_contacts function
    if args.skip_verification:
        global get_verified_contacts
        original_get_verified_contacts = get_verified_contacts
        
        # Define a temporary replacement that doesn't filter by email_verified
        def get_unverified_contacts(batch_size=100, last_id=0, only_unsent=True):
            query = supabase.table('vw_contacts_for_mailerlite')\
                .select('id, first_name, last_name, best_email, email, work_email, personal_email, company, position, taxonomy_classification, email_verified, synced_to_mailerlite')
            
            # Apply filters
            if only_unsent:
                query = query.eq('synced_to_mailerlite', False)
            
            # Add cursor-based pagination
            if last_id > 0:
                query = query.gt('id', last_id)
            
            # Order by ID and limit results
            query = query.order('id', desc=False).limit(batch_size)
            
            response = query.execute()
            
            return response.data
        
        # Replace the function for this run
        get_verified_contacts = get_unverified_contacts
        print("WARNING: Email verification check is disabled. All contacts may be synced regardless of verification status.")
    
    start_time = time.time()
    total_processed, total_success = batch_sync_contacts(
        batch_size=args.batch_size,
        max_contacts=args.max_contacts,
        only_unsent=not args.all,
        delay=args.delay
    )
    
    elapsed_time = time.time() - start_time
    
    print(f"Sync completed in {elapsed_time:.2f} seconds")
    print(f"Total contacts processed: {total_processed}")
    print(f"Successfully synced: {total_success}")
    print(f"Failed: {total_processed - total_success}")


if __name__ == "__main__":
    main() 