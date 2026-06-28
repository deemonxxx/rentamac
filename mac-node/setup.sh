#!/bin/bash
# ============================================================
# RentaMac — Baseline setup for Mac mini node
# Run once on each new Mac mini before joining the cluster.
#
# Usage: sudo ./setup.sh
# ============================================================
set -euo pipefail

echo "🔧 RentaMac Node Setup — starting..."

# ----------------------------------------------------------
# 1. DISABLE SLEEP (server must never sleep)
# ----------------------------------------------------------
echo "⏰ Disabling sleep..."
sudo pmset -a sleep 0 displaysleep 0 disksleep 0
sudo pmset -a womp 1           # Wake on LAN
sudo pmset -a autorestart 1    # Auto-restart after power loss
echo "  ✅ Sleep disabled, auto-restart enabled"

# ----------------------------------------------------------
# 2. ENABLE SSH
# ----------------------------------------------------------
echo "🔑 Enabling SSH..."
sudo systemsetup -setremotelogin on 2>/dev/null || true
echo "  ✅ SSH enabled"

# ----------------------------------------------------------
# 3. ENABLE VNC (Screen Sharing)
# ----------------------------------------------------------
echo "🖥  Enabling VNC / Screen Sharing..."
sudo /System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart \
  -activate -configure -access -on -users admin -privs -all -restart -agent
echo "  ✅ VNC enabled for user 'admin'"

# ----------------------------------------------------------
# 4. FIREWALL — allow ONLY VPN traffic
# ----------------------------------------------------------
echo "🛡  Configuring firewall (pfctl)..."

# Create anchor for RentaMac rules
sudo mkdir -p /etc/pf.anchors

cat > /tmp/com.rentamac.pf.rules << 'PF_RULES'
# =============================================
# RentaMac Firewall Rules
# Allow SSH + VNC ONLY from WireGuard VPN subnet
# Block everything else inbound
# =============================================

# --- Variables ---
vpn_net = "10.0.0.0/24"
gateway_ip = "89.125.30.138"

# --- Loopback ---
pass on lo0

# --- Allow WireGuard outbound (to gateway) ---
pass out on en0 proto udp to $gateway_ip port 51820

# --- Allow established connections ---
pass out all flags S/SA keep state

# --- Allow inbound ONLY from VPN ---
# SSH
pass in on utun* proto tcp from $vpn_net to any port 22 flags S/SA keep state

# VNC
pass in on utun* proto tcp from $vpn_net to any port 5900 flags S/SA keep state

# ICMP (ping) from VPN
pass in on utun* proto icmp from $vpn_net

# --- Block everything else inbound ---
block in all
PF_RULES

sudo cp /tmp/com.rentamac.pf.rules /etc/pf.anchors/com.rentamac

# Add anchor to main pf.conf if not already there
if ! grep -q "com.rentamac" /etc/pf.conf 2>/dev/null; then
  echo 'anchor "com.rentamac"' | sudo tee -a /etc/pf.conf > /dev/null
  echo 'load anchor "com.rentamac" from "/etc/pf.anchors/com.rentamac"' | sudo tee -a /etc/pf.conf > /dev/null
fi

# Enable pf
sudo pfctl -e 2>/dev/null || true
sudo pfctl -f /etc/pf.conf 2>/dev/null || true

echo "  ✅ Firewall configured — SSH/VNC only via VPN (10.0.0.0/24)"

# ----------------------------------------------------------
# 5. CREATE ADMIN USER (if not exists)
# ----------------------------------------------------------
if ! id admin &>/dev/null; then
  echo "👤 Creating admin user..."
  sudo sysadminctl -addUser admin -password - -admin -home /Users/admin -shell /bin/zsh
  echo "  ✅ User 'admin' created (set password manually)"
else
  echo "  ℹ️  User 'admin' already exists"
fi

# ----------------------------------------------------------
# 6. SETUP SSH KEY AUTH
# ----------------------------------------------------------
echo "🔐 Setting up SSH key auth..."
sudo mkdir -p /Users/admin/.ssh
# Gateway public key will be added during provisioning
sudo chmod 700 /Users/admin/.ssh
sudo chown admin:staff /Users/admin/.ssh
echo "  ✅ SSH directory ready (keys added during provisioning)"

# ----------------------------------------------------------
# 7. DISABLE PASSWORD AUTH (key-only)
# ----------------------------------------------------------
echo "🔒 Disabling SSH password authentication..."
sudo sed -i '' 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config 2>/dev/null || true
sudo sed -i '' 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config 2>/dev/null || true
echo "  ✅ SSH key-only authentication"

# ----------------------------------------------------------
# 8. INSTALL HOMEBREW (if not installed)
# ----------------------------------------------------------
if ! command -v brew &>/dev/null; then
  echo "🍺 Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  echo "  ✅ Homebrew installed"
else
  echo "  ℹ️  Homebrew already installed"
fi

# ----------------------------------------------------------
# 9. INSTALL WIREGUARD
# ----------------------------------------------------------
if ! command -v wg &>/dev/null; then
  echo "📡 Installing WireGuard..."
  brew install wireguard-tools
  echo "  ✅ WireGuard installed"
else
  echo "  ℹ️  WireGuard already installed"
fi

# ----------------------------------------------------------
# 10. SETUP WIREGUARD LAUNCHD DAEMON
# ----------------------------------------------------------
echo "🔄 Setting up WireGuard as launchd daemon..."
sudo mkdir -p /opt/wireguard

cat > /tmp/com.wireguard.wg0.plist << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wireguard.wg0</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/wg-quick</string>
        <string>up</string>
        <string>wg0</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/wireguard.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/wireguard.err</string>
</dict>
</plist>
PLIST

sudo cp /tmp/com.wireguard.wg0.plist /Library/LaunchDaemons/
echo "  ✅ WireGuard daemon configured (auto-start on boot)"

# ----------------------------------------------------------
# 11. ENABLE FIREWALL ON BOOT
# ----------------------------------------------------------
echo "🛡  Enabling firewall persistence..."
cat > /tmp/com.rentamac.pf.plist << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rentamac.pf</string>
    <key>ProgramArguments</key>
    <array>
        <string>/sbin/pfctl</string>
        <string>-e</string>
        <string>-f</string>
        <string>/etc/pf.conf</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
PLIST

sudo cp /tmp/com.rentamac.pf.plist /Library/LaunchDaemons/
echo "  ✅ Firewall enabled on boot"

# ----------------------------------------------------------
# DONE
# ----------------------------------------------------------
echo ""
echo "============================================================"
echo "✅ RentaMac Node Setup Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Transfer mac-mini-<N>.conf to this machine"
echo "  2. sudo cp mac-mini-<N>.conf /opt/wireguard/wg0.conf"
echo "  3. sudo launchctl load /Library/LaunchDaemons/com.wireguard.wg0.plist"
echo "  4. ping 10.0.0.1  (should reply)"
echo ""
echo "Firewall: SSH/VNC accessible ONLY from VPN (10.0.0.0/24)"
echo "Sleep: disabled | Auto-restart: enabled"
echo "============================================================"
