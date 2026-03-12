# Come Alive 2026 — Campaign Execution Plan

**Last updated:** March 2, 2026
**Data source:** Supabase `campaign_2026` column (live pipeline data)

---

## Justin's Next Steps

The data pipeline is done. 317 contacts are scaffolded, 25 personal messages are written, 292 campaign copy variants are generated. Everything lives in Supabase. The campaign UI and kanban pipeline are built and ready.

### Tonight (March 2)

- [ ] **Send all 25 List A personal outreach messages.** Review, edit, and send via the campaign UI (`/tools/campaign` → List A tab). Go highest capacity first.
- [ ] **Move sent contacts** to "Outreach Sent" on the kanban (`/tools/pipeline?pipeline=oc-come-alive-2026`)

### This Week (March 3-8)

- [ ] **Text follow-up to List A non-responders** (3-5 days after send). Messages are in `personal_outreach.follow_up_text`.
- [ ] **Get social proof.** Ask early "yes" replies for permission to reference them ("12 people have already stepped up").
- [ ] **Finalize Email 1 copy.** Insert real progress numbers into the template in `COME_ALIVE_2026_Campaign.md`.

### Open Decisions

These need answers before March 10:

| Decision | Options | Notes |
|:--|:--|:--|
| **Mass email tool** | Gmail BCC? Mailchimp? Loops? Campaign UI send button? | You need to send to 317 people. Plain text, personal email address. Gmail BCC caps at ~500/day — works but no tracking. Campaign UI has a "Send Email 1" button that sends via Gmail API. |
| **Open/click tracking** | Email tool analytics vs. honor system | Needed to trigger text follow-ups ("openers who didn't act"). Without tracking, send follow-ups to everyone who hasn't donated. |
| **Text follow-up delivery** | Manual copy-paste? Community.com? | 50-80 texts in Days 2-5, 200+ in Days 10-14. Manual is fine for 50 — not for 200. |
| **$20K matching donor** | Confirmed? | This is referenced in the campaign emails. |

### What's Already Built

| Asset | Status | Where |
|:--|:--|:--|
| 25 personal outreach messages (Opus 4.6) | Ready to send | `campaign_2026.personal_outreach` |
| 292 text follow-ups + thank-yous (GPT-5 mini) | Ready to send | `campaign_2026.campaign_copy` |
| 25 pre-email notes (prior donors/lapsed) | Ready to send | `campaign_2026.campaign_copy.pre_email_note` |
| Email 1/2/3 templates | Need real numbers inserted | `COME_ALIVE_2026_Campaign.md` |
| Scaffold data (persona, ask, motivation) | Complete | `campaign_2026.scaffold` |
| Campaign execution plan (this doc) | Complete | You're reading it |
| Campaign UI (review/edit/send) | Complete | `/tools/campaign` |
| Kanban pipeline (track progress) | Seeded with 317 deals | `/tools/pipeline?pipeline=oc-come-alive-2026` |

---

## Pipeline Status

| Step | Count | Status |
|:--|--:|:--|
| Contacts scaffolded | 317 | Complete |
| Personal outreach written (List A) | 25 | Complete |
| Campaign copy written (Lists B-D) | 292 | Complete |
| **Total campaign-ready contacts** | **317** | **Ready** |

---

## Master Contact Summary

### By Campaign List

| List | Description | Contacts | Avg Ask | Total Ask Potential |
|:--|:--|--:|--:|--:|
| **A** | Inner circle — personal outreach | 25 | $8,000 | $200,000 |
| **B** | Ready now — email campaign primary | 107 | $4,523 | $484,000 |
| **C** | Cultivate first (score >= 76) | 42 | $5,298 | $222,500 |
| **D** | Cultivate first (score 60-75) | 143 | $3,360 | $480,500 |
| | **Total** | **317** | **$4,373** | **$1,387,000** |

### By Campaign List x Persona

| List | Believer | Impact Professional | Network Peer | Total |
|:--|--:|--:|--:|--:|
| A | 25 | — | — | 25 |
| B | 74 | 31 | 2 | 107 |
| C | 13 | 25 | 4 | 42 |
| D | 27 | 95 | 21 | 143 |
| **Total** | **139** | **151** | **27** | **317** |

### By Persona x Capacity Tier

| Persona | Leadership ($10K) | Major ($5K) | Mid ($2.5K) | Base ($1K) | Community ($250) | Total |
|:--|--:|--:|--:|--:|--:|--:|
| Believer | 24 | 60 | 43 | 11 | 1 | 139 |
| Impact Professional | 12 | 75 | 55 | 9 | — | 151 |
| Network Peer | 5 | 2 | 15 | 4 | 1 | 27 |
| **Total** | **41** | **137** | **113** | **24** | **2** | **317** |

### Ask Amount Distribution

