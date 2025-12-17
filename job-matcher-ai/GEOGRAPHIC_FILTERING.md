# Geographic Filtering Strategy

## Research-Backed Approach

Based on industry research of LinkedIn, Indeed, and modern ATS systems, our geographic filtering uses **Metropolitan Statistical Area (MSA)** expansion to match industry best practices.

## How It Works

### Automatic Metro Area Expansion

When you search for a job in **any city**, the system automatically expands to the **entire metro area**:

**Example: Mountain View, CA Job**
- Input: `["Mountain View"]`
- Expanded to: All 80+ Bay Area cities including:
  - San Francisco
  - Oakland
  - Fremont
  - San Jose
  - Berkeley
  - Palo Alto
  - Redwood City
  - ... and 70+ more

**Result**: ✅ Candidate in Fremont **WILL match** Mountain View job

### Industry Standards (from Research)

| Platform | Default Radius | Approach |
|----------|---------------|----------|
| **LinkedIn Recruiter** | 100 miles | MSA-based (our approach) |
| **Indeed, ZipRecruiter** | 25 miles | Radius-based |
| **Google Jobs** | Commute time | Time-based |
| **Our System** | MSA (~100 mi) | **Matches LinkedIn** |

### Supported Metro Areas

We've defined 8 major U.S. metro areas with comprehensive city coverage:

1. **San Francisco Bay Area** (80+ cities)
   - SF, Peninsula, East Bay, South Bay, North Bay
   - Oakland, Fremont, San Jose, Palo Alto, etc.

2. **Seattle Metro** (30+ cities)
   - Seattle, Bellevue, Redmond, Tacoma, etc.

3. **Portland Metro** (20+ cities)
   - Portland, Beaverton, Hillsboro, Vancouver, etc.

4. **New York Metro** (30+ cities)
   - NYC, Jersey City, Hoboken, Stamford, etc.

5. **Boston Metro** (20+ cities)
   - Boston, Cambridge, Newton, Waltham, etc.

6. **Washington DC Metro** (25+ cities)
   - DC, Arlington, Alexandria, Bethesda, etc.

7. **Los Angeles Metro** (20+ cities)
   - LA, Santa Monica, Pasadena, Long Beach, etc.

8. **Chicago Metro** (10+ cities)
   - Chicago, Evanston, Naperville, etc.

## Why This Approach?

### Research Findings (October 2024)

1. **LinkedIn Uses 100-Mile Radius**
   - "Implied 100-mile radius to any location selection in LinkedIn Recruiter"
   - Industry standard for professional recruiting

2. **Average Commute: 15-45 Minutes**
   - Most people commute 10-20 miles
   - MSA boundaries align with realistic commute zones

3. **MSA = Government Standard**
   - Used by U.S. Census Bureau
   - Updated in 2024 based on 2020 census data
   - Recognized by all major recruiting platforms

4. **Remote Work Considerations**
   - 2024 trend: Geographic flexibility increasing
   - Our system: Can omit location entirely for remote roles

## Examples

### Example 1: Bay Area Search
```typescript
Job Location: Mountain View, CA
Agent searches: ["Mountain View"]
System expands to: 80+ Bay Area cities
Results include:
  ✅ Candidate in San Francisco (45 min commute)
  ✅ Candidate in Fremont (30 min commute)
  ✅ Candidate in Oakland (40 min commute)
  ✅ Candidate in San Jose (25 min commute)
```

### Example 2: Seattle Search
```typescript
Job Location: Seattle, WA
Agent searches: ["Seattle"]
System expands to: 30+ Seattle metro cities
Results include:
  ✅ Candidate in Bellevue (15 min commute)
  ✅ Candidate in Redmond (25 min commute)
  ✅ Candidate in Tacoma (45 min commute)
```

### Example 3: Remote Role
```typescript
Job Location: Remote (U.S.)
Agent searches: [] // No location filter
Results include:
  ✅ Any candidate anywhere in U.S.
```

