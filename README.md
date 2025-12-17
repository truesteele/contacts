# Contact Management System

A comprehensive contact management system for importing, enriching, and searching professional contacts from LinkedIn and other sources. Includes AI-powered job candidate search capabilities.

## 📁 Repository Structure

```
contacts/
├── data/                           # CSV data files from LinkedIn and other sources
│   ├── Connections_Updated.csv    # Latest LinkedIn connections export
│   ├── ClayExport*.csv           # Clay.com enrichment exports
│   └── *.csv                      # Other data sources
│
├── scripts/                       # Organized Python scripts
│   ├── import/                   # Contact import scripts
│   │   ├── import_linkedin_supabase.py  # Main LinkedIn importer with deduplication
│   │   ├── batch_upload_to_supabase.py  # Batch upload utility
│   │   └── update_clay_emails.py        # Import Clay enrichment data
│   │
│   ├── enrichment/               # Data enrichment scripts
│   │   ├── enrich_linkedin_profiles.py  # Enrich profiles via Enrich Layer API
│   │   ├── enrich_all_emails.py        # Find personal/work emails
│   │   ├── enrich_personal_emails.py   # Personal email finder
│   │   └── domain_enrichment.py        # Company domain enrichment
│   │
│   ├── parsing/                  # Data parsing and cleaning
│   │   ├── parse_locations.py          # Parse location_name to city/state/country
│   │   ├── parse_locations_with_ai.py  # AI-powered location parsing
│   │   └── parse_all_locations_comprehensive.py  # Full location parsing
│   │
│   ├── job_searches/             # Recruitment search scripts
│   │   ├── evaluate_crankstart_detailed.py       # Crankstart role search (final version)
│   │   └── evaluate_raikes_comprehensive.py      # Raikes Foundation ED search
│   │
│   └── utilities/                # Utility and helper scripts
│       ├── check_contacts.py     # Database verification
│       ├── categorize_contacts.py # Contact categorization
│       └── verify_emails.py      # Email validation
│
├── outputs/                      # Generated output files
│   ├── job_searches/            # Job search results
│   │   ├── crankstart_*.json   # Crankstart candidate evaluations
│   │   └── raikes_*.json       # Raikes Foundation evaluations
│   └── enrichment_reports/      # Enrichment reports
│
├── archive/                      # Archived intermediate/test versions
├── migrations/                   # Database migration files
├── .env                         # Environment variables (API keys, etc.)
├── .mcp.json                    # MCP server configuration
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Key Features

- **LinkedIn Import with Deduplication**: Smart import that tracks employment changes
- **AI-Powered Job Search**: Evaluate candidates with GPT-4 for specific roles
- **Location Parsing**: Convert messy location data into searchable city/state/country
- **Profile Enrichment**: Enhance LinkedIn profiles with additional data (1 credit/profile)
- **Email Discovery**: Find personal and work emails (~24% success rate)
- **Contact Categorization**: Categorize contacts into custom taxonomy using OpenAI
- **Supabase Integration**: Centralized database with change tracking
- **ZeroBounce Integration**: Verify email addresses without sending emails
- **MailerLite Integration**: Sync contacts for email marketing campaigns

## 🚀 Quick Start

### Prerequisites

1. Python 3.8+
2. Supabase account with configured database
3. API keys for:
   - OpenAI (for AI-powered features)
   - Enrich Layer (for profile enrichment)
   - Supabase (database access)

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure `.env` file:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-service-key
   OPENAI_APIKEY=your-openai-key
   ENRICH_LAYER_API_KEY=your-enrich-key
   OPENAI_MODEL=gpt-4o-mini
   ```

## 📚 Core Workflows

### 1. Import LinkedIn Contacts

Import new LinkedIn connections while handling duplicates and tracking changes:

```bash
python scripts/import/import_linkedin_supabase.py
```

Features:
- Deduplicates based on LinkedIn URL
- Tracks employment changes (company/position)
- Updates existing records
- Preserves email addresses

### 2. Enrich Contact Data

