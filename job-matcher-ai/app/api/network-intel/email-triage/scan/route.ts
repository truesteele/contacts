import { NextResponse } from 'next/server';
import { getGmailClients } from '@/lib/gmail-client';

// Node.js runtime — needs fs for OAuth creds
export const runtime = 'nodejs';

interface EmailMessage {
  id: string;
  threadId: string;
  account: string;
  from: string;
  fromName: string;
  to: string;
  subject: string;
  snippet: string;
  date: string;
  timestamp: number;
  labels: string[];
}

function parseFromHeader(from: string): { name: string; email: string } {
  const match = from.match(/^(?:"?([^"<]*?)"?\s*)?<([^>]+)>$/);
  if (match) {
    return { name: (match[1] || '').trim(), email: (match[2] || '').trim() };
  }
  return { name: '', email: from.trim() };
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { newer_than_days = 21 } = body as { newer_than_days?: number };

    const services = getGmailClients();
    if (services.length === 0) {
      return NextResponse.json(
        { error: 'No Gmail accounts configured' },
        { status: 500 }
      );
    }

    const allMessages: EmailMessage[] = [];

    // Search all accounts in parallel
    await Promise.all(
      services.map(async ({ account, client }) => {
        try {
          const q = `is:unread newer_than:${newer_than_days}d -category:{promotions social updates forums}`;
          const res = await client.users.messages.list({
            userId: 'me',
            q,
            maxResults: 50,
          });

          const messageRefs = res.data.messages || [];
          if (messageRefs.length === 0) return;

          // Fetch metadata for each message
          const msgs = await Promise.all(
            messageRefs.map(async (ref) => {
              try {
                const msg = await client.users.messages.get({
                  userId: 'me',
                  id: ref.id!,
                  format: 'metadata',
                  metadataHeaders: ['From', 'To', 'Subject', 'Date'],
                });

                const headers = msg.data.payload?.headers || [];
                const getHeader = (name: string) =>
                  headers.find((h) => h.name?.toLowerCase() === name.toLowerCase())?.value || '';

                const fromRaw = getHeader('From');
                const { name: fromName, email: fromEmail } = parseFromHeader(fromRaw);

                return {
                  id: msg.data.id!,
                  threadId: msg.data.threadId!,
                  account,
                  from: fromEmail || fromRaw,
                  fromName: fromName || fromEmail || fromRaw,
                  to: getHeader('To'),
                  subject: getHeader('Subject') || '(no subject)',
                  snippet: msg.data.snippet || '',
                  date: getHeader('Date'),
                  timestamp: Number(msg.data.internalDate) || 0,
                  labels: msg.data.labelIds || [],
                } as EmailMessage;
              } catch {
                return null;
              }
            })
          );

          for (const m of msgs) {
            if (m) allMessages.push(m);
          }
        } catch (e) {
          console.error(`Error scanning ${account}:`, e);
        }
      })
    );

    // Sort by timestamp descending (newest first)
    allMessages.sort((a, b) => b.timestamp - a.timestamp);

    return NextResponse.json({
      messages: allMessages,
      total: allMessages.length,
      accounts_scanned: services.length,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to scan emails';
    console.error('[Email Triage Scan] Error:', message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
