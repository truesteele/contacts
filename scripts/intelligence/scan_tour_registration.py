#!/usr/bin/env python3
"""Daily scanner for college tour registration availability.

Checks 6 school portals with Playwright and emails justinrsteele@gmail.com
when target June dates become bookable. Tracks state to avoid duplicate alerts.

Usage:
    python scan_tour_registration.py           # Normal scan
    python scan_tour_registration.py --test    # Force send a test email
    python scan_tour_registration.py --reset   # Clear state and re-scan
"""

import sys
import os
import json
import base64
import argparse
from datetime import datetime, date
from email.mime.text import MIMEText
from pathlib import Path

from playwright.sync_api import sync_playwright
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────

CREDENTIALS_DIR = os.path.expanduser("~/.google_workspace_mcp/credentials")
NOTIFY_EMAIL = "justinrsteele@gmail.com"
STATE_FILE = Path(__file__).parent / ".tour_scan_state.json"
EXPIRY_DATE = date(2026, 6, 7)  # Stop scanning after all tour dates pass

SCHOOLS = [
    {
        "name": "Harvard University",
        "date": "Mon, Jun 1",
        "target_day": 1,
        "url": "https://www.eventbrite.com/o/harvard-university-visitor-center-30492393010",
        "register_url": "https://www.eventbrite.com/o/harvard-university-visitor-center-30492393010",
        "check_type": "eventbrite",
    },
    {
        "name": "Northeastern University",
        "date": "Tue, Jun 2",
        "target_day": 2,
        "url": "https://apply.northeastern.edu/portal/campus-visit-registration",
        "register_url": "https://apply.northeastern.edu/portal/campus-visit-registration",
        "check_type": "calendar",
    },
    {
        "name": "Columbia University",
        "date": "Wed, Jun 3",
        "target_day": 3,
        "url": "https://apply.college.columbia.edu/portal/campus_visit",
        "register_url": "https://apply.college.columbia.edu/portal/campus_visit",
        "check_type": "calendar",
    },
    {
        "name": "NYU",
        "date": "Thu, Jun 4",
        "target_day": 4,
        "url": "https://connect.nyu.edu/portal/nyuvisit_tours",
        "register_url": "https://connect.nyu.edu/portal/nyuvisit_tours",
        "check_type": "calendar",
    },
    {
        "name": "Howard University",
        "date": "Thu, Jun 5",
        "target_day": 5,
        "url": "https://applyhu.howard.edu/portal/campusvisit",
        "register_url": "https://applyhu.howard.edu/portal/campusvisit",
        "check_type": "calendar",
    },
    {
        "name": "University of Virginia",
        "date": "Fri, Jun 6",
        "target_day": 6,
        "url": "https://apply.undergradadmission.virginia.edu/portal/events",
        "register_url": "https://apply.undergradadmission.virginia.edu/portal/events",
        "check_type": "calendar",
    },
]


# ── Portal Checking ──────────────────────────────────────────────────

def months_to_advance() -> int:
    """Calculate how many months to advance from current month to June 2026."""
    now = datetime.now()
    current = now.year * 12 + now.month
    target = 2026 * 12 + 6  # June 2026
    return max(0, target - current)


