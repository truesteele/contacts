"""
Smoke tests for LinkedIn News Scraper
Run with: pytest test_smoke.py -v

These tests verify basic functionality without requiring API keys.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))


class TestConfig:
    """Test configuration loading and validation"""

    def test_config_from_env_empty(self):
        """Config loads with empty env vars"""
        from config import Config
        config = Config.from_env(offline_mode=True)
        assert config.max_stories == 10
        assert config.hours_lookback == 24
        assert config.offline_mode is True

    def test_config_validation_fails_without_keys(self):
        """Config validation fails fast when required keys missing"""
        from config import Config, ConfigurationError

        config = Config(
            openai_api_key="",
            sendgrid_api_key="",
            recipient_email="",
            sender_email="",
        )

        with pytest.raises(ConfigurationError) as exc_info:
            config.validate(require_openai=True, require_sendgrid=True)

        assert "OPENAI_API_KEY" in str(exc_info.value)
        assert "SENDGRID_API_KEY" in str(exc_info.value)

    def test_config_validation_passes_with_keys(self):
        """Config validation passes with valid keys"""
        from config import Config

        config = Config(
            openai_api_key="sk-test-key",
            sendgrid_api_key="SG.test-key",
            recipient_email="test@example.com",
            sender_email="sender@example.com",
        )

        # Should not raise
        config.validate(require_openai=True, require_sendgrid=True)

    def test_config_validation_email_format(self):
        """Config validation catches invalid email format"""
        from config import Config, ConfigurationError

        config = Config(
            openai_api_key="sk-test-key",
            sendgrid_api_key="SG.test-key",
            recipient_email="invalid-email",
            sender_email="sender@example.com",
        )

        with pytest.raises(ConfigurationError) as exc_info:
            config.validate(require_openai=True, require_sendgrid=True)

        assert "not a valid email" in str(exc_info.value)


class TestFetcher:
    """Test RSS fetching functionality"""

    def test_build_google_news_url(self):
        """Google News URL is correctly formatted"""
        from fetcher import build_google_news_url

        url = build_google_news_url("AI ethics")
        assert "news.google.com/rss/search" in url
        assert "AI%20ethics" in url
        assert "hl=en-US" in url
        assert "gl=US" in url

    def test_clean_headline(self):
        """Headlines are cleaned and source extracted"""
        from fetcher import clean_headline

        headline, source = clean_headline("Big Tech Company Makes Announcement - Reuters")
        assert headline == "Big Tech Company Makes Announcement"
        assert source == "Reuters"

        # Test with no source
        headline, source = clean_headline("Just a headline")
        assert headline == "Just a headline"
        assert source == "Unknown"

    def test_clean_summary(self):
        """Summaries are cleaned of HTML and truncated"""
        from fetcher import clean_summary

        # HTML stripped
        result = clean_summary("<p>This is a <b>test</b> summary.</p>")
        assert "<p>" not in result
        assert "<b>" not in result
        assert "test" in result

        # Long text truncated
        long_text = "x" * 600
        result = clean_summary(long_text)
        assert len(result) <= 503  # 500 + "..."

    def test_news_story_hours_old(self):
        """NewsStory calculates hours old correctly"""
        from fetcher import NewsStory
        from datetime import timedelta

        story = NewsStory(
            headline="Test",
            summary="Test summary",
            source="Test Source",
            url="https://example.com",
            published=datetime.now(timezone.utc) - timedelta(hours=5),
            topic_pillar="Test",
            raw_title="Test - Source",
        )

        hours = story.hours_old()
        assert 4.9 < hours < 5.1  # Allow small timing variance


class TestEmailer:
    """Test email formatting"""

    def test_escape_html(self):
        """HTML escaping prevents XSS"""
        from emailer import escape_html

        # Basic escaping
        assert escape_html("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        assert escape_html("Normal text") == "Normal text"
        assert escape_html("") == ""
        assert escape_html(None) == ""

    def test_format_voice_emoji(self):
        """Voice types map to correct emojis"""
        from emailer import format_voice_emoji

        assert format_voice_emoji("Prophet") == "📣"
        assert format_voice_emoji("Builder") == "🏗️"
        assert format_voice_emoji("Teacher") == "📚"
        assert format_voice_emoji("Unknown") == "💡"

    def test_build_html_email(self):
        """HTML email is generated with proper structure"""
        from emailer import build_html_email
        from scorer import ScoredStory
        from fetcher import NewsStory

        story = ScoredStory(
            story=NewsStory(
                headline="Test <script>Headline</script>",  # XSS attempt
                summary="Test summary with <b>HTML</b>",
                source="Test Source",
                url="https://example.com?foo=bar&baz=qux",
                published=datetime.now(timezone.utc),
                topic_pillar="Test",
                raw_title="Test",
            ),
            reach_score=8,
            engagement_score=6,
            recommended_voice="Prophet",
            big_name_anchors=["<script>Meta</script>"],  # XSS attempt
            justin_angle="Test angle <img src=x onerror=alert(1)>",  # XSS attempt
            reasoning="Test",
            combined_score=7.2,
        )

        html = build_html_email([story], datetime.now())

        # Verify structure
        assert "<!DOCTYPE html>" in html
        assert "Daily News Digest" in html

        # Verify XSS is escaped
        assert "<script>" not in html
        assert "&lt;script&gt;" in html  # Escaped version

    def test_build_plain_text_email(self):
        """Plain text email is generated correctly"""
        from emailer import build_plain_text_email
        from scorer import ScoredStory
        from fetcher import NewsStory

        story = ScoredStory(
            story=NewsStory(
                headline="Test Headline",
                summary="Test summary",
                source="Test Source",
                url="https://example.com",
                published=datetime.now(timezone.utc),
                topic_pillar="Test",
                raw_title="Test",
            ),
            reach_score=8,
            engagement_score=6,
            recommended_voice="Prophet",
            big_name_anchors=["Meta"],
            justin_angle="Test angle",
            reasoning="Test",
            combined_score=7.2,
        )

        text = build_plain_text_email([story], datetime.now())

        assert "DAILY NEWS DIGEST" in text
        assert "Test Headline" in text
        assert "Reach: 8/10" in text
        assert "Prophet" in text


class TestScorer:
    """Test scoring data structures"""

    def test_scored_story_to_dict(self):
        """ScoredStory serializes correctly"""
        from scorer import ScoredStory
        from fetcher import NewsStory

        story = ScoredStory(
            story=NewsStory(
                headline="Test",
                summary="Test",
                source="Test",
                url="https://example.com",
                published=datetime.now(timezone.utc),
                topic_pillar="Test",
                raw_title="Test",
            ),
            reach_score=7,
            engagement_score=8,
            recommended_voice="Builder",
            big_name_anchors=["Google"],
            justin_angle="Test angle",
            reasoning="Test reason",
            combined_score=7.4,
        )

        d = story.to_dict()

        assert d["reach_score"] == 7
        assert d["engagement_score"] == 8
        assert d["recommended_voice"] == "Builder"
        assert "Google" in d["big_name_anchors"]
        assert d["headline"] == "Test"


class TestMainOffline:
    """Test main pipeline in offline mode"""

    def test_create_sample_data(self):
        """Sample data is created correctly"""
        from main import create_sample_data

        stories = create_sample_data()

        assert len(stories) >= 3
        assert all(hasattr(s, 'reach_score') for s in stories)
        assert all(hasattr(s, 'story') for s in stories)

    def test_offline_pipeline_runs(self, tmp_path, monkeypatch):
        """Offline pipeline completes without errors"""
        from main import run_offline_pipeline
        import main

        # Redirect output directory to temp
        monkeypatch.setattr(main, '__file__', str(tmp_path / 'main.py'))

        result = run_offline_pipeline()

        assert result is True
        # Check that files were created
        assert (tmp_path / 'output').exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
