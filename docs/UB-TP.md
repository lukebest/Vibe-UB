6 Transport Layer




6 Transport Layer


6.1 Overview
The UB transport layer is positioned between the transaction layer and the network layer, as shown in
Figure 6-1. The UB transport layer provides end-to-end reliable and unreliable transmission services to
the transaction layer between transport endpoints (TPEPs). A TPEP serves as a logical endpoint
capable of sending or receiving transport layer packets. The TPEP that sends transport data packets
(TP Packets) is called the transport sender (TP sender), while the one that receives them is called the
transport receiver (TP receiver). The TP sender accepts a transaction operation from the transaction
layer, and then packetizes it into one or more TP Packets, before forwarding them to the network layer.
The TP receiver accepts TP Packets from the network layer. When reliable transmission service is in
use, the TP receiver SHALL verify the successful delivery of all transaction operation data. Upon
successful reception and placement of all TP Packets of the transaction operation, the transport layer
notifies the transaction layer for subsequent processing.




                                   Figure 6-1 Transport layer overview

The transport layer's reliable transmission service uses the packet sequence numbers (PSNs) and
retransmission mechanisms to ensure that a TP Packet is reliably delivered to the receiver and passed
to its transaction layer exactly once. The UB transport layer also provides multipath load balancing and
congestion control to reduce transport latency and improve transmission efficiency. The unreliable
transmission service does not provide retransmission and does not guarantee a TP Packet successfully
delivered to the TP receiver.

When providing reliable transmission service, the UB transaction layer must establish TP channels
between the TP sender and TP receiver. A TP channel can be shared so that multiple initiators and
targets can use a single channel in order to reduce the setup and maintenance overhead. Furthermore,
TP channels between a pair of UB processing units (UBPUs) can be grouped into a transport channel
group (TPG) for centralized management. A TPG appears as a single Entity to the transaction layer to
distribute the load of multiple transaction operations across multiple member TP channels.




unifiedbus.com                                                                                         158
6 Transport Layer



The design of the UB transport layer can adapt to the fine-grained load balancing mechanisms like per-
packet multipathing to maximize network utilization. More specifically the transport layer supports the
out-of-order packet delivery.

The transport layer offers several transport modes for different transaction layer needs: reliable
transport (RTP), compact transport (CTP), and unreliable transport (UTP). The transport layer can also
be configured as transport bypass (TP bypass). Table 6-1 lists the transport layer features of each
mode.

       1.   RTP provides reliable end-to-end transmission services, multipath load balancing, and
            congestion control based on the TP channel. It is suitable for scenarios requiring high
            reliability. A TP channel can be shared by multiple initiator-target pairs to improve scalability
            in RTP mode.
       2.   CTP requires the protocol stack lower-layer to provide reliable transmission services for the
            transaction layer. CTP provides coarse-grained congestion management mechanisms,
            including multipath load balancing based on Entities and congestion control based on
            destination Entities and virtual lanes (VLs). It is optimized for scenarios where the link quality
            is high or UBPUs are directly connected.
       3.   UTP provides unreliable transmission services. It suits transactions that are not sensitive to
            packet loss, such as in-band connection setup.
       4.   TP bypass has no transport layer functionality introduced in order to reduce the overhead. It
            is used mostly in load/store synchronous memory access transactions.

                          Table 6-1 Features supported by different transport modes
 Transfer        Reliability for            Multipath Load
                                                                Congestion Control        Other Features
 Mode            Transaction Layer          Balancing
 RTP             Reliable transmission      Based on TP         Based on TP channel       TPG
                 service                    channel                                       management,
                                                                                          TP channel
                                                                                          sharing
 CTP             Reliable transmission      Based on Entity     Based on the              /
                 service provided jointly                       destination Entity and
                 with the lower-layer of                        VL
                 the protocol stack
 UTP             Unreliable                 /                   /                         /
                 transmission service
 TP Bypass       N/A                        N/A                 N/A                       N/A




unifiedbus.com                                                                                            159
6 Transport Layer



6.2 Transport Layer Packet Format
Transport layer packets include data packets (TP Packets) and response packets. The TP sender
generates TP Packets containing transaction requests or responses. The TP receiver generates
transport layer response packets to respond to TP Packets (RTP only) and to convey congestion
information (RTP/CTP only) when necessary. Transport layer response packets use the same
Configuration (CFG) value and NTH Type value as the associated TP Packets.

Reliable Transport Header (RTPH), Unreliable Transport Header (UTPH), and Compact Transport
Header (CTPH) are basic headers of RTP, CTP, and UTP, respectively. TP bypass has no transport
layer headers. The next layer protocol (NLP) field in the network layer header indicates the type of the
transport layer header followed or whether TP bypass is used.

TP Packet format structure:



                                      Figure 6-2 TP Packet format

Transport layer response packets may include various extension headers. The formats are as follows.
TPACK, TPACK-CC, TPNAK, TPNAK-CC, TPSACK, and TPSACK-CC are used only in RTP.

    (a) Basic transport layer response packets (TPACK/TPNAK):



                                    Figure 6-3 TPACK/TPNAK format

    (b) Transport layer response packets with congestion notification information (TPACK-CC/TPNAK-CC):



                                Figure 6-4 TPACK-CC/TPNAK-CC format

    (c) Selective retransmission transport layer response packet (TPSACK):



                                       Figure 6-5 TPSACK format

    (d) Selective retransmission transport layer response packet with congestion notification information
        (TPSACK-CC):



                                     Figure 6-6 TPSACK-CC format

    (e) Congestion notification packets (CNPs, which are used in RTP/CTP):



                                         Figure 6-7 CNP format




unifiedbus.com                                                                                        160
6 Transport Layer



6.2.1 Transport Header (RTPH/UTPH/CTPH)
RTPH format

                 Byte0                               Byte1                            Byte2                                Byte3

     7   6   5   4    3    2    1   0    7   6   5    4 3 2 1       0   7     6   5    4   3       2   1   0   7   6   5   4   3   2   1    0

 0           TPOpcode                   TPVer Padding         NLP                                      SrcTPN[23:8]

 4           SrcTPN[7:0]                                                              DstTPN

 8   A F             Reserved                                                          PSN

12   RSPST            RSPINFO                                                         TPMSN

                                                      Figure 6-8 RTPH format:

UTPH format

                 Byte0                               Byte1                            Byte2                                Byte3

     7   6   5   4    3    2   1    0    7   6   5    4 3 2    1    0   7     6   5    4   3   2       1   0   7   6   5   4   3   2   1    0

 0           TPOpcode                   TPVer Padding        NLP                                        Reserved

 4            Reserved                                                            Reserved

 8                                                                 Reserved

12                                                                 Reserved

                                                      Figure 6-9 UTPH format

CTPH format

                                                                Byte0
         7                          6                    5                  4                  3               2           1           0
                 TPOpcode                                     Padding                                              NLP
                                                      Figure 6-10 CTPH format

                                                 Table 6-2 RTPH/UTPH/CTPH field
 Field               Bit                RTPH                                           UTPH                         CTPH
 TPOpcode            8 (RTPH),          Transport Opcode[7:0]: indicates                     Transport
                                                                                       TPOpcode[0:0]:
                     8 (UTPH),          the packet type and whether this   ● 0x0: unreliable Opcode[1:0]:
                     2 (CTPH)           TP Packet is the last data packet                    indicates whether
                                                                             TP Packet,
                                        of the transaction operation.                        the packet is a
                                                                             used in UTP.
                                        TPOpcode[6:0]:                                       CNP.
                                                                             The next-layer
                                        ● 0x0: used in UTP.                  header is       TPOpcode[1:0]:
                                                                             specified by    ● 0x0: CTP
                                        ● 0x1: reliable TP Packet, used      the NLP field      Packet.
                                          in RTP. The next-layer header      in the TPH.
                                          is specified by the NLP field in                   ● 0x1: CNP.
                                                                           ● Other:
                                          the TPH.                                           ● Others: reserved
                                                                             reserved.
                                        ● 0x2: TPACK/TPNAK,
                                                                                             The next-layer
                                          transport layer response                           protocol format




unifiedbus.com                                                                                                                             161
6 Transport Layer



 Field           Bit   RTPH                                    UTPH        CTPH
                          packet.                                          after the CTP
                       ● 0x3: TPACK-CC/TPNAK-CC,                           Packet is specified
                                                                           by the NLP field in
                         transport layer response
                                                                           the CTPH.
                         packet with congestion
                         information. The next-layer
                         header is CETPH.
                       ● 0x4: Reserved.
                       ● 0x5: TPSACK, transport layer
                         response packet with selective
                         acknowledgment information.
                         The next-layer header is
                         SAETPH.
                       ● 0x6: TPSACK-CC, transport
                         layer response packet with
                         congestion information and
                         selective acknowledgment
                         information. The next-layer
                         header is CETPH, followed by
                         SAETPH.
                       ● 0x7: Reserved.
                       ● 0x8: CNP, congestion
                         notification packet. The next-
                         layer header is CETPH.
                       ● Others: Reserved.

                       TPOpcode[7] indicates whether
                       a TP Packet is the last data
                       packet of a transaction operation
                       (marked as last). It can be used
                       together with TPMSN (see the
                       following description of the
                       TPMSN field) to determine
                       whether a transaction operation
                       is fully completed. This bit is valid
                       only when TPOpcode[6:0] is
                       0x1.
                       ● 0x0: Not the last TP Packet.
                       ● 0x1: Is the last TP Packet.

 NLP             4     Next layer protocol (NLP)               See RTPH.   Indicates the next-
                       indicates the next-layer protocol                   layer protocol
                       header type, applicable only in                     header type.
                       case TPOpcode[6:0] is 0x0 or                        ● 0x0:
                       0x1.
                                                                             ATAH/BTAH.
                       ● 0x0: ATAH/BTAH (see
                                                                           ● 0x1: 32 bits
                         Section 7.2).
                                                                             UPIH + 256 bits
                       ● 0x1: 32 bits UPIH + 256 bits                        EIDH+TAH.
                         EIDH (see Appendix B)                             ● 0x2: 16 bits
                       ● 0x2: Reserved.                                      UPIH + 40 bits
                       ● 0x3: CIPH (see Section 11.5).                       EIDH +TAH.




unifiedbus.com                                                                              162
6 Transport Layer



 Field           Bit   RTPH                                 UTPH        CTPH
                       ● Others: Reserved.                              ● 0x3: CIPH.
                                                                        ● Others:
                                                                          Reserved.
 Padding         2     The length from the first byte of    See RTPH.   See RTPH.
                       the TPH to the last byte of the
                       payload (the payload can be 0)
                       needs to be 4-byte aligned. This
                       field indicates the number of 0-
                       value bytes appended to the end
                       of the transport layer packet.
 TPVer           2     Transport protocol version, which    See RTPH.   N/A
                       should be 0 for the current
                       protocol version.
 SrcTPN          24    Source TPEP identifier.              N/A         N/A
 DstTPN          24    Destination TPEP identifier.         N/A         N/A
 A               1     Ack required bit indicates           N/A         N/A
                       whether the current TP Packet
                       requires the TP receiver to return
                       a separate response. If the value
                       is 1, the current request requires
                       a separate response. If the value
                       is 0, no separate response is
                       required.
 F               1     A value of 1 indicates a fake TP   N/A           N/A
                       Packet, and a value of 0 indicates
                       a normal TP Packet. When the
                       TP sender receives a transport
                       layer response indicating
                       insufficient resources at the
                       transaction layer, the TP sender
                       sends a fake packet to keep the
                       TP connection alive (see Section
                       8.2.7.3).
 PSN             24    Packet sequence number, which        N/A         N/A
                       SHALL comply with the
                       requirements in Section 6.4.1.
 TPMSN           24    TP message sequence number.          N/A         N/A
 RSPST           3     Response status.                     N/A         N/A
                       ● For TPACK/TPNAK, this field
                         indicates the completion
                         status of the transaction layer.
                          −   3'b000: Successful,
                              indicating the TPACK.
                          −   3'b001: Receiver Not
                              Ready (RNR) indicates a
                              transaction execution error
                              due to insufficient receive
                              resources on the target. In



