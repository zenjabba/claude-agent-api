#!/bin/bash

# Build and push Docker image to Docker Hub
# Usage: ./build-and-push.sh [tag]

set -e

DOCKER_REPO="zenjabba/claude-agent-api"
TAG="${1:-latest}"

echo "Building Docker image..."
docker build -t ${DOCKER_REPO}:${TAG} .

if [ "$TAG" != "latest" ]; then
    docker tag ${DOCKER_REPO}:${TAG} ${DOCKER_REPO}:latest
fi

echo "Pushing to Docker Hub..."
docker push ${DOCKER_REPO}:${TAG}

if [ "$TAG" != "latest" ]; then
    docker push ${DOCKER_REPO}:latest
fi

echo "Done! Image published as ${DOCKER_REPO}:${TAG}"