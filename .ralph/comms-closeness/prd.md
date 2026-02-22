# Project: Communication Closeness Scoring

## Overview
Build a unified communication data architecture across email, LinkedIn DMs, and SMS, then use GPT-5 mini to score each contact's **communication closeness** and **momentum** as a behavioral complement to the existing manual familiarity_rating (0-4).

See `docs/RELATIONSHIP_DIMENSIONS_FRAMEWORK.md` for the full theoretical framework (Granovetter tie strength, 2x2 relationship map, channel signal quality hierarchy).

## Technical Context
- **Database:** Supabase PostgreSQL (use Supabase MCP `execute_sql` for queries, `apply_migration` for DDL)
- **Existing tables:** `contact_email_threads` (10,216 rows — email + LinkedIn), `contact_sms_conversations` (147 rows — SMS)
- **Python venv:** `.venv/` (arm64, Python 3.12). Activate with `source .venv/bin/activate`
- **Scripts directory:** `scripts/intelligence/`
- **OpenAI:** GPT-5 mini, env var `OPENAI_APIKEY`, 150 workers optimal, does NOT support temperature=0
- **Existing patterns:** See `scripts/intelligence/score_ask_readiness.py` and `scripts/intelligence/tag_contacts_gpt5m.py` for GPT-5 mini structured output patterns
- **UI app:** Next.js in `job-matcher-ai/`, TypeScript, Tailwind, shadcn/ui
- **Contact detail API:** `job-matcher-ai/app/api/network-intel/contact/[id]/route.ts`
- **Contact detail sheet:** `job-matcher-ai/components/contact-detail-sheet.tsx`
- **Contacts table:** `job-matcher-ai/components/contacts-table.tsx`

## Important Notes
- All Python scripts should follow existing patterns in `scripts/intelligence/`
- Supabase pagination: use `.range(offset, offset + page_size - 1)` for >1000 rows
- GPT-5 mini does NOT support temperature=0 — use default only
- OpenAI key env var is `OPENAI_APIKEY` (no underscore before KEY)
- For null byte safety in JSONB, see `_strip_null_bytes()` in `score_ask_readiness.py`
- Run Python scripts from repo root: `python scripts/intelligence/script_name.py`

## User Stories

### US-001: Database Migration — Add Unified Comms Columns
**Priority:** 1
**Status:** [x] Complete

**Description:**
Add columns to support the unified communication architecture and closeness scoring.

**Acceptance Criteria:**
- [x] Add `channel` (text, NOT NULL DEFAULT 'email') column to `contact_email_threads`
- [x] Add `is_group` (boolean, DEFAULT false) column to `contact_email_threads`
- [x] Add `participant_count` (smallint, DEFAULT 2) column to `contact_email_threads`
- [x] Add `comms_closeness` (text) column to `contacts` — enum: active_inner_circle, regular_contact, occasional, dormant, one_way, no_history
- [x] Add `comms_momentum` (text) column to `contacts` — enum: growing, stable, fading, inactive
- [x] Add `comms_reasoning` (text) column to `contacts`
- [x] Add `comms_summary` (jsonb) column to `contacts`
- [x] Apply migration via Supabase MCP `apply_migration` tool
- [x] Verify columns exist with a SELECT query

**Notes:**
- Use `apply_migration` MCP tool (NOT `execute_sql`) for DDL
- Migration name should be descriptive: `add_comms_closeness_columns`

---

### US-002: Backfill Channel and Group Status on Existing Threads
**Priority:** 2
**Status:** [ ] Incomplete

**Description:**
Set the `channel` and `is_group` fields for all existing rows in `contact_email_threads`.

**Acceptance Criteria:**
- [ ] Set `channel = 'linkedin'` for all rows where `account_email = 'linkedin'`
- [ ] Set `channel = 'email'` for all rows where `account_email != 'linkedin'` (these are Gmail accounts)
- [ ] Set `is_group = true` for email threads where participants JSONB array has more than 2 entries (or where raw_messages contain multiple distinct non-Justin recipients)
- [ ] Set `is_group = false` for LinkedIn threads (always 1:1) and email threads with ≤2 participants
- [ ] Set `participant_count` based on the length of the `participants` JSONB array
- [ ] Verify with: `SELECT channel, is_group, count(*) FROM contact_email_threads GROUP BY channel, is_group`
- [ ] All 10,216 existing rows should have non-null channel values

**Notes:**
- Use `execute_sql` for UPDATE statements
- The `participants` column is a JSONB array of names/emails
- For rows where participants is null, default is_group to false and participant_count to 2

---

### US-003: Migrate SMS Data into Unified Table
**Priority:** 3
**Status:** [ ] Incomplete

**Description:**
Copy data from `contact_sms_conversations` into `contact_email_threads` with `channel = 'sms'`, creating a truly unified communication table.

