---
name: enrich-contact
description: Add a new contact to the database and run the full enrichment pipeline, or re-enrich an existing contact. Use when the user asks to add someone to contacts, enrich a contact, or run the enrichment pipeline on specific people.
user-invocable: true
---

# Contact Enrichment Pipeline

Add a new contact and/or run the full enrichment pipeline on one or more contacts.

## Reference
@../../docs/CONTACT_ENRICHMENT_PIPELINE.md

## Troubleshooting

### Venv architecture errors (ImportError: incompatible architecture)

The `.venv/` occasionally gets x86_64 packages installed. If any script fails with `incompatible architecture (have 'x86_64', need 'arm64')`, fix the offending package:

```bash
source .venv/bin/activate && pip install --force-reinstall <package_name>
```

Known offenders (as of Mar 2026): `mmh3`, `impit`, `psycopg2-binary`, `pydantic-core`, `pydantic`, `jiter`, `cffi`, `cryptography`

### Apify returns 0 profiles (restricted LinkedIn)

If Step 1 succeeds but returns no data, the profile is restricted. Fallback:
1. Try `enrich_web_research.py --ids {ID}` (Perplexity)
2. If that also fails (low confidence), manually set known fields via SQL UPDATE (headline, summary_experience, enrich_companies_worked, etc.)
3. Continue with Steps 3+ which work with whatever data exists

### Steps that can run independently

All steps are independently runnable. If one fails, skip it and continue. Steps 3-4 and 6-10 work even without Apify enrichment data.

## Instructions

When the user asks to add or enrich a contact, follow this workflow:

### Step 0: Insert (if new contact)

If the contact doesn't exist in the DB, insert via Supabase MCP:

```sql
INSERT INTO contacts (first_name, last_name, email, linkedin_url, company, position, connection_type, enrichment_source)
VALUES ('First', 'Last', 'email@example.com', 'https://www.linkedin.com/in/slug/', 'Company', 'Title', 'Direct', 'manual-2026');
```

Get the new contact's ID from the insert result.

### Step 1: LinkedIn Profile Enrichment (Apify)

```bash
cd /Users/Justin/Code/TrueSteele/contacts && source .venv/bin/activate && python scripts/enrichment/enrich_contacts_apify.py --ids {ID}
```

Writes: headline, summary, company, position, linkedin_username, enrich_employment, enrich_education, enrich_skills, enrich_certifications, enrich_volunteering, enrich_honors_awards, enrich_board_positions, and ~20 more enrichment columns. Sets `enrichment_source='apify'`.

**Cost:** ~$0.004 (Apify profile scrape)

### Step 2: LinkedIn Posts (Apify)

```bash
cd /Users/Justin/Code/TrueSteele/contacts && source .venv/bin/activate && python scripts/enrichment/scrape_contact_posts.py --ids {ID}
```

Writes: rows in `contact_linkedin_posts` table (post content, engagement, dates).

**Cost:** ~$0.03 (up to 15 posts scraped)

### Step 2b: LinkedIn Article Reactions (DB lookup)

Check if the contact has reacted to any of Justin's LinkedIn articles. This is a free DB lookup against the existing `linkedin_article_reactions` table (2,293 reactions across 9 articles).

Query via Supabase MCP:

```sql
SELECT r.id, r.article_title, r.reaction_type, r.reactor_name, r.reactor_headline
FROM linkedin_article_reactions r
WHERE r.contact_id IS NULL
  AND LOWER(r.reactor_name) LIKE LOWER('%{LAST_NAME}%');
```

If matches are found, link them and build the summary:

```sql
-- Link matching reactions to the contact
UPDATE linkedin_article_reactions SET contact_id = {ID} WHERE id IN ({MATCHED_IDS});

-- Build linkedin_reactions JSONB summary
UPDATE contacts SET linkedin_reactions = '{
  "total_reactions": N,
  "reaction_types": {"like": X, "insightful": Y, ...},
  "articles_reacted_to": ["Article Title 1", ...],
  "article_count": N,
  "last_updated": "2026-02-25T00:00:00Z"
}'::jsonb WHERE id = {ID};
```

If no matches found, skip — the contact simply hasn't reacted to Justin's articles.

**Cost:** Free (DB lookup only)

### Step 3: AI Tagging (GPT-5 mini)

```bash
cd /Users/Justin/Code/TrueSteele/contacts && source .venv/bin/activate && python scripts/intelligence/tag_contacts_gpt5m.py --ids {ID}
```

