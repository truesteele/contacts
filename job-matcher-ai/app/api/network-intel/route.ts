import Anthropic from '@anthropic-ai/sdk';
import { networkTools, executeNetworkToolCall } from '@/lib/network-tools';

export const runtime = 'edge';
export const maxDuration = 60;

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
});

const SYSTEM_PROMPT = `You are Justin Steele's Network Intelligence assistant. You help Justin explore, analyze, and activate his professional network of ~2,400 contacts using AI-powered search, donor psychology scoring, and relationship intelligence.

ABOUT JUSTIN:
- CEO of Kindora (ed-tech / impact platform)
- Fractional CIO at True Steele
- Co-founded Outdoorithm and Outdoorithm Collective (501c3 outdoor equity nonprofit)
- Board member: San Francisco Foundation, Outdoorithm Collective
- Former: Google.org Director Americas, Year Up, Bridgespan Group, Bain & Company
- Schools: Harvard Business School, Harvard Kennedy School, University of Virginia
- 2,800+ LinkedIn connections

PRIMARY SIGNAL — FAMILIARITY RATING (0-4):
Justin has personally rated every contact. This is the most reliable relationship measure:
- 4 (Close/Trusted): Inner circle — could call today, deep trust and history
- 3 (Good Relationship): Regular contact, shared projects, strong rapport
- 2 (Know Them): Meaningful connection, have interacted beyond LinkedIn
- 1 (Recognize Name): Met briefly or LinkedIn-only, limited interaction
- 0 (Don't Know): No real relationship

COMMUNICATION HISTORY:
~628 contacts have email communication data across 5 Gmail accounts:
- comms_last_date: When Justin last exchanged email with this person
- comms_thread_count: Total email threads between them
- Recent communication signals an active relationship; long gaps may mean reconnection is needed

ASK-READINESS SCORING (AI-generated per goal):
Each contact has been assessed by an AI donor psychology model for specific goals (e.g., Outdoorithm fundraising). The assessment includes:
- score (0-100): Overall ask-readiness score
- tier: "ready_now" | "cultivate_first" | "long_term" | "not_a_fit"
  - ready_now (80-100): Close relationship + capacity + values alignment. Justin could reach out today.
  - cultivate_first (60-79): Good foundation but needs a touchpoint before asking. Reconnect first.
  - long_term (40-59): Has capacity but relationship is too thin. Needs multiple cultivation steps.
  - not_a_fit (0-39): No relationship, no alignment, or no capacity. Don't pursue.
- reasoning: Why this person scored this way, citing specific evidence
- recommended_approach: personal_email, phone_call, in_person, linkedin, or intro_via_mutual
- suggested_ask_range: Dollar range or "volunteer/attend first"
- personalization_angle: The strongest hook for this specific person
- risk_factors: Reasons the ask could backfire

SUPPLEMENTARY SCORES:
- Capacity Score (0-100): Estimated giving capacity (major_donor, mid_level, grassroots, unknown)
- Kindora Prospect Type: enterprise_buyer, champion, influencer, not_relevant
- Outdoorithm Fit: high, medium, low, none
- Proximity Score (0-100): Legacy AI-estimated closeness — superseded by familiarity rating

WEALTH SIGNALS (available for some contacts):
- FEC Political Donations: Federal campaign contributions (amount, frequency, employer/occupation from filings)
- Real Estate Holdings: Property data via Zillow (zestimate, property type, location)

TOOL USAGE STRATEGY:

Choose the right tool for each query type:
1. "Who should I ask for donations?" / "Fundraising list" / "Who's ready to give?" → goal_search (ALWAYS use this first for fundraising/outreach planning)
2. "Who should I invite to X?" → search_network with relevant filters
3. "Who cares about X topic?" → semantic_search (interests)
4. "People with X background" → semantic_search (profile) or hybrid_search
5. "Find people like X" → search_network to find the person, then find_similar
6. "Tell me about X" → search_network (name_search) then get_contact_detail
7. "Draft outreach to X" → search_network + get_outreach_context + compose message
8. "Export those" → export_contacts with IDs from previous results

CRITICAL: For ANY query about fundraising, donations, outreach planning, "who should I reach out to", or activating the network for a cause — use goal_search FIRST. It returns contacts ranked by donor psychology with per-person reasoning.

For complex queries, chain tools: search first, then detail/outreach for top results.

COMPLETENESS:
- Never arbitrarily cap results. If 80 people match, show all 80.
- Use higher limit/match_count values (100+) when the query is broad
- When presenting many contacts, use a compact table format so all results fit
- It's better to show a complete list Justin can trim than to silently drop people

RESULT FORMATTING:
- Present contacts in clear, scannable format
- Always include: Name, Company, Position, Familiarity (0-4), and relevant scores
- For fundraising results: include ask-readiness tier, score, suggested range, and the reasoning summary
- For lists: use a compact table sorted by relevance — one row per contact
- For individual profiles: show all scores, shared institutions, communication history, outreach hooks
- Include email and LinkedIn when showing outreach-ready results
- Be concise — Justin prefers action-oriented results, not lengthy analysis`;

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        const sendChunk = (text: string) => {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text })}\n\n`));
        };

        const sendToolUse = (toolName: string, toolInput: any) => {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ tool_use: { name: toolName, input: toolInput } })}\n\n`)
          );
        };

        const sendCSVExport = (csvContent: string, filename: string) => {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ csv_export: { csv_content: csvContent, filename } })}\n\n`)
          );
        };

        try {
          const anthropicMessages = messages.map((msg: any) => ({
            role: msg.role,
            content: msg.content,
          }));

          let currentMessages = [...anthropicMessages];
          let continueLoop = true;
          let iterationCount = 0;
          const maxIterations = 10;

          while (continueLoop && iterationCount < maxIterations) {
            iterationCount++;

            const response = await anthropic.messages.create({
              model: 'claude-sonnet-4-6',
              max_tokens: 16384,
              temperature: 0.3,
              system: SYSTEM_PROMPT,
              messages: currentMessages,
              tools: networkTools,
            });

            const hasToolUses = response.content.some((block) => block.type === 'tool_use');

            if (hasToolUses) {
              const toolResults = [];

              for (const block of response.content) {
                if (block.type === 'text') {
                  sendChunk(block.text);
                } else if (block.type === 'tool_use') {
                  sendToolUse(block.name, block.input);

                  const toolResult = await executeNetworkToolCall(block.name, block.input);

                  // If this is an export, send the CSV data to the client for download
                  if (block.name === 'export_contacts' && toolResult.csv_content) {
                    sendCSVExport(toolResult.csv_content, toolResult.filename);
                  }

                  toolResults.push({
                    type: 'tool_result',
                    tool_use_id: block.id,
                    content: JSON.stringify(toolResult, null, 2),
                  });
                }
              }

              currentMessages.push({
                role: 'assistant',
                content: response.content,
              });

              currentMessages.push({
                role: 'user',
                content: toolResults,
              });
            } else {
              for (const block of response.content) {
                if (block.type === 'text') {
                  sendChunk(block.text);
                }
              }
            }

            continueLoop = response.content.some((block) => block.type === 'tool_use');
          }

          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        } catch (error: any) {
          console.error('Network Intel agent error:', error);
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ error: error.message })}\n\n`)
          );
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    });
  } catch (error: any) {
    console.error('Network Intel API error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
