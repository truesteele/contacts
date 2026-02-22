# Project: Pipeline CRM Kanban

## Overview
Build a lightweight Kanban-based pipeline/CRM tool into the existing Next.js app at `/tools/pipeline`. Tracks outreach and deal opportunities across three business entities (Kindora, Outdoorithm, True Steele) with separate pipeline views. Uses drag-and-drop cards, links to existing contacts, and stores data in Supabase.

## Technical Context
- **Tech Stack:** Next.js 15 (App Router), Supabase (PostgreSQL), Tailwind CSS, shadcn/ui, Lucide icons
- **Existing patterns:** `'use client'` pages, service client from `@/lib/supabase`, API routes at `app/api/network-intel/`, `ContactDetailSheet` component for contact drill-down
- **New dependency needed:** `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`
- **Drag-and-drop:** Use `dnd-kit` (NOT react-beautiful-dnd which is deprecated)
- **Existing shadcn/ui components:** badge, button, card, checkbox, dropdown-menu, input, scroll-area, select, separator, sheet, tabs, textarea, tooltip
- **Auth:** The app uses middleware auth. Pipeline pages should follow existing auth patterns.
- **Database:** Supabase with service key (server-side). Use `@/lib/supabase` `supabase` export for API routes.

## Pipeline Stages (default for all pipelines)
1. **Backlog** - Identified, no contact yet
2. **Reached Out** - First outreach sent
3. **Engaged** - They replied or took a meeting
4. **Proposal** - Dollar amount and scope defined
5. **Negotiating** - Back and forth on terms
6. **Won** - Signed or committed
7. **Lost** - Passed or ghosted 60+ days (hidden from board by default)

## User Stories

### US-001: Create Supabase Migration for pipelines and deals tables
**Priority:** 1
**Status:** [x] Complete

**Description:**
Create the database schema for the pipeline CRM. Two tables: `pipelines` and `deals`.

**Acceptance Criteria:**
- [ ] Create migration file at `supabase/migrations/20260222_add_pipeline_crm.sql`
- [ ] `pipelines` table: id (uuid, PK, default gen_random_uuid()), name (text NOT NULL), slug (text UNIQUE NOT NULL), entity (text NOT NULL, e.g. 'kindora', 'outdoorithm', 'truesteele'), stages (jsonb, default array of stage objects with name+color), created_at (timestamptz default now()), updated_at (timestamptz default now())
- [ ] `deals` table: id (uuid, PK, default gen_random_uuid()), pipeline_id (uuid FK references pipelines ON DELETE CASCADE), contact_id (integer REFERENCES contacts(id)), title (text NOT NULL), stage (text NOT NULL default 'backlog'), amount (numeric(12,2)), close_date (date), notes (text), next_action (text), next_action_date (date), source (text), lost_reason (text), position (integer default 0), created_at (timestamptz default now()), updated_at (timestamptz default now())
- [ ] Create index on deals(pipeline_id, stage)
- [ ] Create index on deals(contact_id)
- [ ] Seed 3 default pipelines: Kindora Fundraising (entity: kindora), Outdoorithm Partnerships (entity: outdoorithm), True Steele Consulting (entity: truesteele)
- [ ] Run migration against the database using the Supabase MCP `apply_migration` tool (use the `supabase-contacts` MCP server)
- [ ] Verify tables exist by querying with `execute_sql`

**Notes:**
- Use the `supabase-contacts` MCP server (NOT `supabase_crm`) for all database operations
- The contacts table uses integer `id` column, not uuid

---

### US-002: Install dnd-kit and create API routes for deals CRUD
**Priority:** 2
**Status:** [x] Complete

**Description:**
Install the dnd-kit package and create the API routes needed for the pipeline page.

