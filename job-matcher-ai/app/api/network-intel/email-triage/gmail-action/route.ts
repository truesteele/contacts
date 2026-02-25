import { NextResponse } from 'next/server';
import { getGmailClient } from '@/lib/gmail-client';

export const runtime = 'nodejs';

function buildRfc2822Message(opts: {
  from: string;
  to: string;
  subject: string;
  body: string;
  inReplyTo?: string;
  references?: string;
  threadId?: string;
}): string {
  const lines: string[] = [];
  lines.push(`From: ${opts.from}`);
  lines.push(`To: ${opts.to}`);
  lines.push(`Subject: ${opts.subject}`);
  lines.push('Content-Type: text/plain; charset=utf-8');
  lines.push('MIME-Version: 1.0');
  if (opts.inReplyTo) {
    lines.push(`In-Reply-To: ${opts.inReplyTo}`);
  }
  if (opts.references) {
    lines.push(`References: ${opts.references}`);
  }
  lines.push('');
  lines.push(opts.body);
  return lines.join('\r\n');
}

function encodeBase64Url(str: string): string {
  return Buffer.from(str, 'utf-8')
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

function sanitizeHeaderValue(value: string): string {
  return value.replace(/[\r\n]+/g, ' ').trim();
}

// Map account to the from address Justin uses
const FROM_ADDRESSES: Record<string, string> = {
  'justinrsteele@gmail.com': 'Justin Steele <justinrsteele@gmail.com>',
  'justin@truesteele.com': 'Justin Steele <justin@truesteele.com>',
  'justin@outdoorithm.com': 'Justin Steele <justin@outdoorithm.com>',
  'justin@outdoorithmcollective.org': 'Justin Steele <justin@outdoorithmcollective.org>',
  'justin@kindora.co': 'Justin Steele <justin@kindora.co>',
};

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const {
      action,
      account,
      thread_id,
      message_id,
      subject,
      body: replyBody,
      to,
    } = body as {
      action: 'draft' | 'send';
      account: string;
      thread_id?: string;
      message_id?: string;
      subject: string;
      body: string;
      to: string;
    };

    if (!action || !account || !subject || !replyBody || !to) {
      return NextResponse.json(
        { error: 'action, account, subject, body, and to are required' },
        { status: 400 }
      );
    }

    if (action !== 'draft' && action !== 'send') {
      return NextResponse.json(
        { error: 'action must be "draft" or "send"' },
        { status: 400 }
      );
    }

    const client = getGmailClient(account);
    if (!client) {
      return NextResponse.json(
        { error: `No credentials for account: ${account}` },
        { status: 500 }
      );
    }

    const sanitizedTo = sanitizeHeaderValue(to);
    const sanitizedSubject = sanitizeHeaderValue(subject);
    if (!sanitizedTo || !sanitizedSubject) {
      return NextResponse.json(
        { error: 'to and subject must not contain only whitespace' },
        { status: 400 }
      );
    }

    // If replying, fetch the original message's Message-ID for threading
    let inReplyTo: string | undefined;
    let references: string | undefined;
    if (message_id) {
      try {
        const original = await client.users.messages.get({
          userId: 'me',
          id: message_id,
          format: 'metadata',
          metadataHeaders: ['Message-ID', 'References'],
        });
        const headers = original.data.payload?.headers || [];
        const origMsgId = headers.find(
          (h) => h.name?.toLowerCase() === 'message-id'
        )?.value;
        const origRefs = headers.find(
          (h) => h.name?.toLowerCase() === 'references'
        )?.value;

        if (origMsgId) {
          inReplyTo = origMsgId;
          references = origRefs ? `${origRefs} ${origMsgId}` : origMsgId;
        }
      } catch (e) {
        console.error(
          `[Email Triage Gmail Action] Failed to fetch threading headers for ${message_id}:`,
          e instanceof Error ? e.message : e
        );
      }
    }

    const fromAddress = sanitizeHeaderValue(FROM_ADDRESSES[account] || account);
    const raw = buildRfc2822Message({
      from: fromAddress,
      to: sanitizedTo,
      subject: sanitizedSubject,
      body: replyBody,
      inReplyTo,
      references,
    });

    const encodedRaw = encodeBase64Url(raw);

    if (action === 'draft') {
      const res = await client.users.drafts.create({
        userId: 'me',
        requestBody: {
          message: {
            raw: encodedRaw,
            threadId: thread_id || undefined,
          },
        },
      });

      return NextResponse.json({
        success: true,
        action: 'draft',
        gmail_id: res.data.id,
        message: 'Draft saved to Gmail',
      });
    } else {
      // Send
      const res = await client.users.messages.send({
        userId: 'me',
        requestBody: {
          raw: encodedRaw,
          threadId: thread_id || undefined,
        },
      });

      return NextResponse.json({
        success: true,
        action: 'send',
        gmail_id: res.data.id,
        message: 'Email sent',
      });
    }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Gmail action failed';
    console.error('[Email Triage Gmail Action] Error:', message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
