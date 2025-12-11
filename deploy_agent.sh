#!/bin/bash

# Configuration
WINDOWS_USER="Achu Pradeep"  # User provided
WINDOWS_IP="192.168.122.121" # Windows IP
REMOTE_PATH="C:/Users/achup/OneDrive/Documents/windows_agent/agent.py" # User provided path

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Deploying agent.py to $WINDOWS_IP...${NC}"

# Check if sshpass is installed (optional, for passwordless if keys aren't set)
# sudo apt-get install sshpass

# SCP Command
# Using strict host key checking=no to avoid prompts on local network changes
scp -o StrictHostKeyChecking=no windows_agent/agent.py "$WINDOWS_USER@$WINDOWS_IP:$REMOTE_PATH"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Success! agent.py updated on Windows.${NC}"
    echo "Please restart the agent on Windows if it's running."
else
    echo "Deployment failed. Check username, path, and SSH connectivity."
fi
