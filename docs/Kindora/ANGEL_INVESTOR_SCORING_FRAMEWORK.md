# Kindora Angel Investor Intelligence System

Complete reference for finding, qualifying, and scoring angel investors from Justin's professional network for Kindora's mission-aligned raise.

## Capital Strategy

- **Instrument:** Convertible notes or SAFEs, founder-friendly terms, no board seats
- **Check size:** $10K-$50K per investor
- **Target raise:** $200K-$400K total
- **Entity:** Delaware Public Benefit Corporation (mission-protected)
- **Return profile:** Modest and long-dated (not a 10x VC bet)
- **NOT raising VC** — looking for mission-aligned individuals who believe in the mission and want to support early growth

## The Core Insight: Investing ≠ Philanthropy

The scoring model is built on a fundamental insight that distinguishes angel investment prospecting from donor prospecting:

**Investors get their money back (and more) if the company succeeds.** This has three major implications:

1. **Relationship matters LESS than in philanthropy.** A donation is pure generosity — the donor needs deep personal trust. An angel investment offers financial return, so people with weaker ties may still invest if the opportunity is compelling. Sophisticated investors routinely write checks to founders they barely know.

2. **Risk capital capacity is the DOMINANT factor.** Not just "can they afford it" but "can they afford to LOSE it entirely and not notice?" Angel investments are illiquid (5-10 years), high risk of total loss (most startups fail), and concentrated (a single check, not a portfolio). The check must be trivial relative to their wealth.

3. **Close relationships can actually HURT** if the check size exceeds the person's comfortable risk capital. Asking a close friend to invest $25K they can't afford to lose strains the friendship regardless of outcome — and creates anxiety and resentment if the startup struggles. A $25K loss is devastating to someone with $500K net worth but invisible to someone with $5M+.

## Three-Stage Pipeline

### Stage 1: PitchBook Enrichment (Find Hidden Investors)

61% of network contacts who score well on relationship + alignment have zero visible investor signals on LinkedIn. PitchBook surfaces hidden angel activity.

**How it works:**
1. Search PitchBook by last name via `parseforge/pitchbook-investors-scraper` Apify actor
2. GPT-5 mini evaluates all results against LinkedIn info (name, company, position, headline) and confirms identity match
3. GPT-5 mini classifies investing context into taxonomy:

| Context | Description | Signal Strength |
|---------|-------------|-----------------|
| `personal` | Individual angel investments with own money | **Strongest** — exactly our target |
| `institutional_forprofit` | Invests through VC, PE, hedge fund, or family office | Moderate — understands investing but may have fund mandate conflicts |
| `institutional_philanthropic` | Deploys grants/PRIs through foundation or impact fund | Moderate — understands mission-driven capital but may not do for-profit |
| `both` | Personal angel activity AND institutional role | **Strong** — angel activity + domain expertise |

4. Results stored in `pitchbook_data` JSONB column on contacts table

**Cost:** ~$0.15-0.25 per contact (Apify actor) + ~$0.001 (GPT-5 mini validation)

**Running:**
```bash
source .venv/bin/activate && cd scripts/intelligence

# Search ready_now tier only
python enrich_pitchbook_investors.py --segment ready_now --workers 10

# Search specific contacts by ID
python enrich_pitchbook_investors.py --ids 123,456,789 --workers 10

# Search contacts with investor keywords in their headline/position
python enrich_pitchbook_investors.py --ids $(IDS_FROM_QUERY) --workers 10
```

### Stage 1b: SEC EDGAR Filing Enrichment (Free, Complementary to PitchBook)

EDGAR catches investors PitchBook misses — people who appear in SEC filings (Form D private placements, insider ownership Forms 3/4/5) but don't have formal PitchBook profiles.

**How it works:**
1. Search EDGAR EFTS API by full quoted name `"{first_name} {last_name}"`
2. For Form D/D/A hits, fetch the XML to extract `relatedPersonsList` (names, addresses, roles)
3. GPT-5 mini validates matches cross-referencing name, career/company, geography, and filing context against LinkedIn profile
4. Results stored in `edgar_data` JSONB column on contacts table

**What EDGAR catches that PitchBook misses:**
- Mitch Kapor: 2 Form D filings (BlocPower, UniversityNow) — investor in mission-aligned companies
- Tyler Scriven: 1 Form D filing (RoadSync) — founder/promoter of his own startup

**What EDGAR doesn't catch:**
- Investors who invest through entities (Freada Kapor Klein through Kapor Capital)
- Early-stage angels whose deals don't file Form D
- Common names produce false positives — GPT validation is critical (John Grossman: 10 filings, all different person)

