// Conference Networking Toolkit — Generic LinkedIn Enrichment + Scoring
//
// Takes a LinkedIn URL and conference_slug, reads the scoring prompt and
// partnership types from the conference_config table, scrapes the profile
// via Apify, scores with GPT-5 mini, and returns a scored attendee payload.
//
// Deploy:
//   SUPABASE_ACCESS_TOKEN=$SB_PAT supabase functions deploy conference-enrich \
//   --project-ref ypqsrejrsocebnldicke --no-verify-jwt --use-api
// Secrets:
//   supabase secrets set APIFY_API_KEY=... OPENAI_APIKEY=...

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// ── Config types ────────────────────────────────────────────────────────

interface ConferenceConfigRow {
  slug: string;
  name: string;
  scoring_prompt: string;
  partnership_types: string[];
  primary_user_name: string;
  table_name: string;
}

// ── Helpers ─────────────────────────────────────────────────────────────

function jsonResponse(body: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function asText(value: unknown, maxLength = 500): string {
  if (typeof value !== "string") return "";
  return value.trim().slice(0, maxLength);
}

function clampScore(value: unknown): number {
  const parsed = typeof value === "number"
    ? value
    : Number.parseInt(asText(value, 32), 10);

  if (Number.isNaN(parsed)) return 0;
  return Math.max(0, Math.min(100, Math.round(parsed)));
}

function normalizePartnershipType(
  value: unknown,
  validTypes: string[],
): string {
  const normalized = asText(value, 64).toLowerCase();
  return validTypes.includes(normalized) ? normalized : "unlikely";
}

function normalizePartnershipTypes(
  value: unknown,
  validTypes: string[],
): string[] {
  if (!Array.isArray(value)) return [];

  // Base types = everything except "multiple" and "unlikely"
  const baseTypes = validTypes.filter(
    (t) => t !== "multiple" && t !== "unlikely",
  );

  const normalized = value
    .map((item) => asText(item, 64).toLowerCase())
    .filter((item) => baseTypes.includes(item));

  return [...new Set(normalized)];
}

function firstNonEmpty(...values: unknown[]): string {
  for (const value of values) {
    const text = asText(value, 500);
    if (text) return text;
  }
  return "";
}

function parseLinkedInUrl(value: unknown): URL {
  const raw = asText(value, 2000);
  if (!raw) throw new Error("linkedin_url is required");

  const withProtocol = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;

  let parsed: URL;
  try {
    parsed = new URL(withProtocol);
  } catch {
    throw new Error("Invalid LinkedIn URL");
  }

  const host = parsed.hostname.replace(/^www\./i, "").toLowerCase();
  if (host !== "linkedin.com" && !host.endsWith(".linkedin.com")) {
    throw new Error("linkedin_url must be a LinkedIn profile URL");
  }

  const segments = parsed.pathname.split("/").filter(Boolean);
  if (segments[0] !== "in" || !segments[1]) {
    throw new Error("linkedin_url must use the /in/username format");
  }

  parsed.protocol = "https:";
  parsed.hostname = "www.linkedin.com";
  parsed.pathname = `/in/${segments[1]}`;
  parsed.search = "";
  parsed.hash = "";

  return parsed;
}

function extractLinkedInUsername(url: URL): string {
  const segments = url.pathname.split("/").filter(Boolean);
  return segments[1] || "";
}

function deterministicId(seed: string): number {
  let hash = 2166136261;
  for (const char of seed.toLowerCase()) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return 900_000_000 + ((hash >>> 0) % 1_000_000_000);
}

async function readJsonResponse(
  url: string,
  init: RequestInit,
  errorPrefix: string,
): Promise<unknown> {
  const resp = await fetch(url, init);
  const text = await resp.text();

  if (!resp.ok) {
    throw new Error(`${errorPrefix}: ${resp.status} ${text}`);
  }

  return text ? JSON.parse(text) : null;
}

// ── Load conference config from Supabase ────────────────────────────────

async function loadConferenceConfig(
  slug: string,
): Promise<ConferenceConfigRow> {
  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

  if (!supabaseUrl || !serviceRoleKey) {
    throw new Error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
  }

  const url =
    `${supabaseUrl}/rest/v1/conference_config?slug=eq.${encodeURIComponent(slug)}&select=*`;

  const resp = await fetch(url, {
    method: "GET",
    headers: {
      apikey: serviceRoleKey,
      Authorization: `Bearer ${serviceRoleKey}`,
      "Content-Type": "application/json",
    },
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`Failed to load conference config: ${resp.status} ${err}`);
  }

  const rows = (await resp.json()) as ConferenceConfigRow[];
  if (!rows || rows.length === 0) {
    throw new Error(`No conference config found for slug: ${slug}`);
  }

  return rows[0];
}

// ── Apify LinkedIn Profile Scraper ────────────────────────────────────

async function scrapeLinkedInProfile(
  linkedinUrl: string,
  apifyKey: string,
): Promise<Record<string, unknown> | null> {
  console.log(`Scraping LinkedIn profile: ${linkedinUrl}`);

  const startData = (await readJsonResponse(
    `https://api.apify.com/v2/acts/harvestapi~linkedin-profile-scraper/runs?token=${apifyKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        profileUrls: [linkedinUrl],
        proxy: { useApifyProxy: true },
      }),
    },
    "Apify start failed",
  )) as { data?: { id?: string } };

  const runId = startData.data?.id;
  if (!runId) throw new Error("No run ID from Apify");

  console.log(`Apify run started: ${runId}`);

  const maxWait = 90_000;
  const pollInterval = 3_000;
  const start = Date.now();

  while (Date.now() - start < maxWait) {
    await new Promise((resolve) => setTimeout(resolve, pollInterval));

    const statusData = (await readJsonResponse(
      `https://api.apify.com/v2/actor-runs/${runId}?token=${apifyKey}`,
      { method: "GET" },
      "Apify status failed",
    )) as {
      data?: { status?: string; defaultDatasetId?: string };
    };

    const status = statusData.data?.status;

    if (status === "SUCCEEDED") {
      const datasetId = statusData.data?.defaultDatasetId;
      if (!datasetId) throw new Error("Apify run succeeded without a dataset");

      const items = (await readJsonResponse(
        `https://api.apify.com/v2/datasets/${datasetId}/items?token=${apifyKey}`,
        { method: "GET" },
        "Apify dataset fetch failed",
      )) as unknown[];

      if (Array.isArray(items) && items.length > 0) {
        const profile = items[0];
        if (profile && typeof profile === "object") {
          console.log(
            `Profile scraped: ${
              firstNonEmpty(
                (profile as Record<string, unknown>).fullName,
                (profile as Record<string, unknown>).firstName,
              )
            }`,
          );
          return profile as Record<string, unknown>;
        }
      }

      return null;
    }

    if (
      status === "FAILED" || status === "ABORTED" || status === "TIMED-OUT"
    ) {
      throw new Error(`Apify run ${status}`);
    }
  }

  throw new Error("Apify run timed out after 90s");
}

