import Anthropic from '@anthropic-ai/sdk';
import { FilterState } from '@/lib/types';

export const runtime = 'edge';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
});

const SET_FILTERS_TOOL: Anthropic.Tool = {
  name: 'set_filters',
  description:
    'Set the structured filters for searching Justin\'s network. Translate the user\'s natural language query into these filter parameters.',
  input_schema: {
    type: 'object' as const,
    properties: {
      familiarity_min: {
        type: 'number',
        description:
          'Minimum familiarity rating (0-4). 0=don\'t know, 1=recognize name, 2=know them, 3=good relationship, 4=close/trusted. This is Justin\'s personal rating and the PRIMARY relationship signal. Use 2+ for "people I know", 3+ for "good contacts" or fundraising, 4 for "close friends".',
      },
      has_comms: {
        type: 'boolean',
        description:
          'If true, only include contacts Justin has email history with. Use for queries about "people I\'ve been in touch with" or "active relationships".',
      },
      comms_since: {
        type: 'string',
        description:
          'ISO date string (YYYY-MM-DD). Only include contacts Justin has emailed since this date. Use for "recently in touch" or "contacted this year" queries.',
      },
      goal: {
        type: 'string',
        enum: ['outdoorithm_fundraising', 'kindora_sales'],
        description:
          'Set the fundraising/outreach goal. When set, contacts are ranked by AI ask-readiness score for that goal. ALWAYS set this for fundraising, donation, outreach, or "who should I ask" queries. outdoorithm_fundraising = Outdoorithm Collective nonprofit donations. kindora_sales = Kindora enterprise sales prospects.',
      },
      proximity_min: {
        type: 'number',
        description:
          'Legacy: Minimum AI proximity score (0-100). Superseded by familiarity_min. Only use if query explicitly mentions "proximity score".',
      },
      proximity_tiers: {
        type: 'array',
        items: { type: 'string', enum: ['inner_circle', 'close', 'warm', 'familiar', 'acquaintance', 'distant'] },
        description: 'Legacy: Filter by AI proximity tiers. Superseded by familiarity_min.',
      },
      capacity_min: {
        type: 'number',
        description:
          'Minimum giving/financial capacity score (0-100). major_donor=70+, mid_level=40+, grassroots=10+.',
      },
      capacity_tiers: {
        type: 'array',
        items: { type: 'string', enum: ['major_donor', 'mid_level', 'grassroots', 'unknown'] },
        description: 'Filter by specific capacity tiers.',
      },
      outdoorithm_fit: {
        type: 'array',
        items: { type: 'string', enum: ['high', 'medium', 'low', 'none'] },
        description: 'Filter by Outdoorithm Collective fit level.',
      },
      kindora_type: {
        type: 'array',
        items: { type: 'string', enum: ['enterprise_buyer', 'champion', 'influencer', 'not_relevant'] },
        description: 'Filter by Kindora prospect type.',
      },
      company_keyword: {
        type: 'string',
        description: 'Search for contacts at a specific company (partial match).',
      },
      name_search: {
        type: 'string',
        description: 'Search for a specific person by name.',
      },
      location_state: {
        type: 'string',
        description: 'Filter by US state (e.g., "California", "New York").',
      },
      semantic_query: {
        type: 'string',
        description:
          'A topic/interest query for semantic (embedding) search. Use when the query is about themes, topics, or interests rather than structured attributes. E.g., "outdoor equity", "philanthropy tech", "education reform".',
      },
      sort_by: {
        type: 'string',
        enum: ['familiarity', 'ask_readiness', 'comms_recency', 'capacity', 'proximity', 'name', 'company'],
        description: 'How to sort results. Default: familiarity. Use ask_readiness when goal is set. Use comms_recency for "recent contacts" queries.',
      },
      sort_order: {
        type: 'string',
        enum: ['asc', 'desc'],
        description: 'Sort direction. Default: desc (highest first).',
      },
      limit: {
        type: 'number',
        description:
          'Maximum results to return. Default 50. Use 100-200 for broad queries like "who should I invite" or "all donors".',
      },
      explanation: {
        type: 'string',
        description:
          'A brief, human-readable explanation (1-2 sentences) of why you chose these filters. This is shown to the user under the filter bar.',
      },
    },
    required: ['explanation'],
  },
};

