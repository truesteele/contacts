"""
OpenAI-Powered News Scorer
Uses GPT-4o-mini for intelligent scoring, deduplication, and voice recommendations
"""

import json
import os
import time
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from openai import OpenAI, APIError, RateLimitError, APIConnectionError

from config import (
    SCORING_SYSTEM_PROMPT,
    SCORING_USER_PROMPT,
    DEDUP_SYSTEM_PROMPT,
    DEDUP_USER_PROMPT,
)
from fetcher import NewsStory

logger = logging.getLogger(__name__)


def retry_with_backoff(
    func,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (RateLimitError, APIConnectionError, APIError),
):
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to retry (should be a callable)
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for each retry
        retryable_exceptions: Tuple of exceptions to retry on

    Returns:
        Result of the function call

    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except retryable_exceptions as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"All {max_retries + 1} attempts failed")
                raise

    raise last_exception


@dataclass
class ScoredStory:
    """A news story with AI-generated scores and recommendations"""
    story: NewsStory
    reach_score: int
    engagement_score: int
    recommended_voice: str
    big_name_anchors: List[str]
    justin_angle: str
    reasoning: str
    combined_score: float  # Weighted combination for ranking

    def to_dict(self) -> dict:
        return {
            **self.story.to_dict(),
            "reach_score": self.reach_score,
            "engagement_score": self.engagement_score,
            "recommended_voice": self.recommended_voice,
            "big_name_anchors": self.big_name_anchors,
            "justin_angle": self.justin_angle,
            "reasoning": self.reasoning,
            "combined_score": self.combined_score,
        }


class NewsScorer:
    """Handles AI-powered news analysis"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"  # OpenAI's fast, affordable model

    def deduplicate_stories(self, stories: List[NewsStory]) -> List[NewsStory]:
        """
        Use AI to identify and remove duplicate stories about the same event
        Keeps the story from the most reputable source or most recent

        Returns:
            Deduplicated list of stories
        """
        if len(stories) <= 1:
            return stories

        # Prepare headlines for deduplication
        headlines_text = "\n".join(
            f"{i}: {s.headline} ({s.source})"
            for i, s in enumerate(stories)
        )

        def make_request():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": DEDUP_SYSTEM_PROMPT},
                    {"role": "user", "content": DEDUP_USER_PROMPT.format(headlines=headlines_text)},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistency
                timeout=30,
            )

        try:
            response = retry_with_backoff(make_request)
            clusters = json.loads(response.choices[0].message.content)

            # For each cluster, keep only the best story (first one, or from major source)
            keep_indices = set()
            for cluster_id, indices in clusters.items():
                if len(indices) == 1:
                    keep_indices.add(indices[0])
                else:
                    # Keep the first story (usually most recent/prominent)
                    keep_indices.add(indices[0])

            deduped = [s for i, s in enumerate(stories) if i in keep_indices]
            logger.info(f"Deduplication: {len(stories)} -> {len(deduped)} stories")
            print(f"Deduplication: {len(stories)} -> {len(deduped)} stories")
            return deduped

        except Exception as e:
            logger.error(f"Deduplication error: {e}")
            print(f"Deduplication error: {e}")
            return stories  # Return original on error

    def score_story(self, story: NewsStory) -> Optional[ScoredStory]:
        """
        Score a single story using AI

        Returns:
            ScoredStory with all scores and recommendations, or None if should skip
        """
        def make_request():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": SCORING_USER_PROMPT.format(
                            headline=story.headline,
                            summary=story.summary,
                            source=story.source,
                            published=f"{story.hours_old():.1f} hours ago",
                            topic_pillar=story.topic_pillar,
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                timeout=30,
            )

        try:
            response = retry_with_backoff(make_request)
            result = json.loads(response.choices[0].message.content)

            # Skip if AI says not relevant
            if result.get("skip", False):
                return None

            # Calculate combined score (weighted toward reach for your strategy)
            reach = result.get("reach_score", 0)
            engagement = result.get("engagement_score", 0)
            combined = (reach * 0.6) + (engagement * 0.4)  # Slight reach bias

            return ScoredStory(
                story=story,
                reach_score=reach,
                engagement_score=engagement,
                recommended_voice=result.get("recommended_voice", "Prophet"),
                big_name_anchors=result.get("big_name_anchors", []),
                justin_angle=result.get("justin_angle", ""),
                reasoning=result.get("reasoning", ""),
                combined_score=combined,
            )

        except Exception as e:
            logger.error(f"Scoring error for '{story.headline[:50]}...': {e}")
            print(f"Scoring error for '{story.headline[:50]}...': {e}")
            return None

    def score_stories(self, stories: List[NewsStory], max_to_score: int = 30) -> List[ScoredStory]:
        """
        Score multiple stories

        Args:
            stories: List of stories to score
            max_to_score: Maximum number to score (to control API costs)

        Returns:
            List of ScoredStory objects, sorted by combined score
        """
        # Limit stories to score
        to_score = stories[:max_to_score]

        scored = []
        for i, story in enumerate(to_score):
            print(f"Scoring {i+1}/{len(to_score)}: {story.headline[:50]}...")
            result = self.score_story(story)
            if result:
                scored.append(result)

        # Sort by combined score (highest first)
        scored.sort(key=lambda s: s.combined_score, reverse=True)

        return scored


def process_news(
    stories: List[NewsStory],
    api_key: Optional[str] = None,
    max_stories: int = 10,
) -> List[ScoredStory]:
    """
    Main processing pipeline: deduplicate -> score -> rank -> select top N

    Args:
        stories: Raw stories from fetcher
        api_key: OpenAI API key
        max_stories: Number of stories to return

    Returns:
        Top N scored and ranked stories
    """
    scorer = NewsScorer(api_key)

    # Step 1: Deduplicate
    print("\n--- Deduplicating stories ---")
    deduped = scorer.deduplicate_stories(stories)

    # Step 2: Score (limit to 30 to control costs, ~$0.02 per run)
    print("\n--- Scoring stories ---")
    scored = scorer.score_stories(deduped, max_to_score=30)

    # Step 3: Select top N
    top_stories = scored[:max_stories]

    print(f"\n--- Selected top {len(top_stories)} stories ---")
    return top_stories


if __name__ == "__main__":
    # Test with sample data
    from fetcher import fetch_all_news

    stories = fetch_all_news(hours_lookback=24)

    if stories:
        top = process_news(stories, max_stories=5)

        for i, s in enumerate(top, 1):
            print(f"\n{'='*60}")
            print(f"#{i} [{s.recommended_voice}] {s.story.headline}")
            print(f"Reach: {s.reach_score}/10 | Engagement: {s.engagement_score}/10")
            print(f"Anchors: {', '.join(s.big_name_anchors) or 'None'}")
            print(f"Angle: {s.justin_angle}")
