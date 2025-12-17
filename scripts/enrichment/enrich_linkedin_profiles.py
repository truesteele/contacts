#!/usr/bin/env python3
"""
LinkedIn Profile Enrichment Script
Uses Enrich Layer API to enrich LinkedIn profiles in the Supabase database
Maps enriched data to existing columns and adds new enrichment data
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import argparse

# Load environment variables
load_dotenv()

class LinkedInEnricher:
    def __init__(self, limit: int = None, test_mode: bool = False):
        self.supabase = None
        self.api_key = os.environ.get('ENRICH_LAYER_API_KEY')
        self.limit = limit
        self.test_mode = test_mode
        self.stats = {
            'total_processed': 0,
            'enriched': 0,
            'failed': 0,
            'skipped': 0,
            'emails_found': 0,
            'phones_found': 0
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
    
    def enrich_profile(self, linkedin_url: str) -> Optional[Dict]:
        """Call Enrich Layer API to enrich a single profile"""
        api_endpoint = 'https://enrichlayer.com/api/v2/profile'
        
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        
        params = {
            'url': linkedin_url,
            'use_cache': 'if-present'  # Use cached data if available (1 credit total)
            # Note: 'if-recent' costs 2 credits, 'live_fetch: force' costs 10 credits
        }
        
        try:
            response = requests.get(api_endpoint, headers=headers, params=params, timeout=60)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"  ⚠ Profile not found: {linkedin_url}")
                return None
            else:
                print(f"  ✗ API error {response.status_code}: {response.text[:100]}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Request failed: {e}")
            return None
    
    def map_enriched_data(self, contact: Dict, enriched: Dict) -> Dict:
        """Map enriched data to database fields"""
        updates = {}
        
        # Basic profile information
        if enriched.get('headline'):
            updates['headline'] = enriched['headline']
        
        if enriched.get('summary'):
            updates['summary'] = enriched['summary']
        
        if enriched.get('country_full_name'):
            updates['country'] = enriched['country_full_name']
        
        if enriched.get('location_str'):
            updates['location_name'] = enriched['location_str']
        
        # Profile metrics
        if enriched.get('follower_count'):
            updates['num_followers'] = str(enriched['follower_count'])
        
        if enriched.get('connections'):
            updates['connections'] = str(enriched['connections'])
        
        # Profile URL and picture
        if enriched.get('profile_pic_url'):
            updates['linkedin_profile'] = enriched['profile_pic_url']
        
        # Organization from headline/occupation
        if enriched.get('occupation'):
            # Extract company from occupation (usually "Title at Company")
            parts = enriched['occupation'].split(' at ')
            if len(parts) > 1:
                updates['org'] = parts[-1]
        
        # Current experience details
        experiences = enriched.get('experiences', [])
        if experiences:
            current_exp = experiences[0]  # Most recent experience
            
            # Update company if different and more recent
            if current_exp.get('company'):
                company_name = current_exp['company']
                if not contact.get('company') or contact['company'] != company_name:
                    updates['company'] = company_name
                    if contact.get('company'):
                        updates['previous_company'] = contact['company']
                        updates['company_updated_at'] = datetime.now().isoformat()
            
            # Update position if different and more recent
            if current_exp.get('title'):
                position = current_exp['title']
                if not contact.get('position') or contact['position'] != position:
                    updates['position'] = position
                    if contact.get('position'):
                        updates['previous_position'] = contact['position']
                        updates['position_updated_at'] = datetime.now().isoformat()
            
            # Store experience summary
            if current_exp.get('description'):
                updates['summary_experience'] = current_exp['description']
            
            # Store company domain if available
            if current_exp.get('company_linkedin_profile_url'):
                # Extract company identifier from LinkedIn URL
                company_url = current_exp['company_linkedin_profile_url']
                if '/company/' in company_url:
                    company_id = company_url.split('/company/')[-1].rstrip('/')
                    updates['company_domain_experience'] = company_id
            
            # Store experience dates (commented until columns are added)
            # if current_exp.get('starts_at'):
            #     start_date = current_exp['starts_at']
            #     if start_date:
            #         date_str = f"{start_date.get('year', '')}-{start_date.get('month', ''):02d}-{start_date.get('day', ''):02d}"
            #         updates['start_date_experience'] = date_str
            
            # if current_exp.get('ends_at'):
            #     end_date = current_exp['ends_at']
            #     if end_date:
            #         date_str = f"{end_date.get('year', '')}-{end_date.get('month', ''):02d}-{end_date.get('day', ''):02d}"
            #         updates['end_date_experience'] = date_str
        
        # Education details
        education = enriched.get('education', [])
        if education:
            latest_edu = education[0]
            
            if latest_edu.get('school'):
                updates['school_name_education'] = latest_edu['school']
            
            if latest_edu.get('degree_name'):
                updates['degree_education'] = latest_edu['degree_name']
            
            if latest_edu.get('field_of_study'):
                updates['field_of_study_education'] = latest_edu['field_of_study']
            
            if latest_edu.get('activities_and_societies'):
                updates['activities_education'] = latest_edu['activities_and_societies']
            
            # Education dates (commented until columns are added)
            # if latest_edu.get('starts_at'):
            #     start_date = latest_edu['starts_at']
            #     if start_date:
            #         date_str = f"{start_date.get('year', '')}-{start_date.get('month', ''):02d}-{start_date.get('day', ''):02d}"
            #         updates['start_date_education'] = date_str
            
            # if latest_edu.get('ends_at'):
            #     end_date = latest_edu['ends_at']
            #     if end_date:
            #         date_str = f"{end_date.get('year', '')}-{end_date.get('month', ''):02d}-{end_date.get('day', ''):02d}"
            #         updates['end_date_education'] = date_str
        
        # Projects
        projects = enriched.get('accomplishment_projects', [])
        if projects:
            project_titles = [p.get('title', '') for p in projects if p.get('title')]
            project_summaries = [p.get('description', '') for p in projects if p.get('description')]
            
            if project_titles:
                updates['title_projects'] = ' | '.join(project_titles)
            if project_summaries:
                updates['summary_projects'] = ' | '.join(project_summaries)
        
        # Publications
        publications = enriched.get('accomplishment_publications', [])
        if publications:
            pub_titles = [p.get('name', '') for p in publications if p.get('name')]
            pub_publishers = [p.get('publisher', '') for p in publications if p.get('publisher')]
            pub_urls = [p.get('url', '') for p in publications if p.get('url')]
            
            if pub_titles:
                updates['title_publications'] = ' | '.join(pub_titles)
            if pub_publishers:
                updates['publisher_publications'] = ' | '.join(pub_publishers)
            if pub_urls:
                updates['url_publications'] = ' | '.join(pub_urls)
        
        # Awards
        awards = enriched.get('accomplishment_honors_awards', [])
        if awards:
            award_titles = [a.get('title', '') for a in awards if a.get('title')]
            award_issuers = [a.get('issuer', '') for a in awards if a.get('issuer')]
            
            if award_titles:
                updates['title_awards'] = ' | '.join(award_titles)
            if award_issuers:
                updates['company_name_awards'] = ' | '.join(award_issuers)
        
        # Volunteer work
        volunteer = enriched.get('volunteer_work', [])
        if volunteer:
            vol_titles = [v.get('title', '') for v in volunteer if v.get('title')]
            vol_companies = [v.get('company', '') for v in volunteer if v.get('company')]
            
            if vol_titles:
                updates['role_volunteering'] = ' | '.join(vol_titles)
            if vol_companies:
                updates['company_name_volunteering'] = ' | '.join(vol_companies)
        
        # Contact information (if available)
        personal_emails = enriched.get('personal_emails', [])
        if personal_emails:
            # Store first personal email if no email exists
            if not contact.get('email') and personal_emails:
                updates['email'] = personal_emails[0]
                updates['email_type'] = 'personal'
                updates['personal_email'] = personal_emails[0]
                self.stats['emails_found'] += 1
        
        personal_numbers = enriched.get('personal_numbers', [])
        if personal_numbers:
            # Store first phone number if available
            if personal_numbers:
                updates['normalized_phone_number'] = personal_numbers[0]
                self.stats['phones_found'] += 1
        
        # Add enrichment metadata
        updates['enrich_person_from_profile'] = json.dumps({
            'enriched_at': datetime.now().isoformat(),
            'source': 'enrich_layer',
            'profile_completeness': len(updates)
        })
        
        return updates
    
    def get_contacts_to_enrich(self) -> List[Dict]:
        """Get contacts that need enrichment"""
        query = self.supabase.table('contacts').select(
            'id, first_name, last_name, linkedin_url, company, position, email, '
            'headline, summary, enrich_person_from_profile'
        ).not_.is_('linkedin_url', 'null').neq('linkedin_url', '')
        
        # Prioritize contacts without enrichment data
        query = query.or_('enrich_person_from_profile.is.null,headline.is.null,summary.is.null')
        
        if self.limit:
            query = query.limit(self.limit)
        
        response = query.execute()
        return response.data
    
    def update_contact(self, contact_id: int, updates: Dict) -> bool:
        """Update contact in database"""
        try:
            response = self.supabase.table('contacts').update(updates).eq('id', contact_id).execute()
            return True
        except Exception as e:
            print(f"  ✗ Failed to update contact {contact_id}: {e}")
            return False
    
    def run(self):
        """Main enrichment process"""
        if not self.connect():
            return False
        
        print("\n🔍 Fetching contacts to enrich...")
        contacts = self.get_contacts_to_enrich()
        
        if not contacts:
            print("No contacts need enrichment")
            return True
        
        print(f"Found {len(contacts)} contacts to enrich")
        
        if self.test_mode:
            print("⚠️ TEST MODE - Processing first contact only")
            contacts = contacts[:1]
        
        print("\n🚀 Starting enrichment process...")
        print("=" * 60)
        
        for i, contact in enumerate(contacts, 1):
            self.stats['total_processed'] += 1
            
            print(f"\n[{i}/{len(contacts)}] {contact['first_name']} {contact['last_name']}")
            print(f"  LinkedIn: {contact['linkedin_url']}")
            
            # Enrich profile
            enriched_data = self.enrich_profile(contact['linkedin_url'])
            
            if not enriched_data:
                self.stats['failed'] += 1
                continue
            
            # Map to database fields
            updates = self.map_enriched_data(contact, enriched_data)
            
            if not updates:
                print("  ⚠ No new data to update")
                self.stats['skipped'] += 1
                continue
            
            # Update database
            if self.update_contact(contact['id'], updates):
                self.stats['enriched'] += 1
                print(f"  ✓ Updated {len(updates)} fields")
                
                # Show key updates
                if 'email' in updates:
                    print(f"    📧 Email: {updates['email']}")
                if 'headline' in updates:
                    print(f"    💼 Headline: {updates['headline'][:60]}...")
                if 'company' in updates:
                    print(f"    🏢 Company: {updates['company']}")
                if 'position' in updates:
                    print(f"    👔 Position: {updates['position']}")
            else:
                self.stats['failed'] += 1
            
            # Rate limiting - 300 requests per minute max
            if not self.test_mode:
                time.sleep(0.2)  # ~5 requests per second
        
        self.print_summary()
        return True
    
    def print_summary(self):
        """Print enrichment summary"""
        print("\n" + "=" * 60)
        print("📊 ENRICHMENT SUMMARY")
        print("=" * 60)
        print(f"Total processed:    {self.stats['total_processed']:,}")
        print(f"Successfully enriched: {self.stats['enriched']:,}")
        print(f"Failed:            {self.stats['failed']:,}")
        print(f"Skipped:           {self.stats['skipped']:,}")
        print(f"Emails found:      {self.stats['emails_found']:,}")
        print(f"Phone numbers found: {self.stats['phones_found']:,}")
        print("=" * 60)
        
        credits_used = self.stats['enriched'] + self.stats['failed']
        print(f"\n💳 Credits used: {credits_used} (1 credit per profile)")


def main():
    parser = argparse.ArgumentParser(
        description='Enrich LinkedIn profiles using Enrich Layer API'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Limit number of profiles to enrich'
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Test mode - process only 1 profile'
    )
    
    args = parser.parse_args()
    
    try:
        enricher = LinkedInEnricher(limit=args.limit, test_mode=args.test)
        success = enricher.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()