"""
RSS News Fetcher
Fetches news from Google News RSS feeds for each topic pillar
"""

import feedparser
import requests
import urllib.parse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import List, Optional
import re
import time
import logging

from config import TOPIC_QUERIES

logger = logging.getLogger(__name__)

# Configure requests session with retries and proper TLS verification
def create_http_session() -> requests.Session:
    """Create a requests session with retry logic and proper TLS"""
    session = requests.Session()

    # Retry strategy: 3 retries with exponential backoff for 429, 500, 502, 503, 504
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,  # 1s, 2s, 4s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Standard browser-like headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (compatible; NewsScraper/1.0)',
        'Accept': 'application/rss+xml, application/xml, text/xml',
    })

    return session

# Global session (reused across requests)
_http_session: Optional[requests.Session] = None

def get_http_session() -> requests.Session:
    """Get or create the HTTP session"""
    global _http_session
    if _http_session is None:
        _http_session = create_http_session()
    return _http_session


@dataclass
class NewsStory:
    """Represents a single news story"""
    headline: str
    summary: str
    source: str
    url: str
    published: datetime
    topic_pillar: str
    raw_title: str  # Original title before cleaning

    def hours_old(self) -> float:
        """Calculate hours since publication"""
        now = datetime.now(timezone.utc)
        if self.published.tzinfo is None:
            self.published = self.published.replace(tzinfo=timezone.utc)
        delta = now - self.published
        return delta.total_seconds() / 3600

    def to_dict(self) -> dict:
        return {
            "headline": self.headline,
            "summary": self.summary,
            "source": self.source,
            "url": self.url,
            "published": self.published.isoformat(),
            "topic_pillar": self.topic_pillar,
            "hours_old": round(self.hours_old(), 1),
        }


def build_google_news_url(query: str) -> str:
    """
    Build Google News RSS URL for a search query
    Uses US English settings for US-centric news
    """
    encoded_query = urllib.parse.quote(query)
    # hl=en-US: English US, gl=US: Geolocation US, ceid=US:en: Edition
    return f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"


def clean_headline(raw_title: str) -> tuple[str, str]:
    """
    Clean Google News headline and extract source
    Google News titles typically end with " - Source Name"

    Returns: (clean_headline, source_name)
    """
    # Split on the last occurrence of " - "
    if " - " in raw_title:
        parts = raw_title.rsplit(" - ", 1)
        headline = parts[0].strip()
        source = parts[1].strip() if len(parts) > 1 else "Unknown"
    else:
        headline = raw_title.strip()
        source = "Unknown"

    return headline, source


def parse_published_date(entry: dict) -> datetime:
    """Parse publication date from RSS entry"""
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    else:
        # Default to now if no date found
        return datetime.now(timezone.utc)


def clean_summary(raw_summary: str) -> str:
    """Clean HTML and truncate summary"""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', raw_summary)
    # Remove extra whitespace
    clean = ' '.join(clean.split())
    # Truncate to reasonable length
    if len(clean) > 500:
        clean = clean[:497] + "..."
    return clean


def fetch_topic_news(topic_pillar: str, queries: List[str], hours_lookback: int = 24) -> List[NewsStory]:
    """
    Fetch news for a single topic pillar

    Args:
        topic_pillar: Name of the topic pillar
        queries: List of search queries for this pillar
        hours_lookback: Only include stories from the last N hours

    Returns:
        List of NewsStory objects
    """
    stories = []
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)

    for query in queries:
        url = build_google_news_url(query)

        try:
            # Fetch with proper TLS verification and retries
            session = get_http_session()
            response = session.get(url, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)

            for entry in feed.entries[:10]:  # Limit per query to avoid overwhelming
                # Parse publication date
                published = parse_published_date(entry)

                # Skip if too old
                if published < cutoff_time:
                    continue

                # Clean headline and extract source
                raw_title = entry.get('title', '')
                headline, source = clean_headline(raw_title)

                # Get summary
                raw_summary = entry.get('summary', entry.get('description', ''))
                summary = clean_summary(raw_summary)

                # Create story object
                story = NewsStory(
                    headline=headline,
                    summary=summary,
                    source=source,
                    url=entry.get('link', ''),
                    published=published,
                    topic_pillar=topic_pillar,
                    raw_title=raw_title,
                )

                stories.append(story)

            # Small delay between requests to be respectful
            time.sleep(0.5)

        except Exception as e:
            print(f"Error fetching {query}: {e}")
            continue

    return stories


def fetch_all_news(hours_lookback: int = 24) -> List[NewsStory]:
    """
    Fetch news from all topic pillars

    Returns:
        List of all NewsStory objects, sorted by recency
    """
    all_stories = []

    for topic_pillar, queries in TOPIC_QUERIES.items():
        print(f"Fetching {topic_pillar}...")
        stories = fetch_topic_news(topic_pillar, queries, hours_lookback)
        all_stories.extend(stories)
        print(f"  Found {len(stories)} stories")

    # Sort by publication date (newest first)
    all_stories.sort(key=lambda s: s.published, reverse=True)

    print(f"\nTotal stories fetched: {len(all_stories)}")
    return all_stories


if __name__ == "__main__":
    # Test the fetcher
    stories = fetch_all_news(hours_lookback=24)

    print("\n" + "="*60)
    print("SAMPLE STORIES")
    print("="*60)

    for story in stories[:5]:
        print(f"\n[{story.topic_pillar}] {story.headline}")
        print(f"  Source: {story.source} | {story.hours_old():.1f}h ago")
        print(f"  {story.summary[:200]}...")
