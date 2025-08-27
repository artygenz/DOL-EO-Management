#!/usr/bin/env python3
"""
Test PMO response parsing with regex only (no LLM dependency)
"""

import requests
import json

def test_pmo_response_regex():
    """Test PMO response with regex-parseable format"""
    
    # Test with a valid EO ID that exists in the database
    eo_id = "27cd0784-ca48-4942-ab48-82a58d97a3e6"  # The EO we've been working with
    
    # PMO response in the exact table format that regex expects
    pmo_response = {
        "message_id": "test-mid-125",
        "subject": f"PMO Review Response - EO {eo_id}",
        "sender": "pmo@example.gov",
        "recipients": ["workflow@example.gov"],
        "body_text": f"""
Subject EO: EO: Modernize Workforce Data
EO ID: {eo_id}
EO Message-ID: msg-2001@sample
Received: 2025-08-13T15:00:00+00:00

Below are the PENDING tasks for PMO action.

INSTRUCTIONS:
1. Copy the table below
2. Paste it in your reply email
3. Fill in the 'Status' column with 'Approve' or 'Reject'
4. Fill in the 'Remarks' column with your feedback
5. Send the email back

Task ID | Title | Owner | Assignee | Due | Status | Remarks
--------|-------|-------|----------|-----|--------|--------
1 | Cease Issuance of Paper Checks for Disbursements | — | Sophia Carty | 2025-09-30 | Approve | Looks good
2 | Implement Electronic Processing for All Incoming Federal Payments | — | Sophia Carty | TBD | Reject | Need more details
3 | Develop and Launch Digital Payment Transition Support Plan | — | Ayesha Ahsan | TBD | Approve | Approved
        """,
        "related_eo_id": eo_id
    }
    
    print("Testing PMO response with regex-parseable format...")
    print(f"EO ID: {eo_id}")
    print("Expected: APPROVE_SOME with 2 approved, 1 rejected")
    
    try:
        response = requests.post(
            "http://localhost:8000/webhook/pmo_email",
            json=pmo_response,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 202:
            print("✅ SUCCESS: PMO response accepted for processing")
            print("Check the worker logs to see the parsing results")
        else:
            print("❌ FAILED: PMO response was not accepted")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to API server. Make sure it's running on localhost:8000")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def test_pmo_response_simple():
    """Test PMO response with simple 'approve all' format"""
    
    eo_id = "27cd0784-ca48-4942-ab48-82a58d97a3e6"
    
    # Simple "approve all" response that should work with regex
    pmo_response = {
        "message_id": "test-mid-126",
        "subject": f"PMO Review Response - EO {eo_id}",
        "sender": "pmo@example.gov",
        "recipients": ["workflow@example.gov"],
        "body_text": "approve all",
        "related_eo_id": eo_id
    }
    
    print("\nTesting PMO response with 'approve all'...")
    print(f"EO ID: {eo_id}")
    print("Expected: APPROVE_ALL")
    
    try:
        response = requests.post(
            "http://localhost:8000/webhook/pmo_email",
            json=pmo_response,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 202:
            print("✅ SUCCESS: PMO response accepted for processing")
            print("Check the worker logs to see the parsing results")
        else:
            print("❌ FAILED: PMO response was not accepted")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to API server. Make sure it's running on localhost:8000")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_pmo_response_regex()
    test_pmo_response_simple()
