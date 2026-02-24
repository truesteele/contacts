# Project: Come Alive 2026 — Campaign Command Center

## Overview

Build a campaign management frontend at `/tools/campaign` for the Come Alive 2026 fundraising campaign. The data pipeline is complete: 317 contacts scaffolded, 25 personal outreach messages (Opus 4.6), 292 campaign copy variants (GPT-5 mini) — all stored in `campaign_2026` JSONB column in Supabase. Justin needs a UI to review/edit messages, send emails via Resend, track donations, and manage the campaign day-by-day.

## Technical Context

- **Framework:** Next.js 15, React 19, TypeScript
- **UI:** shadcn/radix components (Badge, Button, Card, Input, Textarea, Select, Sheet, ScrollArea, Tabs, Separator) + Tailwind CSS + lucide-react icons
- **Data:** Supabase `contacts` table, `campaign_2026` JSONB column
- **Email:** Resend (already installed `resend@6.9.2`, existing send route at `app/api/network-intel/outreach/send/route.ts`)
- **App dir:** `job-matcher-ai/` (all paths below are relative to this)

### Key Existing Files

| File | Why It Matters |
|:--|:--|
| `app/tools/ask-readiness/page.tsx` | **Primary pattern** — filterable contact table with tier badges, search, sort, filter dropdowns, expandable rows, contact detail sheet |
| `app/api/network-intel/ask-readiness/route.ts` | **API pattern** — Supabase pagination, JSONB flattening, edge runtime |
| `app/api/network-intel/outreach/send/route.ts` | **Resend pattern** — `textToHtml()`, Resend client setup, `FROM_EMAIL`, `REPLY_TO`, send with status tracking |
| `components/contact-detail-sheet.tsx` | **Detail sheet pattern** — side sheet with rich contact data display |
| `components/outreach-drawer.tsx` | **Edit+send pattern** — draft editing with Textarea, send button, status tracking |
| `components/pipeline/deal-detail-sheet.tsx` | **Editable sheet pattern** — inline editing in a side sheet |
| `lib/supabase.ts` | Supabase client using `SUPABASE_SERVICE_KEY` |
| `components/ui/*` | All shared UI components |

### Data Structure: `campaign_2026` JSONB

```json
{
  "scaffold": {
    "persona": "believer|impact_professional|network_peer",
    "persona_confidence": 82,
    "campaign_list": "A|B|C|D",
    "capacity_tier": "leadership|major|mid|base|community",
    "primary_ask_amount": 5000,
    "motivation_flags": ["relationship", "mission_alignment"],
    "primary_motivation": "relationship",
    "lifecycle_stage": "new|prior_donor|lapsed",
    "lead_story": "valencia|carl|...",
    "opener_insert": "...",
    "personalization_sentence": "...",
    "thank_you_variant": "...",
    "text_followup": "..."
  },
  "personal_outreach": {
    "subject_line": "quick thing — before I send the big ask",
    "message_body": "Hey Tyler — ...",
    "channel": "email|text",
    "follow_up_text": "...",
    "thank_you_message": "...",
    "internal_notes": "..."
  },
  "campaign_copy": {
    "pre_email_note": "...",
    "text_followup_opener": "...",
    "text_followup_milestone": "...",
    "thank_you_message": "...",
    "thank_you_channel": "text|email",
    "email_sequence": [1, 2, 3]
  },
  "send_status": {},
  "donation": null,
  "responded_at": null
}
```

- List A (25 contacts) have `personal_outreach` — personalized messages from Opus 4.6
- Lists B-D (292 contacts) have `campaign_copy` — text follow-ups, thank-yous from GPT-5 mini
- All 317 have `scaffold` — persona, ask amount, motivation, lifecycle, story

### Resend Configuration

- From: `Justin Steele <justin@outdoorithmcollective.org>`
- Reply-to: `justinrsteele@gmail.com`
- Env var: `RESEND_API_KEY_OC`
- Existing `textToHtml()` in `app/api/network-intel/outreach/send/route.ts` — converts plain text to styled HTML

### Contact Email Resolution

Contacts may have email in: `email`, `personal_email`, or `work_email` fields. Use `personal_email || email || work_email` as priority order (personal email preferred for fundraising).

---

## User Stories

### US-001: Campaign API — Fetch contacts
**Status:** [x] Complete

Create `app/api/network-intel/campaign/route.ts`

