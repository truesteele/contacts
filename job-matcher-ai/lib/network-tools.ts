import Anthropic from '@anthropic-ai/sdk';
import { supabase, NetworkContact } from './supabase';
import { generateEmbedding768 } from './openai';

const NETWORK_SELECT_COLS =
  'id, first_name, last_name, company, position, city, state, email, linkedin_url, headline, ' +
  'ai_proximity_score, ai_proximity_tier, ai_capacity_score, ai_capacity_tier, ' +
  'ai_kindora_prospect_score, ai_kindora_prospect_type, ai_outdoorithm_fit, ' +
  'familiarity_rating, comms_last_date, comms_thread_count, ask_readiness';

export const networkTools: Anthropic.Tool[] = [
  {
    name: 'search_network',
    description:
      'Search contacts with structured filters. Use for questions about specific segments: fundraiser invites, Kindora prospects, contacts at a company, contacts in a city, etc. Returns contacts sorted by familiarity rating by default.',
    input_schema: {
      type: 'object' as const,
      properties: {
        familiarity_min: {
          type: 'number',
          description: 'Minimum familiarity rating (0-4). 0=stranger, 1=recognize, 2=know, 3=good relationship, 4=close/trusted.',
        },
        has_comms: {
          type: 'boolean',
          description: 'If true, only return contacts with email communication history.',
        },
        comms_since: {
          type: 'string',
          description: 'Only contacts communicated with since this date (YYYY-MM-DD). E.g., "2025-01-01".',
        },
        proximity_min: {
          type: 'number',
          description: 'Minimum proximity score (0-100). Legacy — prefer familiarity_min.',
        },
        proximity_tiers: {
          type: 'array',
          items: { type: 'string' },
          description:
            'Filter by specific tiers: "inner_circle", "close", "warm", "familiar", "acquaintance", "distant"',
        },
        capacity_min: {
          type: 'number',
          description: 'Minimum giving capacity score (0-100). E.g., 70 for major donors.',
        },
        capacity_tiers: {
          type: 'array',
          items: { type: 'string' },
          description: 'Filter by capacity tiers: "major_donor", "mid_level", "grassroots", "unknown"',
        },
        outdoorithm_fit: {
          type: 'array',
          items: { type: 'string' },
          description: 'Filter by Outdoorithm Collective fit: "high", "medium", "low", "none"',
        },
        kindora_type: {
          type: 'array',
          items: { type: 'string' },
          description:
            'Filter by Kindora prospect type: "enterprise_buyer", "champion", "influencer", "not_relevant"',
        },
        company_keyword: {
          type: 'string',
          description: 'Search for contacts at a specific company (partial match). E.g., "Google", "San Francisco Foundation"',
        },
        name_search: {
          type: 'string',
          description: 'Search for a specific person by name (partial match on first or last name)',
        },
        location_state: {
          type: 'string',
          description: 'Filter by state. E.g., "California", "New York"',
        },
        sort_by: {
          type: 'string',
          enum: ['familiarity', 'comms_recency', 'capacity', 'proximity', 'name'],
          description: 'Sort results by this field (default: familiarity).',
        },
        limit: {
          type: 'number',
          description: 'Maximum results to return (default 50). Use higher values (100-200) when the user wants a comprehensive list.',
        },
      },
      required: [],
    },
  },
  {
    name: 'semantic_search',
    description:
      'Find contacts by topic or interests using natural language. Uses AI embeddings to find people whose interests, skills, or background match the query — even if exact keywords don\'t appear in their profile. Best for: "who cares about outdoor equity", "people in philanthropy tech", "education reform advocates".',
    input_schema: {
      type: 'object' as const,
      properties: {
        query: {
          type: 'string',
          description:
            'Natural language description of what you\'re looking for. E.g., "outdoor equity, nature access, environmental justice"',
        },
        search_type: {
          type: 'string',
          enum: ['interests', 'profile'],
          description:
            'Which embedding to search. "interests" (default) matches on topics/affinities. "profile" matches on career/background similarity.',
        },
        match_count: {
          type: 'number',
          description: 'Number of results (default 30). Use higher values (50-100) for comprehensive lists.',
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'find_similar',
    description:
      'Find contacts similar to a specific person. Provide a contact ID to find people with similar profiles or interests.',
    input_schema: {
      type: 'object' as const,
      properties: {
        contact_id: {
          type: 'number',
          description: 'The contact ID to find similar people for',
        },
        search_type: {
          type: 'string',
          enum: ['profile', 'interests'],
          description: '"profile" (default) finds similar career backgrounds. "interests" finds similar topical interests.',
        },
        count: {
          type: 'number',
          description: 'Number of similar contacts to return (default 20)',
        },
      },
      required: ['contact_id'],
    },
  },
  {
    name: 'hybrid_search',
    description:
      'Combined semantic + keyword search with optional structured filters. Uses Reciprocal Rank Fusion to combine results. Best for broad queries that benefit from both meaning-based and keyword matching.',
    input_schema: {
      type: 'object' as const,
      properties: {
        query: {
          type: 'string',
          description: 'Free text search query. E.g., "philanthropy education technology"',
        },
        proximity_min: {
          type: 'number',
          description: 'Minimum proximity score filter (default 0)',
        },
        capacity_min: {
          type: 'number',
          description: 'Minimum capacity score filter (default 0)',
        },
        match_count: {
          type: 'number',
          description: 'Number of results (default 40). Use higher values for comprehensive lists.',
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'get_contact_detail',
    description:
      'Get full profile details and AI tags for a specific contact. Use after searching to dive deep on a specific person. Returns scores, topics, personalization hooks, and outreach context.',
    input_schema: {
      type: 'object' as const,
      properties: {
        contact_id: {
          type: 'number',
          description: 'The contact ID to fetch details for',
        },
      },
      required: ['contact_id'],
    },
  },
  {
    name: 'get_outreach_context',
    description:
      'Get personalization hooks, suggested opener, and talking points for outreach to a specific contact. Use this when drafting messages or emails.',
    input_schema: {
      type: 'object' as const,
      properties: {
        contact_id: {
          type: 'number',
          description: 'The contact ID to get outreach context for',
        },
      },
      required: ['contact_id'],
    },
  },
  {
    name: 'goal_search',
    description:
      'Find contacts ranked by AI ask-readiness for a specific goal (e.g., fundraising, sales). Returns contacts with donor psychology reasoning for why they are ready (or not) for an ask, including recommended approach, suggested ask range, and personalization angles. Use this FIRST for any fundraising or outreach planning query.',
    input_schema: {
      type: 'object' as const,
      properties: {
        goal: {
          type: 'string',
          enum: ['outdoorithm_fundraising', 'kindora_sales'],
          description: 'The goal to rank contacts for.',
        },
        tier: {
          type: 'string',
          enum: ['ready_now', 'cultivate_first', 'long_term', 'not_a_fit', 'all'],
          description: 'Filter by ask-readiness tier. Default: "all".',
        },
        min_familiarity: {
          type: 'number',
          description: 'Minimum familiarity rating (0-4). E.g., 2 to exclude strangers.',
        },
        limit: {
          type: 'number',
          description: 'Maximum results to return (default 50). Use higher values (100+) for comprehensive lists.',
        },
      },
      required: ['goal'],
    },
  },
  {
    name: 'export_contacts',
    description:
      'Export a list of contacts to CSV for download. Provide the contact IDs from a previous search result.',
    input_schema: {
      type: 'object' as const,
      properties: {
        contact_ids: {
          type: 'array',
          items: { type: 'number' },
          description: 'Array of contact IDs to export',
        },
        label: {
          type: 'string',
          description: 'Label for the export file (e.g., "outdoorithm_fundraiser_invites")',
        },
      },
      required: ['contact_ids'],
    },
  },
];

// ── Tool Implementations ─────────────────────────────────────────────

async function searchNetwork(input: any): Promise<any> {
  let query = supabase
    .from('contacts')
    .select(NETWORK_SELECT_COLS);

  if (input.familiarity_min != null) {
    query = query.gte('familiarity_rating', input.familiarity_min);
  }
  if (input.has_comms) {
    query = query.gt('comms_thread_count', 0);
  }
  if (input.comms_since) {
    query = query.gte('comms_last_date', input.comms_since);
  }
  if (input.proximity_min != null) {
    query = query.gte('ai_proximity_score', input.proximity_min);
  }
  if (input.capacity_min != null) {
    query = query.gte('ai_capacity_score', input.capacity_min);
  }
  if (input.proximity_tiers?.length > 0) {
    query = query.in('ai_proximity_tier', input.proximity_tiers);
  }
  if (input.capacity_tiers?.length > 0) {
    query = query.in('ai_capacity_tier', input.capacity_tiers);
  }
  if (input.outdoorithm_fit?.length > 0) {
    query = query.in('ai_outdoorithm_fit', input.outdoorithm_fit);
  }
  if (input.kindora_type?.length > 0) {
    query = query.in('ai_kindora_prospect_type', input.kindora_type);
  }
  if (input.company_keyword) {
    query = query.ilike('company', `%${input.company_keyword}%`);
  }
  if (input.name_search) {
    const term = `%${input.name_search}%`;
    query = query.or(`first_name.ilike.${term},last_name.ilike.${term}`);
  }
  if (input.location_state) {
    query = query.ilike('state', `%${input.location_state}%`);
  }

  // Determine sort column
  const sortColumn = (() => {
    switch (input.sort_by) {
      case 'comms_recency': return 'comms_last_date';
      case 'capacity': return 'ai_capacity_score';
      case 'proximity': return 'ai_proximity_score';
      case 'name': return 'last_name';
      case 'familiarity':
      default: return 'familiarity_rating';
    }
  })();

  const limit = input.limit || 50;
  query = query
    .order(sortColumn, { ascending: false, nullsFirst: false })
    .order('comms_last_date', { ascending: false, nullsFirst: false })
    .limit(limit);

  const { data, error } = await query;
  if (error) throw new Error(`Search failed: ${error.message}`);

  return {
    count: data?.length || 0,
    contacts: data || [],
  };
}

async function semanticSearch(input: any): Promise<any> {
  const searchType = input.search_type || 'interests';
  const matchCount = input.match_count || 30;

  const queryEmbedding = await generateEmbedding768(input.query);

  const rpcName =
    searchType === 'profile'
      ? 'match_contacts_by_profile'
      : 'match_contacts_by_interests';

  const { data, error } = await supabase.rpc(rpcName, {
    query_embedding: queryEmbedding,
    match_threshold: 0.3,
    match_count: matchCount,
  });

  if (error) throw new Error(`Semantic search failed: ${error.message}`);

  return {
    query: input.query,
    search_type: searchType,
    count: data?.length || 0,
    contacts: data || [],
  };
}

async function findSimilar(input: any): Promise<any> {
  const searchType = input.search_type || 'profile';
  const count = input.count || 20;
  const embeddingCol = searchType === 'profile' ? 'profile_embedding' : 'interests_embedding';

  const { data: contact, error: fetchError } = await supabase
    .from('contacts')
    .select(`id, first_name, last_name, company, ${embeddingCol}`)
    .eq('id', input.contact_id)
    .single();

  if (fetchError || !contact) {
    throw new Error(`Contact ${input.contact_id} not found`);
  }

  const embedding = (contact as any)[embeddingCol];
  if (!embedding) {
    return { error: true, message: `Contact has no ${searchType} embedding` };
  }

  const rpcName =
    searchType === 'profile'
      ? 'match_contacts_by_profile'
      : 'match_contacts_by_interests';

  const { data, error } = await supabase.rpc(rpcName, {
    query_embedding: embedding,
    match_threshold: 0.4,
    match_count: count + 1,
  });

  if (error) throw new Error(`Find similar failed: ${error.message}`);

  // Exclude the source contact from results
  const results = (data || []).filter((r: any) => r.id !== input.contact_id);

  return {
    source: `${contact.first_name} ${contact.last_name}` + (contact.company ? ` (${contact.company})` : ''),
    search_type: searchType,
    count: results.length,
    contacts: results.slice(0, count),
  };
}

async function hybridSearch(input: any): Promise<any> {
  const matchCount = input.match_count || 40;
  const queryEmbedding = await generateEmbedding768(input.query);

  const { data, error } = await supabase.rpc('hybrid_contact_search', {
    query_text: input.query,
    query_embedding: queryEmbedding,
    filter_proximity_min: input.proximity_min || 0,
    filter_capacity_min: input.capacity_min || 0,
    semantic_weight: 1.0,
    keyword_weight: 1.0,
    match_count: matchCount,
    rrf_k: 60,
  });

  if (error) throw new Error(`Hybrid search failed: ${error.message}`);

  // The RPC returns only id, first_name, last_name, score. Fetch full profiles.
  const ids = (data || []).map((r: any) => r.id);
  if (ids.length === 0) {
    return { query: input.query, count: 0, contacts: [] };
  }

  const { data: profiles } = await supabase
    .from('contacts')
    .select(NETWORK_SELECT_COLS)
    .in('id', ids);

  // Merge scores back into profiles
  const scoreMap = new Map((data || []).map((r: any) => [r.id, r.score]));
  const merged = (profiles || [])
    .map((p: any) => ({ ...p, hybrid_score: scoreMap.get(p.id) || 0 }))
    .sort((a: any, b: any) => b.hybrid_score - a.hybrid_score);

  return {
    query: input.query,
    count: merged.length,
    contacts: merged,
  };
}

async function getContactDetail(input: any): Promise<any> {
  const { data, error } = await supabase
    .from('contacts')
    .select(
      'id, first_name, last_name, company, position, city, state, email, personal_email, work_email, ' +
        'linkedin_url, headline, summary, ' +
        'ai_proximity_score, ai_proximity_tier, ai_capacity_score, ai_capacity_tier, ' +
        'ai_kindora_prospect_score, ai_kindora_prospect_type, ai_outdoorithm_fit, ai_tags, ' +
        'familiarity_rating, comms_last_date, comms_thread_count, communication_history, ' +
        'shared_institutions, ask_readiness, fec_donations, real_estate_data'
    )
    .eq('id', input.contact_id)
    .single();

  if (error || !data) {
    throw new Error(`Contact ${input.contact_id} not found`);
  }

  const contact = data as any;
  // Extract key subfields from ai_tags to avoid sending the full blob
  const tags = contact.ai_tags || {};

  // Extract recent threads from communication_history
  const commsHistory = contact.communication_history || {};
  const recentThreads = (commsHistory.recent_threads || commsHistory.threads || []).slice(0, 5);

  return {
    ...contact,
    ai_tags: undefined,
    communication_history: undefined,
    ai_tags_summary: {
      relationship_proximity: tags.relationship_proximity,
      giving_capacity: tags.giving_capacity,
      topical_affinity: tags.topical_affinity,
      sales_fit: tags.sales_fit,
      outreach_context: tags.outreach_context,
    },
    // Communication history summary
    comms_relationship_summary: commsHistory.relationship_summary || null,
    comms_recent_threads: recentThreads,
  };
}

async function getOutreachContext(input: any): Promise<any> {
  const { data, error } = await supabase
    .from('contacts')
    .select(
      'id, first_name, last_name, company, position, headline, city, state, email, linkedin_url, ' +
        'ai_proximity_score, ai_proximity_tier, ai_capacity_tier, ai_tags, ' +
        'familiarity_rating, comms_last_date, comms_thread_count, communication_history, ' +
        'shared_institutions, ask_readiness'
    )
    .eq('id', input.contact_id)
    .single();

  if (error || !data) {
    throw new Error(`Contact ${input.contact_id} not found`);
  }

  const contact = data as any;
  const tags = contact.ai_tags || {};
  const outreach = tags.outreach_context || {};
  const proximity = tags.relationship_proximity || {};
  const affinity = tags.topical_affinity || {};
  const commsHistory = contact.communication_history || {};

  // Build structured institutional overlap from new JSONB or fall back to ai_tags
  const structuredOverlap = Array.isArray(contact.shared_institutions)
    ? contact.shared_institutions.map((inst: any) => ({
        name: inst.name,
        type: inst.type,
        temporal_overlap: inst.temporal_overlap,
        justin_period: inst.justin_period,
        contact_period: inst.contact_period,
        depth: inst.depth,
      }))
    : [];

  // Extract last email context
  const recentThreads = (commsHistory.recent_threads || commsHistory.threads || []).slice(0, 3);
  const lastThread = recentThreads[0] || null;

  return {
    name: `${contact.first_name} ${contact.last_name}`,
    company: contact.company,
    position: contact.position,
    headline: contact.headline,
    location: [contact.city, contact.state].filter(Boolean).join(', '),
    email: contact.email,
    linkedin_url: contact.linkedin_url,
    // Familiarity (primary relationship signal)
    familiarity_rating: contact.familiarity_rating,
    // Legacy proximity (supplementary)
    proximity_tier: contact.ai_proximity_tier,
    proximity_score: contact.ai_proximity_score,
    capacity_tier: contact.ai_capacity_tier,
    // Shared context — structured overlap with temporal data
    shared_context: {
      shared_employers: proximity.shared_employers || [],
      shared_schools: proximity.shared_schools || [],
      shared_boards: proximity.shared_boards || [],
    },
    institutional_overlap: structuredOverlap,
    // Communication history
    last_email_date: contact.comms_last_date,
    email_thread_count: contact.comms_thread_count,
    last_email_subject: lastThread?.subject || null,
    relationship_summary: commsHistory.relationship_summary || null,
    // Ask-readiness (if scored)
    ask_readiness: contact.ask_readiness || null,
    // Topics and interests
    topics: (affinity.topics || []).slice(0, 8),
    primary_interests: affinity.primary_interests || [],
    talking_points: affinity.talking_points || [],
    personalization_hooks: outreach.personalization_hooks || [],
    suggested_opener: outreach.suggested_opener || '',
    best_approach: outreach.best_approach || '',
  };
}

async function goalSearch(input: any): Promise<any> {
  const goal = input.goal;
  const tier = input.tier || 'all';
  const minFamiliarity = input.min_familiarity;
  const limit = input.limit || 50;

  // Fetch contacts that have ask_readiness data for this goal
  // Supabase can't sort by JSONB nested path, so we fetch more rows and sort in JS
  const fetchLimit = limit * 3; // Over-fetch to allow for filtering

  let query = supabase
    .from('contacts')
    .select(
      NETWORK_SELECT_COLS + ', shared_institutions, communication_history'
    )
    .not('ask_readiness', 'is', null);

  if (minFamiliarity != null) {
    query = query.gte('familiarity_rating', minFamiliarity);
  }

  query = query
    .order('familiarity_rating', { ascending: false, nullsFirst: false })
    .limit(fetchLimit);

  const { data, error } = await query;
  if (error) throw new Error(`Goal search failed: ${error.message}`);

  // Filter to contacts that have scoring for this specific goal, and by tier
  let results = (data || []).filter((c: any) => {
    const goalData = c.ask_readiness?.[goal];
    if (!goalData || goalData.score == null) return false;
    if (tier !== 'all' && goalData.tier !== tier) return false;
    return true;
  });

  // Sort by ask_readiness score DESC for this goal
  results.sort((a: any, b: any) => {
    const scoreA = a.ask_readiness?.[goal]?.score ?? 0;
    const scoreB = b.ask_readiness?.[goal]?.score ?? 0;
    return scoreB - scoreA;
  });

  // Trim to limit
  results = results.slice(0, limit);

  // Shape the response to include ask_readiness reasoning inline
  const contacts = results.map((c: any) => {
    const goalData = c.ask_readiness[goal];
    return {
      id: c.id,
      first_name: c.first_name,
      last_name: c.last_name,
      company: c.company,
      position: c.position,
      city: c.city,
      state: c.state,
      email: c.email,
      linkedin_url: c.linkedin_url,
      headline: c.headline,
      familiarity_rating: c.familiarity_rating,
      comms_last_date: c.comms_last_date,
      comms_thread_count: c.comms_thread_count,
      ai_capacity_tier: c.ai_capacity_tier,
      ai_outdoorithm_fit: c.ai_outdoorithm_fit,
      ask_readiness_score: goalData.score,
      ask_readiness_tier: goalData.tier,
      reasoning: goalData.reasoning,
      recommended_approach: goalData.recommended_approach,
      ask_timing: goalData.ask_timing,
      cultivation_needed: goalData.cultivation_needed,
      suggested_ask_range: goalData.suggested_ask_range,
      personalization_angle: goalData.personalization_angle,
      risk_factors: goalData.risk_factors,
    };
  });

  return {
    goal,
    tier_filter: tier,
    count: contacts.length,
    contacts,
  };
}

function escapeCSVValue(val: any): string {
  if (val == null) return '';
  const str = String(val);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

async function exportContacts(input: any): Promise<any> {
  const ids = input.contact_ids || [];
  if (ids.length === 0) {
    return { error: true, message: 'No contact IDs provided' };
  }

  const { data, error } = await supabase
    .from('contacts')
    .select(NETWORK_SELECT_COLS)
    .in('id', ids);

  if (error) throw new Error(`Export failed: ${error.message}`);

  const contacts = data || [];
  const headers = [
    'First Name', 'Last Name', 'Email', 'LinkedIn URL', 'Company', 'Position',
    'City', 'State', 'Proximity Score', 'Proximity Tier', 'Capacity Score',
    'Capacity Tier', 'Kindora Score', 'Kindora Type', 'Outdoorithm Fit',
  ];

  const rows = contacts.map((c: any) =>
    [
      c.first_name, c.last_name, c.email, c.linkedin_url, c.company, c.position,
      c.city, c.state, c.ai_proximity_score, c.ai_proximity_tier, c.ai_capacity_score,
      c.ai_capacity_tier, c.ai_kindora_prospect_score, c.ai_kindora_prospect_type,
      c.ai_outdoorithm_fit,
    ].map(escapeCSVValue).join(',')
  );

  const csvContent = [headers.join(','), ...rows].join('\n');
  const timestamp = new Date().toISOString().split('T')[0];
  const label = input.label ? input.label.replace(/[^a-z0-9_-]/gi, '_') : 'network_export';
  const filename = `${label}_${timestamp}.csv`;

  return {
    csv_content: csvContent,
    filename,
    row_count: contacts.length,
  };
}

// ── Tool Executor ────────────────────────────────────────────────────

export async function executeNetworkToolCall(
  toolName: string,
  toolInput: any
): Promise<any> {
  console.log(`[Network] Executing tool: ${toolName}`, toolInput);
  try {
    switch (toolName) {
      case 'search_network':
        return await searchNetwork(toolInput);
      case 'semantic_search':
        return await semanticSearch(toolInput);
      case 'find_similar':
        return await findSimilar(toolInput);
      case 'hybrid_search':
        return await hybridSearch(toolInput);
      case 'get_contact_detail':
        return await getContactDetail(toolInput);
      case 'get_outreach_context':
        return await getOutreachContext(toolInput);
      case 'goal_search':
        return await goalSearch(toolInput);
      case 'export_contacts':
        return await exportContacts(toolInput);
      default:
        throw new Error(`Unknown network tool: ${toolName}`);
    }
  } catch (error: any) {
    console.error(`[Network] Error in ${toolName}:`, error);
    return { error: true, message: error.message || 'Tool execution failed' };
  }
}
