#!/usr/bin/env python3
"""
Network Intelligence — Rebuild Communication Summary

Aggregates communication data across all channels (email, LinkedIn DM, SMS)
per contact from the unified `contact_email_threads` table and stores a
structured `comms_summary` JSONB on the contacts table.

Usage:
  python scripts/intelligence/rebuild_comms_summary.py --test          # Preview 5 contacts
  python scripts/intelligence/rebuild_comms_summary.py --contact-id 42 # Single contact
  python scripts/intelligence/rebuild_comms_summary.py                 # Full run
"""

import os
import sys
import json
import argparse
from collections import defaultdict
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def build_chronological_summary(channel_data: dict) -> str:
    """Build a human-readable chronological summary of communication activity.

    Groups activity by year and month, e.g.:
    "3 emails in 2024, 1 LinkedIn DM in Jan 2025, 2 SMS in Feb 2026"
    """
    # Collect all threads with their dates and channels
    events = []
    for channel, threads in channel_data.items():
        for t in threads:
            last_date = t.get("last_message_date")
            if not last_date:
                continue
            # Parse date string to extract year/month
            try:
                if isinstance(last_date, str):
                    dt = datetime.fromisoformat(last_date.replace("Z", "+00:00"))
                else:
                    dt = last_date
                events.append((dt.year, dt.month, channel))
            except (ValueError, AttributeError):
                continue

    if not events:
        return "No dated communication"

    # Group by (year, channel) for concise summary
    year_channel_counts = defaultdict(int)
    for year, month, channel in events:
        year_channel_counts[(year, channel)] += 1

    # Sort by year
    sorted_keys = sorted(year_channel_counts.keys())

    # Build readable parts
    channel_labels = {
        "email": "email",
        "linkedin": "LinkedIn DM",
        "sms": "SMS",
    }

    # For the most recent year, break down by month for more detail
    current_year = max(y for y, _ in sorted_keys) if sorted_keys else None

    parts = []
    for year, channel in sorted_keys:
        count = year_channel_counts[(year, channel)]
        label = channel_labels.get(channel, channel)
        plural = "s" if count != 1 and label == "email" else ""
        if label == "LinkedIn DM" and count != 1:
            plural = "s"
        elif label == "SMS":
            plural = ""  # SMS is already plural

        if year == current_year:
            # For current year, get month breakdown
            month_counts = defaultdict(int)
            for y, m, c in events:
                if y == year and c == channel:
                    month_counts[m] += 1

            month_names = {
                1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
                5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
                9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
            }

            if len(month_counts) <= 3:
                # Few months — list them
                for m in sorted(month_counts.keys()):
                    mc = month_counts[m]
                    p = "s" if mc != 1 and label == "email" else ""
                    if label == "LinkedIn DM" and mc != 1:
                        p = "s"
                    elif label == "SMS":
                        p = ""
                    parts.append(f"{mc} {label}{p} in {month_names[m]} {year}")
            else:
                parts.append(f"{count} {label}{plural} in {year}")
        else:
            parts.append(f"{count} {label}{plural} in {year}")

    return ", ".join(parts)


