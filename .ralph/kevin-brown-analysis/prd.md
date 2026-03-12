# Project: Kevin L. Brown LinkedIn Content Analysis — Kindora Application

## Overview

Deep analysis of Kevin L. Brown's 100 LinkedIn posts (Nov 2024 – Feb 2026) to deconstruct what makes his content work at scale (avg 463 engagement, top post 3,134). Kevin is a nonprofit fundraising/comms thought leader with massive LinkedIn reach. The goal: identify which rhetorical devices, framing patterns, content formats, and core messages drive the most engagement — then translate those insights into actionable content strategy for Kindora.

## Technical Context

- **Data source:** `influencer_posts` table on Supabase (supabase-contacts MCP server)
- **100 posts** scraped via Apify, Nov 2024 – Feb 2026
- **23,456 reactions** in `influencer_post_reactions` table (13,167 unique reactors)
- **256 contacts** in Justin's DB engage with Kevin's posts (warm intro targets)
- **Media types:** 61 text posts (avg 539 engagement), 39 carousel posts (avg 345 engagement)
- **Python venv:** `.venv/` — activate with `source .venv/bin/activate`
- **Env vars:** `OPENAI_APIKEY` (no underscore before KEY), `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- **MCP server:** `supabase-contacts` (NOT `supabase_crm`) for SQL queries
- **Output:** Analysis markdown doc at `docs/KEVIN_BROWN_CONTENT_ANALYSIS.md`
- **Kindora context:** Justin is Co-Founder & CEO of Kindora (outdoor education matching platform for families, launched Apr 2025). Kindora needs a LinkedIn content strategy targeting parents, educators, and outdoor program operators.

## About Kevin L. Brown

Kevin L. Brown is a nonprofit communications and fundraising strategist with a large LinkedIn following (~30K+ followers based on reaction volume). He posts consistently about:
- Nonprofit storytelling and communications strategy
- Fundraising best practices and donor engagement
- Advocacy and activism in the social sector
- Visual storytelling and creative campaign design
- Sector trends (USAID cuts, AI in nonprofits, etc.)

His content consistently goes viral in the nonprofit/social impact space. Understanding WHY is the core goal of this analysis.

## User Stories

### US-001: Extract and Catalog All Post Content
**Priority:** 1
**Status:** [x] Complete

**Description:**
Pull all 100 posts from the database and create a structured catalog with engagement metrics. This becomes the raw dataset for all subsequent analysis.

**Acceptance Criteria:**
- [x] Query `influencer_posts` for all Kevin Brown posts with: post_content, post_date, engagement_likes, engagement_comments, engagement_shares, engagement_total, media_type
- [x] Create a Python analysis script at `scripts/intelligence/analyze_kevin_brown.py` that:
  - Loads all posts from Supabase
  - Computes per-post metrics: engagement rate, comment-to-like ratio, share-to-like ratio
  - Categorizes posts by length bucket: short (<300 chars), medium (300-800), long (800-1500), very long (1500+)
  - Saves structured JSON catalog to `docs/kevin_brown_posts_catalog.json`
- [x] Print summary stats: total posts, date range, engagement distribution (min/avg/median/max/p75/p90), length distribution

**Notes:**
- This is the foundational data step — all subsequent stories build on this catalog
- Include the full post text in the JSON for GPT analysis in later stories
- Use Supabase REST client via supabase-py

---

### US-002: Content Theme & Core Message Analysis (GPT-5 mini)
**Priority:** 2
**Status:** [x] Complete

**Description:**
Use GPT-5 mini to analyze every post and extract: primary theme, core message, content category, emotional appeal, and target audience. Then aggregate to find Kevin's dominant themes and which themes drive the most engagement.

**Acceptance Criteria:**
- [x] Add GPT analysis to `analyze_kevin_brown.py` (or extend it)
- [x] For each post, GPT-5 mini extracts (structured output via Pydantic):
  - `primary_theme`: one of [storytelling, fundraising_strategy, donor_psychology, advocacy_activism, visual_creative, sector_trends, leadership, events_conferences, ai_technology, career_advice, other]
  - `core_message`: 1-sentence summary of the post's central argument or insight
  - `content_category`: one of [educational, inspirational, contrarian, curated_resource, listicle, case_study, hot_take, call_to_action]
  - `emotional_appeal`: one of [outrage, aspiration, humor, empathy, urgency, curiosity, pride, fear]
  - `target_audience`: one of [fundraisers, nonprofit_leaders, comms_professionals, donors, general_social_impact]
  - `rhetorical_devices`: list of devices used (see US-003 for full taxonomy)
- [x] Aggregate results:
  - Theme × avg engagement table (sorted by engagement)
  - Content category × avg engagement table
  - Emotional appeal × avg engagement table
  - Target audience × avg engagement table
  - Top 10 core messages by engagement
- [x] Save analysis results to the JSON catalog (enrich each post object)
- [x] Print the aggregation tables to stdout

**Notes:**
- Use ThreadPoolExecutor with 150 workers for parallel GPT calls
- GPT-5 mini does NOT support temperature=0, use default
- Cost estimate: ~100 posts × ~1K tokens each = ~$0.02 total
- The theme taxonomy should capture Kevin's actual content universe, not generic categories

---

### US-003: Rhetorical Device & Framing Deep-Dive (GPT-5 mini)
**Priority:** 3
**Status:** [x] Complete

**Description:**
Analyze every post for specific rhetorical devices, framing techniques, and structural patterns. This is the "how" behind Kevin's success — not just what he says, but HOW he says it.

**Acceptance Criteria:**
- [x] For each post, GPT-5 mini identifies (extend Pydantic schema):
  - `opening_hook`: one of [provocative_statement, question, statistic, quote, emoji_hook, story_opening, list_preview, contrarian_claim, imperative_command]
  - `structural_pattern`: one of [problem_solution, list_format, narrative_arc, before_after, myth_bust, build_to_reveal, call_and_response, parallel_structure]
  - `rhetorical_devices`: list from [anaphora, antithesis, tricolon, amplification, irony, metaphor, analogy, rhetorical_question, repetition, enumeration, juxtaposition, hyperbole, understatement, personification, alliteration]
  - `framing_technique`: one of [reframing, anchor_then_shift, common_enemy, identity_appeal, scarcity, social_proof, authority, contrast, storytelling_frame]
  - `call_to_action`: one of [none, follow_for_more, comment_below, share_this, save_this, link_in_comments, tag_someone, dm_me]
  - `tone`: one of [authoritative, conversational, passionate, analytical, playful, urgent, reflective]
  - `line_break_style`: one of [single_sentence_lines, short_paragraphs, mixed, long_paragraphs]
  - `uses_emoji`: bool
  - `uses_bold_unicode`: bool (the 𝗯𝗼𝗹𝗱 text technique)
  - `has_hook_gap`: bool (line 1 is a hook, then blank line before content)
- [x] Aggregate results:
  - Opening hook type × avg engagement (which hooks work best?)
  - Structural pattern × avg engagement
  - Most common rhetorical device combinations (top 10 combos)
  - Framing technique × avg engagement
  - CTA × avg engagement
  - Tone × avg engagement
  - Bold unicode usage: engagement with vs without
  - Emoji usage: engagement with vs without
  - Hook gap: engagement with vs without
- [x] Save to JSON catalog
- [x] Print all aggregation tables

**Notes:**
- This is the most detailed analysis — the taxonomy should be comprehensive
- Pay special attention to Kevin's "signature moves" — patterns he uses repeatedly that always perform
- The combination of devices matters more than individual devices

---

### US-004: Length, Format & Timing Optimization
**Priority:** 4
**Status:** [x] Complete

**Description:**
Analyze the relationship between post characteristics (length, format, posting time/day) and engagement. Find the optimal content formula.

**Acceptance Criteria:**
- [x] Length analysis:
  - Scatter plot data: content_length vs engagement_total (saved as CSV for optional visualization)
  - Engagement by length bucket: short/medium/long/very_long with avg, median, max
  - Optimal length range identification (which bucket consistently performs?)
  - Character count of first line (hook length) vs engagement
- [x] Format analysis:
  - Text vs carousel: engagement breakdown (likes, comments, shares separately)
  - Comment-to-like ratio by format (which format drives more conversation?)
  - Share-to-like ratio by format (which format gets shared more?)
- [x] Timing analysis:
  - Day of week × avg engagement
  - Posting frequency: posts per week over time, engagement trend over time
- [x] Cross-tabulation:
  - Theme × format × engagement (which themes work better as text vs carousel?)
  - Length × theme × engagement (do some themes need more or fewer words?)
- [x] Save all analysis to the JSON catalog and print tables

**Notes:**
- Timing data may be limited since we only have date, not exact post time
- The cross-tabs are the most valuable insight — they reveal Kevin's "content formulas"

---

### US-005: Kevin's Content Playbook — Signature Patterns
**Priority:** 5
**Status:** [x] Complete

**Description:**
Synthesize findings from US-002 through US-004 into Kevin's "content playbook" — the repeatable patterns that consistently drive high engagement. Use GPT to identify signature moves, viral formulas, and content templates.

**Acceptance Criteria:**
- [x] Use GPT-5 mini (or Claude Opus for quality) to synthesize all analysis data into:
  - **Kevin's Top 5 Signature Moves** — the specific rhetorical/structural patterns he uses most effectively
  - **Kevin's Viral Formula** — the combination of theme + hook + structure + length + tone that predicts high engagement
  - **Kevin's Content Calendar Pattern** — how he sequences themes and formats across weeks
  - **What DOESN'T Work** — themes, formats, or approaches that consistently underperform
  - **Audience Psychology** — what his audience responds to emotionally (based on reaction types and comment patterns)
- [x] For each signature move, include:
  - 3 example posts (with engagement numbers)
  - The specific technique explained
  - Why it works (psychological mechanism)
  - How to replicate it (template/formula)
- [x] Save as section in the JSON catalog
- [x] Print the full playbook summary

**Notes:**
- This is the high-level synthesis — it should read like a content strategy deck
- Focus on actionable patterns, not just observations
- The "why it works" should reference persuasion psychology (Cialdini, Kahneman, etc.)

---

### US-006: Kindora Content Strategy — Apply Kevin's Playbook
**Priority:** 6
**Status:** [x] Complete

**Description:**
Translate Kevin's successful patterns into a concrete LinkedIn content strategy for Kindora. Adapt his techniques to Kindora's audience (parents, educators, outdoor program operators) and mission (outdoor education matching).

**Acceptance Criteria:**
- [x] Create the master analysis document at `docs/KEVIN_BROWN_CONTENT_ANALYSIS.md` containing:
  - **Executive Summary** (1 page) — key findings and recommendations
  - **Kevin's Profile** — who he is, audience, posting cadence, overall engagement metrics
  - **Content Analysis** — themes, categories, emotional appeals with engagement data
  - **Rhetorical Analysis** — devices, framing, structural patterns with engagement data
  - **Format & Length Analysis** — optimal content formula
  - **Kevin's Playbook** — signature moves and viral formulas
  - **Kindora Content Strategy** — the adaptation section (below)
- [x] Kindora Content Strategy section includes:
  - **5 Kindora Content Pillars** — adapted from Kevin's top-performing themes, mapped to Kindora's mission
  - **10 Post Templates** — specific post structures Kindora can use, with placeholder text, adapted from Kevin's highest-performing patterns
  - **Kindora Voice Guide** — how to adapt Kevin's rhetorical style (provocative hooks, short lines, bold claims) while maintaining Justin's authentic voice
  - **Content Calendar Blueprint** — suggested weekly cadence with theme rotation
  - **Hook Library** — 20+ opening hooks adapted for Kindora topics (outdoor ed, family adventure, nature deficit, screen time vs nature, equity in outdoor access)
  - **Engagement Tactics** — which CTAs, emoji usage, formatting to adopt vs skip
- [x] The document should be comprehensive enough to hand to a content marketer and say "execute this"
- [x] Print a summary of the doc structure and key recommendations

**Notes:**
- The Kindora adaptation is the whole point — don't just analyze Kevin, translate for Justin
- Kindora's key topics: outdoor education access, family adventure, nature deficit disorder, screen time, equity in outdoor programming, matching families with programs
- Justin's LinkedIn: justinrichardsteele (~6K followers, 2.8K connections) — smaller audience but highly relevant network
- The post templates should be immediately usable — fill-in-the-blank, not abstract advice
- Reference Justin's voice (from CLAUDE.md): direct, punchy, sentence fragments, em dashes, conversational
