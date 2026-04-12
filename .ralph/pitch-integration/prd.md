# Project: Pitch Integration in Discovery Tab

## Overview

Integrate pitch review, bookmarking, notes, and Opus 4.6 outreach generation directly into the Discovery tab. The Discovery tab becomes the single surface for browsing podcasts, flagging favorites, taking notes, generating pitches, and managing outreach — all in one flow.

## Technical Context

- **Tech Stack:** Next.js 15 App Router, shadcn/Radix UI, Supabase PostgreSQL, Anthropic SDK
- **Existing patterns:** Pitch Review tab (PitchCard component), generate API (Claude Sonnet 4.6), pitches API (GET/PATCH)
- **Key files:**
  - `job-matcher-ai/app/tools/podcast-outreach/page.tsx` — main UI (~1250 lines)
  - `job-matcher-ai/app/api/podcast/pitches/route.ts` — GET + PATCH
  - `job-matcher-ai/app/api/podcast/generate/route.ts` — Claude pitch generation
  - `job-matcher-ai/app/api/podcast/discover/route.ts` — Discovery data
  - `job-matcher-ai/app/api/podcast/detail/route.ts` — Detail data
  - `docs/Writing/SALLY_VOICE_GUIDE.md` — Sally's voice
  - `docs/Sally/SALLY_EMAIL_PERSONA.md` — Sally's email patterns
  - `docs/Justin/JUSTIN_EMAIL_PERSONA.md` — Justin's email patterns
  - `docs/Writing/Signs of AI Writing.md` — Anti-AI rules

## User Stories

### US-001: Database Migration — Add bookmark and notes to pitches
**Priority:** 1
**Status:** [x] Complete

**Description:**
Add `is_bookmarked` and `user_notes` columns to `podcast_pitches` table.

**Acceptance Criteria:**
- [ ] Apply migration via Supabase MCP `apply_migration`:
  ```sql
  ALTER TABLE podcast_pitches
    ADD COLUMN is_bookmarked boolean DEFAULT false,
    ADD COLUMN user_notes text DEFAULT '';
  ```
- [ ] Verify columns exist: `SELECT column_name FROM information_schema.columns WHERE table_name='podcast_pitches' AND column_name IN ('is_bookmarked','user_notes')`

---

### US-002: Pitches API — PATCH for bookmark/notes + POST for pitch creation
**Priority:** 2
**Status:** [ ] Incomplete

**Description:**
Extend the pitches API to support bookmarking, notes, and creating new pitch records.

**File:** `job-matcher-ai/app/api/podcast/pitches/route.ts`

