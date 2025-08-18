#!/usr/bin/env python3
"""
Comprehensive Metrics Collection System Demo

This demo showcases the MetricsCollector's capabilities for monitoring
email processing performance, classification accuracy, connection health,
and security incidents in real-time.

Requirements: 7.1, 7.2
"""

import time
import json
import random
import threading
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.email.metrics_collector import (
    MetricsCollector, SecurityIncidentType
)


def simulate_email_processing(collector: MetricsCollector, num_emails: int = 50):
    """Simulate email processing with metrics collection"""
    print(f"\n🔄 Simulating processing of {num_emails} emails...")
    
    email_types = ["NEW_EO", "PMO_RESPONSE", "DEVELOPER_UPDATE", "EXECUTIVE_REQUEST"]
    
    for i in range(num_emails):
        email_uid = f"demo_email_{i:03d}"
        email_type = random.choice(email_types)
        
        # Start processing timer
        collector.start_processing_timer(email_uid)
        
        # Simulate variable processing time
        processing_time = random.uniform(0.05, 0.3)  # 50-300ms
        time.sleep(processing_time)
        
        # Simulate classification confidence
        confidence = random.uniform(0.6, 0.99)
        success = confidence > 0.7  # Fail if confidence too low
        
        # End processing timer
        collector.end_processing_timer(
            email_uid=email_uid,
            classification_type=email_type,
            confidence_score=confidence,
            success=success,
            error_type="LOW_CONFIDENCE" if not success else None
        )
        
        # Record classification accuracy (simulate ground truth)
        if success and random.random() > 0.1:  # 90% accuracy simulation
            actual_type = email_type
        else:
            # Simulate misclassification
            actual_type = random.choice([t for t in email_types if t != email_type])
        
        collector.record_classification_accuracy(
            email_type=email_type,
            predicted=email_type,
            actual=actual_type,
            confidence=confidence,
            manual_review=(confidence < 0.8)
        )
        
        # Show progress
        if (i + 1) % 10 == 0:
            print(f"  ✅ Processed {i + 1}/{num_emails} emails")
    
    print(f"✅ Completed processing {num_emails} emails")


def simulate_connection_monitoring(collector: MetricsCollector, duration_seconds: int = 30):
    """Simulate connection health monitoring"""
    print(f"\n🌐 Simulating connection monitoring for {duration_seconds} seconds...")
    
    connections = [
        ("imap_primary", "IMAP"),
        ("imap_backup", "IMAP"),
        ("smtp_outbound", "SMTP")
    ]
    
    def monitor_connection(conn_id: str, conn_type: str):
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            # Simulate connection health variations
            if random.random() > 0.8:  # 20% chance of issues
                status = random.choice(["DEGRADED", "FAILED"])
                response_time = random.uniform(500, 2000)  # Slow response
                error_count = random.randint(1, 5)
            else:
                status = "HEALTHY"
                response_time = random.uniform(50, 200)  # Normal response
                error_count = 0
            
            collector.record_connection_health(
                connection_id=conn_id,
                connection_type=conn_type,
                status=status,
                response_time_ms=response_time,
                error_count=error_count
            )
            
            time.sleep(2)  # Check every 2 seconds
    
    # Start monitoring threads
    threads = []
    for conn_id, conn_type in connections:
        thread = threading.Thread(target=monitor_connection, args=(conn_id, conn_type))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # Wait for monitoring to complete
    for thread in threads:
        thread.join()
    
    print("✅ Connection monitoring completed")


def simulate_security_incidents(collector: MetricsCollector):
    """Simulate security incidents"""
    print("\n🔒 Simulating security incidents...")
    
    incidents = [
        (SecurityIncidentType.MALWARE_DETECTED, "CRITICAL", "Trojan.Win32.Generic detected in attachment"),
        (SecurityIncidentType.PHISHING_ATTEMPT, "HIGH", "Suspicious links to fake government sites"),
        (SecurityIncidentType.UNAUTHORIZED_SENDER, "MEDIUM", "Email from unverified domain"),
        (SecurityIncidentType.SUSPICIOUS_CONTENT, "LOW", "Unusual keywords detected"),
        (SecurityIncidentType.ATTACHMENT_THREAT, "HIGH", "Executable file in email attachment")
    ]
    
    incident_ids = []
    for incident_type, severity, description in incidents:
        incident_id = collector.record_security_incident(
            incident_type=incident_type,
            severity=severity,
            description=description,
            email_uid=f"security_email_{len(incident_ids)}",
            sender=f"threat{len(incident_ids)}@suspicious.com"
        )
        incident_ids.append(incident_id)
        print(f"  🚨 Recorded {severity} incident: {incident_id}")
        time.sleep(0.5)
    
    # Simulate incident resolution
    print("\n🔧 Resolving some incidents...")
    for incident_id in incident_ids[:3]:  # Resolve first 3
        time.sleep(1)
        collector.resolve_security_incident(incident_id)
        print(f"  ✅ Resolved incident: {incident_id}")
    
    print("✅ Security incident simulation completed")


