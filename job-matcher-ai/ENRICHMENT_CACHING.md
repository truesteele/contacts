# Enrichment Data Caching

## Overview

The AI Recruiter Agent now **automatically caches Enrich Layer API responses** in the database to avoid duplicate API calls and reduce costs.

**Key Features:**
- ✅ 7-day cache duration (configurable)
- ✅ Automatic cache checking before API calls
- ✅ Timestamp tracking for cache freshness
- ✅ Transparent caching (agent doesn't need to know)
- ✅ Database storage for persistence across sessions

---

## How It Works

### 1. First Enrichment (Cache Miss)

```typescript
// Agent calls enrich_candidate tool
{
  contact_id: "123",
  email: "candidate@example.com",
  linkedin_url: "https://linkedin.com/in/candidate"
}

// System checks database:
// - No enrichment data? → API call
// - OR enrichment data >7 days old? → API call

// Makes Enrich Layer API call...
// ✓ Stores response in contacts.enrich_person_from_profile
// ✓ Records timestamp in contacts.enriched_at
```

### 2. Subsequent Enrichments (Cache Hit)

```typescript
// Agent calls enrich_candidate tool again (same candidate)
{
  contact_id: "123",
  email: "candidate@example.com",
  linkedin_url: "https://linkedin.com/in/candidate"
}

// System checks database:
// - Has enrichment data? ✓
// - enriched_at within 7 days? ✓
// → Returns cached data (no API call!)

// Console: "✓ Using cached enrichment data for contact 123 (age: 2.3 days)"
```

---

## Database Schema

### New Column Added

```sql
ALTER TABLE contacts
ADD COLUMN enriched_at TIMESTAMP WITH TIME ZONE;
```

**Purpose**: Tracks when Enrich Layer data was last fetched

**Values**:
- `NULL` = Never enriched OR no timestamp (legacy data)
- `2025-10-29T10:30:00Z` = Last enriched at this time
- Used to calculate age: `NOW() - enriched_at`

### Migration

Run this SQL to add the column:

```bash
psql $DATABASE_URL < add_enriched_at_column.sql
```

Or manually:

```sql
-- Add column
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMP WITH TIME ZONE;

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_contacts_enriched_at
ON contacts(enriched_at)
WHERE enriched_at IS NOT NULL;

-- Update existing enriched records (makes them stale so they'll refresh)
UPDATE contacts
SET enriched_at = NOW() - INTERVAL '8 days'
WHERE enrich_person_from_profile IS NOT NULL
  AND enriched_at IS NULL;
```

---

## API Changes

### Before (No Caching)

```typescript
export async function enrichCandidate(
  email?: string,
  linkedinUrl?: string
): Promise<EnrichmentData | null> {
  // Always made API call
  const response = await fetch('https://api.enrichlayer.com/v1/person?...');
  return response.json();
}
```

**Problem**: If agent enriches same candidate 3x in one search → 3 API calls

**Cost**: $0.10 per enrichment × 3 = $0.30 wasted

### After (With Caching)

```typescript
export async function enrichCandidate(
  contactId?: string,  // NEW: Required for caching
  email?: string,
  linkedinUrl?: string
): Promise<EnrichmentData | null> {
  // Check cache first
  if (contactId) {
    const cached = await checkEnrichmentCache(contactId);
    if (cached) {
      return cached.data; // No API call!
    }
  }

  // Only make API call if cache miss
  const response = await fetch('https://api.enrichlayer.com/v1/person?...');
  const data = await response.json();

  // Store in cache
  if (contactId && data) {
    await storeEnrichmentData(contactId, data);
  }

  return data;
}
```

**Benefit**: If agent enriches same candidate 3x → 1 API call + 2 cache hits

**Cost**: $0.10 per enrichment × 1 = $0.10 (saves $0.20)

---

## Cache Logic

### Cache Freshness Rules

1. **Fresh (0-7 days)**: Use cached data, no API call
2. **Stale (>7 days)**: Fetch fresh data, update cache
3. **Missing timestamp**: Treat as stale, fetch fresh data
4. **No data**: Fetch and store

### Cache Check Function

```typescript
async function checkEnrichmentCache(contactId: string) {
  // Query database
  const { data } = await supabase
    .from('contacts')
    .select('enrich_person_from_profile, enriched_at')
    .eq('id', contactId)
    .single();

  // No enrichment data?
  if (!data.enrich_person_from_profile) {
    return null; // Cache miss
  }

  // Check age
  const enrichedDate = new Date(data.enriched_at);
  const ageDays = (Date.now() - enrichedDate.getTime()) / (1000 * 60 * 60 * 24);

  if (ageDays <= 7) {
    // Cache hit!
    return { data: data.enrich_person_from_profile, age_days: ageDays };
  }

  // Too old
  return null; // Cache miss
}
```

### Store Function

```typescript
async function storeEnrichmentData(contactId: string, enrichmentData: any) {
  await supabase
    .from('contacts')
    .update({
      enrich_person_from_profile: enrichmentData,
      enriched_at: new Date().toISOString(), // Record timestamp
    })
    .eq('id', contactId);
}
```

---

## Agent Behavior

The AI agent automatically uses caching when calling `enrich_candidate`:

```typescript
// Tool definition now includes contact_id
{
  name: 'enrich_candidate',
  description: '... IMPORTANT: Results are cached for 7 days - always pass contact_id ...',
  input_schema: {
    properties: {
      contact_id: {
        type: 'string',
        description: 'Contact ID from database (REQUIRED for caching)',
      },
      email: { type: 'string' },
      linkedin_url: { type: 'string' },
    },
  },
}
```

**Agent automatically passes contact_id** from search results:

```typescript
// Search returns contacts with IDs
const contacts = await searchContacts({...});
// Returns: [{ id: "123", name: "John", email: "...", ... }]

// Agent enriches with ID
await enrichCandidate({
  contact_id: "123",  // Enables caching!
  email: contacts[0].email,
  linkedin_url: contacts[0].linkedin_url,
});
```

---

## Console Output

### Cache Miss (Fresh API Call)

```
🔍 Fetching fresh enrichment data from Enrich Layer API...
✓ Stored enrichment data in database for contact 123
```

### Cache Hit (Using Cached Data)

```
✓ Using cached enrichment data for contact 123 (age: 2.3 days)
```

### Stale Cache (Refreshing)

```
⚠️  Enrichment data for contact 123 is 9 days old (>7 days), fetching fresh data...
🔍 Fetching fresh enrichment data from Enrich Layer API...
✓ Stored enrichment data in database for contact 123
```

---

## Cost Savings

### Example: Sobrato VP Search

**Scenario**: Agent searches for 50 candidates, enriches top 10

**Without Caching** (before):
- 10 candidates × 1 enrichment each = 10 API calls
- Cost: 10 × $0.10 = $1.00

**With Caching** (after, running same search 3 times):
- Search 1: 10 API calls (all cache misses) = $1.00
- Search 2: 0 API calls (all cache hits) = $0.00
- Search 3: 0 API calls (all cache hits) = $0.00
- **Total**: $1.00 vs $3.00 = **$2.00 saved (67% reduction)**

### Monthly Savings

**Assumptions**:
- 100 searches/month
- 10 enrichments per search
- 30% of searches involve previously enriched candidates

**Without Caching**:
- 100 searches × 10 enrichments × $0.10 = $100/month

**With Caching**:
- 70% new candidates: 700 × $0.10 = $70
- 30% cached candidates: 300 × $0.00 = $0
- **Total**: $70/month = **$30/month saved (30% reduction)**

---

## Configuration

### Cache Duration

Default is 7 days. To change:

```typescript
// In lib/enrichment.ts, line ~122
if (ageDays <= 7) {  // Change this number
  return cached;
}
```

**Recommended values**:
- **7 days** (default): Good balance for most use cases
- **30 days**: For relatively static data (founders, executives)
- **1 day**: For very dynamic data (job changes common)
- **365 days**: For historical/archived contacts

### Disable Caching

To temporarily disable caching (for testing):

```typescript
// In lib/enrichment.ts, line ~54
if (contactId && false) {  // Add && false
  const cached = await checkEnrichmentCache(contactId);
  // ...
}
```

---

## Testing

### Test Cache Miss

```typescript
// Make API call for new contact
const result1 = await enrichCandidate(
  "new-contact-id",
  "test@example.com",
  "https://linkedin.com/in/test"
);

// Check console for:
// "🔍 Fetching fresh enrichment data from Enrich Layer API..."
// "✓ Stored enrichment data in database for contact new-contact-id"
```

### Test Cache Hit

```typescript
// Call again immediately
const result2 = await enrichCandidate(
  "new-contact-id",
  "test@example.com",
  "https://linkedin.com/in/test"
);

// Check console for:
// "✓ Using cached enrichment data for contact new-contact-id (age: 0.0 days)"
```

### Verify in Database

```sql
SELECT
  id,
  first_name,
  last_name,
  enriched_at,
  NOW() - enriched_at AS age,
  enrich_person_from_profile IS NOT NULL AS has_data
FROM contacts
WHERE enriched_at IS NOT NULL
ORDER BY enriched_at DESC
LIMIT 10;
```

---

## Troubleshooting

### Cache Not Working

**Symptom**: Every enrichment makes API call

**Causes**:
1. **contact_id not passed**: Agent must include `contact_id` in tool call
   - Check agent-tools.ts executeToolCall()
   - Verify search results include `id` field

2. **enriched_at column missing**: Run migration SQL
   ```sql
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'contacts' AND column_name = 'enriched_at';
   ```

3. **Timestamp too old**: Check enriched_at values
   ```sql
   SELECT enriched_at, NOW() - enriched_at AS age
   FROM contacts WHERE id = 'problem-contact-id';
   ```

### Stale Data

**Symptom**: Enrichment data doesn't reflect recent job changes

**Solution 1**: Reduce cache duration (7 days → 1 day)

**Solution 2**: Manual cache invalidation
```sql
UPDATE contacts
SET enriched_at = NULL
WHERE id = 'contact-id-to-refresh';
```

**Solution 3**: Bulk refresh stale data
```sql
UPDATE contacts
SET enriched_at = NULL
WHERE enriched_at < NOW() - INTERVAL '30 days';
```

---

## Benefits Summary

### Cost Savings
- ✅ Avoid duplicate API calls
- ✅ 30-70% cost reduction depending on search patterns
- ✅ Predictable API costs

### Performance
- ✅ Faster enrichment (database query vs API call)
- ✅ No rate limit concerns
- ✅ Works offline for cached data

### Data Quality
- ✅ Consistent data across searches
- ✅ Historical tracking (when last enriched)
- ✅ Can refresh stale data on demand

---

## Migration Checklist

- [x] Add `enriched_at` column to database
- [x] Create index on `enriched_at`
- [x] Update `enrichCandidate()` function
- [x] Update agent tool definition
- [x] Update executeToolCall() to pass contact_id
- [x] Build and test successfully
- [ ] Run migration SQL on production database
- [ ] Monitor cache hit rates in logs
- [ ] Verify cost savings in Enrich Layer dashboard

---

## Next Steps

1. **Run migration**:
   ```bash
   psql $DATABASE_URL < add_enriched_at_column.sql
   ```

2. **Deploy to production**:
   ```bash
   cd job-matcher-ai && npx vercel --prod
   ```

3. **Monitor caching**:
   - Watch console logs for cache hits/misses
   - Check Enrich Layer API usage dashboard
   - Verify cost reduction

4. **Optimize cache duration**:
   - Monitor how often data becomes stale
   - Adjust 7-day default if needed
   - Consider different durations for different contact types

---

**Status**: ✅ Implemented and ready for production
**Build**: ✅ Successful
**Next**: Run migration SQL on production database
