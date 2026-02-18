# Project: Network Intelligence System — Phase 1 & 2 (LLM Tagging + Embeddings)

## Overview

Build the first two layers of the Personal Network Intelligence System: LLM structured tagging (GPT-5 mini) and vector embeddings (pgvector). This processes all ~2,498 contacts to produce relationship proximity scores, giving capacity estimates, topical affinity tags, Kindora sales fit scores, and semantic similarity embeddings.

Full architecture and design: `docs/NETWORK_INTELLIGENCE_SYSTEM.md`

## Technical Context

- **Database:** Supabase PostgreSQL with pgvector 0.8.0
- **Python venv:** `/Users/Justin/Code/TrueSteele/contacts/.venv/` (activate with `source .venv/bin/activate`)
- **Existing patterns:** See `scripts/enrichment/enrich_contacts_apify.py` for ThreadPoolExecutor + Supabase pagination pattern
- **Contacts table:** 2,498 rows, ~130 columns including rich JSONB enrichment data (`enrich_employment`, `enrich_education`, `enrich_skills_detailed`, `enrich_volunteering`, etc.)
- **API keys:** In `.env` file (SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_APIKEY)
- **Supabase pagination:** Use `.range(offset, offset + page_size - 1)` for >1000 rows
- **Scripts location:** `scripts/intelligence/`

## Quality Gates

Since this is a Python data pipeline (not a TypeScript app), quality checks are:
1. Python script executes without errors
2. Expected data appears in Supabase (verified via SQL query)
3. Output quality is reasonable (spot-check scores and tags)

## User Stories

### US-001: Run Supabase Migration — Add Intelligence Columns and Indexes
**Priority:** 1
**Status:** [x] Complete

**Description:**
Add all new columns, vector indexes, and composite indexes to the contacts table as specified in Section 9 of the planning doc.

**Acceptance Criteria:**
- [x] Add columns: `ai_tags` (jsonb), `ai_tags_generated_at` (timestamptz), `ai_tags_model` (text)
- [x] Add columns: `profile_embedding` (vector(768)), `interests_embedding` (vector(768))
- [x] Add columns: `communication_history` (jsonb), `comms_last_gathered_at` (timestamptz)
- [x] Add denormalized score columns: `ai_proximity_score` (integer), `ai_proximity_tier` (text), `ai_capacity_score` (integer), `ai_capacity_tier` (text), `ai_kindora_prospect_score` (integer), `ai_kindora_prospect_type` (text), `ai_outdoorithm_fit` (text)
- [x] Create HNSW indexes on `profile_embedding` and `interests_embedding` (vector_cosine_ops, m=16, ef_construction=64)
- [x] Create composite index on `(ai_proximity_tier, ai_capacity_tier)` where `ai_proximity_score IS NOT NULL`
- [x] Create GIN index on `ai_tags` with `jsonb_path_ops`
- [x] Migration applied successfully via Supabase MCP `execute_sql` or `apply_migration`
- [x] Verify columns exist by querying `information_schema.columns`

**Notes:**
- Use the Supabase MCP tool (`mcp__supabase__execute_sql` or `mcp__supabase__apply_migration`) to run the migration
- Use `ALTER TABLE contacts ADD COLUMN IF NOT EXISTS` for idempotency
- See Section 9 of `docs/NETWORK_INTELLIGENCE_SYSTEM.md` for exact DDL

---

### US-002: Write LLM Tagging Script with Pydantic Schema
**Priority:** 2
**Status:** [x] Complete

**Description:**
Create `scripts/intelligence/tag_contacts_gpt5m.py` — the batch processing script that tags all contacts using GPT-5 mini structured output.

