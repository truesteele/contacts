#!/usr/bin/env python3
"""
Comprehensive evaluation for Girls Who Code Chief Executive Officer role
Seeking enterprise-level leaders with political savvy and deep equity commitment
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

# Target locations - national search, but prioritize tech and nonprofit hubs
priority_cities = [
    # Major tech hubs
    'New York', 'San Francisco', 'Oakland', 'Berkeley', 'Palo Alto', 'Mountain View',
    'Seattle', 'Los Angeles', 'Boston', 'Austin', 'Chicago', 'Washington', 'Denver',
    # Nonprofit/philanthropic centers
    'Atlanta', 'Philadelphia', 'Minneapolis', 'Portland', 'San Diego',
    # Bay Area
    'Menlo Park', 'Redwood City', 'San Mateo', 'San Jose', 'Sunnyvale', 'Santa Clara',
    # DC Metro
    'Arlington', 'Alexandria', 'Bethesda', 'Silver Spring', 'Reston',
    # NYC Metro
    'Brooklyn', 'Manhattan', 'Hoboken', 'Jersey City',
    # Other major cities
    'Miami', 'Dallas', 'Houston', 'Phoenix', 'Detroit', 'Baltimore', 'Nashville',
    'Charlotte', 'Raleigh', 'Durham', 'Pittsburgh', 'Columbus', 'Indianapolis',
    'Salt Lake City', 'San Antonio', 'Tampa', 'Orlando', 'Sacramento'
]

full_job_description = """
GIRLS WHO CODE - CHIEF EXECUTIVE OFFICER

ORGANIZATION CONTEXT:
Girls Who Code (www.girlswhocode.com) is at a pivotal inflection point—financially strong,
mission-anchored, and operating with a clear strategic plan—yet navigating a rapidly evolving
technology and social landscape that extends well beyond coding alone.

Founded in 2012, Girls Who Code has become one of the leading organizations working to close
the gender gap in technology. The organization has reached hundreds of thousands of students
through its programs and built a powerful community of alumni, volunteers, and partners.

THE ROLE:
The next CEO will lead an organization that is well-positioned for its next chapter of growth
and impact. This leader will steward the mission while navigating an evolving landscape in
technology education, workforce development, and the broader social-political environment
around equity and inclusion.

KEY LEADERSHIP QUALITIES:
1. Enterprise-Level Leadership
   - Proven track record leading complex organizations at scale
   - Experience with organizational growth, transformation, or turnaround
   - Strong operational and financial acumen
   - Board management and governance experience

2. Political and Stakeholder Savvy
   - Ability to navigate complex political and social landscapes
   - Experience building coalitions across sectors (corporate, government, education, nonprofit)
   - Strong external presence and brand ambassador capabilities
   - Crisis management and communications expertise

3. Deep Commitment to Equity
   - Demonstrated passion for gender equity in technology
   - Track record advancing DEI initiatives
   - Understanding of systemic barriers facing girls and women in STEM
   - Authentic connection to the mission and community served

4. Innovation and Organizational Stewardship
   - Vision for evolving programs in response to changing technology landscape
   - Experience with digital transformation and technology strategy
   - Ability to balance innovation with organizational sustainability
   - Track record of building and developing high-performing teams

IDEAL CANDIDATE PROFILE:
- Senior nonprofit leader with 15+ years experience, including C-suite or ED role
- OR Mission-driven executive from private sector tech with demonstrated nonprofit/social impact experience
- Experience in education technology, workforce development, or youth-serving organizations
- Track record with organizations of similar scale ($20M+ budget, national reach)
- Strong fundraising experience (corporate partnerships, foundations, major donors)
- National visibility and network in technology, education, or social impact sectors
- Experience working with diverse communities and demonstrated equity commitment
- Media savvy with experience as organizational spokesperson

