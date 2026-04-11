#!/usr/bin/env python3
"""
Seed Speaker Profiles — Podcast Outreach Tool

Seeds Sally and Justin Steele's speaker profiles into the speaker_profiles table.
Idempotent via upsert on slug.

Usage:
  python scripts/intelligence/seed_speaker_profiles.py            # seed both profiles
  python scripts/intelligence/seed_speaker_profiles.py --test     # dry run, print only
"""

import os
import json
import argparse

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")

# ── Supabase Client ──────────────────────────────────────────────────

def get_supabase() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)

# ── Profile Data ─────────────────────────────────────────────────────

SALLY = {
    "name": "Sally Steele",
    "slug": "sally",
    "bio": "CEO and Co-Founder of Outdoorithm, a social enterprise simplifying camping for urban families through AI-powered trip planning. Co-Founder and Board Chair of Outdoorithm Collective, a nonprofit creating belonging in nature for historically excluded communities. Ordained minister (MDiv, Gordon-Conwell). Mother of four. 107 family camping trips and counting. REI Embark Fellow. Louisville Institute grantee researching nature, liturgy, and women of color.",
    "headline": "CEO & Co-Founder, Outdoorithm | Board Chair, Outdoorithm Collective | Ordained Minister | 107 Family Camping Trips",
    "website_url": "https://www.sallysteele.org",
    "linkedin_url": "https://www.linkedin.com/in/steelesally",
    "topic_pillars": [
        {
            "name": "Family Camping as Equity Work",
            "description": "Camping is one of the most affordable, accessible ways for families to experience nature. $25/night at Humboldt Redwoods vs $11,300 at Disney. The wilderness does not have Lightning Lanes.",
            "talking_points": [
                "107 trips, 273 nights, 54 campgrounds with four kids",
                "Outdoorithm Collective: free camping trips for urban families, 260+ participants across 9 trips",
                "Disney vs Humboldt comparison: $11,300 vs $100 for the same family",
                "Four families on the trail. One looked like ours. That is not a nature problem. That is an access problem."
            ],
            "keywords": ["outdoor equity", "family camping", "nature access", "camping families", "affordable outdoors"]
        },
        {
            "name": "Sacred Space in Nature",
            "description": "The campfire as sacred space. Nature as encounter with something bigger than ourselves. Louisville Institute grantee studying nature, liturgy, and women of color.",
            "talking_points": [
                "Louisville Institute Pastoral Study Project: Reclaiming Sacred Ground",
                "Sacred spaces are containers we build intentionally for belonging",
                "The arena keeps us competing for scraps. Sacred space is where we practice the relationships that could flip the table.",
                "What started as inventory became something sacred - tending tools that remove barriers"
            ],
            "keywords": ["faith nature", "sacred space", "spirituality outdoors", "nature spirituality", "ministry outdoors"]
        },
        {
            "name": "Black Motherhood Outdoors",
            "description": "A Black mother of four navigating outdoor spaces where her family rarely sees families that look like them. Building community across difference in nature.",
            "talking_points": [
                "Four children ages 4-16, camping since the oldest was a toddler",
                "REI Embark Fellow (outdoor industry credibility as entrepreneur of color)",
                "Greenwood Ave magazine feature alongside Black Wall Street legacy",
                "Formerly Co-Executive Director of City Hope SF ($1.9M nonprofit in the Tenderloin)"
            ],
            "keywords": ["Black motherhood", "parenting outdoors", "women outdoors", "diversity outdoors", "outdoor parenting"]
        },
        {
            "name": "Building Community Across Difference",
            "description": "When a campervan got stuck, the engineer, doctor, social worker, actor all grabbed shovels. The wilderness does not check LinkedIn profiles.",
            "talking_points": [
                "48 people at Humboldt: when it lurched free, we flexed like we had won the championship",
                "Eliza called a man she met 48 hours earlier Uncle John. Now he was family.",
                "At Disney, I knew exactly who could afford Lightning Passes. At Humboldt, nobody sorted us at all.",
                "Justice Outside conference + Climate Week: two rooms not talking to each other"
            ],
            "keywords": ["community building", "bridging difference", "belonging", "outdoor community"]
        },
        {
            "name": "Founder Journey",
            "description": "Starting a business is one of the hardest things I have ever done, probably second only to birthing and parenting 4 kids. Both can be hard, messy and chaotic.",
            "talking_points": [
                "Left nonprofit leadership to start a social enterprise with her husband",
                "REI Path Ahead Ventures Summit: 45 outdoor founders of color, three days",
                "Exploring cooperative ownership model for Outdoorithm",
                "Camp as it comes: perfection is not the goal, adaptation is"
            ],
            "keywords": ["founder story", "social enterprise", "startup journey", "women founders"]
        },
        {
            "name": "Leave Anyway Philosophy",
            "description": "Not 'leave when ready' because you are never ready. Not 'leave when convenient' because it never is. Just: leave anyway.",
            "talking_points": [
                "His week: 24 meetings. Mine: 3 grant deadlines. Our reality: 2 startups to run. The forecast: atmospheric river.",
                "Justin chased a raccoon into the woods at 10pm, wrestled the mac and cheese container back",
                "Morning: rain dripping off redwoods, the Gualala River flowing past our site, a stillness I had not felt in months",
                "Seven more nights camping! demanded Eliza. Not one!"
            ],
            "keywords": ["outdoor family adventure", "camping with kids", "nature resilience", "adventure parenting"]
        }
    ],
    "writing_samples": [
        {
            "text": "$11,300 at Disney. $100 at Humboldt Redwoods. One sorted us by income. The other showed us what America could be. At Disney, I knew exactly who could afford Lightning Passes. The algorithm sorted us perfectly. At Humboldt, nobody sorted us at all. The wilderness does not check LinkedIn profiles. The river does not care about your ZIP code. 449 nights at Humboldt for the price of three at Disney. We will remember both trips. One for the magic money could buy. The other for the magic money could not touch.",
            "source": "LinkedIn - Disney vs Humboldt post (2,189 impressions, 152 engagements)"
        },
        {
            "text": "Leave anyway. That has become a mantra at Outdoorithm Collective. Not 'leave when ready' because you are never ready. Not 'leave when it is convenient' because it never is. Just: Leave anyway. His week: 24 meetings. Mine: 3 grant deadlines. Our reality: 2 startups to run. The forecast: Atmospheric river hitting the west coast. The smart move: Cancel everything. The deeper pull: Leave anyway.",
            "source": "LinkedIn - Leave Anyway post (1,477 impressions, 91 engagements)"
        },
        {
            "text": "Generational Gifts. That is what I was thinking about yesterday as I stood in a public storage unit with two board members and one of our youth leaders to sort camping gear. Not how I would normally spend a Sunday, but there we were. I picked up an unlabeled stuff sack, unzipped it, and found it full of straps. What started as inventory became something sacred.",
            "source": "LinkedIn - Generational Gifts post (2,161 impressions, 72 engagements)"
        },
        {
            "text": "I felt the gap before I could name it. Three days. Two rooms. Same crisis, different lenses. The two rooms were not talking to each other. Both are necessary. One builds community power. One builds literal power grids. But siloed, something essential gets lost. People do not protect what they do not love. And love grows from belonging.",
            "source": "LinkedIn - Justice Outside + Climate Week post (718 impressions)"
        }
    ],
    "past_appearances": [
        {
            "podcast_name": "Justice Outside Podcast",
            "episode_title": "TBD",
            "date": "2026-05",
            "url": None,
            "notes": "Recording complete, airing May 2026"
        }
    ]
}

