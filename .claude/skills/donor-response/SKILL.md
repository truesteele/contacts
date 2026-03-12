---
name: donor-response
description: Draft a personalized response to a donor who has offered or made a gift to Outdoorithm Collective. Use when someone responds to a campaign email, personal outreach, or any fundraising ask with intent to give. Pulls relational context from Supabase, applies donor psychology, and writes in Justin's authentic email voice.
user-invocable: true
---

# Donor Gift Response

Draft a personalized thank-you or logistics response to someone who has offered or completed a gift to Outdoorithm Collective.

## Required: Always load these documents

@../../docs/Justin/JUSTIN_EMAIL_PERSONA.md
@../../docs/Outdoorithm/COME_ALIVE_2026_Campaign.md
@../../docs/Outdoorithm/OC_FUNDRAISING_PLAYBOOK.md
@../../docs/Writing/Signs of AI Writing.md

## Instructions

### Step 1: Identify the donor

Get the donor's name from the user or the email thread. Look them up in Supabase:

```sql
SELECT id, first_name, last_name, email, company, position, headline,
  city, state, familiarity_rating, comms_closeness, comms_momentum,
  ai_tags, ask_readiness, campaign_2026, oc_engagement,
  communication_history, comms_summary, comms_reasoning,
  enrich_current_company, enrich_current_title,
  cultivation_stage, fec_donations
FROM contacts
WHERE last_name ILIKE '%{LAST_NAME}%' AND first_name ILIKE '%{FIRST_NAME}%'
```

Use `mcp__supabase-contacts__execute_sql` for this query.

### Step 2: Read the email thread

If the user hasn't pasted the email, search for it in Gmail:

```
mcp__google-workspace__search_gmail_messages(query="from:{donor_email}", user_google_email="justinrsteele@gmail.com")
```

Then fetch the most recent message content to understand what the donor said.

### Step 3: Analyze context

From the Supabase record, extract:

