# UnifiedBus (UB) Base Specification — section index

This file lists **chapter/section numbers and titles only** from *UnifiedBus (UB) Base Specification Revision 2.0* (release date 2025-12-31). It is a project navigation index, not a copy of the specification.

- Two heading levels for chapters 1–11, plus Appendices A–I and their sub-sections.
- No body text, tables, figures, formulas, or register fields from the specification are reproduced here.
- The **Phase** column maps each item to this project's implementation batch (see [DECISIONS.md](DECISIONS.md) D18, which supersedes D2). Lines A/B/C and the Load/Store priority path are **D19** ([SPEC.md](SPEC.md) §1.4, [arch/TRADEOFFS.md](arch/TRADEOFFS.md)). Module list: [arch/MODULE_INVENTORY.md](arch/MODULE_INVENTORY.md).

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
| 3 | Physical Layer | batch 1 (M1) |
| 3.1 | Overview | batch 1 (M1) |
| 3.2 | Physical Coding Sublayer | batch 1 (M1) |
| 3.3 | Physical Medium Attachment | batch 1 (M1) |
| 3.4 | Link State Management | batch 1 (M1) |
| 4 | Data Link Layer | batch 1 (M1) |
| 4.1 | Overview | batch 1 (M1) |
| 4.2 | Data Link State Machine | batch 1 (M1) |
| 4.3 | DLLCB/DLLDP Sending and Receiving | batch 1 (M1) |
| 4.4 | Initialization Auto-negotiation | batch 1 (M1) |
| 4.5 | VL Mechanism | batch 1 (M1) |
| 4.6 | Credit-based Flow Control Mechanism | batch 1 (M1) |
| 4.7 | Bit Error Detection and Retransmission Mechanism | batch 1 (M1) |
| 4.8 | Exception Handling | batch 1 (M1) |
| 5 | Network Layer | later batch |
| 5.1 | Overview | later batch |
| 5.2 | Network Header (NTH) | later batch |
| 5.3 | Network Layer Features | later batch |
| 6 | Transport Layer | later batch |
| 6.1 | Overview | later batch |
| 6.2 | Transport Layer Packet Format | later batch |
| 6.3 | Transport Layer Mode | later batch |
| 6.4 | RTP Reliable Transmission Mechanism | later batch |
| 6.5 | Multipath Load Balancing | later batch |
| 6.6 | Congestion Control Mechanism | later batch |
| 6.7 | Transmission Process | later batch |
| 6.8 | Interaction Between the Transport Layer and Transaction Layer | later batch |
| 7 | Transaction Layer | later batch |
| 7.1 | Overview | later batch |
| 7.2 | Transaction Headers | later batch |
| 7.3 | Transaction Services | later batch |
| 7.4 | Transaction Types | later batch |
| 8 | Function Layer | later batch |
| 8.1 | Overview | later batch |
| 8.2 | Basic Concepts | later batch |
| 8.3 | Load/Store Synchronous Access | later batch |
| 8.4 | URMA Asynchronous Access | later batch |
| 8.5 | URPC | later batch (optional) |
| 8.6 | Multi-Entity Coordination | later batch (optional) |
| 8.7 | Entity Management | later batch |
| 9 | Memory Management | later batch |
| 9.1 | Overview | later batch |
| 9.2 | Home-User Access Model | later batch |
| 9.3 | UBMD | later batch |
| 9.4 | UMMU Functions and Working Process | later batch |
| 9.5 | UB Decoder Functions and Processes | later batch |
| 10 | Resource Management | later batch |
| 10.1 | Overview | later batch |
| 10.2 | Basic Concepts | later batch |
| 10.3 | Working Mechanism | later batch |
| 10.4 | Management Mechanism | later batch |
| 10.5 | Virtualization | later batch (optional) |
| 10.6 | RAS | later batch |
| 11 | Security | later batch |
| 11.1 | Overview | later batch |
| 11.2 | Device Authentication | later batch |
| 11.3 | Resource Partitioning | later batch |
| 11.4 | Access Control | later batch |
| 11.5 | Data Transmission Security | later batch (optional) |
| 11.6 | TEE Extension | later batch (optional) |
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
| D | Configuration Space Registers | batch 1 subset; later expand |
| D.1 | CFG0_BASIC | later batch |
| D.2 | CFG0_CAP | later batch |
| D.3 | CFG1_BASIC | later batch |
| D.4 | CFG1_CAP | later batch |
| D.5 | CFG0_PORT_BASIC | batch 1 (port subset) |
| D.6 | CFG0_PORT_CAP | batch 1 (port subset) |
| D.7 | CFG0_ROUTE_TABLE | later batch |
| E | Ethernet Interworking | later (appendix) |
| F | Network Management Based on UB Links | later (appendix) |
| F.1 | Applicable Scenarios | later (appendix) |
| F.2 | Management Protocols | later (appendix) |
| G | Device Hot-Plug | later (appendix) |
| G.1 | General Requirements | later (appendix) |
| G.2 | Components Enabling Device Hot-Plug | later (appendix) |
| G.3 | Hot-Removal Process | later (appendix) |
| G.4 | Hot-Add Process | later (appendix) |
| G.5 | Hot-Plug Events | later (appendix) |
| H | URPC Message Format | later (appendix) |
| H.1 | Overview | later (appendix) |
| H.2 | URPC Function | later (appendix) |
| H.3 | URPC Messages | later (appendix) |
| I | Application Example | reference |
| I.1 | Storage PLOG | reference |

Phase key (D18 full controller; **D19** lines):

- **batch 1 (M1)** — chapter 3 PHY / PCS / PMA / LMSM, chapter 4 DLL. Line **A** first slice.
- **batch 1 (port subset)** / **batch 1 subset; later expand** — Appendix D port/link slices already in M1 REGMAP; device-level and route-table slices wait (line C / yaml).
- **later batch** — chapters 5–11. D19: line **A** continues NW; line **B** is TP→TA→Function; line **C** is Memory→Resource→Security. After DLL, **NW→TP→TA→Load/Store** wins resource conflicts. Optional rows marked **(optional)** are deferred (D19 + D4).
- **later (appendix)** — App. E / F / G / H in **extension milestones after M10** (D19).
- **reference** — introductory / architectural / format material (ch. 1–2, App. A–C, App. I).

Related project docs (not part of the official spec): [arch/MODULE_INVENTORY.md](arch/MODULE_INVENTORY.md), [arch/LAYER_CONTRACTS.md](arch/LAYER_CONTRACTS.md), [arch/TRADEOFFS.md](arch/TRADEOFFS.md), [superpowers/specs/2026-03-28-ub-controller-bottom-up-design.md](superpowers/specs/2026-03-28-ub-controller-bottom-up-design.md).

## How to obtain the official specification

Download *UnifiedBus (UB) Base Specification Revision 2.0* from the official site [https://www.unifiedbus.com](https://www.unifiedbus.com). Registration and the UB Specification License Agreement apply.

The full specification text is **not redistributed** in this repository. Rev 2.1 was released 2026-09-18, but this project pins Rev 2.0 (see [DECISIONS.md](DECISIONS.md) D1). Team members use the internal private copy (location not published).
