// TED 2026 — Real-time LinkedIn Enrichment + Outdoorithm Scoring
//
// Takes a LinkedIn URL, scrapes the profile via Apify, scores with GPT-5 mini,
// and returns the structured result for Sally's real-time conference networking.
//
// Deploy: SUPABASE_ACCESS_TOKEN=$SB_PAT supabase functions deploy ted-enrich-contact \
//   --project-ref ypqsrejrsocebnldicke --no-verify-jwt --use-api
// Secrets: supabase secrets set APIFY_API_KEY=... OPENAI_APIKEY=...

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// ── Outdoorithm Triage System Prompt ──────────────────────────────────

const SYSTEM_PROMPT = `You are scoring a person for their potential partnership value with Outdoorithm Collective, a nonprofit that transforms access to public lands by creating community-driven camping experiences for diverse urban families.

ABOUT OUTDOORITHM COLLECTIVE:
- Mission: Transform public lands into spaces of belonging for historically excluded communities
- Model: 48-hour guided group camping trips where families across class/race lines build authentic connections
- Theory of change: Cross-class friendships formed in nature are the #1 predictor of economic mobility
- Based in Oakland, CA; serves families throughout California; plans national expansion
- Co-founded by Sally Steele (CEO, nonprofit executive, ordained faith leader, City Hope SF) and Justin Steele (former Google.org Director, HBS/HKS)
- Current: Running "Come Alive 2026" fundraising campaign ($120K goal)
- 94% BIPOC participants; ~100 families served; 107 camping trips as a family

ABOUT SALLY STEELE (who will be networking):
- Co-Founder & CEO of Outdoorithm Collective
- Former Co-Executive Director of City Hope San Francisco ($1.9M budget)
- Ordained minister, Black woman, mother of four, Oakland resident
- UVA BA, Gordon-Conwell MDiv
- REI Embark Fellow, Louisville Institute grantee
- At TED 2026 as an attendee

PARTNERSHIP TYPES TO SCORE:
1. FUNDING: Philanthropists, foundation leaders, impact investors, CSR/ESG leaders
2. MEDIA & STORYTELLING: Filmmakers, journalists, content creators, podcasters
3. PROGRAMMATIC: Outdoor brands, parks agencies, youth-serving nonprofits, wellness brands, education leaders

SCORING GUIDANCE:
- 80-100: Strong, direct alignment with outdoor equity, family wellness, social cohesion, BIPOC communities
- 60-79: Moderate alignment, adjacent space
- 40-59: Loose alignment, general social impact
- 0-39: Minimal alignment

Be generous with scoring. If someone shows ANY interest in nature, families, community, equity, wellness, or belonging, score them at least 50.

For conversation_hook: Write a specific, warm opener Sally could use. Not salesy. Reference something from their profile.

Return a JSON object with these exact fields:
- relevance_score: integer 0-100
- partnership_type: one of "funding", "media_storytelling", "programmatic", "multiple", "unlikely"
- partnership_types: array of applicable types from ["funding", "media_storytelling", "programmatic"]
- reasoning: 1-2 sentence explanation
- conversation_hook: what Sally should say when meeting them
- key_signal: strongest signal in their profile for Outdoorithm alignment`;

// ── Apify LinkedIn Profile Scraper ────────────────────────────────────

async function scrapeLinkedInProfile(
  linkedinUrl: string,
  apifyKey: string
): Promise<Record<string, unknown> | null> {
  // Normalize URL
  let url = linkedinUrl.trim().replace(/\/$/, "");
  if (!url.startsWith("http")) url = "https://" + url;
  if (!url.includes("www.linkedin.com"))
    url = url.replace("linkedin.com", "www.linkedin.com");

  console.log(`Scraping LinkedIn profile: ${url}`);

  // Start Apify actor run
  const startResp = await fetch(
    `https://api.apify.com/v2/acts/harvestapi~linkedin-profile-scraper/runs?token=${apifyKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        profileUrls: [url],
        proxy: { useApifyProxy: true },
      }),
    }
  );

  if (!startResp.ok) {
    const err = await startResp.text();
    throw new Error(`Apify start failed: ${startResp.status} ${err}`);
  }

  const runData = await startResp.json();
  const runId = runData.data?.id;
  if (!runId) throw new Error("No run ID from Apify");

  console.log(`Apify run started: ${runId}`);

  // Poll for completion (max 90 seconds)
  const maxWait = 90_000;
  const pollInterval = 3_000;
  const start = Date.now();

  while (Date.now() - start < maxWait) {
    await new Promise((r) => setTimeout(r, pollInterval));

    const statusResp = await fetch(
      `https://api.apify.com/v2/actor-runs/${runId}?token=${apifyKey}`
    );
    const statusData = await statusResp.json();
    const status = statusData.data?.status;

    if (status === "SUCCEEDED") {
      // Fetch results
      const datasetId = statusData.data?.defaultDatasetId;
      const itemsResp = await fetch(
        `https://api.apify.com/v2/datasets/${datasetId}/items?token=${apifyKey}`
      );
      const items = await itemsResp.json();
      if (items.length > 0) {
        console.log(
          `Profile scraped: ${items[0].fullName || items[0].firstName}`
        );
        return items[0];
      }
      return null;
    }

    if (status === "FAILED" || status === "ABORTED" || status === "TIMED-OUT") {
      throw new Error(`Apify run ${status}`);
    }
  }

  throw new Error("Apify run timed out after 90s");
}

