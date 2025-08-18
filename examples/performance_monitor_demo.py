"""
Performance Bottleneck Detection Demo

Demonstrates the real-time performance monitoring and bottleneck detection
capabilities of the Email Agent system.

Requirements: 7.4, 6.1, 6.3
"""

import time
import queue
import threading
import random
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.email.performance_monitor import (
    PerformanceMonitor, BottleneckType, SeverityLevel, ResourceType
)


def simulate_email_processing_load(monitor, duration_seconds=30):
    """Simulate email processing load with varying performance characteristics"""
    print(f"🔄 Simulating email processing load for {duration_seconds} seconds...")
    
    start_time = time.time()
    email_count = 0
    
    while time.time() - start_time < duration_seconds:
        email_id = f"email_{email_count}"
        
        # Start processing timer
        monitor.start_operation_timer(email_id, "email_classifier", "classify")
        
        # Simulate variable processing time (some emails are slower)
        if random.random() < 0.1:  # 10% of emails are slow
            processing_time = random.uniform(2.0, 5.0)  # 2-5 seconds (slow)
        else:
            processing_time = random.uniform(0.1, 0.5)  # 100-500ms (normal)
        
        time.sleep(processing_time)
        
        # End processing timer
        duration_ms = monitor.end_operation_timer(email_id, "email_classifier", "classify")
        
        email_count += 1
        
        if email_count % 10 == 0:
            print(f"  📧 Processed {email_count} emails, last duration: {duration_ms:.1f}ms")
        
        # Small delay between emails
        time.sleep(random.uniform(0.1, 0.3))
    
    print(f"✅ Completed processing {email_count} emails")
    return email_count


def simulate_queue_congestion(monitor, queue_obj, queue_name):
    """Simulate queue congestion scenarios"""
    print(f"📊 Simulating queue congestion for {queue_name}...")
    
    # Phase 1: Normal load
    print("  Phase 1: Normal load (10-20 items)")
    for i in range(15):
        queue_obj.put(f"task_{i}")
        time.sleep(0.1)
    
    time.sleep(2)
    
    # Phase 2: Increasing load
    print("  Phase 2: Increasing load (50+ items)")
    for i in range(50):
        queue_obj.put(f"task_{i + 15}")
        time.sleep(0.05)
    
    time.sleep(2)
    
    # Phase 3: Critical congestion
    print("  Phase 3: Critical congestion (200+ items)")
    for i in range(150):
        queue_obj.put(f"task_{i + 65}")
        time.sleep(0.01)
    
    print(f"  📈 Queue {queue_name} now has {queue_obj.qsize()} items")


def simulate_system_resource_pressure():
    """Simulate system resource pressure"""
    print("💻 Simulating system resource pressure...")
    
    # CPU intensive task
    def cpu_intensive_task():
        start = time.time()
        while time.time() - start < 5:
            # Busy work to increase CPU usage
            sum(i * i for i in range(1000))
    
    # Memory intensive task
    def memory_intensive_task():
        large_data = []
        for i in range(100):
            large_data.append([random.random() for _ in range(10000)])
            time.sleep(0.1)
        return large_data
    
    # Run tasks concurrently
    with ThreadPoolExecutor(max_workers=4) as executor:
        cpu_futures = [executor.submit(cpu_intensive_task) for _ in range(2)]
        memory_future = executor.submit(memory_intensive_task)
        
        # Wait for completion
        for future in cpu_futures:
            future.result()
        memory_future.result()
    
    print("✅ Resource pressure simulation completed")


def bottleneck_alert_handler(detection):
    """Handle bottleneck detection alerts"""
    severity_emoji = {
        SeverityLevel.LOW: "🟡",
        SeverityLevel.MEDIUM: "🟠", 
        SeverityLevel.HIGH: "🔴",
        SeverityLevel.CRITICAL: "🚨"
    }
    
    emoji = severity_emoji.get(detection.severity, "⚠️")
    
    print(f"\n{emoji} BOTTLENECK DETECTED!")
    print(f"  ID: {detection.detection_id}")
    print(f"  Type: {detection.bottleneck_type.value}")
    print(f"  Severity: {detection.severity.value}")
    print(f"  Component: {detection.component}")
    print(f"  Description: {detection.description}")
    print(f"  Current Value: {detection.current_value:.2f}")
    print(f"  Threshold: {detection.threshold_value:.2f}")
    print(f"  Impact: {detection.impact_assessment}")
    print("  Recommendations:")
    for i, rec in enumerate(detection.optimization_recommendations[:3], 1):
        print(f"    {i}. {rec}")
    print()


