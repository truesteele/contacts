'use client';

import { useState, useCallback, useMemo } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import { arrayMove } from '@dnd-kit/sortable';
import { KanbanColumn } from './kanban-column';
import { DealCard, type Deal } from './deal-card';

interface StageConfig {
  name: string;
  color: string;
}

interface KanbanBoardProps {
  deals: Deal[];
  stages: StageConfig[];
  hideLost: boolean;
  onDealsChange: (deals: Deal[]) => void;
  onDealClick: (deal: Deal) => void;
}

function stageKey(name: string): string {
  return name.toLowerCase().replace(/\s+/g, '_');
}

export function KanbanBoard({
  deals,
  stages,
  hideLost,
  onDealsChange,
  onDealClick,
}: KanbanBoardProps) {
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    })
  );

  // Group deals by stage
  const dealsByStage = useMemo(() => {
    const map: Record<string, Deal[]> = {};
    for (const stage of stages) {
      const key = stageKey(stage.name);
      map[key] = [];
    }
    for (const deal of deals) {
      if (map[deal.stage]) {
        map[deal.stage].push(deal);
      }
    }
    // Sort each column by position
    for (const key of Object.keys(map)) {
      map[key].sort((a, b) => a.position - b.position);
    }
    return map;
  }, [deals, stages]);

  const activeDeal = useMemo(
    () => deals.find((d) => d.id === activeId) ?? null,
    [deals, activeId]
  );

  // Find which stage column a deal is currently in
  const findStageForDeal = useCallback(
    (dealId: string): string | null => {
      for (const [stage, stageDeals] of Object.entries(dealsByStage)) {
        if (stageDeals.some((d) => d.id === dealId)) {
          return stage;
        }
      }
      return null;
    },
    [dealsByStage]
  );

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  }, []);

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      const { active, over } = event;
      if (!over) return;

      const activeStage = findStageForDeal(active.id as string);
      // The "over" could be a deal card or a column droppable
      let overStage = findStageForDeal(over.id as string);

      // If over.id matches a stage key, it's a column drop
      if (!overStage && dealsByStage[over.id as string] !== undefined) {
        overStage = over.id as string;
      }

      if (!activeStage || !overStage || activeStage === overStage) return;

      // Move the deal to the new column (append at end)
      const updated = deals.map((d) => {
        if (d.id === active.id) {
          const newPosition = dealsByStage[overStage!].length;
          return { ...d, stage: overStage!, position: newPosition };
        }
        return d;
      });

      onDealsChange(updated);
    },
    [deals, dealsByStage, findStageForDeal, onDealsChange]
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveId(null);

      if (!over) return;

      const activeStage = findStageForDeal(active.id as string);
      let overStage = findStageForDeal(over.id as string);

      // If over.id matches a stage key, it's an empty column
      if (!overStage && dealsByStage[over.id as string] !== undefined) {
        overStage = over.id as string;
      }

      if (!activeStage || !overStage) return;

      if (activeStage === overStage) {
        // Reorder within the same column
        const columnDeals = dealsByStage[activeStage];
        const oldIndex = columnDeals.findIndex((d) => d.id === active.id);
        const newIndex = columnDeals.findIndex((d) => d.id === over.id);

        if (oldIndex === -1 || newIndex === -1 || oldIndex === newIndex) return;

        const reordered = arrayMove(columnDeals, oldIndex, newIndex);
        const reorderedWithPositions = reordered.map((d, i) => ({
          ...d,
          position: i,
        }));

        const updated = deals.map((d) => {
          const found = reorderedWithPositions.find((r) => r.id === d.id);
          return found ?? d;
        });

        onDealsChange(updated);

        // Persist reorder
        persistReorder(
          reorderedWithPositions.map((d) => ({
            id: d.id,
            stage: d.stage,
            position: d.position,
          }))
        );
      } else {
        // Moved to a different column -- recalculate positions for both columns
        const sourceDeals = deals
          .filter((d) => d.stage === activeStage && d.id !== (active.id as string))
          .sort((a, b) => a.position - b.position)
          .map((d, i) => ({ ...d, position: i }));

        const targetDeals = deals
          .filter((d) => d.stage === overStage)
          .sort((a, b) => a.position - b.position);

        const movedDeal = deals.find((d) => d.id === active.id);
        if (!movedDeal) return;

        // Insert at the position of the over item, or at end
        const overIndex = targetDeals.findIndex((d) => d.id === over.id);
        const insertIndex = overIndex >= 0 ? overIndex : targetDeals.length;

        const newTargetDeals = [...targetDeals];
        newTargetDeals.splice(insertIndex, 0, {
          ...movedDeal,
          stage: overStage,
        });
        const targetWithPositions = newTargetDeals.map((d, i) => ({
          ...d,
          position: i,
        }));

        const allUpdated = [...sourceDeals, ...targetWithPositions];
        const updated = deals.map((d) => {
          const found = allUpdated.find((u) => u.id === d.id);
          return found ?? d;
        });

        onDealsChange(updated);

        // Persist all changed items
        persistReorder(
          allUpdated.map((d) => ({
            id: d.id,
            stage: d.stage,
            position: d.position,
          }))
        );
      }
    },
    [deals, dealsByStage, findStageForDeal, onDealsChange]
  );

  const visibleStages = hideLost
    ? stages.filter((s) => stageKey(s.name) !== 'lost')
    : stages;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        {visibleStages.map((stage) => {
          const key = stageKey(stage.name);
          return (
            <KanbanColumn
              key={key}
              stage={stage}
              stageKey={key}
              deals={dealsByStage[key] || []}
              onDealClick={onDealClick}
            />
          );
        })}
      </div>

      <DragOverlay>
        {activeDeal ? (
          <div className="w-[264px]">
            <DealCard deal={activeDeal} isDragOverlay />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

async function persistReorder(
  items: { id: string; stage: string; position: number }[]
) {
  try {
    await fetch('/api/network-intel/pipeline/deals/reorder', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items }),
    });
  } catch (err) {
    console.error('Failed to persist reorder:', err);
  }
}
