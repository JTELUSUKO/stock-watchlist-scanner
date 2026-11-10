#!/usr/bin/env bash
# Install the weekday launchd job for wherever this project lives.
# Usage: scripts/install-schedule.sh [HH:MM]   (local time, default 09:00)
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.stockwatchlist.scanner"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
WHEN="${1:-09:00}"

if [[ ! "$WHEN" =~ ^([01]?[0-9]|2[0-3]):([0-5][0-9])$ ]]; then
  echo "Time must be HH:MM, got: $WHEN" >&2
  exit 2
fi
HOUR=$((10#${BASH_REMATCH[1]}))
MINUTE=$((10#${BASH_REMATCH[2]}))

# macOS doesn't let launchd jobs read these folders, so the job would fail every morning.
case "$PROJECT_ROOT" in
  "$HOME/Desktop"/*|"$HOME/Documents"/*|"$HOME/Downloads"/*)
    echo "This project is in a folder macOS protects from scheduled jobs:" >&2
    echo "  $PROJECT_ROOT" >&2
    echo "Move it somewhere else (for example ~/my-project) and run this again." >&2
    exit 1
    ;;
esac

mkdir -p "$PROJECT_ROOT/logs" "$(dirname "$TARGET")"
sed -e "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" \
    -e "s|__HOUR__|$HOUR|g" \
    -e "s|__MINUTE__|$MINUTE|g" \
    "$PROJECT_ROOT/com.stockwatchlist.scanner.plist" > "$TARGET"
plutil -lint "$TARGET" > /dev/null

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$TARGET"

printf 'Installed %s: weekdays at %02d:%02d local time.\n' "$LABEL" "$HOUR" "$MINUTE"
echo "Reports go to $PROJECT_ROOT/logs/scanner.log"
