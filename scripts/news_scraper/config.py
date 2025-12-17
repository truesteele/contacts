"""
Configuration for LinkedIn News Scraper
Based on Justin Steele's LinkedIn Performance Framework
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

# Load .env file from the script directory
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# =============================================================================
# TOPIC PILLARS & RSS QUERIES
# =============================================================================
# Aligned with your LinkedIn content strategy pillars

TOPIC_QUERIES: Dict[str, List[str]] = {
    "Social Commentary": [
        "DEI program corporate",
        "tech ethics controversy",
        "corporate social responsibility",
        "diversity inclusion workplace",
    ],
    "AI Building": [
        "OpenAI announcement",
        "Anthropic AI",
        "Google AI DeepMind",
        "AI startup funding",
        "AI foundation philanthropy",
    ],
    "Philanthropy": [
        "philanthropy foundation grant",
        "nonprofit funding announcement",
        "corporate giving program",
        "MacKenzie Scott donation",
    ],
    "Education": [
        "higher education DEI policy",
        "Harvard university news",
        "college funding cuts",
        "education equity access",
    ],
    "Outdoor": [
        "public lands access policy",
        "national parks equity",
        "outdoor recreation diversity",
        "conservation funding",
    ],
}

# =============================================================================
# BIG-NAME ANCHORS (3.3x Reach Multiplier in your data)
# =============================================================================

BIG_NAME_ANCHORS: List[str] = [
    # Tech Giants
    "Meta", "Facebook", "Google", "Alphabet", "OpenAI", "Anthropic",
    "Microsoft", "Amazon", "Apple", "Tesla", "Nvidia",
    # Tech Leaders
    "Zuckerberg", "Altman", "Pichai", "Musk", "Nadella", "Bezos",
    "Dario Amodei", "Sam Altman",
    # Universities (from your posts)
    "Harvard", "UVA", "Stanford", "Yale", "Princeton", "MIT", "Berkeley",
    # Major Foundations
    "Ford Foundation", "Gates Foundation", "MacKenzie Scott",
    "Rockefeller", "Bloomberg Philanthropies", "Chan Zuckerberg",
    # Government/Institutions
    "Congress", "Supreme Court", "DOJ", "White House", "Department of Education",
    "EEOC", "Federal",
    # Outdoor/REI (your domain)
    "REI", "Patagonia", "National Park Service", "BLM",
]

# =============================================================================
# YOUR PERSONAL DOMAINS (for engagement scoring)
# =============================================================================

PERSONAL_DOMAINS: List[str] = [
    # Direct experience
    "Google", "Google.org", "philanthropy", "grantmaking",
    "Oakland", "Bay Area", "California",
    "camping", "outdoor", "public lands", "redwoods",
    "nonprofit", "social enterprise",
    # Education connections
    "Harvard", "UVA", "business school",
    # Current work
    "AI", "startup", "founder", "CEO",
    "Kindora", "Outdoorithm",
]

# =============================================================================
# SIGNAL KEYWORDS
# =============================================================================

TENSION_SIGNALS: List[str] = [
    "ends", "eliminates", "cuts", "rollback", "reverses",
    "attacks", "under fire", "backlash", "controversy",
    "lawsuit", "investigation", "criticized", "faces pressure",
    "abandons", "retreats", "walks back", "scales back",
]

HUMAN_INTEREST_SIGNALS: List[str] = [
    "family", "families", "student", "students", "youth",
    "community", "communities", "worker", "workers",
    "founder", "teacher", "children", "kids",
    "first-generation", "underrepresented", "underserved",
]

VALUES_SIGNALS: List[str] = [
    "equity", "access", "justice", "inclusion", "belonging",
    "healing", "empowerment", "representation", "diversity",
    "opportunity", "mobility", "fairness",
]

# =============================================================================
# MAJOR NEWS SOURCES (quality signal)
# =============================================================================

MAJOR_SOURCES: List[str] = [
    "New York Times", "NYT", "Washington Post", "Wall Street Journal", "WSJ",
    "Reuters", "Associated Press", "AP News", "Bloomberg",
    "NPR", "PBS", "BBC", "The Guardian",
    "TechCrunch", "Wired", "The Verge", "Ars Technica",
    "Chronicle of Philanthropy", "Inside Philanthropy",
    "Chronicle of Higher Education", "Inside Higher Ed",
    "Outside Magazine", "High Country News",
]

# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================

class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid"""
    pass


