# Outdoorithm Collective — Donor Segmentation & Persona Framework

**Living document. Informs all campaign outreach and stewardship.**

Last updated: February 23, 2026

---

**Companion docs:**
- `OC_FUNDRAISING_PLAYBOOK.md` — Campaign methodology, psychology, measurement
- `COME_ALIVE_2026_Campaign.md` — 2026 campaign plan with outreach tiers
- `COME_ALIVE_Framing_Analysis.md` — Brand frame and stories
- `campaign_sizing_recommendation.md` — $100K goal analysis

---

## Why Segmentation Matters for OC

OC is raising money from Justin's personal network — not a mass donor file. Every person on the list has a real relationship, a real history, and a real reason they might give. The temptation is to treat that closeness as sufficient: "I know these people, I'll just write each one from scratch."

The problem: writing 200+ personalized messages from scratch is a 40-hour project that burns Justin out before Email 2. And without structure, the messages default to whatever feels right in the moment — which means the fundraising psychology that actually drives conversion gets applied inconsistently.

**Personas solve this.** They're not a replacement for personalization — they're the scaffold that makes personalization efficient. Each persona defines:
- The **lead message frame** (what story, what framing, what emotional circuit)
- The **channel and cadence** (text vs. email vs. conversation)
- The **ask strategy** (anchor amount, how to present the match, upgrade path)
- The **stewardship sequence** (what happens after the gift)

Then individual customization happens on top: the specific reference to their job, their kids, their last conversation with Justin, their `receiver_frame` from the ask readiness score. The persona gives you the skeleton in 30 seconds; the customization takes 2 minutes. That's 2.5 minutes per message instead of 15.

---

## List Taxonomy: Who Gets What

The campaign doc targets **200-250 contacts** for Email 1. The ask readiness data covers **~160 scored contacts** in addressable tiers. The gap (~40-90 contacts) is warm-ish contacts who weren't scored as ready_now or top cultivate_first, or who weren't in the scoring system at all but are warm enough to receive a personal email from Justin.

| List | Size | Who | Persona Coverage |
|:--|--:|:--|:--|
| **A: Personal Outreach** | ~20 | Tier 1 inner circle. Justin sends personal text/email before campaign launch. | Believers + select Impact Professionals |
| **B: Primary Campaign** | ~115 | Tier 2 remaining ready_now. Email 1 on launch day. | Impact Professionals + Network Peers |
| **C: Secondary Campaign** | ~25-30 | Tier 3 top cultivate_first, approach = personal_email. Email 1 same day or +1 day. | Network Peers + Impact Professionals |
| **D: Extended Campaign** | ~40-60 | Additional warm contacts not scored or lower-scored but warm enough for Email 1. | Network Peers (default scaffold) |
| **E: Cultivation Pipeline** | ~30 | High-capacity, approach = linkedin/intro. Not this campaign. | See "Major Gift Pipeline" section |
| **Beyond** | ~2,300 | long_term or not_a_fit. | See "Beyond This Campaign" section |

**Total campaign emails (A+B+C+D): ~200-250.** This reconciles the campaign doc's audience with the scored data.

**Which personas apply to which lists:**
- Lists A-D all use the three campaign personas (Believer, Impact Professional, Network Peer)
- List D contacts without ask readiness data get the **Network Peer scaffold by default** — it's the most broadly applicable
- List E uses the Major Gift Pipeline guidance (cultivation, not solicitation)

---

## The Segmentation Layers

Five layers combine into a primary persona assignment plus individual customization signals.

### Layer 1: Relationship Warmth

How close is this person to Justin and Sally? This is the single most predictive variable for whether someone gives and how much.

| Level | Signal | Implication |
|:--|:--|:--|
| **Inner circle** | Justin's judgment. Often: frequent comms, OC engaged, approach = in_person or text | Personal text/email. High ask. Relationship carries the ask. |
| **Warm professional** | Comms history, approach = personal_email, score 85+ | Personal email. Mid-high ask. Story + math carry the ask. |
| **Known but distant** | Comms history exists but sparse, approach = personal_email, score 76-84 | Campaign email. Story + social proof carry the ask. |
| **Connected by network** | Approach = linkedin or intro_via_mutual, no comms history | Not this campaign. Cultivate first. |

