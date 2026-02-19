'use client';

import { useState, useCallback } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

export type OutreachStatusValue =
  | 'not_contacted'
  | 'reached_out'
  | 'responded'
  | 'meeting_scheduled'
  | 'committed'
  | 'declined';

interface PipelineStatusProps {
  contactId: number;
  listId: string;
  status: OutreachStatusValue;
  onStatusChange: (contactId: number, status: OutreachStatusValue) => void;
}

const STATUS_OPTIONS: { value: OutreachStatusValue; label: string; color: string }[] = [
  {
    value: 'not_contacted',
    label: 'Not Contacted',
    color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
  },
  {
    value: 'reached_out',
    label: 'Reached Out',
    color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  },
  {
    value: 'responded',
    label: 'Responded',
    color: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  },
  {
    value: 'meeting_scheduled',
    label: 'Meeting',
    color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
  },
  {
    value: 'committed',
    label: 'Committed',
    color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  },
  {
    value: 'declined',
    label: 'Declined',
    color: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  },
];

const STATUS_COLOR_MAP: Record<string, string> = Object.fromEntries(
  STATUS_OPTIONS.map((opt) => [opt.value, opt.color])
);

export function PipelineStatus({
  contactId,
  listId,
  status,
  onStatusChange,
}: PipelineStatusProps) {
  const [updating, setUpdating] = useState(false);

  const handleChange = useCallback(
    async (newStatus: string) => {
      if (newStatus === status) return;
      setUpdating(true);
      try {
        const res = await fetch(`/api/network-intel/prospect-lists/${listId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            update_status: [{ contact_id: contactId, status: newStatus }],
          }),
        });
        if (res.ok) {
          onStatusChange(contactId, newStatus as OutreachStatusValue);
        }
      } catch (err) {
        console.error('Failed to update status:', err);
      } finally {
        setUpdating(false);
      }
    },
    [contactId, listId, status, onStatusChange]
  );

  const currentColor = STATUS_COLOR_MAP[status] || '';

  return (
    <div onClick={(e) => e.stopPropagation()}>
      <Select value={status} onValueChange={handleChange} disabled={updating}>
        <SelectTrigger
          className={cn(
            'h-6 w-[120px] text-[10px] font-medium border-0 px-2 py-0 rounded-md focus:ring-0 focus:ring-offset-0',
            currentColor,
            updating && 'opacity-50'
          )}
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {STATUS_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value} className="text-xs">
              <div className="flex items-center gap-2">
                <div className={cn('w-2 h-2 rounded-full', opt.color.split(' ')[0])} />
                {opt.label}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

export { STATUS_OPTIONS, STATUS_COLOR_MAP };
