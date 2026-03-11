# Project: UpTogether Sprint Tracker — Landing Page

## Overview
Build an editable, visually appealing project tracker landing page for the UpTogether x True Steele AI Strategy Sprint. The page should be Asana-like, publicly accessible (no auth required), and allow the UpTogether team (Cesar, Rachel, Ivanna) to track progress alongside Justin.

## Technical Context
- **Framework:** Next.js 15 (App Router) at `job-matcher-ai/`
- **UI:** shadcn/ui components (Radix primitives), Tailwind CSS, lucide-react icons
- **Fonts:** DM Sans (body), DM Serif Display (display headings), JetBrains Mono (mono)
- **Theme:** Warm teal primary (`168 50% 28%`), warm white background (`40 20% 98%`)
- **Existing components:** `components/ui/` — button, card, tabs, badge, checkbox, select, dropdown-menu, input, textarea, separator, tooltip, scroll-area, sheet
- **Database:** Supabase project `hjuvqpxvfrzwmlqzkpxh` (separate from main contacts DB)
  - URL: `https://hjuvqpxvfrzwmlqzkpxh.supabase.co`
  - Anon key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqdXZxcHh2ZnJ6d21scXprcHhoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYzNTUyMjUsImV4cCI6MjA3MTkzMTIyNX0.1ouwATKHkAUPNvs9uDUjy79nqAd1KF__WzK4AWceyOA`
  - Service role key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqdXZxcHh2ZnJ6d21scXprcHhoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM1NTIyNSwiZXhwIjoyMDcxOTMxMjI1fQ.AOYbPJPCITnRuGaYbQsbaJy_8fCGkmFL81DzM7h2NdM`
- **Auth:** Supabase Auth with Google OAuth, allowlist in `lib/auth-config.ts`. Middleware at `lib/supabase/middleware.ts` redirects unauthenticated users. `/projects` path must be excluded from auth.
- **Deploy:** `cd job-matcher-ai && npx vercel --prod --yes` to `steele-contacts.vercel.app`
- **Vercel account:** `justin-outdoorithm`, team `true-steele`

## Design Direction
- **Clean, warm, professional** — matches the existing app's teal/warm-white palette
- **NOT generic AI slop** — distinctive, production-grade design quality
- **Card-based sections** — each section in a collapsible card with count badge
- **Status colors:** todo=gray, in_progress=blue, done=green, blocked=red
- **Owner pills:** colored badges (Justin=teal, Cesar=amber, Rachel=violet, Ivanna=rose, UT Team=slate)
- **Typography:** DM Sans body, DM Serif Display for the main title only
- **Responsive:** Works on desktop and tablet
- **Light mode only** — no dark mode for this page

## Sprint Context (for seed data)
- **Engagement:** True Steele LLC consulting for UpTogether ($15K)
- **Goal:** Submit Google.org Impact Challenge application by April 3, 2026
- **Team:** Justin Steele (True Steele), Cesar Aleman (EVP Membership & Impact), Rachel Bernstein (Sr. Dir Product & Tech), Ivanna Neri (UT team)
- **Timeline:** March 10 - April 3, 2026 (4 weeks)
- **Key dates:** Kickoff Mar 10-11, SXSW Mar 12-15, App Draft Mar 21, JT Trip Mar 30-Apr 3, Deadline Apr 3
- **Deliverables:** AI Strategy Document, Google.org Application, Strategy Session
- **Application:** 8 sections, ~25 narrative responses (mostly 100 words each), submitted via Submittable
  - Section I: Org & Submitter Info (Q1-10, mostly factual — UT owns)
  - Section II: Impact (Q11-19, 8 narrative responses ≤100 words — heart of application)
  - Section III: Innovative Technology (Q20-26, note Q26 is 100 CHARACTERS not words)
  - Section IV: Feasibility (Q27-33)
  - Section V: Partnerships (Q34, government partnership + letter of support)
  - Section VI: Scalability (Q35-39)
  - Section VII: Budget & Timeline (Q41-51, $1-3M, 36 months, 3-5 milestones)
  - Section VIII: Ethics (Q52-57, checkboxes)

