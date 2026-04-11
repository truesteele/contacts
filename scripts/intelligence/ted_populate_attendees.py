#!/usr/bin/env python3
"""
Populate Supabase ted_attendees table from TED warm leads + triage results + shortlist.

Usage:
  python scripts/intelligence/ted_populate_attendees.py
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('/Users/Justin/Code/TrueSteele/contacts/.env')

supabase = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_SERVICE_KEY']
)

# Load data
print("Loading data...")
leads = json.load(open('/tmp/ted_warm_leads.json'))
triage = json.load(open('/tmp/ted_triage_results.json'))
shortlist = json.load(open('/tmp/ted_shortlist.json'))

# Build lookups
triage_by_id = {t['ted_id']: t for t in triage}
shortlist_by_id = {s['ted_id']: s for s in shortlist}

print(f"  Leads: {len(leads)}, Triage: {len(triage_by_id)}, Shortlist: {len(shortlist_by_id)}")

# Load existing lookbook state to migrate
print("Loading existing lookbook state...")
state_resp = supabase.table('ted_lookbook_state').select('*').execute()
state_by_name = {s['contact_name']: s for s in state_resp.data} if state_resp.data else {}
print(f"  Existing state entries: {len(state_by_name)}")

# Build rows
rows = []
for lead in leads:
    tid = lead['ted_id']
    t = triage_by_id.get(tid, {})
    s = shortlist_by_id.get(tid)

    # Migrate state from ted_lookbook_state
    name = lead.get('ted_name', '')
    state = state_by_name.get(name, {})

    row = {
        'ted_id': tid,
        'ted_name': name,
        'ted_firstname': lead.get('ted_firstname'),
        'ted_lastname': lead.get('ted_lastname'),
        'ted_title': lead.get('ted_title'),
        'ted_org': lead.get('ted_org'),
        'ted_city': lead.get('ted_city'),
        'ted_country': lead.get('ted_country'),
        'ted_about': lead.get('ted_about'),
        'ted_photo': lead.get('ted_photo'),
        'ted_linkedin': lead.get('ted_linkedin'),
        'ted_is_speaker': bool(lead.get('ted_is_speaker')),
        'ted_is_fellow': bool(lead.get('ted_is_fellow')),
        'justin_connection': bool(lead.get('justin_connection')),
        'sally_connection': bool(lead.get('sally_connection')),
        'relevance_score': t.get('relevance_score'),
        'partnership_type': t.get('partnership_type'),
        'partnership_types': json.dumps(t.get('partnership_types', [])),
        'reasoning': t.get('reasoning'),
        'conversation_hook': t.get('conversation_hook'),
        'key_signal': t.get('key_signal'),
        'tier': s.get('tier') if s else None,
        'sally_pinned': False,
        'sally_reached_out': state.get('sally_reached_out', False) or False,
        'sally_notes': None,
        'justin_context': state.get('justin_context'),
    }
    rows.append(row)

print(f"Prepared {len(rows)} rows")

# Insert in batches of 500
batch_size = 500
for i in range(0, len(rows), batch_size):
    batch = rows[i:i + batch_size]
    supabase.table('ted_attendees').upsert(batch, on_conflict='ted_id').execute()
    print(f"  Inserted batch {i // batch_size + 1}: rows {i+1}-{i+len(batch)}")

# Verify
count_resp = supabase.table('ted_attendees').select('ted_id', count='exact').execute()
print(f"\nTotal rows in ted_attendees: {count_resp.count}")

# Check tiers
for tier in [1, 2, 3]:
    t_resp = supabase.table('ted_attendees').select('ted_id', count='exact').eq('tier', tier).execute()
    print(f"  Tier {tier}: {t_resp.count}")

pinned = supabase.table('ted_attendees').select('ted_id', count='exact').eq('sally_pinned', True).execute()
print(f"  Sally pinned: {pinned.count}")

with_context = supabase.table('ted_attendees').select('ted_name').neq('justin_context', '').not_.is_('justin_context', 'null').execute()
print(f"  With Justin context: {len(with_context.data)}")
if with_context.data:
    for c in with_context.data:
        print(f"    - {c['ted_name']}")

print("\nDone!")