// ── GPT-5 Mini Scoring ────────────────────────────────────────────────

function normalizeScoredResult(
  raw: Record<string, unknown>,
  validTypes: string[],
) {
  return {
    relevance_score: clampScore(raw.relevance_score),
    partnership_type: normalizePartnershipType(raw.partnership_type, validTypes),
    partnership_types: normalizePartnershipTypes(
      raw.partnership_types,
      validTypes,
    ),
    reasoning: asText(raw.reasoning, 400),
    conversation_hook: asText(raw.conversation_hook, 300),
    key_signal: asText(raw.key_signal, 200),
  };
}

async function scoreWithGPT(
  profile: Record<string, unknown>,
  openaiKey: string,
  systemPrompt: string,
  validTypes: string[],
) {
  const parts: string[] = [];

  const fullName = asText(profile.fullName, 200) ||
    `${firstNonEmpty(profile.firstName)} ${firstNonEmpty(profile.lastName)}`
      .trim();
  parts.push(`NAME: ${fullName}`);

  const headline = asText(profile.headline, 300);
  if (headline) parts.push(`HEADLINE: ${headline}`);

  const about = asText(profile.about, 500);
  if (about) parts.push(`ABOUT: ${about}`);

  const exp = (profile.experience || profile.positions || []) as Array<
    Record<string, unknown>
  >;
  if (exp.length > 0) {
    const expStrs = exp.slice(0, 5).map((entry) => {
      const title = firstNonEmpty(entry.position, entry.title);
      const company = firstNonEmpty(entry.companyName, entry.company);
      return [title, company].filter(Boolean).join(" at ");
    }).filter(Boolean);
    if (expStrs.length > 0) parts.push(`EXPERIENCE: ${expStrs.join(" | ")}`);
  }

  const edu = (profile.education || []) as Array<Record<string, unknown>>;
  if (edu.length > 0) {
    const eduStrs = edu.slice(0, 3).map((entry) => {
      const school = firstNonEmpty(entry.schoolName, entry.school);
      const degree = firstNonEmpty(entry.degree, entry.degreeName);
      return degree ? `${degree} from ${school}` : school;
    }).filter(Boolean);
    if (eduStrs.length > 0) parts.push(`EDUCATION: ${eduStrs.join(" | ")}`);
  }

  const vol = (profile.volunteering || []) as Array<Record<string, unknown>>;
  if (vol.length > 0) {
    const volStrs = vol.slice(0, 3).map((entry) => {
      const role = firstNonEmpty(entry.position, entry.title);
      const org = firstNonEmpty(entry.companyName, entry.company);
      return [role, org].filter(Boolean).join(" at ");
    }).filter(Boolean);
    if (volStrs.length > 0) parts.push(`VOLUNTEER: ${volStrs.join(" | ")}`);
  }

  const location = [asText(profile.city, 100), asText(profile.country, 100)]
    .filter(Boolean)
    .join(", ");
  if (location) parts.push(`LOCATION: ${location}`);

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
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      response_format: { type: "json_object" },
    }),
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`OpenAI error: ${resp.status} ${err}`);
  }

  const data = (await resp.json()) as {
    choices?: Array<{ message?: { content?: string } }>;
  };
  const content = data.choices?.[0]?.message?.content;
  if (!content) throw new Error("No GPT response content");

  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(content);
  } catch {
    throw new Error("GPT returned invalid JSON");
  }

  return normalizeScoredResult(parsed, validTypes);
}

