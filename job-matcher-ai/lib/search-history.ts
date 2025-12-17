/**
 * Search History tracking for job searches
 * Enables reviewing past searches, analyzing patterns, and tracking costs
 */

import { supabase } from './supabase';
import { costTracker } from './cost-tracker';

export interface SearchHistoryEntry {
  id?: string;
  created_at?: string;
  job_title?: string;
  job_description?: string;
  job_location?: string;
  search_keywords?: string[];
  search_locations?: string[];
  total_candidates_found?: number;
  candidates_enriched?: number;
  candidates_evaluated?: number;
  top_candidate_ids?: string[];
  cost_anthropic?: number;
  cost_enrich_layer?: number;
  cost_perplexity?: number;
  total_cost?: number;
  enrich_cache_hits?: number;
  enrich_api_calls?: number;
  search_duration_seconds?: number;
  user_id?: string;
}

/**
 * Save a completed search to history
 */
export async function saveSearchHistory(entry: SearchHistoryEntry): Promise<string | null> {
  try {
    const { data, error } = await supabase
      .from('search_history')
      .insert([entry])
      .select('id')
      .single();

    if (error) {
      console.error('Error saving search history:', error);
      return null;
    }

    console.log(`✓ Search saved to history (ID: ${data.id})`);
    return data.id;
  } catch (error) {
    console.error('Error saving search history:', error);
    return null;
  }
}

/**
 * Get recent search history (last 20 searches)
 */
export async function getRecentSearches(limit: number = 20): Promise<SearchHistoryEntry[]> {
  try {
    const { data, error } = await supabase
      .from('search_history')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(limit);

    if (error) {
      console.error('Error fetching search history:', error);
      return [];
    }

    return data || [];
  } catch (error) {
    console.error('Error fetching search history:', error);
    return [];
  }
}

/**
 * Get search history for a specific job title
 */
export async function searchHistoryByJobTitle(jobTitle: string): Promise<SearchHistoryEntry[]> {
  try {
    const { data, error } = await supabase
      .from('search_history')
      .select('*')
      .ilike('job_title', `%${jobTitle}%`)
      .order('created_at', { ascending: false });

    if (error) {
      console.error('Error searching history:', error);
      return [];
    }

    return data || [];
  } catch (error) {
    console.error('Error searching history:', error);
    return [];
  }
}

/**
 * Get cost statistics across all searches
 */
export async function getCostStatistics(): Promise<{
  total_searches: number;
  total_cost: number;
  avg_cost_per_search: number;
  total_candidates_found: number;
  total_candidates_enriched: number;
  total_candidates_evaluated: number;
  avg_cache_hit_rate: number;
}> {
  try {
    const { data, error } = await supabase
      .from('search_history')
      .select('*');

    if (error || !data || data.length === 0) {
      return {
        total_searches: 0,
        total_cost: 0,
        avg_cost_per_search: 0,
        total_candidates_found: 0,
        total_candidates_enriched: 0,
        total_candidates_evaluated: 0,
        avg_cache_hit_rate: 0,
      };
    }

    const stats = data.reduce((acc, search) => {
      acc.total_cost += search.total_cost || 0;
      acc.total_candidates_found += search.total_candidates_found || 0;
      acc.total_candidates_enriched += search.candidates_enriched || 0;
      acc.total_candidates_evaluated += search.candidates_evaluated || 0;

      const total_enrich_calls = (search.enrich_cache_hits || 0) + (search.enrich_api_calls || 0);
      if (total_enrich_calls > 0) {
        acc.cache_hit_rate_sum += (search.enrich_cache_hits || 0) / total_enrich_calls;
        acc.cache_hit_rate_count++;
      }

      return acc;
    }, {
      total_cost: 0,
      total_candidates_found: 0,
      total_candidates_enriched: 0,
      total_candidates_evaluated: 0,
      cache_hit_rate_sum: 0,
      cache_hit_rate_count: 0,
    });

    return {
      total_searches: data.length,
      total_cost: Math.round(stats.total_cost * 100) / 100,
      avg_cost_per_search: Math.round((stats.total_cost / data.length) * 100) / 100,
      total_candidates_found: stats.total_candidates_found,
      total_candidates_enriched: stats.total_candidates_enriched,
      total_candidates_evaluated: stats.total_candidates_evaluated,
      avg_cache_hit_rate: stats.cache_hit_rate_count > 0
        ? Math.round((stats.cache_hit_rate_sum / stats.cache_hit_rate_count) * 100)
        : 0,
    };
  } catch (error) {
    console.error('Error calculating cost statistics:', error);
    return {
      total_searches: 0,
      total_cost: 0,
      avg_cost_per_search: 0,
      total_candidates_found: 0,
      total_candidates_enriched: 0,
      total_candidates_evaluated: 0,
      avg_cache_hit_rate: 0,
    };
  }
}

/**
 * Create a search history entry from current cost tracker and search metadata
 */
export function createSearchHistoryEntry(metadata: {
  jobTitle?: string;
  jobDescription?: string;
  jobLocation?: string;
  searchKeywords?: string[];
  searchLocations?: string[];
  totalCandidatesFound?: number;
  topCandidateIds?: string[];
  searchDurationSeconds?: number;
}): SearchHistoryEntry {
  const metrics = costTracker.getMetrics();

  return {
    job_title: metadata.jobTitle,
    job_description: metadata.jobDescription,
    job_location: metadata.jobLocation,
    search_keywords: metadata.searchKeywords,
    search_locations: metadata.searchLocations,
    total_candidates_found: metadata.totalCandidatesFound,
    candidates_enriched: metrics.enrichLayerCalls,
    candidates_evaluated: metrics.anthropicCalls,
    top_candidate_ids: metadata.topCandidateIds,
    cost_anthropic: metrics.anthropicCalls * 0.03,
    cost_enrich_layer: metrics.enrichLayerCalls * 0.10,
    cost_perplexity: metrics.perplexityCalls * 0.20,
    total_cost: metrics.totalEstimatedCost,
    enrich_cache_hits: metrics.enrichLayerCacheHits,
    enrich_api_calls: metrics.enrichLayerCalls,
    search_duration_seconds: metadata.searchDurationSeconds,
  };
}
