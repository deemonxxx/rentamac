#!/bin/bash
# RentaMac — Fix firewall (allow all VPN traffic)
# Run: curl -sL http://89.125.30.138:9999/mac-fix2.sh -o /tmp/f.sh && bash /tmp/f.sh

set -euo pipefail

echo "🔧 Fixing firewall..."

# Fix rules: pass in quick from vpn_net (all traffic, any interface)
sudo bash -c 'cat > /etc/pf.anchors/com.rentamac << PF
vpn_net = "10.0.0.0/24"
gateway_ip = "89.125.30.138"
pass on lo0
pass in on en0 proto udp from \$gateway_ip port 51820
pass out on en0 proto udp to \$gateway_ip port 51820
pass out all keep state
pass in quick from \$vpn_net
block in all
PF'

sudo pfctl -e -f /etc/pf.conf 2>/dev/null || true

echo "✅ Firewall updated — all VPN traffic allowed"
echo ""
echo "Сообщи мне что обновил — я проверю SSH и ping с сервера."
