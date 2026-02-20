'use client';

import { ChatInterface } from '@/components/chat-interface';
import { SoCalContacts } from '@/components/socal-contacts';
import { CamelbackCoachSearch } from '@/components/camelback-coach-search';
import { NetworkCopilot } from '@/components/network-copilot';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Search, MapPin, Mountain, Network, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';

function ToolsTabs() {
  const searchParams = useSearchParams();
  const defaultTab = searchParams.get('tab') || 'network-intel';

  return (
    <Tabs defaultValue={defaultTab} className="h-[calc(100vh-2rem)]">
      <div className="flex items-center gap-2 mb-4">
        <Link
          href="/"
          className="min-w-[40px] min-h-[40px] flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-muted"
          aria-label="Back to dashboard"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <TabsList>
          <TabsTrigger value="network-intel" className="flex items-center gap-2">
            <Network className="w-4 h-4" />
            Network Intelligence
          </TabsTrigger>
          <TabsTrigger value="job-search" className="flex items-center gap-2">
            <Search className="w-4 h-4" />
            AI Job Search
          </TabsTrigger>
          <TabsTrigger value="socal-contacts" className="flex items-center gap-2">
            <MapPin className="w-4 h-4" />
            LA & San Diego
          </TabsTrigger>
          <TabsTrigger value="coach-search" className="flex items-center gap-2">
            <Mountain className="w-4 h-4" />
            Camelback Coaches
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="network-intel" className="h-[calc(100%-60px)]">
        <NetworkCopilot />
      </TabsContent>

      <TabsContent value="job-search" className="h-[calc(100%-60px)]">
        <ChatInterface />
      </TabsContent>

      <TabsContent value="socal-contacts" className="h-[calc(100%-60px)]">
        <SoCalContacts />
      </TabsContent>

      <TabsContent value="coach-search" className="h-[calc(100%-60px)]">
        <CamelbackCoachSearch />
      </TabsContent>
    </Tabs>
  );
}

export default function ToolsPage() {
  return (
    <main className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto p-4">
        <Suspense fallback={<div className="h-screen flex items-center justify-center text-muted-foreground">Loading...</div>}>
          <ToolsTabs />
        </Suspense>
      </div>
    </main>
  );
}
