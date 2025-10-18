#!/usr/bin/env python3

import sys
import json
from pathlib import Path

# Import functions from server_simple
sys.path.insert(0, str(Path(__file__).parent))
from server_simple import generate_api_key, list_api_keys, delete_api_key

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 manage_keys.py create <name>    - Create new API key")
        print("  python3 manage_keys.py list              - List all API keys")
        print("  python3 manage_keys.py delete <api_key>  - Delete an API key")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'create':
        if len(sys.argv) < 3:
            print("Error: Name required")
            print("Usage: python3 manage_keys.py create <name>")
            sys.exit(1)

        name = sys.argv[2]
        api_key = generate_api_key(name)
        if api_key:
            print(f"\nAPI Key created successfully!")
            print(f"Name: {name}")
            print(f"Key:  {api_key}")
            print(f"\nKeep this key secure - it won't be shown again!")
        else:
            print("Error: Failed to create API key")
            sys.exit(1)

    elif command == 'list':
        keys = list_api_keys()
        if not keys:
            print("No API keys found")
        else:
            print(f"\n{'API Key':<50} {'Name':<20} {'Created':<25} {'Last Used':<25}")
            print("-" * 120)
            for key, info in keys.items():
                masked_key = key[:10] + '...' + key[-8:]
                last_used = info.get('last_used', 'Never')
                print(f"{masked_key:<50} {info['name']:<20} {info['created']:<25} {last_used:<25}")
            print(f"\nTotal: {len(keys)} API key(s)")

    elif command == 'delete':
        if len(sys.argv) < 3:
            print("Error: API key required")
            print("Usage: python3 manage_keys.py delete <api_key>")
            sys.exit(1)

        api_key = sys.argv[2]
        if delete_api_key(api_key):
            print(f"API key deleted successfully")
        else:
            print(f"Error: API key not found")
            sys.exit(1)

    else:
        print(f"Error: Unknown command '{command}'")
        print("Valid commands: create, list, delete")
        sys.exit(1)

if __name__ == '__main__':
    main()
