import { NextRequest } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET(req: NextRequest) {
  try {
    const params = req.nextUrl.searchParams;
    const speaker = params.get('speaker') || '';
    const status = params.get('status') || '';
    const fitTier = params.get('fit_tier') || '';
    const discoveryMethod = params.get('discovery_method') || '';
    const category = params.get('category') || '';
    const activeIn2026 = params.get('active_2026') === 'true';
    const bookmarked = params.get('bookmarked') === 'true';
    const search = params.get('search') || '';
    const page = Math.max(1, parseInt(params.get('page') || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(params.get('limit') || '25', 10)));
    const offset = (page - 1) * limit;

    // ── Resolve speaker ──────────────────────────────────────────────
    let speakerProfileId: number | null = null;
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

    // ── Speaker-driven path: sort by fit_score ───────────────────────
    // When a speaker is selected, we drive pagination from podcast_pitches
    // so the sort order is by fit_score descending across all pages.
    if (speakerProfileId) {
      // Step 1: Fetch ALL pitches for this speaker (sorted by fit_score desc)
      let allPitches: Array<{
        podcast_target_id: number;
        fit_tier: string | null;
        fit_score: number | null;
        fit_rationale: string | null;
        topic_match: unknown;
        pitch_status: string | null;
        subject_line: string | null;
        pitch_body: string | null;
        is_bookmarked: boolean;
        user_notes: string;
      }> = [];

      // Paginate pitch loading (Supabase caps at 1000)
      let pitchOffset = 0;
      const pitchPageSize = 1000;
      while (true) {
        let pitchQuery = supabase
          .from('podcast_pitches')
          .select('podcast_target_id, fit_tier, fit_score, fit_rationale, topic_match, pitch_status, subject_line, pitch_body, is_bookmarked, user_notes')
          .eq('speaker_profile_id', speakerProfileId)
          .order('fit_score', { ascending: false, nullsFirst: false })
          .range(pitchOffset, pitchOffset + pitchPageSize - 1);

        if (bookmarked) {
          pitchQuery = pitchQuery.eq('is_bookmarked', true);
        }

        if (fitTier) {
          pitchQuery = pitchQuery.eq('fit_tier', fitTier);
        }

        const { data: pitchBatch, error: pitchError } = await pitchQuery;
        if (pitchError) {
          return Response.json(
            { error: `Failed to fetch pitches: ${pitchError.message}` },
            { status: 500 }
          );
        }
        allPitches = allPitches.concat(pitchBatch || []);
        if (!pitchBatch || pitchBatch.length < pitchPageSize) break;
        pitchOffset += pitchPageSize;
      }

      // Step 2: Get the podcast IDs in score order
      const allPodcastIds = allPitches.map(p => p.podcast_target_id);

      if (allPodcastIds.length === 0) {
        return Response.json({
          podcasts: [],
          total: 0,
          page,
          limit,
          total_pages: 0,
        });
      }

      // Step 3: Apply podcast-side filters to narrow down the ID list
      // We need to fetch podcasts that match filters, then intersect with pitch IDs
      let filterQuery = supabase
        .from('podcast_targets')
        .select('id')
        .in('id', allPodcastIds);

      if (status) filterQuery = filterQuery.eq('activity_status', status);
      if (discoveryMethod) filterQuery = filterQuery.contains('discovery_methods', [discoveryMethod]);
      if (category) filterQuery = filterQuery.contains('categories', [category]);
      if (activeIn2026) filterQuery = filterQuery.gte('last_episode_date', '2026-01-01T00:00:00Z');
      if (search) {
        const sanitized = search.replace(/[%.,()]/g, '');
        if (sanitized) {
          filterQuery = filterQuery.or(
            `title.ilike.%${sanitized}%,author.ilike.%${sanitized}%,description.ilike.%${sanitized}%`
          );
        }
      }

      // Fetch all matching IDs (paginate if needed)
      let filteredIds = new Set<number>();
      let filterOffset = 0;
      while (true) {
        const { data: batch } = await filterQuery.range(filterOffset, filterOffset + 999);
        if (!batch || batch.length === 0) break;
        for (const row of batch) filteredIds.add(row.id);
        if (batch.length < 1000) break;
        filterOffset += 1000;
      }

      // Step 4: Intersect — keep pitch order, only include filtered IDs
      const orderedFilteredIds = allPodcastIds.filter(id => filteredIds.has(id));
      const totalFiltered = orderedFilteredIds.length;

      // Step 5: Paginate the ordered list
      const pageIds = orderedFilteredIds.slice(offset, offset + limit);

      if (pageIds.length === 0) {
        return Response.json({
          podcasts: [],
          total: totalFiltered,
          page,
          limit,
          total_pages: Math.ceil(totalFiltered / limit),
        });
      }

      // Step 6: Fetch full podcast data for this page
      const { data: podcasts, error: podcastError } = await supabase
        .from('podcast_targets')
        .select('*')
        .in('id', pageIds);

      if (podcastError) {
        return Response.json(
          { error: `Failed to fetch podcasts: ${podcastError.message}` },
          { status: 500 }
        );
      }

      // Step 7: Merge pitches and preserve score order
      const pitchMap = new Map(allPitches.map(p => [p.podcast_target_id, p]));
      const podcastMap = new Map((podcasts || []).map((p: any) => [p.id, p]));

      const ordered = pageIds
        .map(id => {
          const podcast = podcastMap.get(id);
          if (!podcast) return null;
          return { ...podcast, pitch: pitchMap.get(id) || null };
        })
        .filter(Boolean);

      return Response.json({
        podcasts: ordered,
        total: totalFiltered,
        page,
        limit,
        total_pages: Math.ceil(totalFiltered / limit),
      });
    }

    // ── No-speaker path: sort by discovered_at ───────────────────────
    let query = supabase
      .from('podcast_targets')
      .select('*', { count: 'exact' });

    if (status) query = query.eq('activity_status', status);
    if (discoveryMethod) query = query.contains('discovery_methods', [discoveryMethod]);
    if (category) query = query.contains('categories', [category]);
    if (activeIn2026) query = query.gte('last_episode_date', '2026-01-01T00:00:00Z');
    if (search) {
      const sanitized = search.replace(/[%.,()]/g, '');
      if (sanitized) {
        query = query.or(
          `title.ilike.%${sanitized}%,author.ilike.%${sanitized}%,description.ilike.%${sanitized}%`
        );
      }
    }

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

    return Response.json({
      podcasts: podcasts || [],
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
