#!/usr/bin/env python3
"""
Export specific categories from the categorized contacts CSV.
This helps prepare targeted lists for Clay.com enrichment or other purposes.
"""

import argparse
import csv
import os

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
    parser = argparse.ArgumentParser(description="Export specific categories from categorized contacts")
    parser.add_argument("--input", type=str, required=True, help="Input CSV file with categorized contacts")
    parser.add_argument("--output", type=str, required=True, help="Output CSV file for filtered contacts")
    parser.add_argument("--category", type=str, action='append', help="Categories to export (can be used multiple times)")
    parser.add_argument("--subcategory", type=str, action='append', help="Subcategories to export (can be used multiple times)")
    parser.add_argument("--list-categories", action="store_true", help="List all available categories without exporting")
    
    args = parser.parse_args()
    
    # Check that we have the input file
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found")
        return
    
    # Read the categorized CSV and collect categories
    available_categories = set()
    available_subcategories = set()
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check if the file has the taxonomy column
            if 'Taxonomy Classification' not in reader.fieldnames:
                print(f"Error: The file {args.input} does not contain categorization results.")
                print("Make sure you're using a file that has been processed by the categorization script.")
                return
            
            # Read all rows to collect available categories
            all_rows = []
            for row in reader:
                all_rows.append(row)
                classification = row.get('Taxonomy Classification', '')
                
                if not classification:
                    continue
                
                # Parse category
                main_category, full_category = parse_category(classification)
                available_categories.add(main_category)
                if full_category != main_category:
                    available_subcategories.add(full_category)
    
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # If just listing categories, print them and exit
    if args.list_categories:
        print("\nAvailable main categories:")
        print("-" * 50)
        for category in sorted(available_categories):
            print(f"- {category}")
        
        print("\nAvailable subcategories:")
        print("-" * 50)
        for subcategory in sorted(available_subcategories):
            print(f"- {subcategory}")
        return
    
    # Ensure we have categories or subcategories to filter by
    if not args.category and not args.subcategory:
        print("Error: You must specify at least one --category or --subcategory to export")
        print("Use --list-categories to see available options")
        return
    
    # Filter rows based on category/subcategory
    selected_rows = []
    
    categories_to_export = set(args.category) if args.category else set()
    subcategories_to_export = set(args.subcategory) if args.subcategory else set()
    
    for row in all_rows:
        classification = row.get('Taxonomy Classification', '')
        
        if not classification:
            continue
        
        # Parse the categories
        main_category, full_category = parse_category(classification)
        
        # Export if main category or full subcategory matches
        if main_category in categories_to_export or full_category in subcategories_to_export:
            selected_rows.append(row)
    
    # Write the filtered rows to output file
    if selected_rows:
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(selected_rows)
            
        print(f"Successfully exported {len(selected_rows)} contacts to {args.output}")
        
        # Print summary of categories in the export
        category_counts = {}
        for row in selected_rows:
            classification = row.get('Taxonomy Classification', '')
            category_counts[classification] = category_counts.get(classification, 0) + 1
        
        print("\nExported contacts by category:")
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"- {cat}: {count} contacts")
    else:
        print("No contacts matched the specified categories")

if __name__ == "__main__":
    main() 