**Acceptance Criteria:**
- [x] Create `scripts/intelligence/` directory
- [x] Define Pydantic models matching the output schema in Section 5 of the planning doc (relationship_proximity, giving_capacity, topical_affinity, sales_fit, outreach_context)
- [x] Include Justin's profile as anchor context in the prompt (employers, schools, boards, key interests — from Section 3 of planning doc)
- [x] Assemble per-contact context document from enrichment JSONB fields (enrich_employment, enrich_education, enrich_skills_detailed, enrich_volunteering, enrich_certifications, enrich_publications, enrich_honors_awards, headline, summary, company, position, connected_on, city, state)
- [x] Use OpenAI Responses API with `response_format={"type": "json_schema", ...}` for guaranteed schema compliance
- [x] Batch processing with `ThreadPoolExecutor(max_workers=10)` and Supabase pagination (`.range()`)
- [x] Store full LLM output in `ai_tags` JSONB column
- [x] Extract and store denormalized scores (ai_proximity_score, ai_proximity_tier, ai_capacity_score, ai_capacity_tier, ai_kindora_prospect_score, ai_kindora_prospect_type, ai_outdoorithm_fit)
- [x] Set `ai_tags_generated_at` and `ai_tags_model` metadata columns
- [x] Add `--test` flag that processes only 5 contacts for validation
- [x] Add `--dry-run` flag that assembles prompts but doesn't call OpenAI
- [x] Add progress logging (processed X/Y contacts, errors, cost estimate)
- [x] Handle errors gracefully (skip failed contacts, log errors, continue processing)
- [x] Load env vars from `.env` file
- [x] Script runs without import errors: `source .venv/bin/activate && python scripts/intelligence/tag_contacts_gpt5m.py --dry-run`

**Notes:**
- Use model `gpt-5-mini` (or `gpt-4o-mini` as fallback if gpt-5-mini is not available)
- Refer to `scripts/enrichment/enrich_contacts_apify.py` for the ThreadPoolExecutor + Supabase pagination pattern
- The JSONB enrichment fields may contain stringified JSON — handle both parsed and string-wrapped formats
- Skip contacts that already have `ai_tags` (unless `--force` flag is passed)
- Estimated cost: ~$2.50 for all 2,498 contacts

---

### US-003: Test LLM Tagging on 10 Contacts and Validate Output Quality
**Priority:** 3
**Status:** [ ] Incomplete

**Description:**
Run the tagging script in test mode on 10 diverse contacts. Validate that the structured output is correct, scores are reasonable, and personalization hooks are useful.

**Acceptance Criteria:**
- [ ] Run: `source .venv/bin/activate && python scripts/intelligence/tag_contacts_gpt5m.py --test`
- [ ] Script completes without errors for all 10 contacts
- [ ] Verify `ai_tags` JSONB is stored correctly for the 10 test contacts (query Supabase)
- [ ] Verify denormalized scores are populated (ai_proximity_score, ai_capacity_score, etc.)
- [ ] Spot-check: at least one contact with shared employer should have proximity score >= 60
- [ ] Spot-check: C-suite contacts should have capacity_tier of "major_donor" or "mid_level"
- [ ] Spot-check: topics array should contain relevant tags (not empty)
- [ ] Spot-check: outreach_context.personalization_hooks should be non-empty and relevant
- [ ] If output quality is poor, adjust the system prompt and re-test
- [ ] Log the cost of the 10-contact test run

**Notes:**
- Pick diverse contacts: some who clearly worked with Justin (e.g., Google colleagues), some C-suite, some unknown
- If `gpt-5-mini` model is not available, fall back to `gpt-4o-mini` and note this in progress.txt
- The test should reveal any issues with JSONB field parsing, schema compliance, or prompt quality

---

### US-004: Run Full LLM Tagging Batch on All Contacts
**Priority:** 4
**Status:** [ ] Incomplete

**Description:**
Process all ~2,498 contacts through GPT-5 mini structured tagging. Monitor progress, costs, and errors.

**Acceptance Criteria:**
- [ ] Run: `source .venv/bin/activate && python scripts/intelligence/tag_contacts_gpt5m.py`
- [ ] Script completes processing all contacts (may skip already-tagged from test run)
- [ ] Total errors < 5% of contacts
- [ ] Verify count: `SELECT COUNT(*) FROM contacts WHERE ai_tags IS NOT NULL` should be ~2,400+
- [ ] Verify score distribution makes sense:
  - `SELECT ai_proximity_tier, COUNT(*) FROM contacts WHERE ai_proximity_tier IS NOT NULL GROUP BY ai_proximity_tier` — should NOT be 94% "distant" (unlike the old Perplexity scoring)
  - `SELECT ai_capacity_tier, COUNT(*) FROM contacts WHERE ai_capacity_tier IS NOT NULL GROUP BY ai_capacity_tier` — should show spread across tiers
- [ ] Log final statistics: total processed, errors, cost, time elapsed
- [ ] Document the score distribution in progress.txt

**Notes:**
- This will take ~5-10 minutes at 50 RPM with 10 concurrent workers
- Expected cost: ~$2.50
- If rate limited, the script should handle 429 errors with exponential backoff
- If some contacts fail, note the failure count — a few failures are acceptable

---

### US-005: Write and Run Embedding Generation for All Contacts
**Priority:** 5
**Status:** [ ] Incomplete

