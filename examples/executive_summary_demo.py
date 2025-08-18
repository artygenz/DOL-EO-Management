#!/usr/bin/env python3
"""
Executive Summary Email Generator Demo

This demo showcases the executive summary email generation capabilities
of the Email Agent system, including professional formatting, attachment
handling, and priority management for executive communications.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.email.email_generator import (
    EmailGenerator, 
    ExecutiveSummaryData, 
    AttachmentInfo,
    EmailGenerationError
)


def create_sample_metrics() -> Dict[str, Any]:
    """Create sample key performance indicators for the demo"""
    return {
        "emails_processed": {
            "value": "47,832",
            "label": "Emails Processed",
            "trend": "up",
            "change": "+18%"
        },
        "classification_accuracy": {
            "value": "98.9%",
            "label": "Classification Accuracy",
            "trend": "up",
            "change": "+0.4%"
        },
        "response_time": {
            "value": "1.8 sec",
            "label": "Avg Response Time",
            "trend": "down",
            "change": "-22%"
        },
        "system_uptime": {
            "value": "99.98%",
            "label": "System Uptime",
            "trend": "up",
            "change": "+0.01%"
        },
        "security_incidents": {
            "value": "2",
            "label": "Security Incidents",
            "trend": "down",
            "change": "-67%"
        },
        "cost_savings": {
            "value": "$125K",
            "label": "Cost Savings",
            "trend": "up",
            "change": "+$45K"
        }
    }


def create_comprehensive_executive_summary() -> ExecutiveSummaryData:
    """Create a comprehensive executive summary for demonstration"""
    return ExecutiveSummaryData(
        report_title="Q1 2025 Email Agent Performance Review",
        reporting_period="January - March 2025",
        executive_name="Secretary of Labor",
        executive_email="secretary@dol.gov",
        key_metrics=create_sample_metrics(),
        achievements=[
            "Successfully processed 47,832 emails with 98.9% classification accuracy",
            "Reduced average response time by 22% through system optimizations",
            "Achieved 99.98% system uptime with only 2 minor security incidents",
            "Generated $125,000 in cost savings through automation improvements",
            "Completed federal compliance audit with zero findings",
            "Implemented new executive dashboard with real-time metrics"
        ],
        challenges=[
            "Increased email volume during tax season requiring additional resources",
            "Two security incidents related to phishing attempts were successfully mitigated",
            "Staff training required for new classification algorithms",
            "Budget constraints limiting infrastructure expansion",
            "Integration challenges with legacy government systems"
        ],
        recommendations=[
            "Approve additional server capacity to handle peak email volumes",
            "Invest in advanced threat detection systems for enhanced security",
            "Establish quarterly training program for all technical staff",
            "Allocate budget for infrastructure modernization initiative",
            "Create cross-agency collaboration framework for system integration",
            "Implement predictive analytics for proactive capacity planning"
        ],
        attachments=[
            "Q1_2025_Performance_Dashboard.pdf",
            "Email_Volume_Analysis_Report.xlsx",
            "Security_Incident_Summary.docx",
            "Cost_Benefit_Analysis.pdf",
            "Compliance_Audit_Results.pdf",
            "Infrastructure_Upgrade_Proposal.pptx"
        ],
        next_steps=[
            "Present infrastructure upgrade proposal to executive committee by April 15th",
            "Begin procurement process for enhanced security systems by May 1st",
            "Launch quarterly staff training program by April 30th",
            "Initiate cross-agency integration pilot program by June 1st",
            "Deploy predictive analytics dashboard by July 15th",
            "Complete budget allocation review by April 10th"
        ],
        priority_level="CRITICAL",
        requires_acknowledgment=True,
        confidentiality_level="SENSITIVE"
    )


def create_quarterly_summary() -> ExecutiveSummaryData:
    """Create a standard quarterly summary"""
    return ExecutiveSummaryData(
        report_title="Q4 2024 Operations Summary",
        reporting_period="October - December 2024",
        executive_name="Deputy Secretary",
        executive_email="deputy.secretary@dol.gov",
        key_metrics={
            "emails_processed": "38,421",
            "accuracy_rate": "97.8%",
            "uptime": "99.95%"
        },
        achievements=[
            "Maintained high system performance during holiday season",
            "Successfully implemented new security protocols",
            "Completed year-end compliance requirements"
        ],
        challenges=[
            "Higher than expected email volume during December",
            "Temporary staff shortage due to holiday schedules"
        ],
        recommendations=[
            "Plan for increased capacity during future holiday periods",
            "Develop cross-training program for critical roles"
        ],
        attachments=[
            "Q4_Performance_Report.pdf",
            "Year_End_Summary.xlsx"
        ],
        next_steps=[
            "Review capacity planning for Q1 2025",
            "Implement cross-training program"
        ],
        priority_level="HIGH"
    )


def create_security_incident_summary() -> ExecutiveSummaryData:
    """Create a security incident executive summary"""
    return ExecutiveSummaryData(
        report_title="Security Incident Response Summary - March 2025",
        reporting_period="March 15-20, 2025",
        executive_name="Chief Information Security Officer",
        executive_email="ciso@dol.gov",
        key_metrics={
            "incidents_detected": "3",
            "response_time": "12 minutes",
            "systems_affected": "0",
            "data_compromised": "None"
        },
        achievements=[
            "Detected and contained all security threats within 12 minutes",
            "Zero data compromise or system downtime",
            "Successfully tested incident response procedures"
        ],
        challenges=[
            "Sophisticated phishing campaign targeting government employees",
            "Increased attack frequency during high-profile government events"
        ],
        recommendations=[
            "Enhance employee security awareness training",
            "Implement additional email filtering layers",
            "Increase security monitoring during high-risk periods"
        ],
        attachments=[
            "Security_Incident_Details.pdf",
            "Threat_Analysis_Report.docx",
            "Response_Timeline.xlsx"
        ],
        next_steps=[
            "Conduct security awareness training for all staff",
            "Review and update incident response procedures",
            "Implement enhanced email filtering by April 1st"
        ],
        priority_level="URGENT"
    )


def demonstrate_executive_summary_generation():
    """Demonstrate executive summary email generation with various scenarios"""
    print("=" * 80)
    print("EXECUTIVE SUMMARY EMAIL GENERATOR DEMO")
    print("=" * 80)
    print()
    
    # Initialize email generator
    try:
        email_generator = EmailGenerator("templates/email")
        print("✓ Email generator initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize email generator: {e}")
        return
    
    # Demo scenarios
    scenarios = [
        ("Comprehensive Q1 Performance Review", create_comprehensive_executive_summary()),
        ("Standard Quarterly Summary", create_quarterly_summary()),
        ("Security Incident Summary", create_security_incident_summary())
    ]
    
    for scenario_name, summary_data in scenarios:
        print(f"\n{'-' * 60}")
        print(f"SCENARIO: {scenario_name}")
        print(f"{'-' * 60}")
        
        try:
            # Generate executive summary email
            rendered_email = email_generator.generate_executive_summary_email(
                summary_data,
                sender_name="Email Agent System",
                sender_title="Automated Reporting System",
                priority_level=summary_data.priority_level
            )
            
            print(f"✓ Executive summary generated successfully")
            print(f"  Subject: {rendered_email.subject}")
            print(f"  Recipient: {rendered_email.recipient_email}")
            print(f"  Priority: {rendered_email.metadata.get('priority_level', 'N/A')}")
            print(f"  Compliance Level: {rendered_email.compliance_level.value}")
            print(f"  Correlation ID: {rendered_email.correlation_id}")
            print(f"  Attachments: {summary_data.attachments and len(summary_data.attachments) or 0}")
            
            # Show content preview
            print(f"\n  Content Preview:")
            content_preview = rendered_email.body_text[:300].replace('\n', ' ')
            print(f"  {content_preview}...")
            
            # Show key features
            print(f"\n  Key Features:")
            if summary_data.key_metrics:
                print(f"    • {len(summary_data.key_metrics)} key performance indicators")
            if summary_data.achievements:
                print(f"    • {len(summary_data.achievements)} achievements highlighted")
            if summary_data.challenges:
                print(f"    • {len(summary_data.challenges)} challenges identified")
            if summary_data.recommendations:
                print(f"    • {len(summary_data.recommendations)} strategic recommendations")
            if summary_data.attachments:
                print(f"    • {len(summary_data.attachments)} supporting documents attached")
            
            # Validate compliance
            print(f"\n  Compliance Validation:")
            print(f"    • Government email domain: {'✓' if rendered_email.sender_email.endswith('.gov') else '✗'}")
            print(f"    • Correlation ID present: {'✓' if rendered_email.correlation_id else '✗'}")
            print(f"    • Official identification: {'✓' if 'U.S. Department of Labor' in rendered_email.body_html else '✗'}")
            print(f"    • Executive communication flag: {'✓' if rendered_email.metadata.get('executive_communication') else '✗'}")
            
        except EmailGenerationError as e:
            print(f"✗ Email generation failed: {e}")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
    
    print(f"\n{'-' * 60}")
    print("PRIORITY LEVEL DEMONSTRATION")
    print(f"{'-' * 60}")
    
    # Demonstrate different priority levels
    priority_levels = ["CRITICAL", "URGENT", "HIGH", "MEDIUM", "LOW"]
    base_summary = create_quarterly_summary()
    
    for priority in priority_levels:
        try:
            rendered_email = email_generator.generate_executive_summary_email(
                base_summary,
                priority_level=priority
            )
            
            priority_indicator = rendered_email.subject.split(':')[0]
            delivery_priority = rendered_email.metadata.get('delivery_priority', 'normal')
            
            print(f"  {priority:8} → {priority_indicator:15} (Delivery: {delivery_priority})")
            
        except Exception as e:
            print(f"  {priority:8} → Error: {e}")
    
    print(f"\n{'-' * 60}")
    print("ATTACHMENT HANDLING DEMONSTRATION")
    print(f"{'-' * 60}")
    
    # Demonstrate enhanced attachment handling
    attachment_info = [
        AttachmentInfo(
            filename="Executive_Dashboard.pdf",
            description="Real-time performance dashboard with key metrics",
            file_type="PDF",
            size_mb=3.2,
            is_dashboard_report=True,
            requires_executive_review=True
        ),
        AttachmentInfo(
            filename="Budget_Analysis.xlsx",
            description="Detailed budget analysis and cost projections",
            file_type="Excel Spreadsheet",
            size_mb=1.8,
            is_dashboard_report=False,
            requires_executive_review=True
        )
    ]
    
    enhanced_summary = ExecutiveSummaryData(
        report_title="Enhanced Attachment Demo",
        reporting_period="Demo Period",
        executive_name="Demo Executive",
        executive_email="demo@dol.gov",
        achievements=["Demo achievement"],
        attachment_info=attachment_info,
        attachments=["Executive_Dashboard.pdf", "Budget_Analysis.xlsx"]
    )
    
    try:
        rendered_email = email_generator.generate_executive_summary_email(enhanced_summary)
        print(f"✓ Enhanced attachment handling demonstrated")
        print(f"  Attachment count in metadata: {rendered_email.metadata.get('attachment_count', 0)}")
        
        for i, attachment in enumerate(attachment_info, 1):
            print(f"  Attachment {i}: {attachment.filename} ({attachment.file_type}, {attachment.size_mb}MB)")
            print(f"    Description: {attachment.description}")
            print(f"    Dashboard Report: {'Yes' if attachment.is_dashboard_report else 'No'}")
            
    except Exception as e:
        print(f"✗ Enhanced attachment demo failed: {e}")
    
    print(f"\n{'=' * 80}")
    print("DEMO COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print()
    print("The executive summary email generator provides:")
    print("• Professional executive-level formatting and presentation")
    print("• Comprehensive attachment handling with metadata")
    print("• Priority-based subject line formatting and delivery options")
    print("• Government compliance validation and audit trail")
    print("• Rich content support including metrics, achievements, and recommendations")
    print("• Flexible template system for different executive communication needs")
    print()


if __name__ == "__main__":
    demonstrate_executive_summary_generation()