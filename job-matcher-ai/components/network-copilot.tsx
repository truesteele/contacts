'use client';

import { useState, useCallback, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { NLQueryBar } from '@/components/nl-query-bar';
import { FilterBar } from '@/components/filter-bar';
import { ContactsTable } from '@/components/contacts-table';
import { ContactDetailSheet } from '@/components/contact-detail-sheet';
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

  // List mode state
  const [activeList, setActiveList] = useState<ProspectList | null>(null);
  const [memberStatuses, setMemberStatuses] = useState<Map<number, OutreachStatusValue>>(new Map());
  const [listLoading, setListLoading] = useState(false);

  // Abort controller for cancelling in-flight requests
  const abortRef = useRef<AbortController | null>(null);

  const executeSearch = useCallback(async (searchFilters: FilterState) => {
    setPhase('searching');
    setError('');

    try {
      const res = await fetch('/api/network-intel/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filters: searchFilters }),
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
      abortRef.current = new AbortController();

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
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.error || `Filter parsing failed (${res.status})`);
        }

        const data = await res.json();
        setFilters(data.filters || {});
        setExplanation(data.explanation || '');

        // Now execute search with the parsed filters
        await executeSearch(data.filters || {});
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
      setFilters(updatedFilters);
      executeSearch(updatedFilters);
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
        <div className="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-sm">
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

      {/* Loading indicator */}
      {phase === 'parsing' && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
          <div className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
          Interpreting your query...
        </div>
      )}
      {phase === 'searching' && !listLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
          <div className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
          Searching contacts...
        </div>
      )}
      {listLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
          <div className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
          Loading list...
        </div>
      )}

      {/* Error state */}
      {phase === 'error' && (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/50 bg-destructive/5 p-3 text-sm">
          <AlertCircle className="w-4 h-4 text-destructive shrink-0" />
          <span className="text-destructive flex-1">{error}</span>
          {lastQuery && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSearch(lastQuery)}
              className="shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
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

      {/* Contact detail slide-out */}
      <ContactDetailSheet
        contactId={detailContactId}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
    </Card>
  );
}
