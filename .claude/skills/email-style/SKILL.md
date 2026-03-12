---
name: email-style
description: Load Justin's email writing style guide and related docs for drafting emails
user-invocable: true
---

# Email Writing Context

Load Justin's email persona guide and any other reference documents needed for drafting emails in his voice.

## Required: Always load this document
@../../docs/Justin/JUSTIN_EMAIL_PERSONA.md

## Optional: Load if relevant to the task
- Justin's bio: @../../docs/Justin/Justin Bio.md
- Outreach drafting guidance: @../../docs/Outdoorithm/OUTREACH_AI_DRAFTING.md

## Required: Always load this document too
@../../docs/Writing/Signs of AI Writing.md

## Instructions

After loading the style guide above, confirm to the user which documents were loaded and ask what email they'd like to draft. Follow the persona guide precisely — tone, structure, vocabulary, sign-offs, and patterns should all match Justin's authentic voice.

## Anti-AI-Tell Rules (enforce on EVERY draft)

Before finalizing any email, audit it against these rules. Fix violations before presenting or sending:

1. **No em dashes in email.** Justin's persona guide says "rarely in email, default to sentence breaks." Treat this as a hard rule: zero em dashes. Use periods, commas, or parentheses instead.
2. **No generic significance padding.** Cut phrases like "creating unnecessary complexity and potential failure points," "this underscores the importance," "testament to," "broader landscape." Say the specific thing.
3. **No symmetric triads or listicles.** "Remove X, harden Y, test Z" is an AI tell. Vary the rhythm. Two items or four are less suspicious than three.
4. **No present-participle pileups.** Never end sentences with stacked gerunds ("...fostering X, enabling Y, enhancing Z").
5. **No "not X but Y" parallelism** unless Justin used it once for emphasis in the original draft.
6. **Prefer simple verbs.** "is/are/has/does" over "serves as/showcases/represents/transitions cleanly."
7. **Keep human cadence.** Vary sentence length. Allow fragments. Use contractions. Leave 1-2 small imperfections if they feel authentic.
8. **No vague authority phrases.** "Experts say," "research shows," "many believe" — cut unless citing something specific.

## Gmail Draft Formatting

When creating Gmail drafts via `draft_gmail_message`, ALWAYS use `body_format: "html"` with `<p>` tags for paragraphs. Never use plain text format or `<br><br>` for paragraph breaks — both cause formatting issues in Gmail:
- **Plain text** hard-wraps lines at ~72 characters, creating ugly narrow columns
- **`<br><br>`** can trigger Gmail's thread trimming algorithm, which collapses content behind a "..." click

Use this pattern for every draft:
```html
<div dir="ltr">
<p style="margin:0 0 12px 0">First paragraph.</p>
<p style="margin:0 0 12px 0">Second paragraph.</p>
<p style="margin:0">Justin</p>
</div>
```

The `margin:0 0 12px 0` gives natural paragraph spacing. Use `margin:0` on the final line (sign-off) to avoid trailing whitespace.
