# Project: Network Intelligence Overhaul — Donor Psychology & Wealth Signals

## Overview

Full overhaul of the Network Intelligence tool to use Justin's familiarity ratings as primary signal (replacing AI proximity), integrate wealth data (FEC political donations + real estate holdings), structured institutional overlap with temporal analysis, and AI ask-readiness scoring using a deep donor psychology prompt. The tool should produce precisely ranked fundraising lists where every contact has been assessed for ask-readiness by a reasoning model.

## Technical Context

- **Tech Stack:** Next.js 14 (App Router), TypeScript, Supabase (PostgreSQL + pgvector), Tailwind CSS, Claude Sonnet 4.6 for agent, GPT-5 mini for batch processing
- **Python venv:** `/Users/Justin/Code/TrueSteele/contacts/.venv/` (has supabase, apify-client, python-dotenv, openai)
- **Existing patterns:** Python batch scripts in `scripts/intelligence/` use ThreadPoolExecutor, Supabase pagination with `.range()`, `.env` for secrets
- **API keys in .env:** `OPENFEC_API_KEY`, `BATCHDATA_API_KEY`, `OPENAI_APIKEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- **Key API findings (tested 2026-02-20 through 2026-02-21):** OpenFEC works great (free). Real estate uses validated three-step pipeline: Apify `one-api/skip-trace` ($0.007, name→address) → Zillow autocomplete (FREE, address→ZPID) → Apify `happitap/zillow-detail-scraper` (~$0.003, ZPID→Zestimate). GPT-5 mini validates address matches. Tested at 15 contacts: 87% address found, 69% validated, 78% Zestimate obtained. GPT-5 mini does NOT support temperature=0 (use default only). REJECTED: BatchData ($500/mo), Melissa (wrong direction), Trestle (no name→address), EnformionGO (blocked), Open People Search (discontinued).
- **Plan file:** `/Users/Justin/.claude/plans/cozy-munching-dongarra.md` — contains full design details, donor psychology prompt, JSONB schemas, etc.

## Important References

- **Full plan with donor psychology prompt, JSONB schemas, and architecture:** `/Users/Justin/.claude/plans/cozy-munching-dongarra.md`
- **Network Intelligence System doc:** `docs/NETWORK_INTELLIGENCE_SYSTEM.md`
- **Existing enrichment scripts:** `scripts/intelligence/tag_contacts_gpt5m.py`, `scripts/intelligence/generate_embeddings.py`, `scripts/intelligence/gather_comms_history.py`
- **Network tools:** `job-matcher-ai/lib/network-tools.ts`
- **Search route:** `job-matcher-ai/app/api/network-intel/search/route.ts`
- **Agent route:** `job-matcher-ai/app/api/network-intel/route.ts`
- **Types:** `job-matcher-ai/lib/types.ts`

---

## User Stories

### US-001: Update Network Intelligence System Documentation
**Priority:** 1
**Status:** [x] Complete

**Description:**
Update `docs/NETWORK_INTELLIGENCE_SYSTEM.md` with a new "Phase 6: Network Intelligence Overhaul" section documenting: audit findings (7 gaps), donor psychology framework, wealth screening strategy (FEC + real estate), structured institutional overlap design, ask-readiness scoring approach, and the full search/UI rewire plan.

**Acceptance Criteria:**
- [x] New section added covering: audit context, donor psychology framework (4 pillars), wealth signals (FEC + real estate), structured overlap design, ask-readiness schema, search system changes, UI changes
- [x] Donor psychology framework documented in detail (relationship depth, giving capacity, philanthropic propensity, psychological readiness, behavioral insights)
- [x] All new JSONB schemas documented (fec_donations, real_estate_data, shared_institutions, ask_readiness)
- [x] Implementation order and cost estimates included
- [x] File compiles/renders correctly as markdown

---

### US-002: Database Migration — New Columns & Indexes
**Priority:** 2
**Status:** [x] Complete

**Description:**
Create Supabase migration adding new columns for wealth signals, structured overlap, and ask-readiness. Apply via Supabase MCP or direct SQL.

**Acceptance Criteria:**
- [x] Migration file created at `supabase/migrations/20260220_network_intel_overhaul.sql`
- [x] Columns added: `shared_institutions JSONB`, `comms_last_date DATE`, `comms_thread_count SMALLINT`, `fec_donations JSONB`, `real_estate_data JSONB`, `ask_readiness JSONB`
- [x] Indexes created: `idx_contacts_familiarity`, `idx_contacts_comms_last`, `idx_contacts_ask_readiness (GIN)`
- [x] Migration applied successfully to Supabase (use MCP `apply_migration` or direct SQL execution)
- [x] Verify columns exist by querying a sample contact

---

### US-003: Backfill Comms Summary Fields
**Priority:** 3
**Status:** [x] Complete

**Description:**
Create and run a script to denormalize `communication_history` JSONB into the new `comms_last_date` and `comms_thread_count` columns for fast filtering/sorting.

**Acceptance Criteria:**
- [x] Script created at `scripts/intelligence/backfill_comms_fields.py`
- [x] Reads `communication_history` JSONB for contacts that have it (~628 contacts)
- [x] Extracts `last_contact` → `comms_last_date` and `total_threads` → `comms_thread_count`
- [x] Script runs successfully and updates all 628 contacts
- [x] Verify with sample query: `SELECT count(*) FROM contacts WHERE comms_last_date IS NOT NULL` should be ~628

---

### US-004: FEC Political Donation Enrichment Script
**Priority:** 4
**Status:** [x] Complete

**Description:**
Create a script that queries the OpenFEC API to find federal campaign contribution records for each contact, storing results in the `fec_donations` JSONB column. This is the strongest free wealth indicator available.

**Acceptance Criteria:**
- [x] Script created at `scripts/intelligence/enrich_fec_donations.py`
- [x] Queries OpenFEC `/schedules/schedule_a/` endpoint by contributor name (first + last)
- [x] Filters by recent cycles (2020-2026)
- [x] Disambiguates common names using state/city match
- [x] Stores results in `contacts.fec_donations` JSONB matching schema in plan (total_amount, donation_count, max_single, cycles, recent_donations, employer_from_fec, occupation_from_fec, last_checked)
- [x] Supports `--test` flag (1 contact), `--batch N` flag, `--start-from` flag
- [x] Rate limits to stay under 1,000 req/hour
- [x] Test run succeeds with `--test` flag on a known contact
- [x] Uses env var `OPENFEC_API_KEY` from `.env`

**Notes:**
- API docs: https://api.open.fec.gov/developers/
- Endpoint: `GET /v1/schedules/schedule_a/?contributor_name=LAST,FIRST&two_year_transaction_period=2024&api_key=KEY`
- Rate limit: 1,000 requests/hour with API key

---

### US-005: Real Estate Holdings Enrichment Script (Three-Step Pipeline)
**Priority:** 5
**Status:** [x] Complete

**Description:**
Create a production script that uses the validated three-step pipeline to get real estate data for top contacts: (1) Apify `one-api/skip-trace` for home address by name, (2) Zillow autocomplete API for ZPID, (3) Apify `happitap/zillow-detail-scraper` for Zestimate + property data. GPT-5 mini validates each skip-trace result matches the correct person. Stores results in `real_estate_data` JSONB column.

**Background (validated 2026-02-21):**
Three-step pipeline tested at 15 contacts: 87% address found, 69% validated by GPT-5 mini, 100% ZPID found, 78% Zestimate obtained. ~$0.01/contact total. Test script at `scripts/intelligence/test_real_estate_pipeline.py`.

**Acceptance Criteria:**
- [x] Script created at `scripts/intelligence/enrich_real_estate.py`
- [x] Step 1: Apify `one-api/skip-trace` — input `{"name": ["FirstName LastName; City, ST"]}` — returns home address, age, phones, emails
- [x] Step 2: Zillow autocomplete — `https://www.zillowstatic.com/autocomplete/v3/suggestions?q={address}&resultTypes=allAddress` — returns ZPID
- [x] Step 3: Apify `happitap/zillow-detail-scraper` — input `{"startUrls": [{"url": "https://www.zillow.com/homedetails/{slug}/{zpid}_zpid/"}]}` — returns Zestimate + property data
- [x] GPT-5 mini validates skip-trace result matches contact (name match, location consistency, age plausibility) — NOTE: does NOT support temperature=0, use default
- [x] Only processes contacts with `familiarity_rating >= 2 OR ai_capacity_tier = 'major_donor'`
- [x] Stores results in `contacts.real_estate_data` JSONB: {address, zestimate, rent_zestimate, beds, baths, sqft, year_built, property_type, confidence, source, last_checked}
- [x] Batch skip-trace (send multiple names per Apify run, ~25 per batch for efficiency)
- [x] Batch Zillow detail (send multiple URLs per Apify run)
- [x] Supports `--test`, `--batch N`, `--start-from` flags
- [x] Test run succeeds with `--test` flag
- [x] Contacts with failed validation are logged but not stored (or stored with confidence: "rejected")

