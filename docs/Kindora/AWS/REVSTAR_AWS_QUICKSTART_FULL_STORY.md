# RevStar AWS QuickStart: The Full Story

**Last updated:** 2026-03-11 (expanded with full SEA backstory and designation/credits issue)
**Author:** Justin Steele, Founder & CEO, Kindora
**Status:** Engagement complete. AWS sub-account closed. Code archived.

---

## TL;DR

Kindora participated in the **AWS & Deloitte Social Entrepreneur Accelerator (SEA)** in November 2025, where Justin presented alongside Anthropic to ~50 organizations from 20+ countries. The SEA led to a connection with RevStar Consulting, which resulted in an AWS-funded $23,000 PoC engagement (Jan 21 - Mar 4, 2026) to build an AWS-native grant extraction pipeline using Bedrock AgentCore. The engagement delivered a partially functional system but fell significantly short: 3 of 4 extraction categories were commented out, Supabase integration was never completed, and output quality trailed Kindora's existing pipeline by 2x in coverage and 2.6x in data depth. Justin signed off, archived the code, and closed the AWS sub-account. Separately, RevStar discovered that Kindora's AWS account is misclassified as "Small Business" (SMB) and "Unmanaged," which blocks access to all AWS credits and funding programs — despite Kindora being a startup and a direct SEA program participant.

---

## 1. How It Started

### The AWS Social Entrepreneur Accelerator (SEA)

In September 2025, Kindora applied to and was accepted into the **AWS & Deloitte Social Entrepreneur Accelerator (SEA)** — Cohort #3. The acceptance came on September 25, 2025 from Cody Benally and Kat Esser on the AWS Social Responsibility and Impact team.

The SEA was a 3-day in-person capacity building event held at the **AWS Skills Center in Seattle** from **November 4-6, 2025**. Approximately 48 organizations from 20+ countries participated. The program focused on health, education, climate, and workforce — facilitated by AWS and Deloitte professionals. For-profit participants like Kindora received SAFEs (Camelback Ventures invested $50K via SAFE as part of the program); nonprofits received grants.

**Justin's strategic motivation for applying:** He wanted AWS cloud credits to help Kindora scale and reduce compute costs. As he wrote to his co-founder Karibu: "I'm hoping we can get some AWS cloud credits to help us scale and save a ton on compute costs. AWS has access to Claude models, and we could host our own open source models like DeepSeek on AWS computers if we had credits to do so."

During the program, **Anthropic asked Justin to co-present** alongside their Head of Beneficial Deployments, speaking to the full cohort about how he built Kindora with Claude Code. At 3:45 PM — "the dreaded post lunch hour speaking slot" — Justin demoed Kindora's analytics dashboard (built in a weekend), the AI funder search tool, his git graph showing 10,000-100,000 lines/month with 67% fewer errors, and the live pipeline showing 199 beta users. During the demo, Abagail McKiernan signed up from the front row ("I just signed up, does it update in real time?"), pushing the count to 203 live.

After the event, Justin and Kat Esser exchanged LinkedIn DMs on **November 8, 2025**:
- **Justin:** "Send me your email and I'll throw that Outdoorithm Collective signup your way :)"
- **Kat:** "Love that and grateful for your presence this week. esserkat@amazon.com"

### The Post-SEA RevStar Connection

On **November 11, 2025**, Kat sent a thank-you email to all SEA participants with three follow-up items. The critical one: a **free post-SEA consultation with RevStar Consulting** — "In a few short sessions, RevStar will help you map out a modernization, data, or AI roadmap aligned with AWS best practices — and highlight funding opportunities to offset build costs." The contact was **Ken Pomella** at RevStar.

This is how the RevStar relationship began. The AWS Social Impact team connected SEA alumni to RevStar as a pathway to funded technical engagements.

### The Initial Migration Proposal (Jan 2026)

On **January 8, 2026**, David Mumford (Sr. Solutions Specialist at RevStar) emailed Justin after a call with a full proposal for an AWS migration — Aurora (database), Cognito (auth), Fargate (frontend + backend), CodePipeline, CloudWatch, SQS. An enterprise architecture play.

On **January 21, 2026**, Justin wrote back with a detailed counter-proposal. He had studied the recommendation independently, researched every suggested service, and concluded the full migration was too much for where Kindora was — 2 co-founders, 250 users, targeting 1,000 by year end:

