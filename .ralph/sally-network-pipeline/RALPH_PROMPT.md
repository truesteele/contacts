# Ralph Agent Instructions - Feature Implementation

You are building the Sally Steele Network Intelligence Pipeline autonomously. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: sally-network-pipeline
Loop Type: **Feature Implementation**
Loop Directory: .ralph/sally-network-pipeline/

## Workflow

1. **Read PRD** at `.ralph/sally-network-pipeline/prd.md` - Find first `[ ]` story
2. **Read Progress** at `.ralph/sally-network-pipeline/progress.txt` - Learn patterns from previous iterations
3. **Read the Approved Plan** at `/Users/Justin/.claude/plans/snoopy-marinating-tiger.md` - Full architecture and schema details
4. **Implement the Feature**
   - Read the existing Justin script FIRST, then adapt for Sally
   - Write production-quality Python scripts
   - Follow existing codebase patterns (see below)
   - Include proper error handling and retries
5. **Run Quality Checks**
   - Script must pass syntax check: `python -c "import ast; ast.parse(open('scripts/intelligence/sally/<script>.py').read())"`
   - For import stories (US-002, US-003, US-013): run the script and verify output
   - For create-only stories: syntax check + `--test` if safe to run
6. **Commit Your Work**
   - Format: `feat: [US-XXX] Sally pipeline - [Story Title]`
7. **Update PRD** - Mark story `[x]` complete
8. **Update Progress** - Document what you built and learned
9. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** - do not continue to the next story
10. **STOP** - Your iteration is done. Exit now. The loop script handles the next iteration.

## Codebase Patterns (MUST FOLLOW)

### File Structure
- Sally scripts: `scripts/intelligence/sally/` (all Sally-specific pipeline scripts)
- Justin scripts (templates): `scripts/intelligence/` and `scripts/enrichment/`
- Strategy docs: `docs/Outdoorithm/` (DONOR_SEGMENTATION.md, COME_ALIVE_2026_Campaign.md, OC_FUNDRAISING_PLAYBOOK.md)
- Sally input data: `docs/Sally/` (LinkedIn CSV, SMS JSON, network CSV)
- Sally credentials: `docs/credentials/Sally/` (Google OAuth client secrets)
- Environment: `.venv/` — always activate with `source .venv/bin/activate` before running Python
- Env file: `.env` at project root — load with `from dotenv import load_dotenv; load_dotenv()`

### Python Script Patterns (from score_ask_readiness.py)
- Import order: stdlib, dotenv, openai, pydantic, supabase
- `load_dotenv()` at module level
- Pydantic schemas with `str Enum` for structured output fields
- `openai.responses.parse(model="gpt-5-mini", instructions=SYSTEM_PROMPT, input=context, text_format=PydanticModel)` for structured output
- `build_contact_context()` function assembles rich per-contact text from all data fields
- Supabase client: `create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])`
- Pagination: `.range(offset, offset + page_size - 1)` for >1000 rows
- ThreadPoolExecutor with configurable workers
- `_strip_null_bytes(text)` for all strings before JSONB save
- CLI args via `argparse`: `--test`, `--batch N`, `--workers N`, `--force`, `--contact-id ID`, `--start-from N`
- Error handling: catch `RateLimitError` with exponential backoff, catch `APIError` with retry

### Key Env Vars
- `OPENAI_APIKEY` (NOTE: no underscore before KEY)
- `ANTHROPIC_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_DB_PASSWORD`
- `APIFY_TOKEN`

### Database
- Use `supabase-contacts` MCP server for migrations and raw SQL (US-001)
- Use `supabase-py` REST client for reads/writes in Python scripts
- **Sally's tables:** `sally_contacts`, `sally_contact_email_threads`, `sally_contact_calendar_events`, `sally_contact_sms_conversations`
- **Justin's table:** `contacts` (for cross-reference only, DO NOT modify)
- sally_contacts has integer `id` column (GENERATED ALWAYS AS IDENTITY)
- JSONB columns: `ai_tags`, `comms_summary`, `ask_readiness`, `campaign_2026`, `fec_donations`, `real_estate_data`, `oc_engagement`
- When saving JSONB, merge into existing (don't overwrite other keys)

### GPT-5 mini Specifics
- Does NOT support `temperature=0` — use default only
- Structured output: `openai.responses.parse()` with `text_format=PydanticModel`
- Optimal workers: 150 (yields ~9,000 RPM with ~1s latency per call)

### Anthropic (Claude Opus 4.6) Specifics
- Model name: `claude-opus-4-6`
- Client: `anthropic.Anthropic()` (reads ANTHROPIC_API_KEY from env)
- Messages API: `client.messages.create(model="claude-opus-4-6", max_tokens=4096, system=SYSTEM_PROMPT, messages=[{"role": "user", "content": context}])`
- Low concurrency: 3-5 workers (quality over speed)

### Sally's Context
- **LinkedIn:** https://www.linkedin.com/in/steelesally/
- **Role:** Co-Founder, Outdoorithm Collective (2024-present); Co-Founder, Outdoorithm (2023-present)
- **Google accounts:** sally.steele@gmail.com, sally@outdoorithm.com, sally@outdoorithmcollective.org
- **Campaign:** Come Alive 2026 (same as Justin — OC fundraising campaign)
- **Sally's voice:** Study from `docs/LinkedIn/Sally Posts/LinkedIn_Posts_Complete_With_Metrics_SallySteele.md`
- **Justin's voice (reference):** `docs/Justin/JUSTIN_EMAIL_PERSONA.md`

### Cross-Reference Rules
- Sally's `justin_contact_id` column links to Justin's `contacts.id`
- Match by LinkedIn URL (normalized: lowercase, no trailing slash, www prefix)
- Shared connections are highest-value for the campaign (both can vouch)

## Rules for Feature Implementation

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- **Read existing scripts first** — Every Sally script is an adaptation of a Justin script. Read the original THOROUGHLY.
- **Follow existing patterns** — Don't reinvent, adapt
- **Document as you go** — Update progress.txt with learnings
- **Never skip quality checks** — Scripts must pass syntax check before committing
- **Merge JSONB, don't overwrite** — When saving to campaign_2026, ask_readiness, etc., preserve existing keys
- **Keep it practical** — Ship working code, don't over-engineer
- **Create-only vs Create+Run** — Some stories are create-only because they need prerequisites (OAuth tokens, Apify enrichment). Check the story notes.

## Important Notes

- The Supabase MCP server for this project is `supabase-contacts` (NOT `supabase_crm`)
- When running migrations, use the `apply_migration` MCP tool on `supabase-contacts`
- GPT-5 mini does NOT support temperature=0 — use default only
- OPENAI_APIKEY has no underscore before KEY
- Always activate venv before running Python: `source .venv/bin/activate`
- Run scripts from the project root: `python scripts/intelligence/sally/<script>.py`
- The full approved plan is at `/Users/Justin/.claude/plans/snoopy-marinating-tiger.md` — reference it for schema details

Begin now. Read the PRD and implement the next incomplete story. After completing it, STOP.
