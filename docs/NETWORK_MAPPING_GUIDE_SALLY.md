# Network Mapping — Sally's Contact Export

**Purpose:** Generate a full export of Sally's network contacts with rich communication history, so Justin can load them into the Steele Network intelligence system for enrichment, outreach drafting, and Come Alive 2026 campaign targeting.

**Who this is for:** Sally Steele, running Claude Code on her machine with Google Workspace MCP servers connected.

**What you'll get:**
- `sally_network_contacts.csv` — contact roster with density scores
- `sally_comms_history.json` — rich communication content per contact (email threads, meeting details, SMS samples) that the AI uses to write personalized outreach

---

## Prerequisites

Before starting, confirm you have:

1. **Claude Code** installed and running
2. **Google Workspace MCP servers** connected for:
   - `sally.steele@gmail.com`
   - `sally@outdoorithmcollective.org`
   - `sally@outdoorithm.com`
3. **LinkedIn connections CSV** exported from LinkedIn:
   - Go to https://www.linkedin.com/mypreferences/d/download-my-data
   - Request your data archive (select "Connections" at minimum)
   - Download and unzip — you need the `Connections.csv` file
   - Place it somewhere accessible (e.g., `~/Downloads/Connections.csv`)
4. **SMS backup file** (if available):
   - XML export from SMS Backup & Restore app, or
   - Any text file with SMS conversation data
   - Place it somewhere accessible (e.g., `~/Downloads/sms_backup.xml`)

---

## Instructions for Claude Code

Copy everything below this line and paste it as a prompt to Claude Code:

---

### PROMPT START

I need you to build a Python script that maps my network by combining my LinkedIn connections with communication data from my Google Workspace accounts and SMS messages. The output should include both a contact roster AND rich communication content that can be used later to write personalized outreach.

