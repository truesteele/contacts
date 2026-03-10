-- Sally Steele Network Intelligence Pipeline
-- Parallel tables mirroring Justin's schema for Sally's contacts

-- Sally's contacts table
CREATE TABLE IF NOT EXISTS sally_contacts (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  first_name text,
  last_name text,
  normalized_full_name text,
  linkedin_url text,
  linkedin_username text,
  email text,
  email_2 text,
  company text,
  position text,
  headline text,
  summary text,
  city text,
  state text,
  connected_on date,
  -- Apify enrichment
  enrich_current_company text,
  enrich_current_title text,
  enrich_current_since text,
  enrich_years_in_current_role real,
  enrich_total_experience_years real,
  enrich_follower_count int,
  enrich_connections int,
  enrich_schools text[],
  enrich_companies_worked text[],
  enrich_titles_held text[],
  enrich_skills text[],
  enrich_board_positions text[],
  enrich_volunteer_orgs text[],
  enrich_employment jsonb,
  enrich_education jsonb,
  enriched_at timestamptz,
  enrichment_source text,
  -- AI scoring
  ai_tags jsonb,
  ai_proximity_score smallint,
  ai_proximity_tier text,
  ai_capacity_score smallint,
  ai_capacity_tier text,
  ai_outdoorithm_fit text,
  -- Comms
  comms_summary jsonb,
  comms_closeness text,
  comms_momentum text,
  comms_reasoning text,
  comms_last_date date,
  comms_thread_count smallint DEFAULT 0,
  comms_meeting_count smallint DEFAULT 0,
  comms_last_meeting date,
  comms_call_count smallint DEFAULT 0,
  comms_last_call date,
  -- Donor scoring
  ask_readiness jsonb,
  fec_donations jsonb,
  real_estate_data jsonb,
  -- Campaign
  campaign_2026 jsonb,
  -- Overlap with Justin's network
  justin_contact_id bigint REFERENCES contacts(id),
  -- Metadata
  familiarity_rating smallint,
  contact_pools text[],
  shared_institutions jsonb,
  oc_engagement jsonb,
  embedding vector(768),
  interests_embedding vector(768),
  last_import_date timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sally_contacts_linkedin ON sally_contacts(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_sally_contacts_name ON sally_contacts(normalized_full_name);
CREATE INDEX IF NOT EXISTS idx_sally_contacts_ask ON sally_contacts USING GIN(ask_readiness);

-- Sally's email threads (mirrors contact_email_threads)
CREATE TABLE IF NOT EXISTS sally_contact_email_threads (
  id bigserial PRIMARY KEY,
  contact_id bigint NOT NULL REFERENCES sally_contacts(id) ON DELETE CASCADE,
  thread_id text NOT NULL,
  account_email text NOT NULL,
  channel text DEFAULT 'email',
  subject text,
  snippet text,
  message_count int,
  first_message_date timestamptz,
  last_message_date timestamptz,
  direction text,
  participants jsonb,
  labels jsonb,
  raw_messages jsonb,
  summary text,
  is_group boolean DEFAULT false,
  participant_count smallint,
  gathered_at timestamptz DEFAULT now(),
  UNIQUE(contact_id, thread_id, account_email)
);

CREATE INDEX IF NOT EXISTS idx_scet_contact_id ON sally_contact_email_threads(contact_id);

-- Sally's calendar events (mirrors contact_calendar_events)
CREATE TABLE IF NOT EXISTS sally_contact_calendar_events (
  id bigserial PRIMARY KEY,
  contact_id bigint NOT NULL REFERENCES sally_contacts(id) ON DELETE CASCADE,
  event_id text NOT NULL,
  ical_uid text,
  account_email text NOT NULL,
  summary text,
  description text,
  start_time timestamptz,
  end_time timestamptz,
  duration_minutes int,
  location text,
  event_type text,
  attendee_count smallint,
  attendees jsonb,
  organizer_email text,
  is_organizer boolean,
  response_status text,
  recurring boolean DEFAULT false,
  conference_type text,
  gathered_at timestamptz DEFAULT now(),
  UNIQUE(contact_id, event_id, account_email)
);

CREATE INDEX IF NOT EXISTS idx_scce_contact_id ON sally_contact_calendar_events(contact_id);

-- Sally's SMS conversations (mirrors contact_sms_conversations)
CREATE TABLE IF NOT EXISTS sally_contact_sms_conversations (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  contact_id bigint REFERENCES sally_contacts(id) ON DELETE CASCADE,
  phone_number text NOT NULL,
  message_count integer DEFAULT 0,
  sent_count integer DEFAULT 0,
  received_count integer DEFAULT 0,
  first_message_date timestamptz,
  last_message_date timestamptz,
  sms_contact_name text,
  match_method text,
  match_confidence text,
  sample_messages jsonb,
  summary text,
  gathered_at timestamptz DEFAULT now(),
  UNIQUE(contact_id, phone_number)
);

CREATE INDEX IF NOT EXISTS idx_ssms_contact_id ON sally_contact_sms_conversations(contact_id);