> "We need to prioritize fast development with a small team over enterprise architecture. The full migration to Aurora, Cognito, and Fargate for frontend would add complexity and ongoing costs that we're not ready to absorb, and would disrupt some of the AI-assisted development workflows that let me ship features quickly as a solo technical founder."

Justin's proposed reduced scope: (1) migrate Azure App Service to AWS App Runner or Fargate, (2) CI/CD via CodePipeline, (3) CloudWatch monitoring, (4) migrate Celery/Redis to SQS + ECS Tasks, (5) connect to Supabase via PrivateLink. Keep Supabase for database/auth, keep Vercel for frontend.

That same day, David also informed Justin that Kindora's AWS account was **classified as "Small Business" (SMB)** rather than as a startup — which would affect funding eligibility. David said "Thank you, this is helpful! Let me review with Victor, and I'll get back to you with options/the best approach."

### The Designation/Credits Block

David Mumford spent approximately **6 weeks (Jan 21 - Mar 3, 2026)** exploring funding programs. On **March 3**, he came back with bad news:

> "I've been exploring different avenues and funding programs to try and get you either some funding or credits. But unfortunately, nothing seems to qualify. I've exhausted all options I have access to on your behalf."

On **March 9**, David provided the full explanation:

1. **Kindora's AWS account is categorized as "Small Business" (SMB)** rather than "Start-up" — this excludes Kindora from the start-up-specific funding program (which presumably provides credits).
2. **Kindora's AWS account is "Unmanaged"** — meaning no AWS Rep or Account Manager is assigned — which excludes Kindora from a second migration-focused funding program.

David noted: "It would be interesting to know if you get any feedback on what caused this, if anything, when your account was originally created."

**Despite participating in AWS's own Social Entrepreneur Accelerator, Kindora could not access AWS credits because of an account designation that predated and was unrelated to the SEA program.** The SMB + Unmanaged classification locked Kindora out of both startup funding and migration funding programs.

### The QuickStart Pivot

While the migration proposal and credits question were in limbo, a separate engagement track materialized: the **QuickStart** — a time-boxed, milestone-driven PoC funded through the AWS APN PoC program. Rather than migrate Kindora's infrastructure, this engagement focused on building an AWS-native grant extraction pipeline.

AWS offered to fund a Proof of Concept engagement through their APN (AWS Partner Network) PoC program — a mechanism where AWS pays an approved consulting partner to build something for the customer at no cost to the customer.

The stated goal: validate whether an AWS-native architecture (Bedrock, Lambda, S3) could power Kindora's funder intelligence pipeline at scale.

### RevStar Selection

AWS connected Kindora with RevStar Consulting, an AWS Advanced Tier Partner based in Columbus, OH. RevStar was selected by the AWS team — Kindora did not choose them from a competitive process.

RevStar's pitch deck positioned them as specialists in "fast-moving, cloud-native development" with "structured scope, baked-in DevOps, and no ambiguity." They emphasized their AWS Lambda Delivery and Amazon ECS Delivery partner certifications.

### The Engagement Terms

- **Cost:** $23,000 (100% AWS-funded, net $0 to Kindora)
- **Timeline:** 5 weeks (Jan 21 - Mar 4, 2026)
- **Format:** QuickStart — time-boxed, milestone-driven delivery
- **RevStar lead:** John Demeter (Delivery Lead)
- **Kindora lead:** Justin Steele (Founder/CEO)

Partnership agreement signed Jan 26, 2026 (Justin) and Jan 27, 2026 (John Demeter).

---

## 2. What Was Promised

### Pitch Deck Deliverables (Slide 7)

1. AWS Lambda or AppRunner-based ingestion pipeline
2. Agentic LLM workflow for data extraction
3. Sitemap + multi-page traversal logic
4. Supabase integration with JSON schema validation
5. Scheduled recurring pipeline runs with logging & metrics

### Pitch Deck Outcomes

1. Reliable extraction of high-quality grant data
2. Automated weekly refresh of opportunities
3. Foundation for scaled ingestion of 100,000+ sites

### Architecture Diagram (Slide 8)

The architecture slide showed a comprehensive system including:
- **Cognito** for authentication
- **API Gateway** for request routing
- **CloudWatch + CloudTrail** for logging and monitoring
- **Prompt Versioning** for LLM prompt management
- **Guardrails** for content safety
- **Multiple foundation models** (Claude Sonnet 4.5, Amazon Nova, Cohere)
- **Supabase** for structured data storage
- **Memory and Tools** layer (web search, internal tools, actions)
- Baseline AWS cloud cost estimate: $800/month

