'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AlumniDetailSheet } from '@/components/alumni-detail-sheet';
import { cn } from '@/lib/utils';
import {
  Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  ArrowUpDown, ArrowUp, ArrowDown, Building2, Download, Filter, Search,
  ChevronDown, ChevronRight, X, Users, TrendingUp, DollarSign, Newspaper,
  MessageSquare, BarChart3, Table2, Zap, AlertTriangle,
} from 'lucide-react';
import {
  STAGE_CONFIG, SECTOR_CONFIG, ACTIVITY_CONFIG,
  type Alumni, type VentureStage, type Sector, type ActivityLevel, type VentureType,
} from '@/lib/mock-data';

// ── Types ──────────────────────────────────────────────────────────────

type SortField = 'activity_score' | 'name' | 'venture' | 'funding' | 'team_size' | 'linkedin_engagement' | 'news' | 'stage' | 'cohort';
type TabView = 'detailed' | 'dashboard';

// ── Helpers ────────────────────────────────────────────────────────────

function ScoreBar({ score, color }: { score: number; color?: string }) {
  const getColor = (s: number) => {
    if (color) return color;
    if (s >= 80) return 'bg-green-500';
    if (s >= 60) return 'bg-blue-500';
    if (s >= 40) return 'bg-yellow-500';
    return 'bg-gray-400';
  };
  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', getColor(score))} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-mono tabular-nums font-medium w-6 text-right">{score}</span>
    </div>
  );
}

function MomentumBadge({ momentum }: { momentum: string }) {
  const config: Record<string, { label: string; class: string }> = {
    rising: { label: 'Rising', class: 'bg-green-100 text-green-700 border-green-200' },
    stable: { label: 'Stable', class: 'bg-blue-100 text-blue-700 border-blue-200' },
    declining: { label: 'Declining', class: 'bg-red-100 text-red-700 border-red-200' },
    unknown: { label: 'Unknown', class: 'bg-gray-100 text-gray-600 border-gray-200' },
  };
  const c = config[momentum] || config.unknown;
  return <Badge variant="outline" className={cn('text-[10px] px-1.5 py-0', c.class)}>{c.label}</Badge>;
}

function formatCurrency(n: number, isNonprofit?: boolean): string {
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  if (n === 0) return isNonprofit ? 'New' : 'Bootstrap';
  return `$${n}`;
}

function VentureTypeBadge({ type }: { type: VentureType }) {
  return type === 'nonprofit' ? (
    <Badge variant="outline" className="text-[9px] px-1 py-0 bg-teal-100 text-teal-700 border-teal-200">Nonprofit</Badge>
  ) : null;
}

function formatShortDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ── Dashboard Tab ──────────────────────────────────────────────────────