SECTOR EXPERIENCE (HIGHLY VALUED):
- Technology companies (especially those with diversity/inclusion focus)
- Education nonprofits (especially tech education, STEM, youth development)
- Workforce development organizations
- Major national nonprofits with similar scale and complexity
- Corporate social responsibility or foundation leadership
- Government roles in education, technology, or workforce policy
"""

def evaluate_candidate_detailed(candidate: Dict) -> Dict:
    """Provide comprehensive evaluation with detailed rationale"""

    prompt = f"""
    Evaluate this candidate for the Girls Who Code Chief Executive Officer role.

    CANDIDATE:
    Name: {candidate.get('first_name', '')} {candidate.get('last_name', '')}
    Company: {candidate.get('company', 'Unknown')}
    Position: {candidate.get('position', 'Unknown')}
    Location: {candidate.get('city', 'Unknown')}, {candidate.get('state', '')}
    Headline: {candidate.get('headline', 'None')}
    Summary: {(candidate.get('summary', '') or '')[:1000]}

    ROLE CONTEXT:
    Girls Who Code is a nationally-recognized nonprofit that has reached hundreds of thousands
    of students to close the gender gap in technology. The organization is financially strong,
    mission-anchored, with a clear strategic plan, but navigating an evolving technology and
    social landscape.

    CRITICAL REQUIREMENTS:
    1. Enterprise-level leadership (CEO, President, ED, COO, or equivalent at scale)
    2. Political and stakeholder savvy (navigating complex environments, building coalitions)
    3. Deep commitment to equity (especially gender equity in technology/STEM)
    4. Innovation mindset with organizational stewardship

    IDEAL BACKGROUND:
    - Senior nonprofit executive with C-suite experience, OR
    - Mission-driven tech executive with nonprofit/social impact experience
    - Experience with organizations of similar scale ($20M+ budget, national reach)
    - Education, technology, or youth-serving sector experience
    - Strong fundraising and partnership development track record
    - National visibility and network

    Return detailed JSON evaluation:
    {{
        "recommendation": "strong_yes|yes|maybe|no",
        "fit_score": <1-10>,
        "confidence_level": "high|medium|low",

        "experience_assessment": {{
            "years_experience": "<estimate>",
            "has_ceo_ed_experience": <true/false>,
            "has_nonprofit_leadership": <true/false>,
            "has_tech_sector_experience": <true/false>,
            "has_education_sector": <true/false>,
            "has_youth_serving_orgs": <true/false>,
            "has_fundraising_development": <true/false>,
            "has_board_governance": <true/false>,
            "has_equity_dei_focus": <true/false>,
            "has_advocacy_policy": <true/false>,
            "has_media_communications": <true/false>,
            "has_large_org_experience": <true/false>
        }},

        "leadership_level": "ceo_ed|c_suite|vp_svp|director|other",
        "org_scale_experience": "large_national|mid_size|small|unclear",
        "sector_background": ["<primary sector>", "<secondary sector>"],

        "strengths": [
            "<specific strength highly relevant to this role>",
            "<another key strength with evidence>",
            "<third strength that differentiates them>"
        ],

        "gaps_or_concerns": [
            "<specific gap relative to role requirements>",
            "<another concern or development area>"
        ],

        "detailed_rationale": "<5-6 sentences providing thorough explanation of fit. Include specific
        evidence from their background. Explain why they would or wouldn't succeed leading a major
        national nonprofit at an inflection point, navigating complex stakeholder environments, and
        advancing gender equity in technology.>",

        "interview_priority": "immediate|high|medium|low",

        "interview_focus_areas": [
            "<specific area to probe in interview>",
            "<another critical topic to explore>",
            "<third area needing clarification>"
        ],

        "public_profile_strength": "high|medium|low|unknown",

        "equity_commitment": "<Assessment of demonstrated commitment to equity, especially gender
        equity and representation of women/girls in technology>",

        "stakeholder_navigation": "<Assessment of ability to navigate political, corporate, and
        social landscapes based on their experience>",

        "mission_alignment": "<Assessment of authentic connection to Girls Who Code mission based
        on their background and stated interests>"
    }}

    SCORING GUIDANCE:
    - 9-10: Exceptional fit - current or recent CEO/ED of comparable national nonprofit, or C-suite
      tech leader with deep nonprofit board/leadership experience, plus strong equity commitment
    - 7-8: Strong candidate - C-suite experience at smaller scale, or SVP at major org, with
      relevant sector experience and demonstrated mission alignment
    - 5-6: Potential fit - Director/VP level with growth trajectory, relevant experience but would
      be a stretch role
    - 3-4: Weak fit - Missing multiple critical requirements
    - 1-2: Not a fit - Wrong career stage or sector

    AUTOMATIC STRONG YES INDICATORS:
    - Current/recent CEO or ED of national education, tech-focused, or youth-serving nonprofit
    - C-suite tech executive with deep nonprofit board leadership and DEI track record
    - Senior leader at major education technology company with demonstrated social mission

    AUTOMATIC NO INDICATORS:
    - Less than 15 years experience
    - No leadership experience beyond Director level
    - No connection to education, technology, youth development, or equity work
    - Pure corporate executive with no nonprofit/mission-driven experience
    """

    try:
        response = openai_client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "You are an expert executive recruiter specializing in nonprofit CEO and C-suite placements, with deep expertise in the technology, education, and social impact sectors. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1200
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
print("GIRLS WHO CODE - CHIEF EXECUTIVE OFFICER")
print("Comprehensive Candidate Evaluation")
print("=" * 80)
print()

# Query contacts with relevant executive and tech/education experience
print("Phase 1: Identifying candidates with relevant executive experience...")

# Fetch all contacts - we'll filter programmatically for CEO-level roles
all_candidates = []
page_size = 1000
offset = 0

while True:
    response = supabase.table('contacts').select(
        'id, first_name, last_name, email, linkedin_url, company, position, '
        'city, state, headline, summary'
    ).range(offset, offset + page_size - 1).execute()

    if not response.data:
        break

    all_candidates.extend(response.data)
    offset += page_size

    if len(response.data) < page_size:
        break

print(f"  Found {len(all_candidates)} total contacts")

# Keywords for CEO-level roles
executive_keywords = [
    'ceo', 'chief executive', 'president', 'executive director', 'ed ',
    'chief operating', 'coo', 'chief', 'c-suite', 'managing director',
    'general manager', 'svp', 'senior vice president', 'evp',
    'executive vice president', 'founder', 'co-founder', 'principal'
]

# Keywords for nonprofit/mission-driven experience
nonprofit_keywords = [
    'nonprofit', 'non-profit', 'foundation', 'philanthropy', 'social impact',
    'social good', 'mission', 'charitable', 'ngo', '501c3', 'association',
    'institute', 'initiative', 'council', 'society', 'alliance', 'coalition'
]

# Keywords for tech sector
tech_keywords = [
    'technology', 'tech', 'software', 'digital', 'engineering', 'product',
    'platform', 'data', 'ai', 'machine learning', 'coding', 'programming',
    'computer science', 'developer', 'innovation', 'startup', 'saas'
]

# Keywords for education sector
education_keywords = [
    'education', 'school', 'university', 'college', 'academic', 'learning',
    'student', 'teaching', 'curriculum', 'edtech', 'stem', 'k-12', 'k12',
    'higher ed', 'training', 'youth', 'girls', 'women', 'young people'
]

# Keywords for DEI/equity focus
equity_keywords = [
    'equity', 'diversity', 'inclusion', 'dei', 'belonging', 'justice',
    'underrepresented', 'underserved', 'women in tech', 'gender',
    'representation', 'access', 'opportunity', 'gap', 'closing the gap'
]

# Keywords for fundraising/development
development_keywords = [
    'fundraising', 'development', 'donor', 'philanthropy', 'partnership',
    'corporate relations', 'foundation relations', 'major gifts',
    'capital campaign', 'advancement', 'revenue'
]

print("\nPhase 2: Filtering for relevant candidates...")

filtered = []
for c in all_candidates:
    search_text = f"{c.get('company', '')} {c.get('position', '')} {c.get('headline', '')} {(c.get('summary', '') or '')[:800]}".lower()

    # Calculate relevance score
    relevance = 0

    # Executive-level position (CRITICAL)
    has_executive = any(kw in search_text for kw in executive_keywords)
    if has_executive:
        relevance += 15
        # Extra boost for CEO/ED specifically
        if any(kw in search_text for kw in ['ceo', 'chief executive', 'executive director', 'president']):
            relevance += 10

    # Nonprofit/mission-driven experience
    nonprofit_matches = sum(1 for kw in nonprofit_keywords if kw in search_text)
    if nonprofit_matches > 0:
        relevance += nonprofit_matches * 4

    # Tech sector experience
    tech_matches = sum(1 for kw in tech_keywords if kw in search_text)
    if tech_matches > 0:
        relevance += tech_matches * 3

    # Education sector experience
    edu_matches = sum(1 for kw in education_keywords if kw in search_text)
    if edu_matches > 0:
        relevance += edu_matches * 4

    # DEI/equity focus
    equity_matches = sum(1 for kw in equity_keywords if kw in search_text)
    if equity_matches > 0:
        relevance += equity_matches * 5

    # Development/fundraising experience
    dev_matches = sum(1 for kw in development_keywords if kw in search_text)
    if dev_matches > 0:
        relevance += dev_matches * 3

    # Special boosts for highly relevant combinations
    if 'women in tech' in search_text or 'girls who code' in search_text:
        relevance += 20
    if 'stem education' in search_text or 'tech education' in search_text:
        relevance += 10
    if 'gender gap' in search_text or 'closing the gap' in search_text:
        relevance += 10
    if has_executive and (nonprofit_matches > 0 or equity_matches > 0):
        relevance += 8
    if has_executive and (tech_matches > 0 or edu_matches > 0):
        relevance += 5

    # Require executive-level OR very strong mission alignment
    # (to catch board members and senior advisors too)
    if relevance >= 15:
        c['relevance_score'] = relevance
        filtered.append(c)

# Sort by relevance
filtered.sort(key=lambda x: x['relevance_score'], reverse=True)

print(f"  Identified {len(filtered)} candidates with relevant experience")

# Evaluate top candidates
eval_limit = min(40, len(filtered))
print(f"\nPhase 3: Comprehensive AI evaluation of top {eval_limit} candidates...")
print("  (This will take several minutes for thorough analysis)")
print()

evaluated = []

for i, candidate in enumerate(filtered[:eval_limit], 1):
    print(f"  [{i:2}/{eval_limit}] Evaluating: {candidate['first_name']} {candidate.get('last_name', '')} "
          f"({candidate.get('position', 'N/A')[:40]} at {candidate.get('company', 'N/A')[:30]})")

    evaluation = evaluate_candidate_detailed(candidate)
    if evaluation:
        candidate['ai_evaluation'] = evaluation
        evaluated.append(candidate)

        # Show result
        rec = evaluation['recommendation']
        score = evaluation['fit_score']
        priority = evaluation.get('interview_priority', 'low')

        status = "STRONG YES" if rec == 'strong_yes' else "YES" if rec == 'yes' else "MAYBE" if rec == 'maybe' else "NO"
        print(f"       Result: {status} | Score: {score}/10 | Priority: {priority}")
    else:
        print(f"       Result: Evaluation failed")

    # Pause every 5 to avoid rate limits
    if i % 5 == 0 and i < eval_limit:
        print("       [Brief pause for API rate limiting...]")
        time.sleep(2)

# Categorize results
strong_yes = [c for c in evaluated if c['ai_evaluation']['recommendation'] == 'strong_yes']
yes_list = [c for c in evaluated if c['ai_evaluation']['recommendation'] == 'yes']
maybe_list = [c for c in evaluated if c['ai_evaluation']['recommendation'] == 'maybe']
no_list = [c for c in evaluated if c['ai_evaluation']['recommendation'] == 'no']

# Sort by score
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
  - Total contacts reviewed: {len(all_candidates):,}
  - Candidates with relevant keywords: {len(filtered)}
  - Candidates evaluated in detail: {len(evaluated)}

EVALUATION RESULTS:
  - Strong Yes (Interview Immediately): {len(strong_yes)}
  - Yes (Strong Candidates): {len(yes_list)}
  - Maybe (Potential Fit): {len(maybe_list)}
  - No (Not Recommended): {len(no_list)}
""")

