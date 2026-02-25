import { NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';
import { getGmailClient } from '@/lib/gmail-client';

export const runtime = 'nodejs';
export const maxDuration = 60;

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
});

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

function extractTextFromParts(parts: any[]): string {
  let text = '';
  for (const part of parts) {
    if (part.mimeType === 'text/plain' && part.body?.data) {
      text += decodeBase64Url(part.body.data);
    } else if (part.parts) {
      text += extractTextFromParts(part.parts);
    }
  }
  return text;
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

  let body = '';
  if (msg.data.payload?.body?.data) {
    body = decodeBase64Url(msg.data.payload.body.data);
  } else if (msg.data.payload?.parts) {
    body = extractTextFromParts(msg.data.payload.parts);
  }

  return {
    from: getHeader('From'),
    to: getHeader('To'),
    subject: getHeader('Subject'),
    date: getHeader('Date'),
    body: body.slice(0, 8000), // Cap to avoid token bloat
  };
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { message_id, account, thread_context } = body as {
      message_id: string;
      account: string;
      thread_context?: string;
    };

    if (!message_id || !account) {
      return NextResponse.json(
        { error: 'message_id and account are required' },
        { status: 400 }
      );
    }

    // Fetch the full message if no thread context provided
    let emailContext = thread_context;
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

    const userPrompt = `Here is the email thread I need to reply to:\n\n---\n${emailContext}\n---\n\nWrite a reply as Justin. Keep it concise and natural. Match the tone of the conversation.`;

    const response = await anthropic.messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 1024,
      temperature: 0.8,
      system: STYLE_SYSTEM_PROMPT,
      messages: [{ role: 'user', content: userPrompt }],
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
