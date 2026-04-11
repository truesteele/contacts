-- Fix podcast outreach schema: NOT NULL constraints, missing indexes,
-- ON DELETE behavior, updated_at triggers, itunes_id uniqueness

-- 1. Add NOT NULL to FK columns that should never be null
ALTER TABLE podcast_episodes
  ALTER COLUMN podcast_target_id SET NOT NULL;

ALTER TABLE podcast_pitches
  ALTER COLUMN podcast_target_id SET NOT NULL;

-- 2. Add NOT NULL to timestamp columns
ALTER TABLE speaker_profiles
  ALTER COLUMN created_at SET NOT NULL,
  ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE podcast_targets
  ALTER COLUMN discovered_at SET NOT NULL;

ALTER TABLE podcast_episodes
  ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE podcast_pitches
  ALTER COLUMN generated_at SET NOT NULL,
  ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE podcast_campaigns
  ALTER COLUMN created_at SET NOT NULL,
  ALTER COLUMN updated_at SET NOT NULL;

-- 3. Add ON DELETE CASCADE to podcast_campaigns FKs
-- (drop + re-add since ALTER CONSTRAINT doesn't work for FK behavior)
ALTER TABLE podcast_campaigns
  DROP CONSTRAINT IF EXISTS podcast_campaigns_pitch_id_fkey;
ALTER TABLE podcast_campaigns
  ADD CONSTRAINT podcast_campaigns_pitch_id_fkey
  FOREIGN KEY (pitch_id) REFERENCES podcast_pitches(id) ON DELETE CASCADE;

ALTER TABLE podcast_campaigns
  DROP CONSTRAINT IF EXISTS podcast_campaigns_speaker_profile_id_fkey;
ALTER TABLE podcast_campaigns
  ADD CONSTRAINT podcast_campaigns_speaker_profile_id_fkey
  FOREIGN KEY (speaker_profile_id) REFERENCES speaker_profiles(id) ON DELETE SET NULL;

-- Also fix podcast_pitches.speaker_profile_id (should SET NULL, not error)
ALTER TABLE podcast_pitches
  DROP CONSTRAINT IF EXISTS podcast_pitches_speaker_profile_id_fkey;
ALTER TABLE podcast_pitches
  ADD CONSTRAINT podcast_pitches_speaker_profile_id_fkey
  FOREIGN KEY (speaker_profile_id) REFERENCES speaker_profiles(id) ON DELETE SET NULL;

-- 4. Add missing indexes
CREATE INDEX IF NOT EXISTS idx_podcast_episodes_target
  ON podcast_episodes(podcast_target_id);

CREATE INDEX IF NOT EXISTS idx_podcast_campaigns_pitch
  ON podcast_campaigns(pitch_id);

CREATE INDEX IF NOT EXISTS idx_podcast_campaigns_speaker
  ON podcast_campaigns(speaker_profile_id);

-- 5. Add itunes_id partial unique index
CREATE UNIQUE INDEX IF NOT EXISTS idx_podcast_targets_itunes_id
  ON podcast_targets(itunes_id)
  WHERE itunes_id IS NOT NULL;

-- 6. Add unique constraint for dedup: one pitch per (podcast, speaker)
CREATE UNIQUE INDEX IF NOT EXISTS idx_podcast_pitches_target_speaker
  ON podcast_pitches(podcast_target_id, speaker_profile_id);

-- 7. Add updated_at triggers (reuse existing update_updated_at_column function)
CREATE OR REPLACE TRIGGER set_speaker_profiles_updated_at
  BEFORE UPDATE ON speaker_profiles
  FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE OR REPLACE TRIGGER set_podcast_pitches_updated_at
  BEFORE UPDATE ON podcast_pitches
  FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE OR REPLACE TRIGGER set_podcast_campaigns_updated_at
  BEFORE UPDATE ON podcast_campaigns
  FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
