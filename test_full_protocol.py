#!/usr/bin/env python3
"""
Test script for the full integrated transport protocol
Tests reliability features: retransmission, ordering, checksums, etc.
"""

import sys
import time
import threading
import json
from transport.protocol import TransportProtocol

def test_basic_connectivity():
    """Test 1: Basic client-server connectivity"""
    print("\n" + "="*60)
    print("TEST 1: Basic Connectivity")
    print("="*60)
    
    server_received = []
    client_received = []
    
    # Server setup
    def on_new_connection(conn):
        print(f"[Server] New connection: {conn.conn_id}")
        
        def on_message(data):
            msg = data.decode('utf-8')
            print(f"[Server] Received: {msg}")
            server_received.append(msg)
            
            # Echo back
            response = f"Echo: {msg}"
            protocol_server.send_msg(conn, response.encode('utf-8'))
        
        protocol_server.on_message(conn, on_message)
    
    protocol_server = TransportProtocol(local_port=15000)
    protocol_server.on_new_connection(on_new_connection)
    protocol_server.start()
    
    # Give server time to start
    time.sleep(0.5)
    
    # Client setup
    protocol_client = TransportProtocol(local_port=15001)
    
    try:
        conn = protocol_client.connect(('127.0.0.1', 15000))
        print(f"[Client] Connected: {conn.conn_id}")
        
        def on_client_message(data):
            msg = data.decode('utf-8')
            print(f"[Client] Received: {msg}")
            client_received.append(msg)
        
        protocol_client.on_message(conn, on_client_message)
        
        # Send test message
        test_msg = "Hello, Server!"
        print(f"[Client] Sending: {test_msg}")
        protocol_client.send_msg(conn, test_msg.encode('utf-8'))
        
        # Wait for response
        time.sleep(2)
        
        # Verify
        if server_received and client_received:
            print("✓ TEST PASSED: Messages exchanged successfully")
            return True
        else:
            print("✗ TEST FAILED: Messages not received")
            return False
        
    finally:
        protocol_client.stop()
        protocol_server.stop()
        time.sleep(0.5)

def test_multiple_messages():
    """Test 2: Multiple messages in sequence"""
    print("\n" + "="*60)
    print("TEST 2: Multiple Messages")
    print("="*60)
    
    messages_received = []
    
    def on_new_connection(conn):
        print(f"[Server] Connection from {conn.peer_address}")
        
        def on_message(data):
            msg = data.decode('utf-8')
            messages_received.append(msg)
            print(f"[Server] Received #{len(messages_received)}: {msg}")
        
        protocol_server.on_message(conn, on_message)
    
    protocol_server = TransportProtocol(local_port=15002)
    protocol_server.on_new_connection(on_new_connection)
    protocol_server.start()
    
    time.sleep(0.5)
    
    protocol_client = TransportProtocol(local_port=15003)
    
    try:
        conn = protocol_client.connect(('127.0.0.1', 15002))
        
        # Send multiple messages
        num_messages = 10
        for i in range(num_messages):
            msg = f"Message {i+1}"
            protocol_client.send_msg(conn, msg.encode('utf-8'))
            time.sleep(0.1)  # Small delay between messages
        
        # Wait for all messages
        time.sleep(3)
        
        # Verify all received
        if len(messages_received) == num_messages:
            print(f"✓ TEST PASSED: All {num_messages} messages received")
            return True
        else:
            print(f"✗ TEST FAILED: Expected {num_messages}, got {len(messages_received)}")
            return False
        
    finally:
        protocol_client.stop()
        protocol_server.stop()
        time.sleep(0.5)

def test_large_message():
    """Test 3: Large message (should be chunked)"""
    print("\n" + "="*60)
    print("TEST 3: Large Message")
    print("="*60)
    
    received_data = []
    
    def on_new_connection(conn):
        print(f"[Server] Connection established")
        
        def on_message(data):
            received_data.append(data)
            print(f"[Server] Received chunk: {len(data)} bytes")
        
        protocol_server.on_message(conn, on_message)
    
    protocol_server = TransportProtocol(local_port=15004)
    protocol_server.on_new_connection(on_new_connection)
    protocol_server.start()
    
    time.sleep(0.5)
    
    protocol_client = TransportProtocol(local_port=15005)
    
    try:
        conn = protocol_client.connect(('127.0.0.1', 15004))
        
        # Send large message (3KB - should be split into chunks)
        large_msg = "X" * 3000
        print(f"[Client] Sending large message: {len(large_msg)} bytes")
        protocol_client.send_msg(conn, large_msg.encode('utf-8'))
        
        # Wait for transmission
        time.sleep(4)
        
        # Reconstruct received data
        total_received = b''.join(received_data)
        
        if total_received.decode('utf-8') == large_msg:
            print(f"✓ TEST PASSED: Large message received correctly ({len(total_received)} bytes)")
            return True
        else:
            print(f"✗ TEST FAILED: Message corrupted or incomplete")
            return False
        
    finally:
        protocol_client.stop()
        protocol_server.stop()
        time.sleep(0.5)

