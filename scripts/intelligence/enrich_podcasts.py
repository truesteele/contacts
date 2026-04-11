#!/usr/bin/env python3
"""
Podcast Enrichment — Fetch RSS feeds, extract host emails, parse episodes, verify emails.

Enriches discovered podcasts from podcast_targets by:
1. Fetching RSS feed XML
2. Extracting host name/email from <itunes:owner> or <itunes:email>
3. Parsing last 5 episodes (title, description, date, duration)
4. Classifying activity status (active/slow/podfaded)
5. Optionally verifying emails with ZeroBounce

Usage:
  python scripts/intelligence/enrich_podcasts.py --limit 5 --skip-verify
  python scripts/intelligence/enrich_podcasts.py --limit 50 --workers 20
  python scripts/intelligence/enrich_podcasts.py --test
"""

import os
import sys
import re
import time
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime

import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")

# Allow imports from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ── Clients ────────────────────────────────────────────────────────────

def get_supabase() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


# ── ZeroBounce (from find_emails.py pattern) ──────────────────────────

ZEROBOUNCE_BASE = "https://api.zerobounce.net/v2"
_credits_used = 0


def check_zerobounce_credits() -> int:
    api_key = os.environ.get("ZEROBOUNCE_API_KEY", "")
    if not api_key:
        raise ValueError("ZEROBOUNCE_API_KEY not set in environment")
    resp = requests.get(f"{ZEROBOUNCE_BASE}/getcredits", params={"api_key": api_key}, timeout=10)
    resp.raise_for_status()
    return int(resp.json().get("Credits", 0))


