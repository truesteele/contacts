# Ralph Agent Instructions - Feature Implementation

You are building the Familiarity Rater, a mobile-optimized contact rating web app. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: familiarity-rater
Loop Type: **Feature Implementation**
Loop Directory: .ralph/familiarity-rater/

## Workflow

1. **Read PRD** at `.ralph/familiarity-rater/prd.md` - Find first `[ ]` story
2. **Read Progress** at `.ralph/familiarity-rater/progress.txt` - Learn patterns from previous iterations
3. **Implement the Feature**
   - Write production-quality TypeScript code
   - Follow existing codebase patterns in `job-matcher-ai/`
   - Use Tailwind CSS + shadcn/ui component patterns
   - Use the shared Supabase client from `lib/supabase.ts`
4. **Run Quality Check**
   - TypeScript: `cd job-matcher-ai && npx tsc --noEmit` (must pass)
   - If typecheck fails, fix the errors before marking complete
5. **Commit Your Work**
   - Format: `feat: [US-XXX] - Story title`
   - Example: `feat: [US-001] - Add familiarity_rating columns to contacts table`
6. **Update PRD** - Mark story `[x]` complete, mark acceptance criteria `[x]`
7. **Update Progress** - Document what you built and learned
8. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story
9. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Technical Context

### Project Structure
- Next.js 15 app: `job-matcher-ai/`
- App Router pages: `job-matcher-ai/app/`
- API routes: `job-matcher-ai/app/api/`
- Components: `job-matcher-ai/components/`
- Shared libs: `job-matcher-ai/lib/` (supabase.ts, types.ts, network-tools.ts)
- UI components (shadcn): `job-matcher-ai/components/ui/`
- Migrations: `supabase/migrations/`

### Database
- Supabase PostgreSQL — use the shared client in `lib/supabase.ts`
- Contacts table has ~2,498 rows with rich enrichment data
- Environment variables (SUPABASE_URL, SUPABASE_SERVICE_KEY) are in `.env` at project root
- For running migrations, use the Supabase MCP tools if available, otherwise create the SQL file and execute it

### Key Existing Patterns
- API routes use NextResponse.json() for responses
- Components are React client components with 'use client' directive
- Tailwind CSS for all styling, shadcn/ui for component primitives
- Supabase queries use the `@supabase/supabase-js` client

### Justin's Profile (for shared context matching)
- Schools: Harvard Business School (HBS), Harvard Kennedy School (HKS), University of Virginia (UVA)
- Companies: Kindora, True Steele, Outdoorithm, Outdoorithm Collective, Google.org, Year Up, Bridgespan Group, Bain & Company

## Rules for Feature Implementation

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- **Follow existing patterns** - Check similar features in the codebase first
- **Typecheck must pass** - Run `cd job-matcher-ai && npx tsc --noEmit` before marking done
- **Document as you go** - Update progress.txt with learnings
- **Mobile-first design** - This app is primarily used on a phone
- **No tests required** - This project doesn't have a test suite; focus on typecheck

Begin now. Read the PRD and implement the next incomplete story. After completing it, STOP.
