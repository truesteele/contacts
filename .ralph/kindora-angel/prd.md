# Project: Kindora Angel Investment — Ask-Readiness Scoring Pipeline

## Overview

Build an angel investor prospect scoring pipeline for Kindora's $200K-$400K mission-aligned angel raise. Score all ~2,900 contacts using GPT-5 mini with an investor psychology prompt (different from the existing donor psychology prompt used for Outdoorithm fundraising). Create API route and UI page for browsing/filtering results. Deploy.

## Technical Context

- **Tech Stack:** Python 3.12, OpenAI API (GPT-5 mini), Next.js 14 (App Router), Supabase, Tailwind CSS, shadcn/ui
- **Python venv:** `.venv/` (arm64) — activate with `source .venv/bin/activate`
- **Existing patterns:** `scripts/intelligence/score_ask_readiness.py` is THE model — this script already supports parameterized goals via `--goal`. The `ask_readiness` JSONB column stores results keyed by goal name. We are ADDING a new goal, not creating a new script.
- **Existing UI pattern:** `job-matcher-ai/app/tools/ask-readiness/page.tsx` is the model for the new UI page
- **Existing API pattern:** `job-matcher-ai/app/api/network-intel/ask-readiness/route.ts` is the model for the new API route
- **Env vars:** `OPENAI_APIKEY` (no underscore before KEY), `SUPABASE_URL`, `SUPABASE_KEY`
- **GPT-5 mini:** Does NOT support temperature=0. Use default only.
- **OpenAI structured output:** `openai.responses.parse(model="gpt-5-mini", instructions=SYSTEM_PROMPT, input=context, text_format=PydanticModel)`
- **Workers:** 150 for GPT-5 mini
- **Vercel deployment:** Account `justin-outdoorithm`, team `true-steele`, project `contacts`. Deploy from `job-matcher-ai/` dir: `npx vercel --prod --yes --scope true-steele`

## Key Reference Files (READ THESE)

- `scripts/intelligence/score_ask_readiness.py` — The scoring script (add new goal + prompt here)
- `job-matcher-ai/app/tools/ask-readiness/page.tsx` — UI page to copy from
- `job-matcher-ai/app/api/network-intel/ask-readiness/route.ts` — API route to copy from
- `job-matcher-ai/app/page.tsx` — Homepage (add link here)
- `docs/Kindora/strategy/Kindora Strategy.md` — Kindora's capital strategy (context for the prompt)

## Kindora Context (For the GPT Prompt)

Kindora is a Delaware Public Benefit Corporation building AI-powered fundraising tools for the 85% of nonprofits priced out of professional platforms. Co-founded by Justin Steele (CEO, ex-Google.org director who deployed $700M, SF Foundation trustee, Harvard MBA/MPA) and Karibu Nyaggah (President/CPO, Meta operations director, Harvard MBA). 213 registered orgs, ~10 paying, $25-199/mo SaaS pricing, 75% gross margins.

Raising $200K-$400K via mission-aligned angel checks ($10K-$50K each). Instrument: convertible notes or SAFEs with founder-friendly terms, no board seats. NOT raising VC. Looking for people who believe in the mission and want to support early growth. Return profile: modest and long-dated (not 10x VC bet). PBC structure legally protects mission.

## Angel Investor Scoring Framework (Five Dimensions)

### 1. Financial Capacity for Angel Investing
Accredited investor signals: $200K+ income or $1M+ net worth (excl. primary residence).
- VP+ at tech companies ($300K-$1M+ total comp) = likely accredited
- Partner at consulting/law firms = accredited
- Founders with any exit = almost certainly accredited
- Finance/investment professionals = understand the asset class
- FEC donations $5K+ = STRONGEST signal (proves discretionary cash AND values-driven check writing)
- Real estate $1.5M+ as owner = asset wealth signal (but may be illiquid)
- Foundation trustees = typically require give-or-get minimum, signals both wealth and values
- Nonprofit/government/education careers = salaried, no equity wealth. A 20-year nonprofit career at CEO level means $300-600K salary with NO stock options. Do NOT overweight titles in these sectors.
- A $25K angel check needs to feel non-material to their financial life. Target: people for whom $25K is well under 1% of net worth.

