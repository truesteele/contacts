# LinkedIn Enrichment: Master Reference

**Last updated:** 2026-02-18

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
7. [LinkedIn URL Discovery Cascade](#7-linkedin-url-discovery-cascade)
8. [Apify: The Core LinkedIn Data Provider](#8-apify-the-core-linkedin-data-provider)
9. [URL Normalization](#9-url-normalization)
10. [Failure Modes and Remediation](#10-failure-modes-and-remediation)
11. [Database Schema](#11-database-schema)
12. [Environment Variables](#12-environment-variables)
13. [Cost Reference](#13-cost-reference)
14. [Key Files](#14-key-files)
15. [Production Run Log: Feb 2026](#15-production-run-log-feb-2026)

---

## 1. System Overview

Kindora uses five pipelines for LinkedIn data. All share Apify as the core scraping provider.

| Pipeline | Purpose | Trigger | Scale |
|----------|---------|---------|-------|
| **A** | Enrich a single funder contact | User clicks "Enrich" in UI | 1 contact |
| **B** | Scrape a contact's LinkedIn posts | User clicks "Scrape Posts" | 1 contact |
| **C** | Import a user's LinkedIn connection | User imports from network | 1 contact |
| **D** | Bulk-enrich a standalone cohort | CLI script (e.g., Camelback) | 10-100 contacts |
| **E** | Bulk-enrich the contacts database | CLI script with concurrency | 1,000-10,000 contacts |

**Shared infrastructure:**
- **Apify** `harvestapi/linkedin-profile-scraper` — $0.004/profile
- **Apify** `harvestapi/linkedin-profile-posts` — $0.002/post
- **Supabase** — PostgreSQL + Storage + RLS
- **URL normalization** — All pipelines should normalize URLs before sending to Apify

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

Developed for the full contacts database (2,498 contacts). Uses concurrent batch processing for speed.

**Script:** `scripts/enrichment/enrich_contacts_apify.py`

### Key differences from Pipeline D

| Feature | Pipeline D (Camelback) | Pipeline E (Contacts) |
|---------|----------------------|----------------------|
| Scale | 73 records | 2,498 records |
| Concurrency | Sequential (1 at a time) | 25 URLs/batch, 8 concurrent runs |
| URL normalization | None | Decodes percent-encoding, adds `www.` |
| Data storage | Cohort-specific table | `contacts` table (flat + JSONB columns) |
| Posts | Yes | No (profiles only) |
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

## 7. LinkedIn URL Discovery Cascade

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

## 8. Apify: The Core LinkedIn Data Provider

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
    "maxPosts": 50,
    "scrapeReactions": False,
    "scrapeComments": False,
    "includeReposts": False,
    "includeQuotePosts": True,
}
```

### Apify Billing (Starter Plan)

- $29/month with $29 prepaid usage
- $0.300 per compute unit (CU)
- Max 32 concurrent actor runs
- 32 GB actor RAM
- 30 datacenter proxies

---

## 9. URL Normalization

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

## 10. Failure Modes and Remediation

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

## 11. Database Schema

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

### Camelback tables (Pipeline D)

| Table | Purpose |
|-------|---------|
| `camelback_experts` | Cohort records + enriched profile data |
| `camelback_expert_posts` | LinkedIn posts (unique on `linkedin_url, post_url`) |
| `camelback_expert_search_profiles` | AI profiles + embeddings (unique on `expert_id`) |

---

## 12. Environment Variables

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

### Optional

```bash
TOMBA_API_KEY               # Tomba email finder
TOMBA_SECRET_KEY            # Tomba secret key
ENRICH_LAYER_API_KEY        # Legacy Enrich Layer (superseded)
OPENAI_APIKEY               # Pipeline D AI profiles (GPT-5-mini + embeddings)
```

### Feature flags

```bash
CONTACT_ENRICHMENT_O4_MINI_ENABLED=true        # Enable o4-mini Tier 2 (default: true)
CONTACT_ENRICHMENT_ALLOW_TOMBA_FALLBACK=false   # Allow Tomba when cascade fails (default: false)
TOMBA_VERIFY_ALL=false                          # Verify all Tomba emails (default: false)
```

---

## 13. Cost Reference

### Per-unit costs

| Service | Action | Cost |
|---------|--------|------|
| Apify | Profile scrape | $0.004 |
| Apify | Post scrape | $0.002/post |
| Tavily | Web search | $0.001 |
| Firecrawl | Agent search | $0.22 |
| OpenAI o4-mini | Deep research | $0.36 |
| Tomba | Email finder | $0.012 |
| GPT-5-mini | AI profile | $0.002 |
| text-embedding-3-small | Embedding | $0.00002 |
| Enrich Layer (legacy) | Profile | $0.024 |

### Production run costs

| Run | Contacts | Cost | Duration |
|-----|----------|------|----------|
| Camelback cohort (Pipeline D) | 73 | ~$7.74 | ~15 min |
| Contacts full run (Pipeline E) | 2,400 | ~$9.40 | ~4 min |
| Contacts retry #1 (URL normalization) | 110 | ~$0.08 | ~2 min |
| Contacts retry #2 (URL fixes) | 89 | ~$0.02 | ~2 min |
| **Total contacts enrichment** | **2,400** | **~$9.50** | **~8 min** |

---

## 14. Key Files

### Pipeline E (Bulk Contacts)

| File | Purpose |
|------|---------|
| `scripts/enrichment/enrich_contacts_apify.py` | Bulk contacts enrichment with concurrent batching, URL normalization |

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

## 15. Production Run Log: Feb 2026

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

### Lessons learned

1. **Always normalize URLs** — `unquote()` + `www.` prefix is essential. Without it, ~10% of profiles fail silently.
2. **Batch Apify calls** — Sending 25 URLs per actor run with 8 concurrent threads reduced runtime from ~3 hours to ~4 minutes.
3. **Supabase pagination** — Default PostgREST limit is 1000 rows. Must paginate with `.range()` for larger datasets.
4. **LinkedIn URL slug changes** — People change their custom URLs. ~3% of stored URLs were stale. Web search finds current URLs.
5. **Duplicate detection** — Check for duplicate LinkedIn URLs before enrichment. We found 7 duplicate pairs across 2,500 contacts.
6. **Private profiles are permanent failures** — ~3.4% of profiles are private/restricted. No fix without authenticated LinkedIn API.
7. **Apify field names vary** — `volunteering` vs `volunteerExperience`, `honorsAndAwards` vs `honors`. Handle both.
8. **arm64 vs x86_64 Python** — On macOS with universal Python binary, create venv with `arch -arm64 python3 -m venv .venv` to avoid pydantic_core architecture mismatch.
