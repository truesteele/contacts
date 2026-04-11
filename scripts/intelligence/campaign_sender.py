#!/usr/bin/env python3
"""
Come Alive 2026 — Campaign Email Sender
Sends campaign emails via Gmail API from justinrsteele@gmail.com.
Supports email_1 and email_2 via --email-type flag.
Paces sends at configurable intervals, pauses midnight-6am PT.
Logs to logs/campaign_send_YYYY-MM-DD.log.
Uses direct PostgreSQL connection (psycopg2) for reliability.

Usage:
  python campaign_sender.py --email-type email_2 --dry-run    # preview recipients
  python campaign_sender.py --email-type email_2              # send email 2
  python campaign_sender.py --email-type email_2 --interval 90  # custom pacing
  python campaign_sender.py --email-type email_1              # (original behavior)
"""

import os
import sys
import json
import time
import argparse
import base64
import html as html_mod
import logging
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

# ── Config ──────────────────────────────────────────────────────────────
QUIET_START_HOUR = 0     # midnight PT
QUIET_END_HOUR = 6       # 6am PT
PT = ZoneInfo("America/Los_Angeles")

GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")
GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN", "")

SUBJECT = "come alive"

# Sally Steele — co-founder, not a campaign target
EXCLUDE_IDS = {1917}

DB_HOST = "db.ypqsrejrsocebnldicke.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"

# ── Setup ───────────────────────────────────────────────────────────────
root = Path(__file__).resolve().parent.parent.parent
load_dotenv(root / "job-matcher-ai" / ".env.local")
load_dotenv(root / ".env")

DB_PASSWORD = os.environ["SUPABASE_DB_PASSWORD"]

log_dir = root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"campaign_send_{datetime.now(PT).strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def get_db_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )


# ── Email Bodies ────────────────────────────────────────────────────────

def build_email1_body(first_name: str) -> str:
    return f"""{first_name},

If you've known Sally and me at all, you know we camp. A lot. 107 trips. 273 nights under the stars. 54 different campgrounds. We've spent years trying to get friends to come with us. Most of you just laughed. That's starting to change.

Last fall, a mom named Valencia came on one of our trips. First time sleeping outdoors. She grew up afraid of the woods. Couldn't sleep without a locked door. That night she fell asleep to the sound of the ocean. Called it the most restorative sleep she'd had in years. Her daughter spent the weekend running barefoot through camp. No fear. Just joy.

This keeps happening. Families show up cautious and leave different. Real rest. Real food cooked together. Kids free. Strangers becoming family around a fire in 48 hours.

We run 8 trips a year through our nonprofit, Outdoorithm Collective \u2014 Joshua Tree, Pinnacles, Yosemite, Lassen. Each one brings 10-12 families into nature. $10K per trip plus $40K in gear so every family shows up equipped. We\u2019re at $67K of our $120K goal. A friend is matching the first $20K in new donations dollar-for-dollar. Any amount puts the next family at that campfire.

Would you want to be part of this?

outdoorithmcollective.org/comealive

Or just reply. Happy to tell you more.

Justin"""


def build_email2_body(first_name: str) -> str:
    return f"""{first_name},

Wanted to give you a quick update since my note last week.

30 people have said count me in. Friends from Google, HBS, Bridgespan, folks I haven't talked to in years. Gifts of every size. I won't lie, it's been really special to see this community show up like this.

Next Monday, 45 people head to Joshua Tree for our first trip of the year. Most have never camped before. Sally and I spent this week smoking brisket and ribs that we'll bring to the desert and reheat over the campfire. The park is in peak bloom. 80 degrees, wildflowers, boulders, and stars under the darkest sky most of these families will ever see.

We're at $87K of our $120K goal for the season. $33K to fund all 8 trips. If you want to be part of this: outdoorithmcollective.org/comealive

Justin

P.S. If your employer matches through Benevity (Google, Salesforce, Meta, Microsoft), your donation doubles at no extra cost."""


# ── Gmail Helpers ───────────────────────────────────────────────────────

def text_to_gmail_html(body: str) -> str:
    escaped = html_mod.escape(body)
    h = escaped.replace("\n\n", "<br><br>").replace("\n", "<br>")
    h = h.replace(
        "outdoorithmcollective.org/comealive",
        '<a href="https://outdoorithmcollective.org/comealive">outdoorithmcollective.org/comealive</a>',
    )
    return f'<div dir="ltr">{h}</div>'


