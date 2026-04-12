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
- No "I hope this email finds you well" or similar greeting cliches
- No "I am writing to..." or "I wanted to reach out..." openers
- No "I am excited to share" or "I am confident that" constructions
- No "I believe that" — just state the thing
- No stacked "not only X but also Y" constructions
- No "in conclusion", "all in all", "it should be noted that"
- No "transformative experience", "shines brightest", "comfortable hiking weather"
- No "without sacrificing", "one of the most underrated"
- No overly symmetric triads and listicles — do NOT use 3 bullet points or 3 parallel items
- No generic "significance" padding
- No "journey" (use "trip", "season", "stretch" instead)
- No "passion" (use "obsession", "fixation" instead)
- No "community" as abstract noun (name the actual group)
- No "Dear" greeting — always "Hi [Name]," or "Hey [Name],"
- No formal sign-offs — never "Best regards", "Sincerely", "Warm regards", "Cheers", "Kind regards"
- Prefer simple verbs: "is" not "serves as", "has" not "showcases", "does" not "represents"
- Leave 1-2 small imperfections for authenticity. A slightly rough edge makes it real.
- Don't over-smooth. Real emails have asymmetry, asides, and the occasional incomplete thought.`;

const BANNED_PHRASES = [
  'underscores the importance', 'testament to', 'pivotal moment',
  'serves as', 'showcases', 'shines brightest', 'it should be noted',
  'in conclusion', 'all in all', 'I hope this email finds you well',
  'I hope this message finds you', 'transformative experience',
  'without sacrificing', 'one of the most underrated',
  'experts say', 'research shows', 'not only',
  'broader landscape', 'many believe', 'it is worth noting',
  'I am writing to', 'I wanted to reach out', 'I am excited to share',
  'I am confident that', 'I believe that',
  'Best regards', 'Sincerely', 'Warm regards', 'Kind regards',
  'Dear ',
  'deeply resonated', 'truly inspiring', 'incredibly important',
  'I would be honored', 'unique perspective',
  'stayed with me', 'found myself nodding', 'really resonated',
];

interface GenerateRequest {
  pitch_ids?: number[];
  podcast_id?: number;
  speaker_slug?: string;
  force?: boolean;
}

function describeAudience(audience: unknown): string | null {
  if (!audience) return null;
  if (typeof audience === 'string') {
    return audience.trim() || null;
  }
  if (typeof audience === 'object') {
    const data = audience as Record<string, unknown>;
    const parts = [data.size_estimate, data.demographic]
      .map((value) => (typeof value === 'string' ? value.trim() : ''))
      .filter(Boolean);
    return parts.length > 0 ? parts.join(' | ') : null;
  }
  return null;
}

function describeFormat(format: unknown): string | null {
  if (!format) return null;
  if (typeof format === 'string') {
    return format.trim() || null;
  }
  if (typeof format === 'object') {
    const data = format as Record<string, unknown>;
    const parts = [
      typeof data.style === 'string' ? data.style.trim() : '',
      typeof data.frequency === 'string' ? data.frequency.trim() : '',
      typeof data.length_minutes === 'number' ? `~${data.length_minutes} min` : '',
    ].filter(Boolean);
    return parts.length > 0 ? parts.join(' | ') : null;
  }
  return null;
}

