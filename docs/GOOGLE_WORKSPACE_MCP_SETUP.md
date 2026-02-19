# Google Workspace MCP Setup Guide

This document walks through setting up Claude Code with Google Workspace (Gmail, Calendar, Drive, Docs, Sheets, etc.) in a new codebase/environment.

The integration uses [`workspace-mcp`](https://github.com/taylorwilsdon/google_workspace_mcp), an open-source MCP server that bridges Claude Code to Google Workspace APIs via OAuth 2.0.

---

## Prerequisites

- **Python 3.10+**
- **`uv`** (the Python package manager) — install via Homebrew or the official installer:
  ```bash
  # macOS
  brew install uv

  # or universal installer
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
  `uv` provides the `uvx` command used to run the MCP server. Confirm it's available:
  ```bash
  uvx --version
  ```
- **Claude Code CLI** installed and working
- **A Google account** with access to the Workspace services you need

---

## Step 1: Create a Google Cloud Project & OAuth Credentials

Each Google account you want to connect needs its own OAuth client (i.e., its own Google Cloud project, or at least its own OAuth client ID within a project). If you're connecting multiple accounts, repeat this step for each.

### 1a. Create or select a Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top -> **New Project**
3. Name it something like `Claude Workspace MCP` -> **Create**
4. Select the new project from the dropdown

### 1b. Configure the OAuth consent screen

1. Navigate to **APIs & Services -> OAuth consent screen**
2. Select **External** user type (unless you have Google Workspace admin access, in which case **Internal** works)
3. Fill in the required fields:
   - **App name**: e.g., `Claude Workspace MCP`
   - **User support email**: your email
   - **Developer contact email**: your email
4. Click **Save and Continue** through Scopes (no changes needed — scopes are requested at runtime)
5. Under **Test users**, add the Google email address you'll be authenticating with
6. **Save and Continue** -> **Back to Dashboard**

> **Important**: While the app is in "Testing" mode, only the test users you add can authenticate. This is fine for personal/developer use.

### 1c. Create OAuth 2.0 credentials

1. Navigate to **APIs & Services -> Credentials**
2. Click **+ Create Credentials -> OAuth client ID**
3. Application type: **Desktop application**
4. Name: e.g., `Claude MCP Desktop`
5. Click **Create**
6. **Copy the Client ID and Client Secret** — you'll need these in Step 3
7. Optionally, click **Download JSON** to save the credential file as a backup (store it in your project's `docs/` directory, named like `client_secret_<client-id>.json`)

### 1d. Enable the required Google APIs

Enable each API your workflow needs. Below are the direct enable links — click each one (make sure your correct project is selected):

| Service | Enable Link |
|---------|-------------|
| **Gmail** | [Enable Gmail API](https://console.cloud.google.com/flows/enableapi?apiid=gmail.googleapis.com) |
| **Calendar** | [Enable Calendar API](https://console.cloud.google.com/flows/enableapi?apiid=calendar-json.googleapis.com) |
| **Drive** | [Enable Drive API](https://console.cloud.google.com/flows/enableapi?apiid=drive.googleapis.com) |
| **Docs** | [Enable Docs API](https://console.cloud.google.com/flows/enableapi?apiid=docs.googleapis.com) |
| **Sheets** | [Enable Sheets API](https://console.cloud.google.com/flows/enableapi?apiid=sheets.googleapis.com) |
| **Slides** | [Enable Slides API](https://console.cloud.google.com/flows/enableapi?apiid=slides.googleapis.com) |
| **Forms** | [Enable Forms API](https://console.cloud.google.com/flows/enableapi?apiid=forms.googleapis.com) |
| **Tasks** | [Enable Tasks API](https://console.cloud.google.com/flows/enableapi?apiid=tasks.googleapis.com) |
| **People (Contacts)** | [Enable People API](https://console.cloud.google.com/flows/enableapi?apiid=people.googleapis.com) |
| **Chat** | [Enable Chat API](https://console.cloud.google.com/flows/enableapi?apiid=chat.googleapis.com) |
| **Apps Script** | [Enable Apps Script API](https://console.cloud.google.com/flows/enableapi?apiid=script.googleapis.com) |
| **Custom Search** | [Enable Custom Search API](https://console.cloud.google.com/flows/enableapi?apiid=customsearch.googleapis.com) |

**At minimum, enable Gmail, Calendar, Drive, and Docs.** Enable others based on your needs.

---

## Step 2: Create the `.mcp.json` file

In the **root of your project directory**, create a file named `.mcp.json`. This tells Claude Code how to launch and configure the MCP server.

### Single Google account

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uvx",
      "args": ["workspace-mcp", "--tool-tier", "complete"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "<your-client-id>.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "GOCSPX-<your-secret>",
        "USER_GOOGLE_EMAIL": "you@example.com",
        "OAUTHLIB_INSECURE_TRANSPORT": "1"
      }
    }
  }
}
```

### Multiple Google accounts

Add a separate server entry for each account with a unique key name:

```json
{
  "mcpServers": {
    "google-workspace-personal": {
      "command": "uvx",
      "args": ["workspace-mcp", "--tool-tier", "complete"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "<personal-client-id>.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "GOCSPX-<personal-secret>",
        "USER_GOOGLE_EMAIL": "you@gmail.com",
        "OAUTHLIB_INSECURE_TRANSPORT": "1"
      }
    },
    "google-workspace-work": {
      "command": "uvx",
      "args": ["workspace-mcp", "--tool-tier", "complete"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "<work-client-id>.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "GOCSPX-<work-secret>",
        "USER_GOOGLE_EMAIL": "you@yourcompany.com",
        "OAUTHLIB_INSECURE_TRANSPORT": "1"
      }
    }
  }
}
```

### Configuration reference

| Field | Description |
|-------|-------------|
| `command` | Always `"uvx"` — runs the MCP server via uv |
| `args` | `["workspace-mcp", "--tool-tier", "complete"]` gives access to all tools. See tool tier options below. |
| `GOOGLE_OAUTH_CLIENT_ID` | The Client ID from Step 1c |
| `GOOGLE_OAUTH_CLIENT_SECRET` | The Client Secret from Step 1c |
| `USER_GOOGLE_EMAIL` | The Google email address to authenticate |
| `OAUTHLIB_INSECURE_TRANSPORT` | Set to `"1"` for local development (allows OAuth over HTTP localhost callbacks). **Do not use in production.** |

### Tool tier options

- `--tool-tier core` — Gmail, Drive, Calendar
- `--tool-tier extended` — Core + Docs, Sheets, Slides
- `--tool-tier complete` — All services (Gmail, Drive, Calendar, Docs, Sheets, Slides, Chat, Forms, Tasks, Contacts, Search, Apps Script)

### Selecting specific services only

Instead of `--tool-tier`, you can pick individual services:
```json
"args": ["workspace-mcp", "--tools", "gmail", "calendar", "drive"]
```

---

## Step 3: Authenticate (First Run)

1. Open Claude Code in the project directory containing your `.mcp.json`
2. Claude Code will automatically detect and start the MCP server(s)
3. On first use of any Google Workspace tool, the server will need OAuth authentication
4. You can trigger this by asking Claude to call `start_google_auth` for the relevant server, or by asking it to use any Google Workspace tool (e.g., "List my calendar events")
5. The MCP tool will provide an OAuth consent URL — open it in your browser
6. Sign in with the Google account matching `USER_GOOGLE_EMAIL` and grant the requested permissions
7. After approval, the browser will redirect to `http://localhost:8000/oauth2callback` — the server captures the token

### Known issue: Callback server reliability

The `start_google_auth` MCP tool starts a temporary HTTP server on port 8000 to receive the OAuth callback. **This server frequently exits before the user finishes the consent screen**, causing an `ERR_CONNECTION_REFUSED` error in the browser after granting permissions.

**Workaround: Standalone callback server**

If the built-in callback server dies before you complete consent, have Claude run a standalone Python callback server that stays alive long enough:

1. Ask Claude to call `start_google_auth` to get the auth URL (the built-in callback server may die — that's OK)
2. Ask Claude to run a standalone Python HTTP server on port 8000 that:
   - Listens for the OAuth callback at `/oauth2callback`
   - Extracts the authorization code from the query string
   - Exchanges it for tokens via Google's token endpoint
   - Saves credentials to `~/.google_workspace_mcp/credentials/<email>.json`
3. Open the auth URL in your browser and complete consent at your own pace
4. The standalone server catches the callback and saves credentials

A full implementation of this server is documented in the project's `CLAUDE.md` file. Claude Code knows to use this pattern automatically when auth is needed.

**Quick-retry method**: If you're fast, you can sometimes complete the OAuth consent before the built-in server dies. Just click the link immediately and approve quickly. If the redirect fails, retry the `start_google_auth` call and try again.

### OAuth token storage

Tokens are cached at:
```
~/.google_workspace_mcp/credentials/<email>.json
```

For example: `~/.google_workspace_mcp/credentials/you@gmail.com.json`

Once credentials are stored, you won't need to re-authenticate unless tokens expire or are revoked. The MCP server automatically loads credentials from this path on startup.

---

## Step 4: Verify the Connection

Once authenticated, test the integration by asking Claude to perform a simple action:

```
"What's on my calendar today?"
"Show me my 5 most recent emails"
"List files in my Google Drive root"
```

If it works, you're all set.

### Using tools with the correct account

When using multiple accounts, each server gets its own prefixed tools:
- `mcp__google-workspace-personal__search_gmail_messages`
- `mcp__google-workspace-work__search_gmail_messages`

Tell Claude which account to use, and it will call the corresponding prefixed tool. When calling any MCP tool, Claude should always pass the matching `user_google_email` parameter for the server being used.

---

## Step 5: Set Up CLAUDE.md (Recommended)

Create a `CLAUDE.md` file in your project root to give Claude Code persistent context about your setup. This is especially important for multi-account setups and includes troubleshooting procedures that Claude can follow autonomously.

A well-configured `CLAUDE.md` should include:
- A table of your configured accounts (server name, email, tool prefix)
- The credential storage path (`~/.google_workspace_mcp/credentials/<email>.json`)
- The programmatic token refresh script (so Claude can fix expired tokens without browser re-auth)
- The standalone OAuth callback server code (so Claude can handle fresh auth reliably)
- Troubleshooting steps for common issues (port conflicts, missing scopes, etc.)

See this project's `CLAUDE.md` for a complete working example.

---

## Troubleshooting

### "MCP server failed to start"

- Confirm `uvx` is installed and on your PATH: `which uvx`
- Confirm Python 3.10+: `python3 --version`
- Try running the server manually to see errors:
  ```bash
  GOOGLE_OAUTH_CLIENT_ID="your-id" \
  GOOGLE_OAUTH_CLIENT_SECRET="your-secret" \
  USER_GOOGLE_EMAIL="you@example.com" \
  OAUTHLIB_INSECURE_TRANSPORT=1 \
  uvx workspace-mcp --tool-tier complete
  ```

### "OAuth error: access_denied"

- Make sure the authenticating email is listed as a **Test user** in the OAuth consent screen (Step 1b)
- Make sure you're signing into the correct Google account in the browser

### "API not enabled" errors

- Go back to Step 1d and enable the specific API that's failing
- It can take a few minutes for newly enabled APIs to propagate

### Token expired (automatic refresh)

Tokens expire after ~1 hour but can be refreshed programmatically using the `refresh_token` stored in the credential file. You don't need to re-do the browser flow.

To refresh manually:
```python
import json, urllib.request, urllib.parse, ssl
from datetime import datetime, timedelta, timezone

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

cred_path = "/path/to/.google_workspace_mcp/credentials/<EMAIL>.json"
with open(cred_path) as f:
    creds = json.load(f)

data = urllib.parse.urlencode({
    "client_id": "<CLIENT_ID from .mcp.json>",
    "client_secret": "<CLIENT_SECRET from .mcp.json>",
    "refresh_token": creds["refresh_token"],
    "grant_type": "refresh_token"
}).encode()

req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
resp = urllib.request.urlopen(req, context=ctx)
result = json.loads(resp.read())

if "token" in creds:
    creds["token"] = result["access_token"]
if "access_token" in creds:
    creds["access_token"] = result["access_token"]

expiry = datetime.now(timezone.utc) + timedelta(seconds=result["expires_in"])
creds["expiry"] = expiry.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

with open(cred_path, "w") as f:
    json.dump(creds, f, indent=2)
```

If the refresh fails with `invalid_grant`, the refresh token has been revoked. Delete the credential file and re-authenticate from scratch (Step 3).

### Token re-authentication needed

If a credential file is missing or the refresh token is revoked:
1. Delete the old credential file if it exists:
   ```bash
   rm ~/.google_workspace_mcp/credentials/<EMAIL>.json
   ```
2. Follow Step 3 again to re-authenticate via the browser

### Missing scopes

If Gmail works but Calendar/Docs/etc. don't, the token was originally created with limited scopes. Delete the credential file and re-auth with full scopes:
```bash
rm ~/.google_workspace_mcp/credentials/<EMAIL>.json
```
Then trigger any tool call for that account — it will prompt for full re-auth.

### Port 8000 conflict

The OAuth callback server uses port 8000. If authentication fails because the port is in use:
1. Check what's on the port:
   ```bash
   lsof -i :8000
   ```
2. Kill the blocking process if safe:
   ```bash
   kill <PID>
   ```
3. Retry the auth flow

### Multiple accounts: wrong account responding

- Each server entry in `.mcp.json` has its own key name (e.g., `google-workspace-personal` vs `google-workspace-work`). When asking Claude to use a specific account, reference the server by name or specify which email to use.
- The tools for each account will be prefixed with the server name, e.g., `mcp__google-workspace-personal__search_gmail_messages` vs `mcp__google-workspace-work__search_gmail_messages`.

### Batch API rate limits

When making many concurrent API calls (e.g., fetching multiple emails), you may hit Google's rate limits (HTTP 429 errors). If this happens, reduce concurrency or add delays between requests. Some batch MCP tools (like `get_gmail_messages_content_batch`) may fail with validation errors for certain accounts — fall back to individual calls if needed.

---

## Adding a New Account

1. Create a Google Cloud project (or reuse an existing one) and get OAuth client credentials (Client ID + Secret) per Step 1
2. Ensure the user email is listed as a **test user** in the OAuth consent screen
3. Enable required APIs (Gmail, Calendar, Drive, Docs at minimum) in the Google Cloud project
4. Add a new entry to `.mcp.json` with a unique server name and the new credentials
5. Restart Claude Code (or restart MCP servers with `/mcp`) so the new server is detected
6. Trigger any tool call to initiate OAuth — or ask Claude to call `start_google_auth` for the new server

---

## Security Notes

- **Never commit `.mcp.json` to a public repository** — it contains OAuth client secrets. Add it to `.gitignore`:
  ```
  .mcp.json
  ```
- Also consider gitignoring `docs/client_secret_*.json` if you store downloaded credential files there.
- The `OAUTHLIB_INSECURE_TRANSPORT=1` flag is for local development only. It allows the OAuth callback over plain HTTP (localhost). This is standard for desktop OAuth flows but should not be used in deployed/production server environments.
- OAuth client secrets for "Desktop application" type clients are not truly secret (Google documents this), but it's still best practice to keep them private.
- The OAuth tokens (stored in `~/.google_workspace_mcp/credentials/`) grant access to your Google account data. Treat credential caches with the same care as passwords.

---

## Project File Reference

| File | Description |
|------|-------------|
| `.mcp.json` | MCP server config with OAuth credentials (gitignored) |
| `.gitignore` | Excludes `.mcp.json` from version control |
| `CLAUDE.md` | Claude Code project instructions — troubleshooting, auth flows, account table |
| `docs/GOOGLE_WORKSPACE_MCP_SETUP.md` | This setup guide |
| `docs/client_secret_*.json` | Downloaded OAuth client credential files from Google Cloud Console (backups) |
| `~/.google_workspace_mcp/credentials/<email>.json` | Cached OAuth tokens per account (created during auth) |

---

## Quick-Start Checklist

- [ ] `uv` / `uvx` installed (`brew install uv`)
- [ ] Google Cloud project created
- [ ] OAuth consent screen configured with test user(s) added
- [ ] OAuth 2.0 Desktop client credentials created (Client ID + Secret)
- [ ] Required Google APIs enabled (at minimum: Gmail, Calendar, Drive, Docs)
- [ ] `.mcp.json` created in project root with correct credentials
- [ ] `.mcp.json` added to `.gitignore`
- [ ] Claude Code opened in the project — MCP server starts automatically
- [ ] First OAuth consent completed in browser
- [ ] Credentials saved to `~/.google_workspace_mcp/credentials/<email>.json`
- [ ] Test query works ("What's on my calendar today?")
- [ ] `CLAUDE.md` created with account table and troubleshooting procedures
