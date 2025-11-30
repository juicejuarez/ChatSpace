# chat_server.py
# Phase 2: Group Chat Application Server
# Uses the custom TransportProtocol from Phase 1

import time
import json
from transport.protocol import TransportProtocol

SERVER_PORT = 12345

# ----- GLOBAL STATE -----
# Map conn_id -> Connection object
clients = {}
# Map conn_id -> "Username" (Person 4)
usernames = {}
# Map "room_name" -> [conn_id, conn_id, ...] (Person 1)
rooms = {"general": []}
# Map "room_name" -> [{"sender": "A", "text": "Hi"}, ...] (Person 4)
history = {"general": []}

# Protocol instance (set in main)
protocol = None

# ----- HELPER FUNCTIONS -----
def broadcast(room, json_obj, exclude_conn_id=None):
    """
    (Person 3): Helper to send a JSON message to everyone in a specific room.
    """
    payload = json.dumps(json_obj).encode('utf-8')
    
    if room not in rooms:
        return
    
    # Get list of recipients
    recipients = [conn_id for conn_id in rooms[room] 
                  if conn_id != exclude_conn_id and conn_id in clients]
    
    if recipients:
        print(f"[Server] Broadcasting to {len(recipients)} user(s) in '{room}': {[usernames.get(cid, 'Unknown') for cid in recipients]}")
    
    for conn_id in recipients:
        try:
            conn = clients[conn_id]
            protocol.send_msg(conn, payload)
        except Exception as e:
            print(f"[Error] Failed to send to {conn_id}: {e}")

# ----- MESSAGE HANDLERS -----
def handle_login(conn, data):
    """
    (Person 4): Handle LOGIN packet.
    """
    requested_name = data.get('name', '').strip()
    
    # Check if name is taken
    if requested_name in usernames.values():
        print(f"[Server] Login failed: Name '{requested_name}' is already taken")
        error_msg = {"type": "INFO", "msg": f"Name '{requested_name}' is already taken"}
        try:
            protocol.send_msg(conn, json.dumps(error_msg).encode('utf-8'))
        except:
            pass
        # Don't disconnect, let them try again or disconnect themselves
        return
    
    # Register username
    usernames[conn.conn_id] = requested_name
    print(f"[Server] User '{requested_name}' logged in ({conn.conn_id})")
    
    # Send welcome message
    welcome_msg = {"type": "INFO", "msg": f"Welcome, {requested_name}!"}
    try:
        protocol.send_msg(conn, json.dumps(welcome_msg).encode('utf-8'))
    except Exception as e:
        print(f"[Error] Failed to send welcome: {e}")

def handle_join(conn, data):
    """
    (Person 1): Handle JOIN packet.
    """
    room_name = data.get('room', 'general').strip()
    
    # Check if user is logged in
    if conn.conn_id not in usernames:
        error_msg = {"type": "INFO", "msg": "Please login first before joining a room"}
        try:
            protocol.send_msg(conn, json.dumps(error_msg).encode('utf-8'))
        except:
            pass
        print(f"[Server] JOIN rejected: User {conn.conn_id} not logged in")
        return
    
    # Ensure room exists
    if room_name not in rooms:
        rooms[room_name] = []
        history[room_name] = []
        print(f"[Server] New room created: {room_name}")
    
    # Remove user from all other rooms first
    for room in rooms.values():
        if conn.conn_id in room:
            room.remove(conn.conn_id)
    
    # Add to new room
    rooms[room_name].append(conn.conn_id)
    
    username = usernames.get(conn.conn_id, "Unknown")
    print(f"[Server] {username} joined room '{room_name}'")
    
    # Send history to joining user (Person 4)
    if history[room_name]:
        history_msg = {
            "type": "HISTORY",
            "room": room_name,
            "data": history[room_name]
        }
        try:
            protocol.send_msg(conn, json.dumps(history_msg).encode('utf-8'))
        except Exception as e:
            print(f"[Error] Failed to send history: {e}")
    
    # Notify others in room
    join_notification = {
        "type": "INFO",
        "msg": f"{username} joined {room_name}"
    }
    broadcast(room_name, join_notification, exclude_conn_id=conn.conn_id)
    
    # Confirm to user
    confirm_msg = {"type": "INFO", "msg": f"You joined {room_name}"}
    try:
        protocol.send_msg(conn, json.dumps(confirm_msg).encode('utf-8'))
    except Exception as e:
        print(f"[Error] Failed to send confirmation: {e}")

