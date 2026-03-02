-- Deal Activities: auto-tagged communication touchpoints linked to deals
-- Populated by sync_deal_activities.py from contact_email_threads,
-- contact_calendar_events, and contact_call_logs

CREATE TABLE IF NOT EXISTS deal_activities (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  contact_id integer REFERENCES contacts(id),
  activity_type text NOT NULL,        -- 'email_sent', 'email_received', 'email_bidirectional', 'meeting', 'call'
  source_table text NOT NULL,         -- 'contact_email_threads', 'contact_calendar_events', 'contact_call_logs'
  source_id bigint NOT NULL,          -- id from the source table
  activity_date timestamptz NOT NULL, -- when it happened
  subject text,                       -- email subject or meeting title
  summary text,                       -- email summary or meeting context
  account_email text,                 -- which Gmail account
  metadata jsonb,                     -- extra: direction, duration_minutes, attendee_count, etc.
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(deal_id, source_table, source_id)
);

CREATE INDEX idx_deal_activities_deal ON deal_activities(deal_id, activity_date DESC);
CREATE INDEX idx_deal_activities_contact ON deal_activities(contact_id);
