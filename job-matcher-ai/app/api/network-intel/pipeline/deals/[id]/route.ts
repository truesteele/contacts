import { supabase } from '@/lib/supabase';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

const DEAL_SELECT =
  '*, contacts(id, first_name, last_name, company, position, headline, city, state)';

// PATCH update a deal
export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await req.json();

    // Only allow updating known fields
    const allowedFields = [
      'title',
      'stage',
      'amount',
      'close_date',
      'notes',
      'next_action',
      'next_action_date',
      'source',
      'lost_reason',
      'position',
      'contact_id',
    ];

    const updates: Record<string, unknown> = { updated_at: new Date().toISOString() };
    for (const field of allowedFields) {
      if (body[field] !== undefined) {
        updates[field] = body[field];
      }
    }

    const { data, error } = await supabase
      .from('deals')
      .update(updates)
      .eq('id', id)
      .select(DEAL_SELECT)
      .single();

    if (error) throw new Error(`DB error: ${error.message}`);

    return Response.json({ deal: data });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to update deal';
    console.error('Deal update error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}

// DELETE soft-delete a deal (sets stage to 'lost')
export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const { data, error } = await supabase
      .from('deals')
      .update({
        stage: 'lost',
        lost_reason: 'Manually removed',
        updated_at: new Date().toISOString(),
      })
      .eq('id', id)
      .select(DEAL_SELECT)
      .single();

    if (error) throw new Error(`DB error: ${error.message}`);

    return Response.json({ deal: data });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to delete deal';
    console.error('Deal delete error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
