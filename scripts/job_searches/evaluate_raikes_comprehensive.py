#!/usr/bin/env python3
"""
Comprehensive AI evaluation for Raikes Foundation Executive Director role
Full detailed assessment matching Crankstart evaluation quality
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

# Washington and Oregon cities (comprehensive list)
washington_cities = [
    'Seattle', 'Bellevue', 'Tacoma', 'Spokane', 'Vancouver', 'Kent', 'Everett',
    'Renton', 'Federal Way', 'Yakima', 'Bellingham', 'Kirkland', 'Redmond',
    'Sammamish', 'Bothell', 'Issaquah', 'Mercer Island', 'Olympia', 'Bainbridge Island',
    'Woodinville', 'Edmonds', 'Lynnwood', 'Shoreline', 'Lake Forest Park',
    'Snoqualmie', 'Burien', 'Des Moines', 'Tukwila', 'SeaTac', 'Newcastle'
]

oregon_cities = [
    'Portland', 'Eugene', 'Salem', 'Gresham', 'Hillsboro', 'Beaverton', 'Bend',
    'Medford', 'Springfield', 'Corvallis', 'Albany', 'Tigard', 'Lake Oswego',
    'Keizer', 'Grants Pass', 'Oregon City', 'McMinnville', 'Ashland', 'Tualatin'
]

full_job_description = """
RAIKES FOUNDATION EXECUTIVE DIRECTOR

ORGANIZATION CONTEXT:
The Raikes Foundation is a spend-down foundation established by Trustees Tricia and Jeff Raikes (former Microsoft 
executives and philanthropists). With approximately $300M+ in assets and planning to sunset by 2040, the Foundation 
has both the opportunity and responsibility to act boldly and with urgency. The Foundation believes that the future 
of our country depends on young people—and that lasting change happens when they are at the center of shaping it.

FOCUS AREAS:
1. Housing Stability for Youth: Ensuring every young person has a safe, stable place to call home
2. Education: Building a fair and future-ready public education system that enables all young people to thrive
3. Resourcing Democracy: Expanding youth voice and power in the democratic processes that impact their futures

THE ROLE:
- Reports to: Tricia and Jeff Raikes, Trustees
- Direct Reports: 4 Senior Directors (Youth Serving Systems, Resourcing Democracy, Communications, Chief of Staff)
- Total Staff: 15 employees
- Location: Seattle, WA (hybrid 2-3 days/week in office)
- Travel: 25-40%
- Compensation: $325,000 - $375,000

KEY RESPONSIBILITIES:

Foundation Strategy:
- Translate Trustees' values and vision into bold strategies and operational plans
- Develop capital allocation and financial modeling for spend-down timeline
- Ensure adaptive, reflective strategies that achieve durable systems change
- Integrate youth and lived experience as co-creators in solutions

Organizational Leadership:
- Monitor programmatic and operational activities across all focus areas
- Establish clear role boundaries and decision rights
- Partner with Trustees on long-term organizational design for sustained impact beyond sunset
- Align annual plans with appropriate resource levels

Team Development:
- Attract, nurture, coach, and motivate a highly capable team
- Organize senior leadership as true strategic partners
- Act as coach and multiplier for senior directors
- Foster collaborative, inclusive culture grounded in equity

External Partnerships:
- Represent Foundation alongside or in place of Trustees
- Be visible leader in philanthropy and social impact sectors
- Catalyze co-investment and field resourcing
- Partner with Communications to amplify Foundation's influence

REQUIRED EXPERIENCE:
- Significant C-level or organizational leadership experience
- Track record of managing high-performing teams (15+ people)
- Strategic planning and financial modeling expertise
- Experience with philanthropic tools (policy/advocacy, grantmaking)
- Systems-change and measurable impact experience
- Board/trustee relationship management

