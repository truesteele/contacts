#!/usr/bin/env python3
"""
Step 3: Structure Perplexity Output - Extract Structured Data from Research

Uses Azure GPT-5.1-mini to parse raw Perplexity research and extract structured
information into database fields: philanthropic activity, capacity indicators,
affinity signals, and key findings.

Usage:
    python step_3_structure_output.py [--limit N] [--dry-run]
"""

import os
import sys
import argparse
import threading
from typing import Optional, List
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from azure_client import AzureGPT5MiniClient
from prompts import STRUCTURE_OUTPUT_SYSTEM, STRUCTURE_OUTPUT_USER
from env_validator import validate_env, print_env_status
from warmth_matcher import detect_warmth_for_contact

load_dotenv(override=True)

# Validate environment
if not print_env_status():
    sys.exit(1)


# Pydantic models for structured output
class PhilanthropicActivity(BaseModel):
    """Philanthropic giving and engagement."""
    nonprofit_boards: List[str]  # Board positions held
    documented_gifts: List[str]  # Known charitable gifts with amounts/orgs
    family_foundation: str  # Name if they have one, empty string otherwise
    volunteer_roles: List[str]  # Volunteer positions
    awards_recognition: List[str]  # Awards for service/leadership


class CapacityIndicators(BaseModel):
    """Financial capacity signals."""
    real_estate: List[str]  # Property holdings with values if available
    wealth_events: List[str]  # IPOs, acquisitions, inheritances, etc.
    compensation_signals: List[str]  # Salary ranges, equity, executive comp
    other_assets: List[str]  # Investments, businesses, other wealth indicators


class AffinitySignals(BaseModel):
    """Mission alignment indicators."""
    outdoor_environmental: List[str]  # Outdoor/nature/environmental involvement
    equity_access_dei: List[str]  # DEI, equity, access, social justice work
    family_youth_education: List[str]  # Family services, youth, education
    bay_area_community: List[str]  # Bay Area community engagement


class StructuredResearchOutput(BaseModel):
    """Complete structured extraction from research."""
    philanthropic_activity: PhilanthropicActivity
    capacity_indicators: CapacityIndicators
    affinity_signals: AffinitySignals
    key_findings: List[str]  # 3-5 most important findings
    recommended_cultivation_approach: str  # Brief cultivation recommendation
    confidence_level: str  # "high", "medium", or "low" based on data quality


