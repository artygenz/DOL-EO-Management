"""
Integration tests for Email Thread Analysis and Correlation System

Tests complex email thread scenarios including PMO response correlation,
conversation context tracking, and thread-based duplicate detection.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr, formatdate
from typing import List, Dict, Any

from src.email.thread_analyzer import (
    EmailThreadAnalyzer, ThreadType, ConversationRole, ThreadCorrelation,
    ConversationContext, ThreadDuplicateCheck, ConversationParticipant
)
from src.email.content_extractor import EmailHeaders, ThreadAnalysis


class TestEmailThreadAnalyzer:
    """Test suite for EmailThreadAnalyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create thread analyzer instance"""
        return EmailThreadAnalyzer(conversation_cache_size=100)
    
    @pytest.fixture
    def sample_headers(self):
        """Create sample email headers"""
        return EmailHeaders(
            message_id="<test-message-1@dol.gov>",
            sender="john.doe@dol.gov",
            sender_name="John Doe",
            recipients=["jane.smith@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Executive Order Implementation Status",
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
    
    @pytest.fixture
    def sample_email_msg(self):
        """Create sample email message"""
        msg = EmailMessage()
        msg['From'] = formataddr(("John Doe", "john.doe@dol.gov"))
        msg['To'] = "jane.smith@dol.gov"
        msg['Subject'] = "Executive Order Implementation Status"
        msg['Message-ID'] = "<test-message-1@dol.gov>"
        msg['Date'] = formatdate()
        msg.set_content("This is a test email for thread analysis.")
        return msg
    
    def test_analyze_new_email_thread(self, analyzer, sample_email_msg, sample_headers):
        """Test analysis of new email thread"""
        result = analyzer.analyze_email_thread(sample_email_msg, sample_headers)
        
        assert isinstance(result, ThreadAnalysis)
        assert result.thread_id == sample_headers.message_id.strip('<>')
        assert not result.is_reply
        assert not result.is_forward
        assert result.parent_message_id is None
        assert result.thread_depth == 0
        assert sample_headers.sender in result.conversation_participants
        assert result.original_subject == sample_headers.subject
        assert result.reply_chain_length == 0
    
    def test_analyze_reply_email_thread(self, analyzer):
        """Test analysis of reply email thread"""
        # Create reply email
        msg = EmailMessage()
        msg['From'] = "jane.smith@dol.gov"
        msg['To'] = "john.doe@dol.gov"
        msg['Subject'] = "Re: Executive Order Implementation Status"
        msg['Message-ID'] = "<reply-1@dol.gov>"
        msg['In-Reply-To'] = "<test-message-1@dol.gov>"
        msg['References'] = "<test-message-1@dol.gov>"
        msg.set_content("Thank you for the update. PMO approval is required.")
        
        headers = EmailHeaders(
            message_id="<reply-1@dol.gov>",
            sender="jane.smith@dol.gov",
            sender_name="Jane Smith",
            recipients=["john.doe@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Re: Executive Order Implementation Status",
            date=datetime.utcnow(),
            reply_to=None,
            in_reply_to="<test-message-1@dol.gov>",
            references=["<test-message-1@dol.gov>"],
            thread_topic=None,
            priority=None,
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
        
        result = analyzer.analyze_email_thread(msg, headers)
        
        assert result.is_reply
        assert not result.is_forward
        assert result.parent_message_id == "<test-message-1@dol.gov>"
        assert result.thread_id == "test-message-1@dol.gov"
        assert result.thread_depth == 1
        assert result.reply_chain_length >= 1
        assert result.original_subject == "Executive Order Implementation Status"
    
    def test_analyze_forwarded_email_thread(self, analyzer):
        """Test analysis of forwarded email thread"""
        msg = EmailMessage()
        msg['From'] = "director@dol.gov"
        msg['To'] = "team@dol.gov"
        msg['Subject'] = "Fwd: Executive Order Implementation Status"
        msg['Message-ID'] = "<forward-1@dol.gov>"
        msg.set_content("""
        ---------- Forwarded message ---------
        From: John Doe <john.doe@dol.gov>
        To: Jane Smith <jane.smith@dol.gov>
        Subject: Executive Order Implementation Status
        
        This is the original message content.
        """)
        
        headers = EmailHeaders(
            message_id="<forward-1@dol.gov>",
            sender="director@dol.gov",
            sender_name="Director",
            recipients=["team@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Fwd: Executive Order Implementation Status",
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
        
        result = analyzer.analyze_email_thread(msg, headers)
        
        assert not result.is_reply
        assert result.is_forward
        assert result.thread_id == headers.message_id.strip('<>')
        assert result.original_subject == "Executive Order Implementation Status"
        assert len(result.conversation_participants) >= 2  # Should extract forwarded participants
    
    def test_track_conversation_context_new(self, analyzer, sample_email_msg, sample_headers):
        """Test tracking new conversation context"""
        thread_analysis = analyzer.analyze_email_thread(sample_email_msg, sample_headers)
        context = analyzer.track_conversation_context(sample_email_msg, sample_headers, thread_analysis)
        
        assert isinstance(context, ConversationContext)
        assert context.thread_id == thread_analysis.thread_id
        assert len(context.participants) >= 1
        assert len(context.message_timeline) == 1
        assert context.subject_evolution == [sample_headers.subject]
        assert isinstance(context.workflow_correlation, ThreadCorrelation)
    
    def test_track_conversation_context_update(self, analyzer):
        """Test updating existing conversation context"""
        # Create initial email
        msg1 = EmailMessage()
        msg1['From'] = "john.doe@dol.gov"
        msg1['To'] = "jane.smith@dol.gov"
        msg1['Subject'] = "Project Status Update"
        msg1['Message-ID'] = "<msg-1@dol.gov>"
        msg1.set_content("Initial project status update.")
        
        headers1 = EmailHeaders(
            message_id="<msg-1@dol.gov>",
            sender="john.doe@dol.gov",
            sender_name="John Doe",
            recipients=["jane.smith@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Project Status Update",
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
        
        # Track initial conversation
        thread1 = analyzer.analyze_email_thread(msg1, headers1)
        context1 = analyzer.track_conversation_context(msg1, headers1, thread1)
        
        # Create reply email
        msg2 = EmailMessage()
        msg2['From'] = "jane.smith@dol.gov"
        msg2['To'] = "john.doe@dol.gov"
        msg2['Subject'] = "Re: Project Status Update"
        msg2['Message-ID'] = "<msg-2@dol.gov>"
        msg2['In-Reply-To'] = "<msg-1@dol.gov>"
        msg2['References'] = "<msg-1@dol.gov>"
        msg2.set_content("Thanks for the update. PMO approval needed.")
        
        headers2 = EmailHeaders(
            message_id="<msg-2@dol.gov>",
            sender="jane.smith@dol.gov",
            sender_name="Jane Smith",
            recipients=["john.doe@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Re: Project Status Update",
            date=datetime.utcnow() + timedelta(minutes=30),
            reply_to=None,
            in_reply_to="<msg-1@dol.gov>",
            references=["<msg-1@dol.gov>"],
            thread_topic=None,
            priority=None,
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
        
        # Track updated conversation
        thread2 = analyzer.analyze_email_thread(msg2, headers2)
        context2 = analyzer.track_conversation_context(msg2, headers2, thread2)
        
        # Should be same conversation ID
        assert context2.conversation_id == context1.conversation_id
        assert len(context2.message_timeline) == 2
        assert len(context2.participants) >= 2
        assert context2.updated_at > context1.created_at
    
    def test_detect_pmo_response_correlation(self, analyzer, sample_headers):
        """Test PMO response correlation detection"""
        # Create PMO response content
        pmo_content = """
        Thank you for your request. After review by the PMO team, 
        your project proposal has been APPROVED for implementation.
        
        Task ID: PROJ-2024-001
        Approval ID: PMO-APPROVAL-456
        
        Please proceed with the next phase as outlined in your proposal.
        """
        
        thread_analysis = ThreadAnalysis(
            thread_id="<original-request@dol.gov>",
            is_reply=True,
            is_forward=False,
            parent_message_id="<original-request@dol.gov>",
            thread_depth=1,
            conversation_participants={"john.doe@dol.gov", "pmo@dol.gov"},
            thread_subject="Project Approval Request",
            original_subject="Project Approval Request",
            reply_chain_length=1
        )
        
        correlation = analyzer.detect_pmo_response_correlation(
            sample_headers, pmo_content, thread_analysis
        )
        
        assert isinstance(correlation, ThreadCorrelation)
        assert correlation.workflow_type == ThreadType.PMO_RESPONSE_CHAIN
        assert correlation.correlation_confidence > 0.5
        assert "PROJ-2024-001" in correlation.related_task_ids
        assert "PMO-APPROVAL-456" in correlation.approval_request_ids
        assert correlation.original_request_id == "<original-request@dol.gov>"
    
    def test_detect_developer_update_correlation(self, analyzer, sample_headers):
        """Test developer update correlation detection"""
        dev_content = """
        Development update for Task #DEV-789:
        
        Progress: 75% complete
        - Code implementation finished
        - Unit tests written and passing
        - Integration testing in progress
        
        Blockers: None
        ETA: End of week
        """
        
        thread_analysis = ThreadAnalysis(
            thread_id="<dev-task@dol.gov>",
            is_reply=False,
            is_forward=False,
            parent_message_id=None,
            thread_depth=0,
            conversation_participants={"developer@dol.gov", "manager@dol.gov"},
            thread_subject="Development Progress Update",
            original_subject="Development Progress Update",
            reply_chain_length=0
        )
        
        correlation = analyzer.detect_pmo_response_correlation(
            sample_headers, dev_content, thread_analysis
        )
        
        assert correlation.workflow_type == ThreadType.DEVELOPER_UPDATE_CHAIN
        assert "DEV-789" in correlation.related_task_ids
    
    def test_detect_executive_request_correlation(self, analyzer, sample_headers):
        """Test executive request correlation detection"""
        exec_content = """
        Executive Summary Request
        
        Please prepare a comprehensive report on the current status of 
        Executive Order implementation for the Secretary's briefing.
        
        Required metrics:
        - Performance dashboard data
        - Strategic milestone progress
        - Policy compliance status
        
        Priority: HIGH
        Deadline: Tomorrow 9 AM
        """
        
        thread_analysis = ThreadAnalysis(
            thread_id="<exec-request@dol.gov>",
            is_reply=False,
            is_forward=False,
            parent_message_id=None,
            thread_depth=0,
            conversation_participants={"secretary@dol.gov", "staff@dol.gov"},
            thread_subject="Executive Summary Request",
            original_subject="Executive Summary Request",
            reply_chain_length=0
        )
        
        correlation = analyzer.detect_pmo_response_correlation(
            sample_headers, exec_content, thread_analysis
        )
        
        assert correlation.workflow_type == ThreadType.EXECUTIVE_REQUEST_CHAIN
        assert correlation.correlation_confidence > 0.3
    
    def test_detect_thread_based_duplicates_exact(self, analyzer, sample_headers):
        """Test exact duplicate detection"""
        content = "This is a test email content."
        
        thread_analysis = ThreadAnalysis(
            thread_id="<test@dol.gov>",
            is_reply=False,
            is_forward=False,
            parent_message_id=None,
            thread_depth=0,
            conversation_participants={"test@dol.gov"},
            thread_subject="Test Subject",
            original_subject="Test Subject",
            reply_chain_length=0
        )
        
        # First call should not be duplicate
        result1 = analyzer.detect_thread_based_duplicates(sample_headers, content, thread_analysis)
        assert not result1.is_duplicate
        assert result1.duplicate_type == 'none'
        assert result1.confidence_score == 0.0
    
    def test_conversation_participant_role_detection(self, analyzer):
        """Test participant role detection"""
        # Test PMO role
        pmo_role = analyzer._determine_participant_role("pmo.manager@dol.gov")
        assert pmo_role == ConversationRole.PMO_RESPONDER
        
        # Test developer role
        dev_role = analyzer._determine_participant_role("dev.engineer@dol.gov")
        assert dev_role == ConversationRole.DEVELOPER
        
        # Test executive role
        exec_role = analyzer._determine_participant_role("director@dol.gov")
        assert exec_role == ConversationRole.EXECUTIVE
        
        # Test external role
        external_role = analyzer._determine_participant_role("contractor@external.com")
        assert external_role == ConversationRole.EXTERNAL_PARTICIPANT
    
    def test_complex_thread_scenario(self, analyzer):
        """Test complex multi-message thread scenario"""
        messages = []
        headers_list = []
        
        # Original request
        msg1 = EmailMessage()
        msg1['From'] = "requester@dol.gov"
        msg1['To'] = "pmo@dol.gov"
        msg1['Subject'] = "New Executive Order Implementation Request"
        msg1['Message-ID'] = "<request-1@dol.gov>"
        msg1.set_content("Requesting approval for new EO implementation project.")
        messages.append(msg1)
        
        headers1 = EmailHeaders(
            message_id="<request-1@dol.gov>",
            sender="requester@dol.gov",
            sender_name="Requester",
            recipients=["pmo@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="New Executive Order Implementation Request",
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
        headers_list.append(headers1)
        
        # PMO response
        msg2 = EmailMessage()
        msg2['From'] = "pmo@dol.gov"
        msg2['To'] = "requester@dol.gov"
        msg2['Subject'] = "Re: New Executive Order Implementation Request"
        msg2['Message-ID'] = "<pmo-response-1@dol.gov>"
        msg2['In-Reply-To'] = "<request-1@dol.gov>"
        msg2['References'] = "<request-1@dol.gov>"
        msg2.set_content("Request approved. Task ID: EO-2024-001. Please proceed.")
        messages.append(msg2)
        
        headers2 = EmailHeaders(
            message_id="<pmo-response-1@dol.gov>",
            sender="pmo@dol.gov",
            sender_name="PMO Team",
            recipients=["requester@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Re: New Executive Order Implementation Request",
            date=datetime.utcnow() + timedelta(hours=2),
            reply_to=None,
            in_reply_to="<request-1@dol.gov>",
            references=["<request-1@dol.gov>"],
            thread_topic=None,
            priority=None,
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
        headers_list.append(headers2)
        
        # Developer update
        msg3 = EmailMessage()
        msg3['From'] = "developer@dol.gov"
        msg3['To'] = "pmo@dol.gov"
        msg3['Subject'] = "Re: New Executive Order Implementation Request - Progress Update"
        msg3['Message-ID'] = "<dev-update-1@dol.gov>"
        msg3['In-Reply-To'] = "<pmo-response-1@dol.gov>"
        msg3['References'] = "<request-1@dol.gov> <pmo-response-1@dol.gov>"
        msg3.set_content("Task EO-2024-001: 50% complete. Development on track.")
        messages.append(msg3)
        
        headers3 = EmailHeaders(
            message_id="<dev-update-1@dol.gov>",
            sender="developer@dol.gov",
            sender_name="Developer",
            recipients=["pmo@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Re: New Executive Order Implementation Request - Progress Update",
            date=datetime.utcnow() + timedelta(days=1),
            reply_to=None,
            in_reply_to="<pmo-response-1@dol.gov>",
            references=["<request-1@dol.gov>", "<pmo-response-1@dol.gov>"],
            thread_topic=None,
            priority=None,
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
        headers_list.append(headers3)
        
        # Process all messages
        contexts = []
        for msg, headers in zip(messages, headers_list):
            thread_analysis = analyzer.analyze_email_thread(msg, headers)
            context = analyzer.track_conversation_context(msg, headers, thread_analysis)
            contexts.append(context)
        
        # Verify thread continuity
        final_context = contexts[-1]
        assert len(final_context.message_timeline) == 3
        assert len(final_context.participants) >= 3
        assert final_context.workflow_correlation.workflow_type in [
            ThreadType.PMO_RESPONSE_CHAIN, ThreadType.MIXED_WORKFLOW_CHAIN
        ]
        assert "EO-2024-001" in final_context.workflow_correlation.related_task_ids
    
    def test_subject_evolution_tracking(self, analyzer):
        """Test subject evolution tracking in conversations"""
        # Create conversation with evolving subjects
        base_subject = "Project Planning Discussion"
        subjects = [
            base_subject,
            f"Re: {base_subject}",
            f"Re: {base_subject} - Updated Requirements",
            f"Re: {base_subject} - Final Approval Needed"
        ]
        
        conversation_id = None
        for i, subject in enumerate(subjects):
            msg = EmailMessage()
            msg['From'] = f"user{i}@dol.gov"
            msg['To'] = "team@dol.gov"
            msg['Subject'] = subject
            msg['Message-ID'] = f"<msg-{i}@dol.gov>"
            if i > 0:
                msg['In-Reply-To'] = f"<msg-{i-1}@dol.gov>"
                msg['References'] = " ".join([f"<msg-{j}@dol.gov>" for j in range(i)])
            msg.set_content(f"Message {i} content")
            
            headers = EmailHeaders(
                message_id=f"<msg-{i}@dol.gov>",
                sender=f"user{i}@dol.gov",
                sender_name=f"User {i}",
                recipients=["team@dol.gov"],
                cc_recipients=[],
                bcc_recipients=[],
                subject=subject,
                date=datetime.utcnow() + timedelta(hours=i),
                reply_to=None,
                in_reply_to=f"<msg-{i-1}@dol.gov>" if i > 0 else None,
                references=[f"<msg-{j}@dol.gov>" for j in range(i)] if i > 0 else [],
                thread_topic=None,
                priority=None,
                content_type="text/plain",
                encoding="utf-8",
                custom_headers={}
            )
            
            thread_analysis = analyzer.analyze_email_thread(msg, headers)
            context = analyzer.track_conversation_context(msg, headers, thread_analysis)
            
            if conversation_id is None:
                conversation_id = context.conversation_id
            else:
                assert context.conversation_id == conversation_id
        
        # Check final context
        final_context = analyzer.get_conversation_context(conversation_id)
        assert final_context is not None
        assert len(final_context.subject_evolution) == len(set(subjects))  # Unique subjects only
        assert base_subject in final_context.subject_evolution[0]
    
    def test_analyzer_statistics(self, analyzer, sample_email_msg, sample_headers):
        """Test analyzer statistics tracking"""
        initial_stats = analyzer.get_thread_analysis_stats()
        assert initial_stats['threads_analyzed'] == 0
        assert initial_stats['conversations_tracked'] == 0
        
        # Analyze some emails
        for i in range(3):
            headers = EmailHeaders(
                message_id=f"<test-{i}@dol.gov>",
                sender=f"user{i}@dol.gov",
                sender_name=f"User {i}",
                recipients=["team@dol.gov"],
                cc_recipients=[],
                bcc_recipients=[],
                subject=f"Test Subject {i}",
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
            
            thread_analysis = analyzer.analyze_email_thread(sample_email_msg, headers)
            analyzer.track_conversation_context(sample_email_msg, headers, thread_analysis)
        
        final_stats = analyzer.get_thread_analysis_stats()
        assert final_stats['threads_analyzed'] == 3
        assert final_stats['conversations_tracked'] == 3
        assert final_stats['cache_size'] > 0
        assert final_stats['conversation_cache_size'] > 0
    
    def test_cache_management(self, analyzer):
        """Test cache size management"""
        # Create analyzer with small cache
        small_analyzer = EmailThreadAnalyzer(conversation_cache_size=2)
        
        # Add more conversations than cache size
        for i in range(5):
            msg = EmailMessage()
            msg['From'] = f"user{i}@dol.gov"
            msg['To'] = "team@dol.gov"
            msg['Subject'] = f"Unique Subject {i}"
            msg['Message-ID'] = f"<unique-{i}@dol.gov>"
            msg.set_content(f"Content {i}")
            
            headers = EmailHeaders(
                message_id=f"<unique-{i}@dol.gov>",
                sender=f"user{i}@dol.gov",
                sender_name=f"User {i}",
                recipients=["team@dol.gov"],
                cc_recipients=[],
                bcc_recipients=[],
                subject=f"Unique Subject {i}",
                date=datetime.utcnow() + timedelta(minutes=i),
                reply_to=None,
                in_reply_to=None,
                references=[],
                thread_topic=None,
                priority=None,
                content_type="text/plain",
                encoding="utf-8",
                custom_headers={}
            )
            
            thread_analysis = small_analyzer.analyze_email_thread(msg, headers)
            small_analyzer.track_conversation_context(msg, headers, thread_analysis)
        
        stats = small_analyzer.get_thread_analysis_stats()
        assert stats['conversation_cache_size'] <= 2  # Should not exceed cache size
    
    def test_clear_caches(self, analyzer, sample_email_msg, sample_headers):
        """Test cache clearing functionality"""
        # Add some data to caches
        thread_analysis = analyzer.analyze_email_thread(sample_email_msg, sample_headers)
        analyzer.track_conversation_context(sample_email_msg, sample_headers, thread_analysis)
        
        stats_before = analyzer.get_thread_analysis_stats()
        assert stats_before['cache_size'] > 0
        assert stats_before['conversation_cache_size'] > 0
        
        # Clear caches
        analyzer.clear_caches()
        
        stats_after = analyzer.get_thread_analysis_stats()
        assert stats_after['cache_size'] == 0
        assert stats_after['conversation_cache_size'] == 0


class TestComplexThreadScenarios:
    """Test complex email thread scenarios"""
    
    @pytest.fixture
    def analyzer(self):
        return EmailThreadAnalyzer()
    
    def test_mixed_workflow_thread(self, analyzer):
        """Test thread with mixed workflow types"""
        # Create a thread that starts as PMO request, becomes dev update, then exec summary
        messages_data = [
            {
                'from': 'requester@dol.gov',
                'to': 'pmo@dol.gov',
                'subject': 'Budget Approval Request',
                'content': 'Requesting PMO approval for project budget increase.',
                'message_id': '<budget-req@dol.gov>',
                'in_reply_to': None,
                'references': []
            },
            {
                'from': 'pmo@dol.gov',
                'to': 'requester@dol.gov',
                'subject': 'Re: Budget Approval Request',
                'content': 'Budget approved. Task ID: BUDGET-2024-001',
                'message_id': '<pmo-approval@dol.gov>',
                'in_reply_to': '<budget-req@dol.gov>',
                'references': ['<budget-req@dol.gov>']
            },
            {
                'from': 'developer@dol.gov',
                'to': 'pmo@dol.gov',
                'subject': 'Re: Budget Approval Request - Development Update',
                'content': 'Development progress: 80% complete. Code review in progress.',
                'message_id': '<dev-update@dol.gov>',
                'in_reply_to': '<pmo-approval@dol.gov>',
                'references': ['<budget-req@dol.gov>', '<pmo-approval@dol.gov>']
            },
            {
                'from': 'director@dol.gov',
                'to': 'team@dol.gov',
                'subject': 'Re: Budget Approval Request - Executive Summary Needed',
                'content': 'Please prepare executive summary report for Secretary briefing.',
                'message_id': '<exec-summary@dol.gov>',
                'in_reply_to': '<dev-update@dol.gov>',
                'references': ['<budget-req@dol.gov>', '<pmo-approval@dol.gov>', '<dev-update@dol.gov>']
            }
        ]
        
        contexts = []
        for msg_data in messages_data:
            msg = EmailMessage()
            msg['From'] = msg_data['from']
            msg['To'] = msg_data['to']
            msg['Subject'] = msg_data['subject']
            msg['Message-ID'] = msg_data['message_id']
            if msg_data['in_reply_to']:
                msg['In-Reply-To'] = msg_data['in_reply_to']
            if msg_data['references']:
                msg['References'] = ' '.join(msg_data['references'])
            msg.set_content(msg_data['content'])
            
            headers = EmailHeaders(
                message_id=msg_data['message_id'],
                sender=msg_data['from'],
                sender_name=msg_data['from'].split('@')[0],
                recipients=[msg_data['to']],
                cc_recipients=[],
                bcc_recipients=[],
                subject=msg_data['subject'],
                date=datetime.utcnow(),
                reply_to=None,
                in_reply_to=msg_data['in_reply_to'],
                references=msg_data['references'],
                thread_topic=None,
                priority=None,
                content_type="text/plain",
                encoding="utf-8",
                custom_headers={}
            )
            
            thread_analysis = analyzer.analyze_email_thread(msg, headers)
            context = analyzer.track_conversation_context(msg, headers, thread_analysis)
            contexts.append(context)
        
        # Verify the final context captures the mixed workflow
        final_context = contexts[-1]
        assert final_context.thread_type in [
            ThreadType.MIXED_WORKFLOW_CHAIN, ThreadType.EXECUTIVE_REQUEST_CHAIN
        ]
        assert len(final_context.participants) >= 4
        assert 'BUDGET-2024-001' in final_context.workflow_correlation.related_task_ids
    
    def test_long_conversation_chain(self, analyzer):
        """Test very long conversation chain"""
        base_subject = "Long Running Project Discussion"
        num_messages = 20
        
        conversation_id = None
        for i in range(num_messages):
            msg = EmailMessage()
            msg['From'] = f"user{i % 5}@dol.gov"  # Rotate between 5 users
            msg['To'] = "team@dol.gov"
            msg['Subject'] = f"Re: {base_subject}" if i > 0 else base_subject
            msg['Message-ID'] = f"<long-msg-{i}@dol.gov>"
            if i > 0:
                msg['In-Reply-To'] = f"<long-msg-{i-1}@dol.gov>"
                msg['References'] = " ".join([f"<long-msg-{j}@dol.gov>" for j in range(i)])
            msg.set_content(f"Message {i} in long conversation chain.")
            
            headers = EmailHeaders(
                message_id=f"<long-msg-{i}@dol.gov>",
                sender=f"user{i % 5}@dol.gov",
                sender_name=f"User {i % 5}",
                recipients=["team@dol.gov"],
                cc_recipients=[],
                bcc_recipients=[],
                subject=f"Re: {base_subject}" if i > 0 else base_subject,
                date=datetime.utcnow() + timedelta(hours=i),
                reply_to=None,
                in_reply_to=f"<long-msg-{i-1}@dol.gov>" if i > 0 else None,
                references=[f"<long-msg-{j}@dol.gov>" for j in range(i)] if i > 0 else [],
                thread_topic=None,
                priority=None,
                content_type="text/plain",
                encoding="utf-8",
                custom_headers={}
            )
            
            thread_analysis = analyzer.analyze_email_thread(msg, headers)
            context = analyzer.track_conversation_context(msg, headers, thread_analysis)
            
            if conversation_id is None:
                conversation_id = context.conversation_id
            else:
                assert context.conversation_id == conversation_id
        
        # Verify final context
        final_context = analyzer.get_conversation_context(conversation_id)
        assert final_context is not None
        assert len(final_context.message_timeline) == num_messages
        assert len(final_context.participants) == 6  # 5 unique users + 1 recipient
        assert final_context.message_timeline[-1]['message_id'] == f"<long-msg-{num_messages-1}@dol.gov>"
    
    def test_branched_conversation(self, analyzer):
        """Test conversation that branches into multiple sub-threads"""
        # Original message
        original_msg = EmailMessage()
        original_msg['From'] = "initiator@dol.gov"
        original_msg['To'] = "team@dol.gov"
        original_msg['Subject'] = "Project Kickoff Discussion"
        original_msg['Message-ID'] = "<kickoff@dol.gov>"
        original_msg.set_content("Let's discuss the project kickoff requirements.")
        
        original_headers = EmailHeaders(
            message_id="<kickoff@dol.gov>",
            sender="initiator@dol.gov",
            sender_name="Initiator",
            recipients=["team@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Project Kickoff Discussion",
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
        
        # Process original
        original_thread = analyzer.analyze_email_thread(original_msg, original_headers)
        original_context = analyzer.track_conversation_context(original_msg, original_headers, original_thread)
        
        # Branch 1: PMO response
        pmo_msg = EmailMessage()
        pmo_msg['From'] = "pmo@dol.gov"
        pmo_msg['To'] = "initiator@dol.gov"
        pmo_msg['Subject'] = "Re: Project Kickoff Discussion - PMO Approval"
        pmo_msg['Message-ID'] = "<pmo-branch@dol.gov>"
        pmo_msg['In-Reply-To'] = "<kickoff@dol.gov>"
        pmo_msg['References'] = "<kickoff@dol.gov>"
        pmo_msg.set_content("PMO approval granted for project kickoff.")
        
        pmo_headers = EmailHeaders(
            message_id="<pmo-branch@dol.gov>",
            sender="pmo@dol.gov",
            sender_name="PMO Team",
            recipients=["initiator@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Re: Project Kickoff Discussion - PMO Approval",
            date=datetime.utcnow() + timedelta(hours=1),
            reply_to=None,
            in_reply_to="<kickoff@dol.gov>",
            references=["<kickoff@dol.gov>"],
            thread_topic=None,
            priority=None,
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
        
        # Branch 2: Developer response
        dev_msg = EmailMessage()
        dev_msg['From'] = "developer@dol.gov"
        dev_msg['To'] = "initiator@dol.gov"
        dev_msg['Subject'] = "Re: Project Kickoff Discussion - Technical Requirements"
        dev_msg['Message-ID'] = "<dev-branch@dol.gov>"
        dev_msg['In-Reply-To'] = "<kickoff@dol.gov>"
        dev_msg['References'] = "<kickoff@dol.gov>"
        dev_msg.set_content("Technical requirements analysis completed.")
        
        dev_headers = EmailHeaders(
            message_id="<dev-branch@dol.gov>",
            sender="developer@dol.gov",
            sender_name="Developer",
            recipients=["initiator@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Re: Project Kickoff Discussion - Technical Requirements",
            date=datetime.utcnow() + timedelta(hours=2),
            reply_to=None,
            in_reply_to="<kickoff@dol.gov>",
            references=["<kickoff@dol.gov>"],
            thread_topic=None,
            priority=None,
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
        
        # Process branches
        pmo_thread = analyzer.analyze_email_thread(pmo_msg, pmo_headers)
        pmo_context = analyzer.track_conversation_context(pmo_msg, pmo_headers, pmo_thread)
        
        dev_thread = analyzer.analyze_email_thread(dev_msg, dev_headers)
        dev_context = analyzer.track_conversation_context(dev_msg, dev_headers, dev_thread)
        
        # Both branches should be part of the same conversation
        assert pmo_context.conversation_id == original_context.conversation_id
        assert dev_context.conversation_id == original_context.conversation_id
        
        # Final context should have all messages
        final_context = analyzer.get_conversation_context(original_context.conversation_id)
        assert len(final_context.message_timeline) == 3
        assert len(final_context.participants) >= 3