"""
Perplexity API client wrapper for comprehensive donor research.

Handles web research on qualified donor prospects to gather:
- Philanthropic activity (donations, board service)
- Real estate ownership
- Awards and recognition
- Foundation affiliations
- Social impact focus areas
- Connection to outdoor/environmental causes
"""

import os
import time
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv
import requests

load_dotenv()

class PerplexityClient:
    """Wrapper for Perplexity API with comprehensive search capabilities."""

    def __init__(self, model: str = "sonar-reasoning-pro"):
        """
        Initialize Perplexity client.

        Args:
            model: Perplexity model to use
                - "sonar-reasoning-pro": Best reasoning, ~$5/1M tokens
                - "sonar-pro": Fast, ~$3/1M tokens
                - "sonar": Basic, ~$1/1M tokens
        """
        self.api_key = os.environ.get("PERPLEXITY_APIKEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_APIKEY must be set in .env")

        self.model = model
        self.base_url = "https://api.perplexity.ai/chat/completions"

        # Rate limiting (assume conservative limit)
        self.min_request_interval = 0.1  # 10 req/sec
        self.last_request_time = 0

        # Usage tracking
        self.total_requests = 0
        self.total_tokens = 0
        self.estimated_cost = 0.0

    def _wait_for_rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def research_donor(
        self,
        name: str,
        company: Optional[str] = None,
        title: Optional[str] = None,
        location: Optional[str] = None,
        education: Optional[List[str]] = None,
        scope: str = "comprehensive"
    ) -> Dict:
        """
        Research a donor prospect using 3 focused queries with delays.

        Uses multiple targeted queries (3 for comprehensive) with delays to avoid
        rate limiting while getting better source coverage than a single query.

        Args:
            name: Full name of prospect
            company: Current company
            title: Current job title
            location: City/state
            education: List of schools attended
            scope: "quick", "deep", or "comprehensive"

        Returns:
            Dict with 'content' (aggregated research), 'sources' (URLs), 'usage'
        """
        queries = self._build_focused_queries(name, company, title, location, education, scope)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        all_content = []
        all_sources = set()
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # Execute queries with delays to avoid rate limiting
        for i, query in enumerate(queries, 1):
            # Rate limit + extra delay for safety
            self._wait_for_rate_limit()
            if i > 1:
                time.sleep(1.0)  # 1 second delay between queries

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert researcher specializing in philanthropic due diligence and donor capacity assessment. Provide detailed, fact-based information with sources."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "return_citations": True,
                "return_related_questions": False
            }

            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                response.raise_for_status()

                data = response.json()

                # Extract content
                content = data["choices"][0]["message"]["content"]
                all_content.append(content)

                # Extract sources
                if "citations" in data:
                    all_sources.update(data["citations"])

                # Track usage
                usage = data.get("usage", {})
                for key in total_usage:
                    total_usage[key] += usage.get(key, 0)

            except requests.exceptions.RequestException as e:
                all_content.append(f"Query {i} failed: {str(e)}")

        # Combine results
        combined_content = "\n\n---\n\n".join(all_content)

        # Track totals
        self.total_tokens += total_usage["total_tokens"]
        self.total_requests += len(queries)
        self._update_cost_estimate(total_usage["total_tokens"])

        return {
            "content": combined_content,
            "sources": list(all_sources),
            "usage": total_usage,
            "model": self.model,
            "queries_executed": len(queries)
        }

    def _build_focused_queries(
        self,
        name: str,
        company: Optional[str],
        title: Optional[str],
        location: Optional[str],
        education: Optional[List[str]],
        scope: str
    ) -> List[str]:
        """
        Build 3 focused queries with strong identity verification.

        Each query includes identifying details (company, title, location, education)
        to ensure we're researching the correct person.
        """
        # Build strong identity context for each query
        identity_parts = [name]
        if title and company:
            identity_parts.append(f"{title} at {company}")
        elif company:
            identity_parts.append(f"at {company}")
        if location:
            identity_parts.append(f"in {location}")
        if education and len(education) > 0:
            identity_parts.append(f"who attended {education[0]}")

        person_id = ", ".join(identity_parts)

        # Emphasize identity verification
        verify_note = f"\n\nIMPORTANT: Verify this is the correct {name}"
        if company:
            verify_note += f" who works/worked at {company}"
        if education:
            verify_note += f" and attended {', '.join(education[:2])}"
        verify_note += ". If there are multiple people with this name, focus on the one matching these details."

        if scope == "quick":
            return [
                f"{person_id}: Find nonprofit board positions, charitable donations, and philanthropic activity{verify_note}",
                f"{person_id}: Find wealth indicators including real estate, business ownership, and capacity signals{verify_note}"
            ]

        else:  # comprehensive or deep - use 3 focused queries
            queries = [
                # Query 1: Philanthropic Activity & Capacity
                f"{person_id}: Find detailed philanthropic history including nonprofit board positions (with dates), documented charitable donations (specific amounts and recipients), foundation involvement, volunteer work, awards for service, and political donations as capacity indicators{verify_note}",

                # Query 2: Wealth Indicators & Professional Background
                f"{person_id}: Find wealth and capacity indicators including real estate holdings (properties and values), business ownership, equity stakes, executive compensation, career progression, company valuations, IPOs/acquisitions, and luxury assets{verify_note}",

                # Query 3: Mission Affinity & Public Profile
                f"{person_id}: Find connection to outdoor recreation, environmental causes, equity/DEI initiatives, youth development, education causes, Bay Area community involvement, media mentions, interviews, public statements about causes, and personal interests relevant to outdoor access and social equity{verify_note}"
            ]

            return queries

    def _build_comprehensive_query(
        self,
        name: str,
        company: Optional[str],
        title: Optional[str],
        location: Optional[str],
        education: Optional[List[str]],
        scope: str
    ) -> str:
        """Build comprehensive research query (legacy method for reference)."""

        # Build identification context
        context_parts = [f"Research {name}"]
        if title and company:
            context_parts.append(f"who is {title} at {company}")
        elif company:
            context_parts.append(f"who works at {company}")
        if location:
            context_parts.append(f"located in {location}")
        if education:
            context_parts.append(f"and attended {', '.join(education[:2])}")

        context = " ".join(context_parts) + "."

        # Research areas based on scope
        if scope == "quick":
            areas = """
Find:
1. Any nonprofit board positions or advisory roles
2. Major charitable donations or philanthropic activity
3. Current company role and seniority level
"""
        elif scope == "deep":
            areas = """
Find:
1. Philanthropic activity:
   - Nonprofit board positions (current and past)
   - Major charitable donations and causes supported
   - Foundation involvement or family foundations
   - Volunteer work and community engagement

2. Capacity indicators:
   - Real estate ownership (approximate value if available)
   - Business leadership roles and company valuations
   - Awards, honors, or recognition received
   - Executive compensation or wealth indicators

3. Mission alignment:
   - Connection to outdoor recreation or environmental causes
   - Involvement in equity, access, or social justice work
   - Support for youth development or family-focused causes
"""
        else:  # comprehensive
            areas = """
Find:
1. Philanthropic history and propensity:
   - Complete list of nonprofit board positions (current and past) with dates
   - Documented charitable donations (amounts, recipients, years)
   - Foundation involvement (trustee roles, family foundations)
   - Volunteer work, mentorship, and pro bono activities
   - Attendance at charity galas or fundraising events
   - Political donations (as indicator of giving capacity)

2. Wealth and capacity indicators:
   - Real estate holdings (properties, approximate values, locations)
   - Business ownership or equity stakes
   - Executive roles and estimated compensation
   - Awards, honors, and recognition received
   - Speaking engagements, thought leadership
   - Luxury asset ownership (if publicly known)

3. Mission affinity with outdoor access and equity:
   - Connection to outdoor recreation, camping, hiking, environmental causes
   - Involvement in equity, inclusion, diversity, or access initiatives
   - Support for youth development, education, or family services
   - Bay Area community involvement
   - Personal outdoor activities or interests (social media, interviews)

4. Network and connections:
   - Shared affiliations with major Bay Area institutions
   - Professional networks and community involvement
   - Family information (spouse, children - as it relates to mission fit)

5. Media mentions and public profile:
   - News articles, press releases, interviews
   - LinkedIn activity and professional updates
   - Public statements about causes or values
"""

        query = f"""{context}

{areas}

Provide specific, verifiable facts with dates where available. Include source URLs for all claims.
Focus on information from the last 5 years, but include significant historical information.
If information is not available, explicitly state that rather than speculating.
"""

        return query

    def _update_cost_estimate(self, tokens: int):
        """Update estimated cost based on tokens used."""
        # Pricing per 1M tokens (approximate)
        pricing = {
            "sonar-reasoning-pro": 5.0,
            "sonar-pro": 3.0,
            "sonar": 1.0
        }
        rate = pricing.get(self.model, 3.0)
        self.estimated_cost += (tokens / 1_000_000) * rate

    def get_usage_summary(self) -> Dict:
        """Get summary of API usage."""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost,
            "model": self.model
        }

    def print_usage(self):
        """Print usage summary to console."""
        summary = self.get_usage_summary()
        print("\n" + "=" * 80)
        print("PERPLEXITY API USAGE SUMMARY")
        print("=" * 80)
        print(f"Model: {summary['model']}")
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        print(f"Estimated Cost: ${summary['estimated_cost_usd']:.4f}")
        print("=" * 80 + "\n")
