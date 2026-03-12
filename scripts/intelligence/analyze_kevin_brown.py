#!/usr/bin/env python3
"""
Kevin L. Brown LinkedIn Content Analysis
=========================================
Deep analysis of Kevin's 100 LinkedIn posts to deconstruct what makes his content
work at scale. Outputs structured JSON catalog and prints summary stats.

Usage:
    python scripts/intelligence/analyze_kevin_brown.py [--step catalog|themes|rhetoric|format|playbook]

Steps:
    catalog  - US-001: Extract posts, compute metrics, save JSON catalog
    themes   - US-002: GPT-5 mini theme/message analysis
    rhetoric - US-003: Rhetorical device deep-dive
    format   - US-004: Length, format, timing optimization
    playbook - US-005: Synthesize Kevin's content playbook
"""

import argparse
import json
import os
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from enum import Enum
from typing import List

import openai
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from supabase import create_client

load_dotenv()

CATALOG_PATH = "docs/kevin_brown_posts_catalog.json"
INFLUENCER_FILTER = "%kevinlbrown%"
GPT_WORKERS = 150

# ── OpenAI Client ──
oai = openai.OpenAI(api_key=os.environ.get("OPENAI_APIKEY"))


# ── Pydantic Schemas for GPT-5 mini structured output ──


class PrimaryTheme(str, Enum):
    storytelling = "storytelling"
    fundraising_strategy = "fundraising_strategy"
    donor_psychology = "donor_psychology"
    advocacy_activism = "advocacy_activism"
    visual_creative = "visual_creative"
    sector_trends = "sector_trends"
    leadership = "leadership"
    events_conferences = "events_conferences"
    ai_technology = "ai_technology"
    career_advice = "career_advice"
    other = "other"


class ContentCategory(str, Enum):
    educational = "educational"
    inspirational = "inspirational"
    contrarian = "contrarian"
    curated_resource = "curated_resource"
    listicle = "listicle"
    case_study = "case_study"
    hot_take = "hot_take"
    call_to_action = "call_to_action"


class EmotionalAppeal(str, Enum):
    outrage = "outrage"
    aspiration = "aspiration"
    humor = "humor"
    empathy = "empathy"
    urgency = "urgency"
    curiosity = "curiosity"
    pride = "pride"
    fear = "fear"


class TargetAudience(str, Enum):
    fundraisers = "fundraisers"
    nonprofit_leaders = "nonprofit_leaders"
    comms_professionals = "comms_professionals"
    donors = "donors"
    general_social_impact = "general_social_impact"


class RhetoricalDevice(str, Enum):
    anaphora = "anaphora"
    antithesis = "antithesis"
    tricolon = "tricolon"
    amplification = "amplification"
    irony = "irony"
    metaphor = "metaphor"
    analogy = "analogy"
    rhetorical_question = "rhetorical_question"
    repetition = "repetition"
    enumeration = "enumeration"
    juxtaposition = "juxtaposition"
    hyperbole = "hyperbole"
    understatement = "understatement"
    personification = "personification"
    alliteration = "alliteration"


class ThemeAnalysis(BaseModel):
    primary_theme: PrimaryTheme
    core_message: str = Field(description="1-sentence summary of the post's central argument or insight")
    content_category: ContentCategory
    emotional_appeal: EmotionalAppeal
    target_audience: TargetAudience
    rhetorical_devices: List[RhetoricalDevice] = Field(description="List of rhetorical devices used in the post")


# ── US-003: Rhetorical Deep-Dive Schemas ──


class OpeningHook(str, Enum):
    provocative_statement = "provocative_statement"
    question = "question"
    statistic = "statistic"
    quote = "quote"
    emoji_hook = "emoji_hook"
    story_opening = "story_opening"
    list_preview = "list_preview"
    contrarian_claim = "contrarian_claim"
    imperative_command = "imperative_command"


class StructuralPattern(str, Enum):
    problem_solution = "problem_solution"
    list_format = "list_format"
    narrative_arc = "narrative_arc"
    before_after = "before_after"
    myth_bust = "myth_bust"
    build_to_reveal = "build_to_reveal"
    call_and_response = "call_and_response"
    parallel_structure = "parallel_structure"


class FramingTechnique(str, Enum):
    reframing = "reframing"
    anchor_then_shift = "anchor_then_shift"
    common_enemy = "common_enemy"
    identity_appeal = "identity_appeal"
    scarcity = "scarcity"
    social_proof = "social_proof"
    authority = "authority"
    contrast = "contrast"
    storytelling_frame = "storytelling_frame"


class CallToAction(str, Enum):
    none = "none"
    follow_for_more = "follow_for_more"
    comment_below = "comment_below"
    share_this = "share_this"
    save_this = "save_this"
    link_in_comments = "link_in_comments"
    tag_someone = "tag_someone"
    dm_me = "dm_me"


class Tone(str, Enum):
    authoritative = "authoritative"
    conversational = "conversational"
    passionate = "passionate"
    analytical = "analytical"
    playful = "playful"
    urgent = "urgent"
    reflective = "reflective"


class LineBreakStyle(str, Enum):
    single_sentence_lines = "single_sentence_lines"
    short_paragraphs = "short_paragraphs"
    mixed = "mixed"
    long_paragraphs = "long_paragraphs"


class RhetoricAnalysis(BaseModel):
    opening_hook: OpeningHook = Field(description="Type of opening hook used in the first line")
    structural_pattern: StructuralPattern = Field(description="Overall structural pattern of the post")
    rhetorical_devices: List[RhetoricalDevice] = Field(description="All rhetorical/literary devices clearly present")
    framing_technique: FramingTechnique = Field(description="Primary framing technique used")
    call_to_action: CallToAction = Field(description="Type of call to action at the end")
    tone: Tone = Field(description="Overall tone of the post")
    line_break_style: LineBreakStyle = Field(description="How the author uses line breaks and whitespace")
    uses_emoji: bool = Field(description="Whether the post uses emoji")
    uses_bold_unicode: bool = Field(description="Whether the post uses bold unicode text (𝗯𝗼𝗹𝗱 style)")
    has_hook_gap: bool = Field(description="Whether line 1 is a hook followed by a blank line before main content")


THEME_SYSTEM_PROMPT = """You are a content strategist analyzing LinkedIn posts by Kevin L. Brown, a nonprofit communications and fundraising thought leader.

For each post, extract:
1. primary_theme: The dominant topic/theme
2. core_message: A single sentence capturing the post's central argument or insight
3. content_category: The type of content (educational, inspirational, contrarian, etc.)
4. emotional_appeal: The primary emotion the post targets
5. target_audience: Who this post is primarily aimed at
6. rhetorical_devices: List of rhetorical/literary devices used

Be precise and specific. The core_message should capture Kevin's actual point, not just the topic.
For rhetorical_devices, only include devices that are clearly present — don't force-fit."""


def get_supabase():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def fetch_all_posts():
    """Fetch all Kevin Brown posts from influencer_posts table."""
    sb = get_supabase()
    resp = (
        sb.table("influencer_posts")
        .select("id, post_url, post_content, post_date, engagement_likes, engagement_comments, engagement_shares, engagement_total, media_type")
        .ilike("influencer_url", INFLUENCER_FILTER)
        .order("engagement_total", desc=True)
        .limit(200)
        .execute()
    )
    return resp.data


def length_bucket(char_count):
    if char_count < 300:
        return "short (<300)"
    elif char_count < 800:
        return "medium (300-800)"
    elif char_count < 1500:
        return "long (800-1500)"
    else:
        return "very_long (1500+)"


def compute_post_metrics(post):
    """Compute derived metrics for a single post."""
    likes = post["engagement_likes"] or 0
    comments = post["engagement_comments"] or 0
    shares = post["engagement_shares"] or 0
    total = post["engagement_total"] or 0
    content = post["post_content"] or ""
    char_count = len(content)

    # Ratios (avoid division by zero)
    comment_to_like = round(comments / likes, 4) if likes > 0 else 0
    share_to_like = round(shares / likes, 4) if likes > 0 else 0

    # First line (hook) length
    first_line = content.split("\n")[0].strip() if content else ""
    hook_length = len(first_line)

    # Line count
    lines = [l for l in content.split("\n") if l.strip()] if content else []
    line_count = len(lines)

    # Day of week from post_date
    post_date_str = post["post_date"]
    day_of_week = None
    iso_date = None
    if post_date_str:
        try:
            dt = datetime.fromisoformat(post_date_str.replace("Z", "+00:00"))
            day_of_week = dt.strftime("%A")
            iso_date = dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            pass

    return {
        "id": post["id"],
        "post_url": post["post_url"],
        "post_date": post_date_str,
        "iso_date": iso_date,
        "day_of_week": day_of_week,
        "post_content": content,
        "media_type": post["media_type"],
        "engagement_likes": likes,
        "engagement_comments": comments,
        "engagement_shares": shares,
        "engagement_total": total,
        "char_count": char_count,
        "hook_length": hook_length,
        "line_count": line_count,
        "length_bucket": length_bucket(char_count),
        "comment_to_like_ratio": comment_to_like,
        "share_to_like_ratio": share_to_like,
    }


