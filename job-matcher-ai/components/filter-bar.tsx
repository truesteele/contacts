'use client';

import { X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { FilterState } from '@/lib/types';

interface FilterBarProps {
  filters: FilterState;
  explanation?: string;
  totalCount?: number;
  onFilterChange: (filters: FilterState) => void;
}

interface FilterChip {
  key: keyof FilterState;
  label: string;
  value: string;
  colorClass: string;
}

const TIER_LABELS: Record<string, string> = {
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
};

const KINDORA_LABELS: Record<string, string> = {
  enterprise_buyer: 'Enterprise Buyer',
  champion: 'Champion',
  influencer: 'Influencer',
  not_relevant: 'Not Relevant',
};

function formatTierList(tiers: string[]): string {
  return tiers.map((t) => TIER_LABELS[t] || t).join(', ');
}

function formatKindoraList(types: string[]): string {
  return types.map((t) => KINDORA_LABELS[t] || t).join(', ');
}

function buildChips(filters: FilterState): FilterChip[] {
  const chips: FilterChip[] = [];

  if (filters.proximity_min != null) {
    chips.push({
      key: 'proximity_min',
      label: 'Proximity',
      value: `${filters.proximity_min}+`,
      colorClass: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300 dark:border-blue-800',
    });
  }

  if (filters.proximity_tiers?.length) {
    chips.push({
      key: 'proximity_tiers',
      label: 'Proximity Tier',
      value: formatTierList(filters.proximity_tiers),
      colorClass: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300 dark:border-blue-800',
    });
  }

  if (filters.capacity_min != null) {
    chips.push({
      key: 'capacity_min',
      label: 'Capacity',
      value: `${filters.capacity_min}+`,
      colorClass: 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-800',
    });
  }

  if (filters.capacity_tiers?.length) {
    chips.push({
      key: 'capacity_tiers',
      label: 'Capacity Tier',
      value: formatTierList(filters.capacity_tiers),
      colorClass: 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-800',
    });
  }

  if (filters.outdoorithm_fit?.length) {
    chips.push({
      key: 'outdoorithm_fit',
      label: 'Outdoorithm',
      value: formatTierList(filters.outdoorithm_fit),
      colorClass: 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-800',
    });
  }

  if (filters.kindora_type?.length) {
    chips.push({
      key: 'kindora_type',
      label: 'Kindora',
      value: formatKindoraList(filters.kindora_type),
      colorClass: 'bg-violet-100 text-violet-800 border-violet-200 dark:bg-violet-900/40 dark:text-violet-300 dark:border-violet-800',
    });
  }

  if (filters.company_keyword) {
    chips.push({
      key: 'company_keyword',
      label: 'Company',
      value: filters.company_keyword,
      colorClass: 'bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800/40 dark:text-slate-300 dark:border-slate-700',
    });
  }

  if (filters.name_search) {
    chips.push({
      key: 'name_search',
      label: 'Name',
      value: filters.name_search,
      colorClass: 'bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800/40 dark:text-slate-300 dark:border-slate-700',
    });
  }

  if (filters.location_state) {
    chips.push({
      key: 'location_state',
      label: 'State',
      value: filters.location_state,
      colorClass: 'bg-rose-100 text-rose-800 border-rose-200 dark:bg-rose-900/40 dark:text-rose-300 dark:border-rose-800',
    });
  }

  if (filters.semantic_query) {
    chips.push({
      key: 'semantic_query',
      label: 'Topic',
      value: filters.semantic_query,
      colorClass: 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/40 dark:text-purple-300 dark:border-purple-800',
    });
  }

  return chips;
}

export function FilterBar({ filters, explanation, totalCount, onFilterChange }: FilterBarProps) {
  const chips = buildChips(filters);

  if (chips.length === 0) {
    return null;
  }

  function removeFilter(key: keyof FilterState) {
    const updated = { ...filters };
    delete updated[key];
    onFilterChange(updated);
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 flex-wrap transition-all duration-200">
        {chips.map((chip) => (
          <Badge
            key={chip.key}
            variant="outline"
            className={cn(
              'gap-1 py-1 pl-2.5 pr-1.5 text-xs font-medium transition-all duration-150',
              chip.colorClass
            )}
          >
            <span className="opacity-70 mr-0.5">{chip.label}:</span>
            <span>{chip.value}</span>
            <button
              onClick={() => removeFilter(chip.key)}
              className="ml-0.5 rounded-sm p-0.5 opacity-60 hover:opacity-100 hover:bg-black/10 dark:hover:bg-white/10 transition-opacity"
              aria-label={`Remove ${chip.label} filter`}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
      </div>

      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        {totalCount != null && (
          <span className="font-medium tabular-nums">
            {totalCount.toLocaleString()} {totalCount === 1 ? 'contact' : 'contacts'} found
          </span>
        )}
        {explanation && totalCount != null && (
          <span className="text-border">|</span>
        )}
        {explanation && (
          <span className="italic">{explanation}</span>
        )}
      </div>
    </div>
  );
}
