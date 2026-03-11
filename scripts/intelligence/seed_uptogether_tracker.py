#!/usr/bin/env python3
"""Seed the UpTogether x True Steele project tracker with all tasks."""

import json
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../job-matcher-ai/.env.local'))

SUPABASE_URL = os.getenv('NEXT_PUBLIC_PROJECTS_SUPABASE_URL', 'https://hjuvqpxvfrzwmlqzkpxh.supabase.co')
SUPABASE_KEY = os.getenv('PROJECTS_SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_KEY:
    print("ERROR: PROJECTS_SUPABASE_SERVICE_ROLE_KEY not set")
    sys.exit(1)

API_URL = f"{SUPABASE_URL}/rest/v1/project_tasks"
HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal',
}

PROJECT_ID = 'uptogether'


def clear_existing():
    """Delete all existing tasks for this project."""
    resp = requests.delete(
        API_URL,
        headers={**HEADERS, 'Prefer': 'return=minimal'},
        params={'project_id': f'eq.{PROJECT_ID}'}
    )
    if resp.status_code in (200, 204):
        print("Cleared existing tasks")
    else:
        print(f"Warning: clear returned {resp.status_code}: {resp.text}")


def insert_tasks(tasks: list[dict]):
    """Insert tasks in a single batch."""
    # Normalize all objects to have the same keys (PostgREST requirement)
    defaults = {
        'project_id': PROJECT_ID,
        'section': None,
        'subsection': None,
        'title': None,
        'description': None,
        'status': 'todo',
        'owner': None,
        'due_date': None,
        'sort_order': 0,
        'notes': None,
    }
    normalized = [{**defaults, **t, 'project_id': PROJECT_ID} for t in tasks]
    resp = requests.post(API_URL, headers=HEADERS, json=normalized)
    if resp.status_code in (200, 201):
        print(f"Inserted {len(tasks)} tasks")
    else:
        print(f"ERROR inserting tasks: {resp.status_code} {resp.text}")
        sys.exit(1)


# ── Deliverables ─────────────────────────────────────────────────────────

deliverables = [
    # AI Strategy Document
    {'section': 'Deliverables', 'subsection': 'AI Strategy Document', 'title': 'Discovery & current-state analysis', 'description': 'Week 1', 'owner': 'Justin', 'due_date': '2026-03-16', 'sort_order': 10},
    {'section': 'Deliverables', 'subsection': 'AI Strategy Document', 'title': 'Draft AI strategy framework', 'description': 'Week 2', 'owner': 'Justin', 'due_date': '2026-03-23', 'sort_order': 20},
    {'section': 'Deliverables', 'subsection': 'AI Strategy Document', 'title': 'Review with UT leadership', 'description': 'Week 3', 'owner': 'Justin', 'due_date': '2026-03-30', 'sort_order': 30},
    {'section': 'Deliverables', 'subsection': 'AI Strategy Document', 'title': 'Final strategy document delivered', 'description': 'Week 4', 'owner': 'Justin', 'due_date': '2026-04-03', 'sort_order': 40},

    # Google.org Application
    {'section': 'Deliverables', 'subsection': 'Google.org Application', 'title': 'Gather all inputs from UT', 'description': 'Week 1-2', 'owner': 'UT Team', 'due_date': '2026-03-21', 'sort_order': 50},
    {'section': 'Deliverables', 'subsection': 'Google.org Application', 'title': 'Draft all narrative responses', 'description': 'Week 2', 'owner': 'Justin', 'due_date': '2026-03-21', 'sort_order': 60},
    {'section': 'Deliverables', 'subsection': 'Google.org Application', 'title': 'UT review & feedback round', 'description': 'Week 3', 'owner': 'Cesar', 'due_date': '2026-03-28', 'sort_order': 70},
    {'section': 'Deliverables', 'subsection': 'Google.org Application', 'title': 'Final submission on Submittable', 'description': 'Apr 3 deadline', 'owner': 'Justin', 'due_date': '2026-04-03', 'sort_order': 80},

    # Strategy Session
    {'section': 'Deliverables', 'subsection': 'Strategy Session', 'title': 'Prepare strategy session agenda & materials', 'description': 'Week 3', 'owner': 'Justin', 'due_date': '2026-03-28', 'sort_order': 90},
    {'section': 'Deliverables', 'subsection': 'Strategy Session', 'title': 'Facilitate in-person strategy session (JT trip)', 'description': 'Mar 30 – Apr 3', 'owner': 'Justin', 'due_date': '2026-04-03', 'sort_order': 100},
]

