'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { MessageDetailSheet } from '@/components/campaign/message-detail-sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  Megaphone,
  DollarSign,
  Users,
  Mail,
  TrendingUp,
  Loader2,
  Search,
  Filter,
  X,
  Send,
  SendHorizonal,
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

const LIFECYCLE_LABELS: Record<string, string> = {
  new: 'New',
  prior_donor: 'Prior Donor',
  lapsed: 'Lapsed',
};

type BcdSortField = 'name' | 'list' | 'ask_amount' | 'persona';

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

  // Lists B-D filter state
  const [bcdSearch, setBcdSearch] = useState('');
  const [bcdFilterList, setBcdFilterList] = useState('all');
  const [bcdFilterPersona, setBcdFilterPersona] = useState('all');
  const [bcdFilterCapacity, setBcdFilterCapacity] = useState('all');
  const [bcdFilterLifecycle, setBcdFilterLifecycle] = useState('all');
  const [bcdSortBy, setBcdSortBy] = useState<BcdSortField>('ask_amount');
  const [bcdSortOrder, setBcdSortOrder] = useState<'asc' | 'desc'>('desc');

  // Send state
  const [sendingIds, setSendingIds] = useState<Set<number>>(new Set());
  const [sendingAllA, setSendingAllA] = useState(false);
  const [sendingPreEmail, setSendingPreEmail] = useState(false);
  const [sendingEmail1, setSendingEmail1] = useState(false);

  const loadData = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // List A contacts sorted by ask amount descending
  const listAContacts = useMemo(
    () =>
      contacts
        .filter((c) => c.list === 'A')
        .sort((a, b) => (b.ask_amount || 0) - (a.ask_amount || 0)),
    [contacts]
  );

  // Lists B-D contacts with filtering and sorting
  const bcdAllContacts = useMemo(
    () => contacts.filter((c) => c.list && c.list !== 'A'),
    [contacts]
  );

  const bcdFiltered = useMemo(() => {
    let result = bcdAllContacts;

    if (bcdFilterList !== 'all') {
      result = result.filter((c) => c.list === bcdFilterList);
    }
    if (bcdFilterPersona !== 'all') {
      result = result.filter((c) => c.persona === bcdFilterPersona);
    }
    if (bcdFilterCapacity !== 'all') {
      result = result.filter((c) => c.capacity_tier === bcdFilterCapacity);
    }
    if (bcdFilterLifecycle !== 'all') {
      result = result.filter((c) => c.lifecycle === bcdFilterLifecycle);
    }
    if (bcdSearch) {
      const term = bcdSearch.toLowerCase();
      result = result.filter(
        (c) =>
          `${c.first_name} ${c.last_name}`.toLowerCase().includes(term) ||
          (c.company || '').toLowerCase().includes(term)
      );
    }

    const sorted = [...result].sort((a, b) => {
      let cmp = 0;
      switch (bcdSortBy) {
        case 'name':
          cmp = `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`);
          break;
        case 'list':
          cmp = (a.list || '').localeCompare(b.list || '');
          break;
        case 'ask_amount':
          cmp = (a.ask_amount || 0) - (b.ask_amount || 0);
          break;
        case 'persona':
          cmp = (a.persona || '').localeCompare(b.persona || '');
          break;
      }
      return bcdSortOrder === 'asc' ? cmp : -cmp;
    });

    return sorted;
  }, [bcdAllContacts, bcdFilterList, bcdFilterPersona, bcdFilterCapacity, bcdFilterLifecycle, bcdSearch, bcdSortBy, bcdSortOrder]);

  const handleBcdSort = useCallback((field: BcdSortField) => {
    setBcdSortBy((prev) => {
      if (prev === field) {
        setBcdSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
        return prev;
      }
      setBcdSortOrder(field === 'name' || field === 'list' || field === 'persona' ? 'asc' : 'desc');
      return field;
    });
  }, []);

  const bcdActiveFilterCount = useMemo(() => {
    let count = 0;
    if (bcdFilterList !== 'all') count++;
    if (bcdFilterPersona !== 'all') count++;
    if (bcdFilterCapacity !== 'all') count++;
    if (bcdFilterLifecycle !== 'all') count++;
    return count;
  }, [bcdFilterList, bcdFilterPersona, bcdFilterCapacity, bcdFilterLifecycle]);

  const clearBcdFilters = useCallback(() => {
    setBcdFilterList('all');
    setBcdFilterPersona('all');
    setBcdFilterCapacity('all');
    setBcdFilterLifecycle('all');
    setBcdSearch('');
  }, []);

  // ── Send handlers ──────────────────────────────────────────────────

  const sendCampaignEmails = useCallback(async (
    contactIds: number[],
    emailType: string,
  ): Promise<{ total_sent: number; total_failed: number; total_skipped: number }> => {
    const res = await fetch('/api/network-intel/campaign/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contact_ids: contactIds, email_type: emailType }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Send failed (${res.status})`);
    }
    return res.json();
  }, []);

  const handleSendOne = useCallback(async (contact: CampaignContact) => {
    const email = resolveEmail(contact);
    if (!email) return;
    const name = `${contact.first_name} ${contact.last_name}`.trim();
    if (!window.confirm(`Send to ${name} at ${email}?`)) return;

    setSendingIds((prev) => new Set(prev).add(contact.id));
    try {
      await sendCampaignEmails([contact.id], 'personal_outreach');
      await loadData();
    } catch {
      // loadData will show current state regardless
    } finally {
      setSendingIds((prev) => {
        const next = new Set(prev);
        next.delete(contact.id);
        return next;
      });
    }
  }, [sendCampaignEmails, loadData]);

  const handleSendAllA = useCallback(async () => {
    const unsent = listAContacts.filter((c) => {
      const status = getContactStatus(c);
      return status === 'draft' && c.channel === 'email' && resolveEmail(c);
    });
    if (unsent.length === 0) return;
    if (!window.confirm(`Send personal outreach to ${unsent.length} unsent List A contacts?`)) return;

    setSendingAllA(true);
    try {
      await sendCampaignEmails(unsent.map((c) => c.id), 'personal_outreach');
      await loadData();
    } catch {
      // loadData will show current state regardless
    } finally {
      setSendingAllA(false);
    }
  }, [listAContacts, sendCampaignEmails, loadData]);

  const handleSendPreEmail = useCallback(async () => {
    const eligible = bcdAllContacts.filter((c) => {
      const status = getContactStatus(c);
      const hasSent = c.send_status && c.send_status['pre_email_note'];
      return !hasSent && status !== 'donated' && (c.lifecycle === 'prior_donor' || c.lifecycle === 'lapsed') && resolveEmail(c);
    });
    if (eligible.length === 0) return;
    if (!window.confirm(`Send pre-email notes to ${eligible.length} prior donor/lapsed contacts?`)) return;

    setSendingPreEmail(true);
    try {
      await sendCampaignEmails(eligible.map((c) => c.id), 'pre_email_note');
      await loadData();
    } catch {
      // loadData will show current state regardless
    } finally {
      setSendingPreEmail(false);
    }
  }, [bcdAllContacts, sendCampaignEmails, loadData]);

  const handleSendEmail1 = useCallback(async () => {
    const eligible = bcdAllContacts.filter((c) => {
      const hasSent = c.send_status && c.send_status['email_1'];
      return !hasSent && resolveEmail(c);
    });
    if (eligible.length === 0) return;
    if (!window.confirm(`Send Email 1 to ${eligible.length} contacts in Lists B-D?`)) return;

    setSendingEmail1(true);
    try {
      await sendCampaignEmails(eligible.map((c) => c.id), 'email_1');
      await loadData();
    } catch {
      // loadData will show current state regardless
    } finally {
      setSendingEmail1(false);
    }
  }, [bcdAllContacts, sendCampaignEmails, loadData]);

  function getBcdSortIcon(field: BcdSortField) {
    if (bcdSortBy !== field) return <ArrowUpDown className="w-3 h-3 ml-1 opacity-40" />;
    return bcdSortOrder === 'asc' ? (
      <ArrowUp className="w-3 h-3 ml-1" />
    ) : (
      <ArrowDown className="w-3 h-3 ml-1" />
    );
  }

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
            <TabsTrigger value="lists-bcd">Lists B-D ({bcdAllContacts.length})</TabsTrigger>
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
              <div className="flex items-center justify-between mb-3">
                <div className="text-xs text-muted-foreground">
                  {listAContacts.length} personal outreach contacts — sorted by ask amount
                </div>
                {(() => {
                  const unsentCount = listAContacts.filter((c) =>
                    getContactStatus(c) === 'draft' && c.channel === 'email' && resolveEmail(c)
                  ).length;
                  if (unsentCount === 0) return null;
                  return (
                    <Button
                      size="sm"
                      onClick={handleSendAllA}
                      disabled={sendingAllA || sendingIds.size > 0}
                      className="gap-1.5"
                    >
                      {sendingAllA ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        <>
                          <SendHorizonal className="w-3.5 h-3.5" />
                          Send All Unsent ({unsentCount})
                        </>
                      )}
                    </Button>
                  );
                })()}
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
                        <th className="text-center px-3 py-2 font-medium text-xs text-muted-foreground w-20">Status</th>
                        <th className="text-center px-3 py-2 font-medium text-xs text-muted-foreground w-16"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {listAContacts.map((c, idx) => {
                        const status = getContactStatus(c);
                        const config = STATUS_CONFIG[status];
                        const isEmail = c.channel === 'email';
                        const hasEmail = !!resolveEmail(c);
                        const isSending = sendingIds.has(c.id);
                        const canSend = isEmail && hasEmail && status === 'draft' && !sendingAllA;
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
                            <td className="px-3 py-2.5 text-center">
                              <div className="flex items-center justify-center gap-1.5">
                                <div className={cn('w-2 h-2 rounded-full', config.dot)} />
                                <span className="text-xs">{config.label}</span>
                              </div>
                            </td>
                            <td className="px-3 py-2.5 text-center">
                              {canSend && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-7 w-7 p-0"
                                  disabled={isSending}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleSendOne(c);
                                  }}
                                >
                                  {isSending ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  ) : (
                                    <Send className="w-3.5 h-3.5" />
                                  )}
                                </Button>
                              )}
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

          {/* ── Lists B-D Tab ── */}
          <TabsContent value="lists-bcd">
            <div className="mt-2">
              {/* Bulk send buttons */}
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleSendPreEmail}
                  disabled={sendingPreEmail || sendingEmail1}
                  className="gap-1.5"
                >
                  {sendingPreEmail ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Mail className="w-3.5 h-3.5" />
                      Send Pre-Email Notes
                    </>
                  )}
                </Button>
                <Button
                  size="sm"
                  onClick={handleSendEmail1}
                  disabled={sendingEmail1 || sendingPreEmail}
                  className="gap-1.5"
                >
                  {sendingEmail1 ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <SendHorizonal className="w-3.5 h-3.5" />
                      Send Email 1
                    </>
                  )}
                </Button>
              </div>

              {/* Search + count */}
              <div className="flex items-center gap-3 mb-2">
                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search by name, company..."
                    value={bcdSearch}
                    onChange={(e) => setBcdSearch(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 text-sm rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                  {bcdSearch && (
                    <button
                      onClick={() => setBcdSearch('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
                <span className="text-xs text-muted-foreground ml-auto">
                  Showing {bcdFiltered.length} of {bcdAllContacts.length} contacts
                </span>
              </div>

              {/* Filter bar */}
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                <Filter className="w-3.5 h-3.5 text-muted-foreground shrink-0" />

                <Select value={bcdFilterList} onValueChange={setBcdFilterList}>
                  <SelectTrigger className="h-7 w-[100px] text-xs">
                    <SelectValue placeholder="List" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Lists</SelectItem>
                    <SelectItem value="B">List B</SelectItem>
                    <SelectItem value="C">List C</SelectItem>
                    <SelectItem value="D">List D</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={bcdFilterPersona} onValueChange={setBcdFilterPersona}>
                  <SelectTrigger className="h-7 w-[140px] text-xs">
                    <SelectValue placeholder="Persona" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Personas</SelectItem>
                    {Object.entries(PERSONA_LABELS).map(([val, label]) => (
                      <SelectItem key={val} value={val}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={bcdFilterCapacity} onValueChange={setBcdFilterCapacity}>
                  <SelectTrigger className="h-7 w-[130px] text-xs">
                    <SelectValue placeholder="Capacity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Capacity</SelectItem>
                    {Object.entries(CAPACITY_LABELS).map(([val, label]) => (
                      <SelectItem key={val} value={val}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={bcdFilterLifecycle} onValueChange={setBcdFilterLifecycle}>
                  <SelectTrigger className="h-7 w-[130px] text-xs">
                    <SelectValue placeholder="Lifecycle" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Lifecycle</SelectItem>
                    {Object.entries(LIFECYCLE_LABELS).map(([val, label]) => (
                      <SelectItem key={val} value={val}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {bcdActiveFilterCount > 0 && (
                  <button
                    onClick={clearBcdFilters}
                    className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground h-7 px-2 rounded-md hover:bg-muted transition-colors"
                  >
                    <X className="w-3 h-3" />
                    Clear ({bcdActiveFilterCount})
                  </button>
                )}
              </div>

              {/* Table */}
              <Card>
                <ScrollArea className="h-[calc(100vh-340px)] min-h-[400px]">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 sticky top-0 z-10">
                      <tr className="border-b">
                        {([
                          ['name', 'Name', 'min-w-[160px]'],
                          ['list', 'List', 'w-[70px]'],
                          ['persona', 'Persona', 'w-[120px]'],
                          ['ask_amount', 'Ask ($)', 'w-[100px]'],
                        ] as [BcdSortField, string, string][]).map(([field, label, width]) => (
                          <th key={field} className={cn('text-left px-3 py-2', width)}>
                            <button
                              onClick={() => handleBcdSort(field)}
                              className={cn(
                                'flex items-center font-medium text-xs uppercase tracking-wide transition-colors',
                                bcdSortBy === field
                                  ? 'text-foreground'
                                  : 'text-muted-foreground hover:text-foreground'
                              )}
                            >
                              {label}
                              {getBcdSortIcon(field)}
                            </button>
                          </th>
                        ))}
                        <th className="text-left px-3 py-2 w-[100px]">
                          <span className="font-medium text-xs uppercase tracking-wide text-muted-foreground">
                            Lifecycle
                          </span>
                        </th>
                        <th className="text-center px-3 py-2 w-[80px]">
                          <span className="font-medium text-xs uppercase tracking-wide text-muted-foreground">
                            Status
                          </span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {bcdFiltered.map((c) => {
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
                            <td className="px-3 py-2.5">
                              <div className="font-medium">{c.first_name} {c.last_name}</div>
                              {c.company && (
                                <div className="text-xs text-muted-foreground truncate max-w-[200px]">
                                  {c.company}
                                </div>
                              )}
                            </td>
                            <td className="px-3 py-2.5">
                              <Badge variant="outline" className="text-[10px] font-mono">
                                {c.list}
                              </Badge>
                            </td>
                            <td className="px-3 py-2.5">
                              <Badge variant="outline" className="text-[10px]">
                                {PERSONA_LABELS[c.persona || ''] || c.persona || '—'}
                              </Badge>
                            </td>
                            <td className="px-3 py-2.5 font-mono font-medium">
                              {c.ask_amount ? formatCurrency(c.ask_amount) : '—'}
                            </td>
                            <td className="px-3 py-2.5">
                              <Badge variant="outline" className="text-[10px]">
                                {LIFECYCLE_LABELS[c.lifecycle || ''] || c.lifecycle || '—'}
                              </Badge>
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
                      {bcdFiltered.length === 0 && (
                        <tr>
                          <td colSpan={6} className="px-3 py-8 text-center text-sm text-muted-foreground">
                            No contacts match the current filters
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </ScrollArea>
              </Card>
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

      {/* Message detail sheet */}
      <MessageDetailSheet
        contactId={selectedContactId}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        onUpdated={loadData}
      />
    </main>
  );
}
