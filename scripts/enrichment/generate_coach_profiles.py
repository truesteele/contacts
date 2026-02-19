#!/usr/bin/env python3
"""
Generate AI coaching profiles + embeddings for Camelback Expert Bench.

Uses GPT-5-mini to analyze each expert's full data and generate:
- Coaching summary (narrative of unique value)
- Expertise tags, coaching strengths, ideal-for description
- Combined search document for hybrid search

Then generates text-embedding-3-small embeddings for vector search.

Usage:
  python scripts/enrichment/generate_coach_profiles.py --test       # Test with 1 expert
  python scripts/enrichment/generate_coach_profiles.py              # Full run (all 73)
  python scripts/enrichment/generate_coach_profiles.py --embeddings-only  # Only generate embeddings
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = """You are an expert at analyzing professional profiles to understand what makes someone uniquely valuable as a coach or advisor.

Given a person's full professional profile, LinkedIn data, and recent posts, generate a structured coaching profile that will help match them with founders and entrepreneurs seeking specific help.

Return ONLY valid JSON with these fields:
{
  "coaching_summary": "2-3 paragraph narrative about what makes this person uniquely valuable as a coach. What's their superpower? What specific expertise do they bring? What kind of founder would benefit most from working with them? Be specific about their actual experience, not generic.",
  "expertise_tags": ["tag1", "tag2", ...],
  "coaching_strengths": ["strength1", "strength2", ...],
  "ideal_for": "1-2 sentence description of the ideal coaching scenario for this person"
}