#### Enrich LinkedIn Profiles
```bash
python scripts/enrichment/enrich_linkedin_profiles.py
```
- Fetches detailed profile information
- Uses 1 credit per profile (optimized from 10)
- Adds headline, summary, and experience data

#### Find Email Addresses
```bash
python scripts/enrichment/enrich_all_emails.py
```
- Searches for personal email addresses
- ~24% success rate
- Tracks attempted lookups to avoid duplicates

### 3. Parse Locations

Clean and structure location data for better searchability:

```bash
# Standard parsing
python scripts/parsing/parse_locations.py

# AI-powered parsing for complex cases
python scripts/parsing/parse_locations_with_ai.py
```

Converts: "San Francisco Bay Area, United States" → 
- City: San Francisco
- State: California  
- Country: United States

### 4. Search for Job Candidates

Run comprehensive candidate searches with AI evaluation:

```bash
# For Bay Area mid-level roles (Crankstart)
python scripts/job_searches/evaluate_crankstart_detailed.py

# For executive searches (WA/OR - Raikes Foundation)
python scripts/job_searches/evaluate_raikes_comprehensive.py
```

Features:
- AI-powered candidate evaluation
- Seniority assessment
- Detailed fit scoring
- Interview priority ranking
- Exports to JSON and HTML reports

## 📊 Database Schema

### Main `contacts` Table

| Column | Type | Description |
|--------|------|-------------|
| id | integer | Unique identifier |
| first_name | text | Contact's first name |
| last_name | text | Contact's last name |
| email | text | Email address |
| linkedin_url | text | LinkedIn profile URL (unique) |
| company | text | Current company |
| position | text | Current position |
| city | text | Parsed city |
| state | text | Parsed state/province |
| country | text | Parsed country |
| location_name | text | Original location string |
| headline | text | LinkedIn headline |
| summary | text | Profile summary |
| previous_company | text | Previous company (change tracking) |
| previous_position | text | Previous position (change tracking) |
| company_updated_at | timestamp | When company changed |
| position_updated_at | timestamp | When position changed |
| last_import_date | timestamp | Last import/update |
| enrich_person_from_profile | jsonb | Enrichment data |
| email_verified | boolean | Email verification status |
| work_email | text | Work email address |
| personal_email | text | Personal email address |

## 📈 Statistics

Current database status (as of September 2024):
- **Total contacts**: ~2,850
- **Parsed locations**: 82.3% (2,342 contacts)
- **With email addresses**: ~500
- **Washington/Oregon**: 59 contacts
- **California (Bay Area)**: ~600 contacts
- **Successfully enriched**: 453 profiles
- **Email discovery rate**: 24.2%

## Taxonomy Categories

The scripts categorize contacts into the following taxonomy:

### Strategic Business Prospects
- **Corporate Impact Leaders**: CSR/DEI/Impact executives who could use Fractional CIO services
- **Foundation Executives**: Leaders at foundations who make funding decisions
- **Nonprofit Executives**: Leaders who might need impact strategy consulting
- **Corporate Partners**: Companies interested in AI for social good/partnerships

### Knowledge & Industry Network
- **AI/Tech Innovators**: People working in AI who might collaborate on AI ventures
- **Social Impact Practitioners**: People working directly in social impact fields
- **Environmental Champions**: Contacts focused on environmental/outdoor issues
- **Thought Leaders**: Speakers, authors, and influencers in relevant fields
- **Philanthropy Professionals**: People working in grantmaking or fundraising

### Newsletter Audience
- **Social Impact Professionals**: Mid-level professionals interested in transformation
- **DEI Practitioners**: People working in diversity, equity, and inclusion
- **Potential Subscribers**: People likely interested in "The Long Arc" content

### Support Network
- **Investors/Funders**: VCs, angels, and philanthropic funders
- **Mentors/Advisors**: People with expertise to guide your ventures
- **Connectors**: People with large networks who can make introductions
- **Former Colleagues**: People you've worked with who might support your work

