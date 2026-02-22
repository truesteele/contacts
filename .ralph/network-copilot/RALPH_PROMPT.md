# Ralph Agent Instructions — Feature Implementation

You are building the Network Copilot (AI Filter Co-pilot) for a personal contacts database. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: network-copilot
Loop Type: **Feature Implementation**
Loop Directory: .ralph/network-copilot/

## Project Context

You are replacing the chat-based Network Intelligence tab with an **AI Filter Co-pilot** interface in an existing Next.js 15 app. The app is at `job-matcher-ai/` within the repo root.

**What we're building:** A natural language → structured filters → interactive table UI. The user types a question like "Who should I invite to the fundraiser?". Claude translates it into structured filter JSON. The filters appear as editable chips in a filter bar. Results display in a sortable, selectable table. Users can save selections to prospect lists, draft personalized outreach, and send emails.

**Architecture doc (read for context):** `docs/NETWORK_INTELLIGENCE_SYSTEM.md`

**Key existing files:**
- `job-matcher-ai/lib/network-tools.ts` — **REUSE these functions** for search. Contains: `searchNetwork()`, `semanticSearch()`, `hybridSearch()`, `getContactDetail()`, `getOutreachContext()`, `exportContacts()`, `generateEmbedding768()`
- `job-matcher-ai/lib/supabase.ts` — Supabase client, NetworkContact interface
- `job-matcher-ai/lib/openai.ts` — `generateEmbedding768()` for 768-dim embeddings
- `job-matcher-ai/components/socal-contacts.tsx` — **Reference pattern** for sortable table with checkboxes, search, CSV export
- `job-matcher-ai/app/page.tsx` — Main page with 4 tabs (swap `NetworkIntelligence` → `NetworkCopilot`)
- `job-matcher-ai/components/ui/` — Existing shadcn/ui components (button, card, scroll-area, tabs, dialog, toast)

**Tech stack:**
- Next.js 15, React 19, TypeScript 5.7
- Tailwind CSS 3.4 with shadcn/ui pattern (Radix UI + CVA + tailwind-merge)
- Edge runtime for all API routes (`export const runtime = 'edge'`)
- Anthropic SDK for Claude API (model: `claude-sonnet-4-6`)
- Supabase PostgreSQL with pgvector (768-dim embeddings)
- CSS variables: HSL format in globals.css

**Critical technical notes:**
- **768-dim embeddings**: Query embeddings MUST use `dimensions: 768` or RPC fails
- **Empty `.in()` arrays**: Supabase throws 400 on `.in('col', [])` — guard every instance
- **Edge runtime**: No Node.js fs/Buffer. All processing is pure JS/TS strings
- **ai_tags size**: Don't return full JSONB blob — extract subfields to stay within token budget
- **Forced tool_use**: For parse-filters, use `tool_choice: { type: 'tool', name: 'set_filters' }` to guarantee structured JSON output

**Design direction:**
- Very polished, professional frontend — not generic AI aesthetics
- Use shadcn/ui components consistently
- Clean, scannable data tables
- Subtle animations and transitions where appropriate
- Dark mode support via CSS variables (already configured)

## Workflow

1. **Read PRD** at `.ralph/network-copilot/prd.md` — Find first story with `[ ]` status
2. **Read Progress** at `.ralph/network-copilot/progress.txt` — Learn from previous iterations
3. **Implement the Story**
   - Write production-quality TypeScript code
   - Follow existing codebase patterns (check `components/socal-contacts.tsx` for table pattern, `components/ui/` for shadcn pattern)
   - Reuse existing functions from `lib/network-tools.ts` rather than rewriting
   - Ensure Edge runtime compatibility (no Node.js APIs)
4. **Run Quality Check**
   - Build: `cd job-matcher-ai && npm run build` (MUST pass with zero errors)
   - Fix any TypeScript or build errors before proceeding
5. **Commit Your Work**
   - Format: `feat: [US-XXX] - Story title`
   - Example: `feat: [US-001] - Install dependencies and add shadcn/ui components`
   - Stage only relevant files (not .ralph/ directory)
6. **Update PRD** — Mark story `[x]` complete, mark acceptance criteria `[x]`
7. **Update Progress** — Document what you built, files changed, learnings, any issues
8. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story
9. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Rules

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- **Always run `cd job-matcher-ai && npm run build`** before marking a story complete. If it fails, fix the errors.
- **Reuse existing code** — `lib/network-tools.ts` already has all search/detail/outreach functions. Don't rewrite them.
- **Follow shadcn/ui patterns** — look at existing `components/ui/` files for the wrapper pattern.
- **Edge runtime only** — all API routes must use `export const runtime = 'edge'`
- **Use Supabase MCP tools** for database migrations when needed
- **Document learnings** — future iterations depend on your notes in progress.txt
- **Do not print the completion token** except when all stories are complete
- **Do not commit .ralph/ files** — only commit app source code

## If Stuck

If you cannot complete a story after genuine effort:
1. Document what you tried in progress.txt
2. Document the blocker clearly
3. Exit normally — the next iteration will try again with fresh context

Do NOT output `<promise>COMPLETE</promise>` unless ALL stories are done.

---

Now begin. Read the PRD, find the next incomplete story, and implement it. After completing it, STOP.