### Partnership Agreement Goals (Page 1)

1. **Real-Time Grant Discovery** — Automate continuous monitoring of funder websites to surface newly released grant opportunities
2. **Reduce Manual Research** — Eliminate slow, static workflows by replacing manual grant searches with automated extraction
3. **Deliver Structured Grant Data** — Provide clean, consistent JSON-based output for downstream matching and alerts
4. **Validate Scalable Architecture** — Prove an AWS-native approach that can eventually scale to 100k+ weekly monitored sites

### Delivery Team Commitments (Page 1)

1. Service: Prioritize client's needs, work proactively
2. Collaboration: Engage closely with client teams
3. Transparency: Communicate all challenges, risks, or changes openly
4. Accountability: Own our work, correct any shortcomings
5. Quality: Uphold the highest standards in every deliverable

### Payment Terms (Page 3)

- 50% due at kickoff
- 50% due upon delivery, regardless of internal launch or go-live status
- If AWS-funded through the POC program, client agrees to provide timely sign-off (typically within 3 business days of request)

---

## 3. What Was Actually Delivered

### AWS Infrastructure

The following AWS resources were provisioned in a dedicated sub-account (178795222862):

**Deployed:**
- Lambda function (orchestrator) connected to EventBridge for scheduled runs
- Bedrock AgentCore Runtime (ECS-based container)
- S3 buckets for input (domains.json) and output (extraction results)
- Secrets Manager entries for Tavily API key and Supabase credentials
- IAM roles for cross-service access
- Two RevStar IAM users with admin access (sheldon.birch-lucas@revstarconsulting.com, sebastian.castelblanco@revstarconsulting.com)

**Not deployed (despite being in architecture diagram):**
- Cognito (no authentication layer)
- API Gateway (Lambda invoked directly, no REST API)
- CloudWatch dashboards or alarms (basic Lambda logging only)
- CloudTrail (not configured)
- Prompt Versioning (not implemented)
- Guardrails (not implemented)
- Infrastructure-as-Code templates (no CloudFormation, CDK, or Terraform)

### The Agent Code (app.py — 1,187 lines)

The core agent is a Python application running in Bedrock AgentCore. It uses the Strands Agents framework with Tavily for web search and content extraction.

**Pipeline steps:**
1. Receive a foundation domain (e.g., fordfoundation.org)
2. Use Tavily `/map` to discover URLs on the site
3. Filter URLs by category using Bedrock LLM (nvidia.nemotron-nano-3-30b)
4. Extract page content using Tavily `/extract`
5. Summarize/structure content using Bedrock LLM (openai.gpt-oss-120b)
6. Validate against Pydantic schema
7. Save results to S3

**Critical finding — 3 of 4 extractors commented out:**

```python
# app.py lines 175-180
URL_CATEGORIES = {
    # "meta": "mission values history headquarters...",
    "grant": "grant programs apply deadline eligibility requirements",
    # "grantee": "past grantees grants awarded...",
    # "staff": "board of directors leadership team...",
}
```

This pattern repeats across 4 parallel config blocks:
- `URL_CATEGORIES` (line 175-180) — only "grant" active
- `FILTER_PROMPTS` (lines 182-203) — only "grant" active
- `SCHEMAS` (lines 206-211) — only "grant" active
- `SUMMARIZATION_PROMPTS` (lines 213-218) — only "grant" active

The pipeline was scoped to extract 4 categories of data (metadata, programs, grantees, staff). Only programs extraction is active in the deployed code.

**Validation always fails:**

```python
# app.py lines 723-724
wrapper = {
    "metadata": {"legal_name": website_url, "confidence_score": 0.0},
    ...
}
```

The validation wrapper hardcodes `legal_name` as the website URL (a string like "fordfoundation.org") and `confidence_score` as 0.0. Since `FunderMetadata.legal_name` is validated as an optional string but metadata fields are checked, and metadata extraction is commented out, every result reports `validation_failed`.

**No Supabase writes:**

The code imports `get_supabase_tool` and loads credentials from Secrets Manager, but no function in app.py actually writes data to Supabase. All output goes to S3 only.

**Sequential processing only:**

Despite `max_workers = 3` being set in the Lambda handler, the actual loop processes domains sequentially:
```python
# index.py line 184
for entry in valid_entries:
    ...
    result = invoke_agent_for_domain(entry, agent_runtime_arn, request_id)
```

**URL cap of 20:**

```python
# app.py line 469
capped_urls = urls[:20]
```

