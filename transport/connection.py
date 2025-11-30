# transport/connection.py
# Enhanced Connection class with full protocol features

import threading
import time
from collections import deque
from typing import Callable, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol import TransportProtocol

class Connection:
    """
    Represents a single connection with full protocol features
    Includes sequence numbers, windows, RTT tracking, etc.
    """
    
    _id_counter = 0
    _lock = threading.Lock()
    
    def __init__(self, peer_address: Tuple[str, int], protocol_instance: 'TransportProtocol'):
        """
        Initialize a connection
        
        Args:
            peer_address: (host, port) tuple of peer
            protocol_instance: Reference to the TransportProtocol instance
        """
        with Connection._lock:
            self.conn_id = f"conn_{Connection._id_counter}"
            Connection._id_counter += 1
        
        self.peer_address = peer_address
        self.protocol = protocol_instance
        
        # Sequence number management
        self.next_seq = 0
        self.expected_seq = 0
        
        # Window management (Go-Back-N)
        self.send_window = deque()  # Unacknowledged packets
        self.receive_buffer = {}    # Out-of-order packets
        
        # RTT estimation (TCP-like)
        self.rtt_estimate = 1.0  # seconds
        self.rtt_variance = 0.0
        self.rto = 1.0  # Retransmission timeout
        self.packet_times = {}  # seq -> send_time for RTT calculation
        
        # Callbacks
        self.on_message_callback: Optional[Callable[[bytes], None]] = None
        self.on_disconnect_callback: Optional[Callable] = None
        
        # Connection state
        self.connected = True
        self.handshake_complete = False  # Track if three-way handshake is complete
        self.last_activity = time.time()
    
    def __repr__(self):
        return f"Connection(id={self.conn_id}, addr={self.peer_address}, connected={self.connected})"
    
    def __str__(self):
        return f"Connection {self.conn_id} to {self.peer_address}"