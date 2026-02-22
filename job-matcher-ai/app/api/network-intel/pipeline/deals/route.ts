import { supabase } from '@/lib/supabase';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

const DEAL_SELECT =
  '*, contacts(id, first_name, last_name, company, position, headline, city, state)';

// GET deals for a pipeline
export async function GET(req: NextRequest) {
  const pipelineId = req.nextUrl.searchParams.get('pipeline_id');

  if (!pipelineId) {
    return Response.json(
      { error: 'pipeline_id query param is required' },
      { status: 400 }
    );
  }

  try {
    const allDeals: Record<string, unknown>[] = [];
    const pageSize = 1000;
    let offset = 0;

    while (true) {
      const { data, error } = await supabase
        .from('deals')
        .select(DEAL_SELECT)
        .eq('pipeline_id', pipelineId)
        .order('position')
        .order('created_at')
        .range(offset, offset + pageSize - 1);

      if (error) throw new Error(`DB error: ${error.message}`);
      if (!data || data.length === 0) break;

      allDeals.push(...data);
      if (data.length < pageSize) break;
      offset += pageSize;
    }

    return Response.json({ deals: allDeals });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch deals';
    console.error('Deals fetch error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}

// POST create a new deal
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      pipeline_id,
      title,
      contact_id,
      stage,
      amount,
      close_date,
      notes,
      next_action,
      next_action_date,
      source,
    } = body;

    if (!pipeline_id || !title) {
      return Response.json(
        { error: 'pipeline_id and title are required' },
        { status: 400 }
      );
    }

    // Get max position in the target stage to append at end
    const targetStage = stage || 'backlog';
    const { data: existing } = await supabase
      .from('deals')
      .select('position')
      .eq('pipeline_id', pipeline_id)
      .eq('stage', targetStage)
      .order('position', { ascending: false })
      .limit(1);

    const nextPosition = existing && existing.length > 0 ? existing[0].position + 1 : 0;

    const insert: Record<string, unknown> = {
      pipeline_id,
      title,
      stage: targetStage,
      position: nextPosition,
    };

    if (contact_id) insert.contact_id = contact_id;
    if (amount !== undefined && amount !== null) insert.amount = amount;
    if (close_date) insert.close_date = close_date;
    if (notes) insert.notes = notes;
    if (next_action) insert.next_action = next_action;
    if (next_action_date) insert.next_action_date = next_action_date;
    if (source) insert.source = source;

    const { data, error } = await supabase
      .from('deals')
      .insert(insert)
      .select(DEAL_SELECT)
      .single();

    if (error) throw new Error(`DB error: ${error.message}`);

    return Response.json({ deal: data }, { status: 201 });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to create deal';
    console.error('Deal create error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
