-- Daily Phone Backup Sync: Call Logs
-- Stores individual call records matched to contacts from Android call backup XML

CREATE TABLE IF NOT EXISTS contact_call_logs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id bigint REFERENCES contacts(id) ON DELETE CASCADE,
    phone_number text NOT NULL,
    call_date timestamptz NOT NULL,
    call_type text NOT NULL,        -- 'incoming', 'outgoing', 'missed', 'voicemail'
    duration_seconds integer DEFAULT 0,
    contact_name_in_phone text,
    match_method text,              -- 'phone', 'exact_name'
    match_confidence text,          -- 'high', 'medium'
    gathered_at timestamptz DEFAULT now(),
    UNIQUE(contact_id, phone_number, call_date)
);

CREATE INDEX IF NOT EXISTS idx_call_logs_contact ON contact_call_logs(contact_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_date ON contact_call_logs(call_date);

-- Add call stat columns to contacts
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS comms_call_count integer;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS comms_last_call date;
