# TrueSteele Contacts — CLAUDE.md

## API Rate Limits

### OpenAI (Tier 5)
- **GPT-5 mini:** 10,000 RPM, temperature must use default (does NOT support temperature=0)
- **text-embedding-3-small:** 10,000 RPM
- **Optimal concurrent workers:** 150 (yields ~9,000 RPM with ~1s latency per call, leaving headroom)
- GPT-5 mini does NOT support temperature=0 — use default only

### OpenFEC API
- **Rate limit:** 1,000 requests/hour (hard cap, key-based)
- **Script target:** 950 req/hr (5% headroom)
- **API key:** in `.env` as `FEC_API_KEY`

### 411.com (web scraping — no official API)
- **No documented rate limit** — self-imposed politeness delays
- **Current settings:** MIN_DELAY=2s, MAX_DELAY=5s between requests per session
- **Tested safe concurrency:** 5 workers (each with own curl_cffi session/TLS fingerprint), 0 rate-limit errors across 100+ contacts
- **Risk:** No API key, scraping target — being too aggressive could trigger IP ban
- **Fallback:** Apify `one-api/skip-trace` ($0.007/result) if 411.com blocks

### Apify (Starter Plan, $29/mo)
- **Max concurrent runs:** 32
- **Actors used:** `one-api/skip-trace` ($0.007), `maxcopell/zillow-detail-scraper` (~$0.003)

### Zillow Autocomplete
- **Rate limit:** None observed (free, no API key)
- **Endpoint:** `https://www.zillowstatic.com/autocomplete/v3/suggestions`

### Supabase
- **No hard rate limit** for direct PostgreSQL access
- **Pagination:** Use `.range(offset, offset + page_size - 1)` for >1000 rows

## Script Concurrency Defaults

| Script | Workers | Notes |
|--------|---------|-------|
| `tag_contacts_gpt5m.py` | 150 | GPT-5 mini structured output |
| `score_overlap.py` | 150 | GPT-5 mini structured output |
| `score_ask_readiness.py` | 150 | GPT-5 mini structured output |
| `generate_embeddings.py` | 150 | text-embedding-3-small |
| `enrich_real_estate.py` (GPT prep) | 50 | Pre-step, runs once |
| `enrich_real_estate.py` (411 workers) | 10 | Web scraping, each with own session |
| `enrich_fec_donations.py` | 4 | Hard-capped by FEC API at 1,000/hr |

All scripts accept `--workers N` flag to override defaults.

