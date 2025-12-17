#!/usr/bin/env python3
"""
Domain Enrichment Script

This script finds contacts in Supabase where company_experience is populated
but company_domain_experience is empty, and uses Perplexity API to find
the company domain and OpenAI to normalize it.
"""

import os
import time
import json
import argparse
from typing import Dict, List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import requests
from supabase import create_client

# Load environment variables
load_dotenv()

# API keys and configuration
PERPLEXITY_APIKEY = os.environ.get("PERPLEXITY_APIKEY")
PERPLEXITY_MODEL = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")
OPENAI_APIKEY = os.environ.get("OPENAI_APIKEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# Constants
NO_DOMAIN_MARKER = "NO_DOMAIN_FOUND"  # Special marker for when a domain wasn't found

# Rate limit configurations
# Perplexity API has a limit of 50 requests per minute for most models
# OpenAI GPT-4o has a limit of 500 requests per minute and 30,000 tokens per minute for Tier 1
# These values represent the minimum delay needed to stay within the rate limits
PERPLEXITY_MIN_DELAY = 60.0 / 40  # 1.5 sec delay = 40 RPM (safe margin below the 50 RPM limit)
OPENAI_MIN_DELAY = 60.0 / 400      # 0.15 sec delay = 400 RPM (safe margin below the 500 RPM limit)
DEFAULT_DELAY = max(PERPLEXITY_MIN_DELAY, OPENAI_MIN_DELAY)  # Use the more restrictive delay

# Check required environment variables
if not all([PERPLEXITY_APIKEY, OPENAI_APIKEY, SUPABASE_URL, SUPABASE_SERVICE_KEY]):
    missing = []
    if not PERPLEXITY_APIKEY:
        missing.append("PERPLEXITY_APIKEY")
    if not OPENAI_APIKEY:
        missing.append("OPENAI_APIKEY")
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_SERVICE_KEY:
        missing.append("SUPABASE_SERVICE_KEY")
    
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

class DomainInfo(BaseModel):
    """A model for structured output from OpenAI."""
    domain: str

def create_supabase_client():
    """Create and return a Supabase client."""
    try:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as e:
        print(f"Error creating Supabase client: {e}")
        raise

def create_openai_client():
    """Create and return an OpenAI client."""
    try:
        return OpenAI(api_key=OPENAI_APIKEY)
    except Exception as e:
        print(f"Error creating OpenAI client: {e}")
        raise

def find_contacts_missing_domain(supabase, batch_size=100, max_records=None, offset=0, include_previously_not_found=False):
    """
    Find contacts where company_experience is populated but company_domain_experience is empty.
    
    Args:
        supabase: Supabase client
        batch_size: Number of records to fetch at once
        max_records: Maximum number of records to process (for testing)
        offset: Number of records to skip (for pagination)
        include_previously_not_found: Whether to include contacts marked as having no domain
        
    Returns:
        List of contact records
    """
    try:
        # Calculate range boundaries for pagination
        range_start = offset
        range_end = offset + (max_records if max_records else batch_size) - 1
        
        print(f"Querying contacts from index {range_start} to {range_end}")
        
        # Build the query
        query = supabase.table('contacts').select('id,company_experience,company_domain_experience')
        
        # Apply range for pagination
        query = query.range(range_start, range_end)
            
        # Execute the query
        result = query.execute()
        
        # For debugging only
        print(f"Total contacts retrieved from database: {len(result.data)}")
        
        # Filter for contacts with company_experience but no company_domain_experience or NO_DOMAIN_MARKER
        filtered_contacts = []
        for contact in result.data:
            company_exp = contact.get('company_experience')
            domain_exp = contact.get('company_domain_experience')
            
            # Process this contact if:
            # 1. It has company_experience AND
            # 2. EITHER:
            #    a. domain_experience is empty OR
            #    b. domain_experience is NO_DOMAIN_MARKER and include_previously_not_found is True
            if company_exp and company_exp.strip():
                if (domain_exp is None or domain_exp == ''):
                    filtered_contacts.append(contact)
                elif domain_exp == NO_DOMAIN_MARKER and include_previously_not_found:
                    filtered_contacts.append(contact)
                    print(f"Including previously not found domain for company: {company_exp}")
        
        print(f"Contacts with company but no domain: {len(filtered_contacts)}")
        return filtered_contacts
        
    except Exception as e:
        print(f"Error finding contacts missing domain: {e}")
        import traceback
        traceback.print_exc()
        return []

def find_existing_domain_for_company(supabase, company_name):
    """
    Check if there's already a domain for the same company in the database.
    
    Args:
        supabase: Supabase client
        company_name: Name of the company to search for
        
    Returns:
        Domain if found, None otherwise
    """
    try:
        result = supabase.table('contacts')\
            .select('company_domain_experience')\
            .eq('company_experience', company_name)\
            .not_.is_('company_domain_experience', 'null')\
            .not_.eq('company_domain_experience', '')\
            .not_.eq('company_domain_experience', NO_DOMAIN_MARKER)\
            .limit(1)\
            .execute()
        
        if result.data and len(result.data) > 0 and result.data[0].get('company_domain_experience'):
            return result.data[0]['company_domain_experience']
        return None
    except Exception as e:
        print(f"Error finding existing domain for company: {e}")
        return None

def search_company_domain_with_perplexity(company_name):
    """
    Use Perplexity API to search for a company's domain.
    
    Args:
        company_name: Name of the company to search for
        
    Returns:
        Perplexity API response as text
    """
    try:
        # Perplexity API endpoint
        url = "https://api.perplexity.ai/chat/completions"
        
        # Headers with API key
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_APIKEY}",
            "Content-Type": "application/json"
        }
        
        # Create prompt for Perplexity - updated to first determine if this is an actual company
        prompt = f"""
First, determine if '{company_name}' is an actual company/organization name, or if it's just a description of someone's role or position (like "Independent Consultant", "Freelance Writer", etc.).

If it is NOT an actual company but rather a description of someone's role:
- Respond with: "NOT_A_COMPANY: [brief explanation]"

If it IS an actual company/organization:
- What is its official website domain? Return only the domain name in the format example.com (no http or www prefixes).
- If you can't find a reliable domain, say 'No domain found'
"""
        
        # Data payload
        data = {
            "model": PERPLEXITY_MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that provides accurate company domain information. Be precise and concise. Be careful to distinguish between actual companies and descriptive titles."},
                {"role": "user", "content": prompt}
            ]
        }
        
        # Make the API call
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Extract the response content
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            return "No domain found"
    except Exception as e:
        print(f"Error searching company domain with Perplexity: {e}")
        return f"Error: {str(e)}"

