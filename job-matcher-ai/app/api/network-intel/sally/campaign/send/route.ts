import { supabase } from '@/lib/supabase';

export const runtime = 'edge';

const FROM_EMAIL = 'Sally Steele <sally@outdoorithmcollective.org>';
const REPLY_TO = 'sally.steele@gmail.com';

type SendMethod = 'resend' | 'gmail_draft';

interface ResendEmailResponse {
  id?: string;
  error?: { message?: string };
  message?: string;
}

async function sendWithResend(params: {
  toEmail: string;
  subject: string;
  htmlBody: string;
  textBody: string;
}): Promise<{ id: string | null }> {
  const apiKey = process.env.RESEND_API_KEY_OC;
  if (!apiKey) {
    throw new Error('RESEND_API_KEY_OC is not configured');
  }

  const response = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: FROM_EMAIL,
      to: [params.toEmail],
      reply_to: REPLY_TO,
      subject: params.subject,
      html: params.htmlBody,
      text: params.textBody,
      headers: {
        'List-Unsubscribe': `<mailto:${REPLY_TO}?subject=unsubscribe>`,
      },
    }),
  });

  const payload = (await response.json().catch(() => ({}))) as ResendEmailResponse;
  if (!response.ok) {
    throw new Error(
      payload.error?.message ||
        payload.message ||
        `Resend request failed (${response.status})`
    );
  }

  return { id: payload.id ?? null };
}

// ── Gmail Draft ─────────────────────────────────────────────────────────

async function getGmailAccessToken(): Promise<string> {
  // Sally's Gmail credentials (env vars prefixed with SALLY_)
  const clientId = process.env.SALLY_GMAIL_CLIENT_ID || process.env.GMAIL_CLIENT_ID;
  const clientSecret = process.env.SALLY_GMAIL_CLIENT_SECRET || process.env.GMAIL_CLIENT_SECRET;
  const refreshToken = process.env.SALLY_GMAIL_REFRESH_TOKEN || process.env.GMAIL_REFRESH_TOKEN;
  if (!clientId || !clientSecret || !refreshToken) {
    throw new Error('Sally Gmail OAuth credentials not configured (SALLY_GMAIL_CLIENT_ID, SALLY_GMAIL_CLIENT_SECRET, SALLY_GMAIL_REFRESH_TOKEN)');
  }

  const response = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
      client_id: clientId,
      client_secret: clientSecret,
    }),
  });

  const data = await response.json() as { access_token?: string; error?: string };
  if (!response.ok || !data.access_token) {
    throw new Error(`Gmail token refresh failed: ${data.error || response.status}`);
  }
  return data.access_token;
}

function buildRfc2822Message(params: {
  toEmail: string;
  subject: string;
  textBody: string;
}): string {
  const lines = [
    `To: ${params.toEmail}`,
    `Subject: ${params.subject}`,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    '',
    params.textBody,
  ];
  return lines.join('\r\n');
}

function base64UrlEncode(str: string): string {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(str);
  let binary = '';
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function createGmailDraft(params: {
  toEmail: string;
  subject: string;
  htmlBody: string;
  textBody: string;
}): Promise<{ id: string | null }> {
  const accessToken = await getGmailAccessToken();
  const raw = base64UrlEncode(buildRfc2822Message(params));

  const response = await fetch('https://gmail.googleapis.com/gmail/v1/users/me/drafts', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message: { raw } }),
  });

  const data = await response.json() as { id?: string; error?: { message?: string } };
  if (!response.ok) {
    throw new Error(`Gmail draft failed: ${data.error?.message || response.status}`);
  }
  return { id: data.id ?? null };
}

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

function resolveEmail(contact: {
  email?: string | null;
  email_2?: string | null;
}): string | null {
  return contact.email || contact.email_2 || null;
}

// Email 1 template — Sally's version
function buildEmail1Body(
  firstName: string,
  openerInsert: string | null,
  personalizationSentence: string | null
): string {
  const opener = openerInsert
    ? `${firstName},\n\n${openerInsert}\n\n`
    : `${firstName},\n\n`;

  const personalization = personalizationSentence
    ? `${personalizationSentence}\n\n`
    : '';

  return `${opener}${personalization}Last fall, a mom from Alabama came on one of our camping trips. First time sleeping outdoors. She grew up afraid of the woods. Couldn't sleep without a locked door.

That night she fell asleep to the sound of the ocean. Called it the most restorative sleep she'd had in years. Her daughter spent the weekend running barefoot through camp. No fear. Just joy.

This keeps happening. Families show up cautious and leave different. Real rest. Real food cooked together. Kids free. Strangers becoming family around a fire in 48 hours.

Justin and I have 8 trips planned this season through Outdoorithm Collective. Joshua Tree, Pinnacles, Yosemite, Lassen, and more. Each one brings 10-12 families into nature. Each costs about $10K to run. Plus $40K in gear so every family shows up equipped.

$120K for the full season. We've raised $45K from grants and early supporters. A friend is matching the first $20K in donations dollar-for-dollar. $75K to go.

$1,000 puts a family at the campfire. $2,500 covers a quarter of a trip. $5,000 sponsors half.

If you want in: outdoorithmcollective.org/donate

Or just reply. Happy to share more.

Sally`;
}

