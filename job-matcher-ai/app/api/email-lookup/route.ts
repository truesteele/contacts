import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';
import { searchGmailForEmail, type EmailCandidate } from '@/lib/gmail-search';
import OpenAI from 'openai';

const openai = new OpenAI({ apiKey: process.env.OPENAI_APIKEY });

const TOMBA_API_KEY = process.env.TOMBA_API_KEY || '';
const TOMBA_SECRET_KEY = process.env.TOMBA_SECRET_KEY || '';
const TOMBA_BASE = 'https://api.tomba.io/v1';

function normalizeLinkedInUrl(url: string): string[] {
  let cleaned = url.trim();
  cleaned = cleaned.split('?')[0].split('#')[0];
  cleaned = cleaned.replace(/\/+$/, '');
  cleaned = cleaned.replace(/^http:\/\//, 'https://');
  if (!cleaned.startsWith('https://')) {
    cleaned = 'https://' + cleaned;
  }

  const variations: string[] = [];
  const withoutProtocol = cleaned.replace('https://', '');

  const wwwVariant = withoutProtocol.startsWith('www.')
    ? withoutProtocol
    : 'www.' + withoutProtocol;
  const noWwwVariant = withoutProtocol.startsWith('www.')
    ? withoutProtocol.replace('www.', '')
    : withoutProtocol;

  for (const variant of [wwwVariant, noWwwVariant]) {
    variations.push('https://' + variant);
    variations.push('https://' + variant + '/');
    variations.push('http://' + variant);
    variations.push('http://' + variant + '/');
  }

  return [...new Set(variations)];
}

/** Build a canonical https://www.linkedin.com/in/slug URL for Tomba */
function canonicalLinkedInUrl(url: string): string {
  let cleaned = url.trim().split('?')[0].split('#')[0].replace(/\/+$/, '');
  if (!cleaned.startsWith('http')) cleaned = 'https://' + cleaned;
  cleaned = cleaned.replace('://linkedin.com/', '://www.linkedin.com/');
  cleaned = cleaned.replace('http://', 'https://');
  return cleaned;
}

interface ContactRecord {
  id: number;
  first_name: string;
  last_name: string;
  email: string | null;
  work_email: string | null;
  personal_email: string | null;
  email_2: string | null;
  company: string | null;
  position: string | null;
  headline: string | null;
  linkedin_url: string | null;
  enrich_current_company: string | null;
  enrich_current_title: string | null;
  enrich_profile_pic_url: string | null;
}

interface EmailResult {
  email: string;
  source: 'database' | 'gmail' | 'tomba';
  type: string;
  confidence: number;
  details?: string;
}

interface VerifyResult {
  is_match: boolean;
  confidence: number;
  reasoning: string;
  email_type: string;
}

// ── LLM verification for Gmail candidates ──────────────────────────

async function verifyEmailWithLLM(
  contact: ContactRecord,
  candidate: EmailCandidate,
): Promise<VerifyResult | null> {
  const name = `${contact.first_name} ${contact.last_name}`.trim();
  const company = contact.company || contact.enrich_current_company || '?';
  const title = contact.position || contact.enrich_current_title || '?';

  const prompt = `Verify if this email address belongs to this person.

PERSON:
  Name: ${name}
  Current company: ${company}
  Title: ${title}
  Headline: ${contact.headline || '?'}
  LinkedIn: ${contact.linkedin_url || '?'}

CANDIDATE EMAIL: ${candidate.email}
  Display name in email headers: ${candidate.displayName}
  Found in ${candidate.threadCount} email threads
  Found across ${candidate.accounts.length} Gmail account(s)
  Name match score: ${Math.round(candidate.nameScore * 100)}%
  Domain matches current company: ${candidate.domainMatch}

RULES:
1. If the name is distinctive/uncommon AND the display name matches well, accept it.
2. If the email is a COMPANY/WORK domain, REJECT if domain doesn't match current company (old work emails are stale).
3. Be strict for common names (Michael Walker, David Lee, John Smith) — need domain match or multiple threads.
4. Personal emails (gmail, yahoo, hotmail, outlook, icloud, protonmail) are always acceptable if name match is strong.

Respond in JSON format: { "is_match": boolean, "confidence": number (0-100), "reasoning": "string", "email_type": "personal" | "work" | "unknown" }`;

  try {
    const resp = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'system',
          content: 'You verify email address matches. Respond only with valid JSON.',
        },
        { role: 'user', content: prompt },
      ],
      response_format: { type: 'json_object' },
      temperature: 0.1,
    });

    const content = resp.choices[0]?.message?.content;
    if (!content) return null;
    return JSON.parse(content) as VerifyResult;
  } catch (e) {
    console.error('LLM verification error:', e);
    return null;
  }
}

// ── Tomba email lookup ─────────────────────────────────────────────

interface TombaLinkedInResult {
  email: string;
  type: string; // "personal" | "generic" | "work"
  confidence: number;
  first_name?: string;
  last_name?: string;
  company?: string;
  position?: string;
}