def check_calendar_portal(page, school: dict) -> dict:
    """Check a ui-datepicker calendar portal for target date availability."""
    result = {"available": False, "status": "unknown", "events": []}

    try:
        page.goto(school["url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # Advance calendar to June 2026
        advances = months_to_advance()
        for _ in range(advances):
            next_btn = page.locator(".ui-datepicker-next").first
            next_btn.click(force=True)
            page.wait_for_timeout(1000)

        # Verify we're on June 2026
        title = page.evaluate(
            "document.querySelector('.ui-datepicker-title')?.textContent || ''"
        )
        if "June" not in title and "Jun" not in title:
            result["status"] = f"wrong_month:{title.strip()}"
            return result

        # Check target day's cell class
        day = school["target_day"]
        cell_info = page.evaluate(f"""(() => {{
            const cells = document.querySelectorAll('td');
            for (const cell of cells) {{
                const text = cell.textContent.trim();
                if (text === '{day}') {{
                    return {{
                        classes: cell.className,
                        available: cell.className.includes('available'),
                        unavailable: cell.className.includes('unavailable'),
                        disabled: cell.className.includes('disabled'),
                    }};
                }}
            }}
            return null;
        }})()""")

        if cell_info is None:
            result["status"] = "day_not_found"
            return result

        result["available"] = cell_info["available"]
        if cell_info["available"]:
            result["status"] = "available"
            # Try clicking to get time slots
            result["events"] = _get_event_slots(page, day)
        elif cell_info["unavailable"]:
            result["status"] = "filled"
        elif cell_info["disabled"]:
            result["status"] = "not_scheduled"
        else:
            result["status"] = f"unknown:{cell_info['classes']}"

    except Exception as e:
        result["status"] = f"error:{str(e)[:100]}"

    return result


def _get_event_slots(page, day: int) -> list:
    """After finding an available date, click it and extract event time slots."""
    try:
        link = page.locator(f"td.available a[data-date='{day}']").first
        link.click()
        page.wait_for_timeout(2000)

        events = page.evaluate("""(() => {
            const els = document.querySelectorAll('div, section, article');
            const results = [];
            for (const el of els) {
                const text = el.textContent.trim();
                if (text.length > 20 && text.length < 500) {
                    if (/\\d{1,2}:\\d{2}\\s*(AM|PM)/i.test(text) &&
                        (text.includes('Visit') || text.includes('Tour') || text.includes('Session'))) {
                        results.push(text);
                    }
                }
            }
            return [...new Set(results)].slice(0, 8);
        })()""")
        return events
    except Exception:
        return []


def check_eventbrite(page, school: dict) -> dict:
    """Check Harvard's Eventbrite for June event listings."""
    result = {"available": False, "status": "unknown", "events": []}

    try:
        page.goto(school["url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        body_text = page.evaluate("document.body.innerText")

        # Look for June events in the listing
        import re
        june_pattern = re.compile(
            r"(Official.*?Historical Tour.*?(?:June|Jun|06/\d{2}).*?)(?:\n|$)",
            re.IGNORECASE,
        )
        matches = june_pattern.findall(body_text)

        if not matches:
            # Broader check — any mention of June in event context
            lines = body_text.split("\n")
            for line in lines:
                line_stripped = line.strip()
                if ("June" in line_stripped or "Jun " in line_stripped) and (
                    "Tour" in line_stripped or "Week of" in line_stripped
                ):
                    matches.append(line_stripped)

        if matches:
            result["available"] = True
            result["status"] = "available"
            result["events"] = matches[:5]
        else:
            # Check what's currently showing
            if "Upcoming (0)" in body_text:
                result["status"] = "no_upcoming_events"
            elif "Upcoming" in body_text:
                result["status"] = "no_june_events"
            else:
                result["status"] = "not_scheduled"

    except Exception as e:
        result["status"] = f"error:{str(e)[:100]}"

    return result


# ── State Management ─────────────────────────────────────────────────

def load_state() -> dict:
    """Load previous scan state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"alerted": {}, "last_scan": None}


def save_state(state: dict):
    """Save scan state."""
    state["last_scan"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── Email ────────────────────────────────────────────────────────────

def send_alert_email(newly_available: list[dict], still_waiting: list[str]):
    """Send email via Gmail API when tour dates become bookable."""
    cred_path = os.path.join(CREDENTIALS_DIR, f"{NOTIFY_EMAIL}.json")
    with open(cred_path) as f:
        data = json.load(f)

    creds = Credentials(
        token=data.get("token") or data.get("access_token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    # Build email
    school_names = ", ".join(s["name"] for s in newly_available)
    subject = f"[Tour Alert] Registration NOW OPEN: {school_names}"

    lines = ["Good news! College tour registration just opened:\n"]
    for s in newly_available:
        lines.append(f"  \u2713 {s['name']} \u2014 {s['date']}")
        if s.get("events"):
            for ev in s["events"][:3]:
                lines.append(f"    {ev[:120]}")
        lines.append(f"    Register: {s['register_url']}")
        lines.append("")

    if still_waiting:
        lines.append(f"Still waiting on: {', '.join(still_waiting)}")
    else:
        lines.append("All 6 schools now have registration open!")

    lines.append("\n\u2014 Tour Registration Scanner")
    lines.append(f"   Scanned at {datetime.now().strftime('%Y-%m-%d %H:%M PT')}")

    body = "\n".join(lines)

    message = MIMEText(body)
    message["to"] = NOTIFY_EMAIL
    message["from"] = NOTIFY_EMAIL
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()

    print(f"Alert email sent to {NOTIFY_EMAIL}: {school_names}")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Send a test email")
    parser.add_argument("--reset", action="store_true", help="Clear state and re-scan")
    args = parser.parse_args()

    # Self-expiring
    if date.today() > EXPIRY_DATE:
        print(f"Past tour dates ({EXPIRY_DATE}) \u2014 exiting.")
        return

    if args.reset and STATE_FILE.exists():
        STATE_FILE.unlink()
        print("State cleared.")

    if args.test:
        print("Sending test email...")
        send_alert_email(
            [{"name": "TEST University", "date": "Test Date",
              "register_url": "https://example.com", "events": ["Test Event 10:00 AM"]}],
            ["Other School"],
        )
        return

    state = load_state()
    already_alerted = set(state.get("alerted", {}).keys())
    newly_available = []
    still_waiting = []
    results = {}

    print(f"Scanning {len(SCHOOLS)} school portals...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for school in SCHOOLS:
            name = school["name"]
            print(f"  Checking {name}...", end=" ", flush=True)

            page = browser.new_page()
            try:
                if school["check_type"] == "eventbrite":
                    result = check_eventbrite(page, school)
                else:
                    result = check_calendar_portal(page, school)

                results[name] = result
                print(f"{result['status']}")

                if result["available"] and name not in already_alerted:
                    newly_available.append({**school, "events": result.get("events", [])})
                elif not result["available"]:
                    still_waiting.append(f"{name} ({school['date']})")

            except Exception as e:
                print(f"ERROR: {e}")
                results[name] = {"available": False, "status": f"error:{str(e)[:80]}"}
                still_waiting.append(f"{name} ({school['date']})")
            finally:
                page.close()

        browser.close()

    # Send alert for newly available schools
    if newly_available:
        try:
            send_alert_email(newly_available, still_waiting)
            # Update state
            for s in newly_available:
                state.setdefault("alerted", {})[s["name"]] = {
                    "date": datetime.now().isoformat(),
                    "events": s.get("events", [])[:3],
                }
        except Exception as e:
            print(f"ERROR sending email: {e}")
    else:
        print("\nNo new availability detected.")

    # Save state and summary
    state["last_results"] = {
        name: {"status": r["status"], "available": r["available"]}
        for name, r in results.items()
    }
    save_state(state)

    # Print summary
    print(f"\nSummary ({datetime.now().strftime('%Y-%m-%d %H:%M')}):")
    for name, r in results.items():
        marker = "\u2713" if r["available"] else "\u2717"
        alerted = " (alerted)" if name in already_alerted else ""
        new = " ** NEW **" if any(s["name"] == name for s in newly_available) else ""
        print(f"  {marker} {name}: {r['status']}{alerted}{new}")


if __name__ == "__main__":
    main()