// ── Main Handler ──────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  const authHeader = req.headers.get("authorization") || "";
  if (!authHeader.startsWith("Bearer ")) {
    return jsonResponse({ error: "Missing Authorization header" }, 401);
  }

  const anonKey = Deno.env.get("SUPABASE_ANON_KEY");
  const token = authHeader.slice("Bearer ".length).trim();
  if (anonKey && token !== anonKey) {
    return jsonResponse({ error: "Invalid authorization token" }, 401);
  }

  try {
    const body = (await req.json()) as {
      linkedin_url?: unknown;
      conference_slug?: unknown;
    };

    // Validate inputs
    const conferenceSlug = asText(body.conference_slug, 100);
    if (!conferenceSlug) {
      return jsonResponse({ error: "conference_slug is required" }, 400);
    }

    const linkedinUrl = parseLinkedInUrl(body.linkedin_url);
    const linkedinUsername = extractLinkedInUsername(linkedinUrl);

    const apifyKey = Deno.env.get("APIFY_API_KEY");
    const openaiKey = Deno.env.get("OPENAI_APIKEY");

    if (!apifyKey || !openaiKey) {
      return jsonResponse({ error: "Missing API keys" }, 500);
    }

    // Load conference config from database
    console.log(`Loading config for conference: ${conferenceSlug}`);
    const config = await loadConferenceConfig(conferenceSlug);

    // Derive field prefix from table name (e.g., "ted_attendees" -> "ted")
    const fieldPrefix = config.table_name.split("_")[0];

    // Scrape LinkedIn profile
    const profile = await scrapeLinkedInProfile(
      linkedinUrl.toString(),
      apifyKey,
    );
    if (!profile) {
      return jsonResponse({ error: "Could not scrape LinkedIn profile" }, 404);
    }

    // Score with GPT using the config's scoring prompt
    const scored = await scoreWithGPT(
      profile,
      openaiKey,
      config.scoring_prompt,
      config.partnership_types,
    );

    const fullName = asText(profile.fullName, 200) ||
      `${firstNonEmpty(profile.firstName)} ${firstNonEmpty(profile.lastName)}`
        .trim();

    if (!fullName) {
      return jsonResponse(
        { error: "LinkedIn profile did not include a name" },
        422,
      );
    }

    const exp = (profile.experience || profile.positions || []) as Array<
      Record<string, unknown>
    >;
    const currentJob = exp.length > 0 ? exp[0] : {};

    // Build result with config-driven field prefix
    const pinnedCol = `${config.primary_user_name.toLowerCase()}_pinned`;

    const result: Record<string, unknown> = {
      [`${fieldPrefix}_id`]: deterministicId(linkedinUsername),
      [`${fieldPrefix}_name`]: fullName,
      [`${fieldPrefix}_firstname`]: firstNonEmpty(profile.firstName) ||
        fullName.split(/\s+/)[0] || "",
      [`${fieldPrefix}_lastname`]: firstNonEmpty(profile.lastName) ||
        fullName.split(/\s+/).slice(1).join(" "),
      [`${fieldPrefix}_title`]: firstNonEmpty(
        currentJob.position,
        currentJob.title,
        profile.headline,
      ),
      [`${fieldPrefix}_org`]: firstNonEmpty(
        currentJob.companyName,
        currentJob.company,
      ),
      [`${fieldPrefix}_city`]: asText(profile.city, 100),
      [`${fieldPrefix}_country`]: asText(profile.country, 100),
      [`${fieldPrefix}_about`]: asText(profile.about, 1200),
      [`${fieldPrefix}_photo`]: firstNonEmpty(
        profile.profilePicture,
        profile.profilePictureUrl,
      ),
      [`${fieldPrefix}_linkedin`]: linkedinUsername,
      ...scored,
      [pinnedCol]: true,
    };

    return jsonResponse(result);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("Error:", message);
    const status = message === "linkedin_url is required" ||
        message === "conference_slug is required" ||
        message.startsWith("Invalid LinkedIn URL") ||
        message.startsWith("linkedin_url must")
      ? 400
      : message.startsWith("No conference config found")
      ? 404
      : 500;
    return jsonResponse({ error: message }, status);
  }
});