Guidelines for tags and strengths:
- expertise_tags: 5-12 specific areas (e.g., "UX Design", "B2B SaaS Sales", "Nonprofit Fundraising", "Human-Centered Design", "EdTech", "DEI Strategy")
- coaching_strengths: 3-8 specific things they can help with (e.g., "Product-market fit validation", "Building a sales pipeline", "Designing equitable hiring processes")
- Be specific, not generic. "Marketing" is too broad; "B2B Content Marketing for SaaS" is better.
- Draw from their actual experience, employment history, skills, and post topics.
- If they have LinkedIn posts, use the post topics to understand their current interests and expertise."""


class CoachProfileGenerator:
    def __init__(self, test_mode=False, embeddings_only=False):
        self.supabase: Optional[Client] = None
        self.openai: Optional[OpenAI] = None
        self.test_mode = test_mode
        self.embeddings_only = embeddings_only
        self.stats = {
            "profiles_generated": 0,
            "profiles_failed": 0,
            "profiles_skipped": 0,
            "embeddings_generated": 0,
            "embeddings_failed": 0,
        }

    def connect(self) -> bool:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        openai_key = os.environ.get("OPENAI_APIKEY")

        if not url or not key:
            print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            return False
        if not openai_key:
            print("ERROR: Missing OPENAI_APIKEY")
            return False

        self.supabase = create_client(url, key)
        self.openai = OpenAI(api_key=openai_key)
        print("Connected to Supabase and OpenAI")
        return True

    def get_experts(self) -> List[Dict]:
        response = (
            self.supabase.table("camelback_experts")
            .select("*")
            .order("id")
            .execute()
        )
        return response.data

    def get_posts(self, expert_id: int) -> List[Dict]:
        response = (
            self.supabase.table("camelback_expert_posts")
            .select("post_content, post_date")
            .eq("expert_id", expert_id)
            .order("post_date", desc=True)
            .limit(20)
            .execute()
        )
        return response.data

    def get_existing_profile(self, expert_id: int) -> Optional[Dict]:
        response = (
            self.supabase.table("camelback_expert_search_profiles")
            .select("*")
            .eq("expert_id", expert_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None

    def build_expert_context(self, expert: Dict, posts: List[Dict]) -> str:
        """Build a comprehensive context string for GPT-5-mini."""
        parts = []

        parts.append(f"Name: {expert['name']}")
        if expert.get("position"):
            parts.append(f"Position: {expert['position']}")
        if expert.get("organization"):
            parts.append(f"Organization: {expert['organization']}")
        if expert.get("expert_areas"):
            parts.append(f"Camelback Expert Area: {expert['expert_areas']}")
        if expert.get("pronouns"):
            parts.append(f"Pronouns: {expert['pronouns']}")

        if expert.get("headline"):
            parts.append(f"\nLinkedIn Headline: {expert['headline']}")
        if expert.get("about"):
            parts.append(f"\nLinkedIn About:\n{expert['about']}")

        if expert.get("bio"):
            parts.append(f"\nCamelback Bio:\n{expert['bio']}")

        if expert.get("skills") and isinstance(expert["skills"], list):
            parts.append(f"\nCamelback Skills: {', '.join(expert['skills'])}")

        if expert.get("testimonials"):
            parts.append(f"\nTestimonials:\n{expert['testimonials']}")

        # Employment history
        if expert.get("employment"):
            emp = expert["employment"]
            if isinstance(emp, str):
                emp = json.loads(emp)
            if emp:
                parts.append("\nEmployment History:")
                for job in emp[:5]:
                    current = " (current)" if job.get("is_current") else ""
                    company = job.get("company_name", "Unknown")
                    title = job.get("job_title", "Unknown")
                    parts.append(f"  - {title} at {company}{current}")
                    if job.get("description"):
                        parts.append(f"    {job['description'][:200]}")

        # Education
        if expert.get("education"):
            edu = expert["education"]
            if isinstance(edu, str):
                edu = json.loads(edu)
            if edu:
                parts.append("\nEducation:")
                for e in edu:
                    school = e.get("school_name", "")
                    degree = e.get("degree", "")
                    field = e.get("field_of_study", "")
                    parts.append(f"  - {degree} {field} — {school}".strip())

        # Enriched skills
        if expert.get("skills_enriched"):
            sk = expert["skills_enriched"]
            if isinstance(sk, str):
                sk = json.loads(sk)
            if sk:
                skill_names = [s.get("skill_name", "") for s in sk if s.get("skill_name")]
                if skill_names:
                    parts.append(f"\nLinkedIn Skills: {', '.join(skill_names[:20])}")

        # Certifications
        if expert.get("certifications"):
            certs = expert["certifications"]
            if isinstance(certs, str):
                certs = json.loads(certs)
            if certs:
                cert_names = [c.get("name", "") for c in certs if c.get("name")]
                if cert_names:
                    parts.append(f"\nCertifications: {', '.join(cert_names)}")

        # Volunteering
        if expert.get("volunteering"):
            vol = expert["volunteering"]
            if isinstance(vol, str):
                vol = json.loads(vol)
            if vol:
                parts.append("\nVolunteering:")
                for v in vol[:3]:
                    org = v.get("organization", "")
                    role = v.get("role", "")
                    parts.append(f"  - {role} at {org}")

        # Recent posts
        if posts:
            parts.append(f"\nRecent LinkedIn Posts ({len(posts)} most recent):")
            for p in posts[:10]:
                content = (p.get("post_content") or "")[:300]
                date = p.get("post_date", "")[:10] if p.get("post_date") else ""
                parts.append(f"  [{date}] {content}")

        return "\n".join(parts)

    def generate_profile(self, expert_context: str) -> Optional[Dict]:
        """Call GPT-5-mini to generate a coaching profile."""
        try:
            response = self.openai.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": expert_context},
                ],
                max_completion_tokens=1500,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                print(f"    GPT returned empty content. Finish reason: {response.choices[0].finish_reason}")
                return None
            return json.loads(content)
        except Exception as e:
            print(f"    GPT error: {e}")
            return None

    def build_search_document(self, expert: Dict, profile: Dict) -> str:
        """Build a combined search document for full-text + embedding search."""
        parts = [
            f"Name: {expert['name']}",
            f"Position: {expert.get('position', '')} at {expert.get('organization', '')}",
            f"Expert Areas: {expert.get('expert_areas', '')}",
            f"Coaching Summary: {profile.get('coaching_summary', '')}",
            f"Expertise: {', '.join(profile.get('expertise_tags', []))}",
            f"Strengths: {', '.join(profile.get('coaching_strengths', []))}",
            f"Ideal For: {profile.get('ideal_for', '')}",
        ]
        if expert.get("headline"):
            parts.append(f"Headline: {expert['headline']}")
        if expert.get("bio"):
            parts.append(f"Bio: {expert['bio'][:500]}")
        if expert.get("skills") and isinstance(expert["skills"], list):
            parts.append(f"Skills: {', '.join(expert['skills'])}")
        return "\n".join(parts)

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using text-embedding-3-small."""
        try:
            response = self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"    Embedding error: {e}")
            return None

    def save_profile(self, expert_id: int, profile: Dict, search_document: str, embedding: Optional[List[float]]) -> bool:
        """Upsert the search profile into Supabase."""
        try:
            data = {
                "expert_id": expert_id,
                "coaching_summary": profile.get("coaching_summary"),
                "expertise_tags": profile.get("expertise_tags", []),
                "coaching_strengths": profile.get("coaching_strengths", []),
                "ideal_for": profile.get("ideal_for"),
                "search_document": search_document,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            if embedding:
                data["embedding"] = embedding

            self.supabase.table("camelback_expert_search_profiles").upsert(
                data, on_conflict="expert_id"
            ).execute()
            return True
        except Exception as e:
            print(f"    DB save error: {e}")
            return False

    def update_embedding(self, expert_id: int, embedding: List[float]) -> bool:
        """Update just the embedding for an existing profile."""
        try:
            self.supabase.table("camelback_expert_search_profiles").update(
                {"embedding": embedding}
            ).eq("expert_id", expert_id).execute()
            return True
        except Exception as e:
            print(f"    Embedding save error: {e}")
            return False

    def run(self):
        if not self.connect():
            return False

        experts = self.get_experts()
        total = len(experts)
        print(f"Found {total} experts")

        if self.test_mode:
            experts = experts[:1]
            print("TEST MODE: Processing 1 expert only\n")
        else:
            print()

        for i, expert in enumerate(experts, 1):
            name = expert["name"]
            expert_id = expert["id"]
            print(f"[{i}/{len(experts)}] {name}")

            existing = self.get_existing_profile(expert_id)

            if self.embeddings_only:
                if not existing:
                    print("  SKIP: No profile yet (run without --embeddings-only first)")
                    self.stats["profiles_skipped"] += 1
                    continue
                if existing.get("embedding"):
                    print("  SKIP: Already has embedding")
                    self.stats["embeddings_generated"] += 0
                    continue

                search_doc = existing.get("search_document", "")
                if not search_doc:
                    print("  SKIP: No search document")
                    continue

                print("  Generating embedding...")
                embedding = self.generate_embedding(search_doc)
                if embedding and self.update_embedding(expert_id, embedding):
                    print(f"  Embedding: Saved ({len(embedding)} dims)")
                    self.stats["embeddings_generated"] += 1
                else:
                    print("  Embedding: Failed")
                    self.stats["embeddings_failed"] += 1
                continue

            # Full profile generation
            if existing and existing.get("coaching_summary") and not self.test_mode:
                print("  Profile: Already generated, skipping")
                self.stats["profiles_skipped"] += 1

                # Still generate embedding if missing
                if not existing.get("embedding") and existing.get("search_document"):
                    print("  Generating missing embedding...")
                    embedding = self.generate_embedding(existing["search_document"])
                    if embedding and self.update_embedding(expert_id, embedding):
                        print(f"  Embedding: Saved ({len(embedding)} dims)")
                        self.stats["embeddings_generated"] += 1
                    else:
                        self.stats["embeddings_failed"] += 1
                continue

            # Get posts for context
            posts = self.get_posts(expert_id)

            # Build context and generate profile
            context = self.build_expert_context(expert, posts)
            print(f"  Context: {len(context)} chars, {len(posts)} posts")

            print("  Generating AI profile...")
            profile = self.generate_profile(context)
            if not profile:
                print("  Profile: FAILED")
                self.stats["profiles_failed"] += 1
                continue

            tags = profile.get("expertise_tags", [])
            strengths = profile.get("coaching_strengths", [])
            print(f"  Profile: {len(tags)} tags, {len(strengths)} strengths")

            # Build search document
            search_doc = self.build_search_document(expert, profile)

            # Generate embedding
            print("  Generating embedding...")
            embedding = self.generate_embedding(search_doc)
            if embedding:
                print(f"  Embedding: {len(embedding)} dims")
                self.stats["embeddings_generated"] += 1
            else:
                print("  Embedding: Failed (will save profile without it)")
                self.stats["embeddings_failed"] += 1

            # Save everything
            if self.save_profile(expert_id, profile, search_doc, embedding):
                print("  Saved to camelback_expert_search_profiles")
                self.stats["profiles_generated"] += 1
            else:
                self.stats["profiles_failed"] += 1

        self.print_summary()
        return True

    def print_summary(self):
        s = self.stats
        print("\n" + "=" * 60)
        print("COACH PROFILE GENERATION SUMMARY")
        print("=" * 60)
        print(f"  Profiles generated:   {s['profiles_generated']}")
        print(f"  Profiles failed:      {s['profiles_failed']}")
        print(f"  Profiles skipped:     {s['profiles_skipped']}")
        print(f"  Embeddings generated: {s['embeddings_generated']}")
        print(f"  Embeddings failed:    {s['embeddings_failed']}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Generate AI coaching profiles for Camelback experts")
    parser.add_argument("--test", "-t", action="store_true", help="Test with 1 expert")
    parser.add_argument("--embeddings-only", action="store_true", help="Only generate embeddings for existing profiles")
    args = parser.parse_args()

    generator = CoachProfileGenerator(
        test_mode=args.test,
        embeddings_only=args.embeddings_only,
    )
    success = generator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
