#!/usr/bin/env python3
"""
Find contacts who would be good voices for a philanthropy newsletter.
Searches across taxonomy, ai_tags (topical_affinity), text columns,
JSONB enrichment, volunteering, board positions, and LinkedIn posts.
"""

import os
import sys
import json
import csv
import io
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")

DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")
conn = psycopg2.connect(
    host="db.ypqsrejrsocebnldicke.supabase.co",
    port=5432,
    dbname="postgres",
    user="postgres",
    password=DB_PASSWORD,
)
conn.set_client_encoding("UTF8")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN QUERY: Wide-net philanthropy search across multiple signals
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 120)
print("PHILANTHROPY NEWSLETTER CONTACT SEARCH")
print("=" * 120)

# The query uses a scoring approach: each signal adds points.
# We collect contacts matching ANY philanthropy signal, then rank.

cur.execute("""
WITH philanthropy_contacts AS (
    SELECT
        c.id,
        c.normalized_full_name,
        c.first_name,
        c.last_name,
        c.headline,
        c.position,
        c.company,
        c.org,
        c.linkedin_url,
        c.email,
        c.summary,
        c.taxonomy_classification::text as taxonomy,
        c.ai_outdoorithm_fit,
        c.ai_tags,
        c.ask_readiness,
        c.enrich_current_title,
        c.enrich_current_company,
        c.enrich_board_positions,
        c.enrich_volunteering,
        c.enrich_titles_held,
        c.enrich_employment,
        c.enrich_volunteer_orgs,
        c.enrich_follower_count,
        c.summary_volunteering,
        c.company_name_volunteering,
        c.role_volunteering,
        c.summary_experience,
        c.company_experience,
        c.comms_closeness,
        c.comms_last_date,
        c.familiarity_rating,
        c.fec_donations,
        -- Signal flags for scoring
        CASE WHEN c.taxonomy_classification::text IN (
            'Strategic Business Prospects: Foundation Executives',
            'Knowledge & Industry Network: Philanthropy Professionals',
            'Knowledge & Industry Network: Social Impact Practitioners',
            'Strategic Business Prospects: Nonprofit Executives',
            'Newsletter Audience: Social Impact Professionals',
            'Newsletter Audience: DEI Practitioners',
            'Knowledge & Industry Network: Thought Leaders',
            'Support Network: Investors/Funders',
            'Knowledge & Industry Network: Environmental Champions'
        ) THEN 1 ELSE 0 END as taxonomy_match,

        -- Title/headline philanthropy keywords
        CASE WHEN (
            COALESCE(c.headline, '') || ' ' || COALESCE(c.position, '') || ' ' ||
            COALESCE(c.enrich_current_title, '')
        ) ILIKE ANY(ARRAY[
            '%foundation%', '%philanthrop%', '%nonprofit%', '%non-profit%',
            '%social impact%', '%impact invest%', '%grantmak%', '%grant mak%',
            '%charitable%', '%social enterprise%', '%community development%',
            '%social good%', '%mission-driven%', '%endowment%',
            '%CSR%', '%ESG%', '%public interest%', '%civic%',
            '%social justice%', '%racial equity%', '%environmental justice%',
            '%community foundation%', '%giving%', '%development director%',
            '%chief philanthropy%', '%chief impact%', '%social sector%',
            '%program officer%', '%program director%', '%executive director%',
            '%NGO%', '%humanitarian%', '%impact officer%', '%sustainability%',
            '%social innovation%', '%community organiz%', '%advocacy%',
            '%501(c)%', '%fund manager%', '%impact fund%', '%donor%',
            '%venture philanthrop%', '%social venture%', '%public policy%',
            '%government affairs%', '%public affairs%',
            '%board member%', '%trustee%'
        ]) THEN 1 ELSE 0 END as title_match,

        -- Company/org philanthropy keywords
        CASE WHEN (
            COALESCE(c.company, '') || ' ' || COALESCE(c.org, '') || ' ' ||
            COALESCE(c.enrich_current_company, '')
        ) ILIKE ANY(ARRAY[
            '%foundation%', '%philanthrop%', '%nonprofit%', '%non-profit%',
            '%institute%', '%association%', '%charity%', '%fund %',
            '%giving%', '%endowment%', '%trust%', '%social%',
            '%community%', '%united way%', '%red cross%', '%habitat%',
            '%sierra club%', '%nature conserv%', '%aclu%',
            '%omidyar%', '%gates%', '%ford foundation%', '%rockefeller%',
            '%skoll%', '%draper richards%', '%new profit%',
            '%echoing green%', '%ashoka%', '%schwab foundation%',
            '%impact%', '%google.org%', '%salesforce.org%',
            '%chan zuckerberg%', '%czi%', '%bloomberg%',
            '%council%', '%alliance%', '%coalition%',
            '%conservation%', '%environmental%', '%sustainability%',
            '%justice%', '%equity%', '%civic%', '%public%',
            '%ministry%', '%agency%', '%bureau%'
        ]) THEN 1 ELSE 0 END as org_match,

        -- ai_tags topical_affinity high-strength philanthropy topics
        CASE WHEN (
            c.ai_tags IS NOT NULL AND (
                c.ai_tags::text ILIKE '%"philanthropy"%'
                OR c.ai_tags::text ILIKE '%"grantmaking"%'
                OR c.ai_tags::text ILIKE '%"nonprofit_leadership"%'
                OR c.ai_tags::text ILIKE '%"social_impact%"%'
                OR c.ai_tags::text ILIKE '%"community_development"%'
                OR c.ai_tags::text ILIKE '%"social_enterprise"%'
                OR c.ai_tags::text ILIKE '%"impact_investing"%'
                OR c.ai_tags::text ILIKE '%"social_justice"%'
                OR c.ai_tags::text ILIKE '%"civic_engagement"%'
                OR c.ai_tags::text ILIKE '%"environmental_advocacy"%'
                OR c.ai_tags::text ILIKE '%"venture_philanthropy"%'
                OR c.ai_tags::text ILIKE '%"public_interest%"%'
                OR c.ai_tags::text ILIKE '%"social_sector"%'
            )
        ) THEN 1 ELSE 0 END as ai_topic_match,

        -- Volunteering/board signals
        CASE WHEN (
            c.enrich_board_positions IS NOT NULL
            AND c.enrich_board_positions::text != '[]'
            AND c.enrich_board_positions::text != 'null'
        ) THEN 1 ELSE 0 END as has_board_positions,

        -- ai_tags giving_capacity tier
        CASE WHEN c.ai_tags IS NOT NULL AND (
            c.ai_tags->'giving_capacity'->>'tier' IN ('major_donor', 'mid_level_donor')
        ) THEN 1 ELSE 0 END as high_giving_capacity,

        -- Summary/about mentions philanthropy
        CASE WHEN (
            COALESCE(c.summary, '') ILIKE ANY(ARRAY[
                '%philanthrop%', '%foundation%', '%nonprofit%', '%social impact%',
                '%grantmak%', '%charitable%', '%giving%', '%impact invest%',
                '%social enterprise%', '%community%', '%equity%', '%justice%',
                '%advocacy%', '%civic%', '%mission%', '%purpose%',
                '%sustainability%', '%ESG%', '%CSR%'
            ])
        ) THEN 1 ELSE 0 END as summary_match,

        -- FEC donations (politically active = philanthropically inclined proxy)
        CASE WHEN c.fec_donations IS NOT NULL
            AND c.fec_donations::text != '[]'
            AND c.fec_donations::text != 'null'
            AND c.fec_donations::text != '{}'
        THEN 1 ELSE 0 END as has_fec_donations,

        -- Has LinkedIn posts (voice/thought leadership signal)
        (SELECT COUNT(*) FROM contact_linkedin_posts p WHERE p.contact_id = c.id) as post_count

    FROM contacts c
    WHERE
        -- At least ONE philanthropy signal must be present
        (
            -- Taxonomy signals
            c.taxonomy_classification::text IN (
                'Strategic Business Prospects: Foundation Executives',
                'Knowledge & Industry Network: Philanthropy Professionals',
                'Knowledge & Industry Network: Social Impact Practitioners',
                'Strategic Business Prospects: Nonprofit Executives',
                'Newsletter Audience: Social Impact Professionals',
                'Newsletter Audience: DEI Practitioners',
                'Knowledge & Industry Network: Thought Leaders',
                'Support Network: Investors/Funders',
                'Knowledge & Industry Network: Environmental Champions',
                'Strategic Business Prospects: Corporate Impact Leaders'
            )
            -- Title/headline keywords
            OR (COALESCE(c.headline, '') || ' ' || COALESCE(c.position, '') || ' ' ||
                COALESCE(c.enrich_current_title, ''))
                ILIKE ANY(ARRAY[
                    '%foundation%', '%philanthrop%', '%nonprofit%', '%non-profit%',
                    '%social impact%', '%impact invest%', '%grantmak%', '%grant mak%',
                    '%charitable%', '%social enterprise%', '%community development%',
                    '%social good%', '%mission-driven%', '%endowment%',
                    '%CSR%', '%ESG%', '%public interest%', '%civic%',
                    '%social justice%', '%racial equity%', '%environmental justice%',
                    '%community foundation%', '%giving%', '%development director%',
                    '%chief philanthropy%', '%chief impact%', '%social sector%',
                    '%program officer%', '%program director%', '%executive director%',
                    '%NGO%', '%humanitarian%', '%impact officer%', '%sustainability%',
                    '%social innovation%', '%community organiz%', '%advocacy%',
                    '%impact fund%', '%donor%', '%venture philanthrop%',
                    '%social venture%', '%public policy%', '%public affairs%',
                    '%board member%', '%trustee%'
                ])
            -- Company/org keywords
            OR (COALESCE(c.company, '') || ' ' || COALESCE(c.org, '') || ' ' ||
                COALESCE(c.enrich_current_company, ''))
                ILIKE ANY(ARRAY[
                    '%foundation%', '%philanthrop%', '%nonprofit%', '%non-profit%',
                    '%institute%', '%charity%', '%giving%', '%endowment%',
                    '%social%impact%', '%social%enterprise%',
                    '%community%foundation%', '%united way%', '%habitat%',
                    '%omidyar%', '%ford foundation%', '%rockefeller%',
                    '%skoll%', '%draper richards%', '%new profit%',
                    '%echoing green%', '%ashoka%', '%google.org%',
                    '%chan zuckerberg%', '%czi%',
                    '%conservation%', '%justice%fund%', '%equity%fund%',
                    '%impact%fund%', '%venture%philanthrop%'
                ])
            -- ai_tags topical affinity
            OR (c.ai_tags IS NOT NULL AND (
                c.ai_tags::text ILIKE '%"philanthropy"%'
                OR c.ai_tags::text ILIKE '%"grantmaking"%'
                OR c.ai_tags::text ILIKE '%"nonprofit_leadership"%'
                OR c.ai_tags::text ILIKE '%"social_impact%"%'
                OR c.ai_tags::text ILIKE '%"community_development"%'
                OR c.ai_tags::text ILIKE '%"social_enterprise"%'
                OR c.ai_tags::text ILIKE '%"impact_investing"%'
                OR c.ai_tags::text ILIKE '%"social_justice"%'
                OR c.ai_tags::text ILIKE '%"civic_engagement"%'
                OR c.ai_tags::text ILIKE '%"environmental_advocacy"%'
                OR c.ai_tags::text ILIKE '%"venture_philanthropy"%'
                OR c.ai_tags::text ILIKE '%"public_interest%"%'
            ))
            -- Summary
            OR COALESCE(c.summary, '') ILIKE ANY(ARRAY[
                '%philanthrop%', '%foundation%lead%', '%grantmak%',
                '%social impact%', '%impact invest%', '%social enterprise%'
            ])
        )
)
SELECT
    id,
    normalized_full_name,
    headline,
    position,
    company,
    org,
    enrich_current_title,
    enrich_current_company,
    linkedin_url,
    email,
    taxonomy,
    ai_outdoorithm_fit,
    comms_closeness,
    comms_last_date,
    familiarity_rating,
    enrich_follower_count,
    post_count,
    -- Composite score
    (taxonomy_match * 3 +
     title_match * 3 +
     org_match * 2 +
     ai_topic_match * 3 +
     summary_match * 2 +
     high_giving_capacity * 2 +
     has_board_positions * 1 +
     has_fec_donations * 1 +
     CASE WHEN post_count > 0 THEN 2 ELSE 0 END
    ) as philanthropy_score,
    -- Raw flags for debugging
    taxonomy_match,
    title_match,
    org_match,
    ai_topic_match,
    summary_match,
    high_giving_capacity,
    has_board_positions,
    has_fec_donations,
    -- Detailed data
    ai_tags->'topical_affinity'->'topics' as ai_topics,
    ai_tags->'giving_capacity'->>'tier' as giving_tier,
    ai_tags->'giving_capacity'->>'score' as giving_score,
    ask_readiness->'outdoorithm_fundraising'->>'tier' as ask_tier,
    summary
FROM philanthropy_contacts
ORDER BY
    -- Primary: philanthropy_score desc
    (taxonomy_match * 3 +
     title_match * 3 +
     org_match * 2 +
     ai_topic_match * 3 +
     summary_match * 2 +
     high_giving_capacity * 2 +
     has_board_positions * 1 +
     has_fec_donations * 1 +
     CASE WHEN post_count > 0 THEN 2 ELSE 0 END
    ) DESC,
    -- Secondary: post_count (thought leadership signal)
    post_count DESC,
    -- Tertiary: familiarity (closer contacts first)
    COALESCE(familiarity_rating, 0) DESC
""")