JUSTIN = {
    "name": "Justin Steele",
    "slug": "justin",
    "bio": "Co-Founder and CEO of Kindora, an AI platform helping nonprofits find and win grants. Co-Founder and CTO of Outdoorithm, simplifying camping through AI. Board member, San Francisco Foundation. Former Google.org leader who directed over $100M in grants and built AI products for social impact. Ex-Bain consultant, HBS MBA, HKS MPA. Father of four. 107 family camping trips.",
    "headline": "Co-Founder & CEO, Kindora | Co-Founder & CTO, Outdoorithm | SF Foundation Board | Ex Google.org | HBS MBA",
    "website_url": "https://www.truesteele.com",
    "linkedin_url": "https://www.linkedin.com/in/justinrichardsteele",
    "topic_pillars": [
        {
            "name": "Corporate Philanthropy From the Inside",
            "description": "Spent a decade at Google.org directing grants and building AI products for social impact. Left to build what the system would not fund.",
            "talking_points": [
                "Directed $100M+ in Google.org grants across workforce development, racial justice, economic opportunity",
                "Led Google.org Fellowship teams deploying engineers to nonprofits",
                "Watched funders hesitate to make sustained infrastructure investments that great technology requires",
                "Only 36% of funders feel confident evaluating AI technical feasibility"
            ],
            "keywords": ["corporate philanthropy", "philanthropy", "grantmaking", "nonprofit funding", "social impact"]
        },
        {
            "name": "AI for Social Impact",
            "description": "Building Kindora, an AI platform that helps nonprofits find and win grants. If nonprofits do not harness AI, others will shape outcomes without our values.",
            "talking_points": [
                "Kindora uses AI to match nonprofits with funders, eliminating months of tedious prospecting",
                "Created AI funder personas that instantly filter thousands of poor-fit prospects",
                "Building with AI every single day, constantly blown away by what these tools can do",
                "Philanthropy seemed unprepared to scale AI innovation, so I started building myself"
            ],
            "keywords": ["AI social good", "nonprofit technology", "tech for good", "AI nonprofits", "social impact tech"]
        },
        {
            "name": "Leaving Big Tech for Purpose",
            "description": "Had one of those golden tickets for a decade. Made millions at Google. Gave it up. Now building impact for a fraction of that.",
            "talking_points": [
                "10 years at Google, left when his role was eliminated in 2024 layoffs",
                "Chose impact work over returning to Big Tech",
                "The person you have been trained to see as your enemy is drowning in the same rigged game",
                "Only sacrifice creates the moral authority that actually breaks systems"
            ],
            "keywords": ["leaving big tech", "purpose driven career", "career change", "tech to impact"]
        },
        {
            "name": "Outdoor Equity as Social Infrastructure",
            "description": "Co-founded Outdoorithm (for-profit) and Outdoorithm Collective (nonprofit) because nature is one of the most powerful equalizers we have.",
            "talking_points": [
                "107 family camping trips, father of four daughters ages 4-16",
                "Built AI-powered camping platform (Outdoorithm) and free community trips (Collective)",
                "SF Foundation board member, bringing outdoor equity perspective to Bay Area philanthropy",
                "When a campervan got stuck, everyone grabbed shovels. The wilderness does not check LinkedIn profiles."
            ],
            "keywords": ["outdoor equity", "nature access", "family camping", "social infrastructure"]
        },
        {
            "name": "Faith and Values at Work",
            "description": "UVA-trained chemical engineer turned HBS MBA turned philanthropist. Married to an ordained minister. Faith shapes how he builds.",
            "talking_points": [
                "You cannot build a society with people you will not sacrifice for",
                "Everyone feels unsafe. The system is working exactly as designed.",
                "Headwinds/tailwinds asymmetry: we feel every obstacle, forget every advantage",
                "How long will we keep fighting each other for scraps while the table stays exactly where it has always been?"
            ],
            "keywords": ["values leadership", "faith and work", "social justice", "moral leadership"]
        },
        {
            "name": "Founder Hustle",
            "description": "Running two startups, sitting on a major foundation board, raising four kids, and camping every other weekend. Building at the intersection of everything.",
            "talking_points": [
                "Kindora (AI for nonprofits) + Outdoorithm (AI for camping) + Outdoorithm Collective (free trips)",
                "True Steele LLC consulting practice for fractional Chief Impact Officer work",
                "When weather apps failed our group camping trips, built his own app in half a day",
                "Previous: Bain consultant, Bridgespan, Year Up leadership, HBS+HKS dual degree"
            ],
            "keywords": ["founder story", "startup hustle", "serial entrepreneur", "social enterprise"]
        }
    ],
    "writing_samples": [
        {
            "text": "Everyone feels unsafe. That is the point. Jewish students say they do not feel safe on campus. Black students think: Welcome to America, we never felt safe. Conservative employees say they are silenced. Progressive employees say they are gaslit. The system is not broken. It is working exactly as designed to make everyone feel precarious except the truly powerful. I had one of those tickets for a decade. Made millions at Google. Gave it up. Now I am back to doing impact work for a fraction of that.",
            "source": "LinkedIn - Everyone Feels Unsafe (49K impressions)"
        },
        {
            "text": "Researchers discovered something they call the headwinds/tailwinds asymmetry. We feel every bit of wind pushing against us. But the wind at our back? We forget it is even there. I biked to work for 15 years through everything. Snow, bomb cyclones, atmospheric rivers. I know headwinds. Fighting up Oakland hills into Diablo winds, counting every pedal stroke, cursing every gust. But when that same wind pushed me home? I would forget it existed after the first block.",
            "source": "LinkedIn - Headwinds/Tailwinds (follow-up post)"
        },
        {
            "text": "If nonprofits do not harness AI, others will, shaping outcomes without our values or communities in mind. I co-founded Outdoorithm as a for-profit social enterprise because I doubted nonprofit funding would scale to meet the demands of running an AI-powered social impact platform. After years leading nonprofits and directing grantmaking at Google.org, I have repeatedly watched funders hesitate to make the sustained infrastructure and talent investments that great technology requires.",
            "source": "LinkedIn - AI for Nonprofits post"
        },
        {
            "text": "When weather apps failed our Outdoorithm group camping trips, I built my own app in half a day. But that is nothing compared to what is coming. I am building new things with AI every single day, and I am constantly blown away by what these tools can do and how fast they are evolving.",
            "source": "LinkedIn - AI Revolution post"
        }
    ],
    "past_appearances": [
        {
            "podcast_name": "Wantrepreneur to Entrepreneur",
            "episode_title": "TBD",
            "date": "2026",
            "url": None,
            "notes": "Recent appearance"
        }
    ]
}

