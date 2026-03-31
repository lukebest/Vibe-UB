Appendix B Packet Formats




Appendix B Packet Formats


B.1 Overview
This chapter provides an overview of the packet format layouts supported by UB. For detailed
information on header formats of specific layers, including extension header layouts, field definitions,
and usage guidelines, refer to the chapter dedicated to the corresponding protocol layer.

UB packet types are categorized into basic groups according to the configuration type field (CFG)
present in the link packet header (LPH). The following table lists these categories along with basic
subgroups, which are further distinguished by additional fields within the headers of subsequent
protocol layers.

                      Table B-1 Mapping between LPH.CFG values and packet types
 CFG       Packet Type Identification                        Packet Description
 0         CFG == 0                                          Data link layer control block (DLLCB), used
                                                             for control, status, and configuration
                                                             information exchange between the two
                                                             ports of a UB link.
 3         (CFG == 3) & ((Non-UDP packet) | (UDP             TCP/IPv4 stack packets.
           destination port != 4792))
           (CFG == 3) & (UDP destination port == 4792)       UB packets over IPv4.
 4         (CFG == 4) & ((Non-UDP packet) | (UDP             TCP/IPv6 stack packets.
           destination port != 4792))
           (CFG == 4) & (UDP destination port == 4792)       UB packets over IPv6.
 5         CFG == 5                                          Network control packets over the UB link,
                                                             adapted to the IP network management
                                                             system.
 6         (CFG == 6) & ((NTH.NLP == 0) &                    Used for accessing non-coherent memory
           (BTAH.Opcode != 0x10))                            and device resource spaces.
           (CFG == 6) & ((NTH.NLP == 0) &                    Configuration management packets, used
           (BTAH.Opcode == 0x10))                            for configuring space access and
                                                             managing devices.
           (CFG == 6) & (NTH.NLP == 1)                       Enumeration packets.
 7         CFG == 7                                          UB packets, based on the compact
                                                             network address (CNA) at the network
                                                             layer.
 9         CFG == 9                                          Used for accessing coherent memory
                                                             spaces.




unifiedbus.com                                                                                         390
Appendix B Packet Formats




 CFG         Packet Type Identification                            Packet Description
 1, 2, 8,    Reserved                                              Reserved.
 10–15


B.2 Packet Formats
The following color scheme applies to all packet formats in this section unless otherwise specified.

      Link packet header (LPH): For its definition, see Section 4.3.2.2.2.
      Network header (NTH): It utilizes the IP header, 24-bit CNA header, or 16-bit CNA header,
depending on the network scale or communication object. For details, see Section 5.2.
     Transport header (TPH): Depending on the transport mode, reliable transport header (RTPH),
unreliable transport header (UTPH), or compact transport header (CTPH) can be used. For details, see
Section 6.2.1.

                    UB partition identifier header (UPIH, 32-bit or 16-bit) and entity identifier header (EIDH,
256-bit or 40-bit). For details, see Appendix B.3 and Appendix B.4 For details about confidentiality and
integrity protection header (CIPH), see Section 11.5.2.3.

      Transaction header (TAH): Basic transaction header (BTAH) and extension headers vary by use
case and semantics. For details, see Section 7.2.

Note 1: For the Pad and Reserved (or Rsvd) fields in headers, the sender pads them with zeros, and the receiver
ignores the values of these fields.



B.2.1 LPH.CFG == 0
Packets with LPH.CFG == 0 are data link layer control blocks that handle port control, status, and
configuration information exchange, enabling flow control, retry, port information exchange, and other
data link layer functions. Data link layer control blocks are generated and processed at the data link
layer only, and do not include the NTH, TPH, and TAH. For detailed packet formats and definitions, see
Section 4.3.3.


B.2.2 LPH.CFG == 3/4

B.2.2.1 IP-Address-Based UB Packet Format

For IP-address-based UB packets, the LPH.CFG value is 3 (IPv4) or 4 (IPv6). The NTH uses the IP
packet header, and some network interconnection rules are modified or newly defined. For details, see
the network layer specification. The format includes the UDP header, where the UDP destination port is
4792. The transport layer adopts the RTP or UTP mode, and the TPH in the packet format is either
RTPH or UTPH.




