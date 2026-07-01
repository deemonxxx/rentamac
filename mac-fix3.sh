#!/bin/bash
set -e
echo "[1/2] Fixing firewall..."
sudo bash -c 'cat > /etc/pf.anchors/com.rentamac << PF
vpn_net = "10.0.0.0/24"
gateway_ip = "89.125.30.138"
pass on lo0
pass in on en0 proto udp from \$gateway_ip port 51820
pass out on en0 proto udp to \$gateway_ip port 51820
pass out all keep state
pass in on utun* from \$vpn_net
block in all
PF'
sudo pfctl -f /etc/pf.conf
echo "[2/2] Restarting WireGuard..."
sudo /opt/homebrew/bin/wg-quick down /opt/wireguard/wg0.conf 2>/dev/null || true
sudo /opt/homebrew/bin/wg-quick up /opt/wireguard/wg0.conf
echo "Testing..."
ping -c 3 10.0.0.1
echo "✅ Done!"
