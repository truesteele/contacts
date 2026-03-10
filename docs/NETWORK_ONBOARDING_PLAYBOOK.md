# Network Intelligence Onboarding Playbook

A step-by-step guide to onboard a new person's network into the TrueSteele contact intelligence system. This playbook generalizes the pipeline built for Justin Steele (2,940 contacts) and reproduced for Sally Steele (850 contacts).

**Working example:** Sally's pipeline — `scripts/intelligence/sally/` (15 scripts, 9,112 lines of Python)

---

## Prerequisites

### 1. Input Files Required

| File | Format | Content | How to Get |
|------|--------|---------|-----------|
| LinkedIn connections CSV | CSV | First Name, Last Name, LinkedIn URL, Title, Connection Date | LinkedIn Settings > Data Privacy > Get a copy of your data > Connections |
| SMS backup (optional) | JSON | Keyed by phone number: contact_name, message counts, dates, sample messages | Export via SMS Backup & Restore app, parse with `scripts/intelligence/sync_phone_backup.py` pattern |
| Google OAuth client secrets | JSON | One per Google account (Gmail/Calendar access) | Google Cloud Console > APIs & Credentials > Create OAuth 2.0 Client ID (Desktop app) |
| Network contacts CSV (optional) | CSV | Prior export with density scores, emails, etc. | Any existing contact list with email addresses |

### 2. Environment Setup

```bash
# Python venv (already exists at project root)
source .venv/bin/activate

# Required env vars in .env
OPENAI_APIKEY=sk-...          # GPT-5 mini (no underscore before KEY)
ANTHROPIC_API_KEY=sk-ant-...  # Claude Opus 4.6
SUPABASE_URL=https://...      # Supabase project URL
SUPABASE_KEY=eyJ...           # Supabase anon key
SUPABASE_SERVICE_KEY=eyJ...   # Supabase service role key
SUPABASE_DB_PASSWORD=...      # Direct PostgreSQL access
APIFY_TOKEN=apify_api_...     # Apify for LinkedIn enrichment
```

### 3. Naming Convention

All resources for a new user use a consistent prefix: `{user}_` (lowercase first name).

| Resource | Pattern | Example (Sally) |
|----------|---------|-----------------|
| DB tables | `{user}_contacts`, `{user}_contact_email_threads`, etc. | `sally_contacts` |
| Script directory | `scripts/intelligence/{user}/` | `scripts/intelligence/sally/` |
| API routes | `/api/network-intel/{user}/` | `/api/network-intel/sally/` |
| UI pages | `/tools/{user}-ask-readiness`, `/tools/{user}-campaign` | `/tools/sally-ask-readiness` |
| Persona doc | `docs/{User}/` | `docs/Sally/` |

---

## Pipeline Execution

### Stage 1: Database Tables

**Script:** Migration SQL via Supabase MCP
**Depends on:** Nothing
**Cost:** $0
**Time:** 1 minute

Create 4 tables mirroring Justin's schema:

1. **`{user}_contacts`** — main contact table with identity, enrichment, AI scoring, comms, donor scoring, campaign, and cross-reference columns
2. **`{user}_contact_email_threads`** — email threads (FK to `{user}_contacts`)
3. **`{user}_contact_calendar_events`** — calendar events (FK to `{user}_contacts`)
4. **`{user}_contact_sms_conversations`** — SMS conversations (FK to `{user}_contacts`)

Key columns in `{user}_contacts`:
- `justin_contact_id bigint REFERENCES contacts(id)` — cross-reference to Justin's network
- `embedding vector(768)` and `interests_embedding vector(768)` — for vector search (pgvector)
- `ai_tags jsonb`, `ask_readiness jsonb`, `campaign_2026 jsonb` — structured AI output
- `comms_summary jsonb` — aggregated communication stats

**Indexes:** linkedin_url, normalized_full_name, ask_readiness (GIN), contact_id on child tables.