Regardless of how many URLs Tavily discovers on a site, only the first 20 are processed.

### Supporting Code

- **models/grant_schema.py (234 lines):** Well-structured Pydantic models for FunderMetadata, GrantProgram, Grantee, StaffMember. This is arguably the best part of the deliverable — clean, typed data models with sensible field definitions.

- **models/validation.py (108 lines):** Validates against FunderExtraction model. PII scrub fields are all empty lists — no actual scrubbing occurs.

- **tools/web_search.py (204 lines):** Tavily API wrapper with search(), extract(), and map() methods. Functional, clean implementation.

- **tools/extraction_prompts.py (261 lines):** LLM prompts for all 4 extraction categories. The prompts exist and are well-written — they're just not being used because 3 of 4 categories are commented out.

### Output Data (March 9, 2026 Scheduled Run)

The most recent scheduled run processed 10 foundations. Results are stored in S3 and were downloaded for analysis.

**Output format issue:** Results are triple-nested JSON — SSE format wraps a JSON object, which contains a `result` string field that is itself JSON, which contains the actual extraction data. Parsing requires 3 levels of deserialization.

**All 10 foundations show `validation_failed`** in the inner extraction status, but actual program data exists inside the nested structure.

---

## 4. Data Quality Comparison

### Methodology

We extracted program counts and field completeness from RevStar's March 9 output and compared against Kindora's production `funder_programs` table using verified EINs.

**EIN verification was critical.** RevStar's sample input file used incorrect or non-standard EINs for several foundations. Initial comparison using those EINs showed 0 Kindora programs for 5 foundations, which was misleading. After cross-referencing by legal_name and website_url in `us_foundations`, the correct EINs were identified.

### Corrected EIN Mapping

| Foundation | RevStar Input EIN | Correct EIN | Notes |
|---|---|---|---|
| Ford Foundation | 131624150 | 131684331 | RevStar EIN doesn't exist in us_foundations |
| Packard Foundation | 770360948 | 942278431 | Wrong EIN |
| Bloomberg Philanthropies | 205765665 | 205602483 | Wrong EIN |
| RWJF | 222907463 | 226029397 | Wrong EIN |
| Carnegie Corporation | 135009135 | 135009135 | Correct |
| San Francisco Foundation | 941213772 | 941213772 | Correct |
| Hewlett Foundation | 941655673 | 941655673 | Correct |
| Rockefeller Brothers Fund | — | 131760106 | Found by name |
| Moore Foundation | 680397798 | 680397798 | Correct |
| Kresge Foundation | 381359264 | 381359264 | Correct |

### Head-to-Head Comparison

| Foundation | RevStar Programs | Kindora Programs | RS Avg Fields | K Avg Fields | Winner |
|---|---|---|---|---|---|
| Ford Foundation | 8 | 6 | 5.0 | 13.8 | RS (count) |
| Packard Foundation | 1 | 16 | 9.0 | 14.8 | K |
| Carnegie Corporation | 8 | 5 | 5.0 | 15.8 | RS (count) |
| San Francisco Foundation | 6 | 19 | 7.0 | 14.2 | K |
| Hewlett Foundation | 11 | 25 | 5.0 | 17.9 | K |
| Rockefeller Brothers Fund | 7 | 8 | 6.0 | 15.2 | K |
| Bloomberg Philanthropies | 11 | 24 | 4.9 | 15.8 | K |
| Moore Foundation | 4 | 14 | 6.2 | 12.1 | K |
| RWJF | 1 | 12 | 7.0 | 14.6 | K |
| Kresge Foundation | 10 | 0 | 5.0 | — | RS |
| **TOTAL** | **67** | **129** | **5.5** | **14.4** | |

### Key Findings

- **RevStar total programs:** 67 across 10 foundations
- **Kindora total programs:** 129 across 10 foundations (9 with data, 1 not yet enriched)
- **RevStar recall vs Kindora:** 52% (captures about half the programs)
- **Field depth:** RevStar averages 5.5 populated fields per program vs Kindora's 14.4 (2.6x gap)
- **RevStar wins on 3 foundations** by program count: Ford (8 vs 6), Carnegie (8 vs 5), Kresge (10 vs 0)
- **Kindora wins on 7 foundations** — especially Bloomberg (24 vs 11), Hewlett (25 vs 11), SFF (19 vs 6)
- **Kresge gap:** Kindora has 0 programs for Kresge Foundation — this hasn't been enriched yet. RevStar found 10 programs there. This demonstrates that RevStar's agent can discover programs Kindora's pipeline hasn't reached.

