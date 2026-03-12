# The Grant Brief — Content Marketing System

**Last updated**: 2026-03-02
**Version**: 1.2 (first real run)
**Status**: Implemented, behind feature flag (`ENABLE_GRANT_BRIEF_CONTENT`)

---

## How It Works (Plain Language)

The Grant Brief is Kindora's automated content marketing engine. It finds interesting grants in our database, writes LinkedIn posts and newsletters about them, and publishes them to attract nonprofit professionals to Kindora.

**What it does every day:**
1. Looks through our database of 80,000+ grant programs and picks the best one for today's theme
2. Uses AI to write a LinkedIn post about that grant — in a helpful, non-salesy tone
3. Queues the post for an admin to review and approve before it goes live
4. Once approved, publishes it to the Kindora LinkedIn page

**What it does every week:**
1. Scrapes LinkedIn posts from 96 philanthropy thought leaders to find trending topics
2. Compiles the week's best content into a newsletter email
3. Sends the newsletter to subscribers via MailerLite every Tuesday at 8am ET

**The daily schedule:**
| Day | Theme | Content Type |
|-----|-------|-------------|
| Monday | Education & Youth | Grant Feature |
| Tuesday | Health & Human Services | Grant Feature |
| Wednesday | Funder Spotlight | Funder Spotlight (deep profile) |
| Thursday | Environment & Sustainability | Grant Feature |
| Friday | Arts, Culture & Community | Grant Feature |
| Saturday | Philanthropy Pulse | Influencer synthesis (posted from Justin's personal account) |
| Sunday | Week Ahead: Deadlines | Deadline Roundup |

**How content flows:**
```
AI generates draft → Admin reviews in dashboard → Approve or reject → Publish to LinkedIn
                                                                   → Include in weekly newsletter
```

**Cost:** ~$25-35/month total for AI, scraping, and email delivery.

---

## Admin Operations Guide

### Getting Started (First-Time Setup)

Before the system can run, these credentials must be configured in the API environment:

| Credential | Env Var | Where to Get It | Status |
|-----------|---------|-----------------|--------|
| LinkedIn OAuth | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_COMPANY_URN` | LinkedIn Developer Portal → Create app → Request Marketing API access | Not yet configured |
| MailerLite | `MAILERLITE_API_KEY`, `MAILERLITE_GROUP_NEWSLETTER` | MailerLite dashboard → Integrations → API | Not yet configured |
| Apify | `APIFY_API_KEY` | Apify Console → Settings → Integrations | Configured |
| Feature flag | `ENABLE_GRANT_BRIEF_CONTENT=true` | API `.env` file | Currently `false` |

Once credentials are set, flip the feature flag to `true` and restart the API. The Celery beat scheduler will start running the daily/weekly jobs automatically.

### Day-to-Day Admin Workflow

**The admin dashboard lives at**: `kindora-analytics` → `/grant-brief` (or click "Grant Brief" in the left nav).

**Daily routine (5-10 minutes):**

1. **Check the dashboard** — The stats cards at the top show:
   - Drafts Pending (blue) — new content waiting for review
   - Ready to Publish (amber) — approved but not yet published
   - Published This Week (green) — what's gone out
   - Total Content (gray)

2. **Review new drafts** — Click any row in the content list to open the detail modal
   - Read the headline and body
   - Check the AI enrichment data (collapsible section) for the scoring rationale
   - Edit the headline or body if needed (character count shown for LinkedIn's ~3000 limit)
   - Click **Approve** if it looks good, or **Reject** with a reason if not

3. **Publish approved content** — For approved items, click **Publish to LinkedIn**
   - Company posts (Mon-Fri, Sun) go directly to the Kindora LinkedIn page
   - Saturday posts are queued as "queued_for_personal" — Justin posts these manually from his personal account

4. **Use the calendar view** — Toggle to "Calendar" mode to see the week at a glance. Empty days have a "Generate" button to create content for that date.

**Weekly routine (newsletter, 10-15 minutes):**

1. Switch to the **Newsletter** tab
2. Click **Compose Next Edition** — this assembles the newsletter from the week's published content (~10-30 seconds)
3. **Preview** the HTML in the sandboxed iframe to check formatting
4. **Send** when satisfied — goes to all active MailerLite subscribers

**Influencer monitoring (weekly or as needed):**

1. Switch to the **Influencers** tab
2. Click **Seed & Scrape** with batch size 5-15 to pull latest LinkedIn posts (~30-120 seconds)
3. Click **Classify Posts** to run AI classification on new posts
4. The classified insights automatically feed into Saturday's "Philanthropy Pulse" content

### Content Generation

Content is generated in two ways:

**Automatic (via Celery beat):** Every day at 5am ET, the system generates a draft for today's theme. This runs the full 6-stage AI pipeline (search → score → diversify → enrich → select → write). Takes 10-30 seconds.

**Manual (via dashboard):** Click "Generate Content" in the dashboard header → pick a date → Generate. You can also generate a full week at once. Use the calendar view to spot empty days and fill them.

If content already exists for a date, generating again will create a second piece — it won't overwrite. You can then pick the better one and reject the other.

### Handling Common Situations

**Content doesn't look right:**
- Edit the headline and body directly in the detail modal, then save and approve
- Or reject it and generate a new piece for the same date

**Publish failed:**
- The content will show status `publish_failed` with an error. Common causes:
  - LinkedIn access token expired (expires every 60 days) — re-auth in LinkedIn Developer Portal and update `LINKEDIN_ACCESS_TOKEN`
  - LinkedIn rate limit (100 posts/day) — wait and retry
- Re-approve the content (sets it back to `approved`), then try publishing again

**No content generated for a day:**
- Check if `ENABLE_GRANT_BRIEF_CONTENT` is `true`
- Check if Celery beat is running (`celery -A core.celery_app beat`)
- Generate manually from the dashboard

**Newsletter didn't send:**
- Check MailerLite API key is valid
- Check that the edition status is "composed" (must compose before sending)
- Check the MailerLite dashboard for delivery issues

**Influencer scraping returned errors:**
- Some LinkedIn profiles may have privacy settings that block scraping — these show a `scrape_error` in the table
- The system will retry on the next scrape run
- Check Apify credit balance if all scrapes fail

### LinkedIn Token Refresh

LinkedIn access tokens expire every 60 days. When publishing starts failing with 401 errors:

1. Go to the LinkedIn Developer Portal
2. Re-authorize the app to get a new access token
3. Update `LINKEDIN_ACCESS_TOKEN` in the API `.env`
4. Restart the API

Future improvement: automated token refresh via OAuth refresh tokens.

### Content Status Reference

| Status | Meaning | What Can Happen Next |
|--------|---------|---------------------|
| `draft` | AI-generated, waiting for review | Approve, Reject, Edit, Delete |
| `approved` | Reviewed and ready to publish | Publish, Reject (change your mind) |
| `published` | Live on LinkedIn | View engagement data |
| `rejected` | Not suitable for publishing | Re-approve, Delete |
| `queued_for_personal` | Saturday content, waiting for manual post | Admin posts from personal LinkedIn |
| `publish_failed` | LinkedIn API error during publish | Re-approve, then try publishing again |

### Feature Flag

The entire system is gated behind `ENABLE_GRANT_BRIEF_CONTENT` in `core/config.py`:

- **When `false`** (current production state): All Celery tasks skip silently. All mutating API endpoints return 503. Read endpoints (content list, influencer list, newsletter list) still work. The admin dashboard is accessible but generation/publishing won't work.
- **When `true`**: Full system operational. Celery beat runs all scheduled jobs. All API endpoints active.

This allows the database, code, and admin UI to be deployed and tested before going live.

### Deployment Notes

- **Main app** (`kindora-prod`): Auto-deploys from `main` branch via git push
- **Analytics dashboard** (`kindora-funnel-analytics`): Must be deployed manually via `vercel --prod` from `kindora-analytics/` directory using the `justin-kindora` Vercel account (not `justin-outdoorithm`). Use `vercelgate switch` to swap accounts.
- **Backend API**: Deployed to Azure App Service separately
- **Admin auth**: Grant Brief API endpoints require `require_admin` — the user's email must be in `ADMIN_EMAIL` / `ADMIN_EMAIL_2` / `ADMIN_EMAIL_3` env vars

### Known Issues (as of 2026-03-02)

1. **Saturday Philanthropy Pulse requires prior scrape+classify**: The pulse pipeline needs classified insights in `influencer_insights` with `relevance_score >= 0.6`. Run Seed & Scrape + Classify at least once before Saturday generation. Pipeline is now fully working (49 influencers seeded, Apify scraping fixed, classification fixed).
2. **Generate creates duplicates, not overwrites**: Each "Generate" call creates a new row. If you generate twice for the same date, you get two drafts. Keep the better one, reject the other.
3. **Pipeline cost per day**: ~$0.02-0.03 for candidate selection (Stage 4 AI enrichment) + ~$0.01 for post generation = ~$0.03-0.04 total per day. Full week ≈ $0.08-0.25 depending on content types. Influencer classification costs ~$0.015 per scrape run (~32 posts).
4. **Dignity filter is aggressive**: Stage 4 filters out ~50% of candidates via `dignity_flag=false`. This is by design (avoids featuring problematic funders) but means the pipeline needs a large initial candidate pool.

### Bugs Fixed (2026-03-02)

1. **Apify actor URL separator**: Changed from `/` to `~` in `APIFY_ACTOR` constant. Apify v2 API requires `harvestapi~linkedin-profile-posts`, not `harvestapi/linkedin-profile-posts`.
2. **Apify field name mapping**: HarvestAPI actor uses `linkedinUrl` (not `postUrl`), `content` (not `text`), nested `author.linkedinUrl` (not `authorProfileUrl`), and nested `postedAt` dict (not flat string).
3. **GPT-5 nano reasoning tokens**: `max_completion_tokens=500` was too low — GPT-5 nano is a reasoning model that uses hidden reasoning tokens. At 500, reasoning consumed the entire budget, leaving empty response body (`finish_reason=length`). Fixed to 2000. This caused ALL posts to get `relevance_score=0.0` and be deleted.

---

## Overview

"The Grant Brief" is Kindora's content marketing engine — a multi-channel system that publishes grant opportunities across LinkedIn (daily) and email newsletter (weekly) to attract nonprofit leaders to the platform.

**Core philosophy**: This is marketing, not personalized intelligence. The goal is to dangle enticing, widely-applicable opportunities in front of people so they get excited, feel hopeful about available funding, and come to Kindora wanting more. Personalized, actionable intelligence is what a Kindora account provides — this system is the top-of-funnel inspiration layer.

**Channels**:
- **LinkedIn**: 7 days/week — grant features (Mon-Fri), thought leadership (Sat), deadline preview (Sun)
- **Newsletter**: Weekly email digest (Tuesday 8am ET) — curated highlights + sector insights
- **Website**: Newsletter archive pages (SEO value)

### Research Foundation

This system design is informed by research inputs:
- **SEO keyword research** (DataForSEO, 182 keywords) — what nonprofit professionals search for, which themes have the most organic demand
- **User engagement best practices** (`local-files/docs/research/user_engagement_research.md`) — how nonprofit audiences consume content, what cadences work, psychological principles for social-impact SaaS
- **Philanthropy influencer curation** (`local-files/docs/research/philanthropy_influencers.md`) — a 40+ person seed list organized by signal category and viewpoint diversity
- **Roy Bahat's "Not a Newsletter" format analysis** — studied the curator-personality hybrid approach where the author's voice wraps around structured content. Key insight: the personal opener + structured utility + insight close pattern creates both habit and trust.
- **Nonprofit newsletter best practices research** — benchmarked 10+ top nonprofit newsletters. Findings: (1) personality-forward newsletters outperform generic ones by 2-3x in click rates, (2) "brilliant friend who happens to know" positioning beats "authoritative resource" for acquisition, (3) scannable structure (60-second read) is non-negotiable for this audience
- **Justin's voice analysis** — analyzed 150+ emails across 5 accounts (2007-2026), 100+ LinkedIn posts, 10+ long-form articles. Identified the "Steele Arc" rhetorical structure and key voice patterns. Synthesized into a persona guide and anti-AI writing rules.

Key principles from the engagement research that shaped every design decision:
1. **Compete on relevance, not volume** — nonprofits receive ~62 emails/year; one great weekly email beats daily noise
2. **Front-load value** — users read at most 28% of words; first sentence must be the most concrete thing
3. **Dignity-forward tone** — "competent, calm, on-your-side" — no guilt, no FOMO, no growth-hack voice
4. **Weekly pulse + event triggers** — one consistent weekly send (habit anchor) plus situational nudges
5. **Dual-purpose channel** — the newsletter is both acquisition (attract non-users) and retention (re-engage churned users)
6. **Track clicks, not opens** — Apple Mail Privacy Protection makes open rates unreliable

---

## 1. SEO Research — What People Search For

### Methodology

Used DataForSEO Google Ads Search Volume API (US market, location_code 2840) with 182 keywords across 15 grant themes. This data informs which themes have the most organic demand and should drive content prioritization.

### Results by Theme (Monthly Search Volume)

| # | Theme | Total Volume | Top Keywords |
|---|-------|-------------|--------------|
| 1 | **Education Grants** | 13,890 | grants for education (3,600), education grants for nonprofits (2,400), STEM grants (1,600), literacy grants (1,300) |
| 2 | **Community Development** | 11,850 | community development grants (2,900), housing grants for nonprofits (2,400), rural development grants (1,900), neighborhood grants (1,300) |
| 3 | **Arts & Culture** | 7,490 | arts grants for nonprofits (2,400), NEA grants (1,900), music program grants (1,300), cultural preservation grants (590) |
| 4 | **Technology & Innovation** | 6,080 | technology grants for nonprofits (1,900), digital transformation grants (1,300), STEM grants for nonprofits (1,300), AI grants (590) |
| 5 | **Faith-Based** | 4,510 | church grants (1,900), faith-based grants (1,300), religious organization grants (720), ministry grants (590) |
| 6 | **Veterans & Military** | 2,920 | grants for veteran organizations (1,300), veteran nonprofit grants (720), military family grants (590), veteran housing grants (310) |
| 7 | **Animal Welfare** | 1,980 | animal welfare grants (720), animal rescue grants (480), wildlife conservation grants (480), pet shelter grants (300) |
| 8 | **Startup / Small Org** | 1,820 | startup grants for nonprofits (720), new nonprofit funding (480), seed funding for nonprofits (320), first-time grants (300) |
| 9 | **Environment & Climate** | 1,730 | environmental grants (590), climate change grants (480), conservation grants (390), sustainability grants (270) |
| 10 | **Youth Development** | 1,660 | youth program grants (590), after-school grants (480), mentoring grants (320), juvenile justice grants (270) |
| 11 | **Health & Wellness** | 1,630 | health grants for nonprofits (590), mental health grants (480), substance abuse grants (320), wellness program grants (240) |
| 12 | **Seniors & Aging** | 1,460 | grants for senior programs (590), aging services grants (390), elder care grants (270), senior center grants (210) |
| 13 | **Grant Deadlines / Urgency** | 1,430 | grant deadlines this month (590), grants closing soon (390), emergency grants for nonprofits (270), last-minute grants (180) |
| 14 | **Social Justice & Equity** | 700 | social justice grants (320), racial equity grants (210), DEI grants for nonprofits (110), civil rights grants (60) |
| 15 | **International Development** | 680 | international development grants (320), global health grants (210), humanitarian aid grants (100), foreign aid grants (50) |

**Total addressable search volume**: ~58,430/month across these 15 themes.

### Key Insights

1. **Education dominates** — 2.4x the volume of the next theme. Education grants content should appear frequently.
2. **Community development is #2** — housing, rural, and neighborhood grants are high-demand.
3. **Faith-based is surprisingly large** (4,510/mo) — an underserved audience that few grant platforms target.
4. **"Grant deadlines" searches** (1,430/mo) validate a deadline-focused content day.
5. **Environment/climate is lower than expected** (1,730/mo) — still worth featuring but not as dominant as industry buzz suggests.
6. **Social justice & equity** is lowest volume (700/mo) — important for mission alignment but not a traffic driver.

### Existing SEO Research Cross-Reference

Prior research in `docs/SEO_LANDING_PAGE_RESEARCH.md` identified 1,861 keywords with 700K+ monthly volume. Key overlap:
- Geographic grant pages are the #1 SEO opportunity (not directly content-marketing relevant, but informs newsletter localization)
- Topic/sector pages are #2 — directly validates themed content approach
- "Grants for [cause]" keywords have the highest intent-to-action ratio

---

## 2. LinkedIn Daily Theme Schedule

Based on SEO volume data + audience engagement patterns + weekday vs weekend optimization:

**Weekday strategy** (Mon-Fri): Higher LinkedIn traffic, professional mindset. Best for specific, actionable grant content that people bookmark, share, or click through.

**Weekend strategy** (Sat-Sun): Lower traffic but less competition and more reflective engagement. Best for inspirational/educational content and weekly planning.

| Day | Theme | Format | Rationale |
|-----|-------|--------|-----------|
| **Monday** | Education & Youth | Single grant feature | Highest search volume (13,890). Start the week strong. Covers K-12, higher ed, STEM, literacy, after-school, mentoring. |
| **Tuesday** | Community & Housing | Single grant feature | Second highest (11,850). Peak LinkedIn engagement day. Community development, affordable housing, rural grants. |
| **Wednesday** | Funder Spotlight | Foundation profile | Profile a specific foundation — mission, what they fund, tips for approaching. Builds Kindora as the "insider's guide." Drives signups to see full funder profiles. |
| **Thursday** | Sector Spotlight (rotating) | Single grant feature | Rotating focus: Arts (7,490), Health (1,630), Environment (1,730), Faith-Based (4,510), Veterans (2,920), Seniors (1,460), Animal Welfare (1,980). Different sector each week on a ~7-week rotation. |
| **Friday** | Tech & AI for Good | Single grant feature | AI grants, digital transformation, tech-for-good programs, social impact accelerators, innovation funding (6,080 + 1,820 search volume). THE trend in social impact right now — dedicated day for organizations building with technology. |
| **Saturday** | Philanthropy Pulse | Thought leadership / insights | Curated insights from philanthropy influencers. Sector trends, big-picture perspectives. Builds brand authority. Reflective weekend mood. |
| **Sunday** | Week Ahead: Deadlines | Top 3-5 grants closing this week | "Plan your week" content. People check LinkedIn Sunday evening while prepping for Monday. Creates urgency and gives them actionable items for the week ahead. |

### Personal vs Company LinkedIn Strategy

Content is published from two LinkedIn accounts, controlled by the `publishing_account` field on `grant_brief_content`:

| Day | Account | Rationale |
|-----|---------|-----------|
| Mon-Fri, Sun | **Company** (Kindora page) | Professional, brand-building content. Published automatically via LinkedIn Marketing API. |
| Saturday | **Personal** (Justin) | Philanthropy Pulse is thought leadership — personal voice resonates more. Queued as `queued_for_personal` for manual posting. |
| Wednesday | **Company** + personal reshare | Company publishes Funder Spotlight, then reshare copy is generated for Justin to share manually with personal commentary. |

The `LinkedInPublisher` service handles this automatically:
- `publish_company_post()` — calls LinkedIn Marketing API v2 (`ugcPosts` endpoint) for company page posts
- `queue_personal_post()` — sets status to `queued_for_personal` for manual posting (LinkedIn API doesn't support personal profile posting)

**Note:** LinkedIn access tokens expire every 60 days. Token refresh is manual for now.

### Post Format

Each LinkedIn post follows a format matched to its content type:

**Grant Feature Post** (Mon, Tue, Thu, Fri):
```
[THEME TAG] — [Month Day]

[Compelling headline: what the grant funds and why it matters]

[2-3 sentences: who's eligible, what it supports, and the human impact.
Written as a trusted colleague sharing something useful — no hype.]

Amount: [range]
Deadline: [date]
Best for: [org types]

[1-sentence closer that inspires possibility, not anxiety]

More open grants for your mission at kindora.co

#GrantOpportunities #NonprofitFunding #[ThemeHashtag]
```

**Funder Spotlight** (Wednesday):
```
FUNDER SPOTLIGHT — [Foundation Name]

[1 sentence about the foundation's mission and what drives their giving]

Annual giving: $[amount]
Focus areas: [2-3 focus areas]
Geographic reach: [scope]
What they look for: [1-2 key criteria]

[1-2 sentences: what makes this funder distinctive + a practical tip
for organizations considering an approach]

Full profile — programs, recent grants, and fit analysis — at kindora.co

#FunderSpotlight #GrantFunding #NonprofitStrategy
```

**Week Ahead: Deadlines** (Sunday):
```
YOUR WEEK AHEAD — Grants Closing [Date Range]

Worth putting on your calendar this week:

1. [Grant name] — $[amount] for [focus]. Closes [date].
2. [Grant name] — $[amount] for [focus]. Closes [date].
3. [Grant name] — $[amount] for [focus]. Closes [date].

If you can carve out time for one application this week,
any of these would be worth the effort.

Browse more open grants at kindora.co

#GrantDeadlines #NonprofitFunding #WeekAhead
```

**Philanthropy Pulse** (Saturday):
```
PHILANTHROPY PULSE — This Week in Funding

[Structured around 2-3 perspective categories:]

What funders are signaling:
[1-2 sentences from capital allocator posts]

What the sector is watching:
[1-2 sentences from infrastructure/media posts]

What communities are saying:
[1-2 sentences from equity/community leaders]

[1-sentence synthesis: what this means for your organization]

What are you seeing in your corner of the sector?

#Philanthropy #NonprofitLeadership #FundingTrends
```

**Voice notes**: No ALL CAPS urgency. No "DON'T MISS" framing. No excessive emoji. The tone is a knowledgeable colleague sharing intelligence over coffee, not a marketer optimizing for clicks. Dignity-forward framing on all deadline content.

### Content Voice & Tone

All Grant Brief content — LinkedIn posts, newsletter, website — follows a single voice: **a trusted colleague sharing something genuinely useful**. Not a marketing funnel. Not a hype machine.

Guiding principles (informed by user engagement research):
- **Competent, calm, on-your-side, dignity-forward** — no guilt framing, no growth-hack voice, no manufactured urgency
- **Front-load value** — users scan (at most 28% of words on a page); the first sentence must convey the most concrete value
- **Deadline framing with dignity** — "This closes March 15 — worth putting on your calendar" not "DON'T MISS THIS! APPLY NOW BEFORE IT'S TOO LATE!"
- **Social proof without status games** — "Organizations like yours typically pursue 3-5 grants per quarter" not "Top nonprofits use Kindora"
- **Competence framing on CTAs** — "Move faster on your next application" not "Unlock premium features"
- **No FOMO** — inspire possibility, not anxiety. "Here's what's available" not "Here's what you're missing"

These principles are baked into the AI content generation system prompts.

### Content Selection Criteria

For each daily post, the system should select grants that are:
1. **Widely applicable** — not restricted to a single city or hyper-niche cause
2. **Currently open** — deadline is at least 7 days away
3. **Meaningful amounts** — generally $10K+ to be worth featuring
4. **Compelling narrative** — has a clear "who this helps" story
5. **Geographically broad** — national or multi-state preferred
6. **Reputable funder** — known foundations inspire more trust
7. **Realistic odds** — prefer programs that make multiple awards or have rolling deadlines (a $10M grant that funds 1 org out of 5,000 isn't inspiring, it's demoralizing)
8. **Size diversity** — mix across $5K-$500K range, not just mega-grants (small orgs need to see themselves in the content)
9. **First-time friendly** — especially for Friday's Innovation & Startup theme, favor programs open to new applicants

---

## 3. Newsletter Architecture — Weekly "Grant Brief"

### Cadence & Timing
- **Frequency**: Weekly (every Tuesday morning, 8am ET)
- **Why Tuesday**: Highest email open rates for B2B/nonprofit audiences; Monday is too cluttered, Wednesday starts losing engagement

### Newsletter Sections (Voice Mode — Current)

The voice-mode newsletter (Opus 4.6, default) uses a curator-personality hybrid format where Justin's voice wraps around structured grant intelligence:

| Section | Content | Voice Character |
|---------|---------|----------------|
| **1. Justin's Open** | Personal observation, scene, or anecdote connecting to this week's philanthropy landscape | The "Roy Bahat opener" — something kicking around in his head. NOT a summary of contents. NOT "Welcome to this week's Grant Brief." |
| **2. Editor's Pick** | One standout grant with Justin's take on WHY it matters | 3-4 sentences of Justin's perspective, not just what it funds. Funder name, amount, deadline, focus area. |
| **3. This Week's Highlights** | 3-4 grants featured on LinkedIn that week | 1-2 sentences each. Justin might add a one-line take on one or two. |
| **4. Deadline Watch** | Grants closing in the next 7-14 days | Clean list format. Justin one-liner intro: "Three worth putting on your calendar this week:" |
| **5. Philanthropy Pulse** | Justin's synthesis of what thought leaders are saying | Uses the "Steele Arc": specific insight → systemic pattern → what it means. References specific people by name. |
| **6. Justin's Close** | Personal reflection, callback to opener, engagement invitation | NOT a summary. NOT "Until next week!" Sign off: "Justin" (just the first name). |

### Newsletter Sections (Haiku Fallback)

If voice mode is disabled or fails, falls back to section-by-section Haiku generation:

| Section | Content | Source |
|---------|---------|--------|
| **1. Editor's Pick** | One standout grant opportunity with deep context | AI-selected from highest feature_score grants |
| **2. This Week's Highlights** | 3-4 grants featured on LinkedIn that week | Aggregated from daily LinkedIn posts |
| **3. Deadline Watch** | Grants closing in the next 14 days | Automated from `funder_programs` deadline data |
| **4. Sector Spotlight** | Deep dive on the week's funder spotlight | Derived from Wednesday's funder spotlight content |
| **5. Philanthropy Pulse** | 2-3 curated insights from philanthropy influencers | Sourced from influencer monitoring (see §5) |

### Newsletter vs LinkedIn Differentiation

The newsletter is NOT a copy-paste of LinkedIn posts. Key differences:
- **LinkedIn**: Single grant (or short list), quick-hit inspiration, daily cadence
- **Newsletter**: Curated collection, deeper context, strategic framing, weekly cadence
- **Newsletter exclusive**: Deadline Watch section, Philanthropy Pulse, Editor's Pick with application tips
- **Newsletter tone**: More personal, more strategic, more "insider knowledge" feeling

### Voice-First Newsletter Generation (Opus 4.6)

The weekly newsletter uses a **voice-first generation approach** — Claude Opus 4.6 writes the entire newsletter in a single pass, producing it in Justin Steele's authentic voice. This is fundamentally different from the section-by-section Haiku approach used for initial drafts.

**Why Opus 4.6**: The newsletter is the highest-stakes content we produce. It goes to real subscribers' inboxes and represents Justin's personal brand. Haiku can write clean copy, but voice authenticity at this level requires Opus. The cost premium (~$1.50-2.00 per newsletter vs. ~$0.30 for Haiku sections) is justified because a single weekly newsletter has the highest engagement per piece of any content we create.

**Voice training approach**: The generator loads ~300KB of Justin's actual writing (LinkedIn posts, articles, email persona guide) from Supabase storage and feeds it as context alongside the anti-AI writing rules. Opus reads all of it, internalizes Justin's patterns, and generates the newsletter as Justin would write it — not about Justin, AS Justin.

**Voice materials** (stored in `kindora-files/voice-materials/` on Supabase storage):
- `Claude_Project_-_LinkedIn_Posts.md` — 100+ LinkedIn posts showing Justin's daily voice
- `Claude_Project_-_LinkedIn_Articles.md` — 10+ long-form articles showing his analytical style
- `JUSTIN_EMAIL_PERSONA.md` — Persona guide distilled from 150+ emails across 5 accounts
- `Signs_of_AI_Writing.md` — Anti-AI detection rules (no significance padding, no symmetric triads, etc.)

**The hybrid "curator-personality" format** (inspired by Roy Bahat's "Not a Newsletter"):

The newsletter wraps Justin's personality around structured grant intelligence. The format:
1. **Justin's Open** — personal observation or anecdote connecting to this week's philanthropy landscape. NOT a summary of contents. Think: something kicking around in his head.
2. **Editor's Pick** — Justin's take on WHY the top grant matters, not just what it funds
3. **This Week's Highlights** — 3-4 grants, brief (1-2 sentences each)
4. **Deadline Watch** — clean list format with a Justin one-liner intro
5. **Philanthropy Pulse** — Justin's synthesis of thought leader insights. Uses the "Steele Arc": specific insight → systemic pattern → what it means
6. **Justin's Close** — personal reflection, callback to opener, invitation for engagement. Sign off: "Justin"

**Anti-AI writing rules** (from `Signs_of_AI_Writing.md`): No significance padding ("this underscores the importance of"), no stacked negative-parallels, no symmetric triads, no participle pileups, reduced em dashes, no vague authority phrases, prefer simple verbs, maintain human cadence with varied sentence length, every paragraph needs a concrete detail, no template headings.

**Implementation**: `VoiceNewsletterGenerator` in `services/grant_brief/voice_newsletter_generator.py`. Called from `NewsletterComposer.compose_edition()` when `use_voice_mode=True` (default). Falls back to Haiku section-by-section generation if voice mode fails or is disabled.

**Cost**: ~$1.50-2.00 per newsletter (95K input tokens for voice materials + ~3K output). $6-8/month total. The voice materials are cached in memory after first load so only the Opus API call costs money.

### Dual-Audience Design

The Grant Brief serves two audiences with the same core content:

1. **Pre-signup subscribers** (marketing/top-of-funnel): Full Grant Brief with broadly inspiring content. CTA drives to Kindora signup.
2. **Churned/at-risk users** (re-engagement): Same Grant Brief PLUS a personalized header module: "Your matches have been updated — 3 new opportunities this week." CTA drives back into the product.

This doubles the newsletter's value as both an acquisition AND retention channel without doubling the work. Implementation: MailerLite dynamic content blocks segmented by `converted_at IS NOT NULL` in the subscriber record.

### Email Design Principles (from Engagement Research)

Nonprofit audiences receive an average of **62 emails per subscriber per year** across the sector. The Grant Brief competes on **relevance and utility**, not volume.

Design rules:
- **Subject line**: 35-55 characters, front-load the most concrete value. "3 education grants closing this week" not "The Grant Brief — Issue #12"
- **Each section**: One headline, 2-3 short lines, ONE primary CTA button. No competing links within a section.
- **Total length**: Scannable in 60 seconds. If it takes longer, cut content.
- **Measurement**: Track clicks and downstream signups, NOT open rates (Apple Mail Privacy Protection makes opens unreliable)
- **Mobile-first**: 70%+ of nonprofit professionals read email on mobile
- **Layout**: Single-column, clean, Kindora teal + white
- **Footer**: Unsubscribe + preference center (trust is a revenue lever in social-impact SaaS)

---

## 4. Grant Selection Intelligence System

### The Problem

We have 80,178 funder programs from 22,445 foundations and 5.7M grant records. The system needs to automatically identify the most compelling grants to feature each day/week.

### Data Sources

| Table | Schema | Key Fields | Purpose |
|-------|--------|------------|---------|
| `funder_programs` | public | program_name, program_description, focus_areas, geographic_focus, grant_size_max, closing_date, is_rolling_basis, application_url, accepts_unsolicited, invite_only, by_nomination, eligibility_criteria, beneficiary_types | Program metadata + accessibility signals |
| `us_foundations` | public | foundation_name, annual_grants, total_assets, ntee_code, state, geographic_scope, semantic_focus_taxonomy, grant_p25/p50/p75, latest_990_year, confidence_score | Foundation-level stats + enrichment quality |
| `funder_program_embeddings` | public | embedding (512d), funder_key, funder_name, program_label | Vector search via pgvector HNSW |
| `foundation_grants` | public | foundation_ein, recipient_name, grant_amount, grant_purpose, filing_year | Grant history for narrative hooks + "stated vs revealed" analysis |
| `funder_pages` | public | ein, url, summary_md, page_types | Web intelligence (used for Funder Spotlight) |

### 6-Stage Selection Pipeline (Standard Grant Features: Mon/Tue/Thu/Fri)

The pipeline is implemented in `GrantBriefSelectorService` (`services/grant_brief/selector_service.py`).

#### Stage 1: Multi-Path Search (4 paths, up to 400 candidates)

```
Path A: Structured Query (up to 200 results)
  └─ funder_programs filtered by:
     • closing_date > NOW() + 7 days OR is_rolling_basis = true
     • Theme match via 4-way matching:
       1. NTEE prefix on us_foundations.ntee_code
       2. focus_areas keyword ILIKE
       3. semantic_focus_taxonomy array overlap
       4. program_description keyword fallback
     • Excludes invite_only and by_nomination
     • JOINs us_foundations for stats (two-step: query programs, then batch-fetch foundations by EIN)

Path B: Vector Search (up to 100 results)
  └─ Embeds theme description as 512d vector (text-embedding-3-small, Matryoshka truncation)
  └─ Calls `search_funder_programs` RPC (pgvector cosine similarity on funder_program_embeddings)
  └─ Returns best matching program per foundation (deduped at DB level)

Path C: Grant Mining (up to 50 results)
  └─ Searches foundation_grants via `search_grant_purposes` RPC (full-text tsvector search)
  └─ Filters for $25K+ grants from last 3 years
  └─ Returns aggregate stats per foundation (matching_grants, total_amount, avg_grant, sample_purposes)
  └─ Links back to funder_programs by EIN where possible

Path D: Content Archetype Search (up to 50 results)
  └─ Theme-independent "always-on radar"
  └─ Embeds ideal content description: "A broadly applicable grant program accepting applications
     from diverse nonprofits nationwide, offering meaningful funding ($25K-$250K)..."
  └─ Cached via @functools.lru_cache (computed once, reused forever)
  └─ Uses same search_funder_programs RPC as Path B
```

**Union & Dedup**: All 4 paths are merged. Dedup key: `program_id` (UUID) preferred, fallback to `us_foundation_ein`. Candidates found by 2+ paths get `multi_path_bonus=True` and `search_path_count` metadata.

#### Stage 2: Symbolic Scoring (0-100 scale)

Adapted from production `services/agents/scoring.py` but tuned for CONTENT selection (broadly inspiring) rather than MATCH quality (org-specific fit).

| Dimension | Max Points | Logic |
|-----------|-----------|-------|
| **Geographic Breadth** | 20 | national=20, multi-state=15, statewide=10, regional=7, local=5. Uses `geographic_scope` enum from us_foundations. |
| **Grant Size Appeal** | 25 | Sweet spot $25K-$250K = 25. $10-25K = 18. $250K-1M = 15. <$10K = 8. >$1M = 10 (too large for most orgs). Uses grant_size_max, falls back to grant_p50. |
| **Accessibility** | 15 | Additive: accepts_unsolicited +5, has application_url +5, not invite_only +3, has eligibility_criteria +2. |
| **Narrative Richness** | 15 | Description >200 chars +5, semantic_focus_taxonomy 3+ items +4, beneficiary_types +3, focus_areas +3. |
| **Funder Credibility** | 15 | annual_grants >$100M = 10, >$10M = 5, >$1M = 2. Plus: confidence_score >0.7 +2, enrichment proxy +3. |
| **Recency/Momentum** | 10 | latest_990_year within 1 year = 10, 2 years = 7, 3 years = 4. |
| **Multi-path Bonus** | +5 | Candidates found by 2+ search paths. |

**Output**: Top 30 candidates sorted by score descending.

#### Stage 3: Concentration & Diversity Filter

Prevents repetitive content by enforcing temporal, sector, and geographic diversity:

- **Foundation recency penalty**: -20 if featured in last 7 days, -10 if 14 days, -5 if 30 days
- **Exact program dedup**: Skip programs already featured in `grant_brief_content`
- **Sector diversity**: Max 2 candidates per NTEE major category (first letter)
- **Geographic diversity**: Max 3 candidates per state

**Output**: Top 15-20 candidates.

#### Stage 4: AI Enrichment (GPT-5 mini)

Each candidate gets an individual GPT-5 mini call with structured JSON output:

| Field | Type | Purpose |
|-------|------|---------|
| `broad_applicability` | 1-10 | How many types of nonprofits could plausibly apply? |
| `narrative_hook` | string | Best 1-sentence angle for featuring this program |
| `accessibility` | 1-10 | Realistic for small-to-mid-size nonprofit with limited capacity? |
| `theme_fit` | 1-10 | Match quality to today's theme |
| `stated_vs_revealed` | string | Compare program description to actual grant history |
| `dignity_flag` | boolean | False if designed only for large institutions or unrealistically competitive |

The AI prompt includes grant history context from `foundation_grants` for each foundation, enabling "stated vs revealed" analysis (pattern from funder-research ally skill).

**Final score**: `symbolic_score × (broad_applicability + accessibility + theme_fit) / 30`

Candidates with `dignity_flag=false` are filtered out. Top 3-5 are selected for content generation.

### Variant Pipelines (Non-Standard Days)

#### Wednesday: Funder Spotlight

Selects a notable foundation (not a program) for deep-profile content.

```
1. Query us_foundations WHERE annual_grants > $1M, recently active (latest_990_year within 3 years)
2. Score by: total giving (0-30), recency (0-20), data quality (0-20)
3. Diversity check: not featured in grant_brief_content in last 60 days
4. Enrich selected foundation from 3 sources:
   • funder_pages — web intelligence summaries (URL, summary_md)
   • foundation_grants — top 10 recent grants
   • funder_programs — active programs
5. Return comprehensive dict for Claude Sonnet to write spotlight post
```

**Note**: `funder_profiles` is org-scoped (per-customer enrichment) and NOT used here. `funder_pages` provides universal web intelligence.

#### Saturday: Philanthropy Pulse

Synthesizes influencer insights from the `influencer_insights` table.

```
1. Query influencer_insights for last 7 days, relevance_score >= 0.6
2. Narrative dedup: collapse insights with same dedup_cluster_id → keep highest relevance
3. Perspective balancing: max 3 insights per signal_category (ensures 2-3 of 5 categories represented)
4. Enrich with influencer names from philanthropy_influencers table
5. Return top 7 insights for Claude Sonnet synthesis
```

#### Sunday: Deadline Roundup

Curates programs with imminent deadlines for "plan your week" content.

```
1. Reuse Stage 1 Path A in deadline mode: closing_date BETWEEN target_date AND target_date + 7 days
2. Score by: accessibility (0-15), geographic breadth (0-10), grant size appeal (0-10)
3. Sector diversity filter: max 2 per NTEE major category
4. Return top 5 sorted by closing_date
```

### Content Archetype Embedding

A permanent "always-on radar" that surfaces ideal marketing content regardless of daily theme. The archetype embedding encodes:

> "A broadly applicable grant program accepting applications from diverse nonprofits nationwide, offering meaningful funding ($25K-$250K) for programs serving underserved communities, with a clear application process and upcoming deadline."

This 512d vector is computed once and cached via `@functools.lru_cache`. It runs as Path D in every standard pipeline execution, ensuring the system always finds "broadly inspiring" programs even when theme-specific search paths return weak results.

Pattern adapted from `funder_similarity_service.py` centroid-based search.

### Reused Existing Services & Patterns

| Service | What We Reused |
|---------|---------------|
| `services/agents/scoring.py` | 85-point symbolic scoring dimensions (geographic overlap, grant size fit, accessibility, recency). Adapted for content selection (broadly inspiring) vs match quality (org-specific). |
| `services/funder_similarity_service.py` | Centroid-based vector search pattern, `find_similar_to_centroid()` RPC usage. Adapted for Content Archetype embedding. |
| `services/funder_search_service.py` | `_cached_keyword_embedding()` pattern for embedding theme descriptions. Reused OpenAI client and embedding model config. |
| `services/ally_tools/tool_registry.py` | `search_grant_purposes` RPC pattern for grant mining (Path C). Query structure and result mapping. |
| `utils/token_pricing.py` | Cost tracking for all AI API calls (OpenAI + Anthropic). |
| `core/config.py` | Feature flag pattern (`ENABLE_GRANT_BRIEF_CONTENT`), env var loading. |

### Cold Start & Quality Assurance

- **Phase 1** (Launch): Manually curate grants from scored candidates. Human reviews AI-generated copy before posting.
- **Phase 2** (Month 2-3): Semi-automated. AI generates, human approves with one click.
- **Phase 3** (Month 4+): Fully automated with exception-based review. Human only intervenes if flagged.

---

## 5. Philanthropy Influencer Monitoring

### Purpose

Build a structured intelligence pipeline that captures what's happening across the philanthropy ecosystem — not just what big foundations say, but what communities experience, analysts observe, and equity leaders demand. This feeds:
1. Saturday's "Philanthropy Pulse" LinkedIn post
2. Newsletter's "Philanthropy Pulse" section
3. Trend detection for timely content across all channels

### Existing Capability

We already have `ApifyPostScraperService` (`services/contact_enrichment/apify_post_scraper.py`) that uses the `harvestapi/linkedin-profile-posts` Apify actor to scrape LinkedIn posts. Currently used for contact-level outreach personalization.

### Curated Influencer List

Full seed list: `local-files/docs/research/philanthropy_influencers.md` (original 49) + `local-files/docs/PHILANTHROPY_NEWSLETTER_VOICES.md` (47 from Justin's personal network, added March 2026)

96 curated profiles organized into 5 signal categories for **viewpoint diversity**, not popularity:

| Category | Count | Examples | Signal Value |
|----------|-------|----------|-------------|
| **Capital Allocators** | 35 | Gates (Suzman), Ford (Gerken), Rockefeller (Shah), Kresge (Rapson), RWJF (Besser), MacArthur (Williams), Lumina (Merisotis), Skoll (Osberg) | Foreshadow shifting priorities, new commitments, sector responses to policy/economic shocks |
| **Field Infrastructure** | 22 | Council on Foundations (Enright), Candid (Chang), GEO (Walton), CEP (Buchanan), GivingTuesday (Curran), Beth Kanter, Bridgespan (Kaplan), National Council of Nonprofits (Taylor) | Shape norms, convene funders, publish sector-wide perspective |
| **Media & Analysts** | 12 | Inside Philanthropy (Callahan), Chronicle of Philanthropy (Palmer, Stiffman, Di Mento, Childress), Philanthropy News Digest (Francis), Sean Stannard-Stockton | Quickest aggregators of what's changing across multiple funders |
| **Equity & Community** | 14 | ABFE (Taylor Batten), AAPIP (Chung Joe), HIP (Argilagos), Native Americans in Philanthropy (Stegman), Vu Le, Robert Ross (California Endowment), Tia Martinez | Counter "institution-only" blind spots, community-rooted perspectives |
| **Impact Investing** | 13 | GIIN (Bouri), AVPN (Batra), LISC (Andrews), Antony Bugg-Levine (Nonprofit Finance Fund), Clara Miller, Darren Walker (Ford) | "Beyond grants" signals — blended finance, outcomes-based models |

**Expansion history**: Original 49 (March 1, 2026) included Beth Kanter and Vu Le. On March 2, 2026, 47 contacts from Justin's personal network were added, nearly doubling the list. One contact (Julie Ann Crommett) was held back as too tangential to philanthropy. Cross-listed contacts (Alexa Cortes Culwell, Richard Tate, Caroline Whistler) added under their primary category. Full seed list hardcoded in `InfluencerMonitorService.INFLUENCER_SEED_LIST`.

### Intelligence Pipeline (Not Just Scraping)

The pipeline is designed around **signal quality and perspective diversity**, not content volume:

```
1. Scrape: Weekly pull via Apify `harvestapi/linkedin-profile-posts` actor
   - Config: maxPosts=15, scrapeReactions=False, includeReposts=False, includeQuotePosts=True
   - Batch 5 LinkedIn URLs per Apify run (configurable via `batch_size`, up to 20)
   - `days_back` param (default 7): configurable scrape window — use 14 for initial scrape of new contacts
   - `only_unscraped` param (default false): when true, only scrapes influencers with NULL `last_scraped_at` — useful after seeding new contacts
   - URL normalization: urllib.parse.unquote() + ensure www. prefix
     (without www., ~10% of scrapes fail silently)
   - Country-specific LinkedIn prefixes (uk., sg., dk., etc.) → replaced with www.
   - Client-side date filtering: Apify returns all maxPosts — filter for last `days_back` days in Python
   - Dedup: source_post_url UNIQUE constraint prevents duplicate post storage
   - Uses run-sync-get-dataset-items endpoint (returns items directly, no polling)
   - Cost: ~$0.002/post, ~$2.70/week for 96 profiles

2. Signal Classification (GPT-5 nano): Score each post for "funding relevance" (0-1):
   - Grant announcements / new commitments (high)
   - Policy/regulation impacts on funding (high)
   - Strategy shifts / priority changes (high)
   - Evaluation learnings / what worked (medium)
   - Partnership announcements (medium)
   - Personal reflections / general commentary (low)
   - Output: relevance_score (0-1), signal_type, topic, insight_summary
   - Posts with relevance_score < 0.3 are deleted from DB (prevents table bloat)
   - Cost: ~$0.005 per 1000 posts

3. Narrative Deduplication: Groups classified, unclustered insights from last 14 days
   by normalized topic (case-insensitive exact match). Assigns shared dedup_cluster_id UUID
   to groups of 2+ posts on the same topic. Saturday Pulse picks highest-relevance
   representative per cluster.

4. Perspective Balancing: Every "Philanthropy Pulse" output must include
   at least 2-3 of the 5 signal categories. Max 3 insights per category.
   Never publish a Pulse that only amplifies institutional funder messaging.

5. Content Assembly: Surface top 7 insights for Saturday LinkedIn post
   and newsletter section, structured as:
   - "What funders are signaling" (capital allocators)
   - "What the sector is watching" (infrastructure + media)
   - "What communities are saying" (equity leaders)

6. Source Link Extraction (PLANNED — not yet implemented):
   When influencers share articles, reports, or external resources in their
   posts, extract and store the shared URL + title. This enables the newsletter
   to hyperlink directly to primary source material rather than only referencing
   what the thought leader said about it.
```

### Hyperlinking & Source Material Philosophy

The newsletter should be a **gateway to the broader conversation**, not a closed loop. Inspired by Roy Bahat's "Not a Newsletter" approach where every mention links to the original source.

**Linking principles:**
1. **Hyperlink to primary sources** — when a thought leader shares a report, link the report itself (not just the LinkedIn post). Readers should be able to explore the original material.
2. **Link the person** — when referencing a specific insight from a named person, link to their LinkedIn post or the article they wrote/shared. Attribution with access.
3. **Choose the better link** — if an influencer shares a Chronicle of Philanthropy article about a Ford Foundation strategy shift, link the Chronicle article (the primary source), not the LinkedIn reshare. The LinkedIn post is a signal; the source is the value.
4. **Every section should have at least one external link** — Editor's Pick links to the funder or program page, Highlights link to Kindora grant pages, Philanthropy Pulse links to the original sources.
5. **Kindora links are the CTA, not the content** — external links build trust and establish the newsletter as a generous curator. The "Find your next funder at kindora.co" CTA is the conversion mechanism, not the content itself.

**Current gap**: The influencer scraping pipeline captures `post_text` (which often contains embedded URLs) but does NOT currently extract shared article URLs as a structured field. The Apify HarvestAPI actor returns a `document` object with `title` and `transcribedDocumentUrl` when a post shares an article — we need to capture and store this.

**What needs to change to enable source linking:**
1. **DB schema**: Add `shared_url TEXT` and `shared_url_title TEXT` columns to `influencer_insights`
2. **Scraper**: Extract `document.transcribedDocumentUrl` and `document.title` from Apify response; also regex-extract URLs from `post_text` (for inline links)
3. **Classifier**: Add `shared_resource_url` and `shared_resource_title` to the GPT-5 nano classification output — the classifier can identify the most relevant URL from the post text
4. **Newsletter generator**: Update the Opus prompt to instruct Justin's voice to hyperlink source material naturally (e.g., "Phil Buchanan [wrote about](url) the tension between...")
5. **Newsletter HTML**: Ensure the markdown-to-HTML converter handles links properly (already does via `_inline_markdown_to_html`)

### Representation Safeguards

- **Role diversity quotas**: Maintain coverage across all 5 categories; if capital allocators dominate, rebalance
- **Geographic diversity**: Include non-US voices (Wellcome/UK, Novo Nordisk/Denmark, AVPN/Asia)
- **Avoid single-institution capture**: Cap % of insights from any one org
- **Quarterly audits**: Measure whose posts actually make it into published content; add underrepresented voices

### Scouting Guide — What to Look for When Adding Contacts

When sweeping your personal network for new voices, evaluate each contact against the 5 signal categories. The goal is **viewpoint diversity**, not follower count.

**1. Capital Allocators** (currently 35 — well-covered, largest category)
- Foundation leaders who control funding decisions. Their posts foreshadow shifting priorities.
- Look for: program officers, foundation CEOs, giving circle leaders, DAF managers, family foundation principals
- Signal: "where the money is going next"

**2. Field Infrastructure** (currently 22)
- People who shape norms and convene the sector. They set the conversation agenda.
- Look for: Council/affinity group leaders, capacity builders, nonprofit tech advisors, fiscal sponsor leaders, network weavers
- Signal: "what the sector is organizing around"

**3. Media & Analysts** (currently 12)
- Quickest aggregators of what's changing. Journalists and researchers who synthesize trends.
- Look for: philanthropy reporters, sector researchers, podcast hosts, newsletter authors, think tank analysts
- Signal: "what just happened and why it matters"

**4. Equity & Community** (currently 14)
- Counter the "institution-only" blind spots. Community-rooted perspectives on how funding actually lands.
- Look for: grassroots leaders, mutual aid organizers, identity-based philanthropy advocates, community foundation voices from underrepresented communities, participatory grantmaking champions
- Signal: "what communities are actually experiencing"

**5. Impact Investing** (currently 2 — most underrepresented, biggest gap)
- "Beyond grants" signals — where grants and investment are converging.
- Look for: impact fund managers, social enterprise accelerator leaders, CDFI folks, pay-for-success practitioners, blended finance specialists, B Corp leaders in the social sector
- Signal: "where grants and investment are converging"

**Qualifying criteria for any new contact:**
- Posts on LinkedIn at least a few times/month (the scraper needs content to work with)
- Has a distinct perspective — not just resharing press releases or congratulating colleagues
- Bonus for geographic diversity (non-US voices are underrepresented: UK, Asia, Africa, LatAm)
- Avoid duplicating orgs already well-covered (check the 49 existing profiles)
- Priority: fill gaps in impact investing (2) and media/analysts (5) first

**How to add a new contact:**
1. Get their LinkedIn profile URL (ensure it starts with `https://www.linkedin.com/in/`)
2. Assign them a signal category from the 5 above
3. Add to the `INFLUENCER_SEED_LIST` in `InfluencerMonitorService` (in `services/grant_brief/influencer_service.py`)
4. Or add directly via API: `POST /api/grant-brief/influencers/scrape` will seed any new entries in the list
5. Run scrape + classify to start pulling their posts

### Continuous List Expansion

Expand along three axes (per research methodology):
- **Institutional adjacency**: For each funder CEO, add learning/evaluation and partnerships leaders (they post more operationally)
- **Ecosystem adjacency**: For each topic area, ensure coverage of (a) data/infrastructure voice, (b) journalist voice, (c) community voice
- **Representation audits**: Periodically check and rebalance

### Cost Estimate

- 49 influencers × ~15 posts/week × 52 weeks = ~38,220 posts/year
- Apify cost: ~$76/year ($2/1000 posts)
- OpenAI GPT-5 nano classification: ~$50/year (~$0.005/1000 posts)
- **Total: ~$126/year** — negligible

---

## 6. Technical Architecture

### System Components

```
┌──────────────────────────────────────────────────────────────┐
│                     Content Pipeline                          │
│                                                                │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐        │
│  │ Grant     │    │ Content      │    │ Publishing   │        │
│  │ Selector  │───▶│ Generator    │───▶│ Queue        │        │
│  │ (Scoring) │    │ (Sonnet/AI)  │    │              │        │
│  └──────────┘    └──────────────┘    └──────┬───────┘        │
│                                              │                │
│  ┌──────────┐    ┌──────────────┐           │                │
│  │ Influencer│    │ Insight      │           │                │
│  │ Scraper   │───▶│ Classifier   │───┐       │                │
│  └──────────┘    └──────────────┘   │       │                │
│                                      │       │                │
│  ┌──────────────────┐               │       │                │
│  │ Voice Newsletter  │               │       │                │
│  │ Generator         │◄──────────────┘       │                │
│  │ (Opus 4.6)        │                       │                │
│  └────────┬─────────┘                       │                │
│           │  ▲                               │                │
│           │  │ voice materials               │                │
│           │  │ (300KB cached)                │                │
│           │  │                               │                │
│  ┌────────┼──┴──────────┐                   │                │
│  │ Supabase Storage     │                   │                │
│  │ kindora-files/       │                   │                │
│  │ voice-materials/     │                   │                │
│  └──────────────────────┘                   │                │
│                                              │                │
└──────────────────────────────────────┬───────┼────────────────┘
                                       │       │
                              ┌────────▼───────▼────────┐
                              │     Content Store        │
                              │  (Supabase tables)       │
                              └────────┬───────┬────────┘
                                       │       │
                              ┌────────▼─┐  ┌──▼────────┐
                              │ LinkedIn  │  │ MailerLite│
                              │ Publisher │  │ Newsletter│
                              └──────────┘  └───────────┘
```

### Database Tables (Implemented)

Migration: `supabase/migrations/20260228100000_create_grant_brief_content_tables.sql`

All 4 tables are in `public` schema with RLS enabled (service_role-only policies). No user-facing queries.

```sql
-- 1. newsletter_editions (created first for FK references)
CREATE TABLE public.newsletter_editions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  edition_number INTEGER NOT NULL,
  edition_date DATE NOT NULL UNIQUE,
  subject_line TEXT NOT NULL,
  preview_text TEXT,
  editors_pick_content_id UUID,        -- FK to grant_brief_content (circular, added via ALTER TABLE)
  html_content TEXT,                   -- Full newsletter HTML (assembled by NewsletterComposer)
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'composed', 'sent')),
  mailerlite_campaign_id TEXT,
  send_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  open_rate NUMERIC(5,2),
  click_rate NUMERIC(5,2),
  subscriber_count INTEGER,
  unsubscribe_count INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. grant_brief_content (main content table)
CREATE TABLE public.grant_brief_content (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_type TEXT NOT NULL
    CHECK (content_type IN ('grant_feature', 'funder_spotlight', 'deadline_roundup', 'philanthropy_pulse')),
  theme TEXT NOT NULL,
  scheduled_date DATE NOT NULL,
  funder_program_id UUID REFERENCES funder_programs(id),
  us_foundation_ein TEXT,
  headline TEXT NOT NULL,
  body TEXT NOT NULL,
  grant_amount_display TEXT,
  deadline_display TEXT,
  target_audience TEXT,
  feature_score NUMERIC(5,2),
  ai_enrichment_data JSONB,            -- Stage 4 AI enrichment output
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'approved', 'published', 'rejected', 'queued_for_personal', 'publish_failed')),
  publishing_account TEXT NOT NULL DEFAULT 'company'
    CHECK (publishing_account IN ('company', 'personal')),  -- Sat=personal, all others=company
  published_at TIMESTAMPTZ,
  linkedin_post_url TEXT,
  linkedin_post_id TEXT,               -- LinkedIn URN for engagement polling
  engagement_data JSONB,               -- {likes, comments, shares} from LinkedIn socialActions API
  newsletter_edition_id UUID REFERENCES newsletter_editions(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()  -- trigger: update_grant_brief_content_updated_at()
);

-- 3. philanthropy_influencers
CREATE TABLE public.philanthropy_influencers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  linkedin_url TEXT NOT NULL UNIQUE,
  organization TEXT,
  signal_category TEXT NOT NULL
    CHECK (signal_category IN ('capital_allocator', 'infrastructure', 'media_analyst', 'equity_community', 'impact_investing')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  notes TEXT,
  last_scraped_at TIMESTAMPTZ,
  scrape_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. influencer_insights
CREATE TABLE public.influencer_insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  influencer_id UUID NOT NULL REFERENCES philanthropy_influencers(id),
  source_post_url TEXT UNIQUE,         -- Apify post URL, dedup key
  post_date DATE,
  post_text TEXT,                      -- Full post text (for reclassification)
  topic TEXT,                          -- AI-classified topic (1-phrase summary)
  signal_type TEXT NOT NULL,           -- One of 5 categories matching influencer signal_category
  insight_summary TEXT NOT NULL,
  relevance_score NUMERIC(3,2),        -- 0-1, funding relevance
  dedup_cluster_id UUID,              -- Groups related posts about same event
  used_in_edition BOOLEAN NOT NULL DEFAULT FALSE,
  edition_id UUID REFERENCES newsletter_editions(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Key design decisions:**
- `publishing_account` auto-derived from day: Saturday → `personal`, all others → `company`
- `status` includes `queued_for_personal` and `publish_failed` beyond standard draft/approved/published flow
- `content_type` uses 4 values covering all 7 days (grant_feature for Mon-Fri, funder_spotlight for Wed, etc.)
- Circular FK between newsletter_editions.editors_pick_content_id and grant_brief_content handled via deferred ALTER TABLE
- `influencer_insights.signal_type` matches the 5 `signal_category` values from philanthropy_influencers

### Backend Services (Implemented)

| Service | Location | Purpose |
|---------|----------|---------|
| `GrantBriefSelectorService` | `services/grant_brief/selector_service.py` | 6-stage pipeline: multi-path search, symbolic scoring, diversity filter, AI enrichment. Plus variant pipelines for spotlight/pulse/deadlines. |
| `GrantBriefContentGenerator` | `services/grant_brief/content_generator.py` | Claude Sonnet for LinkedIn posts (4 content types), Claude Haiku for newsletter sections + subject lines. Dignity-forward voice guide baked into system prompts. |
| `LinkedInPublisher` | `services/grant_brief/publisher_service.py` | Publishes company posts via LinkedIn Marketing API v2 (`ugcPosts`). Queues personal posts for manual posting. Fetches engagement data via `socialActions` endpoint. |
| `InfluencerMonitorService` | `services/grant_brief/influencer_service.py` | Seeds 49 influencers, scrapes via Apify `harvestapi/linkedin-profile-posts`, classifies with GPT-5 nano, deduplicates by topic. |
| `VoiceNewsletterGenerator` | `services/grant_brief/voice_newsletter_generator.py` | Claude Opus 4.6 voice-first newsletter generator. Loads 300KB of Justin's writing from Supabase storage as voice training context. Generates entire newsletter in one pass. |
| `NewsletterComposer` | `services/grant_brief/newsletter_service.py` | Assembles weekly editions from week's content. Uses `VoiceNewsletterGenerator` (Opus 4.6, default) or falls back to section-by-section Haiku generation. Sends via MailerLite API v2. |

### API Endpoints (Implemented)

Router: `api/routes/grant_brief.py`, prefix `/grant-brief` (registered in `main.py` via `app.include_router(grant_brief.router, prefix=settings.API_V1_STR)`).
All endpoints require API token auth via `require_admin` dependency.

```
# Content management (admin/internal)
GET    /api/grant-brief/content                — List content (filters: status, content_type, date range, limit)
POST   /api/grant-brief/content/generate       — Trigger 6-stage pipeline for a target_date
POST   /api/grant-brief/content/generate-week  — Generate for 7 consecutive days
PUT    /api/grant-brief/content/{id}/approve   — Set status to 'approved'
POST   /api/grant-brief/content/{id}/publish   — Publish to LinkedIn (company) or queue (personal)

# Newsletter
GET    /api/grant-brief/newsletter/editions       — List newsletter editions
POST   /api/grant-brief/newsletter/compose        — Compose next edition from week's content
POST   /api/grant-brief/newsletter/{id}/send      — Send via MailerLite

# Influencer monitoring
GET    /api/grant-brief/influencers               — List monitored influencers
POST   /api/grant-brief/influencers/scrape        — Seeds influencers (idempotent) + triggers Apify scrape
POST   /api/grant-brief/influencers/classify      — Run GPT-5 nano classification on unclassified posts
```

### Scheduled Jobs (Celery Beat)

Tasks: `tasks/grant_brief_tasks.py`. All tasks check `ENABLE_GRANT_BRIEF_CONTENT` feature flag before running. All are idempotent.

| Task | Schedule | Time (UTC / ET) | Action |
|------|----------|-----------------|--------|
| `generate_daily_content_task` | Daily | 10:00 UTC / 5:00 AM ET | Runs 6-stage pipeline for today's theme. Skips if content already exists. |
| `publish_daily_content_task` | Mon-Fri | 14:00 UTC / 9:00 AM ET | Publishes approved company posts to LinkedIn. |
| `publish_daily_content_task` | Sat-Sun | 15:00 UTC / 10:00 AM ET | Publishes approved content (queues personal posts for Saturday). |
| `scrape_influencers_task` | Weekly Sun | 07:00 UTC / 2:00 AM ET | Full pipeline: seed → scrape → classify → deduplicate. |
| `compose_newsletter_task` | Weekly Mon | 23:00 UTC / 6:00 PM ET | Assembles weekly edition from Tue-Mon content. Auto-calculates next Tuesday as edition date. |
| `send_newsletter_task` | Weekly Tue | 13:00 UTC / 8:00 AM ET | Sends latest composed edition via MailerLite. Auto-finds most recent 'composed' edition. |

**Note**: Uses `@celery_app.task(bind=True, name=...)` pattern (not `@shared_task`), matching existing codebase convention. Tasks registered in `core/celery_app.py` include list, task_routes, beat_schedule, and explicit imports.

### LinkedIn Publishing (Implemented)

Uses **LinkedIn Marketing API v2** via company page (`ugcPosts` endpoint).

**Config** (env vars in `core/config.py`):
- `LINKEDIN_CLIENT_ID` — OAuth app client ID
- `LINKEDIN_CLIENT_SECRET` — OAuth app client secret
- `LINKEDIN_ACCESS_TOKEN` — Bearer token (expires every 60 days — manual refresh for now)
- `LINKEDIN_COMPANY_URN` — format `urn:li:organization:XXXXX`

**Flow**:
1. `LinkedInPublisher.publish_company_post(content_id)` — fetches content from DB, validates status, calls LinkedIn API
2. LinkedIn API: `POST https://api.linkedin.com/v2/ugcPosts` with `X-Restli-Protocol-Version: 2.0.0`
3. Post URN returned in `X-RestLi-Id` response header
4. On success: updates DB with `status='published'`, `published_at`, `linkedin_post_id`, `linkedin_post_url`
5. On 429 (rate limit): retry once. On other errors: mark `status='publish_failed'`
6. `fetch_engagement_data(content_id)` — polls `/socialActions/{urn}` for likes/comments/shares

### Cost Projections

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| **Anthropic Claude Sonnet** (content generation) | ~$8-15 | 30 LinkedIn posts/month × ~1000 tokens/post. Claude Sonnet `claude-sonnet-4-20250514` for high-quality creative writing. |
| **Anthropic Claude Opus 4.6** (voice newsletter) | ~$6-8 | 4 editions/month × ~$1.50-2.00 each. Full newsletter in Justin's voice via `claude-opus-4-6`. Includes 95K input tokens of voice training materials. |
| **Anthropic Claude Haiku** (newsletter fallback) | ~$0-1 | Fallback section-by-section generation if voice mode disabled. Claude Haiku `claude-haiku-4-5-20251001`. |
| **OpenAI GPT-5 mini** (AI enrichment) | ~$5-10 | Stage 4 enrichment: 15-20 candidates × 2000 max_completion_tokens × 30 days. |
| **OpenAI GPT-5 nano** (influencer classification) | ~$0.50 | ~600 posts/month classified at ~$0.005/1000 posts. |
| **OpenAI text-embedding-3-small** (vector search) | ~$0.50 | Theme + archetype embeddings, ~60/month. |
| Apify (influencer scraping) | ~$6 | 49 influencers × 15 posts × 4 weeks = ~2,940 posts/month |
| MailerLite | $0 | Free tier covers up to 1,000 subscribers |
| DataForSEO (periodic research) | ~$5 | Quarterly keyword refresh |
| LinkedIn API | $0 | Free tier for organic posting |
| **Total** | **~$27-43/month** | |

**Cost tracking**: All AI API calls (OpenAI + Anthropic) are tracked via `utils/token_pricing.py`. The `GrantBriefContentGenerator` exposes a `total_cost` property for per-session cost aggregation.

---

## 7. Admin Review Dashboard (kindora-analytics)

The admin dashboard at `/grant-brief` in kindora-analytics provides the full content review workflow. No curl commands needed — everything from content generation to LinkedIn publishing is handled through the UI.

### Architecture

**BFF Proxy + Direct Supabase**:
- **Reads**: Direct Supabase queries via service role client (`src/lib/supabase.ts`) — fast, no Python API round-trip
- **Complex operations** (generate, publish, compose, send, scrape, classify): Proxied to Python API via catch-all route `src/app/api/grant-brief/[...path]/route.ts`
- **Route precedence**: Next.js resolves static routes (`content/route.ts`) before catch-all (`[...path]/route.ts`), so reads hit Supabase directly while POST operations fall through to the proxy

### Files

| File | Purpose |
|------|---------|
| `src/app/api/grant-brief/[...path]/route.ts` | BFF proxy to Python API (cloned from KB proxy pattern) |
| `src/app/api/grant-brief/content/route.ts` | Content list + aggregate stats (direct Supabase) |
| `src/app/api/grant-brief/content/[id]/route.ts` | Content detail, edit (PATCH), approve/reject (PUT), delete (DELETE) |
| `src/app/api/grant-brief/newsletter/route.ts` | Newsletter editions list + subscriber count |
| `src/app/api/grant-brief/influencers/route.ts` | Influencer list + per-influencer insight counts |
| `src/app/grant-brief/page.tsx` | Main page: stats cards, tab bar, filter bar, content list, calendar toggle |
| `src/components/grant-brief/ContentDetailModal.tsx` | Full content view/edit modal with approve/reject/publish/delete actions |
| `src/components/grant-brief/GenerateContentModal.tsx` | AI content generation (single day or full week) |
| `src/components/grant-brief/NewsletterTab.tsx` | Newsletter editions table, compose, preview (sandboxed iframe), send |
| `src/components/grant-brief/InfluencerTab.tsx` | Influencer table, seed & scrape, classify posts |
| `src/components/grant-brief/ContentCalendar.tsx` | 7-day week calendar view with week navigation |
| `src/components/Navigation.tsx` | Added `Newspaper` icon + `/grant-brief` nav entry |

### Admin Workflow

1. **Generate**: Click "Generate Content" → pick date → generates via 6-stage AI pipeline (~10-30s per day)
2. **Review**: Content list shows all items with status badges. Click a row → full detail modal with headline, body, metadata, AI enrichment data
3. **Edit**: Modify headline/body inline in the modal. Character count tracks LinkedIn's ~3000 char limit
4. **Approve/Reject**: Status transitions with confirmation dialog. Rejected items can be re-approved
5. **Publish**: Approved items get a "Publish to LinkedIn" button → calls LinkedIn Marketing API
6. **Calendar**: Visual 7-day grid view. Empty days show "Generate" button. Click content cards to open detail modal
7. **Newsletter**: Compose editions (defaults to next Tuesday), preview HTML in sandboxed iframe, send via MailerLite
8. **Influencers**: Seed & scrape LinkedIn profiles (batch size 5/10/15), classify posts with GPT-5 nano

### Content Status Flow (in UI)

```
draft ──→ approved ──→ published (company LinkedIn, Mon-Fri)
  │           │              └──→ queued_for_personal (Saturday personal)
  │           └──→ rejected ──→ (can re-approve)
  └──→ rejected
  └──→ (delete: only draft/rejected)
```

---

## 8. Backend Implementation Status

### v1 Complete (2026-03-01)
- [x] Database tables: 4 tables in `public` schema with RLS (migration `20260228100000`)
- [x] `GrantBriefSelectorService`: 6-stage pipeline with 4 search paths, symbolic scoring, diversity filter, GPT-5 mini enrichment
- [x] `GrantBriefContentGenerator`: Claude Sonnet for LinkedIn posts, Claude Haiku for newsletter sections, dignity-forward voice guide
- [x] `LinkedInPublisher`: LinkedIn Marketing API v2 integration + personal post queuing
- [x] `NewsletterComposer`: 5-section weekly edition assembly + MailerLite API integration
- [x] `InfluencerMonitorService`: 49 influencers seeded, Apify scraping, GPT-5 nano classification, topic-based dedup
- [x] API Routes: 11 endpoints on `/api/grant-brief/*` with admin auth
- [x] Celery Tasks: 5 scheduled tasks with daily/weekly beat schedule
- [x] Edge Function: `sync-mailerlite-newsletter` deployed to Supabase
- [x] Production Migration: All tables applied to production with RLS policies
- [x] Production E2E Test Suite: 37 tests across 4 cost tiers (smoke/critical/moderate/expensive) — 36 pass, 1 skip (generate-week timeout). Test file: `tests/production/test_grant_brief.py`
- [x] Admin Dashboard: Full review UI in `kindora-analytics` at `/grant-brief` — content list, detail modal, calendar view, newsletter tab, influencer tab, generate controls

### v1.1 Voice Newsletter (2026-03-02)
- [x] `VoiceNewsletterGenerator`: Claude Opus 4.6 voice-first newsletter generation (~$1.50-2.00/edition)
- [x] Voice training materials uploaded to Supabase storage (`kindora-files/voice-materials/`)
- [x] Voice materials: 100+ LinkedIn posts, 10+ articles, email persona guide (150+ emails), anti-AI writing rules
- [x] `NewsletterComposer` upgraded: voice mode (default) with Haiku section-by-section fallback
- [x] Pulse insights fetch: dedicated DB query with perspective balancing + influencer name enrichment
- [x] API route: `use_voice_mode` param on `POST /api/grant-brief/newsletter/compose` (default true)
- [x] Influencer scouting guide documented (5 signal categories, qualifying criteria, priority gaps)

### Remaining Work
- [ ] Set up LinkedIn OAuth app and get API credentials (LINKEDIN_* env vars)
- [ ] Configure MailerLite API key in production (MAILERLITE_API_KEY env var)
- [ ] Configure Apify API key in production (APIFY_API_KEY env var)
- [ ] Enable feature flag: `ENABLE_GRANT_BRIEF_CONTENT=true`
- [ ] Add newsletter archive pages to website (SEO value)
- [ ] Implement LinkedIn access token refresh (currently manual, expires every 60 days)
- [ ] Add conversion tracking (LinkedIn viewer → website visitor → signup)
- [ ] Expand influencer list from personal contacts (priority: impact investing, media/analysts — see Scouting Guide in §5)
- [ ] Test voice newsletter end-to-end with real content (compose → preview → verify voice quality)
- [ ] Update voice materials in Supabase storage when new LinkedIn posts/articles are published
- [ ] **Source link extraction**: Add `shared_url` + `shared_url_title` to `influencer_insights` table, capture `document.transcribedDocumentUrl` from Apify actor, extract URLs from post text
- [ ] **Newsletter hyperlinking**: Update classifier to output `shared_resource_url`, update Opus prompt to weave hyperlinks to primary sources (not just LinkedIn posts) into the newsletter

### Future Optimization
- [ ] A/B test post formats and times (measure clicks + downstream signups, not vanity metrics)
- [ ] Refine grant scoring algorithm based on engagement data
- [ ] Expand influencer list along 3 axes (institutional adjacency, ecosystem adjacency, representation audits)
- [ ] Quarterly SEO keyword refresh to update theme priorities
- [ ] Quarterly influencer representation audit — whose voices are making it into published content?
- [ ] Upgrade topic-based dedup to embedding cosine similarity for better clustering
- [ ] Parallelize Stage 4 AI enrichment calls with `asyncio.gather()` for lower latency
- [ ] Voice material auto-refresh: periodically re-upload LinkedIn posts/articles as new ones are published
- [ ] Voice newsletter A/B test: voice mode (Opus) vs. Haiku mode — measure open rate + click rate difference
- [ ] Newsletter click tracking: tag all hyperlinks with UTM params to measure which source links drive the most engagement
- [ ] Source quality ranking: over time, learn which sources (Chronicle, Inside Philanthropy, foundation blogs, etc.) drive the highest click-through and weight them in curation

---

## 9. Success Metrics

| Metric | Target (Month 3) | Target (Month 6) |
|--------|-------------------|-------------------|
| LinkedIn followers | +500 | +2,000 |
| LinkedIn post impressions (avg) | 1,000/post | 5,000/post |
| Newsletter subscribers | 200 | 1,000 |
| Newsletter open rate | 35% | 40% |
| Newsletter → signup conversion | 5% | 8% |
| LinkedIn → website visits | 50/week | 200/week |
| Overall signup attribution | 20/month | 100/month |

### Tracking

- **LinkedIn**: Native analytics (impressions, engagement rate, follower growth)
- **Newsletter**: MailerLite analytics (open rate, click rate, unsubscribes)
- **Conversions**: `newsletter_subscribers.converted_at` + UTM parameter tracking on Kindora links
- **Mixpanel**: Track `content_marketing_signup` events with source attribution

---

## Appendix A: Theme-to-NTEE Code Mapping

| Theme | NTEE Codes | Additional Keywords |
|-------|------------|-------------------|
| Education & Youth | B (Education), O (Youth Development) | school, university, STEM, literacy, scholarship, after-school, mentoring |
| Community & Housing | L (Housing), S (Community Improvement), P (Human Services) | housing, community development, rural, neighborhood, homelessness |
| Arts & Culture | A (Arts, Culture, Humanities) | arts, music, theater, cultural, museum, heritage, creative |
| Tech & AI for Good | U (Science & Technology) | AI, artificial intelligence, machine learning, digital transformation, tech for good, social impact technology, innovation, STEM, civic tech, data science, digital equity, startup accelerator |
| Faith-Based | X (Religion-Related) | church, faith, ministry, religious, congregation |
| Veterans & Military | W (Public, Society Benefit - military) | veteran, military, service member, armed forces |
| Animal Welfare | D (Animal-Related) | animal, wildlife, rescue, conservation, shelter |
| Environment & Climate | C (Environment) | environment, climate, sustainability, conservation, clean energy |
| Health & Wellness | E (Health), F (Mental Health) | health, mental health, wellness, substance abuse, disability |
| Seniors & Aging | N/A (cross-cutting) | senior, aging, elder, retirement, geriatric |

## Appendix B: Full SEO Keyword Data

<details>
<summary>Click to expand full keyword research results (182 keywords)</summary>

### Education Grants
| Keyword | Monthly Volume |
|---------|---------------|
| grants for education | 3,600 |
| education grants for nonprofits | 2,400 |
| STEM grants | 1,600 |
| literacy grants | 1,300 |
| school grants for nonprofits | 1,300 |
| after-school program grants | 1,000 |
| early childhood education grants | 880 |
| special education grants | 720 |
| scholarship grants for nonprofits | 590 |
| higher education grants | 500 |

### Community Development
| Keyword | Monthly Volume |
|---------|---------------|
| community development grants | 2,900 |
| housing grants for nonprofits | 2,400 |
| rural development grants | 1,900 |
| neighborhood grants | 1,300 |
| affordable housing grants | 1,000 |
| community foundation grants | 880 |
| economic development grants | 720 |
| food bank grants | 480 |
| homeless shelter grants | 270 |

### Arts & Culture
| Keyword | Monthly Volume |
|---------|---------------|
| arts grants for nonprofits | 2,400 |
| NEA grants | 1,900 |
| music program grants | 1,300 |
| cultural preservation grants | 590 |
| theater grants | 480 |
| museum grants | 390 |
| public art grants | 270 |
| film grants for nonprofits | 160 |

### Technology & Innovation
| Keyword | Monthly Volume |
|---------|---------------|
| technology grants for nonprofits | 1,900 |
| digital transformation grants | 1,300 |
| STEM grants for nonprofits | 1,300 |
| AI grants for nonprofits | 590 |
| cybersecurity grants | 390 |
| digital literacy grants | 320 |
| tech innovation grants | 280 |

### Faith-Based
| Keyword | Monthly Volume |
|---------|---------------|
| church grants | 1,900 |
| faith-based grants | 1,300 |
| religious organization grants | 720 |
| ministry grants | 590 |

### Veterans & Military
| Keyword | Monthly Volume |
|---------|---------------|
| grants for veteran organizations | 1,300 |
| veteran nonprofit grants | 720 |
| military family grants | 590 |
| veteran housing grants | 310 |

### Animal Welfare
| Keyword | Monthly Volume |
|---------|---------------|
| animal welfare grants | 720 |
| animal rescue grants | 480 |
| wildlife conservation grants | 480 |
| pet shelter grants | 300 |

### Startup / Small Org
| Keyword | Monthly Volume |
|---------|---------------|
| startup grants for nonprofits | 720 |
| new nonprofit funding | 480 |
| seed funding for nonprofits | 320 |
| first-time grants | 300 |

### Environment & Climate
| Keyword | Monthly Volume |
|---------|---------------|
| environmental grants | 590 |
| climate change grants | 480 |
| conservation grants | 390 |
| sustainability grants | 270 |

### Youth Development
| Keyword | Monthly Volume |
|---------|---------------|
| youth program grants | 590 |
| after-school grants | 480 |
| mentoring grants | 320 |
| juvenile justice grants | 270 |

### Health & Wellness
| Keyword | Monthly Volume |
|---------|---------------|
| health grants for nonprofits | 590 |
| mental health grants | 480 |
| substance abuse grants | 320 |
| wellness program grants | 240 |

### Seniors & Aging
| Keyword | Monthly Volume |
|---------|---------------|
| grants for senior programs | 590 |
| aging services grants | 390 |
| elder care grants | 270 |
| senior center grants | 210 |

### Grant Deadlines / Urgency
| Keyword | Monthly Volume |
|---------|---------------|
| grant deadlines this month | 590 |
| grants closing soon | 390 |
| emergency grants for nonprofits | 270 |
| last-minute grants | 180 |

### Social Justice & Equity
| Keyword | Monthly Volume |
|---------|---------------|
| social justice grants | 320 |
| racial equity grants | 210 |
| DEI grants for nonprofits | 110 |
| civil rights grants | 60 |

### International Development
| Keyword | Monthly Volume |
|---------|---------------|
| international development grants | 320 |
| global health grants | 210 |
| humanitarian aid grants | 100 |
| foreign aid grants | 50 |

</details>
