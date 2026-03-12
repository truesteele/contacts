# LinkedIn Email Scraper — Operations Guide

## Overview

Playwright-based scraper that visits LinkedIn `/overlay/contact-info/` pages to extract emails from connected profiles. Emails are classified as personal or work via GPT-5 mini and saved to the appropriate database fields.

Two account-specific scripts:
- **Justin:** `scripts/intelligence/discover_emails_justin.py` (targets `contacts` table, ranked by `ask_readiness` score)
- **Sally:** `scripts/intelligence/sally/discover_emails.py` Phase 3 (targets `sally_contacts` table, ranked by `ai_proximity_score`)

## Results (March 10, 2026)

### Justin — 3 batches

| Batch | Profiles | Found | Hit Rate | Time |
|-------|----------|-------|----------|------|
| 1     | 100      | 76    | 76%      | 50 min |
| 2     | 100      | 53    | 53%      | 50 min |
| 3     | 100      | 10    | 10%      | ~50 min |
| **Total** | **300** | **139** | **46%** | **~2.5 hr** |

- Email coverage: 89.5% → 94.2% (2,680 → 2,819 / 2,993)
- Personal emails: 738 → 843 (+105)
- Work emails: 1,220 → 1,276 (+56)
- Come Alive campaign: 98.5% → 99.4% (323 / 325 have email)

### Sally — Batch 1 (in progress)

