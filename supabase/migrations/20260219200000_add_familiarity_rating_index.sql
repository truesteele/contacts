-- Index for the GET /api/rate queries: filtering by familiarity_rating IS NULL and breakdown counts
CREATE INDEX IF NOT EXISTS idx_contacts_familiarity_rating ON contacts (familiarity_rating);
