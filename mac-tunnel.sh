#!/bin/bash
set -e
echo "[1/3] Adding server host key..."
ssh-keyscan -H 89.125.30.138 >> ~/.ssh/known_hosts 2>/dev/null
echo "[2/3] Testing SSH to server..."
ssh -o ConnectTimeout=10 root@89.125.30.138 "echo REVERSE_SSH_OK" && echo "SSH to server works!" || {
  echo "Cannot SSH to server. Trying via VPN..."
  ssh -o ConnectTimeout=10 root@10.0.0.1 "echo REVERSE_SSH_OK" && echo "SSH via VPN works!"
}
echo "[3/3] Starting reverse tunnel in background..."
# -R 2222:localhost:22 means: on server port 2222, forward to Mac's port 22
# -N = no remote command, -f = background, -o ServerAliveInterval = keep alive
nohup ssh -N -R 2222:localhost:22 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes root@89.125.30.138 &
echo $! > /tmp/reverse-tunnel.pid
sleep 2
if kill -0 $(cat /tmp/reverse-tunnel.pid) 2>/dev/null; then
  echo "✅ Reverse tunnel running! PID: $(cat /tmp/reverse-tunnel.pid)"
  echo "Server can now reach Mac via: ssh -p 2222 admin@localhost"
else
  echo "❌ Tunnel failed. Trying VPN..."
  nohup ssh -N -R 2222:localhost:22 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes root@10.0.0.1 &
  echo $! > /tmp/reverse-tunnel.pid
  sleep 2
  if kill -0 $(cat /tmp/reverse-tunnel.pid) 2>/dev/null; then
    echo "✅ Reverse tunnel via VPN running!"
  else
    echo "❌ Tunnel failed. Check SSH connectivity."
  fi
fi