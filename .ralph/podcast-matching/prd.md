# Project: Best-in-Class Podcast Matching System

## Overview

Upgrade the existing podcast outreach tool from keyword-only discovery + single-signal GPT scoring to a multi-method AI matching system. This adds vector embedding semantic similarity, similar-speaker graph discovery, AI-expanded keyword generation, and composite multi-signal scoring.

**Current state:** 383 podcast_targets (iTunes-only), 345 scored for Sally (74 strong, 126 moderate, 145 weak), all enriched, 224 with host emails. Podcast Index API keys now configured.

**Goal:** Find every relevant podcast (not just keyword matches), score with 5 signals instead of 1, and surface discovery provenance in the UI.

## Architecture Extension

```
EXISTING (unchanged):
  podcast_targets → podcast_episodes → podcast_pitches → podcast_campaigns
  speaker_profiles

NEW columns on podcast_targets:
  description_embedding vector(768)   -- semantic matching
  discovery_methods text[]            -- how each podcast was found

NEW column on speaker_profiles:
  profile_embedding vector(768)       -- for cosine similarity vs podcasts

NEW script:
  embed_podcasts.py                   -- batch embed podcasts + speakers

MODIFIED scripts:
  discover_podcasts.py                -- add 3 new discovery methods
  score_podcast_fit.py                -- composite 5-signal scoring

MODIFIED UI:
  podcast-outreach/page.tsx           -- discovery method badges + signal breakdown
```

## Technical Context