## User Stories

### US-001: Create Database Table and Run Migration
**Priority:** 1
**Status:** [x] Complete

**Description:**
Create the `project_tasks` table on the Supabase project `hjuvqpxvfrzwmlqzkpxh` using the Supabase REST API (SQL endpoint) or MCP tools. This is a separate Supabase project from the main contacts DB.

**Acceptance Criteria:**
- [ ] Create `project_tasks` table with columns: id (uuid PK), project_id (text), section (text), subsection (text), title (text), description (text), status (text default 'todo'), owner (text), due_date (date), sort_order (int), notes (text), created_at (timestamptz), updated_at (timestamptz)
- [ ] Enable RLS with a permissive policy (public read/write)
- [ ] Create index on project_id
- [ ] Verify table exists by querying it
- [ ] Typecheck passes

---

### US-002: Add Environment Variables and Supabase Client for Projects DB
**Priority:** 2
**Status:** [x] Complete

**Description:**
Add the new Supabase project's credentials as environment variables and create a dedicated Supabase client for the projects database, separate from the main contacts database.

**Acceptance Criteria:**
- [ ] Add `NEXT_PUBLIC_PROJECTS_SUPABASE_URL` and `NEXT_PUBLIC_PROJECTS_SUPABASE_ANON_KEY` and `PROJECTS_SUPABASE_SERVICE_ROLE_KEY` to `.env.local` in `job-matcher-ai/`
- [ ] Create `lib/supabase/projects-client.ts` — browser client using the projects DB credentials
- [ ] Create `lib/supabase/projects-server.ts` — server client using service role key for API routes
- [ ] Typecheck passes

---

### US-003: Create API Route for Project Tasks CRUD
**Priority:** 3
**Status:** [x] Complete

**Description:**
Create an API route at `/api/projects/[projectId]/tasks` that handles CRUD operations for project tasks using the projects Supabase client.

**Acceptance Criteria:**
- [ ] `GET /api/projects/uptogether/tasks` — returns all tasks grouped by section, ordered by sort_order
- [ ] `PATCH /api/projects/uptogether/tasks` — updates a task by id (accepts: status, notes, owner, title, description, due_date)
- [ ] `POST /api/projects/uptogether/tasks` — creates a new task
- [ ] `DELETE /api/projects/uptogether/tasks` — deletes a task by id
- [ ] All operations use the projects-server Supabase client (service role key)
- [ ] Typecheck passes
- [ ] Test with curl: GET returns empty array (no data yet)

---

### US-004: Update Middleware to Allow Public Access to /projects
**Priority:** 4
**Status:** [x] Complete

**Description:**
Update the auth middleware to skip authentication for the `/projects` path prefix, allowing the UpTogether team to access the tracker without logging in.

**Acceptance Criteria:**
- [ ] Edit `lib/supabase/middleware.ts` — add `pathname.startsWith('/projects')` to the public paths check on line 35
- [ ] Verify `/projects/uptogether` loads without redirect to login
- [ ] Verify other routes (e.g., `/tools/network-intel`) still require auth
- [ ] Typecheck passes

---

### US-005: Create Projects Layout
**Priority:** 5
**Status:** [x] Complete

**Description:**
Create a minimal layout for the `/projects` route that is standalone — no main app navigation, clean white background, simple wordmark header.

**Acceptance Criteria:**
- [ ] Create `app/projects/layout.tsx` with minimal layout
- [ ] White/warm background, max-width container (max-w-5xl centered)
- [ ] Small "True Steele Labs" wordmark in top-left corner (text, not image)
- [ ] No sidebar, no navigation from the main app
- [ ] Uses the same fonts (DM Sans, DM Serif Display) from root layout
- [ ] Typecheck passes

---

### US-006: Build Main Tracker Page — Structure and Data Fetching
**Priority:** 6
**Status:** [x] Complete

**Description:**
Build the main tracker page at `app/projects/uptogether/page.tsx`. This story focuses on the page structure, data fetching, and rendering all sections with read-only display. Inline editing comes in US-007.

