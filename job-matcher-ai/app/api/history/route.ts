import { getRecentSearches, getCostStatistics } from '@/lib/search-history';

export const runtime = 'edge';

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const action = url.searchParams.get('action') || 'recent';
    const limit = parseInt(url.searchParams.get('limit') || '20');

    if (action === 'stats') {
      const stats = await getCostStatistics();
      return new Response(JSON.stringify(stats), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Default: return recent searches
    const searches = await getRecentSearches(limit);
    return new Response(JSON.stringify(searches), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error: any) {
    console.error('History API error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
