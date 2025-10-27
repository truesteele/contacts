#!/usr/bin/env python3
"""
Comprehensive evaluation for Catalyst Exchange Senior Fellow, State Strategy role
Designed to find candidates with state government, policy, and cross-sector partnership experience
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

# Target locations (remote-friendly role, but focus on U.S.-based candidates)
# Prioritize candidates in state government hubs and education/workforce policy centers
priority_cities = [
    # DC area (state policy hub)
    'Washington', 'Arlington', 'Alexandria', 'Bethesda', 'Silver Spring',
    # Major state capitals
    'Sacramento', 'Albany', 'Boston', 'Austin', 'Denver', 'Atlanta', 'Phoenix',
    'Columbus', 'Indianapolis', 'Madison', 'Lansing', 'Raleigh', 'Nashville',
    # Education policy centers
    'New York', 'Chicago', 'Los Angeles', 'San Francisco', 'Seattle', 'Philadelphia',
    'Baltimore', 'San Diego', 'Portland', 'Minneapolis'
]

full_job_description = """
CATALYST EXCHANGE - SENIOR FELLOW, STATE STRATEGY

ORGANIZATION CONTEXT:
Catalyst Exchange is a national nonprofit dedicated to helping organizations build capacity and deepen
their impact by connecting them to expertise, resources, and hands-on support they need to drive
transformational outcomes for students, families, and communities. Founded and led by a woman of color,
with a strong equity stance. Since 2020, served 1,500+ organizations with 94% meeting project goals.

THE ROLE:
- Reports to: Vice President, Strategy & Services
- Location: Remote (U.S.-based)
- Travel: 1-2 times per quarter
- Compensation: $170,000 - $180,000
- Contract: Fixed-term position ending June 30, 2027

KEY RESPONSIBILITIES:

State Engagement:
- Serve as trusted advisor to state agency staff in scoping high-leverage technical assistance projects
- Support development of project pipelines aligned with state policy priorities, budget constraints, and implementation timelines
- Ensure smaller satellite projects connect to broader strategies and are sequenced for success

TA Infrastructure Design and Oversight:
- Ensure states can deploy TA dollars efficiently with clear oversight, deliverables tracking, milestone-based payments
- Identify opportunities to braid philanthropic and public funding
- Support provider vetting and ensure strong project outcomes

Strategic Thought Partnership:
- Oversee data collection and synthesis of feedback from state leaders and TA providers
- Identify cross-state trends, challenges, and bright spots
- Work with internal/external colleagues to ensure coherence across state-level engagements
- Contribute thought partnership to strengthen internal systems

Management:
- Coach and support direct reports in communicative, inclusive, results-driven culture
- Support professional growth by aligning responsibilities with growth goals
- Establish systems, structures, and recurring meetings for open communication

KEY QUALIFICATIONS:
- 10+ years professional experience, including leadership roles in state government, public sector innovation,
  education systems, or cross-sector partnerships
- Deep knowledge of state-level levers for economic mobility (workforce alignment, place-based strategies,
  cradle-to-career pipelines)
- Consulting experience with state/federal bodies and knowledge of how contracts are structured
- Strong advisory and facilitation skills with senior public-sector leaders and funders
- Proven ability to manage complex, multi-stakeholder initiatives involving contracts and data collection
- Comfort operating in ambiguity and building systems in start-up or pilot contexts
- Excellent communication skills with learning orientation and commitment to equity