### Personal Network
- **Friends/Family**: Personal connections without business relevance
- **Outdoorithm Community**: People interested in outdoor activities/community

### Low Priority
- **Out of Scope**: People whose work is unrelated to your current ventures
- **Weak Connection**: People with whom you have minimal relationship

## Setup

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your API keys and configuration:
   ```
   OPENAI_API_KEY=your_openai_api_key
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_KEY=your_supabase_service_key
   PERPLEXITY_APIKEY=your_perplexity_api_key
   ZEROBOUNCE_API_KEY=your_zerobounce_api_key
   MAILERLITE_API_KEY=your_mailerlite_api_key
   ```

## Using the Domain Enrichment Script

The `domain_enrichment.py` script enhances your contacts by finding company website domains. It uses a combination of API services and database caching to efficiently discover domains.

### Key Features of Domain Enrichment

- **Database Caching**: Reuses domains found for the same company names
- **No-Domain Marking**: Marks companies where no domain could be found to avoid future API calls
- **Pagination**: Processes contacts in batches with offset capabilities
- **Retry Logic**: Handles API failures gracefully
- **Non-Company Detection**: Identifies entries that are role descriptions rather than actual companies
- **API Rate Limiting**: Automatically handles rate limits for Perplexity and OpenAI APIs

### Basic Usage

Process all contacts missing domains:
```
python domain_enrichment.py --batch-size 100 --delay 1.5
```

Process with specific parameters:
```
python domain_enrichment.py --batch-size 100 --delay 1.5 --offset 200 --max-records 500
```

Re-check contacts previously marked as having no domain:
```
python domain_enrichment.py --batch-size 100 --delay 1.5 --include-previously-not-found
```

Process only a single batch (instead of all contacts):
```
python domain_enrichment.py --batch-size 100 --delay 1.5 --single-batch
```

### How Domain Enrichment Works

1. Finds contacts with company information but missing domains
2. Checks if the domain exists for the same company elsewhere in the database
3. If not found in the database, uses Perplexity API to search for the domain
4. Uses OpenAI to normalize and validate the domain format
5. Updates the contact record in Supabase
6. For companies where no domain is found, marks them with a special value (`NO_DOMAIN_MARKER`) to avoid future lookups
7. For entries identified as roles or titles rather than companies, they are tracked separately in statistics

### Processing Modes

The script supports two processing modes:

1. **All Contacts Mode (Default)**: Processes all contacts in the database using pagination to handle large datasets efficiently
2. **Single Batch Mode**: Processes only a specific batch of contacts (useful for testing or targeted updates)

### Rate Limit Handling

The script is optimized to respect API rate limits:

- Perplexity API: Default delay configured for 40 requests per minute (within their 50 RPM limit)
- OpenAI API: Default delay configured for 400 requests per minute (within their 500 RPM limit)
- These values can be customized using the `--delay` parameter

## Using the ZeroBounce Email Verification Scripts

The project includes two main scripts for email verification using ZeroBounce API:

1. **verify_emails.py**: Verifies email addresses for any contacts in the database
2. **verify_and_update_mailerlite.py**: Specifically verifies and handles emails synced to MailerLite
3. **fix_catch_all_emails.py**: Fixes previously processed catch-all domains that were marked as invalid

### Key Features of ZeroBounce Email Verification

- **No-Send Verification**: Verifies email validity without sending actual emails to contacts
- **Individual & Batch Verification**: Supports both single email and batch verification
- **Verification Status Tracking**: Maintains detailed verification history and status
- **Smart Re-verification Scheduling**: Sets different schedules based on email validity
- **Credit Management**: Monitors and efficiently uses ZeroBounce API credits
- **Catch-All Domain Handling**: Treats catch-all domains as valid with special tagging
- **MailerLite Integration**: Option to update invalid emails in MailerLite

### Basic Usage

Verify emails for contacts that haven't been verified yet:
```
python verify_emails.py --batch-size 100
```

Verify a single email address:
```
python verify_emails.py --single-email "test@example.com"
```