**Important design notes:**
- Use the `/frontend-design` skill approach: distinctive, production-grade design quality. NOT generic shadcn defaults.
- Color palette: warm teal primary, warm whites, with accent colors for owners and status
- The page should feel like a premium project management tool

**Acceptance Criteria:**
- [ ] Create `app/projects/uptogether/page.tsx` as a client component
- [ ] Fetch tasks from `/api/projects/uptogether/tasks` on mount
- [ ] **Header section:** "UpTogether x True Steele" title (DM Serif Display), sprint phase badge, overall progress bar (% tasks done), team roster with initials avatars, key dates horizontal strip
- [ ] **Sprint Timeline section:** Visual timeline showing 4 weeks with current week highlighted, key milestones marked
- [ ] **Deliverables section:** 3 collapsible cards (AI Strategy Document, Google.org Application, Strategy Session) each showing sub-tasks as a checklist with status badges and owner pills
- [ ] **Application Tracker section:** 8 collapsible sub-sections mirroring Google.org app structure. Each question as a row with: checkbox, title, word limit badge, owner pill, status indicator
- [ ] **Materials from UT section:** Priority-tiered checklist (P1 Critical, P2 Important, P3 Nice-to-Have)
- [ ] **Meetings & Sessions section:** Log of meetings with date, attendees, notes (empty initially)
- [ ] **Open Questions section:** Numbered list with open/resolved status
- [ ] All sections are collapsible with chevron toggle and item count badge
- [ ] Page is responsive (desktop and tablet)
- [ ] Typecheck passes
- [ ] Page renders without errors at `localhost:3000/projects/uptogether`

---

### US-007: Add Inline Editing and Real-Time Persistence
**Priority:** 7
**Status:** [ ] Incomplete

**Description:**
Add interactive editing capabilities to the tracker page. All changes should persist immediately to Supabase via the API.

**Acceptance Criteria:**
- [ ] Click checkbox → toggles task between todo/done, PATCHes to API immediately
- [ ] Click status badge → cycles through todo → in_progress → done → blocked, PATCHes to API
- [ ] Click owner pill → shows dropdown to reassign (Justin, Cesar, Rachel, Ivanna, UT Team), PATCHes to API
- [ ] Click notes icon → expands inline textarea for notes, saves on blur
- [ ] "Add task" button at bottom of each section → inline form to create new task
- [ ] Optimistic UI updates (update state immediately, revert on error)
- [ ] Loading states for save operations (subtle spinner on the item being saved)
- [ ] Typecheck passes
- [ ] All interactions work end-to-end: click → UI updates → API call → data persisted

---

### US-008: Seed Data and Deploy
**Priority:** 8
**Status:** [ ] Incomplete

**Description:**
Create a seed script to populate all tasks from the Google Doc tracker, add Vercel env vars, and deploy.

**Acceptance Criteria:**
- [ ] Create `scripts/intelligence/seed_uptogether_tracker.py` that inserts all tasks:
  - 3 deliverables with sub-tasks (AI Strategy: 4 sub-tasks, Google.org App: 4 sub-tasks, Strategy Session: 2 sub-tasks)
  - Application questions: all ~25 questions across 8 sections, with owner (Justin or UT Team) and word limits in description
  - Materials needed: ~8 items across 3 priority tiers
  - Workplan phases: 4 weekly milestones
  - Open questions: 9 items
  - Meeting log: 1 entry (Kickoff Mar 10-11)
- [ ] Run the seed script successfully — all tasks appear in the database
- [ ] Add `NEXT_PUBLIC_PROJECTS_SUPABASE_URL`, `NEXT_PUBLIC_PROJECTS_SUPABASE_ANON_KEY`, `PROJECTS_SUPABASE_SERVICE_ROLE_KEY` to Vercel env vars
- [ ] Deploy to Vercel: `cd job-matcher-ai && npx vercel --prod --yes`
- [ ] Verify page loads at `steele-contacts.vercel.app/projects/uptogether`
- [ ] All tasks display correctly with proper sections, owners, and statuses
- [ ] Typecheck passes
