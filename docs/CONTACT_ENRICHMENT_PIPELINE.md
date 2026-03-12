# Contact Enrichment Pipeline

**Last updated:** 2026-02-25

Single source of truth for adding and enriching contacts in the TrueSteele contacts database. Covers the full lifecycle from insertion to fully enriched profile.

## Pipeline Overview

```
Insert contact (Step 0)
    │
    ├── LinkedIn Profile (Step 1) ─── Apify scrape → flat + JSONB columns
    ├── LinkedIn Posts (Step 2) ───── Apify scrape → contact_linkedin_posts table
    │
    ├── Article Reactions (Step 2b) ── DB lookup → linkedin_reactions JSONB
    │
    ├── AI Tagging (Step 3) ────────── GPT-5 mini → ai_tags, proximity, capacity
    ├── Embeddings (Step 4) ────────── text-embedding-3-small → pgvector 768d
    │
    ├── Email Finding (Step 5) ─────── ZeroBounce + GPT → email column
    │
    ├── Comms: Email (Step 6) ──────── Gmail search → contact_email_threads
    ├── Comms: Calendar (Step 7) ───── Calendar scan → contact_calendar_events
    ├── Comms: Rebuild (Step 8) ────── Aggregation → comms_summary JSONB
    ├── Comms: Closeness (Step 9) ──── GPT scoring → comms_closeness
    │
    └── Ask Readiness (Step 10) ────── GPT scoring → ask_readiness JSONB
```

## Step Details

### Step 0: Insert Contact

**Minimum required fields:** `first_name`, `last_name`

**Recommended fields for full enrichment:**
| Field | Type | Notes |
|-------|------|-------|
| `first_name` | text | Required |
| `last_name` | text | Required |
| `email` | text | If known |
| `linkedin_url` | text | Required for Steps 1-2 |
| `company` | text | Current employer |
| `position` | text | Current title |
| `connection_type` | text | 'Direct', 'Indirect', etc. |
| `enrichment_source` | text | 'manual-2026' for manual inserts |

### Step 1: LinkedIn Profile Enrichment

**Script:** `scripts/enrichment/enrich_contacts_apify.py --ids {ID}`
**API:** Apify `harvestapi/linkedin-profile-scraper` ($0.004/profile)
**Prerequisite:** `linkedin_url` must be set

**Columns written (flat):**
`headline`, `summary`, `company`, `position`, `linkedin_username`, `linkedin_profile` (photo), `num_followers`, `connections`, `school_name_education`, `degree_education`, `field_of_study_education`, `role_volunteering`, `company_name_volunteering`, `title_publications`, `title_awards`, `company_name_awards`, `title_projects`

**Columns written (JSONB):**
`enrich_employment`, `enrich_education`, `enrich_skills_detailed`, `enrich_certifications`, `enrich_volunteering`, `enrich_publications`, `enrich_honors_awards`, `enrich_languages`, `enrich_projects`

**Columns written (computed):**
`enrich_current_company`, `enrich_current_title`, `enrich_current_since`, `enrich_years_in_current_role`, `enrich_total_experience_years`, `enrich_number_of_positions`, `enrich_number_of_companies`, `enrich_companies_worked`, `enrich_titles_held`, `enrich_skills`, `enrich_schools`, `enrich_fields_of_study`, `enrich_highest_degree`, `enrich_board_positions`, `enrich_volunteer_orgs`, `enrich_publication_count`, `enrich_award_count`, `enrich_connections`, `enrich_follower_count`, `enrich_profile_pic_url`

Sets: `enrichment_source = 'apify'`, `enriched_at = now()`

### Step 2: LinkedIn Posts

**Script:** `scripts/enrichment/scrape_contact_posts.py --ids {ID}`
**API:** Apify `harvestapi/linkedin-profile-posts` ($0.002/post, max 15 posts)
**Prerequisite:** `enrichment_source = 'apify'` (run Step 1 first)

