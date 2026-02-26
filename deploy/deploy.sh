#!/bin/bash
set -e

VPS_HOST="173.249.21.16"
VPS_USER="root"
REMOTE_DIR="/opt/stock-advisor"

echo "=== Deploying Stock Advisor API to VPS ==="

# 1. Sync files to VPS
echo "[1/4] Syncing files..."
rsync -avz --exclude='venv' --exclude='__pycache__' --exclude='*.db' --exclude='.git' \
  --exclude='data/*.json' --exclude='data/*.csv' --exclude='.env' \
  -e ssh ../ ${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}/

# 2. Setup venv and install deps on VPS
echo "[2/4] Installing dependencies..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /opt/stock-advisor
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
ENDSSH

# 3. Install systemd service
echo "[3/4] Installing systemd service..."
scp stock-advisor.service ${VPS_USER}@${VPS_HOST}:/etc/systemd/system/stock-advisor.service
ssh ${VPS_USER}@${VPS_HOST} "systemctl daemon-reload && systemctl enable stock-advisor"

# 4. Restart service
echo "[4/4] Restarting service..."
ssh ${VPS_USER}@${VPS_HOST} "systemctl restart stock-advisor"

echo "=== Deployment complete! ==="
echo "API running at http://${VPS_HOST}:8100 (internal only)"
echo "Test: ssh ${VPS_USER}@${VPS_HOST} 'curl -s http://localhost:8100/health'"
