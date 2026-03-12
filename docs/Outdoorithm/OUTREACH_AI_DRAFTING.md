# Outreach AI Drafting — Methodology

**How we use Claude Opus 4.6 to draft personalized fundraising outreach at scale.**

Last run: February 25, 2026 — 24 List A personal outreach messages rewritten.

---

## Script

`scripts/intelligence/rewrite_outreach_opus.py`

```
source .venv/bin/activate
python -u scripts/intelligence/rewrite_outreach_opus.py --dry-run           # preview all
python -u scripts/intelligence/rewrite_outreach_opus.py --contact-id 482 --dry-run  # single contact
python -u scripts/intelligence/rewrite_outreach_opus.py                     # write to Supabase
```

---

## How It Works

One API call per contact. Each call sends:

1. **System prompt** (~75K chars) — loaded once, shared across all contacts:
   - Full `JUSTIN_EMAIL_PERSONA.md` (voice, structure, quirks, templates)
   - Full `COME_ALIVE_2026_Campaign.md` (campaign facts, story, math, tiers)
   - Hard rules (see below)

2. **Contact prompt** (~25-36K chars per person) — everything we know:
   - Basic info: name, company, position, headline, location
   - Relationship with Justin: connection type, warmth level, familiarity rating, notes
   - Full communication history: every email thread summary, meetings, calls, chronological summary
   - Donor profile: capacity/propensity/affinity/warmth scores, tier, estimated capacity, past giving
   - AI analysis: tags, proximity score, capacity score, OC fit
   - Employment history, education, board positions, volunteering
   - FEC political donations, real estate data
   - OC engagement (trip attendance)
   - LinkedIn reactions to Justin's posts
   - Ask readiness: score, tier, timing, suggested range, personalization angle, receiver frame, risk factors
   - Campaign scaffold: persona, capacity tier, lifecycle, motivation, lead story, opener insert
   - Current draft message (the one being rewritten)

---

## Hard Rules in the System Prompt

These are non-negotiable constraints the model must follow:

### Campaign facts (must appear in every email)
- 8 trips this season
- Each trip costs about $10K to run
- Plus $40K in gear so every family shows up equipped
- $120K for the full season
- $45K raised from grants and early supporters
- A friend is matching the first $20K dollar-for-dollar
- $75K to go

### Voice rules
1. **No em dashes** in email — use periods, commas, sentence breaks
2. **Calls are earned, not initiated** — "Happy to talk if you want to know more" not "Let's jump on a call"
3. **"Would love to count you in"** — not "Would mean a lot" or "Would mean the world"
4. **Under 200 words** for the message body
5. **No specific dollar amount ask** in first touch — anchors live in the conversation
6. **Story first, then math** — emotion creates impulse, math gives permission
7. **Joining frame** — "If you want in" / "Would love to count you in"
8. **Lead with feeling, not framework** — don't explain "come alive," let stories carry it
9. **Donor-centric language** — "you"/"your" at 2:1 over "we"/"our"
10. **Plain text** — no bullet points, no bold, no formatting
11. **Sign off with "Justin"** — no "Best," no "Sincerely"
12. **Greeting**: "Hey [Name]," for warm, "Hi [Name]," for less familiar
13. **No "means the world"** or "means a lot" anywhere
14. **No "outdoor equity nonprofit"** or "underserved communities" — describe what happens
15. **Subject lines**: short, lowercase

### Output format
JSON object with `subject_line` and `message_body`. No markdown, no commentary.

---

## Validation Checks

The script automatically checks every output:
- Word count (target: under 200)
- `gear` mentioned
- `$120K` or `120K` mentioned
- `8 trip` mentioned
- No em dash (U+2014) present

Any failures are flagged as warnings in the summary.

---

## When to Rerun

Rerun the script when:
- Campaign numbers change (update `COME_ALIVE_2026_Campaign.md` first, then rerun)
- New contacts are added to List A with scaffolded personal outreach
- Voice or framing feedback requires systematic changes across all messages
- Communication history is updated and you want messages to reflect recent conversations

The script reads the current `campaign_2026.personal_outreach.message_body` as context for the rewrite, so it improves on whatever is there — it doesn't start from scratch.

---

## Reference Docs

| Doc | Role |
|:--|:--|
| `docs/Justin/JUSTIN_EMAIL_PERSONA.md` | Justin's voice, patterns, quirks — the "how it sounds" |
| `docs/Outdoorithm/COME_ALIVE_2026_Campaign.md` | Campaign facts, story, math, tiers — the "what to say" |
| `docs/Outdoorithm/OC_FUNDRAISING_PLAYBOOK.md` | Donor psychology, methodology — the "why it works" |
| `docs/Outdoorithm/COME_ALIVE_Framing_Analysis.md` | Brand frame, asset-based language — the "how to frame it" |

---

## Cost

Each run of 24 contacts costs approximately $15-25 in API usage (Opus 4.6 with ~110K input tokens and ~300 output tokens per contact). Dry runs cost the same since the API is still called — use `--contact-id` to test on a single contact first.
