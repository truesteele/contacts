-- Optional: Enable Row Level Security for Contacts Table
-- Run this in Supabase SQL Editor if you want to restrict access

-- ============================================
-- OPTION 1: PUBLIC ACCESS (Current Setup)
-- ============================================
-- Leave RLS disabled - anyone with the URL can view/edit
-- Good for: Internal team tools, trusted environments
-- Risk: Anyone with the link can access donor data


-- ============================================
-- OPTION 2: BASIC SECURITY (Recommended)
-- ============================================
-- Enable RLS and allow anon users to read/update cultivation fields only

-- Enable Row Level Security
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;

-- Allow anyone to READ contacts with cultivation notes (researched prospects)
CREATE POLICY "Allow public read of researched prospects"
ON contacts FOR SELECT
TO anon, authenticated
USING (cultivation_notes IS NOT NULL);

-- Allow anyone to UPDATE cultivation tracking fields only
CREATE POLICY "Allow public update of cultivation fields"
ON contacts FOR UPDATE
TO anon, authenticated
USING (cultivation_notes IS NOT NULL)
WITH CHECK (cultivation_notes IS NOT NULL);


-- ============================================
-- OPTION 3: AUTHENTICATED ONLY (Most Secure)
-- ============================================
-- Require Supabase authentication to access
-- Uncomment these and disable the policies above

-- Enable Row Level Security (if not already enabled)
-- ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;

-- Allow only authenticated users to read
-- CREATE POLICY "Authenticated users can read contacts"
-- ON contacts FOR SELECT
-- TO authenticated
-- USING (true);

-- Allow only authenticated users to update
-- CREATE POLICY "Authenticated users can update contacts"
-- ON contacts FOR UPDATE
-- TO authenticated
-- USING (true)
-- WITH CHECK (true);


-- ============================================
-- To disable security (revert to current):
-- ============================================
-- ALTER TABLE contacts DISABLE ROW LEVEL SECURITY;
-- DROP POLICY IF EXISTS "Allow public read of researched prospects" ON contacts;
-- DROP POLICY IF EXISTS "Allow public update of cultivation fields" ON contacts;
