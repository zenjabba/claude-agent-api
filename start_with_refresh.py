#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import threading
import signal
from pathlib import Path

# Add script directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from token_manager import TokenManager

class ServerManager:
    def __init__(self):
        self.token_manager = TokenManager()
        self.server_process = None
        self.refresh_thread = None
        self.shutdown_event = threading.Event()

    def refresh_token_periodically(self):
        """Background thread to refresh token every 45 minutes"""
        while not self.shutdown_event.is_set():
            # Wait 45 minutes or until shutdown
            if self.shutdown_event.wait(45 * 60):
                break
            
            try:
                print("Checking token validity...")
                self.token_manager.ensure_valid_token()
                print("Token refresh check complete")
            except Exception as e:
                print(f"Failed to refresh token: {e}")
                # Don't exit - let the server continue with current token

    def start_server(self):
        """Start the main server"""
        # Check and refresh token if needed
        try:
            self.token_manager.ensure_valid_token()
            print("Token is valid, starting server...")
        except Exception as e:
            print(f"Failed to ensure valid token: {e}")
            print("Please run initial OAuth setup or provide valid refresh token")
            sys.exit(1)

        # Start the refresh thread
        self.refresh_thread = threading.Thread(target=self.refresh_token_periodically)
        self.refresh_thread.daemon = True
        self.refresh_thread.start()

        # Start the main server
        env = os.environ.copy()
        
        # Load environment from .vars file
        # Use /data directory if it exists (Docker), otherwise use script directory
        if Path('/data').exists() and os.access('/data', os.W_OK):
            vars_file = Path('/data') / '.vars'
        else:
            vars_file = Path(__file__).parent / '.vars'
        
        if vars_file.exists():
            with open(vars_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env[key] = value

        try:
            self.server_process = subprocess.Popen(
                [sys.executable, 'server.py'],
                env=env,
                cwd=Path(__file__).parent
            )
            
            # Wait for server process
            self.server_process.wait()
            
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        self.shutdown_event.set()
        
        if self.server_process and self.server_process.poll() is None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
        
        if self.refresh_thread and self.refresh_thread.is_alive():
            self.refresh_thread.join(timeout=5)

    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)

def main():
    """Main entry point"""
    manager = ServerManager()
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, manager.handle_signal)
    signal.signal(signal.SIGINT, manager.handle_signal)
    
    try:
        manager.start_server()
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()