**Signal classification:**
| Signal | Criteria | Meaning |
|--------|----------|---------|
| `strong` | 3+ Form D filings as Director/Promoter across different companies | Serial investor or serial entrepreneur |
| `moderate` | 1-2 Form D filings, or Forms 3/4/5 (insider at public company) | Some investment activity |
| `weak` | Only Executive Officer at own company | Operator, not investor |

**Cost:** FREE (EDGAR EFTS API, no API key) + ~$0.001/contact (GPT-5 mini validation)

**Running:**
```bash
source .venv/bin/activate && cd scripts/intelligence

# Search specific contacts
python enrich_edgar_filings.py --ids 123,456

# Search all high-potential contacts
python enrich_edgar_filings.py --segment all
```

### Stage 2: Investor-Signal Screening (Target the Right Contacts)

Rather than running PitchBook on every contact (expensive, low hit rate), screen the full network for investor signals first.

**LinkedIn keyword screening** (SQL query against `headline` and `position` columns):
- angel invest, venture, investor, venture capital
- managing partner, general partner, founding partner
- private equity, family office

**Hit rate comparison:**

| Strategy | Contacts Searched | Matches | Hit Rate |
|----------|-------------------|---------|----------|
| Score-based (ready_now) | 116 | 7 | 6.0% |
| Score-based (cultivate_first, top 50) | 50 | 1 | 2.0% |
| **Investor-signal screening** | **149** | **18** | **12.2%** |

Investor-signal screening is 2x more efficient than score-based and 6x more efficient than random cultivate_first sampling.

**Current coverage:** 29 contacts matched to PitchBook investor profiles across all runs.

### Stage 3: AI Scoring (Rank and Prioritize)

GPT-5 mini scores every contact (0-100) against a capacity-weighted angel investor psychology framework. Five scoring pillars, in order of importance:

#### Pillar 1: Risk Capital Capacity (PRIMARY — weighted most heavily)

Not just SEC accredited status ($200K+ income or $1M+ net worth excl. primary residence). The real question: **can this person lose $10K-$50K entirely without any impact on their lifestyle, financial security, or emotional wellbeing?**

Best practices say allocate 5-15% of investable portfolio to angel deals, spread across 10-20+ investments. So:
- For a $25K check → need $170K-$500K+ in investable assets (NOT primary residence, retirement, or emergency fund)
- For a $50K check → need $330K-$1M+ in investable assets

| Risk Capital Level | Profile | Check Size |
|-------------------|---------|------------|
| **HIGH** (can lose $50K without noticing) | VP+ at FAANG 5+ yr, founders with exits, senior partners at top firms, PitchBook-verified angels | $25K-$50K |
| **MODERATE** (can handle $10-25K) | Senior tech directors, mid-tier firm partners, C-suite at mid-size cos | $10K-$25K |
| **LOW** (DO NOT recommend) | Nonprofit/gov/education at any level, consultants, early-career, career transitions, active political candidates, family office/foundation *staff* (not principals) | Not recommended |

**Hard evidence signals (weight heavily — evidence OVERRIDES title inference):**
- FEC political donations $25K+ → extremely strong accreditation signal. $0 FEC for a senior leader is a NEGATIVE signal.
- PitchBook data showing prior angel investments → direct evidence of capacity + willingness + sophistication
- Real estate as OWNER with high Zestimate → asset wealth (but consider mortgage obligations). Modest home (<$700K in low-COL area) for a senior professional is a negative signal.
- Prior angel investments or startup board positions → strongest evidence

**Evidence hierarchy:** When hard evidence (FEC, real estate, PitchBook) contradicts title-based inference, hard evidence wins. "President & CIO, Family Office" with $0 FEC and a $565K home = LOW capacity despite impressive title.

**Title traps to avoid:**
- **Family office/foundation staff ≠ principals:** "President of Family Office" may be a salaried employee managing someone else's money, not the wealthy family member.
- **Active political candidates:** Campaigns consume all discretionary funds. Even if someone previously had capacity, an active race (especially federal) drains personal savings. Score as long_term; revisit after election.
- **Nonprofit/gov/education careers:** NO equity wealth regardless of title. A nonprofit CEO making $400K has no stock options, no equity upside, no liquidity events.

#### Pillar 2: Mission Alignment with Kindora

PBC structure means the company will always prioritize nonprofit access over profit maximization. Investors must believe in the mission.

**Strong signals:** Philanthropic career, Google.org/foundation alumni, nonprofit tech experience, social impact investing, AI-for-good interest, FEC donations to education/equity causes

**Weak/negative signals:** Pure ROI seekers, no philanthropic touchpoints, competitors/advisors to competitors

