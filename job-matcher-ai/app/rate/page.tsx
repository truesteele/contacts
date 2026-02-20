'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Undo2, SkipForward } from 'lucide-react';
import Link from 'next/link';

// Justin's schools and companies for shared context matching
const JUSTIN_SCHOOLS = ['Harvard Business School', 'HBS', 'Harvard Kennedy School', 'HKS', 'University of Virginia', 'UVA'];
const JUSTIN_COMPANIES = ['Kindora', 'Google.org', 'Year Up', 'Bridgespan', 'Bridgespan Group', 'Bain', 'Bain & Company', 'True Steele', 'Outdoorithm', 'Outdoorithm Collective'];

const RATING_LEVELS = [
  { level: 0, label: "Don't Know", color: 'bg-gray-100 text-gray-700 active:bg-gray-200' },
  { level: 1, label: 'Recognize', color: 'bg-blue-50 text-blue-700 active:bg-blue-100' },
  { level: 2, label: 'Acquaintance', color: 'bg-green-50 text-green-700 active:bg-green-100' },
  { level: 3, label: 'Solid', color: 'bg-orange-50 text-orange-700 active:bg-orange-100' },
  { level: 4, label: 'Close', color: 'bg-purple-50 text-purple-700 active:bg-purple-100' },
];

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
  enrich_schools: unknown;
  enrich_companies_worked: unknown;
  connected_on: string | null;
}

interface UndoState {
  contact: RateContact;
  previousRating: number | null;
}

