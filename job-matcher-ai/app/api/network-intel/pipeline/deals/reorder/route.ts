import { supabase } from '@/lib/supabase';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

interface ReorderItem {
  id: string;
  stage: string;
  position: number;
}

// PATCH batch update positions when cards are reordered or moved between columns
export async function PATCH(req: NextRequest) {
  try {
    const body = await req.json();
    const { items } = body as { items: ReorderItem[] };

    if (!items || !Array.isArray(items) || items.length === 0) {
      return Response.json(
        { error: 'items array is required with id, stage, and position' },
        { status: 400 }
      );
    }

    // Update each deal's stage and position
    const now = new Date().toISOString();
    const updates = items.map((item) =>
      supabase
        .from('deals')
        .update({ stage: item.stage, position: item.position, updated_at: now })
        .eq('id', item.id)
    );

    const results = await Promise.all(updates);
    const errors = results.filter((r) => r.error);

    if (errors.length > 0) {
      throw new Error(
        `Failed to update ${errors.length} deals: ${errors[0].error?.message}`
      );
    }

    return Response.json({ updated: items.length });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to reorder deals';
    console.error('Deal reorder error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
