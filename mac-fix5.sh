#!/bin/bash
set -e
printf 'pass in quick all\npass out all keep state\n' | sudo tee /etc/pf.anchors/com.rentamac
sudo pfctl -f /etc/pf.conf
sudo /opt/homebrew/bin/wg-quick down /opt/wireguard/wg0.conf 2>/dev/null || true
sudo /opt/homebrew/bin/wg-quick up /opt/wireguard/wg0.conf
echo "✅ Firewall wide open, WG restarted"
