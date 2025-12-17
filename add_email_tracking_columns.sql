-- SQL script to add email tracking columns to the Supabase contacts table
-- Execute this script in the Supabase SQL Editor or apply as a migration

-- Add email tracking columns to track enrichment status and sources
ALTER TABLE contacts 
ADD COLUMN IF NOT EXISTS email_enriched_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS email_source TEXT,
ADD COLUMN IF NOT EXISTS email_type TEXT,
ADD COLUMN IF NOT EXISTS personal_email TEXT;

-- Create indexes for better query performance on new columns
CREATE INDEX IF NOT EXISTS idx_contacts_email_enriched_at ON contacts (email_enriched_at) WHERE email_enriched_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_email_source ON contacts (email_source) WHERE email_source IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_email_type ON contacts (email_type) WHERE email_type IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_personal_email ON contacts (personal_email) WHERE personal_email IS NOT NULL;

-- Add a comment to document the purpose of these columns
COMMENT ON COLUMN contacts.email_enriched_at IS 'Timestamp when email data was last enriched or updated';
COMMENT ON COLUMN contacts.email_source IS 'Source of the email data (e.g., enrichment_service, manual_entry, import)';
COMMENT ON COLUMN contacts.email_type IS 'Type of email (e.g., work, personal, unknown)';
COMMENT ON COLUMN contacts.personal_email IS 'Personal email address of the contact';

-- Create a view for contacts with email tracking information
CREATE OR REPLACE VIEW vw_contacts_email_tracking AS
SELECT 
  id,
  first_name,
  last_name,
  email,
  work_email,
  personal_email,
  email_type,
  email_source,
  email_enriched_at,
  CASE 
    WHEN email_enriched_at IS NOT NULL THEN 'enriched'
    WHEN email IS NOT NULL OR work_email IS NOT NULL OR personal_email IS NOT NULL THEN 'has_email'
    ELSE 'no_email'
  END AS email_status
FROM 
  contacts
ORDER BY 
  email_enriched_at DESC NULLS LAST;