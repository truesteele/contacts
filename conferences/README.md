# Conference Networking Toolkit

A config-driven pipeline for scoring conference attendees, generating interactive networking lookbooks, and deploying them to Vercel. One YAML file per conference parameterizes everything.

## Pipeline Overview

```
Data Acquisition → Config → Triage → Populate → Generate → Deploy
     (manual)      (YAML)   (GPT)   (Supabase)   (HTML)   (Vercel)
```

1. **Data Acquisition** — Get the attendee list (CSV/JSON) from the conference platform. Manual step.
2. **Config** — Create a YAML config and scoring prompt for your conference + organization.
3. **Triage** — GPT-5 mini scores each attendee on partnership relevance (1-10) and categorizes partnership type.
4. **Populate** — Upsert scored attendees into a Supabase table with per-user columns (pinned, notes, reached out).
5. **Generate** — Produce a self-contained HTML lookbook with search, filters, and Supabase-backed persistence.
6. **Deploy** — Push to Vercel as a static site.

## Quick Start

```bash
# Score attendees (test mode — first 3 only)
python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step triage --test

# Populate Supabase (dry run)
python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step populate --dry-run

# Generate lookbook HTML
python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step generate

# Deploy to Vercel
python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step deploy

# Run full pipeline
python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step all
```

## Creating a New Conference Config

### 1. Copy the template

```bash
cp -r conferences/ted-2026 conferences/skoll-2026
```

### 2. Edit `config.yaml`

Update all sections:

| Section | What to change |
|---------|---------------|
| `conference` | Name, slug, dates, venue, attendee count, connect URL template, field prefix, roles |
| `organization` | Your org's name, tagline, mission, colors, partnership types |
| `users.primary` | The person attending — name, bio, connection signals |
| `users.support` | The support person (optional) — name, bio |
| `supabase` | Table name (create a new table per conference), edge function |
| `vercel` | Deploy directory, alias subdomain |
| `data_paths` | Paths to your attendee JSON files |
| `tiers` | Tier labels and CSS classes |

**Key fields:**

- **`conference.field_prefix`** — Prefix for fields in your source data. If your attendee data has `skoll_firstname`, `skoll_id`, set this to `"skoll"`.
- **`conference.roles`** — Attendee roles that get special badges (e.g., Speaker, Fellow). Each needs a `field` (boolean column name) and `label`.
- **`organization.partnership_types`** — The categories GPT uses to classify attendees. Each type needs a `label`, `color_bg`, `color_fg`, and `description`. Always include `multiple` and `unlikely` as catch-all types.
- **`users.*.columns`** — Maps logical names (pinned, reached_out, notes, context) to actual Supabase column names.
- **`conference.connect_url_template`** — URL pattern for linking to attendee profiles. Use `{field_name}` placeholders matching your data fields.

### 3. Write the scoring prompt

Edit `scoring_prompt.md`. This is the system prompt GPT uses to score each attendee. Use template variables:

| Variable | Source |
|----------|--------|
| `{{conference.name}}` | Conference name |
| `{{org.name}}` | Organization name |
| `{{org.tagline}}` | Organization tagline |
| `{{org.mission}}` | Mission statement |
| `{{org.model}}` | Program model description |
| `{{org.theory_of_change}}` | Theory of change |
| `{{users.primary.name}}` | Primary user's first name |
| `{{users.primary.bio}}` | Primary user's bio (rendered as bullet list) |
| `{{users.primary.connection_signals}}` | Connection signals (rendered as bullet list) |
| `{{org.partnership_types}}` | Partnership types (rendered as numbered list) |
| `{{org.key_concepts}}` | Key concepts (comma-separated) |
| `{{org.campaign.name}}`, `{{org.campaign.goal}}`, `{{org.campaign.raised}}` | Campaign details |

The prompt should describe your organization, the primary user, what kinds of partnerships you're looking for, and how to score relevance on a 1-10 scale.

### 4. Create the Supabase table

Create a table matching your `supabase.table_name`. The populate script will create columns dynamically based on your data, but you need the table to exist first. Minimum schema:

```sql
CREATE TABLE your_conference_attendees (
  id SERIAL PRIMARY KEY,
  {prefix}_id TEXT UNIQUE,  -- e.g., skoll_id
  {prefix}_firstname TEXT,
  {prefix}_lastname TEXT,
  relevance_score INTEGER,
  partnership_type TEXT,
  tier INTEGER
  -- ... additional fields added by populate script
);
```

Enable RLS with a permissive anon read/write policy (the lookbook reads/writes via the anon key).

### 5. Add conference config to Edge Function

If you want the "Add New Person" feature in the lookbook, insert a row into `conference_config`:

```sql
INSERT INTO conference_config (slug, name, scoring_prompt, partnership_types, primary_user_name, table_name)
VALUES (
  'skoll-2026',
  'Skoll World Forum 2026',
  '... your scoring prompt ...',
  '["funding", "media_storytelling", "programmatic", "multiple", "unlikely"]',
  'Sally',
  'skoll_attendees'
);
```

Then set `supabase.edge_function: "conference-enrich"` in your config to use the generic function.

### 6. Run the pipeline

```bash
python scripts/conference/run.py --config conferences/skoll-2026/config.yaml --step all
```

## Deep Writeups (Optional)

For shortlisted contacts, you can create detailed writeups that appear in the lookbook. Create a Python module (e.g., `scripts/intelligence/skoll_deep_writeups.py`) with a `DEEP_WRITEUPS` dict:

```python
DEEP_WRITEUPS = {
    "attendee-id-1": """
    <p>Detailed writeup about this person...</p>
    """,
    "attendee-id-2": """
    <p>Another writeup...</p>
    """,
}
```

Set `data_paths.deep_writeups_module` in your config to the module name (without `.py`).

## Required Secrets

Set these in your `.env` file:

| Variable | Purpose |
|----------|---------|
| `OPENAI_APIKEY` | GPT-5 mini for scoring |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `APIFY_API_KEY` | LinkedIn scraping (Edge Function only) |

## File Structure

```
conferences/
  ted-2026/
    config.yaml          # All conference-specific values
    scoring_prompt.md    # GPT scoring system prompt
  README.md              # This file

scripts/conference/
  __init__.py
  config.py              # Config loader with typed access + template substitution
  triage.py              # GPT scoring pipeline
  populate.py            # Supabase population
  generate_lookbook.py   # HTML generator
  run.py                 # CLI entry point
```
