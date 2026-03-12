# Email Triage System

## Overview

Automated email classification across 5 Gmail accounts using a two-layer system:
1. **Apps Script (server-side)** — rule-based labeling every 5 min, uses existing Gmail labels
2. **Web UI + AI (client-side)** — GPT-5 mini classification for ambiguous emails in the triage UI

## Gmail Accounts

| Account | Email |
|---------|-------|
| Personal | justinrsteele@gmail.com |
| True Steele | justin@truesteele.com |
| Kindora | justin@kindora.co |
| Outdoorithm | justin@outdoorithm.com |
| OC | justin@outdoorithmcollective.org |

## Label System

All 5 accounts share the same label taxonomy:

### Action labels (`!` prefix)
| Label | Meaning |
|-------|---------|
| `!Action` | Needs reply, decision, or RSVP |
| `!Action/Urgent` | Time-sensitive action needed |
| `!FYI` | Informational, no reply needed |
| `!Read-Review` | Worth reading but no action |
| `!Waiting-For` | Waiting on someone else's reply |

### Skip labels (`~` prefix)
| Label | Meaning | Auto-mark read? |
|-------|---------|-----------------|
| `~Sales-Pitch` | Cold outreach, spam, unsolicited offers | Yes |
| `~Notifications` | System notifications (Vercel, Kindora signups, SES) | Most yes |
| `~Newsletters` | Mailing list platforms (Beehiiv, ConvertKit) | Yes |
| `~Calendar` | Calendar acceptances, invitations | Acceptances yes |
| `~Receipts` | Confirmation receipts | No |
| `~Marketing` | Marketing emails | — |
| `~LinkedIn` | LinkedIn notifications | — |
| `~ErrorMonitor` | Vercel error/failure notifications | No |
| `~CRM` | CRM system notifications | — |

### AI labels (`_` prefix)
| Label | Meaning |
|-------|---------|
| `_ai` | Classified by AI (GPT-5 mini) |
| `_ai/unsure` | AI confidence was low |

## Layer 1: Apps Script (Rule-Based)

**Source:** `scripts/gmail-triage-apps-script/Code.gs`

Runs every 5 minutes via time-driven trigger. Processes unread primary inbox threads from last 2 days that don't already have triage labels.

### Apps Script Projects

| Account | Script ID |
|---------|-----------|
| Gmail | `1JMb6d3snN2iHJ5Nyv2A2-Xnm43YuPtq4wrc3NpNslWgyGDH5vzPlxI_z` |
| TrueSteele | `1XLISiq2YFtc_8Vht25aXMoLwLQxlPzJlACu5HjB9a247O5_2u6OBsKze` |
| Kindora | `1ZZKbjlo5RQ0YxGxYp05hToyo14wECYB8Mq2ysanwssHABWdyzrgPZaDJ` |
| Outdoorithm | `1d5Q13UjvZb4VK6sIlN2YnaA4tyh6x49hRRTGQ7k8HoAw1VxBHuf6lNpZ` |
| OC | `1pmfqk-Pen-MhqgbLLEnSVFsCFCHlk2JcnIq6C2xOhITuegAg0GUYjM3_` |

### Classification Rules (order matters — first match wins)

#### ~Notifications
- `info@kindora.co` + "New User Signup" → mark read
- `notifications@vercel.com` → mark read
- `noreply@tickets.*` → keep unread
- `no-reply@*.amazonses.com` + "New User Signup" → mark read
- `billing@*.openai.com` → keep unread

#### ~ErrorMonitor
- `notifications@vercel.com` + "fail" or "error" in subject

#### ~Calendar
- Subject starts with "Accepted:" → mark read
- Subject starts with "Invitation:...YYYY" → keep unread

#### ~Receipts
- `noreply@*` + "Confirmed" in subject

#### ~Newsletters
- `@mail.beehiiv.com` → mark read
- `convertkit-mail` → mark read

#### ~Sales-Pitch (explicit domains)
- Domains: useclaritymail, oursprintops, joinforge, prpodpitch, upscalepulselab, boostbnxt, readingbrandlane → mark read

#### !FYI
- `@bishopodowd.org` — school notifications
- `@oaklandmontessori.com` — school notifications
- `info@outdoorithm.com` + "available again" — campsite alerts

### Cold Sales Heuristics (for non-known-good domains → ~Sales-Pitch)

**Subject patterns:**
- "gentle nudge", "follow up", "following up", "quick question"
- "can I help", "win back", "save time/hours", "checking in"
- "circling back", "touching base"
- "UVA Summer Interns for"
- All patterns also match fake "RE:" prefixes

**Domain keyword matching:**
- claritymail, sprintops, pulselab, brandlane, podpitch, boostbnxt
- reachout, growthlab, funnelmail, pipelinemail, hubreach
- engagemail, convertlab, nurturemail, salesreach, prospectmail, leadmail

