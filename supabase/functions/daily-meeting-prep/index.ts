// Daily Meeting Prep — Supabase Edge Function
//
// Sweeps 5 Google Calendar accounts, researches attendees, generates prep memos
// with Claude Sonnet 4.6, creates a Google Doc, and attaches it to calendar events.
//
// Triggered daily at 15:00 UTC (7am PST) via pg_cron → pg_net HTTP POST.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

// ── Types ───────────────────────────────────────────────────────────────────

interface GoogleAccount {
  email: string;
  label: string;
  refreshToken: string;
  clientId: string;
  clientSecret: string;
  accessToken?: string;
}

interface CalendarEvent {
  id: string;
  summary?: string;
  description?: string;
  location?: string;
  start?: { dateTime?: string; date?: string };
  end?: { dateTime?: string; date?: string };
  attendees?: Array<{
    email: string;
    displayName?: string;
    responseStatus?: string;
    organizer?: boolean;
  }>;
  recurringEventId?: string;
  status?: string;
  _accountEmail: string;
  _accountLabel: string;
}

interface AttendeeProfile {
  email: string;
  displayName: string;
  name: string;
  inDb: boolean;
  contactId?: number;
  position?: string;
  company?: string;
  headline?: string;
  location?: string;
  linkedinUrl?: string;
  commsCloseness?: string;
  commsMomentum?: string;
  commsChronological?: string;
  totalMessages?: number;
  sharedBackground?: string[];
  primaryInterests?: string[];
  talkingPointsFromTags?: string[];
  kindoraProspectType?: string;
  kindoraPitchFit?: string;
  askReadinessTier?: string;
  askReadinessScore?: number;
  taxonomy?: string;
  webResearch?: string;
}

interface CommsHistory {
  emails: Array<Record<string, unknown>>;
  meetings: Array<Record<string, unknown>>;
}

interface MemoData {
  event: CalendarEvent;
  memoText: string;
}

// ── Config ──────────────────────────────────────────────────────────────────

const ENTITY_MAP: Record<string, string> = {
  "justin@kindora.co": "kindora",
  "justin@outdoorithm.com": "outdoorithm",
  "justin@outdoorithmcollective.org": "outdoorithm",
  "justin@truesteele.com": "truesteele",
  "justinrsteele@gmail.com": "truesteele",
};

const ORG_CONTEXT: Record<string, { entity: string; focus: string; pitch: string }> = {
  kindora: {
    entity: "Kindora",
    focus: "New users, distribution, marketing, sales, funding partnerships",
    pitch: "AI-powered fundraising intelligence for nonprofits. Grant discovery, AI-assisted grant writing, pipeline management, funder intelligence.",
  },
  outdoorithm: {
    entity: "Outdoorithm / Outdoorithm Collective",
    focus: "Fundraising, partnerships, program expansion, donor cultivation",
    pitch: "Getting every family outside. AI-powered camping platform + nonprofit providing outdoor access for urban families.",
  },
  truesteele: {
    entity: "True Steele Labs",
    focus: "Client acquisition for AI product studio builds",
    pitch: "Founder-led AI product studio. Fixed-fee, time-boxed builds for mission-driven orgs. $18K-$250K+ depending on scope.",
  },
};

const JUSTIN_BIO = `Justin Steele is a tech founder and consultant based in Oakland, CA.
He's the CEO & Co-Founder of Kindora (AI-powered fundraising intelligence for nonprofits),
Co-Founder of Outdoorithm (AI camping platform) and Outdoorithm Collective (nonprofit for
outdoor access for urban families), and founder of True Steele Labs (AI product studio for
social impact). Previously, he led Google.org's philanthropy across the Americas for nearly
a decade, directing $700M+ in strategic investments. He holds a BS in Chemical Engineering
from UVA, an MBA from Harvard Business School, and an MPA from Harvard Kennedy School.
He sits on the San Francisco Foundation board.`;

const JUSTIN_SCHOOLS = ["University of Virginia", "Harvard Business School", "Harvard Kennedy School"];
const JUSTIN_COMPANIES = ["Bain & Company", "The Bridgespan Group", "Year Up", "Google", "Google.org"];

const JUSTIN_EMAILS = new Set([
  "justinrsteele@gmail.com",
  "justin@truesteele.com",
  "justin@kindora.co",
  "justin@outdoorithm.com",
  "justin@outdoorithmcollective.org",
  "justin.steele@gmail.com",
  "justinrichardsteele@gmail.com",
]);

const CONFIG = {
  excludedDomains: ["flourishfund.org"],
  excludedEmails: [] as string[],
  internalEmails: ["sally@outdoorithmcollective.org", "sally.steele@gmail.com", "karibu@kindora.co"],
  skipRecurring: true,
  skipDeclined: true,
  skipAllDay: true,
  skipCancelled: true,
  skipKeywords: ["wellness session", "group workshop"],
  addUnknownContacts: true,
  contactPoolForNew: "meeting",
  googleDocFolderName: "Meeting Prep Memos",
  googleDocAccount: "justin@truesteele.com",
  attachToCalendar: true,
  reuseDailyGoogleDoc: true,
  perplexityModel: "sonar-pro",
  memoModel: "claude-sonnet-4-6",
  timezone: "America/Los_Angeles",
};

// ── Google OAuth ────────────────────────────────────────────────────────────

