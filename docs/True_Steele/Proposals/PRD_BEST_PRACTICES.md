# PRD Best Practices for True Steele Labs
## How to Scope, Spec, and Price Client Projects

**Date:** March 2026
**Purpose:** Repeatable framework for turning client discovery into a PRD that drives accurate fixed-fee pricing.

---

## 1. Philosophy

**The PRD is not the proposal.** These are distinct documents with distinct purposes:

| Document | Purpose | Audience | Length |
|----------|---------|----------|--------|
| **PRD** | Define what we're building and why | Product + Engineering + Client (technical stakeholders) | 5-15 pages |
| **Proposal** | Confirm the engagement and investment | Client decision-maker | 2-3 pages |
| **SOW/Contract** | Legal terms, milestones, payment gates | Client + Legal | 3-5 pages |
| **Technical Spec** | Architecture, data models, implementation plan | Engineering (internal) | As needed |

The PRD feeds the proposal, not the other way around. Do discovery first, write the PRD, then distill the proposal from it.

**The PRD should read like a confident plan, not a cautious disclaimer.** It demonstrates deep understanding of the client's problem, proposes a clear path, makes trade-offs explicit, and gives everyone enough context to do their best work.

---

## 2. PRD Structure

Use this structure for every client project. Sections scale up or down based on project size.

### Section 1: Problem & Context (1-2 pages)
- **Client situation** — Who they are, what they do, where they are today
- **The problem** — Grounded in specific evidence from discovery (use their words)
- **Why now** — What's changed that makes this urgent
- **Current state** — Existing tools, workflows, pain points, workarounds
- **Competitive/market context** — What alternatives exist and why they fall short

> **Rule:** This section should make the client feel deeply understood. If they can't point to a sentence and say "that's exactly right," rewrite it.

### Section 2: Product Vision & Success Metrics (0.5-1 page)
- **North star statement** — One sentence: what does this product do for whom?
- **Success metrics** — 3-5 measurable signals that prove it's working
  - At least one adoption metric (users, usage frequency)
  - At least one outcome metric (what changes for users)
  - At least one business metric (what changes for the client org)
- **Non-goals** — What this product explicitly does NOT do

> **Format success metrics as testable hypotheses:** "We believe [building X] will result in [Y outcome] as measured by [Z metric]."

### Section 3: Users & Journeys (1-2 pages)
- **User roles** — Table of who uses the product and what they need
- **Primary user journey** — Step-by-step flow for the core use case
- **Secondary journeys** — Other key flows (admin, onboarding, edge cases)
- **As-is vs. to-be** — How things work today vs. how they'll work with the product

> **Use story mapping format where possible.** A horizontal backbone of user steps with features hanging vertically beneath each step. The top horizontal slice = MVP.

### Section 4: Feature Requirements (2-5 pages)
This is the core. Organize by epic, with features decomposed into estimable units.

**For each epic:**

```
### Epic: [Name]
**Why:** [Business/user justification]
**Priority:** Must / Should / Could / Won't (MoSCoW)

| Feature | Description | Acceptance Criteria | Size |
|---------|-------------|-------------------|------|
| Feature 1 | What it does | Given/When/Then | S/M/L/XL |
| Feature 2 | What it does | Given/When/Then | S/M/L/XL |
```

**T-shirt sizing guide (for estimation):**

| Size | Effort | Typical Examples |
|------|--------|-----------------|
| **XS** | < 4 hours | Config change, copy update, simple UI tweak |
| **S** | 4-8 hours (0.5-1 day) | Single form, basic CRUD, simple API endpoint |
| **M** | 8-24 hours (1-3 days) | Multi-step flow, integration with external API, complex component |
| **L** | 24-40 hours (3-5 days) | Full feature with multiple screens, auth flow, complex business logic |
| **XL** | 40-80 hours (1-2 weeks) | Major system component — needs decomposition into smaller items |

> **Rule:** Anything sized XL should be broken into smaller pieces. If it can't be broken down, the requirement isn't well enough understood.

### Section 5: Non-Functional Requirements (0.5-1 page)
These are the requirements that aren't features but drive architecture and cost:

- **Performance** — Page load targets, API response times
- **Security** — Auth model, encryption, PII handling, compliance requirements
- **Accessibility** — WCAG level, screen reader support
- **Device/browser support** — Mobile-first? Which browsers? Native vs. web?
- **Scalability** — Expected user count at launch vs. 12 months
- **Reliability** — Uptime expectations, backup/recovery
- **Internationalization** — Languages, locales, RTL support

