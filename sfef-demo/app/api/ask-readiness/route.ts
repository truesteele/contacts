import { MOCK_CONTACTS } from '@/lib/mock-data';

export async function GET() {
  const contacts = [...MOCK_CONTACTS].sort((a, b) => b.score - a.score);

  return Response.json({
    contacts,
    total: contacts.length,
    goal: 'sfef_individual_giving',
    tier_counts: {
      ready_now: contacts.filter((c) => c.tier === 'ready_now').length,
      cultivate_first: contacts.filter((c) => c.tier === 'cultivate_first').length,
      long_term: contacts.filter((c) => c.tier === 'long_term').length,
      not_a_fit: contacts.filter((c) => c.tier === 'not_a_fit').length,
    },
  });
}
