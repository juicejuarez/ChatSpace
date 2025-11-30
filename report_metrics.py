#!/usr/bin/env python3
"""
Metrics Reporting Script
Run this AFTER a chat session to generate a metrics report.
Can also be run during a session to see live stats.
"""

import json
import sys
from transport.protocol import TransportProtocol

def print_metrics_report(protocol_instance, label="Protocol"):
    """Print a formatted metrics report"""
    stats = protocol_instance.get_stats()
    
    print("\n" + "="*70)
    print(f"{label} METRICS REPORT")
    print("="*70)
    
    print("\n📊 REQUIRED METRICS:")
    print("-" * 70)
    
    # Message Latency
    print(f"\n1. Message Latency:")
    print(f"   Average: {stats.get('avg_latency_ms', 0):.2f} ms")
    print(f"   95th Percentile: {stats.get('p95_latency_ms', 0):.2f} ms")
    
    # Goodput
    print(f"\n2. Goodput:")
    print(f"   Messages per second: {stats.get('goodput_msgs_per_sec', 0):.2f} msg/s")
    
    # Retransmissions per KB
    print(f"\n3. Retransmissions:")
    print(f"   Retransmissions per KB: {stats.get('retransmissions_per_kb', 0):.4f}")
    print(f"   Total retransmissions: {stats['packets_retransmitted']}")
    
    # Out-of-order packets
    print(f"\n4. Out-of-Order Packets:")
    print(f"   Count: {stats['out_of_order_packets']}")
    print(f"   Percentage: {stats.get('out_of_order_percentage', 0):.2f}%")
    
    print("\n📈 PROTOCOL STATISTICS:")
    print("-" * 70)
    print(f"Packets sent: {stats['packets_sent']}")
    print(f"Packets received: {stats['packets_received']}")
    print(f"Bytes sent: {stats['bytes_sent']}")
    print(f"Bytes received: {stats['bytes_received']}")
    print(f"Checksum errors: {stats['checksum_errors']}")
    print(f"Messages sent: {stats['messages_sent']}")
    print(f"Messages received: {stats['messages_received']}")
    
    print("\n" + "="*70)
    
    return stats

if __name__ == "__main__":
    print("""
    This script is for reference only.
    
    To collect metrics from your chat application:
    
    1. DURING a session: Add this to chat_server.py:
       - Import: from report_metrics import print_metrics_report
       - Add command: /stats to print current metrics
       - Or add periodic reporting
    
    2. AFTER a session: The protocol instance stores stats
       - Access via: protocol.get_stats()
       - Print using: print_metrics_report(protocol)
    
    3. For testing: Run collect_metrics.py for controlled tests
    """)