unifiedbus.com                                                                         163
6 Transport Layer



 Field           Bit   RTPH                                   UTPH   CTPH
                              this case, RSPINFO
                              indicates RNR_Timer.
                          −   3'b010: Page Fault. It
                              indicates a transaction
                              execution error due to page
                              faults on the target. In this
                              case, RSPINFO indicates
                              RNR_Timer.
                          −   3'b011: Completer Error of
                              the transaction layer.
                          −   3'b100: Reserved.
                          −   3'b101: TPACK, carrying
                              the transaction layer
                              response details, defined
                              by RSPINFO. When the TP
                              sender receives the
                              response, the TPACK is
                              transparently transmitted to
                              the transaction layer as a
                              response to the transaction
                              operation.
                          −   Others: reserved
                       ● For TPSACK, the RSPST and
                         RSPINFO fields are fixed to 0.
 RSPINFO         5     Response information:                  N/A    N/A
                       ● If RSPST is 3'b001 or 3'b010,
                         this field indicates the
                         RNR_Timer, calculated as:
                         RNR_Timeout = 2μs *
                         2^RNR_Timer. The valid code
                         range of RNR_Timer is [0, 19].
                         Other codes are reserved.
                       ● If RSPST is 3'b011, this field
                         indicates error response
                         information as follows:
                          − 5'b00000 indicates a PSN
                            error. This error occurs only
                            when the TP receiver does
                            not support out-of-order
                            reception.
                          − 5'b00001 indicates an
                            unsupported request at the
                            transaction layer.
                          − 5'b00010 indicates a
                            remote abort at the
                            transaction layer.
                          − Others: reserved

                       ● If RSPST is 3'b101, this field



unifiedbus.com                                                              164
6 Transport Layer



 Field           Bit            RTPH                                  UTPH              CTPH
                                   indicates transaction
                                   execution status as follows:
                                     − 5'b00000 indicates an
                                       abnormal TAACK, and the
                                       type is TA retransmission
                                       recovery.
                                     − 5'b00001 indicates an
                                       abnormal TAACK, and the
                                       type is unrecoverable error.
                                     − 5'b00010 indicates the
                                       correct TAACK.
                                     − Others: reserved

                                ● Others: reserved


6.2.2 Congestion Extended Transport Header (CETPH)
CETPH is sent by the TP receiver to the TP sender to notify congestion information. It is included in
TPACK-CC, TPNAK-CC, and TPSACK-CC, or CNP packet types.

UB MAY support several congestion control algorithms such as LDCP, CAQM, and DCQCN (see
Section 6.6). The type of congestion control algorithm is negotiated during the establishment of the TP
channel; however, the implementation details are out of scope of this specification.

             Byte0                         Byte1                      Byte2                  Byte3
     7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
 0                                                    Ack_Seq
 4                                                    Ce_Seq
                                         Figure 6-11 LDCP CETPH format

                                           Table 6-3 LDCP CETPH field
 Field      Bit        Description
 Ack_Seq    32         Ack sequence: indicates the accumulated number of sequences received by the
                       TP receiver. The unit is 2 bytes. That is, each sequence equals 2 bytes. If the
                       packet size is not an integer multiple of the sequence, it is rounded up to the next
                       multiple of sequence. The TP receiver adds up the number of sequences received
                       each time it receives a TP Packet.
 Ce_Seq     32         Congested sequence: indicates the accumulated number of sequences in a TP
                       Packet received with the congestion flag by the TP receiver. The unit is 2 bytes.
                       The data receiver adds up the number of sequences received each time it receives
                       a TP Packet with the congestion flag.




unifiedbus.com                                                                                           165
6 Transport Layer



             Byte0                      Byte1                     Byte2                      Byte3
     7 6 5 4 3 2        1    0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
0                                                  Ack_Seq
4        Reserved      Loc I              C                                     Hint
                                     Figure 6-12 CAQM CETPH format

                                         Table 6-4 CAQM CETPH
 Field           Bit   Description
 Ack_Seq         32    Same as the description of LDCP CETPH.
 Loc             1     Location flag. It indicates the point where congestion occurs. This field is copied
                       from the NTH.CCI field of the received TP Packet.
                       ● 0: Congestion at network intermediate node.
                       ● 1: Congestion at the last-hop UB Switch egress.

 I               1     I (Increase): This field is copied from the Increase field in the network layer
                       header of the received TP Packet. If the network allows the increase of the
                       sending volume, this bit is set to 1. Otherwise, this bit is set to 0.
 C               8     C (Congestion): indicates the number of TP Packets received by the TP receiver
                       that are marked as congestion after the last TPACK is sent back.
 Hint            16    This field is copied from the Hint field in the NTH.CCI bytes of the received TP
                       Packet. When multiple TPACKs are aggregated (one TPACK acknowledges
                       multiple TP Packets), this field indicates the sum of all allowed congestion
                       window increments since the last TPACK is sent back.


A CNP is a separate packet generated by the TP receiver to convey congestion notification information
to the TP sender.

             Byte0                      Byte1                     Byte2                      Byte3
     7 6   5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0

 0 ECN Loc                                              Reserved

 4                                                 Reserved
 8                                                 Reserved
12                                                 Reserved
                                     Figure 6-13 CNP CETPH Format

                                              Table 6-5 CNP CETPH
 Field       Bit       RTP                                                                        CTP
 ECN         2         Congestion level. This field is used when the DCQCN congestion             Same
                       control algorithm is enabled.                                              as RTP
                       Both 0x1 and 0x3 can indicate that congestion occurs.
                       Two levels of congestion, minor (0x1) or severe (0x3), can be




unifiedbus.com                                                                                            166
6 Transport Layer



 Field        Bit         RTP                                                                      CTP
                          optionally supported when a domain is configured to do so.
                          ● 0x0: no congestion.
                          ● 0x1: minor congestion.
                          ● 0x2: Reserved.
                          ● 0x3: severe congestion.

 Loc          1           The point where congestion occurs. This field is optional.               Same
                          ● 0: Congestion at network intermediate node.                            as RTP

                          ● 1: Congestion at the last-hop switch egress.


6.2.3 Selective Acknowledge Extended Transport Header (SAETPH)
SAETPH encodes information of the TP Packet received by the TP receiver and is included in TPSACK
and TPSACK-CC transport layer response packets.

                  Byte0                     Byte1                    Byte2                   Byte3
         7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                          BitMap
  0       Reserved                                               MaxRcvPSN
                            Size
  4                                                     BitMap
8~32                                                      ...
                                          Figure 6-14 SAETPH format

                                                Table 6-6 SAETPH
 Field            Bit                      Description
 BitMapSize       3                        Number of bits in the BitMap carried in the TPSACK or
                                           TPSACK-CC packet.
                                           ● 0x0: 64 bits.
                                           ● 0x1: 128 bits.
                                           ● 0x2: 256 bits.
                                           ● 0x3: 512 bits.
                                           ● 0x4: 1024 bits.
                                           Others: Reserved.
 MaxRcvPSN        24                       Maximum PSN received by the TP receiver so far.
 BitMap           N (number of bits        Each bit represents a PSN, where BitMap[0] corresponds to
                  specified by             RTPH.PSN.
                  BitMapSize)              ● If the bit is 1, the corresponding TP Packet is received.
                                           ● If the bit is 0, the corresponding TP Packet is not received.




unifiedbus.com                                                                                           167
6 Transport Layer



6.3 Transport Layer Mode

6.3.1 Reliable Transport (RTP)
RTP provides end-to-end reliable transmission services to the transaction layer through transport
endpoints (TPEPs). It guarantees that TP Packets are delivered from the TP sender to the TP receiver
without loss, and each packet is passed to the transaction layer exactly once.

RTP ensures reliable transmission by PSNs and packet retransmission mechanisms. For more details,
see Section 6.4. Before transmission, the TP sender and receiver must negotiate and establish the TP
channel and maintain the transmission context. The TP channel setup procedure is outside the scope of
this document. The TP sender assigns a unique PSN to each TP Packet to indicate its order in a single
TP channel. The TP receiver verifies the PSN of each received packet against the expected sequence
number to detect lost, duplicated, or out-of-order packets and sends a response packet back. The
response packet can be a transport acknowledgement (TPACK), transport negative acknowledgement
(TPNAK), or transport selective acknowledgement (TPSACK). The TP sender determines the status of
each sent TP Packet based on the received response. If packet loss is detected, the TP sender
retransmits the affected packets according to the selected retransmission algorithm.

Figure 6-15 shows the reliable transmission service process provided by RTP.

    1.   The TP sender transmits a TP Packet with a PSN associated. The PSN is monotonically
         incremented with each TP Packet. Retransmission carries the same PSN as the first
         transmission of the lost packet.
    2.   The TP receiver checks the PSN of each received TP Packet to detect if the packet is
         duplicated, in-order, out-of-order, or an invalid PSN. It can respond with a TPACK, TPNAK, or
         TPSACK to the TP sender accordingly to inform the delivery status of the TP Packets.
    3.   The TP sender judges if a packet is successfully delivered based on the received response
         (TPACK, TPNAK, or TPSACK). It SHALL retransmit the lost TP Packets indicated by the
         TPNAK or TPSACK.




                            Figure 6-15 Reliable transmission service process




unifiedbus.com                                                                                       168
6 Transport Layer



RTP supports piggybacking of transaction-layer responses in ROI, ROT, and ROL modes (see Section
7.3.1). In transaction layer ROL mode, the transport layer response is able to carry the transaction layer
response TAACK, or transaction layer errors such as RNR and Page Fault. The transaction layer
response type is jointly specified by the RSPST and RSPINFO fields in the RTPH.

RTP provides TP channel-based UBPU multi-port load balancing (see Section 6.5.1) and a congestion
control mechanism (see Section 6.6.1). TP channel can be shared by transaction operations of several
initiator and target pairs in RTP.


6.3.2 Compact Transport (CTP)
CTP relies on the lower layer of the protocol stack to provide reliable transmission services for
transaction layer. This specification describes an embodiment of CTP. CTP does not generate
transport-layer acknowledgements or provide its own end-to-end retransmission mechanism. Instead,
CTP relies on the hop-by-hop retransmission offered by the link layer. In scenarios of UBPU direct
connections or interconnect with high link quality. The packet loss is minimal and at the same time the
need for resource-intensive end-to-end retransmission is removed.CTP provides coarse-grained
congestion management and load balancing methods (see Sections 6.5.2 and 6.6.2).


6.3.3 Unreliable Transport (UTP)
UTP's unreliable transmission service offers connectionless delivery with no guarantees. UTP does not
establish TP channels, does not generate transport layer response packets, and does not support the
retransmission mechanism.


6.4 RTP Reliable Transmission Mechanism

6.4.1 PSN Mechanism
The UB reliable transmission service employs the PSN mechanism to verify lost or duplicated TP
Packets. The PSN is a unique, monotonically increasing number assigned to every TP Packet sent.
Optionally, as in the transaction layer ROL mode, the PSN can be used to enforce transaction ordering
(see Section 7.3.3).

The TP sender assigns sequential PSNs to non-retransmitted TP Packets. Response packets, such as
TPACK, returned by the TP receiver, report the highest PSN of the consecutively received in-order TP
Packets. In responses such as TPNAK, returned by the TP receiver, the PSN indicates the expected
PSN (EPSN). When a TP channel is established, the TP sender and TP receiver negotiate the initial
PSN, which is randomly selected from 0 to 16M-1. Each TP channel maintains its own PSN space.

The RTPH.PSN field in the TP Packet sent by the TP sender carries the PSN maintained by the TP
sender. Only TP Packets are assigned new PSNs, so the transport layer response packet types, such as
TPACK, do not consume PSN. The TP receiver maintains an EPSN, which represents the sequence
number of the next in-order TP Packet it expects to receive. The initial PSN is negotiated. When a TP
Packet is received, the TP receiver determines whether it is in order by comparing the PSN of the TP



unifiedbus.com                                                                                          169
6 Transport Layer



Packet with the current EPSN. If the PSN is equal to EPSN, the packet is considered in order; otherwise,
it is out of order. An in-order packet will increment EPSN by 1 at the TP receiver; otherwise, EPSN
remains unmodified. When receiving an out-of-order TP Packet, the TP receiver determines whether the
TP Packet is a duplicate, out-of-order, or invalid range packet. A duplicate packet carries a PSN of
previously received TP Packets and SHALL be discarded. When a TP receiver is configured to accept
out-of-order packets, an out-of-order PSN range is established, starting from EPSN + 1 to a configurable
ending value. TP Packets with PSNs falling within this out-of-order PSN range are accepted and
processed normally; otherwise, they SHALL be discarded by the TP receiver.