def handle_leave(conn, data):
    """
    (Person 1): Remove conn.conn_id from rooms[data['room']].
    """
    room_name = data.get('room', '').strip()
    
    if room_name in rooms and conn.conn_id in rooms[room_name]:
        rooms[room_name].remove(conn.conn_id)
        username = usernames.get(conn.conn_id, "Unknown")
        
        # Notify others
        leave_notification = {
            "type": "INFO",
            "msg": f"{username} left {room_name}"
        }
        broadcast(room_name, leave_notification)

def handle_msg(conn, data):
    """
    (Person 3): Handle MSG packet - broadcast to room.
    """
    room_name = data.get('room', '').strip()
    text = data.get('text', '').strip()
    
    if not room_name or not text:
        return
    
    # Check if user is in the room
    if room_name not in rooms or conn.conn_id not in rooms[room_name]:
        error_msg = {"type": "INFO", "msg": f"You are not in room '{room_name}'"}
        try:
            protocol.send_msg(conn, json.dumps(error_msg).encode('utf-8'))
        except:
            pass
        return
    
    username = usernames.get(conn.conn_id, "Unknown")
    
    # Print message on server for debugging/monitoring
    print(f"[Server] [{room_name}] {username}: {text}")
    
    # Create chat message
    chat_msg = {
        "type": "CHAT",
        "room": room_name,
        "sender": username,
        "text": text
    }
    
    # Broadcast to room (Person 3)
    broadcast(room_name, chat_msg)
    
    # Store in history (Person 4)
    history[room_name].append({"sender": username, "text": text})
    # Keep only last 100 messages
    if len(history[room_name]) > 100:
        history[room_name] = history[room_name][-100:]

def handle_dm(conn, data):
    """
    (Person 3): Handle DM packet - send to specific user.
    """
    target_username = data.get('target', '').strip()
    text = data.get('text', '').strip()
    
    if not target_username or not text:
        return
    
    # Find target conn_id
    target_conn_id = None
    for cid, uname in usernames.items():
        if uname == target_username:
            target_conn_id = cid
            break
    
    if target_conn_id is None or target_conn_id not in clients:
        error_msg = {"type": "INFO", "msg": f"User '{target_username}' not found"}
        try:
            protocol.send_msg(conn, json.dumps(error_msg).encode('utf-8'))
        except:
            pass
        return
    
    sender_username = usernames.get(conn.conn_id, "Unknown")
    
    # Print DM on server for debugging/monitoring
    print(f"[Server] DM: {sender_username} -> {target_username}: {text}")
    
    # Send DM
    dm_msg = {
        "type": "DM",
        "sender": sender_username,
        "text": text
    }
    
    try:
        target_conn = clients[target_conn_id]
        protocol.send_msg(target_conn, json.dumps(dm_msg).encode('utf-8'))
        
        # Confirm to sender
        confirm = {"type": "INFO", "msg": f"DM sent to {target_username}"}
        protocol.send_msg(conn, json.dumps(confirm).encode('utf-8'))
    except Exception as e:
        print(f"[Error] Failed to send DM: {e}")

# ----- MAIN DISPATCHER -----
def process_message(conn, raw_data: bytes):
    """
    Decodes raw bytes to JSON and calls the right handler.
    """
    try:
        payload = json.loads(raw_data.decode('utf-8'))
        msg_type = payload.get("type")
        print(f"[Server] Got {msg_type} from {conn.conn_id}")
        
        if msg_type == "LOGIN":
            handle_login(conn, payload)
        elif msg_type == "JOIN":
            handle_join(conn, payload)
        elif msg_type == "LEAVE":
            handle_leave(conn, payload)
        elif msg_type == "MSG":
            handle_msg(conn, payload)
        elif msg_type == "DM":
            handle_dm(conn, payload)
        else:
            print(f"[Server] Unknown message type: {msg_type} from {conn.conn_id}")
            print(f"[Server] Full payload: {payload}")
    except json.JSONDecodeError as e:
        print(f"[Server] Error decoding JSON from {conn.conn_id}: {e}")
        print(f"[Server] Raw data (first 100 bytes): {raw_data[:100]}")
    except Exception as e:
        print(f"[Server] Error processing message from {conn.conn_id}: {e}")
        import traceback
        traceback.print_exc()

