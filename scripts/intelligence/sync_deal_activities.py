#!/usr/bin/env python3
"""
Deal Activity Sync — Auto-tag emails, meetings, and calls to active deals.

Scans active deals (not won/lost), finds their contact's recent communications
from contact_email_threads, contact_calendar_events, and contact_call_logs,
then writes them to the deal_activities table with dedup via UNIQUE constraint.

Usage:
  python scripts/intelligence/sync_deal_activities.py --dry-run          # Preview
  python scripts/intelligence/sync_deal_activities.py --recent-days 90   # Backfill
  python scripts/intelligence/sync_deal_activities.py --recent-days 7    # Daily sync
  python scripts/intelligence/sync_deal_activities.py --deal-id UUID     # Single deal
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


class DealActivitySyncer:
    """Syncs communications from contact-level tables into deal_activities."""

    def __init__(self, recent_days=30, deal_id=None, dry_run=False):
        self.recent_days = recent_days
        self.deal_id = deal_id
        self.dry_run = dry_run
        self.supabase: Client | None = None
        self.stats = {
            "deals_scanned": 0,
            "deals_with_contact": 0,
            "emails_found": 0,
            "meetings_found": 0,
            "calls_found": 0,
            "activities_inserted": 0,
            "activities_skipped_dup": 0,
            "errors": 0,
        }

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        self.supabase = create_client(url, key)
        print("Connected to Supabase")
        return True

    def fetch_active_deals(self) -> list[dict]:
        """Get deals that are not won/lost and have a contact_id."""
        query = (
            self.supabase.table("deals")
            .select("id, contact_id, title, stage, pipeline_id")
            .not_.is_("contact_id", "null")
        )

        if self.deal_id:
            query = query.eq("id", self.deal_id)
        else:
            # Active deals only — exclude terminal stages
            query = query.not_.in_("stage", ["won", "lost"])

        deals = query.execute().data
        return deals or []

    def _cutoff_date(self) -> str:
        """ISO string for the cutoff date."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.recent_days)
        return cutoff.isoformat()

    def _paginated_fetch(self, table: str, select_cols: str,
                         contact_id: int, date_col: str) -> list[dict]:
        """Paginated fetch from a comms table filtered by contact and date."""
        cutoff = self._cutoff_date()
        all_rows = []
        page_size = 1000
        offset = 0

        while True:
            page = (
                self.supabase.table(table)
                .select(select_cols)
                .eq("contact_id", contact_id)
                .gte(date_col, cutoff)
                .order(date_col, desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
                .data
            )
            if not page:
                break
            all_rows.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        return all_rows

    def fetch_emails(self, contact_id: int) -> list[dict]:
        """Fetch recent email threads for a contact."""
        return self._paginated_fetch(
            "contact_email_threads",
            "id, contact_id, account_email, subject, summary, direction, "
            "message_count, last_message_date, is_group, participant_count",
            contact_id,
            "last_message_date",
        )

    def fetch_meetings(self, contact_id: int) -> list[dict]:
        """Fetch recent calendar events for a contact."""
        return self._paginated_fetch(
            "contact_calendar_events",
            "id, contact_id, account_email, summary, description, "
            "start_time, end_time, duration_minutes, location, "
            "event_type, attendee_count, is_organizer",
            contact_id,
            "start_time",
        )

    def fetch_calls(self, contact_id: int) -> list[dict]:
        """Fetch recent call logs for a contact."""
        return self._paginated_fetch(
            "contact_call_logs",
            "id, contact_id, phone_number, call_date, call_type, duration_seconds",
            contact_id,
            "call_date",
        )

    def _email_activity_type(self, direction: str | None) -> str:
        """Map email direction to activity_type."""
        if direction == "sent":
            return "email_sent"
        elif direction == "received":
            return "email_received"
        else:
            return "email_bidirectional"

    def build_activities(self, deal: dict) -> list[dict]:
        """Build activity rows for one deal from its contact's comms."""
        deal_id = deal["id"]
        contact_id = deal["contact_id"]
        activities = []

        # Emails
        emails = self.fetch_emails(contact_id)
        self.stats["emails_found"] += len(emails)
        for e in emails:
            activities.append({
                "deal_id": deal_id,
                "contact_id": contact_id,
                "activity_type": self._email_activity_type(e.get("direction")),
                "source_table": "contact_email_threads",
                "source_id": e["id"],
                "activity_date": e["last_message_date"],
                "subject": e.get("subject"),
                "summary": e.get("summary"),
                "account_email": e.get("account_email"),
                "metadata": json.dumps({
                    "direction": e.get("direction"),
                    "message_count": e.get("message_count"),
                    "is_group": e.get("is_group"),
                    "participant_count": e.get("participant_count"),
                }),
            })

        # Meetings
        meetings = self.fetch_meetings(contact_id)
        self.stats["meetings_found"] += len(meetings)
        for m in meetings:
            activities.append({
                "deal_id": deal_id,
                "contact_id": contact_id,
                "activity_type": "meeting",
                "source_table": "contact_calendar_events",
                "source_id": m["id"],
                "activity_date": m["start_time"],
                "subject": m.get("summary"),
                "summary": m.get("description"),
                "account_email": m.get("account_email"),
                "metadata": json.dumps({
                    "duration_minutes": m.get("duration_minutes"),
                    "attendee_count": m.get("attendee_count"),
                    "location": m.get("location"),
                    "event_type": m.get("event_type"),
                    "is_organizer": m.get("is_organizer"),
                }),
            })

        # Calls
        calls = self.fetch_calls(contact_id)
        self.stats["calls_found"] += len(calls)
        for c in calls:
            duration_sec = c.get("duration_seconds") or 0
            activities.append({
                "deal_id": deal_id,
                "contact_id": contact_id,
                "activity_type": "call",
                "source_table": "contact_call_logs",
                "source_id": c["id"],
                "activity_date": c["call_date"],
                "subject": f"{c.get('call_type', 'call').title()} call"
                           + (f" ({duration_sec // 60}m)" if duration_sec > 0 else ""),
                "summary": None,
                "account_email": None,
                "metadata": json.dumps({
                    "call_type": c.get("call_type"),
                    "duration_seconds": duration_sec,
                    "duration_minutes": round(duration_sec / 60, 1) if duration_sec else 0,
                    "phone_number": c.get("phone_number"),
                }),
            })

        return activities

    def upsert_activities(self, activities: list[dict]) -> int:
        """Insert activities with ON CONFLICT DO NOTHING. Returns inserted count."""
        if not activities:
            return 0

        # Batch insert — Supabase upsert with ignoreDuplicates
        inserted = 0
        batch_size = 100
        for i in range(0, len(activities), batch_size):
            batch = activities[i:i + batch_size]
            try:
                result = (
                    self.supabase.table("deal_activities")
                    .upsert(batch, on_conflict="deal_id,source_table,source_id",
                            ignore_duplicates=True)
                    .execute()
                )
                inserted += len(result.data) if result.data else 0
            except Exception as ex:
                print(f"  ERROR inserting batch: {ex}")
                self.stats["errors"] += 1

        return inserted

    def run(self):
        """Main sync loop."""
        print(f"\n{'='*60}")
        print(f"Deal Activity Sync — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"  Recent days: {self.recent_days}")
        print(f"  Deal filter: {self.deal_id or 'all active'}")
        print(f"  Dry run: {self.dry_run}")
        print(f"{'='*60}\n")

        deals = self.fetch_active_deals()
        self.stats["deals_scanned"] = len(deals)
        self.stats["deals_with_contact"] = len([d for d in deals if d.get("contact_id")])
        print(f"Found {len(deals)} active deal(s) with contacts\n")

        if not deals:
            print("No deals to process.")
            return

        total_activities = 0

        for deal in deals:
            title = deal["title"]
            contact_id = deal["contact_id"]
            print(f"  [{deal['stage']}] {title} (contact #{contact_id})")

            activities = self.build_activities(deal)

            if not activities:
                print(f"    No recent activity found")
                continue

            email_count = sum(1 for a in activities if a["source_table"] == "contact_email_threads")
            meeting_count = sum(1 for a in activities if a["source_table"] == "contact_calendar_events")
            call_count = sum(1 for a in activities if a["source_table"] == "contact_call_logs")
            print(f"    Found: {email_count} emails, {meeting_count} meetings, {call_count} calls")

            if self.dry_run:
                total_activities += len(activities)
                for a in activities[:3]:
                    print(f"      → {a['activity_type']}: {a.get('subject', '(no subject)')}")
                if len(activities) > 3:
                    print(f"      ... and {len(activities) - 3} more")
            else:
                inserted = self.upsert_activities(activities)
                skipped = len(activities) - inserted
                self.stats["activities_inserted"] += inserted
                self.stats["activities_skipped_dup"] += skipped
                total_activities += inserted
                print(f"    Inserted: {inserted}, skipped (dup): {skipped}")

        # Summary
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Deals scanned: {self.stats['deals_scanned']}")
        print(f"  Emails found: {self.stats['emails_found']}")
        print(f"  Meetings found: {self.stats['meetings_found']}")
        print(f"  Calls found: {self.stats['calls_found']}")
        if self.dry_run:
            print(f"  Total activities (dry run): {total_activities}")
        else:
            print(f"  Activities inserted: {self.stats['activities_inserted']}")
            print(f"  Duplicates skipped: {self.stats['activities_skipped_dup']}")
        if self.stats["errors"]:
            print(f"  Errors: {self.stats['errors']}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Sync deal activities from comms tables")
    parser.add_argument("--recent-days", type=int, default=30,
                        help="Look back N days for comms (default: 30)")
    parser.add_argument("--deal-id", type=str, default=None,
                        help="Sync a single deal by UUID")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without inserting")
    args = parser.parse_args()

    syncer = DealActivitySyncer(
        recent_days=args.recent_days,
        deal_id=args.deal_id,
        dry_run=args.dry_run,
    )

    if not syncer.connect():
        sys.exit(1)

    syncer.run()


if __name__ == "__main__":
    main()