function loadGoogleAccounts(): GoogleAccount[] {
  const credsJson = Deno.env.get("GOOGLE_ACCOUNTS_CREDS");
  if (!credsJson) throw new Error("GOOGLE_ACCOUNTS_CREDS secret not set");

  const creds = JSON.parse(credsJson) as Record<string, {
    refresh_token: string;
    client_id: string;
    client_secret: string;
  }>;

  const accounts: { email: string; label: string }[] = [
    { email: "justinrsteele@gmail.com", label: "Personal Gmail" },
    { email: "justin@truesteele.com", label: "True Steele" },
    { email: "justin@kindora.co", label: "Kindora" },
    { email: "justin@outdoorithm.com", label: "Outdoorithm" },
    { email: "justin@outdoorithmcollective.org", label: "Outdoorithm Collective" },
  ];

  return accounts.map((a) => {
    const c = creds[a.email];
    if (!c) throw new Error(`Missing credentials for ${a.email}`);
    return {
      ...a,
      refreshToken: c.refresh_token,
      clientId: c.client_id,
      clientSecret: c.client_secret,
    };
  });
}

async function refreshAccessToken(account: GoogleAccount): Promise<string> {
  const resp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: account.refreshToken,
      client_id: account.clientId,
      client_secret: account.clientSecret,
    }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Token refresh failed for ${account.email}: ${resp.status} ${text}`);
  }

  const data = await resp.json();
  return data.access_token;
}

async function refreshAllTokens(accounts: GoogleAccount[]): Promise<void> {
  const results = await Promise.allSettled(
    accounts.map(async (a) => {
      a.accessToken = await refreshAccessToken(a);
    })
  );
  for (let i = 0; i < results.length; i++) {
    if (results[i].status === "rejected") {
      console.error(`[TOKEN] Failed for ${accounts[i].email}: ${(results[i] as PromiseRejectedResult).reason}`);
    }
  }
}

// ── Google API helpers ──────────────────────────────────────────────────────

async function googleGet(url: string, token: string, params?: Record<string, string>) {
  const u = new URL(url);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      u.searchParams.set(k, v);
    }
  }
  const resp = await fetch(u.toString(), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Google API ${resp.status}: ${text.slice(0, 500)}`);
  }
  return resp.json();
}

async function googlePost(url: string, token: string, body: unknown) {
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Google API POST ${resp.status}: ${text.slice(0, 500)}`);
  }
  return resp.json();
}

async function googlePatch(url: string, token: string, body: unknown, params?: Record<string, string>) {
  const u = new URL(url);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      u.searchParams.set(k, v);
    }
  }
  const resp = await fetch(u.toString(), {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Google API PATCH ${resp.status}: ${text.slice(0, 500)}`);
  }
  return resp.json();
}

// ── Calendar Fetch ──────────────────────────────────────────────────────────

