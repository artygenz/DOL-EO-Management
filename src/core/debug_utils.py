"""
Debug Utilities for Environment Variables and Client Access

This module provides debugging tools to help identify and resolve
environment variable access issues and client connection problems.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from src.core.client_hub import get_client_hub

logger = logging.getLogger(__name__)


class EnvironmentDebugger:
    """Debug utility for environment variable issues."""
    
    def __init__(self):
        self.client_hub = get_client_hub()
    
    def check_required_env_vars(self) -> Dict[str, Any]:
        """Check if all required environment variables are present."""
        required_vars = {
            'database': ['POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB'],
            'redis': ['REDIS_HOST'],
            'openai': ['OPENAI_API_KEY'],
            'email_imap': ['IMAP_HOST', 'IMAP_USERNAME', 'IMAP_PASSWORD'],
            'email_smtp': ['SMTP_HOST', 'EMAIL_USER', 'EMAIL_PASS'],
            'aws': ['AWS_S3_BUCKET', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'],
            'app': ['JWT_SECRET']
        }
        
        results = {}
        for category, vars in required_vars.items():
            results[category] = {
                'missing': [],
                'present': [],
                'status': 'complete'
            }
            
            for var in vars:
                value = os.getenv(var)
                if value:
                    results[category]['present'].append(var)
                else:
                    results[category]['missing'].append(var)
                    results[category]['status'] = 'incomplete'
        
        return results
    
    def get_env_var_usage_report(self) -> Dict[str, Any]:
        """Generate a report of environment variable usage."""
        env_status = self.client_hub.get_env_status()
        client_health = self.client_hub.get_client_health()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'environment_variables': env_status,
            'client_health': client_health,
            'summary': {
                'total_env_vars': len([v for v in env_status['cached_vars'].values() if v is not None]),
                'healthy_clients': len([c for c in client_health.values() if c.get('is_healthy', False)]),
                'unhealthy_clients': len([c for c in client_health.values() if not c.get('is_healthy', False)])
            }
        }
    
    def diagnose_client_issues(self) -> List[Dict[str, Any]]:
        """Diagnose issues with client connections."""
        issues = []
        client_health = self.client_hub.get_client_health()
        
        for client_name, health in client_health.items():
            if not health.get('is_healthy', False):
                issue = {
                    'client': client_name,
                    'status': 'unhealthy',
                    'message': health.get('message', 'Unknown error'),
                    'error_count': health.get('error_count', 0),
                    'last_check': health.get('last_check'),
                    'suggestions': self._get_client_suggestions(client_name)
                }
                issues.append(issue)
        
        return issues
    
    def _get_client_suggestions(self, client_name: str) -> List[str]:
        """Get suggestions for fixing client issues."""
        suggestions = {
            'db_engine': [
                "Check POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB",
                "Verify database server is running and accessible",
                "Check network connectivity to database host"
            ],
            'redis_client': [
                "Check REDIS_HOST, REDIS_PORT environment variables",
                "Verify Redis server is running",
                "Check network connectivity to Redis host"
            ],
            'openai_client': [
                "Check OPENAI_API_KEY environment variable",
                "Verify API key is valid and has sufficient credits",
                "Check OpenAI service status"
            ],
            'langchain_client': [
                "Check OPENAI_API_KEY and OPENAI_MODEL environment variables",
                "Verify LangChain dependencies are installed",
                "Check OpenAI API connectivity"
            ],
            'imap_client': [
                "Check IMAP_HOST, IMAP_PORT, IMAP_USERNAME, IMAP_PASSWORD",
                "Verify IMAP server is accessible",
                "Check email credentials are correct"
            ],
            'smtp_client': [
                "Check SMTP_HOST, SMTP_PORT, EMAIL_USER, EMAIL_PASS",
                "Verify SMTP server is accessible",
                "Check email credentials and authentication"
            ],
            's3_client': [
                "Check AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION",
                "Verify AWS credentials are valid",
                "Check S3 bucket exists and is accessible"
            ],
            'celery_app': [
                "Check CELERY_BROKER_URL, CELERY_RESULT_BACKEND",
                "Verify Redis is running for Celery broker",
                "Check Celery dependencies are installed"
            ]
        }
        
        return suggestions.get(client_name, ["Check client configuration and dependencies"])
    
    def test_all_clients(self) -> Dict[str, Any]:
        """Test all clients and return results."""
        results = {}
        
        # Test database
        try:
            engine = self.client_hub.get_database_engine()
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            results['database'] = {'status': 'success', 'message': 'Connected successfully'}
        except Exception as e:
            results['database'] = {'status': 'error', 'message': str(e)}
        
        # Test Redis
        try:
            redis_client = self.client_hub.get_redis_client()
            redis_client.ping()
            results['redis'] = {'status': 'success', 'message': 'Connected successfully'}
        except Exception as e:
            results['redis'] = {'status': 'error', 'message': str(e)}
        
        # Test OpenAI
        try:
            openai_client = self.client_hub.get_openai_client()
            if openai_client:
                # Simple test - just check if client is initialized
                results['openai'] = {'status': 'success', 'message': 'Client initialized'}
            else:
                results['openai'] = {'status': 'warning', 'message': 'Client not available (missing API key)'}
        except Exception as e:
            results['openai'] = {'status': 'error', 'message': str(e)}
        
        # Test IMAP (if credentials available)
        try:
            if os.getenv('IMAP_USERNAME') and os.getenv('IMAP_PASSWORD'):
                imap_client = self.client_hub.get_imap_client()
                if imap_client:
                    results['imap'] = {'status': 'success', 'message': 'Connected successfully'}
                else:
                    results['imap'] = {'status': 'warning', 'message': 'Client not available'}
            else:
                results['imap'] = {'status': 'skipped', 'message': 'IMAP credentials not provided'}
        except Exception as e:
            results['imap'] = {'status': 'error', 'message': str(e)}
        
        # Test SMTP (if credentials available)
        try:
            if os.getenv('EMAIL_USER') and os.getenv('EMAIL_PASS'):
                smtp_client = self.client_hub.get_smtp_client()
                if smtp_client:
                    results['smtp'] = {'status': 'success', 'message': 'Connected successfully'}
                else:
                    results['smtp'] = {'status': 'warning', 'message': 'Client not available'}
            else:
                results['smtp'] = {'status': 'skipped', 'message': 'SMTP credentials not provided'}
        except Exception as e:
            results['smtp'] = {'status': 'error', 'message': str(e)}
        
        # Test S3 (if credentials available)
        try:
            if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
                s3_client = self.client_hub.get_s3_client()
                if s3_client:
                    results['s3'] = {'status': 'success', 'message': 'Client initialized'}
                else:
                    results['s3'] = {'status': 'warning', 'message': 'Client not available'}
            else:
                results['s3'] = {'status': 'skipped', 'message': 'AWS credentials not provided'}
        except Exception as e:
            results['s3'] = {'status': 'error', 'message': str(e)}
        
        return results


def debug_environment_setup() -> Dict[str, Any]:
    """Main debugging function for environment setup."""
    debugger = EnvironmentDebugger()
    
    return {
        'timestamp': datetime.now().isoformat(),
        'required_vars_check': debugger.check_required_env_vars(),
        'usage_report': debugger.get_env_var_usage_report(),
        'client_issues': debugger.diagnose_client_issues(),
        'client_tests': debugger.test_all_clients()
    }


def print_debug_report():
    """Print a formatted debug report to console."""
    report = debug_environment_setup()
    
    print("\n" + "="*80)
    print("ENVIRONMENT VARIABLES AND CLIENT DEBUG REPORT")
    print("="*80)
    print(f"Generated at: {report['timestamp']}")
    
    # Required variables check
    print("\n📋 REQUIRED ENVIRONMENT VARIABLES CHECK:")
    print("-" * 50)
    for category, status in report['required_vars_check'].items():
        status_icon = "✅" if status['status'] == 'complete' else "❌"
        print(f"{status_icon} {category.upper()}: {status['status']}")
        if status['missing']:
            print(f"   Missing: {', '.join(status['missing'])}")
        if status['present']:
            print(f"   Present: {', '.join(status['present'])}")
    
    # Client health
    print("\n🔧 CLIENT HEALTH STATUS:")
    print("-" * 50)
    client_health = report['usage_report']['client_health']
    for client, health in client_health.items():
        status_icon = "✅" if health.get('is_healthy', False) else "❌"
        print(f"{status_icon} {client}: {health.get('message', 'Unknown')}")
    
    # Client tests
    print("\n🧪 CLIENT CONNECTION TESTS:")
    print("-" * 50)
    for client, test_result in report['client_tests'].items():
        status_icon = {
            'success': "✅",
            'error': "❌", 
            'warning': "⚠️",
            'skipped': "⏭️"
        }.get(test_result['status'], "❓")
        print(f"{status_icon} {client}: {test_result['message']}")
    
    # Issues
    if report['client_issues']:
        print("\n🚨 IDENTIFIED ISSUES:")
        print("-" * 50)
        for issue in report['client_issues']:
            print(f"❌ {issue['client']}: {issue['message']}")
            if issue['suggestions']:
                print("   Suggestions:")
                for suggestion in issue['suggestions']:
                    print(f"   - {suggestion}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    print_debug_report()
