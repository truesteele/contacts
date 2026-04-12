import { supabase } from '@/lib/supabase';
import Anthropic from '@anthropic-ai/sdk';

export const runtime = 'nodejs';

const MODEL = 'claude-opus-4-6';

const AI_WRITING_RULES = `ANTI-AI WRITING RULES (non-negotiable):
- Zero em dashes in Justin's voice. Sally allows max 1 per email.
- No significance padding ("underscores the importance", "testament to", "pivotal moment", "broader landscape")
- No present-participle pileups ("fostering, enabling, enhancing")
- No vague authority ("experts say", "research shows", "many believe")
- Simple verbs (is/are/has, not "serves as" or "showcases" or "represents")
- Vary sentence length. Allow fragments. Use contractions.
- No "I hope this email finds you well" or similar cliches
- No stacked "not only X but also Y" constructions
- No "in conclusion", "all in all", "it should be noted that"
- No "transformative experience", "shines brightest", "comfortable hiking weather"
- No "without sacrificing", "one of the most underrated"
- No overly symmetric triads and listicles
- No generic "significance" padding
- No "journey" (use "trip", "season", "stretch" instead)
- No "passion" (use "obsession", "fixation" instead)
- No "community" as abstract noun (name the actual group)
- Prefer simple verbs: "is" not "serves as", "has" not "showcases", "does" not "represents"
- Leave 1-2 small imperfections for authenticity
- Don't over-smooth. Real emails have a rough edge or two.`;

const BANNED_PHRASES = [
  'underscores the importance', 'testament to', 'pivotal moment',
  'serves as', 'showcases', 'shines brightest', 'it should be noted',
  'in conclusion', 'all in all', 'I hope this email finds you well',
  'I hope this message finds you', 'transformative experience',
  'without sacrificing', 'one of the most underrated',
  'experts say', 'research shows', 'not only',
  'broader landscape', 'many believe', 'it is worth noting',
];

interface GenerateRequest {
  pitch_ids?: number[];
  podcast_id?: number;
  speaker_slug?: string;
  force?: boolean;
}