#### Pillar 3: Investment Sophistication

| Level | Signals | Conversion Likelihood |
|-------|---------|----------------------|
| **Experienced angel** | "Angel investor" in headline, PitchBook portfolio, startup boards, VC/PE experience | **Highest** — they know the playbook. Need LESS relationship depth to convert. |
| **Sophisticated, not angel** | Finance professionals, foundation grant deployers, corporate venture | Good — bridge from their expertise |
| **First-time angel** | High-capacity + mission-aligned, no investment experience | Needs education on SAFE mechanics, risk, illiquidity |
| **Non-investor** | Never invested outside public markets, risk-averse | Low unless exceptional alignment + warmth |

**Key insight:** Experienced investors with moderate relationships (familiarity 2) ARE strong prospects. They invest based on opportunity quality, not just personal connection. Do not penalize for weak relationship if sophistication is high.

#### Pillar 4: Relationship & Trust (Important but NOT Dominant)

Unlike philanthropy where relationship is #1, angel investing offers financial upside that partially substitutes for relationship depth. The trust threshold is lower because there's a financial incentive.

**How relationship interacts with capacity:**

| Capacity | Close (3-4) | Moderate (2) | Weak/None (0-1) |
|----------|-------------|-------------|-----------------|
| HIGH ($5M+) | **IDEAL** — direct ask | **STRONG** — deal quality drives decision | Possible via warm intro |
| MODERATE ($1-2M) | Good — right-size check | Decent — needs cultivation | Unlikely unless experienced |
| LOW (<$500K) | **AVOID** — risks friendship | Not a fit | Not a fit |

**Data sources:** `familiarity_rating` (0-4), `comms_closeness`, `comms_momentum`, `comms_last_date`, `comms_thread_count`, `comms_meeting_count`, `linkedin_reactions`

#### Pillar 5: Strategic Value Beyond Capital

A $25K check from someone who opens doors > $50K from a passive investor:
- Customer introductions (foundation officers → nonprofit customers)
- Fundraising credibility (recognized names compress future diligence)
- Domain expertise (philanthropy, SaaS, nonprofit tech, AI/ML)
- Amplification (LinkedIn following, media presence, speaking)
- Operational experience (founders, enterprise sales, PBC governance)

## Tier Definitions (Capacity-Weighted)

| Score | Tier | Meaning | Action |
|-------|------|---------|--------|
| 80-100 | **ready_now** | HIGH risk capital + aligned + some relationship + investment-savvy. Relationship can be moderate (familiarity 2+) if capacity and sophistication are strong. | Direct investment conversation. Close in 2-4 weeks. |
| 60-79 | **cultivate_first** | Good capacity + alignment but needs cultivation. Also: strong relationship + moderate capacity where $10K could work. | Warm relationship or explain opportunity. Ask in 1-3 months. |
| 40-59 | **long_term** | Has some capacity or alignment but missing key elements. | 4-8 touchpoints over 3-6 months. |
| 20-39 | **long_term** | Distant connection, weak alignment, or uncertain capacity. | Only if very high capacity + warm intro path. |
| 0-19 | **not_a_fit** | Insufficient risk capital (a $10K loss would matter), no relationship path, no alignment, or disqualifying. | Do not pursue. |

## Current Results (March 2026, Capacity-Weighted Prompt v2)

**2,944 contacts scored:**

| Tier | Count | % |
|------|-------|---|
| ready_now | 153 | 5.2% |
| cultivate_first | 1,824 | 62.0% |
| long_term | 423 | 14.4% |
| not_a_fit | 544 | 18.5% |

**Comparison to v1 (relationship-weighted prompt):**

| Change | v1 → v2 | Why |
|--------|---------|-----|
| not_a_fit: 387 → 544 (+157) | Capacity filter working | Nonprofit careers, early-career, low-wealth contacts correctly filtered out |
| ready_now: 126 → 153 (+27) | Sophistication elevated | Experienced investors with moderate relationships scoring higher |
| cultivate_first: 2,020 → 1,824 (-196) | Downgraded to not_a_fit | Many had impressive titles but insufficient risk capital |

**Top prospects (v2):**
1. Freada Kapor Klein (94) — Kapor Capital founding partner, 381 PitchBook investments
2. Mitch Kapor (94) — Warm connection, December 2025 email exchange, growing momentum
3. Candice Morgan (92) — Google family overlap, familiarity 3, mission alignment
4. Michael Ellison (92) — Close collaborator (familiarity 4), CodePath CEO
5. Gerald Chertavian (92) — Close mentor (familiarity 4), Year Up founder