IDEAL CANDIDATE PROFILE:
- Current or former foundation CEO/Executive Director
- Experience with spend-down foundations highly valued
- Deep commitment to equity, especially youth of color and LGBTQ youth
- Experience in housing, education, or democracy/civic engagement
- Seattle-based or willing to relocate
- High emotional intelligence and collaborative leadership
- Able to challenge thinking while building trust
"""

def evaluate_executive_detailed(candidate: Dict) -> Dict:
    """Provide comprehensive executive evaluation with detailed rationale"""
    
    # Build comprehensive profile including enrichment data
    candidate_profile = f"""
    Name: {candidate.get('first_name', '')} {candidate.get('last_name', '')}
    Email: {candidate.get('email', 'Not available')}
    Location: {candidate.get('city', 'Unknown')}, {candidate.get('state', '')}
    Current Company: {candidate.get('company', 'Unknown')}
    Current Position: {candidate.get('position', 'Unknown')}
    LinkedIn Headline: {candidate.get('headline', 'None')}
    
    Professional Summary: 
    {(candidate.get('summary', '') or '')[:1000]}
    
    LinkedIn URL: {candidate.get('linkedin_url', 'Not available')}
    """
    
    # Add enrichment data if available
    if candidate.get('enrich_person_from_profile'):
        enrich = candidate['enrich_person_from_profile']
        if isinstance(enrich, dict):
            candidate_profile += f"\n\nAdditional Profile Data: {json.dumps(enrich, indent=2)[:800]}"
    
    prompt = f"""
    You are an executive search consultant evaluating candidates for the Raikes Foundation Executive Director role.
    This is a critical C-level position requiring exceptional leadership experience.
    
    FULL JOB DESCRIPTION:
    {full_job_description}
    
    CANDIDATE PROFILE:
    {candidate_profile}
    
    Provide a comprehensive evaluation. Return detailed JSON:
    {{
        "overall_recommendation": "strong_yes|yes|maybe|no",
        "fit_score": <1-10, where 8+ is excellent for this role>,
        "confidence_level": "high|medium|low",
        
        "seniority_assessment": {{
            "is_executive_level": <true/false>,
            "current_level": "C-suite|Senior VP|VP|Senior Director|Director|Manager|Other",
            "years_leadership": "<estimated years in leadership roles>",
            "largest_team_managed": "<estimate of largest team size managed>",
            "budget_managed": "<estimate if evident>",
            "readiness": "ready_now|ready_with_development|not_ready"
        }},
        
        "relevant_experience": {{
            "has_foundation_experience": <true/false>,
            "has_ceo_ed_experience": <true/false>,
            "has_youth_focus": <true/false>,
            "has_education_sector": <true/false>,
            "has_housing_homeless": <true/false>,
            "has_democracy_civic": <true/false>,
            "has_equity_dei_focus": <true/false>,
            "has_board_management": <true/false>,
            "has_spend_down_experience": <true/false>,
            "has_systems_change": <true/false>,
            "has_policy_advocacy": <true/false>,
            "has_seattle_connection": <true/false>
        }},
        
        "strengths": [
            "<specific strength highly relevant to this ED role>",
            "<another key strength with evidence>",
            "<third strength that differentiates them>"
        ],
        
        "gaps_or_concerns": [
            "<specific gap relative to role requirements>",
            "<another concern or development area>"
        ],
        
        "detailed_rationale": "<4-5 sentences providing thorough explanation of fit. Include specific evidence from their background. Explain why they would or wouldn't succeed in this particular role with these specific trustees and mission.>",
        
        "interview_priority": "immediate|high|medium|low",
        
        "interview_focus_areas": [
            "<specific area to probe in interview>",
            "<another critical topic to explore>",
            "<third area needing clarification>"
        ],
        
        "trustee_alignment": "<Assessment of likely chemistry with Jeff and Tricia Raikes based on background>",
        
        "relocation_likelihood": "already_local|likely|possible|unlikely",
        
        "network_value": "<Note any valuable connections, board positions, or influence in relevant sectors>",
        
        "compensation_fit": "within_range|might_need_higher|might_accept_lower|unknown"
    }}
    
    Be thorough and precise. Consider:
    - This is a $325-375k executive role requiring seasoned leadership
    - Must manage relationship with high-profile trustees (Jeff Raikes: former Microsoft President)
    - Spend-down timeline creates unique strategic challenges
    - Youth focus with equity lens is absolutely critical
    - Seattle location is strong preference
    - 25-40% travel requirement
    """
    
    try:
        response = openai_client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "You are a senior executive search consultant with deep knowledge of the nonprofit and foundation sectors. Be thorough, precise, and evidence-based. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1200
        )
        
        result_text = response.choices[0].message.content
        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0]
        elif '```' in result_text:
            result_text = result_text.split('```')[1].split('```')[0]
        
        return json.loads(result_text.strip())
    except Exception as e:
        print(f"  Error evaluating: {e}")
        return None

print("=" * 70)
print("RAIKES FOUNDATION EXECUTIVE DIRECTOR SEARCH")
print("Comprehensive Evaluation of Washington & Oregon Executives")
print("=" * 70)
print()

# Query all WA/OR contacts
print("Phase 1: Identifying executives in Washington and Oregon...")

# Query by cities
city_query = supabase.table('contacts').select(
    'id, first_name, last_name, email, linkedin_url, company, position, '
    'city, state, headline, summary, enrich_person_from_profile'
).in_('city', washington_cities + oregon_cities)

city_response = city_query.execute()

# Query by state
state_query = supabase.table('contacts').select(
    'id, first_name, last_name, email, linkedin_url, company, position, '
    'city, state, headline, summary, enrich_person_from_profile'
).in_('state', ['Washington', 'WA', 'Oregon', 'OR'])

state_response = state_query.execute()

# Combine and deduplicate
seen_ids = set()
all_candidates = []
for c in city_response.data + state_response.data:
    if c['id'] not in seen_ids:
        seen_ids.add(c['id'])
        all_candidates.append(c)

print(f"  Found {len(all_candidates)} total contacts in WA/OR")

# Executive-level keywords
exec_keywords = [
    'ceo', 'chief executive', 'executive director', 'president', 'vice president',
    'vp ', 'svp', 'evp', 'managing director', 'senior director', 'chief ',
    'head of', 'principal', 'partner', 'founder', 'board member', 'trustee'
]

# Sector keywords
sector_keywords = [
    'foundation', 'nonprofit', 'philanthrop', 'social', 'youth', 'education',
    'housing', 'homeless', 'democracy', 'civic', 'equity', 'justice', 'community',
    'grant', 'charitable', 'impact', 'advocacy', 'policy'
]

print("\nPhase 2: Filtering for executive-level candidates...")

filtered = []
for c in all_candidates:
    search_text = f"{c.get('company', '')} {c.get('position', '')} {c.get('headline', '')} {(c.get('summary', '') or '')[:500]}".lower()
    
    # Check for executive title
    has_exec = any(kw in search_text for kw in exec_keywords)
    if not has_exec:
        continue
    
    # Calculate relevance
    relevance = 0
    
    # Title scoring
    if 'executive director' in search_text or 'ceo' in search_text:
        relevance += 5
    if 'president' in search_text:
        relevance += 4
    if 'vice president' in search_text or 'vp ' in search_text:
        relevance += 3
    if 'senior director' in search_text or 'managing director' in search_text:
        relevance += 2
    
    # Sector scoring
    if 'foundation' in search_text:
        relevance += 5
    if 'youth' in search_text:
        relevance += 4
    if 'education' in search_text:
        relevance += 3
    if 'housing' in search_text or 'homeless' in search_text:
        relevance += 3
    if 'nonprofit' in search_text or 'philanthrop' in search_text:
        relevance += 3
    if 'equity' in search_text or 'justice' in search_text:
        relevance += 2
    if 'democracy' in search_text or 'civic' in search_text:
        relevance += 2
    
    # Location bonus
    if 'seattle' in c.get('city', '').lower():
        relevance += 2
    
    c['relevance_score'] = relevance
    filtered.append(c)

# Sort by relevance
filtered.sort(key=lambda x: x['relevance_score'], reverse=True)

print(f"  Identified {len(filtered)} executive-level candidates")

# Evaluate top candidates
print(f"\nPhase 3: Comprehensive AI evaluation of top 25 executives...")
print("  (This will take several minutes for thorough analysis)")
print()

evaluated = []
limit = min(25, len(filtered))

for i, candidate in enumerate(filtered[:limit], 1):
    print(f"  [{i:2}/{limit}] Evaluating: {candidate['first_name']} {candidate.get('last_name', '')} "
          f"({candidate.get('position', 'N/A')} at {candidate.get('company', 'N/A')})")
    
    evaluation = evaluate_executive_detailed(candidate)
    if evaluation:
        candidate['ai_evaluation'] = evaluation
        evaluated.append(candidate)
        
        # Show result
        rec = evaluation['overall_recommendation']
        score = evaluation['fit_score']
        priority = evaluation.get('interview_priority', 'low')
        
        status = "✨ STRONG YES" if rec == 'strong_yes' else "✅ YES" if rec == 'yes' else "🤔 MAYBE" if rec == 'maybe' else "❌ NO"
        print(f"       Result: {status} | Score: {score}/10 | Priority: {priority}")
    else:
        print(f"       Result: ⚠️ Evaluation failed")
    
    # Pause every 5 to avoid rate limits
    if i % 5 == 0 and i < limit:
        print("       [Brief pause for API rate limiting...]")
        time.sleep(2)

# Categorize results
strong_yes = [c for c in evaluated if c['ai_evaluation']['overall_recommendation'] == 'strong_yes']
yes_list = [c for c in evaluated if c['ai_evaluation']['overall_recommendation'] == 'yes']
maybe_list = [c for c in evaluated if c['ai_evaluation']['overall_recommendation'] == 'maybe']
no_list = [c for c in evaluated if c['ai_evaluation']['overall_recommendation'] == 'no']

# Sort by score and priority
strong_yes.sort(key=lambda x: (x['ai_evaluation']['fit_score'], 
                               x['ai_evaluation']['interview_priority'] == 'immediate'), reverse=True)
yes_list.sort(key=lambda x: x['ai_evaluation']['fit_score'], reverse=True)
maybe_list.sort(key=lambda x: x['ai_evaluation']['fit_score'], reverse=True)

# Display comprehensive results
print("\n" + "=" * 70)
print("EXECUTIVE SEARCH RESULTS")
print("=" * 70)

print(f"""
SUMMARY STATISTICS:
  • Total WA/OR contacts reviewed: {len(all_candidates):,}
  • Executive-level candidates identified: {len(filtered)}
  • Candidates evaluated in detail: {len(evaluated)}
  