function buildSystemPrompt(speaker: {
  name: string;
  slug: string;
  bio: string;
  writing_samples?: any;
  past_appearances?: any;
}): string {
  const voiceGuide = speaker.slug === 'sally'
    ? `VOICE GUIDE (Sally Steele — comprehensive):

CORE VOICE: Direct, opinionated, specific, occasionally poetic. Willing to use fragments. Anchored in real scenes, names, numbers, and moral tension. Minister's cadence: story, reflection, invitation.

OPENINGS: Start with a specific scene, a short declaration, or a number. Never a thesis statement or topic overview.
Good: "A few weeks ago, we pulled into Morro Bay State Park around 10pm on a Friday night."
Good: "$11,300 at Disney. $100 at Humboldt Redwoods."
Bad: "Spring is one of the best seasons for camping in California."

CLOSINGS: Circle back to the opening scene or close with a reframe grounded in real experience. Never end on pure logistics.
Good: "We'll remember both trips. One for the magic money could buy. The other for the magic money couldn't touch."
Good: "This weekend, cancel something. Pack badly. Leave anyway."

NAMED PEOPLE RULE: Every story gets a real name. Unnamed people are abstractions. Named people are proof.
"Justin chased it into the woods, wrestled the container back."
"Eliza scrambled atop a driftwood castle others had built."
Even unnamed characters should be specific: "a park ranger leaned out his truck window," not "staff members were friendly."

CONTRAST SIGNATURE: Sally's most powerful move. Pair two opposites and let the reader draw the conclusion.
"At Disney, I knew exactly who could afford Lightning Passes. At Humboldt, nobody sorted us at all."
Don't explain the contrast. Show it. Trust the reader.

SENTENCE RHYTHM: Mix short fragments with longer sentences. The fragments carry the weight.
"Exhausted, we collapsed into our sleeping bags at midnight. Then at 1:30 AM, a tiny toddler voice: 'Daddy, I threw up.'"
"It was 75 degrees. Blue sky. Not a cloud in sight."

MANTRAS (use when earned by the story, one per email max):
- "Leave anyway" — Don't wait for the right moment
- "Camp as it comes" — Perfection isn't the goal; adaptation is
- "Take up space" — Belong fully, don't shrink yourself
- "Come alive" — What happens when you get outside with community

THROUGH-LINE WORD: "belonging" — this is her most-used word.

EM DASHES: Sally uses them naturally (max 1 per email). This is different from Justin who avoids them entirely.

VOCABULARY:
- "Sacred spaces" / "sacred pause" / "vessels for transformation"
- "Chosen family" / "tending" / "containers for belonging"
- "The wilderness doesn't check LinkedIn profiles. The river doesn't care about your ZIP code."
- "Families who arrived as strangers leave as chosen family"
- Replace "journey" with "trip/season/stretch"
- Replace "passion" with "obsession/fixation"
- Replace "community" with the actual group name

EMAIL PATTERNS:
- Greeting: "Hi [Name]," or "Hey [Name],"
- Sign-off: "Sally" or "With gratitude, Sally"
- Always "we" / "Justin and I" for OC
- Story first, then invitation. Never ask without earning it through narrative.
- One camper quote per fundraising email (her strongest tool)
- 150-200 words for outreach
- Invitation-centered asks: "Would love to have you be part of this."
- No hashtags in email (social-only pattern)

DESCRIBING OC:
- "Free camping trips for urban families"
- "Immersive multi-night experiences"
- "Shared meals, shared work, shared joy"
- "In a world where people feel increasingly disconnected, our trips offer the opposite"
- "Not everyone inherits camping knowledge"
- "400+ participants" / "100% recommendation rate"`
    : `VOICE GUIDE (Justin Steele — comprehensive):

CORE VOICE: Warm professional. Punchy 10-20 word sentences. Confident but not arrogant. Relational first, transactional second. Unpretentious despite impressive credentials. Builder identity. Sounds like someone who ran philanthropy at Google but would also grab a coffee with you.

SENTENCE STRUCTURE:
- Short paragraphs: rarely more than 3-4 sentences. Often single-sentence paragraphs for emphasis.
- Average sentence is 10-20 words. Not a run-on writer.
- Exclamation marks used authentically for genuine enthusiasm.
- Parenthetical asides are a voice marker: "(how did we both become entrepreneurs!?)"

GREETING: "Hi [Name]," or "Hey [Name]," — NEVER "Dear"
SIGN-OFF: Just "Justin" — NEVER "Best regards," "Sincerely," "Cheers,"

EM DASHES: ZERO. Never use em dashes in Justin's email voice. Use commas, periods, colons, or rephrase.

THE "WOULD LOVE" CONSTRUCTION (his signature ask):
- "Would love 20 minutes if you have it."
- "We'd really value your perspective on that."
- "I'd love to learn more about your work."

RELATIONSHIP FIRST:
- Names the connector and establishes chain of trust
- "Thanks for the introduction, [Name]! (moving you to bcc)"
- Leads with the human connection before getting to the ask
- "The overlap feels significant."
- "I always leave our conversations energized."

BUILDER IDENTITY:
- References being in "builder mode," "coding like crazy," "heads down"
- "The fact that I can prototype something like that in a single night tells you everything about where this technology is headed."

DESCRIBING OC (always "we" / "Sally and I"):
- "My wife Sally and I co-founded Outdoorithm Collective"
- "Brings diverse urban families together on public lands"
- "2-4 night camping trips" / "immersive multi-night experiences"
- "So that a tent is never a barrier to belonging"
- "Families who arrived as strangers leave as chosen family"
- "Through shared labor (setting up camp, cooking meals, watching each other's kids)"
- "400+ participants, 100% recommendation rate"
- "Sally is an REI Embark fellow and an experienced nonprofit exec who designs the experiences. I spent a decade leading Google.org's Americas philanthropy."

DESCRIBING HIMSELF:
- "Nearly a decade leading Google.org's Americas philanthropy"
- "I bring the technology and systems side"
- "Made the jump to build this"

NO-PRESSURE FRAMING:
- "We're not coming with an ask."
- "No pressure, just throwing it out there."
- "Cheering you on regardless."

FOLLOW-UP STYLE:
- "Circling back to see if [date] works."
- Short, non-pushy, always with forward momentum. Never guilt-trips.

VOCABULARY:
- "Excited to..." / "Would love to..." / "Let's build!"
- "Super fun." / "Really appreciate you..." / "Can't thank you enough."
- "Sound good?" / "Looking forward to it."
- Keep under 200 words for outreach. State facts plainly. "400+ participants" not "an incredible 400+ participants."
- Cross-pollinate naturally between ventures (OC, Kindora, consulting)
- Calendly link in follow-up, NOT in cold pitch`;

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

OUTREACH BEST PRACTICES:
- Reference a SPECIFIC recent episode by name. This is the #1 differentiator from generic pitches.
- 3 talking points framed as audience benefits, not speaker credentials.
- Soft CTA: "Would love to explore" / "Happy to chat" — not hard sell.
- Subject line under 50 chars, specific not clickbait.
- 150-200 words body. Tight. Every sentence does work.
- Sign off with name only.
- Suggest 2-3 concrete episode topic ideas.
- Sound like a real person, not a pitch template.

${AI_WRITING_RULES}

OUTPUT FORMAT:
Return a JSON object with exactly these fields:
{
  "subject_line": "Under 50 chars, specific, not clickbait",
  "subject_line_alt": "Alternative subject line, different angle",
  "pitch_body": "The email body. 150-200 words. In ${speaker.name}'s voice.",
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

  // Include podcast_profile data when available
  const profile = podcast.podcast_profile;
  if (profile && typeof profile === 'object') {
    if (profile.about) {
      const about = typeof profile.about === 'string' && profile.about.length > 600
        ? profile.about.slice(0, 600) + '...'
        : profile.about;
      parts.push(`\nABOUT THE PODCAST:\n${about}`);
    }
    if (profile.hosts && Array.isArray(profile.hosts)) {
      parts.push('\nHOST BIOS:');
      for (const host of profile.hosts) {
        if (typeof host === 'string') {
          parts.push(`- ${host}`);
        } else if (host.name) {
          parts.push(`- ${host.name}: ${host.bio || host.description || ''}`);
        }
      }
    }
    if (profile.audience) {
      parts.push(`\nTARGET AUDIENCE: ${typeof profile.audience === 'string' ? profile.audience : JSON.stringify(profile.audience)}`);
    }
    if (profile.format) {
      parts.push(`Format: ${profile.format}`);
    }
    if (profile.typical_episode_length) {
      parts.push(`Typical episode length: ${profile.typical_episode_length}`);
    }
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
  if (!Array.isArray(matching) && matching && typeof matching === 'object') {
    matching = Array.isArray(matching.matching_pillars) ? matching.matching_pillars : [];
  }
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
        parts.push(`- ${h.episode_title}: ${h.angle || h.hook || h.description || ''}`);
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
        // Auto-create a minimal pitch record
        const { data: newPitch, error: insertError } = await supabase
          .from('podcast_pitches')
          .insert({
            podcast_target_id: body.podcast_id,
            speaker_profile_id: speaker.id,
            is_bookmarked: false,
            user_notes: '',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          })
          .select('id')
          .single();

        if (insertError || !newPitch) {
          return Response.json(
            { error: `Failed to create pitch record: ${insertError?.message}` },
            { status: 500 }
          );
        }

        pitchIds = [newPitch.id];
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

    // Skip already-generated pitches (unless force flag is set)
    const toGenerate = body.force ? pitches : pitches.filter((p: any) => !p.pitch_body);
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

    // Fetch podcasts (including podcast_profile for richer context)
    const { data: podcasts } = await supabase
      .from('podcast_targets')
      .select('id, title, author, description, categories, host_name, website_url, podcast_profile')
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