**Acceptance Criteria:**
- [ ] Insert 147 SMS conversation rows into `contact_email_threads` with:
  - `channel = 'sms'`
  - `account_email = 'sms'`
  - `thread_id = 'sms_' || phone_number` (unique identifier)
  - `contact_id` from the SMS table
  - `message_count`, `first_message_date`, `last_message_date` from SMS table
  - `direction` derived from sent_count/received_count (bidirectional if both > 0, outbound if only sent, inbound if only received)
  - `is_group = false` (SMS is always 1:1 in our data)
  - `participant_count = 2`
  - `subject = sms_contact_name` (use contact name as subject for display)
  - `snippet` from first sample message if available
  - `raw_messages = sample_messages` from SMS table
  - `summary` from SMS table
  - `gathered_at` from SMS table
- [ ] Verify count: `SELECT channel, count(*) FROM contact_email_threads GROUP BY channel` should show sms: ~147
- [ ] Verify no duplicate thread_ids
- [ ] Do NOT delete the original `contact_sms_conversations` table (keep as backup)

**Notes:**
- Use `execute_sql` for the INSERT...SELECT statement
- Be careful with null contact_id rows in SMS table (skip them)

---

### US-004: Build rebuild_comms_summary.py Script
**Priority:** 4
**Status:** [ ] Incomplete

**Description:**
Create a Python script that aggregates communication data across all channels per contact and stores a structured `comms_summary` JSONB on the contacts table.

**Acceptance Criteria:**
- [ ] Create `scripts/intelligence/rebuild_comms_summary.py`
- [ ] Script queries `contact_email_threads` grouped by contact_id
- [ ] Per contact, computes:
  - `total_threads` (int)
  - `total_messages` (int, sum of message_count)
  - `channels` object with per-channel breakdown: `{email: {threads, messages, first_date, last_date, bidirectional, inbound, outbound, group_threads}, linkedin: {...}, sms: {...}}`
  - `overall_first_date` and `overall_last_date` across all channels
  - `bidirectional_pct` (float, % of threads that are bidirectional)
  - `group_thread_pct` (float, % of email threads that are group)
  - `most_recent_channel` (which channel had the most recent activity)
  - `chronological_summary` (string, e.g., "3 emails in 2024, 1 LinkedIn DM in Jan 2025, 2 SMS in Feb 2026")
- [ ] Also updates `comms_last_date` and `comms_thread_count` on contacts table
- [ ] Supports `--test` flag to preview 5 contacts without writing
- [ ] Supports `--contact-id N` flag to process a single contact
- [ ] Uses Supabase Python client (not psycopg2) following existing patterns
- [ ] Handles pagination for >1000 rows
- [ ] Script runs without errors in test mode

**Notes:**
- Follow patterns from `scripts/intelligence/gather_comms_history.py` for Supabase client setup
- Use `.env` for SUPABASE_URL and SUPABASE_SERVICE_KEY
- The chronological_summary should be human-readable, grouped by year/month

---

### US-005: Run rebuild_comms_summary.py on All Contacts
**Priority:** 5
**Status:** [ ] Incomplete

**Description:**
Execute the comms summary rebuild script to populate `comms_summary` JSONB for all contacts.

**Acceptance Criteria:**
- [ ] Run `python scripts/intelligence/rebuild_comms_summary.py` (no --test flag)
- [ ] Script completes without errors
- [ ] Verify: `SELECT count(*) FROM contacts WHERE comms_summary IS NOT NULL` shows contacts with communication data populated
- [ ] Verify: `SELECT comms_summary FROM contacts WHERE comms_summary IS NOT NULL LIMIT 1` shows expected JSONB structure
- [ ] Verify: `comms_last_date` and `comms_thread_count` are updated

**Notes:**
- If script errors, fix the bug and retry
- Expected: ~1,100+ contacts should have comms_summary (those with any threads)

---

### US-006: Build score_comms_closeness.py Script
**Priority:** 6
**Status:** [ ] Incomplete

**Description:**
Create a GPT-5 mini scoring script that reads each contact's `comms_summary` JSONB and outputs `comms_closeness`, `comms_momentum`, and `comms_reasoning`.

**Acceptance Criteria:**
- [ ] Create `scripts/intelligence/score_comms_closeness.py`
- [ ] Uses OpenAI Responses API with structured output (Pydantic schema), following patterns from `score_ask_readiness.py`
- [ ] GPT-5 mini prompt includes:
  - The Granovetter framework context (behavioral dimension only)
  - Channel signal quality hierarchy: SMS (highest) > 1:1 email > LinkedIn DM > group email (lowest)
  - Clear definitions for each `comms_closeness` label (from `docs/RELATIONSHIP_DIMENSIONS_FRAMEWORK.md`)
  - Clear definitions for each `comms_momentum` label
  - Instruction to assess ONLY based on communication data, NOT personal knowledge
  - Today's date for recency calculations
