# transport/protocol.py
# Enhanced version integrating your full Transport_protocol.py with Phase 2 requirements
# Supports both server mode (multiple connections) and client mode

import socket
import struct
import time
import threading
import hashlib
import random
from collections import deque
from typing import Callable, Optional, Dict, Tuple
import logging
from .connection import Connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransportProtocol:
    """
    Reliable transport protocol with server and client modes
    Integrates your Phase 1 protocol features with Phase 2 requirements
    """
    
    # Protocol constants (from your original)
    VERSION = 1
    HEADER_SIZE = 20
    MAX_PAYLOAD_SIZE = 1024
    MAX_WINDOW_SIZE = 10
    INITIAL_RTO = 1.0
    MAX_RTO = 30.0
    MIN_RTO = 0.1
    
    # Packet types
    FLAG_DATA = 0x01
    FLAG_ACK = 0x02
    FLAG_SYN = 0x04
    FLAG_FIN = 0x08
    FLAG_RST = 0x10
    
    def __init__(self, local_port: int = 0):
        """Initialize the transport protocol"""
        self.local_port = local_port
        self.socket = None
        self.running = False
        
        # Server or client mode
        self.is_server = False
        self.connections: Dict[Tuple[str, int], Connection] = {}
        
        # Server mode callbacks
        self.on_new_connection_callback: Optional[Callable[[Connection], None]] = None
        
        # Client mode - single connection
        self.client_connection: Optional[Connection] = None
        
        # Threading
        self.receive_thread = None
        self.timer_thread = None
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'packets_retransmitted': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'checksum_errors': 0,
            'messages_sent': 0,  # Application-level messages
            'messages_received': 0,  # Application-level messages
            'out_of_order_packets': 0,  # Packets received out of order
            'message_latencies': [],  # List of message latencies in seconds
            'start_time': time.time()  # For calculating goodput
        }
    
    # ===== HEADER AND CHECKSUM (from your original) =====
    
    def _create_header(self, flags: int, seq: int, ack: int, length: int, 
                       conn_id: int = 0, data: bytes = b'') -> bytes:
        """Create protocol header"""
        checksum = self._calculate_checksum(flags, seq, ack, length, conn_id, data)
        header = struct.pack('!BBHIIII', 
                           self.VERSION, flags, conn_id,
                           seq, ack, length, checksum)
        return header
    
    def _parse_header(self, header: bytes) -> tuple:
        """Parse protocol header"""
        if len(header) < self.HEADER_SIZE:
            raise ValueError("Header too short")
        return struct.unpack('!BBHIIII', header)
    
    def _calculate_checksum(self, flags: int, seq: int, ack: int, 
                           length: int, conn_id: int, data: bytes) -> int:
        """Calculate checksum for error detection"""
        temp_header = struct.pack('!BBHIII', 
                                self.VERSION, flags, conn_id,
                                seq, ack, length)
        checksum_data = temp_header + data
        checksum_bytes = hashlib.md5(checksum_data).digest()[:4]
        return struct.unpack('!I', checksum_bytes)[0]
    
    def _verify_checksum(self, header: bytes, data: bytes) -> bool:
        """Verify packet checksum"""
        try:
            version, flags, conn_id, seq, ack, length, received_checksum = self._parse_header(header)
            calculated_checksum = self._calculate_checksum(flags, seq, ack, length, conn_id, data)
            return received_checksum == calculated_checksum
        except:
            return False
    
    # ===== RTT ESTIMATION (from your original) =====
    
    def _update_rtt(self, conn: Connection, rtt_sample: float):
        """Update RTT estimate using TCP-like algorithm"""
        if conn.rtt_estimate == self.INITIAL_RTO:
            conn.rtt_estimate = rtt_sample
            conn.rtt_variance = rtt_sample / 2
        else:
            error = rtt_sample - conn.rtt_estimate
            conn.rtt_estimate += 0.125 * error
            conn.rtt_variance += 0.25 * (abs(error) - conn.rtt_variance)
        
        conn.rto = conn.rtt_estimate + 4 * conn.rtt_variance
        conn.rto = max(self.MIN_RTO, min(self.MAX_RTO, conn.rto))
    
    # ===== SERVER MODE =====
    
    def start(self):
        """Start in server mode (listening for connections)"""
        if self.running:
            return
        
        self.is_server = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.local_port))
        self.socket.settimeout(1.0)
        
        self.running = True
        
        # Start threads
        self.receive_thread = threading.Thread(target=self._receive_loop_server, daemon=True)
        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.receive_thread.start()
        self.timer_thread.start()
        
        logger.info(f"Protocol started in SERVER mode on port {self.local_port}")
    
    def on_new_connection(self, callback: Callable[[Connection], None]):
        """Register callback for new connections (server mode)"""
        self.on_new_connection_callback = callback
    
    # ===== CLIENT MODE =====
    
    def connect(self, addr: Tuple[str, int], timeout: float = 5.0) -> Connection:
        """Connect to server (client mode)"""
        if self.running:
            raise RuntimeError("Already running in server mode")
        
        self.is_server = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Bind to local_port (0 = OS assigns any available port)
        self.socket.bind(('', self.local_port))
        
        self.socket.settimeout(1.0)
        self.socket.connect(addr)
        
        # Create client connection
        self.client_connection = Connection(addr, self)
        
        self.running = True
        
        # Start threads
        self.receive_thread = threading.Thread(target=self._receive_loop_client, daemon=True)
        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.receive_thread.start()
        self.timer_thread.start()
        
        # Send SYN to establish connection
        self._send_packet_to(self.client_connection, self.FLAG_SYN, 0, 0, b'')
        
        # Wait for handshake to complete (SYN -> SYN-ACK -> ACK)
        # Give it a reasonable timeout
        timeout = 5.0
        start_time = time.time()
        while not self.client_connection.handshake_complete:
            if time.time() - start_time > timeout:
                logger.warning("Handshake timeout, but continuing...")
                break
            time.sleep(0.1)
        
        logger.info(f"Protocol connected to {addr} in CLIENT mode")
        return self.client_connection
    
    # ===== SENDING =====
    
    def send_msg(self, conn: Connection, data: bytes):
        """Send message reliably to a connection"""
        if not self.running or not conn.connected:
            raise RuntimeError("Connection not active")
        
        # Wait for handshake to complete (with timeout)
        timeout = 5.0
        start_time = time.time()
        while not conn.handshake_complete:
            if time.time() - start_time > timeout:
                raise RuntimeError("Connection handshake timeout")
            time.sleep(0.1)
        
        # Track message send time for latency calculation
        message_send_time = time.time()
        self.stats['messages_sent'] += 1
        
        # Embed timestamp in message for latency tracking (if JSON)
        # This is safe - chat app only reads specific fields and ignores '_transport_timestamp'
        try:
            import json
            msg_dict = json.loads(data.decode('utf-8'))
            # Only add timestamp if it doesn't already exist (preserve existing timestamps)
            if '_transport_timestamp' not in msg_dict:
                msg_dict['_transport_timestamp'] = message_send_time  # Use underscore prefix to avoid conflicts
                data = json.dumps(msg_dict).encode('utf-8')
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            # Not JSON or can't decode - pass through unchanged (safe for chat app)
            pass
        
        # Split into chunks if needed
        chunks = [data[i:i+self.MAX_PAYLOAD_SIZE] 
                 for i in range(0, len(data), self.MAX_PAYLOAD_SIZE)]
        
        for chunk in chunks:
            # Wait for window space
            while len(conn.send_window) >= self.MAX_WINDOW_SIZE:
                time.sleep(0.01)
            
            seq = conn.next_seq
            conn.next_seq += 1
            
            with self.lock:
                conn.send_window.append((seq, self.FLAG_DATA, 0, chunk, time.time()))
            
            self._send_packet_to(conn, self.FLAG_DATA, seq, 0, chunk)
        
        # When message is fully acknowledged, calculate latency
        # This will be done in _handle_ack when all chunks are acked
    
    def _send_packet_to(self, conn: Connection, flags: int, seq: int, 
                        ack: int, data: bytes = b''):
        """Send a packet to a specific connection"""
        if not self.socket:
            return
        
        header = self._create_header(flags, seq, ack, len(data), 0, data)
        packet = header + data
        
        try:
            if self.is_server:
                self.socket.sendto(packet, conn.peer_address)
            else:
                self.socket.send(packet)
            
            self.stats['packets_sent'] += 1
            self.stats['bytes_sent'] += len(packet)
            
            # Track time for RTT
            if flags & self.FLAG_DATA:
                conn.packet_times[seq] = time.time()
            
        except Exception as e:
            logger.error(f"Send error: {e}")
    
    # ===== RECEIVING - SERVER MODE =====
    
    def _receive_loop_server(self):
        """Receive loop for server mode (multiple connections)"""
        while self.running:
            try:
                packet, addr = self.socket.recvfrom(4096)
                
                if len(packet) < self.HEADER_SIZE:
                    continue
                
                header = packet[:self.HEADER_SIZE]
                data = packet[self.HEADER_SIZE:]
                
                # Verify checksum
                if not self._verify_checksum(header, data):
                    self.stats['checksum_errors'] += 1
                    continue
                
                version, flags, conn_id, seq, ack, length, checksum = self._parse_header(header)
                
                self.stats['packets_received'] += 1
                self.stats['bytes_received'] += len(packet)
                
                # Get or create connection
                with self.lock:
                    if addr not in self.connections:
                        # New connection
                        conn = Connection(addr, self)
                        self.connections[addr] = conn
                        
                        if self.on_new_connection_callback:
                            self.on_new_connection_callback(conn)
                    else:
                        conn = self.connections[addr]
                
                conn.last_activity = time.time()
                
                # Handle packet
                if flags & self.FLAG_SYN:
                    self._handle_syn(conn, flags, seq, ack)
                elif flags & self.FLAG_ACK:
                    self._handle_ack(conn, seq, ack)
                elif flags & self.FLAG_DATA:
                    self._handle_data(conn, seq, ack, data)
                elif flags & self.FLAG_FIN:
                    self._handle_fin(conn, seq, ack)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Receive error (server): {e}")
    
    # ===== RECEIVING - CLIENT MODE =====
    
    def _receive_loop_client(self):
        """Receive loop for client mode (single connection)"""
        while self.running:
            try:
                packet = self.socket.recv(4096)
                
                # Empty packet means connection closed
                if not packet:
                    break
                
                if len(packet) < self.HEADER_SIZE:
                    continue
                
                header = packet[:self.HEADER_SIZE]
                data = packet[self.HEADER_SIZE:]
                
                if not self._verify_checksum(header, data):
                    self.stats['checksum_errors'] += 1
                    continue
                
                version, flags, conn_id, seq, ack, length, checksum = self._parse_header(header)
                
                self.stats['packets_received'] += 1
                self.stats['bytes_received'] += len(packet)
                
                conn = self.client_connection
                if not conn:
                    continue
                
                conn.last_activity = time.time()
                
                # Handle packet
                if flags & self.FLAG_SYN:
                    self._handle_syn(conn, flags, seq, ack)
                elif flags & self.FLAG_ACK:
                    self._handle_ack(conn, seq, ack)
                elif flags & self.FLAG_DATA:
                    self._handle_data(conn, seq, ack, data)
                elif flags & self.FLAG_FIN:
                    self._handle_fin(conn, seq, ack)
                
            except socket.timeout:
                continue
            except (ConnectionResetError, OSError) as e:
                # Connection was closed by remote host - this is normal when server shuts down
                # Don't log errors if we're shutting down or if server already closed
                break  # Exit the receive loop gracefully
            except Exception as e:
                if self.running:
                    # Only log unexpected errors
                    logger.error(f"Receive error (client): {e}")
                break
    
    # ===== PACKET HANDLERS =====
    
    def _handle_syn(self, conn: Connection, flags: int, seq: int, ack: int):
        """Handle SYN packet or SYN-ACK packet"""
        # Check if this is a SYN-ACK (both SYN and ACK flags set)
        if flags & self.FLAG_ACK:
            # This is a SYN-ACK - client completing handshake
            conn.expected_seq = seq + 1
            # Send ACK to complete three-way handshake
            # Note: ACK uses current next_seq but doesn't increment it
            # After handshake, first DATA packet will use next_seq (which is 0)
            # But server expects seq=1, so we need to align: set expected_seq to 0 for first DATA
            # Actually, let's increment next_seq after sending ACK so first DATA uses seq=1
            ack_seq = conn.next_seq
            self._send_packet_to(conn, self.FLAG_ACK, 
                               ack_seq, conn.expected_seq, b'')
            # Increment next_seq so first DATA packet uses seq=1 (matching server's expected_seq)
            conn.next_seq += 1
            # Mark handshake as complete
            conn.handshake_complete = True
            logger.info(f"Client handshake complete for {conn.conn_id}")
        else:
            # This is a SYN - server responding to client
            conn.expected_seq = seq + 1
            # Send SYN-ACK
            syn_ack_seq = conn.next_seq
            self._send_packet_to(conn, self.FLAG_SYN | self.FLAG_ACK, 
                               syn_ack_seq, conn.expected_seq, b'')
            # Increment next_seq after sending SYN-ACK
            conn.next_seq += 1
            # Server side: handshake will complete when we receive ACK
            logger.info(f"Server sent SYN-ACK for {conn.conn_id}")
    
    def _handle_ack(self, conn: Connection, seq: int, ack: int):
        """Handle ACK packet"""
        # If this is the final ACK of the handshake (acknowledging our SYN-ACK)
        if not conn.handshake_complete and ack > 0:
            conn.handshake_complete = True
            # After handshake, server expects first DATA packet with seq matching expected_seq
            # expected_seq is already set to 1 from SYN handling
            # Client will send first DATA with seq=1 (after we incremented next_seq in _handle_syn)
            logger.info(f"Server handshake complete for {conn.conn_id}, expecting seq={conn.expected_seq}")
        
        # Update RTT if we have timing info
        if ack in conn.packet_times:
            rtt = time.time() - conn.packet_times[ack]
            self._update_rtt(conn, rtt)
            del conn.packet_times[ack]
        
        # Remove acknowledged packets
        with self.lock:
            while conn.send_window and conn.send_window[0][0] < ack:
                conn.send_window.popleft()
    
    def _handle_data(self, conn: Connection, seq: int, ack: int, data: bytes):
        """Handle data packet with in-order delivery"""
        receive_time = time.time()
        
        # Check if in order
        if seq == conn.expected_seq:
            # In-order - deliver immediately
            if conn.on_message_callback:
                conn.on_message_callback(data)
            conn.expected_seq += 1
            self.stats['messages_received'] += 1
            
            # Try to extract timestamp from message for latency calculation
            # Only tracks latency if message has _transport_timestamp field (from our protocol)
            try:
                import json
                msg_data = json.loads(data.decode('utf-8'))
                if '_transport_timestamp' in msg_data:
                    send_time = msg_data['_transport_timestamp']
                    latency = receive_time - send_time
                    self.stats['message_latencies'].append(latency)
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError):
                # Not a JSON message, no timestamp, or can't parse - safe to ignore
                pass
            
            # Check for buffered packets
            while conn.expected_seq in conn.receive_buffer:
                buffered_data = conn.receive_buffer.pop(conn.expected_seq)
                if conn.on_message_callback:
                    conn.on_message_callback(buffered_data)
                conn.expected_seq += 1
                self.stats['messages_received'] += 1
        else:
            # Out of order - buffer it
            conn.receive_buffer[seq] = data
            self.stats['out_of_order_packets'] += 1
        
        # Send ACK
        self._send_packet_to(conn, self.FLAG_ACK, conn.next_seq, conn.expected_seq, b'')
    
    def _handle_fin(self, conn: Connection, seq: int, ack: int):
        """Handle FIN packet"""
        conn.connected = False
        self._send_packet_to(conn, self.FLAG_FIN | self.FLAG_ACK, 
                           conn.next_seq, ack + 1, b'')
        
        if conn.on_disconnect_callback:
            conn.on_disconnect_callback()
    
    # ===== RETRANSMISSION TIMER =====
    
    def _timer_loop(self):
        """Timer loop for retransmissions"""
        while self.running:
            try:
                time.sleep(0.1)
                current_time = time.time()
                
                # Check all connections
                connections_to_check = []
                with self.lock:
                    if self.is_server:
                        connections_to_check = list(self.connections.values())
                    elif self.client_connection:
                        connections_to_check = [self.client_connection]
                
                for conn in connections_to_check:
                    if not conn.connected:
                        continue
                    
                    with self.lock:
                        packets_to_retransmit = []
                        for i, (seq, flags, ack, data, send_time) in enumerate(conn.send_window):
                            if current_time - send_time > conn.rto:
                                packets_to_retransmit.append(i)
                        
                        # Retransmit
                        for i in reversed(packets_to_retransmit):
                            seq, flags, ack, data, send_time = conn.send_window[i]
                            self._send_packet_to(conn, flags, seq, ack, data)
                            conn.send_window[i] = (seq, flags, ack, data, current_time)
                            self.stats['packets_retransmitted'] += 1
                
            except Exception as e:
                if self.running:
                    logger.error(f"Timer error: {e}")
    
    # ===== CALLBACKS =====
    
    def on_message(self, conn: Connection, callback: Callable[[bytes], None]):
        """Register callback for received messages"""
        conn.on_message_callback = callback
    
    def on_disconnect(self, conn: Connection, callback: Callable):
        """Register callback for disconnection"""
        conn.on_disconnect_callback = callback
    
    # ===== CLEANUP =====
    
    def stop(self):
        """Stop the protocol"""
        if not self.running:
            return
        
        self.running = False
        
        # Send FIN to all connections (ignore errors if server is already closed)
        try:
            with self.lock:
                if self.is_server:
                    for conn in self.connections.values():
                        if conn.connected:
                            try:
                                self._send_packet_to(conn, self.FLAG_FIN, conn.next_seq, 0, b'')
                            except:
                                pass  # Server might be closed, ignore
                elif self.client_connection and self.client_connection.connected:
                    try:
                        self._send_packet_to(self.client_connection, self.FLAG_FIN, 
                                           self.client_connection.next_seq, 0, b'')
                    except:
                        pass  # Server might be closed, ignore
        except:
            pass  # Ignore any errors during shutdown
        
        # Wait for threads
        if self.receive_thread:
            self.receive_thread.join(timeout=2.0)
        if self.timer_thread:
            self.timer_thread.join(timeout=2.0)
        
        # Close socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        logger.info("Protocol stopped")
    
    def get_stats(self) -> Dict:
        """Get protocol statistics"""
        stats = self.stats.copy()
        
        # Calculate additional metrics
        elapsed_time = time.time() - stats.get('start_time', time.time())
        if elapsed_time > 0:
            stats['goodput_msgs_per_sec'] = stats['messages_received'] / elapsed_time
        else:
            stats['goodput_msgs_per_sec'] = 0.0
        
        # Calculate retransmissions per KB
        if stats['bytes_sent'] > 0:
            stats['retransmissions_per_kb'] = (stats['packets_retransmitted'] * 1024) / stats['bytes_sent']
        else:
            stats['retransmissions_per_kb'] = 0.0
        
        # Calculate latency statistics
        latencies = stats.get('message_latencies', [])
        if latencies:
            latencies_ms = [l * 1000 for l in latencies]  # Convert to milliseconds
            stats['avg_latency_ms'] = sum(latencies_ms) / len(latencies_ms)
            sorted_latencies = sorted(latencies_ms)
            percentile_95_idx = int(len(sorted_latencies) * 0.95)
            stats['p95_latency_ms'] = sorted_latencies[percentile_95_idx] if percentile_95_idx < len(sorted_latencies) else sorted_latencies[-1]
        else:
            stats['avg_latency_ms'] = 0.0
            stats['p95_latency_ms'] = 0.0
        
        # Calculate out-of-order percentage
        total_packets = stats['packets_received']
        if total_packets > 0:
            stats['out_of_order_percentage'] = (stats['out_of_order_packets'] / total_packets) * 100
        else:
            stats['out_of_order_percentage'] = 0.0
        
        return stats