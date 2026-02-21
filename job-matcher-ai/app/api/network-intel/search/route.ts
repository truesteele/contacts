import { FilterState } from '@/lib/types';
import { supabase } from '@/lib/supabase';
import { generateEmbedding768 } from '@/lib/openai';

export const runtime = 'edge';

const NETWORK_SELECT_COLS =
  'id, first_name, last_name, company, position, city, state, email, linkedin_url, headline, ' +
  'ai_proximity_score, ai_proximity_tier, ai_capacity_score, ai_capacity_tier, ' +
  'ai_kindora_prospect_score, ai_kindora_prospect_type, ai_outdoorithm_fit, ' +
  'familiarity_rating, comms_last_date, comms_thread_count, ask_readiness';

/**
 * Execute a structured search using searchNetwork logic.
 * Maps FilterState fields to Supabase query filters.
 */
async function executeStructuredSearch(filters: FilterState) {
  let query = supabase.from('contacts').select(NETWORK_SELECT_COLS);

  if (filters.proximity_min != null) {
    query = query.gte('ai_proximity_score', filters.proximity_min);
  }
  if (filters.capacity_min != null) {
    query = query.gte('ai_capacity_score', filters.capacity_min);
  }
  if (filters.proximity_tiers && filters.proximity_tiers.length > 0) {
    query = query.in('ai_proximity_tier', filters.proximity_tiers);
  }
  if (filters.capacity_tiers && filters.capacity_tiers.length > 0) {
    query = query.in('ai_capacity_tier', filters.capacity_tiers);
  }
  if (filters.outdoorithm_fit && filters.outdoorithm_fit.length > 0) {
    query = query.in('ai_outdoorithm_fit', filters.outdoorithm_fit);
  }
  if (filters.kindora_type && filters.kindora_type.length > 0) {
    query = query.in('ai_kindora_prospect_type', filters.kindora_type);
  }
  if (filters.company_keyword) {
    query = query.ilike('company', `%${filters.company_keyword}%`);
  }
  if (filters.name_search) {
    // Sanitize to prevent PostgREST filter syntax injection (commas, parens, dots as delimiters)
    const sanitized = filters.name_search.replace(/[,().]/g, ' ').trim();
    if (sanitized) {
      const term = `%${sanitized}%`;
      query = query.or(`first_name.ilike.${term},last_name.ilike.${term}`);
    }
  }
  if (filters.location_state) {
    query = query.ilike('state', `%${filters.location_state}%`);
  }
  if (filters.familiarity_min != null) {
    query = query.gte('familiarity_rating', filters.familiarity_min);
  }
  if (filters.has_comms) {
    query = query.gt('comms_thread_count', 0);
  }
  if (filters.comms_since) {
    query = query.gte('comms_last_date', filters.comms_since);
  }

  // Apply sorting
  if (filters.sort_by === 'ask_readiness' && filters.goal) {
    // Sort by ask_readiness score for a specific goal — requires raw ordering
    // Supabase JS doesn't support JSONB path ordering, so we fetch and sort in-memory
    query = query.not('ask_readiness', 'is', null);
    const limit = filters.limit || 50;
    // Fetch more than needed since we'll sort in-memory
    query = query.limit(limit * 2);
    const { data, error } = await query;
    if (error) throw new Error(`Search failed: ${error.message}`);
    const results = (data || []) as any[];
    results.sort((a: any, b: any) => {
      const scoreA = a.ask_readiness?.[filters.goal!]?.score ?? -1;
      const scoreB = b.ask_readiness?.[filters.goal!]?.score ?? -1;
      return filters.sort_order === 'asc' ? scoreA - scoreB : scoreB - scoreA;
    });
    return results.slice(0, limit);
  }

  const sortColumn = getSortColumn(filters.sort_by);
  const ascending = filters.sort_order === 'asc';
  query = query.order(sortColumn, { ascending, nullsFirst: false });

  // Secondary sort: comms_last_date for familiarity sort, familiarity_rating for default
  if (filters.sort_by === 'familiarity') {
    query = query.order('comms_last_date', { ascending: false, nullsFirst: false });
  } else if (!filters.sort_by || filters.sort_by === 'proximity') {
    // Default: familiarity_rating DESC as secondary
    query = query.order('comms_last_date', { ascending: false, nullsFirst: false });
  }

  const limit = filters.limit || 50;
  query = query.limit(limit);

  const { data, error } = await query;
  if (error) throw new Error(`Search failed: ${error.message}`);

  return data || [];
}

/**
 * Execute a hybrid (semantic + structured) search.
 * Uses the hybrid_contact_search RPC, then fetches full profiles.
 */