def get_access_token() -> str:
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": GMAIL_REFRESH_TOKEN,
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
        },
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"Token refresh failed: {data}")
    return data["access_token"]


def send_email(access_token: str, to_email: str, subject: str, html_body: str) -> str:
    msg = (
        f"From: Justin Steele <justinrsteele@gmail.com>\r\n"
        f"To: {to_email}\r\n"
        f"Subject: {subject}\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: text/html; charset=UTF-8\r\n"
        f"\r\n"
        f"{html_body}"
    )
    raw = base64.urlsafe_b64encode(msg.encode()).decode().rstrip("=")

    resp = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"raw": raw},
    )
    data = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Gmail send failed ({resp.status_code}): {data}")
    return data.get("id", "unknown")


# ── DB Helpers ──────────────────────────────────────────────────────────

def update_send_status(conn, contact_id: int, email_type: str, gmail_message_id: str):
    """Update campaign_2026.send_status.[email_type] via direct SQL."""
    now_iso = datetime.now(PT).isoformat()
    status_json = json.dumps({
        "sent_at": now_iso,
        "gmail_message_id": gmail_message_id,
        "method": "gmail_send",
    })

    with conn.cursor() as cur:
        cur.execute(f"""
            UPDATE contacts
            SET campaign_2026 = jsonb_set(
                jsonb_set(
                    COALESCE(campaign_2026, '{{}}'::jsonb),
                    '{{send_status}}',
                    COALESCE(campaign_2026->'send_status', '{{}}'::jsonb),
                    true
                ),
                '{{send_status,{email_type}}}',
                %s::jsonb,
                true
            )
            WHERE id = %s
        """, (status_json, contact_id))
    conn.commit()


def fetch_email1_contacts(conn):
    """Fetch contacts that need email_1 sent (original behavior)."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, first_name, last_name,
                   COALESCE(personal_email, email, work_email) as send_to_email,
                   campaign_2026->'scaffold'->>'campaign_list' as campaign_list
            FROM contacts
            WHERE ask_readiness->'outdoorithm_fundraising'->>'tier' = 'ready_now'
              AND campaign_2026->'scaffold'->>'campaign_list' IN ('B', 'C', 'D')
              AND (personal_email IS NOT NULL OR email IS NOT NULL OR work_email IS NOT NULL)
              AND campaign_2026->'send_status'->'email_1' IS NULL
            ORDER BY
              CASE campaign_2026->'scaffold'->>'campaign_list'
                WHEN 'B' THEN 1 WHEN 'C' THEN 2 WHEN 'D' THEN 3
              END,
              id
        """)
        return cur.fetchall()


def fetch_email2_contacts(conn):
    """Fetch contacts for email_2: non-donors from B-D who got email_1, plus A-list ghosts."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT * FROM (
                -- B/C/D contacts who received email_1, haven't donated, haven't received email_2
                SELECT id, first_name, last_name,
                       COALESCE(personal_email, email, work_email) as send_to_email,
                       campaign_2026->'scaffold'->>'campaign_list' as campaign_list,
                       1 as sort_order
                FROM contacts
                WHERE campaign_2026->'scaffold'->>'campaign_list' IN ('B', 'C', 'D')
                  AND campaign_2026->'send_status'->'email_1' IS NOT NULL
                  AND campaign_2026->'send_status'->'email_2' IS NULL
                  AND campaign_2026->'donation' IS NULL
                  AND (personal_email IS NOT NULL OR email IS NOT NULL OR work_email IS NOT NULL)

                UNION ALL

                -- A-list ghosts: got personal outreach, never responded, didn't donate
                SELECT id, first_name, last_name,
                       COALESCE(personal_email, email, work_email) as send_to_email,
                       'A-ghost' as campaign_list,
                       4 as sort_order
                FROM contacts
                WHERE campaign_2026->'scaffold'->>'campaign_list' = 'A'
                  AND campaign_2026->'send_status'->'personal_outreach' IS NOT NULL
                  AND campaign_2026->'send_status'->'personal_outreach'->>'responded_at' IS NULL
                  AND campaign_2026->'send_status'->'email_2' IS NULL
                  AND campaign_2026->'donation' IS NULL
                  AND (personal_email IS NOT NULL OR email IS NOT NULL OR work_email IS NOT NULL)
            ) sub
            ORDER BY sort_order, id
        """)
        rows = cur.fetchall()
        # Apply hardcoded exclusions
        return [r for r in rows if r["id"] not in EXCLUDE_IDS]


