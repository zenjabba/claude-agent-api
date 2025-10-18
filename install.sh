#!/bin/bash
set -e

echo "Installing Claude Agent API..."

# Download files
mkdir -p claude-agent-api && cd claude-agent-api
curl -sSL -O https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/docker-compose.yml
mkdir -p data
docker pull zenjabba/claude-agent-api:latest

echo ""
echo "Installation complete!"
echo ""
echo "To set up and start Claude Agent API:"
echo ""
echo "  cd claude-agent-api"
echo ""
echo "Get your OAuth token:"
echo "  1. Run: claude setup-token"
echo "  2. Copy the token (starts with sk-ant-oat01-)"
echo ""
echo "Create .env file with your token:"
echo "  echo 'CLAUDE_CODE_OAUTH_TOKEN=your-token-here' > .env"
echo ""
echo "Start the server:"
echo "  docker-compose up -d"