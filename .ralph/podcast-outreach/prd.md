# Project: Podcast Outreach Tool

## Overview

Build a podcast outreach tool to get Sally and Justin Steele booked on podcasts heading into camping season (May-September 2026). The tool discovers podcasts via free APIs (Podcast Index, iTunes), scores fit with GPT-5.4 mini, generates personalized pitches with Claude Sonnet 4.6, and sends via Gmail. Target: 50-100 podcast outreach in the first campaign.

## Architecture

```
+-----------------------------------------------------+
|  Next.js App (job-matcher-ai)                        |
|  /tools/podcast-outreach                             |
|                                                      |
|  Tab 1: Speaker Profiles (Sally & Justin)            |
|  Tab 2: Podcast Discovery & Matching                 |
|  Tab 3: Pitch Review & Campaign                      |
|  Tab 4: Campaign Tracker                             |
+---------------+-----------------------------+--------+
                |                             |
                v                             v
+------------------------+   +---------------------------+
| Python Scripts          |   | Next.js API Routes        |
| (scripts/intelligence)  |   | (app/api/podcast-*)       |
|                         |   |                           |
| discover_podcasts.py    |   | /api/podcast/discover     |
| enrich_podcasts.py      |   | /api/podcast/score        |
| score_podcast_fit.py    |   | /api/podcast/generate     |
| generate_podcast_pitches|   | /api/podcast/send         |
+----------+--------------+   +------------+--------------+
           |                               |
           v                               v
+------------------------------------------------------+
|  Supabase PostgreSQL                                  |
|                                                       |
|  speaker_profiles      - Sally & Justin profiles      |
|  podcast_targets       - discovered podcasts           |
|  podcast_episodes      - recent episodes per podcast   |
|  podcast_pitches       - generated pitch copy          |
|  podcast_campaigns     - send status, tracking         |
+------------------------------------------------------+
```

## Technical Context

- **Tech Stack:** Next.js 15 (App Router), shadcn/Radix UI, Supabase PostgreSQL, Python 3.12
- **AI Models:** GPT-5.4 mini (fit scoring), Claude Sonnet 4.6 (pitch writing)
- **APIs:** Podcast Index (free), iTunes Search (free), ZeroBounce (existing credits)
- **Env vars:** `OPENAI_APIKEY`, `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ZEROBOUNCE_API_KEY`, `PODCAST_INDEX_API_KEY`, `PODCAST_INDEX_API_SECRET`
- **Supabase project:** `ypqsrejrsocebnldicke`
- **Python venv:** `/Users/Justin/Code/TrueSteele/contacts/.venv/`

---

## Database Schema

The following SQL creates all 5 tables. Use this exact schema in the migration.

```sql
-- Speaker profiles for podcast pitching
CREATE TABLE IF NOT EXISTS speaker_profiles (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name text NOT NULL,
  slug text UNIQUE NOT NULL,
  bio text,
  headline text,
  website_url text,
  linkedin_url text,
  photo_url text,
  topic_pillars jsonb,
  writing_samples jsonb,
  past_appearances jsonb,
  one_sheet_data jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Discovered podcast targets
CREATE TABLE IF NOT EXISTS podcast_targets (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  podcast_index_id bigint,
  itunes_id bigint,
  title text NOT NULL,
  author text,
  description text,
  categories jsonb,
  language text DEFAULT 'en',
  episode_count int,
  last_episode_date timestamptz,
  website_url text,
  rss_url text,
  image_url text,
  host_name text,
  host_email text,
  email_source text,
  email_verified boolean DEFAULT false,
  listener_estimate int,
  activity_status text,
  discovered_at timestamptz DEFAULT now(),
  enriched_at timestamptz,
  UNIQUE(podcast_index_id)
);

-- Recent episodes for pitch personalization
CREATE TABLE IF NOT EXISTS podcast_episodes (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  podcast_target_id bigint REFERENCES podcast_targets(id) ON DELETE CASCADE,
  title text NOT NULL,
  description text,
  published_at timestamptz,
  duration_seconds int,
  episode_url text,
  guests jsonb,
  created_at timestamptz DEFAULT now()
);

-- AI-generated fit scores and pitches
CREATE TABLE IF NOT EXISTS podcast_pitches (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  podcast_target_id bigint REFERENCES podcast_targets(id) ON DELETE CASCADE,
  speaker_profile_id bigint REFERENCES speaker_profiles(id),
  fit_tier text,
  fit_score real,
  fit_rationale text,
  topic_match jsonb,
  episode_hooks jsonb,
  subject_line text,
  subject_line_alt text,
  pitch_body text,
  pitch_body_html text,
  episode_reference text,
  suggested_topics jsonb,
  pitch_status text DEFAULT 'draft',
  approved_at timestamptz,
  approved_by text,
  human_edits text,
  model_used text,
  generated_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Campaign send tracking
CREATE TABLE IF NOT EXISTS podcast_campaigns (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  pitch_id bigint REFERENCES podcast_pitches(id),
  speaker_profile_id bigint REFERENCES speaker_profiles(id),
  sent_from_email text,
  sent_to_email text,
  sent_at timestamptz,
  send_method text,
  gmail_message_id text,
  gmail_thread_id text,
  opened_at timestamptz,
  replied_at timestamptz,
  reply_sentiment text,
  followup_scheduled_at timestamptz,
  followup_sent_at timestamptz,
  followup_body text,
  outcome text,
  recording_date date,
  episode_air_date date,
  episode_url text,
  notes text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Indexes
CREATE INDEX idx_podcast_targets_activity ON podcast_targets(activity_status);
CREATE INDEX idx_podcast_pitches_speaker ON podcast_pitches(speaker_profile_id);
CREATE INDEX idx_podcast_pitches_status ON podcast_pitches(pitch_status);
CREATE INDEX idx_podcast_campaigns_outcome ON podcast_campaigns(outcome);
```

