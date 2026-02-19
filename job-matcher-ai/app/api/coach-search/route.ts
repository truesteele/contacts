import { supabase } from '@/lib/supabase';
import { generateEmbedding, rerankCoaches, CoachRecommendation } from '@/lib/openai';

export const runtime = 'edge';
export const maxDuration = 30;

export async function POST(req: Request) {
  try {
    const { query } = await req.json();

    if (!query || typeof query !== 'string' || query.trim().length === 0) {
      return Response.json({ error: 'Query is required' }, { status: 400 });
    }

    // Step 1: Generate embedding for the query
    const queryEmbedding = await generateEmbedding(query.trim());

    // Step 2: Call hybrid search RPC (vector + full-text + RRF fusion)
    const { data: candidates, error } = await supabase.rpc('hybrid_search_coaches', {
      query_embedding: queryEmbedding,
      query_text: query.trim(),
      match_count: 10,
    });

    if (error) {
      console.error('Hybrid search error:', error);
      return Response.json({ error: 'Search failed' }, { status: 500 });
    }

    if (!candidates || candidates.length === 0) {
      return Response.json({ recommendations: [], query });
    }

    // Step 3: AI rerank with GPT-5-mini for rationale
    const reranked = await rerankCoaches(query.trim(), candidates as CoachRecommendation[]);

    return Response.json({
      recommendations: reranked,
      query,
      total_candidates: candidates.length,
    });
  } catch (error) {
    console.error('Coach search error:', error);
    return Response.json(
      { error: 'An unexpected error occurred' },
      { status: 500 }
    );
  }
}
