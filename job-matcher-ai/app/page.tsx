'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Network,
  Mail,
  Users,
  Search,
  MapPin,
  Mountain,
  ArrowUpRight,
  Sparkles,
  Star,
} from 'lucide-react';

interface Stats {
  total: number;
  rated: number;
  with_email: number;
}

function useNetworkStats() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch('/api/rate?mode=unrated&sort=ai_close');
        if (!res.ok) return;
        const data = await res.json();
        setStats({
          total: (data.unrated_count ?? 0) + (data.rated_count ?? 0),
          rated: data.rated_count ?? 0,
          with_email: 0,
        });
      } catch {
        // silent
      }
    }
    load();
  }, []);

  return stats;
}

const TOOLS = [
  {
    title: 'Network Intelligence',
    description:
      'AI copilot for exploring your 2,500-person network. Natural language queries, smart filters, prospect lists, and outreach drafting.',
    href: '/tools?tab=network-intel',
    icon: Network,
    accent: 'from-teal-500/10 to-emerald-500/5',
    iconColor: 'text-teal-600',
    badge: 'Primary',
    large: true,
  },
  {
    title: 'Email Finder',
    description:
      'Enter a LinkedIn URL, get their email. Checks your database, searches 5 Gmail accounts, then falls back to Tomba API.',
    href: '/email-lookup',
    icon: Mail,
    accent: 'from-violet-500/10 to-purple-500/5',
    iconColor: 'text-violet-600',
  },
  {
    title: 'Familiarity Rater',
    description:
      'Rate every contact 0\u20134 on how well you know them. Mobile-optimized flashcard UI for rapid classification.',
    href: '/rate',
    icon: Star,
    accent: 'from-amber-500/10 to-orange-500/5',
    iconColor: 'text-amber-600',
  },
  {
    title: 'AI Job Search',
    description: 'Chat-based candidate matching from your personal network for open roles.',
    href: '/tools?tab=job-search',
    icon: Search,
    accent: 'from-blue-500/10 to-sky-500/5',
    iconColor: 'text-blue-600',
  },
  {
    title: 'SoCal Contacts',
    description: 'Browse and filter contacts in the LA and San Diego metro areas.',
    href: '/tools?tab=socal-contacts',
    icon: MapPin,
    accent: 'from-rose-500/10 to-pink-500/5',
    iconColor: 'text-rose-600',
  },
  {
    title: 'Camelback Coaches',
    description: 'Search and match coaches from the Camelback Ventures expert network.',
    href: '/tools?tab=coach-search',
    icon: Mountain,
    accent: 'from-emerald-500/10 to-green-500/5',
    iconColor: 'text-emerald-600',
  },
];

export default function Dashboard() {
  const stats = useNetworkStats();

  return (
    <div className="min-h-screen bg-background">
      {/* Subtle grain overlay */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.015]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        }}
      />

      <div className="relative max-w-5xl mx-auto px-5 py-10 sm:py-16">
        {/* Header */}
        <header className="mb-12 sm:mb-16">
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <p className="text-xs font-mono tracking-widest text-muted-foreground uppercase mb-2">
                True Steele
              </p>
              <h1 className="font-display text-4xl sm:text-5xl tracking-tight text-foreground">
                Network Command
              </h1>
            </div>
            <div className="hidden sm:flex items-center gap-2 mt-2">
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-xs font-mono text-muted-foreground">AI-powered</span>
            </div>
          </div>

          {/* Stats row */}
          {stats && (
            <div className="flex flex-wrap items-center gap-2">
              <div className="stat-pill">
                <Users className="w-3.5 h-3.5" />
                <span className="font-mono">{stats.total.toLocaleString()}</span> contacts
              </div>
              <div className="stat-pill">
                <Star className="w-3.5 h-3.5" />
                <span className="font-mono">{stats.rated.toLocaleString()}</span> rated
              </div>
              <div className="stat-pill">
                <span className="font-mono">
                  {stats.total > 0
                    ? Math.round((stats.rated / stats.total) * 100)
                    : 0}
                  %
                </span>{' '}
                classified
              </div>
            </div>
          )}
        </header>

        {/* Tool grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {TOOLS.map((tool) => {
            const Icon = tool.icon;
            return (
              <Link
                key={tool.title}
                href={tool.href}
                className={`tool-card group ${
                  tool.large ? 'sm:col-span-2 lg:col-span-3' : ''
                }`}
              >
                <div
                  className={`absolute inset-0 bg-gradient-to-br ${tool.accent} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}
                />
                <div className="relative">
                  <div className="flex items-start justify-between mb-4">
                    <div
                      className={`w-10 h-10 rounded-lg bg-secondary flex items-center justify-center ${tool.iconColor} transition-colors`}
                    >
                      <Icon className="w-5 h-5" />
                    </div>
                    <ArrowUpRight className="w-4 h-4 text-muted-foreground/40 group-hover:text-foreground/60 transition-all duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <h2 className="text-base font-semibold tracking-tight">
                      {tool.title}
                    </h2>
                    {tool.badge && (
                      <span className="text-[10px] font-mono font-medium uppercase tracking-wider text-primary bg-primary/8 px-1.5 py-0.5 rounded">
                        {tool.badge}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {tool.description}
                  </p>
                </div>
              </Link>
            );
          })}
        </div>

        {/* Footer */}
        <footer className="mt-16 pt-6 border-t">
          <p className="text-xs text-muted-foreground/50 font-mono">
            Kindora &middot; True Steele &middot; Outdoorithm
          </p>
        </footer>
      </div>
    </div>
  );
}
