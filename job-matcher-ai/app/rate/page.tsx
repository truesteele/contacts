'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

// Justin's schools and companies for shared context matching
const JUSTIN_SCHOOLS = ['Harvard Business School', 'HBS', 'Harvard Kennedy School', 'HKS', 'University of Virginia', 'UVA'];
const JUSTIN_COMPANIES = ['Kindora', 'Google.org', 'Year Up', 'Bridgespan', 'Bridgespan Group', 'Bain', 'Bain & Company', 'True Steele', 'Outdoorithm', 'Outdoorithm Collective'];

interface RateContact {
  id: string;
  first_name: string;
  last_name: string;
  enrich_profile_pic_url: string | null;
  enrich_current_title: string | null;
  enrich_current_company: string | null;
  headline: string | null;
  linkedin_url: string | null;
  ai_proximity_score: number | null;
  ai_proximity_tier: string | null;
  enrich_schools: any;
  enrich_companies_worked: any;
  connected_on: string | null;
}

function getInitials(first: string, last: string): string {
  return `${(first || '')[0] || ''}${(last || '')[0] || ''}`.toUpperCase();
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function extractSchoolNames(schools: any): string[] {
  if (!schools) return [];
  if (Array.isArray(schools)) {
    return schools.map((s: any) => {
      if (typeof s === 'string') return s;
      return s?.schoolName || s?.name || s?.school || '';
    }).filter(Boolean);
  }
  return [];
}

function extractCompanyNames(companies: any): string[] {
  if (!companies) return [];
  if (Array.isArray(companies)) {
    return companies.map((c: any) => {
      if (typeof c === 'string') return c;
      return c?.companyName || c?.name || c?.company || '';
    }).filter(Boolean);
  }
  return [];
}

function findSharedItems(contactItems: string[], justinItems: string[]): string[] {
  const justinLower = justinItems.map(i => i.toLowerCase());
  return contactItems.filter(item => {
    const itemLower = item.toLowerCase();
    return justinLower.some(j => itemLower.includes(j) || j.includes(itemLower));
  });
}

function tierColor(tier: string | null): string {
  if (!tier) return 'bg-gray-100 text-gray-600';
  const t = tier.toLowerCase();
  if (t === 'close' || t === 'inner circle') return 'bg-purple-100 text-purple-700';
  if (t === 'solid') return 'bg-orange-100 text-orange-700';
  if (t === 'acquaintance') return 'bg-green-100 text-green-700';
  if (t === 'recognize') return 'bg-blue-100 text-blue-700';
  return 'bg-gray-100 text-gray-600';
}

function ContactCardSkeleton() {
  return (
    <Card className="w-full max-w-[400px] mx-auto">
      <CardContent className="p-6">
        <div className="flex flex-col items-center gap-4 animate-pulse">
          <div className="w-20 h-20 rounded-full bg-muted" />
          <div className="h-6 w-48 bg-muted rounded" />
          <div className="h-4 w-36 bg-muted rounded" />
          <div className="h-4 w-52 bg-muted rounded" />
          <div className="h-4 w-24 bg-muted rounded" />
          <div className="h-12 w-full bg-muted rounded mt-2" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function RatePage() {
  const [contacts, setContacts] = useState<RateContact[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [unratedCount, setUnratedCount] = useState(0);
  const [ratedCount, setRatedCount] = useState(0);

  useEffect(() => {
    fetchContacts();
  }, []);

  async function fetchContacts() {
    setLoading(true);
    try {
      const res = await fetch('/api/rate');
      const data = await res.json();
      setContacts(data.contacts || []);
      setUnratedCount(data.unrated_count ?? 0);
      setRatedCount(data.rated_count ?? 0);
      setCurrentIndex(0);
    } catch (err) {
      console.error('Failed to fetch contacts:', err);
    } finally {
      setLoading(false);
    }
  }

  const contact = contacts[currentIndex] ?? null;
  const total = unratedCount + ratedCount;

  const sharedSchools = contact
    ? findSharedItems(extractSchoolNames(contact.enrich_schools), JUSTIN_SCHOOLS)
    : [];
  const sharedCompanies = contact
    ? findSharedItems(extractCompanyNames(contact.enrich_companies_worked), JUSTIN_COMPANIES)
    : [];
  const hasSharedContext = sharedSchools.length > 0 || sharedCompanies.length > 0;

  return (
    <div className="min-h-dvh bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b">
        <Link href="/" className="p-1 -ml-1 text-muted-foreground hover:text-foreground">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <span className="text-sm text-muted-foreground">
          {total > 0 ? `${ratedCount} / ${total} rated` : ''}
        </span>
        <div className="w-5" />
      </div>

      {/* Card area */}
      <div className="flex-1 flex items-center justify-center px-4 py-6">
        {loading ? (
          <ContactCardSkeleton />
        ) : !contact ? (
          <div className="text-center text-muted-foreground">
            <p className="text-lg font-medium">No contacts to rate</p>
            <p className="text-sm mt-1">All contacts have been rated.</p>
          </div>
        ) : (
          <Card className="w-full max-w-[400px]">
            <CardContent className="p-6">
              <div className="flex flex-col items-center text-center gap-3">
                {/* Profile photo or initials */}
                {contact.enrich_profile_pic_url ? (
                  <img
                    src={contact.enrich_profile_pic_url}
                    alt={`${contact.first_name} ${contact.last_name}`}
                    className="w-20 h-20 rounded-full object-cover"
                  />
                ) : (
                  <div className="w-20 h-20 rounded-full bg-primary/10 text-primary flex items-center justify-center text-2xl font-semibold">
                    {getInitials(contact.first_name, contact.last_name)}
                  </div>
                )}

                {/* Name */}
                <h2 className="text-xl font-semibold leading-tight">
                  {contact.first_name} {contact.last_name}
                </h2>

                {/* Title @ company */}
                {(contact.enrich_current_title || contact.enrich_current_company) && (
                  <p className="text-sm text-muted-foreground">
                    {contact.enrich_current_title}
                    {contact.enrich_current_title && contact.enrich_current_company && ' @ '}
                    {contact.enrich_current_company}
                  </p>
                )}

                {/* Headline */}
                {contact.headline && (
                  <p className="text-xs text-muted-foreground/70 leading-snug line-clamp-2">
                    {contact.headline}
                  </p>
                )}

                {/* Connected on */}
                {contact.connected_on && (
                  <p className="text-xs text-muted-foreground">
                    Connected {formatDate(contact.connected_on)}
                  </p>
                )}

                {/* AI proximity tier badge */}
                {contact.ai_proximity_tier ? (
                  <Badge className={`${tierColor(contact.ai_proximity_tier)} border-0 text-xs`}>
                    AI: {contact.ai_proximity_tier}
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-xs text-muted-foreground">
                    Not scored
                  </Badge>
                )}

                {/* Shared context */}
                {hasSharedContext && (
                  <div className="w-full mt-2 pt-3 border-t">
                    <p className="text-[11px] uppercase tracking-wider text-muted-foreground/60 font-medium mb-2">
                      Shared Context
                    </p>
                    <div className="flex flex-wrap justify-center gap-1.5">
                      {sharedSchools.map(s => (
                        <span key={s} className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-700">
                          🎓 {s}
                        </span>
                      ))}
                      {sharedCompanies.map(c => (
                        <span key={c} className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-emerald-50 text-emerald-700">
                          🏢 {c}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
