#!/usr/bin/env python3
"""
Philanthropy Newsletter Voice Finder
=====================================
Deep-filters contacts to find the top 30-50 genuine philanthropy/social impact
leaders with strong LinkedIn post histories for newsletter curation.
"""

import os
import sys
import json
import re
from datetime import datetime
from collections import defaultdict

import dotenv
import psycopg2
import psycopg2.extras

dotenv.load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")

DB_CONFIG = {
    "host": "db.ypqsrejrsocebnldicke.supabase.co",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": os.getenv("SUPABASE_DB_PASSWORD"),
}

# ── Philanthropy role keywords (title/company matching) ──────────────────────
PHILANTHROPY_TITLE_KEYWORDS = [
    "foundation", "philanthrop", "grantmak", "program officer", "program director",
    "giving", "social impact", "impact invest", "social enterprise", "nonprofit",
    "non-profit", "ngo", "community development", "community foundation",
    "charitable", "donor", "endowment", "capacity build", "civic",
    "social justice", "equity", "mutual aid", "grassroots",
    "cdfi", "microfinance", "blended finance", "impact fund",
    "social venture", "mission-driven", "public interest",
    "human rights", "civil rights", "racial justice",
    "environmental justice", "climate justice",
    "development finance", "humanitarian",
    "poverty", "food bank", "housing",
]

PHILANTHROPY_COMPANY_KEYWORDS = [
    "foundation", "fund", "philanthrop", "trust", "endowment",
    "community", "nonprofit", "non-profit", "impact", "social",
    "united way", "red cross", "habitat", "salvation army",
    "institute", "council", "alliance", "coalition",
    "initiative", "center for", "centre for",
    "cdfi", "development finance",
]

# These indicate the person is NOT primarily in philanthropy
EXCLUDE_TITLE_PATTERNS = [
    r"\bsoftware engineer\b", r"\bdata scientist\b", r"\bproduct manager\b",
    r"\bmarketing manager\b", r"\bsales director\b", r"\baccount executive\b",
    r"\bdevops\b", r"\bfull.?stack\b", r"\bbackend\b", r"\bfrontend\b",
    r"\bml engineer\b", r"\bmachine learning engineer\b",
]

# Post content keywords that signal philanthropy topics
PHILANTHROPY_POST_KEYWORDS = [
    "philanthrop", "grantmak", "nonprofit", "non-profit", "foundation",
    "giving", "donor", "charitable", "social impact", "impact invest",
    "social enterprise", "community development", "capacity build",
    "equity", "justice", "mutual aid", "grassroots",
    "endowment", "cdfi", "microfinance", "blended finance",
    "social sector", "civil society", "public interest",
    "humanitarian", "social good", "social change",
    "fundrais", "grant", "program officer",
    "collective impact", "systems change", "theory of change",
    "racial equity", "economic mobility", "wealth gap",
    "trust-based", "participatory", "community-led",
    "impact measurement", "social return", "outcomes",
    "poverty", "food insecurity", "housing insecurity",
    "climate justice", "environmental justice",
    "human rights", "civic engagement", "democracy",
    "DEI", "diversity", "inclusion", "belonging",
]

# Journalist/media keywords
MEDIA_KEYWORDS = [
    "reporter", "journalist", "editor", "writer", "columnist",
    "correspondent", "podcast", "analyst", "researcher",
    "author", "contributor", "media", "press",
]