def test_json_messages():
    """Test 4: JSON message exchange (Phase 2 use case)"""
    print("\n" + "="*60)
    print("TEST 4: JSON Messages (Phase 2)")
    print("="*60)
    
    received_messages = []
    
    def on_new_connection(conn):
        print(f"[Server] New client connected")
        
        def on_message(data):
            try:
                msg = json.loads(data.decode('utf-8'))
                received_messages.append(msg)
                print(f"[Server] Received JSON: {msg}")
                
                # Send response
                response = {
                    "type": "INFO",
                    "msg": f"Received your {msg.get('type')} message"
                }
                protocol_server.send_msg(conn, json.dumps(response).encode('utf-8'))
            except Exception as e:
                print(f"[Server] Error: {e}")
        
        protocol_server.on_message(conn, on_message)
    
    protocol_server = TransportProtocol(local_port=15006)
    protocol_server.on_new_connection(on_new_connection)
    protocol_server.start()
    
    time.sleep(0.5)
    
    protocol_client = TransportProtocol(local_port=15007)
    client_responses = []
    
    try:
        conn = protocol_client.connect(('127.0.0.1', 15006))
        
        def on_client_message(data):
            msg = json.loads(data.decode('utf-8'))
            client_responses.append(msg)
            print(f"[Client] Received response: {msg}")
        
        protocol_client.on_message(conn, on_client_message)
        
        # Send various JSON messages
        messages = [
            {"type": "LOGIN", "name": "Alice"},
            {"type": "JOIN", "room": "general"},
            {"type": "MSG", "room": "general", "text": "Hello!"}
        ]
        
        for msg in messages:
            print(f"[Client] Sending: {msg}")
            protocol_client.send_msg(conn, json.dumps(msg).encode('utf-8'))
            time.sleep(0.5)
        
        time.sleep(2)
        
        if len(received_messages) == len(messages) and len(client_responses) == len(messages):
            print(f"✓ TEST PASSED: All JSON messages exchanged correctly")
            return True
        else:
            print(f"✗ TEST FAILED: Message count mismatch")
            return False
        
    finally:
        protocol_client.stop()
        protocol_server.stop()
        time.sleep(0.5)

def test_statistics():
    """Test 5: Protocol statistics"""
    print("\n" + "="*60)
    print("TEST 5: Protocol Statistics")
    print("="*60)
    
    def on_new_connection(conn):
        protocol_server.on_message(conn, lambda d: None)
    
    protocol_server = TransportProtocol(local_port=15008)
    protocol_server.on_new_connection(on_new_connection)
    protocol_server.start()
    
    time.sleep(0.5)
    
    protocol_client = TransportProtocol(local_port=15009)
    
    try:
        conn = protocol_client.connect(('127.0.0.1', 15008))
        protocol_client.on_message(conn, lambda d: None)
        
        # Send some messages
        for i in range(5):
            protocol_client.send_msg(conn, f"Message {i}".encode('utf-8'))
            time.sleep(0.2)
        
        time.sleep(2)
        
        # Check statistics
        server_stats = protocol_server.get_stats()
        client_stats = protocol_client.get_stats()
        
        print("\nServer Statistics:")
        for key, value in server_stats.items():
            print(f"  {key}: {value}")
        
        print("\nClient Statistics:")
        for key, value in client_stats.items():
            print(f"  {key}: {value}")
        
        # Verify some packets were sent/received
        if (server_stats['packets_received'] > 0 and 
            client_stats['packets_sent'] > 0):
            print("\n✓ TEST PASSED: Statistics collected correctly")
            return True
        else:
            print("\n✗ TEST FAILED: No traffic in statistics")
            return False
        
    finally:
        protocol_client.stop()
        protocol_server.stop()
        time.sleep(0.5)

