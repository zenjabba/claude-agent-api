#!/usr/bin/env python3

import os
import sys
import json
import secrets
import hashlib
import base64
from pathlib import Path
from datetime import datetime, timedelta

# Try to import requests, use urllib as fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.parse
    HAS_REQUESTS = False

from token_manager import TokenManager

class HeadlessOAuthSetup:
    def __init__(self):
        self.client_id = 'anthropic-oauth-cli'
        self.redirect_uri = 'http://localhost:8899/callback'
        self.auth_endpoint = 'https://console.anthropic.com/oauth/authorize'
        self.token_endpoint = 'https://console.anthropic.com/oauth/token'

    def generate_pkce(self):
        """Generate PKCE verifier and challenge"""
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return verifier, challenge

    def generate_auth_url(self, challenge, state):
        """Generate the authorization URL"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
            'state': state,
            'scope': 'user:inference user:profile'
        }
        
        if HAS_REQUESTS:
            from urllib.parse import urlencode
            return f"{self.auth_endpoint}?{urlencode(params)}"
        else:
            return f"{self.auth_endpoint}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, code, verifier):
        """Exchange authorization code for tokens"""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'code_verifier': verifier
        }
        
        if HAS_REQUESTS:
            response = requests.post(self.token_endpoint, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")
        else:
            # Use urllib as fallback
            req_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(
                self.token_endpoint,
                data=req_data,
                headers={'Content-Type': 'application/json'}
            )
            
            try:
                with urllib.request.urlopen(req) as response:
                    return json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                raise Exception(f"Token exchange failed: {e.code} - {error_body}")

    def save_tokens(self, token_response):
        """Save tokens using TokenManager"""
        manager = TokenManager()
        tokens = {
            'access_token': token_response['access_token'],
            'refresh_token': token_response.get('refresh_token'),
            'expires_at': (
                datetime.now() + timedelta(seconds=token_response.get('expires_in', 3600))
            ).isoformat()
        }
        
        manager.save_tokens(tokens)
        print("\n✓ Tokens saved successfully!")
        print(f"  Access token expires at: {tokens['expires_at']}")
        if tokens['refresh_token']:
            print("  Refresh token saved for automatic renewal")

    def manual_oauth_flow(self):
        """Manual OAuth flow for headless environments"""
        verifier, challenge = self.generate_pkce()
        state = secrets.token_hex(16)
        auth_url = self.generate_auth_url(challenge, state)
        
        print("\n=== Claude OAuth Setup ===\n")
        print("Since no browser is available, please follow these steps:\n")
        print("1. Copy this URL and open it in a browser on any device:")
        print(f"\n{auth_url}\n")
        print("2. Sign in to Claude and authorize the application")
        print("3. After authorization, you'll see a callback URL that starts with:")
        print("   http://localhost:8899/callback?code=...")
        print("4. Copy the entire URL or just the code parameter\n")
        
        user_input = input("Paste the callback URL or authorization code here: ").strip()
        
        # Extract code from input
        code = None
        if 'callback?' in user_input:
            try:
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(user_input)
                params = parse_qs(parsed.query)
                code = params.get('code', [None])[0]
            except Exception:
                pass
        elif 'code=' in user_input:
            # Extract code from partial URL
            import re
            match = re.search(r'code=([^&]+)', user_input)
            if match:
                code = match.group(1)
        else:
            # Assume it's just the code
            code = user_input
        
        if not code:
            raise Exception("No authorization code found in input")
        
        print("\n✓ Authorization code received!")
        print("  Exchanging for tokens...")
        
        tokens = self.exchange_code_for_token(code, verifier)
        self.save_tokens(tokens)
        
        return tokens

    def remote_setup_instructions(self):
        """Instructions for remote setup"""
        print("\n=== Remote OAuth Setup Instructions ===\n")
        print("To set up OAuth tokens from a machine with a browser:\n")
        print("1. On a machine with a browser, clone this repository")
        print("2. Run: python3 oauth_setup.py")
        print("3. Complete the authentication in your browser")
        print("4. Copy the generated files to this server:")
        print("   - .tokens.json (contains refresh token)")
        print("   - .vars (contains access token)")
        print("\n5. Place these files in the current directory")
        print("6. Set proper permissions: chmod 600 .tokens.json .vars\n")
        
        input("Press Enter after copying the files to check... ")
        
        # Check if files exist
        token_file = Path('.tokens.json')
        vars_file = Path('.vars')
        
        if token_file.exists() and vars_file.exists():
            print("\n✓ Token files found!")
            
            # Set proper permissions
            os.chmod(token_file, 0o600)
            os.chmod(vars_file, 0o600)
            
            # Load and display token info
            with open(token_file, 'r') as f:
                tokens = json.load(f)
            
            print(f"  Access token expires at: {tokens.get('expires_at', 'Unknown')}")
            if tokens.get('refresh_token'):
                print("  Refresh token available for automatic renewal")
            return True
        else:
            print("\n✗ Token files not found")
            print("  Expected files:")
            print("  - .tokens.json")
            print("  - .vars")
            return False

    def run(self):
        """Main menu for headless setup"""
        print("\n=== Claude OAuth Setup ===\n")
        print("Choose your setup method:\n")
        print("1. Manual OAuth flow (authenticate via browser on another device)")
        print("2. Remote setup (copy tokens from another machine)")
        print("3. Exit\n")
        
        choice = input("Enter your choice (1-3): ").strip()
        
        try:
            if choice == '1':
                self.manual_oauth_flow()
                print("\n✓ OAuth setup complete with auto-refresh enabled!")
            elif choice == '2':
                success = self.remote_setup_instructions()
                if success:
                    print("\n✓ Remote setup complete!")
            elif choice == '3':
                print("\nExiting...")
                sys.exit(0)
            else:
                print("\nInvalid choice")
                sys.exit(1)
        except Exception as e:
            print(f"\n✗ Setup failed: {e}")
            sys.exit(1)

def main():
    """Run headless OAuth setup"""
    setup = HeadlessOAuthSetup()
    setup.run()

if __name__ == '__main__':
    main()