The PSN width is 24 bits, indicating the range of 0 to 16M-1. When the PSN exceeds the 24-bit
representation range, the highest order bit overflows to make the PSN wrap around. The maximum
PSN of the TP Packet sent by the TP sender minus the minimum PSN of the response SHALL be less
than or equal to 8M-1. The following is an example.

     1.   If the minimum PSN waiting for response is 0, then the maximum PSN allowed to be sent is
          8M-1 (8,388,607).

     2.   If the minimum PSN waiting for response is 8M (8,388,608), then the maximum PSN allowed
          to be sent is 16M-1 (16,777,215).

     3.   If the minimum PSN waiting for response is 10M (10,485,760), then the maximum PSN
          allowed to be sent is 18M-1 (18,874,367), exceeding the 24-bit representation range, so the
          highest order bit overflows. Therefore, the maximum PSN allowed to be sent is 2M-1
          (2,097,151).

Figure 6-16 shows the PSN range. [EPSN-8M,EPSN-1] indicates the maximum duplicate packet range.
The size of the out-of-order PSN range can be set to a value in [128, 256, 512, 1024, 2048].




                                               Figure 6-16 PSN range

Example: PSN usage

Transaction operations, including requests and responses, that are segmented and encapsulated into TP Packets
transmitted through a single TP channel with a single set of PSN space on each direction. The transport layer response
packets TPACK, TPNAK, and TPSACK do not consume the PSNs. As shown in Figure 6-17, UBPU A and UBPU B
exchange traffic through a TP channel. UBPU A and UBPU B each maintain a set of PSNs. When UBPU A sends a TP
Packet to UBPU B, the APSN is used as the PSN, which is initialized to 10. Similarly, when UBPU B sends a TP Packet
to UBPU A, the BPSN is used, which is initialized to 0. To highlight the use of PSNs, the interaction between the




unifiedbus.com                                                                                                      170
6 Transport Layer



transaction layer and transport layer is omitted, and the write operation length is assumed to be exactly one TP Packet.
UBPU A sends a TP Packet containing a transaction layer write operation to UBPU B. The PSN in the TP Packet is the
initial value of APSN, that is, 10. Once UBPU B receives the TP Packet, it responds with a TPACK using the same PSN
value of 10. The write operation consists of a single TP Packet. If the TP Packet is successfully received, the transaction
operation is complete. UBPU B processes the transaction operation and sends a TAACK to UBPU A. The transport layer
encapsulates this TAACK into a TP Packet with a PSN set to the initial BPSN value of 0. Similarly, UBPU B sends a TP
Packet carrying the transaction layer write operation to UBPU A.

                                         UBPU A                         UBPU B




                                          Figure 6-17 PSN usage example


6.4.2 Retransmission Mechanism
UB supports two fundamental retransmission algorithms: 1) Go-Back-N retransmission, with or without
fast retransmission, and 2) selective retransmission, with or without fast retransmission, depending on
the triggering conditions. With fast retransmission, the TP sender retransmits packets immediately after
receiving a negative response. With timeout-based retransmission, the TP sender starts retransmission
only upon expiration of a retransmission timeout (RTO). Timeout-based retransmission is enabled by
default, while fast retransmission MAY be enabled as needed. If both are enabled, timeout-based
retransmission serves as a fallback mechanism and is activated in events such as tail packet loss. See
Section 6.4.2.2 for the detailed specification of the Go-Back-N algorithm and Section 6.4.2.3 for the
detailed specification of the selective retransmission algorithm.

The retransmission algorithms can be configured by users. Table 6-7 lists their applicable scenarios. If
routing might lead to packets being received out of order—such as when TP Packets on the same
channel take multiple paths due to per-packet load balancing—fast retransmission is typically disabled
to avoid spurious (or unnecessary) retransmissions.




unifiedbus.com                                                                                                         171
6 Transport Layer



                       Table 6-7 Recommended use scenarios of retransmission algorithms
                                                                        Use Scenario
 Retransmission Algorithm                                                                            Network Packet
                                         Load Balancing Algorithm
                                                                                                     Loss Rate
 Go-Back-N Retransmission                Packets from the same TP channel are                        Very low
 with Fast Retransmission                transmitted over a single network path. Example
                                         scenario: per-flow load balancing.
 Go-Back-N Retransmission                Packets from the same TP channel may be                     Very low
 Without Fast Retransmission             transmitted over multiple network paths. Example
                                         scenario: per-packet load balancing.
 Selective Retransmission                Packets from the same TP channel are                        Low
 with Fast Retransmission                transmitted over a single network path. Example
                                         scenario: per-flow load balancing.
 Selective Retransmission                Packets from the same TP channel may be                     Low
 Without Fast Retransmission             transmitted over multiple network paths. Example
                                         scenario: per-packet load balancing.


6.4.2.1 Retransmission Trigger Conditions

With fast retransmission, the TP sender retransmits TP Packets immediately after receiving a negative
response. With timeout-based retransmission, the TP sender retransmits unacknowledged TP Packets
only when RTO timer expires. This section describes the detailed design of timeout-based retransmission.

Example: method for setting the timeout-based retransmission timer

During a timing cycle, the timer starts upon the first new packet sending and resets if the PSN in the received
TPACK/TPSACK equals or exceeds the smallest unacknowledged PSN from the sender's TP Packets. The timer
deactivates upon successful receipt of all TP Packets within a cycle. In cases where reception is incomplete, the timer
resets at the end of the timeout interval to initiate retransmission.

The UB transport layer supports two timeout modes: static and dynamic. The static timeout interval is fixed after being
configured, and the dynamic timeout interval changes dynamically with the number of consecutive retransmissions.

Example: configuring a static timeout interval

The static timeout interval can be configured when a TP channel is created. The time threshold can be selected from
[512μs,16ms,128ms,4s].

Dynamic timeout intervals employ an exponential backoff mechanism, where each subsequent interval is 2^N times the
prior one. The timeout interval of dynamic timeout-based retransmission is calculated as follows: RTO = Base_time ×
2^(N × Times). Base_time indicates the initial timeout interval, ranging from 4 to 2097152 microseconds. It is
recommended that Base_time be set to be positively correlated with the round-trip time (RTT). N is a user-configurable
timeout interval coefficient. Times counts the timeout-based retransmissions, starting at 0 and increasing by 1 after each
retransmission. The maximum number of timeout-based retransmissions can be set. When this threshold is exceeded
through consecutive timeout-based retransmissions, the path is deemed unreachable. The UB supports reporting error
type CQE with retransmission exceeding the specified limit to the transaction layer.




unifiedbus.com                                                                                                         172
6 Transport Layer



Example: configuring a dynamic timeout interval

If N is set to 3, the maximum number of retransmissions is set to 7, and the first timeout-based retransmission interval is
set to 20 μs, the intervals for the 7 retransmissions are as shown in Table 6-8.

                                     Table 6-8 Dynamic retransmission intervals
            Number of Retransmissions                                         Timeout Interval (μs)
                            1                                                             20
                            2                                                            160
                            3                                                           1280
                            4                                                          10240
                            5                                                          81920
                            6                                                         655360
                            7                                                         5242880


Gradually increasing timeout interval offers these benefits over fixed ones:

       1.    A short initial retransmission interval allows fast retransmission of TP Packets lost through
             tail packet loss. This helps quickly recover occasional packet loss caused by bit errors and
             other non-congestion situations.
       2.    RTT increases together with network congestion. Increasing RTO reduces unnecessary
             retransmission compared to short RTO, and reduces latency to overcome lost tail packets
             compared to long RTO.
       3.    An end-to-end TP channel perceived by the TPEP is one of multiple reachable paths on the
             network. If a path is unreachable due to multi-plane network failure, route convergence may
             be required. When the TPEP repeatedly fails to send a packet upon timeout after multiple
             attempts, it concludes the transmission path is unavailable. If the timeout interval is set to a
             smaller value, the TPEP may detect an unreachable path faster than route delivery, and then
             it mistakenly concludes the path is unavailable.


6.4.2.2 Go-Back-N Retransmission

Go-Back-N retransmission is able to be used together with fast retransmission and timeout-based
retransmission. When Go-Back-N retransmission is used together with fast retransmission at the UB
transport layer, retransmission is triggered by TPNAK. After receiving the TPNAK, the TP sender
retransmits all TP Packets with PSNs greater than the highest acknowledged PSN. After receiving a TP
Packet, the TP receiver determines to which range the packet belongs based on the PSN in the packet
(see Section 6.4.1), and returns TPACK or TPNAK. The TPACK contains the PSN of the highest
sequence number of in-order TP Packets received by the TP receiver. The PSN field in the TPNAK
contains an EPSN value. Upon reception of TPNAK, the TP sender checks if the TP Packet was
received using the response from the TP receiver, and retransmits the TP Packet identified by the PSN
contained in the TPNAK, along with all subsequent transmitted packets following that PSN. When Go-




unifiedbus.com                                                                                                          173
6 Transport Layer



Back-N retransmission is used without fast retransmission at the UB transport layer, retransmission is
triggered by timeout only. After the timeout is triggered, the TP sender retransmits all TP Packets that
are not acknowledged.

The Go-Back-N algorithm is simple to implement but may require retransmission of a large number of
packets, even if only one is lost. It performs best in environments with very-low packet loss. In the per-
packet load balancing scenario, fast retransmission SHALL NOT be enabled with Go-Back-N
retransmission in order to prevent spurious retransmission.

In Go-Back-N retransmission, the response type is specified by the TPOpcode and RSPST fields in the
RTPH. For a response packet that does not contain the congestion control extension header and does
not operate in the transaction layer ROL mode, the TPACK is represented by TPOpcode=0x2 and
RSPST=3'b000, and the TPNAK is represented by TPOpcode=0x2 and RSPST=3'b011. For details
about how to set the fields in the response packet that contains the congestion control extension
header or operate in transaction layer ROL mode, see Section 6.2.1.


6.4.2.2.1 Go-Back-N Retransmission with Fast Retransmission

Generally, if routing does not cause TP Packet reordering—such as when per-flow load balancing is
enabled—Go-Back-N retransmission MAY work well alongside fast retransmission.

After receiving a TP Packet, the TP receiver behaves as follows: (i) If the TP Packet arrives in order, the
TP receiver accepts it, increments the EPSN by 1, and sends back a TPACK with the RTPH.PSN set to
EPSN - 1. (ii) If the TP Packet received by the TP receiver falls into the duplicate range, the receiver
discards the packet without updating its EPSN. The TP receiver returns a TPACK with the PSN set to
EPSN - 1. (iii) If the TP Packet received by the TP receiver falls into the out-of-order range, the TP
receiver discards the packet without updating its EPSN. The TP receiver returns a TPNAK with the PSN
set to EPSN. After sending a TPNAK, no other TPNAK will be sent until a TPACK is sent. (iv) If the TP
Packet is in an invalid range, the TP receiver silently discards the packet.

Upon receiving a TPNAK, the TP sender retransmits all TP Packets starting from the PSN indicated in
the TPNAK.

The following text describes the process of Go-Back-N retransmission used together with fast
retransmission in typical scenarios involving TP Packet loss and response packet loss. TP Packet loss
is classified into three typical cases: initial, non-initial, and tail losses. Response packet loss is classified
into three typical cases: TPACK loss, TPACK tail loss, and TPNAK loss.

Process of retransmitting lost TP Packets

      1.   Initial TP Packet loss
           Figure 6-18 shows the process of the Go-Back-N retransmission used together with fast
           retransmission when a TP Packet is lost for the first time.
           (1) The TP sender sends TP Packets with PSNs m to m+3.
           (2) The TP Packet (PSN=m) arrives at the TP receiver. The TP receiver examines the PSN of
                 the received TP Packet. Because EPSN maintained by the TP receiver is equal to the PSN




