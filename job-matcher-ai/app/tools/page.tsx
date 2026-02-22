'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { Suspense, useEffect } from 'react';

function ToolsRedirect() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const tab = searchParams.get('tab') || 'network-intel';

  useEffect(() => {
    router.replace(`/tools/${tab}`);
  }, [router, tab]);

  return null;
}

export default function ToolsPage() {
  return (
    <Suspense fallback={null}>
      <ToolsRedirect />
    </Suspense>
  );
}
