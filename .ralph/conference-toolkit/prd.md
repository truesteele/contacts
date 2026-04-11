# Project: Conference Networking Toolkit — Generalization

## Overview
Refactor the TED 2026 lookbook pipeline into a reusable, config-driven conference networking toolkit. A single YAML config file per conference should parameterize: the GPT scoring prompt, HTML generator, Supabase population script, and Edge Function. The existing TED 2026 functionality must continue working identically after refactoring.

## Technical Context
- **Tech Stack:** Python 3.12 (scripts), Deno/TypeScript (Edge Function), static HTML/CSS/JS (lookbook), Supabase PostgreSQL + PostgREST
- **Existing code:** `scripts/intelligence/ted_*.py`, `supabase/functions/ted-enrich-contact/index.ts`
- **Conventions:** Scripts in `scripts/intelligence/`, Edge Functions in `supabase/functions/`, data in `/tmp/`, deploy artifacts in `docs/`
- **Python venv:** `/Users/Justin/Code/TrueSteele/contacts/.venv/` (has supabase, python-dotenv, pyyaml, openai, pydantic)
- **Key constraint:** Must NOT break the live TED 2026 lookbook at ted-outdoorithm.vercel.app
- **Key constraint:** No TypeScript type checking needed — HTML generator is Python, Edge Function is Deno (no npm project)

## User Stories

### US-001: Define conference config schema and create TED 2026 config
**Priority:** 1
**Status:** [x] Complete

**Description:**
Create the config schema (YAML) and extract all conference-specific + org-specific values from the existing TED scripts into a config file. This is the foundation everything else reads from.