## Technical Implementation

### Code Flow

1. **Agent receives job description**
   ```
   "VP of Data role in Mountain View, CA"
   ```

2. **Agent calls search_candidates tool**
   ```typescript
   search_candidates({
     keywords: ["data", "vp", "director"],
     locations: ["Mountain View"]
   })
   ```

3. **System expands locations**
   ```typescript
   expandToMetroAreas(["Mountain View"])
   // Returns: [all 80+ Bay Area cities]
   ```

4. **Database query**
   ```sql
   SELECT * FROM contacts
   WHERE city IN ('Mountain View', 'San Francisco', 'Oakland', ...)
   AND (summary ILIKE '%data%' OR ...)
   ```

5. **Results returned with metro context**
   ```
   Found 45 candidates across San Francisco Bay Area
   ```

## Advantages Over Radius-Based Search

| Aspect | Radius-Based (25 mi) | MSA-Based (Our Approach) |
|--------|---------------------|-------------------------|
| **Simplicity** | Simple circle | Follows real geography |
| **Accuracy** | Misses nearby cities | Includes commute zones |
| **Example** | Mountain View → misses Oakland | Mountain View → includes Oakland |
| **Industry Standard** | Job boards | LinkedIn, ATS systems |
| **Flexibility** | Fixed radius | Adapts to metro shape |

**Real Example**:
- **25-mile radius** from Mountain View: Misses Oakland (35 miles)
- **MSA approach**: Includes Oakland (same metro, realistic commute)

## Future Enhancements

### Phase 2 Possibilities

1. **Geocoding with Distance Calculation**
   - Store lat/long for each candidate
   - Calculate actual driving distance
   - Filter by commute time (Google Maps API)

2. **Hybrid Approach**
   - MSA by default (broad)
   - Optional radius filter (precise)
   - Let user choose: "Strict 25mi" or "Metro area"

3. **Commute Time Analysis**
   - Use Google Maps Directions API
   - Filter by actual drive time
   - Consider traffic patterns

4. **Smart Recommendations**
   - "Consider expanding to full Bay Area? (+30 candidates)"
   - "Nearby cities: Oakland (35 mi), San Jose (40 mi)"

## Configuration

### To Add New Metro Areas

Edit `lib/metro-areas.ts`:

```typescript
export const METRO_AREAS: Record<string, MetroArea> = {
  'your-metro-key': {
    name: 'Your Metro Area Name',
    cities: ['City 1', 'City 2', ...],
    states: ['State', 'ST'],
    description: 'Description',
  },
};
```

### To Adjust Standards

Edit `COMMUTE_STANDARDS` in `lib/metro-areas.ts`:

```typescript
export const COMMUTE_STANDARDS = {
  METRO_AREA_RADIUS_MILES: 100,  // Adjust as needed
  DEFAULT_SEARCH_RADIUS_MILES: 25,
  // ...
};
```

## Logging & Debugging

The system logs metro expansion in the console:

```bash
📍 Location Search: Mountain View → Expanded to 80 metro area cities (MSA standard)
```

This helps you verify the expansion is working correctly.

## References

- U.S. Bureau of Labor Statistics - Metropolitan Statistical Areas (2024)
- LinkedIn Recruiter Documentation - Location Search
- Indeed/ZipRecruiter - Geographic Filtering Best Practices
- Google Cloud Talent Solution - Commute Search Documentation

## Summary

Our **MSA-based approach** matches industry leader **LinkedIn Recruiter** and provides:

✅ **Broader reach** - Don't miss great candidates in nearby cities
✅ **Realistic geography** - Follows actual metro boundaries
✅ **Industry standard** - 100-mile radius matches LinkedIn
✅ **Better UX** - One city search covers entire metro area
✅ **Future-proof** - Can add radius/time filters later

**Bottom line**: A candidate in Fremont is absolutely a match for a Mountain View job, and our system handles this correctly!