def normalize_domain_with_openai(openai_client, perplexity_response, company_name):
    """
    Use OpenAI to normalize the domain from Perplexity's response.
    
    Args:
        openai_client: OpenAI client
        perplexity_response: Response from Perplexity API
        company_name: Name of the company for context
        
    Returns:
        Normalized domain or None if not found
    """
    try:
        # Check if Perplexity identified this as not being a company
        if perplexity_response.startswith("NOT_A_COMPANY:"):
            print(f"  ℹ️ Perplexity identified this as not a company: {perplexity_response}")
            return None
            
        # Create a system prompt for OpenAI - ensure "json" is mentioned
        system_prompt = """
        You are a domain extraction specialist. Your task is to extract and normalize the company domain 
        from the provided text. 
        
        IMPORTANT: You must respond with valid JSON format containing only a "domain" field.
        
        The domain should be in the format "example.com" - no http://, https://, or www. 
        If multiple domains are mentioned, select the most official one.
        
        If the text indicates this is not a company but a role description (like "Freelance Writer"), 
        or if no valid domain is found, return null as the domain value.
        
        Example JSON response: {"domain": "example.com"}
        Or if no domain found: {"domain": null}
        """
        
        # Create a user prompt for OpenAI
        user_prompt = f"""
        Text to analyze: "{company_name}"
        Perplexity response: {perplexity_response}
        
        Extract the normalized domain and return ONLY a JSON object with a "domain" field.
        If the text indicates this is not an actual company but rather a descriptive title or role, return null.
        
        Example JSON response: {{"domain": "example.com"}}
        Or if no domain is found or this is not a company: {{"domain": null}}
        """
        
        # Make the API call with JSON response format
        completion = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # Parse the response
        response_text = completion.choices[0].message.content
        print(f"  OpenAI response: {response_text}")
        response_json = json.loads(response_text)
        
        # Extract domain from response
        domain = response_json.get("domain")
        
        # Return either the domain or None
        if domain and domain.lower() != "null" and domain != "No domain found":
            return domain
        return None
    except Exception as e:
        print(f"Error normalizing domain with OpenAI: {e}")
        import traceback
        traceback.print_exc()
        return None

