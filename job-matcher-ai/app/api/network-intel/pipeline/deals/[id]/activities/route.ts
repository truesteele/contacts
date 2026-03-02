import { supabase } from '@/lib/supabase';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

// GET deal activities (timeline)
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const url = new URL(req.url);
    const limit = Math.min(parseInt(url.searchParams.get('limit') || '50'), 200);
    const offset = parseInt(url.searchParams.get('offset') || '0');

    const { data, error, count } = await supabase
      .from('deal_activities')
      .select('*', { count: 'exact' })
      .eq('deal_id', id)
      .order('activity_date', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) throw new Error(`DB error: ${error.message}`);

    return Response.json({ activities: data || [], total: count || 0 });
  } catch (error: unknown) {
    const message =
      error instanceof Error ? error.message : 'Failed to fetch activities';
    console.error('Deal activities error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
