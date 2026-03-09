#!/usr/bin/env python3
"""
Fix misclassified ReserveCalifornia cancellations.

ReserveCalifornia has two cancellation email patterns the audit missed:
1. Cancellation "Confirmation" emails — subject is "Confirmation" but body
   contains negative quantities (Quantity: -N) and "Refund Total"
2. Park-initiated cancellations — subject is "Your Reserve California
   Reservation - Cancellation" (different subject, not in original search)

This script:
1. Finds all "completed" ReserveCalifornia reservations
2. Searches Gmail for ALL emails matching each reservation number
3. Checks for cancellation signals in any unfound emails
4. Updates the DB

Usage:
  python -u scripts/intelligence/fix_reservecalifornia_cancellations.py
  python -u scripts/intelligence/fix_reservecalifornia_cancellations.py --dry-run
"""

import os
import sys
import json
import re
import base64
import argparse

from dotenv import load_dotenv
from supabase import create_client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()

CREDENTIALS_DIR = os.path.expanduser("~/.google_workspace_mcp/credentials")


def load_gmail_service(account_email: str):
    cred_path = os.path.join(CREDENTIALS_DIR, f"{account_email}.json")
    if not os.path.exists(cred_path):
        return None
    with open(cred_path) as f:
        data = json.load(f)
    creds = Credentials(
        token=data.get("access_token") or data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
    )
    return build("gmail", "v1", credentials=creds)


def get_email_text(gmail, msg_id):
    """Fetch a single email and return (subject, body_text)."""
    msg = gmail.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
    subject = headers.get("subject", "")
    body = _extract_body(msg["payload"])
    return subject, body


def _extract_body(payload):
    parts = []
    def _walk(p):
        mime = p.get("mimeType", "")
        if mime == "text/plain":
            data = p.get("body", {}).get("data", "")
            if data:
                parts.append(base64.urlsafe_b64decode(data).decode("utf-8", errors="replace"))
        elif mime == "text/html" and not parts:
            data = p.get("body", {}).get("data", "")
            if data:
                from bs4 import BeautifulSoup
                html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                parts.append(BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True))
        for child in p.get("parts", []):
            _walk(child)
    _walk(payload)
    return "\n".join(parts)[:4000]


