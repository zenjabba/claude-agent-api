#!/bin/bash

# Docker setup script for Claude Agent API
# Handles OAuth setup and runs the container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Claude Agent API Docker Setup ===${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose first"
    exit 1
fi

# Create data directory for tokens
mkdir -p ./data

# Use docker-compose or docker compose depending on what's available
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# Pull the latest image first
echo "Pulling latest image..."
docker pull zenjabba/claude-agent-api:latest

# Check if tokens already exist
if [ -f "./data/.vars" ]; then
    echo -e "${GREEN}OAuth tokens already configured${NC}"
    echo "To reconfigure, delete ./data/.vars and ./data/.tokens.json"
else
    echo -e "${YELLOW}OAuth setup required${NC}"
    echo ""
    
    # Run OAuth setup inside Docker container
    echo "Starting OAuth setup..."
    docker run -it --rm \
        -v "$(pwd)/data:/data" \
        zenjabba/claude-agent-api:latest \
        python3 oauth_setup.py
    
    if [ ! -f "./data/.vars" ]; then
        echo -e "${RED}OAuth setup was not completed${NC}"
        exit 1
    fi
fi

# Set proper permissions
chmod 600 ./data/.vars 2>/dev/null || true
chmod 600 ./data/.tokens.json 2>/dev/null || true

echo ""
echo -e "${GREEN}Starting Claude Agent API with Docker Compose...${NC}"

# Start the container
$COMPOSE_CMD up -d

echo ""
echo -e "${GREEN}Claude Agent API is starting...${NC}"

# Wait for service to be healthy
echo "Waiting for service to be ready..."
sleep 5

# Test the service
RESPONSE=$(curl -s -X POST http://localhost:8787/query \
    -H "Content-Type: application/json" \
    -d '{"query": "Say hello"}' 2>/dev/null || echo '{"error": "Connection failed"}')

if echo "$RESPONSE" | grep -q '"response"'; then
    echo -e "${GREEN}Service is working correctly!${NC}"
    echo ""
    echo "API Endpoints:"
    echo "  GET  http://localhost:8787/health"
    echo "  POST http://localhost:8787/query"
    echo "  POST http://localhost:8787/execute"
    echo ""
    echo "Docker commands:"
    echo "  View logs:    $COMPOSE_CMD logs -f"
    echo "  Stop:         $COMPOSE_CMD down"
    echo "  Restart:      $COMPOSE_CMD restart"
    echo "  Update:       $COMPOSE_CMD pull && $COMPOSE_CMD up -d"
else
    echo -e "${YELLOW}Service test failed${NC}"
    echo "Response: $RESPONSE"
    echo ""
    echo "Check logs: $COMPOSE_CMD logs"
fi