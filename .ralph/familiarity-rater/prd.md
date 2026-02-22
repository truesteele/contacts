# Project: Familiarity Rater - Mobile Contact Rating App

## Overview
Build a mobile-optimized web app (new route in the existing Next.js 15 app at `job-matcher-ai/`) that lets Justin rapidly rate every contact in his 2,498-person database on a 0-4 familiarity scale. This creates ground-truth "how well do I know this person" data for building prospect lists for Kindora and Outdoorithm.

## Taxonomy (Familiarity Scale)

| Level | Label | Description | Outreach Implication |
|-------|-------|-------------|---------------------|
| 0 | Don't Know | No memory of this person | Cold outreach only |
| 1 | Recognize | Met once/twice, need context to reconnect | Reference shared context |
| 2 | Acquaintance | Know each other, some shared history | Can reach out directly |
| 3 | Solid | Would take my call, mutual respect | Can make a direct ask |
| 4 | Close | Inner circle, frequent contact, high trust | Intro requests, investment asks |

## Technical Context
- **Framework:** Next.js 15 with App Router, TypeScript, Tailwind CSS, shadcn/ui
- **Database:** Supabase PostgreSQL (contacts table, ~2,498 rows)
- **Existing app:** `job-matcher-ai/` with tabs for Network Intelligence, etc.
- **Key columns already available:** `first_name`, `last_name`, `enrich_profile_pic_url`, `enrich_current_title`, `enrich_current_company`, `headline`, `linkedin_url`, `ai_proximity_score`, `ai_proximity_tier`, `enrich_schools`, `enrich_companies_worked`
- **No test suite exists** — skip test requirements, focus on typecheck passing
- **Quality gate:** `cd job-matcher-ai && npx tsc --noEmit` must pass

## User Stories

### US-001: Add familiarity_rating columns to contacts table
**Priority:** 1
**Status:** [x] Complete

**Description:**
Add two new columns to the contacts table to store the manual familiarity rating.

**Acceptance Criteria:**
- [x] Create SQL migration file at `supabase/migrations/` with timestamp prefix
- [x] Add `familiarity_rating` column (SMALLINT, nullable, CHECK constraint 0-4)
- [x] Add `familiarity_rated_at` column (TIMESTAMPTZ, nullable)
- [x] Run the migration against the live Supabase database using the Supabase MCP `apply_migration` tool or direct SQL execution
- [x] Verify the columns exist by querying the table
- [x] Update the `NetworkContact` interface in `job-matcher-ai/lib/supabase.ts` to include `familiarity_rating` and `familiarity_rated_at`
- [x] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

**Notes:**
- Use the Supabase MCP tools (execute_sql or apply_migration) to run the migration
- The Supabase project URL and service key are in the .env file at the project root

---

### US-002: Create API routes for rating contacts
**Priority:** 2
**Status:** [x] Complete

**Description:**
Create API endpoints to (a) fetch the next batch of unrated contacts and (b) save a familiarity rating for a contact.

**Acceptance Criteria:**
- [x] Create `GET /api/rate` route at `job-matcher-ai/app/api/rate/route.ts`
  - Returns batch of 20 unrated contacts (where `familiarity_rating IS NULL`)
  - Ordered by `ai_proximity_score DESC NULLS LAST` (people AI thinks Justin knows best come first)
  - Select fields: `id`, `first_name`, `last_name`, `enrich_profile_pic_url`, `enrich_current_title`, `enrich_current_company`, `headline`, `linkedin_url`, `ai_proximity_score`, `ai_proximity_tier`, `enrich_schools`, `enrich_companies_worked`, `connected_on`
  - Also return total unrated count and total rated count for progress tracking
- [x] Create `POST /api/rate` route in the same file
  - Accepts JSON body: `{ contact_id: number, rating: number }`
  - Validates rating is 0-4
  - Updates `familiarity_rating` and sets `familiarity_rated_at` to current timestamp
  - Returns success response
- [x] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

**Notes:**
- Follow existing API route patterns in `job-matcher-ai/app/api/network-intel/`
- Use the shared Supabase client from `lib/supabase.ts`

---

### US-003: Build the mobile-optimized rate page with contact card
**Priority:** 3
**Status:** [x] Complete

**Description:**
Create a new `/rate` page that displays one contact at a time as a card, optimized for mobile touch interaction. This is a standalone page (not a tab in the main app).

**Acceptance Criteria:**
- [x] Create page at `job-matcher-ai/app/rate/page.tsx`
- [x] Page is full-screen mobile layout (no desktop nav/tabs)
- [x] Shows a contact card with:
  - Profile photo (with fallback initials avatar if no photo)
  - Full name (large, prominent)
  - Current title @ company
  - LinkedIn headline (smaller, secondary)
  - "Connected on" date if available
  - AI proximity tier badge (e.g., "AI: Close" / "AI: Acquaintance") as a reference
  - Shared context section: shared schools and shared companies between the contact and Justin (Justin's schools: HBS, HKS, UVA; Justin's companies: Kindora, Google.org, Year Up, Bridgespan, Bain, True Steele, Outdoorithm)