class ResearchStructurer:
    """Structures Perplexity research output into database fields."""

    def __init__(self, dry_run: bool = False, workers: int = 1):
        """Initialize with Azure and Supabase clients."""
        self.dry_run = dry_run
        self.workers = workers

        # Initialize Azure client
        print("Initializing Azure GPT-5.1-mini client...")
        self.azure_client = AzureGPT5MiniClient()

        # Initialize Supabase client
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)

        # Stats tracking (thread-safe)
        self._lock = threading.Lock()
        self.total_structured = 0
        self.errors = []

    def get_prospects_with_research(self, limit: Optional[int] = None):
        """
        Fetch prospects with Perplexity research that needs structuring.

        Returns contacts with research data but no structured cultivation notes yet.
        """
        query = (self.supabase.table('contacts')
                 .select('*')
                 .not_.is_('perplexity_enriched_at', 'null')
                 .is_('cultivation_notes', 'null'))

        # Override Supabase default limit
        if limit:
            query = query.limit(limit)
        else:
            query = query.limit(10000)

        result = query.execute()
        return result.data

    def structure_research(self, contact: dict) -> Optional[StructuredResearchOutput]:
        """
        Extract structured data from Perplexity research.

        Returns StructuredResearchOutput or None if error.
        """
        try:
            name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

            # Get research content and sources
            research_data = contact.get('perplexity_research_data', {})
            research_content = research_data.get('content', '')
            sources = contact.get('perplexity_sources', [])

            if not research_content:
                print(f"  ⚠️  No research content found")
                return None

            # Confidence gate: Skip if research data is too thin
            content_length = len(research_content)
            source_count = len(sources) if sources else 0

            if content_length < 500:
                print(f"  ⚠️  Insufficient research data (only {content_length} chars) - skipping")
                return None

            if source_count < 2:
                print(f"  ⚠️  Too few sources ({source_count}) - data quality may be low")

            # Format sources for context
            sources_text = '\n'.join([f"- {url}" for url in sources]) if sources else "No sources available"

            # Build messages
            messages = [
                {"role": "system", "content": STRUCTURE_OUTPUT_SYSTEM},
                {"role": "user", "content": STRUCTURE_OUTPUT_USER.format(
                    name=name,
                    research_content=research_content[:15000],  # Limit to fit in context
                    sources=sources_text
                )}
            ]

            # Call Azure with structured output
            result = self.azure_client.structured_completion(
                messages=messages,
                response_model=StructuredResearchOutput,
                strict=True
            )

            return result

        except Exception as e:
            print(f"  ❌ Error structuring research: {e}")
            self.errors.append({
                'contact_id': contact['id'],
                'name': name,
                'error': str(e)
            })
            return None

    def update_contact(self, contact_id: int, contact: dict, result: StructuredResearchOutput):
        """Update contact with structured data."""
        if self.dry_run:
            print(f"  [DRY RUN] Would update contact {contact_id}")
            return

        # Calculate warmth score automatically
        warmth_data = detect_warmth_for_contact(contact)

        # Map structured output to database fields
        update_data = {
            # Philanthropic activity
            'nonprofit_board_member': len(result.philanthropic_activity.nonprofit_boards) > 0,
            'board_service_details': result.philanthropic_activity.nonprofit_boards,
            'known_donor': len(result.philanthropic_activity.documented_gifts) > 0,
            'past_giving_details': {
                'documented_gifts': result.philanthropic_activity.documented_gifts,
                'family_foundation': result.philanthropic_activity.family_foundation,
                'awards': result.philanthropic_activity.awards_recognition
            },
            'volunteer_history_detailed': result.philanthropic_activity.volunteer_roles,

            # Capacity indicators
            'real_estate_indicator': ', '.join(result.capacity_indicators.real_estate[:3]) if result.capacity_indicators.real_estate else None,

            # Affinity signals
            'outdoor_environmental_affinity': len(result.affinity_signals.outdoor_environmental) > 0,
            'outdoor_affinity_evidence': result.affinity_signals.outdoor_environmental,
            'equity_access_focus': len(result.affinity_signals.equity_access_dei) > 0,
            'equity_focus_evidence': result.affinity_signals.equity_access_dei,
            'family_youth_focus': len(result.affinity_signals.family_youth_education) > 0,
            'family_focus_evidence': result.affinity_signals.family_youth_education,

            # Cultivation metadata
            'cultivation_notes': '\n\n'.join([
                'KEY FINDINGS:',
                '\n'.join([f'- {f}' for f in result.key_findings]),
                '',
                'RECOMMENDED APPROACH:',
                result.recommended_cultivation_approach
            ]),

            # Warmth data (automated)
            **warmth_data
        }

        self.supabase.table('contacts').update(update_data).eq('id', contact_id).execute()

    def _process_contact(self, prospect: dict, index: int, total: int) -> bool:
        """Process a single contact (for parallel execution)."""
        result = self.structure_research(prospect)

        if result:
            # Update stats (thread-safe)
            with self._lock:
                self.total_structured += 1

                # Print progress every 10 contacts
                if self.total_structured % 10 == 0:
                    print(f"Progress: {self.total_structured}/{total} structured")

            # Update database
            self.update_contact(prospect['id'], prospect, result)
            return True

        return False

    def run(self, limit: Optional[int] = None):
        """Run the structuring process."""
        print("\n" + "=" * 80)
        print("DONOR PROSPECTING - STEP 3: STRUCTURE PERPLEXITY OUTPUT")
        print("=" * 80)
        if self.workers > 1:
            print(f"Running with {self.workers} parallel workers")
        else:
            print(f"Running single-threaded")

        # Fetch prospects with research
        print(f"\nFetching prospects with research{f' (limit: {limit})' if limit else ''}...")
        prospects = self.get_prospects_with_research(limit)

        if not prospects:
            print("✅ No prospects need structuring!")
            return

        print(f"Found {len(prospects)} prospects to structure\n")

        if self.workers == 1:
            # Single-threaded execution
            for i, prospect in enumerate(prospects, 1):
                name = f"{prospect.get('first_name', '')} {prospect.get('last_name', '')}".strip()
                company = prospect.get('enrich_current_company') or prospect.get('company') or 'Unknown'

                print(f"[{i}/{len(prospects)}] Structuring: {name} ({company})")
                self._process_contact(prospect, i, len(prospects))
                print()
        else:
            # Parallel execution
            print(f"Starting parallel processing with {self.workers} workers...\n")

            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = {
                    executor.submit(self._process_contact, prospect, i, len(prospects)): prospect
                    for i, prospect in enumerate(prospects, 1)
                }

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        prospect = futures[future]
                        name = f"{prospect.get('first_name', '')} {prospect.get('last_name', '')}".strip()
                        print(f"  ❌ Unexpected error for {name}: {e}")

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print structuring summary and usage stats."""
        print("=" * 80)
        print("STRUCTURING SUMMARY")
        print("=" * 80)
        print(f"Total Structured: {self.total_structured}")

        if self.errors:
            print(f"\n⚠️  Errors: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  - {error['name']}: {error['error']}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more")

        # Print Azure usage
        self.azure_client.print_usage()

        if self.total_structured > 0 and not self.dry_run:
            print("\n" + "=" * 80)
            print("NEXT STEP")
            print("=" * 80)
            print(f"✅ {self.total_structured} prospects have structured data!")
            print(f"Run: python step_4_final_scoring.py")
            print("=" * 80 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Structure Perplexity research output into database fields'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of prospects to structure (for testing)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without updating database'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of parallel workers (default: 1, recommended: 30-50 for Azure rate limits)'
    )

    args = parser.parse_args()

    try:
        structurer = ResearchStructurer(dry_run=args.dry_run, workers=args.workers)
        structurer.run(limit=args.limit)
    except KeyboardInterrupt:
        print("\n\n⚠️  Structuring interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