function getTodayDateRange(): { timeMin: string; timeMax: string; dateStr: string } {
  // Get today in Pacific time
  const now = new Date();
  const pacific = new Intl.DateTimeFormat("en-CA", {
    timeZone: CONFIG.timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);

  // Build day boundaries in Pacific
  const dayStart = new Date(`${pacific}T00:00:00`);
  const dayEnd = new Date(`${pacific}T23:59:59`);

  // Convert to UTC offset for Pacific time
  const pstOffset = getPacificOffsetHours(dayStart);
  const startUtc = new Date(dayStart.getTime() + pstOffset * 60 * 60 * 1000);
  const endUtc = new Date(dayEnd.getTime() + pstOffset * 60 * 60 * 1000);

  return {
    timeMin: startUtc.toISOString(),
    timeMax: endUtc.toISOString(),
    dateStr: pacific,
  };
}

function getPacificOffsetHours(date: Date): number {
  // Approximate PST/PDT offset
  const jan = new Date(date.getFullYear(), 0, 1);
  const jul = new Date(date.getFullYear(), 6, 1);
  const stdOffset = Math.max(jan.getTimezoneOffset(), jul.getTimezoneOffset());
  const isDst = date.getTimezoneOffset() < stdOffset;
  return isDst ? 7 : 8;
}

async function fetchCalendarEvents(accounts: GoogleAccount[]): Promise<CalendarEvent[]> {
  const { timeMin, timeMax, dateStr } = getTodayDateRange();
  console.log(`[CALENDAR] Fetching events for ${dateStr} (${timeMin} to ${timeMax})`);

  const allEvents: CalendarEvent[] = [];

  const results = await Promise.allSettled(
    accounts
      .filter((a) => a.accessToken)
      .map(async (account) => {
        const data = await googleGet(
          "https://www.googleapis.com/calendar/v3/calendars/primary/events",
          account.accessToken!,
          {
            timeMin,
            timeMax,
            singleEvents: "true",
            orderBy: "startTime",
            timeZone: CONFIG.timezone,
          }
        );
        const items = (data.items || []) as CalendarEvent[];
        for (const ev of items) {
          ev._accountEmail = account.email;
          ev._accountLabel = account.label;
        }
        console.log(`  [${account.label}] ${items.length} events`);
        return items;
      })
  );

  for (const r of results) {
    if (r.status === "fulfilled") {
      allEvents.push(...r.value);
    } else {
      console.error(`[CALENDAR] Error: ${r.reason}`);
    }
  }

  // Sort by start time
  allEvents.sort((a, b) => {
    const aTime = a.start?.dateTime || a.start?.date || "";
    const bTime = b.start?.dateTime || b.start?.date || "";
    return aTime.localeCompare(bTime);
  });

  return allEvents;
}

// ── Event Filtering ─────────────────────────────────────────────────────────

interface ExternalAttendee {
  email: string;
  displayName: string;
  responseStatus: string;
  organizer: boolean;
}

function getExternalAttendees(event: CalendarEvent): ExternalAttendee[] {
  const internal = new Set(CONFIG.internalEmails.map((e) => e.toLowerCase()));
  const excludedEmails = new Set(CONFIG.excludedEmails.map((e) => e.toLowerCase()));
  const excludedDomains = new Set(CONFIG.excludedDomains.map((d) => d.toLowerCase()));

  const external: ExternalAttendee[] = [];
  for (const a of event.attendees || []) {
    const email = (a.email || "").toLowerCase();
    if (!email) continue;
    if (JUSTIN_EMAILS.has(email)) continue;
    if (internal.has(email)) continue;
    if (excludedEmails.has(email)) continue;
    const domain = email.split("@")[1] || "";
    if (excludedDomains.has(domain)) continue;
    external.push({
      email,
      displayName: a.displayName || "",
      responseStatus: a.responseStatus || "",
      organizer: a.organizer || false,
    });
  }
  return external;
}

function shouldSkipEvent(event: CalendarEvent): string | null {
  if (CONFIG.skipCancelled && event.status === "cancelled") return "cancelled";
  if (CONFIG.skipAllDay && event.start?.date && !event.start?.dateTime) return "all-day event";
  if (CONFIG.skipRecurring && event.recurringEventId) return "recurring event";

  if (CONFIG.skipDeclined) {
    for (const a of event.attendees || []) {
      if (JUSTIN_EMAILS.has((a.email || "").toLowerCase()) && a.responseStatus === "declined") {
        return "declined";
      }
    }
  }

  if (CONFIG.skipKeywords.length > 0) {
    const haystack = `${event.summary || ""} ${event.description || ""}`.toLowerCase();
    for (const kw of CONFIG.skipKeywords) {
      if (kw && haystack.includes(kw)) return `keyword: ${kw}`;
    }
  }

  const ext = getExternalAttendees(event);
  if (ext.length === 0) return "no external attendees";

  return null;
}

function classifyEvents(events: CalendarEvent[]): {
  needsMemo: CalendarEvent[];
  skipped: Array<{ event: CalendarEvent; reason: string }>;
} {
  const needsMemo: CalendarEvent[] = [];
  const skipped: Array<{ event: CalendarEvent; reason: string }> = [];

  for (const ev of events) {
    const reason = shouldSkipEvent(ev);
    if (reason) {
      skipped.push({ event: ev, reason });
    } else {
      needsMemo.push(ev);
    }
  }

  return { needsMemo, skipped };
}

// ── Database ────────────────────────────────────────────────────────────────

function getSupabaseClient() {
  const url = Deno.env.get("SUPABASE_URL")!;
  const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  return createClient(url, key);
}

async function lookupContactByEmail(
  supabase: ReturnType<typeof createClient>,
  email: string
): Promise<Record<string, unknown> | null> {
  const lower = email.toLowerCase();

  const { data, error } = await supabase
    .from("contacts")
    .select(
      "id, first_name, last_name, normalized_full_name, email, email_2, " +
      "linkedin_url, linkedin_username, position, company, headline, summary, " +
      "location_name, city, state, enriched_at, " +
      "comms_summary, ai_tags, comms_closeness, comms_momentum, " +
      "comms_last_date, comms_thread_count, comms_meeting_count, " +
      "comms_last_meeting, comms_call_count, comms_last_call, " +
      "contact_pools, taxonomy_classification, " +
      "enrich_current_company, enrich_current_title, " +
      "enrich_schools, enrich_companies_worked, enrich_volunteer_orgs, " +
      "ask_readiness"
    )
    .or(`email.ilike.${lower},email_2.ilike.${lower},personal_email.ilike.${lower}`)
    .limit(1)
    .maybeSingle();

  if (error) {
    console.error(`[DB] Lookup error for ${email}: ${error.message}`);
    return null;
  }
  return data;
}

async function lookupCommsHistory(
  supabase: ReturnType<typeof createClient>,
  contactId: number
): Promise<CommsHistory> {
  const [emailsRes, meetingsRes] = await Promise.all([
    supabase
      .from("contact_email_threads")
      .select("subject, last_message_date, direction, message_count, account_email")
      .eq("contact_id", contactId)
      .order("last_message_date", { ascending: false })
      .limit(5),
    supabase
      .from("contact_calendar_events")
      .select("summary, start_time, duration_minutes, attendee_count, location")
      .eq("contact_id", contactId)
      .order("start_time", { ascending: false })
      .limit(5),
  ]);

  return {
    emails: emailsRes.data || [],
    meetings: meetingsRes.data || [],
  };
}

async function addMeetingContact(
  supabase: ReturnType<typeof createClient>,
  firstName: string,
  lastName: string,
  email: string,
  company?: string,
  pool = "meeting"
): Promise<number | null> {
  // Check if already exists
  const existing = await lookupContactByEmail(supabase, email);
  if (existing) return existing.id as number;

  const normalizedFullName = [firstName, lastName].filter(Boolean).join(" ").trim();

  const { data, error } = await supabase
    .from("contacts")
    .insert({
      first_name: firstName || "Unknown",
      last_name: lastName || "",
      normalized_first_name: (firstName || "").toLowerCase(),
      normalized_last_name: (lastName || "").toLowerCase(),
      normalized_full_name: normalizedFullName,
      email,
      company: company || null,
      contact_pools: [pool],
    })
    .select("id")
    .single();

  if (error) {
    console.error(`[DB] Insert error: ${error.message}`);
    return null;
  }
  return data.id;
}

// ── Shared Background ───────────────────────────────────────────────────────

function findSharedBackground(contact: Record<string, unknown>): string[] {
  const shared: string[] = [];
  const schools = (contact.enrich_schools as string[]) || [];
  const companies = (contact.enrich_companies_worked as string[]) || [];

  for (const s of schools) {
    for (const js of JUSTIN_SCHOOLS) {
      if (js.toLowerCase().includes(s.toLowerCase()) || s.toLowerCase().includes(js.toLowerCase())) {
        shared.push(`Both attended ${s}`);
      }
    }
  }
  for (const c of companies) {
    for (const jc of JUSTIN_COMPANIES) {
      if (jc.toLowerCase().includes(c.toLowerCase()) || c.toLowerCase().includes(jc.toLowerCase())) {
        shared.push(`Both worked at ${c}`);
      }
    }
  }
  return shared;
}

// ── Perplexity Research ─────────────────────────────────────────────────────

async function researchPerson(name: string, email: string, company?: string): Promise<string> {
  const apiKey = Deno.env.get("PERPLEXITY_APIKEY");
  if (!apiKey) return "[Perplexity API key not set]";

  const domain = email.split("@")[1] || "";
  const personalDomains = new Set(["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]);
  let query = `Who is ${name}`;
  if (company) {
    query += ` at ${company}`;
  } else if (!personalDomains.has(domain)) {
    query += ` at ${domain}`;
  }
  query += "? LinkedIn profile, career background, education, current role, notable achievements.";

  try {
    const resp = await fetch("https://api.perplexity.ai/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: CONFIG.perplexityModel,
        messages: [
          { role: "system", content: "You are a research assistant. Provide a concise professional profile in 300-500 words." },
          { role: "user", content: query },
        ],
        max_tokens: 800,
      }),
    });

    if (!resp.ok) {
      const text = await resp.text();
      return `[Perplexity research failed: ${resp.status} ${text.slice(0, 200)}]`;
    }

    const data = await resp.json();
    return data.choices?.[0]?.message?.content || "[No research content]";
  } catch (e) {
    return `[Perplexity research error: ${e}]`;
  }
}

