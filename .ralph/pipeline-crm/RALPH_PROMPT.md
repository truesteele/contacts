# Ralph Agent Instructions - Feature Implementation

You are building a Pipeline CRM Kanban tool autonomously. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: pipeline-crm
Loop Type: **Feature Implementation**
Loop Directory: .ralph/pipeline-crm/

## Workflow

1. **Read PRD** at `.ralph/pipeline-crm/prd.md` - Find first `[ ]` story
2. **Read Progress** at `.ralph/pipeline-crm/progress.txt` - Learn patterns
3. **Implement the Feature**
   - Write production-quality code
   - Follow existing codebase patterns (see below)
   - Add proper error handling
   - Include TypeScript types
4. **Run Quality Checks**
   - TypeScript: `cd job-matcher-ai && npx tsc --noEmit` (must pass)
   - Build: `cd job-matcher-ai && npm run build` (must pass for final story only)
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
- Pages: `job-matcher-ai/app/tools/pipeline/page.tsx`
- API routes: `job-matcher-ai/app/api/network-intel/pipeline/`
- Components: `job-matcher-ai/components/pipeline/`
- Supabase client: `import { supabase } from '@/lib/supabase'`

### UI Patterns
- All pages are `'use client'` with React hooks for data fetching
- Use shadcn/ui components: Badge, Button, Card, Select, Sheet, ScrollArea, Tabs, Input, Textarea, Tooltip
- Use Lucide React icons
- Use `cn()` from `@/lib/utils` for conditional classnames
- Dark mode support: always include `dark:` variants in Tailwind classes
- Follow the page structure from `app/tools/ask-readiness/page.tsx`

### API Route Patterns
- Use `export const runtime = 'edge'` where possible
- Import supabase from `@/lib/supabase`
- Return `NextResponse.json()` with proper error handling
- Use Supabase `.range()` for pagination on large datasets

### Database
- Use `supabase-contacts` MCP server for migrations and SQL execution
- contacts table has integer `id`, NOT uuid
- Always use `gen_random_uuid()` for new table PKs that are uuid type

### Drag and Drop (dnd-kit)
- Use `@dnd-kit/core` and `@dnd-kit/sortable`
- DndContext wraps the board, SortableContext per column
- Use `closestCorners` collision detection
- Use `DragOverlay` for the floating card during drag
- Optimistic updates: update state first, then API call, revert on error

## Rules for Feature Implementation

- **EXACTLY ONE story per iteration** - after completing one story, STOP. Do not start the next one.
- **Follow existing patterns** - Check similar features first
- **Document as you go** - Update progress.txt with learnings
- **Never skip quality checks** - Broken builds compound across iterations
- **No em dashes** in any UI text or comments (user preference)
- **Keep it practical** - Ship working code, don't over-engineer

## Important Notes

- The Supabase MCP server for this project is `supabase-contacts` (NOT `supabase_crm`)
- When running migrations, use the `apply_migration` MCP tool
- To verify SQL, use the `execute_sql` MCP tool
- dnd-kit must be installed first (US-002) before building board components (US-003)
- Contact IDs in the contacts table are integers, deal IDs should be uuids

Begin now. Read the PRD and implement the next incomplete story. After completing it, STOP.
