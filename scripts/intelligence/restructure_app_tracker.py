"""
Restructure the UpTogether Application section from 47 individual questions
into a logical build sequence of ~8 consolidated tasks.

A great grant application is built in layers, not question-by-question:
1. Strategic foundation (use case decision)
2. Core narrative (Impact + Technical)
3. Execution plan (Feasibility + Budget)
4. Supporting sections (Partnerships + Org info)
5. Final assembly (Review + polish)
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = "https://hjuvqpxvfrzwmlqzkpxh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqdXZxcHh2ZnJ6d21scXprcHhoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM1NTIyNSwiZXhwIjoyMDcxOTMxMjI1fQ.AOYbPJPCITnRuGaYbQsbaJy_8fCGkmFL81DzM7h2NdM"
PROJECT_ID = "uptogether"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Step 1: Delete all 47 existing Application tasks ──────────────────

print("Fetching existing Application tasks...")
existing = sb.table("project_tasks").select("id").eq("project_id", PROJECT_ID).eq("section", "Application").execute()
ids_to_delete = [t["id"] for t in existing.data]
print(f"  Found {len(ids_to_delete)} tasks to replace")

for task_id in ids_to_delete:
    sb.table("project_tasks").delete().eq("id", task_id).execute()
print(f"  Deleted {len(ids_to_delete)} individual question tasks")

# ── Step 2: Insert new consolidated build-sequence tasks ──────────────

NEW_TASKS = [
    {
        "section": "Application",
        "subsection": "Strategic Foundation",
        "title": "Define AI use cases & strategic direction",
        "description": "Must complete before drafting any narrative sections",
        "owner": "Justin",
        "due_date": "2026-03-17",
        "sort_order": 10,
        "notes": """This is the single most important decision for the application. Everything else flows from the use case choice.

CONTRACT: Exhibit A, Deliverable 1 — Must address two priority AI use cases:
1. Agentic application review with external data source consultation
2. Automated benefits counseling for member navigation

INPUTS NEEDED:
- Cesar's email outlined use case prioritization preferences
- Rachel's tech stack and ML feasibility input (uploaded to shared Drive)
- Prior Google.org application from last year (Jesús uploading)

DECISIONS:
- Which use case leads? Agentic app review or benefits counseling?
- What's the 1-sentence framing of the AI solution? (≤100 chars for Q26)
- How do we position this as 'AI for Government Innovation' specifically?

The AI Strategy Document (Deliverable 1) should resolve these questions and directly inform all narrative sections below.""",
    },
    {
        "section": "Application",
        "subsection": "Core Narrative",
        "title": "Draft Impact narrative (Section II — 9 questions)",
        "description": "≤100 words each · The heart of the application",
        "owner": "Justin",
        "due_date": "2026-03-19",
        "sort_order": 20,
        "notes": """Section II: Impact is the HEART of the application. Google.org evaluators weight this heavily.

CONTRACT: Exhibit A, Deliverable 2 — 'Framing of AI use cases as transformative applications of generative and agentic AI in public service delivery'

QUESTIONS TO ANSWER:
- Q11. Problem your org addresses (≤100 words) — frame around government service delivery gaps
- Q12. Target population(s) (≤100 words)
- Q13. Current programs & impact data (≤100 words) — needs UT metrics
- Q14. How AI will enhance impact (≤100 words) — flows directly from use case decision
- Q15. Specific outcomes with AI (≤100 words) — quantifiable targets
- Q16. Measurement approach (≤100 words)
- Q17. Key metrics (≤100 words)
- Q18. Lived experience integration (≤100 words) — UT's member-centered model is a strength here
- Q19. Community engagement approach (≤100 words)

