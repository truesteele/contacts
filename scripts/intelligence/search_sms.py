#!/usr/bin/env python3
"""Search SMS backup XML for messages matching a phone number and/or keyword.

Usage:
  python search_sms.py --phone 3104868289 --keyword "sean|shawn|shaun"
  python search_sms.py --phone 3104868289                  # all messages with this number
  python search_sms.py --keyword "camping"                  # all messages containing keyword
  python search_sms.py --keyword "camping" --context 2      # show 2 messages before/after each match
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

DRIVE_FOLDER_ID = "1bXb4DsB0wP9D3ZZMtVGRcqYJJgODQ3JM"
CRED_PATH = os.path.expanduser("~/.google_workspace_mcp/credentials/justinrsteele@gmail.com.json")
CACHE_DIR = os.path.join(os.path.dirname(__file__), "../../.cache")


def build_drive():
    with open(CRED_PATH) as f:
        data = json.load(f)
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def normalize(phone):
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def find_sms_file(drive):
    results = drive.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and name contains 'sms-'",
        pageSize=1,
        fields="files(id, name, size)",
        orderBy="modifiedTime desc",
    ).execute()
    files = results.get("files", [])
    return files[0] if files else None


def get_cached_xml(drive):
    """Download SMS XML if not cached. Returns path to cached file."""
    sms_file = find_sms_file(drive)
    if not sms_file:
        print("No SMS backup found!")
        sys.exit(1)

    os.makedirs(CACHE_DIR, exist_ok=True)
    cached_path = os.path.join(CACHE_DIR, sms_file["name"])

    if os.path.exists(cached_path):
        size_gb = os.path.getsize(cached_path) / (1024**3)
        print(f"Using cached: {cached_path} ({size_gb:.1f} GB)")
    else:
        size_gb = int(sms_file.get("size", 0)) / (1024**3)
        print(f"Downloading {sms_file['name']} ({size_gb:.1f} GB)...")
        request = drive.files().get_media(fileId=sms_file["id"])
        with open(cached_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request, chunksize=50 * 1024 * 1024)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"  {int(status.progress() * 100)}%", flush=True)

    return cached_path


def parse_message(elem, tag):
    """Extract a message dict from an SMS or MMS element."""
    date_ms = elem.get("date", "0")
    try:
        ts = int(date_ms)
        dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=timezone.utc)
    except (ValueError, OSError):
        dt = None

    address = elem.get("address", "")
    phone = normalize(address)

    if tag == "sms":
        body = elem.get("body", "")
        msg_type = int(elem.get("type", "0"))
    else:  # mms
        parts = []
        for part in elem.iter("part"):
            ct = part.get("ct", "")
            if ct.startswith("text/"):
                text = part.get("text", "").strip()
                if text and text != "null":
                    parts.append(text)
        body = " ".join(parts)
        msg_type = int(elem.get("msg_box", elem.get("type", "0")))

    return {
        "date": dt,
        "phone": phone,
        "contact_name": elem.get("contact_name", ""),
        "direction": "sent" if msg_type == 2 else "received",
        "body": body,
    }


def search_xml(xml_path, target_phone=None, pattern=None, context_lines=0):
    """Search XML for messages matching phone and/or keyword pattern.

    If context_lines > 0, returns surrounding messages from the same conversation.
    """
    # If we need context, we need to collect all messages for the conversation first
    if context_lines > 0 and target_phone:
        return _search_with_context(xml_path, target_phone, pattern, context_lines)

    matches = []
    count = 0
    context = ET.iterparse(xml_path, events=("end",))

    for _, elem in context:
        tag = elem.tag
        if tag not in ("sms", "mms"):
            continue

        msg = parse_message(elem, tag)
        count += 1

        if count % 500000 == 0:
            print(f"  Scanned {count:,} messages...", flush=True)

        phone_ok = (target_phone is None) or (msg["phone"] == target_phone)
        keyword_ok = (pattern is None) or (pattern.search(msg["body"]) if msg["body"] else False)

        if phone_ok and keyword_ok and msg["body"]:
            matches.append(msg)

        elem.clear()

    return matches, count


def _search_with_context(xml_path, target_phone, pattern, context_lines):
    """Collect all messages for a phone, then return matches with surrounding context."""
    all_msgs = []
    count = 0
    context = ET.iterparse(xml_path, events=("end",))

    for _, elem in context:
        tag = elem.tag
        if tag not in ("sms", "mms"):
            continue

        msg = parse_message(elem, tag)
        count += 1

        if count % 500000 == 0:
            print(f"  Scanned {count:,} messages...", flush=True)

        if msg["phone"] == target_phone and msg["body"]:
            all_msgs.append(msg)

        elem.clear()

    # Sort by date
    all_msgs.sort(key=lambda m: m["date"] or datetime.min.replace(tzinfo=timezone.utc))

    # Find matches and collect context
    if pattern is None:
        return all_msgs, count

    matches = []
    match_indices = set()
    for i, msg in enumerate(all_msgs):
        if pattern.search(msg["body"]):
            for j in range(max(0, i - context_lines), min(len(all_msgs), i + context_lines + 1)):
                match_indices.add(j)

    matches = [all_msgs[i] for i in sorted(match_indices)]
    # Mark which are the actual matches vs context
    for i in sorted(match_indices):
        all_msgs[i]["_is_match"] = bool(pattern.search(all_msgs[i]["body"]))

    return matches, count


def main():
    parser = argparse.ArgumentParser(description="Search SMS backup for messages")
    parser.add_argument("--phone", help="Phone number to filter (digits only, e.g. 3104868289)")
    parser.add_argument("--keyword", help="Regex pattern to search for in message bodies")
    parser.add_argument("--context", "-C", type=int, default=0,
                        help="Number of surrounding messages to show (requires --phone)")
    parser.add_argument("--limit", type=int, default=0, help="Max results to show (0=all)")
    args = parser.parse_args()

    if not args.phone and not args.keyword:
        parser.error("At least one of --phone or --keyword is required")

    target_phone = normalize(args.phone) if args.phone else None
    pattern = re.compile(args.keyword, re.IGNORECASE) if args.keyword else None

    print("Connecting to Google Drive...")
    drive = build_drive()
    xml_path = get_cached_xml(drive)

    desc = []
    if target_phone:
        desc.append(f"phone={target_phone}")
    if pattern:
        desc.append(f"keyword='{args.keyword}'")
    print(f"\nSearching: {', '.join(desc)}...")

    matches, total = search_xml(xml_path, target_phone, pattern, args.context)

    print(f"\nScanned {total:,} total messages")
    print(f"Found {len(matches)} matching messages:\n")

    results = sorted(matches, key=lambda x: x["date"] or datetime.min.replace(tzinfo=timezone.utc))
    if args.limit:
        results = results[:args.limit]

    for m in results:
        dt_str = m["date"].strftime("%Y-%m-%d %H:%M") if m["date"] else "unknown date"
        marker = ">>>" if m.get("_is_match") else "   "
        print(f"  {marker} [{dt_str}] ({m['direction']}): {m['body'][:500]}")
        print()


if __name__ == "__main__":
    main()
