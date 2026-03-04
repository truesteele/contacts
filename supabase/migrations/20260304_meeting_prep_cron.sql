-- Meeting Prep: enable pg_cron + pg_net, create observability table, schedule daily job
-- Runs at 15:00 UTC = 7am PST (winter) / 8am PDT (summer)

-- Enable extensions (available on Supabase but not yet installed)
CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

-- Observability table for tracking meeting prep runs
CREATE TABLE IF NOT EXISTS meeting_prep_runs (
  id BIGSERIAL PRIMARY KEY,
  run_date DATE NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'running',
  meetings_found INT,
  memos_generated INT,
  google_doc_url TEXT,
  error_message TEXT,
  metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_meeting_prep_runs_date ON meeting_prep_runs(run_date);

-- Schedule daily meeting prep at 15:00 UTC (7am PST / 8am PDT)
-- pg_cron → pg_net HTTP POST → Edge Function
SELECT cron.schedule(
  'daily-meeting-prep',
  '0 15 * * *',
  $$
  SELECT net.http_post(
    url := 'https://ypqsrejrsocebnldicke.supabase.co/functions/v1/daily-meeting-prep',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('supabase.service_role_key'),
      'Content-Type', 'application/json'
    ),
    body := jsonb_build_object('source', 'pg_cron', 'ts', now()::text)
  );
  $$
);
