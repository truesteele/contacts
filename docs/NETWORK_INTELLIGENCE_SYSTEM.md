# Personal Network Intelligence System

**Last updated:** 2026-02-18
**Status:** Phase 1-2 COMPLETE, Phase 4 COMPLETE (Copilot UI)

---

## Table of Contents

1. [Vision](#1-vision)
2. [What We Have Today](#2-what-we-have-today)
3. [The Anchor: Justin's Profile Graph](#3-the-anchor-justins-profile-graph)
4. [Architecture Overview](#4-architecture-overview)
5. [Layer 1: LLM Structured Tagging](#5-layer-1-llm-structured-tagging)
6. [Layer 2: Vector Embeddings](#6-layer-2-vector-embeddings)
7. [Layer 3: Google Workspace Communication History](#7-layer-3-google-workspace-communication-history)
8. [Scoring Models](#8-scoring-models)
9. [Schema Design](#9-schema-design)
10. [Processing Pipeline](#10-processing-pipeline)
11. [Technology Choices](#11-technology-choices)
12. [Use Cases](#12-use-cases)
13. [Phase Plan](#13-phase-plan)
14. [Cost Estimates](#14-cost-estimates)
15. [Open Questions](#15-open-questions)

---

## 1. Vision

Build a system that lets Justin search, sort, and segment his ~2,500 LinkedIn contacts across multiple dimensions simultaneously:

- **Relationship warmth** — Who do I actually know? Who's a close friend vs. a distant connection?
- **Giving capacity** — Who has the means to donate to Outdoorithm Collective or invest in Kindora?
- **Topical affinity** — Who cares about outdoor equity, philanthropy, nature, AI for social good, CSR?
- **Sales fit** — Who could be a Kindora enterprise customer (foundations, networks, intermediaries)?
- **Communication context** — What have I talked about with this person, and when?

The goal is to generate actionable outreach lists like:
- "Close personal contacts to invite to Outdoorithm Collective's first fundraiser"
- "High-capacity contacts who share my interest in outdoor equity"
- "Foundation leaders I should pitch Kindora enterprise licenses to"
- "People I haven't spoken to in 2+ years who'd be interested in my newsletter"

**Design principles:**
- Practical over perfect — ship something useful quickly, refine later
- Avoid over-abstraction — use simple columns and JSONB, not a graph database
- Leverage what exists — pgvector is already installed, 2,400 contacts are already enriched, Camelback has a working embedding pattern
- LLM for classification, embeddings for similarity — they solve different problems

---

## 2. What We Have Today

### Contacts Database (2,498 rows)

| Data | Coverage | Source |
|------|----------|--------|
| Basic info (name, company, title) | ~100% | LinkedIn export |
| LinkedIn URL | 96% (2,398) | LinkedIn export |
| Apify enrichment (employment, education, skills, volunteering, JSONB) | 96% (2,404) | Apify batch run Feb 2026 |
| Flat enrichment columns (schools, companies_worked, titles_held arrays) | 96% | Computed from Apify data |
| Connection date (when connected on LinkedIn) | 91% (2,266) | LinkedIn export, Apr 2015–Oct 2024 |
| Donor scoring (capacity, propensity, affinity, warmth) | 53% (1,315) | Perplexity sonar-reasoning-pro |
| Warmth/connection type classification | 52% (1,305) | Perplexity — mostly "Cold" (94%) |
| Perplexity deep research | 53% (1,315) | sonar-reasoning-pro ~$0.022/contact |
| Email addresses | ~60% | Various sources |
| LinkedIn posts | 51 posts (Justin's only) | Apify post scraper |

### Key Observations

1. **Existing warmth scoring is useless.** 94% of scored contacts are "Cold" with "No known connection." This was done without Justin's full career graph as context — it couldn't find shared employers, schools, or boards because it didn't have Justin's data as a reference.

2. **Rich JSONB data is already stored.** Each contact has `enrich_employment`, `enrich_education`, `enrich_skills_detailed`, `enrich_volunteering`, `enrich_certifications`, `enrich_publications` as JSONB arrays with company names, titles, dates, descriptions, school names, fields of study.

3. **pgvector 0.8.0 is installed.** The Camelback table already uses 1536-dimension embeddings with HNSW indexing — proven pattern.

4. **Connected_on dates** provide a temporal signal: people Justin connected with 10 years ago in 2015 are likely closer than someone from 2024.

5. **Justin's full profile is now scraped** — 12 positions, 3 schools, 2 board/volunteer roles, 76 posts, 6,061 followers.

---

## 3. The Anchor: Justin's Profile Graph

All scoring is relative to Justin. His career provides the nodes for shared-institution matching:

### Employers
| Organization | Role | Years |
|-------------|------|-------|
| Kindora | Co-Founder & CEO | 2025–present |
| True Steele LLC | Founder & Fractional CIO | 2024–present |
| Outdoorithm Collective | Co-Founder, Treasurer | 2024–present |
| Outdoorithm | Co-Founder, CTO | 2023–present |
| Google / Google.org | Director, Americas; Racial Justice Lead | ~6 years |
| Year Up | Deputy Director, PM, Dir Strategy & Ops | ~5 years |
| Northern Virginia Community College | Adjunct Professor | ~2 years |
| The Bridgespan Group | Senior Associate Consultant | ~2 years |
| Bain and Company | Associate Consultant | ~2 years |

### Schools
| School | Degree |
|--------|--------|
| Harvard Business School | MBA |
| Harvard Kennedy School | MPA/MPP |
| University of Virginia | Engineering (BS) |

### Boards & Volunteering
| Organization | Role |
|-------------|------|
| San Francisco Foundation | Program Chair, Board of Trustees |
| Outdoorithm Collective | Treasurer, Board of Directors |

### Key Topics (from posts and profile)
- Outdoor equity, nature access, public lands
- AI for social good, public interest technology
- Philanthropy, corporate social responsibility
- Nonprofit fundraising, grant matching
- Racial justice, equity, DEI
- Systems change, social innovation
- Education, workforce development
- Fatherhood, family camping

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    CONTACTS TABLE                        │
│  2,498 rows with LinkedIn enrichment JSONB              │
└─────────┬───────────────────────────┬───────────────────┘
          │                           │
    ┌─────▼──────┐             ┌──────▼──────┐
    │  Layer 1   │             │   Layer 2   │
    │  LLM Tags  │             │  Embeddings │
    │ (GPT-5m)   │             │  (pgvector) │
    └─────┬──────┘             └──────┬──────┘
          │                           │
          │  Structured JSONB:        │  vector(768) columns:
          │  - relationship_proximity │  - profile_embedding
          │  - giving_capacity_tier   │  - interests_embedding
          │  - topical_interests[]    │  - posts_embedding (future)
          │  - sales_fit_score        │
          │  - outreach_hooks[]       │  Enables:
          │  - talking_points[]       │  - "Find people like X"
          │                           │  - "Who shares my interests?"
    ┌─────▼───────────────────────────▼───────┐
    │              Layer 3                     │
    │     Google Workspace History             │
    │  Gmail + Calendar + Chat context         │
    │  Stored in communication_history JSONB   │
    └─────────────────────────────────────────┘
```

**Why three layers instead of one:**
- **Layer 1 (LLM tags)** answers discrete questions: "Is this person a VP+ at a large company?" "Did they work at Google?" These are filterable, sortable columns.
- **Layer 2 (embeddings)** answers fuzzy questions: "Who in my network is most similar to this specific foundation program officer?" "Who writes about topics related to outdoor equity?" Embeddings capture semantic similarity that structured tags miss.
- **Layer 3 (comms history)** answers relationship questions: "When did I last email this person?" "What did we discuss?" This is the context that makes outreach personal rather than generic.

---

## 5. Layer 1: LLM Structured Tagging

### Model Choice: GPT-5 mini (structured output mode)

GPT-5 mini with structured JSON output via the Responses API is the right tool here because:
- Large context window (128K+) handles a full profile + posts in one call
- Structured output mode guarantees valid JSON matching a schema
- Cheap enough for batch processing (~$0.10-0.30/contact depending on input size)
- Can reason about relationships ("This person worked at Google from 2018-2022, overlapping with Justin's tenure")

### Input per Contact

Assemble a context document for each contact:

```
ANCHOR PERSON (Justin Steele):
- Employers: [Kindora, True Steele, Outdoorithm, Google/Google.org, Year Up, Bridgespan, Bain]
- Schools: [Harvard Business School, Harvard Kennedy School, University of Virginia]
- Boards: [San Francisco Foundation, Outdoorithm Collective]
- Key interests: [outdoor equity, AI for social good, philanthropy, racial justice, nonprofit fundraising]

TARGET CONTACT: {first_name} {last_name}
- Headline: {headline}
- Current: {company} - {position}
- Summary: {summary}
- Employment History: {enrich_employment JSON}
- Education: {enrich_education JSON}
- Skills: {enrich_skills_detailed JSON}
- Volunteering: {enrich_volunteering JSON}
- Certifications: {enrich_certifications JSON}
- Publications: {enrich_publications JSON}
- Awards: {enrich_honors_awards JSON}
- LinkedIn connected: {connected_on}
- Location: {city}, {state}
```

Estimated input: ~2,000-5,000 tokens per contact for well-enriched profiles.

### Output Schema

```json
{
  "relationship_proximity": {
    "score": 0-100,
    "tier": "inner_circle|close|warm|familiar|acquaintance|distant",
    "shared_employers": [{"org": "Google", "overlap_years": "2018-2022", "relationship": "colleague"}],
    "shared_schools": [{"school": "Harvard Business School", "overlap": "likely"}],
    "shared_boards": [],
    "shared_volunteering": [],
    "proximity_signals": ["direct report at Google.org", "both on Year Up board"],
    "reasoning": "Worked directly under Justin at Google.org for 6 years..."
  },
  "giving_capacity": {
    "tier": "major_donor|mid_level|grassroots|unknown",
    "score": 0-100,
    "signals": ["C-suite at Fortune 500", "Board of XYZ Foundation", "20+ years experience"],
    "estimated_range": "$10K-$50K",
    "reasoning": "VP at Google with 15 years experience, serves on nonprofit boards..."
  },
  "topical_affinity": {
    "topics": [
      {"topic": "outdoor_equity", "strength": "high", "evidence": "Volunteers with Sierra Club"},
      {"topic": "philanthropy", "strength": "medium", "evidence": "Works at foundation"},
      {"topic": "ai_social_good", "strength": "low", "evidence": "Headline mentions AI"}
    ],
    "primary_interests": ["workforce development", "education equity"],
    "talking_points": [
      "Their work at Year Up aligns with Justin's focus on workforce mobility",
      "Recently posted about AI ethics — could connect over Kindora's mission"
    ]
  },
  "sales_fit": {
    "kindora_prospect": true,
    "prospect_type": "enterprise_buyer|champion|influencer|not_relevant",
    "score": 0-100,
    "reasoning": "Leads grantmaking at a network of 50+ nonprofits — ideal enterprise license buyer",
    "signals": ["manages nonprofit network", "VP of Programs at intermediary"]
  },
  "outreach_context": {
    "outdoorithm_invite_fit": "high|medium|low|none",
    "kindora_pitch_fit": "high|medium|low|none",
    "best_approach": "personal_email|linkedin_message|intro_via_mutual",
    "personalization_hooks": [
      "Mention their recent post about accessible parks",
      "Reference shared time at Google.org",
      "Their daughter is same age as Justin's kids"
    ],
    "suggested_opener": "Hey Sarah, I was thinking about you after seeing your post about..."
  }
}
```

### Cost Optimization: Two-Pass LLM Approach

For contacts with very large enrichment payloads (extensive employment history, publications, etc.), use a two-pass strategy:

1. **Pass 1 (GPT-5 Nano, $0.05/M input):** Summarize raw LinkedIn JSONB into a structured ~500-token profile summary. Nano achieves ~98-100% JSON reliability and is sufficient for distillation.
2. **Pass 2 (GPT-5 Mini, structured output):** Classify the compressed summary using the full Pydantic schema above.

This keeps costs under control for the ~10% of contacts with 5,000+ token profiles while maintaining classification quality. For most contacts (~3,000 tokens), a single GPT-5 Mini pass is fine.

**Revised cost estimate with two-pass:**
- 2,250 contacts x single pass: ~$2.10
- 250 contacts x two-pass: ~$0.35 (Nano) + $0.25 (Mini) = ~$0.60
- **Total: ~$2.70** (barely more than single-pass)

### Why Not Just Use Embeddings for Everything?

Embeddings are great for "find similar" but bad for:
- Discrete categorical answers ("Is this person C-suite? Yes/No")
- Numerical scoring ("Give capacity: $10K-$50K range")
- Generating personalized outreach hooks
- Reasoning about temporal overlap ("They were at Google 2018-2022, same as Justin")

The LLM sees the full context and reasons about it. Embeddings compress everything into a vector and lose the specifics.

---

## 6. Layer 2: Vector Embeddings

### What to Embed

Two embedding strategies, stored as separate columns:

**1. Profile Embedding (`profile_embedding vector(768)`):**
Build a composite text document from each contact's structured data:

```
{name} | {headline}
Currently: {current_title} at {current_company}
Previously: {company1} ({title1}), {company2} ({title2}), ...
Education: {school1} ({degree1}), {school2} ({degree2}), ...
Skills: {skill1}, {skill2}, ...
Volunteering: {org1} ({role1}), ...
Location: {city}, {state}
About: {summary}
```

This enables queries like:
- "Find contacts whose career profile is most similar to [a specific foundation program officer]"
- "Who in my network has a background most like [a specific Kindora customer persona]?"

**2. Interests Embedding (`interests_embedding vector(768)`):**
Build from the LLM-generated topical tags + post content:

```
Primary interests: outdoor equity, philanthropy, AI for social good
Talking points: {from LLM output}
Post themes: {summarized from any scraped posts}
About section: {summary}
```

This enables:
- "Who in my network cares about the same things I do?"
- "Find contacts interested in [outdoor recreation AND environmental justice]"
- "Who would resonate with this specific fundraising pitch?"

### Embedding Model: `text-embedding-3-small` at 768 dimensions

**Why 768 and not 1536:**
- Supabase benchmarks show **384-768 dimensions deliver optimal performance-to-accuracy ratio** for pgvector
- 768 dims cut storage and query latency roughly in half vs. 1536 with minimal accuracy loss (~1-2%)
- OpenAI's text-embedding-3-small supports native Matryoshka dimension truncation — request 768 dims directly from the API
- At 2,500 contacts with 2 embeddings each, storage is trivial either way, but faster queries matter for interactive use
- **Note:** Our Camelback embeddings use 1536 dims. Future migration could unify these, but it's a separate concern.

### Indexing

```sql
CREATE INDEX ON contacts
USING hnsw (profile_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX ON contacts
USING hnsw (interests_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

HNSW over IVFFlat because:
- Better recall at small-to-medium scale (2,500 rows)
- No need to rebuild after inserts
- Supabase recommends HNSW as default in 2025

### Similarity Search Function

```sql
CREATE OR REPLACE FUNCTION match_contacts_by_profile(
  query_embedding vector(768),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 20
)
RETURNS TABLE (
  id int,
  first_name text,
  last_name text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT id, first_name, last_name,
    1 - (profile_embedding <=> query_embedding) AS similarity
  FROM contacts
  WHERE 1 - (profile_embedding <=> query_embedding) > match_threshold
  ORDER BY profile_embedding <=> query_embedding
  LIMIT match_count;
$$;
```

### Advanced: Hybrid Search with Reciprocal Rank Fusion (RRF)

For highest-quality results, combine semantic similarity, full-text keyword search, and structured filters using RRF:

```sql
CREATE OR REPLACE FUNCTION hybrid_contact_search(
  query_text text,
  query_embedding vector(768),
  filter_proximity_min int DEFAULT 0,
  filter_capacity_min int DEFAULT 0,
  semantic_weight float DEFAULT 1.0,
  keyword_weight float DEFAULT 1.0,
  match_count int DEFAULT 25,
  rrf_k int DEFAULT 50
)
RETURNS TABLE (id int, first_name text, last_name text, score float)
LANGUAGE sql AS $$
  WITH semantic AS (
    SELECT c.id, c.first_name, c.last_name,
      ROW_NUMBER() OVER (ORDER BY c.profile_embedding <=> query_embedding) AS rank
    FROM contacts c
    WHERE c.profile_embedding IS NOT NULL
      AND c.ai_proximity_score >= filter_proximity_min
      AND c.ai_capacity_score >= filter_capacity_min
    ORDER BY c.profile_embedding <=> query_embedding
    LIMIT match_count * 2
  ),
  keyword AS (
    SELECT c.id, c.first_name, c.last_name,
      ROW_NUMBER() OVER (ORDER BY ts_rank(
        to_tsvector('english', COALESCE(c.headline,'') || ' ' || COALESCE(c.summary,'') || ' ' || COALESCE(c.company,'') || ' ' || COALESCE(c.position,'')),
        websearch_to_tsquery('english', query_text)
      ) DESC) AS rank
    FROM contacts c
    WHERE to_tsvector('english', COALESCE(c.headline,'') || ' ' || COALESCE(c.summary,'') || ' ' || COALESCE(c.company,'') || ' ' || COALESCE(c.position,''))
      @@ websearch_to_tsquery('english', query_text)
      AND c.ai_proximity_score >= filter_proximity_min
      AND c.ai_capacity_score >= filter_capacity_min
    LIMIT match_count * 2
  )
  SELECT COALESCE(s.id, k.id), COALESCE(s.first_name, k.first_name),
    COALESCE(s.last_name, k.last_name),
    COALESCE(semantic_weight / (rrf_k + s.rank), 0.0) +
    COALESCE(keyword_weight / (rrf_k + k.rank), 0.0) AS score
  FROM semantic s FULL OUTER JOIN keyword k ON s.id = k.id
  ORDER BY score DESC
  LIMIT match_count;
$$;
```

This pattern (semantic + keyword + structured WHERE clauses + RRF fusion) is the established best practice across Supabase, Pinecone, and Weaviate ecosystems as of 2025-2026.

### Future Enhancement: Two-Stage Reranking

For highest-quality results when the initial hybrid search returns too many plausible matches:
1. **Stage 1 (Fast ANN):** Run the hybrid search above for top-50 candidates
2. **Stage 2 (Rerank):** Send top 50 to an LLM or cross-encoder (Cohere Rerank) that scores each result against the original query with full profile context
3. **Stage 3 (Business logic):** Apply relationship warmth and capacity scores as final boost/penalty

Not needed at 2,500 contacts where top-25 results are likely precise enough. Worth adding if the database grows or if query quality needs fine-tuning.

### Future Enhancement: Section-Level Chunk Embeddings

For 2,500 contacts, whole-profile embeddings are sufficient. If we later need more precision (e.g., "Who has fintech engineering experience specifically?"), we can add a `contact_embeddings` table with per-section chunks (one row per role, per school, per volunteer position). This enables matching against specific career segments rather than a diluted whole-profile vector. Not needed for Phase 1.

---

## 7. Layer 3: Google Workspace Communication History

### Goal

Add a `communication_history` JSONB column that captures the essence of Justin's interactions with each contact across Gmail, Google Calendar, and Google Chat.

### Data Sources (via MCP Servers)

Justin has MCP server connections to multiple Google Workspace accounts:
- `google-workspace` (primary)
- `google-workspace-truesteele`
- `google-workspace-outdoorithm-collective`
- `google-workspace-kindora`
- `google-workspace-outdoorithm`

Each provides tools like:
- `search_gmail_messages` — search by contact email
- `get_gmail_message_content` — read individual messages
- `get_gmail_thread_content` — read entire email threads
- `get_events` — calendar events with attendees

### Collection Strategy

For each contact with an email address:

1. **Search Gmail** across all accounts for messages to/from that email
2. **Summarize** each thread into a brief description (using LLM, not storing full email text)
3. **Extract metadata**: dates, subject lines, direction (sent/received), account
4. **Store** in a structured JSONB with a token budget

### Schema

```json
{
  "last_gathered": "2026-02-18T00:00:00Z",
  "total_threads": 12,
  "first_contact": "2019-03-15",
  "last_contact": "2025-11-20",
  "accounts_with_activity": ["google-workspace", "google-workspace-kindora"],
  "threads": [
    {
      "date": "2025-11-20",
      "account": "google-workspace-kindora",
      "subject": "Kindora demo follow-up",
      "direction": "sent",
      "summary": "Justin followed up after a Kindora demo, discussing enterprise pricing for their network of 30 nonprofits.",
      "message_count": 4
    },
    {
      "date": "2024-06-10",
      "account": "google-workspace",
      "subject": "Catching up",
      "direction": "received",
      "summary": "Sarah reached out to reconnect after leaving Google. Discussed her new role at the foundation and Justin's Outdoorithm work.",
      "message_count": 6
    }
  ],
  "relationship_summary": "12 email exchanges over 6 years. Started as colleagues at Google (2019), continued after both left. Recent thread about potential Kindora partnership for her foundation network. Warm, professional tone with personal elements (asked about each other's families)."
}
```

### Token Budget

- **Thread summaries:** 1-2 sentences each, ~30-50 tokens
- **Relationship summary:** 2-3 sentences, ~50-100 tokens
- **Max threads stored:** 20 most recent/significant
- **Total per contact:** ~500-1,500 tokens in JSONB
- This keeps the data compact enough to include in LLM context for outreach drafting

### Privacy Considerations

- Store summaries, not raw email text
- Don't expose email content in any public-facing UI
- This data stays in the personal contacts database, not the Kindora product
- Use it only for Justin's own outreach — not shared with others

---

## 8. Scoring Models

### 8.1 Relationship Proximity Score (0-100)

Based on Granovetter's tie strength theory, weighted by:

| Signal | Weight | Max Points | Source |
|--------|--------|------------|--------|
| Shared employer (same time) | High | 25 | LLM analysis of employment overlap |
| Shared school (same era) | High | 20 | LLM analysis of education dates |
| Shared board/volunteer org | High | 15 | LLM analysis of volunteer data |
| Communication recency | Medium | 15 | Google Workspace Layer 3 |
| Communication volume | Medium | 10 | Google Workspace Layer 3 |
| LinkedIn connection tenure | Low | 5 | `connected_on` date |
| Mutual recommendations | Medium | 5 | LinkedIn recommendations |
| Shared location | Low | 5 | Location data |

**Tier mapping:**
- **Inner Circle (80-100):** Worked together directly, regular communication, personal relationship
- **Close (60-79):** Shared institution with overlap, periodic communication
- **Warm (40-59):** Shared institution but different era, or met through mutual context
- **Familiar (20-39):** Connected on LinkedIn, maybe met once, some shared interests
- **Acquaintance (10-19):** LinkedIn connection, no meaningful interaction
- **Distant (0-9):** Connected but no overlap or communication

### 8.2 Giving Capacity Score (0-100)

Proxy-based estimation from public LinkedIn data:

| Signal | Weight | Points |
|--------|--------|--------|
| C-suite / founder title | High | 20 |
| VP+ at large company (10K+ employees) | High | 15 |
| Board seats at foundations/nonprofits | High | 15 |
| 20+ years professional experience | Medium | 10 |
| Elite school (Ivy+, Stanford, MIT, etc.) | Low | 5 |
| Multiple company founder | Medium | 10 |
| Director+ at FAANG/BigTech | Medium | 10 |
| Senior at consulting/finance | Medium | 10 |
| Volunteer leadership roles | Low | 5 |

**Tier mapping:**
- **Major Donor ($10K+):** Score 70+ — C-suite, founders, senior leaders at large companies
- **Mid-Level ($1K-$10K):** Score 40-69 — Directors, senior managers, experienced professionals
- **Grassroots ($100-$1K):** Score 15-39 — Individual contributors, early career
- **Unknown (0-14):** Insufficient data

### 8.3 Topical Affinity (tag-based + embedding)

The LLM tags each contact with topics from a controlled vocabulary:

```
outdoor_equity, nature_recreation, environmental_justice,
philanthropy, grantmaking, nonprofit_leadership,
ai_technology, social_impact_tech, public_interest_tech,
corporate_social_responsibility, esg,
racial_justice, dei, equity,
education, workforce_development,
family_youth, parenting,
social_enterprise, impact_investing,
community_development, urban_equity
```

Each tag gets a strength: `high`, `medium`, `low` with evidence text.

The interests embedding enables fuzzy matching beyond these discrete tags.

### 8.4 Kindora Sales Fit (0-100)

Specific to finding enterprise Kindora customers:

| Signal | Points |
|--------|--------|
| Works at a foundation/funder | 25 |
| Manages/leads a nonprofit network or intermediary | 25 |
| Title includes "Programs", "Grants", "Philanthropy" | 15 |
| Works in nonprofit technology/SaaS | 10 |
| Has influence over nonprofit purchasing decisions | 15 |
| Recently posted about fundraising challenges | 10 |

**Prospect types:**
- **Enterprise Buyer:** Directly licenses Kindora for a network (foundations, intermediaries, United Ways)
- **Champion:** Internal advocate who can push for adoption
- **Influencer:** Respected voice who could refer or amplify
- **Not Relevant:** No clear connection to Kindora's market

---

## 9. Schema Design

### New Columns on `contacts` Table

```sql
-- Layer 1: LLM structured tags
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  ai_tags jsonb;  -- Full LLM output from Section 5

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  ai_tags_generated_at timestamptz;

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  ai_tags_model text;  -- e.g., 'gpt-5-mini-2026-02'

-- Layer 2: Vector embeddings
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  profile_embedding vector(768);

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  interests_embedding vector(768);

-- Layer 3: Communication history
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  communication_history jsonb;

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  comms_last_gathered_at timestamptz;

-- Computed/denormalized scores (from ai_tags, for fast filtering)
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  ai_proximity_score integer;  -- 0-100, from ai_tags.relationship_proximity.score

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  ai_proximity_tier text;  -- inner_circle, close, warm, familiar, acquaintance, distant

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  ai_capacity_score integer;  -- 0-100, from ai_tags.giving_capacity.score

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  ai_capacity_tier text;  -- major_donor, mid_level, grassroots, unknown

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  ai_kindora_prospect_score integer;  -- 0-100

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  ai_kindora_prospect_type text;  -- enterprise_buyer, champion, influencer, not_relevant

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
  ai_outdoorithm_fit text;  -- high, medium, low, none
```

### Why Denormalized Scores + Full JSONB?

- **Denormalized integer columns** (`ai_proximity_score`, `ai_capacity_score`) enable fast SQL filtering: `WHERE ai_proximity_score >= 60 AND ai_capacity_score >= 40`
- **Full JSONB** (`ai_tags`) preserves the reasoning, evidence, talking points — essential for outreach drafting
- This avoids JOIN overhead and keeps queries simple

### Indexes

```sql
-- Composite index for common query patterns
CREATE INDEX idx_contacts_proximity_capacity
ON contacts (ai_proximity_tier, ai_capacity_tier)
WHERE ai_proximity_score IS NOT NULL;

-- Vector indexes
CREATE INDEX idx_contacts_profile_embedding
ON contacts USING hnsw (profile_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_contacts_interests_embedding
ON contacts USING hnsw (interests_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- GIN index on JSONB for tag queries
CREATE INDEX idx_contacts_ai_tags
ON contacts USING gin (ai_tags jsonb_path_ops);
```

---

## 10. Processing Pipeline

### Phase 1: LLM Tagging (Batch)

```
For each contact (2,498):
  1. Assemble context document (Justin's profile + contact's enrichment data)
  2. Call GPT-5 mini with structured output schema
  3. Parse response, store in ai_tags JSONB
  4. Extract scores into denormalized columns
  5. Rate limit: ~50 RPM (OpenAI Tier 5), batch of 10 concurrent
```

**Estimated cost:** ~2,500 contacts x ~3,000 input tokens x ~800 output tokens
- Input: ~7.5M tokens @ $0.15/1M = $1.13
- Output: ~2M tokens @ $0.60/1M = $1.20
- **Total: ~$2.33** (extremely cheap with GPT-5 mini)

**Estimated time:** ~5 minutes at 50 RPM with 10 concurrent

### Phase 2: Embedding Generation (Batch)

```
For each contact:
  1. Build profile text document
  2. Build interests text document
  3. Call text-embedding-3-small with dimensions=768
  4. Store both vectors in contacts table
```

**Estimated cost:** ~5,000 embedding calls x ~500 tokens = 2.5M tokens @ $0.02/1M = $0.05

**Estimated time:** ~2 minutes

### Phase 3: Communication History (Incremental)

```
For each contact with email:
  1. Search Gmail across all accounts for to/from that email
  2. For each thread found, summarize with GPT-5 mini
  3. Store in communication_history JSONB
  4. Rate limit: Gmail API (250 quota units/second)
```

**This is the slowest/most expensive layer.** Strategy:
- Start with high-priority contacts (proximity score >= 40 or capacity >= 40)
- Process incrementally, not all at once
- Set a per-contact thread limit (20 most recent)
- Summarize threads in batches

**Estimated cost:** ~$5-15 for the full database (Gmail API is free, LLM summarization is the cost)

---

## 11. Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| LLM (tagging) | GPT-5 mini (structured output) | Cheapest model with reliable structured JSON, huge context window |
| Embedding model | text-embedding-3-small (768 dims) | Native dimension control, excellent price/performance, Supabase recommended |
| Vector store | pgvector (Supabase built-in) | Already installed, no external service needed, HNSW indexing |
| Email access | Google Workspace MCP servers | Already configured for all Justin's accounts |
| Processing | Python script (like enrich_contacts_apify.py) | Proven pattern, can reuse the ThreadPoolExecutor + Supabase pagination approach |
| API client | OpenAI Python SDK (`openai`) | Structured output via `response_format`, batch API available |

### Why GPT-5 mini Over Alternatives?

- **Claude:** Better reasoning but no structured output guarantee (yet). Could hallucinate JSON.
- **o4-mini:** Good but more expensive than GPT-5 mini for this use case.
- **Local models:** Too slow for 2,500 contacts and unreliable structured output.
- **GPT-5 mini:** Cheapest, fastest, and `response_format={"type": "json_schema", ...}` guarantees valid JSON.

### Why Not Use Supabase Edge Functions?

For production (Kindora product), Edge Functions make sense for real-time embedding on insert. For this personal batch job, a Python script is simpler and more debuggable.

### Competitive Landscape

What exists commercially, and where our system differs:

| Tool | Category | Pricing | What They Do | What We Take |
|------|----------|---------|--------------|-------------|
| **Affinity** | Relationship CRM | Enterprise ($$$) | Graph-based relationship scoring from auto-logged email/calendar. MCP integration with LLMs. | Closest model to ours — their warmth scoring approach (communication frequency × recency × bidirectionality) informs our Section 8.1 formula |
| **4Degrees** | Relationship CRM | Enterprise ($$$) | Real-time relationship strength scores, warm intro path finding | Mutual connection quality weighting concept |
| **Clay** | Data orchestration | $134-720/mo | Waterfall enrichment across 75+ sources, Claygent AI research agent | Waterfall approach (cheap sources first). We already have this with Apify→Perplexity |
| **folk CRM** | Personal CRM | $20-40/mo | AI enrichment via People Data Labs + Perplexity, "Magic Fields" for per-contact AI prompts | Closest to our personal-use case. Our system goes deeper on scoring |
| **DonorSearch** | Wealth screening | ~$4K/yr | AI giving predictions, philanthropic history database | Gold standard for giving data. Too expensive for personal use — our LinkedIn proxy model fills the gap |
| **iWave/Kindsight** | Wealth screening | ~$4K/yr | Customizable capacity scoring weights, combines SEC + real estate + political donations | Their tiered capacity framework informs our Section 8.2 |
| **WealthEngine** | Wealth screening | ~$5K+/yr | ML-powered pre-scored profiles, Altrata data | Enterprise-grade; our proxy approach is ~1% of the cost |
| **Apollo.io** | Sales intelligence | $59/user/mo | 275M+ contact database, built-in sequences | Less relevant — we already have contacts, need intelligence not data |

**Our differentiation:** We combine relationship proximity (like Affinity), giving capacity estimation (like iWave), topical affinity (like semantic search tools), and communication history (like Introhive) in a single personal system for ~$13 total processing cost instead of $10K+/year in SaaS subscriptions. The tradeoff is that our wealth estimates are LinkedIn proxy-based rather than sourced from SEC filings and real estate records.

---

## 12. Use Cases

### Use Case 1: "Outdoorithm Collective Fundraiser Invite"

```sql
SELECT first_name, last_name, company, position,
  ai_proximity_tier, ai_capacity_tier,
  ai_tags->'outreach_context'->>'outdoorithm_invite_fit' as invite_fit,
  ai_tags->'topical_affinity'->'topics' as topics,
  ai_tags->'outreach_context'->'personalization_hooks' as hooks
FROM contacts
WHERE ai_proximity_score >= 40  -- warm or better
  AND ai_tags->'outreach_context'->>'outdoorithm_invite_fit' IN ('high', 'medium')
ORDER BY ai_proximity_score DESC, ai_capacity_score DESC;
```

### Use Case 2: "Kindora Enterprise Prospects"

```sql
SELECT first_name, last_name, company, position,
  ai_kindora_prospect_score, ai_kindora_prospect_type,
  ai_tags->'sales_fit'->>'reasoning' as fit_reasoning
FROM contacts
WHERE ai_kindora_prospect_score >= 50
  AND ai_kindora_prospect_type IN ('enterprise_buyer', 'champion')
ORDER BY ai_kindora_prospect_score DESC;
```

### Use Case 3: "People Interested in Outdoor Equity" (semantic search)

```python
# Generate embedding for the query
query = "outdoor equity, nature access, public lands, camping, environmental justice"
query_embedding = openai.embeddings.create(
    model="text-embedding-3-small",
    input=query,
    dimensions=768
).data[0].embedding

# Search via pgvector
results = supabase.rpc("match_contacts_by_interests", {
    "query_embedding": query_embedding,
    "match_threshold": 0.6,
    "match_count": 50
}).execute()
```

### Use Case 4: "Close Contacts I Haven't Spoken To Recently"

```sql
SELECT first_name, last_name, company,
  ai_proximity_tier,
  communication_history->>'last_contact' as last_contact,
  communication_history->>'relationship_summary' as summary
FROM contacts
WHERE ai_proximity_score >= 60
  AND (communication_history->>'last_contact')::date < NOW() - INTERVAL '2 years'
ORDER BY ai_proximity_score DESC;
```

### Use Case 5: "Hybrid Search — Warm Contacts + Topic Match"

```sql
-- Combine structured filters with semantic similarity
SELECT c.first_name, c.last_name, c.company,
  c.ai_proximity_score,
  1 - (c.interests_embedding <=> $query_embedding) as topic_similarity
FROM contacts c
WHERE c.ai_proximity_score >= 30
  AND c.ai_capacity_score >= 30
  AND c.interests_embedding IS NOT NULL
ORDER BY
  (c.ai_proximity_score / 100.0 * 0.4) +
  (1 - (c.interests_embedding <=> $query_embedding)) * 0.6
  DESC
LIMIT 25;
```

---

## 13. Phase Plan

### Phase 1: LLM Tagging — COMPLETE
**Status:** Done (2026-02-18)
**Script:** `scripts/intelligence/tag_contacts_gpt5m.py` (~540 lines)
**Model:** GPT-5 mini with Pydantic structured output
**Results:** 2,402/2,402 contacts tagged (100% after dedup), 0 errors
**Cost:** ~$5-7 total
**Score distributions:**
- Proximity: inner_circle=23, close=706, warm=997, familiar=563, acquaintance=191, distant=16
- Capacity: major_donor=504, mid_level=1440, grassroots=537, unknown=15
- Averages well-centered: proximity=49, capacity=52, kindora=51

### Phase 2: Vector Embeddings — COMPLETE
**Status:** Done (2026-02-18)
**Script:** `scripts/intelligence/generate_embeddings.py` (~500 lines)
**Model:** text-embedding-3-small at 768 dimensions
**Results:** 2,402/2,402 profile embeddings, 2,400/2,402 interests embeddings (2 contacts have zero profile data)
**Cost:** ~$0.03
**RPC functions created:**
- `match_contacts_by_profile` — semantic similarity on profile_embedding
- `match_contacts_by_interests` — semantic similarity on interests_embedding
- `hybrid_contact_search` — semantic + keyword + RRF fusion
**Validation:** All 5 use cases validated, results in `docs/reports/network-intelligence-validation.md`

### Data Deduplication — COMPLETE
**Status:** Done (2026-02-18)
**Script:** `scripts/intelligence/deduplicate_contacts.py`
**Results:** 96 duplicate rows merged and deleted (77 by LinkedIn URL, 16 by manual review of same-name/different-URL pairs, 3 by email). 91 FK references reassigned.
**Final count:** 2,402 unique contacts (down from 2,498)

### Phase 3: Communication History (Future)
**Goal:** Map Justin's email/calendar history to contacts.

1. Write script that uses MCP Google Workspace tools to search Gmail
2. Process high-priority contacts first (proximity >= 40)
3. Summarize threads with GPT-5 mini
4. Store in communication_history JSONB

**Output:** Rich communication context for ~500+ contacts who Justin has actually emailed.

### Phase 4: AI Filter Co-pilot UI — COMPLETE
**Status:** Done (2026-02-18)
**Goal:** Replace the agentic chat interface with a structured AI Filter Co-pilot — natural language query → structured filters → interactive table → prospect lists → outreach drafting → email sending.

**Architecture (final):**
- **AI Filter Parsing:** Claude Sonnet 4.6 with forced `tool_use` translates NL queries into structured `FilterState` JSON
- **Search Execution:** Separate search endpoint applies filters via Supabase queries or hybrid search (semantic + keyword + RRF)
- **Interactive Table:** Sortable columns, checkbox selection, tier badges, pipeline status tracking
- **Prospect Lists:** Save/load named lists with outreach status per contact (Supabase `prospect_lists` + `prospect_list_members` tables)
- **Outreach Drafting:** Claude Sonnet 4.6 generates personalized emails using contact context, shared history, and personalization hooks
- **Email Sending:** Resend API for HTML email delivery from `justin@truesteele.com`

**Key Components Built:**
| Component | File | Description |
|-----------|------|-------------|
| NLQueryBar | `components/nl-query-bar.tsx` | Natural language input with suggested queries |
| FilterBar | `components/filter-bar.tsx` | Editable filter chips, color-coded by category |
| ContactsTable | `components/contacts-table.tsx` | Sortable data table with selection and tier badges |
| ContactDetailSheet | `components/contact-detail-sheet.tsx` | Slide-out panel with full contact profile |
| ListManager | `components/list-manager.tsx` | Save/load prospect lists |
| PipelineStatus | `components/pipeline-status.tsx` | Per-contact outreach status tracking |
| OutreachDrawer | `components/outreach-drawer.tsx` | Draft generation, editing, and sending |
| NetworkCopilot | `components/network-copilot.tsx` | Main orchestrator container |

**API Routes Built:**
| Route | Method | Description |
|-------|--------|-------------|
| `/api/network-intel/parse-filters` | POST | NL query → FilterState via Claude |
| `/api/network-intel/search` | POST | FilterState → matching contacts |
| `/api/network-intel/contact/[id]` | GET | Full contact detail with ai_tags extraction |
| `/api/network-intel/prospect-lists` | GET/POST | List all or create prospect list |
| `/api/network-intel/prospect-lists/[id]` | GET/PATCH/DELETE | CRUD on individual list |
| `/api/network-intel/outreach/draft` | POST | AI draft generation for selected contacts |
| `/api/network-intel/outreach/send` | POST | Send drafts via Resend |

**Database Tables Added:**
- `prospect_lists` — saved prospect list metadata
- `prospect_list_members` — list membership with outreach status tracking
- `outreach_drafts` — generated email drafts with send status

**Complete User Flow:**
1. Type natural language query (e.g., "Who should I invite to the fundraiser?")
2. Claude parses query into structured filters (proximity, capacity, Outdoorithm fit, etc.)
3. Filters appear as editable chips — remove or modify to refine results
4. Results display in sortable table with AI scores and tier badges
5. Click row to see full contact detail (shared context, outreach hooks, topics)
6. Select contacts and save to prospect list
7. Load list to track outreach pipeline status per contact
8. Draft personalized outreach emails (5 tone options, optional context)
9. Review, edit, and send emails via Resend

### Phase 5: Communication History (Future)
**Goal:** Map Justin's email/calendar history to contacts.

1. Write script that uses MCP Google Workspace tools to search Gmail across all 5 accounts
2. Process high-priority contacts first (proximity >= 40)
3. Summarize threads with GPT-5 mini
4. Store in `communication_history` JSONB column
5. Integrate into contact detail sheet and outreach context

**Output:** Rich communication context for ~500+ contacts who Justin has actually emailed.

---

## 14. Cost Estimates

| Component | Est. Cost | Notes |
|-----------|-----------|-------|
| GPT-5 mini tagging (2,500 contacts) | ~$2.50 | Structured output, ~3K input + 800 output tokens each |
| Embeddings (5,000 calls) | ~$0.05 | text-embedding-3-small is very cheap |
| Gmail summarization (~1,000 contacts x ~5 threads) | ~$5-10 | LLM cost for summarization |
| **Total Phase 1-3** | **~$8-13** | |

This is remarkably cheap. The entire pipeline costs less than a single Perplexity deep research call.

---

## 15. Open Questions

1. **Overwrite existing scoring?** The current `donor_capacity_score`, `warmth_level`, `shared_institutions` columns have data for 1,305 contacts (from Perplexity). Should we overwrite them with the new AI-tagged values, or keep both? Recommendation: **Keep old columns, write to new `ai_*` columns**, then deprecate old ones after validating the new scores are better.

2. **Contact posts scraping.** Currently only Justin's posts are in the DB. Should we scrape posts for high-priority contacts to enrich the interests_embedding? Cost: ~$0.15/contact for 50 posts. Could do top 200-300 contacts for ~$30-45.

3. **Refresh frequency.** How often to re-run the tagging pipeline? Recommendation: quarterly, or on-demand when Justin adds new connections.

4. **LinkedIn connection date as signal.** The `connected_on` field ranges from Apr 2015 to Oct 2024. Earlier connections may indicate closer relationships (connected when networks were smaller) or may just be old. The LLM should weigh this with other signals.

5. **Communication history across accounts.** Justin has 5 Google Workspace accounts. Should we search all of them for each contact? Recommendation: yes, but prioritize by account relevance (e.g., `google-workspace` for personal, `kindora` for business).

6. **Embedding model migration.** Camelback uses 1536 dims. Should we also generate 1536-dim embeddings for contacts for cross-table similarity search? Or migrate Camelback to 768 dims? Not urgent — keep them separate for now.
