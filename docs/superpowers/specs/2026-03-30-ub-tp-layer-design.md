# UB TP Layer (Transport Layer) Design Spec

**Date:** 2026-03-30
**Status:** Draft
**Target:** Vibe-UB project, RTP mode only (simplified version)

## 1. Overview

This document specifies the design of the Transport Layer (TP) for the Vibe-UB project. It implements a simplified RTP (Reliable Transport) mode as specified in UB Base Specification Revision 2.0.

### 1.1 Scope

This implementation focuses on the minimal viable RTP functionality:
- PSN (Packet Sequence Number) generation and tracking
- Basic retransmission mechanism
- TPACK/TPNAK handling
- Out-of-order packet detection and buffering

Advanced features like TPSACK, congestion control, multi-channel support, and TPG are deferred to future iterations.

### 1.2 References

- UB Base Specification Revision 2.0, Section 6 (Transport Layer)
- Existing DLL and PCS layer code in Vibe-UB project

## 2. Architecture

### 2.1 Protocol Stack Position

```
TA Layer (Transaction Layer)
    ↑
TP Layer (Transport Layer) ← This layer
    ↑
NL Layer (Network Layer)
    ↑
DLL Layer (Data Link Layer)
    ↑
PCS/PHY Layer
```

### 2.2 Module Hierarchy

```
ub_controller_tx/rx (top)
    └── ub_tp_controller_tx/rx (TP top)
            ├── ub_tp_transmitter (RTP sender)
            └── ub_tp_receiver (RTP receiver)
```

### 2.3 Directory Structure

```
rtl/
├── tp/
│   ├── ub_tp_transmitter.v      # RTP transmitter
│   ├── ub_tp_receiver.v        # RTP receiver
│   ├── ub_tp_controller_tx.v   # TP TX controller
│   └── ub_tp_controller_rx.v   # TP RX controller
├── dll/                          (existing)
├── pcs/                          (existing)
├── ub_controller_tx.v
└── ub_controller_rx.v

tb/
└── tp/                           (new testbenches)
    ├── ub_tp_transmitter_tb.v
    ├── ub_tp_receiver_tb.v
    └── ub_tp_loopback_tb.v
```

## 3. Interface Definitions

### 3.1 Interface Style

All interfaces follow the same ready/valid handshake pattern as used in existing DLL and PCS layers:
- `clk, rst_n`: Clock and active-low reset
- `valid`: Indicates valid data on the bus
- `ready`: Indicates receiver is ready to accept data
- `sop`: Start of packet (first flit of a transaction)
- `eop`: End of packet (last flit of a transaction)
- `data[159:0]`: 160-bit (20-byte) flit data

### 3.2 TA Layer → TP Layer (TA-TP TX Interface)

Interface from Transaction Layer to TP Transmitter:

```systemverilog
// TA → TP (Transaction Layer to TP Transmitter)
input  [159:0] ta_data,        // Transaction data (flit)
input        ta_valid,         // TA data valid
input        ta_sop,           // Start of transaction packet
input        ta_eop,           // End of transaction packet
output       ta_ready,         // TP is ready to accept

// TP → TA (Transmitter side status)
output [23:0] tp_tx_psn,        // Current PSN being sent
output        tp_tx_busy,       // Transmitter is busy (buffer full)
```

### 3.3 TP Layer → NL Layer (TP-NL TX Interface)

Interface from TP Transmitter to Network Layer:

```systemverilog
// TP → NL (TP Transmitter to Network Layer)
output [159:0] tp_tx_data,       // TP Packet data (with RTPH)
output        tp_tx_valid,      // TP data valid
output        tp_tx_sop,        // Start of TP Packet
output        tp_tx_eop,        // End of TP Packet
input         tp_tx_ready,      // NL is ready to accept
```

### 3.4 NL Layer → TP Layer (NL-TP RX Interface)

Interface from Network Layer to TP Receiver:

