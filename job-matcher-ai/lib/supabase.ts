import { createClient } from '@supabase/supabase-js';
import { expandToMetroAreas } from './metro-areas';

if (!process.env.SUPABASE_URL) {
  throw new Error('Missing SUPABASE_URL environment variable');
}

if (!process.env.SUPABASE_SERVICE_KEY) {
  throw new Error('Missing SUPABASE_SERVICE_KEY environment variable');
}

export const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

export interface Contact {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  linkedin_url?: string;
  company?: string;
  position?: string;
  city?: string;
  state?: string;
  headline?: string;
  summary?: string;
  enrich_person_from_profile?: any;
}

export interface SearchFilters {
  keywords?: string[];
  locations?: string[];
  min_relevance?: number;
  limit?: number;
}

export async function searchContacts(filters: SearchFilters): Promise<Contact[]> {
  let query = supabase
    .from('contacts')
    .select('id, first_name, last_name, email, linkedin_url, company, position, city, state, headline, summary, enrich_person_from_profile');

  // Apply location filters with metro area expansion
  if (filters.locations && filters.locations.length > 0) {
    // Expand locations to include entire metro areas
    // e.g., "San Francisco" becomes all Bay Area cities
    const expandedLocations = expandToMetroAreas(filters.locations);
    console.log(`Expanded ${filters.locations.length} locations to ${expandedLocations.length} metro area cities`);
    query = query.in('city', expandedLocations);
  }

  // Execute query
  const { data, error } = await query;

  if (error) {
    console.error('Supabase query error:', error);
    throw new Error(`Database query failed: ${error.message}`);
  }

  let contacts = data || [];

  // Apply keyword filtering if specified
  if (filters.keywords && filters.keywords.length > 0) {
    contacts = contacts.filter(contact => {
      const searchText = `
        ${contact.company || ''}
        ${contact.position || ''}
        ${contact.headline || ''}
        ${contact.summary || ''}
      `.toLowerCase();

      const matches = filters.keywords!.filter(keyword =>
        searchText.includes(keyword.toLowerCase())
      ).length;

      return matches >= (filters.min_relevance || 1);
    });
  }

  // Apply limit
  if (filters.limit) {
    contacts = contacts.slice(0, filters.limit);
  }

  return contacts;
}

export interface NetworkContact {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  personal_email?: string;
  work_email?: string;
  linkedin_url?: string;
  company?: string;
  position?: string;
  city?: string;
  state?: string;
  headline?: string;
  summary?: string;
  ai_proximity_score?: number;
  ai_proximity_tier?: string;
  ai_capacity_score?: number;
  ai_capacity_tier?: string;
  ai_kindora_prospect_score?: number;
  ai_kindora_prospect_type?: string;
  ai_outdoorithm_fit?: string;
  ai_tags?: Record<string, any>;
  profile_embedding?: string;
  interests_embedding?: string;
  familiarity_rating?: number | null;
  familiarity_rated_at?: string | null;
  comms_last_date?: string | null;
  comms_thread_count?: number | null;
  shared_institutions?: Record<string, any>[] | null;
  ask_readiness?: Record<string, any> | null;
}

export async function getContactById(id: string): Promise<Contact | null> {
  const { data, error } = await supabase
    .from('contacts')
    .select('*')
    .eq('id', id)
    .single();

  if (error) {
    console.error('Error fetching contact:', error);
    return null;
  }

  return data;
}