---

## Speaker Profile Seed Data

### Sally Steele

```json
{
  "name": "Sally Steele",
  "slug": "sally",
  "bio": "CEO and Co-Founder of Outdoorithm, a social enterprise simplifying camping for urban families through AI-powered trip planning. Co-Founder and Board Chair of Outdoorithm Collective, a nonprofit creating belonging in nature for historically excluded communities. Ordained minister (MDiv, Gordon-Conwell). Mother of four. 107 family camping trips and counting. REI Embark Fellow. Louisville Institute grantee researching nature, liturgy, and women of color.",
  "headline": "CEO & Co-Founder, Outdoorithm | Board Chair, Outdoorithm Collective | Ordained Minister | 107 Family Camping Trips",
  "website_url": "https://www.sallysteele.org",
  "linkedin_url": "https://www.linkedin.com/in/steelesally",
  "topic_pillars": [
    {
      "name": "Family Camping as Equity Work",
      "description": "Camping is one of the most affordable, accessible ways for families to experience nature. $25/night at Humboldt Redwoods vs $11,300 at Disney. The wilderness does not have Lightning Lanes.",
      "talking_points": [
        "107 trips, 273 nights, 54 campgrounds with four kids",
        "Outdoorithm Collective: free camping trips for urban families, 260+ participants across 9 trips",
        "Disney vs Humboldt comparison: $11,300 vs $100 for the same family",
        "Four families on the trail. One looked like ours. That is not a nature problem. That is an access problem."
      ],
      "keywords": ["outdoor equity", "family camping", "nature access", "camping families", "affordable outdoors"]
    },
    {
      "name": "Sacred Space in Nature",
      "description": "The campfire as sacred space. Nature as encounter with something bigger than ourselves. Louisville Institute grantee studying nature, liturgy, and women of color.",
      "talking_points": [
        "Louisville Institute Pastoral Study Project: Reclaiming Sacred Ground",
        "Sacred spaces are containers we build intentionally for belonging",
        "The arena keeps us competing for scraps. Sacred space is where we practice the relationships that could flip the table.",
        "What started as inventory became something sacred - tending tools that remove barriers"
      ],
      "keywords": ["faith nature", "sacred space", "spirituality outdoors", "nature spirituality", "ministry outdoors"]
    },
    {
      "name": "Black Motherhood Outdoors",
      "description": "A Black mother of four navigating outdoor spaces where her family rarely sees families that look like them. Building community across difference in nature.",
      "talking_points": [
        "Four children ages 4-16, camping since the oldest was a toddler",
        "REI Embark Fellow (outdoor industry credibility as entrepreneur of color)",
        "Greenwood Ave magazine feature alongside Black Wall Street legacy",
        "Formerly Co-Executive Director of City Hope SF ($1.9M nonprofit in the Tenderloin)"
      ],
      "keywords": ["Black motherhood", "parenting outdoors", "women outdoors", "diversity outdoors", "outdoor parenting"]
    },
    {
      "name": "Building Community Across Difference",
      "description": "When a campervan got stuck, the engineer, doctor, social worker, actor all grabbed shovels. The wilderness does not check LinkedIn profiles.",
      "talking_points": [
        "48 people at Humboldt: when it lurched free, we flexed like we had won the championship",
        "Eliza called a man she met 48 hours earlier Uncle John. Now he was family.",
        "At Disney, I knew exactly who could afford Lightning Passes. At Humboldt, nobody sorted us at all.",
        "Justice Outside conference + Climate Week: two rooms not talking to each other"
      ],
      "keywords": ["community building", "bridging difference", "belonging", "outdoor community"]
    },
    {
      "name": "Founder Journey",
      "description": "Starting a business is one of the hardest things I have ever done, probably second only to birthing and parenting 4 kids. Both can be hard, messy and chaotic.",
      "talking_points": [
        "Left nonprofit leadership to start a social enterprise with her husband",
        "REI Path Ahead Ventures Summit: 45 outdoor founders of color, three days",
        "Exploring cooperative ownership model for Outdoorithm",
        "Camp as it comes: perfection is not the goal, adaptation is"
      ],
      "keywords": ["founder story", "social enterprise", "startup journey", "women founders"]
    },
    {
      "name": "Leave Anyway Philosophy",
      "description": "Not 'leave when ready' because you are never ready. Not 'leave when convenient' because it never is. Just: leave anyway.",
      "talking_points": [
        "His week: 24 meetings. Mine: 3 grant deadlines. Our reality: 2 startups to run. The forecast: atmospheric river.",
        "Justin chased a raccoon into the woods at 10pm, wrestled the mac and cheese container back",
        "Morning: rain dripping off redwoods, the Gualala River flowing past our site, a stillness I had not felt in months",
        "Seven more nights camping! demanded Eliza. Not one!"
      ],
      "keywords": ["outdoor family adventure", "camping with kids", "nature resilience", "adventure parenting"]
    }
  ],
  "writing_samples": [
    {
      "text": "$11,300 at Disney. $100 at Humboldt Redwoods. One sorted us by income. The other showed us what America could be. At Disney, I knew exactly who could afford Lightning Passes. The algorithm sorted us perfectly. At Humboldt, nobody sorted us at all. The wilderness does not check LinkedIn profiles. The river does not care about your ZIP code. 449 nights at Humboldt for the price of three at Disney. We will remember both trips. One for the magic money could buy. The other for the magic money could not touch.",
      "source": "LinkedIn - Disney vs Humboldt post (2,189 impressions, 152 engagements)"
    },
    {
      "text": "Leave anyway. That has become a mantra at Outdoorithm Collective. Not 'leave when ready' because you are never ready. Not 'leave when it is convenient' because it never is. Just: Leave anyway. His week: 24 meetings. Mine: 3 grant deadlines. Our reality: 2 startups to run. The forecast: Atmospheric river hitting the west coast. The smart move: Cancel everything. The deeper pull: Leave anyway.",
      "source": "LinkedIn - Leave Anyway post (1,477 impressions, 91 engagements)"
    },
    {
      "text": "Generational Gifts. That is what I was thinking about yesterday as I stood in a public storage unit with two board members and one of our youth leaders to sort camping gear. Not how I would normally spend a Sunday, but there we were. I picked up an unlabeled stuff sack, unzipped it, and found it full of straps. What started as inventory became something sacred.",
      "source": "LinkedIn - Generational Gifts post (2,161 impressions, 72 engagements)"
    },
    {
      "text": "I felt the gap before I could name it. Three days. Two rooms. Same crisis, different lenses. The two rooms were not talking to each other. Both are necessary. One builds community power. One builds literal power grids. But siloed, something essential gets lost. People do not protect what they do not love. And love grows from belonging.",
      "source": "LinkedIn - Justice Outside + Climate Week post (718 impressions)"
    }
  ],
  "past_appearances": [
    {
      "podcast_name": "Justice Outside Podcast",
      "episode_title": "TBD",
      "date": "2026-05",
      "url": null,
      "notes": "Recording complete, airing May 2026"
    }
  ]
}
```