def display_metrics_dashboard(collector: MetricsCollector):
    """Display comprehensive metrics dashboard"""
    print("\n" + "="*80)
    print("📊 EMAIL AGENT METRICS DASHBOARD")
    print("="*80)
    
    # Processing Latency Metrics
    print("\n📈 PROCESSING LATENCY METRICS")
    print("-" * 40)
    latency_metrics = collector.get_processing_latency_metrics()
    print(f"Total Processed:     {latency_metrics['total_processed']:,}")
    print(f"Average Latency:     {latency_metrics['average_latency_ms']:.2f} ms")
    print(f"Median Latency:      {latency_metrics['median_latency_ms']:.2f} ms")
    print(f"95th Percentile:     {latency_metrics['p95_latency_ms']:.2f} ms")
    print(f"99th Percentile:     {latency_metrics['p99_latency_ms']:.2f} ms")
    print(f"Min/Max Latency:     {latency_metrics['min_latency_ms']:.2f} / {latency_metrics['max_latency_ms']:.2f} ms")
    
    # Throughput Metrics
    print("\n🚀 THROUGHPUT METRICS")
    print("-" * 40)
    throughput_metrics = collector.get_throughput_metrics()
    print(f"Emails per Hour:     {throughput_metrics['emails_per_hour']:.1f}")
    print(f"Emails per Minute:   {throughput_metrics['emails_per_minute']:.1f}")
    print(f"Total Emails:        {throughput_metrics['total_emails']:,}")
    print(f"Time Window:         {throughput_metrics['time_window_hours']:.2f} hours")
    
    # Classification Accuracy
    print("\n🎯 CLASSIFICATION ACCURACY")
    print("-" * 40)
    accuracy_metrics = collector.get_classification_accuracy_metrics()
    print(f"Overall Accuracy:    {accuracy_metrics['overall_accuracy']:.1f}%")
    print(f"Total Classifications: {accuracy_metrics['total_classifications']:,}")
    print("By Email Type:")
    for email_type, accuracy in accuracy_metrics['by_type'].items():
        print(f"  {email_type:20} {accuracy:.1f}%")
    
    # Connection Health
    print("\n🌐 CONNECTION HEALTH")
    print("-" * 40)
    connection_metrics = collector.get_connection_health_metrics()
    for conn_id, health in connection_metrics.items():
        status_emoji = {"HEALTHY": "✅", "DEGRADED": "⚠️", "FAILED": "❌"}.get(health['status'], "❓")
        print(f"{status_emoji} {conn_id:15} ({health['connection_type']})")
        print(f"    Status:          {health['status']}")
        print(f"    Uptime:          {health['uptime_percentage']:.1f}%")
        print(f"    Avg Response:    {health['average_response_time_ms']:.1f} ms")
        print(f"    Total Errors:    {health['total_errors']}")
    
    # Security Incidents
    print("\n🔒 SECURITY INCIDENTS")
    print("-" * 40)
    security_metrics = collector.get_security_incident_metrics()
    print(f"Total Incidents:     {security_metrics['total_incidents']:,}")
    print(f"Resolved:            {security_metrics['resolved_incidents']:,}")
    print(f"Unresolved:          {security_metrics['unresolved_incidents']:,}")
    print(f"Resolution Rate:     {security_metrics['resolution_rate']:.1f}%")
    
    if security_metrics['by_type']:
        print("By Incident Type:")
        for incident_type, count in security_metrics['by_type'].items():
            print(f"  {incident_type:20} {count:,}")
    
    if security_metrics['by_severity']:
        print("By Severity:")
        for severity, count in security_metrics['by_severity'].items():
            print(f"  {severity:20} {count:,}")
    
    # System Uptime
    print("\n⏱️  SYSTEM UPTIME")
    print("-" * 40)
    uptime_metrics = collector.get_system_uptime_metrics()
    print(f"Uptime:              {uptime_metrics['uptime_hours']:.2f} hours")
    print(f"                     {uptime_metrics['uptime_days']:.2f} days")
    print(f"Started:             {uptime_metrics['start_time']}")
    
    # Health Snapshot
    print("\n🏥 SYSTEM HEALTH SNAPSHOT")
    print("-" * 40)
    snapshot = collector.get_comprehensive_health_snapshot()
    health_emoji = {"HEALTHY": "✅", "DEGRADED": "⚠️", "CRITICAL": "❌"}.get(snapshot.overall_health, "❓")
    print(f"Overall Health:      {health_emoji} {snapshot.overall_health}")
    print(f"Classification Acc:  {snapshot.classification_accuracy:.1f}%")
    print(f"Active Connections:  {len(snapshot.connection_health)}")
    print(f"Security Incidents:  {snapshot.security_incidents_count}")
    print(f"System Uptime:       {snapshot.uptime_percentage:.1f}%")