# ── Category definitions ─────────────────────────────────────────────────────
CATEGORIES = {
    "Capital Allocators": {
        "title_kw": ["foundation", "grantmak", "program officer", "program director",
                      "giving", "donor", "endowment", "chief philanthropy",
                      "vice president.*program", "director.*program",
                      "managing director.*foundation", "executive director.*foundation",
                      "president.*foundation", "trust", "giving circle",
                      "donor advised", "daf"],
        "company_kw": ["foundation", "fund", "trust", "endowment", "philanthrop",
                        "united way", "community foundation", "giving"],
    },
    "Field Infrastructure": {
        "title_kw": ["capacity build", "sector", "convener", "nonprofit tech",
                      "nonprofit technolog", "social sector", "affinity group",
                      "network director", "coalition", "alliance",
                      "consulting.*nonprofit", "advisor.*philanthrop",
                      "chief strategy.*nonprofit", "chief impact",
                      "systems change", "collective impact"],
        "company_kw": ["council", "alliance", "coalition", "initiative",
                        "institute", "center for", "centre for",
                        "advisory", "consulting"],
    },
    "Media & Analysts": {
        "title_kw": ["reporter", "journalist", "editor", "writer", "columnist",
                      "correspondent", "podcast", "analyst", "researcher",
                      "author", "contributor"],
        "company_kw": ["media", "news", "press", "journal", "chronicle",
                        "review", "magazine", "podcast"],
    },
    "Equity & Community": {
        "title_kw": ["grassroots", "mutual aid", "community organiz",
                      "community foundation", "civic", "social justice",
                      "racial justice", "equity director", "equity officer",
                      "chief equity", "community development", "community leader",
                      "neighborhood", "resident", "housing",
                      "food bank", "food justice"],
        "company_kw": ["community", "neighborhood", "civic", "justice",
                        "equity", "mutual aid", "grassroots",
                        "housing", "food bank"],
    },
    "Impact Investing": {
        "title_kw": ["impact invest", "social enterprise", "social venture",
                      "cdfi", "microfinance", "blended finance",
                      "development finance", "impact fund", "mission-driven",
                      "impact capital", "sustainable finance",
                      "esg", "responsible invest", "sri",
                      "venture philanthrop", "catalytic capital",
                      "impact partner", "impact director"],
        "company_kw": ["impact", "venture", "cdfi", "microfinance",
                        "social enterprise", "development finance",
                        "sustainable", "catalytic"],
    },
}


def connect_db():
    return psycopg2.connect(**DB_CONFIG)


def fetch_candidates(conn):
    """Fetch all contacts who have LinkedIn posts and relevant data."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Main query: contacts with posts, their ai_tags, and aggregated post stats
    cur.execute("""
        WITH post_stats AS (
            SELECT
                contact_id,
                count(*) as post_count,
                coalesce(sum(engagement_likes), 0) as total_likes,
                coalesce(sum(engagement_comments), 0) as total_comments,
                coalesce(sum(engagement_shares), 0) as total_shares
            FROM contact_linkedin_posts
            GROUP BY contact_id
        )
        SELECT
            c.id,
            c.first_name,
            c.last_name,
            c.position,
            c.company,
            c.linkedin_url,
            c.headline,
            c.summary,
            c.ai_tags,
            c.num_followers,
            c.enrich_follower_count,
            ps.post_count,
            ps.total_likes,
            ps.total_comments,
            ps.total_shares
        FROM contacts c
        INNER JOIN post_stats ps ON ps.contact_id = c.id
        WHERE c.ai_tags IS NOT NULL
        ORDER BY c.id
    """)
    candidates = cur.fetchall()
    print(f"[Step 2] Fetched {len(candidates)} contacts with posts and ai_tags")
    return candidates


def fetch_posts_for_contacts(conn, contact_ids):
    """Fetch the 5 most recent posts for each contact."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Use a window function to rank posts per contact
    cur.execute("""
        WITH ranked AS (
            SELECT
                contact_id,
                post_content,
                post_date,
                engagement_likes,
                engagement_comments,
                engagement_shares,
                ROW_NUMBER() OVER (PARTITION BY contact_id ORDER BY post_date DESC NULLS LAST) as rn
            FROM contact_linkedin_posts
            WHERE contact_id = ANY(%s)
        )
        SELECT * FROM ranked WHERE rn <= 5
        ORDER BY contact_id, rn
    """, (contact_ids,))

    posts_by_contact = defaultdict(list)
    for row in cur.fetchall():
        posts_by_contact[row["contact_id"]].append(row)

    return posts_by_contact


def match_keywords(text, keywords):
    """Check if any keyword appears in text (case-insensitive)."""
    if not text:
        return False, []
    text_lower = text.lower()
    matched = [kw for kw in keywords if kw.lower() in text_lower]
    return len(matched) > 0, matched


