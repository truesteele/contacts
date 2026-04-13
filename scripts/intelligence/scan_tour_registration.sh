#!/bin/bash
# Daily scan of college tour registration portals
# Scheduled via launchd at 7am PT daily
#
# Checks 6 school portals with Playwright, emails when dates become bookable.
# Self-expires after June 6, 2026.

set -euo pipefail

cd /Users/Justin/Code/TrueSteele/contacts
source .venv/bin/activate
# Safe .env loader — handles special chars in values
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  [[ "$line" != *=* ]] && continue
  key="${line%%=*}"
  [[ ! "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] && continue
  value="${line#*=}"
  if [[ "$value" =~ ^\"(.*)\"$ ]]; then
    value="${BASH_REMATCH[1]}"
  fi
  export "$key=$value"
done < .env

DATE=$(date +%Y-%m-%d)
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/tour_scan_${DATE}.log"

echo "=== Tour Registration Scan — $DATE ===" >> "$LOG"
echo "[$(date)] Starting tour portal scan..." >> "$LOG"
python -u scripts/intelligence/scan_tour_registration.py >> "$LOG" 2>&1 || true
echo "[$(date)] Scan complete." >> "$LOG"

# Clean up logs older than 30 days
find "$LOG_DIR" -name "tour_scan_*.log" -mtime +30 -delete 2>/dev/null || true