**Acceptance Criteria:**
- [ ] Run `npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities` in the `job-matcher-ai/` directory
- [ ] Create `app/api/network-intel/pipeline/route.ts` - GET returns all pipelines, POST creates a new pipeline
- [ ] Create `app/api/network-intel/pipeline/deals/route.ts` - GET returns deals for a pipeline_id (query param), POST creates a new deal
- [ ] Create `app/api/network-intel/pipeline/deals/[id]/route.ts` - PATCH updates a deal (stage, position, fields), DELETE soft-deletes (sets stage to 'lost')
- [ ] Create `app/api/network-intel/pipeline/deals/reorder/route.ts` - PATCH batch updates positions when cards are reordered
- [ ] All routes use `import { supabase } from '@/lib/supabase'` pattern
- [ ] All routes use `export const runtime = 'edge'` if possible (fall back to Node runtime if edge doesn't support the queries)
- [ ] GET deals includes contact info via join: `deals(*, contacts(id, first_name, last_name, company, position, headline, city, state))`
- [ ] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

**Notes:**
- Follow the pattern in `app/api/network-intel/ask-readiness/route.ts` for Supabase query patterns
- Supabase pagination with `.range()` for >1000 rows

---

### US-003: Build the Kanban board component with dnd-kit
**Priority:** 3
**Status:** [x] Complete

**Description:**
Create the core Kanban board component that displays deals as draggable cards organized by stage columns.

**Acceptance Criteria:**
- [ ] Create `components/pipeline/kanban-board.tsx` - `'use client'` component using DndContext, SortableContext, DragOverlay from dnd-kit
- [ ] Create `components/pipeline/kanban-column.tsx` - renders a single stage column with droppable area and header showing stage name + deal count + total value
- [ ] Create `components/pipeline/deal-card.tsx` - draggable card showing: title, contact name + company, amount (if set), next action + date (if set), days in stage, source badge
- [ ] Drag a card between columns updates its `stage` field via API
- [ ] Drag a card within a column reorders via `position` field
- [ ] Use optimistic updates: update local state immediately, then call API in background. Revert on error.
- [ ] Cards are compact but readable. Use existing shadcn Card component as base.
- [ ] Columns scroll vertically if they overflow. Use horizontal scroll if board overflows viewport.
- [ ] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

**Notes:**
- DndContext wraps the whole board, one SortableContext per column
- Use `closestCorners` collision detection strategy
- Use `DragOverlay` for the floating card during drag (not inline transform)
- Must be `'use client'` since dnd-kit uses browser APIs

---

### US-004: Build the pipeline page at /tools/pipeline
**Priority:** 4
**Status:** [x] Complete

**Description:**
Create the main pipeline page that ties everything together.

**Acceptance Criteria:**
- [ ] Create `app/tools/pipeline/page.tsx` as `'use client'` page
- [ ] Pipeline selector at top (shadcn Select or Tabs) showing all pipelines, defaults to first one
- [ ] Pipeline selection updates URL query param `?pipeline=slug` (bookmarkable)
- [ ] "New Deal" button opens a dialog/sheet to create a deal: title (required), contact (searchable select linking to contacts table), amount, close date, source, notes, next action + date
- [ ] Contact search in "New Deal" form queries contacts table and shows name + company in dropdown
- [ ] Board renders KanbanBoard component with deals for the selected pipeline
- [ ] "Lost" deals hidden from board by default, with a toggle to show/hide them
- [ ] Back arrow link to /tools (consistent with ask-readiness page pattern)
- [ ] Summary stats bar: total deals, total pipeline value, deals per stage count
- [ ] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

**Notes:**
- Follow the page structure pattern from `/tools/ask-readiness/page.tsx`
- Use the existing `ArrowLeft` + Link pattern for back navigation
- Contact picker should be a searchable input (type to filter), not a giant dropdown of 2900 contacts

---

### US-005: Add deal detail sheet and edit capability
**Priority:** 5
**Status:** [x] Complete

**Description:**
When clicking a deal card, open a detail sheet (right drawer) showing full deal info with edit capability.

**Acceptance Criteria:**
- [ ] Create `components/pipeline/deal-detail-sheet.tsx` using shadcn Sheet component (right side drawer)
- [ ] Shows all deal fields in editable form: title, stage (select), contact (read-only link), amount, close date, notes, next action, next action date, source, lost reason (only if stage is lost)
- [ ] "Save" button patches the deal via API
- [ ] "View Contact" link opens the ContactDetailSheet for the linked contact
- [ ] Shows deal creation date and last updated date
- [ ] Shows days in current stage (calculated from updated_at)
- [ ] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

**Notes:**
- Use the existing `ContactDetailSheet` component pattern as reference
- Sheet should be similar width and style to existing sheets in the app

---

### US-006: Add pipeline page to tools navigation
**Priority:** 6
**Status:** [ ] Incomplete

**Description:**
Wire the pipeline page into the app's navigation so it's accessible from the tools page.

**Acceptance Criteria:**
- [ ] Add "Pipeline" card/link to `app/tools/page.tsx` tools grid, with a Kanban-style icon (use `LayoutGrid` or `Columns3` from lucide-react)
- [ ] Card shows brief description: "Track outreach and deals across Kindora, Outdoorithm, and True Steele"
- [ ] Link navigates to `/tools/pipeline`
- [ ] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`
- [ ] Build passes: `cd job-matcher-ai && npm run build`

**Notes:**
- Follow the existing card pattern on the tools page
- This is the final story - make sure the full build passes, not just typecheck