- **pgvector 0.8.0** installed, contacts table has 2,946 rows with 768-dim embeddings
- **text-embedding-3-small** model, 768 dimensions, $0.02/1M tokens
- **Batch embedding pattern:** `scripts/intelligence/generate_embeddings.py` — BATCH_SIZE=500, OpenAI batch API
- **Cosine distance operator:** `<=>` (pgvector), similarity = `1 - distance`
- **Podcast Index API:** Keys in `.env` as `PODCAST_INDEX_API_KEY` / `PODCAST_INDEX_API_SECRET`
- **Direct DB access:** Use `psycopg2` for pgvector queries (Supabase Python client can't do vector ops)
  - Host: `db.ypqsrejrsocebnldicke.supabase.co:5432`, dbname: `postgres`, user: `postgres`
  - Password: `os.environ["SUPABASE_DB_PASSWORD"]`
- **OpenAI key:** `OPENAI_APIKEY` (no underscore before KEY)
- **GPT-5.4 mini** does NOT support temperature=0, use default only

---

## User Stories

### [x] US-001: Database Migration — Embedding Columns

**Goal:** Add vector embedding columns and discovery tracking to podcast tables.

**File to create:** `supabase/migrations/20260414_add_podcast_embeddings.sql`

**Migration SQL:**
```sql
-- Embedding for semantic matching
ALTER TABLE podcast_targets ADD COLUMN IF NOT EXISTS description_embedding vector(768);

-- Track how each podcast was discovered
ALTER TABLE podcast_targets ADD COLUMN IF NOT EXISTS discovery_methods text[] DEFAULT '{}';

-- Speaker profile embedding for direct comparison
ALTER TABLE speaker_profiles ADD COLUMN IF NOT EXISTS profile_embedding vector(768);

-- IVFFlat index for cosine similarity (lists ~ sqrt(rows), start with 20 for ~400 rows)
CREATE INDEX IF NOT EXISTS idx_podcast_targets_embedding
  ON podcast_targets USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 20);
```

**Apply migration:** Use `mcp__supabase-contacts__apply_migration` MCP tool (most reliable method).

**Acceptance criteria:**
- [ ] Migration file exists at `supabase/migrations/20260414_add_podcast_embeddings.sql`
- [ ] Columns exist: `SELECT column_name FROM information_schema.columns WHERE table_name = 'podcast_targets' AND column_name IN ('description_embedding', 'discovery_methods');` returns 2 rows
- [ ] Speaker profiles column: `SELECT column_name FROM information_schema.columns WHERE table_name = 'speaker_profiles' AND column_name = 'profile_embedding';` returns 1 row
- [ ] Index exists: `SELECT indexname FROM pg_indexes WHERE indexname = 'idx_podcast_targets_embedding';` returns 1 row

---

### [x] US-002: Embed Podcasts and Speaker Profiles

**Goal:** Create a script to generate vector embeddings for podcast descriptions and speaker profiles using text-embedding-3-small.

**File to create:** `scripts/intelligence/embed_podcasts.py`

**CRITICAL: Read `scripts/intelligence/generate_embeddings.py` first.** Reuse its patterns exactly:
- OpenAI client: `OpenAI(api_key=os.environ["OPENAI_APIKEY"])`
- Model: `text-embedding-3-small`, dimensions: 768
- Batch size: 500 (OpenAI supports up to 2048)
- Retry logic: 3 retries with exponential backoff on RateLimitError
- Use `psycopg2` for saving embeddings (Supabase client can't handle vector type well)

**Podcast embedding text format:**
```
{title} | {author}
{description}
Categories: {cat1}, {cat2}, ...
Recent episodes: {ep1_title}; {ep2_title}; {ep3_title}
```

**Speaker profile embedding text format:**
```
{name} | {headline}
Bio: {bio}
Topic Pillars: {pillar1_name}: {pillar1_description}; {pillar2_name}: {pillar2_description}; ...
Keywords: {keyword1}, {keyword2}, ...
```

**Pipeline:**
1. Load podcast_targets where `description_embedding IS NULL` (via Supabase client)
2. For each podcast, load its recent episodes from podcast_episodes (top 3 by published_at)
3. Build embedding text per podcast
4. Batch embed via OpenAI (reuse generate_embeddings.py pattern)
5. Save embeddings via psycopg2: `UPDATE podcast_targets SET description_embedding = %s WHERE id = %s`
6. Also embed speaker_profiles where `profile_embedding IS NULL`
7. Save speaker embeddings via psycopg2

**CLI flags:**
```
--test          # Process 5 podcasts only
--force         # Re-embed already-embedded podcasts
--limit N       # Max podcasts to process
--speakers-only # Only embed speaker profiles
```

**Acceptance criteria:**
- [ ] Script runs: `source .venv/bin/activate && python scripts/intelligence/embed_podcasts.py --test`
- [ ] Embeds 5 podcasts + 2 speaker profiles in test mode
- [ ] Verify: `SELECT count(*) FROM podcast_targets WHERE description_embedding IS NOT NULL;` shows 5 (test) or ~383 (full)
- [ ] Verify: `SELECT count(*) FROM speaker_profiles WHERE profile_embedding IS NOT NULL;` shows 2
- [ ] Embeddings are 768-dim: `SELECT array_length(description_embedding::real[], 1) FROM podcast_targets WHERE description_embedding IS NOT NULL LIMIT 1;` returns 768
- [ ] Full run: `python scripts/intelligence/embed_podcasts.py` embeds all un-embedded podcasts
- [ ] Cost printout shows total tokens and estimated cost

---

### [ ] US-003: Enhanced Discovery — Podcast Index + Expanded Keywords

**Goal:** Upgrade discover_podcasts.py to use Podcast Index API (now configured) and add AI-generated expanded search terms.

**File to modify:** `scripts/intelligence/discover_podcasts.py`

**Read first:** The existing script at `scripts/intelligence/discover_podcasts.py` — understand the full pipeline before modifying.

**Changes:**

1. **Podcast Index now works** — the API keys are in `.env`. The existing code already handles PI gracefully (falls back to iTunes when keys missing). Verify PI search works by running: `python scripts/intelligence/podcast_api.py`

2. **Add `discovery_methods` tracking** — when saving podcasts, set the `discovery_methods` array:
   - Podcasts found via keyword search: `['keyword_search']`
   - When a podcast is found by multiple methods, append to the array (don't overwrite)
   - Modify `save_podcasts()` to handle the new column

3. **Add expanded keyword generation** — new function `generate_expanded_terms()`:
   ```python
   def generate_expanded_terms(speaker: dict, oai: OpenAI, existing_terms: list[str]) -> list[str]:
       """Use GPT-5.4 mini to generate additional search terms from speaker's topic pillars."""
       pillars_text = "\n".join(
           f"- {p['name']}: {p['description']}"
           for p in speaker.get('topic_pillars', [])
       )
       prompt = f"""Generate 25 additional podcast search terms for this speaker.

   Speaker: {speaker['name']}
   Headline: {speaker['headline']}
   Topic Pillars:
   {pillars_text}

   Already searching for: {', '.join(existing_terms)}

   Generate terms that:
   - Cover adjacent topics a podcast booking agent would search
   - Include niche audience-specific phrases
   - Include common podcast category names that match
   - Avoid duplicating the existing terms

   Return a JSON array of strings."""
       # Call GPT-5.4 mini with json_object response_format
       # Parse and return list of new terms
   ```

4. **Add `--method` flag** — `keyword` (default, existing behavior), `expanded` (keyword + expanded terms), `all` (everything)

5. **Load speaker profile from DB** when using `expanded` or `all` method — need topic pillars for expanded term generation

**New CLI flags:**
```
--method keyword|expanded|all    # discovery methods (default: keyword)
```

**Acceptance criteria:**
- [ ] Podcast Index search works: `python scripts/intelligence/discover_podcasts.py --speaker sally --test --limit 5` shows results from both PI and iTunes
- [ ] Expanded keywords: `python scripts/intelligence/discover_podcasts.py --speaker sally --method expanded --test --limit 5` generates new terms from GPT and searches them
- [ ] `discovery_methods` column populated on new saves
- [ ] Re-running is safe (upsert, doesn't duplicate existing podcasts)
- [ ] Total podcast count increases from baseline 383

---

### [ ] US-004: Similar-Speaker Discovery

**Goal:** Find podcasts that have hosted speakers similar to Sally/Justin by using pgvector to find similar contacts in our DB, then searching for their podcast appearances.

**File to modify:** `scripts/intelligence/discover_podcasts.py`

**Read first:**
- `scripts/intelligence/generate_embeddings.py` — understand how contacts table embeddings work
- The contacts table has `interests_embedding vector(768)` on ~2,942 rows

**New function: `discover_by_similar_speakers()`**

Pipeline:
1. Load speaker's `profile_embedding` from `speaker_profiles` (embedded in US-002)
2. Query contacts via psycopg2 for the 50 most similar by interests_embedding:
   ```sql
   SELECT id, first_name, last_name, headline, company,
          1 - (interests_embedding <=> %s) as similarity
   FROM contacts
   WHERE interests_embedding IS NOT NULL
   ORDER BY interests_embedding <=> %s
   LIMIT 50
   ```
3. For each similar contact (similarity > 0.5), search Podcast Index by name:
   ```python
   pi_client.search_by_term(f"{first_name} {last_name}", max_results=20)
   ```
4. Filter results: only keep podcasts where the similar contact appears to be a guest (title/description mentions their name)
5. Tag results with `discovery_methods = ['similar_speaker']`
6. Save via existing `save_podcasts()` function
7. Print the discovery chain: "Found {podcast} via similar speaker {contact_name} (similarity: {score})"

**Important:** Use psycopg2 for the vector query, not Supabase client.

**New `--method` option:** `similar-speaker` (and include in `all`)

**CLI:**
```
--method similar-speaker         # only similar-speaker discovery
--similar-speaker-limit 50      # how many similar contacts to check (default: 50)
```

**Acceptance criteria:**
- [ ] `python scripts/intelligence/discover_podcasts.py --speaker sally --method similar-speaker --test --limit 10` finds contacts similar to Sally and searches for their podcast appearances
- [ ] Output shows the discovery chain (similar contact → podcast found)
- [ ] New podcasts tagged with `discovery_methods = ['similar_speaker']`
- [ ] Does not duplicate existing podcasts (upsert logic)
- [ ] Gracefully handles contacts with no podcast appearances (most won't have any)

---

### [ ] US-005: Composite Multi-Signal Scoring

**Goal:** Replace single-signal GPT scoring with a 5-signal composite score.

**File to modify:** `scripts/intelligence/score_podcast_fit.py`

**Read first:** The existing script — understand the GPT scoring pipeline, the save function, and the podcast_pitches schema.

**Changes:**

1. **Add embedding similarity signal** — compute cosine similarity between speaker's `profile_embedding` and podcast's `description_embedding`:
   ```python
   def compute_embedding_similarity(speaker_embedding: list[float], podcast_embedding: list[float]) -> float:
       """Cosine similarity between two vectors. Returns 0-1."""
       import numpy as np
       a = np.array(speaker_embedding)
       b = np.array(podcast_embedding)
       return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
   ```
   Note: numpy is already in the venv. If not, `pip install numpy`.

2. **Load embeddings** — fetch speaker's `profile_embedding` from speaker_profiles, and each podcast's `description_embedding` from podcast_targets (add to the existing select query)

3. **Add activity recency signal:**
   ```python
   def compute_activity_recency(last_episode_date: str | None) -> float:
       """0-1 score based on how recently the podcast published."""
       if not last_episode_date:
           return 0.3  # unknown = moderate
       days_ago = (datetime.now(timezone.utc) - parse_date(last_episode_date)).days
       if days_ago <= 7: return 1.0
       if days_ago <= 30: return 0.8
       if days_ago <= 60: return 0.5
       if days_ago <= 90: return 0.3
       return 0.1
   ```

4. **Add episode count signal:**
   ```python
   def compute_episode_count_signal(count: int) -> float:
       """0-1 normalized. More episodes = more established."""
       if count >= 200: return 1.0
       if count >= 100: return 0.8
       if count >= 50: return 0.6
       if count >= 20: return 0.4
       if count >= 10: return 0.2
       return 0.1
   ```

5. **Add similar-speaker boost** — check if `'similar_speaker' IN discovery_methods`:
   ```python
   similar_speaker_boost = 0.15 if 'similar_speaker' in (podcast.get('discovery_methods') or []) else 0.0
   ```

6. **Composite formula:**
   ```python
   composite = (
       0.35 * gpt_fit_score +
       0.30 * embedding_similarity +
       0.15 * similar_speaker_boost +
       0.10 * activity_recency +
       0.10 * episode_count_signal
   )

   # Tier from composite
   if composite >= 0.70: tier = "strong"
   elif composite >= 0.45: tier = "moderate"
   else: tier = "weak"
   ```

7. **Save signal breakdown** in `topic_match` JSONB (alongside existing matching_pillars):
   ```json
   {
     "composite_score": 0.82,
     "signals": {
       "gpt_fit_score": 0.85,
       "embedding_similarity": 0.91,
       "similar_speaker_boost": 0.15,
       "activity_recency": 0.8,
       "episode_count_signal": 0.6
     },
     "matching_pillars": ["Family Camping as Equity Work", "Sacred Space in Nature"],
     "discovery_methods": ["keyword_search", "similar_speaker"]
   }
   ```

8. **Add `--composite` flag** (default: on). `--no-composite` falls back to GPT-only scoring (backward compat).

9. **Handle missing embeddings gracefully** — if a podcast has no `description_embedding`, use `embedding_similarity = 0.3` (neutral default). Same for speaker with no `profile_embedding`.

**Acceptance criteria:**
- [ ] `python scripts/intelligence/score_podcast_fit.py --speaker sally --limit 10 --test` shows composite scores with all 5 signals
- [ ] Output includes signal breakdown per podcast
- [ ] Composite tiers differ from GPT-only tiers for some podcasts (embedding signal matters)
- [ ] `--no-composite` flag produces GPT-only scores (backward compat)
- [ ] Scores saved with signal breakdown in `topic_match` JSONB
- [ ] Missing embeddings handled gracefully (no crashes)

---

### [ ] US-006: Re-run Full Pipeline for Sally

**Goal:** Execute the complete upgraded pipeline for Sally, documenting before/after counts.

**This is a pipeline execution story, not a code change story.** Run existing scripts in sequence.

**Steps:**

1. **Record baseline:**
   ```sql
   SELECT count(*) as total_podcasts FROM podcast_targets;
   SELECT fit_tier, count(*) FROM podcast_pitches WHERE speaker_profile_id = 1 GROUP BY fit_tier;
   ```

2. **Embed existing podcasts + speaker profiles:**
   ```bash
   source .venv/bin/activate
   python scripts/intelligence/embed_podcasts.py
   ```

3. **Discover with all methods:**
   ```bash
   python scripts/intelligence/discover_podcasts.py --speaker sally --method all
   ```

4. **Enrich new podcasts:**
   ```bash
   python scripts/intelligence/enrich_podcasts.py --limit 500 --skip-verify
   ```

5. **Embed newly discovered podcasts:**
   ```bash
   python scripts/intelligence/embed_podcasts.py
   ```

6. **Delete old Sally scores (so composite re-scoring replaces them):**
   ```sql
   DELETE FROM podcast_pitches WHERE speaker_profile_id = 1;
   ```

7. **Re-score all with composite scoring:**
   ```bash
   python scripts/intelligence/score_podcast_fit.py --speaker sally --limit 1000 --workers 100
   ```

8. **Record results:**
   ```sql
   SELECT count(*) as total_podcasts FROM podcast_targets;
   SELECT fit_tier, count(*) FROM podcast_pitches WHERE speaker_profile_id = 1 GROUP BY fit_tier;
   SELECT count(*) FROM podcast_targets WHERE 'similar_speaker' = ANY(discovery_methods);
   SELECT count(*) FROM podcast_targets WHERE 'keyword_search' = ANY(discovery_methods);
   SELECT count(*) FROM podcast_targets WHERE 'expanded_keywords' = ANY(discovery_methods);
   ```

**Acceptance criteria:**
- [ ] Total podcast count increased from 383
- [ ] All podcasts have description_embedding
- [ ] Both speaker profiles have profile_embedding
- [ ] Sally's scores use composite scoring (topic_match has 'signals' key)
- [ ] Results documented in progress.txt with before/after comparison

---

### [ ] US-007: UI — Discovery Method Badges + Signal Breakdown

**Goal:** Update the Discovery tab to show how each podcast was found and the composite score breakdown.

**File to modify:** `job-matcher-ai/app/tools/podcast-outreach/page.tsx`
**File to modify:** `job-matcher-ai/app/api/podcast/discover/route.ts`

**Read first:** The existing Discovery tab (DiscoveryTab component) in page.tsx and the discover API route.

**API changes (`discover/route.ts`):**
1. Add `discovery_methods` to the podcast_targets select query
2. Add `topic_match` from podcast_pitches to the join (already joining for fit_tier/fit_score)

**UI changes (DiscoveryTab in `page.tsx`):**

1. **Discovery method badges** — new column in the results table after "Activity":
   - Each badge shows the discovery method: "Keyword" (blue), "Similar Speaker" (purple), "Expanded" (orange), "Embedding" (cyan)
   - A podcast can have multiple badges
   - Use existing Badge component with variant="outline" and colored text

2. **Expandable signal breakdown** — when a row is clicked/expanded:
   - Show a small bar chart or labeled values for each of the 5 composite signals
   - Format: `GPT: 0.85 | Embedding: 0.91 | Speaker: +0.15 | Recency: 0.80 | Episodes: 0.60`
   - Use small colored progress bars or inline badges
   - Show composite score prominently: "Composite: 0.82"
   - Data comes from `topic_match.signals` JSONB

3. **Sort by composite score** — the fit_score column should show the composite score (already stored as fit_score in podcast_pitches)

4. **Filter by discovery method** — add a multi-select filter: "Found via: Keyword / Similar Speaker / Expanded / All"

**Acceptance criteria:**
- [ ] Discovery tab shows discovery method badges per podcast
- [ ] Clicking a row expands to show composite signal breakdown
- [ ] Filter by discovery method works
- [ ] TypeScript compiles: `cd job-matcher-ai && npx tsc --noEmit`
- [ ] Deploy: `cd job-matcher-ai && npx vercel --prod --yes --scope true-steele`
