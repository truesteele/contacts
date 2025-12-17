#!/usr/bin/env python3
"""
Process Bay Area Philanthropy leads CSV and upload to Supabase.
Adapts the existing batch categorization script with column mapping for the new CSV format.
"""

import csv
import json
import os
import time
import hashlib
from openai import OpenAI
from typing import Dict, List, Any, Optional, Tuple
import argparse
from dotenv import load_dotenv
from supabase import create_client
from column_mapping import convert_row, COLUMN_MAPPING

# Load environment variables
load_dotenv()

# Import constants from existing script
from supabase_batch_categorize import (
    TAXONOMY_MAP,
    FLAT_TAXONOMY,
    create_openai_client,
    create_supabase_client,
    get_unique_identifier,
    check_existing_contacts,
    prepare_contact_for_classification,
    batch_classify_contacts,
    convert_row_to_supabase_format,
)

def read_csv_with_mapping(input_file: str) -> List[Dict[str, str]]:
    """Read CSV file and convert rows using column mapping."""
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        mapped_rows = []
        for row in reader:
            mapped_row = convert_row(row)
            mapped_rows.append(mapped_row)
    return mapped_rows

def process_bay_area_leads(
    input_file: str,
    openai_client: OpenAI,
    supabase_client: Any,
    openai_batch_size: int = 5,
    supabase_batch_size: int = 20,
    sample_size: Optional[int] = None,
    start_index: int = 0,
    check_chunk_size: int = 50
) -> None:
    """Process Bay Area leads CSV with column mapping and upload to Supabase."""
    
    # Read the input CSV with column mapping
    all_rows = read_csv_with_mapping(input_file)
    
    total_rows = len(all_rows)
    print(f"Found {total_rows} contacts in the CSV file")
    
    # Determine which rows to process
    if sample_size:
        end_index = min(start_index + sample_size, total_rows)
        rows_to_process = all_rows[start_index:end_index]
    else:
        rows_to_process = all_rows[start_index:]
    
    print(f"Will process {len(rows_to_process)} contacts from index {start_index}")
    
    # Check for existing contacts in Supabase in chunks to avoid query length issues
    print("Checking for existing contacts in Supabase...")
    existing_ids = set()
    
    # Process in chunks to avoid overloading Supabase
    for i in range(0, len(rows_to_process), check_chunk_size):
        chunk = rows_to_process[i:i + check_chunk_size]
        chunk_size = len(chunk)
        print(f"Checking chunk {i//check_chunk_size + 1} of {(len(rows_to_process) + check_chunk_size - 1)//check_chunk_size} ({chunk_size} contacts)...")
        
        chunk_existing_ids = check_existing_contacts(supabase_client, chunk)
        existing_ids.update(chunk_existing_ids)
        
        # Add a delay between chunks to avoid overloading Supabase
        if i + check_chunk_size < len(rows_to_process):
            print("Waiting 2 seconds before checking next chunk...")
            time.sleep(2)
    
    print(f"Found {len(existing_ids)} existing contacts that will be skipped")
    
    # Filter out existing contacts
    rows_to_process = [row for row in rows_to_process if get_unique_identifier(row) not in existing_ids]
    print(f"Will classify and upload {len(rows_to_process)} new contacts")
    
    if not rows_to_process:
        print("No new contacts to process. Exiting.")
        return
    
    # Initialize tracking variables
    processed_count = 0
    upload_batch = []
    start_time = time.time()
    
    # Process contacts in OpenAI batches
    for i in range(0, len(rows_to_process), openai_batch_size):
        batch = rows_to_process[i:i + openai_batch_size]
        
        # Prepare batch of contacts for classification
        contact_data_batch = [prepare_contact_for_classification(contact) for contact in batch]
        
        # Classify batch through OpenAI
        print(f"Classifying batch of {len(batch)} contacts...")
        classifications = batch_classify_contacts(openai_client, contact_data_batch)
        
        # Update rows with classifications and prepare for Supabase
        for j, (row, classification) in enumerate(zip(batch, classifications)):
            # Add the classification to the row
            row['Taxonomy Classification'] = classification
            
            # Convert to Supabase format
            supabase_row = convert_row_to_supabase_format(row)
            
            # Add to the upload batch
            upload_batch.append(supabase_row)
            
            # Print progress
            processed_count += 1
            contact_name = f"{row.get('First Name', '')} {row.get('Last Name', '')}"
            print(f"Processed {processed_count}/{len(rows_to_process)}: {contact_name} -> {classification}")
            
            # If upload batch is full, upload to Supabase
            if len(upload_batch) >= supabase_batch_size:
                upload_success = False
                retries = 0
                max_retries = 3
                
                while not upload_success and retries < max_retries:
                    try:
                        result = supabase_client.table('contacts').insert(upload_batch).execute()
                        
                        # Check for errors
                        if hasattr(result, 'error') and result.error:
                            print(f"Error uploading batch to Supabase: {result.error}")
                            retries += 1
                            if retries >= max_retries:
                                print("Max retries reached. Continuing to next batch.")
                            else:
                                print(f"Retrying upload in 5 seconds (attempt {retries}/{max_retries})...")
                                time.sleep(5)
                        else:
                            upload_success = True
                            # Calculate progress and ETA
                            elapsed = time.time() - start_time
                            avg_time = elapsed / processed_count
                            percent_done = (processed_count / len(rows_to_process)) * 100
                            remaining_items = len(rows_to_process) - processed_count
                            eta_seconds = remaining_items * avg_time
                            eta_minutes = int(eta_seconds / 60)
                            eta_seconds = int(eta_seconds % 60)
                            
                            print(f"Uploaded batch of {len(upload_batch)} contacts to Supabase. "
                                  f"Progress: {processed_count}/{len(rows_to_process)} "
                                  f"({percent_done:.1f}%) - ETA: {eta_minutes}m {eta_seconds}s")
                    except Exception as e:
                        print(f"Error uploading to Supabase: {e}")
                        retries += 1
                        if retries >= max_retries:
                            print("Max retries reached. Continuing to next batch.")
                        else:
                            print(f"Retrying upload in 5 seconds (attempt {retries}/{max_retries})...")
                            time.sleep(5)
                
                # Clear the upload batch
                upload_batch = []
                
                # Add a delay to avoid rate limits
                time.sleep(0.5)
        
        # Add delay between OpenAI batches to respect rate limits
        if i + openai_batch_size < len(rows_to_process):
            print(f"Waiting 1 second before next batch...")
            time.sleep(1)
    
    # Upload any remaining contacts
    if upload_batch:
        upload_success = False
        retries = 0
        max_retries = 3
        
        while not upload_success and retries < max_retries:
            try:
                result = supabase_client.table('contacts').insert(upload_batch).execute()
                
                # Check for errors
                if hasattr(result, 'error') and result.error:
                    print(f"Error uploading final batch to Supabase: {result.error}")
                    retries += 1
                    if retries >= max_retries:
                        print("Max retries reached for final batch.")
                    else:
                        print(f"Retrying final upload in 5 seconds (attempt {retries}/{max_retries})...")
                        time.sleep(5)
                else:
                    upload_success = True
                    print(f"Uploaded final batch of {len(upload_batch)} contacts to Supabase.")
            except Exception as e:
                print(f"Error uploading final batch to Supabase: {e}")
                retries += 1
                if retries >= max_retries:
                    print("Max retries reached for final batch.")
                else:
                    print(f"Retrying final upload in 5 seconds (attempt {retries}/{max_retries})...")
                    time.sleep(5)

    elapsed = time.time() - start_time
    print(f"Processed {processed_count} contacts in {elapsed:.0f} seconds.")
    
    # Print completion statistics
    minutes = int(elapsed / 60)
    seconds = int(elapsed % 60)
    print(f"Processing completed. {processed_count} contacts classified and uploaded in {minutes}m {seconds}s.")

def main():
    parser = argparse.ArgumentParser(description="Process Bay Area Philanthropy leads and upload to Supabase")
    parser.add_argument("--input", type=str, required=True, help="Input CSV file path")
    parser.add_argument("--openai-batch", type=int, default=5, help="Number of contacts to classify in each OpenAI batch")
    parser.add_argument("--supabase-batch", type=int, default=20, help="Number of contacts to upload in each Supabase batch")
    parser.add_argument("--sample", type=int, help="Number of contacts to process (for testing)")
    parser.add_argument("--start", type=int, default=0, help="Starting index in the CSV (for resuming)")
    parser.add_argument("--check-chunk", type=int, default=50, help="Number of contacts to check for existence at once")
    
    args = parser.parse_args()
    
    try:
        print("Creating OpenAI client...")
        openai_client = create_openai_client()
        
        print("Creating Supabase client...")
        supabase_client = create_supabase_client()
        
        print(f"Starting batch processing from {args.input}...")
        process_bay_area_leads(
            args.input,
            openai_client,
            supabase_client,
            args.openai_batch,
            args.supabase_batch,
            args.sample,
            args.start,
            args.check_chunk
        )
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 