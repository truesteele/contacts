"""
Update UpTogether tracker tasks with contract context in notes field,
and add missing deliverable tasks.

Reference: docs/True_Steele/Contracts/UpTogether_Consulting_Agreement.md (Exhibit A)
"""

import json
import os
import requests

SUPABASE_URL = "https://hjuvqpxvfrzwmlqzkpxh.supabase.co"
SERVICE_KEY = os.environ.get("PROJECTS_SUPABASE_SERVICE_ROLE_KEY") or \
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqdXZxcHh2ZnJ6d21scXprcHhoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM1NTIyNSwiZXhwIjoyMDcxOTMxMjI1fQ.AOYbPJPCITnRuGaYbQsbaJy_8fCGkmFL81DzM7h2NdM"
HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

def update_notes(task_id: str, notes: str):
    """Update notes for a task by ID."""
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/project_tasks?id=eq.{task_id}",
        headers=HEADERS,
        json={"notes": notes},
    )
    r.raise_for_status()
    return True

def insert_task(task: dict):
    """Insert a new task."""
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/project_tasks",
        headers={**HEADERS, "Prefer": "return=representation"},
        json=task,
    )
    r.raise_for_status()
    return r.json()


# ─── Contract context notes for existing tasks ──────────────────────────

DELIVERABLE_NOTES = {
    # AI Strategy Document
    "bae2e5cb-d9c1-4c8b-87a5-d83cb43efe9a": (  # Discovery & current-state analysis
        "CONTRACT: Exhibit A, Deliverable 1 — AI Strategy Document\n\n"
        "Evaluate UpTogether's two priority AI use cases:\n"
        "• Agentic application review with external data source consultation for eligibility and verification decisions\n"
        "• Automated benefits counseling for member navigation of public benefits and resources\n\n"
        "This initial deep-dive establishes the foundation for the AI strategy document and Google.org application framing. "
        "Includes assessment of each use case against feasibility, impact potential, and alignment with Google.org challenge criteria "
        "(Impact, Innovative Technology, Feasibility, Scalability)."
    ),
    "7109cbb9-84ef-4754-a207-620feb0a9545": (  # Draft AI strategy framework
        "CONTRACT: Exhibit A, Deliverable 1 — AI Strategy Document\n\n"
        "Produce the draft AI strategy document including:\n"
        "• Assessment of each use case against feasibility, impact potential, and alignment with Google.org criteria\n"
        "• Prioritization recommendation with rationale\n"
        "• AI roadmap connecting the Google.org opportunity to UT's broader technology direction\n"
        "• Consideration of current engineering capacity constraints and platform upgrade priorities\n\n"
        "This draft goes to UT leadership for review in Week 3."
    ),
    "ff51c3c4-2c38-4c25-9383-46668368b985": (  # Review with UT leadership
        "CONTRACT: Exhibit A, Deliverable 3 — Strategy Session\n\n"
        "Present AI strategy findings to Company leadership for review and alignment. "
        "Company provides internal review and feedback within 48 hours (per contract, 'Company Delivery Obligations').\n\n"
        "This review informs the final strategy document and validates the prioritization recommendation before the Google.org application is finalized."
    ),
    "4f41e773-05ab-423c-9ae7-d1ca50ee0d19": (  # Final strategy document delivered
        "CONTRACT: Exhibit A, Deliverable 1 — AI Strategy Document\n\n"
        "Complete, final AI strategy document delivered to UpTogether. Incorporates:\n"
        "• Evaluation of two priority AI use cases\n"
        "• Feasibility and impact assessment against Google.org criteria\n"
        "• Prioritization recommendation with rationale\n"
        "• AI roadmap connecting Google.org opportunity to broader tech direction, including engineering capacity constraints\n\n"
        "This is a work-for-hire deliverable owned by UpTogether per Section 10(d) of the Agreement."
    ),

    # Google.org Application
    "ce62a25e-9387-4d95-81eb-9197dd03209d": (  # Gather all inputs from UT
        "CONTRACT: Exhibit A, 'What Company Provides'\n\n"
        "Company shall provide:\n"
        "• Lightweight access to platform documentation and technical architecture context (via Rachel Bernstein)\n"
        "• Government partnership documentation — MOUs, contracts, letters of support, or similar evidence\n"
        "• Availability of Cesar Aleman, Rachel Bernstein, and Ivanna Neri for kickoff and strategy sessions\n\n"
        "TIMELINE RISK: Per contract 'Company Delivery Obligations,' delays in providing required materials may compress the submission timeline. "
        "Consultant shall use commercially reasonable efforts to meet the deadline but is not liable for Company-caused delays."
    ),
    "ed0097f6-2f9b-4f12-b0c7-f94f419990d8": (  # Draft all narrative responses
        "CONTRACT: Exhibit A, Deliverable 2 — Google.org Impact Challenge Application\n\n"
        "Draft the complete, submission-ready application including:\n"
        "• Positioning of UT's government partnerships for maximum evaluator impact\n"
        "• Framing of AI use cases as transformative applications of generative and agentic AI in public service delivery\n"
        "• Feasibility narrative addressing team capability, technical approach, and implementation plan\n"
        "• Scalability narrative demonstrating potential for replication across government contexts\n\n"
        "All ~25 narrative responses across 8 application sections. See Application Tracker section for individual questions."
    ),
    "736c4ace-2fc5-4221-9c73-b732c9dd252a": (  # UT review & feedback round
        "CONTRACT: Exhibit A, 'Company Delivery Obligations'\n\n"
        "Company provides internal review and feedback on application draft within 48 hours (Weeks 2-3). "
        "This is a contractual obligation — timeline risk clause applies if feedback is delayed.\n\n"
        "Feedback should cover:\n"
        "• Factual accuracy of all claims about UT programs, impact, and partnerships\n"
        "• Alignment with UT's organizational voice and priorities\n"
        "• Any sensitive information that should be excluded\n"
        "• Sign-off from leadership on government partnership framing"
    ),
    "6990693b-5b77-4c39-8c5d-e77d8f4203bc": (  # Final submission on Submittable
        "CONTRACT: Exhibit A, 'Scope Boundaries'\n\n"
        "Company is solely responsible for final review, approval, legal and compliance review, and submission of the Google.org application. "
        "Consultant delivers the submission-ready application but does not submit on Company's behalf.\n\n"
        "Per contract: 'Consultant makes no guarantees regarding the outcome of the Google.org Impact Challenge selection process. "
        "Compensation is owed regardless of application outcome.'\n\n"
        "Deadline: April 3, 2026"
    ),

    # Strategy Session
    "a7e9f7d5-9961-4a36-a9fd-b09e4168c62c": (  # Prepare strategy session agenda & materials
        "CONTRACT: Exhibit A, Deliverable 3 — Strategy Session\n\n"
        "Prepare materials for a 60-minute strategy session with Company leadership. "
        "Session should present AI strategy findings and application positioning.\n\n"
        "Also prepare for a separate application review session with designated team members before final submission."
    ),
    "101f1422-6369-4225-8b01-76ca9e31fd12": (  # Facilitate in-person strategy session
        "CONTRACT: Exhibit A, Deliverable 3 — Strategy Session\n\n"
        "Two components per contract:\n"
        "1. 60-minute strategy session with Company leadership to present AI strategy findings and application positioning\n"
        "2. Application review session with designated team members before final submission\n\n"
        "Scheduled during JT trip (Mar 30 – Apr 3). Must be completed before April 3 submission deadline."
    ),
}

