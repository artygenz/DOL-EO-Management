#!/usr/bin/env python3
"""
Test Task Status

This test checks the status of Dylan's tasks to understand the filtering issue.
"""

import sys
import os

def test_task_status():
    """Test the task status filtering."""
    print("Test Task Status")
    print("=" * 50)
    
    # Import the necessary modules
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    from src.workflow import repository as repo
    
    # Get Dylan's user ID
    user_id = repo.resolve_user_by_email("dylan.sachetti@lumenlighthouse.ai")
    print(f"User ID: {user_id}")
    
    # Get all tasks for Dylan (without status filter)
    with repo.SessionLocal() as db:
        from src.models.task import Task
        from src.models.user import User
        from sqlalchemy import select
        
        # Get all tasks for Dylan
        tasks = db.execute(
            select(Task)
            .join(User, Task.assignee_id == User.id)
            .where(User.email == "dylan.sachetti@lumenlighthouse.ai")
        ).scalars().all()
        
        print(f"Dylan has {len(tasks)} total tasks:")
        for i, task in enumerate(tasks):
            print(f"  {i+1}. ID: {task.id}")
            print(f"     Title: {task.title}")
            print(f"     Status: '{task.status}'")
            print()
        
        # Check which tasks would be considered "active"
        active_statuses = ["pending", "in_progress", "Pending PMO approval"]
        active_tasks = [t for t in tasks if t.status in active_statuses]
        
        print(f"Dylan has {len(active_tasks)} active tasks (status in {active_statuses}):")
        for i, task in enumerate(active_tasks):
            print(f"  {i+1}. ID: {task.id}")
            print(f"     Title: {task.title}")
            print(f"     Status: '{task.status}'")
            print()
        
        # Test the repository function
        repo_tasks = repo.get_user_active_tasks(user_id)
        print(f"Repository function returns {len(repo_tasks)} tasks:")
        for i, task in enumerate(repo_tasks):
            print(f"  {i+1}. ID: {task['id']}")
            print(f"     Title: {task['title']}")
            print(f"     Status: '{task['status']}'")
            print()

if __name__ == "__main__":
    test_task_status()
