#!/bin/bash
# Ralph Wiggum - Autonomous AI Coding Loop
# Communication Closeness Scoring
# Usage: ./ralph.sh [max_iterations]
#
# This script runs Claude Code in a loop, with each iteration getting
# a fresh context window. Progress is tracked via prd.md and progress.txt.

set -Eeuo pipefail

# Configuration
MAX_ITERATIONS="${1:-10}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.md"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
PROMPT_FILE="$SCRIPT_DIR/RALPH_PROMPT.md"
LOG_DIR="${RALPH_LOG_DIR:-$SCRIPT_DIR/logs}"
COMPLETE_TOKEN="${RALPH_COMPLETE_TOKEN:-<promise>COMPLETE</promise>}"
SLEEP_SECONDS="${RALPH_SLEEP_SECONDS:-2}"
ALLOW_DANGEROUS="${RALPH_ALLOW_DANGEROUS:-0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

die() {
  echo -e "${RED}Error: $*${NC}" >&2
  exit 1
}

# Validate dependencies
command -v claude >/dev/null 2>&1 || die "claude CLI not found. Install it or ensure it is on PATH."

# Validate max iterations
if ! [[ "$MAX_ITERATIONS" =~ ^[0-9]+$ ]] || [ "$MAX_ITERATIONS" -lt 1 ]; then
  die "Max iterations must be a positive integer."
fi

# Prevent concurrent runs for the same loop
LOCK_DIR="$SCRIPT_DIR/.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  die "Lock exists at $LOCK_DIR. Another Ralph loop may be running. Remove it if stale."
fi
echo "$$" > "$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT INT TERM

mkdir -p "$LOG_DIR"

# Initialize progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
  {
    echo "# Ralph Progress Log"
    echo "Loop: $(basename "$SCRIPT_DIR")"
    echo "Started: $(date)"
    echo "---"
    echo ""
  } > "$PROGRESS_FILE"
fi

# Check required files exist
[ -f "$PRD_FILE" ] || die "prd.md not found at $PRD_FILE"
[ -f "$PROMPT_FILE" ] || die "RALPH_PROMPT.md not found at $PROMPT_FILE"

# Warn if git working tree is dirty
if command -v git >/dev/null 2>&1 && git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [ -n "$(git -C "$SCRIPT_DIR" status --porcelain)" ]; then
    echo -e "${YELLOW}Warning: git working tree has uncommitted changes.${NC}"
  fi
fi

# Exit early if no incomplete stories
if ! grep -q "\[ \]" "$PRD_FILE"; then
  echo -e "${GREEN}No incomplete stories found. Exiting.${NC}"
  exit 0
fi

if [ "$ALLOW_DANGEROUS" = "1" ]; then
  CLAUDE_ARGS=(--dangerously-skip-permissions --print)
else
  CLAUDE_ARGS=(--print)
  echo -e "${YELLOW}Warning: running without --dangerously-skip-permissions.${NC}"
  echo -e "${YELLOW}Set RALPH_ALLOW_DANGEROUS=1 for unattended runs.${NC}"
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RALPH WIGGUM - Communication Closeness Scoring            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Max iterations: $MAX_ITERATIONS${NC}"
echo -e "${YELLOW}PRD file: $PRD_FILE${NC}"
echo -e "${YELLOW}Progress file: $PROGRESS_FILE${NC}"
echo -e "${YELLOW}Log dir: $LOG_DIR${NC}"
echo -e "${YELLOW}Completion token: $COMPLETE_TOKEN${NC}"
echo ""

for ((i=1; i<=MAX_ITERATIONS; i++)); do
  echo ""
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo -e "${GREEN}  Ralph Iteration $i of $MAX_ITERATIONS${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo ""

  ITERATION_LOG="$LOG_DIR/iteration-${i}-$(date +%Y%m%d-%H%M%S).log"

  # Run Claude Code with the prompt file
  # --print outputs to stdout for capture
  # < redirects the prompt file as input
  set +e
  claude "${CLAUDE_ARGS[@]}" < "$PROMPT_FILE" 2>&1 | tee "$ITERATION_LOG"
  CLAUDE_STATUS=${PIPESTATUS[0]}
  set -e

  if [ "$CLAUDE_STATUS" -ne 0 ]; then
    echo -e "${YELLOW}Claude exited with status $CLAUDE_STATUS. See $ITERATION_LOG${NC}"
  fi

  # Check for completion signal and verify PRD is done
  if grep -qF "$COMPLETE_TOKEN" "$ITERATION_LOG"; then
    if grep -q "\[ \]" "$PRD_FILE"; then
      echo -e "${YELLOW}Completion token found but incomplete stories remain. Continuing...${NC}"
    else
      echo ""
      echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
      echo -e "${GREEN}║           RALPH COMPLETED ALL TASKS!                       ║${NC}"
      echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
      echo ""
      echo -e "Completed at iteration $i of $MAX_ITERATIONS"
      echo ""

      # macOS notification
      osascript -e 'display notification "Comms Closeness Scoring complete!" with title "Ralph"' 2>/dev/null || true

      # Log completion to progress file
      echo "" >> "$PROGRESS_FILE"
      echo "---" >> "$PROGRESS_FILE"
      echo "## COMPLETED" >> "$PROGRESS_FILE"
      echo "Finished at: $(date)" >> "$PROGRESS_FILE"
      echo "Total iterations: $i" >> "$PROGRESS_FILE"

      exit 0
    fi
  fi

  echo ""
  echo -e "${YELLOW}Iteration $i complete. Continuing to next iteration...${NC}"
  sleep "$SLEEP_SECONDS"
done

echo ""
echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║     Ralph reached max iterations without completing        ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Check $PROGRESS_FILE for current status."
echo "Run again with more iterations: ./ralph.sh $((MAX_ITERATIONS + 10))"
exit 1