async function tombaLinkedInLookup(linkedinUrl: string): Promise<TombaLinkedInResult | null> {
  if (!TOMBA_API_KEY || !TOMBA_SECRET_KEY) {
    console.log('Tomba: API keys not configured, skipping');
    return null;
  }

  const url = `${TOMBA_BASE}/linkedin?url=${encodeURIComponent(linkedinUrl)}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'X-Tomba-Key': TOMBA_API_KEY,
        'X-Tomba-Secret': TOMBA_SECRET_KEY,
        'Content-Type': 'application/json',
      },
    });

    if (!res.ok) {
      const text = await res.text();
      console.error(`Tomba LinkedIn lookup failed (${res.status}):`, text);
      return null;
    }

    const data = await res.json();
    const d = data?.data;
    if (!d?.email) return null;

    return {
      email: d.email,
      type: d.type || 'unknown',
      confidence: d.score ?? d.confidence ?? 80,
      first_name: d.first_name,
      last_name: d.last_name,
      company: d.company,
      position: d.position,
    };
  } catch (e) {
    console.error('Tomba LinkedIn lookup error:', e);
    return null;
  }
}

async function tombaEmailFinder(
  firstName: string,
  lastName: string,
  domain: string,
): Promise<TombaLinkedInResult | null> {
  if (!TOMBA_API_KEY || !TOMBA_SECRET_KEY) return null;
  if (!domain) return null;

  const url = `${TOMBA_BASE}/email-finder?domain=${encodeURIComponent(domain)}&first_name=${encodeURIComponent(firstName)}&last_name=${encodeURIComponent(lastName)}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'X-Tomba-Key': TOMBA_API_KEY,
        'X-Tomba-Secret': TOMBA_SECRET_KEY,
        'Content-Type': 'application/json',
      },
    });

    if (!res.ok) return null;

    const data = await res.json();
    const d = data?.data;
    if (!d?.email) return null;

    return {
      email: d.email,
      type: d.type || 'work',
      confidence: d.score ?? d.confidence ?? 70,
      first_name: d.first_name,
      last_name: d.last_name,
      company: d.company,
      position: d.position,
    };
  } catch (e) {
    console.error('Tomba email-finder error:', e);
    return null;
  }
}

async function tombaVerifyEmail(email: string): Promise<boolean> {
  if (!TOMBA_API_KEY || !TOMBA_SECRET_KEY) return true; // skip verification if no keys

  try {
    const res = await fetch(`${TOMBA_BASE}/email-verifier/${encodeURIComponent(email)}`, {
      method: 'GET',
      headers: {
        'X-Tomba-Key': TOMBA_API_KEY,
        'X-Tomba-Secret': TOMBA_SECRET_KEY,
      },
    });

    if (!res.ok) return true; // assume valid if verification fails

    const data = await res.json();
    const result = data?.data?.email?.result;
    // Accept deliverable and risky, reject undeliverable
    return result !== 'undeliverable';
  } catch {
    return true;
  }
}

// ── Helper to build contact info for response ──────────────────────

function contactInfo(contact: ContactRecord | null, tombaResult?: TombaLinkedInResult | null) {
  if (contact) {
    return {
      name: `${contact.first_name} ${contact.last_name}`.trim(),
      company: contact.company || contact.enrich_current_company,
      title: contact.position || contact.enrich_current_title,
      headline: contact.headline,
      linkedin_url: contact.linkedin_url,
      profile_pic: contact.enrich_profile_pic_url,
    };
  }
  // If no DB contact, use Tomba data for display
  if (tombaResult) {
    return {
      name: `${tombaResult.first_name || ''} ${tombaResult.last_name || ''}`.trim() || null,
      company: tombaResult.company || null,
      title: tombaResult.position || null,
      headline: null,
      linkedin_url: null,
      profile_pic: null,
    };
  }
  return null;
}

// ── Company domain extraction ──────────────────────────────────────

function extractCompanyDomain(company: string): string | null {
  if (!company) return null;
  // Simple heuristic: lowercase, remove suffixes, add .com
  let c = company.toLowerCase().trim();
  for (const suffix of [
    ', inc.', ', inc', ' inc.', ' inc', ', llc', ' llc',
    ', ltd', ' ltd', ' corp', ' corporation',
  ]) {
    c = c.replace(suffix, '');
  }
  c = c.trim().replace(/\s+/g, '');
  if (c.length < 2) return null;
  return c + '.com';
}

