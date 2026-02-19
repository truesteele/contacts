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
      proximity_min: {
        type: 'number',
        description:
          'Minimum proximity score (0-100). inner_circle=80+, close=60+, warm=40+, familiar=20+, acquaintance=10+. Leave unset to include everyone.',
      },
      proximity_tiers: {
        type: 'array',
        items: { type: 'string', enum: ['inner_circle', 'close', 'warm', 'familiar', 'acquaintance', 'distant'] },
        description: 'Filter by specific proximity tiers. Only use if the query asks for specific tiers.',
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
        enum: ['proximity', 'capacity', 'name', 'company'],
        description: 'How to sort results. Default: proximity.',
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

SCORING TIERS:

Proximity (how close to Justin):
- inner_circle (80-100): Close collaborators, deep trust
- close (60-79): Regular contact, shared projects
- warm (40-59): Meaningful connection, periodic interaction
- familiar (20-39): Met but limited interaction
- acquaintance (10-19): One-time meeting or LinkedIn-only
- distant (0-9): No real interaction

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

GUIDELINES:
- Be GENEROUS with filters — include more contacts rather than fewer. Justin can always narrow down.
- For fundraiser/event queries, cast a wide net: include warm+ proximity and medium+ fit.
- For "top" or "best" queries, use higher thresholds (close+ proximity, major_donor capacity).
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