def print_table(title, headers, rows, col_widths=None):
    """Print a formatted text table."""
    if not col_widths:
        col_widths = []
        for i, h in enumerate(headers):
            max_w = len(str(h))
            for r in rows:
                max_w = max(max_w, len(str(r[i])))
            col_widths.append(min(max_w + 2, 40))

    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

    header_line = ""
    for i, h in enumerate(headers):
        header_line += str(h).ljust(col_widths[i])
    print(header_line)
    print("-" * sum(col_widths))

    for r in rows:
        line = ""
        for i, val in enumerate(r):
            line += str(val).ljust(col_widths[i])
        print(line)


def step_catalog():
    """US-001: Extract and catalog all posts with metrics."""
    print("Fetching all Kevin Brown posts...")
    posts = fetch_all_posts()
    print(f"  Found {len(posts)} posts")

    # Compute metrics for each post
    catalog = [compute_post_metrics(p) for p in posts]

    # ── Summary Stats ──
    totals = [p["engagement_total"] for p in catalog]
    likes = [p["engagement_likes"] for p in catalog]
    comments = [p["engagement_comments"] for p in catalog]
    shares = [p["engagement_shares"] for p in catalog]
    lengths = [p["char_count"] for p in catalog]
    hook_lengths = [p["hook_length"] for p in catalog]

    sorted_totals = sorted(totals)
    p75 = sorted_totals[int(len(sorted_totals) * 0.75)]
    p90 = sorted_totals[int(len(sorted_totals) * 0.90)]

    dates = [p["iso_date"] for p in catalog if p["iso_date"]]
    date_range = f"{min(dates)} to {max(dates)}" if dates else "N/A"

    print_table(
        "OVERALL ENGAGEMENT STATS",
        ["Metric", "Value"],
        [
            ["Total posts", len(catalog)],
            ["Date range", date_range],
            ["Min engagement", min(totals)],
            ["Avg engagement", round(statistics.mean(totals))],
            ["Median engagement", round(statistics.median(totals))],
            ["P75 engagement", p75],
            ["P90 engagement", p90],
            ["Max engagement", max(totals)],
            ["Avg likes", round(statistics.mean(likes))],
            ["Avg comments", round(statistics.mean(comments))],
            ["Avg shares", round(statistics.mean(shares))],
            ["Avg char length", round(statistics.mean(lengths))],
            ["Avg hook length", round(statistics.mean(hook_lengths))],
        ],
    )

    # ── Engagement Distribution ──
    brackets = [
        ("0-100", 0, 100),
        ("101-200", 101, 200),
        ("201-500", 201, 500),
        ("501-1000", 501, 1000),
        ("1000+", 1001, 999999),
    ]
    dist_rows = []
    for label, lo, hi in brackets:
        cnt = sum(1 for t in totals if lo <= t <= hi)
        pct = round(cnt / len(totals) * 100, 1)
        dist_rows.append([label, cnt, f"{pct}%"])

    print_table(
        "ENGAGEMENT DISTRIBUTION",
        ["Range", "Count", "Pct"],
        dist_rows,
    )

    # ── Length Bucket Analysis ──
    buckets = {}
    for p in catalog:
        b = p["length_bucket"]
        if b not in buckets:
            buckets[b] = []
        buckets[b].append(p["engagement_total"])

    bucket_order = ["short (<300)", "medium (300-800)", "long (800-1500)", "very_long (1500+)"]
    bucket_rows = []
    for b in bucket_order:
        if b in buckets:
            vals = buckets[b]
            bucket_rows.append([
                b,
                len(vals),
                round(statistics.mean(vals)),
                round(statistics.median(vals)),
                max(vals),
            ])

    print_table(
        "ENGAGEMENT BY LENGTH BUCKET",
        ["Bucket", "Count", "Avg", "Median", "Max"],
        bucket_rows,
    )

    # ── Media Type Analysis ──
    media_types = {}
    for p in catalog:
        mt = p["media_type"] or "unknown"
        if mt not in media_types:
            media_types[mt] = []
        media_types[mt].append(p)

    media_rows = []
    for mt, posts_list in sorted(media_types.items(), key=lambda x: -len(x[1])):
        eng = [p["engagement_total"] for p in posts_list]
        clr = [p["comment_to_like_ratio"] for p in posts_list]
        slr = [p["share_to_like_ratio"] for p in posts_list]
        media_rows.append([
            mt,
            len(posts_list),
            round(statistics.mean(eng)),
            round(statistics.median(eng)),
            round(statistics.mean(clr), 3),
            round(statistics.mean(slr), 3),
        ])

    print_table(
        "ENGAGEMENT BY MEDIA TYPE",
        ["Type", "Count", "Avg Eng", "Median", "Comment/Like", "Share/Like"],
        media_rows,
    )

    # ── Top 10 Posts ──
    top10_rows = []
    for p in catalog[:10]:
        snippet = p["post_content"][:80].replace("\n", " ") + "..."
        top10_rows.append([
            p["engagement_total"],
            p["media_type"],
            p["char_count"],
            snippet,
        ])

    print_table(
        "TOP 10 POSTS BY ENGAGEMENT",
        ["Engagement", "Type", "Chars", "Snippet"],
        top10_rows,
        col_widths=[12, 10, 8, 85],
    )

    # ── Day of Week ──
    dow = {}
    for p in catalog:
        d = p["day_of_week"]
        if d:
            if d not in dow:
                dow[d] = []
            dow[d].append(p["engagement_total"])

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_rows = []
    for d in day_order:
        if d in dow:
            vals = dow[d]
            dow_rows.append([d, len(vals), round(statistics.mean(vals)), round(statistics.median(vals))])

    print_table(
        "ENGAGEMENT BY DAY OF WEEK",
        ["Day", "Posts", "Avg Eng", "Median"],
        dow_rows,
    )

    # ── Save Catalog ──
    catalog_data = {
        "metadata": {
            "influencer": "Kevin L. Brown",
            "influencer_url": "kevinlbrown",
            "total_posts": len(catalog),
            "date_range": date_range,
            "generated_at": datetime.now().isoformat(),
            "steps_completed": ["catalog"],
        },
        "summary": {
            "engagement": {
                "min": min(totals),
                "avg": round(statistics.mean(totals)),
                "median": round(statistics.median(totals)),
                "p75": p75,
                "p90": p90,
                "max": max(totals),
            },
            "avg_likes": round(statistics.mean(likes)),
            "avg_comments": round(statistics.mean(comments)),
            "avg_shares": round(statistics.mean(shares)),
            "avg_char_length": round(statistics.mean(lengths)),
        },
        "posts": catalog,
    }

    os.makedirs(os.path.dirname(CATALOG_PATH), exist_ok=True)
    with open(CATALOG_PATH, "w") as f:
        json.dump(catalog_data, f, indent=2, default=str)

    print(f"\nCatalog saved to {CATALOG_PATH} ({len(catalog)} posts)")
    print("US-001 COMPLETE")


def analyze_post_theme(post):
    """Use GPT-5 mini to analyze a single post's theme and content."""
    content = post["post_content"] or ""
    engagement = post["engagement_total"]
    media = post["media_type"] or "unknown"

    user_input = f"""Analyze this LinkedIn post by Kevin L. Brown.

Post ({media} format, {engagement} total engagement, {len(content)} chars):
---
{content}
---

Extract the theme, core message, content category, emotional appeal, target audience, and rhetorical devices."""

    try:
        resp = oai.responses.parse(
            model="gpt-5-mini",
            instructions=THEME_SYSTEM_PROMPT,
            input=user_input,
            text_format=ThemeAnalysis,
        )
        result = resp.output_parsed
        return post["id"], {
            "primary_theme": result.primary_theme.value,
            "core_message": result.core_message,
            "content_category": result.content_category.value,
            "emotional_appeal": result.emotional_appeal.value,
            "target_audience": result.target_audience.value,
            "rhetorical_devices": [d.value for d in result.rhetorical_devices],
        }
    except Exception as e:
        print(f"  ERROR on post {post['id']}: {e}")
        return post["id"], None


