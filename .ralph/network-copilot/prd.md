# Project: Network Copilot — AI Filter Co-pilot

## Overview

Replace the chat-based Network Intelligence tab with an AI Filter Co-pilot interface. Users type natural language queries, Claude translates them to structured filters, results appear in an interactive sortable table. Features include: editable filter bar, prospect list saving, contact detail slide-out, AI outreach drafting, and email sending via Resend.

## Technical Context

- **App:** Next.js 15 at `job-matcher-ai/`
- **UI:** shadcn/ui (Radix UI + CVA + Tailwind), dark mode via CSS variables
- **API:** Edge runtime, Anthropic SDK (claude-sonnet-4-6), Supabase PostgreSQL + pgvector
- **Existing search functions:** `lib/network-tools.ts` (searchNetwork, semanticSearch, hybridSearch, getContactDetail, getOutreachContext, exportContacts)
- **Embeddings:** 768-dim text-embedding-3-small via `lib/openai.ts`
- **Quality gate:** `cd job-matcher-ai && npm run build` must pass

## User Stories

### US-001: Install Dependencies and Add shadcn/ui Components
**Priority:** 1
**Status:** [x] Complete

**Description:**
Install new npm packages needed for the co-pilot UI and create the shadcn/ui wrapper components that don't exist yet.

