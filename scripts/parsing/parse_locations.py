#!/usr/bin/env python3
"""
Location Parser Script
Parses location_name into clean city, state, and country columns
"""

import os
import sys
import re
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import argparse

# Load environment variables
load_dotenv()

class LocationParser:
    def __init__(self, test_mode: bool = False, limit: int = None):
        self.supabase = None
        self.test_mode = test_mode
        self.limit = limit
        self.stats = {
            'total_processed': 0,
            'parsed_successfully': 0,
            'already_parsed': 0,
            'failed': 0,
            'no_location': 0
        }
        
        # Common patterns and mappings
        self.metro_areas = {
            'San Francisco Bay Area': ('San Francisco', 'California'),
            'New York City Metropolitan Area': ('New York', 'New York'),
            'Los Angeles Metropolitan Area': ('Los Angeles', 'California'),
            'Chicago Metropolitan Area': ('Chicago', 'Illinois'),
            'Washington DC Metro Area': ('Washington', 'District of Columbia'),
            'Dallas-Fort Worth Metroplex': ('Dallas', 'Texas'),
            'Greater Boston': ('Boston', 'Massachusetts'),
            'Greater Philadelphia': ('Philadelphia', 'Pennsylvania'),
            'Greater Seattle Area': ('Seattle', 'Washington'),
            'Kansas City Metropolitan Area': ('Kansas City', 'Missouri'),
            'Portland Metro': ('Portland', 'Oregon'),
            'Denver Metropolitan Area': ('Denver', 'Colorado'),
            'Miami-Fort Lauderdale Area': ('Miami', 'Florida'),
            'Phoenix Metropolitan Area': ('Phoenix', 'Arizona'),
            'Detroit Metropolitan Area': ('Detroit', 'Michigan')
        }
        
        # State abbreviations to full names
        self.state_abbrev = {
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
        
        # Country variations
        self.country_mapping = {
            'US': 'United States',
            'USA': 'United States',
            'U.S.': 'United States',
            'U.S.A.': 'United States',
            'UK': 'United Kingdom',
            'U.K.': 'United Kingdom',
            'GB': 'United Kingdom',
            'UAE': 'United Arab Emirates',
            'U.A.E.': 'United Arab Emirates'
        }
    
    def connect(self):
        """Connect to Supabase"""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not url or not key:
            print("✗ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
            
        self.supabase = create_client(url, key)
        print("✓ Connected to Supabase")
        return True
    
    def parse_location(self, location_str: str) -> Dict[str, Optional[str]]:
        """Parse location string into components"""
        if not location_str:
            return {'city': None, 'state': None, 'country': None}
        
        # Clean the string
        location_str = location_str.strip()
        
        # Check for metro areas first
        for metro, (city, state) in self.metro_areas.items():
            if metro.lower() in location_str.lower():
                # Extract country if present
                parts = location_str.split(',')
                country = parts[-1].strip() if len(parts) > 1 else 'United States'
                country = self.normalize_country(country)
                return {
                    'city': city,
                    'state': state,
                    'country': country
                }
        
        # Split by comma
        parts = [p.strip() for p in location_str.split(',')]
        
        # Handle different formats
        if len(parts) == 1:
            # Check common countries first
            known_countries = ['Spain', 'France', 'Germany', 'Italy', 'Canada', 'Mexico', 'Brazil', 
                             'Argentina', 'China', 'Japan', 'India', 'Australia', 'Portugal',
                             'Singapore', 'Venezuela', 'United Kingdom', 'Ireland', 'Netherlands']
            
            # Just country or city
            if parts[0] in self.country_mapping.values() or parts[0] in self.country_mapping or parts[0] in known_countries:
                return {
                    'city': None,
                    'state': None,
                    'country': self.normalize_country(parts[0])
                }
            else:
                # Assume it's a city in the US
                return {
                    'city': parts[0],
                    'state': None,
                    'country': 'United States'
                }
        
        elif len(parts) == 2:
            # Could be City, Country or City, State (US) or State, Country
            second_part = self.normalize_country(parts[1])
            
            # Check if second part is a country
            if second_part in ['United States', 'Canada', 'United Kingdom', 'Australia'] or \
               parts[1] in self.country_mapping.values() or parts[1] in self.country_mapping:
                # City, Country format
                return {
                    'city': parts[0],
                    'state': None,
                    'country': second_part
                }
            else:
                # Likely City, State (assume US)
                state = self.normalize_state(parts[1])
                return {
                    'city': parts[0],
                    'state': state,
                    'country': 'United States'
                }
        
        elif len(parts) >= 3:
            # Standard format: City, State, Country
            return {
                'city': parts[0],
                'state': self.normalize_state(parts[1]),
                'country': self.normalize_country(parts[-1])
            }
        
        return {'city': None, 'state': None, 'country': None}
    
    def normalize_state(self, state_str: str) -> str:
        """Normalize state name"""
        if not state_str:
            return state_str
        
        state_str = state_str.strip()
        
        # Check if it's an abbreviation
        if state_str.upper() in self.state_abbrev:
            return self.state_abbrev[state_str.upper()]
        
        # Handle special cases
        if state_str.lower() == 'dc':
            return 'District of Columbia'
        
        return state_str
    
    def normalize_country(self, country_str: str) -> str:
        """Normalize country name"""
        if not country_str:
            return country_str
        
        country_str = country_str.strip()
        
        # Check mapping
        if country_str in self.country_mapping:
            return self.country_mapping[country_str]
        
        # Check uppercase version
        if country_str.upper() in self.country_mapping:
            return self.country_mapping[country_str.upper()]
        
        return country_str
    
    def get_contacts_to_parse(self) -> list:
        """Get contacts with location_name but no parsed location data"""
        query = self.supabase.table('contacts').select(
            'id, location_name, city, state, country'
        ).not_.is_('location_name', 'null').neq('location_name', '')
        
        # Get contacts where city, state, country are not yet parsed
        query = query.is_('city', 'null')
        
        if self.limit:
            query = query.limit(self.limit)
        
        response = query.execute()
        return response.data
    
    def update_contact_location(self, contact_id: int, location_data: Dict) -> bool:
        """Update contact with parsed location data"""
        try:
            # Only update non-null values
            updates = {}
            if location_data.get('city'):
                updates['city'] = location_data['city']
            if location_data.get('state'):
                updates['state'] = location_data['state']
            if location_data.get('country'):
                updates['country'] = location_data['country']
            
            if updates:
                response = self.supabase.table('contacts').update(updates).eq('id', contact_id).execute()
                return True
            return False
        except Exception as e:
            print(f"  ✗ Failed to update contact {contact_id}: {e}")
            return False
    
    def run(self):
        """Main parsing process"""
        if not self.connect():
            return False
        
        print("\n🔍 Fetching contacts with unparsed locations...")
        contacts = self.get_contacts_to_parse()
        
        if not contacts:
            print("No contacts need location parsing")
            return True
        
        print(f"Found {len(contacts)} contacts to parse")
        
        if self.test_mode:
            print("⚠️ TEST MODE - Processing first 10 contacts only")
            contacts = contacts[:10]
        
        print("\n🚀 Starting location parsing...")
        print("=" * 60)
        
        for i, contact in enumerate(contacts, 1):
            self.stats['total_processed'] += 1
            location_name = contact.get('location_name', '')
            
            print(f"\n[{i}/{len(contacts)}] Location: {location_name}")
            
            if not location_name:
                self.stats['no_location'] += 1
                continue
            
            # Check if already parsed - skip this check since we pre-filter
            # The data comes back with None values, not actual database NULLs
            # So we'll just parse everything that was returned
            
            # Parse location
            parsed = self.parse_location(location_name)
            
            if parsed['city'] or parsed['state'] or parsed['country']:
                print(f"  📍 City: {parsed['city'] or 'N/A'}")
                print(f"  📍 State: {parsed['state'] or 'N/A'}")
                print(f"  📍 Country: {parsed['country'] or 'N/A'}")
                
                # Update database
                if self.update_contact_location(contact['id'], parsed):
                    self.stats['parsed_successfully'] += 1
                    print("  ✓ Updated location data")
                else:
                    self.stats['failed'] += 1
            else:
                print("  ⚠ Could not parse location")
                self.stats['failed'] += 1
            
            # Progress update
            if i % 50 == 0 and i < len(contacts):
                print(f"\n  → Progress: {i}/{len(contacts)} processed...")
        
        self.print_summary()
        return True
    
    def print_summary(self):
        """Print parsing summary"""
        print("\n" + "=" * 60)
        print("📊 LOCATION PARSING SUMMARY")
        print("=" * 60)
        print(f"Total processed:       {self.stats['total_processed']:,}")
        print(f"Parsed successfully:   {self.stats['parsed_successfully']:,}")
        print(f"Already parsed:        {self.stats['already_parsed']:,}")
        print(f"No location data:      {self.stats['no_location']:,}")
        print(f"Failed to parse:       {self.stats['failed']:,}")
        print("=" * 60)
        
        if self.stats['total_processed'] > 0:
            success_rate = (self.stats['parsed_successfully'] / self.stats['total_processed']) * 100
            print(f"📈 Success rate: {success_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description='Parse location data into city, state, country columns'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Limit number of contacts to parse'
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Test mode - process only 10 contacts'
    )
    
    args = parser.parse_args()
    
    try:
        location_parser = LocationParser(test_mode=args.test, limit=args.limit)
        success = location_parser.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()