# ── Application Questions ────────────────────────────────────────────────

application = [
    # Section I: Org & Submitter Info
    {'section': 'Application', 'subsection': 'I. Org & Submitter Info', 'title': 'Q1. Organization legal name', 'owner': 'UT Team', 'sort_order': 10},
    {'section': 'Application', 'subsection': 'I. Org & Submitter Info', 'title': 'Q2. Organization website', 'owner': 'UT Team', 'sort_order': 20},
    {'section': 'Application', 'subsection': 'I. Org & Submitter Info', 'title': 'Q3. Year founded', 'owner': 'UT Team', 'sort_order': 30},
    {'section': 'Application', 'subsection': 'I. Org & Submitter Info', 'title': 'Q4. Organization HQ location', 'owner': 'UT Team', 'sort_order': 40},
    {'section': 'Application', 'subsection': 'I. Org & Submitter Info', 'title': 'Q5. Annual operating budget', 'owner': 'UT Team', 'sort_order': 50},
    {'section': 'Application', 'subsection': 'I. Org & Submitter Info', 'title': 'Q6. Number of employees', 'owner': 'UT Team', 'sort_order': 60},
    {'section': 'Application', 'subsection': 'I. Org & Submitter Info', 'title': 'Q7. CEO/ED name and email', 'owner': 'UT Team', 'sort_order': 70},
    {'section': 'Application', 'subsection': 'I. Org & Submitter Info', 'title': 'Q8. Submitter name, title, email', 'owner': 'UT Team', 'sort_order': 80},
    {'section': 'Application', 'subsection': 'I. Org & Submitter Info', 'title': 'Q9. Mission statement', 'description': '≤100 words', 'owner': 'UT Team', 'sort_order': 90},
    {'section': 'Application', 'subsection': 'I. Org & Submitter Info', 'title': 'Q10. Brief org description', 'description': '≤100 words', 'owner': 'UT Team', 'sort_order': 100},

    # Section II: Impact
    {'section': 'Application', 'subsection': 'II. Impact', 'title': 'Q11. Problem your org addresses', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 110},
    {'section': 'Application', 'subsection': 'II. Impact', 'title': 'Q12. Target population(s)', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 120},
    {'section': 'Application', 'subsection': 'II. Impact', 'title': 'Q13. Current programs & impact data', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 130},
    {'section': 'Application', 'subsection': 'II. Impact', 'title': 'Q14. How AI will enhance impact', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 140},
    {'section': 'Application', 'subsection': 'II. Impact', 'title': 'Q15. Specific outcomes with AI', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 150},
    {'section': 'Application', 'subsection': 'II. Impact', 'title': 'Q16. Measurement approach', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 160},
    {'section': 'Application', 'subsection': 'II. Impact', 'title': 'Q17. Key metrics', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 170},
    {'section': 'Application', 'subsection': 'II. Impact', 'title': 'Q18. Lived experience integration', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 180},
    {'section': 'Application', 'subsection': 'II. Impact', 'title': 'Q19. Community engagement approach', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 190},

    # Section III: Innovative Technology
    {'section': 'Application', 'subsection': 'III. Innovative Technology', 'title': 'Q20. Proposed AI solution overview', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 200},
    {'section': 'Application', 'subsection': 'III. Innovative Technology', 'title': 'Q21. AI/ML techniques to be used', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 210},
    {'section': 'Application', 'subsection': 'III. Innovative Technology', 'title': 'Q22. Technical team & capabilities', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 220},
    {'section': 'Application', 'subsection': 'III. Innovative Technology', 'title': 'Q23. Data strategy', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 230},
    {'section': 'Application', 'subsection': 'III. Innovative Technology', 'title': 'Q24. Current tech stack', 'description': '≤100 words', 'owner': 'Rachel', 'sort_order': 240},
    {'section': 'Application', 'subsection': 'III. Innovative Technology', 'title': 'Q25. Innovation differentiation', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 250},
    {'section': 'Application', 'subsection': 'III. Innovative Technology', 'title': 'Q26. One-line AI solution summary', 'description': '≤100 chars', 'owner': 'Justin', 'sort_order': 260},

    # Section IV: Feasibility
    {'section': 'Application', 'subsection': 'IV. Feasibility', 'title': 'Q27. Implementation plan overview', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 270},
    {'section': 'Application', 'subsection': 'IV. Feasibility', 'title': 'Q28. Risk assessment & mitigation', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 280},
    {'section': 'Application', 'subsection': 'IV. Feasibility', 'title': 'Q29. Change management approach', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 290},
    {'section': 'Application', 'subsection': 'IV. Feasibility', 'title': 'Q30. Stakeholder buy-in', 'description': '≤100 words', 'owner': 'Cesar', 'sort_order': 300},
    {'section': 'Application', 'subsection': 'IV. Feasibility', 'title': 'Q31. Sustainability plan post-grant', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 310},
    {'section': 'Application', 'subsection': 'IV. Feasibility', 'title': 'Q32. Existing resources to leverage', 'description': '≤100 words', 'owner': 'Rachel', 'sort_order': 320},
    {'section': 'Application', 'subsection': 'IV. Feasibility', 'title': 'Q33. Timeline with milestones', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 330},

    # Section V: Partnerships
    {'section': 'Application', 'subsection': 'V. Partnerships', 'title': 'Q34. Government partnership & letter of support', 'description': '≤100 words + letter', 'owner': 'Cesar', 'sort_order': 340},

    # Section VI: Scalability
    {'section': 'Application', 'subsection': 'VI. Scalability', 'title': 'Q35. Scaling strategy', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 350},
    {'section': 'Application', 'subsection': 'VI. Scalability', 'title': 'Q36. Geographic expansion plan', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 360},
    {'section': 'Application', 'subsection': 'VI. Scalability', 'title': 'Q37. Replicability of solution', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 370},
    {'section': 'Application', 'subsection': 'VI. Scalability', 'title': 'Q38. Open-source or shared learnings', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 380},
    {'section': 'Application', 'subsection': 'VI. Scalability', 'title': 'Q39. 5-year vision', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 390},

    # Section VII: Budget & Timeline
    {'section': 'Application', 'subsection': 'VII. Budget & Timeline', 'title': 'Q41. Total budget requested ($1-3M)', 'owner': 'Justin', 'sort_order': 400},
    {'section': 'Application', 'subsection': 'VII. Budget & Timeline', 'title': 'Q42. Budget breakdown by category', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 410},
    {'section': 'Application', 'subsection': 'VII. Budget & Timeline', 'title': 'Q43. Matching/co-funding sources', 'description': '≤100 words', 'owner': 'Cesar', 'sort_order': 420},
    {'section': 'Application', 'subsection': 'VII. Budget & Timeline', 'title': 'Q44. Project duration (up to 36 months)', 'owner': 'Justin', 'sort_order': 430},
    {'section': 'Application', 'subsection': 'VII. Budget & Timeline', 'title': 'Q45-49. Milestones 1-5 (description, timeline, budget)', 'description': '3-5 milestones', 'owner': 'Justin', 'sort_order': 440},
    {'section': 'Application', 'subsection': 'VII. Budget & Timeline', 'title': 'Q50. Key personnel and roles', 'description': '≤100 words', 'owner': 'Justin', 'sort_order': 450},
    {'section': 'Application', 'subsection': 'VII. Budget & Timeline', 'title': 'Q51. Detailed budget spreadsheet upload', 'owner': 'Justin', 'sort_order': 460},

    # Section VIII: Ethics
    {'section': 'Application', 'subsection': 'VIII. Ethics', 'title': 'Q52-57. Ethics & responsible AI checkboxes', 'description': 'Checkbox attestations', 'owner': 'Cesar', 'sort_order': 470},
]