unifiedbus.com                                                                                               174
6 Transport Layer



                 of the TP Packet, the TP receiver determines that the TP Packet (PSN=m) is an in-order
                 packet, accepts it, and returns a TPACK (PSN=m). Then, the EPSN is updated to m+1.
           (3) The TP Packet (PSN=m+1) is lost during transmission.
           (4) The TP Packet (PSN=m+2) arrives at the TP receiver. Because the EPSN maintained by
                 the TP receiver is m+1, the TP receiver determines that the TP Packet (PSN=m+2) is an
                 out-of-order packet, discards the packet, and returns a TPNAK (PSN=m+1). PSN m+1
                 identifies the PSN expected by the TP receiver.
           (5) The TP Packet (PSN=m+3) arrives at the TP receiver. Because the EPSN maintained by
                 the TP receiver is m+1, the TP receiver determines that the TP Packet (PSN=m+3) is an
                 out-of-order packet and discards it. Because the TPNAK (PSN=m+1) has been returned,
                 the response packet will not be returned again.
           (6) After receiving the TPNAK (PSN=m+1), the TP sender starts to retransmit all TP
                 Packets since PSN=m+1, that is, TP Packets with PSNs from m+1 to m+3.
           (7) After correctly receiving the TP Packets with PSNs from m+1 to m+3, the TP receiver
                 returns TPACKs with PSNs from m+1 to m+3, and the TPACKs are correctly received by
                 the TP sender.
           Optionally, to reduce overheads of TPACK response, the TP receiver is able to reply with an
           aggregated TPACK after successfully receiving multiple TP Packets.




                       Figure 6-18 Process of the Go-Back-N retransmission with fast
                          retransmission when a TP Packet is lost for the first time

      2.   Non-initial TP Packet loss
           Figure 6-19 shows the process of the Go-Back-N retransmission used together with fast
           retransmission when a TP Packet is lost again.
           (1) Method of initial retransmission of TP Packet (PSN=m+1) is as the initial packet loss
                 process (1)–(6).



unifiedbus.com                                                                                            175
6 Transport Layer



           (2) The TP Packet (PSN=m+1) is lost again.
           (3) The TP receiver receives the retransmitted TP Packets with PSNs m+2 and m+3.
                 Because the EPSN maintained by the TP receiver is m+1, the TP receiver determines
                 that the TP Packets with PSNs m+2 and m+3 are out-of-order packets and discards the
                 packets. However, the TP receiver has replied with the TPNAK with PSN m+1, so it does
                 not generate repeated responses.
           (4) Upon expiration of RTO interval, the TP sender starts to retransmit the TP Packets with
                 PSNs m+1 to m+3.
           (5) After correctly receiving the TP Packets with PSNs from m+1 to m+3, the TP receiver
                 replies with TPACKs with PSNs from m+1 to m+3, and the TPACKs are correctly
                 received by the TP sender.




                         Figure 6-19 Process of Go-Back-N retransmission with fast
                               retransmission when a TP Packet is lost again

      3.   Tail TP Packet loss
           Figure 6-20 shows the process of Go-Back-N retransmission used together with fast
           retransmission when a tail TP Packet is lost.
           (1) The TP sender sends TP Packets with PSNs m to m+3.
           (2) The TP receiver correctly receives TP Packets with PSNs m and m+1. It then sends
                 back TPACKs with PSNs m and m+1, which the TP sender receives correctly.
           (3) TP Packets with PSNs m+2 and m+3 are lost during transmission.



unifiedbus.com                                                                                       176
6 Transport Layer



           (4) After the timeout interval for receiving the TPACKs reaches the RTO, the TP sender
                 starts to retransmit the TP Packets with PSNs m+2 and m+3.
           (5) After correctly receiving the TP Packets with PSNs m+2 and m+3, the TP receiver
                 respectively replies with TPACKs with PSNs m+2 and m+3, which the TP sender
                 receives correctly.




                        Figure 6-20 Process of Go-Back-N retransmission with fast
                               retransmission when a tail TP Packet is lost

Retransmission process when the TPACK/TPNAK is lost

      1.   A TPACK is lost, but the subsequent TPACKs are not lost.
           Figure 6-21 shows the process of Go-Back-N retransmission used together with fast
           retransmission when a TPACK is lost.
           (1) The TP sender sends TP Packets with PSNs m to m+2, and the TP receiver correctly
                 receives the TP Packets.
           (2) The TP receiver replies with TPACKs with PSNs m to m+2. TPACKs with PSNs m and
                 m+2 are correctly received by the TP sender, but TPACK with PSN m+1 is lost.
           (3) The TP sender receives the TPACK (PSN=m+2). Because the TPACK (PSN=m+2) is
                 able to confirm that the TP Packet whose PSN is less than or equal to m+2 is correctly
                 received, the TP sender updates the delivery status of all TP Packets with PSNs that are
                 less than or equal to m+2 as correctly received.




unifiedbus.com                                                                                        177
6 Transport Layer




                        Figure 6-21 Process of Go-Back-N retransmission with fast
                                  retransmission when a TPACK is lost

      2.   Tail TPACK loss
           Figure 6-22 shows the process of Go-Back-N retransmission used together with fast
           retransmission when a tail TPACK is lost.
           (1) The TP sender sends TP Packets with PSNs m to m+2, and the TP receiver correctly
                 receives the TP Packets.
           (2) The TP receiver replies with TPACKs with PSNs m to m+2. TPACKs with PSNs m and
                 m+1 are correctly received by the TP sender, but TPACK with PSN m+2 is lost.
           (3) After the timeout interval for receiving the TPACKs reaches the RTO, the TP sender
                 starts to retransmit the TP Packet (PSN=m+2).
           (4) When the TP Packet (PSN=m+2) reaches the TP receiver, the TP receiver detects that
                 the TP Packet is in the duplicate range, discards the TP Packet, and returns a TPACK
                 (PSN=m+2).
           (5) The TP sender correctly receives the TPACK (PSN=m+2).




unifiedbus.com                                                                                      178
6 Transport Layer




                       Figure 6-22 Process of Go-Back-N retransmission with fast
                                retransmission when a tail TPACK is lost

      3.   TPNAK loss
           Figure 6-23 shows the process of Go-Back-N retransmission used together with fast
           retransmission when a TPNAK is lost.
           (1) The TP sender sends TP Packets with PSNs from m to m+2.
           (2) The TP receiver correctly receives the TP Packet (PSN=m) and replies with a TPACK
                 (PSN=m).
           (3) The TP Packet (PSN=m+1) is lost during transmission. The out-of-order TP Packet
                 (PSN=m+2) is discarded after arriving at the TP receiver, and the TP receiver responds
                 with a TPNAK (PSN=m+1).
           (4) The TPNAK (PSN=m+1) is lost during transmission.
           (5) After the timeout interval for receiving the TPACKs reaches the RTO, the TP sender
                 starts to retransmit TP Packets with PSNs m+1 and m+2.
           (6) The TP receiver correctly receives TP Packets with PSNs m+1 and m+2. It then sends
                 back TPACKs with PSNs m+1 and m+2, which the TP sender receives correctly.




unifiedbus.com                                                                                       179
6 Transport Layer




                     Figure 6-23 Process of Go-Back-N retransmission with fast
                               retransmission when a TPNAK is lost


6.4.2.2.2 Go-Back-N Retransmission Used Without Fast Retransmission

Generally, in scenarios where TP Packets arrive out of order (for example, due to per-packet load
balancing), Go-Back-N retransmission should not be used together with fast retransmission. In this
case, the TP receiver must enable reception of out-of-order packets, for example by maintaining
reception status using BitMap. In this case, the arrival of out-of-order TP Packets at the receiver does
not necessarily imply that any TP Packets were lost. Timeout-based retransmission helps avoid
unnecessary retransmissions in such scenarios.

After receiving a TP Packet, the TP receiver behaves as follows: (i) If the TP Packet arrives in order, the
TP receiver accepts it, updates the BitMap used for out-of-order reception, and increments the locally
maintained EPSN by 1 (EPSN equals the highest PSN of received in-order packets plus one). It then
sends back a TPACK with the RTPH.PSN set to EPSN - 1. (ii) If the TP Packet received by the TP
receiver falls into the duplicate range, the TP receiver discards the TP Packet, and the EPSN remains
unchanged. The TP receiver returns a TPACK with the PSN set to EPSN - 1. (iii) If the TP receiver gets
an out-of-order packet, it checks the reception status information, for example using a local BitMap. If
the BitMap shows the packet has not been received yet, the receiver accepts it and updates the
BitMap. If the BitMap shows the packet was already received, the receiver drops it. The EPSN stays the
same, and no response is sent. (iv) If the TP Packet is in an invalid range, the TP receiver discards the
TP Packet. The EPSN stays the same, and no response is sent.

The TP sender needs to update the transmission status based on the received TPACK and maintain the
maximum PSN (recorded as MaxPSN) contained in the received TPACK. It starts the retransmission
timer after a TP Packet is sent. When the timeout expires, the TP sender retransmits all TP Packets
whose PSN is greater than or equal to MaxPSN+1.




unifiedbus.com                                                                                         180
6 Transport Layer



This section describes the process of Go-Back-N retransmission used without fast retransmission in
typical scenarios when the TP receiver receives out-of-order TP Packets or response packets are lost.
The scenarios where the TP receiver receives TP Packets that are in the out-of-order range are
classified into three typical cases: out-of-order TP Packets detected for the first time (with or without
actual packet loss), non-initial TP Packet loss, and tail loss. Similarly, response packet loss is classified
into two typical cases: TPACK loss and TPACK tail loss.

TP receiver receives out-of-order TP Packets

      1.   Out-of-order TP Packets detected for the first time (no packet loss)
           Figure 6-24 shows the process of Go-Back-N retransmission used without fast
           retransmission when out-of-order TP Packets are detected for the first time (without actual
           packet loss), that is, when the TP receiver receives TP Packets in the out-of-order range.
           (1) The TP sender sends TP Packets with PSNs m to m+3.
           (2) The TP receiver correctly receives the TP Packet (PSN=m), replies with a TPACK
                 (PSN=m), and updates the EPSN to m+1.
           (3) The TP Packet (PSN=m+2) and TP Packet (PSN=m+3) arrive at the TP receiver. But the
                 TP Packet (PSN=m+1) has not arrived. Because the TP receiver is enabled to receive
                 out-of-order packets, the TP receiver correctly receives TP Packets with PSNs m+2 and
                 m+3. Note that the TP receiver does not need to respond with a TPNAK because the
                 retransmission is triggered upon timeout.
           (4) The TP Packet (PSN=m+1) arrives at the TP receiver after the TP Packet (PSN=m+2) and
                 TP Packet (PSN=m+3). The PSN carried in the TP Packet (PSN=m+1) is the same as the
                 EPSN maintained by the TP receiver. So in this case, the TP receiver receives in-order
                 packets and returns a TPACK (PSN=m+3).
           (5) The TP sender receives the TPACK (PSN=m+3). Because the TPACK (PSN=m+3) is able to
                 confirm that the TP Packet whose PSN is less than or equal to m+3 is correctly received, the
                 TP sender updates the delivery status to indicate that all TP Packets with PSNs <= m+3 have
                 been correctly received. The TP sender cancels the RTO timer.




           Figure 6-24 Process of the Go-Back-N retransmission without fast retransmission when out-
                  of-order TP Packets are detected for the first time (without actual packet loss)



unifiedbus.com                                                                                              181
6 Transport Layer



      2.   Out-of-order TP Packets detected for the first time (with actual packet loss)
           Figure 6-25 shows the process of Go-Back-N retransmission used without fast
           retransmission when out-of-order TP Packets are detected for the first time (with actual
           packet loss). Note that this situation is rare when the link quality is high and the packet loss
           rate is low.
           (1) The TP sender sends TP Packets with PSNs m to m+3.
           (2) The TP receiver correctly receives the TP Packet (PSN=m) and replies with a TPACK
                 (PSN=m).
           (3) The TP Packet (PSN=m+1) is lost during transmission.
           (4) The TP Packet (PSN=m+2) and the TP Packet (PSN=m+3) arrive at the TP receiver.
                 Because the TP receiver is enabled to receive out-of-order packets, the TP receiver
                 correctly receives the TP Packet (PSN=m+2) and the TP Packet (PSN=m+3).
           (5) Upon expiration of RTO interval, the TP sender starts to retransmit the TP Packets with
                 PSNs m+1 to m+3.
           (6) The TP receiver correctly receives the TP Packet (PSN=m+1) and replies with a TPACK
                 (PSN=m+3). The TP receiver detects that the TP Packet (PSN=m+2) and the TP Packet
                 (PSN=m+3) are duplicate packets, discards the packets, and replies with TPACK
                 (PSN=m+3).




             Figure 6-25 Process of the Go-Back-N retransmission without fast retransmission
            when out-of-order TP Packets are detected for the first time (with actual packet loss)




unifiedbus.com                                                                                           182
6 Transport Layer



      3.   Non-initial TP Packet loss
           When Go-Back-N retransmission is used without fast retransmission, the retransmission
           process of the non-initial TP Packet loss is similar to the retransmission process when an
           out-of-order TP Packet is detected for the first time (with actual packet loss).
      4.   Tail TP Packet loss
           Using Go-Back-N retransmission with or without fast retransmission results in the same
           process for tail TP Packet loss. In such cases, only a timeout triggers the retransmission.

