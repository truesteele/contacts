#!/usr/bin/env python3
"""
MailerLite Group Setup Script

This script creates groups in MailerLite to match the taxonomy categories
used in the Supabase contact database. It's typically run once before
starting the sync process.
"""

import os
import time
import requests
import argparse
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# MailerLite API configuration
MAILERLITE_API_KEY = os.getenv("MAILERLITE_API_KEY")
MAILERLITE_BASE_URL = os.getenv("MAILERLITE_API_URL", "https://connect.mailerlite.com/api")
MAILERLITE_HEADERS = {
    "Authorization": f"Bearer {MAILERLITE_API_KEY}",
    "Content-Type": "application/json"
}

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Default taxonomy categories
DEFAULT_TAXONOMY_CATEGORIES = [
    "Strategic Business Prospects",
    "Knowledge & Industry Network",
    "Newsletter Audience",
    "Support Network",
    "Personal Network",
    "Low Priority"
]

# Sub-categories for more detailed grouping
SUBCATEGORIES = {
    "Strategic Business Prospects": [
        "Corporate Impact Leaders",
        "Foundation Executives", 
        "Nonprofit Executives",
        "Corporate Partners"
    ],
    "Knowledge & Industry Network": [
        "AI/Tech Innovators",
        "Social Impact Practitioners",
        "Environmental Champions",
        "Thought Leaders",
        "Philanthropy Professionals"
    ],
    "Newsletter Audience": [
        "Social Impact Professionals",
        "DEI Practitioners",
        "Potential Subscribers"
    ],
    "Support Network": [
        "Investors/Funders",
        "Mentors/Advisors",
        "Connectors",
        "Former Colleagues"
    ],
    "Personal Network": [
        "Friends/Family",
        "Outdoorithm Community"
    ],
    "Low Priority": [
        "Out of Scope",
        "Weak Connection"
    ]
}


def fetch_existing_groups():
    """
    Fetch all existing groups from MailerLite.
    
    Returns:
        dict: Mapping of group names to their IDs
    """
    groups = {}
    page = 1
    limit = 100
    
    while True:
        response = requests.get(
            f"{MAILERLITE_BASE_URL}/groups",
            headers=MAILERLITE_HEADERS,
            params={"page": page, "limit": limit}
        )
        
        if response.status_code != 200:
            print(f"Error fetching groups: {response.text}")
            return groups
        
        data = response.json()
        
        for group in data.get("data", []):
            groups[group["name"]] = group["id"]
        
        # Check if there are more pages
        if page >= data.get("meta", {}).get("last_page", 1):
            break
        
        page += 1
    
    return groups


def create_group(name):
    """
    Create a new group in MailerLite.
    
    Args:
        name: Name of the group to create
        
    Returns:
        str: ID of the newly created group, or None if creation failed
    """
    response = requests.post(
        f"{MAILERLITE_BASE_URL}/groups",
        headers=MAILERLITE_HEADERS,
        json={"name": name}
    )
    
    if response.status_code in [200, 201]:
        return response.json()["data"]["id"]
    else:
        print(f"Failed to create group '{name}': {response.text}")
        return None


def extract_taxonomy_categories_from_database():
    """
    Extract unique taxonomy categories from the Supabase database.
    
    Returns:
        set: Set of unique main taxonomy categories
    """
    try:
        # Query all unique taxonomy classifications
        response = supabase.table('contacts')\
            .select('taxonomy_classification')\
            .not_('taxonomy_classification', 'is', None)\
            .execute()
        
        categories = set()
        
        for record in response.data:
            taxonomy = record.get('taxonomy_classification')
            if taxonomy:
                # Extract the main category (part before the colon)
                parts = taxonomy.split(':', 1)
                main_category = parts[0].strip()
                categories.add(main_category)
        
        return categories
    
    except Exception as e:
        print(f"Error extracting taxonomy categories from database: {e}")
        return set()


