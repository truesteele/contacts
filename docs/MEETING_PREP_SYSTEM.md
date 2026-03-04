# Automated Meeting Prep System

**Author:** Justin Steele / Claude
**Created:** March 3, 2026
**Status:** Production

---

## 1. Why This System Exists

As a tech founder running three ventures (Kindora, Outdoorithm Collective, True Steele Labs) and an active consultant/networker, Justin takes 3-8 external meetings per day across 5 Google Calendar accounts. Each meeting involves different people, organizations, and strategic angles. Walking into a meeting cold wastes opportunity; walking in prepared wins business, deepens relationships, and compounds network value.

This system automates the entire meeting prep workflow:
1. Sweep all 5 Google calendars at 7am daily
2. Identify which meetings need prep (external, non-recurring, non-excluded)
3. Research every attendee (contacts DB + LinkedIn + web)
4. Generate a tailored prep memo for each meeting
5. Create a Google Doc with all memos
6. Attach the doc to each calendar event

The result: Justin opens any calendar event, clicks the attachment, and has a full briefing ready.

---

## 2. Research: What Makes a Great Meeting Prep Memo

### Sources Consulted

| Source | Key Insight | URL |
|--------|------------|-----|
| **Consulting Success** | Spend 15-20 min per meeting on 3-7 bullet points per agenda phase. Preparation separates good consultants from great ones. | [consultingsuccess.com](https://www.consultingsuccess.com/consulting-meeting) |
| **River (Briefing Memos)** | Best briefing memos are 1 page max, start with your recommendation, present options with trade-offs. | [rivereditor.com](https://rivereditor.com/guides/how-to-write-briefing-memos-executives-officials-2026) |
| **ClickUp (Meeting Memos)** | Every memo needs: date/time/place, attendees (who leads), agenda items, desired outcomes. | [clickup.com](https://clickup.com/blog/meeting-memo/) |
| **Fellow (2026 Guide)** | High-performing teams use AI meeting agents for documentation. Focus on what to prepare, not what to record. | [fellow.ai](https://fellow.ai/blog/meeting-minutes-example-and-best-practices/) |
| **Notion (Startup Template)** | Meeting notes should be structured around decisions needed, not transcription. | [notion.com](https://www.notion.com/templates/meeting-notes-startup) |

### Key Principles Adopted

1. **Actionable over informational.** The memo isn't a dossier. It's a playbook. Every section should tell Justin what to DO, not just what to KNOW.

2. **Strategic angle always present.** Every meeting connects to one of Justin's ventures. The memo identifies which one and what to explore.

3. **Relationship context is paramount.** For a networker, knowing your history with someone (last email, shared school, mutual contacts) is more valuable than their resume.

4. **Personalization hooks > generic talking points.** "You were both at Bain SF" is 10x more useful than "Ask about their career journey."

5. **Landmines prevent disasters.** Knowing what NOT to say or do can save a relationship. Every memo includes warnings.

6. **One page per meeting.** Following River's briefing memo guidance: scannable in 2 minutes, actionable immediately.

---

## 3. Memo Template Structure

Each meeting memo follows this structure:

```
## Meeting: [Title]
**Time:** [Start - End] ([Duration])
**Location:** [Physical location or Zoom link]
**Account:** [Which Google account / entity]

### Attendees
| Name | Title | Organization | In DB? | Relationship |
|------|-------|-------------|--------|-------------|

### Key Profiles
For each attendee:
- Current role and career arc
- Shared background with Justin (schools, employers, interests, boards)
- Recent LinkedIn/web activity
- Communication history summary

### Meeting Purpose & Context
- Stated agenda (from calendar description/Calendly notes)
- Organization background
- What prompted this meeting

### Strategic Angle
- Which venture is relevant (Kindora / True Steele Labs / Outdoorithm)
- What Justin can offer
- What Justin wants to get

### Talking Points (5 max)
- Specific, actionable, with personalization hooks
- Reference shared experiences, mutual connections, or recent events

### Landmines to Avoid
- 2-3 specific warnings

### Desired Outcome
- Best case scenario
- Minimum acceptable outcome
- Suggested follow-up action
```

### Why This Structure

- **Attendee table** gives instant visual scan of who's in the room
- **Profiles** are ordered by importance (key decision-maker first)
- **Strategic angle** forces every meeting to connect to a business objective
- **Talking points** are numbered and specific so Justin can mentally queue them
- **Landmines** are often the most valuable section - they prevent unforced errors
- **Desired outcome** ensures Justin walks in with a goal, not just a conversation

---

## 4. AI Model Pipeline

The current production pipeline uses two active AI models:

### Stage 1: Web Research (Perplexity sonar-pro)
- **When:** Attendee is NOT in the contacts database
- **Input:** Person's name, email domain, any known company/title
- **Output:** 400-800 word professional profile covering career, education, current role, notable achievements
- **Cost:** ~$0.01/query
- **Rate limit:** ~50 RPM, sequential with 1.5s delay

### Stage 2: Memo Writing (Claude Sonnet 4.6)
- **When:** All attendee research is complete for a meeting
- **Input:** Attendee profiles, comms history, meeting context, org context docs, Justin's bio
- **Output:** Complete memo following the template structure
- **Cost:** ~$0.03-0.05/memo
- **Model ID:** `claude-sonnet-4-6`

### Why These Models

| Model | Role | Why |
|-------|------|-----|
| Perplexity sonar-pro | Web research | Real-time web search, good at finding people, cites sources |
| Claude Sonnet 4.6 | Memo writing | Best at nuanced, strategic, contextual writing. Understands relationship dynamics. |

### Cost Per Day

Assuming 3-5 external meetings/day with 2-3 attendees each:
- Perplexity: 2-5 unknown attendees x $0.01 = $0.02-0.05
- Claude Sonnet: 3-5 memos x $0.04 = $0.12-0.20
- **Total: ~$0.14-0.25/day, ~$4-8/month**

---

## 5. Filtering Logic

### What Gets a Memo

A meeting gets a prep memo if ALL of the following are true:
1. Has at least one external attendee (not Justin's emails, not internal/family)
2. Is NOT a recurring event (no `recurringEventId` in Calendar API response)
3. External attendees are NOT all from excluded domains
4. Justin has not declined the event
5. Is not an all-day event
6. Is not a wellness session, group workshop, or similar mass event

### Excluded Domains

Configured in `meeting_prep_config.json`. Initial list:
- `flourishfund.org` - Existing client, doesn't need prep memos

### Internal Emails (Always Skipped)

These are Justin's own emails and family:
- All 5 Google account emails
- `justin.steele@gmail.com`, `justinrichardsteele@gmail.com`
- `sally@outdoorithmcollective.org`, `sally.steele@gmail.com`
- `karibu@kindora.co` (Kindora co-founder)

### Recurring Event Detection

The Google Calendar API includes a `recurringEventId` field on events that are instances of a recurring series. If this field exists, the event is recurring and gets skipped.

This catches:
- Weekly 1:1s with team members
- Standing meetings
- Regular check-ins
- Any event created with a recurrence rule

One-off meetings booked via Calendly, scheduling links, or direct calendar invites do NOT have `recurringEventId` and will get memos.

---

## 6. Data Sources

### Contacts Database (Supabase)
- 2,940 contacts with LinkedIn enrichment, AI tags, comms history, ask readiness scores
- Direct PostgreSQL connection via `psycopg2`
- Lookup by email (primary, email_2, personal_email)
- Rich JSONB fields: `comms_summary`, `ai_tags`, `ask_readiness`

### Communication History
- `contact_email_threads` - Email threads across 5 Gmail accounts
- `contact_calendar_events` - Past calendar meetings
- `contact_sms_conversations` - SMS history
- `contact_call_logs` - Phone call records
- `communication_history` JSONB - LinkedIn DM history

### LinkedIn Enrichment
- `enrich_*` columns: current company, title, schools, companies worked, volunteer orgs, skills
- `linkedin_data` JSONB: full Apify scrape data
- Source: Apify `harvestapi/linkedin-profile-scraper`

### Web Research (for unknown contacts)
- Perplexity sonar-pro real-time web search
- Used directly in the memo prompt (optional structuring stage can be added later)

---

## 7. Entity Context

Each meeting is tagged to one of Justin's ventures based on the calendar account:

| Calendar Account | Entity | Focus Areas |
|-----------------|--------|-------------|
| `justin@kindora.co` | Kindora | New users, distribution, marketing, sales, funding |
| `justin@outdoorithm.com` | Outdoorithm | Product development, partnerships |
| `justin@outdoorithmcollective.org` | Outdoorithm Collective | Fundraising, donor cultivation, programs |
| `justin@truesteele.com` | True Steele Labs | Client acquisition, AI builds, consulting |
| `justinrsteele@gmail.com` | True Steele (default) | General networking |

The memo's **Strategic Angle** section is tailored based on this entity mapping.

Context docs are loaded from:
- `docs/Kindora/` - Platform guide, sales email guide, partnership proposals
- `docs/Outdoorithm/` - Campaign plans, fundraising playbook, donor segmentation
- `docs/True_Steele/` - Strategy doc, client research, transcripts

---

## 8. System Architecture

```
7:00 AM PT (launchd)
    │
    ▼
daily_meeting_prep.sh
    │
    ├── Resolve Python interpreter (.venv preferred)
    ├── Acquire lock (prevents overlapping runs)
    └── Stream output to daily log file
    │
    ▼
daily_meeting_prep.py
    │
    ├── 1. FETCH: Calendar events from 5 Google accounts
    │       └── google.oauth2.credentials + googleapiclient
    │
    ├── 2. FILTER: Apply exclusion rules
    │       ├── Skip recurring (recurringEventId)
    │       ├── Skip excluded domains (flourishfund.org)
    │       ├── Skip internal-only
    │       ├── Skip declined
    │       ├── Skip all-day
    │       └── Skip keyword-matched events (e.g. wellness sessions)
    │
    ├── 3. RESEARCH: For each external meeting
    │       ├── Look up attendees in Supabase (psycopg2)
    │       ├── Pull comms history (email, calendar, SMS, calls)
    │       ├── If unknown: Perplexity web research
    │       ├── If unknown: Auto-add as meeting contact
    │       └── Check shared background with Justin
    │
    ├── 4. GENERATE: Write memos (Claude Sonnet 4.6)
    │       └── One memo per meeting, following template
    │
    ├── 5. PUBLISH: Create Google Doc
    │       ├── Reuse daily doc if already exists (idempotent reruns)
    │       └── Replace full doc body with latest run output
    │
    └── 6. ATTACH: Patch calendar events
            └── events().patch(supportsAttachments=True)
```

---

## 9. Configuration Reference

**File:** `scripts/intelligence/meeting_prep_config.json`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `excluded_domains` | string[] | `["flourishfund.org"]` | Skip meetings where ALL external attendees are from these domains |
| `excluded_emails` | string[] | `[]` | Skip specific email addresses |
| `internal_emails` | string[] | (see config) | Always-skip attendees (family, co-founders) |
| `skip_recurring` | bool | `true` | Skip recurring calendar events |
| `skip_declined` | bool | `true` | Skip events Justin declined |
| `skip_all_day` | bool | `true` | Skip all-day events |
| `skip_cancelled` | bool | `true` | Skip cancelled events |
| `skip_keywords` | string[] | `["wellness session", "group workshop"]` | Skip events where title/description matches these keywords |
| `add_unknown_contacts` | bool | `true` | Auto-add unknown attendees as meeting contacts |
| `contact_pool_for_new` | string | `"meeting"` | Contact pool for auto-added contacts |
| `google_doc_folder_name` | string | `"Meeting Prep Memos"` | Drive folder name |
| `google_doc_account` | string | `"justin@truesteele.com"` | Account used for doc creation |
| `reuse_daily_google_doc` | bool | `true` | Reuse and overwrite same daily doc instead of creating duplicates |
| `attach_to_calendar` | bool | `true` | Attach doc to calendar events |
| `timezone` | string | `"America/Los_Angeles"` | Timezone used for event windows and local formatting |

---

## 10. Key Files

| File | Purpose |
|------|---------|
| `scripts/intelligence/daily_meeting_prep.py` | Main automation script |
| `scripts/intelligence/daily_meeting_prep.sh` | Shell wrapper (launchd entry point) |
| `scripts/intelligence/meeting_prep_config.json` | Exclusion & behavior config |
| `docs/MEETING_PREP_SYSTEM.md` | This document |
| `docs/meeting_memos/YYYY-MM-DD_daily_prep.md` | Local markdown backup |
| `logs/meeting_prep_YYYY-MM-DD.log` | Daily run logs |
| `~/Library/LaunchAgents/co.truesteele.meeting-prep.plist` | 7am scheduler |

---

## 11. Usage

```bash
# Today's meetings
python scripts/intelligence/daily_meeting_prep.py

# Dry run (read-only preview: no DB writes, no Docs publish, no calendar patches)
python scripts/intelligence/daily_meeting_prep.py --dry-run

# Specific date
python scripts/intelligence/daily_meeting_prep.py --date 2026-03-04

# Tomorrow
python scripts/intelligence/daily_meeting_prep.py --days-ahead 1

# Skip Google Doc creation (local markdown only)
python scripts/intelligence/daily_meeting_prep.py --no-gdoc

# Verify launchd is running
launchctl list | grep meeting-prep
```

---

## 12. Reliability Hardening (March 4, 2026)

- **Timezone-safe event windows:** Calendar fetch now uses `America/Los_Angeles` (configurable), so DST transitions don't shift which meetings are included.
- **Idempotent reruns:** Google Doc publish step reuses the daily doc title and overwrites content, rather than creating duplicates on retries.
- **Safer dry-run behavior:** `--dry-run` is read-only (no contact inserts, no doc writes, no calendar patches).
- **Graceful DB degradation:** If Supabase is unavailable, memo generation continues with web research and logs warnings.
- **Launch wrapper resilience:** Shell wrapper now prevents overlapping runs with a lock, writes explicit failure status, and no longer suppresses Python errors.
- **Markdown output safety:** Table cells are sanitized to avoid broken markdown when meeting titles contain `|` or line breaks.

---

*Last updated: March 4, 2026*
