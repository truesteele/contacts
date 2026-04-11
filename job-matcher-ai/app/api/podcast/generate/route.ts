import { supabase } from '@/lib/supabase';
import Anthropic from '@anthropic-ai/sdk';

export const runtime = 'nodejs';

const MODEL = 'claude-sonnet-4-6';

const AI_WRITING_RULES = `RULES (non-negotiable):
- Zero em dashes in any outreach material. Use commas, periods, or colons instead.
- No significance padding ("underscores the importance", "testament to", "pivotal moment")
- No present-participle pileups ("fostering, enabling, enhancing")
- No vague authority ("experts say", "research shows")
- Simple verbs (is/are/has, not "serves as" or "showcases")
- Vary sentence length. Allow fragments. Use contractions.
- Reference a SPECIFIC recent episode by name
- Suggest 2-3 concrete episode topic ideas
- Keep the pitch body under 200 words
- Sound like a real person, not a pitch template
- No "I hope this email finds you well" or similar cliches
- Leave 1-2 small imperfections for authenticity
- No stacked "not only X but also Y" constructions
- No "in conclusion", "all in all", "it should be noted that"
- No "transformative experience", "shines brightest", "comfortable hiking weather"
- No "without sacrificing", "one of the most underrated"`;

const BANNED_PHRASES = [
  'underscores the importance', 'testament to', 'pivotal moment',
  'serves as', 'showcases', 'shines brightest', 'it should be noted',
  'in conclusion', 'all in all', 'I hope this email finds you well',
  'I hope this message finds you', 'transformative experience',
  'without sacrificing', 'one of the most underrated',
  'experts say', 'research shows', 'not only',
];

interface GenerateRequest {
  pitch_ids?: number[];
  podcast_id?: number;
  speaker_slug?: string;
}

function buildSystemPrompt(speaker: {
  name: string;
  slug: string;
  bio: string;
  writing_samples?: any;
  past_appearances?: any;
}): string {
  const voiceGuide = speaker.slug === 'sally'
    ? `VOICE GUIDE (Sally Steele):
- Direct, opinionated, specific, occasionally poetic
- Uses fragments for emphasis
- Names real people, places, numbers
- Uses contrast to reveal truth
- Anchored in real scenes and moral tension
- Mix short fragments with longer sentences. The fragments carry the weight.
- Opens with specifics, not overviews
- Closes by circling back or reframing`
    : `VOICE GUIDE (Justin Steele):
- Direct, punchy, uses sentence fragments for emphasis
- Casual and conversational, sounds like a text from a friend
- Names numbers, dates, specific experiences
- Uses contrast to reveal systemic truths
- Anchored in real experience, not abstract principles
- Varies sentence length. Short punches between longer observations.`;

  let samples = speaker.writing_samples || [];
  if (typeof samples === 'string') samples = JSON.parse(samples);
  let samplesText = '';
  for (const s of samples) {
    samplesText += `\n---\n${s.text}\n(Source: ${s.source})\n`;
  }

  let appearances = speaker.past_appearances || [];
  if (typeof appearances === 'string') appearances = JSON.parse(appearances);
  let appearancesText = '';
  if (appearances.length > 0) {
    appearancesText = '\n\nPAST PODCAST APPEARANCES (mention if relevant):';
    for (const a of appearances) {
      appearancesText += `\n- ${a.podcast_name}`;
      if (a.date) appearancesText += ` (${a.date})`;
    }
  }

  return `You are writing a podcast pitch email from ${speaker.name} to a podcast host.

${speaker.bio}

${voiceGuide}

WRITING SAMPLES (match this voice exactly):
${samplesText}
${appearancesText}

${AI_WRITING_RULES}

OUTPUT FORMAT:
Return a JSON object with exactly these fields:
{
  "subject_line": "Under 60 chars, specific, not clickbait",
  "subject_line_alt": "Alternative subject line, different angle",
  "pitch_body": "The email body. Under 200 words. In ${speaker.name}'s voice.",
  "episode_reference": "The specific episode you referenced and why",
  "suggested_topics": ["Topic idea 1", "Topic idea 2", "Topic idea 3"]
}

Return ONLY the JSON object, no markdown fencing, no explanation.`;
}