**Validation — close friends with limited capacity correctly protected:**
- Malia Griggs-Murphy (familiarity 4, admin role) → not_a_fit (12)
- Jade Craig (familiarity 4, asst professor, $310K home, $660 FEC) → not_a_fit (12)
- Karol Steele (familiarity 4, Justin's mother) → not_a_fit (10)

**Validation — wealthy acquaintances correctly surfaced:**
- Imo Udom (familiarity 0, but high-capacity profile) → ready_now (82)
- Lorena C (familiarity 0, Google/Google.org overlap) → ready_now (90)

## Disqualifying Signals (not_a_fit)

- Insufficient risk capital — below accredited threshold, or $10K check would cause financial stress
- No relationship path — cold contact, no mutual connections, no intro route
- Pure ROI seekers who would push for mission-compromising exits
- Conflicts of interest — work at or advise Kindora competitors (Blackbaud, Instrumentl, GrantStation)
- Financial distress or career transition — shouldn't make illiquid investments
- Governance control demands on small checks

## Output Fields (from `ask_readiness.kindora_angel_investment` JSONB)

| Field | Meaning |
|-------|---------|
| `score` | 0-100 overall angel prospect score |
| `tier` | ready_now / cultivate_first / long_term / not_a_fit |
| `reasoning` | Decision-ready paragraph: capacity assessment, mission fit, investment experience, relationship, key risk/opportunity |
| `recommended_approach` | Best outreach channel |
| `ask_timing` | now / after_cultivation / after_reconnection / not_recommended |
| `suggested_ask_range` | Check size: "$25K-$50K", "$10K-$25K", "$10K", "Not recommended" |
| `personalization_angle` | Why Kindora resonates for this person as an investor |
| `cultivation_needed` | Specific, time-bound steps to get to investment conversation |
| `receiver_frame` | What they'd want to hear, from their perspective |
| `risk_factors` | Things that could backfire |

## Technical Details

### Scripts
| Script | Purpose | Cost |
|--------|---------|------|
| `scripts/intelligence/enrich_pitchbook_investors.py` | PitchBook enrichment + GPT match validation | ~$0.15-0.25/contact |
| `scripts/intelligence/enrich_edgar_filings.py` | SEC EDGAR filing enrichment + GPT match validation | FREE (EDGAR) + ~$0.001/contact (GPT) |
| `scripts/intelligence/score_ask_readiness.py --goal kindora_angel_investment` | Full scoring run | ~$6 for all 2,944 contacts |

### Infrastructure
- **Model:** GPT-5 mini (150 concurrent workers for scoring, 10 for PitchBook)
- **PitchBook actor:** `parseforge/pitchbook-investors-scraper` ($0.0475/result), Apify Scale plan
- **EDGAR API:** `efts.sec.gov/LATEST/search-index` (free, no API key, rate-limit 0.25s between requests)
- **Storage:** `contacts.ask_readiness` JSONB (keyed by `kindora_angel_investment`), `contacts.pitchbook_data` JSONB, `contacts.edgar_data` JSONB
- **UI:** `/tools/kindora-angel` page at `steele-contacts.vercel.app`
- **API:** `/api/network-intel/kindora-angel` (GET for list, PATCH for tier overrides)

### Running a full refresh
```bash
source .venv/bin/activate && cd scripts/intelligence

# 1a. (Optional) Enrich new contacts with PitchBook
python enrich_pitchbook_investors.py --segment ready_now --workers 10

# 1b. (Optional) Enrich with SEC EDGAR (free)
python enrich_edgar_filings.py --segment all

# 2. Re-score all contacts (~$6, ~8 min)
python score_ask_readiness.py --goal kindora_angel_investment --force --workers 150

# 3. Re-score specific contacts only
python score_ask_readiness.py --goal kindora_angel_investment --ids 123,456 --force

# 4. Deploy UI changes
cd ../../job-matcher-ai && npx vercel --prod --yes --scope true-steele
```

## Methodology Evolution

| Version | Date | Key Change | Impact |
|---------|------|-----------|--------|
| v1 | 2026-03-21 | Initial 5-pillar framework (relationship = "requires MORE trust than donations") | 126 ready_now, 387 not_a_fit |
| v1.1 | 2026-03-22 | Added PitchBook enrichment pipeline + investor-signal screening | 29 PitchBook-verified investors identified, 12.2% hit rate on signal-screened contacts |
| **v2** | **2026-03-22** | **Capacity-first rewrite** — risk capital is primary filter, relationship demoted, close friends with low capacity protected | **153 ready_now, 544 not_a_fit.** Wealthy acquaintances surfaced, close friends with limited means protected from asks. |