- 100% hit rate on first 19 profiles (Sally's connections have higher email visibility)
- Remaining: ~571 contacts

## Safety Measures (per batch)

| Setting | Value | Rationale |
|---------|-------|-----------|
| Batch size | 100 profiles max | Hard cap per session |
| Delay between profiles | 8-15s (random) | Mimics human browsing speed |
| Distraction pause | 10% chance of extra 5-20s | Breaks up regular cadence |
| Session break | 3-8 min every 25 profiles | Simulates breaks |
| Feed browsing | Before scraping + during breaks | Makes session look natural |
| Human-like typing | 50-150ms per character at login | Defeats keystroke analysis |
| Random viewport | 1260-1380 x 850-950px | Varies fingerprint |
| Webdriver flag | Removed via init script | Basic anti-detection |
| Auth wall | Immediate abort | Protects account |
| Circuit breaker | 5 consecutive errors = stop | Catches rate limits early |
| Cookie persistence | `.linkedin_cookies_justin.json` / `.linkedin_cookies.json` | Avoids re-login |

## Critical Operational Rules

### 1. ONE batch per account per day — no exceptions

Running 3 batches (300 profiles) on Justin's account in one day triggered a LinkedIn warning:

> "We noticed activity from your account that indicates you might be using an automation tool."

Sally's account, running 1 batch per day, has not been flagged. The per-profile delays are identical — the difference is daily volume.

**Rule:** Max 100 profiles per account per 24-hour period. Wait at least 24 hours between batches.

### 2. Security checkpoint = heightened surveillance

If LinkedIn triggers a security checkpoint at login, the account is already under scrutiny. Every action after resolving the checkpoint is monitored more closely. On Justin's account, the checkpoint appeared on all 3 login attempts (the first 2 timed out before the user could complete them).

**Rule:** If you hit a checkpoint, consider that batch "hot" — do NOT run another batch for at least 48 hours on that account.

### 3. Cookie reuse eliminates login risk

After the first successful login, cookies are saved. Subsequent batches reuse the session without logging in again. This is important because:
- Login from a new Playwright browser is the highest-risk moment
- The checkpoint challenge itself is a detection signal
- Cookie reuse skips all login-related fingerprinting

**Rule:** Always let the script try cookie reuse first. Only force a fresh login if cookies are expired/stale.

### 4. Diminishing returns after batch 2

Hit rates drop sharply:
- Batch 1: 76% (highest-scored contacts, most likely to have visible email)
- Batch 2: 53%
- Batch 3: 10% (remaining contacts simply don't show email on LinkedIn)

After 200 profiles, most findable emails have been found. Batch 3 and beyond add marginal value at the cost of account risk.

**Rule:** Prioritize by ask_readiness score (the scripts already do this). Stop after 2 batches unless coverage gaps are critical.

### 5. Space batches across different times of day

Running at the same time every day creates a pattern. Vary the time of day for each batch.

## Commands

### Justin — Scrape missing emails
```bash
cd scripts/intelligence
source ../../.venv/bin/activate
python -u discover_emails_justin.py scrape \
  --linkedin-email "justinrsteele@gmail.com" \
  --linkedin-password 'PASSWORD' \
  --batch-size 100
```

### Justin — Classify campaign emails (personal/work)
```bash
python -u discover_emails_justin.py classify           # All campaign contacts
python -u discover_emails_justin.py classify --new-only # Only unclassified
python -u discover_emails_justin.py classify --dry-run  # Preview
```

### Sally — Scrape missing emails
```bash
cd scripts/intelligence
source ../../.venv/bin/activate
python -u sally/discover_emails.py --phase 3 \
  --linkedin-email "sally.steele@gmail.com" \
  --linkedin-password 'PASSWORD' \
  --batch-size 100
```

### Verify emails against Gmail threads (both accounts)
```bash
python -u verify_emails.py --dry-run --verbose  # Preview
python -u verify_emails.py --fix                 # Auto-fix mismatches
```

## Email Classification Logic

### Heuristic (instant, no API call)
- Gmail, Yahoo, Hotmail, Outlook, iCloud, AOL, Comcast, etc. → **personal**
- Everything else → needs LLM

### GPT-5 mini classification
- Company domain matches their employer → **work**
- `.edu` domains → **work** (academic)
- `.org` domains → usually **work**
- Vanity/personal-name domains → **personal**
- ISP domains → **personal**

### Database field mapping
- `personal` → saved to `personal_email` + `email` (if empty)
- `work` → saved to `work_email` + `email` (if empty)
- Uses `COALESCE` to never overwrite existing values

## Architecture

### Query ordering (Justin)
Contacts are scraped in priority order:
1. `ready_now` tier first (highest ask_readiness score descending)
2. `cultivate_first` tier
3. `long_term` tier
4. `not_a_fit` tier (lowest priority)

### Query ordering (Sally)
Contacts are scraped by `ai_proximity_score` descending (closest connections first).

### Email extraction methods
1. **mailto: links** — Most reliable, directly in `<a href="mailto:...">`
2. **Email section header** — Find `<section>` with `<h3>` containing "email", then extract from child `<a>` or `<span>` elements

### Anti-detection stack
```
Playwright Chromium (non-headless)
├── navigator.webdriver = undefined
├── navigator.languages = ['en-US', 'en']
├── navigator.plugins = [1,2,3,4,5]  (non-empty)
├── locale = en-US
├── timezone = America/Los_Angeles
├── color_scheme = light
├── random viewport (varies per session)
└── real Chrome user-agent string
```

**Known limitations:** LinkedIn can still detect Playwright via:
- Canvas/WebGL fingerprint differences
- Chrome DevTools Protocol (CDP) detection
- Behavioral analysis (even with random delays, the access pattern is unusual)
- IP reputation (if scraping from a known cloud/VPN IP)

## What the scraper does NOT do

- Does NOT use LinkedIn's API (no API key, no OAuth)
- Does NOT scrape profile content (only the contact info overlay)
- Does NOT send messages or connection requests
- Does NOT download images or media
- Does NOT access private/non-connected profiles (only works on 1st-degree connections)

## Alternative email discovery methods (no LinkedIn risk)

For contacts the scraper can't find:
1. **`find_emails.py`** — Company domain discovery → email permutation → ZeroBounce verification ($0.05/contact)
2. **`verify_emails.py`** — Cross-reference against actual Gmail thread participants (free, instant)
3. **`discover_emails.py` Phase 2** — Search Gmail accounts for contact names in email headers (free, API-based)
4. **`enrich_web_research.py`** — Perplexity web search for contact info (works for public figures)

## Cookie files

| Account | Cookie file | Location |
|---------|-------------|----------|
| Justin  | `.linkedin_cookies_justin.json` | repo root |
| Sally   | `.linkedin_cookies.json` | repo root |

Both are in `.gitignore`. Delete to force a fresh login on next run.

## Cost

- **LinkedIn scraping:** Free (no API, just browser automation)
- **Email classification:** ~$0.001/contact (GPT-5 mini structured output)
- **Risk cost:** Account warning/restriction if overused
