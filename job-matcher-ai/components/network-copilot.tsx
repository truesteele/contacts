'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { NLQueryBar } from '@/components/nl-query-bar';
import { FilterBar } from '@/components/filter-bar';
import { ContactsTable } from '@/components/contacts-table';
import { ContactDetailSheet } from '@/components/contact-detail-sheet';
import { OutreachDrawer } from '@/components/outreach-drawer';
import { ListManager } from '@/components/list-manager';
import { OutreachStatusValue } from '@/components/pipeline-status';
import { FilterState, ProspectList } from '@/lib/types';
import { NetworkContact } from '@/lib/supabase';
import {
  AlertCircle,
  RefreshCw,
  Download,
  X,
  FolderOpen,
  Mail,
  Network,
  Sparkles,
  Search,
  Users,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

type Phase = 'idle' | 'parsing' | 'searching' | 'done' | 'error';

export function NetworkCopilot() {
  const [filters, setFilters] = useState<FilterState>({});
  const [explanation, setExplanation] = useState('');
  const [contacts, setContacts] = useState<NetworkContact[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [phase, setPhase] = useState<Phase>('idle');
  const [error, setError] = useState('');
  const [lastQuery, setLastQuery] = useState('');
  const [detailContactId, setDetailContactId] = useState<number | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [outreachOpen, setOutreachOpen] = useState(false);

  // List mode state
  const [activeList, setActiveList] = useState<ProspectList | null>(null);
  const [memberStatuses, setMemberStatuses] = useState<Map<number, OutreachStatusValue>>(new Map());
  const [listLoading, setListLoading] = useState(false);

  // Abort controller for cancelling in-flight requests
  const abortRef = useRef<AbortController | null>(null);

  // Global Escape key handler to close sheets/drawers
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (outreachOpen) {
          setOutreachOpen(false);
        } else if (detailOpen) {
          setDetailOpen(false);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [outreachOpen, detailOpen]);

  const executeSearch = useCallback(async (searchFilters: FilterState, signal?: AbortSignal) => {
    setPhase('searching');
    setError('');

    try {
      const res = await fetch('/api/network-intel/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filters: searchFilters }),
        signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `Search failed (${res.status})`);
      }

      const data = await res.json();
      setContacts(data.contacts || []);
      setPhase('done');
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      setError(err.message || 'Search failed');
      setPhase('error');
    }
  }, []);

  const handleSearch = useCallback(
    async (query: string) => {
      // Cancel any in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      // Exit list mode on new search
      setActiveList(null);
      setMemberStatuses(new Map());

      setLastQuery(query);
      setPhase('parsing');
      setError('');
      setContacts([]);
      setSelectedIds(new Set());

      try {
        const res = await fetch('/api/network-intel/parse-filters', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.error || `Filter parsing failed (${res.status})`);
        }

        const data = await res.json();
        setFilters(data.filters || {});
        setExplanation(data.explanation || '');

        // Now execute search with the parsed filters
        await executeSearch(data.filters || {}, controller.signal);
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        setError(err.message || 'Failed to process query');
        setPhase('error');
      }
    },
    [executeSearch]
  );

  const handleFilterChange = useCallback(
    (updatedFilters: FilterState) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setFilters(updatedFilters);
      executeSearch(updatedFilters, controller.signal);
    },
    [executeSearch]
  );

  const handleContactClick = useCallback((contactId: number) => {
    setDetailContactId(contactId);
    setDetailOpen(true);
  }, []);

  const handleLoadList = useCallback(async (list: ProspectList) => {
    setListLoading(true);
    setPhase('searching');
    setError('');
    setSelectedIds(new Set());
    setFilters({});
    setExplanation('');

    try {
      const res = await fetch(`/api/network-intel/prospect-lists/${list.id}`);
      if (!res.ok) throw new Error('Failed to load list');

      const data = await res.json();
      const members = data.members || [];

      // Extract contacts and build status map
      const contactList: NetworkContact[] = [];
      const statusMap = new Map<number, OutreachStatusValue>();

      for (const member of members) {
        if (member.contact) {
          contactList.push(member.contact as NetworkContact);
          statusMap.set(
            member.contact_id,
            (member.outreach_status || 'not_contacted') as OutreachStatusValue
          );
        }
      }

      setContacts(contactList);
      setMemberStatuses(statusMap);
      setActiveList({ ...list, member_count: contactList.length });
      setPhase('done');
    } catch (err: any) {
      setError(err.message || 'Failed to load list');
      setPhase('error');
    } finally {
      setListLoading(false);
    }
  }, []);

  const handleStatusChange = useCallback(
    (contactId: number, status: OutreachStatusValue) => {
      setMemberStatuses((prev) => {
        const next = new Map(prev);
        next.set(contactId, status);
        return next;
      });
    },
    []
  );

  const handleExitList = useCallback(() => {
    setActiveList(null);
    setMemberStatuses(new Map());
    setContacts([]);
    setSelectedIds(new Set());
    setPhase('idle');
    setFilters({});
    setExplanation('');
  }, []);

  const handleExportCSV = useCallback(() => {
    if (contacts.length === 0) return;

    const headers = [
      'First Name',
      'Last Name',
      'Company',
      'Position',
      'City',
      'State',
      'Email',
      'LinkedIn',
      'Proximity Score',
      'Proximity Tier',
      'Capacity Score',
      'Capacity Tier',
      'Kindora Type',
      'Outdoorithm Fit',
    ];

    const rows = contacts.map((c) => [
      c.first_name || '',
      c.last_name || '',
      c.company || '',
      c.position || '',
      c.city || '',
      c.state || '',
      c.email || '',
      c.linkedin_url || '',
      c.ai_proximity_score ?? '',
      c.ai_proximity_tier || '',
      c.ai_capacity_score ?? '',
      c.ai_capacity_tier || '',
      c.ai_kindora_prospect_type || '',
      c.ai_outdoorithm_fit || '',
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
    const filename = activeList
      ? `${activeList.name.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`
      : `network_search_${new Date().toISOString().split('T')[0]}.csv`;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [contacts, activeList]);

  const isLoading = phase === 'parsing' || phase === 'searching';
  const showResults = phase === 'done' || (phase === 'searching' && contacts.length > 0);

  return (
    <Card className="flex flex-col h-full p-4 gap-4">
      {/* Query bar */}
      <NLQueryBar onSearch={handleSearch} isLoading={isLoading} />

      {/* Active list banner */}
      {activeList && (
        <div className="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-sm transition-all duration-200">
          <FolderOpen className="w-4 h-4 text-primary shrink-0" />
          <span className="font-medium">{activeList.name}</span>
          <span className="text-muted-foreground">
            — {activeList.member_count ?? contacts.length} contacts
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto h-6 px-2 text-xs"
            onClick={handleExitList}
          >
            <X className="w-3 h-3 mr-1" />
            Close
          </Button>
        </div>
      )}

      {/* Loading indicators */}
      {phase === 'parsing' && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            <span>Interpreting your query...</span>
          </div>
          {/* Skeleton filter bar */}
          <div className="flex gap-2">
            <div className="h-6 w-24 rounded-full bg-muted animate-pulse" />
            <div className="h-6 w-32 rounded-full bg-muted animate-pulse" />
            <div className="h-6 w-20 rounded-full bg-muted animate-pulse" />
          </div>
        </div>
      )}
      {phase === 'searching' && !listLoading && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            <span>Searching {contacts.length > 0 ? `${contacts.length}+` : ''} contacts...</span>
          </div>
          {/* Skeleton table rows */}
          <div className="space-y-2 rounded-md border p-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-4 h-4 rounded bg-muted animate-pulse" />
                <div className="h-4 w-32 rounded bg-muted animate-pulse" />
                <div className="h-4 w-24 rounded bg-muted animate-pulse" />
                <div className="h-4 w-20 rounded bg-muted animate-pulse" />
                <div className="h-4 w-16 rounded bg-muted animate-pulse" />
                <div className="ml-auto h-5 w-16 rounded-full bg-muted animate-pulse" />
              </div>
            ))}
          </div>
        </div>
      )}
      {listLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          <span>Loading list...</span>
        </div>
      )}

      {/* Error state */}
      {phase === 'error' && (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/50 bg-destructive/5 p-4 text-sm">
          <AlertCircle className="w-5 h-5 text-destructive shrink-0" />
          <div className="flex-1 space-y-1">
            <p className="font-medium text-destructive">Something went wrong</p>
            <p className="text-muted-foreground">{error}</p>
          </div>
          {lastQuery && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSearch(lastQuery)}
              className="shrink-0 gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Retry
            </Button>
          )}
        </div>
      )}

      {/* Filter bar (only for search results, not list mode) */}
      {!activeList && phase !== 'idle' && phase !== 'parsing' && (
        <FilterBar
          filters={filters}
          explanation={explanation}
          totalCount={contacts.length}
          onFilterChange={handleFilterChange}
        />
      )}

      {/* Action bar */}
      {showResults && contacts.length > 0 && (
        <div className="flex items-center gap-2">
          <ListManager
            selectedIds={selectedIds}
            onLoadList={handleLoadList}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            className="gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOutreachOpen(true)}
            disabled={selectedIds.size === 0}
            className="gap-1.5"
          >
            <Mail className="w-3.5 h-3.5" />
            Draft Outreach
          </Button>

          {selectedIds.size > 0 && (
            <Badge variant="secondary" className="ml-auto text-xs">
              {selectedIds.size} selected
            </Badge>
          )}
        </div>
      )}

      {/* Results table */}
      {showResults && (
        <ContactsTable
          contacts={contacts}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
          onContactClick={handleContactClick}
          listId={activeList?.id}
          memberStatuses={activeList ? memberStatuses : undefined}
          onStatusChange={handleStatusChange}
        />
      )}

      {/* Empty search results */}
      {phase === 'done' && contacts.length === 0 && !activeList && (
        <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
          <Search className="w-10 h-10 text-muted-foreground/40" />
          <div className="space-y-1">
            <p className="font-medium text-muted-foreground">No contacts found</p>
            <p className="text-sm text-muted-foreground/70">
              Try adjusting your query or removing some filters to broaden the search.
            </p>
          </div>
          {lastQuery && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSearch(lastQuery)}
              className="mt-2 gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Try Again
            </Button>
          )}
        </div>
      )}

      {/* Idle welcome state */}
      {phase === 'idle' && !activeList && (
        <div className="flex flex-col items-center justify-center py-12 text-center space-y-6">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
              <Network className="w-8 h-8 text-primary/70" />
            </div>
            <div className="absolute -bottom-1 -right-1 w-7 h-7 rounded-lg bg-background border flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-primary" />
            </div>
          </div>
          <div className="space-y-2 max-w-md">
            <h3 className="text-lg font-semibold">Network Copilot</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Search your network of 2,400+ contacts using natural language.
              Find the right people for fundraisers, introductions, partnerships, and more.
            </p>
          </div>
          <div className="flex items-center gap-6 text-xs text-muted-foreground/60">
            <div className="flex items-center gap-1.5">
              <Search className="w-3.5 h-3.5" />
              AI-Powered Search
            </div>
            <div className="flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5" />
              Prospect Lists
            </div>
            <div className="flex items-center gap-1.5">
              <Mail className="w-3.5 h-3.5" />
              Draft Outreach
            </div>
          </div>
        </div>
      )}

      {/* Contact detail slide-out */}
      <ContactDetailSheet
        contactId={detailContactId}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />

      {/* Outreach drawer */}
      <OutreachDrawer
        open={outreachOpen}
        onOpenChange={setOutreachOpen}
        contacts={contacts.filter((c) => selectedIds.has(parseInt(String(c.id), 10)))}
        listId={activeList?.id}
      />
    </Card>
  );
}
