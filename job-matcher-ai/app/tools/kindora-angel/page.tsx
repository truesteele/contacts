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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  ArrowLeft,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Building2,
  Download,
  Filter,
  TrendingUp,
  Loader2,
  Search,
  ChevronDown,
  ChevronRight,
  X,
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────

interface AngelProspectContact {
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
  investor_status?: string | null;
  pitchbook_investments?: number | null;
  edgar_filings?: number | null;
  edgar_signal?: string | null;
  check_size?: string | null;
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

const INVESTOR_STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  pitchbook_verified: {
    label: 'PitchBook Verified',
    color: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/40 dark:text-green-300',
  },
  pitchbook_institutional: {
    label: 'Institutional',
    color: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300',
  },
  edgar_verified: {
    label: 'SEC Filing',
    color: 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/40 dark:text-amber-300',
  },
  self_identified: {
    label: 'Self-Identified',
    color: 'bg-violet-100 text-violet-800 border-violet-200 dark:bg-violet-900/40 dark:text-violet-300',
  },
};

const CHECK_SIZE_ORDER: Record<string, number> = {
  '$50K': 5,
  '$25K-$50K': 4,
  '$25K': 4,
  '$10K-$25K': 3,
  '$10K-$50K': 3,
  '$10K': 2,
  'Not recommended': 0,
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

export default function KindoraAngelPage() {
  const [contacts, setContacts] = useState<AngelProspectContact[]>([]);
  const [tierCounts, setTierCounts] = useState<TierCounts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTiers, setActiveTiers] = useState<Set<string>>(new Set());
  const [filterInvestor, setFilterInvestor] = useState<string>('all');
  const [filterApproach, setFilterApproach] = useState<string>('all');
  const [filterTiming, setFilterTiming] = useState<string>('all');
  const [filterComms, setFilterComms] = useState<string>('all');
  const [sortBy, setSortBy] = useState<SortField>('score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [selectedContactId, setSelectedContactId] = useState<number | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [savingField, setSavingField] = useState<string | null>(null);

  const loadContacts = useCallback(async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) {
      setLoading(true);
      setError('');
    }

    try {
      const res = await fetch('/api/network-intel/kindora-angel');
      if (!res.ok) throw new Error('Failed to load');
      const data = await res.json();
      setContacts(data.contacts || []);
      setTierCounts(data.tier_counts || null);
      if (!opts?.silent) {
        setError('');
      }
    } catch (err: any) {
      if (opts?.silent) {
        console.error('[Kindora Angel] Failed to refresh contacts:', err);
      } else {
        setError(err.message || 'Failed to load contacts');
      }
    } finally {
      if (!opts?.silent) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    loadContacts();
  }, [loadContacts]);

  const updateContact = useCallback(async (contactId: number, field: 'tier', value: string) => {
    const key = `${contactId}-${field}`;
    setSavingField(key);
    try {
      const res = await fetch('/api/network-intel/kindora-angel', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contact_id: contactId, field, value }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Update failed');
      }
      setContacts((prev) =>
        prev.map((c) => {
          if (c.id !== contactId) return c;
          return { ...c, tier: value };
        })
      );
    } catch (err) {
      console.error(`[Kindora Angel] Failed to update ${field}:`, err);
    } finally {
      setSavingField(null);
    }
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

  const activeFilterCount = useMemo(() => {
    let count = activeTiers.size > 0 ? 1 : 0;
    if (filterInvestor !== 'all') count++;
    if (filterApproach !== 'all') count++;
    if (filterTiming !== 'all') count++;
    if (filterComms !== 'all') count++;
    return count;
  }, [activeTiers, filterInvestor, filterApproach, filterTiming, filterComms]);

  const clearAllFilters = useCallback(() => {
    setActiveTiers(new Set());
    setFilterInvestor('all');
    setFilterApproach('all');
    setFilterTiming('all');
    setFilterComms('all');
    setSearchTerm('');
  }, []);

  const filteredAndSorted = useMemo(() => {
    let result = contacts;

    if (activeTiers.size > 0) {
      result = result.filter((c) => activeTiers.has(c.tier));
    }

    if (filterInvestor !== 'all') {
      if (filterInvestor === 'verified') {
        result = result.filter((c) => c.investor_status != null);
      } else if (filterInvestor === 'sec_filing') {
        result = result.filter((c) => c.edgar_filings != null && c.edgar_filings > 0);
      } else {
        result = result.filter((c) => c.investor_status === filterInvestor);
      }
    }

    if (filterApproach !== 'all') {
      result = result.filter((c) => c.recommended_approach === filterApproach);
    }

    if (filterTiming !== 'all') {
      result = result.filter((c) => c.ask_timing === filterTiming);
    }

    if (filterComms === 'yes') {
      result = result.filter((c) => c.comms_last_date);
    } else if (filterComms === 'no') {
      result = result.filter((c) => !c.comms_last_date);
    }

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
        case 'capacity': {
          const aInv = a.investor_status ? 2 : 0;
          const bInv = b.investor_status ? 2 : 0;
          const aChk = CHECK_SIZE_ORDER[a.check_size || ''] ?? -1;
          const bChk = CHECK_SIZE_ORDER[b.check_size || ''] ?? -1;
          cmp = (aInv + aChk) - (bInv + bChk);
          break;
        }
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
  }, [contacts, activeTiers, filterInvestor, filterApproach, filterTiming, filterComms, searchTerm, sortBy, sortOrder]);

  const handleExportCSV = useCallback(() => {
    if (filteredAndSorted.length === 0) return;

    const headers = [
      'Name', 'Company', 'Position', 'City', 'State', 'Score', 'Tier',
      'Reasoning', 'Approach', 'Timing', 'Cultivation Needed',
      'Check Size', 'Personalization Angle', 'Risk Factors',
      'Familiarity', 'Last Contact', 'Email Threads', 'Investor Status', 'Check Size',
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
      c.comms_thread_count ?? '', c.investor_status || '', c.check_size || '',
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
    link.setAttribute('download', `kindora_angel_prospects_${new Date().toISOString().split('T')[0]}.csv`);
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
            <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center text-violet-600">
              <TrendingUp className="w-4 h-4" />
            </div>
            <h1 className="text-lg font-semibold tracking-tight">Kindora Angel Prospects</h1>
          </div>
          <div className="flex items-center justify-center h-64">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              Loading angel prospect scores...
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
            <h1 className="text-lg font-semibold">Kindora Angel Prospects</h1>
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
          <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center text-violet-600">
            <TrendingUp className="w-4 h-4" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight">
            Kindora Angel Prospects
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
        <div className="flex items-center gap-3 mb-2">
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

          <span className="text-xs text-muted-foreground ml-auto">
            {filteredAndSorted.length.toLocaleString()} contacts
          </span>

          <Button variant="outline" size="sm" onClick={handleExportCSV} className="gap-1.5">
            <Download className="w-3.5 h-3.5" />
            CSV
          </Button>
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-muted-foreground shrink-0" />

          <Select value={filterInvestor} onValueChange={setFilterInvestor}>
            <SelectTrigger className="h-7 w-[150px] text-xs">
              <SelectValue placeholder="Investor" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Investors</SelectItem>
              <SelectItem value="verified">Any Verified</SelectItem>
              {Object.entries(INVESTOR_STATUS_CONFIG).map(([val, cfg]) => (
                <SelectItem key={val} value={val}>{cfg.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={filterApproach} onValueChange={setFilterApproach}>
            <SelectTrigger className="h-7 w-[150px] text-xs">
              <SelectValue placeholder="Approach" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Approaches</SelectItem>
              {Object.entries(APPROACH_LABELS).map(([val, label]) => (
                <SelectItem key={val} value={val}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={filterTiming} onValueChange={setFilterTiming}>
            <SelectTrigger className="h-7 w-[155px] text-xs">
              <SelectValue placeholder="Timing" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Timing</SelectItem>
              {Object.entries(TIMING_LABELS).map(([val, label]) => (
                <SelectItem key={val} value={val}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={filterComms} onValueChange={setFilterComms}>
            <SelectTrigger className="h-7 w-[130px] text-xs">
              <SelectValue placeholder="Comms" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Comms</SelectItem>
              <SelectItem value="yes">Has Comms</SelectItem>
              <SelectItem value="no">No Comms</SelectItem>
            </SelectContent>
          </Select>

          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="text-xs gap-1 h-7 px-2"
            >
              <X className="w-3 h-3" />
              Clear all ({activeFilterCount})
            </Button>
          )}
        </div>

        {/* Table */}
        <Card>
          <ScrollArea className="h-[calc(100vh-300px)] min-h-[400px]">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 sticky top-0 z-10">
                <tr className="border-b">
                  <th className="text-left p-2 w-[40px]">
                    <span className="font-medium text-xs uppercase tracking-wide text-muted-foreground">#</span>
                  </th>
                  {([
                    ['score', 'Score', 'w-[100px]'],
                    ['tier', 'Tier', 'w-[130px]'],
                    ['name', 'Name', 'min-w-[160px]'],
                    ['company', 'Company', 'min-w-[140px]'],
                    ['familiarity', 'Familiarity', 'w-[100px]'],
                    ['last_contact', 'Last Contact', 'w-[100px]'],
                    ['capacity', 'Investor', 'w-[140px]'],
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
                </tr>
              </thead>
              <tbody>
                {filteredAndSorted.map((contact, index) => {
                  const isExpanded = expandedId === contact.id;
                  const tierConfig = TIER_CONFIG[contact.tier] || TIER_CONFIG.long_term;

                  return (
                    <tr
                      key={contact.id}
                      className="border-b hover:bg-muted/30 transition-colors group"
                    >
                      {/* Row number */}
                      <td className="p-2 text-xs text-muted-foreground font-mono tabular-nums">
                        {index + 1}
                      </td>
                      {/* Score */}
                      <td className="p-2">
                        <ScoreBar score={contact.score} />
                      </td>

                      {/* Tier (editable) */}
                      <td className="p-2">
                        <Select
                          value={contact.tier}
                          onValueChange={(val) => updateContact(contact.id, 'tier', val)}
                        >
                          <SelectTrigger className={cn(
                            'h-6 w-[110px] text-[10px] px-1.5 py-0 font-medium border rounded-full',
                            tierConfig.bg, tierConfig.color
                          )}>
                            {savingField === `${contact.id}-tier` ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <SelectValue />
                            )}
                          </SelectTrigger>
                          <SelectContent>
                            {Object.entries(TIER_CONFIG).map(([val, cfg]) => (
                              <SelectItem key={val} value={val}>
                                <span className={cn('text-xs', cfg.color)}>{cfg.label}</span>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
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

                      {/* Investor Profile */}
                      <td className="p-2">
                        <div className="flex flex-col gap-0.5">
                          {contact.investor_status && (() => {
                            const cfg = INVESTOR_STATUS_CONFIG[contact.investor_status];
                            if (!cfg) return null;
                            const count = contact.pitchbook_investments ?? contact.edgar_filings;
                            return (
                              <Badge
                                variant="outline"
                                className={cn('text-[10px] px-1.5 py-0 font-medium whitespace-nowrap', cfg.color)}
                              >
                                {cfg.label}
                                {count != null && count > 0 && (
                                  <span className="ml-1 opacity-70">({count})</span>
                                )}
                              </Badge>
                            );
                          })()}
                          {contact.check_size && contact.check_size !== 'Not recommended' && (
                            <span className="text-[10px] text-muted-foreground font-mono">
                              {contact.check_size}
                            </span>
                          )}
                          {!contact.investor_status && (!contact.check_size || contact.check_size === 'Not recommended') && (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </div>
                      </td>

                      {/* Reasoning & Strategy */}
                      <td className="p-2">
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : contact.id)}
                          className="flex items-start gap-1.5 text-left w-full group/reason"
                        >
                          <span className="shrink-0 mt-0.5">
                            {isExpanded ? (
                              <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
                            )}
                          </span>
                          {!isExpanded && (
                            <span className="text-xs text-muted-foreground leading-relaxed line-clamp-2 group-hover/reason:text-foreground transition-colors">
                              {contact.reasoning}
                            </span>
                          )}
                        </button>
                        {isExpanded && (
                          <div className="mt-1 ml-5 space-y-2 text-xs">
                            <div className="text-muted-foreground leading-relaxed">
                              {contact.reasoning}
                            </div>
                            <div className="border-t pt-2 grid grid-cols-2 gap-x-4 gap-y-1.5">
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
                                <span className="text-muted-foreground">Check Size:</span>{' '}
                                <span className="font-medium">{contact.suggested_ask_range}</span>
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
                          </div>
                        )}
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
        onUpdated={() => {
          void loadContacts({ silent: true });
        }}
      />
    </main>
  );
}
