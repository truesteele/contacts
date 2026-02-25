import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export const runtime = 'edge';

export interface ContactSummary {
  id: number;
  first_name: string;
  last_name: string;
  company: string | null;
  position: string | null;
  headline: string | null;
  city: string | null;
  state: string | null;
  linkedin_url: string | null;
  // Relationship
  familiarity_rating: number | null;
  comms_closeness: string | null;
  comms_momentum: string | null;
  comms_last_date: string | null;
  comms_thread_count: number | null;
  comms_relationship_summary: string | null;
  // Scores
  ai_proximity_tier: string | null;
  ai_capacity_tier: string | null;
  ai_outdoorithm_fit: string | null;
  // Ask-readiness
  ask_readiness_tier: string | null;
  ask_readiness_score: number | null;
  ask_readiness_reasoning: string | null;
  ask_readiness_personalization: string | null;
  // Institutional overlap
  shared_institutions: Array<{
    name: string;
    type: string;
    overlap: string;
    temporal_overlap?: boolean;
    justin_period?: string;
    contact_period?: string;
  }>;
  // Outreach context (from ai_tags)
  personalization_hooks: string[];
  suggested_opener: string;
  talking_points: string[];
  topics: string[];
  primary_interests: string[];
  best_approach: string;
}

const CONTACT_SELECT =
  'id, first_name, last_name, company, position, headline, city, state, ' +
  'email, personal_email, work_email, email_2, linkedin_url, ' +
  'ai_proximity_tier, ai_capacity_tier, ai_outdoorithm_fit, ai_tags, ' +
  'familiarity_rating, comms_last_date, comms_thread_count, comms_closeness, comms_momentum, ' +
  'communication_history, shared_institutions, ask_readiness';

function extractContactSummary(c: any): ContactSummary {
  const tags = c.ai_tags || {};
  const outreach = tags.outreach_context || {};
  const affinity = tags.topical_affinity || {};
  const commsHistory = c.communication_history || {};

  // Extract ask-readiness for primary goal
  const ar = c.ask_readiness?.outdoorithm_fundraising || null;

  return {
    id: c.id,
    first_name: c.first_name,
    last_name: c.last_name,
    company: c.company,
    position: c.position,
    headline: c.headline,
    city: c.city,
    state: c.state,
    linkedin_url: c.linkedin_url,
    familiarity_rating: c.familiarity_rating,
    comms_closeness: c.comms_closeness || null,
    comms_momentum: c.comms_momentum || null,
    comms_last_date: c.comms_last_date,
    comms_thread_count: c.comms_thread_count,
    comms_relationship_summary: commsHistory.relationship_summary || null,
    ai_proximity_tier: c.ai_proximity_tier,
    ai_capacity_tier: c.ai_capacity_tier,
    ai_outdoorithm_fit: c.ai_outdoorithm_fit,
    ask_readiness_tier: ar?.tier || null,
    ask_readiness_score: ar?.score || null,
    ask_readiness_reasoning: ar?.reasoning || null,
    ask_readiness_personalization: ar?.personalization_angle || null,
    shared_institutions: Array.isArray(c.shared_institutions) ? c.shared_institutions : [],
    personalization_hooks: outreach.personalization_hooks || [],
    suggested_opener: outreach.suggested_opener || '',
    talking_points: affinity.talking_points || [],
    topics: (affinity.topics || []).slice(0, 8).map((t: any) =>
      typeof t === 'string' ? t : t?.topic || ''
    ),
    primary_interests: affinity.primary_interests || [],
    best_approach: outreach.best_approach || '',
  };
}

export async function POST(req: Request) {
  try {
    const { emails } = (await req.json()) as { emails: string[] };

    if (!emails || !Array.isArray(emails) || emails.length === 0) {
      return NextResponse.json(
        { error: 'emails array is required' },
        { status: 400 }
      );
    }

    // Deduplicate and lowercase
    const uniqueEmails = [...new Set(emails.map((e) => e.toLowerCase().trim()))];

    // Query all email columns — Supabase doesn't support OR across ilike easily,
    // so we do 4 parallel queries and merge results
    const emailCols = ['email', 'personal_email', 'work_email', 'email_2'] as const;
    const queries = emailCols.map((col) =>
      supabase
        .from('contacts')
        .select(CONTACT_SELECT)
        .in(col, uniqueEmails)
    );

    const results = await Promise.all(queries);

    // Merge results, deduplicate by contact ID
    const contactById = new Map<number, any>();
    const emailToContactId = new Map<string, number>();

    for (let qi = 0; qi < results.length; qi++) {
      const { data, error } = results[qi];
      if (error) {
        console.error(`[Contact Lookup] Query ${qi} error:`, error.message);
        continue;
      }
      if (!data) continue;

      const col = emailCols[qi];
      for (const row of data as any[]) {
        contactById.set(row.id, row);
        const emailVal = row[col];
        if (emailVal) {
          emailToContactId.set(emailVal.toLowerCase(), row.id);
        }
      }
    }

    // Build the result map: email → ContactSummary
    const contactMap: Record<string, ContactSummary> = {};
    for (const email of uniqueEmails) {
      const contactId = emailToContactId.get(email);
      if (contactId != null) {
        const contact = contactById.get(contactId);
        if (contact) {
          contactMap[email] = extractContactSummary(contact);
        }
      }
    }

    return NextResponse.json({
      contacts: contactMap,
      matched: Object.keys(contactMap).length,
      total_queried: uniqueEmails.length,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Contact lookup failed';
    console.error('[Contact Lookup] Error:', message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