**Table:** `contact_linkedin_posts`
| Column | Type | Notes |
|--------|------|-------|
| `contact_id` | int | FK to contacts |
| `linkedin_url` | text | Normalized profile URL |
| `post_url` | text | Post permalink |
| `post_content` | text | Full post text |
| `post_date` | timestamptz | When posted |
| `engagement_likes` | int | |
| `engagement_comments` | int | |
| `engagement_shares` | int | |
| `raw_data` | jsonb | Full Apify response |

### Step 2b: LinkedIn Article Reactions

**Method:** Direct DB lookup against `linkedin_article_reactions` table
**Cost:** Free
**Prerequisite:** None (works on name match)

Checks if the contact has reacted to any of Justin's LinkedIn articles (2,293 reactions across 9 articles already stored). Matches unlinked reactions by last name, then verifies first name + headline. If found, links the reaction rows and builds a summary.

**Column:** `linkedin_reactions` JSONB
```json
{
  "total_reactions": 3,
  "reaction_types": {"like": 2, "insightful": 1},
  "articles_reacted_to": ["Article Title 1", "Article Title 2"],
  "article_count": 2,
  "last_updated": "2026-02-25T00:00:00Z"
}
```

**Downstream usage:** Consumed by ask-readiness scoring (Step 10) as an engagement signal. Contacts who react to 3+ articles are considered warm even without other comms data.

**Batch re-import:** To re-import all reactions from scratch (e.g., after adding new articles), use `scripts/intelligence/import_article_reactions.py --match-only`.

### Step 3: AI Tagging

**Script:** `scripts/intelligence/tag_contacts_gpt5m.py --ids {ID}`
**API:** OpenAI GPT-5 mini (structured output)
**Prerequisite:** Best with LinkedIn data (Steps 1-2), but works without

**Column:** `ai_tags` JSONB
```json
{
  "proximity": {"shared_employers": [...], "shared_schools": [...], "score": 75, "tier": "warm"},
  "affinity": {"topics": [...], "primary_interests": [...], "talking_points": [...]},
  "outreach": {"hooks": [...], "opener": "...", "approach": "..."},
  "capacity": {"score": 80, "tier": "major_donor"},
  "outdoorithm_fit": "high"
}
```

**Also sets:** `ai_proximity_score`, `ai_proximity_tier`, `ai_capacity_score`, `ai_capacity_tier`, `ai_outdoorithm_fit`, `ai_tags_generated_at`, `ai_tags_model`

### Step 4: Vector Embeddings

**Script:** `scripts/intelligence/generate_embeddings.py --ids {ID}`
**API:** OpenAI text-embedding-3-small (768 dimensions)

**Columns:** `profile_embedding` vector(768), `interests_embedding` vector(768)

Used for semantic search in the AI Filter Co-pilot UI.

### Step 5: Email Finding

**Script:** `scripts/intelligence/find_emails.py --ids {ID}`
**APIs:** Tomba (primary lookup, free tier 25/month), ZeroBounce ($0.008/verification), GPT-5 mini (validation)
**Prerequisite:** Contact must have no email; needs company/name

Pipeline: Tomba email-finder (try first) → if miss: company → domain discovery → email permutations → ZeroBounce verify → GPT validate → save

Tomba checks its database of known emails by name + domain. If found with score >= 70 and name match confirmed, verifies with ZeroBounce (1 credit). If Tomba misses, falls through to the existing permutation pipeline (3-10 ZeroBounce credits).

Use `--skip-tomba` flag for batch runs to conserve the 25 searches/month free quota.

**Column:** `email`

### Step 6: Communication History (Email)

**Script:** `scripts/intelligence/gather_comms_history.py --ids {ID}`
**API:** Gmail API (free via Google Workspace MCP)
**Prerequisite:** Contact must have an email address

Searches 5 Gmail accounts for threads with the contact.

**Table:** `contact_email_threads`
**Column:** `communication_history` JSONB, `comms_last_date`, `comms_thread_count`

### Step 7: Calendar Meetings

**Script:** `scripts/intelligence/gather_calendar_meetings.py --ids {ID}`
**API:** Google Calendar API (free via Google Workspace MCP)

Scans calendars for events with the contact's email as an attendee.

**Table:** `contact_calendar_events`
**Columns:** `comms_meeting_count`, `comms_last_meeting`

### Step 8: Rebuild Comms Summary

