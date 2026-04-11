'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Mic,
  User,
  ExternalLink,
  Loader2,
  BookOpen,
  Quote,
  Radio,
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

          {/* Tab 2: Discovery - Placeholder */}
          <TabsContent value="discovery">
            <PlaceholderTab
              title="Podcast Discovery"
              description="Coming soon - Search and discover podcasts, score fit, and manage discovery pipeline."
            />
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
