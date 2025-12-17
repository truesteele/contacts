#!/usr/bin/env python3
"""
Batch process contacts with OpenAI and upload to Supabase.
This script efficiently processes contacts in batches through OpenAI
and uploads the results directly to Supabase, skipping duplicates.
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

# Load environment variables
load_dotenv()

# Define our contact taxonomy with normalized keys for the schema
TAXONOMY_MAP = {
    "STRATEGIC_BUSINESS_PROSPECTS__CORPORATE_IMPACT_LEADERS": "Strategic Business Prospects: Corporate Impact Leaders",
    "STRATEGIC_BUSINESS_PROSPECTS__FOUNDATION_EXECUTIVES": "Strategic Business Prospects: Foundation Executives",
    "STRATEGIC_BUSINESS_PROSPECTS__NONPROFIT_EXECUTIVES": "Strategic Business Prospects: Nonprofit Executives",
    "STRATEGIC_BUSINESS_PROSPECTS__CORPORATE_PARTNERS": "Strategic Business Prospects: Corporate Partners",
    
    "KNOWLEDGE_NETWORK__AI_TECH_INNOVATORS": "Knowledge & Industry Network: AI/Tech Innovators",
    "KNOWLEDGE_NETWORK__SOCIAL_IMPACT_PRACTITIONERS": "Knowledge & Industry Network: Social Impact Practitioners",
    "KNOWLEDGE_NETWORK__ENVIRONMENTAL_CHAMPIONS": "Knowledge & Industry Network: Environmental Champions",
    "KNOWLEDGE_NETWORK__THOUGHT_LEADERS": "Knowledge & Industry Network: Thought Leaders",
    "KNOWLEDGE_NETWORK__PHILANTHROPY_PROFESSIONALS": "Knowledge & Industry Network: Philanthropy Professionals",
    
    "NEWSLETTER_AUDIENCE__SOCIAL_IMPACT_PROFESSIONALS": "Newsletter Audience: Social Impact Professionals",
    "NEWSLETTER_AUDIENCE__DEI_PRACTITIONERS": "Newsletter Audience: DEI Practitioners",
    "NEWSLETTER_AUDIENCE__POTENTIAL_SUBSCRIBERS": "Newsletter Audience: Potential Subscribers",
    
    "SUPPORT_NETWORK__INVESTORS_FUNDERS": "Support Network: Investors/Funders",
    "SUPPORT_NETWORK__MENTORS_ADVISORS": "Support Network: Mentors/Advisors",
    "SUPPORT_NETWORK__CONNECTORS": "Support Network: Connectors",
    "SUPPORT_NETWORK__FORMER_COLLEAGUES": "Support Network: Former Colleagues",
    
    "PERSONAL_NETWORK__FRIENDS_FAMILY": "Personal Network: Friends/Family",
    "PERSONAL_NETWORK__OUTDOORITHM_COMMUNITY": "Personal Network: Outdoorithm Community",
    
    "LOW_PRIORITY__OUT_OF_SCOPE": "Low Priority: Out of Scope",
    "LOW_PRIORITY__WEAK_CONNECTION": "Low Priority: Weak Connection"
}

# Extract the enum values (keys) for the schema
FLAT_TAXONOMY = list(TAXONOMY_MAP.keys())

def create_openai_client() -> OpenAI:
    """Create and return an OpenAI client."""
    api_key = os.environ.get("OPENAI_APIKEY")
    if not api_key:
        raise ValueError("OPENAI_APIKEY environment variable not set")
    return OpenAI(api_key=api_key)

def create_supabase_client():
    """Create and return a Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("Supabase URL and service key must be set in environment variables")
    
    return create_client(url, key)