results = cur.fetchall()
print(f"\nTotal contacts matching philanthropy signals: {len(results)}\n")

# Print results grouped by score tier
current_score = None
for i, r in enumerate(results):
    score = r['philanthropy_score']
    if score != current_score:
        current_score = score
        print(f"\n{'=' * 120}")
        print(f"  PHILANTHROPY SCORE: {score}")
        print(f"{'=' * 120}")

    # Format the key info
    name = r['normalized_full_name'] or f"{r.get('first_name','')} {r.get('last_name','')}"
    title = r['enrich_current_title'] or r['headline'] or r['position'] or ''
    company = r['enrich_current_company'] or r['company'] or r['org'] or ''
    linkedin = r['linkedin_url'] or ''
    email = r['email'] or ''
    taxonomy = r['taxonomy'] or ''
    posts = r['post_count'] or 0
    followers = r['enrich_follower_count'] or ''
    closeness = r['comms_closeness'] or ''
    familiarity = r['familiarity_rating'] or ''
    giving_tier = r['giving_tier'] or ''
    giving_score = r['giving_score'] or ''
    ask_tier = r['ask_tier'] or ''

    # Signals
    signals = []
    if r['taxonomy_match']: signals.append(f"TAX:{taxonomy[:60]}")
    if r['title_match']: signals.append("TITLE")
    if r['org_match']: signals.append("ORG")
    if r['ai_topic_match']: signals.append("AI_TOPICS")
    if r['summary_match']: signals.append("SUMMARY")
    if r['high_giving_capacity']: signals.append(f"GIVING:{giving_tier}({giving_score})")
    if r['has_board_positions']: signals.append("BOARD")
    if r['has_fec_donations']: signals.append("FEC")
    if posts > 0: signals.append(f"POSTS:{posts}")

    # AI topics (philanthropy-related only)
    ai_topics_str = ""
    if r['ai_topics']:
        topics = r['ai_topics']
        if isinstance(topics, list):
            phil_topics = [t.get('topic','') for t in topics
                         if any(kw in t.get('topic','').lower()
                               for kw in ['philanthrop', 'grant', 'nonprofit', 'social',
                                          'impact', 'community', 'civic', 'justice',
                                          'equity', 'environment', 'advocacy', 'giving',
                                          'public_interest', 'venture_philanth'])]
            ai_topics_str = ", ".join(phil_topics)

    print(f"\n  [{i+1:3d}] {name}")
    print(f"        Title:    {title[:100]}")
    print(f"        Company:  {company[:100]}")
    print(f"        Taxonomy: {taxonomy}")
    print(f"        LinkedIn: {linkedin}")
    print(f"        Email:    {email}")
    print(f"        Signals:  {' | '.join(signals)}")
    if ai_topics_str:
        print(f"        AI Topics: {ai_topics_str}")
    if followers:
        print(f"        Followers: {followers}")
    if closeness:
        print(f"        Closeness: {closeness} | Familiarity: {familiarity}")
    if ask_tier:
        print(f"        Ask Tier: {ask_tier}")

