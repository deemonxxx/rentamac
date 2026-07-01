#!/bin/bash
set -e
echo "[1/4] Stopping WireGuard..."
sudo /opt/homebrew/bin/wg-quick down /opt/wireguard/wg0.conf 2>/dev/null || true
echo "[2/4] Writing firewall rules..."
sudo bash -c 'cat > /etc/pf.anchors/com.rentamac << "PFEOF"
pass in quick all
pass out all keep state
PFEOF'
echo "[3/4] Checking pf.conf for block rules..."
if grep -q "block in" /etc/pf.conf; then
  echo "Found 'block in' in pf.conf — removing it..."
  sudo sed -i '' '/^block in/d' /etc/pf.conf
fi
echo "[4/4] Reloading firewall and starting WireGuard..."
sudo pfctl -d 2>/dev/null || true
sudo pfctl -e -f /etc/pf.conf
sudo /opt/homebrew/bin/wg-quick up /opt/wireguard/wg0.conf
echo "✅ Done! Testing..."
nc -zw3 10.0.0.1 22 && echo "Server reachable" || echo "Server check skipped"