```systemverilog
// NL → TP (Network Layer to TP Receiver)
input  [159:0] nl_rx_data,       // Received TP Packet data
input         nl_rx_valid,      // NL data valid
input         nl_rx_sop,        // Start of received TP Packet
input         nl_rx_eop,        // End of received TP Packet
output        nl_rx_ready,      // TP is ready to accept
```

### 3.5 TP Layer → TA Layer (TP-TA RX Interface)

Interface from TP Receiver to Transaction Layer:

```systemverilog
// TP → TA (TP Receiver to Transaction Layer)
output [159:0] tp_rx_data,       // Received transaction data
output        tp_rx_valid,      // TP data valid
output        tp_rx_sop,        // Start of transaction packet
output        tp_rx_eop,        // End of transaction packet
input         tp_rx_ready,      // TA is ready to accept

// TP → TA (Receiver side status)
output [23:0] tp_rx_expected_psn, // Next expected PSN
output        tp_rx_drop,        // Packet dropped (PSN skip detected)
output        tp_rx_dup,         // Duplicate packet received
```

### 3.6 TP Receiver → TP Transmitter (Feedback Interface)

Internal interface for TPACK/TPNAK feedback:

```systemverilog
// TP Receiver → TP Transmitter (feedback)
output [23:0] tp_ack_psn,       // PSN being acknowledged
output        tp_ack_valid,     // TPACK valid
output        tp_nak_psn,       // PSN being NAK'ed
output        tp_nak_valid,     // TPNAK valid
```

## 4. RTP Header (RTPH) Format

### 4.1 RTPH Structure (16 bytes total)

See UB-TP.md Section 6.2.1, Figure 6-8.

```
Byte 0-3:
  [7:0]   TPOpcode     // Transport Opcode (0x00 for RTP data)
  [9:8]   TPVer        // Transport Version (2'b00)
  [11:10] Padding      // Padding bits
  [15:12] NLP          // Next Layer Protocol

Byte 4-7:
  [23:0]  SrcTPN       // Source TPEP identifier (24 bits)

Byte 8-11:
  [23:0]  DstTPN       // Destination TPEP identifier (24 bits)

Byte 12-15:
  [31:24] Reserved     // Reserved bits
  [23:0]  PSN          // Packet Sequence Number (24 bits)
```

### 4.2 TPOpcode Values

- `0x00`: RTP Data Packet
- `0x01`: TPACK (Acknowledgement)
- `0x02`: TPNAK (Negative Acknowledgement)

This simplified implementation only handles `0x00` (Data) and generates/processes `0x01` (TPACK) and `0x02` (TPNAK).

## 5. Module Specifications

### 5.1 ub_tp_transmitter (RTP Transmitter)

**Responsibilities:**
1. Accept transaction data from TA layer
2. Add RTPH header with PSN
3. Store packets in retransmission buffer
4. Forward packets to NL layer
5. Process TPACK/TPNAK from receiver
6. Retransmit packets when requested

**Key Parameters:**
- `PSN_BITS`: 24 bits
- `RETRANSMIT_BUFFER_DEPTH`: 32 entries (configurable)
- `MAX_RETRIES`: 3 (configurable)

**Internal State:**
- `current_psn[23:0]`: Next PSN to assign
- `retransmit_buffer`: Array of buffers storing packets awaiting ACK
- `retry_counters`: Retry count for each buffered packet

**Input/Output:**
See Section 3.2, 3.3, and 3.6.

### 5.2 ub_tp_receiver (RTP Receiver)

**Responsibilities:**
1. Accept TP Packets from NL layer
2. Strip RTPH header
3. Check PSN for expected sequence
4. Buffer out-of-order packets
5. Reorder and deliver to TA layer in sequence
6. Detect duplicate packets
7. Generate TPACK for successful reception
8. Generate TPNAK for missing packets

