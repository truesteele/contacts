'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import { Textarea } from '@/components/ui/textarea';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  ArrowLeft,
  ArrowUpDown,
  BarChart3,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Edit3,
  Lightbulb,
  Loader2,
  Mail,
  MessageSquare,
  Mic,
  Pencil,
  Quote,
  Radio,
  Search,
  Send,
  StickyNote,
  User,
  ExternalLink,
  X,
  Zap,
} from 'lucide-react';

// ── Constants ─────────────────────────────────────────────────────────

const PIPELINE_STAGES = [
  { key: 'draft', label: 'Draft' },
  { key: 'approved', label: 'Approved' },
  { key: 'sent', label: 'Sent' },
  { key: 'replied', label: 'Replied' },
  { key: 'booked', label: 'Booked' },
];

const PIPELINE_COLORS = ['bg-blue-200', 'bg-green-200', 'bg-purple-200', 'bg-emerald-200', 'bg-amber-200'];

// ── Types ──────────────────────────────────────────────────────────────

interface TopicPillar {
  name: string;
  description: string;
  talking_points: string[];
  keywords: string[];
}

interface WritingSample {
  text: string;
  source: string;
}

interface PastAppearance {
  podcast_name: string;
  episode_title: string;
  date: string;
  url: string | null;
  notes: string;
}

interface SpeakerProfile {
  id: number;
  name: string;
  slug: string;
  bio: string;
  headline: string;
  website_url: string | null;
  linkedin_url: string | null;
  topic_pillars: TopicPillar[];
  writing_samples: WritingSample[];
  past_appearances: PastAppearance[];
}

interface CompositeSignals {
  gpt_fit_score: number;
  embedding_similarity: number;
  similar_speaker_boost: number;
  activity_recency: number;
  episode_count_signal: number;
}

interface TopicMatch {
  composite_score?: number;
  signals?: CompositeSignals;
  matching_pillars?: string[];
  discovery_methods?: string[];
}

interface PodcastPitch {
  fit_tier: string | null;
  fit_score: number | null;
  fit_rationale: string | null;
  topic_match: TopicMatch | string[] | null;
  pitch_status: string;
  subject_line: string | null;
  pitch_body: string | null;
}

interface Podcast {
  id: number;
  title: string;
  author: string | null;
  description: string | null;
  rss_url: string | null;
  website_url: string | null;
  host_email: string | null;
  host_name: string | null;
  activity_status: string | null;
  episode_count: number | null;
  last_episode_date: string | null;
  categories: string[] | null;
  email_verified: boolean | null;
  discovery_methods: string[] | null;
  pitch: PodcastPitch | null;
}

const FIT_TIER_STYLES: Record<string, string> = {
  strong: 'bg-green-100 text-green-800 border-green-200',
  moderate: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  weak: 'bg-red-100 text-red-800 border-red-200',
  unscored: 'bg-gray-100 text-gray-600 border-gray-200',
};

const ACTIVITY_STYLES: Record<string, string> = {
  active: 'bg-green-100 text-green-800 border-green-200',
  slow: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  podfaded: 'bg-red-100 text-red-800 border-red-200',
  unknown: 'bg-gray-100 text-gray-600 border-gray-200',
};

const DISCOVERY_METHOD_STYLES: Record<string, { label: string; className: string }> = {
  keyword_search: { label: 'Keyword', className: 'border-blue-300 text-blue-700 bg-blue-50' },
  similar_speaker: { label: 'Similar Speaker', className: 'border-purple-300 text-purple-700 bg-purple-50' },
  expanded_keywords: { label: 'Expanded', className: 'border-orange-300 text-orange-700 bg-orange-50' },
  embedding_match: { label: 'Embedding', className: 'border-cyan-300 text-cyan-700 bg-cyan-50' },
};

const PITCH_STATUS_STYLES: Record<string, string> = {
  draft: 'bg-blue-100 text-blue-800 border-blue-200',
  approved: 'bg-green-100 text-green-800 border-green-200',
  rejected: 'bg-red-100 text-red-800 border-red-200',
  sent: 'bg-purple-100 text-purple-800 border-purple-200',
  drafted: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  replied: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  booked: 'bg-amber-100 text-amber-800 border-amber-200',
  unscored: 'bg-gray-100 text-gray-600 border-gray-200',
};

const OUTCOME_STYLES: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-800 border-gray-200',
  booked: 'bg-green-100 text-green-800 border-green-200',
  declined: 'bg-red-100 text-red-800 border-red-200',
  no_response: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  maybe_later: 'bg-blue-100 text-blue-800 border-blue-200',
};

interface CampaignWithDetails {
  id: number;
  pitch_id: number;
  speaker_profile_id: number;
  sent_from_email: string | null;
  sent_to_email: string | null;
  sent_at: string | null;
  send_method: string | null;
  outcome: string | null;
  notes: string | null;
  opened_at: string | null;
  replied_at: string | null;
  recording_date: string | null;
  episode_air_date: string | null;
  episode_url: string | null;
  pitch: {
    id: number;
    subject_line: string | null;
    pitch_status: string;
    fit_tier: string | null;
  } | null;
  podcast: {
    id: number;
    title: string;
    author: string | null;
    host_name: string | null;
    host_email: string | null;
  } | null;
  speaker: {
    id: number;
    name: string;
    slug: string;
  } | null;
}

interface CampaignStats {
  total_sent: number;
  pipeline: Record<string, number>;
  outcomes: Record<string, number>;
}