> **These are often the hidden cost drivers.** COPPA compliance for minors, multilingual support, or 99.9% uptime can each add 20-40% to a project. Surface them early.

### Section 6: Technical Approach (0.5-1 page)
Client-facing — describe the "what" and "why," not the "how":

- **Stack selection** with brief rationale
- **Hosting/infrastructure** approach
- **Integration points** — what external systems connect
- **Data handling** — storage, backups, retention
- **AI/ML approach** (if applicable) — models, training data, guardrails

> **Keep implementation details out.** Database schemas, API specs, and code architecture go in the Technical Spec, not the PRD.

### Section 7: Content & Asset Requirements (0.5-1 page)
**This section is critical for True Steele Labs projects.** Many clients assume content creation is included in the build. Make explicit:

- **What content the client provides** (copy, images, brand assets, data)
- **What content we create** (UI copy, system messages, sample data)
- **What content is out of scope** (marketing copy, training materials, curriculum)
- **Content deadlines** — When assets must be delivered to avoid timeline delays

> **Rule:** If the client doesn't have content ready, the timeline slips. Bake this into the schedule with explicit deadlines and consequences.

### Section 8: Assumptions & Risks (0.5-1 page)

**Assumptions** — Testable statements:
> "We assume [X]. If this is wrong, [Y is the impact on scope/timeline/cost]."

**Dependencies** — Things outside our control:
> "This project depends on [X]. If delayed, the timeline shifts by [Y]."

**Risks** — Categorized by type:
| Risk | Type | Likelihood | Impact | Mitigation |
|------|------|-----------|--------|------------|
| Users don't adopt | Value | Medium | High | Early pilot with real users |
| AI produces generic output | Feasibility | Medium | High | Curated training data, human review |
| Client content delayed | Dependency | High | Medium | Placeholder content, deadline clauses |

**Open Questions** — With owners and due dates:
| Question | Owner | Due | Impact if Unresolved |
|----------|-------|-----|---------------------|
| Who provides opportunity data? | Client | Week 1 | Blocks feature X |

### Section 9: Phasing & Roadmap (1-2 pages)
Break the product into releases with clear scope boundaries:

```
## Phase 1: MVP (Weeks 1-6)
Must-have features only. Goal: [specific outcome]
[Feature table with sizes]

## Phase 2: Enhancement (Weeks 7-10)
Should-have features. Goal: [specific outcome]
[Feature table with sizes]

## Phase 3: Scale (Future)
Could-have features. Goal: [specific outcome]
[Feature list — no sizing needed]
```

> **The phase boundary is the scope boundary.** Phase 1 has a fixed price. Phase 2 is a separate engagement. This prevents scope creep structurally.

### Section 10: Timeline & Milestones (0.5 page)
Week-by-week with payment gates:

| Week | Milestone | Deliverable | Payment Gate |
|------|-----------|-------------|-------------|
| 0 | Kickoff | Project plan, dev environment | 50% deposit |
| 1-2 | Design & Architecture | Wireframes, data model, tech spec | — |
| 3-4 | Core Build Sprint 1 | [Specific features] deployed to staging | — |
| 5-6 | Core Build Sprint 2 | [Specific features] deployed to staging | 25% milestone |
| 7 | Testing & Polish | QA, bug fixes, client review | — |
| 8 | Launch | Production deploy, handoff, training | 25% final |

---

## 3. Pricing from the PRD

### The Estimation Pipeline

```
PRD Features → T-Shirt Sizes → Hour Ranges → Subtotals → Contingency → Price
```

**Step 1: Size every feature** using the T-shirt guide above.

**Step 2: Convert to hours** using the midpoint of each range:
- XS = 3h, S = 6h, M = 16h, L = 32h, XL = 60h

**Step 3: Sum by category:**
| Category | Hours |
|----------|-------|
| Frontend (UI, components, pages) | X |
| Backend (API, business logic, data) | X |
| Integrations (external APIs, auth) | X |
| AI/ML (model integration, prompts, guardrails) | X |
| Design (wireframes, UI design, iteration) | X |
| DevOps (hosting, CI/CD, monitoring) | X |
| QA & Testing | X |
| **Subtotal** | **X** |

**Step 4: Add contingency (20-30%)**
- 20% for well-understood projects with clear requirements
- 30% for projects with significant unknowns, AI components, or content dependencies

**Step 5: Apply rate and round to tier pricing**

> **Rule:** The estimate drives the tier selection, not the other way around. If the estimate lands at $52K, that's a Tier 2 ($40-65K). Don't stretch scope to fill a tier or cut corners to fit one.