### Justin Steele

```json
{
  "name": "Justin Steele",
  "slug": "justin",
  "bio": "Co-Founder and CEO of Kindora, an AI platform helping nonprofits find and win grants. Co-Founder and CTO of Outdoorithm, simplifying camping through AI. Board member, San Francisco Foundation. Former Google.org leader who directed over $100M in grants and built AI products for social impact. Ex-Bain consultant, HBS MBA, HKS MPA. Father of four. 107 family camping trips.",
  "headline": "Co-Founder & CEO, Kindora | Co-Founder & CTO, Outdoorithm | SF Foundation Board | Ex Google.org | HBS MBA",
  "website_url": "https://www.truesteele.com",
  "linkedin_url": "https://www.linkedin.com/in/justinrichardsteele",
  "topic_pillars": [
    {
      "name": "Corporate Philanthropy From the Inside",
      "description": "Spent a decade at Google.org directing grants and building AI products for social impact. Left to build what the system would not fund.",
      "talking_points": [
        "Directed $100M+ in Google.org grants across workforce development, racial justice, economic opportunity",
        "Led Google.org Fellowship teams deploying engineers to nonprofits",
        "Watched funders hesitate to make sustained infrastructure investments that great technology requires",
        "Only 36% of funders feel confident evaluating AI technical feasibility"
      ],
      "keywords": ["corporate philanthropy", "philanthropy", "grantmaking", "nonprofit funding", "social impact"]
    },
    {
      "name": "AI for Social Impact",
      "description": "Building Kindora, an AI platform that helps nonprofits find and win grants. If nonprofits do not harness AI, others will shape outcomes without our values.",
      "talking_points": [
        "Kindora uses AI to match nonprofits with funders, eliminating months of tedious prospecting",
        "Created AI funder personas that instantly filter thousands of poor-fit prospects",
        "Building with AI every single day, constantly blown away by what these tools can do",
        "Philanthropy seemed unprepared to scale AI innovation, so I started building myself"
      ],
      "keywords": ["AI social good", "nonprofit technology", "tech for good", "AI nonprofits", "social impact tech"]
    },
    {
      "name": "Leaving Big Tech for Purpose",
      "description": "Had one of those golden tickets for a decade. Made millions at Google. Gave it up. Now building impact for a fraction of that.",
      "talking_points": [
        "10 years at Google, left when his role was eliminated in 2024 layoffs",
        "Chose impact work over returning to Big Tech",
        "The person you have been trained to see as your enemy is drowning in the same rigged game",
        "Only sacrifice creates the moral authority that actually breaks systems"
      ],
      "keywords": ["leaving big tech", "purpose driven career", "career change", "tech to impact"]
    },
    {
      "name": "Outdoor Equity as Social Infrastructure",
      "description": "Co-founded Outdoorithm (for-profit) and Outdoorithm Collective (nonprofit) because nature is one of the most powerful equalizers we have.",
      "talking_points": [
        "107 family camping trips, father of four daughters ages 4-16",
        "Built AI-powered camping platform (Outdoorithm) and free community trips (Collective)",
        "SF Foundation board member, bringing outdoor equity perspective to Bay Area philanthropy",
        "When a campervan got stuck, everyone grabbed shovels. The wilderness does not check LinkedIn profiles."
      ],
      "keywords": ["outdoor equity", "nature access", "family camping", "social infrastructure"]
    },
    {
      "name": "Faith and Values at Work",
      "description": "UVA-trained chemical engineer turned HBS MBA turned philanthropist. Married to an ordained minister. Faith shapes how he builds.",
      "talking_points": [
        "You cannot build a society with people you will not sacrifice for",
        "Everyone feels unsafe. The system is working exactly as designed.",
        "Headwinds/tailwinds asymmetry: we feel every obstacle, forget every advantage",
        "How long will we keep fighting each other for scraps while the table stays exactly where it has always been?"
      ],
      "keywords": ["values leadership", "faith and work", "social justice", "moral leadership"]
    },
    {
      "name": "Founder Hustle",
      "description": "Running two startups, sitting on a major foundation board, raising four kids, and camping every other weekend. Building at the intersection of everything.",
      "talking_points": [
        "Kindora (AI for nonprofits) + Outdoorithm (AI for camping) + Outdoorithm Collective (free trips)",
        "True Steele LLC consulting practice for fractional Chief Impact Officer work",
        "When weather apps failed our group camping trips, built his own app in half a day",
        "Previous: Bain consultant, Bridgespan, Year Up leadership, HBS+HKS dual degree"
      ],
      "keywords": ["founder story", "startup hustle", "serial entrepreneur", "social enterprise"]
    }
  ],
  "writing_samples": [
    {
      "text": "Everyone feels unsafe. That is the point. Jewish students say they do not feel safe on campus. Black students think: Welcome to America, we never felt safe. Conservative employees say they are silenced. Progressive employees say they are gaslit. The system is not broken. It is working exactly as designed to make everyone feel precarious except the truly powerful. I had one of those tickets for a decade. Made millions at Google. Gave it up. Now I am back to doing impact work for a fraction of that.",
      "source": "LinkedIn - Everyone Feels Unsafe (49K impressions)"
    },
    {
      "text": "Researchers discovered something they call the headwinds/tailwinds asymmetry. We feel every bit of wind pushing against us. But the wind at our back? We forget it is even there. I biked to work for 15 years through everything. Snow, bomb cyclones, atmospheric rivers. I know headwinds. Fighting up Oakland hills into Diablo winds, counting every pedal stroke, cursing every gust. But when that same wind pushed me home? I would forget it existed after the first block.",
      "source": "LinkedIn - Headwinds/Tailwinds (follow-up post)"
    },
    {
      "text": "If nonprofits do not harness AI, others will, shaping outcomes without our values or communities in mind. I co-founded Outdoorithm as a for-profit social enterprise because I doubted nonprofit funding would scale to meet the demands of running an AI-powered social impact platform. After years leading nonprofits and directing grantmaking at Google.org, I have repeatedly watched funders hesitate to make the sustained infrastructure and talent investments that great technology requires.",
      "source": "LinkedIn - AI for Nonprofits post"
    },
    {
      "text": "When weather apps failed our Outdoorithm group camping trips, I built my own app in half a day. But that is nothing compared to what is coming. I am building new things with AI every single day, and I am constantly blown away by what these tools can do and how fast they are evolving.",
      "source": "LinkedIn - AI Revolution post"
    }
  ],
  "past_appearances": [
    {
      "podcast_name": "Wantrepreneur to Entrepreneur",
      "episode_title": "TBD",
      "date": "2026",
      "url": null,
      "notes": "Recent appearance"
    }
  ]
}
```