function getInitials(first: string, last: string): string {
  return `${(first || '')[0] || ''}${(last || '')[0] || ''}`.toUpperCase();
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function extractSchoolNames(schools: unknown): string[] {
  if (!schools || !Array.isArray(schools)) return [];
  return schools.map((s: Record<string, unknown>) => {
    if (typeof s === 'string') return s;
    return (s?.schoolName || s?.name || s?.school || '') as string;
  }).filter(Boolean);
}

function extractCompanyNames(companies: unknown): string[] {
  if (!companies || !Array.isArray(companies)) return [];
  return companies.map((c: Record<string, unknown>) => {
    if (typeof c === 'string') return c;
    return (c?.companyName || c?.name || c?.company || '') as string;
  }).filter(Boolean);
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
  const [animatingOut, setAnimatingOut] = useState(false);
  const [animatingIn, setAnimatingIn] = useState(false);
  const [undoState, setUndoState] = useState<UndoState | null>(null);
  const [skippedIds, setSkippedIds] = useState<Set<string>>(new Set());
  const [allDone, setAllDone] = useState(false);
  const fetchingRef = useRef(false);

  const fetchContacts = useCallback(async () => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;
    setLoading(true);
    try {
      const res = await fetch('/api/rate');
      const data = await res.json();
      const newContacts: RateContact[] = data.contacts || [];
      setContacts(newContacts);
      setUnratedCount(data.unrated_count ?? 0);
      setRatedCount(data.rated_count ?? 0);
      setCurrentIndex(0);
      setSkippedIds(new Set());
      if (newContacts.length === 0) {
        setAllDone(true);
      }
    } catch (err) {
      console.error('Failed to fetch contacts:', err);
    } finally {
      setLoading(false);
      fetchingRef.current = false;
    }
  }, []);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  // Keyboard shortcuts: 0-4 to rate, u for undo, s for skip
  useEffect(() => {
    function handleKeydown(e: KeyboardEvent) {
      // Don't capture if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (animatingOut || loading || allDone) return;

      const key = e.key;
      if (key >= '0' && key <= '4') {
        e.preventDefault();
        handleRate(parseInt(key));
      } else if (key === 'u' || key === 'U') {
        e.preventDefault();
        handleUndo();
      } else if (key === 's' || key === 'S') {
        e.preventDefault();
        handleSkip();
      }
    }
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [animatingOut, loading, allDone, currentIndex, contacts, undoState]);

  const contact = contacts[currentIndex] ?? null;
  const total = unratedCount + ratedCount;
  const progressPct = total > 0 ? (ratedCount / total) * 100 : 0;

  const sharedSchools = contact
    ? findSharedItems(extractSchoolNames(contact.enrich_schools), JUSTIN_SCHOOLS)
    : [];
  const sharedCompanies = contact
    ? findSharedItems(extractCompanyNames(contact.enrich_companies_worked), JUSTIN_COMPANIES)
    : [];
  const hasSharedContext = sharedSchools.length > 0 || sharedCompanies.length > 0;

  function advanceToNext() {
    const nextIndex = currentIndex + 1;
    if (nextIndex >= contacts.length) {
      // Batch exhausted — fetch next batch
      fetchContacts();
    } else {
      // Animate next card in
      setAnimatingIn(true);
      setCurrentIndex(nextIndex);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setAnimatingIn(false);
        });
      });
    }
  }

  function handleRate(rating: number) {
    if (!contact || animatingOut) return;

    // Save undo state
    setUndoState({ contact, previousRating: null });

    // Optimistic UI: update counts immediately
    setRatedCount(prev => prev + 1);
    setUnratedCount(prev => Math.max(0, prev - 1));

    // Fire-and-forget POST
    fetch('/api/rate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contact_id: contact.id, rating }),
    }).catch(err => console.error('Failed to save rating:', err));

    // Animate out then advance
    setAnimatingOut(true);
    setTimeout(() => {
      setAnimatingOut(false);
      advanceToNext();
    }, 200);
  }

  function handleSkip() {
    if (!contact || animatingOut) return;

    // Add to skipped set
    setSkippedIds(prev => new Set(prev).add(contact.id));

    // Move this contact to end of the queue
    setContacts(prev => {
      const updated = [...prev];
      const [skipped] = updated.splice(currentIndex, 1);
      updated.push(skipped);
      return updated;
    });

    // Animate transition
    setAnimatingOut(true);
    setTimeout(() => {
      setAnimatingOut(false);
      // Since we spliced and re-appended, currentIndex now points to the next contact
      // But if we're at the end of original contacts (all skipped), fetch new batch
      if (skippedIds.size + 1 >= contacts.length) {
        // All contacts in batch have been skipped — fetch fresh
        fetchContacts();
      } else {
        setAnimatingIn(true);
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            setAnimatingIn(false);
          });
        });
      }
    }, 200);
  }

  function handleUndo() {
    if (!undoState || animatingOut) return;

    const { contact: prevContact, previousRating } = undoState;

    // Revert counts
    setRatedCount(prev => Math.max(0, prev - 1));
    setUnratedCount(prev => prev + 1);

    // Re-save with null (undo)
    fetch('/api/rate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contact_id: prevContact.id, rating: previousRating }),
    }).catch(err => console.error('Failed to undo rating:', err));

    // Insert the previous contact back at current position
    setContacts(prev => {
      const updated = [...prev];
      updated.splice(currentIndex, 0, prevContact);
      return updated;
    });

    // Clear undo state (can only undo once)
    setUndoState(null);

    // Animate in
    setAnimatingIn(true);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setAnimatingIn(false);
      });
    });
  }

  return (
    <div className="min-h-dvh bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b">
        <Link href="/" className="p-1 -ml-1 text-muted-foreground hover:text-foreground">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <span className="text-sm text-muted-foreground font-medium">
          {total > 0 ? `${ratedCount} / ${total} rated` : ''}
        </span>
        <button
          onClick={handleUndo}
          disabled={!undoState || animatingOut}
          className="p-1 -mr-1 text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
          title="Undo last rating (u)"
        >
          <Undo2 className="w-5 h-5" />
        </button>
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="h-1 bg-gray-200">
          <div
            className="h-full bg-primary transition-all duration-300 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      )}

      {/* Card area */}
      <div className="flex-1 flex items-center justify-center px-4 py-4">
        {loading ? (
          <ContactCardSkeleton />
        ) : allDone || !contact ? (
          <div className="text-center text-muted-foreground">
            <p className="text-2xl font-semibold mb-2">Done!</p>
            <p className="text-sm">
              All {total.toLocaleString()} contacts have been rated.
            </p>
            <Link
              href="/"
              className="inline-block mt-4 text-sm text-primary hover:underline"
            >
              Back to dashboard
            </Link>
          </div>
        ) : (
          <div
            className={`w-full max-w-[400px] transition-all duration-200 ease-out ${
              animatingOut
                ? 'opacity-0 -translate-y-8'
                : animatingIn
                  ? 'opacity-0 translate-y-4'
                  : 'opacity-100 translate-y-0'
            }`}
          >
            <Card>
              <CardContent className="p-5">
                <div className="flex flex-col items-center text-center gap-2.5">
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
                    <div className="w-full mt-1 pt-2.5 border-t">
                      <p className="text-[11px] uppercase tracking-wider text-muted-foreground/60 font-medium mb-1.5">
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
          </div>
        )}
      </div>

      {/* Rating buttons + Skip */}
      {!loading && !allDone && contact && (
        <div className="px-4 pb-4 pt-0 w-full max-w-[400px] mx-auto space-y-2">
          {RATING_LEVELS.map(({ level, label, color }) => (
            <button
              key={level}
              onClick={() => handleRate(level)}
              disabled={animatingOut}
              className={`w-full min-h-[48px] px-4 py-3 rounded-lg text-left font-medium text-sm transition-colors ${color} disabled:opacity-50`}
            >
              <span className="font-bold mr-2">{level}</span>
              {label}
            </button>
          ))}
          <button
            onClick={handleSkip}
            disabled={animatingOut}
            className="w-full min-h-[44px] px-4 py-2.5 rounded-lg text-sm text-muted-foreground hover:bg-gray-100 active:bg-gray-200 transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <SkipForward className="w-4 h-4" />
            Skip
          </button>
        </div>
      )}
    </div>
  );
}