async function executeHybridSearch(filters: FilterState) {
  const matchCount = filters.limit || 50;
  const queryEmbedding = await generateEmbedding768(filters.semantic_query!);

  const { data, error } = await supabase.rpc('hybrid_contact_search', {
    query_text: filters.semantic_query!,
    query_embedding: queryEmbedding,
    filter_proximity_min: filters.proximity_min || 0,
    filter_capacity_min: filters.capacity_min || 0,
    semantic_weight: 1.0,
    keyword_weight: 1.0,
    match_count: matchCount,
    rrf_k: 60,
  });

  if (error) throw new Error(`Hybrid search failed: ${error.message}`);

  const ids = (data || []).map((r: { id: number }) => r.id);
  if (ids.length === 0) return [];

  const { data: profiles, error: profileError } = await supabase
    .from('contacts')
    .select(NETWORK_SELECT_COLS)
    .in('id', ids);

  if (profileError) throw new Error(`Profile fetch failed: ${profileError.message}`);

  // Merge hybrid scores and sort by them
  const profileList = (profiles || []) as any[];
  const scoreMap = new Map((data || []).map((r: any) => [r.id, r.score]));
  const merged = profileList
    .map((p: any) => ({ ...p, hybrid_score: scoreMap.get(p.id) || 0 }))
    .sort((a: any, b: any) => b.hybrid_score - a.hybrid_score);

  // Apply additional filters that hybrid RPC doesn't handle
  return applyPostFilters(merged, filters);
}

/**
 * Apply filters that the hybrid RPC doesn't natively support.
 * The RPC only handles proximity_min and capacity_min — array filters
 * like tiers, outdoorithm_fit, kindora_type need post-filtering.
 */
function applyPostFilters(contacts: any[], filters: FilterState): any[] {
  let result = contacts;

  if (filters.proximity_tiers && filters.proximity_tiers.length > 0) {
    result = result.filter((c: any) => filters.proximity_tiers!.includes(c.ai_proximity_tier));
  }
  if (filters.capacity_tiers && filters.capacity_tiers.length > 0) {
    result = result.filter((c: any) => filters.capacity_tiers!.includes(c.ai_capacity_tier));
  }
  if (filters.outdoorithm_fit && filters.outdoorithm_fit.length > 0) {
    result = result.filter((c: any) => filters.outdoorithm_fit!.includes(c.ai_outdoorithm_fit));
  }
  if (filters.kindora_type && filters.kindora_type.length > 0) {
    result = result.filter((c: any) => filters.kindora_type!.includes(c.ai_kindora_prospect_type));
  }
  if (filters.company_keyword) {
    const kw = filters.company_keyword.toLowerCase();
    result = result.filter((c: any) => c.company?.toLowerCase().includes(kw));
  }
  if (filters.name_search) {
    const term = filters.name_search.toLowerCase();
    result = result.filter(
      (c: any) =>
        c.first_name?.toLowerCase().includes(term) || c.last_name?.toLowerCase().includes(term)
    );
  }
  if (filters.location_state) {
    const st = filters.location_state.toLowerCase();
    result = result.filter((c: any) => c.state?.toLowerCase().includes(st));
  }
  if (filters.familiarity_min != null) {
    result = result.filter((c: any) => (c.familiarity_rating ?? 0) >= filters.familiarity_min!);
  }
  if (filters.has_comms) {
    result = result.filter((c: any) => (c.comms_thread_count ?? 0) > 0);
  }
  if (filters.comms_since) {
    result = result.filter((c: any) => c.comms_last_date && c.comms_last_date >= filters.comms_since!);
  }

  return result;
}

function getSortColumn(sortBy?: string): string {
  switch (sortBy) {
    case 'capacity':
      return 'ai_capacity_score';
    case 'name':
      return 'last_name';
    case 'company':
      return 'company';
    case 'familiarity':
      return 'familiarity_rating';
    case 'comms_recency':
      return 'comms_last_date';
    case 'proximity':
      return 'ai_proximity_score';
    default:
      return 'familiarity_rating';
  }
}

export async function POST(req: Request) {
  try {
    const { filters } = (await req.json()) as { filters: FilterState };

    if (!filters || typeof filters !== 'object') {
      return new Response(
        JSON.stringify({ error: 'Missing or invalid filters parameter' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    let contacts: any[];

    if (filters.semantic_query) {
      contacts = await executeHybridSearch(filters);
    } else {
      contacts = await executeStructuredSearch(filters);
    }

    return new Response(
      JSON.stringify({
        contacts,
        total_count: contacts.length,
        filters_applied: filters,
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error: any) {
    console.error('Search execution error:', error);
    return new Response(
      JSON.stringify({ error: error.message || 'Search failed' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