// ── GPT-5 Mini Scoring ────────────────────────────────────────────────

async function scoreWithGPT(
  profile: Record<string, unknown>,
  openaiKey: string
): Promise<Record<string, unknown>> {
  const parts: string[] = [];

  const fullName =
    (profile.fullName as string) ||
    `${profile.firstName || ""} ${profile.lastName || ""}`.trim();
  parts.push(`NAME: ${fullName}`);

  if (profile.headline) parts.push(`HEADLINE: ${profile.headline}`);
  if (profile.about)
    parts.push(`ABOUT: ${(profile.about as string).slice(0, 500)}`);

  // Experience
  const exp = (profile.experience || profile.positions || []) as Array<
    Record<string, unknown>
  >;
  if (exp.length > 0) {
    const expStrs = exp.slice(0, 5).map((e) => {
      const title = e.position || e.title || "";
      const company = e.companyName || e.company || "";
      return `${title} at ${company}`;
    });
    parts.push(`EXPERIENCE: ${expStrs.join(" | ")}`);
  }

  // Education
  const edu = (profile.education || []) as Array<Record<string, unknown>>;
  if (edu.length > 0) {
    const eduStrs = edu.slice(0, 3).map((e) => {
      const school = e.schoolName || e.school || "";
      const degree = e.degree || e.degreeName || "";
      return degree ? `${degree} from ${school}` : school;
    });
    parts.push(`EDUCATION: ${eduStrs.join(" | ")}`);
  }

  // Volunteering
  const vol = (profile.volunteering || []) as Array<Record<string, unknown>>;
  if (vol.length > 0) {
    const volStrs = vol.slice(0, 3).map((e) => {
      const role = e.position || e.title || "";
      const org = e.companyName || e.company || "";
      return `${role} at ${org}`;
    });
    parts.push(`VOLUNTEER: ${volStrs.join(" | ")}`);
  }

  if (profile.city || profile.country) {
    parts.push(
      `LOCATION: ${[profile.city, profile.country].filter(Boolean).join(", ")}`
    );
  }

  const userPrompt = parts.join("\n");
  console.log(`GPT scoring: ${fullName}`);

  const resp = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${openaiKey}`,
    },
    body: JSON.stringify({
      model: "gpt-5-mini",
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ],
      response_format: { type: "json_object" },
    }),
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`OpenAI error: ${resp.status} ${err}`);
  }

  const data = await resp.json();
  const content = data.choices?.[0]?.message?.content;
  if (!content) throw new Error("No GPT response content");

  const result = JSON.parse(content);
  return {
    fullName,
    headline: profile.headline || "",
    ...result,
  };
}

// ── Main Handler ──────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { linkedin_url } = await req.json();
    if (!linkedin_url) {
      return new Response(
        JSON.stringify({ error: "linkedin_url is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const apifyKey = Deno.env.get("APIFY_API_KEY");
    const openaiKey = Deno.env.get("OPENAI_APIKEY");

    if (!apifyKey || !openaiKey) {
      return new Response(
        JSON.stringify({ error: "Missing API keys" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Step 1: Scrape LinkedIn profile
    const profile = await scrapeLinkedInProfile(linkedin_url, apifyKey);
    if (!profile) {
      return new Response(
        JSON.stringify({ error: "Could not scrape LinkedIn profile" }),
        { status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Step 2: Score with GPT
    const scored = await scoreWithGPT(profile, openaiKey);

    // Step 3: Build response for client to insert into ted_attendees
    const fullName =
      (profile.fullName as string) ||
      `${profile.firstName || ""} ${profile.lastName || ""}`.trim();

    // Extract current company/title from experience
    const exp = (profile.experience || profile.positions || []) as Array<
      Record<string, unknown>
    >;
    const currentJob = exp.length > 0 ? exp[0] : {};

    const result = {
      ted_id: Date.now(), // Use timestamp as unique ID for non-TED contacts
      ted_name: fullName,
      ted_firstname: (profile.firstName as string) || fullName.split(" ")[0],
      ted_lastname:
        (profile.lastName as string) || fullName.split(" ").slice(1).join(" "),
      ted_title:
        (currentJob.position as string) ||
        (currentJob.title as string) ||
        (profile.headline as string) ||
        "",
      ted_org:
        (currentJob.companyName as string) ||
        (currentJob.company as string) ||
        "",
      ted_city: (profile.city as string) || "",
      ted_country: (profile.country as string) || "",
      ted_about: (profile.about as string) || "",
      ted_photo: (profile.profilePicture as string) || "",
      ted_linkedin: linkedin_url
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.linkedin.com/in/", "")
        .replace(/\/$/, ""),
      relevance_score: scored.relevance_score,
      partnership_type: scored.partnership_type,
      partnership_types: scored.partnership_types || [],
      reasoning: scored.reasoning,
      conversation_hook: scored.conversation_hook,
      key_signal: scored.key_signal || "",
      sally_pinned: true,
    };

    return new Response(JSON.stringify(result), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("Error:", message);
    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
