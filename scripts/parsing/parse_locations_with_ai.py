#!/usr/bin/env python3
"""
Parse locations using OpenAI's structured output feature for accurate city, state, country extraction
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI
from typing import Dict, Optional
import time

# Load environment variables
load_dotenv()

# Initialize clients
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)
openai_client = OpenAI(api_key=os.environ.get('OPENAI_APIKEY'))

def parse_location_with_ai(location_text: str, additional_context: str = "") -> Optional[Dict]:
    """
    Use OpenAI structured output to parse location into city, state, country
    """
    
    # Define the JSON schema for structured output
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "location_parser",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name, or null if not identifiable"
                    },
                    "state": {
                        "type": "string",
                        "description": "The state/province name (full name, not abbreviation), or null if not identifiable"
                    },
                    "country": {
                        "type": "string",
                        "description": "The country name, or null if not identifiable"
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Confidence level in the parsing"
                    },
                    "metro_area": {
                        "type": "string",
                        "description": "Metropolitan area if applicable (e.g., 'San Francisco Bay Area')"
                    }
                },
                "required": ["city", "state", "country", "confidence", "metro_area"],
                "additionalProperties": False
            }
        }
    }
    
    prompt = f"""
    Parse this location information into structured components.
    
    Location text: "{location_text}"
    Additional context: "{additional_context}"
    
    Rules:
    - Use full state names (e.g., "California" not "CA")
    - For US locations, always include "United States" as country
    - For metro areas, identify the specific city if possible
    - Set null for any component you cannot identify
    - Consider common patterns like "Greater [City] Area" or "[City] Metro"
    - If you see "United States" alone, set country to "United States" and others to null
    - For locations like "San Francisco Bay Area", set city to a primary city like "San Francisco"
    """
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Using mini for cost efficiency
            messages=[
                {"role": "system", "content": "You are a location parser. Extract city, state, and country from location text."},
                {"role": "user", "content": prompt}
            ],
            response_format=response_format,
            temperature=0.1,  # Low temperature for consistency
            max_tokens=200
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Clean up the results
        if result['city'] == 'null' or result['city'] == '':
            result['city'] = None
        if result['state'] == 'null' or result['state'] == '':
            result['state'] = None
        if result['country'] == 'null' or result['country'] == '':
            result['country'] = None
        if result['metro_area'] == 'null' or result['metro_area'] == '':
            result['metro_area'] = None
            
        return result
        
    except Exception as e:
        print(f"    ❌ Error parsing with AI: {e}")
        return None

print("🤖 AI-Powered Location Parser")
print("=" * 60)
print("Using OpenAI structured output for accurate location extraction\n")

# Get records that need location parsing
print("📍 Finding records with unparsed locations...")

# Query for records with location data but no parsed city
# Focus on records that have enrichment data (more likely to have location)
unparsed_query = supabase.table('contacts').select(
    'id, first_name, last_name, headline, company, summary, enrich_person_from_profile'
).is_('city', 'null').not_.is_('enrich_person_from_profile', 'null').limit(100)  # Process enriched records first

unparsed = unparsed_query.execute()
records = unparsed.data

print(f"Found {len(records)} records to parse (batch of 100)\n")

# Process each record
successful = 0
failed = 0

for i, record in enumerate(records, 1):
    # Build location context from available fields
    location_sources = []
    
    # Check headline for location
    headline = record.get('headline', '')
    if headline:
        location_sources.append(headline)
    
    # Check enrichment data for location (more thorough)
    enrich_data = record.get('enrich_person_from_profile')
    if enrich_data and isinstance(enrich_data, dict):
        # Direct location fields
        if 'location' in enrich_data and enrich_data['location']:
            location_sources.append(str(enrich_data['location']))
        if 'city' in enrich_data and enrich_data['city']:
            location_sources.append(str(enrich_data['city']))
        if 'state' in enrich_data and enrich_data['state']:
            location_sources.append(str(enrich_data['state']))
        if 'country' in enrich_data and enrich_data['country']:
            location_sources.append(str(enrich_data['country']))
        
        # Check experiences for location
        if 'experiences' in enrich_data and isinstance(enrich_data['experiences'], list):
            for exp in enrich_data['experiences'][:2]:  # Check first 2 experiences
                if isinstance(exp, dict) and 'location' in exp and exp['location']:
                    location_sources.append(f"Work location: {exp['location']}")
    
    # Check summary for location mentions
    summary = record.get('summary', '')
    if summary and len(summary) > 0:
        # Look for location patterns in first 200 chars
        summary_start = summary[:200]
        if 'based in' in summary_start.lower() or 'located in' in summary_start.lower():
            location_sources.append(summary_start)
    
    if not location_sources:
        continue
    
    # Combine all location hints
    location_text = ' | '.join(location_sources)
    
    print(f"[{i}/{len(records)}] {record['first_name']} {record.get('last_name', '')}")
    print(f"    📝 Context: {location_text[:100]}...")
    
    # Parse with AI
    parsed = parse_location_with_ai(
        location_text,
        additional_context=f"Company: {record.get('company', 'Unknown')}"
    )
    
    if parsed and parsed['confidence'] in ['high', 'medium']:
        # Update the database
        update_data = {}
        if parsed['city']:
            update_data['city'] = parsed['city']
        if parsed['state']:
            update_data['state'] = parsed['state']
        if parsed['country']:
            update_data['country'] = parsed['country']
        
        if update_data:
            try:
                result = supabase.table('contacts').update(update_data).eq('id', record['id']).execute()
                print(f"    ✅ Parsed: {parsed['city']}, {parsed['state']}, {parsed['country']} (confidence: {parsed['confidence']})")
                successful += 1
            except Exception as e:
                print(f"    ❌ Database error: {e}")
                failed += 1
        else:
            print(f"    ⚠️ No location data extracted")
            failed += 1
    else:
        print(f"    ⚠️ Low confidence or failed to parse")
        failed += 1
    
    # Rate limiting
    if i % 10 == 0:
        print(f"\n    [Progress: {i}/{len(records)} - Success: {successful}, Failed: {failed}]\n")
        time.sleep(1)  # Brief pause every 10 records

# Final summary
print("\n" + "=" * 60)
print("PARSING COMPLETE")
print("=" * 60)
print(f"✅ Successfully parsed: {successful} records")
print(f"❌ Failed to parse: {failed} records")
print(f"📊 Success rate: {(successful/(successful+failed)*100 if (successful+failed) > 0 else 0):.1f}%")

# Check remaining unparsed
remaining_query = supabase.table('contacts').select('count', count='exact').is_('city', 'null').execute()
remaining = remaining_query.count

print(f"\n📍 Remaining unparsed records: {remaining}")
print("\n💡 Run this script again to process more records (100 at a time)")
print("✨ AI-powered location parsing complete!")