function buildSystemPrompt(speaker: {
  name: string;
  slug: string;
  bio: string;
  writing_samples?: any;
  past_appearances?: any;
}): string {
  const voiceGuide = speaker.slug === 'sally'
    ? `VOICE GUIDE (Sally Steele — podcast outreach):

CORE VOICE: Direct, opinionated, specific, occasionally poetic. Minister's cadence: genuine curiosity, brief story, warm invitation. She sounds like someone who would sit with you after the interview and keep talking because the conversation was real.

THIS IS AN INVITATION, NOT A PITCH:
Sally doesn't sell herself or pitch hard. She's excited to find people who care about the same things. Think: "I found your show and it hit close to home" not "I'd be a great guest because..." The fundraising principles apply here too: we invite people on a journey. We don't ask them to help. We present an opportunity to explore something together.

OPENING (for outreach email — NOT a blog post):
Open with genuine, specific curiosity about the HOST and their work. Reference a real episode by name in the first 1-2 sentences. This proves you listened. Then bridge to why it resonated personally.
Good: "Hi [Name], your conversation with [Guest] on [Episode] hit something I've been thinking about a lot."
Good: "Hi [Name], I caught your episode on [Topic] and found myself nodding through the whole thing."
Bad: "I'm a big fan of your podcast." (generic, proves nothing)
Bad: "A few weeks ago, we pulled into Morro Bay State Park..." (that's a blog opening, not an outreach email)

BRIDGE (the natural connection):
After the episode reference, ONE sentence connecting their world to yours. Not a credential dump. A genuine overlap.
Good: "We're doing something similar with families in the outdoors, and the questions you're asking are the ones we wrestle with every trip."
Bad: "As CEO of Outdoorithm and Co-Founder of Outdoorithm Collective, I have extensive experience in..."

THE INVITATION (not the ask):
Frame the conversation as something that would be genuinely interesting for both sides. Not "I'd love to be a guest" but "I think there's a conversation here that your listeners would find interesting."
Good: "I'd love to explore what that looks like on your show."
Good: "If you're open to it, I think there's a conversation here worth having."
Bad: "I would be honored to appear on your podcast."
Bad: "Please consider me as a guest."

CLOSING:
Short. Warm. Low pressure. Sign off with just "Sally" or "With gratitude, Sally". No Calendly links in cold outreach.

SENTENCE RHYTHM: Mix short fragments with longer sentences. Fragments carry weight.
"400 families. Zero turned away. That's the model."
"It was 75 degrees. Blue sky. Not a cloud."

EM DASHES: Max 1 per email. Prefer periods and commas.

THROUGH-LINE WORD: "belonging" — her most-used word.

VOCABULARY:
- "Chosen family" / "tending"
- "The wilderness doesn't check LinkedIn profiles"
- "Families who arrived as strangers leave as chosen family"
- Replace "journey" with "trip/season/stretch"
- Replace "passion" with "obsession/fixation"
- Replace "community" with the actual group name
- "we" / "Justin and I" for OC, never "I" alone

DESCRIBING OC (keep brief — 1-2 sentences max, not a paragraph):
- "Free camping trips for urban families"
- "400+ participants, 100% recommendation rate"
- "Not everyone inherits camping knowledge. We're changing that."

TONE TEST: Before accepting the output, ask: does this sound like a personal email from a real person, or does it sound like a pitch template? If template, rewrite.`
    : `VOICE GUIDE (Justin Steele — podcast outreach):

CORE VOICE: Warm professional. Punchy 10-20 word sentences. Confident but not arrogant. Relational first, transactional second. Unpretentious despite impressive credentials. Builder identity. Sounds like someone who ran philanthropy at Google but would also grab a coffee with you.

THIS IS AN INVITATION, NOT A PITCH:
Justin doesn't pitch himself. He finds overlap, gets genuinely excited about it, and invites the host to explore a conversation. Think fundraising principles: "There's a difference between 'Would you help us?' and 'Would you want to be part of this?'" He presents opportunities. He doesn't beg or sell.

OPENING (for outreach email):
Open with a specific episode reference that shows real listening. First 1-2 sentences. This is the #1 differentiator from generic pitches — 83% of hosts reject pitches that don't demonstrate familiarity.
Good: "Hi [Name], caught your episode with [Guest] on [Topic]. The part about [specific detail] stuck with me."
Good: "Hey [Name], your conversation with [Guest] reminded me of something we ran into building Outdoorithm."
Bad: "I love your podcast!" (generic, proves nothing)
Bad: "I am writing to introduce myself as a potential guest." (AI pitch template)

BRIDGE (natural connection, not credential dump):
One sentence connecting their show to your world. Lead with the overlap, not the resume.
Good: "Sally and I are building something in that exact space."
Good: "The overlap with what we see on our camping trips is striking."
Bad: "With nearly a decade leading Google.org's Americas philanthropy, I bring a unique perspective..."

THE INVITATION:
Frame as mutually interesting, not self-promotional.
Good: "Would love to explore this on your show if you're open to it."
Good: "I think there's a conversation here your listeners would dig."
Bad: "I would be a great guest because..."
Bad: "Please consider me for an upcoming episode."

SENTENCE STRUCTURE:
- Short paragraphs: 1-3 sentences. Single-sentence paragraphs for emphasis.
- 10-20 words average. Not a run-on writer.
- Exclamation marks used authentically: "(how did we both become entrepreneurs!?)"
- Parenthetical asides are a voice marker.

GREETING: "Hi [Name]," or "Hey [Name]," — NEVER "Dear"
SIGN-OFF: Just "Justin" — NEVER "Best regards," "Sincerely," "Cheers,"

EM DASHES: ZERO. Never use em dashes in Justin's email voice. Use commas, periods, colons, or rephrase.

NO-PRESSURE FRAMING:
- "No pressure, just throwing it out there."
- "Either way, love what you're building."

VOCABULARY:
- "Would love to..." / "Excited to..."
- "Super fun." / "Really appreciate you..."
- "Sound good?" / "Looking forward to it."
- State facts plainly. "400+ participants" not "an incredible 400+ participants."
- Cross-pollinate naturally between ventures (OC, Kindora, consulting)
- Calendly link in follow-up, NOT in cold outreach

DESCRIBING OC (brief — 1-2 sentences, not a paragraph):
- "My wife Sally and I co-founded Outdoorithm Collective"
- "Free camping trips for diverse urban families on public lands"
- "400+ participants, 100% recommendation rate"

TONE TEST: Does this read like a real email from a real person? Or does it read like a pitch template? If template, rewrite.`;

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

  return `You are writing a personal outreach email from ${speaker.name} to a podcast host, inviting them to explore a conversation. This is NOT a pitch template. It's a genuine, human email that happens to suggest being a guest. Write it like ${speaker.name} would actually write it — warm, specific, slightly imperfect.

${speaker.bio}

${voiceGuide}

WRITING SAMPLES (match this voice exactly):
${samplesText}
${appearancesText}

OUTREACH PHILOSOPHY (from our fundraising principles — apply to podcast outreach):
- Impact drives interest. When people understand what we're building and why it matters, they want to be part of the conversation. Our job isn't to convince anyone. It's to invite the right people into something real.
- Personal emails, not marketing pitches. This should sound like what it is: a personal note from one person to another. No nonprofit jargon. No "propelling our mission forward." Just human beings talking about something that matters.
- The moment an email starts to feel "crafted," it stops feeling human. We'd rather be warm and slightly imperfect than polished and hollow.
- We don't over-optimize. No strategic quote placement, no hero framing, no pronoun ratios.
- Before sending, ask: does this sound like me talking to a friend? Would I be comfortable if this person showed it to someone else?

HONESTY ABOUT EPISODES (critical):
We have NOT listened to most of these podcasts. We know episode titles, descriptions, and guest names from our research database. Be HONEST about this:
- DO reference a specific episode by title. This shows real research.
- DO NOT claim it "stayed with me" or "resonated deeply" or "I found myself nodding" — that implies you listened.
- DO use honest framing: "I noticed your episode on...", "Your conversation with [Guest] about [Topic] caught my eye", "I came across your episode on..."
- IF the USER NOTES say they listened to a specific episode, THEN you can use stronger language like "stuck with me" or "got me thinking."
- The goal: demonstrate genuine research without faking a personal listening experience.

OUTREACH STRUCTURE:
1. OPEN with a specific episode reference (title, guest name). Honest framing — "noticed" or "came across", not "stayed with me." First 1-2 sentences.
2. BRIDGE naturally to why the topic connects to your work. One sentence. Not a bio dump.
3. BRIEF context on who you are — 1-2 sentences about OC. Not a paragraph. Not a credential list.
4. INVITE a conversation — one natural sentence about what you'd explore together. Do NOT list 3-4 parallel topic fragments. Just say what the conversation would be about in plain prose.
5. CLOSE warm and low-pressure. Name only as sign-off.
- If a host LinkedIn profile is provided, weave their background into why the conversation would be compelling. Don't just mention LinkedIn. Use what you know about them.
- Subject line under 50 chars, specific not clickbait. Reference the podcast name or a topic, not generic "guest inquiry."
- 150-200 words body. Tight. Every sentence does work.
- Do NOT format topics as a bulleted list in the email body. Do NOT use parallel fragment structures like "What X looks like. How Y works. Why Z matters." That's a listicle in disguise. Just write naturally.

${AI_WRITING_RULES}

OUTPUT FORMAT:
Return a JSON object with exactly these fields:
{
  "subject_line": "Under 50 chars, references podcast or topic",
  "subject_line_alt": "Alternative angle, also under 50 chars",
  "pitch_body": "The full email body. 150-200 words. In ${speaker.name}'s voice. No bullet points in the email body.",
  "episode_reference": "Which episode you referenced and the specific detail you pulled from it",
  "suggested_topics": ["Conversation thread 1", "Conversation thread 2"]
}

CRITICAL: The pitch_body must read like a real email, not a pitch template. No bullet points. No numbered lists. No "Here are three topics I could discuss." Just flowing prose that happens to suggest what you'd talk about.

Return ONLY the JSON object, no markdown fencing, no explanation.`;
}