**Notes:**
- APIFY_API_KEY already in .env
- Skip-trace: $0.007/result, Zillow detail: ~$0.003/result, Zillow autocomplete: FREE
- Expected ~500-700 contacts in scope, ~$6 total
- Reference test script: `scripts/intelligence/test_real_estate_pipeline.py`

---

### US-006: Structured Institutional Overlap Script
**Priority:** 6
**Status:** [x] Complete

**Description:**
Create a script that uses GPT-5 mini to analyze institutional overlap between Justin and each contact, with temporal period analysis. Stores structured results in `shared_institutions` JSONB column.

**Acceptance Criteria:**
- [x] Script created at `scripts/intelligence/score_overlap.py`
- [x] Includes Justin's full career timeline (Bain 2006-2008, Bridgespan 2008-2010, Year Up 2010-2012, HBS/HKS 2012-2014, Google.org 2014-2019, Outdoorithm 2018-present, True Steele 2019-present, Kindora 2020-present, Outdoorithm Collective 2022-present, SF Foundation Board 2021-present, UVA ~2002-2006)
- [x] Sends contact's `enrich_employment`, `enrich_education`, `enrich_volunteering` + `connected_on` to GPT-5 mini with structured output
- [x] Output schema: `[{name, type, overlap, justin_period, contact_period, temporal_overlap, depth, notes}]`
- [x] Only processes contacts with existing shared institutions in ai_tags (~1,200 contacts)
- [x] Supports `--test`, `--batch N`, `--start-from` flags
- [x] Test run succeeds and produces valid structured overlap data
- [x] Uses Pydantic schema for structured output (follow pattern from `tag_contacts_gpt5m.py`)