// ── Main handler ───────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const linkedinUrl: string = body.linkedin_url;

    if (!linkedinUrl) {
      return NextResponse.json({ error: 'linkedin_url is required' }, { status: 400 });
    }

    const urlVariations = normalizeLinkedInUrl(linkedinUrl);
    const canonical = canonicalLinkedInUrl(linkedinUrl);

    // ── Step 1: DB lookup ──────────────────────────────────────────

    const selectCols =
      'id, first_name, last_name, email, work_email, personal_email, email_2, ' +
      'company, position, headline, linkedin_url, enrich_current_company, ' +
      'enrich_current_title, enrich_profile_pic_url';

    let contact: ContactRecord | null = null;

    for (const variation of urlVariations) {
      const { data } = await supabase
        .from('contacts')
        .select(selectCols)
        .eq('linkedin_url', variation)
        .limit(1);

      if (data && data.length > 0) {
        contact = data[0] as unknown as ContactRecord;
        break;
      }
    }

    // Try ilike match on slug
    if (!contact) {
      const slugMatch = linkedinUrl.match(/linkedin\.com\/in\/([^/?#]+)/i);
      if (slugMatch) {
        const slug = slugMatch[1].toLowerCase();
        const { data } = await supabase
          .from('contacts')
          .select(selectCols)
          .ilike('linkedin_url', `%/in/${slug}%`)
          .limit(1);

        if (data && data.length > 0) {
          contact = data[0] as unknown as ContactRecord;
        }
      }
    }

    // Collect existing emails from DB
    const dbEmails: EmailResult[] = [];
    if (contact) {
      const emailFields = [
        { field: 'email', type: 'primary' },
        { field: 'work_email', type: 'work' },
        { field: 'personal_email', type: 'personal' },
        { field: 'email_2', type: 'secondary' },
      ] as const;

      for (const { field, type } of emailFields) {
        const val = contact[field];
        if (val && typeof val === 'string' && val.includes('@')) {
          dbEmails.push({ email: val, source: 'database', type, confidence: 100 });
        }
      }
    }

    // If DB has emails, return immediately
    if (dbEmails.length > 0) {
      return NextResponse.json({
        contact: contactInfo(contact),
        emails: dbEmails,
        gmail_searched: false,
        tomba_searched: false,
        in_database: true,
      });
    }

    // ── Step 2: Gmail search (only if contact in DB with name) ─────

    let gmailEmails: EmailResult[] = [];
    let gmailSearched = false;
    let gmailCandidatesCount = 0;

    if (contact?.first_name && contact?.last_name) {
      const company = contact.company || contact.enrich_current_company || '';
      const gmailCandidates = await searchGmailForEmail(
        contact.first_name,
        contact.last_name,
        company,
      );
      gmailSearched = true;
      gmailCandidatesCount = gmailCandidates.length;

      for (const candidate of gmailCandidates.slice(0, 3)) {
        const verification = await verifyEmailWithLLM(contact, candidate);
        if (verification && verification.is_match && verification.confidence >= 70) {
          gmailEmails.push({
            email: candidate.email,
            source: 'gmail',
            type: verification.email_type,
            confidence: verification.confidence,
            details: verification.reasoning,
          });
        }
      }
    }

    // If Gmail found emails, return
    if (gmailEmails.length > 0) {
      return NextResponse.json({
        contact: contactInfo(contact),
        emails: gmailEmails,
        gmail_searched: true,
        tomba_searched: false,
        in_database: !!contact,
        gmail_candidates_found: gmailCandidatesCount,
      });
    }

    // ── Step 3: Tomba LinkedIn email finder ────────────────────────

    const tombaEmails: EmailResult[] = [];
    let tombaSearched = false;

    // 3a: LinkedIn URL lookup
    const tombaResult = await tombaLinkedInLookup(canonical);
    tombaSearched = true;

    if (tombaResult) {
      // Verify low-confidence results
      let verified = true;
      if (tombaResult.confidence < 90) {
        verified = await tombaVerifyEmail(tombaResult.email);
      }

      if (verified) {
        tombaEmails.push({
          email: tombaResult.email,
          source: 'tomba',
          type: tombaResult.type === 'personal' ? 'personal' : tombaResult.type === 'generic' ? 'generic' : 'work',
          confidence: tombaResult.confidence,
          details: `Found via Tomba LinkedIn lookup${tombaResult.confidence < 90 ? ' (verified deliverable)' : ''}`,
        });
      }
    }

    // 3b: Name + domain finder (if LinkedIn lookup failed and we have name + company)
    if (tombaEmails.length === 0) {
      const firstName = contact?.first_name || tombaResult?.first_name;
      const lastName = contact?.last_name || tombaResult?.last_name;
      const company = contact?.company || contact?.enrich_current_company || tombaResult?.company;

      if (firstName && lastName && company) {
        const domain = extractCompanyDomain(company);
        if (domain) {
          const finderResult = await tombaEmailFinder(firstName, lastName, domain);
          if (finderResult) {
            let verified = true;
            if (finderResult.confidence < 90) {
              verified = await tombaVerifyEmail(finderResult.email);
            }
            if (verified) {
              tombaEmails.push({
                email: finderResult.email,
                source: 'tomba',
                type: 'work',
                confidence: finderResult.confidence,
                details: `Found via Tomba name+domain lookup (${domain})${finderResult.confidence < 90 ? ' (verified deliverable)' : ''}`,
              });
            }
          }
        }
      }
    }

    return NextResponse.json({
      contact: contactInfo(contact, tombaResult),
      emails: tombaEmails,
      gmail_searched: gmailSearched,
      tomba_searched: tombaSearched,
      in_database: !!contact,
      gmail_candidates_found: gmailCandidatesCount,
    });
  } catch (error) {
    console.error('Email lookup error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 },
    );
  }
}
