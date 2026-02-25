# Project: Email Finder Pipeline

## Overview
Build a Python script (`scripts/intelligence/find_emails.py`) that finds email addresses for ~894 contacts who have name + company data but no email. The pipeline: generate email permutations from name + company domain, verify via ZeroBounce API, validate via GPT-5 mini, and save to Supabase.

## Technical Context
- **Tech Stack:** Python 3.12, psycopg2, OpenAI SDK, requests
- **Venv:** `.venv/` (arm64, activate with `source .venv/bin/activate`)
- **Database:** Supabase PostgreSQL via psycopg2 direct connection
- **Env vars:** `SUPABASE_DB_PASSWORD`, `OPENAI_APIKEY`, `ZEROBOUNCE_API_KEY`
- **Existing patterns:** See `scripts/intelligence/discover_emails_v2.py` for DB connection, scoring, LLM verification patterns
- **Run scripts from:** project root with `python -u scripts/intelligence/find_emails.py`

## Key Technical Details

### Contact Data Available (894 contacts)
- `first_name`, `last_name` (all 894 have both)
- `company` or `enrich_current_company` (891 have at least one)
- `enrich_current_title` (872 have it)
- `linkedin_url` (891 have it)
- 69 contacts are at big tech (Google, Amazon, Meta, Microsoft, Apple) with catch-all email servers

### ZeroBounce API
- **Endpoint:** `GET https://api.zerobounce.net/v2/validate?api_key={key}&email={addr}&ip_address=`
- **Response statuses:** `valid`, `invalid`, `catch-all`, `unknown`, `spamtrap`, `abuse`, `do_not_mail`
- **Sub-statuses:** `alternate`, `antispam_system`, `greylisted`, `mail_server_temporary_error`, `forcible_disconnect`, and 20+ more
- **Response fields:** `address`, `status`, `sub_status`, `free_email` (bool), `domain_age_days`, `active_in_days`, `smtp_provider`, `mx_record`, `firstname`, `lastname`
- **Rate limit:** 80,000 requests per 10 seconds (very generous). Exceeding triggers 1-min block.
- **Pricing:** ~$0.01-0.02/credit depending on volume. Never charges for `unknown` results.
- **Credits check:** `GET https://api.zerobounce.net/v2/getcredits?api_key={key}`
- **Key advantage:** AI-powered catch-all detection + `active_in_days` field for stale email detection
- **Free tier:** 100 free monthly validations for testing
- **IMPORTANT: Available credits = 1,275.** Must minimize API calls:
  - Filter with DNS MX check BEFORE calling ZeroBounce (free)
  - Stop testing permutations for a contact once a `valid` result is found
  - Skip domains that return `invalid` on first permutation (likely bad domain)
  - For catch-all domains (Google, Amazon, etc.), only test the most likely 2-3 permutations

### Email Permutation Patterns (generate ~8-12 per contact)
```
first.last@domain.com       (most common corporate pattern)
firstlast@domain.com
first_last@domain.com
flast@domain.com
first.l@domain.com
firstl@domain.com
f.last@domain.com
last.first@domain.com
lfirst@domain.com
first@domain.com            (small companies / founders)
```

### Domain Discovery from Company Name
- Strip suffixes: Inc, LLC, Ltd, Corp, Foundation, etc.
- Try: `companyname.com`, `companyname.org`, `companyname.io`, `companyname.co`
- For known companies, use hardcoded domain map (Google -> google.com, Amazon -> amazon.com, etc.)
- Can also try DNS MX lookup to validate domain has email capability

### GPT-5 mini Validation Rules
- **Accept:** Personal emails (gmail, yahoo, etc.) with good name match
- **Reject:** Corporate emails where domain doesn't match current company (stale employer)
- **Reject:** Catch-all results unless name is highly distinctive
- **Common names:** Require stronger signals (multiple patterns verified, distinctive domain)
- Use existing `EmailVerification` pydantic model from discover_emails_v2.py

### Quality Gates
- Script must run with `source .venv/bin/activate && python -u scripts/intelligence/find_emails.py --dry-run -n 5`
- Must handle rate limits, retries, and graceful shutdown
- Must log progress and costs
- Must not overwrite existing emails

## User Stories

### US-001: Domain Discovery Module
**Priority:** 1
**Status:** [x] Complete

**Description:**
Build the domain discovery module that converts company names to email domains. This is the foundation - without correct domains, permutations are useless.

**Acceptance Criteria:**
- [x] Create `scripts/intelligence/find_emails.py` with domain discovery functions
- [x] `company_to_domains(company_name)` returns list of candidate domains (e.g., ["google.com"])
- [x] Hardcoded map for 20+ known companies (Google, Amazon, Meta, Microsoft, Apple, Year Up, Salesforce, Deloitte, McKinsey, Goldman Sachs, JPMorgan, Cisco, Oracle, Adobe, LinkedIn, TikTok, Netflix, Uber, Lyft, Stripe)
- [x] Generic fallback: strip suffixes, generate .com/.org/.io/.co variants
- [x] DNS MX record check to validate domain can receive email (using `dns.resolver`)
- [x] Write a `--test-domains` CLI flag that tests domain discovery for 10 sample contacts and prints results
- [x] Script runs without errors: `source .venv/bin/activate && python scripts/intelligence/find_emails.py --test-domains`

