import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export const runtime = 'edge';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const contactId = parseInt(id, 10);
    if (isNaN(contactId)) {
      return NextResponse.json({ error: 'Invalid contact ID' }, { status: 400 });
    }

    // Fetch full sally_contact detail
    const { data: contact, error: contactError } = await supabase
      .from('sally_contacts')
      .select(
        'id, first_name, last_name, company, position, city, state, email, email_2, ' +
        'linkedin_url, headline, summary, ' +
        'ai_proximity_score, ai_proximity_tier, ai_capacity_score, ai_capacity_tier, ' +
        'ai_outdoorithm_fit, ai_tags, ' +
        'familiarity_rating, comms_last_date, comms_thread_count, ' +
        'comms_closeness, comms_momentum, comms_reasoning, comms_summary, ' +
        'shared_institutions, ask_readiness, fec_donations, real_estate_data, campaign_2026'
      )
      .eq('id', contactId)
      .single();

    if (contactError || !contact) {
      return NextResponse.json({ error: 'Contact not found' }, { status: 404 });
    }

    const c = contact as any;
    const tags = c.ai_tags || {};
    const proximity = tags.relationship_proximity || {};
    const affinity = tags.topical_affinity || {};
    const outreach = tags.outreach_context || {};
    const commsSummary = c.comms_summary || {};

    // Build recent threads from comms_summary channels
    const recentThreads: any[] = [];
    for (const channel of ['email', 'sms', 'calendar']) {
      const ch = commsSummary[channel];
      if (ch?.recent_threads) {
        recentThreads.push(...ch.recent_threads);
      }
    }
    recentThreads.sort((a: any, b: any) =>
      (b.last_date || b.date || '').localeCompare(a.last_date || a.date || '')
    );

    return NextResponse.json({
      // Basic info
      id: c.id,
      first_name: c.first_name,
      last_name: c.last_name,
      company: c.company,
      position: c.position,
      headline: c.headline,
      summary: c.summary,
      city: c.city,
      state: c.state,
      email: c.email || c.email_2,
      linkedin_url: c.linkedin_url,

      // Relationship
      familiarity_rating: c.familiarity_rating,
      comms_last_date: c.comms_last_date,
      comms_thread_count: c.comms_thread_count,
      comms_closeness: c.comms_closeness || null,
      comms_momentum: c.comms_momentum || null,
      comms_reasoning: c.comms_reasoning || null,
      comms_relationship_summary: null,
      comms_recent_threads: recentThreads.slice(0, 5),

      // Shared institutions
      shared_institutions: c.shared_institutions || [],

      // Ask-readiness
      ask_readiness: c.ask_readiness || null,

      // Wealth signals
      fec_donations: c.fec_donations || null,
      real_estate_data: c.real_estate_data || null,

      // AI scores
      ai_proximity_score: c.ai_proximity_score,
      ai_proximity_tier: c.ai_proximity_tier,
      ai_capacity_score: c.ai_capacity_score,
      ai_capacity_tier: c.ai_capacity_tier,
      ai_kindora_prospect_score: null,
      ai_kindora_prospect_type: null,
      ai_outdoorithm_fit: c.ai_outdoorithm_fit,

      // Shared context from ai_tags
      shared_employers: (proximity.shared_employers || []).map((e: any) => typeof e === 'string' ? e : e?.org || ''),
      shared_schools: (proximity.shared_schools || []).map((s: any) => typeof s === 'string' ? s : s?.org || ''),
      shared_boards: (proximity.shared_boards || []).map((b: any) => typeof b === 'string' ? b : b?.org || ''),

      // Topics and interests
      topics: (affinity.topics || []).slice(0, 10).map((t: any) => typeof t === 'string' ? t : t?.topic || ''),
      primary_interests: affinity.primary_interests || [],

      // Outreach context
      personalization_hooks: outreach.personalization_hooks || [],
      suggested_opener: outreach.suggested_opener || '',
      best_approach: outreach.best_approach || '',
      talking_points: affinity.talking_points || [],

      // Sales fit (not applicable for Sally)
      kindora_rationale: '',

      // Campaign 2026
      campaign_2026: c.campaign_2026 || null,
    });
  } catch (err: any) {
    console.error('[Sally Contact Detail] Error:', err);
    return NextResponse.json(
      { error: err.message || 'Failed to fetch contact detail' },
      { status: 500 }
    );
  }
}