Writes: `ai_tags` JSONB (proximity, affinity, outreach, capacity, outdoorithm_fit), `ai_proximity_score`, `ai_capacity_score`, `ai_outdoorithm_fit`.

**Cost:** ~$0.002

### Step 4: Vector Embeddings

```bash
cd /Users/Justin/Code/TrueSteele/contacts && source .venv/bin/activate && python scripts/intelligence/generate_embeddings.py --ids {ID}
```

Writes: `profile_embedding` (768d), `interests_embedding` (768d) via pgvector.

**Cost:** ~$0.00004

### Step 5: Email Finding (if no email)

Only run if the contact has no email address:

```bash
cd /Users/Justin/Code/TrueSteele/contacts && source .venv/bin/activate && python scripts/intelligence/find_emails.py --ids {ID}
```

Tries Tomba email-finder first (free, 25 lookups/month). If Tomba finds the email, verifies with ZeroBounce (1 credit). If Tomba misses, falls back to permutation + ZeroBounce pipeline (3-10 credits). Use `--skip-tomba` for batch runs to conserve quota.

Writes: `email` column (verified via Tomba/ZeroBounce + GPT validation).

**Cost:** ~$0.008 (if Tomba hit) to ~$0.05 (permutation fallback)

### Step 6: Communication History (Gmail)

```bash
cd /Users/Justin/Code/TrueSteele/contacts && source .venv/bin/activate && python scripts/intelligence/gather_comms_history.py --ids {ID}
```

Writes: rows in `contact_email_threads` table, updates `communication_history` JSONB.

**Cost:** Free (Gmail API)

### Step 7: Calendar Meetings

```bash
cd /Users/Justin/Code/TrueSteele/contacts && source .venv/bin/activate && python scripts/intelligence/gather_calendar_meetings.py --ids {ID}
```

Writes: rows in `contact_calendar_events` table, meeting summaries.

**Cost:** ~$0.002 (GPT summarization)

### Step 8: Rebuild Comms Summary

```bash
cd /Users/Justin/Code/TrueSteele/contacts && source .venv/bin/activate && python scripts/intelligence/rebuild_comms_summary.py --ids {ID}
```

Writes: `comms_summary` JSONB, `comms_last_date`, `comms_thread_count`, `comms_meeting_count`, `comms_last_meeting`.

**Cost:** Free (aggregation only)

### Step 9: Comms Closeness Scoring

```bash
cd /Users/Justin/Code/TrueSteele/contacts && source .venv/bin/activate && python scripts/intelligence/score_comms_closeness.py --ids {ID}
```

Writes: `comms_closeness`, `comms_momentum`, `comms_reasoning`.

**Cost:** ~$0.002

### Step 10: Ask Readiness Scoring

```bash
cd /Users/Justin/Code/TrueSteele/contacts && source .venv/bin/activate && python scripts/intelligence/score_ask_readiness.py --ids {ID}
```

Writes: `ask_readiness` JSONB with score, tier, reasoning per goal.

**Cost:** ~$0.002

### Verification

After running all steps, confirm enrichment with:

```sql
SELECT id, first_name, last_name, email, headline, company,
       enrichment_source,
       ai_tags IS NOT NULL as has_tags,
       profile_embedding IS NOT NULL as has_embedding,
       linkedin_reactions IS NOT NULL as has_reactions,
       comms_summary IS NOT NULL as has_comms,
       ask_readiness IS NOT NULL as has_ask_readiness,
       comms_closeness
FROM contacts WHERE id = {ID};
```

### Notes

- **Total cost per contact:** ~$0.08-0.10 (mostly Apify + ZeroBounce)
- **Total time:** ~2-3 minutes (most steps are <10 seconds)
- **All scripts must be run from the project root** with venv activated
- Steps 1-4 require LinkedIn URL; Step 5 requires company/name; Steps 6-10 work with whatever data exists
- Steps can be run independently for re-enrichment (e.g., re-tag with `--ids`)
- For contacts WITHOUT LinkedIn, use `enrich_web_research.py --ids {ID}` instead of Steps 1-2

### Pipelines NOT included (batch-only)

- **Real estate** (`enrich_real_estate.py`) — needs city/state, high false-positive risk for singles
- **FEC donations** (`enrich_fec_donations.py`) — needs city/state, US-only
- **Deduplication** (`deduplicate_contacts.py`) — batch operation
- **SMS/Call sync** (`sync_phone_backup.py`) — daily batch from phone backup
