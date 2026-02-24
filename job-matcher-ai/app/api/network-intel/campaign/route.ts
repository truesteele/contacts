import { supabase } from '@/lib/supabase';

export const runtime = 'edge';

const SELECT_COLS =
  'id, first_name, last_name, company, position, email, personal_email, work_email, campaign_2026';

export async function GET() {
  try {
    const allContacts: any[] = [];
    const pageSize = 1000;
    let offset = 0;

    while (true) {
      const { data, error } = await supabase
        .from('contacts')
        .select(SELECT_COLS)
        .not('campaign_2026', 'is', null)
        .order('id')
        .range(offset, offset + pageSize - 1);

      if (error) throw new Error(`DB error: ${error.message}`);
      if (!data || data.length === 0) break;

      allContacts.push(...data);
      if (data.length < pageSize) break;
      offset += pageSize;
    }

    // Flatten campaign_2026 JSONB fields for frontend consumption
    const flattened = allContacts.map((c) => {
      const camp = c.campaign_2026 || {};
      const scaffold = camp.scaffold || {};
      const outreach = camp.personal_outreach;
      const copy = camp.campaign_copy;
      const sendStatus = camp.send_status;
      const donation = camp.donation;

      return {
        id: c.id,
        first_name: c.first_name,
        last_name: c.last_name,
        company: c.company,
        position: c.position,
        email: c.email,
        personal_email: c.personal_email,
        work_email: c.work_email,
        // Flattened scaffold fields
        list: scaffold.campaign_list || null,
        persona: scaffold.persona || null,
        ask_amount: scaffold.primary_ask_amount || null,
        capacity_tier: scaffold.capacity_tier || null,
        lifecycle: scaffold.lifecycle_stage || null,
        motivation: scaffold.primary_motivation || null,
        // Channel from personal_outreach or campaign_copy
        channel: outreach?.channel || copy?.thank_you_channel || null,
        // Subject from personal_outreach
        subject: outreach?.subject_line || null,
        // Booleans for which content exists
        has_outreach: !!outreach,
        has_copy: !!copy,
        // Status fields
        send_status: sendStatus && Object.keys(sendStatus).length > 0 ? sendStatus : null,
        donation: donation || null,
        responded_at: camp.responded_at || null,
      };
    });

    // Compute stats
    const stats = {
      by_list: {
        A: flattened.filter((c) => c.list === 'A').length,
        B: flattened.filter((c) => c.list === 'B').length,
        C: flattened.filter((c) => c.list === 'C').length,
        D: flattened.filter((c) => c.list === 'D').length,
      },
      by_persona: {
        believer: flattened.filter((c) => c.persona === 'believer').length,
        impact_professional: flattened.filter((c) => c.persona === 'impact_professional').length,
        network_peer: flattened.filter((c) => c.persona === 'network_peer').length,
      },
      by_capacity: {
        leadership: flattened.filter((c) => c.capacity_tier === 'leadership').length,
        major: flattened.filter((c) => c.capacity_tier === 'major').length,
        mid: flattened.filter((c) => c.capacity_tier === 'mid').length,
        base: flattened.filter((c) => c.capacity_tier === 'base').length,
        community: flattened.filter((c) => c.capacity_tier === 'community').length,
      },
      by_lifecycle: {
        new: flattened.filter((c) => c.lifecycle === 'new').length,
        prior_donor: flattened.filter((c) => c.lifecycle === 'prior_donor').length,
        lapsed: flattened.filter((c) => c.lifecycle === 'lapsed').length,
      },
      by_send_status: {
        not_sent: flattened.filter((c) => !c.send_status).length,
        sent: flattened.filter((c) => c.send_status && !c.donation).length,
        donated: flattened.filter((c) => !!c.donation).length,
        responded: flattened.filter((c) => !!c.responded_at).length,
      },
    };

    return Response.json({
      contacts: flattened,
      total: flattened.length,
      stats,
    });
  } catch (error: any) {
    console.error('Campaign fetch error:', error);
    return Response.json(
      { error: error.message || 'Failed to fetch campaign data' },
      { status: 500 }
    );
  }
}
