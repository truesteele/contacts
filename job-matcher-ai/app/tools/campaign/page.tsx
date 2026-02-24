'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import {
  ArrowLeft,
  Megaphone,
  DollarSign,
  Users,
  Mail,
  TrendingUp,
  Loader2,
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────

interface CampaignContact {
  id: number;
  first_name: string;
  last_name: string;
  company: string | null;
  position: string | null;
  email: string | null;
  personal_email: string | null;
  work_email: string | null;
  list: string | null;
  persona: string | null;
  ask_amount: number | null;
  capacity_tier: string | null;
  lifecycle: string | null;
  motivation: string | null;
  channel: string | null;
  subject: string | null;
  has_outreach: boolean;
  has_copy: boolean;
  send_status: Record<string, { sent_at: string; resend_id: string }> | null;
  donation: { amount: number; donated_at: string; source: string } | null;
  responded_at: string | null;
}

interface CampaignStats {
  by_list: Record<string, number>;
  by_persona: Record<string, number>;
  by_capacity: Record<string, number>;
  by_lifecycle: Record<string, number>;
  by_send_status: Record<string, number>;
}

// ── Constants ──────────────────────────────────────────────────────────

const GOAL = 100_000;

const STATUS_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  donated: { label: 'Donated', color: 'bg-green-100 text-green-800 border-green-200', dot: 'bg-green-500' },
  responded: { label: 'Responded', color: 'bg-yellow-100 text-yellow-800 border-yellow-200', dot: 'bg-yellow-500' },
  sent: { label: 'Sent', color: 'bg-blue-100 text-blue-800 border-blue-200', dot: 'bg-blue-500' },
  draft: { label: 'Draft', color: 'bg-gray-100 text-gray-600 border-gray-200', dot: 'bg-gray-400' },
};

const CAPACITY_LABELS: Record<string, string> = {
  leadership: 'Leadership',
  major: 'Major',
  mid: 'Mid',
  base: 'Base',
  community: 'Community',
};

const PERSONA_LABELS: Record<string, string> = {
  believer: 'Believer',
  impact_professional: 'Impact Pro',
  network_peer: 'Network Peer',
};

// ── Helpers ────────────────────────────────────────────────────────────

function getContactStatus(c: CampaignContact): string {
  if (c.donation) return 'donated';
  if (c.responded_at) return 'responded';
  if (c.send_status && Object.keys(c.send_status).length > 0) return 'sent';
  return 'draft';
}

function formatCurrency(amount: number): string {
  if (amount >= 1000) return `$${(amount / 1000).toFixed(amount % 1000 === 0 ? 0 : 1)}K`;
  return `$${amount.toLocaleString()}`;
}

function resolveEmail(c: CampaignContact): string | null {
  return c.personal_email || c.email || c.work_email || null;
}

// ── Component ──────────────────────────────────────────────────────────