class CommsSummaryBuilder:
    """Aggregates communication data per contact and writes comms_summary JSONB."""

    def __init__(self, test_mode=False, contact_id=None):
        self.test_mode = test_mode
        self.contact_id = contact_id
        self.supabase: Client | None = None
        self.stats = {
            "contacts_processed": 0,
            "contacts_updated": 0,
            "contacts_no_threads": 0,
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

    def get_all_threads(self) -> dict[int, list[dict]]:
        """Fetch all threads from contact_email_threads, grouped by contact_id."""
        all_threads = []
        page_size = 1000
        offset = 0

        select_cols = (
            "contact_id, channel, is_group, direction, message_count, "
            "first_message_date, last_message_date, participant_count"
        )

        while True:
            query = (
                self.supabase.table("contact_email_threads")
                .select(select_cols)
                .order("contact_id")
                .range(offset, offset + page_size - 1)
            )

            if self.contact_id:
                query = query.eq("contact_id", self.contact_id)

            page = query.execute().data
            if not page:
                break
            all_threads.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        print(f"Fetched {len(all_threads)} thread rows")

        # Group by contact_id
        grouped = defaultdict(list)
        for t in all_threads:
            grouped[t["contact_id"]].append(t)

        return dict(grouped)

    def build_summary(self, contact_id: int, threads: list[dict]) -> dict:
        """Build the comms_summary JSONB for one contact."""
        # Organize by channel
        by_channel: dict[str, list[dict]] = defaultdict(list)
        for t in threads:
            by_channel[t.get("channel", "email")].append(t)

        total_threads = len(threads)
        total_messages = sum(t.get("message_count", 0) or 0 for t in threads)

        # Compute per-channel stats
        channels = {}
        all_dates = []

        for channel, ch_threads in by_channel.items():
            ch_messages = sum(t.get("message_count", 0) or 0 for t in ch_threads)
            ch_first_dates = []
            ch_last_dates = []

            bidirectional = 0
            inbound = 0
            outbound = 0
            group_threads = 0

            for t in ch_threads:
                d = t.get("direction", "")
                if d == "bidirectional":
                    bidirectional += 1
                elif d in ("received", "inbound"):
                    inbound += 1
                elif d in ("sent", "outbound"):
                    outbound += 1

                if t.get("is_group"):
                    group_threads += 1

                fd = t.get("first_message_date")
                ld = t.get("last_message_date")
                if fd:
                    fd_str = fd if isinstance(fd, str) else fd.isoformat()
                    ch_first_dates.append(fd_str)
                    all_dates.append(fd_str)
                if ld:
                    ld_str = ld if isinstance(ld, str) else ld.isoformat()
                    ch_last_dates.append(ld_str)
                    all_dates.append(ld_str)

            ch_first = min(ch_first_dates) if ch_first_dates else None
            ch_last = max(ch_last_dates) if ch_last_dates else None

            channels[channel] = {
                "threads": len(ch_threads),
                "messages": ch_messages,
                "first_date": ch_first,
                "last_date": ch_last,
                "bidirectional": bidirectional,
                "inbound": inbound,
                "outbound": outbound,
                "group_threads": group_threads,
            }

        overall_first = min(all_dates) if all_dates else None
        overall_last = max(all_dates) if all_dates else None

        # Bidirectional percentage
        bidir_count = sum(
            1 for t in threads if t.get("direction") == "bidirectional"
        )
        bidirectional_pct = round(bidir_count / total_threads * 100, 1) if total_threads > 0 else 0.0

        # Group thread percentage (email only)
        email_threads = by_channel.get("email", [])
        email_group = sum(1 for t in email_threads if t.get("is_group"))
        group_thread_pct = round(email_group / len(email_threads) * 100, 1) if email_threads else 0.0

        # Most recent channel
        most_recent_channel = None
        most_recent_date = None
        for channel, stats in channels.items():
            ld = stats.get("last_date")
            if ld and (most_recent_date is None or ld > most_recent_date):
                most_recent_date = ld
                most_recent_channel = channel

        # Chronological summary
        chronological_summary = build_chronological_summary(by_channel)

        return {
            "total_threads": total_threads,
            "total_messages": total_messages,
            "channels": channels,
            "overall_first_date": overall_first,
            "overall_last_date": overall_last,
            "bidirectional_pct": bidirectional_pct,
            "group_thread_pct": group_thread_pct,
            "most_recent_channel": most_recent_channel,
            "chronological_summary": chronological_summary,
        }

    def save_summary(self, contact_id: int, summary: dict) -> bool:
        """Write comms_summary, comms_last_date, comms_thread_count to contacts."""
        try:
            # Extract last date as date only (YYYY-MM-DD)
            last_date = summary.get("overall_last_date")
            if last_date:
                last_date = last_date[:10]  # Take YYYY-MM-DD portion

            self.supabase.table("contacts").update({
                "comms_summary": summary,
                "comms_last_date": last_date,
                "comms_thread_count": summary["total_threads"],
            }).eq("id", contact_id).execute()
            return True
        except Exception as e:
            print(f"  ERROR saving contact {contact_id}: {e}")
            self.stats["errors"] += 1
            return False

    def run(self):
        if not self.connect():
            return False

        # Fetch all threads
        grouped = self.get_all_threads()
        total_contacts = len(grouped)
        print(f"Found {total_contacts} contacts with threads")

        if total_contacts == 0:
            print("No contacts with threads found")
            return True

        # In test mode, limit to 5 contacts
        contact_ids = sorted(grouped.keys())
        if self.test_mode:
            contact_ids = contact_ids[:5]
            print(f"TEST MODE: Processing {len(contact_ids)} contacts (preview only)")

        for i, cid in enumerate(contact_ids):
            threads = grouped[cid]
            summary = self.build_summary(cid, threads)
            self.stats["contacts_processed"] += 1

            if self.test_mode:
                # Print preview without saving
                print(f"\n--- Contact {cid} ({len(threads)} threads) ---")
                print(f"  Total messages: {summary['total_messages']}")
                print(f"  Channels: {list(summary['channels'].keys())}")
                print(f"  First date: {summary['overall_first_date']}")
                print(f"  Last date: {summary['overall_last_date']}")
                print(f"  Bidirectional %: {summary['bidirectional_pct']}")
                print(f"  Group thread %: {summary['group_thread_pct']}")
                print(f"  Most recent channel: {summary['most_recent_channel']}")
                print(f"  Chronological: {summary['chronological_summary']}")
                for ch, stats in summary["channels"].items():
                    print(f"  {ch}: {stats['threads']} threads, {stats['messages']} msgs, "
                          f"bidir={stats['bidirectional']}, in={stats['inbound']}, out={stats['outbound']}, "
                          f"group={stats['group_threads']}")
            else:
                if self.save_summary(cid, summary):
                    self.stats["contacts_updated"] += 1

                if (i + 1) % 100 == 0 or (i + 1) == len(contact_ids):
                    print(f"  Progress: {i + 1}/{len(contact_ids)} "
                          f"(updated={self.stats['contacts_updated']}, errors={self.stats['errors']})")

        # Print summary
        print("\n" + "=" * 50)
        print("COMMS SUMMARY REBUILD")
        print("=" * 50)
        print(f"  Contacts processed:  {self.stats['contacts_processed']}")
        print(f"  Contacts updated:    {self.stats['contacts_updated']}")
        print(f"  Errors:              {self.stats['errors']}")
        print("=" * 50)
        return self.stats["errors"] == 0


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild comms_summary JSONB for all contacts from unified threads table"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Preview 5 contacts without writing to DB")
    parser.add_argument("--contact-id", "-c", type=int, default=None,
                        help="Process a single contact by ID")
    args = parser.parse_args()

    builder = CommsSummaryBuilder(
        test_mode=args.test,
        contact_id=args.contact_id,
    )
    success = builder.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
