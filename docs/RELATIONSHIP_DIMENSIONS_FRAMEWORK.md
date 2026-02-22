# Relationship Dimensions Framework

## Overview

Our contact intelligence system measures relationship strength across **two independent dimensions**, inspired by Granovetter's (1973) tie strength theory. Each dimension captures different aspects of relationship quality, and together they reveal actionable segments that neither measure could identify alone.

---

## Granovetter's Four Dimensions of Tie Strength

Mark Granovetter identified four dimensions that determine the strength of an interpersonal tie:

1. **Time invested** — How much time is spent in the relationship (frequency, duration of interactions)
2. **Emotional intensity** — The depth of feeling and personal significance of the relationship
3. **Intimacy** — Mutual confiding, trust, and the private nature of exchanges
4. **Reciprocity** — The degree to which both parties invest in the relationship (vs. one-way)

These four dimensions cluster naturally into two groups:

- **Subjective/perceptual**: Emotional intensity + Intimacy — How close do I *feel* to this person?
- **Behavioral/observable**: Time invested + Reciprocity — How much do we *actually* communicate?

---

## Dimension 1: Familiarity Rating (Subjective)

**Field:** `familiarity_rating` (integer, 0–4)
**Source:** Justin's manual assessment of every contact
**Updated:** One-time comprehensive review (Feb 2026)

| Score | Label | Meaning |
|-------|-------|---------|
| 0 | Stranger | Don't recognize the name |
| 1 | Recognize | Know the name/face, minimal interaction |
| 2 | Acquaintance | Have met, know who they are, some shared context |
| 3 | Good relationship | Genuine rapport, would take a call/meeting |
| 4 | Close/trusted | Inner circle, high trust, personal relationship |

### What it captures (Granovetter mapping):
- **Emotional intensity** — How personally significant is this person to Justin?
- **Intimacy** — How much mutual trust and confiding exists?
- Partially captures **historical time invested** — years of shared context inform the rating

