# Deployment Guide

## Quick Deploy to Vercel

### Option 1: Via Vercel Dashboard (Recommended)

1. **Push to GitHub**:
```bash
cd job-matcher-ai
git init
git add .
git commit -m "Initial commit: AI Job Search Agent"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

2. **Import to Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new)
   - Click "Import Git Repository"
   - Select your repository
   - Vercel will auto-detect Next.js

3. **Configure Environment Variables**:
   In the Vercel dashboard, go to Settings → Environment Variables and add:

   ```
   ANTHROPIC_API_KEY = sk-ant-api03-...
   SUPABASE_URL = https://ypqsrejrsocebnldicke.supabase.co
   SUPABASE_SERVICE_KEY = eyJhbGciOiJIUzI1NiIs...
   ENRICH_LAYER_API_KEY = Z6mEE3xJ3_sRXrZEXMjxEg
   PERPLEXITY_API_KEY = pplx-YOUR_KEY_HERE
   PERPLEXITY_MODEL = sonar-reasoning-pro
   ```

4. **Deploy**:
   - Click "Deploy"
   - Wait for build to complete
   - Your app will be live at `https://your-app.vercel.app`

### Option 2: Via Vercel CLI

1. **Install Vercel CLI**:
```bash
npm i -g vercel
```

2. **Login**:
```bash
vercel login
```

3. **Deploy**:
```bash
cd job-matcher-ai
vercel
```

4. **Add Environment Variables**:
```bash
vercel env add ANTHROPIC_API_KEY production
# Paste your API key when prompted

vercel env add SUPABASE_URL production
# Paste your Supabase URL

vercel env add SUPABASE_SERVICE_KEY production
# Paste your service key

vercel env add ENRICH_LAYER_API_KEY production
# Optional: Paste your Enrich Layer key

vercel env add PERPLEXITY_API_KEY production
# Optional: Paste your Perplexity key
```

5. **Deploy to Production**:
```bash
vercel --prod
```

## Environment Variables Setup

### Required Variables

1. **ANTHROPIC_API_KEY**
   - Get from: https://console.anthropic.com/
   - Format: `sk-ant-api03-...`
   - Used for: Main AI agent (Claude 4.5 Sonnet)

2. **SUPABASE_URL**
   - Get from: Supabase project settings
   - Format: `https://[project-id].supabase.co`
   - Used for: Database connection

3. **SUPABASE_SERVICE_KEY**
   - Get from: Supabase project settings → API
   - Format: `eyJhbGciOiJIUzI1NiIs...`
   - Used for: Server-side database queries
   - ⚠️ Keep this secret!

### Optional But Recommended

4. **ENRICH_LAYER_API_KEY**
   - Get from: https://enrichlayer.com
   - Used for: Candidate data enrichment
   - Without this: Agent works but with limited candidate info

5. **PERPLEXITY_API_KEY**
   - Get from: https://www.perplexity.ai/settings/api
   - Used for: Real-time market research
   - Without this: Agent works but cannot do research

6. **PERPLEXITY_MODEL**
   - Default: `sonar-reasoning-pro`
   - Options: `sonar`, `sonar-pro`, `sonar-reasoning`

## Copying Existing Environment

You can copy from your existing `.env` file:

```bash
cd /Users/Justin/Code/TrueSteele/contacts/job-matcher-ai

# Create .env.local from your existing credentials
cat > .env.local << 'EOF'
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
SUPABASE_URL=https://ypqsrejrsocebnldicke.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlwcXNyZWpyc29jZWJubGRpY2tlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjMxOTU0NCwiZXhwIjoyMDUxODk1NTQ0fQ.rqMazvcbqBULxwYNM0AZSKu43Hps2FSkwwyZYtNkik8
ENRICH_LAYER_API_KEY=Z6mEE3xJ3_sRXrZEXMjxEg
PERPLEXITY_API_KEY=pplx-YOUR_KEY_HERE
PERPLEXITY_MODEL=sonar-reasoning-pro
EOF
```

## Testing Before Deployment

1. **Local Test**:
```bash
npm run dev
```
   - Open http://localhost:3000
   - Upload the Sobrato VP PDF
   - Verify results

2. **Build Test**:
```bash
npm run build
npm start
```
   - Ensures production build works

## Post-Deployment

### 1. Test Your Production App

Upload the Sobrato VP of Data job description and verify:
- PDF uploads successfully
- Agent searches database
- Results are formatted correctly
- Follow-up questions work

### 2. Monitor Performance

In Vercel Dashboard:
- Check function execution times
- Monitor error logs
- Review bandwidth usage

### 3. Set Up Custom Domain (Optional)

1. Go to Vercel project settings
2. Click "Domains"
3. Add your custom domain
4. Update DNS records as instructed

## Troubleshooting

### Build Fails

**Error**: "Module not found"
```bash
npm install
npm run build
```

**Error**: "Type errors"
- Check `tsconfig.json`
- Run `npm run lint`

### Runtime Errors

**Error**: "Unauthorized" from Supabase
- Check `SUPABASE_SERVICE_KEY` is set correctly
- Verify key has not expired

**Error**: "Anthropic API error"
- Check `ANTHROPIC_API_KEY` is valid
- Verify account has credits

### Function Timeout

If agent takes too long:
- Increase `maxDuration` in `app/api/chat/route.ts`
- Optimize database queries
- Reduce number of candidates evaluated

## Scaling Considerations

### For Heavy Usage

1. **Add Rate Limiting**:
   - Use Vercel rate limiting
   - Or implement Upstash Redis

2. **Optimize Database**:
```sql
-- Add indexes
CREATE INDEX idx_contacts_search ON contacts USING gin(to_tsvector('english', summary));
```

3. **Cache Enrichment Data**:
   - Use Redis for enriched candidates
   - Reduce API calls to Enrich Layer

4. **Upgrade Vercel Plan**:
   - Pro plan for longer function execution
   - More concurrent requests

## Security Checklist

- [ ] Environment variables are set in Vercel (not in code)
- [ ] `.env.local` is in `.gitignore`
- [ ] Supabase RLS policies are configured
- [ ] CORS is properly configured
- [ ] Rate limiting is enabled
- [ ] API keys are rotated regularly

## Cost Estimation

### Vercel
- **Hobby Plan**: Free (good for personal use)
- **Pro Plan**: $20/month (recommended for production)

### APIs
- **Anthropic**: ~$3-5 per 100 candidate evaluations
- **Enrich Layer**: Varies by plan
- **Perplexity**: ~$0.20 per search

## Support

If you encounter issues:
1. Check Vercel deployment logs
2. Review API function logs
3. Test locally with `npm run dev`
4. Check environment variables are set correctly
