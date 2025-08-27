#!/usr/bin/env python3
"""
Simple test script for PMO response parsing only.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_pmo_parsing():
    """Test the PMO response parsing functionality."""
    
    print("=== Testing PMO Response Parsing ===")
    
    # Test PMO response email
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
    
    try:
        from src.workflow.parse_pmo import parse_pmo_email
        
        parsed = parse_pmo_email(pmo_email_body)
        
        print(f"✅ Parsed intent: {parsed.get('intent')}")
        print(f"✅ Approved tasks: {parsed.get('approve_task_ids')}")
        print(f"✅ Rejected tasks: {parsed.get('reject_task_ids')}")
        print(f"✅ Global remarks: {parsed.get('remarks')}")
        print(f"✅ Per-task remarks: {parsed.get('per_task_remarks')}")
        
        # Verify the results
        expected_approved = ['1', '2', '3', '4', '10', '11', '12']
        expected_rejected = ['5', '6', '7', '8', '9']
        
        if parsed.get('approve_task_ids') == expected_approved:
            print("✅ Approved tasks parsing: CORRECT")
        else:
            print(f"❌ Approved tasks parsing: EXPECTED {expected_approved}, GOT {parsed.get('approve_task_ids')}")
        
        if parsed.get('reject_task_ids') == expected_rejected:
            print("✅ Rejected tasks parsing: CORRECT")
        else:
            print(f"❌ Rejected tasks parsing: EXPECTED {expected_rejected}, GOT {parsed.get('reject_task_ids')}")
        
        if parsed.get('intent') == 'APPROVE_SOME':
            print("✅ Intent parsing: CORRECT")
        else:
            print(f"❌ Intent parsing: EXPECTED APPROVE_SOME, GOT {parsed.get('intent')}")
        
        # Check per-task remarks
        expected_remarks = {
            '1': 'Clear scope and timeline, good to proceed',
            '2': 'Well-defined transition plan',
            '3': 'Straightforward elimination process',
            '4': 'Comprehensive support framework',
            '10': 'Critical security consideration, approved',
            '11': 'Standard compliance requirement',
            '12': 'Proper reporting timeline',
            '5': 'Exception procedures too vague, need specific criteria and approval workflows',
            '6': 'Alternative options not clearly defined, specify what alternatives will be available',
            '7': 'Campaign scope too broad, need targeted audience segments and messaging strategy',
            '8': 'Coordination approach unclear, need specific agency engagement plan',
            '9': 'Unbanked population solution insufficient, need partnership with financial institutions'
        }
        
        if parsed.get('per_task_remarks') == expected_remarks:
            print("✅ Per-task remarks parsing: CORRECT")
        else:
            print(f"❌ Per-task remarks parsing: EXPECTED {expected_remarks}, GOT {parsed.get('per_task_remarks')}")
        
    except Exception as e:
        print(f"❌ Error during parsing test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pmo_parsing() 