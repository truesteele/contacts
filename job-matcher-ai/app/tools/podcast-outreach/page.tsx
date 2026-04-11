'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
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
import {
  ArrowLeft,
  ArrowUpDown,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Mic,
  User,
  ExternalLink,
  Loader2,
  BookOpen,
  Quote,
  Radio,
  Search,
  Zap,
} from 'lucide-react';

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

interface PodcastPitch {
  fit_tier: string | null;
  fit_score: number | null;
  fit_rationale: string | null;
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

// ── Placeholder Tab ────────────────────────────────────────────────────

function PlaceholderTab({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <BookOpen className="mb-4 h-12 w-12 text-muted-foreground/40" />
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
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
  }, [page, speaker, search, activityFilter, fitTierFilter]);

  useEffect(() => {
    fetchPodcasts();
  }, [fetchPodcasts]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
    setSelected(new Set());
  }, [search, speaker, fitTierFilter, activityFilter]);

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
    setPage(1);
    fetchPodcasts();
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
                Scoring...
              </>
            ) : (
              <>
                <Zap className="mr-1 h-3 w-3" />
                Score Selected
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
                  return (
                    <tr
                      key={podcast.id}
                      className={cn(
                        'border-b hover:bg-muted/30 transition-colors',
                        selected.has(podcast.id) && 'bg-blue-50/50'
                      )}
                    >
                      <td className="px-3 py-2">
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
                        <Badge variant="outline" className={cn('text-[10px] capitalize', FIT_TIER_STYLES[tier])}>
                          {tier}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-center font-mono text-xs">
                        {podcast.pitch?.fit_score != null ? podcast.pitch.fit_score : '-'}
                      </td>
                    </tr>
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

          {/* Tab 3: Pitch Review - Placeholder */}
          <TabsContent value="pitches">
            <PlaceholderTab
              title="Pitch Review"
              description="Coming soon - Review, edit, and approve AI-generated podcast pitches."
            />
          </TabsContent>

          {/* Tab 4: Campaign Tracker - Placeholder */}
          <TabsContent value="tracker">
            <PlaceholderTab
              title="Campaign Tracker"
              description="Coming soon - Track outreach progress, responses, and bookings."
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
