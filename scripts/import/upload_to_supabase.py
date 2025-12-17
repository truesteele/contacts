#!/usr/bin/env python3
"""
Upload classified contacts to Supabase database.
This script processes the input CSV file, classifies contacts using OpenAI,
and uploads the results to Supabase instead of writing to a CSV file.
"""

import csv
import json
import os
import time
from openai import OpenAI
from typing import Dict, List, Any, Optional
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

# Define the JSON schema for structured output
CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": FLAT_TAXONOMY,
            "description": "The single best-fit taxonomy label for this contact"
        }
    },
    "required": ["category"],
    "additionalProperties": False
}

def create_openai_client() -> OpenAI:
    """Create and return an OpenAI client."""
    # Try different variations of the API key environment variable
    api_key = os.environ.get("OPENAI_APIKEY") or os.environ.get("OPENAI_API_KEY")
    
    # If API key not found in environment, try to read directly from .env file
    if not api_key:
        try:
            print("Attempting to read API key directly from .env file...")
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('OPENAI_APIKEY='):
                        api_key = line.strip().split('=', 1)[1].strip()
                        print("Found API key in .env file")
                        break
        except Exception as e:
            print(f"Error reading .env file: {e}")
    
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables or .env file. Please set OPENAI_APIKEY.")
    
    # Remove any quotes that might be in the API key
    api_key = api_key.strip('\'"')
    
    return OpenAI(api_key=api_key)

def create_supabase_client():
    """Create and return a Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("Supabase URL and service key must be set in environment variables")
    
    return create_client(url, key)

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

def classify_contact(client: OpenAI, contact_data: str) -> str:
    """Use OpenAI with structured output to classify the contact based on the taxonomy."""
    
    # Format enum values for system prompt
    enum_values = "\n".join([f"- {key}" for key in FLAT_TAXONOMY])
    
    system_prompt = f"""You are an AI assistant categorizing professional contacts for True Steele's business.
True Steele focuses on:
• Fractional Chief Impact Officer & strategic advisory (social impact + ROI)
• Outdoorithm nonprofit for outdoor equity
• A social impact newsletter ("The Long Arc")
• Startup ideas (Kindora, Proximity AI Lab) in philanthropic tech

You must return valid JSON that matches the schema with exactly one property: "category".
The "category" value MUST be one of these exact enum values:

{enum_values}

No extra keys or explanations. Only pure JSON.
If multiple categories apply, choose the single best fit.
If you are unsure, choose LOW_PRIORITY__OUT_OF_SCOPE.
"""
    
    user_prompt = f"""Contact info:

{contact_data}

Return only valid JSON with a single property "category". The value for category must be one of the enum values specified.
Example: {{"category": "STRATEGIC_BUSINESS_PROSPECTS__CORPORATE_IMPACT_LEADERS"}}
"""
    
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
        result = json.loads(response.choices[0].message.content)
        category_key = result.get("category")
        
        # Convert the enum key to the display format
        display_category = TAXONOMY_MAP.get(category_key)
        
        if not display_category:
            print(f"Warning: Unexpected enum or parsing error: {category_key}")
            return "Low Priority: Out of Scope"  # Default fallback
        
        return display_category
    
    except Exception as e:
        print(f"Error classifying contact: {e}")
        return "Low Priority: Out of Scope"  # Default fallback

def convert_row_to_supabase_format(row: Dict[str, str], fieldnames: List[str]) -> Dict[str, str]:
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
    for field in fieldnames:
        if field in column_mapping:
            db_column = column_mapping[field]
            supabase_row[db_column] = row.get(field, '')
    
    return supabase_row

def process_contacts(
    input_file: str,
    openai_client: OpenAI,
    supabase_client: Any,
    sample_size: Optional[int] = None,
    start_index: int = 0,
    batch_size: int = 10
) -> None:
    """Process the CSV file, classify contacts, and upload to Supabase."""
    
    # Read the input CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
    
    # Determine which rows to process
    if sample_size:
        end_index = min(start_index + sample_size, len(all_rows))
        rows_to_process = all_rows[start_index:end_index]
    else:
        rows_to_process = all_rows[start_index:]
    
    # Get fieldnames for column mapping
    fieldnames = reader.fieldnames + ['Taxonomy Classification']
    
    # Keep track of processed contacts for batch insertion
    batch = []
    processed_count = 0
    
    # Process each contact
    for i, row in enumerate(rows_to_process):
        try:
            # Prepare and classify the contact
            contact_data = prepare_contact_for_classification(row)
            classification = classify_contact(openai_client, contact_data)
            
            # Add the classification to the row
            row['Taxonomy Classification'] = classification
            
            # Convert to Supabase format
            supabase_row = convert_row_to_supabase_format(row, fieldnames)
            
            # Add to the batch
            batch.append(supabase_row)
            
            # Print progress
            print(f"Processed {i+1}/{len(rows_to_process)}: {row.get('First Name', '')} {row.get('Last Name', '')} -> {classification}")
            
            # If we have reached the batch size, upload to Supabase
            if len(batch) >= batch_size:
                result = supabase_client.table('contacts').insert(batch).execute()
                
                # Check for errors
                if hasattr(result, 'error') and result.error:
                    print(f"Error uploading batch to Supabase: {result.error}")
                else:
                    processed_count += len(batch)
                    print(f"Uploaded batch of {len(batch)} contacts to Supabase. Total uploaded: {processed_count}")
                
                # Clear the batch
                batch = []
                
                # Sleep to avoid rate limits
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Error processing contact {i+1}: {e}")
    
    # Upload any remaining contacts in the batch
    if batch:
        try:
            result = supabase_client.table('contacts').insert(batch).execute()
            
            # Check for errors
            if hasattr(result, 'error') and result.error:
                print(f"Error uploading final batch to Supabase: {result.error}")
            else:
                processed_count += len(batch)
                print(f"Uploaded final batch of {len(batch)} contacts to Supabase. Total uploaded: {processed_count}")
        except Exception as e:
            print(f"Error uploading final batch: {e}")
    
    print(f"Completed processing. Total {processed_count} contacts uploaded to Supabase.")

def main():
    parser = argparse.ArgumentParser(description="Classify contacts and upload to Supabase")
    parser.add_argument("--input", type=str, required=True, help="Input CSV file path")
    parser.add_argument("--sample", type=int, help="Number of contacts to process (for testing)")
    parser.add_argument("--start", type=int, default=0, help="Starting index in the CSV (for resuming)")
    parser.add_argument("--batch", type=int, default=10, help="Number of contacts to upload in each batch")
    
    args = parser.parse_args()
    
    print("Creating OpenAI client...")
    openai_client = create_openai_client()
    
    print("Creating Supabase client...")
    supabase_client = create_supabase_client()
    
    print("Starting to process contacts...")
    process_contacts(
        args.input, 
        openai_client, 
        supabase_client, 
        args.sample, 
        args.start,
        args.batch
    )

if __name__ == "__main__":
    main() 