unifiedbus.com                                                                                                    391
Appendix B Packet Formats




For physical-machine-based or virtual-machine-based communication, the packet MAY optionally
include the UPIH (with 32-bit UPI) or the EIDH (with 128-bit source and destination EIDs). For details
about the UPIH and EIDH formats, see Appendix B.3 and Appendix B.4, respectively.

Basic format (TPH.NLP == 0):




                        Figure B-1 Basic format of an IP-address-based packet


Packet format when the UPIH and EIDH are included for virtualization scenarios, where TPH.NLP == 1:




                 Figure B-2 Format of an IP-address-based packet with UPIH and EIDH


Packet format when the TPH is followed by the CIPH, where TPH.NLP == 3 and CIPH.NLP == 2:




                     Figure B-3 Format of an IP-address-based packet with CIPH


Packet format when the CIPH is followed by UPIH and EIDH, where TPH.NLP == 3 and CIPH.NLP == 0:




            Figure B-4 Format of an IP-address-based packet with CIPH, UPIH, and EIDH


B.2.2.2 TCP/IP Packet Format over the UB Link

This specification supports the TCP/IP stack based on the UB link. In this case, the NTH is derived from
the network layer headers of the TCP/IP stack. Specifically, IPv4 packet headers are used when
LPH.CFG == 3, and IPv6 packet headers are used when LPH.CFG == 4. For details about the packet
formats, see Section 5.2.3.


B.2.3 LPH.CFG == 5
Packets with LPH.CFG == 5 are network control packets.

Network control packets support interoperability between the UB network and IP network management
protocols. For details about the packet formats, see Appendix F.2.




unifiedbus.com                                                                                       392
Appendix B Packet Formats




B.2.4 LPH.CFG == 6

B.2.4.1 Formats of Packets Accessing Non-Coherent Memory Spaces

Packets that access non-coherent memory and device resource spaces are identified by LPH.CFG == 6
and utilize the 16-bit CNA-based NTH, with NTH.NLP == 0.

Packets of this type adopt the CTP mode at the transport layer, with CTPH.NLP == 2.

The packet described in this section contains the 16-bit UPI and the EIDH (with 20-bit source and
destination EIDs respectively). For details about the UPI and EID headers, refer to the content about
UPIH and EIDH formats in this chapter.




                 Figure B-5 Format of packets that access non-coherent memory spaces


Packet format when CIPH, UPIH, and EIDH are included (CTPH.NLP == 3 and CIPH.NLP == 1):




         Figure B-6 Format of packets that access non-coherent memory spaces, with CIPH


B.2.4.2 Formats of Configuration Management Packets

Configuration management packets are used for configuring space access and managing devices.

These packets are identified by LPH.CFG == 6, with NTH.NLP == 0.

For details about the packet formats, see Section 10.4.3.


B.2.4.3 Formats of Enumeration Packets

Enumeration packets are used by the UB Fabric Manager (UBFM) for device enumeration, CNA
allocation, and address query.

These packets are identified by LPH.CFG == 6, with NTH.NLP == 1.

For details about the packet formats, see Section 10.4.3.


B.2.5 LPH.CFG == 7
For UB packets based on the 24-bit CNA, the LPH.CFG value is 7, with the NTH based on the 24-bit CNA.

If the UPIH is contained in the packet, the 32-bit UPI is required; if the EIDH is contained, the source
EID and destination EID should be 128 bits respectively. For details about the UPIH and EIDH, refer to
the content about UPIH and EIDH formats in this chapter.




unifiedbus.com                                                                                             393
Appendix B Packet Formats




These packets can carry CTPH or RTPH, depending on the value of NTH.NLP. For details, see
Section 5.2.2.

