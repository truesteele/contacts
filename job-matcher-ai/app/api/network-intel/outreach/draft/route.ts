import { NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';
import { supabase } from '@/lib/supabase';

export const runtime = 'edge';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
});

const TONE_DESCRIPTIONS: Record<string, string> = {
  warm_professional:
    'Warm but professional. Friendly and personable while maintaining credibility. Use a conversational tone that references shared connections or context naturally.',
  formal:
    'Formal and polished. Appropriate for senior executives or first-time outreach to high-profile contacts. Respectful, concise, and clearly stating the purpose.',
  casual:
    'Casual and friendly. Like reaching out to a friend or close colleague. Relaxed language, can use humor or informal references.',
  networking:
    'Networking-oriented. Focus on mutual value, shared interests, and exploring potential collaboration. Not asking for anything specific, just building the relationship.',
  fundraising:
    'Fundraising-focused. Clear ask with compelling mission framing. Connect the donor\'s interests/values to the cause. Include specific impact metrics or stories when possible.',
};

const SYSTEM_PROMPT = `You are drafting personalized outreach emails on behalf of Justin Steele. Write emails that feel genuinely personal — not templated or AI-generated.

ABOUT JUSTIN:
- CEO of Kindora (ed-tech / impact platform)
- Fractional CIO at True Steele
- Co-founded Outdoorithm and Outdoorithm Collective (outdoor equity nonprofit)
- Board member: San Francisco Foundation, Outdoorithm Collective
- Former: Google.org Director Americas, Year Up, Bridgespan Group, Bain & Company
- Schools: Harvard Business School, Harvard Kennedy School, University of Virginia

GUIDELINES:
- Write in first person as Justin
- Keep emails concise (150-250 words for the body)
- Reference specific shared context (employers, schools, boards, interests) when available
- Open with something personal — NOT "I hope this email finds you well"
- The subject line should be specific and compelling (not generic)
- End with a clear but low-pressure call to action
- Sound like a real person writing a real email, not a form letter
- Include unsubscribe text at the very bottom: "If you'd prefer not to receive emails like this, just reply and let me know."`;

interface ContactContext {
  name: string;
  company: string | null;
  position: string | null;
  headline: string | null;
  location: string;
  email: string | null;
  proximity_tier: string | null;
  proximity_score: number | null;
  capacity_tier: string | null;
  shared_employers: string[];
  shared_schools: string[];
  shared_boards: string[];
  topics: string[];
  primary_interests: string[];
  talking_points: string[];
  personalization_hooks: string[];
  suggested_opener: string;
  best_approach: string;
}

async function fetchContactContext(contactId: number): Promise<ContactContext> {
  const { data, error } = await supabase
    .from('contacts')
    .select(
      'id, first_name, last_name, company, position, headline, city, state, email, personal_email, work_email, ' +
        'ai_proximity_score, ai_proximity_tier, ai_capacity_tier, ai_tags'
    )
    .eq('id', contactId)
    .single();

  if (error || !data) {
    throw new Error(`Contact ${contactId} not found`);
  }

  const c = data as any;
  const tags = c.ai_tags || {};
  const outreach = tags.outreach_context || {};
  const proximity = tags.relationship_proximity || {};
  const affinity = tags.topical_affinity || {};

  return {
    name: `${c.first_name} ${c.last_name}`,
    company: c.company,
    position: c.position,
    headline: c.headline,
    location: [c.city, c.state].filter(Boolean).join(', '),
    email: c.email || c.personal_email || c.work_email,
    proximity_tier: c.ai_proximity_tier,
    proximity_score: c.ai_proximity_score,
    capacity_tier: c.ai_capacity_tier,
    shared_employers: proximity.shared_employers || [],
    shared_schools: proximity.shared_schools || [],
    shared_boards: proximity.shared_boards || [],
    topics: (affinity.topics || []).slice(0, 8),
    primary_interests: affinity.primary_interests || [],
    talking_points: affinity.talking_points || [],
    personalization_hooks: outreach.personalization_hooks || [],
    suggested_opener: outreach.suggested_opener || '',
    best_approach: outreach.best_approach || '',
  };
}