function buildUserPrompt(
  podcast: any,
  episodes: any[],
  fitData: { fit_tier?: string; fit_score?: number; fit_rationale?: string; topic_match?: any; episode_hooks?: any }
): string {
  const parts: string[] = [
    `PODCAST: ${podcast.title}`,
    `Host: ${podcast.host_name || podcast.author || 'Unknown'}`,
  ];

  if (podcast.description) {
    const desc = podcast.description.length > 500
      ? podcast.description.slice(0, 500) + '...'
      : podcast.description;
    parts.push(`Description: ${desc}`);
  }

  let categories = podcast.categories;
  if (typeof categories === 'string') categories = JSON.parse(categories);
  if (Array.isArray(categories) && categories.length > 0) {
    parts.push(`Categories: ${categories.join(', ')}`);
  }

  if (podcast.website_url) {
    parts.push(`Website: ${podcast.website_url}`);
  }

  if (episodes.length > 0) {
    parts.push(`\nRECENT EPISODES (${episodes.length}):`);
    for (const ep of episodes) {
      const title = ep.title || 'Untitled';
      let desc = ep.description || '';
      if (desc.length > 200) desc = desc.slice(0, 200) + '...';
      const date = ep.published_at ? ep.published_at.slice(0, 10) : '';
      const durStr = ep.duration_seconds ? ` (${Math.floor(ep.duration_seconds / 60)}min)` : '';
      parts.push(`- [${date}]${durStr} ${title}`);
      if (desc) parts.push(`  ${desc}`);
    }
  }

  parts.push('\nFIT ANALYSIS:');
  parts.push(`Fit tier: ${fitData.fit_tier || 'unknown'}`);
  parts.push(`Fit score: ${(fitData.fit_score ?? 0).toFixed(2)}`);
  parts.push(`Rationale: ${fitData.fit_rationale || ''}`);

  let matching = fitData.topic_match || [];
  if (typeof matching === 'string') matching = JSON.parse(matching);
  if (Array.isArray(matching) && matching.length > 0) {
    parts.push(`Matching pillars: ${matching.join(', ')}`);
  }

  let hooks = fitData.episode_hooks || [];
  if (typeof hooks === 'string') hooks = JSON.parse(hooks);
  if (Array.isArray(hooks) && hooks.length > 0) {
    parts.push('\nEPISODE HOOKS:');
    for (const h of hooks) {
      if (typeof h === 'string') {
        parts.push(`- ${h}`);
      } else if (h.episode_title) {
        parts.push(`- ${h.episode_title}: ${h.hook || ''}`);
      }
    }
  }

  parts.push('\nWrite the pitch email now.');
  return parts.join('\n');
}

function fixEmDashes(text: string): string {
  return text.replace(/\u2014/g, ',').replace(/\u2013/g, '-');
}