def get_unique_identifier(contact: Dict[str, str]) -> str:
    """Generate a unique identifier for a contact, preferring LinkedIn URL or using name."""
    if contact.get('LinkedIn URL'):
        return contact['LinkedIn URL'].strip()
    else:
        # Create a unique ID from first and last name
        first_name = (contact.get('First Name') or '').strip()
        last_name = (contact.get('Last Name') or '').strip()
        
        # If we have a company, include it for uniqueness
        company = (contact.get('Company') or '').strip()
        if company:
            combined = f"{first_name} {last_name} {company}".strip().lower()
        else:
            combined = f"{first_name} {last_name}".strip().lower()
            
        if not combined:
            # Last resort: hash all values as a fingerprint
            all_values = ''.join([str(v) for v in contact.values() if v])
            return hashlib.md5(all_values.encode()).hexdigest()
            
        return combined

def check_existing_contacts(supabase, contacts, max_retries=3):
    """Check which contacts already exist in Supabase based on LinkedIn URL or names."""
    existing_ids = set()
    
    # Extract LinkedIn URLs for checking
    linkedin_urls = [c.get('LinkedIn URL') for c in contacts if c.get('LinkedIn URL')]
    
    # Process LinkedIn URLs in small batches to avoid URL length limits
    if linkedin_urls:
        # Process LinkedIn URLs in smaller batches to avoid query length issues
        batch_size = 10  # Reduced from 20 to avoid query length errors
        total_batches = (len(linkedin_urls) + batch_size - 1) // batch_size
        print(f"Checking {len(linkedin_urls)} LinkedIn URLs in {total_batches} batches...")
        
        for i in range(0, len(linkedin_urls), batch_size):
            batch_urls = linkedin_urls[i:i + batch_size]
            
            print(f"Checking LinkedIn URL batch {i//batch_size + 1} of {total_batches}...")
            
            # Check for existing LinkedIn URLs with retry logic
            retries = 0
            while retries < max_retries:
                try:
                    result = supabase.table('contacts').select('linkedin_url').in_('linkedin_url', batch_urls).execute()
                    for item in result.data:
                        if item.get('linkedin_url'):
                            existing_ids.add(item['linkedin_url'])
                    break  # Success, exit the retry loop
                except Exception as e:
                    retries += 1
                    print(f"Supabase connection error (attempt {retries}/{max_retries}): {e}")
                    if retries >= max_retries:
                        print(f"Max retries reached for batch {i//batch_size + 1}. Continuing to next batch.")
                    else:
                        print(f"Retrying in 5 seconds...")
                        time.sleep(5)
            
            # Add a small delay between batches
            time.sleep(0.5)
    
    # Extract name combinations for contacts without LinkedIn URLs
    name_combinations = []
    name_to_index = {}
    
    for i, contact in enumerate(contacts):
        if not contact.get('LinkedIn URL'):
            first_name = (contact.get('First Name') or '').strip()
            last_name = (contact.get('Last Name') or '').strip()
            if first_name and last_name:
                full_name = f"{first_name} {last_name}".lower()
                name_combinations.append({
                    'first_name': first_name.lower(),
                    'last_name': last_name.lower()
                })
                name_to_index[f"{first_name.lower()}:{last_name.lower()}"] = i
    
    if name_combinations:
        # Process name combinations in batches to avoid too many sequential queries
        batch_size = 50
        for i in range(0, len(name_combinations), batch_size):
            batch_combos = name_combinations[i:i + batch_size]
            
            print(f"Checking batch {i//batch_size + 1} of {(len(name_combinations) + batch_size - 1)//batch_size} name combinations...")
            
            # For each name combination in this batch, check if it exists
            for combo in batch_combos:
                retries = 0
                while retries < max_retries:
                    try:
                        result = supabase.table('contacts').select('first_name', 'last_name') \
                            .eq('first_name', combo['first_name']) \
                            .eq('last_name', combo['last_name']) \
                            .execute()
                        
                        if result.data:
                            key = f"{combo['first_name']}:{combo['last_name']}"
                            idx = name_to_index.get(key)
                            if idx is not None:
                                # Mark this contact as existing by its name combo
                                contact_key = get_unique_identifier(contacts[idx])
                                existing_ids.add(contact_key)
                        break  # Success, exit the retry loop
                    except Exception as e:
                        retries += 1
                        print(f"Supabase connection error (attempt {retries}/{max_retries}): {e}")
                        if retries >= max_retries:
                            print(f"Max retries reached for name check. Continuing to next name.")
                        else:
                            print(f"Retrying in 5 seconds...")
                            time.sleep(5)
            
            # Add a small delay between batches
            time.sleep(0.5)
    
    return existing_ids