# ── Time Helpers ────────────────────────────────────────────────────────

def is_quiet_hours() -> bool:
    now = datetime.now(PT)
    return QUIET_START_HOUR <= now.hour < QUIET_END_HOUR


def wait_for_quiet_hours_end():
    now = datetime.now(PT)
    resume_time = now.replace(hour=QUIET_END_HOUR, minute=0, second=0, microsecond=0)
    if resume_time <= now:
        resume_time += timedelta(days=1)
    wait_secs = (resume_time - now).total_seconds()
    log.info(f"Quiet hours -- sleeping until {resume_time.strftime('%H:%M %Z')} ({wait_secs/3600:.1f}h)")
    time.sleep(wait_secs)


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Come Alive 2026 Campaign Sender")
    parser.add_argument("--email-type", default="email_1", choices=["email_1", "email_2"],
                        help="Which email to send (default: email_1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print recipient list without sending")
    parser.add_argument("--interval", type=int, default=None,
                        help="Seconds between sends (default: 180 for email_1, 60 for email_2)")
    args = parser.parse_args()

    email_type = args.email_type
    interval = args.interval
    if interval is None:
        interval = 60 if email_type == "email_2" else 180

    log.info("=" * 60)
    log.info(f"Come Alive 2026 -- Campaign Sender ({email_type})")
    log.info("=" * 60)

    conn = get_db_conn()

    if email_type == "email_1":
        contacts = fetch_email1_contacts(conn)
    else:
        contacts = fetch_email2_contacts(conn)

    # Count by list
    list_counts = {}
    for c in contacts:
        lst = c["campaign_list"]
        list_counts[lst] = list_counts.get(lst, 0) + 1

    log.info(f"Found {len(contacts)} contacts to send {email_type} to")
    for lst in sorted(list_counts.keys()):
        log.info(f"  List {lst}: {list_counts[lst]}")

    if not contacts:
        log.info("Nothing to send!")
        conn.close()
        return

    # Dry run: print recipients and exit
    if args.dry_run:
        log.info("")
        log.info("DRY RUN -- Recipients:")
        log.info("-" * 60)
        for i, c in enumerate(contacts):
            name = f"{c['first_name'] or ''} {c['last_name'] or ''}".strip()
            email = c["send_to_email"]
            log.info(f"  {i+1:3d}. {name:<30s} <{email}> (List {c['campaign_list']})")
        log.info("-" * 60)
        log.info(f"Total: {len(contacts)} recipients")
        est_hours = len(contacts) * interval / 3600
        log.info(f"Estimated send time at {interval}s intervals: {est_hours:.1f} hours")
        conn.close()
        return

    # Build email body function
    if email_type == "email_1":
        build_body = build_email1_body
    else:
        build_body = build_email2_body

    # Get Gmail access token (refresh every 45 min)
    access_token = get_access_token()
    token_time = time.time()

    sent = 0
    failed = 0

    for i, contact in enumerate(contacts):
        # Check quiet hours
        if is_quiet_hours():
            wait_for_quiet_hours_end()
            access_token = get_access_token()
            token_time = time.time()
            try:
                conn.close()
            except Exception:
                pass
            conn = get_db_conn()

        # Refresh token every 45 min
        if time.time() - token_time > 2700:
            log.info("Refreshing access token...")
            access_token = get_access_token()
            token_time = time.time()

        name = f"{contact['first_name'] or ''} {contact['last_name'] or ''}".strip()
        email = contact["send_to_email"]
        log.info(f"[{i+1}/{len(contacts)}] Sending to {name} <{email}> (List {contact['campaign_list']})")

        try:
            body = build_body(contact["first_name"] or "Friend")
            html_body = text_to_gmail_html(body)
            msg_id = send_email(access_token, email, SUBJECT, html_body)
            update_send_status(conn, contact["id"], email_type, msg_id)
            sent += 1
            log.info(f"  Sent (msg_id: {msg_id})")
        except Exception as e:
            failed += 1
            log.error(f"  Failed: {e}")

        # Pace: wait between emails (skip wait on last one)
        if i < len(contacts) - 1:
            log.info(f"  Waiting {interval}s before next send...")
            time.sleep(interval)

    conn.close()
    log.info("=" * 60)
    log.info(f"DONE -- Sent: {sent}, Failed: {failed}, Total: {len(contacts)}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
