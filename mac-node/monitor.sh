#!/bin/bash
# monitor.sh — Health check script for a macOS node
# Run via cron or launchd to report node status
set -euo pipefail

API_URL="${RENTAMAC_API_URL:-http://89.125.30.138:8000}"
NODE_ID="${RENTAMAC_NODE_ID:-}"

if [ -z "$NODE_ID" ]; then
    echo "ERROR: Set RENTAMAC_NODE_ID environment variable"
    exit 1
fi

# Collect system metrics
HOSTNAME=$(hostname)
UPTIME=$(uptime | sed 's/.*up //' | sed 's/,.*//')
CPU_USAGE=$(top -l 1 -n 0 | grep "CPU usage" | awk '{print $3}' | tr -d '%' || echo "0")
MEM_TOTAL=$(sysctl -n hw.memsize)
MEM_PRESSURE=$(memory_pressure 2>/dev/null | grep "System-wide memory" | awk '{print $5}' || echo "unknown")
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')
LOAD_AVG=$(sysctl -n vm.loadavg | awk '{print $2}')

# Check WireGuard status
WG_STATUS="down"
if ifconfig wg0 &>/dev/null; then
    WG_STATUS="up"
fi

# Report to API (non-blocking)
REPORT=$(cat <<EOF
{
    "node_id": $NODE_ID,
    "hostname": "$HOSTNAME",
    "uptime": "$UPTIME",
    "cpu_usage": "$CPU_USAGE",
    "disk_usage_percent": $DISK_USAGE,
    "load_average": "$LOAD_AVG",
    "wireguard": "$WG_STATUS",
    "mem_pressure": "$MEM_PRESSURE"
}
EOF
)

# Try to update node status
if command -v curl &>/dev/null; then
    curl -s -X PATCH "$API_URL/api/nodes/$NODE_ID" \
        -H "Content-Type: application/json" \
        -d "{\"status\": \"online\", \"hardware\": \"$HOSTNAME | CPU: ${CPU_USAGE}% | Disk: ${DISK_USAGE}% | Load: ${LOAD_AVG}\"}" \
        &>/dev/null || true
fi

echo "[$(date -Iseconds)] Health check OK — Node $NODE_ID"
echo "  Hostname: $HOSTNAME"
echo "  Uptime: $UPTIME"
echo "  CPU: ${CPU_USAGE}%"
echo "  Disk: ${DISK_USAGE}%"
echo "  Load: $LOAD_AVG"
echo "  WireGuard: $WG_STATUS"