### What it does NOT capture:
- Current communication activity (a 4-rated friend you haven't spoken to in 3 years is still rated 4)
- Whether the relationship is active, growing, or dormant
- Communication reciprocity (one-way vs. bidirectional)
- Channel mix (are exchanges happening via SMS, email, LinkedIn?)

---

## Dimension 2: Communication Closeness (Behavioral/Data-Derived)

**Field:** `comms_closeness` (enum label, set by GPT-5 mini)
**Source:** Raw communication data from all channels (email, LinkedIn DMs, SMS)
**Updated:** Recomputed whenever communication data changes

### Labels

| Label | Meaning |
|-------|---------|
| `active_inner_circle` | Frequent, recent, bidirectional communication across intimate channels (SMS, 1:1 email). This person is in regular active contact. |
| `regular_contact` | Consistent communication pattern. Not daily, but reliably in touch — monthly or quarterly exchanges, mostly bidirectional. |
| `occasional` | Some communication exists but it's infrequent. A few threads over a long period, or a burst of activity that hasn't sustained. |
| `dormant` | Communication history exists but has gone cold. Last meaningful exchange was 6+ months ago. The relationship *was* active but isn't currently. |
| `one_way` | Communication is predominantly one-directional. Either Justin reaches out without response, or the contact reaches out without sustained engagement. |
| `no_history` | Zero communication records across all channels. |

### Communication Momentum

**Field:** `comms_momentum` (enum label, set by GPT-5 mini alongside closeness)

| Label | Meaning |
|-------|---------|
| `growing` | Communication frequency or depth is increasing. More recent activity than historical average. New channels being used. |
| `stable` | Consistent pattern over time. No significant change in frequency or depth. |
| `fading` | Communication was once more active but is declining. Gaps are lengthening. |
| `inactive` | No recent communication. Flat line. |

### Reasoning

**Field:** `comms_reasoning` (free text, set by GPT-5 mini)

A 1-2 sentence explanation of the assessment, citing specific evidence. Example:
> "Regular bidirectional email exchange (14 threads over 18 months) plus recent SMS activity. Last contact 2 weeks ago. Pattern is stable with slight uptick after OC event in January."

### Signal Quality by Channel

The GPT prompt instructs the model to weight channels differently based on their inherent signal quality:

| Channel | Signal Quality | Why |
|---------|---------------|-----|
| **SMS** | Highest | Most intimate channel. Reserved for people you actually know. Implies phone number exchange, which is a trust signal. |
| **1:1 Email** | High | Direct, intentional communication. Requires knowing someone's email. |
| **LinkedIn DM** | Medium | Direct but lower barrier. Platform-mediated. Common for professional networking without deep relationship. |
| **Group Email** | Low | Shared context but not necessarily relationship. Being CC'd on a group thread is weak signal. |

### Input Data Provided to GPT

For each contact, the model receives:
- Total thread count per channel (email, LinkedIn, SMS)
- Thread count that is bidirectional vs. one-way per channel
- Date of first and last communication per channel
- Date of most recent communication across all channels
- Whether group threads exist (and what fraction of email threads are group vs. 1:1)
- Message count per channel
- A chronological summary of communication activity (e.g., "3 emails in 2024, 1 LinkedIn DM in 2025, 2 SMS in Feb 2026")

The model does NOT receive:
- The familiarity_rating (to keep the dimensions independent)
- Message content or subject lines (privacy + prompt size)
- The contact's name or profile data (to prevent the model from using external knowledge)

---

## The 2x2 Relationship Map

Combining both dimensions creates four actionable quadrants:

```
                    Communication Closeness
                    Low                    High
                ┌──────────────────┬──────────────────┐
           High │  DORMANT STRONG  │  ACTIVE INNER    │
                │  TIES            │  CIRCLE          │
Familiarity     │                  │                  │
Rating          │  You know them   │  Close AND in    │
                │  well but aren't │  regular contact. │
                │  in touch.       │  Your core.      │
                │  HIGHEST LEVERAGE│                  │
                │  for reactivation│                  │
                ├──────────────────┼──────────────────┤
           Low  │  COLD CONTACTS   │  ACTIVE WEAK     │
                │                  │  TIES            │
                │  Don't know them,│  Communicate     │
                │  don't talk.     │  regularly but   │
                │  Lowest priority │  not personally  │
                │  for outreach.   │  close. Group    │
                │                  │  threads, LinkedIn│
                │                  │  networking.     │
                └──────────────────┴──────────────────┘
```

### Fundraising Implications by Quadrant

| Quadrant | Familiarity | Comms | Strategy |
|----------|------------|-------|----------|
| **Active Inner Circle** | 3-4 | active/regular | Direct ask. These people know you and are in touch. Warm introduction to the cause if not already engaged. |
| **Dormant Strong Ties** | 3-4 | dormant/occasional | **Highest leverage.** Reactivate with personal outreach. "It's been too long" opener. They already trust you — you just need to reconnect. |
| **Active Weak Ties** | 0-2 | active/regular | Cultivate deeper. Move from transactional to personal. Invite to events, find shared interests beyond the current communication context. |
| **Cold Contacts** | 0-2 | dormant/none | Low priority unless strong profile overlap with your cause. Requires introduction or shared context to initiate. |

### Momentum as a Third Signal

The `comms_momentum` field adds a temporal dimension that further refines strategy:

- **Dormant Strong Tie + Growing momentum** = Relationship is naturally reactivating. Strike now.
- **Active Inner Circle + Fading momentum** = Risk of losing an engaged supporter. Check in.
- **Active Weak Tie + Growing momentum** = Relationship is deepening organically. Nurture it.
- **Cold Contact + Growing momentum** = New connection forming. Pay attention.

---

## Implementation Notes

### Independence of Dimensions

The two dimensions are deliberately kept independent:
- `familiarity_rating` is never shown to the comms scoring model
- `comms_closeness` is computed purely from behavioral data
- This prevents circular reasoning and ensures each measure adds unique signal

### When to Re-score

- **familiarity_rating**: Updated manually by Justin when relationships meaningfully change
- **comms_closeness + comms_momentum**: Re-scored whenever new communication data is ingested (new email sync, LinkedIn export, SMS backup import)

### Relationship to Ask-Readiness

The ask-readiness model (`score_ask_readiness.py`) receives BOTH dimensions as input, along with profile data, overlap scores, and engagement history. It synthesizes all signals into a holistic fundraising readiness assessment. The two relationship dimensions are key inputs but not the only factors — capacity, alignment, and engagement history also matter.

---

## References

- Granovetter, M. S. (1973). "The Strength of Weak Ties." *American Journal of Sociology*, 78(6), 1360–1380.
- Granovetter, M. S. (1983). "The Strength of Weak Ties: A Network Theory Revisited." *Sociological Theory*, 1, 201–233.
- Marsden, P. V., & Campbell, K. E. (1984). "Measuring Tie Strength." *Social Forces*, 63(2), 482–501.
