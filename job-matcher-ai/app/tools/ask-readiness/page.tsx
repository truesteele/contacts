'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ContactDetailSheet } from '@/components/contact-detail-sheet';
import { cn } from '@/lib/utils';
import {
  ArrowLeft,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Building2,
  Download,
  Heart,
  MapPin,
  Search,
  ChevronDown,
  ChevronRight,
  X,
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────

interface AskReadinessContact {
  id: number;
  first_name: string;
  last_name: string;
  company?: string;
  position?: string;
  city?: string;
  state?: string;
  headline?: string;
  familiarity_rating?: number;
  comms_last_date?: string;
  comms_thread_count?: number;
  ai_capacity_tier?: string;
  ai_capacity_score?: number;
  ai_outdoorithm_fit?: string;
  oc_engagement?: Record<string, any>;
  score: number;
  tier: string;
  reasoning: string;
  recommended_approach: string;
  ask_timing: string;
  cultivation_needed: string;
  suggested_ask_range: string;
  personalization_angle: string;
  risk_factors: string[];
  scored_at: string;
}

interface TierCounts {
  ready_now: number;
  cultivate_first: number;
  long_term: number;
  not_a_fit: number;
}

type SortField =
  | 'score'
  | 'name'
  | 'company'
  | 'familiarity'
  | 'last_contact'
  | 'capacity'
  | 'ask_range'
  | 'tier';

// ── Constants ──────────────────────────────────────────────────────────

const TIER_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  ready_now: {
    label: 'Ready Now',
    color: 'text-green-700 dark:text-green-300',
    bg: 'bg-green-100 border-green-200 dark:bg-green-900/40 dark:border-green-800',
  },
  cultivate_first: {
    label: 'Cultivate First',
    color: 'text-yellow-700 dark:text-yellow-300',
    bg: 'bg-yellow-100 border-yellow-200 dark:bg-yellow-900/40 dark:border-yellow-800',
  },
  long_term: {
    label: 'Long Term',
    color: 'text-gray-600 dark:text-gray-400',
    bg: 'bg-gray-100 border-gray-200 dark:bg-gray-800/40 dark:border-gray-700',
  },
  not_a_fit: {
    label: 'Not a Fit',
    color: 'text-red-700 dark:text-red-300',
    bg: 'bg-red-100 border-red-200 dark:bg-red-900/40 dark:border-red-800',
  },
};

const APPROACH_LABELS: Record<string, string> = {
  personal_email: 'Personal Email',
  phone_call: 'Phone Call',
  in_person: 'In Person',
  linkedin: 'LinkedIn',
  intro_via_mutual: 'Intro via Mutual',
};

const TIMING_LABELS: Record<string, string> = {
  now: 'Now',
  after_cultivation: 'After Cultivation',
  after_reconnection: 'After Reconnection',
  not_recommended: 'Not Recommended',
};

const CAPACITY_COLORS: Record<string, string> = {
  major_donor: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/40 dark:text-green-300',
  mid_level: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300',
  grassroots: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300',
  unknown: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800/40 dark:text-gray-400',
};

const CAPACITY_LABELS: Record<string, string> = {
  major_donor: 'Major Donor',
  mid_level: 'Mid-Level',
  grassroots: 'Grassroots',
  unknown: 'Unknown',
};

// ── Helpers ────────────────────────────────────────────────────────────

function FamiliarityDots({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className={cn(
            'w-2 h-2 rounded-full',
            i < rating ? 'bg-blue-500 dark:bg-blue-400' : 'bg-gray-200 dark:bg-gray-700'
          )}
        />
      ))}
      <span className="ml-1 text-xs text-muted-foreground tabular-nums">{rating}</span>
    </div>
  );
}

function getRecencyColor(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  const now = new Date();
  const monthsAgo = (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24 * 30);
  if (monthsAgo < 3) return 'text-green-600 dark:text-green-400';
  if (monthsAgo < 12) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-gray-500 dark:text-gray-400';
}

function formatShortDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  const now = new Date();
  const sameYear = d.getFullYear() === now.getFullYear();
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    ...(sameYear ? {} : { year: '2-digit' }),
  });
}

function ScoreBar({ score }: { score: number }) {
  const getColor = (s: number) => {
    if (s >= 80) return 'bg-green-500';
    if (s >= 60) return 'bg-yellow-500';
    if (s >= 40) return 'bg-orange-400';
    return 'bg-gray-400';
  };

  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', getColor(score))}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-xs font-mono tabular-nums font-medium w-6 text-right">{score}</span>
    </div>
  );
}

// ── Component ──────────────────────────────────────────────────────────