---

### US-002: Email Permutation Generator
**Priority:** 2
**Status:** [x] Complete

**Description:**
Build the permutation generator that creates candidate email addresses from name + domain.

**Acceptance Criteria:**
- [x] `generate_permutations(first, last, domain)` returns 8-12 email candidates
- [x] Handles hyphenated names (Marie-Ange -> marieange, marie-ange, marie)
- [x] Handles names with suffixes (III, Jr, etc.) - strips them
- [x] Handles nicknames / short names (Jen vs Jennifer) - uses what's given
- [x] Add `--test-perms` CLI flag that generates permutations for 5 sample contacts
- [x] Script runs without errors: `source .venv/bin/activate && python scripts/intelligence/find_emails.py --test-perms`

---

### US-003: ZeroBounce Integration
**Priority:** 3
**Status:** [x] Complete

**Description:**
Integrate ZeroBounce API for email verification. This is the core validation step. ZeroBounce returns rich data including status, sub_status, free_email flag, active_in_days, and smtp_provider.

**Acceptance Criteria:**
- [x] `verify_email(email_addr)` calls ZeroBounce API and returns full response (status, sub_status, free_email, active_in_days, etc.)
- [x] Concurrent verification with `ThreadPoolExecutor(max_workers=50)` (conservative, well under 80K/10sec limit)
- [x] Retry logic for transient errors (status=unknown, sub_status=greylisted/mail_server_temporary_error) with exponential backoff
- [x] Credit balance check before starting (`GET /v2/getcredits` endpoint)
- [x] `--test-verify` CLI flag that verifies 3 known emails (one valid, one invalid, one catch-all) using real API key (100 free monthly credits)
- [x] Graceful handling of API errors, rate limits (1-min block if exceeded)
- [x] Cost tracking (count credits used, note: unknown results are free)
- [x] Script runs without errors: `source .venv/bin/activate && python scripts/intelligence/find_emails.py --test-verify`
- [x] Install any new dependencies (dnspython if not present) into .venv

---

### US-004: GPT-5 Mini Validation + Scoring
**Priority:** 4
**Status:** [x] Complete

**Description:**
Add LLM validation for verified emails. Screens for stale employer emails, common name conflicts, and assigns confidence.

**Acceptance Criteria:**
- [x] `validate_with_llm(contact, email, zb_result)` returns EmailVerification (reuse pydantic model)
- [x] LLM prompt includes: contact name, current company, title, LinkedIn URL, email domain, ZB status/sub_status, free_email flag, active_in_days
- [x] Rules in prompt: reject stale employer domains, accept personal emails with good match, be strict for common names
- [x] Skip LLM for obvious matches (full name in email + domain matches company, score >= 90)
- [x] `--test-validate` CLI flag that runs LLM validation on 3 mock scenarios
- [x] Concurrent LLM calls with 150 workers (per existing pattern)
- [x] Script runs: `source .venv/bin/activate && python scripts/intelligence/find_emails.py --test-validate`

---

### US-005: Main Pipeline + DB Integration
**Priority:** 5
**Status:** [x] Complete

**Description:**
Wire everything together: fetch contacts from DB, run the full pipeline (domain -> permutations -> verify -> validate -> save), with progress tracking.

**Acceptance Criteria:**
- [x] Fetch 894 contacts missing email, ordered by ai_proximity_score DESC
- [x] For each contact: discover domains -> generate permutations -> verify all with ZeroBounce -> pick best verified -> LLM validate -> save
- [x] "Best verified" selection logic: prefer valid over catch-all, prefer recent activity (active_in_days), prefer name.domain match
- [x] Save to contacts.email field (only if currently NULL/empty)
- [x] CLI args: `--dry-run`, `--limit N`, `--min-confidence 70`, `--workers 50`
- [x] Progress reporting every 25 contacts (found, skipped, no-domain, cost)
- [x] Final summary with total found, cost, time elapsed
- [x] Handle interrupts gracefully (Ctrl+C saves progress)
- [x] Script runs end-to-end: `source .venv/bin/activate && python -u scripts/intelligence/find_emails.py --dry-run -n 5`

---

### US-006: Full Dry-Run Test + Cost Estimation
**Priority:** 6
**Status:** [x] Complete

**Description:**
Run a dry-run test on 50 contacts to validate the pipeline works end-to-end, estimate costs for full run, and fix any bugs.

**Acceptance Criteria:**
- [x] Run `python -u scripts/intelligence/find_emails.py --dry-run -n 50` successfully
- [x] All 50 contacts processed without crashes
- [x] Print cost estimate for full 894-contact run (ZeroBounce credits + OpenAI tokens)
- [x] Document results in progress.txt: hit rate, common failure modes, estimated total cost
- [x] Fix any bugs discovered during the test run
- [x] Script handles edge cases found during testing (missing company, hyphenated names, etc.)