def step_themes():
    """US-002: GPT-5 mini theme and content analysis for all posts."""
    # Load existing catalog
    if not os.path.exists(CATALOG_PATH):
        print(f"ERROR: Catalog not found at {CATALOG_PATH}. Run --step catalog first.")
        return

    with open(CATALOG_PATH) as f:
        catalog_data = json.load(f)

    posts = catalog_data["posts"]
    print(f"Loaded {len(posts)} posts from catalog")
    print(f"Running GPT-5 mini theme analysis with {GPT_WORKERS} workers...")

    # ── Parallel GPT analysis ──
    results = {}
    completed = 0
    with ThreadPoolExecutor(max_workers=GPT_WORKERS) as executor:
        futures = {executor.submit(analyze_post_theme, p): p["id"] for p in posts}
        for future in as_completed(futures):
            post_id, analysis = future.result()
            if analysis:
                results[post_id] = analysis
            completed += 1
            if completed % 25 == 0:
                print(f"  Analyzed {completed}/{len(posts)} posts...")

    print(f"  Successfully analyzed {len(results)}/{len(posts)} posts")

    # ── Enrich catalog posts with theme data ──
    for post in posts:
        if post["id"] in results:
            post.update(results[post["id"]])

    # ── Aggregation Tables ──

    # Helper: group posts by field and compute avg engagement
    def agg_by_field(field_name):
        groups = {}
        for p in posts:
            val = p.get(field_name)
            if val:
                if val not in groups:
                    groups[val] = []
                groups[val].append(p["engagement_total"])
        rows = []
        for val, engs in sorted(groups.items(), key=lambda x: -statistics.mean(x[1])):
            rows.append([
                val,
                len(engs),
                round(statistics.mean(engs)),
                round(statistics.median(engs)),
                max(engs),
            ])
        return rows

    # Theme × Engagement
    print_table(
        "THEME × AVG ENGAGEMENT (sorted by avg)",
        ["Theme", "Count", "Avg", "Median", "Max"],
        agg_by_field("primary_theme"),
    )

    # Content Category × Engagement
    print_table(
        "CONTENT CATEGORY × AVG ENGAGEMENT",
        ["Category", "Count", "Avg", "Median", "Max"],
        agg_by_field("content_category"),
    )

    # Emotional Appeal × Engagement
    print_table(
        "EMOTIONAL APPEAL × AVG ENGAGEMENT",
        ["Appeal", "Count", "Avg", "Median", "Max"],
        agg_by_field("emotional_appeal"),
    )

    # Target Audience × Engagement
    print_table(
        "TARGET AUDIENCE × AVG ENGAGEMENT",
        ["Audience", "Count", "Avg", "Median", "Max"],
        agg_by_field("target_audience"),
    )

    # ── Top 10 Core Messages by Engagement ──
    messages = []
    for p in posts:
        cm = p.get("core_message")
        if cm:
            messages.append([p["engagement_total"], cm[:90], p["primary_theme"]])
    messages.sort(key=lambda x: -x[0])
    print_table(
        "TOP 10 CORE MESSAGES BY ENGAGEMENT",
        ["Engagement", "Core Message", "Theme"],
        messages[:10],
        col_widths=[12, 92, 25],
    )

    # ── Rhetorical Device Frequency ──
    device_counts = {}
    device_eng = {}
    for p in posts:
        devs = p.get("rhetorical_devices", [])
        for d in devs:
            device_counts[d] = device_counts.get(d, 0) + 1
            if d not in device_eng:
                device_eng[d] = []
            device_eng[d].append(p["engagement_total"])

    device_rows = []
    for d, cnt in sorted(device_counts.items(), key=lambda x: -x[1]):
        device_rows.append([
            d,
            cnt,
            round(statistics.mean(device_eng[d])),
            round(statistics.median(device_eng[d])),
        ])
    print_table(
        "RHETORICAL DEVICE FREQUENCY & ENGAGEMENT",
        ["Device", "Count", "Avg Eng", "Median Eng"],
        device_rows,
    )

    # ── Update and save catalog ──
    catalog_data["metadata"]["steps_completed"].append("themes")
    catalog_data["metadata"]["themes_analyzed_at"] = datetime.now().isoformat()

    # Add theme summary to catalog
    theme_summary = {}
    for field in ["primary_theme", "content_category", "emotional_appeal", "target_audience"]:
        groups = {}
        for p in posts:
            val = p.get(field)
            if val:
                if val not in groups:
                    groups[val] = []
                groups[val].append(p["engagement_total"])
        theme_summary[field] = {
            val: {"count": len(engs), "avg_engagement": round(statistics.mean(engs))}
            for val, engs in sorted(groups.items(), key=lambda x: -statistics.mean(x[1]))
        }
    catalog_data["theme_summary"] = theme_summary

    with open(CATALOG_PATH, "w") as f:
        json.dump(catalog_data, f, indent=2, default=str)

    print(f"\nCatalog updated with theme analysis at {CATALOG_PATH}")
    print("US-002 COMPLETE")


# ── US-003: Rhetoric Analysis ──

RHETORIC_SYSTEM_PROMPT = """You are a rhetoric and persuasion expert analyzing LinkedIn posts by Kevin L. Brown, a nonprofit communications and fundraising thought leader with massive LinkedIn reach.

For each post, analyze the STRUCTURE and TECHNIQUE — not the topic. Focus on:

1. opening_hook: What type of hook does the first line use? Look at ONLY the first line.
   - provocative_statement: Bold claim that challenges assumptions
   - question: Opens with a question
   - statistic: Opens with a number or data point
   - quote: Opens with a quote from someone
   - emoji_hook: Opens with emoji as the attention-grabber
   - story_opening: Opens with a narrative/anecdote
   - list_preview: Opens by previewing a list ("Here are 5 things...")
   - contrarian_claim: Opens by disagreeing with conventional wisdom
   - imperative_command: Opens with a direct command ("Stop doing X")

2. structural_pattern: How is the overall post organized?
   - problem_solution: States a problem then offers solution(s)
   - list_format: Organized as a numbered or bulleted list
   - narrative_arc: Tells a story with beginning, middle, end
   - before_after: Contrasts a before and after state
   - myth_bust: States a myth/misconception then debunks it
   - build_to_reveal: Builds tension/context then reveals the key insight
   - call_and_response: Series of statements followed by responses
   - parallel_structure: Repeating grammatical patterns to make points

3. rhetorical_devices: Which specific devices are CLEARLY present? Only include devices you can point to specific text for.

4. framing_technique: How does the author frame the argument?
   - reframing: Takes a familiar concept and presents it differently
   - anchor_then_shift: Establishes one frame then pivots to another
   - common_enemy: Unites audience against a shared adversary/problem
   - identity_appeal: Appeals to audience's professional identity
   - scarcity: Creates urgency through limited time/resources
   - social_proof: Uses examples of others doing it
   - authority: Leverages expertise or credentials
   - contrast: Places two things side by side to highlight differences
   - storytelling_frame: Wraps the argument in a narrative

5. call_to_action: What does the post ask readers to do at the end?
6. tone: What is the overall emotional register?
7. line_break_style: How does the author use whitespace?
8. uses_emoji: Are emoji present anywhere in the post?
9. uses_bold_unicode: Does the post use special bold unicode characters (𝗯𝗼𝗹𝗱 𝘁𝗲𝘅𝘁 like this)?
10. has_hook_gap: Is there a blank line between the first line (hook) and the rest of the content?

Be precise. Every choice should be defensible with evidence from the text."""


def analyze_post_rhetoric(post):
    """Use GPT-5 mini to analyze a single post's rhetorical structure."""
    content = post["post_content"] or ""
    engagement = post["engagement_total"]
    media = post["media_type"] or "unknown"

    user_input = f"""Analyze the rhetorical structure and techniques of this LinkedIn post by Kevin L. Brown.

Post ({media} format, {engagement} total engagement, {len(content)} chars):
---
{content}
---

Identify the opening hook type, structural pattern, rhetorical devices, framing technique, call to action, tone, line break style, emoji usage, bold unicode usage, and hook gap."""

    try:
        resp = oai.responses.parse(
            model="gpt-5-mini",
            instructions=RHETORIC_SYSTEM_PROMPT,
            input=user_input,
            text_format=RhetoricAnalysis,
        )
        result = resp.output_parsed
        return post["id"], {
            "opening_hook": result.opening_hook.value,
            "structural_pattern": result.structural_pattern.value,
            "rhetoric_devices": [d.value for d in result.rhetorical_devices],
            "framing_technique": result.framing_technique.value,
            "call_to_action": result.call_to_action.value,
            "tone": result.tone.value,
            "line_break_style": result.line_break_style.value,
            "uses_emoji": result.uses_emoji,
            "uses_bold_unicode": result.uses_bold_unicode,
            "has_hook_gap": result.has_hook_gap,
        }
    except Exception as e:
        print(f"  ERROR on post {post['id']}: {e}")
        return post["id"], None


