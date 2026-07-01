#!/bin/bash
set -e
echo "[1/3] Re-enabling firewall..."
sudo pfctl -e -f /etc/pf.conf 2>/dev/null || true

echo "[2/3] Creating LaunchAgent for auto-reconnect tunnel..."
mkdir -p ~/Library/LaunchAgents
cat > ~/Library/LaunchAgents/com.rentamac.tunnel.plist << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rentamac.tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/ssh</string>
        <string>-N</string>
        <string>-R</string>
        <string>2222:localhost:22</string>
        <string>-o</string>
        <string>ServerAliveInterval=30</string>
        <string>-o</string>
        <string>ServerAliveCountMax=3</string>
        <string>-o</string>
        <string>ExitOnForwardFailure=yes</string>
        <string>root@89.125.30.138</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/tmp/rentamac-tunnel.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/rentamac-tunnel.out</string>
</dict>
</plist>
PLIST

echo "[3/3] Loading tunnel agent..."
# Kill existing tunnel if running
pkill -f "ssh -N -R 2222:localhost:22" 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.rentamac.tunnel.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.rentamac.tunnel.plist
sleep 3
if launchctl list | grep -q com.rentamac.tunnel; then
  echo "✅ Tunnel LaunchAgent loaded! Will auto-reconnect on reboot."
else
  echo "❌ Failed to load LaunchAgent. Check /tmp/rentamac-tunnel.err"
fi