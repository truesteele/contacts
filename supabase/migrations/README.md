# Supabase Migrations

This directory contains all database migrations for the donor prospect management system.

## Migration Files

Migrations are named with the format: `YYYYMMDDHHMMSS_migration_name.sql`

### Security-Critical Migrations

**20251204172645_enable_rls_and_auth_policies.sql**
- Enables Row Level Security on contacts table
- Restricts access to authenticated users only
- **CRITICAL:** Must be applied before deploying to production

**20251204172700_create_log_outreach_rpc.sql**
- Creates secure RPC function for logging outreach
- Validates input server-side
- Prevents XSS and lost-update concurrency bugs
- **CRITICAL:** Required for outreach tracking feature

### Feature Migrations

**20251204170953_add_outreach_tracking.sql**
- Adds `outreach_history` JSONB field
- Adds indexes for performance
- Required for CRM outreach tracking

## Applying Migrations

### Via Supabase MCP Server (Recommended)
The migrations have already been applied via the MCP server.

### Via Supabase CLI
```bash
# Apply all pending migrations
supabase db push

# Or apply specific migration
psql $DATABASE_URL -f supabase/migrations/20251204172645_enable_rls_and_auth_policies.sql
```

### Via Supabase Dashboard
1. Go to SQL Editor
2. Copy/paste migration SQL
3. Execute

## Verification

After applying security migrations, verify:

```sql
-- Check RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public' AND tablename = 'contacts';
-- Should return: rowsecurity = true

-- Check policies exist
SELECT policyname, cmd, roles
FROM pg_policies
WHERE tablename = 'contacts';
-- Should show 2 policies for authenticated role

-- Check RPC function exists
SELECT proname, proowner::regrole
FROM pg_proc
WHERE proname = 'log_outreach';
-- Should return: log_outreach
```

## Rollback (Emergency Only)

```sql
-- To disable RLS (NOT RECOMMENDED FOR PRODUCTION)
ALTER TABLE contacts DISABLE ROW LEVEL SECURITY;

-- To remove policies
DROP POLICY IF EXISTS "authenticated_users_read_researched_prospects" ON contacts;
DROP POLICY IF EXISTS "authenticated_users_update_cultivation" ON contacts;

-- To remove RPC function
DROP FUNCTION IF EXISTS log_outreach(UUID, DATE, TEXT, TEXT, TEXT, TEXT);
```

## Migration History

All applied migrations are tracked in Supabase's `supabase_migrations.schema_migrations` table.
