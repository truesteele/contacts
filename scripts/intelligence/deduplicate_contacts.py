#!/usr/bin/env python3
"""
Deduplicate contacts using LinkedIn URL as primary key, email as backup.

Strategy:
  1. Normalize LinkedIn URLs (lowercase, strip trailing slash, normalize www)
  2. Group duplicates by normalized URL
  3. Pick "winner" per group: prefers connected_on, enrichment, email, lower ID
  4. Merge any non-null fields from losers into winner
  5. Delete loser rows
  6. For same-name/different-URL pairs, flag for review

Usage:
  python scripts/intelligence/deduplicate_contacts.py              # Dry run
  python scripts/intelligence/deduplicate_contacts.py --execute    # Actually merge + delete
"""

import os
import re
import json
import argparse
from collections import defaultdict
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

# Manually confirmed same-person pairs with different LinkedIn URLs.
# Format: list of ID lists — first ID in each list is preferred "keep" candidate.
# Bob Friedman (1934 vs 2643) excluded: different people.
MANUAL_MERGE_GROUPS = [
    [370, 2958],   # Abi Ogunmwonyi (Beyond Sport -> WOW Foundation)
    [667, 2966],   # Annie Lewin (Google -> career break)
    [82, 2947],    # Brandon Jones (Comerica, URL slug change)
    [709, 2968],   # Chelsea Tate (Google/Women Techmakers -> Mercor)
    [1928, 2816],  # Chris Kiagiri (empty -> Sinapis)
    [338, 2955],   # Donnel Baird (same company, URL change)
    [401, 2959],   # Dwight Williams (Bank Street -> Teaching Matters)
    [575, 2962],   # Jalon Thomas (Google, URL change)
    [694, 2600],   # Jenny Flores (AMH Catalyst, URL change)
    [276, 2954],   # Kate Leidy (Strively -> LinkedIn)
    [206, 2949],   # Mariam Wakili (Self-employed/Freelance)
    [247, 2951],   # Michael Munoz (Google, URL change)
    [691, 2967],   # Milena Meehan (Google, URL change)
    [409, 2961],   # Ryan Demarco Anderson (Comerica -> Ameriprise)
    [343, 2956],   # Samuel Rugi (Foundry -> Nasdaq)
    [654, 2965],   # Velda Habaj (ADS Inc, URL change)
]

# Columns to merge (COALESCE from loser into winner where winner is NULL)
MERGE_COLS = [
    "email", "email_2", "normalized_phone_number", "company", "position",
    "connected_on", "headline", "summary", "country", "location_name",
    "city", "state", "org", "connections", "num_followers",
    "work_email", "personal_email", "email_verified", "email_type",
    "enriched_at", "enrich_employment", "enrich_education",
    "enrich_skills_detailed", "enrich_certifications", "enrich_volunteering",
    "enrich_publications", "enrich_honors_awards", "enrich_languages", "enrich_projects",
    "enrich_follower_count", "enrich_connections", "enrich_profile_pic_url",
    "enrich_current_company", "enrich_current_title", "enrich_current_since",
    "enrich_years_in_current_role", "enrich_total_experience_years",
    "enrich_number_of_positions", "enrich_number_of_companies",
    "enrich_highest_degree", "enrich_schools", "enrich_fields_of_study",
    "enrich_companies_worked", "enrich_titles_held", "enrich_skills",
    "enrich_board_positions", "enrich_volunteer_orgs",
    "enrich_publication_count", "enrich_award_count",
    "donor_capacity_score", "donor_propensity_score", "donor_affinity_score",
    "donor_warmth_score", "donor_total_score", "donor_tier",
    "estimated_capacity", "real_estate_indicator", "company_revenue_tier",
    "executive_level", "known_donor", "past_giving_details",
    "nonprofit_board_member", "board_service_details",
    "outdoor_environmental_affinity", "outdoor_affinity_evidence",
    "equity_access_focus", "equity_focus_evidence",
    "family_youth_focus", "family_focus_evidence",
    "warmth_level", "shared_institutions", "shared_institutions_details",
    "connection_type", "relationship_notes", "personal_connection_strength",
    "perplexity_enriched_at", "perplexity_research_data", "perplexity_sources",
    "cultivation_stage", "cultivation_notes", "cultivation_plan",
    "next_touchpoint_date", "next_touchpoint_type",
    "last_contact_date", "last_contact_method",
    "notes", "joshua_tree_invited",
    "ai_tags", "ai_tags_generated_at", "ai_tags_model",
    "ai_proximity_score", "ai_proximity_tier",
    "ai_capacity_score", "ai_capacity_tier",
    "ai_kindora_prospect_score", "ai_kindora_prospect_type", "ai_outdoorithm_fit",
    "mailerlite_subscriber_id", "mailerlite_groups", "mailerlite_status",
    "synced_to_mailerlite",
]