**My accounts:**
- Google Workspace: `sally.steele@gmail.com`, `sally@outdoorithmcollective.org`, `sally@outdoorithm.com`
- My own email addresses (exclude these from contact discovery): `sally.steele@gmail.com`, `sally@outdoorithmcollective.org`, `sally@outdoorithm.com`
- LinkedIn connections CSV: `~/Downloads/Connections.csv` (adjust path if different)
- SMS backup: `~/Downloads/sms_backup.xml` (skip if I don't have this)

**What the script should do:**

#### Step 1: Load LinkedIn Connections

Read my LinkedIn `Connections.csv` file. LinkedIn exports have these columns:
- `First Name`, `Last Name`, `Email Address`, `Company`, `Position`, `Connected On`, `URL`

Load all rows into a dictionary keyed by full name (lowercase, stripped). Store the LinkedIn URL, company, position, email (if present), and connected date.

#### Step 2: Scan Gmail for Email Threads WITH Content

Use the Google Workspace MCP tools to search Gmail across all three of my accounts (`sally.steele@gmail.com`, `sally@outdoorithmcollective.org`, `sally@outdoorithm.com`).

For each LinkedIn connection that has an email address:
1. Search Gmail for threads involving that email address
2. For each thread found, capture:
   - **Thread subject line**
   - **Snippet/preview** (the first ~200 chars Gmail returns)
   - **Full message content** for the most recent 3 messages in the thread (sender, date, body text — strip HTML, keep plain text, truncate each message body to 2,000 characters)
   - **Direction**: did Sally send, receive, or both in this thread?
   - **Message count** in the thread
   - **Date of first and last message**
   - **Which of Sally's accounts** this thread was on
3. Store ALL threads found (up to 20 per contact per account). We need the actual content for outreach writing later.

For efficiency:
- Use `search_gmail_messages` with the contact's email as the query
- Then use `get_gmail_message_content` or `get_gmail_thread_content` to pull actual message bodies for threads
- Process in batches, pausing briefly between searches to avoid rate limits

**Why we need content:** An AI will later use these thread summaries to write personalized outreach emails. It needs to know what Sally and this person actually talked about — not just that they emailed 5 times. Thread subjects and message snippets are the minimum; full recent messages are ideal.

#### Step 3: Scan Calendar for Meeting Details WITH Context

Use the Google Workspace MCP tools to pull calendar events from all three accounts.

For each account:
1. Pull all events from the last 3 years (since January 2023)
2. For each event, capture:
   - **Event title/summary**
   - **Date and time** (start, end, duration in minutes)
   - **Description/notes** (truncate to 1,000 characters)
   - **Location** (if present)
   - **All attendees** (names and emails)
   - **Number of attendees** (1:1 meetings are high signal, 20-person meetings are low signal)
   - **Whether Sally organized** the event
   - **Conference type** (Zoom, Google Meet, in-person, etc.)
3. Match attendee emails against LinkedIn connections
4. Store the full meeting details per contact — not just counts

**Why we need details:** Meeting titles like "Coffee catch-up" vs. "OC Board Planning" vs. "Intro: Sally <> David" tell the AI what the relationship is about. 1:1 meetings signal much stronger ties than large group calls.

#### Step 4: Process SMS Data WITH Sample Messages (if available)

If an SMS backup XML file exists:
1. Parse the XML (SMS Backup & Restore format: `<sms>` elements with `address`, `date`, `type`, `body`, `contact_name` attributes)
2. Group messages by phone number
3. Filter out short codes (6 digits or fewer) and obvious spam/verification messages (verification codes, 2FA, alerts, marketing)
4. For each conversation, capture:
   - **Phone number** and **contact name** from the phone
   - **Total message count**, sent count, received count
   - **Date of first and last message**
   - **10 most recent messages** (date, direction, body text — truncate each to 500 chars)
   - **A representative sample**: also grab 5 messages from the middle of the conversation history to show relationship evolution
5. Try to match phone numbers to LinkedIn connections by name (the SMS `contact_name` field vs LinkedIn names — fuzzy match is fine)

**Why we need sample messages:** SMS is the highest-trust communication channel. If Sally texts someone regularly, the tone and topics of those texts are gold for writing outreach that sounds like a real continuation of the relationship.

#### Step 5: Discover Non-LinkedIn Contacts

This is critical — find people Sally communicates with frequently who are NOT in her LinkedIn connections.

From the Gmail and Calendar data:
1. Collect all unique email addresses that appeared in threads or calendar events
2. Remove Sally's own addresses (`sally.steele@gmail.com`, `sally@outdoorithmcollective.org`, `sally@outdoorithm.com`)
3. Remove obvious non-person addresses: anything matching these patterns:
   - `noreply@`, `no-reply@`, `notifications@`, `alerts@`, `info@`, `support@`, `hello@`, `team@`, `admin@`
   - `*@calendar.google.com`, `*@group.calendar.google.com`
   - `*@docs.google.com`, `*@resource.calendar.google.com`
   - Anything with `unsubscribe`, `mailer-daemon`, `postmaster`
4. Remove addresses already matched to a LinkedIn connection
5. For remaining addresses, count: email threads + calendar appearances
6. Keep anyone with **3+ total touchpoints** (emails + meetings combined)
7. Try to extract their name from email headers (the display name in "From" or "To" fields) or calendar event attendee display names
8. Mark these as `source: discovered` (vs `source: linkedin` for LinkedIn connections)
9. **Capture the same rich communication data** for discovered contacts as for LinkedIn connections (thread content, meeting details)

#### Step 6: Score Communication Density

For every contact (LinkedIn + discovered), compute a density score:

```
density_score = (email_thread_count * 2) + (calendar_meeting_count * 3) + (sms_message_count > 0 ? 5 : 0)
```

Weight meetings highest (intentional time), then email (direct communication), then SMS as a binary trust signal.

Also assign a recency tier based on the most recent communication across all channels:
- `active` — last communication within 90 days
- `recent` — last communication 91-365 days ago
- `dormant` — last communication over 1 year ago
- `no_history` — no communication data found

#### Step 7: Output Two Files

**File 1: `sally_network_contacts.csv`** — The contact roster

| Column | Description |
|--------|-------------|
| `first_name` | First name |
| `last_name` | Last name |
| `email` | Primary email address |
| `linkedin_url` | LinkedIn profile URL (blank for discovered contacts) |
| `company` | Current company |
| `position` | Current title |
| `connected_on` | LinkedIn connection date |
| `source` | `linkedin` or `discovered` |
| `email_thread_count` | Total email threads found |
| `email_first_date` | Earliest email thread date |
| `email_last_date` | Most recent email thread date |
| `email_direction` | `sent` / `received` / `bidirectional` / blank |
| `email_accounts` | Which of Sally's accounts had activity (comma-separated) |
| `calendar_meeting_count` | Total calendar meetings |
| `calendar_last_date` | Most recent meeting date |
| `sms_message_count` | SMS message count (0 if no SMS data) |
| `sms_last_date` | Most recent SMS date |
| `density_score` | Computed density score |
| `recency_tier` | `active` / `recent` / `dormant` / `no_history` |

Sort by `density_score` descending.

**File 2: `sally_comms_history.json`** — Rich communication content

A JSON file with one entry per contact. Structure:

```json
{
  "contacts": [
    {
      "first_name": "Jane",
      "last_name": "Doe",
      "email": "jane@example.com",
      "linkedin_url": "https://linkedin.com/in/janedoe",
      "source": "linkedin",
      "density_score": 15,
      "recency_tier": "active",
      "email_threads": [
        {
          "account": "sally@outdoorithmcollective.org",
          "thread_id": "abc123",
          "subject": "Re: OC Spring Trip Planning",
          "direction": "bidirectional",
          "message_count": 4,
          "first_message_date": "2025-11-03",
          "last_message_date": "2026-01-15",
          "messages": [
            {
              "date": "2026-01-15",
              "from": "jane@example.com",
              "to": "sally@outdoorithmcollective.org",
              "body": "Sounds great! I'd love to help with the March trip..."
            },
            {
              "date": "2026-01-10",
              "from": "sally@outdoorithmcollective.org",
              "to": "jane@example.com",
              "body": "Hey Jane — we're planning the spring season and I immediately thought of you..."
            }
          ]
        }
      ],
      "calendar_events": [
        {
          "account": "sally@outdoorithmcollective.org",
          "summary": "Coffee with Jane",
          "date": "2025-12-05",
          "duration_minutes": 60,
          "location": "Blue Bottle, Oakland",
          "attendee_count": 2,
          "attendees": ["sally@outdoorithmcollective.org", "jane@example.com"],
          "is_organizer": true,
          "description": "Catching up about her new role and OC spring plans"
        }
      ],
      "sms_messages": [
        {
          "date": "2026-02-01",
          "direction": "received",
          "body": "Hey! Are you guys doing Joshua Tree again this year? We want in"
        },
        {
          "date": "2026-02-01",
          "direction": "sent",
          "body": "YES!! March 30. Sending you the details now"
        }
      ]
    }
  ]
}
```

For each contact, include:
- **Up to 20 email threads** per account, with the **3 most recent messages per thread** (full body, truncated to 2,000 chars each)
- **All calendar events** where this person was an attendee
- **Up to 15 SMS messages** (10 most recent + 5 from the middle of the history), truncated to 500 chars each

**Important notes:**
- These two files work together: the CSV is the roster for database import, the JSON is the communication context for AI-powered outreach writing
- This script should be self-contained — no database needed, no API keys beyond Google Workspace MCP
- Save both files to the current working directory
- Print progress every 25 contacts (this will take a while with full content pulls)
- Print a summary at the end: total contacts, LinkedIn count, discovered count, density distribution, total threads captured, total meetings captured
- Handle errors gracefully — if a Gmail search or thread fetch fails for one contact, log the error and continue
- The JSON file may be large (50-200MB depending on email volume). That's fine — it compresses well.

### PROMPT END

---

## What Happens Next

Once you have both files, send them to Justin. He will:

1. **Import** your contacts into the Steele Network database (separate from his, tagged as Sally's network)
2. **Load communication history** from the JSON into `contact_email_threads` and `contact_calendar_events` tables — this is what powers personalized outreach
3. **Enrich** LinkedIn profiles via Apify (employment history, education, skills, board positions, volunteer work)
4. **Score** each contact for donor capacity, affinity to Outdoorithm Collective, and ask readiness for Come Alive 2026
5. **Cross-reference** with Justin's network to find shared connections, warm intro paths, and contacts already in the campaign
6. **Generate** personalized outreach drafts that reference real past conversations — the AI reads the actual email threads and meeting history to write messages that sound like a natural continuation of the relationship, not a cold ask
7. **Build** a dashboard view of Sally's network with filters for campaign targeting

## Why Communication Content Matters

The difference between a generic fundraising email and a great one:

**Without communication history:**
> "Hi Jane — I wanted to share what Outdoorithm Collective is doing this spring..."

**With communication history (what the AI can write using the JSON data):**
> "Jane — remember when you asked about Joshua Tree? We're going March 30, and we're trying to fund the whole spring season. 8 trips, $120K total. You've seen what these trips do firsthand..."

The JSON file gives the AI everything it needs to write outreach that sounds like Sally, references real shared experiences, and picks up where the last conversation left off.

## Expected Output

A typical run produces:
- **500-2,000 LinkedIn connections** in the CSV (depends on Sally's network size)
- **50-200 discovered contacts** (frequent email/calendar contacts not on LinkedIn)
- **Processing time:** 1-3 hours depending on email volume (content pulls are slower than count-only)
- **CSV size:** Under 1MB
- **JSON size:** 50-200MB (compressed: 5-20MB)

The density score distribution helps prioritize:
- **Score 10+** — Strong active relationship, high-priority for campaign
- **Score 5-9** — Moderate engagement, good campaign candidates
- **Score 1-4** — Light touch, may be worth a personal note
- **Score 0** — LinkedIn-only connection, no communication history found
