#!/usr/bin/env python3
"""
Email Verification with ZeroBounce

This script verifies email addresses using ZeroBounce's API without
sending any emails to contacts. It updates the verification status in Supabase.

Usage:
  python verify_emails.py --batch-size 100
  python verify_emails.py --single-email "test@example.com"
  python verify_emails.py --taxonomy "Strategic Business Prospects"
  python verify_emails.py --mailerlite-synced
"""

import os
import time
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import requests
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# ZeroBounce API configuration
ZEROBOUNCE_API_KEY = os.getenv("ZEROBOUNCE_API_KEY")
ZEROBOUNCE_API_URL = "https://api.zerobounce.net/v2"

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_zerobounce_credits() -> int:
    """
    Check the number of credits available in your ZeroBounce account.
    
    Returns:
        int: Number of credits available
    """
    response = requests.get(
        f"{ZEROBOUNCE_API_URL}/getcredits",
        params={"api_key": ZEROBOUNCE_API_KEY}
    )
    
    if response.status_code != 200:
        print(f"Error checking ZeroBounce credits: {response.text}")
        return 0
    
    data = response.json()
    # Extract credits and convert to integer (API might return it as a string)
    try:
        credits = int(data.get("Credits", 0))
    except (ValueError, TypeError):
        # If conversion fails, print the raw response and default to 0
        print(f"Warning: Unable to parse credits from response: {data}")
        credits = 0
        
    print(f"ZeroBounce credits available: {credits}")
    return credits

def verify_single_email(email: str) -> Dict[str, Any]:
    """
    Verify a single email address with ZeroBounce.
    
    Args:
        email: Email address to verify
        
    Returns:
        Dict[str, Any]: Verification result with status and details
    """
    response = requests.get(
        f"{ZEROBOUNCE_API_URL}/validate",
        params={
            "api_key": ZEROBOUNCE_API_KEY,
            "email": email,
            "ip_address": ""  # Optional IP address
        }
    )
    
    if response.status_code != 200:
        print(f"Error verifying email {email}: {response.text}")
        return {
            "email": email,
            "status": "error",
            "sub_status": "",
            "is_valid": False,
            "is_catch_all": False,
            "error": response.text
        }
    
    data = response.json()
    
    # Handle catch-all domains as a special case - not automatically invalid
    status = data.get("status", "")
    is_catch_all = status == "catch-all"
    
    # Map ZeroBounce status to our system
    result = {
        "email": email,
        "status": status,
        "sub_status": data.get("sub_status", ""),
        # Consider catch-all as valid since many are actually valid emails
        "is_valid": status == "valid" or is_catch_all,
        "is_catch_all": is_catch_all,
        "did_you_mean": data.get("did_you_mean", ""),
        "domain_age_days": data.get("domain_age_days", None),
        "first_name": data.get("firstname", ""),
        "last_name": data.get("lastname", ""),
        "gender": data.get("gender", ""),
        "country": data.get("country", ""),
        "region": data.get("region", ""),
        "city": data.get("city", ""),
        "zipcode": data.get("zipcode", ""),
        "processed_at": data.get("processed_at", "")
    }
    
    return result

def verify_email_batch(emails: List[str], max_batch_size: int = 100) -> List[Dict[str, Any]]:
    """
    Verify a batch of email addresses with ZeroBounce.
    Uses individual verification for each email to avoid batch API issues.
    
    Args:
        emails: List of email addresses to verify
        max_batch_size: Maximum batch size (ignored, kept for backward compatibility)
        
    Returns:
        List[Dict[str, Any]]: List of verification results
    """
    # Ensure we don't exceed ZeroBounce's rate limits
    if len(emails) > 100:
        print(f"Warning: Large batch size {len(emails)}. This may take some time.")
    
    results = []
    
    # Process each email individually instead of using batch API
    for email in emails:
        try:
            # Verify each email individually
            result = verify_single_email(email)
            results.append(result)
            
            # Add a small delay between requests to respect rate limits
            time.sleep(0.2)
        except Exception as e:
            print(f"Error verifying email {email}: {str(e)}")
            # Add a basic error result to keep the batch processing going
            results.append({
                "email": email,
                "status": "error",
                "sub_status": "",
                "is_valid": False,
                "is_catch_all": False,
                "error": str(e)
            })
    
    return results