---

## Podcast Index API Reference

**Base URL:** `https://api.podcastindex.org/api/1.0`

**Auth headers (required on every request):**
```
X-Auth-Key: {PODCAST_INDEX_API_KEY}
X-Auth-Date: {unix_epoch_seconds}
Authorization: {sha1_hash_of(api_key + api_secret + unix_epoch_seconds)}
User-Agent: TrueSteelePodcastOutreach/1.0
```

**Key endpoints:**
- `GET /search/byterm?q={term}&max=100` - Search podcasts by keyword
- `GET /podcasts/byfeedid?id={feed_id}` - Get podcast by feed ID
- `GET /episodes/byfeedid?id={feed_id}&max=10` - Get recent episodes

**Free tier:** Unlimited requests, just need API key from https://api.podcastindex.org

**iTunes Search API:**
- `GET https://itunes.apple.com/search?term={term}&entity=podcast&limit=50`
- Rate limit: 20 requests/minute, use 1s delay between calls
- No API key needed

---

## Search Terms by Speaker

**Sally keywords:**
"camping families", "outdoor family", "parenting outdoors", "Black motherhood", "outdoor equity", "nature spirituality", "faith nature", "women outdoors", "family adventure", "camping with kids", "outdoor community", "nature belonging", "sacred space nature", "outdoor ministry"

**Justin keywords:**
"social impact", "philanthropy", "nonprofit technology", "AI social good", "corporate responsibility", "tech for good", "founder story", "leaving big tech", "AI nonprofits", "grantmaking", "social enterprise", "outdoor equity", "purpose driven career"

---

## AI Writing Rules (MUST be included in all pitch generation prompts)

```
RULES (non-negotiable):
1. Zero em dashes. Use periods, commas, or colons instead.
2. No significance padding: "underscores the importance", "testament to",
   "pivotal moment", "broader landscape"
3. No stacked negative-parallel structures ("not X but Y" repeated)
4. No present-participle pileups at sentence ends ("fostering, enabling, enhancing")
5. No "serves as", "showcases", "represents" - use is/are/has
6. No "experts say", "many believe", "research shows" unless citing specifics
7. Vary sentence length. Allow fragments. Use contractions naturally.
8. Leave 1-2 small imperfections for authenticity
9. Reference a SPECIFIC recent episode by name
10. Suggest 2-3 concrete episode topic ideas
11. Keep under 200 words total
12. No "I hope this email finds you well" or similar cliches
13. Sound like a real person writing a real email, not a pitch template
```

---

## User Stories

### US-001: Database Schema & Migration
**Priority:** 1
**Status:** [x] Complete

**Description:**
Create the Supabase migration with all 5 tables (speaker_profiles, podcast_targets, podcast_episodes, podcast_pitches, podcast_campaigns) and indexes. Run the migration.

