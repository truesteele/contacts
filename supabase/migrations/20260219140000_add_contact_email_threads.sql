-- Phase 5: Communication History
-- Raw email thread storage for Gmail data across 5 Google Workspace accounts

CREATE TABLE IF NOT EXISTS contact_email_threads (
  id bigserial PRIMARY KEY,
  contact_id bigint NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  thread_id text NOT NULL,            -- Gmail thread ID
  account_email text NOT NULL,        -- Which Google account
  subject text,
  snippet text,                       -- Gmail snippet preview
  message_count int,
  first_message_date timestamptz,
  last_message_date timestamptz,
  direction text,                     -- 'sent' | 'received' | 'bidirectional'
  participants jsonb,                 -- [{email, name}]
  labels jsonb,                       -- Gmail labels
  raw_messages jsonb,                 -- Full raw message data (headers, body text, dates)
  summary text,                       -- LLM-generated thread summary
  gathered_at timestamptz DEFAULT now(),
  UNIQUE(contact_id, thread_id, account_email)
);

CREATE INDEX IF NOT EXISTS idx_cet_contact_id ON contact_email_threads(contact_id);
CREATE INDEX IF NOT EXISTS idx_cet_last_message ON contact_email_threads(last_message_date DESC);
