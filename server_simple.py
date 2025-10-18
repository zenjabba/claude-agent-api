#!/usr/bin/env python3

import os
import sys
import json
import logging
import subprocess
import secrets
import sqlite3
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Configuration
PORT = int(os.environ.get('PORT', 8787))
TOKEN = os.environ.get('CLAUDE_CODE_OAUTH_TOKEN')
DB_PATH = Path('/data/claude_api.db') if Path('/data').exists() else Path('claude_api.db')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if not TOKEN:
    logger.error('Error: CLAUDE_CODE_OAUTH_TOKEN environment variable is not set')
    logger.error('Get token with: claude setup-token')
    logger.error('Then set: export CLAUDE_CODE_OAUTH_TOKEN=your-token')
    sys.exit(1)

# Initialize database
def init_db():
    """Initialize SQLite database with schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # API Keys table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            api_key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_used_at TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # Usage tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            query TEXT,
            model TEXT,
            session_id TEXT,
            duration_ms INTEGER,
            duration_api_ms INTEGER,
            num_turns INTEGER,
            total_cost_usd REAL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            cache_creation_input_tokens INTEGER,
            cache_read_input_tokens INTEGER,
            model_usage TEXT,
            FOREIGN KEY (api_key) REFERENCES api_keys(api_key)
        )
    ''')

    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_api_key ON usage(api_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage(timestamp)')

    conn.commit()
    conn.close()
    logger.info('Database initialized')

init_db()

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

# API Key management
def generate_api_key(name):
    """Generate a new API key"""
    api_key = f"sk-{secrets.token_urlsafe(32)}"
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO api_keys (api_key, name, created_at)
            VALUES (?, ?, ?)
        ''', (api_key, name, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return api_key
    except Exception as e:
        logger.error(f'Error creating API key: {e}')
        return None

def validate_api_key(api_key):
    """Validate an API key and update last used timestamp"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT api_key FROM api_keys
            WHERE api_key = ? AND is_active = 1
        ''', (api_key,))
        result = cursor.fetchone()

        if result:
            # Update last used timestamp
            cursor.execute('''
                UPDATE api_keys
                SET last_used_at = ?
                WHERE api_key = ?
            ''', (datetime.now().isoformat(), api_key))
            conn.commit()
            conn.close()
            return True

        conn.close()
        return False
    except Exception as e:
        logger.error(f'Error validating API key: {e}')
        return False

def list_api_keys():
    """List all API keys"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT api_key, name, created_at, last_used_at, is_active
            FROM api_keys
            ORDER BY created_at DESC
        ''')
        keys = {}
        for row in cursor.fetchall():
            keys[row[0]] = {
                'name': row[1],
                'created': row[2],
                'created_at': row[2],
                'last_used': row[3],
                'is_active': bool(row[4])
            }
        conn.close()
        return keys
    except Exception as e:
        logger.error(f'Error listing API keys: {e}')
        return {}

