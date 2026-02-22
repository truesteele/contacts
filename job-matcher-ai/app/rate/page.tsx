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
import { ArrowLeft, Undo2, SkipForward, ChevronDown, ChevronUp, ExternalLink, SlidersHorizontal, AlertCircle, Search, ChevronLeft, X } from 'lucide-react';
import Link from 'next/link';

// Justin's schools and companies for shared context matching
const JUSTIN_SCHOOLS = ['Harvard Business School', 'HBS', 'Harvard Kennedy School', 'HKS', 'University of Virginia', 'UVA'];
const JUSTIN_COMPANIES = ['Kindora', 'Google.org', 'Year Up', 'Bridgespan', 'Bridgespan Group', 'Bain', 'Bain & Company', 'True Steele', 'Outdoorithm', 'Outdoorithm Collective'];

const RATING_LEVELS = [
  { level: 0, label: "Don't Know", color: 'bg-gray-100 text-gray-700', activeColor: 'bg-gray-400 text-white', dotColor: 'bg-gray-400' },
  { level: 1, label: 'Recognize', color: 'bg-blue-50 text-blue-700', activeColor: 'bg-blue-500 text-white', dotColor: 'bg-blue-500' },
  { level: 2, label: 'Acquaintance', color: 'bg-green-50 text-green-700', activeColor: 'bg-green-500 text-white', dotColor: 'bg-green-500' },
  { level: 3, label: 'Solid', color: 'bg-orange-50 text-orange-700', activeColor: 'bg-orange-500 text-white', dotColor: 'bg-orange-500' },
  { level: 4, label: 'Close', color: 'bg-purple-50 text-purple-700', activeColor: 'bg-purple-500 text-white', dotColor: 'bg-purple-500' },
];

const SORT_OPTIONS = [
  { value: 'ai_close', label: 'AI: Close first' },
  { value: 'ai_distant', label: 'AI: Distant first' },
  { value: 'recent', label: 'Recently connected' },
];

interface RateContact {
  id: number;
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
  appliedRating: number;
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

function ErrorToast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 4000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div className="fixed bottom-20 left-4 right-4 z-50 flex justify-center pointer-events-none">
      <div
        className="pointer-events-auto flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 text-red-700 rounded-lg shadow-lg text-sm max-w-[400px] w-full animate-in fade-in slide-in-from-bottom-2 duration-200"
        role="alert"
      >
        <AlertCircle className="w-4 h-4 flex-shrink-0" />
        <span className="flex-1">{message}</span>
        <button
          onClick={onDismiss}
          className="text-red-400 hover:text-red-600 flex-shrink-0 min-w-[44px] min-h-[44px] flex items-center justify-center -mr-2"
          aria-label="Dismiss"
        >
          &times;
        </button>
      </div>
    </div>
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
  const [skippedIds, setSkippedIds] = useState<Set<number>>(new Set());
  const [allDone, setAllDone] = useState(false);
  const [sessionCount, setSessionCount] = useState(0);
  const [statsExpanded, setStatsExpanded] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [sortBy, setSortBy] = useState('ai_close');
  const [mode, setMode] = useState<'unrated' | 'rerate'>('unrated');
  const [errorToast, setErrorToast] = useState<string | null>(null);
  const [imgError, setImgError] = useState<number | null>(null);
  const [selectedRating, setSelectedRating] = useState<number | null>(null);
  // History of rated contacts for back navigation
  const [history, setHistory] = useState<RateContact[]>([]);
  const [viewingHistory, setViewingHistory] = useState(false);
  const [historyIndex, setHistoryIndex] = useState(-1);
  // Search
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<RateContact[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const fetchingRef = useRef(false);
  // Queue for failed requests to retry
  const retryQueueRef = useRef<Array<{ contact_id: number; rating: number | null }>>([]);

  const showError = useCallback((msg: string) => {
    setErrorToast(msg);
  }, []);

  const saveRating = useCallback(async (contact_id: number, rating: number | null) => {
    try {
      const res = await fetch('/api/rate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contact_id, rating }),
      });
      if (!res.ok) {
        throw new Error(`Server error ${res.status}`);
      }
    } catch {
      // Queue for retry
      retryQueueRef.current.push({ contact_id, rating });
      showError('Rating failed to save. Will retry automatically.');
    }
  }, [showError]);