@dataclass
class Config:
    openai_api_key: str
    sendgrid_api_key: str
    recipient_email: str
    sender_email: str
    max_stories: int = 10
    hours_lookback: int = 24
    offline_mode: bool = False  # True = skip all API calls, use sample data

    def validate(self, require_openai: bool = True, require_sendgrid: bool = True) -> None:
        """
        Validate configuration and fail fast with clear errors.

        Args:
            require_openai: Whether OpenAI key is required (False for offline mode)
            require_sendgrid: Whether SendGrid key is required (False for dry-run)

        Raises:
            ConfigurationError: If required configuration is missing
        """
        errors = []

        if require_openai and not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required (get one at https://platform.openai.com/api-keys)")

        if require_sendgrid and not self.sendgrid_api_key:
            errors.append("SENDGRID_API_KEY is required (get one at https://app.sendgrid.com/settings/api_keys)")

        if require_sendgrid and not self.recipient_email:
            errors.append("RECIPIENT_EMAIL is required")

        if require_sendgrid and not self.sender_email:
            errors.append("SENDER_EMAIL is required (must be verified in SendGrid)")

        # Validate email format (basic check)
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if self.recipient_email and not re.match(email_pattern, self.recipient_email):
            errors.append(f"RECIPIENT_EMAIL '{self.recipient_email}' is not a valid email address")
        if self.sender_email and not re.match(email_pattern, self.sender_email):
            errors.append(f"SENDER_EMAIL '{self.sender_email}' is not a valid email address")

        if errors:
            raise ConfigurationError("\n".join([
                "Configuration errors:",
                *[f"  - {e}" for e in errors],
                "",
                "Set these as environment variables or in a .env file.",
            ]))

    @classmethod
    def from_env(cls, offline_mode: bool = False) -> "Config":
        """
        Load configuration from environment variables.

        Args:
            offline_mode: If True, API keys are not required

        Returns:
            Config object (not yet validated - call validate() to check)
        """
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            sendgrid_api_key=os.environ.get("SENDGRID_API_KEY", ""),
            recipient_email=os.environ.get("RECIPIENT_EMAIL", ""),
            sender_email=os.environ.get("SENDER_EMAIL", ""),
            max_stories=int(os.environ.get("MAX_STORIES", "10")),
            hours_lookback=int(os.environ.get("HOURS_LOOKBACK", "24")),
            offline_mode=offline_mode,
        )

# =============================================================================
# OPENAI PROMPTS
# =============================================================================

SCORING_SYSTEM_PROMPT = """You are an AI assistant helping curate news for a LinkedIn content creator.

CREATOR PROFILE:
- Justin Steele: Former Google.org director ($700M+ in philanthropy), now founder of Kindora (AI for nonprofits) and Outdoorithm Collective (outdoor equity nonprofit)
- Harvard MBA, UVA engineering degree
- Based in Oakland, CA
- Content pillars: Social Commentary, AI Building, Philanthropy, Education, Outdoor Equity

LINKEDIN PERFORMANCE DATA (from his framework):
- Text-only Prophet posts on breaking news with big-name anchors = highest reach (avg 42K impressions)
- Photo + personal narrative Builder posts = highest engagement (avg 4%+ ER)
- Social Commentary topic pillar gets 6x more reach than AI Building
- Big-name anchors (Meta, Google, OpenAI, Harvard) = 3.3x reach multiplier

VOICE DEFINITIONS:
- Prophet: Socratic questioning, moral tension, timely commentary, no CTA, ends with answerable question
- Builder: Cinematic scene, personal stakes, turning point, transferable lesson, community gratitude
- Teacher: Framework-oriented, practical takeaways, grounded in specific moments

Your job is to score news stories on their potential for Justin's LinkedIn content."""

SCORING_USER_PROMPT = """Analyze this news story and provide scores and recommendations.

HEADLINE: {headline}
SUMMARY: {summary}
SOURCE: {source}
PUBLISHED: {published}
TOPIC PILLAR: {topic_pillar}

Respond in this exact JSON format:
{{
    "reach_score": <0-10>,
    "engagement_score": <0-10>,
    "recommended_voice": "<Prophet|Builder|Teacher>",
    "big_name_anchors": ["<list of big names mentioned>"],
    "justin_angle": "<1-2 sentence suggestion for how Justin could approach this based on his experience>",
    "reasoning": "<brief explanation of scores>",
    "skip": <true if story is not relevant or too niche, false otherwise>
}}

SCORING CRITERIA:
Reach (0-10):
- +2 if breaking news (< 6 hours old)
- +2 if strong big-name anchor in headline
- +2 if moral tension/controversy
- +2 if part of broader national conversation
- +2 if Social Commentary pillar

Engagement (0-10):
- +2 if connects to Justin's direct experience (Google, philanthropy, Oakland, camping, Harvard/UVA)
- +2 if human interest angle (families, students, communities)
- +2 if values-aligned (equity, access, justice, belonging)
- +2 if story/origin potential
- +2 if could prompt genuine questions to audience"""

DEDUP_SYSTEM_PROMPT = """You are deduplicating news stories. Given a list of headlines, identify which ones are about the SAME underlying news event or announcement.

Return a JSON object where keys are cluster IDs (1, 2, 3...) and values are arrays of headline indices that belong together.

Stories about different aspects of the same company/topic are NOT duplicates unless they're covering the exact same announcement or event."""

DEDUP_USER_PROMPT = """Identify duplicate/same-story clusters from these headlines:

{headlines}

Return JSON like: {{"1": [0, 3, 7], "2": [1], "3": [2, 5]}}
where indices refer to the headline numbers above."""
