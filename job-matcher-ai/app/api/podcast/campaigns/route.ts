import { NextRequest } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET(req: NextRequest) {
  try {
    const params = req.nextUrl.searchParams;
    const speaker = params.get('speaker') || '';
    const outcome = params.get('outcome') || '';
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

    // Build campaign query — when search is active, fetch all rows first
    // so we can filter across joined fields before paginating
    let query = supabase
      .from('podcast_campaigns')
      .select('*', { count: 'exact' });

    if (speakerId) {
      query = query.eq('speaker_profile_id', speakerId);
    }

    if (outcome && outcome !== 'all') {
      query = query.eq('outcome', outcome);
    }

    query = query.order('sent_at', { ascending: false });

    // Only paginate at DB level when there's no cross-table search
    if (!search) {
      query = query.range(offset, offset + limit - 1);
    }

    const { data: campaigns, error: campaignError, count } = await query;

    if (campaignError) {
      return Response.json(
        { error: `Failed to fetch campaigns: ${campaignError.message}` },
        { status: 500 }
      );
    }

    if (!campaigns || campaigns.length === 0) {
      return Response.json({
        campaigns: [],
        total: 0,
        page,
        limit,
        total_pages: 0,
      });
    }

    // Fetch associated pitches
    const pitchIds = [...new Set(campaigns.map((c: any) => c.pitch_id).filter(Boolean))];
    const pitchMap = new Map<number, any>();
    if (pitchIds.length > 0) {
      const { data: pitches } = await supabase
        .from('podcast_pitches')
        .select('id, podcast_target_id, subject_line, pitch_status, fit_tier')
        .in('id', pitchIds);
      if (pitches) {
        for (const p of pitches) pitchMap.set(p.id, p);
      }
    }

    // Fetch associated podcasts
    const podcastIds = [...new Set(
      Array.from(pitchMap.values()).map((p: any) => p.podcast_target_id).filter(Boolean)
    )];
    const podcastMap = new Map<number, any>();
    if (podcastIds.length > 0) {
      const { data: podcasts } = await supabase
        .from('podcast_targets')
        .select('id, title, author, host_name, host_email')
        .in('id', podcastIds);
      if (podcasts) {
        for (const p of podcasts) podcastMap.set(p.id, p);
      }
    }

    // Fetch speaker names
    const speakerIds = [...new Set(campaigns.map((c: any) => c.speaker_profile_id).filter(Boolean))];
    const speakerMap = new Map<number, any>();
    if (speakerIds.length > 0) {
      const { data: speakers } = await supabase
        .from('speaker_profiles')
        .select('id, name, slug')
        .in('id', speakerIds);
      if (speakers) {
        for (const s of speakers) speakerMap.set(s.id, s);
      }
    }

    // Merge
    let merged = campaigns.map((c: any) => {
      const pitch = pitchMap.get(c.pitch_id) || null;
      const podcast = pitch ? podcastMap.get(pitch.podcast_target_id) || null : null;
      return {
        ...c,
        pitch,
        podcast,
        speaker: speakerMap.get(c.speaker_profile_id) || null,
      };
    });

    // Search filter (cross-table: podcast title, pitch subject, notes, email)
    // When search is active, we fetched all rows above and paginate after filtering
    if (search) {
      const q = search.toLowerCase();
      merged = merged.filter(
        (c: any) =>
          c.podcast?.title?.toLowerCase().includes(q) ||
          c.pitch?.subject_line?.toLowerCase().includes(q) ||
          c.notes?.toLowerCase().includes(q) ||
          c.sent_to_email?.toLowerCase().includes(q)
      );
    }

    // When search is active, paginate the filtered results
    const filteredTotal = search ? merged.length : (count ?? 0);
    const filteredTotalPages = Math.ceil(filteredTotal / limit);
    if (search) {
      merged = merged.slice(offset, offset + limit);
    }

    // Pipeline stats for dashboard
    const { data: allPitches } = await supabase
      .from('podcast_pitches')
      .select('pitch_status');

    const pipeline: Record<string, number> = {
      draft: 0,
      approved: 0,
      sent: 0,
      replied: 0,
      booked: 0,
    };
    if (allPitches) {
      for (const p of allPitches) {
        const s = (p as any).pitch_status || 'draft';
        if (s in pipeline) pipeline[s]++;
      }
    }

    // Campaign outcome stats
    const { data: allCampaigns } = await supabase
      .from('podcast_campaigns')
      .select('outcome');

    const outcomes: Record<string, number> = {
      pending: 0,
      booked: 0,
      declined: 0,
      no_response: 0,
      maybe_later: 0,
    };
    let totalSent = 0;
    if (allCampaigns) {
      totalSent = allCampaigns.length;
      for (const c of allCampaigns) {
        const o = (c as any).outcome || 'pending';
        if (o in outcomes) outcomes[o]++;
        else outcomes[o] = 1;
      }
    }

    return Response.json({
      campaigns: merged,
      total: filteredTotal,
      page,
      limit,
      total_pages: filteredTotalPages,
      stats: {
        total_sent: totalSent,
        pipeline,
        outcomes,
      },
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to fetch campaigns';
    console.error('[Podcast Campaigns] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}

export async function PATCH(req: Request) {
  try {
    const body = await req.json() as {
      campaign_id: number;
      notes?: string;
      outcome?: string;
    };

    if (!body.campaign_id) {
      return Response.json({ error: 'campaign_id is required' }, { status: 400 });
    }

    const updates: Record<string, any> = {
      updated_at: new Date().toISOString(),
    };

    if (body.notes !== undefined) {
      updates.notes = body.notes;
    }

    if (body.outcome !== undefined) {
      const valid = ['pending', 'booked', 'declined', 'no_response', 'maybe_later'];
      if (!valid.includes(body.outcome)) {
        return Response.json(
          { error: `Invalid outcome. Must be one of: ${valid.join(', ')}` },
          { status: 400 }
        );
      }
      updates.outcome = body.outcome;

      // Keep pitch status in sync with campaign outcome
      const { data: campaign } = await supabase
        .from('podcast_campaigns')
        .select('pitch_id, outcome')
        .eq('id', body.campaign_id)
        .single();

      if (campaign?.pitch_id) {
        const pitchStatus = body.outcome === 'booked' ? 'booked' : 'sent';
        await supabase
          .from('podcast_pitches')
          .update({ pitch_status: pitchStatus, updated_at: new Date().toISOString() })
          .eq('id', campaign.pitch_id);
      }
    }

    const { error: updateError } = await supabase
      .from('podcast_campaigns')
      .update(updates)
      .eq('id', body.campaign_id);

    if (updateError) {
      return Response.json(
        { error: `Failed to update campaign: ${updateError.message}` },
        { status: 500 }
      );
    }

    return Response.json({ status: 'updated', campaign_id: body.campaign_id });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to update campaign';
    console.error('[Podcast Campaigns] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
