# SFEF Sprint Work Plan

**Client:** San Francisco Education Fund
**Engagement:** Fundraising Intelligence Sprint + Strategic Advisory ($32K)
**Contract signed:** March 10, 2026
**Sprint Phase:** March 10–28, 2026
**Advisory Phase:** April 1 – May 31, 2026

---

## Availability Constraints

| Period | Status | Notes |
|--------|--------|-------|
| March 10 (Tue) | **Available** | Sprint Day 1. Josh Pollack (Kindora, 10:30am). |
| March 11 (Wed) | **AM only** | Hector Salazar (Kindora, 10am). Travel to Austin PM. |
| March 12–15 (Thu–Sun) | **SXSW Austin** | TC Founder House (Thu), THE LIGHT HOUSE Day 1 (Fri), Day 2 + Closing (Sat). Miss SFEF March 12 event (Laura OK'd). |
| March 16 (Sun) | **Return day** | FF Senior Leadership (9am), Justin & Scott (Kindora, 1pm). |
| March 17–21 | **Partial** | Camelback sessions (Mon 11am, Thu 10am–1pm). SFEF event March 18. Back-to-back TrueSteele meetings Fri. |
| March 22–23 | **Weekend + Mon** | SFEF funder convening March 23 (Zoom). FF meeting + Kindora meetings Mon. |
| March 24–28 | **Partial** | Heavy meeting load across Kindora + TrueSteele. Equitable AI full day Wed. Oakland Tech Week Thu evening. |
| March 30 – April 3 | **UNAVAILABLE** | OC Spring Break trip — Joshua Tree National Park. |

---

## Sprint Deliverables (due March 28)

1. **SFLC Institutional Funder Prospect List and Approach Strategy** — 25–40 funders scored, top 10 approach memos, draft LOIs, draft outreach
2. **Individual Donor Heat Map and Intelligence Report** — enrichment, scoring (capacity/propensity/affinity/warmth), tiered segmentation, top 20 profiles with cultivation recs, draft outreach
3. **Interactive Donor Intelligence Dashboard** — web-based, queryable, filterable

---

## Day-by-Day Work Plan

### WEEK 1: Data Intake & Enrichment (March 10–14)

#### Tuesday March 10 — SPRINT DAY 1
- [ ] **Sign DocuSign** — Laura has signed, countersign and return
- [ ] **Send $16K invoice** — first payment due at execution
- [ ] **Kickoff call** — 60 min with Laura King, Ann Levy Walden, Terrence Riley. Align on goals, data access, SFLC priorities. Schedule for today.
- [ ] **Request CRM donor data export** — ask Laura to send during/after kickoff
- [ ] **Begin SFLC research** — initial landscape scan using Kindora platform (foundations funding literacy, education equity, Bay Area youth)
- [ ] **Set up SFEF data workspace** — Supabase table/schema for SFEF donor data (separate from personal contacts)

#### Wednesday March 11 — LAST DAY BEFORE SXSW
- [ ] **Ingest CRM data** — clean, normalize, import SFEF donor records
- [ ] **Launch enrichment pipeline** — LinkedIn enrichment (Apify), begin email discovery
- [ ] **Queue overnight enrichment** — set up batch runs to process while at SXSW: FEC donations, real estate, web research
- Hector Salazar (Kindora, 10–11am)
- PM: Fly to Austin

#### Thursday March 12 — SXSW Day 1
- SXSW: TC Founder House + workshops (all day)
- **SFEF community event** — will miss (Laura approved)
- [ ] **Evening check:** Review enrichment pipeline progress, fix any failures

#### Friday March 13 — SXSW Day 2
- SXSW: THE LIGHT HOUSE Day 1 (all day)
- [ ] **Morning (before events):** Check enrichment results, queue additional batches

#### Saturday March 14 — SXSW Day 3
- SXSW: THE LIGHT HOUSE Day 2 + Closing Party
- Enrichment pipelines running autonomously

#### Sunday March 15 — Travel Home
- [ ] Return from Austin
- [ ] **Review all enrichment results** — quality check, identify gaps
- [ ] **Begin donor scoring model design** — define SFEF-specific scoring dimensions

---

### WEEK 2: Analysis & Scoring (March 17–21)

#### Monday March 16
- FF Senior Leadership Meeting (9am)
- Justin & Scott (Kindora, 1pm)
- [ ] **Run donor scoring pipeline** — adapt existing GPT-5 mini scoring for SFEF context (capacity, propensity, affinity to education/literacy, relationship warmth)
- [ ] **Begin institutional funder scan** — Kindora platform search for SFLC-aligned funders, cross-reference 990 filings

#### Tuesday March 17
- Camelback wellness session (11am)
- [ ] **Complete donor scoring** — review results, validate tiers, identify outliers
- [ ] **Tier segmentation** — Ready to Ask, Cultivate First, Long Term, Steward
- [ ] **Continue institutional funder research** — build initial list of 30–50 candidates

#### Wednesday March 18 — SFEF EVENT DAY
- [ ] **SFEF community event** — attend in person. Observe, meet stakeholders, gather context.
- [ ] **30-min call with Terrence Riley** — SFLC funding priorities, coalition structure, key relationships. Schedule around event.
- Gabe Hanzel-Sello (Kindora, 2pm)
- [ ] **PM:** Qualify and score institutional funders — giving history, focus area match, grant size fit, geographic alignment

#### Thursday March 19
- Camelback "How to Price and Sell" (10am–1pm)
- [ ] **PM:** Finalize institutional prospect list (25–40 funders)
- [ ] **Begin top 20 individual donor profiles** — pull enrichment data, draft cultivation recommendations
- [ ] **Generate heat map** — visualization of highest-potential donor clusters

#### Friday March 20
- TrueSteele meetings: Nikole Collins-Puri (10), Nicole Kelm (10:30), Stephanie Lo (11), Hillary Blout (12:30)
- [ ] **AM (before meetings):** Continue donor profiles
- [ ] **PM (after meetings):** Send Week 2 draft to Laura for feedback (scoring results, preliminary funder list, initial donor profiles)
- **FEEDBACK DUE from Laura by end of day Monday March 23** (per contract: 48 hours)

---

### WEEK 3: Refinement & Presentation (March 24–28)

#### Monday March 23
- FF Senior Leadership Meeting (9am)
- Naomi Morenzoni (Kindora, 10:30)
- Justin & Scott (Kindora, 1pm)
- [ ] **SFEF funder convening** — Zoom in. Take notes on funder landscape, identify warm connections.
- [ ] **Incorporate Laura's feedback** on Week 2 drafts
- [ ] **Begin approach strategy memos** for top 10 institutional funders

#### Tuesday March 24
- Felipe Ventura (TrueSteele, 10:30)
- Nicole Serena Silver (Kindora, 2pm), Sam Cobbs (Kindora, 2:30)
- [ ] **Draft LOIs** for top-ranked institutional funders
- [ ] **Draft outreach messages** — institutional funders + top individual prospects
- [ ] **Identify open grant opportunities** — draft application answers where applicable

#### Wednesday March 25
- Equitable AI For Outcomes (8am–2pm)
- Kate Rouch (TrueSteele, 1:30)
- [ ] **Evening:** Build SFEF donor intelligence dashboard — adapt existing platform with SFEF donor data, scoring, and filters

#### Thursday March 26
- Nick Cain (Kindora, 9:30), Usability Research (10am–1pm)
- Oakland Tech Week (5:30pm)
- [ ] **PM:** Dashboard refinement and testing
- [ ] **Finalize all individual donor outreach drafts**
- [ ] **Complete approach strategy memos** for top 10 funders

#### Friday March 27
- Kindora + Blackbaud sync (9am)
- [ ] **Finalize all deliverables:**
  - SFLC Institutional Funder Prospect List (25–40 funders) with scoring
  - Top 10 approach strategy memos
  - Draft LOIs and application answers
  - Individual donor heat map and intelligence report
  - Top 20 donor profiles with cultivation recommendations
  - Draft outreach messages (institutional + individual)
  - Dashboard deployed and accessible
- [ ] **Prep final presentation** — slides/deck summarizing findings, key recommendations

#### Saturday March 28 — SPRINT DEADLINE
- [ ] **Present findings to SFEF leadership team** (Laura, Ann, Terrence + stakeholders)
- [ ] **Send $16K invoice** — second payment, due April 15 with Net 15
- [ ] **Sprint Phase complete**

---

### BUFFER WEEK: March 30 – April 3
**UNAVAILABLE — OC Joshua Tree Trip**

No SFEF work this week. Any spillover from sprint should be wrapped before March 28.

---

## Advisory Phase (April 1 – May 31)

**5 hours/month** of scheduled meetings and ad hoc advisory. Prep time for listed deliverables is included in retainer.

### April Deliverables
- [ ] **Board Presentation Deck** — translate sprint findings into board-ready narrative for SFEF's next board meeting
- [ ] **90-Day Cultivation Calendar** — sequenced action plan: who to contact, when, with what message (institutional + individual)
- [ ] **Ongoing advisory** — donor conversation coaching, funder approach review, dashboard guidance

### May Deliverables
- [ ] **Donor Data Refresh** — updated scoring cycle at ~60-day mark to reflect new donor activity and outreach outcomes
- [ ] **Ongoing advisory** — continued strategic support through first outreach round

---

## Automation Plan (What Runs Without Me)

These pipelines can execute overnight or during SXSW with minimal supervision:

| Pipeline | Script/Tool | Runtime | Notes |
|----------|-------------|---------|-------|
| LinkedIn enrichment | `enrich_contacts_apify.py` | ~2 hrs for 500 contacts | Apify, 32 concurrent |
| Email discovery | `find_emails.py` | ~3 hrs for 500 contacts | ZeroBounce verification |
| FEC donations | `enrich_fec_donations.py` | ~4 hrs (rate limited) | 4 workers, 1K/hr cap |
| Real estate | `enrich_real_estate.py` | ~1 hr for 500 contacts | 411.com + Zillow |
| Web research | `enrich_web_research.py` | ~2 hrs for 50 contacts | Perplexity + GPT |
| Donor scoring | `score_ask_readiness.py` | ~30 min for 500 contacts | GPT-5 mini, 150 workers |
| AI tagging | `tag_contacts_gpt5m.py` | ~15 min for 500 contacts | GPT-5 mini, 150 workers |
| Embeddings | `generate_embeddings.py` | ~10 min for 500 contacts | text-embedding-3-small |

**Strategy:** Queue enrichment pipelines Tuesday night March 11 before flying to Austin. Monitor via phone. By Monday March 16, all enrichment should be complete and ready for scoring.

---

## Key Risks

1. **CRM data quality** — if SFEF's donor data is messy, cleanup could eat into Week 1 time. Mitigate: ask for export format during kickoff.
2. **SXSW overlap** — 3 days of sprint time lost. Mitigate: automate enrichment, use SXSW evenings for reviews.
3. **Week 3 meeting density** — very little unblocked time. Mitigate: front-load analysis work in Week 2, use evenings in Week 3 for writing.
4. **Presentation timing** — March 28 is Saturday. May need to schedule for Friday March 27 instead. Confirm with Laura.
5. **OC trip buffer** — no flex time after March 28. Everything must ship on time.

---

## Immediate Actions (Today, March 10)

1. **Countersign DocuSign** and return to Laura
2. **Send first invoice** ($16K)
3. **Schedule kickoff call** with Laura, Ann, Terrence (today if possible, tomorrow AM latest)
4. **Email Laura** requesting CRM donor data export (CSV or similar)
5. **Set up SFEF data workspace** in Supabase
6. **Begin Kindora scan** for SFLC institutional funders
