# ChatSpace - Custom Transport Protocol Chat Application

A multi-user chat application built on top of a custom reliable transport protocol implemented over UDP.

## Features

- **Custom Transport Protocol**: Implements Go-Back-N sliding window, RTT-based retransmission, flow control, and checksum verification
- **Multi-User Chat**: Support for multiple concurrent clients
- **Chat Rooms**: Join and switch between different chat rooms
- **Direct Messaging**: Send private messages to specific users
- **Message History**: View chat history when joining a room
- **Username System**: Login with unique usernames
- **Metrics Collection**: Comprehensive performance metrics (latency, goodput, retransmissions)

## Project Structure

```
.
├── chat_server.py          # Chat server application
├── chat_client.py          # Chat client application
├── collect_metrics.py      # Metrics collection and reporting script
├── test_full_protocol.py   # Protocol test suite
├── transport/              # Transport protocol implementation
│   ├── __init__.py
│   ├── protocol.py         # Main transport protocol (Go-Back-N)
│   └── connection.py       # Connection management
└── README.md
```

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/juicejuarez/ChatSpace.git
cd ChatSpace
```

2. No additional installation needed - uses Python standard library only.

## Usage

### Starting the Server

```bash
python chat_server.py
```

The server will start on port 12345 by default.

### Running a Client

```bash
python chat_client.py
```

You can run multiple clients simultaneously. Each client will be assigned an available port automatically.

### Client Commands

- `/join <room_name>` - Join a chat room
- `/dm <username> <message>` - Send a direct message
- `/quit` - Exit the client

### Collecting Metrics

Run the metrics collection script to generate performance reports:

```bash
python collect_metrics.py
```

This will generate a `metrics_report.json` file with detailed statistics.

## Transport Protocol Features

- **Reliability**: Go-Back-N sliding window ARQ
- **Flow Control**: Receiver-advertised window (max 10 packets)
- **Retransmission**: RTT-based timeout estimation (TCP-like)
- **Error Detection**: MD5-based checksum verification
- **In-Order Delivery**: Handles out-of-order packets with buffering
- **Connection Management**: Three-way handshake (SYN, SYN-ACK, ACK)

## Metrics Collected

- Message latency (average and 95th percentile)
- Goodput (messages per second)
- Retransmissions per KB
- Out-of-order packet count and percentage
- Packet and byte statistics

## Testing

Run the full protocol test suite:

```bash
python test_full_protocol.py
```

## Project Requirements

This project implements:
- ✅ Custom transport protocol over UDP
- ✅ Reliable, in-order message delivery
- ✅ Flow control and congestion control
- ✅ Error detection and retransmission
- ✅ Multi-user chat application
- ✅ Message history
- ✅ Direct messaging
- ✅ Username/login system
- ✅ Comprehensive metrics collection

## License

This project is part of a Computer Networks course assignment.

## Authors

Team project for CSCI 4406 Computer Networks