---

### US-007: Ask-Readiness Scoring Script (Donor Psychology)
**Priority:** 7
**Status:** [x] Complete

**Description:**
Create the core scoring script that uses GPT-5 mini with the donor psychology prompt to assess each contact's ask-readiness for Outdoorithm fundraising. This is the most important script — it produces the per-contact reasoning that powers the entire system.

**Acceptance Criteria:**
- [x] Script created at `scripts/intelligence/score_ask_readiness.py`
- [x] Uses full donor psychology system prompt from plan file (all 4 pillars + behavioral insights + scoring guidance)
- [x] Per-contact context includes: familiarity_rating, position/company/headline, shared_institutions, ai_capacity_tier, ai_outdoorithm_fit, fec_donations summary, real_estate_data summary, communication_history summary, connected_on
- [x] Uses GPT-5 mini with Pydantic structured output for the response schema (score, tier, reasoning, recommended_approach, ask_timing, cultivation_needed, suggested_ask_range, personalization_angle, risk_factors)
- [x] Stores results in `contacts.ask_readiness` JSONB under `outdoorithm_fundraising` key with `scored_at` timestamp
- [x] Goal is parameterized (can re-run for `kindora_sales` etc.)
- [x] Supports `--test`, `--batch N`, `--start-from`, `--goal` flags
- [x] Concurrent batch processing (ThreadPoolExecutor, ~8 workers)
- [x] Test run on 1 contact produces valid, reasonable scoring
- [x] Prints summary stats at end (count by tier, score distribution)

**Notes:**
- Read the full donor psychology prompt from `/Users/Justin/.claude/plans/cozy-munching-dongarra.md` Phase 3
- Expected cost: ~$7.20 for all 2,400 contacts
- This is the most critical script — take time to get the prompt and context assembly right

---

### US-008: Update FilterState & Types
**Priority:** 8
**Status:** [x] Complete

**Description:**
Add new filter fields to the FilterState type and NetworkContact interface to support familiarity, communication history, and ask-readiness filtering.

**Acceptance Criteria:**
- [x] `job-matcher-ai/lib/types.ts` updated: FilterState adds `familiarity_min?: number`, `has_comms?: boolean`, `comms_since?: string`, `shared_institution?: string`, `goal?: string`
- [x] FilterState `sort_by` type extended with `'familiarity' | 'comms_recency' | 'ask_readiness'`
- [x] `job-matcher-ai/lib/supabase.ts` NetworkContact interface verified to include `familiarity_rating`, `comms_last_date`, `comms_thread_count`, `shared_institutions`, `ask_readiness`
- [x] TypeScript compiles without errors (`cd job-matcher-ai && npx tsc --noEmit`)

