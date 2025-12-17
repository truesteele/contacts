#!/usr/bin/env python3
"""
Email Verification and MailerLite Management

This script verifies email addresses for contacts that have been synced to MailerLite
and takes appropriate actions for invalid emails both in Supabase and MailerLite.

Usage:
  python verify_and_update_mailerlite.py --batch-size 100
  python verify_and_update_mailerlite.py --max-contacts 200
  python verify_and_update_mailerlite.py --dry-run  # Only verify, don't update MailerLite
"""

import os
import time
import argparse
import json
import csv
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

# MailerLite configuration
MAILERLITE_API_KEY = os.getenv("MAILERLITE_API_KEY")
MAILERLITE_API_URL = "https://connect.mailerlite.com/api"
MAILERLITE_HEADERS = {
    "Authorization": f"Bearer {MAILERLITE_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Constants
INVALID_EMAIL_GROUP_NAME = "Invalid Emails"
INVALID_EMAIL_TAG_NAME = "Invalid Email"

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
    
    # Handle catch-all domains as a special case
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

def update_contact_email_status(contact_id: int, email_field: str, result: Dict[str, Any], dry_run: bool = False) -> Dict:
    """
    Update the email verification status for a contact in Supabase.
    
    Args:
        contact_id: ID of the contact to update
        email_field: Field name containing the email ('email', 'work_email', or 'personal_email')
        result: Email verification result from ZeroBounce
        dry_run: If True, don't actually update the database
        
    Returns:
        Dict: Contact data with updated information
    """
    # First get the contact to check if it was synced to MailerLite
    contact_response = supabase.table('contacts')\
        .select('id, first_name, last_name, email, work_email, personal_email, synced_to_mailerlite, mailerlite_subscriber_id, mailerlite_sync_date')\
        .eq('id', contact_id)\
        .execute()
    
    if not contact_response.data:
        print(f"Error: Could not find contact with ID {contact_id}")
        return {}
    
    contact = contact_response.data[0]
    was_synced_to_mailerlite = contact.get('synced_to_mailerlite', False)
    mailerlite_id = contact.get('mailerlite_subscriber_id')
    
    # Set the verification due date - 90 days for all valid emails, including catch-all
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
    
    # If it's truly invalid (not catch-all), reset the synced_to_mailerlite flag
    # Catch-all domains are considered valid for MailerLite purposes
    if not result["is_valid"] and not result["is_catch_all"] and was_synced_to_mailerlite:
        update_data['mailerlite_update_required'] = True
        update_data['mailerlite_update_reason'] = f"Invalid email ({result['status']}) detected by ZeroBounce on {datetime.now().strftime('%Y-%m-%d')}"
    
    # Perform the update unless this is a dry run
    if not dry_run:
        update_response = supabase.table('contacts').update(update_data).eq('id', contact_id).execute()
        
        if not update_response.data:
            print(f"Failed to update contact {contact_id} with status for {email_field}")
            return contact  # Return original contact data
    
    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    email = result["email"]
    
    # Create status message with catch-all information
    if result["is_catch_all"]:
        status_info = f"Valid (catch-all domain)"
    else:
        status_info = f"{'Valid' if result['is_valid'] else 'Invalid'} ({result['status']})"
    
    # Add contact info to the returned data including catch-all status
    contact.update({
        'email_verified': result["is_valid"],
        'verification_status': result['status'],
        'verification_sub_status': result['sub_status'],
        'is_catch_all': result["is_catch_all"]
    })
    
    # Special handling for different scenarios
    if was_synced_to_mailerlite:
        if not result["is_valid"] and not result["is_catch_all"]:
            # Truly invalid and synced to MailerLite
            print(f"📋 MAILERLITE UPDATE NEEDED: {name} <{email}> - {status_info} - MailerLite ID: {mailerlite_id}")
            contact.update({'needs_mailerlite_update': True})
            
            # Append to the report file for truly invalid emails
            with open("mailerlite_invalid_emails.csv", "a") as f:
                f.write(f"{contact_id},\"{name}\",{email},{result['status']},{result['sub_status']},{mailerlite_id},{datetime.now().strftime('%Y-%m-%d')}\n")
        
        elif result["is_catch_all"]:
            # Catch-all domain emails need special tagging but remain active in MailerLite
            print(f"📊 MAILERLITE CATCH-ALL DOMAIN: {name} <{email}> - {status_info} - MailerLite ID: {mailerlite_id}")
            contact.update({'needs_mailerlite_catch_all_tag': True})
            
            # Append to a separate catch-all report file
            with open("mailerlite_catch_all_emails.csv", "a") as f:
                if os.path.getsize("mailerlite_catch_all_emails.csv") == 0:
                    # Write header if file is empty
                    f.write("contact_id,name,email,verification_status,sub_status,mailerlite_id,verification_date\n")
                f.write(f"{contact_id},\"{name}\",{email},{result['status']},{result['sub_status']},{mailerlite_id},{datetime.now().strftime('%Y-%m-%d')}\n")
        else:
            # Valid email
            action = "Would update" if dry_run else "Updated"
            print(f"{action} contact {contact_id} {email_field}: {status_info}")
    else:
        # Not synced to MailerLite
        action = "Would update" if dry_run else "Updated"
        print(f"{action} contact {contact_id} {email_field}: {status_info}")
    
    return contact

def get_contacts_for_verification(batch_size: int = 100, last_id: int = 0) -> Tuple[List[Dict[str, Any]], Dict[str, List[int]]]:
    """
    Retrieve contacts from Supabase that have been synced to MailerLite.
    Uses cursor-based pagination for efficiency.
    
    Args:
        batch_size: Number of contacts to retrieve
        last_id: Last ID processed for pagination
        
    Returns:
        Tuple[List[Dict[str, Any]], Dict[str, List[int]]]:
            List of contacts and a dictionary mapping email types to contact IDs
    """
    # Get contacts that have been synced to MailerLite
    query = supabase.table('contacts')\
        .select('id, first_name, last_name, email, work_email, personal_email, email_verified, email_verification_due_at, synced_to_mailerlite, mailerlite_subscriber_id')\
        .eq('synced_to_mailerlite', True)
    
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
                              delay: float = 1.0, dry_run: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Verify contacts in batches using ZeroBounce and collect invalid contacts for MailerLite update.
    
    Args:
        batch_size: Size of each batch to process
        max_contacts: Maximum number of contacts to process
        delay: Delay between API calls in seconds
        dry_run: If True, don't actually update databases
        
    Returns:
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
            List of invalid contacts and list of catch-all domain contacts
    """
    # Check available credits first
    credits = check_zerobounce_credits()
    if credits <= 0:
        print("No ZeroBounce credits available. Aborting.")
        return [], []
    
    last_id = 0
    total_processed = 0
    total_valid = 0
    total_invalid = 0
    total_catch_all = 0
    invalid_contacts = []
    catch_all_contacts = []
    
    # Create/reset the report files
    with open("mailerlite_invalid_emails.csv", "w") as f:
        f.write("contact_id,name,email,verification_status,sub_status,mailerlite_id,verification_date\n")
    
    with open("mailerlite_catch_all_emails.csv", "w") as f:
        f.write("contact_id,name,email,verification_status,sub_status,mailerlite_id,verification_date\n")
    
    while True:
        # Get next batch of contacts
        contacts, email_map = get_contacts_for_verification(batch_size, last_id)
        
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
                    updated_contact = update_contact_email_status(contact_id, email_type, result, dry_run)
                    
                    if updated_contact:
                        if result["is_catch_all"]:
                            total_catch_all += 1
                            # Track catch-all contacts for special handling in MailerLite
                            if updated_contact.get('needs_mailerlite_catch_all_tag'):
                                catch_all_contacts.append(updated_contact)
                        elif result["is_valid"]:
                            total_valid += 1
                        else:
                            total_invalid += 1
                            
                            # Track invalid contacts for MailerLite update
                            if updated_contact.get('needs_mailerlite_update'):
                                invalid_contacts.append(updated_contact)
                    
                    total_processed += 1
                
                # Check if we've reached the maximum contacts
                if max_contacts and total_processed >= max_contacts:
                    print(f"Reached maximum contacts limit ({max_contacts})")
                    return invalid_contacts, catch_all_contacts
                
                # Update credits and delay for API rate limits
                credits -= len(batch)
                time.sleep(delay)
            
            # Check credits after each email type batch
            if credits <= 0:
                print("No more ZeroBounce credits available. Stopping.")
                return invalid_contacts, catch_all_contacts
        
        # Update the last ID for pagination
        if contacts:
            last_id = max(contact['id'] for contact in contacts)
    
    print(f"Process completed successfully.")
    print(f"Total emails processed: {total_processed}")
    print(f"Valid emails: {total_valid}")
    print(f"Catch-all domain emails: {total_catch_all}")
    print(f"Invalid emails: {total_invalid}")
    print(f"Invalid rate: {(total_invalid / total_processed * 100) if total_processed else 0:.2f}%")
    
    return invalid_contacts, catch_all_contacts

def setup_mailerlite_invalid_group() -> str:
    """
    Set up or find the MailerLite group for invalid emails.
    
    Returns:
        str: ID of the invalid emails group
    """
    # Check if the group already exists
    response = requests.get(
        f"{MAILERLITE_API_URL}/groups",
        headers=MAILERLITE_HEADERS
    )
    
    if response.status_code != 200:
        print(f"Error checking MailerLite groups: {response.text}")
        return None
    
    groups = response.json().get("data", [])
    
    # Look for our invalid emails group
    for group in groups:
        if group.get("name") == INVALID_EMAIL_GROUP_NAME:
            print(f"Found existing Invalid Emails group with ID: {group.get('id')}")
            return group.get("id")
    
    # Create the group if it doesn't exist
    response = requests.post(
        f"{MAILERLITE_API_URL}/groups",
        headers=MAILERLITE_HEADERS,
        json={"name": INVALID_EMAIL_GROUP_NAME}
    )
    
    if response.status_code != 201:
        print(f"Error creating Invalid Emails group: {response.text}")
        return None
    
    group_id = response.json().get("data", {}).get("id")
    print(f"Created new Invalid Emails group with ID: {group_id}")
    return group_id

def setup_mailerlite_invalid_tag() -> str:
    """
    Set up or find the MailerLite tag for invalid emails.
    
    Returns:
        str: Name of the invalid emails tag
    """
    # Check if the tag already exists - just return the name since we use it, not an ID
    print(f"Using tag: {INVALID_EMAIL_TAG_NAME} for invalid emails")
    return INVALID_EMAIL_TAG_NAME

def process_invalid_emails_in_mailerlite(invalid_contacts: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """
    Process invalid emails in MailerLite by:
    1. Adding them to the Invalid Emails group
    2. Tagging them as Invalid Email
    3. Updating their status to unsubscribed
    
    Args:
        invalid_contacts: List of contacts with invalid emails
        dry_run: If True, don't actually update MailerLite
        
    Returns:
        int: Number of successfully processed contacts
    """
    if not invalid_contacts:
        print("No invalid emails to process in MailerLite")
        return 0
    
    # Set up required MailerLite infrastructure
    invalid_group_id = None if dry_run else setup_mailerlite_invalid_group()
    invalid_tag = setup_mailerlite_invalid_tag()
    
    successful_updates = 0
    
    for contact in invalid_contacts:
        mailerlite_id = contact.get("mailerlite_subscriber_id")
        if not mailerlite_id:
            print(f"No MailerLite ID for contact {contact.get('id')}, skipping")
            continue
        
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        email_field = next((field for field in ["email", "work_email", "personal_email"] 
                          if contact.get(field) and contact.get('verification_status')), None)
        
        if not email_field:
            print(f"No verified email field found for contact {contact.get('id')}, skipping")
            continue
            
        email = contact.get(email_field)
        verification_status = contact.get('verification_status')
        
        if dry_run:
            print(f"DRY RUN: Would update MailerLite for {name} <{email}> ({verification_status})")
            successful_updates += 1
            continue
        
        try:
            # 1. Update subscriber status to unsubscribed
            response = requests.put(
                f"{MAILERLITE_API_URL}/subscribers/{mailerlite_id}",
                headers=MAILERLITE_HEADERS,
                json={
                    "status": "unsubscribed",
                    "unsubscribe_reason": f"Invalid email ({verification_status}) detected by ZeroBounce"
                }
            )
            
            if response.status_code not in [200, 201]:
                print(f"Error updating subscriber status for {email}: {response.text}")
                continue
                
            # 2. Add to invalid emails group
            if invalid_group_id:
                response = requests.post(
                    f"{MAILERLITE_API_URL}/subscribers/{mailerlite_id}/groups/{invalid_group_id}",
                    headers=MAILERLITE_HEADERS
                )
                
                if response.status_code not in [200, 201, 204]:
                    print(f"Error adding {email} to Invalid Emails group: {response.text}")
            
            # 3. Add invalid email tag
            response = requests.post(
                f"{MAILERLITE_API_URL}/subscribers/{mailerlite_id}/tags",
                headers=MAILERLITE_HEADERS,
                json={"tags": [invalid_tag]}
            )
            
            if response.status_code not in [200, 201, 204]:
                print(f"Error tagging {email} as Invalid Email: {response.text}")
                continue
            
            print(f"✅ Successfully processed {name} <{email}> in MailerLite (unsubscribed and tagged)")
            successful_updates += 1
            
        except Exception as e:
            print(f"Error updating MailerLite for {email}: {str(e)}")
    
    return successful_updates

def process_catch_all_emails_in_mailerlite(catch_all_contacts: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """
    Process catch-all domain emails in MailerLite by tagging them appropriately.
    Unlike invalid emails, catch-all domains remain active subscribers.
    
    Args:
        catch_all_contacts: List of contacts with catch-all domain emails
        dry_run: If True, don't actually update MailerLite
        
    Returns:
        int: Number of successfully processed contacts
    """
    if not catch_all_contacts:
        print("No catch-all domain emails to process in MailerLite")
        return 0
    
    # Set up tag for catch-all domains
    catch_all_tag = "Catch-All Domain"
    print(f"Using tag: {catch_all_tag} for catch-all domain emails")
    
    successful_updates = 0
    
    for contact in catch_all_contacts:
        mailerlite_id = contact.get("mailerlite_subscriber_id")
        if not mailerlite_id:
            print(f"No MailerLite ID for contact {contact.get('id')}, skipping")
            continue
        
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        email_field = next((field for field in ["email", "work_email", "personal_email"] 
                          if contact.get(field) and contact.get('verification_status')), None)
        
        if not email_field:
            print(f"No verified email field found for contact {contact.get('id')}, skipping")
            continue
            
        email = contact.get(email_field)
        
        if dry_run:
            print(f"DRY RUN: Would tag {name} <{email}> as Catch-All Domain in MailerLite")
            successful_updates += 1
            continue
        
        try:
            # Add catch-all domain tag
            response = requests.post(
                f"{MAILERLITE_API_URL}/subscribers/{mailerlite_id}/tags",
                headers=MAILERLITE_HEADERS,
                json={"tags": [catch_all_tag]}
            )
            
            if response.status_code not in [200, 201, 204]:
                print(f"Error tagging {email} as Catch-All Domain: {response.text}")
                continue
            
            print(f"✓ Successfully tagged {name} <{email}> as Catch-All Domain in MailerLite")
            successful_updates += 1
            
        except Exception as e:
            print(f"Error updating MailerLite for {email}: {str(e)}")
    
    return successful_updates

def summarize_results(invalid_contacts: List[Dict[str, Any]], catch_all_contacts: List[Dict[str, Any]], 
                     invalid_processed_count: int, catch_all_processed_count: int, dry_run: bool):
    """
    Generate a summary of the verification and MailerLite update process.
    
    Args:
        invalid_contacts: List of contacts with truly invalid emails
        catch_all_contacts: List of contacts with catch-all domain emails
        invalid_processed_count: Number of invalid emails successfully processed in MailerLite
        catch_all_processed_count: Number of catch-all emails successfully processed in MailerLite
        dry_run: Whether this was a dry run
    """
    print("\n=== EMAIL VERIFICATION SUMMARY ===")
    
    # Summarize invalid emails
    if not invalid_contacts:
        print("\nNo truly invalid emails found among MailerLite contacts.")
    else:
        print(f"\nTruly invalid emails found: {len(invalid_contacts)}")
        
        # Group by status
        status_counts = {}
        for contact in invalid_contacts:
            status = contact.get('verification_status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\nBreakdown by verification status:")
        for status, count in status_counts.items():
            print(f"  - {status}: {count}")
        
        if dry_run:
            print(f"\nDRY RUN: Would have processed {len(invalid_contacts)} invalid emails in MailerLite")
        else:
            print(f"\nSuccessfully processed {invalid_processed_count} out of {len(invalid_contacts)} invalid emails in MailerLite")
        
        print(f"\nFull report of invalid emails available in: mailerlite_invalid_emails.csv")
    
    # Summarize catch-all domain emails
    if catch_all_contacts:
        print(f"\nCatch-all domain emails found: {len(catch_all_contacts)}")
        
        if dry_run:
            print(f"DRY RUN: Would have tagged {len(catch_all_contacts)} catch-all emails in MailerLite")
        else:
            print(f"Successfully tagged {catch_all_processed_count} out of {len(catch_all_contacts)} catch-all emails in MailerLite")
        
        print(f"Full report of catch-all emails available in: mailerlite_catch_all_emails.csv")

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Verify emails synced to MailerLite and update invalid ones')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing contacts')
    parser.add_argument('--max-contacts', type=int, default=None, help='Maximum number of contacts to process')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between API calls in seconds')
    parser.add_argument('--dry-run', action='store_true', help='Verify emails but don\'t update MailerLite')
    
    args = parser.parse_args()
    
    # Check required API keys
    if not ZEROBOUNCE_API_KEY:
        print("ERROR: ZEROBOUNCE_API_KEY not found in environment variables")
        print("Please add it to your .env file")
        return
    
    if not MAILERLITE_API_KEY and not args.dry_run:
        print("ERROR: MAILERLITE_API_KEY not found in environment variables")
        print("Please add it to your .env file or use --dry-run")
        return
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase configuration not found in environment variables")
        print("Please add SUPABASE_URL and SUPABASE_SERVICE_KEY to your .env file")
        return
    
    print(f"Starting email verification and MailerLite update process...")
    print(f"Batch size: {args.batch_size}")
    if args.max_contacts:
        print(f"Maximum contacts: {args.max_contacts}")
    if args.dry_run:
        print("DRY RUN MODE: Will verify emails but not update MailerLite")
    
    start_time = time.time()
    
    # Step 1: Verify emails and collect invalid ones and catch-all domains
    invalid_contacts, catch_all_contacts = verify_contacts_in_batches(
        batch_size=args.batch_size,
        max_contacts=args.max_contacts,
        delay=args.delay,
        dry_run=args.dry_run
    )
    
    # Step 2a: Process truly invalid emails in MailerLite
    invalid_processed_count = 0
    if invalid_contacts:
        invalid_processed_count = process_invalid_emails_in_mailerlite(invalid_contacts, args.dry_run)
    
    # Step 2b: Process catch-all domain emails in MailerLite
    catch_all_processed_count = 0
    if catch_all_contacts:
        catch_all_processed_count = process_catch_all_emails_in_mailerlite(catch_all_contacts, args.dry_run)
    
    elapsed_time = time.time() - start_time
    
    print(f"\nProcess completed in {elapsed_time:.2f} seconds")
    
    # Step 3: Generate summary
    summarize_results(invalid_contacts, catch_all_contacts, 
                     invalid_processed_count, catch_all_processed_count, args.dry_run)
    
    if (invalid_contacts or catch_all_contacts) and not args.dry_run:
        print("\nNext steps:")
        print("1. Review the mailerlite_invalid_emails.csv and mailerlite_catch_all_emails.csv files")
        print("2. In MailerLite, check the 'Invalid Emails' group and subscribers tagged with 'Invalid Email' or 'Catch-All Domain'")
        print("3. Consider following up with important contacts via alternative means if needed")

if __name__ == "__main__":
    main() 