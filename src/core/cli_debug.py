#!/usr/bin/env python3
"""
CLI Debug Tool for Environment Variables and Client Access

This script provides command-line tools to debug environment variable
access issues and client connection problems.
"""

import sys
import argparse
import json
from typing import Dict, Any
from src.core.debug_utils import debug_environment_setup, print_debug_report
from src.core.migration_guide import print_migration_guide
from src.core.client_hub import get_client_hub


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Debug environment variables and client connections"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Debug command
    debug_parser = subparsers.add_parser('debug', help='Debug environment and clients')
    debug_parser.add_argument(
        '--format', 
        choices=['console', 'json'], 
        default='console',
        help='Output format (default: console)'
    )
    debug_parser.add_argument(
        '--output',
        help='Output file (for JSON format)'
    )
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test client connections')
    test_parser.add_argument(
        '--client',
        choices=['database', 'redis', 'openai', 'imap', 'smtp', 's3', 'celery', 'all'],
        default='all',
        help='Client to test (default: all)'
    )
    
    # Health command
    health_parser = subparsers.add_parser('health', help='Check client health')
    health_parser.add_argument(
        '--format',
        choices=['console', 'json'],
        default='console',
        help='Output format (default: console)'
    )
    
    # Migration command
    migration_parser = subparsers.add_parser('migration', help='Show migration guide')
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset client connections')
    reset_parser.add_argument(
        '--client',
        help='Specific client to reset (or all if not specified)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'debug':
        handle_debug_command(args)
    elif args.command == 'test':
        handle_test_command(args)
    elif args.command == 'health':
        handle_health_command(args)
    elif args.command == 'migration':
        handle_migration_command(args)
    elif args.command == 'reset':
        handle_reset_command(args)
    else:
        parser.print_help()


def handle_debug_command(args):
    """Handle debug command."""
    report = debug_environment_setup()
    
    if args.format == 'json':
        output = json.dumps(report, indent=2)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Debug report saved to {args.output}")
        else:
            print(output)
    else:
        print_debug_report()


def handle_test_command(args):
    """Handle test command."""
    client_hub = get_client_hub()
    
    if args.client == 'all':
        test_all_clients(client_hub)
    else:
        test_specific_client(client_hub, args.client)


def test_all_clients(client_hub):
    """Test all clients."""
    print("🧪 Testing all clients...")
    print("-" * 50)
    
    clients = {
        'database': lambda: client_hub.get_database_engine(),
        'redis': lambda: client_hub.get_redis_client(),
        'openai': lambda: client_hub.get_openai_client(),
        'imap': lambda: client_hub.get_imap_client(),
        'smtp': lambda: client_hub.get_smtp_client(),
        's3': lambda: client_hub.get_s3_client(),
        'celery': lambda: client_hub.get_celery_app()
    }
    
    for name, get_client in clients.items():
        try:
            client = get_client()
            if client:
                print(f"✅ {name}: Client initialized successfully")
            else:
                print(f"⚠️  {name}: Client not available (missing credentials)")
        except Exception as e:
            print(f"❌ {name}: {e}")


def test_specific_client(client_hub, client_name):
    """Test a specific client."""
    print(f"🧪 Testing {client_name} client...")
    print("-" * 50)
    
    try:
        if client_name == 'database':
            from sqlalchemy import text
            engine = client_hub.get_database_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print("✅ Database: Connection successful")
        elif client_name == 'redis':
            redis_client = client_hub.get_redis_client()
            redis_client.ping()
            print("✅ Redis: Connection successful")
        elif client_name == 'openai':
            client = client_hub.get_openai_client()
            if client:
                print("✅ OpenAI: Client initialized")
            else:
                print("⚠️  OpenAI: Client not available")
        elif client_name == 'imap':
            client = client_hub.get_imap_client()
            if client:
                print("✅ IMAP: Client initialized")
            else:
                print("⚠️  IMAP: Client not available")
        elif client_name == 'smtp':
            # Test both cached and fresh SMTP connections
            cached_client = client_hub.get_smtp_client()
            fresh_client = client_hub.create_smtp_connection()
            
            if cached_client and fresh_client:
                print("✅ SMTP: Both cached and fresh connections working")
                fresh_client.quit()  # Close the test connection
            elif cached_client:
                print("✅ SMTP: Cached client available")
            elif fresh_client:
                print("✅ SMTP: Fresh connection working")
                fresh_client.quit()
            else:
                print("⚠️  SMTP: Client not available")
        elif client_name == 's3':
            client = client_hub.get_s3_client()
            if client:
                print("✅ S3: Client initialized")
            else:
                print("⚠️  S3: Client not available")
        elif client_name == 'celery':
            app = client_hub.get_celery_app()
            if app:
                print("✅ Celery: App initialized")
            else:
                print("⚠️  Celery: App not available")
        else:
            print(f"❌ Unknown client: {client_name}")
            
    except Exception as e:
        print(f"❌ {client_name}: {e}")


def handle_health_command(args):
    """Handle health command."""
    client_hub = get_client_hub()
    health = client_hub.get_client_health()
    
    if args.format == 'json':
        output = json.dumps(health, indent=2)
        print(output)
    else:
        print("🏥 Client Health Status:")
        print("-" * 50)
        for client, status in health.items():
            icon = "✅" if status.get('is_healthy', False) else "❌"
            print(f"{icon} {client}: {status.get('message', 'Unknown')}")
            if not status.get('is_healthy', False):
                print(f"   Error count: {status.get('error_count', 0)}")
                print(f"   Last check: {status.get('last_check', 'Never')}")


def handle_migration_command(args):
    """Handle migration command."""
    print_migration_guide()


def handle_reset_command(args):
    """Handle reset command."""
    client_hub = get_client_hub()
    
    if args.client:
        client_hub.reset_client(args.client)
        print(f"🔄 Reset {args.client} client")
    else:
        client_hub.reset_all_clients()
        print("🔄 Reset all clients")


if __name__ == "__main__":
    main()
