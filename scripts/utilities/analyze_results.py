#!/usr/bin/env python3
"""
Analyze categorization results.
This script generates a summary of how many contacts fall into each taxonomy category.
"""

import argparse
import csv
from collections import Counter, defaultdict
import re

def parse_category(classification):
    """Parse the category from the classification string."""
    if not classification:
        return "Uncategorized", "Uncategorized"
    
    # Split into main category and subcategory
    parts = classification.split(': ', 1)
    if len(parts) == 2:
        return parts[0], classification
    else:
        return "Other", classification

def main():
    parser = argparse.ArgumentParser(description="Analyze contact categorization results")
    parser.add_argument("--input", type=str, required=True, help="Input CSV file with categorized contacts")
    parser.add_argument("--detailed", action="store_true", help="Show detailed breakdown by subcategory")
    
    args = parser.parse_args()
    
    # Read the categorized CSV
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check if the file has the taxonomy column
            if 'Taxonomy Classification' not in reader.fieldnames:
                print(f"Error: The file {args.input} does not contain categorization results.")
                print("Make sure you're using a file that has been processed by the categorization script.")
                return
            
            # Count occurrences of each category
            main_categories = Counter()
            subcategories = Counter()
            category_to_contacts = defaultdict(list)
            
            # Process all rows
            for row in reader:
                classification = row.get('Taxonomy Classification', 'Uncategorized')
                
                # Handle uncategorized contacts
                if not classification or classification == 'Error in classification':
                    classification = 'Uncategorized'
                
                # Parse category
                main_category, full_category = parse_category(classification)
                main_categories[main_category] += 1
                subcategories[full_category] += 1
                
                # Store contact names for detailed reporting
                contact_name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                category_to_contacts[full_category].append(contact_name)
    
    except FileNotFoundError:
        print(f"Error: File {args.input} not found")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Print summary
    total_contacts = sum(main_categories.values())
    print("\n" + "="*50)
    print(f"CONTACT CATEGORIZATION SUMMARY")
    print(f"Total contacts analyzed: {total_contacts}")
    print("="*50)
    
    print("\nMAIN CATEGORIES:")
    print("-"*50)
    # Sort by count in descending order
    for category, count in sorted(main_categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_contacts) * 100
        print(f"{category}: {count} contacts ({percentage:.1f}%)")
    
    # Print detailed breakdown if requested
    if args.detailed:
        print("\nDETAILED BREAKDOWN:")
        print("-"*50)
        
        # Group subcategories by main category
        grouped = defaultdict(list)
        for subcat, count in subcategories.items():
            main_cat, _ = parse_category(subcat)
            grouped[main_cat].append((subcat, count))
        
        # Print grouped by main category
        for main_cat, subcats in sorted(grouped.items()):
            print(f"\n{main_cat}:")
            for subcat, count in sorted(subcats, key=lambda x: x[1], reverse=True):
                percentage = (count / total_contacts) * 100
                # Get just the subcategory name without the main category
                parts = subcat.split(': ', 1)
                if len(parts) == 2:
                    subcat_name = parts[1]
                else:
                    subcat_name = subcat
                print(f"  - {subcat_name}: {count} contacts ({percentage:.1f}%)")
    
    print("\nRECOMMENDED ACTIONS:")
    print("-"*50)
    
    # Strategic prospects
    strategic_count = main_categories.get('Strategic Business Prospects', 0)
    strategic_pct = (strategic_count / total_contacts) * 100 if total_contacts else 0
    print(f"• Strategic Business Prospects: {strategic_count} contacts ({strategic_pct:.1f}%)")
    print("  Recommendation: Prioritize these contacts for email enrichment and")
    print("  create targeted outreach about your Fractional CIO services.")
    
    # Newsletter audience
    newsletter_count = main_categories.get('Newsletter Audience', 0)
    newsletter_pct = (newsletter_count / total_contacts) * 100 if total_contacts else 0
    print(f"\n• Newsletter Audience: {newsletter_count} contacts ({newsletter_pct:.1f}%)")
    print("  Recommendation: Send a personalized invitation to subscribe to")
    print("  'The Long Arc' newsletter with content samples.")
    
    # Knowledge network
    knowledge_count = main_categories.get('Knowledge & Industry Network', 0)
    knowledge_pct = (knowledge_count / total_contacts) * 100 if total_contacts else 0
    print(f"\n• Knowledge & Industry Network: {knowledge_count} contacts ({knowledge_pct:.1f}%)")
    print("  Recommendation: Share updates about your ventures and explore")
    print("  potential partnerships for your startup ideas.")
    
    # Environmental champions for Outdoorithm
    env_cat = 'Knowledge & Industry Network: Environmental Champions'
    env_count = subcategories.get(env_cat, 0)
    env_pct = (env_count / total_contacts) * 100 if total_contacts else 0
    print(f"\n• Environmental Champions: {env_count} contacts ({env_pct:.1f}%)")
    print("  Recommendation: Reach out specifically about Outdoorithm Collective")
    print("  to explore support and partnerships.")
    
    print("\nNext steps for email enrichment prioritization:")
    print("1. Export Strategic Business Prospects and high-value Knowledge Network contacts")
    print("2. Enrich these contacts with Clay.com first")
    print("3. Create targeted messaging based on subcategories")
    
    # Generate a sample of contacts from the highest priority category
    highest_cat = sorted(subcategories.items(), key=lambda x: x[1], reverse=True)[0][0]
    sample_contacts = category_to_contacts.get(highest_cat, [])[:5]
    if sample_contacts:
        print(f"\nSample contacts from highest category ({highest_cat}):")
        for contact in sample_contacts:
            print(f"- {contact}")

if __name__ == "__main__":
    main() 