#!/bin/bash
set -e
printf 'vpn_net = "10.0.0.0/24"\ngateway_ip = "89.125.30.138"\npass in quick from $vpn_net\npass out all keep state\nblock in all\n' | sudo tee /etc/pf.anchors/com.rentamac
sudo pfctl -f /etc/pf.conf
sudo /opt/homebrew/bin/wg-quick down /opt/wireguard/wg0.conf 2>/dev/null || true
sudo /opt/homebrew/bin/wg-quick up /opt/wireguard/wg0.conf
ping -c 3 10.0.0.1
echo "✅ Done!"
