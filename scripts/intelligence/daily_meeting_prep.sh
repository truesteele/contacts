#!/bin/bash
# Daily meeting prep memo generation (launchd entrypoint)

set -euo pipefail

PROJECT_ROOT="/Users/Justin/Code/TrueSteele/contacts"
LOG_DIR="$PROJECT_ROOT/logs"
DATE=$(date +%Y-%m-%d)
LOG="$LOG_DIR/meeting_prep_${DATE}.log"
LOCK_DIR="/tmp/co.truesteele.meeting-prep.lock"

mkdir -p "$LOG_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[$(date)] Another meeting prep run is already in progress. Exiting." >> "$LOG"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

cd "$PROJECT_ROOT"

if [[ -x ".venv/bin/python3" ]]; then
  PYTHON_BIN=".venv/bin/python3"
elif [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="python3"
fi

echo "=== Daily Meeting Prep — $DATE ===" >> "$LOG"
echo "[$(date)] Starting meeting prep generation..." >> "$LOG"

if "$PYTHON_BIN" -u scripts/intelligence/daily_meeting_prep.py >> "$LOG" 2>&1; then
  echo "[$(date)] Meeting prep complete." >> "$LOG"
else
  STATUS=$?
  echo "[$(date)] Meeting prep FAILED (exit $STATUS)." >> "$LOG"
  exit "$STATUS"
fi

# Clean up logs older than 30 days
find "$LOG_DIR" -name "meeting_prep_*.log" -mtime +30 -delete 2>/dev/null || true
