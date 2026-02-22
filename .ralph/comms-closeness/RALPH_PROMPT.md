# Ralph Agent Instructions — Communication Closeness Scoring

You are an autonomous coding agent building a unified communication architecture and GPT-5 mini closeness scoring system. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: comms-closeness
Loop Type: **Feature Implementation**
Loop Directory: .ralph/comms-closeness/

## Project Context

This project builds a behavioral communication closeness measure that complements the existing manual `familiarity_rating` (0-4). The system unifies email, LinkedIn DM, and SMS data into a single table, then uses GPT-5 mini to assess each contact's communication closeness and momentum.

**Key docs:**
- `docs/RELATIONSHIP_DIMENSIONS_FRAMEWORK.md` — Full theoretical framework (Granovetter tie strength, 2x2 map, channel signal quality)
- `CLAUDE.md` — API rate limits and project conventions
- `scripts/intelligence/score_ask_readiness.py` — Reference for GPT-5 mini structured output patterns
- `scripts/intelligence/tag_contacts_gpt5m.py` — Reference for GPT-5 mini structured output patterns

## Tech Stack

- **Database:** Supabase PostgreSQL
  - For DDL (CREATE TABLE, ALTER TABLE, etc.): Use Supabase MCP `apply_migration` tool
  - For DML (SELECT, INSERT, UPDATE): Use Supabase MCP `execute_sql` tool
  - The correct MCP server name prefix is `mcp__supabase-contacts__` (with hyphen, not underscore)
- **Python:** 3.12, venv at `.venv/`, activate with `source .venv/bin/activate`
- **Scripts:** `scripts/intelligence/` directory
- **OpenAI:** GPT-5 mini via Responses API, env var `OPENAI_APIKEY`, 150 workers optimal
- **UI:** Next.js in `job-matcher-ai/`, TypeScript, Tailwind, shadcn/ui
- **Environment:** `.env` file has SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_APIKEY

## Workflow

1. **Read PRD** at `.ralph/comms-closeness/prd.md` — Find first story with `[ ]` status
2. **Read Progress** at `.ralph/comms-closeness/progress.txt` — Learn from previous iterations
3. **Implement** the story following existing codebase patterns
4. **Quality Check:**
   - For Python scripts: Run with `--test` flag if available, or verify syntax with `python -c "import ast; ast.parse(open('path').read())"`
   - For SQL migrations: Verify columns exist after applying
   - For UI changes: Run `cd job-matcher-ai && npx tsc --noEmit`
5. **Commit** with format: `feat: [US-XXX] - Story title`
6. **Update PRD** — Change story status from `[ ]` to `[x]`, mark acceptance criteria `[x]`
7. **Update Progress** — Append what you did and learned
8. **Check Completion**:
   - Verify PRD has no `[ ]` items
   - If ALL stories complete, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story
9. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Important Conventions

- **Supabase pagination:** Use `.range(offset, offset + page_size - 1)` for >1000 rows
- **GPT-5 mini:** Does NOT support temperature=0 — use default only
- **OpenAI key:** env var is `OPENAI_APIKEY` (no underscore before KEY)
- **Null bytes:** Use `_strip_null_bytes()` when saving text to PostgreSQL JSONB (see score_ask_readiness.py)
- **Model ID:** Check `score_ask_readiness.py` or `tag_contacts_gpt5m.py` for the correct model string — use the same one
- **Python runs:** Always activate venv first: `source .venv/bin/activate`
- **Script execution:** Run from repo root: `python scripts/intelligence/script_name.py`
- **Concurrent workers:** Default 150 for GPT calls (ThreadPoolExecutor)
- **Structured output:** Use OpenAI Responses API with Pydantic schemas (see existing scripts for exact pattern)

## Rules

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- Never skip quality checks
- Document learnings for future iterations in progress.txt
- Follow existing code patterns in `scripts/intelligence/`
- Do not print the completion token in normal logs or explanations
- For database changes, always verify the result with a SELECT query
- When running scripts that process all contacts, monitor for errors and report final counts

Begin now. Read the PRD and implement the next incomplete story. After completing it, STOP.
