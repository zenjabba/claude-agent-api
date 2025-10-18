#!/bin/bash
# Claude Agent API - One-line installer
# Usage: curl -sSL https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/install.sh | bash

set -e

echo "Installing Claude Agent API..."
echo ""

# Create directory
mkdir -p claude-agent-api
cd claude-agent-api

# Download files
echo "Downloading configuration files..."
curl -sSL -O https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/docker-compose.yml
curl -sSL -O https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/docker-setup.sh
chmod +x docker-setup.sh

# Create data directory
mkdir -p data

# Pull Docker image
echo "Pulling Docker image..."
docker pull zenjabba/claude-agent-api:latest

echo ""
echo "✓ Installation complete!"
echo ""
echo "To set up OAuth authentication and start the service:"
echo ""
echo "  cd claude-agent-api"
echo "  ./docker-setup.sh"
echo ""
echo "Or run OAuth setup directly:"
echo ""
echo "  cd claude-agent-api"
echo "  docker run -it --rm -v \$(pwd)/data:/data zenjabba/claude-agent-api:latest python3 oauth_setup.py"
echo "  docker-compose up -d"
echo ""