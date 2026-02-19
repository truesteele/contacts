'use client';

import { useState, useMemo, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { NetworkContact } from '@/lib/supabase';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Building2,
  MapPin,
} from 'lucide-react';
import { PipelineStatus, OutreachStatusValue } from '@/components/pipeline-status';

// ── Types ──────────────────────────────────────────────────────────────

type SortField =
  | 'name'
  | 'company'
  | 'position'
  | 'location'
  | 'proximity'
  | 'capacity'
  | 'kindora'
  | 'outdoorithm';

interface ContactsTableProps {
  contacts: NetworkContact[];
  selectedIds: Set<number>;
  onSelectionChange: (ids: Set<number>) => void;
  onContactClick: (contactId: number) => void;
  listId?: string;
  memberStatuses?: Map<number, OutreachStatusValue>;
  onStatusChange?: (contactId: number, status: OutreachStatusValue) => void;
}

// ── Tier badge colors ──────────────────────────────────────────────────

const PROXIMITY_TIER_COLORS: Record<string, string> = {
  inner_circle: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/40 dark:text-green-300 dark:border-green-800',
  close: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300 dark:border-blue-800',
  warm: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300 dark:border-yellow-800',
  familiar: 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/40 dark:text-orange-300 dark:border-orange-800',
  distant: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800/40 dark:text-gray-400 dark:border-gray-700',
};

const CAPACITY_TIER_COLORS: Record<string, string> = {
  high: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/40 dark:text-green-300 dark:border-green-800',
  medium: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300 dark:border-blue-800',
  low: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300 dark:border-yellow-800',
  none: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800/40 dark:text-gray-400 dark:border-gray-700',
};

const OUTDOORITHM_COLORS: Record<string, string> = {
  high: 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-800',
  medium: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800',
  low: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800/40 dark:text-gray-400 dark:border-gray-700',
  none: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800/40 dark:text-gray-400 dark:border-gray-700',
};

const TIER_DISPLAY: Record<string, string> = {
  inner_circle: 'Inner Circle',
  close: 'Close',
  warm: 'Warm',
  familiar: 'Familiar',
  distant: 'Distant',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  none: 'None',
  enterprise_prospect: 'Enterprise',
  sme_prospect: 'SME',
  partner: 'Partner',
  investor: 'Investor',
  advisor: 'Advisor',
  talent: 'Talent',
};

// ── Helpers ────────────────────────────────────────────────────────────

function getContactId(contact: NetworkContact): number {
  return typeof contact.id === 'string' ? parseInt(contact.id, 10) : (contact.id as unknown as number);
}

function getContactName(contact: NetworkContact): string {
  return `${contact.first_name || ''} ${contact.last_name || ''}`.trim() || '—';
}

function getSortValue(contact: NetworkContact, field: SortField): string | number {
  switch (field) {
    case 'name':
      return `${contact.first_name || ''} ${contact.last_name || ''}`.toLowerCase();
    case 'company':
      return (contact.company || '').toLowerCase();
    case 'position':
      return (contact.position || '').toLowerCase();
    case 'location':
      return `${contact.state || ''} ${contact.city || ''}`.toLowerCase();
    case 'proximity':
      return contact.ai_proximity_score ?? -1;
    case 'capacity':
      return contact.ai_capacity_score ?? -1;
    case 'kindora':
      return contact.ai_kindora_prospect_score ?? -1;
    case 'outdoorithm':
      return (contact.ai_outdoorithm_fit || 'zzz').toLowerCase();
    default:
      return '';
  }
}

// ── Component ──────────────────────────────────────────────────────────

