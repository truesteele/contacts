import { NextResponse } from 'next/server';
import OpenAI from 'openai';

export const runtime = 'nodejs';

interface EmailInput {
  id: string;
  from: string;
  fromName: string;
  subject: string;
  snippet: string;
  account: string;
}

interface Classification {
  id: string;
  category: 'action' | 'fyi' | 'skip';
  reason: string;
}

const SYSTEM_PROMPT = `You classify emails for Justin Steele, a startup CEO and nonprofit leader.
For each email, output exactly one category: action, fyi, or skip.

ABOUT JUSTIN (for context):
- CEO of Kindora (ed-tech). Co-founder of Outdoorithm / Outdoorithm Collective (outdoor equity nonprofit).
- Board member: San Francisco Foundation. Former: Google.org Director, Year Up, Bridgespan, Bain.
- His email accounts: justinrsteele@gmail.com, justin@truesteele.com, justin@kindora.co, justin@outdoorithm.com, justin@outdoorithmcollective.org

═══ SKIP — Cold sales, spam, automated noise ═══

Classify as SKIP when ANY of these are true:

COLD SALES PATTERNS:
- Subject uses sales cadence language from an unknown sender: "following up", "gentle nudge",
  "quick question", "can I help", "win back", "save time", "last follow up", "checking in",
  "circling back", "touching base", "wanted to connect", "reaching out"
- Sender domain looks like a sales/marketing SaaS tool — domains containing words like:
  mail, pulse, boost, sprint, clarity, brand, pitch, forge, scale, outreach, prospect, lead,
  growth, funnel, pipeline, hub, reach, engage, convert, nurture
- Fake "RE:" or "Re:" — a reply-style subject but the email is actually a cold first contact
  (the sender never had a real conversation with Justin)
- Subject mentions "True Steele LLC", "Kindora", or "Outdoorithm" by name in a cold pitch
  (scraped from LinkedIn/website to personalize)
- Unsolicited offers: interns, PR services, podcast appearances, partnerships, hiring/recruiting
  tools, SEO, web development, AI tools — from people Justin doesn't know
- Subject contains Justin's first name as a lazy personalization token:
  "Justin - following up", "last follow up Justin", "A gentle nudge from my end"
- Sender name looks like a sales rep + generic company: "Marcus from ClarityMail", etc.

NEWSLETTERS/MARKETING:
- Mass-distributed newsletters from mailing list platforms (beehiiv, convertkit, substack, mailchimp)
  UNLESS the sender is someone Justin personally knows

═══ FYI — Informational, no reply needed ═══

- Thank-you notes for events Justin already attended
- "Fwd:" messages that are FYI-only (no question asked)
- Event recaps or post-event follow-ups that don't ask for anything
- Information sharing without a question or ask
- Read receipts or delivery confirmations

═══ ACTION — Needs a reply, decision, or RSVP ═══

- Reply in an existing conversation thread (genuine "Re:" with real context)
- Personal ask from someone in Justin's network (manuscript review, intro request, etc.)
- Meeting scheduling or rescheduling requests
- Board or committee business requiring input
- Event invitations that need an RSVP decision
- Business follow-ups from known partners or collaborators (Andela, Blackbaud, Camelback, etc.)
- Outreach from government (.gov), universities (.edu), or established nonprofits (.org with
  recognizable names) that appears genuine
- Co-founder messages (Karibu, Sally when about OC/Outdoorithm business)

IMPORTANT NUANCES:
- "Re:" from a known collaborator = action. "RE:" from a random sales domain = skip.
- Someone at a real company reaching out about a real opportunity = action.
  Someone at a SaaS tool reaching out to sell = skip.
- If unsure, lean toward action — false negatives (missing a real email) are worse than
  false positives (showing a sales email).

Return JSON with this exact structure:
{
  "classifications": [
    {"id": "msg_id", "category": "action|fyi|skip", "reason": "brief 5-10 word explanation"}
  ]
}`;

const VALID_CATEGORIES = new Set(['action', 'fyi', 'skip']);
const BATCH_SIZE = 40;

async function classifyBatch(
  openai: OpenAI,
  batch: EmailInput[]
): Promise<Classification[]> {
  const emailList = batch
    .map(
      (e, i) =>
        `[${i + 1}] id=${e.id} | from=${e.fromName} <${e.from}> | account=${e.account}\n    subject: ${e.subject}\n    snippet: ${e.snippet.slice(0, 200)}`
    )
    .join('\n\n');

  const response = await openai.chat.completions.create({
    model: 'gpt-5-mini',
    max_completion_tokens: 4000,
    response_format: { type: 'json_object' },
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      {
        role: 'user',
        content: `Classify these ${batch.length} emails:\n\n${emailList}`,
      },
    ],
  });

  const content = response.choices[0].message.content;
  if (!content) return [];

  let parsed: { classifications?: unknown };
  try {
    parsed = JSON.parse(content);
  } catch (e) {
    console.error(
      '[Email Triage Classify] Invalid JSON from GPT:',
      content.slice(0, 500)
    );
    return [];
  }

  if (!Array.isArray(parsed.classifications)) {
    console.error(
      '[Email Triage Classify] Missing classifications array, got keys:',
      Object.keys(parsed)
    );
    return [];
  }

  // Validate each classification
  const valid = parsed.classifications.filter(
    (c: any): c is Classification =>
      c &&
      typeof c.id === 'string' &&
      VALID_CATEGORIES.has(c.category) &&
      typeof c.reason === 'string'
  );

  if (valid.length < parsed.classifications.length) {
    console.warn(
      `[Email Triage Classify] ${parsed.classifications.length - valid.length} malformed entries dropped`
    );
  }

  return valid;
}

export async function POST(req: Request) {
  try {
    const { emails } = (await req.json()) as { emails: EmailInput[] };

    if (!emails || !Array.isArray(emails) || emails.length === 0) {
      return NextResponse.json(
        { error: 'emails array is required' },
        { status: 400 }
      );
    }

    const apiKey = process.env.OPENAI_APIKEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: 'OPENAI_APIKEY environment variable is not configured' },
        { status: 500 }
      );
    }
    const openai = new OpenAI({ apiKey });

    // Chunk into batches to avoid exceeding context/token limits
    const allClassifications: Classification[] = [];
    for (let i = 0; i < emails.length; i += BATCH_SIZE) {
      const batch = emails.slice(i, i + BATCH_SIZE);
      const results = await classifyBatch(openai, batch);
      allClassifications.push(...results);
    }

    return NextResponse.json({
      classifications: allClassifications,
    });
  } catch (error: unknown) {
    const message =
      error instanceof Error ? error.message : 'Classification failed';
    console.error('[Email Triage Classify] Error:', message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