**Files to create:**
- `supabase/migrations/20260412_add_podcast_outreach.sql`

**Acceptance Criteria:**
- [ ] Migration file created with exact schema from Database Schema section above
- [ ] Migration runs successfully: `SUPABASE_ACCESS_TOKEN=$SB_PAT supabase db push --project-ref ypqsrejrsocebnldicke`
- [ ] All 5 tables exist in the database
- [ ] All 4 indexes created

**Verification:**
```bash
cd /Users/Justin/Code/TrueSteele/contacts
SUPABASE_ACCESS_TOKEN=$SB_PAT supabase db push --project-ref ypqsrejrsocebnldicke
```

---

### US-002: Seed Speaker Profiles
**Priority:** 2
**Status:** [x] Complete

**Description:**
Create a Python script to seed Sally and Justin's speaker profiles into the `speaker_profiles` table. Use the exact profile data from the "Speaker Profile Seed Data" section above.

**Files to create:**
- `scripts/intelligence/seed_speaker_profiles.py`

**Pattern:**
```python
# Follow write_campaign_copy.py conventions
# - load_dotenv with absolute path
# - argparse (--test flag for dry run)
# - supabase client from env vars
# - upsert by slug
```

**Acceptance Criteria:**
- [ ] Script created following existing Python patterns
- [ ] Sally's profile seeded with all 6 topic pillars, 4 writing samples, 1 past appearance
- [ ] Justin's profile seeded with all 6 topic pillars, 4 writing samples, 1 past appearance
- [ ] Script is idempotent (can run multiple times via upsert on slug)
- [ ] Runs successfully: `source .venv/bin/activate && python scripts/intelligence/seed_speaker_profiles.py`

**Verification:**
```bash
cd /Users/Justin/Code/TrueSteele/contacts
source .venv/bin/activate
python scripts/intelligence/seed_speaker_profiles.py
```

---

### US-003: Podcast Index API Client
**Priority:** 3
**Status:** [x] Complete

**Description:**
Create a Python module with a Podcast Index API client that handles auth (SHA-1 hash), search by term, and episode fetching. Also include an iTunes Search wrapper. This is a shared utility used by the discovery and enrichment scripts.

**Files to create:**
- `scripts/intelligence/podcast_api.py`

**Implementation details:**
```python
import hashlib, time, requests

class PodcastIndexClient:
    BASE_URL = "https://api.podcastindex.org/api/1.0"

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    def _headers(self) -> dict:
        epoch = str(int(time.time()))
        hash_input = self.api_key + self.api_secret + epoch
        auth_hash = hashlib.sha1(hash_input.encode()).hexdigest()
        return {
            "X-Auth-Key": self.api_key,
            "X-Auth-Date": epoch,
            "Authorization": auth_hash,
            "User-Agent": "TrueSteelePodcastOutreach/1.0"
        }

    def search_by_term(self, term: str, max_results: int = 100) -> list:
        # GET /search/byterm?q={term}&max={max}
        ...

    def get_episodes(self, feed_id: int, max_results: int = 10) -> list:
        # GET /episodes/byfeedid?id={feed_id}&max={max}
        ...

def search_itunes(term: str, limit: int = 50) -> list:
    # GET https://itunes.apple.com/search?term={term}&entity=podcast&limit={limit}
    # 1 second delay between calls (20 req/min rate limit)
    ...
```

**Acceptance Criteria:**
- [ ] PodcastIndexClient class with auth header generation
- [ ] search_by_term method returns list of podcast dicts
- [ ] get_episodes method returns list of episode dicts
- [ ] search_itunes function returns list of podcast dicts
- [ ] Proper error handling for API failures
- [ ] Test with: `python -c "from scripts.intelligence.podcast_api import PodcastIndexClient; print('OK')"`

**Verification:**
```bash
cd /Users/Justin/Code/TrueSteele/contacts
source .venv/bin/activate
python -c "from scripts.intelligence.podcast_api import PodcastIndexClient; print('import OK')"
```

---

### US-004: Podcast Discovery Script
**Priority:** 4
**Status:** [x] Complete

**Description:**
Create `discover_podcasts.py` that searches Podcast Index and iTunes for podcasts matching Sally and Justin's topics, deduplicates results using GPT-5.4 mini (NOT regex), filters out inactive shows, and saves to `podcast_targets`.

**Files to create:**
- `scripts/intelligence/discover_podcasts.py`

**CLI interface:**
```
python scripts/intelligence/discover_podcasts.py \
  --speaker sally|justin|both \
  --search-terms "camping,outdoor family" \  # optional override
  --limit 200 \                               # max results per term
  --test                                      # dry run, print don't save
```

**Pipeline:**
1. Load search terms for selected speaker from hardcoded lists (see "Search Terms by Speaker" above)
2. Search Podcast Index API for each term
3. Search iTunes API for each term (supplemental)
4. Deduplicate using GPT-5.4 mini (pass pairs of title+author, ask if same podcast)
5. Filter: skip podcasts with language != 'en'
6. Save to `podcast_targets` table (upsert on podcast_index_id)
7. Print summary: total found, duplicates removed, saved count

**Dedup with GPT-5.4 mini (NOT regex):**
```python
# Use structured output to compare potential duplicates
# System: "You are a podcast deduplication expert."
# User: "Are these the same podcast? A: {title_a} by {author_a}. B: {title_b} by {author_b}"
# Response schema: {"is_duplicate": bool, "confidence": float}
```