Verify only contacts from a specific taxonomy:
```
python verify_emails.py --taxonomy "Strategic Business Prospects"
```

Verify contacts synced to MailerLite and update invalid ones:
```
python verify_and_update_mailerlite.py
```

Test the verification process without making changes:
```
python verify_and_update_mailerlite.py --dry-run
```

Fix catch-all emails previously marked as invalid:
```
python fix_catch_all_emails.py
```

### How ZeroBounce Email Verification Works

1. **verify_emails.py**:
   - Retrieves contacts from Supabase that need verification (never verified or due for re-verification)
   - Uses ZeroBounce API to check email validity
   - Updates Supabase with verification results and sets next verification due date
   - Treats catch-all domains as valid with special flagging
   - Generates statistics on verification results

2. **verify_and_update_mailerlite.py**:
   - Focuses specifically on contacts that have been synced to MailerLite
   - Verifies all email types (primary, work, personal)
   - Handles catch-all domains differently from truly invalid emails
   - For invalid emails:
     - Updates Supabase records with verification status
     - Changes contact status in MailerLite to "unsubscribed"
     - Adds contacts to an "Invalid Emails" group in MailerLite
     - Tags contacts with "Invalid Email" tag
   - For catch-all domains:
     - Treats them as valid but tags them with "Catch-All Domain" in MailerLite
     - Keeps them as active subscribers
     - Generates a separate CSV report for catch-all domains

3. **fix_catch_all_emails.py**:
   - Identifies contacts previously marked as invalid due to being catch-all domains
   - Updates them to be treated as valid with the appropriate catch-all flag
   - Optionally fixes their status in MailerLite:
     - Resubscribes them if they were unsubscribed
     - Removes them from "Invalid Emails" group
     - Adds "Catch-All Domain" tag
     - Removes "Invalid Email" tag

### Email Verification Status Management

The scripts maintain comprehensive email health tracking:
- Valid emails are scheduled for re-verification in 90 days
- Catch-all domains are treated as valid but tracked separately
- Truly invalid emails are scheduled for re-verification in 180 days
- Verification source, timestamp, and attempt count are tracked
- Comprehensive reporting on status distribution
- Separate CSV reports for invalid and catch-all emails

### Understanding Catch-All Domains

A catch-all domain is one that accepts all emails sent to it, regardless of whether the specific mailbox exists. Many large companies, universities, and organizations use catch-all configurations, making these emails often valid despite ZeroBounce's categorization.

The system handles catch-all domains as follows:
- Marks them as valid (email_verified = TRUE) but with a special flag (email_is_catch_all = TRUE)
- In MailerLite, keeps them as active subscribers but adds a "Catch-All Domain" tag
- Re-verifies them on the same schedule as valid emails (90 days)
- Maintains separate reporting for monitoring purposes

## Using the Email Verification & Enrichment Script

The `update_clay_emails.py` script updates your Supabase contacts with email verification and work email data from Clay.com exports. It maintains a comprehensive email health tracking system.

### Key Features of Email Verification & Enrichment

- **Email Verification**: Updates contact records with email validation results
- **Work Email Discovery**: Adds work emails found via Clay's enrichment
- **Email Type Classification**: Distinguishes between work and personal emails
- **Verification Health Tracking**: Tracks when emails were verified and when they need re-verification
- **Smart Scheduling**: Sets different re-verification intervals based on email validity (90 days for valid, 180 days for invalid)

### Basic Usage

Process Clay.com export with email verification data:
```
python update_clay_emails.py
```

### How Email Verification Works

1. Adds necessary columns to track email verification status in Supabase
2. Processes a CSV file from Clay.com containing email verification results
3. For each contact:
   - Updates the email verification status (valid/invalid)
   - Records the verification source, timestamp, and attempt count
   - Sets a due date for the next verification based on the result
   - Updates work and personal email fields as appropriate
   - Classifies emails as 'work', 'personal', or 'unknown' type
4. Maintains email verification health through scheduled re-verification

