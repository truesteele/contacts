import Anthropic from '@anthropic-ai/sdk';
import { supabase, NetworkContact } from './supabase';
import { generateEmbedding768 } from './openai';

const NETWORK_SELECT_COLS =
  'id, first_name, last_name, company, position, city, state, email, linkedin_url, headline, ' +
  'ai_proximity_score, ai_proximity_tier, ai_capacity_score, ai_capacity_tier, ' +
  'ai_kindora_prospect_score, ai_kindora_prospect_type, ai_outdoorithm_fit, ' +
  'familiarity_rating, comms_last_date, comms_thread_count, ask_readiness';

const CANDIDATE_SELECT_COLS =
  'id, first_name, last_name, company, position, city, state, email, linkedin_url, headline, summary, ' +
  'familiarity_rating, comms_last_date, comms_thread_count, comms_closeness, ' +
  'enrich_current_title, enrich_current_company, enrich_current_since, ' +
  'enrich_titles_held, enrich_companies_worked, enrich_skills, enrich_schools, ' +
  'enrich_board_positions, enrich_volunteer_orgs, enrich_total_experience_years, ' +
  'enrich_employment, enrich_education';

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
        title_keyword: {
          type: 'string',
          description:
            'Search for contacts who have held a title containing this keyword (searches enrich_titles_held array and headline). E.g., "marketing", "engineering", "product".',
        },
        skill_keyword: {
          type: 'string',
          description:
            'Search for contacts with a specific LinkedIn skill (searches enrich_skills array). E.g., "python", "fundraising", "seo".',
        },
        school_keyword: {
          type: 'string',
          description:
            'Search for contacts who attended a specific school (searches enrich_schools array). E.g., "Harvard", "Stanford".',
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
  {
    name: 'job_candidate_search',
    description:
      'Find contacts who could be candidates for a specific job role. Searches across enrichment data: career titles (enrich_titles_held), skills (enrich_skills), companies worked (enrich_companies_worked), education (enrich_schools), board positions, volunteer orgs, and LinkedIn summary. Combines semantic profile-embedding search with structured filtering on title keywords, skills, experience years, and location. Use when Justin asks "who in my network would be good for this role?" or "find candidates for X job."',
    input_schema: {
      type: 'object' as const,
      properties: {
        job_description: {
          type: 'string',
          description:
            'Natural language description of the role. Used for semantic search against profile embeddings. E.g., "Director of Marketing at a nonprofit focused on worker support, 10+ years experience, multi-channel growth, category creation, Bay Area"',
        },
        title_keywords: {
          type: 'array',
          items: { type: 'string' },
          description:
            'Keywords to match against titles held across their career (enrich_titles_held). E.g., ["marketing", "brand", "growth", "communications"]. Matches partial substrings.',
        },
        seniority_keywords: {
          type: 'array',
          items: { type: 'string' },
          description:
            'Seniority-level keywords that must co-occur with title_keywords. E.g., ["director", "vp", "head", "chief", "senior"]. If omitted, all seniority levels match.',
        },
        skill_keywords: {
          type: 'array',
          items: { type: 'string' },
          description:
            'Keywords to match against LinkedIn skills (enrich_skills). E.g., ["seo", "content strategy", "digital marketing"].',
        },
        company_keywords: {
          type: 'array',
          items: { type: 'string' },
          description:
            'Keywords to match against companies worked at (enrich_companies_worked). E.g., ["google", "facebook", "year up"]. Useful for finding nonprofit or industry experience.',
        },
        industry_signals: {
          type: 'array',
          items: { type: 'string' },
          description:
            'Keywords to search in headline, summary, company names, board positions, and volunteer orgs for industry/sector signals. E.g., ["nonprofit", "social impact", "equity", "mission-driven", "worker"].',
        },
        location_states: {
          type: 'array',
          items: { type: 'string' },
          description:
            'Filter to contacts in these states. E.g., ["California", "New York", "Illinois"]. Leave empty for all locations.',
        },
        min_familiarity: {
          type: 'number',
          description: 'Minimum familiarity rating (0-4). Default 1 (at least recognizes them).',
        },
        match_count: {
          type: 'number',
          description: 'Maximum candidates to return (default 30).',
        },
      },
      required: ['job_description'],
    },
  },
];