TPACK loss

Using Go-Back-N retransmission with or without fast retransmission results in the same process for
TPACK loss. In this case, a timeout triggers the retransmission of data packets.


6.4.2.3 Selective Retransmission

With selective retransmission enabled at the UB transport layer, the TP sender retransmits only the
missing TP Packets indicated by the TPSACK. It does not retransmit TP Packets already correctly
received by the TP receiver. Selective retransmission eliminates redundant retransmission compared to
Go-Back-N but is more complex to implement. It requires the TP receiver to accept out-of-order TP
Packets within a specific limit (see Section 6.5.1.4.1). Selective retransmission is beneficial on poor-
quality links where the packet loss rate is high.

When selective retransmission is enabled, the TP receiver maintains a BitMap locally to record the
PSNs of received TP Packets. After receiving a TP Packet, the TP receiver determines the range of the
TP Packet based on the PSN (see Section 6.4.1) and returns a TPACK or TPSACK packet.TPACK and
TPSACK both carry the highest in-order PSN, indicating the accumulated highest PSN of the in-order
packets that a TP receiver has received. In addition, the TPSACK packet carries the SAETPH.BitMap
field, which indicates the reception status of individual TP Packets whose sequence numbers are within
the [RTPH.PSN, RTPH.PSN+SAETPH.BitMapSize-1] range and SAETPH.MaxRcvPSN indicates the
highest PSN received by the TP receiver irrespective of packet order. The TP sender checks if the TP
Packet was delivered using the response from the TP receiver and retransmits the TP Packet that is not
acknowledged according to the BitMap field in the TPSACK.

Upon receiving a TP Packet, the TP receiver behaves as follows: (i) If the TP Packet arrives in order,
the TP receiver processes it as usual. It updates the EPSN to the PSN of the received packet plus 1.
When no out-of-order packets exist in the BitMap, the receiver sends a TPACK with the PSN in the
RTPH.PSN field set to EPSN - 1; otherwise, the receiver sends a TPSACK with the PSN in the
RTPH.PSN field matching BitMap[0]. (ii) If the TP Packet received by the TP receiver falls within the
duplicate range, the TP receiver discards the TP Packet, and EPSN remains unchanged. Similarly, the
TP receiver returns a TPACK/TPSACK, depending on whether an out-of-order packet exists in the
reception status of the TP receiver. (iii) If the TP Packet received by the TP receiver falls within the out-
of-order range, the EPSN remains unchanged. The TP receiver returns a TPSACK. (iv) If the TP Packet
is in an invalid range, the TP receiver discards the TP Packet. The EPSN stays the same, and no
response is sent.




unifiedbus.com                                                                                             183
6 Transport Layer



If the TP sender receives a TPSACK where MaxRcvPSN is less than RTPH.PSN plus
SAETPH.BitMapSize (the total bits in the BitMap), it resends missing TP Packets between
RTPH.PSN+1 and MaxRcvPSN. If not, it resends missing TP Packets between RTPH.PSN+1 and
RTPH.PSN+BitMapSize. The foregoing design considers a case in which MaxRcvPSN may be greater
than or equal to a maximum PSN that can be represented by the BitMap of the TPSACK packet. For
example, if the TP receiver receives an out-of-order packet but cannot record it, it discards the out-of-
order packet, but updates MaxRcvPSN with the packet's PSN. MaxRcvPSN monotonically increases.

Selective retransmission MAY be used together with fast or timeout-based retransmission. With fast
retransmission, the TP sender updates the TP Packet reception status and begins retransmitting right
after getting a TPSACK. Without fast retransmission, the TP sender updates the TP Packet reception
status on receiving a TPSACK but waits for an RTO to expire before initiating retransmission.

The type of the response packet sent by the TP receiver is specified by the TPOpcode and RSPST
fields in the RTPH. For a response packet that does not contain the congestion control extension
header and the transaction layer is not operating in ROL mode, the TPACK is represented by
TPOpcode=0x2 and RSPST=3'b000, and the TPSACK is represented by TPOpcode=0x5. The
TPSACK requires the SAETPH header to include a BitMap field indicating a TP Packet reception status
and a MaxRcvPSN field identifying a maximum PSN received by the TP receiver. The SAETPH packet
header SHALL meet the requirements in Section 6.2.3.


6.4.2.3.1 Selective Retransmission with Fast Retransmission

In general, when the interconnect does not introduce TP Packet reordering, such as per-flow load
balancing, selective retransmission MAY operate effectively with fast retransmission.

This section describes the operation of selective retransmission with fast retransmission in typical
scenarios involving TP Packet loss or transport response packet loss. TP Packet loss is classified as:
initial loss, non-initial loss, and tail loss. Non-initial loss is further categorized based on whether the
MarkPSN mechanism is enabled. Transport response packet loss includes TPACK/TPSACK loss and
tail TPACK/TPSACK loss.

MarkPSN mechanism

Without the MarkPSN method, non-initial TP Packet losses are recovered only after a timeout, potentially
causing redundant retransmissions. Because the timeout interval is difficult to set (see Section 6.4.2.1),
the UB protocol introduces the MarkPSN method, which, when per-flow load balancing is enabled,
improves retransmission efficiency by allowing prompt detection and recovery of non-initial losses.

The MarkPSN mechanism categorizes data transfer into two stages: transmitting new packets and
retransmitting lost ones. During the new packet transmission stage, only new TP Packets are sent, and
any detected lost TP Packet is recorded as candidates for retransmission. In the lost packet
retransmission stage, only the lost TP Packets recorded in the previous stage are retransmitted, and no
new TP Packets are sent. MarkPSN represents the PSN of the first new TP Packet transmitted
following the previous retransmission stage. Initially, it is set to the PSN of the first TP Packet and
maintained per each TP channel. The initial value is the PSN of the first TP Packet. During the new




unifiedbus.com                                                                                                184
6 Transport Layer



packet sending phase, if the TP sender receives a TPSACK notifying that packets with sequence
numbers at or above MarkPSN were received, it means those packets either reached the TP receiver or
were lost. The TP sender switches from the new packet sending phase to the lost packet
retransmission phase. If all lost TP Packets are successfully retransmitted, the TP sender switches back
to the new packet sending phase and sets MarkPSN to the sequence number of the first new TP
Packet transmitted.

LastFirstRtx is a per TP channel variable that records the PSN of the first packet in the most recent
retransmission burst, and is used to distinguish initial from non-initial losses by the TP sender. Among
the TP Packets that are not received and indicated in the TPSACK response, a TP Packet whose PSN
is greater than LastFirstRtx is identified as an initial loss and promptly added to the retransmission
queue. Other missing TP Packets, having undergone prior retransmissions, might still be in flight. These
are confirmed as subsequent losses and queued for retransmission only when the TPSACK response
notifies that their PSN meets or exceeds MarkPSN, triggering a switch from sending new packets to
retransmitting lost ones and the next cycle of retransmissions.

Note that the MarkPSN mechanism does not take effect in the following two cases, where the
retransmission is triggered by a timeout:

    1.     No new TP Packet can be sent after the retransmission is complete.
    2.     The tail TP Packet is lost.

Process of retransmitting lost TP Packets

      1.    Initial TP Packet loss
            When the TP sender receives a TPSACK response indicating that the TP Packet is lost for
            the first time, retransmission is triggered. To avoid repeated retransmissions, the TP sender
            maintains the HighRtxPSN and records the maximum PSN of retransmitted TP Packets.
            When a new TPSACK is received, the retransmission starts from HighRtxPSN.
            Figure 6-26 shows the process of selective retransmission used together with fast
            retransmission when a TP Packet is lost for the first time.
            (1) The TP sender sends TP Packets with PSNs m to m+3.
            (2) The TP Packet (PSN=m) arrives at the TP receiver. Because EPSN maintained by the
                 TP receiver is the same as the PSN of the TP Packet, the TP receiver determines that
                 the TP Packet (PSN=m) is an in-order packet, receives it, and returns a TPACK
                 (PSN=m). Then, the EPSN is updated to m+1.
            (3) The TP Packet (PSN=m+1) is lost during transmission.
            (4) The TP Packet (PSN=m+2) arrives at the TP receiver. Because the EPSN maintained by
                 the TP receiver is m+1, the TP receiver determines that the TP Packet (PSN=m+2) is an
                 out-of-order packet, accepts the packet, updates the maintained BitMap, and returns a
                 TPSACK (PSN=m, [1,0,1]), where PSN m identifies the largest PSN sequentially
                 received by the TP receiver. BitMap[1,0,1] indicates that the TP Packet (PSN=m+1) is
                 not correctly received, while the TP Packet (PSN=m) and TP Packet (PSN=m+2) are
                 correctly received. This section simplifies explanations by using TPSACK(PSN, bitMap)




unifiedbus.com                                                                                           185
6 Transport Layer



                 as a logical representation for the data contained in RTPH.PSN and Bitmap within the
                 TPSACK.
           (5) The TP Packet (PSN=m+3) arrives at the TP receiver. Similarly, the TP receiver replies
                 with a TPSACK (PSN=m,[1,0,1,1]), indicating that all TP Packets whose PSNs are less
                 than or equal to m+3 except PSN=m+1 are correctly received.
           (6) After receiving the TPSACK (PSN=m, [1,0,1]), the TP sender retransmits only the TP
                 Packet (PSN=m+1) and records HighRtxPSN=m+1.
           (7) The TP sender receives the TPSACK (PSN=m,[1,0,1,1]), indicating that the TP Packet
                 (PSN=m+1) is not received. However, the HighRtxPSN maintained by the TP sender is
                 m+1, indicating that the TP Packet (PSN=m+1) has been retransmitted. So, the TP
                 sender does not retransmit it repeatedly.
           (8) After correctly receiving the TP Packet (PSN=m+1), the TP receiver replies with the
                 TPACK (PSN=m+3), which is correctly received by the TP sender.




           Figure 6-26 Process of the selective retransmission with fast retransmission when a TP
                                       Packet is lost for the first time

           In addition, to reduce the overhead of TPSACK replies, the TP receiver is able to support
           aggregated TPSACK.
      2.   Non-initial TP Packet loss (without using the MarkPSN mechanism)
           Figure 6-27 shows the process of selective retransmission used together with fast retransmission
           when the retransmitted TP Packet is lost and the MarkPSN mechanism is not used.
           (1) The method for initiating retransmission after the TP Packet (PSN=m+1) is lost for the
                 first time is the same as for the initial packet loss process (1)–(5).




unifiedbus.com                                                                                         186
6 Transport Layer



           (2) The TP sender retransmits the TP Packet (PSN=m+1) and transmits the new TP Packet
                 (PSN=m+4).
           (3) The TP Packet (PSN=m+1) is lost again during transmission.
           (4) The TP receiver accepts the TP Packet (PSN=m+4) and replies with a TPSACK
                 (PSN=m, [1,0,1,1,1]).
           (5) The TP sender receives the TPSACK (PSN=m, [1,0,1,1,1]). Because the TP sender
                 cannot determine whether the TPSACK is sent before the retransmitted TP Packet
                 (PSN=m+1) arrives, the TP sender does not retransmit the TP Packet (PSN=m+1) again.
           (6) After the timeout interval for receiving the TPACK reaches the RTO, the TP sender
                 retransmits the TP Packet (PSN=m+1).
           (7) After correctly receiving the TP Packet (PSN=m+1), the TP receiver replies with the
                 TPACK (PSN=m+4), which is correctly received by the TP sender.




       Figure 6-27 Process of the selective retransmission with fast retransmission when the TP Packet
                           is lost again (without using the MarkPSN mechanism)

      3.   Non-initial TP Packet loss (using the MarkPSN mechanism)
           Figure 6-28 shows the process of selective retransmission used together with fast
           retransmission when the TP Packet is lost again and the MarkPSN mechanism is used.
           (1) Logic for initiating retransmission after the TP Packet (PSN=m+1) is lost for the first time
                 is the same as the initial packet loss process (1)–(5).




