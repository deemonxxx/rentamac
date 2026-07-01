#!/bin/bash
set -e
echo "[1/2] Disabling pf completely..."
sudo pfctl -d
echo "[2/2] Restarting WireGuard..."
sudo /opt/homebrew/bin/wg-quick down /opt/wireguard/wg0.conf 2>/dev/null || true
sudo /opt/homebrew/bin/wg-quick up /opt/wireguard/wg0.conf
echo "✅ pf disabled, WG restarted. Test SSH now."
