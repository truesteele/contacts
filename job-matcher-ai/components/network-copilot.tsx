'use client';

import { useState, useCallback, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { NLQueryBar } from '@/components/nl-query-bar';
import { FilterBar } from '@/components/filter-bar';
import { ContactsTable } from '@/components/contacts-table';
import { FilterState } from '@/lib/types';
import { NetworkContact } from '@/lib/supabase';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

type Phase = 'idle' | 'parsing' | 'searching' | 'done' | 'error';

export function NetworkCopilot() {
  const [filters, setFilters] = useState<FilterState>({});
  const [explanation, setExplanation] = useState('');
  const [contacts, setContacts] = useState<NetworkContact[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [phase, setPhase] = useState<Phase>('idle');
  const [error, setError] = useState('');
  const [lastQuery, setLastQuery] = useState('');

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
    // Placeholder — contact detail sheet will be wired in US-007
    console.log('Contact clicked:', contactId);
  }, []);

  const isLoading = phase === 'parsing' || phase === 'searching';

  return (
    <Card className="flex flex-col h-full p-4 gap-4">
      {/* Query bar */}
      <NLQueryBar onSearch={handleSearch} isLoading={isLoading} />

      {/* Loading indicator */}
      {phase === 'parsing' && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
          <div className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
          Interpreting your query...
        </div>
      )}
      {phase === 'searching' && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
          <div className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
          Searching contacts...
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

      {/* Filter bar */}
      {phase !== 'idle' && phase !== 'parsing' && (
        <FilterBar
          filters={filters}
          explanation={explanation}
          totalCount={contacts.length}
          onFilterChange={handleFilterChange}
        />
      )}

      {/* Results table */}
      {phase === 'done' && (
        <ContactsTable
          contacts={contacts}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
          onContactClick={handleContactClick}
        />
      )}
    </Card>
  );
}