if strong_yes:
    print("=" * 80)
    print("PRIORITY CANDIDATES - INTERVIEW IMMEDIATELY")
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
        print(f"  - Years of Experience: {exp_assess['years_experience']}")
        print(f"  - Leadership Level: {e.get('leadership_level', 'Unknown')}")
        print(f"  - Org Scale Experience: {e.get('org_scale_experience', 'Unknown')}")
        print(f"  - Sector Background: {', '.join(e.get('sector_background', []))}")

        # Key qualifications
        print(f"\nKey Qualifications:")
        qualifications = []
        if exp_assess.get('has_ceo_ed_experience'): qualifications.append("CEO/ED Experience")
        if exp_assess.get('has_nonprofit_leadership'): qualifications.append("Nonprofit Leadership")
        if exp_assess.get('has_tech_sector_experience'): qualifications.append("Tech Sector")
        if exp_assess.get('has_education_sector'): qualifications.append("Education Sector")
        if exp_assess.get('has_youth_serving_orgs'): qualifications.append("Youth-Serving Orgs")
        if exp_assess.get('has_fundraising_development'): qualifications.append("Fundraising/Development")
        if exp_assess.get('has_board_governance'): qualifications.append("Board Governance")
        if exp_assess.get('has_equity_dei_focus'): qualifications.append("Equity/DEI Focus")
        if exp_assess.get('has_advocacy_policy'): qualifications.append("Advocacy/Policy")
        if exp_assess.get('has_media_communications'): qualifications.append("Media/Communications")
        if exp_assess.get('has_large_org_experience'): qualifications.append("Large Org Experience")

        for qual in qualifications:
            print(f"  - {qual}")

        # Detailed assessment
        print(f"\nDetailed Assessment:")
        print(f"{e['detailed_rationale']}")

        # Strengths
        print(f"\nKey Strengths:")
        for s in e['strengths']:
            print(f"  - {s}")

        # Areas to explore
        if e.get('gaps_or_concerns'):
            print(f"\nAreas to Explore in Interview:")
            for concern in e['gaps_or_concerns']:
                print(f"  - {concern}")

        # Interview focus
        if e.get('interview_focus_areas'):
            print(f"\nInterview Focus Areas:")
            for focus in e['interview_focus_areas'][:3]:
                print(f"  - {focus}")

        # Additional insights
        if e.get('equity_commitment'):
            print(f"\nEquity Commitment: {e['equity_commitment']}")
        if e.get('stakeholder_navigation'):
            print(f"Stakeholder Navigation: {e['stakeholder_navigation']}")
        if e.get('mission_alignment'):
            print(f"Mission Alignment: {e['mission_alignment']}")
        print(f"Public Profile Strength: {e.get('public_profile_strength', 'Unknown')}")

        # Contact information
        print(f"\nContact Information:")
        if c.get('email'):
            print(f"  Email: {c['email']}")
        if c.get('linkedin_url'):
            print(f"  LinkedIn: {c['linkedin_url']}")

        # LinkedIn headline
        if c.get('headline'):
            print(f"  Headline: {c['headline']}")