function DashboardView({ alumni }: { alumni: Alumni[] }) {
  const stats = useMemo(() => {
    const totalFunding = alumni.reduce((s, a) => s + a.total_funding, 0);
    const totalTeam = alumni.reduce((s, a) => s + a.team_size, 0);
    const activeVentures = alumni.filter(a => !['closed', 'acquired', 'merged'].includes(a.venture_stage)).length;
    const rising = alumni.filter(a => a.momentum === 'rising').length;
    const declining = alumni.filter(a => a.momentum === 'declining').length;
    const avgActivity = Math.round(alumni.reduce((s, a) => s + a.activity_score, 0) / alumni.length);
    const avgEngagement = (alumni.reduce((s, a) => s + a.linkedin_engagement_rate, 0) / alumni.length).toFixed(1);
    const totalNews = alumni.reduce((s, a) => s + a.news_mentions_90d, 0);
    const totalPosts = alumni.reduce((s, a) => s + a.linkedin_posts_30d, 0);

    const stageCounts: Record<string, number> = {};
    const sectorCounts: Record<string, number> = {};
    const cohortCounts: Record<string, number> = {};
    for (const a of alumni) {
      stageCounts[a.venture_stage] = (stageCounts[a.venture_stage] || 0) + 1;
      sectorCounts[a.sector] = (sectorCounts[a.sector] || 0) + 1;
      cohortCounts[a.cohort] = (cohortCounts[a.cohort] || 0) + 1;
    }

    const forProfitCount = alumni.filter(a => a.venture_type === 'for_profit').length;
    const nonprofitCount = alumni.filter(a => a.venture_type === 'nonprofit').length;
    const totalPeopleServed = alumni.filter(a => a.venture_type === 'nonprofit' && a.people_served).reduce((s, a) => s + (a.people_served || 0), 0);
    const totalGrantFunding = alumni.filter(a => a.venture_type === 'nonprofit').reduce((s, a) => s + a.total_funding, 0);
    const totalVCFunding = alumni.filter(a => a.venture_type === 'for_profit').reduce((s, a) => s + a.total_funding, 0);

    const topByActivity = [...alumni].sort((a, b) => b.activity_score - a.activity_score).slice(0, 5);
    const topByFunding = [...alumni].filter(a => a.venture_type === 'for_profit' && a.total_funding > 0).sort((a, b) => b.total_funding - a.total_funding).slice(0, 5);
    const topByGrants = [...alumni].filter(a => a.venture_type === 'nonprofit' && a.total_funding > 0).sort((a, b) => b.total_funding - a.total_funding).slice(0, 5);
    const topByImpact = [...alumni].filter(a => a.venture_type === 'nonprofit' && a.people_served && a.people_served > 0).sort((a, b) => (b.people_served || 0) - (a.people_served || 0)).slice(0, 5);
    const needsAttention = alumni.filter(a => a.risk_flags.length > 0 || a.momentum === 'declining' || a.activity_level === 'inactive' || a.activity_level === 'quiet');
    const recentNews = alumni.filter(a => a.last_news_headline).sort((a, b) => (b.last_news_date || '').localeCompare(a.last_news_date || '')).slice(0, 5);
    const nonprofitTeam = alumni.filter(a => a.venture_type === 'nonprofit').reduce((s, a) => s + a.team_size, 0);
    const forProfitTeam = alumni.filter(a => a.venture_type === 'for_profit').reduce((s, a) => s + a.team_size, 0);

    return { totalFunding, totalTeam, activeVentures, rising, declining, avgActivity, avgEngagement, totalNews, totalPosts, stageCounts, sectorCounts, cohortCounts, topByActivity, topByFunding, topByGrants, topByImpact, needsAttention, recentNews, forProfitCount, nonprofitCount, totalPeopleServed, totalGrantFunding, totalVCFunding, nonprofitTeam, forProfitTeam };
  }, [alumni]);

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <Card className="p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Users className="w-4 h-4" /> Portfolio
          </div>
          <div className="text-2xl font-bold">{stats.activeVentures}</div>
          <div className="text-xs text-muted-foreground">{stats.nonprofitCount} nonprofit &middot; {stats.forProfitCount} for-profit</div>
        </Card>
        <Card className="p-4 border-teal-200 bg-teal-50/30 dark:bg-teal-900/10 dark:border-teal-800">
          <div className="flex items-center gap-2 text-sm text-teal-700 dark:text-teal-400 mb-1">
            <DollarSign className="w-4 h-4" /> Grants Received
          </div>
          <div className="text-2xl font-bold text-teal-800 dark:text-teal-300">{formatCurrency(stats.totalGrantFunding)}</div>
          <div className="text-xs text-teal-600 dark:text-teal-400">{stats.nonprofitCount} nonprofit orgs &middot; {stats.nonprofitTeam} staff</div>
        </Card>
        <Card className="p-4 border-teal-200 bg-teal-50/30 dark:bg-teal-900/10 dark:border-teal-800">
          <div className="flex items-center gap-2 text-sm text-teal-700 dark:text-teal-400 mb-1">
            <Users className="w-4 h-4" /> People Served
          </div>
          <div className="text-2xl font-bold text-teal-800 dark:text-teal-300">{stats.totalPeopleServed.toLocaleString()}</div>
          <div className="text-xs text-teal-600 dark:text-teal-400">across nonprofit ventures</div>
        </Card>
        <Card className="p-4 border-indigo-200 bg-indigo-50/30 dark:bg-indigo-900/10 dark:border-indigo-800">
          <div className="flex items-center gap-2 text-sm text-indigo-700 dark:text-indigo-400 mb-1">
            <DollarSign className="w-4 h-4" /> Capital Raised
          </div>
          <div className="text-2xl font-bold text-indigo-800 dark:text-indigo-300">{formatCurrency(stats.totalVCFunding)}</div>
          <div className="text-xs text-indigo-600 dark:text-indigo-400">{stats.forProfitCount} for-profit ventures &middot; {stats.forProfitTeam} employees</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <TrendingUp className="w-4 h-4" /> Momentum
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-green-600">{stats.rising}</span>
            <span className="text-sm text-green-600">rising</span>
            {stats.declining > 0 && (
              <>
                <span className="text-lg font-bold text-red-500">{stats.declining}</span>
                <span className="text-sm text-red-500">declining</span>
              </>
            )}
          </div>
          <div className="text-xs text-muted-foreground">Avg activity: {stats.avgActivity} &middot; {stats.totalNews} news (90d)</div>
        </Card>
      </div>

      {/* Stage & Sector breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="p-4">
          <h3 className="text-sm font-semibold mb-3">Portfolio by Stage</h3>
          <div className="space-y-2">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-teal-600 dark:text-teal-400 mt-1">Nonprofit</div>
            {Object.entries(STAGE_CONFIG)
              .filter(([, conf]) => conf.group === 'nonprofit')
              .sort((a, b) => a[1].order - b[1].order)
              .map(([stage, conf]) => {
                const count = stats.stageCounts[stage] || 0;
                if (count === 0) return null;
                const pct = Math.round((count / alumni.length) * 100);
                return (
                  <div key={stage} className="flex items-center gap-3">
                    <Badge variant="outline" className={cn('text-[10px] px-1.5 py-0 w-20 justify-center', conf.bg, conf.color)}>
                      {conf.label}
                    </Badge>
                    <div className="flex-1 h-3 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                      <div className="h-full rounded-full bg-teal-400/60 transition-all" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs font-mono w-8 text-right">{count}</span>
                  </div>
                );
              })}
            <div className="text-[10px] font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mt-3">For-Profit</div>
            {Object.entries(STAGE_CONFIG)
              .filter(([, conf]) => conf.group === 'for_profit')
              .sort((a, b) => a[1].order - b[1].order)
              .map(([stage, conf]) => {
                const count = stats.stageCounts[stage] || 0;
                if (count === 0) return null;
                const pct = Math.round((count / alumni.length) * 100);
                return (
                  <div key={stage} className="flex items-center gap-3">
                    <Badge variant="outline" className={cn('text-[10px] px-1.5 py-0 w-20 justify-center', conf.bg, conf.color)}>
                      {conf.label}
                    </Badge>
                    <div className="flex-1 h-3 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                      <div className="h-full rounded-full bg-indigo-400/60 transition-all" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs font-mono w-8 text-right">{count}</span>
                  </div>
                );
              })}
            {Object.entries(STAGE_CONFIG)
              .filter(([, conf]) => conf.group === 'shared')
              .map(([stage, conf]) => {
                const count = stats.stageCounts[stage] || 0;
                if (count === 0) return null;
                const pct = Math.round((count / alumni.length) * 100);
                return (
                  <div key={stage} className="flex items-center gap-3 mt-2">
                    <Badge variant="outline" className={cn('text-[10px] px-1.5 py-0 w-20 justify-center', conf.bg, conf.color)}>
                      {conf.label}
                    </Badge>
                    <div className="flex-1 h-3 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                      <div className="h-full rounded-full bg-gray-400/60 transition-all" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs font-mono w-8 text-right">{count}</span>
                  </div>
                );
              })}
          </div>
        </Card>
        <Card className="p-4">
          <h3 className="text-sm font-semibold mb-3">Portfolio by Sector</h3>
          <div className="space-y-2">
            {Object.entries(stats.sectorCounts)
              .sort((a, b) => b[1] - a[1])
              .map(([sector, count]) => {
                const conf = SECTOR_CONFIG[sector as Sector];
                const pct = Math.round((count / alumni.length) * 100);
                return (
                  <div key={sector} className="flex items-center gap-3">
                    <Badge variant="outline" className={cn('text-[10px] px-1.5 py-0 w-24 justify-center', conf?.color)}>
                      {conf?.label || sector}
                    </Badge>
                    <div className="flex-1 h-3 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                      <div className="h-full rounded-full bg-primary/60 transition-all" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs font-mono w-8 text-right">{count}</span>
                  </div>
                );
              })}
          </div>
        </Card>
      </div>

      {/* Leaderboards — 3 columns */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-yellow-500" /> Most Active (30 Days)
          </h3>
          <div className="space-y-2">
            {stats.topByActivity.map((a, i) => (
              <div key={a.id} className="flex items-center gap-2 text-sm">
                <span className="text-xs text-muted-foreground font-mono w-4">{i + 1}.</span>
                <div className="flex-1 min-w-0">
                  <span className="font-medium">{a.first_name} {a.last_name}</span>
                  <span className="text-muted-foreground"> &middot; {a.venture_name}</span>
                </div>
                <ScoreBar score={a.activity_score} />
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-4 border-teal-200 bg-teal-50/30 dark:bg-teal-900/10 dark:border-teal-800">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5 text-teal-700 dark:text-teal-400">
            <DollarSign className="w-3.5 h-3.5" /> Nonprofit — Top Grants
          </h3>
          <div className="space-y-2">
            {stats.topByGrants.map((a, i) => (
              <div key={a.id} className="flex items-center gap-2 text-sm">
                <span className="text-xs text-muted-foreground font-mono w-4">{i + 1}.</span>
                <div className="flex-1 min-w-0">
                  <span className="font-medium">{a.first_name} {a.last_name}</span>
                  <span className="text-muted-foreground"> &middot; {a.venture_name}</span>
                </div>
                <span className="font-mono text-xs font-medium">{formatCurrency(a.total_funding)}</span>
              </div>
            ))}
          </div>
          {stats.topByImpact.length > 0 && (
            <>
              <h3 className="text-sm font-semibold mt-4 mb-3 flex items-center gap-1.5 text-teal-700 dark:text-teal-400">
                <Users className="w-3.5 h-3.5" /> Nonprofit — People Served
              </h3>
              <div className="space-y-2">
                {stats.topByImpact.map((a, i) => (
                  <div key={a.id} className="flex items-center gap-2 text-sm">
                    <span className="text-xs text-muted-foreground font-mono w-4">{i + 1}.</span>
                    <div className="flex-1 min-w-0">
                      <span className="font-medium">{a.first_name} {a.last_name}</span>
                      <span className="text-muted-foreground"> &middot; {a.venture_name}</span>
                    </div>
                    <span className="font-mono text-xs font-medium">{(a.people_served || 0).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
        <Card className="p-4 border-indigo-200 bg-indigo-50/30 dark:bg-indigo-900/10 dark:border-indigo-800">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5 text-indigo-700 dark:text-indigo-400">
            <DollarSign className="w-3.5 h-3.5" /> For-Profit — Capital Raised
          </h3>
          <div className="space-y-2">
            {stats.topByFunding.map((a, i) => (
              <div key={a.id} className="flex items-center gap-2 text-sm">
                <span className="text-xs text-muted-foreground font-mono w-4">{i + 1}.</span>
                <div className="flex-1 min-w-0">
                  <span className="font-medium">{a.first_name} {a.last_name}</span>
                  <span className="text-muted-foreground"> &middot; {a.venture_name}</span>
                </div>
                <span className="font-mono text-xs font-medium">{formatCurrency(a.total_funding)}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Recent news feed */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
          <Newspaper className="w-3.5 h-3.5 text-blue-500" /> Recent News
        </h3>
        <div className="space-y-3">
          {stats.recentNews.map((a) => (
            <div key={a.id} className="flex items-start gap-3 text-sm">
              <div className="w-8 h-8 rounded bg-primary/10 flex items-center justify-center text-primary font-bold text-xs shrink-0">
                {a.venture_name.charAt(0)}
              </div>
              <div className="flex-1">
                <div className="font-medium">{a.last_news_headline}</div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {a.venture_name} &middot; {a.last_news_date && formatShortDate(a.last_news_date)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Needs attention */}
      {stats.needsAttention.length > 0 && (
        <Card className="p-4 border-amber-200 bg-amber-50/50 dark:bg-amber-900/10 dark:border-amber-800">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5 text-amber-700 dark:text-amber-400">
            <AlertTriangle className="w-3.5 h-3.5" /> Needs Attention ({stats.needsAttention.length})
          </h3>
          <div className="space-y-2">
            {stats.needsAttention.map((a) => (
              <div key={a.id} className="flex items-start gap-2 text-sm">
                <span className="font-medium">{a.first_name} {a.last_name}</span>
                <span className="text-muted-foreground">&middot; {a.venture_name}</span>
                <div className="ml-auto flex gap-1">
                  {a.momentum === 'declining' && <MomentumBadge momentum="declining" />}
                  {(a.activity_level === 'inactive' || a.activity_level === 'quiet') && (
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-orange-100 text-orange-700 border-orange-200">
                      {ACTIVITY_CONFIG[a.activity_level].label}
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────

export default function AlumniIntelligencePage() {
  const [alumni, setAlumni] = useState<Alumni[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<TabView>('detailed');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStage, setFilterStage] = useState<string>('all');
  const [filterSector, setFilterSector] = useState<string>('all');
  const [filterActivity, setFilterActivity] = useState<string>('all');
  const [filterMomentum, setFilterMomentum] = useState<string>('all');
  const [filterVentureType, setFilterVentureType] = useState<string>('all');
  const [sortBy, setSortBy] = useState<SortField>('activity_score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [selectedAlumniId, setSelectedAlumniId] = useState<number | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const loadAlumni = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/alumni');
      if (!res.ok) throw new Error('Failed to load');
      const data = await res.json();
      setAlumni(data.alumni || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAlumni(); }, [loadAlumni]);

  const handleSort = useCallback((field: SortField) => {
    setSortBy((prev) => {
      if (prev === field) {
        setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
        return prev;
      }
      setSortOrder(field === 'name' || field === 'venture' ? 'asc' : 'desc');
      return field;
    });
  }, []);

  const activeFilterCount = useMemo(() => {
    let c = 0;
    if (filterStage !== 'all') c++;
    if (filterSector !== 'all') c++;
    if (filterActivity !== 'all') c++;
    if (filterMomentum !== 'all') c++;
    if (filterVentureType !== 'all') c++;
    return c;
  }, [filterStage, filterSector, filterActivity, filterMomentum, filterVentureType]);

  const clearAllFilters = useCallback(() => {
    setFilterStage('all');
    setFilterSector('all');
    setFilterActivity('all');
    setFilterMomentum('all');
    setFilterVentureType('all');
    setSearchTerm('');
  }, []);

  const filteredAndSorted = useMemo(() => {
    let result = alumni;
    if (filterVentureType !== 'all') result = result.filter(a => a.venture_type === filterVentureType);
    if (filterStage !== 'all') result = result.filter(a => a.venture_stage === filterStage);
    if (filterSector !== 'all') result = result.filter(a => a.sector === filterSector);
    if (filterActivity !== 'all') result = result.filter(a => a.activity_level === filterActivity);
    if (filterMomentum !== 'all') result = result.filter(a => a.momentum === filterMomentum);
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(a =>
        `${a.first_name} ${a.last_name}`.toLowerCase().includes(term) ||
        a.venture_name.toLowerCase().includes(term) ||
        a.headline.toLowerCase().includes(term) ||
        a.city.toLowerCase().includes(term) ||
        a.key_updates.some(u => u.toLowerCase().includes(term))
      );
    }
    return [...result].sort((a, b) => {
      let cmp = 0;
      switch (sortBy) {
        case 'activity_score': cmp = a.activity_score - b.activity_score; break;
        case 'name': cmp = `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`); break;
        case 'venture': cmp = a.venture_name.localeCompare(b.venture_name); break;
        case 'funding': cmp = a.total_funding - b.total_funding; break;
        case 'team_size': cmp = a.team_size - b.team_size; break;
        case 'linkedin_engagement': cmp = a.linkedin_engagement_rate - b.linkedin_engagement_rate; break;
        case 'news': cmp = a.news_mentions_90d - b.news_mentions_90d; break;
        case 'stage': cmp = (STAGE_CONFIG[a.venture_stage]?.order || 0) - (STAGE_CONFIG[b.venture_stage]?.order || 0); break;
        case 'cohort': cmp = a.cohort_year - b.cohort_year; break;
      }
      return sortOrder === 'asc' ? cmp : -cmp;
    });
  }, [alumni, filterVentureType, filterStage, filterSector, filterActivity, filterMomentum, searchTerm, sortBy, sortOrder]);

  const handleExportCSV = useCallback(() => {
    if (filteredAndSorted.length === 0) return;
    const headers = ['Name', 'Venture', 'Role', 'Sector', 'Stage', 'City', 'State', 'Cohort', 'Total Funding', 'Revenue Range', 'Team Size', 'Activity Score', 'Momentum', 'LinkedIn Followers', 'Posts (30d)', 'Engagement Rate', 'News (90d)', 'Last News', 'Key Updates', 'Risk Flags'];
    const rows = filteredAndSorted.map(a => [
      `${a.first_name} ${a.last_name}`, a.venture_name, a.venture_role,
      SECTOR_CONFIG[a.sector]?.label || a.sector, STAGE_CONFIG[a.venture_stage]?.label || a.venture_stage,
      a.city, a.state, a.cohort, a.total_funding, a.revenue_range || '', a.team_size,
      a.activity_score, a.momentum, a.linkedin_followers, a.linkedin_posts_30d,
      a.linkedin_engagement_rate, a.news_mentions_90d, a.last_news_headline || '',
      a.key_updates.join('; '), a.risk_flags.join('; '),
    ]);
    const csv = [headers.join(','), ...rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `camelback_alumni_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [filteredAndSorted]);

  function getSortIcon(field: SortField) {
    if (sortBy !== field) return <ArrowUpDown className="w-3 h-3 ml-1 opacity-40" />;
    return sortOrder === 'asc' ? <ArrowUp className="w-3 h-3 ml-1" /> : <ArrowDown className="w-3 h-3 ml-1" />;
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-background">
        <div className="max-w-7xl mx-auto p-4">
          <div className="page-header">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary"><Users className="w-4 h-4" /></div>
            <h1 className="text-lg font-semibold tracking-tight">Alumni Intelligence</h1>
          </div>
          <div className="flex items-center justify-center h-64">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              Loading alumni data...
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="max-w-[1400px] mx-auto p-4">
        {/* Header */}
        <div className="page-header">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            <Users className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Alumni Intelligence</h1>
            <p className="text-xs text-muted-foreground">Camelback Ventures | Portfolio Tracker</p>
          </div>
          {/* Tab toggle */}
          <div className="ml-auto flex items-center gap-1 rounded-lg border p-0.5 bg-muted/50">
            <button
              onClick={() => setActiveTab('detailed')}
              className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                activeTab === 'detailed' ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Table2 className="w-3.5 h-3.5" /> Detailed
            </button>
            <button
              onClick={() => setActiveTab('dashboard')}
              className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                activeTab === 'dashboard' ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <BarChart3 className="w-3.5 h-3.5" /> Dashboard
            </button>
          </div>
        </div>

        {activeTab === 'dashboard' ? (
          <DashboardView alumni={filteredAndSorted.length < alumni.length ? filteredAndSorted : alumni} />
        ) : (
          <>
            {/* Search + actions bar */}
            <div className="flex items-center gap-3 mb-2">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input type="text" placeholder="Search by name, venture, city, updates..."
                  value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-sm rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-primary/30" />
                {searchTerm && (
                  <button onClick={() => setSearchTerm('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
              <span className="text-xs text-muted-foreground ml-auto">{filteredAndSorted.length} alumni</span>
              <Button variant="outline" size="sm" onClick={handleExportCSV} className="gap-1.5">
                <Download className="w-3.5 h-3.5" /> CSV
              </Button>
            </div>

            {/* Filter bar */}
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <Filter className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              <Select value={filterVentureType} onValueChange={setFilterVentureType}>
                <SelectTrigger className="h-7 w-[120px] text-xs"><SelectValue placeholder="Type" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="for_profit">For-Profit</SelectItem>
                  <SelectItem value="nonprofit">Nonprofit</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterStage} onValueChange={setFilterStage}>
                <SelectTrigger className="h-7 w-[130px] text-xs"><SelectValue placeholder="Stage" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Stages</SelectItem>
                  <SelectGroup>
                    <SelectLabel className="text-[10px] text-teal-600">Nonprofit</SelectLabel>
                    {Object.entries(STAGE_CONFIG).filter(([, v]) => v.group === 'nonprofit').sort((a, b) => a[1].order - b[1].order).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                  </SelectGroup>
                  <SelectGroup>
                    <SelectLabel className="text-[10px] text-indigo-600">For-Profit</SelectLabel>
                    {Object.entries(STAGE_CONFIG).filter(([, v]) => v.group === 'for_profit').sort((a, b) => a[1].order - b[1].order).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                  </SelectGroup>
                  <SelectGroup>
                    <SelectLabel className="text-[10px] text-muted-foreground">Other</SelectLabel>
                    {Object.entries(STAGE_CONFIG).filter(([, v]) => v.group === 'shared').map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                  </SelectGroup>
                </SelectContent>
              </Select>
              <Select value={filterSector} onValueChange={setFilterSector}>
                <SelectTrigger className="h-7 w-[140px] text-xs"><SelectValue placeholder="Sector" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sectors</SelectItem>
                  {Object.entries(SECTOR_CONFIG).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={filterActivity} onValueChange={setFilterActivity}>
                <SelectTrigger className="h-7 w-[130px] text-xs"><SelectValue placeholder="Activity" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Activity</SelectItem>
                  {Object.entries(ACTIVITY_CONFIG).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={filterMomentum} onValueChange={setFilterMomentum}>
                <SelectTrigger className="h-7 w-[130px] text-xs"><SelectValue placeholder="Momentum" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Momentum</SelectItem>
                  <SelectItem value="rising">Rising</SelectItem>
                  <SelectItem value="stable">Stable</SelectItem>
                  <SelectItem value="declining">Declining</SelectItem>
                </SelectContent>
              </Select>
              {activeFilterCount > 0 && (
                <Button variant="ghost" size="sm" onClick={clearAllFilters} className="text-xs gap-1 h-7 px-2">
                  <X className="w-3 h-3" /> Clear all ({activeFilterCount})
                </Button>
              )}
            </div>

            {/* Table */}
            <Card>
              <ScrollArea className="h-[calc(100vh-260px)] min-h-[400px]">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 sticky top-0 z-10">
                    <tr className="border-b">
                      <th className="text-left p-2 w-[30px]"><span className="font-medium text-xs uppercase tracking-wide text-muted-foreground">#</span></th>
                      {([
                        ['activity_score', 'Activity', 'w-[100px]'],
                        ['stage', 'Stage', 'w-[100px]'],
                        ['name', 'Founder', 'min-w-[140px]'],
                        ['venture', 'Venture', 'min-w-[140px]'],
                        ['funding', 'Funding / Grants', 'w-[110px]'],
                        ['team_size', 'Team', 'w-[60px]'],
                        ['linkedin_engagement', 'LinkedIn', 'w-[90px]'],
                        ['news', 'News', 'w-[60px]'],
                        ['cohort', 'Cohort', 'w-[80px]'],
                      ] as [SortField, string, string][]).map(([field, label, width]) => (
                        <th key={field} className={cn('text-left p-2', width)}>
                          <button onClick={() => handleSort(field)}
                            className={cn('flex items-center font-medium text-xs uppercase tracking-wide transition-colors',
                              sortBy === field ? 'text-foreground' : 'text-muted-foreground hover:text-foreground')}>
                            {label}{getSortIcon(field)}
                          </button>
                        </th>
                      ))}
                      <th className="text-left p-2 min-w-[180px]">
                        <span className="font-medium text-xs uppercase tracking-wide text-muted-foreground">Updates & Momentum</span>
                      </th>
                      <th className="w-8 p-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAndSorted.map((a, index) => {
                      const isExpanded = expandedId === a.id;
                      const stageConf = STAGE_CONFIG[a.venture_stage];
                      const sectorConf = SECTOR_CONFIG[a.sector];
                      const actConf = ACTIVITY_CONFIG[a.activity_level];

                      return (
                        <tr key={a.id} className="border-b hover:bg-muted/30 transition-colors">
                          <td className="p-2 text-xs text-muted-foreground font-mono tabular-nums">{index + 1}</td>
                          <td className="p-2"><ScoreBar score={a.activity_score} /></td>
                          <td className="p-2">
                            <Badge variant="outline" className={cn('text-[10px] px-1.5 py-0 font-medium', stageConf.bg, stageConf.color)}>
                              {stageConf.label}
                            </Badge>
                          </td>
                          <td className="p-2">
                            <button
                              className="font-medium text-left hover:text-primary hover:underline underline-offset-2 transition-colors"
                              onClick={() => { setSelectedAlumniId(a.id); setSheetOpen(true); }}>
                              {a.first_name} {a.last_name}
                            </button>
                            <div className="text-xs text-muted-foreground truncate max-w-[180px]">{a.headline}</div>
                          </td>
                          <td className="p-2">
                            <div className="font-medium">{a.venture_name}</div>
                            <div className="flex items-center gap-1 mt-0.5">
                              <Badge variant="outline" className={cn('text-[9px] px-1 py-0', sectorConf.color)}>
                                {sectorConf.label}
                              </Badge>
                              <VentureTypeBadge type={a.venture_type} />
                            </div>
                          </td>
                          <td className="p-2">
                            <div className="font-medium tabular-nums">{formatCurrency(a.total_funding, a.venture_type === 'nonprofit')}</div>
                            {a.venture_type === 'nonprofit' ? (
                              <div className="text-[10px] text-teal-600">{a.last_funding_type || 'Grants'}</div>
                            ) : (
                              a.revenue_range && <div className="text-[10px] text-muted-foreground">{a.revenue_range}</div>
                            )}
                          </td>
                          <td className="p-2 text-center font-mono tabular-nums">{a.team_size || '-'}</td>
                          <td className="p-2">
                            <div className="text-xs">
                              <span className="font-medium">{a.linkedin_posts_30d}</span>
                              <span className="text-muted-foreground"> posts</span>
                            </div>
                            <div className="text-[10px] text-muted-foreground">
                              {a.linkedin_engagement_rate}% eng
                            </div>
                          </td>
                          <td className="p-2 text-center">
                            {a.news_mentions_90d > 0 ? (
                              <span className="font-medium">{a.news_mentions_90d}</span>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </td>
                          <td className="p-2 text-xs text-muted-foreground">{a.cohort}</td>
                          <td className="p-2">
                            <div className="flex items-center gap-1.5 mb-1">
                              <MomentumBadge momentum={a.momentum} />
                              {a.risk_flags.length > 0 && (
                                <AlertTriangle className="w-3 h-3 text-amber-500" />
                              )}
                            </div>
                            <div className="text-xs text-muted-foreground line-clamp-2">
                              {a.key_updates[0] || '-'}
                            </div>
                            {isExpanded && (
                              <div className="mt-2 space-y-2 text-xs border-t pt-2">
                                {a.key_updates.length > 1 && (
                                  <div>
                                    <span className="text-muted-foreground font-medium">All updates:</span>
                                    <ul className="mt-1 space-y-0.5">
                                      {a.key_updates.map((u, i) => (
                                        <li key={i} className="flex items-start gap-1.5">
                                          <span className="mt-1 w-1 h-1 rounded-full bg-primary shrink-0" />
                                          {u}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {a.last_news_headline && (
                                  <div>
                                    <span className="text-muted-foreground font-medium">Latest news:</span>{' '}
                                    <span>{a.last_news_headline}</span>
                                    {a.last_news_date && <span className="text-muted-foreground"> ({formatShortDate(a.last_news_date)})</span>}
                                  </div>
                                )}
                                {a.risk_flags.length > 0 && (
                                  <div>
                                    <span className="text-red-600 font-medium">Risks:</span>{' '}
                                    <span className="text-red-600 dark:text-red-400">{a.risk_flags.join('; ')}</span>
                                  </div>
                                )}
                                {a.venture_type === 'nonprofit' && a.impact_metric && (
                                  <div>
                                    <span className="text-teal-600 font-medium">Impact:</span>{' '}
                                    <span className="text-teal-700 dark:text-teal-400">{a.impact_metric}</span>
                                  </div>
                                )}
                                <div className="grid grid-cols-2 gap-2">
                                  <div><span className="text-muted-foreground">Location:</span> {a.city}, {a.state}</div>
                                  <div><span className="text-muted-foreground">Followers:</span> {a.linkedin_followers.toLocaleString()}</div>
                                  <div><span className="text-muted-foreground">Last touchpoint:</span> {a.last_camelback_touchpoint ? formatShortDate(a.last_camelback_touchpoint) : 'None'}</div>
                                  <div><span className="text-muted-foreground">Engagement score:</span> {a.camelback_engagement_score}</div>
                                  {a.venture_type === 'nonprofit' && a.people_served && (
                                    <div><span className="text-muted-foreground">People served:</span> {a.people_served.toLocaleString()}</div>
                                  )}
                                  {a.venture_type === 'nonprofit' && a.revenue_range && (
                                    <div><span className="text-muted-foreground">Annual budget:</span> {a.revenue_range}</div>
                                  )}
                                </div>
                              </div>
                            )}
                          </td>
                          <td className="p-2">
                            <button onClick={() => setExpandedId(isExpanded ? null : a.id)}
                              className="p-1 rounded hover:bg-muted transition-colors">
                              {isExpanded ? <ChevronDown className="w-4 h-4 text-muted-foreground" /> : <ChevronRight className="w-4 h-4 text-muted-foreground" />}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </ScrollArea>
            </Card>
          </>
        )}
      </div>

      <AlumniDetailSheet alumniId={selectedAlumniId} open={sheetOpen} onOpenChange={setSheetOpen} />
    </main>
  );
}
