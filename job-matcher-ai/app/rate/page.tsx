'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ArrowLeft, Undo2, SkipForward, ChevronDown, ChevronUp, ExternalLink, SlidersHorizontal } from 'lucide-react';
import Link from 'next/link';

// Justin's schools and companies for shared context matching
const JUSTIN_SCHOOLS = ['Harvard Business School', 'HBS', 'Harvard Kennedy School', 'HKS', 'University of Virginia', 'UVA'];
const JUSTIN_COMPANIES = ['Kindora', 'Google.org', 'Year Up', 'Bridgespan', 'Bridgespan Group', 'Bain', 'Bain & Company', 'True Steele', 'Outdoorithm', 'Outdoorithm Collective'];

const RATING_LEVELS = [
  { level: 0, label: "Don't Know", color: 'bg-gray-100 text-gray-700 active:bg-gray-200', dotColor: 'bg-gray-400' },
  { level: 1, label: 'Recognize', color: 'bg-blue-50 text-blue-700 active:bg-blue-100', dotColor: 'bg-blue-500' },
  { level: 2, label: 'Acquaintance', color: 'bg-green-50 text-green-700 active:bg-green-100', dotColor: 'bg-green-500' },
  { level: 3, label: 'Solid', color: 'bg-orange-50 text-orange-700 active:bg-orange-100', dotColor: 'bg-orange-500' },
  { level: 4, label: 'Close', color: 'bg-purple-50 text-purple-700 active:bg-purple-100', dotColor: 'bg-purple-500' },
];

const SORT_OPTIONS = [
  { value: 'ai_close', label: 'AI: Close first' },
  { value: 'ai_distant', label: 'AI: Distant first' },
  { value: 'recent', label: 'Recently connected' },
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
  familiarity_rating: number | null;
}

interface UndoState {
  contact: RateContact;
  previousRating: number | null;
}

