import { NextRequest } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET(req: NextRequest) {
  try {
    const podcastId = req.nextUrl.searchParams.get('id');
    const speaker = req.nextUrl.searchParams.get('speaker') || '';

    if (!podcastId) {
      return Response.json({ error: 'Missing podcast id' }, { status: 400 });
    }

    const id = parseInt(podcastId, 10);
    if (isNaN(id)) {
      return Response.json({ error: 'Invalid podcast id' }, { status: 400 });
    }

    // Fetch the podcast with all columns including podcast_profile
    const { data: podcast, error: podcastError } = await supabase
      .from('podcast_targets')
      .select('*')
      .eq('id', id)
      .single();

    if (podcastError || !podcast) {
      return Response.json(
        { error: `Podcast not found: ${podcastError?.message || 'no data'}` },
        { status: 404 }
      );
    }

    // Fetch recent episodes (up to 10)
    const { data: episodes } = await supabase
      .from('podcast_episodes')
      .select('*')
      .eq('podcast_target_id', id)
      .order('published_at', { ascending: false })
      .limit(10);

    // Fetch pitch data for the speaker if specified
    let pitch = null;
    if (speaker) {
      const { data: speakerProfile } = await supabase
        .from('speaker_profiles')
        .select('id')
        .eq('slug', speaker)
        .single();

      if (speakerProfile) {
        const { data: pitchData } = await supabase
          .from('podcast_pitches')
          .select('*')
          .eq('podcast_target_id', id)
          .eq('speaker_profile_id', speakerProfile.id)
          .single();

        pitch = pitchData;
      }
    }

    return Response.json({
      podcast,
      episodes: episodes || [],
      pitch,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch podcast detail';
    console.error('[Podcast Detail] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