def prepare_contact_for_classification(contact: Dict[str, str]) -> str:
    """Format contact data into a string for classification."""
    relevant_fields = [
        f"Name: {contact.get('First Name', '')} {contact.get('Last Name', '')}",
        f"Position: {contact.get('Position', '')}",
        f"Company: {contact.get('Company', '')}",
        f"Headline: {contact.get('Headline', '')}",
    ]
    
    # Add summary if it exists and isn't too long
    summary = contact.get('Summary', '')
    if summary and len(summary) > 0:
        # Truncate very long summaries
        if len(summary) > 500:
            summary = summary[:500] + "..."
        relevant_fields.append(f"Summary: {summary}")
    
    # Add experience if available
    experience = contact.get('Summary - Experience', '')
    if experience:
        # Truncate very long experience
        if len(experience) > 300:
            experience = experience[:300] + "..."
        relevant_fields.append(f"Experience: {experience}")
    
    # Include education
    education = []
    school = contact.get('School Name - Education', '')
    degree = contact.get('Degree - Education', '')
    field = contact.get('Field Of Study - Education', '')
    if school or degree or field:
        edu_str = f"Education: {school} {degree} {field}".strip()
        relevant_fields.append(edu_str)
    
    # Include volunteering if available
    volunteering = contact.get('Summary - Volunteering', '')
    volunteering_role = contact.get('Role - Volunteering', '')
    volunteering_company = contact.get('Company Name - Volunteering', '')
    if volunteering or volunteering_role or volunteering_company:
        vol_info = f"Volunteering: {volunteering_role} at {volunteering_company}".strip()
        relevant_fields.append(vol_info)
        if volunteering and len(volunteering) > 0:
            vol_summary = volunteering
            if len(vol_summary) > 200:
                vol_summary = vol_summary[:200] + "..."
            relevant_fields.append(f"Volunteering Summary: {vol_summary}")
    
    return "\n".join(relevant_fields)

