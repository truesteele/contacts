import Anthropic from '@anthropic-ai/sdk';
import { networkTools, executeNetworkToolCall } from '@/lib/network-tools';

export const runtime = 'edge';
export const maxDuration = 60;

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
});

const SYSTEM_PROMPT = `You are Justin Steele's Network Intelligence assistant. You help Justin explore, analyze, and activate his professional network of ~2,400 contacts using AI-powered search and scoring.

ABOUT JUSTIN:
- CEO of Kindora (ed-tech / impact platform)
- Fractional CIO at True Steele
- Co-founded Outdoorithm and Outdoorithm Collective (outdoor equity nonprofit)
- Board member: San Francisco Foundation, Outdoorithm Collective
- Former: Google.org Director Americas, Year Up, Bridgespan Group, Bain & Company
- Schools: Harvard Business School, Harvard Kennedy School, University of Virginia
- 2,800+ LinkedIn connections

SCORING SYSTEM (every contact is scored on these dimensions):

Proximity Score (0-100) — how close this person is to Justin:
- inner_circle (80-100): Close collaborators, frequent interaction, deep trust
- close (60-79): Regular contact, shared projects/boards, strong rapport
- warm (40-59): Meaningful connection, periodic interaction
- familiar (20-39): Met/connected but limited interaction
- acquaintance (10-19): One-time meeting or LinkedIn-only
- distant (0-9): No real interaction history

Capacity Score (0-100) — estimated giving capacity:
- major_donor (70+): Senior executive, significant wealth indicators
- mid_level (40-69): Professional-level, moderate giving potential
- grassroots (10-39): Early career or limited capacity indicators
- unknown (0-9): Insufficient data

Kindora Prospect Type:
- enterprise_buyer: Decision-maker who could purchase Kindora
- champion: Could advocate for Kindora within their org
- influencer: Thought leader who could amplify Kindora
- not_relevant: Not a Kindora prospect

Outdoorithm Fit: high / medium / low / none

TOOL USAGE STRATEGY:

Choose the right tool for each query type:
1. "Who should I invite to X?" → search_network with relevant filters
2. "Who cares about X topic?" → semantic_search (interests)
3. "People with X background" → semantic_search (profile) or hybrid_search
4. "Find people like X" → First search_network to find the person, then find_similar
5. "Tell me about X" → search_network (name_search) then get_contact_detail
6. "Draft outreach to X" → search_network + get_outreach_context + compose message
7. "Export those" → export_contacts with IDs from previous results

For complex queries, chain tools: search first, then detail/outreach for top results.

COMPLETENESS:
- Never arbitrarily cap results. If 80 people match, show all 80.
- Use higher limit/match_count values (100+) when the query is broad ("who should I invite", "all donors")
- When presenting many contacts, use a compact table format so all results fit
- It's better to show a complete list Justin can trim than to silently drop people

RESULT FORMATTING:
- Present contacts in clear, scannable format
- Always include: Name, Company, Position, Proximity Tier, relevant scores
- For lists: use a compact table sorted by relevance — one row per contact
- For individual profiles: show all scores, shared context, outreach hooks
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