def step_rhetoric():
    """US-003: Rhetorical device and framing deep-dive for all posts."""
    if not os.path.exists(CATALOG_PATH):
        print(f"ERROR: Catalog not found at {CATALOG_PATH}. Run --step catalog first.")
        return

    with open(CATALOG_PATH) as f:
        catalog_data = json.load(f)

    posts = catalog_data["posts"]
    print(f"Loaded {len(posts)} posts from catalog")
    print(f"Running GPT-5 mini rhetoric analysis with {GPT_WORKERS} workers...")

    # ── Parallel GPT analysis ──
    results = {}
    completed = 0
    with ThreadPoolExecutor(max_workers=GPT_WORKERS) as executor:
        futures = {executor.submit(analyze_post_rhetoric, p): p["id"] for p in posts}
        for future in as_completed(futures):
            post_id, analysis = future.result()
            if analysis:
                results[post_id] = analysis
            completed += 1
            if completed % 25 == 0:
                print(f"  Analyzed {completed}/{len(posts)} posts...")

    print(f"  Successfully analyzed {len(results)}/{len(posts)} posts")

    # ── Enrich catalog posts with rhetoric data ──
    for post in posts:
        if post["id"] in results:
            post.update(results[post["id"]])

    # ── Helper: group by field and compute avg engagement ──
    def agg_by_field(field_name):
        groups = {}
        for p in posts:
            val = p.get(field_name)
            if val is not None:
                if val not in groups:
                    groups[val] = []
                groups[val].append(p["engagement_total"])
        rows = []
        for val, engs in sorted(groups.items(), key=lambda x: -statistics.mean(x[1])):
            rows.append([
                val,
                len(engs),
                round(statistics.mean(engs)),
                round(statistics.median(engs)),
                max(engs),
            ])
        return rows

    # ── Helper: group by boolean field ──
    def agg_by_bool(field_name, label):
        true_eng = [p["engagement_total"] for p in posts if p.get(field_name) is True]
        false_eng = [p["engagement_total"] for p in posts if p.get(field_name) is False]
        rows = []
        if true_eng:
            rows.append([f"With {label}", len(true_eng), round(statistics.mean(true_eng)), round(statistics.median(true_eng)), max(true_eng)])
        if false_eng:
            rows.append([f"Without {label}", len(false_eng), round(statistics.mean(false_eng)), round(statistics.median(false_eng)), max(false_eng)])
        return rows

    # ── Aggregation Tables ──

    # 1. Opening Hook × Engagement
    print_table(
        "OPENING HOOK × AVG ENGAGEMENT",
        ["Hook Type", "Count", "Avg", "Median", "Max"],
        agg_by_field("opening_hook"),
    )

    # 2. Structural Pattern × Engagement
    print_table(
        "STRUCTURAL PATTERN × AVG ENGAGEMENT",
        ["Pattern", "Count", "Avg", "Median", "Max"],
        agg_by_field("structural_pattern"),
    )

    # 3. Framing Technique × Engagement
    print_table(
        "FRAMING TECHNIQUE × AVG ENGAGEMENT",
        ["Technique", "Count", "Avg", "Median", "Max"],
        agg_by_field("framing_technique"),
    )

    # 4. CTA × Engagement
    print_table(
        "CALL TO ACTION × AVG ENGAGEMENT",
        ["CTA", "Count", "Avg", "Median", "Max"],
        agg_by_field("call_to_action"),
    )

    # 5. Tone × Engagement
    print_table(
        "TONE × AVG ENGAGEMENT",
        ["Tone", "Count", "Avg", "Median", "Max"],
        agg_by_field("tone"),
    )

    # 6. Boolean comparisons
    print_table(
        "BOLD UNICODE USAGE × ENGAGEMENT",
        ["Group", "Count", "Avg", "Median", "Max"],
        agg_by_bool("uses_bold_unicode", "Bold Unicode"),
    )

    print_table(
        "EMOJI USAGE × ENGAGEMENT",
        ["Group", "Count", "Avg", "Median", "Max"],
        agg_by_bool("uses_emoji", "Emoji"),
    )

    print_table(
        "HOOK GAP × ENGAGEMENT",
        ["Group", "Count", "Avg", "Median", "Max"],
        agg_by_bool("has_hook_gap", "Hook Gap"),
    )

    # 7. Most common rhetorical device combinations (top 10)
    combo_counts = {}
    combo_eng = {}
    for p in posts:
        devs = p.get("rhetoric_devices", [])
        if devs:
            # Sort devices for consistent combo key
            combo_key = " + ".join(sorted(devs))
            combo_counts[combo_key] = combo_counts.get(combo_key, 0) + 1
            if combo_key not in combo_eng:
                combo_eng[combo_key] = []
            combo_eng[combo_key].append(p["engagement_total"])

    combo_rows = []
    for combo, cnt in sorted(combo_counts.items(), key=lambda x: -x[1]):
        combo_rows.append([
            combo[:70],
            cnt,
            round(statistics.mean(combo_eng[combo])),
            round(statistics.median(combo_eng[combo])),
        ])
    print_table(
        "TOP 15 RHETORICAL DEVICE COMBOS (by frequency)",
        ["Combo", "Count", "Avg Eng", "Median Eng"],
        combo_rows[:15],
        col_widths=[72, 8, 10, 12],
    )

    # Also show top 10 combos by avg engagement (min 2 posts)
    combo_by_eng = []
    for combo, engs in combo_eng.items():
        if len(engs) >= 2:
            combo_by_eng.append([
                combo[:70],
                len(engs),
                round(statistics.mean(engs)),
                round(statistics.median(engs)),
            ])
    combo_by_eng.sort(key=lambda x: -x[2])
    print_table(
        "TOP 10 DEVICE COMBOS BY AVG ENGAGEMENT (min 2 posts)",
        ["Combo", "Count", "Avg Eng", "Median Eng"],
        combo_by_eng[:10],
        col_widths=[72, 8, 10, 12],
    )

    # 8. Rhetoric device frequency (from this analysis, separate from US-002)
    device_counts = {}
    device_eng = {}
    for p in posts:
        devs = p.get("rhetoric_devices", [])
        for d in devs:
            device_counts[d] = device_counts.get(d, 0) + 1
            if d not in device_eng:
                device_eng[d] = []
            device_eng[d].append(p["engagement_total"])

    device_rows = []
    for d, cnt in sorted(device_counts.items(), key=lambda x: -x[1]):
        device_rows.append([
            d,
            cnt,
            round(statistics.mean(device_eng[d])),
            round(statistics.median(device_eng[d])),
        ])
    print_table(
        "RHETORICAL DEVICE FREQUENCY (US-003 analysis)",
        ["Device", "Count", "Avg Eng", "Median Eng"],
        device_rows,
    )

    # ── Update and save catalog ──
    if "rhetoric" not in catalog_data["metadata"]["steps_completed"]:
        catalog_data["metadata"]["steps_completed"].append("rhetoric")
    catalog_data["metadata"]["rhetoric_analyzed_at"] = datetime.now().isoformat()

    # Add rhetoric summary to catalog
    rhetoric_summary = {}
    for field in ["opening_hook", "structural_pattern", "framing_technique", "call_to_action", "tone", "line_break_style"]:
        groups = {}
        for p in posts:
            val = p.get(field)
            if val is not None:
                if val not in groups:
                    groups[val] = []
                groups[val].append(p["engagement_total"])
        rhetoric_summary[field] = {
            val: {"count": len(engs), "avg_engagement": round(statistics.mean(engs))}
            for val, engs in sorted(groups.items(), key=lambda x: -statistics.mean(x[1]))
        }

    # Boolean summaries
    for field, label in [("uses_bold_unicode", "bold_unicode"), ("uses_emoji", "emoji"), ("has_hook_gap", "hook_gap")]:
        true_eng = [p["engagement_total"] for p in posts if p.get(field) is True]
        false_eng = [p["engagement_total"] for p in posts if p.get(field) is False]
        rhetoric_summary[label] = {
            "with": {"count": len(true_eng), "avg_engagement": round(statistics.mean(true_eng)) if true_eng else 0},
            "without": {"count": len(false_eng), "avg_engagement": round(statistics.mean(false_eng)) if false_eng else 0},
        }

    catalog_data["rhetoric_summary"] = rhetoric_summary

    with open(CATALOG_PATH, "w") as f:
        json.dump(catalog_data, f, indent=2, default=str)

    print(f"\nCatalog updated with rhetoric analysis at {CATALOG_PATH}")
    print("US-003 COMPLETE")


# ── US-004: Length, Format & Timing Optimization ──

CSV_SCATTER_PATH = "docs/kevin_brown_length_vs_engagement.csv"