**Acceptance Criteria:**
- [ ] Script searches Podcast Index and iTunes APIs
- [ ] Deduplication uses GPT-5.4 mini (no regex matching)
- [ ] Inactive shows filtered (no episode in 90 days, based on API data)
- [ ] Results saved to podcast_targets table
- [ ] --test flag prints results without saving
- [ ] Runs: `python scripts/intelligence/discover_podcasts.py --speaker sally --test --limit 10`

---

### US-005: RSS Enrichment Script
**Priority:** 5
**Status:** [ ] Incomplete

**Description:**
Create `enrich_podcasts.py` that fetches RSS feeds for discovered podcasts, extracts host emails, parses recent episodes, verifies emails with ZeroBounce, and classifies activity status.

**Files to create:**
- `scripts/intelligence/enrich_podcasts.py`

**CLI interface:**
```
python scripts/intelligence/enrich_podcasts.py \
  --limit 50 \        # max podcasts to enrich
  --workers 20 \       # concurrent RSS fetchers
  --skip-verify \      # skip ZeroBounce (saves credits)
  --test               # dry run
```

**Pipeline:**
1. Load un-enriched podcasts from `podcast_targets` (WHERE enriched_at IS NULL)
2. Fetch RSS feed XML for each (concurrent, 20 workers)
3. Parse RSS to extract:
   - `<itunes:owner><itunes:email>` (host email)
   - `<itunes:author>` (host name)
   - Last 5 episodes: title, description, date, duration
   - `<itunes:category>` tags
4. Classify activity: active (<30 days), slow (30-90 days), podfaded (>90 days)
5. Save episodes to `podcast_episodes` table
6. If email found and --skip-verify not set, verify with ZeroBounce
   - Pattern from `scripts/intelligence/find_emails.py`
7. Update `podcast_targets` with enriched data

**Acceptance Criteria:**
- [ ] Fetches and parses RSS XML feeds
- [ ] Extracts host email from `<itunes:owner>` or `<itunes:email>`
- [ ] Saves last 5 episodes per podcast to `podcast_episodes`
- [ ] Activity status classified correctly
- [ ] ZeroBounce verification works (with --skip-verify option)
- [ ] Runs: `python scripts/intelligence/enrich_podcasts.py --limit 5 --skip-verify`

---

### US-006: AI Fit Scoring Script
**Priority:** 6
**Status:** [ ] Incomplete

**Description:**
Create `score_podcast_fit.py` that uses GPT-5.4 mini structured output to score how well each podcast fits a speaker's topic pillars. Pattern directly adapted from Kindora's `nano_fit_scorer.py`.

**Files to create:**
- `scripts/intelligence/score_podcast_fit.py`

**CLI interface:**
```
python scripts/intelligence/score_podcast_fit.py \
  --speaker sally|justin \
  --limit 50 \
  --workers 50 \
  --min-episodes 3 \  # skip podcasts with fewer episodes
  --test
```

**GPT-5.4 mini structured output schema:**
```python
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "podcast_fit_score",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "fit_tier": {"type": "string", "enum": ["strong", "moderate", "weak"]},
                "fit_score": {"type": "number"},
                "fit_rationale": {"type": "string"},
                "matching_pillars": {"type": "array", "items": {"type": "string"}},
                "episode_hooks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "episode_title": {"type": "string"},
                            "angle": {"type": "string"}
                        },
                        "required": ["episode_title", "angle"],
                        "additionalProperties": False
                    }
                },
                "suggested_episode_ideas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["title", "description"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["fit_tier", "fit_score", "fit_rationale", "matching_pillars", "episode_hooks", "suggested_episode_ideas"],
            "additionalProperties": False
        }
    }
}
```

**System prompt:**
```
You are a podcast booking expert evaluating whether a podcast is a good
fit for a speaker. Score the fit based on topic alignment, audience
relevance, and how naturally the speaker's expertise connects to the
podcast's content. Consider recent episodes to identify specific
conversation angles.

Score 0.0-1.0 where:
- 0.8-1.0 = strong (clear topic overlap, audience match)
- 0.5-0.79 = moderate (some overlap, could work with right angle)
- 0.0-0.49 = weak (poor fit, forced connection)
```

**Pipeline:**
1. Load speaker profile from `speaker_profiles`
2. Load unscored podcasts (LEFT JOIN podcast_pitches WHERE fit_tier IS NULL)
3. For each podcast, include recent episodes from `podcast_episodes`
4. Call GPT-5.4 mini with structured output (50 concurrent workers)
5. Save to `podcast_pitches` (fit fields only, pitch copy comes later)

**Acceptance Criteria:**
- [ ] GPT-5.4 mini structured output with strict JSON schema
- [ ] Scores saved to podcast_pitches table
- [ ] Distribution of strong/moderate/weak tiers looks reasonable
- [ ] --test prints results without saving
- [ ] Runs: `python scripts/intelligence/score_podcast_fit.py --speaker sally --limit 5 --test`

---

### US-007: Pitch Generation Script
**Priority:** 7
**Status:** [ ] Incomplete

**Description:**
Create `generate_podcast_pitches.py` that uses Claude Sonnet 4.6 to generate personalized podcast pitch emails in the speaker's authentic voice. Uses writing samples for voice matching.

**Files to create:**
- `scripts/intelligence/generate_podcast_pitches.py`

**CLI interface:**
```
python scripts/intelligence/generate_podcast_pitches.py \
  --speaker sally|justin \
  --tier strong,moderate \  # which fit tiers to generate for
  --limit 20 \
  --workers 10 \
  --test
```