# AI score columns — use the HIGHER score when merging
SCORE_COLS = {
    "ai_proximity_score": "ai_proximity_tier",
    "ai_capacity_score": "ai_capacity_tier",
    "ai_kindora_prospect_score": "ai_kindora_prospect_type",
}


def normalize_linkedin_url(url: str) -> str:
    """Normalize LinkedIn URL for comparison."""
    if not url:
        return ""
    url = url.strip().lower()
    url = re.sub(r"/$", "", url)
    url = re.sub(r"https://(www\.)?linkedin\.com", "https://www.linkedin.com", url)
    return url


def fetch_all_contacts():
    """Fetch all contacts with pagination."""
    all_contacts = []
    page_size = 1000
    offset = 0
    while True:
        resp = supabase.table("contacts").select("*").order("id").range(
            offset, offset + page_size - 1
        ).execute()
        if not resp.data:
            break
        all_contacts.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_contacts


def pick_winner(contacts: list[dict]) -> tuple[dict, list[dict]]:
    """Pick the best record to keep. Returns (winner, losers)."""
    def score(c):
        s = 0
        if c.get("connected_on"):
            s += 100  # LinkedIn export record — has connection date
        if c.get("enriched_at"):
            s += 50
        if c.get("email"):
            s += 25
        if c.get("headline"):
            s += 10
        if c.get("summary"):
            s += 10
        if c.get("ai_tags"):
            s += 5
        # Prefer lower ID as tiebreaker (original record)
        s -= c["id"] * 0.001
        return s

    sorted_contacts = sorted(contacts, key=score, reverse=True)
    return sorted_contacts[0], sorted_contacts[1:]


