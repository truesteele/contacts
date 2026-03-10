# Project: Sally Steele — Network Intelligence Pipeline

## Overview

Reproduce Justin's full contact intelligence system for Sally Steele (co-founder, Outdoorithm Collective) to expand the Come Alive 2026 donor campaign to Sally's network. Sally's data lives in separate tables — not mixed with Justin's 2,940 contacts. The pipeline: import contacts → enrich → score → scaffold campaign → write outreach → build UI.

## Technical Context

- **Tech Stack:** Python 3.12, OpenAI API (GPT-5 mini), Anthropic API (Claude Opus 4.6), Supabase (PostgreSQL), psycopg2
- **Python venv:** `.venv/` (arm64) — activate with `source .venv/bin/activate`
- **Existing patterns:** Justin's scripts in `scripts/intelligence/` are THE model — adapt them for Sally's tables
- **Env vars:** `OPENAI_APIKEY` (no underscore before KEY), `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_DB_PASSWORD`, `APIFY_TOKEN`
- **DB connection:** Supabase REST API via `supabase-py` for reads/writes. Direct psycopg2 via `db.ypqsrejrsocebnldicke.supabase.co:5432` if needed.
- **GPT-5 mini:** Does NOT support temperature=0. Use default only.
- **OpenAI structured output:** `openai.responses.parse(model="gpt-5-mini", instructions=SYSTEM_PROMPT, input=context, text_format=PydanticModel)`
- **Workers:** 150 for GPT-5 mini, 3-5 for Opus (quality over speed)
- **MCP server:** `supabase-contacts` for DB operations (NOT `supabase_crm`)

## Sally's Input Data

| File | Content |
|------|---------|
| `docs/Sally/linkedin_connections.csv` | 849 LinkedIn connections: First Name, Last Name, LinkedIn URL, Title, Connection Date |
| `docs/Sally/sally_network_contacts.csv` | 850 rows with density scores, calendar_email column (56 with emails) |
| `docs/Sally/sms_parsed.json` | 1,230 SMS conversations keyed by phone number |
| `docs/Sally/COMMS_HISTORY_PROMPT.md` | Prompt for Sally to fill Gmail/Calendar gaps (future use) |

## Sally's Google Accounts

- `sally.steele@gmail.com` (project: claude-mcp-sally-steele)
- `sally@outdoorithm.com` (project: claude-mcp-outdoorithm)
- `sally@outdoorithmcollective.org` (project: claude-mcp-collective)

Credentials at: `docs/credentials/Sally/` (client_secret JSON files — app credentials, NOT tokens)

## Database Tables (created in US-001)

- `sally_contacts` — main contact table (mirrors `contacts`)
- `sally_contact_email_threads` — email threads (mirrors `contact_email_threads`)
- `sally_contact_calendar_events` — calendar events (mirrors `contact_calendar_events`)
- `sally_contact_sms_conversations` — SMS threads (mirrors `contact_sms_conversations`)

## Key Reference Scripts (MUST READ before adapting)

| Justin's Script | Sally's Adaptation | Purpose |
|-----------------|-------------------|---------|
| `scripts/intelligence/gather_comms_history.py` | `sally/gather_comms.py` | Gmail scanning |
| `scripts/intelligence/gather_calendar_meetings.py` | `sally/gather_calendar.py` | Calendar fetching |
| `scripts/enrichment/enrich_contacts_apify.py` | `sally/enrich_apify.py` | LinkedIn enrichment |
| `scripts/intelligence/tag_contacts_gpt5m.py` | `sally/tag_contacts.py` | AI tagging |
| `scripts/intelligence/score_comms_closeness.py` | `sally/score_comms_closeness.py` | Comms scoring |
| `scripts/intelligence/rebuild_comms_summary.py` | `sally/rebuild_comms_summary.py` | Comms rollup |
| `scripts/intelligence/score_ask_readiness.py` | `sally/score_ask_readiness.py` | Ask readiness |
| `scripts/intelligence/scaffold_campaign.py` | `sally/scaffold_campaign.py` | Campaign scaffolding |
| `scripts/intelligence/write_personal_outreach.py` | `sally/write_outreach.py` | Outreach writing |
| `scripts/intelligence/write_campaign_copy.py` | `sally/write_campaign_copy.py` | Campaign copy |