### Creating Targeted Email Lists

After enriching your contacts with both domain and email data, you can create highly targeted outreach lists:

```sql
-- Example query for creating a targeted email list
SELECT 
  id,
  first_name,
  last_name,
  work_email,
  company,
  position,
  company_domain_experience
FROM 
  contacts
WHERE 
  taxonomy_classification LIKE 'Strategic Business Prospects%'
  AND email_verified = true
  AND work_email IS NOT NULL
  AND email_verification_due_at > CURRENT_TIMESTAMP
ORDER BY 
  taxonomy_classification;
```

## Using the Email Classification Script

The `classify_existing_emails.py` script classifies emails in your Supabase database as either work or personal emails based on patterns and domain analysis.

### Key Features of Email Classification

- **Intelligent Classification**: Uses OpenAI to analyze email patterns and determine if they're work or personal emails
- **Context-Aware**: Takes company name and domain into account when classifying
- **Confidence Scoring**: Includes a confidence score for each classification
- **Batch Processing**: Efficiently processes contacts in batches
- **Organization**: Places emails in appropriate work_email or personal_email columns

### Basic Usage

Process all contacts with unclassified emails:
```
python classify_existing_emails.py
```

Process with specific parameters:
```
python classify_existing_emails.py --batch-size 50 --offset 100
```

### How Email Classification Works

1. Finds contacts with emails that haven't been classified yet
2. Uses OpenAI to analyze each email address based on:
   - Email domain patterns (company domains vs. public email providers)
   - Name formats (professional formats vs. personal identifiers)
   - Company context (matching company domain or name)
3. Classifies each email as 'work', 'personal', or 'unknown'
4. Organizes emails into the appropriate columns:
   - `work_email`: For professional email addresses
   - `personal_email`: For personal email addresses
   - Maintains original `email` field for backward compatibility

## Using the Bay Area Leads Uploader

The `bay_area_leads_upload.py` script is specifically designed for processing and uploading Bay Area Philanthropy leads to Supabase.

### Usage

```
python bay_area_leads_upload.py --input ./data/Bay-Area-Philanthropy-Leads.csv --openai-batch 10 --supabase-batch 25
```

The script:
1. Uses `column_mapping.py` to standardize CSV column names
2. Checks for existing contacts in Supabase to avoid duplicates
3. Classifies contacts using OpenAI's taxonomy
4. Uploads new contacts to Supabase in batches

## Supabase Database Schema

The contact management system uses a Supabase database with a comprehensive schema designed to store detailed contact information and support advanced features like email verification and classification.

### Contacts Table Structure

The main `contacts` table includes the following key field groups:

#### Basic Contact Information
- `id`: Integer, Primary Key (auto-incrementing)
- `first_name`, `last_name`: Text fields for contact names
- `email`, `email_2`: Text fields for contact email addresses
- `normalized_phone_number`: Text field for standardized phone numbers
- `company`, `position`: Text fields for professional information
- `country`, `location_name`: Text fields for geographic information
- `created_at`: Timestamp with timezone (default: current time)

#### Email Management & Verification
- `email_verified`: Boolean flag indicating if the email is verified
- `email_is_catch_all`: Boolean flag indicating if the email is from a catch-all domain
- `email_type`: Character varying (10) - categorizes email type (work/personal)
- `work_email`, `personal_email`: Character varying (255) - categorized email addresses
- `email_verified_at`: Timestamp of last verification
- `email_verification_source`: Character varying (50) - source of verification
- `email_verification_attempts`: Integer - count of verification attempts
- `email_verification_due_at`: Timestamp - when reverification is needed
- `work_email_discovery_status`: Character varying (50) - status of work email discovery
- `work_email_discovery_date`: Timestamp - when work email was discovered

#### MailerLite Integration
- `synced_to_mailerlite`: Boolean - indicates if the contact is synced to MailerLite
- `mailerlite_subscriber_id`: Character varying (255) - MailerLite subscriber ID
- `mailerlite_sync_date`: Timestamp - when the contact was last synced
- `mailerlite_update_required`: Boolean - indicates if the contact needs updating in MailerLite
- `mailerlite_update_reason`: Text - reason why the contact needs updating

