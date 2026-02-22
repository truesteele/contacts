'use client';

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Building2, Calendar, DollarSign, Zap } from 'lucide-react';

export interface DealContact {
  id: number;
  first_name: string;
  last_name: string;
  company?: string | null;
  position?: string | null;
  headline?: string | null;
  city?: string | null;
  state?: string | null;
}

export interface Deal {
  id: string;
  pipeline_id: string;
  contact_id: number | null;
  title: string;
  stage: string;
  amount: number | null;
  close_date: string | null;
  notes: string | null;
  next_action: string | null;
  next_action_date: string | null;
  source: string | null;
  lost_reason: string | null;
  position: number;
  created_at: string;
  updated_at: string;
  contacts: DealContact | null;
}

interface DealCardProps {
  deal: Deal;
  onClick?: () => void;
  isDragOverlay?: boolean;
}

function daysInStage(updatedAt: string): number {
  const updated = new Date(updatedAt);
  const now = new Date();
  return Math.floor((now.getTime() - updated.getTime()) / (1000 * 60 * 60 * 24));
}

function formatAmount(amount: number): string {
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(0)}K`;
  return `$${amount.toLocaleString()}`;
}

export function DealCard({ deal, onClick, isDragOverlay }: DealCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: deal.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const days = daysInStage(deal.updated_at);
  const contactName = deal.contacts
    ? `${deal.contacts.first_name} ${deal.contacts.last_name}`
    : null;

  return (
    <Card
      ref={isDragOverlay ? undefined : setNodeRef}
      style={isDragOverlay ? undefined : style}
      {...(isDragOverlay ? {} : attributes)}
      {...(isDragOverlay ? {} : listeners)}
      onClick={onClick}
      className={cn(
        'p-3 cursor-grab active:cursor-grabbing select-none',
        'hover:ring-1 hover:ring-primary/20 transition-all',
        isDragging && 'opacity-30',
        isDragOverlay && 'shadow-lg ring-2 ring-primary/30 rotate-1',
      )}
    >
      {/* Title */}
      <div className="font-medium text-sm leading-tight mb-1.5">{deal.title}</div>

      {/* Contact + Company */}
      {contactName && (
        <div className="text-xs text-muted-foreground mb-1.5">
          <span>{contactName}</span>
          {deal.contacts?.company && (
            <span className="flex items-center gap-1 mt-0.5">
              <Building2 className="w-3 h-3 shrink-0" />
              <span className="truncate">{deal.contacts.company}</span>
            </span>
          )}
        </div>
      )}

      {/* Amount + Next action row */}
      <div className="flex items-center gap-2 flex-wrap">
        {deal.amount != null && deal.amount > 0 && (
          <Badge
            variant="outline"
            className="text-[10px] px-1.5 py-0 font-mono bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800"
          >
            <DollarSign className="w-3 h-3 mr-0.5" />
            {formatAmount(deal.amount)}
          </Badge>
        )}

        {deal.next_action && (
          <Badge
            variant="outline"
            className="text-[10px] px-1.5 py-0 bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800 max-w-[140px] truncate"
          >
            <Zap className="w-3 h-3 mr-0.5 shrink-0" />
            {deal.next_action}
          </Badge>
        )}

        {deal.next_action_date && (
          <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
            <Calendar className="w-3 h-3" />
            {new Date(deal.next_action_date + 'T00:00:00').toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
            })}
          </span>
        )}
      </div>

      {/* Footer: source + days in stage */}
      <div className="flex items-center justify-between mt-2 text-[10px] text-muted-foreground">
        {deal.source ? (
          <Badge variant="secondary" className="text-[9px] px-1 py-0">
            {deal.source}
          </Badge>
        ) : (
          <span />
        )}
        <span className="tabular-nums">
          {days === 0 ? 'Today' : `${days}d`}
        </span>
      </div>
    </Card>
  );
}