const SYSTEM_PROMPT = `You are a filter translator for Justin Steele's professional network database of ~2,400 contacts. Your ONLY job is to translate the user's natural language query into structured filter parameters by calling the set_filters tool.

ABOUT JUSTIN:
- CEO of Kindora (ed-tech / impact platform)
- Fractional CIO at True Steele
- Co-founded Outdoorithm and Outdoorithm Collective (outdoor equity nonprofit)
- Board member: San Francisco Foundation, Outdoorithm Collective
- Former: Google.org Director Americas, Year Up, Bridgespan Group, Bain & Company
- Schools: Harvard Business School, Harvard Kennedy School, University of Virginia

PRIMARY SIGNAL — FAMILIARITY RATING (Justin's personal assessment):
- 0: Don't know / no relationship
- 1: Recognize the name but no real interaction
- 2: Know them — have met, some interaction
- 3: Good relationship — regular contact, mutual respect
- 4: Close / trusted — inner circle, would call anytime

This is the MOST IMPORTANT filter. Use familiarity_min instead of proximity_min for relationship-based queries.

ASK-READINESS (AI donor psychology scoring):
Each contact has been assessed by AI for ask-readiness toward specific goals. Tiers:
- ready_now (80-100): Strong relationship + capacity + values alignment. Can ask directly.
- cultivate_first (60-79): Good foundation but needs a touchpoint before asking.
- long_term (20-59): Has potential but relationship is too thin for a direct ask.
- not_a_fit (0-19): No relationship, alignment, or capacity. Skip.

When the user asks about fundraising, donations, outreach, "who should I ask", or anything related to approaching people for a specific purpose, ALWAYS set the goal parameter and sort_by: ask_readiness.

GOALS:
- outdoorithm_fundraising: Outdoorithm Collective nonprofit individual donor fundraising (DEFAULT for fundraising queries)
- kindora_sales: Kindora enterprise sales prospect outreach

COMMUNICATION HISTORY:
- ~628 contacts have email thread history with Justin
- has_comms=true filters to only contacts with email history
- comms_since filters to contacts emailed since a specific date

Capacity (giving potential):
- major_donor (70+): Senior executive, significant wealth
- mid_level (40-69): Professional-level, moderate giving
- grassroots (10-39): Early career or limited indicators
- unknown (0-9): Insufficient data

Kindora Prospect Type:
- enterprise_buyer: Could purchase Kindora
- champion: Could advocate for Kindora in their org
- influencer: Thought leader who could amplify Kindora
- not_relevant: Not a Kindora prospect

Outdoorithm Fit: high / medium / low / none

Proximity (LEGACY — AI-estimated closeness, superseded by familiarity):
- inner_circle (80-100), close (60-79), warm (40-59), familiar (20-39), acquaintance (10-19), distant (0-9)
- Only use proximity_min if the query explicitly mentions "proximity score"

GUIDELINES:
- Be GENEROUS with filters — include more contacts rather than fewer. Justin can always narrow down.
- For fundraising/outreach queries: set goal='outdoorithm_fundraising', sort_by='ask_readiness', familiarity_min=2, limit=100.
- For Kindora sales queries: set goal='kindora_sales', sort_by='ask_readiness'.
- For "who do I know at X" or relationship queries: use familiarity_min=2 and sort_by='familiarity'.
- For "who have I been in touch with": use has_comms=true and sort_by='comms_recency'.
- For "top" or "best" queries, use familiarity_min=3 and/or major_donor capacity.
- For topic-based queries ("who cares about X"), use semantic_query instead of structured filters.
- Use higher limits (100-200) for broad queries. Use lower limits (20-50) for specific queries.
- When in doubt, prefer semantic_query over overly narrow structured filters.
- If the query mentions a specific person by name, use name_search.
- If the query mentions a company, use company_keyword.
- Always provide a clear, brief explanation of the filters you chose.`;

export async function POST(req: Request) {
  try {
    const { query } = await req.json();

    if (!query || typeof query !== 'string') {
      return new Response(
        JSON.stringify({ error: 'Missing or invalid query parameter' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const response = await anthropic.messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 1024,
      temperature: 0,
      system: SYSTEM_PROMPT,
      messages: [{ role: 'user', content: query }],
      tools: [SET_FILTERS_TOOL],
      tool_choice: { type: 'tool', name: 'set_filters' },
    });

    // Extract the tool use block
    const toolUse = response.content.find(
      (block): block is Anthropic.ToolUseBlock => block.type === 'tool_use'
    );

    if (!toolUse) {
      return new Response(
        JSON.stringify({ error: 'Failed to parse filters from query' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const input = toolUse.input as Record<string, any>;

    // Separate explanation from filter fields
    const explanation = input.explanation || '';
    const filters: FilterState = {};

    if (input.familiarity_min != null) filters.familiarity_min = input.familiarity_min;
    if (input.has_comms != null) filters.has_comms = input.has_comms;
    if (input.comms_since) filters.comms_since = input.comms_since;
    if (input.goal) filters.goal = input.goal;
    if (input.proximity_min != null) filters.proximity_min = input.proximity_min;
    if (input.proximity_tiers?.length) filters.proximity_tiers = input.proximity_tiers;
    if (input.capacity_min != null) filters.capacity_min = input.capacity_min;
    if (input.capacity_tiers?.length) filters.capacity_tiers = input.capacity_tiers;
    if (input.outdoorithm_fit?.length) filters.outdoorithm_fit = input.outdoorithm_fit;
    if (input.kindora_type?.length) filters.kindora_type = input.kindora_type;
    if (input.company_keyword) filters.company_keyword = input.company_keyword;
    if (input.name_search) filters.name_search = input.name_search;
    if (input.location_state) filters.location_state = input.location_state;
    if (input.semantic_query) filters.semantic_query = input.semantic_query;
    if (input.sort_by) filters.sort_by = input.sort_by;
    if (input.sort_order) filters.sort_order = input.sort_order;
    if (input.limit != null) filters.limit = input.limit;

    return new Response(
      JSON.stringify({ filters, explanation }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error: any) {
    console.error('Parse filters error:', error);
    return new Response(
      JSON.stringify({ error: error.message || 'Failed to parse filters' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
