import { supabase } from '@/lib/supabase';

export async function GET() {
  try {
    const { data: profiles, error } = await supabase
      .from('speaker_profiles')
      .select('*')
      .order('name', { ascending: true });

    if (error) {
      return Response.json(
        { error: `Failed to fetch profiles: ${error.message}` },
        { status: 500 }
      );
    }

    return Response.json({ profiles: profiles || [] });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch profiles';
    console.error('[Podcast Profiles] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