def demonstrate_performance_monitoring():
    """Main demonstration of performance monitoring capabilities"""
    print("🚀 Email Agent Performance Monitoring Demo")
    print("=" * 50)
    
    # Initialize performance monitor
    monitor = PerformanceMonitor(check_interval=2)  # Check every 2 seconds
    
    # Register alert handler
    monitor.register_alert_callback(bottleneck_alert_handler)
    
    # Configure thresholds for demonstration
    print("⚙️  Configuring performance thresholds...")
    monitor.set_resource_threshold(ResourceType.CPU, 60.0, 80.0)
    monitor.set_resource_threshold(ResourceType.MEMORY, 70.0, 85.0)
    monitor.set_resource_threshold(ResourceType.QUEUE_DEPTH, 30, 100)
    monitor.set_resource_threshold(ResourceType.PROCESSING_TIME, 1000.0, 3000.0)  # 1s warning, 3s critical
    
    # Create test queues
    email_queue = queue.Queue()
    processing_queue = queue.Queue()
    
    monitor.register_queue("email_intake", email_queue)
    monitor.register_queue("email_processing", processing_queue)
    
    print("✅ Performance monitor configured")
    
    # Start monitoring
    print("\n📊 Starting performance monitoring...")
    monitor.start_monitoring()
    
    try:
        # Demonstrate different scenarios
        print("\n" + "=" * 50)
        print("SCENARIO 1: Normal Email Processing")
        print("=" * 50)
        
        # Normal processing load
        with ThreadPoolExecutor(max_workers=2) as executor:
            processing_future = executor.submit(simulate_email_processing_load, monitor, 15)
            
            # Let it run and show status
            time.sleep(5)
            status = monitor.get_current_performance_status()
            print(f"📈 Current Status: {status['overall_health']}")
            print(f"   Active Bottlenecks: {status['active_bottlenecks']}")
            
            processing_future.result()
        
        print("\n" + "=" * 50)
        print("SCENARIO 2: Queue Congestion")
        print("=" * 50)
        
        # Simulate queue congestion
        congestion_thread = threading.Thread(
            target=simulate_queue_congestion, 
            args=(monitor, email_queue, "email_intake")
        )
        congestion_thread.start()
        congestion_thread.join()
        
        # Wait for detection
        time.sleep(3)
        
        print("\n" + "=" * 50)
        print("SCENARIO 3: Processing Time Bottlenecks")
        print("=" * 50)
        
        # Simulate slow processing
        print("🐌 Simulating slow email classification...")
        for i in range(5):
            email_id = f"slow_email_{i}"
            monitor.start_operation_timer(email_id, "email_classifier", "classify")
            time.sleep(random.uniform(2.0, 4.0))  # 2-4 seconds (very slow)
            duration = monitor.end_operation_timer(email_id, "email_classifier", "classify")
            print(f"  📧 Slow email {i+1} processed in {duration:.1f}ms")
        
        # Wait for analysis
        time.sleep(3)
        
        print("\n" + "=" * 50)
        print("SCENARIO 4: System Resource Pressure")
        print("=" * 50)
        
        # Note: This would normally trigger system resource bottlenecks,
        # but we're using mocked system metrics in the demo
        simulate_system_resource_pressure()
        
        # Wait for final analysis
        time.sleep(5)
        
        print("\n" + "=" * 50)
        print("PERFORMANCE ANALYSIS RESULTS")
        print("=" * 50)
        
        # Get comprehensive status
        final_status = monitor.get_current_performance_status()
        print(f"🏥 Overall Health: {final_status['overall_health']}")
        print(f"📊 Total Active Bottlenecks: {final_status['active_bottlenecks']}")
        
        if final_status['bottleneck_summary']:
            print("\n🔍 Detected Bottlenecks:")
            for bottleneck in final_status['bottleneck_summary']:
                print(f"  • {bottleneck['type']} ({bottleneck['severity']}) in {bottleneck['component']}")
        
        # Show queue status
        if final_status['queue_status']:
            print("\n📋 Queue Status:")
            for queue_name, status in final_status['queue_status'].items():
                print(f"  • {queue_name}: {status['depth']} items ({status['congestion']} congestion)")
        
        # Get bottleneck history
        history = monitor.get_bottleneck_history(1)  # Last hour
        print(f"\n📈 Bottlenecks in last hour: {len(history)}")
        
        # Get optimization recommendations
        recommendations = monitor.get_optimization_recommendations()
        if recommendations:
            print(f"\n💡 Optimization Recommendations: {len(recommendations)}")
            for rec in recommendations[:3]:  # Show top 3
                print(f"  • {rec.title} (Priority: {rec.priority.value})")
                print(f"    Expected improvement: {rec.expected_improvement}")
        
        # Export performance report
        print("\n📄 Generating performance report...")
        report = monitor.export_performance_report()
        
        # Save report to file
        with open("performance_report.json", "w") as f:
            f.write(report)
        print("✅ Performance report saved to 'performance_report.json'")
        
        # Show summary statistics
        report_data = json.loads(report)
        print(f"\n📊 Report Summary:")
        print(f"  • Total metrics collected: {report_data['system_metrics']['total_metrics_collected']}")
        print(f"  • Total bottlenecks detected: {report_data['system_metrics']['total_bottlenecks_detected']}")
        print(f"  • Monitored queues: {len(report_data['system_metrics']['monitored_queues'])}")
        
    finally:
        # Stop monitoring
        print("\n🛑 Stopping performance monitoring...")
        monitor.stop_monitoring()
        print("✅ Performance monitoring stopped")
    
    print("\n" + "=" * 50)
    print("DEMO COMPLETED")
    print("=" * 50)
    print("🎯 Key Features Demonstrated:")
    print("  ✅ Real-time performance monitoring")
    print("  ✅ Bottleneck detection with severity levels")
    print("  ✅ Queue depth and congestion analysis")
    print("  ✅ Processing time analysis and trends")
    print("  ✅ Automated optimization recommendations")
    print("  ✅ Alert system for critical issues")
    print("  ✅ Comprehensive performance reporting")
    print("\n💡 Check 'performance_report.json' for detailed analysis!")


if __name__ == "__main__":
    demonstrate_performance_monitoring()