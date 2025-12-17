# Quick Start Guide

## Test Locally (2 minutes)

1. **Start the development server**:
```bash
cd /Users/Justin/Code/TrueSteele/contacts/job-matcher-ai
npm run dev
```

2. **Open browser**: http://localhost:3000

3. **Test with Sobrato VP job**:
   - Click "Upload PDF"
   - Select: `/Users/Justin/Code/TrueSteele/contacts/docs/Vice President of Data, Impact, and Learning.pdf`
   - Watch the agent work!

## Expected Behavior

The agent will automatically:

1. **Parse the PDF**:
   ```
   ✓ Extracted job details:
     - Role: VP of Data, Impact, and Learning
     - Location: Mountain View, CA
     - Salary: $257k-$321k
     - Key requirements: Data strategy, philanthropy, learning systems
   ```

2. **Search Strategy**:
   ```
   Searching contacts with keywords:
   - ["data", "impact", "learning", "philanthropy", "measurement"]
   - Location: Bay Area cities
   - Initial pool: 50+ candidates
   ```

3. **Filter & Enrich**:
   ```
   Filtering to top 20 candidates...
   Enriching top 10 with additional data...
   ```

4. **Detailed Evaluation**:
   ```
   Evaluating final 5-8 candidates:
   - Scoring against job criteria
   - Assessing experience fit
   - Identifying strengths and gaps
   ```

5. **Present Results**:
   ```
   TOP CANDIDATES:

   1. [Name] - Score: 9/10
      Current: [Position] at [Company]
      Location: [City]

      Why they're a great fit:
      - [Specific evidence from their background]
      - [Another key qualification]

      Areas to explore in interview:
      - [Question 1]
      - [Question 2]

   2. [Next candidate]...
   ```

## Deploy to Vercel (5 minutes)

### Method 1: One Command

```bash
cd /Users/Justin/Code/TrueSteele/contacts/job-matcher-ai
npx vercel --prod
```

When prompted:
- "Set up and deploy?": **Yes**
- "Which scope?": Select your account
- "Link to existing project?": **No**
- "What's your project's name?": **job-matcher-ai**
- "In which directory?": **./**
- "Override settings?": **No**

Then add environment variables:

```bash
# Required
vercel env add ANTHROPIC_API_KEY production
# Paste: sk-ant-api03-YOUR_KEY_HERE

vercel env add SUPABASE_URL production
# Paste: https://ypqsrejrsocebnldicke.supabase.co

vercel env add SUPABASE_SERVICE_KEY production
# Paste: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlwcXNyZWpyc29jZWJubGRpY2tlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjMxOTU0NCwiZXhwIjoyMDUxODk1NTQ0fQ.rqMazvcbqBULxwYNM0AZSKu43Hps2FSkwwyZYtNkik8

# Optional but recommended
vercel env add ENRICH_LAYER_API_KEY production
# Paste: Z6mEE3xJ3_sRXrZEXMjxEg

vercel env add PERPLEXITY_API_KEY production
# Paste: pplx-YOUR_KEY_HERE
```

Redeploy with new env vars:
```bash
vercel --prod
```

Done! Your app is live at `https://job-matcher-ai.vercel.app`

### Method 2: GitHub + Vercel Dashboard

```bash
# Initialize git and push
cd /Users/Justin/Code/TrueSteele/contacts/job-matcher-ai
git init
git add .
git commit -m "Initial commit: AI Job Matcher"

# Create GitHub repo at github.com/new
# Then:
git remote add origin git@github.com:YOUR_USERNAME/job-matcher-ai.git
git branch -M main
git push -u origin main
```

Then:
1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository
3. Add environment variables (see above)
4. Deploy!

## Test in Production

1. Go to your deployed URL
2. Upload: `Vice President of Data, Impact, and Learning.pdf`
3. Verify results match local testing

## Example Usage Scenarios

### Scenario 1: Upload Job Description
```
User: [Uploads Sobrato VP PDF]

Agent:
✓ Parsed job description
✓ Identified key requirements
✓ Searching 50 candidates in Bay Area
✓ Found 12 with data/impact/learning experience
✓ Enriching top 8 candidates
✓ Detailed evaluation of 5 finalists

Results: [Ranked list with scores and rationale]
```

### Scenario 2: Text Description
```
User: "Find candidates for a mid-level grants manager role
at a foundation in the Bay Area. Need Salesforce experience."

Agent:
✓ Extracted requirements: grants management, foundation, Salesforce, Bay Area
✓ Searching database with keywords
✓ Found 15 candidates
✓ Filtering for mid-level (excluding senior executives)
✓ Evaluating top 8

Results: [Ranked candidates]
```

### Scenario 3: Refine Search
```
User: [After initial results] "Can you find more candidates
in Seattle or Portland?"

Agent:
✓ Expanding search to Pacific Northwest
✓ Found 8 additional candidates
✓ Evaluating against same criteria

Additional Results: [New candidates]
```

### Scenario 4: Research Market
```
User: "Before showing candidates, can you research the current
market for data leaders in philanthropy?"

Agent:
✓ Using Perplexity to research
✓ Analyzing market trends

Insights:
- Average salary for VP of Data in philanthropy: $280k-$350k
- Key skills in demand: AI/ML, data governance, impact measurement
- Competitive landscape: [Details]

Now searching candidates with these insights...
```

## Troubleshooting

### Local Development

**Port already in use**:
```bash
kill -9 $(lsof -ti:3000)
npm run dev
```

**Can't connect to Supabase**:
- Check `.env.local` file exists
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are correct

**PDF upload fails**:
- Ensure file is under 10MB
- Check file is valid PDF format

### Production

**"Unauthorized" errors**:
- Verify environment variables are set in Vercel
- Check Supabase service key hasn't expired

**Function timeout**:
- Check Vercel function logs
- Consider upgrading Vercel plan for longer execution time

**No candidates found**:
- Verify database has contacts
- Check keyword matching is appropriate
- Try broader search terms

## Next Steps

1. **Test with your other job descriptions**:
   - Catalyst Exchange Senior Fellow
   - Raikes Foundation ED
   - Any custom searches

2. **Customize evaluation criteria**:
   - Edit `lib/agent-tools.ts`
   - Modify scoring in `evaluateCandidate` function

3. **Add custom tools**:
   - Email integration
   - Calendar scheduling
   - CRM export

4. **Optimize performance**:
   - Add database indexes
   - Implement caching
   - Batch processing

## Support

Check these files for detailed information:
- `README.md` - Complete documentation
- `ARCHITECTURE.md` - System design
- `DEPLOYMENT.md` - Deployment details

## Cost Tracking

Monitor your usage:
- **Anthropic**: ~$0.03 per detailed evaluation
- **Perplexity**: ~$0.20 per research query
- **Enrich Layer**: Varies by plan
- **Vercel**: Free for hobby projects

For a typical search (10 evaluations, 2 research queries):
- Cost: ~$0.70
- Time: 30-60 seconds

Enjoy your AI-powered job search tool! 🚀
