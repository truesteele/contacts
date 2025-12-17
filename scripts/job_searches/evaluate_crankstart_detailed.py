#!/usr/bin/env python3
"""
Detailed evaluation for Crankstart candidates with comprehensive rationale
Optimized for performance with batch processing
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

# Core Bay Area cities for focused search
bay_area_cities = [
    'San Francisco', 'Oakland', 'Berkeley', 'Palo Alto', 'Mountain View',
    'San Jose', 'Redwood City', 'San Mateo', 'Menlo Park', 'Burlingame',
    'Sunnyvale', 'Santa Clara', 'Cupertino', 'Fremont', 'Walnut Creek'
]

def evaluate_candidate_detailed(candidate: Dict) -> Dict:
    """Provide detailed evaluation with comprehensive rationale"""
    
    prompt = f"""
    Evaluate this candidate for Crankstart Manager - Grants and Operations role ($165-180k, mid-level, 3-7 years exp).
    
    CANDIDATE:
    Name: {candidate.get('first_name', '')} {candidate.get('last_name', '')}
    Company: {candidate.get('company', 'Unknown')}
    Position: {candidate.get('position', 'Unknown')}
    Location: {candidate.get('city', 'Unknown')}
    Headline: {candidate.get('headline', 'None')}
    Summary: {(candidate.get('summary', '') or '')[:400]}
    
    ROLE REQUIREMENTS:
    - Mid-level grants and operations manager at $4B foundation
    - Must have foundation/nonprofit experience
    - Ideally has Salesforce and grants management experience
    - NOT senior executive level (no VPs, Directors, C-suite)
    
    Return detailed JSON evaluation:
    {{
        "recommendation": "strong_yes|yes|maybe|no",
        "fit_score": <1-10>,
        "seniority_level": "appropriate|too_senior|too_junior",
        "years_experience": "<estimate>",
        "key_qualifications": {{
            "foundation_experience": <true/false>,
            "grants_experience": <true/false>,
            "operations_experience": <true/false>,
            "salesforce_experience": <true/false>
        }},
        "strengths": ["<strength1>", "<strength2>"],
        "concerns": ["<concern1>", "<concern2>"],
        "detailed_rationale": "<2-3 sentences explaining fit>",
        "interview_priority": "high|medium|low"
    }}
    
    Be strict on seniority - reject VPs, Directors, senior consultants.
    """
    
    try:
        response = openai_client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "You are an expert recruiter. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        if '```' in result:
            result = result.split('```')[1].replace('json', '').strip()
        return json.loads(result)
    except Exception as e:
        print(f"  Error: {e}")
        return None

print("🎯 Detailed Crankstart Candidate Evaluation")
print("=" * 60)

# Query Bay Area candidates with relevant experience
query = supabase.table('contacts').select(
    'id, first_name, last_name, email, linkedin_url, company, position, '
    'city, state, headline, summary'
).in_('city', bay_area_cities)

response = query.execute()
all_candidates = response.data

print(f"Found {len(all_candidates)} Bay Area contacts")

# Strong filtering for relevant candidates
relevant_keywords = [
    'foundation', 'nonprofit', 'grant', 'philanthrop', 'social',
    'operations', 'salesforce', 'program', 'manager', 'officer',
    'analyst', 'coordinator', 'administrator'
]

senior_titles = [
    'ceo', 'chief', 'president', 'vice president', 'vp ', 'director',
    'head of', 'principal', 'partner', 'founder', 'executive'
]

# Filter candidates
print("Filtering for relevant mid-level professionals...")
filtered = []
for c in all_candidates:
    summary_text = c.get('summary', '') or ''
    text = f"{c.get('company', '')} {c.get('position', '')} {c.get('headline', '')} {summary_text[:200]}".lower()
    
    # Skip senior people
    if any(title in text for title in senior_titles):
        continue
    
    # Check for relevant experience
    relevance_score = sum(1 for kw in relevant_keywords if kw in text)
    
    # Boost for specific keywords
    if 'grant' in text: relevance_score += 2
    if 'foundation' in text: relevance_score += 2
    if 'salesforce' in text: relevance_score += 3
    if 'program officer' in text: relevance_score += 3
    
    if relevance_score >= 2:  # Must have at least 2 keyword matches
        c['relevance_score'] = relevance_score
        filtered.append(c)

# Sort by relevance
filtered.sort(key=lambda x: x['relevance_score'], reverse=True)

print(f"Found {len(filtered)} potentially relevant candidates")
print(f"Evaluating top 25 candidates in detail...\n")

# Evaluate top candidates
evaluated = []
limit = min(25, len(filtered))

for i, candidate in enumerate(filtered[:limit], 1):
    print(f"{i}/{limit}: {candidate['first_name']} {candidate.get('last_name', '')} "
          f"- {candidate.get('position', 'N/A')} at {candidate.get('company', 'N/A')}")
    
    evaluation = evaluate_candidate_detailed(candidate)
    if evaluation:
        candidate['evaluation'] = evaluation
        evaluated.append(candidate)
        
        # Show immediate feedback
        rec = evaluation['recommendation']
        score = evaluation['fit_score']
        if rec == 'strong_yes':
            print(f"  ✨ STRONG YES - Score: {score}/10")
        elif rec == 'yes':
            print(f"  ✅ YES - Score: {score}/10")
        elif rec == 'maybe':
            print(f"  🤔 Maybe - Score: {score}/10")
        else:
            print(f"  ❌ No - Score: {score}/10")
    
    # Brief pause to avoid API rate limits
    if i % 5 == 0:
        time.sleep(1)

# Categorize results
strong_yes = [c for c in evaluated if c['evaluation']['recommendation'] == 'strong_yes']
yes_list = [c for c in evaluated if c['evaluation']['recommendation'] == 'yes']
maybe_list = [c for c in evaluated if c['evaluation']['recommendation'] == 'maybe']
no_list = [c for c in evaluated if c['evaluation']['recommendation'] == 'no']

# Sort by score
strong_yes.sort(key=lambda x: x['evaluation']['fit_score'], reverse=True)
yes_list.sort(key=lambda x: x['evaluation']['fit_score'], reverse=True)

# Display detailed results
print("\n" + "=" * 60)
print("DETAILED EVALUATION RESULTS")
print("=" * 60)

print(f"\nSummary: {len(strong_yes)} Strong Yes | {len(yes_list)} Yes | "
      f"{len(maybe_list)} Maybe | {len(no_list)} No")

if strong_yes:
    print(f"\n🌟 STRONG YES - PRIORITY INTERVIEWS ({len(strong_yes)})")
    print("-" * 60)
    for c in strong_yes:
        e = c['evaluation']
        print(f"\n{c['first_name']} {c.get('last_name', '')}")
        print(f"Current: {c.get('company', 'N/A')} - {c.get('position', 'N/A')}")
        print(f"Location: {c.get('city', 'N/A')}")
        print(f"Score: {e['fit_score']}/10 | Experience: {e['years_experience']}")
        print(f"\nRationale: {e['detailed_rationale']}")
        print(f"\nStrengths:")
        for s in e['strengths']:
            print(f"  • {s}")
        
        quals = e['key_qualifications']
        print(f"\nQualifications:")
        if quals.get('foundation_experience'): print("  ✓ Foundation experience")
        if quals.get('grants_experience'): print("  ✓ Grants management")
        if quals.get('operations_experience'): print("  ✓ Operations experience")
        if quals.get('salesforce_experience'): print("  ✓ Salesforce")
        
        if e.get('concerns'):
            print(f"\nAreas to explore:")
            for concern in e['concerns']:
                print(f"  • {concern}")
        
        if c.get('email'):
            print(f"\n📧 {c['email']}")
        if c.get('linkedin_url'):
            print(f"🔗 {c['linkedin_url']}")

if yes_list:
    print(f"\n✅ YES - RECOMMENDED ({len(yes_list)})")
    print("-" * 60)
    for c in yes_list[:10]:
        e = c['evaluation']
        print(f"\n{c['first_name']} {c.get('last_name', '')}")
        print(f"  {c.get('company', 'N/A')} - {c.get('position', 'N/A')}")
        print(f"  Score: {e['fit_score']}/10 | {e['years_experience']} experience")
        print(f"  {e['detailed_rationale']}")
        if c.get('email'):
            print(f"  📧 {c['email']}")

if maybe_list:
    print(f"\n🤔 MAYBE - POTENTIAL ({len(maybe_list)})")
    print("-" * 60)
    for c in maybe_list[:5]:
        e = c['evaluation']
        print(f"\n{c['first_name']} {c.get('last_name', '')}")
        print(f"  {c.get('company', 'N/A')} - {c.get('position', 'N/A')}")
        print(f"  Score: {e['fit_score']}/10")
        print(f"  Concerns: {', '.join(e.get('concerns', [])[:2])}")

# Save detailed results
results = {
    'evaluation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
    'job': 'Crankstart Manager - Grants and Operations',
    'salary_range': '$165,000 - $180,000',
    'summary': {
        'total_evaluated': len(evaluated),
        'strong_yes': len(strong_yes),
        'yes': len(yes_list),
        'maybe': len(maybe_list),
        'no': len(no_list)
    },
    'candidates': {
        'strong_yes': strong_yes,
        'yes': yes_list,
        'maybe': maybe_list
    }
}

with open('crankstart_detailed_evaluation.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n💾 Detailed results saved to crankstart_detailed_evaluation.json")
print("✨ Evaluation complete!")