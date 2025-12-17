-- Enable Row Level Security on contacts table
-- SECURITY FIX: Previously database was open to anyone with anon key
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;

-- Policy: Only authenticated users can read contacts with cultivation notes
-- This restricts anonymous access while allowing authenticated staff to view prospects
CREATE POLICY "authenticated_users_read_researched_prospects"
ON contacts FOR SELECT
TO authenticated
USING (cultivation_notes IS NOT NULL);

-- Policy: Only authenticated users can update cultivation fields
-- This prevents anonymous users from modifying donor data
CREATE POLICY "authenticated_users_update_cultivation"
ON contacts FOR UPDATE
TO authenticated
USING (cultivation_notes IS NOT NULL)
WITH CHECK (cultivation_notes IS NOT NULL);

-- Note: After applying this migration, you must:
-- 1. Set up user accounts in Supabase Auth
-- 2. Update frontend to require authentication (login screen)
-- 3. Test that anonymous users are properly blocked