def batch_classify_contacts(client: OpenAI, contacts_data: List[str]) -> List[str]:
    """Use OpenAI with structured output to classify multiple contacts at once."""
    
    if not contacts_data:
        return []
    
    # Format enum values for system prompt
    enum_values = "\n".join([f"- {key}" for key in FLAT_TAXONOMY])
    
    system_prompt = f"""You are an AI assistant categorizing professional contacts for True Steele's business.
True Steele focuses on:
• Fractional Chief Impact Officer & strategic advisory (social impact + ROI)
• Outdoorithm nonprofit for outdoor equity
• A social impact newsletter ("The Long Arc")
• Startup ideas (Kindora, Proximity AI Lab) in philanthropic tech

I'm going to give you multiple contacts to classify. For each contact, you must assign exactly one category from the following list:

{enum_values}

Return your response as a JSON object with a single property called "classifications" that contains an array of objects.
Each object in the array should have a single property "category" corresponding to exactly one contact in the order provided.

Example: 
{{
  "classifications": [
    {{"category": "STRATEGIC_BUSINESS_PROSPECTS__CORPORATE_IMPACT_LEADERS"}},
    {{"category": "KNOWLEDGE_NETWORK__THOUGHT_LEADERS"}},
    ...
  ]
}}

If multiple categories apply to a contact, choose the single best fit.
If you are unsure, choose LOW_PRIORITY__OUT_OF_SCOPE.
"""
    
    # Prepare the user prompt with multiple contacts
    contacts_formatted = []
    for i, contact_data in enumerate(contacts_data):
        contacts_formatted.append(f"CONTACT #{i+1}:\n{contact_data}\n---")
    
    user_prompt = "Here are the contacts to classify:\n\n" + "\n\n".join(contacts_formatted)
    
    try:
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={
                "type": "json_object"
            }
        )
        
        # Parse the JSON response
        result_obj = json.loads(response.choices[0].message.content)
        
        # Extract the array from the classifications property
        result = result_obj.get("classifications", [])
        
        # Ensure we got an array of results
        if not isinstance(result, list):
            print(f"Warning: Expected array in 'classifications', got: {type(result)}")
            # Return fallback classifications
            return ["Low Priority: Out of Scope"] * len(contacts_data)
        
        # Map the enum keys to display categories
        display_categories = []
        for i, item in enumerate(result):
            if isinstance(item, dict) and "category" in item:
                category_key = item["category"]
                display_category = TAXONOMY_MAP.get(category_key)
                
                if not display_category:
                    print(f"Warning: Unexpected enum or parsing error for contact {i+1}: {category_key}")
                    display_category = "Low Priority: Out of Scope"  # Default fallback
                
                display_categories.append(display_category)
            else:
                print(f"Warning: Invalid format for contact {i+1}: {item}")
                display_categories.append("Low Priority: Out of Scope")  # Default fallback
        
        # Handle case where we get fewer results than expected
        if len(display_categories) < len(contacts_data):
            print(f"Warning: Got fewer results ({len(display_categories)}) than contacts ({len(contacts_data)})")
            display_categories.extend(["Low Priority: Out of Scope"] * (len(contacts_data) - len(display_categories)))
        
        return display_categories
    
    except Exception as e:
        print(f"Error batch classifying contacts: {e}")
        # Return fallback classifications
        return ["Low Priority: Out of Scope"] * len(contacts_data)

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

def process_contacts(
    input_file: str,
    openai_client: OpenAI,
    supabase_client: Any,
    openai_batch_size: int = 5,
    supabase_batch_size: int = 20,
    sample_size: Optional[int] = None,
    start_index: int = 0,
    check_chunk_size: int = 500
) -> None:
    """Process CSV file, classify contacts in batches, and upload to Supabase.
    
    Args:
        input_file: Path to the CSV file containing contacts
        openai_client: OpenAI client for classification
        supabase_client: Supabase client for database operations
        openai_batch_size: Number of contacts to classify in each OpenAI API call
        supabase_batch_size: Number of contacts to upload in each Supabase batch
        sample_size: Optional number of contacts to process (for testing)
        start_index: Starting index in the CSV (for resuming)
        check_chunk_size: Number of contacts to check for existence at once
    """
    
    # Read the input CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
    
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
    parser = argparse.ArgumentParser(description="Batch classify contacts and upload to Supabase")
    parser.add_argument("--input", type=str, required=True, help="Input CSV file path")
    parser.add_argument("--openai-batch", type=int, default=5, help="Number of contacts to classify in each OpenAI batch")
    parser.add_argument("--supabase-batch", type=int, default=20, help="Number of contacts to upload in each Supabase batch")
    parser.add_argument("--sample", type=int, help="Number of contacts to process (for testing)")
    parser.add_argument("--start", type=int, default=0, help="Starting index in the CSV (for resuming)")
    parser.add_argument("--check-chunk", type=int, default=500, help="Number of contacts to check for existence at once")
    
    args = parser.parse_args()
    
    try:
        print("Creating OpenAI client...")
        openai_client = create_openai_client()
        
        print("Creating Supabase client...")
        supabase_client = create_supabase_client()
        
        print(f"Starting batch processing from {args.input}...")
        process_contacts(
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