### 2. Mission Alignment with Kindora
- Philanthropic career or board service = values alignment
- Google.org / foundation alumni = understand the problem space intimately
- Nonprofit technology experience = understand the market
- Social impact / equity / AI-for-good interests (from LinkedIn content, ai_tags, volunteer orgs)
- Prior donations to education, equity, or technology causes
- NOT looking for pure financial return seekers — someone whose only interest is ROI is a bad fit for a PBC

### 3. Relationship Warmth (reuse existing 2x2 framework)
Same familiarity_rating + comms_closeness model from donor scoring. Angel investing requires even MORE trust than donations — you're asking someone to put capital at risk in an illiquid startup.
- Active Inner Circle (fam 3-4, active comms) = direct conversation
- Dormant Strong Ties (fam 3-4, dormant comms) = reactivate then discuss
- Active Weak Ties (fam 0-2, active comms) = deepen before asking
- Cold (fam 0-2, dormant/none) = only if very high capacity + warm intro path

### 4. Investment Sophistication
- Prior angel investing (self-identified on LinkedIn, "angel investor" in headline/about, AngelList profile) = strongest signal
- Startup board memberships = has crossed from observer to participant
- VC/PE/startup experience = understands risk/return and illiquidity
- People who have deployed philanthropic capital (grants) also understand mission-driven, illiquid capital deployment
- First-time angel investors need more education on mechanics (SAFEs, risk of total loss) — flag this in cultivation_needed

### 5. Strategic Value Beyond Capital
- Can they introduce Kindora to paying customers? (Foundation program officers, nonprofit network leaders)
- Do they bring fundraising credibility? (Recognized name on cap table compresses future diligence)
- Domain expertise in philanthropy, SaaS, or nonprofit technology?
- Can they amplify Kindora's story? (Media, LinkedIn following, conference speaking)
- Operational experience building startups?

### Disqualifying Signals (score as not_a_fit)
- Pure financial return seekers (only care about ROI, would push for mission-compromising exits)
- People who want governance control (board seat demands on small checks, veto rights)
- Conflicts of interest (work at/advise Kindora competitors)
- Insufficient financial capacity (below accredited threshold, a $25K check would cause financial stress)
- No relationship path (cold contact, no mutual connections, no way to warm the intro)

### Scoring Guidance
- 80-100 (ready_now): Accredited + mission-aligned + warm relationship + investment-sophisticated. Ready for a direct conversation.
- 60-79 (cultivate_first): Good profile but relationship needs warming, or needs investment education. 1-3 touchpoints before the ask.
- 40-59 (long_term): Has capacity or alignment but relationship too thin for a direct ask. Needs 4-8 cultivation touchpoints.
- 20-39 (long_term): Distant connection or weak alignment. Only if very high capacity + warm intro path.
- 0-19 (not_a_fit): No relationship, no alignment, no capacity, or actively disqualifying.

Most contacts will be not_a_fit or long_term. A 2,900-person network might yield 30-50 ready_now, 100-200 cultivate_first. This is expected.

---

## User Stories

### US-001: Add `kindora_angel_investment` Goal and Investor Psychology Prompt
**Priority:** 1
**Status:** [x] Complete

**Description:**
Add a new goal `kindora_angel_investment` to `score_ask_readiness.py` with an investor psychology system prompt. The script already supports multiple goals via the `--goal` flag and stores results in `ask_readiness` JSONB keyed by goal name — we're adding a new goal, not modifying the existing one.

**Acceptance Criteria:**
- [ ] Add `kindora_angel_investment` entry to `GOAL_CONTEXTS` dict (~line 75) with Kindora context
- [ ] Create a new system prompt `INVESTOR_SYSTEM_PROMPT` with the five-dimension angel investor psychology framework (see framework above). This must be comprehensive — at least as detailed as the existing `SYSTEM_PROMPT` for donor psychology. Include all five dimensions with specific signal guidance, scoring tiers, output requirements, and behavioral insights.
- [ ] Modify the scoring function to use `INVESTOR_SYSTEM_PROMPT` when `goal == "kindora_angel_investment"` and `SYSTEM_PROMPT` for all other goals
- [ ] The Pydantic schema `AskReadinessResult` stays the same — we reuse it with different semantic meaning:
  - `suggested_ask_range` → investment check size like "$25K-$50K" or "$10K-$25K"
  - `personalization_angle` → why Kindora's mission resonates for THIS person as an investor
  - `cultivation_needed` → steps to get from current state to investment conversation
  - `risk_factors` → things that could backfire (governance demands, return expectations, relationship damage)
  - `receiver_frame` → what kind of investment conversation they'd welcome, from their perspective
