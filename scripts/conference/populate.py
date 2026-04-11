#!/usr/bin/env python3
"""
Conference networking toolkit — Config-driven Supabase population.

Loads warm leads + triage results + shortlist from config data paths,
joins them by attendee ID, and upserts into the configured Supabase table.

Usage:
  python scripts/conference/populate.py --config conferences/ted-2026/config.yaml
  python scripts/conference/populate.py --config conferences/ted-2026/config.yaml --dry-run
"""

import os
import json
import argparse
from collections import Counter

from dotenv import load_dotenv
from supabase import create_client

load_dotenv('/Users/Justin/Code/TrueSteele/contacts/.env')

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.conference.config import ConferenceConfig


def load_json(path: str) -> list[dict]:
    """Load a JSON file, returning empty list if missing."""
    if not path or not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def build_rows(config: ConferenceConfig, leads: list[dict], triage: list[dict], shortlist: list[dict],
               existing_state: dict[str, dict]) -> list[dict]:
    """Build upsert rows by joining leads + triage + shortlist."""
    prefix = config.conference.field_prefix
    id_field = f"{prefix}_id" if prefix else "id"
    name_field = f"{prefix}_name" if prefix else "name"

    triage_by_id = {t[id_field]: t for t in triage if id_field in t}
    shortlist_by_id = {s[id_field]: s for s in shortlist if id_field in s}

    # Determine which lead fields to copy (all fields with the prefix, plus connection fields)
    # We'll auto-detect: copy all fields from leads as-is
    rows = []
    for lead in leads:
        aid = lead.get(id_field)
        if not aid:
            continue

        t = triage_by_id.get(aid, {})
        s = shortlist_by_id.get(aid)

        # Start with all lead fields
        row = {}
        for k, v in lead.items():
            # Boolean-ify known role fields
            role_fields = {r['field'] for r in config.conference.roles}
            if k in role_fields:
                row[k] = bool(v)
            else:
                row[k] = v

        # Connection fields — also boolean
        for user_key in ('primary', 'support'):
            user = getattr(config.users, user_key)
            conn_field = user.connection_field or f"{user.name.lower()}_connection"
            if conn_field in lead:
                row[conn_field] = bool(lead[conn_field])

        # Triage scoring fields
        row['relevance_score'] = t.get('relevance_score')
        row['partnership_type'] = t.get('partnership_type')
        row['partnership_types'] = json.dumps(t.get('partnership_types', []))
        row['reasoning'] = t.get('reasoning')
        row['conversation_hook'] = t.get('conversation_hook')
        row['key_signal'] = t.get('key_signal')

        # Tier from shortlist
        row['tier'] = s.get('tier') if s else None

        # User-specific columns — initialize with defaults, migrate existing state
        name = lead.get(name_field, '')
        state = existing_state.get(name, {})

        for user_key in ('primary', 'support'):
            user = getattr(config.users, user_key)
            for col_role, col_name in user.columns.items():
                if col_role == 'pinned':
                    row[col_name] = False
                elif col_role == 'reached_out':
                    row[col_name] = state.get(col_name, False) or False
                elif col_role == 'notes':
                    row[col_name] = None
                elif col_role == 'context':
                    row[col_name] = state.get(col_name)
                else:
                    row[col_name] = state.get(col_name)

        rows.append(row)

    return rows


def main():
    parser = argparse.ArgumentParser(description='Config-driven Supabase population for conference attendees')
    parser.add_argument('--config', required=True, help='Path to conference config YAML')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be inserted without touching DB')
    parser.add_argument('--batch-size', type=int, default=500, help='Upsert batch size (default: 500)')
    args = parser.parse_args()

    config = ConferenceConfig(args.config)
    prefix = config.conference.field_prefix
    id_field = f"{prefix}_id" if prefix else "id"
    table_name = config.supabase.table_name

    print(f"Conference: {config.conference.name}")
    print(f"Table: {table_name}")
    print(f"ID field: {id_field}")
    print()

    # Load data files
    print("Loading data...")
    leads = load_json(config.data_paths.warm_leads)
    triage = load_json(config.data_paths.triage_results)
    shortlist = load_json(config.data_paths.shortlist)
    print(f"  Leads: {len(leads)}, Triage: {len(triage)}, Shortlist: {len(shortlist)}")

    # Load existing state to migrate (if table exists and not dry-run)
    existing_state: dict[str, dict] = {}
    if not args.dry_run:
        sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])
        try:
            # Try loading existing state from the legacy lookbook_state table
            state_table = f"{prefix}_lookbook_state" if prefix else "lookbook_state"
            state_resp = sb.table(state_table).select('*').execute()
            if state_resp.data:
                existing_state = {s.get('contact_name', ''): s for s in state_resp.data}
                print(f"  Existing state entries: {len(existing_state)}")
        except Exception:
            print("  No legacy state table found (OK)")

    # Build rows
    rows = build_rows(config, leads, triage, shortlist, existing_state)
    print(f"\nPrepared {len(rows)} rows")

    # Summary stats
    tier_counts = Counter(r.get('tier') for r in rows if r.get('tier') is not None)
    for tier_num in sorted(tier_counts):
        label = config.tiers[tier_num].label if tier_num in config.tiers else f"Tier {tier_num}"
        print(f"  Tier {tier_num} ({label}): {tier_counts[tier_num]}")

    scored = sum(1 for r in rows if r.get('relevance_score') is not None)
    print(f"  Scored: {scored}/{len(rows)}")

    pt_counts = Counter(r.get('partnership_type') for r in rows if r.get('partnership_type'))
    for pt, count in pt_counts.most_common():
        print(f"  {pt}: {count}")

    if args.dry_run:
        print("\n[DRY RUN] Would upsert these rows to Supabase. No changes made.")
        if rows:
            print(f"\nSample row keys: {list(rows[0].keys())}")
            print(f"Sample row (first): {json.dumps(rows[0], indent=2, default=str)[:500]}...")
        return

    # Upsert to Supabase
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])
    for i in range(0, len(rows), args.batch_size):
        batch = rows[i:i + args.batch_size]
        sb.table(table_name).upsert(batch, on_conflict=id_field).execute()
        print(f"  Inserted batch {i // args.batch_size + 1}: rows {i+1}-{i+len(batch)}")

    # Verify
    count_resp = sb.table(table_name).select(id_field, count='exact').execute()
    print(f"\nTotal rows in {table_name}: {count_resp.count}")

    for tier_num in sorted(config.tiers.keys()):
        t_resp = sb.table(table_name).select(id_field, count='exact').eq('tier', tier_num).execute()
        label = config.tiers[tier_num].label
        print(f"  Tier {tier_num} ({label}): {t_resp.count}")

    # Check user-specific columns
    primary_cols = config.users.primary.columns
    if 'pinned' in primary_cols:
        pinned = sb.table(table_name).select(id_field, count='exact').eq(primary_cols['pinned'], True).execute()
        print(f"  {config.users.primary.name} pinned: {pinned.count}")

    support_cols = config.users.support.columns
    if 'context' in support_cols:
        ctx_col = support_cols['context']
        name_field_db = f"{prefix}_name" if prefix else "name"
        with_ctx = sb.table(table_name).select(name_field_db).neq(ctx_col, '').not_.is_(ctx_col, 'null').execute()
        print(f"  With {config.users.support.name} context: {len(with_ctx.data)}")
        for c in with_ctx.data:
            print(f"    - {c[name_field_db]}")

    print("\nDone!")


if __name__ == '__main__':
    main()