**Acceptance Criteria:**
- [ ] `GET /api/network-intel/campaign` returns all contacts with `campaign_2026` data
- [ ] Selects: `id, first_name, last_name, company, position, email, personal_email, work_email, campaign_2026`
- [ ] Flattens key fields from `campaign_2026` JSONB for easy frontend consumption:
  - `list` (scaffold.campaign_list)
  - `persona` (scaffold.persona)
  - `ask_amount` (scaffold.primary_ask_amount)
  - `capacity_tier` (scaffold.capacity_tier)
  - `lifecycle` (scaffold.lifecycle_stage)
  - `motivation` (scaffold.primary_motivation)
  - `channel` (personal_outreach.channel or campaign_copy.thank_you_channel)
  - `subject` (personal_outreach.subject_line or null)
  - `has_outreach` (boolean)
  - `has_copy` (boolean)
  - `send_status` (from send_status object or null)
  - `donation` (from donation object or null)
- [ ] Returns `stats` object: counts by list, persona, capacity tier, lifecycle, send status
- [ ] Uses Supabase pagination for >1000 rows (follow ask-readiness route pattern)
- [ ] `export const runtime = 'edge';`
- [ ] Verify: `curl localhost:3000/api/network-intel/campaign | jq '.total'` returns 317

### US-002: Campaign API — Update contact + Record donation
**Status:** [x] Complete

Create `app/api/network-intel/campaign/[id]/route.ts`

**Acceptance Criteria:**
- [ ] `GET /api/network-intel/campaign/[id]` returns single contact with full `campaign_2026` JSONB (not flattened)
- [ ] `PATCH /api/network-intel/campaign/[id]` updates fields in `campaign_2026` JSONB
  - Body format: `{ "section": "personal_outreach", "field": "message_body", "value": "new text" }`
  - Uses Supabase raw SQL with `jsonb_set()` for nested updates
  - Preserves all other JSONB keys
- [ ] `PATCH` also supports recording donations: `{ "section": "donation", "value": { "amount": 5000, "donated_at": "2026-03-01", "source": "personal_outreach" } }`
- [ ] `PATCH` also supports recording response: `{ "section": "responded_at", "value": "2026-02-25" }`
- [ ] Returns updated contact data after patch
- [ ] `export const runtime = 'edge';`

### US-003: Campaign page — Dashboard tab + List A tab
**Status:** [x] Complete

Create `app/tools/campaign/page.tsx` and add to tools navigation.

**Acceptance Criteria:**
- [ ] Page at `/tools/campaign` with page header (back arrow, icon, title "Campaign")
- [ ] Uses `Tabs` component (from `@radix-ui/react-tabs` via `components/ui/tabs.tsx`) with tabs: Dashboard, List A, Lists B-D, Activity
- [ ] **Dashboard tab:**
  - Campaign progress: "$X raised of $100K" with progress bar
  - Donor count and total donated (from contacts with `donation` data)
  - Summary cards: List A (X/25 sent), total contacts by list
  - Phase indicator based on current date vs timeline
- [ ] **List A tab:**
  - Table of 25 contacts showing: #, Name, Company, Ask ($), Channel, Subject, Status
  - Status shows: draft (gray), sent (blue), responded (yellow), donated (green)
  - Rows are clickable — sets `selectedContactId` for the detail sheet
  - Sorted by ask amount descending (leadership first)
