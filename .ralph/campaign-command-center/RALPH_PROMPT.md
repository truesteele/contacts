# Ralph Agent Instructions - Feature Implementation

You are building the Come Alive 2026 Campaign Command Center — a Next.js frontend for managing a fundraising campaign. Complete exactly ONE user story per iteration, then STOP.

**CRITICAL: You must STOP after completing ONE story. Do NOT continue to the next story. The loop script will start a fresh session for the next story.**

## This Loop
Loop Name: campaign-command-center
Loop Type: **Feature Implementation**
Loop Directory: .ralph/campaign-command-center/

## Workflow

1. **Read PRD** at `.ralph/campaign-command-center/prd.md` - Find first `[ ]` story
2. **Read Progress** at `.ralph/campaign-command-center/progress.txt` - Learn patterns from previous iterations
3. **Study Existing Patterns** - Read the reference files listed below BEFORE writing code
4. **Implement the Feature**
   - Write production-quality TypeScript/React code
   - Follow existing codebase patterns exactly
   - Use existing UI components — do NOT create new ones unless absolutely necessary
5. **Run Quality Checks**
   - `cd job-matcher-ai && npx next build` must succeed (or at minimum, `npx tsc --noEmit` must pass)
   - For page stories: verify the page renders by starting dev server if needed
6. **Commit Your Work**
   - Format: `feat: [US-XXX] - [Story Title]`
   - Stage only the files you created/modified
7. **Update PRD** - Mark story `[x]` complete
8. **Update Progress** - Document what you built and learned
9. **Check Completion**
   - If ALL stories in PRD are `[x]`, output `<promise>COMPLETE</promise>`
   - If stories remain, **STOP IMMEDIATELY** - do not continue to the next story
10. **STOP** - Your iteration is done. Exit now.

## Codebase Patterns (MUST FOLLOW)

### Directory Structure
All paths are relative to project root. The Next.js app lives in `job-matcher-ai/`.

```
job-matcher-ai/
├── app/
│   ├── tools/
│   │   ├── campaign/page.tsx          ← NEW (you build this)
│   │   ├── ask-readiness/page.tsx     ← PATTERN: filterable contact table
│   │   ├── pipeline/page.tsx          ← PATTERN: detail sheet + editing
│   │   └── network-intel/page.tsx     ← PATTERN: page layout
│   └── api/network-intel/
│       ├── campaign/                  ← NEW (you build these)
│       │   ├── route.ts
│       │   ├── [id]/route.ts
│       │   └── send/route.ts
│       ├── ask-readiness/route.ts     ← PATTERN: data API with JSONB flattening
│       ├── outreach/send/route.ts     ← PATTERN: Resend send + textToHtml()
│       └── pipeline/route.ts          ← PATTERN: CRUD API
├── components/
│   ├── campaign/                      ← NEW (you build these)
│   │   └── message-detail-sheet.tsx
│   ├── contact-detail-sheet.tsx       ← PATTERN: side sheet with rich data
│   ├── outreach-drawer.tsx            ← PATTERN: draft editing + send
│   ├── pipeline/deal-detail-sheet.tsx ← PATTERN: editable side sheet
│   └── ui/                            ← SHARED: Badge, Button, Card, Input, etc.
├── lib/
│   └── supabase.ts                    ← Supabase client
└── package.json                       ← resend@6.9.2 already installed
```

### Page Pattern (from ask-readiness/page.tsx)
```tsx
'use client';
import { useState, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
// ... more UI imports

export default function CampaignPage() {
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch('/api/network-intel/campaign');
        if (!res.ok) throw new Error('Failed to load');
        const data = await res.json();
        setContacts(data.contacts || []);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);
  // ...
}
```

### API Route Pattern (from ask-readiness/route.ts)
```tsx
import { supabase } from '@/lib/supabase';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

export async function GET(req: NextRequest) {
  try {
    const allContacts: any[] = [];
    const pageSize = 1000;
    let offset = 0;

    while (true) {
      const { data, error } = await supabase
        .from('contacts')
        .select('id, first_name, ..., campaign_2026')
        .not('campaign_2026', 'is', null)
        .order('id')
        .range(offset, offset + pageSize - 1);

      if (error) throw new Error(`DB error: ${error.message}`);
      if (!data || data.length === 0) break;
      allContacts.push(...data);
      if (data.length < pageSize) break;
      offset += pageSize;
    }

    // Flatten JSONB fields...
    return Response.json({ contacts: flattened, total: flattened.length });
  } catch (error: any) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}
```

### Resend Send Pattern (from outreach/send/route.ts)
```tsx
import { Resend } from 'resend';

const FROM_EMAIL = 'Justin Steele <justin@outdoorithmcollective.org>';
const REPLY_TO = 'justinrsteele@gmail.com';

let _resend: Resend | null = null;
function getResend(): Resend {
  if (!_resend) { _resend = new Resend(process.env.RESEND_API_KEY_OC); }
  return _resend;
}

// textToHtml() converts plain text to styled HTML email
// COPY THIS FUNCTION from app/api/network-intel/outreach/send/route.ts
```

