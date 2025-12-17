# AI Job Search Agent

An intelligent, agentic conversational tool for finding the best candidates from your personal network based on job descriptions.

## Features

- **Conversational AI Interface**: Natural language interaction with Claude 4.5 Sonnet
- **PDF Job Description Upload**: Automatically parse and analyze job requirements
- **Intelligent Candidate Search**: Multi-criteria filtering with keyword and location matching
- **Real-time Enrichment**: Integration with Enrich Layer for detailed candidate data
- **Market Research**: Perplexity AI integration for industry insights
- **Detailed Evaluations**: AI-powered candidate assessments with scoring and rationale
- **Streaming Responses**: Real-time updates as the agent works

## Technology Stack

- **Frontend**: Next.js 15, React 19, TailwindCSS, Shadcn/UI
- **Backend**: Next.js API Routes (Edge Runtime)
- **AI**: Anthropic Claude 4.5 Sonnet with tool calling
- **Database**: Supabase (PostgreSQL)
- **Integrations**: Enrich Layer, Perplexity AI
- **Deployment**: Vercel

## Setup

### Prerequisites

- Node.js 18+
- Supabase account and database
- Anthropic API key
- Enrich Layer API key (optional but recommended)
- Perplexity API key (optional but recommended)

### Installation

1. Clone or navigate to the project:
```bash
cd job-matcher-ai
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env.local` file:
```bash
cp .env.local.example .env.local
```

4. Configure environment variables in `.env.local`:
```env
ANTHROPIC_API_KEY=your_anthropic_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
ENRICH_LAYER_API_KEY=your_enrich_layer_key
PERPLEXITY_API_KEY=your_perplexity_key
PERPLEXITY_MODEL=sonar-reasoning-pro
```

5. Run development server:
```bash
npm run dev
```

6. Open [http://localhost:3000](http://localhost:3000)

## Usage

### Basic Workflow

1. **Upload Job Description**: Click "Upload PDF" and select a job description PDF
2. **AI Analysis**: The agent automatically:
   - Parses the job requirements
   - Identifies key qualifications and criteria
   - Searches your network database
   - Enriches top candidates
   - Performs detailed evaluations
   - Ranks and presents results

3. **Refine Search**: Ask follow-up questions like:
   - "Can you find more candidates in Seattle?"
   - "Focus on candidates with nonprofit experience"
   - "What about remote candidates?"

### Example Queries

- "Find candidates for a VP of Data role in Mountain View, CA with philanthropy experience"
- "I need someone with state government and education policy background"
- "Search for mid-level grants managers in the Bay Area"

## Architecture

### Agent Workflow

```
User Input → Claude Agent → Tool Selection → Execution → Response
                 ↓
         [search_candidates]
         [enrich_candidate]
         [research_topic]
         [evaluate_candidate]
```

### Key Files

- `app/api/chat/route.ts` - Main agent orchestration
- `lib/agent-tools.ts` - Tool definitions and execution
- `lib/supabase.ts` - Database queries
- `lib/enrichment.ts` - External API integrations
- `components/chat-interface.tsx` - UI component

## Deployment to Vercel

### Via Vercel CLI

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Login to Vercel:
```bash
vercel login
```

3. Deploy:
```bash
vercel
```

4. Set environment variables:
```bash
vercel env add ANTHROPIC_API_KEY
vercel env add SUPABASE_URL
vercel env add SUPABASE_SERVICE_KEY
vercel env add ENRICH_LAYER_API_KEY
vercel env add PERPLEXITY_API_KEY
```

5. Deploy to production:
```bash
vercel --prod
```

### Via Vercel Dashboard

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your Git repository
3. Configure environment variables in Settings → Environment Variables
4. Deploy

## Database Schema

The agent expects a `contacts` table in Supabase with the following columns:

```sql
CREATE TABLE contacts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  first_name TEXT,
  last_name TEXT,
  email TEXT,
  linkedin_url TEXT,
  company TEXT,
  position TEXT,
  city TEXT,
  state TEXT,
  headline TEXT,
  summary TEXT,
  enrich_person_from_profile JSONB
);

-- Add indexes for performance
CREATE INDEX idx_contacts_city ON contacts(city);
CREATE INDEX idx_contacts_state ON contacts(state);
CREATE INDEX idx_contacts_company ON contacts(company);
```

## Customization

### Modify Evaluation Criteria

Edit `lib/agent-tools.ts` in the `evaluateCandidate` function to customize scoring criteria.

### Add New Tools

1. Define tool in `lib/agent-tools.ts`:
```typescript
{
  name: 'my_custom_tool',
  description: 'What this tool does',
  input_schema: { /* parameters */ }
}
```

2. Add execution logic in `executeToolCall` function

3. The agent will automatically use the new tool when appropriate

### Adjust Search Strategy

Modify the system prompt in `app/api/chat/route.ts` to change how the agent approaches searches.

## Performance Optimization

- **Database Indexing**: Add indexes on frequently queried columns
- **Caching**: Implement Redis caching for enriched candidate data
- **Batch Processing**: Use parallel evaluation for multiple candidates
- **Rate Limiting**: Implement rate limits on API routes

## Troubleshooting

### PDF Upload Fails
- Check file size (max 10MB)
- Ensure file is valid PDF format
- Check API route logs

### No Candidates Found
- Verify database connection
- Check keyword matching logic
- Review location filters

### Agent Not Using Tools
- Check tool definitions in `agent-tools.ts`
- Review system prompt
- Check API key configuration

## Future Enhancements

- [ ] Vector embeddings for semantic search
- [ ] Multi-modal analysis (resume parsing, portfolio review)
- [ ] Email integration for candidate outreach
- [ ] Calendar integration for interview scheduling
- [ ] CRM export (Pipedrive, Salesforce)
- [ ] Analytics dashboard
- [ ] Saved search templates
- [ ] Candidate comparison views

## License

MIT

## Support

For issues or questions, please open an issue in the repository.