### Context for Comparison

This comparison has important caveats:
- RevStar's system only runs 1 of 4 extractors (grant programs). Kindora runs all 4 categories.
- RevStar processes 10 foundations. Kindora has enriched 18,000+ of 49,000+ foundations.
- RevStar's output sits in S3 as JSON. Kindora's programs are in production, serving users.
- The 5.5 avg fields means most programs have only: name, description, focus_areas, geographic_focus, and one additional field. Missing: deadlines, eligibility, application URLs, grant sizes — the fields users care most about.

---

## 5. Deliverable Scorecard

| Promised Deliverable | Status | Notes |
|---|---|---|
| AWS Lambda-based ingestion pipeline | Partial | Lambda exists, invokes AgentCore. Sequential only. |
| Agentic LLM workflow for data extraction | Partial | Works for 1 of 4 categories. 3 extractors commented out. |
| Sitemap + multi-page traversal logic | Delivered | Tavily map/extract handles this. URL cap at 20. |
| Supabase integration with JSON schema validation | Not delivered | Credentials loaded but no write operations implemented. |
| Scheduled recurring pipeline runs | Delivered | EventBridge triggers weekly runs. Results go to S3. |
| Logging & metrics | Minimal | Basic Lambda CloudWatch logs. No dashboards, alerts, or CloudTrail. |
| Cognito authentication | Not delivered | Not implemented despite being in architecture diagram. |
| CloudWatch dashboards | Not delivered | Not implemented despite being in architecture diagram. |
| Prompt Versioning | Not delivered | Not implemented despite being in architecture diagram. |
| Guardrails | Not delivered | Not implemented despite being in architecture diagram. |
| Infrastructure-as-Code | Not delivered | No CloudFormation, CDK, or Terraform. Manual AWS console setup. |
| Documentation | Minimal | README.md and help.txt exist but are generic. |

**Delivered: 2 of 12** (sitemap traversal, scheduled runs)
**Partially delivered: 3 of 12** (Lambda pipeline, agentic workflow, logging)
**Not delivered: 7 of 12**

---

## 6. RevStar's UAT Responses

During UAT review, Justin submitted 16 issues. RevStar provided responses. Key claims vs reality:

| RevStar Claim | Reality |
|---|---|
| "82% success rate across all test foundations" | All 10 results show `validation_failed` in the inner extraction. "Success" is measured at the Lambda invocation level, not data quality. |
| "Agent splits into 4 sub-agents for metadata, grants, grantees, and staff" | 3 of 4 sub-agent categories are commented out in deployed code. Only grants runs. |
| "Supabase integration established and retrieving credentials" | Credentials are loaded from Secrets Manager. No write operations exist in the code. |
| "JSON schema validation working and logging results" | Validation runs but always fails because metadata.legal_name is hardcoded as empty/URL string. |

---

## 7. Kindora's Existing Pipeline (For Context)

At the time of this engagement, Kindora already had a production funder enrichment pipeline:

- **Architecture:** FastAPI + Celery on Azure, Supabase (PostgreSQL), Redis
- **Coverage:** 18,000+ foundations enriched of 49,000+ total
- **Extraction categories:** All 4 (metadata, programs, grantees, staff)
- **Programs in production:** 100,000+ in `funder_programs` table
- **Field depth:** Average 14.4 populated fields per program
- **LLM stack:** OpenAI GPT-5 mini (extraction) + GPT-5 nano (classification)
- **Web scraping:** Firecrawl (site mapping) + direct extraction
- **Cost:** ~$0.023/foundation (standard API), ~$0.014/foundation (batch API)
- **Integration:** Full production — programs power search, matching, and alerts for Kindora users

The QuickStart was intended to validate whether an AWS-native alternative could match or improve on this pipeline, potentially enabling migration to AWS infrastructure.

---

## 8. Key People

### Kindora
- **Justin Steele** — Kindora Founder/CEO, client POC, sole technical founder
- **Karibu Nyaggah** — Kindora Co-Founder (offered second SEA seat but did not attend)

### AWS
- **Kat Esser** (esserkat@amazon.com) — Global Lead, Impact Initiatives, Social Responsibility and Impact, AWS. Senior program leader who runs the SEA program. Direct relationship with Justin from the November 2025 SEA event and LinkedIn DM exchange.
- **Cody Benally** (cbenally@amazon.com) — Social Responsibility and Impact, AWS. Operational/logistics lead for the SEA program. Justin's primary contact for program logistics.

