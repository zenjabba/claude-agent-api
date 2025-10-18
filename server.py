#!/usr/bin/env python3

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

# Try to import anthropic, provide instructions if not available
try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not installed")
    print("Please run: pip3 install anthropic")
    sys.exit(1)

# Configuration
PORT = int(os.environ.get('PORT', 8787))
TOKEN = os.environ.get('CLAUDE_CODE_OAUTH_TOKEN')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if not TOKEN:
    logger.error('Error: CLAUDE_CODE_OAUTH_TOKEN environment variable is not set')
    sys.exit(1)

# Load default model from config
DEFAULT_MODEL = 'claude-3-opus-20240229'
config_file = Path('/data/.config.json') if Path('/data').exists() else Path('.config.json')
if config_file.exists():
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            DEFAULT_MODEL = config.get('default_model', DEFAULT_MODEL)
            logger.info(f'Loaded default model from config: {DEFAULT_MODEL}')
    except Exception as e:
        logger.warning(f'Could not load config: {e}')

# Initialize Claude client
anthropic = Anthropic(api_key=TOKEN)

class ClaudeAPIHandler(BaseHTTPRequestHandler):
    def _send_json_response(self, status_code, data):
        """Send JSON response"""
        response = json.dumps(data)
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def _read_body(self):
        """Read and parse JSON body"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self._send_json_response(200, {
                'status': 'healthy',
                'hasToken': bool(TOKEN),
                'timestamp': datetime.now().isoformat()
            })
        else:
            self._send_json_response(404, {'error': 'Not found'})

    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/query':
            self._handle_query()
        elif self.path == '/execute':
            self._handle_execute()
        else:
            self._send_json_response(404, {'error': 'Not found'})

    def _handle_query(self):
        """Handle query endpoint"""
        try:
            body = self._read_body()
            prompt = body.get('query') or body.get('prompt')
            
            if not prompt:
                self._send_json_response(400, {'error': 'No prompt provided'})
                return
            
            logger.info(f"Processing query: {prompt}")
            
            # Get model from request or use default
            model = body.get('model', DEFAULT_MODEL)
            
            # Call Claude API
            message = anthropic.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }]
            )
            
            # Extract text response
            response_text = message.content[0].text
            
            self._send_json_response(200, {
                'response': response_text,
                'usage': {
                    'input_tokens': message.usage.input_tokens,
                    'output_tokens': message.usage.output_tokens
                }
            })
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            self._send_json_response(500, {
                'error': str(e),
                'details': str(e)
            })

    def _handle_execute(self):
        """Handle execute endpoint"""
        try:
            body = self._read_body()
            command = body.get('command')
            
            if not command:
                self._send_json_response(400, {'error': 'No command provided'})
                return
            
            logger.info(f"Executing command: {command}")
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            self._send_json_response(200, {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exitCode': result.returncode
            })
            
        except subprocess.TimeoutExpired:
            self._send_json_response(500, {
                'error': 'Command timeout',
                'stdout': '',
                'stderr': 'Command exceeded 30 second timeout',
                'exitCode': -1
            })
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            self._send_json_response(500, {
                'error': str(e),
                'stdout': '',
                'stderr': str(e),
                'exitCode': 1
            })

    def log_message(self, format, *args):
        """Override to use logger instead of stderr"""
        logger.info("%s - %s" % (self.address_string(), format % args))

def run_server():
    """Start the HTTP server"""
    server_address = ('0.0.0.0', PORT)
    httpd = HTTPServer(server_address, ClaudeAPIHandler)
    
    logger.info(f"Claude Agent server listening on http://0.0.0.0:{PORT}")
    logger.info("Endpoints:")
    logger.info("  GET  /health - Health check")
    logger.info("  POST /query  - Send queries to Claude")
    logger.info("  POST /execute - Execute system commands")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        httpd.server_close()

if __name__ == '__main__':
    run_server()