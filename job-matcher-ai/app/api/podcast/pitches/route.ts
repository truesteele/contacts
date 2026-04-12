import { NextRequest } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET(req: NextRequest) {
  try {
    const params = req.nextUrl.searchParams;
    const speaker = params.get('speaker') || '';
    const pitchStatus = params.get('pitch_status') || '';
    const fitTier = params.get('fit_tier') || '';
    const search = params.get('search') || '';
    const page = Math.max(1, parseInt(params.get('page') || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(params.get('limit') || '25', 10)));
    const offset = (page - 1) * limit;

    // Look up speaker profile if specified
    let speakerId: number | null = null;
    if (speaker) {
      const { data: speakerProfile } = await supabase
        .from('speaker_profiles')
        .select('id')
        .eq('slug', speaker)
        .single();
      if (speakerProfile) speakerId = speakerProfile.id;
    }

    // Build pitch query
    let query = supabase
      .from('podcast_pitches')
      .select('*', { count: 'exact' });

    if (speakerId) {
      query = query.eq('speaker_profile_id', speakerId);
    }

    if (pitchStatus) {
      query = query.eq('pitch_status', pitchStatus);
    }

    if (fitTier) {
      query = query.eq('fit_tier', fitTier);
    }

    query = query
      .order('generated_at', { ascending: false })
      .range(offset, offset + limit - 1);

    const { data: pitches, error: pitchError, count } = await query;

    if (pitchError) {
      return Response.json(
        { error: `Failed to fetch pitches: ${pitchError.message}` },
        { status: 500 }
      );
    }

    if (!pitches || pitches.length === 0) {
      return Response.json({
        pitches: [],
        total: 0,
        page,
        limit,
        total_pages: 0,
      });
    }

    // Fetch associated podcasts
    const podcastIds = [...new Set(pitches.map((p: any) => p.podcast_target_id))];
    const { data: podcasts } = await supabase
      .from('podcast_targets')
      .select('id, title, author, host_name, host_email, email_verified, activity_status, website_url')
      .in('id', podcastIds);

    const podcastMap = new Map<number, any>();
    if (podcasts) {
      for (const p of podcasts) podcastMap.set(p.id, p);
    }

    // Fetch speaker names
    const speakerIds = [...new Set(pitches.map((p: any) => p.speaker_profile_id))];
    const { data: speakers } = await supabase
      .from('speaker_profiles')
      .select('id, name, slug')
      .in('id', speakerIds);

    const speakerMap = new Map<number, any>();
    if (speakers) {
      for (const s of speakers) speakerMap.set(s.id, s);
    }

    // Merge and optionally filter by search
    let merged = pitches.map((p: any) => ({
      ...p,
      podcast: podcastMap.get(p.podcast_target_id) || null,
      speaker: speakerMap.get(p.speaker_profile_id) || null,
    }));

    if (search) {
      const q = search.toLowerCase();
      merged = merged.filter(
        (p: any) =>
          p.podcast?.title?.toLowerCase().includes(q) ||
          p.subject_line?.toLowerCase().includes(q) ||
          p.pitch_body?.toLowerCase().includes(q)
      );
    }

    return Response.json({
      pitches: merged,
      total: count ?? 0,
      page,
      limit,
      total_pages: Math.ceil((count ?? 0) / limit),
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch pitches';
    console.error('[Podcast Pitches] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}

export async function PATCH(req: Request) {
  try {
    const body = await req.json() as {
      pitch_id: number;
      subject_line?: string;
      pitch_body?: string;
      pitch_status?: string;
      is_bookmarked?: boolean;
      user_notes?: string;
    };

    if (!body.pitch_id) {
      return Response.json({ error: 'pitch_id is required' }, { status: 400 });
    }

    const updates: Record<string, any> = {
      updated_at: new Date().toISOString(),
    };

    if (body.subject_line !== undefined) {
      updates.subject_line = body.subject_line;
    }
    if (body.pitch_body !== undefined) {
      updates.pitch_body = body.pitch_body;
    }
    if (body.is_bookmarked !== undefined) {
      updates.is_bookmarked = body.is_bookmarked;
    }
    if (body.user_notes !== undefined) {
      updates.user_notes = body.user_notes;
    }
    if (body.pitch_status !== undefined) {
      const valid = ['draft', 'approved', 'rejected', 'sent', 'replied', 'booked'];
      if (!valid.includes(body.pitch_status)) {
        return Response.json(
          { error: `Invalid status. Must be one of: ${valid.join(', ')}` },
          { status: 400 }
        );
      }
      updates.pitch_status = body.pitch_status;
      if (body.pitch_status === 'approved') {
        updates.approved_at = new Date().toISOString();
      }
    }

    const { error: updateError } = await supabase
      .from('podcast_pitches')
      .update(updates)
      .eq('id', body.pitch_id);

    if (updateError) {
      return Response.json(
        { error: `Failed to update pitch: ${updateError.message}` },
        { status: 500 }
      );
    }

    return Response.json({ status: 'updated', pitch_id: body.pitch_id });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to update pitch';
    console.error('[Podcast Pitches] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json() as {
      podcast_target_id: number;
      speaker_slug: string;
      is_bookmarked?: boolean;
      user_notes?: string;
    };

    if (!body.podcast_target_id || !body.speaker_slug) {
      return Response.json(
        { error: 'podcast_target_id and speaker_slug are required' },
        { status: 400 }
      );
    }

    // Resolve speaker_profile_id from slug
    const { data: speakerProfile, error: speakerError } = await supabase
      .from('speaker_profiles')
      .select('id')
      .eq('slug', body.speaker_slug)
      .single();

    if (speakerError || !speakerProfile) {
      return Response.json(
        { error: `Speaker not found for slug: ${body.speaker_slug}` },
        { status: 404 }
      );
    }

    // Check if pitch already exists for this podcast+speaker combo
    const { data: existing } = await supabase
      .from('podcast_pitches')
      .select('id')
      .eq('podcast_target_id', body.podcast_target_id)
      .eq('speaker_profile_id', speakerProfile.id)
      .single();

    if (existing) {
      // Upsert: return existing record instead of creating duplicate
      return Response.json({ id: existing.id, pitch_id: existing.id });
    }

    // Create minimal pitch record
    const { data: newPitch, error: insertError } = await supabase
      .from('podcast_pitches')
      .insert({
        podcast_target_id: body.podcast_target_id,
        speaker_profile_id: speakerProfile.id,
        is_bookmarked: body.is_bookmarked ?? false,
        user_notes: body.user_notes ?? '',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
      .select('id')
      .single();

    if (insertError || !newPitch) {
      return Response.json(
        { error: `Failed to create pitch: ${insertError?.message}` },
        { status: 500 }
      );
    }

    return Response.json({ id: newPitch.id, pitch_id: newPitch.id });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to create pitch';
    console.error('[Podcast Pitches] POST Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
