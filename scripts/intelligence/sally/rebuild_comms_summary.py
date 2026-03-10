#!/usr/bin/env python3
"""
Sally Network Intelligence — Rebuild Communication Summary

Aggregates communication data across all channels (email, LinkedIn DM, SMS,
calendar meetings) per contact from sally_contact_email_threads,
sally_contact_calendar_events, and sally_contact_sms_conversations tables.
Stores a structured `comms_summary` JSONB on sally_contacts.

Usage:
  python scripts/intelligence/sally/rebuild_comms_summary.py --test          # Preview 5 contacts
  python scripts/intelligence/sally/rebuild_comms_summary.py --contact-id 42 # Single contact
  python scripts/intelligence/sally/rebuild_comms_summary.py                 # Full run
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
    events = []
    for channel, threads in channel_data.items():
        for t in threads:
            last_date = t.get("last_message_date")
            if not last_date:
                continue
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

    year_channel_counts = defaultdict(int)
    for year, month, channel in events:
        year_channel_counts[(year, channel)] += 1

    sorted_keys = sorted(year_channel_counts.keys())

    channel_labels = {
        "email": "email",
        "linkedin": "LinkedIn DM",
        "sms": "SMS",
        "calendar": "meeting",
    }

    current_year = max(y for y, _ in sorted_keys) if sorted_keys else None

    parts = []
    for year, channel in sorted_keys:
        count = year_channel_counts[(year, channel)]
        label = channel_labels.get(channel, channel)
        plural = ""
        if count != 1 and label in ("email", "LinkedIn DM", "meeting"):
            plural = "s"

        if year == current_year:
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
                for m in sorted(month_counts.keys()):
                    mc = month_counts[m]
                    p = "s" if mc != 1 and label in ("email", "LinkedIn DM", "meeting") else ""
                    parts.append(f"{mc} {label}{p} in {month_names[m]} {year}")
            else:
                parts.append(f"{count} {label}{plural} in {year}")
        else:
            parts.append(f"{count} {label}{plural} in {year}")

    return ", ".join(parts)


class CommsSummaryBuilder:
    """Aggregates communication data per Sally contact and writes comms_summary JSONB."""

    def __init__(self, test_mode=False, contact_id=None, ids=None, force=False):
        self.test_mode = test_mode
        self.contact_id = contact_id
        self.ids = ids
        self.force = force
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

    def _paginated_fetch(self, table: str, select_cols: str) -> list[dict]:
        """Generic paginated fetch from a Supabase table."""
        all_rows = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                self.supabase.table(table)
                .select(select_cols)
                .order("contact_id")
                .range(offset, offset + page_size - 1)
            )

            if self.contact_id:
                query = query.eq("contact_id", self.contact_id)
            elif self.ids:
                query = query.in_("contact_id", self.ids)

            page = query.execute().data
            if not page:
                break
            all_rows.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        return all_rows

    def get_all_threads(self) -> dict[int, list[dict]]:
        """Fetch all threads from sally_contact_email_threads, grouped by contact_id."""
        select_cols = (
            "contact_id, channel, is_group, direction, message_count, "
            "first_message_date, last_message_date, participant_count"
        )
        all_threads = self._paginated_fetch("sally_contact_email_threads", select_cols)
        print(f"Fetched {len(all_threads)} email/LinkedIn thread rows")

        grouped = defaultdict(list)
        for t in all_threads:
            grouped[t["contact_id"]].append(t)
        return dict(grouped)

    def get_all_calendar_events(self) -> dict[int, list[dict]]:
        """Fetch all calendar events from sally_contact_calendar_events, grouped by contact_id."""
        select_cols = (
            "contact_id, start_time, duration_minutes, attendee_count, "
            "event_type, ical_uid"
        )
        all_events = self._paginated_fetch("sally_contact_calendar_events", select_cols)
        print(f"Fetched {len(all_events)} calendar event rows")

        grouped = defaultdict(list)
        for e in all_events:
            grouped[e["contact_id"]].append(e)
        return dict(grouped)

    def get_all_sms(self) -> dict[int, list[dict]]:
        """Fetch all SMS conversations from sally_contact_sms_conversations, grouped by contact_id."""
        select_cols = (
            "contact_id, message_count, sent_count, received_count, "
            "first_message_date, last_message_date"
        )
        all_sms = self._paginated_fetch("sally_contact_sms_conversations", select_cols)
        print(f"Fetched {len(all_sms)} SMS conversation rows")

        grouped = defaultdict(list)
        for s in all_sms:
            grouped[s["contact_id"]].append(s)
        return dict(grouped)

    def build_calendar_channel(self, events: list[dict]) -> dict:
        """Build channel stats for calendar events."""
        seen_uids = set()
        unique_events = []
        for e in events:
            uid = e.get("ical_uid")
            if uid and uid in seen_uids:
                continue
            if uid:
                seen_uids.add(uid)
            unique_events.append(e)

        dates = []
        group_count = 0
        total_minutes = 0

        for e in unique_events:
            st = e.get("start_time")
            if st:
                dates.append(st if isinstance(st, str) else st.isoformat())
            attendees = e.get("attendee_count", 0) or 0
            if attendees > 2:
                group_count += 1
            total_minutes += e.get("duration_minutes", 0) or 0

        first_date = min(dates) if dates else None
        last_date = max(dates) if dates else None
        count = len(unique_events)

        return {
            "threads": count,
            "messages": 0,
            "first_date": first_date,
            "last_date": last_date,
            "bidirectional": count,
            "inbound": 0,
            "outbound": 0,
            "group_threads": group_count,
            "total_duration_minutes": total_minutes,
        }

    def build_sms_channel(self, sms_convos: list[dict]) -> dict:
        """Build channel stats for SMS conversations."""
        total_messages = 0
        total_sent = 0
        total_received = 0
        dates = []

        for s in sms_convos:
            total_messages += s.get("message_count", 0) or 0
            total_sent += s.get("sent_count", 0) or 0
            total_received += s.get("received_count", 0) or 0
            fd = s.get("first_message_date")
            ld = s.get("last_message_date")
            if fd:
                dates.append(fd if isinstance(fd, str) else fd.isoformat())
            if ld:
                dates.append(ld if isinstance(ld, str) else ld.isoformat())

        first_date = min(dates) if dates else None
        last_date = max(dates) if dates else None

        # Determine directionality per conversation
        bidirectional = sum(1 for s in sms_convos
                           if (s.get("sent_count", 0) or 0) > 0 and (s.get("received_count", 0) or 0) > 0)
        outbound_only = sum(1 for s in sms_convos
                            if (s.get("sent_count", 0) or 0) > 0 and (s.get("received_count", 0) or 0) == 0)
        inbound_only = sum(1 for s in sms_convos
                           if (s.get("sent_count", 0) or 0) == 0 and (s.get("received_count", 0) or 0) > 0)

        return {
            "threads": len(sms_convos),
            "messages": total_messages,
            "first_date": first_date,
            "last_date": last_date,
            "bidirectional": bidirectional,
            "inbound": inbound_only,
            "outbound": outbound_only,
            "group_threads": 0,
        }

    def build_summary(self, contact_id: int, threads: list[dict]) -> dict:
        """Build the comms_summary JSONB for one contact from email/LinkedIn threads."""
        by_channel: dict[str, list[dict]] = defaultdict(list)
        for t in threads:
            by_channel[t.get("channel", "email")].append(t)

        total_threads = len(threads)
        total_messages = sum(t.get("message_count", 0) or 0 for t in threads)

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

        bidir_count = sum(
            1 for t in threads if t.get("direction") == "bidirectional"
        )
        bidirectional_pct = round(bidir_count / total_threads * 100, 1) if total_threads > 0 else 0.0

        email_threads = by_channel.get("email", [])
        email_group = sum(1 for t in email_threads if t.get("is_group"))
        group_thread_pct = round(email_group / len(email_threads) * 100, 1) if email_threads else 0.0

        most_recent_channel = None
        most_recent_date = None
        for channel, stats in channels.items():
            ld = stats.get("last_date")
            if ld and (most_recent_date is None or ld > most_recent_date):
                most_recent_date = ld
                most_recent_channel = channel

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
        """Write comms_summary and aggregate stats to sally_contacts."""
        try:
            last_date = summary.get("overall_last_date")
            if last_date:
                last_date = last_date[:10]

            update = {
                "comms_summary": summary,
                "comms_last_date": last_date,
                "comms_thread_count": summary["total_threads"],
            }

            # Calendar stats
            cal_ch = summary.get("channels", {}).get("calendar")
            if cal_ch:
                update["comms_meeting_count"] = cal_ch["threads"]
                update["comms_last_meeting"] = cal_ch["last_date"][:10] if cal_ch.get("last_date") else None

            self.supabase.table("sally_contacts").update(update).eq("id", contact_id).execute()
            return True
        except Exception as e:
            print(f"  ERROR saving contact {contact_id}: {e}")
            self.stats["errors"] += 1
            return False

    def run(self):
        if not self.connect():
            return False

        # Fetch all data sources
        threads_grouped = self.get_all_threads()
        calendar_grouped = self.get_all_calendar_events()
        sms_grouped = self.get_all_sms()

        # Merge all contact IDs across data sources
        all_contact_ids = set(threads_grouped.keys()) | set(calendar_grouped.keys()) | set(sms_grouped.keys())
        total_contacts = len(all_contact_ids)
        print(f"Found {total_contacts} contacts with communication data "
              f"(threads: {len(threads_grouped)}, calendar: {len(calendar_grouped)}, sms: {len(sms_grouped)})")

        if total_contacts == 0:
            print("No contacts with communication data found")
            return True

        contact_ids = sorted(all_contact_ids)
        if self.test_mode:
            contact_ids = contact_ids[:5]
            print(f"TEST MODE: Processing {len(contact_ids)} contacts (preview only)")

        for i, cid in enumerate(contact_ids):
            threads = threads_grouped.get(cid, [])
            cal_events = calendar_grouped.get(cid, [])
            sms_convos = sms_grouped.get(cid, [])

            summary = self.build_summary(cid, threads)

            # Add calendar channel if events exist
            if cal_events:
                cal_channel = self.build_calendar_channel(cal_events)
                summary["channels"]["calendar"] = cal_channel
                summary["total_threads"] += cal_channel["threads"]
                if cal_channel["first_date"]:
                    dates = [d for d in [summary["overall_first_date"], cal_channel["first_date"]] if d]
                    summary["overall_first_date"] = min(dates) if dates else None
                if cal_channel["last_date"]:
                    dates = [d for d in [summary["overall_last_date"], cal_channel["last_date"]] if d]
                    summary["overall_last_date"] = max(dates) if dates else None

            # Add SMS channel if conversations exist
            if sms_convos:
                sms_channel = self.build_sms_channel(sms_convos)
                summary["channels"]["sms"] = sms_channel
                summary["total_threads"] += sms_channel["threads"]
                summary["total_messages"] += sms_channel["messages"]
                if sms_channel["first_date"]:
                    dates = [d for d in [summary["overall_first_date"], sms_channel["first_date"]] if d]
                    summary["overall_first_date"] = min(dates) if dates else None
                if sms_channel["last_date"]:
                    dates = [d for d in [summary["overall_last_date"], sms_channel["last_date"]] if d]
                    summary["overall_last_date"] = max(dates) if dates else None

            # Recompute most recent channel with all channels
            most_recent_channel = None
            most_recent_date = None
            for channel, stats in summary["channels"].items():
                ld = stats.get("last_date")
                if ld and (most_recent_date is None or ld > most_recent_date):
                    most_recent_date = ld
                    most_recent_channel = channel
            summary["most_recent_channel"] = most_recent_channel

            # Rebuild chronological summary from raw data across all sources
            raw_by_channel = {}
            for t in threads:
                ch = t.get("channel", "email")
                raw_by_channel.setdefault(ch, []).append(t)
            for e in cal_events:
                raw_by_channel.setdefault("calendar", []).append({
                    "last_message_date": e.get("start_time"),
                })
            for s in sms_convos:
                raw_by_channel.setdefault("sms", []).append({
                    "last_message_date": s.get("last_message_date"),
                })
            summary["chronological_summary"] = build_chronological_summary(raw_by_channel)

            self.stats["contacts_processed"] += 1

            if self.test_mode:
                print(f"\n--- Contact {cid} ({len(threads)} threads, {len(cal_events)} events, {len(sms_convos)} SMS) ---")
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
        print("SALLY COMMS SUMMARY REBUILD")
        print("=" * 50)
        print(f"  Contacts processed:  {self.stats['contacts_processed']}")
        print(f"  Contacts updated:    {self.stats['contacts_updated']}")
        print(f"  Errors:              {self.stats['errors']}")
        print("=" * 50)
        return self.stats["errors"] == 0


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild comms_summary JSONB for Sally's contacts from unified comms tables"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Preview 5 contacts without writing to DB")
    parser.add_argument("--contact-id", "-c", type=int, default=None,
                        help="Process a single contact by ID")
    parser.add_argument("--ids", type=str, default=None,
                        help="Comma-separated contact IDs to process")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-process all contacts (currently same as default)")
    args = parser.parse_args()

    ids = [int(x.strip()) for x in args.ids.split(",")] if args.ids else None

    builder = CommsSummaryBuilder(
        test_mode=args.test,
        contact_id=args.contact_id,
        ids=ids,
        force=args.force,
    )
    success = builder.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
