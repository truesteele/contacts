# Ralph Wiggum Method for Claude Code

> **Version**: 4.0.0
> **Last Updated**: January 25, 2026
>
> This document describes the **shell script approach** to running autonomous Ralph loops. This is the community-recommended method that spawns fresh Claude sessions per iteration, providing superior context management compared to the official plugin.
>
> **NEW in v4.0**: Three specialized loop types for complete development workflow - Feature Implementation → Production Readiness Evaluation → UI/Brand Review

---

## 🤖 CLAUDE: Auto-Setup Instructions

**If you are Claude Code reading this document**, follow these instructions to set up and run a Ralph loop for the user.

### When to Use These Instructions

Use this section when the user:
1. Gives you this document along with their project requirements
2. Asks you to "set up Ralph" or "run Ralph" for their project
3. Provides a requirements doc, PRD, or feature description and wants autonomous implementation

### Auto-Setup Workflow

**Step 1: Gather Requirements**

If the user has not provided a requirements document, ask them:
```
"What would you like me to build? You can:
1. Describe the feature/project in plain text
2. Provide a requirements document
3. Point me to an existing PRD or spec file

Once I understand what you want, I'll set up the Ralph loop to build it autonomously."
```

**Step 2: Create a Named Ralph Loop Directory**

Each Ralph loop gets its own subfolder to avoid conflicts:

```bash
# Create named subfolder for this specific loop
mkdir -p .ralph/<loop-name>

# Examples:
mkdir -p .ralph/priority-system
mkdir -p .ralph/auth-flow
mkdir -p .ralph/dashboard-v2
```

**Naming Convention:**
- Use kebab-case: `feature-name`
- Be descriptive: `user-priority-badges` not `feature1`
- Include version if iterating: `auth-v2`, `dashboard-redesign`

**Directory Structure (Multiple Loops):**
```
your-project/
├── .ralph/
│   ├── priority-system/          # First feature
│   │   ├── ralph.sh
│   │   ├── logs/                 # Iteration output (created on first run)
│   │   ├── prd.md
│   │   ├── progress.txt
│   │   └── RALPH_PROMPT.md
│   ├── auth-flow/                # Second feature
│   │   ├── ralph.sh
│   │   ├── logs/                 # Iteration output (created on first run)
│   │   ├── prd.md
│   │   ├── progress.txt
│   │   └── RALPH_PROMPT.md
│   └── dashboard-v2/             # Third feature
│       ├── ralph.sh
│       ├── logs/                 # Iteration output (created on first run)
│       ├── prd.md
│       ├── progress.txt
│       └── RALPH_PROMPT.md
├── src/
└── ...
```

**Step 3: Generate the PRD from Requirements**

Convert the user's requirements into a properly formatted `prd.md`:

1. **Analyze the requirements** - Identify discrete features and tasks
2. **Break into user stories** - Each story should complete within one Claude session (one iteration)
3. **Order by dependency** - Database → Types → Backend → Frontend → Tests
4. **Add quality gates** - Every story must include typecheck/test pass criteria
5. **Use checkbox format** - `[ ]` for incomplete, `[x]` for complete

**PRD Generation Template:**

```markdown
# Project: [Extract from requirements]

## Overview
[Summarize what the user wants to build]

## Technical Context
- Tech Stack: [Detect from codebase or ask user]
- Existing Patterns: [Note any discovered patterns]

## User Stories

### US-001: [First Task - Usually Database/Schema]
**Priority:** 1
**Status:** [ ] Incomplete

**Description:**
[Convert requirement to user story format]

**Acceptance Criteria:**
- [ ] [Specific, verifiable criterion 1]
- [ ] [Specific, verifiable criterion 2]
- [ ] Typecheck passes
- [ ] Tests pass (if applicable)

---

### US-002: [Second Task]
**Priority:** 2
**Status:** [ ] Incomplete

[Continue for all identified tasks...]
```

**Story Sizing Rules:**
- ✅ One database migration
- ✅ One API endpoint
- ✅ One UI component
- ✅ One set of tests
- ❌ "Build the whole feature" (too big - split it)
- ❌ "Implement authentication" (too big - split into login, logout, protected routes, etc.)

**Step 4: Create ralph.sh**

