# Project Requirements Checklist

## ✅ IMPLEMENTED

### Transport Protocol Requirements
- ✅ Header Definition: `ver`, `flags`, `conn_id`, `seq`, `ack`, `len`, `checksum`
- ✅ Reliability: Go-Back-N sliding window (MAX_WINDOW_SIZE = 10)
- ✅ Flow Control: Receiver-advertised window
- ✅ Timeout & Retransmission: RTT-based estimation (TCP-like)
- ✅ API: Message-oriented (`connect()`, `send_msg()`, `on_message()`, `close()`)
- ✅ Checksum: MD5-based checksum verification
- ✅ Out-of-order handling: Buffering and in-order delivery

### Application Requirements (Chat)
- ✅ Reliable, in-order message delivery
- ✅ Sliding Window ARQ (Go-Back-N)
- ✅ Out-of-order arrivals handled
- ✅ Concurrency: ≥2 concurrent clients supported
- ✅ Message history (+2% bonus) ✅
- ✅ Private messages/DM (+2% bonus) ✅
- ✅ Persistent usernames (+2% bonus) ✅

## ❌ MISSING / NEEDS IMPLEMENTATION

### Metrics Collection & Reporting (REQUIRED)
- ❌ **Message Latency**: Average and 95th-percentile (in milliseconds)
- ❌ **Goodput**: Messages per second successfully delivered
- ❌ **Retransmissions per KB**: Calculate from stats
- ❌ **Out-of-order messages**: Count/percentage of out-of-order packets received and corrected
- ❌ **Maximum concurrent clients**: Test and report maximum supported
- ❌ **Metrics reporting script**: Generate tables/plots from collected data

### Bonus Features (Optional)
- ❌ Priority messages (+2%): Ensure presence updates delivered before chat messages
- ❌ Multiple servers (+2%): Federation across >1 server

### Testing Requirements
- ❌ **Lossy network shim testing**: Test under 3 different profiles
- ❌ **Metrics analysis**: Proper collection, analysis, and reporting
- ❌ **Reproducible results**: Clear testing methodology

## ACTION ITEMS

1. **Create metrics collection system** - Track message send/receive times
2. **Create metrics reporting script** - Calculate and display all required metrics
3. **Add out-of-order tracking** - Count out-of-order packets
4. **Test maximum concurrent clients** - Stress test and report limit
5. **Create lossy network shim integration** - Test under packet loss conditions
6. **Document testing methodology** - Make results reproducible

