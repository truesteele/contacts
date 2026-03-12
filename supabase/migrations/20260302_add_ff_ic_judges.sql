-- Flourish Fund Innovation Challenge: Judge Candidates
-- Stores researched judge profiles separately from the main contacts table

CREATE TABLE IF NOT EXISTS ff_ic_judges (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE,
    organization text,
    category text NOT NULL,           -- 'celebrity', 'donor_stakeholder', 'lived_experience', 'subject_matter_expert'
    tier text,                        -- 'tier_1_ready', 'tier_2_warm', 'tier_3_intro_needed', 'tier_4_cold'
    linkedin_url text,
    role_title text,
    relationship text,                -- notes on connection path
    foster_care_connection text,      -- summary of foster care relevance
    outreach_hook text,               -- personalized angle from research
    recommended_sender text,          -- who should send the email
    outreach_wave integer,            -- 1-5 per domino strategy
    request_sent boolean DEFAULT false,
    response text,                    -- reply status
    first_round_ask boolean DEFAULT false,
    research_profile jsonb,           -- full research profile
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ff_ic_judges_category ON ff_ic_judges(category);
CREATE INDEX IF NOT EXISTS idx_ff_ic_judges_tier ON ff_ic_judges(tier);
CREATE INDEX IF NOT EXISTS idx_ff_ic_judges_wave ON ff_ic_judges(outreach_wave);