# ── Main ─────────────────────────────────────────────────────────────

def seed_profiles(test: bool = False):
    profiles = [SALLY, JUSTIN]

    if test:
        for p in profiles:
            print(f"\n{'='*60}")
            print(f"Speaker: {p['name']} (slug: {p['slug']})")
            print(f"Bio: {p['bio'][:80]}...")
            print(f"Topic pillars: {len(p['topic_pillars'])}")
            print(f"Writing samples: {len(p['writing_samples'])}")
            print(f"Past appearances: {len(p['past_appearances'])}")
        print(f"\n{'='*60}")
        print("DRY RUN — no database changes made")
        return

    sb = get_supabase()

    for p in profiles:
        row = {
            "name": p["name"],
            "slug": p["slug"],
            "bio": p["bio"],
            "headline": p["headline"],
            "website_url": p["website_url"],
            "linkedin_url": p["linkedin_url"],
            "topic_pillars": p["topic_pillars"],
            "writing_samples": p["writing_samples"],
            "past_appearances": p["past_appearances"],
        }

        result = sb.table("speaker_profiles").upsert(
            row, on_conflict="slug"
        ).execute()

        print(f"Upserted {p['name']} (slug: {p['slug']}) — {len(result.data)} row(s)")

    print("\nDone. Both speaker profiles seeded.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed speaker profiles for podcast outreach")
    parser.add_argument("--test", action="store_true", help="Dry run, print profiles without saving")
    args = parser.parse_args()

    seed_profiles(test=args.test)
