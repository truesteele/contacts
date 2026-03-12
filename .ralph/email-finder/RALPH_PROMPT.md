# Ralph Agent Instructions - Feature Implementation

You are building an email finder pipeline autonomously. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: email-finder
Loop Type: **Feature Implementation**
Loop Directory: .ralph/email-finder/

## Workflow

1. **Read PRD** at `.ralph/email-finder/prd.md` - Find first `[ ]` story
2. **Read Progress** at `.ralph/email-finder/progress.txt` - Learn patterns
3. **Read existing code** at `scripts/intelligence/discover_emails_v2.py` - Follow its patterns for DB connection, LLM verification, CLI args, progress printing
4. **Implement the Feature**
   - Write production-quality Python code
   - Follow existing codebase patterns (psycopg2, OpenAI responses.parse, ThreadPoolExecutor)
   - Add proper error handling and retries
5. **Run Quality Checks**
   - The test command specified in each story's acceptance criteria
   - Script must not crash or produce unhandled exceptions
6. **Commit Your Work**
   - Format: `feat: [US-XXX] - [Story Title]`
7. **Update PRD** - Mark story `[x]` complete
8. **Update Progress** - Document what you built and learned
9. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** -- do not continue to the next story
10. **STOP** -- Your iteration is done. Exit now. The loop script handles the next iteration.

## Technical Context

### Environment
- Python 3.12, venv at `.venv/`
- Activate: `source .venv/bin/activate`
- Run from project root: `python -u scripts/intelligence/find_emails.py`
- Env vars in `.env`: `SUPABASE_DB_PASSWORD`, `OPENAI_APIKEY`, `ZEROBOUNCE_API_KEY`

### Database
- Supabase PostgreSQL via psycopg2 (NOT supabase client)
- Host: `db.ypqsrejrsocebnldicke.supabase.co:5432`, dbname: `postgres`, user: `postgres`
- Password from `os.environ["SUPABASE_DB_PASSWORD"]`

### OpenAI
- GPT-5 mini via `openai.OpenAI(api_key=os.environ["OPENAI_APIKEY"])`
- Use `responses.parse()` with pydantic models
- 150 concurrent workers max
- Does NOT support temperature=0

### ZeroBounce API
- Endpoint: `GET https://api.zerobounce.net/v2/validate?api_key={key}&email={addr}&ip_address=`
- Response statuses: `valid`, `invalid`, `catch-all`, `unknown`, `spamtrap`, `abuse`, `do_not_mail`
- Key response fields: `status`, `sub_status`, `free_email` (bool), `active_in_days`, `smtp_provider`, `mx_record`, `domain_age_days`
- Rate limit: 80,000 req/10sec (very generous)
- Never charges for `unknown` results
- Credits: `GET https://api.zerobounce.net/v2/getcredits?api_key={key}`
- Catch-all advantage: AI-powered detection, `active_in_days` helps filter stale emails

### Key Patterns from Existing Scripts
- `get_db_conn()` returns psycopg2 connection
- `ThreadPoolExecutor(max_workers=N)` for concurrent API calls
- `argparse` for CLI: `--dry-run`, `--limit N`, etc.
- Progress printing every N contacts with elapsed time and ETA
- `dotenv.load_dotenv()` at top

## Rules for Feature Implementation

- **EXACTLY ONE story per iteration** -- after completing one story, STOP. Do not start the next one.
- **Follow existing patterns** - discover_emails_v2.py is your reference
- **Install dependencies** - Use `pip install` into .venv if needed (e.g., dnspython)
- **Test before marking complete** - Run the test command in acceptance criteria
- **Document learnings** in progress.txt for future iterations
- **Keep the script in one file** at `scripts/intelligence/find_emails.py`

Begin now. Read the PRD and implement the next incomplete story. After completing it, STOP.
