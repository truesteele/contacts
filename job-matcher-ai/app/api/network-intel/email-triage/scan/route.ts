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

// ── Gmail label → category mapping ──────────────────────────────────
// Maps existing Gmail labels to our triage categories.
// The Apps Script applies these labels; this route reads them.

const LABEL_TO_CATEGORY: Record<string, { category: EmailCategory; reason: string }> = {
  '!Action':        { category: 'action', reason: 'Labeled !Action' },
  '!Action/Urgent': { category: 'action', reason: 'Labeled !Action/Urgent' },
  '!FYI':           { category: 'fyi',    reason: 'Labeled !FYI' },
  '!Read-Review':   { category: 'fyi',    reason: 'Labeled !Read-Review' },
  '!Waiting-For':   { category: 'fyi',    reason: 'Labeled !Waiting-For' },
  '~Sales-Pitch':   { category: 'skip',   reason: 'Labeled ~Sales-Pitch' },
  '~Marketing':     { category: 'skip',   reason: 'Labeled ~Marketing' },
  '~Newsletters':   { category: 'skip',   reason: 'Labeled ~Newsletters' },
  '~Notifications': { category: 'skip',   reason: 'Labeled ~Notifications' },
  '~Calendar':      { category: 'skip',   reason: 'Labeled ~Calendar' },
  '~Receipts':      { category: 'skip',   reason: 'Labeled ~Receipts' },
  '~LinkedIn':      { category: 'skip',   reason: 'Labeled ~LinkedIn' },
  '~ErrorMonitor':  { category: 'skip',   reason: 'Labeled ~ErrorMonitor' },
  '~CRM':           { category: 'skip',   reason: 'Labeled ~CRM' },
};

// ── Rule-based pre-filtering ──────────────────────────────────────────

interface FilterRule {
  from?: RegExp;
  subject?: RegExp;
  category: 'skip' | 'fyi';
  reason: string;
}

