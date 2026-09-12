#!/usr/bin/env bash
# Entry point for the macOS daily check-in.
# Locates the engine, runs it (idempotent), and appends output to run.log.
#
# Usage:
#   bash checkin.sh              # check in now
#   bash checkin.sh --dry-run    # probe only, no actual claim
set -u

SK="$(cd "$(dirname "$0")/.." && pwd)"

ENGINE=""
for cand in "$SK/macos/workbuddy_daily_checkin.py" "$SK/scripts/claim_api.py"; do
  [ -f "$cand" ] && ENGINE="$cand" && break
done
# Fallback: any installed skill that ships the engine (original design).
if [ -z "$ENGINE" ]; then
  ENGINE="$(ls "$HOME/.workbuddy/skills"/*/scripts/workbuddy_daily_checkin.py 2>/dev/null | head -1)"
fi
if [ -z "$ENGINE" ]; then
  echo "config_error: engine (workbuddy_daily_checkin.py) not found"
  exit 2
fi

PY="${WORKBUDDY_CHECKIN_PYTHON:-/usr/bin/python3}"
LOG_DIR="$SK/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/run.log"

"$PY" "$ENGINE" "$@" 2>&1 | tee -a "$LOG"
exit "${PIPESTATUS[0]}"
