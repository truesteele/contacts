'use client';

import { useEffect } from 'react';

export default function CampaignError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[Campaign Error Boundary]', error);
  }, [error]);

  return (
    <main className="min-h-screen bg-background flex items-center justify-center">
      <div className="max-w-md mx-auto p-6 text-center space-y-4">
        <h2 className="text-lg font-semibold text-destructive">Campaign Error</h2>
        <p className="text-sm text-muted-foreground">
          {error.message || 'An unexpected error occurred'}
        </p>
        {error.digest && (
          <p className="text-xs font-mono text-muted-foreground">Ref: {error.digest}</p>
        )}
        <button
          onClick={reset}
          className="px-4 py-2 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Try again
        </button>
      </div>
    </main>
  );
}
