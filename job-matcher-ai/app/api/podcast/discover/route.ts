import { NextRequest } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET(req: NextRequest) {
  try {
    const params = req.nextUrl.searchParams;
    const speaker = params.get('speaker') || '';
    const status = params.get('status') || '';
    const fitTier = params.get('fit_tier') || '';
    const discoveryMethod = params.get('discovery_method') || '';
    const search = params.get('search') || '';
    const page = Math.max(1, parseInt(params.get('page') || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(params.get('limit') || '25', 10)));
    const offset = (page - 1) * limit;
    let speakerProfileId: number | null = null;
    let prefetchedPitches: Array<{
      podcast_target_id: number;
      fit_tier: string | null;
      fit_score: number | null;
      fit_rationale: string | null;
      topic_match: unknown;
      pitch_status: string | null;
      subject_line: string | null;
      pitch_body: string | null;
    }> = [];

    if (speaker) {
      const { data: speakerProfile, error: speakerError } = await supabase
        .from('speaker_profiles')
        .select('id')
        .eq('slug', speaker)
        .single();

      if (speakerError || !speakerProfile) {
        return Response.json(
          { error: `Speaker not found: ${speaker}` },
          { status: 404 }
        );
      }

      speakerProfileId = speakerProfile.id;
    }

    // Build the base query
    let query = supabase
      .from('podcast_targets')
      .select('*', { count: 'exact' });

    // Filter by activity status
    if (status) {
      query = query.eq('activity_status', status);
    }

    // Filter by discovery method
    if (discoveryMethod) {
      query = query.contains('discovery_methods', [discoveryMethod]);
    }

    // Text search on title, author, description
    if (search) {
      // Sanitize search to prevent PostgREST filter injection
      const sanitized = search.replace(/[%.,()]/g, '');
      if (sanitized) {
        query = query.or(
          `title.ilike.%${sanitized}%,author.ilike.%${sanitized}%,description.ilike.%${sanitized}%`
        );
      }
    }

    if (speakerProfileId && fitTier) {
      const { data: matchingPitches, error: pitchFilterError } = await supabase
        .from('podcast_pitches')
        .select('podcast_target_id, fit_tier, fit_score, fit_rationale, topic_match, pitch_status, subject_line, pitch_body')
        .eq('speaker_profile_id', speakerProfileId)
        .eq('fit_tier', fitTier);

      if (pitchFilterError) {
        return Response.json(
          { error: `Failed to filter podcasts by fit tier: ${pitchFilterError.message}` },
          { status: 500 }
        );
      }

      prefetchedPitches = matchingPitches || [];

      const matchingIds = prefetchedPitches.map((pitch) => pitch.podcast_target_id);
      if (matchingIds.length === 0) {
        return Response.json({
          podcasts: [],
          total: 0,
          page,
          limit,
          total_pages: 0,
        });
      }

      query = query.in('id', matchingIds);
    }

    // Paginate
    query = query
      .order('discovered_at', { ascending: false })
      .range(offset, offset + limit - 1);

    const { data: podcasts, error: podcastError, count } = await query;

    if (podcastError) {
      return Response.json(
        { error: `Failed to fetch podcasts: ${podcastError.message}` },
        { status: 500 }
      );
    }

    // If speaker is specified, join fit scores from podcast_pitches
    let podcastsWithScores = podcasts || [];
    if (speakerProfileId && podcastsWithScores.length > 0) {
      const podcastIds = podcastsWithScores.map((p: any) => p.id);
      let pitches = prefetchedPitches;

      if (!fitTier) {
        const { data: fetchedPitches, error: pitchError } = await supabase
          .from('podcast_pitches')
          .select('podcast_target_id, fit_tier, fit_score, fit_rationale, topic_match, pitch_status, subject_line, pitch_body')
          .eq('speaker_profile_id', speakerProfileId)
          .in('podcast_target_id', podcastIds);

        if (pitchError) {
          return Response.json(
            { error: `Failed to fetch podcast pitches: ${pitchError.message}` },
            { status: 500 }
          );
        }

        pitches = fetchedPitches || [];
      } else {
        pitches = pitches.filter((pitch) => podcastIds.includes(pitch.podcast_target_id));
      }

      const pitchMap = new Map<number, any>();
      for (const pitch of pitches) {
        pitchMap.set(pitch.podcast_target_id, pitch);
      }

      podcastsWithScores = podcastsWithScores.map((p: any) => ({
        ...p,
        pitch: pitchMap.get(p.id) || null,
      }));

      if (fitTier) {
        podcastsWithScores = podcastsWithScores.filter(
          (p: any) => p.pitch?.fit_tier === fitTier
        );
      }

      if (page > 1 && podcastsWithScores.length === 0 && (count ?? 0) > 0) {
        return Response.json({
          podcasts: [],
          total: count ?? 0,
          page,
          limit,
          total_pages: Math.ceil((count ?? 0) / limit),
          warning: 'Requested page is beyond the filtered result set.',
        });
      }
        }

    return Response.json({
      podcasts: podcastsWithScores,
      total: count ?? 0,
      page,
      limit,
      total_pages: Math.ceil((count ?? 0) / limit),
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to discover podcasts';
    console.error('[Podcast Discover] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
