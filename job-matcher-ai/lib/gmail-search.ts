/**
 * Gmail-based email discovery — searches across Justin's 5 Gmail accounts
 * to find email addresses for a given person.
 *
 * Ported from scripts/intelligence/discover_emails.py
 * NOTE: Only works in local/dev mode (reads credential files from disk).
 */

import { google } from 'googleapis';
import { OAuth2Client } from 'google-auth-library';
import * as fs from 'fs';
import * as path from 'path';

const GOOGLE_ACCOUNTS = [
  'justinrsteele@gmail.com',
  'justin@truesteele.com',
  'justin@outdoorithm.com',
  'justin@outdoorithmcollective.org',
  'justin@kindora.co',
];

const CREDENTIALS_DIR = path.join(
  process.env.HOME || '/Users/Justin',
  '.google_workspace_mcp',
  'credentials'
);

const JUSTIN_EMAILS = new Set([
  'justinrsteele@gmail.com',
  'justin@truesteele.com',
  'justin@outdoorithm.com',
  'justin@outdoorithmcollective.org',
  'justin@kindora.co',
  'jsteele@google.com',
  'justinsteele@google.com',
  'justin.steele@google.com',
]);

const SKIP_PATTERNS = [
  /noreply@/i, /no-reply@/i, /notifications@/i, /notify@/i,
  /mailer-daemon@/i, /postmaster@/i, /bounce@/i,
  /@googlegroups\.com$/i, /@groups\.google\.com$/i,
  /@calendar\.google\.com$/i, /@docs\.google\.com$/i,
  /@linkedin\.com$/i, /@facebookmail\.com$/i,
];

function isSkipEmail(addr: string): boolean {
  addr = addr.toLowerCase().trim();
  if (JUSTIN_EMAILS.has(addr)) return true;
  return SKIP_PATTERNS.some(p => p.test(addr));
}

function nameMatchScore(firstName: string, lastName: string, displayName: string): number {
  if (!displayName) return 0;
  const first = firstName.toLowerCase().trim();
  const last = lastName.toLowerCase().trim();
  const display = displayName.toLowerCase().trim();

  if (`${first} ${last}` === display) return 1.0;
  if (`${last}, ${first}` === display) return 1.0;
  if (`${last} ${first}` === display) return 0.95;
  if (first && last && display.includes(first) && display.includes(last)) return 0.9;
  if (last && first && display.includes(last) && display.startsWith(first[0])) return 0.7;
  if (last && last.length > 3 && display.includes(last)) return 0.4;
  return 0;
}

function normalizeCompanyForDomain(company: string): string[] {
  if (!company) return [];
  let c = company.toLowerCase().trim();
  for (const suffix of [
    ', inc.', ', inc', ' inc.', ' inc', ', llc', ' llc',
    ', ltd', ' ltd', ' corp', ' corporation', ' co.',
    ' foundation', ' fund', ' group', ' consulting',
  ]) {
    c = c.replace(suffix, '');
  }
  c = c.trim();
  const frags = [c.replace(/ /g, ''), c.replace(/ /g, '-')];
  const parts = c.split(' ');
  if (parts.length > 1) {
    frags.push(parts[0]);
    frags.push(parts.map(p => p[0]).join(''));
  }
  return frags.filter(f => f.length > 2);
}

function parseEmailAddresses(headerValue: string): { name: string; address: string }[] {
  const results: { name: string; address: string }[] = [];
  // Handle complex header values with multiple addresses
  // Split carefully, respecting quoted strings
  const parts: string[] = [];
  let current = '';
  let inQuotes = false;
  let depth = 0;

  for (const ch of headerValue) {
    if (ch === '"') inQuotes = !inQuotes;
    if (ch === '<') depth++;
    if (ch === '>') depth--;
    if (ch === ',' && !inQuotes && depth === 0) {
      parts.push(current.trim());
      current = '';
    } else {
      current += ch;
    }
  }
  if (current.trim()) parts.push(current.trim());

  for (const part of parts) {
    const trimmed = part.trim();
    // Pattern: "Display Name" <email@domain.com> or Display Name <email@domain.com>
    const angleMatch = trimmed.match(/^(?:"?([^"<]*?)"?\s*)?<([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>$/);
    if (angleMatch) {
      results.push({
        name: (angleMatch[1] || '').trim(),
        address: (angleMatch[2] || '').toLowerCase().trim(),
      });
      continue;
    }
    // Bare email
    const bareMatch = trimmed.match(/^([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})$/);
    if (bareMatch) {
      results.push({ name: '', address: bareMatch[1].toLowerCase().trim() });
    }
  }
  return results;
}

