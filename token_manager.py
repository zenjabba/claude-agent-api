#!/usr/bin/env python3

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Try to import requests, use urllib as fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.parse
    import urllib.error
    HAS_REQUESTS = False

class TokenManager:
    def __init__(self):
        # Use /data directory if it exists (Docker), otherwise use script directory
        if Path('/data').exists() and os.access('/data', os.W_OK):
            self.data_dir = Path('/data')
        else:
            self.data_dir = Path(__file__).parent
        
        self.token_file = self.data_dir / '.tokens.json'
        self.vars_file = self.data_dir / '.vars'
        self.tokens = self.load_tokens()

    def load_tokens(self):
        """Load tokens from file"""
        try:
            if self.token_file.exists():
                with open(self.token_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading tokens: {e}")
        return None

    def save_tokens(self, tokens):
        """Save tokens to file"""
        # Save to .tokens.json
        with open(self.token_file, 'w') as f:
            json.dump(tokens, f, indent=2)
        os.chmod(self.token_file, 0o600)
        self.tokens = tokens
        
        # Update .vars file with new access token
        with open(self.vars_file, 'w') as f:
            f.write(f"CLAUDE_CODE_OAUTH_TOKEN={tokens['access_token']}\n")
        os.chmod(self.vars_file, 0o600)

    def _make_request(self, url, data):
        """Make HTTP POST request"""
        if HAS_REQUESTS:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Request failed: {response.status_code} - {response.text}")
        else:
            # Use urllib as fallback
            req_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={'Content-Type': 'application/json'}
            )
            
            try:
                with urllib.request.urlopen(req) as response:
                    return json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                raise Exception(f"Request failed: {e.code} - {error_body}")

    def refresh_token(self):
        """Refresh the OAuth token"""
        if not self.tokens or not self.tokens.get('refresh_token'):
            raise Exception("No refresh token available. Please run initial setup.")
        
        print("Refreshing Claude OAuth token...")
        
        url = 'https://console.anthropic.com/oauth/token'
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.tokens['refresh_token'],
            'client_id': 'anthropic-oauth-cli'
        }
        
        try:
            response = self._make_request(url, data)
            
            if 'access_token' in response:
                new_tokens = {
                    'access_token': response['access_token'],
                    'refresh_token': response.get('refresh_token', self.tokens['refresh_token']),
                    'expires_at': (datetime.now() + timedelta(seconds=response.get('expires_in', 3600))).isoformat()
                }
                
                self.save_tokens(new_tokens)
                print("Token refreshed successfully!")
                print(f"Expires at: {new_tokens['expires_at']}")
                return new_tokens
            else:
                raise Exception(f"Token refresh failed: {response}")
                
        except Exception as e:
            raise Exception(f"Failed to refresh token: {e}")

    def is_token_expired(self):
        """Check if token is expired or will expire soon"""
        if not self.tokens or not self.tokens.get('expires_at'):
            return True
        
        expires_at = datetime.fromisoformat(self.tokens['expires_at'])
        now = datetime.now()
        
        # Refresh 5 minutes before expiration
        return now >= expires_at - timedelta(minutes=5)

    def ensure_valid_token(self):
        """Ensure we have a valid token, refresh if needed"""
        if self.is_token_expired():
            try:
                self.refresh_token()
            except Exception as e:
                print(f"Failed to refresh token: {e}")
                raise

    def setup_from_oauth_token(self, oauth_token):
        """Initial setup from claude setup-token output"""
        tokens = {
            'access_token': oauth_token,
            'refresh_token': None,  # Will need to be obtained from initial OAuth flow
            'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        self.save_tokens(tokens)
        print("Initial token saved. Note: Auto-refresh requires full OAuth flow.")

def main():
    """CLI usage"""
    if len(sys.argv) < 2:
        print("Usage: python3 token_manager.py [refresh|check|setup <token>]")
        sys.exit(1)
    
    manager = TokenManager()
    command = sys.argv[1]
    
    if command == 'refresh':
        try:
            manager.refresh_token()
            print("Token refreshed successfully")
        except Exception as e:
            print(f"Failed to refresh token: {e}")
            sys.exit(1)
    
    elif command == 'check':
        if manager.is_token_expired():
            print("Token is expired or will expire soon")
            sys.exit(1)
        else:
            print("Token is valid")
            if manager.tokens:
                print(f"Expires at: {manager.tokens.get('expires_at', 'Unknown')}")
    
    elif command == 'setup':
        if len(sys.argv) < 3:
            print("Usage: python3 token_manager.py setup <token>")
            sys.exit(1)
        
        token = sys.argv[2]
        try:
            manager.setup_from_oauth_token(token)
            print("Token setup complete")
        except Exception as e:
            print(f"Setup failed: {e}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: python3 token_manager.py [refresh|check|setup <token>]")
        sys.exit(1)

if __name__ == '__main__':
    main()