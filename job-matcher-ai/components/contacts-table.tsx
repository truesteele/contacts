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
  | 'familiarity'
  | 'last_contact'
  | 'capacity'
  | 'kindora'
  | 'outdoorithm'
  | 'ask_readiness';

interface ContactsTableProps {
  contacts: NetworkContact[];
  selectedIds: Set<number>;
  onSelectionChange: (ids: Set<number>) => void;
  onContactClick: (contactId: number) => void;
  activeGoal?: string;
  listId?: string;
  memberStatuses?: Map<number, OutreachStatusValue>;
  onStatusChange?: (contactId: number, status: OutreachStatusValue) => void;
}

// ── Tier badge colors ──────────────────────────────────────────────────

const ASK_READINESS_TIER_COLORS: Record<string, string> = {
  ready_now: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/40 dark:text-green-300 dark:border-green-800',
  cultivate_first: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300 dark:border-yellow-800',
  long_term: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800/40 dark:text-gray-400 dark:border-gray-700',
  not_a_fit: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/40 dark:text-red-300 dark:border-red-800',
};

const CAPACITY_TIER_COLORS: Record<string, string> = {
  major_donor: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/40 dark:text-green-300 dark:border-green-800',
  mid_level: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300 dark:border-blue-800',
  grassroots: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300 dark:border-yellow-800',
  unknown: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800/40 dark:text-gray-400 dark:border-gray-700',
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
  acquaintance: 'Acquaintance',
  distant: 'Distant',
  major_donor: 'Major Donor',
  mid_level: 'Mid-Level',
  grassroots: 'Grassroots',
  unknown: 'Unknown',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  none: 'None',
  enterprise_buyer: 'Enterprise Buyer',
  champion: 'Champion',
  influencer: 'Influencer',
  not_relevant: 'Not Relevant',
  ready_now: 'Ready Now',
  cultivate_first: 'Cultivate',
  long_term: 'Long Term',
  not_a_fit: 'Not a Fit',
};

// ── Helpers ────────────────────────────────────────────────────────────

function getContactId(contact: NetworkContact): number {
  return typeof contact.id === 'string' ? parseInt(contact.id, 10) : (contact.id as unknown as number);
}

function getContactName(contact: NetworkContact): string {
  return `${contact.first_name || ''} ${contact.last_name || ''}`.trim() || '—';
}

function FamiliarityDots({ rating }: { rating: number }) {
  const max = 4;
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: max }, (_, i) => (
        <div
          key={i}
          className={cn(
            'w-2 h-2 rounded-full',
            i < rating
              ? 'bg-blue-500 dark:bg-blue-400'
              : 'bg-gray-200 dark:bg-gray-700'
          )}
        />
      ))}
      <span className="ml-1 text-xs text-muted-foreground tabular-nums">{rating}</span>
    </div>
  );
}

function getRecencyColor(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  const now = new Date();
  const monthsAgo = (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24 * 30);
  if (monthsAgo < 3) return 'text-green-600 dark:text-green-400';
  if (monthsAgo < 12) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-gray-500 dark:text-gray-400';
}

function formatShortDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  const now = new Date();
  const sameYear = d.getFullYear() === now.getFullYear();
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    ...(sameYear ? {} : { year: '2-digit' }),
  });
}

function getAskReadinessForGoal(contact: NetworkContact, goal?: string): { score: number; tier: string } | null {
  if (!goal || !contact.ask_readiness) return null;
  const goalData = contact.ask_readiness[goal];
  if (!goalData || typeof goalData.score !== 'number') return null;
  return { score: goalData.score, tier: goalData.tier || 'unknown' };
}

