#!/bin/bash
set -e
echo "[1/3] Stopping WireGuard..."
sudo /opt/homebrew/bin/wg-quick down /opt/wireguard/wg0.conf 2>/dev/null || true
echo "[2/3] Writing pf.conf directly (no anchors)..."
sudo bash -c 'cat > /etc/pf.conf << PFEOF
pass in quick all
pass out all keep state
PFEOF'
echo "[3/3] Reloading firewall and starting WireGuard..."
sudo pfctl -d 2>/dev/null || true
sudo pfctl -e -f /etc/pf.conf
sudo /opt/homebrew/bin/wg-quick up /opt/wireguard/wg0.conf
echo "✅ Done!"
