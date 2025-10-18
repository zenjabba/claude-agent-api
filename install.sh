#!/bin/bash
# Claude Agent API - One-line installer
# Usage: curl -sSL https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/install.sh | bash

set -e

echo "Installing Claude Agent API..."

# Download files
curl -sSL -O https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/docker-compose.yml
curl -sSL -O https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/docker-setup.sh

# Make executable and run
chmod +x docker-setup.sh
./docker-setup.sh