---

## User Stories

### US-001: Create Sally Database Tables
**Priority:** 1
**Status:** [x] Complete

**Description:**
Create the Sally-specific database tables via Supabase migration.

**Acceptance Criteria:**
- [ ] Run migration SQL to create `sally_contacts` table with all columns from the plan (identity, contact info, enrichment, AI scoring, comms, donor scoring, campaign, cross-reference)
- [ ] Create `sally_contact_email_threads` table (mirrors `contact_email_threads` with FK to `sally_contacts`)
- [ ] Create `sally_contact_calendar_events` table (mirrors `contact_calendar_events` with FK to `sally_contacts`)
- [ ] Create `sally_contact_sms_conversations` table (mirrors `contact_sms_conversations` with FK to `sally_contacts`)
- [ ] Create indexes on sally_contacts: linkedin_url, normalized_full_name, ask_readiness (GIN)
- [ ] Create indexes on related tables: contact_id columns
- [ ] Verify all 4 tables exist: `SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'sally_%'`
- [ ] Save migration file at `supabase/migrations/20260309_add_sally_contacts.sql`

**Notes:**
- Use the full schema from the approved plan at `/Users/Justin/.claude/plans/snoopy-marinating-tiger.md`
- Use `supabase-contacts` MCP server's `apply_migration` tool for the SQL
- The `justin_contact_id` column should reference `contacts(id)` for cross-network linking
- Include `embedding vector(768)` and `interests_embedding vector(768)` columns (pgvector is already installed)

---

### US-002: Create and Run import_linkedin.py
**Priority:** 2
**Status:** [x] Complete

**Description:**
Import Sally's 849 LinkedIn connections into `sally_contacts`.

**Acceptance Criteria:**
- [ ] Script created at `scripts/intelligence/sally/import_linkedin.py`
- [ ] Reads `docs/Sally/linkedin_connections.csv` (columns: First Name, Last Name, LinkedIn URL, Title, Connection Date)
- [ ] Cross-references `docs/Sally/sally_network_contacts.csv` to pull `calendar_email` where available
- [ ] Normalizes LinkedIn URLs (lowercase, strip trailing slash, ensure www prefix)
- [ ] Generates `normalized_full_name` (lowercase, stripped)
- [ ] Generates `linkedin_username` from URL
- [ ] Sets `position` from Title column, `connected_on` from Connection Date
- [ ] Inserts into `sally_contacts` with upsert on `linkedin_url`
- [ ] Run: `source .venv/bin/activate && python scripts/intelligence/sally/import_linkedin.py`
- [ ] Verify: `SELECT count(*) FROM sally_contacts` → ~849
- [ ] Verify: `SELECT count(*) FROM sally_contacts WHERE email IS NOT NULL` → ~56

**Notes:**
- Read `docs/Sally/linkedin_connections.csv` and `docs/Sally/sally_network_contacts.csv` to understand the column mappings
- The sally_network_contacts.csv has a `calendar_email` column with ~56 non-null values — these are the email addresses
- Use supabase-py client for inserts (same pattern as other import scripts)

---

### US-003: Create and Run import_sms.py
**Priority:** 3
**Status:** [x] Complete

**Description:**
Match Sally's 1,230 SMS conversations to her imported contacts and store in `sally_contact_sms_conversations`.