interface PitchWithDetails {
  id: number;
  podcast_target_id: number;
  speaker_profile_id: number;
  fit_tier: string | null;
  fit_score: number | null;
  fit_rationale: string | null;
  topic_match: string[] | null;
  episode_hooks: any[] | null;
  subject_line: string | null;
  subject_line_alt: string | null;
  pitch_body: string | null;
  episode_reference: string | null;
  suggested_topics: any[] | null;
  pitch_status: string;
  generated_at: string | null;
  podcast: {
    id: number;
    title: string;
    author: string | null;
    host_name: string | null;
    host_email: string | null;
    email_verified: boolean | null;
    activity_status: string | null;
    website_url: string | null;
  } | null;
  speaker: {
    id: number;
    name: string;
    slug: string;
  } | null;
}

type SortField = 'fit_score' | 'episode_count' | 'last_episode_date';
type SortDir = 'asc' | 'desc';

// ── Speaker Profile Card ───────────────────────────────────────────────

function SpeakerCard({ profile }: { profile: SpeakerProfile }) {
  const [expandedPillars, setExpandedPillars] = useState<Set<number>>(new Set());
  const [showSamples, setShowSamples] = useState(false);

  const togglePillar = (idx: number) => {
    setExpandedPillars(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="flex items-start gap-4">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-muted">
            <User className="h-7 w-7 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <CardTitle className="text-xl">{profile.name}</CardTitle>
            <CardDescription className="mt-1 line-clamp-2">
              {profile.headline}
            </CardDescription>
            <div className="mt-2 flex flex-wrap gap-2">
              {profile.linkedin_url && (
                <a
                  href={profile.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                >
                  LinkedIn <ExternalLink className="h-3 w-3" />
                </a>
              )}
              {profile.website_url && (
                <a
                  href={profile.website_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                >
                  Website <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-5">
        {/* Bio */}
        <p className="text-sm text-muted-foreground leading-relaxed">{profile.bio}</p>

        {/* Topic Pillars */}
        <div>
          <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <Mic className="h-4 w-4" /> Topic Pillars ({profile.topic_pillars.length})
          </h4>
          <div className="space-y-1">
            {profile.topic_pillars.map((pillar, idx) => (
              <div key={idx} className="rounded-md border">
                <button
                  onClick={() => togglePillar(idx)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium hover:bg-muted/50"
                >
                  {expandedPillars.has(idx) ? (
                    <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="flex-1">{pillar.name}</span>
                </button>
                {expandedPillars.has(idx) && (
                  <div className="border-t px-3 py-2">
                    <p className="mb-2 text-xs text-muted-foreground">{pillar.description}</p>
                    <ul className="space-y-1">
                      {pillar.talking_points.map((point, pIdx) => (
                        <li key={pIdx} className="flex items-start gap-2 text-xs">
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-foreground" />
                          {point}
                        </li>
                      ))}
                    </ul>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {pillar.keywords.map((kw, kIdx) => (
                        <Badge key={kIdx} variant="secondary" className="text-[10px]">
                          {kw}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Past Appearances */}
        {profile.past_appearances.length > 0 && (
          <div>
            <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <Radio className="h-4 w-4" /> Past Appearances
            </h4>
            <div className="space-y-1">
              {profile.past_appearances.map((app, idx) => (
                <div key={idx} className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                  <span className="font-medium">{app.podcast_name}</span>
                  {app.date && (
                    <Badge variant="outline" className="text-[10px]">
                      {app.date}
                    </Badge>
                  )}
                  {app.notes && (
                    <span className="text-xs text-muted-foreground">{app.notes}</span>
                  )}
                  {app.url && (
                    <a
                      href={app.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-auto"
                    >
                      <ExternalLink className="h-3 w-3 text-blue-600" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Writing Samples */}
        <div>
          <button
            onClick={() => setShowSamples(!showSamples)}
            className="mb-2 flex items-center gap-2 text-sm font-semibold hover:text-foreground/80"
          >
            {showSamples ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <Quote className="h-4 w-4" /> Writing Samples ({profile.writing_samples.length})
          </button>
          {showSamples && (
            <div className="space-y-3">
              {profile.writing_samples.map((sample, idx) => (
                <div key={idx} className="rounded-md border bg-muted/30 px-3 py-2">
                  <p className="text-xs leading-relaxed">{sample.text}</p>
                  <p className="mt-1 text-[10px] font-medium text-muted-foreground">
                    {sample.source}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Signal Bar ────────────────────────────────────────────────────────

function SignalBar({ label, value, weight, color }: { label: string; value: number; weight: string; color: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[10px]">
        <span className="font-medium">{label} <span className="text-muted-foreground">({weight})</span></span>
        <span className="font-mono">{value.toFixed(2)}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Discovery Tab ─────────────────────────────────────────────────────

function DiscoveryTab() {
  const [podcasts, setPodcasts] = useState<Podcast[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [speaker, setSpeaker] = useState('sally');
  const [fitTierFilter, setFitTierFilter] = useState('all');
  const [activityFilter, setActivityFilter] = useState('all');
  const [discoveryMethodFilter, setDiscoveryMethodFilter] = useState('all');

  // Expanded row for signal breakdown
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  // Sorting
  const [sortField, setSortField] = useState<SortField>('fit_score');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 25;

  // Selection
  const [selected, setSelected] = useState<Set<number>>(new Set());

  // Scoring state
  const [scoring, setScoring] = useState(false);
  const [scoreMsg, setScoreMsg] = useState<string | null>(null);

  const fetchPodcasts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('limit', String(limit));
      if (speaker) params.set('speaker', speaker);
      if (search) params.set('search', search);
      if (activityFilter !== 'all') params.set('status', activityFilter);
      if (fitTierFilter !== 'all') params.set('fit_tier', fitTierFilter);
      if (discoveryMethodFilter !== 'all') params.set('discovery_method', discoveryMethodFilter);

      const res = await fetch(`/api/podcast/discover?${params}`);
      if (!res.ok) throw new Error('Failed to fetch podcasts');
      const data = await res.json();
      setPodcasts(data.podcasts || []);
      setTotal(data.total ?? 0);
      setTotalPages(data.total_pages ?? 1);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load podcasts');
    } finally {
      setLoading(false);
    }
  }, [page, speaker, search, activityFilter, fitTierFilter, discoveryMethodFilter]);

  useEffect(() => {
    fetchPodcasts();
  }, [fetchPodcasts]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
    setSelected(new Set());
  }, [search, speaker, fitTierFilter, activityFilter, discoveryMethodFilter]);

  // Client-side sort
  const sorted = useMemo(() => {
    const list = [...podcasts];
    list.sort((a, b) => {
      let aVal: number;
      let bVal: number;
      if (sortField === 'fit_score') {
        aVal = a.pitch?.fit_score ?? -1;
        bVal = b.pitch?.fit_score ?? -1;
      } else if (sortField === 'episode_count') {
        aVal = a.episode_count ?? 0;
        bVal = b.episode_count ?? 0;
      } else {
        aVal = a.last_episode_date ? new Date(a.last_episode_date).getTime() : 0;
        bVal = b.last_episode_date ? new Date(b.last_episode_date).getTime() : 0;
      }
      return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
    });
    return list;
  }, [podcasts, sortField, sortDir]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(d => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === sorted.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(sorted.map(p => p.id)));
    }
  };

  const handleScore = async () => {
    if (selected.size === 0) return;
    setScoring(true);
    setScoreMsg(null);
    try {
      const res = await fetch('/api/podcast/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          podcast_ids: Array.from(selected),
          speaker_slug: speaker,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Scoring failed');
      setScoreMsg(data.message);
      setSelected(new Set());
      fetchPodcasts();
    } catch (err: unknown) {
      setScoreMsg(err instanceof Error ? err.message : 'Scoring failed');
    } finally {
      setScoring(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // setPage(1) triggers useCallback/useEffect chain to refetch
    setPage(1);
  };

  const formatDate = (d: string | null) => {
    if (!d) return '-';
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="space-y-4">
      {/* Controls row */}
      <div className="flex flex-wrap items-end gap-3">
        {/* Search */}
        <form onSubmit={handleSearch} className="flex flex-1 items-center gap-2" style={{ minWidth: 200 }}>
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search podcasts..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Button type="submit" size="sm" variant="outline">Search</Button>
        </form>

        {/* Speaker */}
        <Select value={speaker} onValueChange={setSpeaker}>
          <SelectTrigger className="w-[130px]">
            <SelectValue placeholder="Speaker" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="sally">Sally</SelectItem>
            <SelectItem value="justin">Justin</SelectItem>
          </SelectContent>
        </Select>

        {/* Fit tier filter */}
        <Select value={fitTierFilter} onValueChange={setFitTierFilter}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Fit tier" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All tiers</SelectItem>
            <SelectItem value="strong">Strong</SelectItem>
            <SelectItem value="moderate">Moderate</SelectItem>
            <SelectItem value="weak">Weak</SelectItem>
          </SelectContent>
        </Select>

        {/* Activity filter */}
        <Select value={activityFilter} onValueChange={setActivityFilter}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Activity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All activity</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="slow">Slow</SelectItem>
            <SelectItem value="podfaded">Podfaded</SelectItem>
          </SelectContent>
        </Select>

        {/* Discovery method filter */}
        <Select value={discoveryMethodFilter} onValueChange={setDiscoveryMethodFilter}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Found via" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All methods</SelectItem>
            <SelectItem value="keyword_search">Keyword</SelectItem>
            <SelectItem value="expanded_keywords">Expanded</SelectItem>
            <SelectItem value="similar_speaker">Similar Speaker</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3 rounded-md border bg-muted/50 px-4 py-2">
          <span className="text-sm font-medium">{selected.size} selected</span>
          <Button
            size="sm"
            onClick={handleScore}
            disabled={scoring}
          >
            {scoring ? (
              <>
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                Preparing...
              </>
            ) : (
              <>
                <Zap className="mr-1 h-3 w-3" />
                Prepare Selected
              </>
            )}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>
            Clear
          </Button>
        </div>
      )}

      {/* Score feedback */}
      {scoreMsg && (
        <div className="rounded-md border bg-blue-50 px-4 py-2 text-sm text-blue-800">
          {scoreMsg}
          <button onClick={() => setScoreMsg(null)} className="ml-2 font-medium underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Results table */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading podcasts...</span>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={fetchPodcasts}>
            Retry
          </Button>
        </div>
      ) : sorted.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Radio className="mb-4 h-12 w-12 text-muted-foreground/40" />
          <h3 className="text-lg font-semibold">No Podcasts Found</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Run the discovery script to find podcasts, or adjust your filters.
          </p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="w-10 px-3 py-2">
                    <Checkbox
                      checked={selected.size === sorted.length && sorted.length > 0}
                      onCheckedChange={toggleSelectAll}
                    />
                  </th>
                  <th className="px-3 py-2 text-left font-medium">Podcast</th>
                  <th className="px-3 py-2 text-left font-medium">Host</th>
                  <th className="w-20 px-3 py-2 text-left font-medium">
                    <button onClick={() => toggleSort('episode_count')} className="inline-flex items-center gap-1 hover:text-foreground">
                      Episodes
                      <ArrowUpDown className="h-3 w-3" />
                    </button>
                  </th>
                  <th className="w-28 px-3 py-2 text-left font-medium">
                    <button onClick={() => toggleSort('last_episode_date')} className="inline-flex items-center gap-1 hover:text-foreground">
                      Last Ep.
                      <ArrowUpDown className="h-3 w-3" />
                    </button>
                  </th>
                  <th className="w-24 px-3 py-2 text-left font-medium">Activity</th>
                  <th className="px-3 py-2 text-left font-medium">Found via</th>
                  <th className="w-24 px-3 py-2 text-left font-medium">
                    <button onClick={() => toggleSort('fit_score')} className="inline-flex items-center gap-1 hover:text-foreground">
                      Fit
                      <ArrowUpDown className="h-3 w-3" />
                    </button>
                  </th>
                  <th className="w-16 px-3 py-2 text-left font-medium">Score</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map(podcast => {
                  const tier = podcast.pitch?.fit_tier || 'unscored';
                  const activity = podcast.activity_status || 'unknown';
                  const methods = podcast.discovery_methods || [];
                  const topicMatch = podcast.pitch?.topic_match;
                  const signals = topicMatch && !Array.isArray(topicMatch) ? topicMatch.signals : null;
                  const compositeScore = topicMatch && !Array.isArray(topicMatch) ? topicMatch.composite_score : null;
                  const isExpanded = expandedRow === podcast.id;
                  return (
                    <React.Fragment key={podcast.id}>
                    <tr
                      className={cn(
                        'border-b hover:bg-muted/30 transition-colors cursor-pointer',
                        selected.has(podcast.id) && 'bg-blue-50/50',
                        isExpanded && 'bg-muted/20'
                      )}
                      onClick={() => setExpandedRow(isExpanded ? null : podcast.id)}
                    >
                      <td className="px-3 py-2" onClick={e => e.stopPropagation()}>
                        <Checkbox
                          checked={selected.has(podcast.id)}
                          onCheckedChange={() => toggleSelect(podcast.id)}
                        />
                      </td>
                      <td className="max-w-[250px] px-3 py-2">
                        <div className="font-medium truncate">{podcast.title}</div>
                        {podcast.author && (
                          <div className="text-xs text-muted-foreground truncate">{podcast.author}</div>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <div className="truncate max-w-[150px]">
                          {podcast.host_name || '-'}
                        </div>
                        {podcast.host_email && (
                          <div className="text-xs text-muted-foreground truncate max-w-[150px]">
                            {podcast.host_email}
                            {podcast.email_verified && (
                              <Badge variant="outline" className="ml-1 text-[9px] px-1 py-0 border-green-300 text-green-700">
                                verified
                              </Badge>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {podcast.episode_count ?? '-'}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {formatDate(podcast.last_episode_date)}
                      </td>
                      <td className="px-3 py-2">
                        <Badge variant="outline" className={cn('text-[10px] capitalize', ACTIVITY_STYLES[activity])}>
                          {activity}
                        </Badge>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {methods.length > 0 ? methods.map(m => {
                            const style = DISCOVERY_METHOD_STYLES[m];
                            return style ? (
                              <Badge key={m} variant="outline" className={cn('text-[9px] px-1.5 py-0', style.className)}>
                                {style.label}
                              </Badge>
                            ) : null;
                          }) : (
                            <span className="text-xs text-muted-foreground">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <Badge variant="outline" className={cn('text-[10px] capitalize', FIT_TIER_STYLES[tier])}>
                          {tier}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-center font-mono text-xs">
                        {compositeScore != null ? compositeScore.toFixed(2) : (podcast.pitch?.fit_score != null ? podcast.pitch.fit_score : '-')}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="border-b bg-muted/10">
                        <td colSpan={9} className="px-6 py-3">
                          {signals ? (
                            <div className="space-y-2">
                              <div className="flex items-center gap-3">
                                <span className="text-sm font-semibold">
                                  Composite: {compositeScore?.toFixed(2)}
                                </span>
                                <Badge variant="outline" className={cn('text-[10px] capitalize', FIT_TIER_STYLES[tier])}>
                                  {tier}
                                </Badge>
                              </div>
                              <div className="grid grid-cols-5 gap-3">
                                <SignalBar label="GPT Fit" value={signals.gpt_fit_score} weight="41%" color="bg-blue-500" />
                                <SignalBar label="Embedding" value={signals.embedding_similarity} weight="35%" color="bg-cyan-500" />
                                <SignalBar label="Speaker" value={signals.similar_speaker_boost} weight="bonus" color="bg-purple-500" />
                                <SignalBar label="Recency" value={signals.activity_recency} weight="12%" color="bg-green-500" />
                                <SignalBar label="Episodes" value={signals.episode_count_signal} weight="12%" color="bg-orange-500" />
                              </div>
                              {topicMatch && !Array.isArray(topicMatch) && topicMatch.matching_pillars && topicMatch.matching_pillars.length > 0 && (
                                <div className="text-xs text-muted-foreground">
                                  <span className="font-medium">Matching pillars:</span>{' '}
                                  {topicMatch.matching_pillars.join(', ')}
                                </div>
                              )}
                            </div>
                          ) : (
                            <div className="text-xs text-muted-foreground">
                              {podcast.pitch?.fit_rationale || 'No composite scoring data available. Score this podcast to see signal breakdown.'}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              Showing {(page - 1) * limit + 1}-{Math.min(page * limit, total)} of {total}
            </span>
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="px-3 text-sm">
                {page} / {totalPages}
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Pitch Card ────────────────────────────────────────────────────────

function PitchCard({
  pitch,
  onUpdate,
}: {
  pitch: PitchWithDetails;
  onUpdate: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editSubject, setEditSubject] = useState(pitch.subject_line || '');
  const [editBody, setEditBody] = useState(pitch.pitch_body || '');
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const tier = pitch.fit_tier || 'unscored';
  const status = pitch.pitch_status || 'unscored';
  const hasPitch = !!pitch.pitch_body;

  const handleSaveEdit = async () => {
    setSaving(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/podcast/pitches', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pitch_id: pitch.id,
          subject_line: editSubject,
          pitch_body: editBody,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Save failed');
      }
      setEditing(false);
      setFeedback('Saved');
      onUpdate();
    } catch (err: unknown) {
      setFeedback(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    setSaving(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/podcast/pitches', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pitch_id: pitch.id,
          pitch_status: newStatus,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Update failed');
      }
      setFeedback(newStatus === 'approved' ? 'Approved' : 'Rejected');
      onUpdate();
    } catch (err: unknown) {
      setFeedback(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/podcast/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pitch_ids: [pitch.id] }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Generation failed');
      const result = data.results?.[0];
      if (result?.status === 'failed') throw new Error(result.error || 'Generation failed');
      setFeedback('Pitch generated');
      onUpdate();
    } catch (err: unknown) {
      setFeedback(err instanceof Error ? err.message : 'Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleSend = async (method: string) => {
    setSending(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/podcast/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pitch_id: pitch.id, method }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Send failed');
      setFeedback(method === 'gmail_draft' ? 'Draft created' : method === 'manual' ? 'Marked as sent' : 'Sent');
      onUpdate();
    } catch (err: unknown) {
      setFeedback(err instanceof Error ? err.message : 'Send failed');
    } finally {
      setSending(false);
    }
  };

  const topics = Array.isArray(pitch.suggested_topics)
    ? pitch.suggested_topics.map((t: any) => (typeof t === 'string' ? t : t.title || t.topic || String(t)))
    : [];

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <CardTitle className="text-base truncate">
              {pitch.podcast?.title || 'Unknown Podcast'}
            </CardTitle>
            {pitch.podcast?.author && (
              <CardDescription className="text-xs mt-0.5 truncate">
                {pitch.podcast.author}
                {pitch.podcast.host_name && pitch.podcast.host_name !== pitch.podcast.author
                  ? ` / Host: ${pitch.podcast.host_name}`
                  : ''}
              </CardDescription>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <Badge variant="outline" className={cn('text-[10px] capitalize', FIT_TIER_STYLES[tier])}>
              {tier}
            </Badge>
            {pitch.fit_score != null && (
              <span className="text-xs font-mono text-muted-foreground">{pitch.fit_score.toFixed(1)}</span>
            )}
            <Badge variant="outline" className={cn('text-[10px] capitalize', PITCH_STATUS_STYLES[status])}>
              {status}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 pt-0">
        {/* Subject line */}
        {hasPitch && !editing && (
          <div className="flex items-center gap-2">
            <Mail className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span className="text-sm font-medium truncate flex-1">
              {pitch.subject_line}
            </span>
            <button
              onClick={() => {
                setEditSubject(pitch.subject_line || '');
                setEditBody(pitch.pitch_body || '');
                setEditing(true);
                setExpanded(true);
              }}
              className="shrink-0 text-muted-foreground hover:text-foreground"
              title="Edit pitch"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* Body preview / expanded */}
        {hasPitch && !editing && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full text-left"
          >
            <p className={cn(
              'text-xs text-muted-foreground leading-relaxed',
              !expanded && 'line-clamp-3'
            )}>
              {pitch.pitch_body}
            </p>
            <span className="text-[10px] text-blue-600 mt-1 inline-block">
              {expanded ? 'Show less' : 'Show more'}
            </span>
          </button>
        )}

        {/* Edit mode */}
        {editing && (
          <div className="space-y-2">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Subject Line</label>
              <Input
                value={editSubject}
                onChange={e => setEditSubject(e.target.value)}
                className="mt-1 text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Pitch Body</label>
              <Textarea
                value={editBody}
                onChange={e => setEditBody(e.target.value)}
                rows={8}
                className="mt-1 text-xs leading-relaxed"
              />
              <div className="mt-1 text-[10px] text-muted-foreground">
                {editBody.split(/\s+/).filter(Boolean).length} words
              </div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={handleSaveEdit} disabled={saving}>
                {saving ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <Check className="mr-1 h-3 w-3" />}
                Save
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditing(false)}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Episode reference */}
        {expanded && pitch.episode_reference && (
          <div className="rounded-md border bg-muted/30 px-3 py-2">
            <div className="flex items-center gap-1.5 text-[10px] font-medium text-muted-foreground mb-1">
              <Edit3 className="h-3 w-3" /> Episode Reference
            </div>
            <p className="text-xs">{pitch.episode_reference}</p>
          </div>
        )}

        {/* Suggested topics */}
        {expanded && topics.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 text-[10px] font-medium text-muted-foreground mb-1.5">
              <Lightbulb className="h-3 w-3" /> Suggested Topics
            </div>
            <div className="flex flex-wrap gap-1">
              {topics.map((t: string, i: number) => (
                <Badge key={i} variant="secondary" className="text-[10px]">
                  {t}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* No pitch content */}
        {!hasPitch && (
          <div className="py-3 text-center">
            <p className="text-xs text-muted-foreground mb-2">No pitch generated yet</p>
            <Button
              size="sm"
              variant="outline"
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating ? (
                <><Loader2 className="mr-1 h-3 w-3 animate-spin" /> Generating...</>
              ) : (
                <><Zap className="mr-1 h-3 w-3" /> Generate Pitch</>
              )}
            </Button>
          </div>
        )}

        {/* Action buttons */}
        {hasPitch && !editing && (
          <div className="flex items-center gap-2 pt-1 border-t">
            {status !== 'approved' && status !== 'sent' && status !== 'booked' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleStatusChange('approved')}
                disabled={saving}
                className="text-green-700 border-green-200 hover:bg-green-50"
              >
                <Check className="mr-1 h-3 w-3" /> Approve
              </Button>
            )}
            {status !== 'rejected' && status !== 'sent' && status !== 'booked' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleStatusChange('rejected')}
                disabled={saving}
                className="text-red-700 border-red-200 hover:bg-red-50"
              >
                <X className="mr-1 h-3 w-3" /> Reject
              </Button>
            )}
            {status !== 'sent' && status !== 'booked' && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleGenerate}
                disabled={generating}
              >
                {generating ? (
                  <><Loader2 className="mr-1 h-3 w-3 animate-spin" /> Regenerating...</>
                ) : (
                  <><Zap className="mr-1 h-3 w-3" /> Regenerate</>
                )}
              </Button>
            )}
            {(status === 'draft' || status === 'approved') && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="sm" disabled={sending}>
                    {sending ? (
                      <><Loader2 className="mr-1 h-3 w-3 animate-spin" /> Sending...</>
                    ) : (
                      <><Send className="mr-1 h-3 w-3" /> Send</>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => handleSend('gmail_draft')}>
                    Gmail Draft
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleSend('direct_send')}>
                    Direct Send
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleSend('manual')}>
                    Manual (copy/paste)
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        )}

        {/* Feedback message */}
        {feedback && (
          <div className="rounded-md bg-blue-50 px-3 py-1.5 text-xs text-blue-800">
            {feedback}
            <button onClick={() => setFeedback(null)} className="ml-2 font-medium underline">
              Dismiss
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Pitch Review Tab ──────────────────────────────────────────────────

function PitchReviewTab() {
  const [pitches, setPitches] = useState<PitchWithDetails[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [speaker, setSpeaker] = useState('sally');
  const [statusFilter, setStatusFilter] = useState('all');
  const [fitTierFilter, setFitTierFilter] = useState('all');
  const [search, setSearch] = useState('');

  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 20;

  const fetchPitches = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('limit', String(limit));
      if (speaker) params.set('speaker', speaker);
      if (statusFilter !== 'all') params.set('pitch_status', statusFilter);
      if (fitTierFilter !== 'all') params.set('fit_tier', fitTierFilter);
      if (search) params.set('search', search);

      const res = await fetch(`/api/podcast/pitches?${params}`);
      if (!res.ok) throw new Error('Failed to fetch pitches');
      const data = await res.json();
      setPitches(data.pitches || []);
      setTotal(data.total ?? 0);
      setTotalPages(data.total_pages ?? 1);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load pitches');
    } finally {
      setLoading(false);
    }
  }, [page, speaker, statusFilter, fitTierFilter, search]);

  useEffect(() => {
    fetchPitches();
  }, [fetchPitches]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [speaker, statusFilter, fitTierFilter, search]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-end gap-3">
        <form onSubmit={handleSearch} className="flex flex-1 items-center gap-2" style={{ minWidth: 200 }}>
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search pitches..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Button type="submit" size="sm" variant="outline">Search</Button>
        </form>

        <Select value={speaker} onValueChange={setSpeaker}>
          <SelectTrigger className="w-[130px]">
            <SelectValue placeholder="Speaker" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="sally">Sally</SelectItem>
            <SelectItem value="justin">Justin</SelectItem>
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
            <SelectItem value="sent">Sent</SelectItem>
            <SelectItem value="replied">Replied</SelectItem>
            <SelectItem value="booked">Booked</SelectItem>
          </SelectContent>
        </Select>

        <Select value={fitTierFilter} onValueChange={setFitTierFilter}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Fit tier" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All tiers</SelectItem>
            <SelectItem value="strong">Strong</SelectItem>
            <SelectItem value="moderate">Moderate</SelectItem>
            <SelectItem value="weak">Weak</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading pitches...</span>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={fetchPitches}>
            Retry
          </Button>
        </div>
      ) : pitches.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Mic className="mb-4 h-12 w-12 text-muted-foreground/40" />
          <h3 className="text-lg font-semibold">No Pitches Found</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Score podcasts in the Discovery tab, then run the pitch generation script.
          </p>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            {pitches.map(pitch => (
              <PitchCard key={pitch.id} pitch={pitch} onUpdate={fetchPitches} />
            ))}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              Showing {(page - 1) * limit + 1}-{Math.min(page * limit, total)} of {total}
            </span>
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="px-3 text-sm">
                {page} / {totalPages}
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Campaign Tracker Tab ─────────────────────────────────────────────

function CampaignTrackerTab() {
  const [campaigns, setCampaigns] = useState<CampaignWithDetails[]>([]);
  const [stats, setStats] = useState<CampaignStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [outcomeFilter, setOutcomeFilter] = useState('all');
  const [search, setSearch] = useState('');

  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 25;

  // Inline editing
  const [editingNotes, setEditingNotes] = useState<number | null>(null);
  const [notesValue, setNotesValue] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);

  const fetchCampaigns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('limit', String(limit));
      if (outcomeFilter !== 'all') params.set('outcome', outcomeFilter);
      if (search) params.set('search', search);

      const res = await fetch(`/api/podcast/campaigns?${params}`);
      if (!res.ok) throw new Error('Failed to fetch campaigns');
      const data = await res.json();
      setCampaigns(data.campaigns || []);
      setTotal(data.total ?? 0);
      setTotalPages(data.total_pages ?? 1);
      setStats(data.stats || null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load campaigns');
    } finally {
      setLoading(false);
    }
  }, [page, outcomeFilter, search]);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  useEffect(() => {
    setPage(1);
  }, [outcomeFilter, search]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  const updateCampaign = async (campaignId: number, updates: { notes?: string; outcome?: string }) => {
    try {
      const res = await fetch('/api/podcast/campaigns', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ campaign_id: campaignId, ...updates }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Update failed');
      }
      setFeedback('Updated successfully');
      setTimeout(() => setFeedback(null), 3000);
      fetchCampaigns();
    } catch (err: unknown) {
      setFeedback(err instanceof Error ? err.message : 'Update failed');
    }
  };

  const saveNotes = async (campaignId: number) => {
    await updateCampaign(campaignId, { notes: notesValue });
    setEditingNotes(null);
  };

  const formatDate = (d: string | null) => {
    if (!d) return '-';
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const pipelineStages = PIPELINE_STAGES;

  return (
    <div className="space-y-6">
      {/* Dashboard Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Sent</CardDescription>
            <CardTitle className="text-3xl">{stats?.total_sent ?? 0}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              <Send className="inline h-3 w-3 mr-1" />
              Pitches sent to podcast hosts
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Replied</CardDescription>
            <CardTitle className="text-3xl">{(stats?.outcomes?.booked ?? 0) + (stats?.outcomes?.maybe_later ?? 0) + (stats?.pipeline?.replied ?? 0)}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              <MessageSquare className="inline h-3 w-3 mr-1" />
              Got a response back
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Booked</CardDescription>
            <CardTitle className="text-3xl text-green-600">{stats?.outcomes?.booked ?? 0}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              <Mic className="inline h-3 w-3 mr-1" />
              Episodes confirmed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Response Rate</CardDescription>
            <CardTitle className="text-3xl">
              {stats && stats.total_sent > 0
                ? `${Math.round(((stats.outcomes?.booked ?? 0) + (stats.outcomes?.declined ?? 0) + (stats.outcomes?.maybe_later ?? 0)) / stats.total_sent * 100)}%`
                : '0%'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              <BarChart3 className="inline h-3 w-3 mr-1" />
              Any response (booked + declined + maybe)
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline Visualization */}
      {stats && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Pipeline</CardTitle>
          </CardHeader>
          <CardContent>
            {(() => {
              const totalInPipeline = Object.values(stats.pipeline || {}).reduce((a: number, b: number) => a + b, 0);
              return (
                <div className="flex items-center gap-1">
                  {pipelineStages.map((stage, i) => {
                    const count = stats.pipeline?.[stage.key] ?? 0;
                    const widthPct = totalInPipeline > 0 ? Math.max(count / totalInPipeline * 100, 8) : 20;
                    return (
                      <div key={stage.key} className="flex flex-col items-center" style={{ width: `${widthPct}%`, minWidth: 60 }}>
                        <div className={cn('w-full rounded-md py-3 text-center text-sm font-medium', PIPELINE_COLORS[i])}>
                          {count}
                        </div>
                        <span className="mt-1 text-xs text-muted-foreground">{stage.label}</span>
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3">
        <form onSubmit={handleSearch} className="flex flex-1 items-center gap-2" style={{ minWidth: 200 }}>
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search campaigns..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Button type="submit" size="sm" variant="outline">Search</Button>
        </form>

        <Select value={outcomeFilter} onValueChange={setOutcomeFilter}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Outcome" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All outcomes</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="booked">Booked</SelectItem>
            <SelectItem value="declined">Declined</SelectItem>
            <SelectItem value="no_response">No Response</SelectItem>
            <SelectItem value="maybe_later">Maybe Later</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Feedback */}
      {feedback && (
        <div className="flex items-center rounded-md bg-green-50 px-4 py-2 text-sm text-green-700 border border-green-200">
          {feedback}
          <button onClick={() => setFeedback(null)} className="ml-2 font-medium underline">Dismiss</button>
        </div>
      )}

      {/* Campaign Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading campaigns...</span>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={fetchCampaigns}>Retry</Button>
        </div>
      ) : campaigns.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Send className="mb-4 h-12 w-12 text-muted-foreground/40" />
          <h3 className="text-lg font-semibold">No Campaigns Yet</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Send pitches from the Pitch Review tab to start tracking campaigns.
          </p>
        </div>
      ) : (
        <>
          <div className="rounded-md border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-3 py-2 text-left font-medium">Podcast</th>
                  <th className="px-3 py-2 text-left font-medium">Speaker</th>
                  <th className="px-3 py-2 text-left font-medium">Sent</th>
                  <th className="px-3 py-2 text-left font-medium">Outcome</th>
                  <th className="px-3 py-2 text-left font-medium">Notes</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map(campaign => (
                  <tr key={campaign.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-3 py-2">
                      <div>
                        <span className="font-medium">{campaign.podcast?.title ?? 'Unknown'}</span>
                        {campaign.pitch?.subject_line && (
                          <p className="text-xs text-muted-foreground truncate max-w-[250px]">
                            {campaign.pitch.subject_line}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <Badge variant="outline" className="text-xs">
                        {campaign.speaker?.name ?? '-'}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-xs text-muted-foreground">
                      {formatDate(campaign.sent_at)}
                      {campaign.send_method && (
                        <span className="ml-1 text-muted-foreground/60">
                          ({campaign.send_method === 'gmail_draft' ? 'draft' : campaign.send_method})
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <Select
                        value={campaign.outcome || 'pending'}
                        onValueChange={(val) => updateCampaign(campaign.id, { outcome: val })}
                      >
                        <SelectTrigger className="h-7 w-[140px] text-xs">
                          <Badge
                            variant="outline"
                            className={cn('text-xs', OUTCOME_STYLES[campaign.outcome || 'pending'] || OUTCOME_STYLES.pending)}
                          >
                            {(campaign.outcome || 'pending').replace('_', ' ')}
                          </Badge>
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="pending">Pending</SelectItem>
                          <SelectItem value="booked">Booked</SelectItem>
                          <SelectItem value="declined">Declined</SelectItem>
                          <SelectItem value="no_response">No Response</SelectItem>
                          <SelectItem value="maybe_later">Maybe Later</SelectItem>
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-3 py-2">
                      {editingNotes === campaign.id ? (
                        <div className="flex items-center gap-1">
                          <Input
                            value={notesValue}
                            onChange={e => setNotesValue(e.target.value)}
                            className="h-7 text-xs"
                            placeholder="Add notes..."
                            onKeyDown={e => {
                              if (e.key === 'Enter') saveNotes(campaign.id);
                              if (e.key === 'Escape') setEditingNotes(null);
                            }}
                            autoFocus
                          />
                          <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => saveNotes(campaign.id)}>
                            <Check className="h-3 w-3" />
                          </Button>
                          <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setEditingNotes(null)}>
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      ) : (
                        <button
                          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                          onClick={() => {
                            setEditingNotes(campaign.id);
                            setNotesValue(campaign.notes || '');
                          }}
                        >
                          {campaign.notes ? (
                            <span className="truncate max-w-[200px]">{campaign.notes}</span>
                          ) : (
                            <>
                              <StickyNote className="h-3 w-3" />
                              <span>Add note</span>
                            </>
                          )}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              Showing {(page - 1) * limit + 1}-{Math.min(page * limit, total)} of {total}
            </span>
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="px-3 text-sm">
                {page} / {totalPages}
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────

export default function PodcastOutreachPage() {
  const [profiles, setProfiles] = useState<SpeakerProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchProfiles() {
      try {
        const res = await fetch('/api/podcast/profiles');
        if (!res.ok) throw new Error('Failed to fetch profiles');
        const data = await res.json();
        setProfiles(data.profiles || []);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to load profiles';
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
    fetchProfiles();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-6 py-4">
          <Link href="/tools" className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-xl font-bold">Podcast Outreach</h1>
            <p className="text-sm text-muted-foreground">
              Book Sally and Justin on podcasts for camping season 2026
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-7xl px-6 py-6">
        <Tabs defaultValue="profiles" className="w-full">
          <TabsList className="mb-6 grid w-full grid-cols-4">
            <TabsTrigger value="profiles">Speaker Profiles</TabsTrigger>
            <TabsTrigger value="discovery">Discovery</TabsTrigger>
            <TabsTrigger value="pitches">Pitch Review</TabsTrigger>
            <TabsTrigger value="tracker">Campaign Tracker</TabsTrigger>
          </TabsList>

          {/* Tab 1: Speaker Profiles */}
          <TabsContent value="profiles">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">Loading profiles...</span>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <p className="text-sm text-destructive">{error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => window.location.reload()}
                >
                  Retry
                </Button>
              </div>
            ) : profiles.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <User className="mb-4 h-12 w-12 text-muted-foreground/40" />
                <h3 className="text-lg font-semibold">No Speaker Profiles</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Run the seed script to add profiles: python scripts/intelligence/seed_speaker_profiles.py
                </p>
              </div>
            ) : (
              <div className="grid gap-6 lg:grid-cols-2">
                {profiles.map(profile => (
                  <SpeakerCard key={profile.id} profile={profile} />
                ))}
              </div>
            )}
          </TabsContent>

          {/* Tab 2: Discovery & Scoring */}
          <TabsContent value="discovery">
            <DiscoveryTab />
          </TabsContent>

          {/* Tab 3: Pitch Review */}
          <TabsContent value="pitches">
            <PitchReviewTab />
          </TabsContent>

          {/* Tab 4: Campaign Tracker */}
          <TabsContent value="tracker">
            <CampaignTrackerTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
