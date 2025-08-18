#!/usr/bin/env python3
"""
Demo script for Email Thread Analysis and Correlation System

This script demonstrates the thread analyzer capabilities including:
- Email thread analysis
- PMO response correlation
- Conversation context tracking
- Thread-based duplicate detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr, formatdate

from src.email.thread_analyzer import EmailThreadAnalyzer, ThreadType
from src.email.content_extractor import EnhancedContentExtractor, EmailHeaders


def create_sample_email(from_addr, to_addr, subject, content, message_id, 
                       in_reply_to=None, references=None):
    """Create a sample email message"""
    msg = EmailMessage()
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg['Message-ID'] = message_id
    msg['Date'] = formatdate()
    
    if in_reply_to:
        msg['In-Reply-To'] = in_reply_to
    if references:
        msg['References'] = ' '.join(references)
    
    msg.set_content(content)
    return msg


def demo_pmo_workflow():
    """Demonstrate PMO workflow thread analysis"""
    print("=== PMO Workflow Thread Analysis Demo ===\n")
    
    analyzer = EmailThreadAnalyzer()
    extractor = EnhancedContentExtractor()
    
    # Step 1: Initial PMO request
    request_msg = create_sample_email(
        from_addr="project.manager@dol.gov",
        to_addr="pmo@dol.gov",
        subject="Budget Approval Request - Project Alpha",
        content="""
        Dear PMO Team,
        
        I am requesting approval for additional budget allocation.
        
        Project Details:
        - Project ID: ALPHA-2024-001
        - Additional Budget: $75,000
        - Justification: Security compliance requirements
        
        Please review and approve.
        
        Best regards,
        Project Manager
        """,
        message_id="<budget-request-alpha@dol.gov>"
    )
    
    # Extract and analyze
    request_content = extractor.extract_email_content(request_msg)
    request_thread = analyzer.analyze_email_thread(request_msg, request_content.headers)
    request_context = analyzer.track_conversation_context(
        request_msg, request_content.headers, request_thread
    )
    
    print(f"Initial Request Analysis:")
    print(f"  Thread ID: {request_thread.thread_id}")
    print(f"  Is Reply: {request_thread.is_reply}")
    print(f"  Thread Depth: {request_thread.thread_depth}")
    print(f"  Conversation ID: {request_context.conversation_id}")
    print(f"  Thread Type: {request_context.thread_type.value}")
    print(f"  Participants: {len(request_context.participants)}")
    print(f"  Workflow Confidence: {request_context.workflow_correlation.correlation_confidence:.2f}")
    print(f"  Task IDs: {request_context.workflow_correlation.related_task_ids}")
    print()
    
    # Step 2: PMO Response
    pmo_response_msg = create_sample_email(
        from_addr="pmo.manager@dol.gov",
        to_addr="project.manager@dol.gov",
        subject="Re: Budget Approval Request - Project Alpha",
        content="""
        Dear Project Manager,
        
        Your budget request has been APPROVED.
        
        Approval Details:
        - Approval ID: PMO-APPROVAL-2024-789
        - Approved Amount: $75,000
        - Task ID: BUDGET-TASK-456
        
        Please proceed with implementation.
        
        Best regards,
        PMO Manager
        """,
        message_id="<pmo-approval-alpha@dol.gov>",
        in_reply_to="<budget-request-alpha@dol.gov>",
        references=["<budget-request-alpha@dol.gov>"]
    )
    
    # Extract and analyze PMO response
    pmo_content = extractor.extract_email_content(pmo_response_msg)
    pmo_thread = analyzer.analyze_email_thread(pmo_response_msg, pmo_content.headers)
    pmo_context = analyzer.track_conversation_context(
        pmo_response_msg, pmo_content.headers, pmo_thread
    )
    
    print(f"PMO Response Analysis:")
    print(f"  Thread ID: {pmo_thread.thread_id}")
    print(f"  Is Reply: {pmo_thread.is_reply}")
    print(f"  Thread Depth: {pmo_thread.thread_depth}")
    print(f"  Parent Message: {pmo_thread.parent_message_id}")
    print(f"  Conversation ID: {pmo_context.conversation_id}")
    print(f"  Thread Type: {pmo_context.thread_type.value}")
    print(f"  Participants: {len(pmo_context.participants)}")
    print(f"  Messages in Timeline: {len(pmo_context.message_timeline)}")
    print(f"  Workflow Confidence: {pmo_context.workflow_correlation.correlation_confidence:.2f}")
    print(f"  Task IDs: {pmo_context.workflow_correlation.related_task_ids}")
    print(f"  Approval IDs: {pmo_context.workflow_correlation.approval_request_ids}")
    print()
    
    # Step 3: Developer Update
    dev_update_msg = create_sample_email(
        from_addr="senior.developer@dol.gov",
        to_addr="pmo.manager@dol.gov",
        subject="Re: Budget Approval Request - Project Alpha - Development Progress",
        content="""
        PMO Team,
        
        Development update for Task BUDGET-TASK-456:
        
        Progress: 60% complete
        - Security framework: DONE
        - Integration testing: IN PROGRESS
        - Documentation: PENDING
        
        Blockers: None
        ETA: Next Friday
        
        Developer Team
        """,
        message_id="<dev-progress-alpha@dol.gov>",
        in_reply_to="<pmo-approval-alpha@dol.gov>",
        references=["<budget-request-alpha@dol.gov>", "<pmo-approval-alpha@dol.gov>"]
    )
    
    # Extract and analyze developer update
    dev_content = extractor.extract_email_content(dev_update_msg)
    dev_thread = analyzer.analyze_email_thread(dev_update_msg, dev_content.headers)
    dev_context = analyzer.track_conversation_context(
        dev_update_msg, dev_content.headers, dev_thread
    )
    
    print(f"Developer Update Analysis:")
    print(f"  Thread ID: {dev_thread.thread_id}")
    print(f"  Is Reply: {dev_thread.is_reply}")
    print(f"  Thread Depth: {dev_thread.thread_depth}")
    print(f"  Conversation ID: {dev_context.conversation_id}")
    print(f"  Thread Type: {dev_context.thread_type.value}")
    print(f"  Participants: {len(dev_context.participants)}")
    print(f"  Messages in Timeline: {len(dev_context.message_timeline)}")
    print(f"  Workflow Confidence: {dev_context.workflow_correlation.correlation_confidence:.2f}")
    print(f"  Task IDs: {dev_context.workflow_correlation.related_task_ids}")
    print()
    
    # Verify conversation continuity
    print("Conversation Continuity Check:")
    print(f"  Request Conversation ID: {request_context.conversation_id}")
    print(f"  PMO Response Conversation ID: {pmo_context.conversation_id}")
    print(f"  Dev Update Conversation ID: {dev_context.conversation_id}")
    print(f"  All Same Conversation: {request_context.conversation_id == pmo_context.conversation_id == dev_context.conversation_id}")
    print()
    
    # Show final conversation state
    final_context = analyzer.get_conversation_context(dev_context.conversation_id)
    if final_context:
        print("Final Conversation State:")
        print(f"  Total Messages: {len(final_context.message_timeline)}")
        print(f"  Total Participants: {len(final_context.participants)}")
        print(f"  Subject Evolution: {len(final_context.subject_evolution)} subjects")
        print(f"  Final Workflow Type: {final_context.workflow_correlation.workflow_type.value}")
        print(f"  All Task IDs: {final_context.workflow_correlation.related_task_ids}")
        print(f"  All Approval IDs: {final_context.workflow_correlation.approval_request_ids}")
    
    return analyzer


def demo_duplicate_detection():
    """Demonstrate thread-based duplicate detection"""
    print("\n=== Thread-Based Duplicate Detection Demo ===\n")
    
    analyzer = EmailThreadAnalyzer()
    
    # Create original email
    original_msg = create_sample_email(
        from_addr="user@dol.gov",
        to_addr="team@dol.gov",
        subject="Important Project Update",
        content="This is an important project status update.",
        message_id="<project-update-1@dol.gov>"
    )
    
    # Create headers for original
    original_headers = EmailHeaders(
        message_id="<project-update-1@dol.gov>",
        sender="user@dol.gov",
        sender_name="User",
        recipients=["team@dol.gov"],
        cc_recipients=[],
        bcc_recipients=[],
        subject="Important Project Update",
        date=datetime.utcnow(),
        reply_to=None,
        in_reply_to=None,
        references=[],
        thread_topic=None,
        priority=None,
        content_type="text/plain",
        encoding="utf-8",
        custom_headers={}
    )
    
    # Analyze original
    original_thread = analyzer.analyze_email_thread(original_msg, original_headers)
    original_context = analyzer.track_conversation_context(original_msg, original_headers, original_thread)
    
    # Check for duplicates (should be none)
    duplicate_check = analyzer.detect_thread_based_duplicates(
        original_headers, "This is an important project status update.", original_thread
    )
    
    print(f"Original Email Duplicate Check:")
    print(f"  Is Duplicate: {duplicate_check.is_duplicate}")
    print(f"  Duplicate Type: {duplicate_check.duplicate_type}")
    print(f"  Confidence Score: {duplicate_check.confidence_score}")
    print(f"  Detection Method: {duplicate_check.detection_method}")
    print()


def demo_conversation_branching():
    """Demonstrate conversation branching and merging"""
    print("\n=== Conversation Branching Demo ===\n")
    
    analyzer = EmailThreadAnalyzer()
    
    # Original discussion
    original_msg = create_sample_email(
        from_addr="team.lead@dol.gov",
        to_addr="development.team@dol.gov",
        subject="Security Implementation Discussion",
        content="Let's discuss the security implementation approach.",
        message_id="<security-discussion@dol.gov>"
    )
    
    original_headers = EmailHeaders(
        message_id="<security-discussion@dol.gov>",
        sender="team.lead@dol.gov",
        sender_name="Team Lead",
        recipients=["development.team@dol.gov"],
        cc_recipients=[],
        bcc_recipients=[],
        subject="Security Implementation Discussion",
        date=datetime.utcnow(),
        reply_to=None,
        in_reply_to=None,
        references=[],
        thread_topic=None,
        priority=None,
        content_type="text/plain",
        encoding="utf-8",
        custom_headers={}
    )
    
    original_thread = analyzer.analyze_email_thread(original_msg, original_headers)
    original_context = analyzer.track_conversation_context(original_msg, original_headers, original_thread)
    
    print(f"Original Discussion:")
    print(f"  Conversation ID: {original_context.conversation_id}")
    print(f"  Thread Type: {original_context.thread_type.value}")
    print()
    
    # Branch 1: Technical response
    tech_msg = create_sample_email(
        from_addr="security.architect@dol.gov",
        to_addr="team.lead@dol.gov",
        subject="Re: Security Implementation Discussion - Technical Approach",
        content="I recommend OAuth 2.0 with PKCE for authentication.",
        message_id="<tech-response@dol.gov>",
        in_reply_to="<security-discussion@dol.gov>",
        references=["<security-discussion@dol.gov>"]
    )
    
    tech_headers = EmailHeaders(
        message_id="<tech-response@dol.gov>",
        sender="security.architect@dol.gov",
        sender_name="Security Architect",
        recipients=["team.lead@dol.gov"],
        cc_recipients=[],
        bcc_recipients=[],
        subject="Re: Security Implementation Discussion - Technical Approach",
        date=datetime.utcnow() + timedelta(hours=1),
        reply_to=None,
        in_reply_to="<security-discussion@dol.gov>",
        references=["<security-discussion@dol.gov>"],
        thread_topic=None,
        priority=None,
        content_type="text/plain",
        encoding="utf-8",
        custom_headers={}
    )
    
    tech_thread = analyzer.analyze_email_thread(tech_msg, tech_headers)
    tech_context = analyzer.track_conversation_context(tech_msg, tech_headers, tech_thread)
    
    print(f"Technical Branch:")
    print(f"  Conversation ID: {tech_context.conversation_id}")
    print(f"  Same as Original: {tech_context.conversation_id == original_context.conversation_id}")
    print(f"  Messages in Timeline: {len(tech_context.message_timeline)}")
    print()
    
    # Show analyzer statistics
    stats = analyzer.get_thread_analysis_stats()
    print("Thread Analyzer Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def main():
    """Run all demos"""
    print("Email Thread Analysis and Correlation System Demo")
    print("=" * 50)
    
    try:
        # Run PMO workflow demo
        analyzer = demo_pmo_workflow()
        
        # Run duplicate detection demo
        demo_duplicate_detection()
        
        # Run conversation branching demo
        demo_conversation_branching()
        
        print("\n=== Demo Complete ===")
        print("All thread analysis features demonstrated successfully!")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())