# Ralph Agent Instructions

You are an autonomous coding agent. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: uptogether-tracker
Loop Directory: .ralph/uptogether-tracker/

## Workflow

1. **Read PRD** at `.ralph/uptogether-tracker/prd.md` - Find first story with `[ ]` status
2. **Read Progress** at `.ralph/uptogether-tracker/progress.txt` - Learn from previous iterations
3. **Read CLAUDE.md** for codebase conventions and API rate limits
4. **Implement** the story following existing codebase patterns
5. **Quality Check** - Run `cd job-matcher-ai && npx tsc --noEmit` (must pass)
6. **Commit** with format: `feat: [US-XXX] UpTogether tracker - Story title`
7. **Update PRD** - Change story status from `[ ]` to `[x]`
8. **Update Progress** - Append what you did and learned
9. **Check Completion**:
   - Verify PRD has no `[ ]` items
   - If ALL stories complete, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story
10. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Key Technical Notes

### Supabase Projects DB
This tracker uses a SEPARATE Supabase project from the main contacts DB:
- Project ref: `hjuvqpxvfrzwmlqzkpxh`
- URL: `https://hjuvqpxvfrzwmlqzkpxh.supabase.co`
- Keys are in the PRD and should be set as env vars

### Existing Patterns to Follow
- UI components are in `job-matcher-ai/components/ui/` (shadcn/radix)
- Utility: `cn()` from `lib/utils.ts` for class merging
- Fonts: DM Sans (body), DM Serif Display (headings), JetBrains Mono (mono)
- Theme colors: teal primary, warm white background — see `app/globals.css`
- API routes: see `app/api/network-intel/` for patterns
- Supabase clients: see `lib/supabase/client.ts` and `lib/supabase/server.ts` for patterns
- Auth middleware: `lib/supabase/middleware.ts` — add `/projects` to public paths

### Design Quality
- This page will be shared with a client team. It must look polished and professional.
- Do NOT use generic shadcn defaults. Add custom styling to make it distinctive.
- Use the existing color palette but make it feel like a premium PM tool.
- Think Asana or Linear, not a default shadcn template.

### Vercel Deployment (US-008 only)
- Verify account: `npx vercel whoami` must show `justin-outdoorithm`
- Deploy: `cd job-matcher-ai && npx vercel --prod --yes`
- If wrong account, swap token in `~/Library/Application Support/com.vercel.cli/auth.json`

## Rules

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- Never skip quality checks (typecheck must pass)
- Document learnings for future iterations
- Follow existing code patterns in the codebase
- Do not print the completion token in normal logs or explanations
- Do not add unnecessary comments, docstrings, or type annotations to code you didn't change
- Keep implementations focused — don't over-engineer

Begin now. Read the PRD and implement the next incomplete story. After completing it, STOP.