export function ContactsTable({
  contacts,
  selectedIds,
  onSelectionChange,
  onContactClick,
  listId,
  memberStatuses,
  onStatusChange,
}: ContactsTableProps) {
  const showPipeline = !!listId && !!memberStatuses;
  const [sortBy, setSortBy] = useState<SortField>('proximity');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const handleSort = useCallback((field: SortField) => {
    setSortBy((prev) => {
      if (prev === field) {
        setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
        return prev;
      }
      setSortOrder(field === 'name' || field === 'company' || field === 'position' || field === 'location' ? 'asc' : 'desc');
      return field;
    });
  }, []);

  const sortedContacts = useMemo(() => {
    const sorted = [...contacts].sort((a, b) => {
      const va = getSortValue(a, sortBy);
      const vb = getSortValue(b, sortBy);

      let cmp: number;
      if (typeof va === 'number' && typeof vb === 'number') {
        cmp = va - vb;
      } else {
        cmp = String(va).localeCompare(String(vb));
      }
      return sortOrder === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [contacts, sortBy, sortOrder]);

  const allSelected = contacts.length > 0 && contacts.every((c) => selectedIds.has(getContactId(c)));
  const someSelected = contacts.some((c) => selectedIds.has(getContactId(c))) && !allSelected;

  const toggleSelectAll = useCallback(() => {
    if (allSelected) {
      onSelectionChange(new Set());
    } else {
      onSelectionChange(new Set(contacts.map(getContactId)));
    }
  }, [allSelected, contacts, onSelectionChange]);

  const toggleSelect = useCallback(
    (contactId: number) => {
      const next = new Set(selectedIds);
      if (next.has(contactId)) {
        next.delete(contactId);
      } else {
        next.add(contactId);
      }
      onSelectionChange(next);
    },
    [selectedIds, onSelectionChange]
  );

  function getSortIcon(field: SortField) {
    if (sortBy !== field) return <ArrowUpDown className="w-3.5 h-3.5 ml-1 opacity-40" />;
    return sortOrder === 'asc' ? (
      <ArrowUp className="w-3.5 h-3.5 ml-1" />
    ) : (
      <ArrowDown className="w-3.5 h-3.5 ml-1" />
    );
  }

  if (contacts.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        No contacts to display. Try a different search query.
      </div>
    );
  }

  return (
    <ScrollArea className="h-[calc(100vh-360px)] rounded-md border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 sticky top-0 z-10">
          <tr className="border-b">
            <th className="w-10 p-2 text-center">
              <Checkbox
                checked={allSelected}
                ref={(el) => {
                  if (el) {
                    // Set indeterminate via DOM since Radix doesn't support it as a prop
                    const input = el.querySelector('button');
                    if (input) input.setAttribute('data-indeterminate', someSelected ? 'true' : 'false');
                  }
                }}
                onCheckedChange={toggleSelectAll}
                aria-label="Select all contacts"
              />
            </th>
            {([
              ['name', 'Name'],
              ['company', 'Company'],
              ['position', 'Position'],
              ['location', 'Location'],
              ['proximity', 'Proximity'],
              ['capacity', 'Capacity'],
              ['kindora', 'Kindora'],
              ['outdoorithm', 'Outdoorithm'],
            ] as [SortField, string][]).map(([field, label]) => (
              <th key={field} className="text-left p-2">
                <button
                  onClick={() => handleSort(field)}
                  className="flex items-center font-medium text-xs uppercase tracking-wide hover:text-foreground text-muted-foreground transition-colors"
                >
                  {label}
                  {getSortIcon(field)}
                </button>
              </th>
            ))}
            {showPipeline && (
              <th className="text-left p-2">
                <span className="font-medium text-xs uppercase tracking-wide text-muted-foreground">
                  Status
                </span>
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {sortedContacts.map((contact) => {
            const cid = getContactId(contact);
            const isSelected = selectedIds.has(cid);

            return (
              <tr
                key={cid}
                className={cn(
                  'border-b transition-colors cursor-pointer',
                  isSelected
                    ? 'bg-primary/5 hover:bg-primary/10'
                    : 'hover:bg-muted/50'
                )}
                onClick={() => onContactClick(cid)}
              >
                <td className="p-2 text-center" onClick={(e) => e.stopPropagation()}>
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => toggleSelect(cid)}
                    aria-label={`Select ${getContactName(contact)}`}
                  />
                </td>

                {/* Name */}
                <td className="p-2 max-w-[180px]">
                  <div className="font-medium truncate">{getContactName(contact)}</div>
                  {contact.headline && (
                    <div className="text-xs text-muted-foreground truncate">
                      {contact.headline}
                    </div>
                  )}
                </td>

                {/* Company */}
                <td className="p-2 max-w-[150px]">
                  {contact.company ? (
                    <div className="flex items-center gap-1.5 truncate">
                      <Building2 className="w-3 h-3 text-muted-foreground shrink-0" />
                      <span className="truncate">{contact.company}</span>
                    </div>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>

                {/* Position */}
                <td className="p-2 max-w-[150px]">
                  <span className="truncate block">{contact.position || '—'}</span>
                </td>

                {/* Location */}
                <td className="p-2 max-w-[120px]">
                  {contact.city || contact.state ? (
                    <div className="flex items-center gap-1.5 truncate">
                      <MapPin className="w-3 h-3 text-muted-foreground shrink-0" />
                      <span className="truncate">
                        {[contact.city, contact.state].filter(Boolean).join(', ')}
                      </span>
                    </div>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>

                {/* Proximity */}
                <td className="p-2">
                  {contact.ai_proximity_tier ? (
                    <div className="flex items-center gap-1.5">
                      <Badge
                        variant="outline"
                        className={cn(
                          'text-[10px] px-1.5 py-0 font-medium',
                          PROXIMITY_TIER_COLORS[contact.ai_proximity_tier] || ''
                        )}
                      >
                        {TIER_DISPLAY[contact.ai_proximity_tier] || contact.ai_proximity_tier}
                      </Badge>
                      {contact.ai_proximity_score != null && (
                        <span className="text-xs text-muted-foreground tabular-nums">
                          {contact.ai_proximity_score}
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>

                {/* Capacity */}
                <td className="p-2">
                  {contact.ai_capacity_tier ? (
                    <div className="flex items-center gap-1.5">
                      <Badge
                        variant="outline"
                        className={cn(
                          'text-[10px] px-1.5 py-0 font-medium',
                          CAPACITY_TIER_COLORS[contact.ai_capacity_tier] || ''
                        )}
                      >
                        {TIER_DISPLAY[contact.ai_capacity_tier] || contact.ai_capacity_tier}
                      </Badge>
                      {contact.ai_capacity_score != null && (
                        <span className="text-xs text-muted-foreground tabular-nums">
                          {contact.ai_capacity_score}
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>

                {/* Kindora Type */}
                <td className="p-2">
                  {contact.ai_kindora_prospect_type ? (
                    <Badge
                      variant="outline"
                      className="text-[10px] px-1.5 py-0 font-medium bg-violet-100 text-violet-800 border-violet-200 dark:bg-violet-900/40 dark:text-violet-300 dark:border-violet-800"
                    >
                      {TIER_DISPLAY[contact.ai_kindora_prospect_type] || contact.ai_kindora_prospect_type}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>

                {/* Outdoorithm Fit */}
                <td className="p-2">
                  {contact.ai_outdoorithm_fit ? (
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-[10px] px-1.5 py-0 font-medium',
                        OUTDOORITHM_COLORS[contact.ai_outdoorithm_fit] || ''
                      )}
                    >
                      {TIER_DISPLAY[contact.ai_outdoorithm_fit] || contact.ai_outdoorithm_fit}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>

                {/* Pipeline Status (only for saved lists) */}
                {showPipeline && (
                  <td className="p-2">
                    <PipelineStatus
                      contactId={cid}
                      listId={listId!}
                      status={memberStatuses!.get(cid) || 'not_contacted'}
                      onStatusChange={onStatusChange || (() => {})}
                    />
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </ScrollArea>
  );
}
