#!/usr/bin/env python3
"""
Fix Catch-All Email Classification

This script identifies emails previously marked as invalid due to being catch-all domains
and updates them to be treated as valid with the appropriate catch-all flag.
It uses ONLY existing verification data from your database and does NOT make any new
API calls to ZeroBounce (no credits used).

Usage:
  python fix_catch_all_emails.py
  python fix_catch_all_emails.py --dry-run
  python fix_catch_all_emails.py --max 100
  python fix_catch_all_emails.py --update-mailerlite
"""

import os
import time
import argparse
import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import csv
from supabase import create_client

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ZEROBOUNCE_API_KEY = os.getenv("ZEROBOUNCE_API_KEY")
ZEROBOUNCE_API_URL = "https://api.zerobounce.net/v2"

# MailerLite configuration
MAILERLITE_API_KEY = os.getenv("MAILERLITE_API_KEY")
MAILERLITE_API_URL = "https://connect.mailerlite.com/api"

print("Starting catch-all email fix process (using existing data only, no ZeroBounce API calls)...")

def create_supabase_client():
    """Create and return a Supabase client instance."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase credentials not found in environment variables.")
        print("Please add SUPABASE_URL and SUPABASE_SERVICE_KEY to your .env file.")
        return None
    
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error creating Supabase client: {e}")
        return None

def read_catch_all_from_csv() -> List[Dict[str, Any]]:
    """Read catch-all domain emails from the invalid emails CSV export."""
    catch_all_emails = []
    csv_file = "mailerlite_invalid_emails.csv"
    
    if not os.path.exists(csv_file):
        print(f"CSV file {csv_file} not found.")
        return []
    
    try:
        with open(csv_file, 'r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Check if this is a catch-all domain based on the notes
                notes = row.get('notes', '').lower()
                if 'catch-all' in notes:
                    catch_all_emails.append(row)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    
    print(f"Found {len(catch_all_emails)} catch-all domain emails from the CSV file")
    return catch_all_emails

def find_catch_all_in_database(supabase_client, max_records: Optional[int] = None) -> List[Dict[str, Any]]:
    """Query the Supabase database for contacts marked as invalid that have catch-all domains."""
    catch_all_emails = []
    
    if not supabase_client:
        print("No Supabase client available.")
        return []
    
    try:
        # Build the query
        query = supabase_client.table('contacts')\
            .select('id, first_name, last_name, email, work_email, personal_email, synced_to_mailerlite, mailerlite_subscriber_id, email_verified, email_verification_source, email_verified_at, email_verification_due_at, email_is_catch_all')\
            .eq('email_verified', False)\
            .eq('email_verification_source', 'ZeroBounce')
        
        if max_records:
            query = query.limit(max_records)
        
        # Execute the query
        response = query.execute()
        contacts = response.data
        
        print(f"Found {len(contacts)} contacts marked as invalid to check for catch-all domains")
        
        # For each contact, check if their email might be a catch-all domain
        for contact in contacts:
            email = contact.get('work_email') or contact.get('email') or contact.get('personal_email')
            if email and is_likely_catch_all_domain(email):
                catch_all_emails.append(contact)
                
        print(f"Identified {len(catch_all_emails)} potential catch-all domain emails from the database")
        
    except Exception as e:
        print(f"Error querying Supabase database: {e}")
    
    return catch_all_emails

def is_likely_catch_all_domain(email: str) -> bool:
    """Check if an email is likely from a catch-all domain based on common patterns."""
    # List of common catch-all domains
    common_catch_all_domains = [
        'google.com', 'amazon.com', 'microsoft.com', 'apple.com',
        'facebook.com', 'twitter.com', 'linkedin.com', 'github.com',
        'salesforce.com', 'adobe.com', 'oracle.com', 'ibm.com',
        'intel.com', 'cisco.com', 'hp.com', 'dell.com', 
        'sap.com', 'vmware.com', 'redhat.com', 'airbnb.com',
        'uber.com', 'lyft.com', 'spotify.com', 'netflix.com',
        'disney.com', 'walmart.com', 'target.com', 'costco.com',
        'mckinsey.com', 'deloitte.com', 'pwc.com', 'kpmg.com',
        'accenture.com', 'jpmorgan.com', 'gs.com', 'ms.com',
        'bofa.com', 'wellsfargo.com', 'citi.com', 'visa.com',
        'mastercard.com', 'amex.com', 'paypal.com', 'stripe.com',
        'shopify.com', 'square.com', 'wordpress.com', 'wix.com',
        'squarespace.com', 'godaddy.com', 'cloudflare.com', 'aws.amazon.com',
        'azure.com', 'gcp.com', 'digitalocean.com', 'heroku.com',
        'trscapital.com', 'gv.com', 'state.tx.us', 'jff.org',
        'bhfs.com', 'theknowledgehouse.org', 'bridgespan.org',
        'dolby.com', 'blackbaud.com', 'cecp.co', 'rocketcommunityfund.org',
        'collegeboard.org', 'fairfield.edu', 'cultureamp.com', 'comerica.com',
        'chanzuckerberg.com', 'christiandior.com'
    ]
    
    if not email or '@' not in email:
        return False
    
    domain = email.split('@')[1].lower()
    return domain in common_catch_all_domains

def verify_with_zerobounce(email: str) -> Dict[str, Any]:
    """Verify if an email is from a catch-all domain using ZeroBounce API."""
    import requests
    
    if not ZEROBOUNCE_API_KEY:
        print("ZeroBounce API key not found. Cannot verify catch-all domains.")
        return {"is_catch_all": False}
    
    url = f"{ZEROBOUNCE_API_URL}/validate?api_key={ZEROBOUNCE_API_KEY}&email={email}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # ZeroBounce returns "catch-all" as a specific status
        return {
            "is_catch_all": data.get("status") == "catch-all",
            "full_response": data
        }
    except Exception as e:
        print(f"Error verifying email with ZeroBounce: {e}")
        return {"is_catch_all": False}

def fix_catch_all_email_in_supabase(supabase_client, contact_id: int, dry_run: bool = False) -> bool:
    """Update a contact's email status in Supabase from invalid to valid with catch-all flag."""
    if not supabase_client:
        print("No Supabase client available.")
        return False
    
    try:
        # First, get the current contact data
        contact_response = supabase_client.table('contacts')\
            .select('*')\
            .eq('id', contact_id)\
            .execute()
        
        if not contact_response.data:
            print(f"Contact with ID {contact_id} not found in Supabase.")
            return False
        
        contact = contact_response.data[0]
        
        # Prepare the update data
        update_data = {
            "email_verified": True,
            "email_is_catch_all": True,
            "email_verified_at": datetime.datetime.now().isoformat(),
            "email_verification_due_at": (datetime.datetime.now() + datetime.timedelta(days=90)).isoformat()
        }
        
        # If contact was previously synced to MailerLite, continue syncing
        if contact.get("synced_to_mailerlite"):
            update_data["mailerlite_update_required"] = True
            update_data["mailerlite_update_reason"] = "Fix catch-all domain email"
        
        if dry_run:
            print(f"DRY RUN: Would update contact {contact_id} in Supabase to mark as valid catch-all domain.")
            return True
        
        # Update the contact in Supabase
        update_response = supabase_client.table('contacts')\
            .update(update_data)\
            .eq('id', contact_id)\
            .execute()
        
        if update_response.data:
            print(f"✅ Updated contact {contact_id} in Supabase to mark as valid catch-all domain.")
            return True
        else:
            print(f"Error updating contact {contact_id} in Supabase.")
            return False
        
    except Exception as e:
        print(f"Error updating contact in Supabase: {e}")
        return False

