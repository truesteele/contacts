/**
 * Shared Gmail OAuth client factory.
 *
 * Production (Vercel): reads credentials from GOOGLE_OAUTH_CREDENTIALS env var.
 * Local dev: falls back to ~/.google_workspace_mcp/credentials/ files.
 *
 * Only refresh_token + client_id + client_secret are needed — the
 * google-auth-library handles access_token refresh automatically.
 */

import { google } from 'googleapis';
import { OAuth2Client } from 'google-auth-library';

export const GOOGLE_ACCOUNTS = [
  'justinrsteele@gmail.com',
  'justin@truesteele.com',
  'justin@outdoorithm.com',
  'justin@outdoorithmcollective.org',
  'justin@kindora.co',
] as const;

export type GoogleAccount = (typeof GOOGLE_ACCOUNTS)[number];

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

interface AccountCredentials {
  client_id: string;
  client_secret: string;
  refresh_token: string;
}

let _credentialsCache: Record<string, AccountCredentials> | null = null;

function loadCredentials(): Record<string, AccountCredentials> {
  // Production: parse from env var
  const envCreds = process.env.GOOGLE_OAUTH_CREDENTIALS;
  if (envCreds) {
    return JSON.parse(envCreds);
  }

  // Local dev: read from credential files on disk
  // Dynamic require so fs/path aren't bundled for production
  const fs = require('fs') as typeof import('fs');
  const path = require('path') as typeof import('path');
  const dir = path.join(
    process.env.HOME || '/Users/Justin',
    '.google_workspace_mcp',
    'credentials'
  );

  const creds: Record<string, AccountCredentials> = {};
  for (const account of GOOGLE_ACCOUNTS) {
    const credPath = path.join(dir, `${account}.json`);
    try {
      if (fs.existsSync(credPath)) {
        const data = JSON.parse(fs.readFileSync(credPath, 'utf-8'));
        creds[account] = {
          client_id: data.client_id,
          client_secret: data.client_secret,
          refresh_token: data.refresh_token,
        };
      }
    } catch (e) {
      console.error(`Failed to load credentials for ${account}:`, e);
    }
  }
  return creds;
}

function getCredentials(): Record<string, AccountCredentials> {
  if (!_credentialsCache) {
    _credentialsCache = loadCredentials();
  }
  return _credentialsCache;
}

export function getGmailClient(account: string): GmailClient | null {
  const creds = getCredentials();
  const data = creds[account];
  if (!data) return null;

  try {
    const oauth2 = new OAuth2Client(data.client_id, data.client_secret);
    oauth2.setCredentials({
      refresh_token: data.refresh_token,
    });
    return google.gmail({ version: 'v1', auth: oauth2 });
  } catch (e) {
    console.error(`Failed to create Gmail client for ${account}:`, e);
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
