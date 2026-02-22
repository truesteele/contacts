-- Pipeline O: SMS Communication History
-- Stores matched SMS conversations from Android SMS Backup & Restore XML

CREATE TABLE IF NOT EXISTS contact_sms_conversations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id bigint REFERENCES contacts(id) ON DELETE CASCADE,
    phone_number text NOT NULL,
    message_count integer DEFAULT 0,
    sent_count integer DEFAULT 0,
    received_count integer DEFAULT 0,
    first_message_date timestamptz,
    last_message_date timestamptz,
    sms_contact_name text,
    match_method text,               -- 'phone', 'exact_name', 'fuzzy_name_gpt'
    match_confidence text,           -- 'high', 'medium'
    sample_messages jsonb,           -- up to 50 representative messages for LLM context
    summary text,                    -- LLM conversation summary
    gathered_at timestamptz DEFAULT now(),
    UNIQUE(contact_id, phone_number)
);

CREATE INDEX IF NOT EXISTS idx_sms_conv_contact ON contact_sms_conversations(contact_id);