**Description:**
Create `scripts/intelligence/generate_embeddings.py` and run it to generate profile_embedding and interests_embedding for all contacts.

**Acceptance Criteria:**
- [ ] Create script at `scripts/intelligence/generate_embeddings.py`
- [ ] Build profile text document per contact: `{name} | {headline}\nCurrently: {title} at {company}\nPreviously: {company1} ({title1}), ...\nEducation: {school1} ({degree1}), ...\nSkills: {skill1}, ...\nVolunteering: {org1} ({role1}), ...\nLocation: {city}, {state}\nAbout: {summary}`
- [ ] Build interests text document per contact: use LLM-generated tags from ai_tags (topical_affinity.topics, talking_points) + summary + headline
- [ ] Call `text-embedding-3-small` with `dimensions=768` for both documents
- [ ] Store vectors in `profile_embedding` and `interests_embedding` columns
- [ ] Batch embedding calls (OpenAI supports batching up to 2048 inputs per call)
- [ ] Process all ~2,498 contacts
- [ ] Verify count: `SELECT COUNT(*) FROM contacts WHERE profile_embedding IS NOT NULL` should be ~2,400+
- [ ] Test a sample similarity query: find 5 contacts most similar to a known contact
- [ ] Log cost and time elapsed (expected: ~$0.05 total, ~2 minutes)
- [ ] Script runs without errors

**Notes:**
- OpenAI's embedding API supports batch input — send up to 100 texts per call for efficiency
- For contacts without ai_tags (failed tagging), build interests text from raw enrichment data
- Use the same `.env` file and venv as the tagging script

---

### US-006: Create Supabase RPC Functions for Search
**Priority:** 6
**Status:** [ ] Incomplete

**Description:**
Create the SQL RPC functions in Supabase that enable similarity search and hybrid search queries.

**Acceptance Criteria:**
- [ ] Create `match_contacts_by_profile` function (Section 6 of planning doc) — takes query_embedding, match_threshold, match_count
- [ ] Create `match_contacts_by_interests` function — same pattern but uses interests_embedding
- [ ] Create `hybrid_contact_search` function (Section 6 of planning doc) — combines semantic + keyword + structured filters with RRF fusion
- [ ] Create full-text search tsvector index on `headline || summary || company || position`
- [ ] All functions created via Supabase MCP execute_sql
- [ ] Test `match_contacts_by_profile` with a sample embedding — returns ranked results
- [ ] Test `hybrid_contact_search` with text query + embedding — returns fused results
- [ ] Verify functions are accessible via Supabase RPC client

**Notes:**
- See Section 6 of `docs/NETWORK_INTELLIGENCE_SYSTEM.md` for exact SQL
- The hybrid search function uses COALESCE for the FULL OUTER JOIN
- Test with a real query like "outdoor equity education nonprofit"

---

### US-007: Validate End-to-End with Use Case Queries
**Priority:** 7
**Status:** [ ] Incomplete

**Description:**
Run all 5 use cases from Section 12 of the planning doc and verify the system produces meaningful results.

**Acceptance Criteria:**
- [ ] Use Case 1 (Outdoorithm Collective Fundraiser Invite): Query contacts with proximity >= 40 AND outdoorithm_invite_fit IN ('high', 'medium') — should return a list of real contacts
- [ ] Use Case 2 (Kindora Enterprise Prospects): Query contacts with kindora_prospect_score >= 50 AND prospect_type IN ('enterprise_buyer', 'champion') — should return foundation/network leaders
- [ ] Use Case 3 (People Interested in Outdoor Equity): Run semantic search with "outdoor equity, nature access, public lands" embedding — results should include people with relevant backgrounds
- [ ] Use Case 4 (Close Contacts I Haven't Spoken To): Query proximity >= 60 — should return people Justin actually knows (Google colleagues, HBS classmates, etc.)
- [ ] Use Case 5 (Hybrid Search): Run hybrid_contact_search with "philanthropy education technology" — results should combine semantic and keyword matches
- [ ] Save sample results (top 10 from each use case) to `docs/reports/network-intelligence-validation.md`
- [ ] Identify any calibration issues (e.g., scores too high, too low, wrong tier assignments)
- [ ] Document findings in progress.txt

**Notes:**
- Use Supabase MCP execute_sql to run queries
- For Use Case 3, generate the query embedding via OpenAI API first
- If results look wrong, note what needs calibration — this is validation, not a blocker
- This story is primarily evaluation — document results, don't fix calibration issues
