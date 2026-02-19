import OpenAI from 'openai';

let _openai: OpenAI | null = null;

function getOpenAI(): OpenAI {
  if (!_openai) {
    if (!process.env.OPENAI_APIKEY) {
      throw new Error('Missing OPENAI_APIKEY environment variable');
    }
    _openai = new OpenAI({ apiKey: process.env.OPENAI_APIKEY });
  }
  return _openai;
}

export async function generateEmbedding(text: string): Promise<number[]> {
  const response = await getOpenAI().embeddings.create({
    model: 'text-embedding-3-small',
    input: text,
  });
  return response.data[0].embedding;
}

export async function generateEmbedding768(text: string): Promise<number[]> {
  const response = await getOpenAI().embeddings.create({
    model: 'text-embedding-3-small',
    input: text,
    dimensions: 768,
  });
  return response.data[0].embedding;
}

export interface CoachRecommendation {
  expert_id: number;
  expert_name: string;
  expert_position: string;
  expert_organization: string;
  expert_areas: string;
  expert_headline: string;
  expert_profile_picture_url: string | null;
  expert_linkedin_url: string | null;
  expert_profile_url: string | null;
  expert_follower_count: number | null;
  coaching_summary: string;
  expertise_tags: string[];
  coaching_strengths: string[];
  ideal_for: string;
  rrf_score: number;
  match_rationale?: string;
  match_score?: number;
}

export async function rerankCoaches(
  query: string,
  candidates: CoachRecommendation[]
): Promise<CoachRecommendation[]> {
  const candidateSummaries = candidates.map((c, i) => (
    `[${i + 1}] ${c.expert_name} — ${c.expert_position} at ${c.expert_organization}
Expertise: ${c.expertise_tags.join(', ')}
Strengths: ${c.coaching_strengths.join(', ')}
Ideal for: ${c.ideal_for}
Summary: ${c.coaching_summary.slice(0, 400)}`
  )).join('\n\n');

  const response = await getOpenAI().chat.completions.create({
    model: 'gpt-5-mini',
    max_completion_tokens: 2000,
    response_format: { type: 'json_object' },
    messages: [
      {
        role: 'system',
        content: `You are an expert at matching founders with the right coaches/advisors. Given a founder's query and a list of coach candidates, rerank them by relevance and provide specific rationale for each match.

Return JSON:
{
  "recommendations": [
    {
      "index": 1,
      "match_score": 9,
      "rationale": "2-3 sentence explanation of why this coach is a great match for the specific query. Be specific about which of their skills/experience aligns."
    }
  ]
}

Rules:
- Return the top 5 most relevant candidates, reranked by fit
- match_score is 1-10 (10 = perfect match)
- rationale should reference specific expertise that matches the query
- If a candidate is a poor match, don't include them`
      },
      {
        role: 'user',
        content: `Query: "${query}"\n\nCandidates:\n${candidateSummaries}`
      }
    ],
  });

  const content = response.choices[0].message.content;
  if (!content) return candidates.slice(0, 5);

  try {
    const result = JSON.parse(content);
    const recommendations = result.recommendations || [];

    return recommendations
      .map((rec: { index: number; match_score: number; rationale: string }) => {
        const candidate = candidates[rec.index - 1];
        if (!candidate) return null;
        return {
          ...candidate,
          match_rationale: rec.rationale,
          match_score: rec.match_score,
        };
      })
      .filter(Boolean) as CoachRecommendation[];
  } catch {
    return candidates.slice(0, 5);
  }
}
