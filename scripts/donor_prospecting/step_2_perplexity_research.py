#!/usr/bin/env python3
"""
Step 2: Perplexity Research - Deep Web Research on Qualified Prospects

Performs comprehensive web research using Perplexity API on prospects who
passed initial screening. Uses multi-query search (5 queries per prospect)
for comprehensive coverage.

Usage:
    python step_2_perplexity_research.py [--limit N] [--dry-run] [--scope SCOPE] [--workers N]
"""

import os
import sys
import argparse
import threading
from typing import Optional
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from perplexity_client import PerplexityClient

load_dotenv(override=True)


class DonorResearcher:
    """Handles Perplexity research for qualified donor prospects."""

    def __init__(self, dry_run: bool = False, scope: str = "comprehensive", workers: int = 1):
        """Initialize researcher with Perplexity and Supabase clients."""
        self.dry_run = dry_run
        self.scope = scope
        self.workers = workers

        # Initialize Perplexity client
        print(f"Initializing Perplexity client (scope: {scope})...")
        self.perplexity = PerplexityClient()

        # Initialize Supabase client
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)

        # Stats tracking (thread-safe)
        self._lock = threading.Lock()
        self.total_researched = 0
        self.total_with_results = 0
        self.total_no_results = 0
        self.errors = []

    def get_qualified_prospects(self, limit: Optional[int] = None):
        """
        Fetch qualified prospects who need Perplexity research.

        Returns contacts who passed screening but haven't been researched yet.
        """
        query = (self.supabase.table('contacts')
                 .select('*')
                 .eq('initial_screening_passed', True)
                 .is_('perplexity_enriched_at', 'null'))

        # Override Supabase default limit
        if limit:
            query = query.limit(limit)
        else:
            query = query.limit(10000)

        result = query.execute()
        return result.data

    def prepare_contact_context(self, contact: dict) -> dict:
        """Extract contact information for research query."""
        return {
            'name': f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
            'company': contact.get('enrich_current_company') or contact.get('company'),
            'title': contact.get('enrich_current_title') or contact.get('position'),
            'headline': contact.get('headline'),
            'location': contact.get('location_name') or contact.get('city'),
            'education': ', '.join(contact.get('enrich_schools', [])[:2]) if contact.get('enrich_schools') else None
        }

    def research_prospect(self, contact: dict) -> Optional[dict]:
        """
        Conduct Perplexity research on a prospect.

        Returns research result dict or None if error.
        """
        try:
            # Prepare context
            context = self.prepare_contact_context(contact)

            # Call Perplexity API
            result = self.perplexity.research_donor(
                name=context['name'],
                company=context['company'],
                title=context['title'],
                education=context['education'],
                location=context['location'],
                scope=self.scope
            )

            return result

        except Exception as e:
            print(f"  ❌ Error researching {context['name']}: {e}")
            self.errors.append({
                'contact_id': contact['id'],
                'name': context['name'],
                'error': str(e)
            })
            return None

    def update_contact(self, contact_id: int, result: dict):
        """Update contact record with research results."""
        if self.dry_run:
            print(f"  [DRY RUN] Would update contact {contact_id}")
            return

        # Extract sources as array of URLs
        sources = []
        if result.get('sources'):
            # Handle sources as either strings or dicts
            for s in result['sources']:
                if isinstance(s, str):
                    sources.append(s)
                elif isinstance(s, dict) and s.get('url'):
                    sources.append(s['url'])

        update_data = {
            'perplexity_enriched_at': datetime.now(timezone.utc).isoformat(),
            'perplexity_research_data': {
                'content': result.get('content'),
                'model': result.get('model'),
                'usage': result.get('usage')
            },
            'perplexity_sources': sources
        }

        self.supabase.table('contacts').update(update_data).eq('id', contact_id).execute()

    def _process_prospect(self, prospect: dict, index: int, total: int) -> bool:
        """Process a single prospect (for parallel execution)."""
        name = f"{prospect.get('first_name', '')} {prospect.get('last_name', '')}".strip()

        result = self.research_prospect(prospect)

        if result and result.get('content'):
            content_length = len(result['content'])
            source_count = len(result.get('sources', []))

            # Update stats (thread-safe)
            with self._lock:
                self.total_researched += 1
                if content_length > 200:
                    self.total_with_results += 1
                else:
                    self.total_no_results += 1

                # Print progress every 5 prospects
                if self.total_researched % 5 == 0:
                    print(f"Progress: {self.total_researched}/{total} researched, {self.total_with_results} with meaningful results ({self.total_with_results/self.total_researched*100:.1f}%)")

            # Update database
            self.update_contact(prospect['id'], result)
            return True

        return False

    def run(self, limit: Optional[int] = None):
        """Run the research process."""
        print("\n" + "=" * 80)
        print("DONOR PROSPECTING - STEP 2: PERPLEXITY RESEARCH")
        print("=" * 80)
        if self.workers > 1:
            print(f"Running with {self.workers} parallel workers (multi-query: 5 queries/prospect)")
        else:
            print(f"Running single-threaded (multi-query: 5 queries/prospect)")

        # Fetch qualified prospects
        print(f"\nFetching qualified prospects{f' (limit: {limit})' if limit else ''}...")
        prospects = self.get_qualified_prospects(limit)

        if not prospects:
            print("✅ No prospects need research!")
            return

        print(f"Found {len(prospects)} qualified prospects to research")

        # Estimate cost (5 queries per prospect with comprehensive scope)
        if self.scope == "comprehensive":
            estimated_cost = len(prospects) * 0.06  # ~$0.06 per prospect (5 queries * $0.012 per query)
            print(f"Estimated cost: ${estimated_cost:.2f} ({self.scope}, 5 queries per prospect)\n")
        else:
            estimated_cost = len(prospects) * 0.024  # ~$0.024 per prospect (2-3 queries)
            print(f"Estimated cost: ${estimated_cost:.2f} ({self.scope})\n")

        if self.workers == 1:
            # Single-threaded execution
            for i, prospect in enumerate(prospects, 1):
                name = f"{prospect.get('first_name', '')} {prospect.get('last_name', '')}".strip()
                company = prospect.get('enrich_current_company') or prospect.get('company') or 'Unknown'

                print(f"[{i}/{len(prospects)}] Researching: {name} ({company})")
                self._process_prospect(prospect, i, len(prospects))
                print()
        else:
            # Parallel execution
            print(f"Starting parallel processing with {self.workers} workers...\n")

            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = {
                    executor.submit(self._process_prospect, prospect, i, len(prospects)): prospect
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
        """Print research summary and usage stats."""
        print("=" * 80)
        print("RESEARCH SUMMARY")
        print("=" * 80)
        print(f"Total Researched: {self.total_researched}")
        print(f"With Results: {self.total_with_results} ({self.total_with_results/self.total_researched*100:.1f}%)" if self.total_researched > 0 else "With Results: 0")
        print(f"Limited/No Results: {self.total_no_results} ({self.total_no_results/self.total_researched*100:.1f}%)" if self.total_researched > 0 else "Limited/No Results: 0")

        if self.errors:
            print(f"\n⚠️  Errors: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  - {error['name']}: {error['error']}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more")

        # Print Perplexity usage
        self.perplexity.print_usage()

        if self.total_with_results > 0 and not self.dry_run:
            print("\n" + "=" * 80)
            print("NEXT STEP")
            print("=" * 80)
            print(f"✅ {self.total_with_results} prospects enriched with web research!")
            print(f"Run: python step_3_structure_output.py")
            print("=" * 80 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Research qualified prospects using Perplexity API'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of prospects to research (for testing)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without updating database'
    )
    parser.add_argument(
        '--scope',
        choices=['quick', 'deep', 'comprehensive'],
        default='comprehensive',
        help='Research scope (default: comprehensive)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of parallel workers (default: 1, recommended: 5-10 for Perplexity rate limits)'
    )

    args = parser.parse_args()

    try:
        researcher = DonorResearcher(dry_run=args.dry_run, scope=args.scope, workers=args.workers)
        researcher.run(limit=args.limit)
    except KeyboardInterrupt:
        print("\n\n⚠️  Research interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