unifiedbus.com                                                                                           187
6 Transport Layer



           (2) The TP sender retransmits the TP Packet (PSN=m+1) and transmits the new TP Packet
                 (PSN=m+4). Because the TP Packet (PSN=m+4) is the first TP Packet sent after the
                 retransmission of the TP Packet, the TP sender needs to record MarkPSN=m+4.
           (3) The TP Packet (PSN=m+1) is lost again during transmission.
           (4) The TP receiver receives the TP Packet (PSN=m+4) and replies with a TPSACK
                 (PSN=m, [1,0,1,1,1]).
           (5) The TP sender receives the TPSACK (PSN=m,[1,0,1,1,1]), indicating that all TP Packets
                 whose PSN is less than or equal to m+4 except PSN=m+1 are received. In this case,
                 the TP sender records MarkPSN=m+4 and the TP Packet (PSN=m+4) is correctly
                 received. Therefore, the TP Packet (PSN=m+1) can be retransmitted.
           (6) After correctly receiving the TP Packet (PSN=m+1), the TP receiver replies with the
                 TPACK (PSN=m+4), which is correctly received by the TP sender.




    Figure 6-28 Process of the selective retransmission with fast retransmission when the TP Packet
                             is lost again (using the MarkPSN mechanism)

      4.   Tail TP Packet loss
           Figure 6-29 shows the process of selective retransmission used together with fast
           retransmission when a tail TP Packet is lost.
           (1) The TP sender sends TP Packets with PSNs m to m+4.
           (2) The TP Packet (PSN=m+1) and TP Packet (PSN=m+4) are lost during transmission.




unifiedbus.com                                                                                        188
6 Transport Layer



           (3) Similar to the process in the initial TP Packet loss scenario, after receiving the TPSACK
                 (PSN=m, [1,0,1]), the TP sender starts to retransmit the TP Packet (PSN=m+1), which
                 the TP receiver then successfully receives.
           (4) Because the TP receiver cannot detect the loss of the tail packet, the time for the TP
                 sender to wait for the TPACK reaches the RTO. As a result, timeout-based
                 retransmission is triggered and the TP Packet (PSN=m+4) is retransmitted.




                       Figure 6-29 Process of the selective retransmission with fast
                              retransmission when the tail TP Packet is lost

Retransmission process when the TPACK/TPSACK is lost

      1.   TPACK loss
           Using selective retransmission with fast retransmission operates similarly to using Go-Back-
           N retransmission with fast retransmission when handling TPACK loss.
      2.   Tail TPACK loss
           Using selective retransmission with fast retransmission operates similarly to using Go-Back-
           N retransmission with fast retransmission when handling tail TPACK loss.
      3.   TPSACK loss
           Figure 6-30 shows the process of selective retransmission used together with fast
           retransmission when a TPSACK is lost.
           (1) The TP sender sends TP Packets with PSNs m to m+3.
           (2) The TP Packet (PSN=m+1) is lost during transmission.




unifiedbus.com                                                                                          189
6 Transport Layer



           (3) Upon receipt of the TP Packet (PSN=m+2), the TP receiver replies with a TPSACK
                 (PSN=m, [1,0,1]). Similarly, upon receipt of the TP Packet (PSN=m+3), the TP receiver
                 replies with a TPSACK (PSN=m, [1,0,1,1]).
           (4) The TPSACK (PSN=m, [1,0,1]) is lost during transmission.
           (5) The TP sender receives the TPSACK (PSN=m,[1,0,1,1]), indicating that all TP Packets
                 whose PSN is less than or equal to m+3 except PSN=m+1 are received. Then, the TP
                 sender retransmits the TP Packet (PSN=m+1).
           (6) After correctly receiving the TP Packet (PSN=m+1), the TP receiver replies with the
                 TPACK (PSN=m+3), which is correctly received by the TP sender.




                        Figure 6-30 Process of selective retransmission with fast
                               retransmission when the TPSACK is lost

      4.   Tail TPSACK loss
           Using selective retransmission with fast retransmission to handle tail TPSACK loss operates
           similarly to using Go-Back-N retransmission with fast retransmission to handle TPACK loss.
           In such cases, only a timeout triggers the retransmission.


6.4.2.3.2 Selective Retransmission Used Without Fast Retransmission

In general, when TP Packets can arrive out of order—for example, with per-packet load balancing—
selective retransmission is not used with fast retransmission, because reordering may cause spurious
retransmissions. In such scenarios, the TP receiver must enable out-of-order reception to properly
handle reordered packets. In this case, out-of-order arrival of TP Packets at the TP receiver does not




unifiedbus.com                                                                                       190
6 Transport Layer



necessarily imply that any TP Packets have been lost. The TP receiver MAY be configured to send
TPSACK packets only after a configurable value of out-of-order TP Packets has been received. This
reduces unnecessary TPSACK transmissions when multiple out-of-order packets arrive consecutively.

This section describes the process of selective retransmission used without fast retransmission in
typical scenarios when the TP receiver receives out-of-order TP Packets and response packets are lost.
The scenarios where the TP receiver receives TP Packets that are in the out-of-order range are
classified into three typical cases: out-of-order TP Packets detected for the first time (with or without
actual packet loss), non-initial TP Packet loss, and tail loss.

TP receiver receives out-of-order TP Packets

      1.   Out-of-order TP Packets detected for the first time (without actual packet loss)
           Figure 6-31 shows the selective retransmission process used without fast retransmission
           when out-of-order TP Packets are detected for the first time (without actual packet loss), that
           is, when the TP receiver receives TP Packets in the out-of-order range.
           (1) The TP sender sends TP Packets with PSNs m to m+3.

           (2) The TP Packet (PSN=m+1) arrives at the TP receiver later than the TP Packet
                 (PSN=m+2) and TP Packet (PSN=m+3).

           (3) After receiving the TP Packet (PSN=m+2) and TP Packet (PSN=m+3), the TP receiver
                 responds with a TPSACK (PSN=m, [1,0,1]) and a TPSACK (PSN=m, [1,0,1,1]),
                 respectively.

           (4) After receiving the TPSACK (PSN=m, [1,0,1]) and TPSACK (PSN=m, [1,0,1,1]), the TP
                 sender confirms that all TP Packets whose PSNs are less than or equal to m+3 except
                 PSN=m+1 are correctly received.

           (5) After receiving the TP Packet (PSN=m+1), the TP receiver responds with a TPACK
                 (PSN=m+3).

           (6) The TP sender receives the TPACK (PSN=m+3). Because the TPACK (PSN=m+3) is
                 able to confirm that the TP Packet whose PSN is less than or equal to m+3 is correctly
                 received, the TP sender updates the delivery status of all TP Packets with PSNs that are
                 less than or equal to m+3 as correctly received. The TP sender cancels the timeout-
                 based retransmission timer.




unifiedbus.com                                                                                              191
6 Transport Layer




       Figure 6-31 Process of the selective retransmission without fast retransmission when a TP
                      Packet is lost for the first time (without actual packet loss)

      2.   Initial TP Packet loss (with actual packet loss)
           Figure 6-32 shows the selective retransmission process used without fast retransmission
           when out-of-order TP Packets are detected for the first time (with actual packet loss), that is,
           when the TP receiver receives TP Packets in the out-of-order range.
           (1) The TP sender sends TP Packets with PSNs m to m+3.
           (2) The TP Packet (PSN=m+1) is lost during transmission.
           (3) After receiving the TP Packet (PSN=m+2) and TP Packet (PSN=m+3), the TP receiver
                 responds with a TPSACK (PSN=m, [1,0,1]) and a TPSACK (PSN=m, [1,0,1,1]),
                 respectively.
           (4) After the timeout interval for receiving the TPACK reaches the RTO, the TP sender
                 retransmits the TP Packet (PSN=m+1).
           (5) After correctly receiving the TP Packet (PSN=m+1), the TP receiver replies with the
                 TPACK (PSN=m+3), which is correctly received by the TP sender.




unifiedbus.com                                                                                          192
6 Transport Layer




           Figure 6-32 Process of the selective retransmission without fast retransmission when a
                         TP Packet is lost for the first time (with actual packet loss)

      3.   Non-initial TP Packet loss
           Using selective retransmission with or without fast retransmission results in the same
           process for non-initial TP Packet loss.
      4.   Tail TP Packet loss
           Using selective retransmission with or without fast retransmission results in the same
           process for tail TP Packet loss.

TPACK/TPSACK loss

Using selective retransmission without fast retransmission follows a similar process to the selective
retransmission with fast retransmission. In this case, a timeout triggers the retransmission of data packets.


6.5 Multipath Load Balancing

6.5.1 RTP Multipath Load Balancing
RTP supports multipath load balancing. To fully utilize the bandwidth of UBPUs and UB switches,
multiple TP channels can be established and/or per-packet load balancing can be enabled for traffic
multipathing between UBPU pairs. Per-packet load balancing can be achieved in two ways: (i) changing
fields such as Srcport and LBF in the packet header at the UB transport layer to hint packet paths on
the UB Switch, or (ii) enabling per-packet load balancing directly on the UB Switch. For more
information, refer to Section 5.3.2 This section describes two mechanisms to support load balancing,




unifiedbus.com                                                                                           193
6 Transport Layer



where multiple TP channels between a pair of UBPUs are established, or controlling the per-packet
load balancing by the transport layer.

In per-packet load balancing mode, the bandwidth, latency, and degree of congestion of each path may
be different. As a result, TP Packets transmitted through the same TP channel may arrive at the TP
receiver out of order. The UB transport layer supports out-of-order reception of TP Packets and allows
the retransmission algorithm to be configured to avoid or reduce spurious retransmissions.


6.5.1.1 Transport Channel Group (TPG) Mechanism

A TPG is a transport channel group that the UB transport layer's reliable transmission service provides
for the transaction layer. It is one way to realize load balancing over multiple TP channels in RTP
transport mode. A TPG consists of multiple TP channels and manages their collective operation,
including load distribution and resource coordination. A TPG distributes TP Packets from different
transactions across its member TP channels using load-balancing policies, such as round-robin or
congestion-aware selection. A TPG sends the packets from a single transaction operation to the same
TP channel. TP channels in a TPG can be bound to the same port or different ports. A TP channel can
be bound to only one TPG.

Example: interaction between the UB TPG and transaction layer

Figure 6-33 shows how TPGs are used. In the figure, each pair of UBPUs maintains a TPG, which contains three TP
channels. Each TP channel connects a pair of TPEPs at two ends. When data is transmitted between UBPUs, the
transaction layer delivers a transaction operation to the transport layer. The TPG distributes the transaction operation to
the TP channels bound to the TPG.




                          Figure 6-33 Interaction between the TPG and transaction layer




unifiedbus.com                                                                                                          194
6 Transport Layer



6.5.1.2 Load Balancing Based on TP Channels

A UBPU may contain multiple ports, enabling multiple paths between a pair of UBPUs. The transport layer
supports the creation of multiple TP channels between a pair of UBPUs to fully utilize the bandwidth of the
UBPUs and UB Switches. Managing TP channels via TPG or selecting them at the transaction layer
enables scheduling diverse transaction operations for transmission across multiple TP channels.

Example: TPG multipathing

UB is able to create several TP channels for network multipathing using per-flow load balancing. Table 6-9 describes the
example of creating multiple TP channels by the TP sender and managing them by the TPG when per-flow load
balancing is used. IP addressing is applied and TP channels can be distinguished by UDP port number (when CNA
addressing is applied, different TP channels can be identified by specifying different LBF fields). The UBPU sender
creates a TPG consisting of four TP channels (TP channels 1 to 4) for a UBPU receiver by specifying different UDP
source ports. TP channels 1 and 2 use the same source physical port 1, and TP channels 3 and 4 use the same source
physical port 2.

                                                 Table 6-9 TPG example
                    TP Channel 1 (destination, source physical port 1, UDP source port 1...)

                    TP Channel 2 (destination, source physical port 1, UDP source port 2...)
       TPG
                    TP Channel 3 (destination, source physical port 2, UDP source port 3...)

                    TP Channel 4 (destination, source physical port 2, UDP source port 4...)



The TPG schedules its managed TP channels for TP Packet transmission using customizable modes, such as queue-depth-
based. If the TPG schedules TP channel 1, the source port field of the TP Packets is set to source port 1. The same rule
applies to other TP channels. By managing several TP channels, the TPG ensures balanced, efficient utilization of all
available UBPU physical port bandwidths. When the UB Switch selects a route, the traffic sent from one TP channel passes
through the same route because the traffic has the same tuple used for route selection, including the source port field.
Packets from the four TP channels have unique source ports, allowing them to take different routes and maximize network
bandwidth usage.


6.5.1.3 Per-Packet Load Balancing Controlled by RTP