- **Relationship depth:** `familiarity_rating` (1-4), `comms_closeness`, `comms_momentum`
- **Communication history:** `communication_history` threads (what you've talked about, shared history)
- **Campaign context:** `campaign_2026` (what outreach was sent, personalization hooks, suggested ask range)
- **Ask readiness:** `ask_readiness` (score, reasoning, personalization_angle, receiver_frame)
- **OC engagement:** `oc_engagement` (have they attended trips, volunteered?)
- **Their world:** company, position, headline, city/state

### Step 4: Draft the response

Apply these donor psychology principles from the playbook:

#### Speed
Thank-you within 24 hours. The brain's reward, empathy, and identity circuits cool within hours. A thank-you that arrives while the glow is warm reinforces all three.

#### Identity-affirming language
"You're the kind of person who shows up for families like Valencia's" hits harder than "thanks for your generous gift." Position the donor as someone whose identity is confirmed by this act, not just someone who wrote a check.

Calibrate intensity to the relationship:
- **Close friends (familiarity 3-4, inner_circle):** Keep it real. "This means a lot" or "Man, thank you" is more authentic than formal gratitude language.
- **Warm contacts (familiarity 2-3):** Slightly more identity language. "You're exactly the kind of person I was hoping would step up."
- **Professional/newer relationships (familiarity 1-2):** More structured gratitude with specific impact.

#### Specific impact
Tie their gift to a named trip or concrete outcome. Use the campaign gift range chart:

| Amount | Impact |
|:--|:--|
| $250 | Sends one family camping |
| $500 | Gear for a family (quality tent and camp systems) |
| $1,000 | A family at the campfire |
| $2,500 | A quarter of a trip funded |
| $5,000 | Half a trip (rest, community, grit for 10 families) |
| $10,000 | A full trip (10-12 families come alive together) |

#### The match
If the $20K match is still live, mention it naturally: "Your $X doubles with the match" or "With the match that's $2X." Don't belabor it.

#### Promise of follow-up
"I'll send you a photo from the campfire" or reference a future touchpoint. Creates continuity and anticipation.

#### Keep the relationship thread alive
Reference something specific from your history together (from `communication_history`). If there was a personalization hook in the campaign outreach (`campaign_2026.personal_outreach`), carry it forward.

### Step 5: Donation logistics

If the donor asked for logistics (EIN, where to donate, etc.), include:

- **Official org name:** Outdoorithm Collective Fund
- **EIN:** 99-4715981
- **Donate link:** [donate](https://outdoorithmcollective.org/donate?frequency=one-time) (always hyperlink, never show the full URL)
- **Employer matching:** If their company is Google, Meta, Salesforce, Microsoft, Apple, or Amazon, mention Benevity/YourCause matching: "If {company} matches through Benevity, your gift doubles again at no extra cost."

### Step 6: Anti-AI-Tell Audit (MANDATORY)

Before presenting ANY draft, run every sentence through this checklist. Fix all violations before showing to the user. This is the most important step. AI-sounding email destroys trust with donors.

**Hard rules (zero tolerance):**

1. **ZERO em dashes.** Not one. Replace with periods, commas, or parentheses. Justin rarely uses em dashes in email (see persona guide: "rarely in email, default to sentence breaks"). This is the single most common AI tell.
2. **No generic significance padding.** Cut: "testament to," "broader landscape," "underscores the importance," "pivotal moment," "creating unnecessary complexity." Say the specific thing or say nothing.
3. **No symmetric triads or listicles.** "Remove X, harden Y, test Z" is an AI fingerprint. Two items or four are less suspicious than three. Vary the rhythm.
4. **No present-participle pileups.** Never end sentences with stacked gerunds ("...fostering X, enabling Y, enhancing Z").
5. **No "not X but Y" parallelism** unless used exactly once for emphasis.
6. **No vague authority phrases.** "Experts say," "research shows," "many believe." Cut unless citing something specific.

**Voice rules (enforce always):**

7. **Prefer simple verbs.** "is/are/has/does" over "serves as/showcases/represents/transitions cleanly."
8. **Keep human cadence.** Vary sentence length. Allow fragments. Use contractions. Leave 1-2 small imperfections if they feel authentic.
9. **Match the register to the relationship.** Close friends get casual warmth. Newer contacts get slightly more structure. Never over-formal.
10. **Don't over-smooth.** If a sentence sounds like it was polished by a copywriter, roughen it up. Justin's emails read like he typed them on his phone, because he often did.

**Final check:** Read the draft out loud. If any sentence sounds like it came from a fundraising template or a corporate thank-you card, rewrite it.

### Step 7: Format considerations

- **If creating a Gmail draft:** Use `body_format: "html"` with `<p style="margin:0 0 12px 0">` tags. Never plain text (hard-wraps at 72 chars) or `<br><br>` (triggers Gmail thread trimming).
- **If just presenting the draft:** Show as plain text for the user to review.
- **Account:** Campaign emails are typically sent from `justin@outdoorithmcollective.org` but personal thank-yous from close friends may come from `justinrsteele@gmail.com`. Match the account the donor replied to.

### Tone calibration by relationship tier

| Closeness | Greeting | Gratitude style | Sign-off | Length |
|:--|:--|:--|:--|:--|
| Inner circle (familiarity 4) | "Hey Tyler," | "Man, this means a lot." | "Justin" | 50-80 words |
| Close (familiarity 3) | "Hey [Name]," | "This means the world. Thank you." | "Justin" | 60-100 words |
| Warm (familiarity 2) | "Hi [Name]," or "Hey [Name]," | "[Name], this means the world. You're the kind of person who shows up..." | "With gratitude, Justin" | 80-120 words |
| Professional (familiarity 1) | "Hi [Name]," | "Thank you, [Name]. Your gift is going toward..." | "With gratitude, Justin" | 100-150 words |

### What NOT to do

- **Don't push for more.** They gave what they gave. Even if $1K is below a $25K-$100K suggested range, celebrate the $1K. The relationship matters more than the gift size. Cultivation for a larger gift happens over time, not in the thank-you.
- **Don't over-explain OC.** They already know enough to give. Don't re-pitch.
- **Don't manufacture urgency.** If there's genuine urgency (trip date), mention it naturally. Don't invent it.
- **Don't mix gratitude with another ask.** The thank-you is pure. No "and by the way" asks.
- **Don't send a template.** Every response must reference something specific from the donor's message, your shared history, or their world.