- [ ] Test: `source .venv/bin/activate && cd scripts/intelligence && python score_ask_readiness.py --goal kindora_angel_investment --test`
- [ ] Test output shows investor-psychology reasoning (mentions investment capacity, check size, SAFE/note terms) not donor-psychology reasoning (no mention of donation, gift, giving)

**Notes:**
- READ the full existing `SYSTEM_PROMPT` in score_ask_readiness.py — your new investor prompt should match its depth and specificity
- The investor prompt should reference the SAME data fields (FEC, real estate, comms, employment, familiarity) but interpret them through an investment lens
- GPT-5 mini does NOT support temperature=0. Use default only.
- Env var is `OPENAI_APIKEY` (no underscore before KEY)

---

### US-002: Create API Route for Kindora Angel Prospects
**Priority:** 2
**Status:** [ ] Incomplete

**Description:**
Create a new API route at `job-matcher-ai/app/api/network-intel/kindora-angel/route.ts` for fetching and updating Kindora angel prospect data. Copy from the existing ask-readiness route.

**Acceptance Criteria:**
- [ ] File created at `job-matcher-ai/app/api/network-intel/kindora-angel/route.ts`
- [ ] GET endpoint:
  - Default goal = `kindora_angel_investment`
  - Select columns: id, first_name, last_name, company, position, city, state, headline, familiarity_rating, comms_last_date, comms_thread_count, ai_capacity_tier, ai_capacity_score, ask_readiness, campaign_2026
  - Remove OC-specific fields: `ai_outdoorithm_fit`, `oc_engagement`
  - Filter: `ask_readiness` not null, goal data exists with numeric score
  - Map fields same as ask-readiness route but without oc_engagement and ai_outdoorithm_fit
  - Return: `{ contacts, total, goal, tier_counts }`
- [ ] PATCH endpoint:
  - Supports field = 'tier' (updates ask_readiness JSONB for kindora_angel_investment goal)
  - Supports field = 'campaign_list' (updates campaign_2026 JSONB)
  - Same validation logic as ask-readiness route
