"""
Integration tests for complex email thread scenarios

Tests real-world email thread patterns including PMO workflows,
multi-participant conversations, and workflow correlation scenarios.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr, formatdate

from src.email.thread_analyzer import EmailThreadAnalyzer, ThreadType
from src.email.content_extractor import EnhancedContentExtractor, EmailHeaders


class TestComplexThreadIntegration:
    """Integration tests for complex thread scenarios"""
    
    @pytest.fixture
    def analyzer(self):
        return EmailThreadAnalyzer(conversation_cache_size=50)
    
    @pytest.fixture
    def content_extractor(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            yield EnhancedContentExtractor(temp_dir=temp_dir)
    
    def create_email_message(self, from_addr, to_addr, subject, content, 
                           message_id, in_reply_to=None, references=None):
        """Helper to create email messages"""
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
    
    def test_end_to_end_pmo_workflow(self, analyzer, content_extractor):
        """Test complete PMO workflow from request to completion"""
        # Step 1: Initial request
        request_msg = self.create_email_message(
            from_addr="project.manager@dol.gov",
            to_addr="pmo@dol.gov",
            subject="Executive Order Implementation - Budget Approval Request",
            content="""
            Dear PMO Team,
            
            I am requesting approval for additional budget allocation for the 
            Executive Order implementation project.
            
            Project Details:
            - Project ID: EO-IMPL-2024-001
            - Additional Budget: $50,000
            - Justification: Additional security requirements
            
            Please review and approve at your earliest convenience.
            
            Best regards,
            Project Manager
            """,
            message_id="<eo-budget-request@dol.gov>"
        )
        
        # Extract and analyze
        request_content = content_extractor.extract_email_content(request_msg)
        request_thread = analyzer.analyze_email_thread(request_msg, request_content.headers)
        request_context = analyzer.track_conversation_context(
            request_msg, request_content.headers, request_thread
        )
        
        # Verify initial analysis
        assert request_thread.thread_id == "eo-budget-request@dol.gov"
        assert not request_thread.is_reply
        # Initial request should be classified as PMO-related due to content
        assert request_context.thread_type in [ThreadType.NEW_CONVERSATION, ThreadType.PMO_RESPONSE_CHAIN]
        
        # Step 2: PMO Response
        pmo_response_msg = self.create_email_message(
            from_addr="pmo.manager@dol.gov",
            to_addr="project.manager@dol.gov",
            subject="Re: Executive Order Implementation - Budget Approval Request",
            content="""
            Dear Project Manager,
            
            Thank you for your budget approval request.
            
            After review, your request has been APPROVED.
            
            Approval Details:
            - Approval ID: PMO-APPROVAL-2024-156
            - Approved Amount: $50,000
            - Task ID: BUDGET-TASK-789
            
            Please proceed with the implementation.
            
            Best regards,
            PMO Manager
            """,
            message_id="<pmo-approval-response@dol.gov>",
            in_reply_to="<eo-budget-request@dol.gov>",
            references=["<eo-budget-request@dol.gov>"]
        )
        
        # Extract and analyze PMO response
        pmo_content = content_extractor.extract_email_content(pmo_response_msg)
        pmo_thread = analyzer.analyze_email_thread(pmo_response_msg, pmo_content.headers)
        pmo_context = analyzer.track_conversation_context(
            pmo_response_msg, pmo_content.headers, pmo_thread
        )
        
        # Verify PMO response analysis
        assert pmo_thread.is_reply
        assert pmo_thread.parent_message_id == "<eo-budget-request@dol.gov>"
        assert pmo_context.workflow_correlation.workflow_type == ThreadType.PMO_RESPONSE_CHAIN
        assert pmo_context.workflow_correlation.correlation_confidence > 0.5
        assert "PMO-APPROVAL-2024-156" in pmo_context.workflow_correlation.approval_request_ids
        assert "BUDGET-TASK-789" in pmo_context.workflow_correlation.related_task_ids
        
        # Verify conversation continuity
        assert pmo_context.conversation_id == request_context.conversation_id
        assert len(pmo_context.message_timeline) == 2
        
        # Step 3: Developer Update
        dev_update_msg = self.create_email_message(
            from_addr="senior.developer@dol.gov",
            to_addr="pmo.manager@dol.gov",
            subject="Re: Executive Order Implementation - Development Progress Update",
            content="""
            PMO Team,
            
            Development update for Task BUDGET-TASK-789:
            
            Progress: 75% complete
            - Security framework implementation: DONE
            - Integration testing: IN PROGRESS
            - Documentation: PENDING
            
            Blockers: None
            ETA: End of week
            
            Next milestone: Security review completion
            
            Developer Team
            """,
            message_id="<dev-progress-update@dol.gov>",
            in_reply_to="<pmo-approval-response@dol.gov>",
            references=["<eo-budget-request@dol.gov>", "<pmo-approval-response@dol.gov>"]
        )
        
        # Extract and analyze developer update
        dev_content = content_extractor.extract_email_content(dev_update_msg)
        dev_thread = analyzer.analyze_email_thread(dev_update_msg, dev_content.headers)
        dev_context = analyzer.track_conversation_context(
            dev_update_msg, dev_content.headers, dev_thread
        )
        
        # Verify developer update analysis
        assert dev_thread.thread_depth == 2
        assert dev_context.thread_type in [
            ThreadType.DEVELOPER_UPDATE_CHAIN, ThreadType.MIXED_WORKFLOW_CHAIN
        ]
        assert "BUDGET-TASK-789" in dev_context.workflow_correlation.related_task_ids
        
        # Verify final conversation state
        final_context = analyzer.get_conversation_context(request_context.conversation_id)
        assert len(final_context.message_timeline) == 3
        assert len(final_context.participants) >= 3
        assert final_context.workflow_correlation.correlation_confidence > 0.6
    
    def test_multi_branch_conversation_merge(self, analyzer, content_extractor):
        """Test conversation that branches and merges back"""
        # Original discussion
        original_msg = self.create_email_message(
            from_addr="team.lead@dol.gov",
            to_addr="development.team@dol.gov",
            subject="Security Implementation Strategy Discussion",
            content="Let's discuss the security implementation approach for the new system.",
            message_id="<security-discussion@dol.gov>"
        )
        
        original_content = content_extractor.extract_email_content(original_msg)
        original_thread = analyzer.analyze_email_thread(original_msg, original_content.headers)
        original_context = analyzer.track_conversation_context(
            original_msg, original_content.headers, original_thread
        )
        
        # Branch 1: Technical discussion
        tech_branch_msg = self.create_email_message(
            from_addr="security.architect@dol.gov",
            to_addr="team.lead@dol.gov",
            subject="Re: Security Implementation Strategy Discussion - Technical Approach",
            content="I recommend using OAuth 2.0 with PKCE for authentication.",
            message_id="<tech-branch@dol.gov>",
            in_reply_to="<security-discussion@dol.gov>",
            references=["<security-discussion@dol.gov>"]
        )
        
        # Branch 2: Compliance discussion
        compliance_branch_msg = self.create_email_message(
            from_addr="compliance.officer@dol.gov",
            to_addr="team.lead@dol.gov",
            subject="Re: Security Implementation Strategy Discussion - Compliance Requirements",
            content="We need to ensure FISMA compliance for all security implementations.",
            message_id="<compliance-branch@dol.gov>",
            in_reply_to="<security-discussion@dol.gov>",
            references=["<security-discussion@dol.gov>"]
        )
        
        # Process branches
        for branch_msg in [tech_branch_msg, compliance_branch_msg]:
            branch_content = content_extractor.extract_email_content(branch_msg)
            branch_thread = analyzer.analyze_email_thread(branch_msg, branch_content.headers)
            branch_context = analyzer.track_conversation_context(
                branch_msg, branch_content.headers, branch_thread
            )
            
            # Should be same conversation
            assert branch_context.conversation_id == original_context.conversation_id
        
        # Merge response addressing both branches
        merge_msg = self.create_email_message(
            from_addr="team.lead@dol.gov",
            to_addr="development.team@dol.gov",
            subject="Re: Security Implementation Strategy Discussion - Final Decision",
            content="""
            Thank you all for the input.
            
            Final decision:
            - Technical: We'll implement OAuth 2.0 with PKCE as recommended
            - Compliance: Full FISMA compliance will be maintained
            
            Let's proceed with implementation.
            """,
            message_id="<merge-decision@dol.gov>",
            in_reply_to="<compliance-branch@dol.gov>",
            references=["<security-discussion@dol.gov>", "<tech-branch@dol.gov>", "<compliance-branch@dol.gov>"]
        )
        
        merge_content = content_extractor.extract_email_content(merge_msg)
        merge_thread = analyzer.analyze_email_thread(merge_msg, merge_content.headers)
        merge_context = analyzer.track_conversation_context(
            merge_msg, merge_content.headers, merge_thread
        )
        
        # Verify merge
        assert merge_context.conversation_id == original_context.conversation_id
        assert len(merge_context.message_timeline) == 4
        assert merge_thread.thread_depth == 3  # References all previous messages
    
    def test_cross_workflow_correlation(self, analyzer, content_extractor):
        """Test correlation across different workflow types"""
        workflows = [
            {
                'type': 'executive_request',
                'from': 'assistant.secretary@dol.gov',
                'subject': 'Executive Summary Request - Q4 Performance',
                'content': 'Please prepare executive summary for Secretary briefing on Q4 performance metrics.',
                'message_id': '<exec-request@dol.gov>'
            },
            {
                'type': 'pmo_response',
                'from': 'pmo.director@dol.gov',
                'subject': 'Re: Executive Summary Request - PMO Data Required',
                'content': 'PMO approval needed for data release. Task ID: DATA-RELEASE-001',
                'message_id': '<pmo-data-response@dol.gov>',
                'in_reply_to': '<exec-request@dol.gov>',
                'references': ['<exec-request@dol.gov>']
            },
            {
                'type': 'developer_update',
                'from': 'data.engineer@dol.gov',
                'subject': 'Re: Executive Summary Request - Data Extraction Complete',
                'content': 'Data extraction for Task DATA-RELEASE-001 completed. Dashboard updated.',
                'message_id': '<dev-data-complete@dol.gov>',
                'in_reply_to': '<pmo-data-response@dol.gov>',
                'references': ['<exec-request@dol.gov>', '<pmo-data-response@dol.gov>']
            }
        ]
        
        contexts = []
        for workflow in workflows:
            msg = self.create_email_message(
                from_addr=workflow['from'],
                to_addr='team@dol.gov',
                subject=workflow['subject'],
                content=workflow['content'],
                message_id=workflow['message_id'],
                in_reply_to=workflow.get('in_reply_to'),
                references=workflow.get('references')
            )
            
            content = content_extractor.extract_email_content(msg)
            thread = analyzer.analyze_email_thread(msg, content.headers)
            context = analyzer.track_conversation_context(msg, content.headers, thread)
            contexts.append(context)
        
        # Verify cross-workflow correlation
        final_context = contexts[-1]
        assert final_context.workflow_correlation.workflow_type == ThreadType.MIXED_WORKFLOW_CHAIN
        assert 'DATA-RELEASE-001' in final_context.workflow_correlation.related_task_ids
        assert len(final_context.participants) >= 3
        
        # All should be same conversation
        conversation_ids = [ctx.conversation_id for ctx in contexts]
        assert len(set(conversation_ids)) == 1  # All same conversation ID