**Personalization token detection:**
- Subject contains "justin" + follow/nudge/check/touch/reach from unknown domain

### Known Good Domains (never auto-skip)
gmail.com, yahoo.com, outlook.com, hotmail.com, icloud.com,
truesteele.com, kindora.co, outdoorithm.com, outdoorithmcollective.org,
google.com, andela.com, bridgespan.org, camelbackventures.org,
sff.org, *.gov, *.edu, *.mil, blackbaud.com, uptogether.org,
tenstrands.org, collectivemoxie.com, measuresforjustice.org,
sojo.net, omidyar.com, learnupcenters.org, fullscale.ph,
olegreensgroup.com, philanthropyforum.org, rcenterprises.org, appsnxt.com

### Management Functions
- `setupTrigger()` — creates 5-min time trigger (run once per account)
- `backfillLabels()` — labels unread from last 21 days (run once per account)
- `removeAllTriageLabels()` — reset all labels tagged with `_ai`

## Layer 2: Web UI + AI Classification

### API Routes

| Route | Purpose |
|-------|---------|
| `POST /api/network-intel/email-triage/scan` | Fetches unread emails, resolves labels, applies rule filters |
| `POST /api/network-intel/email-triage/classify` | GPT-5 mini batch classification for unclassified emails |
| `POST /api/network-intel/email-triage/message` | Fetches full email body |
| `POST /api/network-intel/email-triage/draft-response` | AI-drafted reply (Claude Sonnet) |
| `POST /api/network-intel/email-triage/gmail-action` | Send/draft/archive via Gmail API |

### Scan Route Flow
1. Fetch unread primary emails from all 5 accounts (parallel)
2. Resolve Gmail label IDs → label names (e.g., `Label_59` → `!Action`)
3. Check existing labels — if `!Action`, `~Sales-Pitch`, etc. already applied by Apps Script, use those
4. Fall through to regex-based rules for any without labels
5. Return with `category` and `categoryReason` per message

### Classify Route (GPT-5 mini)
- Batch size: 40 emails per API call
- Model: `gpt-5-mini` with `response_format: { type: 'json_object' }`
- Categories: action, fyi, skip
- Aggressive cold sales detection prompt with domain heuristics, subject patterns, personalization token detection
- Cost: ~$0.002 per batch of 40

### UI (`/tools/email-triage`)
- Filter tabs: Action | FYI | Skipped | All (with count badges)
- Default view: Action tab (includes unclassified)
- Auto-triggers `/classify` after scan for unclassified emails
- Manual reclassify buttons (Action/Skip) in detail view
- Skip emails shown dimmed with strikethrough
- Category reason shown as italic text

## Data Flow

```
New email arrives
  → Apps Script (every 5 min) applies label (!Action, ~Sales-Pitch, etc.)
  → Some skip emails auto-marked read

User opens triage UI
  → POST /scan fetches unread, checks existing Gmail labels
  → Already-labeled emails get instant classification
  → Unlabeled emails stay "unclassified"
  → UI auto-fires POST /classify for remaining
  → GPT-5 mini classifies in one batch call
  → UI updates in place

User clicks email
  → POST /message fetches full body
  → POST /draft-response generates AI reply (Claude Sonnet)
  → User reviews/edits/sends
```

## Adding New Rules

1. **Edit `Code.gs`** — add rule to `RULES` array (specify label, reason, markRead)
2. **Edit `scan/route.ts`** — add corresponding regex to `FILTER_RULES` array
3. **Re-upload to all 5 Apps Script projects** via Google Workspace MCP `update_script_content`
4. **Run `backfillLabels()`** on each account to apply to existing emails
5. **Deploy web app** to Vercel

## Files

| File | Purpose |
|------|---------|
| `scripts/gmail-triage-apps-script/Code.gs` | Apps Script source (deployed to all 5 accounts) |
| `job-matcher-ai/app/api/network-intel/email-triage/scan/route.ts` | Scan + rule filter route |
| `job-matcher-ai/app/api/network-intel/email-triage/classify/route.ts` | GPT-5 mini AI classification |
| `job-matcher-ai/app/api/network-intel/email-triage/message/route.ts` | Full message body fetch |
| `job-matcher-ai/app/api/network-intel/email-triage/draft-response/route.ts` | AI draft reply (Claude) |
| `job-matcher-ai/app/api/network-intel/email-triage/gmail-action/route.ts` | Send/draft/archive Gmail actions |
| `job-matcher-ai/app/tools/email-triage/page.tsx` | Triage UI page |
| `job-matcher-ai/lib/gmail-client.ts` | OAuth2 Gmail client factory |
