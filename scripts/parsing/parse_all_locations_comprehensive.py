#!/usr/bin/env python3
"""
Comprehensive location parser that ensures ALL available location data is parsed
Handles location_name, enrichment data, and uses AI for complex cases
"""

import os
import json
import re
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

class ComprehensiveLocationParser:
    def __init__(self):
        self.stats = {
            'total_processed': 0,
            'location_name_parsed': 0,
            'enrichment_parsed': 0,
            'ai_parsed': 0,
            'failed': 0,
            'already_parsed': 0
        }
        
        # Common metro areas
        self.metro_areas = {
            'San Francisco Bay Area': 'San Francisco',
            'Greater Seattle Area': 'Seattle',
            'Portland Metro': 'Portland',
            'New York City Metropolitan Area': 'New York',
            'Greater Los Angeles': 'Los Angeles',
            'Chicago Metropolitan Area': 'Chicago',
            'Dallas-Fort Worth': 'Dallas',
            'Washington DC Metro': 'Washington',
            'Greater Boston': 'Boston'
        }
        
        # State mappings
        self.state_abbreviations = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
            'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
            'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
            'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
            'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
            'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
            'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
            'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
            'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
            'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
            'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
        }

    def parse_simple_location(self, location_str: str) -> Optional[Dict]:
        """Parse standard location format: City, State, Country"""
        if not location_str:
            return None
            
        location_str = location_str.strip()
        
        # Check for metro areas
        for metro, city in self.metro_areas.items():
            if metro.lower() in location_str.lower():
                parts = location_str.split(',')
                state = None
                country = 'United States' if 'united states' in location_str.lower() else None
                
                # Try to extract state
                for part in parts:
                    clean_part = part.strip()
                    if clean_part in self.state_abbreviations:
                        state = self.state_abbreviations[clean_part]
                    elif any(clean_part == s for s in self.state_abbreviations.values()):
                        state = clean_part
                
                return {'city': city, 'state': state, 'country': country}
        
        # Standard parsing
        parts = [p.strip() for p in location_str.split(',')]
        
        if len(parts) == 1:
            # Just country or state
            if parts[0] in ['United States', 'USA', 'US']:
                return {'city': None, 'state': None, 'country': 'United States'}
            elif parts[0] in self.state_abbreviations:
                return {'city': None, 'state': self.state_abbreviations[parts[0]], 'country': 'United States'}
            elif parts[0] in self.state_abbreviations.values():
                return {'city': None, 'state': parts[0], 'country': 'United States'}
            else:
                return {'city': parts[0], 'state': None, 'country': None}
                
        elif len(parts) == 2:
            # City, State or City, Country
            city = parts[0]
            second = parts[1]
            
            if second in self.state_abbreviations:
                return {'city': city, 'state': self.state_abbreviations[second], 'country': 'United States'}
            elif second in self.state_abbreviations.values():
                return {'city': city, 'state': second, 'country': 'United States'}
            elif 'united states' in second.lower() or second in ['USA', 'US']:
                return {'city': city, 'state': None, 'country': 'United States'}
            else:
                # Assume it's a country
                return {'city': city, 'state': None, 'country': second}
                
        elif len(parts) >= 3:
            # City, State, Country
            city = parts[0]
            state = parts[1]
            country = parts[2] if len(parts) > 2 else None
            
            # Clean up state
            if state in self.state_abbreviations:
                state = self.state_abbreviations[state]
            
            # Clean up country
            if country and ('united states' in country.lower() or country in ['USA', 'US']):
                country = 'United States'
                
            return {'city': city, 'state': state, 'country': country}
        
        return None

    def parse_with_ai(self, location_hints: str, context: str = "") -> Optional[Dict]:
        """Use AI for complex location parsing"""
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "location_parser",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": ["string", "null"]},
                        "state": {"type": ["string", "null"]},
                        "country": {"type": ["string", "null"]},
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"]}
                    },
                    "required": ["city", "state", "country", "confidence"],
                    "additionalProperties": False
                }
            }
        }
        
        prompt = f"""
        Extract location from this text. Return null for unknown components.
        Text: {location_hints}
        Context: {context}
        
        Rules:
        - Use full state names (California not CA)
        - For US locations, set country to "United States"
        - Only return high/medium confidence if you're sure
        """
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract location components from text."},
                    {"role": "user", "content": prompt}
                ],
                response_format=response_format,
                temperature=0.1,
                max_tokens=150
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Only return if confident
            if result['confidence'] in ['high', 'medium']:
                return {
                    'city': result['city'],
                    'state': result['state'],
                    'country': result['country']
                }
        except Exception as e:
            return None
        
        return None

    def process_contact(self, contact: Dict) -> Optional[Dict]:
        """Process a single contact and extract location"""
        
        # Skip if already has city
        if contact.get('city'):
            self.stats['already_parsed'] += 1
            return None
        
        # 1. Try location_name first (most reliable)
        if contact.get('location_name'):
            parsed = self.parse_simple_location(contact['location_name'])
            if parsed and parsed.get('city'):
                self.stats['location_name_parsed'] += 1
                return parsed
        
        # 2. Check enrichment data
        enrich_data = contact.get('enrich_person_from_profile')
        if enrich_data and isinstance(enrich_data, dict):
            # Direct location fields
            if enrich_data.get('city') or enrich_data.get('location'):
                location_str = f"{enrich_data.get('city', '')}, {enrich_data.get('state', '')}, {enrich_data.get('country', '')}"
                location_str = location_str.replace(', ,', ',').strip(', ')
                
                if not location_str or location_str == ',':
                    location_str = enrich_data.get('location', '')
                
                if location_str:
                    parsed = self.parse_simple_location(location_str)
                    if parsed and parsed.get('city'):
                        self.stats['enrichment_parsed'] += 1
                        return parsed
        
        # 3. Try AI parsing as last resort
        location_hints = []
        if contact.get('location_name'):
            location_hints.append(contact['location_name'])
        if contact.get('headline'):
            location_hints.append(contact['headline'])
        if enrich_data and isinstance(enrich_data, dict):
            if enrich_data.get('location'):
                location_hints.append(str(enrich_data['location']))
        
        if location_hints:
            combined_hints = ' | '.join(location_hints[:3])
            parsed = self.parse_with_ai(combined_hints, f"Company: {contact.get('company', '')}")
            if parsed and parsed.get('city'):
                self.stats['ai_parsed'] += 1
                return parsed
        
        self.stats['failed'] += 1
        return None

    def run(self):
        """Process all contacts with unparsed locations"""
        print("🌍 COMPREHENSIVE LOCATION PARSER")
        print("=" * 60)
        print("Processing ALL contacts with any location data...\n")
        
        # Get all contacts with potential location data but no parsed city
        query = supabase.table('contacts').select(
            'id, location_name, city, state, country, headline, company, enrich_person_from_profile'
        ).is_('city', 'null')
        
        # Process in batches
        batch_size = 500
        offset = 0
        
        while True:
            batch_query = query.range(offset, offset + batch_size - 1)
            result = batch_query.execute()
            contacts = result.data
            
            if not contacts:
                break
            
            print(f"Processing batch: {offset + 1} to {offset + len(contacts)}")
            
            for i, contact in enumerate(contacts, 1):
                self.stats['total_processed'] += 1
                
                # Process the contact
                parsed = self.process_contact(contact)
                
                if parsed:
                    # Update database
                    update_data = {}
                    if parsed.get('city'):
                        update_data['city'] = parsed['city']
                    if parsed.get('state'):
                        update_data['state'] = parsed['state']
                    if parsed.get('country'):
                        update_data['country'] = parsed['country']
                    
                    if update_data:
                        try:
                            supabase.table('contacts').update(update_data).eq('id', contact['id']).execute()
                        except Exception as e:
                            print(f"  Error updating ID {contact['id']}: {e}")
                
                # Progress update
                if self.stats['total_processed'] % 100 == 0:
                    print(f"  Progress: {self.stats['total_processed']} processed | "
                          f"Parsed: {self.stats['location_name_parsed'] + self.stats['enrichment_parsed'] + self.stats['ai_parsed']} | "
                          f"Failed: {self.stats['failed']}")
            
            offset += batch_size
            
            # Brief pause between batches
            if len(contacts) == batch_size:
                time.sleep(0.5)
        
        self.print_summary()
    
    def print_summary(self):
        """Print final summary"""
        print("\n" + "=" * 60)
        print("📊 PARSING COMPLETE")
        print("=" * 60)
        print(f"Total processed: {self.stats['total_processed']:,}")
        print(f"Already had city: {self.stats['already_parsed']:,}")
        print(f"\nSuccessfully parsed:")
        print(f"  From location_name: {self.stats['location_name_parsed']:,}")
        print(f"  From enrichment data: {self.stats['enrichment_parsed']:,}")
        print(f"  Using AI: {self.stats['ai_parsed']:,}")
        total_parsed = self.stats['location_name_parsed'] + self.stats['enrichment_parsed'] + self.stats['ai_parsed']
        print(f"  TOTAL: {total_parsed:,}")
        print(f"\nFailed to parse: {self.stats['failed']:,}")
        
        if self.stats['total_processed'] > 0:
            success_rate = (total_parsed / (self.stats['total_processed'] - self.stats['already_parsed']) * 100) if (self.stats['total_processed'] - self.stats['already_parsed']) > 0 else 0
            print(f"Success rate: {success_rate:.1f}%")

if __name__ == "__main__":
    parser = ComprehensiveLocationParser()
    parser.run()