- [x] Card is vertically centered on mobile, max-width ~400px
- [x] Clean, minimal design using Tailwind — white card on subtle gray background
- [x] Shows loading skeleton while fetching contacts
- [x] Fetches contacts from `GET /api/rate` on mount
- [x] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

**Notes:**
- This should feel like a flashcard app — focus is entirely on the one contact
- Keep it simple and fast. No sidebar, no navigation, no tabs.
- Add a small back-arrow link to "/" at the top-left for navigation back to main app
- Use viewport meta tag for proper mobile scaling (Next.js app layout should handle this)

---

### US-004: Build rating buttons and card flow interaction
**Priority:** 4
**Status:** [x] Complete

**Description:**
Add the 5 rating tap targets below the card, wire up the rating flow (tap → save → animate out → next card), and add undo/skip functionality.

**Acceptance Criteria:**
- [x] 5 large tap buttons below the card, one for each familiarity level (0-4)
  - Each button shows the level number and label (e.g., "0 Don't Know", "1 Recognize", etc.)
  - Buttons are full-width, stacked vertically, minimum 48px tall for easy touch
  - Color-coded: gray(0) → blue(1) → green(2) → orange(3) → purple(4) or similar progression
- [x] Tapping a rating button:
  - Immediately sends POST to `/api/rate` with the contact_id and rating
  - Card animates out (fade + slide up, ~200ms)
  - Next card slides in from below
  - Optimistic UI — don't wait for server response to show next card
- [x] Undo button (top-right or floating)
  - Reverts the last rating (re-saves with null or previous value)
  - Brings back the previous card
  - Only needs to support undoing the last 1 rating (not full history)
- [x] Skip button
  - Moves to next card without saving a rating
  - Skipped contacts go to the end of the current batch
- [x] Progress bar at top of page showing "X / 2,498 rated" with percentage
  - Updates after each rating
- [x] When batch is exhausted (all 20 rated/skipped), auto-fetch next batch
- [x] When all contacts are rated, show a "Done!" completion message
- [x] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

**Notes:**
- Optimistic UI is key — the app should feel instant. Fire-and-forget the POST.
- Use React state to manage the card queue locally
- Keyboard shortcuts are nice-to-have but not required (0-4 keys to rate)

---

### US-005: Add stats dashboard and session controls
**Priority:** 5
**Status:** [x] Complete

**Description:**
Add a collapsible stats panel and session controls so Justin can track progress and filter what he's rating.

**Acceptance Criteria:**
- [x] Stats bar (always visible, compact) showing:
  - Total rated / total contacts
  - Percentage complete
  - Session count (how many rated in this session)
  - Breakdown by level: how many at each familiarity level (0/1/2/3/4)
- [x] Stats bar is collapsible — tap to expand/collapse the breakdown detail
- [x] Filter control to choose which contacts to rate:
  - "All unrated" (default)
  - "AI: Close first" (sort by ai_proximity_score DESC) — default sort
  - "AI: Distant first" (sort by ai_proximity_score ASC)
  - "Recently connected" (sort by connected_on DESC)
  - "Re-rate" mode — show already-rated contacts to revise ratings
- [x] Update the GET /api/rate endpoint to accept `sort` and `mode` query params
- [x] LinkedIn profile link — small icon on the card that opens their LinkedIn in a new tab (for when you need to jog your memory)
- [x] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

**Notes:**
- Stats should update in real-time as ratings are made (local state, not re-fetching)
- Keep the stats compact — this is a mobile app, screen real estate is precious

---

### US-006: Polish UI and end-to-end verification
**Priority:** 6
**Status:** [x] Complete

**Description:**
Final polish pass — ensure the app works end-to-end, looks great on mobile, and handles edge cases.

**Acceptance Criteria:**
- [x] Test the full flow: open /rate → see card → tap rating → card animates → next card appears
- [x] Verify ratings persist in Supabase (query a few rated contacts)
- [x] Handle edge cases:
  - Contact with no photo (show initials)
  - Contact with no title/company (show "—" or hide section)
  - Contact with no AI score (show "Not scored" instead of badge)
  - Empty batch (all contacts rated)
  - Network error on POST (queue and retry, or show toast)
- [x] Add subtle transition animations (card enter/exit)
- [x] Ensure touch targets are at least 44px per Apple HIG guidelines
- [x] Responsive: works on iPhone SE (375px) through iPad
- [x] Add keyboard shortcuts: 0-4 keys map to ratings, 'u' for undo, 's' for skip (for desktop use)
- [x] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

**Notes:**
- This is the final story. Make sure everything works together smoothly.
- Run `cd job-matcher-ai && npx tsc --noEmit` as final check.