type Breakdown = Record<number, number>;

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
  const [breakdown, setBreakdown] = useState<Breakdown>({ 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 });
  const [animatingOut, setAnimatingOut] = useState(false);
  const [animatingIn, setAnimatingIn] = useState(false);
  const [undoState, setUndoState] = useState<UndoState | null>(null);
  const [skippedIds, setSkippedIds] = useState<Set<string>>(new Set());
  const [allDone, setAllDone] = useState(false);
  const [sessionCount, setSessionCount] = useState(0);
  const [statsExpanded, setStatsExpanded] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [sortBy, setSortBy] = useState('ai_close');
  const [mode, setMode] = useState<'unrated' | 'rerate'>('unrated');
  const fetchingRef = useRef(false);

  const fetchContacts = useCallback(async (sort?: string, fetchMode?: string) => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('sort', sort ?? sortBy);
      params.set('mode', fetchMode ?? mode);
      const res = await fetch(`/api/rate?${params.toString()}`);
      const data = await res.json();
      const newContacts: RateContact[] = data.contacts || [];
      setContacts(newContacts);
      setUnratedCount(data.unrated_count ?? 0);
      setRatedCount(data.rated_count ?? 0);
      if (data.breakdown) {
        setBreakdown(data.breakdown);
      }
      setCurrentIndex(0);
      setSkippedIds(new Set());
      if (newContacts.length === 0) {
        setAllDone(true);
      } else {
        setAllDone(false);
      }
    } catch (err) {
      console.error('Failed to fetch contacts:', err);
    } finally {
      setLoading(false);
      fetchingRef.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortBy, mode]);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  // Keyboard shortcuts: 0-4 to rate, u for undo, s for skip
  useEffect(() => {
    function handleKeydown(e: KeyboardEvent) {
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
      fetchContacts();
    } else {
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

    // Save undo state (preserve existing rating for re-rate mode)
    setUndoState({ contact, previousRating: contact.familiarity_rating ?? null });

    // Session counter
    setSessionCount(prev => prev + 1);

    // Optimistic UI: update counts
    if (mode === 'unrated') {
      setRatedCount(prev => prev + 1);
      setUnratedCount(prev => Math.max(0, prev - 1));
    }

    // Optimistic breakdown update
    setBreakdown(prev => {
      const updated = { ...prev };
      // If re-rating, decrement old level
      if (contact.familiarity_rating !== null && updated[contact.familiarity_rating] !== undefined) {
        updated[contact.familiarity_rating] = Math.max(0, updated[contact.familiarity_rating] - 1);
      }
      updated[rating] = (updated[rating] || 0) + 1;
      return updated;
    });

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

    setSkippedIds(prev => new Set(prev).add(contact.id));

    setContacts(prev => {
      const updated = [...prev];
      const [skipped] = updated.splice(currentIndex, 1);
      updated.push(skipped);
      return updated;
    });

    setAnimatingOut(true);
    setTimeout(() => {
      setAnimatingOut(false);
      if (skippedIds.size + 1 >= contacts.length) {
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

    // Revert session counter
    setSessionCount(prev => Math.max(0, prev - 1));

    // Revert counts
    if (mode === 'unrated') {
      setRatedCount(prev => Math.max(0, prev - 1));
      setUnratedCount(prev => prev + 1);
    }

    // Revert breakdown (undo the last rating, restore previous)
    setBreakdown(prev => {
      const updated = { ...prev };
      // We don't know the rating that was just applied, but we can restore from previous
      // The simplest approach: decrement current counts will happen on next fetch
      // For now, just restore the previous rating level
      if (previousRating !== null && updated[previousRating] !== undefined) {
        updated[previousRating] = (updated[previousRating] || 0) + 1;
      }
      return updated;
    });

    // Re-save with previous value
    fetch('/api/rate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contact_id: prevContact.id, rating: previousRating }),
    }).catch(err => console.error('Failed to undo rating:', err));

    setContacts(prev => {
      const updated = [...prev];
      updated.splice(currentIndex, 0, prevContact);
      return updated;
    });

    setUndoState(null);

    setAnimatingIn(true);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setAnimatingIn(false);
      });
    });
  }

  function handleSortChange(value: string) {
    setSortBy(value);
    setFilterOpen(false);
    fetchContacts(value, mode);
  }

  function handleModeChange(newMode: 'unrated' | 'rerate') {
    setMode(newMode);
    setFilterOpen(false);
    fetchContacts(sortBy, newMode);
  }

  return (
    <div className="min-h-dvh bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b">
        <Link href="/" className="p-1 -ml-1 text-muted-foreground hover:text-foreground">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <button
          onClick={() => setStatsExpanded(!statsExpanded)}
          className="flex items-center gap-1 text-sm text-muted-foreground font-medium hover:text-foreground transition-colors"
        >
          {total > 0 ? `${ratedCount} / ${total} rated` : '...'}
          {total > 0 && (
            statsExpanded
              ? <ChevronUp className="w-3.5 h-3.5" />
              : <ChevronDown className="w-3.5 h-3.5" />
          )}
        </button>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setFilterOpen(!filterOpen)}
            className={`p-1 text-muted-foreground hover:text-foreground transition-colors ${filterOpen ? 'text-foreground' : ''}`}
            title="Filter & sort"
          >
            <SlidersHorizontal className="w-5 h-5" />
          </button>
          <button
            onClick={handleUndo}
            disabled={!undoState || animatingOut}
            className="p-1 -mr-1 text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
            title="Undo last rating (u)"
          >
            <Undo2 className="w-5 h-5" />
          </button>
        </div>
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

      {/* Collapsible stats panel */}
      {statsExpanded && (
        <div className="bg-white border-b px-4 py-3 space-y-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{progressPct.toFixed(1)}% complete</span>
            <span>Session: {sessionCount} rated</span>
          </div>
          <div className="flex gap-1.5">
            {RATING_LEVELS.map(({ level, label, dotColor }) => (
              <div key={level} className="flex-1 text-center">
                <div className="flex items-center justify-center gap-1 mb-0.5">
                  <div className={`w-2 h-2 rounded-full ${dotColor}`} />
                  <span className="text-xs font-medium">{breakdown[level] ?? 0}</span>
                </div>
                <span className="text-[10px] text-muted-foreground leading-none">{label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter panel */}
      {filterOpen && (
        <div className="bg-white border-b px-4 py-3 space-y-3">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Sort order</label>
            <Select value={sortBy} onValueChange={handleSortChange}>
              <SelectTrigger className="h-8 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Mode</label>
            <div className="flex gap-2">
              <button
                onClick={() => handleModeChange('unrated')}
                className={`flex-1 py-1.5 px-3 rounded-md text-sm font-medium transition-colors ${
                  mode === 'unrated'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-gray-100 text-muted-foreground hover:bg-gray-200'
                }`}
              >
                Unrated
              </button>
              <button
                onClick={() => handleModeChange('rerate')}
                className={`flex-1 py-1.5 px-3 rounded-md text-sm font-medium transition-colors ${
                  mode === 'rerate'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-gray-100 text-muted-foreground hover:bg-gray-200'
                }`}
              >
                Re-rate
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Card area */}
      <div className="flex-1 flex items-center justify-center px-4 py-4">
        {loading ? (
          <ContactCardSkeleton />
        ) : allDone || !contact ? (
          <div className="text-center text-muted-foreground">
            <p className="text-2xl font-semibold mb-2">
              {mode === 'rerate' ? 'No rated contacts' : 'Done!'}
            </p>
            <p className="text-sm">
              {mode === 'rerate'
                ? 'Rate some contacts first, then come back to re-rate.'
                : `All ${total.toLocaleString()} contacts have been rated.`}
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

                  {/* Name with LinkedIn link */}
                  <div className="flex items-center gap-1.5">
                    <h2 className="text-xl font-semibold leading-tight">
                      {contact.first_name} {contact.last_name}
                    </h2>
                    {contact.linkedin_url && (
                      <a
                        href={contact.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground/50 hover:text-blue-600 transition-colors flex-shrink-0"
                        title="View LinkedIn profile"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>

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

                  {/* AI proximity tier badge + current rating in re-rate mode */}
                  <div className="flex items-center gap-1.5">
                    {contact.ai_proximity_tier ? (
                      <Badge className={`${tierColor(contact.ai_proximity_tier)} border-0 text-xs`}>
                        AI: {contact.ai_proximity_tier}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-xs text-muted-foreground">
                        Not scored
                      </Badge>
                    )}
                    {mode === 'rerate' && contact.familiarity_rating !== null && (
                      <Badge variant="outline" className="text-xs">
                        Current: {contact.familiarity_rating} — {RATING_LEVELS[contact.familiarity_rating]?.label}
                      </Badge>
                    )}
                  </div>

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
