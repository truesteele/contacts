-- Camping Reservation Audit
-- Complete historical record of all camping reservations across Gmail accounts

CREATE TABLE IF NOT EXISTS camping_reservations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Reservation identity
    reservation_number text NOT NULL,
    provider text NOT NULL,
    confirmation_number text,

    -- Location
    campground_name text NOT NULL,
    park_system text,
    site_number text,

    -- Final/canonical dates
    check_in_date date NOT NULL,
    check_out_date date NOT NULL,
    num_nights integer,

    -- Original dates (before any modifications)
    original_check_in date,
    original_check_out date,
    original_num_nights integer,

    -- Trip details
    primary_occupant text,
    num_occupants integer,
    equipment text,
    num_vehicles integer,

    -- Financial
    total_cost numeric(10,2),
    cancellation_fee numeric(10,2),
    refund_amount numeric(10,2),

    -- Status
    status text NOT NULL DEFAULT 'confirmed',
    was_modified boolean DEFAULT false,
    was_cancelled boolean DEFAULT false,
    cancellation_date date,

    -- Weekend / Sunday analysis
    includes_sunday_night boolean,
    sunday_night_dates date[],
    is_weekend_trip boolean,
    day_of_week_checkin text,
    day_of_week_checkout text,

    -- Source tracking
    account_email text NOT NULL,
    gmail_message_ids text[],
    email_subjects text[],

    -- Modification history
    modification_history jsonb,

    -- Raw parsed data for review
    raw_parsed jsonb,

    gathered_at timestamptz DEFAULT now(),

    UNIQUE(reservation_number, provider)
);

CREATE INDEX IF NOT EXISTS idx_camping_res_dates ON camping_reservations(check_in_date);
CREATE INDEX IF NOT EXISTS idx_camping_res_status ON camping_reservations(status);
CREATE INDEX IF NOT EXISTS idx_camping_res_provider ON camping_reservations(provider);
CREATE INDEX IF NOT EXISTS idx_camping_res_campground ON camping_reservations(campground_name);
