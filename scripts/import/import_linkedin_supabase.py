#!/usr/bin/env python3
"""
LinkedIn Contacts Import Script for Supabase
Imports contacts from LinkedIn CSV export to Supabase database
Tracks changes to company and position fields
"""

import csv
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import argparse

# Load environment variables
load_dotenv()

class LinkedInSupabaseImporter:
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.supabase: Client = None
        self.stats = {
            'total': 0,
            'new': 0,
            'updated_company': 0,
            'updated_position': 0,
            'updated_both': 0,
            'unchanged': 0,
            'errors': 0,
            'skipped': 0
        }
        
    def connect(self):
        """Establish Supabase connection"""
        try:
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_KEY")
            
            if not url or not key:
                print("✗ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env file")
                return False
                
            self.supabase = create_client(url, key)
            print("✓ Connected to Supabase")
            return True
        except Exception as e:
            print(f"✗ Supabase connection failed: {e}")
            return False
    
    def normalize_linkedin_url(self, url: str) -> str:
        """Normalize LinkedIn URL to consistent format"""
        if not url:
            return ''
        
        # Remove trailing slashes
        url = url.rstrip('/')
        
        # Ensure https
        if url.startswith('http://'):
            url = url.replace('http://', 'https://', 1)
        elif not url.startswith('https://'):
            url = 'https://' + url
            
        return url
    
    def check_existing_contact(self, linkedin_url: str) -> Optional[Dict]:
        """Check if contact exists and return current data"""
        try:
            response = self.supabase.table('contacts').select(
                'id, first_name, last_name, company, position, email, linkedin_url'
            ).eq('linkedin_url', linkedin_url).limit(1).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            print(f"  ✗ Error checking existing contact: {e}")
            return None
    
    def insert_new_contact(self, data: Dict) -> bool:
        """Insert a new contact record"""
        try:
            # Set last_import_date
            data['last_import_date'] = datetime.now().isoformat()
            
            response = self.supabase.table('contacts').insert(data).execute()
            return True
        except Exception as e:
            print(f"  ✗ Insert failed for {data['first_name']} {data['last_name']}: {e}")
            return False
    
    def update_existing_contact(self, contact_id: int, updates: Dict, 
                              old_company: str, old_position: str) -> bool:
        """Update existing contact with change tracking"""
        update_data = {}
        
        # Track company changes
        if 'company' in updates and updates['company'] != old_company:
            update_data['company'] = updates['company']
            update_data['previous_company'] = old_company
            update_data['company_updated_at'] = datetime.now().isoformat()
        
        # Track position changes
        if 'position' in updates and updates['position'] != old_position:
            update_data['position'] = updates['position']
            update_data['previous_position'] = old_position
            update_data['position_updated_at'] = datetime.now().isoformat()
        
        # Update email if provided and not already set
        if 'email' in updates and updates['email']:
            # We'll only update if email is not already set
            # This is handled by checking in process_row
            update_data['email'] = updates['email']
        
        # Always update last import date
        update_data['last_import_date'] = datetime.now().isoformat()
        
        try:
            response = self.supabase.table('contacts').update(update_data).eq('id', contact_id).execute()
            return True
        except Exception as e:
            print(f"  ✗ Update failed for ID {contact_id}: {e}")
            return False
    
    def process_row(self, row: Dict) -> None:
        """Process a single CSV row"""
        self.stats['total'] += 1
        
        # Extract and clean data
        first_name = row.get('First Name', '').strip()
        last_name = row.get('Last Name', '').strip()
        linkedin_url = self.normalize_linkedin_url(row.get('URL', '').strip())
        email = row.get('Email Address', '').strip() or None
        company = row.get('Company', '').strip() or None
        position = row.get('Position', '').strip() or None
        connected_on = row.get('Connected On', '').strip() or None
        
        # Skip if no LinkedIn URL
        if not linkedin_url:
            print(f"  ⚠ Row {self.stats['total']}: Skipping - no LinkedIn URL")
            self.stats['skipped'] += 1
            return
        
        # Check if contact exists
        existing = self.check_existing_contact(linkedin_url)
        
        if existing:
            # Check for changes
            company_changed = (company and company != existing.get('company'))
            position_changed = (position and position != existing.get('position'))
            
            if company_changed or position_changed:
                updates = {}
                if company_changed:
                    updates['company'] = company
                if position_changed:
                    updates['position'] = position
                if email and not existing.get('email'):
                    updates['email'] = email
                
                if self.update_existing_contact(
                    existing['id'], 
                    updates,
                    existing.get('company'),
                    existing.get('position')
                ):
                    if company_changed and position_changed:
                        self.stats['updated_both'] += 1
                        print(f"  ✓ Updated both: {first_name} {last_name}")
                    elif company_changed:
                        self.stats['updated_company'] += 1
                        print(f"  ✓ Updated company: {first_name} {last_name} → {company}")
                    else:
                        self.stats['updated_position'] += 1
                        print(f"  ✓ Updated position: {first_name} {last_name} → {position}")
                else:
                    self.stats['errors'] += 1
            else:
                self.stats['unchanged'] += 1
                # Still update last_import_date
                try:
                    self.supabase.table('contacts').update({
                        'last_import_date': datetime.now().isoformat()
                    }).eq('id', existing['id']).execute()
                except:
                    pass  # Silent fail for unchanged records
        else:
            # Insert new contact
            data = {
                'first_name': first_name,
                'last_name': last_name,
                'linkedin_url': linkedin_url,
                'email': email,
                'company': company,
                'position': position,
                'connected_on': connected_on
            }
            
            # Remove None values for insert
            data = {k: v for k, v in data.items() if v is not None}
            
            if self.insert_new_contact(data):
                self.stats['new'] += 1
                print(f"  ✓ Added: {first_name} {last_name} - {company}")
            else:
                self.stats['errors'] += 1
        
        # Progress update every 100 records
        if self.stats['total'] % 100 == 0:
            print(f"  → Processed {self.stats['total']} records...")
    
    def import_contacts(self) -> bool:
        """Main import process"""
        print(f"\n📁 Reading CSV file: {self.csv_file}")
        
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                # Skip the notes at the beginning
                first_line = file.readline()
                if first_line.startswith('Notes:'):
                    # Skip the entire notes block and empty line
                    while True:
                        line = file.readline()
                        if line.strip() == '':
                            break
                else:
                    # If no notes, reset to beginning
                    file.seek(0)
                
                # Read CSV
                reader = csv.DictReader(file)
                
                print("\n🔄 Processing contacts...")
                for row in reader:
                    self.process_row(row)
                
                print("\n✓ All changes processed")
                return True
                
        except FileNotFoundError:
            print(f"✗ File not found: {self.csv_file}")
            return False
        except Exception as e:
            print(f"✗ Error processing file: {e}")
            return False
    
    def print_summary(self):
        """Print import summary"""
        print("\n" + "="*60)
        print("📊 IMPORT SUMMARY")
        print("="*60)
        print(f"Total rows processed:     {self.stats['total']:,}")
        print(f"New contacts added:       {self.stats['new']:,}")
        print(f"Updated (company only):   {self.stats['updated_company']:,}")
        print(f"Updated (position only):  {self.stats['updated_position']:,}")
        print(f"Updated (both):          {self.stats['updated_both']:,}")
        print(f"Unchanged:               {self.stats['unchanged']:,}")
        print(f"Skipped (no URL):        {self.stats['skipped']:,}")
        print(f"Errors:                  {self.stats['errors']:,}")
        print("="*60)
        
        total_updated = (self.stats['updated_company'] + 
                        self.stats['updated_position'] + 
                        self.stats['updated_both'])
        print(f"\n✅ Successfully processed {self.stats['new'] + total_updated:,} changes")
    
    def run(self) -> bool:
        """Execute the full import process"""
        if not self.connect():
            return False
        
        try:
            success = self.import_contacts()
            self.print_summary()
            return success
        except Exception as e:
            print(f"✗ Import failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Import LinkedIn contacts to Supabase'
    )
    parser.add_argument(
        '--file', '-f',
        default='/Volumes/T7/true_steele/Code/contacts/data/Connections.csv',
        help='Path to LinkedIn Connections CSV file'
    )
    
    args = parser.parse_args()
    
    # Check for required environment variables
    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_KEY"):
        print("Error: Missing required environment variables!")
        print("Please ensure SUPABASE_URL and SUPABASE_SERVICE_KEY are set in .env file")
        sys.exit(1)
    
    # Run import
    importer = LinkedInSupabaseImporter(args.file)
    success = importer.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()