## Vercel Deployment
- **Project:** `true-steele/contacts` (https://vercel.com/true-steele/contacts)
- **Vercel account:** `justin-outdoorithm` (NOT `justin-kindora`)
- **Deploy command:** `cd /Users/Justin/Code/TrueSteele/contacts/job-matcher-ai && npx vercel --prod --yes`

### Pre-deploy checklist
1. **Verify account:** Run `npx vercel whoami` — must show `justin-outdoorithm`
2. **If wrong account:** Switch with vercelgate by editing the auth.json token:
   - Config path: `/Users/Justin/Library/Application Support/com.vercel.cli/auth.json`
   - Tokens stored in `~/Library/Application Support/com.vercel.cli/auth.json` (see memory notes for values)
   - (Interactive `vercelgate switch` doesn't work in non-interactive shells)
3. **Verify project link:** `cat job-matcher-ai/.vercel/project.json` should show `"projectName":"contacts"` under `true-steele`
4. **If wrong project:** Re-link: `cd job-matcher-ai && rm -rf .vercel && npx vercel link --yes --project contacts --scope true-steele`

## Google Workspace MCP — Token Refresh (No Browser)

When a Google Workspace MCP server fails to load (tools missing from deferred list), refresh the token programmatically:

1. **Identify the account** from `.mcp.json` — get `USER_GOOGLE_EMAIL`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
2. **Read the credential file:** `~/.google_workspace_mcp/credentials/{email}.json` — get the `refresh_token`
3. **POST to Google OAuth2:**
```bash
curl -s -X POST "https://oauth2.googleapis.com/token" \
  --data-urlencode "grant_type=refresh_token" \
  --data-urlencode "refresh_token=REFRESH_TOKEN_HERE" \
  --data-urlencode "client_id=CLIENT_ID_HERE" \
  --data-urlencode "client_secret=CLIENT_SECRET_HERE"
```
4. **Update the credential file** with the new `access_token` and `expiry` (now + `expires_in` seconds)
5. **Restart Claude Code** — MCP servers re-initialize on session start

### Account credentials reference (from `.mcp.json`)

| Account | Email | Client ID | Client Secret |
|---------|-------|-----------|---------------|
| gmail | justinrsteele@gmail.com | `917389778928-...` | `GOCSPX-U-VVV...` |
| truesteele | justin@truesteele.com | `5115291851-...` | `GOCSPX-HuT7...` |
| kindora | justin@kindora.co | `321514384644-...` | `GOCSPX-vYVK...` |
| outdoorithm | justin@outdoorithm.com | `511709495997-...` | `GOCSPX-ACL5...` |
| outdoorithm-collective | justin@outdoorithmcollective.org | `740038156430-...` | `GOCSPX-L-My...` |

**When this won't work** (need browser login):
- `invalid_grant` error → refresh token was revoked
- Credential file missing entirely
- Need to add new OAuth scopes

### Browser Auth Fix — Manual OAuth Flow (PREFERRED METHOD)

The MCP `start_google_auth` tool is unreliable because:
1. Stale workspace-mcp processes from old sessions squat on port 8000
2. State parameters expire if there's any delay between generating and completing the flow
3. Killing the wrong process crashes the MCP server for the rest of the session

**Use this manual flow instead — it always works:**

```bash
# 1. Generate PKCE credentials and auth URL (uses port 8888, not 8000)
python3 << 'PYEOF'
import hashlib, base64, secrets, json, os, urllib.parse

code_verifier = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).decode().rstrip('=')

with open('/tmp/gmail_oauth_verifier.json', 'w') as f:
    json.dump({'code_verifier': code_verifier}, f)

# Change this to the target account's client_id from .mcp.json
mcp = json.load(open(os.path.expanduser('~/Code/TrueSteele/contacts/.mcp.json')))
# Pick the right MCP server key: google-workspace, google-workspace-truesteele, etc.
client_id = mcp['mcpServers']['google-workspace']['env']['GOOGLE_OAUTH_CLIENT_ID']

params = {
    'response_type': 'code',
    'client_id': client_id,
    'redirect_uri': 'http://localhost:8888/callback',
    'scope': 'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.modify',
    'access_type': 'offline',
    'prompt': 'consent',
    'code_challenge': code_challenge,
    'code_challenge_method': 'S256',
    'state': secrets.token_hex(16),
}
print('https://accounts.google.com/o/oauth2/auth?' + urllib.parse.urlencode(params))
PYEOF

# 2. Start a temporary callback server on port 8888
python3 << 'PYEOF' &
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse, json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        with open('/tmp/gmail_oauth_code.txt', 'w') as f:
            f.write(params.get('code', ['NO_CODE'])[0])
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h2>Auth successful! You can close this window.</h2>')
    def log_message(self, *args): pass

server = HTTPServer(('127.0.0.1', 8888), Handler)
server.timeout = 120
server.handle_request()
PYEOF

# 3. Present the auth URL to the user — they click, sign in, approve
#    Browser shows "Auth successful!" when done

# 4. Exchange the code for tokens
CODE=$(cat /tmp/gmail_oauth_code.txt)
VERIFIER=$(python3 -c "import json; print(json.load(open('/tmp/gmail_oauth_verifier.json'))['code_verifier'], end='')")
# CLIENT_ID and CLIENT_SECRET from .mcp.json for the target account
curl -s -X POST "https://oauth2.googleapis.com/token" \
  -d "grant_type=authorization_code" \
  -d "code=$CODE" \
  -d "redirect_uri=http://localhost:8888/callback" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "code_verifier=$VERIFIER"
# Returns: access_token, refresh_token, expires_in

# 5. Update the credential file
#    ~/.google_workspace_mcp/credentials/{email}.json
#    Set: access_token, refresh_token, client_id, client_secret, expiry

# 6. If GMAIL_REFRESH_TOKEN is set on Vercel, update it too:
#    printf '%s' "$NEW_REFRESH" | npx vercel env add GMAIL_REFRESH_TOKEN production --scope true-steele
#    Then redeploy: npx vercel --prod --yes --scope true-steele
```

**Why this works vs `start_google_auth`:**
- Uses port 8888 (avoids the port 8000 collision with MCP servers)
- Self-contained — no dependency on MCP server state or process lifecycle
- PKCE verifier is saved to disk, so code exchange always succeeds
- No state parameter expiry issues since the flow runs end-to-end

**Important:** When piping env vars to `vercel env add`, use `printf '%s'` NOT `echo` — echo adds a trailing newline that corrupts OAuth tokens.

### Legacy: `start_google_auth` MCP Flow (avoid if possible)

Only use this if the manual flow above can't work for some reason.

1. Kill ALL stale workspace-mcp processes: `ps aux | grep workspace-mcp | grep -v grep` → kill old PIDs
2. Verify port 8000 is free: `lsof -i :8000 -P -n`
3. Call `start_google_auth(service_name="gmail", user_google_email="...")`
4. User clicks URL, signs in, approves — browser must complete the redirect (don't paste URL back)
5. If "Invalid or expired OAuth state parameter" → state expired, start over

**Key insight:** With 5+ Google Workspace MCP servers, zombie processes accumulate. Always kill stale ones first.

## Database Schema (Supabase PostgreSQL)

### `contacts` — main contact table (~2,940 rows)
**Identity:** `id` (int PK), `first_name`, `last_name`, `normalized_full_name`, `linkedin_url`, `linkedin_username`
**Contact info:** `email`, `email_2`, `work_email`, `personal_email`, `normalized_phone_number`, `city`, `state`
**Current role:** `company`, `position`, `headline`, `summary`
**Enrichment (Apify):** `enrich_current_company`, `enrich_current_title`, `enrich_current_since`, `enrich_years_in_current_role`, `enrich_total_experience_years`, `enrich_follower_count`, `enrich_connections`, `enrich_schools` (array), `enrich_companies_worked` (array), `enrich_titles_held` (array), `enrich_skills` (array), `enrich_board_positions` (array), `enrich_volunteer_orgs` (array), `enrich_employment` (jsonb), `enrich_education` (jsonb)
**Donor scoring:** `donor_capacity_score`, `donor_propensity_score`, `donor_affinity_score`, `donor_warmth_score`, `donor_total_score`, `donor_tier`, `estimated_capacity`
**AI scoring:** `ai_proximity_score`, `ai_proximity_tier`, `ai_capacity_score`, `ai_capacity_tier`, `ai_kindora_prospect_score`, `ai_kindora_prospect_type`, `ai_outdoorithm_fit`, `ai_tags` (jsonb), `ask_readiness` (jsonb)
**Comms (rollup):** `communication_history` (jsonb — email thread summaries), `comms_summary` (jsonb — channel-level stats for email/calendar/linkedin/sms/calls), `comms_last_date`, `comms_thread_count`, `comms_closeness`, `comms_momentum`, `comms_reasoning`, `comms_meeting_count`, `comms_last_meeting`, `comms_call_count`, `comms_last_call`
**Other enrichment:** `fec_donations` (jsonb), `real_estate_data` (jsonb), `oc_engagement` (jsonb), `linkedin_reactions` (jsonb), `campaign_2026` (jsonb), `contact_pools` (array), `familiarity_rating` (smallint)
**Cultivation:** `cultivation_stage`, `cultivation_notes`, `cultivation_plan`, `next_touchpoint_date`, `last_contact_date`, `expected_ask_date`, `expected_ask_amount`

### `contact_email_threads` — email AND LinkedIn DM threads
**Note:** `channel` column = `'email'` or `'linkedin'`. LinkedIn DMs are stored here too.
`id`, `contact_id` (FK), `thread_id`, `account_email`, `channel`, `subject`, `snippet`, `summary`, `message_count`, `first_message_date`, `last_message_date`, `direction` (sent/received/bidirectional), `participants` (jsonb), `labels` (jsonb), `raw_messages` (jsonb — full message bodies), `is_group`, `participant_count`

### `contact_calendar_events` — meetings
`id`, `contact_id` (FK), `event_id`, `ical_uid`, `account_email`, `summary`, `description`, `start_time`, `end_time`, `duration_minutes`, `location`, `event_type`, `attendee_count`, `attendees` (jsonb), `organizer_email`, `is_organizer`, `response_status`, `recurring`, `conference_type`

### `contact_sms_conversations` — SMS threads
`id`, `contact_id` (FK), `phone_number`, `message_count`, `sent_count`, `received_count`, `first_message_date`, `last_message_date`, `sms_contact_name`, `match_method`, `match_confidence`, `sample_messages` (jsonb), `summary`

### `contact_call_logs` — phone calls
`id`, `contact_id` (FK), `phone_number`, `call_date`, `call_type`, `duration_seconds`, `contact_name_in_phone`, `match_method`, `match_confidence`

### Common query patterns
- **Find contact:** `WHERE first_name ILIKE '%X%' AND last_name ILIKE '%Y%'` or `WHERE normalized_full_name ILIKE '%X%Y%'`
- **Get LinkedIn DMs:** `SELECT raw_messages FROM contact_email_threads WHERE contact_id = X AND channel = 'linkedin'`
- **Get all comms:** Query `contact_email_threads`, `contact_calendar_events`, `contact_sms_conversations`, `contact_call_logs` by `contact_id`

## Python Environment
- **Venv:** `.venv/` (arm64, Python 3.12)
- **Activate:** `source .venv/bin/activate`
- **Run scripts from:** `scripts/intelligence/` directory (for local imports)
- **Background runs:** Use `python -u` flag with nohup for unbuffered output
