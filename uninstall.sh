#!/usr/bin/env bash
# Stop + remove the login agent. Leaves the folder/clips intact.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.realitycheck.agent"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
pkill -f "$ROOT/app" 2>/dev/null || true
echo "Reality Check stopped + autostart removed. (Your clips are left in place.)"
