#!/bin/bash
# RentaMac — Fix WireGuard tunnel
# Run: curl -sL http://89.125.30.138:9999/mac-fix.sh | bash

set -euo pipefail

echo "🔧 Fixing WireGuard tunnel..."

# 1. Stop tunnel
echo "[1/5] Stopping current tunnel..."
sudo /opt/homebrew/bin/wg-quick down /opt/wireguard/wg0.conf 2>/dev/null || true

# 2. Fix firewall rules
echo "[2/5] Fixing firewall rules..."
sudo bash -c 'cat > /etc/pf.anchors/com.rentamac << PF
vpn_net = "10.0.0.0/24"
gateway_ip = "89.125.30.138"
pass on lo0
pass in on en0 proto udp from \$gateway_ip port 51820
pass out on en0 proto udp to \$gateway_ip port 51820
pass out all flags S/SA keep state
pass in on utun* proto tcp from \$vpn_net to any port 22 flags S/SA keep state
pass in on utun* proto tcp from \$vpn_net to any port 5900 flags S/SA keep state
pass in on utun* proto icmp from \$vpn_net
block in all
PF'

# 3. Reload firewall
echo "[3/5] Reloading firewall..."
sudo pfctl -e -f /etc/pf.conf 2>/dev/null || true

# 4. Start tunnel
echo "[4/5] Starting WireGuard..."
sudo /opt/homebrew/bin/wg-quick up /opt/wireguard/wg0.conf

# 5. Verify
echo "[5/5] Verifying..."
sleep 3
if ping -c 3 -t 5 10.0.0.1 &>/dev/null; then
  echo ""
  echo "============================================================"
  echo "✅ SUCCESS! Tunnel is stable"
  echo "   Mac IP (VPN): 10.0.0.10"
  echo "   Gateway IP:   10.0.0.1"
  echo "============================================================"
  echo ""
  echo "Сообщи мне что всё работает — я проверю с сервера."
else
  echo ""
  echo "⚠️  Пинг не проходит. Попробуй:"
  echo "   ping -c 5 10.0.0.1"
  echo ""
  echo "Логи WireGuard:"
  echo "   cat /var/log/wireguard.err"
  echo ""
  echo "Статус:"
  echo "   sudo wg show"
fi