**Claude Sonnet 4.6 system prompt (for Sally):**
```
You are writing a podcast pitch email from Sally Steele to a podcast host.
Sally is CEO of Outdoorithm, Board Chair of Outdoorithm Collective, an
ordained minister, a Black mother of four, and has been on 107 family
camping trips. Write in her authentic voice using her writing samples below.

VOICE GUIDE:
- Direct, opinionated, specific, occasionally poetic
- Uses fragments for emphasis
- Names real people, places, numbers
- Uses contrast to reveal truth
- Anchored in real scenes and moral tension

WRITING SAMPLES:
{insert writing samples from speaker profile}

RULES (non-negotiable):
{insert AI Writing Rules from above}

Write the pitch email. Include:
1. Subject line (under 60 chars, specific, not clickbait)
2. Alternative subject line
3. Pitch body (under 200 words)
4. Reference to a specific recent episode
5. 2-3 concrete episode topic ideas they could record together
```

**For Justin, adjust the system prompt with his profile and voice.**

**Pipeline:**
1. Load speaker profile + writing samples from `speaker_profiles`
2. Load strong/moderate fit scores from `podcast_pitches` (WHERE pitch_body IS NULL)
3. For each, load episode hooks from the fit scoring step
4. Call Claude Sonnet 4.6 via Anthropic SDK (10 concurrent workers)
5. Parse response into subject_line, subject_line_alt, pitch_body, episode_reference, suggested_topics
6. Save to `podcast_pitches` table
7. Run AI-tell audit: verify zero em dashes, no banned phrases

**Anthropic SDK usage:**
```python
from anthropic import Anthropic

client = Anthropic()  # uses ANTHROPIC_API_KEY env var
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}]
)
```

**Acceptance Criteria:**
- [ ] Claude Sonnet 4.6 generates pitches via Anthropic SDK
- [ ] Each pitch has subject line, alt subject, body, episode reference, suggested topics
- [ ] Zero em dashes in any generated pitch
- [ ] No banned AI phrases (check against rules list)
- [ ] Pitches are under 200 words
- [ ] Voice matches writing samples (reads like Sally/Justin, not a template)
- [ ] Runs: `python scripts/intelligence/generate_podcast_pitches.py --speaker sally --limit 3 --test`

---

### US-008: Next.js API Routes - Discovery & Scoring
**Priority:** 8
**Status:** [ ] Incomplete

**Description:**
Create Next.js API routes for podcast discovery and scoring that the UI will call.

**Files to create:**
- `job-matcher-ai/app/api/podcast/discover/route.ts`
- `job-matcher-ai/app/api/podcast/score/route.ts`
- `job-matcher-ai/app/api/podcast/status/route.ts`

**`/api/podcast/discover` (GET):**
- Query params: `speaker`, `status`, `fit_tier`, `search`, `page`, `limit`
- Returns: paginated list of podcast_targets with joined fit scores
- Join podcast_pitches for fit_tier if available

**`/api/podcast/score` (POST):**
- Body: `{ podcast_ids: number[], speaker_slug: string }`
- Triggers fit scoring for selected podcasts
- Calls the Python script via child_process or direct Supabase operations
- Returns: `{ status: "started", count: number }`

**`/api/podcast/status` (GET):**
- Returns campaign dashboard stats:
  - Total podcasts discovered
  - Scored count by tier
  - Pitches generated/approved/sent
  - Campaign outcomes (booked, declined, no_response)

**Pattern:** Follow `app/api/network-intel/campaign/send/route.ts` conventions:
- Import supabase from `@/lib/supabase`
- Use NextResponse
- Error handling with try/catch

**Acceptance Criteria:**
- [ ] GET /api/podcast/discover returns paginated podcast list
- [ ] POST /api/podcast/score accepts podcast IDs and speaker
- [ ] GET /api/podcast/status returns campaign stats
- [ ] All routes use Supabase client from lib/supabase
- [ ] Verify: `cd job-matcher-ai && npx tsc --noEmit` passes

---

### US-009: Next.js API Routes - Generate & Send
**Priority:** 9
**Status:** [ ] Incomplete

**Description:**
Create Next.js API routes for pitch generation and Gmail sending.

**Files to create:**
- `job-matcher-ai/app/api/podcast/generate/route.ts`
- `job-matcher-ai/app/api/podcast/send/route.ts`

**`/api/podcast/generate` (POST):**
- Body: `{ pitch_ids: number[] }` or `{ podcast_id: number, speaker_slug: string }`
- Generates pitch copy using Claude Sonnet 4.6 (inline, not Python script)
- Uses Anthropic SDK (`@anthropic-ai/sdk`)
- Applies all AI writing rules from the system prompt
- Returns generated pitch with subject, body, episode reference, topics

**`/api/podcast/send` (POST):**
- Body: `{ pitch_id: number, method: "gmail_draft" | "direct_send" | "manual" }`
- For gmail_draft/direct_send: uses Gmail API pattern from campaign/send route
- Sally pitches from: `sally@outdoorithmcollective.org` (or configured email)
- Justin pitches from: `justin@truesteele.com`
- Creates podcast_campaigns record with send tracking
- For "manual": just marks as sent with timestamp

**Gmail send pattern (from existing codebase):**
```typescript
// Follow the pattern in app/api/network-intel/campaign/send/route.ts
// Uses Google OAuth credentials for the sender's account
// Creates draft or sends directly via Gmail API
```

**Acceptance Criteria:**
- [ ] POST /api/podcast/generate creates pitch via Claude Sonnet 4.6
- [ ] POST /api/podcast/send sends via Gmail API or marks as manual
- [ ] Campaign record created in podcast_campaigns on send
- [ ] TypeScript compiles: `cd job-matcher-ai && npx tsc --noEmit`

