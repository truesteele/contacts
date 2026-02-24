import { supabase } from '@/lib/supabase';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

const SELECT_COLS =
  'id, first_name, last_name, company, position, email, personal_email, work_email, campaign_2026';

// GET single contact with full campaign_2026 JSONB
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const { data, error } = await supabase
      .from('contacts')
      .select(SELECT_COLS)
      .eq('id', id)
      .single();

    if (error) throw new Error(`DB error: ${error.message}`);
    if (!data) return Response.json({ error: 'Contact not found' }, { status: 404 });

    return Response.json({ contact: data });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch contact';
    console.error('Campaign contact fetch error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}

// PATCH update fields in campaign_2026 JSONB
export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await req.json();
    const { section, field, value } = body;

    if (!section) {
      return Response.json({ error: 'Missing "section" in request body' }, { status: 400 });
    }

    // Fetch current campaign_2026 data
    const { data: contact, error: fetchError } = await supabase
      .from('contacts')
      .select('campaign_2026')
      .eq('id', id)
      .single();

    if (fetchError) throw new Error(`DB error: ${fetchError.message}`);
    if (!contact) return Response.json({ error: 'Contact not found' }, { status: 404 });

    const campaign = { ...(contact.campaign_2026 || {}) };

    if (section === 'donation') {
      // Record donation: { "section": "donation", "value": { amount, donated_at, source } }
      campaign.donation = value;
    } else if (section === 'responded_at') {
      // Record response: { "section": "responded_at", "value": "2026-02-25" }
      campaign.responded_at = value;
    } else if (section === 'send_status') {
      // Update send status: { "section": "send_status", "field": "personal_outreach", "value": { sent_at, resend_id } }
      campaign.send_status = { ...(campaign.send_status || {}), [field]: value };
    } else if (field) {
      // Nested field update: { "section": "personal_outreach", "field": "message_body", "value": "new text" }
      if (!campaign[section]) {
        campaign[section] = {};
      }
      campaign[section] = { ...campaign[section], [field]: value };
    } else {
      return Response.json(
        { error: 'Missing "field" for section update, or use "donation"/"responded_at" section' },
        { status: 400 }
      );
    }

    // Write back the full updated campaign_2026
    const { data: updated, error: updateError } = await supabase
      .from('contacts')
      .update({ campaign_2026: campaign })
      .eq('id', id)
      .select(SELECT_COLS)
      .single();

    if (updateError) throw new Error(`DB error: ${updateError.message}`);

    return Response.json({ contact: updated });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to update contact';
    console.error('Campaign contact update error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
