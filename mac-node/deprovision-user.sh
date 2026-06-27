#!/bin/bash
# deprovision-user.sh — Delete a client user from a macOS node
# Usage: sudo ./deprovision-user.sh <username>
set -euo pipefail

USERNAME="${1:?Usage: $0 <username>}"

echo "=== Deprovisioning user: $USERNAME ==="

# Check if user exists
if ! id "$USERNAME" &>/dev/null; then
    echo "WARNING: User '$USERNAME' does not exist, skipping"
    exit 0
fi

# Kill all processes owned by the user
echo "Killing user processes..."
sudo pkill -u "$USERNAME" 2>/dev/null || true
sleep 2

# Remove crontab
sudo crontab -r -u "$USERNAME" 2>/dev/null || true

# Delete the user and home directory
echo "Deleting user and home directory..."
sudo sysadminctl -deleteUser "$USERNAME" -deleteHome

# Remove any lingering files
sudo rm -rf "/Users/$USERNAME" 2>/dev/null || true

echo "=== User '$USERNAME' deprovisioned successfully ==="