def test_network_emulation_clean():
    """Test 6: Clean network (no packet loss)"""
    print("\n" + "="*60)
    print("TEST 6: Network Emulation - CLEAN NETWORK")
    print("="*60)
    
    messages_received = []
    
    def on_new_connection(conn):
        def on_message(data):
            msg = data.decode('utf-8')
            messages_received.append(msg)
            print(f"[Server] Received: {msg}")
        
        protocol_server.on_message(conn, on_message)
    
    protocol_server = TransportProtocol(local_port=15010)
    protocol_server.set_network_profile('clean')
    protocol_server.on_new_connection(on_new_connection)
    protocol_server.start()
    
    time.sleep(0.5)
    
    protocol_client = TransportProtocol(local_port=15011)
    protocol_client.set_network_profile('clean')
    
    try:
        conn = protocol_client.connect(('127.0.0.1', 15010))
        
        # Send multiple messages
        num_messages = 10
        for i in range(num_messages):
            msg = f"Clean test message {i+1}"
            protocol_client.send_msg(conn, msg.encode('utf-8'))
            time.sleep(0.1)
        
        # Wait for all messages
        time.sleep(3)
        
        # Get statistics
        server_stats = protocol_server.get_stats()
        client_stats = protocol_client.get_stats()
        
        print(f"\n[Server] Packets attempted: {server_stats.get('packets_attempted', 0)}")
        print(f"[Server] Packets dropped: {server_stats.get('packets_dropped', 0)}")
        print(f"[Server] Drop rate: {server_stats.get('packet_drop_percentage', 0):.2f}%")
        print(f"[Client] Packets attempted: {client_stats.get('packets_attempted', 0)}")
        print(f"[Client] Packets dropped: {client_stats.get('packets_dropped', 0)}")
        print(f"[Client] Drop rate: {client_stats.get('packet_drop_percentage', 0):.2f}%")
        
        # Verify all messages received
        if len(messages_received) == num_messages:
            print(f"\n✓ TEST PASSED: All {num_messages} messages received on clean network")
            return True
        else:
            print(f"\n✗ TEST FAILED: Expected {num_messages}, got {len(messages_received)}")
            return False
        
    finally:
        protocol_client.stop()
        protocol_server.stop()
        time.sleep(0.5)

def test_network_emulation_random_loss():
    """Test 7: Random packet loss (5% loss rate)"""
    print("\n" + "="*60)
    print("TEST 7: Network Emulation - RANDOM PACKET LOSS")
    print("="*60)
    
    messages_received = []
    
    def on_new_connection(conn):
        def on_message(data):
            msg = data.decode('utf-8')
            messages_received.append(msg)
            print(f"[Server] Received: {msg}")
        
        protocol_server.on_message(conn, on_message)
    
    protocol_server = TransportProtocol(local_port=15012)
    protocol_server.set_network_profile('random_loss')
    protocol_server.on_new_connection(on_new_connection)
    protocol_server.start()
    
    time.sleep(0.5)
    
    protocol_client = TransportProtocol(local_port=15013)
    protocol_client.set_network_profile('random_loss')
    
    try:
        conn = protocol_client.connect(('127.0.0.1', 15012))
        
        # Send more messages to see retransmissions
        num_messages = 20
        for i in range(num_messages):
            msg = f"Random loss test message {i+1}"
            protocol_client.send_msg(conn, msg.encode('utf-8'))
            time.sleep(0.1)
        
        # Wait longer for retransmissions
        time.sleep(5)
        
        # Get statistics
        server_stats = protocol_server.get_stats()
        client_stats = protocol_client.get_stats()
        
        print(f"\n[Server] Packets attempted: {server_stats.get('packets_attempted', 0)}")
        print(f"[Server] Packets dropped: {server_stats.get('packets_dropped', 0)}")
        print(f"[Server] Drop rate: {server_stats.get('packet_drop_percentage', 0):.2f}%")
        print(f"[Server] Retransmissions: {server_stats.get('packets_retransmitted', 0)}")
        print(f"[Client] Packets attempted: {client_stats.get('packets_attempted', 0)}")
        print(f"[Client] Packets dropped: {client_stats.get('packets_dropped', 0)}")
        print(f"[Client] Drop rate: {client_stats.get('packet_drop_percentage', 0):.2f}%")
        print(f"[Client] Retransmissions: {client_stats.get('packets_retransmitted', 0)}")
        
        # Verify all messages received (protocol should handle retransmissions)
        if len(messages_received) == num_messages:
            print(f"\n✓ TEST PASSED: All {num_messages} messages received despite random packet loss")
            print(f"   Protocol successfully handled {server_stats.get('packets_dropped', 0) + client_stats.get('packets_dropped', 0)} dropped packets")
            return True
        else:
            print(f"\n✗ TEST FAILED: Expected {num_messages}, got {len(messages_received)}")
            return False
        
    finally:
        protocol_client.stop()
        protocol_server.stop()
        time.sleep(0.5)

