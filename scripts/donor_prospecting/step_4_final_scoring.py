#!/usr/bin/env python3
"""
Step 4: Final Scoring - Comprehensive Donor Qualification Scoring

Uses Azure GPT-5.1-mini to perform comprehensive reasoning and score prospects
across four dimensions: Capacity, Propensity, Affinity, and Warmth.
Assigns final tier and cultivation recommendations.

Usage:
    python step_4_final_scoring.py [--limit N] [--dry-run]
"""

import os
import sys
import argparse
from typing import Optional, List
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from pydantic import BaseModel

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from azure_client import AzureGPT5MiniClient
from prompts import FINAL_SCORING_SYSTEM, FINAL_SCORING_USER

load_dotenv()


# Pydantic model for final scoring
class DimensionScore(BaseModel):
    """Score and reasoning for one dimension."""
    score: int  # 0-100
    reasoning: str  # Detailed explanation
    key_evidence: List[str]  # 3-5 pieces of evidence


class FinalScoringResult(BaseModel):
    """Complete final scoring output."""
    capacity: DimensionScore
    propensity: DimensionScore
    affinity: DimensionScore
    warmth: DimensionScore
    total_score: int  # Weighted sum
    tier: int  # 1-5 based on total_score
    tier_rationale: str  # Why this tier
    cultivation_stage: str  # "immediate", "short-term", "medium-term", "long-term", "watch"
    next_steps: List[str]  # 3-5 specific cultivation actions
    estimated_capacity_range: str  # e.g., "$5k-$10k", "$10k-$25k"


