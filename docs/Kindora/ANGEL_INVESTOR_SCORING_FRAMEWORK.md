# Kindora Angel Investor Scoring Framework

Reference document for the `kindora_angel_investment` ask-readiness scoring goal. Used to interpret AI-scored angel prospect results for Kindora's $200K-$400K mission-aligned raise.

## Capital Strategy

- **Instrument:** Convertible notes or SAFEs, founder-friendly terms, no board seats
- **Check size:** $10K-$50K per investor
- **Target raise:** $200K-$400K total
- **Entity:** Delaware Public Benefit Corporation (mission-protected)
- **Return profile:** Modest and long-dated (not a 10x VC bet)
- **NOT raising VC** — looking for mission-aligned individuals

## Five Scoring Dimensions

### 1. Financial Capacity for Angel Investing (Most Important Filter)

Accredited investor threshold: $200K+ annual income OR $1M+ net worth (excluding primary residence). A $25K check should feel non-material — well under 1% of net worth.

| Signal | Strength | Notes |
|--------|----------|-------|
| FEC donations $5K+ | **Strongest** | Proves discretionary cash AND values-driven check writing |
| FEC donations $25K+ | **Very strong** | Extremely strong accreditation signal |
| VP+ at tech companies (5+ years) | Strong | $300K-$1M+ total comp, significant equity wealth |
| Founder with any exit | Strong | Almost certainly accredited |
| Partner at consulting/law firm | Strong | High income, likely accredited |
| Finance/investment professionals | Strong | Understand the asset class |
| Real estate $1.5M+ (owner) | Moderate | Asset wealth but may be illiquid/mortgaged |
| Prior angel investments | **Strongest** | Proves both capacity and willingness |
| Nonprofit/gov/education careers | **Weak** | Salaried, no equity wealth — do not overweight titles |

**Data sources:** `enrich_employment` (career history), `fec_donations` (political giving), `real_estate_data` (property ownership + Zestimate), `enrich_current_title`, `enrich_total_experience_years`

### 2. Mission Alignment with Kindora

Investors must believe in the mission, not just financial return. PBC structure means the company will always prioritize nonprofit access over profit maximization.

**Strong alignment signals:**
- Philanthropic career or nonprofit board service
- Google.org / foundation alumni (understand the problem space)
- Nonprofit technology experience (Blackbaud, Salesforce.org, etc.)
- Social impact investing experience
- AI/ML enthusiasm + social impact interest
- Prior donations to education, equity, technology access causes
- LinkedIn content about equity, access, AI ethics, nonprofit innovation
- Foundation trustee or program officer experience

**Weak/negative alignment signals:**
- Pure financial return seekers (all about portfolio returns and alpha)
- No philanthropic touchpoints in career
- Competitors or people advising competitors
- People who demand governance control on small checks

**Data sources:** `enrich_employment`, `enrich_board_positions`, `enrich_volunteer_orgs`, `ai_tags`, `fec_donations` (cause alignment), `linkedin_reactions`, `headline`, `summary`

### 3. Relationship Warmth

Angel investing requires MORE trust than donations — capital at risk in an illiquid startup. Uses a 2x2 framework:

| Quadrant | Familiarity | Comms | Strategy |
|----------|------------|-------|----------|
| **Active Inner Circle** | 3-4 | active/regular | Direct conversation. Highest trust. Invest in Justin as much as the company. |
| **Dormant Strong Ties** | 3-4 | dormant/occasional | **Highest leverage.** Reactivate + share Kindora story. |
| **Active Weak Ties** | 0-2 | active/regular | Deepen first. Move from professional to personal before asking. |
| **Cold Contacts** | 0-2 | dormant/none | Only via warm intro, and only if very high capacity + mission alignment. |

**Momentum modifiers:**
- Dormant Strong Tie + growing momentum = perfect timing
- Active Inner Circle + fading momentum = check in before asking
- Growing momentum on any relationship = window of opportunity

**Data sources:** `familiarity_rating` (0-4), `comms_closeness`, `comms_momentum`, `comms_last_date`, `comms_thread_count`, `comms_meeting_count`, `linkedin_reactions`

### 4. Investment Sophistication

| Level | Signals | Framing |
|-------|---------|---------|
| **Experienced angel** | "Angel investor" in headline, listed portfolio companies, startup boards | Standard angel pitch: terms, traction, market, team |
| **Sophisticated, not angel** | Finance professionals, foundation grant deployers, corporate venture | Bridge from expertise: "like a grant with equity upside" |
| **First-time angel** | High-capacity + mission-aligned, no investment experience | Educate on SAFE mechanics, risk of total loss, illiquidity timeline |
| **Non-investor** | Never invested outside public markets, risk-averse | Score lower unless exceptional alignment + warmth |