**Acceptance Criteria:**
- [ ] PATCH handler accepts `is_bookmarked` (boolean) and `user_notes` (string) in addition to existing fields
- [ ] New POST handler: accepts `{ podcast_target_id, speaker_slug, is_bookmarked?, user_notes? }`, resolves speaker_profile_id from slug, creates minimal `podcast_pitches` row (no fit data), returns `{ id, pitch_id }`
- [ ] POST handler upserts — if pitch record already exists for that podcast+speaker combo, returns existing ID instead of creating duplicate
- [ ] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`

---

### US-003: Discover API — Return bookmark/notes + bookmarked filter
**Priority:** 3
**Status:** [ ] Incomplete

**Description:**
Update the discover API to include bookmark/notes data in pitch results and support filtering by bookmarked.

**File:** `job-matcher-ai/app/api/podcast/discover/route.ts`

**Acceptance Criteria:**
- [ ] Speaker-driven path: add `is_bookmarked, user_notes` to the pitch select fields (line ~58, currently selects `podcast_target_id, fit_tier, fit_score, fit_rationale, topic_match, pitch_status, subject_line, pitch_body`)
- [ ] New query param `bookmarked=true`: when set, filter pitches to `is_bookmarked = true` only
- [ ] Pitch data flows through to response correctly (verify via API call)
- [ ] Typecheck passes

---

### US-004: Generate API — Upgrade to Opus 4.6 with full voice guides
**Priority:** 4
**Status:** [ ] Incomplete

**Description:**
Upgrade the pitch generation API from Sonnet 4.6 to Opus 4.6, embed comprehensive voice guides, add force flag for regeneration, and auto-create pitch records.

**File:** `job-matcher-ai/app/api/podcast/generate/route.ts`

**Changes:**
1. Change MODEL from `'claude-sonnet-4-6'` to `'claude-opus-4-6'`
2. Replace abbreviated voice guides with full versions (read from the docs referenced below)
3. Add `force?: boolean` to request body — when true, skip the `!p.pitch_body` filter to allow regeneration
4. Auto-create pitch record: when called with `podcast_id` + `speaker_slug` and no pitch exists, create a minimal pitch row first, then generate into it
5. Include podcast_profile data (about, hosts, audience) in the user prompt when available

**Voice guide sources (READ these files and embed the key content):**
- Sally: `docs/Writing/SALLY_VOICE_GUIDE.md` + `docs/Sally/SALLY_EMAIL_PERSONA.md`
- Justin: `docs/Justin/JUSTIN_EMAIL_PERSONA.md`
- Anti-AI: `docs/Writing/Signs of AI Writing.md`

**Sally voice key elements to embed:**
- Direct, opinionated, specific, occasionally poetic
- Scene-first openings (specific moment, not topic overview)
- Named People Rule: every story gets a real name
- Contrast Signature: "We didn't have X. We had Y." / "It's not X. It's Y."
- Mantras: "Leave anyway", "Camp as it comes", "Take up space", "Come alive"
- Through-line word: "belonging"
- Sentence rhythm: short fragment, then longer sentence, fragment carries weight
- Em dashes OK (max 1 per email), contractions, fragments
- Word replacements: "journey" > "trip/season/stretch", "passion" > "obsession/fixation", "community" > name the actual group
- Email patterns: invitation-centered asks, 150-250 words, camper quotes as crown jewels
- Closing: circle back or reframe, never logistics

**Justin voice key elements to embed:**
- Warm professional, punchy 10-20 word sentences
- "Hi [Name]," never "Dear"; sign off "Justin" never "Best regards"
- "Would love [X] if you have it" ask signature
- Always "we" / "Sally and I" for OC
- Parenthetical asides OK, Calendly in follow-up NOT cold pitch
- No em dashes EVER. Commas, periods, colons instead.
- Specific experience references, not abstract principles

**Outreach best practices to embed in prompt:**
- Reference a SPECIFIC recent episode by name (#1 differentiator)
- 3 talking points framed as audience benefits, not speaker credentials
- Soft CTA: "Would love to explore" / "Happy to chat"
- Subject line under 50 chars, specific not clickbait
- 150-200 words body
- Sign off with name only

**Acceptance Criteria:**
- [ ] MODEL constant is `'claude-opus-4-6'`
- [ ] `buildSystemPrompt()` returns comprehensive voice guide (~1000+ tokens for each speaker)
- [ ] `force` flag works: calling with `force: true` regenerates existing pitches
- [ ] Auto-create: calling with `podcast_id` + `speaker_slug` when no pitch exists creates one and generates into it
- [ ] `buildUserPrompt()` includes podcast_profile data (about, host bios, audience) when available
- [ ] Typecheck passes

---

### US-005: TypeScript types + PodcastDetailPanel — Pitch section with bookmark, notes, generate
**Priority:** 5
**Status:** [ ] Incomplete

**Description:**
Update TypeScript interfaces and add a Pitch & Outreach section to the PodcastDetailPanel in the Discovery tab.

**File:** `job-matcher-ai/app/tools/podcast-outreach/page.tsx`

**Type updates:**
- `PodcastPitch` interface: add `id: number`, `is_bookmarked: boolean`, `user_notes: string`, `subject_line_alt: string | null`, `episode_reference: string | null`, `suggested_topics: string[] | null`, `generated_at: string | null`, `model_used: string | null`
- `PodcastDetailData.pitch`: update to return full pitch data (currently partial)
- `Podcast.pitch` (from discover): add `is_bookmarked: boolean | null`, `user_notes: string | null`

**PodcastDetailPanel additions (below existing content, lines 523-732):**

Add a new section after the existing grid (About/Host/Fit/Episodes):

1. **Bookmark + Notes row:**
   - Bookmark toggle: star/heart icon button. Calls PATCH `/api/podcast/pitches` with `is_bookmarked`. If no pitch record exists, calls POST first to create one, then PATCH.
   - Notes: expandable textarea, auto-saves on blur via PATCH. If no pitch record, creates one on first note save.

2. **Outreach Email section:**
   - "Generate Pitch" button (shown when no `pitch_body`). Calls POST `/api/podcast/generate` with `{ podcast_id: X, speaker_slug: Y }`. Shows loading spinner.
   - When pitch exists: inline editable subject line (Input) and body (Textarea). Save on blur via PATCH.
   - Alt subject line shown below primary (from `subject_line_alt`)
   - Episode reference shown as context
   - Suggested topics listed

3. **Status actions row:**
   - Buttons: Approve, Reject, Regenerate (calls generate with `force: true`)
   - Send dropdown: "Create Gmail Draft", "Copy to Clipboard"
   - Status badge showing current pitch_status

**State management:**
- Local state for editing (subject, body, notes, bookmark)
- API calls on user actions (blur for text, click for buttons)
- `fetchDetail()` called after generate/save to refresh data

**Acceptance Criteria:**
- [ ] TypeScript interfaces updated with all new pitch fields
- [ ] PodcastDetailPanel shows bookmark toggle (persists via API)
- [ ] PodcastDetailPanel shows notes textarea (persists via API)
- [ ] "Generate Pitch" button calls generate API and populates subject/body
- [ ] Subject and body are inline-editable, save on blur
- [ ] Approve/Reject/Regenerate buttons work
- [ ] Send dropdown with "Create Gmail Draft" and "Copy to Clipboard" options
- [ ] Loading states for generate and save operations
- [ ] Typecheck passes

---

### US-006: Discovery tab — Bookmarked filter + indicators in table
**Priority:** 6
**Status:** [ ] Incomplete

**Description:**
Add bookmarked filter and visual indicators to the Discovery tab table.

**File:** `job-matcher-ai/app/tools/podcast-outreach/page.tsx`

**Changes:**

1. **Bookmarked filter:** Add checkbox in the controls row (near "Active in 2026 only"): "Bookmarked only". When checked, passes `bookmarked=true` to discover API. Add `bookmarkedOnly` state (boolean, default false) and wire to fetchPodcasts params.

2. **Bookmark indicator in table rows:** In the Podcast column (td), show a small filled star icon before the title for bookmarked podcasts (`podcast.pitch?.is_bookmarked === true`).

3. **Pitch status indicator:** After the Fit badge column, or in the Score column, show a small status badge if the podcast has a pitch with status other than null (draft, approved, sent, etc.).

4. **Update colSpan** if new columns added (currently `colSpan={9}` on the expanded row).

**Acceptance Criteria:**
- [ ] "Bookmarked only" checkbox works and filters results via API
- [ ] Bookmarked podcasts show star icon in table row
- [ ] Pitch status badge visible in table row when pitch has a status
- [ ] Page resets to 1 when bookmarked filter changes
- [ ] Typecheck passes

---

### US-007: Deploy to Vercel
**Priority:** 7
**Status:** [ ] Incomplete

**Description:**
Deploy the updated application to Vercel production.

**Acceptance Criteria:**
- [ ] Typecheck passes: `cd job-matcher-ai && npx tsc --noEmit`
- [ ] Build succeeds: `cd job-matcher-ai && npx next build` (or verify via deploy)
- [ ] Deploy: `cd job-matcher-ai && npx vercel --prod --yes --scope true-steele`
- [ ] Verify deployed app loads at steele-contacts.vercel.app
- [ ] Verify Discovery tab works with new features (bookmark, notes, generate)
