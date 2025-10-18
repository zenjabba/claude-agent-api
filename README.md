# Claude Agent API

Simple HTTP API server for Claude, distributed as a Docker container.

```bash
curl -sSL https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/install.sh | bash
```

[![Docker Pulls](https://img.shields.io/docker/pulls/zenjabba/claude-agent-api)](https://hub.docker.com/r/zenjabba/claude-agent-api)
[![Docker Image Size](https://img.shields.io/docker/image-size/zenjabba/claude-agent-api)](https://hub.docker.com/r/zenjabba/claude-agent-api)
[![Build Status](https://github.com/zenjabba/claude-agent-api/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/zenjabba/claude-agent-api/actions)

## Features

- **Claude CLI Integration** - Uses official Claude CLI with OAuth tokens (auto-renewal handled by CLI)
- **API Key Protection** - Secure API key authentication
- **Model Selection** - Choose from any Claude model (Haiku 4.5 default)
- **Docker-only** - Simple, consistent deployment
- **Persistent Storage** - API keys stored in Docker volumes
- **Simple API** - RESTful endpoints for Claude
- **Multi-arch** - Supports AMD64 and ARM64

## Quick Start

### 1. Install

```bash
curl -sSL https://raw.githubusercontent.com/zenjabba/claude-agent-api/main/install.sh | bash
cd claude-agent-api
```

### 2. Setup OAuth Token

Get your Claude OAuth token:

```bash
# Install Claude CLI (if not already installed)
npm install -g @anthropic-ai/claude-code

# Generate OAuth token
claude setup-token
```

Create `.env` file with your token:

```bash
echo "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here" > .env
```

### 3. Start the Server

```bash
docker-compose up -d
```

### 4. Create an API Key

```bash
docker-compose exec claude-agent python3 manage_keys.py create "my-app"
```

This will output your API key:
```
API Key created successfully!
Name: my-app
Key:  sk-xnavTWseV_vPyi9HtAnpJ9KQ1o4mb9hgNU0zkFKMXH4

Keep this key secure - it won't be shown again!
```

## API Usage

### Health Check

```bash
curl http://localhost:8787/health
```

**Response:**
```json
{
  "status": "healthy",
  "hasToken": true,
  "timestamp": "2025-10-18T01:54:45.806285"
}
```

### Query Claude

**Basic Query (uses default model: claude-haiku-4-5):**

```bash
curl -X POST http://localhost:8787/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the meaning of life?",
    "api_key": "sk-your-api-key-here"
  }'
```

**Response:**
```json
{
  "response": "The meaning of life is a philosophical question..."
}
```

**Query with Custom Model:**

```bash
curl -X POST http://localhost:8787/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Write a Python function to calculate fibonacci",
    "model": "claude-sonnet-4-5",
    "api_key": "sk-your-api-key-here"
  }'
```

**Available Models:**
- `claude-haiku-4-5` (default - fastest, cheapest)
- `claude-sonnet-4-5` (balanced)
- `claude-opus-4` (most capable)
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`

### Error Responses

**Missing API Key (401):**
```json
{
  "error": "API key required",
  "message": "Include \"api_key\" in request body"
}
```

**Invalid API Key (403):**
```json
{
  "error": "Invalid API key"
}
```

**No Query (400):**
```json
{
  "error": "No prompt provided"
}
```

## API Key Management

### Create API Key

```bash
docker-compose exec claude-agent python3 manage_keys.py create "my-app-name"
```

### List API Keys

```bash
docker-compose exec claude-agent python3 manage_keys.py list
```

**Output:**
```
API Key                                            Name                 Created                   Last Used
------------------------------------------------------------------------------------------------------------------------
sk-xnavTWs...zkFKMXH4                              my-app               2025-10-18T01:54:46.329585 2025-10-18T01:54:58.066326

Total: 1 API key(s)
```

### Delete API Key

```bash
docker-compose exec claude-agent python3 manage_keys.py delete sk-xnavTWseV_vPyi9HtAnpJ9KQ1o4mb9hgNU0zkFKMXH4
```

## Docker Compose

```yaml
services:
  claude-agent:
    build: .
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

volumes:
  claude-data:
```

## Environment Variables

Create a `.env` file:

```bash
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here
PORT=8787
```

## Configuration

API keys are stored in `/data/api_keys.json` (persisted in Docker volume)

Default model can be changed by creating `/data/.config.json`:

```json
{
  "default_model": "claude-sonnet-4-5"
}
```

## Updating

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d
```

## Example Integration

### Python

```python
import requests

api_key = "sk-your-api-key-here"
url = "http://localhost:8787/query"

response = requests.post(url, json={
    "query": "What is 2+2?",
    "api_key": api_key
})

print(response.json()["response"])
```

### JavaScript/Node.js

```javascript
const response = await fetch('http://localhost:8787/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'What is 2+2?',
    api_key: 'sk-your-api-key-here'
  })
});

const data = await response.json();
console.log(data.response);
```

### curl

```bash
curl -X POST http://localhost:8787/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is 2+2?",
    "api_key": "sk-your-api-key-here"
  }'
```

## Security Notes

- API keys are stored securely in `/data/api_keys.json`
- OAuth tokens are stored in container environment variables
- API keys include creation and last-used timestamps
- Health endpoint is public (no API key required)
- Query endpoint requires valid API key

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs
```

### Token issues

OAuth tokens are managed automatically by Claude CLI and should not expire. If you see authentication errors:

1. Check that your token is correctly set in `.env`
2. Verify Claude CLI is installed in the container
3. Restart the container:
```bash
docker-compose restart
```

If issues persist, regenerate the token:
```bash
claude setup-token
# Update .env file with new token
docker-compose restart
```

### API key not working

List existing keys:
```bash
docker-compose exec claude-agent python3 manage_keys.py list
```

Create new key if needed:
```bash
docker-compose exec claude-agent python3 manage_keys.py create "new-key"
```

## License

MIT