def setup_groups(use_subcategories=False, use_db_categories=False, 
                delay=0.5, prefix=""):
    """
    Set up MailerLite groups based on taxonomy categories.
    
    Args:
        use_subcategories: Whether to create groups for subcategories
        use_db_categories: Whether to extract categories from the database
        delay: Delay between API calls in seconds
        prefix: Optional prefix to add to group names
    
    Returns:
        dict: Mapping of created group names to their IDs
    """
    # Fetch existing groups
    existing_groups = fetch_existing_groups()
    print(f"Found {len(existing_groups)} existing groups in MailerLite")
    
    # Determine categories to use
    if use_db_categories:
        db_categories = extract_taxonomy_categories_from_database()
        if db_categories:
            categories = db_categories
            print(f"Extracted {len(categories)} categories from database: {categories}")
        else:
            categories = DEFAULT_TAXONOMY_CATEGORIES
            print(f"No categories found in database, using defaults: {categories}")
    else:
        categories = DEFAULT_TAXONOMY_CATEGORIES
        print(f"Using default categories: {categories}")
    
    # Create main category groups
    created_groups = {}
    for category in categories:
        group_name = f"{prefix}{category}" if prefix else category
        
        if group_name in existing_groups:
            print(f"Group '{group_name}' already exists with ID: {existing_groups[group_name]}")
            created_groups[category] = existing_groups[group_name]
        else:
            print(f"Creating group: {group_name}")
            group_id = create_group(group_name)
            if group_id:
                created_groups[category] = group_id
                print(f"Created group '{group_name}' with ID: {group_id}")
            else:
                print(f"Failed to create group: {group_name}")
        
        time.sleep(delay)
        
        # Create subcategory groups if requested
        if use_subcategories and category in SUBCATEGORIES:
            for subcategory in SUBCATEGORIES[category]:
                subcategory_name = f"{prefix}{category} - {subcategory}" if prefix else f"{category} - {subcategory}"
                
                if subcategory_name in existing_groups:
                    print(f"Subcategory group '{subcategory_name}' already exists")
                    created_groups[f"{category} - {subcategory}"] = existing_groups[subcategory_name]
                else:
                    print(f"Creating subcategory group: {subcategory_name}")
                    subcategory_id = create_group(subcategory_name)
                    if subcategory_id:
                        created_groups[f"{category} - {subcategory}"] = subcategory_id
                        print(f"Created subcategory group '{subcategory_name}' with ID: {subcategory_id}")
                    else:
                        print(f"Failed to create subcategory group: {subcategory_name}")
                
                time.sleep(delay)
    
    return created_groups


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Set up MailerLite groups for taxonomy categories')
    parser.add_argument('--use-subcategories', action='store_true', help='Create groups for subcategories')
    parser.add_argument('--use-db-categories', action='store_true', help='Extract categories from the database')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between API calls in seconds')
    parser.add_argument('--prefix', type=str, default='', help='Add a prefix to all group names')
    parser.add_argument('--list', action='store_true', help='List existing groups and exit')
    
    args = parser.parse_args()
    
    if not MAILERLITE_API_KEY:
        print("ERROR: MAILERLITE_API_KEY not found in environment variables")
        print("Please add it to your .env file")
        return
    
    if args.use_db_categories and (not SUPABASE_URL or not SUPABASE_KEY):
        print("ERROR: Supabase configuration not found in environment variables")
        print("Please add SUPABASE_URL and SUPABASE_SERVICE_KEY to your .env file")
        return
    
    # List existing groups if requested
    if args.list:
        existing_groups = fetch_existing_groups()
        print(f"Found {len(existing_groups)} existing groups in MailerLite:")
        for name, group_id in existing_groups.items():
            print(f"- {name} (ID: {group_id})")
        return
    
    # Setup groups
    print(f"Setting up MailerLite groups...")
    created_groups = setup_groups(
        use_subcategories=args.use_subcategories,
        use_db_categories=args.use_db_categories,
        delay=args.delay,
        prefix=args.prefix
    )
    
    print(f"Group setup completed. Created/found {len(created_groups)} groups.")
    

if __name__ == "__main__":
    main() 