import { NextRequest } from 'next/server';
import { supabase } from '@/lib/supabase';
import OpenAI from 'openai';

const PERPLEXITY_MODEL = 'sonar-pro';

const PODCAST_PROFILE_SCHEMA = {
  type: 'json_schema' as const,
  json_schema: {
    name: 'podcast_profile',
    strict: true,
    schema: {
      type: 'object',
      properties: {
        about: { type: 'string' },
        hosts: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              bio: { type: 'string' },
              social_links: {
                type: 'object',
                properties: {
                  twitter: { type: 'string' },
                  linkedin: { type: 'string' },
                  instagram: { type: 'string' },
                  website: { type: 'string' },
                },
                required: ['twitter', 'linkedin', 'instagram', 'website'],
                additionalProperties: false,
              },
            },
            required: ['name', 'bio', 'social_links'],
            additionalProperties: false,
          },
        },
        audience: {
          type: 'object',
          properties: {
            size_estimate: { type: 'string' },
            demographic: { type: 'string' },
          },
          required: ['size_estimate', 'demographic'],
          additionalProperties: false,
        },
        platforms: {
          type: 'object',
          properties: {
            apple_url: { type: 'string' },
            spotify_url: { type: 'string' },
            youtube_url: { type: 'string' },
            website_url: { type: 'string' },
          },
          required: ['apple_url', 'spotify_url', 'youtube_url', 'website_url'],
          additionalProperties: false,
        },
        notable_guests: { type: 'array', items: { type: 'string' } },
        format: {
          type: 'object',
          properties: {
            style: { type: 'string' },
            length_minutes: { type: 'integer' },
            frequency: { type: 'string' },
          },
          required: ['style', 'length_minutes', 'frequency'],
          additionalProperties: false,
        },
        social_media: {
          type: 'object',
          properties: {
            twitter: { type: 'string' },
            instagram: { type: 'string' },
            facebook: { type: 'string' },
            tiktok: { type: 'string' },
          },
          required: ['twitter', 'instagram', 'facebook', 'tiktok'],
          additionalProperties: false,
        },
        awards_recognition: { type: 'array', items: { type: 'string' } },
      },
      required: [
        'about', 'hosts', 'audience', 'platforms',
        'notable_guests', 'format', 'social_media', 'awards_recognition',
      ],
      additionalProperties: false,
    },
  },
};

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const podcastId = body.podcast_id;

    if (!podcastId) {
      return Response.json({ error: 'Missing podcast_id' }, { status: 400 });
    }

    // Load the podcast
    const { data: podcast, error: podcastError } = await supabase
      .from('podcast_targets')
      .select('*')
      .eq('id', podcastId)
      .single();

    if (podcastError || !podcast) {
      return Response.json({ error: 'Podcast not found' }, { status: 404 });
    }

    // Step 1: Perplexity research
    const perplexityKey = process.env.PERPLEXITY_APIKEY;
    if (!perplexityKey) {
      return Response.json({ error: 'PERPLEXITY_APIKEY not configured' }, { status: 500 });
    }

    const host = podcast.host_name || podcast.author || '';
    const website = podcast.website_url || '';
    let query = `Research the podcast "${podcast.title}"`;
    if (host) query += ` hosted by ${host}`;
    if (website) query += `. Website: ${website}`;
    query += `\n\nProvide:\n1. What the podcast is about (mission, focus areas, typical topics)\n2. Host bio(s) — background, credentials, other work\n3. Audience size estimate and demographic\n4. Where to listen — Apple Podcasts URL, Spotify URL, YouTube URL\n5. Notable past guests\n6. Format: interview vs solo vs panel, typical episode length, release frequency\n7. Social media accounts\n8. Any awards, recognition, or press coverage`;

    const perplexityResp = await fetch('https://api.perplexity.ai/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${perplexityKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: PERPLEXITY_MODEL,
        messages: [
          {
            role: 'system',
            content: 'You are an expert podcast industry researcher. Provide detailed, factual information about podcasts including host backgrounds, audience metrics, distribution platforms, and notable guests. Be specific with URLs and numbers when available.',
          },
          { role: 'user', content: query },
        ],
        return_citations: true,
        return_related_questions: false,
      }),
    });

    if (!perplexityResp.ok) {
      const errText = await perplexityResp.text();
      return Response.json(
        { error: `Perplexity API error: ${perplexityResp.status} ${errText}` },
        { status: 502 }
      );
    }

    const perplexityData = await perplexityResp.json();
    const rawResearch = perplexityData.choices?.[0]?.message?.content || '';

    if (!rawResearch) {
      return Response.json({ error: 'Perplexity returned empty research' }, { status: 502 });
    }

    // Step 2: GPT-5.4 mini structuring
    const openaiKey = process.env.OPENAI_APIKEY;
    if (!openaiKey) {
      return Response.json({ error: 'OPENAI_APIKEY not configured' }, { status: 500 });
    }

    const openai = new OpenAI({ apiKey: openaiKey });

    const categories = Array.isArray(podcast.categories)
      ? podcast.categories.join(', ')
      : '';

    const knownContext = [
      `Podcast title: ${podcast.title}`,
      `Author: ${podcast.author || ''}`,
      `Host name (from RSS): ${podcast.host_name || ''}`,
      `Website: ${podcast.website_url || ''}`,
      `Episode count: ${podcast.episode_count || ''}`,
      `Activity status: ${podcast.activity_status || ''}`,
      categories ? `Categories: ${categories}` : '',
    ].filter(Boolean).join('\n');

    const gptResp = await openai.chat.completions.create({
      model: 'gpt-5.4-mini',
      messages: [
        {
          role: 'system',
          content: 'You extract structured podcast profile data from raw web research. Be precise — only include information explicitly stated in the research. For missing data, use empty strings or empty arrays. Never fabricate URLs.',
        },
        {
          role: 'user',
          content: `${knownContext}\n\n--- RAW WEB RESEARCH ---\n${rawResearch}\n--- END RESEARCH ---\n\nExtract a structured podcast profile from the research above. For any fields where information is not available, use empty strings or empty arrays. Provide URLs only if they appear in the research.`,
        },
      ],
      response_format: PODCAST_PROFILE_SCHEMA,
    });

    const profileJson = gptResp.choices[0].message.content;
    if (!profileJson) {
      return Response.json({ error: 'GPT returned empty response' }, { status: 502 });
    }

    const profile = JSON.parse(profileJson);

    // Step 3: Save to database
    const { error: updateError } = await supabase
      .from('podcast_targets')
      .update({
        podcast_profile: profile,
        researched_at: new Date().toISOString(),
      })
      .eq('id', podcastId);

    if (updateError) {
      return Response.json(
        { error: `Failed to save profile: ${updateError.message}` },
        { status: 500 }
      );
    }

    // Bonus: fill empty description from research
    if (!podcast.description && profile.about) {
      await supabase
        .from('podcast_targets')
        .update({ description: profile.about })
        .eq('id', podcastId);
    }

    return Response.json({
      success: true,
      podcast_id: podcastId,
      profile,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to research podcast';
    console.error('[Podcast Research] Error:', message);
    return Response.json({ error: message }, { status: 500 });
  }
}
