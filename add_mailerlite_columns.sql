-- SQL script to add MailerLite integration columns to the Supabase contacts table
-- Execute this script in the Supabase SQL Editor

-- Add columns for tracking sync status with MailerLite
ALTER TABLE contacts 
ADD COLUMN IF NOT EXISTS synced_to_mailerlite BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS mailerlite_sync_date TIMESTAMP WITHOUT TIME ZONE;

-- Add columns for tracking unsubscribe status
ALTER TABLE contacts 
ADD COLUMN IF NOT EXISTS unsubscribed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS unsubscribed_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS unsubscribe_source VARCHAR(50);

-- Add columns for tracking MailerLite subscriber details
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS mailerlite_subscriber_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS mailerlite_groups TEXT[],
ADD COLUMN IF NOT EXISTS mailerlite_status VARCHAR(20);

-- Create an index to speed up email searches (especially for unsubscribe synchronization)
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts (email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_work_email ON contacts (work_email) WHERE work_email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_personal_email ON contacts (personal_email) WHERE personal_email IS NOT NULL;

-- Update function to prevent syncing unsubscribed contacts to MailerLite
CREATE OR REPLACE FUNCTION prevent_sync_unsubscribed()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.unsubscribed = TRUE AND NEW.synced_to_mailerlite = TRUE THEN
    -- Reset the synced flag to ensure the unsubscribe gets propagated to MailerLite
    NEW.synced_to_mailerlite := FALSE;
    -- Record when the sync status was reset
    NEW.mailerlite_sync_date := NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to apply the function
DROP TRIGGER IF EXISTS tr_prevent_sync_unsubscribed ON contacts;
CREATE TRIGGER tr_prevent_sync_unsubscribed
BEFORE UPDATE ON contacts
FOR EACH ROW
EXECUTE FUNCTION prevent_sync_unsubscribed();

-- Create a view for easy access to contacts ready for MailerLite sync
CREATE OR REPLACE VIEW vw_contacts_for_mailerlite AS
SELECT 
  id,
  first_name,
  last_name,
  COALESCE(work_email, email, personal_email) AS best_email,
  email,
  work_email,
  personal_email,
  company,
  position,
  taxonomy_classification,
  email_verified,
  unsubscribed,
  synced_to_mailerlite
FROM 
  contacts
WHERE 
  email_verified = TRUE
  AND unsubscribed = FALSE
  AND (
    email IS NOT NULL OR 
    work_email IS NOT NULL OR 
    personal_email IS NOT NULL
  );

-- Create a view for contacts that have unsubscribed
CREATE OR REPLACE VIEW vw_unsubscribed_contacts AS
SELECT 
  id,
  first_name,
  last_name,
  email,
  work_email,
  personal_email,
  unsubscribed_at,
  unsubscribe_source
FROM 
  contacts
WHERE 
  unsubscribed = TRUE; 