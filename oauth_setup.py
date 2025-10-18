#!/usr/bin/env python3

import os
import sys
import json
from pathlib import Path

# Try to import requests, use urllib as fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

from token_manager import TokenManager

# Ensure we use /data directory when running in Docker
if os.path.exists('/data') and os.access('/data', os.W_OK):
    import token_manager
    token_manager.DATA_DIR_OVERRIDE = Path('/data')

class HeadlessOAuthSetup:
    def __init__(self):
        self.api_endpoint = 'https://api.anthropic.com/v1'

    def test_token_and_get_models(self, token):
        """Test token validity and get available models"""
        headers = {
            'Authorization': f"Bearer {token}",
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
        }
        
        # List of known Claude models
        known_models = [
            'claude-3-opus-20240229',
            'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307',
            'claude-3-5-sonnet-20241022',
            'claude-3-5-haiku-20241022',
            'claude-2.1',
            'claude-2.0',
            'claude-instant-1.2'
        ]
        
        print("\nTesting token and checking available models...")
        
        # Test with a simple completion to verify token works
        test_data = {
            'model': 'claude-3-haiku-20240307',  # Use Haiku as it's most likely to be available
            'max_tokens': 10,
            'messages': [{'role': 'user', 'content': 'Hi'}]
        }
        
        try:
            if HAS_REQUESTS:
                response = requests.post(
                    f'{self.api_endpoint}/messages',
                    json=test_data,
                    headers=headers
                )
                if response.status_code == 401:
                    return False, "Invalid token (401 Unauthorized)", []
                elif response.status_code != 200:
                    return False, f"API error (status {response.status_code})", []
            else:
                # Use urllib
                req_data = json.dumps(test_data).encode('utf-8')
                req = urllib.request.Request(
                    f'{self.api_endpoint}/messages',
                    data=req_data,
                    headers=headers
                )
                try:
                    with urllib.request.urlopen(req) as response:
                        pass  # Token is valid
                except urllib.error.HTTPError as e:
                    if e.code == 401:
                        return False, "Invalid token (401 Unauthorized)", []
                    else:
                        return False, f"API error (status {e.code})", []
            
            # Token is valid, now test which models work
            available_models = []
            print("\nChecking available models...")
            
            for model in known_models:
                test_data['model'] = model
                try:
                    if HAS_REQUESTS:
                        response = requests.post(
                            f'{self.api_endpoint}/messages',
                            json=test_data,
                            headers=headers
                        )
                        if response.status_code == 200:
                            available_models.append(model)
                            print(f"  [OK] {model}")
                        else:
                            print(f"  [NO] {model} (status {response.status_code})")
                    else:
                        req_data = json.dumps(test_data).encode('utf-8')
                        req = urllib.request.Request(
                            f'{self.api_endpoint}/messages',
                            data=req_data,
                            headers=headers
                        )
                        try:
                            with urllib.request.urlopen(req) as response:
                                available_models.append(model)
                                print(f"  [OK] {model}")
                        except urllib.error.HTTPError as e:
                            print(f"  [NO] {model} (status {e.code})")
                except Exception as e:
                    print(f"  [NO] {model} (error: {str(e)})")
            
            if not available_models:
                return True, "Token is valid but no models are accessible", []
            
            return True, "Token is valid", available_models
            
        except Exception as e:
            return False, f"Error testing token: {str(e)}", []

    def select_default_model(self, available_models):
        """Let user select a default model"""
        print("\n=== Select Default Model ===\n")
        print("Available models:")
        for i, model in enumerate(available_models, 1):
            print(f"{i}. {model}")
        
        # Default to Claude 3 Opus if available, otherwise first in list
        default_choice = 1
        for i, model in enumerate(available_models, 1):
            if 'opus' in model:
                default_choice = i
                break
        
        print(f"\nEnter your choice (1-{len(available_models)}) [default: {default_choice}]: ", end='')
        choice = input().strip()
        
        if not choice:
            choice = str(default_choice)
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(available_models):
                return available_models[idx]
        except ValueError:
            pass
        
        print(f"\nInvalid choice, using default: {available_models[default_choice - 1]}")
        return available_models[default_choice - 1]

    def save_config(self, model):
        """Save selected model to config file"""
        config_file = Path('.config.json')
        if Path('/data').exists() and os.access('/data', os.W_OK):
            config_file = Path('/data/.config.json')
        
        config = {'default_model': model}
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\nDefault model '{model}' saved to config")

    def claude_cli_token_setup(self):
        """Setup using Claude CLI generated token"""
        print("This method uses a long-lived token generated by the Claude CLI.\n")
        print("Prerequisites:")
        print("1. Install Claude CLI: npm install -g @anthropic/claude-code")
        print("2. Run: claude setup-token")
        print("3. Copy the generated token (starts with sk-ant-oat01-)\n")
        
        token = input("Paste your Claude token here: ").strip()
        
        if not token:
            print("\nNo token provided")
            return False
        
        if not token.startswith('sk-ant-oat01-'):
            print("\nWarning: Token doesn't start with expected prefix 'sk-ant-oat01-'")
            cont = input("Continue anyway? (y/n): ").strip().lower()
            if cont != 'y':
                return False
        
        # Test token and get available models
        is_valid, message, available_models = self.test_token_and_get_models(token)
        
        if not is_valid:
            print(f"\nToken validation failed: {message}")
            return False
        
        print(f"\n{message}")
        
        # Save token using TokenManager
        manager = TokenManager()
        manager.setup_from_oauth_token(token)
        
        # Select default model if models are available
        if available_models:
            default_model = self.select_default_model(available_models)
            self.save_config(default_model)
        
        print("\nSetup complete!")
        print("Note: This token will need manual renewal when it expires.")
        return True

    def run(self):
        """Direct Claude CLI token setup"""
        print("\n=== Claude OAuth Setup ===\n")
        print("Due to Cloudflare protection, only Claude CLI tokens are supported.\n")
        
        # Go directly to Claude CLI token setup
        success = self.claude_cli_token_setup()
        
        if not success:
            print("\nSetup cancelled.")
            sys.exit(1)
        
        sys.exit(0)

def main():
    """Run headless OAuth setup"""
    setup = HeadlessOAuthSetup()
    setup.run()

if __name__ == '__main__':
    main()