| Ask Amount | Count | Subtotal Potential |
|--:|--:|--:|
| $10,000 | 38 | $380,000 |
| $5,000 | 135 | $675,000 |
| $2,500 | 113 | $282,500 |
| $1,000 | 24 | $24,000 |
| $250 | 2 | $500 |

### By Lifecycle Stage

| List | New | Prior Donor | Lapsed | Total |
|:--|--:|--:|--:|--:|
| A | 22 | 2 | 1 | 25 |
| B | 89 | 13 | 5 | 107 |
| C | 38 | 3 | 1 | 42 |
| D | 140 | 2 | 1 | 143 |
| **Total** | **289** | **20** | **8** | **317** |

---

## List A: Personal Outreach Checklist

25 contacts. Each has a personalized message written by Claude Opus 4.6 in Justin's voice. Channel is email for 24 and text for 1 (Hector Mujica).

### Leadership Tier ($10K ask) — 14 contacts

| # | Name | Company | Channel | Subject | Motivation |
|--:|:--|:--|:--|:--|:--|
| 1 | Chris Busselle | Single Family Office | email | quick thing — before I send the broader ask | relationship |
| 2 | Terry Kramer | UCLA-Anderson | email | quick thing before I send this wider | mission_alignment |
| 3 | Brigitte Hoyer Gosselink | Google | email | quick thing — before I send the big ask | mission_alignment |
| 4 | Rosita Najmi | Micron Technology | email | a personal ask | mission_alignment |
| 5 | Bryan Breckenridge | VITAL | email | quick thing — want your eye on this | relationship |
| 6 | Patrick Dickinson | Ninth Street Capital | email | quick thing | mission_alignment |
| 7 | Mitch Kapor | Kapor Capital | email | quick thing — outdoorithm | mission_alignment |
| 8 | Erin Teague | Disney | email | quick thing | mission_alignment |
| 9 | Freada Kapor Klein | SMASH | email | quick thing — wanted you to hear this first | mission_alignment |
| 10 | Jon Huggett | Catherine Hamlin Foundation | email | quick thing — and an ask | relationship |
| 11 | Lo Toney | Plexo Capital | email | quick thing | mission_alignment |
| 12 | Sergio Garcia | UC Berkeley | email | quick thing — before I go wide | relationship |
| 13 | Karibu Nyaggah | Kindora | email | quick thing — outside of Kindora | mission_alignment |
| 14 | Tyler Scriven | Saltbox | email | quick thing before I send the big ask | relationship |

### Major Tier ($5K-$10K ask) — 11 contacts

| # | Name | Company | Ask | Channel | Subject | Motivation |
|--:|:--|:--|--:|:--|:--|:--|
| 15 | Jason Trimiew | Meta | $10,000 | email | quick thing before I go wide | relationship |
| 16 | Carrie Varoquiers | Workday | $5,000 | email | quick thing — before I send the broader ask | mission_alignment |
| 17 | Marcus Steele | HHS | $5,000 | email | quick thing — OC this year | relationship |
| 18 | Hector Mujica | US Senate | $5,000 | text | *(text message — no subject)* | relationship |
| 19 | Tiffany Cheng Nyaggah | Catalyst Exchange | $5,000 | email | quick thing — before I send the big ask | relationship |
| 20 | Jose Gordon | AWS | $5,000 | email | quick thing — before I send the broader ask | mission_alignment |
| 21 | Kavell Brown | LinkedIn | $5,000 | email | quick thing — wanted you to hear this first | mission_alignment |
| 22 | Austin Swift | Google | $5,000 | email | quick thing — OC's big season | relationship |
| 23 | Roxana Shirkhoda | Private Family Foundation | $5,000 | email | quick ask — want your brain on this | relationship |
| 24 | Kevin Brege | Google.org | $5,000 | email | quick thing | mission_alignment |
| 25 | Adrian Schurr | Google | $5,000 | email | quick thing — 10 trips this year | relationship |

**List A math:** If 15-20 of 25 commit at $5K-$10K average = **$75K-$200K** ask potential. Realistic conversion at 50-60% = **$30K-$50K** from personal outreach.

---

## Day-by-Day Execution Timeline

All dates are 2026. Campaign launches March 10 and closes approximately March 28. Joshua Tree is March 30.

### Pre-Campaign: March 2-9

| Date | Day | Action | Details |
|:--|:--|:--|:--|
| **Mar 2** | **Mon** | **Send all 25 List A personal outreach** | Review, edit, send via campaign UI. Highest capacity first. |
| Mar 3-4 | Tue-Wed | Reply to early responses | Follow up on conversations |
| Mar 5-6 | Thu-Fri | Text follow-up to List A non-responders | 3-4 days after send. Messages in `personal_outreach.follow_up_text` |
| Mar 7-8 | Weekend | Tally early commitments | Get social proof permission. Finalize Email 1 with real numbers. |

