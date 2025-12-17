#!/usr/bin/env python3
"""Test Azure OpenAI with raw HTTP requests."""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

AZURE_APIKEY = os.environ.get("AZURE_APIKEY")
AZURE_ENDPOINT = os.environ.get("AZURE_5.1_MINI_ENDPOINT")

print(f"API Key (first 10 chars): {AZURE_APIKEY[:10]}...")
print(f"Endpoint: {AZURE_ENDPOINT}\n")

# Try with api-key header (Azure Cognitive Services style)
headers = {
    "api-key": AZURE_APIKEY,
    "Content-Type": "application/json"
}

payload = {
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France? Answer in one word."}
    ]
    # Note: gpt-5-mini only supports temperature=1 (default), so we omit it
}

print("=" * 80)
print("TEST 1: Using api-key header")
print("=" * 80)

try:
    response = requests.post(
        AZURE_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=30
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}\n")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Answer: {result['choices'][0]['message']['content']}")
    else:
        print(f"❌ Failed with status {response.status_code}")

except Exception as e:
    print(f"❌ Error: {e}\n")

# Try with Authorization header (alternative)
print("=" * 80)
print("TEST 2: Using Authorization Bearer header")
print("=" * 80)

headers2 = {
    "Authorization": f"Bearer {AZURE_APIKEY}",
    "Content-Type": "application/json"
}

try:
    response = requests.post(
        AZURE_ENDPOINT,
        headers=headers2,
        json=payload,
        timeout=30
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}\n")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Answer: {result['choices'][0]['message']['content']}")
    else:
        print(f"❌ Failed with status {response.status_code}")

except Exception as e:
    print(f"❌ Error: {e}\n")
