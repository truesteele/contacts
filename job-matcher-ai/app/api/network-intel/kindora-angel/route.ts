import { supabase } from '@/lib/supabase';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

const SELECT_COLS =
  'id, first_name, last_name, company, position, city, state, headline, ' +
  'familiarity_rating, comms_last_date, comms_thread_count, ' +
  'pitchbook_data, edgar_data, ' +
  'ask_readiness';

const INVESTOR_KEYWORDS = /\b(angel invest|venture capital|investor|managing partner|general partner|founding partner|private equity|family office|venture partner)\b/i;

export async function GET(req: NextRequest) {
  const goal = req.nextUrl.searchParams.get('goal') || 'kindora_angel_investment';

  try {
    const allContacts: any[] = [];
    const pageSize = 1000;
    let offset = 0;

    while (true) {
      const { data, error } = await supabase
        .from('contacts')
        .select(SELECT_COLS)
        .not('ask_readiness', 'is', null)
        .order('id')
        .range(offset, offset + pageSize - 1);

      if (error) throw new Error(`DB error: ${error.message}`);
      if (!data || data.length === 0) break;

      allContacts.push(...data);
      if (data.length < pageSize) break;
      offset += pageSize;
    }

    const scored = allContacts
      .filter((c) => {
        const ar = c.ask_readiness;
        return ar && typeof ar === 'object' && ar[goal] && typeof ar[goal].score === 'number';
      })
      .map((c) => {
        const goalData = c.ask_readiness[goal];
        const pb = c.pitchbook_data;
        const pbMatched = pb && typeof pb === 'object' && pb.status === 'matched';
        const pbPersonal = pbMatched && (pb.investing_context === 'personal' || pb.investing_context === 'both');
        const ed = c.edgar_data;
        const edMatched = ed && typeof ed === 'object' && ed.status === 'matched';
        const edSignal = edMatched ? (ed.investor_signal || 'weak') : null;
        const selfIdentified = INVESTOR_KEYWORDS.test(c.headline || '') || INVESTOR_KEYWORDS.test(c.position || '');

        let investor_status: string | null = null;
        if (pbPersonal) investor_status = 'pitchbook_verified';
        else if (pbMatched) investor_status = 'pitchbook_institutional';
        else if (edMatched && (edSignal === 'strong' || edSignal === 'moderate')) investor_status = 'edgar_verified';
        else if (selfIdentified) investor_status = 'self_identified';

        return {
          id: c.id,
          first_name: c.first_name,
          last_name: c.last_name,
          company: c.company,
          position: c.position,
          city: c.city,
          state: c.state,
          headline: c.headline,
          familiarity_rating: c.familiarity_rating,
          comms_last_date: c.comms_last_date,
          comms_thread_count: c.comms_thread_count,
          investor_status,
          pitchbook_investments: pbMatched ? (pb.total_investments ?? null) : null,
          edgar_filings: edMatched ? (ed.matched_filings_count ?? ed.filings?.length ?? null) : null,
          edgar_signal: edSignal,
          check_size: goalData.suggested_ask_range || null,
          score: goalData.score,
          tier: goalData.tier,
          reasoning: goalData.reasoning,
          recommended_approach: goalData.recommended_approach,
          ask_timing: goalData.ask_timing,
          cultivation_needed: goalData.cultivation_needed,
          suggested_ask_range: goalData.suggested_ask_range,
          personalization_angle: goalData.personalization_angle,
          risk_factors: goalData.risk_factors || [],
          scored_at: goalData.scored_at,
        };
      })
      .sort((a, b) => b.score - a.score);

    return Response.json({
      contacts: scored,
      total: scored.length,
      goal,
      tier_counts: {
        ready_now: scored.filter((c) => c.tier === 'ready_now').length,
        cultivate_first: scored.filter((c) => c.tier === 'cultivate_first').length,
        long_term: scored.filter((c) => c.tier === 'long_term').length,
        not_a_fit: scored.filter((c) => c.tier === 'not_a_fit').length,
      },
    });
  } catch (error: any) {
    console.error('Kindora angel fetch error:', error);
    return Response.json(
      { error: error.message || 'Failed to fetch kindora angel data' },
      { status: 500 }
    );
  }
}

export async function PATCH(req: NextRequest) {
  try {
    const body = await req.json();
    const { contact_id, field, value, goal } = body as {
      contact_id: number;
      field: 'tier';
      value: string;
      goal?: string;
    };

    if (!contact_id || !field || value === undefined) {
      return Response.json({ error: 'contact_id, field, and value are required' }, { status: 400 });
    }

    if (field === 'tier') {
      const goalKey = goal || 'kindora_angel_investment';
      const validTiers = ['ready_now', 'cultivate_first', 'long_term', 'not_a_fit'];
      if (!validTiers.includes(value)) {
        return Response.json({ error: `tier must be one of: ${validTiers.join(', ')}` }, { status: 400 });
      }

      const { data: contact, error: fetchErr } = await supabase
        .from('contacts')
        .select('ask_readiness')
        .eq('id', contact_id)
        .single();

      if (fetchErr || !contact) {
        return Response.json({ error: 'Contact not found' }, { status: 404 });
      }

      const ar = contact.ask_readiness || {};
      const goalData = ar[goalKey] || {};
      goalData.tier = value;
      ar[goalKey] = goalData;

      const { error: updateErr } = await supabase
        .from('contacts')
        .update({ ask_readiness: ar })
        .eq('id', contact_id);

      if (updateErr) throw new Error(updateErr.message);

      return Response.json({ ok: true, field, value });
    }

    return Response.json({ error: `Unknown field: ${field}` }, { status: 400 });
  } catch (error: any) {
    console.error('Kindora angel PATCH error:', error);
    return Response.json(
      { error: error.message || 'Failed to update' },
      { status: 500 }
    );
  }
}
