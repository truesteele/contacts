#!/usr/bin/env python3
"""Test Azure OpenAI gpt-5-mini endpoint and structured output capability."""

import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Get Azure credentials
AZURE_APIKEY = os.environ.get("AZURE_APIKEY")
AZURE_ENDPOINT = os.environ.get("AZURE_5.1_MINI_ENDPOINT")

if not AZURE_APIKEY or not AZURE_ENDPOINT:
    raise ValueError("AZURE_APIKEY and AZURE_5.1_MINI_ENDPOINT must be set in .env")

# Extract components from endpoint URL
# Format: https://outdoorithm.cognitiveservices.azure.com/openai/deployments/gpt-5-mini/chat/completions?api-version=2024-05-01-preview
import re
from urllib.parse import urlparse, parse_qs

parsed = urlparse(AZURE_ENDPOINT)
base_url = f"{parsed.scheme}://{parsed.netloc}"
deployment_name = parsed.path.split('/')[3]  # /openai/deployments/gpt-5-mini/...
api_version = parse_qs(parsed.query).get('api-version', ['2024-05-01-preview'])[0]

print(f"Base URL: {base_url}")
print(f"Deployment: {deployment_name}")
print(f"API Version: {api_version}")
print(f"Full Endpoint: {AZURE_ENDPOINT}\n")

# Use AzureOpenAI client
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=base_url,
    api_key=AZURE_APIKEY,
    api_version=api_version
)

print("=" * 80)
print("TEST 1: Basic Chat Completion")
print("=" * 80)

try:
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France? Answer in one word."}
        ],
        temperature=0
    )

    print(f"✅ Basic chat completion works!")
    print(f"Response: {response.choices[0].message.content}\n")

except Exception as e:
    print(f"❌ Basic chat completion failed: {e}\n")
    exit(1)

print("=" * 80)
print("TEST 2: JSON Mode (Unstructured)")
print("=" * 80)

try:
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
            {"role": "user", "content": "List 3 major cities in France with their populations. Return as JSON with format: {cities: [{name: str, population: int}]}"}
        ],
        response_format={"type": "json_object"},
        temperature=0
    )

    result = json.loads(response.choices[0].message.content)
    print(f"✅ JSON mode works!")
    print(f"Response: {json.dumps(result, indent=2)}\n")

except Exception as e:
    print(f"❌ JSON mode failed: {e}\n")
    # Don't exit - might not be supported

print("=" * 80)
print("TEST 3: Structured Output with JSON Schema")
print("=" * 80)

# Define a simple Pydantic model for testing
class CityInfo(BaseModel):
    name: str
    population: int
    is_capital: bool

class CitiesResponse(BaseModel):
    cities: list[CityInfo]
    country: str

# Convert Pydantic model to JSON schema
schema = CitiesResponse.model_json_schema()

try:
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "List 3 major cities in France with their populations and whether they are the capital."}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "cities_response",
                "strict": True,
                "schema": schema
            }
        },
        temperature=0
    )

    result = json.loads(response.choices[0].message.content)
    print(f"✅ Structured output with JSON schema works!")
    print(f"Response: {json.dumps(result, indent=2)}\n")

    # Validate it matches our Pydantic model
    validated = CitiesResponse(**result)
    print(f"✅ Response validates against Pydantic model!")
    print(f"Validated: {validated}\n")

except Exception as e:
    print(f"❌ Structured output failed: {e}")
    print(f"This might mean:")
    print(f"  1. The model doesn't support structured outputs")
    print(f"  2. The API version is too old")
    print(f"  3. The deployment needs to be updated\n")

print("=" * 80)
print("TEST 4: Donor Qualification Example")
print("=" * 80)

# Test with a realistic donor qualification prompt
class DonorQualification(BaseModel):
    is_qualified: bool
    capacity_score: int  # 0-100
    reasoning: str
    key_indicators: list[str]
    estimated_capacity: str  # e.g., "$5k-$10k", "$10k-$25k"

donor_profile = """
Name: Sarah Johnson
Company: Google
Title: VP of Engineering
LinkedIn Headline: VP Engineering at Google | Former Director at Meta | Stanford MBA
Experience: 15 years in tech, previously Director at Meta, Senior Manager at Amazon
Education: MBA from Stanford, BS Computer Science from MIT
Location: Palo Alto, CA
Volunteer: Board member at Bay Area Women in Tech, Volunteer mentor at Code2040
"""

try:
    schema = DonorQualification.model_json_schema()

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {
                "role": "system",
                "content": """You are an expert at evaluating donor capacity for a nonprofit called Outdoorithm Collective, which provides outdoor experiences for urban families.

Evaluate if this person has legitimate capacity to give $5,000+ based on their professional profile. Consider:
- Job title and seniority (VP+ at major tech = high capacity)
- Company prestige (Google, Meta, Amazon = high compensation)
- Education (Stanford, MIT = high earning potential)
- Volunteer/board service (indicates philanthropic propensity)
- Location (Bay Area = high cost of living but high income)

Score their capacity from 0-100 where:
- 80-100: Very high capacity ($25k+ potential)
- 60-79: High capacity ($10k-$25k potential)
- 40-59: Moderate capacity ($5k-$10k potential)
- 20-39: Low capacity ($1k-$5k potential)
- 0-19: Very low capacity (<$1k potential)"""
            },
            {
                "role": "user",
                "content": f"Evaluate this donor prospect:\n\n{donor_profile}"
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "donor_qualification",
                "strict": True,
                "schema": schema
            }
        },
        temperature=0
    )

    result = json.loads(response.choices[0].message.content)
    print(f"✅ Donor qualification example works!")
    print(f"Response: {json.dumps(result, indent=2)}\n")

    validated = DonorQualification(**result)
    print(f"✅ Qualified: {validated.is_qualified}")
    print(f"✅ Capacity Score: {validated.capacity_score}/100")
    print(f"✅ Estimated Capacity: {validated.estimated_capacity}")
    print(f"✅ Reasoning: {validated.reasoning}\n")

except Exception as e:
    print(f"❌ Donor qualification example failed: {e}\n")

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print("If all tests passed, you're ready to proceed with implementation!")
print("If structured output failed, we can use json_object mode instead (less strict but works).")
