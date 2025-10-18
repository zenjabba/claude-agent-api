# Claude Agent API

Simple HTTP API server for Claude, distributed as a Docker container.

```bash
curl -sSL https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/install.sh | bash
```

[![Docker Pulls](https://img.shields.io/docker/pulls/zenjabba/claude-agent-api)](https://hub.docker.com/r/zenjabba/claude-agent-api)
[![Docker Image Size](https://img.shields.io/docker/image-size/zenjabba/claude-agent-api)](https://hub.docker.com/r/zenjabba/claude-agent-api)
[![Build Status](https://github.com/zenjabba/claude-agent-api/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/zenjabba/claude-agent-api/actions)

## Features

- **Docker-only** - Simple, consistent deployment
- **Auto-refresh** - OAuth tokens renew automatically
- **Secure** - Tokens stored in Docker volumes
- **Simple API** - RESTful endpoints for Claude
- **Multi-arch** - Supports AMD64 and ARM64

## Quick Start

```bash
curl -sSL https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/install.sh | bash
```

## API Usage

### Health Check
```bash
curl http://localhost:8787/health
```

### Query Claude
```bash
curl -X POST http://localhost:8787/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the meaning of life?"}'
```

### Execute Command (Optional)
```bash
curl -X POST http://localhost:8787/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "date"}'
```

## OAuth Setup

On first run, you'll need to authenticate with Claude. The setup script provides two options:

1. **Manual OAuth Flow** - Get a URL, authenticate on any device, paste code back
2. **Remote Setup** - Copy existing tokens from another installation

Tokens are stored in a Docker volume and automatically refresh.

## Docker Compose

```yaml
services:
  claude-agent:
    image: zenjabba/claude-agent-api:latest
    container_name: claude-agent-api
    ports:
      - "8787:8787"
    volumes:
      - claude-data:/data
    restart: unless-stopped

volumes:
  claude-data:
```

## Environment Variables

- `PORT` - API port (default: 8787)

## Updating

```bash
# Pull latest image
docker-compose pull

# Restart container
docker-compose up -d
```

## License

MIT# Trigger build
