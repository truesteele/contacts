# Ralph Agent Instructions — Feature Implementation

You are building the Network Intelligence System for a personal contacts database. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: network-intelligence
Loop Type: **Feature Implementation**
Loop Directory: .ralph/network-intelligence/

## Project Context

You are building an AI-powered network intelligence system on top of ~2,498 LinkedIn contacts stored in Supabase PostgreSQL with pgvector. The system uses GPT-5 mini structured output for classification/tagging and OpenAI text-embedding-3-small for semantic similarity search.

**Full architecture doc:** `docs/NETWORK_INTELLIGENCE_SYSTEM.md` — READ THIS before your first story. It contains the complete schema, prompts, scoring models, and SQL.

**Key files:**
- `.env` — API keys (SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_APIKEY)
- `scripts/enrichment/enrich_contacts_apify.py` — Reference pattern for ThreadPoolExecutor + Supabase pagination
- `scripts/intelligence/` — Where new scripts go

**Tech stack:**
- Python 3 with venv at `.venv/` — activate with `source .venv/bin/activate`
- Supabase Python client (`supabase`)
- OpenAI Python SDK (`openai`)
- Pydantic for schema validation
- Supabase MCP tools for SQL execution (`mcp__supabase__execute_sql`)

**Key patterns:**
- Supabase pagination: `.range(offset, offset + page_size - 1)` for >1000 rows
- Always load `.env` with `python-dotenv`
- JSONB enrichment fields may be string-wrapped JSON — handle both formats
- Use `ThreadPoolExecutor(max_workers=10)` for concurrent API calls

## Workflow

1. **Read PRD** at `.ralph/network-intelligence/prd.md` — Find first story with `[ ]` status
2. **Read Progress** at `.ralph/network-intelligence/progress.txt` — Learn from previous iterations
3. **Read Planning Doc** at `docs/NETWORK_INTELLIGENCE_SYSTEM.md` — Get schema, prompts, SQL
4. **Implement the Story**
   - Write production-quality Python code
   - Follow existing codebase patterns (check `scripts/enrichment/` for reference)
   - Handle errors gracefully
   - Add progress logging
5. **Run Quality Checks**
   - Python script runs without errors
   - Expected data appears in database (verify via Supabase MCP query)
   - Output quality is reasonable (spot-check for scoring/tagging stories)
6. **Commit Your Work**
   - Format: `feat: [US-XXX] - Story title`
   - Example: `feat: [US-001] - Add intelligence columns and indexes to contacts table`
7. **Update PRD** — Mark story `[x]` complete, mark acceptance criteria `[x]`
8. **Update Progress** — Document what you built, files changed, learnings, any issues
9. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story
10. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Rules

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- **Always activate venv** before running Python: `source .venv/bin/activate`
- **Install missing packages** into the venv if needed: `pip install openai pydantic`
- **Never hardcode API keys** — always load from `.env`
- **Use Supabase MCP tools** for SQL execution when needed (migrations, queries, verification)
- **Handle JSONB carefully** — enrichment fields like `enrich_employment` may be stored as strings or native JSONB
- **Skip already-processed contacts** — check if `ai_tags IS NOT NULL` before re-processing (unless `--force`)
- **Document learnings** — future iterations depend on your notes in progress.txt
- **Do not print the completion token** except when all stories are complete

## If Stuck

If you cannot complete a story after genuine effort:
1. Document what you tried in progress.txt
2. Document the blocker clearly
3. Exit normally — the next iteration will try again with fresh context

Do NOT output `<promise>COMPLETE</promise>` unless ALL stories are done.

---

Now begin. Read the PRD, find the next incomplete story, and implement it. After completing it, STOP.
