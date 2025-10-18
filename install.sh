#!/bin/bash
set -e

echo "Installing Claude Agent API..."

# Download files
mkdir -p claude-agent-api && cd claude-agent-api
curl -sSL -O https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/docker-compose.yml
mkdir -p data
docker pull zenjabba/claude-agent-api:latest

echo ""
echo "✓ Installation complete!"
echo ""
echo "To set up and start Claude Agent API:"
echo ""
echo "  cd claude-agent-api"
echo "  docker run -it --rm -v \$(pwd)/data:/data zenjabba/claude-agent-api:latest python3 oauth_setup.py"
echo "  docker-compose up -d"