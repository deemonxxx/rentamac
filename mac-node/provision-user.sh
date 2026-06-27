#!/bin/bash
# provision-user.sh — Create a client user on a macOS node
# Usage: sudo ./provision-user.sh <username>
set -euo pipefail

USERNAME="${1:?Usage: $0 <username>}"

echo "=== Provisioning user: $USERNAME ==="

# Check if user already exists
if id "$USERNAME" &>/dev/null; then
    echo "ERROR: User '$USERNAME' already exists"
    exit 1
fi

# Create user
sudo sysadminctl -addUser "$USERNAME" \
    -shell /bin/zsh \
    -home "/Users/$USERNAME" \
    -password '*'

# Create SSH directory
sudo mkdir -p "/Users/$USERNAME/.ssh"
sudo chmod 700 "/Users/$USERNAME/.ssh"
sudo touch "/Users/$USERNAME/.ssh/authorized_keys"
sudo chmod 600 "/Users/$USERNAME/.ssh/authorized_keys"

# Set ownership
sudo chown -R "$USERNAME":staff "/Users/$USERNAME"

# Create user-level LaunchAgents directory for monitoring
sudo mkdir -p "/Users/$USERNAME/Library/LaunchAgents"
sudo chown "$USERNAME":staff "/Users/$USERNAME/Library/LaunchAgents"

echo "=== User '$USERNAME' provisioned successfully ==="
echo "Home: /Users/$USERNAME"
echo "SSH: /Users/$USERNAME/.ssh/"
echo ""
echo "Add SSH public keys to: /Users/$USERNAME/.ssh/authorized_keys"