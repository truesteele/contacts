#!/bin/bash
# Daily sync of email, calendar, SMS + call data with contacts
# Scheduled via launchd at 8am PT daily
#
# Email: checks last 3 days of Gmail threads across 5 accounts
# Calendar: checks last 7 days of events across 5 accounts
# SMS + Calls: downloads latest backup from Google Drive, processes incrementally

set -euo pipefail

cd /Users/Justin/Code/TrueSteele/contacts
source .venv/bin/activate
# Safe .env loader — handles special chars in values (<, >, #, spaces, dots in keys)
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  [[ "$line" != *=* ]] && continue
  key="${line%%=*}"
  # Skip invalid bash identifiers (e.g. AZURE_5.1_MINI_ENDPOINT)
  [[ ! "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] && continue
  value="${line#*=}"
  # Strip surrounding double quotes if present
  if [[ "$value" =~ ^\"(.*)\"$ ]]; then
    value="${BASH_REMATCH[1]}"
  fi
  export "$key=$value"
done < .env

DATE=$(date +%Y-%m-%d)
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/daily_sync_${DATE}.log"

echo "=== Daily Contact Sync — $DATE ===" >> "$LOG"

# Email: collect threads from last 3 days (covers weekend gaps)
echo "[$(date)] Starting email sync (--recent-days 3, --collect-only)..." >> "$LOG"
python -u scripts/intelligence/gather_comms_history.py --recent-days 3 --collect-only >> "$LOG" 2>&1 || true

# Calendar: collect events from last 7 days
echo "[$(date)] Starting calendar sync (--recent-days 7, --collect-only)..." >> "$LOG"
python -u scripts/intelligence/gather_calendar_meetings.py --recent-days 7 --collect-only >> "$LOG" 2>&1 || true

# SMS + Calls: download latest backup from Drive, process incrementally
echo "[$(date)] Starting phone backup sync (SMS + calls)..." >> "$LOG"
python -u scripts/intelligence/sync_phone_backup.py >> "$LOG" 2>&1 || true

# Deal activities: tag recent comms to active deals
echo "[$(date)] Syncing deal activities (--recent-days 7)..." >> "$LOG"
python -u scripts/intelligence/sync_deal_activities.py --recent-days 7 >> "$LOG" 2>&1 || true

echo "[$(date)] Sync complete." >> "$LOG"

# Clean up logs older than 30 days
find "$LOG_DIR" -name "daily_sync_*.log" -mtime +30 -delete 2>/dev/null || true