- [ ] Input per contact: the `comms_summary` JSONB (no name, no profile data, no familiarity_rating)
- [ ] Output schema: `comms_closeness` (enum), `comms_momentum` (enum), `comms_reasoning` (string, 1-2 sentences)
- [ ] Uses `ThreadPoolExecutor(max_workers=150)` for concurrent API calls
- [ ] Supports `--test` flag (process 5 contacts, print results, don't write)
- [ ] Supports `--workers N` flag to override default concurrency
- [ ] Supports `--force` flag to re-score contacts that already have comms_closeness
- [ ] Contacts with no comms_summary get `comms_closeness = 'no_history'`, `comms_momentum = 'inactive'` without calling GPT
- [ ] Saves results to `comms_closeness`, `comms_momentum`, `comms_reasoning` columns on contacts table
- [ ] Uses `_strip_null_bytes()` for JSONB safety (copy from score_ask_readiness.py)
- [ ] Script runs without errors in test mode

**Notes:**
- Model: `gpt-4.1-mini` (this is GPT-5 mini model ID in the OpenAI API)
  - Actually, check the model ID used in existing scripts (`score_ask_readiness.py` or `tag_contacts_gpt5m.py`) and use the same one
- Do NOT send familiarity_rating to the model — keep dimensions independent
- Estimated cost: ~$3-4 for ~2,900 contacts

---

### US-007: Run score_comms_closeness.py on All Contacts
**Priority:** 7
**Status:** [ ] Incomplete

**Description:**
Execute the comms closeness scoring script to label all contacts.

**Acceptance Criteria:**
- [ ] Run `python scripts/intelligence/score_comms_closeness.py` (no --test flag, 150 workers)
- [ ] Script completes without errors (or with <5 errors)
- [ ] Verify distribution: `SELECT comms_closeness, count(*) FROM contacts GROUP BY comms_closeness ORDER BY count(*) DESC`
- [ ] Verify momentum: `SELECT comms_momentum, count(*) FROM contacts GROUP BY comms_momentum ORDER BY count(*) DESC`
- [ ] Verify reasoning: `SELECT comms_reasoning FROM contacts WHERE comms_closeness = 'active_inner_circle' LIMIT 3`
- [ ] All contacts should have a comms_closeness value (including 'no_history' for those without comms data)

**Notes:**
- Use 150 workers (GPT-5 mini Tier 5 rate limit: 10,000 RPM)
- Expected distribution: ~1,100 with actual scored labels, ~1,800 with 'no_history'

---

### US-008: Update Ask-Readiness Script to Use Comms Closeness
**Priority:** 8
**Status:** [ ] Incomplete

**Description:**
Wire the new `comms_closeness` and `comms_momentum` into the ask-readiness scoring prompt so GPT can use behavioral communication data alongside subjective familiarity.

**Acceptance Criteria:**
- [ ] Update `scripts/intelligence/score_ask_readiness.py`:
  - Add `comms_closeness`, `comms_momentum` to the SELECT query
  - Update `summarize_comms()` to include closeness and momentum labels
  - Add a new section to the prompt explaining the two relationship dimensions:
    - familiarity_rating = subjective closeness (already in prompt)
    - comms_closeness = behavioral/data-derived communication signal
    - Explain that dormant strong ties (high familiarity + dormant comms) are high-leverage reactivation targets
  - Include the comms_momentum in the prompt (growing = strike now, fading = risk of losing)
- [ ] Verify script runs in test mode without errors: `python scripts/intelligence/score_ask_readiness.py --test --goal outdoorithm_fundraising`
- [ ] The prompt should reference the 2x2 relationship map from the framework doc

**Notes:**
- Do NOT run a full re-score in this story — just update the script
- The re-score can happen later as a separate decision

---

### US-009: Update Contact Detail API and UI
**Priority:** 9
**Status:** [ ] Incomplete

**Description:**
Show comms_closeness and comms_momentum in the contact detail sheet UI.

**Acceptance Criteria:**
- [ ] Update `job-matcher-ai/app/api/network-intel/contact/[id]/route.ts` to include `comms_closeness`, `comms_momentum`, `comms_reasoning` in the SELECT query
- [ ] Update `job-matcher-ai/components/contact-detail-sheet.tsx` to display:
  - Comms Closeness label with appropriate color badge (active_inner_circle=green, regular_contact=blue, occasional=yellow, dormant=orange, one_way=purple, no_history=gray)
  - Comms Momentum label with icon or badge (growing=up arrow green, stable=dash blue, fading=down arrow orange, inactive=x gray)
  - Comms Reasoning text below the badges
- [ ] Place this in the existing "Relationship" or "Communication" section of the detail sheet
- [ ] TypeScript typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

**Notes:**
- Follow existing UI patterns in contact-detail-sheet.tsx (look at how familiarity_rating, ask_readiness_tier are displayed)
- Use shadcn/ui Badge component for labels
- Keep it simple — badges + reasoning text