def count_philanthropy_post_keywords(posts):
    """Count how many philanthropy keywords appear across a contact's posts."""
    total_hits = 0
    keyword_set = set()
    for post in posts:
        content = (post.get("post_content") or "").lower()
        for kw in PHILANTHROPY_POST_KEYWORDS:
            if kw.lower() in content:
                total_hits += 1
                keyword_set.add(kw)
    return total_hits, keyword_set


def is_excluded_role(position):
    """Check if the position matches exclusion patterns."""
    if not position:
        return False
    pos_lower = position.lower()
    for pat in EXCLUDE_TITLE_PATTERNS:
        if re.search(pat, pos_lower):
            return True
    return False


def classify_category(contact, posts):
    """Assign the best-fit category. Returns (category_name, confidence, reason)."""
    position = (contact.get("position") or "").lower()
    company = (contact.get("company") or "").lower()
    headline = (contact.get("headline") or "").lower()
    combined_title = f"{position} {headline}"

    scores = {}
    for cat_name, cat_def in CATEGORIES.items():
        score = 0
        reasons = []
        # Title match
        for kw in cat_def["title_kw"]:
            if kw.lower() in combined_title:
                score += 3
                reasons.append(f"title match: '{kw}'")
        # Company match
        for kw in cat_def["company_kw"]:
            if kw.lower() in company:
                score += 2
                reasons.append(f"company match: '{kw}'")
        # Post content boost for Impact Investing (underrepresented)
        if cat_name == "Impact Investing":
            for post in posts:
                content = (post.get("post_content") or "").lower()
                for kw in ["impact invest", "social enterprise", "cdfi",
                           "blended finance", "catalytic capital", "impact fund",
                           "development finance", "microfinance", "esg",
                           "sustainable finance", "venture philanthrop"]:
                    if kw in content:
                        score += 1
                        reasons.append(f"post mention: '{kw}'")

        scores[cat_name] = (score, reasons)

    # Find best
    best_cat = max(scores, key=lambda x: scores[x][0])
    best_score, best_reasons = scores[best_cat]

    if best_score == 0:
        # Fallback: look at post content to decide
        post_text = " ".join((p.get("post_content") or "") for p in posts).lower()
        if any(kw in post_text for kw in ["impact invest", "social enterprise", "cdfi", "blended finance"]):
            return "Impact Investing", 1, ["post content fallback"]
        if any(kw in post_text for kw in ["grassroots", "mutual aid", "community organiz", "racial justice"]):
            return "Equity & Community", 1, ["post content fallback"]
        if any(kw in combined_title for kw in MEDIA_KEYWORDS):
            return "Media & Analysts", 1, ["title media keyword"]
        # Default to Capital Allocators for foundation/grantmaking folks
        return "Capital Allocators", 0, ["default"]

    return best_cat, best_score, best_reasons


def calculate_score(contact, posts, post_keyword_hits, category):
    """Calculate newsletter value score (0-100)."""
    post_count = contact.get("post_count") or 0
    total_likes = contact.get("total_likes") or 0
    total_comments = contact.get("total_comments") or 0
    followers_raw = contact.get("num_followers") or contact.get("enrich_follower_count") or 0
    try:
        followers = int(followers_raw)
    except (ValueError, TypeError):
        followers = 0

    # Post frequency score (0-25): more posts = better
    freq_score = min(25, post_count * 2.5)  # 10+ posts = max

    # Engagement score (0-30): avg engagement per post
    avg_engagement = (total_likes + total_comments) / max(post_count, 1)
    eng_score = min(30, avg_engagement * 1.5)  # 20+ avg = max

    # Follower score (0-20): logarithmic scale
    import math
    if followers > 0:
        follow_score = min(20, math.log10(followers) * 5)  # 10k+ = max
    else:
        follow_score = 0

    # Philanthropy relevance (0-15): keyword density in posts
    relevance_score = min(15, post_keyword_hits * 1.5)

    # Category bonus (0-10): boost underrepresented categories
    cat_bonus = {
        "Impact Investing": 10,
        "Equity & Community": 7,
        "Media & Analysts": 5,
        "Field Infrastructure": 5,
        "Capital Allocators": 3,
    }
    bonus = cat_bonus.get(category, 0)

    total = freq_score + eng_score + follow_score + relevance_score + bonus
    return round(total, 1)


