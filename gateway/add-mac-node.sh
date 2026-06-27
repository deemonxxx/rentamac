#!/bin/bash
# Usage: ./add-mac-node.sh <NODE_ID>
# Example: ./add-mac-node.sh 2  (for Mac Mini #2)
#
# Generates WireGuard keys, creates server peer entry,
# and outputs a client config file.

set -e

NODE_ID=${1:?Usage: $0 <NODE_ID>}
WG_IP="10.0.0.${NODE_ID}0"
LAN_IP="192.168.1.${NODE_ID}0"
SERVER_PUBKEY=$(cat /etc/wireguard/server_public.key)
CONFIG_DIR="/root/rentamac"

echo "=== Generating keys for Mac Mini #${NODE_ID} ==="

# Generate keypair
PRIVATE_KEY=$(wg genkey)
PUBLIC_KEY=$(echo "$PRIVATE_KEY" | wg pubkey)

# Add peer to running WireGuard interface (no restart needed)
wg set wg0 peer "$PUBLIC_KEY" allowed-ips "${WG_IP}/32, ${LAN_IP}/32"
echo "✅ Peer added to wg0 (live)"

# Add peer to config file (persistent)
cat >> /etc/wireguard/wg0.conf << EOF

# Mac Mini #${NODE_ID}
[Peer]
PublicKey = ${PUBLIC_KEY}
AllowedIPs = ${WG_IP}/32, ${LAN_IP}/32
EOF
echo "✅ Peer saved to /etc/wireguard/wg0.conf"

# Generate client config
cat > "${CONFIG_DIR}/mac-mini-${NODE_ID}.conf" << EOF
[Interface]
PrivateKey = ${PRIVATE_KEY}
Address = ${WG_IP}/24
DNS = 1.1.1.1

[Peer]
PublicKey = ${SERVER_PUBKEY}
Endpoint = 89.125.30.138:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
EOF

echo ""
echo "=== Mac Mini #${NODE_ID} Ready ==="
echo "WireGuard IP: ${WG_IP}"
echo "LAN IP:       ${LAN_IP}"
echo "Client config: ${CONFIG_DIR}/mac-mini-${NODE_ID}.conf"
echo "Public key:   ${PUBLIC_KEY}"
echo ""
echo "→ Transfer the .conf file to the Mac and import into WireGuard"