function buildDraftPrompt(
  contact: ContactContext,
  tone: string,
  userContext?: string
): string {
  const toneDesc = TONE_DESCRIPTIONS[tone] || TONE_DESCRIPTIONS.warm_professional;

  const parts: string[] = [
    `RECIPIENT: ${contact.name}`,
    contact.company ? `Company: ${contact.company}` : null,
    contact.position ? `Position: ${contact.position}` : null,
    contact.headline ? `Headline: ${contact.headline}` : null,
    contact.location ? `Location: ${contact.location}` : null,
    contact.proximity_tier ? `Relationship: ${contact.proximity_tier} (score: ${contact.proximity_score})` : null,
    contact.capacity_tier ? `Capacity: ${contact.capacity_tier}` : null,
  ].filter(Boolean) as string[];

  if (contact.shared_employers.length > 0) {
    parts.push(`Shared employers: ${contact.shared_employers.join(', ')}`);
  }
  if (contact.shared_schools.length > 0) {
    parts.push(`Shared schools: ${contact.shared_schools.join(', ')}`);
  }
  if (contact.shared_boards.length > 0) {
    parts.push(`Shared boards: ${contact.shared_boards.join(', ')}`);
  }
  if (contact.topics.length > 0) {
    parts.push(`Topics of interest: ${contact.topics.join(', ')}`);
  }
  if (contact.primary_interests.length > 0) {
    parts.push(`Primary interests: ${contact.primary_interests.join(', ')}`);
  }
  if (contact.personalization_hooks.length > 0) {
    parts.push(`Personalization hooks: ${contact.personalization_hooks.join('; ')}`);
  }
  if (contact.suggested_opener) {
    parts.push(`Suggested opener: ${contact.suggested_opener}`);
  }
  if (contact.talking_points.length > 0) {
    parts.push(`Talking points: ${contact.talking_points.join('; ')}`);
  }
  if (contact.best_approach) {
    parts.push(`Best approach: ${contact.best_approach}`);
  }

  parts.push('');
  parts.push(`TONE: ${tone}`);
  parts.push(toneDesc);

  if (userContext) {
    parts.push('');
    parts.push(`ADDITIONAL CONTEXT FROM SENDER: ${userContext}`);
  }

  parts.push('');
  parts.push(
    'Write a personalized email with a compelling subject line and concise body. ' +
    'Output ONLY the email in this exact format:\n' +
    'Subject: [subject line]\n\n[email body]'
  );

  return parts.join('\n');
}

function parseEmailDraft(
  text: string
): { subject: string; body: string } {
  const subjectMatch = text.match(/^Subject:\s*(.+?)(?:\n\n|\r\n\r\n)/s);
  if (subjectMatch) {
    const subject = subjectMatch[1].trim();
    const body = text.slice(subjectMatch[0].length).trim();
    return { subject, body };
  }

  // Fallback: first line is subject, rest is body
  const lines = text.trim().split('\n');
  const firstLine = lines[0].replace(/^Subject:\s*/i, '').trim();
  const rest = lines.slice(1).join('\n').trim();
  return { subject: firstLine, body: rest || text };
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const {
      list_id,
      contact_ids,
      context: userContext,
      tone = 'warm_professional',
    } = body as {
      list_id?: string;
      contact_ids: number[];
      context?: string;
      tone?: string;
    };

    if (!contact_ids || !Array.isArray(contact_ids) || contact_ids.length === 0) {
      return NextResponse.json(
        { error: 'contact_ids is required and must be a non-empty array' },
        { status: 400 }
      );
    }

    const validTones = ['warm_professional', 'formal', 'casual', 'networking', 'fundraising'];
    if (!validTones.includes(tone)) {
      return NextResponse.json(
        { error: `Invalid tone. Must be one of: ${validTones.join(', ')}` },
        { status: 400 }
      );
    }

    const drafts: any[] = [];
    const errors: any[] = [];

    // Generate drafts one at a time for quality
    for (const contactId of contact_ids) {
      try {
        // Fetch contact context
        const contactCtx = await fetchContactContext(contactId);

        if (!contactCtx.email) {
          errors.push({
            contact_id: contactId,
            name: contactCtx.name,
            error: 'No email address on file',
          });
          continue;
        }

        // Generate draft via Claude
        const prompt = buildDraftPrompt(contactCtx, tone, userContext);

        const response = await anthropic.messages.create({
          model: 'claude-sonnet-4-6',
          max_tokens: 1024,
          temperature: 0.7,
          system: SYSTEM_PROMPT,
          messages: [{ role: 'user', content: prompt }],
        });

        const textBlock = response.content.find(
          (block): block is Anthropic.TextBlock => block.type === 'text'
        );

        if (!textBlock) {
          errors.push({
            contact_id: contactId,
            name: contactCtx.name,
            error: 'Failed to generate draft',
          });
          continue;
        }

        const { subject, body: emailBody } = parseEmailDraft(textBlock.text);

        // Save draft to database
        const { data: draft, error: insertError } = await supabase
          .from('outreach_drafts')
          .insert({
            list_id: list_id || null,
            contact_id: contactId,
            subject,
            body: emailBody,
            tone,
            status: 'draft',
          })
          .select()
          .single();

        if (insertError) {
          errors.push({
            contact_id: contactId,
            name: contactCtx.name,
            error: `Failed to save draft: ${insertError.message}`,
          });
          continue;
        }

        drafts.push({
          ...draft,
          contact_name: contactCtx.name,
          contact_email: contactCtx.email,
          contact_company: contactCtx.company,
        });
      } catch (err: any) {
        errors.push({
          contact_id: contactId,
          error: err.message || 'Unknown error',
        });
      }
    }

    return NextResponse.json({
      drafts,
      errors: errors.length > 0 ? errors : undefined,
      total_drafted: drafts.length,
      total_errors: errors.length,
    });
  } catch (error: any) {
    console.error('[Outreach Draft] Error:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to generate drafts' },
      { status: 500 }
    );
  }
}