def test_network_emulation_bursty_loss():
    """Test 8: Bursty packet loss (clustered loss events)"""
    print("\n" + "="*60)
    print("TEST 8: Network Emulation - BURSTY PACKET LOSS")
    print("="*60)
    
    messages_received = []
    
    def on_new_connection(conn):
        def on_message(data):
            msg = data.decode('utf-8')
            messages_received.append(msg)
            print(f"[Server] Received: {msg}")
        
        protocol_server.on_message(conn, on_message)
    
    protocol_server = TransportProtocol(local_port=15014)
    protocol_server.set_network_profile('bursty_loss')
    protocol_server.on_new_connection(on_new_connection)
    protocol_server.start()
    
    time.sleep(0.5)
    
    protocol_client = TransportProtocol(local_port=15015)
    protocol_client.set_network_profile('bursty_loss')
    
    try:
        conn = protocol_client.connect(('127.0.0.1', 15014))
        
        # Send many messages to observe bursty behavior
        num_messages = 30
        for i in range(num_messages):
            msg = f"Bursty loss test message {i+1}"
            protocol_client.send_msg(conn, msg.encode('utf-8'))
            time.sleep(0.05)  # Faster sending to see bursts
        
        # Wait longer for retransmissions during bursts
        time.sleep(6)
        
        # Get statistics
        server_stats = protocol_server.get_stats()
        client_stats = protocol_client.get_stats()
        
        print(f"\n[Server] Packets attempted: {server_stats.get('packets_attempted', 0)}")
        print(f"[Server] Packets dropped: {server_stats.get('packets_dropped', 0)}")
        print(f"[Server] Drop rate: {server_stats.get('packet_drop_percentage', 0):.2f}%")
        print(f"[Server] Retransmissions: {server_stats.get('packets_retransmitted', 0)}")
        print(f"[Client] Packets attempted: {client_stats.get('packets_attempted', 0)}")
        print(f"[Client] Packets dropped: {client_stats.get('packets_dropped', 0)}")
        print(f"[Client] Drop rate: {client_stats.get('packet_drop_percentage', 0):.2f}%")
        print(f"[Client] Retransmissions: {client_stats.get('packets_retransmitted', 0)}")
        
        # Verify all messages received (protocol should handle bursty retransmissions)
        if len(messages_received) == num_messages:
            print(f"\n✓ TEST PASSED: All {num_messages} messages received despite bursty packet loss")
            print(f"   Protocol successfully handled bursty loss with {server_stats.get('packets_dropped', 0) + client_stats.get('packets_dropped', 0)} dropped packets")
            return True
        else:
            print(f"\n✗ TEST FAILED: Expected {num_messages}, got {len(messages_received)}")
            return False
        
    finally:
        protocol_client.stop()
        protocol_server.stop()
        time.sleep(0.5)

def main():
    """Run all tests"""
    print("="*60)
    print("FULL TRANSPORT PROTOCOL TEST SUITE")
    print("="*60)
    print("\nTesting integrated protocol with:")
    print("  - Reliability (retransmission)")
    print("  - Flow control (windowing)")
    print("  - Error detection (checksums)")
    print("  - RTT estimation")
    print("  - Server and client modes")
    print("  - Network emulation (packet loss)")
    
    results = []
    
    try:
        results.append(("Basic Connectivity", test_basic_connectivity()))
        results.append(("Multiple Messages", test_multiple_messages()))
        results.append(("Large Message", test_large_message()))
        results.append(("JSON Messages", test_json_messages()))
        results.append(("Statistics", test_statistics()))
        results.append(("Network: Clean", test_network_emulation_clean()))
        results.append(("Network: Random Loss", test_network_emulation_random_loss()))
        results.append(("Network: Bursty Loss", test_network_emulation_bursty_loss()))
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return
    except Exception as e:
        print(f"\n\nTest suite error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name:25} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your protocol is working correctly.")
        print("\nNext steps:")
        print("  1. Run: python chat_server.py")
        print("  2. In another terminal: python chat_client.py")
        print("  3. Test the chat application!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review the output above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code if exit_code else 0)