function auditPitch(pitch: { subject_line: string; pitch_body: string }): string[] {
  const issues: string[] = [];
  const body = pitch.pitch_body;

  if (body.includes('\u2014') || body.includes('\u2013')) {
    issues.push('Contains em/en dashes');
  }

  for (const phrase of BANNED_PHRASES) {
    if (body.toLowerCase().includes(phrase.toLowerCase())) {
      issues.push(`Banned phrase: "${phrase}"`);
    }
  }

  const wordCount = body.split(/\s+/).length;
  if (wordCount > 200) {
    issues.push(`Over 200 words (${wordCount})`);
  }

  if (pitch.subject_line.length > 60) {
    issues.push(`Subject line over 60 chars (${pitch.subject_line.length})`);
  }

  return issues;
}

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as GenerateRequest;
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      return Response.json({ error: 'ANTHROPIC_API_KEY not configured' }, { status: 500 });
    }

    const anthropic = new Anthropic({ apiKey });

    // Determine which pitches to generate
    let pitchIds: number[] = [];

    if (body.pitch_ids && body.pitch_ids.length > 0) {
      pitchIds = body.pitch_ids;
    } else if (body.podcast_id && body.speaker_slug) {
      // Find or create the pitch record for this podcast + speaker
      const { data: speaker } = await supabase
        .from('speaker_profiles')
        .select('id')
        .eq('slug', body.speaker_slug)
        .single();

      if (!speaker) {
        return Response.json({ error: `Speaker not found: ${body.speaker_slug}` }, { status: 404 });
      }

      const { data: existingPitch } = await supabase
        .from('podcast_pitches')
        .select('id')
        .eq('podcast_target_id', body.podcast_id)
        .eq('speaker_profile_id', speaker.id)
        .single();

      if (existingPitch) {
        pitchIds = [existingPitch.id];
      } else {
        return Response.json(
          { error: 'No pitch record found. Run scoring first or provide pitch_ids.' },
          { status: 400 }
        );
      }
    } else {
      return Response.json(
        { error: 'Provide pitch_ids or both podcast_id and speaker_slug' },
        { status: 400 }
      );
    }

    // Fetch pitch records with speaker and podcast data
    const { data: pitches, error: pitchError } = await supabase
      .from('podcast_pitches')
      .select('id, podcast_target_id, speaker_profile_id, fit_tier, fit_score, fit_rationale, topic_match, episode_hooks, pitch_body')
      .in('id', pitchIds);

    if (pitchError || !pitches || pitches.length === 0) {
      return Response.json({ error: 'No pitches found for the given IDs' }, { status: 404 });
    }

    // Skip already-generated pitches
    const toGenerate = pitches.filter((p: any) => !p.pitch_body);
    if (toGenerate.length === 0) {
      return Response.json({
        status: 'complete',
        message: 'All pitches already have generated content',
        skipped: pitches.length,
        generated: 0,
      });
    }

    // Gather all unique speaker and podcast IDs
    const speakerIds = [...new Set(toGenerate.map((p: any) => p.speaker_profile_id))];
    const podcastIds = [...new Set(toGenerate.map((p: any) => p.podcast_target_id))];

    // Fetch speakers
    const { data: speakers } = await supabase
      .from('speaker_profiles')
      .select('id, name, slug, bio, writing_samples, past_appearances')
      .in('id', speakerIds);

    const speakerMap = new Map<number, any>();
    if (speakers) {
      for (const s of speakers) speakerMap.set(s.id, s);
    }

    // Fetch podcasts
    const { data: podcasts } = await supabase
      .from('podcast_targets')
      .select('id, title, author, description, categories, host_name, website_url')
      .in('id', podcastIds);

    const podcastMap = new Map<number, any>();
    if (podcasts) {
      for (const p of podcasts) podcastMap.set(p.id, p);
    }

    // Fetch episodes for all podcasts
    const { data: allEpisodes } = await supabase
      .from('podcast_episodes')
      .select('podcast_target_id, title, description, published_at, duration_seconds')
      .in('podcast_target_id', podcastIds)
      .order('published_at', { ascending: false });

    const episodeMap = new Map<number, any[]>();
    if (allEpisodes) {
      for (const ep of allEpisodes) {
        const list = episodeMap.get(ep.podcast_target_id) || [];
        if (list.length < 5) list.push(ep);
        episodeMap.set(ep.podcast_target_id, list);
      }
    }

    // Generate pitches sequentially (Claude rate limits are tighter)
    const results: Array<{
      pitch_id: number;
      status: 'generated' | 'failed';
      subject_line?: string;
      audit_issues?: string[];
      error?: string;
    }> = [];

    for (const pitch of toGenerate) {
      const p = pitch as any;
      const speaker = speakerMap.get(p.speaker_profile_id);
      const podcast = podcastMap.get(p.podcast_target_id);

      if (!speaker || !podcast) {
        results.push({ pitch_id: p.id, status: 'failed', error: 'Missing speaker or podcast data' });
        continue;
      }

      const episodes = episodeMap.get(p.podcast_target_id) || [];

      try {
        const systemPrompt = buildSystemPrompt(speaker);
        const userPrompt = buildUserPrompt(podcast, episodes, {
          fit_tier: p.fit_tier,
          fit_score: p.fit_score,
          fit_rationale: p.fit_rationale,
          topic_match: p.topic_match,
          episode_hooks: p.episode_hooks,
        });

        const response = await anthropic.messages.create({
          model: MODEL,
          max_tokens: 1024,
          messages: [{ role: 'user', content: userPrompt }],
          system: systemPrompt,
        });

        // Extract text from response
        let rawText = '';
        for (const block of response.content) {
          if (block.type === 'text') rawText += block.text;
        }

        // Strip markdown fencing if present
        rawText = rawText.replace(/^```json\s*/i, '').replace(/```\s*$/, '').trim();

        const generated = JSON.parse(rawText) as {
          subject_line: string;
          subject_line_alt: string;
          pitch_body: string;
          episode_reference: string;
          suggested_topics: string[];
        };

        // Validate required fields
        if (!generated.subject_line || !generated.pitch_body) {
          results.push({ pitch_id: p.id, status: 'failed', error: 'Missing subject_line or pitch_body in generated output' });
          continue;
        }

        // Fix em dashes
        generated.pitch_body = fixEmDashes(generated.pitch_body);
        generated.subject_line = fixEmDashes(generated.subject_line);
        generated.subject_line_alt = fixEmDashes(generated.subject_line_alt);

        // Audit
        const auditIssues = auditPitch(generated);

        // Normalize suggested_topics to string array
        const topics = (generated.suggested_topics || []).map((t: any) =>
          typeof t === 'string' ? t : t.title || t.topic || String(t)
        );

        // Save to database
        const { error: updateError } = await supabase
          .from('podcast_pitches')
          .update({
            subject_line: generated.subject_line,
            subject_line_alt: generated.subject_line_alt,
            pitch_body: generated.pitch_body,
            episode_reference: generated.episode_reference,
            suggested_topics: topics,
            pitch_status: 'draft',
            model_used: MODEL,
            generated_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          })
          .eq('id', p.id);

        if (updateError) {
          results.push({ pitch_id: p.id, status: 'failed', error: updateError.message });
        } else {
          results.push({
            pitch_id: p.id,
            status: 'generated',
            subject_line: generated.subject_line,
            audit_issues: auditIssues.length > 0 ? auditIssues : undefined,
          });
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Generation failed';
        results.push({ pitch_id: p.id, status: 'failed', error: message });
      }
    }

    const generated = results.filter(r => r.status === 'generated').length;
    const failed = results.filter(r => r.status === 'failed').length;

    return Response.json({
      results,
      generated,
      failed,
      skipped: pitches.length - toGenerate.length,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to generate pitches';
    console.error('[Podcast Generate] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