def update_contact_domain(supabase, contact_id, domain, max_retries=3):
    """
    Update the company_domain_experience field for a contact in Supabase.
    
    Args:
        supabase: Supabase client
        contact_id: ID of the contact to update
        domain: Domain to set
        max_retries: Maximum number of retries for connection issues
        
    Returns:
        True if successful, False otherwise
    """
    retries = 0
    while retries < max_retries:
        try:
            result = supabase.table('contacts')\
                .update({"company_domain_experience": domain})\
                .eq('id', contact_id)\
                .execute()
            
            return True
        except Exception as e:
            retries += 1
            print(f"Error updating contact domain (attempt {retries}/{max_retries}): {e}")
            if retries >= max_retries:
                print(f"Max retries reached for contact ID {contact_id}")
                return False
            time.sleep(5)  # Wait before retrying

def process_contacts(supabase, openai_client, batch_size=10, max_records=None, delay=DEFAULT_DELAY, offset=0, include_previously_not_found=False):
    """
    Process contacts missing domains, find domains, and update Supabase.
    
    Args:
        supabase: Supabase client
        openai_client: OpenAI client
        batch_size: Number of records to process at once
        max_records: Maximum number of records to process (for testing)
        delay: Delay between API calls in seconds (default optimized for API rate limits)
        offset: Number of records to skip (for pagination)
        include_previously_not_found: Whether to include contacts marked as having no domain
        
    Returns:
        Statistics about the processing
    """
    stats = {
        "processed": 0,
        "updated": 0,
        "not_found": 0,
        "not_a_company": 0,  # New stat for tracking non-company entries
        "errors": 0,
        "cached": 0,  # Stat for domains found in our database
        "previously_not_found": 0,  # Stat for contacts previously marked as having no domain
        "start_time": time.time()
    }
    
    # Find contacts missing domains
    try:
        import traceback
        contacts = find_contacts_missing_domain(
            supabase, 
            batch_size=batch_size, 
            max_records=max_records, 
            offset=offset,
            include_previously_not_found=include_previously_not_found
        )
    except Exception as e:
        print(f"Detailed error in find_contacts_missing_domain:")
        traceback.print_exc()
        contacts = []
    
    total_contacts = len(contacts)
    
    print(f"Found {total_contacts} contacts with missing domains")
    
    # Process each contact
    for i, contact in enumerate(contacts):
        contact_id = contact['id']
        company_name = contact['company_experience']
        
        print(f"Processing {i+1}/{total_contacts}: '{company_name}'")
        
        # First, check if we already have a domain for this company in our database
        existing_domain = find_existing_domain_for_company(supabase, company_name)
        
        if existing_domain:
            print(f"  🔍 Found existing domain in database: {existing_domain}")
            # Update contact with the domain we already have
            if update_contact_domain(supabase, contact_id, existing_domain):
                stats["updated"] += 1
                stats["cached"] += 1  # Count as both updated and cached
                print(f"  ✅ Updated contact ID {contact_id} using cached domain")
            else:
                stats["errors"] += 1
                print(f"  ❌ Failed to update contact ID {contact_id}")
        else:
            # No existing domain found, proceed with API calls
            # Search for company domain with Perplexity
            perplexity_response = search_company_domain_with_perplexity(company_name)
            print(f"  Perplexity response: {perplexity_response}")
            
            # Small delay to avoid rate limits
            time.sleep(delay)
            
            # Normalize domain with OpenAI
            domain = normalize_domain_with_openai(openai_client, perplexity_response, company_name)
            
            if domain:
                print(f"  Normalized domain: {domain}")
                
                # Update contact in Supabase
                if update_contact_domain(supabase, contact_id, domain):
                    stats["updated"] += 1
                    print(f"  ✅ Updated contact ID {contact_id}")
                else:
                    stats["errors"] += 1
                    print(f"  ❌ Failed to update contact ID {contact_id}")
            else:
                # Check if this was identified as not a company
                if perplexity_response.startswith("NOT_A_COMPANY:"):
                    stats["not_a_company"] += 1
                    print(f"  ⚠️ '{company_name}' identified as not a company but a role/title")
                else:
                    stats["not_found"] += 1
                    print(f"  ⚠️ No valid domain found for '{company_name}'")
                
                # Mark this contact as having no domain by setting our special marker
                if update_contact_domain(supabase, contact_id, NO_DOMAIN_MARKER):
                    print(f"  ✅ Marked contact ID {contact_id} as having no domain")
                else:
                    stats["errors"] += 1
                    print(f"  ❌ Failed to mark contact ID {contact_id}")
        
        stats["processed"] += 1
        
        # Calculate and display progress
        elapsed = time.time() - stats["start_time"]
        avg_time = elapsed / stats["processed"]
        percent_done = (stats["processed"] / total_contacts) * 100
        remaining = total_contacts - stats["processed"]
        eta_seconds = remaining * avg_time
        eta_minutes = int(eta_seconds / 60)
        eta_seconds = int(eta_seconds % 60)
        
        print(f"  Progress: {stats['processed']}/{total_contacts} ({percent_done:.1f}%) - ETA: {eta_minutes}m {eta_seconds}s")
        print("  ---------------------------------")
        
        # Small delay to avoid rate limits
        time.sleep(delay)
    
    # Calculate total elapsed time
    stats["total_elapsed"] = time.time() - stats["start_time"]
    stats["total_minutes"] = stats["total_elapsed"] / 60
    
    return stats