**Quiet phase target:** $15K-$25K committed from personal outreach + $45K grants = $60K-$70K (50-58% of $120K).

### Week 1: March 10-16

| Date | Day | Action | Audience | Count |
|:--|:--|:--|:--|--:|
| **Mar 10** | **Tue** | **Email 1: The Invitation** | All Lists A-D | 317 |
| Mar 10 | Tue | Pre-email notes sent first | Prior donors + lapsed (B-D) | 25 |
| Mar 11-13 | Wed-Fri | Reply to responses | Responders | — |
| **Mar 12-14** | **Thu-Sat** | **Text follow-up (opener)** | Email openers who didn't act | Est. 50-80 |

**Email 1 subject options:** *8 trips this year | a personal ask | come alive*
**Story:** Valencia — fear to freedom. Daughter running barefoot. "No fear. Just joy."

### Week 2: March 17-23

| Date | Day | Action | Audience | Count |
|:--|:--|:--|:--|--:|
| **Mar 17** | **Tue** | **Email 2: Momentum Update** | Non-donors only (all lists) | Est. 250-280 |
| Mar 18-21 | Wed-Sat | Continue conversations | Repliers | — |
| **Mar 19-21** | **Thu-Sat** | **Text follow-up (milestone)** | Non-donors | Est. 200-250 |

**Email 2 subject options:** *[X] people are in | quick update | halfway there*
**Story:** The 8-year-old who wanted to "go home to the campfire."
**Include:** Real progress numbers, social proof count, employer matching mention.

### Week 3: March 24-29

| Date | Day | Action | Audience | Count |
|:--|:--|:--|:--|--:|
| **Mar 24** | **Tue** | **Email 3: Final Push** | Non-donors only | Est. 200-250 |

**Email 3 subject options:** *6 days to Joshua Tree | before the season starts | close*
**No new story.** The trip is the story. Joshua Tree is March 30. Genuine urgency is sharper than the original "two weeks."
**~55 words.** Entire email visible on phone without scrolling.

### Post-Campaign: March 30-April 5

| Date | Day | Action | Details |
|:--|:--|:--|:--|
| Mar 25-29 | | Personal thank-yous | Within 24 hours of each gift. Text or email per thank-you workflow. |
| **Mar 30** | **Mon** | Joshua Tree launches | One-line note to donors: "We're here. 40 people. Thank you." |
| Apr 2-5 | | Post-trip photo update | One photo + one line to all campaign donors |

---

## Email Audience Rules

### Email 1: The Invitation (Mar 10)
- **Sent to:** All 317 campaign contacts (Lists A-D)
- **Pre-email note:** 25 contacts with prior_donor or lapsed lifecycle stage receive a brief personal note before Email 1 (already generated in campaign_copy)
- **Format:** Plain text from Justin's personal email. No HTML, no logos.

### Email 2: Momentum Update (Mar 17)
- **Sent to:** Non-donors only (exclude anyone who gave after Email 1)
- **Insert real numbers:** "[X] people have stepped up" and "We're at $[X] toward our $120K goal"
- **Employer matching:** Mention Benevity (Google, Meta, Salesforce, Microsoft, Apple, Amazon)

### Email 3: Final Push (Mar 24)
- **Sent to:** Non-donors only
- **No story.** Trip math only. Joshua Tree countdown creates genuine urgency.
- **Short.** ~55 words. Phone-screen visible.

---

## Text Follow-up Triggers & Timing

292 contacts (Lists B-D) have personalized text follow-ups generated. Channel split for thank-yous: 101 text, 191 email.

| Timing | Trigger | Who | Message Source |
|:--|:--|:--|:--|
| Days 2-4 (Mar 12-14) | Opened Email 1, didn't act | Email openers | `campaign_copy.text_followup_opener` |
| Days 7-11 (Mar 19-21) | Still haven't donated | Non-donors | `campaign_copy.text_followup_milestone` |
| Within 24 hours of gift | Donation received | All donors | `campaign_copy.thank_you_message` or `personal_outreach.thank_you_message` |

**List A follow-ups** are in `personal_outreach.follow_up_text` — personalized by Opus, not GPT-5 mini.

---

## Thank-You Workflow

Speed matters. 82% of first-time donors never give again. A thank-you within 24 hours reinforces identity, empathy, and reward circuits while the warm glow is still active.

### Thank-You by Persona x Motivation Flag