---

### US-009: Update Search Route & NETWORK_SELECT_COLS
**Priority:** 9
**Status:** [x] Complete

**Description:**
Add the new columns to NETWORK_SELECT_COLS in both `network-tools.ts` and `search/route.ts`. Add new filter support to the search route for familiarity, comms, and goal-based sorting.

**Acceptance Criteria:**
- [x] `NETWORK_SELECT_COLS` in `job-matcher-ai/lib/network-tools.ts` adds: `familiarity_rating, comms_last_date, comms_thread_count, ask_readiness`
- [x] `NETWORK_SELECT_COLS` in `job-matcher-ai/app/api/network-intel/search/route.ts` adds same columns
- [x] `executeStructuredSearch` handles: `familiarity_min` (gte filter), `has_comms` (comms_thread_count > 0), `comms_since` (comms_last_date gte), `goal` (sorts by ask_readiness->>goal->>score DESC)
- [x] New sort options: `familiarity` (familiarity_rating DESC), `comms_recency` (comms_last_date DESC), `ask_readiness` (requires goal)
- [x] Default sort changed from `ai_proximity_score` to `familiarity_rating DESC, comms_last_date DESC NULLS LAST`
- [x] `applyPostFilters` updated for hybrid search path
- [x] TypeScript compiles without errors

---

### US-010: Add goal_search Tool
**Priority:** 10
**Status:** [x] Complete

**Description:**
Add a new `goal_search` tool to the agent's toolkit that queries contacts ranked by AI ask-readiness for a specific goal, returning reasoning alongside results.

**Acceptance Criteria:**
- [x] New tool `goal_search` added to `NETWORK_TOOLS` array in `job-matcher-ai/lib/network-tools.ts`
- [x] Tool definition includes: goal (enum), tier filter, min_familiarity, limit parameters
- [x] Implementation queries contacts WHERE `ask_readiness->{goal}` IS NOT NULL
- [x] Filters by tier if specified
- [x] Sorts by `(ask_readiness->{goal}->>'score')::int DESC`
- [x] Returns contact data + ask_readiness reasoning, tier, score, recommended_approach
- [x] Tool handler added to the agent's tool execution in `route.ts`
- [x] TypeScript compiles without errors

---

### US-011: Update Agent System Prompt
**Priority:** 11
**Status:** [x] Complete

**Description:**
Rewrite the agent system prompt in `route.ts` to replace AI proximity with familiarity as primary signal, explain ask-readiness tiers, and instruct the agent to use `goal_search` for fundraising queries.

**Acceptance Criteria:**
- [x] System prompt in `job-matcher-ai/app/api/network-intel/route.ts` rewritten
- [x] Familiarity rating (0-4) explained as primary relationship measure
- [x] Ask-readiness tiers explained (ready_now, cultivate_first, long_term, not_a_fit)
- [x] Agent instructed to use `goal_search` tool first for fundraising/outreach queries
- [x] Agent instructed to show reasoning from ask_readiness alongside results
- [x] Communication history context mentioned as available data
- [x] Proximity score demoted to supplementary/legacy signal
- [x] TypeScript compiles without errors

---

### US-012: Update Parse-Filters Route
**Priority:** 12
**Status:** [ ] Incomplete

**Description:**
Update the NL query → FilterState parsing system prompt to understand familiarity ratings, communication history filters, and goal-based sorting.

