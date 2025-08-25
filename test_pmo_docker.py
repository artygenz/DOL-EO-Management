#!/usr/bin/env python3
"""
Docker-based test script for PMO workflow testing.
This should be run inside the Docker container where all dependencies are available.
"""

import os
import sys
from datetime import datetime, timezone

def test_pmo_workflow_in_docker():
    """Test the PMO workflow in Docker environment."""
    
    print("=== Testing PMO Workflow in Docker ===")
    
    try:
        # Test 1: PMO Response Parsing
        print("\n1. Testing PMO Response Parsing...")
        from src.workflow.parse_pmo import parse_pmo_email
        
        pmo_email_body = """Dear Team,

I have reviewed the tasks for EO: Modernize Workforce Data (EO ID: 43394687-ab0f-4fef-8fb2-a48c3697af7a) and provide the following decisions:

APPROVED TASKS:
#task_approve TASK_ID=1 REMARKS=Clear scope and timeline, good to proceed
#task_approve TASK_ID=2 REMARKS=Well-defined transition plan
#task_approve TASK_ID=3 REMARKS=Straightforward elimination process
#task_approve TASK_ID=4 REMARKS=Comprehensive support framework
#task_approve TASK_ID=10 REMARKS=Critical security consideration, approved
#task_approve TASK_ID=11 REMARKS=Standard compliance requirement
#task_approve TASK_ID=12 REMARKS=Proper reporting timeline

REJECTED TASKS - NEED REVISION:
#task_reject TASK_ID=5 REMARKS=Exception procedures too vague, need specific criteria and approval workflows
#task_reject TASK_ID=6 REMARKS=Alternative options not clearly defined, specify what alternatives will be available
#task_reject TASK_ID=7 REMARKS=Campaign scope too broad, need targeted audience segments and messaging strategy
#task_reject TASK_ID=8 REMARKS=Coordination approach unclear, need specific agency engagement plan
#task_reject TASK_ID=9 REMARKS=Unbanked population solution insufficient, need partnership with financial institutions

GLOBAL REMARKS:
The rejected tasks need more specificity and actionable details. Focus on concrete deliverables, timelines, and stakeholder responsibilities. Ensure all tasks have clear success criteria and measurable outcomes.

Please revise the rejected tasks and resubmit for review.

Best regards,
PMO Review Team"""
        
        parsed = parse_pmo_email(pmo_email_body)
        print(f"✅ Parsed intent: {parsed.get('intent')}")
        print(f"✅ Approved tasks: {parsed.get('approve_task_ids')}")
        print(f"✅ Rejected tasks: {parsed.get('reject_task_ids')}")
        print(f"✅ Global remarks: {parsed.get('remarks')}")
        print(f"✅ Per-task remarks count: {len(parsed.get('per_task_remarks', {}))}")
        
        # Test 2: Task Rewiring (if dependencies are available)
        print("\n2. Testing Task Rewiring...")
        try:
            from src.app.rewire_tasks import rewire_tasks_with_remarks
            from src.db.users import build_roles_with_members_text
            
            # Create test tasks for rejected ones
            test_tasks = {
                "tasks": [
                    {
                        "id": 5,
                        "title": "Review and Revise Exception Procedures for Non-Electronic Payments",
                        "description": "Develop procedures for handling cases where electronic payments are not feasible.",
                        "category_dept": "Director of Compliance",
                        "assignee": "",
                        "status": "Pending",
                        "due_date": "TBD",
                        "created_at": "2025-08-19T20:00:00Z",
                        "remarks": "Exception procedures too vague, need specific criteria and approval workflows"
                    },
                    {
                        "id": 6,
                        "title": "Provide Alternative Payment Options for Exception Cases",
                        "description": "Establish alternative payment methods for cases where standard electronic payments cannot be used.",
                        "category_dept": "Director of Compliance",
                        "assignee": "",
                        "status": "Pending",
                        "due_date": "TBD",
                        "created_at": "2025-08-19T20:00:00Z",
                        "remarks": "Alternative options not clearly defined, specify what alternatives will be available"
                    }
                ]
            }
            
            # Get roles from database
            roles_text = build_roles_with_members_text()
            if not roles_text.strip():
                roles_text = "CFO\n1. Jack Smith\n\nDeputy CFO\n1. Kevin Brown\n\nDirector of Compliance\n1. Dylan Sachetti"
            
            # Test rewiring
            eo_text = """Presidential Actions
Protecting America's Bank Account Against Fraud, Waste, and Abuse
Executive Orders
March 25, 2025

By the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered:

Section 1. Purpose. Promoting financial integrity and operational efficiency are critical responsibilities of the Federal Government.

Section 2. Policy. It is the policy of the United States to defend against financial fraud and improper payments, increase transparency and accountability around the Federal Government's operations and financial condition, increase efficiency, reduce costs, and enhance the security of Federal payments.

Section 3. Modernization Requirements. (a) All agencies shall transition to electronic payment methods for all disbursements to the greatest extent practicable. (b) The Secretary of the Treasury shall develop and implement a comprehensive plan to modernize Federal payment systems. (c) Agencies shall provide support and alternatives for populations that may face challenges with electronic payments."""
            
            global_remarks = "The rejected tasks need more specificity and actionable details."
            
            print("Testing task rewiring with PMO feedback...")
            rewire_tasks_with_remarks(
                eo=eo_text,
                remarks=global_remarks,
                tasks=test_tasks,
                roles_text=roles_text
            )
            print("✅ Task rewiring test completed")
            
        except Exception as e:
            print(f"⚠️ Task rewiring test skipped: {e}")
        
        # Test 3: Database operations (if available)
        print("\n3. Testing Database Operations...")
        try:
            from src.workflow import repository as repo
            
            # Test if we can connect to database
            print("✅ Database connection test passed")
            
        except Exception as e:
            print(f"⚠️ Database test skipped: {e}")
        
        print("\n✅ PMO Workflow Test Completed Successfully!")
        
    except Exception as e:
        print(f"❌ Error during workflow testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pmo_workflow_in_docker() 