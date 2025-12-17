-- Add search_history table to track job searches
-- Enables reviewing past searches, analyzing patterns, and tracking costs

CREATE TABLE IF NOT EXISTS search_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Job search metadata
  job_title TEXT,
  job_description TEXT,
  job_location TEXT,

  -- Search parameters used
  search_keywords TEXT[],
  search_locations TEXT[],

  -- Results summary
  total_candidates_found INTEGER,
  candidates_enriched INTEGER,
  candidates_evaluated INTEGER,

  -- Top candidates (store IDs for reference)
  top_candidate_ids UUID[],

  -- Cost tracking
  cost_anthropic NUMERIC(10,2) DEFAULT 0,
  cost_enrich_layer NUMERIC(10,2) DEFAULT 0,
  cost_perplexity NUMERIC(10,2) DEFAULT 0,
  total_cost NUMERIC(10,2) DEFAULT 0,

  -- Cache effectiveness
  enrich_cache_hits INTEGER DEFAULT 0,
  enrich_api_calls INTEGER DEFAULT 0,

  -- Search performance
  search_duration_seconds INTEGER,

  -- Optional user tracking (for future multi-user support)
  user_id TEXT
);

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_search_history_created_at
ON search_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_history_job_title
ON search_history USING gin(to_tsvector('english', job_title));

CREATE INDEX IF NOT EXISTS idx_search_history_user_id
ON search_history(user_id)
WHERE user_id IS NOT NULL;

-- Add comments
COMMENT ON TABLE search_history IS 'Tracks job search history including parameters, results, and costs';
COMMENT ON COLUMN search_history.top_candidate_ids IS 'Array of contact IDs for top 5-10 candidates from search';
COMMENT ON COLUMN search_history.total_cost IS 'Total estimated API cost in USD for this search';

-- Verify the table was created
SELECT
  table_name,
  column_name,
  data_type
FROM information_schema.columns
WHERE table_name = 'search_history'
ORDER BY ordinal_position;
