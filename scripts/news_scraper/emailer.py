"""
SendGrid Email Formatter and Sender
Delivers daily news digest in a clean, scannable format
"""

import os
import html
import logging
import time
from datetime import datetime
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scorer import ScoredStory

logger = logging.getLogger(__name__)


def create_sendgrid_session() -> requests.Session:
    """Create a requests session with retry logic for SendGrid"""
    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)

    return session


def escape_html(text: str) -> str:
    """
    Escape HTML special characters to prevent XSS injection.
    All user-sourced content (headlines, summaries, URLs, angles) must be escaped.
    """
    if not text:
        return ""
    return html.escape(str(text), quote=True)


def format_voice_emoji(voice: str) -> str:
    """Get emoji for voice type"""
    return {
        "Prophet": "📣",
        "Builder": "🏗️",
        "Teacher": "📚",
    }.get(voice, "💡")


def format_score_bar(score: int, max_score: int = 10) -> str:
    """Create a visual score bar"""
    filled = "█" * score
    empty = "░" * (max_score - score)
    return f"{filled}{empty}"


def build_html_email(stories: List[ScoredStory], date: datetime) -> str:
    """
    Build a beautiful HTML email with the news digest

    Args:
        stories: List of scored stories
        date: Date for the digest

    Returns:
        HTML string for the email body
    """
    date_str = date.strftime("%A, %B %d, %Y")

    # Separate into reach vs engagement opportunities
    high_reach = [s for s in stories if s.reach_score >= 7]
    high_engagement = [s for s in stories if s.engagement_score >= 7 and s not in high_reach]
    other = [s for s in stories if s not in high_reach and s not in high_engagement]

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily News Digest</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            color: #1e40af;
            font-size: 24px;
        }}
        .header .date {{
            color: #6b7280;
            font-size: 14px;
            margin-top: 5px;
        }}
        .header .count {{
            background: #dbeafe;
            color: #1e40af;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: inline-block;
            margin-top: 10px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .section-title.reach {{
            color: #dc2626;
        }}
        .section-title.engagement {{
            color: #059669;
        }}
        .story {{
            margin-bottom: 25px;
            padding: 15px;
            background: #fafafa;
            border-radius: 6px;
            border-left: 4px solid #e5e7eb;
        }}
        .story.high-reach {{
            border-left-color: #dc2626;
        }}
        .story.high-engagement {{
            border-left-color: #059669;
        }}
        .story-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }}
        .story-meta {{
            font-size: 11px;
            color: #6b7280;
        }}
        .story-meta .source {{
            font-weight: 600;
        }}
        .story-meta .time {{
            color: #9ca3af;
        }}
        .story-title {{
            font-size: 15px;
            font-weight: 600;
            color: #111827;
            margin: 8px 0;
            line-height: 1.4;
        }}
        .story-title a {{
            color: #111827;
            text-decoration: none;
        }}
        .story-title a:hover {{
            color: #2563eb;
        }}
        .story-summary {{
            font-size: 13px;
            color: #4b5563;
            margin: 10px 0;
        }}
        .scores {{
            display: flex;
            gap: 20px;
            margin: 12px 0;
            font-size: 12px;
        }}
        .score {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .score-label {{
            color: #6b7280;
            font-weight: 500;
        }}
        .score-value {{
            font-weight: 700;
            color: #111827;
        }}
        .score-value.high {{
            color: #059669;
        }}
        .voice-tag {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .voice-tag.prophet {{
            background: #fef3c7;
            color: #92400e;
        }}
        .voice-tag.builder {{
            background: #dbeafe;
            color: #1e40af;
        }}
        .voice-tag.teacher {{
            background: #d1fae5;
            color: #065f46;
        }}
        .angle {{
            margin-top: 12px;
            padding: 10px;
            background: #eff6ff;
            border-radius: 4px;
            font-size: 12px;
            color: #1e40af;
        }}
        .angle-label {{
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .anchors {{
            margin-top: 8px;
            font-size: 11px;
        }}
        .anchors .label {{
            color: #6b7280;
        }}
        .anchors .names {{
            color: #111827;
            font-weight: 500;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            font-size: 11px;
            color: #9ca3af;
            text-align: center;
        }}
        .quick-stats {{
            display: flex;
            gap: 15px;
            margin: 15px 0;
            flex-wrap: wrap;
        }}
        .stat {{
            background: #f3f4f6;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
        }}
        .stat-value {{
            font-weight: 700;
            color: #111827;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📰 Daily News Digest</h1>
            <div class="date">{date_str}</div>
            <div class="count">{len(stories)} stories curated for your LinkedIn</div>
        </div>

        <div class="quick-stats">
            <div class="stat">🔥 High Reach: <span class="stat-value">{len(high_reach)}</span></div>
            <div class="stat">💬 High Engagement: <span class="stat-value">{len(high_engagement)}</span></div>
            <div class="stat">📣 Prophet: <span class="stat-value">{len([s for s in stories if s.recommended_voice == 'Prophet'])}</span></div>
            <div class="stat">🏗️ Builder: <span class="stat-value">{len([s for s in stories if s.recommended_voice == 'Builder'])}</span></div>
        </div>
"""

    def render_story(story: ScoredStory, css_class: str = "") -> str:
        voice_class = story.recommended_voice.lower()

        # Escape all user-sourced content to prevent XSS
        safe_source = escape_html(story.story.source)
        safe_topic = escape_html(story.story.topic_pillar)
        safe_url = escape_html(story.story.url)
        safe_headline = escape_html(story.story.headline)
        safe_summary = escape_html(story.story.summary[:300])
        safe_angle = escape_html(story.justin_angle)
        safe_anchors = [escape_html(a) for a in story.big_name_anchors]

        anchors_html = ""
        if safe_anchors:
            anchors_html = f"""
            <div class="anchors">
                <span class="label">Anchors:</span>
                <span class="names">{', '.join(safe_anchors)}</span>
            </div>
            """

        reach_class = "high" if story.reach_score >= 7 else ""
        eng_class = "high" if story.engagement_score >= 7 else ""
        ellipsis = "..." if len(story.story.summary) > 300 else ""

        return f"""
        <div class="story {css_class}">
            <div class="story-meta">
                <span class="source">{safe_source}</span>
                <span class="time"> · {story.story.hours_old():.0f}h ago</span>
                <span> · {safe_topic}</span>
            </div>
            <div class="story-title">
                <a href="{safe_url}" target="_blank">{safe_headline}</a>
            </div>
            <div class="story-summary">{safe_summary}{ellipsis}</div>
            <div class="scores">
                <div class="score">
                    <span class="score-label">Reach:</span>
                    <span class="score-value {reach_class}">{story.reach_score}/10</span>
                </div>
                <div class="score">
                    <span class="score-label">Engagement:</span>
                    <span class="score-value {eng_class}">{story.engagement_score}/10</span>
                </div>
                <span class="voice-tag {voice_class}">{format_voice_emoji(story.recommended_voice)} {story.recommended_voice}</span>
            </div>
            {anchors_html}
            <div class="angle">
                <div class="angle-label">💡 Your Angle:</div>
                {safe_angle}
            </div>
        </div>
        """

    # High Reach Section
    if high_reach:
        html += """
        <div class="section">
            <div class="section-title reach">🔥 HIGH REACH OPPORTUNITIES</div>
        """
        for story in high_reach:
            html += render_story(story, "high-reach")
        html += "</div>"

    # High Engagement Section
    if high_engagement:
        html += """
        <div class="section">
            <div class="section-title engagement">💬 HIGH ENGAGEMENT OPPORTUNITIES</div>
        """
        for story in high_engagement:
            html += render_story(story, "high-engagement")
        html += "</div>"

    # Other Stories
    if other:
        html += """
        <div class="section">
            <div class="section-title">📋 OTHER NOTABLE STORIES</div>
        """
        for story in other:
            html += render_story(story)
        html += "</div>"

    html += f"""
        <div class="footer">
            Generated by your LinkedIn News Scraper<br>
            Based on your Performance Framework | Pillars: Social Commentary, AI, Philanthropy, Education, Outdoor
        </div>
    </div>
</body>
</html>
"""

    return html


def build_plain_text_email(stories: List[ScoredStory], date: datetime) -> str:
    """Build plain text version of the email"""
    date_str = date.strftime("%A, %B %d, %Y")

    lines = [
        "=" * 60,
        f"📰 DAILY NEWS DIGEST | {date_str}",
        f"   {len(stories)} stories curated for your LinkedIn",
        "=" * 60,
        "",
    ]

    for i, story in enumerate(stories, 1):
        emoji = format_voice_emoji(story.recommended_voice)
        lines.extend([
            f"\n{'─' * 60}",
            f"#{i} [{story.recommended_voice} {emoji}] {story.story.topic_pillar}",
            f"",
            f"📰 {story.story.headline}",
            f"   Source: {story.story.source} | {story.story.hours_old():.0f}h ago",
            f"",
            f"   {story.story.summary[:250]}...",
            f"",
            f"   Reach: {story.reach_score}/10 | Engagement: {story.engagement_score}/10",
        ])

        if story.big_name_anchors:
            lines.append(f"   Anchors: {', '.join(story.big_name_anchors)}")

        lines.extend([
            f"",
            f"   💡 Your Angle: {story.justin_angle}",
            f"",
            f"   🔗 {story.story.url}",
        ])

    lines.extend([
        "",
        "=" * 60,
        "Generated by your LinkedIn News Scraper",
        "Based on your Performance Framework",
        "=" * 60,
    ])

    return "\n".join(lines)


def send_email(
    stories: List[ScoredStory],
    recipient_email: str,
    sender_email: str,
    api_key: Optional[str] = None,
) -> bool:
    """
    Send the news digest via SendGrid REST API (using requests for proper TLS)

    Args:
        stories: List of scored stories
        recipient_email: Where to send the digest
        sender_email: Verified sender email
        api_key: SendGrid API key

    Returns:
        True if successful, False otherwise
    """
    api_key = api_key or os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        logger.error("SendGrid API key required")
        print("ERROR: SendGrid API key required")
        return False

    date = datetime.now()
    date_str = date.strftime("%b %d")

    # Build email content
    html_content = build_html_email(stories, date)
    plain_content = build_plain_text_email(stories, date)

    # High reach count for subject line
    high_reach_count = len([s for s in stories if s.reach_score >= 7])

    subject = f"📰 LinkedIn News Digest ({date_str})"
    if high_reach_count > 0:
        subject = f"🔥 {high_reach_count} High-Reach Stories | LinkedIn News ({date_str})"

    # Build SendGrid v3 API payload
    payload = {
        "personalizations": [
            {
                "to": [{"email": recipient_email}]
            }
        ],
        "from": {
            "email": sender_email,
            "name": "News Scraper"
        },
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": plain_content},
            {"type": "text/html", "value": html_content}
        ]
    }

    # Use requests for proper TLS handling
    session = create_sendgrid_session()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = session.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 202:
            logger.info(f"Email sent! Status: {response.status_code}")
            print(f"Email sent! Status: {response.status_code}")
            return True
        else:
            error_body = response.text
            logger.error(f"SendGrid returned {response.status_code}: {error_body}")
            print(f"Email error: SendGrid returned {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"SendGrid request failed: {e}")
        print(f"Email error: {e}")
        return False


if __name__ == "__main__":
    # Test email formatting
    from fetcher import NewsStory
    from datetime import timezone

    # Create sample data
    sample_story = NewsStory(
        headline="Meta Ends DEI Programs Citing New Corporate Strategy",
        summary="Meta announced today it will end its diversity, equity and inclusion programs...",
        source="New York Times",
        url="https://example.com",
        published=datetime.now(timezone.utc),
        topic_pillar="Social Commentary",
        raw_title="Meta Ends DEI Programs - NYT",
    )

    sample_scored = ScoredStory(
        story=sample_story,
        reach_score=9,
        engagement_score=5,
        recommended_voice="Prophet",
        big_name_anchors=["Meta", "Zuckerberg"],
        justin_angle="Connect to your Meta DEI rollback post - this is the continuation of corporate retreat you predicted.",
        reasoning="Breaking news with major tech anchor, moral tension.",
        combined_score=7.4,
    )

    # Print sample HTML
    html = build_html_email([sample_scored], datetime.now())
    print("HTML email generated successfully")
    print(f"Length: {len(html)} characters")

    # Print plain text
    plain = build_plain_text_email([sample_scored], datetime.now())
    print("\n" + plain)