def step_format():
    """US-004: Length, format, and timing optimization analysis."""
    if not os.path.exists(CATALOG_PATH):
        print(f"ERROR: Catalog not found at {CATALOG_PATH}. Run --step catalog first.")
        return

    with open(CATALOG_PATH) as f:
        catalog_data = json.load(f)

    posts = catalog_data["posts"]
    print(f"Loaded {len(posts)} posts from catalog")
    print("Running format, length, and timing analysis...\n")

    # ── 1. LENGTH ANALYSIS ──

    # 1a. Scatter plot data: content_length vs engagement_total (CSV)
    with open(CSV_SCATTER_PATH, "w") as csvf:
        csvf.write("post_id,char_count,engagement_total,media_type,length_bucket,hook_length,primary_theme\n")
        for p in posts:
            theme = p.get("primary_theme", "unknown")
            csvf.write(f"{p['id']},{p['char_count']},{p['engagement_total']},{p['media_type']},{p['length_bucket']},{p['hook_length']},{theme}\n")
    print(f"Scatter plot CSV saved to {CSV_SCATTER_PATH}")

    # 1b. Engagement by length bucket (avg, median, max, count)
    buckets = {}
    for p in posts:
        b = p["length_bucket"]
        if b not in buckets:
            buckets[b] = {"eng": [], "likes": [], "comments": [], "shares": []}
        buckets[b]["eng"].append(p["engagement_total"])
        buckets[b]["likes"].append(p["engagement_likes"])
        buckets[b]["comments"].append(p["engagement_comments"])
        buckets[b]["shares"].append(p["engagement_shares"])

    bucket_order = ["short (<300)", "medium (300-800)", "long (800-1500)", "very_long (1500+)"]
    bucket_rows = []
    for b in bucket_order:
        if b in buckets:
            e = buckets[b]["eng"]
            bucket_rows.append([
                b,
                len(e),
                round(statistics.mean(e)),
                round(statistics.median(e)),
                max(e),
                round(statistics.mean(buckets[b]["likes"])),
                round(statistics.mean(buckets[b]["comments"])),
                round(statistics.mean(buckets[b]["shares"])),
            ])

    print_table(
        "LENGTH BUCKET × ENGAGEMENT (detailed)",
        ["Bucket", "N", "Avg", "Median", "Max", "Avg Likes", "Avg Cmts", "Avg Shares"],
        bucket_rows,
    )

    # 1c. Optimal length range: which bucket has highest median AND most consistent performance?
    print("\n  OPTIMAL LENGTH INSIGHT:")
    best_median_bucket = max(
        [(b, round(statistics.median(buckets[b]["eng"]))) for b in bucket_order if b in buckets],
        key=lambda x: x[1],
    )
    best_avg_bucket = max(
        [(b, round(statistics.mean(buckets[b]["eng"]))) for b in bucket_order if b in buckets],
        key=lambda x: x[1],
    )
    print(f"  Highest median engagement: {best_median_bucket[0]} ({best_median_bucket[1]})")
    print(f"  Highest avg engagement:    {best_avg_bucket[0]} ({best_avg_bucket[1]})")

    # 1d. Hook length (first line char count) vs engagement — bucketed
    hook_buckets = {"<25 chars": [], "25-50 chars": [], "50-80 chars": [], "80+ chars": []}
    for p in posts:
        hl = p["hook_length"]
        eng = p["engagement_total"]
        if hl < 25:
            hook_buckets["<25 chars"].append(eng)
        elif hl < 50:
            hook_buckets["25-50 chars"].append(eng)
        elif hl < 80:
            hook_buckets["50-80 chars"].append(eng)
        else:
            hook_buckets["80+ chars"].append(eng)

    hook_rows = []
    for label in ["<25 chars", "25-50 chars", "50-80 chars", "80+ chars"]:
        vals = hook_buckets[label]
        if vals:
            hook_rows.append([
                label,
                len(vals),
                round(statistics.mean(vals)),
                round(statistics.median(vals)),
                max(vals),
            ])

    print_table(
        "HOOK LENGTH (first line) × ENGAGEMENT",
        ["Hook Length", "N", "Avg", "Median", "Max"],
        hook_rows,
    )

    # ── 2. FORMAT ANALYSIS ──

    # 2a. Text vs carousel — full breakdown
    format_groups = {}
    for p in posts:
        mt = p["media_type"] or "unknown"
        if mt not in format_groups:
            format_groups[mt] = {"eng": [], "likes": [], "comments": [], "shares": [], "clr": [], "slr": []}
        format_groups[mt]["eng"].append(p["engagement_total"])
        format_groups[mt]["likes"].append(p["engagement_likes"])
        format_groups[mt]["comments"].append(p["engagement_comments"])
        format_groups[mt]["shares"].append(p["engagement_shares"])
        format_groups[mt]["clr"].append(p["comment_to_like_ratio"])
        format_groups[mt]["slr"].append(p["share_to_like_ratio"])

    format_rows = []
    for mt in sorted(format_groups.keys()):
        g = format_groups[mt]
        format_rows.append([
            mt,
            len(g["eng"]),
            round(statistics.mean(g["eng"])),
            round(statistics.median(g["eng"])),
            max(g["eng"]),
            round(statistics.mean(g["likes"])),
            round(statistics.mean(g["comments"])),
            round(statistics.mean(g["shares"])),
            round(statistics.mean(g["clr"]), 3),
            round(statistics.mean(g["slr"]), 3),
        ])

    print_table(
        "FORMAT BREAKDOWN (text vs carousel)",
        ["Type", "N", "Avg Eng", "Median", "Max", "Avg Lk", "Avg Cmt", "Avg Shr", "Cmt/Lk", "Shr/Lk"],
        format_rows,
    )

    # 2b. Format insight
    print("\n  FORMAT INSIGHT:")
    for mt in sorted(format_groups.keys()):
        g = format_groups[mt]
        print(f"  {mt}: {len(g['eng'])} posts, avg engagement {round(statistics.mean(g['eng']))}, "
              f"comment/like ratio {round(statistics.mean(g['clr']), 3)}, share/like ratio {round(statistics.mean(g['slr']), 3)}")

    # ── 3. TIMING ANALYSIS ──

    # 3a. Day of week × engagement (with likes/comments/shares breakdown)
    dow = {}
    for p in posts:
        d = p["day_of_week"]
        if d:
            if d not in dow:
                dow[d] = {"eng": [], "likes": [], "comments": [], "shares": []}
            dow[d]["eng"].append(p["engagement_total"])
            dow[d]["likes"].append(p["engagement_likes"])
            dow[d]["comments"].append(p["engagement_comments"])
            dow[d]["shares"].append(p["engagement_shares"])

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_rows = []
    for d in day_order:
        if d in dow:
            g = dow[d]
            dow_rows.append([
                d,
                len(g["eng"]),
                round(statistics.mean(g["eng"])),
                round(statistics.median(g["eng"])),
                max(g["eng"]),
                round(statistics.mean(g["likes"])),
                round(statistics.mean(g["comments"])),
                round(statistics.mean(g["shares"])),
            ])

    print_table(
        "DAY OF WEEK × ENGAGEMENT (detailed)",
        ["Day", "N", "Avg Eng", "Median", "Max", "Avg Lk", "Avg Cmt", "Avg Shr"],
        dow_rows,
    )

    # 3b. Posting frequency: posts per week over time
    # Group posts by ISO week
    weekly = {}
    for p in posts:
        iso = p.get("iso_date")
        if iso:
            try:
                dt = datetime.strptime(iso, "%Y-%m-%d")
                week_key = dt.strftime("%Y-W%V")
                if week_key not in weekly:
                    weekly[week_key] = {"count": 0, "eng": []}
                weekly[week_key]["count"] += 1
                weekly[week_key]["eng"].append(p["engagement_total"])
            except ValueError:
                pass

    weekly_rows = []
    for wk in sorted(weekly.keys()):
        w = weekly[wk]
        weekly_rows.append([
            wk,
            w["count"],
            round(statistics.mean(w["eng"])),
            sum(w["eng"]),
        ])

    print_table(
        "POSTING FREQUENCY BY WEEK",
        ["Week", "Posts", "Avg Eng", "Total Eng"],
        weekly_rows,
    )

    # Weekly summary stats
    counts = [w["count"] for w in weekly.values()]
    print(f"\n  Posting cadence: {round(statistics.mean(counts), 1)} posts/week avg, "
          f"median {statistics.median(counts)}, range {min(counts)}-{max(counts)}")

    # 3c. Engagement trend over time (by month)
    monthly = {}
    for p in posts:
        iso = p.get("iso_date")
        if iso:
            month_key = iso[:7]  # YYYY-MM
            if month_key not in monthly:
                monthly[month_key] = {"count": 0, "eng": []}
            monthly[month_key]["count"] += 1
            monthly[month_key]["eng"].append(p["engagement_total"])

    monthly_rows = []
    for mk in sorted(monthly.keys()):
        m = monthly[mk]
        monthly_rows.append([
            mk,
            m["count"],
            round(statistics.mean(m["eng"])),
            round(statistics.median(m["eng"])),
            max(m["eng"]),
            sum(m["eng"]),
        ])

    print_table(
        "ENGAGEMENT TREND BY MONTH",
        ["Month", "Posts", "Avg Eng", "Median", "Max", "Total"],
        monthly_rows,
    )

    # ── 4. CROSS-TABULATIONS ──

    # 4a. Theme × format × engagement
    theme_format = {}
    for p in posts:
        theme = p.get("primary_theme", "unknown")
        fmt = p["media_type"] or "unknown"
        key = f"{theme} × {fmt}"
        if key not in theme_format:
            theme_format[key] = []
        theme_format[key].append(p["engagement_total"])

    tf_rows = []
    for key, engs in sorted(theme_format.items(), key=lambda x: -statistics.mean(x[1])):
        tf_rows.append([
            key,
            len(engs),
            round(statistics.mean(engs)),
            round(statistics.median(engs)),
            max(engs),
        ])

    print_table(
        "THEME × FORMAT × ENGAGEMENT (which themes work better in which format?)",
        ["Theme × Format", "N", "Avg", "Median", "Max"],
        tf_rows,
    )

    # 4b. Length × theme × engagement
    theme_length = {}
    for p in posts:
        theme = p.get("primary_theme", "unknown")
        lb = p["length_bucket"]
        key = f"{theme} × {lb}"
        if key not in theme_length:
            theme_length[key] = []
        theme_length[key].append(p["engagement_total"])

    tl_rows = []
    for key, engs in sorted(theme_length.items(), key=lambda x: -statistics.mean(x[1])):
        tl_rows.append([
            key,
            len(engs),
            round(statistics.mean(engs)),
            round(statistics.median(engs)),
            max(engs),
        ])

    print_table(
        "THEME × LENGTH × ENGAGEMENT (do some themes need more or fewer words?)",
        ["Theme × Length", "N", "Avg", "Median", "Max"],
        tl_rows,
    )

    # 4c. Hook type × format × engagement
    hook_format = {}
    for p in posts:
        hook = p.get("opening_hook", "unknown")
        fmt = p["media_type"] or "unknown"
        key = f"{hook} × {fmt}"
        if key not in hook_format:
            hook_format[key] = []
        hook_format[key].append(p["engagement_total"])

    hf_rows = []
    for key, engs in sorted(hook_format.items(), key=lambda x: -statistics.mean(x[1])):
        if len(engs) >= 2:  # Only show combos with 2+ posts
            hf_rows.append([
                key,
                len(engs),
                round(statistics.mean(engs)),
                round(statistics.median(engs)),
                max(engs),
            ])

    print_table(
        "HOOK TYPE × FORMAT × ENGAGEMENT (min 2 posts)",
        ["Hook × Format", "N", "Avg", "Median", "Max"],
        hf_rows,
    )

    # 4d. Line count analysis — bucketed
    line_buckets = {"1-5 lines": [], "6-10 lines": [], "11-15 lines": [], "16-20 lines": [], "21+ lines": []}
    for p in posts:
        lc = p["line_count"]
        eng = p["engagement_total"]
        if lc <= 5:
            line_buckets["1-5 lines"].append(eng)
        elif lc <= 10:
            line_buckets["6-10 lines"].append(eng)
        elif lc <= 15:
            line_buckets["11-15 lines"].append(eng)
        elif lc <= 20:
            line_buckets["16-20 lines"].append(eng)
        else:
            line_buckets["21+ lines"].append(eng)

    line_rows = []
    for label in ["1-5 lines", "6-10 lines", "11-15 lines", "16-20 lines", "21+ lines"]:
        vals = line_buckets[label]
        if vals:
            line_rows.append([
                label,
                len(vals),
                round(statistics.mean(vals)),
                round(statistics.median(vals)),
                max(vals),
            ])

    print_table(
        "LINE COUNT × ENGAGEMENT",
        ["Line Count", "N", "Avg", "Median", "Max"],
        line_rows,
    )

    # ── 5. OPTIMAL CONTENT FORMULA ──
    print(f"\n{'='*60}")
    print("  OPTIMAL CONTENT FORMULA (US-004 SYNTHESIS)")
    print(f"{'='*60}")

    # Find the best combos
    # Best length bucket by median
    best_length = max(
        [(b, statistics.median(buckets[b]["eng"]), len(buckets[b]["eng"])) for b in bucket_order if b in buckets and len(buckets[b]["eng"]) >= 5],
        key=lambda x: x[1],
    )
    # Best format by avg
    best_format = max(
        [(mt, statistics.mean(format_groups[mt]["eng"]), len(format_groups[mt]["eng"])) for mt in format_groups],
        key=lambda x: x[1],
    )
    # Best day by avg
    best_day = max(
        [(d, statistics.mean(dow[d]["eng"]), len(dow[d]["eng"])) for d in dow if len(dow[d]["eng"]) >= 3],
        key=lambda x: x[1],
    )
    # Best hook length
    best_hook = max(
        [(label, statistics.mean(hook_buckets[label]), len(hook_buckets[label])) for label in hook_buckets if len(hook_buckets[label]) >= 5],
        key=lambda x: x[1],
    )

    print(f"\n  Best length:     {best_length[0]} (median {round(best_length[1])}, n={best_length[2]})")
    print(f"  Best format:     {best_format[0]} (avg {round(best_format[1])}, n={best_format[2]})")
    print(f"  Best day:        {best_day[0]} (avg {round(best_day[1])}, n={best_day[2]})")
    print(f"  Best hook range: {best_hook[0]} (avg {round(best_hook[1])}, n={best_hook[2]})")

    # ── Save format analysis summary to catalog ──
    format_summary = {
        "length_buckets": {},
        "format_breakdown": {},
        "day_of_week": {},
        "hook_length_buckets": {},
        "posting_cadence": {
            "avg_posts_per_week": round(statistics.mean(counts), 1),
            "median_posts_per_week": statistics.median(counts),
        },
        "optimal_formula": {
            "best_length": best_length[0],
            "best_format": best_format[0],
            "best_day": best_day[0],
            "best_hook_range": best_hook[0],
        },
        "cross_tabs": {
            "theme_x_format": {},
            "theme_x_length": {},
        },
    }

    for b in bucket_order:
        if b in buckets:
            e = buckets[b]["eng"]
            format_summary["length_buckets"][b] = {
                "count": len(e),
                "avg_engagement": round(statistics.mean(e)),
                "median_engagement": round(statistics.median(e)),
            }

    for mt in format_groups:
        g = format_groups[mt]
        format_summary["format_breakdown"][mt] = {
            "count": len(g["eng"]),
            "avg_engagement": round(statistics.mean(g["eng"])),
            "avg_comment_to_like": round(statistics.mean(g["clr"]), 3),
            "avg_share_to_like": round(statistics.mean(g["slr"]), 3),
        }

    for d in day_order:
        if d in dow:
            g = dow[d]
            format_summary["day_of_week"][d] = {
                "count": len(g["eng"]),
                "avg_engagement": round(statistics.mean(g["eng"])),
                "median_engagement": round(statistics.median(g["eng"])),
            }

    for label in ["<25 chars", "25-50 chars", "50-80 chars", "80+ chars"]:
        vals = hook_buckets[label]
        if vals:
            format_summary["hook_length_buckets"][label] = {
                "count": len(vals),
                "avg_engagement": round(statistics.mean(vals)),
                "median_engagement": round(statistics.median(vals)),
            }

    # Cross-tabs (top 10 by avg engagement)
    for key, engs in sorted(theme_format.items(), key=lambda x: -statistics.mean(x[1]))[:15]:
        format_summary["cross_tabs"]["theme_x_format"][key] = {
            "count": len(engs),
            "avg_engagement": round(statistics.mean(engs)),
        }

    for key, engs in sorted(theme_length.items(), key=lambda x: -statistics.mean(x[1]))[:15]:
        format_summary["cross_tabs"]["theme_x_length"][key] = {
            "count": len(engs),
            "avg_engagement": round(statistics.mean(engs)),
        }

    catalog_data["format_summary"] = format_summary

    if "format" not in catalog_data["metadata"]["steps_completed"]:
        catalog_data["metadata"]["steps_completed"].append("format")
    catalog_data["metadata"]["format_analyzed_at"] = datetime.now().isoformat()

    with open(CATALOG_PATH, "w") as f:
        json.dump(catalog_data, f, indent=2, default=str)

    print(f"\nCatalog updated with format analysis at {CATALOG_PATH}")
    print("US-004 COMPLETE")


