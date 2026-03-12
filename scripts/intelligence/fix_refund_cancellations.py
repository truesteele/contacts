#!/usr/bin/env python3
"""
Fix misclassified cancellations — reservations marked "completed" that have
refund emails but no explicit cancellation email.

Recreation.gov doesn't always send a "Reservation Cancellation" email.
Sometimes the only signal is a "Refund Confirmation" email. This script:
1. Finds all "completed" reservations with refund emails but no cancellation email
2. Fetches all Gmail emails for each reservation number
3. Uses GPT-5 mini to determine true status (cancelled vs completed)
4. Updates the DB

Usage:
  python -u scripts/intelligence/fix_refund_cancellations.py
  python -u scripts/intelligence/fix_refund_cancellations.py --dry-run
"""

import os
import sys
import json
import re
import base64
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from supabase import create_client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()

CREDENTIALS_DIR = os.path.expanduser("~/.google_workspace_mcp/credentials")


class ReservationStatus(BaseModel):
    """GPT-5 mini output for determining true reservation status."""
    true_status: str = Field(description="cancelled or completed")
    refund_type: str = Field(description="full_cancellation, partial_cancellation, modification_refund, early_departure, or unknown")
    refund_amount: float = Field(default=0, description="Refund amount in dollars if found")
    total_cost: float = Field(default=0, description="Original total cost if found")
    reasoning: str = Field(description="Brief explanation of the determination")


def load_gmail_credentials(account_email: str):
    """Load OAuth credentials for a Gmail account."""
    cred_path = os.path.join(CREDENTIALS_DIR, f"{account_email}.json")
    if not os.path.exists(cred_path):
        return None
    with open(cred_path) as f:
        data = json.load(f)
    return Credentials(
        token=data.get("access_token") or data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
    )


