-- Add enriched_at column to track when Enrich Layer data was last fetched
-- This enables 7-day caching to avoid duplicate API calls

-- Add the column if it doesn't exist
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMP WITH TIME ZONE;

-- Add comment to explain the column
COMMENT ON COLUMN contacts.enriched_at IS 'Timestamp when Enrich Layer API data was last fetched. Used for caching (7-day freshness).';

-- Create index for efficient cache checking queries
CREATE INDEX IF NOT EXISTS idx_contacts_enriched_at
ON contacts(enriched_at)
WHERE enriched_at IS NOT NULL;

-- Optional: Update existing records that have enrichment data but no timestamp
-- (Sets them to a date in the past so they'll be refreshed on next enrichment)
UPDATE contacts
SET enriched_at = NOW() - INTERVAL '8 days'
WHERE enrich_person_from_profile IS NOT NULL
  AND enriched_at IS NULL;

-- Verify the changes
SELECT
  COUNT(*) AS total_contacts,
  COUNT(enrich_person_from_profile) AS enriched_contacts,
  COUNT(enriched_at) AS contacts_with_timestamp,
  COUNT(CASE WHEN enriched_at > NOW() - INTERVAL '7 days' THEN 1 END) AS fresh_enrichments
FROM contacts;
