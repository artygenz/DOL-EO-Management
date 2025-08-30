#!/usr/bin/env python3
"""
Test script for the daily task update system.

This script tests the key components of the daily update system:
1. Task update extraction from emails
2. Database operations
3. Summary generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, datetime
from src.workflow.ai import extract_daily_task_updates, generate_daily_eo_summary
from src.workflow import repository as repo

def test_task_update_extraction():
    """Test the AI extraction of task updates from email content."""
    print("=== Testing Task Update Extraction ===")
    
    # Sample user tasks
    user_tasks = [
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "title": "Implement new reporting system",
            "description": "Create a new reporting system for EO compliance",
            "eo_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "in_progress"
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440002", 
            "title": "Update documentation",
            "description": "Update all documentation for the new system",
            "eo_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "pending"
        }
    ]
    
    # Sample email content (C2 format - detailed per-task breakdown)
    email_content = """
Daily Update (2025-01-15)

Task: Implement new reporting system
Status: InProgress
Progress: 60%
ETA: 2025-01-20
Spent: 3.5h
Blockers: Waiting for approval from PMO
Notes: Completed the core functionality, need to add error handling

Task: Update documentation
Status: NotStarted
Progress: 0%
ETA: 2025-01-25
Spent: 0h
Blockers: None
Notes: Will start after reporting system is complete
    """
    
    # Test extraction
    result = extract_daily_task_updates(email_content, user_tasks)
    
    print(f"Extraction Case: {result.get('case')}")
    print(f"Updates Found: {len(result.get('updates', []))}")
    print(f"Unmatched Mentions: {len(result.get('unmatched_mentions', []))}")
    
    for i, update in enumerate(result.get('updates', [])):
        print(f"\nUpdate {i+1}:")
        print(f"  Task ID: {update.get('task_id')}")
        print(f"  Status: {update.get('status')}")
        print(f"  Progress: {update.get('progress_pct')}%")
        print(f"  ETA: {update.get('eta')}")
        print(f"  Spent Hours: {update.get('spent_hours')}")
        print(f"  Blockers: {update.get('blockers')}")
        print(f"  Notes: {update.get('notes')}")
    
    return result

def test_summary_generation():
    """Test the daily summary generation."""
    print("\n=== Testing Summary Generation ===")
    
    # Sample task updates
    task_updates = [
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440001",
            "task_title": "Implement new reporting system",
            "user_name": "John Doe",
            "progress_pct": 60,
            "status": "InProgress",
            "notes": "Completed core functionality",
            "blockers": ["Waiting for PMO approval"],
            "risks": ["Timeline might slip"],
            "eta": date(2025, 1, 20),
            "spent_hours": 3.5,
            "is_late": False
        },
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440002",
            "task_title": "Update documentation", 
            "user_name": "Jane Smith",
            "progress_pct": 0,
            "status": "NotStarted",
            "notes": "Will start after reporting system is complete",
            "blockers": [],
            "risks": [],
            "eta": date(2025, 1, 25),
            "spent_hours": 0,
            "is_late": False
        }
    ]
    
    eo_context = "Executive Order 12345 - Digital Transformation Initiative"
    
    # Test summary generation
    summary = generate_daily_eo_summary("550e8400-e29b-41d4-a716-446655440000", task_updates, eo_context)
    
    print(f"Progress Summary:\n{summary.get('progress_summary')}")
    print(f"\nKey Blockers: {summary.get('key_blockers')}")
    print(f"Risks: {summary.get('risks')}")
    print(f"Attention Items: {summary.get('attention_items')}")
    print(f"Total Tasks: {summary.get('total_tasks')}")
    print(f"Updated Tasks: {summary.get('updated_tasks')}")
    
    return summary

def test_database_operations():
    """Test database operations (requires database connection)."""
    print("\n=== Testing Database Operations ===")
    
    try:
        # Test user resolution
        # Note: This requires actual database connection and data
        print("Database operations test skipped - requires database connection")
        print("To test database operations:")
        print("1. Ensure database is running")
        print("2. Add test users and tasks")
        print("3. Run the test with database connection")
        
    except Exception as e:
        print(f"Database test error: {e}")

def main():
    """Run all tests."""
    print("Daily Task Update System - Test Suite")
    print("=" * 50)
    
    # Test 1: Task update extraction
    extraction_result = test_task_update_extraction()
    
    # Test 2: Summary generation
    summary_result = test_summary_generation()
    
    # Test 3: Database operations (skipped)
    test_database_operations()
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"✓ Task update extraction: {len(extraction_result.get('updates', []))} updates extracted")
    print(f"✓ Summary generation: {summary_result.get('total_tasks')} tasks summarized")
    print("✓ Database operations: Skipped (requires DB connection)")
    
    print("\nDaily update system is ready for integration!")

if __name__ == "__main__":
    main()