STRATEGY: Lead with UT's unique position as a member-led platform that already serves 150K+ families. The AI doesn't replace human connection — it amplifies it.""",
    },
    {
        "section": "Application",
        "subsection": "Core Narrative",
        "title": "Draft Technical Approach (Section III — 7 questions)",
        "description": "≤100 words each · AI solution, ML techniques, data strategy",
        "owner": "Justin",
        "due_date": "2026-03-19",
        "sort_order": 30,
        "notes": """Section III: Innovative Technology — what we're building and how.

CONTRACT: Exhibit A, Deliverable 1 — AI Strategy Document must cover 'Technical requirements and data infrastructure needs for each use case'

QUESTIONS TO ANSWER:
- Q20. Proposed AI solution overview (≤100 words)
- Q21. AI/ML techniques to be used (≤100 words) — be specific: LLMs, RAG, agentic workflows, etc.
- Q22. Technical team & capabilities (≤100 words) — Rachel's team + any planned hires
- Q23. Data strategy (≤100 words) — member data, government data sources, privacy approach
- Q24. Current tech stack (≤100 words) — Rachel provides this
- Q25. Innovation differentiation (≤100 words) — what makes this different from generic AI chatbots
- Q26. One-line AI solution summary (≤100 chars)

INPUTS FROM RACHEL:
- Tech stack overview (uploaded to shared Drive)
- Current ML uses and feasibility responses
- Data infrastructure capabilities""",
    },
    {
        "section": "Application",
        "subsection": "Execution Plan",
        "title": "Draft Feasibility & Implementation (Section IV — 7 questions)",
        "description": "≤100 words each · Prove UT can actually build this",
        "owner": "Justin",
        "due_date": "2026-03-20",
        "sort_order": 40,
        "notes": """Section IV: Feasibility — proving this isn't just a good idea, but one UT can execute.

CONTRACT: Exhibit A, Deliverable 2 — 'Feasibility narrative addressing team capability, technical approach, and implementation plan'

QUESTIONS TO ANSWER:
- Q27. Implementation plan overview (≤100 words) — phased rollout, milestones
- Q28. Risk assessment & mitigation (≤100 words) — data quality, adoption, technical risks
- Q29. Change management approach (≤100 words) — how UT staff and members adapt
- Q30. Stakeholder buy-in (≤100 words) — Cesar provides org readiness context
- Q31. Sustainability plan post-grant (≤100 words) — what happens after 36 months
- Q32. Existing resources to leverage (≤100 words) — Rachel provides tech assets
- Q33. Timeline with milestones (≤100 words) — align with Budget section milestones

INPUTS NEEDED:
- Rachel: tech capability and resource assessment
- Cesar: organizational capacity and stakeholder context
- AI Strategy Document roadmap should inform the implementation plan""",
    },
    {
        "section": "Application",
        "subsection": "Execution Plan",
        "title": "Build Budget, Timeline & Milestones (Section VII — 7 questions + upload)",
        "description": "$1-3M over up to 36 months · Spreadsheet required",
        "owner": "Justin",
        "due_date": "2026-03-20",
        "sort_order": 50,
        "notes": """Section VII: Budget & Timeline — the financial case.

KEY OPEN QUESTION: What is the target grant amount within the $1-3M range? Must be realistic but competitive.

QUESTIONS TO ANSWER:
- Q41. Total budget requested ($1-3M)
- Q42. Budget breakdown by category (≤100 words) — personnel, technology, data, etc.
- Q43. Matching/co-funding sources (≤100 words) — Cesar provides any matching commitments
- Q44. Project duration (up to 36 months)
- Q45-49. Milestones 1-5 — each needs description, timeline, and budget allocation
- Q50. Key personnel and roles (≤100 words) — who's doing what
- Q51. Detailed budget spreadsheet upload — requires Excel/Sheets document

MILESTONE STRUCTURE: Should align with AI Strategy Document roadmap phases. Google.org wants to see clear deliverables tied to spend.