def update_contact_email_status(contact_id: int, email_field: str, result: Dict[str, Any]) -> bool:
    """
    Update the email verification status for a contact in Supabase.
    
    Args:
        contact_id: ID of the contact to update
        email_field: Field name containing the email ('email', 'work_email', or 'personal_email')
        result: Email verification result from ZeroBounce
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    # First get the contact to check if it was synced to MailerLite
    contact_response = supabase.table('contacts')\
        .select('first_name, last_name, synced_to_mailerlite, mailerlite_subscriber_id, mailerlite_sync_date')\
        .eq('id', contact_id)\
        .execute()
    
    if not contact_response.data:
        print(f"Error: Could not find contact with ID {contact_id}")
        return False
    
    contact = contact_response.data[0]
    was_synced_to_mailerlite = contact.get('synced_to_mailerlite', False)
    mailerlite_id = contact.get('mailerlite_subscriber_id')
    
    # Set the verification due date - 90 days for all valid and catch-all emails
    # Only truly invalid emails need to be checked more frequently
    verification_due_date = (datetime.now() + timedelta(days=90)).isoformat()
    
    # Prepare update data
    update_data = {
        'email_verified': result["is_valid"],
        'email_is_catch_all': result["is_catch_all"],
        'email_verification_source': 'ZeroBounce',
        'email_verification_due_at': verification_due_date,
        'email_verification_attempts': supabase.table('contacts').select('email_verification_attempts').eq('id', contact_id).execute().data[0].get('email_verification_attempts', 0) + 1,
        'email_verified_at': datetime.now().isoformat()
    }
    
    # If it's truly invalid, also reset the synced_to_mailerlite flag to prevent syncing
    # but don't do this for catch-all domains, which may still be valid
    if not result["is_valid"] and not result["is_catch_all"]:
        update_data['synced_to_mailerlite'] = False
        
        if was_synced_to_mailerlite:
            update_data['mailerlite_update_required'] = True
            update_data['mailerlite_update_reason'] = f"Invalid email ({result['status']}) detected by ZeroBounce on {datetime.now().strftime('%Y-%m-%d')}"
    
    # Perform the update
    update_response = supabase.table('contacts').update(update_data).eq('id', contact_id).execute()
    
    if not update_response.data:
        print(f"Failed to update contact {contact_id} with status for {email_field}")
        return False
    
    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    email = result["email"]
    
    # Create a status message that includes catch-all information
    if result["is_catch_all"]:
        status_info = f"Valid (catch-all domain)"
    else:
        status_info = f"{'Valid' if result['is_valid'] else 'Invalid'} ({result['status']})"
    
    # Add more info if it was synced to MailerLite and is truly invalid (not catch-all)
    if was_synced_to_mailerlite and not result["is_valid"] and not result["is_catch_all"]:
        print(f"📋 MAILERLITE UPDATE NEEDED: {name} <{email}> - {status_info} - MailerLite ID: {mailerlite_id}")
        
        # Append to a report file for easy tracking
        with open("mailerlite_invalid_emails.csv", "a") as f:
            if os.path.getsize("mailerlite_invalid_emails.csv") == 0:
                # Write header if file is empty
                f.write("contact_id,name,email,verification_status,sub_status,mailerlite_id,verification_date\n")
            f.write(f"{contact_id},\"{name}\",{email},{result['status']},{result['sub_status']},{mailerlite_id},{datetime.now().strftime('%Y-%m-%d')}\n")
    else:
        print(f"Updated contact {contact_id} {email_field}: {status_info}")
    
    return True

def get_contacts_for_verification(batch_size: int = 100, taxonomy: Optional[str] = None, last_id: int = 0, mailerlite_synced: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, List[int]]]:
    """
    Retrieve contacts from Supabase that need email verification.
    Uses cursor-based pagination for efficiency.
    
    Args:
        batch_size: Number of contacts to retrieve
        taxonomy: Optional taxonomy filter
        last_id: Last ID processed for pagination
        mailerlite_synced: If True, only get contacts already synced to MailerLite
        
    Returns:
        Tuple[List[Dict[str, Any]], Dict[str, List[int]]]:
            List of contacts and a dictionary mapping email types to contact IDs
    """
    # Start with a base query that selects MailerLite sync status
    query = supabase.table('contacts')\
        .select('id, first_name, last_name, email, work_email, personal_email, email_verified, email_verification_due_at, synced_to_mailerlite, mailerlite_subscriber_id')
    
    if mailerlite_synced:
        # Filter for contacts that have been synced to MailerLite
        query = query.eq('synced_to_mailerlite', True)
        
        # Also ensure we only verify emails that need verification
        # First get the ones that have never been verified
        query = query.is_('email_verified', None)
        
        # Add a condition for verification being due
        current_time = datetime.now().isoformat()
        query = query.or_(f"email_verification_due_at.lt.{current_time}")
    else:
        # Default behavior: filter for contacts that need verification
        query = query.is_('email_verified', None)  # Never been verified
        # Or due for verification
        query = query.or_(f"email_verification_due_at.lt.{datetime.now().isoformat()}")
    
    # Add taxonomy filter if specified
    if taxonomy:
        query = query.like('taxonomy_classification', f"{taxonomy}%")
    
    # Add cursor-based pagination
    if last_id > 0:
        query = query.gt('id', last_id)
    
    # Order by ID and limit results
    query = query.order('id').limit(batch_size)
    
    # Execute the query
    response = query.execute()
    
    contacts = response.data
    email_map = {
        "email": [],
        "work_email": [],
        "personal_email": []
    }
    
    # Build map of email types to contact IDs
    for contact in contacts:
        if contact.get('email'):
            email_map["email"].append(contact['id'])
        if contact.get('work_email'):
            email_map["work_email"].append(contact['id'])
        if contact.get('personal_email'):
            email_map["personal_email"].append(contact['id'])
    
    return contacts, email_map

def verify_contacts_in_batches(batch_size: int = 100, max_contacts: Optional[int] = None, 
                              taxonomy: Optional[str] = None, delay: float = 1.0,
                              mailerlite_synced: bool = False):
    """
    Verify contacts in batches using ZeroBounce.
    
    Args:
        batch_size: Size of each batch to process
        max_contacts: Maximum number of contacts to process
        taxonomy: Optional taxonomy filter
        delay: Delay between API calls in seconds
        mailerlite_synced: If True, only verify contacts already synced to MailerLite
    """
    # Check available credits first
    credits = check_zerobounce_credits()
    if credits <= 0:
        print("No ZeroBounce credits available. Aborting.")
        return
    
    last_id = 0
    total_processed = 0
    total_valid = 0
    total_invalid = 0
    total_catch_all = 0
    
    while True:
        # Get next batch of contacts
        contacts, email_map = get_contacts_for_verification(batch_size, taxonomy, last_id, mailerlite_synced)
        
        if not contacts:
            print("No more contacts to process")
            break
        
        print(f"Processing batch of {len(contacts)} contacts")
        
        # Process each email type separately
        for email_type in ["work_email", "email", "personal_email"]:
            contact_ids = email_map[email_type]
            if not contact_ids:
                continue
            
            # Get the emails for this type
            emails = []
            id_to_email = {}
            
            for contact in contacts:
                if contact['id'] in contact_ids and contact.get(email_type):
                    emails.append(contact[email_type])
                    id_to_email[contact[email_type]] = contact['id']
            
            if not emails:
                continue
            
            print(f"Verifying {len(emails)} {email_type} addresses...")
            
            # Process in smaller batches to respect API limits
            for i in range(0, len(emails), 100):
                batch = emails[i:i+100]
                
                # Check if we have enough credits
                if len(batch) > credits:
                    print(f"Warning: Only {credits} credits left, but need {len(batch)}. Processing what we can.")
                    batch = batch[:credits]
                    if not batch:
                        print("No more credits available. Stopping.")
                        break
                
                # Verify the batch
                results = verify_email_batch(batch)
                
                for result in results:
                    email = result["email"]
                    contact_id = id_to_email.get(email)
                    
                    if not contact_id:
                        print(f"Error: Could not find contact ID for email {email}")
                        continue
                    
                    # Update the contact
                    success = update_contact_email_status(contact_id, email_type, result)
                    
                    if success:
                        if result["is_catch_all"]:
                            total_catch_all += 1
                        elif result["is_valid"]:
                            total_valid += 1
                        else:
                            total_invalid += 1
                    
                    total_processed += 1
                
                # Check if we've reached the maximum contacts
                if max_contacts and total_processed >= max_contacts:
                    print(f"Reached maximum contacts limit ({max_contacts})")
                    return total_processed, total_valid, total_invalid, total_catch_all
                
                # Update credits and delay for API rate limits
                credits -= len(batch)
                time.sleep(delay)
            
            # Check credits after each email type batch
            if credits <= 0:
                print("No more ZeroBounce credits available. Stopping.")
                return total_processed, total_valid, total_invalid, total_catch_all
        
        # Update the last ID for pagination
        if contacts:
            last_id = max(contact['id'] for contact in contacts)
    
    return total_processed, total_valid, total_invalid, total_catch_all

def summarize_mailerlite_invalid_emails():
    """
    Generate a summary of invalid emails that were synced to MailerLite.
    """
    report_file = "mailerlite_invalid_emails.csv"
    if not os.path.exists(report_file) or os.path.getsize(report_file) == 0:
        print("No invalid MailerLite emails found.")
        return
    
    try:
        import pandas as pd
        df = pd.read_csv(report_file)
        
        print("\n=== MAILERLITE INVALID EMAILS REPORT ===")
        print(f"Total invalid emails synced to MailerLite: {len(df)}")
        
        if len(df) > 0:
            # Group by status
            status_counts = df['verification_status'].value_counts()
            print("\nBreakdown by verification status:")
            for status, count in status_counts.items():
                print(f"  - {status}: {count}")
            
            # Show sample of contacts
            print("\nSample of affected contacts:")
            sample = df.head(min(5, len(df)))
            for _, row in sample.iterrows():
                print(f"  - {row['name']} <{row['email']}> ({row['verification_status']})")
            
            print(f"\nFull report available in: {report_file}")
            print("Consider running the following to update MailerLite:")
            print("  python track_unsubscribes.py --direction to-mailerlite")
    except ImportError:
        print(f"Invalid emails report saved to: {report_file}")
        print("Install pandas to see a detailed summary.")

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Verify email addresses using ZeroBounce')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing contacts')
    parser.add_argument('--max-contacts', type=int, default=None, help='Maximum number of contacts to process')
    parser.add_argument('--taxonomy', type=str, default=None, help='Only process contacts with this taxonomy prefix')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between API calls in seconds')
    parser.add_argument('--single-email', type=str, default=None, help='Verify a single email address')
    parser.add_argument('--mailerlite-synced', action='store_true', help='Only verify contacts already synced to MailerLite')
    
    args = parser.parse_args()
    
    if not ZEROBOUNCE_API_KEY:
        print("ERROR: ZEROBOUNCE_API_KEY not found in environment variables")
        print("Please add it to your .env file")
        return
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase configuration not found in environment variables")
        print("Please add SUPABASE_URL and SUPABASE_SERVICE_KEY to your .env file")
        return
    
    # Create/reset the report file if we're checking MailerLite synced contacts
    if args.mailerlite_synced:
        with open("mailerlite_invalid_emails.csv", "w") as f:
            f.write("contact_id,name,email,verification_status,sub_status,mailerlite_id,verification_date\n")
    
    # Process a single email if specified
    if args.single_email:
        print(f"Verifying single email: {args.single_email}")
        result = verify_single_email(args.single_email)
        print(json.dumps(result, indent=2))
        return
    
    # Otherwise process contacts in batches
    print(f"Starting email verification process...")
    print(f"Batch size: {args.batch_size}")
    if args.max_contacts:
        print(f"Maximum contacts: {args.max_contacts}")
    if args.taxonomy:
        print(f"Taxonomy filter: {args.taxonomy}")
    if args.mailerlite_synced:
        print(f"Only verifying contacts already synced to MailerLite")
    
    start_time = time.time()
    total_processed, total_valid, total_invalid, total_catch_all = verify_contacts_in_batches(
        batch_size=args.batch_size,
        max_contacts=args.max_contacts,
        taxonomy=args.taxonomy,
        delay=args.delay,
        mailerlite_synced=args.mailerlite_synced
    )
    
    elapsed_time = time.time() - start_time
    
    print(f"Process completed in {elapsed_time:.2f} seconds")
    print(f"Total emails processed: {total_processed}")
    print(f"Valid emails: {total_valid}")
    print(f"Catch-all domains (treated as valid): {total_catch_all}")
    print(f"Invalid emails: {total_invalid}")
    print(f"Invalid rate: {(total_invalid / total_processed * 100) if total_processed else 0:.2f}%")
    
    # Show notification if invalid emails were found in MailerLite synced contacts
    if args.mailerlite_synced and total_invalid > 0:
        print(f"\n⚠️ WARNING: Found {total_invalid} invalid emails among contacts synced to MailerLite.")
        # Generate a detailed report
        summarize_mailerlite_invalid_emails()

if __name__ == "__main__":
    main() 