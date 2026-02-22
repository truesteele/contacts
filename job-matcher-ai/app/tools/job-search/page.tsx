'use client';

import { ChatInterface } from '@/components/chat-interface';
import Link from 'next/link';
import { ArrowLeft, Search } from 'lucide-react';

export default function JobSearchPage() {
  return (
    <main className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto p-4">
        <div className="page-header">
          <Link href="/" className="page-back" aria-label="Back to dashboard">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-600">
            <Search className="w-4 h-4" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight">AI Job Search</h1>
        </div>
        <div className="h-[calc(100vh-5rem)]">
          <ChatInterface />
        </div>
      </div>
    </main>
  );
}
