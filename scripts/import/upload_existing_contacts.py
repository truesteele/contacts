#!/usr/bin/env python3
"""
Upload existing classified contacts to Supabase database.
This script takes the already classified contacts from a CSV file
and uploads them to Supabase.
"""

import csv
import os
import time
import argparse
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def create_supabase_client():
    """Create and return a Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("Supabase URL and service key must be set in environment variables")
    
    return create_client(url, key)

def convert_row_to_supabase_format(row: Dict[str, str]) -> Dict[str, str]:
    """Convert CSV row to the format expected by Supabase table."""
    # Create a mapping of CSV column names to database column names
    column_mapping = {
        'First Name': 'first_name',
        'Last Name': 'last_name',
        'LinkedIn URL': 'linkedin_url',
        'Email': 'email',
        'Email (2)': 'email_2',
        'Normalized Phone Number': 'normalized_phone_number',
        'Company': 'company',
        'Position': 'position',
        'Connected On': 'connected_on',
        'Enrich Person from Profile': 'enrich_person_from_profile',
        'Headline': 'headline',
        'Summary': 'summary',
        'Country': 'country',
        'Location Name': 'location_name',
        'Title - Projects': 'title_projects',
        'Summary - Projects': 'summary_projects',
        'End Date - Projects': 'end_date_projects',
        'Start Date - Projects': 'start_date_projects',
        'Summary - Volunteering': 'summary_volunteering',
        'Role - Volunteering': 'role_volunteering',
        'Company Name - Volunteering': 'company_name_volunteering',
        'Company Domain - Volunteering': 'company_domain_volunteering',
        'Title - Publications': 'title_publications',
        'Summary - Publications': 'summary_publications',
        'Publisher - Publications': 'publisher_publications',
        'Url - Publications': 'url_publications',
        'Org': 'org',
        'Connections': 'connections',
        'Num Followers': 'num_followers',
        'Summary - Experience': 'summary_experience',
        'Company - Experience': 'company_experience',
        'End Date - Experience': 'end_date_experience',
        'Company Domain - Experience': 'company_domain_experience',
        'School Name - Education': 'school_name_education',
        'Activities - Education': 'activities_education',
        'Degree - Education': 'degree_education',
        'End Date - Education': 'end_date_education',
        'Start Date - Education': 'start_date_education',
        'Field Of Study - Education': 'field_of_study_education',
        'Company Name - Awards': 'company_name_awards',
        'Title - Awards': 'title_awards',
        'Summary - Awards': 'summary_awards',
        'Normalized First Name': 'normalized_first_name',
        'Normalized Last Name': 'normalized_last_name',
        'Normalized Full Name': 'normalized_full_name',
        'Lookup Single Row in Other Table': 'lookup_single_row_in_other_table',
        'LinkedIn Profile': 'linkedin_profile',
        'Taxonomy Classification': 'taxonomy_classification'
    }
    
    # Create a new dictionary with the correct column names
    supabase_row = {}
    for field, value in row.items():
        if field in column_mapping:
            db_column = column_mapping[field]
            supabase_row[db_column] = value if value else ''
    
    return supabase_row

def upload_existing_contacts(
    input_file: str,
    supabase_client: Any,
    batch_size: int = 10,
    start_index: int = 0,
    end_index: Optional[int] = None
) -> None:
    """Upload existing classified contacts to Supabase."""
    
    # Read the input CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
    
    total_rows = len(all_rows)
    print(f"Found {total_rows} contacts in the CSV file")
    
    # Determine the range of rows to process
    if end_index is None:
        end_index = total_rows
    else:
        end_index = min(end_index, total_rows)
    
    if start_index >= total_rows:
        print(f"Start index {start_index} is beyond the end of the file. Nothing to process.")
        return
    
    rows_to_process = all_rows[start_index:end_index]
    print(f"Will process {len(rows_to_process)} contacts from index {start_index} to {end_index - 1}")
    
    # For progress tracking
    batch = []
    processed_count = 0
    start_time = time.time()
    
    try:
        # Process contacts in batches
        for i, row in enumerate(rows_to_process):
            if 'Taxonomy Classification' not in row or not row['Taxonomy Classification']:
                print(f"Warning: Contact at position {start_index + i} has no classification. Skipping.")
                continue
            
            # Convert to Supabase format
            supabase_row = convert_row_to_supabase_format(row)
            
            # Add to the batch
            batch.append(supabase_row)
            
            # If batch is full or this is the last item, upload to Supabase
            if len(batch) >= batch_size or i == len(rows_to_process) - 1:
                try:
                    result = supabase_client.table('contacts').insert(batch).execute()
                    
                    # Check for errors
                    if hasattr(result, 'error') and result.error:
                        print(f"Error uploading batch to Supabase: {result.error}")
                    else:
                        processed_count += len(batch)
                        elapsed = time.time() - start_time
                        avg_time = elapsed / processed_count if processed_count > 0 else 0
                        
                        # Calculate progress and ETA
                        percent_done = (processed_count / len(rows_to_process)) * 100
                        remaining_items = len(rows_to_process) - processed_count
                        eta_seconds = remaining_items * avg_time if avg_time > 0 else 0
                        eta_minutes = int(eta_seconds / 60)
                        eta_seconds = int(eta_seconds % 60)
                        
                        print(f"Uploaded batch of {len(batch)} contacts to Supabase. "
                              f"Progress: {processed_count}/{len(rows_to_process)} "
                              f"({percent_done:.1f}%) - ETA: {eta_minutes}m {eta_seconds}s")
                        
                except Exception as e:
                    print(f"Error during batch upload: {e}")
                
                # Clear the batch and add a small delay
                batch = []
                time.sleep(0.2)  # Small delay to avoid overwhelming the Supabase API
                
            # Print progress every 100 contacts
            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(rows_to_process)} contacts...")
        
        total_time = time.time() - start_time
        minutes = int(total_time / 60)
        seconds = int(total_time % 60)
        print(f"Upload completed. {processed_count} contacts uploaded in {minutes}m {seconds}s.")
        
    except KeyboardInterrupt:
        current_position = start_index + processed_count
        print("\nProcess interrupted by user.")
        print(f"Uploaded {processed_count} out of {len(rows_to_process)} contacts.")
        print(f"To resume, start from index {current_position}.")

def main():
    parser = argparse.ArgumentParser(description="Upload existing classified contacts to Supabase")
    parser.add_argument("--input", type=str, required=True, help="Path to the classified contacts CSV file")
    parser.add_argument("--batch-size", type=int, default=20, help="Number of contacts to upload in each batch")
    parser.add_argument("--start", type=int, default=0, help="Starting index in the CSV")
    parser.add_argument("--end", type=int, help="Ending index in the CSV (optional)")
    parser.add_argument("--only-classified", action="store_true", help="Only upload contacts that have classifications")
    
    args = parser.parse_args()
    
    try:
        print("Creating Supabase client...")
        supabase_client = create_supabase_client()
        
        print(f"Starting upload from {args.input} to Supabase...")
        upload_existing_contacts(
            args.input,
            supabase_client,
            args.batch_size,
            args.start,
            args.end
        )
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 