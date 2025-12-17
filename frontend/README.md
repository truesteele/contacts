# Donor Prospect Management Frontend

A beautiful, nature-inspired interface for managing Outdoorithm Collective's 1,498 donor prospects.

## Design Philosophy

**"Nature Journal × Editorial CRM"**

This interface blends organic, nature-inspired aesthetics with editorial refinement:
- **Earth-tone palette**: Sage green, terracotta, cream, and charcoal
- **Beautiful typography**: Crimson Pro (serif) + Work Sans (sans-serif)
- **Topographic patterns**: Subtle contour lines evoking trail maps
- **Smooth interactions**: Thoughtful animations and micro-interactions

## Features

### Advanced Filtering
- **Search**: Find prospects by name, company, or title
- **Philanthropic Activity**: Filter by board members and known donors
- **Mission Affinity**: Filter by outdoor/environmental, equity/DEI, or family/youth focus
- **Warmth Level**: Filter by Hot, Warm, Cool, or Cold relationships
- **Active Filter Chips**: See what filters are applied at a glance
- **Saved Context**: Filters persist during your session

### Sorting Options
- Sort by warmth/connection strength
- Sort alphabetically by name
- Sort by capacity score
- Sort by affinity score

### Prospect Cards
Each card displays:
- Name and current role
- Warmth level badge
- Board membership and donor status indicators
- Mission affinity tags (Outdoor, Equity, Family)
- Cultivation notes preview
- Connection strength (0-10)

### Detailed View Modal
Click any prospect to see:
- **Complete AI research summary**: KEY FINDINGS and RECOMMENDED APPROACH from Perplexity + GPT-5.1-mini
- **Philanthropic activity**: Board positions, giving history
- **Mission affinity evidence**: Specific outdoor, equity, and family connections
- **Editable cultivation fields**:
  - Warmth level (Hot/Warm/Cool/Cold)
  - Connection strength (0-10)
  - Cultivation stage (Not Started → Closed Won)
  - Next touchpoint date and type
  - Personal relationship notes

### Data Integration
- **Live Supabase connection**: Real-time data from your PostgreSQL database
- **1,498 structured prospects**: All prospects with AI research and structured data
- **Instant updates**: Changes save directly to the database

## Running the Frontend

### Option 1: npm (Recommended)

```bash
cd frontend
npm run dev
```

Then open: http://localhost:8080

### Option 2: Python Server

```bash
cd frontend
python3 server.py
```

Then open: http://localhost:8080

### Option 3: Any Web Server

Serve the `frontend/` directory with any static file server.

## Project Structure

```
frontend/
├── index.html          # HTML structure
├── styles.css          # Nature-inspired CSS with topographic patterns
├── app.js             # React application with Supabase integration
└── README.md          # This file
```

## Manual Fields

Users can manually edit these fields in the modal:
- **warmth_level**: Relationship temperature (Hot/Warm/Cool/Cold)
- **personal_connection_strength**: 0-10 rating
- **relationship_notes**: Free-form personal notes
- **cultivation_stage**: Pipeline stage
- **next_touchpoint_date**: Scheduled next contact
- **next_touchpoint_type**: Type of next interaction

All changes save immediately to Supabase.

## Filter Best Practices

Based on 2025 CRM research:

1. **Instant filtering**: Results update in real-time as you type/click
2. **Active filter visibility**: Chips show what's applied
3. **Compound filters**: Combine multiple criteria (e.g., "Board Members" + "Equity Focus" + "Warm")
4. **Clear path to reset**: One-click "Clear all" button
5. **Persistent context**: Filters remain while browsing prospects

## Design Differentiators

What makes this interface memorable:

1. **Topographic background**: Subtle contour lines create depth without distraction
2. **Nature palette**: Earthy tones reflect the outdoor mission
3. **Editorial typography**: Crimson Pro serif headlines feel refined, not corporate
4. **Staggered animations**: Cards fade in with slight delays for polish
5. **Organic shapes**: Rounded corners and flowing layouts
6. **Context-appropriate**: Design matches Outdoorithm's outdoor/equity mission

## Sources

Design research:
- [Filter UI Best Practices 2025](https://www.eleken.co/blog-posts/filter-ux-and-ui-for-saas)
- [CRM Contact Management Strategies](https://bigsea.co/ideas/7-contact-management-nonprofit-strategies/)
- [Nonprofit Donor Management Best Practices](https://www.netsuite.com/portal/resource/articles/crm/donor-management-best-practices.shtml)
- [Advanced Filtering UX Patterns](https://smart-interface-design-patterns.com/articles/complex-filtering/)

---

Built with production-ready code, distinctive aesthetics, and donor cultivation best practices.