IDEAL CANDIDATE:
- Has worked directly in state government (executive branch, governor's office, state agencies)
- Experience with education and/or workforce development policy
- Background in technical assistance, capacity building, or consulting to government
- Understanding of state budget cycles, procurement, and implementation challenges
- Proven track record with economic mobility initiatives
- Strong equity lens, particularly for youth of color and marginalized communities
- Comfortable being customer-facing advisor to state agency leaders
- Can translate policy priorities into actionable TA projects
"""

def evaluate_candidate_detailed(candidate: Dict) -> Dict:
    """Provide comprehensive evaluation with detailed rationale"""

    prompt = f"""
    Evaluate this candidate for Catalyst Exchange Senior Fellow, State Strategy role
    ($170-180k, 10+ years exp, state government/policy background required).

    CANDIDATE:
    Name: {candidate.get('first_name', '')} {candidate.get('last_name', '')}
    Company: {candidate.get('company', 'Unknown')}
    Position: {candidate.get('position', 'Unknown')}
    Location: {candidate.get('city', 'Unknown')}, {candidate.get('state', '')}
    Headline: {candidate.get('headline', 'None')}
    Summary: {(candidate.get('summary', '') or '')[:800]}

    ROLE REQUIREMENTS:
    - 10+ years in state government, public sector innovation, education systems, or cross-sector partnerships
    - MUST have deep state government knowledge (budget cycles, procurement, implementation)
    - Experience with economic mobility levers (workforce, education alignment, cradle-to-career)
    - Consulting experience with state/federal bodies
    - Advisory/facilitation skills with senior public-sector leaders
    - Complex multi-stakeholder initiative management
    - Strong equity commitment

    CRITICAL FIT FACTORS:
    1. Direct state government experience (not just working with government, but IN government)
    2. Economic mobility focus (education, workforce development, place-based strategies)
    3. Technical assistance or capacity building background
    4. Ability to advise senior state leaders (commissioners, deputies, chiefs of staff)
    5. Understanding of state contracting and procurement
    6. Multi-stakeholder project management
    7. Equity-centered approach

    Return detailed JSON evaluation:
    {{
        "recommendation": "strong_yes|yes|maybe|no",
        "fit_score": <1-10>,
        "confidence_level": "high|medium|low",

        "experience_assessment": {{
            "years_experience": "<estimate>",
            "has_state_govt_experience": <true/false>,
            "has_education_sector": <true/false>,
            "has_workforce_development": <true/false>,
            "has_economic_mobility_focus": <true/false>,
            "has_consulting_govt_bodies": <true/false>,
            "has_ta_capacity_building": <true/false>,
            "has_policy_advisory": <true/false>,
            "has_equity_dei_focus": <true/false>,
            "has_multi_stakeholder_mgmt": <true/false>,
            "has_public_sector_contracts": <true/false>
        }},

        "state_government_depth": "deep_insider|moderate_experience|limited_interaction|none",
        "sector_expertise": ["<primary sector>", "<secondary sector>"],

        "strengths": [
            "<specific strength highly relevant to this role>",
            "<another key strength with evidence>",
            "<third strength that differentiates them>"
        ],

        "gaps_or_concerns": [
            "<specific gap relative to role requirements>",
            "<another concern or development area>"
        ],

        "detailed_rationale": "<4-5 sentences providing thorough explanation of fit. Include specific evidence
        from their background. Explain why they would or wouldn't succeed in this particular role advising
        state agency leaders on technical assistance projects.>",

        "interview_priority": "immediate|high|medium|low",

        "interview_focus_areas": [
            "<specific area to probe in interview>",
            "<another critical topic to explore>",
            "<third area needing clarification>"
        ],

        "remote_work_fit": "excellent|good|uncertain",

        "advisor_capability": "<Assessment of ability to serve as trusted advisor to state commissioners and senior leaders>",

        "equity_alignment": "<Evidence of commitment to equity, especially for youth of color and marginalized communities>"
    }}

    Be thorough and precise. This role requires:
    - Someone who has been INSIDE state government, not just worked with it
    - Deep understanding of how states actually operate (budget, procurement, politics)
    - Ability to speak the language of state agency leaders
    - Experience with education/workforce policy at state level
    - Track record of complex TA/capacity building work
    - Must be comfortable as customer-facing advisor, not behind-the-scenes analyst

    REJECT candidates who are:
    - Pure researchers/academics without implementation experience
    - Federal-only experience without state government depth
    - Local government only (city/county) without state level work
    - Private sector consultants without deep public sector embedded experience
    - Too early-career (less than 10 years)
    """

    try:
        response = openai_client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "You are an expert recruiter specializing in state government, education policy, and public sector roles. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
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
print("CATALYST EXCHANGE - SENIOR FELLOW, STATE STRATEGY")
print("Comprehensive Candidate Evaluation")
print("=" * 80)
print()

# Query contacts with relevant state government and education policy experience
print("Phase 1: Identifying candidates with state government and policy experience...")

# Search in priority cities (state capitals and policy centers)
city_query = supabase.table('contacts').select(
    'id, first_name, last_name, email, linkedin_url, company, position, '
    'city, state, headline, summary'
).in_('city', priority_cities)

city_response = city_query.execute()

# Also search by state (to capture people in smaller cities who might have state roles)
state_query = supabase.table('contacts').select(
    'id, first_name, last_name, email, linkedin_url, company, position, '
    'city, state, headline, summary'
).not_.is_('state', 'null')

state_response = state_query.execute()

# Combine and deduplicate
seen_ids = set()
all_candidates = []
for c in city_response.data + state_response.data:
    if c['id'] not in seen_ids:
        seen_ids.add(c['id'])
        all_candidates.append(c)

print(f"  Found {len(all_candidates)} total contacts")

# Keywords for state government, education policy, and economic mobility
state_govt_keywords = [
    'state government', 'governor', 'state agency', 'state department',
    'state office', 'state policy', 'executive branch', 'legislative',
    'commissioner', 'deputy commissioner', 'chief of staff', 'state director',
    'state budget', 'procurement', 'state contract'
]

education_workforce_keywords = [
    'education', 'schools', 'k-12', 'early childhood', 'higher ed',
    'workforce', 'workforce development', 'career pathways', 'apprenticeship',
    'economic mobility', 'cradle to career', 'p-20', 'college access',
    'postsecondary', 'training', 'skills development'
]

capacity_building_keywords = [
    'technical assistance', 'capacity building', 'ta provider',
    'consulting', 'advisory', 'implementation support', 'coaching',
    'systems change', 'cross-sector', 'partnership', 'collaborative'
]

equity_keywords = [
    'equity', 'dei', 'inclusion', 'racial justice', 'social justice',
    'underserved', 'marginalized', 'disadvantaged', 'low-income', 'bipoc'
]

print("\nPhase 2: Filtering for relevant candidates...")

filtered = []
for c in all_candidates:
    search_text = f"{c.get('company', '')} {c.get('position', '')} {c.get('headline', '')} {(c.get('summary', '') or '')[:600]}".lower()

    # Calculate relevance score
    relevance = 0

    # State government experience (CRITICAL)
    state_govt_matches = sum(1 for kw in state_govt_keywords if kw in search_text)
    if state_govt_matches > 0:
        relevance += state_govt_matches * 5

    # Education/workforce experience
    edu_workforce_matches = sum(1 for kw in education_workforce_keywords if kw in search_text)
    if edu_workforce_matches > 0:
        relevance += edu_workforce_matches * 3

    # Capacity building/TA experience
    capacity_matches = sum(1 for kw in capacity_building_keywords if kw in search_text)
    if capacity_matches > 0:
        relevance += capacity_matches * 4

    # Equity focus
    equity_matches = sum(1 for kw in equity_keywords if kw in search_text)
    if equity_matches > 0:
        relevance += equity_matches * 2

    # Boost for specific high-value indicators
    if 'state government' in search_text or 'governor' in search_text:
        relevance += 8
    if 'economic mobility' in search_text:
        relevance += 6
    if 'technical assistance' in search_text or 'capacity building' in search_text:
        relevance += 5
    if 'workforce development' in search_text:
        relevance += 4
    if 'state policy' in search_text:
        relevance += 4

    # Require minimum threshold of relevant keywords
    if relevance >= 5:  # Must have substantial relevant experience
        c['relevance_score'] = relevance
        filtered.append(c)

# Sort by relevance
filtered.sort(key=lambda x: x['relevance_score'], reverse=True)

print(f"  Identified {len(filtered)} candidates with relevant experience")

# Evaluate top candidates
print(f"\nPhase 3: Comprehensive AI evaluation of top 30 candidates...")
print("  (This will take several minutes for thorough analysis)")
print()

evaluated = []
limit = min(30, len(filtered))

for i, candidate in enumerate(filtered[:limit], 1):
    print(f"  [{i:2}/{limit}] Evaluating: {candidate['first_name']} {candidate.get('last_name', '')} "
          f"({candidate.get('position', 'N/A')} at {candidate.get('company', 'N/A')})")

    evaluation = evaluate_candidate_detailed(candidate)
    if evaluation:
        candidate['ai_evaluation'] = evaluation
        evaluated.append(candidate)

        # Show result
        rec = evaluation['recommendation']
        score = evaluation['fit_score']
        priority = evaluation.get('interview_priority', 'low')

        status = "✨ STRONG YES" if rec == 'strong_yes' else "✅ YES" if rec == 'yes' else "�� MAYBE" if rec == 'maybe' else "❌ NO"
        print(f"       Result: {status} | Score: {score}/10 | Priority: {priority}")
    else:
        print(f"       Result: ⚠️ Evaluation failed")

    # Pause every 5 to avoid rate limits
    if i % 5 == 0 and i < limit:
        print("       [Brief pause for API rate limiting...]")
        time.sleep(2)

# Categorize results
strong_yes = [c for c in evaluated if c['ai_evaluation']['recommendation'] == 'strong_yes']
yes_list = [c for c in evaluated if c['ai_evaluation']['recommendation'] == 'yes']
maybe_list = [c for c in evaluated if c['ai_evaluation']['recommendation'] == 'maybe']
no_list = [c for c in evaluated if c['ai_evaluation']['recommendation'] == 'no']

# Sort by score and priority
strong_yes.sort(key=lambda x: (x['ai_evaluation']['fit_score'],
                               x['ai_evaluation']['interview_priority'] == 'immediate'), reverse=True)
yes_list.sort(key=lambda x: x['ai_evaluation']['fit_score'], reverse=True)
maybe_list.sort(key=lambda x: x['ai_evaluation']['fit_score'], reverse=True)

# Display comprehensive results
print("\n" + "=" * 80)
print("CANDIDATE EVALUATION RESULTS")
print("=" * 80)

print(f"""
SUMMARY STATISTICS:
  • Total contacts reviewed: {len(all_candidates):,}
  • Candidates with relevant keywords: {len(filtered)}
  • Candidates evaluated in detail: {len(evaluated)}

EVALUATION RESULTS:
  • Strong Yes (Interview Immediately): {len(strong_yes)}
  • Yes (Strong Candidates): {len(yes_list)}
  • Maybe (Potential Fit): {len(maybe_list)}
  • No (Not Recommended): {len(no_list)}
""")

if strong_yes:
    print("=" * 80)
    print("🌟 PRIORITY CANDIDATES - INTERVIEW IMMEDIATELY")
    print("=" * 80)

    for idx, c in enumerate(strong_yes, 1):
        e = c['ai_evaluation']
        print(f"\n{idx}. {c['first_name']} {c.get('last_name', '')}")
        print("-" * 60)
        print(f"Current Role: {c.get('position', 'N/A')}")
        print(f"Organization: {c.get('company', 'N/A')}")
        print(f"Location: {c.get('city', 'N/A')}, {c.get('state', '')}")
        print(f"\nFit Score: {e['fit_score']}/10")
        print(f"Interview Priority: {e['interview_priority'].upper()}")
        print(f"Confidence Level: {e.get('confidence_level', 'medium')}")

        # Experience profile
        exp_assess = e['experience_assessment']
        print(f"\nExperience Profile:")
        print(f"  • Years of Experience: {exp_assess['years_experience']}")
        print(f"  • State Government Depth: {e.get('state_government_depth', 'Unknown')}")
        print(f"  • Sector Expertise: {', '.join(e.get('sector_expertise', []))}")

        # Key qualifications
        print(f"\nKey Qualifications:")
        qualifications = []
        if exp_assess.get('has_state_govt_experience'): qualifications.append("✓ State Government Experience")
        if exp_assess.get('has_education_sector'): qualifications.append("✓ Education Sector")
        if exp_assess.get('has_workforce_development'): qualifications.append("✓ Workforce Development")
        if exp_assess.get('has_economic_mobility_focus'): qualifications.append("✓ Economic Mobility Focus")
        if exp_assess.get('has_consulting_govt_bodies'): qualifications.append("✓ Government Consulting")
        if exp_assess.get('has_ta_capacity_building'): qualifications.append("✓ TA/Capacity Building")
        if exp_assess.get('has_policy_advisory'): qualifications.append("✓ Policy Advisory")
        if exp_assess.get('has_equity_dei_focus'): qualifications.append("✓ Equity/DEI Focus")
        if exp_assess.get('has_multi_stakeholder_mgmt'): qualifications.append("✓ Multi-Stakeholder Management")
        if exp_assess.get('has_public_sector_contracts'): qualifications.append("✓ Public Sector Contracting")

        for qual in qualifications:
            print(f"  {qual}")

        # Detailed assessment
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
        if e.get('advisor_capability'):
            print(f"\nAdvisor Capability: {e['advisor_capability']}")
        if e.get('equity_alignment'):
            print(f"Equity Alignment: {e['equity_alignment']}")
        print(f"Remote Work Fit: {e.get('remote_work_fit', 'Unknown')}")

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
    print("\n" + "=" * 80)
    print("✅ STRONG CANDIDATES - RECOMMENDED FOR INTERVIEW")
    print("=" * 80)

    for idx, c in enumerate(yes_list[:10], 1):
        e = c['ai_evaluation']
        print(f"\n{idx}. {c['first_name']} {c.get('last_name', '')}")
        print(f"   {c.get('position', 'N/A')} at {c.get('company', 'N/A')}")
        print(f"   {c.get('city', 'N/A')}, {c.get('state', '')}")
        print(f"   Score: {e['fit_score']}/10 | Priority: {e['interview_priority']}")
        print(f"   State Govt Depth: {e.get('state_government_depth', 'Unknown')}")
        print(f"\n   Assessment: {e['detailed_rationale'][:250]}...")
        if c.get('email'):
            print(f"   📧 {c['email']}")

if maybe_list:
    print("\n" + "=" * 80)
    print("🤔 POTENTIAL CANDIDATES - CONSIDER IF NEEDED")
    print("=" * 80)

    for idx, c in enumerate(maybe_list[:5], 1):
        e = c['ai_evaluation']
        print(f"\n{idx}. {c['first_name']} {c.get('last_name', '')}")
        print(f"   {c.get('position', 'N/A')} at {c.get('company', 'N/A')}")
        print(f"   Score: {e['fit_score']}/10")
        print(f"   Main Concerns: {', '.join(e.get('gaps_or_concerns', [])[:2])}")

# Save comprehensive results
print("\n" + "=" * 80)
print("SAVING RESULTS")
print("=" * 80)

results = {
    'search_date': time.strftime('%Y-%m-%d %H:%M:%S'),
    'position': 'Senior Fellow, State Strategy',
    'organization': 'Catalyst Exchange',
    'location': 'Remote (U.S.-based)',
    'salary_range': '$170,000 - $180,000',
    'contract_term': 'Fixed-term through June 30, 2027',
    'summary': {
        'total_contacts': len(all_candidates),
        'relevant_candidates': len(filtered),
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

output_file = 'catalyst_exchange_state_strategy_evaluation.json'
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✅ Full results saved to: {output_file}")
print("\n✨ Candidate search complete!")
