# LinkedIn News Scraper

Daily news scraper that curates 8-10 stories aligned with your LinkedIn content strategy, scores them using AI, and delivers a digest to your inbox.

## Features

- **RSS Fetching**: Pulls from Google News RSS for 5 topic pillars (Social Commentary, AI Building, Philanthropy, Education, Outdoor)
- **AI-Powered Scoring**: Uses GPT-4o-mini to deduplicate stories and score for Reach (0-10) and Engagement (0-10)
- **Voice Recommendations**: Suggests Prophet, Builder, or Teacher voice based on your framework
- **Personalized Angles**: AI suggests how YOU should approach each story based on your experience
- **Beautiful Email**: HTML digest with sections for high-reach vs high-engagement opportunities
- **Security**: Proper TLS verification, HTML escaping to prevent XSS, fail-fast config validation
- **Reliability**: Retry with exponential backoff for all API calls, comprehensive smoke tests

## Quick Start

### 1. Install Dependencies

```bash
cd scripts/news_scraper
pip install -r requirements.txt
```

### 2. Test Offline (No API Keys Needed)

```bash
# Test the full pipeline with sample data - zero cost
python main.py --offline
```

This generates a preview of the email digest with sample stories, perfect for testing.

### 3. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required variables:
- `OPENAI_API_KEY` - Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- `SENDGRID_API_KEY` - Get from [SendGrid](https://app.sendgrid.com/settings/api_keys)
- `RECIPIENT_EMAIL` - Your email address
- `SENDER_EMAIL` - Must be [verified in SendGrid](https://docs.sendgrid.com/ui/sending-email/sender-verification)

### 4. Test with Real Data

```bash
# Fetch real news + score with AI, but don't send email (requires OPENAI_API_KEY)
python main.py --dry-run

# Send test email with sample data (requires SENDGRID_API_KEY)
python main.py --test-email

# Full run: fetch, score, and send email (requires all keys)
python main.py
```

## GitHub Actions Setup

The scraper runs automatically at 7am Pacific daily via GitHub Actions.

### Add Repository Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:
- `OPENAI_API_KEY`
- `SENDGRID_API_KEY`
- `RECIPIENT_EMAIL`
- `SENDER_EMAIL`

### Manual Trigger

You can also trigger manually:
1. Go to Actions → "Daily News Digest"
2. Click "Run workflow"
3. Optionally check "dry_run" to test without email

## Architecture

```
news_scraper/
├── config.py      # Configuration, prompts, constants
├── fetcher.py     # Google News RSS fetching
├── scorer.py      # OpenAI-powered scoring & dedup
├── emailer.py     # SendGrid email formatting
├── main.py        # Main orchestration
├── requirements.txt
└── output/        # Daily JSON archives
```

## Scoring System (Based on Your Framework)

### Reach Score (0-10)
- +2 Breaking news (< 6 hours old)
- +2 Big-name anchor in headline (Meta, Google, OpenAI, Harvard...)
- +2 Moral tension/controversy
- +2 Part of broader national conversation
- +2 Social Commentary pillar

### Engagement Score (0-10)
- +2 Connects to your experience (Google, philanthropy, Oakland, camping...)
- +2 Human interest angle (families, students, communities)
- +2 Values alignment (equity, access, justice, belonging)
- +2 Story/origin potential
- +2 Could prompt genuine questions

### Voice Recommendations
- **Prophet 📣**: Reach ≥7 + big anchor → timely commentary, moral questioning
- **Builder 🏗️**: Engagement ≥7 + personal connection → photo + origin story
- **Teacher 📚**: Framework opportunity → structured takeaways

## Costs

- **OpenAI**: ~$0.01-0.03 per run (GPT-4o-mini, ~30 API calls)
- **SendGrid**: Free tier covers 100 emails/day
- **GitHub Actions**: Free for public repos, 2000 mins/month for private

## Customization

### Add/Remove Topics

Edit `TOPIC_QUERIES` in `config.py`:

```python
TOPIC_QUERIES = {
    "Social Commentary": [...],
    "AI Building": [...],
    # Add your own pillar
    "Climate Tech": ["climate tech funding", "clean energy startup"],
}
```

### Adjust Big-Name Anchors

Edit `BIG_NAME_ANCHORS` in `config.py` to add companies/people that boost reach for your audience.

### Change Schedule

Edit `.github/workflows/news-scraper.yml`:

```yaml
schedule:
  - cron: '0 15 * * *'  # Currently 7am PST
  # Change to run at 6am PST:
  - cron: '0 14 * * *'
```

## Troubleshooting

### No stories found
- Google News RSS may be rate-limiting. Wait and retry.
- Check if queries return results manually: `https://news.google.com/rss/search?q=YOUR+QUERY`

### Email not received
- Check SendGrid sender verification
- Check spam folder
- Verify `SENDER_EMAIL` matches a verified sender

### OpenAI errors
- Check API key is valid
- Check you have credits/quota
- Model `gpt-4o-mini` requires API access (not ChatGPT Plus)

## Sample Output

```
📰 DAILY NEWS DIGEST | December 15, 2025
   10 stories curated for your LinkedIn

🔥 HIGH REACH OPPORTUNITIES

#1 [Prophet 📣] Social Commentary
   Meta Ends Workplace DEI Initiatives
   Reach: 9/10 | Engagement: 5/10
   Anchors: Meta, Zuckerberg
   💡 Your Angle: Continue corporate retreat theme from your viral post...

💬 HIGH ENGAGEMENT OPPORTUNITIES

#2 [Builder 🏗️] Outdoor
   Black Outdoor Leaders Form National Coalition
   Reach: 5/10 | Engagement: 9/10
   💡 Your Angle: Direct Outdoorithm Collective connection...
```
