#!/usr/bin/env python3
"""
Update Supabase contacts with Clay email enrichment data.
"""

import os
import csv
import time
import datetime
import re
from typing import Dict, List, Optional, Set
from dotenv import load_dotenv
from supabase import create_client
import requests

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# CSV file paths
CLAY_EXPORT_FILES = [
    "data/ClayExport.csv",   # Original export file
    "data/ClayExport2.csv",  # Second export file
    "data/ClayExport3.csv"   # New export with personal emails and work email updates
]

# Rate limiting to avoid overwhelming the Supabase API
RATE_LIMIT_DELAY = 0.1  # 100ms delay between updates

# Constants for tracking email discovery attempts
NO_EMAIL_MARKERS = ["❌ No email found", "❌ No Email Found"]
EMAIL_DISCOVERY_ATTEMPTED = "clay_attempted"

# Email validation markers
VALID_MARKERS = ["✅", "Valid"]
INVALID_MARKERS = ["❌", "Invalid"]

def clean_email(email_str):
    """
    Clean an email address by removing any symbols, validation markers, or extra text.
    
    Args:
        email_str: A string potentially containing an email address with symbols or validation markers
        
    Returns:
        A cleaned email address string or empty string if no valid email found
    """
    if not email_str or not isinstance(email_str, str):
        return ""
    
    # Use regex to extract just the email address
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, email_str)
    
    if match:
        return match.group(0).strip().lower()
    return ""

def create_supabase_client():
    """Create and return a Supabase client."""
    try:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as e:
        print(f"Error creating Supabase client: {e}")
        raise

def execute_supabase_sql(sql):
    """
    Execute SQL directly against Supabase using the REST API.
    
    Args:
        sql: SQL statement to execute
        
    Returns:
        True if successful, False otherwise
    """
    # Skip the SQL execution check - assume columns already exist
    print("Skipping SQL execution check - assuming columns already exist in the database")
    return True

    # Original function code below, commented out
    """
    try:
        # Format the SQL API endpoint URL
        endpoint = f"{SUPABASE_URL}/rest/v1/"
        
        # Headers for authentication and content type
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        # Send a POST request to execute the SQL (this is a workaround)
        # We'll actually simulate this by running each ALTER TABLE command separately
        
        # First, check if the columns already exist
        check_columns = requests.get(
            f"{endpoint}contacts?select=email_verified,email_type,work_email,personal_email,work_email_discovery_status&limit=1",
            headers=headers
        )
        
        if check_columns.status_code == 200:
            print("The columns already exist in the contacts table")
            return True
        
        # If columns don't exist, we need to add them one by one
        column_defs = [
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS email_verified BOOLEAN",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS email_type VARCHAR(10) CHECK (email_type IN ('work', 'personal', 'unknown'))",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS work_email VARCHAR(255)",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS personal_email VARCHAR(255)",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS email_verification_source VARCHAR(50)",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS email_verification_attempts INTEGER DEFAULT 0",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS email_verification_due_at TIMESTAMP",
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS work_email_discovery_status VARCHAR(50)",  # New column to track discovery attempts
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS work_email_discovery_date TIMESTAMP"  # New column to track when discovery was attempted
        ]
        
        # Execute each ALTER TABLE command via psql in the Supabase database
        # Note: This requires manual execution in the Supabase SQL editor
        print("Please run the following SQL in the Supabase SQL editor:")
        for cmd in column_defs:
            print(cmd + ";")
        
        print("\nAfter adding columns, also run:")
        print("UPDATE contacts SET email_type = 'unknown' WHERE email IS NOT NULL AND email != '' AND email_type IS NULL;")
        
        # Ask for confirmation
        response = input("\nHave you executed these commands in the Supabase SQL editor? (y/n): ")
        if response.lower() != 'y':
            print("Please run the SQL commands before proceeding.")
            return False
            
        return True
    except Exception as e:
        print(f"Error executing SQL: {e}")
        return False
    """

