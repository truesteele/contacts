import { NextResponse } from 'next/server';
import { getGmailClient } from '@/lib/gmail-client';

export const runtime = 'nodejs';

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

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { message_id, account } = body as {
      message_id: string;
      account: string;
    };

    if (!message_id || !account) {
      return NextResponse.json(
        { error: 'message_id and account are required' },
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

    const msg = await client.users.messages.get({
      userId: 'me',
      id: message_id,
      format: 'full',
    });

    const headers = msg.data.payload?.headers || [];
    const getHeader = (name: string) =>
      headers.find((h) => h.name?.toLowerCase() === name.toLowerCase())?.value || '';

    let textBody = '';
    if (msg.data.payload?.body?.data) {
      textBody = decodeBase64Url(msg.data.payload.body.data);
    } else if (msg.data.payload?.parts) {
      textBody = extractTextFromParts(msg.data.payload.parts);
    }

    return NextResponse.json({
      id: msg.data.id,
      threadId: msg.data.threadId,
      from: getHeader('From'),
      to: getHeader('To'),
      cc: getHeader('Cc'),
      subject: getHeader('Subject'),
      date: getHeader('Date'),
      body: textBody,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch message';
    console.error('[Email Triage Message] Error:', message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
