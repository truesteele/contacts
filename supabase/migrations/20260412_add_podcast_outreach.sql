-- Podcast Outreach Tool: all tables for discovery, scoring, pitching, and campaign tracking

-- Speaker profiles for podcast pitching
CREATE TABLE IF NOT EXISTS speaker_profiles (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name text NOT NULL,
  slug text UNIQUE NOT NULL,
  bio text,
  headline text,
  website_url text,
  linkedin_url text,
  photo_url text,
  topic_pillars jsonb,
  writing_samples jsonb,
  past_appearances jsonb,
  one_sheet_data jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Discovered podcast targets
CREATE TABLE IF NOT EXISTS podcast_targets (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  podcast_index_id bigint,
  itunes_id bigint,
  title text NOT NULL,
  author text,
  description text,
  categories jsonb,
  language text DEFAULT 'en',
  episode_count int,
  last_episode_date timestamptz,
  website_url text,
  rss_url text,
  image_url text,
  host_name text,
  host_email text,
  email_source text,
  email_verified boolean DEFAULT false,
  listener_estimate int,
  activity_status text,
  discovered_at timestamptz DEFAULT now(),
  enriched_at timestamptz,
  UNIQUE(podcast_index_id)
);

-- Recent episodes for pitch personalization
CREATE TABLE IF NOT EXISTS podcast_episodes (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  podcast_target_id bigint REFERENCES podcast_targets(id) ON DELETE CASCADE,
  title text NOT NULL,
  description text,
  published_at timestamptz,
  duration_seconds int,
  episode_url text,
  guests jsonb,
  created_at timestamptz DEFAULT now()
);

-- AI-generated fit scores and pitches
CREATE TABLE IF NOT EXISTS podcast_pitches (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  podcast_target_id bigint REFERENCES podcast_targets(id) ON DELETE CASCADE,
  speaker_profile_id bigint REFERENCES speaker_profiles(id),
  fit_tier text,
  fit_score real,
  fit_rationale text,
  topic_match jsonb,
  episode_hooks jsonb,
  subject_line text,
  subject_line_alt text,
  pitch_body text,
  pitch_body_html text,
  episode_reference text,
  suggested_topics jsonb,
  pitch_status text DEFAULT 'draft',
  approved_at timestamptz,
  approved_by text,
  human_edits text,
  model_used text,
  generated_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Campaign send tracking
CREATE TABLE IF NOT EXISTS podcast_campaigns (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  pitch_id bigint REFERENCES podcast_pitches(id),
  speaker_profile_id bigint REFERENCES speaker_profiles(id),
  sent_from_email text,
  sent_to_email text,
  sent_at timestamptz,
  send_method text,
  gmail_message_id text,
  gmail_thread_id text,
  opened_at timestamptz,
  replied_at timestamptz,
  reply_sentiment text,
  followup_scheduled_at timestamptz,
  followup_sent_at timestamptz,
  followup_body text,
  outcome text,
  recording_date date,
  episode_air_date date,
  episode_url text,
  notes text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Indexes
CREATE INDEX idx_podcast_targets_activity ON podcast_targets(activity_status);
CREATE INDEX idx_podcast_pitches_speaker ON podcast_pitches(speaker_profile_id);
CREATE INDEX idx_podcast_pitches_status ON podcast_pitches(pitch_status);
CREATE INDEX idx_podcast_campaigns_outcome ON podcast_campaigns(outcome);