class FinalScorer:
    """Performs comprehensive final scoring for donor prospects."""

    def __init__(self, dry_run: bool = False):
        """Initialize with Azure and Supabase clients."""
        self.dry_run = dry_run

        # Initialize Azure client
        print("Initializing Azure GPT-5.1-mini client...")
        self.azure_client = AzureGPT5MiniClient()

        # Initialize Supabase client
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)

        # Stats tracking
        self.total_scored = 0
        self.tier_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        self.errors = []

    def get_prospects_for_scoring(self, limit: Optional[int] = None):
        """
        Fetch prospects ready for final scoring.

        Returns contacts with research and structured data but no final scoring.
        """
        query = (self.supabase.table('contacts')
                 .select('*')
                 .not_.is_('perplexity_enriched_at', 'null')
                 .is_('final_scoring_date', 'null'))

        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data

    def prepare_scoring_data(self, contact: dict) -> dict:
        """Prepare comprehensive data package for scoring."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

        # LinkedIn profile summary
        linkedin_data = []
        if contact.get('headline'):
            linkedin_data.append(f"Headline: {contact['headline']}")
        if contact.get('enrich_current_company'):
            linkedin_data.append(f"Company: {contact['enrich_current_company']}")
        if contact.get('enrich_current_title'):
            linkedin_data.append(f"Title: {contact['enrich_current_title']}")
        if contact.get('enrich_total_experience_years'):
            linkedin_data.append(f"Experience: {contact['enrich_total_experience_years']} years")
        if contact.get('enrich_schools'):
            linkedin_data.append(f"Education: {', '.join(contact['enrich_schools'][:2])}")
        if contact.get('enrich_board_positions'):
            linkedin_data.append(f"Board Positions: {', '.join(contact['enrich_board_positions'][:3])}")

        linkedin_summary = '\n'.join(linkedin_data) if linkedin_data else 'Limited LinkedIn data'

        # Enrichment data from Perplexity
        enrichment = []

        if contact.get('board_service_details'):
            enrichment.append(f"Board Service: {', '.join(contact['board_service_details'][:3])}")

        if contact.get('past_giving_details'):
            giving = contact['past_giving_details']
            if isinstance(giving, dict):
                if giving.get('documented_gifts'):
                    enrichment.append(f"Known Gifts: {', '.join(giving['documented_gifts'][:3])}")
                if giving.get('family_foundation'):
                    enrichment.append(f"Family Foundation: {giving['family_foundation']}")

        if contact.get('real_estate_indicator'):
            enrichment.append(f"Real Estate: {contact['real_estate_indicator']}")

        if contact.get('outdoor_affinity_evidence'):
            enrichment.append(f"Outdoor/Environmental: {', '.join(contact['outdoor_affinity_evidence'][:2])}")

        if contact.get('equity_focus_evidence'):
            enrichment.append(f"Equity/DEI Focus: {', '.join(contact['equity_focus_evidence'][:2])}")

        if contact.get('family_focus_evidence'):
            enrichment.append(f"Family/Youth Focus: {', '.join(contact['family_focus_evidence'][:2])}")

        enrichment_data = '\n'.join(enrichment) if enrichment else 'Limited enrichment data available'

        return {
            'name': name,
            'company': contact.get('enrich_current_company') or contact.get('company') or 'Unknown',
            'position': contact.get('enrich_current_title') or contact.get('position') or 'Unknown',
            'location': contact.get('location_name') or contact.get('city', 'Unknown'),
            'education': ', '.join(contact.get('enrich_schools', [])[:2]) if contact.get('enrich_schools') else 'Not provided',
            'linkedin_summary': linkedin_summary,
            'enrichment_data': enrichment_data
        }

    def score_prospect(self, contact: dict) -> Optional[FinalScoringResult]:
        """
        Perform comprehensive final scoring.

        Returns FinalScoringResult or None if error.
        """
        try:
            scoring_data = self.prepare_scoring_data(contact)

            # Build messages
            messages = [
                {"role": "system", "content": FINAL_SCORING_SYSTEM},
                {"role": "user", "content": FINAL_SCORING_USER.format(**scoring_data)}
            ]

            # Call Azure with structured output
            result = self.azure_client.structured_completion(
                messages=messages,
                response_model=FinalScoringResult,
                strict=True
            )

            return result

        except Exception as e:
            print(f"  ❌ Error scoring: {e}")
            self.errors.append({
                'contact_id': contact['id'],
                'name': scoring_data['name'],
                'error': str(e)
            })
            return None

    def update_contact(self, contact_id: int, result: FinalScoringResult):
        """Update contact with final scores."""
        if self.dry_run:
            print(f"  [DRY RUN] Would update contact {contact_id}")
            return

        update_data = {
            # Individual dimension scores
            'donor_capacity_score': result.capacity.score,
            'donor_propensity_score': result.propensity.score,
            'donor_affinity_score': result.affinity.score,
            'donor_warmth_score': result.warmth.score,

            # Total score and tier
            'donor_total_score': result.total_score,
            'donor_tier': f"Tier {result.tier}",

            # Capacity estimate
            'estimated_capacity': result.estimated_capacity_range,

            # Cultivation planning
            'cultivation_stage': result.cultivation_stage,
            'cultivation_plan': '\n'.join([
                f"TIER {result.tier} - {result.tier_rationale}",
                '',
                'SCORES:',
                f"- Capacity: {result.capacity.score}/100 - {result.capacity.reasoning[:150]}...",
                f"- Propensity: {result.propensity.score}/100 - {result.propensity.reasoning[:150]}...",
                f"- Affinity: {result.affinity.score}/100 - {result.affinity.reasoning[:150]}...",
                f"- Warmth: {result.warmth.score}/100 - {result.warmth.reasoning[:150]}...",
                '',
                'NEXT STEPS:',
                '\n'.join([f"{i+1}. {step}" for i, step in enumerate(result.next_steps)])
            ]),

            # Timestamp
            'final_scoring_date': datetime.now(timezone.utc).isoformat(),
            'donor_score_last_calculated': datetime.now(timezone.utc).isoformat()
        }

        self.supabase.table('contacts').update(update_data).eq('id', contact_id).execute()

    def run(self, limit: Optional[int] = None):
        """Run the final scoring process."""
        print("\n" + "=" * 80)
        print("DONOR PROSPECTING - STEP 4: FINAL SCORING")
        print("=" * 80)

        # Fetch prospects ready for scoring
        print(f"\nFetching prospects for scoring{f' (limit: {limit})' if limit else ''}...")
        prospects = self.get_prospects_for_scoring(limit)

        if not prospects:
            print("✅ No prospects need scoring!")
            return

        print(f"Found {len(prospects)} prospects to score\n")

        # Score each prospect
        for i, prospect in enumerate(prospects, 1):
            name = f"{prospect.get('first_name', '')} {prospect.get('last_name', '')}".strip()
            company = prospect.get('enrich_current_company') or prospect.get('company') or 'Unknown'

            print(f"[{i}/{len(prospects)}] Scoring: {name} ({company})")

            result = self.score_prospect(prospect)

            if result:
                print(f"  ✅ Scored - Tier {result.tier} (Total: {result.total_score}/100)")
                print(f"     Capacity: {result.capacity.score}, Propensity: {result.propensity.score}, " +
                      f"Affinity: {result.affinity.score}, Warmth: {result.warmth.score}")
                print(f"     Estimated Capacity: {result.estimated_capacity_range}")
                print(f"     Cultivation: {result.cultivation_stage}")

                # Update database
                self.update_contact(prospect['id'], result)
                self.total_scored += 1
                self.tier_counts[result.tier] += 1

            print()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print scoring summary and usage stats."""
        print("=" * 80)
        print("FINAL SCORING SUMMARY")
        print("=" * 80)
        print(f"Total Scored: {self.total_scored}")

        if self.total_scored > 0:
            print("\nTier Distribution:")
            print(f"  Tier 1 (Priority): {self.tier_counts[1]} ({self.tier_counts[1]/self.total_scored*100:.1f}%)")
            print(f"  Tier 2 (Strong): {self.tier_counts[2]} ({self.tier_counts[2]/self.total_scored*100:.1f}%)")
            print(f"  Tier 3 (Emerging): {self.tier_counts[3]} ({self.tier_counts[3]/self.total_scored*100:.1f}%)")
            print(f"  Tier 4 (Watch): {self.tier_counts[4]} ({self.tier_counts[4]/self.total_scored*100:.1f}%)")
            print(f"  Tier 5 (Lower): {self.tier_counts[5]} ({self.tier_counts[5]/self.total_scored*100:.1f}%)")

        if self.errors:
            print(f"\n⚠️  Errors: {len(self.errors)}")
            for error in self.errors[:5]:
                print(f"  - {error['name']}: {error['error']}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more")

        # Print Azure usage
        self.azure_client.print_usage()

        if self.total_scored > 0 and not self.dry_run:
            print("\n" + "=" * 80)
            print("✅ DONOR PROSPECTING WORKFLOW COMPLETE!")
            print("=" * 80)
            print(f"{self.total_scored} prospects fully qualified and ready for cultivation")
            print(f"\nPriority prospects (Tier 1-2): {self.tier_counts[1] + self.tier_counts[2]}")
            print("\nNext: Review prospects in Supabase and begin cultivation outreach!")
            print("=" * 80 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Perform final comprehensive scoring on donor prospects'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of prospects to score (for testing)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without updating database'
    )

    args = parser.parse_args()

    try:
        scorer = FinalScorer(dry_run=args.dry_run)
        scorer.run(limit=args.limit)
    except KeyboardInterrupt:
        print("\n\n⚠️  Scoring interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
