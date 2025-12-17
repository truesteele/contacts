/**
 * Enrich Layer integration for candidate enrichment
 * Now with database caching to avoid duplicate API calls
 */

import { supabase } from './supabase';
import { costTracker } from './cost-tracker';

export interface EnrichmentData {
  email?: string;
  linkedin_url?: string;
  phone?: string;
  location?: string;
  current_company?: string;
  current_title?: string;
  previous_companies?: Array<{
    company: string;
    title: string;
    duration?: string;
  }>;
  education?: Array<{
    school: string;
    degree?: string;
    field?: string;
  }>;
  skills?: string[];
}

/**
 * Enrich candidate with Enrich Layer data
 * Caches results in database for 7 days to avoid duplicate API calls
 *
 * @param contactId - Contact ID to enrich (required for caching)
 * @param email - Email address
 * @param linkedinUrl - LinkedIn URL
 * @returns Enrichment data or null
 */
export async function enrichCandidate(
  contactId?: string,
  email?: string,
  linkedinUrl?: string
): Promise<EnrichmentData | null> {
  const apiKey = process.env.ENRICH_LAYER_API_KEY;

  if (!apiKey) {
    console.warn('Enrich Layer API key not configured');
    return null;
  }

  if (!email && !linkedinUrl) {
    return null;
  }

  // Check cache first if we have a contact ID
  if (contactId) {
    const cached = await checkEnrichmentCache(contactId);
    if (cached) {
      console.log(`✓ Using cached enrichment data for contact ${contactId} (age: ${cached.age_days} days)`);
      costTracker.trackEnrichLayerCall(true); // Cache hit
      return cached.data;
    }
  }

  // Make API call
  try {
    const params = new URLSearchParams();
    if (email) params.append('email', email);
    if (linkedinUrl) params.append('linkedin_url', linkedinUrl);

    console.log(`🔍 Fetching fresh enrichment data from Enrich Layer API...`);
    const response = await fetch(`https://api.enrichlayer.com/v1/person?${params}`, {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.error('Enrich Layer API error:', response.statusText);
      return null;
    }

    const data = await response.json();

    // Track API call cost
    costTracker.trackEnrichLayerCall(false); // API call made

    // Store in database cache if we have a contact ID
    if (contactId && data) {
      await storeEnrichmentData(contactId, data);
      console.log(`✓ Stored enrichment data in database for contact ${contactId}`);
    }

    return data;
  } catch (error) {
    console.error('Error enriching candidate:', error);
    return null;
  }
}

/**
 * Check if we have recent enrichment data cached (within 7 days)
 * @param contactId - Contact ID
 * @returns Cached data and age if available, null otherwise
 */
async function checkEnrichmentCache(contactId: string): Promise<{ data: any; age_days: number } | null> {
  try {
    const { data, error } = await supabase
      .from('contacts')
      .select('enrich_person_from_profile, enriched_at')
      .eq('id', contactId)
      .single();

    if (error || !data) {
      return null;
    }

    // Check if we have enrichment data
    if (!data.enrich_person_from_profile) {
      return null;
    }

    // Check if enrichment is recent (within 7 days)
    if (data.enriched_at) {
      const enrichedDate = new Date(data.enriched_at);
      const now = new Date();
      const ageDays = (now.getTime() - enrichedDate.getTime()) / (1000 * 60 * 60 * 24);

      if (ageDays <= 7) {
        return {
          data: data.enrich_person_from_profile,
          age_days: Math.round(ageDays * 10) / 10, // Round to 1 decimal
        };
      } else {
        console.log(`⚠️  Enrichment data for contact ${contactId} is ${Math.round(ageDays)} days old (>7 days), fetching fresh data...`);
        return null;
      }
    }

    // If we have data but no timestamp, consider it stale
    console.log(`⚠️  Enrichment data for contact ${contactId} has no timestamp, fetching fresh data...`);
    return null;
  } catch (error) {
    console.error('Error checking enrichment cache:', error);
    return null;
  }
}

/**
 * Store enrichment data in database
 * Stores both raw JSON and extracted structured data
 * @param contactId - Contact ID
 * @param enrichmentData - Data from Enrich Layer API
 */
async function storeEnrichmentData(contactId: string, enrichmentData: any): Promise<void> {
  try {
    // Extract structured data
    const structured = extractStructuredData(enrichmentData);

    const { error } = await supabase
      .from('contacts')
      .update({
        // Raw JSON blob (for full data access)
        enrich_person_from_profile: enrichmentData,
        enriched_at: new Date().toISOString(),

        // Structured data (for fast querying)
        ...structured,
      })
      .eq('id', contactId);

    if (error) {
      console.error('Error storing enrichment data:', error);
    }
  } catch (error) {
    console.error('Error storing enrichment data:', error);
  }
}

/**
 * Extract structured data from Enrich Layer response
 * @param data - Raw Enrich Layer API response
 * @returns Structured data object for database columns
 */
function extractStructuredData(data: any): Record<string, any> {
  const structured: Record<string, any> = {};

  // Core profile data
  if (data.follower_count) structured.enrich_follower_count = data.follower_count;
  if (data.connections) structured.enrich_connections = data.connections;
  if (data.profile_pic_url) structured.enrich_profile_pic_url = data.profile_pic_url;

  // Process experiences (work history)
  if (data.experiences && Array.isArray(data.experiences) && data.experiences.length > 0) {
    const experiences = data.experiences;

    // Current position (most recent with no end date)
    const currentRole = experiences.find((exp: any) => !exp.ends_at) || experiences[0];
    if (currentRole) {
      structured.enrich_current_company = currentRole.company;
      structured.enrich_current_title = currentRole.title;

      // Calculate years in current role
      if (currentRole.starts_at?.year) {
        const startDate = new Date(
          currentRole.starts_at.year,
          (currentRole.starts_at.month || 1) - 1,
          currentRole.starts_at.day || 1
        );
        structured.enrich_current_since = startDate.toISOString().split('T')[0];

        const yearsInRole = (new Date().getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24 * 365.25);
        structured.enrich_years_in_current_role = Math.round(yearsInRole * 10) / 10;
      }
    }

    // Extract all companies and titles
    structured.enrich_companies_worked = [...new Set(
      experiences.map((exp: any) => exp.company).filter(Boolean)
    )];
    structured.enrich_titles_held = [...new Set(
      experiences.map((exp: any) => exp.title).filter(Boolean)
    )];

    // Calculate total experience
    const oldestRole = experiences[experiences.length - 1];
    if (oldestRole?.starts_at?.year) {
      const startYear = oldestRole.starts_at.year;
      const totalYears = new Date().getFullYear() - startYear;
      structured.enrich_total_experience_years = totalYears;
    }

    // Count positions and companies
    structured.enrich_number_of_positions = experiences.length;
    structured.enrich_number_of_companies = structured.enrich_companies_worked.length;
  }

  // Process education
  if (data.education && Array.isArray(data.education) && data.education.length > 0) {
    const education = data.education;

    // Extract schools and fields of study
    structured.enrich_schools = [...new Set(
      education.map((edu: any) => edu.school).filter(Boolean)
    )];
    structured.enrich_fields_of_study = [...new Set(
      education.map((edu: any) => edu.field_of_study).filter(Boolean)
    )];

    // Determine highest degree
    const degreeRanking = ['PhD', 'Ph.D', 'Doctorate', 'Masters', 'Master', 'MBA', 'Bachelors', 'Bachelor', 'B.A.', 'B.S.', 'Associate'];
    let highestDegree = null;
    let highestRank = 999;

    for (const edu of education) {
      if (edu.degree_name) {
        const degreeRank = degreeRanking.findIndex(d => edu.degree_name.includes(d));
        if (degreeRank !== -1 && degreeRank < highestRank) {
          highestRank = degreeRank;
          highestDegree = edu.degree_name;
        }
      }
    }

    if (highestDegree) {
      structured.enrich_highest_degree = highestDegree;
    }
  }

  // Process volunteer work (important for nonprofit searches)
  if (data.volunteer_work && Array.isArray(data.volunteer_work) && data.volunteer_work.length > 0) {
    const volunteer = data.volunteer_work;

    // Extract board positions (titles containing "board")
    const boardPositions = volunteer
      .filter((v: any) => v.title && v.title.toLowerCase().includes('board'))
      .map((v: any) => `${v.title} @ ${v.company}`)
      .filter(Boolean);

    if (boardPositions.length > 0) {
      structured.enrich_board_positions = boardPositions;
    }

    // Extract all volunteer organizations
    structured.enrich_volunteer_orgs = [...new Set(
      volunteer.map((v: any) => v.company).filter(Boolean)
    )];
  }

  // Process skills
  if (data.skills && Array.isArray(data.skills) && data.skills.length > 0) {
    structured.enrich_skills = data.skills;
  }

  // Count publications and awards
  if (data.accomplishment_publications && Array.isArray(data.accomplishment_publications)) {
    structured.enrich_publication_count = data.accomplishment_publications.length;
  }

  if (data.accomplishment_honors_awards && Array.isArray(data.accomplishment_honors_awards)) {
    structured.enrich_award_count = data.accomplishment_honors_awards.length;
  }

  return structured;
}

/**
 * Perplexity integration for research
 */
export async function researchTopic(query: string): Promise<string> {
  const apiKey = process.env.PERPLEXITY_API_KEY;
  const model = process.env.PERPLEXITY_MODEL || 'sonar-reasoning-pro';

  if (!apiKey) {
    console.warn('Perplexity API key not configured');
    return 'Research unavailable: API key not configured';
  }

  try {
    const response = await fetch('https://api.perplexity.ai/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        messages: [
          {
            role: 'user',
            content: query,
          },
        ],
      }),
    });

    if (!response.ok) {
      console.error('Perplexity API error:', response.statusText);
      return 'Research failed: API error';
    }

    const data = await response.json();

    // Track cost
    costTracker.trackPerplexityCall();

    return data.choices[0]?.message?.content || 'No results found';
  } catch (error) {
    console.error('Error researching topic:', error);
    return 'Research failed: Network error';
  }
}