function buildUserPrompt(
  podcast: any,
  episodes: any[],
  fitData: { fit_tier?: string; fit_score?: number; fit_rationale?: string; topic_match?: any; episode_hooks?: any },
  userNotes?: string | null
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

  if (podcast.host_linkedin) {
    parts.push(`Host LinkedIn: ${podcast.host_linkedin}`);
  }

  if (podcast.host_instagram) {
    parts.push(`Host Instagram: ${podcast.host_instagram}`);
  }

  if (podcast.host_email) {
    parts.push(`Host Email: ${podcast.host_email}`);
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
    const audienceSummary = describeAudience(profile.audience);
    if (audienceSummary) parts.push(`\nTARGET AUDIENCE: ${audienceSummary}`);

    const formatSummary = describeFormat(profile.format);
    if (formatSummary) parts.push(`Format: ${formatSummary}`);
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

  if (userNotes && userNotes.trim()) {
    parts.push(`\nUSER NOTES (from the person managing outreach — use these to personalize):\n${userNotes.trim()}`);
  }

  parts.push('\nWrite the outreach email now. Remember: invitation, not pitch. Open with a specific episode reference. Keep it human.');
  return parts.join('\n');
}

function fixEmDashes(text: string, allowOne = false): string {
  let result = text.replace(/\u2013/g, '-');
  if (allowOne) {
    // Sally: keep the first em dash, replace the rest
    let found = false;
    result = result.replace(/\u2014/g, () => {
      if (!found) { found = true; return '\u2014'; }
      return ',';
    });
  } else {
    result = result.replace(/\u2014/g, ',');
  }
  return result;
}

function auditPitch(pitch: { subject_line: string; pitch_body: string }, isSally = false): string[] {
  const issues: string[] = [];
  const body = pitch.pitch_body;
  const bodyLower = body.toLowerCase();

  const emDashCount = (body.match(/\u2014/g) || []).length;
  if (body.includes('\u2013')) {
    issues.push('Contains en dashes');
  }
  if (isSally && emDashCount > 1) {
    issues.push(`Too many em dashes for Sally (${emDashCount}, max 1)`);
  } else if (!isSally && emDashCount > 0) {
    issues.push('Contains em dashes (not allowed for Justin)');
  }

  for (const phrase of BANNED_PHRASES) {
    if (bodyLower.includes(phrase.toLowerCase()) || pitch.subject_line.toLowerCase().includes(phrase.toLowerCase())) {
      issues.push(`Banned phrase: "${phrase}"`);
    }
  }

  const wordCount = body.split(/\s+/).length;
  if (wordCount > 200) {
    issues.push(`Over 200 words (${wordCount})`);
  }

  if (pitch.subject_line.length > 50) {
    issues.push(`Subject line over 50 chars (${pitch.subject_line.length})`);
  }

  // Check for bullet points or numbered lists in body (sign of template pitch)
  if (/^[\s]*[-•*]\s/m.test(body) || /^[\s]*\d+[.)]\s/m.test(body)) {
    issues.push('Contains bullet points or numbered list (should be flowing prose)');
  }

  // Check for present-participle pileups (3+ gerunds separated by commas)
  if (/\b\w+ing,\s*\w+ing,\s*\w+ing\b/.test(body)) {
    issues.push('Present-participle pileup detected');
  }

  // Check for greeting/sign-off violations
  if (body.startsWith('Dear ')) {
    issues.push('Uses "Dear" greeting');
  }

  // Check for disguised listicles: 3+ sentences starting with What/How/Why/When in sequence
  const sentences = body.split(/[.!?]\s+/);
  let questionWordStreak = 0;
  for (const s of sentences) {
    if (/^(What|How|Why|When|Where)\s/.test(s.trim())) {
      questionWordStreak++;
      if (questionWordStreak >= 3) {
        issues.push('Disguised listicle: 3+ parallel What/How/Why fragments');
        break;
      }
    } else {
      questionWordStreak = 0;
    }
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

      const { data: existingPitch, error: existingPitchError } = await supabase
        .from('podcast_pitches')
        .select('id')
        .eq('podcast_target_id', body.podcast_id)
        .eq('speaker_profile_id', speaker.id)
        .maybeSingle();

      if (existingPitchError) {
        return Response.json(
          { error: `Failed to check existing pitch: ${existingPitchError.message}` },
          { status: 500 }
        );
      }

      if (existingPitch) {
        pitchIds = [existingPitch.id];
      } else {
        // Auto-create a minimal pitch record
        const { data: newPitch, error: insertError } = await supabase
          .from('podcast_pitches')
          .insert({
            podcast_target_id: body.podcast_id,
            speaker_profile_id: speaker.id,
            pitch_status: 'unscored',
            is_bookmarked: false,
            user_notes: '',
            updated_at: new Date().toISOString(),
          })
          .select('id')
          .single();

        if (insertError?.code === '23505') {
          const { data: concurrentPitch, error: concurrentError } = await supabase
            .from('podcast_pitches')
            .select('id')
            .eq('podcast_target_id', body.podcast_id)
            .eq('speaker_profile_id', speaker.id)
            .maybeSingle();

          if (concurrentError || !concurrentPitch) {
            return Response.json(
              { error: `Failed to resolve concurrent pitch creation: ${concurrentError?.message || insertError.message}` },
              { status: 500 }
            );
          }

          pitchIds = [concurrentPitch.id];
        } else if (insertError || !newPitch) {
          return Response.json(
            { error: `Failed to create pitch record: ${insertError?.message}` },
            { status: 500 }
          );
        } else {
          pitchIds = [newPitch.id];
        }
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
      .select('id, podcast_target_id, speaker_profile_id, fit_tier, fit_score, fit_rationale, topic_match, episode_hooks, pitch_body, user_notes')
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
      .select('id, title, author, description, categories, host_name, website_url, podcast_profile, host_linkedin, host_instagram, host_email')
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
        }, p.user_notes);

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

        // Fix em dashes (Sally allows max 1, Justin allows none)
        const isSally = speaker.slug === 'sally';
        generated.pitch_body = fixEmDashes(generated.pitch_body, isSally);
        generated.subject_line = fixEmDashes(generated.subject_line);
        generated.subject_line_alt = fixEmDashes(generated.subject_line_alt);

        // Audit
        const auditIssues = auditPitch(generated, isSally);

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
