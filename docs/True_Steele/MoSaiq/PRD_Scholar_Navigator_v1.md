# iQNNECTED Scholar Navigator — Product Requirements Document
## True Steele Labs x Mo-saIQ

**Version:** 1.0 (Draft)
**Date:** March 2026
**Author:** Justin Steele, True Steele Labs
**Client:** Nikole Collins-Puri, CEO & Co-Founder, Mo-saIQ
**Status:** Draft — Pending Client Review

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-03-04 | 1.0 | Initial draft from discovery recordings + research | JS |
| 2026-03-04 | 1.1 | Revised timeline and estimates for AI-augmented build methodology | JS |

---

## 1. Problem & Context

### The Client

Mo-saIQ is a Durham-based 501(c)(3) (EIN 92-3111629, founded 2023) focused on empowering high-achieving Black and brown youth to persist and thrive in competitive STEM and entrepreneurship pathways. The organization runs a 9-month Scholar Empowerment Program currently serving ~100 scholars across 19 states, supplemented by a Calculus Kickstart summer intensive (with The Calculus Project Inc.), college application boot camps, and the ME2 (Empowerment Exchange) community network.

Mo-saIQ is led by CEO Nikole Collins-Puri with support from co-founders Shawna Young, Paris Andrew, and Tammy Stevens, plus Dr. Roystone Martinez (college advising) and Elaine (Mosaic Mindset curriculum). The operating team is effectively 1-2 people day-to-day.

### The Problem

Schools — especially underresourced ones — lack the capacity to provide personalized STEM pathway counseling. As a result, high-achieving Black and brown students enter competitive academic environments without the confidence, social capital, or navigation tools to thrive. Fragmented systems and high counselor caseloads mean students receive generic advice disconnected from their lived experiences, identities, and aspirations.

Existing alternatives fall short:

| Alternative | What It Gets Right | Where It Falls Short |
|-------------|-------------------|---------------------|
| **Reach Pathways** | Career exploration — connects academics to career paths; strong visualization | Generic across all industries; informational not interactive; doesn't address hidden rules or social dynamics |
| **Project Basta** | Practical workforce navigation — internships, networking, workplace expectations | Engages students too late (college/post-college); key structural decisions already made |
| **School counselors** | Trusted relationship, institutional context | Overwhelmed caseloads; can't personalize STEM pathway guidance at scale |
| **Generic college platforms** | Information delivery at scale | No cultural context; no identity-centered navigation; no ongoing adaptation |

Mo-saIQ's scholars are high-potential students — often first in their family or community to pursue selective STEM pathways — who need more than information. They need a tool that sees them, understands their context, and helps them make strategic decisions at the moments that matter most.

### Why Now

- Mo-saIQ has completed one full year of the Scholar Empowerment Program with real scholars and proven curriculum
- The iQNNECTED platform was announced publicly (Spring 2025 launch on the website) but has not been built
- Mo-saIQ is going through the Catapult accelerator and refining its business model
- The current tech stack (WordPress + Wufoo + Donorbox + Zoom + Google Classroom) is fragmented — scholars experience friction, data is siloed, and outcomes can't be measured
- Nikole has deep clarity on the product vision but no technical capacity to execute

### Current State

**Scholar journey today:**
1. Scholar discovers Mo-saIQ (website, social media, referral)
2. Completes Wufoo application (grades, language, interests, counselor engagement, support areas)
3. Accepted into 9-month Empowerment Program ($750, financial aid available)
4. Virtual sessions 1-2x/month, ~2 hours each (college advising + Mosaic Mindset)
5. Between sessions: unclear — no structured digital engagement
6. Program ends: no persistent connection unless scholar stays in ME2 network
7. Tracking: presumed manual (spreadsheets, email) — specifics unknown

**Key pain points in current state:**
- No personalized pathway guidance — sessions are group-based
- No way to track individual scholar progress or milestones
- No between-session engagement mechanism
- No outcomes measurement infrastructure
- Program value evaporates after 9 months — no persistent tool

---

## 2. Product Vision & Success Metrics

### North Star

The iQNNECTED Scholar Navigator is a personalized guidance system that helps high-achieving Black and brown students define a STEM or entrepreneurship goal, chart a clear path to get there, and navigate the hidden rules of competitive academic spaces — with their identity as a strength, not a barrier.

The simplest metaphor: **"Waze for a scholar's STEM and entrepreneurship journey."**

### Success Metrics (12 Months Post-Launch)

| Metric | Target | Type |
|--------|--------|------|
| **Peer referrals** — scholars organically recommending the platform | 30%+ of new users come via peer referral | Adoption |
| **Active engagement** — scholars using the platform as a decision-making tool, not a passive checklist | 60%+ monthly active rate among enrolled scholars | Engagement |
| **Confidence & belonging** — measurable improvement in self-reported confidence, clarity, and community | Positive movement on pre/post pulse surveys | Outcome |
| **Roadmap completion** — scholars with a completed roadmap within 14 days of onboarding | 80%+ | Product |
| **Milestone progress** — scholars completing grade-appropriate milestones on schedule | 50%+ milestone completion rate | Outcome |

### Non-Goals (Explicit)