def count_contacts_with_no_domain_marker(supabase):
    """
    Count contacts that have been marked with NO_DOMAIN_MARKER.
    
    Args:
        supabase: Supabase client
        
    Returns:
        Number of contacts with NO_DOMAIN_MARKER
    """
    try:
        result = supabase.table('contacts')\
            .select('id')\
            .eq('company_domain_experience', NO_DOMAIN_MARKER)\
            .execute()
        
        count = len(result.data) if result.data else 0
        return count
    except Exception as e:
        print(f"Error counting contacts with no domain marker: {e}")
        return 0

def process_all_contacts(supabase, openai_client, batch_size=100, delay=DEFAULT_DELAY, include_previously_not_found=False):
    """
    Process all contacts in the database using pagination.
    
    Args:
        supabase: Supabase client
        openai_client: OpenAI client
        batch_size: Number of records to fetch in each batch
        delay: Delay between API calls in seconds (default optimized for API rate limits)
        include_previously_not_found: Whether to include contacts previously marked as having no domain
        
    Returns:
        Combined statistics about the processing
    """
    # Initialize combined stats
    combined_stats = {
        "processed": 0,
        "updated": 0,
        "not_found": 0,
        "not_a_company": 0,  # New stat for tracking non-company entries
        "errors": 0,
        "cached": 0,
        "previously_not_found": 0,
        "start_time": time.time()
    }
    
    # Get total count of contacts for progress tracking
    try:
        count_result = supabase.table('contacts').select('id', count='exact').execute()
        total_contacts = count_result.count if hasattr(count_result, 'count') else 1000  # Fallback if count not available
        print(f"Total contacts in database: {total_contacts}")
    except Exception as e:
        print(f"Error getting total count, using estimate: {e}")
        total_contacts = 3000  # Estimate if we can't get an exact count
    
    # Process contacts in batches with pagination
    offset = 0
    batch_num = 1
    
    # Continue until we've processed all contacts in the database
    while offset < total_contacts:
        print(f"\n--- Processing batch {batch_num} (offset: {offset}) ---\n")
        
        # Process current batch
        batch_stats = process_contacts(
            supabase,
            openai_client,
            batch_size=batch_size,
            max_records=None,  # Process all records in this batch
            delay=delay,
            offset=offset,
            include_previously_not_found=include_previously_not_found
        )
        
        # Update combined stats
        for key in ["processed", "updated", "not_found", "not_a_company", "errors", "cached", "previously_not_found"]:
            combined_stats[key] += batch_stats.get(key, 0)
        
        # Move to next batch regardless of whether any contacts were processed
        offset += batch_size
        batch_num += 1
        
        # Print overall progress
        progress_percent = min(100, (offset / total_contacts) * 100)
        print(f"Overall progress: Processed {offset}/{total_contacts} records ({progress_percent:.1f}% of database)")
        print(f"Found {combined_stats['updated']} domains so far ({combined_stats['cached']} from cache, {combined_stats['not_found']} not found, {combined_stats['not_a_company']} not companies)")
        
        # If we've checked all records or more (e.g., if the count was an underestimate), exit
        if offset >= total_contacts:
            print(f"Completed checking all {total_contacts} records in the database.")
    
    # Calculate total elapsed time
    combined_stats["total_elapsed"] = time.time() - combined_stats["start_time"]
    combined_stats["total_minutes"] = combined_stats["total_elapsed"] / 60
    
    return combined_stats