def delete_api_key(api_key):
    """Delete an API key (soft delete)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE api_keys
            SET is_active = 0
            WHERE api_key = ?
        ''', (api_key,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    except Exception as e:
        logger.error(f'Error deleting API key: {e}')
        return False

def log_usage(api_key, query, model, json_response):
    """Log usage statistics to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Extract usage data from JSON response
        usage = json_response.get('usage', {})

        cursor.execute('''
            INSERT INTO usage (
                api_key, timestamp, query, model, session_id,
                duration_ms, duration_api_ms, num_turns, total_cost_usd,
                input_tokens, output_tokens,
                cache_creation_input_tokens, cache_read_input_tokens,
                model_usage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            api_key,
            datetime.now().isoformat(),
            query[:500],  # Truncate long queries
            model,
            json_response.get('session_id'),
            json_response.get('duration_ms'),
            json_response.get('duration_api_ms'),
            json_response.get('num_turns'),
            json_response.get('total_cost_usd'),
            usage.get('input_tokens'),
            usage.get('output_tokens'),
            usage.get('cache_creation_input_tokens'),
            usage.get('cache_read_input_tokens'),
            json.dumps(json_response.get('modelUsage', {}))
        ))

        conn.commit()
        conn.close()
        logger.info(f'Usage logged for API key {api_key[:10]}...')
    except Exception as e:
        logger.error(f'Error logging usage: {e}')

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
        try:
            response = json.dumps(data)
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected before response was sent - ignore
            pass

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
        elif self.path.startswith('/usage'):
            self._handle_usage_report()
        elif self.path == '/':
            self._send_json_response(200, {
                'name': 'Claude Agent API',
                'version': '1.0.0',
                'endpoints': {
                    'GET /health': 'Health check',
                    'POST /query': 'Send queries to Claude (requires api_key)',
                    'GET /usage?api_key=XXX': 'View usage statistics'
                },
                'documentation': 'https://github.com/zenjabba/claude-agent-api'
            })
        else:
            self._send_json_response(404, {'error': 'Not found'})

    def do_HEAD(self):
        # Handle HEAD requests (used by monitoring tools)
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/query':
            self._handle_query()
        else:
            self._send_json_response(404, {'error': 'Not found'})

    def _handle_query(self):
        try:
            body = self._read_body()

            # Validate API key
            api_key = body.get('api_key')
            if not api_key:
                self._send_json_response(401, {'error': 'API key required', 'message': 'Include "api_key" in request body'})
                return

            if not validate_api_key(api_key):
                self._send_json_response(403, {'error': 'Invalid API key'})
                return

            prompt = body.get('query') or body.get('prompt')

            if not prompt:
                self._send_json_response(400, {'error': 'No prompt provided'})
                return

            logger.info(f"Processing query: {prompt[:100]}...")

            # Get model from request or use default
            model = body.get('model', DEFAULT_MODEL)

            # Use Claude CLI to process the query with JSON output
            env = os.environ.copy()
            env['CLAUDE_CODE_OAUTH_TOKEN'] = TOKEN

            # Run claude CLI with JSON output format for usage tracking
            result = subprocess.run(
                ['claude', '--print', '--output-format', 'json', '--model', model, prompt],
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

            # Parse JSON response
            try:
                json_response = json.loads(result.stdout.strip())

                # Log usage to database
                log_usage(api_key, prompt, model, json_response)

                # Extract the actual response text
                response_text = json_response.get('result', '')

                # Return response with optional usage data
                response_data = {
                    'response': response_text,
                    'usage': {
                        'total_cost_usd': json_response.get('total_cost_usd', 0),
                        'input_tokens': json_response.get('usage', {}).get('input_tokens', 0),
                        'output_tokens': json_response.get('usage', {}).get('output_tokens', 0),
                        'duration_ms': json_response.get('duration_ms', 0)
                    }
                }

                self._send_json_response(200, response_data)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                self._send_json_response(500, {
                    'error': 'Failed to parse response',
                    'details': str(e)
                })
                return

        except subprocess.TimeoutExpired:
            logger.error("Query timeout")
            self._send_json_response(500, {'error': 'Query timeout (120s)'})
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            self._send_json_response(500, {'error': str(e)})

    def _handle_usage_report(self):
        """Handle usage statistics endpoint"""
        try:
            # Parse query parameters for API key
            from urllib.parse import urlparse, parse_qs
            query_params = parse_qs(urlparse(self.path).query)
            api_key = query_params.get('api_key', [None])[0]

            if not api_key:
                self._send_json_response(401, {'error': 'API key required in query parameter'})
                return

            if not validate_api_key(api_key):
                self._send_json_response(403, {'error': 'Invalid API key'})
                return

            # Get usage statistics for this API key
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Summary statistics
            cursor.execute('''
                SELECT
                    COUNT(*) as total_requests,
                    SUM(total_cost_usd) as total_cost,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    AVG(duration_ms) as avg_duration_ms
                FROM usage
                WHERE api_key = ?
            ''', (api_key,))

            summary = cursor.fetchone()

            # Recent requests (last 10)
            cursor.execute('''
                SELECT timestamp, query, model, total_cost_usd,
                       input_tokens, output_tokens, duration_ms
                FROM usage
                WHERE api_key = ?
                ORDER BY timestamp DESC
                LIMIT 10
            ''', (api_key,))

            recent = []
            for row in cursor.fetchall():
                recent.append({
                    'timestamp': row[0],
                    'query': row[1][:100] if row[1] else '',
                    'model': row[2],
                    'cost_usd': row[3],
                    'input_tokens': row[4],
                    'output_tokens': row[5],
                    'duration_ms': row[6]
                })

            conn.close()

            self._send_json_response(200, {
                'api_key': api_key[:10] + '...',
                'summary': {
                    'total_requests': summary[0] or 0,
                    'total_cost_usd': round(summary[1] or 0, 4),
                    'total_input_tokens': summary[2] or 0,
                    'total_output_tokens': summary[3] or 0,
                    'avg_duration_ms': round(summary[4] or 0, 2)
                },
                'recent_requests': recent
            })

        except Exception as e:
            logger.error(f"Error generating usage report: {e}")
            self._send_json_response(500, {'error': str(e)})

    def log_message(self, format, *args):
        logger.info("%s - %s" % (self.address_string(), format % args))

def run_server():
    server_address = ('0.0.0.0', PORT)
    httpd = HTTPServer(server_address, ClaudeAPIHandler)

    logger.info(f"Claude Agent API server listening on http://0.0.0.0:{PORT}")
    logger.info(f"Using Claude CLI with OAuth token, model: {DEFAULT_MODEL}")
    logger.info(f"Database: {DB_PATH}")
    logger.info("Endpoints:")
    logger.info("  GET  /health - Health check")
    logger.info("  POST /query  - Send queries to Claude (with usage tracking)")
    logger.info("  GET  /usage?api_key=XXX - View usage statistics")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        httpd.server_close()

if __name__ == '__main__':
    run_server()
