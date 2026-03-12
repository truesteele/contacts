# Blackbaud SKY API Integration — Development Plan

**Version:** 3.0
**Last Updated:** March 8, 2026
**Status:** All Phases Complete, QA Audited, Deployed to Production
**Owner:** Justin Steele

---

## Table of Contents

1. [Overview](#1-overview)
2. [Blackbaud Credentials & API Details](#2-blackbaud-credentials--api-details)
3. [Phase 1: OAuth + Foundation Import](#3-phase-1-oauth--foundation-import)
4. [Phase 2: Push to RE NXT + Gift History](#4-phase-2-push-to-re-nxt--gift-history)
5. [Phase 3: "Who Do You Know?" Relationship Mapping](#5-phase-3-who-do-you-know-relationship-mapping)
6. [Phase 4: SKY Add-in Tile](#6-phase-4-sky-add-in-tile)
7. [Database Schema](#7-database-schema)
8. [File Structure](#8-file-structure)
9. [Security & Token Management](#9-security--token-management)
10. [Rate Limits & Error Handling](#10-rate-limits--error-handling)
11. [Testing Strategy](#11-testing-strategy)
12. [API Endpoint Reference](#12-api-endpoint-reference)
13. [Timeline & Milestones](#13-timeline--milestones)
14. [Deprioritized Integrations](#14-deprioritized-integrations)
15. [Blackbaud Platform Prerequisites](#15-blackbaud-platform-prerequisites)
16. [Progress Log](#16-progress-log)

---

## 1. Overview

### Strategic Position

Kindora integrates as an **intelligence layer on top of Raiser's Edge NXT** — not a competing CRM. RE NXT remains the source of truth for relationship tracking; Kindora enriches it with AI-powered funder intelligence and surfaces new opportunities that sync back.

### Integration Summary

| # | Integration | Phase | Purpose |
|---|---|---|---|
| 1 | OAuth "Connect to Blackbaud" | Phase 1 | Authentication foundation — everything depends on this |
| 2 | Import Foundation Constituents | Phase 1 | Pull RE NXT foundations → enrich with Kindora intelligence |
| 3 | Push Kindora Matches → RE NXT | Phase 2 | "Add to RE NXT" button creates constituent + opportunity records |
| 4 | Gift History Import | Phase 2 | Past grant data for re-approach intelligence |
| 5 | "Who Do You Know?" Relationship Mapping | Phase 3 | Cross-reference RE NXT relationships × 990 officer data |
| 6 | SKY Add-in Tile in RE NXT | Phase 4 | Kindora intelligence card embedded inside RE NXT UI |

### Value Proposition for RE NXT Users

- "Connect Kindora and instantly enrich your foundation prospects with AI-powered intelligence"
- "Discover new funders and add them to RE NXT with one click — no manual data entry"
- "See who in your donor base is connected to foundation decision-makers"
- "Get Kindora fit scores right inside your RE NXT workflow"

---

## 2. Blackbaud Credentials & API Details

### API Subscription

| Field | Value |
|---|---|
| **Tier** | Standard |
| **Rate Limit** | 10 calls/second |
| **Daily Limit** | 100,000 calls/24-hour period (upgraded, approved 3/3/2026) |
| **Primary Subscription Key** | `d4ef4001d79142928cd1a998a50551be` |
| **Secondary Subscription Key** | `5d1a9545a9e246ae8e5dd04e12685a15` |

### OAuth 2.0 Endpoints

| Endpoint | URL |
|---|---|
| **Authorization** | `https://oauth2.sky.blackbaud.com/authorization` |
| **Token Exchange** | `https://oauth2.sky.blackbaud.com/token` |
| **Token Refresh** | `https://oauth2.sky.blackbaud.com/token` (with `grant_type=refresh_token`) |

### Required Headers for API Calls

```
Authorization: Bearer {oauth_access_token}
Bb-Api-Subscription-Key: d4ef4001d79142928cd1a998a50551be
```

### SKY API Application Credentials

| Field | Value |
|---|---|
| **Application ID (client_id)** | `781e3f16-0123-4ea0-b03c-444282f480fd` |
| **Application Secret (client_secret)** | `Boe08nnn78W8aaVe8PdalMyRas3Mk26tV0hebZGQHl4=` (primary) |
| **Secondary Secret** | `eISFnLw/BgERMuiBzYL3+y0AOE+kQzrWx3MpON4v7y0=` |
| **Redirect URI (production)** | `https://kindora.co/api/integrations/blackbaud/callback` |
| **Redirect URI (local dev)** | `http://localhost:8000/api/integrations/blackbaud/callback` |
| **Redirect URI (local dev alt)** | `http://localhost:8001/api/integrations/blackbaud/callback` |
| **Token Encryption Key** | `hoWpJmvBEeJYWDa2_IWuGKeuS_O2PA4jX2BvhgAfnGU=` (Fernet) |

### RE NXT API Base URL

```
https://api.sky.blackbaud.com
```

### Key API Endpoints We'll Use

#### Constituent API
```
GET  /constituent/v1/constituents                    # List constituents (filterable)
GET  /constituent/v1/constituents/{id}               # Get single constituent
POST /constituent/v1/constituents                    # Create constituent
PATCH /constituent/v1/constituents/{id}              # Update constituent
GET  /constituent/v1/constituents/{id}/relationships # Get relationships
GET  /constituent/v1/constituents/search             # Search by name
GET  /constituent/v1/organizations                   # List organizations specifically
```

#### Gift API
```
GET  /gift/v1/gifts                                  # List gifts
GET  /gift/v1/gifts/{id}                             # Get single gift
```

#### Opportunity API
```
GET  /opportunity/v1/opportunities                   # List opportunities
POST /opportunity/v1/opportunities                   # Create opportunity
PATCH /opportunity/v1/opportunities/{id}             # Update opportunity
```

#### Fundraising API
```
GET  /fundraising/v1/campaigns                       # List campaigns
GET  /fundraising/v1/funds                           # List funds
GET  /fundraising/v1/appeals                         # List appeals
```

#### Action API (within Constituent)
```
POST /constituent/v1/actions                         # Create action/task
GET  /constituent/v1/constituents/{id}/actions       # List actions for constituent
```

#### Note API (within Constituent)
```
POST /constituent/v1/constituents/{id}/notes         # Add note to constituent
GET  /constituent/v1/constituents/{id}/notes         # List notes
```

---

## 3. Phase 1: OAuth + Foundation Import

**Target:** February–March 2026
**Goal:** Users connect RE NXT and see their foundations enriched with Kindora intelligence

### Integration 1: OAuth "Connect to Blackbaud"

#### User Flow

```
Settings → Integrations tab → "Connect to Blackbaud RE NXT" button
  → Redirect to oauth2.sky.blackbaud.com/authorization
  → User logs in to Blackbaud, authorizes Kindora
  → Redirect back to Kindora with auth code
  → Backend exchanges code for access_token + refresh_token
  → Tokens stored encrypted in client.blackbaud_integrations
  → UI shows "Connected" status with last sync time
```

#### Backend Implementation

**File: `services/blackbaud/client.py`**
- `BlackbaudOAuthClient` class
  - `get_authorization_url(organization_id)` → returns redirect URL with state param
  - `exchange_code(code, state)` → POST to token endpoint, store tokens
  - `refresh_token(integration_id)` → proactive refresh before expiry
  - `make_request(integration_id, method, endpoint, **kwargs)` → authenticated API call with auto-refresh
- Token encryption using Fernet (symmetric, key from `BLACKBAUD_ENCRYPTION_KEY` env var)
- State parameter includes `organization_id` to route callback correctly

**File: `api/routes/blackbaud.py`**
- `GET /integrations/blackbaud/connect` — initiate OAuth, returns redirect URL
- `GET /integrations/blackbaud/callback` — OAuth callback, exchanges code
- `GET /integrations/blackbaud/status` — connection status for UI
- `DELETE /integrations/blackbaud/disconnect` — revoke tokens, mark disconnected
- `POST /integrations/blackbaud/sync` — trigger manual sync

**Auth requirements:** All endpoints require Supabase JWT + organization membership check.

#### Frontend Implementation

**File: `src/app/dashboard/settings/integrations/page.tsx`**
- New "Integrations" tab in settings
- Blackbaud connection card showing:
  - Connection status (connected/disconnected/error)
  - Connected user name and environment
  - Last sync timestamp
  - "Connect" / "Disconnect" / "Re-sync" buttons
  - Sync history table (recent syncs with record counts)

**File: `src/components/blackbaud/ConnectBlackbaudButton.tsx`**
- Initiates OAuth flow
- Handles redirect back with success/error state
- Shows loading during token exchange

#### Token Lifecycle

```
1. User clicks "Connect" → GET /integrations/blackbaud/connect
2. Backend generates state param (org_id + CSRF nonce), stores in Redis (5 min TTL)
3. Redirect to Blackbaud authorization URL
4. User authorizes → redirect to callback with ?code=xxx&state=yyy
5. Backend verifies state, exchanges code for tokens
6. Access token (60 min) + refresh token stored encrypted in DB
7. Before every API call: check token expiry, refresh if < 5 min remaining
8. Refresh tokens have long expiry but can be revoked by user in Blackbaud
```

### Integration 2: Import Foundation Constituents

#### User Flow

```
After connecting → "Import Foundations" button (or auto-trigger)
  → Backend fetches organizational constituents from RE NXT
  → Filters for foundation/funder types
  → Cross-references against Kindora's us_foundations (by name, EIN) and non_990_funders
  → Creates funder_evaluations for matches
  → UI shows: "Found 47 foundations in your RE NXT. 38 matched to Kindora data."
  → Each matched foundation gets Kindora fit score + intelligence summary
```

#### Backend Implementation

**File: `services/blackbaud/constituent_service.py`**
- `import_foundation_constituents(organization_id)`:
  1. `GET /constituent/v1/organizations` — paginate through all org constituents
  2. Filter by type indicators (foundation, grant-making, charitable org)
  3. For each foundation:
     - Extract: name, EIN (if available), address, website, contacts
     - Fuzzy match against `us_foundations.legal_name` (using existing matching patterns)
     - If EIN available, exact match against `us_foundations.ein`
     - Check `non_990_funders` by name/website
     - Store mapping in `blackbaud_constituent_mappings`
  4. For matched funders: trigger Kindora enrichment (fit score, intelligence)
  5. Record sync in `blackbaud_sync_history`

**File: `tasks/blackbaud_tasks.py`**
- `sync_constituents_task(organization_id)` — Celery task for background import
- `enrich_imported_foundations_task(organization_id, funder_ids)` — batch enrichment

#### Data Mapping: RE NXT → Kindora

| RE NXT Field | Kindora Field | Notes |
|---|---|---|
| `name` | Fuzzy match → `us_foundations.legal_name` | Primary matching field |
| `lookup_id` (EIN) | `us_foundations.ein` | Exact match when available |
| `address` | Validation of match | City/state for disambiguation |
| `web` | `us_foundations.website_url` | Secondary matching signal |
| `constituent_id` | `blackbaud_constituent_mappings.bb_constituent_id` | Stored for two-way reference |

#### Matching Strategy

1. **EIN exact match** — highest confidence (if RE NXT has EIN stored)
2. **Name + State match** — fuzzy match legal name within same state
3. **Website domain match** — normalize and compare domains
4. **Manual review queue** — unmatched foundations flagged for user confirmation

#### Pagination Note

RE NXT list endpoints return paginated results. Use `offset` and `limit` query params.
Kindora's Supabase 1000-row cap also applies to lookup queries — use `.range()` loops.

### Phase 1 Deliverables Checklist

- [x] Database migration: `blackbaud_integrations`, `blackbaud_constituent_mappings`, `blackbaud_sync_history`
- [x] RLS policies + schema grants for new tables
- [x] `BlackbaudOAuthClient` with token encryption
- [x] OAuth routes (connect, callback, status, disconnect)
- [x] Settings > Integrations tab UI
- [x] Constituent import service with matching logic
- [x] Celery tasks for background sync
- [x] Import results UI (matched/unmatched counts, review queue)
- [x] Error handling for expired tokens, revoked access, API errors
- [x] Integration tests with Blackbaud sandbox

---

## 4. Phase 2: Push to RE NXT + Gift History

**Target:** March–May 2026
**Goal:** Two-way data flow — Kindora matches create RE NXT records; RE NXT gift history powers re-approach intelligence

### Integration 3: Push Kindora Matches → RE NXT

#### User Flow

```
Funder match results or funder detail page:
  → "Add to RE NXT Pipeline" button
  → Kindora creates in RE NXT:
     (a) Organizational constituent record (foundation details)
     (b) Opportunity record (suggested ask amount, deadline, Kindora fit score)
     (c) Note with Kindora intelligence brief summary
  → User sees: "Added to RE NXT. View in Blackbaud →"
  → Mapping stored so future syncs don't duplicate
```

#### Backend Implementation

**File: `services/blackbaud/push_service.py`**
- `push_funder_to_renxt(organization_id, funder_id)`:
  1. Check `blackbaud_constituent_mappings` — skip if already pushed
  2. Build constituent payload from Kindora data:
     - Organization name, address, website, EIN
     - Constituent type = "Organization"
  3. `POST /constituent/v1/constituents` → get `constituent_id`
  4. Build opportunity payload:
     - Description from Kindora match rationale
     - Ask amount from median grant size
     - Expected date from typical grant cycle
     - Status = "Prospect"
  5. `POST /opportunity/v1/opportunities` → get `opportunity_id`
  6. Build note with Kindora intelligence summary:
     - Fit score and rationale
     - Key focus areas and giving patterns
     - Recent grants relevant to user's mission
  7. `POST /constituent/v1/constituents/{id}/notes`
  8. Store all IDs in `blackbaud_constituent_mappings`

#### Constituent Payload Example

```json
{
  "type": "Organization",
  "name": "The William and Flora Hewlett Foundation",
  "address": {
    "street_address": "2121 Sand Hill Road",
    "city": "Menlo Park",
    "state": "CA",
    "zip": "94025",
    "country": "US",
    "type": "Business"
  },
  "online_presence": {
    "url": "https://hewlett.org",
    "type": "Website"
  }
}
```

#### Opportunity Payload Example

```json
{
  "constituent_id": "{bb_constituent_id}",
  "name": "Hewlett Foundation — General Operating Support",
  "purpose": "Kindora match (92/100 fit score). Strong alignment on climate resilience and community-led solutions.",
  "ask_amount": {
    "value": 50000
  },
  "expected_date": "2026-09-01",
  "status": "Prospect",
  "fundraisers": ["{current_user_bb_id}"]
}
```

### Integration 4: Gift History Import

#### User Flow

```
After initial constituent import:
  → Backend fetches gift history for mapped foundations
  → For each foundation with gift records:
     - "You received $25K from this funder in 2023"
     - "Last gift: $10K on 6/15/2024"
     - "Total received: $85K across 4 grants"
  → Enriched funder view shows RE NXT relationship data alongside Kindora intelligence
  → Re-approach recommendations: "This funder increased giving to similar orgs by 30%"
```

#### Backend Implementation

**File: `services/blackbaud/gift_service.py`**
- `import_gift_history(organization_id)`:
  1. For each mapped foundation in `blackbaud_constituent_mappings`:
     - `GET /gift/v1/gifts?constituent_id={bb_id}` — paginate
     - Filter for grants/foundation gifts (vs. individual donations)
     - Extract: amount, date, fund, campaign, type
     - Store in `blackbaud_gift_history`
  2. Compute aggregate stats per funder:
     - Total received, grant count, avg amount, last gift date
  3. Cross-reference with Kindora's `foundation_grants` data:
     - Compare what the funder gave THIS org vs. similar orgs
     - Identify giving trend (increasing, stable, declining)
  4. Generate re-approach scoring signal

#### Data Model: `blackbaud_gift_history`

```sql
CREATE TABLE client.blackbaud_gift_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES client.organizations(id),
  bb_constituent_id TEXT NOT NULL,        -- RE NXT foundation constituent
  kindora_funder_id TEXT,                 -- Mapped Kindora funder (EIN or UUID)
  bb_gift_id TEXT NOT NULL,               -- RE NXT gift ID
  gift_amount DECIMAL(12,2),
  gift_date DATE,
  gift_type TEXT,                         -- Grant, pledge, etc.
  fund_name TEXT,
  campaign_name TEXT,
  notes TEXT,
  imported_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(organization_id, bb_gift_id)
);
```

### Phase 2 Deliverables Checklist

- [x] Database migration: `blackbaud_gift_history`, updates to `blackbaud_constituent_mappings`
- [x] Push service (create constituent + opportunity + note in RE NXT)
- [x] "Add to RE NXT" button on funder match results and funder detail page
- [x] Gift history import service
- [x] Gift history display in enriched funder view
- [x] Re-approach scoring logic (gift history + Kindora 990 trends)
- [x] Duplicate detection (don't create duplicate constituents on re-push)
- [x] Celery task for batch gift history import
- [x] UI: gift history timeline on funder detail page

---

## 5. Phase 3: "Who Do You Know?" Relationship Mapping

**Target:** May–July 2026
**Goal:** Surface warm introduction paths by cross-referencing RE NXT relationships with 990 officer data

### The Killer Feature

This is Kindora's **strongest differentiator** against Instrumentl, Candid, and every other funder discovery tool. Nobody else has:
- 173K foundations' worth of 990 Part VII officer/director/trustee data
- Cross-referenced against a nonprofit's own donor/constituent database
- Surfaced as actionable warm introduction paths

### User Flow

```
Funder detail page → "Who Do You Know?" section:
  → "You may know 3 people connected to this funder"
  → Card 1: "Jane Doe is in your RE NXT database AND sits on XYZ Foundation's board"
     [Direct connection — highest strength]
  → Card 2: "Tom Jones (your major donor) works at Acme Corp.
     Acme's CEO Sarah Chen sits on XYZ Foundation's board."
     [Employer chain — medium strength]
  → Card 3: "Your board member Mike Smith worked at XYZ Foundation 2019-2022."
     [Past affiliation — informational]
  → Quick action: "Ask [Name] for an introduction" → links to RE NXT record
```

### Data Sources

#### Kindora Side (Foundation Decision-Makers)
- **IRS 990 Part VII:** Officers, directors, trustees, key employees for 173K foundations
- **Foundation websites:** CEO, program officers, board via web scraping
- **Contact enrichment data:** LinkedIn profiles, employment history
- Tables: `us_foundations`, `funder_990_snapshots`, enriched leadership data

#### RE NXT Side (Nonprofit's Network)
- **Constituent relationships:** Employer, board member, family, friend, colleague
- **Constituent codes:** "Board Member", "Volunteer", "Major Donor", "Staff"
- **Organization links:** Employer organizations, affiliated orgs
- API: `GET /constituent/v1/constituents/{id}/relationships`

### Backend Implementation

**File: `services/blackbaud/relationship_service.py`**

#### Step 1: Build Foundation Decision-Maker Index
- For a given funder, extract all known decision-makers:
  - 990 Part VII officers/directors/trustees
  - Enriched staff profiles (CEO, program officers)
  - Board members from web scraping
- Normalize names for matching (lowercase, remove titles/suffixes)

#### Step 2: Scan RE NXT Constituents for Matches
- `GET /constituent/v1/constituents/search?search_text={name}` for each decision-maker
- Also check existing imported constituents from Phase 1
- Match types:
  - **Name exact match:** Same person in both systems
  - **Employer match:** Constituent works at same company as a foundation board member
  - **Organization match:** Constituent has relationship to foundation's parent org

#### Step 3: Classify Connection Strength
```python
class ConnectionStrength(Enum):
    DIRECT = "direct"           # Person is in both RE NXT and on funder's board
    EMPLOYER = "employer"       # RE NXT constituent's employer → funder board member
    SHARED_ORG = "shared_org"   # Both affiliated with same non-funder organization
    FAMILY = "family"           # Family connection to funder decision-maker
    PAST = "past"               # Past affiliation (former employer, former board)
```

#### Step 4: Cache Results
- Store discovered connections in `blackbaud_relationship_matches`
- Refresh on sync or on-demand
- Show "last checked" timestamp in UI

### Name Matching Strategy

Use existing V4 matching patterns:
1. **Exact normalized match:** "Jane A. Doe" == "jane doe" after normalization
2. **Fuzzy match:** Levenshtein distance < 2 for short names, < 3 for long
3. **Embedding similarity:** If exact/fuzzy fails, use text-embedding-3-small for semantic similarity (reuse FAISS infrastructure from EIN matching)

### API Call Budget

For a typical nonprofit with 500 constituents and checking against 10 target funders:
- 10 funders × ~5 decision-makers each = 50 name searches
- 50 searches × 1 API call each = 50 calls
- Well within 25K/day limit
- For bulk scanning: batch via Celery, respect 10/sec rate limit

### Phase 3 Deliverables Checklist

- [x] Database migration: `blackbaud_relationship_matches`
- [x] Foundation decision-maker index builder (from 990 + enrichment data)
- [x] RE NXT relationship scanner
- [x] Name matching engine (exact + Jaccard similarity ≥ 0.80)
- [x] Connection strength classifier (direct/employer/shared_org/past, 1-5 scale)
- [x] "Who Do You Know?" UI component on funder detail page
- [x] Connection cards with relationship path visualization
- [x] "Scan for Connections" button with rescan capability
- [x] Celery task for bulk relationship scanning (single funder or all promoted)
- [x] Dedup via unique constraint on (org, funder, constituent, person_name)

---

## 6. Phase 4: SKY Add-in Tile

**Target:** Q4 2026
**Goal:** Kindora intelligence visible inside RE NXT without switching apps

### How SKY Add-ins Work

- Add-ins are **iframe-based extensions** that render inside the RE NXT interface
- Registered via the SKY Developer Portal on the application settings
- Uses `@blackbaud/sky-addin-client` npm package for host ↔ iframe communication
- Two supported types: **Tile** (visible content area) and **Button** (action trigger)

### What the Tile Shows

When viewing a foundation constituent in RE NXT, a Kindora tile appears:

```
┌─────────────────────────────────────┐
│  🔍 Kindora Intelligence            │
│                                     │
│  Fit Score: 87/100  ████████░░      │
│                                     │
│  Focus: Climate, Education, Equity  │
│  Avg Grant: $45,000                 │
│  Recent: Increased giving 23% YoY   │
│                                     │
│  [View Full Brief] [Find Similar]   │
└─────────────────────────────────────┘
```

### Implementation

**File: `src/app/dashboard/addin/blackbaud-tile/page.tsx`**
- Lightweight Next.js page optimized for iframe embedding
- Receives constituent context from host page via `sky-addin-client`
- Looks up constituent → Kindora funder mapping
- Renders compact intelligence card
- Links open in new tab to full Kindora funder detail

**npm dependency:** `@blackbaud/sky-addin-client`

**Registration:** Configure add-in URL in SKY Developer Portal application settings

### SKY Add-in Registration Guide

Follow these steps to register the Kindora tile in the SKY Developer Portal:

#### Step 1: Navigate to Add-in Configuration

1. Go to [SKY Developer Portal](https://developer.blackbaud.com/apps/)
2. Select the **Kindora** application
3. Navigate to the **Add-ins** tab in the application settings

#### Step 2: Create the Tile Add-in

1. Click **"Add"** to create a new add-in
2. Configure the add-in:
   - **Add-in type:** Tile
   - **Extension point:** Constituent > Organization (the tile appears on organization constituent records)
   - **Add-in name:** `Kindora Intelligence`
   - **Add-in description:** `AI-powered funder intelligence — fit scores, focus areas, and grant data`

#### Step 3: Configure the Tile URL

The tile URL includes the per-org API key as a query parameter:

```
https://kindora.co/addin/blackbaud-tile?key={addin_api_key}
```

- The `key` parameter is the API key generated via `POST /integrations/blackbaud/addin/generate-key`
- Each organization gets its own API key (generated once, stored hashed in DB)
- The tile URL is the same for all users within an organization

**Note:** The tile URL is configured per-application in the developer portal, NOT per-org. For multi-tenant support, the API key in the URL identifies which org's data to serve. Users must generate their org's API key via Kindora's settings page first.

#### Step 4: Context Parameters

The SKY Add-in host page passes context to the iframe via `AddinClient.init()`:

| Parameter | Description | Usage |
|---|---|---|
| `context.id` | RE NXT constituent record ID | Used as `bb_constituent_id` to look up mapping |
| `context.envId` | Blackbaud environment ID | Used for environment validation |

The tile's `AddinClient` receives these in the `init` callback and uses `context.id` to call the backend endpoint.

#### Step 5: Test in Sandbox

1. After registering, the add-in appears in the SKY Developer Cohort environment
2. Navigate to an organization constituent record in RE NXT
3. The Kindora tile should load in the constituent record's tile section
4. For testing, create a test org API key and configure the tile URL

**Sandbox URL (for testing):**
```
https://host.nxt.blackbaud.com/gmk/dashboard?envid=p-vnVAbDtfu0GyMqSDmG-_qw
```

### Add-in API Key Generation Flow

Users must generate an API key to enable the SKY Add-in tile for their organization:

```
Settings → Integrations → Blackbaud section
  → "Generate Add-in Key" button (only shown when connected)
  → Backend: POST /integrations/blackbaud/addin/generate-key
     → Generates kbi_{secrets.token_urlsafe(32)} plaintext key
     → Stores SHA-256 hash in client.blackbaud_integrations.addin_api_key
     → Returns plaintext key ONCE
  → User copies key and configures it in the tile URL
  → Key cannot be retrieved again (only regenerated)
```

**API Key Format:** `kbi_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`

**Security model:**
- Key prefix `kbi_` identifies Kindora Blackbaud Integration keys
- Only the SHA-256 hash is stored in the database
- Lookup: hash the incoming `X-Blackbaud-Addin-Key` header → match against stored hash → resolve org
- CORS restricted to `*.blackbaud.com` and `*.blackbaud-dev.com` origins
- No Supabase JWT required (iframe has no Kindora session context)

**Endpoints:**
- `POST /api/integrations/blackbaud/addin/generate-key` — Authenticated (standard dual-auth), generates new key
- `GET /api/integrations/blackbaud/addin/constituent/{bb_constituent_id}` — Public (API key auth via `X-Blackbaud-Addin-Key` header)

### Phase 4 Deliverables Checklist

- [x] Install `@blackbaud/sky-addin-client` dependency (v1.7.2)
- [x] Build lightweight tile page (optimized for iframe, ~300px width)
- [x] Constituent → Kindora funder lookup (via per-org API key auth)
- [x] Compact intelligence card component (fit score, focus areas, median grant)
- [x] Add-in API key generation endpoint (`POST /addin/generate-key`)
- [x] Add-in data endpoint (`GET /addin/constituent/{bb_constituent_id}`)
- [x] Handle "no match" state gracefully (`{matched: false}`)
- [x] CORS for `*.blackbaud.com` and `*.blackbaud-dev.com`
- [x] Middleware bypass for `/addin` routes (no Supabase auth redirect)
- [ ] Register add-in in SKY Developer Portal (manual step — see registration guide above)
- [ ] Test in sandbox environment (requires portal registration first)

---

## 7. Database Schema

### New Tables (all in `client` schema)

```sql
-- Core integration record (one per org)
CREATE TABLE client.blackbaud_integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES client.organizations(id) UNIQUE,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'active', 'disconnected', 'error', 'token_expired')),
  bb_environment_id TEXT,                    -- Blackbaud environment identifier
  bb_environment_name TEXT,                  -- Human-readable environment name
  oauth_access_token_encrypted TEXT,
  oauth_refresh_token_encrypted TEXT,
  token_expires_at TIMESTAMPTZ,
  connected_by UUID REFERENCES auth.users(id),
  connected_at TIMESTAMPTZ,
  last_sync_at TIMESTAMPTZ,
  last_sync_status TEXT,
  last_sync_error TEXT,
  auto_sync_enabled BOOLEAN DEFAULT false,
  sync_interval_hours INTEGER DEFAULT 24,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Mapping between RE NXT constituents and Kindora funders
CREATE TABLE client.blackbaud_constituent_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES client.organizations(id),
  bb_constituent_id TEXT NOT NULL,          -- RE NXT constituent ID
  bb_constituent_name TEXT,                 -- Name from RE NXT
  bb_constituent_type TEXT,                 -- Organization, Individual
  kindora_funder_id TEXT,                   -- EIN or UUID (polymorphic)
  kindora_funder_type TEXT,                 -- us_foundation, non_990, unmatched
  match_method TEXT,                        -- ein_exact, name_fuzzy, domain, manual
  match_confidence DECIMAL(5,2),
  push_direction TEXT DEFAULT 'imported'    -- imported (RE NXT→Kindora) or pushed (Kindora→RE NXT)
    CHECK (push_direction IN ('imported', 'pushed')),
  bb_opportunity_id TEXT,                   -- If we created an opportunity in RE NXT
  last_synced_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(organization_id, bb_constituent_id)
);

-- Gift history from RE NXT
CREATE TABLE client.blackbaud_gift_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES client.organizations(id),
  bb_constituent_id TEXT NOT NULL,
  kindora_funder_id TEXT,
  bb_gift_id TEXT NOT NULL,
  gift_amount DECIMAL(12,2),
  gift_date DATE,
  gift_type TEXT,
  fund_name TEXT,
  campaign_name TEXT,
  notes TEXT,
  imported_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(organization_id, bb_gift_id)
);

-- Sync operation history
CREATE TABLE client.blackbaud_sync_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES client.organizations(id),
  integration_id UUID NOT NULL REFERENCES client.blackbaud_integrations(id),
  sync_type TEXT NOT NULL
    CHECK (sync_type IN ('constituent_import', 'gift_import', 'push_funder', 'relationship_scan', 'full_sync')),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')),
  records_processed INTEGER DEFAULT 0,
  records_matched INTEGER DEFAULT 0,
  records_created INTEGER DEFAULT 0,
  records_failed INTEGER DEFAULT 0,
  error_message TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Relationship match results for "Who Do You Know?"
CREATE TABLE client.blackbaud_relationship_matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES client.organizations(id),
  kindora_funder_id TEXT NOT NULL,          -- Foundation being checked
  bb_constituent_id TEXT NOT NULL,          -- RE NXT person with connection
  bb_constituent_name TEXT,
  funder_person_name TEXT,                  -- Decision-maker at foundation
  funder_person_role TEXT,                  -- Board member, CEO, Program Officer
  connection_type TEXT NOT NULL
    CHECK (connection_type IN ('direct', 'employer', 'shared_org', 'family', 'past')),
  connection_strength INTEGER               -- 1-5 scale
    CHECK (connection_strength BETWEEN 1 AND 5),
  connection_path TEXT,                     -- Human-readable path description
  match_confidence DECIMAL(5,2),
  last_verified_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(organization_id, kindora_funder_id, bb_constituent_id, funder_person_name)
);

-- Indexes
CREATE INDEX idx_bb_integrations_org ON client.blackbaud_integrations(organization_id);
CREATE INDEX idx_bb_mappings_org ON client.blackbaud_constituent_mappings(organization_id);
CREATE INDEX idx_bb_mappings_funder ON client.blackbaud_constituent_mappings(kindora_funder_id);
CREATE INDEX idx_bb_mappings_bb_id ON client.blackbaud_constituent_mappings(bb_constituent_id);
CREATE INDEX idx_bb_gifts_org ON client.blackbaud_gift_history(organization_id);
CREATE INDEX idx_bb_gifts_funder ON client.blackbaud_gift_history(kindora_funder_id);
CREATE INDEX idx_bb_sync_org ON client.blackbaud_sync_history(organization_id);
CREATE INDEX idx_bb_relationships_org_funder ON client.blackbaud_relationship_matches(organization_id, kindora_funder_id);
```

### RLS Policies Required

```sql
-- All tables: organization-scoped access
ALTER TABLE client.blackbaud_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE client.blackbaud_constituent_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE client.blackbaud_gift_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE client.blackbaud_sync_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE client.blackbaud_relationship_matches ENABLE ROW LEVEL SECURITY;

-- Grant permissions
GRANT USAGE ON SCHEMA client TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON client.blackbaud_integrations TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON client.blackbaud_constituent_mappings TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON client.blackbaud_gift_history TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON client.blackbaud_sync_history TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON client.blackbaud_relationship_matches TO authenticated;
```

---

## 8. File Structure

### Backend (kindora-api/python_api/)

```
services/blackbaud/
  __init__.py
  client.py                          # OAuth client, token management, API wrapper
  constituent_service.py             # Import/search foundation constituents (3-tier matching)
  promotion_service.py               # Promote matched constituents to funder_evaluations pipeline
  push_service.py                    # Push Kindora matches → RE NXT (constituent + opportunity + note)
  gift_service.py                    # Import gift/grant history from RE NXT
  officer_extraction_service.py      # Extract decision-makers from IRS 990 Part VII + enrichment data
  relationship_fetch_service.py      # Fetch RE NXT constituent relationships
  relationship_matching_service.py   # Cross-reference 990 officers × RE NXT relationships
  exceptions.py                      # Custom exceptions (TokenExpired, RateLimited, etc.)
  constants.py                       # API URLs, endpoints, rate limits

api/routes/
  blackbaud.py                       # All endpoints: OAuth, sync, gifts, push, relationships, add-in
                                     # 3 routers: main (16 routes), callback (1), addin (1)

tasks/
  blackbaud_tasks.py                 # Celery tasks: sync, gift import, relationship scan

repositories/
  blackbaud_repository.py            # Full CRUD for all 5 BB tables + gift/relationship methods

tests/
  test_blackbaud_client.py                      # 46 tests (OAuth, encryption, refresh, retry)
  test_blackbaud_promotion_service.py           # 14 tests
  test_blackbaud_routes.py                      # 5 tests (promote + import-summary + push-status)
  test_blackbaud_gift_service.py                # 11 tests
  test_blackbaud_push_service.py                # 16 tests (incl. duplicate push prevention)
  test_blackbaud_officer_extraction.py          # 36 tests
  test_blackbaud_relationship_fetch_service.py  # 15 tests
  test_blackbaud_relationship_matching.py       # 30 tests
  test_blackbaud_addin.py                       # 12 tests
```

### Frontend (kindora-app/src/)

```
app/addin/
  layout.tsx                         # Minimal layout (no Kindora chrome — iframe-safe)
  blackbaud-tile/
    page.tsx                         # SKY Add-in tile page (AddinClient, API key auth, intelligence card)

app/dashboard/settings/
  page.tsx                           # Settings page with Integrations tab (Blackbaud card + import summary)

components/settings/
  BlackbaudImportSummary.tsx         # Import stats (matched/unmatched/promoted) + "Add to My Funders" button

components/dashboard/funder/
  GiftHistorySection.tsx             # RE NXT gift history timeline on funder detail page
  AddToRENXTButton.tsx               # "Add to RE NXT" / "In RE NXT" button
  WhoDoYouKnowSection.tsx            # Relationship connections display with strength dots

hooks/
  useBlackbaudIntegration.ts         # All BB hooks: status, import summary, gifts, push, relationships, scan

services/
  blackbaudService.ts                # API client: all BB endpoint methods with TypeScript interfaces

e2e/
  blackbaud-integration.spec.ts      # Playwright E2E tests: 15 tests across 4 describe blocks
```

---

## 9. Security & Token Management

### Token Encryption

```python
from cryptography.fernet import Fernet

# Key from environment variable (generate once, store securely)
BLACKBAUD_ENCRYPTION_KEY = os.environ["BLACKBAUD_ENCRYPTION_KEY"]
fernet = Fernet(BLACKBAUD_ENCRYPTION_KEY)

def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode()).decode()
```

### Environment Variables (New)

```bash
# kindora-api/.env
BLACKBAUD_CLIENT_ID=<from developer portal>
BLACKBAUD_CLIENT_SECRET=<from developer portal>
BLACKBAUD_SUBSCRIPTION_KEY=d4ef4001d79142928cd1a998a50551be
BLACKBAUD_SUBSCRIPTION_KEY_SECONDARY=5d1a9545a9e246ae8e5dd04e12685a15
BLACKBAUD_REDIRECT_URI=https://kindora.co/api/integrations/blackbaud/callback
BLACKBAUD_ENCRYPTION_KEY=<generate with Fernet.generate_key()>
```

### Security Checklist

- [x] Tokens encrypted at rest (Fernet symmetric encryption)
- [x] State parameter includes CSRF nonce (verified on callback)
- [x] Refresh tokens rotated on each use
- [x] Disconnection revokes tokens on Blackbaud side
- [x] All endpoints require org membership verification
- [x] Subscription key NOT exposed to frontend
- [x] RLS policies enforce org-level isolation
- [x] Token expiry tracked and proactively refreshed
- [x] Add-in API key stored as SHA-256 hash (plaintext shown once)
- [x] CORS restricted to `*.blackbaud.com` and `*.blackbaud-dev.com`
- [x] Internal error details stripped from HTTP responses (QA PR-001)

---

## 10. Rate Limits & Error Handling

### Rate Limit Strategy

| Scenario | Approach |
|---|---|
| Normal operations (single API calls) | No throttling needed |
| Batch import (100+ constituents) | Queue via Celery, 8 calls/sec with backoff |
| Bulk relationship scan | Batch 50 names at a time, 5-second intervals |
| Daily sync | Run at off-peak hours (2-4 AM ET) |

### Error Categories & Handling

```python
class BlackbaudAPIError(Exception):
    """Base error for Blackbaud API calls"""

class TokenExpiredError(BlackbaudAPIError):
    """Access token expired — attempt refresh"""

class TokenRevokedError(BlackbaudAPIError):
    """Refresh token invalid — user must reconnect"""

class RateLimitedError(BlackbaudAPIError):
    """429 response — back off and retry"""

class BlackbaudServerError(BlackbaudAPIError):
    """5xx response — retry with exponential backoff"""

class ConstituentNotFoundError(BlackbaudAPIError):
    """404 for constituent — may have been deleted in RE NXT"""
```

### Retry Strategy

```python
# Exponential backoff: 1s, 2s, 4s, 8s, 16s (max 5 retries)
# 429 responses: wait for Retry-After header value
# 5xx responses: retry up to 3 times
# 401 responses: attempt token refresh once, then fail
```

---

## 11. Testing Strategy

### Sandbox Testing

**Test Environment:** SKY Developer Cohort (Grantmaking)
- **Environment ID:** `p-vnVAbDtfu0GyMqSDmG-_qw`
- **URL:** `https://host.nxt.blackbaud.com/gmk/dashboard?envid=p-vnVAbDtfu0GyMqSDmG-_qw`
- **Module:** Grantmaking (includes constituent management)
- Full read/write access for development and integration testing

**Local Testing Prerequisites:**
1. Redis running (`brew services start redis`)
2. API on port 8001 (`cd kindora-api/python_api && uvicorn main:app --reload --port 8001`)
   - Port 8000 may be occupied by MCP server; port 8001 is registered as alternate redirect URI
3. Frontend on port 3000 (`cd kindora-app && npm run dev`) with `NEXT_PUBLIC_API_URL=http://localhost:8001`
4. `BLACKBAUD_REDIRECT_URI=http://localhost:8001/api/integrations/blackbaud/callback`
5. Logged into Blackbaud in browser (same account as developer portal)

**Port Gotcha:** Port 8000 is used by workspace-mcp server. Use port 8001 for local API testing. Both ports 8000 and 8001 are registered as redirect URIs in the SKY Developer Portal.

### Unit Tests (139 total across 9 test files)

| Test File | Tests | Coverage |
|---|---|---|
| `test_blackbaud_client.py` | 46 | OAuth flow, token encryption, refresh, retry logic, rate limiting |
| `test_blackbaud_officer_extraction.py` | 36 | 990 officer parsing, name normalization, role priority, dedup |
| `test_blackbaud_relationship_matching.py` | 30 | Cross-reference matching, connection classification, strength scoring |
| `test_blackbaud_relationship_fetch_service.py` | 15 | RE NXT relationship fetch, pagination, name normalization |
| `test_blackbaud_promotion_service.py` | 14 | Promotion dedup, funder type mapping, canonical FK columns |
| `test_blackbaud_push_service.py` | 16 | Push to RE NXT, duplicate prevention (imported + pushed), payload building |
| `test_blackbaud_addin.py` | 12 | API key generation, constituent lookup, CORS, error states |
| `test_blackbaud_gift_service.py` | 11 | Gift import, upsert, field mapping, pagination |
| `test_blackbaud_routes.py` | 5 | Promote endpoint, import summary, push status (route-level) |

Run all Blackbaud tests:
```bash
cd kindora-api/python_api
pytest tests/test_blackbaud*.py -v
```

### E2E Tests (Playwright)

**File:** `kindora-app/e2e/blackbaud-integration.spec.ts`

15 tests across 4 describe blocks covering all integration features:

| # | Test | What It Verifies |
|---|---|---|
| 01 | Settings page loads Integrations tab | Tab navigation, Blackbaud section renders |
| 02 | Shows connection status badge | Connected/Disconnected badge displays correctly |
| 03 | Shows sync history table | Sync records visible with timestamps and counts |
| 04 | Shows import summary stats | Total/Matched/Unmatched/Pipeline counts |
| 05 | Disconnect dialog appears | Confirmation dialog when clicking Disconnect |
| 06 | Trigger sync shows feedback | Loading state, success toast after sync |
| 07 | Funder detail page has Blackbaud sections | GiftHistorySection + WhoDoYouKnowSection + AddToRENXTButton render |
| 08 | Gift history section renders | Summary stats, expandable gift list |
| 09 | Who Do You Know section renders | Connection cards with strength dots |
| 10 | Add to RE NXT button appears | Button or "In RE NXT" badge visible |
| 11 | Push to RE NXT works | Click button, verify status change |
| 12 | SKY Add-in tile renders no-key state | Shows "Configuration Required" without API key |
| 13 | SKY Add-in tile renders error state | Handles API errors gracefully |
| 14 | API health endpoint responds | `/api/health` returns alive status |
| 15 | Blackbaud status endpoint responds | `/api/integrations/blackbaud/status` returns valid JSON |

**Running E2E tests:**

```bash
# Default (Outdoorithm org — tests gracefully skip Blackbaud-connected features)
cd kindora-app
npx playwright test e2e/blackbaud-integration.spec.ts --project=chromium --no-deps

# Full integration test (Kindora org with active Blackbaud connection)
KINDORA_EMAIL=justin+test@kindora.co KINDORA_PASSWORD=<password> \
  npx playwright test e2e/blackbaud-integration.spec.ts --project=chromium --no-deps
```

**Design note:** Tests are designed to work in two modes:
- **Disconnected mode** (default): Tests 02-06, 08-11 gracefully skip when Blackbaud isn't connected on the test org
- **Connected mode** (via env vars): Full integration testing against an org with active Blackbaud connection

### Test Categories Summary

| Category | Count | Tools | Status |
|---|---|---|---|
| **Unit tests** | 139 | pytest + mocks | All passing |
| **E2E tests** | 15 | Playwright | 6 pass / 9 skip (disconnected mode) |
| **Live integration** | Manual | Sandbox API | OAuth, sync, matching all verified |
| **QA audit** | 15 issues | Manual review | All CRITICAL/HIGH fixed |

---

## 12. API Endpoint Reference

All Blackbaud endpoints live under `/api/integrations/blackbaud/`.

### Authenticated Endpoints (Supabase JWT + org membership)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/connect` | Initiate OAuth flow — returns `redirect_url` to Blackbaud authorization |
| GET | `/status` | Integration status, mapping summary, 5 most recent syncs |
| DELETE | `/disconnect` | Clear tokens, mark integration as disconnected |
| POST | `/sync` | Queue constituent import task (returns `sync_id`) |
| GET | `/sync/history` | List sync history records (paginated, newest first) |
| GET | `/mappings` | List constituent mappings (paginated with `limit`/`offset`) |
| POST | `/promote` | Promote matched un-promoted constituents to `funder_evaluations` pipeline |
| GET | `/import-summary` | Aggregate import stats: total/matched/unmatched/promoted/not_yet_promoted |
| POST | `/push/{funder_evaluation_id}` | Push funder to RE NXT (creates constituent + opportunity + note) |
| GET | `/push-status/{funder_evaluation_id}` | Check if funder is in RE NXT (returns `pushed` bool + BB IDs) |
| POST | `/gifts/sync` | Queue gift history import task |
| GET | `/gifts/summary` | Org-wide gift aggregate: total_gifts, total_amount, unique_funders |
| GET | `/gifts/{funder_id}` | Gift history + summary for a specific funder |
| POST | `/relationships/scan` | Queue relationship cross-reference scan (optional `funder_ein` scope) |
| GET | `/relationships/{funder_ein}` | Stored relationship matches sorted by connection_strength DESC |
| POST | `/addin/generate-key` | Generate per-org API key for SKY Add-in tile (hashed in DB) |

### Public Endpoints (no JWT)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/callback` | OAuth state nonce | OAuth redirect — exchanges code for tokens, redirects to frontend |
| GET | `/addin/constituent/{bb_constituent_id}` | `X-Blackbaud-Addin-Key` header | SKY Add-in tile data — returns funder intelligence for a constituent |

### Frontend React Query Hooks

All hooks defined in `kindora-app/src/hooks/useBlackbaudIntegration.ts`:

| Hook | Type | Key |
|------|------|-----|
| `useBlackbaudStatus` | Query | `blackbaud-status` |
| `useBlackbaudSyncHistory` | Query | `blackbaud-sync-history` |
| `useBlackbaudImportSummary` | Query | `blackbaud-import-summary` |
| `useBlackbaudGiftHistory` | Query | `blackbaud-gifts` |
| `useBlackbaudPushStatus` | Query | `blackbaud-push-status` |
| `useBlackbaudRelationships` | Query | `blackbaud-relationships` |
| `useBlackbaudIntegrationStatus` | Query | `blackbaud-integration-status` (lightweight) |
| `useBlackbaudConnect` | Mutation | — |
| `useBlackbaudDisconnect` | Mutation | Invalidates `blackbaud-status` |
| `useBlackbaudSync` | Mutation | Invalidates `blackbaud-status`, `sync-history` |
| `usePromoteBlackbaudFunders` | Mutation | Invalidates `import-summary`, `funders` |
| `useBlackbaudPushFunder` | Mutation | Invalidates `push-status`, `funders` |
| `useScanRelationships` | Mutation | Invalidates `blackbaud-relationships` |

---

## 13. Timeline & Milestones

### Phase 1: Foundation (Feb 2026) — COMPLETE

| Date | Deliverable |
|---|---|
| Feb 6 | All Phase 1 stories complete (8/8) — OAuth, import, matching, UI |
| Feb 6 | QA audit complete — 3 high issues fixed, 9 medium documented |
| Mar 7 | Live testing against SKY Developer Cohort — all flows passed |
| **Feb 6** | **Phase 1 Complete** |

### Phase 2: Value Bridge + Gift History + Push (Mar 7-8, 2026) — COMPLETE

| Date | Deliverable |
|---|---|
| Mar 7 | US-001–003: Promotion service + migration + API endpoints |
| Mar 7 | US-004: Frontend badge + import summary component |
| Mar 7 | US-005–006: Gift history import service + Celery task + API endpoints |
| Mar 7 | US-007: Gift history display on funder detail page |
| Mar 7 | US-008: Push-to-RE NXT service |
| Mar 8 | US-009: "Add to RE NXT" button + push status UI |
| **Mar 8** | **Phase 2 Complete** |

### Phase 3: Relationship Mapping (Mar 8, 2026) — COMPLETE

| Date | Deliverable |
|---|---|
| Mar 8 | US-010: 990 officer extraction service (36 tests) |
| Mar 8 | US-011: RE NXT relationship fetch service (15 tests) |
| Mar 8 | US-012: Cross-reference matching engine (30 tests) |
| Mar 8 | US-013: Relationship scan task + API endpoints |
| Mar 8 | US-014: "Who Do You Know?" UI on funder detail page |
| **Mar 8** | **Phase 3 Complete** |

### Phase 4: SKY Add-in (Mar 8, 2026) — COMPLETE

| Date | Deliverable |
|---|---|
| Mar 8 | US-015: Add-in backend (API key auth, CORS, data endpoint, 12 tests) |
| Mar 8 | US-016: Add-in tile frontend (AddinClient, intelligence card, middleware bypass) |
| Mar 8 | US-017: Documentation (registration guide, API key flow, dev plan v2.0) |
| **Mar 8** | **Phase 4 Complete (code)** — portal registration is a manual step |

### Key Event Alignment (Updated)

| Date | Event | Integration State |
|---|---|---|
| **Mar 3** | BB Dev Days speaker submission deadline | Phase 1 complete (demo OAuth + import) |
| **Mar 8** | All phases code-complete + QA + deployed | Full integration suite in production |
| **Jun 2–4** | BB Dev Days | Demo all 4 phases live |
| **Jul–Aug** | Marketplace listing submission | All phases working + tested |
| **Sep** | Startup Showcase (Charleston) | Full integration demo |
| **Sep 29–Oct 1** | BB Con (Columbus) | Marketplace live, all phases |

---

## 14. Deprioritized Integrations

These integrations were evaluated and deprioritized for the initial build:

| Integration | Reason | Revisit When |
|---|---|---|
| **Pipeline bidirectional sync** | Different stage models in RE NXT vs Kindora; bidirectional sync is fragile | After Phase 2, if users request it |
| **Action/interaction logging** | Low-value duplication; users already log in RE NXT | After Phase 3, as part of activity feed |
| **Blackbaud Grantmaking** | Wrong side of market (grantmakers, not seekers) | If/when Kindora adds grantmaker features |
| **Real-time webhooks from RE NXT** | Blackbaud webhook infrastructure is limited; polling is simpler | When user base exceeds 1000 connected orgs |
| **Corporate impact (YourCause)** | Different product line, different API | After RE NXT integration is proven |
| **Full constituent sync** | Most RE NXT constituents are individual donors, not funders | Only import org-type constituents (foundations) |

---

## 15. Blackbaud Platform Prerequisites

### What Justin Needs to Do Manually in Blackbaud Developer Portal

#### Step 1: Register a SKY API Application
1. Go to https://developer.blackbaud.com/apps/
2. Click "Add" to create a new application
3. Fill in:
   - **Application name:** `Kindora`
   - **Application details/description:** `AI-powered funder intelligence for Raiser's Edge NXT`
   - **Organization name:** `Kindora PBC`
   - **Application website URL:** `https://kindora.co`
4. Save and note the generated:
   - **Application ID** (this is the OAuth `client_id`)
   - **Application Secret** (this is the OAuth `client_secret`)

#### Step 2: Configure Redirect URIs
1. In the application settings, add redirect URIs:
   - Production: `https://kindora.co/api/integrations/blackbaud/callback`
   - Local dev: `http://localhost:8000/api/integrations/blackbaud/callback`

#### Step 3: Connect to Test Environment
1. Access SKY Developer Cohort environment (Grantmaking module)
2. **Environment ID:** `p-vnVAbDtfu0GyMqSDmG-_qw`
3. **URL:** `https://host.nxt.blackbaud.com/gmk/dashboard?envid=p-vnVAbDtfu0GyMqSDmG-_qw`
4. Login via Blackbaud SSO (same account as developer portal)
5. Test API access with sandbox credentials

#### Step 4: Verify API Subscription
1. Go to https://developer.blackbaud.com/subscriptions/
2. Confirm Standard tier subscription is active
3. Note both primary and secondary keys (already captured above)

#### After These Steps
Provide the following values so they can be added to environment configuration:
- `BLACKBAUD_CLIENT_ID` (Application ID)
- `BLACKBAUD_CLIENT_SECRET` (Application Secret)
- Sandbox environment details

---

## 16. Progress Log

Track implementation progress here. Update as work is completed.

| Date | Phase | What Was Done | Status |
|---|---|---|---|
| 2026-02-06 | Planning | Development plan created | Complete |
| 2026-02-06 | Phase 1 | Blackbaud credentials registered, env vars configured, Ralph loop set up | Complete |
| 2026-02-06 | Phase 1 | US-001: Database migration (5 tables, RLS, grants) — applied to staging + production | Complete |
| 2026-02-06 | Phase 1 | US-002: BlackbaudOAuthClient service (OAuth flow, token encryption, API wrapper) | Complete |
| 2026-02-06 | Phase 1 | US-003: API routes (connect, callback, status, disconnect, sync, mappings) | Complete |
| 2026-02-06 | Phase 1 | US-004: BlackbaudRepository data access layer (CRUD for all 4 tables) | Complete |
| 2026-02-06 | Phase 1 | US-005: Constituent import service (3-tier matching: EIN, name+state, name-only) | Complete |
| 2026-02-06 | Phase 1 | US-006: Celery background tasks (sync, token refresh, scheduled refresh) | Complete |
| 2026-02-06 | Phase 1 | US-007: Frontend Settings > Integrations page (connect, sync, history, disconnect) | Complete |
| 2026-02-06 | Phase 1 | US-008: Full verification — backend imports, frontend build, type safety audit | Complete |
| 2026-02-06 | Phase 1 | **PHASE 1 COMPLETE** — All 8 stories done in 8 Ralph iterations (blackbaud-phase1 loop) | Complete |
| 2026-02-06 | QA | PR-001: Security audit — removed internal error details from 6 HTTP responses | Complete |
| 2026-02-06 | QA | PR-002: Multi-tenancy audit — all queries org-scoped, RLS verified, no violations | Complete |
| 2026-02-06 | QA | PR-003: Error handling audit — fixed duplicate sync history records | Complete |
| 2026-02-06 | QA | PR-004: Frontend audit — added error state handling for integration status API failures | Complete |
| 2026-02-06 | QA | PR-005: Backend pattern compliance — all patterns correct, no violations | Complete |
| 2026-02-06 | QA | PR-006: Final verification — backend imports, frontend build, staging DB all pass | Complete |
| 2026-02-06 | QA | **QA COMPLETE** — 3 High issues fixed, 9 Medium documented, 2 Low documented. Phase 1 production ready. | Complete |
| 2026-03-07 | Testing | SKY Developer Portal audit: app approved (3/3/2026), redirect URIs correct, API quota upgraded to 100k/day | Complete |
| 2026-03-07 | Testing | Fixed BLACKBAUD_REDIRECT_URI in .env (was port 8001, corrected to 8000 to match portal registration) | Complete |
| 2026-03-07 | Testing | Updated constants.py MAX_REQUESTS_PER_DAY from 25k to 100k to match approved quota | Complete |
| 2026-03-07 | Testing | RE NXT test environment confirmed: SKY Developer Cohort (envid=p-vnVAbDtfu0GyMqSDmG-_qw) | Complete |
| 2026-03-07 | Testing | Fixed Redis connection pool crash on macOS — TCP keepalive socket options (TCP_KEEPIDLE etc.) don't exist on macOS, causing silent `client=None`. Platform-gated to Linux-only in `redis_cache.py` | Complete |
| 2026-03-07 | Testing | Added `http://localhost:8001` redirect URI to SKY Developer Portal (port 8000 occupied by workspace-mcp) | Complete |
| 2026-03-07 | Testing | **OAuth flow PASSED** — full authorization code flow against SKY Developer Cohort. State nonce stored/verified in Redis, tokens exchanged and encrypted in DB | Complete |
| 2026-03-07 | Testing | **API calls PASSED** — fetched constituents from SKY Developer Cohort (162k test records). Auth headers + subscription key working | Complete |
| 2026-03-07 | Testing | Test env limitation: SKY Developer Cohort only has Individual-type constituents (no Organizations). Constituent import sync would return 0 matches. Real org-type data requires a connected RE NXT production environment | Documented |
| 2026-03-07 | Testing | Integration record created: id=`bc5f47ee-9fdb-4a48-a6b3-d03b4d0c2bc2`, env=`SKY Developer Cohort Environment 1`, status=`active` | Complete |
| 2026-03-07 | Testing | **Constituent matching PASSED** — 3-tier matching verified: EIN exact (Gates Foundation, confidence 1.0), name+state (Ford Foundation, confidence 0.95), unmatched (fake name correctly stored) | Complete |
| 2026-03-07 | Testing | **All 7 API endpoints PASSED** — status, mappings, sync/history, sync trigger, connect, disconnect. Pagination, counts, and response shapes all correct | Complete |
| 2026-03-07 | Testing | **Auth guards PASSED** — wrong org → 403, no auth → 401, invalid UUID → 400, sync while disconnected → 400 | Complete |
| 2026-03-07 | Testing | **Disconnect + reconnect PASSED** — disconnect clears tokens, status → disconnected. Reconnect uses UPDATE path (not INSERT), tokens refreshed, status → active | Complete |
| 2026-03-07 | Testing | **Token refresh PASSED** — explicit refresh_access_token() obtained new token from Blackbaud, updated encrypted tokens and expiry in DB | Complete |
| 2026-03-07 | Testing | **46 unit tests PASSED** — all test_blackbaud_client.py tests pass (encryption, OAuth, refresh, retry, matching, pagination, sync tracking) | Complete |
| 2026-03-07 | Testing | Test data cleaned up: 3 test mappings + 2 sync records deleted, integration kept active | Complete |
| 2026-03-07 | Testing | **PHASE 1 LIVE TESTING COMPLETE** — All flows verified against SKY Developer Cohort. Integration production-ready. | Complete |
| 2026-03-07 | Audit | **Value delivery audit** — Cross-referenced against original strategy doc (`local-files/docs/Kindora/Kindora_Blackbaud_Strategy.md`). See "Production Readiness Gap Analysis" section below. | Complete |

### Production Readiness Gap Analysis (March 7, 2026) — ALL GAPS CLOSED

Cross-referencing the original Blackbaud Strategy (Jan 2026, v2.0) against what's built.

**Strategy Vision vs. Current Reality:**

The strategy defines Kindora as an "intelligence layer on top of RE NXT." All 8 gaps identified during the March 7 audit have been resolved by the Phase 2-4 build (March 7-8).

| # | Gap | Resolution | Status |
|---|---|---|---|
| G-1 | **Matched funders don't auto-add to prospect list** | `BlackbaudPromotionService` auto-promotes after sync; also manual via `POST /promote` | CLOSED (US-001, US-003) |
| G-2 | **No "imported from Blackbaud" indicator** | `blackbaud_import` badge on prospect cards via `PROSPECT_SUBCATEGORY_CONFIG` | CLOSED (US-004) |
| G-3 | **Mappings endpoint not wired to UI** | `BlackbaudImportSummary` component shows stats + "Add to My Funders" button | CLOSED (US-004) |
| G-4 | **No post-sync enrichment trigger** | Funders promoted as `evaluation_status='not_requested'`; users enrich via existing pipeline UI | CLOSED (by design) |
| G-5 | **No "Add to RE NXT" push-back** | `BlackbaudPushService` creates constituent + opportunity + note in RE NXT | CLOSED (US-008, US-009) |
| G-6 | **No gift history import** | `BlackbaudGiftService` imports gifts for all matched constituents | CLOSED (US-005, US-006, US-007) |
| G-7 | **No "Who Do You Know?" relationship mapping** | Full 3-service pipeline: officer extraction → relationship fetch → cross-reference matching | CLOSED (US-010 through US-014) |
| G-8 | **No SKY Add-in tile** | Tile page at `/addin/blackbaud-tile` with `AddinClient` integration + per-org API key auth | CLOSED (US-015, US-016, US-017) |

### Phase 1 Build Summary

**Ralph Loop:** `.ralph/blackbaud-phase1/` — 8 iterations, 8/8 stories complete
**Completed:** February 6, 2026 at 10:29 PM PST

**What was built:**

| Layer | Files Created | Key Deliverables |
|---|---|---|
| **Database** | 1 migration | 5 tables with RLS + grants in `client` schema (staging + production) |
| **Backend Services** | 4 files | OAuth client (Fernet encryption, auto-refresh), constituent import (3-tier matching), exceptions, constants |
| **Backend Routes** | 1 file | 7 endpoints: connect, callback, status, disconnect, sync, history, mappings |
| **Backend Repository** | 1 file | Full CRUD for all 4 Blackbaud tables with pagination |
| **Backend Tasks** | 1 file | 3 Celery tasks: sync, token refresh, scheduled refresh (every 45 min) |
| **Frontend Service** | 1 file | TypeScript API client with full type interfaces |
| **Frontend Hooks** | 1 file | React Query hooks for status, history, connect, disconnect, sync |
| **Frontend UI** | 1 file modified | Settings page "Integrations" tab with full connect/disconnect/sync UI |
| **Config** | 1 file modified | 8 BLACKBAUD_* env vars added to `core/config.py` Settings class |

**Quality gates passed:**
- Backend: All modules import successfully
- Frontend: `npm run build` — 0 TypeScript errors, 113 pages compiled
- No `as any` bypasses
- Proper Python type hints throughout

### Phase 1 QA Summary

**Ralph Loop:** `.ralph/blackbaud-phase1-qa/` — 6 evaluations, 6/6 complete
**Completed:** February 6, 2026

**Issues Found and Fixed (Critical/High):**

| ID | Severity | Fix | Commit |
|---|---|---|---|
| H-001 | High | Removed `{e}` from 6 HTTPException detail fields — prevented leaking internal error details | `fix(blackbaud): [PR-001]` |
| H-002 | High | Eliminated duplicate sync_history records — task and service both created records independently | `fix(blackbaud): [PR-003]` |
| H-003 | High | Added error state banner for integration status API failures — previously silently showed "Disconnected" | `fix(blackbaud): [PR-004]` |

**Issues Documented (Medium/Low — no fix needed):**

| ID | Severity | Description |
|---|---|---|
| M-001 | Medium | Token exchange error log includes `response.text` (server-side only) |
| M-002 | Medium | `update_mapping` filters by PK only, not org_id (internal-only, RLS backup) |
| M-003 | Medium | `update_sync_record` filters by PK only, not org_id (internal-only, RLS backup) |
| M-004 | Medium | `trigger_sync` leaks integration status in error message to authenticated user |
| M-005 | Medium | No cleanup job for stuck in_progress sync records after Celery worker crash |
| M-006 | Medium | Non-ASCII characters stripped by regex, reducing match quality for non-English names |
| M-007 | Medium | Generic error messages in toasts (consistent with codebase pattern) |
| M-008 | Medium | OAuth callback toast repeats on page refresh (minor UX) |
| M-009 | Medium | Potential sync record race if two concurrent syncs fire (low probability) |
| L-001 | Low | Redundant `timedelta` imports inside functions instead of module top |
| L-002 | Low | OAuth error param not URL-encoded in redirect (safe per OAuth spec) |

**Final Verification:**
- `python -c "from main import app"` — PASS
- All Blackbaud module imports — PASS
- `npm run build` (kindora-app) — PASS (0 errors)
- Staging DB: 5 tables present with RLS enabled

### Phase 2-4 Build Summary

**Ralph Loop:** `.ralph/blackbaud-full/` — 17 stories (US-001 through US-017), all complete
**Completed:** March 8, 2026

#### Phase 1 Completion: The Value Bridge (US-001 through US-004)

| Date | Story | What Was Done |
|---|---|---|
| 2026-03-07 | US-001 | `BlackbaudPromotionService` — promotes matched constituents to `funder_evaluations` pipeline (dedup, 3 funder types, paginated, 14 unit tests) |
| 2026-03-07 | US-002 | DB migration: `promoted_at`, `promoted_evaluation_id` columns + 2 indexes on `blackbaud_constituent_mappings` (staging + production) |
| 2026-03-07 | US-003 | Wired promotion into sync flow (auto-promote after import), added `POST /promote` + `GET /import-summary` + enhanced `GET /status` (5 tests) |
| 2026-03-07 | US-004 | Frontend: `blackbaud_import` badge on prospect cards, `BlackbaudImportSummary` component on settings page, React Query hooks with invalidation |

#### Phase 2: Gift History + Push to RE NXT (US-005 through US-009)

| Date | Story | What Was Done |
|---|---|---|
| 2026-03-07 | US-005 | `BlackbaudGiftService` — imports gift history from RE NXT API (paginated, rate-limited, field mapping for amount/fund/campaign, 11 tests) |
| 2026-03-07 | US-006 | Celery task `import_blackbaud_gifts` + 3 API endpoints: `POST /gifts/sync`, `GET /gifts/summary`, `GET /gifts/{funder_id}` |
| 2026-03-07 | US-007 | `GiftHistorySection` component on funder detail page — summary stats, expandable gift timeline, self-gating on integration status |
| 2026-03-07 | US-008 | `BlackbaudPushService` — pushes funder to RE NXT (constituent + opportunity + note), 409 conflict handling, 13 tests |
| 2026-03-08 | US-009 | `AddToRENXTButton` component, `POST /push/{eval_id}` + `GET /push-status/{eval_id}` endpoints, React Query hooks |

#### Phase 3: "Who Do You Know?" Relationship Mapping (US-010 through US-014)

| Date | Story | What Was Done |
|---|---|---|
| 2026-03-08 | US-010 | `OfficerExtractionService` — extracts decision-makers from IRS 990 Part VII + enrichment data (name normalization, role priority, 36 tests) |
| 2026-03-08 | US-011 | `BlackbaudRelationshipFetchService` — fetches relationships from RE NXT API for all mapped constituents (15 tests) |
| 2026-03-08 | US-012 | `RelationshipMatchingService` — cross-references 990 officers × RE NXT relationships (direct/employer/shared_org/past, Jaccard ≥ 0.80, 30 tests) |
| 2026-03-08 | US-013 | Celery task `scan_blackbaud_relationships` + `POST /relationships/scan` + `GET /relationships/{funder_ein}` endpoints |
| 2026-03-08 | US-014 | `WhoDoYouKnowSection` component on funder detail page — connection cards with strength dots, type badges, expandable list |

#### Phase 4: SKY Add-in Tile (US-015 through US-017)

| Date | Story | What Was Done |
|---|---|---|
| 2026-03-08 | US-015 | Add-in backend: `addin_api_key` column migration, `POST /addin/generate-key`, `GET /addin/constituent/{id}`, CORS for Blackbaud domains, 12 tests |
| 2026-03-08 | US-016 | Add-in frontend: `page.tsx` at `/addin/blackbaud-tile`, `AddinClient` integration, inline-styled intelligence card (~300px), middleware bypass |
| 2026-03-08 | US-017 | Documentation: SKY Developer Portal registration guide, API key generation flow, dev plan v2.0 with all phases complete |

#### Full Build Statistics

| Metric | Count |
|---|---|
| **User stories completed** | 17 |
| **Backend services created** | 7 (OAuth client, constituent import, promotion, gift, push, officer extraction, relationship fetch + matching) |
| **API endpoints** | 18 total (16 authenticated + 1 OAuth callback + 1 add-in data) |
| **Celery tasks** | 5 (sync, gift import, relationship scan, token refresh, scheduled refresh) |
| **Frontend components** | 5 (BlackbaudImportSummary, GiftHistorySection, AddToRENXTButton, WhoDoYouKnowSection, SKY Add-in tile) |
| **React Query hooks** | 13 (7 queries + 6 mutations) |
| **DB migrations applied** | 3 (core tables, promotion tracking, add-in API key) |
| **Unit tests** | 139 across 9 test files |
| **E2E tests** | 15 (Playwright) |
| **TypeScript interfaces** | 14 (in blackbaudService.ts) |

#### Quality Gates

- All backend services import cleanly — PASS
- Frontend builds: `npm run build` — PASS (0 TypeScript errors)
- TypeScript strict mode: `npx tsc --noEmit` — PASS
- No `as any` bypasses in frontend code
- All queries scoped by `organization_id` (multi-tenancy verified)
- Proper schema usage: `supabase_public` for funder data, `supabase_client` for Blackbaud tables
- All 139 unit tests passing
- E2E tests: 6 pass / 9 skip (graceful skip in disconnected mode)
- Production deployment verified (both Vercel + Azure)

### Phase 2-4 QA Audit (March 8, 2026)

Post-build QA audit identified and fixed 13 issues. Commit: `a442f9b1`.

**Issues Fixed:**

| # | Severity | Fix |
|---|---|---|
| QA-001 | CRITICAL | Wrong import in `officer_extraction_service.py` (`core.supabase_clients` → `core.clients`) — would crash at runtime |
| QA-002 | CRITICAL | Imported mappings not counted as "already in RE NXT" — users could create duplicate constituents via push |
| QA-003 | HIGH | `push-status` endpoint only checked `pushed` direction — missed `imported` mappings (showed "Add to RE NXT" for funders already imported from RE NXT) |
| QA-004 | HIGH | Frontend `blackbaudService.ts` didn't normalize API response shapes — sync history and status fields mismatched between API and TypeScript interfaces |
| QA-005 | HIGH | `GiftHistorySection` and `WhoDoYouKnowSection` rendered `null` on API errors — now show error states |
| QA-006 | HIGH | Missing query invalidation after push mutation — funders list didn't refresh to show "In RE NXT" badge |
| QA-007 | MEDIUM | Addin tile: no `.catch()` on dynamic import of `@blackbaud/sky-addin-client` — unhandled promise rejection |
| QA-008 | MEDIUM | Addin tile: `useRef<any>` → typed ref (`useRef<{ destroy: () => void } | null>`) |
| QA-009 | MEDIUM | Promotion service dedup check didn't scope by `program_id` — cross-program false positives |
| QA-010 | MEDIUM | Missing `aria-expanded` and `aria-label` on gift/relationship expand/collapse buttons |
| QA-011 | MEDIUM | Missing FK constraint + index on `promoted_evaluation_id` column |
| QA-012 | LOW | Async test helper used deprecated `asyncio.get_event_loop()` — replaced with `asyncio.run()` for Python 3.12 |
| QA-013 | LOW | 3 new regression tests added for duplicate push prevention scenarios |

**Key behavioral change from QA:** The push service now considers an `imported` mapping as "already in RE NXT." If a funder was imported from RE NXT (via constituent sync), the `push-status` endpoint returns `pushed: true` with `push_direction: 'imported'`, and the frontend shows "In RE NXT" instead of "Add to RE NXT." This prevents users from accidentally creating duplicate constituent records in RE NXT for funders that were originally imported from there.

| 2026-03-08 | QA | **Phase 2-4 QA audit** — 13 issues found: 2 CRITICAL, 4 HIGH, 4 MEDIUM, 2 LOW, 1 regression test addition. All CRITICAL and HIGH fixed. See "Phase 2-4 QA Audit" section above. | Complete |
| 2026-03-08 | Deploy | **Frontend deployed to production** — Vercel `dpl_GFfsKzGryKVjAtuPXSniHyvLrmce`, aliased to `kindora.co` and `www.kindora.co` | Complete |
| 2026-03-08 | Deploy | **Backend deployed to production** — GitHub Actions run #22836437524, all 22 steps passed, Azure App Service restarted | Complete |
| 2026-03-08 | Deploy | **Production health verified** — `GET /api/health` returns `{"status":"alive"}` | Complete |
| 2026-03-08 | Testing | **E2E test suite created** — `blackbaud-integration.spec.ts` with 15 Playwright tests covering settings page, funder detail, SKY Add-in tile, and API endpoints | Complete |
| 2026-03-08 | Docs | **Dev plan updated to v3.0** — all gaps closed, QA audit documented, E2E tests added, deployment status confirmed | Complete |

### Remaining Manual Steps

| # | Step | Status | Notes |
|---|---|---|---|
| 1 | Register SKY Add-in in Developer Portal | NOT DONE | See "SKY Add-in Registration Guide" in Phase 4 section |
| 2 | Test tile in sandbox after registration | NOT DONE | Requires step 1 |
| 3 | Submit for Blackbaud Marketplace listing | NOT DONE | Target: Jul-Aug 2026 |

---

## References

- [SKY API Portal](https://developer.blackbaud.com/skyapi)
- [SKY API Authorization](https://developer.blackbaud.com/skyapi/docs/authorization)
- [Authorization Code Flow](https://developer.blackbaud.com/skyapi/docs/authorization/auth-code-flow)
- [RE NXT API Reference](https://developer.blackbaud.com/skyapi/products/renxt)
- [Constituent API](https://developer.blackbaud.com/skyapi/products/renxt/constituent)
- [SKY Add-ins Overview](https://developer.blackbaud.com/skyapi/docs/addins/overview)
- [SKY Add-in Client Library](https://github.com/blackbaud/sky-addin-client)
- [Blackbaud Marketplace Policies](https://developer.blackbaud.com/skyapi/partners/marketplace/policies)
- [Kindora Blackbaud Strategy Doc](../local-files/docs/Kindora_Blackbaud_Strategy.md)

---

*This document is the source of truth for Blackbaud integration development. Update the Progress Log as work is completed.*
