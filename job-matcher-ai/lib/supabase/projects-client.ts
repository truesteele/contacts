import { createBrowserClient } from '@supabase/ssr'

export function createProjectsClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_PROJECTS_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_PROJECTS_SUPABASE_ANON_KEY!
  )
}
