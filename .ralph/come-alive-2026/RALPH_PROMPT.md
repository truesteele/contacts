# Ralph Agent Instructions - Feature Implementation

You are building the Come Alive 2026 campaign data pipeline autonomously. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: come-alive-2026
Loop Type: **Feature Implementation**
Loop Directory: .ralph/come-alive-2026/

## Workflow

1. **Read PRD** at `.ralph/come-alive-2026/prd.md` - Find first `[ ]` story
2. **Read Progress** at `.ralph/come-alive-2026/progress.txt` - Learn patterns from previous iterations
3. **Implement the Feature**
   - Write production-quality Python scripts
   - Follow existing codebase patterns (see below)
   - Include proper error handling and retries
4. **Run Quality Checks**
   - Script must run without errors: `source .venv/bin/activate && python scripts/intelligence/<script>.py --test`
   - For run stories (US-003, US-005, US-007): run the full batch and verify output
5. **Commit Your Work**
   - Format: `feat: [US-XXX] - [Story Title]`
6. **Update PRD** - Mark story `[x]` complete
7. **Update Progress** - Document what you built and learned
8. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** - do not continue to the next story
9. **STOP** - Your iteration is done. Exit now. The loop script handles the next iteration.

## Codebase Patterns (MUST FOLLOW)

### File Structure
- Scripts: `scripts/intelligence/` (this is where all Python scripts live)
- Strategy docs: `docs/Outdoorithm/` (DONOR_SEGMENTATION.md, COME_ALIVE_2026_Campaign.md, OC_FUNDRAISING_PLAYBOOK.md)
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

### Database
- Use `supabase-contacts` MCP server for migrations and raw SQL (US-001)
- Use `supabase-py` REST client for reads/writes in Python scripts
- contacts table has integer `id` column
- JSONB columns: `ask_readiness`, `oc_engagement`, `communication_history`, `ai_tags`, `campaign_2026` (new)
- Campaign data structure: `campaign_2026` = `{"scaffold": {...}, "personal_outreach": {...}, "campaign_copy": {...}, "scaffolded_at": "...", ...}`
- When saving, merge into existing JSONB (don't overwrite other keys)

### GPT-5 mini Specifics
- Does NOT support `temperature=0` — use default only
- Structured output: `openai.responses.parse()` with `text_format=PydanticModel`
- Optimal workers: 150 (yields ~9,000 RPM with ~1s latency per call)

### Anthropic (Claude Opus 4.6) Specifics
- Model name: `claude-opus-4-6`
- Client: `anthropic.Anthropic()` (reads ANTHROPIC_API_KEY from env)
- Messages API: `client.messages.create(model="claude-opus-4-6", max_tokens=4096, system=SYSTEM_PROMPT, messages=[{"role": "user", "content": context}])`
- For structured output: use JSON mode via system prompt instruction + parse JSON from response, OR use tool_use pattern
- Low concurrency: 3-5 workers (these are high-quality, expensive calls)

### Strategy Docs (READ THESE for system prompts)

**CRITICAL: When building system prompts for the scaffolding and copy-writing scripts, you MUST read the full strategy docs and embed their content. These docs contain the persona decision trees, execution matrices, story banks, and donor psychology frameworks that the LLM needs to produce correct output.**

- `docs/Outdoorithm/DONOR_SEGMENTATION.md` — Contains:
  - 3 campaign personas (Believer, Impact Professional, Network Peer) with full scaffolds
  - Execution matrix: Persona x Lifecycle → opener inserts, ask anchors, follow-up timing, thank-you frames
  - Motivation flags: relationship, mission_alignment, peer_identity, parental_empathy, justice_equity, community_belonging
  - Capacity tier mapping: leadership ($25K+), major ($5K-$25K), mid ($1K-$5K), base ($250-$1K), community (<$250)
  - Data governance guidelines

- `docs/Outdoorithm/COME_ALIVE_2026_Campaign.md` — Contains:
  - Personal outreach template (lines 130-155) — THE voice target for Justin's messages
  - Story bank: Valencia, Carl, 8-year-old, Michelle Latting, Joy, Aftan, Dorian, Sally Disney
  - Email templates (Email 1, 2, 3) with exact copy
  - Text follow-up templates
  - Thank-you template
  - Tier 1 outreach contacts (lines 163-211) — named List A contacts
  - Impact language: $500=one family, $1K=two families, $2.5K=quarter trip, $5K=half trip, $10K=full trip

- `docs/Outdoorithm/OC_FUNDRAISING_PLAYBOOK.md` — Contains:
  - Donor psychology quick reference (identity circuit, warm glow, decision friction, etc.)
  - Channel roles and effectiveness data
  - Stewardship sequences

### Justin's Voice (for system prompts)
- Direct, punchy, uses sentence fragments for emphasis
- Em dashes for parenthetical thoughts
- "This keeps happening" as a transition
- "Quick thing" as an opener
- Casual and conversational — sounds like a text from a friend
- Never sounds like a development officer or nonprofit pitch
- 2:1 "you/your" to "we/our" ratio
- Under 200 words for emails, shorter for texts
- "If you want in" = joining, not saving

## Rules for Feature Implementation

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- **Follow existing patterns** — Read score_ask_readiness.py before writing any script
- **Read strategy docs** — The system prompts must be comprehensive and accurate
- **Document as you go** — Update progress.txt with learnings
- **Never skip quality checks** — Scripts must run without errors before committing
- **Merge JSONB, don't overwrite** — When saving to campaign_2026, preserve existing keys
- **Keep it practical** — Ship working code, don't over-engineer

## Important Notes

- The Supabase MCP server for this project is `supabase-contacts` (NOT `supabase_crm`)
- When running migrations, use the `execute_sql` MCP tool on `supabase-contacts`
- GPT-5 mini does NOT support temperature=0 — use default only
- OPENAI_APIKEY has no underscore before KEY
- Always activate venv before running Python: `source .venv/bin/activate`
- Run scripts from the project root: `python scripts/intelligence/<script>.py`

Begin now. Read the PRD and implement the next incomplete story. After completing it, STOP.
