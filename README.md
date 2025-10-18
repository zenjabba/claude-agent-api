# Claude Agent API

A simple HTTP API server for Claude that runs anywhere - Docker, systemd, or standalone Python.

## Features

- 🔄 Automatic token refresh (OAuth tokens auto-renew)
- 🐳 Docker support with one-line deployment
- 🔒 Secure token storage
- 🚀 Simple REST API for Claude interactions
- 📦 No complex dependencies - just Python

## Quick Start (Docker)

```bash
# Clone and run
git clone https://github.com/zenjabba/claude-agent-api.git
cd claude-agent-api
./docker-setup.sh
```

That's it! The script will guide you through OAuth setup and start the API server.

## API Endpoints

- `GET /health` - Health check
- `POST /query` - Send queries to Claude
  ```json
  {
    "query": "Your question here"
  }
  ```
- `POST /execute` - Execute system commands (optional)
  ```json
  {
    "command": "ls -la"
  }
  ```

## Installation Methods

### Method 1: Docker (Recommended)

```bash
# Using docker-compose
docker-compose up -d

# Or using the setup script
./docker-setup.sh
```

### Method 2: Standalone Python

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run OAuth setup
./oauth_setup.py

# Start server
python3 server.py
```

### Method 3: Systemd Service

```bash
# Complete setup with systemd
sudo ./setup.sh
```

## OAuth Setup

The API requires Claude OAuth tokens. During setup, you'll choose between:

1. **Manual OAuth Flow** - Get a URL to authenticate on any device
2. **Remote Setup** - Copy tokens from another machine

Both methods support automatic token refresh.

## Environment Variables

- `PORT` - API port (default: 8787)
- `CLAUDE_CODE_OAUTH_TOKEN` - Your Claude OAuth token

## Docker Hub

```bash
# Pull directly from Docker Hub
docker pull zenjabba/claude-agent-api:latest

# Run with volume for token persistence
docker run -d \
  -p 8787:8787 \
  -v claude-data:/data \
  --name claude-agent \
  zenjabba/claude-agent-api:latest
```

## Development

```bash
# Build Docker image
docker build -t claude-agent-api .

# Run tests
./test.sh
```

## License

MIT