**Data sources:** `headline`, `summary`, `enrich_titles_held`, `enrich_board_positions`, `enrich_employment`

### 5. Strategic Value Beyond Capital

A $25K check from someone who opens doors is worth more than $50K from a passive investor.

- **Customer introductions:** Foundation program officers, nonprofit network leaders
- **Fundraising credibility:** Recognized names compress future diligence
- **Domain expertise:** Philanthropy, SaaS, nonprofit tech, AI/ML
- **Amplification:** Large LinkedIn following, conference speaking, media presence
- **Operational experience:** Founders who've built startups, scaled teams

**Data sources:** `enrich_current_company`, `enrich_current_title`, `enrich_follower_count`, `enrich_board_positions`, `enrich_volunteer_orgs`

## Disqualifying Signals (not_a_fit)

- Pure financial return seekers who would push for mission-compromising exits
- Governance control demands (board seats, veto rights on small checks)
- Conflicts of interest (work at/advise Kindora competitors)
- Below accredited threshold, or $25K check would cause financial stress
- No relationship path (cold, no mutual connections, no intro route)
- Financial distress or career transition (shouldn't make illiquid investments)

## Tier Definitions

| Score | Tier | Meaning | Expected Action |
|-------|------|---------|-----------------|
| 80-100 | **ready_now** | Accredited + aligned + warm + sophisticated | Direct investment conversation. Check in 2-4 weeks. |
| 60-79 | **cultivate_first** | Good profile, needs 1-3 touchpoints | Warm relationship or explain opportunity. Ask in 1-3 months. |
| 40-59 | **long_term** | Has capacity or alignment, relationship too thin | 4-8 cultivation touchpoints over 3-6 months. |
| 20-39 | **long_term** | Distant connection or weak alignment | Only if very high capacity + warm intro path. |
| 0-19 | **not_a_fit** | No relationship, alignment, capacity, or disqualifying | Do not pursue. |

**Expected distribution** for a ~2,900-person network: 30-50 ready_now, 100-200 cultivate_first, majority not_a_fit or long_term.

## Interpreting Results

### What a "ready_now" angel prospect looks like
- VP+ at tech company or founder with exit (financial capacity confirmed)
- Philanthropy/nonprofit background or social impact involvement (mission alignment)
- Familiarity 3-4 with active/regular communication (trust established)
- Understands startup investing or at least mission-driven capital deployment
- Ideally brings strategic value (customer intros, credibility, expertise)

### What to look for in "cultivate_first"
- Check the `cultivation_needed` field for specific, time-bound steps
- First-time angels flagged here need education on SAFE mechanics before the ask
- Dormant strong ties need reactivation before investment conversation
- Look for contacts with growing communication momentum — window of opportunity

### Red flags in scoring
- High score but low familiarity = relationship risk (verify warm intro path exists)
- High capacity but nonprofit career = may have overweighted title vs actual wealth
- "Ready now" but no comms history = likely needs downgrade to cultivate_first

## Output Fields (from `ask_readiness` JSONB)

| Field | Angel Investment Meaning |
|-------|------------------------|
| `score` | 0-100 overall angel prospect score |
| `tier` | ready_now / cultivate_first / long_term / not_a_fit |
| `reasoning` | Decision-ready paragraph: relationship, capacity signals, alignment, risk |
| `recommended_approach` | Best outreach channel for this person |
| `ask_timing` | now / after_cultivation / after_reconnection / not_recommended |
| `suggested_ask_range` | Investment check size: "$25K-$50K", "$10K-$25K", "$10K", "Not recommended" |
| `personalization_angle` | Why Kindora's mission resonates for THIS person as an investor |
| `cultivation_needed` | Specific steps to get from current state to investment conversation |
| `receiver_frame` | What kind of investment conversation they'd welcome, from their perspective |
| `risk_factors` | Things that could backfire (governance demands, return expectations, relationship damage) |

## Technical Details

- **Script:** `scripts/intelligence/score_ask_readiness.py --goal kindora_angel_investment`
- **Model:** GPT-5 mini (150 concurrent workers)
- **Storage:** `contacts.ask_readiness` JSONB, keyed by `kindora_angel_investment`
- **UI:** `/tools/kindora-angel` page
- **API:** `/api/network-intel/kindora-angel` endpoint
- **Cost:** ~$3-4 per full run (~2,400 contacts)