def generate_rationale(contact, posts, keyword_set, category):
    """Generate a 2-3 sentence rationale for why this person was chosen."""
    position = contact.get("position") or "Unknown role"
    company = contact.get("company") or "Unknown org"
    post_count = contact.get("post_count") or 0
    followers_raw = contact.get("num_followers") or contact.get("enrich_follower_count") or 0
    try:
        followers = int(followers_raw)
    except (ValueError, TypeError):
        followers = 0
    avg_eng = (
        ((contact.get("total_likes") or 0) + (contact.get("total_comments") or 0))
        / max(post_count, 1)
    )

    parts = []
    parts.append(f"{position} at {company}")

    if followers > 5000:
        parts.append(f"with {followers:,} followers")
    elif followers > 1000:
        parts.append(f"with a solid {followers:,} followers")

    if avg_eng > 20:
        parts.append(f"generating strong engagement ({avg_eng:.0f} avg likes+comments per post)")
    elif avg_eng > 5:
        parts.append(f"with solid engagement ({avg_eng:.0f} avg per post)")

    if keyword_set:
        top_topics = list(keyword_set)[:4]
        parts.append(f"posts frequently about {', '.join(top_topics)}")

    # Build narrative
    rationale = ". ".join(parts[:3]) + "."
    return rationale


