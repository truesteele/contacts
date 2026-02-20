-- Add familiarity_rating columns for manual contact rating
-- Scale: 0=Don't Know, 1=Recognize, 2=Acquaintance, 3=Solid, 4=Close
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS familiarity_rating SMALLINT CHECK (familiarity_rating >= 0 AND familiarity_rating <= 4);
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS familiarity_rated_at TIMESTAMPTZ;
