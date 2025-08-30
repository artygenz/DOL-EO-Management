#!/usr/bin/env python3
"""
Simple Task Matching Test

This test helps debug the task matching logic without importing complex modules.
"""

def test_task_matching():
    """Test the task matching logic."""
    print("Simple Task Matching Test")
    print("=" * 50)
    
    # Dylan's actual tasks from database
    dylan_tasks = [
        {
            "id": "d6b4ef70-cd60-4612-a027-3a353234d0e1",
            "title": "Issue Guidance on Data Access for Fraud Prevention"
        },
        {
            "id": "f9ae9927-17eb-436c-a1f6-9e2c25958926", 
            "title": "Update and Issue Payment Verification Guidance in Consultation with OMB Director"
        },
        {
            "id": "3f01131e-e1f0-4856-8b06-94b61cad8ce9",
            "title": "Update Privacy Act System of Records Notices for Treasury Data Sharing"
        },
        {
            "id": "0924dcbc-9246-4e0b-b0cd-30bc48d0ae20",
            "title": "Develop Transparent Exemption Request Process for Payment Verification"
        },
        {
            "id": "48426c30-e66a-4e5b-9bc9-1c07fb088368",
            "title": "Submit Agency Compliance Plan to OMB Director"
        }
    ]
    
    # Test email content
    email_content = """
Daily Update - 2025-01-15

Working on the Update Privacy Act System of Records Notices for Treasury Data Sharing - about 60% complete, spent 3.5 hours today. Need PMO approval to proceed further. 

Also made progress on the Issue Guidance on Data Access for Fraud Prevention - about 40% done, spent 2 hours today.

Security review is pending until the system implementation is further along.

Overall progress is good, but waiting for some approvals.
    """.strip()
    
    print(f"Email content length: {len(email_content)}")
    print(f"Email content: {email_content}")
    print()
    
    # Test task matching logic
    print("Testing task matching logic:")
    email_lower = email_content.lower()
    
    matches = []
    for task in dylan_tasks:
        task_title_lower = task['title'].lower()
        is_match = task_title_lower in email_lower
        print(f"  Task: {task['title']}")
        print(f"    Lowercase: {task_title_lower}")
        print(f"    In email: {is_match}")
        if is_match:
            matches.append(task)
        print()
    
    print(f"Found {len(matches)} matching tasks:")
    for match in matches:
        print(f"  - {match['title']}")
    
    # Test case determination logic
    print("\nTesting case determination logic:")
    
    # Check for C3 indicators (single task)
    if len(dylan_tasks) == 1:
        case = "C3"
        print(f"  C3 case: {len(dylan_tasks)} == 1")
    else:
        # Check for C2 indicators (detailed breakdown)
        if "task:" in email_lower and "status:" in email_lower:
            task_count = email_lower.count("task:")
            if task_count > 1:
                case = "C2"
                print(f"  C2 case: found {task_count} task: mentions")
            else:
                case = "C1"
                print(f"  C1 case: not enough task: mentions")
        else:
            # Check if any tasks are actually mentioned before defaulting to C1
            mentioned_tasks = []
            for task in dylan_tasks:
                task_title_lower = task['title'].lower()
                if task_title_lower in email_lower:
                    mentioned_tasks.append(task)
            
            if mentioned_tasks:
                case = "C1"
                print(f"  C1 case: found {len(mentioned_tasks)} mentioned tasks")
            else:
                case = "C1"
                print(f"  C1 case: no tasks mentioned")
    
    print(f"  Determined case: {case}")
    
    return matches, case

if __name__ == "__main__":
    matches, case = test_task_matching()
    print(f"\nResult: {len(matches)} matches, case: {case}")