**Acceptance Criteria:**
- [ ] Script created at `scripts/intelligence/sally/import_sms.py`
- [ ] Reads `docs/Sally/sms_parsed.json` (keyed by phone number)
- [ ] For each SMS entry, extracts: contact_name, phone_number, total_count, sent_count, received_count, first_date, last_date, sample_messages (from recent_messages field)
- [ ] Matches phone numbers to `sally_contacts` by fuzzy name matching (same approach as `sync_phone_backup.py`)
- [ ] Matching strategy: exact first+last name match first, then fuzzy (Levenshtein or token overlap)
- [ ] Inserts into `sally_contact_sms_conversations` with `match_method` and `match_confidence`
- [ ] Updates `sally_contacts` SMS comms fields where matched
- [ ] CLI args: `--test` (10 contacts), `--force`, `--dry-run`
- [ ] Run: `source .venv/bin/activate && python scripts/intelligence/sally/import_sms.py`
- [ ] Verify: `SELECT count(*) FROM sally_contact_sms_conversations` → 100+ matched
- [ ] Print summary: total SMS entries, matched to contacts, unmatched

**Notes:**
- Read `scripts/intelligence/sync_phone_backup.py` for the name-matching approach
- The SMS JSON structure per entry: `{contact_name, phone_number, total_count, sent_count, received_count, first_date, last_date, recent_messages: [{date, direction, body, contact_name, readable_date}], sample_messages: [...]}`
- Many SMS entries won't match LinkedIn contacts — that's expected (service numbers, non-LinkedIn contacts)

---

### US-004: Create gather_comms.py and gather_calendar.py
**Priority:** 4
**Status:** [x] Complete

**Description:**
Create Gmail and Calendar gathering scripts for Sally's 3 Google accounts. These scripts require OAuth tokens to run — create the scripts and an OAuth setup helper, but don't run the full gather (tokens not yet available).

**Acceptance Criteria:**
- [ ] Script created at `scripts/intelligence/sally/gather_comms.py`
  - Adapted from `scripts/intelligence/gather_comms_history.py`
  - Reads from `sally_contacts` instead of `contacts`
  - Writes to `sally_contact_email_threads` instead of `contact_email_threads`
  - Scans 3 accounts: sally.steele@gmail.com, sally@outdoorithm.com, sally@outdoorithmcollective.org
  - Uses Google OAuth credentials from `docs/credentials/Sally/` or `~/.google_workspace_mcp/credentials/`
  - Includes `--recent-days N` flag for incremental scanning
  - CLI args: `--test`, `--batch N`, `--workers N`, `--contact-id ID`, `--recent-days N`
- [ ] Script created at `scripts/intelligence/sally/gather_calendar.py`
  - Adapted from `scripts/intelligence/gather_calendar_meetings.py`
  - Reads from `sally_contacts` instead of `contacts`
  - Writes to `sally_contact_calendar_events` instead of `contact_calendar_events`
  - Scans same 3 accounts
  - Pulls events since Jan 1, 2023
  - CLI args: `--test`, `--recent-days N`
- [ ] Script created at `scripts/intelligence/sally/setup_oauth.py`
  - Reads client_secret files from `docs/credentials/Sally/`
  - Runs OAuth2 installed app flow for each account
  - Saves tokens to `docs/credentials/Sally/tokens/` or `~/.google_workspace_mcp/credentials/`
  - Uses `google-auth-oauthlib` library
  - Scopes: Gmail readonly, Calendar readonly
- [ ] All 3 scripts pass syntax check: `python -c "import ast; ast.parse(open('scripts/intelligence/sally/<script>.py').read())"`

**Notes:**
- READ `scripts/intelligence/gather_comms_history.py` and `scripts/intelligence/gather_calendar_meetings.py` THOROUGHLY before adapting
- The OAuth helper uses `google-auth-oauthlib` InstalledAppFlow — Sally will need to run this interactively in a browser
- Credential files at `docs/credentials/Sally/`:
  - `client_secret_682208951145-*.json` → sally.steele@gmail.com
  - `client_secret_498441498515-*.json` → sally@outdoorithm.com
  - `client_secret_443275901963-*.json` → sally@outdoorithmcollective.org
- Do NOT run gather_comms.py or gather_calendar.py in this story — tokens aren't available yet

---

### US-005: Create enrich_apify.py
**Priority:** 5
**Status:** [x] Complete

