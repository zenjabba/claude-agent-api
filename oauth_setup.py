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

# Ensure we use /data directory when running in Docker
if os.path.exists('/data') and os.access('/data', os.W_OK):
    import token_manager
    token_manager.DATA_DIR_OVERRIDE = Path('/data')

class HeadlessOAuthSetup:
    def __init__(self):
        # Use Claude's official OAuth client ID
        self.client_id = '9d1c250a-e61b-44d9-88ed-5944d1962f5e'
        # Two redirect options: localhost for automated flow, or console for manual code display
        self.redirect_uri_local = 'http://localhost:8899/callback'
        self.redirect_uri_console = 'https://console.anthropic.com/oauth/code/callback'
        self.auth_endpoint = 'https://claude.ai/oauth/authorize'
        self.token_endpoint = 'https://claude.ai/api/oauth/token'

    def generate_pkce(self):
        """Generate PKCE verifier and challenge"""
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return verifier, challenge

    def generate_auth_url(self, challenge, state, redirect_uri=None, code_display=False):
        """Generate the authorization URL"""
        if redirect_uri is None:
            redirect_uri = self.redirect_uri_local
            
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': 'user:inference',
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
            'state': state
        }
        
        # Add code=true for browser display mode
        if code_display:
            params = {'code': 'true', **params}
        
        if HAS_REQUESTS:
            from urllib.parse import urlencode
            return f"{self.auth_endpoint}?{urlencode(params)}"
        else:
            return f"{self.auth_endpoint}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, code, verifier, redirect_uri=None):
        """Exchange authorization code for tokens"""
        if redirect_uri is None:
            redirect_uri = self.redirect_uri_local
            
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
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
        print("\nTokens saved successfully!")
        print(f"  Access token expires at: {tokens['expires_at']}")
        if tokens['refresh_token']:
            print("  Refresh token saved for automatic renewal")

    def browser_code_display_flow(self):
        """OAuth flow that displays code in browser (like Claude CLI)"""
        verifier, challenge = self.generate_pkce()
        state = secrets.token_hex(16)
        auth_url = self.generate_auth_url(
            challenge, state, 
            redirect_uri=self.redirect_uri_console,
            code_display=True
        )
        
        print("\n=== Claude OAuth Setup (Browser Code Display) ===\n")
        print("This method displays the authorization code in your browser.\n")
        print("1. Copy this URL and open it in a browser:")
        print(f"\n{auth_url}\n")
        print("2. Sign in to Claude and authorize the application")
        print("3. The authorization code will be displayed in the browser")
        print("4. Copy the authorization code\n")
        
        code = input("Paste the authorization code here: ").strip()
        
        if not code:
            raise Exception("No authorization code provided")
        
        print("\nAuthorization code received!")
        print("  Exchanging for tokens...")
        
        tokens = self.exchange_code_for_token(code, verifier, self.redirect_uri_console)
        self.save_tokens(tokens)
        
        return tokens

    def manual_oauth_flow(self):
        """Manual OAuth flow for headless environments"""
        verifier, challenge = self.generate_pkce()
        state = secrets.token_hex(16)
        auth_url = self.generate_auth_url(challenge, state)
        
        print("\n=== Claude OAuth Setup (Localhost Callback) ===\n")
        print("IMPORTANT: Due to Cloudflare protection, the automated token exchange may fail.")
        print("If you encounter issues, try option 2 (Browser Code Display) instead.\n")
        print("To proceed with localhost callback setup:\n")
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
        
        print("\nAuthorization code received!")
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
            print("\nToken files found!")
            
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
            print("\nToken files not found")
            print("  Expected files:")
            print("  - .tokens.json")
            print("  - .vars")
            return False

    def claude_cli_token_setup(self):
        """Setup using Claude CLI generated token"""
        print("\n=== Claude CLI Token Setup ===\n")
        print("This method uses a long-lived token generated by the Claude CLI.\n")
        print("Prerequisites:")
        print("1. Install Claude CLI: npm install -g @anthropic/claude-code")
        print("2. Run: claude setup-token")
        print("3. Copy the generated token\n")
        
        token = input("Paste your Claude token here: ").strip()
        
        if not token:
            print("\nNo token provided")
            return False
        
        # Save token using TokenManager
        manager = TokenManager()
        manager.setup_from_oauth_token(token)
        
        print("\nToken saved successfully!")
        print("Note: This token will need manual renewal when it expires.")
        return True

    def run(self):
        """Main menu for headless setup"""
        print("\n=== Claude OAuth Setup ===\n")
        print("Choose your setup method:\n")
        print("1. Localhost callback (may fail due to Cloudflare protection)")
        print("2. Browser code display (recommended - like Claude CLI)")
        print("3. Remote setup (copy tokens from another machine)")
        print("4. Use Claude CLI token")
        print("5. Exit\n")
        
        choice = input("Enter your choice (1-5): ").strip()
        
        try:
            if choice == '1':
                self.manual_oauth_flow()
                print("\nOAuth setup complete with auto-refresh enabled!")
            elif choice == '2':
                self.browser_code_display_flow()
                print("\nOAuth setup complete with auto-refresh enabled!")
            elif choice == '3':
                success = self.remote_setup_instructions()
                if success:
                    print("\nRemote setup complete!")
            elif choice == '4':
                self.claude_cli_token_setup()
            elif choice == '5':
                print("\nExiting...")
                sys.exit(0)
            else:
                print("\nInvalid choice")
                sys.exit(1)
        except Exception as e:
            print(f"\nSetup failed: {e}")
            if "403" in str(e) or "Cloudflare" in str(e) or "Just a moment" in str(e):
                print("\nThis appears to be a Cloudflare protection issue.")
                print("\nRecommended alternative: Use the Claude CLI to generate a long-lived token:")
                print("1. Install Claude CLI: npm install -g @anthropic/claude-code")
                print("2. Run: claude setup-token")
                print("3. Copy the generated token")
                print("4. Use the token with this API\n")
            sys.exit(1)

def main():
    """Run headless OAuth setup"""
    setup = HeadlessOAuthSetup()
    setup.run()

if __name__ == '__main__':
    main()