#!/usr/bin/env python3
"""
LinkedIn News Scraper - Main Entry Point
Fetches news, scores with AI, and sends daily email digest

Usage:
    python main.py                    # Run full pipeline (requires all API keys)
    python main.py --dry-run          # Fetch + score, but don't send email (requires OpenAI)
    python main.py --offline          # Use sample data, no API calls (zero cost)
    python main.py --test-email       # Send test email with sample data (requires SendGrid)
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import Config, ConfigurationError
from fetcher import fetch_all_news, NewsStory
from scorer import process_news, ScoredStory
from emailer import send_email, build_plain_text_email, build_html_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def save_results(stories: list[ScoredStory], output_dir: Path) -> str:
    """Save results to JSON file for debugging/archiving"""
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = output_dir / f"digest_{date_str}.json"

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "story_count": len(stories),
        "stories": [s.to_dict() for s in stories],
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Results saved to {filename}")
    return str(filename)


def create_sample_data() -> list[ScoredStory]:
    """
    Create sample data for offline testing.
    This allows testing the full pipeline without any API calls.
    """
    sample_stories = [
        ScoredStory(
            story=NewsStory(
                headline="Meta Announces End to Workplace DEI Initiatives",
                summary="Meta will discontinue its diversity, equity, and inclusion programs affecting hiring and supplier diversity, joining other tech companies in scaling back such efforts amid political pressure.",
                source="New York Times",
                url="https://nytimes.com/example",
                published=datetime.now(timezone.utc),
                topic_pillar="Social Commentary",
                raw_title="Meta Announces End to DEI - NYT",
            ),
            reach_score=9,
            engagement_score=5,
            recommended_voice="Prophet",
            big_name_anchors=["Meta", "Zuckerberg"],
            justin_angle="This continues the corporate retreat pattern you identified in your viral Meta DEI post. Your unique angle: you've seen this from the inside at Google.",
            reasoning="Breaking news, major anchor, moral tension, national conversation",
            combined_score=7.4,
        ),
        ScoredStory(
            story=NewsStory(
                headline="OpenAI Foundation Launches $500M Initiative for AI Education",
                summary="The newly formed OpenAI Foundation announced a major philanthropic push to bring AI literacy to underserved schools across America.",
                source="TechCrunch",
                url="https://techcrunch.com/example",
                published=datetime.now(timezone.utc),
                topic_pillar="AI Building",
                raw_title="OpenAI Foundation Launches Initiative - TC",
            ),
            reach_score=8,
            engagement_score=6,
            recommended_voice="Prophet",
            big_name_anchors=["OpenAI"],
            justin_angle="Follow up to your OpenAI Foundation critique. Question whether this is genuine impact or 'redemptive philanthropy' after extraction.",
            reasoning="Big anchor, philanthropy angle, connects to your prior content",
            combined_score=7.2,
        ),
        ScoredStory(
            story=NewsStory(
                headline="Black Outdoor Leaders Form National Coalition for Public Lands Access",
                summary="More than 50 Black-led outdoor organizations announced a new coalition to advocate for equitable access to national parks and public lands.",
                source="Outside Magazine",
                url="https://outside.com/example",
                published=datetime.now(timezone.utc),
                topic_pillar="Outdoor",
                raw_title="Black Outdoor Leaders Coalition - Outside",
            ),
            reach_score=5,
            engagement_score=9,
            recommended_voice="Builder",
            big_name_anchors=[],
            justin_angle="Direct connection to Outdoorithm Collective's mission. Share your story of building in this space and name specific leaders you've worked with.",
            reasoning="Deep personal connection, community angle, values alignment",
            combined_score=6.6,
        ),
        ScoredStory(
            story=NewsStory(
                headline="Harvard Receives Record $3B Gift for Financial Aid",
                summary="An anonymous donor has given Harvard University its largest gift ever, earmarked entirely for expanding financial aid to low-income students.",
                source="Chronicle of Higher Education",
                url="https://chronicle.com/example",
                published=datetime.now(timezone.utc),
                topic_pillar="Education",
                raw_title="Harvard Gift - Chronicle",
            ),
            reach_score=7,
            engagement_score=7,
            recommended_voice="Prophet",
            big_name_anchors=["Harvard"],
            justin_angle="Your Harvard connection + philanthropy expertise. Question: does this address root causes or just redistribute access to elite institutions?",
            reasoning="Big anchor (Harvard), philanthropy angle, your alma mater",
            combined_score=7.0,
        ),
    ]
    return sample_stories


def run_offline_pipeline() -> bool:
    """
    Run pipeline with sample data - no API calls, zero cost.
    Useful for testing email formatting and workflow.
    """
    print("=" * 60)
    print("🧪 LinkedIn News Scraper - OFFLINE MODE")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("   Using sample data (no API calls)")
    print("=" * 60)

    scored_stories = create_sample_data()
    print(f"\n✅ Loaded {len(scored_stories)} sample stories")

    # Save results
    output_dir = Path(__file__).parent / "output"
    save_results(scored_stories, output_dir)

    # Print summary
    print("\n📊 SAMPLE STORIES:")
    print("-" * 60)
    for i, s in enumerate(scored_stories, 1):
        emoji = {"Prophet": "📣", "Builder": "🏗️", "Teacher": "📚"}.get(s.recommended_voice, "💡")
        print(f"{i}. [{s.reach_score}/{s.engagement_score}] {emoji} {s.story.headline[:60]}...")

    # Show email preview
    print("\n📧 EMAIL PREVIEW (plain text):")
    print("-" * 60)
    print(build_plain_text_email(scored_stories, datetime.now()))

    # Also save HTML for inspection
    html_file = output_dir / "preview.html"
    with open(html_file, "w") as f:
        f.write(build_html_email(scored_stories, datetime.now()))
    print(f"\n✅ HTML preview saved to {html_file}")

    return True


def run_pipeline(config: Config, dry_run: bool = False) -> bool:
    """
    Run the full news scraping pipeline

    Args:
        config: Configuration object
        dry_run: If True, don't send email (but still calls OpenAI)

    Returns:
        True if successful
    """
    print("=" * 60)
    print("🚀 LinkedIn News Scraper")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if dry_run:
        print("   Mode: DRY RUN (no email)")
    print("=" * 60)

    # Step 1: Fetch news
    print("\n📡 FETCHING NEWS...")
    try:
        stories = fetch_all_news(hours_lookback=config.hours_lookback)
    except Exception as e:
        logger.error(f"Failed to fetch news: {e}")
        print(f"❌ Failed to fetch news: {e}")
        return False

    if not stories:
        print(f"❌ No stories found in the last {config.hours_lookback} hours")
        return False

    print(f"✅ Found {len(stories)} stories")

    # Step 2: Process with AI (dedupe + score)
    print("\n🤖 PROCESSING WITH AI...")
    try:
        scored_stories = process_news(
            stories,
            api_key=config.openai_api_key,
            max_stories=config.max_stories,
        )
    except Exception as e:
        logger.error(f"Failed to score stories: {e}")
        print(f"❌ Failed to score stories: {e}")
        return False

    if not scored_stories:
        print("❌ No stories passed scoring!")
        return False

    print(f"✅ Selected top {len(scored_stories)} stories")

    # Step 3: Save results
    output_dir = Path(__file__).parent / "output"
    save_results(scored_stories, output_dir)

    # Step 4: Print summary
    print("\n📊 TOP STORIES:")
    print("-" * 60)
    for i, s in enumerate(scored_stories, 1):
        emoji = {"Prophet": "📣", "Builder": "🏗️", "Teacher": "📚"}.get(s.recommended_voice, "💡")
        print(f"{i}. [{s.reach_score}/{s.engagement_score}] {emoji} {s.story.headline[:60]}...")

    # Step 5: Send email (unless dry run)
    if dry_run:
        print("\n📧 DRY RUN - Email not sent")
        print("\nPlain text preview:")
        print(build_plain_text_email(scored_stories, datetime.now()))
        return True

    print(f"\n📧 SENDING EMAIL to {config.recipient_email}...")
    try:
        success = send_email(
            scored_stories,
            recipient_email=config.recipient_email,
            sender_email=config.sender_email,
            api_key=config.sendgrid_api_key,
        )
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        print(f"❌ Failed to send email: {e}")
        return False

    if success:
        print("✅ Email sent successfully!")
    else:
        print("❌ Failed to send email")

    return success


def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn News Scraper - Daily digest of news for your content strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --offline          # Test with sample data, no API keys needed
  python main.py --dry-run          # Fetch + score news, but don't send email
  python main.py                    # Full run: fetch, score, and send email
  python main.py --test-email       # Send test email with sample stories
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and score news, but don't send email (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use sample data only - no API calls, zero cost (for testing)",
    )
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Send test email with sample data (requires SENDGRID_API_KEY)",
    )
    args = parser.parse_args()

    # Offline mode - no config needed
    if args.offline:
        success = run_offline_pipeline()
        sys.exit(0 if success else 1)

    # Load and validate config based on mode
    try:
        config = Config.from_env()

        if args.test_email:
            # Only need SendGrid for test email
            config.validate(require_openai=False, require_sendgrid=True)
        elif args.dry_run:
            # Need OpenAI but not SendGrid for dry run
            config.validate(require_openai=True, require_sendgrid=False)
        else:
            # Full run needs everything
            config.validate(require_openai=True, require_sendgrid=True)

    except ConfigurationError as e:
        print(f"\n❌ {e}")
        print("\nTip: Use --offline to test without any API keys")
        sys.exit(1)

    # Run test email
    if args.test_email:
        print("📧 Sending test email with sample data...")
        test_stories = create_sample_data()
        try:
            success = send_email(
                test_stories,
                recipient_email=config.recipient_email,
                sender_email=config.sender_email,
                api_key=config.sendgrid_api_key,
            )
            if success:
                print(f"✅ Test email sent to {config.recipient_email}")
            else:
                print("❌ Failed to send test email")
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            sys.exit(1)

    # Run full or dry-run pipeline
    success = run_pipeline(config, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