type GmailClient = ReturnType<typeof google.gmail>;

interface GmailService {
  account: string;
  client: GmailClient;
}

function loadGmailServices(): GmailService[] {
  const services: GmailService[] = [];
  for (const account of GOOGLE_ACCOUNTS) {
    const credPath = path.join(CREDENTIALS_DIR, `${account}.json`);
    try {
      if (!fs.existsSync(credPath)) continue;
      const data = JSON.parse(fs.readFileSync(credPath, 'utf-8'));
      const oauth2 = new OAuth2Client(data.client_id, data.client_secret);
      oauth2.setCredentials({
        access_token: data.token,
        refresh_token: data.refresh_token,
        token_type: 'Bearer',
      });
      const gmail = google.gmail({ version: 'v1', auth: oauth2 });
      services.push({ account, client: gmail });
    } catch (e) {
      console.error(`Failed to load credentials for ${account}:`, e);
    }
  }
  return services;
}

export interface EmailCandidate {
  email: string;
  displayName: string;
  nameScore: number;
  threadCount: number;
  accounts: string[];
  domainMatch: boolean;
  score: number;
}

interface CandidateInfo {
  nameScore: number;
  displayName: string;
  threadCount: number;
  accounts: Set<string>;
}

export async function searchGmailForEmail(
  firstName: string,
  lastName: string,
  company?: string,
): Promise<EmailCandidate[]> {
  const services = loadGmailServices();
  if (services.length === 0) return [];

  const candidates: Record<string, CandidateInfo> = {};
  const query = `"${firstName} ${lastName}"`;

  // Search each account in parallel
  await Promise.all(
    services.map(async ({ account, client }) => {
      try {
        const res = await client.users.messages.list({
          userId: 'me',
          q: query,
          maxResults: 20,
        });

        const messages = res.data.messages || [];

        for (const msgRef of messages.slice(0, 15)) {
          try {
            const msg = await client.users.messages.get({
              userId: 'me',
              id: msgRef.id!,
              format: 'metadata',
              metadataHeaders: ['From', 'To', 'Cc'],
            });

            const headers = msg.data.payload?.headers || [];

            for (const hdr of headers) {
              const hdrName = (hdr.name || '').toLowerCase();
              if (!['from', 'to', 'cc'].includes(hdrName)) continue;

              const addrs = parseEmailAddresses(hdr.value || '');
              for (const { name: dispName, address: addr } of addrs) {
                if (!addr || isSkipEmail(addr)) continue;

                let ns = nameMatchScore(firstName, lastName, dispName);

                // Also check email local part
                if (ns < 0.4) {
                  const local = addr.split('@')[0] || '';
                  const lastLower = lastName.toLowerCase();
                  const firstChar = firstName.toLowerCase()[0] || '';
                  if (lastLower && local.includes(lastLower) && firstChar && local.includes(firstChar)) {
                    ns = Math.max(ns, 0.5);
                  } else if (lastLower && local.includes(lastLower)) {
                    ns = Math.max(ns, 0.3);
                  }
                }

                if (ns < 0.3) continue;

                if (!candidates[addr]) {
                  candidates[addr] = {
                    nameScore: ns,
                    displayName: dispName,
                    threadCount: 0,
                    accounts: new Set(),
                  };
                } else {
                  candidates[addr].nameScore = Math.max(candidates[addr].nameScore, ns);
                  if (dispName && !candidates[addr].displayName) {
                    candidates[addr].displayName = dispName;
                  }
                }

                candidates[addr].threadCount++;
                candidates[addr].accounts.add(account);
              }
            }
          } catch {
            // Skip individual message errors
          }
        }
      } catch (e) {
        console.error(`Error searching ${account}:`, e);
      }
    })
  );

  // Score and rank candidates
  const companyDomainFrags = normalizeCompanyForDomain(company || '');

  const scored: EmailCandidate[] = Object.entries(candidates).map(([addr, info]) => {
    let score = info.nameScore * 50;
    let domainMatch = false;

    const domain = addr.split('@')[1]?.toLowerCase() || '';
    for (const frag of companyDomainFrags) {
      if (domain.includes(frag)) {
        score += 30;
        domainMatch = true;
        break;
      }
    }

    score += Math.min(info.threadCount * 2, 10);
    score += Math.min(info.accounts.size * 5, 10);

    return {
      email: addr,
      displayName: info.displayName,
      nameScore: info.nameScore,
      threadCount: info.threadCount,
      accounts: Array.from(info.accounts),
      domainMatch,
      score,
    };
  });

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, 10); // Top 10 candidates
}
