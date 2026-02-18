#!/usr/bin/env python3
"""
Test script for Supabase RPC search functions.

Tests:
1. match_contacts_by_profile — semantic search on profile embedding
2. match_contacts_by_interests — semantic search on interests embedding
3. hybrid_contact_search — combined semantic + keyword with RRF fusion

Usage:
  source .venv/bin/activate
  python scripts/intelligence/test_search_functions.py
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
    """Generate a 768-dim embedding for a text query."""
    resp = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMS,
    )
    return resp.data[0].embedding


def test_match_contacts_by_profile():
    """Test profile similarity search using a known contact's embedding."""
    print("=" * 60)
    print("TEST 1: match_contacts_by_profile")
    print("Query: contacts similar to Kay Fernandez Smith (id=10)")
    print("=" * 60)

    # Get Kay's embedding as the query
    row = supabase.table("contacts").select("profile_embedding").eq("id", 10).single().execute()
    query_emb = row.data["profile_embedding"]

    results = supabase.rpc("match_contacts_by_profile", {
        "query_embedding": query_emb,
        "match_threshold": 0.6,
        "match_count": 10,
    }).execute()

    for i, r in enumerate(results.data):
        print(f"  {i+1}. {r['first_name']} {r['last_name']} | {r['company']} | "
              f"proximity={r['ai_proximity_score']} ({r['ai_proximity_tier']}) | "
              f"sim={r['similarity']:.3f}")
    print()


def test_match_contacts_by_interests():
    """Test interests similarity search with a text query."""
    print("=" * 60)
    print("TEST 2: match_contacts_by_interests")
    print("Query: 'outdoor equity, nature access, public lands, environmental justice'")
    print("=" * 60)

    query = "outdoor equity, nature access, public lands, camping, environmental justice"
    emb = get_embedding(query)

    results = supabase.rpc("match_contacts_by_interests", {
        "query_embedding": emb,
        "match_threshold": 0.5,
        "match_count": 10,
    }).execute()

    for i, r in enumerate(results.data):
        print(f"  {i+1}. {r['first_name']} {r['last_name']} | {r['company']} | "
              f"proximity={r['ai_proximity_score']} ({r['ai_proximity_tier']}) | "
              f"sim={r['similarity']:.3f}")
    print()


def test_hybrid_contact_search():
    """Test hybrid search combining semantic + keyword + structured filters."""
    print("=" * 60)
    print("TEST 3: hybrid_contact_search")
    print("Query text: 'philanthropy education technology'")
    print("Filters: proximity >= 0, capacity >= 0")
    print("=" * 60)

    query_text = "philanthropy education technology"
    query_emb = get_embedding(query_text)

    results = supabase.rpc("hybrid_contact_search", {
        "query_text": query_text,
        "query_embedding": query_emb,
        "filter_proximity_min": 0,
        "filter_capacity_min": 0,
        "semantic_weight": 1.0,
        "keyword_weight": 1.0,
        "match_count": 15,
        "rrf_k": 50,
    }).execute()

    for i, r in enumerate(results.data):
        print(f"  {i+1}. {r['first_name']} {r['last_name']} | {r['company']} | "
              f"score={r['score']:.4f}")
    print()


def test_hybrid_with_filters():
    """Test hybrid search with proximity and capacity filters."""
    print("=" * 60)
    print("TEST 4: hybrid_contact_search (with filters)")
    print("Query text: 'foundation grantmaking nonprofit'")
    print("Filters: proximity >= 30, capacity >= 40")
    print("=" * 60)

    query_text = "foundation grantmaking nonprofit"
    query_emb = get_embedding(query_text)

    results = supabase.rpc("hybrid_contact_search", {
        "query_text": query_text,
        "query_embedding": query_emb,
        "filter_proximity_min": 30,
        "filter_capacity_min": 40,
        "semantic_weight": 1.0,
        "keyword_weight": 1.5,  # boost keyword matches
        "match_count": 10,
        "rrf_k": 50,
    }).execute()

    for i, r in enumerate(results.data):
        print(f"  {i+1}. {r['first_name']} {r['last_name']} | {r['company']} | "
              f"score={r['score']:.4f}")
    print()


if __name__ == "__main__":
    test_match_contacts_by_profile()
    test_match_contacts_by_interests()
    test_hybrid_contact_search()
    test_hybrid_with_filters()
    print("All tests passed!")
