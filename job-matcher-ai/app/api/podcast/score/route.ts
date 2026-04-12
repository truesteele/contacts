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
        { error: 'speaker_slug is required (e.g., "sally" or "justin")' },
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

    // Check which podcasts already have pitch rows for this speaker.
    // Rows with null fit_score are pending placeholders created by this route.
    const { data: existingPitches } = await supabase
      .from('podcast_pitches')
      .select('podcast_target_id, fit_score')
      .eq('speaker_profile_id', speaker.id)
      .in('podcast_target_id', body.podcast_ids);

    const alreadyPrepared = new Set(
      (existingPitches || []).map((p: any) => p.podcast_target_id)
    );
    const toScore = body.podcast_ids.filter((id) => !alreadyPrepared.has(id));

    if (toScore.length === 0) {
      return Response.json({
        status: 'prepared',
        message: 'All selected podcasts already have pitch rows for this speaker',
        already_prepared: body.podcast_ids.length,
        newly_prepared: 0,
      });
    }

    // Create placeholder pitch rows so the scorer can update them later.
    const pitchRows = toScore.map((podcastId) => ({
      podcast_target_id: podcastId,
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
      status: 'prepared',
      count: toScore.length,
      already_prepared: alreadyPrepared.size,
      message: `Prepared ${toScore.length} podcasts for scoring. Run score_podcast_fit.py --speaker ${body.speaker_slug} to score them.`,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to score podcasts';
    console.error('[Podcast Score] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
