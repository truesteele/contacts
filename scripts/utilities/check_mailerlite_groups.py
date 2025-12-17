#!/usr/bin/env python3

from supabase import create_client
import os
import sys
from dotenv import load_dotenv
import json
from collections import Counter
import requests

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
MAILERLITE_API_KEY = os.getenv('MAILERLITE_API_KEY')

if not MAILERLITE_API_KEY:
    print("Error: MAILERLITE_API_KEY not found in environment variables")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get MailerLite groups to map IDs to names
def get_mailerlite_groups():
    headers = {
        "Authorization": f"Bearer {MAILERLITE_API_KEY}",
        "Content-Type": "application/json",
    }
    
    response = requests.get("https://connect.mailerlite.com/api/groups", headers=headers)
    if response.status_code == 200:
        groups_data = response.json()
        return {str(group["id"]): group["name"] for group in groups_data.get("data", [])}
    else:
        print(f"Error fetching MailerLite groups: {response.status_code} - {response.text}")
        return {}

# Fetch group mappings
mailerlite_groups_map = get_mailerlite_groups()
print(f"Retrieved {len(mailerlite_groups_map)} groups from MailerLite API")
for group_id, name in mailerlite_groups_map.items():
    print(f"  {group_id}: {name}")

print("\n=== BASIC COUNTS ===")
# First check total synced contacts
response = supabase.table('contacts').select('count').eq('synced_to_mailerlite', True).execute()
total_synced = response.data[0]['count'] if response.data else 0
print(f'Total contacts synced to MailerLite: {total_synced}')

# Check invalid emails (email_verified = False)
response = supabase.table('contacts').select('count').eq('synced_to_mailerlite', True).eq('email_verified', False).eq('email_is_catch_all', False).execute()
invalid_count = response.data[0]['count'] if response.data else 0
print(f'Invalid emails synced to MailerLite: {invalid_count}')

# Check catch-all emails
response = supabase.table('contacts').select('count').eq('synced_to_mailerlite', True).eq('email_is_catch_all', True).execute()
catch_all_count = response.data[0]['count'] if response.data else 0
print(f'Catch-all emails synced to MailerLite: {catch_all_count}')

# Check unsubscribed contacts
response = supabase.table('contacts').select('count').eq('synced_to_mailerlite', True).eq('unsubscribed', True).execute()
unsubscribed_count = response.data[0]['count'] if response.data else 0
print(f'Unsubscribed contacts synced to MailerLite: {unsubscribed_count}')

print("\n=== MAILERLITE STATUS ===")
# Check contacts by mailerlite_status
response = supabase.table('contacts').select('mailerlite_status').eq('synced_to_mailerlite', True).execute()
status_counts = {}
for contact in response.data:
    status = contact.get('mailerlite_status')
    if status is None:
        status = "None"
    status_counts[status] = status_counts.get(status, 0) + 1

# Sort keys with None handling
for status, count in sorted(status_counts.items(), key=lambda x: str(x[0]) if x[0] is not None else ""):
    print(f"  {status}: {count} contacts")

print("\n=== MAILERLITE GROUPS DISTRIBUTION ===")
# Get all mailerlite_groups and count the frequency of each group ID
print("Fetching all mailerlite_groups to analyze (this might take a moment)...")
response = supabase.table('contacts').select('mailerlite_groups').eq('synced_to_mailerlite', True).execute()

# Process the groups data
group_counter = Counter()
contacts_without_groups = 0
contacts_with_groups = 0

for contact in response.data:
    groups_data = contact.get('mailerlite_groups')
    if not groups_data:
        contacts_without_groups += 1
        continue
        
    # Try to parse if it's a string representation of a list
    if isinstance(groups_data, str) and groups_data.startswith('['):
        try:
            groups_data = json.loads(groups_data)
        except:
            pass
    
    # Handle both list and string formats
    if isinstance(groups_data, list):
        if len(groups_data) == 0:
            contacts_without_groups += 1
        else:
            contacts_with_groups += 1
            for group_id in groups_data:
                # Check if group_id is a string or dict
                if isinstance(group_id, dict) and 'id' in group_id:
                    group_id = group_id['id']
                    
                group_name = mailerlite_groups_map.get(str(group_id), "Unknown")
                group_counter[f"{group_id} ({group_name})"] += 1
    else:
        # Handle single string ID
        contacts_with_groups += 1
        group_id = groups_data
        group_name = mailerlite_groups_map.get(str(group_id), "Unknown")
        group_counter[f"{group_id} ({group_name})"] += 1

# Print results
print(f"Contacts with groups: {contacts_with_groups}")
print(f"Contacts without groups: {contacts_without_groups}")
print(f"Total contacts checked: {contacts_with_groups + contacts_without_groups}")

print("\nMailerLite groups distribution (by group ID):")
for group_info, count in group_counter.most_common():
    print(f"  {group_info}: {count} contacts")

# Check for meaningful contact classification columns
print("\nChecking potential group columns:")
potential_group_columns = [
    'contact_type', 
    'relationship_level', 
    'mailerlite_groups',
    'mailerlite_group',
    'group',
    'groups',
    'tags',
    'category',
    'priority'
]

for column in potential_group_columns:
    try:
        response = supabase.table('contacts').select(f'{column}').limit(1).execute()
        if response.data and column in response.data[0]:
            print(f"Found column: {column}")
            # Get distribution of values in this column
            response = supabase.table('contacts').select(f'{column}, count').eq('synced_to_mailerlite', True).group_by(column).execute()
            print(f"Values in {column} (for synced contacts):")
            for item in response.data:
                value = item[column] if item[column] is not None else "NULL"
                print(f"  {value}: {item['count']} contacts")
    except Exception as e:
        # Column doesn't exist or query error
        pass 