---

### US-010: UI - Speaker Profiles Tab
**Priority:** 10
**Status:** [ ] Incomplete

**Description:**
Create the main podcast outreach page with Tab 1 showing speaker profiles.

**Files to create:**
- `job-matcher-ai/app/tools/podcast-outreach/page.tsx`

**UI Pattern:** Follow `app/tools/campaign/page.tsx`:
- 'use client' directive
- shadcn Tabs component for 4 tabs
- For this story, only implement Tab 1 (Speaker Profiles)
- Other tabs show "Coming soon" placeholder

**Tab 1 - Speaker Profiles:**
- Fetch profiles from `/api/podcast/discover?type=profiles` or direct Supabase query
- Card layout for Sally and Justin
- Each card shows: name, headline, photo placeholder, bio
- Topic pillars as expandable sections with talking points
- Past appearances list
- Writing samples preview (collapsible)

**Components to use:** Badge, Button, Card, CardContent, CardHeader, Tabs, TabsContent, TabsList, TabsTrigger, ScrollArea

**Acceptance Criteria:**
- [ ] Page renders at `/tools/podcast-outreach`
- [ ] 4 tabs visible: Speaker Profiles, Discovery, Pitch Review, Campaign Tracker
- [ ] Speaker Profiles tab shows Sally and Justin cards
- [ ] Topic pillars expandable with talking points
- [ ] No TypeScript errors: `cd job-matcher-ai && npx tsc --noEmit`

---

### US-011: UI - Discovery & Scoring Tab
**Priority:** 11
**Status:** [ ] Incomplete

**Description:**
Implement Tab 2 (Podcast Discovery & Matching) with search, results table, and scoring controls.

**Files to modify:**
- `job-matcher-ai/app/tools/podcast-outreach/page.tsx`

**Tab 2 - Podcast Discovery:**
- Search bar for keyword discovery
- Results table columns: podcast name, host, episode count, last episode date, activity status, fit tier, fit score
- Filter by: fit tier (strong/moderate/weak/unscored), activity status (active/slow/podfaded)
- Sort by: fit score, episode count, last episode date
- Checkbox selection for bulk actions
- "Score Selected" button (calls /api/podcast/score)
- "Discover More" button with search terms input
- Pagination

**Badge colors for fit tiers:**
- strong: green
- moderate: yellow
- weak: red
- unscored: gray

**Acceptance Criteria:**
- [ ] Search bar triggers podcast discovery
- [ ] Results table with all specified columns
- [ ] Filters work for fit tier and activity status
- [ ] Bulk "Score Selected" calls API
- [ ] Pagination works
- [ ] No TypeScript errors

---

### US-012: UI - Pitch Review Tab
**Priority:** 12
**Status:** [ ] Incomplete

**Description:**
Implement Tab 3 (Pitch Review) with pitch cards, inline editing, approve/reject, and send controls.

**Files to modify:**
- `job-matcher-ai/app/tools/podcast-outreach/page.tsx`

**Tab 3 - Pitch Review:**
- List of generated pitches grouped by speaker (Sally / Justin toggle)
- Each pitch card shows:
  - Podcast name, fit tier badge, fit score
  - Subject line (editable inline)
  - Pitch body preview (click to expand)
  - Episode reference
  - Suggested topics
  - Status badge (draft/approved/sent/replied/booked)
- Expanded view: full pitch body, editable textarea
- Action buttons: Approve, Reject, Generate (if no pitch yet), Send
- Send options: Gmail Draft, Direct Send, Manual
- Filter by: pitch status, fit tier

**Acceptance Criteria:**
- [ ] Pitch cards render with all fields
- [ ] Inline edit for subject line and pitch body
- [ ] Approve/reject updates pitch_status
- [ ] Send button with method selection (draft/direct/manual)
- [ ] Filter by status works
- [ ] No TypeScript errors

---

### US-013: UI - Campaign Tracker Tab
**Priority:** 13
**Status:** [ ] Incomplete

**Description:**
Implement Tab 4 (Campaign Tracker) with pipeline dashboard and outcome tracking.

**Files to modify:**
- `job-matcher-ai/app/tools/podcast-outreach/page.tsx`

**Tab 4 - Campaign Tracker:**
- Dashboard stats cards: Total Sent, Open Rate, Reply Rate, Booked Count
- Pipeline visualization: Draft -> Approved -> Sent -> Opened -> Replied -> Booked (counts at each stage)
- Table: podcast name, speaker, sent date, status/outcome, notes
- Notes field per podcast (editable, saves to podcast_campaigns.notes)
- Outcome dropdown: booked, declined, no_response, maybe_later

**Acceptance Criteria:**
- [ ] Dashboard stats cards render
- [ ] Pipeline shows counts at each stage
- [ ] Table with all campaigns
- [ ] Notes field saves inline
- [ ] Outcome dropdown updates campaign
- [ ] No TypeScript errors
- [ ] Final deploy: `cd job-matcher-ai && npx vercel --prod --yes --scope true-steele`

---

## Verification Plan

After all stories complete:
1. All 5 tables exist in Supabase
2. Speaker profiles seeded for Sally and Justin
3. `discover_podcasts.py --speaker sally --test --limit 5` prints results
4. `enrich_podcasts.py --limit 3 --skip-verify` enriches RSS data
5. `score_podcast_fit.py --speaker sally --limit 3 --test` scores fit
6. `generate_podcast_pitches.py --speaker sally --limit 2 --test` generates pitches with zero em dashes
7. `/tools/podcast-outreach` loads with all 4 tabs functional
8. App deployed to Vercel successfully