**Key Parameters:**
- `PSN_BITS`: 24 bits
- `REORDER_BUFFER_DEPTH`: 32 entries (configurable)

**Internal State:**
- `expected_psn[23:0]`: Next expected PSN
- `reorder_buffer`: Array of buffers storing out-of-order packets
- `received_bitmap`: Bitmap tracking received packets

**Input/Output:**
See Section 3.4, 3.5, and 3.6.

### 5.3 ub_tp_controller_tx (TP TX Controller)

**Responsibilities:**
1. Instantiate `ub_tp_transmitter`
2. Connect TA layer interface to transmitter
3. Connect transmitter to NL layer interface
4. Connect feedback from TP receiver to transmitter

### 5.4 ub_tp_controller_rx (TP RX Controller)

**Responsibilities:**
1. Instantiate `ub_tp_receiver`
2. Connect NL layer interface to receiver
3. Connect receiver to TA layer interface
4. Connect feedback from receiver to transmitter

## 6. Data Flow

### 6.1 Transmit Path (TA → TP → NL)

1. TA layer presents transaction data with `ta_valid/ta_sop/ta_eop`
2. TP Transmitter:
   - Accepts data when `ta_ready` is high
   - Assigns PSN (incrementing from 0)
   - Prepends RTPH header
   - Stores copy in retransmission buffer
   - Presents to NL layer with `tp_tx_valid/tp_tx_sop/tp_tx_eop`
3. NL layer accepts data when `tp_tx_ready` is high

### 6.2 Receive Path (NL → TP → TA)

1. NL layer presents TP Packet with `nl_rx_valid/nl_rx_sop/nl_rx_eop`
2. TP Receiver:
   - Accepts data when `nl_rx_ready` is high
   - Strips RTPH header
   - Extracts PSN
   - If PSN == expected_psn:
     - Delivers to TA layer immediately
     - Increments expected_psn
     - Checks reorder buffer for next packets
     - Generates TPACK
   - Else if PSN > expected_psn:
     - Stores in reorder buffer
     - Generates TPNAK for missing PSN
   - Else (PSN < expected_psn):
     - Drops as duplicate (or accepts if gap was reported)
3. TA layer accepts data when `tp_rx_ready` is high

### 6.3 Retransmission Flow

1. TP Receiver detects missing packet (PSN gap)
2. TP Receiver generates TPNAK for missing PSN
3. TP Transmitter receives TPNAK
4. TP Transmitter retrieves packet from retransmission buffer
5. TP Transmitter retransmits the packet
6. TP Receiver receives retransmitted packet
7. TP Receiver delivers to TA layer in order
8. TP Receiver generates TPACK

## 7. Testing Strategy

### 7.1 Module-Level Tests

- `ub_tp_transmitter_tb.v`: Verify PSN generation, header insertion, buffer storage
- `ub_tp_receiver_tb.v`: Verify PSN checking, reordering, TPACK/TPNAK generation
- `ub_tp_loopback_tb.v`: End-to-end loopback test with packet loss and retransmission

### 7.2 Test Cases

1. Basic packet transmission (no loss)
2. Out-of-order packet reception
3. Missing packet detection and retransmission
4. Duplicate packet detection
5. Backpressure handling (ready/valid flow control)

## 8. Configuration Parameters

All configurable parameters defined as module parameters:

```systemverilog
parameter PSN_BITS        = 24,    // PSN bit width
parameter RETRANSMIT_DEPTH = 32,   // Retransmission buffer depth
parameter REORDER_DEPTH    = 32,   // Reorder buffer depth
parameter MAX_RETRIES      = 3     // Max retransmission attempts
```

## 9. Future Enhancements

This is a simplified RTP implementation. Future iterations may add:

- TPSACK (Selective Acknowledgement)
- Congestion control (CNP handling)
- Multiple TP Channels
- TPG (Transport Channel Group) support
- CTP and UTP modes
- TP Bypass mode