function getSortValue(contact: NetworkContact, field: SortField, goal?: string): string | number {
  switch (field) {
    case 'name':
      return `${contact.first_name || ''} ${contact.last_name || ''}`.toLowerCase();
    case 'company':
      return (contact.company || '').toLowerCase();
    case 'position':
      return (contact.position || '').toLowerCase();
    case 'location':
      return `${contact.state || ''} ${contact.city || ''}`.toLowerCase();
    case 'familiarity':
      return contact.familiarity_rating ?? -1;
    case 'last_contact':
      return contact.comms_last_date ? new Date(contact.comms_last_date).getTime() : -1;
    case 'capacity':
      return contact.ai_capacity_score ?? -1;
    case 'kindora':
      return contact.ai_kindora_prospect_score ?? -1;
    case 'outdoorithm':
      return (contact.ai_outdoorithm_fit || 'zzz').toLowerCase();
    case 'ask_readiness': {
      const ar = getAskReadinessForGoal(contact, goal);
      return ar?.score ?? -1;
    }
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
  activeGoal,
  listId,
  memberStatuses,
  onStatusChange,
}: ContactsTableProps) {
  const showPipeline = !!listId && !!memberStatuses;
  const [sortBy, setSortBy] = useState<SortField>('familiarity');
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
      const va = getSortValue(a, sortBy, activeGoal);
      const vb = getSortValue(b, sortBy, activeGoal);

      let cmp: number;
      if (typeof va === 'number' && typeof vb === 'number') {
        cmp = va - vb;
      } else {
        cmp = String(va).localeCompare(String(vb));
      }
      return sortOrder === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [contacts, sortBy, sortOrder, activeGoal]);

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
    return null;
  }

  return (
    <ScrollArea className="h-[calc(100vh-360px)] min-h-[300px] rounded-md border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 sticky top-0 z-10">
          <tr className="border-b">
            <th className="w-10 p-2 text-center">
              <Checkbox
                checked={allSelected}
                ref={(el) => {
                  if (el) {
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
              ['familiarity', 'Familiarity'],
              ['last_contact', 'Last Contact'],
              ['capacity', 'Capacity'],
              ['kindora', 'Kindora'],
              ['outdoorithm', 'Outdoorithm'],
              ...(activeGoal ? [['ask_readiness', 'Ask Readiness'] as [SortField, string]] : []),
            ] as [SortField, string][]).map(([field, label]) => (
              <th key={field} className="text-left p-2">
                <button
                  onClick={() => handleSort(field)}
                  className={cn(
                    'flex items-center font-medium text-xs uppercase tracking-wide transition-colors',
                    sortBy === field
                      ? 'text-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
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
                  'border-b transition-colors duration-150 cursor-pointer group',
                  isSelected
                    ? 'bg-primary/5 hover:bg-primary/10'
                    : 'hover:bg-muted/50 active:bg-muted/70'
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

                {/* Familiarity */}
                <td className="p-2">
                  {contact.familiarity_rating != null && contact.familiarity_rating > 0 ? (
                    <FamiliarityDots rating={contact.familiarity_rating} />
                  ) : (
                    <span className="text-muted-foreground text-xs">—</span>
                  )}
                </td>

                {/* Last Contact */}
                <td className="p-2">
                  {contact.comms_last_date ? (
                    <span className={cn('text-xs tabular-nums', getRecencyColor(contact.comms_last_date))}>
                      {formatShortDate(contact.comms_last_date)}
                    </span>
                  ) : (
                    <span className="text-muted-foreground text-xs">—</span>
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

                {/* Ask Readiness (only when goal filter is active) */}
                {activeGoal && (() => {
                  const ar = getAskReadinessForGoal(contact, activeGoal);
                  return (
                    <td className="p-2">
                      {ar ? (
                        <div className="flex items-center gap-1.5">
                          <Badge
                            variant="outline"
                            className={cn(
                              'text-[10px] px-1.5 py-0 font-medium',
                              ASK_READINESS_TIER_COLORS[ar.tier] || ''
                            )}
                          >
                            {TIER_DISPLAY[ar.tier] || ar.tier}
                          </Badge>
                          <span className="text-xs text-muted-foreground tabular-nums">
                            {ar.score}
                          </span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </td>
                  );
                })()}

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