# ── Materials from UT ────────────────────────────────────────────────────

materials = [
    # P1 Critical
    {'section': 'Materials', 'subsection': 'P1 Critical', 'title': 'Org factual info (name, year, budget, headcount)', 'owner': 'UT Team', 'sort_order': 10},
    {'section': 'Materials', 'subsection': 'P1 Critical', 'title': 'Current programs & impact data / metrics', 'owner': 'Cesar', 'sort_order': 20},
    {'section': 'Materials', 'subsection': 'P1 Critical', 'title': 'Existing tech stack overview from product team', 'owner': 'Rachel', 'sort_order': 30},

    # P2 Important
    {'section': 'Materials', 'subsection': 'P2 Important', 'title': 'Government partnership details & letter of support', 'owner': 'Cesar', 'sort_order': 40},
    {'section': 'Materials', 'subsection': 'P2 Important', 'title': 'Matching/co-funding commitments or plans', 'owner': 'Cesar', 'sort_order': 50},
    {'section': 'Materials', 'subsection': 'P2 Important', 'title': 'Internal AI/data strategy docs (if any)', 'owner': 'Rachel', 'sort_order': 60},

    # P3 Nice-to-Have
    {'section': 'Materials', 'subsection': 'P3 Nice-to-Have', 'title': 'Member stories or testimonials for narrative', 'owner': 'UT Team', 'sort_order': 70},
    {'section': 'Materials', 'subsection': 'P3 Nice-to-Have', 'title': 'Brand guidelines / style guide', 'owner': 'UT Team', 'sort_order': 80},
]

