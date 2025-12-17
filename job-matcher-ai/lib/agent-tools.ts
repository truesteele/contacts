import Anthropic from '@anthropic-ai/sdk';
import { searchContacts, Contact } from './supabase';
import { enrichCandidate, researchTopic } from './enrichment';
import { costTracker } from './cost-tracker';
import { saveSearchHistory, createSearchHistoryEntry } from './search-history';
import { contactsToCSV } from './csv-export';

/**
 * Tool definitions for Claude agent
 */
export const tools: Anthropic.Tool[] = [
  {
    name: 'search_candidates',
    description: 'Search the contacts database for potential candidates. Use keywords from the job description to filter candidates. Returns a list of contacts with basic information.',
    input_schema: {
      type: 'object',
      properties: {
        keywords: {
          type: 'array',
          items: { type: 'string' },
          description: 'Keywords to search for in candidate profiles (company, position, headline, summary). Examples: ["data", "philanthropy", "leadership"]',
        },
        locations: {
          type: 'array',
          items: { type: 'string' },
          description: 'City names or metro area names to filter candidates. The system automatically expands to entire metro areas. Examples: ["San Francisco"] will include all Bay Area cities like Oakland, Fremont, Mountain View. ["Seattle"] includes Bellevue, Redmond, Tacoma. ["Mountain View"] searches the entire SF Bay Area.',
        },
        min_relevance: {
          type: 'number',
          description: 'Minimum number of keyword matches required (default: 1)',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results to return (default: 50)',
        },
      },
      required: [],
    },
  },
  {
    name: 'enrich_candidate',
    description: 'Get additional enrichment data for a candidate using Enrich Layer. Provides detailed work history, education, skills, and other professional information. IMPORTANT: Results are cached for 7 days - always pass contact_id to enable caching and avoid duplicate API calls.',
    input_schema: {
      type: 'object',
      properties: {
        contact_id: {
          type: 'string',
          description: 'Contact ID from database (REQUIRED for caching - pass the id field from search results)',
        },
        email: {
          type: 'string',
          description: 'Candidate email address',
        },
        linkedin_url: {
          type: 'string',
          description: 'Candidate LinkedIn profile URL',
        },
      },
      required: [],
    },
  },
  {
    name: 'research_topic',
    description: 'Use Perplexity AI to research a topic in real-time. Useful for understanding industry trends, market conditions, or specific domain knowledge relevant to the job search.',
    input_schema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'The research query or question',
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'evaluate_candidate',
    description: 'Perform a detailed AI-powered evaluation of a candidate against job requirements. This is computationally expensive, so use only for top candidates after initial filtering.',
    input_schema: {
      type: 'object',
      properties: {
        candidate: {
          type: 'object',
          description: 'The candidate object with all available information',
        },
        job_description: {
          type: 'string',
          description: 'The full job description text',
        },
        criteria: {
          type: 'object',
          description: 'Specific evaluation criteria extracted from the job description',
        },
      },
      required: ['candidate', 'job_description'],
    },
  },
  {
    name: 'save_search',
    description: 'Save the current search to history for future reference. Call this at the end of a successful search to track costs, parameters, and results.',
    input_schema: {
      type: 'object',
      properties: {
        job_title: {
          type: 'string',
          description: 'Job title being searched for',
        },
        job_description: {
          type: 'string',
          description: 'Full job description text',
        },
        job_location: {
          type: 'string',
          description: 'Primary job location',
        },
        search_keywords: {
          type: 'array',
          items: { type: 'string' },
          description: 'Keywords used in the search',
        },
        search_locations: {
          type: 'array',
          items: { type: 'string' },
          description: 'Locations searched',
        },
        total_candidates_found: {
          type: 'number',
          description: 'Total number of candidates found',
        },
        top_candidate_ids: {
          type: 'array',
          items: { type: 'string' },
          description: 'IDs of top 5-10 candidates from this search',
        },
      },
      required: ['job_title'],
    },
  },
  {
    name: 'export_to_csv',
    description: 'Generate a CSV export of candidate data. Returns CSV content as a string that can be presented to the user for download.',
    input_schema: {
      type: 'object',
      properties: {
        candidates: {
          type: 'array',
          description: 'Array of candidate objects to export',
        },
        include_enrichment_data: {
          type: 'boolean',
          description: 'Whether to include enriched fields (default: true)',
        },
        job_title: {
          type: 'string',
          description: 'Job title for filename generation',
        },
      },
      required: ['candidates'],
    },
  },
];

