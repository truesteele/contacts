#!/usr/bin/env python3
"""
Podcast API Client — Podcast Index + iTunes Search

Shared utility for podcast discovery and enrichment scripts.
Handles Podcast Index SHA-1 auth, search by term, episode fetching,
and iTunes Search API wrapper.

Usage as library:
    from podcast_api import PodcastIndexClient, search_itunes

    client = PodcastIndexClient(api_key="...", api_secret="...")
    results = client.search_by_term("outdoor equity")
    episodes = client.get_episodes(feed_id=12345)
    itunes_results = search_itunes("camping families")
"""

import hashlib
import time
import requests


class PodcastIndexClient:
    """Client for the Podcast Index API (https://api.podcastindex.org)."""

    BASE_URL = "https://api.podcastindex.org/api/1.0"

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()

    def _headers(self) -> dict:
        """Generate auth headers with SHA-1 hash per Podcast Index spec."""
        epoch = str(int(time.time()))
        hash_input = self.api_key + self.api_secret + epoch
        auth_hash = hashlib.sha1(hash_input.encode()).hexdigest()
        return {
            "X-Auth-Key": self.api_key,
            "X-Auth-Date": epoch,
            "Authorization": auth_hash,
            "User-Agent": "TrueSteelePodcastOutreach/1.0",
        }

    def _get(self, endpoint: str, params: dict) -> dict:
        """Make authenticated GET request to Podcast Index API."""
        url = f"{self.BASE_URL}{endpoint}"
        resp = self.session.get(url, headers=self._headers(), params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def search_by_term(self, term: str, max_results: int = 100) -> list:
        """Search podcasts by keyword term.

        Returns list of podcast dicts with keys like:
        id, title, author, description, url, image, language,
        categories, lastUpdateTime, episodeCount, etc.
        """
        data = self._get("/search/byterm", {"q": term, "max": max_results})
        feeds = data.get("feeds", [])
        return [_normalize_podcast(f) for f in feeds]

    def get_episodes(self, feed_id: int, max_results: int = 10) -> list:
        """Get recent episodes for a podcast by feed ID.

        Returns list of episode dicts with keys like:
        id, title, description, datePublished, duration, enclosureUrl, etc.
        """
        data = self._get("/episodes/byfeedid", {"id": feed_id, "max": max_results})
        items = data.get("items", [])
        return [_normalize_episode(e) for e in items]

    def get_podcast_by_id(self, feed_id: int) -> dict | None:
        """Get a single podcast by its feed ID."""
        data = self._get("/podcasts/byfeedid", {"id": feed_id})
        feed = data.get("feed")
        if not feed:
            return None
        return _normalize_podcast(feed)


def _normalize_podcast(raw: dict) -> dict:
    """Normalize a Podcast Index feed record into a clean dict."""
    # Categories come as a dict {id: name} — flatten to list of names
    cats = raw.get("categories") or {}
    if isinstance(cats, dict):
        cat_list = list(cats.values())
    elif isinstance(cats, list):
        cat_list = cats
    else:
        cat_list = []

    return {
        "podcast_index_id": raw.get("id"),
        "title": raw.get("title", "").strip(),
        "author": raw.get("author", "").strip(),
        "description": raw.get("description", "").strip(),
        "categories": cat_list,
        "language": raw.get("language", "en"),
        "episode_count": raw.get("episodeCount", 0),
        "last_update_time": raw.get("lastUpdateTime", 0),
        "website_url": raw.get("link", "").strip(),
        "rss_url": raw.get("url", "").strip(),
        "image_url": raw.get("image", "").strip(),
        "itunes_id": raw.get("itunesId"),
    }


def _normalize_episode(raw: dict) -> dict:
    """Normalize a Podcast Index episode record into a clean dict."""
    return {
        "title": raw.get("title", "").strip(),
        "description": raw.get("description", "").strip(),
        "published_at": raw.get("datePublished", 0),
        "duration_seconds": raw.get("duration", 0),
        "episode_url": raw.get("enclosureUrl", "").strip() or raw.get("link", "").strip(),
        "guests": None,
    }


# ── iTunes Search API ──────────────────────────────────────────────────

_last_itunes_call = 0.0


def search_itunes(term: str, limit: int = 50) -> list:
    """Search iTunes for podcasts by keyword.

    Rate limited to ~20 req/min (1s delay between calls).
    Returns list of normalized podcast dicts.
    """
    global _last_itunes_call

    # Enforce 1s delay between calls
    elapsed = time.time() - _last_itunes_call
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    url = "https://itunes.apple.com/search"
    params = {"term": term, "entity": "podcast", "limit": limit}

    resp = requests.get(url, params=params, timeout=15)
    _last_itunes_call = time.time()
    resp.raise_for_status()

    data = resp.json()
    results = data.get("results", [])
    return [_normalize_itunes(r) for r in results]


def _normalize_itunes(raw: dict) -> dict:
    """Normalize an iTunes Search result into our standard podcast dict."""
    return {
        "podcast_index_id": None,
        "itunes_id": raw.get("collectionId"),
        "title": raw.get("collectionName", "").strip(),
        "author": raw.get("artistName", "").strip(),
        "description": "",  # iTunes search doesn't return full descriptions
        "categories": [g.strip() for g in raw.get("genres", []) if g.strip() != "Podcasts"],
        "language": "",
        "episode_count": raw.get("trackCount", 0),
        "last_update_time": 0,
        "website_url": raw.get("collectionViewUrl", "").strip(),
        "rss_url": raw.get("feedUrl", "").strip(),
        "image_url": raw.get("artworkUrl600", "") or raw.get("artworkUrl100", ""),
    }


# ── Quick self-test ────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")

    api_key = os.environ.get("PODCAST_INDEX_API_KEY")
    api_secret = os.environ.get("PODCAST_INDEX_API_SECRET")

    if api_key and api_secret:
        print("=== Podcast Index API Test ===")
        client = PodcastIndexClient(api_key, api_secret)
        results = client.search_by_term("outdoor equity", max_results=3)
        print(f"Found {len(results)} podcasts for 'outdoor equity':")
        for r in results:
            print(f"  - {r['title']} by {r['author']} ({r['episode_count']} eps)")

        if results:
            feed_id = results[0]["podcast_index_id"]
            eps = client.get_episodes(feed_id, max_results=3)
            print(f"\nRecent episodes for '{results[0]['title']}':")
            for e in eps:
                print(f"  - {e['title']}")
    else:
        print("PODCAST_INDEX_API_KEY / PODCAST_INDEX_API_SECRET not set, skipping PI test")

    print("\n=== iTunes Search API Test ===")
    itunes_results = search_itunes("camping families", limit=3)
    print(f"Found {len(itunes_results)} podcasts for 'camping families':")
    for r in itunes_results:
        print(f"  - {r['title']} by {r['author']} ({r['episode_count']} eps)")

    print("\nAll imports and classes OK.")
