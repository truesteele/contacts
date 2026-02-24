# Project: Come Alive 2026 — Campaign Execution Pipeline

## Overview

Build the full campaign data pipeline for Outdoorithm Collective's Come Alive 2026 fundraising campaign. Three Python scripts scaffold, write, and store campaign-ready copy for ~200 contacts using GPT-5 mini (scaffolding + campaign copy) and Claude Opus 4.6 (personal outreach). All output is stored in a `campaign_2026` JSONB column on the Supabase contacts table for frontend display and editing.

## Technical Context

- **Tech Stack:** Python 3.12, OpenAI API (GPT-5 mini), Anthropic API (Claude Opus 4.6), Supabase (PostgreSQL), psycopg2
- **Python venv:** `.venv/` (arm64) — activate with `source .venv/bin/activate`
- **Existing patterns:** `scripts/intelligence/score_ask_readiness.py` is THE model — Pydantic schemas, `openai.responses.parse()`, `build_contact_context()`, ThreadPoolExecutor, Supabase pagination with `.range()`, `_strip_null_bytes()` for JSONB
- **Env vars:** `OPENAI_APIKEY` (no underscore before KEY), `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_DB_PASSWORD`
- **DB connection:** Supabase REST API via `supabase-py` for reads/writes. Direct psycopg2 via `db.ypqsrejrsocebnldicke.supabase.co:5432` if needed.
- **GPT-5 mini:** Does NOT support temperature=0. Use default only.
- **OpenAI structured output:** `openai.responses.parse(model="gpt-5-mini", instructions=SYSTEM_PROMPT, input=context, text_format=PydanticModel)`
- **Anthropic SDK:** Needs `pip install anthropic` first (US-001)
- **Workers:** 150 for GPT-5 mini, 3-5 for Opus (quality over speed)
- **Strategy docs (READ THESE for system prompts):**
  - `docs/Outdoorithm/DONOR_SEGMENTATION.md` — Personas, execution matrix, motivation flags, capacity tiers
  - `docs/Outdoorithm/COME_ALIVE_2026_Campaign.md` — Story bank, email templates, outreach tiers, timeline
  - `docs/Outdoorithm/OC_FUNDRAISING_PLAYBOOK.md` — Donor psychology, campaign methodology

## Contact Selection Criteria

The campaign universe is ~200 contacts from the `ask_readiness` JSONB column:

```sql
-- List A-B: ready_now with addressable approach
WHERE ask_readiness->'outdoorithm_fundraising'->>'tier' = 'ready_now'
  AND ask_readiness->'outdoorithm_fundraising'->>'recommended_approach' IN ('personal_email', 'in_person', 'text_message')

-- List C: top cultivate_first
WHERE ask_readiness->'outdoorithm_fundraising'->>'tier' = 'cultivate_first'
  AND CAST(ask_readiness->'outdoorithm_fundraising'->>'score' AS int) >= 76
  AND ask_readiness->'outdoorithm_fundraising'->>'recommended_approach' IN ('personal_email', 'in_person', 'text_message')

-- List D: extended cultivate_first
WHERE ask_readiness->'outdoorithm_fundraising'->>'tier' = 'cultivate_first'
  AND CAST(ask_readiness->'outdoorithm_fundraising'->>'score' AS int) BETWEEN 60 AND 75
  AND ask_readiness->'outdoorithm_fundraising'->>'recommended_approach' IN ('personal_email', 'in_person', 'text_message')
```

## Output Schema: campaign_2026 JSONB Column

```json
{
  "scaffold": {
    "persona": "impact_professional",
    "persona_confidence": 82,
    "persona_reasoning": "...",
    "campaign_list": "B",
    "capacity_tier": "mid",
    "primary_ask_amount": 2500,
    "motivation_flags": ["peer_identity", "mission_alignment"],
    "primary_motivation": "peer_identity",
    "lifecycle_stage": "new",
    "lead_story": "valencia",
    "story_reasoning": "...",
    "opener_insert": "...",
    "personalization_sentence": "...",
    "thank_you_variant": "...",
    "text_followup": "..."
  },
  "personal_outreach": {
    "subject_line": "...",
    "message_body": "...",
    "channel": "email",
    "follow_up_text": "...",
    "thank_you_message": "...",
    "internal_notes": "..."
  },
  "campaign_copy": {
    "pre_email_note": null,
    "text_followup_opener": "...",
    "text_followup_milestone": "...",
    "thank_you_message": "...",
    "thank_you_channel": "text",
    "email_sequence": [1, 2, 3]
  },
  "scaffolded_at": "2026-02-23T...",
  "outreach_written_at": "2026-02-23T...",
  "copy_written_at": "2026-02-23T..."
}
```

---

## User Stories

### US-001: Setup — Add campaign_2026 Column and Install Anthropic SDK
**Priority:** 1
**Status:** [x] Complete

