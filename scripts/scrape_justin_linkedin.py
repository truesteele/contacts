"""
Scrape Justin's LinkedIn profile and posts using Apify actors.
"""
import json
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

# Load API key
load_dotenv("/Users/Justin/Code/TrueSteele/contacts/.env")
api_key = os.getenv("APIFY_API_KEY")
if not api_key:
    raise RuntimeError("APIFY_API_KEY not found in .env")

client = ApifyClient(api_key)

# 1. Profile scrape
print("=" * 80)
print("SCRAPING LINKEDIN PROFILE")
print("=" * 80)

profile_input = {
    "urls": ["https://www.linkedin.com/in/justinrichardsteele/"]
}

print("Starting actor: harvestapi/linkedin-profile-scraper ...")
profile_run = client.actor("harvestapi/linkedin-profile-scraper").call(run_input=profile_input)

print(f"Run finished. Status: {profile_run.get('status')}")
print(f"Dataset ID: {profile_run.get('defaultDatasetId')}")
print()

profile_items = list(client.dataset(profile_run["defaultDatasetId"]).iterate_items())
print(f"Got {len(profile_items)} profile result(s).")
print()
print("FULL PROFILE JSON:")
print("-" * 80)
print(json.dumps(profile_items, indent=2, default=str))
print()

# 2. Posts scrape
print("=" * 80)
print("SCRAPING LINKEDIN POSTS")
print("=" * 80)

posts_input = {
    "profileUrls": ["https://www.linkedin.com/in/justinrichardsteele/"],
    "maxPosts": 100
}

print("Starting actor: harvestapi/linkedin-profile-posts ...")
posts_run = client.actor("harvestapi/linkedin-profile-posts").call(run_input=posts_input)

print(f"Run finished. Status: {posts_run.get('status')}")
print(f"Dataset ID: {posts_run.get('defaultDatasetId')}")
print()

posts_items = list(client.dataset(posts_run["defaultDatasetId"]).iterate_items())
print(f"Got {len(posts_items)} post(s).")
print()
print("FULL POSTS JSON:")
print("-" * 80)
print(json.dumps(posts_items, indent=2, default=str))
