#!/usr/bin/env python3

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Configuration
PORT = int(os.environ.get('PORT', 8787))
TOKEN = os.environ.get('CLAUDE_CODE_OAUTH_TOKEN')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if not TOKEN:
    logger.error('Error: CLAUDE_CODE_OAUTH_TOKEN environment variable is not set')
    logger.error('Get token with: claude setup-token')
    logger.error('Then set: export CLAUDE_CODE_OAUTH_TOKEN=your-token')
    sys.exit(1)

# Configure Claude CLI with OAuth token
def configure_claude_cli():
    """Configure Claude CLI with OAuth token"""
    try:
        # Set up the token in Claude CLI's config
        config_dir = Path.home() / '.claude' / 'config'
        config_dir.mkdir(parents=True, exist_ok=True)

        config_file = config_dir / 'auth.json'
        config_data = {
            'oauth': {
                'access_token': TOKEN,
                'token_type': 'bearer'
            }
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        logger.info('Claude CLI configured with OAuth token')
        return True
    except Exception as e:
        logger.error(f'Failed to configure Claude CLI: {e}')
        return False

# Configure on startup
configure_claude_cli()

# Load default model from config
DEFAULT_MODEL = 'claude-haiku-4-5'
config_file = Path('/data/.config.json') if Path('/data').exists() else Path('.config.json')
if config_file.exists():
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            DEFAULT_MODEL = config.get('default_model', DEFAULT_MODEL)
            logger.info(f'Loaded default model: {DEFAULT_MODEL}')
    except Exception as e:
        logger.warning(f'Could not load config: {e}')

class ClaudeAPIHandler(BaseHTTPRequestHandler):
    def _send_json_response(self, status_code, data):
        response = json.dumps(data)
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def _read_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        if self.path == '/health':
            self._send_json_response(200, {
                'status': 'healthy',
                'hasToken': bool(TOKEN),
                'timestamp': datetime.now().isoformat()
            })
        else:
            self._send_json_response(404, {'error': 'Not found'})

    def do_POST(self):
        if self.path == '/query':
            self._handle_query()
        else:
            self._send_json_response(404, {'error': 'Not found'})

    def _handle_query(self):
        try:
            body = self._read_body()
            prompt = body.get('query') or body.get('prompt')

            if not prompt:
                self._send_json_response(400, {'error': 'No prompt provided'})
                return

            logger.info(f"Processing query: {prompt[:100]}...")

            # Get model from request or use default
            model = body.get('model', DEFAULT_MODEL)

            # Use Claude CLI to process the query
            env = os.environ.copy()
            env['CLAUDE_CODE_OAUTH_TOKEN'] = TOKEN

            # Run claude CLI with the prompt in non-interactive mode
            result = subprocess.run(
                ['claude', '--print', '--model', model, prompt],
                env=env,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                logger.error(f"Claude CLI error: {result.stderr}")
                self._send_json_response(500, {
                    'error': 'Claude CLI error',
                    'details': result.stderr
                })
                return

            # Extract response
            response_text = result.stdout.strip()

            self._send_json_response(200, {
                'response': response_text
            })

        except subprocess.TimeoutExpired:
            logger.error("Query timeout")
            self._send_json_response(500, {'error': 'Query timeout (120s)'})
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            self._send_json_response(500, {'error': str(e)})

    def log_message(self, format, *args):
        logger.info("%s - %s" % (self.address_string(), format % args))

def run_server():
    server_address = ('0.0.0.0', PORT)
    httpd = HTTPServer(server_address, ClaudeAPIHandler)

    logger.info(f"Claude Agent API server listening on http://0.0.0.0:{PORT}")
    logger.info(f"Using Claude CLI with OAuth token, model: {DEFAULT_MODEL}")
    logger.info("Endpoints:")
    logger.info("  GET  /health - Health check")
    logger.info("  POST /query  - Send queries to Claude")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        httpd.server_close()

if __name__ == '__main__':
    run_server()
