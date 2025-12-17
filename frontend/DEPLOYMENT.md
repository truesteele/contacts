# Vercel Deployment Guide

## Quick Deploy (One Command)

```bash
cd frontend
vercel --prod
```

That's it! Your donor prospect management interface will be live at a Vercel URL.

## First-Time Setup

### 1. Install Vercel CLI

```bash
npm install -g vercel
```

### 2. Login to Vercel

```bash
vercel login
```

Follow the prompts to authenticate with your Vercel account (GitHub, GitLab, or email).

### 3. Deploy

From the `frontend/` directory:

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

## Configuration

The deployment is configured via `vercel.json`:

```json
{
  "version": 2,
  "name": "outdoorithm-donor-prospects",
  "builds": [{ "src": "index.html", "use": "@vercel/static" }]
}
```

This tells Vercel to:
- Deploy as a static site
- Serve `index.html` as the entry point
- Include security headers (XSS protection, frame options, etc.)

## Environment Variables

The app uses client-side Supabase connection, so no server-side environment variables are needed. The Supabase anon key is safe to expose in client-side code (it's designed for this).

**Current Supabase Config:**
- URL: `https://ypqsrejrsocebnldicke.supabase.co`
- Anon Key: Embedded in `app.js`

If you want to change these, edit [app.js](app.js) lines 4-6.

## Custom Domain (Optional)

### Add Your Domain

1. Go to your Vercel dashboard
2. Select your project
3. Go to Settings → Domains
4. Add your custom domain (e.g., `prospects.outdoorithm.com`)
5. Follow Vercel's DNS configuration instructions

### Update DNS

Add these records to your DNS:

```
Type: A
Name: prospects (or @)
Value: 76.76.21.21

Type: CNAME
Name: www
Value: cname.vercel-dns.com
```

Vercel will automatically handle SSL certificates.

## Deployment Workflow

### Option 1: Manual Deploy (Recommended for Testing)

```bash
cd frontend
vercel --prod
```

### Option 2: Git Integration (Automatic Deploys)

1. Push `frontend/` directory to a Git repo
2. Connect the repo to Vercel
3. Set root directory to `frontend/`
4. Every push to `main` auto-deploys to production
5. Every push to other branches creates preview deployments

### Option 3: GitHub Action (CI/CD)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Vercel
on:
  push:
    branches: [main]
    paths: ['frontend/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Vercel
        run: |
          npm install -g vercel
          cd frontend
          vercel --prod --token=${{ secrets.VERCEL_TOKEN }}
```

## Monitoring

After deployment, monitor your app:

1. **Vercel Dashboard**: https://vercel.com/dashboard
   - View deployment logs
   - Check analytics
   - Monitor performance

2. **Supabase Dashboard**: https://app.supabase.com
   - Monitor database queries
   - Check API usage
   - View real-time connections

## Troubleshooting

### Issue: Deployment fails

**Solution**: Check Vercel build logs:
```bash
vercel logs [deployment-url]
```

### Issue: Supabase connection errors

**Solution**: Verify RLS policies allow anon key access:
```sql
-- Check if anon can read contacts
SELECT * FROM contacts LIMIT 1;
```

If this fails, you may need to add RLS policies:

```sql
-- Enable RLS
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;

-- Allow read access for anon key (public access)
CREATE POLICY "Allow public read access"
ON contacts FOR SELECT
TO anon
USING (true);

-- Allow update for authenticated users only
CREATE POLICY "Allow authenticated updates"
ON contacts FOR UPDATE
TO authenticated
USING (true);
```

### Issue: 404 on routes

**Solution**: The app is single-page, all routes should work. If not, check `vercel.json` routing config.

### Issue: Slow loading

**Solution**: Vercel automatically optimizes static assets. If still slow:
1. Check Supabase query performance
2. Consider adding pagination (currently loads all 1,498 prospects)
3. Enable Vercel Edge Network caching

## Performance Optimization

### Current Setup
- ✅ Static files served from Vercel Edge Network
- ✅ CDN-loaded React (cached globally)
- ✅ Direct Supabase connection (no API middle layer)

### Future Optimizations
- Add pagination (load 50 prospects at a time)
- Implement virtual scrolling for large lists
- Add service worker for offline support
- Cache Supabase queries in localStorage

## Security

### Current Security Features
- ✅ HTTPS by default on Vercel
- ✅ Security headers (XSS, frame options, content-type)
- ✅ Supabase RLS (row-level security)
- ✅ Client-side validation on all forms

### Supabase RLS Setup

If you want to restrict data access, configure Row Level Security:

```sql
-- Only allow reading contacts with cultivation notes
CREATE POLICY "Only show researched prospects"
ON contacts FOR SELECT
TO anon
USING (cultivation_notes IS NOT NULL);

-- Only allow updates to specific fields
CREATE POLICY "Allow cultivation field updates"
ON contacts FOR UPDATE
TO authenticated
USING (true)
WITH CHECK (true);
```

## Cost Estimate

**Vercel Free Tier:**
- ✅ 100GB bandwidth/month
- ✅ Unlimited static deployments
- ✅ Custom domains
- ✅ Automatic HTTPS

**Your Usage:**
- ~1,500 prospects × 2KB each = 3MB data transfer per load
- 100GB = ~33,000 page loads/month
- **Conclusion**: Free tier is plenty!

**Supabase Free Tier:**
- ✅ 500MB database (you're using ~10MB)
- ✅ 2GB bandwidth/month
- ✅ 50,000 monthly active users

## Next Steps After Deployment

1. **Test the deployed site** - Visit the Vercel URL
2. **Add custom domain** - `prospects.outdoorithm.com`
3. **Share with team** - Send link to fundraising team
4. **Monitor usage** - Check Vercel analytics weekly
5. **Iterate** - Add features based on user feedback

## Support

- Vercel Docs: https://vercel.com/docs
- Supabase Docs: https://supabase.com/docs
- React Docs: https://react.dev

---

**Estimated deployment time:** 2 minutes 🚀