### Page Layout Pattern (from network-intel/page.tsx)
```tsx
<main className="min-h-screen bg-background">
  <div className="max-w-7xl mx-auto p-4">
    <div className="page-header">
      <Link href="/" className="page-back" aria-label="Back to dashboard">
        <ArrowLeft className="w-5 h-5" />
      </Link>
      <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-600">
        <Megaphone className="w-4 h-4" />
      </div>
      <h1 className="text-lg font-semibold tracking-tight">Campaign</h1>
    </div>
    {/* page content */}
  </div>
</main>
```

### Detail Sheet Pattern (from contact-detail-sheet.tsx)
```tsx
<Sheet open={open} onOpenChange={onOpenChange}>
  <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
    <SheetHeader>
      <SheetTitle>{contact.first_name} {contact.last_name}</SheetTitle>
    </SheetHeader>
    {/* content sections */}
  </SheetContent>
</Sheet>
```

### Editable Field Pattern
```tsx
// Use Textarea for message bodies, Input for subject lines
// Save on blur or via explicit Save button
<Textarea
  value={field}
  onChange={(e) => setField(e.target.value)}
  className="min-h-[120px] text-sm"
/>
<Button onClick={handleSave} disabled={saving}>
  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save'}
</Button>
```

### UI Component Imports
```tsx
// All from @/components/ui/
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
// Icons from lucide-react
import { ArrowLeft, Search, Send, Check, X, Loader2, DollarSign, Users, Mail, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
```

### Supabase Client
```tsx
import { supabase } from '@/lib/supabase';
// Uses SUPABASE_URL and SUPABASE_SERVICE_KEY env vars
```

### JSONB Update Pattern (for PATCH routes)
```tsx
// Use Supabase's raw SQL for nested JSONB updates
const { data, error } = await supabase.rpc('exec_sql', {
  query: `UPDATE contacts SET campaign_2026 = jsonb_set(campaign_2026, '{personal_outreach,message_body}', $1::jsonb) WHERE id = $2 RETURNING campaign_2026`,
  params: [JSON.stringify(value), id]
});

// OR use the simpler approach: fetch full JSONB, modify in JS, write back
const { data: contact } = await supabase.from('contacts').select('campaign_2026').eq('id', id).single();
const updated = { ...contact.campaign_2026 };
updated.personal_outreach.message_body = newValue;
await supabase.from('contacts').update({ campaign_2026: updated }).eq('id', id);
```

## Reference Files to Read

Before writing ANY code for a story, read the relevant reference files:

| Story | Must Read First |
|:--|:--|
| US-001 (API) | `app/api/network-intel/ask-readiness/route.ts`, `lib/supabase.ts` |
| US-002 (Update API) | `app/api/network-intel/pipeline/deals/[id]/route.ts` |
| US-003 (Page + tabs) | `app/tools/ask-readiness/page.tsx` (first 200 lines), `app/tools/network-intel/page.tsx`, `components/ui/tabs.tsx` |
| US-004 (Detail sheet) | `components/contact-detail-sheet.tsx` (first 150 lines), `components/pipeline/deal-detail-sheet.tsx` |
| US-005 (B-D tab) | `app/tools/ask-readiness/page.tsx` (filter logic, ~lines 200-400) |
| US-006 (Send API) | `app/api/network-intel/outreach/send/route.ts` (FULL file — copy textToHtml and Resend pattern) |
| US-007 (Send UI) | `components/outreach-drawer.tsx` (send button pattern) |
| US-008 (Activity) | No specific reference — follow existing patterns |

## Rules

- **EXACTLY ONE story per iteration** — after completing one story, STOP
- **Follow existing patterns** — Read reference files before writing code. Match the style exactly.
- **Use existing UI components** — Do NOT create new primitive components. Use `@/components/ui/*`.
- **TypeScript strict** — No `any` types in component props (API routes can use `any` for Supabase data)
- **Edge runtime** — All API routes must have `export const runtime = 'edge';`
- **No new dependencies** — Everything needed is already installed (resend, supabase, radix, lucide, etc.)
- **Commit format** — `feat: [US-XXX] - Story title`
- **Quality check** — At minimum, run `cd job-matcher-ai && npx tsc --noEmit` before committing. If it has errors, fix them.

## Important Notes

- The Next.js app is at `job-matcher-ai/` — all file paths for the app are relative to this directory
- Supabase env var for the service key is `SUPABASE_SERVICE_KEY` (not `SUPABASE_KEY`)
- `campaign_2026` JSONB may have null sub-objects — always null-check before accessing nested fields
- Contact email priority: `personal_email || email || work_email`
- For text/SMS messages, show a "Copy to clipboard" button (no SMS gateway integration yet)
- The `textToHtml()` function from the existing send route converts plain text to a styled HTML email with Georgia font, proper paragraph formatting, and an unsubscribe link — COPY this function, don't reinvent it

Begin now. Read the PRD and implement the next incomplete story. After completing it, STOP.
