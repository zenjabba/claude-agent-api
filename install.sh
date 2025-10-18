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

# Check if Claude CLI is installed
if ! command -v claude &> /dev/null; then
    echo "Claude CLI not found. Installing..."
    npm install -g @anthropic-ai/claude-code
    echo ""
fi

# Run OAuth setup
echo "Setting up Claude OAuth token..."
echo "This will open a browser window for authentication."
echo "After you complete the OAuth flow, you'll see a token starting with 'sk-ant-oat01-'"
echo ""
read -p "Press Enter to start the OAuth setup..."

# Run claude setup-token
claude setup-token

# After setup-token completes (it clears screen), prompt for token
echo ""
echo "OAuth setup complete!"
echo ""
echo "Please paste your OAuth token below (starts with sk-ant-oat01-):"
read -r OAUTH_TOKEN

# Validate token format
if [[ ! $OAUTH_TOKEN =~ ^sk-ant-oat01- ]]; then
    echo "Error: Token must start with 'sk-ant-oat01-'"
    echo "Please run the setup manually:"
    echo "  1. Run: claude setup-token"
    echo "  2. Create .env: echo 'CLAUDE_CODE_OAUTH_TOKEN=your-token' > .env"
    echo "  3. Start server: docker-compose up -d"
    exit 1
fi

# Create .env file
echo "CLAUDE_CODE_OAUTH_TOKEN=$OAUTH_TOKEN" > .env
echo ""
echo ".env file created successfully!"
echo ""

# Start the server
echo "Starting Claude Agent API server..."
docker-compose up -d

echo ""
echo "Server started successfully!"
echo ""
echo "Next steps:"
echo "  1. Create an API key:"
echo "     docker-compose exec claude-agent python3 manage_keys.py create \"your-app-name\""
echo ""
echo "  2. Test the API:"
echo "     curl http://localhost:8787/health"
echo ""
echo "  3. Make a query:"
echo "     curl -X POST http://localhost:8787/query \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"query\": \"What is 2+2?\", \"api_key\": \"your-api-key\"}'"
echo ""