**Description:**
Create the Apify LinkedIn enrichment script for Sally's contacts.

**Acceptance Criteria:**
- [ ] Script created at `scripts/intelligence/sally/enrich_apify.py`
- [ ] Adapted from `scripts/enrichment/enrich_contacts_apify.py`
- [ ] Reads from `sally_contacts` instead of `contacts`
- [ ] Writes enrichment data to `sally_contacts` enrich_* columns
- [ ] Uses `harvestapi/linkedin-profile-scraper` Apify actor
- [ ] Same column mapping as Justin's enrichment: enrich_current_company, enrich_current_title, enrich_current_since, enrich_years_in_current_role, enrich_total_experience_years, enrich_follower_count, enrich_connections, enrich_schools, enrich_companies_worked, enrich_titles_held, enrich_skills, enrich_board_positions, enrich_volunteer_orgs, enrich_employment, enrich_education
- [ ] CLI args: `--test` (1 contact), `--batch N`, `--force`, `--contact-id ID`
- [ ] Script passes syntax check: `python -c "import ast; ast.parse(open('scripts/intelligence/sally/enrich_apify.py').read())"`
- [ ] Test with `--test` flag (enriches 1 contact): `source .venv/bin/activate && python scripts/intelligence/sally/enrich_apify.py --test`

**Notes:**
- READ `scripts/enrichment/enrich_contacts_apify.py` THOROUGHLY before adapting
- The Apify actor `harvestapi/linkedin-profile-scraper` costs ~$0.004/profile
- Full run (849 contacts) costs ~$3.40 and takes 30-60 minutes — DO NOT run full batch, only `--test`
- The `APIFY_TOKEN` env var is already in `.env`
- URL normalization: `urllib.parse.unquote()` + ensure `www.linkedin.com` prefix

---

### US-006: Create tag_contacts.py with Sally Anchor Profile
**Priority:** 6
**Status:** [x] Complete

**Description:**
Create the LLM tagging script for Sally's contacts with her own anchor profile.

**Acceptance Criteria:**
- [ ] Script created at `scripts/intelligence/sally/tag_contacts.py`
- [ ] Adapted from `scripts/intelligence/tag_contacts_gpt5m.py`
- [ ] Reads from `sally_contacts` instead of `contacts`
- [ ] Writes AI scoring fields to `sally_contacts`: ai_tags, ai_proximity_score, ai_proximity_tier, ai_capacity_score, ai_capacity_tier, ai_outdoorithm_fit
- [ ] Contains `SALLY_ANCHOR_PROFILE` constant — Sally's career timeline:
  - LinkedIn: https://www.linkedin.com/in/steelesally/
  - Co-Founder, Outdoorithm / Outdoorithm Collective
  - Build the profile from what we know + note it should be updated after Apify enrichment runs
  - Include key facts: Sally Steele, co-founder Outdoorithm Collective (2024-present), co-founder Outdoorithm (2023-present)
- [ ] System prompt references Sally (not Justin) as the network anchor
- [ ] Same Pydantic schemas: RelationshipProximity, GivingCapacity, TopicalAffinity, SalesFit, OutreachContext → ContactIntelligence
- [ ] ThreadPoolExecutor with 150 default workers
- [ ] CLI args: `--test`, `--batch N`, `--workers N`, `--force`, `--contact-id ID`, `--ids` (comma-separated)
- [ ] Script passes syntax check
- [ ] Do NOT run full batch (requires Apify enrichment first)

**Notes:**
- READ `scripts/intelligence/tag_contacts_gpt5m.py` THOROUGHLY — the ANCHOR_PROFILE pattern is critical
- Sally's full profile will be available after Apify enrichment (US-005 full run) — for now, use a placeholder with known facts
- Add a comment noting: "TODO: Update SALLY_ANCHOR_PROFILE after running enrich_apify.py on Sally's LinkedIn profile"

---

### US-007: Create rebuild_comms_summary.py and score_comms_closeness.py
**Priority:** 7
**Status:** [x] Complete