| Persona | Motivation | Thank-You Frame | Channel |
|:--|:--|:--|:--|
| Believer (139) | relationship (58) | "Means the world" — personal, warm, references shared history | text |
| Believer | mission_alignment (73) | "You're helping families come alive" — impact-centered | text |
| Believer | parental_empathy (3) | "You're showing up for families like Valencia's" — parental | text |
| Believer | justice_equity (5) | "This is what showing up looks like" — equity-affirming | text |
| Impact Professional (151) | mission_alignment (143) | "Your gift is building what public lands should have been" — systems framing | email |
| Impact Professional | justice_equity (8) | "Helping build what public lands should have been" — equity + systems | email |
| Network Peer (27) | mission_alignment (20) | "You're the kind of person who shows up" — identity-affirming | email |
| Network Peer | peer_identity (4) | "Means a lot coming from you" — peer validation | email |
| Network Peer | parental_empathy (2) | "You're showing up for families" — parental + peer | email |
| Network Peer | relationship (1) | "Means the world" — personal warmth | email |

**Key rule:** Identity-affirming language always. "You're the kind of person who shows up" > "Thank you for your generous gift."

### Thank-You Channel Summary

| Channel | Count | When to Use |
|:--|--:|:--|
| Text | 101 | Believers (close relationships), contacts with SMS history |
| Email | 216 | Impact Professionals, Network Peers, formal relationships |

*(25 List A thank-yous via personal_outreach + 292 List B-D via campaign_copy = 317 total)*

### Thank-You Template

> [Name] — this means the world. You're the kind of person who shows up for families like Valencia's, and that's exactly what you just did. Your gift is going toward our Pinnacles trip in May — 12 families, three days in the park. I'll send you a photo from the campfire.
>
> — Justin

**Adapt per persona and motivation flag using the matrix above.** Each contact's personalized thank-you is pre-written in `campaign_2026.campaign_copy.thank_you_message` (Lists B-D) or `campaign_2026.personal_outreach.thank_you_message` (List A).

---

## Post-Campaign Measurement Plan

Track these metrics during and after the campaign. Run the full post-mortem from OC_FUNDRAISING_PLAYBOOK.md Section 7.

### During Campaign

| Metric | How to Track |
|:--|:--|
| Total raised by source | Personal outreach, email, match, employer matching |
| Donor count | New vs. returning, by tier |
| Conversion funnel | Emails sent (317) → opened → clicked → donated |
| Gift range accuracy | Compare actual distribution to pyramid: 38 leadership, 137 major, 113 mid, 24 base, 2 community |
| Pre-campaign % at launch | $35K grants + quiet phase commitments as % of $100K |
| Time to close | When did most gifts arrive relative to emails? |
| Channel attribution | Which email/text/conversation drove each gift? |
| Thank-you speed | % of donors thanked within 24 hours (target: 100%) |

### Post-Campaign (April)

| Action | Timeline |
|:--|:--|
| Post-trip photo to all donors | Apr 2-5 (after Joshua Tree) |
| Full post-mortem | Apr 7-11 |
| Donor retention plan | Apr 14-18 |
| Cultivation plan for 2027 prospects | Apr 21-25 |

### Gift Range Pyramid Check

Compare actual results against the scaffolded pyramid:

| Tier | Ask Amount | Contacts | Target # Donors | Target Revenue |
|:--|--:|--:|--:|--:|
| Leadership | $10,000 | 38 | 1-3 | $10K-$30K |
| Major | $5,000 | 137 | 4-8 | $20K-$40K |
| Mid | $2,500 | 113 | 6-12 | $15K-$30K |
| Base | $1,000 | 24 | 8-12 | $8K-$12K |
| Community | $250 | 2 | 2 | $500 |

---

## Quick Reference: Where to Find Everything

| What | Where |
|:--|:--|
| Pre-written personal outreach (List A) | `campaign_2026.personal_outreach` — 25 messages |
| Pre-written campaign copy (Lists B-D) | `campaign_2026.campaign_copy` — 292 contacts |
| Scaffold data (persona, ask, motivation) | `campaign_2026.scaffold` — all 317 contacts |
| Email 1/2/3 templates | `docs/Outdoorithm/COME_ALIVE_2026_Campaign.md` |
| Donor personas and execution matrix | `docs/Outdoorithm/DONOR_SEGMENTATION.md` |
| Campaign methodology and psychology | `docs/Outdoorithm/OC_FUNDRAISING_PLAYBOOK.md` |
| Ask readiness dashboard | `/tools/ask-readiness` (Vercel app) |
| Donation link | outdoorithmcollective.org/donate |

---

## What We Don't Do

- **Manufacture urgency.** Joshua Tree on March 30 is real.
- **Over-polish.** Warm and slightly imperfect beats polished and hollow.
- **Cold-call anyone.** "Reply and we can talk" is the bridge.
- **Mix stories with statistics.** One family's story per email. Not "100+ families served."
- **Let donors "own" trips.** "I'll count you in" = joining a team, not buying a trip.
- **Compromise the experience.** Trips center the families. Donors are supporters, not guests.