### Pricing Sanity Checks

Before finalizing, validate against:

1. **Per-screen heuristic** — $2,000-$5,000 per unique screen/page for a production app. Count the screens in your PRD. If you have 15 screens and your price is $30K, something is too low.
2. **Comparable projects** — What did similar builds cost? (Kindora ~$60K total, Flourish Fund ATS, etc.)
3. **Client's budget signal** — Does the price match what the client indicated they could spend?
4. **Hourly rate backcast** — Total price / total estimated hours = effective rate. Should be $150-250/hr for True Steele Labs. Below $150 means underpriced. Above $250 means the estimate might be padded.

---

## 4. MVP Scoping Framework

### MoSCoW + Impact/Effort (Combined Approach)

**Step 1: MoSCoW categorization** — For each feature, assign:
- **Must** — Product cannot launch without this. Users literally cannot complete the core task.
- **Should** — Important for a good experience. Missing it would hurt but not block launch.
- **Could** — Nice to have. Include if time/budget permits.
- **Won't (this time)** — Explicitly deferred. Documented for future phases.

**Step 2: Validate the "Must" list** by asking:
1. Can a user complete the primary job-to-be-done without this feature?
2. If we launched without this, would users still get value?
3. Is this a feature or a polish item disguised as a feature?

**Step 3: For "Should" items**, use Impact/Effort to decide what might graduate to "Must":
- High impact + Low effort → Move to Must
- High impact + High effort → Keep as Should (Phase 2)
- Low impact + Low effort → Could (include if easy)
- Low impact + High effort → Cut

> **The MVP should be uncomfortably small.** If the client isn't slightly nervous about what's missing, the scope isn't tight enough. A tight MVP that ships and gets user feedback beats a comprehensive product that takes twice as long.

### The "One Core Loop" Test

Every product has one core loop — the primary action a user takes repeatedly. For a good MVP:

1. **Identify the core loop** — e.g., "Scholar completes assessment → gets personalized roadmap → tracks milestones"
2. **Strip everything that isn't the core loop** — Social features, gamification, admin dashboards, integrations — all Phase 2
3. **Make the core loop excellent** — Invest the saved effort in making the primary experience genuinely good

---

## 5. Acceptance Criteria Standards

### Use Given/When/Then for Every Feature

```
Feature: Scholar completes onboarding assessment

Given a new scholar who has been accepted into the program
When they log in for the first time
Then they are presented with the assessment flow (not the dashboard)

Given a scholar is mid-assessment
When they close the app and return later
Then they resume from where they left off

Given a scholar has completed all assessment sections
When they submit their final answers
Then the system generates a personalized roadmap within 30 seconds
And the scholar sees a summary of their profile and top 3 recommended pathways
```

### Deliverable Acceptance Criteria (for SOW/Contract)

Be surgical about what "done" means:

- **"Deployed to production"** — Not "code complete." It's live and accessible.
- **"Client-reviewed and accepted"** — Client has 5 business days to review. Silence = acceptance.
- **Revision limits** — "Includes up to 2 rounds of revision per deliverable. Additional rounds billed at $X/hour."
- **Content dependency** — "Deliverable completion assumes client-provided content by [date]. Delays shift timeline 1:1."
- **Bug vs. enhancement** — "A bug is behavior that deviates from the acceptance criteria in this PRD. A new request or changed requirement is an enhancement and requires a change order."

---

## 6. Change Control

Every PRD/SOW should include:

> **Change Request Process:** Any work not described in this PRD requires a written Change Request. Each CR will include: description of the change, impact on timeline, impact on cost, and approval signature. No out-of-scope work begins without a signed CR. Minor scope adjustments (< 4 hours) may be absorbed at True Steele Labs' discretion within the existing contingency. Adjustments exceeding 4 hours require a formal CR.

---

## 7. Common Pitfalls

### PRD Anti-Patterns to Avoid

| Anti-Pattern | What It Looks Like | Fix |
|--------------|-------------------|-----|
| **The Dissertation** | 30-page spec nobody reads | Keep to 5-15 pages. Link to appendices for detail. |
| **Solution-First** | "We need a dashboard" before defining the problem | Always start with the user problem |
| **Vague Acceptance** | "System should be user-friendly" | Quantify: "First-time users complete onboarding in < 5 minutes" |
| **Missing Exclusions** | No out-of-scope section | Client will assume everything is included |
| **Content Handwave** | "Client provides content" with no deadlines | Specify what, when, and consequences of delay |
| **NFR Blindness** | No performance, security, or accessibility requirements | These drive architecture. Surface them early or pay later. |
| **Phase Bleed** | Phase 1 keeps growing as "just one more thing" | Phase boundary = scope boundary. New items go to Phase 2. |
| **Estimate Without Decomposition** | "The whole thing is about $60K" | Break into epics → features → sizes. Sum bottom-up. |

