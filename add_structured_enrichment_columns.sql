-- Add structured columns for enriched data
-- This allows fast querying without parsing JSON blob

-- Core profile data
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS enrich_follower_count INTEGER,
ADD COLUMN IF NOT EXISTS enrich_connections INTEGER,
ADD COLUMN IF NOT EXISTS enrich_profile_pic_url TEXT;

-- Current position (most valuable for searches)
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS enrich_current_company TEXT,
ADD COLUMN IF NOT EXISTS enrich_current_title TEXT,
ADD COLUMN IF NOT EXISTS enrich_current_since DATE,
ADD COLUMN IF NOT EXISTS enrich_years_in_current_role NUMERIC(4,1);

-- Career summary
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS enrich_total_experience_years NUMERIC(4,1),
ADD COLUMN IF NOT EXISTS enrich_number_of_positions INTEGER,
ADD COLUMN IF NOT EXISTS enrich_number_of_companies INTEGER;

-- Education
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS enrich_highest_degree TEXT,
ADD COLUMN IF NOT EXISTS enrich_schools TEXT[], -- Array of school names
ADD COLUMN IF NOT EXISTS enrich_fields_of_study TEXT[]; -- Array of fields

-- Experience arrays (for filtering/searching)
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS enrich_companies_worked TEXT[], -- All companies
ADD COLUMN IF NOT EXISTS enrich_titles_held TEXT[], -- All titles
ADD COLUMN IF NOT EXISTS enrich_skills TEXT[]; -- Skills if available

-- Volunteer/Board (important for nonprofit searches)
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS enrich_board_positions TEXT[], -- Board memberships
ADD COLUMN IF NOT EXISTS enrich_volunteer_orgs TEXT[]; -- Volunteer organizations

-- Publications/Awards (for thought leadership assessment)
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS enrich_publication_count INTEGER,
ADD COLUMN IF NOT EXISTS enrich_award_count INTEGER;

-- Add comments
COMMENT ON COLUMN contacts.enrich_follower_count IS 'LinkedIn follower count from Enrich Layer';
COMMENT ON COLUMN contacts.enrich_connections IS 'LinkedIn connection count from Enrich Layer';
COMMENT ON COLUMN contacts.enrich_current_company IS 'Current company from most recent experience';
COMMENT ON COLUMN contacts.enrich_current_title IS 'Current job title from most recent experience';
COMMENT ON COLUMN contacts.enrich_current_since IS 'Start date of current role';
COMMENT ON COLUMN contacts.enrich_years_in_current_role IS 'Calculated years in current position';
COMMENT ON COLUMN contacts.enrich_total_experience_years IS 'Total professional experience in years';
COMMENT ON COLUMN contacts.enrich_number_of_positions IS 'Total number of positions held';
COMMENT ON COLUMN contacts.enrich_number_of_companies IS 'Total number of companies worked for';
COMMENT ON COLUMN contacts.enrich_highest_degree IS 'Highest degree earned (PhD, Masters, Bachelors, etc)';
COMMENT ON COLUMN contacts.enrich_schools IS 'Array of schools attended';
COMMENT ON COLUMN contacts.enrich_fields_of_study IS 'Array of fields of study';
COMMENT ON COLUMN contacts.enrich_companies_worked IS 'Array of all companies in work history';
COMMENT ON COLUMN contacts.enrich_titles_held IS 'Array of all titles held';
COMMENT ON COLUMN contacts.enrich_skills IS 'Array of skills from LinkedIn';
COMMENT ON COLUMN contacts.enrich_board_positions IS 'Array of board positions';
COMMENT ON COLUMN contacts.enrich_volunteer_orgs IS 'Array of volunteer organizations';
COMMENT ON COLUMN contacts.enrich_publication_count IS 'Number of publications';
COMMENT ON COLUMN contacts.enrich_award_count IS 'Number of awards/honors';

-- Create useful indexes
CREATE INDEX IF NOT EXISTS idx_contacts_current_company ON contacts(enrich_current_company) WHERE enrich_current_company IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_current_title ON contacts(enrich_current_title) WHERE enrich_current_title IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_total_experience ON contacts(enrich_total_experience_years) WHERE enrich_total_experience_years IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_highest_degree ON contacts(enrich_highest_degree) WHERE enrich_highest_degree IS NOT NULL;

-- GIN indexes for array searching (fast "has company X in history" queries)
CREATE INDEX IF NOT EXISTS idx_contacts_companies_worked_gin ON contacts USING GIN(enrich_companies_worked) WHERE enrich_companies_worked IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_titles_held_gin ON contacts USING GIN(enrich_titles_held) WHERE enrich_titles_held IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_skills_gin ON contacts USING GIN(enrich_skills) WHERE enrich_skills IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_board_positions_gin ON contacts USING GIN(enrich_board_positions) WHERE enrich_board_positions IS NOT NULL;

-- Example queries these indexes enable:

-- Find all candidates who worked at Google
-- SELECT * FROM contacts WHERE 'Google' = ANY(enrich_companies_worked);

-- Find all VPs with 10+ years experience
-- SELECT * FROM contacts
-- WHERE enrich_current_title ILIKE '%vice president%'
-- AND enrich_total_experience_years >= 10;

-- Find candidates with foundation experience
-- SELECT * FROM contacts
-- WHERE enrich_companies_worked && ARRAY['Gates Foundation', 'Ford Foundation', 'Packard Foundation'];

-- Find board members
-- SELECT * FROM contacts
-- WHERE enrich_board_positions IS NOT NULL
-- AND array_length(enrich_board_positions, 1) > 0;

-- Verify the changes
SELECT
  COUNT(*) AS total_contacts,
  COUNT(enrich_current_company) AS has_current_company,
  COUNT(enrich_total_experience_years) AS has_experience_calc,
  COUNT(enrich_companies_worked) AS has_company_history,
  COUNT(enrich_board_positions) AS has_board_positions
FROM contacts;
