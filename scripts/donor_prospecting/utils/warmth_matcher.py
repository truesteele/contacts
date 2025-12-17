"""
Automated warmth/affinity matching based on shared institutions and connections.

Detects overlaps between contacts and Justin Steele's background (schools, employers, geography, networks).
"""

from typing import Dict, List, Tuple


# Justin's background data (from prompts.py)
JUSTIN_SCHOOLS = [
    'University of Virginia', 'UVA',
    'Harvard Business School', 'HBS',
    'Harvard Kennedy School', 'HKS',
    'Harvard'
]

JUSTIN_EMPLOYERS = [
    'Google', 'Google.org',
    'Year Up',
    'Bain & Company', 'Bain',
    'Bridgespan', 'The Bridgespan Group'
]

JUSTIN_ORGANIZATIONS = [
    'Kindora',
    'Outdoorithm Collective', 'Outdoorithm',
    'True Steele',
    'San Francisco Foundation',
    'National Society of Black Engineers', 'NSBE',
    'Management Leadership for Tomorrow', 'MLT',
    'Education Pioneers'
]

JUSTIN_LOCATIONS = [
    'Oakland', 'Bay Area', 'San Francisco', 'SF',
    'Boston', 'Cambridge',
    'Arlington', 'DC', 'Washington',
    'Charlottesville', 'Virginia',
    'Atlanta', 'Georgia'
]


def calculate_warmth_score(contact: dict) -> Tuple[int, str, List[str], Dict]:
    """
    Calculate warmth score (0-100) based on overlap with Justin's background.

    Returns:
        (score, level, shared_institutions, details)
        - score: 0-100 warmth score
        - level: 'hot', 'warm', 'warm-ish', 'cool', 'cold'
        - shared_institutions: List of shared institutions
        - details: Dict with breakdown by category
    """
    score = 0
    shared_institutions = []
    details = {
        'schools': [],
        'employers': [],
        'organizations': [],
        'locations': [],
        'connection_type': 'none'
    }

    # Check schools (worth 30 points max)
    schools = contact.get('enrich_schools', []) or []
    if isinstance(schools, list):
        for school in schools:
            for justin_school in JUSTIN_SCHOOLS:
                if justin_school.lower() in school.lower():
                    score += 15  # Major school overlap
                    shared_institutions.append(f"School: {school}")
                    details['schools'].append(school)
                    break

    # Check employers (worth 35 points max)
    # Current employer
    current_company = contact.get('enrich_current_company') or contact.get('company') or ''
    for justin_employer in JUSTIN_EMPLOYERS:
        if justin_employer.lower() in current_company.lower():
            score += 20  # Current same employer
            shared_institutions.append(f"Current employer: {current_company}")
            details['employers'].append(current_company)
            break

    # Past employers
    past_companies = contact.get('enrich_companies_worked', []) or []
    if isinstance(past_companies, list):
        for company in past_companies:
            for justin_employer in JUSTIN_EMPLOYERS:
                if justin_employer.lower() in company.lower():
                    score += 10  # Past same employer
                    shared_institutions.append(f"Past employer: {company}")
                    details['employers'].append(company)
                    break

    # Check organizations/boards (worth 25 points max)
    boards = contact.get('enrich_board_positions', []) or []
    volunteer_orgs = contact.get('enrich_volunteer_orgs', []) or []
    all_orgs = (boards if isinstance(boards, list) else []) + (volunteer_orgs if isinstance(volunteer_orgs, list) else [])

    for org in all_orgs:
        for justin_org in JUSTIN_ORGANIZATIONS:
            if justin_org.lower() in org.lower():
                score += 15  # Same organization/board
                shared_institutions.append(f"Organization: {org}")
                details['organizations'].append(org)
                break

    # Check geography (worth 10 points max)
    location = contact.get('location_name') or contact.get('city', '') + ', ' + contact.get('state', '')
    for justin_location in JUSTIN_LOCATIONS:
        if justin_location.lower() in location.lower():
            score += 5  # Geographic overlap
            shared_institutions.append(f"Location: {location}")
            details['locations'].append(location)
            break

    # Cap at 100
    score = min(score, 100)

    # Determine warmth level and connection type (must match DB constraints)
    # warmth_level options: 'Hot', 'Warm', 'Cool', 'Cold'
    # connection_type options: 'Direct', 'Second-degree', 'Community', 'No known connection'
    if score >= 75:
        level = 'Hot'
        details['connection_type'] = 'Direct'
    elif score >= 50:
        level = 'Warm'
        details['connection_type'] = 'Community'
    elif score >= 25:
        level = 'Cool'
        details['connection_type'] = 'Second-degree'
    else:
        level = 'Cold'
        details['connection_type'] = 'No known connection'

    return score, level, shared_institutions, details


def detect_warmth_for_contact(contact: dict) -> Dict:
    """
    Detect warmth/overlap for a single contact.

    Returns dict with warmth data ready for database update.
    """
    score, level, institutions, details = calculate_warmth_score(contact)

    return {
        'personal_connection_strength': round(score / 10),  # Scale 0-100 to 0-10
        'warmth_level': level,
        'shared_institutions': institutions,
        'shared_institutions_details': details,
        'connection_type': details['connection_type']
    }
