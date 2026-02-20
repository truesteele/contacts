import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

const BATCH_SIZE = 20;

const SELECT_FIELDS = [
  'id',
  'first_name',
  'last_name',
  'enrich_profile_pic_url',
  'enrich_current_title',
  'enrich_current_company',
  'headline',
  'linkedin_url',
  'ai_proximity_score',
  'ai_proximity_tier',
  'enrich_schools',
  'enrich_companies_worked',
  'connected_on',
  'familiarity_rating',
].join(', ');

type SortOption = 'ai_close' | 'ai_distant' | 'recent' | 'default';
type ModeOption = 'unrated' | 'rerate';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const sort = (searchParams.get('sort') || 'ai_close') as SortOption;
    const mode = (searchParams.get('mode') || 'unrated') as ModeOption;

    // Build contacts query
    let query = supabase.from('contacts').select(SELECT_FIELDS);

    if (mode === 'rerate') {
      query = query.not('familiarity_rating', 'is', null);
    } else {
      query = query.is('familiarity_rating', null);
    }

    switch (sort) {
      case 'ai_distant':
        query = query.order('ai_proximity_score', { ascending: true, nullsFirst: false });
        break;
      case 'recent':
        query = query.order('connected_on', { ascending: false, nullsFirst: false });
        break;
      case 'ai_close':
      default:
        query = query.order('ai_proximity_score', { ascending: false, nullsFirst: false });
        break;
    }

    // Run all queries in parallel instead of sequentially
    const [contactsResult, unratedResult, ratedResult, ...breakdownResults] = await Promise.all([
      query.limit(BATCH_SIZE),
      supabase.from('contacts').select('id', { count: 'exact', head: true }).is('familiarity_rating', null),
      supabase.from('contacts').select('id', { count: 'exact', head: true }).not('familiarity_rating', 'is', null),
      ...([0, 1, 2, 3, 4] as const).map(level =>
        supabase.from('contacts').select('id', { count: 'exact', head: true }).eq('familiarity_rating', level)
      ),
    ]);

    if (contactsResult.error) {
      console.error('[Rate GET] Contacts query error:', contactsResult.error);
      return NextResponse.json({ error: contactsResult.error.message }, { status: 500 });
    }

    if (unratedResult.error || ratedResult.error) {
      const err = unratedResult.error || ratedResult.error;
      console.error('[Rate GET] Count query error:', err);
      return NextResponse.json({ error: err!.message }, { status: 500 });
    }

    const breakdown: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 };
    breakdownResults.forEach((result, i) => {
      if (!result.error && result.count !== null) {
        breakdown[i] = result.count;
      }
    });

    return NextResponse.json({
      contacts: contactsResult.data || [],
      unrated_count: unratedResult.count ?? 0,
      rated_count: ratedResult.count ?? 0,
      breakdown,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to fetch contacts';
    console.error('[Rate GET] Error:', err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { contact_id, rating } = body;

    // Validate contact_id is a number (contacts.id is INTEGER)
    if (typeof contact_id !== 'number' || !Number.isInteger(contact_id)) {
      return NextResponse.json(
        { error: 'contact_id must be an integer' },
        { status: 400 }
      );
    }

    // Validate rating is 0-4 or null (null = undo)
    if (rating !== null && (typeof rating !== 'number' || !Number.isInteger(rating) || rating < 0 || rating > 4)) {
      return NextResponse.json(
        { error: 'rating must be an integer between 0 and 4, or null' },
        { status: 400 }
      );
    }

    const { data: updated, error: updateError } = await supabase
      .from('contacts')
      .update({
        familiarity_rating: rating,
        familiarity_rated_at: rating !== null ? new Date().toISOString() : null,
      })
      .eq('id', contact_id)
      .select('id');

    if (updateError) {
      console.error('[Rate POST] Update error:', updateError);
      return NextResponse.json({ error: updateError.message }, { status: 500 });
    }

    if (!updated || updated.length === 0) {
      return NextResponse.json({ error: 'Contact not found' }, { status: 404 });
    }

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to save rating';
    console.error('[Rate POST] Error:', err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