MATERIALS_NOTES = {
    "d3524e3e-5feb-4d54-b19f-5d92a8d93417": (  # Org factual info
        "CONTRACT: Exhibit A, 'What Company Provides'\n\n"
        "Needed for Section I of the Google.org application (Q1-Q10). "
        "Basic organizational facts that only the UT team can provide: legal name, website, year founded, HQ location, annual budget, employee count, CEO info."
    ),
    "eec0f5ce-70b2-4692-857a-1c851e612c7d": (  # Current programs & impact data
        "CONTRACT: Exhibit A, Deliverable 2\n\n"
        "Required for Section II: Impact (Q11-Q19). The application's 'Impact' section is the heart of the application — "
        "Google.org evaluators weight this heavily. Need concrete numbers: total members served, geographic reach, "
        "quantitative outcomes data, program descriptions."
    ),
    "c8bf7434-f750-41b2-adb6-1139a6d36660": (  # Existing tech stack overview
        "CONTRACT: Exhibit A, 'What Company Provides'\n\n"
        "'Lightweight access to platform documentation and technical architecture context (coordinated through Rachel Bernstein)'\n\n"
        "Needed for Section III: Innovative Technology (Q20-Q26) and Section IV: Feasibility (Q27-Q33). "
        "A system diagram, tech stack, data flow, or even a whiteboard photo. This establishes the 'before' state for the AI transformation narrative."
    ),
    "b7a91c0a-cce1-4a7c-88c4-4df4f3a41646": (  # Government partnership details
        "CONTRACT: Exhibit A, 'What Company Provides'\n\n"
        "'Government partnership documentation (MOUs, contracts, letters of support, or similar evidence of government relationships)'\n\n"
        "CRITICAL for Section V: Partnerships (Q34). The Google.org 'AI for Government Innovation' challenge specifically requires "
        "proof of government partnership. A letter of support from at least one government partner is the single most important "
        "supporting document for this application."
    ),
    "0ee98d4e-a9f7-497e-a74a-fbe6034c5c63": (  # Matching/co-funding
        "CONTRACT: Exhibit A, Deliverable 2\n\n"
        "Needed for Section VII: Budget & Timeline (Q43). Google.org evaluators look favorably on organizations that can demonstrate "
        "co-investment. Even a commitment to allocate existing staff time counts."
    ),
    "12fa9cb2-b58c-4994-a267-5b4e05eaf182": (  # Internal AI/data strategy docs
        "CONTRACT: Exhibit A, Deliverable 1\n\n"
        "Needed for the AI Strategy Document and for Sections III-IV of the application. "
        "Any existing AI/ML features, automation, experiments, vendor evaluations, or prior AI exploration. "
        "Even 'we discussed X but haven't built it yet' is useful context."
    ),
    "c7d43de9-e29d-4d32-a1c4-ccfeedd420f6": (  # Member stories
        "Helpful for Impact section narrative (Q11-Q19). Concrete member stories make the application more compelling "
        "to evaluators. One strong anecdote can be worth more than aggregate statistics."
    ),
}

