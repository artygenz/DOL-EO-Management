#!/usr/bin/env python3
"""
Test script for task ID mapping functionality.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_task_mapping():
    """Test the task ID mapping functionality."""
    
    print("=== Testing Task ID Mapping ===")
    
    try:
        from src.workflow import repository as repo
        
        # Test EO ID
        eo_id = "43394687-ab0f-4fef-8fb2-a48c3697af7a"
        
        # Test simple task IDs
        simple_task_ids = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
        
        print(f"Mapping simple task IDs: {simple_task_ids}")
        print(f"For EO: {eo_id}")
        
        # Map simple IDs to UUIDs
        mapped_ids = repo.map_simple_task_ids_to_uuids(eo_id, simple_task_ids)
        
        print(f"Mapped UUIDs: {mapped_ids}")
        print(f"Mapping count: {len(mapped_ids)}")
        
        if mapped_ids:
            print("✅ Task mapping successful!")
            
            # Test updating tasks with mapped IDs
            print("\nTesting task status update with mapped IDs...")
            
            # Test with first few mapped IDs
            test_ids = mapped_ids[:3]  # First 3 tasks
            if test_ids:
                result = repo.update_tasks_status_and_remarks(test_ids, status="test_status", remarks="Test mapping")
                print(f"✅ Updated {result} tasks with test status")
        else:
            print("⚠️ No tasks found for this EO - make sure tasks exist in database")
        
    except Exception as e:
        print(f"❌ Error during mapping test: {e}")
        import traceback
        traceback.print_exc()

def test_pmo_parsing_with_mapping():
    """Test PMO parsing with task ID mapping."""
    
    print("\n=== Testing PMO Parsing with Mapping ===")
    
    try:
        from src.workflow.parse_pmo import parse_pmo_email
        from src.workflow import repository as repo
        
        # Test PMO response
        pmo_email_body = """Dear Team,

I have reviewed the tasks for EO: Modernize Workforce Data (EO ID: 43394687-ab0f-4fef-8fb2-a48c3697af7a) and provide the following decisions:

APPROVED TASKS:
#task_approve TASK_ID=1 REMARKS=Clear scope and timeline, good to proceed
#task_approve TASK_ID=2 REMARKS=Well-defined transition plan
#task_approve TASK_ID=3 REMARKS=Straightforward elimination process

REJECTED TASKS - NEED REVISION:
#task_reject TASK_ID=5 REMARKS=Exception procedures too vague, need specific criteria and approval workflows
#task_reject TASK_ID=6 REMARKS=Alternative options not clearly defined, specify what alternatives will be available

GLOBAL REMARKS:
The rejected tasks need more specificity and actionable details.

Best regards,
PMO Review Team"""
        
        # Parse PMO response
        parsed = parse_pmo_email(pmo_email_body)
        print(f"Parsed approved tasks: {parsed.get('approve_task_ids')}")
        print(f"Parsed rejected tasks: {parsed.get('reject_task_ids')}")
        print(f"Parsed per-task remarks: {parsed.get('per_task_remarks')}")
        
        # Test mapping
        eo_id = "43394687-ab0f-4fef-8fb2-a48c3697af7a"
        approve_ids = parsed.get('approve_task_ids', [])
        reject_ids = parsed.get('reject_task_ids', [])
        
        if approve_ids:
            mapped_approve = repo.map_simple_task_ids_to_uuids(eo_id, approve_ids)
            print(f"Mapped approved IDs: {mapped_approve}")
        
        if reject_ids:
            mapped_reject = repo.map_simple_task_ids_to_uuids(eo_id, reject_ids)
            print(f"Mapped rejected IDs: {mapped_reject}")
        
        print("✅ PMO parsing with mapping test completed")
        
    except Exception as e:
        print(f"❌ Error during PMO parsing test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_task_mapping()
    test_pmo_parsing_with_mapping() 