function guessNameFromEmail(email: string, displayName = ""): { first: string; last: string } {
  if (displayName && displayName.includes(" ")) {
    const parts = displayName.trim().split(/\s+/);
    return { first: parts[0], last: parts.slice(1).join(" ") };
  }
  const prefix = email.split("@")[0];
  for (const sep of [".", "_", "-"]) {
    if (prefix.includes(sep)) {
      const parts = prefix.split(sep, 2);
      return {
        first: parts[0].charAt(0).toUpperCase() + parts[0].slice(1),
        last: parts[1].charAt(0).toUpperCase() + parts[1].slice(1),
      };
    }
  }
  return { first: prefix.charAt(0).toUpperCase() + prefix.slice(1), last: "" };
}

// ── Attendee Research Pipeline ──────────────────────────────────────────────

async function researchAttendees(
  event: CalendarEvent,
  supabase: ReturnType<typeof createClient>
): Promise<{ profiles: AttendeeProfile[]; comms: CommsHistory }> {
  const external = getExternalAttendees(event);
  const profiles: AttendeeProfile[] = [];
  const allComms: CommsHistory = { emails: [], meetings: [] };

  for (const att of external) {
    const email = att.email;
    console.log(`     Researching ${email}...`);

    const contact = await lookupContactByEmail(supabase, email);

    if (contact) {
      const name = (contact.normalized_full_name as string) ||
        `${contact.first_name || ""} ${contact.last_name || ""}`.trim();
      console.log(`       Found in DB: ${name} (id:${contact.id})`);

      const profile: AttendeeProfile = {
        email,
        displayName: att.displayName,
        name,
        inDb: true,
        contactId: contact.id as number,
        position: (contact.enrich_current_title as string) || (contact.position as string) || "",
        company: (contact.enrich_current_company as string) || (contact.company as string) || "",
        headline: (contact.headline as string) || "",
        location: (contact.location_name as string) || (contact.city as string) || "",
        linkedinUrl: (contact.linkedin_url as string) || "",
        commsCloseness: (contact.comms_closeness as string) || "unknown",
        commsMomentum: (contact.comms_momentum as string) || "unknown",
        taxonomy: (contact.taxonomy_classification as string) || "",
      };

      // Comms summary
      const cs = contact.comms_summary as Record<string, unknown> | null;
      if (cs) {
        profile.commsChronological = (cs.chronological_summary as string) || "";
        profile.totalMessages = (cs.total_messages as number) || 0;
      }

      // AI tags
      const tags = contact.ai_tags as Record<string, unknown> | null;
      if (tags) {
        const tp = tags.topical_affinity as Record<string, unknown> | undefined;
        if (tp) {
          profile.primaryInterests = (tp.primary_interests as string[]) || [];
          profile.talkingPointsFromTags = (tp.talking_points as string[]) || [];
        }
        const sf = tags.sales_fit as Record<string, unknown> | undefined;
        if (sf) {
          profile.kindoraProspectType = (sf.prospect_type as string) || "";
          profile.kindoraPitchFit = (sf.kindora_pitch_fit as string) || "";
        }
      }

      // Ask readiness
      const ar = contact.ask_readiness as Record<string, unknown> | null;
      if (ar) {
        const ofr = ar.outdoorithm_fundraising as Record<string, unknown> | undefined;
        if (ofr) {
          profile.askReadinessTier = (ofr.tier as string) || "";
          profile.askReadinessScore = (ofr.score as number) || 0;
        }
      }

      // Shared background
      const shared = findSharedBackground(contact);
      if (shared.length > 0) profile.sharedBackground = shared;

      // Comms history
      const comms = await lookupCommsHistory(supabase, contact.id as number);
      allComms.emails.push(...comms.emails);
      allComms.meetings.push(...comms.meetings);

      profiles.push(profile);
    } else {
      // Not in DB — web research
      const { first, last } = guessNameFromEmail(email, att.displayName);
      const name = `${first} ${last}`.trim() || email.split("@")[0];
      const domain = email.split("@")[1] || "";
      const personalDomains = new Set(["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]);
      const companyGuess = personalDomains.has(domain) ? undefined : domain.split(".")[0].charAt(0).toUpperCase() + domain.split(".")[0].slice(1);

      console.log(`       Not in DB. Web research for '${name}'...`);
      const research = await researchPerson(name, email, companyGuess);
      // Rate limit delay
      await new Promise((r) => setTimeout(r, 1500));

      const profile: AttendeeProfile = {
        email,
        displayName: att.displayName,
        name,
        inDb: false,
        company: companyGuess || "",
        webResearch: research,
      };

      // Auto-add as meeting contact
      if (CONFIG.addUnknownContacts && first) {
        const newId = await addMeetingContact(supabase, first, last, email, companyGuess, CONFIG.contactPoolForNew);
        if (newId) {
          console.log(`       Added as meeting contact (id:${newId})`);
          profile.contactId = newId;
        }
      }

      profiles.push(profile);
    }
  }

  return { profiles, comms: allComms };
}

// ── Memo Generation (Claude Sonnet 4.6) ─────────────────────────────────────

function buildMemoPrompt(
  event: CalendarEvent,
  profiles: AttendeeProfile[],
  comms: CommsHistory,
  entityKey: string
): string {
  const entityCtx = ORG_CONTEXT[entityKey] || ORG_CONTEXT.truesteele;

  const start = event.start?.dateTime || "";
  const end = event.end?.dateTime || "";
  const summary = event.summary || "Untitled Meeting";
  const location = event.location || "No location";
  const description = (event.description || "").slice(0, 2000);
  const account = event._accountLabel || "Unknown";

  // Build attendee text
  let attendeeText = "";
  for (const p of profiles) {
    attendeeText += `\n**${p.name}**\n`;
    attendeeText += `- Email: ${p.email}\n`;
    if (p.position) attendeeText += `- Title: ${p.position}\n`;
    if (p.company) attendeeText += `- Company: ${p.company}\n`;
    if (p.headline) attendeeText += `- Headline: ${p.headline}\n`;
    if (p.location) attendeeText += `- Location: ${p.location}\n`;
    if (p.linkedinUrl) attendeeText += `- LinkedIn: ${p.linkedinUrl}\n`;
    if (p.commsCloseness) attendeeText += `- Relationship: ${p.commsCloseness} (momentum: ${p.commsMomentum || "?"})\n`;
    if (p.commsChronological) attendeeText += `- Comms history: ${p.commsChronological}\n`;
    if (p.sharedBackground?.length) attendeeText += `- SHARED BACKGROUND: ${p.sharedBackground.join("; ")}\n`;
    if (p.primaryInterests?.length) attendeeText += `- Interests: ${p.primaryInterests.slice(0, 5).join(", ")}\n`;
    if (p.talkingPointsFromTags?.length) attendeeText += `- Existing talking points: ${p.talkingPointsFromTags.slice(0, 3).join("; ")}\n`;
    if (p.kindoraProspectType) attendeeText += `- Kindora prospect: ${p.kindoraProspectType} (fit: ${p.kindoraPitchFit || "?"})\n`;
    if (p.askReadinessTier) attendeeText += `- OC ask readiness: ${p.askReadinessTier} (score: ${p.askReadinessScore || "?"})\n`;
    if (p.taxonomy) attendeeText += `- Category: ${p.taxonomy}\n`;
    if (p.webResearch) attendeeText += `- Web research:\n${p.webResearch.slice(0, 1500)}\n`;
  }

  // Build comms text
  let commsText = "";
  if (comms.emails.length > 0) {
    commsText += "\nRecent email threads:\n";
    for (const e of comms.emails.slice(0, 5)) {
      const d = String(e.last_message_date || "").slice(0, 10);
      commsText += `  - [${d}] ${e.subject || ""} (${e.direction || ""}, ${e.message_count || 0} msgs)\n`;
    }
  }
  if (comms.meetings.length > 0) {
    commsText += "\nPast calendar meetings:\n";
    for (const m of comms.meetings.slice(0, 5)) {
      const d = String(m.start_time || "").slice(0, 10);
      commsText += `  - [${d}] ${m.summary || ""} (${m.duration_minutes || 0} min)\n`;
    }
  }

  return `Write a meeting prep memo for Justin Steele following this exact structure:

## Meeting: [Title]
**Time:** [time range and duration]
**Location:** [location or video link]
**Account:** [entity name]

### Attendees
A markdown table with columns: Name, Title, Organization, Relationship

### Key Profiles
For each attendee, 3-5 bullet points covering:
- Current role and career trajectory
- Any shared background with Justin (HIGHLIGHT these prominently)
- Communication history and relationship temperature

### Meeting Purpose & Context
- What this meeting is about (from description/calendly notes)
- Organization background (what they do, size, recent news if known)
- What prompted this meeting

### Strategic Angle: [Entity Name]
- Which of Justin's ventures this connects to and why
- What Justin can offer them
- What Justin should explore or ask for

### Talking Points
5 numbered, specific, actionable talking points with personalization hooks.
Reference shared experiences, mutual connections, or recent events.
Make these SPECIFIC not generic.

### Landmines to Avoid
2-3 specific things NOT to do or say

### Desired Outcome
- Best case
- Minimum acceptable
- Suggested follow-up action

---

CONTEXT FOR THIS MEMO:

**Justin's Bio:** ${JUSTIN_BIO}

**Meeting Details:**
- Title: ${summary}
- Time: ${start} to ${end}
- Location: ${location}
- Account: ${account}
- Description/Notes: ${description}

**Entity Context:**
- Entity: ${entityCtx.entity}
- Strategic Focus: ${entityCtx.focus}
- Elevator Pitch: ${entityCtx.pitch}

**Attendee Profiles:**
${attendeeText}

**Communication History:**
${commsText || "No prior communication history found with any attendee."}

INSTRUCTIONS:
- Write in a direct, practical style. No fluff.
- Shared background items (same school, employer, board) are GOLD. Highlight them prominently.
- Make talking points specific to THIS person and THIS meeting, not generic.
- If there's a stated agenda or Calendly question, address it directly in the Strategic Angle.
- Keep the whole memo scannable in under 2 minutes.`;
}

async function generateMemo(
  event: CalendarEvent,
  profiles: AttendeeProfile[],
  comms: CommsHistory,
  entityKey: string
): Promise<string> {
  const apiKey = Deno.env.get("ANTHROPIC_API_KEY");
  if (!apiKey) throw new Error("ANTHROPIC_API_KEY not set");

  const prompt = buildMemoPrompt(event, profiles, comms, entityKey);

  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: CONFIG.memoModel,
      max_tokens: 3000,
      messages: [{ role: "user", content: prompt }],
    }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Anthropic API ${resp.status}: ${text.slice(0, 500)}`);
  }

  const data = await resp.json();
  return data.content?.[0]?.text || "[No memo generated]";
}

// ── Google Doc Creation ─────────────────────────────────────────────────────

async function getOrCreateDriveFolder(token: string, folderName: string): Promise<string> {
  const escapedName = folderName.replace(/'/g, "\\'");
  const query = `name='${escapedName}' and mimeType='application/vnd.google-apps.folder' and trashed=false`;

  const data = await googleGet(
    "https://www.googleapis.com/drive/v3/files",
    token,
    { q: query, spaces: "drive", fields: "files(id,name)", orderBy: "createdTime", pageSize: "1" }
  );

  if (data.files?.length > 0) return data.files[0].id;

  const folder = await googlePost("https://www.googleapis.com/drive/v3/files", token, {
    name: folderName,
    mimeType: "application/vnd.google-apps.folder",
  });
  return folder.id;
}

async function findExistingDailyDoc(token: string, folderId: string, title: string): Promise<string | null> {
  const escapedTitle = title.replace(/'/g, "\\'");
  const query = `name='${escapedTitle}' and mimeType='application/vnd.google-apps.document' and '${folderId}' in parents and trashed=false`;

  const data = await googleGet("https://www.googleapis.com/drive/v3/files", token, {
    q: query,
    spaces: "drive",
    fields: "files(id,name)",
    orderBy: "modifiedTime desc",
    pageSize: "1",
  });

  return data.files?.length > 0 ? data.files[0].id : null;
}

function formatEventTime(event: CalendarEvent): string {
  const dt = event.start?.dateTime;
  if (!dt) return event.start?.date ? "all-day" : "";
  try {
    const d = new Date(dt);
    return d.toLocaleTimeString("en-US", {
      timeZone: CONFIG.timezone,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return "";
  }
}

function buildDocText(dateStr: string, memos: MemoData[]): string {
  const parts: string[] = [];
  parts.push(`Meeting Prep Memos\n${dateStr}\n\n`);
  parts.push("TODAY'S SCHEDULE\n\n");

  for (const m of memos) {
    const timeStr = formatEventTime(m.event);
    const summary = m.event.summary || "Untitled";
    parts.push(`  ${timeStr}  ${summary}\n`);
  }
  parts.push("\n" + "=".repeat(60) + "\n\n");

  for (const m of memos) {
    parts.push(m.memoText);
    parts.push("\n\n" + "=".repeat(60) + "\n\n");
  }

  return parts.join("");
}

async function replaceGoogleDocText(token: string, docId: string, text: string): Promise<void> {
  const doc = await googleGet(`https://docs.googleapis.com/v1/documents/${docId}`, token);
  const body = doc.body?.content || [];
  const endIndex = body.length > 0 ? body[body.length - 1].endIndex || 1 : 1;

  const requests: unknown[] = [];
  if (endIndex > 1) {
    requests.push({
      deleteContentRange: { range: { startIndex: 1, endIndex: endIndex - 1 } },
    });
  }
  requests.push({ insertText: { location: { index: 1 }, text } });

  await googlePost(`https://docs.googleapis.com/v1/documents/${docId}:batchUpdate`, token, { requests });
}

async function createGoogleDoc(
  accounts: GoogleAccount[],
  dateStr: string,
  memos: MemoData[]
): Promise<{ docId: string; docUrl: string } | null> {
  const account = accounts.find((a) => a.email === CONFIG.googleDocAccount);
  if (!account?.accessToken) {
    console.error(`[DOC] No access token for ${CONFIG.googleDocAccount}`);
    return null;
  }
  const token = account.accessToken;

  const folderId = await getOrCreateDriveFolder(token, CONFIG.googleDocFolderName);
  console.log(`  Drive folder: ${CONFIG.googleDocFolderName} (${folderId})`);

  // Format date for title
  const d = new Date(dateStr + "T12:00:00");
  const titleDate = d.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
  const title = `Meeting Prep \u2014 ${titleDate}`;

  let docId: string | null = null;
  let created = false;

  if (CONFIG.reuseDailyGoogleDoc) {
    docId = await findExistingDailyDoc(token, folderId, title);
    if (docId) console.log("  Reusing existing daily Google Doc");
  }

  if (!docId) {
    const doc = await googlePost("https://docs.googleapis.com/v1/documents", token, { title });
    docId = doc.documentId;
    created = true;

    // Move to folder
    const fileMeta = await googleGet(`https://www.googleapis.com/drive/v3/files/${docId}`, token, {
      fields: "parents",
    });
    const parents = (fileMeta.parents || []).join(",");

    await fetch(
      `https://www.googleapis.com/drive/v3/files/${docId}?addParents=${folderId}${parents ? `&removeParents=${parents}` : ""}&fields=id`,
      {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: "{}",
      }
    );
  }

  const fullContent = buildDocText(titleDate, memos);
  await replaceGoogleDocText(token, docId!, fullContent);

  const docUrl = `https://docs.google.com/document/d/${docId}/edit`;
  console.log(`  ${created ? "Created" : "Updated"} Google Doc: ${docUrl}`);
  return { docId: docId!, docUrl };
}

// ── Calendar Attachment ─────────────────────────────────────────────────────

async function attachDocToEvents(
  accounts: GoogleAccount[],
  memos: MemoData[],
  docInfo: { docId: string; docUrl: string }
): Promise<void> {
  const docPrefix = `https://docs.google.com/document/d/${docInfo.docId}`;

  for (const m of memos) {
    const account = accounts.find((a) => a.email === m.event._accountEmail);
    if (!account?.accessToken) continue;
    const eventId = m.event.id;
    if (!eventId) continue;

    try {
      const currentEvent = await googleGet(
        `https://www.googleapis.com/calendar/v3/calendars/primary/events/${eventId}`,
        account.accessToken
      );

      const existing = (currentEvent.attachments || []) as Array<{ fileUrl?: string }>;
      if (existing.some((a) => a.fileUrl?.startsWith(docPrefix))) {
        console.log(`    [SKIP] Doc already attached to ${m.event.summary || ""}`);
        continue;
      }

      const newAttachment = {
        fileUrl: docInfo.docUrl,
        mimeType: "application/vnd.google-apps.document",
        title: `Meeting Prep \u2014 ${m.event.summary || "Meeting"}`,
      };

      await googlePatch(
        `https://www.googleapis.com/calendar/v3/calendars/primary/events/${eventId}`,
        account.accessToken,
        { attachments: [...existing, newAttachment] },
        { supportsAttachments: "true" }
      );
      console.log(`    Attached to: ${m.event.summary || "Unknown"}`);
    } catch (e) {
      console.error(`    [ERROR] Attaching to ${m.event.summary || ""}: ${e}`);
    }
  }
}

// ── Observability ───────────────────────────────────────────────────────────

async function recordRunStart(supabase: ReturnType<typeof createClient>, dateStr: string): Promise<number | null> {
  const { data, error } = await supabase
    .from("meeting_prep_runs")
    .insert({ run_date: dateStr, status: "running" })
    .select("id")
    .single();

  if (error) {
    console.error(`[DB] Failed to record run start: ${error.message}`);
    return null;
  }
  return data.id;
}

async function recordRunEnd(
  supabase: ReturnType<typeof createClient>,
  runId: number,
  status: string,
  meetingsFound: number,
  memosGenerated: number,
  docUrl?: string,
  errorMessage?: string
): Promise<void> {
  const { error } = await supabase
    .from("meeting_prep_runs")
    .update({
      status,
      completed_at: new Date().toISOString(),
      meetings_found: meetingsFound,
      memos_generated: memosGenerated,
      google_doc_url: docUrl || null,
      error_message: errorMessage || null,
    })
    .eq("id", runId);

  if (error) {
    console.error(`[DB] Failed to record run end: ${error.message}`);
  }
}

// ── Main Pipeline ───────────────────────────────────────────────────────────

async function runPipeline(): Promise<{
  success: boolean;
  meetingsFound: number;
  memosGenerated: number;
  docUrl?: string;
  error?: string;
}> {
  console.log("\n" + "=".repeat(60));
  console.log("  Daily Meeting Prep — Edge Function");
  console.log("=".repeat(60) + "\n");

  // 1. Load Google accounts and refresh tokens
  console.log("1. Loading Google accounts & refreshing tokens...");
  const accounts = loadGoogleAccounts();
  await refreshAllTokens(accounts);
  const activeAccounts = accounts.filter((a) => a.accessToken);
  console.log(`   ${activeAccounts.length}/${accounts.length} accounts authenticated\n`);

  if (activeAccounts.length === 0) {
    throw new Error("No Google accounts could authenticate");
  }

  // 2. Fetch calendar events
  console.log("2. Fetching calendar events...");
  const allEvents = await fetchCalendarEvents(accounts);
  console.log(`   Total: ${allEvents.length} events\n`);

  if (allEvents.length === 0) {
    console.log("No events found. Nothing to prep.");
    return { success: true, meetingsFound: 0, memosGenerated: 0 };
  }

  // 3. Filter
  console.log("3. Filtering events...");
  const { needsMemo, skipped } = classifyEvents(allEvents);
  for (const s of skipped) {
    console.log(`   [SKIP] ${s.event.summary || "Untitled"}: ${s.reason}`);
  }
  console.log(`\n   ${needsMemo.length} meetings need prep memos`);

  if (needsMemo.length === 0) {
    console.log("\nNo external meetings to prep.");
    return { success: true, meetingsFound: allEvents.length, memosGenerated: 0 };
  }

  // 4. Research attendees
  console.log("\n4. Researching attendees...");
  const supabase = getSupabaseClient();
  const meetingData: Array<{
    event: CalendarEvent;
    profiles: AttendeeProfile[];
    comms: CommsHistory;
    entityKey: string;
  }> = [];

  for (const ev of needsMemo) {
    console.log(`   Meeting: ${ev.summary || "Untitled"}`);
    const { profiles, comms } = await researchAttendees(ev, supabase);
    const entityKey = ENTITY_MAP[ev._accountEmail] || "truesteele";
    meetingData.push({ event: ev, profiles, comms, entityKey });
  }

  // 5. Generate memos
  console.log(`\n5. Generating memos with Claude Sonnet 4.6...`);
  const memos: MemoData[] = [];
  for (const md of meetingData) {
    console.log(`   Writing: ${md.event.summary || "Untitled"}...`);
    try {
      const memoText = await generateMemo(md.event, md.profiles, md.comms, md.entityKey);
      memos.push({ event: md.event, memoText });
      await new Promise((r) => setTimeout(r, 1000));
    } catch (e) {
      console.error(`   [ERROR] Memo generation failed: ${e}`);
      memos.push({ event: md.event, memoText: `[Memo generation failed: ${e}]` });
    }
  }

  // 6. Create Google Doc
  console.log("\n6. Creating Google Doc...");
  let docInfo: { docId: string; docUrl: string } | null = null;
  try {
    const { dateStr } = getTodayDateRange();
    docInfo = await createGoogleDoc(accounts, dateStr, memos);
  } catch (e) {
    console.error(`   [ERROR] Google Doc creation failed: ${e}`);
  }

  // 7. Attach to calendar events
  if (docInfo && CONFIG.attachToCalendar) {
    console.log("\n7. Attaching doc to calendar events...");
    await attachDocToEvents(accounts, memos, docInfo);
  }

  console.log("\n" + "=".repeat(60));
  console.log(`  Done! ${memos.length} memos generated.`);
  if (docInfo) console.log(`  Google Doc: ${docInfo.docUrl}`);
  console.log("=".repeat(60) + "\n");

  return {
    success: true,
    meetingsFound: allEvents.length,
    memosGenerated: memos.length,
    docUrl: docInfo?.docUrl,
  };
}

// ── HTTP Handler ────────────────────────────────────────────────────────────

Deno.serve(async (req) => {
  // Only accept POST (from pg_cron/pg_net) or manual invocation
  if (req.method === "OPTIONS") {
    return new Response("ok", {
      headers: { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, content-type" },
    });
  }

  const supabase = getSupabaseClient();
  const { dateStr } = getTodayDateRange();
  const runId = await recordRunStart(supabase, dateStr);

  try {
    const result = await runPipeline();

    if (runId) {
      await recordRunEnd(
        supabase,
        runId,
        result.success ? "success" : "error",
        result.meetingsFound,
        result.memosGenerated,
        result.docUrl,
        result.error
      );
    }

    return new Response(
      JSON.stringify({
        status: "ok",
        date: dateStr,
        meetingsFound: result.meetingsFound,
        memosGenerated: result.memosGenerated,
        docUrl: result.docUrl,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : String(err);
    console.error(`[FATAL] ${errorMessage}`);

    if (runId) {
      await recordRunEnd(supabase, runId, "error", 0, 0, undefined, errorMessage);
    }

    return new Response(
      JSON.stringify({ status: "error", error: errorMessage }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