- [ ] Fetches from `GET /api/network-intel/campaign` on mount (follow ask-readiness pattern)
- [ ] Loading state, error state
- [ ] Add `/tools/campaign` link to the page header navigation (look at how pipeline is linked — check if there's a nav component or just direct Links)

### US-004: Message detail sheet
**Status:** [x] Complete

Create `components/campaign/message-detail-sheet.tsx`

**Acceptance Criteria:**
- [ ] Side sheet component using `Sheet` from `components/ui/sheet.tsx`
- [ ] Props: `contactId: number | null`, `open: boolean`, `onOpenChange: (open: boolean) => void`, `onUpdated: () => void`
- [ ] Fetches full contact data from `GET /api/network-intel/campaign/[id]`
- [ ] **For List A contacts (personal_outreach):** Shows editable fields:
  - Subject line (Input)
  - Message body (Textarea, ~8 rows)
  - Channel (Badge, read-only)
  - Follow-up text (Textarea, ~3 rows)
  - Thank-you message (Textarea, ~3 rows)
  - Internal notes (Textarea, ~3 rows)
  - Scaffold summary: persona, ask amount, motivation, lead story (read-only Badges)
- [ ] **For Lists B-D contacts (campaign_copy):** Shows editable fields:
  - Pre-email note (Textarea, only if lifecycle is prior_donor or lapsed)
  - Text follow-up opener (Textarea, ~2 rows)
  - Text follow-up milestone (Textarea, ~2 rows)
  - Thank-you message (Textarea, ~3 rows)
  - Thank-you channel (Badge, read-only)
  - Scaffold summary: persona, ask amount, motivation, lead story (read-only Badges)
- [ ] "Save" button calls `PATCH /api/network-intel/campaign/[id]` for each changed field
- [ ] Shows save confirmation (brief success state on button)
- [ ] Calls `onUpdated()` after successful save to refresh the parent table
- [ ] Wire into the campaign page: clicking a row in List A or Lists B-D opens this sheet

### US-005: Lists B-D tab with filters
**Status:** [x] Complete

Add Lists B-D tab to the campaign page.

**Acceptance Criteria:**
- [ ] Table of 292 contacts showing: Name, List, Persona, Ask ($), Lifecycle, Status
- [ ] Filter bar with dropdowns (follow ask-readiness pattern):
  - List: All, B, C, D
  - Persona: All, Believer, Impact Professional, Network Peer
  - Capacity: All, Leadership, Major, Mid, Base, Community
  - Lifecycle: All, New, Prior Donor, Lapsed
- [ ] Search box filters by name, company
- [ ] Sort by: name, list, ask amount, persona
- [ ] Rows are clickable — opens message detail sheet
- [ ] Status column shows send status for each email type (draft/sent)
- [ ] Count display: "Showing X of 292 contacts"

### US-006: Campaign send API route
**Status:** [x] Complete

Create `app/api/network-intel/campaign/send/route.ts`

**Acceptance Criteria:**
- [ ] `POST /api/network-intel/campaign/send`
- [ ] Body: `{ "contact_ids": [1,2,3], "email_type": "personal_outreach" | "pre_email_note" | "email_1" }`
- [ ] Resend client setup: `new Resend(process.env.RESEND_API_KEY_OC)`
- [ ] From: `Justin Steele <justin@outdoorithmcollective.org>`
- [ ] Reply-to: `justinrsteele@gmail.com`
- [ ] **For `personal_outreach`:** reads `campaign_2026.personal_outreach.subject_line` and `.message_body` from each contact
- [ ] **For `pre_email_note`:** reads `campaign_2026.campaign_copy.pre_email_note` — subject: "quick note before the big ask"
- [ ] **For `email_1`:** uses a template (hardcoded from COME_ALIVE_2026_Campaign.md Email 1) with per-contact `opener_insert` and `personalization_sentence` from scaffold
- [ ] Email to: `personal_email || email || work_email` (resolve best email per contact)
- [ ] Converts text to HTML using `textToHtml()` (copy from existing outreach/send/route.ts)
- [ ] After successful send, updates `campaign_2026.send_status.<email_type>` with `{ "sent_at": ISO, "resend_id": "..." }`
- [ ] Returns: `{ results: [...], total_sent: N, total_failed: N }`
- [ ] Sequential sends (not parallel) to avoid rate limits
- [ ] Skips contacts already sent for that email type (check `send_status`)
- [ ] `export const runtime = 'edge';`

### US-007: Send buttons + status tracking in UI
**Status:** [x] Complete

Add send functionality to the campaign page.

**Acceptance Criteria:**
- [ ] **List A tab:** "Send" button per contact row (only for email channel contacts)
  - Disabled if already sent
  - Shows spinner while sending
  - Updates row status on success
  - Confirm dialog before send: "Send to {name} at {email}?"
- [ ] **List A tab:** "Send All Unsent" button at top — sends all unsent List A emails
- [ ] **Lists B-D tab:** "Send Pre-Email Notes" button — sends pre_email_note to all prior_donor/lapsed contacts
- [ ] **Lists B-D tab:** "Send Email 1" button — sends email_1 to all contacts in Lists B-D
- [ ] Send status visual indicators on each contact row:
  - Gray dot = not sent
  - Blue dot = sent
  - Green dot = donated
  - Yellow dot = responded
- [ ] All send buttons call `POST /api/network-intel/campaign/send`
- [ ] After send, refresh contact data from API

### US-008: Activity tab + donation recording
**Status:** [x] Complete

Add Activity tab and donation recording to the campaign page.

**Acceptance Criteria:**
- [ ] **Activity tab** shows a reverse-chronological list of campaign events:
  - Emails sent (name, type, timestamp)
  - Donations recorded (name, amount, timestamp)
  - Responses recorded (name, timestamp)
  - Data sourced from: iterate all contacts, collect events from `send_status`, `donation`, `responded_at`
- [ ] **Record Donation form** in Activity tab:
  - Contact search/select (name search → dropdown of campaign contacts)
  - Amount (number input, pre-filled from contact's ask_amount)
  - Date (date input, defaults to today)
  - Source dropdown: personal_outreach, email_1, email_2, email_3, other
  - "Record" button calls `PATCH /api/network-intel/campaign/[id]` with donation data
- [ ] **Record Response** quick action: button on each contact row to mark "responded"
- [ ] Dashboard tab updates live: progress bar, donor count, total raised
- [ ] Dashboard shows "X donors, $Y raised, Z% of $100K goal"
