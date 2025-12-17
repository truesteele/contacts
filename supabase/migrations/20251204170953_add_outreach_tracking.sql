-- Add outreach_history JSON field to track all interactions
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS outreach_history JSONB DEFAULT '[]'::jsonb;

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_contacts_last_contact_date ON contacts(last_contact_date DESC);
CREATE INDEX IF NOT EXISTS idx_contacts_cultivation_stage ON contacts(cultivation_stage);

-- Example structure for outreach_history:
-- [
--   {
--     "date": "2025-12-04",
--     "type": "email",
--     "subject": "Introduction to Outdoorithm",
--     "notes": "Sent intro email about our mission",
--     "outcome": "sent",
--     "logged_at": "2025-12-04T12:34:56.789Z"
--   }
-- ]
