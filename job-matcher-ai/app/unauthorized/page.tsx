'use client'

import { createClient } from '@/lib/supabase/client'

export default function UnauthorizedPage() {
  const handleSignOut = async () => {
    const supabase = createClient()
    await supabase.auth.signOut()
    window.location.href = '/login'
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm mx-auto px-6 text-center">
        <h1 className="font-display text-2xl text-foreground mb-2">
          Access Denied
        </h1>
        <p className="text-muted-foreground text-sm mb-6">
          Your Google account is not authorized to access this application.
        </p>
        <button
          onClick={handleSignOut}
          className="px-4 py-2 text-sm font-medium rounded-lg border border-border bg-card hover:bg-accent transition-colors text-foreground"
        >
          Sign out and try a different account
        </button>
      </div>
    </div>
  )
}
