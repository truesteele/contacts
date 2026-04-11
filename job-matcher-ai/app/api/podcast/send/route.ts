import { supabase } from '@/lib/supabase';

type SendMethod = 'gmail_draft' | 'direct_send' | 'manual';

// Speaker email accounts
const SPEAKER_EMAILS: Record<string, { from: string; name: string }> = {
  sally: { from: 'sally@outdoorithmcollective.org', name: 'Sally Steele' },
  justin: { from: 'justin@truesteele.com', name: 'Justin Steele' },
};

async function getGmailAccessToken(speakerSlug: string): Promise<string> {
  // Per-speaker Gmail credentials: SALLY_GMAIL_CLIENT_ID, JUSTIN_GMAIL_CLIENT_ID, etc.
  // Falls back to generic GMAIL_* if speaker-specific vars not set
  const prefix = speakerSlug.toUpperCase();
  const clientId = process.env[`${prefix}_GMAIL_CLIENT_ID`] || process.env.GMAIL_CLIENT_ID;
  const clientSecret = process.env[`${prefix}_GMAIL_CLIENT_SECRET`] || process.env.GMAIL_CLIENT_SECRET;
  const refreshToken = process.env[`${prefix}_GMAIL_REFRESH_TOKEN`] || process.env.GMAIL_REFRESH_TOKEN;
  if (!clientId || !clientSecret || !refreshToken) {
    throw new Error(`Gmail OAuth credentials not configured for ${speakerSlug} (${prefix}_GMAIL_CLIENT_ID, ${prefix}_GMAIL_CLIENT_SECRET, ${prefix}_GMAIL_REFRESH_TOKEN)`);
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

function base64UrlEncode(str: string): string {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(str);
  let binary = '';
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function buildRfc2822Message(params: {
  fromEmail: string;
  fromName: string;
  toEmail: string;
  subject: string;
  textBody: string;
}): string {
  const lines = [
    `From: ${params.fromName} <${params.fromEmail}>`,
    `To: ${params.toEmail}`,
    `Subject: ${params.subject}`,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    '',
    params.textBody,
  ];
  return lines.join('\r\n');
}

async function createGmailDraft(params: {
  fromEmail: string;
  fromName: string;
  toEmail: string;
  subject: string;
  textBody: string;
  speakerSlug: string;
}): Promise<{ id: string | null }> {
  const accessToken = await getGmailAccessToken(params.speakerSlug);
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

async function sendWithGmail(params: {
  fromEmail: string;
  fromName: string;
  toEmail: string;
  subject: string;
  textBody: string;
  speakerSlug: string;
}): Promise<{ id: string | null; threadId: string | null }> {
  const accessToken = await getGmailAccessToken(params.speakerSlug);
  const raw = base64UrlEncode(buildRfc2822Message(params));

  const response = await fetch('https://gmail.googleapis.com/gmail/v1/users/me/messages/send', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ raw }),
  });

  const data = await response.json() as { id?: string; threadId?: string; error?: { message?: string } };
  if (!response.ok) {
    throw new Error(`Gmail send failed: ${data.error?.message || response.status}`);
  }
  return { id: data.id ?? null, threadId: data.threadId ?? null };
}

export async function POST(req: Request) {
  try {
    const body = await req.json() as {
      pitch_id?: number;
      method?: SendMethod;
    };

    if (!body.pitch_id) {
      return Response.json({ error: 'pitch_id is required' }, { status: 400 });
    }

    const method: SendMethod = body.method || 'gmail_draft';
    if (!['gmail_draft', 'direct_send', 'manual'].includes(method)) {
      return Response.json(
        { error: 'method must be gmail_draft, direct_send, or manual' },
        { status: 400 }
      );
    }

    // Fetch pitch with speaker and podcast data
    const { data: pitch, error: pitchError } = await supabase
      .from('podcast_pitches')
      .select('id, podcast_target_id, speaker_profile_id, subject_line, pitch_body, pitch_status')
      .eq('id', body.pitch_id)
      .single();

    if (pitchError || !pitch) {
      return Response.json({ error: 'Pitch not found' }, { status: 404 });
    }

    if (!pitch.pitch_body || !pitch.subject_line) {
      return Response.json(
        { error: 'Pitch has no generated content. Generate first.' },
        { status: 400 }
      );
    }

    // Fetch speaker
    const { data: speaker } = await supabase
      .from('speaker_profiles')
      .select('id, slug, name')
      .eq('id', pitch.speaker_profile_id)
      .single();

    if (!speaker) {
      return Response.json({ error: 'Speaker not found' }, { status: 404 });
    }

    // Fetch podcast for the recipient email
    const { data: podcast } = await supabase
      .from('podcast_targets')
      .select('id, title, host_email, host_name')
      .eq('id', pitch.podcast_target_id)
      .single();

    if (!podcast) {
      return Response.json({ error: 'Podcast not found' }, { status: 404 });
    }

    const speakerSlug = speaker.slug.replace('-steele', '');
    const senderConfig = SPEAKER_EMAILS[speakerSlug];
    if (!senderConfig) {
      return Response.json({ error: `No email config for speaker: ${speaker.slug}` }, { status: 400 });
    }

    const toEmail = podcast.host_email;
    const now = new Date().toISOString();

    // Handle manual sends
    if (method === 'manual') {
      const { data: campaign, error: campaignError } = await supabase
        .from('podcast_campaigns')
        .insert({
          pitch_id: pitch.id,
          speaker_profile_id: speaker.id,
          sent_from_email: senderConfig.from,
          sent_to_email: toEmail || null,
          sent_at: now,
          send_method: 'manual',
          outcome: 'pending',
        })
        .select('id')
        .single();

      if (campaignError) {
        return Response.json({ error: `Failed to create campaign: ${campaignError.message}` }, { status: 500 });
      }

      // Update pitch status
      await supabase
        .from('podcast_pitches')
        .update({ pitch_status: 'sent', updated_at: now })
        .eq('id', pitch.id);

      return Response.json({
        status: 'sent',
        method: 'manual',
        campaign_id: campaign?.id,
        podcast_title: podcast.title,
      });
    }

    // Gmail draft or direct send requires a recipient email
    if (!toEmail) {
      return Response.json(
        { error: `No email address for podcast "${podcast.title}". Use manual method or add host email first.` },
        { status: 400 }
      );
    }

    let gmailMessageId: string | null = null;
    let gmailThreadId: string | null = null;
    let resultStatus: 'draft' | 'sent';

    // Create campaign record BEFORE sending (so we have a record even if send fails)
    const { data: campaign, error: campaignError } = await supabase
      .from('podcast_campaigns')
      .insert({
        pitch_id: pitch.id,
        speaker_profile_id: speaker.id,
        sent_from_email: senderConfig.from,
        sent_to_email: toEmail,
        sent_at: now,
        send_method: method,
        outcome: 'pending',
      })
      .select('id')
      .single();

    if (campaignError) {
      return Response.json({ error: `Failed to create campaign record: ${campaignError.message}` }, { status: 500 });
    }

    if (method === 'gmail_draft') {
      const result = await createGmailDraft({
        fromEmail: senderConfig.from,
        fromName: senderConfig.name,
        toEmail,
        subject: pitch.subject_line,
        textBody: pitch.pitch_body,
        speakerSlug,
      });
      gmailMessageId = result.id;
      resultStatus = 'draft';
    } else {
      const result = await sendWithGmail({
        fromEmail: senderConfig.from,
        fromName: senderConfig.name,
        toEmail,
        subject: pitch.subject_line,
        textBody: pitch.pitch_body,
        speakerSlug,
      });
      gmailMessageId = result.id;
      gmailThreadId = result.threadId;
      resultStatus = 'sent';
    }

    // Update campaign with Gmail IDs
    if (gmailMessageId || gmailThreadId) {
      await supabase
        .from('podcast_campaigns')
        .update({
          gmail_message_id: gmailMessageId,
          gmail_thread_id: gmailThreadId,
        })
        .eq('id', campaign?.id);
    }

    // Update pitch status
    await supabase
      .from('podcast_pitches')
      .update({ pitch_status: resultStatus, updated_at: now })
      .eq('id', pitch.id);

    return Response.json({
      status: resultStatus,
      method,
      campaign_id: campaign?.id,
      gmail_message_id: gmailMessageId,
      gmail_thread_id: gmailThreadId,
      podcast_title: podcast.title,
      sent_to: toEmail,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to send pitch';
    console.error('[Podcast Send] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