export default function AskReadinessPage() {
  const [contacts, setContacts] = useState<AskReadinessContact[]>([]);
  const [tierCounts, setTierCounts] = useState<TierCounts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTiers, setActiveTiers] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<SortField>('score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [selectedContactId, setSelectedContactId] = useState<number | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch('/api/network-intel/ask-readiness?goal=outdoorithm_fundraising');
        if (!res.ok) throw new Error('Failed to load');
        const data = await res.json();
        setContacts(data.contacts || []);
        setTierCounts(data.tier_counts || null);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const toggleTier = useCallback((tier: string) => {
    setActiveTiers((prev) => {
      const next = new Set(prev);
      if (next.has(tier)) {
        next.delete(tier);
      } else {
        next.add(tier);
      }
      return next;
    });
  }, []);

  const handleSort = useCallback((field: SortField) => {
    setSortBy((prev) => {
      if (prev === field) {
        setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
        return prev;
      }
      setSortOrder(field === 'name' || field === 'company' ? 'asc' : 'desc');
      return field;
    });
  }, []);

  const filteredAndSorted = useMemo(() => {
    let result = contacts;

    // Filter by tier
    if (activeTiers.size > 0) {
      result = result.filter((c) => activeTiers.has(c.tier));
    }

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        (c) =>
          `${c.first_name} ${c.last_name}`.toLowerCase().includes(term) ||
          (c.company || '').toLowerCase().includes(term) ||
          (c.position || '').toLowerCase().includes(term) ||
          (c.reasoning || '').toLowerCase().includes(term) ||
          (c.personalization_angle || '').toLowerCase().includes(term)
      );
    }

    // Sort
    const sorted = [...result].sort((a, b) => {
      let cmp = 0;
      switch (sortBy) {
        case 'score':
          cmp = a.score - b.score;
          break;
        case 'name':
          cmp = `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`);
          break;
        case 'company':
          cmp = (a.company || '').localeCompare(b.company || '');
          break;
        case 'familiarity':
          cmp = (a.familiarity_rating ?? -1) - (b.familiarity_rating ?? -1);
          break;
        case 'last_contact':
          cmp = (a.comms_last_date || '').localeCompare(b.comms_last_date || '');
          break;
        case 'capacity':
          cmp = (a.ai_capacity_score ?? -1) - (b.ai_capacity_score ?? -1);
          break;
        case 'tier': {
          const order = { ready_now: 4, cultivate_first: 3, long_term: 2, not_a_fit: 1 };
          cmp = (order[a.tier as keyof typeof order] || 0) - (order[b.tier as keyof typeof order] || 0);
          break;
        }
        default:
          cmp = a.score - b.score;
      }
      return sortOrder === 'asc' ? cmp : -cmp;
    });

    return sorted;
  }, [contacts, activeTiers, searchTerm, sortBy, sortOrder]);

  const handleExportCSV = useCallback(() => {
    if (filteredAndSorted.length === 0) return;

    const headers = [
      'Name', 'Company', 'Position', 'City', 'State', 'Score', 'Tier',
      'Reasoning', 'Approach', 'Timing', 'Cultivation Needed',
      'Suggested Ask Range', 'Personalization Angle', 'Risk Factors',
      'Familiarity', 'Last Contact', 'Email Threads', 'Capacity Tier',
    ];

    const rows = filteredAndSorted.map((c) => [
      `${c.first_name} ${c.last_name}`,
      c.company || '', c.position || '', c.city || '', c.state || '',
      c.score, c.tier, c.reasoning,
      APPROACH_LABELS[c.recommended_approach] || c.recommended_approach,
      TIMING_LABELS[c.ask_timing] || c.ask_timing,
      c.cultivation_needed, c.suggested_ask_range, c.personalization_angle,
      (c.risk_factors || []).join('; '),
      c.familiarity_rating ?? '', c.comms_last_date || '',
      c.comms_thread_count ?? '', c.ai_capacity_tier || '',
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) =>
        row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')
      ),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `ask_readiness_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [filteredAndSorted]);

  function getSortIcon(field: SortField) {
    if (sortBy !== field) return <ArrowUpDown className="w-3 h-3 ml-1 opacity-40" />;
    return sortOrder === 'asc' ? (
      <ArrowUp className="w-3 h-3 ml-1" />
    ) : (
      <ArrowDown className="w-3 h-3 ml-1" />
    );
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-background">
        <div className="max-w-7xl mx-auto p-4">
          <div className="page-header">
            <Link href="/" className="page-back"><ArrowLeft className="w-5 h-5" /></Link>
            <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center text-green-600">
              <Heart className="w-4 h-4" />
            </div>
            <h1 className="text-lg font-semibold tracking-tight">Ask Readiness</h1>
          </div>
          <div className="flex items-center justify-center h-64">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              Loading ask-readiness scores...
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-background">
        <div className="max-w-7xl mx-auto p-4">
          <div className="page-header">
            <Link href="/" className="page-back"><ArrowLeft className="w-5 h-5" /></Link>
            <h1 className="text-lg font-semibold">Ask Readiness</h1>
          </div>
          <p className="text-destructive">{error}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="max-w-[1400px] mx-auto p-4">
        {/* Header */}
        <div className="page-header">
          <Link href="/" className="page-back" aria-label="Back to dashboard">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center text-green-600">
            <Heart className="w-4 h-4" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight">
            Ask Readiness — Outdoorithm Fundraising
          </h1>
          <span className="ml-auto text-xs text-muted-foreground font-mono">
            {contacts.length.toLocaleString()} scored
          </span>
        </div>

        {/* Tier summary cards */}
        {tierCounts && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            {(Object.entries(TIER_CONFIG) as [string, typeof TIER_CONFIG[string]][]).map(
              ([tier, config]) => {
                const count = tierCounts[tier as keyof TierCounts] || 0;
                const isActive = activeTiers.has(tier);
                return (
                  <button
                    key={tier}
                    onClick={() => toggleTier(tier)}
                    className={cn(
                      'rounded-lg border p-3 text-left transition-all',
                      isActive
                        ? `${config.bg} ring-2 ring-offset-1 ring-primary/30`
                        : 'bg-card hover:bg-muted/50'
                    )}
                  >
                    <div className={cn('text-2xl font-mono font-bold', config.color)}>
                      {count.toLocaleString()}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">{config.label}</div>
                  </button>
                );
              }
            )}
          </div>
        )}

        {/* Search + actions bar */}
        <div className="flex items-center gap-3 mb-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by name, company, reasoning..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {activeTiers.size > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setActiveTiers(new Set())}
              className="text-xs gap-1"
            >
              <X className="w-3 h-3" />
              Clear filter
            </Button>
          )}

          <span className="text-xs text-muted-foreground ml-auto">
            {filteredAndSorted.length.toLocaleString()} contacts
          </span>

          <Button variant="outline" size="sm" onClick={handleExportCSV} className="gap-1.5">
            <Download className="w-3.5 h-3.5" />
            CSV
          </Button>
        </div>

        {/* Table */}
        <Card>
          <ScrollArea className="h-[calc(100vh-300px)] min-h-[400px]">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 sticky top-0 z-10">
                <tr className="border-b">
                  {([
                    ['score', 'Score', 'w-[100px]'],
                    ['tier', 'Tier', 'w-[110px]'],
                    ['name', 'Name', 'min-w-[160px]'],
                    ['company', 'Company', 'min-w-[140px]'],
                    ['familiarity', 'Familiarity', 'w-[100px]'],
                    ['last_contact', 'Last Contact', 'w-[100px]'],
                    ['capacity', 'Capacity', 'w-[100px]'],
                  ] as [SortField, string, string][]).map(([field, label, width]) => (
                    <th key={field} className={cn('text-left p-2', width)}>
                      <button
                        onClick={() => handleSort(field)}
                        className={cn(
                          'flex items-center font-medium text-xs uppercase tracking-wide transition-colors',
                          sortBy === field
                            ? 'text-foreground'
                            : 'text-muted-foreground hover:text-foreground'
                        )}
                      >
                        {label}
                        {getSortIcon(field)}
                      </button>
                    </th>
                  ))}
                  <th className="text-left p-2 min-w-[200px]">
                    <span className="font-medium text-xs uppercase tracking-wide text-muted-foreground">
                      Reasoning & Strategy
                    </span>
                  </th>
                  <th className="w-8 p-2" />
                </tr>
              </thead>
              <tbody>
                {filteredAndSorted.map((contact) => {
                  const isExpanded = expandedId === contact.id;
                  const tierConfig = TIER_CONFIG[contact.tier] || TIER_CONFIG.long_term;
                  const ocEng = contact.oc_engagement;
                  const isOcDonor = ocEng?.is_oc_donor;
                  const ocRoles = ocEng?.crm_roles as string[] | undefined;

                  return (
                    <tr
                      key={contact.id}
                      className="border-b hover:bg-muted/30 transition-colors group"
                    >
                      {/* Score */}
                      <td className="p-2">
                        <ScoreBar score={contact.score} />
                      </td>

                      {/* Tier */}
                      <td className="p-2">
                        <Badge
                          variant="outline"
                          className={cn('text-[10px] px-1.5 py-0 font-medium', tierConfig.bg, tierConfig.color)}
                        >
                          {tierConfig.label}
                        </Badge>
                      </td>

                      {/* Name */}
                      <td className="p-2">
                        <button
                          className="font-medium text-left hover:text-primary hover:underline underline-offset-2 transition-colors"
                          onClick={() => {
                            setSelectedContactId(contact.id);
                            setSheetOpen(true);
                          }}
                        >
                          {contact.first_name} {contact.last_name}
                        </button>
                        {contact.headline && (
                          <div className="text-xs text-muted-foreground truncate max-w-[200px]">
                            {contact.headline}
                          </div>
                        )}
                        {/* OC engagement badges */}
                        {ocRoles && ocRoles.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {isOcDonor && (
                              <Badge variant="outline" className="text-[9px] px-1 py-0 bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800">
                                OC Donor
                              </Badge>
                            )}
                            {ocRoles.includes('Participant') && (
                              <Badge variant="outline" className="text-[9px] px-1 py-0 bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-900/30 dark:text-sky-300 dark:border-sky-800">
                                OC Participant
                              </Badge>
                            )}
                            {ocRoles.includes('Board') && (
                              <Badge variant="outline" className="text-[9px] px-1 py-0 bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-800">
                                OC Board
                              </Badge>
                            )}
                          </div>
                        )}
                      </td>

                      {/* Company */}
                      <td className="p-2 max-w-[160px]">
                        {contact.company ? (
                          <div className="flex items-center gap-1.5 truncate">
                            <Building2 className="w-3 h-3 text-muted-foreground shrink-0" />
                            <span className="truncate">{contact.company}</span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>

                      {/* Familiarity */}
                      <td className="p-2">
                        {contact.familiarity_rating != null && contact.familiarity_rating > 0 ? (
                          <FamiliarityDots rating={contact.familiarity_rating} />
                        ) : (
                          <span className="text-muted-foreground text-xs">—</span>
                        )}
                      </td>

                      {/* Last Contact */}
                      <td className="p-2">
                        {contact.comms_last_date ? (
                          <div>
                            <span className={cn('text-xs tabular-nums', getRecencyColor(contact.comms_last_date))}>
                              {formatShortDate(contact.comms_last_date)}
                            </span>
                            {contact.comms_thread_count != null && contact.comms_thread_count > 0 && (
                              <div className="text-[10px] text-muted-foreground">
                                {contact.comms_thread_count} threads
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-muted-foreground text-xs">—</span>
                        )}
                      </td>

                      {/* Capacity */}
                      <td className="p-2">
                        {contact.ai_capacity_tier ? (
                          <Badge
                            variant="outline"
                            className={cn(
                              'text-[10px] px-1.5 py-0 font-medium',
                              CAPACITY_COLORS[contact.ai_capacity_tier] || ''
                            )}
                          >
                            {CAPACITY_LABELS[contact.ai_capacity_tier] || contact.ai_capacity_tier}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>

                      {/* Reasoning & Strategy summary */}
                      <td className="p-2">
                        <div className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                          {contact.reasoning}
                        </div>
                        {isExpanded && (
                          <div className="mt-2 space-y-2 text-xs border-t pt-2">
                            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                              <div>
                                <span className="text-muted-foreground">Approach:</span>{' '}
                                <span className="font-medium">
                                  {APPROACH_LABELS[contact.recommended_approach] || contact.recommended_approach}
                                </span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Timing:</span>{' '}
                                <span className="font-medium">
                                  {TIMING_LABELS[contact.ask_timing] || contact.ask_timing}
                                </span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Ask Range:</span>{' '}
                                <span className="font-medium">{contact.suggested_ask_range}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">OC Fit:</span>{' '}
                                <span className="font-medium">{contact.ai_outdoorithm_fit || '—'}</span>
                              </div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Cultivation:</span>{' '}
                              <span>{contact.cultivation_needed}</span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Personalization:</span>{' '}
                              <span className="italic">{contact.personalization_angle}</span>
                            </div>
                            {contact.risk_factors.length > 0 && (
                              <div>
                                <span className="text-muted-foreground">Risks:</span>{' '}
                                <span className="text-red-600 dark:text-red-400">
                                  {contact.risk_factors.join('; ')}
                                </span>
                              </div>
                            )}
                            {ocEng && (
                              <div>
                                <span className="text-muted-foreground">OC Engagement:</span>{' '}
                                {isOcDonor && (
                                  <span>
                                    Donor (${(ocEng.oc_total_donated || 0).toLocaleString()}, {ocEng.oc_donation_count} donations)
                                  </span>
                                )}
                                {(ocEng.trips_attended > 0 || ocEng.trips_registered > 0) && (
                                  <span>
                                    {isOcDonor ? ' · ' : ''}
                                    {ocEng.trips_attended} trips attended, {ocEng.trips_registered} registered
                                  </span>
                                )}
                                {!isOcDonor && !ocEng.trips_attended && ocRoles && (
                                  <span>{ocRoles.join(', ')}</span>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </td>

                      {/* Expand toggle */}
                      <td className="p-2">
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : contact.id)}
                          className="p-1 rounded hover:bg-muted transition-colors"
                          aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-muted-foreground" />
                          )}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </ScrollArea>
        </Card>
      </div>

      <ContactDetailSheet
        contactId={selectedContactId}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
      />
    </main>
  );
}
