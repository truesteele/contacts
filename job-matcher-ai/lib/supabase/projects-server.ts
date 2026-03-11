import { createClient } from '@supabase/supabase-js'

export function createProjectsServerClient() {
  return createClient(
    process.env.NEXT_PUBLIC_PROJECTS_SUPABASE_URL!,
    process.env.PROJECTS_SUPABASE_SERVICE_ROLE_KEY!
  )
}
