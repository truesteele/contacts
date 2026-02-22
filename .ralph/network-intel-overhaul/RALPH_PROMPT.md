# Ralph Agent Instructions — Network Intelligence Overhaul

You are an autonomous coding agent building a donor psychology-powered network intelligence system. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: network-intel-overhaul
Loop Type: **Feature Implementation**
Loop Directory: .ralph/network-intel-overhaul/

## Key References

**IMPORTANT: Read the plan file for full architecture details, donor psychology prompt text, JSONB schemas, and design decisions:**
- **Plan file:** `/Users/Justin/.claude/plans/cozy-munching-dongarra.md`
- **Network Intelligence System doc:** `docs/NETWORK_INTELLIGENCE_SYSTEM.md`

## Codebase Patterns

- **Python scripts:** Located in `scripts/intelligence/`. Use ThreadPoolExecutor for concurrency, Supabase pagination with `.range(offset, offset + page_size - 1)`, `.env` for API keys via `python-dotenv`
- **Python venv:** `/Users/Justin/Code/TrueSteele/contacts/.venv/` — activate with `source .venv/bin/activate`
- **Existing script patterns:** See `tag_contacts_gpt5m.py` for GPT-5 mini structured output, `gather_comms_history.py` for Gmail, `scrape_contact_posts.py` for Apify
- **Next.js app:** `job-matcher-ai/` directory. App Router, TypeScript, Tailwind CSS
- **API routes:** `job-matcher-ai/app/api/network-intel/` — search, parse-filters, contact/[id], outreach/draft, prospect-lists
- **Core lib:** `job-matcher-ai/lib/network-tools.ts` (tool definitions + implementations), `types.ts`, `supabase.ts`, `openai.ts`
- **Components:** `job-matcher-ai/components/` — contacts-table, contact-detail-sheet, filter-bar, network-copilot, etc.
- **API keys in .env:** `OPENFEC_API_KEY`, `BATCHDATA_API_KEY`, `OPENAI_APIKEY` (note: APIKEY not API_KEY), `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- **Supabase MCP:** Available for migrations and SQL execution

## Workflow

1. **Read PRD** at `.ralph/network-intel-overhaul/prd.md` - Find first story with `[ ]` status
2. **Read Progress** at `.ralph/network-intel-overhaul/progress.txt` - Learn from previous iterations
3. **Read Plan File** at `/Users/Justin/.claude/plans/cozy-munching-dongarra.md` - Get full design details for the current story
4. **Implement** the story following existing codebase patterns
5. **Quality Check:**
   - For Python scripts: run with `--test` flag to verify
   - For TypeScript: run `cd job-matcher-ai && npx tsc --noEmit` (must pass)
   - For migrations: verify columns exist after applying
6. **Commit** with format: `feat: [US-XXX] - Story title`
7. **Update PRD** - Change story status from `[ ]` to `[x]`, mark acceptance criteria `[x]`
8. **Update Progress** - Append what you did and learned
9. **Check Completion**:
   - Verify PRD has no `[ ]` items
   - If ALL stories complete, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story
10. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Rules

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- Never skip quality checks
- Document learnings for future iterations in progress.txt
- Follow existing code patterns — read similar files before writing new ones
- For Python scripts: always include `--test`, `--batch`, `--start-from` CLI flags
- For TypeScript: always verify compilation passes
- Do not print the completion token in normal logs or explanations
- When running Python scripts for data enrichment, only run with `--test` flag — do NOT run full batch (the user will do that manually)

## Special Notes

- **US-001 through US-003** are setup/documentation stories — straightforward
- **US-004 through US-007** are Python enrichment scripts — follow the pattern of existing scripts in `scripts/intelligence/`
- **US-008 through US-013** are TypeScript backend changes — read existing code carefully before modifying
- **US-014 through US-016** are React UI changes — follow existing component patterns
- **US-017** runs existing scripts — just execute and verify

Begin now. Read the PRD and implement the next incomplete story. After completing it, STOP.
