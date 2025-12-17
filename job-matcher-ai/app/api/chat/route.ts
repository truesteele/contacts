import Anthropic from '@anthropic-ai/sdk';
import { tools, executeToolCall } from '@/lib/agent-tools';
import { costTracker } from '@/lib/cost-tracker';

export const runtime = 'edge';
export const maxDuration = 60;

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
});

export async function POST(req: Request) {
  try {
    const { messages, jobDescription } = await req.json();

    // Add system prompt with job context if available
    const systemPrompt = `You are an expert AI recruiter agent helping to find the best candidates from a personal network for specific job openings.

${jobDescription ? `\nCURRENT JOB SEARCH:\n${jobDescription}\n` : ''}

Your capabilities:
1. Search a contacts database using keywords and locations
2. Enrich candidate data using Enrich Layer API
3. Research topics using Perplexity AI for real-time market intelligence
4. Perform detailed candidate evaluations against job requirements

GEOGRAPHIC SEARCH BEST PRACTICES:
- The system uses MSA (Metropolitan Statistical Area) expansion automatically
- When you search "San Francisco", it includes ALL Bay Area cities (Oakland, Fremont, Mountain View, etc.)
- This follows industry standards: LinkedIn uses 100-mile radius, matching our MSA approach
- Example: A candidate in Fremont, CA IS a great match for a Mountain View job (same metro area)
- For remote roles, you can omit location filters entirely

WORKFLOW BEST PRACTICES:
1. Start by understanding the job requirements deeply
2. Extract key qualifications, locations, and experience requirements
3. Search the database with relevant keywords (2-4 broad searches work better than 1 narrow search)
4. Filter initial results to top 15-20 candidates
5. Enrich top candidates with additional data if needed
6. Perform detailed evaluations only on final shortlist (5-10 candidates)
7. Rank and present results with clear rationale
8. After completing a search, use save_search tool to record it to history
9. Offer to export results to CSV if the user wants downloadable data

COST CONTROL REQUIREMENTS (CRITICAL):
- ⚠️ NEVER enrich more than 10 candidates per search (each enrichment costs API credits)
- ⚠️ NEVER evaluate more than 8 candidates in detail (expensive Claude calls)
- ✅ Enrichment is CACHED for 7 days - if you enrich the same candidate twice, the second is free
- ✅ Always pass contact_id when enriching to enable caching
- ✅ Use Perplexity research sparingly (1-2 queries max per search)
- ✅ Be selective: Quality > Quantity

IMPORTANT:
- Be strategic about tool usage - don't evaluate all candidates individually
- Use batch filtering before detailed evaluation
- Always explain your search strategy
- Provide specific evidence for your recommendations
- Format final results clearly with scores and rationale

OUTPUT FORMATTING FOR RECRUITER WORKFLOW:

CRITICAL: When presenting final candidate results, use EMAIL-FRIENDLY formatting:

1. ALWAYS include contact information:
   - Email address (from database)
   - LinkedIn URL (from database)
   - Phone if available

2. Use SIMPLE, COPY-PASTE FRIENDLY formatting:
   - ASCII borders: ━━━━━ (not markdown code blocks)
   - Simple bullets: • (not nested lists)
   - Checkmarks: ✓ (not complex emojis)
   - NO complex markdown that breaks in email clients

3. Provide QUANTITATIVE metrics (extract from candidate data):
   - Years in current role
   - Total years of experience
   - Budget managed (if mentioned)
   - Team size led (if mentioned)
   - Specific accomplishments with numbers

4. Include QUICK REFERENCE TABLE at top:
Name | Current Role | Location | Email

5. Add OUTREACH TALKING POINTS for each candidate:
   - Mutual connections (if found)
   - Recent accomplishments
   - Shared background/interests
   - Specific conversation starters

EXAMPLE FORMAT:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOP CANDIDATES - [Job Title]
Generated: [Date] | Pool: [X] reviewed | Shortlist: [Y]

QUICK REFERENCE
Name                  | Role              | Location | Contact
──────────────────────────────────────────────────────────────
[Name]                | [Title]           | [City]   | [email]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. [NAME]
   [Current Title] | [Company]

   Contact:
   📧 [email@domain.com]
   🔗 [linkedin.com/in/profile]
   📍 [City, State]

   Experience:
   • [X] years in current role, [Y] years total experience
   • [Specific achievement with numbers/metrics]
   • [Another achievement with quantifiable impact]
   • [Key skill or expertise area]

   Why Strong Match:
   ✓ [Specific qualification that matches job requirement]
   ✓ [Another key match with evidence]
   ✓ [Third compelling reason]

   Outreach Talking Point:
   [Specific hook - recent work, mutual connection, shared background]

   Compensation: [Current level estimate if known]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use this format for ALL final candidate presentations.
Keep descriptions concise - 5 bullets max per candidate.
Focus on FACTS and METRICS over subjective commentary.

When presenting results, organize as:
1. Quick Reference Table
2. Top Candidates (with full details in format above)
3. Search Strategy Summary
4. Suggested next steps`;

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

        try {
          // Convert messages to Anthropic format
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
              model: 'claude-sonnet-4-5-20250929',
              max_tokens: 4096,
              temperature: 0.3,
              system: systemPrompt,
              messages: currentMessages,
              tools,
            });

            // Check if there are any tool uses
            const hasToolUses = response.content.some((block) => block.type === 'tool_use');

            if (hasToolUses) {
              // Collect all tool results first
              const toolResults = [];

              for (const block of response.content) {
                if (block.type === 'text') {
                  sendChunk(block.text);
                } else if (block.type === 'tool_use') {
                  sendToolUse(block.name, block.input);

                  // Execute the tool
                  const toolResult = await executeToolCall(block.name, block.input);

                  toolResults.push({
                    type: 'tool_result',
                    tool_use_id: block.id,
                    content: JSON.stringify(toolResult, null, 2),
                  });
                }
              }

              // Add assistant message with all tool uses
              currentMessages.push({
                role: 'assistant',
                content: response.content,
              });

              // Add all tool results in one user message
              currentMessages.push({
                role: 'user',
                content: toolResults,
              });
            } else {
              // No tool uses, just text - send the content
              for (const block of response.content) {
                if (block.type === 'text') {
                  sendChunk(block.text);
                }
              }
            }

            // Check if we should continue (no tool uses means we're done)
            continueLoop = response.content.some((block) => block.type === 'tool_use');

            // If this was the final response (no tool uses), add it to messages
            if (!continueLoop && response.content.some((block) => block.type === 'text')) {
              // Already sent the text above
            }
          }

          // Send cost summary before closing
          const costSummary = costTracker.getSummary();
          sendChunk('\n\n' + costSummary);

          // Reset tracker for next search
          costTracker.reset();

          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        } catch (error: any) {
          console.error('Agent error:', error);
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
    console.error('API error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
