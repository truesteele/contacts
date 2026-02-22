# Custom People Search Scraper — Design Document

**Created:** 2026-02-21
**Status:** In Development
**Goal:** Replace Apify `one-api/skip-trace` ($0.007/result, 1 result) with a free, multi-result scraper

---

## 1. Problem

The current real estate enrichment pipeline (`scripts/intelligence/enrich_real_estate.py`) uses Apify's `one-api/skip-trace` actor to find home addresses. It has two critical limitations:

1. **Returns exactly 1 result per name** — no way to get multiple candidates
2. **49% rejection rate** — GPT-5 mini correctly rejects wrong-person results, but we have no fallback candidates

In the full batch of 551 contacts:
- 211 validated (38%)
- 340 rejected or no result (62%)
- Many rejections are likely the correct person at position 2-10 in the underlying database

## 2. Research Findings

### Sites Tested (2026-02-21)

| Site | Cloudflare? | curl_cffi Works? | Data Quality | Free Data |
|------|------------|-------------------|-------------|-----------|
| **411.com** | **None/Light** | **YES** | **Excellent** | **Name, age, full address, phones, relatives** |
| TruePeopleSearch | Heavy (Turnstile) | No | Excellent | Blocked |
| FastPeopleSearch | Heavy (Turnstile) | No | Excellent | Blocked |
| Nuwber | Heavy (Managed) | No | Best | Blocked |
| ThatsThem | Moderate | Partial (challenge) | Good | Blocked |

### 411.com Deep Dive

411.com (owned by Whitepages) is our primary target because:
- **No Cloudflare protection** — returns real data via standard HTTP requests
- **`curl_cffi` with Chrome TLS impersonation** bypasses any fingerprinting
- **Multiple candidates** per search (3+ results for most names)
- **Full address with ZIP code** on person detail pages
- **Age brackets, relatives, landline phones** — all free, in the HTML

#### Data Available (Free)

| Field | Availability | Example |
|-------|-------------|---------|
| Full name | Always | Adrian Martin Schurr |
| Age bracket | Always | 30s |
| Current city, state | Always | San Leandro, CA |
| **Full street address + ZIP** | **On detail page** | **1873 Wayne Ave, San Leandro, CA 94577** |
| Landline phones | On detail page | (650) 253-0000 |
| Relatives + ages + cities | On detail page | Rebecca Schnurr, 60s, Dublin CA |
| Previous addresses (city only) | On detail page | South San Francisco, CA |

#### Data Behind Paywall (Not Needed)

| Field | Status |
|-------|--------|
| Cell phone numbers | Masked ("NAY-PEEK") |
| Full previous addresses | Masked ("NOSHOW") |
| Background reports | Paywall |

### Anti-Scraping Measures

| Measure | 411.com | TruePeopleSearch | FastPeopleSearch |
|---------|---------|------------------|-----------------|
| Cloudflare | None/Light | Heavy (Turnstile) | Heavy (Turnstile) |
| TLS fingerprinting | None detected | Yes | Yes |
| US geo-restriction | No | Yes | Yes |
| TOS speedbump | Yes (JS overlay) | No | No |
| Rate limiting | Likely (untested) | Aggressive | Aggressive |

The TOS speedbump on 411.com is a JavaScript overlay (class `Speedbumps`) that blocks the UI but does NOT prevent the data from being in the HTML response. All data is server-rendered.

### Browser Automation Approaches Tested

| Approach | Result | Notes |
|----------|--------|-------|
| Camoufox (anti-detect Firefox) headless | Failed | Cloudflare Turnstile not solved |
| Camoufox visible | Failed | Same Cloudflare issue |
| nodriver (undetected Chrome) | Failed | Chrome connection issues on macOS |
| cloudscraper | Failed | Can't solve Turnstile |
| **curl_cffi (Chrome TLS impersonation)** | **SUCCESS for 411.com** | No browser needed! |

**Key insight:** For 411.com, we don't need a browser at all. Simple HTTP requests with TLS impersonation work perfectly.

### Tools Not Worth Pursuing

- **Camoufox/Playwright**: Overkill — 411.com doesn't need a browser
- **nodriver**: Chrome connection issues, unnecessary for 411.com
- **FlareSolverr**: Docker overhead for a problem that doesn't exist on 411.com
- **2Captcha/CapSolver**: Unnecessary — no CAPTCHAs on 411.com

---

## 3. Architecture

### Current Pipeline (Apify skip-trace)

```
Name + City/State → one-api/skip-trace → 1 result → GPT-5 mini validates → Zillow
                     $0.007/result         38% pass rate
```

### New Pipeline (411.com scraper)

```
Name + City/State → 411.com search → 3-10 candidates → 411.com detail pages → GPT-5 mini picks best
                     FREE              ~$0.003/validation                        → Zillow
```