  // Retry queued saves periodically
  useEffect(() => {
    const interval = setInterval(async () => {
      if (retryQueueRef.current.length === 0) return;
      const batch = [...retryQueueRef.current];
      retryQueueRef.current = [];
      for (const item of batch) {
        try {
          const res = await fetch('/api/rate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item),
          });
          if (!res.ok) {
            retryQueueRef.current.push(item);
          }
        } catch {
          retryQueueRef.current.push(item);
        }
      }
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  // Search contacts by name
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    if (query.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    searchTimerRef.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const res = await fetch(`/api/rate?search=${encodeURIComponent(query.trim())}`);
        if (!res.ok) throw new Error('Search failed');
        const data = await res.json();
        setSearchResults(data.contacts || []);
      } catch {
        showError('Search failed');
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  }, [showError]);

  // Select a search result to rate/re-rate
  function handleSearchSelect(selected: RateContact) {
    setSearchOpen(false);
    setSearchQuery('');
    setSearchResults([]);
    // Exit history mode if in it
    setViewingHistory(false);
    setHistoryIndex(-1);
    // Insert at current position so it becomes the active card
    setContacts(prev => {
      const updated = [...prev];
      updated.splice(currentIndex, 0, selected);
      return updated;
    });
    setAnimatingIn(true);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => setAnimatingIn(false));
    });
  }

  const fetchContacts = useCallback(async (sort?: string, fetchMode?: string) => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('sort', sort ?? sortBy);
      params.set('mode', fetchMode ?? mode);
      const res = await fetch(`/api/rate?${params.toString()}`);
      if (!res.ok) throw new Error(`Failed to fetch (${res.status})`);
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
      setImgError(null);
      if (newContacts.length === 0) {
        setAllDone(true);
      } else {
        setAllDone(false);
      }
    } catch (err) {
      console.error('Failed to fetch contacts:', err);
      showError('Failed to load contacts. Check your connection.');
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
      // Escape closes search from anywhere
      if (e.key === 'Escape' && searchOpen) {
        e.preventDefault();
        setSearchOpen(false);
        setSearchQuery('');
        setSearchResults([]);
        return;
      }

      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (searchOpen) return;
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
      } else if (key === 'b' || key === 'B') {
        e.preventDefault();
        handleBack();
      } else if (key === '/') {
        e.preventDefault();
        setSearchOpen(true);
        setTimeout(() => searchInputRef.current?.focus(), 100);
      }
    }
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [animatingOut, loading, allDone, currentIndex, contacts, undoState, searchOpen, history, viewingHistory, historyIndex]);

  const contact = viewingHistory && historyIndex >= 0 && historyIndex < history.length
    ? history[historyIndex]
    : contacts[currentIndex] ?? null;
  const total = unratedCount + ratedCount;
  const progressPct = total > 0 ? (ratedCount / total) * 100 : 0;

  const sharedSchools = contact
    ? findSharedItems(extractSchoolNames(contact.enrich_schools), JUSTIN_SCHOOLS)
    : [];
  const sharedCompanies = contact
    ? findSharedItems(extractCompanyNames(contact.enrich_companies_worked), JUSTIN_COMPANIES)
    : [];
  const hasSharedContext = sharedSchools.length > 0 || sharedCompanies.length > 0;

  // Reset image error state when contact changes
  useEffect(() => {
    setImgError(null);
  }, [contact?.id]);

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

    // Flash the selected button
    setSelectedRating(rating);

    if (viewingHistory) {
      // Re-rating a history contact
      saveRating(contact.id, rating);
      setSessionCount(prev => prev + 1);

      // Optimistic breakdown update
      setBreakdown(prev => {
        const updated = { ...prev };
        if (contact.familiarity_rating !== null && updated[contact.familiarity_rating] !== undefined) {
          updated[contact.familiarity_rating] = Math.max(0, updated[contact.familiarity_rating] - 1);
        }
        updated[rating] = (updated[rating] || 0) + 1;
        return updated;
      });

      // Update the history entry's rating
      setHistory(prev => {
        const updated = [...prev];
        updated[historyIndex] = { ...updated[historyIndex], familiarity_rating: rating };
        return updated;
      });

      // Brief flash then exit history mode back to queue
      setTimeout(() => {
        setAnimatingOut(true);
        setTimeout(() => {
          setAnimatingOut(false);
          setSelectedRating(null);
          setViewingHistory(false);
          setHistoryIndex(-1);
          setAnimatingIn(true);
          requestAnimationFrame(() => {
            requestAnimationFrame(() => setAnimatingIn(false));
          });
        }, 200);
      }, 150);
      return;
    }

    // Push to history for back navigation
    setHistory(prev => [...prev, contact]);

    // Save undo state (preserve existing rating for re-rate mode)
    setUndoState({ contact, previousRating: contact.familiarity_rating ?? null, appliedRating: rating });

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

    // Save with retry support
    saveRating(contact.id, rating);

    // Brief delay to show the selected state, then animate out
    setTimeout(() => {
      setAnimatingOut(true);
      setTimeout(() => {
        setAnimatingOut(false);
        setSelectedRating(null);
        advanceToNext();
      }, 200);
    }, 150);
  }

  function handleBack() {
    if (animatingOut || history.length === 0) return;

    const targetIndex = viewingHistory ? historyIndex - 1 : history.length - 1;
    if (targetIndex < 0) return;

    setAnimatingOut(true);
    setTimeout(() => {
      setAnimatingOut(false);
      setViewingHistory(true);
      setHistoryIndex(targetIndex);
      setAnimatingIn(true);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => setAnimatingIn(false));
      });
    }, 200);
  }

  function exitHistoryMode() {
    if (animatingOut) return;
    setAnimatingOut(true);
    setTimeout(() => {
      setAnimatingOut(false);
      setViewingHistory(false);
      setHistoryIndex(-1);
      setAnimatingIn(true);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => setAnimatingIn(false));
      });
    }, 200);
  }

  function handleSkip() {
    if (!contact || animatingOut) return;

    if (viewingHistory) {
      exitHistoryMode();
      return;
    }

    const newSkippedCount = skippedIds.size + 1;
    const totalInBatch = contacts.length;
    const willExhaustBatch = newSkippedCount >= totalInBatch;

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
      if (willExhaustBatch) {
        fetchContacts();
      } else {
        setAnimatingIn(true);
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            setAnimatingIn(false);
          });
        });
      }
    }, 250);
  }

  function handleUndo() {
    if (!undoState || animatingOut) return;

    const { contact: prevContact, previousRating, appliedRating } = undoState;

    // Revert session counter
    setSessionCount(prev => Math.max(0, prev - 1));

    // Revert counts
    if (mode === 'unrated') {
      setRatedCount(prev => Math.max(0, prev - 1));
      setUnratedCount(prev => prev + 1);
    }

    // Revert breakdown accurately using the applied rating
    setBreakdown(prev => {
      const updated = { ...prev };
      // Decrement the rating that was just applied
      updated[appliedRating] = Math.max(0, (updated[appliedRating] || 0) - 1);
      // Restore the previous rating level
      if (previousRating !== null) {
        updated[previousRating] = (updated[previousRating] || 0) + 1;
      }
      return updated;
    });

    // Re-save with previous value
    saveRating(prevContact.id, previousRating);

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

  const showInitials = !contact?.enrich_profile_pic_url || imgError === contact?.id;

  return (
    <div className="min-h-dvh bg-background flex flex-col">
      {/* Header — all touch targets ≥44px */}
      <div className="flex items-center justify-between px-2 py-1 bg-card border-b">
        <div className="flex items-center">
          <Link
            href="/"
            className="min-w-[44px] min-h-[44px] flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Back to dashboard"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <button
            onClick={handleBack}
            disabled={history.length === 0 || animatingOut || (viewingHistory && historyIndex <= 0)}
            className="min-w-[44px] min-h-[44px] flex items-center justify-center text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Back to previous contact (b)"
            aria-label="Back to previous contact"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>
        <button
          onClick={() => setStatsExpanded(!statsExpanded)}
          className="flex items-center gap-1 text-sm text-muted-foreground font-medium hover:text-foreground transition-colors min-h-[44px] px-2"
        >
          {viewingHistory
            ? `Viewing #${historyIndex + 1} of ${history.length}`
            : total > 0 ? `${ratedCount} / ${total} rated` : '...'}
          {!viewingHistory && total > 0 && (
            statsExpanded
              ? <ChevronUp className="w-3.5 h-3.5" />
              : <ChevronDown className="w-3.5 h-3.5" />
          )}
        </button>
        <div className="flex items-center">
          <button
            onClick={() => { setSearchOpen(true); setTimeout(() => searchInputRef.current?.focus(), 100); }}
            className="min-w-[44px] min-h-[44px] flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            title="Search contacts (/)"
            aria-label="Search contacts"
          >
            <Search className="w-5 h-5" />
          </button>
          <button
            onClick={() => setFilterOpen(!filterOpen)}
            className={`min-w-[44px] min-h-[44px] flex items-center justify-center transition-colors ${filterOpen ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            title="Filter & sort"
            aria-label="Filter and sort options"
          >
            <SlidersHorizontal className="w-5 h-5" />
          </button>
          <button
            onClick={handleUndo}
            disabled={!undoState || animatingOut}
            className="min-w-[44px] min-h-[44px] flex items-center justify-center text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Undo last rating (u)"
            aria-label="Undo last rating"
          >
            <Undo2 className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="h-1 bg-muted">
          <div
            className="h-full bg-primary transition-all duration-300 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      )}

      {/* Collapsible stats panel */}
      {statsExpanded && (
        <div className="bg-card border-b px-4 py-3 space-y-2">
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
        <div className="bg-card border-b px-4 py-3 space-y-3">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Sort order</label>
            <Select value={sortBy} onValueChange={handleSortChange}>
              <SelectTrigger className="h-10 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value} className="min-h-[44px] flex items-center">
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
                className={`flex-1 min-h-[44px] py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                  mode === 'unrated'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary text-muted-foreground hover:bg-muted'
                }`}
              >
                Unrated
              </button>
              <button
                onClick={() => handleModeChange('rerate')}
                className={`flex-1 min-h-[44px] py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                  mode === 'rerate'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary text-muted-foreground hover:bg-muted'
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
              className="inline-block mt-4 text-sm text-primary hover:underline min-h-[44px] leading-[44px]"
            >
              Back to dashboard
            </Link>
          </div>
        ) : (
          <div
            className={`w-full max-w-[400px] transition-all duration-250 ${
              animatingOut
                ? 'opacity-0 -translate-y-6 scale-[0.98] ease-in'
                : animatingIn
                  ? 'opacity-0 translate-y-4 scale-[0.98]'
                  : 'opacity-100 translate-y-0 scale-100 ease-out'
            }`}
          >
            <Card>
              <CardContent className="p-5">
                <div className="flex flex-col items-center text-center gap-2.5">
                  {/* Profile photo or initials fallback */}
                  {!showInitials ? (
                    <img
                      src={contact.enrich_profile_pic_url!}
                      alt={`${contact.first_name} ${contact.last_name}`}
                      className="w-20 h-20 rounded-full object-cover bg-muted"
                      onError={() => setImgError(contact.id)}
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
                        className="text-muted-foreground/50 hover:text-blue-600 transition-colors flex-shrink-0 min-w-[44px] min-h-[44px] flex items-center justify-center -my-2"
                        title="View LinkedIn profile"
                        aria-label="View LinkedIn profile"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>

                  {/* Title @ company, or dash if both missing */}
                  {(contact.enrich_current_title || contact.enrich_current_company) ? (
                    <p className="text-sm text-muted-foreground">
                      {contact.enrich_current_title || ''}
                      {contact.enrich_current_title && contact.enrich_current_company && ' @ '}
                      {contact.enrich_current_company || ''}
                    </p>
                  ) : (
                    !contact.headline && (
                      <p className="text-sm text-muted-foreground/40">&mdash;</p>
                    )
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
                  <div className="flex flex-wrap items-center justify-center gap-1.5">
                    {contact.ai_proximity_tier ? (
                      <Badge className={`${tierColor(contact.ai_proximity_tier)} border-0 text-xs`}>
                        AI: {contact.ai_proximity_tier}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-xs text-muted-foreground">
                        Not scored
                      </Badge>
                    )}
                    {(mode === 'rerate' || viewingHistory) && contact.familiarity_rating !== null && (
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

      {/* Rating buttons + Skip — safe area padding for iPhone home indicator */}
      {!loading && !allDone && contact && (
        <div className="px-4 pb-4 pt-0 w-full max-w-[400px] mx-auto space-y-2" style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
          {RATING_LEVELS.map(({ level, label, color, activeColor }) => {
            const isSelected = selectedRating === level;
            return (
              <button
                key={level}
                onClick={() => handleRate(level)}
                disabled={animatingOut || selectedRating !== null}
                className={`w-full min-h-[48px] px-4 py-3 rounded-lg text-left font-medium text-sm select-none transition-all duration-150 ${
                  isSelected
                    ? `${activeColor} scale-[1.03] shadow-md ring-2 ring-offset-1 ring-current`
                    : selectedRating !== null
                      ? `${color} opacity-40`
                      : `${color} active:scale-[0.97]`
                } disabled:cursor-default`}
              >
                <span className="font-bold mr-2">{level}</span>
                {label}
              </button>
            );
          })}
          <button
            onClick={handleSkip}
            disabled={animatingOut}
            className="w-full min-h-[44px] px-4 py-2.5 rounded-lg text-sm text-muted-foreground hover:bg-secondary active:bg-muted transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50 select-none"
          >
            {viewingHistory ? (
              <>
                <ArrowLeft className="w-4 h-4" />
                Resume queue
              </>
            ) : (
              <>
                <SkipForward className="w-4 h-4" />
                Skip
              </>
            )}
          </button>
        </div>
      )}

      {/* Search overlay */}
      {searchOpen && (
        <div className="fixed inset-0 z-50 bg-card flex flex-col">
          <div className="flex items-center gap-2 px-3 py-2 border-b">
            <Search className="w-5 h-5 text-muted-foreground flex-shrink-0" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search by name..."
              className="flex-1 text-base outline-none bg-transparent min-h-[44px]"
              autoComplete="off"
            />
            <button
              onClick={() => { setSearchOpen(false); setSearchQuery(''); setSearchResults([]); }}
              className="min-w-[44px] min-h-[44px] flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Close search"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {searchLoading && (
              <div className="px-4 py-8 text-center text-muted-foreground text-sm">Searching...</div>
            )}
            {!searchLoading && searchQuery.length >= 2 && searchResults.length === 0 && (
              <div className="px-4 py-8 text-center text-muted-foreground text-sm">No contacts found</div>
            )}
            {!searchLoading && searchQuery.length < 2 && searchQuery.length > 0 && (
              <div className="px-4 py-8 text-center text-muted-foreground text-sm">Type at least 2 characters</div>
            )}
            {searchResults.map(result => (
              <button
                key={result.id}
                onClick={() => handleSearchSelect(result)}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-secondary active:bg-muted transition-colors border-b text-left"
              >
                {result.enrich_profile_pic_url ? (
                  <img
                    src={result.enrich_profile_pic_url}
                    alt=""
                    className="w-10 h-10 rounded-full object-cover bg-muted flex-shrink-0"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-semibold flex-shrink-0">
                    {getInitials(result.first_name, result.last_name)}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">
                    {result.first_name} {result.last_name}
                  </div>
                  {(result.enrich_current_title || result.enrich_current_company) && (
                    <div className="text-xs text-muted-foreground truncate">
                      {result.enrich_current_title || ''}
                      {result.enrich_current_title && result.enrich_current_company ? ' @ ' : ''}
                      {result.enrich_current_company || ''}
                    </div>
                  )}
                </div>
                {result.familiarity_rating !== null && result.familiarity_rating !== undefined && (
                  <Badge className={`${RATING_LEVELS[result.familiarity_rating]?.activeColor || 'bg-gray-400 text-white'} text-xs flex-shrink-0`}>
                    {result.familiarity_rating}
                  </Badge>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error toast */}
      {errorToast && (
        <ErrorToast message={errorToast} onDismiss={() => setErrorToast(null)} />
      )}
    </div>
  );
}
