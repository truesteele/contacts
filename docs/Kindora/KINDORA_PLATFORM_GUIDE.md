# Kindora Platform Guide

**Version:** 7.0
**Last Updated:** February 21, 2026
**Status:** Production

> *"We exist to democratize philanthropy so every worthy cause finds its champion."*

This comprehensive guide covers everything about the Kindora platform - from our mission and features to technical architecture. Use the table of contents to navigate to the section most relevant to your needs.

---

## Table of Contents

### Company & Product
1. [About Kindora](#1-about-kindora)
2. [Core Features](#2-core-features)
   - Funder Discovery & Intelligence
   - Government Grants (SAM.gov)
   - Open Grants & Opportunities
   - Pipeline Management
   - Grant Writing
   - Dashboard Intelligence
   - AI Assistants
   - Organization Management
   - Relationship Management
   - CRM Integrations
   - Help Center & Knowledge Base
3. [Subscription Plans & Pricing](#3-subscription-plans--pricing)
4. [User Journeys](#4-user-journeys)

### Market & Impact
5. [Market Opportunity](#5-market-opportunity)
6. [Competitive Positioning](#6-competitive-positioning)
7. [Impact & Social Value](#7-impact--social-value)

### For Developers
8. [Architecture Overview](#8-architecture-overview)
9. [Repository Structure](#9-repository-structure)
10. [Database Schema](#10-database-schema)
11. [API Architecture](#11-api-architecture)
12. [AI Integrations](#12-ai-integrations)
13. [Deployment & Infrastructure](#13-deployment--infrastructure)

### Reference
14. [Data Assets](#14-data-assets)
15. [Known Issues & Technical Debt](#15-known-issues--technical-debt)
16. [Glossary](#16-glossary)

---

# Part 1: Company & Product

## 1. About Kindora

### What We Do

Kindora is a **Public Benefit Corporation** that transforms how funding flows in the social sector through an AI-powered grant intelligence platform. We help nonprofit organizations discover funders and win more grants by combining AI-powered research with comprehensive foundation data.

### The Problem We Solve

Traditional fundraising platforms overwhelm users with thousands of irrelevant matches while charging $220-$500/month with annual commitments. Small nonprofits—those closest to community challenges—are priced out of professional fundraising tools, creating a vicious cycle where organizations that need funding most can least afford to pursue it.

| Traditional Approach | Kindora Approach |
|---------------------|------------------|
| Hiring consultants costs **$1,500-$5,000** per grant | Starting at **$0/month** (Explore) or **$25/month** (Community) |
| Instrumentl/Candid charge **$179-$500/month** with annual contracts | **No annual contracts** - cancel anytime |
| Researching funders takes **40-80 hours** per project | Get matched funders in **minutes** |
| 3,000-10,000 irrelevant matches | 25-300 highly relevant, quality matches |
| No data on corporate/government funders | **890+ non-990 funders** (corporate, government, international) |

### Public Benefit Corporation Charter

**Legal Structure:** Delaware Public Benefit Corporation (incorporated August 2025)

**Specific Public Benefit:** *"To democratize philanthropic giving to under-resourced nonprofits"*

**What This Means:**
- Legally required to balance profit with social impact
- Board-adopted KPIs measuring progress toward public benefit
- Stakeholder governance including nonprofits, communities, and employees

**Key Performance Indicators:**
1. Number of active nonprofit organizations using the platform annually
2. Total hours returned to nonprofits through automated prospecting and research
3. Grant dollars secured by organizations in subsidized access program
4. Year-over-year revenue growth of platform users vs. nonprofit sector baseline

### Leadership Team

#### Justin Steele - CEO & Chief Technology Officer

**The Funder's Perspective:**
- Led Google.org's philanthropy across the Americas, directing **$698 million** in strategic investments
- Managed $100M outcomes-based loan fund and $75M AI Opportunity Fund
- Deep understanding of how funding decisions actually get made

**Nonprofit Operations Experience:**
- Deputy Director at Year Up (workforce development)
- Consultant at Bain & Company and The Bridgespan Group
- Currently founding Outdoorithm Collective (outdoor access for urban families)

**Technical Expertise:** Built Kindora's entire platform prototype using engineering background and AI capabilities.

#### Karibu Nyaggah - President & Chief Product Officer

**The Nonprofit Builder:**
- Co-founded Sinapis, scaling entrepreneurship programs across **6 countries** in Africa and Latin America
- Trained **7,000+ entrepreneurs**, supported **130,000+ job creation**
- Facilitated **$200M+ in revenue growth** for small/medium enterprises

**Global Impact Expertise:**
- World Bank consultant on investment policy and strategic planning
- Chief of Staff at Alphabet's Loon project (global internet connectivity)
- Currently Director at Meta leading AI efficiency initiatives

**Product Leadership:** Designed Kindora's front-end experience and user journey, bringing deep operational knowledge of program scaling.

#### Twenty-Year Partnership

Justin and Karibu met at Harvard Business School's Summer Ventures program in 2003, bonding over shared values about business as a force for good. Their complementary experience—Justin on the funder side, Karibu on the nonprofit operations side—provides unique dual perspective on both sides of the philanthropy ecosystem.

### Who Uses Kindora

| User Type | Description | Primary Use Cases |
|-----------|-------------|-------------------|
| **Nonprofit Staff** | Development directors, grant writers | Funder discovery, Intel Briefs, grant drafting, network mapping |
| **Executive Directors** | Small org leaders wearing many hats | Quick research, strategic planning |
| **Board Members** | Governance and oversight | Progress tracking, saved funders |
| **Consultants** | Fundraising consultants serving multiple clients | High-volume research, client portfolios |

### Early Traction

- **First week of beta:** 50 nonprofit organizations signed up
- **Current:** 258 nonprofit organizations on the platform
- **Acquisition offer:** Received within two weeks of PBC incorporation approval
- **Real-world validation:** Secured grants using the platform (George Family Foundation)

---

## 2. Core Features

### Funder Discovery & Intelligence

#### Intelligent Matching System

AI-powered matching that finds funders most likely to fund your organization.

- **Peer-Based Discovery:** Identifies funders who already support similar organizations
- **AI Program Officer Persona:** Reasons like experienced program officers, not algorithms
- **Comprehensive Analysis:** Analyzes foundation websites, annual reports, 990 forms
- **Quality Over Quantity:** Provides 25-300 highly relevant matches vs. thousands of false positives
- **Match Scoring:** Each funder receives a 0-100 fit score with detailed rationale
- **Location:** Dashboard → Your Prospects → Matches

#### Find Funders (5-Modality Filtered Search)

Advanced funder search across 175K+ foundations and 890+ non-990 funders.

- **Keyword Search:** AI semantic embeddings for intelligent text matching
- **Geographic Filters:** State, city, and regional focus
- **NTEE Code Filtering:** Filter by National Taxonomy codes
- **Priority Populations:** Target specific beneficiary groups
- **Equity Focus Areas:** Filter funders by equity-related priorities
- **Program Types:** Match by funding program categories
- **Grantee Budget Ranges:** Filter by typical grantee budget size
- **Additional Filters (Premium):** Geographic concentration, NTEE focus diversity, accepts unsolicited applications, general operating support, multi-year funding, capital grants, fiscal sponsorship
- **Plan Gating:** Basic filters free; premium filters require Community+ plans
- **Location:** Dashboard → Find Funders

#### Deep Search

Advanced AI-powered deep funder research with web crawling.

- **Web Intelligence:** Crawls foundation websites for real-time data
- **Beyond 990 Data:** Discovers information not available in IRS filings
- **Strategic Context:** Surfaces funding philosophy, recent priorities, and leadership changes
- **Location:** Find Funders → Deep Search

#### Global Search (Cmd/Ctrl+K)

Org-wide instant search across all objects in the platform.

- **Cross-Object Search:** Searches funders, organizations, programs, pipeline deals, and more
- **Keyboard Shortcut:** Cmd+K (Mac) / Ctrl+K (Windows) for instant access
- **Always Org-Wide:** Never filtered by program — searches across entire organization
- **Location:** Available from any page via keyboard shortcut

#### Intel Briefs

Comprehensive 5-8 page strategic analyses of specific funders.

- **What's included:**
  - Funder mission, leadership, and decision-makers
  - Historical giving patterns from IRS 990 data
  - Geographic and programmatic focus areas
  - 10-20 stratified grant examples (large/medium/small)
  - Strategic approach recommendations
  - Key contacts and board members
- **Generation time:** 24-48 hours via AI-powered research
- **Real insider intelligence:** Typically requires expensive consultants
- **Cost:** Included in subscription or $8 per brief add-on
- **Location:** Dashboard → Create Intel Brief (search any funder)

#### 990 Insights

Direct access to IRS Form 990 data for any foundation.

- **Key metrics:** Total assets, annual giving, grant counts
- **Grant history:** Searchable list from 6.7M+ IRS records
- **Giving trends:** Year-over-year analysis
- **Geographic breakdown:** Where they actually give (not just stated focus)
- **NTEE analysis:** What types of organizations they fund
- **Location:** Funder detail page → 990 Insights tab

#### Funder Intelligence (Premium Feature)

AI-enriched insights providing deeper strategic understanding of funders.

- **Funding Philosophy Tags:** Identifies funder approach (Strategic, Responsive, Capacity Building, Place-Based, Catalytic)
- **Semantic Focus Taxonomy:** Detailed focus areas beyond NTEE codes
- **Beneficiary Types:** Who the funder ultimately aims to serve
- **DAF Classification:** Donor-Advised Fund status and implications
- **Application Mode:** How to apply (LOI, full proposal, invitation-only)
- **Gated Feature:** Available to Individual, Team, and Consultant tier subscribers
- **Location:** Funder detail page → Funder Intelligence Card

#### Funding Programs

Track active grant programs, deadlines, and application requirements.

- **Program Discovery:** Browse funding programs by funder
- **Application Status:** Open, closed, rolling, upcoming indicators
- **Deadline Tracking:** Due dates with pattern recognition
- **Grant Size Ranges:** Typical award amounts
- **Focus Areas:** Program-specific funding priorities
- **Geographic Focus:** Regional restrictions and preferences
- **Support Types:** Multi-year, matching grants, operating support
- **Application Access:** Direct links to application portals
- **Location:** Funder detail page → Funding Programs tab

#### Accelerator & Incubator Discovery

Smart UX for early-stage organizations to discover accelerators and incubators.

- **Contextual Callout:** Appears when an org's profile suggests accelerator fit
- **Taxonomy Integration:** Funder taxonomy includes accelerator and incubator types
- **Location:** Dashboard → Your Prospects (contextual callout)

#### Org-Aware Search Intelligence

Search results enhanced with organization-specific relevance signals.

- **Org-Fit Signal Badges:** Visual indicators on search result cards showing relevance to your org's profile
- **"Recommended for You" Filter:** Smart preset that auto-filters based on your org context and funder giving patterns
- **Context-Aware Ranking:** Search results weighted by geographic overlap, NTEE alignment, and budget fit
- **Location:** Find Funders → search results

#### Knowledge Level Indicators (Value Ladder UI)

Visual indicators showing enrichment depth for each funder in your pipeline.

- **5 Knowledge Levels:**
  - Level 0 (0%, Gray): Not Analyzed
  - Level 1 (25%, Blue): Matched - has match score
  - Level 2 (50%, Purple): Evaluated - AI evaluated fit
  - Level 3 (75%, Orange): In-Depth - deep dive analysis complete
  - Level 4 (100%, Green): Engagement Intel - Intel Brief generated
- **Features:**
  - Circular progress ring on funder cards
  - Sort funders by knowledge level
  - Smart Evaluation Banner recommending top unevaluated matches
- **Purpose:** Makes AI enrichment value self-evident, driving conversion to paid tiers

### Government Grants (SAM.gov Integration)

#### Federal Grant Discovery

AI-powered discovery of federal grant opportunities from SAM.gov.

- **Deadline-Based Browsing:** Filter by urgency (urgent/soon/upcoming/later)
- **Award Amount Filtering:** Find grants matching your funding needs
- **Agency Filters:** Browse by federal agency (NIH, NSF, ED, etc.)
- **CFDA Filtering:** Filter by Catalog of Federal Domestic Assistance codes
- **Eligibility Matching:** Nonprofit eligibility verification
- **Historical Data:** Past award amounts and funding patterns
- **Pattern Analysis:** AI-identified funding trends
- **Location:** Dashboard → Government Grants

### Open Grants & Opportunities

#### Open Grants

Browse grants that are currently accepting applications from your matched and pipeline funders.

- **Active Opportunities:** Shows only grants with open application windows
- **Deadline Tracking:** Filter by urgency and due dates
- **Amount Filtering:** Find grants matching your funding needs
- **Focus Area Matching:** Filter by programmatic alignment
- **Direct Application Links:** Quick access to application portals
- **Pipeline Integration:** Add opportunities directly to your grant tracker
- **Location:** Dashboard → Open Grants

### Pipeline Management

#### Grant Tracker (Funder Pipeline)

Visual pipeline to track funder relationships through stages.

- **Kanban Board:** Drag-and-drop cards through pipeline stages
- **List View:** Table format with sorting and filtering
- **Mobile View:** Responsive interface for mobile devices
- **Pipeline Stages:** Prospect → Researching → Ready to Apply → Drafting Application → Submitted → Won/Lost
- **Stage Suggestions:** AI-recommended stage transitions
- **Deal Tracking:** Funding amounts, deadlines, notes
- **Deal History:** Track all stage changes and events over time
- **Task Management:** Add tasks/to-dos to individual pipeline deals
- **Bulk Actions:** Move multiple funders simultaneously
- **Analytics:** Pipeline health metrics, stage distribution, success rates, and revenue tracking
- **Upcoming Deadlines:** Widget showing 60-day deadline preview
- **Funder Notes:** Per-funder note-taking within pipeline deals
- **Location:** Dashboard → Grant Tracker

### Grant Writing

#### Kindora Draft Grant Assistant

AI-powered grant application writing from uploaded RFPs.

- **Workflow:**
  1. Select a funder from your pipeline
  2. Provide grant requirements or upload RFP
  3. AI generates complete first draft
  4. Edit and refine in real-time
  5. Export when ready
- **Features:**
  - Uses your organization's voice and data
  - Incorporates funder-specific insights
  - Word count compliance
  - Application status tracking
  - Credit-based pricing for transparent, fair usage
  - Real-time credit usage display
- **Cost:** Uses Kira Credits from your subscription (~30 credits per application, ~25 per pitch deck)
- **Location:** Dashboard → Kindora Draft

### Dashboard Intelligence

#### Dashboard Widgets (V2.5)

Customizable dashboard with intelligent widgets for at-a-glance insights.

- **Daily Briefing Widget:** Aggregated intelligence including critical funder updates, new opportunities, and deadline alerts
- **Action Stack Widget:** Prioritized task list with recommended next steps
- **Network Intelligence Widget:** Connection-based insights and warm intro opportunities
- **Top Matches Widget:** Highest-fit funder recommendations
- **Briefs Ready Widget:** Status of generated Intel Briefs
- **Pulse Widget:** Key fundraising metrics and trends
- **Activation Meter:** Platform engagement and onboarding progress tracking
- **Notifications:** Real-time notification system with preference management
- **Location:** Dashboard (main page)

#### Smart Evaluation System

AI-powered funder fit assessment with transparency.

- **Real-Time Evaluation:** Live evaluation progress tracking
- **Bulk Evaluation:** Assess multiple funders simultaneously
- **Evaluation Costs:** 2 Kira Credits per funder evaluation
- **Deep Dive Reasoning:** Detailed fit rationale with scoring
- **Evaluation History:** Track when funders were last evaluated
- **Unevaluated Banner:** Prompts to evaluate top matches
- **Location:** Your Prospects → Evaluate button; Bulk Evaluation Modal

### AI Assistants

#### Ally Chat (with Agentic Skill Routing)

Context-aware AI assistant with 7 specialized skills, available throughout the platform.

- **Intelligent Skill Routing:** First message is classified by AI to select the best skill for the conversation
- **Agentic Tools:** Ally can search funders, get funder profiles, and access platform data directly
- **Location:** Floating chat widget on dashboard pages

**7 Specialized Skills:**

| Skill | Trigger Examples | What It Does |
|-------|------------------|--------------|
| **Funder Discovery** | "Find funders for youth education in Texas" | Multi-angle search for mission-matched foundations |
| **Funder Research** | "Tell me about the Ford Foundation" | Deep-dive analysis of a specific funder's giving patterns & leadership |
| **Fit Evaluation** | "Would this funder be a good fit for us?" | Alignment assessment for a specific nonprofit-funder pair |
| **Prospect List** | "Build me a prospect list for our new program" | Prioritized, research-backed prospect lists |
| **Landscape Analysis** | "What does funding look like for climate in the Midwest?" | Sector-wide funding patterns and trends |
| **Grant Application Prep** | "Help me prepare to apply to the Gates Foundation" | Application strategy, LOI drafting, and component preparation |
| **Funder Pitch Deck** | "Create a pitch deck for our meeting with Bloomberg" | Bespoke Reveal.js pitch decks tailored to each nonprofit+funder pair |

- Skill is matched once per conversation and reused for subsequent messages
- Falls back to general AI assistant if no skill matches
- Frontend shows a skill badge when a skill is matched

#### Grant Finder

Conversational funder discovery within Ally Chat.

- Natural language search for funders
- Real-time AI evaluation of results
- Sources: IRS 990 data, web research, foundation websites
- Results ranked by fit with your organization

#### Pitch Practice (Voice AI)

Interactive pitch coaching with real-time voice AI.

- **Live Voice Practice:** Practice your funder pitch with a simulated program officer
- **Real-Time Feedback:** AI responds conversationally and provides coaching
- **Technology:** GPT-4o Realtime API for natural voice interaction
- **Location:** Dashboard → Pitch Practice

#### Pitch Deck Generator

AI-generated presentation decks for funder meetings.

- **Bespoke Decks:** Each deck is unique to the nonprofit + funder + context
- **Reveal.js Format:** Professional slide presentations
- **Cost:** ~25 Kira Credits per generation
- **Location:** Accessible via Ally Chat or funder detail pages

### Organization Management

#### Multi-Tenant Structure

Flexible account hierarchy for any organization size.

```
Account (billing & limits)
  └── Organization (your nonprofit)
        └── Programs (fundraising initiatives)
```

- **Accounts:** Manage billing, team seats, and overall limits
- **Organizations:** Your nonprofit's profile, funders, and applications
- **Programs:** Separate fundraising initiatives with unique funder matches

#### Organization Profile

Your nonprofit's comprehensive profile that powers all matching.

- Mission statement and focus areas
- Programs and impact metrics
- Leadership team information
- Budget and financial data
- Geographic scope
- NTEE classification
- Strategic priorities
- Target populations
- Program delivery methods
- Partnerships and collaborations
- Featured programs
- Specific funding needs
- **Profile Completeness Tracking:** Progress indicator showing how complete your profile is
- **Document Uploads:** Upload 990s, annual reports, and other org documents
- **PDF Export:** Download your org profile as a shareable PDF
- **Peer Organizations:** Discover and compare with similar nonprofits
- **AI Profile Generation:** Automatic profile creation from uploaded documents during onboarding
- **Location:** Dashboard → Your Org Profile

#### Team Management

Invite and manage team members with role-based access.

- **Invite Members:** Email invitations with role assignment
- **Role Management:** Change team member roles (Admin, Member, etc.)
- **Pending Invitations:** Track and resend outstanding invites
- **Ownership Transfer:** Transfer organization ownership to another member
- **Remove Members:** Remove team members with confirmation
- **Seat Limits:** Team size governed by subscription plan
- **Location:** Dashboard → Settings → Team

### Relationship Management

#### Current Funders

Track your existing funder relationships.

- Application history and outcomes
- Relationship stages (prospect → cultivation → ask → stewardship)
- Re-approach recommendations based on funder changes
- Foundation feedback logging
- CSV import and manual entry

#### Funder Leadership Mapping

Know the key people at each foundation.

- CEO and executive team
- Board members
- Program officers
- Contact information and LinkedIn profiles

#### Contact Enrichment

AI-powered enrichment of funder staff profiles.

- **What's enriched:**
  - Full employment history with dates
  - Education background
  - Board positions
  - LinkedIn profile URL
  - Work email (when available)
- **Cost:** 5 Kira Credits for new enrichment, 2 Credits for refresh
- **Technology:** Cascading approach using Firecrawl Agent, Enrich Layer, and Apify
- **Location:** Funder detail page → Leadership tab → Enrich Contact

#### Network Mapping (Connections)

Track your team's connections to funder staff and discover warm introduction paths.

- **LinkedIn Import:** Upload LinkedIn data export for automatic network mapping
  - Parses LinkedIn connection data (CSV export)
  - AI-powered entity resolution matches connections to funder leadership
  - Connection matching identifies overlaps with your prospect funders
- **Manual Connection Entry:** Add connections manually
- **Connection Strength Indicators:** Visualize relationship quality
- **Warm Introduction Discovery:** Find paths to key decision-makers through your network
- **Network Stats:** Summary cards showing total connections, matched funders, and intro opportunities
- **Connection Opportunities List:** Browse warm intro opportunities ranked by relevance
- **Person Detail View:** Detailed view of individual network connections
- **Cost:** 2 Kira Credits per auto-imported connection
- **Location:** Dashboard → Connections

#### Saved Searches (Community+)

Save and monitor your funder search queries.

- Save frequent search criteria
- Get notified when new funders match
- Quick access from sidebar
- **Available on:** Community, Individual, Team, and Consultant plans
- **Location:** Search results → Save Search

#### Board Review Sharing

Share grant applications with board members for review and approval.

- **Token-Based Access:** Secure shareable links (no login required)
- **Email Templates:** Pre-built board notification emails
- **Preview Generation:** Board-friendly application summaries
- **Response Tracking:** Monitor board member engagement
- **Secure Access:** Time-limited access tokens
- **Location:** Kindora Draft → Application → Share with Board

#### Peer Organization Network

Discover funding opportunities through similar organizations.

- **Peer Identification:** Find nonprofits with similar missions
- **Shared Funders:** See which funders support your peers
- **Co-Funding Opportunities:** Identify collaborative funding prospects
- **Organization Comparisons:** Side-by-side peer analysis
- **Location:** Dashboard → Your Prospects → Similar Prospects; Your Org Profile → Peers

#### Community Intelligence

Crowdsourced insights from the Kindora nonprofit community.

- **Community Tips:** User-contributed funder engagement advice
- **Best Practices:** Successful approach strategies
- **Engagement Notes:** Feedback on funder interactions
- **Opt-In Sharing:** Privacy-controlled collaborative data
- **Location:** Funder detail page → Community tab

#### Deadline Management

Centralized view of all upcoming funder and grant deadlines.

- **Calendar View:** Visual deadline timeline
- **Urgency Indicators:** Color-coded priority levels
- **Government + Foundation:** Combined deadline tracking
- **Custom Deadlines:** Add manual deadline entries
- **Priority Flagging:** Mark critical deadlines
- **Location:** Dashboard → Deadlines

#### API Access (Team+)

Programmatic access to Kindora data and features.

- RESTful API with OpenAPI documentation
- Bearer token authentication with 30-day expiry
- Rate limited (100 requests/hour)
- Endpoints: funder search, pipeline management, analytics
- **Location:** Settings → API Keys

### CRM Integrations

#### Salesforce Integration

Sync your Kindora funder data with Salesforce CRM.

- **Bidirectional Sync:** Push funder prospects and pipeline data to Salesforce
- **Contact Mapping:** Map Kindora funder contacts to Salesforce records
- **Pipeline Sync:** Keep grant tracker stages in sync with Salesforce opportunities
- **Location:** Dashboard → Settings → Integrations

#### Blackbaud Integration

Connect with Blackbaud's constituent relationship management system.

- **Constituent Sync:** Push funder data to Blackbaud CRM
- **Relationship Tracking:** Sync engagement history
- **Location:** Dashboard → Settings → Integrations

### Help Center & Knowledge Base

#### Public Help Center

Searchable knowledge base with guides, tutorials, and best practices.

- **Category Browsing:** Articles organized by topic and feature area
- **Full-Text Search:** Search across all help articles
- **Role-Based Content:** Articles targeted to specific user roles (nonprofit staff, executive directors, consultants, board members)
- **Quick Start Guides:** Sequenced onboarding articles for new users
- **Contextual Help:** Route-aware help suggestions based on current page
- **Location:** Dashboard → Help Center; also accessible at /resources

#### AI Help Chat

Conversational AI assistant for navigating the knowledge base.

- **Natural Language Queries:** Ask questions in plain language
- **Article Suggestions:** Surfaces relevant help articles based on your question
- **Semantic Search:** AI-powered matching beyond keyword search
- **Location:** /resources/chat

---

## 3. Subscription Plans & Pricing

### Pricing Philosophy: Mission-Aligned

Kindora is committed to accessible pricing that serves under-resourced nonprofits:

- **90-99% cost savings** vs. traditional consultants ($1,500-$5,000 per application)
- **50-88% cheaper** than competitors (Candid FDO Pro: $220/month)
- **No annual contracts** removing barriers for resource-constrained nonprofits
- **Unlimited funder browsing** on all tiers including free (Explore)
- **Community tier accessibility** despite lower margins

### Plan Comparison (Pricing Model 3.0)

| Feature | Explore | Community | Individual | Team | Consultant |
|---------|---------|-----------|------------|------|------------|
| **Monthly Price** | $0 | $25 | $49 | $199 | $399 |
| **Annual Option** | — | $250/yr (17% off) | $490/yr (17% off) | $1,990/yr (17% off) | $3,990/yr (17% off) |
| **Annual Contract** | Never | Never | Never | Never | Never |
| **Funder Browsing** | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited |
| **Intel Briefs/month** | Welcome bonus only | 6 | 10 | 30 | 60 |
| **Kira Credits/month** | Welcome bonus only | 250 | 500 | 2,000 | 4,000 |
| **Programs per Org** | 1 | 3 | 5 | 10 | Unlimited |
| **Team Seats** | 1 + 1 Guest | 2 + 2 Guests | 3 + 3 Guests | 8 + Unlimited Guests | 15 + Unlimited Guests |
| **Client Organizations** | 1 | 1 | 1 | 1 | Up to 10 |
| **Pipeline + Saved Searches** | — | Yes | Yes | Yes | Yes |
| **Advanced Exports** | — | — | Yes | Yes | Yes |
| **Collaboration Tools** | — | — | — | Yes | Yes |
| **Credit/Brief Rollover** | No | Yes (60 days) | Yes (60 days) | Yes (60 days) | Yes (60 days) |
| **Target Customer** | Exploration | Small nonprofits | Solo grant professionals | Growing dev teams | Agencies & consultants |

**Add-On Pricing:** $8 per Intel Brief, $18 per 100 Kira Credits (all tiers)

### Feature Gating by Tier

#### Pipeline & Saved Searches (Community+)
- Full pipeline view with drag-and-drop Kanban board
- Save and name frequent search queries
- Quick access from sidebar

#### Advanced Exports (Individual+)
- Export funder lists, pipeline data, and analytics as CSV/PDF

#### Collaboration Tools (Team+)
- Real-time alerts and collaboration features
- Unlimited guest seats (view-only)

#### Consultant Plan: Account-Level Pooled Billing
- Manage up to 10 client organizations under one subscription
- Intel Briefs and Kira Credits pooled across all client workspaces
- Each client gets their own workspace with separate funder matches, programs, and pipeline
- 14-day free trial available
- Dedicated onboarding support

### Welcome Package (New Users)

All new Explore signups receive a **30-day Welcome Package**:
- 3 Intel Briefs (bonus, expires in 30 days)
- 150 Kira Credits (bonus, expires in 30 days)
- Full platform access during onboarding

Credits expire if not used within 30 days to encourage exploration.

### Add-On Services

#### Deep Funder Research ($599-$2,499)

Custom research packages for organizations needing comprehensive funder discovery:

| Package | Price | Matches | Scope |
|---------|-------|---------|-------|
| **Focused** | $599 | 25-50 | Local/single program focus |
| **Comprehensive** | $1,499 | 75-150 | Multi-state/program |
| **Maximum** | $2,499 | 150-300 | National scope |

#### Funder List Analysis ($25-$300)

- Evaluate existing prospect lists for alignment and quality
- Volume discounts available
- Deduplication guarantees

#### Custom Intelligence Briefs ($8 each)

- On-demand funder analysis
- Same comprehensive 5-8 page format
- Available on all tiers as add-on

### Credit System

**Intel Briefs:** Premium funder research reports
- Included monthly based on plan
- Additional briefs: $8 each
- Rollover: Up to 2x monthly allocation (60-day cap, Community+ plans)

**Kira Credits:** AI-powered features
- Used for: Grant drafting, AI chat, document analysis, evaluations, contact enrichment
- Roughly: 30 credits ≈ 1 grant application, 2 credits per evaluation, 5 credits per contact enrichment
- Rollover: Capped at 2x monthly allocation (60-day cap, Community+ plans)
- Promotional/welcome credits expire after 30 days

### Unit Economics

| Metric | Value |
|--------|-------|
| **Gross Margins (Blended)** | 72-75% |
| **Community Tier Margin** | 60% (below market for accessibility) |
| **Individual/Team/Consultant Margin** | 75-80% |
| **Intel Brief Cost** | ~$5.00 per brief (AI + data costs) |
| **Kira AI Cost** | ~$3.87 per application |

### Who Should Choose Each Plan

**Explore ($0/mo)** - Best for:
- Organizations evaluating the platform
- Those wanting to browse funders without commitment
- Budget-conscious nonprofits testing fit
- Occasional funder research needs

**Community ($25/mo)** - Best for:
- Small nonprofits with limited fundraising staff
- Organizations just starting grant seeking
- Budget under $500K
- Those who need pipeline tracking and saved searches

**Individual ($49/mo)** - Best for:
- Solo grant writers and development directors
- Active grant seekers managing multiple programs
- Those needing advanced exports and more credits

**Team ($199/mo)** - Best for:
- Organizations with dedicated development teams
- Growing orgs with 10+ programs and multiple staff
- Teams needing collaboration tools and real-time alerts

**Consultant ($399/mo)** - Best for:
- Grant consultants and agencies managing multiple client organizations
- Firms needing pooled billing across client workspaces
- High-volume operations with 60 briefs and 4,000 credits per month

---

## 4. User Journeys

### Journey 1: New User Setup

```
Sign Up → Choose Path → Onboarding → Profile Generation → Peer Discovery → Funder Matches
```

| Step | Time | Description |
|------|------|-------------|
| **Sign Up** | 5 min | Create account with email verification |
| **Choose Path** | 1 min | Select onboarding path: Seamless (upload docs), Manual (enter details), or Consultant |
| **Onboarding** | 10-30 min | Enter organization details via chosen path |
| **Profile Generation** | 5-10 min | AI builds comprehensive org profile from your data |
| **Peer Discovery** | 2 min | Find similar nonprofits to improve matching |
| **Review & Confirm** | 5 min | Review generated profile and confirm |
| **Get Matches** | 2-6 hours | AI identifies matching funders |

**Onboarding Paths:**
- **Seamless:** Upload existing documents (990s, annual reports) for AI-powered profile generation
- **Manual:** Enter organization details step-by-step
- **Consultant:** Specialized onboarding for consultants managing multiple clients

### Journey 2: Research a New Funder

```
Search → Review Profile → Generate Brief → Add to Pipeline
```

1. **Search:** Enter funder name in Custom Funder search
2. **Quick Review:** See 990 data, giving history, geographic focus
3. **Generate Brief:** Click to create comprehensive Intel Brief
4. **Save & Track:** Bookmark funder and add to My Funders

### Journey 3: Write a Grant Application

```
Select Funder → Enter Requirements → AI Draft → Edit → Export
```

1. **Select Funder:** Choose from My Funders or search
2. **Add Details:** Paste grant requirements or upload RFP
3. **Generate Draft:** Kindora Draft creates complete application
4. **Refine:** Edit sections, adjust tone, ensure compliance
5. **Export:** Download or copy for submission

### Journey 4: Track Existing Funders

```
Add Funder → Log History → Get Insights → Plan Re-approach
```

1. **Add to Current Funders:** Enter funder with application history
2. **Log Outcomes:** Record grants received, declined, pending
3. **Review Insights:** See giving patterns and relationship health
4. **Plan Next Steps:** Get AI recommendations for re-approach

### Journey 5: Manage Pipeline

```
Add to Pipeline → Track Stage → Update Status → Win/Close
```

1. **Add Funders:** Move matched funders into pipeline
2. **Track Progress:** Drag through stages (Prospect → Researching → Ready to Apply → Drafting → Submitted)
3. **Set Deadlines:** Add application due dates and reminders
4. **Manage Tasks:** Add to-dos and track tasks within each deal
5. **Record Outcomes:** Mark as Won or Lost with notes
6. **Analyze:** Review pipeline health, stage distribution, and conversion metrics

### Journey 6: Discover Government Grants

```
Browse Deadlines → Filter Eligibility → Save Opportunities → Apply
```

1. **Browse by Urgency:** View grants by deadline proximity
2. **Filter by Eligibility:** Narrow to nonprofit-eligible opportunities
3. **Review Details:** Check award amounts, CFDA codes, agencies
4. **Save Opportunities:** Bookmark relevant grants
5. **Track in Pipeline:** Add to pipeline for application tracking

### Journey 7: Map Your Network & Find Warm Intros

```
Import LinkedIn → Entity Resolution → Discover Overlaps → Request Intros
```

1. **Import Network:** Upload LinkedIn data export (CSV)
2. **AI Matching:** Entity resolution matches your connections to funder leadership
3. **Discover Overlaps:** See which of your connections work at prospect funders
4. **Find Warm Paths:** Identify introduction opportunities through your network
5. **Prioritize Outreach:** Focus on funders where you have the strongest connections

### Success Metrics

| Metric | Target |
|--------|--------|
| Profile generation | 5-10 minutes (automated AI analysis) |
| Funder matching | 2-6 hours for comprehensive analysis |
| Time savings | 15-100 hours per month returned to mission work |
| Success rate improvement | From 5% blind applications to 25%+ targeted approach |

---

# Part 2: Market & Impact

## 5. Market Opportunity

### Market Size

The nonprofit fundraising support market represents a **$10.3 billion total addressable market**, encompassing grant discovery platforms, grant writing services, and funder intelligence tools.

| Segment | Size | Description |
|---------|------|-------------|
| **US Nonprofits** | 1.8 million | Organizations with $2.62 trillion in assets |
| **Annual Donations** | $450 billion | Philanthropic giving to nonprofits |
| **Grant Software Market** | $1.24 billion | North America (45% of global market) |
| **Grant Consulting Services** | $6.48 billion | Professional grant writers and consultants |
| **Underserved Market** | $1.84 billion | Organizations priced out of current solutions |

### The Problem: 85% Are Priced Out

Despite this massive market, only 5-10% of nonprofits can afford professional fundraising tools:

| Solution | Cost | Barrier |
|----------|------|---------|
| Traditional grant consultants | $150-400/hour | $3,000-5,000 per application |
| Instrumentl | $179-499/month | Annual contracts required |
| Candid Foundation Directory | $220/month | $1,599/year for professional access |

This pricing barrier leaves **1.53 million nonprofits**—those closest to community problems—without access to professional fundraising support.

### Market Validation

- Grant management software market growing at **10.3% CAGR**, projected to reach $4.8B globally by 2030
- Instrumentl's 4,500+ customers report winning **$1.1M more annually** using technology
- 30% of nonprofits currently hire consultants, spending **$12,000+ annually**
- 72% of Kindora beta users report struggling with funder discovery

### Why Now?

1. **AI Technology Maturity:** GPT-4/5 and Claude enable sophisticated grant writing at 90% lower cost
2. **Market Demand:** Existing solutions clearly inadequate (10,000 match overwhelm vs. 150 quality prospects)
3. **Funding Pressure:** Federal funding uncertainty driving nonprofits to diversify grant portfolios
4. **Digital Transformation:** Nonprofits increasingly adopting cloud-based solutions post-COVID
5. **Founder Expertise:** Unique combination of technical skills and deep sector experience

---

## 6. Competitive Positioning

### Competitive Landscape

| Platform | Monthly Cost | Annual Lock-in | Our Advantage |
|----------|--------------|----------------|---------------|
| Candid FDO Pro | $220 | Optional | 88% cheaper, AI-powered |
| Instrumentl | $179-$499 | Required | No contracts, quality matches |
| GrantStation | $99-$179 | Optional | AI insights vs. basic search |
| **Kindora Explore** | **$0** | **Never** | **Free unlimited funder browsing** |
| **Kindora Community** | **$25** | **Never** | **Up to 95% savings** |

### Differentiation Strategy

1. **AI-First Approach:** Program officer reasoning vs. keyword matching
2. **Accessibility Focus:** Serving underserved market competitors ignore
3. **Dual Perspective:** Founders with experience on both sides of philanthropy
4. **Complete Solution:** Discovery + intelligence + application assistance
5. **Public Benefit Structure:** Mission alignment built into corporate governance
6. **No Annual Contracts:** Removing commitment barriers for resource-constrained nonprofits

### Investment Highlights

1. **Massive Underserved Market:** 1.8M nonprofits, most priced out of existing solutions
2. **Strong Founder-Market Fit:** Unique dual perspective from both sides of philanthropy
3. **Defensible Technology:** AI moats in reasoning models and data processing
4. **Healthy Unit Economics:** SaaS-level margins (72-75%) with clear path to profitability
5. **Social Impact Alignment:** Public Benefit Corporation structure attracting values-aligned capital
6. **Early Traction:** 200+ signups and acquisition interest before formal launch

---

## 7. Impact & Social Value

### Theory of Change

**If** we remove barriers to funding discovery and application **then** more resources flow to community-rooted organizations **resulting in** increased impact in underserved communities.

### Impact Metrics (Beyond Revenue)

| Metric | Target | Description |
|--------|--------|-------------|
| **Hours Returned** | 1 million annually | Time redirected to mission work vs. research |
| **Funding Secured** | Track all grants | Especially first-time recipients |
| **Geographic Diversity** | Measure success | Across rural/urban and different regions |
| **Demographic Representation** | Ensure access | Leaders from affected communities |
| **Community Transformation** | Document stories | Programs launched/expanded through funding |

### Stakeholder Value Creation

| Stakeholder | Value |
|-------------|-------|
| **Nonprofits** | 90-99% cost reduction vs. consultants, 15-100 hours/month time savings |
| **Communities** | More efficient funding flow to organizations serving them |
| **Funders** | Better alignment with organizations advancing their missions |
| **Employees** | Purpose-driven careers advancing social good |
| **Sector** | Rising tide lifting all boats through shared intelligence and tools |

### The Kindora Difference

We're not just changing how nonprofits raise money—we're changing who gets to change the world. Every algorithm we train, every feature we ship, every partnership we forge advances our mission of creating equitable access to the resources needed to drive social change.

**The bottom line:** When nonprofits spend time building relationships instead of wrestling with spreadsheets, communities thrive. When funders discover organizations they never knew existed, innovation flourishes. When those closest to problems have equal access to resources, real change happens.

---

# Part 3: Technical Documentation

## 8. Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER FACING                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    kindora-app                               │   │
│  │   Next.js 14 • TypeScript • Tailwind CSS                    │   │
│  │   130+ pages • 250+ components                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    kindora-api                               │   │
│  │   FastAPI • Python 3.x • Celery + Redis                     │   │
│  │   70+ route modules • 230+ services                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DATABASE                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 Supabase PostgreSQL                          │   │
│  │   200+ tables • 3 schemas • Row Level Security              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ADMIN TOOLS                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 kindora-analytics                            │   │
│  │   Next.js 14 • Mixpanel • Support Tickets                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Tech Stack Summary

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, Tremor React, Radix UI |
| **Backend** | FastAPI, Python 3.x, Celery, Redis |
| **Database** | Supabase (PostgreSQL), Row Level Security |
| **Auth** | Supabase Auth + API tokens (dual auth) |
| **AI/ML** | OpenAI (GPT-5.2, GPT-5-mini, GPT-4o), Anthropic (Claude Opus/Sonnet/Haiku 4.5), Perplexity |
| **Payments** | Stripe (subscriptions, checkout, webhooks) |
| **Email** | Resend (transactional) |
| **Hosting** | Vercel (frontend), Azure App Service (API) |
| **Analytics** | Mixpanel |

### Technical Scalability

- **Cloud-native architecture** on Vercel/Azure
- **Async processing** via Celery for resource-intensive AI operations
- **Real-time updates** via WebSocket connections
- **Horizontal scaling** designed for 10,000+ organizations

---

## 9. Repository Structure

```
kindora/
├── kindora-app/              # Main customer-facing application
│   ├── src/
│   │   ├── app/              # Next.js 14 App Router (130+ pages)
│   │   ├── components/       # React components (250+)
│   │   ├── services/         # API integration services
│   │   ├── hooks/            # Custom React hooks
│   │   ├── context/          # React Context providers
│   │   ├── lib/              # Utilities (Supabase, analytics)
│   │   └── types/            # TypeScript definitions
│   └── package.json
│
├── kindora-analytics/        # Internal admin dashboard
│   ├── src/
│   │   ├── app/              # Next.js 14 App Router
│   │   │   ├── analytics/    # Mixpanel dashboards
│   │   │   ├── tickets/      # Support ticket management
│   │   │   └── feedback/     # Product feedback
│   │   └── components/
│   └── package.json
│
├── kindora-api/              # Python FastAPI backend
│   └── python_api/
│       ├── api/routes/       # 70+ API route modules
│       ├── services/         # 230+ service classes
│       ├── repositories/     # 70 data access layers
│       ├── models/           # Pydantic models
│       ├── tasks/            # Celery background tasks
│       └── core/             # Auth, config, clients
│
├── kindora-data/             # Data pipelines & ingestion
│   └── funder-intelligence/
│       ├── 01-data-ingestion/     # IRS 990 data processing
│       ├── 02-ein-matching/       # V4 ML-based EIN matching
│       │   ├── v4_embeddings/     # FAISS index + embeddings
│       │   └── batch_verification # GPT-5-mini verification
│       ├── 03-web-scraping/       # Foundation website scraping
│       ├── 04-agentic-matching/   # AI-powered funder evaluation
│       └── non-990-ingestion/     # Corporate/govt/intl funders
│           ├── phase2_queries/    # Perplexity deep research
│           ├── grantee_discovery/ # Phase 5 grantee finding
│           └── staff_queries/     # Phase 2B leadership data
│
├── supabase/                 # Database configuration
│   └── migrations/           # 500+ timestamped migrations
│
└── docs/                     # Documentation
```

### Key Files

| File | Purpose |
|------|---------|
| `kindora-app/src/app/layout.tsx` | Root layout with providers |
| `kindora-app/src/middleware.ts` | Auth middleware |
| `kindora-api/main.py` | FastAPI application entry |
| `kindora-api/celery_worker.py` | Background task workers |
| `CLAUDE.md` | Development guidelines (this repo) |

---

## 10. Database Schema

### Schema Organization

| Schema | Tables | Purpose |
|--------|--------|---------|
| `public` | 100+ | Core domain: organizations, funders, grants, 990 data |
| `client` | 98 | Multi-tenant: accounts, orgs, programs, profiles, tickets |
| `billing` | 17 | Subscriptions, credits, payments, promo codes |
| `auth` | 5 | Supabase authentication |

### Core Tables

#### Multi-Tenant Hierarchy

```sql
-- Account (billing owner)
client.accounts
  ├── id, name, account_type
  ├── max_organizations, max_programs_per_org
  ├── subscription_tier, stripe_customer_id
  └── created_by

-- Organization (nonprofit)
client.organizations
  ├── id, name, ein, mission
  ├── account_id (FK → accounts)
  └── status, headquarters

-- Program (fundraising initiative)
client.programs
  ├── id, name, description
  ├── organization_id (FK → organizations)
  └── focus_areas, is_active

-- User Profile
client.profiles
  ├── id (FK → auth.users)
  ├── full_name, email
  └── organization_id
```

#### Funder Data

```sql
-- US Foundations (IRS 990 Data - 173K)
public.us_foundations
  ├── ein, legal_name, city, state
  ├── total_assets, annual_grants
  ├── ceo_name, website_url
  └── foundation_type, ntee_code

-- Non-990 Funders (Corporate, Government, International - 891)
public.non_990_funders
  ├── id (UUID), legal_name
  ├── website_url, city, state
  ├── funder_type, primary_focus_areas
  ├── geographic_scope, profile_summary
  └── median_grant_size, total_annual_giving

-- Funder Evaluations (per-program matches - 29K+)
public.funder_evaluations (canonical evaluations junction)
  ├── id (evaluation_id), funder_id (polymorphic)
  ├── organization_id, program_id
  ├── canonical_us_foundation_ein, canonical_non_990_funder_id
  └── deep_dive_score, deep_dive_rationale, workflow_status

-- IRS 990 Grants (6.7M records)
public.foundation_grants
  ├── foundation_ein, foundation_name
  ├── recipient_name, recipient_ein, matched_ein
  ├── grant_amount, grant_purpose, filing_year
  └── match_confidence, match_method (v4_embedding_llm, ml_probabilistic, ein_exact)

-- Pre-computed 990 Stats (173K records)
public.funder_990_snapshots
  ├── funder_id, ein
  ├── total_grants, total_amount, median_amount
  ├── ntee_breakdown (JSONB)
  └── geographic_distribution (JSONB)
```

#### Billing

```sql
-- Subscription Plans
billing.subscription_plans
  ├── id (free, community, professional, enterprise)
  ├── display_name, price, billing_interval
  ├── features (JSONB)
  └── monthly_credits

-- Active Subscriptions
billing.subscriptions
  ├── organization_id, subscription_plan_id
  ├── status, stripe_subscription_id
  └── current_period_start, current_period_end

-- Credit Transactions
billing.kira_credit_transactions
  ├── organization_id, transaction_type
  ├── credit_amount, remaining_balance
  └── description, created_at
```

### Key Relationships

```
client.accounts
    └── 1:N → client.organizations
                  └── 1:N → client.programs
                              └── 1:N → funder_evaluations
                                          └── N:1 → canonical funder tables
                                                  ├── us_foundations (EIN, 173K)
                                                  │    └── 1:N → foundation_grants (6.7M)
                                                  └── non_990_funders (UUID, 807)
                                                       └── 1:N → funder_grants (via grantee discovery)
```

### Important ID Semantics

| ID Field | Type | Use |
|----------|------|-----|
| `funder_id` | Polymorphic | **Primary identifier in URLs** (EIN for us_foundation, UUID for non_990/unresearched) |
| `evaluation_id` | UUID | Junction table ID |
| `organization_id` | UUID | Client org reference |

---

## 11. API Architecture

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DUAL AUTHENTICATION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  API Token Auth                    Supabase JWT Auth            │
│  (Service-to-Service)              (User Context)               │
│                                                                  │
│  POST /token                       X-Supabase-Auth: <jwt>       │
│  → Returns JWT (30min)             → Verified via JWT_SECRET    │
│                                                                  │
│  Authorization: Bearer <token>     Extracts user_id, email      │
│                                                                  │
│            └──────────────┬─────────────────┘                   │
│                           ▼                                      │
│                    ┌─────────────┐                               │
│                    │ AuthContext │                               │
│                    │ api_token   │                               │
│                    │ user_id     │                               │
│                    └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### Major API Endpoints

#### Funder Discovery
```
GET  /client/{org}/funders/list            # List matched funders
POST /client/{org}/funders/decline         # Decline a funder
POST /client/{org}/funders/{id}/star       # Star a funder
GET  /funders/{org}/{id}/details           # Funder details (EIN or UUID)
GET  /client/{org}/funder_profile/{id}     # Get enriched funder profile
GET  /funder-programs/{funder_id}          # Get funder's grant programs
GET  /funder-intelligence/{funder_id}      # Get AI-enriched funder intelligence
```

#### Pipeline Management
```
GET  /client/{org}/pipeline                # Get pipeline funders
POST /client/{org}/pipeline/add            # Add funder to pipeline
PUT  /client/{org}/pipeline/{id}/stage     # Update pipeline stage
DELETE /client/{org}/pipeline/{id}         # Remove from pipeline
GET  /client/{org}/pipeline/analytics      # Pipeline metrics
```

#### Government Grants
```
GET  /government-grants                    # List federal opportunities
GET  /government-grants/{id}               # Get grant details
GET  /government-grants/deadlines          # Deadline-based listing
```

#### AI Features
```
POST /ai/chat                              # Kira AI conversation
POST /ai/detect-intent                     # Intent classification
POST /ai/parse-application                 # Extract from PDF
POST /ai/generate-response                 # Generate section
POST /grant-finder/conversations/start     # Start grant search
POST /grant-finder/conversations/{id}/messages  # Search query
POST /client/{org}/funders/evaluate        # AI funder evaluation
POST /client/{org}/funders/bulk-evaluate   # Bulk evaluation
```

#### Billing
```
POST /billing/subscription/create          # Create subscription
POST /billing/subscription/cancel          # Cancel subscription
GET  /billing/kira-credits/balance         # Get credit balance
POST /billing/stripe/create-checkout       # Stripe checkout
POST /billing/webhook                      # Stripe webhooks
```

### Request Flow

```
Client Request
      │
      ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Route     │ ──► │   Service   │ ──► │ Repository  │
│  (FastAPI)  │     │  (Logic)    │     │  (Data)     │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                    │
      │                   │                    ▼
      │                   │            ┌─────────────┐
      │                   │            │  Supabase   │
      │                   │            └─────────────┘
      │                   │
      │                   ▼ (for AI operations)
      │            ┌─────────────┐
      │            │ OpenAI /    │
      │            │ Claude      │
      │            └─────────────┘
      │
      ▼ (for background jobs)
┌─────────────┐
│   Celery    │
│   (Redis)   │
└─────────────┘
```

---

## 12. AI Integrations

### Model Selection

| Task | Model | Cost | Notes |
|------|-------|------|-------|
| **Intel Brief Intelligence** | GPT-5.2 | Per token | Highest intelligence for analysis |
| **Intel Brief Writing** | Claude Opus 4.5 | Per token | Narrative quality |
| **Intel Brief Research** | Perplexity sonar-deep-research | ~$0.92/brief | 9K words avg, comprehensive |
| **Intent Detection** | GPT-5-mini | ~$0.0003/query | Fast classification |
| **Funder Evaluation** | Claude Opus 4.5 | Per token | Complex reasoning |
| **Grant Drafting** | Claude Sonnet 4.5 | Per token | Writing quality |
| **Ally Chat** | Claude Sonnet 4.5 | Per token | Agentic skill conversations |
| **Skill Routing** | Claude Haiku 4.5 | ~$0.0001/query | Fast skill classification |
| **Pitch Practice** | GPT-4o Realtime | Per token | Real-time voice interaction |
| **Summary Memos** | GPT-4o | Per token | Structured summaries |
| **General Chat** | GPT-5-mini | Per token | Fast responses |
| **Non-990 Research** | Perplexity sonar-pro | ~$0.06/query | Web research |
| **Data Extraction** | GPT-5-mini | ~$0.005/query | Structured JSON output |
| **EIN Verification** | GPT-5-mini | ~$0.002/match | LLM adjudication |
| **Embeddings** | text-embedding-3-small | ~$0.00002/embed | Semantic similarity |

### API Configuration

```python
# GPT-5 models require different parameters
response = openai.chat.completions.create(
    model="gpt-5-mini",
    messages=[...],
    max_completion_tokens=2000,  # NOT max_tokens
    reasoning_effort="low",      # For JSON responses
    response_format={"type": "json_object"},  # Structured output
    # NO temperature parameter (uses default reasoning)
)
```

**GPT-5 Breaking Changes:**
- `max_tokens` → `max_completion_tokens` (required)
- `temperature` → not supported (omit entirely)
- Reasoning tokens count against completion limit

### External Services

| Service | Purpose | Rate Limit |
|---------|---------|------------|
| **OpenAI** | GPT-5.2, GPT-5-mini, GPT-4o, GPT-4o Realtime | Per account |
| **Anthropic** | Claude Opus 4.5, Claude Sonnet 4.5, Claude Haiku 4.5 | Per account |
| **Perplexity** | sonar-pro (4000 RPM), sonar-deep-research (60 RPM) | Per model |
| **Firecrawl** | Web scraping (Standard plan) | 100K credits/mo |
| **Stripe** | Payments & subscriptions | N/A |
| **Resend** | Transactional email | N/A |

### Web Scraping Strategy

| Method | Cost | Use Case |
|--------|------|----------|
| **Custom HybridScraper** | ~$0.001/page | Default, 75-80% savings |
| **Firecrawl** | ~$0.001/page | Fallback for complex pages |
| **Perplexity** | ~$0.06/query | Research with citations |

### Data Sources

- **IRS 990 Forms:** Foundation financial and grant data (6.7M grants)
- **Foundation Websites:** Mission, priorities, contacts
- **Annual Reports:** Strategic focus, recent grants
- **IRS BMF Registry:** Nonprofit organization data (1.93M orgs)
- **Public databases:** EIN matching, NTEE codes
- **Web Research:** Real-time funder intelligence via Perplexity

---

## 13. Deployment & Infrastructure

### Environments

| Environment | Frontend | API | Database |
|-------------|----------|-----|----------|
| **Production** | Vercel (kindora-prod) | Azure App Service | supabase-kindora |
| **Staging** | Vercel (kindora-staging-kzgo) | Azure (staging slot) | supabase-kindora-staging |
| **Development** | localhost:3000 | localhost:8000 | Local or staging |

### Deployment Flow

```
Feature Branch → PR → develop (staging) → main (production)
                         │                    │
                         ▼                    ▼
                   Auto-deploy           Manual approval
                   to staging            to production
```

### Key URLs

| Service | URL |
|---------|-----|
| **Production App** | https://kindora.co |
| **Production API** | https://kindora-api-avg0d5awgjgjhjhk.eastus2-01.azurewebsites.net |
| **API Docs** | /api/docs |
| **Admin Dashboard** | https://kindora-funnel-analytics.vercel.app |

### Environment Variables

```bash
# Supabase
SUPABASE_URL=https://[project].supabase.co
SUPABASE_SERVICE_KEY=[service-key]
SUPABASE_JWT_SECRET=[jwt-secret]

# AI
OPENAI_API_KEY=[key]
ANTHROPIC_CLAUDE_API_KEY=[key]
PERPLEXITY_API_KEY=[key]

# Payments
STRIPE_SECRET_KEY=[key]
STRIPE_WEBHOOK_SECRET=[secret]

# Email
RESEND_API_KEY=[key]
```

---

# Part 4: Reference

## 14. Data Assets

### Database Statistics (February 21, 2026)

| Asset | Records | Description |
|-------|---------|-------------|
| **US Foundations** | 173,491 | Foundation master data with financials |
| **Foundation Grants** | 6,715,367 | IRS 990-PF grant transactions |
| **Nonprofit Organizations** | 1,932,171 | IRS BMF registry |
| **IRS 990 Filings** | 428,728 | Form 990/990-PF filings |
| **Non-990 Funders** | 891 | Corporate, government, international funders |
| **Funder Evaluations** | 29,126 | Program-specific match scores |
| **990 Snapshots** | 142,016 | Pre-computed funder statistics |
| **Funder Leadership Records** | 90,000+ | Deduplicated board/staff profiles |
| **Client Organizations** | 258 | Active nonprofit organizations |
| **Client Programs** | 208 | Active fundraising programs |

### IRS 990 Data Pipeline

```
IRS Form 990 XML Files (Monthly Updates)
       ↓
irs_990_filings (429K)
       ↓
foundation_grants (6.7M) ←→ V4 EIN Matching (74.89%) ←→ nonprofit_organizations (1.93M)
       ↓
us_foundations (173K) - Enriched master data
       ↓
funder_990_snapshots (142K) - Pre-computed stats
       ↓
URL Validation & Enrichment - Foundation website intelligence
```

### V4 EIN Matching System

High-accuracy ML-based matching of grant recipients to nonprofit organizations:

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Embeddings** | OpenAI text-embedding-3-small | Semantic text similarity |
| **Vector Search** | FAISS index (1.2M vectors) | Fast nearest neighbor search |
| **Verification** | GPT-5-mini structured output | LLM adjudication of matches |

**Performance Metrics:**
- **Match Rate:** 74.89% of grants matched to verified EINs
- **New Matches (V4):** 275,501 additional matches
- **Accuracy:** 96%+ average confidence on verified matches
- **Cost:** ~$0.002 per verification

### Non-990 Funder Ingestion System

Comprehensive data collection for funders not in IRS 990 database (corporate, government, international):

| Phase | Status | Description | Records |
|-------|--------|-------------|---------|
| **Phase 1** | Complete | Seed List Generation | 654 funders |
| **Phase 2** | Complete | Deep Research Queries | 891 funders |
| **Phase 2B** | Complete | Staff Queries | 826 funders, 100% success |
| **Phase 5** | Complete | Grantee Discovery | 570 funders, 3,155 grantees |

**Technology Stack:**
- **Research:** Perplexity sonar-pro (fast) + sonar-deep-research (comprehensive)
- **Extraction:** GPT-5-mini with structured JSON output
- **Web Scraping:** Custom HybridScraper (75-80% cost savings vs Firecrawl)
- **Deduplication:** 4-tier matching (EIN, domain, fuzzy name, LLM adjudication)

**Cost Efficiency:**
- Perplexity sonar-pro: ~$0.06/query
- GPT-5-mini extraction: ~$0.005/query
- Grantee discovery: ~$0.012/grantee

### Foundation URL Validation & Enrichment

Validating and enriching foundation website data for 168K+ foundations:

| Phase | Status | Records | Valid Rate |
|-------|--------|---------|------------|
| **Phase 1** | Complete | 37,679 | 56.2% (21,180 valid) |
| **Phase 2** | In Progress | Remaining 130K | — |

**Benefits:**
- Verified, working foundation website URLs
- Website metadata extraction (mission, focus areas)
- Contact information enrichment
- Improved user experience with working links

### Data Security

- **Public data only:** 990 forms, annual reports, foundation websites
- **No AI training on customer data**
- **Row-level security** and encrypted storage
- **SOC 2 Type II compliance** (in progress)

---

## 15. Known Issues & Technical Debt

### High Priority

| Issue | Severity | Description |
|-------|----------|-------------|
| **Giant Components** | High | Some components exceed 30K lines, need splitting |
| **Test Coverage** | Medium | Limited automated tests |
| **Error Monitoring** | Medium | Need comprehensive Sentry setup |

### Technical Debt

- Some duplicate code between kindora-app and kindora-analytics
- Mix of Pydantic v1 and v2 patterns in API
- JSON cache files should use Redis
- Some deprecated routes need cleanup

### Recommended Improvements

| Priority | Improvement |
|----------|-------------|
| High | Refactor large components (GrantFinderChat, funder-profile-modal) |
| High | Add comprehensive test suite |
| Medium | Implement proper secrets management (Vault) |
| Medium | Add API rate limiting to all endpoints |
| Low | Consolidate shared UI components |

---

## 16. Glossary

| Term | Definition |
|------|------------|
| **Intel Brief** | AI-generated 5-8 page research report on a funder |
| **Funder** | Foundation, corporation, or grant-making organization |
| **Kira AI** | Kindora's AI assistant for grant drafting |
| **Ally** | Contextual AI chat assistant on dashboard pages |
| **Match Score** | Algorithmic fit between nonprofit and funder (0-100) |
| **Deep Dive** | Comprehensive funder analysis with scoring |
| **Peer Organization** | Similar nonprofit used for funder discovery |
| **Kira Credits** | Consumable units for AI features |
| **RLS** | Row Level Security (Supabase access control) |
| **NTEE Code** | National Taxonomy of Exempt Entities classification |
| **EIN** | Employer Identification Number (IRS tax ID) |
| **990 Form** | IRS tax form filed by nonprofits/foundations |
| **PBC** | Public Benefit Corporation |
| **TAM** | Total Addressable Market |
| **SAM** | Serviceable Addressable Market |
| **UFI** | Unified Funder Intelligence (curated funder database) |
| **Contact Enrichment** | AI-powered enhancement of funder staff profiles |
| **Network Mapping** | Tracking personal connections to funder leadership |
| **Funder Intelligence** | Premium AI-enriched insights including funding philosophy and semantic focus |
| **Funding Programs** | Active grant programs offered by a funder with deadlines and requirements |
| **SAM.gov** | System for Award Management - federal grants portal |
| **CFDA** | Catalog of Federal Domestic Assistance (grant classification codes) |
| **Pipeline** | Visual workflow tracking funder relationships through stages |
| **Board Review** | Token-based sharing system for board member application review |
| **Community Intelligence** | Crowdsourced funder insights from the Kindora nonprofit community |
| **Daily Briefing** | Aggregated dashboard widget with critical updates and opportunities |
| **Smart Evaluation** | AI-powered bulk funder fit assessment with credit tracking |
| **DAF** | Donor-Advised Fund - a charitable giving vehicle |
| **Deep Search** | Advanced AI-powered funder research using web crawling beyond 990 data |
| **Global Search** | Org-wide Cmd/Ctrl+K instant search across all platform objects |
| **Find Funders** | 5-modality filtered search across 175K+ foundations |
| **Grant Tracker** | Visual pipeline for tracking funder relationships through stages |
| **Open Grants** | Grants currently accepting applications from your funders |
| **Connections** | Network mapping feature for discovering warm introduction paths |
| **Entity Resolution** | AI matching of imported contacts to funder leadership records |
| **Activation Meter** | Dashboard widget tracking onboarding progress and platform engagement |
| **Profile Completeness** | Indicator showing how complete a user's organization profile is |
| **Help Center** | Public knowledge base with searchable guides and AI chat |
| **Skill Routing** | AI classification of user intent to select the best Ally Chat skill per conversation |
| **Pitch Practice** | Real-time voice AI coaching for funder pitch preparation |
| **Pitch Deck** | AI-generated Reveal.js presentation tailored to a specific nonprofit+funder pair |
| **Org-Fit Signals** | Visual badges on search results showing relevance to the user's organization profile |
| **Account-Level Pooling** | Consultant plan feature where credits and briefs are shared across client organizations |

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| Feb 21, 2026 | 7.0 | **Pricing Model 3.0:** Replaced Momentum/Catalyst/Agency tiers with Community ($25)/Individual ($49)/Team ($199)/Consultant ($399). Added account-level pooled billing for Consultant plan (10 client orgs). Updated Welcome Package (3 briefs + 150 credits). Updated add-on pricing ($8/brief, $18/100 credits). **New Features:** Accelerator & Incubator Discovery, Org-Aware Search Intelligence (fit signal badges, "Recommended for You" filter), Pitch Practice (real-time voice AI), Pitch Deck Generator (Reveal.js). **Ally Chat:** Expanded with 7 agentic skills (funder-discovery, funder-research, fit-evaluation, prospect-list, landscape-analysis, grant-application-prep, funder-pitch-deck). **AI Models:** Added GPT-5.2 for Intel Brief intelligence, Claude Sonnet 4.5 for Ally Chat, Claude Haiku 4.5 for skill routing, GPT-4o Realtime for Pitch Practice. **Data:** Updated stats (891 non-990 funders, 29K+ evaluations, 258 client orgs). Consolidated PLATFORM_OVERVIEW.md into this doc. |
| Feb 8, 2026 | 6.0 | Feature sync: Added Find Funders (5-modality filtered search with premium filter gating), Deep Search, Global Search (Cmd+K), Open Grants & Opportunities page, CRM Integrations (Salesforce, Blackbaud), Help Center & Knowledge Base with AI chat, Team Management, enhanced Network Mapping with LinkedIn import and entity resolution. Updated pipeline stages to match code (Prospect → Researching → Ready to Apply → Drafting → Submitted → Won/Lost). Added deal history, task management, and funder notes to pipeline. Expanded Organization Profile with completeness tracking, document uploads, PDF export, and 10+ editable sections. Added onboarding paths (Seamless/Manual/Consultant). Fixed Next.js version to 14. Updated data statistics. Added 12 new glossary terms. |
| Feb 2, 2026 | 5.0 | Major feature update: Added Funder Intelligence (premium), Funding Programs tab, Government Grants (SAM.gov), Pipeline Management (Kanban), Dashboard V2.5 widgets (Daily Briefing, Action Stack, Network Intelligence), Smart Evaluation system, Board Review sharing, Peer Organization Network, Community Intelligence, Deadline Management. Updated user journeys for Pipeline and Government Grants. |
| Jan 26, 2026 | 4.1 | Updated architecture stats (70+ routes, 230+ services, 250+ components, 500+ migrations), updated database schema (unified_funder_intelligence replaces prospect_funders, 200+ tables across schemas), refreshed data statistics, added Contact Enrichment, Network Mapping features |
| Jan 22, 2026 | 4.0 | Pricing Model 2.0 (Explore/Momentum/Catalyst/Agency tiers), updated data statistics (6.7M grants, 173K foundations, 428K filings), Non-990 Funder Ingestion System, V4 EIN Matching, Foundation URL Validation, Value Ladder UI, API Access, Saved Searches, Data Exports |
| Jan 17, 2026 | 3.0 | Major update with company overview, market analysis, founders, impact metrics from Comprehensive Company Overview |
| Jan 17, 2026 | 2.0 | Consolidated from original PLATFORM_OVERVIEW and TECHNICAL_SPECIFICATION |
| Jan 2026 | 1.0 | Original TECHNICAL_SPECIFICATION created |
| Dec 2024 | 1.0 | Original PLATFORM_OVERVIEW created |

---

*This document is the comprehensive source of truth for the Kindora platform. For specific feature documentation, see the individual guides in `/docs`.*

*Related documents:*
- *[KINDORA_USER_JOURNEY.md](KINDORA_USER_JOURNEY.md) - Detailed user flow documentation*
- *[Kindora_Data_Security_and_Privacy_Guide.md](Kindora_Data_Security_and_Privacy_Guide.md) - Security reference*
- *[PRICING_MODEL_2_0_MASTER.md](PRICING_MODEL_2_0_MASTER.md) - Complete pricing implementation guide*
- *[IRS_990_DATA_INGESTION_GUIDE.md](IRS_990_DATA_INGESTION_GUIDE.md) - 990 data pipeline documentation*
- *[NON_990_FUNDER_INGESTION_PLAN.md](NON_990_FUNDER_INGESTION_PLAN.md) - Non-990 funder data system*
- *[PHASE_6_VALUE_LADDER_UI_IMPLEMENTATION.md](PHASE_6_VALUE_LADDER_UI_IMPLEMENTATION.md) - Knowledge level indicators*
