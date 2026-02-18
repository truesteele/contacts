#!/usr/bin/env python3
"""
Validate end-to-end Network Intelligence System with all 5 use cases from Section 12.

Usage:
  source .venv/bin/activate
  python scripts/intelligence/validate_use_cases.py
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
openai_client = OpenAI(api_key=os.environ["OPENAI_APIKEY"])

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 768


def get_embedding(text: str) -> list[float]:
    resp = openai_client.embeddings.create(
        model=EMBEDDING_MODEL, input=text, dimensions=EMBEDDING_DIMS
    )
    return resp.data[0].embedding


def use_case_1():
    """Outdoorithm Collective Fundraiser Invite"""
    print("=" * 70)
    print("USE CASE 1: Outdoorithm Collective Fundraiser Invite")
    print("Query: proximity >= 40 AND outdoorithm_invite_fit IN (high, medium)")
    print("=" * 70)

    result = supabase.table("contacts").select(
        "first_name, last_name, company, position, "
        "ai_proximity_score, ai_proximity_tier, ai_capacity_score, ai_capacity_tier, "
        "ai_outdoorithm_fit"
    ).gte("ai_proximity_score", 40).in_(
        "ai_outdoorithm_fit", ["high", "medium"]
    ).order("ai_proximity_score", desc=True).order(
        "ai_capacity_score", desc=True
    ).limit(10).execute()

    print(f"\nTotal matching (top 10 shown):")
    for i, r in enumerate(result.data):
        print(f"  {i+1:2d}. {r['first_name']} {r['last_name']:<25s} | {r['company']:<40s} | "
              f"prox={r['ai_proximity_score']} ({r['ai_proximity_tier']}) | "
              f"cap={r['ai_capacity_score']} ({r['ai_capacity_tier']}) | "
              f"fit={r['ai_outdoorithm_fit']}")

    # Count total
    count_result = supabase.table("contacts").select(
        "id", count="exact"
    ).gte("ai_proximity_score", 40).in_(
        "ai_outdoorithm_fit", ["high", "medium"]
    ).execute()
    total = count_result.count
    print(f"\n  Total contacts matching: {total}")
    print()
    return result.data, total


def use_case_2():
    """Kindora Enterprise Prospects"""
    print("=" * 70)
    print("USE CASE 2: Kindora Enterprise Prospects")
    print("Query: kindora_prospect_score >= 50 AND type IN (enterprise_buyer, champion)")
    print("=" * 70)

    result = supabase.table("contacts").select(
        "first_name, last_name, company, position, "
        "ai_kindora_prospect_score, ai_kindora_prospect_type, "
        "ai_proximity_score, ai_proximity_tier, ai_capacity_tier"
    ).gte("ai_kindora_prospect_score", 50).in_(
        "ai_kindora_prospect_type", ["enterprise_buyer", "champion"]
    ).order("ai_kindora_prospect_score", desc=True).limit(10).execute()

    print(f"\nTop 10 Kindora prospects:")
    for i, r in enumerate(result.data):
        print(f"  {i+1:2d}. {r['first_name']} {r['last_name']:<25s} | {r['company']:<40s} | "
              f"score={r['ai_kindora_prospect_score']} ({r['ai_kindora_prospect_type']}) | "
              f"prox={r['ai_proximity_score']} ({r['ai_proximity_tier']})")

    count_result = supabase.table("contacts").select(
        "id", count="exact"
    ).gte("ai_kindora_prospect_score", 50).in_(
        "ai_kindora_prospect_type", ["enterprise_buyer", "champion"]
    ).execute()
    total = count_result.count
    print(f"\n  Total contacts matching: {total}")
    print()
    return result.data, total


def use_case_3():
    """People Interested in Outdoor Equity (semantic search)"""
    print("=" * 70)
    print("USE CASE 3: People Interested in Outdoor Equity (Semantic Search)")
    print("Query embedding: 'outdoor equity, nature access, public lands, camping, environmental justice'")
    print("=" * 70)

    query = "outdoor equity, nature access, public lands, camping, environmental justice"
    emb = get_embedding(query)

    results = supabase.rpc("match_contacts_by_interests", {
        "query_embedding": emb,
        "match_threshold": 0.45,
        "match_count": 10,
    }).execute()

    print(f"\nTop 10 by interests similarity:")
    for i, r in enumerate(results.data):
        print(f"  {i+1:2d}. {r['first_name']} {r['last_name']:<25s} | {r.get('company', 'N/A'):<40s} | "
              f"sim={r['similarity']:.3f} | "
              f"prox={r.get('ai_proximity_score', 'N/A')} ({r.get('ai_proximity_tier', 'N/A')})")

    print()
    return results.data


def use_case_4():
    """Close Contacts (proximity >= 60)"""
    print("=" * 70)
    print("USE CASE 4: Close Contacts (proximity >= 60)")
    print("Note: Without Layer 3 (comms history), showing all close+ contacts")
    print("=" * 70)

    result = supabase.table("contacts").select(
        "first_name, last_name, company, position, "
        "ai_proximity_score, ai_proximity_tier, ai_capacity_score, ai_capacity_tier"
    ).gte("ai_proximity_score", 60).order(
        "ai_proximity_score", desc=True
    ).limit(10).execute()

    print(f"\nTop 10 close contacts:")
    for i, r in enumerate(result.data):
        print(f"  {i+1:2d}. {r['first_name']} {r['last_name']:<25s} | {r['company']:<40s} | "
              f"prox={r['ai_proximity_score']} ({r['ai_proximity_tier']}) | "
              f"cap={r['ai_capacity_score']} ({r['ai_capacity_tier']})")

    count_result = supabase.table("contacts").select(
        "id", count="exact"
    ).gte("ai_proximity_score", 60).execute()
    total = count_result.count
    print(f"\n  Total contacts with proximity >= 60: {total}")
    print()
    return result.data, total


def use_case_5():
    """Hybrid Search — philanthropy education technology"""
    print("=" * 70)
    print("USE CASE 5: Hybrid Search — 'philanthropy education technology'")
    print("Combines semantic similarity + keyword search with RRF fusion")
    print("=" * 70)

    query_text = "philanthropy education technology"
    query_emb = get_embedding(query_text)

    results = supabase.rpc("hybrid_contact_search", {
        "query_text": query_text,
        "query_embedding": query_emb,
        "filter_proximity_min": 0,
        "filter_capacity_min": 0,
        "semantic_weight": 1.0,
        "keyword_weight": 1.0,
        "match_count": 10,
        "rrf_k": 50,
    }).execute()

    print(f"\nTop 10 hybrid search results:")
    for i, r in enumerate(results.data):
        print(f"  {i+1:2d}. {r['first_name']} {r['last_name']:<25s} | {r.get('company', 'N/A'):<40s} | "
              f"rrf_score={r['score']:.4f}")

    print()
    return results.data


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("NETWORK INTELLIGENCE SYSTEM — END-TO-END VALIDATION")
    print("=" * 70 + "\n")

    uc1_data, uc1_total = use_case_1()
    uc2_data, uc2_total = use_case_2()
    uc3_data = use_case_3()
    uc4_data, uc4_total = use_case_4()
    uc5_data = use_case_5()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  UC1 (Outdoorithm Invite): {uc1_total} contacts match")
    print(f"  UC2 (Kindora Prospects):   {uc2_total} contacts match")
    print(f"  UC3 (Outdoor Equity):      {len(uc3_data)} semantic results returned")
    print(f"  UC4 (Close Contacts):      {uc4_total} contacts with proximity >= 60")
    print(f"  UC5 (Hybrid Search):       {len(uc5_data)} hybrid results returned")
    print()
    print("All 5 use cases executed successfully!")
