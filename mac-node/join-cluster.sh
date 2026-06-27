#!/bin/bash
# join-cluster.sh — Join a macOS node to the WireGuard cluster
# Usage: sudo ./join-cluster.sh
set -euo pipefail

# Configuration — edit these
WG_IFACE="wg0"
WG_SUBNET="10.66.66.0/24"
GATEWAY_IP="${GATEWAY_IP:-89.125.30.138}"
GATEWAY_WG_PORT="${GATEWAY_WG_PORT:-51820}"
GATEWAY_WG_PUBKEY="${GATEWAY_WG_PUBLIC_KEY:?Set GATEWAY_WG_PUBLIC_KEY env var}"

echo "=== Joining WireGuard Cluster ==="

# Generate keys if not already present
WG_DIR="/etc/wireguard"
sudo mkdir -p "$WG_DIR"

if [ ! -f "$WG_DIR/privatekey" ]; then
    echo "Generating WireGuard key pair..."
    sudo wg genkey | sudo tee "$WG_DIR/privatekey" > /dev/null
    sudo chmod 600 "$WG_DIR/privatekey"
    sudo wg pubkey < "$WG_DIR/privatekey" | sudo tee "$WG_DIR/publickey" > /dev/null
fi

PRIVATE_KEY=$(sudo cat "$WG_DIR/privatekey")
PUBLIC_KEY=$(sudo cat "$WG_DIR/publickey")

echo "Node public key: $PUBLIC_KEY"
echo ""
echo ">>> Add this node on the gateway with: <<<"
echo "  wg set $WG_IFACE peer $PUBLIC_KEY allowed-ips <NODE_WG_IP>/32"
echo ""

# Prompt for this node's WireGuard IP
read -p "Enter this node's WireGuard IP (e.g., 10.66.66.10): " NODE_WG_IP
if [ -z "$NODE_WG_IP" ]; then
    echo "ERROR: Node WireGuard IP is required"
    exit 1
fi

# Write WireGuard config
sudo tee "$WG_DIR/$WG_IFACE.conf" > /dev/null << EOF
[Interface]
PrivateKey = $PRIVATE_KEY
Address = ${NODE_WG_IP}/24

[Peer]
PublicKey = $GATEWAY_WG_PUBKEY
Endpoint = ${GATEWAY_IP}:${GATEWAY_WG_PORT}
AllowedIPs = $WG_SUBNET
PersistentKeepalive = 25
EOF

sudo chmod 600 "$WG_DIR/$WG_IFACE.conf"

# Start WireGuard
echo "Starting WireGuard interface..."
sudo wg-quick down "$WG_IFACE" 2>/dev/null || true
sudo wg-quick up "$WG_IFACE"

# Verify connectivity
echo "Verifying connectivity to gateway..."
if ping -c 3 -t 5 "10.66.66.1" &>/dev/null; then
    echo "=== Connected to cluster successfully! ==="
else
    echo "WARNING: Could not ping gateway at 10.66.66.1"
    echo "Make sure this node's public key has been added to the gateway."
fi

echo ""
echo "WireGuard interface: $WG_IFACE"
echo "Node IP: $NODE_WG_IP"
echo "Gateway: $GATEWAY_IP:$GATEWAY_WG_PORT"