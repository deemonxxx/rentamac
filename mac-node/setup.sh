#!/bin/bash
# setup.sh — Baseline macOS setup for a new RentaMac node
# Run as admin user with sudo privileges
set -euo pipefail

echo "=== RentaMac Node Setup ==="

# Install Homebrew if not present
if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install WireGuard
echo "Installing WireGuard..."
brew install wireguard-tools

# Install OpenSSH server (macOS has it built-in, ensure it's enabled)
echo "Enabling Remote Login..."
sudo systemsetup -setremotelogin on

# Configure firewall
echo "Configuring firewall..."
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setblockall off
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/sbin/sshd
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setallowsshd on

# Enable SSH key-based auth only
echo "Configuring SSH..."
sudo sed -i '' 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sudo sed -i '' 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Install monitoring tools
brew install htop

# Set hostname
echo "Current hostname: $(hostname)"
read -p "Enter new hostname (or press Enter to keep current): " NEW_HOSTNAME
if [ -n "$NEW_HOSTNAME" ]; then
    sudo scset --set ComputerName "$NEW_HOSTNAME"
    sudo scset --set LocalHostName "$NEW_HOSTNAME"
    echo "Hostname set to $NEW_HOSTNAME"
fi

# Disable sleep
echo "Disabling sleep..."
sudo pmset -a sleep 0
sudo pmset -a disksleep 0
sudo pmset -a displaysleep 0

echo ""
echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. Run join-cluster.sh to join the WireGuard network"
echo "  2. Copy the SSH public key from the gateway to ~/.ssh/authorized_keys"