**Description:**
Create the communication summary aggregator and closeness scoring scripts for Sally.

**Acceptance Criteria:**
- [ ] Script created at `scripts/intelligence/sally/rebuild_comms_summary.py`
  - Adapted from `scripts/intelligence/rebuild_comms_summary.py`
  - Aggregates from `sally_contact_email_threads`, `sally_contact_sms_conversations`, `sally_contact_calendar_events` into `sally_contacts.comms_summary`
  - Updates: `comms_last_date`, `comms_thread_count`, `comms_meeting_count`, `comms_last_meeting`, `comms_call_count`, `comms_last_call`
  - CLI args: `--test`, `--contact-id ID`, `--force`
- [ ] Script created at `scripts/intelligence/sally/score_comms_closeness.py`
  - Adapted from `scripts/intelligence/score_comms_closeness.py`
  - Reads comms data from Sally's tables
  - Writes to `sally_contacts`: comms_closeness, comms_momentum, comms_reasoning
  - Same channel signal hierarchy: Phone > SMS > Calendar > 1:1 Email > LinkedIn DM > Group Email
  - No anchor profile needed (purely behavioral)
  - CLI args: `--test`, `--batch N`, `--workers N`, `--force`, `--contact-id ID`
- [ ] Both scripts pass syntax check
- [ ] Do NOT run full batch (requires comms data from US-004)

**Notes:**
- READ `scripts/intelligence/rebuild_comms_summary.py` and `scripts/intelligence/score_comms_closeness.py` before adapting
- The closeness script is purely behavioral — no anchor profile changes needed, just table names

---

### US-008: Create backfill_familiarity.py and score_ask_readiness.py
**Priority:** 8
**Status:** [ ] Complete

**Description:**
Create the familiarity backfill and ask-readiness scoring scripts for Sally.

**Acceptance Criteria:**
- [ ] Script created at `scripts/intelligence/sally/backfill_familiarity.py`
  - Uses comms density + SMS presence as proxy for familiarity_rating (0-4 scale)
  - Logic: SMS present = at least 2, high SMS count (>50) = 3, very high (>200) + calendar meetings = 4
  - No SMS or comms = 0 (unknown)
  - Reads from `sally_contacts` + `sally_contact_sms_conversations`
  - Writes to `sally_contacts.familiarity_rating`
- [ ] Script created at `scripts/intelligence/sally/score_ask_readiness.py`
  - Adapted from `scripts/intelligence/score_ask_readiness.py`
  - Reads from `sally_contacts` instead of `contacts`
  - Writes to `sally_contacts.ask_readiness`
  - System prompt replaces "Justin Steele" with "Sally Steele" throughout
  - Same donor psychology GPT-5 mini prompt (Granovetter framework, 2x2 relationship map)
  - Same goal: `outdoorithm_fundraising`
  - ThreadPoolExecutor with 150 default workers
  - CLI args: `--test`, `--batch N`, `--workers N`, `--force`, `--contact-id ID`
- [ ] Both scripts pass syntax check
- [ ] Do NOT run full batch (requires enrichment + comms data)

**Notes:**
- READ `scripts/intelligence/score_ask_readiness.py` — the system prompt is long and has many "Justin Steele" references to replace
- The familiarity backfill is a simple heuristic — Sally can override manually later

---

### US-009: Create scaffold_campaign.py and write_campaign_copy.py
**Priority:** 9
**Status:** [ ] Complete

**Description:**
Create the campaign scaffolding and copy-writing scripts for Sally's contacts.

**Acceptance Criteria:**
- [ ] Script created at `scripts/intelligence/sally/scaffold_campaign.py`
  - Adapted from `scripts/intelligence/scaffold_campaign.py`
  - Reads from `sally_contacts` where ask_readiness tier is ready_now or cultivate_first ≥60
  - Writes to `sally_contacts.campaign_2026`
  - Same Pydantic schemas: persona, campaign_list, capacity_tier, etc.
  - System prompt embeds full strategy docs content
  - CLI args: `--test`, `--batch N`, `--workers N`, `--force`, `--contact-id ID`
