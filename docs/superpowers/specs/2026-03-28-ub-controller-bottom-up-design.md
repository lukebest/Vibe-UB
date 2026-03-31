# Design Spec: UB Controller Bottom-Up (PCS & DLL)

**Date:** 2026-03-28  
**Status:** Draft for Review  
**Target:** UnifiedBus (UB) Base Specification Revision 2.0 (PHY Mode-2)

## 1. Overview
This document specifies the design for the Bottom-Up implementation of a UB Controller, focusing on the Physical Coding Sublayer (PCS) and the Data Link Layer (DLL). The target configuration is PHY Mode-2 (53G/106G PAM4) with support for 4 or 8 lanes.

## 2. Architecture

### 2.1 Data Link Layer (DLL)
The DLL provides reliable, point-to-point packet delivery using flit-based transfer.

*   **Framing:**
    *   **DLLDP (Data Packets):** 1-512 flits.
    *   **DLLCB (Control Blocks):** 1-32 flits.
    *   **DLLDB (Data Blocks):** Maximum 32 flits per segment.
*   **Headers:**
    *   **LPH (Link Packet Header):** 4 bytes (First flit of first DLLDB).
    *   **LBH (Link Block Header):** 2 bytes (First flit of middle/last DLLDB).
*   **Reliability:**
    *   **BCRC (Block CRC):** CRC-32 (4 bytes) at the end of each DLLDB.
    *   **Retry Buffer:** TX storage for flits awaiting ACK.
    *   **Flow Control:** Credit-based, per Virtual Lane (up to 16 VLs).
*   **Internal Interface:** Simple Ready/Valid flit-based interface for data packets from the Network Layer.
    *   `flit_data[159:0]`: 20-byte flit payload.
    *   `flit_valid`: Indicates valid data on the bus.
    *   `flit_ready`: Backpressure from the DLL (TX) or Network (RX).
    *   `flit_sop`: Start of Packet (first flit of DLLDP).
    *   `flit_eop`: End of Packet (last flit of DLLDP).
    *   `flit_vl[3:0]`: Virtual Lane ID for the packet.

### 2.2 Physical Coding Sublayer (PCS)
The PCS manages FEC, scrambling, and lane distribution.

*   **Scrambler:** PRBS-based randomization to prevent data patterns.
*   **FEC:** RS(128,120,T=4) Reed-Solomon encoding/decoding in GF(2^8).
    *   Implementation: Parallel systematic architecture for high throughput.
*   **Gray Coder:** Maps bits to symbols for PAM4 modulation.
*   **Lane Distributor:** Symbols are striped across physical lanes (4 or 8).
*   **Alignment Marker (AMCTL):** Insertion of markers for multi-lane deskew.

### 2.3 Control & Status Logic (LMSM)
*   **States:** `Disabled`, `Param_Init`, `Credit_Init`, `Normal`.
*   **CSRs:** Port configuration (lanes, speed, FEC), status monitoring, and error counters.

## 3. Data Flow

### 3.1 Transmit (TX) Path
1.  **Network Layer** sends packet over Ready/Valid flit-based interface.
2.  **DLL** segments packet into DLLDBs (max 32 flits), adds LPH/LBH and BCRC.
3.  **DLL** stores flits in Retry Buffer.
4.  **PCS** scrambles the flit stream.
5.  **PCS** applies RS-FEC encoding.
6.  **PCS** Gray codes bits into symbols.
7.  **PCS** distributes symbols to lanes and inserts AMCTL markers.
8.  **PMA Interface** sends symbol stream to SerDes.

### 3.2 Receive (RX) Path
1.  **PMA Interface** receives symbols from SerDes.
2.  **PCS** detects AMCTL and deskews lanes.
3.  **PCS** Gray decodes symbols back to bits.
4.  **PCS** performs RS-FEC decoding (error correction).
5.  **PCS** descrambles the bit stream.
6.  **DLL** checks BCRC for each DLLDB.
7.  **DLL** parses LPH/LBH and reassembles packet.
8.  **DLL** forwards completed packet to **Network Layer** over Ready/Valid flit-based interface.

## 4. Resource & Timing Goals
*   **Clock Frequency:** Target 250MHz - 400MHz depending on internal bus width (128-512 bits).
*   **Throughput:** Must support 100Gbps+ effective line rate.
*   **Latency:** Minimal latency through FEC/CRC paths.

## 5. Testing Strategy
*   **Module-Level:** UVM/Verilog testbenches for FEC, CRC, and Scrambler.
*   **Integration:** Loopback testing between TX and RX paths.
*   **Protocol Compliance:** Verified against UB Base Specification 2.0 packet formats.
