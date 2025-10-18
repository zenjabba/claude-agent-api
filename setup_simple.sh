#!/bin/bash

echo "=== Simple Claude Agent API Setup ==="
echo ""
echo "Step 1: Get your OAuth token"
echo "Run this command on your machine:"
echo "  claude setup-token"
echo ""
echo "Step 2: Copy the token (starts with sk-ant-oat01-)"
echo ""
read -p "Paste your token here: " TOKEN

if [ -z "$TOKEN" ]; then
    echo "No token provided!"
    exit 1
fi

# Save to .env file
echo "CLAUDE_CODE_OAUTH_TOKEN=$TOKEN" > .env
echo "PORT=8787" >> .env

echo ""
echo "Setup complete! Token saved to .env"
echo ""
echo "To start the server:"
echo "  docker-compose up -d"