# ── US-005: Kevin's Content Playbook — Signature Patterns ──

PLAYBOOK_SYSTEM_PROMPT = """You are a world-class content strategist synthesizing LinkedIn post data into an actionable content playbook.

You are given comprehensive analysis data from 100 LinkedIn posts by Kevin L. Brown — a nonprofit fundraising/comms thought leader whose posts average 463 engagement (top post: 3,134).

Your job: synthesize ALL the data into Kevin's content playbook. Be specific, data-backed, and practical. Every claim must reference actual numbers from the data.

Output a structured playbook with:
1. Top 5 Signature Moves — the specific patterns Kevin uses that consistently drive high engagement
2. The Viral Formula — the exact combination of attributes that predicts a top-10% post
3. Content Calendar Pattern — how Kevin sequences themes and formats
4. What Doesn't Work — patterns that consistently underperform
5. Audience Psychology — what emotional/identity triggers his audience responds to

For each signature move, explain:
- What it is (the technique)
- Why it works (the psychology — reference Cialdini, Kahneman, Heath brothers, etc.)
- How to replicate it (a fill-in-the-blank template)

Be concrete. Use numbers. No vague advice."""


class SignatureMove(BaseModel):
    name: str = Field(description="Short name for the signature move (e.g., 'The Identity Mirror')")
    technique: str = Field(description="What the technique is — 2-3 sentences explaining the pattern")
    why_it_works: str = Field(description="Why this works psychologically — reference persuasion research")
    template: str = Field(description="Fill-in-the-blank template someone can use to replicate this move")
    avg_engagement: int = Field(description="Average engagement of posts using this move")
    post_count: int = Field(description="Number of posts using this move")


class ViralFormula(BaseModel):
    formula_summary: str = Field(description="One-sentence summary of the viral formula")
    theme: str = Field(description="Best theme(s) for viral potential")
    opening_hook: str = Field(description="Best opening hook type(s)")
    structural_pattern: str = Field(description="Best structural pattern(s)")
    framing_technique: str = Field(description="Best framing technique(s)")
    tone: str = Field(description="Best tone")
    length: str = Field(description="Optimal length range")
    format: str = Field(description="Best format (text vs carousel)")
    cta: str = Field(description="Best call to action")
    emotional_appeal: str = Field(description="Best emotional appeal(s)")
    rhetorical_devices: str = Field(description="Must-have rhetorical devices")


class ContentCalendarPattern(BaseModel):
    posting_frequency: str = Field(description="How often Kevin posts and optimal cadence")
    best_days: str = Field(description="Best days to post and why")
    theme_rotation: str = Field(description="How Kevin rotates themes across the week")
    format_mix: str = Field(description="How Kevin mixes text vs carousel")


class AntiPattern(BaseModel):
    pattern: str = Field(description="What the underperforming pattern is")
    avg_engagement: int = Field(description="Average engagement")
    why_it_fails: str = Field(description="Why this doesn't work for Kevin's audience")


class AudiencePsychology(BaseModel):
    primary_identity: str = Field(description="Who Kevin's audience sees themselves as")
    emotional_triggers: str = Field(description="Which emotions drive the most engagement and why")
    content_preferences: str = Field(description="What the audience wants (frameworks vs stories, etc.)")
    sharing_motivation: str = Field(description="Why people share Kevin's content (identity signaling, utility, etc.)")