/**
 * Execute tool calls made by the agent
 */
export async function executeToolCall(
  toolName: string,
  toolInput: any
): Promise<any> {
  console.log(`Executing tool: ${toolName}`, toolInput);

  try {
    switch (toolName) {
      case 'search_candidates':
        return await searchContacts({
          keywords: toolInput.keywords,
          locations: toolInput.locations,
          min_relevance: toolInput.min_relevance || 1,
          limit: toolInput.limit || 50,
        });

      case 'enrich_candidate':
        return await enrichCandidate(
          toolInput.contact_id,
          toolInput.email,
          toolInput.linkedin_url
        );

      case 'research_topic':
        return await researchTopic(toolInput.query);

      case 'evaluate_candidate':
        return await evaluateCandidate(
          toolInput.candidate,
          toolInput.job_description,
          toolInput.criteria
        );

      case 'save_search':
        const entry = createSearchHistoryEntry({
          jobTitle: toolInput.job_title,
          jobDescription: toolInput.job_description,
          jobLocation: toolInput.job_location,
          searchKeywords: toolInput.search_keywords,
          searchLocations: toolInput.search_locations,
          totalCandidatesFound: toolInput.total_candidates_found,
          topCandidateIds: toolInput.top_candidate_ids,
        });
        const searchId = await saveSearchHistory(entry);
        return {
          success: true,
          search_id: searchId,
          message: 'Search saved to history',
        };

      case 'export_to_csv':
        const csvContent = contactsToCSV(
          toolInput.candidates,
          toolInput.include_enrichment_data !== false
        );
        const timestamp = new Date().toISOString().split('T')[0];
        const filename = toolInput.job_title
          ? `${toolInput.job_title.toLowerCase().replace(/[^a-z0-9]+/g, '_')}_${timestamp}.csv`
          : `candidates_${timestamp}.csv`;

        return {
          success: true,
          csv_content: csvContent,
          filename,
          row_count: toolInput.candidates.length,
          message: `CSV export ready with ${toolInput.candidates.length} candidates`,
        };

      default:
        throw new Error(`Unknown tool: ${toolName}`);
    }
  } catch (error: any) {
    console.error(`Error executing tool ${toolName}:`, error);
    return {
      error: true,
      message: error.message || 'Tool execution failed',
    };
  }
}

/**
 * Detailed candidate evaluation using Claude
 */