def main():
    """Main function to run the domain enrichment process."""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Domain Enrichment Script')
        parser.add_argument('--batch-size', type=int, default=1000, help='Number of contacts to process in one batch')
        parser.add_argument('--max-records', type=int, default=None, help='Maximum number of records to process (for testing)')
        parser.add_argument('--delay', type=float, default=DEFAULT_DELAY, help=f'Delay between API calls in seconds (default: {DEFAULT_DELAY})')
        parser.add_argument('--offset', type=int, default=0, help='Number of records to skip (for pagination)')
        parser.add_argument('--include-previously-not-found', action='store_true', help='Include contacts previously marked as having no domain')
        parser.add_argument('--single-batch', action='store_true', help='Process only a single batch instead of all contacts')
        args = parser.parse_args()
        
        print("Domain Enrichment Script")
        print("-----------------------")
        print(f"Perplexity Model: {PERPLEXITY_MODEL}")
        print(f"OpenAI Model: {OPENAI_MODEL}")
        print(f"Batch Size: {args.batch_size}")
        print(f"Max Records: {args.max_records if args.max_records else 'No limit'}")
        print(f"Offset: {args.offset}")
        print(f"Delay: {args.delay} seconds")
        print(f"  (Perplexity min delay: {PERPLEXITY_MIN_DELAY:.2f}s, OpenAI min delay: {OPENAI_MIN_DELAY:.2f}s)")
        print(f"Include Previously Not Found: {args.include_previously_not_found}")
        print(f"Processing Mode: {'Single Batch' if args.single_batch else 'All Contacts'}")
        print("-----------------------")
        
        # Create clients
        print("Creating Supabase client...")
        supabase = create_supabase_client()
        
        # Debug: Print Supabase client version
        import pkg_resources
        try:
            supabase_version = pkg_resources.get_distribution("supabase").version
            print(f"Supabase client version: {supabase_version}")
        except Exception as e:
            print(f"Could not determine Supabase version: {e}")
        
        # Debug: Try a simple query to test Supabase connection
        print("Testing Supabase connection with a simple query...")
        try:
            # Try a simple query to the contacts table
            result = supabase.table('contacts').select('id').limit(1).execute()
            print(f"Simple query result: {result.data}")
            
            # Count contacts with NO_DOMAIN_MARKER
            no_domain_count = count_contacts_with_no_domain_marker(supabase)
            print(f"Contacts marked as having no domain: {no_domain_count}")
        except Exception as e:
            print(f"Error with simple Supabase query: {e}")
            import traceback
            traceback.print_exc()
        
        print("Creating OpenAI client...")
        openai_client = create_openai_client()
        
        # Process contacts
        print("Starting domain enrichment process...")
        
        if args.single_batch:
            # Process a single batch (legacy mode)
            stats = process_contacts(
                supabase,
                openai_client,
                batch_size=args.batch_size,
                max_records=args.max_records,
                delay=args.delay,
                offset=args.offset,
                include_previously_not_found=args.include_previously_not_found
            )
        else:
            # Process all contacts with pagination
            stats = process_all_contacts(
                supabase,
                openai_client,
                batch_size=args.batch_size,
                delay=args.delay,
                include_previously_not_found=args.include_previously_not_found
            )
        
        # Print statistics
        print("\nDomain Enrichment Complete")
        print("--------------------------")
        print(f"Contacts processed: {stats['processed']}")
        print(f"Domains updated: {stats['updated']}")
        print(f"Domains cached: {stats['cached']}")
        print(f"Domains not found: {stats['not_found']}")
        print(f"Not companies but roles/titles: {stats.get('not_a_company', 0)}")
        print(f"Errors: {stats['errors']}")
        print(f"Total time: {stats['total_minutes']:.2f} minutes")
        print("--------------------------")
    except Exception as e:
        print(f"An error occurred in the main function: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 