def build_merge_update(winner: dict, losers: list[dict]) -> dict:
    """Build update dict: fill winner's NULLs from loser data, take higher AI scores."""
    update = {}

    for col in MERGE_COLS:
        if col in SCORE_COLS:
            continue  # Handle score cols separately
        winner_val = winner.get(col)
        if winner_val is None or winner_val == "" or winner_val == []:
            for loser in losers:
                loser_val = loser.get(col)
                if loser_val is not None and loser_val != "" and loser_val != []:
                    update[col] = loser_val
                    break

    # For AI scores, take the higher value
    for score_col, tier_col in SCORE_COLS.items():
        winner_score = winner.get(score_col) or 0
        best_score = winner_score
        best_tier = winner.get(tier_col)
        best_source = winner
        for loser in losers:
            loser_score = loser.get(score_col) or 0
            if loser_score > best_score:
                best_score = loser_score
                best_tier = loser.get(tier_col)
                best_source = loser
        if best_score > (winner.get(score_col) or 0):
            update[score_col] = best_score
            update[tier_col] = best_tier
            # Also take the full ai_tags from the higher-scored source if the score col is proximity
            if score_col == "ai_proximity_score" and best_source.get("ai_tags"):
                update["ai_tags"] = best_source["ai_tags"]
                update["ai_tags_generated_at"] = best_source.get("ai_tags_generated_at")
                update["ai_tags_model"] = best_source.get("ai_tags_model")

    return update


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Actually perform merges and deletes")
    args = parser.parse_args()

    dry_run = not args.execute

    print(f"{'DRY RUN' if dry_run else 'EXECUTING'} — Deduplicating contacts")
    print("=" * 70)

    contacts = fetch_all_contacts()
    print(f"Fetched {len(contacts)} contacts")

    # --- Phase 1: LinkedIn URL duplicates ---
    url_groups = defaultdict(list)
    no_url = []
    for c in contacts:
        norm = normalize_linkedin_url(c.get("linkedin_url", "") or "")
        if norm:
            url_groups[norm].append(c)
        else:
            no_url.append(c)

    url_dupes = {url: group for url, group in url_groups.items() if len(group) > 1}
    print(f"\nPhase 1: LinkedIn URL duplicates: {len(url_dupes)} groups, "
          f"{sum(len(g) - 1 for g in url_dupes.values())} rows to remove")

    merge_actions = []
    for url, group in sorted(url_dupes.items()):
        winner, losers = pick_winner(group)
        merge_update = build_merge_update(winner, losers)
        merge_actions.append((winner, losers, merge_update))

        loser_ids = [l["id"] for l in losers]
        name = f"{winner['first_name']} {winner['last_name']}"
        fields_merged = list(merge_update.keys()) if merge_update else []
        print(f"  KEEP id={winner['id']:4d} {name:<30s} | DELETE ids={loser_ids}"
              f"{f' | merge: {fields_merged}' if fields_merged else ''}")

    # --- Phase 2: Manual merge groups (same name, different URL, confirmed same person) ---
    contacts_by_id = {c["id"]: c for c in contacts}
    already_deleted = set()
    for _, losers, _ in merge_actions:
        for l in losers:
            already_deleted.add(l["id"])

    manual_count = 0
    print(f"\nPhase 2: Manual merge groups (confirmed same person, different URLs): {len(MANUAL_MERGE_GROUPS)} groups")
    for id_list in MANUAL_MERGE_GROUPS:
        group = [contacts_by_id[cid] for cid in id_list if cid in contacts_by_id and cid not in already_deleted]
        if len(group) <= 1:
            continue
        winner, losers = pick_winner(group)
        merge_update = build_merge_update(winner, losers)
        merge_actions.append((winner, losers, merge_update))
        for l in losers:
            already_deleted.add(l["id"])
        manual_count += len(losers)
        loser_ids = [l["id"] for l in losers]
        name = f"{winner['first_name']} {winner['last_name']}"
        fields_merged = list(merge_update.keys()) if merge_update else []
        print(f"  KEEP id={winner['id']:4d} {name:<30s} | DELETE ids={loser_ids}"
              f"{f' | merge: {fields_merged}' if fields_merged else ''}")
    print(f"  {manual_count} additional rows to remove")

    # --- Phase 3: Email duplicates (for contacts without LinkedIn URL) ---
    email_groups = defaultdict(list)
    for c in no_url:
        if c["id"] in already_deleted:
            continue
        email = (c.get("email") or "").strip().lower()
        if email:
            email_groups[email].append(c)

    email_dupes = {e: g for e, g in email_groups.items() if len(g) > 1}
    if email_dupes:
        print(f"\nPhase 3: Email duplicates (no LinkedIn URL): {len(email_dupes)} groups")
        for email, group in sorted(email_dupes.items()):
            winner, losers = pick_winner(group)
            merge_update = build_merge_update(winner, losers)
            merge_actions.append((winner, losers, merge_update))
            loser_ids = [l["id"] for l in losers]
            name = f"{winner['first_name']} {winner['last_name']}"
            print(f"  KEEP id={winner['id']:4d} {name:<30s} | DELETE ids={loser_ids}")
    else:
        print(f"\nPhase 3: No email duplicates among contacts without LinkedIn URL")

    # --- Phase 4: Flag same-name/different-URL pairs ---
    name_groups = defaultdict(list)
    for c in contacts:
        key = (c.get("first_name", "").strip().lower(), c.get("last_name", "").strip().lower())
        if key[0] and key[1]:
            name_groups[key].append(c)

    print(f"\nPhase 4: Same name, different LinkedIn URL (review needed):")
    flagged = 0

    for (fn, ln), group in sorted(name_groups.items()):
        remaining = [c for c in group if c["id"] not in already_deleted]
        if len(remaining) <= 1:
            continue
        # Check if they have different normalized URLs
        urls = set()
        for c in remaining:
            norm = normalize_linkedin_url(c.get("linkedin_url", "") or "")
            if norm:
                urls.add(norm)
        if len(urls) > 1:
            flagged += 1
            print(f"  {remaining[0]['first_name']} {remaining[0]['last_name']}:")
            for c in remaining:
                print(f"    id={c['id']:4d} | {c.get('company', 'N/A'):<35s} | {c.get('linkedin_url', 'N/A')}")

    if flagged == 0:
        print("  None — all name dupes resolved by URL matching")

    # --- Summary ---
    total_deletes = sum(len(losers) for _, losers, _ in merge_actions)
    total_merges = sum(1 for _, _, u in merge_actions if u)
    print(f"\n{'=' * 70}")
    print(f"SUMMARY: {len(merge_actions)} groups, {total_deletes} rows to delete, "
          f"{total_merges} winner records to update, {flagged} flagged for review")
    print(f"Final contact count: {len(contacts)} -> {len(contacts) - total_deletes}")

    if dry_run:
        print(f"\nRe-run with --execute to apply changes")
        return

    # --- Execute ---
    print(f"\nExecuting merges and deletes...")
    merged = 0
    deleted = 0
    refs_reassigned = 0

    # Tables that reference contacts via foreign key
    REFERENCING_TABLES = ["invalid_emails", "email_sends"]

    for winner, losers, merge_update in merge_actions:
        # Update winner with merged fields
        if merge_update:
            supabase.table("contacts").update(merge_update).eq("id", winner["id"]).execute()
            merged += 1

        # Reassign foreign key references from losers to winner, then delete losers
        for loser in losers:
            for ref_table in REFERENCING_TABLES:
                try:
                    result = supabase.table(ref_table).update(
                        {"contact_id": winner["id"]}
                    ).eq("contact_id", loser["id"]).execute()
                    if result.data:
                        refs_reassigned += len(result.data)
                except Exception:
                    pass  # No rows to reassign

            supabase.table("contacts").delete().eq("id", loser["id"]).execute()
            deleted += 1

    print(f"Done! Updated {merged} winners, deleted {deleted} duplicate rows, "
          f"reassigned {refs_reassigned} FK references")

    # Verify final count
    count = supabase.table("contacts").select("id", count="exact").execute()
    print(f"Final contact count: {count.count}")


if __name__ == "__main__":
    main()
