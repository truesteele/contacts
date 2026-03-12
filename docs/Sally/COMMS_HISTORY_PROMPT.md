# Prompt for Sally — Communication History Export

Copy everything below and paste it into Claude Code as a single prompt.

---

I need you to build a rich communication history export by scanning my Gmail and Google Calendar across all 3 of my accounts, then outputting a JSON file. I already have a CSV of my LinkedIn connections — use that as the starting contact list, then also discover people I communicate with who are NOT in that CSV.

## My Accounts

- `sally.steele@gmail.com`
- `sally@outdoorithmcollective.org`
- `sally@outdoorithm.com`

These are my own addresses — exclude them when identifying contacts.

## Input File

Read `sally_network_contacts.csv` in this directory. It has 850 LinkedIn connections with columns: `first_name`, `last_name`, `linkedin_url`, `title`, `connection_date`, `calendar_email`, `sms_phone`, etc. Use the `calendar_email` column as the contact's email address for Gmail searches.

## What To Do

### Part 1: Scan Gmail for Email Threads

For every contact in the CSV that has a value in the `calendar_email` column, search Gmail across all 3 of my accounts.

For each account, use `search_gmail_messages` to find threads involving that contact's email address. Then for each thread found, use `get_gmail_thread_content` to pull the actual messages.

For each thread, capture:
- `thread_id`
- `account` — which of my 3 accounts
- `subject` — thread subject line
- `direction` — `sent` (I wrote), `received` (they wrote), or `bidirectional` (both)
- `message_count` — total messages in thread
- `first_message_date` — ISO date of earliest message
- `last_message_date` — ISO date of most recent message
- `messages` — array of the **5 most recent messages** in the thread, each with:
  - `date` — ISO date
  - `from` — sender email
  - `to` — recipient email(s)
  - `body` — plain text body, stripped of HTML, truncated to 2000 characters

Capture up to 20 threads per contact per account. We need the actual message text — this will be used to write personalized outreach later.

**Pacing:** Pause 1-2 seconds between Gmail API calls to avoid rate limits. Print progress every 10 contacts.

### Part 2: Scan Calendar for Meeting Details

For each of my 3 accounts, use `get_events` to pull all calendar events from January 1, 2023 through today.

For each event, capture:
- `event_id`
- `account` — which of my 3 accounts
- `summary` — event title
- `date` — start date (ISO)
- `start_time` and `end_time`
- `duration_minutes`
- `description` — event description/notes, truncated to 1000 characters
- `location`
- `attendees` — array of attendee objects with `email` and `displayName`
- `attendee_count`
- `is_organizer` — whether I organized this event
- `conference_type` — Zoom, Google Meet, phone, or blank

Then match attendee emails against the contacts in the CSV (match on `calendar_email` column). Assign each event to all matching contacts.

### Part 3: Discover Non-LinkedIn Contacts

From the Gmail threads and calendar events collected above:

1. Collect every unique email address that appeared as a sender, recipient, or attendee
2. Remove my own addresses: `sally.steele@gmail.com`, `sally@outdoorithmcollective.org`, `sally@outdoorithm.com`
3. Remove non-person addresses matching any of these patterns:
   - Starts with: `noreply`, `no-reply`, `notifications`, `alerts`, `info@`, `support@`, `hello@`, `team@`, `admin@`, `billing@`, `sales@`, `marketing@`, `feedback@`, `help@`
   - Contains: `calendar.google.com`, `docs.google.com`, `resource.calendar`, `unsubscribe`, `mailer-daemon`, `postmaster`, `bounce`
   - Domains: `calendly.com`, `zoom.us`, `notion.so`, `slack.com`, `github.com`, `vercel.com`, `stripe.com`, `squarespace.com`, `mailchimp.com`, `google.com`
4. Remove any email that already matches a contact in the CSV
5. For each remaining email, count total touchpoints (email threads + calendar appearances)
6. Keep anyone with **3 or more touchpoints**
7. Extract their display name from email headers or calendar attendee names
8. These are "discovered" contacts — collect the same email thread and calendar data for them

### Part 4: Output JSON

Write `sally_comms_history.json` with this structure:

```json
{
  "export_date": "2026-03-09",
  "accounts_scanned": ["sally.steele@gmail.com", "sally@outdoorithmcollective.org", "sally@outdoorithm.com"],
  "contacts": [
    {
      "first_name": "Kay",
      "last_name": "Fernandez Smith",
      "email": "kay@talastrategies.com",
      "linkedin_url": "https://www.linkedin.com/in/kay-fernandez-smith-24a3777",
      "source": "linkedin",
      "email_threads": [
        {
          "account": "sally@outdoorithmcollective.org",
          "thread_id": "18abc123",
          "subject": "Re: Spring planning session",
          "direction": "bidirectional",
          "message_count": 6,
          "first_message_date": "2025-09-15",
          "last_message_date": "2026-02-20",
          "messages": [
            {
              "date": "2026-02-20",
              "from": "kay@talastrategies.com",
              "to": "sally@outdoorithmcollective.org",
              "body": "Sounds great — I'll block March 15 for the planning call..."
            }
          ]
        }
      ],
      "calendar_events": [
        {
          "account": "sally@outdoorithmcollective.org",
          "event_id": "evt_456",
          "summary": "OC Board Meeting",
          "date": "2026-01-10",
          "start_time": "2026-01-10T10:00:00-08:00",
          "end_time": "2026-01-10T11:30:00-08:00",
          "duration_minutes": 90,
          "description": "Monthly board meeting — budget review and spring trip planning",
          "location": "Google Meet",
          "attendees": [
            {"email": "kay@talastrategies.com", "displayName": "Kay Fernandez Smith"},
            {"email": "sally@outdoorithmcollective.org", "displayName": "Sally Steele"}
          ],
          "attendee_count": 2,
          "is_organizer": true,
          "conference_type": "Google Meet"
        }
      ]
    },
    {
      "first_name": "Maria",
      "last_name": "Chen",
      "email": "maria@example.org",
      "linkedin_url": "",
      "source": "discovered",
      "email_threads": [],
      "calendar_events": []
    }
  ]
}
```

For discovered contacts, set `linkedin_url` to empty string and `source` to `"discovered"`.

## Important

- **Do not skip Gmail scanning.** This is the most important part. The email thread content is what enables personalized outreach writing.
- **Pull actual message bodies**, not just subjects and dates. The full text of recent messages is essential.
- **Process all 3 accounts** for both Gmail and Calendar.
- **The file will be large** (possibly 50-200MB). That's expected and fine.
- **Handle errors gracefully.** If a search fails for one contact, log it and continue to the next.
- **Print progress** so I can see it's working: "Scanned Gmail for 10/56 contacts...", "Pulled 1,847 calendar events from sally.steele@gmail.com...", etc.
- Save the file to the current working directory.
- At the end, print a summary: total contacts with email data, total threads captured, total calendar events, number of discovered contacts.
