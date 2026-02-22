import { supabase } from '@/lib/supabase';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

// GET - search contacts by name or company for the deal form
export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get('q');

  if (!q || q.length < 2) {
    return Response.json({ contacts: [] });
  }

  try {
    const searchTerm = `%${q}%`;

    const { data, error } = await supabase
      .from('contacts')
      .select('id, first_name, last_name, company')
      .or(
        `first_name.ilike.${searchTerm},last_name.ilike.${searchTerm},company.ilike.${searchTerm}`
      )
      .order('last_name')
      .limit(20);

    if (error) throw new Error(`DB error: ${error.message}`);

    return Response.json({ contacts: data || [] });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Search failed';
    console.error('Contact search error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
