-- Add parsed location columns to contacts table
ALTER TABLE contacts 
ADD COLUMN IF NOT EXISTS city TEXT,
ADD COLUMN IF NOT EXISTS state TEXT,
ADD COLUMN IF NOT EXISTS country TEXT;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_contacts_city ON contacts (city) WHERE city IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_state ON contacts (state) WHERE state IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_country ON contacts (country) WHERE country IS NOT NULL;

-- Add comments to document the columns
COMMENT ON COLUMN contacts.city IS 'Parsed city from location_name';
COMMENT ON COLUMN contacts.state IS 'Parsed state/province from location_name';
COMMENT ON COLUMN contacts.country IS 'Parsed country from location_name';

-- Create a view for location analysis
CREATE OR REPLACE VIEW vw_contact_locations AS
SELECT 
    country,
    state,
    city,
    COUNT(*) as contact_count
FROM contacts
WHERE country IS NOT NULL OR state IS NOT NULL OR city IS NOT NULL
GROUP BY country, state, city
ORDER BY country, state, city;