WORKPLAN_NOTES = {
    "8c5eb123-3020-4d25-8ebf-09a5db726168": (  # Week 1
        "CONTRACT: Exhibit A, Timeline — Week 1 (March 10-14)\n\n"
        "'AI use case deep-dive and prioritization. Evaluate agentic application review and automated benefits counseling "
        "use cases against Google.org evaluation criteria (Impact, Innovative Technology, Feasibility, Scalability). "
        "Stress-test feasibility and framing.'\n\n"
        "Key milestone: Kickoff session completed. Discovery pack sent to UT team."
    ),
    "329fe4f1-39af-45a3-bd6f-c253c0d8077c": (  # Week 2
        "CONTRACT: Exhibit A, Timeline — Week 2 (March 17-21)\n\n"
        "'AI strategy document finalized. Google.org application draft complete. Review with Company team for feedback "
        "and internal alignment.'\n\n"
        "Key deliverables due: AI Strategy Document draft, Google.org application draft. "
        "Company feedback expected within 48 hours of delivery."
    ),
    "97b9c430-ff64-458d-81ca-837c7fe1f6cd": (  # Week 3
        "CONTRACT: Exhibit A, Timeline — Week 3 (March 24-28)\n\n"
        "'Application refinement based on team feedback. Final polish and submission preparation.'\n\n"
        "Depends on timely Company feedback from Week 2 review. Strategy session prep also happens this week."
    ),
    "2c08704b-d122-47ec-9d39-26bd2bbdd733": (  # Week 4
        "CONTRACT: Exhibit A, Timeline — Week 4 (March 31 - April 3)\n\n"
        "'Final review, internal sign-off, and submission by April 3 deadline.'\n\n"
        "Justin is on family trip Mar 30-Apr 3. Application must be essentially complete by Friday March 28. "
        "In-person strategy session during this window. Company responsible for final submission."
    ),
}

