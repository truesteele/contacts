# LinkedIn Enrichment: Master Reference

**Last updated:** 2026-03-02

This is the single source of truth for all LinkedIn enrichment at Kindora. It covers discovery, scraping, batch enrichment, URL normalization, failure handling, and production lessons learned.

**Note:** This document replaces the former `CONTACT_ENRICHMENT_LINKEDIN_DISCOVERY.md` and `LINKEDIN_ENRICHMENT_GUIDE.md`, which have been deleted.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Pipeline A: Single-Contact Enrichment (API)](#2-pipeline-a-single-contact-enrichment-api)
3. [Pipeline B: LinkedIn Post Scraping (API)](#3-pipeline-b-linkedin-post-scraping-api)
4. [Pipeline C: Network Import](#4-pipeline-c-network-import)
5. [Pipeline D: Batch Cohort Enrichment (Camelback)](#5-pipeline-d-batch-cohort-enrichment-camelback)
6. [Pipeline E: Bulk Contacts Enrichment](#6-pipeline-e-bulk-contacts-enrichment)
7. [Pipeline F: LinkedIn CSV Import](#7-pipeline-f-linkedin-csv-import)
8. [Pipeline G: Bulk Contact Post Scraping](#8-pipeline-g-bulk-contact-post-scraping)
9. [LinkedIn URL Discovery Cascade](#9-linkedin-url-discovery-cascade)
10. [Apify: The Core LinkedIn Data Provider](#10-apify-the-core-linkedin-data-provider)
11. [URL Normalization](#11-url-normalization)
12. [Failure Modes and Remediation](#12-failure-modes-and-remediation)
13. [Database Schema](#13-database-schema)
14. [Environment Variables](#14-environment-variables)
15. [Cost Reference](#15-cost-reference)
16. [Key Files](#16-key-files)
17. [Production Run Log: Feb 2026](#17-production-run-log-feb-2026)
18. [Network Intelligence Pipelines](#18-network-intelligence-pipelines-feb-2026) (Pipelines H–Y + Daily Sync + Campaign Tools)
19. [Influencer Analysis Pipeline](#19-influencer-analysis-pipeline-z) (Pipeline Z)

---

## 1. System Overview

The contacts database (2,940 rows) is enriched through multiple pipelines. Pipelines A-G handle LinkedIn data via Apify. Pipelines H-Y handle network intelligence (AI tagging, embeddings, real estate, FEC, communications, scoring). Pipeline Z handles influencer content analysis. A daily sync keeps comms data fresh.

| Pipeline | Purpose | Trigger | Scale |
|----------|---------|---------|-------|
| **A** | Enrich a single funder contact | User clicks "Enrich" in UI | 1 contact |
| **B** | Scrape a contact's LinkedIn posts | User clicks "Scrape Posts" | 1 contact |
| **C** | Import a user's LinkedIn connection | User imports from network | 1 contact |
| **D** | Bulk-enrich a standalone cohort | CLI script (e.g., Camelback) | 10-100 contacts |
| **E** | Bulk-enrich the contacts database | CLI script with concurrency | 1,000-10,000 contacts |
| **F** | Import LinkedIn Connections.csv | CLI script | 1,000-10,000 contacts |
| **G** | Bulk-scrape contact LinkedIn posts | CLI script with concurrency | 1,000-10,000 contacts |
| **H** | AI tagging (GPT-5 mini) | CLI script | 2,400 contacts |
| **I** | Vector embeddings | CLI script | 2,400 contacts |
| **J** | Deduplication | CLI script | full DB |
| **K** | Real estate enrichment | CLI script | 1,000-2,000 contacts |
| **L** | FEC political donations | CLI script | 1,000-2,000 contacts |
| **M** | Email communication history | CLI script | 5 Gmail accounts |
| **N** | Ask-readiness scoring | CLI script | 2,900 contacts |
| **O** | SMS communication history | CLI script | 1,000-3,000 convos |
| **P** | Import LinkedIn DM messages | CLI script | 1,000-3,000 messages |
| **Q** | Import LinkedIn article reactions | CLI script | 1,000-5,000 reactions |
| **R** | Scrape LinkedIn post reactions | CLI script | 5,000-10,000 reactions |
| **S** | Email finder (ZeroBounce) | CLI script | 500-1,000 contacts |
| **T** | Web research (non-LinkedIn contacts) | CLI script | 30-100 contacts |
| **U** | Comms summary aggregator | CLI script | full DB |
| **V** | Comms closeness scoring (GPT) | CLI script | 1,200 contacts |
| **W** | Calendar meeting history | CLI script | 5 Google accounts |
| **X** | Phone backup sync (SMS + calls) | CLI / daily sync | incremental |
| **Y** | Overlap scoring (GPT) | CLI script | 2,400 contacts |
| **Z** | Influencer post analysis + reactor matching | CLI script | per influencer |

**Shared infrastructure:**
- **Apify** `harvestapi/linkedin-profile-scraper` — $0.004/profile
- **Apify** `harvestapi/linkedin-profile-posts` — $0.002/post
- **Apify** `apimaestro/linkedin-post-reactions` — ~$0.003/post (reactions only)
- **OpenAI GPT-5 mini** — structured output for tagging, scoring, validation ($0.002/call avg)
- **OpenAI text-embedding-3-small** — 768d embeddings for semantic search
- **ZeroBounce** — email verification ($0.008/credit)
- **Perplexity sonar-pro** — web research for non-LinkedIn contacts
- **Google Workspace MCP** — 5 Gmail/Calendar accounts for comms history
- **Supabase** — PostgreSQL + pgvector + Storage + RLS
- **URL normalization** — All pipelines should normalize URLs before sending to Apify
- **Daily sync** — launchd at 8am PT for email, calendar, SMS+calls

---

## 2. Pipeline A: Single-Contact Enrichment (API)

**Entry:** `POST /api/contact-enrichment/enrich`
**Service:** `ContactEnrichmentService.enrich_contact()`
**Cost to user:** 5 Kira credits (new) or 2 credits (refresh >6 months)

### Flow

```
Request(name, organization, title, funder_ein)
│
├── Cache check (linkedin_username or name+org match)
│   ├── Fresh (<6 months) → return cached (0 credits)
│   └── Stale/missing → continue
│
├── Credit check (org must have sufficient balance)
│
├── Discovery cascade (if no LinkedIn URL known)
│   ├── Tier 0.5: Tavily search (~$0.001, ~2s)
│   ├── Tier 1: Firecrawl agent (~$0.22, ~2min)
│   ├── Tier 1.5: IRS 990 lookup (free)
│   └── Tier 2: OpenAI o4-mini (~$0.36, ~30s)
│
├── Apify profile scrape ($0.004)
├── Photo download → Supabase Storage
├── Tomba email lookup ($0.012, if no email found)
├── Atomic DB write (enrich_contact_atomic RPC)
└── Return enriched person + quality score
```

### Key details

- **Deduplication:** `linkedin_username` is the primary key for person identity
- **Photo handling:** LinkedIn CDN URLs expire; photos are downloaded and re-uploaded to Supabase Storage (`kindora-images` bucket, `profile-photos/` prefix)
- **Rate limit:** 10 requests per 60 seconds per organization
- **Idempotency:** SHA-256 hash of `org_id + normalized_name + org + title + funder_staff_id + refresh_flag`

---

## 3. Pipeline B: LinkedIn Post Scraping (API)

**Entry:** `POST /api/outreach/scrape-linkedin-posts`
**Service:** `ApifyPostScraperService.scrape_and_store_posts()`

```
LinkedIn URL
  └─ Apify harvestapi/linkedin-profile-posts
     ├─ maxPosts: 50
     ├─ scrapeReactions: false
     ├─ includeReposts: false
     ├─ includeQuotePosts: true
     └─ Filter to last 6 months → upsert to linkedin_post_history
```

**Post date parsing** handles three Apify formats:
```python
{"postedAt": {"timestamp": 1706745600000}}   # ms timestamp in nested dict
{"postedAt": {"date": "2024-01-31T..."}}      # ISO string in nested dict
{"postedAt": 1706745600000}                   # raw ms timestamp
```

**Downstream usage:** Posts feed into outreach personalization (`outreach_context_builder.py`), intel briefs, and final memos.

---

## 4. Pipeline C: Network Import

**Entry:** `POST /api/network/import`
**Service:** `NetworkImportService.import_network_connection()`

Two methods:
- **Apify** (5 credits): Takes LinkedIn URL, calls Apify scraper, stores full profile
- **GPT parsing** (free): Takes copy-pasted profile text, parses with GPT-5 mini

---

## 5. Pipeline D: Batch Cohort Enrichment (Camelback)

Reference implementation for enriching a standalone cohort with known LinkedIn URLs.

**Scripts:**
- `scripts/enrichment/enrich_camelback_experts.py` — Profile + post enrichment
- `scripts/enrichment/generate_coach_profiles.py` — AI profile generation + embeddings

### Three-step workflow

```
Step 1: Data collection → insert into cohort table with linkedin_url
Step 2: Apify enrichment (profiles + posts) → update cohort table + posts table
Step 3: AI profiles (GPT-5-mini + text-embedding-3-small) → search_profiles table
```

### CLI usage

```bash
python scripts/enrichment/enrich_camelback_experts.py --test       # 1 expert
python scripts/enrichment/enrich_camelback_experts.py               # all
python scripts/enrichment/enrich_camelback_experts.py --posts-only  # posts only
python scripts/enrichment/enrich_camelback_experts.py --months 6    # custom window
```

### Cost (73 experts)

| Step | Total |
|------|-------|
| Apify profiles | ~$0.29 |
| Apify posts (~50/expert) | ~$7.30 |
| GPT-5-mini profiles | ~$0.15 |
| Embeddings | ~$0.001 |
| **Total** | **~$7.74** |

### Adapting for a new cohort

1. Create cohort table (`id`, `name`, `linkedin_url`, `enriched_at`)
2. Create posts table with unique constraint on `(linkedin_url, post_url)`
3. Copy and adapt the enrichment script (change table names, field mapping)
4. If AI summaries needed, copy and adapt `generate_coach_profiles.py`
5. Run enrichment first, then AI generation

---

## 6. Pipeline E: Bulk Contacts Enrichment

Developed for the full contacts database (2,940 contacts as of Mar 2026). Uses concurrent batch processing for speed.

**Script:** `scripts/enrichment/enrich_contacts_apify.py`

### Key differences from Pipeline D

| Feature | Pipeline D (Camelback) | Pipeline E (Contacts) |
|---------|----------------------|----------------------|
| Scale | 73 records | 2,498 records |
| Concurrency | Sequential (1 at a time) | 25 URLs/batch, 8 concurrent runs |
| URL normalization | None | Decodes percent-encoding, adds `www.` |
| Data storage | Cohort-specific table | `contacts` table (flat + JSONB columns) |
| Posts | Yes | Via Pipeline G (separate script) |
| Duration | ~15 minutes | ~4 minutes |

### CLI usage

```bash
python scripts/enrichment/enrich_contacts_apify.py --test          # 1 contact
python scripts/enrichment/enrich_contacts_apify.py --batch 50      # 50 contacts
python scripts/enrichment/enrich_contacts_apify.py --start-from 500 # resume from id
python scripts/enrichment/enrich_contacts_apify.py --force         # re-enrich apify
python scripts/enrichment/enrich_contacts_apify.py                 # full run
```

### Architecture

```
get_contacts() ──► paginated fetch (1000/page, skips enrichment_source='apify')
        │
        ▼
Split into batches of 25 URLs
        │
        ▼
ThreadPoolExecutor (8 workers)
  ├── Batch 1: enrich_profile_batch([25 URLs]) ──► single Apify actor run
  ├── Batch 2: enrich_profile_batch([25 URLs]) ──► single Apify actor run
  ├── ...
  └── Batch N: enrich_profile_batch([remaining])
        │
        ▼
For each result: map_profile_to_updates() → save_profile()
```

### Concurrency design

Each call to `enrich_profile_batch()` sends up to 25 URLs to a **single Apify actor run**. The actor scrapes them in parallel internally. With 8 concurrent threads, we get 8 actor runs at once (200 profiles being scraped simultaneously). Apify Starter plan allows 32 concurrent runs, so 8 is conservative.

### Field mapping strategy

The script writes to **both** the legacy flat columns and new structured JSONB columns:

**Overwritten flat columns** (LinkedIn-sourced):
- `headline`, `summary`, `company`, `position`
- `linkedin_username`, `linkedin_profile` (photo URL)
- `num_followers`, `connections`
- `school_name_education`, `degree_education`, `field_of_study_education`
- `role_volunteering`, `company_name_volunteering`
- `title_publications`, `title_awards`, `company_name_awards`, `title_projects`

**New JSONB columns** (added via migration):
- `enrich_employment`, `enrich_education`, `enrich_skills_detailed`
- `enrich_certifications`, `enrich_volunteering`, `enrich_publications`
- `enrich_honors_awards`, `enrich_languages`, `enrich_projects`

**Computed summary columns**:
- `enrich_current_company`, `enrich_current_title`, `enrich_current_since`
- `enrich_years_in_current_role`, `enrich_total_experience_years`
- `enrich_number_of_positions`, `enrich_number_of_companies`
- `enrich_companies_worked`, `enrich_titles_held`, `enrich_skills`
- `enrich_schools`, `enrich_fields_of_study`, `enrich_highest_degree`
- `enrich_board_positions`, `enrich_volunteer_orgs`
- `enrich_publication_count`, `enrich_award_count`

**Preserved (never overwritten)**: emails, donor scores, Perplexity data, cultivation data, tags

### Board position extraction

Volunteering entries are scanned for board-related keywords (`board`, `director`, `trustee`, `advisor`, `advisory`). Matches populate `enrich_board_positions` and set `nonprofit_board_member = true`.

---

## 7. Pipeline F: LinkedIn CSV Import

Imports contacts from a LinkedIn "Connections" CSV export, deduplicates against existing contacts, and detects changed LinkedIn URLs.

**Script:** `scripts/import_linkedin_csv.py`

### Flow

```
LinkedIn Connections.csv
  │
  ├── Parse CSV (skip LinkedIn notes header, extract First Name, Last Name, URL, Email, Company, Position)
  │
  ├── Fetch all existing contacts from Supabase (paginated, 1000/page)
  │
  ├── Build lookup indexes:
  │   ├── By normalized LinkedIn URL (primary dedup key)
  │   └── By (first_name, last_name) lowercase (secondary dedup)
  │
  ├── For each CSV contact:
  │   ├── URL match found → skip (duplicate)
  │   ├── Name match found, no LinkedIn URL in DB → update with LinkedIn URL
  │   ├── Name match found, different LinkedIn URL → flag as URL change, update
  │   └── No match → insert as new contact
  │
  ├── Apply URL updates (batch)
  └── Insert new contacts (batches of 50, connection_type='Direct', enrichment_source='linkedin-csv-2026')
```

### CLI usage

```bash
python scripts/import_linkedin_csv.py
```

### Key details

- **CSV format:** LinkedIn exports a `Connections.csv` with a multi-line notes header before the actual CSV header (`First Name,Last Name,URL,Email Address,Company,Position,Connected On`)
- **Deduplication:** Primary match on normalized LinkedIn URL, secondary match on exact (first_name, last_name) lowercase
- **URL change detection:** When a name-matched contact has a different LinkedIn URL in the CSV vs DB, the script updates the DB URL. This catches people who changed their LinkedIn vanity URL slug.
- **URL additions:** Contacts in DB without a LinkedIn URL get one added if found in the CSV
- **New contacts:** Inserted with `connection_type='Direct'` and `enrichment_source='linkedin-csv-2026'`
- **Post-import:** Run Pipeline E (`enrich_contacts_apify.py`) to Apify-enrich the new contacts, then Pipeline G for posts, then AI tags

### Production run: Feb 20, 2026

- CSV: 2,764 contacts
- Existing DB: 2,410 contacts
- **527 new contacts** inserted
- **52 LinkedIn URL updates** (people who changed their vanity URLs)
- 2 contacts got LinkedIn URLs added where they had none
- 2,185 duplicates skipped

---

## 8. Pipeline G: Bulk Contact Post Scraping

Scrapes LinkedIn posts for all Apify-enriched contacts using concurrent batching. Stores posts in `contact_linkedin_posts` table.

**Script:** `scripts/enrichment/scrape_contact_posts.py`

### Architecture

```
get_contacts() ──► paginated fetch (enrichment_source='apify', has linkedin_url)
        │
        ├── Filter out contacts already in contact_linkedin_posts
        │
        ▼
Split into batches of 5 profile URLs
        │
        ▼
ThreadPoolExecutor (8 workers)
  ├── Batch 1: scrape_posts_batch([5 URLs]) ──► single Apify actor run
  ├── Batch 2: scrape_posts_batch([5 URLs]) ──► single Apify actor run
  ├── ...
  └── Batch N: scrape_posts_batch([remaining])
        │
        ▼
For each result: parse post dates → filter to time window → upsert to contact_linkedin_posts
```

### CLI usage

```bash
python scripts/enrichment/scrape_contact_posts.py --test           # Test with 1 contact
python scripts/enrichment/scrape_contact_posts.py --batch 50       # Process 50 contacts
python scripts/enrichment/scrape_contact_posts.py --start-from 500 # Resume from id >= 500
python scripts/enrichment/scrape_contact_posts.py --months 6       # Posts within last 6 months (default)
python scripts/enrichment/scrape_contact_posts.py --max-posts 15   # Max posts per contact (default: 15)
python scripts/enrichment/scrape_contact_posts.py --force          # Re-scrape contacts that already have posts
python scripts/enrichment/scrape_contact_posts.py                  # Full run (all enriched contacts)
```

### Key details

- **Apify actor:** `harvestapi/linkedin-profile-posts` at $0.002/post scraped
- **maxPosts parameter:** Controls how many posts Apify fetches per profile. Set to 15 by default to balance cost vs coverage. Apify charges per post scraped regardless of whether we store it.
- **Time window:** Only posts within the last 6 months are stored (older posts are scraped by Apify but filtered out before DB insert)
- **Batching:** 5 profile URLs per Apify actor run (smaller than Pipeline E's 25 because posts are heavier). The `profileUrls` array input allows batching multiple profiles in one run.
- **Concurrency:** 8 concurrent actor runs via ThreadPoolExecutor (same as Pipeline E)
- **Deduplication:** `contact_linkedin_posts` table has a unique constraint on `(linkedin_url, post_url)` — upsert safely handles re-runs
- **Skip logic:** Contacts already in `contact_linkedin_posts` are skipped unless `--force` is used
- **Post matching:** Posts are mapped back to contacts via the nested `author.publicIdentifier` field (exact match on LinkedIn username). Falls back to extracting username from `author.linkedinUrl` or `query.profilePublicIdentifier`.
- **Raw data:** Full Apify JSON response stored in `raw_data` JSONB column for each post (~3 KB/post)

### Apify Post Scraper input parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `profileUrls` | string[] | required | LinkedIn profile URLs to scrape |
| `maxPosts` | int | 0 (all) | Max posts per profile. **Controls cost.** |
| `scrapeReactions` | bool | false | Scrape reactions (charged as separate posts) |
| `scrapeComments` | bool | false | Scrape comments (charged as separate posts) |
| `maxReactions` | int | 0 (all) | Max reactions per post |
| `maxComments` | int | 0 (all) | Max comments per post |
| `includeReposts` | bool | true | Include shared posts without comments |
| `includeQuotePosts` | bool | true | Include shared posts with comments |

### Cost control

The `maxPosts` parameter is the primary cost lever:

| maxPosts | Cost/contact (max) | Est. for 2,900 contacts |
|----------|-------------------|------------------------|
| 50 | $0.10 | ~$290 |
| 25 | $0.05 | ~$145 |
| 15 | $0.03 | ~$87 |
| 10 | $0.02 | ~$58 |
| 5 | $0.01 | ~$29 |

Actual costs are lower because many contacts don't post at all or have fewer posts than the max.

---

## 9. LinkedIn URL Discovery Cascade

When a LinkedIn URL is not known, the system runs a tiered cascade. Each tier catches exceptions independently and falls through to the next.

### Tier 0: Cache Check

**File:** `contact_enrichment_service.py` — `_check_cached_result()`

Lookup order:
1. **LinkedIn username match** — extract username from URL, look up `contact_persons.linkedin_username`
2. **Normalized name + org match** — normalize name, find matching `contact_persons`, verify `person_board_positions` at target org

Cache freshness: 6 months. Stale records trigger refresh (2 credits instead of 5).

### Tier 0.5: Tavily Search

**File:** `tavily_enrichment.py`
**Cost:** ~$0.001 | **Speed:** ~1-2 seconds

1. Query: `"{name} {organization} {title} LinkedIn"`
2. Filter results for `linkedin.com/in/` URLs (exclude `/posts/` and `activity-`)
3. Name match scoring:
   - 0.9 = exact match
   - 0.75 = substring match
   - 0.6 = last name + first initial
   - 0.45 = last name only
   - Threshold: **>= 0.4**
4. Combined confidence: `(tavily_score * 0.6) + (name_score * 0.4)`

### Tier 1: Firecrawl Agent

**File:** `firecrawl_enrichment.py`
**Cost:** ~$0.22 | **Speed:** ~2-3 minutes | **Timeout:** 3 minutes

Structured search with Pydantic output. Returns `BoardMemberEnrichmentResult` with flat fields only (nested models cause Firecrawl failures). Escalates if `match_confidence < 0.4` or no `linkedin_url` found.

### Tier 1.5: IRS 990 Leadership

**File:** `funder_leadership_service.py`
**Cost:** Free | **Requirement:** `funder_ein` available

Fuzzy name match against IRS 990 board/staff data. Match threshold: 0.45. **Does not find LinkedIn URLs** — only confirms identity and org affiliation.

### Tier 2: OpenAI o4-mini

**File:** `contact_enrichment_service.py` — `_run_o4_mini_research()`
**Cost:** ~$0.36 | **Feature flag:** `CONTACT_ENRICHMENT_O4_MINI_ENABLED` (default: `true`)

Uses OpenAI Responses API with web search tool. Structured JSON output. Last resort — only runs if all previous tiers failed.

### Post-Processing: Tomba Email

**File:** `tomba_enrichment.py`
**Cost:** ~$0.012 per email

Runs only if no email found by previous tiers:
1. **LinkedIn Email Finder** — `POST /v1/linkedin?url={url}`
2. **Name + Domain Finder** (staff only) — `POST /v1/email-finder`
3. **Parent Company Domain Fallback** (staff only) — tries parent company domain for corporate foundations

Board members are excluded from name+domain lookup (they work elsewhere). Emails with Tomba confidence < 90 are verified via `POST /v1/email-verifier`.

---

## 10. Apify: The Core LinkedIn Data Provider

### Profile Scraper

**Actor:** `harvestapi/linkedin-profile-scraper`
**Cost:** $0.004/profile ($4 per 1,000)
**Mode:** "Profile details no email"

Returns:
- `headline`, `about`, `photo`, `publicIdentifier`
- `followerCount`, `connectionsCount`
- `experience[]` — employment with dates, type, location, description
- `education[]` — school, degree, field of study
- `skills[]` — can be strings or `{name: "..."}` objects
- `certifications[]`, `volunteering[]`/`volunteerExperience[]`
- `publications[]`, `honorsAndAwards[]`/`honors[]`
- `languages[]`, `projects[]`
- Open-to-work, verified, premium, influencer flags

### Field Mapping Reference

| Apify Field | Our Field | Notes |
|-------------|-----------|-------|
| `headline` | `headline` | Direct |
| `about` | `summary` / `about` | Direct |
| `photo` | `linkedin_profile` / `profile_picture_url` | CDN URL (may expire) |
| `publicIdentifier` | `linkedin_username` | URL slug |
| `followerCount` | `num_followers` / `enrich_follower_count` | Integer |
| `connectionsCount` | `connections` / `enrich_connections` | Integer |
| `experience[].position` | `job_title` | **Not** `title` |
| `experience[].companyName` | `company_name` | Direct |
| `experience[].dateRange.start` | `start_date` | `{year, month}` → `"2020-03"` |
| `experience[].dateRange.end` | `end_date` | Empty/null = current role |
| `volunteering[]` or `volunteerExperience[]` | varies | Field name differs between Apify versions |
| `honorsAndAwards[]` or `honors[]` | varies | Field name differs between Apify versions |

### Batch Usage

The profile scraper accepts multiple URLs in a single run:

```python
run_input = {"urls": ["url1", "url2", ..., "url25"]}
run = apify.actor("harvestapi/linkedin-profile-scraper").call(run_input=run_input)
items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
```

Match results back to input URLs via `item["linkedinUrl"]` or `item["publicIdentifier"]`.

### Post Scraper

**Actor:** `harvestapi/linkedin-profile-posts`
**Cost:** $0.002/post ($2 per 1,000)

```python
run_input = {
    "profileUrls": [linkedin_url],
    "maxPosts": 15,
    "scrapeReactions": False,
    "scrapeComments": False,
    "includeReposts": False,
    "includeQuotePosts": True,
}
```

**Response structure** (key fields per post item):

```json
{
  "type": "post",
  "id": "7419768155193131008",
  "linkedinUrl": "https://www.linkedin.com/posts/username_topic-activity-...",
  "content": "Full post text...",
  "author": {
    "publicIdentifier": "username",
    "linkedinUrl": "https://www.linkedin.com/in/username?miniProfileUrn=...",
    "name": "Display Name",
    "info": "Headline text"
  },
  "postedAt": {
    "timestamp": 1769010580824,
    "date": "2026-01-21T15:49:40.824Z"
  },
  "engagement": {
    "likes": 57,
    "comments": 5,
    "shares": 7
  },
  "query": {
    "profilePublicIdentifier": "https://www.linkedin.com/in/username"
  }
}
```

**Matching posts to contacts:** Use `author.publicIdentifier` (most reliable), fall back to extracting username from `author.linkedinUrl` or `query.profilePublicIdentifier`. Do NOT use top-level `authorUrl`/`profileUrl` — these fields do not exist in the response.

### Apify Billing (Starter Plan)

- $29/month with $29 prepaid usage
- $0.300 per compute unit (CU)
- Max 32 concurrent actor runs
- 32 GB actor RAM
- 30 datacenter proxies

---

## 11. URL Normalization

**Critical lesson from production:** Always normalize LinkedIn URLs before sending to Apify. Without normalization, ~10% of profiles fail.

### The `_normalize_linkedin_url()` method

```python
from urllib.parse import unquote

def _normalize_linkedin_url(url: str) -> str:
    url = url.strip().rstrip("/")
    # Decode percent-encoded characters (é, ñ, Gujarati, Chinese, etc.)
    url = unquote(url)
    # Ensure https://
    if not url.startswith("http"):
        url = "https://" + url
    # Ensure www. prefix
    url = url.replace("://linkedin.com/", "://www.linkedin.com/")
    return url
```

### Common URL issues encountered

| Issue | Example | Fix |
|-------|---------|-----|
| Percent-encoded accents | `marcela-mu%C3%B1iz` | `unquote()` → `marcela-muñiz` |
| Percent-encoded Unicode | `%E0%AA%B0%E0%AB%87...` (Gujarati) | `unquote()` decodes to actual chars |
| Chinese characters in URL | `%E4%B8%B9%E5%B0%BC%E7%88%BE` | `unquote()` or use vanity URL |
| Missing `www.` prefix | `linkedin.com/in/username` | Add `www.` |
| Trailing slash | `linkedin.com/in/username/` | Strip trailing `/` |
| Missing `https://` | `linkedin.com/in/username` | Prepend `https://` |

### URL matching for result mapping

When mapping Apify batch results back to input URLs, compare usernames after normalization:

```python
def _urls_match(url1: str, url2: str) -> bool:
    def extract_username(url):
        url = unquote(url).rstrip("/").lower()
        if "/in/" in url:
            return url.split("/in/")[-1].split("?")[0]
        return url
    return extract_username(url1) == extract_username(url2)
```

---

## 12. Failure Modes and Remediation

### Why Apify returns no data

From our production run of 2,498 contacts, 85 (3.4%) consistently returned no data after 3 attempts. Root causes:

| Category | Count | Description |
|----------|-------|-------------|
| **Private/restricted profiles** | ~70 | Profile exists but has privacy settings blocking scrapers |
| **URL slug changed** | ~7 | User changed their custom LinkedIn URL |
| **Profile deleted/deactivated** | ~3 | Account no longer exists |
| **Wrong URL stored** | ~3 | URL in DB doesn't match the intended person |
| **Apify scraper limitation** | ~2 | Valid profile but scraper can't process it |

### Remediation playbook

1. **URL-encoded failures:** Apply `unquote()` normalization (fixed 12 profiles in our run)
2. **Missing `www.` prefix:** Add prefix normalization (fixed some in our run)
3. **URL slug changed:** Web search `"{name} LinkedIn"` to find current URL, then update DB
4. **Wrong URL:** Search for correct person, update or clear the `linkedin_url` field
5. **Private profiles:** No fix available without authenticated LinkedIn API access
6. **Transient failures:** Simple re-run usually succeeds

### Duplicate detection

During URL discovery, check for duplicate contacts by LinkedIn URL:

```sql
SELECT linkedin_url, count(*), array_agg(id), array_agg(first_name || ' ' || last_name)
FROM contacts
WHERE linkedin_url IS NOT NULL
GROUP BY linkedin_url
HAVING count(*) > 1;
```

Keep the earlier record (lower ID), delete duplicates after merging any unique data.

### LinkedIn URL discovery for contacts without URLs

For contacts missing LinkedIn URLs, web search `"{name} {organization} LinkedIn"` and validate results. In our run:
- Started with 19 contacts without LinkedIn URLs
- Found 5 confirmed URLs via web search
- 3 were duplicate records (deleted)
- 11 genuinely have no LinkedIn presence (high-profile people who don't use LinkedIn)

---

## 13. Database Schema

### Contacts table (Pipeline E)

**Legacy flat columns** (pre-existing, overwritten by Apify):

```
headline, summary, company, position, linkedin_username, linkedin_profile,
num_followers, connections, school_name_education, degree_education,
field_of_study_education, role_volunteering, company_name_volunteering,
title_publications, title_awards, company_name_awards, title_projects
```

**New JSONB columns** (added Feb 2026 migration):

```sql
linkedin_username text,
enrich_employment jsonb,          -- [{job_title, company_name, start_date, end_date, is_current, ...}]
enrich_education jsonb,           -- [{school_name, degree, field_of_study, description}]
enrich_skills_detailed jsonb,     -- [{skill_name}]
enrich_certifications jsonb,      -- [{name, organization, url}]
enrich_volunteering jsonb,        -- [{organization, role, cause}]
enrich_publications jsonb,        -- [{name, publisher, url}]
enrich_honors_awards jsonb,       -- [{title, issuer}]
enrich_languages jsonb,           -- [{language, proficiency}]
enrich_projects jsonb,            -- [{name, description, url}]
enrichment_source text            -- 'apify' | 'enrich_layer' | null
```

### Kindora API tables (Pipelines A-C)

| Table | Purpose |
|-------|---------|
| `contact_persons` | Canonical person records (deduped by `linkedin_username`) |
| `person_employment` | Work history with dates, type, location |
| `person_education` | Education history |
| `person_board_positions` | Board/advisory roles |
| `person_skills` | LinkedIn skills with endorsement counts |
| `person_certifications` | Certifications |
| `person_projects` | Projects |
| `person_volunteering` | Volunteer work |
| `person_languages` | Languages |
| `person_publications` | Publications |
| `person_honors_awards` | Awards |
| `person_courses` | Courses |
| `person_patents` | Patents |
| `contact_enrichment_requests` | Audit trail |
| `linkedin_post_history` | Post content + engagement (client schema) |

### Contact posts table (Pipeline G)

```sql
contact_linkedin_posts (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id integer REFERENCES contacts(id) ON DELETE CASCADE,
    linkedin_url text NOT NULL,           -- normalized profile URL
    post_url text NOT NULL,               -- LinkedIn post/activity URL
    post_content text,                    -- full post text
    post_date timestamptz,                -- when the post was published
    engagement_likes integer DEFAULT 0,
    engagement_comments integer DEFAULT 0,
    engagement_shares integer DEFAULT 0,
    raw_data jsonb,                       -- full Apify JSON response (~3 KB/post)
    scraped_at timestamptz DEFAULT now(),
    UNIQUE(linkedin_url, post_url)        -- upsert key
)
```

Indexes: `contact_id`, `linkedin_url`, `post_date`

### Article reactions table (Pipeline Q)

```sql
linkedin_article_reactions (
    id SERIAL PRIMARY KEY,
    article_title TEXT NOT NULL,
    reaction_type TEXT NOT NULL,       -- like, insightful, love, support, celebrate
    reactor_name TEXT NOT NULL,        -- name as shown on LinkedIn
    reactor_headline TEXT,
    connection_degree TEXT,            -- 1st, 2nd, 3rd+
    contact_id INT REFERENCES contacts(id),  -- matched contact (nullable)
    match_method TEXT,                 -- exact, fuzzy, gpt, unmatched
    match_confidence REAL,
    created_at TIMESTAMPTZ DEFAULT now()
)
```

Indexes: `contact_id`, `article_title`

### Post reactions table (Pipeline R)

```sql
post_reactions (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    post_url TEXT NOT NULL,                    -- LinkedIn post URL
    post_date TEXT,                            -- ISO date string
    post_snippet TEXT,                         -- first 150 chars of post
    reactor_name TEXT NOT NULL,                -- name as shown on LinkedIn
    reactor_headline TEXT,
    reactor_linkedin_urn TEXT NOT NULL,        -- urn:li:fsd_profile:ACoAAA...
    reaction_type TEXT DEFAULT 'LIKE',         -- LIKE, EMPATHY, INTEREST, PRAISE, APPRECIATION, ENTERTAINMENT
    contact_id INT REFERENCES contacts(id),   -- matched contact (nullable)
    match_method TEXT,                         -- exact, fuzzy, gpt, unmatched
    match_confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(post_url, reactor_linkedin_urn)     -- upsert key
)
```

Indexes: `contact_id`, `post_url`, `reactor_linkedin_urn`

### Calendar events table (Pipeline W)

```sql
contact_calendar_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id integer REFERENCES contacts(id),
    account_email text NOT NULL,           -- which Google account
    event_id text NOT NULL,                -- Google Calendar event ID
    event_summary text,
    event_start timestamptz,
    event_end timestamptz,
    attendees jsonb,                       -- [{email, name, response_status}]
    raw_data jsonb,
    created_at timestamptz DEFAULT now(),
    UNIQUE(account_email, event_id, contact_id)
)
```

### Call logs table (Pipeline X)

```sql
contact_call_logs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id integer REFERENCES contacts(id),
    phone_number text NOT NULL,
    call_date timestamptz NOT NULL,
    duration_seconds integer,
    call_type text,                        -- incoming, outgoing, missed
    raw_data jsonb,
    created_at timestamptz DEFAULT now()
)
```

### Invalid emails blocklist (Pipeline S)

```sql
invalid_emails (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email text NOT NULL UNIQUE,
    reason text,                           -- bounced, invalid, catch-all-reject, etc.
    created_at timestamptz DEFAULT now()
)
```

### Camelback tables (Pipeline D)

| Table | Purpose |
|-------|---------|
| `camelback_experts` | Cohort records + enriched profile data |
| `camelback_expert_posts` | LinkedIn posts (unique on `linkedin_url, post_url`) |
| `camelback_expert_search_profiles` | AI profiles + embeddings (unique on `expert_id`) |

### Influencer tables (Pipeline Z)

```sql
influencer_posts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    influencer_url TEXT NOT NULL,                -- normalized LinkedIn URL
    influencer_name TEXT,                        -- scraped display name
    post_url TEXT NOT NULL,
    post_content TEXT,
    post_date TIMESTAMPTZ,
    engagement_likes INT DEFAULT 0,
    engagement_comments INT DEFAULT 0,
    engagement_shares INT DEFAULT 0,
    engagement_total INT GENERATED ALWAYS AS (engagement_likes + engagement_comments + engagement_shares) STORED,
    media_type TEXT,                             -- text, image, video, article, carousel
    raw_data JSONB,
    scraped_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(influencer_url, post_url)
)

influencer_post_reactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    influencer_url TEXT NOT NULL,
    post_url TEXT NOT NULL,
    post_date TIMESTAMPTZ,
    reactor_name TEXT NOT NULL,
    reactor_headline TEXT,
    reactor_linkedin_urn TEXT NOT NULL,
    reaction_type TEXT DEFAULT 'LIKE',
    contact_id INT REFERENCES contacts(id),
    match_method TEXT,
    match_confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(post_url, reactor_linkedin_urn)
)
```

Indexes: `influencer_url` on both tables, `contact_id WHERE contact_id IS NOT NULL` on reactions.

---

## 14. Environment Variables

### Required for all pipelines

```bash
SUPABASE_URL                # Database connection
SUPABASE_SERVICE_KEY        # Service role key (bypasses RLS)
APIFY_API_KEY               # Apify profile + post scraper
```

### Required for Pipeline A discovery cascade

```bash
TAVILY_API_KEY              # Tier 0.5: Tavily web search
FIRECRAWL_API_KEY           # Tier 1: Firecrawl agent
OPENAI_API_KEY              # Tier 2: o4-mini deep research
```

### Required for intelligence pipelines (H-Y)

```bash
OPENAI_APIKEY               # GPT-5 mini + embeddings (note: no underscore before KEY)
SUPABASE_DB_PASSWORD        # Direct psycopg2 connection for bulk scripts
ZEROBOUNCE_API_KEY          # Pipeline S: Email verification
PERPLEXITY_APIKEY           # Pipeline T: Web research (sonar-pro)
```

### Optional

```bash
TOMBA_API_KEY               # Tomba email finder
TOMBA_SECRET_KEY            # Tomba secret key
ENRICH_LAYER_API_KEY        # Legacy Enrich Layer (superseded)
FEC_API_KEY                 # Pipeline L: OpenFEC donations
PROXY_HOST                  # SmartProxy for ZeroBounce when Cloudflare blocks
PROXY_PORT                  # SmartProxy port
PROXY_USER                  # SmartProxy auth
PROXY_PASS                  # SmartProxy auth
```

### Feature flags

```bash
CONTACT_ENRICHMENT_O4_MINI_ENABLED=true        # Enable o4-mini Tier 2 (default: true)
CONTACT_ENRICHMENT_ALLOW_TOMBA_FALLBACK=false   # Allow Tomba when cascade fails (default: false)
TOMBA_VERIFY_ALL=false                          # Verify all Tomba emails (default: false)
```

---

## 15. Cost Reference

### Per-unit costs

| Service | Action | Cost |
|---------|--------|------|
| Apify | Profile scrape | $0.004 |
| Apify | Post scrape | $0.002/post |
| Apify | Post reactions (apimaestro) | ~$0.003/post |
| Tavily | Web search | $0.001 |
| Firecrawl | Agent search | $0.22 |
| OpenAI o4-mini | Deep research | $0.36 |
| Tomba | Email finder | $0.012 |
| GPT-5-mini | AI profile/tag/score | $0.002 |
| text-embedding-3-small | Embedding | $0.00002 |
| ZeroBounce | Email verification | $0.008/credit |
| Perplexity sonar-pro | Web research | $0.003 |
| Enrich Layer (legacy) | Profile | $0.024 |

### Production run costs

| Run | Contacts | Cost | Duration |
|-----|----------|------|----------|
| Camelback cohort (Pipeline D) | 73 | ~$7.74 | ~15 min |
| Contacts full run (Pipeline E) | 2,400 | ~$9.40 | ~4 min |
| Contacts retry #1 (URL normalization) | 110 | ~$0.08 | ~2 min |
| Contacts retry #2 (URL fixes) | 89 | ~$0.02 | ~2 min |
| **Total contacts enrichment** | **2,400** | **~$9.50** | **~8 min** |
| LinkedIn CSV import (Pipeline F) | 2,764 CSV → 527 new | free | ~10 sec |
| New contacts enrichment (Pipeline E) | 611 | ~$2.25 | ~5 min |
| Contact post scraping (Pipeline G) | 2,856 | ~$62.28 | ~18 min |
| Post reactions scraping (Pipeline R) | 57 posts → 8,699 reactions | ~$11.50 | ~25 min |
| Email finder run 1+2 (Pipeline S) | 358 emails found | ~$36 ZB credits | ~30 min |
| Web research (Pipeline T) | 30 contacts enriched | ~$0.11 | ~5 min |
| AI tagging (Pipeline H) | 2,402 contacts | ~$5 | ~8 min |
| Ask-readiness scoring (Pipeline N) | 2,921 contacts | ~$6.80 (2 runs) | ~10 min |
| Comms closeness scoring (Pipeline V) | ~1,200 contacts | ~$3 | ~5 min |
| Influencer analysis — Kevin Brown (Pipeline Z) | 100 posts, 23,456 reactions | ~$0.80 | ~20 min |

---

## 16. Key Files

### Pipeline E (Bulk Contacts) + Pipeline G (Bulk Posts)

| File | Purpose |
|------|---------|
| `scripts/enrichment/enrich_contacts_apify.py` | Bulk contacts profile enrichment with concurrent batching, URL normalization |
| `scripts/enrichment/scrape_contact_posts.py` | Bulk contact post scraping with concurrent batching |

### Pipeline F (LinkedIn CSV Import)

| File | Purpose |
|------|---------|
| `scripts/import_linkedin_csv.py` | Import LinkedIn Connections.csv, deduplicate, detect URL changes |

### Pipeline D (Batch Cohort)

| File | Purpose |
|------|---------|
| `scripts/enrichment/enrich_camelback_experts.py` | Camelback profile + post enrichment |
| `scripts/enrichment/generate_coach_profiles.py` | AI coaching profiles + embeddings |

### Pipeline A Services

| File | Purpose |
|------|---------|
| `services/contact_enrichment/contact_enrichment_service.py` | Main orchestrator (~2400 lines) |
| `services/contact_enrichment/apify_enrichment.py` | Apify profile scraper wrapper |
| `services/contact_enrichment/apify_post_scraper.py` | Apify post scraper + DB storage |
| `services/contact_enrichment/tavily_enrichment.py` | Tier 0.5: Tavily search |
| `services/contact_enrichment/firecrawl_enrichment.py` | Tier 1: Firecrawl agent |
| `services/contact_enrichment/tomba_enrichment.py` | Tomba email discovery |
| `services/contact_enrichment/enrich_layer_service.py` | Legacy Enrich Layer (superseded) |
| `services/contact_enrichment/schemas.py` | Pydantic models |
| `services/funder_leadership_service.py` | Tier 1.5: IRS 990 data |

### Other

| File | Purpose |
|------|---------|
| `services/network_mapping/network_import_service.py` | Pipeline C: network import |
| `services/outreach_context_builder.py` | Uses LinkedIn posts for outreach |
| `scripts/enrichment/enrich_linkedin_profiles.py` | Legacy Enrich Layer script (superseded) |

---

## 17. Production Run Log: Feb 2026

### Context

Full re-enrichment of the contacts database, replacing stale Enrich Layer data (single-day bulk import from Oct 2025) with fresh Apify data in structured JSONB format.

### Pre-enrichment state

- 2,502 contacts total
- 2,491 with LinkedIn URLs, 11 without
- All `enrich_*` structured columns empty (0% populated)
- Skills: 0%, profile pictures: 13%, employment history: flat text only
- Previous enrichment: Enrich Layer ($0.024/profile), all on a single date

### What we did

1. **LinkedIn URL discovery** — Found 5 missing URLs via web search, identified "Phil Solomon" as Phillip Atiba Solomon (f.k.a. Goff), deleted 3 duplicate records
2. **Database migration** — Added 11 new JSONB columns to contacts table
3. **Built Pipeline E script** — `enrich_contacts_apify.py` with concurrent batching
4. **Python environment** — Created `.venv` with arm64 architecture to fix pydantic_core mismatch
5. **Production run** — 2,400 contacts enriched in ~4 minutes, ~$9.40
6. **Failure analysis** — Researched 114 failures, categorized by root cause
7. **URL normalization fix** — Added `unquote()` + `www.` prefix normalization, recovered 19 more profiles
8. **URL corrections** — Updated 7 changed URLs, cleared 2 bad slugs, deleted 4 more duplicates
9. **Final retry** — Recovered 4 more profiles from URL fixes

### Post-enrichment state

| Metric | Before | After |
|--------|--------|-------|
| Total contacts | 2,502 | 2,498 (4 dupes deleted) |
| Apify enriched | 0 | 2,400 (96.1%) |
| Employment history (structured) | 0% | 94.6% |
| Education (structured) | 0% | 93.3% |
| Skills (detailed) | 0% | 89.0% |
| Certifications | 0% | 33.6% |
| Volunteering | 0% | 47.6% |
| Profile photos | 13% | 75.4% |
| Remaining unenrichable | — | 85 (private/restricted profiles) |

### Contact post scraping (Pipeline G): Feb 20, 2026

| Metric | Value |
|--------|-------|
| Contacts processed | 2,856 |
| Contacts with posts | 2,506 (87.8%) |
| Contacts no posts | 350 (12.2%) |
| Posts found (by Apify) | 31,138 |
| Posts stored (within 6-month window) | 12,671 |
| Posts skipped (older than 6 months) | 18,594 |
| Posts skipped (empty content) | 122 |
| Apify errors | 0 |
| DB errors | 0 |
| Cost | ~$62.28 |
| Duration | ~18 min |
| Avg cost per contact | ~$0.022 |
| Avg posts found per contact | 10.9 |

**Data quality (post-run validation):**

| Check | Result |
|-------|--------|
| Null content/URL/date/raw_data | 0 across all fields |
| Orphaned posts (no matching contact) | 0 |
| Contacts over maxPosts=15 limit | 0 |
| Post date range | Aug 2025 – Feb 2026 (correct 6-month window) |
| Avg content length | 659 chars |
| Avg engagement | 53 likes, 5.5 comments, 2.4 shares |
| Raw data stored | 100% (avg ~3 KB/post) |

**Post distribution by count:**

| Posts per contact | Contacts |
|-------------------|----------|
| 1–5 | 802 |
| 6–10 | 282 |
| 11–15 | 592 |

### Lessons learned

1. **Always normalize URLs** — `unquote()` + `www.` prefix is essential. Without it, ~10% of profiles fail silently.
2. **Batch Apify calls** — Sending 25 URLs per actor run with 8 concurrent threads reduced runtime from ~3 hours to ~4 minutes.
3. **Supabase pagination** — Default PostgREST limit is 1000 rows. Must paginate with `.range()` for larger datasets.
4. **LinkedIn URL slug changes** — People change their custom URLs. ~3% of stored URLs were stale. Web search finds current URLs.
5. **Duplicate detection** — Check for duplicate LinkedIn URLs before enrichment. We found 7 duplicate pairs across 2,500 contacts.
6. **Private profiles are permanent failures** — ~3.4% of profiles are private/restricted. No fix without authenticated LinkedIn API.
7. **Apify field names vary** — `volunteering` vs `volunteerExperience`, `honorsAndAwards` vs `honors`. Handle both.
8. **arm64 vs x86_64 Python** — On macOS with universal Python binary, create venv with `arch -arm64 python3 -m venv .venv` to avoid pydantic_core architecture mismatch.
9. **Apify post response uses nested author object** — Post items have `author.publicIdentifier` (not top-level `authorUrl`). Always inspect raw API output with `--test` before running at scale.
10. **Always test with small batches first** — Run `--test` (1 contact) then `--batch 25` before a full run. Wasted runs cost real money ($62/run at scale).
11. **Apify charges for all scraped posts** — `maxPosts` limits scraping, but the 6-month filter is local. Apify charged for all 31K posts scraped even though only 12.6K were stored. Consider reducing `maxPosts` to save cost.
12. **DB retry logic prevents "Server disconnected" errors** — Concurrent Supabase writes can fail with connection resets. 3-attempt retry with backoff (0.5s × attempt) eliminates these.
13. **Skip-trace requires location** — Never run skip-trace with just a name (no city/state). Common names like "Shane Douglas" or "Tom Watson" will match the wrong person. Always use `location_name` from LinkedIn to backfill city/state before skip-trace. If no US location can be determined, skip the contact entirely.
14. **Non-US contacts have no FEC data** — FEC is US-only. The enrichment script skips non-US contacts and marks them with `skipped_reason: "non_us_contact"`. Common names (e.g., "Dan Walker") will aggregate thousands of false donations if country isn't checked.
15. **Building-level Zillow records** — Zillow scraper can return entire building data (155K sqft, $30M) instead of individual units for condo/apartment contacts. Flag records with `sqft > 10,000` as `building_level_data: true` and suppress the inflated Zestimate.

---

## 18. Network Intelligence Pipelines (Feb 2026)

The Network Intelligence system extends LinkedIn enrichment with AI tagging, vector embeddings, deduplication, real estate, FEC donations, communication history, and ask-readiness scoring. All scripts live in `scripts/intelligence/`.

### Primary Contact (Anchor) Profile

Multiple scripts embed Justin Steele's career timeline and profile for overlap analysis, proximity scoring, and ask-readiness context. **These dates must be sourced from his actual LinkedIn profile and resume** — not estimated or inferred.

**Source of truth:** `docs/Justin/` folder contains:
- `Justin Steele - Resume.pdf` — canonical resume with dates
- `LinkedIn Resume.pdf` — full LinkedIn profile export with exact month/year dates
- `LinkedIn Bio.pdf` — LinkedIn About section

**Scripts that embed the anchor profile (must be kept in sync):**
- `tag_contacts_gpt5m.py` — `ANCHOR_PROFILE` constant (durations + dates)
- `score_overlap.py` — `JUSTIN_TIMELINE` constant (exact dates for temporal overlap analysis)

**Correct timeline (from LinkedIn, verified Feb 2026):**

| Role | Organization | Dates |
|------|-------------|-------|
| BS Chemical Engineering | University of Virginia | 2000-2004 |
| Associate Consultant | Bain & Company | Jul 2004 - Aug 2006 |
| Senior Associate Consultant | The Bridgespan Group | Aug 2006 - Jul 2007 |
| MBA / MPA | Harvard Business School / Harvard Kennedy School | 2007-2010 |
| Intern → Dir Strategy → PM → Deputy Director | Year Up | May 2009 - Aug 2014 |
| Adjunct Business Professor | Northern Virginia Community College | Jul 2011 - Jul 2014 |
| Racial Justice Lead → Director Americas | Google / Google.org | Aug 2014 - Nov 2024 |
| Co-Founder & CTO | Outdoorithm | Feb 2023 - present |
| Co-Founder & Treasurer | Outdoorithm Collective | Jan 2024 - present |
| Founder & Fractional CIO | True Steele LLC | Dec 2024 - present |
| Co-Founder & CEO | Kindora | Apr 2025 - present |
| Program Chair, Board of Trustees | San Francisco Foundation | Sep 2020 - present |
| Treasurer, Board of Directors | Outdoorithm Collective | Aug 2024 - present |

**IMPORTANT:** If these dates are ever updated, all scripts listed above must be updated simultaneously. The `score_overlap.py` timeline is especially critical since it determines temporal overlap judgments for ~1,400 contacts.

### Pipeline H: AI Tagging (GPT-5 mini)

**Script:** `scripts/intelligence/tag_contacts_gpt5m.py`
**Model:** GPT-5 mini (structured output)
**Cost:** ~$5 for 2,400 contacts

Generates structured `ai_tags` JSONB for each contact:
- `proximity` — shared employers/schools/boards with Justin, overlap years
- `affinity` — topics, primary interests, talking points
- `outreach` — personalization hooks, suggested opener, best approach
- `capacity` — score (0-100), tier (major_donor/mid_level/grassroots/unknown)
- `outdoorithm_fit` — high/medium/low/none

Uses LinkedIn enrichment data + FEC donations + real estate as input.

### Pipeline I: Vector Embeddings

**Script:** `scripts/intelligence/generate_embeddings.py`
**Model:** text-embedding-3-small (768 dimensions)

Generates two embeddings per contact stored in pgvector columns:
- `profile_embedding` — career, skills, education summary
- `interests_embedding` — topics, interests, talking points

Used for semantic search in the AI Filter Co-pilot.

### Pipeline J: Deduplication

**Script:** `scripts/intelligence/deduplicate_contacts.py`

Identifies duplicate contacts via:
1. Exact LinkedIn URL match
2. Fuzzy name + company match
3. Vector similarity (cosine > 0.95)

Merged 96 duplicates → 2,402 unique contacts.

### Pipeline K: Real Estate Enrichment

**Script:** `scripts/intelligence/enrich_real_estate.py`
**Rescrape:** `scripts/intelligence/rescrape_zillow.py`

Three-step pipeline:
1. **Skip-trace** — Apify `one-api/skip-trace` ($0.007/contact) or 411.com (free) — name + city/state → address
2. **Zillow autocomplete** — free API → address → ZPID
3. **Zillow detail scraper** — Apify `maxcopell/zillow-detail-scraper` (~$0.003) → Zestimate + property data

GPT-5 mini validates each match. Results stored in `real_estate_data` JSONB:
```json
{
  "address": "123 Main St, City, ST 12345",
  "zestimate": 1500000,
  "rent_zestimate": 5000,
  "beds": 4, "baths": 3, "sqft": 2500,
  "year_built": 1990,
  "property_type": "SINGLE_FAMILY",
  "ownership_likelihood": "likely_owner",
  "confidence": "high",
  "source": "zillow_rescrape"
}
```

**ownership_likelihood values:** `likely_owner`, `likely_owner_condo`, `likely_renter`, `uncertain`

**Key safeguards (learned from production):**
- `backfill_location()` uses GPT-5 mini to extract city/state from LinkedIn `location_name` before skip-trace
- Contacts with no US location are skipped entirely (prevents wrong-person matches for common names)
- Building records (sqft > 10K) flagged as `building_level_data: true` with Zestimate suppressed

### Pipeline L: FEC Political Donations

**Script:** `scripts/intelligence/enrich_fec_donations.py`
**API:** OpenFEC API (free, key required)

Queries FEC for political donation history. Results stored in `fec_donations` JSONB:
- `total_amount`, `donation_count`, `max_single`
- `cycles[]` — election cycles with amounts
- `recent_donations[]` — last 10 donations with details
- `employer_from_fec`, `occupation_from_fec`

**Key safeguard:** Non-US contacts are skipped (`country` not in US values). Common names like "Dan Walker" would otherwise aggregate thousands of false donations from different people. Skipped contacts get `skipped_reason: "non_us_contact"`.

### Pipeline M: Communication History

**Script:** `scripts/intelligence/gather_comms_history.py`
**Email discovery:** `scripts/intelligence/discover_emails.py`

Searches 5 Gmail accounts (via Google Workspace MCP) for email threads with each contact. Combined with LinkedIn DM data (Pipeline P). Results stored in:
- `contact_email_threads` table — raw thread data (9,425 email threads for 628 contacts + 791 LinkedIn conversations for 752 contacts)
- `contacts.communication_history` JSONB — summarized per-contact
- `contacts.comms_last_date` / `comms_thread_count` — aggregated across email + LinkedIn

### Pipeline P: LinkedIn Message Import

**Script:** `scripts/import_linkedin_messages.py`
**Source:** LinkedIn data export → `docs/LinkedIn/messages.csv`
**Cost:** Free

Imports LinkedIn DM conversations from LinkedIn's data export CSV, groups by conversation ID, matches participants to contacts via LinkedIn profile URL, and stores in `contact_email_threads` with `account_email='linkedin'`.

```
LinkedIn messages.csv
  │
  ├── Parse CSV (skip sponsored/empty/HTML messages)
  │
  ├── Group by CONVERSATION ID → threads
  │
  ├── For each conversation:
  │   ├── Identify non-Justin participant(s) by LinkedIn URL
  │   ├── Match to contacts table via normalized linkedin_url
  │   ├── Determine direction (outbound/inbound/bidirectional)
  │   └── Build raw_messages array with from/to/date/body
  │
  └── Insert into contact_email_threads (batches of 50)
```

**CLI usage:**

```bash
python scripts/import_linkedin_messages.py --test          # Preview 5 conversations
python scripts/import_linkedin_messages.py                 # Full import
python scripts/import_linkedin_messages.py --clear-first   # Clear existing linkedin rows first
```

**Production run: Feb 22, 2026**

| Metric | Value |
|--------|-------|
| CSV messages | 2,864 |
| Conversations parsed | 1,004 |
| Matched to contacts | 791 (79%) |
| Unmatched (not in DB) | 213 |
| Bidirectional | 431 |
| Outbound only | 41 |
| Inbound only | 319 |
| Errors | 0 |

**Impact on comms data:**
- 560 contacts gained communication history for the first time (had LinkedIn DMs but no email)
- 613 contacts had their most recent contact date extended (LinkedIn DM more recent than last email)
- After import, `comms_last_date` and `comms_thread_count` on contacts must be recalculated to include LinkedIn threads

### Pipeline Q: LinkedIn Article Reactions

**Script:** `scripts/intelligence/import_article_reactions.py`
**Source:** `docs/LinkedIn/LinkedIn Article Reactions.md` (copy-pasted from LinkedIn)
**Cost:** ~$0.50 (GPT-5 mini for fuzzy name matching)

Imports reactions to Justin's LinkedIn articles, matches reactors to contacts via 3-pass matching (exact → fuzzy → GPT), and stores engagement summaries on each contact.

```
LinkedIn Article Reactions.md
  │
  ├── Parse markdown → extract article titles, reaction types, reactor names/headlines
  │
  ├── Insert into linkedin_article_reactions table (2,293 reactions across 9 articles)
  │
  ├── 3-pass contact matching:
  │   ├── Pass 1: Exact name match (normalized, case-insensitive)
  │   ├── Pass 2: Fuzzy match (difflib SequenceMatcher, threshold 0.85)
  │   └── Pass 3: GPT-5 mini adjudication (candidates from first name + fuzzy)
  │
  └── Build linkedin_reactions JSONB summary per contact
```

**CLI usage:**

```bash
python scripts/intelligence/import_article_reactions.py --test          # Parse only, no DB
python scripts/intelligence/import_article_reactions.py                 # Full import + match
python scripts/intelligence/import_article_reactions.py --match-only    # Re-run matching only
```

**Production run: Feb 22, 2026**

| Metric | Value |
|--------|-------|
| Reactions parsed | 2,293 |
| Articles | 9 |
| Exact match | 1,023 (44.6%) |
| Fuzzy match | 78 (3.4%) |
| GPT match | 26 (1.1%) |
| Unmatched | 1,166 (50.8%) |
| Total matched to contacts | 1,128 (49.1%) |
| 1st-degree match rate | 99.6% (1,097 of 1,101) |
| Unique contacts linked | 693 |
| Cost | $0.46 |

**Unmatched reactions are expected:** ~50% of reactors are 2nd/3rd-degree connections not in Justin's contacts DB. The 99.6% match rate for 1st-degree connections is the meaningful metric.

**Reaction type distribution:** like (1,363), insightful (394), love (336), celebrate (143), support (57)

**Downstream usage:** `linkedin_reactions` JSONB is consumed by ask-readiness scoring (Pipeline N) as an engagement signal. Contacts who react to 3+ articles are considered warm even without other comms data. Reaction types indicate emotional intensity ('love'/'insightful' > 'like').

### Pipeline R: LinkedIn Post Reactions

**Script:** `scripts/intelligence/scrape_post_reactions.py`
**Source:** `docs/LinkedIn/Justin Posts/Shares.csv` (LinkedIn's official post export)
**Apify actor:** `apimaestro/linkedin-post-reactions`
**Cost:** ~$10 for 57 posts + ~$1.50 GPT matching (8,700 reactions)

Scrapes who reacted to each of Justin's LinkedIn posts using Apify, matches reactors to contacts via 3-pass matching (same as Pipeline Q), and stores ALL reactions — including unmatched reactors — for future identification as the contacts DB grows.

```
LinkedIn Shares.csv
  │
  ├── Parse CSV → extract post URLs + dates (filter by --since cutoff)
  │
  ├── Apify scraping (batches of 15 posts per actor run):
  │   ├── apimaestro/linkedin-post-reactions with limit=100
  │   ├── Pagination for posts with >100 reactions (page_number increment)
  │   └── Raw reactor data: name, headline, URN, profile_url, reaction_type
  │
  ├── 3-pass contact matching:
  │   ├── Pass 1: Exact name match (normalized, case-insensitive)
  │   ├── Pass 2: Fuzzy match (difflib SequenceMatcher, threshold 0.85)
  │   └── Pass 3: GPT-5 mini adjudication (50 concurrent workers)
  │
  ├── Deduplicate by (post_url, reactor_linkedin_urn) before save
  │
  └── Upsert into post_reactions table (batches of 200)
```

**CLI usage:**

```bash
python scripts/intelligence/scrape_post_reactions.py                    # All posts since Nov 2024
python scripts/intelligence/scrape_post_reactions.py --limit 5          # Test with 5 posts
python scripts/intelligence/scrape_post_reactions.py --since 2025-06-01 # Custom date cutoff
python scripts/intelligence/scrape_post_reactions.py --dry-run           # Show what would be scraped
python scripts/intelligence/scrape_post_reactions.py --match-only        # Re-run matching on existing DB data
python scripts/intelligence/scrape_post_reactions.py --json-output f.json # Save raw reactions to JSON
python scripts/intelligence/scrape_post_reactions.py --workers 50        # GPT workers (default 50)
```

**Apify actor details (`apimaestro/linkedin-post-reactions`):**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `post_urls` | string[] | required | LinkedIn post URLs (**snake_case**, NOT camelCase) |
| `limit` | int | 100 | Max reactions per post per page |
| `page_number` | int | 1 | Page for pagination (1-indexed) |
| `reaction_type` | string | "ALL" | Filter: ALL, LIKE, EMPATHY, INTEREST, PRAISE, APPRECIATION, ENTERTAINMENT |

**Reactor data structure** (per reaction item):

```json
{
  "reactor": {
    "name": "Jane Doe",
    "headline": "VP of Impact at Foundation X",
    "urn": "urn:li:fsd_profile:ACoAAA...",
    "profile_url": "https://www.linkedin.com/in/ACoAAA..."
  },
  "reaction_type": "LIKE",
  "input": "https://www.linkedin.com/feed/update/urn:li:ugcPost:...",
  "total_reactions": 728
}
```

**Key technical notes:**
- Reactor `profile_url` uses URN format (`/in/ACoAAA...`), NOT vanity URLs — cannot match by URL, must match by name + headline
- Pagination is necessary for viral posts: `total_reactions` in response indicates when more pages exist (total > limit)
- Duplicate reactions appear across pagination boundaries — deduplicate by `(post_url, reactor_linkedin_urn)` before upsert
- The `--match-only` flag re-runs the 3-pass matcher against existing DB data (useful after adding new contacts)

**Production run: Feb 25, 2026**

| Metric | Value |
|--------|-------|
| Posts scraped | 57 (since Nov 2024) |
| Total reactions scraped | 8,733 |
| After deduplication | 8,699 |
| Exact match | 4,519 (51.7%) |
| Fuzzy match | 683 (7.8%) |
| GPT match | 197 (2.3%) |
| Total matched to contacts | 5,399 (61.8%) |
| Unmatched (stored for future) | 3,334 |
| Unique contacts engaged | 1,308 |
| Unique unmatched reactors | 2,274 |
| Cost (Apify) | ~$10 |
| Cost (GPT matching) | ~$1.50 |

**Reaction type distribution:** LIKE (5,106), EMPATHY (1,505), PRAISE (1,367), INTEREST (518), APPRECIATION (232), ENTERTAINMENT (2)

**Top posts by reactions:**

| Reactions | Date | Post |
|-----------|------|------|
| 1,069 | 2024-11-20 | Leaving Google announcement |
| 844 | 2024-12-04 | Baldwin quote |
| 728 | 2025-08-18 | New position at Kindora |
| 498 | 2024-12-18 | Founder announcement |
| 497 | 2025-08-15 | Sweet Fingers / $100M post |
| 453 | 2025-01-11 | Meta ends DEI programs |
| 444 | 2025-06-30 | Harvard and UVA diplomas |
| 433 | 2025-07-10 | Drove straight to trailhead |

**vs Pipeline Q (Article Reactions):**

| Dimension | Pipeline Q (Articles) | Pipeline R (Posts) |
|-----------|----------------------|-------------------|
| Source | Manual markdown copy-paste | Automated Apify scrape |
| Content type | Long-form articles | Short-form posts |
| Reactor identifier | Name + headline only | Name + headline + LinkedIn URN |
| Match rate | 49.1% | 61.8% |
| Unmatched stored? | Yes (in DB, no URN) | Yes (with URN for future matching) |
| Reaction types | like, insightful, love, support, celebrate | LIKE, EMPATHY, PRAISE, INTEREST, APPRECIATION, ENTERTAINMENT |
| Re-run matching | `--match-only` | `--match-only` |

**Downstream usage:** Post reaction data is valuable for:
- Identifying warm contacts who consistently engage (top reactors reacted to 25-39 posts)
- Discovering potential new connections (2,274 unmatched reactors with headlines)
- Enriching ask-readiness scoring with engagement signals
- Understanding which content resonates with the network

### Pipeline N: Ask-Readiness Scoring

**Script:** `scripts/intelligence/score_ask_readiness.py`
**Model:** GPT-5 mini (structured output)
**Cost:** ~$4 for 2,900 contacts

Scores each contact's readiness for a specific fundraising goal. Uses ALL enrichment data as context:
- LinkedIn profile, employment, education
- FEC donations, real estate (with ownership/renter handling)
- Communication history, familiarity rating
- OC engagement (donor status, board membership)

Results stored in `ask_readiness` JSONB keyed by goal:
```json
{
  "outdoorithm_fundraising": {
    "score": 85,
    "tier": "ready_now",
    "reasoning": "4-6 sentence prospect summary...",
    "top_goals": [...],
    "risk_factors": [...],
    "scored_at": "2026-02-22T..."
  }
}
```

**Tiers:** `ready_now` (75+), `cultivate_first` (50-74), `long_term` (25-49), `not_a_fit` (0-24)

**Key safeguards:**
- Renters' Zestimates suppressed (it's the landlord's value)
- Institutional philanthropy roles scored on personal capacity only
- Building-level records noted as "unit-level value unknown"
- Non-US FEC data marked and excluded

### Database Schema: Intelligence Columns

```sql
-- AI Tags (Pipeline H)
ai_tags jsonb,                    -- {proximity, affinity, outreach, capacity, outdoorithm_fit}
ai_tags_generated_at timestamptz,
ai_tags_model text,               -- 'gpt-5-mini'

-- Computed from ai_tags
ai_proximity_score integer,       -- 0-100
ai_proximity_tier text,           -- 'close', 'warm', 'distant'
ai_capacity_score integer,        -- 0-100
ai_capacity_tier text,            -- 'major_donor', 'mid_level', 'grassroots', 'unknown'
ai_outdoorithm_fit text,          -- 'high', 'medium', 'low', 'none'
ai_kindora_prospect_score integer,
ai_kindora_prospect_type text,

-- Vector Embeddings (Pipeline I, pgvector 768d)
profile_embedding vector(768),
interests_embedding vector(768),

-- Real Estate (Pipeline K)
real_estate_data jsonb,           -- {address, zestimate, ownership_likelihood, ...}

-- FEC Donations (Pipeline L)
fec_donations jsonb,              -- {total_amount, donation_count, cycles[], ...}

-- Communication History (Pipeline M)
communication_history jsonb,      -- {thread_count, last_contact, accounts[], ...}

-- Ask-Readiness (Pipeline N)
ask_readiness jsonb,              -- {goal_name: {score, tier, reasoning, ...}}

-- LinkedIn Article Reactions (Pipeline Q)
linkedin_reactions jsonb,         -- {total_reactions, reaction_types, articles_reacted_to[], article_count}

-- Communication Summary (Pipeline U)
comms_summary jsonb,              -- {channels, total_threads, last_contact, chronological_summary, ...}

-- Comms Closeness (Pipeline V)
comms_closeness text,             -- 'inner_circle', 'active', 'occasional', 'dormant', 'no_comms'
comms_momentum text,              -- 'accelerating', 'steady', 'decelerating', 'stale', 'new'
comms_reasoning text,             -- 1-2 sentence explanation

-- Call Data (Pipeline X)
comms_call_count integer,         -- total matched calls
comms_last_call timestamptz,      -- most recent call

-- Overlap Scoring (Pipeline Y)
overlap_data jsonb,               -- {institutions[], overlap_score, ...}

-- Familiarity (manual + AI)
familiarity_rating integer,       -- 0-4
familiarity_rated_at timestamptz,

-- OC Engagement (CRM sync)
oc_engagement jsonb,              -- {is_oc_donor, known_donor, crm_roles[], total_donated, ...}

-- Location (from LinkedIn)
location_name text,               -- Raw LinkedIn location string
```

### Pipeline S: Email Finder (ZeroBounce)

**Script:** `scripts/intelligence/find_emails.py`
**Cost:** ~$0.05/contact (~6.3 ZeroBounce credits/contact)
**Results:** 358 new emails found across 2 runs, coverage 73% to 84.8% (2,494/2,940)

Pipeline: company name to domain discovery (hardcoded map + DNS MX lookup) to email permutations (first.last, flast, etc.) to ZeroBounce verification to GPT-5 mini validation to save.

**CLI usage:**

```bash
python scripts/intelligence/find_emails.py --dry-run -n 5         # Dry-run 5 contacts
python scripts/intelligence/find_emails.py -n 50                  # Run on 50 contacts
python scripts/intelligence/find_emails.py --ids 123,456          # Specific contacts
python scripts/intelligence/find_emails.py --proxy                # Route through SmartProxy
python scripts/intelligence/find_emails.py --skip-tomba           # Skip Tomba fallback
python scripts/intelligence/find_emails.py --offset 100 -n 50    # Paginated batch
```

**Key details:**
- **ZeroBounce API:** `api.zerobounce.net/v2/validate`, key in `ZEROBOUNCE_API_KEY`
- **Credit conservation:** DNS MX pre-filter, early-stop on valid, catch-all 3-perm cap, non-catch-all 5-perm cap, bad domain detection
- **Invalid emails blocklist:** `invalid_emails` table (2,092 entries) prevents re-assigning bounced emails
- **Proxy support:** `--proxy` flag routes through SmartProxy (env vars `PROXY_*`) when Cloudflare blocks IP
- **Cloudflare 1015 fix:** Detects HTTP 401/402/403 + Cloudflare error 1015, returns None immediately (no retry storm)

### Pipeline T: Web Research Enrichment (Perplexity)

**Script:** `scripts/intelligence/enrich_web_research.py`
**Model:** Perplexity sonar-pro + GPT-5 mini structuring
**Cost:** ~$0.004/contact

For contacts without LinkedIn profiles (Quinn Delaney, Bryan Stevenson, James Cash, etc.). Perplexity searches the web, GPT-5 mini structures the results, and they get saved to the same enrichment columns as LinkedIn data.

**CLI usage:**

```bash
python enrich_web_research.py --discover --dry-run       # Preview what would be researched
python enrich_web_research.py --ids 1933                 # Research specific contact
python enrich_web_research.py --discover                 # Auto-find empty/thin profiles
python enrich_web_research.py --discover --re-score      # Research + re-run AI scoring
python enrich_web_research.py --discover --force          # Re-research already researched
```

**Key details:**
- **Discovery mode:** auto-finds contacts with no LinkedIn and thin profiles
- **Confidence gating:** high/medium = save, low = skip (raw research saved for manual review)
- **First run:** 39 discovered, 30 enriched, 9 skipped (low confidence)
- **Perplexity rate limit:** ~50 RPM, script uses 1.5s sequential delay

### Pipeline U: Communication Summary Aggregator

**Script:** `scripts/intelligence/rebuild_comms_summary.py`
**Cost:** Free (no API calls)

Aggregates data from `contact_email_threads`, `contact_calendar_events`, `contact_call_logs`, and `contact_sms_conversations` into a single `comms_summary` JSONB on each contact. Produces per-channel breakdowns, a chronological summary, and unified last-contact dates.

**CLI usage:**

```bash
python scripts/intelligence/rebuild_comms_summary.py --test          # Preview 5 contacts
python scripts/intelligence/rebuild_comms_summary.py --contact-id 42 # Single contact
python scripts/intelligence/rebuild_comms_summary.py --ids 1,2,3     # Specific contacts
python scripts/intelligence/rebuild_comms_summary.py                 # Full run
```

**Results:** 1,242 contacts with `comms_summary` populated across 5 channels (email, LinkedIn DM, SMS, calendar, calls).

### Pipeline V: Comms Closeness Scoring

**Script:** `scripts/intelligence/score_comms_closeness.py`
**Model:** GPT-5 mini (structured output)
**Cost:** ~$3 for full run

Uses `comms_summary` data to score each contact's communication closeness and momentum. Pure behavioral assessment (not subjective like familiarity_rating).

**CLI usage:**

```bash
python scripts/intelligence/score_comms_closeness.py --test            # 5 contacts, no write
python scripts/intelligence/score_comms_closeness.py --workers 150     # Full run
python scripts/intelligence/score_comms_closeness.py --force           # Re-score already scored
python scripts/intelligence/score_comms_closeness.py --contact-id 42   # Single contact
python scripts/intelligence/score_comms_closeness.py --ids 1,2,3       # Specific contacts
```

**Output:** `comms_closeness` (inner_circle/active/occasional/dormant/no_comms), `comms_momentum` (accelerating/steady/decelerating/stale/new), `comms_reasoning` (1-2 sentence explanation).

### Pipeline W: Calendar Meeting History

**Script:** `scripts/intelligence/gather_calendar_meetings.py`
**Source:** 5 Google Calendar accounts via Google Workspace MCP
**Cost:** Free (API calls only)

Event-centric approach: pulls ALL events per calendar, then batch-matches attendee emails to contacts. Stores in `contact_calendar_events` table. 288 contacts matched in first run.

**CLI usage:**

```bash
python scripts/intelligence/gather_calendar_meetings.py --test              # 1 account, 100 events
python scripts/intelligence/gather_calendar_meetings.py --collect-only      # All accounts, no LLM summary
python scripts/intelligence/gather_calendar_meetings.py --summarize-only    # LLM summary from existing data
python scripts/intelligence/gather_calendar_meetings.py --recent-days 7     # Only last 7 days (daily sync)
python scripts/intelligence/gather_calendar_meetings.py --account EMAIL     # Single account
python scripts/intelligence/gather_calendar_meetings.py --force             # Re-collect everything
```

### Pipeline X: Phone Backup Sync (SMS + Calls)

**Script:** `scripts/intelligence/sync_phone_backup.py`
**Source:** SMS Backup & Restore XML files from `SMS_Calls_Backup` folder in Google Drive
**Cost:** Free

Downloads latest SMS and call backup XML files from Drive, processes incrementally, matches phone numbers to contacts, and stores in `contact_sms_conversations` and `contact_call_logs`. SMS files are ~5GB each; call files are ~450KB.

**CLI usage:**

```bash
python scripts/intelligence/sync_phone_backup.py                    # Full sync (SMS + calls)
python scripts/intelligence/sync_phone_backup.py --calls-only       # Calls only (fast, no 5GB download)
python scripts/intelligence/sync_phone_backup.py --sms-only         # SMS only
python scripts/intelligence/sync_phone_backup.py --test             # 1 SMS conv + 10 calls
python scripts/intelligence/sync_phone_backup.py --recent-days 7    # Override SMS cutoff
```

**Results:** 147 contacts with SMS data, 50 contacts with call data (785 calls matched).

### Pipeline Y: Overlap Scoring

**Script:** `scripts/intelligence/score_overlap.py`
**Model:** GPT-5 mini (structured output)
**Cost:** ~$4 for full run

Identifies shared institutions (employers, schools, boards) between each contact and Justin, with temporal overlap detection. Embeds `JUSTIN_TIMELINE` constant with exact month/year dates for overlap judgment.

**Output:** `overlap_data` JSONB with shared institutions, overlap periods, and relationship context.

### Daily Sync Automation

**Wrapper:** `scripts/intelligence/daily_sync.sh`
**Schedule:** launchd at 8am PT daily (`~/Library/LaunchAgents/co.truesteele.contacts-sync.plist`)

Runs three syncs sequentially:
1. **Email:** `gather_comms_history.py --recent-days 3 --collect-only`
2. **Calendar:** `gather_calendar_meetings.py --recent-days 7 --collect-only`
3. **SMS + Calls:** `sync_phone_backup.py` (downloads from Drive, processes incrementally)

Logs to `logs/daily_sync_YYYY-MM-DD.log`, auto-cleaned after 30 days.

**Verify:** `launchctl list | grep truesteele`

### Campaign Tools

Three scripts for generating outreach at scale:

| Script | Purpose |
|--------|---------|
| `scripts/intelligence/scaffold_campaign.py` | Creates campaign structure, selects contacts, generates send schedule |
| `scripts/intelligence/write_campaign_copy.py` | GPT-5 mini generates personalized email copy per contact |
| `scripts/intelligence/write_personal_outreach.py` | GPT-5 mini generates 1:1 outreach emails using full contact intelligence |

All three use `--test`, `--batch`, `--workers`, `--force`, `--contact-id` flags.

### Key Files: Intelligence Scripts

| File | Purpose |
|------|---------|
| `scripts/intelligence/tag_contacts_gpt5m.py` | Pipeline H: AI tagging with GPT-5 mini |
| `scripts/intelligence/generate_embeddings.py` | Pipeline I: Vector embeddings |
| `scripts/intelligence/deduplicate_contacts.py` | Pipeline J: Contact deduplication |
| `scripts/intelligence/enrich_real_estate.py` | Pipeline K: Real estate enrichment |
| `scripts/intelligence/rescrape_zillow.py` | Pipeline K: Zillow rescrape for existing addresses |
| `scripts/intelligence/people_search_scraper.py` | Pipeline K: 411.com people search scraper |
| `scripts/intelligence/enrich_fec_donations.py` | Pipeline L: FEC political donations |
| `scripts/intelligence/gather_comms_history.py` | Pipeline M: Gmail communication history |
| `scripts/intelligence/discover_emails.py` | Pipeline M: Email address discovery (legacy) |
| `scripts/intelligence/score_ask_readiness.py` | Pipeline N: Ask-readiness scoring |
| `scripts/intelligence/gather_sms_history.py` | Pipeline O: SMS communication history |
| `scripts/import_linkedin_messages.py` | Pipeline P: LinkedIn DM message import |
| `scripts/intelligence/import_article_reactions.py` | Pipeline Q: LinkedIn article reaction import + matching |
| `scripts/intelligence/scrape_post_reactions.py` | Pipeline R: LinkedIn post reaction scraping + 3-pass matching |
| `scripts/intelligence/find_emails.py` | Pipeline S: Email finder (ZeroBounce + GPT validation) |
| `scripts/intelligence/enrich_web_research.py` | Pipeline T: Web research for non-LinkedIn contacts |
| `scripts/intelligence/rebuild_comms_summary.py` | Pipeline U: Unified comms summary aggregator |
| `scripts/intelligence/score_comms_closeness.py` | Pipeline V: Communication closeness scoring |
| `scripts/intelligence/gather_calendar_meetings.py` | Pipeline W: Calendar meeting history |
| `scripts/intelligence/sync_phone_backup.py` | Pipeline X: Phone backup sync (SMS + calls from Drive) |
| `scripts/intelligence/score_overlap.py` | Pipeline Y: Temporal overlap scoring |
| `scripts/intelligence/daily_sync.sh` | Daily sync wrapper (email + calendar + phone) |
| `scripts/intelligence/scaffold_campaign.py` | Campaign scaffolding + contact selection |
| `scripts/intelligence/write_campaign_copy.py` | Campaign email copy generation |
| `scripts/intelligence/write_personal_outreach.py` | 1:1 personal outreach generation |
| `scripts/intelligence/backfill_comms_fields.py` | Backfill comms aggregate columns |
| `scripts/intelligence/analyze_influencer.py` | Pipeline Z: Influencer post scraping + reactor matching |
| `scripts/intelligence/analyze_kevin_brown.py` | Pipeline Z: Kevin Brown content analysis (GPT-5 mini) |
| `scripts/intelligence/contact_matcher.py` | Shared: 3-pass contact matcher (exact → fuzzy → GPT) |

---

## 19. Influencer Analysis Pipeline (Z)

Analyzes any LinkedIn influencer's posts to understand what content works, who engages, and which of Justin's contacts overlap with their audience. Two scripts: a generic scraper/matcher (`analyze_influencer.py`) and a Kevin Brown-specific GPT content analysis (`analyze_kevin_brown.py`).

### Script 1: `analyze_influencer.py` — Scrape + Match

**4-phase pipeline:**

1. **Scrape posts** — Apify `harvestapi/linkedin-profile-posts` (single run, `maxPosts` configurable)
2. **Scrape reactions** — Apify `apimaestro/linkedin-post-reactions` (batched 15 posts/run, paginated for >100 reactions)
3. **Match reactors to contacts** — uses `ContactMatcher` (3-pass: exact → fuzzy → GPT-5 mini)
4. **Save + Report** — upsert to `influencer_posts` and `influencer_post_reactions`, print analysis

**CLI:**

```bash
python analyze_influencer.py https://www.linkedin.com/in/kevinlbrown/
python analyze_influencer.py kevinlbrown --months 6 --max-posts 100
python analyze_influencer.py kevinlbrown --skip-reactions    # posts only
python analyze_influencer.py kevinlbrown --report-only       # re-analyze from DB
python analyze_influencer.py kevinlbrown --workers 50        # GPT matching workers
```

**Report includes:**
- Post performance (top 10 by engagement, avg engagement, by media type, by length)
- Posting frequency
- Reactor analysis (unique reactors, top 25 most engaged, reaction type distribution)
- Contacts overlap (which of Justin's contacts engage with this influencer — warm intro targets)
- Engagement concentration (top 10% share)

### Script 2: `analyze_kevin_brown.py` — GPT Content Analysis

Runs GPT-5 mini structured output analysis on every post in the `influencer_posts` table for Kevin Brown. Five analysis steps, each runnable independently:

```bash
python analyze_kevin_brown.py --step catalog    # US-001: extract + metrics
python analyze_kevin_brown.py --step themes     # US-002: theme/message analysis
python analyze_kevin_brown.py --step rhetoric   # US-003: rhetorical device deep-dive
python analyze_kevin_brown.py --step format     # US-004: length/format/timing
python analyze_kevin_brown.py --step playbook   # US-005: synthesize signature patterns
```

**Per-post GPT analysis fields (33 total):**
- Theme: `primary_theme`, `core_message`, `content_category`, `emotional_appeal`, `target_audience`
- Rhetoric: `opening_hook`, `structural_pattern`, `rhetorical_devices[]`, `framing_technique`, `call_to_action`, `tone`
- Format: `line_break_style`, `uses_emoji`, `uses_bold_unicode`, `has_hook_gap`

**Outputs:**
- `docs/kevin_brown_posts_catalog.json` — 100 posts with all 33 analysis fields (~288 KB)
- `docs/KEVIN_BROWN_CONTENT_ANALYSIS.md` — strategic analysis + Kindora content strategy

**Cost:** ~$0.05 total (100 posts × ~$0.0005/post GPT-5 mini)

### Shared Module: `contact_matcher.py`

Extracted from `scrape_post_reactions.py` for reuse across Pipelines R and Z.

**Classes/functions:**
- `ContactMatcher` — loads all contacts, runs 3-pass matching (exact → fuzzy → GPT-5 mini batch)
- `normalize_name()`, `split_first_last()` — name normalization with suffix/emoji handling
- `NameMatchResult` — Pydantic schema for GPT structured output
- `GPT_MATCH_PROMPT` — few-shot prompt for GPT name adjudication

Both `scrape_post_reactions.py` and `analyze_influencer.py` import from this module.

### Production Run: Kevin L. Brown (Feb 2026)

| Metric | Value |
|--------|-------|
| Posts scraped | 100 (Nov 2024 – Feb 2026) |
| Total reactions | 23,456 |
| Unique reactors | 13,167 |
| Matched to contacts | 256 (warm intro targets) |
| Avg engagement per post | 463 |
| Top post engagement | 3,134 ("Communications Officer") |
| Media split | 61 text (avg 539 eng), 39 carousel (avg 345 eng) |
| Cost (Apify posts) | ~$0.20 |
| Cost (Apify reactions) | ~$0.45 |
| Cost (GPT matching) | ~$0.10 |
| Cost (GPT content analysis) | ~$0.05 |
| **Total cost** | **~$0.80** |

### Key Findings (Kevin Brown Analysis)

See `docs/KEVIN_BROWN_CONTENT_ANALYSIS.md` for the full strategic analysis. Top-level findings:

1. **Advocacy beats education** — provocative identity-driven posts (avg 684 engagement) outperform educational content (avg 345) by 2x
2. **Text > carousel** — text-only posts average 539 engagement vs 345 for carousels
3. **Long posts win** — very long posts (1500+ chars) average 625 engagement vs 306 for short (<300)
4. **Kevin's 5 signature moves:** provocative reframe, listicle manifesto, "let me tell you a story", the data flip, industry callout
5. **256 of Justin's contacts** engage with Kevin's posts — these are warm intro targets who already follow nonprofit fundraising content