### Flow

```
Step 1: Search 411.com/name/{First}-{Last}/{City}-{ST}
        → Get list of candidates (name, age, city)
        → Get person detail URLs (/person/{hash})

Step 2: For top N candidates, fetch detail pages
        → Get full address, ZIP, phones, relatives

Step 3: GPT-5 mini multi-candidate matching
        → Compare ALL candidates against LinkedIn profile
        → Pick best match or reject all

Step 4: Zillow autocomplete (unchanged)
Step 5: Zillow detail scraper (unchanged)
```

### URL Patterns

| Type | Pattern | Example |
|------|---------|---------|
| Search | `/name/{First}-{Last}/{City}-{ST}` | `/name/Adrian-Schurr/San-Francisco-CA` |
| Detail | `/person/{hex_hash}` | `/person/3431312d506279506d4c3135353330` |
| State search | `/person-search/{First}-{Last}/{ST}` | `/person-search/Adrian-Schurr/CA` |

### HTML Structure

**Search page:**
```
H1: "{Name} in {City}, {ST} — N people found"
For each result:
  H2: "{Full Name}" (parent: div.flex.flex-col.flex-grow)
  H3: "{City}, {ST}"
  A[href="/person/{hash}"]: "View Details"
  (Each person appears twice — desktop + mobile layout)
```

**Detail page:**
```
H1: "{Full Name} from {City}, {ST}"
  Age: "30s" (near H1)

H3 "Current Address":
  "1873 Wayne Ave"
  "San Leandro, CA 94577"

H3 "Landlines":
  "(650) 253-0000"
  "(510) 357-5245"

H3 "Cell Phones":
  "(510) NAY-PEEK" (masked — paywall)

H3 "Previous Addresses":
  "NOSHOW Lux Ave, South San Francisco, CA" (partially masked)

H3 "Relatives & Associates":
  "Rebecca Schnurr, Age 60s, in Dublin, CA"
  "Anay Martinez, Age 30s, in San Leandro, CA"
```

---

## 4. Technology

| Component | Choice | Rationale |
|-----------|--------|-----------|
| HTTP client | `curl_cffi` | Chrome TLS impersonation bypasses fingerprinting |
| Browser profile | `chrome131` | Latest stable Chrome fingerprint |
| HTML parser | `BeautifulSoup` | Robust, handles messy HTML |
| Session | `curl_cffi.requests.Session` | Cookie persistence across requests |
| Validation | GPT-5 mini | Multi-candidate matching against LinkedIn data |
| Rate limiting | 2-5 sec random delay | Prevent IP blocks |

### Dependencies

```
curl_cffi>=0.14     # TLS impersonation (Chrome, Safari, Firefox)
beautifulsoup4       # HTML parsing
openai               # GPT-5 mini validation
```

No browser automation libraries needed (Playwright, Selenium, etc.).

---

## 5. Cost Comparison

| Approach | Cost/Contact | 340 Rejected Contacts | 2,400 Full Run |
|----------|-------------|----------------------|----------------|
| Apify skip-trace (current) | $0.007 | Already spent | $16.80 |
| **411.com scraper (new)** | **$0.000** | **$0.00** | **$0.00** |
| GPT-5 mini multi-candidate validation | ~$0.005 | ~$1.70 | ~$12.00 |
| **Total new cost** | **~$0.005** | **~$1.70** | **~$12.00** |
| **Savings vs Apify** | | | **$4.80 saved** |

The real win isn't cost — it's **validation rate improvement**:
- Current: 38% (1 candidate, no fallback)
- Expected: 55-80% (multiple candidates, GPT picks best)

---

## 6. GPT-5 Mini Multi-Candidate Validation

### Prompt Design

Instead of validating 1 candidate at a time, the new prompt evaluates ALL candidates simultaneously:

```
Given these N candidates from 411.com for "{contact_name}":

Candidate 1: Adrian Martin Schurr, Age 30s, 1873 Wayne Ave, San Leandro, CA 94577
  Phones: (650) 253-0000, (510) 357-5245
  Relatives: Rebecca Schnurr (60s, Dublin CA), Anay Martinez (30s, San Leandro CA)

Candidate 2: Martin W Schurr, Age 60s, South San Francisco, CA
  ...

Candidate 3: Adrian Charles Scurry, Age 60s, San Francisco, CA
  ...

LinkedIn profile for the contact:
- Name: Adrian Schurr
- City: San Francisco, CA
- Company: [current employer]
- Schools: [education]

Which candidate (if any) is the correct match? Consider:
1. Name match (exact, middle name, nickname)
2. Location plausibility (Bay Area suburb is consistent with SF)
3. Age plausibility (30s matches early-career professional)
4. Relative names (any recognizable?)

Return JSON: {best_candidate_index, confidence, reasoning}
```

