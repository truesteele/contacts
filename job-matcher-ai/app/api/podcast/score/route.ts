import { supabase } from '@/lib/supabase';

interface ScoreRequest {
  podcast_ids: number[];
  speaker_slug: string;
}

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as Partial<ScoreRequest>;

    if (!body.podcast_ids || !Array.isArray(body.podcast_ids) || body.podcast_ids.length === 0) {
      return Response.json(
        { error: 'podcast_ids is required and must be a non-empty array' },
        { status: 400 }
      );
    }

    if (!body.speaker_slug) {
      return Response.json(
        { error: 'speaker_slug is required (e.g., "sally-steele" or "justin-steele")' },
        { status: 400 }
      );
    }

    // Verify speaker exists
    const { data: speaker, error: speakerError } = await supabase
      .from('speaker_profiles')
      .select('id, name, slug')
      .eq('slug', body.speaker_slug)
      .single();

    if (speakerError || !speaker) {
      return Response.json(
        { error: `Speaker not found: ${body.speaker_slug}` },
        { status: 404 }
      );
    }

    // Check which podcasts already have scores for this speaker
    const { data: existingPitches } = await supabase
      .from('podcast_pitches')
      .select('podcast_target_id')
      .eq('speaker_profile_id', speaker.id)
      .in('podcast_target_id', body.podcast_ids);

    const alreadyScored = new Set(
      (existingPitches || []).map((p: any) => p.podcast_target_id)
    );
    const toScore = body.podcast_ids.filter((id) => !alreadyScored.has(id));

    if (toScore.length === 0) {
      return Response.json({
        status: 'complete',
        message: 'All selected podcasts already scored for this speaker',
        already_scored: body.podcast_ids.length,
        newly_scored: 0,
      });
    }

    // Fetch podcast data + episodes for scoring
    const { data: podcasts, error: podcastError } = await supabase
      .from('podcast_targets')
      .select('id, title, author, description, categories, activity_status, host_name')
      .in('id', toScore);

    if (podcastError || !podcasts) {
      return Response.json(
        { error: `Failed to fetch podcasts: ${podcastError?.message}` },
        { status: 500 }
      );
    }

    // Fetch episodes for all podcasts in one query
    const { data: allEpisodes } = await supabase
      .from('podcast_episodes')
      .select('podcast_target_id, title, description')
      .in('podcast_target_id', toScore)
      .order('published_at', { ascending: false });

    // Group episodes by podcast
    const episodeMap = new Map<number, any[]>();
    if (allEpisodes) {
      for (const ep of allEpisodes) {
        const list = episodeMap.get(ep.podcast_target_id) || [];
        list.push(ep);
        episodeMap.set(ep.podcast_target_id, list);
      }
    }

    // Create placeholder pitch rows (unscored) so the UI can track progress
    // The actual scoring is done by the Python script: score_podcast_fit.py
    const pitchRows = podcasts.map((p: any) => ({
      podcast_target_id: p.id,
      speaker_profile_id: speaker.id,
      fit_tier: null,
      fit_score: null,
      pitch_status: 'unscored',
    }));

    const { error: insertError } = await supabase
      .from('podcast_pitches')
      .insert(pitchRows);

    if (insertError) {
      return Response.json(
        { error: `Failed to create pitch records: ${insertError.message}` },
        { status: 500 }
      );
    }

    return Response.json({
      status: 'started',
      count: toScore.length,
      already_scored: alreadyScored.size,
      message: `Created ${toScore.length} pitch records. Run score_podcast_fit.py --speaker ${body.speaker_slug.split('-')[0]} to score them.`,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to score podcasts';
    console.error('[Podcast Score] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