def is_cancellation_email(subject, body):
    """Detect ReserveCalifornia cancellation signals.

    IMPORTANT: ReserveCalifornia modification emails also have negative quantities
    (for the removed nights) but include [New Reservation] blocks and positive
    quantities for the new dates. These are NOT cancellations.

    True cancellations have:
    - "Refund Total" (not "Grand Total")
    - "CANCELLED" status in body
    - Explicit "Cancellation" in subject
    - Only negative quantities (no positive Quantity: N lines)

    Modifications have:
    - [Original Reservation] + [New Reservation] blocks
    - Both negative AND positive quantities
    - "Grand Total" (not "Refund Total")
    - Modification/Change fee
    """
    subject_lower = subject.lower()
    body_lower = body.lower()

    # Strong cancellation signals — check FIRST, before modification check
    # These override [New Reservation] blocks since a cancellation of a
    # previously-modified reservation still shows [Original]/[New] context.

    # Pattern: Explicit cancellation subject
    if "cancellation" in subject_lower:
        return True, "explicit_cancellation_subject"

    # Pattern: "Refund Total" in body — definitive cancellation signal.
    # Modifications use "Grand Total", cancellations use "Refund Total".
    if "refund total" in body_lower:
        return True, "refund_total_in_body"

    # Pattern: Explicit cancellation language in body
    if "has been cancelled" in body_lower or "has been canceled" in body_lower:
        return True, "cancelled_in_body"

    # Pattern: Status: CANCELLED in body
    if "status: cancelled" in body_lower or "status:cancelled" in body_lower:
        return True, "status_cancelled_in_body"

    # If it has [New Reservation] + "Grand Total", it's a modification
    if "[new reservation]" in body_lower:
        return False, None

    # Pattern: Negative quantities WITHOUT any positive campsite quantities
    # (modifications have both negative and positive)
    has_negative = bool(re.search(r'Quantity:\s*-\d+', body))
    has_positive = bool(re.search(r'Quantity:\s+\d+', body))  # positive (no minus)
    if has_negative and not has_positive:
        return True, "negative_quantity_only"

    return False, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reaudit", action="store_true",
                        help="Re-check ALL ReserveCalifornia reservations (both completed and cancelled)")
    args = parser.parse_args()

    sb_url = os.environ["SUPABASE_URL"]
    sb_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    supabase = create_client(sb_url, sb_key)

    # Get ReserveCalifornia reservations
    statuses = ["completed", "cancelled"] if args.reaudit else ["completed"]
    status_label = "completed + cancelled" if args.reaudit else "completed"
    print(f"Finding {status_label} ReserveCalifornia reservations...")
    all_rows = []
    offset = 0
    page_size = 1000
    while True:
        resp = supabase.table("camping_reservations") \
            .select("id, reservation_number, campground_name, check_in_date, check_out_date, num_nights, total_cost, status, provider, account_email, gmail_message_ids") \
            .in_("status", statuses) \
            .in_("provider", ["reserve_california", "itinio"]) \
            .order("check_in_date") \
            .range(offset, offset + page_size - 1) \
            .execute()
        all_rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size

    # Filter out calendar cross-references (no real reservation number)
    rows = [r for r in all_rows if not r["reservation_number"].startswith("CAL-")]
    print(f"  {len(rows)} completed ReserveCalifornia reservations (excluding calendar-only)\n")

    # Build Gmail services per account
    gmail_cache = {}

    def get_gmail(acct):
        if acct not in gmail_cache:
            gmail_cache[acct] = load_gmail_service(acct)
            if gmail_cache[acct]:
                print(f"  Gmail connected: {acct}")
        return gmail_cache[acct]

    # Check each reservation
    to_cancel = []    # (id, res_num, campground, reason) — completed → cancelled
    to_restore = []   # (id, res_num, campground, reason) — cancelled → completed (false positives)
    checked = 0
    skipped = 0

    for i, row in enumerate(rows, 1):
        rid = row["id"]
        res_num = row["reservation_number"]
        campground = row["campground_name"]
        acct = row["account_email"]
        current_status = row["status"]
        stored_ids = set(row.get("gmail_message_ids") or [])

        gmail = get_gmail(acct)
        if not gmail:
            skipped += 1
            continue

        # Search Gmail for ALL emails with this reservation number
        try:
            result = gmail.users().messages().list(
                userId="me", q=f"from:usedirect.com {res_num}", maxResults=10
            ).execute()
            gmail_ids = set(m["id"] for m in result.get("messages", []))
        except Exception as e:
            print(f"  [{i}] ERROR searching {res_num}: {e}")
            skipped += 1
            continue

        # Also search for park-initiated cancellation emails
        try:
            result2 = gmail.users().messages().list(
                userId="me",
                q=f"from:usedirect.com subject:cancellation {res_num}",
                maxResults=5
            ).execute()
            gmail_ids.update(m["id"] for m in result2.get("messages", []))
        except Exception:
            pass

        all_msg_ids = gmail_ids | stored_ids
        checked += 1

        if not all_msg_ids:
            continue

        # Check ALL emails (stored + new) for cancellation signals
        found_cancel = False
        cancel_reason = None

        for msg_id in all_msg_ids:
            try:
                subject, body = get_email_text(gmail, msg_id)
                is_cancel, reason = is_cancellation_email(subject, body)
                if is_cancel:
                    found_cancel = True
                    cancel_reason = reason
                    break
            except Exception:
                pass

        # Determine if status needs to change
        should_be = "cancelled" if found_cancel else "completed"

        if should_be != current_status:
            if should_be == "cancelled":
                to_cancel.append((rid, res_num, campground, cancel_reason))
                print(f"  [{i}/{len(rows)}] {res_num:>12}  {campground:<50}  CANCEL ({cancel_reason})")
            else:
                to_restore.append((rid, res_num, campground, "no_cancellation_signal"))
                print(f"  [{i}/{len(rows)}] {res_num:>12}  {campground:<50}  RESTORE (was false positive)")

    print(f"\n  Checked: {checked}, Skipped: {skipped}")
    print(f"  Found {len(to_cancel)} to cancel, {len(to_restore)} to restore\n")

    if not to_cancel and not to_restore:
        print("  No changes needed. Done.")
        return

    if to_cancel:
        print("  Will CANCEL:")
        for rid, res_num, cg, reason in to_cancel:
            print(f"    [{rid}] {res_num} {cg} — {reason}")
    if to_restore:
        print("  Will RESTORE to completed:")
        for rid, res_num, cg, reason in to_restore:
            print(f"    [{rid}] {res_num} {cg}")

    if args.dry_run:
        print("\n  DRY RUN — no changes made.")
        return

    # Update DB — cancellations
    saved = 0
    if to_cancel:
        print(f"\n  Cancelling {len(to_cancel)} reservations...")
        for rid, res_num, cg, reason in to_cancel:
            try:
                supabase.table("camping_reservations").update({
                    "status": "cancelled",
                    "was_cancelled": True,
                }).eq("id", rid).execute()
                saved += 1
            except Exception as e:
                print(f"    Error updating {rid}: {e}")

    # Update DB — restorations
    restored = 0
    if to_restore:
        print(f"  Restoring {len(to_restore)} reservations to completed...")
        for rid, res_num, cg, reason in to_restore:
            try:
                supabase.table("camping_reservations").update({
                    "status": "completed",
                    "was_cancelled": False,
                }).eq("id", rid).execute()
                restored += 1
            except Exception as e:
                print(f"    Error updating {rid}: {e}")

    print(f"  Cancelled: {saved}, Restored: {restored}")

    # Verify
    print("\n  Final counts:")
    for status in ["completed", "cancelled", "confirmed"]:
        resp = supabase.table("camping_reservations") \
            .select("id", count="exact") \
            .eq("status", status) \
            .execute()
        print(f"    {status}: {resp.count}")


if __name__ == "__main__":
    main()