- [ ] Script created at `scripts/intelligence/sally/write_campaign_copy.py`
  - Adapted from `scripts/intelligence/write_campaign_copy.py`
  - Reads from `sally_contacts` where campaign_2026 scaffold exists and campaign_list IN (B, C, D)
  - Writes campaign_copy to `sally_contacts.campaign_2026`
  - Same Pydantic schemas: pre_email_note, text_followup_opener, etc.
  - CLI args: `--test`, `--batch N`, `--workers N`, `--force`, `--contact-id ID`
- [ ] Both scripts pass syntax check
- [ ] Do NOT run full batch (requires ask-readiness scoring first)

**Notes:**
- READ `scripts/intelligence/scaffold_campaign.py` and `scripts/intelligence/write_campaign_copy.py` before adapting
- READ strategy docs: `docs/Outdoorithm/DONOR_SEGMENTATION.md`, `docs/Outdoorithm/COME_ALIVE_2026_Campaign.md`, `docs/Outdoorithm/OC_FUNDRAISING_PLAYBOOK.md`
- The system prompts reference Justin's voice — for Sally, we'll use Sally's persona (created in US-010)
- For now, use a placeholder for Sally's voice until US-010 creates the persona doc

---

### US-010: Create Sally Email Persona and write_outreach.py
**Priority:** 10
**Status:** [ ] Complete

**Description:**
Build Sally's email persona from her LinkedIn posts and create the personal outreach writer script.

**Acceptance Criteria:**
- [ ] Read `docs/LinkedIn/Sally Posts/LinkedIn_Posts_Complete_With_Metrics_SallySteele.md` to analyze Sally's writing voice
- [ ] Create `docs/Sally/SALLY_EMAIL_PERSONA.md` following same structure as `docs/Justin/JUSTIN_EMAIL_PERSONA.md`
  - Voice patterns (sentence structure, common phrases, transitions)
  - Tone and register
  - Topics and themes she writes about
  - How she addresses people
  - Example phrases and fragments
- [ ] Script created at `scripts/intelligence/sally/write_outreach.py`
  - Adapted from `scripts/intelligence/write_personal_outreach.py`
  - Uses Claude Opus 4.6 for List A personal messages
  - System prompt uses Sally's voice patterns (from SALLY_EMAIL_PERSONA.md)
  - Reads from `sally_contacts` where campaign_2026 scaffold list = A
  - Writes to `sally_contacts.campaign_2026.personal_outreach`
  - Low concurrency: 3 workers
  - CLI args: `--test`, `--force`, `--contact-id ID`, `--workers N`
- [ ] Script passes syntax check
- [ ] Do NOT run (requires full pipeline completion first)

**Notes:**
- READ `docs/Justin/JUSTIN_EMAIL_PERSONA.md` for the format/structure to follow
- READ `docs/LinkedIn/Sally Posts/LinkedIn_Posts_Complete_With_Metrics_SallySteele.md` to study Sally's writing voice
- READ `scripts/intelligence/write_personal_outreach.py` for the script pattern
- The persona doc is critical — it determines whether outreach sounds like Sally

---

### US-011: Create Sally Ask-Readiness API Route and UI Page
**Priority:** 11
**Status:** [ ] Complete

**Description:**
Create the API route and UI page for Sally's ask-readiness view.

**Acceptance Criteria:**
- [ ] API route created at `job-matcher-ai/app/api/network-intel/sally/ask-readiness/route.ts`
  - Same query pattern as `job-matcher-ai/app/api/network-intel/ask-readiness/route.ts`
  - Reads from `sally_contacts` instead of `contacts`
  - Flattens ask_readiness JSONB by goal into top-level fields
  - Returns sorted by score descending with tier_counts
