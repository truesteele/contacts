import { supabase } from '@/lib/supabase';

export async function GET() {
  try {
    // Total podcasts discovered
    const { count: totalPodcasts } = await supabase
      .from('podcast_targets')
      .select('*', { count: 'exact', head: true });

    // Podcasts by activity status
    const { data: activityRows } = await supabase
      .from('podcast_targets')
      .select('activity_status');

    const activityCounts: Record<string, number> = {};
    if (activityRows) {
      for (const row of activityRows) {
        const status = (row as any).activity_status || 'unknown';
        activityCounts[status] = (activityCounts[status] || 0) + 1;
      }
    }

    // Scored count by tier
    const { data: pitchRows } = await supabase
      .from('podcast_pitches')
      .select('fit_tier, pitch_status');

    const tierCounts: Record<string, number> = {};
    const pitchStatusCounts: Record<string, number> = {};
    if (pitchRows) {
      for (const row of pitchRows) {
        const tier = (row as any).fit_tier || 'unscored';
        tierCounts[tier] = (tierCounts[tier] || 0) + 1;

        const pStatus = (row as any).pitch_status || 'unknown';
        pitchStatusCounts[pStatus] = (pitchStatusCounts[pStatus] || 0) + 1;
      }
    }

    // Campaign outcomes
    const { data: campaignRows } = await supabase
      .from('podcast_campaigns')
      .select('outcome, send_method');

    const outcomeCounts: Record<string, number> = {};
    let totalSent = 0;
    if (campaignRows) {
      totalSent = campaignRows.length;
      for (const row of campaignRows) {
        const outcome = (row as any).outcome || 'pending';
        outcomeCounts[outcome] = (outcomeCounts[outcome] || 0) + 1;
      }
    }

    // Podcasts with verified emails
    const { count: withEmail } = await supabase
      .from('podcast_targets')
      .select('*', { count: 'exact', head: true })
      .not('host_email', 'is', null);

    const { count: verifiedEmail } = await supabase
      .from('podcast_targets')
      .select('*', { count: 'exact', head: true })
      .eq('email_verified', true);

    return Response.json({
      discovery: {
        total_podcasts: totalPodcasts ?? 0,
        with_email: withEmail ?? 0,
        verified_email: verifiedEmail ?? 0,
        by_activity: activityCounts,
      },
      scoring: {
        by_tier: tierCounts,
        by_pitch_status: pitchStatusCounts,
      },
      campaigns: {
        total_sent: totalSent,
        by_outcome: outcomeCounts,
      },
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch status';
    console.error('[Podcast Status] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
