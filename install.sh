#!/bin/bash
set -e

echo "Installing Claude Agent API..."

# Download files
mkdir -p claude-agent-api && cd claude-agent-api

# Create docker-compose.yml that uses pre-built image
cat > docker-compose.yml <<'EOF'
services:
  claude-agent:
    image: zenjabba/claude-agent-api:latest
    container_name: claude-agent-api
    ports:
      - "8787:8787"
    volumes:
      - claude-data:/data
    env_file:
      - .env
    environment:
      - PORT=8787
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8787/health"]
      interval: 30s
      timeout: 3s
      retries: 3

volumes:
  claude-data:
EOF

mkdir -p data
docker pull zenjabba/claude-agent-api:latest

echo ""
echo "Installation complete!"
echo ""

# Check if Claude CLI is installed
if ! command -v claude &> /dev/null; then
    echo "Claude CLI not found."
    echo ""
    echo "To install Claude CLI, run:"
    echo "  npm install -g @anthropic-ai/claude-code"
    echo ""
    echo "Or continue without it and paste your existing token below."
    echo ""
fi

# Get OAuth token
echo "Getting Claude OAuth token..."
echo ""
echo "If you don't have a token yet:"
echo "  1. Open a NEW terminal window"
echo "  2. Run: claude setup-token"
echo "  3. Complete the OAuth flow in your browser"
echo "  4. Copy the token (starts with sk-ant-oat01-)"
echo "  5. Return here and paste it below"
echo ""
echo "If you already have a token, paste it below:"
echo ""
read -p "OAuth Token (sk-ant-oat01-...): " OAUTH_TOKEN

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