# UnifiedBus (UB) Base Specification — section index

This file lists **chapter/section numbers and titles only** from *UnifiedBus (UB) Base Specification Revision 2.0* (release date 2025-12-31). It is a project navigation index, not a copy of the specification.

- Two heading levels for chapters 1–11, plus Appendices A–I and their sub-sections.
- No body text, tables, figures, formulas, or register fields from the specification are reproduced here.
- The **Phase** column maps each item to this project's phased scope (see [DECISIONS.md](DECISIONS.md) D1–D2).

| Section | Title | Phase |
| --- | --- | --- |
| 1 | Introduction | reference |
| 1.1 | Purpose | reference |
| 1.2 | Scope | reference |
| 1.3 | Organization | reference |
| 1.4 | Specification Conventions | reference |
| 1.5 | Normative References | reference |
| 1.6 | Terminology | reference |
| 2 | Architecture | reference |
| 2.1 | Overview | reference |
| 2.2 | Protocol Stack | reference |
| 3 | Physical Layer | phase 1 |
| 3.1 | Overview | phase 1 |
| 3.2 | Physical Coding Sublayer | phase 1 |
| 3.3 | Physical Medium Attachment | phase 1 |
| 3.4 | Link State Management | phase 1 |
| 4 | Data Link Layer | phase 1 |
| 4.1 | Overview | phase 1 |
| 4.2 | Data Link State Machine | phase 1 |
| 4.3 | DLLCB/DLLDP Sending and Receiving | phase 1 |
| 4.4 | Initialization Auto-negotiation | phase 1 |
| 4.5 | VL Mechanism | phase 1 |
| 4.6 | Credit-based Flow Control Mechanism | phase 1 |
| 4.7 | Bit Error Detection and Retransmission Mechanism | phase 1 |
| 4.8 | Exception Handling | phase 1 |
| 5 | Network Layer | deferred |
| 5.1 | Overview | deferred |
| 5.2 | Network Header (NTH) | deferred |
| 5.3 | Network Layer Features | deferred |
| 6 | Transport Layer | deferred |
| 6.1 | Overview | deferred |
| 6.2 | Transport Layer Packet Format | deferred |
| 6.3 | Transport Layer Mode | deferred |
| 6.4 | RTP Reliable Transmission Mechanism | deferred |
| 6.5 | Multipath Load Balancing | deferred |
| 6.6 | Congestion Control Mechanism | deferred |
| 6.7 | Transmission Process | deferred |
| 6.8 | Interaction Between the Transport Layer and Transaction Layer | deferred |
| 7 | Transaction Layer | deferred |
| 7.1 | Overview | deferred |
| 7.2 | Transaction Headers | deferred |
| 7.3 | Transaction Services | deferred |
| 7.4 | Transaction Types | deferred |
| 8 | Function Layer | deferred |
| 8.1 | Overview | deferred |
| 8.2 | Basic Concepts | deferred |
| 8.3 | Load/Store Synchronous Access | deferred |
| 8.4 | URMA Asynchronous Access | deferred |
| 8.5 | URPC | deferred |
| 8.6 | Multi-Entity Coordination | deferred |
| 8.7 | Entity Management | deferred |
| 9 | Memory Management | deferred |
| 9.1 | Overview | deferred |
| 9.2 | Home-User Access Model | deferred |
| 9.3 | UBMD | deferred |
| 9.4 | UMMU Functions and Working Process | deferred |
| 9.5 | UB Decoder Functions and Processes | deferred |
| 10 | Resource Management | deferred |
| 10.1 | Overview | deferred |
| 10.2 | Basic Concepts | deferred |
| 10.3 | Working Mechanism | deferred |
| 10.4 | Management Mechanism | deferred |
| 10.5 | Virtualization | deferred |
| 10.6 | RAS | deferred |
| 11 | Security | deferred |
| 11.1 | Overview | deferred |
| 11.2 | Device Authentication | deferred |
| 11.3 | Resource Partitioning | deferred |
| 11.4 | Access Control | deferred |
| 11.5 | Data Transmission Security | deferred |
| 11.6 | TEE Extension | deferred |
| A | Acronyms and Abbreviations | reference |
| B | Packet Formats | reference |
| B.1 | Overview | reference |
| B.2 | Packet Formats | reference |
| B.3 | UPI Header (UPIH) | reference |
| B.4 | EID Header (EIDH) | reference |
| C | GUID and Class Code | reference |
| C.1 | GUID Definition | reference |
| C.2 | Class Code Definition | reference |
| C.3 | Code Usage | reference |
| D | Configuration Space Registers | phase 1 (registers subset) |
| D.1 | CFG0_BASIC | phase 1 (registers subset) |
| D.2 | CFG0_CAP | phase 1 (registers subset) |
| D.3 | CFG1_BASIC | phase 1 (registers subset) |
| D.4 | CFG1_CAP | phase 1 (registers subset) |
| D.5 | CFG0_PORT_BASIC | phase 1 (registers subset) |
| D.6 | CFG0_PORT_CAP | phase 1 (registers subset) |
| D.7 | CFG0_ROUTE_TABLE | phase 1 (registers subset) |
| E | Ethernet Interworking | reference |
| F | Network Management Based on UB Links | reference |
| F.1 | Applicable Scenarios | reference |
| F.2 | Management Protocols | reference |
| G | Device Hot-Plug | reference |
| G.1 | General Requirements | reference |
| G.2 | Components Enabling Device Hot-Plug | reference |
| G.3 | Hot-Removal Process | reference |
| G.4 | Hot-Add Process | reference |
| G.5 | Hot-Plug Events | reference |
| H | URPC Message Format | reference |
| H.1 | Overview | reference |
| H.2 | URPC Function | reference |
| H.3 | URPC Messages | reference |
| I | Application Example | reference |
| I.1 | Storage PLOG | reference |

Phase key:

- **phase 1** — chapter 3 PHY / PCS / PMA / LMSM, chapter 4 DLL, and Appendix D configuration-registers subset.
- **deferred** — chapter 5 NW, chapter 6 TP, chapter 7 TA, chapters 8–11.
- **reference** — introductory / architectural / appendix material not itself a later implementation phase in D2.

Related project note (not part of the official spec): [superpowers/specs/2026-03-28-ub-controller-bottom-up-design.md](superpowers/specs/2026-03-28-ub-controller-bottom-up-design.md).

## How to obtain the official specification

Download *UnifiedBus (UB) Base Specification Revision 2.0* from the official site [https://www.unifiedbus.com](https://www.unifiedbus.com). Registration and the UB Specification License Agreement apply.

The full specification text is **not redistributed** in this repository. Rev 2.1 was released 2026-09-18, but this project pins Rev 2.0 (see [DECISIONS.md](DECISIONS.md) D1). Team members use the internal private copy (location not published).