def verify_email(email_addr: str, max_retries: int = 2) -> dict | None:
    """Verify a single email via ZeroBounce API. Returns result dict or None."""
    global _credits_used
    api_key = os.environ.get("ZEROBOUNCE_API_KEY", "")

    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(
                f"{ZEROBOUNCE_BASE}/validate",
                params={"api_key": api_key, "email": email_addr, "ip_address": ""},
                timeout=30,
            )

            if resp.status_code == 429:
                wait = 65
                print(f"    ZeroBounce rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code in (401, 402, 403):
                print(f"    ZeroBounce auth/credit error (HTTP {resp.status_code})")
                return None

            if "error code: 1015" in resp.text:
                print(f"    ZeroBounce IP blocked by Cloudflare")
                return None

            resp.raise_for_status()
            data = resp.json()

            status = data.get("status", "").lower()
            if status != "unknown":
                _credits_used += 1

            return {
                "address": data.get("address", email_addr),
                "status": status,
                "sub_status": (data.get("sub_status") or "").lower(),
            }

        except requests.exceptions.RequestException:
            if attempt < max_retries:
                time.sleep(2 ** attempt * 2)
                continue
            return None

    return None


# ── RSS Parsing ────────────────────────────────────────────────────────

# iTunes namespace used in podcast RSS feeds
ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"

# Common noreply/generic addresses to skip
NOREPLY_PATTERNS = re.compile(
    r"(noreply|no-reply|donotreply|support@|abuse@|@anchor\.fm|@mg[\w-]*\.acast\.com)",
    re.IGNORECASE,
)


def fetch_rss(rss_url: str, timeout: int = 20) -> str | None:
    """Fetch RSS feed XML. Returns raw text or None on error."""
    try:
        resp = requests.get(rss_url, timeout=timeout, headers={
            "User-Agent": "TrueSteelePodcastOutreach/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        })
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def parse_rss(xml_text: str) -> dict:
    """Parse RSS XML and extract podcast metadata + episodes.

    Returns dict with keys:
      host_name, host_email, categories, episodes (list of dicts),
      last_episode_date (datetime or None), activity_status
    """
    result = {
        "host_name": None,
        "host_email": None,
        "categories": [],
        "episodes": [],
        "last_episode_date": None,
        "activity_status": "unknown",
    }

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return result

    channel = root.find("channel")
    if channel is None:
        return result

    # Extract host email from <itunes:owner><itunes:email>
    owner = channel.find(f"{{{ITUNES_NS}}}owner")
    if owner is not None:
        email_el = owner.find(f"{{{ITUNES_NS}}}email")
        name_el = owner.find(f"{{{ITUNES_NS}}}name")
        if email_el is not None and email_el.text:
            result["host_email"] = email_el.text.strip()
        if name_el is not None and name_el.text:
            result["host_name"] = name_el.text.strip()

    # Fallback: <itunes:email> directly on channel
    if not result["host_email"]:
        email_el = channel.find(f"{{{ITUNES_NS}}}email")
        if email_el is not None and email_el.text:
            result["host_email"] = email_el.text.strip()

    # Fallback: <itunes:author> for host name
    if not result["host_name"]:
        author_el = channel.find(f"{{{ITUNES_NS}}}author")
        if author_el is not None and author_el.text:
            result["host_name"] = author_el.text.strip()

    # Filter out noreply/generic emails
    if result["host_email"] and NOREPLY_PATTERNS.search(result["host_email"]):
        result["host_email"] = None

    # Extract categories
    for cat_el in channel.findall(f"{{{ITUNES_NS}}}category"):
        cat_text = cat_el.get("text", "").strip()
        if cat_text:
            result["categories"].append(cat_text)
        # Check subcategories
        for sub_el in cat_el.findall(f"{{{ITUNES_NS}}}category"):
            sub_text = sub_el.get("text", "").strip()
            if sub_text:
                result["categories"].append(sub_text)

    # Parse episodes (last 5 by pub date)
    items = channel.findall("item")
    parsed_episodes = []
    for item in items:
        ep = _parse_episode(item)
        if ep:
            parsed_episodes.append(ep)

    # Sort by date descending, take last 5
    parsed_episodes.sort(key=lambda e: e["published_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    result["episodes"] = parsed_episodes[:5]

    # Determine activity status from most recent episode
    if result["episodes"]:
        latest = result["episodes"][0]["published_at"]
        if latest:
            result["last_episode_date"] = latest
            now = datetime.now(timezone.utc)
            days_ago = (now - latest).days
            if days_ago <= 30:
                result["activity_status"] = "active"
            elif days_ago <= 90:
                result["activity_status"] = "slow"
            else:
                result["activity_status"] = "podfaded"

    return result


def _parse_episode(item: ET.Element) -> dict | None:
    """Parse a single <item> element into an episode dict."""
    title_el = item.find("title")
    if title_el is None or not title_el.text:
        return None

    title = title_el.text.strip()

    # Description: try <itunes:summary>, <description>, <content:encoded>
    desc = ""
    for tag in [f"{{{ITUNES_NS}}}summary", "description"]:
        el = item.find(tag)
        if el is not None and el.text:
            desc = el.text.strip()
            # Strip HTML tags for cleaner text
            desc = re.sub(r"<[^>]+>", " ", desc)
            desc = re.sub(r"\s+", " ", desc).strip()
            if len(desc) > 500:
                desc = desc[:500] + "..."
            break

    # Published date
    pub_date = None
    pub_el = item.find("pubDate")
    if pub_el is not None and pub_el.text:
        try:
            pub_date = parsedate_to_datetime(pub_el.text.strip())
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    # Duration from <itunes:duration> (can be seconds or HH:MM:SS)
    duration_seconds = None
    dur_el = item.find(f"{{{ITUNES_NS}}}duration")
    if dur_el is not None and dur_el.text:
        duration_seconds = _parse_duration(dur_el.text.strip())

    # Episode URL
    episode_url = ""
    enclosure = item.find("enclosure")
    if enclosure is not None:
        episode_url = enclosure.get("url", "")
    if not episode_url:
        link_el = item.find("link")
        if link_el is not None and link_el.text:
            episode_url = link_el.text.strip()

    # Guests (from <itunes:name> in <podcast:person> if available)
    guests = None

    return {
        "title": title,
        "description": desc,
        "published_at": pub_date,
        "duration_seconds": duration_seconds,
        "episode_url": episode_url,
        "guests": guests,
    }


def _parse_duration(raw: str) -> int | None:
    """Parse iTunes duration string to seconds. Handles HH:MM:SS, MM:SS, or raw seconds."""
    if not raw:
        return None

    # Pure integer = seconds
    if raw.isdigit():
        return int(raw)

    # HH:MM:SS or MM:SS
    parts = raw.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        pass

    return None


# ── Enrichment Pipeline ────────────────────────────────────────────────

def enrich_one(podcast: dict, skip_verify: bool = True) -> dict:
    """Enrich a single podcast. Returns update dict for podcast_targets + episodes list."""
    pid = podcast["id"]
    rss_url = podcast.get("rss_url", "")
    update = {"enriched_at": datetime.now(timezone.utc).isoformat()}
    episodes = []

    if not rss_url:
        update["activity_status"] = "unknown"
        return {"id": pid, "update": update, "episodes": episodes}

    # Fetch RSS
    xml_text = fetch_rss(rss_url)
    if not xml_text:
        return {"id": pid, "update": update, "episodes": episodes}

    # Parse
    parsed = parse_rss(xml_text)

    # Host info
    if parsed["host_name"]:
        update["host_name"] = parsed["host_name"]
    if parsed["host_email"]:
        update["host_email"] = parsed["host_email"]
        update["email_source"] = "rss_itunes_owner"

    # Activity status
    update["activity_status"] = parsed["activity_status"]
    if parsed["last_episode_date"]:
        update["last_episode_date"] = parsed["last_episode_date"].isoformat()

    # Categories (merge with existing)
    if parsed["categories"]:
        existing_cats = podcast.get("categories") or []
        merged = list(set(existing_cats + parsed["categories"]))
        update["categories"] = merged

    # Episodes
    for ep in parsed["episodes"]:
        episodes.append({
            "podcast_target_id": pid,
            "title": ep["title"],
            "description": ep["description"],
            "published_at": ep["published_at"].isoformat() if ep["published_at"] else None,
            "duration_seconds": ep["duration_seconds"],
            "episode_url": ep["episode_url"],
            "guests": ep["guests"],
        })

    # Email verification
    if parsed["host_email"] and not skip_verify:
        zb_result = verify_email(parsed["host_email"])
        if zb_result:
            status = zb_result["status"]
            if status == "valid":
                update["email_verified"] = True
            elif status in ("invalid", "abuse", "spamtrap"):
                update["email_verified"] = False
                update["host_email"] = None  # Don't keep bad emails
            else:
                update["email_verified"] = False  # catch-all, unknown, etc.

    return {"id": pid, "update": update, "episodes": episodes}


# ── Save Results ───────────────────────────────────────────────────────

def save_enrichment(result: dict, sb: Client) -> bool:
    """Save enrichment result to database. Returns True on success."""
    pid = result["id"]
    try:
        # Update podcast_targets
        sb.table("podcast_targets").update(result["update"]).eq("id", pid).execute()

        # Delete old episodes for this podcast (avoid duplicates on re-enrichment)
        sb.table("podcast_episodes").delete().eq("podcast_target_id", pid).execute()

        # Insert new episodes
        for ep in result["episodes"]:
            sb.table("podcast_episodes").insert(ep).execute()

        return True
    except Exception as e:
        print(f"    Save error (id={pid}): {e}")
        return False


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Enrich podcast targets with RSS feed data")
    parser.add_argument("--limit", type=int, default=50,
                        help="Max podcasts to enrich (default: 50)")
    parser.add_argument("--workers", type=int, default=20,
                        help="Concurrent RSS fetchers (default: 20)")
    parser.add_argument("--skip-verify", action="store_true",
                        help="Skip ZeroBounce email verification (saves credits)")
    parser.add_argument("--test", action="store_true",
                        help="Dry run: fetch and parse but don't save")
    args = parser.parse_args()

    print(f"=== Podcast Enrichment ===")
    print(f"Limit: {args.limit}")
    print(f"Workers: {args.workers}")
    print(f"Email verify: {'OFF (--skip-verify)' if args.skip_verify else 'ON (ZeroBounce)'}")
    print(f"Mode: {'TEST (dry run)' if args.test else 'LIVE'}")
    print()

    # Check ZeroBounce credits if verifying
    if not args.skip_verify:
        try:
            credits = check_zerobounce_credits()
            print(f"ZeroBounce credits: {credits}")
            if credits < 10:
                print("WARNING: Low ZeroBounce credits. Use --skip-verify to skip.")
        except Exception as e:
            print(f"WARNING: Could not check ZeroBounce credits: {e}")

    # Load un-enriched podcasts
    sb = get_supabase()
    resp = sb.table("podcast_targets") \
        .select("id, title, author, rss_url, categories, activity_status") \
        .is_("enriched_at", "null") \
        .limit(args.limit) \
        .execute()

    podcasts = resp.data or []
    print(f"Found {len(podcasts)} un-enriched podcasts")

    if not podcasts:
        print("Nothing to enrich. Done.")
        return

    # Enrich concurrently
    print(f"\nEnriching {len(podcasts)} podcasts...")
    results = []
    emails_found = 0
    emails_verified = 0
    episodes_total = 0
    activity_counts = {"active": 0, "slow": 0, "podfaded": 0, "unknown": 0}

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(enrich_one, p, args.skip_verify): p
            for p in podcasts
        }
        for i, future in enumerate(as_completed(futures), 1):
            podcast = futures[future]
            try:
                result = future.result()
                results.append(result)

                # Stats
                update = result["update"]
                status = update.get("activity_status", "unknown")
                activity_counts[status] = activity_counts.get(status, 0) + 1

                if update.get("host_email"):
                    emails_found += 1
                if update.get("email_verified"):
                    emails_verified += 1

                ep_count = len(result["episodes"])
                episodes_total += ep_count

                # Progress
                email_str = f" | email: {update['host_email']}" if update.get("host_email") else ""
                print(f"  [{i}/{len(podcasts)}] {podcast['title'][:50]} → {status}, {ep_count} eps{email_str}")

            except Exception as e:
                print(f"  [{i}/{len(podcasts)}] ERROR {podcast['title'][:50]}: {e}")

    # Summary
    print(f"\n{'='*60}")
    print(f"Enrichment Summary")
    print(f"{'='*60}")
    print(f"  Podcasts processed: {len(results)}")
    print(f"  Emails found:       {emails_found}")
    if not args.skip_verify:
        print(f"  Emails verified:    {emails_verified}")
        print(f"  ZeroBounce credits: {_credits_used} used")
    print(f"  Episodes parsed:    {episodes_total}")
    print(f"  Activity: {activity_counts}")

    # Save
    if args.test:
        print(f"\nDRY RUN -- no database changes made")
        # Print sample results
        for r in results[:5]:
            update = r["update"]
            print(f"\n  id={r['id']}: {update.get('activity_status', '?')}")
            if update.get("host_name"):
                print(f"    host: {update['host_name']}")
            if update.get("host_email"):
                print(f"    email: {update['host_email']} (verified={update.get('email_verified', 'N/A')})")
            if r["episodes"]:
                print(f"    episodes ({len(r['episodes'])}):")
                for ep in r["episodes"][:3]:
                    print(f"      - {ep['title'][:60]}")
    else:
        print(f"\nSaving to database...")
        saved = 0
        for result in results:
            if save_enrichment(result, sb):
                saved += 1
        print(f"Saved {saved}/{len(results)} enrichments")

    print("\nDone.")


if __name__ == "__main__":
    main()
