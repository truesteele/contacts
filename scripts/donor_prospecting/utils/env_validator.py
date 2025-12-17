"""
Environment variable validation for donor prospecting system.

Validates all required environment variables at startup to fail fast with clear error messages.
"""

import os
from typing import List, Dict


class EnvValidationError(Exception):
    """Raised when required environment variables are missing or invalid."""
    pass


def validate_env() -> Dict[str, str]:
    """
    Validate all required environment variables.

    Returns:
        Dict of validated env vars

    Raises:
        EnvValidationError if validation fails
    """
    required_vars = {
        'AZURE_APIKEY': 'Azure OpenAI API key',
        'AZURE_5.1_MINI_ENDPOINT': 'Azure GPT-5-mini endpoint URL',
        'PERPLEXITY_APIKEY': 'Perplexity API key',
        'SUPABASE_URL': 'Supabase project URL',
        'SUPABASE_SERVICE_KEY': 'Supabase service role key'
    }

    missing = []
    invalid = []
    env_values = {}

    # Check for missing vars
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if not value:
            missing.append(f"{var} ({description})")
        else:
            env_values[var] = value

    if missing:
        raise EnvValidationError(
            f"Missing required environment variables:\n  " +
            "\n  ".join(missing) +
            "\n\nPlease set these in your .env file or environment."
        )

    # Validate Azure endpoint format
    azure_endpoint = env_values.get('AZURE_5.1_MINI_ENDPOINT', '')
    if not azure_endpoint.startswith('https://'):
        invalid.append("AZURE_5.1_MINI_ENDPOINT must start with https://")

    if 'api-version' not in azure_endpoint:
        invalid.append("AZURE_5.1_MINI_ENDPOINT must include api-version parameter")
    elif 'api-version=2024-08-01-preview' not in azure_endpoint:
        # Warn about API version but don't fail
        print(f"⚠️  WARNING: AZURE_5.1_MINI_ENDPOINT uses different API version than tested (2024-08-01-preview)")
        print(f"   Structured outputs may not work correctly.")

    # Validate Supabase URL format
    supabase_url = env_values.get('SUPABASE_URL', '')
    if not supabase_url.startswith('https://') or '.supabase.co' not in supabase_url:
        invalid.append("SUPABASE_URL must be a valid Supabase URL (https://xxxxx.supabase.co)")

    # Validate API keys have reasonable length
    if len(env_values.get('AZURE_APIKEY', '')) < 32:
        invalid.append("AZURE_APIKEY appears too short (expected 64+ chars)")

    if len(env_values.get('PERPLEXITY_APIKEY', '')) < 20:
        invalid.append("PERPLEXITY_APIKEY appears too short")

    if invalid:
        raise EnvValidationError(
            f"Invalid environment variables:\n  " +
            "\n  ".join(invalid)
        )

    return env_values


def print_env_status():
    """Print environment configuration status."""
    print("\n" + "=" * 80)
    print("ENVIRONMENT VALIDATION")
    print("=" * 80)

    try:
        env_values = validate_env()

        print("✅ All required environment variables are set")
        print(f"\nAzure Endpoint: {env_values['AZURE_5.1_MINI_ENDPOINT'][:60]}...")
        print(f"Azure API Key: {env_values['AZURE_APIKEY'][:10]}...{env_values['AZURE_APIKEY'][-10:]}")
        print(f"Perplexity API Key: {env_values['PERPLEXITY_APIKEY'][:10]}...")
        print(f"Supabase URL: {env_values['SUPABASE_URL']}")
        print("=" * 80 + "\n")

        return True

    except EnvValidationError as e:
        print(f"❌ ENVIRONMENT VALIDATION FAILED")
        print(f"\n{str(e)}")
        print("\n" + "=" * 80 + "\n")
        return False