if yes_list:
    print("\n" + "=" * 80)
    print("STRONG CANDIDATES - RECOMMENDED FOR INTERVIEW")
    print("=" * 80)

    for idx, c in enumerate(yes_list[:15], 1):
        e = c['ai_evaluation']
        print(f"\n{idx}. {c['first_name']} {c.get('last_name', '')}")
        print(f"   {c.get('position', 'N/A')} at {c.get('company', 'N/A')}")
        print(f"   {c.get('city', 'N/A')}, {c.get('state', '')}")
        print(f"   Score: {e['fit_score']}/10 | Priority: {e['interview_priority']}")
        print(f"   Leadership Level: {e.get('leadership_level', 'Unknown')}")
        print(f"\n   Assessment: {e['detailed_rationale'][:300]}...")
        if c.get('email'):
            print(f"   Email: {c['email']}")
        if c.get('linkedin_url'):
            print(f"   LinkedIn: {c['linkedin_url']}")

if maybe_list:
    print("\n" + "=" * 80)
    print("POTENTIAL CANDIDATES - CONSIDER IF NEEDED")
    print("=" * 80)

    for idx, c in enumerate(maybe_list[:10], 1):
        e = c['ai_evaluation']
        print(f"\n{idx}. {c['first_name']} {c.get('last_name', '')}")
        print(f"   {c.get('position', 'N/A')} at {c.get('company', 'N/A')}")
        print(f"   Score: {e['fit_score']}/10")
        print(f"   Main Concerns: {', '.join(e.get('gaps_or_concerns', [])[:2])}")
        if c.get('email'):
            print(f"   Email: {c['email']}")

# Save comprehensive results
print("\n" + "=" * 80)
print("SAVING RESULTS")
print("=" * 80)

results = {
    'search_date': time.strftime('%Y-%m-%d %H:%M:%S'),
    'position': 'Chief Executive Officer',
    'organization': 'Girls Who Code',
    'search_firm': 'Bridge Partners',
    'contact': 'Tory Clarke',
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

output_file = 'scripts/job_searches/girls_who_code_ceo_evaluation.json'
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nFull results saved to: {output_file}")
print("\nCandidate search complete!")