**Acceptance Criteria:**
- [ ] `job-matcher-ai/app/api/network-intel/parse-filters/route.ts` system prompt updated
- [ ] Prompt explains familiarity scale (0=don't know, 1=recognize, 2=know, 3=good relationship, 4=close/trusted)
- [ ] Prompt explains ask-readiness tiers and goal parameter
- [ ] For fundraising/outreach queries, parser defaults to setting `goal: 'outdoorithm_fundraising'` and `sort_by: 'ask_readiness'`
- [ ] Tool schema updated to include new FilterState fields
- [ ] Test: "who should I reach out to for fundraising?" should produce filters with goal set
- [ ] TypeScript compiles without errors

---

### US-013: Update Contact Detail & Outreach Context
**Priority:** 13
**Status:** [ ] Incomplete

**Description:**
Add familiarity rating, communication history, institutional overlap, and ask-readiness data to the contact detail endpoint and outreach draft context.

**Acceptance Criteria:**
- [ ] `job-matcher-ai/app/api/network-intel/contact/[id]/route.ts` returns: familiarity_rating, comms_last_date, comms_thread_count, communication_history (recent threads + relationship_summary), shared_institutions, ask_readiness
- [ ] `getContactDetail` in `network-tools.ts` fetches all new fields (select `*` or add specific columns)
- [ ] `getOutreachContext` in `network-tools.ts` includes familiarity level, last email date/subject, shared institutional overlap with dates
- [ ] `job-matcher-ai/app/api/network-intel/outreach/draft/route.ts` `fetchContactContext` includes communication history and familiarity in the context sent to Claude for draft generation
- [ ] TypeScript compiles without errors

---

### US-014: Update Contacts Table UI
**Priority:** 14
**Status:** [ ] Incomplete

**Description:**
Replace the Proximity column with Familiarity, add Last Contact column, and add Ask Readiness column when a goal filter is active.

**Acceptance Criteria:**
- [ ] `job-matcher-ai/components/contacts-table.tsx` updated
- [ ] "Proximity" column replaced with "Familiarity" showing 0-4 as filled/empty circles (e.g., 3/4 = three filled, one empty)
- [ ] "Last Contact" column added showing date with recency color coding (green = <3mo, yellow = 3-12mo, gray = >12mo, no color = no data)
- [ ] When `goal` filter is active in current filters, show "Ask Readiness" column with tier badge (colored: green=ready_now, yellow=cultivate_first, gray=long_term, red=not_a_fit) + score number
- [ ] Sort options updated: add familiarity, last_contact, ask_readiness to SortField type
- [ ] Keep existing columns: capacity, outdoorithm fit, kindora type
- [ ] TypeScript compiles without errors
- [ ] Visual check: table renders correctly with new columns

---

### US-015: Update Contact Detail Sheet UI
**Priority:** 15
**Status:** [ ] Incomplete

**Description:**
Add relationship, communication history, institutional overlap, and ask-readiness sections to the contact detail slide-out sheet.

**Acceptance Criteria:**
- [ ] `job-matcher-ai/components/contact-detail-sheet.tsx` updated
- [ ] New "Your Relationship" section at top: familiarity rating as filled circles/stars, last contact date, email thread count
- [ ] New "Communication History" section: recent thread subjects with dates, relationship summary text
- [ ] New "Institutional Overlap" section: list of shared institutions with type badges (employer/school/board), temporal overlap indicator (checkmark if overlapping periods, dates shown)
- [ ] When ask_readiness exists for current goal: "Ask Readiness" card showing tier badge, score, reasoning text, recommended approach, suggested ask range, personalization angle
- [ ] "AI Scores" section renamed to "AI Analysis", proximity demoted to secondary
- [ ] TypeScript compiles without errors
- [ ] Visual check: detail sheet renders correctly with new sections

---

### US-016: Update Filter Bar UI
**Priority:** 16
**Status:** [ ] Incomplete

**Description:**
Add filter chips for the new filter types: familiarity minimum, has communications, communications since date, and goal.

**Acceptance Criteria:**
- [ ] `job-matcher-ai/components/filter-bar.tsx` updated
- [ ] New chip type for `familiarity_min` (e.g., "Familiarity >= 3")
- [ ] New chip type for `has_comms` (e.g., "Has Email History")
- [ ] New chip type for `comms_since` (e.g., "Contacted Since Jan 2025")
- [ ] New chip type for `goal` (e.g., "Goal: Outdoorithm Fundraising")
- [ ] Chips are removable (clicking X removes the filter)
- [ ] Chip colors follow existing pattern (category-based color coding)
- [ ] TypeScript compiles without errors

---

### US-017: Tag Remaining 527 Contacts & Generate Embeddings
**Priority:** 17
**Status:** [ ] Incomplete

**Description:**
Run the existing `tag_contacts_gpt5m.py` and `generate_embeddings.py` scripts for the ~527 contacts that don't have AI tags yet.

**Acceptance Criteria:**
- [ ] Run `python scripts/intelligence/tag_contacts_gpt5m.py` — should find and tag ~527 untagged contacts
- [ ] Run `python scripts/intelligence/generate_embeddings.py` — should generate embeddings for contacts missing them
- [ ] Verify: `SELECT count(*) FROM contacts WHERE ai_tags IS NULL` should be 0 (or very close)
- [ ] Verify: `SELECT count(*) FROM contacts WHERE profile_embedding IS NULL AND enrichment_source = 'apify'` should be 0 (or very close)
- [ ] No errors in script output
