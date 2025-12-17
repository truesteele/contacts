import os
import supabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get environment variables
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print('Supabase credentials not found in environment variables.')
    exit(1)

# Initialize Supabase client
print('Connecting to Supabase...')
client = supabase.create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Get total contact count
print('Counting total contacts...')
result = client.table('contacts').select('count').execute()
total_count = result.data[0]['count'] if result.data else 0
print(f'Total contacts in database: {total_count}')

# Try counting Bay Area contacts
print('Counting Bay Area contacts...')
result = client.table('contacts').select('count').filter('location_name', 'ilike', '%Bay Area%').execute()
bay_area_count = result.data[0]['count'] if result.data else 0
print(f'Bay Area contacts: {bay_area_count}')

# Count a few major cities
cities = ['San Francisco', 'Oakland', 'San Jose', 'Palo Alto', 'Mountain View']
for city in cities:
    result = client.table('contacts').select('count').filter('location_name', 'ilike', f'%{city}%').execute()
    city_count = result.data[0]['count'] if result.data else 0
    print(f'{city} contacts: {city_count}')

# Check pagination behavior
print('\nTesting pagination with location filter:')
for offset in [0, 50, 100]:
    result = client.table('contacts').select('id').filter('location_name', 'ilike', '%Bay Area%').range(offset, offset + 49).execute()
    print(f'Offset {offset}: {len(result.data)} results')

print('Done!') 