#!/usr/bin/env python3
"""
Philanthropy Network Connections for Kavell Brown
Finding program officers and directors at foundations with economic justice focus
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI
from typing import Dict
import time

# Load environment variables
load_dotenv()

# Initialize clients
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)
openai_client = OpenAI(api_key=os.environ.get('OPENAI_APIKEY'))

# Kavell's target profile
kavell_profile = """
KAVELL BROWN - TRANSITION GOALS:
- Currently: Corporate philanthropy at LinkedIn
- Target: Senior Program Officer role in private or institutional philanthropy
- Focus Areas: Anti-poverty, economic justice, economic mobility, workforce development
- Goal: Learn day-to-day realities and idiosyncrasies of foundation program officer roles
- Especially interested in: Economic justice-related cause areas
- Values: Justice-minded, equity-focused
"""

def evaluate_connection_fit(candidate: Dict) -> Dict:
    """Evaluate how good a connection this would be for Kavell"""

    prompt = f"""
    Evaluate this contact as a potential connection for Kavell Brown.

    KAVELL'S PROFILE:
    {kavell_profile}

    POTENTIAL CONNECTION:
    Name: {candidate.get('first_name', '')} {candidate.get('last_name', '')}
    Company: {candidate.get('company', 'Unknown')}
    Position: {candidate.get('position', 'Unknown')}
    Location: {candidate.get('city', 'Unknown')}, {candidate.get('state', '')}
    Headline: {candidate.get('headline', 'None')}
    Summary: {(candidate.get('summary', '') or '')[:600]}

    Evaluate and return JSON:
    {{
        "relevance_score": <1-10, how relevant to Kavell's goals>,
        "connection_value": "high|medium|low",
        "why_connect": "<2-3 sentences on why Kavell should connect with this person>",
        "talking_points": ["<point 1>", "<point 2>"],
        "role_type": "program_officer|program_director|foundation_executive|philanthropy_adjacent|other",
        "economic_justice_alignment": <1-10>,
        "intro_priority": "immediate|high|medium|low"
    }}
    """

    try:
        response = openai_client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "You are a networking expert helping someone transition into foundation philanthropy work. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        result = response.choices[0].message.content
        if '```json' in result:
            result = result.split('```json')[1].split('```')[0]
        elif '```' in result:
            result = result.split('```')[1].split('```')[0]
        return json.loads(result.strip())
    except Exception as e:
        print(f"  Error: {e}")
        return None


print("=" * 80)
print("PHILANTHROPY NETWORK CONNECTIONS FOR KAVELL BROWN")
print("Finding Program Officers & Directors with Economic Justice Focus")
print("=" * 80)
print()

# Query 1: Program Officers and Directors at Foundations
print("Phase 1: Finding Program Officers and Directors at Foundations...")

foundation_query = supabase.table('contacts').select(
    'id, first_name, last_name, email, linkedin_url, company, position, '
    'city, state, headline, summary'
).or_(
    'position.ilike.%program officer%,'
    'position.ilike.%program director%'
).ilike('company', '%foundation%')

foundation_response = foundation_query.execute()
print(f"  Found {len(foundation_response.data)} program officers/directors at foundations")

# Query 2: Economic Justice Focus
print("\nPhase 2: Finding contacts with economic justice focus...")

justice_query = supabase.table('contacts').select(
    'id, first_name, last_name, email, linkedin_url, company, position, '
    'city, state, headline, summary'
).or_(
    'position.ilike.%economic%,'
    'headline.ilike.%economic justice%,'
    'headline.ilike.%economic mobility%,'
    'headline.ilike.%workforce%,'
    'headline.ilike.%anti-poverty%,'
    'summary.ilike.%economic mobility%,'
    'summary.ilike.%economic justice%'
)

justice_response = justice_query.execute()
print(f"  Found {len(justice_response.data)} contacts with economic justice focus")

# Query 3: Philanthropy professionals more broadly
print("\nPhase 3: Finding philanthropy professionals...")

philanthropy_query = supabase.table('contacts').select(
    'id, first_name, last_name, email, linkedin_url, company, position, '
    'city, state, headline, summary'
).or_(
    'position.ilike.%philanthrop%,'
    'headline.ilike.%philanthrop%,'
    'headline.ilike.%grantmak%,'
    'position.ilike.%grantmak%'
)

philanthropy_response = philanthropy_query.execute()
print(f"  Found {len(philanthropy_response.data)} philanthropy professionals")

# Combine and deduplicate
seen_ids = set()
all_candidates = []
for c in foundation_response.data + justice_response.data + philanthropy_response.data:
    if c['id'] not in seen_ids:
        seen_ids.add(c['id'])
        all_candidates.append(c)

print(f"\nTotal unique candidates: {len(all_candidates)}")

# Evaluate top candidates
print(f"\nPhase 4: AI evaluation of candidates for Kavell's network...")
print()

evaluated = []
limit = min(40, len(all_candidates))

for i, candidate in enumerate(all_candidates[:limit], 1):
    print(f"  [{i:2}/{limit}] Evaluating: {candidate['first_name']} {candidate.get('last_name', '')} "
          f"({candidate.get('position', 'N/A')} at {candidate.get('company', 'N/A')})")

    evaluation = evaluate_connection_fit(candidate)
    if evaluation:
        candidate['evaluation'] = evaluation
        evaluated.append(candidate)

        score = evaluation['relevance_score']
        priority = evaluation.get('intro_priority', 'low')
        value = evaluation.get('connection_value', 'low')

        print(f"       Score: {score}/10 | Value: {value} | Priority: {priority}")
    else:
        print(f"       ⚠️ Evaluation failed")

    if i % 5 == 0 and i < limit:
        time.sleep(1)

# Categorize by priority
immediate = [c for c in evaluated if c['evaluation'].get('intro_priority') == 'immediate']
high = [c for c in evaluated if c['evaluation'].get('intro_priority') == 'high']
medium = [c for c in evaluated if c['evaluation'].get('intro_priority') == 'medium']

# Sort each by relevance score
immediate.sort(key=lambda x: x['evaluation']['relevance_score'], reverse=True)
high.sort(key=lambda x: x['evaluation']['relevance_score'], reverse=True)
medium.sort(key=lambda x: x['evaluation']['relevance_score'], reverse=True)

# Display results
print("\n" + "=" * 80)
print("RECOMMENDED CONNECTIONS FOR KAVELL")
print("=" * 80)

if immediate:
    print("\n🌟 IMMEDIATE INTRODUCTIONS (Highest Priority)")
    print("-" * 60)
    for idx, c in enumerate(immediate, 1):
        e = c['evaluation']
        print(f"\n{idx}. {c['first_name']} {c.get('last_name', '')}")
        print(f"   Role: {c.get('position', 'N/A')}")
        print(f"   Organization: {c.get('company', 'N/A')}")
        print(f"   Location: {c.get('city', 'N/A')}, {c.get('state', '')}")
        print(f"   Relevance: {e['relevance_score']}/10 | Economic Justice Alignment: {e.get('economic_justice_alignment', 'N/A')}/10")
        print(f"\n   Why Connect: {e['why_connect']}")
        if e.get('talking_points'):
            print(f"   Talking Points:")
            for tp in e['talking_points']:
                print(f"     • {tp}")
        if c.get('email'):
            print(f"   📧 {c['email']}")
        if c.get('linkedin_url'):
            print(f"   🔗 {c['linkedin_url']}")

if high:
    print("\n\n✅ HIGH PRIORITY CONNECTIONS")
    print("-" * 60)
    for idx, c in enumerate(high[:10], 1):
        e = c['evaluation']
        print(f"\n{idx}. {c['first_name']} {c.get('last_name', '')}")
        print(f"   {c.get('position', 'N/A')} at {c.get('company', 'N/A')}")
        print(f"   Relevance: {e['relevance_score']}/10")
        print(f"   Why: {e['why_connect']}")
        if c.get('email'):
            print(f"   📧 {c['email']}")

if medium:
    print("\n\n🤔 MEDIUM PRIORITY CONNECTIONS")
    print("-" * 60)
    for idx, c in enumerate(medium[:5], 1):
        e = c['evaluation']
        print(f"\n{idx}. {c['first_name']} {c.get('last_name', '')} - {c.get('position', 'N/A')} at {c.get('company', 'N/A')}")
        print(f"   Why: {e['why_connect']}")

# Save results
results = {
    'search_date': time.strftime('%Y-%m-%d %H:%M:%S'),
    'purpose': 'Philanthropy network connections for Kavell Brown',
    'target_role': 'Senior Program Officer in private/institutional philanthropy',
    'focus_areas': ['anti-poverty', 'economic justice', 'economic mobility', 'workforce development'],
    'summary': {
        'total_candidates': len(all_candidates),
        'evaluated': len(evaluated),
        'immediate_priority': len(immediate),
        'high_priority': len(high),
        'medium_priority': len(medium)
    },
    'connections': {
        'immediate': immediate,
        'high': high,
        'medium': medium
    }
}

output_file = 'kavell_philanthropy_connections.json'
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n\n✅ Results saved to: {output_file}")
print("✨ Connection search complete!")
