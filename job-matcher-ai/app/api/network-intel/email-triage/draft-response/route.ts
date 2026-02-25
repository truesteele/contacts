import { NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';
import { getGmailClient } from '@/lib/gmail-client';

export const runtime = 'nodejs';
export const maxDuration = 60;

let anthropicClient: Anthropic | null = null;

function getAnthropicClient(): Anthropic {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error('ANTHROPIC_API_KEY environment variable is not configured');
  }
  if (!anthropicClient) {
    anthropicClient = new Anthropic({ apiKey });
  }
  return anthropicClient;
}

const STYLE_SYSTEM_PROMPT = `You are drafting an email reply as Justin Steele. You must write EXACTLY like Justin — not like an AI assistant.

ABOUT JUSTIN:
- CEO of Kindora (ed-tech / impact platform)
- Co-founded Outdoorithm and Outdoorithm Collective (outdoor equity nonprofit)
- Board member: San Francisco Foundation, Outdoorithm Collective
- Former: Google.org Director Americas (10 years), Year Up, Bridgespan Group, Bain & Company
- Schools: Harvard Business School, Harvard Kennedy School, University of Virginia
- Family: wife Sally, two daughters, lives in Oakland

JUSTIN'S WRITING VOICE:
- Builder's authenticity: writes from actively building, not theorizing
- Vulnerable authority: shares failures and uncertainties alongside achievements
- Direct, specific, occasionally poetic
- Uses contractions naturally (I'm, we're, don't, can't)
- Occasional fragments for emphasis. Like this.
- Varies sentence length — short punches mixed with longer thoughts
- Em dashes for parenthetical insights — but don't overdo them
- Specific numbers, names, places over abstractions
- Ends with genuine questions or specific calls to action, not platitudes

ANTI-AI RULES (CRITICAL — violating these makes the email sound fake):
- NO generic significance padding ("It's important to note...", "this underscores...", "testament to...")
- NO stacked negative-parallel structures ("not X but Y" repeated)
- NO symmetric triads or listicles unless truly necessary
- NO present-participle pileups at sentence ends ("...fostering..., enabling..., enhancing...")
- NO inflated verbs: don't use "navigate", "leverage", "craft", "delve", "utilize", "facilitate"
  Use simple verbs: "is", "has", "does", "works", "runs", "built", "started"
- NO false comfort closings ("I hope this helps!", "Don't hesitate to reach out!")
- NO corporate jargon ("synergy", "stakeholder alignment", "value proposition")
- NO AI hedging ("I think", "I believe", "In my opinion") — just state it
- Leave 1-2 small imperfections if they feel authentic
- Keep it SHORT. Most email replies should be 2-6 sentences. Don't over-explain.

FORMAT:
- Write ONLY the reply body text. No "Subject:" prefix, no signature block.
- The reply will be sent as Justin — don't add "Best," or "Thanks," closings unless the context warrants it.
- Match the formality level of the incoming email.
- If the email is casual, be casual. If formal, be slightly more formal (but still human).`;

function decodeBase64Url(data: string): string {
  const base64 = data.replace(/-/g, '+').replace(/_/g, '/');
  return Buffer.from(base64, 'base64').toString('utf-8');
}

function stripHtml(html: string): string {
  return html
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div|li|tr|h[1-6])>/gi, '\n')
    .replace(/<\/td>/gi, '\t')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/\r\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function collectTextFromParts(parts: any[]): { plain: string; html: string } {
  let plain = '';
  let html = '';

  for (const part of parts) {
    if (part.mimeType === 'text/plain' && part.body?.data) {
      plain += decodeBase64Url(part.body.data);
      continue;
    }
    if (part.mimeType === 'text/html' && part.body?.data) {
      html += decodeBase64Url(part.body.data);
      continue;
    }
    if (part.parts) {
      const nested = collectTextFromParts(part.parts);
      plain += nested.plain;
      html += nested.html;
    }
  }

  return { plain, html };
}

function extractTextFromParts(parts: any[]): string {
  const { plain, html } = collectTextFromParts(parts);
  if (plain.trim()) return plain;
  if (html.trim()) return stripHtml(html);
  return '';
}

function getBodyText(payload: any): string {
  if (!payload) return '';
  if (payload.body?.data) {
    const decoded = decodeBase64Url(payload.body.data);
    return payload.mimeType === 'text/html' ? stripHtml(decoded) : decoded;
  }
  if (payload.parts) {
    return extractTextFromParts(payload.parts);
  }
  return '';
}

async function fetchFullMessage(
  account: string,
  messageId: string
): Promise<{ from: string; to: string; subject: string; date: string; body: string } | null> {
  const client = getGmailClient(account);
  if (!client) return null;

  const msg = await client.users.messages.get({
    userId: 'me',
    id: messageId,
    format: 'full',
  });

  const headers = msg.data.payload?.headers || [];
  const getHeader = (name: string) =>
    headers.find((h) => h.name?.toLowerCase() === name.toLowerCase())?.value || '';

  const body = getBodyText(msg.data.payload);

  return {
    from: getHeader('From'),
    to: getHeader('To'),
    subject: getHeader('Subject'),
    date: getHeader('Date'),
    body: body.slice(0, 8000), // Cap to avoid token bloat
  };
}

interface ContactContext {
  first_name: string;
  last_name: string;
  company?: string | null;
  position?: string | null;
  headline?: string | null;
  city?: string | null;
  state?: string | null;
  familiarity_rating?: number | null;
  comms_closeness?: string | null;
  comms_momentum?: string | null;
  comms_last_date?: string | null;
  comms_thread_count?: number | null;
  comms_relationship_summary?: string | null;
  ai_proximity_tier?: string | null;
  ai_capacity_tier?: string | null;
  ask_readiness_tier?: string | null;
  ask_readiness_personalization?: string | null;
  shared_institutions?: Array<{
    name: string;
    type: string;
    temporal_overlap?: boolean;
    justin_period?: string;
    contact_period?: string;
  }>;
  personalization_hooks?: string[];
  suggested_opener?: string;
  talking_points?: string[];
  topics?: string[];
  best_approach?: string;
}