class PlaybookSynthesis(BaseModel):
    executive_summary: str = Field(description="3-4 sentence executive summary of Kevin's content strategy")
    signature_moves: List[SignatureMove] = Field(description="Top 5 signature moves")
    viral_formula: ViralFormula
    calendar_pattern: ContentCalendarPattern
    anti_patterns: List[AntiPattern] = Field(description="Top 5 things that don't work")
    audience_psychology: AudiencePsychology


def step_playbook():
    """US-005: Synthesize Kevin's content playbook from all analysis data."""
    if not os.path.exists(CATALOG_PATH):
        print(f"ERROR: Catalog not found at {CATALOG_PATH}. Run previous steps first.")
        return

    with open(CATALOG_PATH) as f:
        catalog_data = json.load(f)

    posts = catalog_data["posts"]
    theme_summary = catalog_data.get("theme_summary", {})
    rhetoric_summary = catalog_data.get("rhetoric_summary", {})
    format_summary = catalog_data.get("format_summary", {})

    print(f"Loaded {len(posts)} posts from catalog")
    print("Synthesizing Kevin's content playbook via GPT-5 mini...\n")

    # ── Build comprehensive context for GPT ──

    # Top 10 posts with details
    top_posts_ctx = []
    for i, p in enumerate(posts[:10]):
        hook_text = p["post_content"].split("\n")[0][:80] if p["post_content"] else ""
        top_posts_ctx.append(
            f"#{i+1} (Eng: {p['engagement_total']}): Hook=\"{hook_text}\" | "
            f"Theme={p.get('primary_theme')} | Category={p.get('content_category')} | "
            f"Emotion={p.get('emotional_appeal')} | Hook={p.get('opening_hook')} | "
            f"Structure={p.get('structural_pattern')} | Frame={p.get('framing_technique')} | "
            f"Tone={p.get('tone')} | CTA={p.get('call_to_action')} | "
            f"Format={p['media_type']} | Chars={p['char_count']} | "
            f"Devices={p.get('rhetoric_devices', [])}"
        )

    # Bottom 10 posts
    bottom_posts_ctx = []
    for i, p in enumerate(posts[-10:]):
        hook_text = p["post_content"].split("\n")[0][:80] if p["post_content"] else ""
        bottom_posts_ctx.append(
            f"(Eng: {p['engagement_total']}): Hook=\"{hook_text}\" | "
            f"Theme={p.get('primary_theme')} | Category={p.get('content_category')} | "
            f"Hook={p.get('opening_hook')} | Structure={p.get('structural_pattern')} | "
            f"Frame={p.get('framing_technique')} | Tone={p.get('tone')} | CTA={p.get('call_to_action')}"
        )

    # Signature pattern candidates (computed from data)
    import statistics as stats

    sig_patterns = []

    # Passionate + CTA category
    combo = [p for p in posts if p.get("tone") == "passionate" and p.get("content_category") == "call_to_action"]
    if combo:
        eng = [p["engagement_total"] for p in combo]
        sig_patterns.append(f"Passionate tone + CTA category: {len(combo)} posts, avg {round(stats.mean(eng))}, max {max(eng)}")

    # Identity appeal framing
    combo = [p for p in posts if p.get("framing_technique") == "identity_appeal"]
    if combo:
        eng = [p["engagement_total"] for p in combo]
        sig_patterns.append(f"Identity appeal framing: {len(combo)} posts, avg {round(stats.mean(eng))}, max {max(eng)}")

    # Build to reveal
    combo = [p for p in posts if p.get("structural_pattern") == "build_to_reveal"]
    if combo:
        eng = [p["engagement_total"] for p in combo]
        sig_patterns.append(f"Build-to-reveal structure: {len(combo)} posts, avg {round(stats.mean(eng))}, max {max(eng)}")

    # Antithesis + tricolon combo
    combo = [p for p in posts if "antithesis" in p.get("rhetoric_devices", []) and "tricolon" in p.get("rhetoric_devices", [])]
    if combo:
        eng = [p["engagement_total"] for p in combo]
        sig_patterns.append(f"Antithesis + tricolon devices: {len(combo)} posts, avg {round(stats.mean(eng))}, max {max(eng)}")

    # Rhetorical question + metaphor
    combo = [p for p in posts if "rhetorical_question" in p.get("rhetoric_devices", []) and "metaphor" in p.get("rhetoric_devices", [])]
    if combo:
        eng = [p["engagement_total"] for p in combo]
        sig_patterns.append(f"Rhetorical Q + metaphor: {len(combo)} posts, avg {round(stats.mean(eng))}, max {max(eng)}")

    # Share CTA
    combo = [p for p in posts if p.get("call_to_action") == "share_this"]
    if combo:
        eng = [p["engagement_total"] for p in combo]
        sig_patterns.append(f"Share this CTA: {len(combo)} posts, avg {round(stats.mean(eng))}, max {max(eng)}")

    # Myth bust
    combo = [p for p in posts if p.get("structural_pattern") == "myth_bust"]
    if combo:
        eng = [p["engagement_total"] for p in combo]
        sig_patterns.append(f"Myth bust structure: {len(combo)} posts, avg {round(stats.mean(eng))}, max {max(eng)}")

    # Advocacy theme
    combo = [p for p in posts if p.get("primary_theme") == "advocacy_activism"]
    if combo:
        eng = [p["engagement_total"] for p in combo]
        sig_patterns.append(f"Advocacy/activism theme: {len(combo)} posts, avg {round(stats.mean(eng))}, max {max(eng)}")

    # Empathy emotion
    combo = [p for p in posts if p.get("emotional_appeal") == "empathy"]
    if combo:
        eng = [p["engagement_total"] for p in combo]
        sig_patterns.append(f"Empathy emotional appeal: {len(combo)} posts, avg {round(stats.mean(eng))}, max {max(eng)}")

    # Pride emotion
    combo = [p for p in posts if p.get("emotional_appeal") == "pride"]
    if combo:
        eng = [p["engagement_total"] for p in combo]
        sig_patterns.append(f"Pride emotional appeal: {len(combo)} posts, avg {round(stats.mean(eng))}, max {max(eng)}")

    # Anti-patterns
    anti_patterns = []
    anti_combos = [
        ("story_opening", "opening_hook"),
        ("narrative_arc", "structural_pattern"),
        ("storytelling_frame", "framing_technique"),
        ("imperative_command", "opening_hook"),
        ("link_in_comments", "call_to_action"),
        ("contrarian", "content_category"),
    ]
    for val, field in anti_combos:
        combo = [p for p in posts if p.get(field) == val]
        if combo:
            eng = [p["engagement_total"] for p in combo]
            anti_patterns.append(f"{val} ({field}): {len(combo)} posts, avg {round(stats.mean(eng))}")

    # Top 10% characteristics
    p90_threshold = sorted([p["engagement_total"] for p in posts])[int(len(posts) * 0.90)]
    top10pct = [p for p in posts if p["engagement_total"] >= p90_threshold]
    top10_chars = {}
    for field in ["opening_hook", "structural_pattern", "framing_technique", "tone", "call_to_action", "content_category", "emotional_appeal", "primary_theme"]:
        counts = {}
        for p in top10pct:
            v = p.get(field)
            if v:
                counts[v] = counts.get(v, 0) + 1
        top2 = sorted(counts.items(), key=lambda x: -x[1])[:3]
        top10_chars[field] = top2

    context = f"""KEVIN L. BROWN — LINKEDIN CONTENT ANALYSIS DATA
=================================================

OVERALL: 100 posts, Nov 2024 – Feb 2026
Engagement: min 75, avg 463, median 229, P75 578, P90 {p90_threshold}, max 3,134
Text: 61 posts (avg 539), Carousel: 39 posts (avg 345)
Avg char length: 686, Avg hook length: 40 chars

THEME PERFORMANCE (sorted by avg engagement):
{json.dumps(theme_summary.get('primary_theme', {}), indent=2)}

CONTENT CATEGORY PERFORMANCE:
{json.dumps(theme_summary.get('content_category', {}), indent=2)}

EMOTIONAL APPEAL PERFORMANCE:
{json.dumps(theme_summary.get('emotional_appeal', {}), indent=2)}

TARGET AUDIENCE PERFORMANCE:
{json.dumps(theme_summary.get('target_audience', {}), indent=2)}

OPENING HOOK PERFORMANCE:
{json.dumps(rhetoric_summary.get('opening_hook', {}), indent=2)}

STRUCTURAL PATTERN PERFORMANCE:
{json.dumps(rhetoric_summary.get('structural_pattern', {}), indent=2)}

FRAMING TECHNIQUE PERFORMANCE:
{json.dumps(rhetoric_summary.get('framing_technique', {}), indent=2)}

CTA PERFORMANCE:
{json.dumps(rhetoric_summary.get('call_to_action', {}), indent=2)}

TONE PERFORMANCE:
{json.dumps(rhetoric_summary.get('tone', {}), indent=2)}

FORMAT SUMMARY:
{json.dumps(format_summary, indent=2)}

HIGH-ENGAGEMENT PATTERN COMBOS:
{chr(10).join(sig_patterns)}

ANTI-PATTERNS (underperformers):
{chr(10).join(anti_patterns)}

TOP 10% POST CHARACTERISTICS (engagement >= {p90_threshold}):
{json.dumps(top10_chars, indent=2, default=str)}

TOP 10 POSTS:
{chr(10).join(top_posts_ctx)}

BOTTOM 10 POSTS:
{chr(10).join(bottom_posts_ctx)}

FULL POST EXAMPLES (top 3):

POST #1 (3,134 engagement):
{posts[0]['post_content'][:600]}

POST #2 (2,661 engagement):
{posts[1]['post_content'][:600]}

POST #3 (2,375 engagement):
{posts[2]['post_content'][:600]}
"""

    # ── Call GPT-5 mini for synthesis ──
    try:
        resp = oai.responses.parse(
            model="gpt-5-mini",
            instructions=PLAYBOOK_SYSTEM_PROMPT,
            input=context,
            text_format=PlaybookSynthesis,
        )
        playbook = resp.output_parsed
    except Exception as e:
        print(f"ERROR: GPT synthesis failed: {e}")
        return

    # ── Print the playbook ──
    print(f"\n{'='*70}")
    print("  KEVIN L. BROWN — CONTENT PLAYBOOK")
    print(f"{'='*70}")

    print(f"\n{'─'*70}")
    print("  EXECUTIVE SUMMARY")
    print(f"{'─'*70}")
    print(f"\n{playbook.executive_summary}\n")

    # Signature Moves
    print(f"\n{'='*70}")
    print("  TOP 5 SIGNATURE MOVES")
    print(f"{'='*70}")

    for i, move in enumerate(playbook.signature_moves, 1):
        print(f"\n  [{i}] {move.name}")
        print(f"      Posts: {move.post_count} | Avg Engagement: {move.avg_engagement}")
        print(f"\n      TECHNIQUE: {move.technique}")
        print(f"\n      WHY IT WORKS: {move.why_it_works}")
        print(f"\n      TEMPLATE: {move.template}")

    # Viral Formula
    print(f"\n{'='*70}")
    print("  THE VIRAL FORMULA")
    print(f"{'='*70}")
    vf = playbook.viral_formula
    print(f"\n  {vf.formula_summary}\n")
    for attr in ["theme", "opening_hook", "structural_pattern", "framing_technique",
                  "tone", "length", "format", "cta", "emotional_appeal", "rhetorical_devices"]:
        print(f"  {attr.replace('_', ' ').title():25s}: {getattr(vf, attr)}")

    # Content Calendar
    print(f"\n{'='*70}")
    print("  CONTENT CALENDAR PATTERN")
    print(f"{'='*70}")
    cal = playbook.calendar_pattern
    print(f"\n  Frequency:      {cal.posting_frequency}")
    print(f"  Best Days:      {cal.best_days}")
    print(f"  Theme Rotation: {cal.theme_rotation}")
    print(f"  Format Mix:     {cal.format_mix}")

    # Anti-Patterns
    print(f"\n{'='*70}")
    print("  WHAT DOESN'T WORK")
    print(f"{'='*70}")
    for i, ap in enumerate(playbook.anti_patterns, 1):
        print(f"\n  [{i}] {ap.pattern} (avg engagement: {ap.avg_engagement})")
        print(f"      {ap.why_it_fails}")

    # Audience Psychology
    print(f"\n{'='*70}")
    print("  AUDIENCE PSYCHOLOGY")
    print(f"{'='*70}")
    ap = playbook.audience_psychology
    print(f"\n  Primary Identity:    {ap.primary_identity}")
    print(f"  Emotional Triggers:  {ap.emotional_triggers}")
    print(f"  Content Preferences: {ap.content_preferences}")
    print(f"  Sharing Motivation:  {ap.sharing_motivation}")

    # ── Enrich with example posts for each signature move ──
    # Find 3 example posts for each move based on relevant criteria
    move_examples = _find_move_examples(posts, playbook.signature_moves)

    print(f"\n{'='*70}")
    print("  SIGNATURE MOVE EXAMPLES (from actual posts)")
    print(f"{'='*70}")
    for move_name, examples in move_examples.items():
        print(f"\n  ── {move_name} ──")
        for ex in examples:
            hook = ex["post_content"].split("\n")[0][:70]
            print(f"    • (Eng: {ex['engagement_total']}) \"{hook}...\"")

    # ── Save playbook to catalog ──
    playbook_data = {
        "executive_summary": playbook.executive_summary,
        "signature_moves": [
            {
                "name": m.name,
                "technique": m.technique,
                "why_it_works": m.why_it_works,
                "template": m.template,
                "avg_engagement": m.avg_engagement,
                "post_count": m.post_count,
                "example_posts": [
                    {"engagement": ex["engagement_total"], "hook": ex["post_content"].split("\n")[0][:100]}
                    for ex in move_examples.get(m.name, [])
                ],
            }
            for m in playbook.signature_moves
        ],
        "viral_formula": {
            "summary": vf.formula_summary,
            "theme": vf.theme,
            "opening_hook": vf.opening_hook,
            "structural_pattern": vf.structural_pattern,
            "framing_technique": vf.framing_technique,
            "tone": vf.tone,
            "length": vf.length,
            "format": vf.format,
            "cta": vf.cta,
            "emotional_appeal": vf.emotional_appeal,
            "rhetorical_devices": vf.rhetorical_devices,
        },
        "calendar_pattern": {
            "posting_frequency": cal.posting_frequency,
            "best_days": cal.best_days,
            "theme_rotation": cal.theme_rotation,
            "format_mix": cal.format_mix,
        },
        "anti_patterns": [
            {"pattern": a.pattern, "avg_engagement": a.avg_engagement, "why_it_fails": a.why_it_fails}
            for a in playbook.anti_patterns
        ],
        "audience_psychology": {
            "primary_identity": ap.primary_identity,
            "emotional_triggers": ap.emotional_triggers,
            "content_preferences": ap.content_preferences,
            "sharing_motivation": ap.sharing_motivation,
        },
    }

    catalog_data["playbook"] = playbook_data
    if "playbook" not in catalog_data["metadata"]["steps_completed"]:
        catalog_data["metadata"]["steps_completed"].append("playbook")
    catalog_data["metadata"]["playbook_generated_at"] = datetime.now().isoformat()

    with open(CATALOG_PATH, "w") as f:
        json.dump(catalog_data, f, indent=2, default=str)

    print(f"\nCatalog updated with playbook at {CATALOG_PATH}")
    print("US-005 COMPLETE")