INPUTS FROM CESAR:
- Matching/co-funding plans
- Key personnel decisions (who leads internally)""",
    },
    {
        "section": "Application",
        "subsection": "Supporting Sections",
        "title": "Government Partnership & Scalability (Sections V-VI — 6 questions)",
        "description": "CRITICAL: Letter of support required · Scaling narrative",
        "owner": "Justin",
        "due_date": "2026-03-21",
        "sort_order": 60,
        "notes": """Sections V & VI — Partnership is MAKE-OR-BREAK for this challenge.

The Google.org 'AI for Government Innovation' challenge SPECIFICALLY requires government partnerships. A strong letter of support could be the difference between advancing and being cut.

CONTRACT: Exhibit A, 'What Company Provides' — 'Government partnership documentation (MOUs, contracts, letters of support, or similar evidence of government relationships)'

PARTNERSHIP (Section V):
- Q34. Government partnership & letter of support (≤100 words + letter upload)
- Cesar owns the government relationship; Justin drafts the narrative
- UT has existing MOUs (uploaded by Ivanna to shared Drive)

SCALABILITY (Section VI):
- Q35. Scaling strategy (≤100 words)
- Q36. Geographic expansion plan (≤100 words)
- Q37. Replicability of solution (≤100 words)
- Q38. Open-source or shared learnings (≤100 words)
- Q39. 5-year vision (≤100 words)

CONTRACT: Exhibit A, Deliverable 2 — 'Scalability narrative demonstrating potential for replication across government contexts'

Frame UT's government partnership model as inherently replicable — the AI solution can be deployed in any jurisdiction where members interact with government services.""",
    },
    {
        "section": "Application",
        "subsection": "Supporting Sections",
        "title": "Org Info & Ethics (Sections I, VIII — 11 items)",
        "description": "Fill-in-the-blank from UT Team · Ethics checkboxes",
        "owner": "UT Team",
        "due_date": "2026-03-21",
        "sort_order": 70,
        "notes": """Sections I and VIII are straightforward inputs from the UT team.

ORG & SUBMITTER INFO (Section I — 10 items):
- Q1. Organization legal name
- Q2. Organization website
- Q3. Year founded
- Q4. Organization HQ location
- Q5. Annual operating budget
- Q6. Number of employees
- Q7. CEO/ED name and email
- Q8. Submitter name, title, email
- Q9. Mission statement (≤100 words)
- Q10. Brief org description (≤100 words)

Most of these are factual lookups. Q9 and Q10 may need light editing to align with the application's narrative framing.

ETHICS (Section VIII — 1 item):
- Q52-57. Ethics & responsible AI checkboxes — attestations about data privacy, bias mitigation, transparency, etc.

These are checkbox attestations that Cesar signs off on.""",
    },
    {
        "section": "Application",
        "subsection": "Final Assembly",
        "title": "Full application review, polish & narrative consistency",
        "description": "Word count check · Cross-reference with AI Strategy · UT sign-off prep",
        "owner": "Justin",
        "due_date": "2026-03-21",
        "sort_order": 80,
        "notes": """Final pass before handing to UT for review.

CHECKLIST:
- All ≤100-word answers within limit
- Narrative arc is coherent: Problem → AI Solution → Impact → Feasibility → Scale
- Budget milestones align with implementation timeline (Sections IV and VII match)
- Government partnership narrative is strong and specific (not generic)
- One-line summary (Q26) captures the essence
- Technical approach is specific enough to be credible, accessible enough for non-technical reviewers
- Cross-reference all claims with AI Strategy Document (Deliverable 1)
- Spreadsheet upload is formatted and complete
- Letter of support is attached

THEN: Hand off to UT for 48-hour review (tracked in Deliverables section)""",
    },
]

print("\nInserting new consolidated tasks...")
for task in NEW_TASKS:
    task["project_id"] = PROJECT_ID
    task["status"] = "todo"
    res = sb.table("project_tasks").insert(task).execute()
    print(f"  ✓ {task['title']}")

print(f"\nDone! Replaced 47 individual questions with {len(NEW_TASKS)} build-sequence tasks.")
