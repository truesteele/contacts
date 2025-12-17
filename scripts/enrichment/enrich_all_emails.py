#!/usr/bin/env python3
"""
Comprehensive Email Enrichment Script
Uses Enrich Layer API to find both personal and work emails
Tracks attempts to avoid duplicate lookups
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from supabase import create_client, Client
import argparse

# Load environment variables
load_dotenv()

class ComprehensiveEmailEnricher:
    def __init__(self, limit: int = None, test_mode: bool = False):
        self.supabase = None
        self.api_key = os.environ.get('ENRICH_LAYER_API_KEY')
        self.limit = limit
        self.test_mode = test_mode
        self.stats = {
            'total_processed': 0,
            'personal_emails_found': 0,
            'work_emails_found': 0,
            'both_emails_found': 0,
            'no_emails_found': 0,
            'already_attempted': 0,
            'failed': 0
        }
        
        if not self.api_key:
            raise ValueError("ENRICH_LAYER_API_KEY not found in environment variables")
    
    def connect(self):
        """Connect to Supabase"""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not url or not key:
            print("✗ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
            
        self.supabase = create_client(url, key)
        print("✓ Connected to Supabase")
        return True
    
    def get_personal_email(self, linkedin_url: str) -> Optional[List[str]]:
        """Call Enrich Layer Personal Email API"""
        api_endpoint = 'https://enrichlayer.com/api/v2/contact-api/personal-email'
        
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        
        params = {
            'url': linkedin_url
        }
        
        try:
            response = requests.get(api_endpoint, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    emails = data.get('emails', data.get('personal_emails', []))
                    if emails and isinstance(emails, list):
                        return emails
                    if data.get('email'):
                        return [data['email']]
                elif isinstance(data, list) and data:
                    return data
                return None
            else:
                return None
                
        except requests.exceptions.RequestException:
            return None
    
    def get_work_email(self, linkedin_url: str) -> Optional[List[str]]:
        """Call Enrich Layer Work Email API"""
        api_endpoint = 'https://enrichlayer.com/api/v2/contact-api/work-email'
        
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        
        params = {
            'url': linkedin_url
        }
        
        try:
            response = requests.get(api_endpoint, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                # Debug: print response structure
                if self.test_mode:
                    print(f"    Work email response: {data}")
                if isinstance(data, dict):
                    emails = data.get('emails', data.get('work_emails', []))
                    if emails and isinstance(emails, list):
                        return emails
                    if data.get('email'):
                        return [data['email']]
                elif isinstance(data, list) and data:
                    return data
                return None
            else:
                if self.test_mode:
                    print(f"    Work email API error: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            if self.test_mode:
                print(f"    Work email request failed: {e}")
            return None
    
    def get_contacts_without_email(self) -> List[Dict]:
        """Get contacts that have LinkedIn URL but no email, excluding those already attempted"""
        # First, get all contacts without email
        query = self.supabase.table('contacts').select(
            'id, first_name, last_name, linkedin_url, company, position, '
            'email, work_email, personal_email, enrich_person_from_profile'
        ).not_.is_('linkedin_url', 'null').neq('linkedin_url', '')
        
        # Get contacts with no email addresses at all (all three fields must be empty)
        query = query.is_('email', 'null').is_('work_email', 'null').is_('personal_email', 'null')
        
        if self.limit:
            query = query.limit(self.limit * 2)  # Get extra to account for filtering
        
        response = query.execute()
        contacts = response.data
        
        # Filter out contacts where we've already attempted email lookup
        filtered_contacts = []
        for contact in contacts:
            # Check if we've already attempted email enrichment
            enrich_data = contact.get('enrich_person_from_profile')
            if enrich_data:
                try:
                    data = json.loads(enrich_data) if isinstance(enrich_data, str) else enrich_data
                    # Skip if we've already attempted email lookup
                    if data.get('email_lookup_attempted'):
                        self.stats['already_attempted'] += 1
                        continue
                except:
                    pass
            
            # Only process if NO email exists
            if not contact.get('email') and not contact.get('work_email') and not contact.get('personal_email'):
                filtered_contacts.append(contact)
                if self.limit and len(filtered_contacts) >= self.limit:
                    break
        
        return filtered_contacts
    
    def update_contact_emails(self, contact_id: int, contact: Dict, personal_emails: List[str] = None, work_emails: List[str] = None) -> bool:
        """Update contact with email addresses and track attempt"""
        try:
            updates = {}
            
            # Get existing enrichment data
            enrich_data = {}
            if contact.get('enrich_person_from_profile'):
                try:
                    enrich_data = json.loads(contact['enrich_person_from_profile']) if isinstance(contact['enrich_person_from_profile'], str) else contact['enrich_person_from_profile']
                except:
                    pass
            
            # Mark that we've attempted email lookup
            enrich_data['email_lookup_attempted'] = True
            enrich_data['email_lookup_date'] = datetime.now().isoformat()
            
            # Add personal email if found and not already present
            if personal_emails and personal_emails[0]:
                if not contact.get('personal_email'):
                    updates['personal_email'] = personal_emails[0]
                    enrich_data['personal_email_found'] = True
                # Set as primary email if no email exists
                if not contact.get('email'):
                    updates['email'] = personal_emails[0]
                    updates['email_type'] = 'personal'
            else:
                enrich_data['personal_email_found'] = False
            
            # Add work email if found and not already present
            if work_emails and work_emails[0]:
                if not contact.get('work_email'):
                    updates['work_email'] = work_emails[0]
                    enrich_data['work_email_found'] = True
                # Set as primary email if no email exists and no personal email was found
                if not contact.get('email') and not personal_emails:
                    updates['email'] = work_emails[0]
                    updates['email_type'] = 'work'
            else:
                enrich_data['work_email_found'] = False
            
            # Always update enrichment data to track attempt
            updates['enrich_person_from_profile'] = json.dumps(enrich_data)
            
            response = self.supabase.table('contacts').update(updates).eq('id', contact_id).execute()
            return True
        except Exception as e:
            print(f"  ✗ Failed to update contact {contact_id}: {e}")
            return False
    
    def run(self):
        """Main enrichment process"""
        if not self.connect():
            return False
        
        print("\n🔍 Fetching contacts without email addresses...")
        contacts = self.get_contacts_without_email()
        
        if not contacts:
            print("No contacts need email enrichment (or all have been attempted)")
            print(f"Skipped {self.stats['already_attempted']} contacts with previous lookup attempts")
            return True
        
        print(f"Found {len(contacts)} contacts without email addresses")
        print(f"Skipped {self.stats['already_attempted']} contacts with previous lookup attempts")
        
        if self.test_mode:
            print("⚠️ TEST MODE - Processing first 5 contacts only")
            contacts = contacts[:5]
        
        print("\n🚀 Starting comprehensive email enrichment...")
        print("=" * 60)
        
        for i, contact in enumerate(contacts, 1):
            self.stats['total_processed'] += 1
            
            print(f"\n[{i}/{len(contacts)}] {contact['first_name']} {contact.get('last_name', '')}")
            if contact.get('company'):
                print(f"  Company: {contact['company']}")
            print(f"  LinkedIn: {contact['linkedin_url']}")
            
            # Try to get personal email (this endpoint returns actual email addresses)
            personal_emails = self.get_personal_email(contact['linkedin_url'])
            if personal_emails:
                print(f"  📧 Email found: {personal_emails[0]}")
                self.stats['personal_emails_found'] += 1
            
            # Note: Work email endpoint doesn't exist in the API
            # The profile endpoint returns work_emails but they're usually empty
            # So we'll just use the personal email endpoint
            work_emails = None
            
            # Track results
            if personal_emails and work_emails:
                self.stats['both_emails_found'] += 1
            elif not personal_emails and not work_emails:
                self.stats['no_emails_found'] += 1
                print("  ⚠ No emails found")
            
            # Update database (always update to track attempt)
            if self.update_contact_emails(contact['id'], contact, personal_emails, work_emails):
                if personal_emails or work_emails:
                    print(f"  ✓ Updated contact")
                else:
                    print(f"  ✓ Marked as attempted")
            else:
                self.stats['failed'] += 1
            
            # Rate limiting
            if not self.test_mode:
                time.sleep(0.5)  # ~2 requests per second per endpoint
            
            # Progress update every 25 contacts
            if i % 25 == 0 and i < len(contacts):
                print(f"\n  → Progress: {i}/{len(contacts)} processed...")
                print(f"     Personal emails: {self.stats['personal_emails_found']}")
                print(f"     Work emails: {self.stats['work_emails_found']}")
        
        self.print_summary()
        return True
    
    def print_summary(self):
        """Print enrichment summary"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE EMAIL ENRICHMENT SUMMARY")
        print("=" * 60)
        print(f"Total processed:        {self.stats['total_processed']:,}")
        print(f"Personal emails found:  {self.stats['personal_emails_found']:,}")
        print(f"Work emails found:      {self.stats['work_emails_found']:,}")
        print(f"Both types found:       {self.stats['both_emails_found']:,}")
        print(f"No emails found:        {self.stats['no_emails_found']:,}")
        print(f"Previously attempted:   {self.stats['already_attempted']:,}")
        print(f"Failed to update:       {self.stats['failed']:,}")
        print("=" * 60)
        
        # Estimate credits (2 per contact - one for personal, one for work)
        credits_used = self.stats['total_processed'] * 2
        print(f"\n💳 Estimated credits used: {credits_used} (2 lookups per contact)")
        
        # Success rate
        if self.stats['total_processed'] > 0:
            success_rate = ((self.stats['personal_emails_found'] + self.stats['work_emails_found'] - self.stats['both_emails_found']) / self.stats['total_processed']) * 100
            print(f"📈 Overall success rate: {success_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description='Comprehensive email enrichment for contacts'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Limit number of contacts to enrich'
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Test mode - process only 5 contacts'
    )
    
    args = parser.parse_args()
    
    try:
        enricher = ComprehensiveEmailEnricher(limit=args.limit, test_mode=args.test)
        success = enricher.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()