const FILTER_RULES: FilterRule[] = [
  // ── SKIP: Error monitors ──
  { from: /notifications@vercel\.com/i, subject: /fail|error/i, category: 'skip', reason: 'Vercel error notification' },
  { from: /noreply@outdoorithm\.com/i, subject: /\[Error Report\]|\[INCIDENT\]/i, category: 'skip', reason: 'Outdoorithm error monitor' },
  { from: /@kindora\.co$/i, subject: /\[Error Report\]|\[Daily Digest\].*(?:error|issue)/i, category: 'skip', reason: 'Kindora error monitor' },
  { from: /alert@kindora\.co/i, subject: /stuck-task report/i, category: 'skip', reason: 'Kindora stuck-task alert' },

  // ── SKIP: LinkedIn ──
  { from: /@linkedin\.com$/i, category: 'skip', reason: 'LinkedIn notification' },

  // ── SKIP: Receipts ──
  { from: /receipts@mercury\.com/i, category: 'skip', reason: 'Mercury receipt' },
  { from: /billing@apify\.com/i, category: 'skip', reason: 'Apify billing' },
  { from: /hello@apify\.com/i, subject: /usage|invoice|billing/i, category: 'skip', reason: 'Apify usage notice' },
  { from: /noreply@order\.eventbrite\.com/i, category: 'skip', reason: 'Eventbrite order' },
  { from: /help@paddle\.com/i, subject: /receipt/i, category: 'skip', reason: 'Paddle receipt' },
  { from: /invoice.*@vercel\.com/i, category: 'skip', reason: 'Vercel invoice' },
  { from: /no-reply@toasttab\.com/i, subject: /receipt|order/i, category: 'skip', reason: 'Restaurant receipt' },

  // ── SKIP: Notifications ──
  { from: /^info@kindora\.co$/i, subject: /New User Signup/i, category: 'skip', reason: 'Kindora system notification' },
  { from: /notifications@vercel\.com/i, category: 'skip', reason: 'Vercel deploy notification' },
  { from: /noreply@tickets\./i, category: 'skip', reason: 'Ticket confirmation' },
  { from: /no-?reply@.*amazonses\.com/i, subject: /New User Signup/i, category: 'skip', reason: 'System notification via SES' },
  { from: /billing@.*openai\.com/i, category: 'skip', reason: 'OpenAI billing' },
  { from: /notification@slack\.com/i, category: 'skip', reason: 'Slack notification' },
  { from: /no-reply.*@slack\.com/i, category: 'skip', reason: 'Slack notification' },
  { from: /chat-noreply@google\.com/i, category: 'skip', reason: 'Google Chat notification' },
  { from: /workspace-noreply@google\.com/i, category: 'skip', reason: 'Google Workspace notification' },
  { from: /noreply@supabase\.com/i, category: 'skip', reason: 'Supabase notification' },
  { from: /sc-noreply@google\.com/i, category: 'skip', reason: 'Google Search Console' },
  { from: /noreply@collective\.com/i, category: 'skip', reason: 'Collective notification' },
  { from: /no-reply@email\.claude\.com/i, category: 'skip', reason: 'Claude notification' },
  { from: /noreply@mail\.cloud\.scansnap/i, category: 'skip', reason: 'ScanSnap notification' },
  { from: /no-reply@amazonaws\.com/i, category: 'skip', reason: 'AWS notification' },
  { from: /health@aws\.com/i, category: 'skip', reason: 'AWS health notification' },
  { from: /no-reply@otter\.ai/i, category: 'skip', reason: 'Otter.ai notification' },
  { from: /notifications@calendly\.com/i, category: 'skip', reason: 'Calendly notification' },
  { from: /hello@gofarmhand\.com/i, category: 'skip', reason: 'Farmhand notification' },
  { from: /support@zerobounce\.net/i, category: 'skip', reason: 'ZeroBounce notification' },
  { from: /hello@sanity\.io/i, category: 'skip', reason: 'Sanity.io notification' },
  { from: /noreply@blackbaud\.com/i, category: 'skip', reason: 'Blackbaud notification' },
  { from: /drive-shares-dm-noreply@google\.com/i, category: 'skip', reason: 'Google Drive share' },
  { from: /comments-noreply@docs\.google\.com/i, category: 'skip', reason: 'Google Docs comment' },

  // ── SKIP: Calendar ──
  { subject: /^Accepted:/i, category: 'skip', reason: 'Calendar acceptance' },
  { subject: /^Declined:/i, category: 'skip', reason: 'Calendar decline' },
  { subject: /^Tentative:/i, category: 'skip', reason: 'Calendar tentative' },
  { subject: /^Updated invitation:/i, category: 'skip', reason: 'Calendar update' },

  // ── SKIP: Newsletters ──
  { from: /@mail\.beehiiv\.com$/i, category: 'skip', reason: 'Newsletter platform' },
  { from: /convertkit-mail/i, category: 'skip', reason: 'Newsletter platform' },
  { from: /comms@ellabakercenter\.org/i, category: 'skip', reason: 'Ella Baker Center newsletter' },

  // ── SKIP: Marketing ──
  { from: /@partnernotification\.capitalone\.com/i, category: 'skip', reason: 'Capital One marketing' },
  { from: /mail@update\.strava\.com/i, category: 'skip', reason: 'Strava marketing' },
  { from: /jacksonfordc\.com/i, category: 'skip', reason: 'Political campaign email' },
  { from: /livefreeusa\.org/i, category: 'skip', reason: 'Organization mass email' },

  // ── SKIP: Cold sales (known domains) ──
  { from: /@(useclaritymail|oursprintops|joinforge|prpodpitch|upscalepulselab|boostbnxt|readingbrandlane)\./i, category: 'skip', reason: 'Known cold sales domain' },
  { from: /dataforseo\.com/i, category: 'skip', reason: 'DataForSEO vendor outreach' },
  { from: /trestleiq\.com/i, category: 'skip', reason: 'Trestle vendor outreach' },

  // ── SKIP: Generic receipts ──
  { from: /noreply@/i, subject: /Confirmed/i, category: 'skip', reason: 'Confirmation receipt' },

  // ── FYI rules ──
  { subject: /^Invitation:.*\d{4}/i, category: 'fyi', reason: 'Calendar invitation' },
  { from: /@bishopodowd\.org$/i, category: 'fyi', reason: 'School notification' },
  { from: /@oaklandmontessori\.com$/i, category: 'fyi', reason: 'School notification' },
  { from: /no-reply@.*mybrightwheel\.com/i, category: 'fyi', reason: 'School notification (Brightwheel)' },
  { from: /mailer@email\.naviance\.com/i, category: 'fyi', reason: 'School notification (Naviance)' },
  { from: /@leiya\.com$/i, category: 'fyi', reason: 'School notification (Leiya)' },
  { from: /^info@outdoorithm\.com$/i, subject: /available|campsite/i, category: 'fyi', reason: 'Campsite availability alert' },
  { from: /txt\.voice\.google\.com/i, category: 'fyi', reason: 'Google Voice text' },
];

