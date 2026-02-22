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

**When this won't work** (need browser login via `start_google_auth`):
- `invalid_grant` error → refresh token was revoked
- Credential file missing entirely
- Need to add new OAuth scopes

## Python Environment
- **Venv:** `.venv/` (arm64, Python 3.12)
- **Activate:** `source .venv/bin/activate`
- **Run scripts from:** `scripts/intelligence/` directory (for local imports)
- **Background runs:** Use `python -u` flag with nohup for unbuffered output
