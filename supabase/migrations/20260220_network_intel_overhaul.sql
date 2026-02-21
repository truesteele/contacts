-- Network Intelligence Overhaul: New columns for wealth signals, structured overlap, and ask-readiness
-- Phase 6 of the Network Intelligence System

-- Rename existing TEXT[] shared_institutions to legacy (contains freetext like "Location: SF", "Current employer: Google")
-- New JSONB column will store structured overlap with temporal analysis (populated by score_overlap.py)
ALTER TABLE contacts RENAME COLUMN shared_institutions TO shared_institutions_legacy;

-- Structured institutional overlap (replaces freetext in ai_tags)
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS shared_institutions JSONB DEFAULT NULL;

-- Denormalized comms summary fields for fast filtering/sorting
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS comms_last_date DATE DEFAULT NULL;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS comms_thread_count SMALLINT DEFAULT 0;

-- FEC political donation data (free wealth signal)
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS fec_donations JSONB DEFAULT NULL;

-- Real estate holdings (wealth signal)
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS real_estate_data JSONB DEFAULT NULL;

-- Ask-readiness assessment (AI-generated per goal)
-- Structure: { "outdoorithm_fundraising": { "score": 87, "tier": "ready_now", ... } }
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS ask_readiness JSONB DEFAULT NULL;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_contacts_familiarity ON contacts(familiarity_rating DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_contacts_comms_last ON contacts(comms_last_date DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_contacts_ask_readiness ON contacts USING GIN(ask_readiness);
