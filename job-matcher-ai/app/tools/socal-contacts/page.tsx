'use client';

import { SoCalContacts } from '@/components/socal-contacts';
import Link from 'next/link';
import { ArrowLeft, MapPin } from 'lucide-react';

export default function SoCalContactsPage() {
  return (
    <main className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto p-4">
        <div className="page-header">
          <Link href="/" className="page-back" aria-label="Back to dashboard">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="w-8 h-8 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-600">
            <MapPin className="w-4 h-4" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight">SoCal Contacts</h1>
        </div>
        <div className="h-[calc(100vh-5rem)]">
          <SoCalContacts />
        </div>
      </div>
    </main>
  );
}
