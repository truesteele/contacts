# Agentic Job Search Chat Tool - Architecture

## Overview
Production-ready conversational AI system for intelligent candidate matching from personal network.

## System Architecture

```
┌─────────────────┐
│  Next.js UI     │  ← User drops job description (PDF/text)
│  (Vercel)       │  ← Chat interface with streaming responses
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  API Routes     │  ← /api/chat - Main agent endpoint
│  (Vercel Edge)  │  ← /api/upload - PDF upload handler
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────────┐
│         Claude AI Agent (Sonnet 4.5)         │
│  - Orchestrates entire search workflow       │
│  - Uses tool calling for data access         │
│  - Generates structured evaluations          │
└────────┬────────────────────────────────────┘
         │
         ├──────────┐──────────┐─────────────┐
         ↓          ↓          ↓             ↓
    ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
    │Supabase│ │Enrich  │ │Perplexity│ │PDF Parse │
    │contacts│ │Layer   │ │Research  │ │PyPDF2    │
    └────────┘ └────────┘ └──────────┘ └──────────┘
```

## Core Components

### 1. Frontend (Next.js 15 with App Router)
- **Chat Interface**: Streaming responses with markdown support
- **PDF Upload**: Drag-and-drop job description upload
- **Results Display**: Formatted candidate cards with scoring
- **Conversation History**: Persistent chat sessions

### 2. Backend (API Routes)
- **Agent Orchestration**: Claude handles tool calling autonomously
- **Tool Implementations**:
  - `search_candidates`: Query Supabase with filters
  - `evaluate_candidate`: AI-powered detailed evaluation
  - `enrich_candidate`: Call Enrich Layer for additional data
  - `research_topic`: Use Perplexity for market research
  - `parse_job_description`: Extract requirements from PDF/text

### 3. Data Layer
- **Supabase**: Contact database with enrichment data
- **Vector Search** (future): Semantic candidate matching
- **Session Store**: Conversation state management

## Key Features

### Agentic Capabilities
1. **Autonomous Planning**: Claude decides search strategy based on job requirements
2. **Multi-step Reasoning**: Filters → Enrichment → Evaluation → Ranking
3. **Adaptive Queries**: Refines search based on initial results
4. **Self-correction**: Can iterate if initial results are weak

### Tools Available to Agent

```typescript
tools = [
  {
    name: "search_candidates",
    description: "Search contacts database with filters",
    parameters: {
      keywords: string[],
      locations: string[],
      limit: number
    }
  },
  {
    name: "evaluate_candidate",
    description: "Detailed AI evaluation against job requirements",
    parameters: {
      candidate_id: string,
      job_description: string,
      criteria: object
    }
  },
  {
    name: "enrich_candidate",
    description: "Get additional data from Enrich Layer",
    parameters: {
      email: string,
      linkedin_url: string
    }
  },
  {
    name: "research_topic",
    description: "Use Perplexity for real-time market research",
    parameters: {
      query: string
    }
  }
]
```

## Workflow Example

User: "Find candidates for this VP of Data role at Sobrato [uploads PDF]"

```
Agent Planning:
1. Parse PDF → Extract: Mountain View, $257-321k, Data/Impact/Learning focus
2. Research → "Latest trends in philanthropy data leadership"
3. Search → Keywords: ["data", "philanthropy", "impact", "learning"], Location: Bay Area
4. Filter → 50 initial candidates
5. Enrich → Top 20 candidates with Enrich Layer
6. Evaluate → Detailed scoring on 15 strongest matches
7. Rank → Present top 5 with rationale
8. Respond → Formatted results with follow-up suggestions
```

## Technology Stack

### Frontend
- **Next.js 15**: App Router, React Server Components
- **TailwindCSS**: Styling
- **Shadcn/UI**: Component library
- **Vercel AI SDK**: Streaming responses

### Backend
- **Anthropic Claude 4.5 Sonnet**: Main agent
- **Supabase**: PostgreSQL database
- **Enrich Layer**: Contact enrichment
- **Perplexity API**: Research capability
- **PyPDF2/pdf-parse**: PDF processing

### Deployment
- **Vercel**: Hosting (Frontend + Edge Functions)
- **Environment Variables**: Secure key management
- **Edge Runtime**: Fast response times

## Security & Privacy

1. **API Keys**: Stored as Vercel environment variables
2. **Rate Limiting**: Implement on API routes
3. **Data Privacy**: No candidate data leaves your control
4. **Session Management**: Secure conversation state
5. **CORS**: Restrict origins

## Scalability Considerations

1. **Streaming**: Progressive response rendering
2. **Caching**: Cache enriched candidate data
3. **Batch Processing**: Parallel candidate evaluation
4. **Database Indexing**: Optimize Supabase queries
5. **Edge Functions**: Global distribution

## Future Enhancements

1. **Vector Embeddings**: Semantic candidate search
2. **Multi-modal**: Parse resumes, analyze portfolios
3. **Email Integration**: Auto-reach out to top candidates
4. **Calendar Integration**: Schedule interviews
5. **CRM Sync**: Export to Pipedrive
6. **Analytics Dashboard**: Track search performance