**Description:**
Add the `campaign_2026` JSONB column to the contacts table and install the Anthropic Python SDK.

**Acceptance Criteria:**
- [x] Run SQL: `ALTER TABLE contacts ADD COLUMN IF NOT EXISTS campaign_2026 JSONB;` via the `supabase-contacts` MCP server's `execute_sql` tool
- [x] Verify column exists: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'contacts' AND column_name = 'campaign_2026';`
- [x] Run: `source .venv/bin/activate && pip install anthropic`
- [x] Verify: `source .venv/bin/activate && python -c "import anthropic; print(anthropic.__version__)"`
- [x] Verify OpenAI still works: `source .venv/bin/activate && python -c "import openai; print(openai.__version__)"`

**Notes:**
- Use `supabase-contacts` MCP server (NOT `supabase_crm`) for the SQL
- The contacts table already has ~130 columns including `ask_readiness`, `oc_engagement`, `communication_history`, etc.

---

### US-002: Create scaffold_campaign.py
**Priority:** 2
**Status:** [x] Complete

**Description:**
Create the campaign scaffolding script that uses GPT-5 mini structured output to assign personas, capacity tiers, motivation flags, lifecycle stages, stories, and copy building blocks to each campaign contact. Follow the exact pattern of `score_ask_readiness.py`.

**Acceptance Criteria:**
- [x] Script created at `scripts/intelligence/scaffold_campaign.py`
- [x] Pydantic schema `CampaignScaffold` with all fields: persona (believer/impact_professional/network_peer), persona_confidence (0-100), persona_reasoning, campaign_list (A/B/C/D), capacity_tier (leadership/major/mid/base/community), primary_ask_amount (250/500/1000/2500/5000/10000), motivation_flags (list), primary_motivation, lifecycle_stage (new/prior_donor/lapsed), lead_story (valencia/carl/8_year_old/michelle_latting/joy/aftan/dorian/sally_disney/skip), story_reasoning, opener_insert, personalization_sentence, thank_you_variant, text_followup
- [x] System prompt includes: full persona decision tree from DONOR_SEGMENTATION.md, execution matrix (Persona x Lifecycle), motivation flags definitions, capacity tier mapping, story bank from COME_ALIVE_2026_Campaign.md, Justin's profile context
- [x] Contact context builder reuses patterns from `score_ask_readiness.py` `build_contact_context()`: ask_readiness fields, oc_engagement, communication_history, employment, education, ai_tags, real estate, FEC, comms closeness
- [x] Contact selection: ready_now (addressable) + cultivate_first score>=76 (addressable) + cultivate_first score 60-75 (addressable)
- [x] Uses `openai.responses.parse(model="gpt-5-mini", ...)` with `text_format=CampaignScaffold`
- [x] ThreadPoolExecutor with default 150 workers, configurable via `--workers`
- [x] Saves to `campaign_2026` JSONB column as `{"scaffold": {...}, "scaffolded_at": "..."}` — preserves existing `personal_outreach` and `campaign_copy` keys if present
- [x] Includes `_strip_null_bytes()` for PostgreSQL JSONB compatibility
- [x] CLI args: `--test` (1 contact), `--batch N`, `--workers N`, `--force` (re-scaffold already scaffolded), `--contact-id ID`
- [x] Pagination via `.range()` for >1000 rows
- [x] Error handling with retries for rate limits
- [x] Script runs without errors: `source .venv/bin/activate && python scripts/intelligence/scaffold_campaign.py --test`

**Notes:**
- READ `docs/Outdoorithm/DONOR_SEGMENTATION.md` carefully for the persona decision tree, execution matrix tables, and motivation flag definitions — embed the FULL content in the system prompt
- READ `docs/Outdoorithm/COME_ALIVE_2026_Campaign.md` for the story bank — embed story descriptions so GPT can match stories to contacts
- READ `scripts/intelligence/score_ask_readiness.py` for code patterns — this is the template
- The system prompt is the most critical part of this script. It needs to be comprehensive. Don't skimp on token count.
- GPT-5 mini does NOT support temperature=0. Use default only.
- Env var is `OPENAI_APIKEY` (no underscore before KEY)

---

### US-003: Run scaffold_campaign.py and Verify Output
**Priority:** 3
**Status:** [x] Complete

**Description:**
Run the scaffold on all ~200 campaign contacts and verify the output quality.

**Acceptance Criteria:**
- [x] Run: `source .venv/bin/activate && python scripts/intelligence/scaffold_campaign.py`
- [x] Script completes without errors
- [x] Print count of contacts scaffolded
- [x] Query Supabase for distribution summary: count by persona, campaign_list, capacity_tier, lifecycle_stage
- [x] Query 5 sample contacts and verify:
  - Persona assignment makes sense given their title/company/relationship
  - Capacity tier aligns with their suggested_ask_range
  - Lifecycle stage matches oc_engagement donor status (if oc_engagement exists)
  - Campaign list assignment is correct for their ask_readiness tier/score
  - Lead story matches primary motivation flag
- [x] Print the summary table to stdout

**Notes:**
- If the script fails partway through, check for rate limit errors and adjust workers
- Expected runtime: ~2-5 minutes with 150 workers
- Expected cost: ~$2-3 on OpenAI

---

### US-004: Create write_personal_outreach.py (Opus 4.6)
**Priority:** 4
**Status:** [x] Complete

**Description:**
Create the personal outreach writer script that uses Claude Opus 4.6 to write high-quality, voice-authentic personal messages for List A contacts (~20 inner circle). These are the highest-stakes messages in the campaign.

**Acceptance Criteria:**
- [x] Script created at `scripts/intelligence/write_personal_outreach.py`
- [x] Uses `anthropic` SDK: `client = anthropic.Anthropic()` (reads ANTHROPIC_API_KEY from env)
- [x] Output schema per contact (use JSON mode or structured extraction): subject_line (str), message_body (str, 100-200 words), channel (text/email), follow_up_text (str), thank_you_message (str), internal_notes (str)
- [x] System prompt includes:
  - Justin's voice patterns: direct, punchy, sentence fragments for emphasis, em dashes, conversational, "this keeps happening" transitions, "quick thing" openers. Reads like a text from a friend, not a fundraiser.
  - Full personal outreach template from COME_ALIVE_2026_Campaign.md
  - Believer + Impact Professional persona scaffolds from DONOR_SEGMENTATION.md
  - Donor psychology framework (identity circuits, warm glow, matching)
  - Explicit instruction: "Sound like Justin texting or emailing a friend. NOT a development officer. NOT a nonprofit pitch."
  - Story bank with when to use each story
- [x] Per-contact context includes:
  - All scaffold data (persona, list, capacity, motivation, story, opener_insert, etc.)
  - Full communication_history (recent thread subjects, last exchange date)
  - LinkedIn headline, summary, current title/company
  - Shared institutions (education, employers) and overlap summary
  - receiver_frame and personalization_angle from ask_readiness
  - OC engagement details (trips attended, roles, donation history)
  - The specific ask amount and lead story from scaffold
- [x] Selects List A contacts: `WHERE campaign_2026->'scaffold'->>'campaign_list' = 'A'`
- [x] Low concurrency: 3-5 workers (quality over speed)
- [x] Saves to `campaign_2026` JSONB as `{"personal_outreach": {...}, "outreach_written_at": "..."}` — preserves existing scaffold data
- [x] CLI args: `--test` (1 contact), `--force`, `--contact-id ID`, `--workers N` (default 3)
- [x] Error handling for Anthropic API errors
- [x] Script runs without errors: `source .venv/bin/activate && python scripts/intelligence/write_personal_outreach.py --test`

**Notes:**
- Use `claude-opus-4-6` as the model name for Anthropic API
- READ the personal outreach template in COME_ALIVE_2026_Campaign.md (lines 130-155) — this is the voice target
- READ the Tier 1 outreach list in COME_ALIVE_2026_Campaign.md (lines 163-211) — these are the contacts
- The messages must sound like they came from Justin's phone. If they sound like they came from a CRM, they've failed.
- The Anthropic SDK uses `client.messages.create()` — NOT `responses.parse()` like OpenAI
- For structured output with Anthropic, use the tool_use pattern or parse JSON from the response
- Each message should reference specific shared history from communication_history if available

---

### US-005: Run write_personal_outreach.py and Verify Output
**Priority:** 5
**Status:** [x] Complete

**Description:**
Run the personal outreach writer on List A contacts and verify the quality of each message.

**Acceptance Criteria:**
- [x] Run: `source .venv/bin/activate && python scripts/intelligence/write_personal_outreach.py`
- [x] Script completes without errors
- [x] Print count of messages written
- [x] Print ALL messages (all ~20) to stdout in a readable format: contact name, channel, subject line, message body, follow-up text, internal notes
- [x] Verify at least 3 messages manually:
  - Does it sound like Justin? (casual, direct, fragments, not polished/corporate)
  - Is the ask amount appropriate for their capacity tier?
  - Does the story match their motivation flag?
  - Are shared history references accurate (from comms data)?
  - Is it 100-200 words?

**Notes:**
- Expected runtime: ~5-10 minutes with 3 workers (20 contacts)
- Expected cost: ~$2-5 on Anthropic
- This is the most important verification step — these messages are the campaign's highest-leverage output

---

### US-006: Create write_campaign_copy.py (GPT-5 mini)
**Priority:** 6
**Status:** [x] Complete

**Description:**
Create the campaign copy variant writer for Lists B-D contacts (~175). Generates personalized text follow-ups, thank-you messages, and pre-email notes using GPT-5 mini structured output.

**Acceptance Criteria:**
- [x] Script created at `scripts/intelligence/write_campaign_copy.py`
- [x] Pydantic schema `CampaignCopy` with fields: pre_email_note (Optional[str], for prior_donor/lapsed only), text_followup_opener (str, Days 2-5), text_followup_milestone (str, Days 10-14), thank_you_message (str), thank_you_channel (text/email), email_sequence (list[int])
- [x] System prompt includes:
  - Justin's voice patterns (same as outreach but adapted for shorter messages)
  - Thank-you frame matrix from DONOR_SEGMENTATION.md (Persona x Motivation Flag)
  - Follow-up timing from execution matrix
  - Identity-affirming language patterns from donor psychology
  - Text message conventions (shorter, more casual than email)
- [x] Per-contact context includes: scaffold data, communication_history summary, current title/company, receiver_frame, personalization_angle
- [x] Selects Lists B-D contacts: `WHERE campaign_2026->'scaffold'->>'campaign_list' IN ('B', 'C', 'D')`
- [x] Uses `openai.responses.parse(model="gpt-5-mini", ...)` with `text_format=CampaignCopy`
- [x] ThreadPoolExecutor with default 150 workers
- [x] Saves to `campaign_2026` JSONB as `{"campaign_copy": {...}, "copy_written_at": "..."}` — preserves existing scaffold and outreach data
- [x] CLI args: `--test`, `--batch N`, `--workers N`, `--force`, `--contact-id ID`
- [x] Script runs without errors: `source .venv/bin/activate && python scripts/intelligence/write_campaign_copy.py --test`

**Notes:**
- Follow `score_ask_readiness.py` patterns for batch processing
- The thank-you messages should use identity-affirming language: "You're the kind of person who shows up" not "Thank you for your generous gift"
- Pre-email notes are ONLY for prior_donor and lapsed lifecycle stages
- email_sequence should be [1, 2, 3] for most contacts; prior donors may skip Email 2 or 3

---

### US-007: Run write_campaign_copy.py and Verify Output
**Priority:** 7
**Status:** [x] Complete

**Description:**
Run the campaign copy writer on Lists B-D contacts and verify the output quality.

**Acceptance Criteria:**
- [x] Run: `source .venv/bin/activate && python scripts/intelligence/write_campaign_copy.py`
- [x] Script completes without errors
- [x] Print count of contacts with copy written
- [x] Spot-check 10 contacts across different personas and motivation flags:
  - Is the thank-you identity-affirming (not generic)?
  - Do text follow-ups sound natural and brief?
  - Are pre-email notes present only for prior/lapsed donors?
  - Does the email_sequence make sense for their lifecycle?
- [x] Print distribution: count by persona, capacity tier, lifecycle

**Notes:**
- Expected runtime: ~2-5 minutes with 150 workers
- Expected cost: ~$1-2 on OpenAI

---

### US-008: Create CAMPAIGN_EXECUTION_PLAN.md
**Priority:** 8
**Status:** [x] Complete

**Description:**
Create the master campaign execution document that ties everything together. Query Supabase for real data to populate all summary tables and counts.

**Acceptance Criteria:**
- [x] Doc created at `docs/Outdoorithm/CAMPAIGN_EXECUTION_PLAN.md`
- [x] Includes pipeline status: contacts scaffolded (count), personal outreach written (count), campaign copy written (count)
- [x] Includes master contact summary table: count by campaign_list x persona x capacity_tier
- [x] Includes List A personal outreach checklist: each contact's name, channel, ask amount, one-line note about the message
- [x] Includes day-by-day execution timeline:
  - Pre-campaign: personal outreach to List A (specific dates)
  - Day 1 (Feb 26): Email 1 to Lists A-D
  - Days 2-5: Text follow-ups (openers who didn't act)
  - Days 7-10: Email 2 to non-donors
  - Days 10-14: Text milestone update to non-donors
  - Days 14-21: Email 3 to non-donors (Joshua Tree countdown)
  - Post-gift: Thank-you within 24 hours
- [x] Includes email 1/2/3 audience rules (who gets each email)
- [x] Includes text follow-up triggers and timing
- [x] Includes thank-you workflow: persona x flag → which template
- [x] Includes post-campaign measurement plan (from playbook)
- [x] All data is queried from Supabase `campaign_2026` column — no hardcoded numbers
- [x] Doc is self-contained: Justin can follow it day-by-day without referencing other docs

**Notes:**
- Query the campaign_2026 column to get real counts and distributions
- Reference specific contact names for List A (these are already in the scaffold data)
- The timeline should use actual dates from COME_ALIVE_2026_Campaign.md
- This doc replaces the need for CSV exports — the data lives in Supabase, this doc is the execution guide