# Application section context (group-level notes for subsection headers)
APP_SECTION_NOTES = {
    # Section II: Impact — the heart of the application
    "d5322d72-96df-4940-bdfb-1f36427293c9": (  # Q11 - first question in Impact section
        "Section II: Impact is the HEART of the application. Google.org evaluators weight this heavily.\n\n"
        "This question frames the core problem UpTogether addresses. Must connect to government service delivery "
        "to align with the 'AI for Government Innovation' challenge theme.\n\n"
        "CONTRACT: Exhibit A, Deliverable 2 — 'Framing of AI use cases as transformative applications of generative "
        "and agentic AI in public service delivery'"
    ),
    "a5a8a043-d4a3-45ae-90bf-f0fd0bef7df4": (  # Q20 - first question in Innovative Technology
        "Section III: Innovative Technology covers the AI/ML approach.\n\n"
        "CONTRACT: Exhibit A, Deliverable 1 — Must address the two priority AI use cases:\n"
        "1. Agentic application review with external data source consultation\n"
        "2. Automated benefits counseling for member navigation\n\n"
        "The strategy document's prioritization recommendation directly informs which use case to lead with here."
    ),
    "1d2f43e1-5d68-4e67-ba38-3366696dfcab": (  # Q27 - first question in Feasibility
        "Section IV: Feasibility is where we prove UT can actually build this.\n\n"
        "CONTRACT: Exhibit A, Deliverable 2 — 'Feasibility narrative addressing team capability, technical approach, "
        "and implementation plan'\n\n"
        "Needs input from Rachel (tech capability) and Cesar (organizational capacity). "
        "The AI Strategy Document's roadmap should inform the implementation plan here."
    ),
    "a7381009-4de8-456a-b4c1-4ccb7a31b5f8": (  # Q34 - Government partnership
        "Section V: Partnerships is CRITICAL for this challenge.\n\n"
        "The Google.org 'AI for Government Innovation' challenge specifically requires government partnerships. "
        "This is arguably the make-or-break section.\n\n"
        "CONTRACT: Exhibit A, 'What Company Provides' — 'Government partnership documentation (MOUs, contracts, "
        "letters of support, or similar evidence of government relationships)'\n\n"
        "A strong letter of support from a government partner could be the difference between advancing and being cut."
    ),
    "10aa5032-3055-4094-901e-f654785538ad": (  # Q35 - first question in Scalability
        "Section VI: Scalability — demonstrating replication potential.\n\n"
        "CONTRACT: Exhibit A, Deliverable 2 — 'Scalability narrative demonstrating potential for replication "
        "across government contexts'\n\n"
        "Google.org invests in solutions that can scale beyond the initial deployment. "
        "Frame UT's government partnership model as inherently replicable."
    ),
    "0ea31efb-2815-4270-b79f-46ea485893b0": (  # Q41 - Budget
        "Section VII: Budget & Timeline — $1-3M over up to 36 months.\n\n"
        "Must include 3-5 milestones with descriptions, timelines, and budgets. "
        "The AI Strategy Document's roadmap should inform milestone structure.\n\n"
        "Key open question: What is the target grant amount within the $1-3M range? "
        "Budget should reflect realistic implementation costs while being competitive."
    ),
}

OPEN_Q_NOTES = {
    "09ff1dcf-b03a-4eab-aff5-65baf00129ce": (  # Which government partner
        "CRITICAL — directly impacts Section V: Partnerships (Q34) and the required letter of support. "
        "This is the single most important open question. The entire 'AI for Government Innovation' challenge "
        "centers on government partnerships."
    ),
    "f4e491ca-3a24-471a-a082-0103efba4349": (  # Target grant amount
        "Directly impacts Section VII: Budget & Timeline (Q41-Q51). "
        "The budget must be credible — too low looks under-ambitious, too high looks unrealistic. "
        "Need to calibrate against UT's current engineering capacity and the scope of the proposed AI work."
    ),
    "50083d0c-6d41-4fb4-b1db-9fb925c1bf9a": (  # Key personnel
        "Needed for Q50: Key personnel and roles. Google.org evaluators assess whether the team can execute. "
        "Need 3-5 named individuals with relevant AI/tech/program experience. "
        "Contract specifies: Cesar (EVP Membership & Impact), Rachel (Sr. Dir Product & Tech) as key contacts."
    ),
    "cd6ae746-6186-4d10-9eda-7b13ff591e97": (  # Member data
        "Critical for Sections III and IV (Technology & Feasibility). "
        "The AI solution's viability depends on what data UT collects. "
        "Need to understand: data volume, quality, privacy constraints, consent models."
    ),
    "bf99858c-6fc9-4c50-a781-d6c036735edc": (  # Data privacy
        "Impacts Section VIII: Ethics (Q52-Q57) and the overall feasibility narrative. "
        "UT works with vulnerable populations — data privacy and ethical AI considerations "
        "must be front and center. This is both a risk and a differentiator."
    ),
}


