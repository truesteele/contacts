# How We Find Email Addresses During Contact Enrichment

## Overview

Email discovery is part of the broader contact enrichment cascade. We don't look for emails in isolation -- we first need to find the person's LinkedIn profile, then use that (plus name/org context) to discover their email address.

## The Enrichment Cascade (Context)

Before email discovery happens, we run through these steps to identify the person:

1. **Cache check** -- Do we already have a canonical person record (by LinkedIn URL or name+org)?
2. **Tavily Search** (~$0.001) -- Fast LinkedIn URL discovery via web search
3. **Firecrawl Agent** (~$0.23) -- Deep web search with structured output, if Tavily fails
4. **IRS 990 leadership fallback** -- Match against 990 filing data when EIN is available
5. **o4-mini deep research** (~$0.36) -- OpenAI web search fallback (configurable via `CONTACT_ENRICHMENT_O4_MINI_ENABLED`)

Once we have data (ideally a LinkedIn URL), we move to profile enrichment (Apify) and then email discovery (Tomba).

## Email Discovery (Tomba)

Email lookup only runs if no email was already found during the cascade. The service is `TombaEnrichmentService` in `services/contact_enrichment/tomba_enrichment.py`.

Three strategies, tried in order:

### Strategy 1: LinkedIn URL → Tomba LinkedIn Finder

If we found a LinkedIn URL in the cascade, we pass it to Tomba's `/linkedin` endpoint. This is the highest-quality path since LinkedIn profiles are a strong identifier.

```
Tomba API: GET /v1/linkedin?url=https://linkedin.com/in/darren-walker
```

### Strategy 2: Name + Foundation Domain → Tomba Email Finder

Staff members only (not board members -- board members are unlikely to have domain emails at the foundation). If we have:
- `first_name` + `last_name` (split from the search name)
- `company_domain` (extracted from the enriched data, e.g., fordfoundation.org)

We call Tomba's general email finder:

```
Tomba API: GET /v1/email-finder?first_name=Jane&last_name=Smith&domain=fordfoundation.org
```

### Strategy 3: Parent Company Domain Fallback

Staff at corporate foundations only. Foundation staff often use parent company emails (e.g., kragain@rei.com for someone at REI Cooperative Action Fund). The `_extract_parent_company_domains()` method strips foundation suffixes and tries the core company name + `.com`:

- "REI Cooperative Action Fund" → tries `rei.com`
- "The Ford Foundation" → tries `ford.com`

```
Tomba API: GET /v1/email-finder?first_name=Kristen&last_name=Ragain&domain=rei.com
```

## Board vs Staff Logic

The `_is_staff_for_tomba()` method determines whether to try the name-based strategies (2 and 3):

- If we have `role_type` from `funder_staff`, it checks `role_type == "staff"`
- Otherwise, it checks the title against board keywords (board, trustee, chair, advisory, emeritus)
- Board members skip strategies 2 and 3 (LinkedIn-only email lookup is still attempted)

## Email Verification

After Tomba finds an email, we optionally verify it:

- **When:** If Tomba's confidence score is < 90, or if `TOMBA_VERIFY_ALL=true`
- **How:** Tomba's `/email-verifier` endpoint checks MX records, SMTP, deliverability
- **Rejection criteria:** Email is rejected if it's disposable, blocked, gibberish, or explicitly undeliverable
- **Cost:** Uses Tomba Verifier Credits (20K bonus credits on the Pro plan, essentially free)

## Email Assignment (Work vs Personal)

The `_assign_tomba_email()` method categorizes the found email:

- **Work email:** If the email domain matches the company domain (e.g., jane@fordfoundation.org when company domain is fordfoundation.org) AND it's not flagged as webmail
- **Personal email:** Everything else (Gmail, Yahoo, or non-matching domains)

Verification metadata (deliverability score, flags like `accept_all`, `disposable`, `webmail`) is stored alongside the email.

## Enrich Layer Async Email (Secondary Path)

There's also an async email lookup via Enrich Layer (`enrich_layer_service.py`). This queues a job on Enrich Layer's side:

```
GET /api/v2/profile/email?profile_url=<linkedin_url>&callback_url=<webhook>
```

Results arrive later via webhook at `/api/webhooks/contact-enrichment/enrich-layer-email`. The webhook handler matches the person by LinkedIn username, updates `contact_persons.email`, and marks `email_verified=true` in `person_enrichment_metadata`.

Cost: 3 credits (~$0.012), refunded if no email found.

## Tomba-Only Fallback

If the entire enrichment cascade fails (no Firecrawl result, no 990 match, etc.) and `CONTACT_ENRICHMENT_ALLOW_TOMBA_FALLBACK=true`, we skip profile enrichment entirely and just try Tomba email discovery with whatever data we have. This produces a minimal enrichment record with `data_sources: ["tomba_only_fallback"]`.

## Cost Summary

| Service | Method | Cost |
|---|---|---|
| Tomba LinkedIn Finder | LinkedIn URL → email | ~$0.012 (free if not found) |
| Tomba Email Finder | Name + domain → email | ~$0.012 (free if not found) |
| Tomba Email Verifier | Verify deliverability | Free (uses bonus credits) |
| Enrich Layer Email | Async LinkedIn → email | ~$0.012 (refunded if not found) |

## Key Files

| File | Purpose |
|---|---|
| `services/contact_enrichment/contact_enrichment_service.py` | Orchestrator -- runs the cascade + email discovery |
| `services/contact_enrichment/tomba_enrichment.py` | Tomba API client (find + verify) |
| `services/contact_enrichment/enrich_layer_service.py` | Enrich Layer API client (profile + async email) |
| `api/routes/contact_enrichment_webhook.py` | Webhook for Enrich Layer async email results |
| `services/contact_enrichment/apify_enrichment.py` | Apify profile scraping (no email, profile data only) |

## Environment Variables

| Variable | Purpose |
|---|---|
| `TOMBA_API_KEY` | Tomba API key |
| `TOMBA_SECRET_KEY` | Tomba API secret |
| `TOMBA_VERIFY_ALL` | Force verification on all emails (default: false) |
| `ENRICH_LAYER_API_KEY` | Enrich Layer API key |
| `ENRICH_LAYER_WEBHOOK_SECRET` | HMAC secret for webhook signature verification |
| `CONTACT_ENRICHMENT_ALLOW_TOMBA_FALLBACK` | Enable Tomba-only fallback when cascade fails (default: false) |
| `CONTACT_ENRICHMENT_O4_MINI_ENABLED` | Enable o4-mini deep research fallback (default: true) |