### Expected Improvement Factors

1. **Multiple candidates**: The right person is often in the results but not #1
2. **Relatives as signal**: If a relative's name matches known data, strong confirmation
3. **Age bracket validation**: 30s vs 60s immediately eliminates wrong-generation matches
4. **Simultaneous comparison**: GPT can compare candidates against each other, not just threshold

---

## 7. Risk Factors

| Risk | Mitigation |
|------|-----------|
| 411.com rate limiting | 2-5 sec delays, session rotation |
| TOS violations | Same legal gray area as one-api/skip-trace (scrapes same sites) |
| HTML structure changes | Robust CSS selectors with fallbacks, version detection |
| IP blocking | Residential proxy support (configurable) |
| Missing data | Fallback to Apify skip-trace for contacts 411.com can't find |

---

## 8. Implementation Plan

### Phase 1: Core Scraper — COMPLETE
- [x] Research & test multiple people search sites
- [x] Validate 411.com works with curl_cffi
- [x] Document HTML structure and data fields
- [x] Build `Scraper411` class with search + detail page parsing
- [x] Test with 5 known contacts (3/5 exact address match, 5/5 correct person found)
- [x] Validate multi-candidate GPT-5 mini matching (high confidence, correct picks)
- [x] Name cleaning (strip PhD, CFRE, JD, etc.)
- [x] State normalization (full names → 2-letter abbreviations, skip non-US)

### Phase 2: Pipeline Integration — COMPLETE
- [x] Add `skip_trace_411()` as drop-in replacement for `skip_trace_batch()`
- [x] Update `enrich_real_estate.py` with `--source 411` flag
- [x] Add `--retry-rejected` flag for re-processing previously failed contacts
- [x] Test full pipeline: 411.com → GPT match → Zillow (end-to-end working)
- [x] Validated on batch of 10 previously-rejected contacts (2/5 searched validated)

### Phase 3: Production Hardening
- [x] Rate limiting (2-5 sec random delays between requests)
- [x] Browser profile rotation (chrome131/136/124/120)
- [x] Rate-limit detection (429 → 30s backoff)
- [ ] Add proxy rotation support
- [ ] Add retry logic for transient failures
- [ ] Add caching (avoid re-scraping same person)
- [ ] Monitor for HTML structure changes

### Phase 4: Full Batch Run
- [ ] Run `--source 411 --retry-rejected` against all ~700 rejected contacts
- [ ] Measure improvement: previously 38% validation → expected 55-80%
- [ ] Optionally run against contacts with no real_estate_data at all

---

## 9. Test Results (2026-02-21)

### Known Contacts Test (5 contacts)
| Contact | Candidates | Correct Person? | Correct Address? |
|---------|-----------|----------------|-----------------|
| Adrian Schurr, SF, CA | 3 | YES (#1) | YES (1873 Wayne Ave) |
| Taj James, Oakland, CA | 1 | YES | Different address |
| Rob Gitin, SF, CA | 3 | YES (#1) | Different address |
| Jeff Kositsky, Denver, CO | 5 | YES (#1) | YES (749 S Grant St) |
| Trina Villanueva, Oakland, CA | 1 | YES | YES (4629 Mountain Blvd) |

### GPT-5 Mini Validation Test
- Adrian Schurr: Picked #1, high confidence (correct)
- Jeff Kositsky: Picked #1, high confidence (correct)

### Retry-Rejected Batch (10 contacts)
- 5 skipped (no US state/city)
- 2/5 validated (40% of searchable contacts) — these were ALL previously rejected by Apify
- 0 errors

---

## 10. Files

| File | Purpose |
|------|---------|
| `scripts/intelligence/people_search_scraper.py` | Core 411.com scraper + GPT-5 mini validation |
| `scripts/intelligence/enrich_real_estate.py` | Pipeline: 411.com/Apify → GPT → Zillow |
| `docs/CUSTOM_PEOPLE_SCRAPER.md` | This document |

## 11. Usage

```bash
# Search for a single person
python scripts/intelligence/people_search_scraper.py search "Adrian Schurr" "San Francisco, CA"

# Fetch a detail page
python scripts/intelligence/people_search_scraper.py detail /person/3431312d506279506d4c3135353330

# Run test suite (5 known contacts)
python scripts/intelligence/people_search_scraper.py test

# Full pipeline with 411.com (retry previously rejected)
python scripts/intelligence/enrich_real_estate.py --source 411 --retry-rejected --batch 50

# Full pipeline with 411.com (new contacts)
python scripts/intelligence/enrich_real_estate.py --source 411 --batch 50
```