- **Not a tutoring platform.** The Navigator does not deliver math instruction, test prep, or coursework. It points scholars to resources and programs (including Mo-saIQ's own, like Calculus Kickstart), but it is not an LMS.
- **Not a social media app.** Community and social capital features are part of the long-term vision, but v1 is not building a social network. The core loop is assessment → roadmap → milestones.
- **Not a replacement for human advising.** The platform augments Dr. Roystone, Elaine, and Nikole — it doesn't replace them. AI generates roadmaps and nudges; humans make the high-stakes decisions alongside scholars.
- **Not a general-purpose college planning tool.** The Navigator is specifically for STEM and entrepreneurship pathways, specifically for students of color navigating spaces not designed for them. Generic is the enemy.

---

## 3. Users & Journeys

### User Roles

| Role | Who | What They Need | Phase |
|------|-----|---------------|-------|
| **Scholar** (primary) | High school students, grades 9-12; primarily Black, Latinx, Indigenous; high-achieving, high-potential | Complete assessment, receive personalized roadmap, track milestones, get nudges, explore opportunities | Phase 1 |
| **Admin** (Nikole) | Mo-saIQ CEO, manages all scholars and program operations | View all scholars, track engagement, manage content, see aggregate analytics | Phase 1 |
| **Advisor** (Dr. Roystone) | College advisor working with scholars on selective admissions | View assigned scholars' profiles + roadmaps, add advising notes, track college prep milestones | Phase 2 |
| **Caregiver** | Parent/guardian of minor scholar | View child's progress (read-only), receive updates, provide consent | Phase 2 |
| **Mentor** | Matched adult in scholar's network | Communicate with scholar (moderated), log interactions, view mentee's goals | Phase 3 |

### Primary User Journey (Scholar — Phase 1)

```
1. DISCOVER → Scholar learns about Mo-saIQ (referral, social, website)
       ↓
2. APPLY → Completes program application (existing Wufoo process OR in-platform)
       ↓
3. ACCEPT + CONSENT → Accepted into program; guardian consent collected for minors
       ↓
4. ONBOARD → First login; greeted with assessment experience
       ↓
5. ASSESS → Completes scenario-based assessment (interests, strengths,
             context, goals, environments where they thrive)
             Duration: 15-25 minutes | Can save and resume
       ↓
6. PROFILE → System generates scholar profile summary
             Scholar reviews: "Does this feel like me?"
             Can adjust/refine before proceeding
       ↓
7. ROADMAP → AI generates personalized roadmap:
             - 2-3 recommended STEM/entrepreneurship pathways
             - Academic preparation needed (courses, prerequisites, gaps)
             - Grade-level-specific milestones (what to do THIS year)
             - Aligned opportunities (programs, internships, competitions)
             Scholar reviews and selects primary pathway
       ↓
8. NAVIGATE → Ongoing engagement:
             - Dashboard shows current milestones + next actions
             - Nudges/reminders for upcoming deadlines
             - Affirmations and confidence-building prompts
             - Pressure tests: "Is this what you really want?"
             - Milestone check-off as scholar progresses
       ↓
9. ADAPT → Periodic pulse checks:
             - Has anything changed? New interests?
             - Roadmap updates dynamically
             - Scholar remains the driver, not a passenger
       ↓
10. PERSIST → After program ends, scholar retains access
              Roadmap continues through college transition
```

### Admin Journey (Nikole — Phase 1)

```
1. Dashboard → Overview of all scholars (enrollment, engagement, milestone progress)
2. Scholar List → Search, filter, sort by cohort/grade/engagement/milestone status
3. Scholar Detail → Individual profile, roadmap, milestone progress, activity log
4. Content Management → Manage assessment scenarios, opportunity listings, affirmation content
5. Analytics → Aggregate metrics: completion rates, engagement trends, milestone progress by cohort
```

---

## 4. Feature Requirements

### Epic 1: Authentication & User Management
**Why:** Scholars need secure accounts; guardians must consent for minors; admin needs control.
**Priority:** Must

| Feature | Description | Acceptance Criteria | Size |
|---------|-------------|-------------------|------|
| Scholar registration | Email-based sign-up with profile basics (name, grade, school, location) | Given a new scholar, when they register, then account is created and email verified | S |
| Guardian consent flow | Minor scholars trigger a consent request to guardian email; guardian reviews and approves before scholar can proceed to assessment | Given a minor scholar, when they register, then guardian receives consent request; scholar cannot proceed until approved | M |
| Admin login | Nikole access with full platform visibility | Given admin credentials, when login succeeds, then admin sees the admin dashboard | XS |
| Role-based access | Scholars see their own data; admin sees all data; future roles (advisor, caregiver) are architecturally supported | Given a scholar, when they log in, they cannot access other scholars' data or admin views | S |
| Password reset + session management | Standard auth flows | Given a user who forgot their password, when they request reset, then they receive a reset link that expires in 15 minutes | XS |

**Epic total: ~3-4 hours** (Supabase auth is a solved pattern; guardian consent flow is the main complexity)

---

### Epic 2: Assessment Engine
**Why:** The assessment is the entry point to the entire experience. It must feel engaging, reflective, and identity-affirming — not like a form.
**Priority:** Must

| Feature | Description | Acceptance Criteria | Size |
|---------|-------------|-------------------|------|
| Scenario-based assessment flow | Multi-step experience presenting scenarios (not static questions) that reveal interests, strengths, goals, cultural identity, environments, and career curiosity. Inspired by 16 Personalities style. | Given a scholar starting the assessment, when they proceed through scenarios, then each response captures structured data mapped to profile dimensions; flow feels conversational, not form-like | L |
| Progress save + resume | Scholar can close the app mid-assessment and resume later from where they left off | Given a scholar who completed 60% of the assessment, when they return, then they start at the next incomplete section | S |
| Assessment content framework | Structured format for scenarios that Mo-saIQ staff can author and update; supports adding/editing/reordering scenarios without code changes | Given an admin, when they edit a scenario in the CMS, then the change reflects in the scholar experience within minutes | M |
| Mobile-optimized experience | Assessment works on phones (primary device for target demographic) with touch-friendly interactions | Given a scholar on a mobile phone (320px-428px viewport), when they take the assessment, then all interactions are usable without horizontal scrolling or tiny tap targets | S |

**Epic total: ~10-14 hours** (multi-step UI is the real work; scenario content framework is the creative bottleneck, not the code)

**Content dependency:** Mo-saIQ must provide or co-create the assessment scenarios. True Steele Labs designs the framework and initial set of 15-20 scenarios; Mo-saIQ refines for cultural authenticity and program alignment.

---

### Epic 3: Profile Generation
**Why:** The profile is the bridge between the assessment and the roadmap. It must make the scholar feel seen — "this is me."
**Priority:** Must

| Feature | Description | Acceptance Criteria | Size |
|---------|-------------|-------------------|------|
| AI-powered profile synthesis | System analyzes assessment responses and generates a narrative profile summary: strengths, interests, pathway affinities, growth areas, preferred environments | Given a completed assessment, when the system processes responses, then a profile summary is generated within 30 seconds that feels personalized (not generic) | M |
| Scholar review + adjust | Scholar sees their profile and can flag anything that doesn't feel right ("This doesn't sound like me"); adjustments feed back into the profile | Given a generated profile, when the scholar reviews it, then they can adjust key dimensions before proceeding to roadmap | M |
| Culturally affirming framing | Profile language positions identity as a strength; avoids deficit framing; reflects Mo-saIQ's voice | Given any generated profile, when reviewed by Mo-saIQ staff, then the language consistently frames the scholar's background as an asset | S |

**Epic total: ~5-7 hours** (mostly prompt engineering + display; Claude Code handles the UI)

---

### Epic 4: Personalized Roadmap
**Why:** This is the core value proposition — "GPS for your STEM journey." The roadmap must be specific, actionable, grade-appropriate, and adaptive.
**Priority:** Must

| Feature | Description | Acceptance Criteria | Size |
|---------|-------------|-------------------|------|
| AI roadmap generation | System generates a personalized roadmap based on profile, grade level, geography, and stated goals. Includes: 2-3 recommended pathways, academic prep needed, aligned opportunities, and grade-specific milestones | Given a completed profile for a 10th grader interested in biomedical engineering in rural NC, when the roadmap generates, then it includes specific course recommendations, relevant summer programs accessible from their area, and milestones appropriate for a 10th grader | L |
| Roadmap display | Visual timeline/roadmap showing milestones organized by semester/year with clear "what to do now" prioritization | Given a generated roadmap, when the scholar views it, then they see current-period milestones prominently with future milestones visible but not overwhelming | L |
| Pathway selection | Scholar reviews 2-3 recommended pathways and selects a primary focus; roadmap adapts to emphasize that pathway | Given 3 recommended pathways, when the scholar selects "biomedical engineering," then milestones and opportunities reorder to prioritize that pathway | M |
| Milestone detail | Each milestone expands to show: what it is, why it matters, how to do it, and resources/links | Given a milestone "Register for AP Chemistry," when the scholar taps it, then they see context ("This course is a prerequisite for competitive pre-med programs"), action steps, and a deadline if applicable | M |
| Roadmap adaptation | When scholar updates their profile or interests change (via pulse check or manual edit), the roadmap recalculates and notifies of changes | Given a scholar who shifts interest from engineering to entrepreneurship, when they update their profile, then the roadmap regenerates with new pathway recommendations and a clear "here's what changed" summary | M |

**Epic total: ~14-20 hours** (most complex epic — AI logic, prompt iteration, visualization, and adaptation logic)

**Content dependency:** Roadmap generation requires a structured dataset of STEM/entrepreneurship pathways, prerequisite courses, and aligned opportunities. See Section 7 (Content Requirements) for sourcing approach.

---

### Epic 5: Scholar Dashboard
**Why:** The daily touchpoint. Must feel supportive and simplifying, not demanding.
**Priority:** Must

| Feature | Description | Acceptance Criteria | Size |
|---------|-------------|-------------------|------|
| Dashboard home | Shows: current milestone progress, next 2-3 actions, recent affirmation/nudge, and roadmap summary | Given a scholar logging in, when they see the dashboard, then the most important current action is immediately visible without scrolling | M |
| Milestone tracker | Visual progress through the roadmap; scholars can mark milestones complete with optional reflection note | Given a scholar who completed "Submit summer program application," when they mark it done, then progress updates, a congratulatory affirmation displays, and the next milestone becomes prominent | M |
| Nudges + affirmations | Contextual messages: deadline reminders, affirmations, and pressure-test prompts ("Is this what you really want, or what you think you have to do?") | Given a scholarship deadline in 2 weeks, when the scholar opens the dashboard, then they see a nudge with the deadline and a direct link to more info | S |
| Profile view + edit | Scholar can view and update their profile, triggering roadmap recalculation | Given a scholar editing their profile, when they change their primary interest, then they're prompted: "This will update your roadmap. Continue?" | S |

**Epic total: ~6-8 hours**

---

### Epic 6: Admin Dashboard
**Why:** Nikole needs visibility into scholar engagement and program health without being a bottleneck.
**Priority:** Must

| Feature | Description | Acceptance Criteria | Size |
|---------|-------------|-------------------|------|
| Scholar management | List all scholars with search, filter (by cohort, grade, state, engagement level, milestone status), and sort | Given 100 scholars, when admin filters by "10th grade + low engagement," then the list shows matching scholars with last-active date | M |
| Scholar detail view | See individual scholar's profile, roadmap, milestone progress, activity log, and engagement history | Given a specific scholar, when admin views their detail page, then all information is visible on one page without needing to switch between multiple tools | M |
| Aggregate analytics | Dashboard showing: total enrolled, assessment completion rate, roadmap completion rate, milestone progress distribution, engagement trends over time | Given the admin dashboard, when loaded, then key metrics are visible with trend indicators (up/down vs. prior period) | M |
| Content management | CRUD interface for assessment scenarios, opportunity listings, and affirmation/nudge content | Given an admin, when they add a new scholarship opportunity, then it becomes available in scholars' roadmap recommendations within the next roadmap refresh | L |

**Epic total: ~8-12 hours** (CRUD + analytics are Claude Code's sweet spot)

---

### Epic 7: AI Integration & Guardrails
**Why:** AI powers the assessment-to-roadmap pipeline. It must be culturally affirming, never generic, and grounded in Mo-saIQ's frameworks.
**Priority:** Must

| Feature | Description | Acceptance Criteria | Size |
|---------|-------------|-------------------|------|
| LLM integration for profile + roadmap | Claude or GPT integration for generating profile summaries and personalized roadmaps from assessment data | Given assessment data, when the LLM generates a profile, then it completes in <30 seconds and produces structured output matching the required schema | L |
| Culturally affirming prompt engineering | System prompts grounded in Mo-saIQ's voice, frameworks, and scholar stories; explicit instructions to avoid generic advice, deficit framing, and Silicon Valley-centric narratives | Given any LLM-generated content, when reviewed, then it consistently: positions identity as strength, acknowledges systemic dynamics, provides context not just information, and references diverse role models | L |
| Output quality guardrails | Content filtering to catch and prevent: generic platitudes, harmful stereotypes, inaccurate information, overwhelming tone | Given a generated roadmap, when it contains a generic statement like "work hard and join clubs," then the guardrail flags it for regeneration | M |
| Affirmation + nudge generation | AI generates contextual affirmations and nudges based on scholar's profile, progress, and upcoming milestones | Given a scholar approaching a deadline, when the system generates a nudge, then it references their specific context (not a generic reminder) | M |

**Epic total: ~14-20 hours** (prompt engineering is iterative — generate, review with Mo-saIQ, refine, repeat; guardrail testing can't be rushed)

---

### Epic 8: Design & Visual Identity
**Why:** The platform must feel culturally affirming visually — not corporate, not generic, not "built for someone else."
**Priority:** Must

| Feature | Description | Acceptance Criteria | Size |
|---------|-------------|-------------------|------|
| UI/UX design system | Component library, color palette, typography, and visual language that reflects Mo-saIQ's brand and feels culturally affirming to the target demographic | Given the design system, when reviewed by Mo-saIQ staff and 3-5 scholars, then feedback confirms it feels "like it was built for us" | L |
| Assessment flow design | Scenario-based UX that feels engaging and reflective, not like a form. Interactions designed for mobile-first with visual variety | Given the assessment prototype, when tested with 3-5 scholars, then completion rate is >80% and qualitative feedback confirms it felt engaging | L |
| Roadmap visualization | Clear, motivating visual representation of the scholar's journey — current position, milestones ahead, progress made | Given the roadmap design, when viewed on mobile, then the scholar can immediately identify "where I am" and "what's next" | M |
| Dashboard and admin screens | Clean, functional layouts for daily use | Standard responsive design best practices | M |

**Epic total: ~12-16 hours** (Tailwind + component library is fast; culturally affirming visual identity needs creative iteration with Mo-saIQ)

---

### Epic 9: Infrastructure & DevOps
**Why:** Production-quality hosting, security, and deployment.
**Priority:** Must

| Feature | Description | Acceptance Criteria | Size |
|---------|-------------|-------------------|------|
| Project setup | Next.js (or comparable) + Supabase, hosted on Vercel or similar | Given the production environment, when deployed, then the app loads in <2 seconds on 4G mobile | M |
| Database design | Schema for scholars, assessments, profiles, roadmaps, milestones, content, and admin data | Given the schema, when reviewed, then it supports all Phase 1 features with room for Phase 2 extension | M |
| CI/CD pipeline | Automated testing and deployment on merge to main | Standard best practices | S |
| SSL, encryption, secure auth | HTTPS, encrypted data at rest, secure session management | Given the production app, when security-scanned, then no critical or high vulnerabilities | S |

**Epic total: ~2-3 hours** (Next.js + Supabase + Vercel is a solved pattern; CI/CD is built-in with Vercel)

---

### Epic 10: QA & Testing
**Priority:** Must

| Feature | Description | Size |
|---------|-------------|------|
| End-to-end testing | Full scholar journey: register → consent → assess → profile → roadmap → milestones | M |
| Mobile testing | Test on iOS Safari + Android Chrome across 3 device sizes | S |
| AI output testing | Review 20+ generated profiles and roadmaps for quality, cultural sensitivity, accuracy | M |
| Admin flow testing | Full admin journey: login → scholar list → detail → content management → analytics | S |
| Accessibility | WCAG 2.1 AA compliance check on all scholar-facing screens | S |

**Epic total: ~8-12 hours** (Claude Code generates test suites from working code; AI output quality review with Mo-saIQ is the real time investment)

---

### Estimation Summary

True Steele Labs builds with Claude Code (Anthropic's AI-native development CLI). This compresses actual build time 3-5x compared to traditional development. Calendar time is driven by client feedback loops, content dependencies, and pilot schedules — not code production.

| Epic | Priority | Build Hours (AI-Augmented) |
|------|----------|--------------------------|
| 1. Authentication & User Management | Must | 3-4 |
| 2. Assessment Engine | Must | 10-14 |
| 3. Profile Generation | Must | 5-7 |
| 4. Personalized Roadmap | Must | 14-20 |
| 5. Scholar Dashboard | Must | 6-8 |
| 6. Admin Dashboard | Must | 8-12 |
| 7. AI Integration & Guardrails | Must | 14-20 |
| 8. Design & Visual Identity | Must | 12-16 |
| 9. Infrastructure & DevOps | Must | 2-3 |
| 10. QA & Testing | Must | 8-12 |
| **Subtotal** | | **82-116** |
| **Contingency (25%)** | | **21-29** |
| **Total Build Hours** | | **~103-145** |
| **Calendar Time** | | **~8 weeks** |

Calendar time reflects a maximum of 15 hours/week dedicated to this project (True Steele Labs runs concurrent ventures). At that pace, the build — not client feedback — drives the calendar. Content delivery and design reviews from Mo-saIQ run in parallel with build sprints.

---

## 5. Non-Functional Requirements

### Privacy & Safeguarding (Critical)

Mo-saIQ serves minors and collects sensitive data (race/ethnicity, academic records, geographic location). The platform must:

- **Parental/guardian consent** required before any minor can create an account or submit assessment data
- **Data minimization** — collect only what's needed for the roadmap; no extraneous personal data
- **Role-based access** — scholars see only their own data; admin sees all; future advisor role sees only assigned scholars
- **No PII in AI prompts** — assessment data sent to LLMs must be anonymized/pseudonymized
- **Data retention policy** — define how long scholar data is stored after program completion
- **Encryption** — data encrypted at rest and in transit (TLS 1.3, AES-256)
- **COPPA awareness** — while scholars are primarily 14-18 (not under 13), the consent flow should be robust enough to satisfy concerned parents and institutional partners

### Performance

- Page load: < 2 seconds on 4G mobile connection
- AI generation (profile + roadmap): < 30 seconds
- 99.5% uptime (standard for early-stage production app)

### Device & Browser Support

- **Primary:** Mobile web (iOS Safari, Android Chrome) — scholars' primary device
- **Secondary:** Desktop web (Chrome, Safari, Firefox, Edge)
- **Native app:** Not in scope for any phase. Progressive Web App (PWA) capabilities for home screen install and offline assessment resume.

### Accessibility

- WCAG 2.1 AA compliance on all scholar-facing screens
- Screen reader compatibility
- Minimum touch target sizes (44x44px)
- Color contrast ratios meeting AA standards

### Language

- **Phase 1:** English only
- **Phase 2+:** Multilingual support (Spanish, Portuguese, Creole) — architecturally supported from Phase 1 (i18n-ready string externalization) but not translated

---

## 6. Technical Approach

### Recommended Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | Next.js + React + Tailwind CSS | Fast development, excellent mobile web performance, strong ecosystem |
| **Backend / Database** | Supabase (PostgreSQL + Auth + Storage) | Managed backend; built-in auth with email/magic link; row-level security for RBAC; real-time capabilities for future phases |
| **AI** | Claude API (Anthropic) or OpenAI GPT | Profile generation, roadmap creation, affirmation/nudge content; model selection based on cost/quality testing |
| **Hosting** | Vercel | Zero-config Next.js deployment, edge functions, preview deploys |
| **CMS** | Admin panel (custom-built) | Assessment scenarios, opportunity listings, and affirmation content managed by Mo-saIQ staff directly |

### Integration Points

| System | Integration | Phase |
|--------|------------|-------|
| **Email (transactional)** | Resend or SendGrid — account verification, consent requests, notifications | Phase 1 |
| **LLM API** | Profile + roadmap generation, nudge content | Phase 1 |
| **Opportunity data sources** | Manual entry in Phase 1; API integrations (scholarship DBs, internship boards) in Phase 2+ | Phase 1 (manual), Phase 2 (automated) |
| **Analytics** | PostHog or Mixpanel — engagement tracking, funnel analysis | Phase 1 |
| **Calendar** | Google Calendar integration for session scheduling and reminders | Phase 2 |

### Data Architecture

```
scholars
  ├── id, email, name, grade, school, state, zip
  ├── guardian_email, consent_status, consent_date
  ├── assessment_responses (JSONB)
  ├── profile_summary (JSONB — AI-generated)
  ├── created_at, last_active_at
  │
  ├── roadmaps (1:many)
  │     ├── id, scholar_id, pathway, version
  │     ├── milestones (JSONB array)
  │     ├── opportunities (JSONB array)
  │     ├── generated_at, model_used
  │     └── is_active
  │
  ├── milestone_progress (1:many)
  │     ├── id, scholar_id, milestone_id
  │     ├── status (pending/in_progress/completed/skipped)
  │     ├── completed_at, reflection_note
  │     └── created_at
  │
  └── activity_log (1:many)
        ├── id, scholar_id, action, metadata
        └── timestamp

assessment_content
  ├── id, scenario_text, scenario_type, order
  ├── response_options (JSONB)
  ├── dimension_mapping (which profile dimensions this informs)
  └── is_active

opportunity_listings
  ├── id, title, description, type (internship/program/scholarship/competition)
  ├── url, deadline, eligibility_criteria
  ├── states_available, grade_levels
  ├── pathways (STEM subfields this applies to)
  └── is_active

affirmation_content
  ├── id, text, context_tags, trigger_conditions
  └── is_active
```

---

## 7. Content & Asset Requirements

This section is critical. The Scholar Navigator requires significant content that does not currently exist in digital form.

### Content True Steele Labs Creates

| Content | Description | Effort |
|---------|-------------|--------|
| Assessment framework | Structural design: dimensions measured, scenario format, scoring logic, profile output schema | Included in Phase 1 |
| Initial assessment scenarios (15-20) | Draft scenarios for the v1 assessment based on Mo-saIQ's program pillars | Included in Phase 1 |
| Roadmap generation prompts | LLM prompts that produce culturally affirming, specific, grade-appropriate roadmaps | Included in Phase 1 |
| Affirmation + nudge templates (20-30) | Starter set of contextual affirmations and nudges | Included in Phase 1 |
| UI copy | All interface text, labels, empty states, error messages, onboarding copy | Included in Phase 1 |

### Content Mo-saIQ Provides (Client Responsibility)

| Content | Description | Deadline |
|---------|-------------|----------|
| Assessment scenario review + refinement | Review and refine the initial 15-20 scenarios for cultural authenticity and program alignment | Week 3 |
| Opportunity listings (initial 30-50) | Curated list of STEM programs, internships, scholarships, competitions relevant to Mo-saIQ scholars — title, URL, eligibility, deadlines | Week 4 |
| Mosaic Mindset content excerpts | Key frameworks, principles, or language from the curriculum that should inform the AI's voice | Week 2 |
| Scholar stories / role model profiles (5-10) | Anonymized scholar success stories or profiles of innovators of color that can be embedded in the experience | Week 5 |
| Brand assets | Logo (SVG), color palette, any existing brand guidelines | Week 1 |
| Pilot scholar cohort | 10-20 scholars who will beta test the platform with active engagement | Week 5 |

> **Deadline enforcement:** Content not delivered by the specified week will push dependent features to the following sprint. True Steele Labs will use placeholder content during development, but the platform cannot launch to scholars with placeholder data.

### Content Out of Scope

- Full Mosaic Mindset curriculum digitization
- Full college advising curriculum digitization
- Math/science practice modules or gamified content
- Multilingual translations
- Marketing website copy or redesign
- Ongoing opportunity database maintenance (post-launch)

---

## 8. Assumptions & Risks

### Assumptions

| # | Assumption | If Wrong, Impact |
|---|-----------|-----------------|
| A1 | Mo-saIQ can provide branded visual assets (logo, colors) by Week 1 | Design work blocked; 1-week delay |
| A2 | Guardian consent can be collected via email (no wet signature or notarized form required) | Legal review needed; potential 2-week delay + additional cost |
| A3 | Mo-saIQ's existing Wufoo application process continues separately; platform does not replace the application/acceptance flow in Phase 1 | If in-scope, adds ~40 hours and 1-2 weeks |
| A4 | The assessment can be designed with 15-20 scenarios and still produce meaningful profile differentiation | If more scenarios needed, content creation timeline extends |
| A5 | LLM-generated roadmaps, with proper prompt engineering and content guardrails, can produce consistently culturally affirming output | If AI quality is insufficient, fallback to template-based roadmaps with human curation (adds effort) |
| A6 | Scholars have consistent access to a smartphone with a web browser and data/wifi | If access is a barrier, offline-first architecture needed (significant scope increase) |
| A7 | 10-20 scholars are available for beta testing in the pilot window | If fewer, pilot feedback may be insufficient to validate the product |

### Dependencies

| # | Dependency | Owner | Impact if Delayed |
|---|-----------|-------|-------------------|
| D1 | Mo-saIQ content deliverables (see Section 7) | Mo-saIQ | Timeline shifts 1:1 with content delays |
| D2 | LLM API availability and pricing stability | Anthropic / OpenAI | Minimal risk; fallback provider available |
| D3 | Pilot scholar recruitment and onboarding | Mo-saIQ | Cannot validate product without real users |
| D4 | Domain and hosting account setup | Mo-saIQ (domain) / TSL (hosting) | Minor; can use staging URL for pilot |

### Risks

| Risk | Type | Likelihood | Impact | Mitigation |
|------|------|-----------|--------|------------|
| AI output feels generic or tone-deaf | Feasibility | Medium | High | Invest in prompt engineering; test with Mo-saIQ staff and 3-5 scholars before pilot; build feedback mechanism for flagging poor output |
| Scholars don't engage beyond initial assessment | Value | Medium | High | Design assessment to be intrinsically rewarding; surface immediate value (profile + roadmap) within first session; test engagement flow with real scholars early |
| Opportunity database is too thin to be useful | Value | Medium | Medium | Launch with curated 30-50 high-quality listings rather than a comprehensive but shallow database; quality over quantity |
| Content dependencies delay launch | Dependency | High | Medium | Start with placeholder content; design content pipeline so Mo-saIQ can add content independently post-launch; build content management tools early |
| Platform increases anxiety instead of reducing it | Value | Low-Medium | High | Prioritize "what matters now" over "everything you should do"; tone audit with scholars; Nikole reviews all nudge/reminder copy |
| Guardian consent creates friction for sign-up | Usability | Medium | Medium | Make consent flow as frictionless as possible (email-based, one-click approval); track drop-off rate |

### Open Questions

| # | Question | Owner | Due | Impact if Unresolved |
|---|----------|-------|-----|---------------------|
| Q1 | What does the current scholar tracking process actually look like? (Spreadsheet? Doc? Nikole's memory?) | Mo-saIQ | Pre-kickoff | Affects data migration and admin dashboard design |
| Q2 | Does Mo-saIQ have existing consent/release forms for minors in digital programs? | Mo-saIQ | Pre-kickoff | Affects consent flow design |
| Q3 | What specific STEM pathways should the roadmap cover in v1? (All STEM + entrepreneurship, or a focused subset?) | Mo-saIQ + TSL | Week 1 | Affects content scope and AI prompt design |
| Q4 | Budget and funding sources for this project? | Mo-saIQ | Pre-proposal | Determines which tier/phase is feasible |
| Q5 | Has Nikole recorded Voice Modules NC2, NC4, and NC5 from the discovery pack? | Mo-saIQ | Pre-kickoff | NC2 (current journey) and NC5 (roles, privacy, MVP, pilot) contain critical details |
| Q6 | What is the target launch date? Is there a Catapult demo day or grant milestone driving the timeline? | Mo-saIQ | Pre-proposal | Determines phase and timeline |

---

## 9. Phasing & Roadmap

### Phase 1: Core Navigator MVP
**Duration:** ~8 weeks | **Goal:** Assessment → Profile → Roadmap → Milestone Tracker — the core loop, in scholars' hands.

Includes all "Must" features from Epics 1-10 above.

**What a scholar can do in Phase 1:**
- Create an account (with guardian consent)
- Complete a scenario-based assessment
- Receive a personalized profile and roadmap
- View grade-specific milestones and next actions
- Mark milestones complete with reflections
- Receive nudges and affirmations
- Update their profile and see roadmap adapt

**What Nikole can do in Phase 1:**
- View all scholars and their progress
- Manage assessment content and opportunity listings
- See aggregate engagement analytics

**What Phase 1 intentionally excludes:**
- Opportunity database with external API feeds (uses curated manual listings)
- Advisor portal (Dr. Roystone)
- Caregiver portal
- Community/social features
- Mentorship matching
- Gamification
- Multilingual support (i18n-ready architecture, English content only)
- Native mobile app
- Integration with existing Wufoo application process

---

### Phase 2: Expand & Engage (Separate Engagement)
**Duration:** 4-6 weeks | **Goal:** Deepen engagement, build social capital, and extend the platform to advisors and caregivers.

| Feature | Description | Priority |
|---------|-------------|----------|
| Social capital network | Scholar-to-scholar connections. "Does anybody in my network know about this?" Scholars can see peers on similar pathways, share milestones, ask questions. Think early-stage LinkedIn for scholars. This is central to Nikole's vision and the first priority for Phase 2. | Should |
| AI mentor chatbot | Conversational AI with a relatable persona grounded in Mo-saIQ's voice and scholar stories. Scholars can ask questions, get encouragement, and pressure-test decisions in a chat interface that feels like talking to someone who gets it. | Should |
| Opportunity engine v2 | API-fed opportunity database with scholarship, internship, and program listings from external sources; smart matching to scholar profiles | Should |
| Advisor portal | Dr. Roystone can view assigned scholars, add advising notes, track college prep milestones | Should |
| Caregiver view | Read-only portal for guardians to see child's progress and upcoming milestones | Should |
| Notification system | Email + push notifications for deadlines, nudges, affirmations, milestone celebrations | Should |
| Enhanced analytics | Cohort comparisons, funnel analysis, outcome tracking | Should |
| Pulse check surveys | In-app micro-surveys for confidence, clarity, and belonging measurement | Should |
| Live session integration | In-platform scheduling and access for Mo-saIQ's existing virtual sessions (college prep, Calculus Kickstart, boot camps). Replaces the current Zoom/Google Classroom setup. | Should |

---

### Phase 3: Community & Scale (Future)
**Goal:** Full community experience and social media engagement patterns.

| Feature | Description | Priority |
|---------|-------------|----------|
| Social media engagement layer | Quick-reaction engagement (likes, hearts, celebrations on peer milestones), visual feed of activity, behavioral patterns that mirror how scholars already use their phones | Could |
| Peer community feed | Moderated feed where scholars share wins, ask questions, and connect. 12th graders sharing college acceptances, 9th graders asking questions. | Could |
| Mentorship matching | Match scholars with mentors based on pathway, interests, and geography | Could |
| Gamification | Points, badges, or levels tied to milestone completion and engagement | Could |
| Multilingual support | Spanish, Portuguese, Creole translations of all content and UI | Could |
| In-platform application | Replace Wufoo with native program application and enrollment | Could |
| Gamified math practice modules | Interactive practice content for calculus, physics, coding | Won't (separate product) |

---

## 10. Timeline & Milestones (Phase 1)

True Steele Labs builds with Claude Code (Anthropic's AI-native CLI), which compresses actual build effort 3-5x compared to traditional development. Calendar time reflects a maximum of 15 hours/week dedicated to this project. Content delivery and design reviews from Mo-saIQ run in parallel with build sprints.

| Week | Milestone | Deliverables | Client Actions |
|------|-----------|-------------|----------------|
| **0** | **Kickoff** | Project plan, comms channel, dev environment setup | Provide brand assets, domain, introduce pilot cohort leads |
| **1** | **Design + Architecture** | Wireframes, design system, database schema, AI prompt prototypes, assessment framework | Review wireframes; deliver Mosaic Mindset content excerpts |
| **2-3** | **Core Build** | Auth + onboarding + assessment engine + profile generation deployed to staging | Refine assessment scenarios for cultural authenticity; deliver opportunity listings |
| **4-5** | **Full Build** | Roadmap engine + scholar dashboard + admin dashboard + content CMS deployed to staging | Deliver scholar stories / role model profiles; recruit pilot scholars |
| **6-7** | **Pilot + QA** | Pilot scholars using the platform; bug fixes, AI quality tuning, UX refinements based on live feedback | Support pilot scholars; gather and relay feedback |
| **8** | **Launch + Handoff** | Production deploy; documentation; 60-min training session; Continuity Plan | Accept deliverables; plan for ongoing content management |

### Payment Gates

| Gate | Trigger | Amount |
|------|---------|--------|
| **Deposit** | Contract signed | 50% of project total |
| **Milestone 1** | End of Week 4: Assessment + Profile + Roadmap on staging, client-reviewed | 25% of project total |
| **Final** | End of Week 8: Production launch + handoff complete | 25% of project total |

---

## Appendix A: Culturally Affirming Design Principles

These principles should guide every design and content decision. Derived from Nikole Collins-Puri's discovery recordings.

1. **Identity as strength.** The platform consistently communicates: "You belong in these spaces. Your background and experiences are assets, not barriers."

2. **Context, not just information.** Don't just say "apply to this program." Acknowledge: "Many students entering competitive STEM programs feel pressure to prove they belong. Here are strategies other scholars have used to find mentors, build community, and advocate for themselves."

3. **Representation in everything.** Stories, examples, and role models reflect innovators of color. Entrepreneurship examples emphasize community impact, not just the Silicon Valley tech-startup narrative.

4. **Scholar as driver, not passenger.** The platform helps scholars think through choices — it doesn't tell them what to do. Pressure-test prompts ("Is this what you really want, or what you think you have to do?") build agency and critical thinking.

5. **Simplify, don't overwhelm.** Prioritize "what matters most right now" over presenting everything at once. The tone is encouraging and coaching-oriented. Reminders are helpful nudges, not stress-inducing alerts.

6. **Never generic.** If content could apply to any student at any school, it's not specific enough. The platform should feel informed by the real decision points students face when navigating selective institutions and innovation ecosystems.

---

## Appendix B: Pilot Plan

### Pilot Cohort
- **Size:** 10-20 scholars from the existing Empowerment Program
- **Selection criteria:** Mix of grade levels (9th-12th), geographies, and engagement levels; include at least 2-3 scholars Nikole considers "power users" who will give direct feedback
- **Duration:** 2 weeks (Week 6-7 of the build)

### Pilot Success Criteria
| Metric | Target |
|--------|--------|
| Assessment completion rate | >80% of pilot scholars complete the full assessment |
| "Feels like me" rate | >70% of scholars say their profile accurately reflects them |
| Roadmap usefulness | >70% of scholars rate their roadmap as "helpful" or "very helpful" |
| Return visits | >50% of scholars return to the platform within 7 days of first use |
| Qualitative | At least 3 scholars provide unprompted positive feedback or share with a peer |

### Feedback Collection
- In-app feedback button on every screen ("Does this feel right?")
- 5-minute post-pilot survey (confidence, clarity, belonging, usefulness)
- Optional: 15-minute Zoom interviews with 5 scholars

---

*Document ends.*

---

*TRUE STEELE LABS — Ship production software for mission-driven organizations.*
