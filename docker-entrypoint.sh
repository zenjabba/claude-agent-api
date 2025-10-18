#!/bin/bash
set -e

# Check if tokens exist
if [ ! -f "/data/.vars" ]; then
    echo "OAuth tokens not found. Running setup..."
    echo ""
    cd /app
    python3 oauth_setup.py
    
    # Move tokens to /data if created in /app
    [ -f ".vars" ] && mv .vars /data/
    [ -f ".tokens.json" ] && mv .tokens.json /data/
    
    if [ ! -f "/data/.vars" ]; then
        echo "Setup incomplete. Container will exit."
        exit 1
    fi
fi

# Start the application
exec python3 start_with_refresh.py