def main():
    conn = connect_db()

    # ── Step 1: Sample ai_tags ────────────────────────────────────────────
    print("=" * 80)
    print("STEP 1: ai_tags structure sample")
    print("=" * 80)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, first_name, last_name, ai_tags FROM contacts WHERE ai_tags IS NOT NULL LIMIT 3")
    for row in cur.fetchall():
        tags = row["ai_tags"] if isinstance(row["ai_tags"], dict) else json.loads(row["ai_tags"])
        print(f"\n  {row['first_name']} {row['last_name']}: keys = {list(tags.keys())}")
        if "giving_capacity" in tags:
            gc = tags["giving_capacity"]
            print(f"    giving_capacity.tier = {gc.get('tier')}, score = {gc.get('score')}")
        if "topical_affinity" in tags:
            ta = tags["topical_affinity"]
            topics = ta.get("topics", [])
            print(f"    topical_affinity: {len(topics)} topics, primary_interests = {ta.get('primary_interests', [])[:3]}")

    # ── Step 2: Fetch all candidates ──────────────────────────────────────
    print("\n" + "=" * 80)
    print("STEP 2: Fetching candidates with LinkedIn posts")
    print("=" * 80)
    candidates = fetch_candidates(conn)

    # ── Step 3: Smart filtering ───────────────────────────────────────────
    print("\n" + "=" * 80)
    print("STEP 3: Smart filtering for philanthropy/social impact leaders")
    print("=" * 80)

    # First pass: identify potential matches by role/company
    potential = []
    for c in candidates:
        position = c.get("position") or ""
        company = c.get("company") or ""
        headline = c.get("headline") or ""
        combined = f"{position} {company} {headline}".lower()

        tags = c["ai_tags"] if isinstance(c["ai_tags"], dict) else json.loads(c["ai_tags"])
        giving_tier = tags.get("giving_capacity", {}).get("tier", "")
        topical = tags.get("topical_affinity", {})
        topics = topical.get("topics", [])
        primary_interests = topical.get("primary_interests", [])

        # Check if excluded role
        if is_excluded_role(position):
            continue

        # Criterion 1: Title/company matches philanthropy org
        title_match, title_kws = match_keywords(combined, PHILANTHROPY_TITLE_KEYWORDS)

        # Criterion 2: Major donor + philanthropy topics in ai_tags
        has_philanthropy_topic = any(
            t.get("topic", "") in ["philanthropy", "social_impact_tech", "nonprofit_leadership",
                                     "social_justice", "community_development", "impact_investing"]
            and t.get("strength", "") in ["high", "medium"]
            for t in topics
        )
        is_major_donor_philanthropist = giving_tier == "major_donor" and has_philanthropy_topic

        # Criterion 3: Media covering philanthropy
        media_match, _ = match_keywords(combined, MEDIA_KEYWORDS)
        is_philanthropy_media = media_match and has_philanthropy_topic

        # Criterion 4: Is their title/company PRIMARILY philanthropy?
        title_is_philanthropy_primary = any(
            kw in combined for kw in [
                "foundation", "philanthrop", "grantmak", "program officer",
                "social impact", "impact invest", "social enterprise",
                "nonprofit", "non-profit", "community development",
                "community foundation", "cdfi", "giving",
                "mutual aid", "grassroots", "civic engagement",
            ]
        )

        # Criterion 5: primary_interests include philanthropy-related items
        philanthropy_interests = [
            pi for pi in primary_interests
            if any(kw in pi.lower() for kw in [
                "philanthrop", "social impact", "nonprofit", "giving",
                "grant", "community development", "justice", "equity",
                "impact invest", "social enterprise", "cdfi"
            ])
        ]
        has_strong_interests = len(philanthropy_interests) >= 2

        # Criterion 6: Strong ai_tags philanthropy topics
        strong_philanthropy_topics = [
            t for t in topics
            if t.get("topic", "") in [
                "philanthropy", "social_impact_tech", "nonprofit_leadership",
                "social_justice", "community_development", "impact_investing",
                "social_enterprise", "public_interest_tech"
            ]
            and t.get("strength", "") == "high"
        ]
        has_strong_tags = len(strong_philanthropy_topics) >= 1

        # Gate: require primary philanthropy role OR strong multi-signal evidence
        if (title_is_philanthropy_primary
            or is_major_donor_philanthropist
            or is_philanthropy_media
            or (has_strong_interests and has_strong_tags)):
            c["_tags"] = tags
            c["_title_match"] = title_match
            c["_title_kws"] = title_kws
            c["_giving_tier"] = giving_tier
            c["_has_philanthropy_topic"] = has_philanthropy_topic
            c["_philanthropy_interests"] = philanthropy_interests
            potential.append(c)

    print(f"  First pass (role/company/tags filter): {len(potential)} candidates")

    # Fetch posts for all potential candidates
    contact_ids = [c["id"] for c in potential]
    posts_by_contact = fetch_posts_for_contacts(conn, contact_ids)
    print(f"  Fetched posts for {len(posts_by_contact)} contacts")

    # Second pass: verify post content is actually about philanthropy
    filtered = []
    for c in potential:
        posts = posts_by_contact.get(c["id"], [])
        if not posts:
            continue

        post_hits, keyword_set = count_philanthropy_post_keywords(posts)

        # Require at least SOME philanthropy content in posts
        # More lenient for people whose TITLE is clearly philanthropy
        title_is_clearly_philanthropy = any(
            kw in (c.get("position") or "").lower()
            for kw in ["foundation", "philanthrop", "grantmak", "nonprofit",
                        "impact invest", "social enterprise", "cdfi",
                        "community development", "social impact"]
        )
        company_is_clearly_philanthropy = any(
            kw in (c.get("company") or "").lower()
            for kw in ["foundation", "philanthrop", "trust", "fund",
                        "nonprofit", "community", "institute"]
        )

        if title_is_clearly_philanthropy or company_is_clearly_philanthropy:
            # Their role IS philanthropy, posts can be about anything related
            min_hits = 1  # at least 1 philanthropy keyword even for clear roles
        elif c.get("_giving_tier") == "major_donor":
            min_hits = 4  # major donors need strong post evidence
        else:
            min_hits = 5  # others need very clear post evidence

        # Also require minimum post activity (at least 3 posts)
        if (c.get("post_count") or 0) < 3:
            continue

        if post_hits >= min_hits:
            c["_posts"] = posts
            c["_post_keyword_hits"] = post_hits
            c["_keyword_set"] = keyword_set
            filtered.append(c)

    print(f"  Second pass (post content verification): {len(filtered)} candidates")

    # ── Step 4: Categorize ────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("STEP 4: Categorizing contacts")
    print("=" * 80)

    categorized = defaultdict(list)
    for c in filtered:
        cat, conf, reasons = classify_category(c, c["_posts"])
        c["_category"] = cat
        c["_cat_confidence"] = conf
        c["_cat_reasons"] = reasons
        categorized[cat].append(c)

    for cat, members in sorted(categorized.items()):
        print(f"  {cat}: {len(members)} contacts")

    # ── Step 5: Score and rank ────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("STEP 5: Scoring and ranking")
    print("=" * 80)

    for cat in categorized:
        for c in categorized[cat]:
            score = calculate_score(
                c, c["_posts"], c["_post_keyword_hits"], cat
            )
            c["_score"] = score

        # Sort by score descending
        categorized[cat].sort(key=lambda x: x["_score"], reverse=True)

    # Select top candidates: aim for 30-50 total
    # Distribute across categories, ensuring Impact Investing gets extra slots
    target_per_category = {
        "Capital Allocators": 12,
        "Field Infrastructure": 10,
        "Media & Analysts": 8,
        "Equity & Community": 10,
        "Impact Investing": 12,
    }

    selected = defaultdict(list)
    total_selected = 0
    for cat, max_n in target_per_category.items():
        available = categorized.get(cat, [])
        n = min(max_n, len(available))
        selected[cat] = available[:n]
        total_selected += n
        print(f"  {cat}: selected {n}/{len(available)} (target {max_n})")

    print(f"\n  TOTAL SELECTED: {total_selected}")

    # ── Step 6: Output ────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("STEP 6: FINAL RESULTS — TOP PHILANTHROPY NEWSLETTER VOICES")
    print("=" * 80)

    for cat in ["Capital Allocators", "Field Infrastructure", "Media & Analysts",
                 "Equity & Community", "Impact Investing"]:
        members = selected.get(cat, [])
        if not members:
            continue

        print(f"\n{'=' * 80}")
        print(f"=== {cat.upper()} === ({len(members)} contacts)")
        print(f"{'=' * 80}")

        for c in members:
            name = f"{c['first_name'] or ''} {c['last_name'] or ''}".strip()
            position = c.get("position") or "Unknown"
            company = c.get("company") or "Unknown"
            linkedin = c.get("linkedin_url") or "N/A"
            followers_raw = c.get("num_followers") or c.get("enrich_follower_count") or 0
            try:
                followers = int(followers_raw)
            except (ValueError, TypeError):
                followers = 0
            post_count = c.get("post_count") or 0
            total_likes = c.get("total_likes") or 0
            total_comments = c.get("total_comments") or 0
            avg_eng = (total_likes + total_comments) / max(post_count, 1)
            score = c.get("_score", 0)

            rationale = generate_rationale(c, c["_posts"], c["_keyword_set"], cat)

            print(f"\nNAME: {name}")
            print(f"TITLE: {position} at {company}")
            print(f"LINKEDIN: {linkedin}")
            print(f"FOLLOWERS: {followers:,}")
            print(f"POSTS: {post_count} | AVG ENGAGEMENT: {avg_eng:.1f} likes+comments/post | SCORE: {score}")
            print(f"WHY CHOSEN: {rationale}")
            print(f"SAMPLE POSTS:")

            for i, post in enumerate(c["_posts"][:3], 1):
                content = (post.get("post_content") or "")[:200]
                # Clean up newlines for display
                content = content.replace("\n", " ").strip()
                date = post.get("post_date")
                if date:
                    if isinstance(date, str):
                        date_str = date[:10]
                    else:
                        date_str = date.strftime("%Y-%m-%d")
                else:
                    date_str = "N/A"
                likes = post.get("engagement_likes") or 0
                print(f"  {i}. {content} ({date_str}, {likes} likes)")

            print("---")

    conn.close()
    print(f"\n{'=' * 80}")
    print(f"DONE. {total_selected} voices selected across {len(selected)} categories.")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