def main():
    print("Updating UpTogether tracker tasks with contract context...\n")

    # 1. Update Deliverables notes
    print("=== Deliverables ===")
    for task_id, notes in DELIVERABLE_NOTES.items():
        update_notes(task_id, notes)
        print(f"  Updated {task_id[:8]}")
    print(f"  {len(DELIVERABLE_NOTES)} deliverable tasks updated")

    # 2. Update Materials notes
    print("\n=== Materials ===")
    for task_id, notes in MATERIALS_NOTES.items():
        update_notes(task_id, notes)
        print(f"  Updated {task_id[:8]}")
    print(f"  {len(MATERIALS_NOTES)} material tasks updated")

    # 3. Update Workplan notes
    print("\n=== Workplan ===")
    for task_id, notes in WORKPLAN_NOTES.items():
        update_notes(task_id, notes)
        print(f"  Updated {task_id[:8]}")
    print(f"  {len(WORKPLAN_NOTES)} workplan tasks updated")

    # 4. Update key Application section notes
    print("\n=== Application (key sections) ===")
    for task_id, notes in APP_SECTION_NOTES.items():
        update_notes(task_id, notes)
        print(f"  Updated {task_id[:8]}")
    print(f"  {len(APP_SECTION_NOTES)} application tasks updated")

    # 5. Update Open Questions notes
    print("\n=== Open Questions ===")
    for task_id, notes in OPEN_Q_NOTES.items():
        update_notes(task_id, notes)
        print(f"  Updated {task_id[:8]}")
    print(f"  {len(OPEN_Q_NOTES)} open question tasks updated")

    # 6. Add missing tasks
    print("\n=== Adding missing tasks ===")

    missing_tasks = [
        {
            "project_id": "uptogether",
            "section": "Deliverables",
            "subsection": "Strategy Session",
            "title": "Application review session with UT team",
            "description": "Pre-submission",
            "status": "todo",
            "owner": "Justin",
            "sort_order": 95,
            "notes": (
                "CONTRACT: Exhibit A, Deliverable 3 — Strategy Session\n\n"
                "'Application review session with designated team members before final submission'\n\n"
                "This is a separate deliverable from the 60-minute strategy session with leadership. "
                "The review session focuses specifically on walking through the completed application "
                "with the team to catch factual errors, alignment issues, and get final sign-off."
            ),
        },
        {
            "project_id": "uptogether",
            "section": "Deliverables",
            "subsection": "Google.org Application",
            "title": "Company sign-off on final application",
            "description": "Required before submission",
            "status": "todo",
            "owner": "Cesar",
            "sort_order": 75,
            "notes": (
                "CONTRACT: Exhibit A, 'What Company Provides'\n\n"
                "'Internal sign-off authority for final application submission'\n\n"
                "Company is solely responsible for final review, approval, legal and compliance review, "
                "and submission. This sign-off must happen before the April 3 deadline.\n\n"
                "Per contract Scope Boundaries: 'Consultant will not... submit the application on "
                "Company's behalf.'"
            ),
        },
        {
            "project_id": "uptogether",
            "section": "Deliverables",
            "subsection": "Google.org Application",
            "title": "UT 48-hour review turnaround",
            "description": "Contract obligation",
            "status": "todo",
            "owner": "UT Team",
            "sort_order": 65,
            "notes": (
                "CONTRACT: Exhibit A, 'Company Delivery Obligations'\n\n"
                "'Internal review and feedback on application draft within 48 hours (Week 2-3)'\n\n"
                "This is a contractual obligation on UT's side. If Company delays in providing feedback, "
                "it may compress the timeline. Per contract: 'Consultant shall use commercially reasonable "
                "efforts to meet the original submission deadline but shall not be liable for any delay "
                "in deliverables attributable to Company's delay.'"
            ),
        },
        {
            "project_id": "uptogether",
            "section": "Materials",
            "subsection": "P1 Critical",
            "title": "Platform documentation & architecture context",
            "description": "Via Rachel",
            "status": "todo",
            "owner": "Rachel",
            "sort_order": 5,
            "notes": (
                "CONTRACT: Exhibit A, 'What Company Provides'\n\n"
                "'Lightweight access to platform documentation and technical architecture context "
                "(coordinated through Rachel Bernstein)'\n\n"
                "Doesn't need to be polished — a whiteboard diagram, internal wiki page, or even "
                "a verbal walkthrough that Justin can document. Needed to write credible feasibility "
                "and technology narratives in the application."
            ),
        },
        {
            "project_id": "uptogether",
            "section": "Materials",
            "subsection": "P1 Critical",
            "title": "Team bios for key project leads",
            "description": "2-3 sentences each",
            "status": "todo",
            "owner": "Cesar",
            "sort_order": 35,
            "notes": (
                "CONTRACT: Exhibit A, Deliverable 2\n\n"
                "Application Q50 requires identifying key personnel and roles. "
                "Need 2-3 sentence bios for whoever would lead the AI project if funded: "
                "name, title, relevant experience. Google.org evaluators assess whether the team "
                "can execute the proposed work."
            ),
        },
    ]

    for task in missing_tasks:
        result = insert_task(task)
        title = task["title"]
        print(f"  Added: {title}")

    print(f"  {len(missing_tasks)} new tasks added")

    total = (len(DELIVERABLE_NOTES) + len(MATERIALS_NOTES) + len(WORKPLAN_NOTES) +
             len(APP_SECTION_NOTES) + len(OPEN_Q_NOTES))
    print(f"\n{'='*50}")
    print(f"DONE: {total} tasks updated with contract context, {len(missing_tasks)} new tasks added")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
