import { NextResponse } from 'next/server';
import { getGmailClients } from '@/lib/gmail-client';

// Node.js runtime — needs fs for OAuth creds
export const runtime = 'nodejs';
export const maxDuration = 60;

export type EmailCategory = 'action' | 'fyi' | 'skip' | 'unclassified';

export interface EmailMessage {
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
  category: EmailCategory;
  categoryReason: string;
}

function parseFromHeader(from: string): { name: string; email: string } {
  const match = from.match(/^(?:"?([^"<]*?)"?\s*)?<([^>]+)>$/);
  if (match) {
    return { name: (match[1] || '').trim(), email: (match[2] || '').trim() };
  }
  return { name: '', email: from.trim() };
}

// ── Rule-based pre-filtering ──────────────────────────────────────────

interface FilterRule {
  from?: RegExp;
  subject?: RegExp;
  category: 'skip' | 'fyi';
  reason: string;
}

const FILTER_RULES: FilterRule[] = [
  // ── SKIP rules ──
  {
    from: /^info@kindora\.co$/i,
    subject: /New User Signup/i,
    category: 'skip',
    reason: 'Kindora system notification',
  },
  {
    from: /notifications@vercel\.com/i,
    category: 'skip',
    reason: 'Vercel deploy notification',
  },
  {
    subject: /^Accepted:/i,
    category: 'skip',
    reason: 'Calendar acceptance',
  },
  {
    from: /billing@.*openai\.com/i,
    category: 'skip',
    reason: 'Billing notification',
  },
  {
    from: /noreply@tickets\./i,
    category: 'skip',
    reason: 'Ticket confirmation',
  },
  {
    from: /no-?reply@.*amazonses\.com/i,
    subject: /New User Signup/i,
    category: 'skip',
    reason: 'System notification via SES',
  },

  // ── FYI rules ──
  {
    // Google Calendar invitations (contain date/time patterns)
    subject: /^Invitation:.*\d{4}/i,
    category: 'fyi',
    reason: 'Calendar invitation',
  },
  {
    from: /@bishopodowd\.org$/i,
    category: 'fyi',
    reason: 'School notification',
  },
  {
    from: /@oaklandmontessori\.com$/i,
    category: 'fyi',
    reason: 'School notification',
  },
  {
    from: /^info@outdoorithm\.com$/i,
    subject: /available again/i,
    category: 'fyi',
    reason: 'Campsite availability alert',
  },
  {
    from: /noreply@/i,
    subject: /Confirmed/i,
    category: 'fyi',
    reason: 'Confirmation receipt',
  },
];

function applyRuleFilters(msg: EmailMessage): EmailMessage {
  const fromLower = msg.from.toLowerCase();
  const subjectLower = msg.subject.toLowerCase();

  for (const rule of FILTER_RULES) {
    const fromMatch = !rule.from || rule.from.test(fromLower);
    const subjectMatch = !rule.subject || rule.subject.test(subjectLower);

    if (fromMatch && subjectMatch) {
      return { ...msg, category: rule.category, categoryReason: rule.reason };
    }
  }

  return msg; // stays 'unclassified'
}

// ── Route handler ─────────────────────────────────────────────────────

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
    const accountErrors: Array<{ account: string; error: string }> = [];
    let fetchFailures = 0;

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
              if (!ref.id) return null;
              try {
                const msg = await client.users.messages.get({
                  userId: 'me',
                  id: ref.id,
                  format: 'metadata',
                  metadataHeaders: ['From', 'To', 'Subject', 'Date'],
                });

                const headers = msg.data.payload?.headers || [];
                const getHeader = (name: string) =>
                  headers.find((h) => h.name?.toLowerCase() === name.toLowerCase())?.value || '';

                const fromRaw = getHeader('From');
                const { name: fromName, email: fromEmail } = parseFromHeader(fromRaw);

                return {
                  id: msg.data.id || ref.id,
                  threadId: msg.data.threadId || '',
                  account,
                  from: fromEmail || fromRaw,
                  fromName: fromName || fromEmail || fromRaw,
                  to: getHeader('To'),
                  subject: getHeader('Subject') || '(no subject)',
                  snippet: msg.data.snippet || '',
                  date: getHeader('Date'),
                  timestamp: Number(msg.data.internalDate) || 0,
                  labels: msg.data.labelIds || [],
                  category: 'unclassified' as EmailCategory,
                  categoryReason: '',
                } as EmailMessage;
              } catch (e) {
                fetchFailures++;
                console.error(
                  `[Email Triage Scan] Failed to fetch message ${ref.id} for ${account}:`,
                  e instanceof Error ? e.message : e
                );
                return null;
              }
            })
          );

          for (const m of msgs) {
            if (m) allMessages.push(m);
          }
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          console.error(`[Email Triage Scan] Error scanning ${account}:`, msg);
          accountErrors.push({ account, error: msg });
        }
      })
    );

    // Apply rule-based filters
    const classified = allMessages.map(applyRuleFilters);

    // Sort by timestamp descending (newest first)
    classified.sort((a, b) => b.timestamp - a.timestamp);

    const ruleFiltered = classified.filter((m) => m.category !== 'unclassified').length;

    return NextResponse.json({
      messages: classified,
      total: classified.length,
      rule_filtered: ruleFiltered,
      accounts_scanned: services.length,
      accounts_failed: accountErrors,
      fetch_failures: fetchFailures,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to scan emails';
    console.error('[Email Triage Scan] Error:', message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