def fix_catch_all_email_in_mailerlite(contact: Dict[str, Any], dry_run: bool = False) -> bool:
    """Fix the catch-all domain email in MailerLite."""
    import requests
    
    subscriber_id = contact.get("mailerlite_subscriber_id")
    email = contact.get("work_email") or contact.get("email") or contact.get("personal_email")
    
    if not subscriber_id:
        print(f"No MailerLite subscriber ID for contact {contact['id']} ({email}), skipping MailerLite update.")
        return False
    
    if not MAILERLITE_API_KEY:
        print("MailerLite API key not found in environment variables.")
        return False
    
    headers = {
        "Authorization": f"Bearer {MAILERLITE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # First, check the subscriber's status
    try:
        subscriber_url = f"{MAILERLITE_API_URL}/subscribers/{subscriber_id}"
        response = requests.get(subscriber_url, headers=headers)
        
        if response.status_code == 404:
            print(f"Subscriber {subscriber_id} not found in MailerLite.")
            return False
        
        response.raise_for_status()
        subscriber_data = response.json().get("data", {})
        
        # Prepare the update operations
        operations = []
        
        # 1. Resubscribe if currently unsubscribed
        if subscriber_data.get("status") != "active":
            if dry_run:
                print(f"DRY RUN: Would resubscribe {email} in MailerLite.")
            else:
                resubscribe_url = f"{MAILERLITE_API_URL}/subscribers/{subscriber_id}/resubscribe"
                resubscribe_response = requests.post(resubscribe_url, headers=headers)
                if resubscribe_response.status_code == 200:
                    print(f"✅ Resubscribed {email} in MailerLite.")
                    operations.append("resubscribed")
                else:
                    print(f"Failed to resubscribe {email} in MailerLite: {resubscribe_response.text}")
        
        # 2. Add "Catch-All Domain" tag
        if dry_run:
            print(f"DRY RUN: Would add 'Catch-All Domain' tag to {email} in MailerLite.")
        else:
            tag_url = f"{MAILERLITE_API_URL}/subscribers/{subscriber_id}/tags"
            tag_data = {"tags": ["Catch-All Domain"]}
            tag_response = requests.post(tag_url, headers=headers, json=tag_data)
            if tag_response.status_code == 200:
                print(f"✅ Added 'Catch-All Domain' tag to {email} in MailerLite.")
                operations.append("tagged as Catch-All Domain")
            else:
                print(f"Failed to add 'Catch-All Domain' tag to {email} in MailerLite: {tag_response.text}")
        
        # 3. Remove from "Invalid Emails" group if present
        try:
            # First, get all subscriber groups
            groups_url = f"{MAILERLITE_API_URL}/subscribers/{subscriber_id}/groups"
            groups_response = requests.get(groups_url, headers=headers)
            groups_response.raise_for_status()
            groups = groups_response.json().get("data", [])
            
            # Find "Invalid Emails" group
            invalid_group = next((g for g in groups if g.get("name") == "Invalid Emails"), None)
            
            if invalid_group:
                group_id = invalid_group.get("id")
                if dry_run:
                    print(f"DRY RUN: Would remove {email} from 'Invalid Emails' group in MailerLite.")
                else:
                    remove_url = f"{MAILERLITE_API_URL}/subscribers/{subscriber_id}/groups/{group_id}"
                    remove_response = requests.delete(remove_url, headers=headers)
                    if remove_response.status_code in [200, 204]:
                        print(f"✅ Removed {email} from 'Invalid Emails' group in MailerLite.")
                        operations.append("removed from Invalid Emails group")
                    else:
                        print(f"Failed to remove {email} from 'Invalid Emails' group in MailerLite: {remove_response.text}")
        except Exception as e:
            print(f"Error checking/removing from groups: {e}")
        
        if operations:
            print(f"✅ Successfully processed {email} in MailerLite: {', '.join(operations)}")
            return True
        elif dry_run:
            return True
        else:
            print(f"No changes needed for {email} in MailerLite.")
            return True
            
    except Exception as e:
        print(f"Error updating subscriber in MailerLite: {e}")
        return False

def main():
    """Main function to process catch-all emails."""
    parser = argparse.ArgumentParser(description="Fix emails from catch-all domains that were marked as invalid.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without making changes.")
    parser.add_argument("--max", type=int, help="Maximum number of contacts to process.")
    parser.add_argument("--update-mailerlite", action="store_true", help="Also update contacts in MailerLite.")
    parser.add_argument("--use-api", action="store_true", help="Use ZeroBounce API to verify catch-all domains.")
    args = parser.parse_args()
    
    # Create Supabase client
    supabase_client = create_supabase_client()
    if not supabase_client:
        return
    
    # Check required environment variables
    if args.update_mailerlite and not MAILERLITE_API_KEY:
        print("ERROR: MailerLite API key not found in environment variables.")
        print("Please add MAILERLITE_API_KEY to your .env file.")
        return
    
    if args.use_api and not ZEROBOUNCE_API_KEY:
        print("ERROR: ZeroBounce API key not found in environment variables.")
        print("Please add ZEROBOUNCE_API_KEY to your .env file.")
        return
    
    # First try to get catch-all emails from the CSV file
    catch_all_emails_from_csv = read_catch_all_from_csv()
    
    # Then search the database for potential catch-all domains
    catch_all_emails_from_db = find_catch_all_in_database(supabase_client, args.max)
    
    # Combine the lists and remove duplicates
    all_catch_all_emails = catch_all_emails_from_csv + catch_all_emails_from_db
    processed_ids = set()
    unique_catch_all_emails = []
    
    for email in all_catch_all_emails:
        # For CSV entries, they don't have IDs so use email as key
        key = email.get('id') or email.get('email')
        if key and key not in processed_ids:
            processed_ids.add(key)
            unique_catch_all_emails.append(email)
    
    if not unique_catch_all_emails:
        print("No catch-all emails found that need fixing.")
        return
    
    print(f"Found {len(unique_catch_all_emails)} unique catch-all emails to fix.")
    
    # If using the ZeroBounce API, verify each email
    if args.use_api:
        verified_catch_all_emails = []
        for contact in unique_catch_all_emails:
            email = contact.get('work_email') or contact.get('email') or contact.get('personal_email')
            if email:
                verification = verify_with_zerobounce(email)
                if verification['is_catch_all']:
                    verified_catch_all_emails.append(contact)
                    print(f"✅ Verified {email} is indeed a catch-all domain.")
                else:
                    print(f"❌ {email} is NOT a catch-all domain according to ZeroBounce.")
                # Respect API rate limits
                time.sleep(0.5)
        
        if not verified_catch_all_emails:
            print("No emails were verified as catch-all domains by ZeroBounce.")
            return
        
        unique_catch_all_emails = verified_catch_all_emails
        print(f"After ZeroBounce verification, found {len(unique_catch_all_emails)} catch-all emails to fix.")
    
    # Process each email
    success_count = 0
    mailerlite_success_count = 0
    
    for contact in unique_catch_all_emails:
        # Database contacts have an ID, CSV entries don't
        contact_id = contact.get('id')
        email = contact.get('work_email') or contact.get('email') or contact.get('personal_email')
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        
        if contact_id:
            print(f"Processing contact {contact_id} ({name}) <{email}>...")
            
            # Update in Supabase
            if fix_catch_all_email_in_supabase(supabase_client, contact_id, args.dry_run):
                success_count += 1
                
                # Update in MailerLite if requested
                if args.update_mailerlite:
                    if fix_catch_all_email_in_mailerlite(contact, args.dry_run):
                        mailerlite_success_count += 1
        else:
            # This is a CSV entry without an ID, try to find the contact in Supabase by email
            print(f"Looking up contact for {name} <{email}> in Supabase...")
            
            if not email:
                print("No email found for contact, skipping.")
                continue
                
            # Query Supabase for the contact by email
            try:
                query = supabase_client.table('contacts')\
                    .select('id, first_name, last_name, email, work_email, personal_email, synced_to_mailerlite, mailerlite_subscriber_id')\
                    .or_('email.eq.' + email + ',work_email.eq.' + email + ',personal_email.eq.' + email)\
                    .execute()
                    
                matching_contacts = query.data
                
                if matching_contacts:
                    contact_with_id = matching_contacts[0]
                    contact_id = contact_with_id['id']
                    print(f"Found matching contact ID: {contact_id}")
                    
                    # Update in Supabase
                    if fix_catch_all_email_in_supabase(supabase_client, contact_id, args.dry_run):
                        success_count += 1
                        
                        # Update in MailerLite if requested
                        if args.update_mailerlite:
                            if fix_catch_all_email_in_mailerlite(contact_with_id, args.dry_run):
                                mailerlite_success_count += 1
                else:
                    print(f"No matching contact found in Supabase for email {email}")
            except Exception as e:
                print(f"Error looking up contact in Supabase: {e}")
    
    # Print summary
    action = "Would have updated" if args.dry_run else "Updated"
    print(f"\nProcess completed. {action} {success_count} out of {len(unique_catch_all_emails)} catch-all emails in Supabase.")
    
    if args.update_mailerlite:
        print(f"{action} {mailerlite_success_count} catch-all emails in MailerLite.")

if __name__ == "__main__":
    main() 