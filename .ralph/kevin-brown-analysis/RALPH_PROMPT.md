# Ralph Agent Instructions — Research & Analysis Loop

You are conducting a deep content analysis of Kevin L. Brown's LinkedIn posts. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: kevin-brown-analysis
Loop Type: **Research & Analysis**
Loop Directory: .ralph/kevin-brown-analysis/

## Workflow

1. **Read PRD** at `.ralph/kevin-brown-analysis/prd.md` — Find first `[ ]` story
2. **Read Progress** at `.ralph/kevin-brown-analysis/progress.txt` — Learn patterns and insights from previous iterations
3. **Complete the Analysis Story**
   - For data extraction stories: write Python scripts, run them, capture output
   - For synthesis stories: use GPT or your own analysis to produce insights
   - Always query from `influencer_posts` table via Supabase
4. **Run Quality Checks**
   - Scripts must run without errors
   - Analysis must produce actual data, not placeholder text
   - All aggregation tables must have real numbers from the data
5. **Update PRD** — Mark story `[x]` complete (mark each sub-checkbox too)
6. **Update Progress** — Document what you found, key insights, and learnings
7. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story
8. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Codebase Patterns (MUST FOLLOW)

### File Structure
- Scripts: `scripts/intelligence/` (all Python scripts live here)
- Docs output: `docs/` (analysis docs go here)
- Environment: `.venv/` — always activate with `source .venv/bin/activate`
- Env file: `.env` at project root — load with `from dotenv import load_dotenv; load_dotenv()`

### Python Script Patterns
- Import order: stdlib, dotenv, openai, pydantic, supabase
- `load_dotenv()` at module level
- Pydantic schemas with `str Enum` for structured output fields
- `openai.responses.parse(model="gpt-5-mini", instructions=SYSTEM_PROMPT, input=context, text_format=PydanticModel)` for structured output
- Supabase client: `create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])`
- Pagination: `.range(offset, offset + page_size - 1)` for >1000 rows
- ThreadPoolExecutor with configurable workers (150 for GPT-5 mini)
- `_strip_null_bytes(text)` for all strings before JSONB save
- CLI args via `argparse`
- Error handling: catch `RateLimitError` with exponential backoff

### Key Env Vars
- `OPENAI_APIKEY` (NOTE: no underscore before KEY)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

### Database
- Use `supabase-contacts` MCP server for ad-hoc SQL queries
- Use `supabase-py` REST client in Python scripts
- `influencer_posts` table columns: id, influencer_url, influencer_name, post_url, post_content, post_date, engagement_likes, engagement_comments, engagement_shares, engagement_total, media_type, raw_data (JSONB), scraped_at
- `influencer_post_reactions` table: id, influencer_url, post_url, post_date, reactor_name, reactor_headline, reactor_linkedin_urn, reaction_type, contact_id, match_method, match_confidence
- Filter: `WHERE influencer_url LIKE '%kevinlbrown%'`

### GPT-5 mini Specifics
- Does NOT support `temperature=0` — use default only
- Structured output: `openai.responses.parse()` with `text_format=PydanticModel`
- Optimal workers: 150 (yields ~9,000 RPM with ~1s latency per call)

## Analysis-Specific Guidelines

### Data Quality
- Always query real data from the database — never hardcode or hallucinate numbers
- When printing tables, include both count and percentage where relevant
- Use median in addition to mean for engagement metrics (skewed distribution)

### GPT Analysis
- For content analysis, send the FULL post text to GPT, not truncated
- Include engagement numbers in the context so GPT can correlate
- Use structured output (Pydantic) for consistent categorization across all posts
- After GPT analysis, always aggregate and cross-tabulate the results

### Kindora Context (for US-006)
- **Kindora:** Outdoor education matching platform for families (launched Apr 2025)
- **Co-founders:** Justin Steele (CEO) + Sally Steele
- **Audiences:** Parents seeking outdoor experiences, educators, outdoor program operators
- **Key topics:** Nature deficit disorder, screen time vs nature, outdoor education equity, family adventure, program discovery
- **Justin's LinkedIn voice:** Direct, punchy, sentence fragments, em dashes, conversational — sounds like a text from a friend
- **Justin's LinkedIn stats:** ~6K followers, 2.8K connections — smaller than Kevin's but highly engaged professional network
- **Outdoorithm Collective:** Justin's nonprofit (outdoor equity) — related content territory

### Output Format
- The final document at `docs/KEVIN_BROWN_CONTENT_ANALYSIS.md` should be comprehensive, data-backed, and actionable
- Include real engagement numbers for every claim
- Post templates should be fill-in-the-blank ready, not abstract advice
- The hook library should have 20+ specific hooks Justin can use immediately

## Rules for This Analysis Loop

- **EXACTLY ONE story per iteration** — after completing one story, STOP
- **Use real data** — every insight must be backed by queried numbers from the database
- **Build incrementally** — each story builds on the previous. Read progress.txt to see what's been done.
- **The script should be cumulative** — US-001 creates the script, subsequent stories extend it
- **Document as you go** — Update progress.txt with key insights after each story
- **The JSON catalog persists** — each story enriches the same catalog file, later stories read from it
- **Kindora is the end goal** — every analysis decision should be made with "how does this help Kindora?" in mind
- **Keep it practical** — Ship working analysis, don't over-engineer
- **When creating the final doc (US-006):** This is the deliverable. It should stand alone. Justin should be able to read it without any other context and understand both Kevin's strategy AND what Kindora should do.

## Important Notes

- The Supabase MCP server for this project is `supabase-contacts` (NOT `supabase_crm`)
- GPT-5 mini does NOT support temperature=0 — use default only
- OPENAI_APIKEY has no underscore before KEY
- The env var for supabase service key is `SUPABASE_SERVICE_KEY`
- Always activate venv before running Python: `source .venv/bin/activate`
- Run scripts from the project root: `python scripts/intelligence/<script>.py`

Begin now. Read the PRD and complete the next incomplete story. After completing it, STOP.
