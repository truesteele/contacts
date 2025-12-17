-- Add email verification and type columns
ALTER TABLE contacts 
  ADD COLUMN IF NOT EXISTS email_verified BOOLEAN,
  ADD COLUMN IF NOT EXISTS email_type VARCHAR(10) CHECK (email_type IN ('work', 'personal', 'unknown')),
  ADD COLUMN IF NOT EXISTS work_email VARCHAR(255),
  ADD COLUMN IF NOT EXISTS personal_email VARCHAR(255);

-- Update existing data: Set email_type to 'unknown' for all existing records with emails
UPDATE contacts 
SET email_type = 'unknown' 
WHERE email IS NOT NULL AND email != '' AND email_type IS NULL; 