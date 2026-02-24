import { Resend } from 'resend';
import { supabase } from '@/lib/supabase';

export const runtime = 'edge';

const FROM_EMAIL = 'Justin Steele <justin@outdoorithmcollective.org>';
const REPLY_TO = 'justinrsteele@gmail.com';

let _resend: Resend | null = null;
function getResend(): Resend {
  if (!_resend) {
    _resend = new Resend(process.env.RESEND_API_KEY_OC);
  }
  return _resend;
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
  personal_email?: string | null;
  email?: string | null;
  work_email?: string | null;
}): string | null {
  return contact.personal_email || contact.email || contact.work_email || null;
}

// Email 1 template from COME_ALIVE_2026_Campaign.md
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

Sally and I have 10 trips planned this season through Outdoorithm Collective — Joshua Tree, Pinnacles, Yosemite, Lassen, and more. Each one brings 10-12 families into nature. Each costs about $10K to run.

We've raised $40K from grants and early supporters. A friend is matching the first $20K in donations dollar-for-dollar. $60K to go to fund every trip.

$1,000 puts two families at the campfire. $2,500 covers a quarter of a trip. $5,000 sponsors half.

If you want in: outdoorithmcollective.org/donate

Or just reply — happy to tell you more.

Justin`;
}

interface SendResult {
  contact_id: number;
  contact_name: string;
  status: 'sent' | 'failed' | 'skipped';
  resend_id?: string;
  error?: string;
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { contact_ids, email_type } = body as {
      contact_ids?: number[];
      email_type?: string;
    };

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

    // Fetch contacts with campaign data
    const { data: contacts, error: fetchError } = await supabase
      .from('contacts')
      .select('id, first_name, last_name, email, personal_email, work_email, campaign_2026')
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

    // Send sequentially to avoid rate limits
    for (const contact of contacts) {
      const c = contact as any;
      const campaign = c.campaign_2026 || {};
      const sendStatus = campaign.send_status || {};
      const contactName = `${c.first_name || ''} ${c.last_name || ''}`.trim();

      // Skip if already sent for this email type
      if (sendStatus[email_type]) {
        results.push({
          contact_id: c.id,
          contact_name: contactName,
          status: 'skipped',
          error: `Already sent ${email_type}`,
        });
        continue;
      }

      // Resolve email address
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

      // Build subject and body based on email type
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
        subject = outreach.subject_line || 'quick thing — before I send the big ask';
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
        subject = '10 trips this year';
        messageBody = buildEmail1Body(firstName, openerInsert, personalizationSentence);
      }

      try {
        const htmlBody = textToHtml(messageBody);

        const { data: sendData, error: sendError } = await getResend().emails.send({
          from: FROM_EMAIL,
          to: [toEmail],
          replyTo: REPLY_TO,
          subject,
          html: htmlBody,
          text: messageBody,
          headers: {
            'List-Unsubscribe': `<mailto:${REPLY_TO}?subject=unsubscribe>`,
          },
        });

        if (sendError) {
          results.push({
            contact_id: c.id,
            contact_name: contactName,
            status: 'failed',
            error: sendError.message,
          });
          continue;
        }

        // Update send_status in campaign_2026
        const updatedSendStatus = {
          ...sendStatus,
          [email_type]: {
            sent_at: new Date().toISOString(),
            resend_id: sendData?.id || null,
          },
        };
        const updatedCampaign = { ...campaign, send_status: updatedSendStatus };

        await supabase
          .from('contacts')
          .update({ campaign_2026: updatedCampaign })
          .eq('id', c.id);

        results.push({
          contact_id: c.id,
          contact_name: contactName,
          status: 'sent',
          resend_id: sendData?.id,
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Send failed';
        results.push({
          contact_id: c.id,
          contact_name: contactName,
          status: 'failed',
          error: message,
        });
      }
    }

    const totalSent = results.filter((r) => r.status === 'sent').length;
    const totalFailed = results.filter((r) => r.status === 'failed').length;
    const totalSkipped = results.filter((r) => r.status === 'skipped').length;

    return Response.json({
      results,
      total_sent: totalSent,
      total_failed: totalFailed,
      total_skipped: totalSkipped,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to send campaign emails';
    console.error('[Campaign Send] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