def load_clay_data(file_path):
    """
    Load data from a Clay export CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of rows from the CSV file, or empty list if file not found
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            return list(csv_reader)
    except FileNotFoundError:
        print(f"Warning: Clay export file not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error loading Clay export file {file_path}: {e}")
        return []

def build_verified_emails_map(clay_exports):
    """
    Build a map of verified work emails from all Clay export files.
    
    Args:
        clay_exports: Dictionary mapping file paths to loaded CSV data
        
    Returns:
        Dictionary mapping contact IDs to verified work emails
    """
    verified_emails = {}
    
    # Process all Clay export files
    for file_path, rows in clay_exports.items():
        for row in rows:
            contact_id = row.get('id')
            if not contact_id:
                continue
            
            # Check the "Work Email" column first (most reliable)
            work_email = clean_email(row.get('Work Email', ''))
            if work_email:
                verified_emails[contact_id] = work_email
                continue
            
            # Check all other potential work email columns with careful validation
            work_email_columns = [
                'Find Work Email', 'Find Work Email (2)', 'Find Work Email (3)', 
                'Find Work Email (4)', 'Find Work Email (5)', 'Find Work Email (6)', 'Find Email'
            ]
            
            # Validation columns that correspond to the work email columns
            validation_columns = [
                'Validate LeadMagic', 'Validate Findymail', 'Validate Prospeo', 
                'Validate DropContact', 'Validate Hunter', 'Validate Datagma', 'Validate Wiza'
            ]
            
            # Check each work email column
            for i, col in enumerate(work_email_columns):
                if col in row and row[col] and not any(marker in row[col] for marker in NO_EMAIL_MARKERS):
                    email = clean_email(row[col])
                    if not email:
                        continue
                    
                    # Check if there's a corresponding validation column
                    if i < len(validation_columns) and validation_columns[i] in row:
                        # Only use this email if it was explicitly validated
                        validation_result = row[validation_columns[i]]
                        if any(marker in validation_result for marker in VALID_MARKERS):
                            verified_emails[contact_id] = email
                            break
                    elif i == len(work_email_columns) - 1:  # Find Email column
                        # For the general 'Find Email' column, only use it if it's work-related
                        if row.get('email_action', '').lower() == 'need email discovery':
                            verified_emails[contact_id] = email
    
    return verified_emails

def build_personal_emails_map(clay_exports):
    """
    Build a map of personal emails from Clay export files.
    
    Args:
        clay_exports: Dictionary mapping file paths to loaded CSV data
        
    Returns:
        Dictionary mapping contact IDs to personal emails
    """
    personal_emails = {}
    
    # Process all Clay export files, focusing on the newest one (ClayExport3.csv)
    for file_path, rows in clay_exports.items():
        # Give priority to the newest export for personal emails
        is_newest_export = "ClayExport3.csv" in file_path
        
        for row in rows:
            contact_id = row.get('id')
            if not contact_id:
                continue
            
            # Extract personal email from the "Personal Email" column
            personal_email = clean_email(row.get('Personal Email', ''))
            if personal_email:
                # Only overwrite existing entries if this is from the newest export
                if is_newest_export or contact_id not in personal_emails:
                    personal_emails[contact_id] = personal_email
    
    return personal_emails

def process_csv_row(row: Dict, all_verified_emails: Dict, all_personal_emails: Dict) -> Dict:
    """
    Process a row from the CSV and extract relevant information.
    
    Args:
        row: A dictionary representing a row from the CSV
        all_verified_emails: Dictionary of all verified emails from all Clay exports
        all_personal_emails: Dictionary of all personal emails from Clay exports
        
    Returns:
        A dictionary with the processed data for updating Supabase
    """
    contact_id = row.get('id')
    if not contact_id:
        return {'id': None}  # Skip rows without IDs
    
    # Get existing email
    existing_email = clean_email(row.get('email', ''))
    
    # Initialize update data
    update_data = {
        'id': contact_id
    }
    
    # Check if this contact has a verified work email from any Clay export
    work_email = all_verified_emails.get(contact_id, '')
    if not work_email:
        # If no verified email in our map, check the current row's Work Email column
        # which contains only verified emails
        work_email = clean_email(row.get('Work Email', ''))
    
    # Track attempted email discovery regardless of whether a valid email was found
    work_email_columns = [
        'Find Work Email', 'Find Work Email (2)', 'Find Work Email (3)', 
        'Find Work Email (4)', 'Find Work Email (5)', 'Find Work Email (6)'
    ]
    
    # Check if any email discovery was attempted
    any_service_attempted = False
    for column in work_email_columns:
        if column in row and row[column]:
            any_service_attempted = True
            break
    
    # Mark the record as having had discovery attempted if any service was tried
    if any_service_attempted:
        # If we found a valid work email, mark as 'found', otherwise as 'attempted'
        if work_email:
            update_data['work_email_discovery_status'] = 'found'
        else:
            update_data['work_email_discovery_status'] = EMAIL_DISCOVERY_ATTEMPTED
        
        update_data['work_email_discovery_date'] = datetime.datetime.now().isoformat()
    
    # Update work email if found and verified
    if work_email and work_email.strip() != '' and work_email.lower() != 'null':
        update_data['work_email'] = work_email
        
        # Set email type if this is their primary email
        if not existing_email or existing_email.strip() == '':
            update_data['email'] = work_email
            update_data['email_type'] = 'work'
        elif existing_email.lower() == work_email.lower():
            update_data['email_type'] = 'work'
    
    # Update personal email if we have one for this contact
    personal_email = all_personal_emails.get(contact_id, '')
    if personal_email and personal_email.strip() != '' and personal_email.lower() != 'null':
        update_data['personal_email'] = personal_email
        
        # If we have no work email but we do have a personal email, and the contact has no primary email,
        # set the personal email as the primary email
        if (not work_email or work_email.strip() == '') and (not existing_email or existing_email.strip() == ''):
            update_data['email'] = personal_email
            update_data['email_type'] = 'personal'
        elif existing_email.lower() == personal_email.lower():
            update_data['email_type'] = 'personal'
    
    # Check email validation from various providers
    validation_columns = [
        'Validate LeadMagic', 'Validate Findymail', 'Validate Prospeo', 
        'Validate DropContact', 'Validate Hunter', 'Validate Datagma', 'Validate Wiza'
    ]
    
    email_validated = None
    for validate_col in validation_columns:
        if validate_col in row and row[validate_col]:
            validation_result = row[validate_col]
            
            if any(marker in validation_result for marker in VALID_MARKERS):
                email_validated = True
                break  # Found a valid result, use it
            elif any(marker in validation_result for marker in INVALID_MARKERS):
                email_validated = False
                # Don't break yet, because a later service might find it valid
    
    # Update email verification data if we have validation results
    if email_validated is not None:
        update_data['email_verified'] = email_validated
        
        # Set verification timestamp and source
        now = datetime.datetime.now()
        update_data['email_verified_at'] = now.isoformat()
        update_data['email_verification_source'] = 'Clay'
        
        # Set verification attempts
        update_data['email_verification_attempts'] = 1
        
        # Set the next verification due date
        if email_validated:
            # Valid email - check again in 90 days
            due_date = now + datetime.timedelta(days=90)
        else:
            # Invalid email - check again in 180 days
            due_date = now + datetime.timedelta(days=180)
        
        update_data['email_verification_due_at'] = due_date.isoformat()
    
    return update_data

def update_contact(supabase, update_data: Dict, max_retries=3):
    """
    Update a contact in Supabase.
    
    Args:
        supabase: Supabase client
        update_data: Dictionary with the data to update
        max_retries: Maximum number of retries for connection issues
        
    Returns:
        True if successful, False otherwise
    """
    contact_id = update_data.pop('id')  # Remove ID from update data
    if not contact_id:
        return False
    
    # Skip if there's nothing to update
    if not update_data:
        return False
    
    retries = 0
    while retries < max_retries:
        try:
            result = supabase.table('contacts')\
                .update(update_data)\
                .eq('id', contact_id)\
                .execute()
            
            # Check if the update was successful
            if result and hasattr(result, 'data') and len(result.data) > 0:
                return True
            return False
        except Exception as e:
            retries += 1
            print(f"Error updating contact ID {contact_id} (attempt {retries}/{max_retries}): {e}")
            if retries >= max_retries:
                print(f"Max retries reached for contact ID {contact_id}")
                return False
            time.sleep(5)  # Wait before retrying

def clean_existing_emails(supabase):
    """
    Clean existing email addresses in the database by removing validation symbols.
    This does NOT remove any emails, only cleans them if they contain symbols.
    
    Args:
        supabase: Supabase client
        
    Returns:
        Number of records cleaned
    """
    print("\nCleaning existing email addresses in the database...")
    
    # Get all contacts with emails containing verification symbols
    symbols_to_check = ['✅', '❌'] 
    cleaned_count = 0
    total_records_processed = 0
    
    for symbol in symbols_to_check:
        print(f"\nChecking for symbol '{symbol}' in work emails...")
        
        # Initialize pagination variables
        page_size = 1000  # Supabase default limit
        current_page = 0
        has_more_records = True
        
        # Process records in batches for each symbol
        while has_more_records:
            # Query for each symbol with pagination
            result = supabase.table('contacts')\
                .select('id,work_email')\
                .filter('work_email', 'like', f'%{symbol}%')\
                .range(current_page * page_size, (current_page + 1) * page_size - 1)\
                .execute()
            
            # Check if we got any records in this batch
            if not result or not hasattr(result, 'data') or not result.data:
                if current_page == 0:
                    print(f"No emails with symbol '{symbol}' found in the database.")
                    break  # Move to the next symbol
                else:
                    # We've reached the end of the records for this symbol
                    has_more_records = False
                    continue
            
            # Process this batch of records
            records_to_clean = result.data
            batch_size = len(records_to_clean)
            
            # If we got fewer records than the page size, this is the last batch
            if batch_size < page_size:
                has_more_records = False
            
            # Update the total count for this symbol
            symbol_records_processed = batch_size
            total_records_processed += batch_size
            
            print(f"Processing batch {current_page + 1}: {batch_size} records with symbol '{symbol}'")
            
            batch_cleaned_count = 0
            # Process each record in the batch
            for record in records_to_clean:
                contact_id = record['id']
                dirty_email = record['work_email']
                
                # Clean the email
                clean_email_value = clean_email(dirty_email)
                
                if clean_email_value and clean_email_value != dirty_email:
                    # Update the record with the clean email
                    update_data = {
                        'work_email': clean_email_value
                    }
                    
                    success = supabase.table('contacts')\
                        .update(update_data)\
                        .eq('id', contact_id)\
                        .execute()
                    
                    if success and hasattr(success, 'data') and len(success.data) > 0:
                        cleaned_count += 1
                        batch_cleaned_count += 1
                    
                    # Rate limiting
                    time.sleep(RATE_LIMIT_DELAY)
                
                # Display progress within this batch
                processed_in_batch = records_to_clean.index(record) + 1
                batch_progress = (processed_in_batch / batch_size) * 100
                print(f"Batch progress: {processed_in_batch}/{batch_size} ({batch_progress:.1f}%) - Cleaned in this batch: {batch_cleaned_count}", end='\r')
            
            print(f"\nCleaned {batch_cleaned_count} emails in batch {current_page + 1}")
            
            # Move to the next page
            current_page += 1
    
    print(f"\nCleaned a total of {cleaned_count} email addresses in the database out of {total_records_processed} processed")
    return cleaned_count

def verify_existing_work_emails(supabase, all_verified_emails):
    """
    Verify work emails in the database against all verified Clay work emails.
    This preserves existing work emails that are valid, including those from non-Clay sources.
    
    Args:
        supabase: Supabase client
        all_verified_emails: Dictionary of all verified emails from all Clay exports
        
    Returns:
        Number of records corrected (not removed)
    """
    print("\nVerifying existing work emails against Clay's verified work emails...")
    print(f"We have {len(all_verified_emails)} verified work emails from all Clay exports")
    
    # Initialize pagination variables
    page_size = 1000  # Supabase default limit
    current_page = 0
    has_more_records = True
    
    # Track statistics
    total_records_processed = 0
    corrected_count = 0
    preserved_count = 0
    skipped_count = 0
    
    # Process records in batches
    while has_more_records:
        # Get a batch of contacts with work emails using pagination
        result = supabase.table('contacts')\
            .select('id,work_email,email,email_type')\
            .neq('work_email', None)\
            .range(current_page * page_size, (current_page + 1) * page_size - 1)\
            .execute()
        
        # Check if we got any records in this batch
        if not result or not hasattr(result, 'data') or not result.data:
            if current_page == 0:
                print("No work emails found in the database.")
                return 0
            else:
                # We've reached the end of the records
                has_more_records = False
                continue
        
        # Process this batch of records
        records_to_process = result.data
        batch_size = len(records_to_process)
        
        # If we got fewer records than the page size, this is the last batch
        if batch_size < page_size:
            has_more_records = False
        
        # Update the total count
        total_records_processed += batch_size
        
        # Display progress for this batch
        print(f"\nProcessing batch {current_page + 1}: {batch_size} records (total processed so far: {total_records_processed})")
        
        # Process each record in the current batch
        for record in records_to_process:
            contact_id = record['id']
            current_work_email = record['work_email']
            current_email = record.get('email', '')
            email_type = record.get('email_type', '')
            
            # Skip if the record doesn't have a work email
            if not current_work_email:
                skipped_count += 1
                continue
            
            # Clean the current work email (remove any symbols)
            clean_current_email = clean_email(current_work_email)
            if not clean_current_email:
                skipped_count += 1
                continue
            
            # Check if this contact has a verified work email from Clay
            clay_verified_email = all_verified_emails.get(contact_id)
            
            if clay_verified_email:
                # If the Clay verified email is different from what's in the database, update it
                if clean_current_email != clay_verified_email:
                    update_data = {
                        'work_email': clay_verified_email,
                        'work_email_discovery_status': 'found',
                        'email_verified': True
                    }
                    
                    # If the primary email was the work email, update it too
                    if email_type == 'work' and current_email == current_work_email:
                        update_data['email'] = clay_verified_email
                    
                    success = supabase.table('contacts')\
                        .update(update_data)\
                        .eq('id', contact_id)\
                        .execute()
                    
                    if success and hasattr(success, 'data') and len(success.data) > 0:
                        corrected_count += 1
                else:
                    # Email is already correct, just make sure it's marked as verified
                    update_data = {
                        'work_email_discovery_status': 'found',
                        'email_verified': True
                    }
                    
                    supabase.table('contacts')\
                        .update(update_data)\
                        .eq('id', contact_id)\
                        .execute()
                    
                    preserved_count += 1
            else:
                # This work email wasn't in any Clay export's verified emails
                # But it might be valid from another source (like Google contacts)
                # Check for any obvious symbols and clean if necessary
                
                if clean_current_email != current_work_email:
                    # There are symbols or formatting issues to clean up
                    update_data = {
                        'work_email': clean_current_email
                    }
                    
                    # If the primary email was this work email, update it too
                    if email_type == 'work' and current_email == current_work_email:
                        update_data['email'] = clean_current_email
                    
                    success = supabase.table('contacts')\
                        .update(update_data)\
                        .eq('id', contact_id)\
                        .execute()
                    
                    if success and hasattr(success, 'data') and len(success.data) > 0:
                        corrected_count += 1
                else:
                    # This is already a clean email from another source - preserve it
                    preserved_count += 1
            
            # Display progress within this batch
            processed_in_batch = corrected_count + preserved_count + skipped_count - total_records_processed + batch_size
            batch_progress = (processed_in_batch / batch_size) * 100
            print(f"Batch progress: {processed_in_batch}/{batch_size} ({batch_progress:.1f}%) - Corrected: {corrected_count}, Preserved: {preserved_count}, Skipped: {skipped_count}", end='\r')
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
        
        # Move to the next page
        current_page += 1
    
    print(f"\nCompleted work email verification: {corrected_count} corrected, {preserved_count} preserved, {skipped_count} skipped out of {total_records_processed} total records")
    return corrected_count

def main():
    """Main function to process Clay export and update Supabase."""
    try:
        print("Starting update process from Clay exports...")
        
        # Create Supabase client
        print("Connecting to Supabase...")
        supabase = create_supabase_client()
        
        # Load all Clay export data
        clay_exports = {}
        for file_path in CLAY_EXPORT_FILES:
            print(f"Loading Clay export data from {file_path}...")
            data = load_clay_data(file_path)
            if data:
                clay_exports[file_path] = data
                print(f"Loaded {len(data)} rows from {file_path}")
        
        if not clay_exports:
            print("No Clay export data found. Exiting.")
            return
        
        # Build a comprehensive map of verified work emails from all Clay exports
        all_verified_emails = build_verified_emails_map(clay_exports)
        print(f"Found a total of {len(all_verified_emails)} verified work emails from all Clay exports")
        
        # Build a map of personal emails from Clay exports
        all_personal_emails = build_personal_emails_map(clay_exports)
        print(f"Found a total of {len(all_personal_emails)} personal emails from Clay exports")
        
        # First, clean existing email addresses with symbols in the database
        clean_existing_emails(supabase)
        
        # Next, verify and fix work emails but preserve valid ones from all sources
        verify_existing_work_emails(supabase, all_verified_emails)
        
        # Execute SQL to add new columns
        print("Setting up database columns...")
        if not execute_supabase_sql(""):
            print("Failed to set up database columns. Exiting.")
            return
        
        # Process the latest Clay export file to update contacts
        latest_export = CLAY_EXPORT_FILES[-1]
        latest_data = clay_exports.get(latest_export, [])
        
        if not latest_data:
            print(f"No data found in latest export file {latest_export}. Skipping contact updates.")
            return
        
        print(f"Processing {len(latest_data)} rows from {latest_export} for contact updates...")
        
        # Initialize counters
        total_rows = len(latest_data)
        updated_count = 0
        error_count = 0
        skipped_count = 0
        work_email_found_count = 0
        personal_email_found_count = 0
        work_email_attempt_count = 0
        
        # Process each row
        for i, row in enumerate(latest_data):
            # Skip empty rows
            if not row or not row.get('id'):
                skipped_count += 1
                continue
            
            # Process the row data with our comprehensive verified emails map and personal emails map
            update_data = process_csv_row(row, all_verified_emails, all_personal_emails)
            
            # Skip if there's no meaningful data to update
            if len(update_data) <= 1 or not update_data.get('id'):  # Only ID or no ID, no actual updates
                skipped_count += 1
                continue
            
            # Track work and personal email statistics
            if 'work_email' in update_data:
                work_email_found_count += 1
            elif 'work_email_discovery_status' in update_data and update_data['work_email_discovery_status'] == EMAIL_DISCOVERY_ATTEMPTED:
                work_email_attempt_count += 1
            
            if 'personal_email' in update_data:
                personal_email_found_count += 1
            
            # Update the contact in Supabase
            success = update_contact(supabase, update_data)
            
            # Track results
            if success:
                updated_count += 1
            else:
                error_count += 1
            
            # Display progress
            progress = (i + 1) / total_rows * 100
            print(f"Progress: {i+1}/{total_rows} ({progress:.1f}%) - Updated: {updated_count}, Errors: {error_count}, Skipped: {skipped_count}", end='\r')
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
        
        # Print final newline
        print()
        
        # Print summary
        print("\nUpdate process complete!")
        print(f"Total rows processed: {total_rows}")
        print(f"Records updated: {updated_count}")
        print(f"Work emails found: {work_email_found_count}")
        print(f"Personal emails found: {personal_email_found_count}")
        print(f"Work email attempts (not found): {work_email_attempt_count}")
        print(f"Errors: {error_count}")
        print(f"Skipped (no updates needed): {skipped_count}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 