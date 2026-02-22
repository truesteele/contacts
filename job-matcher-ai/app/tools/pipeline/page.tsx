'use client';

import { useState, useEffect, useCallback, useMemo, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import {
  ArrowLeft,
  Columns3,
  DollarSign,
  Eye,
  EyeOff,
  Layers,
  Plus,
  Search,
  X,
} from 'lucide-react';
import { KanbanBoard } from '@/components/pipeline/kanban-board';
import { DealDetailSheet } from '@/components/pipeline/deal-detail-sheet';
import { ContactDetailSheet } from '@/components/contact-detail-sheet';
import { type Deal } from '@/components/pipeline/deal-card';

// ── Types ──────────────────────────────────────────────────────────────

interface Pipeline {
  id: string;
  name: string;
  slug: string;
  entity: string;
  stages: { name: string; color: string }[];
  created_at: string;
}

interface ContactOption {
  id: number;
  first_name: string;
  last_name: string;
  company?: string | null;
}

// ── New Deal Form ──────────────────────────────────────────────────────

interface NewDealFormProps {
  pipelineId: string;
  onCreated: (deal: Deal) => void;
  onClose: () => void;
}

function NewDealForm({ pipelineId, onCreated, onClose }: NewDealFormProps) {
  const [title, setTitle] = useState('');
  const [contactSearch, setContactSearch] = useState('');
  const [contactResults, setContactResults] = useState<ContactOption[]>([]);
  const [selectedContact, setSelectedContact] = useState<ContactOption | null>(null);
  const [amount, setAmount] = useState('');
  const [closeDate, setCloseDate] = useState('');
  const [source, setSource] = useState('');
  const [notes, setNotes] = useState('');
  const [nextAction, setNextAction] = useState('');
  const [nextActionDate, setNextActionDate] = useState('');
  const [saving, setSaving] = useState(false);
  const [searching, setSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);

  // Debounced contact search
  useEffect(() => {
    if (contactSearch.length < 2) {
      setContactResults([]);
      setShowResults(false);
      return;
    }

    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await fetch(
          `/api/network-intel/pipeline/contacts?q=${encodeURIComponent(contactSearch)}`
        );
        if (res.ok) {
          const data = await res.json();
          setContactResults(data.contacts || []);
          setShowResults(true);
        }
      } catch {
        // ignore search errors
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [contactSearch]);

  const handleSubmit = async () => {
    if (!title.trim()) return;
    setSaving(true);

    try {
      const body: Record<string, unknown> = {
        pipeline_id: pipelineId,
        title: title.trim(),
      };
      if (selectedContact) body.contact_id = selectedContact.id;
      if (amount) body.amount = parseFloat(amount);
      if (closeDate) body.close_date = closeDate;
      if (source.trim()) body.source = source.trim();
      if (notes.trim()) body.notes = notes.trim();
      if (nextAction.trim()) body.next_action = nextAction.trim();
      if (nextActionDate) body.next_action_date = nextActionDate;

      const res = await fetch('/api/network-intel/pipeline/deals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error('Failed to create deal');

      const data = await res.json();
      onCreated(data.deal);
      onClose();
    } catch (err) {
      console.error('Failed to create deal:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4 pt-4">
      {/* Title */}
      <div>
        <label className="text-sm font-medium mb-1.5 block">Title *</label>
        <Input
          placeholder="e.g. Series A investment, Consulting engagement..."
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          autoFocus
        />
      </div>

      {/* Contact search */}
      <div>
        <label className="text-sm font-medium mb-1.5 block">Contact</label>
        {selectedContact ? (
          <div className="flex items-center gap-2 px-3 py-2 rounded-md border bg-muted/30">
            <span className="text-sm font-medium">
              {selectedContact.first_name} {selectedContact.last_name}
            </span>
            {selectedContact.company && (
              <span className="text-xs text-muted-foreground">
                at {selectedContact.company}
              </span>
            )}
            <button
              onClick={() => {
                setSelectedContact(null);
                setContactSearch('');
              }}
              className="ml-auto text-muted-foreground hover:text-foreground"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search by name or company..."
              value={contactSearch}
              onChange={(e) => setContactSearch(e.target.value)}
              onFocus={() => contactResults.length > 0 && setShowResults(true)}
              onBlur={() => setTimeout(() => setShowResults(false), 200)}
              className="pl-9"
            />
            {searching && (
              <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
                <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              </div>
            )}

            {/* Search results dropdown */}
            {showResults && contactResults.length > 0 && (
              <div className="absolute z-50 top-full mt-1 left-0 right-0 max-h-48 overflow-y-auto rounded-md border bg-popover shadow-md">
                {contactResults.map((c) => (
                  <button
                    key={c.id}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => {
                      setSelectedContact(c);
                      setContactSearch('');
                      setShowResults(false);
                    }}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-muted/50 transition-colors"
                  >
                    <span className="font-medium">
                      {c.first_name} {c.last_name}
                    </span>
                    {c.company && (
                      <span className="text-muted-foreground ml-2 text-xs">
                        {c.company}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
            {showResults && contactSearch.length >= 2 && contactResults.length === 0 && !searching && (
              <div className="absolute z-50 top-full mt-1 left-0 right-0 rounded-md border bg-popover shadow-md p-3 text-sm text-muted-foreground">
                No contacts found
              </div>
            )}
          </div>
        )}
      </div>

      {/* Amount + Close Date */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-sm font-medium mb-1.5 block">Amount ($)</label>
          <Input
            type="number"
            placeholder="0"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-1.5 block">Close Date</label>
          <Input
            type="date"
            value={closeDate}
            onChange={(e) => setCloseDate(e.target.value)}
          />
        </div>
      </div>

      {/* Source */}
      <div>
        <label className="text-sm font-medium mb-1.5 block">Source</label>
        <Input
          placeholder="e.g. LinkedIn, Referral, Conference..."
          value={source}
          onChange={(e) => setSource(e.target.value)}
        />
      </div>

      {/* Next Action + Date */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-sm font-medium mb-1.5 block">Next Action</label>
          <Input
            placeholder="e.g. Send proposal"
            value={nextAction}
            onChange={(e) => setNextAction(e.target.value)}
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-1.5 block">Action Date</label>
          <Input
            type="date"
            value={nextActionDate}
            onChange={(e) => setNextActionDate(e.target.value)}
          />
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="text-sm font-medium mb-1.5 block">Notes</label>
        <Textarea
          placeholder="Any context or notes about this deal..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
        />
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="outline" onClick={onClose} disabled={saving}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={!title.trim() || saving}>
          {saving ? 'Creating...' : 'Create Deal'}
        </Button>
      </div>
    </div>
  );
}

// ── Stats Bar ──────────────────────────────────────────────────────────

function StatsBar({ deals, stages }: { deals: Deal[]; stages: { name: string; color: string }[] }) {
  const totalValue = deals.reduce((sum, d) => sum + (d.amount ? Number(d.amount) : 0), 0);

  const formatValue = (v: number) => {
    if (v === 0) return '$0';
    if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
    if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
    return `$${v.toLocaleString()}`;
  };

  return (
    <div className="flex items-center gap-4 flex-wrap text-sm">
      <div className="stat-pill">
        <Layers className="w-3.5 h-3.5" />
        {deals.length} deals
      </div>
      <div className="stat-pill">
        <DollarSign className="w-3.5 h-3.5" />
        {formatValue(totalValue)} pipeline value
      </div>
      {stages.map((stage) => {
        const key = stage.name.toLowerCase().replace(/\s+/g, '_');
        const count = deals.filter((d) => d.stage === key).length;
        if (count === 0) return null;
        return (
          <div key={key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: stage.color }}
            />
            {stage.name}: {count}
          </div>
        );
      })}
    </div>
  );
}

// ── Main Page (inner, needs useSearchParams) ───────────────────────────

function PipelinePageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pipelineSlug = searchParams.get('pipeline');

  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [activePipeline, setActivePipeline] = useState<Pipeline | null>(null);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [hideLost, setHideLost] = useState(true);
  const [newDealOpen, setNewDealOpen] = useState(false);
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);
  const [dealDetailOpen, setDealDetailOpen] = useState(false);
  const [contactSheetId, setContactSheetId] = useState<number | null>(null);
  const [contactSheetOpen, setContactSheetOpen] = useState(false);

  // Load pipelines
  useEffect(() => {
    async function loadPipelines() {
      try {
        const res = await fetch('/api/network-intel/pipeline');
        if (!res.ok) throw new Error('Failed to load pipelines');
        const data = await res.json();
        const pipelineList: Pipeline[] = data.pipelines || [];
        setPipelines(pipelineList);

        // Select pipeline from URL or default to first
        const target = pipelineSlug
          ? pipelineList.find((p) => p.slug === pipelineSlug)
          : pipelineList[0];

        if (target) {
          setActivePipeline(target);
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to load';
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    loadPipelines();
  }, [pipelineSlug]);

  // Load deals when pipeline changes
  useEffect(() => {
    if (!activePipeline) return;

    async function loadDeals() {
      try {
        const res = await fetch(
          `/api/network-intel/pipeline/deals?pipeline_id=${activePipeline!.id}`
        );
        if (!res.ok) throw new Error('Failed to load deals');
        const data = await res.json();
        setDeals(data.deals || []);
      } catch (err: unknown) {
        console.error('Failed to load deals:', err);
      }
    }
    loadDeals();
  }, [activePipeline]);

  // Switch pipeline
  const handlePipelineChange = useCallback(
    (slug: string) => {
      const pipeline = pipelines.find((p) => p.slug === slug);
      if (pipeline) {
        setActivePipeline(pipeline);
        setDeals([]);
        router.replace(`/tools/pipeline?pipeline=${slug}`, { scroll: false });
      }
    },
    [pipelines, router]
  );

  // Handle new deal created
  const handleDealCreated = useCallback((deal: Deal) => {
    setDeals((prev) => [...prev, deal]);
  }, []);

  // Handle deal click -- open detail sheet
  const handleDealClick = useCallback((deal: Deal) => {
    setSelectedDeal(deal);
    setDealDetailOpen(true);
  }, []);

  // Handle deal updated from detail sheet
  const handleDealUpdated = useCallback((updated: Deal) => {
    setDeals((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
    setSelectedDeal(updated);
  }, []);

  // Handle "View Contact" from deal detail sheet
  const handleViewContact = useCallback((contactId: number) => {
    setContactSheetId(contactId);
    setContactSheetOpen(true);
  }, []);

  // Filter deals for display (exclude lost if hidden)
  const displayDeals = useMemo(
    () => (hideLost ? deals.filter((d) => d.stage !== 'lost') : deals),
    [deals, hideLost]
  );

  const lostCount = useMemo(() => deals.filter((d) => d.stage === 'lost').length, [deals]);

  // ── Loading State ────────────────────────────────────────────────

  if (loading) {
    return (
      <main className="min-h-screen bg-background">
        <div className="max-w-[1600px] mx-auto p-4">
          <div className="page-header">
            <Link href="/tools/network-intel" className="page-back">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <Columns3 className="w-4 h-4" />
            </div>
            <h1 className="text-lg font-semibold tracking-tight">Pipeline</h1>
          </div>
          <div className="flex items-center justify-center h-64">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              Loading pipelines...
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-background">
        <div className="max-w-[1600px] mx-auto p-4">
          <div className="page-header">
            <Link href="/tools/network-intel" className="page-back">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <h1 className="text-lg font-semibold">Pipeline</h1>
          </div>
          <p className="text-destructive">{error}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="max-w-[1600px] mx-auto p-4">
        {/* Header */}
        <div className="page-header">
          <Link href="/tools/network-intel" className="page-back" aria-label="Back to tools">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            <Columns3 className="w-4 h-4" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight">Pipeline</h1>

          {/* Pipeline selector */}
          <div className="ml-4">
            <Select
              value={activePipeline?.slug || ''}
              onValueChange={handlePipelineChange}
            >
              <SelectTrigger className="w-[220px] h-8 text-sm">
                <SelectValue placeholder="Select pipeline" />
              </SelectTrigger>
              <SelectContent>
                {pipelines.map((p) => (
                  <SelectItem key={p.id} value={p.slug}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {/* Lost toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setHideLost((v) => !v)}
              className={cn(
                'text-xs gap-1.5',
                !hideLost && 'text-muted-foreground'
              )}
            >
              {hideLost ? (
                <>
                  <EyeOff className="w-3.5 h-3.5" />
                  Lost hidden ({lostCount})
                </>
              ) : (
                <>
                  <Eye className="w-3.5 h-3.5" />
                  Showing lost ({lostCount})
                </>
              )}
            </Button>

            {/* New Deal */}
            <Button size="sm" onClick={() => setNewDealOpen(true)} className="gap-1.5">
              <Plus className="w-3.5 h-3.5" />
              New Deal
            </Button>
          </div>
        </div>

        {/* Stats bar */}
        {activePipeline && (
          <div className="mb-4">
            <StatsBar deals={deals} stages={activePipeline.stages} />
          </div>
        )}

        {/* Kanban Board */}
        {activePipeline && (
          <KanbanBoard
            deals={deals}
            stages={activePipeline.stages}
            hideLost={hideLost}
            onDealsChange={setDeals}
            onDealClick={handleDealClick}
          />
        )}

        {/* New Deal Sheet */}
        <Sheet open={newDealOpen} onOpenChange={setNewDealOpen}>
          <SheetContent className="sm:max-w-[480px] overflow-y-auto">
            <SheetHeader>
              <SheetTitle>New Deal</SheetTitle>
            </SheetHeader>
            {activePipeline && (
              <NewDealForm
                pipelineId={activePipeline.id}
                onCreated={handleDealCreated}
                onClose={() => setNewDealOpen(false)}
              />
            )}
          </SheetContent>
        </Sheet>

        {/* Deal Detail Sheet */}
        {activePipeline && (
          <DealDetailSheet
            deal={selectedDeal}
            open={dealDetailOpen}
            stages={activePipeline.stages}
            onOpenChange={setDealDetailOpen}
            onDealUpdated={handleDealUpdated}
            onViewContact={handleViewContact}
          />
        )}

        {/* Contact Detail Sheet (opened from deal detail) */}
        <ContactDetailSheet
          contactId={contactSheetId}
          open={contactSheetOpen}
          onOpenChange={setContactSheetOpen}
        />
      </div>
    </main>
  );
}

// ── Page Export (Suspense boundary for useSearchParams) ─────────────

export default function PipelinePage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-background">
          <div className="max-w-[1600px] mx-auto p-4">
            <div className="page-header">
              <Link href="/tools/network-intel" className="page-back">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <Columns3 className="w-4 h-4" />
              </div>
              <h1 className="text-lg font-semibold tracking-tight">Pipeline</h1>
            </div>
          </div>
        </main>
      }
    >
      <PipelinePageInner />
    </Suspense>
  );
}
