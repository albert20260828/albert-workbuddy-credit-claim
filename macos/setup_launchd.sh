#!/usr/bin/env bash
# Manage the macOS launchd timer for daily check-in.
#
# Usage:
#   bash setup_launchd.sh install [HH:MM,HH:MM]   # install (default 11:00,20:00)
#   bash setup_launchd.sh status                  # show registration + last run
#   bash setup_launchd.sh run                     # trigger once via launchd
#   bash setup_launchd.sh remove                  # uninstall
set -u

SK="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.albert.workbuddy.dailycheckin"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
TIMES="${WORKBUDDY_CHECKIN_TIMES:-11:00,20:00}"

case "${1:-help}" in
  install)
    [ $# -ge 2 ] && TIMES="$2"
    IFS=',' read -ra ARR <<< "$TIMES"
    ENTRIES=""
    for t in "${ARR[@]}"; do
      hh="${t%%:*}"; mm="${t##*:}"
      ENTRIES="${ENTRIES}    <dict><key>Hour</key><integer>${hh}</integer><key>Minute</key><integer>${mm}</integer></dict>"$'\n'
    done
    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${SK}/macos/checkin.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
${ENTRIES}  </array>
  <key>StandardOutPath</key><string>${SK}/logs/launchd.out.log</string>
  <key>StandardErrorPath</key><string>${SK}/logs/launchd.err.log</string>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
PL
    echo "plist written: $PLIST"
    if launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null; then
      echo "loaded. verify with: bash $0 status"
    else
      echo "bootstrap returned non-zero (often EIO inside a sandboxed shell)."
      echo "The plist is in place and will auto-load on next login/restart."
      echo "To activate now, run in Terminal.app:"
      echo "  launchctl bootstrap gui/$(id -u) '$PLIST'"
    fi
    ;;
  status)
    launchctl list | grep -i "$LABEL" || echo "not currently loaded"
    echo "--- plist exists: $([ -f "$PLIST" ] && echo yes || echo no)"
    echo "--- recent run.log:"; tail -5 "$SK/logs/run.log" 2>/dev/null || echo "(no log yet)"
    ;;
  run)
    if launchctl kickstart "gui/$(id -u)/${LABEL}" 2>/dev/null; then
      echo "kickstarted"
    else
      echo "kickstart failed; running directly instead:"
      bash "$SK/macos/checkin.sh"
    fi
    ;;
  remove)
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null
    rm -f "$PLIST"
    echo "removed"
    ;;
  *)
    echo "usage: $0 {install [HH:MM,HH:MM]|status|run|remove}"
    ;;
esac