export default function CampaignPage() {
  const [contacts, setContacts] = useState<CampaignContact[]>([]);
  const [stats, setStats] = useState<CampaignStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedContactId, setSelectedContactId] = useState<number | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch('/api/network-intel/campaign');
        if (!res.ok) throw new Error('Failed to load campaign data');
        const data = await res.json();
        setContacts(data.contacts || []);
        setStats(data.stats || null);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // List A contacts sorted by ask amount descending
  const listAContacts = useMemo(
    () =>
      contacts
        .filter((c) => c.list === 'A')
        .sort((a, b) => (b.ask_amount || 0) - (a.ask_amount || 0)),
    [contacts]
  );

  // Dashboard computed values
  const dashboardData = useMemo(() => {
    const donors = contacts.filter((c) => c.donation);
    const totalRaised = donors.reduce((sum, c) => sum + (c.donation?.amount || 0), 0);
    const listASent = listAContacts.filter(
      (c) => c.send_status && Object.keys(c.send_status).length > 0
    ).length;

    // Determine campaign phase based on current date
    const now = new Date();
    const phases = [
      { name: 'Personal Outreach', start: '2026-02-24', end: '2026-03-02' },
      { name: 'Pre-Email Notes', start: '2026-03-03', end: '2026-03-07' },
      { name: 'Email Sequence', start: '2026-03-09', end: '2026-03-23' },
      { name: 'Follow-Up & Close', start: '2026-03-24', end: '2026-04-06' },
    ];
    let currentPhase = 'Pre-Launch';
    for (const phase of phases) {
      if (now >= new Date(phase.start) && now <= new Date(phase.end)) {
        currentPhase = phase.name;
        break;
      }
      if (now > new Date(phase.end)) {
        currentPhase = phase.name + ' (Complete)';
      }
    }

    return { donors: donors.length, totalRaised, listASent, currentPhase };
  }, [contacts, listAContacts]);

  if (loading) {
    return (
      <main className="min-h-screen bg-background">
        <div className="max-w-7xl mx-auto p-4">
          <div className="page-header">
            <Link href="/" className="page-back"><ArrowLeft className="w-5 h-5" /></Link>
            <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-600">
              <Megaphone className="w-4 h-4" />
            </div>
            <h1 className="text-lg font-semibold tracking-tight">Campaign</h1>
          </div>
          <div className="flex items-center justify-center h-64">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading campaign data...
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
            <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-600">
              <Megaphone className="w-4 h-4" />
            </div>
            <h1 className="text-lg font-semibold tracking-tight">Campaign</h1>
          </div>
          <p className="text-destructive mt-4">{error}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto p-4">
        {/* Header */}
        <div className="page-header">
          <Link href="/" className="page-back" aria-label="Back to dashboard">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-600">
            <Megaphone className="w-4 h-4" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight">Campaign</h1>
          <span className="ml-auto text-xs text-muted-foreground font-mono">
            {contacts.length} contacts
          </span>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="dashboard" className="mt-4">
          <TabsList>
            <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
            <TabsTrigger value="list-a">List A ({listAContacts.length})</TabsTrigger>
            <TabsTrigger value="lists-bcd">Lists B-D</TabsTrigger>
            <TabsTrigger value="activity">Activity</TabsTrigger>
          </TabsList>

          {/* ── Dashboard Tab ── */}
          <TabsContent value="dashboard">
            <div className="space-y-4 mt-2">
              {/* Progress toward goal */}
              <Card className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-green-600" />
                    <span className="text-sm font-medium">Campaign Progress</span>
                  </div>
                  <Badge variant="outline" className="text-xs font-mono">
                    {dashboardData.currentPhase}
                  </Badge>
                </div>
                <div className="text-3xl font-mono font-bold tracking-tight">
                  ${dashboardData.totalRaised.toLocaleString()}
                  <span className="text-base font-normal text-muted-foreground ml-1">
                    of ${GOAL.toLocaleString()}
                  </span>
                </div>
                <div className="mt-3 h-2.5 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-green-500 transition-all duration-500"
                    style={{ width: `${Math.min((dashboardData.totalRaised / GOAL) * 100, 100)}%` }}
                  />
                </div>
                <div className="text-xs text-muted-foreground mt-1.5 font-mono">
                  {((dashboardData.totalRaised / GOAL) * 100).toFixed(1)}% of goal
                </div>
              </Card>

              {/* Stats row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Card className="p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Users className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Donors</span>
                  </div>
                  <div className="text-2xl font-mono font-bold">{dashboardData.donors}</div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <TrendingUp className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Total Raised</span>
                  </div>
                  <div className="text-2xl font-mono font-bold">
                    ${dashboardData.totalRaised.toLocaleString()}
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Mail className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">List A Sent</span>
                  </div>
                  <div className="text-2xl font-mono font-bold">
                    {dashboardData.listASent}
                    <span className="text-sm font-normal text-muted-foreground">
                      /{listAContacts.length}
                    </span>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Users className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Responded</span>
                  </div>
                  <div className="text-2xl font-mono font-bold">
                    {stats?.by_send_status?.responded || 0}
                  </div>
                </Card>
              </div>

              {/* Contacts by list */}
              <Card className="p-5">
                <h3 className="text-sm font-medium mb-3">Contacts by List</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {(['A', 'B', 'C', 'D'] as const).map((list) => (
                    <div key={list} className="flex items-center justify-between rounded-md border px-3 py-2">
                      <span className="text-sm font-medium">List {list}</span>
                      <span className="text-sm font-mono text-muted-foreground">
                        {stats?.by_list?.[list] || 0}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Breakdown cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Card className="p-4">
                  <h3 className="text-xs font-medium text-muted-foreground mb-2">By Persona</h3>
                  <div className="space-y-1.5">
                    {Object.entries(PERSONA_LABELS).map(([key, label]) => (
                      <div key={key} className="flex items-center justify-between text-sm">
                        <span>{label}</span>
                        <span className="font-mono text-muted-foreground">
                          {stats?.by_persona?.[key] || 0}
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>

                <Card className="p-4">
                  <h3 className="text-xs font-medium text-muted-foreground mb-2">By Capacity</h3>
                  <div className="space-y-1.5">
                    {Object.entries(CAPACITY_LABELS).map(([key, label]) => (
                      <div key={key} className="flex items-center justify-between text-sm">
                        <span>{label}</span>
                        <span className="font-mono text-muted-foreground">
                          {stats?.by_capacity?.[key] || 0}
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>

                <Card className="p-4">
                  <h3 className="text-xs font-medium text-muted-foreground mb-2">Send Status</h3>
                  <div className="space-y-1.5">
                    {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                      <div key={key} className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <div className={cn('w-2 h-2 rounded-full', config.dot)} />
                          <span>{config.label}</span>
                        </div>
                        <span className="font-mono text-muted-foreground">
                          {key === 'draft'
                            ? stats?.by_send_status?.not_sent || 0
                            : stats?.by_send_status?.[key] || 0}
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* ── List A Tab ── */}
          <TabsContent value="list-a">
            <div className="mt-2">
              <div className="text-xs text-muted-foreground mb-3">
                {listAContacts.length} personal outreach contacts — sorted by ask amount
              </div>

              {/* Table */}
              <div className="rounded-lg border overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="text-left px-3 py-2 font-medium text-xs text-muted-foreground w-8">#</th>
                        <th className="text-left px-3 py-2 font-medium text-xs text-muted-foreground">Name</th>
                        <th className="text-left px-3 py-2 font-medium text-xs text-muted-foreground hidden sm:table-cell">Company</th>
                        <th className="text-right px-3 py-2 font-medium text-xs text-muted-foreground">Ask</th>
                        <th className="text-center px-3 py-2 font-medium text-xs text-muted-foreground hidden md:table-cell">Channel</th>
                        <th className="text-left px-3 py-2 font-medium text-xs text-muted-foreground hidden lg:table-cell">Subject</th>
                        <th className="text-center px-3 py-2 font-medium text-xs text-muted-foreground w-20">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {listAContacts.map((c, idx) => {
                        const status = getContactStatus(c);
                        const config = STATUS_CONFIG[status];
                        return (
                          <tr
                            key={c.id}
                            className="border-b last:border-b-0 hover:bg-muted/30 cursor-pointer transition-colors"
                            onClick={() => {
                              setSelectedContactId(c.id);
                              setSheetOpen(true);
                            }}
                          >
                            <td className="px-3 py-2.5 text-xs text-muted-foreground font-mono">{idx + 1}</td>
                            <td className="px-3 py-2.5">
                              <div className="font-medium">{c.first_name} {c.last_name}</div>
                              <div className="text-xs text-muted-foreground sm:hidden">{c.company || ''}</div>
                            </td>
                            <td className="px-3 py-2.5 text-muted-foreground hidden sm:table-cell">
                              {c.company || '—'}
                            </td>
                            <td className="px-3 py-2.5 text-right font-mono font-medium">
                              {c.ask_amount ? formatCurrency(c.ask_amount) : '—'}
                            </td>
                            <td className="px-3 py-2.5 text-center hidden md:table-cell">
                              <Badge variant="outline" className="text-[10px]">
                                {c.channel || 'email'}
                              </Badge>
                            </td>
                            <td className="px-3 py-2.5 hidden lg:table-cell">
                              <span className="text-xs text-muted-foreground line-clamp-1 max-w-[250px]">
                                {c.subject || '—'}
                              </span>
                            </td>
                            <td className="px-3 py-2.5 text-center">
                              <div className="flex items-center justify-center gap-1.5">
                                <div className={cn('w-2 h-2 rounded-full', config.dot)} />
                                <span className="text-xs">{config.label}</span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* ── Lists B-D Tab (placeholder for US-005) ── */}
          <TabsContent value="lists-bcd">
            <div className="flex items-center justify-center h-48 text-sm text-muted-foreground">
              Lists B-D view coming soon
            </div>
          </TabsContent>

          {/* ── Activity Tab (placeholder for US-008) ── */}
          <TabsContent value="activity">
            <div className="flex items-center justify-center h-48 text-sm text-muted-foreground">
              Activity view coming soon
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