// ── Tool Implementations ─────────────────────────────────────────────

async function searchNetwork(input: any): Promise<any> {
  // Use enriched columns if title/skill/school filters are present
  const needsEnrichment = input.title_keyword || input.skill_keyword || input.school_keyword;
  const selectCols = needsEnrichment ? CANDIDATE_SELECT_COLS : NETWORK_SELECT_COLS;
  let query = supabase
    .from('contacts')
    .select(selectCols);

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
    const sanitized = String(input.name_search).replace(/[,().]/g, ' ').trim();
    if (sanitized) {
      const term = `%${sanitized}%`;
      query = query.or(`first_name.ilike.${term},last_name.ilike.${term}`);
    }
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
  // Over-fetch when post-filtering on enrichment arrays, since Supabase limit runs before our filter
  const fetchLimit = needsEnrichment ? Math.max(limit * 5, 500) : limit;
  query = query
    .order(sortColumn, { ascending: false, nullsFirst: false })
    .order('comms_last_date', { ascending: false, nullsFirst: false })
    .limit(fetchLimit);

  const { data, error } = await query;
  if (error) throw new Error(`Search failed: ${error.message}`);

  let results = data || [];

  // Post-filter on enrichment array fields (not supported by Supabase JS client)
  if (input.title_keyword) {
    const kw = input.title_keyword.toLowerCase();
    results = results.filter((c: any) => {
      const titles: string[] = c.enrich_titles_held || [];
      const headline = (c.headline || '').toLowerCase();
      return titles.some((t: string) => t.toLowerCase().includes(kw)) || headline.includes(kw);
    });
  }
  if (input.skill_keyword) {
    const kw = input.skill_keyword.toLowerCase();
    results = results.filter((c: any) => {
      const skills: string[] = c.enrich_skills || [];
      return skills.some((s: string) => s.toLowerCase().includes(kw));
    });
  }
  if (input.school_keyword) {
    const kw = input.school_keyword.toLowerCase();
    results = results.filter((c: any) => {
      const schools: string[] = c.enrich_schools || [];
      return schools.some((s: string) => s.toLowerCase().includes(kw));
    });
  }

  // Trim to requested limit after post-filtering
  if (results.length > limit) {
    results = results.slice(0, limit);
  }

  return {
    count: results.length,
    contacts: results,
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
        'shared_institutions, ask_readiness, fec_donations, real_estate_data, ' +
        'enrich_current_title, enrich_current_company, enrich_current_since, ' +
        'enrich_titles_held, enrich_companies_worked, enrich_skills, enrich_schools, ' +
        'enrich_board_positions, enrich_volunteer_orgs, enrich_total_experience_years, ' +
        'comms_closeness, comms_momentum'
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
    // Career enrichment data
    career: {
      current_title: contact.enrich_current_title,
      current_company: contact.enrich_current_company,
      current_since: contact.enrich_current_since,
      total_experience_years: contact.enrich_total_experience_years,
      titles_held: contact.enrich_titles_held,
      companies_worked: contact.enrich_companies_worked,
      skills: contact.enrich_skills,
      schools: contact.enrich_schools,
      board_positions: contact.enrich_board_positions,
      volunteer_orgs: contact.enrich_volunteer_orgs,
    },
    comms_closeness: contact.comms_closeness,
    comms_momentum: contact.comms_momentum,
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

async function jobCandidateSearch(input: any): Promise<any> {
  const matchCount = input.match_count || 30;
  const minFamiliarity = input.min_familiarity ?? 1;
  const titleKeywords = (input.title_keywords || []).map((k: string) => k.toLowerCase());
  const seniorityKeywords = (input.seniority_keywords || []).map((k: string) => k.toLowerCase());
  const skillKeywords = (input.skill_keywords || []).map((k: string) => k.toLowerCase());
  const companyKeywords = (input.company_keywords || []).map((k: string) => k.toLowerCase());
  const industrySignals = (input.industry_signals || []).map((k: string) => k.toLowerCase());
  const locationStates = (input.location_states || []).map((s: string) => s.toLowerCase());

  // Step 1: Semantic search on profile embeddings for the job description
  const queryEmbedding = await generateEmbedding768(input.job_description);
  const { data: semanticHits, error: semError } = await supabase.rpc('match_contacts_by_profile', {
    query_embedding: queryEmbedding,
    match_threshold: 0.25,
    match_count: Math.max(matchCount * 4, 200), // Over-fetch for post-filtering
  });
  if (semError) throw new Error(`Semantic search failed: ${semError.message}`);

  const semanticIds = (semanticHits || []).map((r: any) => r.id);
  const semanticScoreMap = new Map((semanticHits || []).map((r: any) => [r.id, r.similarity]));

  if (semanticIds.length === 0) {
    return { job_description: input.job_description, count: 0, candidates: [] };
  }

  // Step 2: Fetch full enrichment profiles for semantic matches
  // Supabase .in() has a practical limit, so batch if needed
  const batchSize = 200;
  let allProfiles: any[] = [];
  for (let i = 0; i < semanticIds.length; i += batchSize) {
    const batch = semanticIds.slice(i, i + batchSize);
    const { data: profiles, error: profError } = await supabase
      .from('contacts')
      .select(CANDIDATE_SELECT_COLS)
      .in('id', batch)
      .gte('familiarity_rating', minFamiliarity);
    if (profError) throw new Error(`Profile fetch failed: ${profError.message}`);
    allProfiles.push(...(profiles || []));
  }

  // Step 3: Score each candidate based on structured enrichment data
  const scored = allProfiles.map((c: any) => {
    let score = 0;
    const reasons: string[] = [];
    const titlesHeld: string[] = (c.enrich_titles_held || []).map((t: string) => t.toLowerCase());
    const skills: string[] = (c.enrich_skills || []).map((s: string) => s.toLowerCase());
    const companies: string[] = (c.enrich_companies_worked || []).map((co: string) => co.toLowerCase());
    const schools: string[] = (c.enrich_schools || []).map((s: string) => s.toLowerCase());
    const boards: string[] = (c.enrich_board_positions || []).map((b: string) => b.toLowerCase());
    const volunteerOrgs: string[] = (c.enrich_volunteer_orgs || []).map((v: string) => v.toLowerCase());
    const headline = (c.headline || '').toLowerCase();
    const summary = (c.summary || '').toLowerCase();

    // Title matching: find titles that match both title keywords AND seniority keywords
    const matchingTitles: string[] = [];
    for (const title of titlesHeld) {
      const hasTitle = titleKeywords.length === 0 || titleKeywords.some((k: string) => title.includes(k));
      const hasSeniority = seniorityKeywords.length === 0 || seniorityKeywords.some((k: string) => title.includes(k));
      if (hasTitle && hasSeniority && titleKeywords.length > 0) {
        matchingTitles.push(title);
      }
    }
    if (matchingTitles.length > 0) {
      score += Math.min(matchingTitles.length * 3, 12);
      reasons.push(`${matchingTitles.length} matching titles`);
    }

    // Also check headline/current position for title matches
    if (titleKeywords.some((k: string) => headline.includes(k))) {
      score += 2;
      reasons.push('headline match');
    }

    // Skill matching
    const matchingSkills = skillKeywords.filter((k: string) => skills.some((s: string) => s.includes(k)));
    if (matchingSkills.length > 0) {
      score += Math.min(matchingSkills.length * 2, 8);
      reasons.push(`${matchingSkills.length} skill matches`);
    }

    // Company/industry experience matching
    const matchingCompanies = companyKeywords.filter((k: string) => companies.some((co: string) => co.includes(k)));
    if (matchingCompanies.length > 0) {
      score += matchingCompanies.length * 2;
      reasons.push(`worked at: ${matchingCompanies.join(', ')}`);
    }

    // Industry signals (search headline, summary, companies, boards, volunteer orgs)
    const allText = [headline, summary, ...companies, ...boards, ...volunteerOrgs].join(' ');
    const matchingSignals = industrySignals.filter((k: string) => allText.includes(k));
    if (matchingSignals.length > 0) {
      score += Math.min(matchingSignals.length * 2, 8);
      reasons.push(`industry signals: ${matchingSignals.join(', ')}`);
    }

    // Board/volunteer involvement (general signal of mission-driven leadership)
    if (boards.length > 0) {
      score += 1;
      reasons.push(`${boards.length} board positions`);
    }
    if (volunteerOrgs.length > 0) {
      score += 1;
      reasons.push(`${volunteerOrgs.length} volunteer orgs`);
    }

    // Familiarity bonus (stronger relationship = easier intro)
    score += c.familiarity_rating;

    // Semantic similarity bonus
    const semScore: number = (semanticScoreMap.get(c.id) as number) || 0;
    score += Math.round(semScore * 10);

    // Location filter (if specified)
    const contactState = (c.state || '').toLowerCase();
    if (locationStates.length > 0 && contactState && !locationStates.some((s: string) => contactState.includes(s))) {
      score -= 5; // Penalize but don't exclude — user can see location
    }

    return {
      ...c,
      candidate_score: score,
      semantic_similarity: Math.round(semScore * 100) / 100,
      matching_titles: matchingTitles.map((t: string) =>
        // Re-capitalize from original array
        (c.enrich_titles_held || []).find((orig: string) => orig.toLowerCase() === t) || t
      ),
      matching_skills: matchingSkills,
      match_reasons: reasons,
    };
  });

  // Step 4: Sort by score DESC, filter to top results
  scored.sort((a: any, b: any) => b.candidate_score - a.candidate_score);
  const topCandidates = scored.slice(0, matchCount);

  // Step 5: Shape response with relevant enrichment highlights
  const candidates = topCandidates.map((c: any) => ({
    id: c.id,
    first_name: c.first_name,
    last_name: c.last_name,
    current_title: c.enrich_current_title || c.position,
    current_company: c.enrich_current_company || c.company,
    headline: c.headline,
    city: c.city,
    state: c.state,
    email: c.email,
    linkedin_url: c.linkedin_url,
    familiarity_rating: c.familiarity_rating,
    comms_last_date: c.comms_last_date,
    comms_thread_count: c.comms_thread_count,
    comms_closeness: c.comms_closeness,
    // Enrichment highlights
    matching_titles: c.matching_titles?.slice(0, 5),
    total_titles_held: (c.enrich_titles_held || []).length,
    recent_titles: (c.enrich_titles_held || []).slice(0, 5),
    companies_worked: (c.enrich_companies_worked || []).slice(0, 8),
    schools: c.enrich_schools,
    skills: (c.enrich_skills || []).slice(0, 12),
    matching_skills: c.matching_skills,
    board_positions: c.enrich_board_positions,
    volunteer_orgs: c.enrich_volunteer_orgs,
    total_experience_years: c.enrich_total_experience_years,
    // Scoring
    candidate_score: c.candidate_score,
    semantic_similarity: c.semantic_similarity,
    match_reasons: c.match_reasons,
    // Brief bio excerpt
    summary_excerpt: c.summary ? c.summary.substring(0, 250) : null,
  }));

  return {
    job_description: input.job_description,
    filters_applied: {
      title_keywords: input.title_keywords,
      seniority_keywords: input.seniority_keywords,
      skill_keywords: input.skill_keywords,
      company_keywords: input.company_keywords,
      industry_signals: input.industry_signals,
      location_states: input.location_states,
      min_familiarity: minFamiliarity,
    },
    count: candidates.length,
    candidates,
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
    'City', 'State', 'Familiarity Rating', 'Last Contact', 'Email Threads',
    'Capacity Score', 'Capacity Tier', 'Kindora Type', 'Outdoorithm Fit',
    'Ask Readiness Tier', 'Ask Readiness Score',
  ];

  const rows = contacts.map((c: any) => {
    const ar = c.ask_readiness?.outdoorithm_fundraising || c.ask_readiness?.kindora_sales || null;
    return [
      c.first_name, c.last_name, c.email, c.linkedin_url, c.company, c.position,
      c.city, c.state, c.familiarity_rating, c.comms_last_date, c.comms_thread_count,
      c.ai_capacity_score, c.ai_capacity_tier, c.ai_kindora_prospect_type,
      c.ai_outdoorithm_fit, ar?.tier, ar?.score,
    ].map(escapeCSVValue).join(',');
  });

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
      case 'job_candidate_search':
        return await jobCandidateSearch(toolInput);
      default:
        throw new Error(`Unknown network tool: ${toolName}`);
    }
  } catch (error: any) {
    console.error(`[Network] Error in ${toolName}:`, error);
    return { error: true, message: error.message || 'Tool execution failed' };
  }
}