def _find_move_examples(posts, signature_moves):
    """Find 3 example posts for each signature move based on move name keywords."""
    # Map move names to filtering criteria
    move_filters = {}
    for move in signature_moves:
        name = move.name
        # Heuristic: match posts based on key terms in the move's technique description
        technique_lower = move.technique.lower()
        # Try to find posts that match the described pattern
        matched = []
        for p in posts:
            score = 0
            # Check for keywords from the technique description
            if "identity" in technique_lower and p.get("framing_technique") == "identity_appeal":
                score += 3
            if "passionate" in technique_lower and p.get("tone") == "passionate":
                score += 2
            if "call to action" in technique_lower and p.get("content_category") == "call_to_action":
                score += 2
            if "build" in technique_lower and "reveal" in technique_lower and p.get("structural_pattern") == "build_to_reveal":
                score += 3
            if "myth" in technique_lower and p.get("structural_pattern") == "myth_bust":
                score += 3
            if "share" in technique_lower and p.get("call_to_action") == "share_this":
                score += 2
            if "antithesis" in technique_lower and "antithesis" in p.get("rhetoric_devices", []):
                score += 1
            if "tricolon" in technique_lower and "tricolon" in p.get("rhetoric_devices", []):
                score += 1
            if "rhetorical question" in technique_lower and "rhetorical_question" in p.get("rhetoric_devices", []):
                score += 1
            if "reframing" in technique_lower and p.get("framing_technique") == "reframing":
                score += 1
            if "provoc" in technique_lower and p.get("opening_hook") == "provocative_statement":
                score += 1
            if "empathy" in technique_lower and p.get("emotional_appeal") == "empathy":
                score += 2
            if "pride" in technique_lower and p.get("emotional_appeal") == "pride":
                score += 2
            if "advocacy" in technique_lower and p.get("primary_theme") == "advocacy_activism":
                score += 2
            if "statistic" in technique_lower and p.get("opening_hook") == "statistic":
                score += 2
            if "contrast" in technique_lower and p.get("framing_technique") == "contrast":
                score += 2
            if "list" in technique_lower and p.get("structural_pattern") == "list_format":
                score += 1
            if score > 0:
                matched.append((score, p["engagement_total"], p))

        # Sort by match score then engagement, take top 3
        matched.sort(key=lambda x: (-x[0], -x[1]))
        move_filters[name] = [m[2] for m in matched[:3]]

    return move_filters


def main():
    parser = argparse.ArgumentParser(description="Kevin Brown LinkedIn Content Analysis")
    parser.add_argument(
        "--step",
        choices=["catalog", "themes", "rhetoric", "format", "playbook"],
        default="catalog",
        help="Which analysis step to run",
    )
    args = parser.parse_args()

    if args.step == "catalog":
        step_catalog()
    elif args.step == "themes":
        step_themes()
    elif args.step == "rhetoric":
        step_rhetoric()
    elif args.step == "format":
        step_format()
    elif args.step == "playbook":
        step_playbook()


if __name__ == "__main__":
    main()
