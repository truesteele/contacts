'use client';

import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { DealCard, type Deal } from './deal-card';

interface StageConfig {
  name: string;
  color: string;
}

interface KanbanColumnProps {
  stage: StageConfig;
  stageKey: string;
  deals: Deal[];
  onDealClick: (deal: Deal) => void;
}

function formatTotal(deals: Deal[]): string {
  const total = deals.reduce((sum, d) => sum + (d.amount ? Number(d.amount) : 0), 0);
  if (total === 0) return '';
  if (total >= 1_000_000) return `$${(total / 1_000_000).toFixed(1)}M`;
  if (total >= 1_000) return `$${(total / 1_000).toFixed(0)}K`;
  return `$${total.toLocaleString()}`;
}

export function KanbanColumn({ stage, stageKey, deals, onDealClick }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: stageKey });
  const dealIds = deals.map((d) => d.id);
  const totalValue = formatTotal(deals);

  return (
    <div className="flex flex-col min-w-[280px] w-[280px] shrink-0">
      {/* Column header */}
      <div className="flex items-center gap-2 px-2 py-2 mb-2">
        <div
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: stage.color }}
        />
        <span className="text-sm font-medium truncate">{stage.name}</span>
        <span className="text-xs text-muted-foreground tabular-nums ml-auto">
          {deals.length}
        </span>
        {totalValue && (
          <span className="text-xs text-muted-foreground font-mono">{totalValue}</span>
        )}
      </div>

      {/* Droppable area */}
      <SortableContext items={dealIds} strategy={verticalListSortingStrategy}>
        <div
          ref={setNodeRef}
          className={cn(
            'flex-1 rounded-lg border border-dashed p-2 space-y-2 min-h-[120px] transition-colors',
            isOver
              ? 'border-primary/50 bg-primary/5 dark:bg-primary/10'
              : 'border-transparent bg-muted/30 dark:bg-muted/10'
          )}
        >
          <ScrollArea className="h-[calc(100vh-260px)]">
            <div className="space-y-2 pr-2">
              {deals.map((deal) => (
                <DealCard
                  key={deal.id}
                  deal={deal}
                  onClick={() => onDealClick(deal)}
                />
              ))}
              {deals.length === 0 && (
                <div className="flex items-center justify-center h-20 text-xs text-muted-foreground">
                  Drop deals here
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      </SortableContext>
    </div>
  );
}