async function evaluateCandidate(
  candidate: Contact,
  jobDescription: string,
  criteria?: any
): Promise<any> {
  const anthropic = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY,
  });

  const evaluationPrompt = `
You are an expert executive recruiter. Evaluate this candidate for the following role with comprehensive, structured analysis.

JOB DESCRIPTION:
${jobDescription}

CANDIDATE PROFILE:
Name: ${candidate.first_name} ${candidate.last_name}
Email: ${candidate.email || 'Not available'}
LinkedIn: ${candidate.linkedin_url || 'Not available'}
Company: ${candidate.company || 'Unknown'}
Position: ${candidate.position || 'Unknown'}
Location: ${candidate.city}, ${candidate.state}
Headline: ${candidate.headline || 'None'}
Summary: ${candidate.summary?.substring(0, 1000) || 'No summary available'}

${candidate.enrich_person_from_profile ? `\nEnrichment Data: ${JSON.stringify(candidate.enrich_person_from_profile, null, 2).substring(0, 1000)}` : ''}

${criteria ? `\nADDITIONAL EVALUATION CRITERIA:\n${JSON.stringify(criteria, null, 2)}` : ''}

Return a comprehensive JSON evaluation with the following structure:
{
  "recommendation": "strong_yes|yes|maybe|no",
  "fit_score": <1-10, where 8+ is excellent fit>,
  "confidence_level": "high|medium|low",

  "seniority_assessment": {
    "current_level": "C-suite|Senior VP|VP|Senior Director|Director|Manager|Individual Contributor|Other",
    "years_in_field": "<estimated total years>",
    "years_leadership": "<estimated years in leadership roles>",
    "largest_team_managed": "<estimate of largest team size, or 'unknown'>",
    "budget_managed": "<estimate if evident from profile, or 'unknown'>",
    "seniority_match": "perfect|step_up|lateral|overqualified|underqualified",
    "readiness": "ready_now|ready_with_development|not_ready"
  },

  "relevant_experience": {
    <Extract 8-12 key boolean flags specific to this job description>
    Examples based on job type:
    - For foundation roles: "has_foundation_experience", "has_grantmaking_experience", "has_board_management"
    - For tech roles: "has_relevant_tech_stack", "has_scale_experience", "has_startup_experience"
    - For nonprofit: "has_nonprofit_experience", "has_fundraising_experience", "has_program_development"

    Each should be: true|false with clear relevance to the job requirements
  },

  "strengths": [
    "<specific strength with concrete evidence from profile>",
    "<another key strength relevant to role>",
    "<third differentiating strength>"
  ],

  "gaps_or_concerns": [
    "<specific gap or red flag relative to requirements>",
    "<another concern or development area>",
    "<third potential issue if applicable>"
  ],

  "detailed_rationale": "<4-5 sentences explaining overall fit. Include specific evidence from background. Explain likelihood of success in this particular role. Address both strengths and concerns.>",

  "interview_priority": "immediate|high|medium|low",

  "interview_focus_areas": [
    "<specific critical area to probe in interview>",
    "<another important topic to explore>",
    "<third area needing clarification>"
  ],

  "location_fit": {
    "current_location": "${candidate.city}, ${candidate.state}",
    "job_location": "<extract from job description>",
    "relocation_required": true|false,
    "relocation_likelihood": "already_local|very_likely|possible|unlikely|very_unlikely",
    "remote_work_option": "<note if job allows remote/hybrid>"
  },

  "compensation_assessment": {
    "job_range": "<extract salary range from job description if mentioned>",
    "estimated_current": "<estimate candidate's current comp based on role/company>",
    "fit": "within_range|might_need_higher|might_accept_lower|significant_gap_up|significant_gap_down|unknown"
  },

  "cultural_factors": {
    "org_size_match": "<assess if candidate's current org size matches target org>",
    "sector_transition": "<note if transitioning between sectors (corporate→nonprofit, etc)>",
    "leadership_style_indicators": "<note any evident leadership style from profile>",
    "potential_chemistry": "<assess likely fit with org culture/leadership based on background>"
  },

  "network_value": "<Note any valuable connections, board positions, industry influence, or network effects this candidate brings beyond their direct contributions>",

  "unique_considerations": "<Any unique factors specific to this candidate or role that don't fit above categories>"
}

CRITICAL INSTRUCTIONS:
- Be thorough and precise
- Base ALL assessments on concrete evidence from the profile
- Extract job-specific boolean flags for "relevant_experience" (don't use generic placeholders)
- Provide quantitative estimates where possible (years, team sizes, budget)
- Consider practical factors: relocation, compensation, seniority match, sector transition
- Flag both strengths AND concerns - be honest about gaps
- Make the evaluation actionable for recruitment decisions
`;

  const response = await anthropic.messages.create({
    model: 'claude-sonnet-4-5-20250929',
    max_tokens: 3000, // Increased for comprehensive evaluation
    temperature: 0.3,
    messages: [
      {
        role: 'user',
        content: evaluationPrompt,
      },
    ],
  });

  // Track cost
  costTracker.trackAnthropicCall();

  const content = response.content[0];
  if (content.type === 'text') {
    // Extract JSON from response
    let jsonText = content.text;
    if (jsonText.includes('```json')) {
      jsonText = jsonText.split('```json')[1].split('```')[0];
    } else if (jsonText.includes('```')) {
      jsonText = jsonText.split('```')[1].split('```')[0];
    }

    try {
      return JSON.parse(jsonText.trim());
    } catch (e) {
      console.error('Failed to parse evaluation JSON:', e);
      return {
        recommendation: 'maybe',
        fit_score: 5,
        detailed_rationale: content.text,
        error: 'Failed to parse structured evaluation',
      };
    }
  }

  return {
    error: true,
    message: 'Unexpected response format',
  };
}