- [ ] UI page created at `job-matcher-ai/app/tools/sally-ask-readiness/page.tsx`
  - Clone of `job-matcher-ai/app/tools/ask-readiness/page.tsx`
  - Header says "Sally's Network — Ask Readiness" to differentiate
  - Points to `/api/network-intel/sally/ask-readiness` endpoint
  - Same features: sortable table, tier filters, search, CSV export
- [ ] TypeScript compiles without errors

**Notes:**
- READ `job-matcher-ai/app/api/network-intel/ask-readiness/route.ts` and `job-matcher-ai/app/tools/ask-readiness/page.tsx` THOROUGHLY
- The Supabase client in the Next.js app uses `NEXT_PUBLIC_SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` env vars
- Verify the table name `sally_contacts` is correctly referenced in all queries

---

### US-012: Create Sally Campaign API Route and UI Page
**Priority:** 12
**Status:** [ ] Complete

**Description:**
Create the API route and UI page for Sally's campaign view.

**Acceptance Criteria:**
- [ ] API route created at `job-matcher-ai/app/api/network-intel/sally/campaign/route.ts`
  - Same query pattern as `job-matcher-ai/app/api/network-intel/campaign/route.ts`
  - Reads from `sally_contacts` instead of `contacts`
  - Flattens campaign_2026 JSONB (scaffold, personal_outreach, campaign_copy, send_status)
- [ ] UI page created at `job-matcher-ai/app/tools/sally-campaign/page.tsx`
  - Clone of `job-matcher-ai/app/tools/campaign/page.tsx`
  - Header says "Sally's Network — Campaign" to differentiate
  - Points to `/api/network-intel/sally/campaign` endpoint
  - Same features: list selector, outreach preview, send functionality
- [ ] TypeScript compiles without errors

**Notes:**
- READ `job-matcher-ai/app/api/network-intel/campaign/route.ts` and `job-matcher-ai/app/tools/campaign/page.tsx` THOROUGHLY
- The campaign send route will also need a Sally version eventually but skip it for now — just the view

---

### US-013: Create and Run cross_reference.py
**Priority:** 13
**Status:** [ ] Complete

**Description:**
Match Sally's contacts against Justin's to find shared connections.

**Acceptance Criteria:**
- [ ] Script created at `scripts/intelligence/sally/cross_reference.py`
- [ ] Matches `sally_contacts` against Justin's `contacts` by LinkedIn URL
- [ ] Populates `justin_contact_id` FK for shared connections
- [ ] Generates summary: total shared connections, top shared contacts by combined score
- [ ] Run: `source .venv/bin/activate && python scripts/intelligence/sally/cross_reference.py`
- [ ] Verify: `SELECT count(*) FROM sally_contacts WHERE justin_contact_id IS NOT NULL` → print count
- [ ] Print top 20 shared connections (sorted by Justin's ask_readiness score)

**Notes:**
- LinkedIn URL matching should normalize URLs first (lowercase, strip trailing slash, www prefix)
- This can run immediately after US-002 (LinkedIn import) — no enrichment needed

---

### US-014: Create NETWORK_ONBOARDING_PLAYBOOK.md
**Priority:** 14
**Status:** [ ] Complete

**Description:**
Document the entire pipeline as a reproducible playbook for onboarding future users.

**Acceptance Criteria:**
- [ ] Doc created at `docs/NETWORK_ONBOARDING_PLAYBOOK.md`
- [ ] Covers what input files are needed (LinkedIn CSV, SMS backup, Google credentials)
- [ ] Documents database table creation pattern (prefix with username)
- [ ] Lists all scripts and their purpose
- [ ] Provides script adaptation checklist (what constants to change per user)
- [ ] Documents pipeline execution order with dependencies
- [ ] Includes verification steps for each stage
- [ ] Includes cost estimates per stage
- [ ] References Sally's pipeline as the working example
- [ ] Self-contained — someone can follow this doc to onboard a new user

**Notes:**
- This should generalize the Sally pipeline — replace "Sally" with placeholders where appropriate
- Include the Google OAuth setup process
- Document the Apify enrichment costs and timing