**Script:** `scripts/intelligence/rebuild_comms_summary.py --ids {ID}`
**Cost:** Free (local aggregation)

Aggregates email threads + calendar events + SMS + calls → unified summary.

**Column:** `comms_summary` JSONB
```json
{
  "email": {"thread_count": 5, "last_date": "2026-02-10", ...},
  "calendar": {"meeting_count": 3, "last_date": "2026-01-15", ...},
  "sms": {...},
  "calls": {...},
  "overall": {"total_interactions": 12, "last_contact": "2026-02-10", ...}
}
```

### Step 9: Comms Closeness

**Script:** `scripts/intelligence/score_comms_closeness.py --ids {ID}`
**API:** GPT-5 mini

Scores relationship closeness based on communication patterns.

**Columns:** `comms_closeness` (active_inner_circle/regular_contact/occasional/dormant/one_way/no_history), `comms_momentum` (growing/stable/fading/inactive), `comms_reasoning`

### Step 10: Ask Readiness

**Script:** `scripts/intelligence/score_ask_readiness.py --ids {ID}`
**API:** GPT-5 mini (structured output)

Holistic scoring using ALL enrichment data: LinkedIn profile, FEC donations, real estate, comms history, OC engagement.

**Column:** `ask_readiness` JSONB (keyed by goal)
```json
{
  "outdoorithm_fundraising": {
    "score": 85,
    "tier": "ready_now",
    "reasoning": "...",
    "top_goals": [...],
    "risk_factors": [...]
  }
}
```

**Tiers:** `ready_now` (75+), `cultivate_first` (50-74), `long_term` (25-49), `not_a_fit` (0-24)

## Cost Summary

| Step | Cost | API |
|------|------|-----|
| 1. LinkedIn Profile | $0.004 | Apify |
| 2. LinkedIn Posts | ~$0.03 | Apify |
| 2b. Article Reactions | Free | DB lookup |
| 3. AI Tagging | ~$0.002 | OpenAI |
| 4. Embeddings | ~$0.00004 | OpenAI |
| 5. Email Finding | ~$0.05 | ZeroBounce + OpenAI |
| 6. Comms History | Free | Gmail API |
| 7. Calendar | ~$0.002 | Calendar API + OpenAI |
| 8. Comms Rebuild | Free | Local |
| 9. Comms Closeness | ~$0.002 | OpenAI |
| 10. Ask Readiness | ~$0.002 | OpenAI |
| **Total** | **~$0.09** | |

## Batch-Only Pipelines (not included)

| Pipeline | Script | Why not single-contact |
|----------|--------|----------------------|
| Real Estate | `enrich_real_estate.py` | Needs city/state, skip-trace has false-positive risk |
| FEC Donations | `enrich_fec_donations.py` | Needs city/state, US-only, common name collision risk |
| Deduplication | `deduplicate_contacts.py` | Batch comparison operation |
| SMS/Call Sync | `sync_phone_backup.py` | Daily batch from phone backup |
| Web Research | `enrich_web_research.py --ids {ID}` | Only for contacts WITHOUT LinkedIn |

## All Scripts Supporting --ids

| Script | Flag | Notes |
|--------|------|-------|
| `enrich_contacts_apify.py` | `--ids 123,456` | Auto-enables `--force` |
| `scrape_contact_posts.py` | `--ids 123,456` | Auto-enables `--force` |
| `tag_contacts_gpt5m.py` | `--ids 123,456` | |
| `generate_embeddings.py` | `--ids 123,456` | Auto-enables `--force` |
| `find_emails.py` | `--ids 123,456` | Only contacts missing email |
| `gather_comms_history.py` | `--ids 123,456` | Auto-enables `--force` |
| `gather_calendar_meetings.py` | `--ids 123,456` | Auto-enables `--force` |
| `rebuild_comms_summary.py` | `--ids 123,456` | Also has `--contact-id` |
| `score_comms_closeness.py` | `--ids 123,456` | Also has `--contact-id` |
| `score_ask_readiness.py` | `--ids 123,456` | |
| `enrich_web_research.py` | `--ids 123,456` | For non-LinkedIn contacts |
