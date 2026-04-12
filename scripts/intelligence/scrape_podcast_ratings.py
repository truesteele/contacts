#!/usr/bin/env python3
"""
Scrape Apple Podcasts and Spotify for podcast ratings/review counts.

Apple Podcasts: uses itunes_id to fetch the podcast page, extracts rating
and review count from JSON-LD structured data in the HTML.

Spotify: uses spotify_url from podcast_profile.platforms to fetch the show
page, extracts rating and rating count from aria-label attributes.

Usage:
    python scrape_podcast_ratings.py                    # All podcasts with itunes_id
    python scrape_podcast_ratings.py --limit 50         # First 50
    python scrape_podcast_ratings.py --ids 9,697,3      # Specific IDs
    python scrape_podcast_ratings.py --force             # Re-scrape already scraped
    python scrape_podcast_ratings.py --test              # Dry run, no DB writes
    python scrape_podcast_ratings.py --spotify-only      # Only scrape Spotify
    python scrape_podcast_ratings.py --workers 10        # Concurrent requests
    python scrape_podcast_ratings.py --proxy              # Route through SmartProxy
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import dotenv
import requests
from supabase import create_client

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_SERVICE_KEY']

USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
)

# Rate limiting — lower delays when using proxy since IPs rotate
APPLE_DELAY = 0.5    # seconds between Apple requests (proxy rotates IPs)
SPOTIFY_DELAY = 1.0  # seconds between Spotify requests


def build_proxy_url():
    """Build SmartProxy residential proxy URL from env vars."""
    user = os.environ.get('PROXY_USERNAME', '')
    pwd = os.environ.get('PROXY_PASSWORD', '')
    host = os.environ.get('PROXY_HOSTNAME', '')
    port = os.environ.get('PROXY_PORT', '')
    if not all([user, pwd, host, port]):
        return None
    return f'http://{user}:{pwd}@{host}:{port}'


def get_session(use_proxy: bool = False) -> requests.Session:
    """Create a requests session, optionally with proxy."""
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    if use_proxy:
        proxy_url = build_proxy_url()
        if proxy_url:
            session.proxies = {
                'http': proxy_url,
                'https': proxy_url,
            }
    return session


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def load_podcasts(sb, args):
    """Load podcasts to scrape with pagination for >1000 rows."""
    all_data = []
    page_size = 1000
    offset = 0

    while True:
        query = sb.table('podcast_targets').select(
            'id, itunes_id, title, podcast_profile, ratings_scraped_at'
        )

        if args.ids:
            id_list = [int(x.strip()) for x in args.ids.split(',')]
            query = query.in_('id', id_list)
        elif not args.force:
            query = query.is_('ratings_scraped_at', 'null')

        if not args.spotify_only:
            query = query.not_.is_('itunes_id', 'null')

        query = query.order('id')
        query = query.range(offset, offset + page_size - 1)

        result = query.execute()
        batch = result.data or []
        all_data.extend(batch)

        if len(batch) < page_size:
            break
        offset += page_size

    if args.limit:
        all_data = all_data[:args.limit]

    return all_data


def scrape_apple_rating(itunes_id: int, session: requests.Session | None = None) -> dict:
    """Scrape Apple Podcasts page for rating data."""
    url = f'https://podcasts.apple.com/us/podcast/id{itunes_id}'
    try:
        requester = session or requests
        resp = requester.get(url, timeout=15)
        if resp.status_code != 200:
            return {'error': f'HTTP {resp.status_code}'}

        html = resp.text

        # Primary: JSON-LD aggregateRating
        result = {}
        ld_match = re.search(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        if ld_match:
            try:
                ld_data = json.loads(ld_match.group(1))
                agg = ld_data.get('aggregateRating', {})
                if agg:
                    result['rating'] = agg.get('ratingValue')
                    result['review_count'] = agg.get('reviewCount')
            except json.JSONDecodeError:
                pass

        # Secondary: embedded product rating data (more detailed)
        prod_match = re.search(
            r'"ratingAverage":([\d.]+),'
            r'"totalNumberOfRatings":(\d+),'
            r'"totalNumberOfReviews":(\d+)',
            html
        )
        if prod_match:
            result['rating'] = float(prod_match.group(1))
            result['rating_count'] = int(prod_match.group(2))
            result['review_count'] = int(prod_match.group(3))

        if not result:
            return {'error': 'No rating data found in page'}

        return result

    except requests.RequestException as e:
        return {'error': str(e)}


def scrape_spotify_rating(spotify_url: str, session: requests.Session | None = None) -> dict:
    """Scrape Spotify show page for rating data."""
    # Normalize URL — ensure it's a show URL, not an episode
    if '/episode/' in spotify_url:
        return {'error': 'Episode URL, not show URL'}

    try:
        requester = session or requests
        resp = requester.get(spotify_url, timeout=15)
        if resp.status_code != 200:
            return {'error': f'HTTP {resp.status_code}'}

        html = resp.text

        # Pattern: aria-label="X.X stars, NNN ratings"
        match = re.search(
            r'aria-label="([\d.]+)\s+stars?,\s+([\d.,KkMm]+)\s+ratings?"',
            html
        )
        if not match:
            return {'error': 'No rating data found'}

        rating = float(match.group(1))
        count_str = match.group(2).replace(',', '')

        if count_str.upper().endswith('K'):
            count = int(float(count_str[:-1]) * 1000)
        elif count_str.upper().endswith('M'):
            count = int(float(count_str[:-1]) * 1000000)
        else:
            count = int(float(count_str))

        return {'rating': rating, 'rating_count': count}

    except requests.RequestException as e:
        return {'error': str(e)}


def get_spotify_url(podcast: dict) -> str | None:
    """Extract Spotify show URL from podcast_profile."""
    profile = podcast.get('podcast_profile')
    if not profile:
        return None
    platforms = profile.get('platforms', {})
    url = platforms.get('spotify_url', '')
    if url and '/show/' in url:
        return url
    return None


def process_one(podcast: dict, args, session: requests.Session | None = None) -> dict:
    """Scrape ratings for one podcast. Returns update dict."""
    pid = podcast['id']
    title = podcast['title']
    itunes_id = podcast.get('itunes_id')
    spotify_url = get_spotify_url(podcast)

    result = {
        'id': pid,
        'title': title,
        'apple': None,
        'spotify': None,
    }

    # Apple Podcasts
    if itunes_id and not args.spotify_only:
        apple = scrape_apple_rating(int(itunes_id), session)
        result['apple'] = apple
        if 'error' not in apple:
            time.sleep(APPLE_DELAY)
        else:
            time.sleep(0.5)

    # Spotify
    if spotify_url:
        spotify = scrape_spotify_rating(spotify_url, session)
        result['spotify'] = spotify
        if 'error' not in spotify:
            time.sleep(SPOTIFY_DELAY)
        else:
            time.sleep(0.5)

    return result


def save_result(sb, result: dict, test: bool = False):
    """Save scraped ratings to database."""
    update = {'ratings_scraped_at': datetime.now(timezone.utc).isoformat()}

    apple = result.get('apple')
    if apple and 'error' not in apple:
        if apple.get('rating') is not None:
            update['apple_rating'] = apple['rating']
        if apple.get('rating_count') is not None:
            update['apple_rating_count'] = apple['rating_count']
        elif apple.get('review_count') is not None:
            # Fall back to review_count if rating_count not available
            update['apple_rating_count'] = apple['review_count']
        if apple.get('review_count') is not None:
            update['apple_review_count'] = apple['review_count']

    spotify = result.get('spotify')
    if spotify and 'error' not in spotify:
        if spotify.get('rating') is not None:
            update['spotify_rating'] = spotify['rating']
        if spotify.get('rating_count') is not None:
            update['spotify_rating_count'] = spotify['rating_count']

    # Use apple_rating_count as listener_estimate proxy if we don't have one yet
    if update.get('apple_rating_count') and update['apple_rating_count'] > 0:
        update['listener_estimate'] = update['apple_rating_count']

    if test:
        return update

    sb.table('podcast_targets').update(update).eq('id', result['id']).execute()
    return update


def main():
    parser = argparse.ArgumentParser(description='Scrape podcast ratings from Apple & Spotify')
    parser.add_argument('--limit', type=int, help='Max podcasts to scrape')
    parser.add_argument('--ids', type=str, help='Comma-separated podcast IDs')
    parser.add_argument('--force', action='store_true', help='Re-scrape already scraped')
    parser.add_argument('--test', action='store_true', help='Dry run, no DB writes')
    parser.add_argument('--spotify-only', action='store_true', help='Only scrape Spotify')
    parser.add_argument('--workers', type=int, default=1, help='Concurrent workers (default 1 for politeness)')
    parser.add_argument('--proxy', action='store_true', help='Route through SmartProxy residential proxies')
    args = parser.parse_args()

    sb = get_supabase()
    podcasts = load_podcasts(sb, args)
    total = len(podcasts)
    print(f'Loaded {total} podcasts to scrape')

    # Set up session with optional proxy
    session = get_session(use_proxy=args.proxy)
    if args.proxy:
        proxy_url = build_proxy_url()
        if proxy_url:
            print(f'Using proxy: {proxy_url.split("@")[1]}')
        else:
            print('WARNING: --proxy specified but PROXY_* env vars not set, using direct')
            session = get_session(use_proxy=False)

    if total == 0:
        print('Nothing to do.')
        return

    stats = {
        'apple_success': 0,
        'apple_error': 0,
        'spotify_success': 0,
        'spotify_error': 0,
        'spotify_skipped': 0,
        'saved': 0,
    }

    start_time = time.time()

    for i, podcast in enumerate(podcasts, 1):
        result = process_one(podcast, args, session)

        # Stats
        if result['apple']:
            if 'error' in result['apple']:
                stats['apple_error'] += 1
            else:
                stats['apple_success'] += 1

        if result['spotify']:
            if 'error' in result['spotify']:
                stats['spotify_error'] += 1
            else:
                stats['spotify_success'] += 1
        else:
            stats['spotify_skipped'] += 1

        # Display
        apple_str = ''
        if result['apple'] and 'error' not in result['apple']:
            r = result['apple']
            apple_str = f"Apple: {r.get('rating', '?')}★ ({r.get('rating_count', r.get('review_count', '?'))} ratings)"
        elif result['apple']:
            apple_str = f"Apple: {result['apple']['error']}"

        spotify_str = ''
        if result['spotify'] and 'error' not in result['spotify']:
            r = result['spotify']
            spotify_str = f"Spotify: {r.get('rating', '?')}★ ({r.get('rating_count', '?')} ratings)"
        elif result['spotify']:
            spotify_str = f"Spotify: {result['spotify']['error']}"

        status_parts = [s for s in [apple_str, spotify_str] if s]
        status = ' | '.join(status_parts) if status_parts else 'No data sources'

        print(f'[{i}/{total}] {result["title"][:50]:50s} {status}')

        # Save
        if not args.test:
            save_result(sb, result)
            stats['saved'] += 1
        else:
            save_result(sb, result, test=True)

    elapsed = time.time() - start_time
    print(f'\n--- Done in {elapsed:.0f}s ---')
    print(f'Apple:   {stats["apple_success"]} success, {stats["apple_error"]} errors')
    print(f'Spotify: {stats["spotify_success"]} success, {stats["spotify_error"]} errors, {stats["spotify_skipped"]} no URL')
    print(f'Saved:   {stats["saved"]}')


if __name__ == '__main__':
    main()