**Data fields:** `recommended_approach`, `communication_history`, `oc_engagement`, `ask_readiness score`

### Layer 2: Giving Capacity

What can this person realistically give? Capacity is necessary but not sufficient — high-capacity donors who aren't personally engaged don't convert.

**Standardized capacity tiers** (for campaign execution — use these for ask anchors and post-campaign analysis):

| Tier | Ask Range | Campaign Anchor | Campaign Role |
|:--|:--|--:|:--|
| **Leadership** | $25,000+ | $10,000 | Pre-campaign personal outreach. Anchor gift or match candidate. |
| **Major** | $5,000-$25,000 | $5,000 | Pre-campaign personal outreach or Email 1 priority. |
| **Mid** | $1,000-$5,000 | $2,500 | Email campaign with specific anchor amounts. |
| **Base** | $250-$1,000 | $1,000 | Email campaign. Employer matching emphasis. |
| **Community** | Under $250 | $250 | Email campaign. Volume and community participation. |

**Mapping from `suggested_ask_range` to tier:** The raw field contains ~2,250 unique free-text GPT values (e.g., "$2,000-$5,000," "$5K-$10K," "$2,500-$7,500"). For manual persona assignment, read these as rough ranges and bin into the tiers above. For any future automation, a cleanup script will normalize them into consistent tiers and populate a `capacity_tier` field.

**Data fields:** `suggested_ask_range`, `current_title`, `current_company`, real estate data, FEC donation history

### Layer 3: Motivation Flags

Why would this person give? Rather than defining separate personas for each motivation — which creates false segments in a network where 1,300+ contacts show parent/family language and 880+ show justice/equity language — we use **motivation flags** as a customization layer on top of the primary persona.

Research supports this approach: Jen Shang's work on moral identity shows that individual-level identity matching outperforms segment-level approaches, producing a 27% increase in giving from identity-matching language. The right question isn't "which motivation bucket does this person fall into?" but "what combination of motivations does this specific person carry?"

| Flag | What Drives Them | Brain Circuit | OC Framing | How to Detect |
|:--|:--|:--|:--|:--|
| **Relationship** | Loyalty to Justin/Sally personally | Identity + Reward | "I'm building something. Want you in." | Frequent comms, shared history, OC engaged |
| **Mission alignment** | OC's work matches their professional values | Empathy + Identity | "Here's what's happening — and why it matters." | Social impact title, `receiver_frame` mentions effectiveness |
| **Peer identity** | Being part of what their cohort supports | Identity + Reward | "[X] friends have backed the season." | Google/HBS/HKS cohort, `receiver_frame` mentions leadership |
| **Parental empathy** | They see their own family in OC's stories | Empathy | "Her daughter runs barefoot through camp. No fear. Just joy." | `personalization_angle` or `receiver_frame` mentions family/kids/parenting |
| **Justice/equity** | They care about who gets access to nature | Identity + Empathy | "Being able to feel safe camping changes the narrative." | `receiver_frame` mentions equity/justice/access/representation |
| **Community/belonging** | They value connection and shared experience | Empathy + Reward | "A community that will never fail me." | `receiver_frame` mentions community/connection/belonging |

Most contacts carry 2-3 flags. The primary flag determines the **lead frame**; secondary flags add reinforcement lines. A Network Peer with strong parental empathy gets the standard campaign email but with Valencia's daughter story emphasized. An Impact Professional with a justice/equity flag gets Carl's "changes the narrative" quote alongside the model-effectiveness framing.

**Data fields:** `personalization_angle`, `receiver_frame`, `ai_tags`, LinkedIn profile data

### Layer 4: Engagement Stage (Lifecycle)

Where is this person in the donor lifecycle? This determines **both** the stewardship action **and** the solicitation message. Different lifecycle stages need different opener lines, ask frames, and follow-up cadences — not just different thank-yous.

