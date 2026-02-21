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

    // Fetch full contact detail
    const { data: contact, error: contactError } = await supabase
      .from('contacts')
      .select(
        'id, first_name, last_name, company, position, city, state, email, personal_email, work_email, ' +
        'linkedin_url, headline, summary, ' +
        'ai_proximity_score, ai_proximity_tier, ai_capacity_score, ai_capacity_tier, ' +
        'ai_kindora_prospect_score, ai_kindora_prospect_type, ai_outdoorithm_fit, ai_tags, ' +
        'familiarity_rating, comms_last_date, comms_thread_count, communication_history, ' +
        'shared_institutions, ask_readiness, fec_donations, real_estate_data'
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
    const salesFit = tags.sales_fit || {};
    const commsHistory = c.communication_history || {};

    // Extract recent threads from communication_history
    const recentThreads = (commsHistory.recent_threads || commsHistory.threads || []).slice(0, 5);

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
      email: c.email || c.personal_email || c.work_email,
      linkedin_url: c.linkedin_url,

      // Relationship — familiarity is primary signal
      familiarity_rating: c.familiarity_rating,
      comms_last_date: c.comms_last_date,
      comms_thread_count: c.comms_thread_count,
      comms_relationship_summary: commsHistory.relationship_summary || null,
      comms_recent_threads: recentThreads,

      // Structured institutional overlap (temporal analysis)
      shared_institutions: c.shared_institutions || [],

      // Ask-readiness (AI-scored per goal)
      ask_readiness: c.ask_readiness || null,

      // Wealth signals
      fec_donations: c.fec_donations || null,
      real_estate_data: c.real_estate_data || null,

      // AI scores
      ai_proximity_score: c.ai_proximity_score,
      ai_proximity_tier: c.ai_proximity_tier,
      ai_capacity_score: c.ai_capacity_score,
      ai_capacity_tier: c.ai_capacity_tier,
      ai_kindora_prospect_score: c.ai_kindora_prospect_score,
      ai_kindora_prospect_type: c.ai_kindora_prospect_type,
      ai_outdoorithm_fit: c.ai_outdoorithm_fit,

      // Shared context (legacy from ai_tags)
      shared_employers: proximity.shared_employers || [],
      shared_schools: proximity.shared_schools || [],
      shared_boards: proximity.shared_boards || [],

      // Topics and interests
      topics: (affinity.topics || []).slice(0, 10),
      primary_interests: affinity.primary_interests || [],

      // Outreach context
      personalization_hooks: outreach.personalization_hooks || [],
      suggested_opener: outreach.suggested_opener || '',
      best_approach: outreach.best_approach || '',
      talking_points: affinity.talking_points || [],

      // Sales fit
      kindora_rationale: salesFit.kindora_rationale || '',
    });
  } catch (err: any) {
    console.error('[Contact Detail] Error:', err);
    return NextResponse.json(
      { error: err.message || 'Failed to fetch contact detail' },
      { status: 500 }
    );
  }
}