- [ ] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit` (or at minimum, no red squiggles in the new file)

**Notes:**
- Copy from `job-matcher-ai/app/api/network-intel/ask-readiness/route.ts` — it's the exact pattern
- Use `export const runtime = 'edge';`
- Import supabase from `@/lib/supabase`

---

### US-003: Create UI Page for Kindora Angel Prospects
**Priority:** 3
**Status:** [ ] Incomplete

**Description:**
Create a new UI page at `job-matcher-ai/app/tools/kindora-angel/page.tsx` for browsing and filtering Kindora angel investment prospects.

**Acceptance Criteria:**
- [ ] File created at `job-matcher-ai/app/tools/kindora-angel/page.tsx`
- [ ] Title: "Kindora Angel Prospects"
- [ ] Fetches from `/api/network-intel/kindora-angel`
- [ ] Tier summary cards: ready_now, cultivate_first, long_term, not_a_fit (clickable filter toggles)
- [ ] Search bar (search by name, company, reasoning)
- [ ] Filters: Capacity tier, Approach, Timing, Comms history
- [ ] Remove OC-specific filters: OC Fit filter
- [ ] Remove OC-specific columns/badges: OC engagement badges (OC Donor, OC Participant, OC Board)
- [ ] Table columns: #, Score, Tier (editable dropdown), List (editable dropdown), Name, Company, Familiarity, Last Contact, Capacity, Reasoning & Strategy
- [ ] Rename "Ask Range" → "Check Size" in expanded details
- [ ] Expandable row details: Approach, Timing, Check Size, Cultivation Needed, Personalization Angle, Risk Factors
- [ ] CSV export with investor-relevant headers
- [ ] Contact detail sheet integration (clicking name opens ContactDetailSheet)
- [ ] Sortable columns
- [ ] Icon: Use TrendingUp from lucide-react (import it)

**Notes:**
- Copy from `job-matcher-ai/app/tools/ask-readiness/page.tsx` — modify, don't write from scratch
- Use the same shadcn/ui components: Badge, Button, Card, ScrollArea, Select, ContactDetailSheet
- Keep the same TIER_CONFIG, APPROACH_LABELS, TIMING_LABELS, CAPACITY_COLORS
- The page should be functional as a standalone tool — all the interactive features from ask-readiness

---

### US-004: Add Homepage Link
**Priority:** 4
**Status:** [ ] Incomplete

**Description:**
Add a card for Kindora Angel Prospects to the homepage dashboard.

**Acceptance Criteria:**
- [ ] Read `job-matcher-ai/app/page.tsx` to understand the TOOLS array structure
- [ ] Add new entry to TOOLS array:
  - title: 'Kindora Angel Prospects'
  - description: 'Angel investor prospect scoring for Kindora\'s $200K-$400K raise. AI-scored across financial capacity, mission alignment, relationship warmth, and investment sophistication.'
  - href: '/tools/kindora-angel'
  - icon: TrendingUp (import from lucide-react)
  - accent: appropriate gradient colors (different from existing cards)
  - iconColor: appropriate color
- [ ] Import TrendingUp if not already imported

---

### US-005: Create Angel Investor Scoring Framework Doc
**Priority:** 5
**Status:** [ ] Incomplete

**Description:**
Create a reference document for the angel investor scoring framework at `docs/Kindora/ANGEL_INVESTOR_SCORING_FRAMEWORK.md`.

**Acceptance Criteria:**
- [ ] File created at `docs/Kindora/ANGEL_INVESTOR_SCORING_FRAMEWORK.md`
- [ ] Documents the five scoring dimensions with specific signal definitions
- [ ] Includes tier definitions and score ranges
- [ ] Includes disqualifying signals
- [ ] Includes guidance on interpreting results (what a "ready_now" angel prospect looks like)
- [ ] Includes the capital strategy context (what we're raising, instrument, terms)
- [ ] Includes data sources used (which database columns feed each dimension)
- [ ] Concise and actionable — this is a reference for Justin when reviewing scoring results

---

### US-006: Run Full Scoring and Verify Results
**Priority:** 6
**Status:** [ ] Incomplete

**Description:**
Run the angel investment scoring on all contacts and verify the results.

**Acceptance Criteria:**
- [ ] Run: `source .venv/bin/activate && cd scripts/intelligence && python score_ask_readiness.py --goal kindora_angel_investment`
- [ ] Script completes without errors
- [ ] Print distribution: count by tier (ready_now, cultivate_first, long_term, not_a_fit)
- [ ] Query and display top 20 ready_now contacts: name, company, score, check size, reasoning (first 100 chars)
- [ ] Verify top 5 results make intuitive sense (high-capacity, mission-aligned, warm relationship)
- [ ] Verify at least 1 not_a_fit result makes sense (cold, no capacity, or wrong profile)

**Notes:**
- Expected runtime: ~5-10 minutes with 150 workers
- Expected cost: ~$3-4 on OpenAI
- The full run scores ~2,400 contacts (those with enough data)
- Use Supabase MCP `execute_sql` to query results after scoring

---

### US-007: Deploy to Vercel
**Priority:** 7
**Status:** [ ] Incomplete

**Description:**
Deploy the new API route and UI page to production.

**Acceptance Criteria:**
- [ ] Verify Vercel account: `cd job-matcher-ai && npx vercel whoami` should show `justin-outdoorithm`
- [ ] If wrong account: update token in `~/Library/Application Support/com.vercel.cli/auth.json` to `vcp_8dUg...dRM8`
- [ ] Deploy: `cd /Users/Justin/Code/TrueSteele/contacts/job-matcher-ai && npx vercel --prod --yes --scope true-steele`
- [ ] Verify deployment succeeds (no build errors)
- [ ] Verify page loads at production URL

**Notes:**
- Auth token for justin-outdoorithm: `vcp_8dUg...dRM8` (permanent, no expiration)
- Config path: `~/Library/Application Support/com.vercel.cli/auth.json`