**⚠️ IMPORTANT**: Before creating the script, read the [Claude CLI Invocation Pattern](#ralphsh---the-loop-script) section to understand the correct way to invoke Claude. Common mistake: building the prompt in the shell script instead of piping RALPH_PROMPT.md.

**Recommended approach - Copy from existing working loop:**
```bash
# Copy proven working script from existing loop
cp .ralph/pricing-fixes/ralph.sh .ralph/<loop-name>/ralph.sh

# Update the header message to match your loop name
sed -i '' 's/Pricing Fixes/<Your Loop Name>/g' .ralph/<loop-name>/ralph.sh
```

**Alternative - Copy from template:**
Copy the production-hardened script from the [ralph.sh section](#ralphsh---the-loop-script) below into `.ralph/<loop-name>/ralph.sh`. It includes:
- Dependency checks (`claude` CLI)
- Safe defaults and explicit opt-in for `--dangerously-skip-permissions`
- Per-iteration log files
- A lock file to prevent concurrent runs
- Completion token verification against the PRD
- **CRITICAL**: Correct Claude invocation pattern (`claude "${CLAUDE_ARGS[@]}" < "$PROMPT_FILE"`)

Then make it executable:
```bash
chmod +x .ralph/<loop-name>/ralph.sh
```

**Verify the Claude invocation is correct:**
```bash
# Check that your script uses the correct pattern
grep 'claude.*<.*PROMPT_FILE' .ralph/<loop-name>/ralph.sh
# Should output: claude "${CLAUDE_ARGS[@]}" < "$PROMPT_FILE" 2>&1 | tee "$ITERATION_LOG"
```

**Step 5: Create RALPH_PROMPT.md**

Write the Claude instructions to `.ralph/<loop-name>/RALPH_PROMPT.md`:

```markdown
# Ralph Agent Instructions

You are an autonomous coding agent. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: <loop-name>
Loop Directory: .ralph/<loop-name>/

## Workflow

1. **Read PRD** at `.ralph/<loop-name>/prd.md` - Find first story with `[ ]` status
2. **Read Progress** at `.ralph/<loop-name>/progress.txt` - Learn from previous iterations
3. **Implement** the story following existing codebase patterns
4. **Quality Check** - Run typecheck and tests (must pass)
5. **Commit** with format: `feat: [US-XXX] - Story title`
6. **Update PRD** - Change story status from `[ ]` to `[x]`
7. **Update Progress** - Append what you did and learned
8. **Check Completion**:
   - Verify PRD has no `[ ]` items
   - If ALL stories complete, output `<promise>COMPLETE</promise>` (must match `RALPH_COMPLETE_TOKEN` if overridden)
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story
9. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Rules

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- Never skip quality checks
- Document learnings for future iterations
- Follow existing code patterns
- Do not print the completion token in normal logs or explanations

Begin now. Read the PRD and implement the next incomplete story. After completing it, STOP.
```

**Step 6: Initialize progress.txt**

Create the progress log:

```bash
cat > .ralph/<loop-name>/progress.txt << 'EOF'
# Ralph Progress Log
Loop: <loop-name>
Started: [CURRENT_DATE]
---

## Codebase Patterns
(Will be discovered and added during iterations)

---

## Iteration Log
EOF
```

**Step 7: Verify Setup**

Before running, verify all files exist:
```bash
ls -la .ralph/<loop-name>/
# Should show: ralph.sh, prd.md, progress.txt, RALPH_PROMPT.md (logs/ appears after first run)
```

**Step 8: Run the Loop**

Execute the Ralph loop:
```bash
RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 15  # Adjust iterations based on PRD size
```

**Listing All Ralph Loops:**
```bash
ls -la .ralph/
# Shows all loop directories: priority-system/, auth-flow/, dashboard-v2/
```

**Running a Specific Loop:**
```bash
# Run the priority-system loop
RALPH_ALLOW_DANGEROUS=1 ./.ralph/priority-system/ralph.sh 20

# Run the auth-flow loop
RALPH_ALLOW_DANGEROUS=1 ./.ralph/auth-flow/ralph.sh 15
```

### Example: Converting User Requirements to PRD

**User says:** "I want to add a priority system to my task app. Tasks should have high/medium/low priority, show a colored badge, and be sortable."

**Generated PRD:**

```markdown
# Project: Task Priority System

## Overview
Add priority levels to tasks with visual indicators and sorting.

## User Stories

### US-001: Add Priority Field to Database
**Priority:** 1
**Status:** [ ] Incomplete

**Description:**
As a developer, I need a priority field in the database to store task priorities.

**Acceptance Criteria:**
- [ ] Add `priority` column to tasks table (enum: high, medium, low)
- [ ] Default value is `medium`
- [ ] Migration runs successfully
- [ ] Typecheck passes

---

### US-002: Update Task Type Definitions
**Priority:** 2
**Status:** [ ] Incomplete

**Description:**
As a developer, I need TypeScript types updated to include priority.

**Acceptance Criteria:**
- [ ] Task interface includes `priority: 'high' | 'medium' | 'low'`
- [ ] All existing code compiles
- [ ] Typecheck passes

---

### US-003: Create Priority Badge Component
**Priority:** 3
**Status:** [ ] Incomplete

**Description:**
As a user, I want to see a colored badge showing task priority.

**Acceptance Criteria:**
- [ ] PriorityBadge component created
- [ ] Colors: red=high, yellow=medium, gray=low
- [ ] Accessible (aria-label)
- [ ] Component tests pass
- [ ] Typecheck passes

---

### US-004: Add Priority Badge to TaskCard
**Priority:** 4
**Status:** [ ] Incomplete

**Description:**
As a user, I want to see priority on my task cards.

**Acceptance Criteria:**
- [ ] TaskCard shows PriorityBadge
- [ ] Badge position is consistent
- [ ] Typecheck passes
- [ ] Existing tests pass

---

### US-005: Add Priority Sorting
**Priority:** 5
**Status:** [ ] Incomplete

**Description:**
As a user, I want to sort tasks by priority.

**Acceptance Criteria:**
- [ ] Sort dropdown includes "Priority" option
- [ ] High priority tasks sort first
- [ ] Sort persists across page refresh
- [ ] Typecheck passes
- [ ] Tests pass
```

### Checklist Before Running Ralph

Before starting the loop, verify:

- [ ] `claude` CLI is installed and on your PATH
- [ ] `.ralph/<loop-name>/ralph.sh` exists and is executable
- [ ] `.ralph/<loop-name>/prd.md` has properly formatted user stories with `[ ]` checkboxes
- [ ] `.ralph/<loop-name>/RALPH_PROMPT.md` has Claude instructions
- [ ] `.ralph/<loop-name>/progress.txt` exists (can be empty header)
- [ ] `RALPH_ALLOW_DANGEROUS=1` is set if you want unattended runs
- [ ] User stories are right-sized (one per iteration)
- [ ] Stories are ordered by dependency
- [ ] Each story has verifiable acceptance criteria
- [ ] Quality gates (typecheck, tests) are included

### After Setup Message

After creating all files, tell the user:

```
✅ Ralph loop "<loop-name>" is ready!

Created files in .ralph/<loop-name>/:
- ralph.sh (loop script)
- prd.md ([X] user stories)
- RALPH_PROMPT.md (Claude instructions)
- progress.txt (iteration log)
- logs/ (iteration output; created on first run)

To start autonomous development:
  RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 15

Ralph will work through each story, running quality checks and committing as it goes.
Watch progress with: tail -f .ralph/<loop-name>/progress.txt
Inspect iteration output in: .ralph/<loop-name>/logs/

Stop anytime with Ctrl+C - progress is saved.

To list all Ralph loops: ls -la .ralph/
```

---

## Ralph Loop Types: Three-Stage Development Process

**CRITICAL FOR CLAUDE**: When the user asks you to create a Ralph loop, you MUST determine which loop type they need. Do NOT default to Feature Implementation if they're asking for quality checks, UI reviews, or evaluations.

### Overview

Ralph loops are specialized for different phases of development. Using the right loop type ensures appropriate story structure, evaluation patterns, and quality gates.

| Loop Type | Purpose | When to Use | Primary Output |
|-----------|---------|-------------|----------------|
| **Feature Implementation** | Build new functionality | User wants features developed | Working code commits |
| **Production Readiness Evaluation** | Quality assurance checks | Before production deployment | Evaluation reports |
| **UI/Brand Review** | Design & brand compliance | After features built, before launch | Design improvement reports |

**Typical Workflow:**
```
1. Feature Implementation Loop
   ↓ (builds features)

2. Production Readiness Evaluation Loop
   ↓ (identifies quality issues)

3. UI/Brand Review Loop
   ↓ (validates design standards)

4. Production Deployment
```

---

### Loop Type 1: Feature Implementation

**Use when:** User wants to build new features, add functionality, or implement requirements.

**Key Characteristics:**
- Stories = discrete features to implement
- Each iteration commits code changes
- Focus on functionality first, quality second
- Heavy use of tests to verify behavior

**PRD Structure Pattern:**

```markdown
# Project: [Feature Name] - Implementation

## Overview
Building [feature description] with [key capabilities].

## Technical Context
- Tech Stack: [Framework, database, etc.]
- Existing Patterns: [Conventions to follow]
- Related Features: [Dependencies]

## User Stories

### US-001: [Database/Schema Change]
**Priority:** 1
**Status:** [ ] Incomplete

**Description:**
As a developer, I need [data model] so that [feature] can store data.

**Acceptance Criteria:**
- [ ] Create migration for [table/column]
- [ ] Add validation rules
- [ ] Update TypeScript types
- [ ] Migration runs successfully
- [ ] Typecheck passes
- [ ] Tests pass

---

### US-002: [Backend API Endpoint]
**Priority:** 2
**Status:** [ ] Incomplete

**Description:**
As a frontend, I need an API endpoint to [action] so that users can [benefit].

**Acceptance Criteria:**
- [ ] Create POST/GET endpoint at [path]
- [ ] Implement business logic
- [ ] Add request/response validation
- [ ] Write API tests
- [ ] Typecheck passes
- [ ] All tests pass

---

### US-003: [UI Component]
**Priority:** 3
**Status:** [ ] Incomplete

**Description:**
As a user, I want to [action] via [UI element] so that I can [benefit].

**Acceptance Criteria:**
- [ ] Create [Component] with [props]
- [ ] Implement [interaction] behavior
- [ ] Add loading and error states
- [ ] Write component tests
- [ ] Typecheck passes
- [ ] Tests pass
- [ ] Accessibility check (ARIA labels, keyboard navigation)

---
```

**RALPH_PROMPT.md Template:**

```markdown
# Ralph Agent Instructions - Feature Implementation

You are building new features autonomously. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: [loop-name]
Loop Type: **Feature Implementation**
Loop Directory: .ralph/[loop-name]/

## Workflow

1. **Read PRD** at `.ralph/[loop-name]/prd.md` - Find first `[ ]` story
2. **Read Progress** at `.ralph/[loop-name]/progress.txt` - Learn patterns
3. **Implement the Feature**
   - Write production-quality code
   - Follow existing codebase patterns
   - Add proper error handling
   - Include TypeScript types
4. **Write Tests**
   - Unit tests for business logic
   - Integration tests for API endpoints
   - Component tests for UI elements
5. **Run Quality Checks**
   - TypeScript: `npm run type-check` (must pass)
   - Tests: `npm test` (must pass)
   - Lint: `npm run lint` (should pass)
6. **Commit Your Work**
   - Format: `feat: [US-XXX] - [Story Title]`
   - Example: `feat: [US-001] - Add priority field to tasks`
7. **Update PRD** - Mark story `[x]` complete
8. **Update Progress** - Document what you built and learned
9. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story
10. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Rules for Feature Implementation

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- **Always write tests** - No untested code
- **Follow existing patterns** - Check similar features first
- **Document as you go** - Update progress.txt with learnings
- **Never skip quality checks** - Broken builds compound across iterations

## Code Quality Standards

- All functions have explicit TypeScript types
- All user inputs are validated
- All errors are properly handled
- All components have loading/error states
- All interactive elements are keyboard accessible
- All tests pass before marking story complete

Begin now. Read the PRD and implement the next incomplete story. After completing it, STOP.
```

**Example Naming:**
- `.ralph/mobile-web-parity` - Build mobile app features
- `.ralph/user-authentication` - Add auth system
- `.ralph/payment-integration` - Stripe payments

---

### Loop Type 2: Production Readiness Evaluation

**Use when:** Features are built, now checking if code is ready for production deployment.

**Key Characteristics:**
- Stories = evaluation tasks (run checks, document findings)
- Most iterations DO NOT commit code (evaluation only)
- Some stories may fix issues found during evaluation
- Focus on quality, security, performance, compliance

**PRD Structure Pattern:**

```markdown
# Project: [App Name] - Production Readiness Evaluation

## Overview
Systematic evaluation of production readiness across code quality, security, performance, accessibility, and store requirements.

## Evaluation Patterns

### Report Structure
All evaluation reports should include:
- Executive Summary (total issues, severity breakdown)
- Detailed Findings (file paths, severity, descriptions, recommendations)
- Recommendations (prioritized action items)
- Impact Assessment (production readiness verdict)

### Severity Definitions
- **Critical**: Blocks App Store/Play Store submission or causes crashes
- **High**: Significant user impact, security risk, or quality issue
- **Medium**: Moderate user impact, minor security concern
- **Low**: Minor issue, code smell, or nice-to-have improvement

## User Stories

### WORKSTREAM 1: CODE QUALITY

#### PR-001: Run TypeScript Type Check & Fix Errors
**Priority:** 1
**Status:** [ ] Incomplete
**Type:** EVALUATION

**Description:**
As a developer, I want to ensure zero TypeScript errors before production deployment.

**Acceptance Criteria:**
- [ ] Run `npx tsc --noEmit`
- [ ] Document all errors found
- [ ] Create report at `docs/reports/typescript-errors-report.md`
- [ ] Assess production readiness impact
- [ ] Note: This is EVALUATION only - do not fix errors (unless story says "Fix")

**Report Template:**
```
# TypeScript Error Report (PR-001)

**Generated**: [Date]
**Evaluator**: Ralph Agent

## Executive Summary
- Total errors: X
- Critical: X | High: X | Medium: X | Low: X

## Detailed Findings
[List each error with file path, severity, recommendation]

## Production Readiness
✅ PASSED / ⚠️ NEEDS WORK / ❌ BLOCKED
```

---

#### PR-002: Run ESLint & Document Issues
**Priority:** 2
**Status:** [ ] Incomplete
**Type:** EVALUATION

**Description:**
Check for code quality issues, potential bugs, and style violations.

**Acceptance Criteria:**
- [ ] Run `npm run lint`
- [ ] Document all errors and warnings
- [ ] Create report at `docs/reports/eslint-report.md`
- [ ] Categorize by severity
- [ ] Note: EVALUATION only - do not fix issues

---

### WORKSTREAM 2: SECURITY

#### PR-005: Audit API Keys & Secrets Exposure
**Priority:** 5
**Status:** [ ] Incomplete
**Type:** EVALUATION

**Description:**
Scan codebase for hardcoded secrets, API keys, or sensitive data.

**Acceptance Criteria:**
- [ ] Search for common secret patterns (sk_live, AKIA, etc.)
- [ ] Check for hardcoded passwords or tokens
- [ ] Verify environment variables are used correctly
- [ ] Document findings in `docs/reports/security-audit-report.md`
- [ ] Assess severity of any exposures

---

### WORKSTREAM 3: PERFORMANCE

#### PR-008: Analyze Bundle Size
**Priority:** 8
**Status:** [ ] Incomplete
**Type:** EVALUATION

**Description:**
Measure JavaScript bundle size and identify optimization opportunities.

**Acceptance Criteria:**
- [ ] Run production build
- [ ] Document bundle sizes
- [ ] Identify large dependencies
- [ ] Compare against industry benchmarks
- [ ] Create report at `docs/reports/bundle-analysis-report.md`

---

### WORKSTREAM 4: FINAL REPORT

#### PR-030: Create Production Readiness Report
**Priority:** 30
**Status:** [ ] Incomplete
**Type:** SYNTHESIS

**Description:**
Synthesize all evaluation findings into final production readiness report.

**Acceptance Criteria:**
- [ ] Read all evaluation reports (PR-001 through PR-029)
- [ ] Summarize critical blockers
- [ ] List high-priority recommendations
- [ ] Provide go/no-go verdict for production
- [ ] Create final report at `docs/PRODUCTION_READINESS_REPORT.md`

---
```

**RALPH_PROMPT.md Template:**

```markdown
# Ralph Agent Instructions - Production Readiness Evaluation

You are evaluating production readiness. Complete exactly ONE evaluation story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: [loop-name]
Loop Type: **Production Readiness Evaluation**
Loop Directory: .ralph/[loop-name]/

## Workflow

1. **Read PRD** at `.ralph/[loop-name]/prd.md` - Find first `[ ]` evaluation story
2. **Read Progress** at `.ralph/[loop-name]/progress.txt` - Learn from past evaluations
3. **Run the Evaluation**
   - Execute the check/audit specified in the story
   - Collect ALL findings (do not filter or summarize prematurely)
   - Document specific file paths, line numbers, and code snippets
4. **Create Detailed Report**
   - Use the report template from the PRD
   - Categorize findings by severity (Critical, High, Medium, Low)
   - Provide specific, actionable recommendations
   - Save report to specified location (e.g., `docs/reports/`)
5. **DO NOT FIX ISSUES** (unless story explicitly says "Fix")
   - Evaluation stories document problems, they don't solve them
   - Fixing comes later in separate "Fix" stories if needed
6. **Update PRD** - Mark evaluation story `[x]` complete
7. **Update Progress** - Summarize findings and learnings
8. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story
9. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Rules for Production Readiness Evaluation

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- **EVALUATION vs. FIX**: Most stories are evaluation-only. Do NOT commit code changes unless story title contains "Fix"
- **Be thorough**: Run the FULL check. Don't skip steps to save time.
- **Document everything**: Include file paths, line numbers, severity, and recommendations
- **Severity matters**: Use the PRD's severity definitions consistently
- **Reports are deliverables**: They should be comprehensive enough for a developer to act on

## Severity Definitions (from PRD)

- **Critical**: Blocks App Store/Play Store submission or causes app crashes
- **High**: Significant user impact, security risk, or quality issue
- **Medium**: Moderate user impact, minor security concern, or maintenance issue
- **Low**: Minor issue, code smell, or nice-to-have improvement

## Evaluation vs. Fix Stories

**EVALUATION stories** (most stories in this loop):
- Run checks (linting, type checking, security audits, accessibility tests)
- Document findings in detail
- Create reports (save to `docs/` or embed in progress.txt)
- Do NOT commit code changes
- Mark criteria complete when evaluation is done

**FIX stories** (occasional):
- Implement fixes for issues found in evaluation stories
- Commit changes with clear messages
- Update tests if needed
- Verify fixes work
- Reference which evaluation report is being addressed

Begin now. Read the PRD and run the next incomplete evaluation. After completing it, STOP.
```

**Example Naming:**
- `.ralph/mobile-production-readiness` - Pre-launch quality checks
- `.ralph/security-audit-q1` - Quarterly security review
- `.ralph/performance-evaluation` - Performance optimization assessment

---

### Loop Type 3: UI/Brand Review

**Use when:** Features are built and working, now checking visual design, brand compliance, and UX best practices.

**Key Characteristics:**
- Stories = UI/UX evaluation tasks
- Most iterations DO NOT commit code (evaluation only)
- Focus on visual consistency, accessibility, brand adherence
- Some stories may fix design issues found

**PRD Structure Pattern:**

```markdown
# Project: [App Name] - UI/Brand Review

## Overview
Systematic review of user interface design, brand guideline adherence, and UX best practices.

## Brand Guidelines Reference
- Primary Colors: [List from brand guide]
- Typography: [Font families, sizes, weights]
- Component Patterns: [Buttons, cards, etc.]
- Spacing/Layout: [Grid system, margins, padding]
- Accessibility: [WCAG level, contrast ratios]

## Evaluation Patterns

### Severity Definitions
- **Critical**: Brand violation, accessibility failure, unusable UI
- **High**: Inconsistent design, poor UX, minor accessibility issue
- **Medium**: Style inconsistency, suboptimal UX
- **Low**: Polish, nice-to-have improvements

## User Stories

### WORKSTREAM 1: BRAND COMPLIANCE

#### UI-001: Audit Color Usage Against Brand Guidelines
**Priority:** 1
**Status:** [ ] Incomplete
**Type:** EVALUATION

**Description:**
Verify all UI elements use approved brand colors, no arbitrary hex codes.

**Acceptance Criteria:**
- [ ] Scan all component files for color usage
- [ ] Identify colors not in brand palette
- [ ] Check for hardcoded hex values instead of design tokens
- [ ] Document violations in `docs/reports/color-audit-report.md`
- [ ] Assess severity of each violation

---

#### UI-002: Verify Typography Consistency
**Priority:** 2
**Status:** [ ] Incomplete
**Type:** EVALUATION

**Description:**
Ensure all text uses approved fonts, sizes, and weights from brand guidelines.

**Acceptance Criteria:**
- [ ] Audit all headings (h1-h6) for font family
- [ ] Check body text for approved font stack
- [ ] Identify any custom font sizes not in design system
- [ ] Document findings in `docs/reports/typography-audit-report.md`

---

### WORKSTREAM 2: COMPONENT CONSISTENCY

#### UI-005: Audit Button Styles Across App
**Priority:** 5
**Status:** [ ] Incomplete
**Type:** EVALUATION

**Description:**
Verify all buttons follow design system patterns (variants, sizes, states).

**Acceptance Criteria:**
- [ ] Find all button implementations
- [ ] Check for consistent variants (primary, secondary, tertiary)
- [ ] Verify disabled and loading states exist
- [ ] Identify custom one-off button styles
- [ ] Document in `docs/reports/button-audit-report.md`

---

### WORKSTREAM 3: ACCESSIBILITY

#### UI-010: Check Color Contrast Ratios
**Priority:** 10
**Status:** [ ] Incomplete
**Type:** EVALUATION

**Description:**
Verify all text meets WCAG AA contrast requirements (4.5:1 for normal text).

**Acceptance Criteria:**
- [ ] Test foreground/background color combinations
- [ ] Identify contrast failures
- [ ] Check focus states have visible indicators
- [ ] Document failures in `docs/reports/contrast-audit-report.md`

---

### WORKSTREAM 4: USER EXPERIENCE

#### UI-015: Evaluate Form Validation UX
**Priority:** 15
**Status:** [ ] Incomplete
**Type:** EVALUATION

**Description:**
Review all forms for clear error messages, helpful hints, and good UX.

**Acceptance Criteria:**
- [ ] Test all form validation scenarios
- [ ] Check error message clarity
- [ ] Verify inline validation vs. submit-time validation
- [ ] Document UX issues in `docs/reports/form-ux-report.md`

---

### WORKSTREAM 5: FINAL REPORT

#### UI-030: Create UI/Brand Compliance Report
**Priority:** 30
**Status:** [ ] Incomplete
**Type:** SYNTHESIS

**Description:**
Synthesize all UI/brand findings into final compliance report.

**Acceptance Criteria:**
- [ ] Read all UI evaluation reports (UI-001 through UI-029)
- [ ] Summarize critical brand violations
- [ ] List high-priority design improvements
- [ ] Provide go/no-go verdict for brand approval
- [ ] Create final report at `docs/UI_BRAND_COMPLIANCE_REPORT.md`

---
```

**RALPH_PROMPT.md Template:**

```markdown
# Ralph Agent Instructions - UI/Brand Review

You are evaluating UI design and brand compliance. Complete exactly ONE review story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: [loop-name]
Loop Type: **UI/Brand Review**
Loop Directory: .ralph/[loop-name]/

## Brand Guidelines Reference

**CRITICAL**: Always reference the project's brand guidelines (e.g., `docs/BRAND_GUIDELINES.md`) when evaluating:
- Colors: [Primary brand colors]
- Typography: [Approved fonts]
- Component patterns: [Button styles, card styles, etc.]
- Spacing: [Grid system]
- Accessibility: [WCAG level]

## Workflow

1. **Read PRD** at `.ralph/[loop-name]/prd.md` - Find first `[ ]` UI review story
2. **Read Progress** at `.ralph/[loop-name]/progress.txt` - Learn from past reviews
3. **Read Brand Guidelines** - Refresh on approved colors, fonts, components
4. **Run the UI Review**
   - Scan relevant files for the UI element being reviewed
   - Compare against brand guidelines
   - Test visual consistency across different screens
   - Check accessibility (color contrast, keyboard navigation, ARIA)
5. **Create Detailed Report**
   - Document specific violations with file paths and line numbers
   - Include screenshots or visual examples when helpful
   - Categorize by severity (Critical, High, Medium, Low)
   - Provide specific recommendations (e.g., "Change #FF5733 to brand orange #F47B20")
   - Save report to specified location
6. **DO NOT FIX ISSUES** (unless story explicitly says "Fix")
   - UI review stories document design problems, they don't solve them
   - Design fixes come later in separate "Fix" stories if needed
7. **Update PRD** - Mark review story `[x]` complete
8. **Update Progress** - Summarize findings and learnings
9. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story
10. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Rules for UI/Brand Review

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- **ALWAYS reference brand guidelines** - Don't guess approved colors/fonts
- **Visual consistency matters** - Same UI pattern should look identical everywhere
- **Accessibility is non-negotiable** - WCAG compliance is mandatory
- **Document with specifics** - "Button is wrong color" ❌ vs. "Button uses #FF5733 instead of brand orange #F47B20" ✅
- **Screenshots help** - Include visual examples in reports when useful

## Severity Definitions

- **Critical**: Brand violation visible to all users, accessibility failure (WCAG fail), unusable UI
- **High**: Inconsistent design across screens, poor UX, minor accessibility issue
- **Medium**: Style inconsistency, suboptimal UX, polish needed
- **Low**: Nice-to-have improvements, minor polish

## Common Issues to Check

- Hardcoded colors instead of design tokens
- Custom button styles instead of component variants
- Inconsistent spacing (magic numbers instead of spacing scale)
- Missing focus states (keyboard accessibility)
- Poor color contrast (text readability)
- Inconsistent font usage (mixing font families)
- Missing loading/error states

Begin now. Read the brand guidelines, then read the PRD and run the next incomplete UI review. After completing it, STOP.
```

**Example Naming:**
- `.ralph/mobile-ui-review` - Pre-launch design audit
- `.ralph/brand-compliance-q2` - Quarterly brand check
- `.ralph/accessibility-audit` - WCAG compliance review

---

### Decision Matrix: Which Loop Type Should I Use?

**Use this decision tree when setting up a Ralph loop:**

```
Is the user asking to BUILD features or EVALUATE existing code?

├─ BUILD features
│  └─ Use: Feature Implementation Loop
│     Examples:
│     - "Add user authentication"
│     - "Build a dashboard"
│     - "Implement payment processing"
│
└─ EVALUATE existing code
   │
   ├─ What kind of evaluation?
   │
   ├─ Code quality, security, performance, testing
   │  └─ Use: Production Readiness Evaluation Loop
   │     Examples:
   │     - "Check if app is ready for production"
   │     - "Audit security vulnerabilities"
   │     - "Run all quality checks before launch"
   │
   └─ Design, branding, UX, accessibility
      └─ Use: UI/Brand Review Loop
         Examples:
         - "Check if UI follows brand guidelines"
         - "Review all button styles for consistency"
         - "Audit color contrast for accessibility"
```

**Red Flags (User is asking for evaluation, NOT implementation):**
- "Check if...", "Audit...", "Review...", "Evaluate..."
- "Is the app ready for production?"
- "Do we have any security issues?"
- "Does the UI follow our brand guidelines?"
- "Find all instances of..."

**Green Flags (User is asking for implementation):**
- "Build...", "Add...", "Implement...", "Create..."
- "I want to add a feature that..."
- "Can you build a dashboard that..."
- "Let's implement authentication"

---

### Sequential Loop Pattern (Recommended Workflow)

For a complete feature from conception to production:

**Phase 1: Feature Implementation Loop**
```bash
mkdir -p .ralph/mobile-web-parity
# ... create PRD with feature stories ...
RALPH_ALLOW_DANGEROUS=1 ./.ralph/mobile-web-parity/ralph.sh 50
```

**Result**: Working features with 40 stories implemented ✅

**Phase 2: Production Readiness Evaluation Loop**
```bash
mkdir -p .ralph/mobile-production-readiness
# ... create PRD with evaluation stories ...
RALPH_ALLOW_DANGEROUS=1 ./.ralph/mobile-production-readiness/ralph.sh 30
```

**Result**: Comprehensive quality reports identifying 15 issues ✅

**Phase 3: UI/Brand Review Loop**
```bash
mkdir -p .ralph/mobile-ui-review
# ... create PRD with UI review stories ...
RALPH_ALLOW_DANGEROUS=1 ./.ralph/mobile-ui-review/ralph.sh 20
```

**Result**: Brand compliance verified, 8 design improvements identified ✅

**Phase 4: Fix Loop (if needed)**
```bash
mkdir -p .ralph/mobile-pre-launch-fixes
# ... create PRD with fix stories from evaluation findings ...
RALPH_ALLOW_DANGEROUS=1 ./.ralph/mobile-pre-launch-fixes/ralph.sh 25
```

**Result**: All critical and high-priority issues resolved ✅

**Phase 5: Production Deployment** 🚀

---

## Table of Contents

- [🤖 CLAUDE: Auto-Setup Instructions](#-claude-auto-setup-instructions) ← **START HERE if giving this to Claude**
- [Ralph Loop Types: Three-Stage Development Process](#ralph-loop-types-three-stage-development-process) ← **CHOOSE THE RIGHT LOOP TYPE**
  - [Loop Type 1: Feature Implementation](#loop-type-1-feature-implementation)
  - [Loop Type 2: Production Readiness Evaluation](#loop-type-2-production-readiness-evaluation)
  - [Loop Type 3: UI/Brand Review](#loop-type-3-uibrand-review)
  - [Decision Matrix: Which Loop Type Should I Use?](#decision-matrix-which-loop-type-should-i-use)
  - [Sequential Loop Pattern (Recommended Workflow)](#sequential-loop-pattern-recommended-workflow)
- [Why Not the Official Plugin?](#why-not-the-official-plugin)
- [How the Shell Script Approach Works](#how-the-shell-script-approach-works)
- [Quick Start](#quick-start)
- [File Structure](#file-structure)
  - [ralph.sh - The Loop Script](#ralphsh---the-loop-script)
  - [prd.md - Product Requirements Document](#prdmd---product-requirements-document)
  - [progress.txt - Iteration Learnings](#progresstxt---iteration-learnings)
  - [RALPH_PROMPT.md - Claude Instructions](#ralph_promptmd---claude-instructions)
- [Step-by-Step Setup](#step-by-step-setup)
- [Creating Your PRD](#creating-your-prd)
- [Running the Loop](#running-the-loop)
- [Best Practices](#best-practices)
- [Advanced Patterns](#advanced-patterns)
- [Troubleshooting](#troubleshooting)
- [Resources](#resources)

---

## Why Not the Official Plugin?

The official `ralph-wiggum` plugin has a critical limitation: **it doesn't start fresh sessions**.

**Official Plugin Behavior:**
```
Claude works → Tries to exit → Hook blocks exit → Continues in SAME session
                                                    ↓
                                        Context window fills up
                                                    ↓
                                        Eventually auto-compacts
                                                    ↓
                                        Quality degrades over time
```

**Shell Script Approach (Recommended):**
```
Iteration 1: Fresh Claude session → Works → Updates progress → Exits
                                                                ↓
Iteration 2: Fresh Claude session → Reads progress → Works → Updates → Exits
                                                                        ↓
Iteration N: Fresh Claude session → Reads progress → All done? → <promise>COMPLETE</promise>
```

**Key Advantages of Shell Script Approach:**

| Aspect | Official Plugin | Shell Script |
|--------|-----------------|--------------|
| Context per iteration | Accumulated/degraded | Fresh every time |
| Memory management | Auto-compact only | Clean slate per iteration |
| Progress persistence | In-session only | File-based (survives crashes) |
| Debugging | Hard to inspect | Read prd.md and progress.txt |
| Resumability | Restart from scratch | Continue from last checkpoint |

---

## How the Shell Script Approach Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RALPH LOOP ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ralph.sh                                                            │
│     │                                                                │
│     ├──► Iteration 1 ──────────────────────────────────────────────┐│
│     │    │                                                         ││
│     │    │  1. Start NEW Claude Code session                       ││
│     │    │  2. Claude reads RALPH_PROMPT.md (instructions)         ││
│     │    │  3. Claude reads prd.md (finds first unchecked task)    ││
│     │    │  4. Claude reads progress.txt (learns from past)        ││
│     │    │  5. Claude implements the task                          ││
│     │    │  6. Claude runs quality checks (typecheck, test, lint)  ││
│     │    │  7. Claude marks task [x] in prd.md                     ││
│     │    │  8. Claude appends learnings to progress.txt            ││
│     │    │  9. Claude exits                                        ││
│     │    │                                                         ││
│     │    └─────────────────────────────────────────────────────────┘│
│     │                                                                │
│     ├──► Iteration 2 (same process, fresh context)                  │
│     │                                                                │
│     ├──► ...                                                         │
│     │                                                                │
│     └──► Iteration N                                                 │
│          │                                                           │
│          └──► All tasks [x]? ──► Output <promise>COMPLETE</promise>  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**The loop continues until:**
1. Claude outputs `<promise>COMPLETE</promise>` and the PRD has no `[ ]` tasks, OR
2. Max iterations reached

---

## Quick Start

```bash
# 1. Create a named Ralph loop directory
mkdir -p .ralph/my-feature

# 2. Create the Ralph files
touch .ralph/my-feature/ralph.sh .ralph/my-feature/prd.md \
      .ralph/my-feature/progress.txt .ralph/my-feature/RALPH_PROMPT.md

# 3. Copy the script content (see below)
# 4. Make executable
chmod +x .ralph/my-feature/ralph.sh

# 5. Create your PRD with tasks (see PRD section)
# 6. Run the loop
RALPH_ALLOW_DANGEROUS=1 ./.ralph/my-feature/ralph.sh 10  # 10 iterations max (optional, for unattended runs)

# List all your Ralph loops
ls -la .ralph/
```

---

## File Structure

Each Ralph loop gets its own named subfolder:

```
your-project/
├── .ralph/                          # Ralph orchestration directory
│   ├── priority-system/             # First feature loop
│   │   ├── ralph.sh
│   │   ├── logs/                    # Iteration output (created on first run)
│   │   ├── prd.md
│   │   ├── progress.txt
│   │   └── RALPH_PROMPT.md
│   ├── auth-flow/                   # Second feature loop
│   │   ├── ralph.sh
│   │   ├── logs/                    # Iteration output (created on first run)
│   │   ├── prd.md
│   │   ├── progress.txt
│   │   └── RALPH_PROMPT.md
│   └── dashboard-v2/                # Third feature loop
│       └── ...
├── src/                             # Your application code
├── package.json
└── ...
```

**Benefits of Named Subfolders:**
- Run multiple independent Ralph loops simultaneously
- Keep history of past loops for reference
- Resume any loop at any time
- No risk of overwriting another loop's progress

**Optional:** Add `.ralph/` to `.gitignore` if you don't want to track Ralph files, or selectively ignore completed loops.

---

### ralph.sh - The Loop Script

**⚠️ CRITICAL: Claude CLI Invocation Pattern**

Before copying the ralph.sh script, understand the correct Claude invocation pattern to avoid common mistakes.

**✅ CORRECT - Pipe RALPH_PROMPT.md file to claude CLI:**

```bash
# Line 1361 in ralph.sh (THE ONLY CORRECT WAY)
claude "${CLAUDE_ARGS[@]}" < "$PROMPT_FILE" 2>&1 | tee "$ITERATION_LOG"
```

**Key points:**
1. **Use input redirection `< "$PROMPT_FILE"`** - This pipes the RALPH_PROMPT.md file contents to Claude
2. **DO NOT build prompt in shell** - The prompt already exists in RALPH_PROMPT.md
3. **DO NOT use echo** - Don't construct the prompt as a shell variable
4. **Capture output with `tee`** - Writes to log file AND displays to terminal

**❌ WRONG - Common mistakes to avoid:**

```bash
# ❌ WRONG: Building prompt in shell script
CLAUDE_PROMPT="You are Ralph..."
echo "${CLAUDE_PROMPT}" | claude --dangermode

# ❌ WRONG: Using --dangermode without variable
claude --dangermode

# ❌ WRONG: Not redirecting RALPH_PROMPT.md
claude "${CLAUDE_ARGS[@]}"

# ❌ WRONG: Reading file into variable then echoing
PROMPT_CONTENT=$(cat "$PROMPT_FILE")
echo "$PROMPT_CONTENT" | claude "${CLAUDE_ARGS[@]}"
```

**Why the correct pattern works:**
- **Fresh context per iteration**: Each `claude` invocation gets a clean context window
- **File-based prompt**: RALPH_PROMPT.md contains the instructions, not the script
- **Proper output capture**: `tee` writes to log AND displays in terminal
- **Status code checking**: `${PIPESTATUS[0]}` captures Claude's exit code

**How to verify your script is correct:**
```bash
# Search for the correct pattern in your ralph.sh
grep 'claude.*<.*PROMPT_FILE' .ralph/your-loop/ralph.sh

# Should output something like:
# claude "${CLAUDE_ARGS[@]}" < "$PROMPT_FILE" 2>&1 | tee "$ITERATION_LOG"

# If you see anything else (echo, cat, variable assignment), FIX IT!
```

**Reference working examples:**
If you're unsure, copy the exact script from an existing working loop:
```bash
# Copy from a proven working loop
cp .ralph/pricing-fixes/ralph.sh .ralph/your-new-loop/ralph.sh

# Or examine the exact invocation pattern
grep -A2 -B2 "< \"\$PROMPT_FILE\"" .ralph/*/ralph.sh
```

---

Create `.ralph/<loop-name>/ralph.sh` with the following content:

```bash
#!/bin/bash
# Ralph Wiggum - Autonomous AI Coding Loop
# Usage: ./ralph.sh [max_iterations]
#
# This script runs Claude Code in a loop, with each iteration getting
# a fresh context window. Progress is tracked via prd.md and progress.txt.

set -Eeuo pipefail

# Configuration
MAX_ITERATIONS="${1:-10}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.md"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
PROMPT_FILE="$SCRIPT_DIR/RALPH_PROMPT.md"
LOG_DIR="${RALPH_LOG_DIR:-$SCRIPT_DIR/logs}"
COMPLETE_TOKEN="${RALPH_COMPLETE_TOKEN:-<promise>COMPLETE</promise>}"
SLEEP_SECONDS="${RALPH_SLEEP_SECONDS:-2}"
ALLOW_DANGEROUS="${RALPH_ALLOW_DANGEROUS:-0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

die() {
  echo -e "${RED}Error: $*${NC}" >&2
  exit 1
}

# Validate dependencies
command -v claude >/dev/null 2>&1 || die "claude CLI not found. Install it or ensure it is on PATH."

# Validate max iterations
if ! [[ "$MAX_ITERATIONS" =~ ^[0-9]+$ ]] || [ "$MAX_ITERATIONS" -lt 1 ]; then
  die "Max iterations must be a positive integer."
fi

# Prevent concurrent runs for the same loop
LOCK_DIR="$SCRIPT_DIR/.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  die "Lock exists at $LOCK_DIR. Another Ralph loop may be running. Remove it if stale."
fi
echo "$$" > "$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT INT TERM

mkdir -p "$LOG_DIR"

# Initialize progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
  {
    echo "# Ralph Progress Log"
    echo "Loop: $(basename "$SCRIPT_DIR")"
    echo "Started: $(date)"
    echo "---"
    echo ""
  } > "$PROGRESS_FILE"
fi

# Check required files exist
[ -f "$PRD_FILE" ] || die "prd.md not found at $PRD_FILE"
[ -f "$PROMPT_FILE" ] || die "RALPH_PROMPT.md not found at $PROMPT_FILE"

# Warn if git working tree is dirty
if command -v git >/dev/null 2>&1 && git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [ -n "$(git -C "$SCRIPT_DIR" status --porcelain)" ]; then
    echo -e "${YELLOW}Warning: git working tree has uncommitted changes.${NC}"
  fi
fi

# Exit early if no incomplete stories
if ! grep -q "\[ \]" "$PRD_FILE"; then
  echo -e "${GREEN}No incomplete stories found. Exiting.${NC}"
  exit 0
fi

if [ "$ALLOW_DANGEROUS" = "1" ]; then
  CLAUDE_ARGS=(--dangerously-skip-permissions --print)
else
  CLAUDE_ARGS=(--print)
  echo -e "${YELLOW}Warning: running without --dangerously-skip-permissions.${NC}"
  echo -e "${YELLOW}Set RALPH_ALLOW_DANGEROUS=1 for unattended runs.${NC}"
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           RALPH WIGGUM - Autonomous Coding Loop            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Max iterations: $MAX_ITERATIONS${NC}"
echo -e "${YELLOW}PRD file: $PRD_FILE${NC}"
echo -e "${YELLOW}Progress file: $PROGRESS_FILE${NC}"
echo -e "${YELLOW}Log dir: $LOG_DIR${NC}"
echo -e "${YELLOW}Completion token: $COMPLETE_TOKEN${NC}"
echo ""

for ((i=1; i<=MAX_ITERATIONS; i++)); do
  echo ""
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo -e "${GREEN}  Ralph Iteration $i of $MAX_ITERATIONS${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo ""

  ITERATION_LOG="$LOG_DIR/iteration-${i}-$(date +%Y%m%d-%H%M%S).log"

  # Run Claude Code with the prompt file
  # --print outputs to stdout for capture
  # < redirects the prompt file as input
  set +e
  claude "${CLAUDE_ARGS[@]}" < "$PROMPT_FILE" 2>&1 | tee "$ITERATION_LOG"
  CLAUDE_STATUS=${PIPESTATUS[0]}
  set -e

  if [ "$CLAUDE_STATUS" -ne 0 ]; then
    echo -e "${YELLOW}Claude exited with status $CLAUDE_STATUS. See $ITERATION_LOG${NC}"
  fi

  # Check for completion signal and verify PRD is done
  if grep -qF "$COMPLETE_TOKEN" "$ITERATION_LOG"; then
    if grep -q "\[ \]" "$PRD_FILE"; then
      echo -e "${YELLOW}Completion token found but incomplete stories remain. Continuing...${NC}"
    else
      echo ""
      echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
      echo -e "${GREEN}║                 RALPH COMPLETED ALL TASKS!                 ║${NC}"
      echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
      echo ""
      echo -e "Completed at iteration $i of $MAX_ITERATIONS"
      echo ""

      # Log completion to progress file
      echo "" >> "$PROGRESS_FILE"
      echo "---" >> "$PROGRESS_FILE"
      echo "## COMPLETED" >> "$PROGRESS_FILE"
      echo "Finished at: $(date)" >> "$PROGRESS_FILE"
      echo "Total iterations: $i" >> "$PROGRESS_FILE"

      exit 0
    fi
  fi

  echo ""
  echo -e "${YELLOW}Iteration $i complete. Continuing to next iteration...${NC}"
  sleep "$SLEEP_SECONDS"
done

echo ""
echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║     Ralph reached max iterations without completing        ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Check $PROGRESS_FILE for current status."
echo "Run again with more iterations: ./ralph.sh $((MAX_ITERATIONS + 10))"
exit 1
```

**Make it executable:**
```bash
chmod +x .ralph/<loop-name>/ralph.sh
```

---

### prd.md - Product Requirements Document

The PRD defines what tasks need to be completed. Use markdown checkboxes that Claude will mark as `[x]` when done.

**Create `.ralph/<loop-name>/prd.md`:**

```markdown
# Project: [Your Project Name]

## Overview
Brief description of what you're building.

## User Stories

### US-001: [First Feature]
**Priority:** 1
**Status:** [ ] Incomplete

**Description:**
As a user, I want [feature] so that [benefit].

**Acceptance Criteria:**
- [ ] Criterion 1 (be specific, verifiable)
- [ ] Criterion 2
- [ ] Typecheck passes (`npm run type-check`)
- [ ] Tests pass (`npm test`)

**Notes:** Any additional context.

---

### US-002: [Second Feature]
**Priority:** 2
**Status:** [ ] Incomplete

**Description:**
As a user, I want [feature] so that [benefit].

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Typecheck passes
- [ ] Tests pass

---

### US-003: [Third Feature]
**Priority:** 3
**Status:** [ ] Incomplete

...continue for all features...
```

**PRD Best Practices:**

1. **Right-size your stories**: Each story should complete within one Claude session
   - ✅ "Add a priority field to the database schema"
   - ✅ "Create a UI component for displaying task priority"
   - ❌ "Build the entire dashboard" (too big)

2. **Order by dependency**: Lower priority numbers execute first
   - Priority 1: Database schema changes
   - Priority 2: Backend logic
   - Priority 3: UI components
   - Priority 4: Integration/polish

3. **Verifiable acceptance criteria**: Each criterion must be objectively checkable
   - ✅ "Button shows confirmation dialog before deleting"
   - ✅ "Typecheck passes with zero errors"
   - ❌ "Works correctly" (vague)
   - ❌ "Good UX" (subjective)

4. **Include quality gates**: Every story should include:
   - Typecheck passes
   - Tests pass (if applicable)
   - Lint passes (optional)

---

### progress.txt - Iteration Learnings

This file is **automatically populated** by Claude during each iteration. It serves two purposes:

1. **Memory between sessions**: Claude reads this at the start of each iteration
2. **Debugging aid**: You can see exactly what happened in each iteration

**Initial `.ralph/<loop-name>/progress.txt`:**

```
# Ralph Progress Log
Started: [date will be auto-populated]
---

## Codebase Patterns
(Claude will add discovered patterns here)

---

## Iteration Log
(Claude will append entries here)
```

**Example populated progress.txt:**

```
# Ralph Progress Log
Started: Fri Jan 24 10:30:00 PST 2026
---

## Codebase Patterns
- Use `sql<type>` template literals for database queries
- Components in src/components/ use named exports
- All API routes require authentication middleware
- Tests use vitest with @testing-library/react

---

## Iteration Log

### Iteration 1 - 2026-01-24 10:30:15
**Story:** US-001 - Add priority field to database
**Status:** COMPLETED

**What was implemented:**
- Added `priority` column to tasks table (enum: high, medium, low)
- Created migration file: 20260124_add_priority_to_tasks.sql
- Updated Task type in src/types/task.ts

**Files changed:**
- supabase/migrations/20260124_add_priority_to_tasks.sql (created)
- src/types/task.ts (modified)
- src/lib/database.ts (modified)

**Learnings for future iterations:**
- Database uses Supabase with typed client
- Migrations go in supabase/migrations/ with timestamp prefix
- Type definitions auto-generated from database schema

---

### Iteration 2 - 2026-01-24 10:35:42
**Story:** US-002 - Display priority indicator on task cards
**Status:** COMPLETED

...
```

---

### RALPH_PROMPT.md - Claude Instructions

This file contains the instructions Claude receives at the start of each iteration.

**Create `.ralph/<loop-name>/RALPH_PROMPT.md`:**

```markdown
# Ralph Agent Instructions

You are an autonomous coding agent working through a Product Requirements Document (PRD).
Your goal is to implement exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## Your Workflow

1. **Read the PRD** at `.ralph/<loop-name>/prd.md`
   - Find the highest-priority story that is NOT marked complete
   - A story is incomplete if its Status checkbox is `[ ]`

2. **Read the Progress Log** at `.ralph/<loop-name>/progress.txt`
   - Check the "Codebase Patterns" section for conventions
   - Review recent iteration logs to understand context

3. **Implement the Story**
   - Focus on ONE story only
   - Follow existing code patterns
   - Write clean, well-documented code

4. **Run Quality Checks**
   - TypeScript: `npm run type-check` (must pass)
   - Tests: `npm test` (must pass)
   - Lint: `npm run lint` (should pass)

5. **Commit Your Work**
   - Use format: `feat: [US-XXX] - [Story Title]`
   - Example: `feat: [US-001] - Add priority field to database`

6. **Update the PRD**
   - Mark the story's Status as `[x]`
   - Mark completed acceptance criteria as `[x]`

7. **Update Progress Log**
   - Append an entry with:
     - Story ID and title
     - What was implemented
     - Files changed
     - Learnings for future iterations
   - Update "Codebase Patterns" if you discovered new conventions

8. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>` (must match `RALPH_COMPLETE_TOKEN` if overridden)
   - If stories remain, **STOP IMMEDIATELY** — do not continue to the next story

9. **STOP** — Your iteration is done. Exit now. The loop script handles the next iteration.

## Rules

- **EXACTLY ONE story per iteration** — after completing one story, STOP. Do not start the next one.
- **Never skip quality checks** - Broken code compounds across iterations
- **Document learnings** - Future iterations depend on your notes
- **Follow existing patterns** - Check the codebase before inventing new approaches
- **Be explicit in commits** - Clear commit messages help debugging
- **Do not print the completion token** except when all stories are complete

## If Stuck

If you cannot complete a story after genuine effort:
1. Document what you tried in progress.txt
2. Document the blocker clearly
3. Exit normally - the next iteration will try again with fresh context

Do NOT output `<promise>COMPLETE</promise>` unless ALL stories are done and the token matches `RALPH_COMPLETE_TOKEN`.

---

Now begin. Read the PRD, find the next incomplete story, and implement it.
```

---

## Step-by-Step Setup

### 1. Create the Ralph Directory

```bash
# Use a descriptive name for your loop
mkdir -p .ralph/<loop-name>

# Examples:
# mkdir -p .ralph/user-auth
# mkdir -p .ralph/payment-flow
```

### 2. Create ralph.sh

Copy the script from the [ralph.sh section](#ralphsh---the-loop-script) above.

```bash
chmod +x .ralph/<loop-name>/ralph.sh
```

### 3. Create RALPH_PROMPT.md

Copy the template from the [RALPH_PROMPT.md section](#ralph_promptmd---claude-instructions) above, customizing for your project:

- Update quality check commands for your stack
- Add project-specific rules
- Include any file/directory conventions

### 4. Create Your PRD

Use Claude Code's plan mode to generate a detailed PRD:

```bash
# In Claude Code, use plan mode
claude

# Then ask:
"I want to build [your feature]. Help me create a detailed PRD with user stories.
Each story should:
- Be completable in one session
- Have specific, verifiable acceptance criteria
- Include quality gates (typecheck, tests)
- Be ordered by dependency (database → backend → frontend)

Save the PRD to .ralph/<loop-name>/prd.md using markdown checkboxes."
```

### 5. Initialize Progress File

```bash
echo "# Ralph Progress Log" > .ralph/<loop-name>/progress.txt
echo "Started: $(date)" >> .ralph/<loop-name>/progress.txt
echo "---" >> .ralph/<loop-name>/progress.txt
echo "" >> .ralph/<loop-name>/progress.txt
echo "## Codebase Patterns" >> .ralph/<loop-name>/progress.txt
echo "(Patterns will be added as Ralph discovers them)" >> .ralph/<loop-name>/progress.txt
echo "" >> .ralph/<loop-name>/progress.txt
echo "---" >> .ralph/<loop-name>/progress.txt
echo "" >> .ralph/<loop-name>/progress.txt
echo "## Iteration Log" >> .ralph/<loop-name>/progress.txt
```

### 6. Test with a Small Run

Before running overnight:

```bash
# Test with 3 iterations
RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 3
```

Watch for:
- Does Claude read the PRD correctly?
- Does it mark tasks complete?
- Does it update progress.txt?
- Do quality checks run?

### 7. Run the Full Loop

```bash
# Run with enough iterations for your PRD
RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 20

# For larger projects
RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 50
```

---

## Creating Your PRD

### Option 1: Use Claude Code's Plan Mode

The easiest way to create a well-structured PRD:

```bash
claude

# Ask Claude to create the PRD
"I want to build a [description of your feature/project].

Create a detailed PRD saved to .ralph/<loop-name>/prd.md with:
1. Overview section
2. User stories (US-001, US-002, etc.)
3. Each story has:
   - Priority number (execution order)
   - Status checkbox [ ]
   - Description (user story format)
   - Acceptance criteria (specific, verifiable)
   - Quality gates (typecheck, tests)

Stories should be:
- Small enough to complete in one Claude session
- Ordered by dependency (database → backend → frontend)
- Include clear acceptance criteria

Example acceptance criterion:
✅ 'Button displays confirmation dialog before deleting'
❌ 'Works correctly' (too vague)"
```

### Option 2: Manual Creation

Use this template:

```markdown
# Project: My Feature

## Overview
Building a task management system with priorities.

## User Stories

### US-001: Add Priority Field to Database
**Priority:** 1
**Status:** [ ] Incomplete

**Description:**
As a developer, I need a priority field in the database so tasks can be sorted.

**Acceptance Criteria:**
- [ ] Add `priority` column to `tasks` table (enum: high, medium, low)
- [ ] Default value is `medium`
- [ ] Migration runs without errors
- [ ] Typecheck passes

---

### US-002: Display Priority Badge on Task Cards
**Priority:** 2
**Status:** [ ] Incomplete

**Description:**
As a user, I want to see priority badges on task cards so I know what's urgent.

**Acceptance Criteria:**
- [ ] Badge shows on TaskCard component
- [ ] Colors: red=high, yellow=medium, gray=low
- [ ] Badge is accessible (aria-label)
- [ ] Component tests pass
- [ ] Typecheck passes

---

### US-003: Add Priority Selector to Task Edit Modal
**Priority:** 3
**Status:** [ ] Incomplete

...
```

### Story Sizing Guidelines

**Right-sized stories** (complete in one iteration):
- Add a database column
- Create a UI component
- Add an API endpoint
- Write tests for a feature
- Update type definitions

**Too large** (split into multiple stories):
- "Build the dashboard" → Split into: add layout, add sidebar, add header, add widgets
- "Implement authentication" → Split into: add schema, add login UI, add logout, add protected routes
- "Refactor the codebase" → Split into specific refactoring tasks

---

## Running the Loop

### Basic Usage

```bash
# Run with default 10 iterations
RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh

# Run with custom iteration count
RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 30

# Run overnight (increase iterations)
RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 100
```

### Monitoring Progress

**While running:**
- Watch the terminal for iteration updates
- Check `.ralph/<loop-name>/prd.md` to see tasks being marked complete
- Check `.ralph/<loop-name>/progress.txt` for detailed logs

**IMPORTANT - Wait before checking logs:**
- Log files (`.ralph/<loop-name>/logs/iteration-X-*.log`) write incrementally during execution
- First iteration takes 5-10 minutes - **wait at least 10 minutes** before checking
- Log files will appear empty (0 bytes) until iteration completes
- **Don't panic if logs are empty** - check PRD and progress.txt instead

**Real-time progress check (recommended):**
```bash
# Check how many tasks completed (most reliable indicator)
grep -c "\[x\] Complete" .ralph/<loop-name>/prd.md

# Check if Ralph is actively working
tail -20 .ralph/<loop-name>/progress.txt  # Shows latest iteration

# Monitor which iteration is running (terminal will show "Running iteration X/Y")
```

**After running:**
```bash
# Check how many tasks are done
grep -c "\[x\]" .ralph/<loop-name>/prd.md

# Check remaining tasks
grep "\[ \]" .ralph/<loop-name>/prd.md

# View progress log
cat .ralph/<loop-name>/progress.txt
```

### Stopping the Loop

Press `Ctrl+C` to stop. Progress is preserved in:
- `.ralph/<loop-name>/prd.md` (completed tasks stay marked)
- `.ralph/<loop-name>/progress.txt` (learnings preserved)

Resume by running the script again.

### Emergency Recovery

If Claude makes breaking changes:
```bash
# Revert to last good commit (safe, keeps history)
git log --oneline -10
git revert <commit-hash>

# If you're on a disposable branch and want to discard local changes (destructive):
# git reset --hard <commit-hash>

# Edit prd.md to uncheck the broken story
# Run again
RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 10
```

---

## Best Practices

### 1. Start Small

Before running a 100-iteration overnight loop:
```bash
# Test with 3-5 iterations
RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 5
```

Verify:
- PRD is being read correctly
- Tasks are being marked complete
- Quality checks are running
- Progress is being logged

### 2. Write Verifiable Acceptance Criteria

Every criterion should be objectively checkable:

✅ **Good:**
- "Button displays 'Delete' with trash icon"
- "API returns 404 for non-existent resources"
- "Form validation shows error for empty email"
- "Typecheck passes with zero errors"

❌ **Bad:**
- "Works correctly"
- "Good user experience"
- "Handles edge cases"
- "Is performant"

### 3. Include Quality Gates

Every story should end with:
```markdown
- [ ] Typecheck passes (`npm run type-check`)
- [ ] Tests pass (`npm test`)
```

### 4. Order Stories by Dependency

```markdown
Priority 1: Database schema (no dependencies)
Priority 2: Type definitions (depends on schema)
Priority 3: Backend API (depends on types)
Priority 4: Frontend components (depends on API)
Priority 5: Integration tests (depends on everything)
```

### 5. Document Codebase Patterns

In your RALPH_PROMPT.md, include existing patterns:
```markdown
## Codebase Patterns
- API routes are in src/app/api/
- Components use named exports
- State management uses Zustand
- Tests are co-located with components (*.test.tsx)
```

### 6. Use Git Branches

Run Ralph on a feature branch:
```bash
git checkout -b feature/ralph-implementation
RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 20
# Review changes
git diff main
```

---

## Advanced Patterns

### Pattern 1: Fast Mode (Skip Tests)

For prototyping or when tests don't exist yet (not recommended for production):

**Modify RALPH_PROMPT.md:**
```markdown
## Quality Checks
- TypeScript: `npm run type-check` (must pass)
- Tests: SKIP for this run
- Lint: `npm run lint` (should pass)
```

### Pattern 2: Resume After Crash

If the script crashes or you stop it:
```bash
# Progress is preserved - just run again
RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 20

# Claude will read progress.txt and continue where it left off
```

### Pattern 3: Multiple Features (Named Loops)

Each feature gets its own named folder - no need for environment variables to select the loop:

```bash
# List all loops
ls -la .ralph/

# Run authentication loop
RALPH_ALLOW_DANGEROUS=1 ./.ralph/auth-flow/ralph.sh 15

# Run dashboard loop (can run in parallel in separate terminals!)
RALPH_ALLOW_DANGEROUS=1 ./.ralph/dashboard-v2/ralph.sh 20
```

This is the default pattern with named subfolders - each loop is completely isolated.

### Pattern 4: Notification on Completion

Add inside the completion branch in ralph.sh (right before `exit 0`):
```bash
# macOS notification
osascript -e 'display notification "All tasks completed!" with title "Ralph"'

# Or send to Slack webhook
# curl -X POST -H 'Content-type: application/json' \
#   --data '{"text":"Ralph completed all tasks!"}' \
#   YOUR_SLACK_WEBHOOK_URL
```

### Pattern 5: Cost Tracking

Add to ralph.sh to track API costs:
```bash
# After each iteration
COST=$(grep -o 'Cost: \$[0-9.]*' "$ITERATION_LOG" | tail -1)
if [ -n "$COST" ]; then
  echo "Iteration $i cost: $COST" >> "$LOG_DIR/costs.log"
fi
```

---

## Troubleshooting

### Issue: Ralph Appears Not Working (Empty Log Files)

**Symptoms:**
- Iteration log files show 0 bytes (empty)
- No visible progress in terminal after 2-3 minutes
- Appears like nothing is happening

**Root Cause:**
- Log files write incrementally - they appear empty until the iteration completes
- First iteration takes 5-10 minutes (Claude is reading codebase, planning, implementing)
- Checking too early gives false impression that Ralph isn't working

**Solutions:**
1. **Wait 10 minutes minimum** before checking first iteration
2. **Check PRD instead of logs**:
   ```bash
   grep -c "\[x\] Complete" .ralph/<loop-name>/prd.md  # Should increase over time
   ```
3. **Check progress.txt instead of logs**:
   ```bash
   tail -20 .ralph/<loop-name>/progress.txt  # Shows completed iterations
   ```
4. **Monitor terminal output** - ralph.sh prints "Running iteration X/Y" messages
5. **Verify Claude is running**:
   ```bash
   ps aux | grep claude  # Should show active process
   ```

**Expected Behavior:**
- Iteration 1: 5-10 minutes (longest - Claude explores codebase)
- Iteration 2+: 3-7 minutes each (Claude has context from progress.txt)
- Log files appear empty until iteration completes, then populate all at once

**If still stuck after 15 minutes on first iteration:**
- Check `.ralph/<loop-name>/prd.md` - if checkbox changed from `[ ]` to `[x]`, Ralph IS working
- Check git status - if files were modified/committed, Ralph IS working
- Only kill and restart if PRD unchanged AND no git activity after 20+ minutes

---

### Issue: Ralph Loop Fails to Start (Script Exits Immediately)

**Symptoms:**
- Script starts but no Claude process ever runs
- No iteration logs created in `logs/` directory
- Process exits quickly with no visible error
- Running in background shows task complete but no progress made

**Root Cause:**
- **Wrong Claude CLI invocation pattern in ralph.sh**
- Script tries to build prompt as shell variable instead of piping RALPH_PROMPT.md file

**❌ Common Mistake in ralph.sh:**
```bash
# WRONG - Building prompt in shell
CLAUDE_PROMPT="You are Ralph..."
echo "${CLAUDE_PROMPT}" | claude --dangermode

# WRONG - Using --dangermode without proper flags
claude --dangermode

# WRONG - Not redirecting RALPH_PROMPT.md
claude "${CLAUDE_ARGS[@]}"
```

**✅ Correct Pattern:**
```bash
# CORRECT - Pipe RALPH_PROMPT.md to claude CLI
claude "${CLAUDE_ARGS[@]}" < "$PROMPT_FILE" 2>&1 | tee "$ITERATION_LOG"
```

**How to Fix:**
1. **Verify your ralph.sh uses the correct pattern:**
   ```bash
   grep 'claude.*<.*PROMPT_FILE' .ralph/<loop-name>/ralph.sh
   ```
   Should output: `claude "${CLAUDE_ARGS[@]}" < "$PROMPT_FILE" 2>&1 | tee "$ITERATION_LOG"`

2. **If pattern is wrong, copy from working loop:**
   ```bash
   # Backup your PRD and progress files
   cp .ralph/<loop-name>/prd.md /tmp/prd-backup.md
   cp .ralph/<loop-name>/progress.txt /tmp/progress-backup.txt

   # Copy working ralph.sh from existing loop
   cp .ralph/pricing-fixes/ralph.sh .ralph/<loop-name>/ralph.sh

   # Update loop name in header
   sed -i '' 's/Pricing Fixes/<Your Loop Name>/g' .ralph/<loop-name>/ralph.sh

   # Restore your PRD and progress
   cp /tmp/prd-backup.md .ralph/<loop-name>/prd.md
   cp /tmp/progress-backup.txt .ralph/<loop-name>/progress.txt
   ```

3. **Make executable and retry:**
   ```bash
   chmod +x .ralph/<loop-name>/ralph.sh
   RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh 15
   ```

**Verification:**
After fixing, you should see:
- Terminal output showing "Ralph Iteration 1 of X"
- `claude` process running: `ps aux | grep claude`
- Iteration log file created (may be empty until iteration completes)
- PRD checkboxes changing from `[ ]` to `[x]` after 5-10 minutes

**Prevention:**
- Always copy ralph.sh from a working loop instead of writing from scratch
- Review the [Claude CLI Invocation Pattern](#ralphsh---the-loop-script) section before creating new loops
- Test with just 1-2 iterations first: `./.ralph/<loop-name>/ralph.sh 2`

---

### Issue: Claude Completes Multiple Stories in One Iteration

**Symptoms:**
- All (or most) stories completed in a single iteration instead of one per iteration
- Progress.txt shows multiple story entries from the same session
- Loop finishes in 1-2 iterations instead of N iterations for N stories

**Root Cause:**
- The RALPH_PROMPT.md says "ONE story per iteration" but doesn't explicitly tell Claude to **STOP and EXIT** after one story
- Claude interprets "exit normally" as "don't print the completion token" rather than "terminate your session right now"
- Without a hard stop instruction, Claude sees remaining stories and keeps going

**Solutions:**
1. **Update RALPH_PROMPT.md** with explicit stop language (this is the primary fix):
   - Add bold `**CRITICAL**` block at top: "You must STOP after completing ONE story. Do NOT continue to the next story."
   - Add step 9/10: `**STOP** — Your iteration is done. Exit now.`
   - Change "exit normally" to "**STOP IMMEDIATELY** — do not continue to the next story"
   - Change rules from "ONE story per iteration" to "**EXACTLY ONE story per iteration** — after completing one story, STOP"
   - End the prompt with "After completing it, STOP."

2. **Copy the updated template** from the [RALPH_PROMPT.md section](#ralph_promptmd---claude-instructions) which now includes all the stop language

3. **Verify your RALPH_PROMPT.md has the stop language:**
   ```bash
   grep -c "STOP" .ralph/<loop-name>/RALPH_PROMPT.md
   # Should show 3+ occurrences
   ```

**Prevention:**
- Always use the latest RALPH_PROMPT.md template from this document
- The key phrases that enforce single-story behavior are:
  - `"CRITICAL: You must STOP after completing ONE story"`
  - `"STOP IMMEDIATELY — do not continue to the next story"`
  - `"Your iteration is done. Exit now."`
  - `"After completing it, STOP."`

---

### Issue: Claude Doesn't Mark Tasks Complete

**Symptoms:**
- Same task attempted every iteration
- PRD checkboxes stay `[ ]`

**Solutions:**
1. Check RALPH_PROMPT.md includes clear instructions to update PRD
2. Verify Claude has write permissions to `.ralph/<loop-name>/prd.md`
3. Add explicit instruction: "After completing a story, edit `.ralph/<loop-name>/prd.md` and change its Status from `[ ]` to `[x]`"

### Issue: Claude Outputs COMPLETE Too Early

**Symptoms:**
- Loop exits but tasks remain incomplete

**Solutions:**
1. Use `RALPH_COMPLETE_TOKEN` to set a unique token and update RALPH_PROMPT.md to match
2. Ensure you're using the production-hardened ralph.sh (it verifies PRD has no `[ ]` before exiting)
3. Check if the completion token appears in code/logs or tests

### Issue: Same Error Repeated Every Iteration

**Symptoms:**
- Progress.txt shows same error across iterations

**Solutions:**
1. Fresh context should help, but if not:
2. Add to RALPH_PROMPT.md: "If you see the same error 3 times in progress.txt, try a completely different approach"
3. Manually add context to progress.txt: "DO NOT try approach X, it failed"

### Issue: Quality Checks Failing

**Symptoms:**
- Typecheck/tests fail, task not marked complete

**Solutions:**
1. This is correct behavior - broken code shouldn't be marked done
2. Check if tests are flaky (run manually)
3. Reduce story scope so each is achievable
4. Add debugging instruction: "If tests fail, read the error output and fix the specific issue"

### Issue: Permission Errors

**Symptoms:**
- Claude asks for permission, breaking autonomy

**Solutions:**
1. Set `RALPH_ALLOW_DANGEROUS=1` before running to enable `--dangerously-skip-permissions`
2. Check your Claude Code version supports the flag
3. Configure permissions in `~/.claude/settings.json` if you prefer manual approval

### Issue: Lock Exists

**Symptoms:**
- Script exits immediately with: `Error: Lock exists at .ralph/<loop-name>/.lock`
- Cannot start a new Ralph run

**Root Cause:**
- Previous Ralph run crashed or was force-killed (Ctrl+C didn't clean up properly)
- Lock file prevents two simultaneous Ralph runs from conflicting

**Solutions:**
1. **Verify no other Ralph is running**:
   ```bash
   ps aux | grep "ralph.sh"  # Check for running ralph.sh processes
   ps aux | grep claude      # Check for active Claude sessions
   ```
2. **If no processes found, safe to remove lock**:
   ```bash
   rm -rf .ralph/<loop-name>/.lock
   ```
3. **Then retry**:
   ```bash
   RALPH_ALLOW_DANGEROUS=1 ./.ralph/<loop-name>/ralph.sh
   ```

**Prevention:**
- Use `Ctrl+C` to stop Ralph (triggers cleanup trap in ralph.sh)
- Avoid force-killing with `kill -9` (bypasses cleanup)
- The script includes `trap 'rm -rf "$LOCK_DIR"' EXIT INT TERM` for automatic cleanup

---

## Resources

### Community Implementations

- **[snarktank/ralph](https://github.com/snarktank/ralph)** - Original Ralph implementation with JSON PRD format
- **[michaelshimeles/ralphy](https://github.com/michaelshimeles/ralphy)** - Enhanced version with parallel execution, multiple AI engines

### Video Tutorials

- [Ralph Wiggum Explained (YouTube)](https://www.youtube.com/results?search_query=ralph+wiggum+claude+code) - Search for recent tutorials

### Key Differences from Official Plugin

| Feature | Official Plugin | Shell Script |
|---------|-----------------|--------------|
| Fresh context per iteration | ❌ No | ✅ Yes |
| Progress persistence | In-memory | File-based |
| Crash recovery | Restart from scratch | Continue from checkpoint |
| Debugging visibility | Limited | Full (prd.md, progress.txt) |
| Customization | Plugin API | Edit shell script |
| Multi-engine support | Claude only | Claude, Amp, etc. |

---

## Quick Reference

### File Locations

| File | Purpose |
|------|---------|
| `.ralph/<loop-name>/ralph.sh` | Loop script |
| `.ralph/<loop-name>/prd.md` | Tasks with checkboxes |
| `.ralph/<loop-name>/progress.txt` | Iteration learnings |
| `.ralph/<loop-name>/RALPH_PROMPT.md` | Claude instructions |
| `.ralph/<loop-name>/logs/` | Per-iteration logs |

### Commands

```bash
# List all Ralph loops
ls -la .ralph/

# Run a specific loop with 10 iterations (default)
./.ralph/my-feature/ralph.sh

# Run unattended (opt-in to --dangerously-skip-permissions)
RALPH_ALLOW_DANGEROUS=1 ./.ralph/my-feature/ralph.sh

# Run with custom iterations
./.ralph/my-feature/ralph.sh 30

# Check progress for a specific loop
grep "\[x\]" .ralph/my-feature/prd.md | wc -l  # Completed
grep "\[ \]" .ralph/my-feature/prd.md | wc -l  # Remaining
```

### Completion Signal

Claude outputs this when all tasks are done (must match `RALPH_COMPLETE_TOKEN` if overridden):
```
<promise>COMPLETE</promise>
```

---

**Document Version**: 4.0.0
**Last Updated**: January 25, 2026
**Maintained By**: Kindora Development Team

**v4.0.0 Changes (January 25, 2026):**
- **MAJOR**: Added "Ralph Loop Types: Three-Stage Development Process" section
- Introduced three specialized loop types with complete templates:
  1. **Feature Implementation Loop** - For building new functionality with code commits
  2. **Production Readiness Evaluation Loop** - For quality/security/performance audits
  3. **UI/Brand Review Loop** - For design compliance and UX best practices
- Added decision matrix to help Claude choose correct loop type
- Added sequential loop pattern (Feature → Evaluation → UI Review → Production)
- Added loop-type-specific PRD structure patterns
- Added loop-type-specific RALPH_PROMPT.md templates
- Added severity definitions and report templates for evaluation loops
- Added brand guidelines integration for UI review loops
- Added critical warning for Claude to identify evaluation vs. implementation requests
- Updated Table of Contents with new section
- Prevents confusion between building features vs. evaluating quality

**v3.2.2 Changes (January 24, 2026):**
- Added troubleshooting section: "Ralph Appears Not Working (Empty Log Files)"
- Enhanced "Monitoring Progress" with wait times and real-time checking commands
- Enhanced "Lock Exists" troubleshooting with verification steps and prevention tips
- Added expected iteration duration guidance (5-10 min first, 3-7 min subsequent)
- Clarified that log files write incrementally and appear empty until completion

**v3.2.1 Changes (January 25, 2026):**
- Hardened ralph.sh with dependency checks, locking, per-iteration logs, and PRD-verified completion
- Added explicit opt-in for `--dangerously-skip-permissions` via `RALPH_ALLOW_DANGEROUS`
- Updated prompts, troubleshooting, and patterns to match the hardened flow

**v3.2.0 Changes (January 24, 2026):**
- Added named subfolder structure: `.ralph/<loop-name>/` for each Ralph loop
- Multiple loops can now run independently without overwriting each other
- Added listing command to show all loops: `ls -la .ralph/`
- Each loop is self-contained and resumable
- Updated all file paths to use named folder pattern

**v3.1.0 Changes (January 24, 2026):**
- Added "🤖 CLAUDE: Auto-Setup Instructions" section for self-executing workflow
- Claude can now read this doc + user requirements and auto-generate all Ralph files
- Added PRD generation template with story sizing rules
- Added example showing requirements-to-PRD conversion
- Added pre-run checklist for verification
- Added "After Setup Message" template for user communication

**v3.0.0 Changes (January 24, 2026):**
- Complete rewrite to use shell script approach instead of official plugin
- Added ralph.sh script template
- Added prd.md template with checkbox format
- Added progress.txt format and auto-population
- Added RALPH_PROMPT.md instructions template
- Explained why shell script approach is superior (fresh context per iteration)
- Added step-by-step setup guide
- Added troubleshooting section

_This document is self-executing: give it to Claude Code along with your requirements, and Claude will set up and run the Ralph loop automatically._