#### Professional Experience & Education
- Fields for experience: `summary_experience`, `company_experience`, `company_domain_experience`, etc.
- Fields for education: `school_name_education`, `degree_education`, `field_of_study_education`, etc.
- Fields for projects: `title_projects`, `summary_projects`, etc.
- Fields for publications: `title_publications`, `publisher_publications`, etc.
- Fields for volunteering: `company_name_volunteering`, `role_volunteering`, etc.
- Fields for awards: `title_awards`, `summary_awards`, etc.

#### LinkedIn-specific Data
- `linkedin_url`, `linkedin_profile`: Text fields for LinkedIn profile links
- `headline`, `summary`: Text fields for LinkedIn profile content
- `connections`, `num_followers`: Text fields for LinkedIn network metrics

#### Categorization & Analysis
- `taxonomy_classification`: User-defined type for contact categorization
- `normalized_first_name`, `normalized_last_name`, `normalized_full_name`: Text fields for standardized names

This comprehensive schema supports the various scripts in this repository, enabling advanced contact management, enrichment, and targeted outreach features.

## MailerLite Integration

This project includes a comprehensive integration with MailerLite for email marketing campaigns. The integration allows you to sync your Supabase contacts to MailerLite, organize them into groups based on taxonomy classifications, and track unsubscribes.

### Features

- **Taxonomy-Based Groups**: Automatically creates and assigns contacts to groups based on their taxonomy classification.
- **Selective Syncing**: Only syncs contacts with verified email addresses to maintain high deliverability.
- **Unsubscribe Tracking**: Automatically updates contact status in Supabase when someone unsubscribes in MailerLite.
- **Smart Email Selection**: Prioritizes work emails over personal emails for B2B communications.
- **Batch Processing**: Efficiently processes large contact lists in batches.
- **Email Verification**: Integrates with ZeroBounce to verify email addresses without sending any emails to contacts.
- **Catch-All Domain Handling**: Specially tags catch-all domains while keeping them as active subscribers.
- **Invalid Email Management**: Specially handles truly invalid emails in MailerLite by tagging, grouping, and unsubscribing them.

### Scripts Included

1. **sync_to_mailerlite.py**: Main script for syncing contacts from Supabase to MailerLite.
2. **setup_mailerlite_groups.py**: Creates and manages MailerLite groups based on taxonomy categories.
3. **track_unsubscribes.py**: Monitors and processes unsubscribes from MailerLite.
4. **verify_emails.py**: Verifies email addresses using ZeroBounce API without sending actual emails.
5. **verify_and_update_mailerlite.py**: Verifies emails synced to MailerLite and handles invalid ones appropriately.
6. **add_mailerlite_columns.sql**: Sets up necessary database schema for the integration.

For detailed setup and usage instructions, see [MAILERLITE-INTEGRATION.md](./MAILERLITE-INTEGRATION.md).

## Strategy for Using These Tools

1. **Start with categorization**: Process your contacts to understand their relevance to your business
2. **Upload to Supabase**: Create a centralized database of all your contacts
3. **Setup database schema**: Run SQL scripts to add necessary columns for advanced features
4. **Enrich with domains**: Add company domains to enable better outreach
5. **Verify emails with ZeroBounce**: Validate existing emails to maintain email deliverability
6. **Find and classify emails**: Discover and categorize work and personal emails 
7. **Maintain email health**: Regularly verify emails to keep your database clean
8. **Sync to MailerLite**: Send verified contacts to MailerLite for email campaigns
9. **Manage invalid emails**: Handle invalid emails properly in both Supabase and MailerLite
10. **Targeted outreach**: Export specific categories for targeted campaigns
11. **Regular updates**: Process new contacts as you acquire them

This complete workflow ensures you maintain an organized, enriched contact database with healthy email data that's ready for strategic outreach and email marketing campaigns. 