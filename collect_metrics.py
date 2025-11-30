#!/usr/bin/env python3
"""
Metrics Collection and Reporting Script
Collects metrics from the transport protocol and generates a report.
"""

import time
import json
from transport.protocol import TransportProtocol

def collect_metrics(num_messages=100, message_size=100):
    """Collect metrics by sending messages and measuring performance"""
    
    server_received = []
    client_received = []
    
    def on_new_connection(conn):
        def on_message(data):
            receive_time = time.time()
            server_received.append((receive_time, data))
            # Echo back - preserve original timestamp for round-trip latency calculation
            try:
                msg_dict = json.loads(data.decode('utf-8'))
                # Keep the original _transport_timestamp if it exists
                msg_dict['echo'] = True
                echo_msg = json.dumps(msg_dict).encode('utf-8')
                protocol_server.send_msg(conn, echo_msg)
            except:
                # Not JSON, echo as-is
                protocol_server.send_msg(conn, data)
        protocol_server.on_message(conn, on_message)
    
    protocol_server = TransportProtocol(local_port=16000)
    protocol_server.on_new_connection(on_new_connection)
    protocol_server.start()
    
    time.sleep(0.5)
    
    protocol_client = TransportProtocol(local_port=16001)
    
    try:
        conn = protocol_client.connect(('127.0.0.1', 16000))
        
        def on_client_message(data):
            receive_time = time.time()
            client_received.append((receive_time, data))
            # Calculate round-trip latency if echo message
            try:
                msg_dict = json.loads(data.decode('utf-8'))
                if 'echo' in msg_dict and '_transport_timestamp' in msg_dict:
                    send_time = msg_dict['_transport_timestamp']
                    latency = receive_time - send_time
                    # Store latency in client stats (will be aggregated)
                    if not hasattr(protocol_client, '_latencies'):
                        protocol_client._latencies = []
                    protocol_client._latencies.append(latency)
            except:
                pass
        protocol_client.on_message(conn, on_client_message)
        
        # Send test messages with timestamps for latency tracking
        print(f"Sending {num_messages} messages of {message_size} bytes each...")
        start_time = time.time()
        
        for i in range(num_messages):
            # Create JSON message with timestamp for latency tracking
            msg_dict = {
                "type": "TEST",
                "id": i,
                "text": f"Message {i}: {'X' * message_size}",
                "timestamp": time.time()
            }
            msg = json.dumps(msg_dict).encode('utf-8')
            protocol_client.send_msg(conn, msg)
            time.sleep(0.01)  # Small delay between messages
        
        # Wait for all messages to be delivered
        time.sleep(5)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Get statistics
        server_stats = protocol_server.get_stats()
        client_stats = protocol_client.get_stats()
        
        # Add round-trip latencies from client if available
        if hasattr(protocol_client, '_latencies') and protocol_client._latencies:
            latencies_ms = [l * 1000 for l in protocol_client._latencies]
            client_stats['avg_latency_ms'] = sum(latencies_ms) / len(latencies_ms)
            sorted_latencies = sorted(latencies_ms)
            percentile_95_idx = int(len(sorted_latencies) * 0.95)
            client_stats['p95_latency_ms'] = sorted_latencies[percentile_95_idx] if percentile_95_idx < len(sorted_latencies) else sorted_latencies[-1]
            # Also update server stats with these latencies
            server_stats['avg_latency_ms'] = client_stats['avg_latency_ms']
            server_stats['p95_latency_ms'] = client_stats['p95_latency_ms']
            server_stats['message_latencies'] = protocol_client._latencies
        
        return {
            'server_stats': server_stats,
            'client_stats': client_stats,
            'total_time': total_time,
            'messages_sent': num_messages,
            'messages_received_server': len(server_received),
            'messages_received_client': len(client_received)
        }
        
    finally:
        protocol_client.stop()
        protocol_server.stop()
        time.sleep(0.5)

def generate_report(metrics):
    """Generate a formatted report of metrics"""
    
    print("\n" + "="*70)
    print("TRANSPORT PROTOCOL METRICS REPORT")
    print("="*70)
    
    server = metrics['server_stats']
    client = metrics['client_stats']
    
    print("\n📊 REQUIRED METRICS:")
    print("-" * 70)
    
    # Message Latency
    print(f"\n1. Message Latency:")
    print(f"   Average: {server.get('avg_latency_ms', 0):.2f} ms")
    print(f"   95th Percentile: {server.get('p95_latency_ms', 0):.2f} ms")
    
    # Goodput
    print(f"\n2. Goodput:")
    print(f"   Messages per second: {server.get('goodput_msgs_per_sec', 0):.2f} msg/s")
    
    # Retransmissions per KB
    print(f"\n3. Retransmissions:")
    print(f"   Retransmissions per KB: {server.get('retransmissions_per_kb', 0):.4f}")
    print(f"   Total retransmissions: {server['packets_retransmitted']}")
    
    # Out-of-order packets
    print(f"\n4. Out-of-Order Packets:")
    print(f"   Count: {server['out_of_order_packets']}")
    print(f"   Percentage: {server.get('out_of_order_percentage', 0):.2f}%")
    
    # Maximum concurrent clients (would need separate test)
    print(f"\n5. Maximum Concurrent Clients:")
    print(f"   (Test separately with stress test)")
    
    print("\n📈 PROTOCOL STATISTICS:")
    print("-" * 70)
    print(f"Packets sent: {server['packets_sent']}")
    print(f"Packets received: {server['packets_received']}")
    print(f"Bytes sent: {server['bytes_sent']}")
    print(f"Bytes received: {server['bytes_received']}")
    print(f"Checksum errors: {server['checksum_errors']}")
    print(f"Messages sent: {server['messages_sent']}")
    print(f"Messages received: {server['messages_received']}")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    print("Collecting metrics...")
    metrics = collect_metrics(num_messages=100, message_size=100)
    generate_report(metrics)
    
    # Save to JSON file
    with open('metrics_report.json', 'w') as f:
        json.dump(metrics, f, indent=2, default=str)
    print("\n✅ Metrics saved to metrics_report.json")