**Acceptance Criteria:**
- [ ] Create `conferences/` directory at repo root
- [ ] Create `conferences/ted-2026/config.yaml` with all extracted values
- [ ] Config covers: conference metadata (name, slug, dates, venue, attendee_count, connect_url_template), organization (name, tagline, color_primary, color_accent, partnership_types with display labels), users (primary networker + support person with name, role, bio lines, linkedin), supabase settings (table name, edge_function name, project_url, anon_key), vercel deployment settings (deploy_dir, alias), and data file paths (warm_leads, triage_results, shortlist, deep_writeups module)
- [ ] Create `conferences/ted-2026/scoring_prompt.md` — extract the system prompt from `ted_triage_outdoorithm.py` into its own file (verbatim, no template variables yet — that's US-002)
- [ ] Verify: `python -c "import yaml; yaml.safe_load(open('conferences/ted-2026/config.yaml'))"` succeeds
- [ ] Commit with message: `feat: [US-001] Conference toolkit - Define config schema and TED 2026 config`

---

### US-002: Create config loader module with prompt templating
**Priority:** 2
**Status:** [x] Complete

**Description:**
Create a shared Python module that loads and validates a conference config, and supports Jinja2-style template variables in the scoring prompt file. This module will be imported by all other scripts.

**Acceptance Criteria:**
- [ ] Create `scripts/conference/` directory (new package, not inside `intelligence/`)
- [ ] Create `scripts/conference/__init__.py` (empty)
- [ ] Create `scripts/conference/config.py` with a `ConferenceConfig` dataclass/class that:
  - Loads YAML config from a path
  - Validates required fields exist (raise clear errors if missing)
  - Provides typed access to all config sections (conference, organization, users, supabase, vercel, data_paths)
  - Has a `load_scoring_prompt()` method that reads the prompt file and substitutes `{{org.name}}`, `{{org.tagline}}`, `{{users.primary.name}}`, `{{users.primary.bio}}`, `{{conference.name}}`, etc. using simple string `.replace()` (no Jinja2 dependency needed)
  - Has a `resolve_path(relative_path)` method that resolves paths relative to the config file's directory
- [ ] Update `conferences/ted-2026/scoring_prompt.md` to use `{{template_variables}}` for org name, mission description, user bio, campaign details, etc. The prompt should still read naturally.
- [ ] Write a quick smoke test: `python -c "from scripts.conference.config import ConferenceConfig; c = ConferenceConfig('conferences/ted-2026/config.yaml'); print(c.conference.name, c.load_scoring_prompt()[:100])"` — must print "TED 2026" and the start of the rendered prompt
- [ ] Commit with message: `feat: [US-002] Conference toolkit - Config loader with prompt templating`

---

### US-003: Refactor triage script to be config-driven
**Priority:** 3
**Status:** [x] Complete

**Description:**
Create a generic `scripts/conference/triage.py` that reads the conference config and runs GPT scoring. The existing `ted_triage_outdoorithm.py` should still work (don't delete it) but the new script should be the preferred path forward.

**Acceptance Criteria:**
- [ ] Create `scripts/conference/triage.py` that:
  - Accepts `--config conferences/ted-2026/config.yaml` as CLI argument
  - Loads attendee data from the config's `data_paths.warm_leads` path
  - Loads the scoring prompt via `config.load_scoring_prompt()`
  - Reads partnership types from config (not hardcoded)
  - Uses the same concurrent GPT-5 mini scoring pattern (ThreadPoolExecutor, structured output, retry) from `ted_triage_outdoorithm.py`
  - Saves results to the config's `data_paths.triage_results` path
  - Supports `--test` (process first 3 only) and `--workers N` flags
  - Uses field names from the input data as-is (no assumption about `ted_*` prefix — the config should specify the field mapping OR the script should auto-detect)
- [ ] Verify: `python scripts/conference/triage.py --config conferences/ted-2026/config.yaml --test` runs successfully and produces valid JSON output matching the existing format
- [ ] Do NOT delete `scripts/intelligence/ted_triage_outdoorithm.py` (keep for reference)
- [ ] Commit with message: `feat: [US-003] Conference toolkit - Config-driven triage script`

---

### US-004: Refactor populate script to be config-driven
**Priority:** 4
**Status:** [x] Complete

**Description:**
Create a generic `scripts/conference/populate.py` that reads the conference config and populates Supabase.

**Acceptance Criteria:**
- [ ] Create `scripts/conference/populate.py` that:
  - Accepts `--config conferences/ted-2026/config.yaml` as CLI argument
  - Reads data file paths from config
  - Reads Supabase table name from config
  - Joins warm_leads + triage_results + shortlist by the attendee ID field
  - Handles the user-specific columns (pinned, notes, reached_out, context) generically — config defines which user fields exist under `users.primary` and `users.support`
  - Upserts in batches of 500
  - Reports counts per tier and other summary stats
- [ ] Verify: `python scripts/conference/populate.py --config conferences/ted-2026/config.yaml --dry-run` shows what would be inserted without touching the DB
- [ ] Do NOT delete `scripts/intelligence/ted_populate_attendees.py`
- [ ] Commit with message: `feat: [US-004] Conference toolkit - Config-driven populate script`

---

### US-005: Refactor HTML generator to be config-driven
**Priority:** 5
**Status:** [x] Complete

**Description:**
Create a generic `scripts/conference/generate_lookbook.py` that reads the conference config and produces the HTML lookbook. This is the largest refactoring task — the generator has ~1400 lines with ~15 hardcoded conference/org-specific strings.

**Acceptance Criteria:**
- [ ] Create `scripts/conference/generate_lookbook.py` that:
  - Accepts `--config conferences/ted-2026/config.yaml` as CLI argument
  - Reads ALL conference-specific strings from config: title, dates, venue, subtitle, attendee count, color scheme, section labels
  - Reads Supabase project URL, anon key, table name, and edge function name from config
  - Reads the deep writeups module path from config and dynamically imports it
  - Generates the same HTML structure: header, search bar, Sally's Picks (renamed to `{user.primary.name}'s Picks`), tier sections, quick reference table
  - All JavaScript references to table names, edge function URLs, and user labels come from config values embedded in the generated HTML
  - Uses the partnership type display labels from config for badges
  - Output path comes from config's `vercel.deploy_dir` + conference name
- [ ] Verify: Running `python scripts/conference/generate_lookbook.py --config conferences/ted-2026/config.yaml` produces HTML that is functionally equivalent to the current `docs/TED2026/TED_2026_Outdoorithm_Networking_Brief.html` (same structure, same data, same JS behavior — may differ in whitespace/formatting)
- [ ] The generated HTML should work with the existing Supabase table and Edge Function
- [ ] Do NOT delete `scripts/intelligence/ted_generate_lookbook.py`
- [ ] Commit with message: `feat: [US-005] Conference toolkit - Config-driven HTML generator`

---

### US-006: Refactor Edge Function to read scoring prompt from config table
**Priority:** 6
**Status:** [x] Complete

**Description:**
Make the Edge Function generic by reading its scoring system prompt from a Supabase `conference_config` table instead of hardcoding it. This way one Edge Function serves all conferences.

**Acceptance Criteria:**
- [ ] Create a `conference_config` table in Supabase via SQL (use the supabase-contacts MCP `execute_sql`):
  ```sql
  CREATE TABLE conference_config (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    scoring_prompt TEXT NOT NULL,
    partnership_types JSONB NOT NULL,
    primary_user_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
  );
  ```
  Enable RLS with permissive anon read policy. Service role for writes.
- [ ] Insert the TED 2026 config row: slug='ted-2026', scoring prompt from the existing Edge Function, partnership types array, primary_user_name='Sally', table_name='ted_attendees'
- [ ] Create `supabase/functions/conference-enrich/index.ts` — a copy of `ted-enrich-contact/index.ts` that:
  - Accepts `{ linkedin_url: string, conference_slug: string }` as input
  - Reads the scoring prompt and partnership types from `conference_config` where `slug = conference_slug`
  - Reads the target table name from `conference_config` for the insert
  - Uses the same Apify + GPT scoring pipeline
  - Returns the same response format
- [ ] Deploy: `SUPABASE_ACCESS_TOKEN=$SB_PAT supabase functions deploy conference-enrich --project-ref ypqsrejrsocebnldicke --no-verify-jwt --use-api`
- [ ] Set same secrets as ted-enrich-contact (APIFY_API_KEY, OPENAI_APIKEY) — these should already be set project-wide
- [ ] Verify: `curl -X POST https://ypqsrejrsocebnldicke.supabase.co/functions/v1/conference-enrich -H "Authorization: Bearer <anon_key>" -H "Content-Type: application/json" -d '{"linkedin_url":"https://linkedin.com/in/justinrichardsteele","conference_slug":"ted-2026"}'` returns a valid scored response (use a known LinkedIn profile for testing)
- [ ] Do NOT delete the `ted-enrich-contact` function (keep for backward compatibility until the new lookbook is deployed)
- [ ] Commit with message: `feat: [US-006] Conference toolkit - Generic Edge Function with config table`

---

### US-007: Create CLI entry point and documentation
**Priority:** 7
**Status:** [x] Complete

**Description:**
Create a single CLI entry point that orchestrates the full pipeline, and document the toolkit for future use.

**Acceptance Criteria:**
- [ ] Create `scripts/conference/run.py` CLI that accepts:
  - `--config conferences/ted-2026/config.yaml` (required)
  - `--step triage|populate|generate|deploy|all` (required)
  - `--test` flag (passes through to triage)
  - `--workers N` flag (passes through to triage)
  - `--dry-run` flag (passes through to populate)
  - For `deploy` step: runs `npx vercel --prod --yes --scope true-steele` from the deploy dir, then aliases
  - For `all` step: runs triage → populate → generate → deploy in sequence
- [ ] Create `conferences/README.md` documenting:
  - How to create a new conference config (copy ted-2026 as template)
  - The full pipeline: data acquisition → config → triage → populate → generate → deploy
  - How to write a scoring prompt for a new organization
  - How to add deep writeups (optional)
  - Required secrets and environment variables
  - Example: "Setting up for Skoll World Forum 2026"
- [ ] Verify: `python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step generate` produces the lookbook HTML
- [ ] Commit with message: `feat: [US-007] Conference toolkit - CLI entry point and documentation`

---

### US-008: End-to-end validation — regenerate TED 2026 from new toolkit
**Priority:** 8
**Status:** [x] Complete

**Description:**
Validate the full toolkit by regenerating the TED 2026 lookbook from the new config-driven pipeline and deploying it. This proves the refactoring is complete and nothing broke.

**Acceptance Criteria:**
- [ ] Run `python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step generate`
- [ ] Diff the generated HTML against the current deployed version — should be functionally equivalent (same data, same JS behavior, same cards)
- [ ] Copy to deploy dir and deploy to Vercel: `python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step deploy`
- [ ] Verify ted-outdoorithm.vercel.app still works: search, Sally's Picks, outreach toggles, add new person
- [ ] Update the HTML generator in config to point to `conference-enrich` Edge Function (instead of `ted-enrich-contact`)
- [ ] Redeploy and verify "Add New Person" still works with the generic Edge Function
- [ ] Commit with message: `feat: [US-008] Conference toolkit - End-to-end validation with TED 2026`
