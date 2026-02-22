import { supabase } from '@/lib/supabase';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

// GET all pipelines
export async function GET() {
  try {
    const { data, error } = await supabase
      .from('pipelines')
      .select('*')
      .order('created_at');

    if (error) throw new Error(`DB error: ${error.message}`);

    return Response.json({ pipelines: data });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch pipelines';
    console.error('Pipeline fetch error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}

// POST create a new pipeline
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { name, slug, entity, stages } = body;

    if (!name || !slug || !entity) {
      return Response.json(
        { error: 'name, slug, and entity are required' },
        { status: 400 }
      );
    }

    const insert: Record<string, unknown> = { name, slug, entity };
    if (stages) insert.stages = stages;

    const { data, error } = await supabase
      .from('pipelines')
      .insert(insert)
      .select()
      .single();

    if (error) throw new Error(`DB error: ${error.message}`);

    return Response.json({ pipeline: data }, { status: 201 });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to create pipeline';
    console.error('Pipeline create error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
