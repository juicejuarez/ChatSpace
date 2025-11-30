# chat_client.py
# Phase 2: Group Chat Application Client
# Uses the custom TransportProtocol from Phase 1

import time
import json
import threading
from transport.protocol import TransportProtocol

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345
CLIENT_PORT = 0  # 0 = let OS assign any available port (allows multiple clients)

# Client State
current_room = "general"
my_username = ""

def handle_server_message(data: bytes):
    """
    (Person 2): Receive JSON from server and display it nicely.
    """
    try:
        payload = json.loads(data.decode('utf-8'))
        msg_type = payload.get("type")
        
        if msg_type == "INFO":
            print(f"\n[System] {payload['msg']}")
        
        elif msg_type == "CHAT":
            print(f"\n[{payload['room']}] {payload['sender']}: {payload['text']}")
        
        elif msg_type == "DM":
            print(f"\n[DM from {payload['sender']}]: {payload['text']}")
        
        elif msg_type == "HISTORY":
            print(f"\n--- History for {payload['room']} ---")
            for item in payload['data']:
                print(f"[{payload['room']}] {item['sender']}: {item['text']}")
            print("------------------------------------")
        
        # Update current room when we get confirmation of joining
        if msg_type == "INFO":
            msg = payload.get('msg', '')
            if "You joined" in msg:
                # Extract room name from "You joined roomname"
                room_name = msg.replace("You joined", "").strip()
                global current_room
                current_room = room_name
                print(f"\n[System] Switched to room: {room_name}")
        
        # Re-print prompt
        print(f"({current_room})> ", end="", flush=True)
        
    except Exception as e:
        print(f"Error parsing server msg: {e}")

def main():
    global current_room, my_username
    
    protocol = TransportProtocol(local_port=CLIENT_PORT)
    
    try:
        print("Connecting to server...")
        conn = protocol.connect((SERVER_IP, SERVER_PORT), timeout=5.0)
        
        # Wait for connection handshake to complete (SYN -> SYN-ACK -> ACK)
        print("Waiting for connection to establish...")
        time.sleep(2.0)  # Give more time for handshake
        
        # Register callback
        protocol.on_message(conn, lambda d: handle_server_message(d))
        
        # ----- LOGIN (Person 4 Requirement) -----
        my_username = input("Enter username: ")
        login_packet = json.dumps({"type": "LOGIN", "name": my_username}).encode('utf-8')
        
        # Send LOGIN with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Sending LOGIN for '{my_username}'... (attempt {attempt + 1})")
                protocol.send_msg(conn, login_packet)
                time.sleep(1.5)  # Wait for server to process
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Retrying LOGIN... ({e})")
                    time.sleep(1.0)
                else:
                    print(f"Failed to send LOGIN after {max_retries} attempts: {e}")
                    raise
        
        # ----- AUTO-JOIN GENERAL ROOM -----
        # Automatically join the general room after login
        join_packet = json.dumps({"type": "JOIN", "room": current_room}).encode('utf-8')
        protocol.send_msg(conn, join_packet)
        time.sleep(0.5)  # Wait for join confirmation
        
        # ----- INPUT LOOP (Person 2) -----
        print("Commands: /join <room>, /dm <user> <msg>, /quit")
        
        while True:
            text = input(f"({current_room})> ").strip()
            
            if not text:
                continue
            
            if text.startswith("/quit"):
                break
            
            elif text.startswith("/join") or text.startswith("/ join"):
                # Parse: "/join roomname" or "/ join roomname" (handle space after slash)
                try:
                    # Remove leading slash and any spaces, then split
                    cleaned = text.lstrip("/").strip()
                    parts = cleaned.split(" ", 1)
                    if len(parts) < 2:
                        print("Usage: /join <room_name>")
                        print("Example: /join gambling")
                        continue
                    
                    room_name = parts[1].strip()
                    if not room_name:
                        print("Error: Room name cannot be empty")
                        print("Usage: /join <room_name>")
                        continue
                    
                    # Don't update current_room until server confirms
                    pkt = json.dumps({"type": "JOIN", "room": room_name}).encode('utf-8')
                    protocol.send_msg(conn, pkt)
                    print(f"Joining room '{room_name}'...")
                except Exception as e:
                    print(f"Error: {e}")
            
            elif text.startswith("/dm"):
                # Parse: "/dm user message..."
                try:
                    parts = text.split(" ", 2)
                    if len(parts) < 3:
                        print("Usage: /dm <user> <message>")
                        continue
                    
                    target = parts[1]
                    msg = parts[2]
                    pkt = json.dumps({"type": "DM", "target": target, "text": msg}).encode('utf-8')
                    protocol.send_msg(conn, pkt)
                except Exception as e:
                    print(f"Error: {e}")
            
            else:
                # Regular chat message
                pkt = json.dumps({
                    "type": "MSG",
                    "room": current_room,
                    "text": text
                }).encode('utf-8')
                protocol.send_msg(conn, pkt)
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        try:
            protocol.stop()
        except Exception as e:
            # Ignore errors when stopping - server might already be closed
            pass
        print("Client shut down.")

if __name__ == "__main__":
    main()