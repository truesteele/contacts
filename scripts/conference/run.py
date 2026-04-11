#!/usr/bin/env python3
"""
Conference networking toolkit — CLI entry point.

Orchestrates the full pipeline: triage → populate → generate → deploy.

Usage:
  python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step generate
  python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step triage --test
  python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step all
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts" / "conference"


def run_step(step_script: str, config_path: str, extra_args: list[str] | None = None):
    """Run a pipeline step as a subprocess, streaming output."""
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / step_script),
        "--config", config_path,
    ]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'='*60}")
    print(f"  Running: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        print(f"\nERROR: {step_script} exited with code {result.returncode}")
        sys.exit(result.returncode)


def step_triage(config_path: str, args: argparse.Namespace):
    extra = []
    if args.test:
        extra.append("--test")
    if args.workers:
        extra.extend(["--workers", str(args.workers)])
    run_step("triage.py", config_path, extra)


def step_populate(config_path: str, args: argparse.Namespace):
    extra = []
    if args.dry_run:
        extra.append("--dry-run")
    run_step("populate.py", config_path, extra)


def step_generate(config_path: str, args: argparse.Namespace):
    run_step("generate_lookbook.py", config_path)


def step_deploy(config_path: str, args: argparse.Namespace):
    # Load config to get deploy_dir and alias
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.conference.config import ConferenceConfig
    config = ConferenceConfig(config_path)

    deploy_dir = Path(config.vercel.deploy_dir)
    if not deploy_dir.is_absolute():
        deploy_dir = REPO_ROOT / deploy_dir

    if not deploy_dir.exists():
        print(f"ERROR: Deploy directory does not exist: {deploy_dir}")
        sys.exit(1)

    alias = config.vercel.alias
    scope = config.vercel.scope

    print(f"\n{'='*60}")
    print(f"  Deploying from: {deploy_dir}")
    print(f"  Scope: {scope}")
    print(f"  Alias: {alias}")
    print(f"{'='*60}\n")

    # Deploy to Vercel
    result = subprocess.run(
        ["npx", "vercel", "--prod", "--yes", "--scope", scope],
        cwd=str(deploy_dir),
    )
    if result.returncode != 0:
        print(f"\nERROR: Vercel deploy failed with code {result.returncode}")
        sys.exit(result.returncode)

    # Alias if configured
    if alias:
        result = subprocess.run(
            ["npx", "vercel", "alias", "set", ".", f"{alias}.vercel.app", "--scope", scope],
            cwd=str(deploy_dir),
        )
        if result.returncode != 0:
            print(f"\nWARNING: Alias failed (deploy succeeded). You may need to set alias manually.")


STEPS = {
    "triage": step_triage,
    "populate": step_populate,
    "generate": step_generate,
    "deploy": step_deploy,
}


def main():
    parser = argparse.ArgumentParser(
        description="Conference networking toolkit — run pipeline steps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Score attendees
  python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step triage --test

  # Populate Supabase (dry run)
  python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step populate --dry-run

  # Generate lookbook HTML
  python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step generate

  # Deploy to Vercel
  python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step deploy

  # Run full pipeline
  python scripts/conference/run.py --config conferences/ted-2026/config.yaml --step all
        """,
    )
    parser.add_argument("--config", required=True, help="Path to conference config YAML")
    parser.add_argument(
        "--step",
        required=True,
        choices=["triage", "populate", "generate", "deploy", "all"],
        help="Pipeline step to run",
    )
    parser.add_argument("--test", action="store_true", help="Test mode (triage: process first N only)")
    parser.add_argument("--workers", type=int, help="Number of concurrent GPT workers (triage)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without changes (populate)")

    args = parser.parse_args()
    config_path = args.config

    # Validate config exists
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    if args.step == "all":
        for step_name in ["triage", "populate", "generate", "deploy"]:
            print(f"\n{'#'*60}")
            print(f"  STEP: {step_name.upper()}")
            print(f"{'#'*60}")
            STEPS[step_name](config_path, args)
        print(f"\n{'='*60}")
        print("  All steps complete!")
        print(f"{'='*60}")
    else:
        STEPS[args.step](config_path, args)


if __name__ == "__main__":
    main()