### True Steele Labs-Specific Pitfalls

1. **Underestimating AI integration effort.** Prompt engineering, guardrails, testing for edge cases, and ongoing tuning are real work. Add 30% contingency on any AI-powered feature.
2. **Assuming content exists.** Most nonprofit clients don't have content ready for a digital product. Either scope content creation separately or build with placeholder content and a handoff plan.
3. **Confusing a product vision with a v1.** Clients describe their ultimate vision. Your job is to scope the smallest version that proves the core hypothesis. The PRD should document the full vision but clearly delineate what's Phase 1 vs. later.
4. **Skipping the pilot plan.** For nonprofit products, who uses it first and how you learn from them matters as much as what you build. Include a pilot/launch plan in the PRD.

---

## 8. Document Lifecycle

### The Evolving PRD (Reforge Model)

PRDs should mature through stages, not be written all at once:

| Stage | Document | When | Purpose |
|-------|----------|------|---------|
| **Discovery** | Product Brief (1 page) | After first call | Capture problem, users, and hypothesis |
| **Deep Discovery** | Draft PRD (5-8 pages) | After voice recordings / workshops | Features, sizing, phasing — enough to price |
| **Proposal Accepted** | Final PRD (8-15 pages) | After client signs | Full spec with acceptance criteria, architecture |
| **During Build** | Living PRD | Ongoing | Updated as decisions are made, tracked via changelog |

> **Key insight:** "Worry about your PRD being enough to get started, not about it being finished or perfect." The PRD is a living document, not a contract carved in stone.

### Changelog

Every PRD update should be tracked:

```
## Changelog
| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-03-10 | 1.0 | Initial draft from discovery | JS |
| 2026-03-15 | 1.1 | Updated Phase 1 scope per client review | JS |
| 2026-03-20 | 2.0 | Final PRD — proposal accepted | JS |
```

---

## 9. Templates & References

### PRD Template (Quick Start)
Copy the Section 2 structure above. Fill in for each project. Delete sections that don't apply.

### Estimation Worksheet
For each project, create a table:

```
| Epic | Feature | Priority | Size | Hours (mid) | Category |
|------|---------|----------|------|-------------|----------|
| Onboarding | Assessment flow | Must | L | 32 | Frontend + Backend |
| Onboarding | Profile generation | Must | M | 16 | Backend + AI |
| Roadmap | Milestone tracker | Must | M | 16 | Frontend + Backend |
| ... | ... | ... | ... | ... | ... |
| | | | **Subtotal** | **X** | |
| | | | **Contingency (25%)** | **X** | |
| | | | **Total** | **X** | |
```

### Proposal (Distilled from PRD)
Per the Proposal Best Practices doc — keep to 2-3 pages:
1. Problem recap (from PRD Section 1)
2. What we'll build (from PRD Sections 4 + 9, summarized)
3. Timeline & milestones (from PRD Section 10)
4. Investment (from pricing calculation)
5. What's not included (from PRD exclusions + Phase 2+)
6. Next steps

---

## 10. Sources

**Agency Practices:**
- Thoughtbot: 5-day Product Design Sprint → validated prototype → firm estimate
- Pivotal Labs: Discovery & Framing workshops → story map → balanced team execution
- DECODE Agency: 5-phase MVP scoping (alignment → risks → design → prioritize → architecture)
- ABZ Agency: Discovery phase → PRD with wireframes for public, personal, admin, notifications, and infrastructure layers

**Frameworks:**
- MoSCoW prioritization (ProductPlan)
- RICE scoring (Intercom / Plane.so)
- Story mapping (Jeff Patton)
- Evolving PRD model (Reforge)
- Marty Cagan's 4 risk categories (value, usability, feasibility, viability)

**Estimation:**
- T-shirt sizing (Easy Agile)
- Bottom-up story-level estimation (Toptal)
- Milestone-based payment structures (DealHub, Cobrief)

**Consulting-Specific:**
- Consulting Success — proposal templates, pricing psychology
- WhiteLabelIQ — SOW best practices, revision limits
- GlobalDev — fixed-price vs. T&M vs. milestone pricing models

---

*TRUE STEELE LABS — Ship production software for mission-driven organizations.*
