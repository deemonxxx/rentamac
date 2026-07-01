#!/bin/bash
set -e
echo "=== Fixing pf.conf ==="
sudo bash -c 'cat > /etc/pf.conf << PFMAIN
scrub-anchor "com.rentamac"
anchor "com.rentamac"
load anchor "com.rentamac" from "/etc/pf.anchors/com.rentamac"
PFMAIN'
sudo bash -c 'cat > /etc/pf.anchors/com.rentamac << PFANCHOR
pass in quick all
pass out all keep state
PFANCHOR'
sudo pfctl -d 2>/dev/null || true
sudo pfctl -e -f /etc/pf.conf
echo "=== Restarting WireGuard ==="
sudo /opt/homebrew/bin/wg-quick down /opt/wireguard/wg0.conf 2>/dev/null || true
sudo /opt/homebrew/bin/wg-quick up /opt/wireguard/wg0.conf
echo "=== Testing ==="
ping -c 3 10.0.0.1
echo "✅ Done!"
