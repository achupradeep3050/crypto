#!/bin/bash

# Configuration
WINDOWS_USER="achu"
WINDOWS_IP="192.168.122.121"
REMOTE_DIR="C:/Users/achup/OneDrive/Documents/windows_agent"
REMOTE_FILE="$REMOTE_DIR/agent.py"

# SSH Password
SSH_PASS="root"

# Helper to run SSH command
run_remote() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$WINDOWS_USER@$WINDOWS_IP" "$1"
}

# Helper to Copy file
copy_file() {
    sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no windows_agent/agent.py "$WINDOWS_USER@$WINDOWS_IP:$REMOTE_FILE"
}

echo "---------------------------------------------------"
echo "🔄 Connecting to Windows ($WINDOWS_IP)..."

# 1. Kill existing Python Agent
echo "💀 Killing existing agent process..."
run_remote "taskkill /F /IM python.exe"

# 2. Update File
echo "Cc Uploading latest agent.py..."
copy_file

# 3. Start Agent
echo "🚀 Starting new agent process..."
# Using PowerShell to start detached process
run_remote "powershell -Command \"Start-Process python -ArgumentList 'agent.py' -WorkingDirectory '$REMOTE_DIR' -WindowStyle Minimized\""

echo "---------------------------------------------------"
echo "✅ Done! Check logs/agent_remote.log for output."
