#!/bin/bash
set -euo pipefail

echo "[lab] Starting infrastructure services..."

mkdir -p /run/sshd

echo "[lab] Starting SSH daemon..."
/usr/sbin/sshd
echo "[lab] SSH started (pid $(pgrep -x sshd | head -1))"

echo "[lab] Staging authorized_keys..."
mkdir -p /run/nexus
if [ ! -f /run/nexus/authorized_keys ]; then
    echo "[lab] ERROR: Staged authorized_keys file not found at /run/nexus/authorized_keys" >&2
    echo "[lab] Ensure the compose volume mounts ./linux-lab/ssh/authorized_keys to /run/nexus/authorized_keys" >&2
    exit 1
fi
mkdir -p /home/nexus/.ssh
chown nexus:nexus /home/nexus/.ssh
chmod 700 /home/nexus/.ssh
cp /run/nexus/authorized_keys /home/nexus/.ssh/authorized_keys
chown nexus:nexus /home/nexus/.ssh/authorized_keys
chmod 600 /home/nexus/.ssh/authorized_keys
echo "[lab] Authorized keys staged successfully"

echo "[lab] Starting Nginx..."
nginx -g "daemon off;" &
NGINX_PID=$!
echo "[lab] Nginx started (pid $NGINX_PID)"

sleep 2

if ! kill -0 "$NGINX_PID" 2>/dev/null; then
    echo "[lab] ERROR: Nginx failed to start"
    exit 1
fi

echo "[lab] Starting Python API..."
cd /opt/api
nohup python3 app.py --host 0.0.0.0 --port 5000 > /var/log/app/api.log 2>&1 &
API_PID=$!
echo "[lab] API started (pid $API_PID)"

sleep 3

if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "[lab] ERROR: API failed to start"
    cat /var/log/app/api.log
    exit 1
fi

echo "[lab] All services started. Container is healthy."

wait "$NGINX_PID"