**Acceptance Criteria:**
- [x] Install npm packages: `resend`, `@radix-ui/react-checkbox`, `@radix-ui/react-select`, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-tooltip`, `@radix-ui/react-separator`
- [x] Create `components/ui/sheet.tsx` — shadcn Sheet component (wraps `@radix-ui/react-dialog` — already installed)
- [x] Create `components/ui/badge.tsx` — shadcn Badge component (pure Tailwind + CVA, no Radix needed)
- [x] Create `components/ui/checkbox.tsx` — wraps `@radix-ui/react-checkbox`
- [x] Create `components/ui/select.tsx` — wraps `@radix-ui/react-select`
- [x] Create `components/ui/dropdown-menu.tsx` — wraps `@radix-ui/react-dropdown-menu`
- [x] Create `components/ui/input.tsx` — pure HTML input with Tailwind styling
- [x] Create `components/ui/textarea.tsx` — pure HTML textarea with Tailwind styling
- [x] Create `components/ui/separator.tsx` — wraps `@radix-ui/react-separator`
- [x] Create `components/ui/tooltip.tsx` — wraps `@radix-ui/react-tooltip`
- [x] All components follow existing shadcn/ui pattern (see `components/ui/button.tsx` for reference)
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- Check existing `components/ui/` files for the exact CVA + cn() pattern used in this project
- Sheet uses the Dialog primitive under the hood with slide-in animation
- Don't install `@radix-ui/react-dialog` — it's already a dependency

---

### US-002: Create FilterState Types and Parse-Filters API Route
**Priority:** 2
**Status:** [x] Complete

**Description:**
Define the core TypeScript types for the co-pilot and create the AI filter parsing endpoint that translates natural language into structured filters.

**Acceptance Criteria:**
- [x] Create `lib/types.ts` with interfaces: `FilterState`, `ProspectList`, `ProspectListMember`, `OutreachDraft`
- [x] `FilterState` includes: proximity_min, proximity_tiers, capacity_min, capacity_tiers, outdoorithm_fit, kindora_type, company_keyword, name_search, location_state, semantic_query, sort_by, sort_order, limit
- [x] Create `app/api/network-intel/parse-filters/route.ts`
- [x] Route uses Claude Sonnet 4.6 with `tool_choice: { type: 'tool', name: 'set_filters' }` (forced tool use)
- [x] The `set_filters` tool schema matches FilterState interface
- [x] System prompt includes Justin's profile context and scoring tier definitions
- [x] System prompt instructs Claude to be generous with filters (include more contacts rather than fewer)
- [x] Request: `{ query: string }`, Response: `{ filters: FilterState, explanation: string }`
- [x] Edge runtime (`export const runtime = 'edge'`)
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- This is single-shot request/response, NOT SSE streaming
- The `explanation` field is a brief text showing why Claude chose these filters (shown under the filter bar)
- Example: query "Who should I invite to the Outdoorithm fundraiser?" → filters: `{ outdoorithm_fit: ["high", "medium"], proximity_min: 20, sort_by: "proximity", limit: 100 }`, explanation: "Showing contacts with high/medium Outdoorithm fit, sorted by proximity"

---

### US-003: Create Search Execution API Route
**Priority:** 3
**Status:** [x] Complete

**Description:**
Create the search endpoint that takes a FilterState and executes it against Supabase, returning matching contacts.

**Acceptance Criteria:**
- [x] Create `app/api/network-intel/search/route.ts`
- [x] POST handler accepts `{ filters: FilterState }`
- [x] If `filters.semantic_query` is present, use `hybridSearch()` from `lib/network-tools.ts`
- [x] Otherwise, use `searchNetwork()` from `lib/network-tools.ts` (build the input object from FilterState)
- [x] Response: `{ contacts: NetworkContact[], total_count: number, filters_applied: FilterState }`
- [x] Guard against empty array filters (Supabase `.in()` crashes on empty arrays)
- [x] Edge runtime
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- Reuse the existing `searchNetwork()` and `hybridSearch()` functions — they already handle all the Supabase query building
- Map FilterState fields to the tool input format expected by searchNetwork (e.g., `proximity_min` maps directly)
- The search route is separate from parse-filters so filters can be edited and re-searched without re-calling Claude

---

### US-004: Build FilterBar Component
**Priority:** 4
**Status:** [x] Complete

**Description:**
Create the filter bar that displays active filters as editable chips and supports removing individual filters.

**Acceptance Criteria:**
- [x] Create `components/filter-bar.tsx`
- [x] Renders each active filter as a Badge chip (e.g., "Proximity: 40+" or "Outdoorithm: high, medium")
- [x] Each chip has an X button to remove that filter
- [x] Removing a filter calls `onFilterChange(updatedFilters)` callback
- [x] Shows filter explanation text below the chips (from Claude's explanation)
- [x] Shows total result count (e.g., "82 contacts found")
- [x] Empty state when no filters are active
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- Use the Badge component from US-001
- Filter chips should be color-coded by category (proximity=blue, capacity=green, topic=purple, etc.)
- Keep it compact — one row of chips, wrapping if needed

---

### US-005: Build ContactsTable Component
**Priority:** 5
**Status:** [x] Complete

**Description:**
Create the main data table for displaying search results with sorting, selection, and row actions.

**Acceptance Criteria:**
- [x] Create `components/contacts-table.tsx`
- [x] Columns: checkbox, Name, Company, Position, Location, Proximity (score + tier), Capacity (score + tier), Kindora Type, Outdoorithm Fit
- [x] All columns are sortable (click header to toggle asc/desc)
- [x] Checkbox in header selects/deselects all visible rows
- [x] Individual row checkboxes for selection
- [x] Click on a row (not checkbox) triggers `onContactClick(contactId)` callback
- [x] Selected contacts tracked via `Set<number>` (contact IDs)
- [x] Proximity and Capacity tiers shown as colored badges (inner_circle=green, close=blue, warm=yellow, etc.)
- [x] Compact row height — show as many contacts as possible
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- Reference `components/socal-contacts.tsx` for the sort implementation pattern (handleSort, getSortIcon)
- Don't use a third-party table library — build with native HTML table + Tailwind (matching existing pattern)
- Pagination is optional for now — most queries return <200 results

---

### US-006: Build NLQueryBar, NetworkCopilot Container, and Wire to Page
**Priority:** 6
**Status:** [x] Complete

**Description:**
Create the natural language input bar, the main container component that orchestrates everything, and replace the old Network Intelligence tab.

**Acceptance Criteria:**
- [x] Create `components/nl-query-bar.tsx` — text input with "Search" button, suggested query chips on empty state
- [x] Suggested queries: "Who should I invite to the Outdoorithm fundraiser?", "Find Kindora enterprise prospects in my inner circle", "Who cares about outdoor equity?", "Top donors in my close network", "People in philanthropy tech"
- [x] Create `components/network-copilot.tsx` — main container that manages FilterState, contacts, selection
- [x] NetworkCopilot flow: user types query → calls parse-filters API → sets FilterState → calls search API → displays results in ContactsTable
- [x] FilterBar is shown between query bar and table
- [x] Editing filters in FilterBar triggers re-search automatically
- [x] Loading states during API calls (skeleton or spinner)
- [x] Error handling with user-friendly messages
- [x] Update `app/page.tsx`: replace `NetworkIntelligence` import with `NetworkCopilot`
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- This is the integration story — everything from US-001 through US-005 comes together here
- The old `components/network-intelligence.tsx` and `app/api/network-intel/route.ts` can stay as unused files for now (don't delete)
- State management is local React state (useState) — no external state library needed

---

### US-007: Build ContactDetailSheet
**Priority:** 7
**Status:** [x] Complete

**Description:**
Create a slide-out panel that shows full contact details when a row is clicked.

**Acceptance Criteria:**
- [x] Create `components/contact-detail-sheet.tsx`
- [x] Uses shadcn Sheet component (slide in from right)
- [x] Fetches full contact detail via `getContactDetail()` from `lib/network-tools.ts` (call an API route or import directly)
- [x] Shows: name, company, position, headline, location, email, LinkedIn URL
- [x] Shows AI scores: proximity (score + tier), capacity (score + tier), Kindora type, Outdoorithm fit
- [x] Shows shared context: shared employers, shared schools, shared boards
- [x] Shows topics/interests as badges
- [x] Shows outreach context: personalization hooks, suggested opener
- [x] Wire into NetworkCopilot: clicking a table row opens the sheet
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- Create a new API route `app/api/network-intel/contact/[id]/route.ts` that calls `getContactDetail()` and `getOutreachContext()`
- Or reuse the existing functions directly if they can be called from the client side (they can't — they use server-side Supabase)
- The sheet should have a clean, card-based layout with sections

---

### US-008: Create Supabase Migration for Prospect Lists
**Priority:** 8
**Status:** [x] Complete

**Description:**
Create the database tables for saving prospect lists and tracking pipeline status.

**Acceptance Criteria:**
- [x] Create `prospect_lists` table: id (UUID, PK), name (text, not null), description (text), created_at (timestamptz), updated_at (timestamptz)
- [x] Create `prospect_list_members` table: id (UUID, PK), list_id (UUID, FK → prospect_lists), contact_id (bigint, not null), outreach_status (text, default 'not_contacted'), notes (text), added_at (timestamptz)
- [x] Add CHECK constraint on outreach_status: 'not_contacted', 'reached_out', 'responded', 'meeting_scheduled', 'committed', 'declined'
- [x] Add UNIQUE constraint on (list_id, contact_id) — no duplicate members
- [x] Apply migration via Supabase MCP tool (`mcp__supabase__apply_migration`)
- [x] Verify tables exist by querying information_schema
- [x] `cd job-matcher-ai && npm run build` passes (no code changes needed, but verify)

**Notes:**
- Use `gen_random_uuid()` for UUID defaults
- CASCADE on delete: removing a list removes its members
- This is database-only — API routes come in the next story

---

### US-009: Build Prospect Lists API Routes
**Priority:** 9
**Status:** [x] Complete

**Description:**
Create the API routes for CRUD operations on prospect lists.

**Acceptance Criteria:**
- [x] Create `app/api/network-intel/prospect-lists/route.ts`
  - GET: returns all lists with member counts
  - POST: creates a new list, optionally with initial contact_ids
- [x] Create `app/api/network-intel/prospect-lists/[id]/route.ts`
  - GET: returns list details with all members (joined with contact data)
  - PATCH: update list name/description, add/remove members, update member outreach_status
  - DELETE: delete the list (CASCADE deletes members)
- [x] All routes use Edge runtime
- [x] Proper error handling (404 for missing list, 400 for invalid input)
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- For GET list with members, join prospect_list_members with contacts table to get contact names/companies
- PATCH should support multiple operations: `{ add_contacts?: number[], remove_contacts?: number[], update_status?: { contact_id: number, status: string }[], name?: string, description?: string }`

---

### US-010: Build ListManager and PipelineStatus Components
**Priority:** 10
**Status:** [x] Complete

**Description:**
Create the UI components for managing prospect lists and tracking outreach pipeline status.

**Acceptance Criteria:**
- [x] Create `components/list-manager.tsx`
  - "Save to List" button in the action bar (above table)
  - Dropdown showing existing lists + "Create New List" option
  - Creating a list saves currently selected contacts
  - Loading a saved list re-populates the table with list members
- [x] Create `components/pipeline-status.tsx`
  - Inline dropdown on each contact row showing outreach status
  - Status options: Not Contacted, Reached Out, Responded, Meeting Scheduled, Committed, Declined
  - Color-coded: gray → blue → green → purple → gold → red
  - Changing status calls PATCH API to update
- [x] Wire both into NetworkCopilot
- [x] Add an ActionBar area between FilterBar and ContactsTable with: "Save to List" button, "Export CSV" button, selected count badge
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- Export CSV reuses the existing `exportContacts()` logic but client-side (or via a new API route)
- The PipelineStatus column only shows when viewing a saved list (not for fresh search results)

---

### US-011: Create Outreach Drafts Migration and Draft API Route
**Priority:** 11
**Status:** [x] Complete

**Description:**
Create the outreach_drafts table and the AI-powered draft generation endpoint.

**Acceptance Criteria:**
- [x] Create `outreach_drafts` table via Supabase MCP: id (UUID, PK), list_id (UUID, FK), contact_id (bigint), subject (text), body (text), tone (text, default 'warm_professional'), status (text, default 'draft'), sent_at (timestamptz), created_at (timestamptz)
- [x] Add CHECK constraint on status: 'draft', 'sent', 'failed'
- [x] Create `app/api/network-intel/outreach/draft/route.ts`
- [x] POST accepts: `{ list_id: string, contact_ids: number[], context?: string, tone?: string }`
- [x] For each contact: fetch outreach context via `getOutreachContext()`, then use Claude to draft a personalized email
- [x] Claude prompt includes: Justin's profile, contact's context, personalization hooks, tone, optional user context
- [x] Email drafts include: subject line, body text, sender context (Justin Steele, [role])
- [x] Save drafts to outreach_drafts table
- [x] Return generated drafts in response
- [x] Edge runtime
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- Generate drafts one at a time (not batch) to maintain quality
- Use Claude Sonnet 4.6 for draft generation
- CAN-SPAM compliance: drafts should include unsubscribe language at the bottom
- The tone options: warm_professional (default), formal, casual, networking, fundraising

---

### US-012: Build Outreach Send API Route (Resend)
**Priority:** 12
**Status:** [x] Complete

**Description:**
Create the email sending endpoint using Resend.

**Acceptance Criteria:**
- [x] Create `app/api/network-intel/outreach/send/route.ts`
- [x] POST accepts: `{ draft_id: string }` or `{ draft_ids: string[] }`
- [x] Fetch draft from outreach_drafts table
- [x] Send email via Resend API: from `justin@truesteele.com`, to contact's email
- [x] Update draft status to 'sent' and set sent_at timestamp on success
- [x] Update draft status to 'failed' on error
- [x] Return send results
- [x] Edge runtime (Resend has an Edge-compatible SDK)
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- Resend API key should be in Vercel env vars as `RESEND_API_KEY`
- Reference `scripts/email_campaigns/send_year_end_email.py` for the sending pattern
- HTML email format with basic styling
- Include unsubscribe link in footer (can use a placeholder URL for now)

---

### US-013: Build OutreachDrawer Component
**Priority:** 13
**Status:** [x] Complete

**Description:**
Create the UI for composing, previewing, editing, and sending outreach emails.

**Acceptance Criteria:**
- [x] Create `components/outreach-drawer.tsx`
- [x] Opens as a Sheet (slide-in from right, wider than contact detail)
- [x] Shows list of contacts to draft for (from selected contacts or list members)
- [x] "Generate Drafts" button calls outreach/draft API
- [x] Shows each draft with: recipient name, subject, body preview
- [x] Click on a draft to expand and edit (editable subject + body textarea)
- [x] "Send" button per draft, "Send All" button for batch
- [x] Sending shows loading state and success/error feedback
- [x] Wire into NetworkCopilot: "Draft Outreach" button in ActionBar opens the drawer
- [x] `cd job-matcher-ai && npm run build` passes

**Notes:**
- The drawer should show a compact list of drafts on the left and the expanded draft editor on the right
- Include a tone selector (warm_professional, formal, casual, networking, fundraising)
- Include optional "context" textarea for user to add specific context (e.g., "mention the upcoming gala")

---

### US-014: Polish UI and End-to-End Verification
**Priority:** 14
**Status:** [x] Complete

**Description:**
Final polish pass on the entire Network Copilot UI. Ensure everything works end-to-end and looks professional.

**Acceptance Criteria:**
- [x] All loading states have proper skeleton or spinner indicators
- [x] Empty states have helpful messages (no results, no lists, etc.)
- [x] Error states have user-friendly messages with retry options
- [x] Keyboard shortcuts: Enter to search in NLQueryBar, Escape to close sheets/drawers
- [x] Table row hover states and active states
- [x] Smooth transitions on filter changes, sheet open/close
- [x] Responsive layout works at common desktop widths (1024px - 1920px)
- [x] Consistent spacing, typography, and color usage throughout
- [x] No console errors or warnings in production build
- [x] `cd job-matcher-ai && npm run build` passes
- [x] Update `docs/NETWORK_INTELLIGENCE_SYSTEM.md` with Phase 3 (Copilot UI) completion notes

**Notes:**
- Don't over-engineer — focus on the core workflows being smooth and professional
- Check both light and dark mode (toggle via system preference)
- This is the last story — verify the complete flow: NL query → filters → table → select contacts → save list → draft outreach → send email
