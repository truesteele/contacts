import { NextResponse } from 'next/server';
import { getGmailClient } from '@/lib/gmail-client';

export const runtime = 'nodejs';

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

function parseMessage(msg: any): {
  id: string;
  threadId: string;
  from: string;
  fromName: string;
  fromEmail: string;
  to: string;
  cc: string;
  subject: string;
  date: string;
  timestamp: number;
  body: string;
} {
  const headers = msg.payload?.headers || [];
  const getHeader = (name: string) =>
    headers.find((h: any) => h.name?.toLowerCase() === name.toLowerCase())?.value || '';

  const body = getBodyText(msg.payload);

  const fromRaw = getHeader('From');
  const fromMatch = fromRaw.match(/^(?:"?([^"<]*?)"?\s*)?<([^>]+)>$/);
  const fromName = fromMatch ? (fromMatch[1] || '').trim() : '';
  const fromEmail = fromMatch ? (fromMatch[2] || '').trim() : fromRaw.trim();

  return {
    id: msg.id || '',
    threadId: msg.threadId || '',
    from: fromRaw,
    fromName: fromName || fromEmail || fromRaw,
    fromEmail: fromEmail || fromRaw,
    to: getHeader('To'),
    cc: getHeader('Cc'),
    subject: getHeader('Subject') || '(no subject)',
    date: getHeader('Date'),
    timestamp: Number(msg.internalDate) || 0,
    body: body.slice(0, 12000), // Cap to avoid token bloat
  };
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { thread_id, message_id, account } = body as {
      thread_id?: string;
      message_id?: string;
      account: string;
    };

    if (!account || (!thread_id && !message_id)) {
      return NextResponse.json(
        { error: 'account and either thread_id or message_id are required' },
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

    // Thread fetch mode: return all messages in the thread
    if (thread_id) {
      const thread = await client.users.threads.get({
        userId: 'me',
        id: thread_id,
        format: 'full',
      });

      const messages = (thread.data.messages || []).map(parseMessage);
      // Sort oldest first (conversation order)
      messages.sort((a, b) => a.timestamp - b.timestamp);

      // Collect all unique participants
      const participants = new Set<string>();
      for (const m of messages) {
        if (m.fromEmail) participants.add(m.fromEmail);
      }

      return NextResponse.json({
        threadId: thread_id,
        subject: messages[0]?.subject || '(no subject)',
        messages,
        participants: Array.from(participants),
        messageCount: messages.length,
      });
    }

    // Single message mode (backward compat)
    const msg = await client.users.messages.get({
      userId: 'me',
      id: message_id!,
      format: 'full',
    });

    const parsed = parseMessage(msg.data);
    return NextResponse.json(parsed);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch message';
    console.error('[Email Triage Message] Error:', message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