def export_metrics_to_file(collector: MetricsCollector, filename: str = "metrics_export.json"):
    """Export metrics to JSON file"""
    print(f"\n💾 Exporting metrics to {filename}...")
    
    json_data = collector.export_metrics_to_json(include_raw_data=True)
    
    with open(filename, 'w') as f:
        f.write(json_data)
    
    print(f"✅ Metrics exported to {filename}")
    
    # Show file size
    import os
    file_size = os.path.getsize(filename)
    print(f"   File size: {file_size:,} bytes")


def demonstrate_real_time_monitoring(collector: MetricsCollector):
    """Demonstrate real-time metrics monitoring"""
    print("\n⏱️  REAL-TIME MONITORING DEMO")
    print("=" * 50)
    
    def background_processing():
        """Simulate continuous background processing"""
        for i in range(20):
            email_uid = f"realtime_email_{i}"
            collector.start_processing_timer(email_uid)
            time.sleep(random.uniform(0.1, 0.5))
            collector.end_processing_timer(
                email_uid, 
                random.choice(["NEW_EO", "PMO_RESPONSE"]), 
                random.uniform(0.8, 0.99)
            )
            time.sleep(1)
    
    # Start background processing
    bg_thread = threading.Thread(target=background_processing, daemon=True)
    bg_thread.start()
    
    # Monitor metrics in real-time
    for i in range(10):
        print(f"\n📊 Real-time Update #{i+1}")
        print("-" * 30)
        
        # Get current metrics
        latency = collector.get_processing_latency_metrics(hours=0.1)  # Last 6 minutes
        throughput = collector.get_throughput_metrics(hours=0.1)
        
        print(f"Recent Emails:       {latency['total_processed']}")
        print(f"Avg Latency:         {latency['average_latency_ms']:.1f} ms")
        print(f"Current Rate:        {throughput['emails_per_hour']:.1f} emails/hour")
        
        time.sleep(3)
    
    bg_thread.join(timeout=1)
    print("\n✅ Real-time monitoring demo completed")


def main():
    """Main demo function"""
    print("🚀 Starting Comprehensive Metrics Collection System Demo")
    print("=" * 80)
    
    # Initialize metrics collector
    collector = MetricsCollector(retention_hours=24)
    print("✅ MetricsCollector initialized")
    
    try:
        # Run simulations concurrently
        print("\n🔄 Starting concurrent simulations...")
        
        # Start connection monitoring in background
        monitor_thread = threading.Thread(
            target=simulate_connection_monitoring, 
            args=(collector, 20), 
            daemon=True
        )
        monitor_thread.start()
        
        # Simulate email processing
        simulate_email_processing(collector, num_emails=30)
        
        # Simulate security incidents
        simulate_security_incidents(collector)
        
        # Wait for connection monitoring to complete
        monitor_thread.join()
        
        # Display comprehensive dashboard
        display_metrics_dashboard(collector)
        
        # Export metrics
        export_metrics_to_file(collector)
        
        # Demonstrate real-time monitoring
        demonstrate_real_time_monitoring(collector)
        
        print("\n" + "="*80)
        print("✅ DEMO COMPLETED SUCCESSFULLY")
        print("="*80)
        
        # Final summary
        summary = collector.get_metrics_summary()
        print(f"\nFinal Summary:")
        print(f"- Processed {summary['processing']['total_processed']} emails")
        print(f"- Average latency: {summary['processing']['average_latency_ms']:.1f} ms")
        print(f"- Classification accuracy: {summary['accuracy']['overall_accuracy']:.1f}%")
        print(f"- Active connections: {len(summary['connections'])}")
        print(f"- Security incidents: {summary['security']['total_incidents']}")
        print(f"- System uptime: {summary['uptime']['uptime_hours']:.2f} hours")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        raise
    finally:
        print("\n🔄 Cleaning up...")
        print("✅ Demo cleanup completed")


if __name__ == "__main__":
    main()