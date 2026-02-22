# Pipeline O: SMS Communication History Enrichment

**Last updated:** 2026-02-22

Parses an Android SMS Backup & Restore XML file, matches SMS conversations to contacts in the database, and enriches the `communication_history` JSONB field with SMS data alongside existing email data.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Data Source](#2-data-source)
3. [Matching Strategy](#3-matching-strategy)
4. [Database Schema](#4-database-schema)
5. [Script Usage](#5-script-usage)
6. [Merge Strategy](#6-merge-strategy)
7. [Phone Number Backfill](#7-phone-number-backfill)
8. [Filters](#8-filters)
9. [Cost](#9-cost)
10. [Key Files](#10-key-files)

---

## 1. Overview

This pipeline extracts SMS/MMS conversations from a phone backup, matches them to contacts using phone numbers and GPT-5 mini name confirmation, then merges the data into the existing `communication_history` field. This gives a more complete picture of Justin's relationships beyond email alone.

**Production run results (Feb 22, 2026):**
- Source file: `tool-results/sms-backup.xml` (4.86 GB)
- Total messages parsed: 47,304 (after filtering 17,673 short codes, 2,731 own-number, 570 group texts, 88 spam)
- Named conversations: 206
- **Phone-matched: 98 contacts**
- **Exact name matched (GPT confirmed): 30 contacts**
- **Fuzzy name matched (GPT confirmed): 19 contacts**
- **Total matched: 147 contacts** (143 unique)
- Unmatched: 59 conversations
- Phone numbers backfilled: 37
- LLM cost: $0.11
- Runtime: 157 seconds (20 concurrent workers)

## 2. Data Source

**Android SMS Backup & Restore** (app by Carbonite) creates XML backups of all SMS and MMS messages. The XML format uses `<sms>` and `<mms>` elements:

```xml
<sms protocol="0" address="+15551234567" date="1708556234000" type="1"
     body="Hey, are you free for lunch?" contact_name="John Smith" />

<mms date="1708556234" msg_box="2" address="+15551234567"
     contact_name="John Smith">
  <parts>
    <part ct="text/plain" text="Sounds great!" />
  </parts>
</mms>
```

Key fields:
- `address` — Phone number (may include country code)
- `contact_name` — Name from phone contacts at backup time
- `type` (SMS) / `msg_box` (MMS) — 1=received, 2=sent
- `date` — Epoch milliseconds (SMS) or seconds (MMS)
- `body` (SMS) / `part[@ct='text/plain']` (MMS) — Message text

## 3. Matching Strategy

Three-tier matching, each confirmed by GPT-5 mini where needed:

### Tier 1: Phone Number Match (highest confidence)
- Normalize phone to E.164 format (e.g., `+15551234567`)
- Match against `contacts.normalized_phone_number`
- No GPT confirmation needed — phone is a unique identifier
- ~80 contacts matched this way

### Tier 2: Exact Name Match + GPT Confirmation
- SMS `contact_name` matches `first_name + " " + last_name` exactly
- GPT-5 mini confirms using message context and employment data
- Catches false duplicates (e.g., two "John Smith" entries)
- ~40 contacts matched this way

### Tier 3: Fuzzy Name Match + GPT Confirmation
- Candidate generation using string similarity (SequenceMatcher ≥0.75)
- Checks: substring match, first name + similar last name, overall similarity
- GPT-5 mini confirms or rejects each candidate using:
  - SMS contact name + phone number
  - Recent message samples (last 5 messages)
  - DB contact name, company, position, headline
- Successfully matches: "Dave Winder" → "David Winder", "Hector Mujuca" → "Hector Mujica", "Bob Yueki" → "Bob Uyeki"
- Correctly rejects: "David Kim" → "David Simms", "Siena Steele" → "Sally Steele"

### GPT-5 mini Confirmation Prompt
```
Determine if this SMS contact is the same person as the database contact.

SMS Contact:
- Name in phone: "Dave Winder"
- Phone number: +15551234567
- Total messages: 627
- Recent messages: [samples]

Database Contact:
- Name: David Winder
- Company: Acme Corp
- Position: VP Engineering

Consider: name variations (nicknames, maiden names, hyphenation), message context clues.
```

## 4. Database Schema

### Table: `contact_sms_conversations`
```sql
CREATE TABLE contact_sms_conversations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id bigint REFERENCES contacts(id) ON DELETE CASCADE,
    phone_number text NOT NULL,
    message_count integer DEFAULT 0,
    sent_count integer DEFAULT 0,
    received_count integer DEFAULT 0,
    first_message_date timestamptz,
    last_message_date timestamptz,
    sms_contact_name text,
    match_method text,               -- 'phone', 'exact_name', 'fuzzy_name_gpt'
    match_confidence text,           -- 'high', 'medium'
    sample_messages jsonb,           -- up to 50 representative messages
    summary text,                    -- LLM conversation summary
    gathered_at timestamptz DEFAULT now(),
    UNIQUE(contact_id, phone_number)
);
```

### Enriched field: `contacts.communication_history` (JSONB)

SMS data is merged into the existing email-based communication_history:
```json
{
  "total_threads": 15,
  "total_sms_conversations": 3,
  "first_contact": "2016-01-06",
  "last_contact": "2026-02-20",
  "accounts_with_activity": ["justinrsteele@gmail.com", "sms:+15551234567"],
  "threads": [
    { "date": "2026-02-15", "source": "email", "account": "justin@truesteele.com", "subject": "..." },
    { "date": "2026-02-18", "source": "sms", "phone": "+15551234567", "direction": "bidirectional",
      "summary": "Regular personal check-ins.", "message_count": 145 }
  ],
  "relationship_summary": "Combines email and SMS history..."
}
```

## 5. Script Usage

```bash
# Parse XML + match contacts (no LLM cost, no DB writes except table check)
python scripts/intelligence/gather_sms_history.py --parse-only

# End-to-end test with 1 conversation
python scripts/intelligence/gather_sms_history.py --test

# Process N conversations
python scripts/intelligence/gather_sms_history.py --batch 20

# Full run — all conversations
python scripts/intelligence/gather_sms_history.py

# Re-process already gathered conversations
python scripts/intelligence/gather_sms_history.py --force
```

## 6. Merge Strategy

SMS threads are merged into the existing `communication_history` JSONB field (same field as email):

1. Fetch current `communication_history` for the contact
2. Remove any existing SMS entry for this phone number (idempotent)
3. Add new SMS thread entry with `"source": "sms"`
4. Update date ranges (`first_contact`, `last_contact`) to span both email + SMS
5. Add `sms:{phone}` to `accounts_with_activity`
6. Append SMS summary to `relationship_summary`
7. Update denormalized fields: `comms_last_date`, `comms_thread_count`

## 7. Phone Number Backfill

For every contact matched by **name** (exact or fuzzy), the script updates `normalized_phone_number` in the contacts table. This gives us verified phone numbers for contacts that previously had none.

**Production results:** 37 phone numbers backfilled from name matches.
- Before: ~160 contacts with phone numbers
- After: 220 contacts with phone numbers

## 8. Filters

The following are filtered out during XML parsing:
- **Short codes** — Phone numbers with ≤6 digits (verification services, alerts)
- **Own numbers** — Justin's Twilio number (+15103958187 / "Outdoorithm")
- **Group texts** — MMS with multiple phone numbers concatenated
- **Spam/automated** — Verification codes, ADT alerts, carrier messages, 2FA
- **Self-texts** — Messages to "Justin Steele" (own name)
- **Group contact names** — Comma-separated multi-person names from group MMS

## 9. Cost

| Step | Count | Cost/unit | Total |
|------|-------|-----------|-------|
| GPT-5 mini name matching | ~49 calls | ~$0.001 | ~$0.02 |
| GPT-5 mini summarization | 147 conversations | ~$0.001 | ~$0.09 |
| **Total** | | | **$0.11** |

*Actual production run cost: $0.11, runtime: 157 seconds with 20 concurrent workers.*

## 10. Key Files

| File | Purpose |
|------|---------|
| `scripts/intelligence/gather_sms_history.py` | Main enrichment script |
| `supabase/migrations/20260222_add_contact_sms_conversations.sql` | DB migration |
| `tool-results/sms-backup.xml` | Source SMS backup (4.86 GB) |
| `docs/SMS_ENRICHMENT.md` | This document |

### Related Files
| File | Purpose |
|------|---------|
| `scripts/intelligence/gather_comms_history.py` | Pipeline M: Email communication history (same pattern) |
| `job-matcher-ai/components/contact-detail-sheet.tsx` | UI displaying SMS in contact detail |
| `job-matcher-ai/app/api/network-intel/contact/[id]/route.ts` | API route (no changes needed — passes through `communication_history`) |
