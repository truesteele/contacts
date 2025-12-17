#!/usr/bin/env python3
"""
LinkedIn Contacts Import Script
Imports contacts from LinkedIn CSV export to Supabase database
Tracks changes to company and position fields
"""

import csv
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import argparse
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection settings
DB_CONFIG = {
    'host': 'aws-0-us-east-1.pooler.supabase.com',
    'port': 6543,  # Using pooler port
    'database': 'postgres',
    'user': 'postgres.ypqsrejrsocebnldicke',
    'password': os.environ.get('SUPABASE_DB_PASSWORD', '')
}

class LinkedInImporter:
    def __init__(self, db_config: Dict, csv_file: str):
        self.db_config = db_config
        self.csv_file = csv_file
        self.conn = None
        self.cursor = None
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
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            print("✓ Connected to database")
            return True
        except psycopg2.Error as e:
            print(f"✗ Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            
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
        query = """
            SELECT id, first_name, last_name, company, position, email, linkedin_url
            FROM contacts 
            WHERE linkedin_url = %s
            LIMIT 1
        """
        self.cursor.execute(query, (linkedin_url,))
        return self.cursor.fetchone()
    
    def insert_new_contact(self, data: Dict) -> bool:
        """Insert a new contact record"""
        query = """
            INSERT INTO contacts (
                first_name, last_name, linkedin_url, email, 
                company, position, connected_on, last_import_date
            ) VALUES (
                %(first_name)s, %(last_name)s, %(linkedin_url)s, %(email)s,
                %(company)s, %(position)s, %(connected_on)s, NOW()
            )
        """
        try:
            self.cursor.execute(query, data)
            return True
        except psycopg2.Error as e:
            print(f"  ✗ Insert failed for {data['first_name']} {data['last_name']}: {e}")
            self.conn.rollback()
            return False
    
    def update_existing_contact(self, contact_id: int, updates: Dict, 
                              old_company: str, old_position: str) -> bool:
        """Update existing contact with change tracking"""
        update_parts = []
        params = {'id': contact_id}
        
        # Track company changes
        if 'company' in updates and updates['company'] != old_company:
            update_parts.extend([
                "company = %(company)s",
                "previous_company = %(previous_company)s",
                "company_updated_at = NOW()"
            ])
            params['company'] = updates['company']
            params['previous_company'] = old_company
        
        # Track position changes
        if 'position' in updates and updates['position'] != old_position:
            update_parts.extend([
                "position = %(position)s",
                "previous_position = %(previous_position)s",
                "position_updated_at = NOW()"
            ])
            params['position'] = updates['position']
            params['previous_position'] = old_position
        
        # Update email if provided and not already set
        if 'email' in updates and updates['email']:
            update_parts.append("email = COALESCE(email, %(email)s)")
            params['email'] = updates['email']
        
        # Always update last import date
        update_parts.append("last_import_date = NOW()")
        
        query = f"""
            UPDATE contacts 
            SET {', '.join(update_parts)}
            WHERE id = %(id)s
        """
        
        try:
            self.cursor.execute(query, params)
            return True
        except psycopg2.Error as e:
            print(f"  ✗ Update failed for ID {contact_id}: {e}")
            self.conn.rollback()
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
            company_changed = (company and company != existing['company'])
            position_changed = (position and position != existing['position'])
            
            if company_changed or position_changed:
                updates = {}
                if company_changed:
                    updates['company'] = company
                if position_changed:
                    updates['position'] = position
                if email and not existing['email']:
                    updates['email'] = email
                
                if self.update_existing_contact(
                    existing['id'], 
                    updates,
                    existing['company'],
                    existing['position']
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
                query = "UPDATE contacts SET last_import_date = NOW() WHERE id = %s"
                self.cursor.execute(query, (existing['id'],))
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
            
            if self.insert_new_contact(data):
                self.stats['new'] += 1
                print(f"  ✓ Added: {first_name} {last_name} - {company}")
            else:
                self.stats['errors'] += 1
        
        # Commit every 100 records
        if self.stats['total'] % 100 == 0:
            self.conn.commit()
            print(f"  → Processed {self.stats['total']} records...")
    
    def import_contacts(self) -> bool:
        """Main import process"""
        print(f"\n📁 Reading CSV file: {self.csv_file}")
        
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                # Skip the notes at the beginning
                notes_line = file.readline()
                if notes_line.startswith('Notes:'):
                    empty_line = file.readline()  # Skip empty line after notes
                else:
                    # If no notes, reset to beginning
                    file.seek(0)
                
                # Read CSV
                reader = csv.DictReader(file)
                
                print("\n🔄 Processing contacts...")
                for row in reader:
                    self.process_row(row)
                
                # Final commit
                self.conn.commit()
                print("\n✓ All changes committed")
                return True
                
        except FileNotFoundError:
            print(f"✗ File not found: {self.csv_file}")
            return False
        except Exception as e:
            print(f"✗ Error processing file: {e}")
            self.conn.rollback()
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
        finally:
            self.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description='Import LinkedIn contacts to Supabase'
    )
    parser.add_argument(
        '--file', '-f',
        default='/Volumes/T7/true_steele/Code/contacts/data/Connections.csv',
        help='Path to LinkedIn Connections CSV file'
    )
    parser.add_argument(
        '--password', '-p',
        help='Database password (or set SUPABASE_DB_PASSWORD env var)'
    )
    
    args = parser.parse_args()
    
    # Check for password
    if args.password:
        DB_CONFIG['password'] = args.password
    elif not DB_CONFIG['password']:
        print("Error: Database password required!")
        print("Set SUPABASE_DB_PASSWORD environment variable or use --password flag")
        sys.exit(1)
    
    # Run import
    importer = LinkedInImporter(DB_CONFIG, args.file)
    success = importer.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()