interface SendResult {
  contact_id: number;
  contact_name: string;
  status: 'sent' | 'drafted' | 'failed' | 'skipped';
  resend_id?: string;
  gmail_draft_id?: string;
  method?: SendMethod;
  error?: string;
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { contact_ids, email_type, send_method } = body as {
      contact_ids?: number[];
      email_type?: string;
      send_method?: SendMethod;
    };
    const method: SendMethod = send_method === 'gmail_draft' ? 'gmail_draft' : 'resend';

    if (!contact_ids || contact_ids.length === 0) {
      return Response.json(
        { error: 'contact_ids is required and must be non-empty' },
        { status: 400 }
      );
    }

    const validTypes = ['personal_outreach', 'pre_email_note', 'email_1'];
    if (!email_type || !validTypes.includes(email_type)) {
      return Response.json(
        { error: `email_type must be one of: ${validTypes.join(', ')}` },
        { status: 400 }
      );
    }

    // Fetch contacts from sally_contacts
    const { data: contacts, error: fetchError } = await supabase
      .from('sally_contacts')
      .select('id, first_name, last_name, email, email_2, campaign_2026')
      .in('id', contact_ids);

    if (fetchError) {
      return Response.json(
        { error: `Failed to fetch contacts: ${fetchError.message}` },
        { status: 500 }
      );
    }

    if (!contacts || contacts.length === 0) {
      return Response.json(
        { error: 'No contacts found for the provided IDs' },
        { status: 404 }
      );
    }

    const results: SendResult[] = [];

    for (const contact of contacts) {
      const c = contact as any;
      const campaign = c.campaign_2026 || {};
      const sendStatus = campaign.send_status || {};
      const contactName = `${c.first_name || ''} ${c.last_name || ''}`.trim();

      if (sendStatus[email_type]) {
        results.push({
          contact_id: c.id,
          contact_name: contactName,
          status: 'skipped',
          error: `Already sent ${email_type}`,
        });
        continue;
      }

      const toEmail = resolveEmail(c);
      if (!toEmail) {
        results.push({
          contact_id: c.id,
          contact_name: contactName,
          status: 'failed',
          error: 'No email address',
        });
        continue;
      }

      let subject: string;
      let messageBody: string;

      if (email_type === 'personal_outreach') {
        const outreach = campaign.personal_outreach;
        if (!outreach || !outreach.message_body) {
          results.push({
            contact_id: c.id,
            contact_name: contactName,
            status: 'failed',
            error: 'No personal outreach message found',
          });
          continue;
        }
        subject = outreach.subject_line || 'something I wanted to share with you';
        messageBody = outreach.message_body;
      } else if (email_type === 'pre_email_note') {
        const copy = campaign.campaign_copy;
        if (!copy || !copy.pre_email_note) {
          results.push({
            contact_id: c.id,
            contact_name: contactName,
            status: 'skipped',
            error: 'No pre-email note (not prior_donor/lapsed)',
          });
          continue;
        }
        subject = 'quick note before the big ask';
        messageBody = copy.pre_email_note;
      } else {
        // email_1
        const scaffold = campaign.scaffold || {};
        const firstName = c.first_name || 'Friend';
        const openerInsert = scaffold.opener_insert || null;
        const personalizationSentence = scaffold.personalization_sentence || null;
        subject = '8 trips this year';
        messageBody = buildEmail1Body(firstName, openerInsert, personalizationSentence);
      }

      try {
        const htmlBody = textToHtml(messageBody);

        let statusEntry: Record<string, unknown>;
        let resultEntry: SendResult;

        if (method === 'gmail_draft') {
          const draftData = await createGmailDraft({
            toEmail,
            subject,
            htmlBody,
            textBody: messageBody,
          });
          statusEntry = {
            drafted_at: new Date().toISOString(),
            gmail_draft_id: draftData.id || null,
            method: 'gmail_draft',
          };
          resultEntry = {
            contact_id: c.id,
            contact_name: contactName,
            status: 'drafted',
            gmail_draft_id: draftData.id || undefined,
            method: 'gmail_draft',
          };
        } else {
          const sendData = await sendWithResend({
            toEmail,
            subject,
            htmlBody,
            textBody: messageBody,
          });
          statusEntry = {
            sent_at: new Date().toISOString(),
            resend_id: sendData.id || null,
            method: 'resend',
          };
          resultEntry = {
            contact_id: c.id,
            contact_name: contactName,
            status: 'sent',
            resend_id: sendData.id || undefined,
            method: 'resend',
          };
        }

        const updatedSendStatus = {
          ...sendStatus,
          [email_type]: statusEntry,
        };
        const updatedCampaign = { ...campaign, send_status: updatedSendStatus };

        await supabase
          .from('sally_contacts')
          .update({ campaign_2026: updatedCampaign })
          .eq('id', c.id);

        results.push(resultEntry);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Send failed';
        console.error(`[Sally Campaign Send] Failed for ${contactName} (${c.id}):`, message);
        results.push({
          contact_id: c.id,
          contact_name: contactName,
          status: 'failed',
          error: message,
        });
      }
    }

    const totalSent = results.filter((r) => r.status === 'sent' || r.status === 'drafted').length;
    const totalFailed = results.filter((r) => r.status === 'failed').length;
    const totalSkipped = results.filter((r) => r.status === 'skipped').length;
    const totalDrafted = results.filter((r) => r.status === 'drafted').length;

    return Response.json({
      results,
      total_sent: totalSent,
      total_drafted: totalDrafted,
      total_failed: totalFailed,
      total_skipped: totalSkipped,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to send campaign emails';
    console.error('[Sally Campaign Send] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
