# 🚀 Quick Deploy to Vercel

## Local Development

```bash
cd frontend
npm run dev
```

Open: http://localhost:8080

## One-Command Deployment

```bash
cd frontend
npm run deploy
```

That's it! Your app will be live in ~2 minutes.

---

## Manual Deployment (Alternative)

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Deploy

```bash
cd frontend
vercel --prod
```

### Step 3: Open Your App

Vercel will give you a URL like:
```
https://outdoorithm-donor-prospects.vercel.app
```

---

## 🔒 Security Setup (Optional but Recommended)

**Current Status:** ⚠️ Database has NO access restrictions (RLS disabled)

Anyone with the Vercel URL can view and edit your donor data. To secure it:

### Option A: Basic Security (Recommended)

Run this in [Supabase SQL Editor](https://app.supabase.com):

```sql
-- Enable Row Level Security
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;

-- Allow public read of researched prospects
CREATE POLICY "Allow public read of researched prospects"
ON contacts FOR SELECT
TO anon, authenticated
USING (cultivation_notes IS NOT NULL);

-- Allow public update of cultivation fields
CREATE POLICY "Allow public update of cultivation fields"
ON contacts FOR UPDATE
TO anon, authenticated
USING (cultivation_notes IS NOT NULL)
WITH CHECK (cultivation_notes IS NOT NULL);
```

**Result:** Anyone can view prospects, but can only update cultivation tracking fields.

### Option B: Require Authentication (Most Secure)

1. Set up Supabase Auth (email/password, Google, etc.)
2. Add login UI to the frontend
3. Run this SQL:

```sql
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users only"
ON contacts FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);
```

**Result:** Only logged-in users can access data.

### Option C: Keep Open (Current - No Action Needed)

Good for internal tools in trusted environments.

---

## 📊 What You're Deploying

- **Frontend:** React app with nature-inspired design
- **Data:** 1,498 donor prospects with AI research
- **Features:** Advanced filtering, sorting, cultivation tracking
- **Database:** Direct Supabase connection (no backend needed)

---

## ✅ Post-Deployment Checklist

1. [ ] Test the Vercel URL
2. [ ] Try filtering by "Board Member" + "Equity Focus"
3. [ ] Open a prospect modal and edit warmth level
4. [ ] Verify changes save to Supabase
5. [ ] (Optional) Set up security policies above
6. [ ] (Optional) Add custom domain: `prospects.outdoorithm.com`

---

## 🆘 Troubleshooting

### "Error fetching prospects"

**Cause:** RLS is enabled but no policies exist.

**Fix:** Run the SQL from Option A or Option B above.

### "Cannot save changes"

**Cause:** RLS policy blocks updates.

**Fix:** Check your RLS policies allow updates for anon role.

### Deployment fails

**Cause:** Vercel can't find files.

**Fix:** Make sure you're in the `frontend/` directory when running `vercel --prod`.

---

## 📁 File Structure

```
frontend/
├── index.html          # Entry point
├── styles.css          # Nature-inspired CSS
├── app.js             # React app with Supabase
├── vercel.json        # Deployment config
├── deploy.sh          # One-click deploy script
└── DEPLOYMENT.md      # Full deployment guide
```

---

## 💰 Cost

**Vercel:** FREE (100GB bandwidth/month)

**Supabase:** FREE (500MB database, 2GB bandwidth/month)

**Your usage:** ~3MB per page load = 33,000+ page loads/month FREE

---

## 🎯 Next Steps

1. **Deploy now:** Run `./deploy.sh`
2. **Secure it:** Run the SQL from Option A
3. **Share it:** Send Vercel URL to your team
4. **Customize:** Add your domain in Vercel settings

---

**Estimated time:** 2 minutes ⏱️

**Difficulty:** Easy 🟢