### RevStar Consulting
- **David Mumford** — Sr. Solutions Specialist / Sr. Account Executive (Canada). Initial contact for the migration proposal. Spent 6 weeks exploring funding avenues. Identified the SMB/Unmanaged designation issue blocking credits.
- **Ken Pomella** — RevStar contact for post-SEA follow-up sessions (original booking link from Kat's Nov 11 email).
- **John Demeter** — Sr. Product Manager / Delivery Lead for the QuickStart. Primary contact during the 5-week build.
- **Sheldon Birch-Lucas** — RevStar developer (had admin IAM access to AWS sub-account). Led the pipeline demo.
- **Sebastian Castelblanco** — RevStar developer (had admin IAM access to AWS sub-account). Handled metrics and cost analysis.
- **Mariana Colorado** — RevStar (sent the AWS APN Funding Sign-off document).
- **Victor** — RevStar internal (reviewed scope reduction with David).

### Deloitte
- Co-host of the SEA program. Contact: SEAInfo@Deloitte.com. No individual Deloitte contacts named in correspondence.

### Anthropic
- Unnamed representative (Head of Beneficial Deployments) — Invited Justin to co-present at the SEA about building Kindora with Claude Code.

---

## 9. Timeline of Events

| Date | Event |
|---|---|
| Sep 25, 2025 | Kindora accepted into AWS & Deloitte Social Entrepreneur Accelerator (SEA), Cohort #3 |
| Oct 1, 2025 | Justin confirms participation; resolves Nov 5 scheduling conflict (SF AI training webinar) |
| Oct 10, 2025 | SEA pre-work due: Abaca Business Readiness Assessment, travel, DocuSign releases |
| Nov 4-6, 2025 | SEA program in Seattle (AWS Skills Center). ~48 orgs, 20+ countries. Justin presents with Anthropic. |
| Nov 8, 2025 | Justin and Kat Esser exchange LinkedIn DMs. Kat: "grateful for your presence this week" |
| Nov 11, 2025 | Kat sends post-SEA follow-up email. Introduces RevStar for free post-SEA consultations (Ken Pomella). |
| Jan 8, 2026 | David Mumford (RevStar) sends initial migration proposal after call with Justin |
| Jan 21, 2026 | Justin proposes reduced scope; David informs him of SMB classification issue |
| Jan 21, 2026 | QuickStart engagement kickoff (separate track — AgentCore pipeline, not migration) |
| Jan 26, 2026 | Justin signs QuickStart Partnership Agreement |
| Jan 27, 2026 | John Demeter countersigns Partnership Agreement |
| Weeks 1-3 | Development period (QuickStart) |
| Feb 10, 2026 | Justin in Atlanta for accelerator; reschedules RevStar check-in |
| Feb 25, 2026 | Week 4 UAT demo (42 min). Justin tests against production pipeline. |
| Feb 25, 2026 | Justin sends detailed UAT results: 77% miss rate (13 vs 56 programs), 14 issues logged |
| Mar 3, 2026 | David Mumford returns after 6 weeks: "I've exhausted all options" on credits/funding |
| Mar 4, 2026 | Official QuickStart engagement end date (Week 5) |
| Mar 6, 2026 | RevStar's latest code commit (app.py last modified) |
| Mar 8, 2026 | John Demeter sends close-out email. Requests APN Funding Sign-off. 7-day warranty through Mar 11. |
| Mar 9, 2026 | David Mumford explains designation issue in detail: SMB + Unmanaged = no credits access |
| Mar 9, 2026 | Most recent scheduled pipeline run (10 foundations). Partnership Agreement signed via Adobe Sign. |
| Mar 10, 2026 | Independent code audit conducted |
| Mar 11, 2026 | Justin signs APN Funding Customer Sign-off Template (last day of warranty) |
| Mar 11, 2026 | RevStar IAM users deleted, RevStarAdminRole deleted from main account |
| Mar 11, 2026 | AWS sub-account 178795222862 closed (SUSPENDED, permanent deletion ~June 2026) |
| Mar 11, 2026 | Source code archived to `RevStar-archive-2026-03-11.tar.gz` |
| Mar 11, 2026 | This document finalized |

---

## 10. Financial Summary

| Item | Amount |
|---|---|
| QuickStart SoW cost | $23,000 |
| AWS PoC funding | $23,000 |
| Net cost to Kindora | $0 |
| AWS sub-account charges (accrued) | ~$60 total (Feb-Mar 2026, mainly Bedrock Claude Sonnet) |
| Kindora time investment | ~20+ hours (meetings, reviews, UAT, code audit) |

---

## 11. AWS Account Details

- **Sub-account ID:** 178795222862
- **Sub-account name:** Kindora-RevStar (within Kindora's AWS Organization)
- **Region:** us-west-2
- **S3 input bucket:** agentcore-input-kin-178795222862-us-west-2
- **S3 output bucket (new, empty summaries):** agentcore-output-kin-178795222862-us-west-2
- **S3 output bucket (old, has data):** agentcorequickstartstack-outputbucket7114eb27-yamlpllwvuwc
- **Bedrock models used:** nvidia.nemotron-nano-3-30b (filtering), openai.gpt-oss-120b-1:0 (summarization)
- **RevStar IAM users:** Deleted 2026-03-11 (sheldon.birch-lucas@, sebastian.castelblanco@)
- **Account status:** SUSPENDED 2026-03-11 (permanent deletion ~June 2026)

---

## 12. Closure Actions (Completed 2026-03-11)

### AWS Cleanup

| Action | Date | Details |
|--------|------|---------|
| RevStar IAM users deleted | 2026-03-11 | Removed `sheldon.birch-lucas@revstarconsulting.com` and `sebastian.castelblanco@revstarconsulting.com` from sub-account (178795222862). Both had billing read access + `RevStarAssumeAdminRolePolicy` + `AssumeRevStarSubAccountRole` inline policy. |
| RevStar IAM role deleted | 2026-03-11 | Removed `RevStarAdminRole` from main account (725511698310). Had `AdministratorAccess` policy attached. |
| RevStar IAM policy deleted | 2026-03-11 | Removed `RevStarAssumeAdminRolePolicy` from main account. |
| Sub-account closed | 2026-03-11 | Closed account 178795222862 via AWS Organizations. Status: SUSPENDED. All resources (Lambda, S3, Bedrock AgentCore) will be permanently deleted after 90-day waiting period (~June 2026). |

### Code Archive

RevStar's source code is preserved in two locations:
- **Full directory:** `local-files/RevStar/` (33MB, 2,327 files — includes Lambda vendor packages)
- **Clean archive:** `local-files/RevStar-archive-2026-03-11.tar.gz` (3MB — source code, docs, and configs only; excludes `__pycache__`, `.pyc`, and `kin-lambda/` vendor packages)

Neither location is tracked in git (`local-files/` is gitignored). The archive exists only on the development machine.

### Code Audit Findings

Before deprecation, a thorough review of RevStar's codebase identified patterns worth noting for future reference:

**Nothing architecturally worth adopting.** Kindora's pipeline outperforms RevStar's on every dimension: 40x concurrency vs sequential, full DB integration vs S3-only, all 4 extractors vs 1, 14.4 avg fields vs 5.5.

**3 schema fields worth considering** (future nice-to-have, not urgent):
- `application_format` (enum: online_form, email, mail, portal) — helps users know HOW to apply
- `required_documents` (list of strings) — saves nonprofits prep time
- `operating_support_available` (boolean) — key differentiator for nonprofits

These would require adding columns to `funder_programs`, updating extraction prompts, and updating the UI.

### Sign-Off

Justin signed both documents as requested:
- **March 9, 2026:** QuickStart Client and Delivery Team Partnership Agreement completed (Adobe Sign — signed by RevStar, Justin Steele, John Demeter).
- **March 11, 2026:** APN Funding Customer Sign-off Template signed (Adobe Sign — last day of the 7-day warranty).

Justin signed off despite the UAT results showing significant gaps (77% miss rate, missing fields, stale data). The engagement was free to Kindora ($23K AWS-funded), the warranty was expiring, and the code had already been audited and archived.

### Remaining Open Items

1. **Account designation** — Kindora's AWS account is classified as "Small Business" (SMB) and "Unmanaged" (no AWS rep assigned). This blocks access to startup funding programs and migration funding programs. Need to engage Kat Esser / AWS Social Impact team to understand the path to reclassification.
2. **AWS credits** — Despite participating in the SEA program and completing a $23K funded engagement, Kindora has received zero AWS credits. David Mumford exhausted all avenues accessible to RevStar. The path forward likely runs through the AWS Social Impact team directly.
3. **AWS Social Impact relationship** — Kat Esser is the key relationship. Maintaining and deepening this connection has strategic value for credits, reclassification, and future programs.

---

## 13. Source Files

All source materials are preserved in `local-files/RevStar/` (not tracked in git):

```
local-files/RevStar/
  Kindora - QuickStart Client and Delivery Team Partnership Agreement.pdf
  Kindora - Quick Starts Pitch Deck.pdf
  REVSTAR_AWS_QUICKSTART_FULL_STORY.md  (this document)
  audit/
    agent-source/           # RevStar's AgentCore agent code
      app.py                # Main agent (1,187 lines)
      models/
        grant_schema.py     # Pydantic data models
        validation.py       # Validation logic
      tools/
        web_search.py       # Tavily API wrapper
        extraction_prompts.py  # LLM prompts for extraction
    kin-lambda/             # Lambda orchestrator code (+ vendor packages)
      index.py              # Lambda handler (246 lines)
    latest-summary.json     # March 9, 2026 scheduled run output

local-files/RevStar-archive-2026-03-11.tar.gz  # Clean 3MB archive (excludes vendor packages)
```

**Note:** The AWS sub-account (178795222862) has been closed. All cloud resources (Lambda functions, S3 buckets, Bedrock AgentCore agent, IAM users) will be permanently deleted after the 90-day waiting period (~June 2026). This local archive is the only remaining copy of RevStar's code.

---

## 14. The Designation / Credits Problem (Unresolved)

This is the single most important unresolved issue from the entire AWS engagement.

### What Happened

During the engagement, David Mumford at RevStar discovered that Kindora's AWS account has two designations that block it from all funding programs:

1. **"Small Business" (SMB)** — Kindora is classified as a Small Business rather than a Start-up. This excludes Kindora from the start-up-specific AWS funding program that provides credits.

2. **"Unmanaged"** — No AWS Representative or Account Manager is assigned to Kindora. This excludes Kindora from a second, migration-focused funding program.

David spent 6 weeks (Jan 21 - Mar 3, 2026) exploring every alternative funding avenue and came back empty. His exact words: "I've exhausted all options I have access to on your behalf."

### The Irony

Kindora was selected by AWS's own Social Impact team to participate in the SEA. AWS funded a $23,000 PoC engagement for Kindora through the APN program. But the same company's account classification system categorizes Kindora in a way that prevents it from accessing startup credits or having an assigned account representative.

### What Needs to Happen

The path to credits likely runs through the AWS Social Impact team (Kat Esser), not through RevStar or standard AWS account channels. Kindora needs:

1. **Reclassification** from SMB to Start-up (or equivalent designation that enables funding program eligibility)
2. **An assigned AWS representative** (moving from "Unmanaged" to managed status)
3. **Access to AWS credits** to support Kindora's compute-intensive grant extraction pipeline, which is currently the company's largest cost

### Why It Matters Now

Kindora is deploying its own AI model to AWS and plans to run its grant extraction pipeline there. The cost of running the pipeline is by far Kindora's largest expense. Without credits, Kindora is paying full price for compute on a platform whose Social Impact team has recognized Kindora as an organization worth supporting.

---

## 15. Lessons Learned

1. **AWS-funded doesn't mean risk-free.** The $0 cost removed financial risk but not time risk. ~20+ hours of founder time on reviews, meetings, and auditing could have been spent on product development.

2. **Consulting partner selection matters.** Kindora didn't choose RevStar — AWS assigned them. Future engagements should involve client input on partner selection.

3. **Architecture diagrams aren't commitments.** The pitch deck showed Cognito, CloudWatch, Guardrails, and Prompt Versioning. None were implemented. The diagram was aspirational, not contractual.

4. **Code audits reveal truth.** RevStar's UAT responses painted a positive picture. The code told a different story. Always inspect the actual deliverable.

5. **The existing system was already better.** Kindora's pipeline (built primarily by the founder with AI coding assistants) outperformed a $23K consulting engagement on every measurable dimension except one foundation's coverage.

6. **The relationship has value beyond the deliverable.** The AWS Social Impact team connection — especially Kat Esser — and the validation that Kindora's approach is competitive with professional consulting output have significant strategic value. The unresolved designation/credits issue represents a concrete, actionable next step in that relationship.

7. **Account designations can silently block everything.** Kindora participated in the SEA, received a $23K funded engagement, and presented alongside Anthropic — yet an account classification set at account creation time prevented access to any credits or funding programs. Nobody flagged this until 6 weeks into the engagement. When engaging with large platforms, always verify your account tier and assigned support level early.