# ── Workplan ─────────────────────────────────────────────────────────────

workplan = [
    {'section': 'Workplan', 'title': 'Week 1 (Mar 10-16): Kickoff, discovery, gather inputs', 'description': 'Kickoff + SXSW', 'owner': 'Justin', 'due_date': '2026-03-16', 'sort_order': 10},
    {'section': 'Workplan', 'title': 'Week 2 (Mar 17-23): Draft application & AI strategy', 'description': 'App Draft due Mar 21', 'owner': 'Justin', 'due_date': '2026-03-23', 'sort_order': 20},
    {'section': 'Workplan', 'title': 'Week 3 (Mar 24-30): Review, refine, strategy session prep', 'description': 'Review & Refine', 'owner': 'Justin', 'due_date': '2026-03-30', 'sort_order': 30},
    {'section': 'Workplan', 'title': 'Week 4 (Mar 31 – Apr 3): Final edits, in-person session, submit', 'description': 'Final Submit Apr 3', 'owner': 'Justin', 'due_date': '2026-04-03', 'sort_order': 40},
]

# ── Meetings ─────────────────────────────────────────────────────────────

meetings = [
    {'section': 'Meetings', 'title': 'Kickoff session — Justin + Cesar + Rachel', 'description': 'Mar 10-11', 'owner': 'Justin', 'due_date': '2026-03-11', 'status': 'done', 'sort_order': 10},
]

# ── Open Questions ───────────────────────────────────────────────────────

open_questions = [
    {'section': 'Open Questions', 'title': 'Which government partner will provide letter of support?', 'owner': 'Cesar', 'sort_order': 10},
    {'section': 'Open Questions', 'title': 'What is the target grant amount ($1-3M range)?', 'owner': 'Justin', 'sort_order': 20},
    {'section': 'Open Questions', 'title': 'Does UT have existing AI/ML vendor relationships?', 'owner': 'Rachel', 'sort_order': 30},
    {'section': 'Open Questions', 'title': 'What matching funds or co-funding is available?', 'owner': 'Cesar', 'sort_order': 40},
    {'section': 'Open Questions', 'title': 'Who are the 3-5 key personnel for the project?', 'owner': 'Cesar', 'sort_order': 50},
    {'section': 'Open Questions', 'title': 'What member data is available for the AI solution?', 'owner': 'Rachel', 'sort_order': 60},
    {'section': 'Open Questions', 'title': 'Are there data privacy constraints to consider?', 'owner': 'Rachel', 'sort_order': 70},
    {'section': 'Open Questions', 'title': 'What is the preferred project duration (12-36 months)?', 'owner': 'Justin', 'sort_order': 80},
    {'section': 'Open Questions', 'title': 'Will UT apply as sole org or with a partner?', 'owner': 'Cesar', 'sort_order': 90},
]


def main():
    print(f"Seeding UpTogether tracker at {SUPABASE_URL}")
    clear_existing()

    all_tasks = deliverables + application + materials + workplan + meetings + open_questions
    print(f"Inserting {len(all_tasks)} tasks...")
    insert_tasks(all_tasks)

    print(f"\nDone! {len(all_tasks)} tasks seeded.")
    print(f"  Deliverables: {len(deliverables)}")
    print(f"  Application:  {len(application)}")
    print(f"  Materials:    {len(materials)}")
    print(f"  Workplan:     {len(workplan)}")
    print(f"  Meetings:     {len(meetings)}")
    print(f"  Open Questions: {len(open_questions)}")


if __name__ == '__main__':
    main()
