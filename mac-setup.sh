#!/bin/bash
# RentaMac — Mac Mini Full Setup
# Run WITHOUT sudo first:
#   curl -sL http://89.125.30.138:9999/mac-setup.sh | bash
# The script will ask for sudo password when needed.

set -euo pipefail

echo "🔧 RentaMac Node Setup — starting..."
echo ""

# --- Steps that need sudo ---
echo "[1/7] Disabling sleep..."
sudo pmset -a sleep 0 displaysleep 0 disksleep 0
sudo pmset -a womp 1 autorestart 1
echo "  ✅ Sleep off, auto-restart on"

echo "[2/7] Configuring firewall..."
sudo bash -c 'cat > /etc/pf.anchors/com.rentamac << PF
vpn_net = "10.0.0.0/24"
gateway_ip = "89.125.30.138"
pass on lo0
pass out on en0 proto udp to \$gateway_ip port 51820
pass out all flags S/SA keep state
pass in on utun* proto tcp from \$vpn_net to any port 22 flags S/SA keep state
pass in on utun* proto tcp from \$vpn_net to any port 5900 flags S/SA keep state
pass in on utun* proto icmp from \$vpn_net
block in all
PF'

if ! grep -q "com.rentamac" /etc/pf.conf 2>/dev/null; then
  echo 'anchor "com.rentamac"' | sudo tee -a /etc/pf.conf > /dev/null
  echo 'load anchor "com.rentamac" from "/etc/pf.anchors/com.rentamac"' | sudo tee -a /etc/pf.conf > /dev/null
fi
sudo pfctl -e -f /etc/pf.conf 2>/dev/null || true
echo "  ✅ Firewall: SSH/VNC only via VPN"

echo "[3/7] Hardening SSH..."
sudo sed -i '' 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config 2>/dev/null || true
sudo sed -i '' 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config 2>/dev/null || true
echo "  ✅ SSH key-only"

# --- Homebrew (must be installed as regular user, NOT root) ---
echo "[4/7] Installing Homebrew..."
if ! command -v brew &>/dev/null; then
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Add brew to PATH for this session
  if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
  elif [ -f /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
  echo "  ✅ Homebrew installed"
else
  echo "  ℹ️  Homebrew already installed"
fi

# --- WireGuard ---
echo "[5/7] Installing WireGuard..."
brew install wireguard-tools
echo "  ✅ WireGuard installed"

# --- WireGuard config (needs sudo) ---
echo "[6/7] Setting up WireGuard tunnel..."
sudo mkdir -p /opt/wireguard
sudo bash -c 'cat > /opt/wireguard/wg0.conf << WGEOF
[Interface]
PrivateKey = aMIauGmvvHpU2pY5w6EDJR/VBcN12ICpsVTKvH09lGY=
Address = 10.0.0.10/24
DNS = 1.1.1.1

[Peer]
PublicKey = N6qJKDol7tpSOdeiIcwgS8s8sGL5XQv3eYMvsr3oZH0=
Endpoint = 89.125.30.138:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
WGEOF'

# Find wg-quick path
WG_QUICK=$(which wg-quick)
if [ -z "$WG_QUICK" ]; then
  WG_QUICK="/opt/homebrew/bin/wg-quick"
fi

sudo bash -c "cat > /Library/LaunchDaemons/com.wireguard.wg0.plist << PLISTEOF
<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
    <key>Label</key><string>com.wireguard.wg0</string>
    <key>ProgramArguments</key>
    <array>
        <string>${WG_QUICK}</string>
        <string>up</string>
        <string>/opt/wireguard/wg0.conf</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>/var/log/wireguard.log</string>
    <key>StandardErrorPath</key><string>/var/log/wireguard.err</string>
</dict>
</plist>
PLISTEOF"

# Unload first if already loaded
sudo launchctl unload /Library/LaunchDaemons/com.wireguard.wg0.plist 2>/dev/null || true
sudo launchctl load /Library/LaunchDaemons/com.wireguard.wg0.plist
echo "  ✅ WireGuard daemon started"

# --- Verify ---
echo "[7/7] Verifying tunnel..."
sleep 4
if ping -c 2 -t 5 10.0.0.1 &>/dev/null; then
  echo ""
  echo "============================================================"
  echo "✅ SUCCESS! Tunnel to Gateway is UP"
  echo "   Mac IP (VPN): 10.0.0.10"
  echo "   Gateway IP:   10.0.0.1"
  echo "============================================================"
  echo ""
  echo "Сообщи мне что туннель работает — я проверю с сервера."
else
  echo ""
  echo "⚠️  Туннель пока не отвечает. Подожди 15 секунд и попробуй:"
  echo "   ping 10.0.0.1"
  echo ""
  echo "Если не работает — проверь логи:"
  echo "   cat /var/log/wireguard.err"
fi
