# Personal Network Intelligence System

**Last updated:** 2026-02-22
**Status:** Phase 1-5 COMPLETE, Phase 6 COMPLETE — All enrichments run, all 2,937 contacts fully scored

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
14. [Phase 6: Donor Psychology Overhaul](#14-phase-6-donor-psychology-overhaul-complete)
    - [14.12 Custom People Search Scraper](#1412-custom-multi-result-people-search-scraper--implemented-2026-02-21)
    - [14.13 Ownership Likelihood Classification](#1413-ownership-likelihood-classification)
    - [14.14 Zillow Batch Data Bug & Re-scrape](#1414-zillow-batch-data-bug--re-scrape-2026-02-22)
    - [14.15 FEC Multi-Person Aggregation Bug Fix](#1415-fec-multi-person-aggregation-bug-fix-2026-02-22)
15. [Cost Estimates](#15-cost-estimates)
16. [Open Questions](#16-open-questions)

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

### Contacts Database (2,937 rows)

| Data | Coverage | Source |
|------|----------|--------|
| Basic info (name, company, title) | ~100% | LinkedIn export |
| LinkedIn URL | 96% | LinkedIn export |
| Apify enrichment (employment, education, skills, volunteering, JSONB) | 96% | Apify batch run Feb 2026 |
| Flat enrichment columns (schools, companies_worked, titles_held arrays) | 96% | Computed from Apify data |
| Connection date (when connected on LinkedIn) | 91% | LinkedIn export, Apr 2015–Oct 2024 |
| AI structured tags (LLM scored) | 100% (2,937) | GPT-5 mini structured output |
| Profile embeddings (768d) | 100% (2,937) | text-embedding-3-small |
| Interests embeddings (768d) | 99.9% (2,933) | text-embedding-3-small |
| Communication history (Gmail) | 628 contacts | 5 Gmail accounts, LLM-summarized |
| Familiarity ratings (0-4) | 100% (2,937) | Human-rated + backfilled |
| FEC political donations | 100% (2,937) — 325 verified donors | OpenFEC API + GPT verification |
| Real estate data | 46% (1,358) — 690 with Zestimates | Skip-trace + Zillow pipeline |
| Structured institutional overlap | 66% (1,949) | GPT-5 mini with career timeline |
| Ask-readiness scoring | 100% (2,937) | GPT-5 mini donor psychology model |
| Email addresses | ~60% | Various sources + email discovery |
| LinkedIn posts | 76 posts (Justin's only) | Apify post scraper |
| Legacy Perplexity scoring | 53% (1,315) | Deprecated — replaced by AI tags |

### Key Observations

1. **All contacts are fully scored.** Every contact has LLM tags, embeddings, FEC data (verified or confirmed zero), and ask-readiness scores. Real estate covers 46% — limited by skip-trace success rates for US contacts.

2. **Rich JSONB data is already stored.** Each contact has `enrich_employment`, `enrich_education`, `enrich_skills_detailed`, `enrich_volunteering`, `enrich_certifications`, `enrich_publications` as JSONB arrays with company names, titles, dates, descriptions, school names, fields of study.

3. **pgvector 0.8.0 is installed.** The Camelback table already uses 1536-dimension embeddings with HNSW indexing — proven pattern.

4. **Connected_on dates** provide a temporal signal: people Justin connected with 10 years ago in 2015 are likely closer than someone from 2024.

5. **Justin's full profile is now scraped** — 12 positions, 3 schools, 2 board/volunteer roles, 76 posts, 6,061 followers.

6. **GPT verification catches bad data.** FEC: 292 wrong-person matches rejected. Real estate: skip-trace validation rejects wrong-state/wrong-employer results. Zillow: zpid-based matching prevents data misassignment.

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

**Our differentiation:** We combine relationship proximity (like Affinity), giving capacity estimation (like iWave), topical affinity (like semantic search tools), and communication history (like Introhive) in a single personal system for ~$33 total processing cost instead of $10K+/year in SaaS subscriptions. Unlike earlier versions, wealth estimates now incorporate **real estate data** (1,358 contacts enriched, 690 with Zestimates, ownership classified) and **FEC political donation records** (325 GPT-verified donors totaling $5.38M) alongside LinkedIn career proxy signals. All 2,937 contacts are scored with an AI donor-psychology ask-readiness model.

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

### Phase 3: Communication History
**Status:** Superseded by Phase 5 (originally planned as Phase 3, implemented as Phase 5 with expanded scope).

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

### Phase 5: Communication History — COMPLETE
**Status:** Done (2026-02-20)
**Scripts:**
- `scripts/intelligence/gather_comms_history.py` — Gmail collection + LLM summarization
- `scripts/intelligence/discover_emails.py` — Email discovery for contacts without email addresses

**Approach:** Python scripts using Gmail API directly via OAuth credentials (stored at `~/.google_workspace_mcp/credentials/`) across 5 Google Workspace accounts. Two-phase pipeline: Phase A collects raw Gmail thread data, Phase B summarizes with GPT-5 mini.

**5 Google Workspace Accounts Searched:**
| Account | Email |
|---------|-------|
| Primary | justinrsteele@gmail.com |
| True Steele | justin@truesteele.com |
| Outdoorithm | justin@outdoorithm.com |
| Outdoorithm Collective | justin@outdoorithmcollective.org |
| Kindora | justin@kindora.co |

**Results:**
- **628 contacts** with email thread history (out of ~1,900 with email addresses)
- **9,425 email threads** stored with full raw message data (headers, body text, dates, participants)
- **628 LLM-generated summaries** with per-thread summaries and relationship overviews
- **73 email addresses discovered** for contacts that had no email (via name-based Gmail search + LLM verification)
- **0 errors** across all runs
- **Total LLM cost:** ~$1.35 (GPT-5 mini structured output)

**Database:**
- New table: `contact_email_threads` — raw thread data with `UNIQUE(contact_id, thread_id, account_email)`
- Existing column: `contacts.communication_history` JSONB — aggregate summaries per contact
- Existing column: `contacts.comms_last_gathered_at` — timestamp of last collection

**Email Discovery:**
- Searched Gmail by name for 579 contacts without email addresses
- Multi-signal scoring: display name match, company domain match, thread count, multi-account appearance
- LLM verification (GPT-5 mini) with confidence threshold of 80%
- Rules: distinctive names accepted with name match; company domain emails rejected if not current employer; common names require domain match or strong contextual evidence

**CLI:**
```bash
# Collect Gmail threads
python scripts/intelligence/gather_comms_history.py --collect-only
python scripts/intelligence/gather_comms_history.py --min-proximity 40  # Warm+ only
python scripts/intelligence/gather_comms_history.py --ids-file ids.json  # Specific contacts

# Summarize with GPT-5 mini
python scripts/intelligence/gather_comms_history.py --summarize-only

# Discover emails
python scripts/intelligence/discover_emails.py --test --dry-run
python scripts/intelligence/discover_emails.py  # Full run
```

---

## 14. Phase 6: Donor Psychology Overhaul — COMPLETE

**Status:** All 17 user stories implemented. All enrichment scripts run against full database. All 2,937 contacts fully scored.
**Plan file:** `/Users/Justin/.claude/plans/cozy-munching-dongarra.md`
**Ralph loop:** `.ralph/network-intel-overhaul/`

### 14.1 Motivation

The existing system has two key gaps:
1. **Justin's human signals are underused.** 1,499 contacts have familiarity ratings (0-4), 628 have communication history — but the UI still sorts by AI proximity score (GPT's guess) instead of Justin's actual assessment.
2. **No wealth data beyond LinkedIn proxy.** Capacity scoring relies entirely on job titles and career trajectory. Two free/cheap public data sources — FEC political donations and real estate records — can provide behavioral proof of wealth.

The overhaul rewires everything so Justin's human signals (familiarity, comms) are primary, AI signals supplement, and a donor psychology reasoning model assesses ask-readiness.

### 14.2 New Database Columns

```sql
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS shared_institutions JSONB DEFAULT NULL;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS comms_last_date DATE DEFAULT NULL;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS comms_thread_count SMALLINT DEFAULT 0;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS fec_donations JSONB DEFAULT NULL;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS real_estate_data JSONB DEFAULT NULL;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS ask_readiness JSONB DEFAULT NULL;
```

### 14.3 FEC Political Donation Enrichment (FREE) — COMPLETE

Federal campaign contributions are public record via the **OpenFEC API** (free, rate limit 1,000 req/hr). Anyone who donates $200+ to a political campaign is searchable by name. This is the strongest free wealth indicator:

- Someone giving $2,800/candidate (max individual contribution) has significant disposable income
- Aggregate patterns reveal both capacity and philanthropic propensity
- FEC data includes employer and occupation, providing cross-validation

**API tested and validated (2026-02-20):**
- Endpoint: `GET https://api.open.fec.gov/v1/schedules/schedule_a/`
- Params: `contributor_name`, `contributor_state`, `is_individual=true`, `two_year_transaction_period`
- Successfully returned data for known donors (Reid Hoffman: 1,906 records)
- State filtering effectively reduces false positives for common names
- GPT-5 mini verification handles disambiguation excellently (see 14.6)

**Full run results (2,937 contacts):**

| Metric | Result |
|--------|--------|
| Contacts processed | 2,937 |
| GPT-verified donors | 325 (11%) |
| GPT-rejected (wrong person) | 292 |
| No FEC records | ~2,320 |
| Total verified donations | $5.38M across 325 donors |
| Average per verified donor | $16,549 |
| Cost | $0 (FEC API) + ~$2 (GPT verification) |

**Bug fix applied (2026-02-22):** Original script used loose prefix name matching (`fec_first.startswith(first_lower)`) which caused "Andrea" to match "Andre", "Christopher" to match "Chris", etc. — producing 308 contacts with >50 donations each (clearly aggregating multiple people). Fixed with:

1. **Exact first name matching only** — no more prefix matching
2. **GPT-5 mini verification** on every match — verifies employer/location/plausibility against LinkedIn profile
3. **State extraction from employment** — extracts US state from `enrich_employment` JSONB when `state` field is null, reducing false positives

After fix and re-run: 51 contacts with >50 donations remain — all are legitimate high-frequency donors (e.g., Donnel Baird/BlocPower 525 donations, Michelle Boyers/Give Forward Foundation $1.4M, Regan Pritzker $1.84M). See [Section 14.15](#1415-fec-multi-person-aggregation-bug-fix-2026-02-22) for details.

**JSONB schema:**
```json
{
  "total_amount": 15400,
  "donation_count": 8,
  "max_single": 2800,
  "cycles": ["2024", "2022", "2020"],
  "recent_donations": [
    {"committee": "ActBlue", "amount": 2800, "date": "2024-03-15"}
  ],
  "employer_from_fec": "Google LLC",
  "occupation_from_fec": "Software Engineer",
  "verification": {
    "is_match": true,
    "confidence": "high",
    "reasoning": "FEC employer matches LinkedIn profile..."
  },
  "last_checked": "2026-02-22"
}
```

**Cost:** $0 (free API) + ~$2 GPT verification. ~3 hours for 2,937 contacts at 1,000 req/hr.

### 14.4 Real Estate Enrichment — Three-Step Pipeline (VALIDATED)

Property ownership is one of the strongest wealth indicators. Achieved via a validated three-step pipeline that costs **~$0.01/contact**.

#### API Research & Testing Summary (2026-02-20 through 2026-02-21)

**Services REJECTED after testing:**
- **BatchData** — Reverse owner name search requires $500/mo tier. `searchCriteria.ownerName` returns garbage data. `owner-profile` endpoint returns 403. ~$49.40 credit remains for address-based lookups only.
- **Melissa Personator Consumer** — Goes address→person, NOT name→address. Research agents got this wrong. GitHub examples confirm input is address components.
- **EnformionGO** — Signup blocked ("unable to allow you to sign-up for an account right now").
- **Open People Search** — Discontinued. Dev docs site (dev.openpeoplesearch.com) returns DNS error.
- **Trestle (TrestleIQ)** — No "Find Person by name" endpoint. Only offers Reverse Phone, Reverse Address, Caller ID. All go wrong direction.
- **Apify Zillow scrapers (4 tested):** `aknahin/zillow-property-info-scraper` (ImportError), `burbn/zillow-address-scraper` (returns random listings), `jupri/zillow-scraper` (requires paid rental), `maxcopell/zillow-scraper` (needs searchQueryState URL).

#### Validated Pipeline (tested 2026-02-21)

**Step 1: Name → Home Address — Apify Skip Trace ($0.007/result)**

Actor: `one-api/skip-trace` on Apify marketplace (1.5M+ runs, 3,600+ users, 3.5/5 rating)

Scrapes TruePeopleSearch, FastPeopleSearch, Spokeo, BeenVerified, and PeopleFinders. Returns current address, previous addresses, phone numbers, emails, relatives, age/DOB.

```python
# Input format (array of "Name; City, ST" strings)
body = {"name": ["Adrian Schurr; San Francisco, CA"]}

# Output fields
{
  "First Name": "Adrian", "Last Name": "Schurr",
  "Street Address": "1873 Wayne Ave",
  "Address Locality": "San Leandro", "Address Region": "CA", "Postal Code": "94577",
  "Age": "36", "Born": "November 1989",
  "Email-1": "adrianschurr@yahoo.com",
  "Phone-1": "(650) 875-4352", "Phone-1 Type": "Landline",
  "Previous Addresses": [...], "Relatives": [...], "Associates": [...]
}
```

**Step 2: Address → Zillow ZPID — Zillow Autocomplete API (FREE)**

Undocumented but stable Zillow autocomplete endpoint. No API key needed.

```python
url = "https://www.zillowstatic.com/autocomplete/v3/suggestions"
params = {"q": "1873 Wayne Ave, San Leandro, CA 94577", "resultTypes": "allAddress", "resultCount": 3}
# Returns: {"results": [{"metaData": {"zpid": "24882391"}, "display": "1873 Wayne Ave San Leandro, CA 94577"}]}
```

**Step 3: ZPID → Property Data — Apify `maxcopell/zillow-detail-scraper` (~$0.003/result)**

Takes Zillow detail URLs, returns full property data including Zestimate.

```python
body = {"startUrls": [{"url": "https://www.zillow.com/homedetails/1873-Wayne-Ave-San-Leandro-CA-94577/24882391_zpid/"}]}
# Returns: zestimate, rentZestimate, bedrooms, bathrooms, livingArea, yearBuilt, homeType, propertyTaxRate
```

#### Scaled Test Results (2026-02-21, 15 contacts)

**Script:** `scripts/intelligence/test_real_estate_pipeline.py`

| Metric | Result |
|--------|--------|
| Addresses found (skip-trace) | 13/15 (87%) |
| GPT-5 mini validated as correct person | 9/13 (69%) |
| Zillow ZPIDs found | 9/9 (100%) |
| Zestimates obtained | 7/9 (78%) |
| **End-to-end success rate** | **7/15 (47%)** |
| Total cost | $0.16 |

**Sample results:**
| Contact | Address | Zestimate | Validation |
|---------|---------|-----------|------------|
| Adrian Schurr (SF) | 1873 Wayne Ave, San Leandro, CA | $838,600 | ✅ high |
| Taj James (Oakland) | 4347 Leach Ave #3, Oakland, CA | $686,200 | ✅ high |
| Rob Gitin (SF) | 177 Granada Ave, San Francisco, CA | — | ✅ high |
| Freada Kapor Klein (Oakland) | 222 Broadway #1504, Oakland, CA | — | ✅ high |
| Jeff Kositsky (Denver) | 749 S Grant St, Denver, CO | $1,057,100 | ✅ medium |
| Trina Villanueva (Oakland) | 4629 Mountain Blvd, Oakland, CA | $1,572,300 | ✅ medium |

**Correct rejections (validation working):**
- Gina Clayton-Johnson: Skip-trace returned 68yo in Tennessee (contact is in LA, much younger)
- Kamau Bobb: Different first name returned (Damu, not Kamau), wrong state
- Neela Pal: Different first name (Nilanjana), wrong state (MA not NY)
- Jake Edwards: Age implausible for career stage, common name

#### Cost Summary

| Step | Service | Cost/contact | For 600 contacts |
|------|---------|-------------|-----------------|
| Name → Address | Apify `one-api/skip-trace` | $0.007 | $4.20 |
| Address → ZPID | Zillow autocomplete | FREE | $0 |
| ZPID → Zestimate | Apify `maxcopell/zillow-detail-scraper` | ~$0.003 | $1.80 |
| **Total** | | **~$0.01** | **~$6.00** |

**Scope:** Top contacts — familiarity >= 2 OR capacity tier = major_donor (~500-700 contacts).

#### Address Validation (GPT-5 mini)

Each skip-trace result is verified against the contact's known profile data (city, state, employer, LinkedIn data) using GPT-5 mini to confirm the address belongs to the right person — critical for common names. See section 14.6 for verification methodology.

**JSONB schema:**
```json
{
  "address": "123 Main St, Palo Alto, CA 94301",
  "zestimate": 2100000,
  "rent_zestimate": 7500,
  "beds": 4,
  "baths": 3,
  "sqft": 2400,
  "year_built": 1965,
  "property_type": "SINGLE_FAMILY",
  "ownership_likelihood": "likely_owner",
  "confidence": "high",
  "source": "zillow_via_skip_trace",
  "last_checked": "2026-02-21"
}
```

See [Section 14.13](#1413-ownership-likelihood-classification) for `ownership_likelihood` classification logic.

### 14.5 Structured Institutional Overlap (GPT-5 mini)

For ~1,200 contacts with shared institutions, run GPT-5 mini with Justin's exact career timeline to produce structured overlap data replacing freetext in `ai_tags`.

**Output JSONB:**
```json
[{
  "name": "Google / Google.org",
  "type": "employer",
  "overlap": "confirmed",
  "justin_period": "2014-2019",
  "contact_period": "2016-2020",
  "temporal_overlap": true,
  "depth": "same_org",
  "notes": "Both in social impact roles, 3 years overlap"
}]
```

**Cost:** ~$2.40

### 14.6 GPT-5 Mini Match Verification

All enrichment scripts use GPT-5 mini to verify API matches against contact profiles. Tested and validated (2026-02-20):

**Key findings from testing:**
- Correctly matched unique names (Olatunde Sobomehin → StreetCode Academy FEC records)
- Correctly rejected ALL 11 false positives for common name (Manuel Lopez — 60 FEC results in NY)
- Correctly matched despite city mismatch (Gina Clayton-Johnson in Altadena vs LA metro area)
- Uses employer, occupation, city/state, and career context for disambiguation

**Important:** GPT-5 mini does NOT support `temperature=0`. Use default temperature (1) only.

**Cost:** ~$0.002/contact for verification pass.

### 14.7 AI Ask-Readiness Scoring (Donor Psychology)

Instead of hardcoded composite scoring, uses a strong AI reasoning model with a deep donor psychology prompt to holistically assess each contact's ask-readiness for a given goal. The prompt encodes a comprehensive donor psychology framework that the model applies to each contact's full data profile.

**Donor Psychology Framework — Four Pillars:**

**1. Relationship Depth (most important for individual fundraising)**

The #1 predictor of individual giving is trust in the person asking. Warm outreach converts at 10x the rate of cold approaches. Assessed via:
- **Familiarity rating** (0-4): Justin's personal assessment of how well he knows them
- **Communication recency/frequency**: Recent email contact signals active relationship vs dormant connection
- **Shared formative experiences**: People who worked together, went to school together, or served on boards together share identity-level bonds. Temporal overlap amplifies this — being at Google at the SAME TIME creates a fundamentally different bond than both having worked there in different decades
- **Reciprocity history**: Prior favors, shared projects, mutual support create giving obligations

**2. Giving Capacity**

Financial ability to give, assessed from:
- Career level and trajectory (C-suite, VP, director, IC)
- Company size and type (tech exec vs nonprofit staff)
- Board positions (signal wealth and philanthropic identity)
- **FEC political donations**: If someone donated $5,000+ to political campaigns, they demonstrably have disposable income AND willingness to write checks. This is the strongest behavioral signal of capacity — it's not estimated, it's proven.
- **Real estate holdings**: Property ownership is a factual wealth indicator. Someone with $2M+ in assessed property value has fundamentally different capacity than a renter.
- Capacity WITHOUT relationship is meaningless for individual asks — a billionaire who doesn't know Justin won't give

**3. Philanthropic Propensity**

Likelihood of giving based on values and identity alignment:
- **Philanthropic identity**: Board service, volunteer history, nonprofit work
- **Values alignment**: Do they post/talk about causes, equity, giving back?
- **Cause alignment**: Specific alignment with outdoor equity, youth access, environmental justice
- **Identity-based giving**: "People like me give to causes like this" — shared social circles, similar career arcs, peer effects
- **Prior support**: Have they supported similar organizations?

**4. Psychological Readiness**

Timing and receptivity:
- **Life stage**: New role = less capacity but possibly more openness; recently retired = more time and philanthropic interest
- **Communication warmth**: Was the last exchange positive, collaborative, friendly?
- **Cultivation state**: Has Justin already cultivated this relationship, or would the ask come out of nowhere?
- **Authenticity**: Would this person feel the ask is genuine from Justin, or would it feel transactional?
- **Warm glow factor**: Will giving to this cause make them feel good about themselves?

**Critical Behavioral Insights (encoded in prompt):**
- **Insider effect**: Donors who feel like insiders give more. Shared institutional membership creates insider feeling.
- **Identifiable victim effect**: Donors respond to individual stories, not statistics. Contacts who've experienced the outdoors (or have kids) are more likely to empathize.
- **Social proof**: Contacts who know OTHER supporters in Justin's network are more likely to give. Peer clusters matter.
- **Loss aversion**: Framing matters. "Don't miss being part of this founding group" > "Please donate."
- **Second-gift psychology**: If someone has already given to Outdoorithm or supported Justin's ventures, they're 2-3x more likely to give again.
- **Monthly giving**: Converts best within 30-90 days of first gift or engagement.
- **Cultivation timelines**: Major donors need 12-18 months of cultivation before a large ask. Mid-level donors need 2-4 touchpoints.

**Scoring Tiers:**
- 80-100 (`ready_now`): Close relationship + capacity + alignment + recent positive contact. Justin could call today.
- 60-79 (`cultivate_first`): Good relationship foundation but needs a touchpoint before asking. Reconnect first, share the mission, then ask.
- 40-59 (`long_term`): Has capacity and some alignment, but relationship too thin for direct ask. Needs multiple cultivation touchpoints.
- 20-39 (`long_term`): Distant connection or misaligned values. Only worth pursuing if capacity is very high.
- 0-19 (`not_a_fit`): No relationship, no alignment, or no capacity. Don't waste effort.

**Realistic expectations**: Most LinkedIn connections are NOT ready for a fundraising ask. A 2,400-person network might yield 50-100 people who are genuinely ready, 200-300 worth cultivating, and the rest are too distant.

**Per-contact context sent to the model:**

Each contact is evaluated with their full data profile:
- Familiarity rating (Justin's personal 0-4 assessment)
- Current role, company, headline, location
- Shared institutions (structured overlap from Phase 2c)
- AI capacity tier and score, AI Outdoorithm fit
- FEC political donations summary (if any)
- Real estate holdings summary (if any)
- Topics of interest, philanthropic signals
- Communication history: last contact date, thread count, relationship summary, recent thread subjects
- LinkedIn connection date

**Output schema per contact:**
```json
{
  "score": 82,
  "tier": "ready_now",
  "reasoning": "2-3 sentence explanation citing specific evidence",
  "recommended_approach": "personal_email | phone_call | in_person | linkedin | intro_via_mutual",
  "ask_timing": "now | after_cultivation | after_reconnection | not_recommended",
  "cultivation_needed": "None — ready for direct ask | description of cultivation needed",
  "suggested_ask_range": "$X-$Y | volunteer/attend first",
  "personalization_angle": "Single strongest personalization hook for this person and goal",
  "risk_factors": ["reasons this ask could backfire or damage the relationship"]
}
```

**JSONB schema (stored in `ask_readiness`):**
```json
{
  "outdoorithm_fundraising": {
    "score": 82,
    "tier": "ready_now",
    "reasoning": "Close relationship (4/4), shared Google.org tenure...",
    "recommended_approach": "personal_email",
    "ask_timing": "now",
    "cultivation_needed": "None — ready for direct ask",
    "suggested_ask_range": "$500-$2,000",
    "personalization_angle": "Your shared Google.org work on equity...",
    "risk_factors": [],
    "scored_at": "2026-02-21T..."
  }
}
```

Can be re-run for multiple goals (kindora_sales, etc.) — results stack in same JSONB. Goal is parameterized in the script via `--goal` flag.

**Cost:** ~$7.20 for 2,400 contacts (GPT-5 mini structured output, ~$0.003/contact)

### 14.8 Search System Overhaul

The AI Filter Co-pilot (Phase 4) is rewired:
- **Primary signal:** `familiarity_rating` (Justin's human assessment) replaces `ai_proximity_score` (GPT's guess)
- **New filters:** `familiarity_min`, `has_comms`, `comms_since`, `shared_institution`, `goal`
- **New sort options:** familiarity, comms_recency, ask_readiness
- **New tool:** `goal_search` — finds contacts ranked by ask-readiness for a specific goal
- **Default sort:** `familiarity_rating DESC, comms_last_date DESC NULLS LAST`

### 14.9 UI Updates

- Contacts table: Replace "Proximity" with "Familiarity" (0-4 visual), add "Last Contact" column, add "Ask Readiness" column when goal filter active
- Contact detail: Add "Your Relationship" section (familiarity + comms), "Institutional Overlap" with temporal badges, "Ask Readiness" card with tier/reasoning/approach
- Filter bar: New chips for familiarity, comms, goal

### 14.10 Implementation Status

All 17 user stories complete (`.ralph/network-intel-overhaul/prd.md`):

| Story | Description | Status |
|-------|-------------|--------|
| US-001 | Documentation update | Done |
| US-002 | Database migration (new columns + indexes) | Done |
| US-003 | Backfill comms fields (628 contacts) | Done |
| US-004 | FEC enrichment script | Done — 2,937 contacts, 325 verified donors |
| US-005 | Real estate enrichment script (three-step) | Done — 1,358 contacts, 690 with Zestimates |
| US-006 | Structured overlap scoring | Done — 1,949 contacts with shared institutions |
| US-007 | Ask-readiness scoring (donor psychology) | Done — 2,937 contacts scored |
| US-008 | Update FilterState + types | Done |
| US-009 | Update search route + select cols | Done |
| US-010 | Add goal_search tool | Done |
| US-011 | Update agent system prompt | Done |
| US-012 | Update parse-filters | Done |
| US-013 | Update contact detail + outreach context | Done |
| US-014 | Update contacts table UI | Done |
| US-015 | Update contact detail sheet UI | Done |
| US-016 | Update filter bar UI | Done |
| US-017 | Tag remaining 527 contacts | Done — all 2,937 tagged and embedded |

**Production audit (2026-02-21):** 4 issues fixed — timezone bug in date display, PostgREST input sanitization in agent tool, CSV exports updated with new columns (familiarity/comms/ask-readiness replacing legacy proximity), Array.isArray guard on risk_factors rendering.

**Data quality fixes (2026-02-22):** Zillow batch zpid matching bug (property data assigned to wrong contacts) — fixed and all 794 properties re-scraped. FEC multi-person aggregation bug (prefix name matching) — fixed with exact matching + GPT verification and full re-run.

### 14.11 Data Enrichment Coverage — ALL COMPLETE

All enrichment pipelines have been run against the full database. Current state:

| Data | Coverage | Status |
|------|----------|--------|
| AI tags (LLM structured) | 2,937 / 2,937 (100%) | Complete |
| Profile embeddings | 2,937 / 2,937 (100%) | Complete |
| Interests embeddings | 2,933 / 2,937 (99.9%) | Complete (4 contacts with zero profile data) |
| Communication history | 628 contacts | Complete |
| Familiarity ratings | 2,937 / 2,937 (100%) | Complete (human-rated + backfilled) |
| FEC donations | 2,937 / 2,937 (100%) | Complete — 325 verified donors, 292 GPT-rejected |
| Real estate | 1,358 / 2,937 (46%) | Complete — 690 with Zestimates, 795 re-scraped |
| Structured overlap | 1,949 / 2,937 (66%) | Complete — contacts with shared institutions |
| Ask-readiness scoring | 2,937 / 2,937 (100%) | Complete — 87 ready_now, 2,118 cultivate_first |

**Ask-readiness score distribution (outdoorithm_fundraising goal):**

| Tier | Count | % |
|------|-------|---|
| ready_now (80-100) | 87 | 3% |
| cultivate_first (60-79) | 2,118 | 72% |
| long_term (40-59) | 657 | 22% |
| not_a_fit (0-39) | 75 | 3% |
| **Average score** | **60.8** | |

**Re-run commands (for future updates):**
```bash
python scripts/intelligence/tag_contacts_gpt5m.py          # LLM tagging
python scripts/intelligence/generate_embeddings.py          # Vector embeddings
python scripts/intelligence/enrich_fec_donations.py         # FEC donations
python scripts/intelligence/enrich_real_estate.py           # Real estate (Apify skip-trace)
python scripts/intelligence/enrich_real_estate.py --source 411 --retry-rejected  # 411.com retry
python scripts/intelligence/rescrape_zillow.py              # Re-scrape Zillow details (zpid-matched)
python scripts/intelligence/score_overlap.py                # Structured overlap
python scripts/intelligence/score_ask_readiness.py --goal outdoorithm_fundraising  # Ask-readiness
```

All scripts support `--test` (1 contact), `--batch N`, and `--start-from` flags for incremental runs.

---

## 15. Cost Estimates (All Phases — Actuals)

| Component | Cost | Notes |
|-----------|------|-------|
| GPT-5 mini tagging (2,937 contacts) | ~$7 | Structured output, Phase 1 (run in batches) |
| Embeddings (5,870 calls) | ~$0.04 | text-embedding-3-small, Phase 2 |
| Gmail thread summarization (628 contacts) | ~$1.30 | GPT-5 mini structured output |
| Email discovery (579 contacts) | ~$0.05 | GPT-5 mini verification |
| **Total Phases 1-5** | **~$8.40** | |
| FEC political donations (2,937 contacts) | ~$2 | Free OpenFEC API + $2 GPT verification |
| Real estate — Apify batch Run 1 (551 contacts) | $5.31 | Apify skip-trace + Zillow detail |
| Real estate — 411.com retry Run 2 (100 contacts) | ~$0.25 | curl_cffi (free) + GPT + Zillow detail |
| Real estate — 411.com full retry Run 3 (793 contacts) | ~$3.00 | GPT prep + 411.com (free) + GPT + Zillow detail |
| Real estate — Zillow re-scrape (794 contacts) | $2.38 | zpid-matched re-scrape after bug fix |
| Structured overlap (1,949 contacts) | ~$3.00 | GPT-5 mini |
| Ask-readiness scoring (2,937 contacts) | ~$8.50 | GPT-5 mini donor psychology (multiple runs) |
| **Total Phase 6** | **~$24.50** | |
| **Grand Total (all phases)** | **~$33** | |

The entire 6-phase pipeline costs less than a month of any commercial wealth screening tool.

#### Batch Run Results

**Script:** `scripts/intelligence/enrich_real_estate.py`

After auditing all Zillow detail scrapers on Apify, we switched from `happitap/zillow-detail-scraper` (12 users, 80 total runs) to `maxcopell/zillow-detail-scraper` (4,074 users, 1.97M runs, 383 monthly active users, 4.7/5 rating from 14 reviews). Same price ($0.003), same input/output format, vastly more battle-tested.

| Metric | happitap (old) | maxcopell (new) |
|--------|---------------|-----------------|
| Validated → ZPID found | 75% | 86% |
| ZPID → Zestimate found | 64% | 85% |
| End-to-end success | 24% | 28% |

##### Run 1: Apify Skip-Trace (2026-02-21, 551 contacts)

| Metric | Result |
|--------|--------|
| Contacts processed | 551 |
| GPT-5 mini validated | 211 (38%) |
| Zestimates obtained | 153 (28% end-to-end) |
| Errors | 0 |
| Total cost | $5.31 |
| Runtime | 15 min |

##### Run 2: 411.com Retry-Rejected (2026-02-21, 100 contacts)

After building the 411.com custom scraper (see [14.12](#1412-custom-multi-result-people-search-scraper--implemented-2026-02-21)), re-processed contacts that Apify's single-result skip-trace had failed on.

| Metric | Result |
|--------|--------|
| Contacts re-processed | 100 (from 340 rejected/no-result) |
| Skipped (non-US/no city) | 15 |
| GPT-5 mini validated | 18/85 searchable (21%) |
| Zestimates obtained | 16 |
| Recovery rate (previously impossible contacts) | 43% of searchable |
| Total cost | ~$0.25 (GPT validation only + Zillow detail) |

These 18 contacts had ALL been rejected by the Apify skip-trace — the multi-candidate approach recovered them.

##### Run 3: 411.com Full Retry with GPT Prep (2026-02-22, 793 contacts) — COMPLETE

Re-processes ALL previously rejected and no-result contacts through the 411.com pipeline with two major improvements:

**1. GPT-5 mini Search Param Preparation**

Instead of regex/keyword cleaning, each contact's full profile is sent to GPT-5 mini to extract clean search parameters:
- **Name cleaning:** Strips credentials (PhD, MBA, CFRE, Ed.D., MPA, CSSGB), pronouns (she/her/ella), removes accents (Jesús→Jesus)
- **Location extraction:** When profile city/state is empty, reads employment JSONB to find US locations (e.g., Jesús Gerena had no city/state but employment showed "Salt Lake City, UT")
- **Non-US filtering:** Correctly identifies and skips non-US contacts (Dan Walker in Vancouver, Annie Lewin in Auckland, Barry Newstead in Melbourne)
- **Searchability assessment:** Returns `is_searchable: false` with `skip_reason` for contacts that can't be searched

```python
def prepare_search_params(contact: dict, openai_client: OpenAI) -> dict:
    """Use GPT-5 mini to extract clean name and US location for 411.com search."""
    # Sends: name fields, city/state, company, position, headline, employment locations, education
    # Returns: {first_name, last_name, city, state, is_searchable, skip_reason}
```

**2. Concurrent Architecture**

Restructured from sequential (17 sec/contact) to fully concurrent:
- **GPT prep:** 50 concurrent workers (`N_GPT_WORKERS = 50`) — processes all contacts in parallel
- **411 search + validation:** 5 concurrent workers (`N_411_WORKERS = 5`) — each creates own `Scraper411` instance with own `curl_cffi` session/TLS fingerprint for thread safety
- **Result:** 6.7 sec/contact (3x faster than sequential)

```
Step 0: GPT-5 mini prep (all contacts, 50 concurrent) → clean params
Step 1: 411.com search (5 concurrent workers, each with own session)
Step 2: GPT-5 mini validation (inline per worker)
Step 3: Zillow autocomplete + detail scraper
```

**Progress at 100/691:**

| Metric | Result |
|--------|--------|
| Contacts in scope | 793 (all rejected + no_result) |
| GPT-prepped & searchable | ~85% (non-US and no-location contacts skipped) |
| Validated (at 100 processed) | 61/100 (61%) |
| Zestimates (at 100 processed) | 45/61 (74% of validated) |
| Errors | 0 |
| Speed | 6.7 sec/contact (670s for 100) |
| Estimated total time | ~80 min |
| Cost | ~$2 GPT + free 411.com + ~$1 Zillow detail |

##### Zillow Re-scrape (2026-02-22) — Critical Bug Fix

A systemic batch data bug was discovered: Apify's `maxcopell/zillow-detail-scraper` returns results in arbitrary order, but the code matched results by **array index** instead of **zpid**. This caused property data to be assigned to the wrong contacts across hundreds of records. See [Section 14.14](#1414-zillow-batch-data-bug--re-scrape-2026-02-22) for details.

**Fix:** Changed both Zillow result consumption paths in `enrich_real_estate.py` to build a `zr_by_zpid` lookup dict and match by zpid. Built `rescrape_zillow.py` to re-scrape all existing addresses.

| Metric | Result |
|--------|--------|
| Contacts with addresses | 1,059 |
| ZPIDs found | 794 |
| Successfully re-scraped | 794 (100%) |
| Errors | 0 |
| Cost | $2.38 (Apify) |
| Time | 23 min |

##### Cumulative Real Estate Coverage (as of 2026-02-22, COMPLETE)

| Category | Count | Notes |
|----------|-------|-------|
| Total contacts with `real_estate_data` | 1,358 | Includes all sources |
| With Zestimate | 690 | |
| Zillow re-scraped (zpid-matched) | 795 | Correct data via zpid matching |
| Ownership: likely_owner (SFH) | 598 | |
| Ownership: likely_owner_condo | 86 | |
| Ownership: likely_renter | 109 | |
| Ownership: uncertain | 92 | |
| Skip-trace failed/rejected | 414 | No valid address found |
| Skip-trace only (no Zillow data) | 149 | Address found but no zpid/Zestimate |

#### Skip Trace Audit (2026-02-21)

All Apify skip trace / people search actors were audited:

| Actor | Users | Total Runs | Monthly Users | Price | Rating |
|-------|-------|-----------|---------------|-------|--------|
| **one-api/skip-trace** (ours) | 3,635 | 1.6M | 1,297 | $0.007 | 3.52/5 (21 reviews) |
| twoapi/skip-trace | 3 | 24 | 2 | $0.01 | N/A |
| wisteria_banjo/skip-tracer | — | — | — | — | DEPRECATED |
| DealMachine | 37 | — | — | $49.99/mo | 1/5 |

**Conclusion:** `one-api/skip-trace` is the only viable option by a wide margin.

### 14.12 Custom Multi-Result People Search Scraper — IMPLEMENTED (2026-02-21)

> **Full design doc:** `docs/CUSTOM_PEOPLE_SCRAPER.md`

#### Summary

Replaced `one-api/skip-trace` (Apify, $0.007/result, 1 result only) with a **free 411.com scraper** returning **3-10 candidates per name** with full addresses, phones, ages, and relatives. GPT-5 mini then picks the best match from all candidates simultaneously.

**Key breakthrough:** 411.com (Whitepages) has **no Cloudflare protection** — simple HTTP requests with `curl_cffi` Chrome TLS impersonation work perfectly. No browser automation needed. TruePeopleSearch, FastPeopleSearch, and Nuwber all have heavy Cloudflare Turnstile that defeated Camoufox, nodriver, cloudscraper, and Playwright.

#### Results

| Metric | Apify (old) | 411.com (new) |
|--------|-------------|---------------|
| Cost per search | $0.007 | $0.000 (FREE) |
| Candidates per name | 1 | 3-10 |
| Known contacts test (5) | N/A | 3/5 exact address, 5/5 correct person |
| Retry-rejected batch (100) | 0% (all rejected) | 21% validated, 43% of searchable |

**Key technique improvements over Apify:**
- **Multi-candidate comparison**: GPT-5 mini evaluates ALL candidates simultaneously, not just threshold-checking one result
- **Relative/age signals**: 411.com provides age brackets and relative names — strong disambiguation signals
- **GPT-5 mini search prep** (added Run 3): LLM-based name cleaning and location extraction replaces regex. Handles credentials (PhD, CFRE, Ed.D., MPA), pronouns (she/her/ella), accents (Jesús→Jesus), and extracts US city/state from employment JSONB when profile fields are empty
- **Non-US filtering**: GPT correctly identifies and skips non-US contacts (Vancouver, Auckland, Melbourne, Nairobi) — saves unnecessary 411 searches
- **State normalization**: Converts full state names ("California") to 2-letter abbreviations for URL construction
- **403 retry**: Fresh curl_cffi session + 5-10s delay on HTTP 403 responses
- **Concurrent execution**: 5 parallel 411.com workers (each with own session for thread safety) + 50 concurrent GPT workers = 6.7 sec/contact vs 17 sec sequential

#### Architecture

```
Step 0: GPT-5 mini prep — clean names, extract US locations, filter non-searchable
Step 1: 411.com search → 3-10 candidates (FREE, curl_cffi + BeautifulSoup)
Step 2: GPT-5 mini multi-candidate validation (picks best or rejects all)
Step 3: Zillow autocomplete (address → ZPID, free)
Step 4: Zillow detail scraper (ZPID → Zestimate, ~$0.003)
```

**Concurrent execution model (for batch runs):**
```
┌─────────────────────────────────────────────┐
│ Step 0: GPT Prep (50 concurrent workers)    │
│ All contacts prepped in parallel            │
│ Output: clean params + searchable/skip list │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ Steps 1-2: 411 Search + Validate            │
│ 5 concurrent workers, each with own         │
│ Scraper411 instance (own curl_cffi session)  │
│ GPT validation runs inline per worker       │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│ Steps 3-4: Zillow ZPID + Detail             │
│ Concurrent for validated addresses          │
└─────────────────────────────────────────────┘
```

#### Usage

```bash
# Full retry of all rejected/no-result (concurrent, GPT prep)
python scripts/intelligence/enrich_real_estate.py --source 411 --retry-rejected

# Resume from a specific offset
python scripts/intelligence/enrich_real_estate.py --source 411 --retry-rejected --start-from 100

# Smaller batch
python scripts/intelligence/enrich_real_estate.py --source 411 --retry-rejected --batch 50

# New contacts
python scripts/intelligence/enrich_real_estate.py --source 411 --batch 50

# Standalone scraper
python scripts/intelligence/people_search_scraper.py search "Adrian Schurr" "San Francisco, CA"
python scripts/intelligence/people_search_scraper.py test  # 5 known contacts
```

#### Key Files

- `scripts/intelligence/people_search_scraper.py` — Core 411.com scraper + GPT-5 mini validation
- `scripts/intelligence/enrich_real_estate.py` — Pipeline with `--source 411` and `--retry-rejected` flags (zpid matching fixed 2026-02-22)
- `scripts/intelligence/rescrape_zillow.py` — Standalone Zillow re-scrape with correct zpid matching
- `docs/CUSTOM_PEOPLE_SCRAPER.md` — Full design document with research findings

### 14.13 Ownership Likelihood Classification

#### Problem

Real estate data without ownership context produces misleading wealth signals. If a contact rents an apartment at a $3M building, the Zestimate reflects the landlord's wealth — not the contact's capacity. We need to distinguish homeowners (Zestimate = valid wealth signal) from renters (Zestimate = irrelevant).

#### Property Ownership API Research (2026-02-21)

Zillow does NOT return owner name data. Researched alternative APIs:

| Service | Price | Owner Name? | Status |
|---------|-------|-------------|--------|
| **Propwire** | Free | Yes | Blocked by DataDome anti-bot (tested, all URL patterns returned 404) |
| **Estated** | Was $179/mo | Yes | Being absorbed into ATTOM Data; 120-property sandbox only |
| **ATTOM** | $179+/mo | Yes | Enterprise pricing, overkill for personal use |
| **RentCast** | 50 free/mo | Yes | Only 50 calls too few for batch processing |
| **County assessor sites** | Free | Yes | No unified API, each county different |
| **Zillow** | Free | No | Returns property data but NOT owner information |

**Conclusion:** No viable free/cheap API exists for property ownership verification at scale. Implemented heuristic classification instead.

#### Heuristic Classification Logic

Uses three signals already available from Zillow data: `property_type`, address format (unit numbers), and Zestimate presence.

```python
def classify_ownership(address, property_type, zestimate):
    has_unit = re.search(r"#|Apt |Unit |Ste |Suite |Floor ", address)
    has_zest = zestimate is not None

    if property_type == "APARTMENT":
        return "likely_renter" if not has_zest else "uncertain"
    if property_type == "SINGLE_FAMILY":
        if not has_unit: return "likely_owner"
        return "likely_owner_condo" if has_zest else "likely_renter"
    if property_type == "CONDO":
        return "likely_owner_condo" if has_zest else "uncertain"
    if property_type in ("TOWNHOUSE", "MULTI_FAMILY", "MANUFACTURED"):
        return "likely_owner"
    # No property_type
    if has_unit and not has_zest: return "likely_renter"
    return "uncertain"
```

#### Classification Results (updated 2026-02-22 after Zillow re-scrape)

| Category | Count | % | Notes |
|----------|-------|---|-------|
| **likely_owner** | 598 | 44% | SFH without unit numbers |
| **likely_owner_condo** | 86 | 6% | Condos/units with Zestimates |
| **uncertain** | 92 | 7% | Ambiguous — need more data |
| **likely_renter** | 109 | 8% | APARTMENTs or unit addresses with no Zestimate |
| **No real estate data** | 1,579 | 54% | Skip-trace failed/rejected or not enriched |
| **With Zestimate** | 690 | 51% of enriched | |

**Key finding:** The classification is defensive — likely renters have no Zestimates, ensuring no bad wealth data is being used in scoring.

#### Integration

- **Database:** `ownership_likelihood` field added to `real_estate_data` JSONB for all 505 contacts
- **Pipeline:** `classify_ownership()` function in `enrich_real_estate.py` auto-classifies on ingest (both Apify and 411.com paths)
- **UI:** Contact detail sheet shows color-coded ownership badge:
  - Green: "Owner" (likely_owner)
  - Blue: "Condo Owner" (likely_owner_condo)
  - Orange: "Renter" (likely_renter)
  - Gray: "Uncertain"
- **Wealth signals:** New "Wealth Signals" section in contact detail sheet shows address, Zestimate, property type, ownership badge, and FEC donation data

#### Final Decision (2026-02-22): Heuristic Is Sufficient

After researching all ownership verification APIs and analyzing the data, the heuristic approach is the right call. Here's why:

| Group | Count | Zestimate? | Risk | Action |
|-------|-------|------------|------|--------|
| **Likely owners** (SFH, no unit#) | 598 | Most yes | None — >90% US SFH are owner-occupied | Trust |
| **Likely condo owners** (unit# + Zestimate) | 86 | 86 yes | Low — Zillow only Zestimates owned units | Trust |
| **Likely renters** | 109 | 0 | None — no Zestimate = no bad wealth data | Safe |
| **Uncertain** | 92 | Some | Low risk — small subset | Manual spot-check if needed |

**The heuristic approach works.** Likely renters have zero Zestimates, so no bad wealth data leaks into scoring. The ROI of a $179/mo ownership API subscription is not justified for the small uncertain subset.

#### Edge Cases

Some contacts are likely misclassified due to Zillow data quirks:
- **Zillow mislabels condos as SINGLE_FAMILY**: Common for multi-unit buildings with individual Zestimates. These get classified as `likely_owner_condo` (correct behavior).
- **High-end neighborhoods mislabeled APARTMENT**: e.g., Sea Cliff (SF), Brickell (Miami). These may actually be owners. The `uncertain` and `likely_renter` categories warrant manual review for high-priority contacts.
- **$36M "SINGLE_FAMILY" with unit number**: Keosha Moon at `99 W Paces Ferry Rd NW #836, Atlanta` — Zillow says SINGLE_FAMILY with $36.5M Zestimate. Classified as `likely_owner_condo` which is reasonable.

### 14.14 Zillow Batch Data Bug & Re-scrape (2026-02-22)

#### The Bug

Apify's `maxcopell/zillow-detail-scraper` returns results in **arbitrary order** — not matching the order of input URLs. The original code in `enrich_real_estate.py` matched results by **array index position**:

```python
# OLD (broken) — matched by index, not zpid
for j, zr in enumerate(zillow_results):
    zpid_item = zpid_items[j]  # WRONG — results are in random order
```

This caused property data to be assigned to the **wrong contacts**. Evidence: contacts in different states with different property types had identical Zestimates. Example: Morgan Hallmon's 4bd/3.5ba single-family home ($1.96M) was showing as a 1bd/1ba condo ($496K) — data from a completely different person's property.

#### The Fix

Changed both Zillow result consumption paths in `enrich_real_estate.py` (skip-trace path ~line 910 and 411 scraper path ~line 1077) to match by zpid:

```python
# NEW (correct) — build lookup dict, match by zpid
zr_by_zpid = {}
for zr in zillow_results:
    zr_zpid = zr.get("zpid")
    if zr_zpid:
        zr_by_zpid[int(zr_zpid)] = zr

for zpid_item in zpid_items:
    target_zpid = int(zpid_item["zpid"])
    zr = zr_by_zpid.get(target_zpid)  # CORRECT — matched by unique zpid
```

#### Re-scrape

Built standalone `scripts/intelligence/rescrape_zillow.py` to re-scrape all contacts with existing `real_estate_data`:

1. Fetches all contacts with addresses from `real_estate_data`
2. Looks up ZPIDs via Zillow autocomplete API (concurrent, 5 workers)
3. Batches zpid→URL to Apify (25 per batch)
4. Matches results by zpid (not index)
5. Updates database with correct property data

| Metric | Result |
|--------|--------|
| Contacts with addresses | 1,059 |
| ZPIDs found | 794 (75%) |
| Successfully updated | 794 (100%) |
| Errors | 0 |
| Cost | $2.38 (Apify) |
| Time | 23 minutes |

**Verified examples of corrected data:**
- Jason Rissman: $1,057,100 → $2,902,500
- Gerald Chertavian: $1,366,500 → $4,820,600
- Freada Kapor Klein: $301,700 → $1,546,900
- Morgan Hallmon: $496,500 (1bd condo) → $1,963,400 (4bd SFH)

**Note on missing ZPIDs (265 contacts):** Some addresses don't resolve via Zillow autocomplete due to city name mismatches (e.g., Zillow uses "El Sobrante" instead of "Richmond" for the same 94803 zip code). These could be recovered with city-name fuzzy matching in the future.

#### Outscraper Comparison (evaluated 2026-02-22)

Also evaluated Outscraper's `zillow-search` API as an alternative to Apify:

| Metric | Apify | Outscraper |
|--------|-------|------------|
| Cost per property | ~$0.003 | ~$0.002 |
| Speed | ~0.8s/property (batch) | 8-70s/property |
| Batch support | Yes (25+ URLs/run) | No (one at a time) |
| rentZestimate | Yes | No |
| lotSize | Yes | No |
| taxAssessedValue | Yes | No |
| taxHistory | Yes | No |

**Verdict:** Apify wins decisively — 35x faster in batch, richer data, only $1/1K more expensive.

#### Key Files

- `scripts/intelligence/enrich_real_estate.py` — Fixed zpid matching (both paths)
- `scripts/intelligence/rescrape_zillow.py` — Standalone re-scrape script

### 14.15 FEC Multi-Person Aggregation Bug Fix (2026-02-22)

#### The Bug

The original FEC enrichment script used **prefix-based first name matching**:

```python
# OLD (broken)
first_match = (
    fec_first == first_lower or
    fec_first.startswith(first_lower) or  # "andrea" matches "andre"!
    first_lower.startswith(fec_first)      # "chris" matches "christopher"!
)
```

This caused 308 contacts to show >50 donations each, clearly aggregating records from multiple different people. Example: "Andre Steele" (Puget Sound Naval Shipyard, WA) had $43K across 389 donations — but the data included "Andrea Dew Steele" (Platypus Advisors, SF) and "Andrew Steele" (physician, KY).

#### The Fix (3 changes)

1. **Exact first name matching** — no prefix matching:
```python
first_match = (fec_first == first_lower)
```

2. **GPT-5 mini verification** on every match — sends contact's LinkedIn profile (employer, location, career history) alongside FEC summary (employer, occupation, contributor states/cities) to verify same person

3. **State extraction from employment** — when `contact.state` is null, extracts US state from `enrich_employment` JSONB to give FEC a state filter

#### Results After Fix

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Contacts with >50 donations | 308 | 51 |
| GPT-verified donors | N/A (no verification) | 325 |
| GPT-rejected (wrong person) | N/A | 292 |
| Total verified donation amount | Inflated/wrong | $5.38M |

The 51 remaining >50-donation contacts are **legitimate high-frequency donors** (GPT-verified with employer matches):
- Donnel Baird (BlocPower) — 525 donations, $29K, high confidence
- Michelle Boyers (Give Forward Foundation) — 248 donations, $1.4M, high confidence
- Regan Pritzker (Pritzker family) — 143 donations, $1.84M, medium confidence
- Dakarai Aarons (Chan Zuckerberg Initiative) — 323 donations, high confidence

#### Key File

- `scripts/intelligence/enrich_fec_donations.py` — Full rewrite with GPT verification, exact matching, employment state extraction

---

## 16. Open Questions

1. **Overwrite existing scoring?** The current `donor_capacity_score`, `warmth_level`, `shared_institutions` columns have data for 1,305 contacts (from Perplexity). Should we overwrite them with the new AI-tagged values, or keep both? Recommendation: **Keep old columns, write to new `ai_*` columns**, then deprecate old ones after validating the new scores are better.

2. **Contact posts scraping.** Currently only Justin's posts are in the DB. Should we scrape posts for high-priority contacts to enrich the interests_embedding? Cost: ~$0.15/contact for 50 posts. Could do top 200-300 contacts for ~$30-45.

3. **Refresh frequency.** How often to re-run the tagging pipeline? Recommendation: quarterly, or on-demand when Justin adds new connections.

4. **LinkedIn connection date as signal.** The `connected_on` field ranges from Apr 2015 to Oct 2024. Earlier connections may indicate closer relationships (connected when networks were smaller) or may just be old. The LLM should weigh this with other signals.

5. **Communication history across accounts.** Justin has 5 Google Workspace accounts. Should we search all of them for each contact? Recommendation: yes, but prioritize by account relevance (e.g., `google-workspace` for personal, `kindora` for business).

6. **Embedding model migration.** Camelback uses 1536 dims. Should we also generate 1536-dim embeddings for contacts for cross-table similarity search? Or migrate Camelback to 768 dims? Not urgent — keep them separate for now.

7. **Property ownership verification — RESOLVED.** Heuristic classifier is sufficient. Only 10 contacts have ambiguous ownership WITH a Zestimate (the only scenario where bad data matters). No ownership API is cost-effective ($179+/mo for ATTOM, Propwire blocked, RentCast 50/mo limit). Manual spot-check of those 10 contacts if needed. See section 14.13 "Final Decision" for full analysis.

8. **411.com long-term reliability.** The free 411.com scraper works today (no Cloudflare, data in server-rendered HTML), but could break if they add anti-bot protection. The Apify skip-trace pipeline remains as a fallback. Monitor for HTML structure changes or rate limiting tightening. **Update 2026-02-22:** Full 793-contact retry run showed 0 rate-limit errors and 0 HTTP errors through 100+ contacts with 5 concurrent workers — very stable.

9. **Zillow autocomplete city mismatches — IDENTIFIED.** ~265 contacts with addresses didn't resolve via Zillow autocomplete because Zillow sometimes uses different city names than skip-trace (e.g., "El Sobrante" vs "Richmond" for the same 94803 zip). Could be resolved with city-name fuzzy matching or zip-code-based search in a future pass.
