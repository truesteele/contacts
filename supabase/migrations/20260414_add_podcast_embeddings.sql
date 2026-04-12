-- Add vector embedding columns for semantic podcast matching
-- and discovery method tracking

-- Embedding for semantic matching (text-embedding-3-small, 768 dims)
ALTER TABLE podcast_targets ADD COLUMN IF NOT EXISTS description_embedding vector(768);

-- Track how each podcast was discovered (keyword_search, similar_speaker, expanded_keywords, etc.)
ALTER TABLE podcast_targets ADD COLUMN IF NOT EXISTS discovery_methods text[] DEFAULT '{}';

-- Speaker profile embedding for direct comparison
ALTER TABLE speaker_profiles ADD COLUMN IF NOT EXISTS profile_embedding vector(768);

-- IVFFlat index for cosine similarity (lists ~ sqrt(rows), ~20 for ~400 rows)
CREATE INDEX IF NOT EXISTS idx_podcast_targets_embedding
  ON podcast_targets USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 20);