Packets sent from a TP channel are forwarded on the network. If the transaction operation at the
transaction layer supports per-packet load balancing, the UB transport layer is able to set different load
balance factor (LBF) values for each packet (see Section 5.2). This directs different TP Packets from a
TP channel through different network paths.

Specifically, the TP sender can set different UDP source ports (in IP/UDP packet format) or LBF fields
(in CNA-based packet format) for TP Packets to proactively control per-packet load balancing.




unifiedbus.com                                                                                                             195
6 Transport Layer



6.5.1.4 Per-Packet Load Balancing Adaptation

6.5.1.4.1 Out-of-Order Reception Adapted to Per-Packet Load Balancing

Per-packet load balancing may cause TP Packet disorder. UB supports out-of-order reception. The out-
of-order degree can be configured based on the TP channel. The out-of-order degree can be set to 128,
256, 512, 1024, or 2048 TP Packets. The UB can limit the number of in-transit TP Packets on a single
TP channel by setting the maximum send window of the TP sender, and control the out-of-order range
of the TP channel within an acceptable limit. If necessary, the UB multi-TP channel capability can be
used to ensure service bandwidth.


6.5.1.4.2 Retransmission Mechanism Adapted to Per-Packet Load Balancing

The specification of the retransmission mechanism (Section 6.4.2) describes the fast retransmission
and timeout-based retransmission supported by the UB protocol. When per-packet load balancing is
enabled, the TP sender must be configured to use timeout-based retransmission only since out-of-order
TP Packets may cause unnecessary retransmissions in case of fast retransmission. Also, the TP
receiver must be configured to trigger TPSACKs based on a threshold of accumulated out-of-order
packets, reducing the number of response packets generated.


6.5.2 CTP Multipath Load Balancing

6.5.2.1 Entity-based Load Balancing

When multiple physical ports are bound as an Entity, CTP can be used to provide Entity-based load
balancing without the overhead of TP channel or TP group maintenance. It is a flexible and lightweight
load balancing mechanism to distribute traffic to multiple ports via a single Entity by CTP sender. When
flow-based load balancing is used, the CTP sender can specify the same LBF field in a CNA-based
packet network header for packets from a single flow to implicitly select a member port for sending that
flow. LBF value practically determines which member port of the Entity is selected for outgoing packets.
When packet-based load balancing is used, the CTP sender can either vary the LBF field for each
CNA-based packet header or directly select a port in a round-robin (RR) way or based on port load.


6.5.2.2 CTP-based Per-packet Load Balancing

Similar to RTP, per-packet load balancing is able to work in two ways: (i) changing fields such as LBF in
the packet header at the UB transport layer to hint packet paths on the UB Switch, and/or (ii) enabling
per-packet load balancing directly on the UB Switch. For more information, refer to Section 5.3.2.




unifiedbus.com                                                                                          196
6 Transport Layer



6.6 Congestion Control Mechanism

6.6.1 RTP Congestion Control Mechanism
The UB transport layer implements congestion control by regulating the TP sender's sending window or
rate to avoid or mitigate network congestion. The UB provides several congestion control algorithms
and also allows customized congestion control algorithms. Congestion control algorithms to be used
are negotiated and determined when a TP channel is established (This document does not detail how
to establish a TP channel). At the transport layer, four types of packets can be used to carry congestion
signals to the TP sender: TPACK-CC, TPNAK-CC, TPSACK-CC, and CNP. The packet type is specified
by TPOpcode field. The detailed congestion control information is carried inside the Congestion
Extended Transport Header (CETPH) in the packet. Different congestion control algorithms have
different CETPH structures. The CETPH header must meet the requirements in Section 6.2.2.

The TP sender can control the data sending based on the sending window or sending rate. The UB
transport layer supports low delay control protocol (LDCP), which is window-based congestion control.
It also supports the CNP functionality, which can be used to implement DCQCN. It also supports the
confined active queue management (CAQM) algorithm. In addition to the congestion control algorithms
supported by the UB, the UB also supports custom congestion control algorithms.


6.6.1.1 Window-Based Congestion Control

Congestion control manages network congestion by adjusting the sending window, referred to as the
congestion window (cw). The cw unit is negotiated upon TP channel establishment and defaults to 1
byte. The value of cw varies based on network congestion.


6.6.1.1.1 Sender Status

The TP sender needs to maintain the congestion control (CC) context per TP channel to control the
congestion window. That is, each TP channel has an independent CC context. Table 6-10 lists the
variables related to congestion control in the CC context. The data size in the table includes the
transport layer packet header, transport layer payload, and ICRC. The unit of the data size is the same
as that of the congestion window.

                    Table 6-10 Variables related to congestion control in the CC context
 Variable             Full Name              Description
 cw                   congestion window      Window used to control the inflight TP Packet of the TP
                                             sender
 inflight             inflight data size     Amount of data that has been sent by TP sender and is
                                             assumed to still be in the network
 data_size_sent       data size sent         Amount of data that has been injected by TP sender into
                                             the network so far
 data_size_recvd      data size received     Amount of data that has been received by TP receiver so far
 aval_win             available window       Amount of data that is allowed to be sent by TP sender




unifiedbus.com                                                                                         197
6 Transport Layer



6.6.1.1.2 Processing Logic on the Sender

Before sending data, the TP sender needs to check whether the available window (aval_win) is sufficient.
aval_win is the amount of more data that the TP sender can inject into the network at the moment. A TP
Packet can be sent only when its data size is no more than aval_win. aval_win is calculated by
subtracting the flight traffic (inflight) from the congestion window (cw), that is, aval_win = cw - inflight.

The TP sender adjusts the cw value based on the network congestion status. Generally, the TP sender
decreases the cw when detecting congestion, and increases the cw when detecting that congestion is
relieved. The TP sender detects the congestion status based on the congestion information carried in the
CETPH of the TPACK-CC/TPNAK-CC/TPSACK-CC. For example, when LDCP is enabled for TP, the TP
sender obtains the number of marked TP Packets through CETPH.Ce_Seq and reduces the cw value.

The TP sender needs to keep track of the inflight traffic, which refers to the amount of data that the TP
sender has sent to the network but has not yet been acknowledged. The inflight is updated when the TP
sender sends the TP Packet and when the TP sender receives the TPACK-CC/TPNAK-CC/TPSACK-CC.

To calculate the inflight, the TP sender needs to maintain the data_size_sent variable, which is
initialized to 0. Each time a TP Packet is sent, the value of this variable increases by the corresponding
data volume. The TP sender and TP receiver each maintain data_size_recvd to record how much data
the TP receiver has acknowledged receiving. When the TP receiver generates a TPACK-CC,
data_size_recvd is returned through the Ack_seq field of the CETPH and is used to update
data_size_recvd maintained by the TP sender. The inflight maintained by the TP sender is calculated
by subtracting data_size_recvd from data_size_sent.

The UB supports two retransmission algorithms: selective retransmission and Go-Back-N. The way the
inflight variable updates depends on which algorithm is used.

When the TP sender initiates Go-Back-N retransmission, data_size_sent is reset to CETPH.Ack_seq
in the TPNAK-CC. In this case, inflight is set to 0, that is, all inflight traffic is discarded during
retransmission.

When the TP sender initiates selective retransmission, the size of the TP Packet to be retransmitted
indicated by the TPSACK-CC needs to be subtracted from data_size_sent for inflight update.

In particular, when the TP sender starts timeout-based retransmission, it directly resets inflight to 0.
When the next TPACK-CC/TPNAK-CC/TPSACK-CC is returned, inflight is calculated according to the
preceding logic.


6.6.1.1.3 Status and Processing Logic on the Switch

UB Switch is responsible for congestion detection and marking of congested TP Packets. The specific
mechanism SHALL comply with the requirements in Section 5.3.5 at the network layer.


6.6.1.1.4 Receiver Status

The TP receiver maintains the data_size_recvd variable, which is initialized to 0. This value is
increased by the size of each successfully received TP Packet through PSN verification.




unifiedbus.com                                                                                                  198
6 Transport Layer



6.6.1.1.5 Processing Logic on the Receiver

When the TP receiver correctly receives a TP Packet and no retransmission is required, it generates a
TPACK-CC and returns the current data_size_recvd value in the CETPH.Ack_seq field.

With Go-Back-N retransmission, if the TP receiver receives out-of-order TP Packets, data_size_recvd
remains unchanged. The TP receiver generates a TPNAK-CC and sends data_size_recvd back to the
TP sender using the CETPH.Ack_seq field in the TPNAK-CC.

With selective retransmission, if the TP receiver receives out-of-order TP Packets that are within the
out-of-order range, the TP receiver receives the TP Packets normally, increments data_size_recvd by
the size of the TP Packets, generates a TPSACK-CC, and sends data_size_recvd back to the TP
sender using the CETPH.Ack_seq field in the TPSACK-CC.

In addition to the basic Ack_seq field, the CETPH in TPACK-CC/TPNAK-CC/TPSACK-CC also carries
other congestion information when different congestion control algorithms are in use. The CETPH
format SHALL comply with the requirements in Section 6.2.2.


6.6.1.2 Rate-based Congestion Control

Rate-based congestion control differs from window-based methods in the following ways:

      1.   The TP sender directly adjusts its packet transmission rate according to the network
           congestion information received in the response packets. The TP sender does not keep a
           sending window, and therefore cannot accurately control the number of TP Packets in flight.
      2.   At TP sender, variables inflight and aval_win are not required since there is no sending
           window. Therefore, response packets do not need to carry Ack_seq value, and the TP
           sender's CC context does not need to maintain variables related to the number of the sent and
           received sequences. The resource usage is relatively low.


6.6.1.3 Congestion Control Based on Active Queue Management of the Switch

UB MAY support CAQM for congestion control. CAQM requires the collaboration from both the TPEP
and UB Switch. The TP sender sends TP Packets with a window increase request. Each UB Switch on
the network path determines whether to approve the window increase request based on its available
resources. The decision is sent to the TP receiver with TP Packets. The TP receiver sends the decision
back to the TP sender via TPACK-CC, TPNAK-CC, or TPSACK-CC. The TP sender then adjusts its
window accordingly. CAQM can be used with window-based or rate-based congestion control. This
section describes the window-based CAQM.


6.6.1.3.1 CAQM Field

The TP sender sends a TP Packet carrying the "window increase request" using three fields: a 1-bit
congestion flag (C bit), a 1-bit increase request indicator (I bit), and an 8-bit Hint field. The congestion
flag (C bit) indicates whether congestion is experienced by the packet at any intermediate switch. The
increase request indication (I bit) indicates whether the Hint field is valid. When the value of the I bit is
1, the Hint field carries the congestion window increase amount requested by the TP sender (see



unifiedbus.com                                                                                             199
6 Transport Layer



Section 5.3.5.3). The three fields are carried in the network layer CCI field in a packet. The UB Switch
implements the CAQM algorithm based on the information carried in the three fields. The result of the
algorithm is represented by the C bit and I bit. The three fields are returned to the TP sender through
the CETPH of TPACK-CC/TPNAK-CC/TPSACK-CC.


6.6.1.3.2 CAQM Process on the Sender

The TP sender includes a window increase request when sending a TP Packet. Specifically, the C bit is
cleared, the I bit is set to 1, and the Hint field is filled with the expected window increase (if no increase
is required, the I bit is set to 0).

When the TP sender receives a response packet (TPACK-CC/TPNAK-CC/TPSACK-CC), the TP sender
adjusts the size of the cw window based on the C, I, and Hint information in the CETPH. Table 6-11
describes the window adjustment rules.

                                       Table 6-11 Window adjustment rules
 C                 I    TP Sender Behavior
 If it's greater   0    Reduce the congestion window.
 than 0,
 If it's greater   1    The window is incremented by the value indicated by CETPH.Hint, and
 than 0,                decremented according to CETPH.C.
 0                 1    Increase the congestion window. The increment size is indicated by CETPH.Hint.
 0                 0    Keep the congestion window unchanged.


6.6.1.3.3 CAQM Process on the Switch

When a TP Packet passes through the UB Switch, the UB Switch updates the network-layer CCI control
bits (C and I) based on its congestion status. The specific mechanism SHALL meet the requirements in
Section 5.3.5.


6.6.1.3.4 CAQM Process on the Receiver

