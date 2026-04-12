#!/usr/bin/env python3
"""
Podcast Embedding Generation — text-embedding-3-small (768 dims)

Generates vector embeddings for:
1. podcast_targets.description_embedding — podcast description + categories + recent episodes
2. speaker_profiles.profile_embedding — speaker bio + topic pillars + keywords

Uses the same batch embedding pattern as generate_embeddings.py.

Usage:
  python scripts/intelligence/embed_podcasts.py --test          # 5 podcasts + 2 speakers
  python scripts/intelligence/embed_podcasts.py --force         # Re-embed everything
  python scripts/intelligence/embed_podcasts.py --limit 50      # Cap at 50 podcasts
  python scripts/intelligence/embed_podcasts.py --speakers-only # Only embed speaker profiles
  python scripts/intelligence/embed_podcasts.py                 # Full run
"""

import os
import sys
import json
import time
import argparse

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError
from supabase import create_client, Client
import psycopg2

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 768
BATCH_SIZE = 500
PAGE_SIZE = 1000


# ── Text Builders ─────────────────────────────────────────────────────

def build_podcast_text(podcast: dict, episodes: list[dict]) -> str:
    """Build embedding text for a podcast.

    Format:
      {title} | {author}
      {description}
      Categories: {cat1}, {cat2}, ...
      Recent episodes: {ep1_title}; {ep2_title}; {ep3_title}
    """
    parts = []

    title = podcast.get("title", "")
    author = podcast.get("author", "")
    if author:
        parts.append(f"{title} | {author}")
    else:
        parts.append(title)

    description = podcast.get("description", "")
    if description:
        if len(description) > 1500:
            description = description[:1500] + "..."
        parts.append(description)

    categories = podcast.get("categories")
    if categories:
        if isinstance(categories, str):
            try:
                categories = json.loads(categories)
            except (json.JSONDecodeError, ValueError):
                categories = [categories]
        if isinstance(categories, list) and categories:
            parts.append(f"Categories: {', '.join(str(c) for c in categories)}")

    if episodes:
        ep_titles = [ep.get("title", "") for ep in episodes if ep.get("title")]
        if ep_titles:
            parts.append(f"Recent episodes: {'; '.join(ep_titles[:3])}")

    return "\n".join(parts)


def build_speaker_text(speaker: dict) -> str:
    """Build embedding text for a speaker profile.

    Format:
      {name} | {headline}
      Bio: {bio}
      Topic Pillars: {pillar1_name}: {pillar1_description}; {pillar2_name}: ...
      Keywords: {kw1}, {kw2}, ...
    """
    parts = []

    name = speaker.get("name", "")
    headline = speaker.get("headline", "")
    if headline:
        parts.append(f"{name} | {headline}")
    else:
        parts.append(name)

    bio = speaker.get("bio", "")
    if bio:
        parts.append(f"Bio: {bio}")

    pillars = speaker.get("topic_pillars") or []
    if isinstance(pillars, str):
        try:
            pillars = json.loads(pillars)
        except (json.JSONDecodeError, ValueError):
            pillars = []

    if pillars:
        pillar_strs = []
        all_keywords = []
        for p in pillars:
            if isinstance(p, dict):
                pname = p.get("name", "")
                pdesc = p.get("description", "")
                if pname:
                    pillar_strs.append(f"{pname}: {pdesc}" if pdesc else pname)
                kws = p.get("keywords", [])
                if isinstance(kws, list):
                    all_keywords.extend(kws)
        if pillar_strs:
            parts.append(f"Topic Pillars: {'; '.join(pillar_strs)}")
        if all_keywords:
            parts.append(f"Keywords: {', '.join(all_keywords)}")

    return "\n".join(parts)


# ── Embedding Engine ──────────────────────────────────────────────────