# ── Summary stats ───────────────────────────────────────────────────────────
print(f"\n\n{'=' * 120}")
print("SUMMARY STATISTICS")
print(f"{'=' * 120}")

score_dist = defaultdict(int)
taxonomy_dist = defaultdict(int)
with_posts = 0
with_email = 0
with_linkedin = 0

for r in results:
    score_dist[r['philanthropy_score']] += 1
    if r['taxonomy']:
        taxonomy_dist[r['taxonomy']] += 1
    if r['post_count'] and r['post_count'] > 0:
        with_posts += 1
    if r['email']:
        with_email += 1
    if r['linkedin_url']:
        with_linkedin += 1

print(f"\nTotal matches: {len(results)}")
print(f"With email: {with_email}")
print(f"With LinkedIn: {with_linkedin}")
print(f"With LinkedIn posts: {with_posts}")

print(f"\nScore distribution:")
for score in sorted(score_dist.keys(), reverse=True):
    print(f"  Score {score:2d}: {score_dist[score]:4d} contacts")

print(f"\nTaxonomy distribution:")
for tax in sorted(taxonomy_dist.keys(), key=lambda x: taxonomy_dist[x], reverse=True):
    print(f"  {tax:60s} {taxonomy_dist[tax]:4d}")

# ── Top philanthropy voices (high score + posts) ───────────────────────────
print(f"\n\n{'=' * 120}")
print("TOP PHILANTHROPY VOICES (Score >= 8 AND Has Posts)")
print(f"{'=' * 120}")

top_voices = [r for r in results if r['philanthropy_score'] >= 8 and r['post_count'] and r['post_count'] > 0]
print(f"\n{len(top_voices)} contacts")

for r in top_voices:
    name = r['normalized_full_name'] or ''
    title = r['enrich_current_title'] or r['headline'] or r['position'] or ''
    company = r['enrich_current_company'] or r['company'] or ''
    print(f"  - {name} | {title[:80]} @ {company[:60]} | {r['post_count']} posts")

# ── Also show top voices by score alone (score >= 10) ───────────────────────
print(f"\n\n{'=' * 120}")
print("HIGHEST SCORED CONTACTS (Score >= 10, regardless of posts)")
print(f"{'=' * 120}")

top_scored = [r for r in results if r['philanthropy_score'] >= 10]
print(f"\n{len(top_scored)} contacts")

for r in top_scored:
    name = r['normalized_full_name'] or ''
    title = r['enrich_current_title'] or r['headline'] or r['position'] or ''
    company = r['enrich_current_company'] or r['company'] or ''
    posts = r['post_count'] or 0
    print(f"  - {name} | {title[:80]} @ {company[:60]} | posts:{posts} | score:{r['philanthropy_score']}")

conn.close()
print("\n\nDone.")
