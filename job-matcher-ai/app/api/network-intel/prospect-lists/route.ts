import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export const runtime = 'edge';

/**
 * GET /api/network-intel/prospect-lists
 * Returns all prospect lists with member counts.
 */
export async function GET() {
  try {
    const { data: lists, error } = await supabase
      .from('prospect_lists')
      .select('id, name, description, created_at, updated_at')
      .order('updated_at', { ascending: false });

    if (error) throw new Error(`Failed to fetch lists: ${error.message}`);

    // Get member counts for each list
    const { data: counts, error: countError } = await supabase
      .from('prospect_list_members')
      .select('list_id');

    if (countError) throw new Error(`Failed to fetch member counts: ${countError.message}`);

    const countMap = new Map<string, number>();
    for (const row of counts || []) {
      countMap.set(row.list_id, (countMap.get(row.list_id) || 0) + 1);
    }

    const listsWithCounts = (lists || []).map((list: any) => ({
      ...list,
      member_count: countMap.get(list.id) || 0,
    }));

    return NextResponse.json({ lists: listsWithCounts });
  } catch (err: any) {
    console.error('[Prospect Lists GET] Error:', err);
    return NextResponse.json(
      { error: err.message || 'Failed to fetch prospect lists' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/network-intel/prospect-lists
 * Creates a new prospect list, optionally with initial contact_ids.
 * Body: { name: string, description?: string, contact_ids?: number[] }
 */
export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { name, description, contact_ids } = body as {
      name: string;
      description?: string;
      contact_ids?: number[];
    };

    if (!name || typeof name !== 'string' || name.trim().length === 0) {
      return NextResponse.json(
        { error: 'Missing or invalid "name" parameter' },
        { status: 400 }
      );
    }

    // Create the list
    const { data: list, error: createError } = await supabase
      .from('prospect_lists')
      .insert({ name: name.trim(), description: description?.trim() || null })
      .select('id, name, description, created_at, updated_at')
      .single();

    if (createError) throw new Error(`Failed to create list: ${createError.message}`);

    let member_count = 0;

    // Add initial members if provided
    if (contact_ids && contact_ids.length > 0) {
      const members = contact_ids.map((contact_id) => ({
        list_id: list.id,
        contact_id,
      }));

      const { error: memberError } = await supabase
        .from('prospect_list_members')
        .insert(members);

      if (memberError) {
        console.error('[Prospect Lists POST] Error adding members:', memberError);
        // Don't fail the whole request — list was created successfully
      } else {
        member_count = contact_ids.length;
      }
    }

    return NextResponse.json(
      { ...list, member_count },
      { status: 201 }
    );
  } catch (err: any) {
    console.error('[Prospect Lists POST] Error:', err);
    return NextResponse.json(
      { error: err.message || 'Failed to create prospect list' },
      { status: 500 }
    );
  }
}
