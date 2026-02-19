import { NextResponse } from 'next/server';
import { Resend } from 'resend';
import { supabase } from '@/lib/supabase';

export const runtime = 'edge';

let _resend: Resend | null = null;
function getResend(): Resend {
  if (!_resend) {
    _resend = new Resend(process.env.RESEND_API_KEY);
  }
  return _resend;
}

const FROM_EMAIL = 'Justin Steele <justin@truesteele.com>';
const REPLY_TO = 'justinrsteele@gmail.com';

function textToHtml(body: string): string {
  const escaped = body
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  const paragraphs = escaped
    .split(/\n\n+/)
    .map((p) => `<p>${p.replace(/\n/g, '<br>')}</p>`)
    .join('');

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      font-family: Georgia, 'Times New Roman', serif;
      line-height: 1.7;
      color: #333;
      max-width: 600px;
      margin: 0 auto;
      padding: 20px;
      background-color: #ffffff;
    }
    p { margin: 1em 0; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .footer {
      margin-top: 3em;
      padding-top: 1em;
      border-top: 1px solid #eee;
      font-size: 0.8em;
      color: #999;
    }
  </style>
</head>
<body>
  ${paragraphs}
  <div class="footer">
    <p><a href="mailto:${REPLY_TO}?subject=unsubscribe" style="color: #999;">Unsubscribe</a> from future emails</p>
  </div>
</body>
</html>`;
}

interface SendResult {
  draft_id: string;
  contact_id: number;
  status: 'sent' | 'failed';
  resend_id?: string;
  error?: string;
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { draft_id, draft_ids, overrides } = body as {
      draft_id?: string;
      draft_ids?: string[];
      overrides?: Record<string, { subject?: string; body?: string }>;
    };

    // Normalize to array
    const ids: string[] = draft_ids?.length
      ? draft_ids
      : draft_id
        ? [draft_id]
        : [];

    if (ids.length === 0) {
      return NextResponse.json(
        { error: 'draft_id or draft_ids is required' },
        { status: 400 }
      );
    }

    // Fetch drafts
    const { data: drafts, error: fetchError } = await supabase
      .from('outreach_drafts')
      .select('id, contact_id, subject, body, status')
      .in('id', ids);

    if (fetchError) {
      return NextResponse.json(
        { error: `Failed to fetch drafts: ${fetchError.message}` },
        { status: 500 }
      );
    }

    if (!drafts || drafts.length === 0) {
      return NextResponse.json(
        { error: 'No drafts found for the provided IDs' },
        { status: 404 }
      );
    }

    // Fetch contact emails for all drafts
    const contactIds = [...new Set(drafts.map((d: any) => d.contact_id))];
    const { data: contacts, error: contactError } = await supabase
      .from('contacts')
      .select('id, first_name, last_name, email, personal_email, work_email')
      .in('id', contactIds);

    if (contactError) {
      return NextResponse.json(
        { error: `Failed to fetch contacts: ${contactError.message}` },
        { status: 500 }
      );
    }

    const contactMap = new Map<number, any>();
    for (const c of contacts || []) {
      contactMap.set(Number(c.id), c);
    }

    const results: SendResult[] = [];

    // Send each draft sequentially
    for (const draft of drafts) {
      const d = draft as any;

      // Skip already-sent drafts
      if (d.status === 'sent') {
        results.push({
          draft_id: d.id,
          contact_id: d.contact_id,
          status: 'failed',
          error: 'Draft already sent',
        });
        continue;
      }

      const contact = contactMap.get(Number(d.contact_id));
      if (!contact) {
        // Update draft status to failed
        await supabase
          .from('outreach_drafts')
          .update({ status: 'failed' })
          .eq('id', d.id);

        results.push({
          draft_id: d.id,
          contact_id: d.contact_id,
          status: 'failed',
          error: 'Contact not found',
        });
        continue;
      }

      const toEmail =
        contact.email || contact.personal_email || contact.work_email;
      if (!toEmail) {
        await supabase
          .from('outreach_drafts')
          .update({ status: 'failed' })
          .eq('id', d.id);

        results.push({
          draft_id: d.id,
          contact_id: d.contact_id,
          status: 'failed',
          error: 'Contact has no email address',
        });
        continue;
      }

      try {
        // Apply local edits if provided
        const draftOverride = overrides?.[d.id];
        const finalSubject = draftOverride?.subject ?? d.subject;
        const finalBody = draftOverride?.body ?? d.body;

        // Persist overrides to DB before sending
        if (draftOverride) {
          const updates: Record<string, string> = {};
          if (draftOverride.subject) updates.subject = draftOverride.subject;
          if (draftOverride.body) updates.body = draftOverride.body;
          if (Object.keys(updates).length > 0) {
            await supabase
              .from('outreach_drafts')
              .update(updates)
              .eq('id', d.id);
          }
        }

        const htmlBody = textToHtml(finalBody);

        const { data: sendData, error: sendError } = await getResend().emails.send({
          from: FROM_EMAIL,
          to: [toEmail],
          replyTo: REPLY_TO,
          subject: finalSubject,
          html: htmlBody,
          text: finalBody,
          headers: {
            'List-Unsubscribe': `<mailto:${REPLY_TO}?subject=unsubscribe>`,
          },
        });

        if (sendError) {
          await supabase
            .from('outreach_drafts')
            .update({ status: 'failed' })
            .eq('id', d.id);

          results.push({
            draft_id: d.id,
            contact_id: d.contact_id,
            status: 'failed',
            error: sendError.message,
          });
          continue;
        }

        // Update draft as sent
        await supabase
          .from('outreach_drafts')
          .update({
            status: 'sent',
            sent_at: new Date().toISOString(),
          })
          .eq('id', d.id);

        results.push({
          draft_id: d.id,
          contact_id: d.contact_id,
          status: 'sent',
          resend_id: sendData?.id,
        });
      } catch (err: any) {
        await supabase
          .from('outreach_drafts')
          .update({ status: 'failed' })
          .eq('id', d.id);

        results.push({
          draft_id: d.id,
          contact_id: d.contact_id,
          status: 'failed',
          error: err.message || 'Send failed',
        });
      }
    }

    const sent = results.filter((r) => r.status === 'sent').length;
    const failed = results.filter((r) => r.status === 'failed').length;

    return NextResponse.json({
      results,
      total_sent: sent,
      total_failed: failed,
    });
  } catch (error: any) {
    console.error('[Outreach Send] Error:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to send emails' },
      { status: 500 }
    );
  }
}