function buildContactContextBlock(contact: ContactContext): string {
  const familiarityLabels: Record<number, string> = {
    0: "Don't know",
    1: 'Recognize name',
    2: 'Know them',
    3: 'Good relationship',
    4: 'Close/trusted',
  };

  const parts: string[] = [
    `ABOUT THE SENDER (from Justin's contacts database):`,
    `Name: ${contact.first_name} ${contact.last_name}`,
  ];

  if (contact.company) parts.push(`Company: ${contact.company}`);
  if (contact.position) parts.push(`Position: ${contact.position}`);
  if (contact.headline) parts.push(`Headline: ${contact.headline}`);
  const location = [contact.city, contact.state].filter(Boolean).join(', ');
  if (location) parts.push(`Location: ${location}`);

  if (contact.familiarity_rating != null) {
    parts.push(`Familiarity: ${contact.familiarity_rating}/4 (${familiarityLabels[contact.familiarity_rating] || 'Unknown'})`);
  }
  if (contact.comms_closeness) parts.push(`Relationship closeness: ${contact.comms_closeness.replace(/_/g, ' ')}`);
  if (contact.comms_momentum) parts.push(`Communication momentum: ${contact.comms_momentum}`);
  if (contact.comms_last_date) parts.push(`Last email: ${contact.comms_last_date}`);
  if (contact.comms_thread_count && contact.comms_thread_count > 0) {
    parts.push(`Total email threads: ${contact.comms_thread_count}`);
  }
  if (contact.comms_relationship_summary) {
    parts.push(`Relationship summary: ${contact.comms_relationship_summary}`);
  }

  // Institutional overlap
  if (contact.shared_institutions && contact.shared_institutions.length > 0) {
    const lines = contact.shared_institutions.map((inst) => {
      const temporal = inst.temporal_overlap ? '(overlapping periods)' : '(different periods)';
      return `  - ${inst.name} [${inst.type}] ${temporal}${inst.justin_period ? `: Justin ${inst.justin_period}, Contact ${inst.contact_period}` : ''}`;
    });
    parts.push(`Shared institutions with Justin:\n${lines.join('\n')}`);
  }

  // Ask-readiness
  if (contact.ask_readiness_tier) {
    parts.push(`Ask-readiness: ${contact.ask_readiness_tier.replace(/_/g, ' ')}`);
    if (contact.ask_readiness_personalization) {
      parts.push(`Personalization angle: ${contact.ask_readiness_personalization}`);
    }
  }

  // Outreach intelligence
  if (contact.personalization_hooks && contact.personalization_hooks.length > 0) {
    parts.push(`Personalization hooks: ${contact.personalization_hooks.join('; ')}`);
  }
  if (contact.topics && contact.topics.length > 0) {
    parts.push(`Topics of interest: ${contact.topics.join(', ')}`);
  }
  if (contact.talking_points && contact.talking_points.length > 0) {
    parts.push(`Talking points: ${contact.talking_points.join('; ')}`);
  }
  if (contact.best_approach) {
    parts.push(`Best approach: ${contact.best_approach}`);
  }

  return parts.join('\n');
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { message_id, account, thread_context, contact_context } = body as {
      message_id: string;
      account: string;
      thread_context?: string;
      contact_context?: ContactContext;
    };

    if (!message_id || !account) {
      return NextResponse.json(
        { error: 'message_id and account are required' },
        { status: 400 }
      );
    }

    // Fetch the full message if no thread context provided
    let emailContext = thread_context;
    const maxContextChars = 20000;
    if (emailContext && emailContext.length > maxContextChars) {
      emailContext = emailContext.slice(-maxContextChars);
    }
    if (!emailContext) {
      const fullMsg = await fetchFullMessage(account, message_id);
      if (!fullMsg) {
        return NextResponse.json(
          { error: 'Could not fetch message content' },
          { status: 404 }
        );
      }
      emailContext = `From: ${fullMsg.from}\nTo: ${fullMsg.to}\nDate: ${fullMsg.date}\nSubject: ${fullMsg.subject}\n\n${fullMsg.body}`;
    }

    // Build the user prompt with optional contact context
    const promptParts: string[] = [];

    if (contact_context) {
      promptParts.push(buildContactContextBlock(contact_context));
      promptParts.push('');
    }

    promptParts.push(`Here is the email thread I need to reply to:\n\n---\n${emailContext}\n---`);
    promptParts.push('');

    if (contact_context) {
      promptParts.push(
        'Write a reply as Justin. Use the relationship context above to personalize the response — ' +
        'reference shared history, institutions, or recent interactions where natural. ' +
        'Keep it concise and match the tone of the conversation.'
      );
    } else {
      promptParts.push('Write a reply as Justin. Keep it concise and natural. Match the tone of the conversation.');
    }

    const anthropic = getAnthropicClient();
    const response = await anthropic.messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 1024,
      temperature: 0.8,
      system: STYLE_SYSTEM_PROMPT,
      messages: [{ role: 'user', content: promptParts.join('\n') }],
    });

    const textBlock = response.content.find(
      (block): block is Anthropic.TextBlock => block.type === 'text'
    );

    if (!textBlock) {
      return NextResponse.json(
        { error: 'Failed to generate draft' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      draft_body: textBlock.text,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to generate draft';
    console.error('[Email Triage Draft] Error:', message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
