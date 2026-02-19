'use client';

import { ChatInterface } from '@/components/chat-interface';
import { SoCalContacts } from '@/components/socal-contacts';
import { CamelbackCoachSearch } from '@/components/camelback-coach-search';
import { NetworkIntelligence } from '@/components/network-intelligence';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Search, MapPin, Mountain, Network } from 'lucide-react';

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto p-4">
        <Tabs defaultValue="job-search" className="h-[calc(100vh-2rem)]">
          <TabsList className="mb-4">
            <TabsTrigger value="job-search" className="flex items-center gap-2">
              <Search className="w-4 h-4" />
              AI Job Search
            </TabsTrigger>
            <TabsTrigger value="socal-contacts" className="flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              LA & San Diego Contacts
            </TabsTrigger>
            <TabsTrigger value="coach-search" className="flex items-center gap-2">
              <Mountain className="w-4 h-4" />
              Camelback Coaches
            </TabsTrigger>
            <TabsTrigger value="network-intel" className="flex items-center gap-2">
              <Network className="w-4 h-4" />
              Network Intelligence
            </TabsTrigger>
          </TabsList>

          <TabsContent value="job-search" className="h-[calc(100%-60px)]">
            <ChatInterface />
          </TabsContent>

          <TabsContent value="socal-contacts" className="h-[calc(100%-60px)]">
            <SoCalContacts />
          </TabsContent>

          <TabsContent value="coach-search" className="h-[calc(100%-60px)]">
            <CamelbackCoachSearch />
          </TabsContent>

          <TabsContent value="network-intel" className="h-[calc(100%-60px)]">
            <NetworkIntelligence />
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
