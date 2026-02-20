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
].join(', ');

export async function GET(request: NextRequest) {
  try {
    // Fetch batch of unrated contacts, ordered by AI proximity score descending
    const { data: contacts, error: contactsError } = await supabase
      .from('contacts')
      .select(SELECT_FIELDS)
      .is('familiarity_rating', null)
      .order('ai_proximity_score', { ascending: false, nullsFirst: false })
      .limit(BATCH_SIZE);

    if (contactsError) {
      console.error('[Rate GET] Contacts query error:', contactsError);
      return NextResponse.json(
        { error: contactsError.message },
        { status: 500 }
      );
    }

    // Get counts for progress tracking
    const { count: unratedCount, error: unratedError } = await supabase
      .from('contacts')
      .select('id', { count: 'exact', head: true })
      .is('familiarity_rating', null);

    if (unratedError) {
      console.error('[Rate GET] Unrated count error:', unratedError);
      return NextResponse.json(
        { error: unratedError.message },
        { status: 500 }
      );
    }

    const { count: ratedCount, error: ratedError } = await supabase
      .from('contacts')
      .select('id', { count: 'exact', head: true })
      .not('familiarity_rating', 'is', null);

    if (ratedError) {
      console.error('[Rate GET] Rated count error:', ratedError);
      return NextResponse.json(
        { error: ratedError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({
      contacts: contacts || [],
      unrated_count: unratedCount ?? 0,
      rated_count: ratedCount ?? 0,
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

    // Validate contact_id
    if (contact_id === undefined || contact_id === null) {
      return NextResponse.json(
        { error: 'contact_id is required' },
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

    const { error: updateError } = await supabase
      .from('contacts')
      .update({
        familiarity_rating: rating,
        familiarity_rated_at: rating !== null ? new Date().toISOString() : null,
      })
      .eq('id', contact_id);

    if (updateError) {
      console.error('[Rate POST] Update error:', updateError);
      return NextResponse.json(
        { error: updateError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to save rating';
    console.error('[Rate POST] Error:', err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
