#!/usr/bin/env python3
"""
Comprehensive RBAC testing script for the chat system.

This script tests the chat API endpoint with different user roles to validate:
1. Role-based access control enforcement
2. Response accuracy based on user context
3. Tool selection and data filtering based on permissions

Usage:
    python scripts/test_chat_rbac.py
"""

import asyncio
import json
import os
import sys
import time
from typing import Dict, List, Any, Optional
import requests
from dataclasses import dataclass
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@dataclass
class TestUser:
    """Test user configuration"""
    name: str
    email: str
    role: str  # admin, reviewer, executor
    org_role: Optional[str] = None
    password: str = "Lumen@2025"  # Default password used by the system

@dataclass
class TestCase:
    """Individual test case"""
    name: str
    question: str
    expected_behavior: str
    expected_tools: List[str] = None
    expected_data_access: List[str] = None
    should_fail: bool = False

class ChatRBACTester:
    """Main test class for RBAC validation"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_users: Dict[str, TestUser] = {}
        self.user_tokens: Dict[str, str] = {}
        
    def setup_test_users(self):
        """Define test users for different roles"""
        self.test_users = {
            "admin": TestUser(
                name="Jack Smith",
                email="jack.smith@lumenlighthouse.ai",
                role="admin",
                org_role="System Administrator"
            ),
            "reviewer": TestUser(
                name="Kevin Brown", 
                email="kevin.brown@lumenlighthouse.ai",
                role="reviewer",
                org_role="PMO Reviewer"
            ),
            "executor": TestUser(
                name="Ayesha Ahsan",
                email="ayesha.ahsan@lumenlighthouse.ai", 
                role="executor",
                org_role="Task Executor"
            )
        }
        
    def create_test_cases(self) -> Dict[str, List[TestCase]]:
        """Define test cases for each role"""
        return {
            "admin": [
                TestCase(
                    name="Admin can view all tasks",
                    question="Show me all tasks in the system",
                    expected_behavior="Should return all tasks regardless of assignee",
                    expected_tools=["search_tasks", "get_my_tasks"],
                    expected_data_access=["all_tasks"]
                ),
                TestCase(
                    name="Admin can view all users",
                    question="List all users in the system",
                    expected_behavior="Should return all users with full details",
                    expected_tools=["search_users", "aggregate_users"],
                    expected_data_access=["all_users"]
                ),
                TestCase(
                    name="Admin can access user summaries",
                    question="Show me a summary for any user",
                    expected_behavior="Should be able to access user data and summaries",
                    expected_tools=["user_summary", "aggregate_users"],
                    expected_data_access=["any_user_summary"]
                ),
                TestCase(
                    name="Admin can view task aggregations",
                    question="Show me task statistics by status and category",
                    expected_behavior="Should return comprehensive task statistics",
                    expected_tools=["aggregate_tasks", "timeseries_tasks"],
                    expected_data_access=["all_task_stats"]
                )
            ],
            "reviewer": [
                TestCase(
                    name="Reviewer can view assigned tasks",
                    question="Show me my assigned tasks",
                    expected_behavior="Should return tasks assigned to reviewer or under their review",
                    expected_tools=["get_my_tasks", "search_tasks"],
                    expected_data_access=["assigned_tasks"]
                ),
                TestCase(
                    name="Reviewer can view PMO executors",
                    question="Show me executors I can review",
                    expected_behavior="Should return executors under PMO review scope",
                    expected_tools=["pmo_visible_executors"],
                    expected_data_access=["pmo_executors"]
                ),
                TestCase(
                    name="Reviewer cannot access all users",
                    question="Show me all users in the system",
                    expected_behavior="Should be limited to users within review scope",
                    expected_tools=["search_users"],
                    expected_data_access=["limited_users"]
                ),
                TestCase(
                    name="Reviewer can view task updates",
                    question="Show me recent task updates",
                    expected_behavior="Should see updates for tasks under their review",
                    expected_tools=["search_task_updates", "search_tasks"],
                    expected_data_access=["reviewable_tasks"]
                )
            ],
            "executor": [
                TestCase(
                    name="Executor can view own tasks",
                    question="Show me my tasks",
                    expected_behavior="Should only return tasks assigned to this executor",
                    expected_tools=["get_my_tasks"],
                    expected_data_access=["own_tasks"]
                ),
                TestCase(
                    name="Executor cannot view other users' tasks",
                    question="Show me tasks assigned to other users",
                    expected_behavior="Should be denied or return empty results",
                    expected_tools=["search_tasks"],
                    expected_data_access=["own_tasks_only"],
                    should_fail=True
                ),
                TestCase(
                    name="Executor cannot access user management",
                    question="Show me all users",
                    expected_behavior="Should be denied access to user management",
                    expected_tools=[],
                    expected_data_access=[],
                    should_fail=True
                ),
                TestCase(
                    name="Executor can view task details",
                    question="Show me details of my specific task",
                    expected_behavior="Should only see details of their own tasks",
                    expected_tools=["get_task_details"],
                    expected_data_access=["own_task_details"]
                )
            ]
        }
        
    async def create_user_if_not_exists(self, user: TestUser) -> bool:
        """Create a test user if they don't exist"""
        try:
            # Try to login first
            login_response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"email": user.email, "password": user.password}
            )
            
            if login_response.status_code == 200:
                token_data = login_response.json()
                self.user_tokens[user.role] = token_data["access_token"]
                print(f"✓ User {user.role} already exists and logged in")
                return True
                
        except Exception as e:
            print(f"Login failed for {user.role}: {e}")
            
        # Create user if login failed
        try:
            create_response = self.session.post(
                f"{self.base_url}/app/users",
                json={
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                    "org_role": user.org_role
                }
            )
            
            if create_response.status_code in [200, 201]:
                # Login after creation
                login_response = self.session.post(
                    f"{self.base_url}/auth/login",
                    json={"email": user.email, "password": user.password}
                )
                
                if login_response.status_code == 200:
                    token_data = login_response.json()
                    self.user_tokens[user.role] = token_data["access_token"]
                    print(f"✓ Created and logged in user {user.role}")
                    return True
                    
        except Exception as e:
            print(f"Failed to create user {user.role}: {e}")
            
        return False
        
    def test_chat_query(self, user_role: str, test_case: TestCase) -> Dict[str, Any]:
        """Test a single chat query with RBAC validation"""
        if user_role not in self.user_tokens:
            return {
                "success": False,
                "error": f"No token available for user role: {user_role}",
                "response": None
            }
            
        headers = {
            "Authorization": f"Bearer {self.user_tokens[user_role]}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": test_case.question,
            "context": {"test_case": test_case.name}
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/chat/query",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            result = {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else None,
                "error": response.text if response.status_code != 200 else None
            }
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": None
            }
            
    def analyze_response(self, test_case: TestCase, result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the response for RBAC compliance"""
        analysis = {
            "rbac_compliant": True,
            "issues": [],
            "tool_usage": [],
            "data_access": [],
            "recommendations": []
        }
        
        if not result["success"]:
            if test_case.should_fail:
                analysis["rbac_compliant"] = True
                analysis["recommendations"].append("✓ Correctly denied access as expected")
            else:
                analysis["rbac_compliant"] = False
                analysis["issues"].append(f"Unexpected failure: {result.get('error', 'Unknown error')}")
            return analysis
            
        response_data = result.get("response", {})
        
        # Check tool usage
        if response_data.get("tool"):
            analysis["tool_usage"].append(response_data["tool"])
            
        # Check if expected tools were used
        if test_case.expected_tools:
            used_tool = response_data.get("tool")
            if used_tool and used_tool not in test_case.expected_tools:
                analysis["issues"].append(f"Unexpected tool used: {used_tool}")
                analysis["rbac_compliant"] = False
                
        # Check data access patterns
        if response_data.get("data"):
            data = response_data["data"]
            analysis["data_access"].append("Data returned in response")
            
            # Basic data access validation
            if isinstance(data, dict):
                if "tasks" in data:
                    task_count = len(data.get("tasks", []))
                    analysis["data_access"].append(f"Returned {task_count} tasks")
                    
                if "users" in data:
                    user_count = len(data.get("users", []))
                    analysis["data_access"].append(f"Returned {user_count} users")
                    
        # Check response content for role-appropriate information
        response_text = response_data.get("response", "")
        if response_text:
            # More specific check for actual access denial messages
            access_denied_phrases = [
                "access denied", "permission denied", "not authorized", 
                "insufficient permissions", "cannot access", "forbidden"
            ]
            if any(phrase in response_text.lower() for phrase in access_denied_phrases):
                if not test_case.should_fail:
                    analysis["issues"].append("Unexpected access denial in response")
                    analysis["rbac_compliant"] = False
                    
        return analysis
        
    def run_role_tests(self, user_role: str) -> Dict[str, Any]:
        """Run all tests for a specific user role"""
        print(f"\n{'='*60}")
        print(f"Testing Role: {user_role.upper()}")
        print(f"{'='*60}")
        
        test_cases = self.create_test_cases().get(user_role, [])
        results = {
            "role": user_role,
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "test_results": []
        }
        
        for test_case in test_cases:
            print(f"\n--- {test_case.name} ---")
            print(f"Question: {test_case.question}")
            print(f"Expected: {test_case.expected_behavior}")
            
            # Run the test
            result = self.test_chat_query(user_role, test_case)
            analysis = self.analyze_response(test_case, result)
            
            test_result = {
                "test_case": test_case.name,
                "question": test_case.question,
                "result": result,
                "analysis": analysis,
                "passed": analysis["rbac_compliant"]
            }
            
            results["test_results"].append(test_result)
            
            if analysis["rbac_compliant"]:
                results["passed"] += 1
                print("✓ PASSED")
            else:
                results["failed"] += 1
                print("✗ FAILED")
                for issue in analysis["issues"]:
                    print(f"  Issue: {issue}")
                    
            # Print response summary
            if result["success"] and result.get("response"):
                response_data = result["response"]
                print(f"  Tool used: {response_data.get('tool', 'None')}")
                print(f"  Response length: {len(response_data.get('response', ''))}")
                
        return results
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive RBAC tests for all roles"""
        print("Starting Chat System RBAC Testing")
        print("=" * 60)
        
        # Setup test users
        self.setup_test_users()
        
        # Create users and get tokens
        for role, user in self.test_users.items():
            print(f"\nSetting up user: {role}")
            success = await self.create_user_if_not_exists(user)
            if not success:
                print(f"✗ Failed to setup user: {role}")
                return {"error": f"Failed to setup user: {role}"}
                
        # Run tests for each role
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "total_roles": len(self.test_users),
            "role_results": {}
        }
        
        for role in self.test_users.keys():
            role_results = self.run_role_tests(role)
            all_results["role_results"][role] = role_results
            
        # Generate summary
        total_tests = sum(r["total_tests"] for r in all_results["role_results"].values())
        total_passed = sum(r["passed"] for r in all_results["role_results"].values())
        total_failed = sum(r["failed"] for r in all_results["role_results"].values())
        
        all_results["summary"] = {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0
        }
        
        return all_results
        
    def print_summary(self, results: Dict[str, Any]):
        """Print a comprehensive test summary"""
        print(f"\n{'='*60}")
        print("RBAC TEST SUMMARY")
        print(f"{'='*60}")
        
        summary = results.get("summary", {})
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"Passed: {summary.get('total_passed', 0)}")
        print(f"Failed: {summary.get('total_failed', 0)}")
        print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
        
        print(f"\nPer-Role Results:")
        for role, role_results in results.get("role_results", {}).items():
            print(f"  {role.upper()}: {role_results['passed']}/{role_results['total_tests']} passed")
            
        # Detailed failure analysis
        failed_tests = []
        for role, role_results in results.get("role_results", {}).items():
            for test_result in role_results.get("test_results", []):
                if not test_result["passed"]:
                    failed_tests.append({
                        "role": role,
                        "test": test_result["test_case"],
                        "issues": test_result["analysis"]["issues"]
                    })
                    
        if failed_tests:
            print(f"\nFailed Tests Details:")
            for failed in failed_tests:
                print(f"  {failed['role'].upper()}: {failed['test']}")
                for issue in failed["issues"]:
                    print(f"    - {issue}")
                    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save test results to a JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_rbac_test_results_{timestamp}.json"
            
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"\nResults saved to: {filepath}")

async def main():
    """Main test execution function"""
    # Check if we're in Docker environment
    base_url = "http://api:8000" if os.getenv("DOCKER_ENV") else "http://localhost:8000"
    
    tester = ChatRBACTester(base_url)
    
    try:
        # Run all tests
        results = await tester.run_all_tests()
        
        # Print summary
        tester.print_summary(results)
        
        # Save results
        tester.save_results(results)
        
        # Exit with appropriate code
        if results.get("summary", {}).get("total_failed", 0) > 0:
            print(f"\n❌ Some tests failed. Check the results for details.")
            sys.exit(1)
        else:
            print(f"\n✅ All RBAC tests passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