def get_email_body(msg_payload):
    """Extract text body from Gmail message payload."""
    parts = []

    def _extract(payload):
        mime = payload.get("mimeType", "")
        if mime == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                parts.append(base64.urlsafe_b64decode(data).decode("utf-8", errors="replace"))
        elif mime == "text/html" and not parts:
            data = payload.get("body", {}).get("data", "")
            if data:
                from bs4 import BeautifulSoup
                html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                parts.append(BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True))
        for p in payload.get("parts", []):
            _extract(p)

    _extract(msg_payload)
    return "\n".join(parts)[:4000]  # Truncate to avoid token limits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without updating DB")
    args = parser.parse_args()

    sb_url = os.environ["SUPABASE_URL"]
    sb_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    supabase = create_client(sb_url, sb_key)
    openai = OpenAI(api_key=os.environ["OPENAI_APIKEY"])

    # Find suspect reservations: completed + refund email, no cancellation email
    print("Finding suspect reservations...")
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = supabase.table("camping_reservations") \
            .select("id, reservation_number, campground_name, check_in_date, check_out_date, num_nights, total_cost, status, provider, account_email, email_subjects, gmail_message_ids") \
            .eq("status", "completed") \
            .order("check_in_date") \
            .range(offset, offset + page_size - 1) \
            .execute()
        all_rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size

    # Filter: has refund email, no cancellation email
    suspects = []
    for r in all_rows:
        subjects = r.get("email_subjects") or []
        has_refund = any("refund" in s.lower() for s in subjects)
        has_cancel = any("cancel" in s.lower() or "closure" in s.lower() for s in subjects)
        if has_refund and not has_cancel:
            suspects.append(r)

    print(f"  {len(all_rows)} completed reservations total")
    print(f"  {len(suspects)} with refund email but no cancellation email\n")

    if not suspects:
        print("  No suspects found. Done.")
        return

    # Pre-load credentials for each account
    gmail_creds = {}
    accounts_needed = set(r["account_email"] for r in suspects)
    for acct in accounts_needed:
        creds = load_gmail_credentials(acct)
        if creds:
            gmail_creds[acct] = creds
            print(f"  Gmail credentials loaded: {acct}")

    # For each suspect, fetch all emails for that reservation and classify
    stats = {"input_tokens": 0, "output_tokens": 0}
    results = []  # (id, reservation_number, campground, old_status, new_status, reasoning)

    def classify_reservation(row):
        rid = row["id"]
        res_num = row["reservation_number"]
        acct = row["account_email"]
        campground = row["campground_name"]

        # Build Gmail service fresh each call to avoid segfault
        creds = gmail_creds.get(acct)
        if not creds:
            return (rid, res_num, campground, "completed", "completed", "No Gmail access")
        gmail = build("gmail", "v1", credentials=creds)

        # Search for all emails mentioning this reservation number
        email_texts = []

        # Use stored gmail_message_ids to fetch directly
        msg_ids = row.get("gmail_message_ids") or []
        for msg_id in msg_ids[:10]:  # Cap at 10 emails per reservation
            try:
                msg = gmail.users().messages().get(userId="me", id=msg_id, format="full").execute()
                headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
                subject = headers.get("subject", "")
                body = get_email_body(msg["payload"])
                email_texts.append(f"Subject: {subject}\n{body}")
            except Exception as e:
                pass

        if not email_texts:
            return (rid, res_num, campground, "completed", "completed", "Could not fetch emails")

        # Use GPT-5 mini to determine true status
        combined = "\n\n---EMAIL SEPARATOR---\n\n".join(email_texts)
        prompt = f"""Analyze these emails for camping reservation {res_num} at {campground}.
Check-in: {row['check_in_date']}, Check-out: {row['check_out_date']}, Nights: {row['num_nights']}
Recorded cost: {row.get('total_cost') or 'unknown'}

Determine the TRUE status of this reservation:
- "cancelled" if the reservation was cancelled/refunded (full refund = cancellation, refund without any indication the trip happened)
- "completed" if the trip was actually taken (e.g., modification refund for date change but trip still happened, or early departure partial refund)

Key signals:
- "Refund Confirmation" with full or near-full refund amount = CANCELLED
- "Refund Confirmation" + no "Reservation Reminder" close to trip date = likely CANCELLED (reminders stop if cancelled)
- "Reservation Reminder" 2 days before + no refund until after trip dates = likely COMPLETED
- Multiple refund amounts for modifications = trip may have been COMPLETED with changes
- "Location Closure" = CANCELLED by the park

Here are ALL the emails for this reservation:

{combined}"""

        try:
            resp = openai.responses.parse(
                model="gpt-5-mini",
                instructions="Determine whether a camping reservation was actually completed or was cancelled. Focus on refund emails, cancellation signals, and reminder timing.",
                input=prompt,
                text_format=ReservationStatus,
            )
            if resp.usage:
                stats["input_tokens"] += resp.usage.input_tokens
                stats["output_tokens"] += resp.usage.output_tokens
            if resp.output_parsed:
                result = resp.output_parsed
                return (rid, res_num, campground, "completed", result.true_status, result.reasoning)
        except Exception as e:
            return (rid, res_num, campground, "completed", "completed", f"Error: {e}")

        return (rid, res_num, campground, "completed", "completed", "No result")

    print(f"Classifying {len(suspects)} reservations with GPT-5 mini...\n")

    for i, row in enumerate(suspects, 1):
        result = classify_reservation(row)
        results.append(result)
        rid, res_num, campground, old_status, new_status, reasoning = result
        marker = "  CHANGED" if new_status != old_status else ""
        print(f"  [{i}/{len(suspects)}] {res_num:>15}  {campground:<40}  {old_status} → {new_status}{marker}")
        if new_status != old_status:
            print(f"    Reason: {reasoning}")

    # Summary
    changed = [(rid, res_num, cg, old, new, reason) for rid, res_num, cg, old, new, reason in results if old != new]
    unchanged = [r for r in results if r[4] == r[3]]
    print(f"\n  Results: {len(changed)} should be cancelled, {len(unchanged)} confirmed completed")

    if not changed:
        print("  No changes needed. Done.")
        return

    # Update DB
    if args.dry_run:
        print("\n  DRY RUN — no changes made.")
        print("\n  Would update:")
        for rid, res_num, cg, old, new, reason in changed:
            print(f"    [{rid}] {res_num} {cg} → {new}")
        return

    print(f"\n  Updating {len(changed)} reservations...")
    saved = 0
    errors = 0
    for rid, res_num, cg, old, new, reason in changed:
        try:
            supabase.table("camping_reservations").update({
                "status": "cancelled",
                "was_cancelled": True,
            }).eq("id", rid).execute()
            saved += 1
        except Exception as e:
            errors += 1
            print(f"    Error updating {rid}: {e}")

    print(f"  Saved: {saved}, Errors: {errors}")
    cost = (stats["input_tokens"] * 0.15 + stats["output_tokens"] * 0.60) / 1_000_000
    print(f"  Tokens: {stats['input_tokens']:,} in / {stats['output_tokens']:,} out (${cost:.3f})")

    # Verify
    print("\n  Verifying...")
    for status in ["completed", "cancelled", "confirmed"]:
        resp = supabase.table("camping_reservations") \
            .select("id", count="exact") \
            .eq("status", status) \
            .execute()
        print(f"    {status}: {resp.count}")


if __name__ == "__main__":
    main()
