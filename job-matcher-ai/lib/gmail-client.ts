/**
 * Shared Gmail OAuth client factory.
 * Reads credentials from ~/.google_workspace_mcp/credentials/
 * NOTE: Only works in Node.js runtime (needs fs access).
 */

import { google } from 'googleapis';
import { OAuth2Client } from 'google-auth-library';
import * as fs from 'fs';
import * as path from 'path';

export const GOOGLE_ACCOUNTS = [
  'justinrsteele@gmail.com',
  'justin@truesteele.com',
  'justin@outdoorithm.com',
  'justin@outdoorithmcollective.org',
  'justin@kindora.co',
] as const;

export type GoogleAccount = (typeof GOOGLE_ACCOUNTS)[number];

const CREDENTIALS_DIR = path.join(
  process.env.HOME || '/Users/Justin',
  '.google_workspace_mcp',
  'credentials'
);

export const ACCOUNT_LABELS: Record<string, { label: string; color: string }> = {
  'justinrsteele@gmail.com': { label: 'Gmail', color: 'red' },
  'justin@truesteele.com': { label: 'TrueSteele', color: 'blue' },
  'justin@outdoorithm.com': { label: 'Outdoorithm', color: 'green' },
  'justin@outdoorithmcollective.org': { label: 'OC', color: 'orange' },
  'justin@kindora.co': { label: 'Kindora', color: 'purple' },
};

export type GmailClient = ReturnType<typeof google.gmail>;

export interface GmailService {
  account: string;
  client: GmailClient;
}

export function getGmailClient(account: string): GmailClient | null {
  const credPath = path.join(CREDENTIALS_DIR, `${account}.json`);
  try {
    if (!fs.existsSync(credPath)) return null;
    const data = JSON.parse(fs.readFileSync(credPath, 'utf-8'));
    const oauth2 = new OAuth2Client(data.client_id, data.client_secret);
    oauth2.setCredentials({
      access_token: data.token,
      refresh_token: data.refresh_token,
      token_type: 'Bearer',
    });
    return google.gmail({ version: 'v1', auth: oauth2 });
  } catch (e) {
    console.error(`Failed to load credentials for ${account}:`, e);
    return null;
  }
}

export function getGmailClients(): GmailService[] {
  const services: GmailService[] = [];
  for (const account of GOOGLE_ACCOUNTS) {
    const client = getGmailClient(account);
    if (client) {
      services.push({ account, client });
    }
  }
  return services;
}