function applyRuleFilters(msg: EmailMessage, labelNames: string[]): EmailMessage {
  // First check if Gmail labels already classify this message
  for (const labelName of labelNames) {
    const mapping = LABEL_TO_CATEGORY[labelName];
    if (mapping) {
      return { ...msg, category: mapping.category, categoryReason: mapping.reason };
    }
  }

  // Then apply regex-based rules
  for (const rule of FILTER_RULES) {
    const fromMatch = !rule.from || rule.from.test(msg.from.toLowerCase());
    const subjectMatch = !rule.subject || rule.subject.test(msg.subject.toLowerCase());

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
    const safeDays = Number.isFinite(newer_than_days)
      ? Math.min(Math.max(Math.floor(newer_than_days), 1), 90)
      : 21;

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
    // Also track label ID → name mappings per account for triage label recognition
    const labelMaps = new Map<string, Map<string, string>>();

    await Promise.all(
      services.map(async ({ account, client }) => {
        try {
          // Fetch label list to resolve IDs → names
          try {
            const labelsRes = await client.users.labels.list({ userId: 'me' });
            const idToName = new Map<string, string>();
            for (const label of labelsRes.data.labels || []) {
              if (label.id && label.name) {
                idToName.set(label.id, label.name);
              }
            }
            labelMaps.set(account, idToName);
          } catch (e) {
            console.warn(`[Email Triage Scan] Could not fetch labels for ${account}:`, e instanceof Error ? e.message : e);
          }

          const q = `is:unread newer_than:${safeDays}d -category:{promotions social updates forums}`;
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

                // Resolve label IDs to names
                const labelIds = msg.data.labelIds || [];
                const idToName = labelMaps.get(account);
                const labelNames = idToName
                  ? labelIds.map((id) => idToName.get(id) || id)
                  : labelIds;

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
                  labels: labelNames,
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

    // Apply rule-based filters (checks existing Gmail labels first, then regex rules)
    const classified = allMessages.map((msg) => applyRuleFilters(msg, msg.labels));

    // Sort by timestamp descending (newest first)
    classified.sort((a, b) => b.timestamp - a.timestamp);

    // Group messages into threads
    const threadMap = new Map<string, EmailMessage[]>();
    for (const msg of classified) {
      const key = msg.threadId || msg.id; // fall back to id if no threadId
      const existing = threadMap.get(key) || [];
      existing.push(msg);
      threadMap.set(key, existing);
    }

    const threads = Array.from(threadMap.entries()).map(([threadId, msgs]) => {
      // Sort messages within thread: oldest first
      msgs.sort((a, b) => a.timestamp - b.timestamp);
      const lastMessage = msgs[msgs.length - 1];
      // Thread category = highest priority among messages (action > fyi > unclassified > skip)
      const categoryPriority: Record<EmailCategory, number> = {
        action: 3,
        unclassified: 2,
        fyi: 1,
        skip: 0,
      };
      let threadCategory = lastMessage.category;
      let threadCategoryReason = lastMessage.categoryReason;
      for (const m of msgs) {
        if (categoryPriority[m.category] > categoryPriority[threadCategory]) {
          threadCategory = m.category;
          threadCategoryReason = m.categoryReason;
        }
      }

      return {
        threadId,
        subject: lastMessage.subject,
        account: lastMessage.account,
        lastMessage,
        messageCount: msgs.length,
        messages: msgs,
        category: threadCategory,
        categoryReason: threadCategoryReason,
        timestamp: lastMessage.timestamp,
      };
    });

    // Sort threads by most recent message
    threads.sort((a, b) => b.timestamp - a.timestamp);

    const ruleFiltered = classified.filter((m) => m.category !== 'unclassified').length;

    return NextResponse.json({
      threads,
      messages: classified, // keep flat list for backward compat with classify route
      total: classified.length,
      thread_count: threads.length,
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
