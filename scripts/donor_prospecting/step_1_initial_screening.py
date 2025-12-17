#!/usr/bin/env python3
"""
Step 1: Initial Screening - Donor Capacity Assessment

Evaluates all contacts in Supabase for donor capacity using Azure GPT-5.1-mini.
Uses existing LinkedIn data to identify prospects with capacity for $5k+ gifts.

Usage:
    python step_1_initial_screening.py [--limit N] [--dry-run]
"""

import os
import sys
import argparse
import threading
from typing import Optional
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from supabase import create_client, Client
from pydantic import BaseModel

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from azure_client import AzureGPT5MiniClient
from prompts import INITIAL_SCREENING_SYSTEM, INITIAL_SCREENING_USER

load_dotenv()

# Pydantic model for structured output
class InitialScreeningResult(BaseModel):
    """Structured result from initial screening."""
    is_qualified: bool
    capacity_score: int  # 0-100
    reasoning: str
    key_indicators: list[str]
    failure_reason: str  # Empty string if not applicable


class DonorScreener:
    """Handles initial donor capacity screening."""

    def __init__(self, dry_run: bool = False, workers: int = 1):
        """Initialize screener with Azure and Supabase clients."""
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
        self.total_screened = 0
        self.total_qualified = 0
        self.total_failed = 0
        self.errors = []

    def get_unscreened_contacts(self, limit: Optional[int] = None):
        """
        Fetch contacts that haven't been screened yet.

        Returns contacts with LinkedIn data who need initial screening.
        """
        query = self.supabase.table('contacts').select('*').or_(
            'initial_screening_completed.is.null,initial_screening_completed.eq.false'
        )

        # Only screen contacts with meaningful LinkedIn data (headline or current company)
        query = query.or_('headline.not.is.null,enrich_current_company.not.is.null,company.not.is.null')

        # Set limit - if not specified, fetch all (use large limit to override Supabase default of 1000)
        if limit:
            query = query.limit(limit)
        else:
            query = query.limit(10000)  # Fetch all unscreened contacts

        result = query.execute()
        return result.data

    def prepare_contact_data(self, contact: dict) -> dict:
        """Extract and format contact data for screening."""
        # Build education summary from enriched data or raw data
        education = 'Not provided'
        if contact.get('enrich_schools'):
            schools = ', '.join(contact['enrich_schools'][:3])  # Top 3 schools
            degree = contact.get('enrich_highest_degree', '')
            fields = contact.get('enrich_fields_of_study', [])
            field_str = ', '.join(fields[:2]) if fields else ''
            education = f"{degree} from {schools}" if degree else schools
            if field_str:
                education += f" ({field_str})"
        elif contact.get('school_name_education'):
            education = contact['school_name_education']
            if contact.get('degree_education'):
                education += f", {contact['degree_education']}"

        # Build experience summary
        experience = 'Not provided'
        if contact.get('enrich_total_experience_years'):
            years = contact['enrich_total_experience_years']
            companies = contact.get('enrich_number_of_companies', 0)
            titles = ', '.join(contact.get('enrich_titles_held', [])[:3]) if contact.get('enrich_titles_held') else ''
            experience = f"{years} years experience across {companies} companies"
            if titles:
                experience += f". Past titles: {titles}"
        elif contact.get('summary_experience'):
            experience = contact['summary_experience']

        # Build volunteer/board summary
        volunteer = 'None listed'
        board_positions = 'None listed'
        if contact.get('enrich_board_positions'):
            board_positions = ', '.join(contact['enrich_board_positions'][:3])
        if contact.get('enrich_volunteer_orgs'):
            volunteer = ', '.join(contact['enrich_volunteer_orgs'][:3])
        elif contact.get('company_name_volunteering'):
            volunteer = contact['company_name_volunteering']

        # Skills
        skills = 'Not listed'
        if contact.get('enrich_skills'):
            skills = ', '.join(contact['enrich_skills'][:10])

        return {
            'name': f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip() or 'Unknown',
            'company': contact.get('enrich_current_company') or contact.get('company') or 'Unknown',
            'position': contact.get('enrich_current_title') or contact.get('position') or 'Unknown',
            'headline': contact.get('headline') or 'Not provided',
            'location': contact.get('location_name') or contact.get('city', '') + ', ' + contact.get('state', '') if contact.get('city') or contact.get('state') else 'Unknown',
            'education': education,
            'experience_summary': experience,
            'volunteer_work': volunteer,
            'board_positions': board_positions,
            'skills': skills
        }

    def screen_contact(self, contact: dict, show_progress: bool = True) -> Optional[InitialScreeningResult]:
        """
        Screen a single contact for donor capacity.

        Returns InitialScreeningResult or None if error.
        """
        try:
            # Prepare data
            contact_data = self.prepare_contact_data(contact)

            # Build messages
            messages = [
                {"role": "system", "content": INITIAL_SCREENING_SYSTEM},
                {"role": "user", "content": INITIAL_SCREENING_USER.format(**contact_data)}
            ]

            # Call Azure with structured output
            result = self.azure_client.structured_completion(
                messages=messages,
                response_model=InitialScreeningResult,
                strict=True
            )

            return result

        except Exception as e:
            if show_progress:
                print(f"  ❌ Error screening {contact_data.get('name', 'Unknown')}: {e}")
            with self._lock:
                self.errors.append({
                    'contact_id': contact['id'],
                    'name': contact_data.get('name', 'Unknown'),
                    'error': str(e)
                })
            return None

    def update_contact(self, contact_id: int, result: InitialScreeningResult):
        """Update contact record with screening results."""
        if self.dry_run:
            print(f"  [DRY RUN] Would update contact {contact_id}")
            return

        update_data = {
            'initial_screening_completed': True,
            'initial_screening_passed': result.is_qualified,
            'initial_screening_reasoning': result.reasoning,
            'initial_screening_date': datetime.now(timezone.utc).isoformat(),
            'donor_capacity_score': result.capacity_score if result.is_qualified else None,
            'capacity_indicators': result.key_indicators if result.is_qualified else [],
            'disqualification_reason': result.failure_reason if result.failure_reason else None
        }

        self.supabase.table('contacts').update(update_data).eq('id', contact_id).execute()

    def _process_contact(self, contact: dict, index: int, total: int) -> bool:
        """Process a single contact (for parallel execution)."""
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip() or 'Unknown'

        # Screen contact
        result = self.screen_contact(contact, show_progress=False)

        if result:
            # Update stats
            with self._lock:
                if result.is_qualified:
                    self.total_qualified += 1
                else:
                    self.total_failed += 1
                self.total_screened += 1

                # Print progress every 10 contacts
                if self.total_screened % 10 == 0:
                    print(f"Progress: {self.total_screened}/{total} screened, {self.total_qualified} qualified ({self.total_qualified/self.total_screened*100:.1f}%)")

            # Update database
            self.update_contact(contact['id'], result)
            return True

        return False

    def run(self, limit: Optional[int] = None):
        """Run the screening process."""
        print("\n" + "=" * 80)
        print("DONOR PROSPECTING - STEP 1: INITIAL SCREENING")
        print("=" * 80)

        if self.workers > 1:
            print(f"Running with {self.workers} parallel workers")

        # Fetch contacts to screen
        print(f"\nFetching unscreened contacts{f' (limit: {limit})' if limit else ''}...")
        contacts = self.get_unscreened_contacts(limit)

        if not contacts:
            print("✅ No contacts need screening!")
            return

        print(f"Found {len(contacts)} contacts to screen\n")

        if self.workers == 1:
            # Single-threaded (original behavior)
            for i, contact in enumerate(contacts, 1):
                name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip() or 'Unknown'
                company = contact.get('enrich_current_company') or contact.get('company') or 'Unknown'

                print(f"[{i}/{len(contacts)}] Screening: {name} ({company})")

                result = self.screen_contact(contact, show_progress=True)

                if result:
                    if result.is_qualified:
                        print(f"  ✅ QUALIFIED - Capacity Score: {result.capacity_score}/100")
                        print(f"     Reasoning: {result.reasoning[:100]}...")
                        self.total_qualified += 1
                    else:
                        print(f"  ❌ NOT QUALIFIED - {result.failure_reason or 'Low capacity'}")
                        self.total_failed += 1

                    # Update database
                    self.update_contact(contact['id'], result)
                    self.total_screened += 1

                print()
        else:
            # Parallel processing
            print(f"Starting parallel processing with {self.workers} workers...\n")

            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                # Submit all contacts
                futures = {
                    executor.submit(self._process_contact, contact, i, len(contacts)): contact
                    for i, contact in enumerate(contacts, 1)
                }

                # Wait for completion
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"  ❌ Unexpected error: {e}")

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print screening summary and usage stats."""
        print("=" * 80)
        print("SCREENING SUMMARY")
        print("=" * 80)
        print(f"Total Screened: {self.total_screened}")
        print(f"Qualified: {self.total_qualified} ({self.total_qualified/self.total_screened*100:.1f}%)" if self.total_screened > 0 else "Qualified: 0")
        print(f"Not Qualified: {self.total_failed} ({self.total_failed/self.total_screened*100:.1f}%)" if self.total_screened > 0 else "Not Qualified: 0")

        if self.errors:
            print(f"\n⚠️  Errors: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  - {error['name']}: {error['error']}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more")

        # Print Azure usage
        self.azure_client.print_usage()

        if self.total_qualified > 0 and not self.dry_run:
            print("\n" + "=" * 80)
            print("NEXT STEP")
            print("=" * 80)
            print(f"✅ {self.total_qualified} prospects qualified for Perplexity research!")
            print(f"Run: python step_2_perplexity_research.py")
            print("=" * 80 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Screen contacts for donor capacity using Azure GPT-5.1-mini'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of contacts to screen (for testing)'
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
        help='Number of parallel workers (default: 1, recommended: 50-80 for full rate limit)'
    )

    args = parser.parse_args()

    try:
        screener = DonorScreener(dry_run=args.dry_run, workers=args.workers)
        screener.run(limit=args.limit)
    except KeyboardInterrupt:
        print("\n\n⚠️  Screening interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
