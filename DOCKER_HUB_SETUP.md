# Docker Hub Setup Instructions

## Setting up Automated Builds

1. **Create Docker Hub Repository**
   - Go to https://hub.docker.com/
   - Create repository: `zenjabba/claude-agent-api`

2. **Add GitHub Secret**
   - Go to GitHub repository settings
   - Navigate to Settings → Secrets and variables → Actions
   - Add new repository secret:
     - Name: `DOCKER_HUB_TOKEN`
     - Value: Your Docker Hub access token

3. **Create Docker Hub Access Token**
   - Go to Docker Hub → Account Settings → Security
   - New Access Token
   - Description: `claude-agent-api-github`
   - Access permissions: Read, Write, Delete
   - Copy the token and add it as GitHub secret

4. **Test the Workflow**
   - Push to main branch
   - Check Actions tab in GitHub
   - Verify image appears in Docker Hub

## Manual Build Commands

```bash
# Build locally
docker build -t zenjabba/claude-agent-api:latest .

# Test locally
docker run -it --rm -v claude-data:/data -p 8787:8787 zenjabba/claude-agent-api:latest

# Push manually (if needed)
docker push zenjabba/claude-agent-api:latest
```

## Tagging for Releases

Create a git tag to trigger versioned builds:

```bash
git tag v1.0.0
git push origin v1.0.0
```

This will create Docker tags:
- `zenjabba/claude-agent-api:1.0.0`
- `zenjabba/claude-agent-api:1.0`
- `zenjabba/claude-agent-api:1`
- `zenjabba/claude-agent-api:latest`