**Adaptation checklist:**
- [ ] Replace `sally_` prefix with `{user}_` in all table/index names
- [ ] Keep the `justin_contact_id` FK (all networks cross-reference to Justin's as the primary)

**Verification:**
```sql
SELECT table_name FROM information_schema.tables WHERE table_name LIKE '{user}_%';
-- Should return 4 tables
```

**Reference:** `supabase/migrations/20260309_add_sally_contacts.sql`

---

### Stage 2: Import LinkedIn Connections

**Script:** `{user}/import_linkedin.py`
**Depends on:** Stage 1
**Cost:** $0
**Time:** 1 minute

Reads the LinkedIn CSV, normalizes URLs, and inserts into `{user}_contacts`.

**What it does:**
- Parses CSV columns: First Name, Last Name, LinkedIn URL, Title, Connection Date
- Normalizes LinkedIn URLs (lowercase, strip trailing slash, add `www.` prefix)
- Generates `normalized_full_name` (lowercase, stripped) and `linkedin_username` from URL
- Cross-references optional network CSV for email addresses
- Inserts with check-then-insert/update pattern (supabase-py has no native upsert on non-PK)

**Adaptation checklist:**
- [ ] Update table name: `sally_contacts` → `{user}_contacts`
- [ ] Update input file paths
- [ ] Update email column mapping if network CSV has different column names
- [ ] Handle connection date format (Sally's was "March 6, 2026" — others may differ)

**Verification:**
```sql
SELECT count(*) FROM {user}_contacts;              -- Should match CSV row count
SELECT count(*) FROM {user}_contacts WHERE email IS NOT NULL;  -- Contacts with known emails
```

**Reference:** `scripts/intelligence/sally/import_linkedin.py` (185 lines)

---

### Stage 3: Import SMS Conversations (Optional)

**Script:** `{user}/import_sms.py`
**Depends on:** Stage 2
**Cost:** $0
**Time:** 2 minutes

Matches SMS conversations to imported contacts by name.

**What it does:**
- Reads parsed SMS JSON (keyed by phone number)
- Merges duplicate phone formats (+1, parenthesized, plain digits)
- Filters to entries with contact_name (matchable)
- Matches by exact name (high confidence) then fuzzy SequenceMatcher >= 0.85 (medium confidence)
- Inserts into `{user}_contact_sms_conversations`

**Adaptation checklist:**
- [ ] Update table names
- [ ] Input file path for parsed SMS JSON
- [ ] Name matching may need tuning per user (nicknames, middle names)

**Verification:**
```sql
SELECT count(*) FROM {user}_contact_sms_conversations;  -- Matched conversations
```

**Reference:** `scripts/intelligence/sally/import_sms.py` (372 lines)

---

### Stage 4: Set Up Google OAuth

**Script:** `{user}/setup_oauth.py`
**Depends on:** Google OAuth client secrets
**Cost:** $0
**Time:** 5-10 minutes (interactive)

Runs OAuth2 installed app flow for each Google account. The user must sign in via browser and approve access.

**What it does:**
- Maps each account to its client_secret file
- Uses `google_auth_oauthlib.InstalledAppFlow` with local server on port 8080
- Saves tokens to `docs/credentials/{User}/tokens/{account}.json`
- Scopes: Gmail readonly, Calendar readonly

**Adaptation checklist:**
- [ ] Update account list (email addresses)
- [ ] Update client_secret file paths and project_id prefixes
- [ ] Store credential files in `docs/credentials/{User}/`

**Verification:**
```bash
python scripts/intelligence/{user}/setup_oauth.py --check
# Should show token status for each account
```

**Reference:** `scripts/intelligence/sally/setup_oauth.py` (235 lines)

---

### Stage 5: Gather Gmail Communication History

**Script:** `{user}/gather_comms.py`
**Depends on:** Stage 2, Stage 4 (OAuth tokens)
**Cost:** $0
**Time:** 30-60 minutes (depends on email volume)

Scans Gmail across all accounts for threads involving known contacts.

**What it does:**
- For each contact with an email, searches Gmail for matching threads
- Extracts thread metadata: subject, snippet, message count, dates, participants, direction
- Stores full `raw_messages` in JSONB for later analysis
- GPT-5 mini generates thread summaries
- Supports `--recent-days N` for incremental daily syncs

**Adaptation checklist:**
- [ ] Update table names: `sally_contacts` → `{user}_contacts`, `sally_contact_email_threads` → `{user}_contact_email_threads`
- [ ] Update `{USER}_EMAILS` set (self-filtering so user doesn't match as their own contact)
- [ ] Update account list
- [ ] Update credential paths
- [ ] System prompt: replace user name references

**Verification:**
```sql
SELECT count(DISTINCT contact_id) FROM {user}_contact_email_threads;  -- Contacts with email threads
SELECT count(*) FROM {user}_contact_email_threads;                     -- Total threads
```

**Reference:** `scripts/intelligence/sally/gather_comms.py` (838 lines)

---

### Stage 6: Gather Calendar Events

**Script:** `{user}/gather_calendar.py`
**Depends on:** Stage 2, Stage 4 (OAuth tokens)
**Cost:** $0
**Time:** 10-20 minutes

Pulls calendar events and matches attendees against contacts.

**What it does:**
- Event-centric: pulls ALL events, matches attendee emails against contact email lookup
- Classifies events: 1:1, small group, large group, all-day, conference
- Detects conference type: Zoom, Meet, Teams
- Updates `comms_meeting_count` and `comms_last_meeting` on contacts

**Adaptation checklist:**
- [ ] Update table names
- [ ] Update account list and credentials
- [ ] Update `{USER}_EMAILS` set
- [ ] Adjust event date range if needed (default: since Jan 1, 2023)

**Verification:**
```sql
SELECT count(DISTINCT contact_id) FROM {user}_contact_calendar_events;  -- Contacts with meetings
SELECT count(*) FROM {user}_contact_calendar_events;                     -- Total events
```

**Reference:** `scripts/intelligence/sally/gather_calendar.py` (836 lines)

---

### Stage 7: LinkedIn Enrichment (Apify)

**Script:** `{user}/enrich_apify.py`
**Depends on:** Stage 2
**Cost:** ~$0.004/profile (~$3.40 for 850 contacts)
**Time:** 30-60 minutes

Enriches contacts with full LinkedIn profile data via Apify.

**What it does:**
- Uses `harvestapi/linkedin-profile-scraper` Apify actor
- Batches 25 URLs per run, 8 concurrent runs
- Writes 16+ enrichment columns: current company/title, experience years, skills, schools, companies, employment history, education, board positions, volunteer orgs
- URL normalization: `urllib.parse.unquote()` + `www.linkedin.com` prefix

**Adaptation checklist:**
- [ ] Update table name
- [ ] Update `VALID_COLUMNS` whitelist (ensure only columns in `{user}_contacts` schema are written)
- [ ] `SUPABASE_SERVICE_KEY` env var

**Verification:**
```sql
SELECT count(*) FROM {user}_contacts WHERE enriched_at IS NOT NULL;  -- Should be 90%+ of total
SELECT count(*) FROM {user}_contacts WHERE enrich_current_company IS NOT NULL;
```

**Reference:** `scripts/intelligence/sally/enrich_apify.py` (498 lines)

---

### Stage 8: LLM Structured Tagging

**Script:** `{user}/tag_contacts.py`
**Depends on:** Stage 7 (Apify enrichment)
**Cost:** ~$1.70 for 850 contacts (GPT-5 mini)
**Time:** 10 minutes

AI tags every contact with proximity, capacity, topical affinity, and outreach context.

**What it does:**
- GPT-5 mini structured output via Pydantic schemas
- `{USER}_ANCHOR_PROFILE` constant — the user's career timeline for proximity scoring
- Produces: `ai_proximity_score` (0-100), `ai_capacity_score` (0-100), `ai_outdoorithm_fit`, `ai_tags` JSONB
- 150 concurrent workers (GPT-5 mini rate limit headroom)

**Adaptation checklist:**
- [ ] **CRITICAL:** Create `{USER}_ANCHOR_PROFILE` with the user's career timeline (schools, employers, boards, dates)
- [ ] Update after Apify enrichment reveals full career history
- [ ] Update table name
- [ ] System prompt: replace user name in all proximity descriptions
- [ ] Adjust `SELECT_COLS` based on which columns exist in `{user}_contacts`

**Verification:**
```sql
SELECT count(*) FROM {user}_contacts WHERE ai_tags IS NOT NULL;
SELECT ai_proximity_tier, count(*) FROM {user}_contacts GROUP BY ai_proximity_tier;
```

**Reference:** `scripts/intelligence/sally/tag_contacts.py` (599 lines)

---

### Stage 9: Rebuild Communication Summary

**Script:** `{user}/rebuild_comms_summary.py`
**Depends on:** Stages 3, 5, 6 (all comms data)
**Cost:** $0
**Time:** 2 minutes

Aggregates all communication channels into a single JSONB summary per contact.

**What it does:**
- Reads from `{user}_contact_email_threads`, `{user}_contact_calendar_events`, `{user}_contact_sms_conversations`
- Computes per-channel stats: thread count, message count, first/last dates, direction breakdown
- Writes `comms_summary` JSONB + denormalized fields to `{user}_contacts`

**Adaptation checklist:**
- [ ] Update all table names
- [ ] Add/remove channels based on available data (e.g., no call logs for some users)

**Verification:**
```sql
SELECT count(*) FROM {user}_contacts WHERE comms_summary IS NOT NULL;
```

**Reference:** `scripts/intelligence/sally/rebuild_comms_summary.py` (541 lines)

---

### Stage 10: Communication Closeness Scoring

**Script:** `{user}/score_comms_closeness.py`
**Depends on:** Stage 9
**Cost:** ~$0.50 (GPT-5 mini)
**Time:** 5 minutes

AI scores relationship closeness from communication patterns.

**What it does:**
- GPT-5 mini reads `comms_summary` and scores closeness + momentum
- Channel signal hierarchy: Phone > SMS > Calendar > 1:1 Email > LinkedIn DM > Group Email
- Produces: `comms_closeness` (distant/acquaintance/warm/close/inner_circle), `comms_momentum` (dormant/cooling/stable/warming/accelerating), `comms_reasoning` (text)
- Purely behavioral — no anchor profile needed

**Adaptation checklist:**
- [ ] Update table name
- [ ] Update user name in system prompt labels
- [ ] Adjust channel hierarchy if some channels are missing (e.g., no call logs)

**Verification:**
```sql
SELECT comms_closeness, count(*) FROM {user}_contacts WHERE comms_closeness IS NOT NULL GROUP BY comms_closeness;
```

**Reference:** `scripts/intelligence/sally/score_comms_closeness.py` (503 lines)

---

### Stage 11: Familiarity Backfill

**Script:** `{user}/backfill_familiarity.py`
**Depends on:** Stages 3, 9
**Cost:** $0
**Time:** 2 minutes

Heuristic familiarity rating (0-4) from comms density. User can manually override later.

**Logic:**
| Rating | Criteria |
|--------|----------|
| 0 | No comms data |
| 1 | Email or calendar only |
| 2 | Has SMS conversations |
| 3 | High SMS (>50 messages) or multi-channel |
| 4 | Very high SMS (>200) + calendar meetings |

**Adaptation checklist:**
- [ ] Update table names
- [ ] Adjust thresholds if appropriate for the user's communication patterns

**Reference:** `scripts/intelligence/sally/backfill_familiarity.py` (190 lines)

---

### Stage 12: Ask-Readiness Scoring

**Script:** `{user}/score_ask_readiness.py`
**Depends on:** Stages 8, 9, 10, 11
**Cost:** ~$3.40 for 850 contacts (GPT-5 mini)
**Time:** 10 minutes

Holistic donor readiness assessment using donor psychology framework.

**What it does:**
- GPT-5 mini evaluates each contact across: relationship strength, giving capacity, mission alignment, timing signals
- Uses Granovetter framework and 2x2 relationship mapping
- Produces: `ask_readiness` JSONB with tier (ready_now/cultivate_first/long_term/not_a_fit), score (0-100), reasoning
- Goal: `outdoorithm_fundraising`

**Adaptation checklist:**
- [ ] **CRITICAL:** Replace ALL user name references in the ~280-line system prompt
- [ ] Update table name
- [ ] Adjust `SELECT_COLS` for columns available in `{user}_contacts`
- [ ] Remove references to columns that don't exist (e.g., `known_donor`, `outdoor_environmental_affinity` if not applicable)
- [ ] Update goal context if the fundraising campaign differs

**Verification:**
```sql
SELECT
  ask_readiness->'outdoorithm_fundraising'->>'tier' as tier,
  count(*)
FROM {user}_contacts
WHERE ask_readiness IS NOT NULL
GROUP BY tier;
```

**Expected distribution:** ~5% ready_now, ~65% cultivate_first, ~25% long_term, ~5% not_a_fit

**Reference:** `scripts/intelligence/sally/score_ask_readiness.py` (1,139 lines)

---

### Stage 13: Campaign Scaffolding

**Script:** `{user}/scaffold_campaign.py`
**Depends on:** Stage 12
**Cost:** ~$0.50 (GPT-5 mini)
**Time:** 5 minutes

Assigns campaign personas, lists, and capacity tiers.

**What it does:**
- GPT-5 mini reads full contact context and assigns: campaign list (A/B/C/D), persona, capacity tier
- List A: personal 1:1 outreach (inner circle, high capacity)
- Lists B-D: templated campaign emails by tier
- Writes to `{user}_contacts.campaign_2026` JSONB

**Adaptation checklist:**
- [ ] Update table name
- [ ] Replace user name in system prompt
- [ ] Set `{USER}_TIER_1_NAMES` — inner circle contacts (must be manually identified by the user)
- [ ] Update user bio section
- [ ] Update voice patterns section (placeholder until persona doc is created)

**Reference:** `scripts/intelligence/sally/scaffold_campaign.py` (1,176 lines)

---

### Stage 14: Create Email Persona

**File:** `docs/{User}/{USER}_EMAIL_PERSONA.md`
**Depends on:** LinkedIn posts or email samples
**Cost:** $0 (manual analysis)
**Time:** 30-60 minutes

Analyze the user's writing to build a voice guide for AI-generated outreach.

**Structure (from Sally's persona doc):**
1. Voice overview (3 primary modes)
2. Signature patterns (sentence structure, openers, closers)
3. Key phrases and transitions
4. Tone and register
5. Topics and themes
6. How they address people
7. Em dash / punctuation style
8. Comparison to Justin's voice
9. Representative snippets (10+ examples)
10. Quick reference checklist (15 points)
11. Calibration notes for email vs LinkedIn vs SMS

**Sources to analyze:**
- LinkedIn posts (primary — public, easiest to access)
- Email threads (once gathered in Stage 5)
- SMS conversations (for casual register)

**Reference:** `docs/Sally/SALLY_EMAIL_PERSONA.md`, `docs/Justin/JUSTIN_EMAIL_PERSONA.md`

---

### Stage 15: Write Campaign Copy

**Script:** `{user}/write_campaign_copy.py`
**Depends on:** Stages 13, 14
**Cost:** ~$0.50 (GPT-5 mini for Lists B-D)
**Time:** 5 minutes

Generates templated campaign emails for Lists B-D contacts.

**What it does:**
- Reads contacts with `campaign_2026` scaffold and `campaign_list IN (B, C, D)`
- Generates per-contact: pre_email_note, text_followup_opener, text_followup_milestone, thank_you_message, email_sequence (3 emails)
- Uses the user's voice patterns from persona doc

**Adaptation checklist:**
- [ ] Update table name
- [ ] Update voice patterns in system prompt from persona doc
- [ ] Replace user name references throughout

**Reference:** `scripts/intelligence/sally/write_campaign_copy.py` (826 lines)

---

### Stage 16: Write Personal Outreach (List A)

**Script:** `{user}/write_outreach.py`
**Depends on:** Stages 13, 14
**Cost:** ~$2-5 (Claude Opus 4.6 for high-quality personal messages)
**Time:** 15 minutes

Generates deeply personal 1:1 messages for List A (inner circle) contacts.

**What it does:**
- Claude Opus 4.6 writes individual messages using the user's authentic voice
- Low concurrency: 3 workers (quality over speed)
- Each message references specific shared history, connection points
- Writes to `{user}_contacts.campaign_2026.personal_outreach`

**Adaptation checklist:**
- [ ] Update table name
- [ ] **CRITICAL:** Rewrite system prompt for user's voice (openers, closers, tone, story bank)
- [ ] Update story bank with user-specific anecdotes
- [ ] Update bio section
- [ ] Adjust message length if the user writes shorter/longer

**Reference:** `scripts/intelligence/sally/write_outreach.py` (986 lines)

---

### Stage 17: Cross-Reference Networks

**Script:** `{user}/cross_reference.py`
**Depends on:** Stage 2
**Cost:** $0
**Time:** 1 minute

Matches the user's contacts against Justin's network by LinkedIn URL.

**What it does:**
- Normalizes LinkedIn URLs on both sides
- Sets `justin_contact_id` FK for shared connections
- Prints overlap stats and top shared contacts by ask-readiness score

**Adaptation checklist:**
- [ ] Update table name

**Verification:**
```sql
SELECT count(*) FROM {user}_contacts WHERE justin_contact_id IS NOT NULL;
```

**Reference:** `scripts/intelligence/sally/cross_reference.py` (188 lines)

---

### Stage 18: API Routes and UI Pages

**Files:**
- `job-matcher-ai/app/api/network-intel/{user}/ask-readiness/route.ts`
- `job-matcher-ai/app/api/network-intel/{user}/campaign/route.ts`
- `job-matcher-ai/app/tools/{user}-ask-readiness/page.tsx`
- `job-matcher-ai/app/tools/{user}-campaign/page.tsx`

**Depends on:** Stage 1
**Cost:** $0
**Time:** 10 minutes

Clone Justin's existing routes and pages, change table name and headers.

**Adaptation checklist:**
- [ ] API routes: change `from('contacts')` to `from('{user}_contacts')`
- [ ] API routes: adjust `SELECT_COLS` for columns that exist in `{user}_contacts`
- [ ] UI pages: update header text to `"{User}'s Network"`
- [ ] UI pages: update API endpoint paths
- [ ] UI pages: update CSV export filenames
- [ ] UI pages: update component names to avoid conflicts

**Reference:** `job-matcher-ai/app/api/network-intel/sally/`, `job-matcher-ai/app/tools/sally-ask-readiness/`, `job-matcher-ai/app/tools/sally-campaign/`

---

## Execution Order Summary

```
Stage 1:  Create DB tables                    [$0, 1 min]
Stage 2:  Import LinkedIn CSV                 [$0, 1 min]        ← depends on 1
Stage 3:  Import SMS (optional)               [$0, 2 min]        ← depends on 2
Stage 4:  Set up Google OAuth                 [$0, 5-10 min]     ← needs user interaction
Stage 5:  Gather Gmail                        [$0, 30-60 min]    ← depends on 2, 4
Stage 6:  Gather Calendar                     [$0, 10-20 min]    ← depends on 2, 4
Stage 7:  Apify LinkedIn enrichment           [~$3-4, 30-60 min] ← depends on 2
Stage 8:  LLM tagging                         [~$1.70, 10 min]   ← depends on 7
Stage 9:  Rebuild comms summary               [$0, 2 min]        ← depends on 3, 5, 6
Stage 10: Score comms closeness               [~$0.50, 5 min]    ← depends on 9
Stage 11: Backfill familiarity                [$0, 2 min]        ← depends on 3, 9
Stage 12: Score ask readiness                 [~$3.40, 10 min]   ← depends on 8, 9, 10, 11
Stage 13: Scaffold campaign                   [~$0.50, 5 min]    ← depends on 12
Stage 14: Create email persona (manual)       [$0, 30-60 min]    ← needs writing samples
Stage 15: Write campaign copy (Lists B-D)     [~$0.50, 5 min]    ← depends on 13, 14
Stage 16: Write personal outreach (List A)    [~$2-5, 15 min]    ← depends on 13, 14
Stage 17: Cross-reference networks            [$0, 1 min]        ← depends on 2
Stage 18: API routes + UI pages               [$0, 10 min]       ← depends on 1
```

**Parallel opportunities:**
- Stages 3, 4, 7, 17, 18 can all run in parallel after Stage 2
- Stages 5 and 6 can run in parallel after Stage 4
- Stages 15 and 16 can run in parallel after Stages 13+14

**Total estimated cost:** ~$12-16 per user
**Total estimated time:** 3-5 hours (mostly waiting on Apify and Gmail scanning)

---

## Cost Breakdown

| Service | Usage | Cost |
|---------|-------|------|
| Apify (LinkedIn enrichment) | ~850 profiles x $0.004 | ~$3.40 |
| OpenAI GPT-5 mini (tagging) | ~850 contacts x 150 workers | ~$1.70 |
| OpenAI GPT-5 mini (comms closeness) | ~300 contacts with comms | ~$0.50 |
| OpenAI GPT-5 mini (ask readiness) | ~850 contacts | ~$3.40 |
| OpenAI GPT-5 mini (scaffold + copy) | ~200 campaign contacts | ~$1.00 |
| Anthropic Claude Opus 4.6 (List A outreach) | ~20-50 personal messages | ~$2-5 |
| **Total** | | **~$12-16** |

---

## Common Issues and Solutions

### Supabase

- **Pagination:** Use `.range(offset, offset + page_size - 1)` for >1000 rows
- **JSONB null bytes:** Strip with `_strip_null_bytes()` before saving — PostgreSQL rejects `\x00` in JSONB
- **Env var names:** `SUPABASE_SERVICE_KEY` (Sally scripts), `SUPABASE_KEY` (some older Justin scripts)

### GPT-5 mini

- Does NOT support `temperature=0` — use default only
- Structured output: `openai.responses.parse(model="gpt-5-mini", instructions=..., input=..., text_format=PydanticModel)`
- Env var: `OPENAI_APIKEY` (no underscore before KEY)
- Optimal workers: 150 (yields ~9,000 RPM within Tier 5 10,000 RPM limit)

### Google OAuth

- Setup uses port 8080 (not 8000) to avoid conflict with Google Workspace MCP servers
- If `invalid_grant` error: refresh token was revoked, need to re-run OAuth flow
- Kill stale processes before auth: `ps aux | grep workspace-mcp | grep -v grep`

### Apify

- Actor: `harvestapi/linkedin-profile-scraper` (~$0.004/profile)
- Max concurrent runs: 32 (Starter plan)
- URL normalization is critical: `urllib.parse.unquote()` + `www.linkedin.com` prefix
- Some profiles are private/restricted — these will have partial data

### Name Matching (SMS)

- Exact first+last name match first (high confidence)
- Fuzzy SequenceMatcher >= 0.85 second pass (medium confidence)
- Common mismatches: nicknames ("Mom"), first-name-only, hyphenated names
- Unmatched entries are expected — many SMS contacts aren't on LinkedIn

---

## Quick-Start Checklist

For adding a new user (replace `{user}` with lowercase first name):

- [ ] Get LinkedIn connections CSV export
- [ ] Get SMS backup (optional, parse with sync_phone_backup.py pattern)
- [ ] Set up Google Cloud OAuth client IDs for each Google account
- [ ] Create `docs/{User}/` directory for persona docs and input files
- [ ] Create `docs/credentials/{User}/` for OAuth client secrets
- [ ] Run migration to create `{user}_` prefixed tables
- [ ] Copy `scripts/intelligence/sally/` to `scripts/intelligence/{user}/`
- [ ] Global find-replace in all scripts: `sally_contacts` → `{user}_contacts`, `sally_contact_` → `{user}_contact_`, `Sally` → `{User}`, `SALLY` → `{USER}`
- [ ] Update anchor profile with user's career timeline
- [ ] Update `{USER}_EMAILS` set in gather scripts
- [ ] Update account lists in gather_comms.py, gather_calendar.py, setup_oauth.py
- [ ] Run stages 1-3 (tables, LinkedIn import, SMS import)
- [ ] Run stage 4 interactively (OAuth setup — needs browser)
- [ ] Run stages 5-7 in parallel (Gmail, Calendar, Apify)
- [ ] Run stages 8-12 sequentially (tagging → comms → ask readiness → campaign)
- [ ] Create email persona doc (stage 14)
- [ ] Run stages 15-16 (campaign copy + personal outreach)
- [ ] Run stage 17-18 (cross-reference + UI)
- [ ] Verify: visit `/tools/{user}-ask-readiness` and `/tools/{user}-campaign`