class PodcastEmbedder:

    def __init__(self, test_mode=False, force=False, limit=None, speakers_only=False):
        self.test_mode = test_mode
        self.force = force
        self.limit = limit
        self.speakers_only = speakers_only
        self.sb: Client | None = None
        self.oai: OpenAI | None = None
        self.pg_conn = None
        self.stats = {
            "podcasts_embedded": 0,
            "speakers_embedded": 0,
            "errors": 0,
            "total_tokens": 0,
            "api_calls": 0,
        }

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        openai_key = os.environ.get("OPENAI_APIKEY")
        db_password = os.environ.get("SUPABASE_DB_PASSWORD")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        if not openai_key:
            print("ERROR: Missing OPENAI_APIKEY")
            return False
        if not db_password:
            print("ERROR: Missing SUPABASE_DB_PASSWORD (needed for psycopg2 vector saves)")
            return False

        self.sb = create_client(url, key)
        self.oai = OpenAI(api_key=openai_key)
        self.pg_conn = psycopg2.connect(
            host="db.ypqsrejrsocebnldicke.supabase.co",
            port=5432,
            dbname="postgres",
            user="postgres",
            password=db_password,
        )
        self.pg_conn.autocommit = True
        print("Connected to Supabase, OpenAI, and PostgreSQL (psycopg2)")
        return True

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI embedding API for a batch of texts."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.oai.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts,
                    dimensions=EMBEDDING_DIMS,
                )
                self.stats["api_calls"] += 1
                self.stats["total_tokens"] += response.usage.total_tokens
                return [item.embedding for item in response.data]
            except RateLimitError:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            except APIError as e:
                print(f"  API error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise
        return []

    def save_podcast_embedding(self, podcast_id: int, embedding: list[float]) -> bool:
        """Save podcast embedding via psycopg2."""
        try:
            cur = self.pg_conn.cursor()
            cur.execute(
                "UPDATE podcast_targets SET description_embedding = %s::vector WHERE id = %s",
                (str(embedding), podcast_id),
            )
            cur.close()
            return True
        except Exception as e:
            print(f"  DB error saving podcast {podcast_id}: {e}")
            return False

    def save_speaker_embedding(self, speaker_id: int, embedding: list[float]) -> bool:
        """Save speaker profile embedding via psycopg2."""
        try:
            cur = self.pg_conn.cursor()
            cur.execute(
                "UPDATE speaker_profiles SET profile_embedding = %s::vector WHERE id = %s",
                (str(embedding), speaker_id),
            )
            cur.close()
            return True
        except Exception as e:
            print(f"  DB error saving speaker {speaker_id}: {e}")
            return False

    def load_podcasts(self) -> list[dict]:
        """Load podcasts needing embeddings."""
        all_podcasts = []
        offset = 0

        while True:
            query = (
                self.sb.table("podcast_targets")
                .select("id, title, author, description, categories, episode_count")
                .order("id")
                .range(offset, offset + PAGE_SIZE - 1)
            )

            if not self.force:
                query = query.is_("description_embedding", "null")

            response = query.execute()
            page = response.data
            if not page:
                break

            all_podcasts.extend(page)
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        if self.test_mode:
            all_podcasts = all_podcasts[:5]
        elif self.limit:
            all_podcasts = all_podcasts[:self.limit]

        return all_podcasts

    def load_episodes_for_podcasts(self, podcast_ids: list[int]) -> dict[int, list[dict]]:
        """Load top 3 recent episodes per podcast."""
        episodes_map: dict[int, list[dict]] = {pid: [] for pid in podcast_ids}

        # Batch load — get all episodes for these podcasts, sorted by published_at desc
        # Process in chunks to avoid query size limits
        chunk_size = 100
        for i in range(0, len(podcast_ids), chunk_size):
            chunk = podcast_ids[i:i + chunk_size]
            result = (
                self.sb.table("podcast_episodes")
                .select("podcast_target_id, title, published_at")
                .in_("podcast_target_id", chunk)
                .order("published_at", desc=True)
                .limit(chunk_size * 5)  # generous limit
                .execute()
            )

            for ep in result.data:
                pid = ep["podcast_target_id"]
                if pid in episodes_map and len(episodes_map[pid]) < 3:
                    episodes_map[pid].append(ep)

        return episodes_map

    def load_speakers(self) -> list[dict]:
        """Load speaker profiles needing embeddings."""
        query = self.sb.table("speaker_profiles").select("*").order("id")

        if not self.force:
            query = query.is_("profile_embedding", "null")

        result = query.execute()
        return result.data

    def embed_podcasts(self):
        """Embed all unembedded podcasts."""
        podcasts = self.load_podcasts()
        total = len(podcasts)
        print(f"\nPodcasts to embed: {total}")

        if total == 0:
            print("All podcasts already have embeddings (use --force to re-embed)")
            return

        # Load episodes for all podcasts
        podcast_ids = [p["id"] for p in podcasts]
        print("Loading recent episodes...")
        episodes_map = self.load_episodes_for_podcasts(podcast_ids)

        eps_with_episodes = sum(1 for eps in episodes_map.values() if eps)
        print(f"  {eps_with_episodes}/{total} podcasts have episode data")

        # Build texts
        texts = []
        ids = []
        for p in podcasts:
            text = build_podcast_text(p, episodes_map.get(p["id"], []))
            texts.append(text)
            ids.append(p["id"])

        # Embed in batches
        print(f"Embedding {total} podcasts in batches of {BATCH_SIZE}...")
        for batch_start in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[batch_start:batch_start + BATCH_SIZE]
            batch_ids = ids[batch_start:batch_start + BATCH_SIZE]

            try:
                vectors = self.generate_embeddings_batch(batch_texts)
                if not vectors:
                    print(f"  ERROR: Failed batch at {batch_start}")
                    self.stats["errors"] += len(batch_ids)
                    continue

                for vec, pid in zip(vectors, batch_ids):
                    if self.save_podcast_embedding(pid, vec):
                        self.stats["podcasts_embedded"] += 1
                    else:
                        self.stats["errors"] += 1

                print(f"  Batch {batch_start // BATCH_SIZE + 1}: embedded {len(batch_ids)} podcasts")

            except Exception as e:
                print(f"  ERROR in batch at {batch_start}: {e}")
                self.stats["errors"] += len(batch_ids)

    def embed_speakers(self):
        """Embed all unembedded speaker profiles."""
        speakers = self.load_speakers()
        total = len(speakers)
        print(f"\nSpeaker profiles to embed: {total}")

        if total == 0:
            print("All speakers already have embeddings (use --force to re-embed)")
            return

        # Build texts and embed one batch (only 2 speakers)
        texts = []
        ids = []
        for s in speakers:
            text = build_speaker_text(s)
            texts.append(text)
            ids.append(s["id"])
            print(f"  Speaker {s['name']}: {len(text)} chars")

        vectors = self.generate_embeddings_batch(texts)
        if not vectors:
            print("  ERROR: Failed to embed speakers")
            self.stats["errors"] += len(ids)
            return

        for vec, sid, speaker in zip(vectors, ids, speakers):
            if self.save_speaker_embedding(sid, vec):
                self.stats["speakers_embedded"] += 1
                print(f"  Embedded: {speaker['name']}")
            else:
                self.stats["errors"] += 1

    def run(self):
        if not self.connect():
            return False

        start_time = time.time()

        if not self.speakers_only:
            self.embed_podcasts()

        self.embed_speakers()

        elapsed = time.time() - start_time
        self._print_summary(elapsed)

        if self.pg_conn:
            self.pg_conn.close()

        return self.stats["errors"] == 0

    def _print_summary(self, elapsed: float):
        s = self.stats
        cost = s["total_tokens"] * 0.02 / 1_000_000

        print(f"\n{'='*60}")
        print("PODCAST EMBEDDING SUMMARY")
        print("=" * 60)
        print(f"  Podcasts embedded:    {s['podcasts_embedded']}")
        print(f"  Speakers embedded:    {s['speakers_embedded']}")
        print(f"  Errors:               {s['errors']}")
        print(f"  Total tokens:         {s['total_tokens']:,}")
        print(f"  API calls:            {s['api_calls']}")
        print(f"  Est. cost:            ${cost:.4f}")
        print(f"  Time elapsed:         {elapsed:.1f}s")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate embeddings for podcast targets and speaker profiles"
    )
    parser.add_argument("--test", "-t", action="store_true",
                        help="Process 5 podcasts + all speakers for validation")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Re-embed already-embedded items")
    parser.add_argument("--limit", "-n", type=int, default=None,
                        help="Max podcasts to process")
    parser.add_argument("--speakers-only", action="store_true",
                        help="Only embed speaker profiles")
    args = parser.parse_args()

    embedder = PodcastEmbedder(
        test_mode=args.test,
        force=args.force,
        limit=args.limit,
        speakers_only=args.speakers_only,
    )
    success = embedder.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