# ----- CONNECTION EVENTS -----
def on_new_client(conn):
    """Called when a new client connects"""
    print(f"[App] New client connected: {conn.conn_id}")
    clients[conn.conn_id] = conn
    
    # Register message handler
    protocol.on_message(conn, lambda d: process_message(conn, d))
    protocol.on_disconnect(conn, lambda: on_client_disconnect(conn))

def on_client_disconnect(conn):
    """(Person 1): Clean up when client disconnects"""
    print(f"[App] Client {conn.conn_id} disconnected.")
    
    username = usernames.get(conn.conn_id, "Unknown")
    
    # Remove from all rooms
    for room_name, room_members in rooms.items():
        if conn.conn_id in room_members:
            room_members.remove(conn.conn_id)
            # Notify room
            leave_msg = {"type": "INFO", "msg": f"{username} disconnected"}
            broadcast(room_name, leave_msg)
    
    # Clean up
    if conn.conn_id in clients:
        del clients[conn.conn_id]
    if conn.conn_id in usernames:
        del usernames[conn.conn_id]

# ----- MAIN -----
if __name__ == "__main__":
    protocol = TransportProtocol(local_port=SERVER_PORT)
    protocol.on_new_connection(on_new_client)
    protocol.start()
    
    print(f"[Server] Chat server started on port {SERVER_PORT}")
    print("[Server] Waiting for connections...")
    print("[Server] Type '/stats' to see metrics, '/quit' to shutdown")
    
    try:
        import sys
        import select
        
        # For Windows, use a simple input loop
        import threading
        
        def stats_command():
            """Handle /stats command"""
            while True:
                try:
                    cmd = input().strip().lower()
                    if cmd == '/stats':
                        stats = protocol.get_stats()
                        print("\n" + "="*60)
                        print("SERVER METRICS")
                        print("="*60)
                        print(f"Messages sent: {stats['messages_sent']}")
                        print(f"Messages received: {stats['messages_received']}")
                        print(f"Goodput: {stats.get('goodput_msgs_per_sec', 0):.2f} msg/s")
                        print(f"Retransmissions: {stats['packets_retransmitted']} ({stats.get('retransmissions_per_kb', 0):.4f} per KB)")
                        print(f"Out-of-order: {stats['out_of_order_packets']} ({stats.get('out_of_order_percentage', 0):.2f}%)")
                        print(f"Avg latency: {stats.get('avg_latency_ms', 0):.2f} ms")
                        print(f"95th percentile latency: {stats.get('p95_latency_ms', 0):.2f} ms")
                        print("="*60 + "\n")
                    elif cmd == '/quit':
                        break
                except (EOFError, KeyboardInterrupt):
                    break
        
        # Start stats command handler in background (non-blocking)
        # For simplicity, we'll just print stats on shutdown
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Server] Shutting down...")
        
        # Print final metrics report
        stats = protocol.get_stats()
        print("\n" + "="*60)
        print("FINAL SERVER METRICS REPORT")
        print("="*60)
        print(f"Messages sent: {stats['messages_sent']}")
        print(f"Messages received: {stats['messages_received']}")
        print(f"Goodput: {stats.get('goodput_msgs_per_sec', 0):.2f} msg/s")
        print(f"Retransmissions: {stats['packets_retransmitted']} ({stats.get('retransmissions_per_kb', 0):.4f} per KB)")
        print(f"Out-of-order packets: {stats['out_of_order_packets']} ({stats.get('out_of_order_percentage', 0):.2f}%)")
        print(f"Average latency: {stats.get('avg_latency_ms', 0):.2f} ms")
        print(f"95th percentile latency: {stats.get('p95_latency_ms', 0):.2f} ms")
        print("="*60)
        
        protocol.stop()