Format of UB packets (NTH.NLP == 3'b000) based on the 24-bit CNA and CTP:

CTPH.NLP == 1, with UPIH and EIDH




            Figure B-7 Format of a 24-bit CNA-based packet, with CTPH, UPIH, and EIDH


CTPH.NLP == 3, with CIPH and subsequent packet format specified by the CIPH




         Figure B-8 Format of a 24-bit CNA-based packet, with CIPH, CTPH, UPIH, and EIDH


Format of UB packets (NTH.NLP == 3'b010) based on the 24-bit CNA and RTP:

Except for using the 24-bit CNA-based NTH, packets in this mode have the same format structures and
header definitions as the IP-address-based UB packets (LPH.CFG == 3/4). For details, refer to the
formats of IP-address-based UB packets (LPH.CFG == 3/4).


B.2.6 LPH.CFG == 9
Packets of this type are identified by LPH.CFG == 9 and use the 16-bit CNA-based NTH, with
NTH.NLP == 0, and no invariant cyclic redundancy code (ICRC) is included.

These packets do not contain the TPH, without EIDH or UPIH.

This section outlines the LPH.CFG == 9 packet formats according to different requests and responses.
For details about extension header types and formats contained in the TAH under different transaction
operations, refer to the transaction layer specification.

Packet format of request with payload (write, write with BE, atomic):




                       Figure B-9 Packet format of a CFG9 request with payload


Packet format of request without payload (read, PrefetchTgt):




                     Figure B-10 Packet format of a CFG9 request without payload




unifiedbus.com                                                                                      394
Appendix B Packet Formats




Packet format of response with payload (read response, atomic response, excluding atomic store response):




                      Figure B-11 Packet format of a CFG9 response with payload


Packet format of response without payload (write response, atomic store response):




                     Figure B-12 Packet format of a CFG9 response without payload


B.2.7 Formats of Transport Layer Packets
Transport layer packets are generated and processed by the transport layer itself, serving two primary
purposes, responding to service packets and transmitting congestion notifications.

CTP mode only implements congestion control and supports congestion notification packets (CNPs).
Since request operations do not require transport acknowledgment (TPACK) responses, this mode
does not support any TPACK packet.

RTP mode supports all types of transport layer packets.

For details about the packet formats, see Section 6.2.


B.3 UPI Header (UPIH)
A UPI is an isolation identifier for a collection of Entities. It implements partitioned Entity access and
guarantees unique identification within a domain. Entity partitions with different UPIs are isolated, and
the UPI never participates in switch forwarding. For verification, the receiver checks if the packet's UPI
matches the local UPI. Local resource access is permitted only if both UPIs match.

UPIH formats and definitions:

          Byte0                       Byte1                        Byte2                     Byte3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0

                                                       UPI[31:0]

                                     Figure B-13 32-bit UPIH format


                        Byte0                                                  Byte1
  7      6       5     4      3      2      1      0       7       6    5     4      3      2      1         0
                                                  UPI[15:0]
                                     Figure B-14 16-bit UPIH format




unifiedbus.com                                                                                               395
Appendix B Packet Formats



                                          Table B-2 UPIH fields
 Field               Bit Width    Description
 UPI                 32/16        UPI has two formats:
                                  ● Non-compact format:
                                    UPI[23:0]: Indicates the partition number.
                                    UPI[31:24]: Reserved.
                                  ● Compact format:
                                    UPI[14:0]: Indicates the partition number.
                                    UPI[15]: Reserved.


B.4 EID Header (EIDH)
EIDH formats and definitions:

          Byte0                      Byte1                     Byte2                     Byte3

 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0

                                                SEID[127:96]

                                                SEID[95:64]

                                                SEID[63:32]

                                                 SEID[31:0]

                                                DEID[127:96]

                                                DEID[95:64]

                                                DEID[63:32]

                                                 DEID[31:0]

                                   Figure B-15 128-bit EIDH format


          Byte0                      Byte1                     Byte2                     Byte3

 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0

                             SEID[19:0]                                          DEID[19:8]

         DEID[7:0]

                                    Figure B-16 20-bit EIDH format




unifiedbus.com                                                                                   396
Appendix B Packet Formats



                                   Table B-3 EIDH fields
 Field           Bit Width   Description
 SEID            128/20      Source EID, with two formats:
                             ● Non-compact format: 128 bits
                             ● Compact format: 20 bits

 DEID            128/20      Destination EID, with two formats:
                             ● Non-compact format: 128 bits
                             ● Compact format: 20 bits




unifiedbus.com                                                    397
