#!/usr/bin/env python3
"""
Sally Network Pipeline — OAuth Setup Helper

Runs the Google OAuth2 installed-app flow for Sally's 3 Google accounts.
Sally will need to run this interactively in a browser to authorize access.

After authorization, tokens are saved so gather_comms.py and gather_calendar.py
can access Sally's Gmail and Calendar data.

Usage:
  python scripts/intelligence/sally/setup_oauth.py                        # All 3 accounts
  python scripts/intelligence/sally/setup_oauth.py --account sally.steele@gmail.com  # Single account
  python scripts/intelligence/sally/setup_oauth.py --check                # Check which tokens exist

Prerequisites:
  pip install google-auth-oauthlib google-auth google-api-python-client
"""

import os
import sys
import json
import argparse
from pathlib import Path

# ── Sally's Google Accounts & Client Secret Mapping ──────────────────

CREDENTIALS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "docs", "credentials", "Sally"
)

TOKENS_DIR = os.path.join(CREDENTIALS_DIR, "tokens")

# Map each account to its client_secret file (identified by project_id prefix)
ACCOUNT_CONFIG = {
    "sally.steele@gmail.com": {
        "client_secret_prefix": "client_secret_682208951145",
        "project": "claude-mcp-sally-steele",
    },
    "sally@outdoorithm.com": {
        "client_secret_prefix": "client_secret_498441498515",
        "project": "claude-mcp-outdoorithm",
    },
    "sally@outdoorithmcollective.org": {
        "client_secret_prefix": "client_secret_443275901963",
        "project": "claude-mcp-collective",
    },
}

# Scopes needed for Gmail reading and Calendar reading
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def find_client_secret(account_email: str) -> str | None:
    """Find the client_secret JSON file for a given account."""
    config = ACCOUNT_CONFIG.get(account_email)
    if not config:
        return None

    prefix = config["client_secret_prefix"]
    cred_dir = Path(CREDENTIALS_DIR)

    for f in cred_dir.glob(f"{prefix}*.json"):
        return str(f)

    return None


def check_existing_tokens():
    """Check which accounts already have tokens."""
    print("Token status:")
    print("-" * 60)

    for account in ACCOUNT_CONFIG:
        # Check both token locations
        token_path_local = os.path.join(TOKENS_DIR, f"{account}.json")
        token_path_mcp = os.path.expanduser(
            f"~/.google_workspace_mcp/credentials/{account}.json"
        )

        has_local = os.path.exists(token_path_local)
        has_mcp = os.path.exists(token_path_mcp)

        if has_local:
            with open(token_path_local) as f:
                data = json.load(f)
            has_refresh = bool(data.get("refresh_token"))
            print(f"  {account}: LOCAL token {'(with refresh)' if has_refresh else '(no refresh token!)'}")
        elif has_mcp:
            with open(token_path_mcp) as f:
                data = json.load(f)
            has_refresh = bool(data.get("refresh_token"))
            print(f"  {account}: MCP token {'(with refresh)' if has_refresh else '(no refresh token!)'}")
        else:
            print(f"  {account}: NO TOKEN — needs setup")

    print("-" * 60)


def run_oauth_flow(account_email: str):
    """Run the OAuth2 installed-app flow for a single account."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: google-auth-oauthlib not installed.")
        print("  Run: pip install google-auth-oauthlib")
        return False

    client_secret_path = find_client_secret(account_email)
    if not client_secret_path:
        print(f"ERROR: No client_secret file found for {account_email}")
        print(f"  Expected files matching: {ACCOUNT_CONFIG[account_email]['client_secret_prefix']}*.json")
        print(f"  In directory: {CREDENTIALS_DIR}")
        return False

    print(f"\n{'='*60}")
    print(f"Setting up OAuth for: {account_email}")
    print(f"  Client secret: {os.path.basename(client_secret_path)}")
    print(f"  Project: {ACCOUNT_CONFIG[account_email]['project']}")
    print(f"  Scopes: Gmail (readonly), Calendar (readonly)")
    print(f"{'='*60}")
    print(f"\nA browser window will open. Sign in as {account_email}")
    print(f"and approve the requested permissions.\n")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret_path,
            scopes=SCOPES,
        )

        # Run local server flow (opens browser)
        creds = flow.run_local_server(
            port=8080,
            prompt="consent",
            login_hint=account_email,
        )

        # Save token
        os.makedirs(TOKENS_DIR, exist_ok=True)
        token_path = os.path.join(TOKENS_DIR, f"{account_email}.json")

        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else SCOPES,
            "account_email": account_email,
        }

        with open(token_path, "w") as f:
            json.dump(token_data, f, indent=2)

        print(f"\n  Token saved to: {token_path}")
        print(f"  Refresh token: {'YES' if creds.refresh_token else 'NO (will expire!)'}")
        return True

    except Exception as e:
        print(f"\nERROR during OAuth flow: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Set up Google OAuth tokens for Sally's accounts"
    )
    parser.add_argument("--account", type=str, default=None,
                        help="Set up only this account (e.g., sally.steele@gmail.com)")
    parser.add_argument("--check", action="store_true",
                        help="Only check which tokens exist, don't set up")
    args = parser.parse_args()

    if args.check:
        check_existing_tokens()
        return

    accounts_to_setup = []
    if args.account:
        if args.account not in ACCOUNT_CONFIG:
            print(f"Unknown account: {args.account}")
            print(f"Available accounts:")
            for acct in ACCOUNT_CONFIG:
                print(f"  {acct}")
            sys.exit(1)
        accounts_to_setup = [args.account]
    else:
        accounts_to_setup = list(ACCOUNT_CONFIG.keys())

    print("Sally's Google OAuth Setup")
    print("=" * 60)
    print(f"Accounts to set up: {len(accounts_to_setup)}")
    print(f"Credentials dir: {os.path.abspath(CREDENTIALS_DIR)}")
    print(f"Tokens will be saved to: {os.path.abspath(TOKENS_DIR)}")
    print()

    # Verify client_secret files exist
    for acct in accounts_to_setup:
        cs = find_client_secret(acct)
        if cs:
            print(f"  {acct}: {os.path.basename(cs)}")
        else:
            print(f"  {acct}: CLIENT SECRET NOT FOUND!")

    print()

    results = {}
    for acct in accounts_to_setup:
        success = run_oauth_flow(acct)
        results[acct] = success
        if success:
            print(f"  {acct}: SUCCESS")
        else:
            print(f"  {acct}: FAILED")

    print(f"\n{'='*60}")
    print("Setup Summary:")
    for acct, ok in results.items():
        status = "OK" if ok else "FAILED"
        print(f"  {acct}: {status}")
    print(f"{'='*60}")

    if all(results.values()):
        print("\nAll accounts set up! You can now run:")
        print("  python scripts/intelligence/sally/gather_comms.py --test")
        print("  python scripts/intelligence/sally/gather_calendar.py --test")
    else:
        print("\nSome accounts failed. Re-run with --account <email> to retry.")


if __name__ == "__main__":
    main()