The TP receiver operates in two modes. If the coalesced acknowledgement packet is disabled, it
echoes the C, I, and Hint fields from the NTH.CCI field of the received TP Packet back to the sender
via the CETPH header in the TPACK-CC, TPNAK-CC, or TPSACK-CC response. If the coalesced
acknowledgement packets is enabled, the TP receiver maintains local accumulators for Hint, C, and I to
aggregate congestion information. Each time the TP receiver receives a TP Packet, if the C field in
NTH.CCI is 0 and the I field is 1, the local Hint is accumulated and the local I variable is set to 1. If the
C field is 1, the local C variable is incremented by 1. The TP receiver sends its local C, I, and Hint
values to the TP sender via the response packet's fields, then clears these variables.




unifiedbus.com                                                                                             200
6 Transport Layer



6.6.1.4 Congestion Control Adapted to Multipath Load Balancing

For RTP, the congestion control context is maintained per TP channel base. However, in per-packet
load balancing enabled in network, TP Packets within the same TP channel can follow separate
network routes. In per-packet load balancing, if the rate adjustment of congestion control is overly
sensitive to network congestion, it may result in over-reaction. A single congested network route may
reduce the transmission rate for all traffic in the TP channel despite the multiple network paths in use. It
can lower the overall network performance. Therefore, in per-packet load balancing, it is recommended
to coordinate congestion control and load balancing. For example, congestion control still maintains the
congestion control context at the granularity of TP channel, but only when the overall congestion is
identified across all available paths, and the sender reduces its transmission rate.

In flow-based load balancing, all TP Packets within a TP channel traverse the same network path.
Consequently, each TP channel in the TPG can maintain an independent congestion control context.


6.6.2 CTP Congestion Control Mechanism
When congestion control is enabled for CTP, coarse-grained congestion control is performed at the
granularity of {destination Entity, virtual link (VL)}, where the VL is an independent logical channel on a
physical link. CTP operates without transport-layer responses. Congestion signals can be carried back
in a separate congestion notification packet (such as CNP).

CTP-based per-packet load balancing is similar to RTP-based per-packet load balancing. The network
can be considered as a whole for congestion control.


6.7 Transmission Process

6.7.1 RTP Transmission Process

6.7.1.1 TP Sender Transmission Process

6.7.1.1.1 TP Sender Sends TP Packets

The process for the TP sender to send TP Packets is as follows:

      1.   TP channel selection
           The transport layer receives the transaction operation from the transaction layer, and selects
           the corresponding TP channel or TPG for data transmission according to the transaction
           information. If a TPG is used, the sender selects an appropriate TP channel based on the
           TPG context and a configured policy (see Section 6.5.1.1), aligned with the granularity of the
           transaction operation.




unifiedbus.com                                                                                           201
6 Transport Layer



      2.   PSN generation
           The TP sender divides the operations passed from the transaction layer into TP Packets
           based on the maximum transmission unit (MTU) at the transport layer for transmission. The
           TP sender assigns the PSN in the RTPH of the TP Packet.
           Each time the TP sender generates a new TP Packet, its PSN value is incremented by 1.
           According to the preceding rules, if the current PSN is curr_PSN and the next PSN is
           next_PSN, then next_PSN = (curr_PSN + 1) mod 16M. When the TP Packet is generated
           again, curr_PSN is set to next_PSN, and then next_PSN is calculated.
      3.   Operation code generation
           TPOpcode[6:0] SHALL be set to 1. TPOpcode[7] (last flag) indicates whether the TP Packet
           is the last one of the current transaction operation. A value of 0 means it is not the last TP
           Packet; a value of 1 marks it as the last packet for the transaction.
      4.   Payload generation
           When the operation code indicates the current TP Packet is not the last packet of the
           transaction, the payload length (transaction layer data, excluding the transaction layer packet
           header) must match the transport layer MTU. If it is the last TP Packet, the payload length
           can range from 1 to the MTU. If the payload length of a transaction operation exceeds the
           MTU, the transport layer will generate more than one packet. The payload length of the last
           TP Packet must be greater than 0.


6.7.1.1.2 TP Sender Processes Transport Layer Responses

The response types at the transport layer include TPACK, TPNAK, and TPSACK. For details about the
response packet processing logic of the TP sender, see Section 6.4.2.


6.7.1.2 TP Receiver Transmission Process

6.7.1.2.1 TP Receiver Receives TP Packets

The process for the TP receiver to receive TP Packets is as follows:

      1.   TP Packet receiving
           Find the corresponding TP context based on the RTPH. DstTPN in the TP Packet and
           receive the corresponding TP Packet.
      2.   PSN verification
           The TP receiver verifies the maintained EPSN field and the PSN contained in the TP Packet.
           For details about the processing logic, see Section 6.4.2.
      3.   Submission to the transaction layer
           Submit the payload in the TP Packet to the transaction layer.
      4.   Operation delivery to transaction layer
           The TP receiver needs to check whether the received TP Packet is the last one of the current
           operation. This information is indicated by bit 7 of the TPOpcode field (the "last" flag) in the



unifiedbus.com                                                                                              202
6 Transport Layer



           RTPH. The sequence number of the current operation is carried in the TPMSN in the RTPH.
           If the last flag is 1, it indicates that the TP Packet is the last TP Packet of the current
           operation. Once the last TP Packet of the current operation and all preceding packets have
           been received, the packets of the operation are considered fully received. The transport layer
           notifies the transaction layer that the operation with TPMSN has been received. Then, the
           transaction layer can proceed to execute the operation. After the transaction layer
           successfully executes the operation, if the transaction layer returns a TAACK to the TP
           receiver, the transport layer sends the TAACK as a TP data packet. The original TP receiver
           becomes the TP sender to send the TP Packet whose payload is the TAACK. Upon receiving
           that TP Packet, the peer TPEP processes it using the TP receiver logic and responds with a
           TPACK, TPNAK, or TPSACK, as appropriate.


6.7.1.2.2 TP Receiver Sends Transport Layer Responses

For details about the generation logic of the three types of transport layer responses, see Section 6.4.2.
Specifically, the transport layer responses can also be used to carry transaction layer response
information (see Section 7.3.1).


6.7.2 CTP Transmission Process

6.7.2.1 TP Sender Sends TP Packets

The process for the TP sender to send TP Packets is as follows:

      1.   Operation code generation
           The TPOpcode operation code in the CTPH has a length of 2 bits. In the CTP, all transaction
           operations passed from the transaction layer are carried by one TP Packet, with the value of
           TPOpcode[1:0] set to 0x0.
      2.   Payload generation
           The payload length must be between 0 and the MTU of the transport layer.


6.7.2.2 TP Receiver Receives TP Packets

The process for the TP receiver to receive TP Packets is as follows:

      1.   TP Packet receiving
           The TP receiver receives the TP Packets.
      2.   Delivery to the transaction layer
           In CTP mode, each TP Packet carries a complete transaction operation. Therefore, when
           receiving a TP Packet, the TP receiver directly instructs the transaction layer to execute the
           transaction operation corresponding to the TP Packet.
      3.   Completion check on received operation (transaction layer)




unifiedbus.com                                                                                           203
6 Transport Layer



           After the transaction layer successfully executes the transaction operation, if the transaction
           layer returns a TAACK to the TP receiver, the transport layer sends the TAACK as a TP data
           packet. The original TP receiver becomes the TP sender to send the TP Packet whose
           payload is the TAACK. After receiving the TP Packet, the peer TPEP executes the TP
           receiver logic to receive the TP Packet.


6.8 Interaction Between the Transport Layer and Transaction
Layer
This section describes the interaction between the transaction layer and transport layer.

The transaction layer assigns initiator (requests transaction) and target (completes transaction) roles.
The transport layer assigns TP sender (sends packets) and TP receiver (receives them) roles, which
can switch during transactions. For example, UBPU A acts as the initiator and UBPU B acts as the
target. The transport layer of UBPU A serves as the TP sender to send the TP Packet carrying the
transaction operation, and the transport layer of UBPU B serves as the TP receiver to receive the TP
Packet. Then, the transport layer of UBPU B serves as the TP sender to reply with the TP Packet
carrying the TAACK, and the transport layer of UBPU A serves as the TP receiver. To avoid confusion,
the initiator transport layer and target transport layer are used in this section.


6.8.1 Interaction Process in Transaction Layer ROI and ROT Modes
This section uses the write transaction as an example to describe the RTP transport process in
transaction layer ROI and ROT modes, as shown in Figure 6-34. (Note: In this example, each
transaction operation consists of two TP Packets, and the initial PSNs negotiated between the initiator
and target transport layers before transmission are m and n, respectively.) The transaction layer
response packets are named TAACK and TANAK. From the transport layer's view, both transaction
operations and the TAACK passed from the transaction layer may contain one or more TP Packets.
Therefore, when the initiator receives a transaction operation carrying the transaction layer TAACK, its
transport layer should respond with a TPACK.

      1.   The initiator transport layer receives a transaction operation from the transaction layer,
           segments its payload according to the transport-layer MTU, encapsulates it into TP Packets,
           and sends them out. In the example below, the operation fits into two TP Packets, which the
           TP sender transmits with PSNs m and m+1.
      2.   The target transport layer receives and identifies the TP Packet with PSN=m as in-order
           using its EPSN and sends back a TPACK with PSN=m. It then processes the next in-order
           TP Packet with PSN=m+1 and responds with a TPACK with PSN=m+1.
      3.   Receiving the TP Packet with PSN m+1 confirms successful receipt of the whole transaction.
           The information should be reported to the target transaction layer and the target transaction
           layer responds with a TAACK. The target transport layer sends the TP Packet with PSN=n,
           which carries the TAACK.




unifiedbus.com                                                                                          204
6 Transport Layer



      4.   The initiator transport layer receives the TPACKs with PSN m and m+1, indicating that the
           TP Packets with PSN m+1 and earlier have been successfully received. The initiator
           transport layer then updates its transmission status.
      5.   After receiving the TP Packet with PSN=n, which carries the TAACK, the initiator transport
           layer replies with the TPACK with PSN=n. After the TP Packet is successfully received, the
           corresponding transaction operation (TAACK) is also successfully received and delivered to
           the initiator transaction layer.




                        Figure 6-34 Write operation process (ROI and ROT modes)

In the ROI or ROT mode at the transaction layer, if the transport layer uses the CTP mode, since CTP
does not generate TPACK, only the transaction layer will generate responses, i.e., TAACK.


6.8.2 Interaction Process in Transaction Layer ROL Mode
The transaction layer ROL mode is different from the other transaction layer modes. The target
transaction layer does not generate a separate response (TAACK) packet; instead, the transport layer's
response packet carries responses to both the TP Packet and the transaction operation. Therefore, the
transport layer's response packet, such as TPACK responding to the last TP Packet of the transaction,
is generated only upon completion of the transaction by the target transaction layer. This section uses
the write transaction as an example to describe the RTP transport process in transaction layer ROL
mode, as shown in Figure 6-35.

      1.   The initiator transport layer receives a transaction operation from the transaction layer,
           segments its payload according to the transport-layer MTU, encapsulates it into TP Packets,
           and sends them out. This transaction operation is carried by two TP Packets. The initiator




unifiedbus.com                                                                                          205
6 Transport Layer



           transport layer sends a TP Packet carrying PSN=m and PSN=m+1 (the initial PSN of the
           initiator transport layer is m).
      2.   The target transport layer receives and identifies the TP Packet with PSN m as in-order
           based on its PSN and immediately sends a TPACK acknowledging PSN m. However, upon
           receiving the TP Packet with PSN m+1, the TP receiver delays sending a TPACK—unlike in
           other transaction layer modes such as ROI.
      3.   The TP Packet with PSN m+1 is the last packet of the transaction operation. Its receipt
           confirms that the entire operation has been successfully received. The target transport layer
           notifies the target transaction layer accordingly. After completing processing, the transaction
           layer informs the transport layer, which then generates a TPACK for PSN m+1. This TPACK
           carries combined acknowledgments from both the target transport layer and transaction
           layer, destined for their counterparts on the initiator.
      4.   The initiator transport layer receives the TPACKs with PSNs m and m+1, indicating that the
           TP Packets with PSNs m and m+1 have been successfully received. The initiator transport
           layer then updates the local transmission status. The TPACK also carries the response to
           the initiator transaction layer. Therefore, the initiator transport layer notifies the transaction
           layer of the transaction completion information retrieved from the TPACK packet.




                              Figure 6-35 Write operation process (ROL mode)

The CTP transport layer does not generate the TPACK. The transaction layer needs to generate the
TAACK in ROL mode.




unifiedbus.com                                                                                              206
