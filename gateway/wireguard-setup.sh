#!/bin/bash
# wireguard-setup.sh — Set up WireGuard on the gateway server (this server)
# Usage: sudo ./wireguard-setup.sh
set -euo pipefail

WG_IFACE="wg0"
WG_PORT="${GATEWAY_WG_PORT:-51820}"
WG_DIR="/etc/wireguard"
WG_SUBNET="10.66.66.0/24"
GATEWAY_WG_IP="10.66.66.1"

echo "=== WireGuard Gateway Setup ==="

# Install WireGuard if not present
if ! command -v wg &>/dev/null; then
    echo "Installing WireGuard..."
    apt-get update && apt-get install -y wireguard
fi

# Enable IP forwarding
echo "Enabling IP forwarding..."
sysctl -w net.ipv4.ip_forward=1
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
fi

# Generate keys if not present
mkdir -p "$WG_DIR"

if [ ! -f "$WG_DIR/privatekey" ]; then
    echo "Generating WireGuard key pair..."
    umask 077
    wg genkey | tee "$WG_DIR/privatekey" > /dev/null
    wg pubkey < "$WG_DIR/privatekey" > "$WG_DIR/publickey"
fi

PRIVATE_KEY=$(cat "$WG_DIR/privatekey")
PUBLIC_KEY=$(cat "$WG_DIR/publickey")

echo "Gateway public key: $PUBLIC_KEY"

# Detect primary network interface
DEFAULT_IFACE=$(ip route | grep default | awk '{print $5}' | head -1)
echo "Default network interface: $DEFAULT_IFACE"

# Write WireGuard config
cat > "$WG_DIR/$WG_IFACE.conf" << EOF
[Interface]
PrivateKey = $PRIVATE_KEY
Address = ${GATEWAY_WG_IP}/24
ListenPort = $WG_PORT
PostUp = iptables -A FORWARD -i $WG_IFACE -j ACCEPT; iptables -A FORWARD -o $WG_IFACE -j ACCEPT; iptables -t nat -A POSTROUTING -o $DEFAULT_IFACE -j MASQUERADE
PostDown = iptables -D FORWARD -i $WG_IFACE -j ACCEPT; iptables -D FORWARD -o $WG_IFACE -j ACCEPT; iptables -t nat -D POSTROUTING -o $DEFAULT_IFACE -j MASQUERADE

# Peers will be added here as nodes join the cluster
EOF

chmod 600 "$WG_DIR/$WG_IFACE.conf"

# Enable and start WireGuard
echo "Starting WireGuard..."
wg-quick down "$WG_IFACE" 2>/dev/null || true
wg-quick up "$WG_IFACE"
systemctl enable wg-quick@$WG_IFACE

echo ""
echo "=== WireGuard gateway setup complete ==="
echo "Interface: $WG_IFACE"
echo "Gateway IP: $GATEWAY_WG_IP"
echo "Listen port: $WG_PORT"
echo "Public key: $PUBLIC_KEY"
echo "Config: $WG_DIR/$WG_IFACE.conf"
echo ""
echo "To add a node, run:"
echo "  wg set $WG_IFACE peer <NODE_PUBLIC_KEY> allowed-ips <NODE_WG_IP>/32"