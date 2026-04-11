import { NextRequest } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET(req: NextRequest) {
  try {
    const params = req.nextUrl.searchParams;
    const speaker = params.get('speaker') || '';
    const status = params.get('status') || '';
    const fitTier = params.get('fit_tier') || '';
    const search = params.get('search') || '';
    const page = Math.max(1, parseInt(params.get('page') || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(params.get('limit') || '25', 10)));
    const offset = (page - 1) * limit;

    // Build the base query
    let query = supabase
      .from('podcast_targets')
      .select('*', { count: 'exact' });

    // Filter by activity status
    if (status) {
      query = query.eq('activity_status', status);
    }

    // Text search on title, author, description
    if (search) {
      query = query.or(
        `title.ilike.%${search}%,author.ilike.%${search}%,description.ilike.%${search}%`
      );
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
    if (speaker && podcastsWithScores.length > 0) {
      // Look up speaker profile
      const { data: speakerProfile } = await supabase
        .from('speaker_profiles')
        .select('id')
        .eq('slug', speaker)
        .single();

      if (speakerProfile) {
        const podcastIds = podcastsWithScores.map((p: any) => p.id);
        const { data: pitches } = await supabase
          .from('podcast_pitches')
          .select('podcast_target_id, fit_tier, fit_score, fit_rationale, pitch_status, subject_line, pitch_body')
          .eq('speaker_profile_id', speakerProfile.id)
          .in('podcast_target_id', podcastIds);

        // Index pitches by podcast_target_id
        const pitchMap = new Map<number, any>();
        if (pitches) {
          for (const pitch of pitches) {
            pitchMap.set(pitch.podcast_target_id, pitch);
          }
        }

        // Merge pitch data onto podcasts
        podcastsWithScores = podcastsWithScores.map((p: any) => ({
          ...p,
          pitch: pitchMap.get(p.id) || null,
        }));

        // Filter by fit tier if requested
        if (fitTier) {
          podcastsWithScores = podcastsWithScores.filter(
            (p: any) => p.pitch?.fit_tier === fitTier
          );
        }
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
