#!/usr/bin/env bash
# Install Reality Check as a login agent (starts silently at login, restarts if it dies).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
APP="$ROOT/app"
LABEL="com.realitycheck.agent"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
ELECTRON="$APP/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron"
LOG="$ROOT/agent.log"

if [ ! -x "$ELECTRON" ]; then
  echo "Electron binary not found at $ELECTRON. Run 'npm install' in $APP first." >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>            <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$ELECTRON</string>
    <string>$APP</string>
  </array>
  <key>RunAtLoad</key>        <true/>
  <key>KeepAlive</key>        <true/>
  <key>StandardOutPath</key>  <string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
PLIST_EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Installed + started: $LABEL"
echo "First time you open a watched site, macOS will ask to let it control Chrome -> click Allow."
echo "Log: $LOG"