EVALUATION RESULTS:
  • Strong Yes (Interview Immediately): {len(strong_yes)}
  • Yes (Strong Candidates): {len(yes_list)}
  • Maybe (Potential Fit): {len(maybe_list)}
  • No (Not Recommended): {len(no_list)}
""")

if strong_yes:
    print("=" * 70)
    print("🌟 PRIORITY CANDIDATES - INTERVIEW IMMEDIATELY")
    print("=" * 70)
    
    for idx, c in enumerate(strong_yes, 1):
        e = c['ai_evaluation']
        print(f"\n{idx}. {c['first_name']} {c.get('last_name', '')}")
        print("-" * 50)
        print(f"Current Role: {c.get('position', 'N/A')}")
        print(f"Organization: {c.get('company', 'N/A')}")
        print(f"Location: {c.get('city', 'N/A')}, {c.get('state', '')}")
        print(f"\nFit Score: {e['fit_score']}/10")
        print(f"Interview Priority: {e['interview_priority'].upper()}")
        print(f"Confidence Level: {e.get('confidence_level', 'medium')}")
        
        # Leadership profile
        seniority = e['seniority_assessment']
        print(f"\nLeadership Profile:")
        print(f"  • Current Level: {seniority['current_level']}")
        print(f"  • Years in Leadership: {seniority['years_leadership']}")
        print(f"  • Largest Team Managed: {seniority.get('largest_team_managed', 'Unknown')}")
        print(f"  • Readiness: {seniority['readiness']}")
        
        # Relevant experience
        exp = e['relevant_experience']
        print(f"\nRelevant Experience:")
        exp_items = []
        if exp.get('has_foundation_experience'): exp_items.append("Foundation/Philanthropy")
        if exp.get('has_ceo_ed_experience'): exp_items.append("CEO/Executive Director")
        if exp.get('has_youth_focus'): exp_items.append("Youth Programs")
        if exp.get('has_education_sector'): exp_items.append("Education")
        if exp.get('has_housing_homeless'): exp_items.append("Housing/Homelessness")
        if exp.get('has_democracy_civic'): exp_items.append("Democracy/Civic Engagement")
        if exp.get('has_equity_dei_focus'): exp_items.append("Equity/DEI Leadership")
        if exp.get('has_board_management'): exp_items.append("Board Management")
        if exp.get('has_spend_down_experience'): exp_items.append("✨ Spend-down Experience")
        if exp.get('has_systems_change'): exp_items.append("Systems Change")
        if exp.get('has_seattle_connection'): exp_items.append("📍 Seattle Connection")
        
        for item in exp_items:
            print(f"  ✓ {item}")
        
        # Detailed rationale
        print(f"\nDetailed Assessment:")
        print(f"{e['detailed_rationale']}")
        
        # Strengths
        print(f"\nKey Strengths:")
        for s in e['strengths']:
            print(f"  • {s}")
        
        # Areas to explore
        if e.get('gaps_or_concerns'):
            print(f"\nAreas to Explore in Interview:")
            for concern in e['gaps_or_concerns']:
                print(f"  • {concern}")
        
        # Interview focus
        if e.get('interview_focus_areas'):
            print(f"\nInterview Focus Areas:")
            for focus in e['interview_focus_areas'][:3]:
                print(f"  • {focus}")
        
        # Additional insights
        if e.get('trustee_alignment'):
            print(f"\nTrustee Alignment: {e['trustee_alignment']}")
        if e.get('network_value'):
            print(f"Network Value: {e['network_value']}")
        print(f"Relocation: {e.get('relocation_likelihood', 'Unknown')}")
        print(f"Compensation: {e.get('compensation_fit', 'Unknown')}")
        
        # Contact information
        print(f"\nContact Information:")
        if c.get('email'):
            print(f"  📧 {c['email']}")
        if c.get('linkedin_url'):
            print(f"  🔗 {c['linkedin_url']}")
        
        # LinkedIn headline
        if c.get('headline'):
            print(f"  💼 {c['headline']}")

if yes_list:
    print("\n" + "=" * 70)
    print("✅ STRONG CANDIDATES - RECOMMENDED FOR INTERVIEW")
    print("=" * 70)
    
    for idx, c in enumerate(yes_list[:10], 1):
        e = c['ai_evaluation']
        print(f"\n{idx}. {c['first_name']} {c.get('last_name', '')}")
        print(f"   {c.get('position', 'N/A')} at {c.get('company', 'N/A')}")
        print(f"   {c.get('city', 'N/A')}, {c.get('state', '')}")
        print(f"   Score: {e['fit_score']}/10 | Priority: {e['interview_priority']}")
        print(f"   {e['seniority_assessment']['current_level']} with {e['seniority_assessment']['years_leadership']} experience")
        print(f"\n   Assessment: {e['detailed_rationale'][:250]}...")
        if c.get('email'):
            print(f"   📧 {c['email']}")

if maybe_list:
    print("\n" + "=" * 70)
    print("🤔 POTENTIAL CANDIDATES - CONSIDER IF NEEDED")
    print("=" * 70)
    
    for idx, c in enumerate(maybe_list[:5], 1):
        e = c['ai_evaluation']
        print(f"\n{idx}. {c['first_name']} {c.get('last_name', '')}")
        print(f"   {c.get('position', 'N/A')} at {c.get('company', 'N/A')}")
        print(f"   Score: {e['fit_score']}/10")
        print(f"   Main Concerns: {', '.join(e.get('gaps_or_concerns', [])[:2])}")

# Save comprehensive results
print("\n" + "=" * 70)
print("SAVING RESULTS")
print("=" * 70)

results = {
    'search_date': time.strftime('%Y-%m-%d %H:%M:%S'),
    'position': 'Raikes Foundation Executive Director',
    'location': 'Seattle, WA',
    'salary_range': '$325,000 - $375,000',
    'search_firm': 'Viewcrest Advisors (Kathleen Yazbak)',
    'summary': {
        'total_wa_or_contacts': len(all_candidates),
        'executives_identified': len(filtered),
        'evaluated': len(evaluated),
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

output_file = 'raikes_executive_comprehensive.json'
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✅ Full results saved to: {output_file}")
print(f"📧 Share top candidates with: kathleen@viewcrestadvisors.com")
print("\n✨ Executive search complete!")