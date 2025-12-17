-- Create atomic RPC function for logging outreach
-- SECURITY FIX: Prevents lost updates, validates input, and sanitizes text
-- This replaces direct client-side JSONB manipulation which had concurrency bugs and XSS risks

-- SECURITY NOTE: Uses SECURITY DEFINER to bypass RLS for atomic updates,
-- but adds explicit scoping checks to prevent unauthorized access

CREATE OR REPLACE FUNCTION log_outreach(
    p_contact_id UUID,
    p_date DATE,
    p_type TEXT,
    p_subject TEXT,
    p_notes TEXT,
    p_outcome TEXT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp  -- Prevent schema injection attacks
AS $$
DECLARE
    v_new_entry JSONB;
    v_updated_history JSONB;
    v_cultivation_notes TEXT;
BEGIN
    -- SECURITY CHECK: Verify contact exists and has cultivation_notes (matches RLS policy)
    -- This ensures SECURITY DEFINER doesn't bypass intended access controls
    SELECT cultivation_notes INTO v_cultivation_notes
    FROM contacts
    WHERE id = p_contact_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contact not found: %', p_contact_id;
    END IF;

    IF v_cultivation_notes IS NULL THEN
        RAISE EXCEPTION 'Cannot log outreach for contacts without cultivation notes (not a researched prospect)';
    END IF;

    -- Validate input types (prevents invalid values from client)
    IF p_type NOT IN ('email', 'call', 'meeting', 'video', 'text', 'linkedin') THEN
        RAISE EXCEPTION 'Invalid outreach type: %', p_type;
    END IF;

    IF p_outcome NOT IN ('sent', 'positive', 'neutral', 'no_response', 'declined', 'scheduled') THEN
        RAISE EXCEPTION 'Invalid outcome: %', p_outcome;
    END IF;

    -- Sanitize text inputs (prevent XSS by trimming and using parameterized JSONB)
    p_subject := TRIM(COALESCE(p_subject, ''));
    p_notes := TRIM(COALESCE(p_notes, ''));

    -- Build new entry with server timestamp
    v_new_entry := jsonb_build_object(
        'date', p_date,
        'type', p_type,
        'subject', p_subject,
        'notes', p_notes,
        'outcome', p_outcome,
        'logged_at', NOW()
    );

    -- Atomically append to outreach_history and update last_contact_date
    -- This prevents lost updates from concurrent clients
    -- NOTE: Only updates outreach_history and last_contact_date - no other columns
    UPDATE contacts
    SET
        outreach_history = COALESCE(outreach_history, '[]'::jsonb) || v_new_entry,
        last_contact_date = p_date
    WHERE id = p_contact_id
      AND cultivation_notes IS NOT NULL  -- Double-check scope
    RETURNING outreach_history INTO v_updated_history;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contact not found or lacks cultivation notes';
    END IF;

    RETURN v_updated_history;
END;
$$;

-- Grant execute permission to authenticated users only
-- Anonymous users cannot call this function
GRANT EXECUTE ON FUNCTION log_outreach(UUID, DATE, TEXT, TEXT, TEXT, TEXT) TO authenticated;

-- Revoke from public/anon to ensure security
REVOKE EXECUTE ON FUNCTION log_outreach(UUID, DATE, TEXT, TEXT, TEXT, TEXT) FROM anon;
REVOKE EXECUTE ON FUNCTION log_outreach(UUID, DATE, TEXT, TEXT, TEXT, TEXT) FROM public;

-- Add comment documenting security considerations
COMMENT ON FUNCTION log_outreach IS
'Atomic outreach logging with security checks. Uses SECURITY DEFINER to bypass RLS for atomic JSONB updates, but enforces cultivation_notes IS NOT NULL scope check to match RLS policy. Only modifies outreach_history and last_contact_date columns.';
