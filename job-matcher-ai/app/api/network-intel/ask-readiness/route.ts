import { supabase } from '@/lib/supabase';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

const SELECT_COLS =
  'id, first_name, last_name, company, position, city, state, headline, ' +
  'familiarity_rating, comms_last_date, comms_thread_count, ' +
  'ai_capacity_tier, ai_capacity_score, ai_outdoorithm_fit, ' +
  'ask_readiness, oc_engagement';

export async function GET(req: NextRequest) {
  const goal = req.nextUrl.searchParams.get('goal') || 'outdoorithm_fundraising';

  try {
    // Fetch all contacts that have ask_readiness data
    // Supabase pagination for large datasets
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

    // Filter to contacts that have a score for the requested goal
    // and flatten the ask_readiness JSONB into top-level fields
    const scored = allContacts
      .filter((c) => {
        const ar = c.ask_readiness;
        return ar && typeof ar === 'object' && ar[goal] && typeof ar[goal].score === 'number';
      })
      .map((c) => {
        const goalData = c.ask_readiness[goal];
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
          ai_capacity_tier: c.ai_capacity_tier,
          ai_capacity_score: c.ai_capacity_score,
          ai_outdoorithm_fit: c.ai_outdoorithm_fit,
          oc_engagement: c.oc_engagement,
          // Flattened ask-readiness fields
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
    console.error('Ask readiness fetch error:', error);
    return Response.json(
      { error: error.message || 'Failed to fetch ask-readiness data' },
      { status: 500 }
    );
  }
}