| Stage | Definition | Solicitation Insert | Stewardship Action |
|:--|:--|:--|:--|
| **New prospect** | Never given to OC | Lead with story + invitation. "If you want in." | Acquisition: identity-affirming thank-you within 24 hours |
| **Prior donor** | Gave in 2025 or before this campaign | Reference past gift + impact. "Your support last year helped fund [trip]. Here's what's next." | Retention: second gift opportunity within 90 days, upgrade ask |
| **Lapsed** | Gave previously but not in 12+ months | Personal re-engagement. "You backed OC before. We're doing something bigger this year." | Reactivation: personal outreach, match or exceed original gift |
| **Repeat donor** | Gave 2+ times | Monthly giving conversion opportunity. "You keep showing up. Want to make it official?" | Upgrade: recurring giving program, increased ask |
| **Major donor** | $5K+ cumulative or single gift | Peer-to-peer, strategic conversation. No mass email. | Stewardship: quarterly personal updates, trip invitations |

**Why lifecycle changes the ask, not just stewardship:** A lapsed donor and a never-donor may share a persona (both Network Peers), but the most effective sentence for a lapsed donor is "Thank you for your last gift — here's what it made possible." That single line leverages their existing identity as a giver. Treating both as blank-slate prospects wastes the most potent tool in renewal copy. (Blackbaud's annual giving guidance explicitly frames journey stage as a key driver of messaging strategy alongside persona.)

**Note on OC engagement data:** The `oc_engagement` field covers 133 contacts, but only ~49 (37%) are actual donors. The rest are participants, prospective participants, influencers, or vendors. Having `oc_engagement` indicates a relationship with OC, not a giving history. For lifecycle assignment, use Stripe records or direct knowledge — not `oc_engagement` alone. In future campaigns, add an `oc_engagement_type` field (donor / participant / prospect / vendor / influencer) for cleaner segmentation.

**Data fields:** Stripe giving history (when integrated), `oc_engagement`, campaign tracking

### Layer 5: Channel Preference

How does this person prefer to be reached? Multi-channel donors give 3x more than single-channel (Virtuous/NextAfter), but the *lead* channel matters.

| Channel | Best For | OC Data Signal |
|:--|:--|:--|
| **Text/SMS** | Inner circle, follow-ups, urgency | approach = text_message, phone number on file |
| **Personal email** | Primary channel for both personal outreach and campaign | approach = personal_email or in_person |
| **Campaign email** | Broader network, social proof emphasis | All ready_now and top cultivate_first |
| **Phone/video** | Thank-yous, donor-initiated conversations only | After donor replies to email/text |
| **LinkedIn** | Cultivation touchpoints, not fundraising asks | approach = linkedin (not for this campaign) |

**Data fields:** `recommended_approach`, `communication_history` (shows which channels have actual history)

---

## The Three Campaign Personas

Each persona represents a distinct combination of the segmentation layers. A contact is assigned one primary persona for campaign execution. Motivation flags and lifecycle stage then customize the message within the persona scaffold.

**These three personas cover Lists A through D — every contact who receives a campaign touchpoint.** The Major Gift Pipeline (List E) is covered separately below.

### Persona 1: The Believer

> *"I'm in because Justin asked."*

**Who they are:** Close friends, family, co-founders, people who've been on OC trips or deeply involved with the organization. Their giving is relationship-first. They'd support almost anything Justin and Sally build because they trust them, have seen the work firsthand, and feel personally invested in the mission.

**How they're identified:** Justin decides. This is not a data-derived segment — it's a judgment call about who's truly inner circle. The data can *suggest* candidates: contacts with OC donor engagement, frequent comms, in_person/text approach, and high scores tend to be Believers. But the final list is Justin's because he knows which relationships carry this level of trust.

**Motivation:** Relationship loyalty + personal identity ("I'm the kind of person who backs my people")

**Brain circuits:** Identity (this is who I am) + Reward (feels good to support something real)

**Size of segment:** ~15-20 contacts (List A)

**Example contacts:** Roxana Shirkhoda, Hector Mujica, Adrian Schurr, Marcus Steele, Karibu Nyaggah, Sally Steele — plus whoever else Justin adds

**Outreach scaffold:**
- **Channel:** Personal text or casual email
- **Tone:** Warm, brief, insider language. No selling needed.
- **Lead frame:** "Quick thing. Here's what's happening. Would love to count you in."
- **Story emphasis:** Whichever story they've personally witnessed or heard Justin talk about. Or skip the story entirely — the relationship is the story.
- **Ask strategy:** Anchor to capacity tier, not past giving. They'll stretch for Justin. Don't underask.
- **Match framing:** Light touch — "A friend is matching the first $20K" is sufficient.
- **What NOT to do:** Don't over-explain OC's mission to people who already know it. Don't send them the campaign email — they should hear from Justin directly first.

**Lifecycle-aware inserts:**
- **New to OC giving:** "Quick thing. [story/context]. Would love to count you in this season."
- **Prior donor:** "Your support last year went straight to [trip]. Meant the world. Here's what's next — [this season's plan]."
- **Lapsed:** "Haven't caught up in a while. OC is doing something bigger this year — [context]. Would love to have you in it."

**Stewardship:**
- Thank-you text within hours, not days. "Means the world. Thank you."
- Post-trip photos and personal updates
- Trip invitations — they may want to attend, volunteer, or bring friends
- Ask for social proof permission: "Can I mention you've backed the season?"

---

### Persona 2: The Impact Professional

> *"This model works. I want to support it."*

**Who they are:** Senior social impact executives, foundation leaders, CSR directors, philanthropy professionals, nonprofit CEOs, community development leaders. People who evaluate nonprofits for a living or as a core part of their identity. They see OC through a professional lens — the model, the outcomes, the scalability, the community infrastructure angle.

**Motivation:** Mission alignment + professional identity ("I back effective organizations doing important work")

**Brain circuits:** Identity (I'm someone who spots and supports impact) + Empathy (the stories move me, but I need the model to be sound too)

**Size of segment:** ~35-50 contacts (across Lists A, B, C)

**Data signals:**
- Title includes "Impact," "Foundation," "Philanthropy," "Social," "CSR," "Community," or they run a nonprofit/social enterprise
- `receiver_frame` mentions effectiveness, community development, social infrastructure
- Companies: Google.org, foundations, social enterprises, impact investors, nonprofits
- Score 80+

**Example contacts:** Brigitte Hoyer Gosselink, Jose Gordon, Carrie Varoquiers, Megan Wheeler, Bryan Breckenridge, Amy Dominguez-Arms, Meg Garlinghouse, Rosita Najmi, Bob Friedman, Jon Huggett, Susan Colby, James Weinberg, Darren Isom, Stacey Harris, Sam Cobbs, Tynesia Boyea-Robinson

**Outreach scaffold:**
- **Channel:** Personal email (List A contacts) or campaign email (Lists B-C)
- **Tone:** Warm but substantive. Show you respect their expertise.
- **Lead frame:** Story first (they're human, not robots), then the model. "10 trips. $10K each. Families coming alive." The math resonates with this group because they evaluate math professionally.
- **Story emphasis:** Stories that show systemic change. Carl's "changes the narrative," Michelle Latting's "core aspects of who we are as a family are *made* on these trips," Joy's "community that will never fail me."
- **Ask strategy:** Mid-to-high based on capacity tier. Frame as investment: "Your $5K funds half a trip — rest, community, grit for 10 families."
- **Match framing:** Lead with it. This group understands leverage. "$2,500 becomes $5,000 — half a trip funded" is a complete sentence for them.
- **Motivation flag application:**
  - **+ Justice/equity:** Lead with Carl's story and the structural access angle.
  - **+ Parental empathy:** Add Michelle Latting's family transformation quote.
  - **+ Community/belonging:** Emphasize Joy's "community that will never fail me."
- **What NOT to do:** Don't be vague. "Helping families" without specifics loses them. Don't use jargon they'd see through — "outdoor equity" is fine for a grant, not for a personal email to Brigitte.

**Lifecycle-aware inserts:**
- **New to OC giving:** Standard scaffold above. "I don't think you've backed OC yet — if you want in this season, here's what's happening."
- **Prior donor:** "Your gift last year went toward [trip] — [X] families, [X] days. We're building on that with 10 trips this season."
- **Lapsed:** "You supported OC before, and I'm reaching out personally because we're doing something bigger this year. [Current season context.]"

**Stewardship:**
- Thank-you email within 24 hours with specific impact allocation
- Invite to see a trip in action — offer to bring them along
- Quarterly impact update: families served, trips completed, stories collected
- Ask their advice — "What would you do differently?" creates reciprocity
- Employer matching reminder if at a matching company

---

### Persona 3: The Network Peer

> *"My people support this. I should too."*

**Who they are:** Google colleagues, HBS/HKS classmates, Bain/Bridgespan alumni, professional network contacts. They know Justin, respect him, but aren't in the inner circle. Their relationship is primarily professional or alumni-based. They're successful, busy, and get a lot of asks.

This is the **largest segment** and the primary audience for the 3-email campaign sequence. The campaign emails are written for this group. **This is also the default persona for List D contacts** (warm contacts without ask readiness data).

**Motivation:** Peer identity + social proof ("People like me support things like this")

**Brain circuits:** Identity (I'm a successful professional who gives back) + Reward (it feels good to back a friend's meaningful venture)

**Size of segment:** ~80-120 contacts (across Lists B, C, D)

**Data signals:**
- Company = Google, former Google, or major tech/consulting/finance
- Education signals: HBS, HKS, UVA, or similar
- `recommended_approach` = personal_email
- Score 76-88
- No social impact title (those go to Impact Professional)

**Example contacts:** Richard Baltimore, Micah Berman, Sebastien Floodpage, Michael Munoz, Bradlaugh Robinson, David Winder, Christina Kelleher Knoll, Amanda Irizarry, Patrick Dickinson, Tyler Scriven

**Outreach scaffold:**
- **Channel:** Campaign email (Email 1, 2, 3 sequence)
- **Tone:** Justin's natural voice — personal, specific, warm but not needy
- **Lead frame:** Valencia's story + social proof. The "[X] friends have stepped up" line in Email 2 is written for this group. When they see 30 people from their network have given, the question shifts from "should I?" to "why haven't I?"
- **Story emphasis:** Stories anyone can connect to. Valencia (fear → freedom). The 8-year-old wanting to "go home to the campfire." Human stories, not cause-specific ones.
- **Ask strategy:** $1,000 / $2,500 / $5,000 ascending anchors (the email defaults). Many in this segment will give $1,000-$2,500.
- **Match framing:** Standard: "A friend is matching the first $20K dollar-for-dollar."
- **Employer matching:** Critical. Many work at Google, Meta, Salesforce with 1:1 matching.
- **Motivation flag application:**
  - **+ Parental empathy:** Valencia's daughter in Email 1 already hits this. No change needed.
  - **+ Justice/equity:** In personal follow-up, swap to Carl's story.
  - **+ Achievement/leadership:** "Given what you've built at [Company], I think you'd appreciate what 48 hours in nature does for a family."
- **What NOT to do:** Don't make the email feel like a mass blast. The plain-text, from-Justin's-personal-email format is essential. Don't over-explain. Don't manufacture social proof — "several friends" beats a specific number if it's low.

**Lifecycle-aware inserts:**
- **New to OC giving:** Campaign emails as-is — they're written for first-time prospects.
- **Prior donor:** Add to the personal follow-up text: "Thank you for backing us last year — here's what your gift made possible: [specific trip/families]. We're doing 10 trips this season."
- **Lapsed:** Send a personal email instead of (or before) the campaign email: "You supported OC before, and I wanted to reach out personally. We're doing something bigger this year." Then the campaign emails follow.

**Stewardship:**
- Automated Stripe receipt (already in place)
- Personal thank-you email within 24 hours — identity-affirming: "You're the kind of person who shows up"
- Post-trip photo update — brief, visual, no additional ask
- Employer matching reminder 30 days post-gift if they didn't submit
- Second gift opportunity within 90 days (year-end campaign, specific trip need)

---

## Execution Matrix: Persona × Lifecycle → What You Actually Write

This is the bridge between strategy and execution. For each combination, here's the concrete copy element.

### Opener Inserts by Persona × Lifecycle

| | New to OC | Prior Donor | Lapsed |
|:--|:--|:--|:--|
| **Believer** | "Quick thing. [Context]. Would love to count you in." | "Your support last year went to [trip]. Meant the world. Here's what's next." | "Haven't caught up in a while. OC is bigger this year. Would love to have you in it." |
| **Impact Pro** | "I don't think you've backed OC yet — if you want in this season, here's what's happening." | "Your gift last year went toward [trip] — [X] families. Building on that with 10 trips." | "You supported OC before. Reaching out personally because we're doing something bigger." |
| **Network Peer** | Campaign emails as-written (designed for new prospects). | Text follow-up: "Thanks for backing us last year. [Impact]. 10 trips this season." | Personal email before campaign: "You supported OC before. Wanted to reach out personally." |

### Ask Anchors by Persona × Capacity Tier

| | Community | Base | Mid | Major | Leadership |
|:--|--:|--:|--:|--:|--:|
| **Believer** | $250 | $1,000 | $2,500 | $5,000 | $10,000 |
| **Impact Pro** | $500 | $1,000 | $2,500 | $5,000 | $10,000 |
| **Network Peer** | $250 | $1,000 | $2,500 | $5,000 | $5,000 |

*Prior donors:* anchor 25-50% above their last gift. *Lapsed donors:* match or slightly exceed their original gift.

### Follow-up Channel × Timing

| | First Follow-up | Second Follow-up | Thank-you |
|:--|:--|:--|:--|
| **Believer** | Text, 3 days | Text, 7 days (if no response) | Text within hours |
| **Impact Pro** | Email, 5-7 days | Text, 10-12 days | Email within 24 hours |
| **Network Peer** | Text to openers, 3-5 days | Email 2 (automatic, non-donors) | Email within 24 hours |

### Thank-you Frame by Persona + Motivation Flag

| Persona | Base Thank-you | + Parental Empathy | + Justice/Equity | + Community |
|:--|:--|:--|:--|:--|
| **Believer** | "Means the world. Thank you." | Same — relationship is the frame | Same | Same |
| **Impact Pro** | "Your $X is going toward [trip]. [X] families." | "…families like yours." | "You're helping build what public lands should have been." | "You're funding a community that will outlast any program." |
| **Network Peer** | "You're the kind of person who shows up." | "Your gift sends [X] families to the campfire." | "You're funding spaces where every family belongs." | "You just joined something real." |

---

## Stewardship Sequences

### The Critical Window: First 24 Hours

Cherian Koshy's research shows the brain's three giving circuits (reward, empathy, identity) cool within hours, not days. The first touchpoint after a gift is the most important moment in the donor relationship.

**Thank-you speed targets:**
- Believers: within hours (text)
- Impact Professionals: within 24 hours (email with impact specifics)
- Network Peers: within 24 hours (email with identity-affirming language)

### The Second Gift Window: 90 Days

Only 18-19% of first-time donors give again (FEP Q3 2024: 18.6% YTD for single-gift donors). But those who give a second time retain at 38%+, and three-gift donors at 61%+. The 90-day window is the most important retention period. OC should compute its own retention rates from Stripe once campaign data is in.

| Persona | Second Gift Opportunity | Frame |
|:--|:--|:--|
| The Believer | Monthly giving conversion | "Want to make it recurring? Even $100/month keeps families coming alive year-round." |
| Impact Professional | Specific project need | "We have an opportunity to add an 11th trip. Your investment would fund it." |
| Network Peer | Year-end campaign | "Remember Valencia's story? Here's what happened after your gift." |

### Post-Campaign: Ongoing Cultivation

| Touchpoint | Frequency | All Personas |
|:--|:--|:--|
| Post-trip photo update | After each trip (~monthly in season) | One photo, one line. No ask. |
| Personal update from Justin | Quarterly | OC growth, new trips, community stories |
| Trip invitation | 1-2x per year | Invite to observe, participate, or volunteer |
| Year-end impact summary | Annual (November) | Families served, trips completed, stories collected |
| Campaign ask | 1-2x per year | Spring campaign + possible year-end campaign |

**The 7-touch rule:** Each donor should receive ~7 touchpoints between asks. For OC with one major campaign per year: post-trip updates, personal notes, media shares, trip invitations, and the year-end summary.

---

## The Customization Layer: What Makes Each Message Unique

The persona gives you the scaffold in 30 seconds. These individual data points take another 2 minutes.

### Always Use (Every Message)

1. **Their name** — First name only for Believers and close peers.

2. **The `personalization_angle`** — Free-text suggestion for connecting OC to their values. Use as a seed for one sentence of genuine connection.

3. **The ask amount** — From the capacity tier table, not a one-size-fits-all anchor.

4. **The motivation flag** — Which story to lead with, which reinforcement line to add.

5. **The lifecycle insert** — New, prior, or lapsed opener line from the execution matrix.

### Use When Available

6. **Reference to their work or company** — One sentence, authentic, not forced.

7. **Shared history with Justin** — If comms history shows a recent exchange, reference it.

8. **Past giving** — If they gave in 2025, reference it with impact. This is the single most effective retention driver (Burk, 2003).

9. **Their `receiver_frame`** — Maps to identity-affirming thank-you language.

### Never Do

- Don't reference data you shouldn't have. No "I saw your home is worth $2M" or "Your FEC records show you gave $5K to [candidate]."
- Don't force a personalization. If you can't find a natural connection in 30 seconds, the persona scaffold is enough.
- Don't mix personas in one message. Motivation flags add a reinforcement *line*, not a second frame.

---

## Major Gift Pipeline: 2027 Prospects

This section covers **List E** — ~30 high-capacity contacts where the relationship exists but the OC connection doesn't yet. These are not campaign personas; they're a moves management pipeline. The campaign plan already treats them as "Not This Campaign."

### Who They Are

Ultra-high net worth contacts — VCs, family office managers, major philanthropists, senior executives — who could give $25K-$250K+ but need to understand and believe in OC first. These are 2027's major donors.

### Data Signals

- `suggested_ask` >= $25,000
- `recommended_approach` = linkedin or intro_via_mutual
- Often: sparse or no `communication_history`
- May or may not have `oc_engagement`

### Example Contacts

Laura Arrillaga-Andreessen, Caitlin Heising, Regan Pritzker, Gerald Chertavian, Luis Miranda, John Rice, Christian Sutherland-Wong, Ebony Beckwith, Melonie Parker

### 2026 Cultivation Actions (No Ask)

| Action | Timing | Purpose |
|:--|:--|:--|
| **LinkedIn engagement** | Ongoing | Like/comment on their content. Build visibility. |
| **Content sharing** | Monthly | Share OC trip stories, Sally's writing, media coverage. |
| **Mutual introduction** | When organic | Ask Believers who know them for a warm intro. |
| **Trip invitation** | 1-2x | Invite to observe a trip as a guest. Experience converts. |
| **Personal update** | Quarterly | Brief note from Justin about OC's growth. |

### Moves Management Timeline

1. **Identification** — Done (scored in ask readiness).
2. **Qualification** — 2026 campaign period. Who responds to cultivation touches?
3. **Cultivation** — 2026 trips, updates, relationship-building. 6-18 months.
4. **Solicitation** — 2027 campaign or earlier if organic.
5. **Stewardship** — When they give, treat as Believers from day one.

### What NOT to Do

Don't send the campaign email to people who aren't warm enough. A cold $100K-prospect getting an unsolicited fundraising email is a wasted touch — or worse, it makes OC look small. Don't conflate capacity with readiness.

---

## Beyond This Campaign: The Other 2,300 Contacts

The ~2,300 contacts scored `long_term` or `not_a_fit` aren't targets for Come Alive 2026. They represent Year 2+ potential.

**What to do in 2026 (no fundraising):**
1. **LinkedIn engagement** — Like, comment on, and share content from the top 50-100 long_term contacts with highest scores.
2. **Content sharing** — Post OC trip stories and impact updates. Let the work speak.
3. **Mutual introductions** — When a donor knows a long_term contact, ask for an intro.
4. **Event invitations** — Invite selectively to OC events or trip observations.
5. **Re-score annually** — Re-run ask readiness scoring after a year of cultivation. Many will move to cultivate_first.

**What NOT to do:** Don't add these contacts to the campaign email list. A fundraising ask from someone they barely know is worse than no touch at all.

---

## Measuring Segmentation Effectiveness

After the 2026 campaign, analyze by persona:

| Metric | What It Tells You |
|:--|:--|
| **Conversion rate by persona** | Which personas respond to the current approach? |
| **Average gift by persona** | Are ask anchors calibrated correctly? |
| **Gift range chart accuracy by persona** | Did the pyramid hold within each segment? |
| **Lifecycle conversion** | Did prior donors upgrade? Did lapsed donors reactivate? |
| **Motivation flag effectiveness** | Which stories/frames drove which gifts? |
| **Channel response rate** | Is email/text/personal outreach working for each persona? |
| **Thank-you speed** | Did we hit the 24-hour window? |

**Post-campaign re-segmentation:** Personas are not permanent. A Network Peer who gives $5K may become an Impact Professional or Believer for the next campaign. A Prospect who responds to a cultivation touch enters the campaign universe. Update persona assignments after each campaign based on actual behavior.

---

## Implementation Checklist: Come Alive 2026

1. **Assign primary personas** to List A (~20) and top List B-C contacts (~40-50). Believers first (Justin's judgment), then Impact Professionals (title/company), then Network Peers (default).
2. **Apply motivation flags** — read `personalization_angle` and `receiver_frame`. Note 1-2 flags per contact.
3. **Identify lifecycle stage** — check 2025 Stripe records and direct knowledge. Mark each as new, prior, or lapsed.
4. **Draft personal outreach** (List A) using persona scaffold + lifecycle insert + motivation flag + individual customization. Target: 2-3 minutes per message.
5. **Prepare thank-you templates** — one per persona × motivation flag combination, pre-drafted with blanks. Ready before launch.
6. **Tag each gift** with persona, lifecycle stage, and motivation flags for post-campaign analysis.
7. **List D contacts** without scoring data: default to Network Peer scaffold, campaign email channel, $1,000 base anchor.

---

## Appendix A: Evidence Base

| Source | Key Finding | Where Applied |
|:--|:--|:--|
| Koshy, *Neurogiving* (2025) | Three brain circuits; generosity decay; 24-hour memory window | Thank-you timing, identity-affirming language |
| Burk, *Donor-Centered Fundraising* (2003) | 93% would give again with better communication; thank-you letter most critical | Stewardship sequences |
| Shang, moral identity research | 27% increase from identity-matching language; individual-level matching > segment-level | Motivation flags design (not fixed persona segments) |
| Sargeant, retention research | "Very satisfied" donors 2x more likely to give again; 7 drivers of commitment | Stewardship touchpoints |
| Prince & File, *Seven Faces of Philanthropy* (1994) | 7 donor identity types with specific engagement strategies | Persona motivation mapping |
| Konrath & Handy (2018) | 6 primary donor motivations; 75% need to be passionate about cause | Motivation flag design |
| Karlan & List, matching gifts field experiment | ~22% higher probability of giving; ~19% higher revenue per solicitation; match ratio (1:1 vs 2:1 vs 3:1) doesn't significantly affect outcomes | Match framing; don't over-invest in ratio negotiation |
| Kahneman, anchoring research | First number primes expectations; ascending order essential | Ask amount strategies |
| Saeri et al. (2022), *Voluntas* meta-review | Individual beneficiary emphasis, visibility/social proof, impact clarity, and tax info have most robust evidence for donation lift; effect sizes typically small and context-dependent | Story selection, social proof; treat any single "psychology hack" as incremental |
| DonorVoice, 7 Drivers of Commitment | Effectiveness, consistency, timely thanks, voice, important cause, appreciation, who is helped | Stewardship matrix |
| Virtuous/NextAfter multi-channel study | Multi-channel donors give 3x more in lifetime value | Channel strategy |
| FEP Q3 2024 benchmark (AFP) | 18.6% YTD retention for single-gift donors; 38.1% for two-gift; 61.2% for three-to-six-gift | 90-day second gift window; OC should compute own rates from Stripe |
| Blackbaud annual giving guidance | Journey stage (acquisition/renewal/reactivation) is a key driver of messaging alongside persona | Lifecycle-aware inserts in persona scaffolds |

---

## Appendix B: Data Governance

OC has access to sensitive enrichment data (real estate values, FEC donation records, LinkedIn profiles, communication history). Brief guidelines for responsible use:

1. **Internal use only.** Wealth indicators, FEC records, and real estate data inform capacity tier assignment and internal prioritization. They never appear in donor-facing messages.
2. **No sensitive inferences in copy.** Don't write anything that makes a donor feel surveilled. "Given what you're building at [Company]" is fine. "Based on your home value and political giving" is not.
3. **Access restricted.** Campaign execution data (persona assignments, capacity tiers, ask amounts) is accessible to Justin and Sally only. Raw enrichment data stays in the database, not in shared documents or email drafts.
4. **AI-generated fields are prompts, not truth.** `receiver_frame`, `personalization_angle`, and `suggested_ask_range` are GPT-generated suggestions. Treat them as starting points — verify against your own knowledge of the relationship before using in outreach.
5. **Prefer volunteered signals.** Past giving, event attendance, stated interests, and direct conversations are stronger and safer signals than inferred capacity.
