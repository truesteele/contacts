# True Steele Labs: AI-Augmented Build Methodology
## Baseline Assumptions for Scoping & Pricing

**Date:** March 2026
**Author:** Justin Steele
**Version:** 1.0

---

## 1. How I Build

I build production software using Claude Code (Anthropic's CLI tool) as my primary development environment. I describe what I want in plain language from my terminal, and Claude builds across my entire codebase — writing code, running tests, deploying, and iterating in real time.

This is not "AI-assisted" development where a copilot suggests autocomplete. This is AI-native development where Claude Code writes 90%+ of the code, and my job is to direct it with product judgment, domain expertise, and architectural decisions.

**My stack:**
- **Frontend:** Next.js + React + Tailwind CSS
- **Backend/Database:** Supabase (PostgreSQL + Auth + Storage + Edge Functions)
- **AI:** Claude API (Anthropic) and OpenAI API
- **Hosting:** Vercel
- **Development tool:** Claude Code (Anthropic CLI)

**What I bring that the AI doesn't:**
- Product judgment — knowing what to build, for whom, and why
- Domain expertise — understanding nonprofit operations, funder psychology, program design
- Architectural decisions — choosing the right patterns, data models, and integration approaches
- Quality bar — knowing when AI output is good enough vs. needs refinement
- User empathy — designing for real humans, not theoretical personas

---

## 2. Build Speed Evidence

### My Own Track Record

| Project | What I Built | Time | Notes |
|---------|-------------|------|-------|
| Outdoorithm weather widget | Weather forecasts for 10,000+ campgrounds, elevation-specific | 4 hours | Dec 2024. First real AI build. Published article about it. |
| Kindora funder matching | AI system that evaluates funder alignment like a program officer | 1 night | Feb 2025. Found George Family Foundation match I'd missed for years. |
| Kindora production platform | Full SaaS — funder matching, grant intelligence, analytics, email automation | ~$60K total over 6 months | Apr-Dec 2025. Included paid developer at $6.5K/mo for first 6 months; ended contract when Claude Code closed the gap. |
| Weekend feature sprint | Analytics dashboard + email automation + feedback system + support ticketing | 1 weekend | Aug 2025. First weekend with Claude Code. Work that would have taken our developer multiple weeks. |
| Voice AI assistant | Funder conversation simulator for nonprofit pitch practice | 1 night, 4 prompts | Feb 2026. Working prototype. |
| Contacts platform | Network intelligence system — 2,940 contacts, enrichment pipelines, AI scoring, communication history, campaign tools | Ongoing since Dec 2024 | Production system serving daily. Multiple AI-powered pipelines. |
| Daily meeting prep system | Automated calendar scan → attendee research → AI memo generation → Google Doc creation | 3 days | Mar 2026. Supabase Edge Function + 5 Google accounts + Claude API + Perplexity. |

### Industry Benchmarks (2025-2026)

**Speed:**
- **Thoughtbot** built a production Rails app with Claude Code in a **2-week sprint** with full test suite and clean commits (2025)
- **Composio** built a full-stack finance app in **2-3 days**; individual features shipped in **30-60 minutes** vs. 8-10 hours manually (2025)
- **Consuly** MVP built in **under a month** with Claude + Cursor — a task that would normally take up to a year (Apr 2025)
- A single 10-hour Claude Code session produced **~5,000 lines of working code** with a prototype in 30 minutes

**Scale:**
- **Base44:** Solo founder hit 300K users and $3.5M ARR in 6 months, sold to Wix for $80M (Jun 2025)
- **YC W25 batch:** ~25% had codebases that were 95% AI-generated. All founders were "highly technical, completely capable of building from scratch" — they chose AI because it was faster and better.
- **YC S25 batch:** Over 50% of slots went to AI-first companies

**Anthropic's own data:**
- Internal survey (Aug 2025): Engineers self-report using Claude in **60% of their work**, with ~50% productivity boost
- **67% increase in merged PRs per engineer per day** after adopting Claude Code
- Boris Cherny (Claude Code creator, Jan 2026): "100% of my code is now written by Claude Code. I haven't written any code in two+ months."
- Company-wide, AI writes **70-90% of Anthropic's code**
- Claude Code accounts for **4% of all public GitHub commits** (~135K commits/day) as of Feb 2026

**Academic/controlled studies:**
- Controlled experiments: **30-55% faster** task completion for scoped coding tasks
- Developers using AI tools touched **~47% more PRs per day**
- Onboarding time cut in half (time to 10th PR) from Q1 2024 through Q4 2025
- **Important caveat (METR study, Jul 2025):** Experienced developers working on *their own mature codebases* saw **no speedup or slight slowdown**. AI gains are largest for **greenfield projects** and **unfamiliar codebases** — which is exactly what client work is.

---

## 3. What's Fast and What's Not

### Dramatically Faster with AI (5-10x)

| Activity | Traditional | With Claude Code | Why |
|----------|------------|-----------------|-----|
| Scaffolding a new project | 1-2 days | 15-30 minutes | Next.js + Supabase + Vercel setup is a solved pattern |
| Building CRUD interfaces | 2-4 days per entity | 2-4 hours per entity | Admin dashboards, list/detail views, forms |
| Auth + user management | 3-5 days | 2-4 hours | Supabase auth handles most complexity |
| API integrations | 1-3 days per integration | 1-4 hours per integration | Claude reads API docs and writes integration code |
| Database schema + migrations | 1-2 days | 30-60 minutes | Schema design still needs judgment; implementation is instant |
| UI component development | 1-2 days per complex component | 1-3 hours per component | Tailwind + React components are Claude Code's sweet spot |
| Writing tests | 1:1 with development time | Minutes per feature | Claude generates comprehensive test suites from working code |
| Bug fixes | Varies | Minutes to 1 hour | Claude can read the full codebase and trace issues |
| Documentation | Days | 30-60 minutes | Generated from code with human review |

### Moderately Faster (2-3x)

| Activity | Traditional | With Claude Code | Why |
|----------|------------|-----------------|-----|
| AI prompt engineering | N/A | 4-8 hours per major prompt | Iterative by nature; each cycle is fast but you need multiple cycles |
| Complex business logic | 2-5 days | 1-2 days | Needs human judgment on edge cases and rules |
| Data modeling | 1-3 days | 0.5-1 day | Schema design is fast; getting it *right* requires thinking |
| Performance optimization | Days | Hours | Claude identifies bottlenecks but human judgment picks the fix |

### Same Speed (Human-Bottlenecked)

| Activity | Why AI Doesn't Help |
|----------|-------------------|
| Product strategy & scoping | Deciding *what* to build requires domain expertise and client understanding |
| Design decisions & UX iteration | Visual design judgment, user empathy, brand alignment |
| Client feedback loops | Humans review at human speed. Waiting for sign-off is waiting. |
| Content creation | Assessment scenarios, culturally specific copy, curated opportunity listings — requires domain knowledge |
| AI output quality review | Reviewing LLM-generated content for tone, accuracy, and cultural sensitivity can't be automated |
| Pilot/user testing | Real users, real time, real feedback |
| Stakeholder alignment | Meetings, presentations, consensus-building |

### The Critical Insight

> **Calendar time is driven by human feedback loops, not code production.** A 4-week project isn't 4 weeks of coding — it's 2 weeks of coding interleaved with 2 weeks of client reviews, content dependencies, design iteration, and pilot feedback.

---

## 4. Estimation Framework

### Step 1: Estimate Actual Build Hours

Use these multipliers against traditional estimates:

| Feature Type | Traditional Hours | Claude Code Multiplier | Realistic Hours |
|-------------|------------------|----------------------|----------------|
| Standard web features (CRUD, forms, dashboards, auth) | X | **÷ 5-8** | X/5 to X/8 |
| AI-powered features (LLM integration, prompt engineering) | X | **÷ 2-3** | X/2 to X/3 |
| Design & UX | X | **÷ 1.5-2** | X/1.5 to X/2 |
| Content-dependent features | X | **÷ 1** (no compression) | X |
| Complex integrations (3rd party APIs, data pipelines) | X | **÷ 3-5** | X/3 to X/5 |
| Testing & QA | X | **÷ 2-3** | X/2 to X/3 |

### Step 2: Estimate Calendar Time

```
Calendar weeks = max(
  Build weeks (actual hours ÷ 30 hrs/week on this project),
  Client feedback cycles (# of review gates × 3-5 days each),
  Content dependency timeline (when does client deliver assets?)
)
```

**Typical calendar time by project type:**

| Project Type | Actual Build Hours | Calendar Time | Why the Gap |
|-------------|-------------------|---------------|-------------|
| Discovery Sprint + Prototype | 30-40h | 1-2 weeks | 1 design review cycle |
| Production MVP | 80-120h | 4-5 weeks | 2-3 review cycles + pilot week |
| Adoption-Ready Product | 140-200h | 6-8 weeks | 3-4 review cycles + extended pilot |
| Complex Platform | 250-400h | 10-14 weeks | Multiple stakeholders, content heavy |

### Step 3: Price on Value, Not Hours

**The principle:** I sell deliverables, not time. Getting faster with AI means higher effective rates, not lower prices. The value to the client is the same whether it takes me 100 hours or 500 hours — they get a production application.

**Pricing formula:**
```
Price = Market rate for comparable deliverable × 0.35-0.50 discount
```

I consistently deliver at **50-65% below market rates** because:
- AI-augmented development compresses actual build time 3-5x
- Solo builder = no overhead, no layers, no project management tax
- Reusable patterns and components from prior projects compound

**But I don't race to the bottom.** The discount is a competitive advantage, not a charity. The effective hourly rate should land at **$300-600/hr** — which is premium consulting territory, justified by:
- Deep domain expertise (10 years directing $698M in philanthropy)
- Production-grade output (not prototypes)
- Speed of delivery (weeks, not months)
- Direct access to the builder (no layers)

### Step 4: Sanity Checks

Before finalizing any project price:

| Check | How | Red Flag |
|-------|-----|----------|
| **Effective rate** | Price ÷ estimated actual hours | Below $250/hr = underpriced. Above $700/hr = might be hard to defend. |
| **Market comparison** | What would a traditional shop charge? | If I'm above 50% of market rate, justify with speed + domain expertise. |
| **Client budget** | Can they actually pay this? | If not, scope down to a tier they can fund. Don't discount — descope. |
| **Opportunity cost** | What else could I build with those hours? | If Kindora or Outdoorithm would benefit more, pass. |
| **Per-screen heuristic** | $1,500-3,000 per unique screen | If the math doesn't roughly work, recheck scope. |

---

## 5. Tier Reference (Updated March 2026)

| Tier | Deliverable | Actual Build Hours | Calendar Time | Price Range |
|------|------------|-------------------|---------------|-------------|
| **Discovery Sprint** | PRD + clickable prototype + technical architecture | 30-40h | 1-2 weeks | $12,000-18,000 |
| **Production MVP** | Deployed app with core features, tested with real users | 80-120h | 4-5 weeks | $35,000-50,000 |
| **Adoption-Ready** | Production app + integrations + admin tools + expanded features | 140-200h | 6-8 weeks | $55,000-85,000 |
| **Platform** | Multi-tenant, multi-role, complex business logic, scale | 250-400h | 10-14 weeks | $100,000-175,000 |
| **True Steele Care** | Ongoing support, bug fixes, minor enhancements | 5h/month max | Monthly | $3,500-5,500/mo |

---

## 6. What This Means for Clients

**The pitch:**

> What traditional development shops deliver in 4-6 months for $150K+, I ship in 4-5 weeks for a fraction of the cost. Not because I cut corners — because I build with AI the way Anthropic's own engineers build. I direct Claude Code with a decade of product judgment and deep domain expertise. The code is production-grade. The IP is yours. And you work directly with me — no account managers, no layers, no handoffs.

**The proof:**
- Kindora: concept to production, ~$60K total
- Flourish Fund ATS: production system managing real grant applications
- Outdoorithm: AI-powered platform serving hundreds of users
- Four products shipped in the past year, all in active production

**The honest caveat:**

Speed doesn't eliminate all risk. The parts that still take time — getting the product right, testing with real users, iterating on feedback — are the parts that matter most. I build fast so we can spend more time on what actually determines success: whether the people who use this product find it valuable.

---

## 7. Sources

### Personal
- "Something Bigger Is Happening" — LinkedIn article, Feb 2026
- "Yosemite's Weather Apps Failed Us" — LinkedIn article, Dec 2024
- True Steele Labs Strategy Document, Jan 2026

### Industry
- Thoughtbot: "Claude Code Skills: Production-Ready Code in a Two-Week Sprint" (2025)
- Composio: "Full-Stack Claude Code Setup" (2025)
- TechCrunch: "A quarter of startups in YC's current cohort have codebases almost entirely AI-generated" (Mar 2025)
- Fortune: "100% of code at Anthropic is now AI-written" — Boris Cherny interview (Jan 2026)
- Anthropic Research: "How AI Is Transforming Work at Anthropic" (Aug 2025)
- SemiAnalysis: "Claude Code Is the Inflection Point" (Feb 2026)
- METR: "Early 2025 AI Experienced OS Dev Study" (Jul 2025)
- Bain & Company: AI coding productivity analysis (Sep 2025)
- Index.dev: "Developer Productivity Statistics with AI Tools" (2025-2026)
- Digital Applied: "AI Micro-Consulting Premium Rates Solo Guide" (2025)

---

*TRUE STEELE LABS — Ship production software for mission-driven organizations.*
