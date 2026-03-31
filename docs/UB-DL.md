4 Data Link Layer




4 Data Link Layer


4.1 Overview




                                 Figure 4-1 Overview of the data link layer

The data link layer resides between the physical layer and the network layer. It provides reliable, in-
order, point-to-point packet delivery for upper-layer protocols. The data link layer SHALL perform the
following functions:

      ⚫    Encapsulate and parse data link layer control blocks (DLLCBs) for link management and
           control, and data link layer data packets (DLLDPs) for payload sending and receiving. See
           Section 4.3.
      ⚫    Support both cyclic redundancy check (CRC) and non-CRC encapsulation modes to balance
           reliability and latency. See Section 4.3.
      ⚫    Support up to 16 virtual lanes (VLs) per link to enable traffic isolation and differentiated QoS.
           See Section 4.5.
      ⚫    Implement credit-based flow control on a per-VL basis to prevent receiver buffer overflow.
           See Section 4.6.
      ⚫    Support point-to-point retransmission to ensure lossless delivery of DLLCBs and DLLDPs.
           See Section 4.7.


4.2 Data Link State Machine
The data link layer SHALL implement a state machine to manage link initialization, parameter
negotiation, credit exchange, and normal link operation. The state machine SHALL transition based on
the signals on the physical layer and other conditions. Figure 4-2 shows the data link state machine.




unifiedbus.com                                                                                            90
4 Data Link Layer




                                    Figure 4-2 Data link state machine

The states in a data link state machine are defined as follows:

      ⚫   DLL_Disabled: initial link state after a UB device or port reset. This state indicates that the
          link is not set up at the physical layer (physical layer signal LinkUp==1'b0). However, the
          reset of an Entity does not cause the link state machine to enter the DLL_Disabled state. For
          details about the reset requirements, see Section 10.6.1.
      ⚫   DLL_Param_Init: parameter initialization state. The physical layer notifies that the physical
          link has been set up (physical layer signal LinkUp==1'b1). The data link layer negotiates
          parameters such as the credit return granularity, ACK return granularity, and VL enabling with
          the peer end in this state. For details, see Section 4.4.
      ⚫   DLL_Credit_Init: credit initialization state. After the parameter auto-negotiation is completed,
          the data link layer initializes the credit in this state. For details, see Section 4.6.1.
      ⚫   DLL_Normal: data communication state. The local data link layer communicates with the
          peer data link layer with DLLDPs.

The data link layer SHALL report status to the network layer:

      ⚫   DLL_Status_Down: No DLLDPs can be sent.
      ⚫   DLL_Status_Up: DLLDPs can be sent.

The link in different states SHALL meet the following requirements:

      ⚫   DLL_Disabled
          (1) In the DLL_Disabled state, the link:
                 –   Reports the DLL_Status_Down state to the network layer.




unifiedbus.com                                                                                              91
4 Data Link Layer



                 –   Discards packets originating from the local network layer and DLLCBs and DLLDPs
                     received by the local physical layer.
                 –   Does not generate DLLCBs.
          (2) Condition for transitioning to the DLL_Param_Init state: The physical layer reports the
                 LinkUp==1'b1 signal.
      ⚫   DLL_Param_Init:
          (1) In the DLL_Param_Init state, the link:
                 –   Reports the DLL_Status_Down state to the network layer.
                 –   Discards packets originating from the local network layer and DLLDPs received by
                     the local physical layer.
                 –   Sends a retransmission request set, and exchanges the Init Block for parameter
                     initialization auto-negotiation after receiving a retransmission acknowledgment set
                     from the peer end. For details about retransmission sets, see Section 4.7.3. For
                     details about the Init Block, see Section 4.3.3.9. For details about initialization auto-
                     negotiation, see Section 4.4.
          (2) Condition for transitioning to the DLL_Credit_Init state: The data link layer completes
                 initialization auto-negotiation and the physical layer continuously reports the
                 LinkUp==1'b1 signal.
          (3) Condition for transitioning to the DLL_Disabled state: The physical layer reports the
                 LinkUp==1'b0 signal.
      ⚫   DLL_Credit_Init:
          (1) In the DLL_Credit_Init state, the link:
                 –   Reports the DLL_Status_Down state to the network layer.
                 –   Discards packets originating from the local network layer and DLLDPs received by
                     the local physical layer.
                 –   Receives and sends the Crd_Ack Block to initialize the credit at the data link layer.
                     For details, see Section 4.6.1.
          (2) Condition for transitioning to the DLL_Normal state: The data link layer completes credit
                 initialization and the physical layer continuously reports the LinkUp==1'b1 signal.
          (3) Condition for transitioning to the DLL_Disabled state: The physical layer reports the
                 LinkUp==1'b0 signal.
      ⚫   DLL_Normal:
          (1) In the DLL_Normal state, the link:
                 –   Reports the DLL_Status_Up state to the network layer.
                 –   Sends and receives DLLDPs and DLLCBs.
          (2) Condition for transitioning to the DLL_Disabled state: The physical layer reports the
                 LinkUp==1'b0 signal.




unifiedbus.com                                                                                              92
4 Data Link Layer



4.3 DLLCB/DLLDP Sending and Receiving

4.3.1 Overview
The data link layer supports sending and receiving DLLCBs and DLLDPs. DLLCBs and DLLDPs
support two packet encapsulation modes: non-CRC and CRC, each suited for different link conditions.
Encapsulation mode switching is initiated by the physical layer and completed with the cooperation of
the data link layer. For details about the bit error rate (BER) measurement and encapsulation mode
switching, see Section 3.4.2.8 and Section 4.3.3.8.

The data link layer SHALL transmit upper-layer data using DLLDPs and control messages using
DLLCBs. Both SHALL be encapsulated in flits (1 flit = 20 bytes):

      ⚫    DLLDP: payload carrier (1 to 512 flits)
      ⚫    DLLCB: DLL control block (1 to 32 flits)


4.3.2 DLLDP Format

4.3.2.1 DLLDP Composition

The data link layers at both ends of a link transmit upper-layer service data using DLLDPs as the
transmission granularity. Each DLLDP SHALL consist of 1 to 512 flits:

      ⚫    If ≤ 32 flits: transmitted in one data link layer data block (DLLDB)
      ⚫    If > 32 flits: segmented into up to 16 DLLDBs (maximum 32 flits each)

The first DLLDB in a DLLDP is called the first block, the last DLLDB is called the last block, and the
other DLLDBs are called middle blocks. Each DLLDB is limited to a maximum of 32 flits. Figure 4-3
shows the mapping between the DLLDP, DLLDB, and flit. The size of each flit is fixed at 20 bytes. If a
flit's payload is shorter than 20 bytes, the sender pads it with zeros to fill the full flit size. The receiver
discards these padding bits during processing.




unifiedbus.com                                                                                                    93
4 Data Link Layer




                              Figure 4-3 Mapping between the DLLDP, DLLDB, and flit

Example: flit padding in CRC mode

As shown in Figure 4-4, the DLLDB consists of three flits. Only the last flit needs to be filled with padding. For details
about the CRC mode, see Section 4.3.2.2.




                                              Figure 4-4 Padding example


4.3.2.2 CRC Mode

4.3.2.2.1 DLLDP Format

In CRC mode:

       ⚫     Link Packet Header (LPH, 4 bytes) in the first flit of the first DLLDB
       ⚫     Link Block Header (LBH, 2 bytes) in the first flit of the middle/last DLLDB
       ⚫     Block Cyclic Redundancy Check (BCRC, 4 bytes) in the last flit of each DLLDB

In CRC mode, the physical-layer forward error correction (FEC) can be optionally enabled. When the
physical-layer FEC is enabled, the data link needs to determine whether FEC decoding is successful
after receiving flits. If FEC decoding is successful, functions such as delimitation and credit-based flow




unifiedbus.com                                                                                                               94
4 Data Link Layer



control are implemented via LPH/LBH, and accuracy is verified through CRC. If FEC decoding fails or a
CRC check error occurs, retransmission is performed using a data link layer retransmission
mechanism. Figure 4-5 shows the DLLDP format in CRC mode.




                                 Figure 4-5 DLLDP format in CRC mode


4.3.2.2.2 LPH Format

The LPH SHALL store DLLDP description and control information, including the DLLDP length and
credit return information. For details about credit return, see Section 4.6. Figure 4-6 shows the format of
the first flit of a DLLDP. Depending on the payload length, the Payload[31:0] field may also be BCRC.

          Byte 0                     Byte 1                     Byte 2                    Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                           Link Packet Header
                                              Payload[127:96]
                                              Payload[95:64]
                                              Payload[63:32]
                                          Payload[31:0]/BCRC
                               Figure 4-6 Format of the first flit of a DLLDP




unifiedbus.com                                                                                          95
4 Data Link Layer



The LPH occupies 4 bytes. For details about the meaning of each field, see Table 4-1.

                                  Table 4-1 LPH fields in CRC mode
                                                   LPH
 Byte ID   Bit ID    Field                Description
 0         7         CRD                  Indicates whether the block returns the credit. 1b'0
                                          indicates that the credit is not returned, and 1b'1 indicates
                                          that the credit is returned. The return granularity is
                                          determined through negotiation during initialization. For
                                          details, see Section 4.4.
           6         ACK                  Indicates whether the block releases the retry buffer space.
                                          1b'0 indicates that the retry buffer space is not released,
                                          and 1b'1 indicates that the retry buffer space is released.
                                          For details, see Section 4.7.3.
                                          The release granularity is determined through negotiation
                                          during initialization. For details, see Section 4.4.
           5         CRD_VL[3:0]          ID of the VL to which the credits carried in the CRD field
                                          SHALL be returned.
           4
           3
           2
           1         Reserved             Reserved. The sender sets this field to 0 by default, and the
                                          receiver ignores this field.
           0         VL[3:0]              VL ID of the block. The VL field value is carried from the
                                          network layer to the data link layer. For details, see
 1         7                              Section 4.5.
           6
           5
           4         Reserved             Reserved. The sender sets this field to 0 by default, and the
                                          receiver ignores this field.
           3         CFG[3:0]             The data link layer distinguishes DLLDPs and DLLCBs by
                                          the CFG field.
           2
                                          If CFG == 0, it is a DLLCB, and the field value is generated
           1                              and filled by the data link layer.
                                          If CFG == 3, 4, 5, 6, 7, or 9, it is a DLLDP, and the value of
           0
                                          this field is carried from the network layer to the data link
                                          layer. The specific type is defined by the upper layer and is
                                          not sensed by the data link layer.
                                          If CFG == others, the field is reserved.
                                          Note: The value of CFG in a DLLDP SHALL NOT be 0.

 2         7         RT                   Routing type. The value of this field is carried from the network
                                          layer to the data link layer. For details, see Section 5.3.2.
           6
           5         PLENGTH[13:10]       Number of DLLDBs. The values 0 to 15 indicate 1 to 16
                                          DLLDBs, respectively.
           4




unifiedbus.com                                                                                            96
4 Data Link Layer



                                            LPH
 Byte ID   Bit ID   Field          Description
           3
           2
           1        PLENGTH[9:5]   Number of flits of the last DLLDB. The values 0 to 31
                                   indicate 1 to 32 flits, respectively.
           0
 3         7
           6
           5
           4        PLENGTH[4:0]   Flit in which the payload in the last DLLDB ends. It is used
                                   to calculate the payload size in the flit. The meanings in
           3                       CRC and non-CRC modes are different.
           2                       In CRC mode:
                                   ● Rule 1: When PLENGTH[4:0] is 0 to 15, the payload
           1
                                     ends at the last flit of the DLLDP and the payload size of
           0                         the flit is PLENGTH[4:0] + 1 bytes.
                                   ● Rule 2: When PLENGTH[4:0] is 16 to 19, the payload
                                     ends at the second before the last flit of the DLLDP and
                                     the payload size of the flit is PLENGTH[4:0] + 1 bytes.
                                   ● Rule 3: When PLENGTH[4:0] is 24 to 27, the payload
                                     ends at the second before the last flit of the DLLDP and
                                     the payload size of the flit is PLENGTH[4:0] – 11 bytes.
                                   ● Rule 4: When PLENGTH[4:0] is others, this field is
                                     reserved.
                                   In non-CRC mode:
                                   ● Rule 1: When PLENGTH[4:0] is 0 to 15, the payload
                                     ends at the last flit of the DLLDP and the payload size of
                                     the flit is PLENGTH[4:0] + 1 bytes.
                                   ● Rule 2: When PLENGTH[4:0] is 17 or 19, the payload
                                     ends at the second before the last flit of the DLLDP and
                                     the payload size of the flit is PLENGTH[4:0] + 1 bytes.
                                   ● Rule 3: When PLENGTH[4:0] is 27, the payload ends at
                                     the second before the last flit of the DLLDP and the
                                     payload size of the flit is PLENGTH[4:0] – 11 bytes.
                                   ● Rule 4: When PLENGTH[4:0] is 28 to 30, the payload
                                     ends at the last flit of the DLLDP and the payload size of
                                     the flit is PLENGTH[4:0] – 11 bytes.
                                   ● Rule 5: When PLENGTH[4:0] is others, this field is
                                     reserved.




unifiedbus.com                                                                                    97
4 Data Link Layer



Note:

Each point-to-point link supports a maximum of 16 VLs.

Due to the BCRC/END position and length restrictions, the payload may end at either the last or second before the last
flit. PLENGTH[4:0] indicates the end position.

During packet encapsulation, the sender identifies the last flit that contains the payload, calculates the value of
PLENGTH[4:0] based on the number of remaining payload bytes in the flit, and fills the value into the LPH. While parsing
the packet, the receiver determines the payload length using PLENGTH[4:0] and discards the padding.

Example: PLENGTH[4:0] conversion

When encapsulating packets, the sender calculates PLENGTH[4:0] and fills it into the field.

In Figure 4-7, the DLLDB is the last block of a DLLDP. The payload ends at the second before the last flit (excluding rule
1 in CRC mode in the preceding PLENGTH[4:0] description). This flit contains a 16-byte payload. Based on the
PLENGTH range, rule 3 in CRC mode applies. Since Payload = PLENGTH[4:0] – 11, PLENGTH[4:0] is 27. Therefore,
set the value of the PLENGTH[4:0] field to 27.




                      Figure 4-7 PLENGTH conversion example – DLLDP/DLLDB format 1

In Figure 4-8, there is only one DLLDB in a DLLDP. The payload ends at the last flit (only rule 1 in CRC mode applies).
This flit contains a 10-byte payload. According to rule 1 in CRC mode, since Payload = PLENGTH[4:0] + 1,
PLENGTH[4:0] is 9. Therefore, set the value of the PLENGTH[4:0] field to 9.




                      Figure 4-8 PLENGTH conversion example – DLLDP/DLLDB format 2

In Figure 4-9, the DLLDB is the last block of a DLLDP. The payload ends at the last flit (only rule 1 in CRC mode applies).
This flit contains a 14-byte payload. According to rule 1 in CRC mode, since Payload = PLENGTH[4:0] + 1,
PLENGTH[4:0] is 13. Therefore, set the value of the PLENGTH[4:0] field to 13.




unifiedbus.com                                                                                                            98
4 Data Link Layer




                     Figure 4-9 PLENGTH conversion example – DLLDP/DLLDB format 3


4.3.2.2.3 LBH Format

The LBH SHALL contain DLLDB description and control information, including credit return information.
Figure 4-5 shows the position of the LBH field. The LBH SHALL occupy the first 2 bytes of the first flit in
middle blocks and the last block of a DLLDP. Figure 4-10 shows the structure of the flit. Depending on
the payload length, the field Payload[31:0] may also be BCRC in the last flit.

           Byte 0                       Byte 1                       Byte 2                      Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                    Link Block Header                                         Payload[143:128]
                                                  Payload[127:96]
                                                  Payload[95:64]
                                                  Payload[63:32]
                                              Payload[31:0]/BCRC
                                Figure 4-10 LBH position in middle and last blocks

Table 4-2 defines each field of LBH.
                                       Table 4-2 LBH fields in CRC mode
                                                          LBH
 Byte ID    Bit ID      Field                    Description
 0          7           CRD                      Indicates whether the block returns the credit. 1b'0
                                                 indicates that the credit is not returned, and 1b'1 indicates
                                                 that the credit is returned. The return granularity is
                                                 determined through negotiation during initialization. For
                                                 details, see Section 4.4. If multiple CRD fields in a DLLDP
                                                 are set to 1b'1, multiple credits are returned.
            6           ACK                      Indicates whether the block releases the retry buffer space.
                                                 1b'0 indicates that the retry buffer space is not released,
                                                 and 1b'1 indicates that the retry buffer space is released.
                                                 The release granularity is determined through negotiation
                                                 during initialization. For details, see Section 4.4. If multiple
                                                 ACK fields in a DLLDP are set to 1b'1, multiple
                                                 acknowledgements are returned and the retry buffer space
                                                 is released accordingly.




unifiedbus.com                                                                                                   99
4 Data Link Layer



                                                       LBH
 Byte ID    Bit ID     Field                  Description
            5          CRD_VL[3:0]            ID of the VL to which the credits carried in the CRD field
                                              SHALL be returned.
            4
            3
            2
            1          Reserved               Reserved. The sender sets this field to 0 by default, and the
                                              receiver ignores this field.
            0          VL[3:0]                VL ID of the block. The VL field value is carried from the
                                              network layer to the data link layer. For details, see
 1          7                                 Section 4.5.
            6
            5
            4          Reserved               Reserved. The sender sets this field to 0 by default, and the
                                              receiver ignores this field.
            3          CFG[3:0]               The data link layer distinguishes DLLDPs and DLLCBs by
                                              the CFG field.
            2
                                              If CFG == 0, it is a DLLCB, and the field value is generated
            1                                 and filled by the data link layer.
                                              If CFG == 3, 4, 5, 6, 7, or 9, it is a DLLDP, and the network
            0
                                              layer transfers the field value to the data link layer. The
                                              specific type is defined by the upper layer and is not sensed
                                              by the data link layer.
                                              If CFG == others, the field is reserved.
                                              Note: The value of CFG in a DLLDP SHALL NOT be 0.


4.3.2.2.4 BCRC Format

The BCRC SHALL provide error detection for each DLLDB. It SHALL consist of one 30-bit CRC
(CRC30) and two information bits. Figure 4-5 shows the BCRC position. The BCRC SHALL be
appended to the last flit of every DLLDB in CRC mode. Figure 4-11 shows the flit structure.

           Byte 0                    Byte 1                      Byte 2                     Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                               Payload[79:48]
                                               Payload[47:16]
                     Payload[15:0]                                        Padding[47:32]
                                                Padding[31:0]
                                                    BCRC
                           Figure 4-11 BCRC position in the last flit of a DLLDB




unifiedbus.com                                                                                             100
4 Data Link Layer



If a DLLDB has only one flit, the header of the flit carries the LPH or LBH field based on the DLLDB
position.

The BCRC fields occupy 32 bits. For details about the meaning of each bit, see Table 4-3.

                                   Table 4-3 BCRC fields in CRC mode
                                                     BCRC
 Byte ID    Bit ID     Field                Description
 16         7          Reserved             Reserved. The sender sets this field to 0 by default, and the
                                            receiver ignores this field.
            6          ERROR_FLAG           Packet error flag, which is valid only for the last DLLDB in a
                                            DLLDP:
                                            1'b0: This DLLDP is a correct packet.
                                            1'b1: This DLLDP is a wrong packet.
                                            For details, see Section 4.8.3.
            5          CRC30[29:0]          30-bit CRC result. For details, see Section 4.7.2.

            4

            3

            2

            1

            0

 17:19      7

            6

            5

            4

            3

            2

            1

            0


4.3.2.3 Non-CRC Mode

In non-CRC mode, the first four bytes of the first block in a DLLDP contain the LPH, the first two bytes
of middle blocks and the last block contain the LBH, and END is located at the last flit of the last block.
For details about the END field, see Table 4-4. The data link layer uses the END field to identify packet
errors. In non-CRC mode, the FEC function SHALL be enabled at the physical layer. If the physical-
layer FEC decoding corresponding to the flit received by the data link layer fails, data is retransmitted
by using the retransmission mechanism. Figure 4-12 shows the DLLDP format in non-CRC mode.




unifiedbus.com                                                                                           101
4 Data Link Layer




                                Figure 4-12 DLLDP format in non-CRC mode

The LPH and LBH formats in non-CRC mode SHALL be identical to those in CRC mode (see Section
4.3.2.2.2 and Section 4.3.2.2.3). The END field SHALL be placed in the last flit of the final DLLDB of the
DLLDP. Figure 4-13 shows the flit format. If the flit is the first flit of the DLLDP/DLLDB, the
corresponding LPH/LBH header field is carried.

           Byte 0                     Byte 1                        Byte 2                    Byte 3
 7 6 5 4 3 2 1 0               7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                Payload[79:48]
                                                Payload[47:16]
                     Payload[15:0]                                           Padding[71:56]
                                                Padding[55:24]
                                  Padding[23:0]                                               END
                     Figure 4-13 END field in the last flit of a DLLDP in non-CRC mode

                                            Table 4-4 END fields
                                                        END
 Byte ID    Bit ID     Field                   Description
 19         7          Reserved                Reserved. The sender sets this field to 0 by default, and the
                                               receiver ignores this field.
            6          ERROR_FLAG              Packet error flag:
                                               ● 1'b0: This DLLDP is a correct packet.
                                               ● 1'b1: This DLLDP is a wrong packet.
                                               The ERROR_FLAG field indicates an error packet. For




unifiedbus.com                                                                                           102
4 Data Link Layer



                                                   END
 Byte ID   Bit ID    Field                Description
                                          details, see Section 4.8.3.
           5         Reserved             Reserved. The sender sets this field to 0 by default, and the
                                          receiver ignores this field.
           4
           3
           2
           1
           0


4.3.3 DLLCB Format

4.3.3.1 DLLCB Header and Type

The data link layer SHALL support transmission and reception of DLLCBs to enable link management
functions, including credit return, retransmission, and parameter exchange. To prevent packet
delimitation errors, DLLCBs cannot be inserted into DLLDBs. That is, DLLCBs can be inserted only
between two DLLDBs. Each DLLCB SHALL consist of 1 to 32 flits and may use CRC or non-CRC
mode. Figure 4-14 and Figure 4-15 show the DLLCB format.




                                Figure 4-14 DLLCB format in CRC mode




                             Figure 4-15 DLLCB format in non-CRC mode




unifiedbus.com                                                                                      103
4 Data Link Layer



The Link Control Header (LCH) SHALL occupy the first 4 bytes of the initial flit of a DLLCB. For details
about the fields, see Table 4-5.

                                    Table 4-5 LCH fields in a DLLCB
                                                    LCH
 Byte ID    Bit ID    Field                Description
 0          7         N/A                  Fixed value 1'b0.
            6         CLENGTH              Flit length of a DLLCB.
            5                              0 to 31 respectively indicate 1 to 32 flits.

            4
            3
            2
            1         N/A                  Fixed value 6'b100000.
            0
 1          7
            6
            5
            4
            3         CFG[3:0]             The data link layer distinguishes DLLDPs and DLLCBs by
                                           the CFG field.
            2
                                           If CFG == 0, it is a DLLCB, and the field value is generated
            1                              and filled by the data link layer.
                                           If CFG == 3, 4, 5, 6, 7, or 9, it is a DLLDP, and the field
            0
                                           value is carried by the network layer to the data link layer.
                                           The specific type is defined by the upper layer and is not
                                           sensed by the data link layer.
                                           If CFG == others, the field is reserved.
                                           Note: The value of CFG in a DLLCB SHALL be 0.

 2          7         CTRL                 DLLCB type. For details, see Table 4-6.
            6
            5
            4
            3         SUB_CTRL             DLLCB subtype. For details, see Table 4-6.
            2
            1
            0
 3          7         For the DLLCB of a specific type, see Sections 4.3.3.2 to 4.3.3.9.
            6




unifiedbus.com                                                                                             104
4 Data Link Layer



                                                     LCH
 Byte ID      Bit ID    Field               Description
              5
              4
              3
              2
              1
              0


DLLCBs SHALL be classified by the CTRL and SUB_CTRL fields at the data link layer. Among them,
Null Block, No_Operation Block, Retry_Idle Block, Retry_Req Block, Retry_Ack Block, and Crd_Ack
Block are the DLLCBs of the data plane, while the remaining blocks are the DLLCBs of the control
plane. For details, see Table 4-6.

                                          Table 4-6 DLLCB types
                                                   DLLCB
 DLLCB Type                          CTRL                     SUB_CTRL             Meaning
 Null Block                          4'b0000                  4'b0000              See Section 4.3.3.2

 No_Operation Block                  4'b0000                  4'b0001              See Section 4.3.3.3

 Retry_Idle Block                    4'b0001                  4'b0000              See Section 4.3.3.4

 Retry_Req Block                     4'b0001                  4'b0001

 Retry_Ack Block                     4'b0001                  4'b0010

 Crd_Ack Block                       4'b0010                  4'b0100              See Section 4.3.3.5

 Param_Exchg Block                   4'b0011                  4'b0000              See Section 4.3.3.6

 Lane_Manage Block                   4'b0100                  4'b0001              See Section 4.3.3.7

 Block_Mode_Chg Block                4'b0101                  4'b0000              See Section 4.3.3.8

 Init Block                          4'b1100                  4'b1000              See Section 4.3.3.9


As shown in Figure 4-14 and Figure 4-15, the header LCH field format is the same in CRC and non-
CRC modes, and only the tail is different. The following uses the DLLCB format in CRC mode as an
example by default. In non-CRC mode, only the tail of the last flit needs to be replaced. The tail
differences are as follows:

      ⚫       For the BCRC fields in CRC mode, see Section 4.3.2.2.4.
      ⚫       For the END fields in non-CRC mode, see Figure 4-13 and Table 4-4.




unifiedbus.com                                                                                       105
4 Data Link Layer



Example: priority setting

The priority of DLLCBs/DLLDPs sent by the sender at the data link layer can be adjusted according to the specific
implementation. The following list provides a reference example, with priorities ranked in descending order:

Retry_Ack_Set (including 1 Retry_Idle Block and 32 Retry_Ack Blocks in succession) > Retry_Req_Set (including 1
Retry_Idle Block and 32 Retry_Req Blocks in succession) > Block_Mode_Chg Block > Crd_Ack Block (Type == 1'b0) >
Lane_Manage Block > Param_Exchg Block > Crd_Ack Block (Type == 1'b1) > Init Block > No_Operation Block >
DLLDP > Null Block


4.3.3.2 Null Block

A Null Block is sent when no DLLDP is transmitted at the data link layer, that is, when the link is idle.
The peer end discards the Null Block upon receival. The mechanisms for sending and discarding Null
Blocks may be implemented at either the data link layer or the physical layer, depending on the specific
design. This behavior is not constrained by this specification. Each Null Block has a length of one flit.
Figure 4-16 shows the format.

            Byte 0                         Byte 1                        Byte 2                        Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
 1'b0




        CLENGTH              6'b100000              CFG           CTRL        SUB_CTRL               Reserved

                                                       Reserved
                                                       Reserved
                                                       Reserved
                                                          BCRC
                                    Figure 4-16 Null Block format in CRC mode

The fields are described as follows:

        ⚫   CLENGTH: The value is 5'b00000, indicating that the Null Block length is 1 flit.
        ⚫   CFG: The value is 4'b0000, indicating that the block is a DLLCB.
        ⚫   CTRL and SUB_CTRL: The values are 4'b0000, indicating that the DLLCB type is Null
            Block. For details about other types, see Table 4-6.


4.3.3.3 No_Operation Block

No_Operation Blocks (NOBs) are blocks filled when small packets (DLLDPs shorter than
PACKET_MIN_INTERVAL) are sent. The receiver has a limited rate for processing small packets.
Therefore, the sender SHALL reduce the rate of sending small packets. Otherwise, the receiver cannot
process the packets due to traffic burst. The size of a small packet depends on the actual service
scenario. The sender appends several NOBs after the small packet to meet the minimum interval
between two consecutive DLLDPs specified by the PACKET_MIN_INTERVAL field in the Init Block.
The receiver discards the received NOBs. NOBs are stored in the local retry buffer when they are sent.
The length of an NOB is 1 flit. Figure 4-17 shows the format of an NOB.



unifiedbus.com                                                                                                      106
4 Data Link Layer



            Byte 0                        Byte 1                       Byte 2             Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
 1'b0




        CLENGTH               6'b100000            CFG          CTRL      SUB_CTRL      Reserved

                                                    Reserved
                                                    Reserved
                                                    Reserved
                                                         BCRC
                                     Figure 4-17 NOB format in CRC mode

The fields are described as follows:

        ⚫   CLENGTH: The value is 5'b00000, indicating that the NOB length is 1 flit.
        ⚫   CFG: The value is 4'b0000, indicating that the block is a DLLCB.
        ⚫   CTRL and SUB_CTRL: The values are 4'b0000 and 4'b0001, respectively, indicating that
            the DLLCB type is NOB.


4.3.3.4 Retry Block

4.3.3.4.1 Retry_Idle Block

Retry_Idle Blocks are used to isolate DLLDPs from Retry_Req/Retry_Ack Blocks, preventing the
receiver from incorrectly identifying payloads as Retry_Req/Retry_Ack Blocks. The length of a
Retry_Idle Block is 1 flit.

            Byte 0                        Byte 1                       Byte 2             Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
1'b0




        CLENGTH               6'b100000            CFG          CTRL      SUB_CTRL      Reserved

                                                    Reserved
                                                    Reserved
                                                    Reserved
                                                         BCRC
                                Figure 4-18 Retry_Idle Block format in CRC mode

The fields are described as follows:

        ⚫   CLENGTH: The value is 5'b00000, indicating that the Retry_Idle Block length is 1 flit.
        ⚫   CFG: The value is 4'b0000, indicating that the block is a DLLCB.
        ⚫   CTRL and SUB_CTRL: The values are 4'b0001 and 4'b0000, respectively, indicating that
            the DLLCB type is Retry_Idle Block. For details about other types, see Table 4-6.




unifiedbus.com                                                                                       107
4 Data Link Layer



4.3.3.4.2 Retry_Req Block

Retry_Req Blocks are used to send a retransmission request. The length of a Retry_Req Block is 1 flit.

            Byte 0                       Byte 1                     Byte 2                      Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
1'b0




       CLENGTH               6'b100000            CFG        CTRL       SUB_CTRL              Reserved

                                                   Reserved
                          RcvPtr                             NUM_PHY_REINIT                 NUM_RETRY
                                                   Reserved
                                                     BCRC
                             Figure 4-19 Format of a Retry_Req Block in CRC mode

The fields are described as follows:

       ⚫    CLENGTH: The value is 5'b00000, indicating that the Retry_Req Block length is 1 flit.
       ⚫    CFG: The value is 4'b0000, indicating that the block is a DLLCB.
       ⚫    CTRL and SUB_CTRL: The values are 4'b0001, indicating that the DLLCB type is
            Retry_Req Block. For details about other types, see Table 4-6.
       ⚫    RcvPtr: start address for retransmission, that is, the ID of the first flit to be retransmitted in
            the retry buffer of the peer end.
       ⚫    NUM_RETRY: number of retransmission request sets initiated before the physical layer is
            reinitialized in a retransmission event. The value is cleared and re-counted after the physical
            layer is reinitialized.
       ⚫    NUM_PHY_REINIT: number of times the physical layer is reinitialized in a retransmission event.


4.3.3.4.3 Retry_Ack Block

Retry_Ack Blocks are used to return a retransmission acknowledgment to the peer end. The length of a
Retry_Ack Block is 1 flit.

            Byte 0                       Byte 1                     Byte 2                      Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
1'b0




       CLENGTH               6'b100000            CFG        CTRL        SUB_CTRL             Reserved

           Reserved                   NUM_RETRY                               NumFreeBuf
                           RdPtr                                                  WrPtr
                                                   Reserved
                                                     BCRC
                             Figure 4-20 Format of a Retry_Ack Block in CRC mode




unifiedbus.com                                                                                               108
4 Data Link Layer



The fields are described as follows:

       ⚫   CLENGTH: The value is 5'b00000, indicating that the Retry_Ack Block length is 1 flit.
       ⚫   CFG: The value is 4'b0000, indicating that the block is a DLLCB.
       ⚫   CTRL and SUB_CTRL: The values are 4'b0001 and 4'b0010, respectively, indicating that
           the DLLCB type is Retry_Ack Block. For details about other types, see Table 4-6.
       ⚫   NUM_RETRY: number of retransmission request sets initiated before the physical layer is
           reinitialized in a retransmission event. The value is cleared and re-counted after the physical
           layer is reinitialized.
       ⚫   NumFreeBuf: free space of the retry buffer, in flits
       ⚫   RdPtr: read pointer of the retry buffer for the current retransmission event
       ⚫   WrPtr: write pointer of the retry buffer for the current retransmission event


4.3.3.5 Crd_Ack Block

The data link layer implements credit-based flow control using VLs. It can send a Crd_Ack Block to the
peer end to return the credit. For details, see Section 4.6.

The data link layer supports retransmission. The local data link layer can send a Crd_Ack Block to the
peer to acknowledge flits stored in the retry buffer, thereby allowing the peer end to release the
corresponding buffer space. For details about retry buffer management, see Section 4.7.3.2.

The length of a Crd_Ack Block is 2 flits. Figure 4-21 and Figure 4-22 show the formats.

           Byte 0                      Byte 1                     Byte 2                    Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
1'b0




                                                                                  SD



       CLENGTH           6'b100000              CFG        CTRL       SUB_CTRL             Reserved      T

                      ACK_NUM                                              CRD_NUM[95:80]
                                                CRD_NUM[79:48]
                                                CRD_NUM[47:16]
                    CRD_NUM[15:0]                                             Reserved
                        Figure 4-21 Flit 0 format of a Crd_Ack Block in CRC mode

           Byte 0                      Byte 1                     Byte 2                    Byte 3
 7 6 5 4 3 2 1 0            7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                   Reserved
                                                   Reserved
                                                   Reserved
                                                   Reserved
                                                    BCRC
                        Figure 4-22 Flit 1 format of a Crd_Ack Block in CRC mode




unifiedbus.com                                                                                         109
4 Data Link Layer



Each field of a Crd_Ack Block is defined as follows:

       ⚫   CLENGTH: The value is 5'b00001, indicating that the length of the Crd_Ack Block is 2 flits. In
           non-CRC mode, the length remains unchanged, and the END field is not filled in the first flit.
       ⚫   CFG: The value is 4'b0000, indicating that the block is a DLLCB.
       ⚫   CTRL and SUB_CTRL: The values are 4'b0010 and 4'b0100, respectively, indicating that
           the DLLCB type is Crd_Ack Block. For details about other types, see Table 4-6.
       ⚫   SD: initialized credit sending done flag. 1'b1 indicates that the initialized credit sending
           process has completed, and 1'b0 indicates that the process is still in progress. This field is
           valid only when Type == 1'b1. For details about the definition of the Type field, refer to the
           following T field description.
       ⚫   T: credit type. 1'b1 indicates that the initialized credit is carried, and 1'b0 indicates that the
           non-initialized credit is returned. In the initialization phase, multiple Crd_Ack Blocks may need
           to be sent. When SEND_DONE == 1'b1 and Type == 1'b1, the last Crd_Ack Block is sent.
       ⚫   ACK_NUM: number of released retry buffers. It is 16 bits wide. The granularity of ACK_NUM
           is specified by CTRL_ACK_GRAIN_SIZE. The size of released buffers is ACK_NUM times
           CTRL_ACK_GRAIN_SIZE flits. CTRL_ACK_GRAIN_SIZE is negotiated during initialization.
           For details about parameter initialization negotiation, see Section 4.4.
       ⚫   CRD_NUM: 96 bits in total, with each 6-bit segment representing the number of credits carried
           or returned by one VL. The numbers of credits carried or returned by 16 VLs are
           {Crd_num_VL15,Crd_num_VL14,...,Crd_num_VL0}. The credit granularity is specified by
           CTRL_CREDIT_GRAIN_SIZE. The number of credits carried or returned by each VL is
           Crd_num_VL(N) times CTRL_CREDIT_GRAIN_SIZE(N) cells. CTRL_CREDIT_GRAIN_SIZE
           is negotiated during initialization. N indicates the corresponding VL ID. Cell is the basic unit of
           credit-based flow control. For details about parameter initialization negotiation, see Section 4.4.
           For details about credit initialization, see Section 4.6.1.1.


4.3.3.6 Param_Exchg Block

This block facilitates neighbor advertisement exchanges for the network layer. Once the data link layer
reaches the DLL_Normal state, the local device can continue exchanging information with the peer
device using Param_Exchg Blocks. The length of a Param_Exchg Block ranges from 1 to 32 flits.
Assume the length of a Param_Exchg Block is N flits. Figure 4-23 to Figure 4-25 show the formats.

           Byte 0                      Byte 1                       Byte 2                       Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
1'b0




       CLENGTH            6'b100000             CFG          CTRL       SUB_CTRL               Reserved

                                                   Reserved
                                        PARAM_EXCHG_DATA[31:0]
                                                   Reserved
                                                   Reserved
                      Figure 4-23 Flit 0 format of a Param_Exchg Block in CRC mode




unifiedbus.com                                                                                                  110
4 Data Link Layer



          Byte 0                       Byte 1                   Byte 2                    Byte 3
 7 6 5 4 3 2 1 0            7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                 Reserved
                                                 Reserved
                                       PARAM_EXCHG_DATA[31:0]
                                                 Reserved
                                                 Reserved
                 Figure 4-24 Flit 1 to flit (N-2) format of a Param_Exchg Block in CRC mode

          Byte 0                       Byte 1                   Byte 2                    Byte 3
 7 6 5 4 3 2 1 0            7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                 Reserved
                                                 Reserved
                                       PARAM_EXCHG_DATA[31:0]
                                                 Reserved
                                                  BCRC
                    Figure 4-25 Flit (N-1) format of a Param_Exchg Block in CRC mode

The fields are described as follows:

      ⚫    CLENGTH: The value is 5'b00000~5'b11111, indicating that the length of the Param_Exchg
           Block ranges from 1 to 32 flits.
      ⚫    CFG: The value is 4'b0000, indicating that the block is a DLLCB.
      ⚫    CTRL and SUB_CTRL: The values are 4'b0011 and 4'b0000, respectively, indicating that
           the DLLCB type is Param_Exchg Block. For details about other types, see Table 4-6.
      ⚫    PARAM_EXCHG_DATA: neighbor advertisement information. See Section 10.4.4.


4.3.3.7 Lane_Manage Block

The UB physical layer supports dynamic lane increase and decrease. The local physical layer initiates a
lane switching request to the local data link layer, prompting the local data link layer to send dynamic
lane increase and decrease commands to the physical layers at both ends via the Lane_Manage Block.
For the detailed process, see Section 3.4.2.3. The length of a Lane_Manage Block is 1 flit. Figure 4-26
shows the packet format.




unifiedbus.com                                                                                             111
4 Data Link Layer



           Byte 0                      Byte 1                       Byte 2                 Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
1'b0




       CLENGTH           6'b100000              CFG          CTRL      SUB_CTRL          Reserved

                                                 CMD[63:32]
                                                 CMD[31:0]
                                                 Reserved
                                                      BCRC
                          Figure 4-26 Lane_Manage Block format in CRC mode

The fields are described as follows:

       ⚫   CLENGTH: The value is 5'b00000, indicating that the Lane_Manage Block length is 1 flit.
       ⚫   CFG: The value is 4'b0000, indicating that the block is a DLLCB.
       ⚫   CTRL and SUB_CTRL: The values are 4'b0100 and 4'b0001, respectively, indicating that
           the DLLCB type is Lane_Manage Block. For details about other types, see Table 4-6.
       ⚫   Table 4-7 describes the CMD fields.
                                           Table 4-7 CMD fields
                                                       CMD
 Byte ID    Bit ID    Field                 Description
 0          7         REQ_ID                Link width switching request ID. The value is fixed at 0x5.
            6
            5
            4
            3         Reserved              Reserved. The sender sets this field to 0 by default, and the
                                            receiver ignores this field.
            2         Power_Down            Request to disable all lanes. 1b'1 indicates valid.
            1         Change_RLW            Request to switch the RLW (RX_Link_Width). 1b'1
                                            indicates valid.
            0         Change_TLW            Request to switch the TLW (TX_Link_Width). 1b'1 indicates
                                            valid.
 1          7         RSP_ID                Response ID. The value is fixed at 0xA.
            6
            5
            4
            3         Reserved              Reserved. The sender sets this field to 0 by default, and the
                                            receiver ignores this field.
            2         RX_Lane_Up            Lane increase acknowledgement. 1b'1 indicates lane




unifiedbus.com                                                                                            112
4 Data Link Layer



                                       CMD
 Byte ID   Bit ID   Field      Description
                               increase completed.
           1        RSP_RLW    Response to the request for switching the RLW: 1b'0 NAK
                               or 1b'1 ACK
           0        RSP_TLW    Response to the request for switching the TLW: 1b'0 NAK
                               or 1b'1 ACK
 2         7        Reserved   Reserved. The sender sets this field to 0 by default, and the
                               receiver ignores this field.
           6
           5        TLW        6'b000001: Set the value to X1.
           4                   6'b000010: Set the value to X2.
                               6'b000100: Set the value to X4.
           3
                               6'b001000: Set the value to X8.
           2                   Others: reserved
           1
           0
 3         7        Reserved   Reserved. The sender sets this field to 0 by default, and the
                               receiver ignores this field.
           6
           5        RLW        6'b000001: Set the value to X1.
           4                   6'b000010: Set the value to X2.
                               6'b000100: Set the value to X4.
           3
                               6'b001000: Set the value to X8.
           2                   Others: reserved
           1
           0
 4:7       7        Reserved   Reserved. The sender sets this field to 0 by default, and the
                               receiver ignores this field.
           6

           5

           4

           3

           2

           1

           0




unifiedbus.com                                                                           113
4 Data Link Layer



4.3.3.8 Block_Mode_Chg Block

UB supports encapsulation mode switching at the data link layer, enabling transitions between CRC
and non-CRC modes. The switching command is transmitted by the data link layer to both endpoints via
a Block_Mode_Chg Block. The length of a Block_Mode_Chg Block is 1 flit. Figure 4-27 shows the
format of a Block_Mode_Chg Block.

            Byte 0                         Byte 1                           Byte 2                       Byte 3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
1'b0




       CLENGTH               6'b100000               CFG            CTRL        SUB_CTRL Reserved                 TYPE

                                                        Reserved
                                                        Reserved
                                                        Reserved
                                                           BCRC
                         Figure 4-27 Format of a Block_Mode_Chg Block in CRC mode

The fields are described as follows:

       ⚫    CLENGTH: The value is 5'b00000, indicating that the Block_Mode_Chg Block length is 1 flit.
       ⚫    CFG: The value is 4'b0000, indicating that the block is a DLLCB.
       ⚫    CTRL and SUB_CTRL: The values are 4'b0101 and 4'b0000, respectively, indicating that
            the DLLCB type is Block_Mode_Chg Block. For details about other types, see Table 4-6.
       ⚫    TYPE: 4'b0000 indicates that the current Block_Mode_Chg Block is of
            Block_Mode_Chg_REQ type, and 4'b0001 indicates that the current Block_Mode_Chg Block
            is of Block_Mode_Chg_ACK type.

Example: encapsulation mode switching

Figure 4-28 shows the procedure for switching between CRC and non-CRC encapsulation modes via the
Block_Mode_Chg Block. The details are as follows:

       1.   Encapsulation mode switching can be triggered by two mechanisms: (1) when the local software requests a
            change in encapsulation mode, it instructs the physical layer to initiate the switch; and (2) when the physical
            layer proactively initiates the switch based on BER conditions. In both cases, the primary port at the physical
            layer initiates the encapsulation mode switching and coordinates with the data link layer. For detailed
            definitions of the primary port at the physical layer, see Section 3.4.2.1.

       2.   After receiving an encapsulation mode switching request from the physical layer, the local data link layer
            applies backpressure to the network layer traffic.

       3.   After the backpressure is completed, the encapsulation mode switching process is started by sending
            Block_Mode_Chg_REQ to the peer end. Subsequently, the local data link layer can only send Crd_Ack
            Block or Block_Mode_Chg_ACK.




unifiedbus.com                                                                                                           114
4 Data Link Layer



      4.   Upon receiving the Block_Mode_Chg_REQ, the peer data link layer also applies backpressure to the
           network layer traffic.

      5.   After the backpressure is completed, the peer end sends Block_Mode_Chg_REQ to the local data link layer,
           informing it that Block_Mode_Chg_REQ has been received; thereafter, the peer data link layer can only
           send Crd_Ack Block or Block_Mode_Chg_ACK.

      6.   Upon receiving the Block_Mode_Chg_REQ, the local data link layer returns all pending local ACKs to the
           peer end via the Crd_Ack Block and sends a Block_Mode_Chg_ACK to the peer data link layer to inform it
           that the Block_Mode_Chg_REQ has been received. Thereafter, the local data link layer ceases sending any
           DLLCB/DLLDP.

      7.   Upon receiving the Block_Mode_Chg_ACK, the peer data link layer returns all pending local ACKs to the
           local end via the Crd_Ack Block and sends a Block_Mode_Chg_ACK to the local data link layer to inform it
           that the Block_Mode_Chg_ACK has been received. Thereafter, the peer data link layer ceases sending any
           DLLCB/DLLDP.

      8.   Upon receiving the Block_Mode_Chg_ACK, the local data link layer sends an encapsulation mode switching
           response to the local physical layer, triggering the local physical layer to perform retraining, while sending
           the Retrain Link Training Block (RLTB) to the peer physical layer. Upon receiving the RLTB, the peer
           physical layer begins retraining. For details about RLTB, see Section 3.4.1.1.

      9.   Once the local physical layer completes retraining, it sends a new mode enabling signal to the local data link
           layer, with similar operations performed at the peer end.

      10. The local data link layer removes the backpressure on the network layer traffic, with similar operations
           performed at the peer end.

      11. The encapsulation mode switching procedure is completed, and the two ends of the link start to
           communicate with each other using the new encapsulation mode.




unifiedbus.com                                                                                                          115
4 Data Link Layer




                           Figure 4-28 Encapsulation mode switching procedure


4.3.3.9 Init Block

During the initialization of data link layer parameters, Init Blocks are sent and received to achieve the
following functions:

      ⚫    In the DLL_Param_Init state, the data link layers at both ends send Init Blocks to each other
           to ensure normal communication.
      ⚫    In the DLL_Param_Init state, the data link layer sends an Init Block that carries initialization
           parameters to notify the peer data link layer of the working mode configured at the local end,
           completing auto-negotiation.




unifiedbus.com                                                                                           116
4 Data Link Layer



The Init Block has a variable length N, ranging from 5 to 32 flits. The first four flits carry basic initialization
parameters, while the last flit contains the BCRC/END field—ensuring a minimum packet length of 5 flits.
Additional flits can be appended as needed to extend initialization parameters. Figure 4-29 to Figure 4-34
show the Init Block formats.

           Byte 0                         Byte 1                       Byte 2                      Byte 3
 7 6 5 4 3          2   1 0     7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
1'b0




        CLENGTH             6'b100000              CFG          CTRL       SUB_CTRL              Reserved

                                       Reserved                                             FEATURE_ID[15:8]
                                                               DATA_ACK_GRAIN_             CTRL_ACK_GRAIN_
       FEATURE_ID[7:0]                Reserved           R
                                                                     SIZE                        SIZE
       FLOW_CTRL_SIZE                                VL_ENABLE                                   Reserved
                 RETRY_BUF_DEPTH                                                   Reserved
                             Figure 4-29 Flit 0 format of an Init Block in CRC mode

           Byte 0                       Byte 1                       Byte 2                       Byte 3
 7 6 5 4 3 2 1 0              7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                    Reserved
                                    CTRL_CREDIT_GRAIN_SIZE[111:80]
                                     CTRL_CREDIT_GRAIN_SIZE[79:48]
                                     CTRL_CREDIT_GRAIN_SIZE[47:16]
          CTRL_CREDIT_GRAIN_SIZE[15:0]                                            Reserved
                             Figure 4-30 Flit 1 format of an Init Block in CRC mode

           Byte 0                       Byte 1                       Byte 2                       Byte 3
 7 6 5 4 3 2 1 0              7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                    Reserved
                                     DATA_CREDIT_GRAIN_SIZE[95:64]
                                     DATA_CREDIT_GRAIN_SIZE[63:32]
                                      DATA_CREDIT_GRAIN_SIZE[31:0]
        CTRL_CREDIT_GRAIN_SIZE[127:112]                                           Reserved
                             Figure 4-31 Flit 2 format of an Init Block in CRC mode




unifiedbus.com                                                                                                  117
4 Data Link Layer



           Byte 0                      Byte 1                     Byte 2                    Byte 3
 7 6 5 4 3 2 1 0            7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                 Reserved
                                                 Reserved
                                                 Reserved
                             PACKET_MIN_INTER
          Reserved                                           DATA_CREDIT_GRAIN_SIZE[127:112]
                                   VAL
       DATA_CREDIT_GRAIN_SIZE[111:96]                                         Reserved
                          Figure 4-32 Flit 3 format of an Init Block in CRC mode

           Byte 0                      Byte 1                    Byte 2                     Byte 3
 7 6 5 4 3 2 1 0            7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                 Reserved
                                                 Reserved
                                                 Reserved
                                                 Reserved
                                                 Reserved
                     Figure 4-33 Flit 4 to flit (N–2) format of an Init Block in CRC mode

           Byte 0                      Byte 1                    Byte 2                     Byte 3
 7 6 5 4 3 2 1 0            7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                 Reserved
                                                 Reserved
                                                 Reserved
                                                 Reserved
                                                   BCRC
                        Figure 4-34 Flit (N–1) format of an Init Block in CRC mode

The fields are described as follows:

      ⚫    CLENGTH: The value is 5'b00100~5'b11111, indicating that the Init Block length is 5 to 32
           flits.
      ⚫    CFG: The value is 4'b0000, indicating that the block is a DLLCB.
      ⚫    CTRL and SUB_CTRL: The values are 4'b1100 and 4'b1000, respectively, indicating that
           the DLLCB type is Init Block. For details about other types, see Table 4-6.
      ⚫    R: RXBUF_VL_SHARE field. For details, see Table 4-8.




unifiedbus.com                                                                                       118
4 Data Link Layer



Flits 0 to 3 of an Init Block carry initialization parameters. Table 4-8 lists all initialization parameters.

                                      Table 4-8 Init Block field information
                                                     Init Block
 Flit ID   Bit ID      Field                      Description
 0         111:88      Reserved                   Reserved. The sender sets this field to 0 by default, and
                                                  the receiver ignores this field.
           87:72       FEATURE_ID                 Protocol version of the data link layer. Set the value to 1
                                                  for this specification.
           71:65       Reserved                   Reserved. The sender sets this field to 0 by default, and
                                                  the receiver ignores this field.
           64          RXBUF_VL_SHARE             Indicates whether the receive buffer supports VL
                                                  sharing. 1'b1: supported; 1'b0: not supported.
           63:56       DATA_ACK_GRAIN_            A DLLDP supports retry buffer space release via the
                       SIZE                       ACK field of the LPH/LBH. The release granularity is
                                                  determined by the negotiated
                                                  DATA_ACK_GRAIN_SIZE value (unit: flit).
                                                  Each bit corresponds to a flit quantity, which are
                                                  {128,64,32,16,8,4,2,1}.
           55:48       CTRL_ACK_GRAIN_            The Crd_Ack Block supports retry buffer space release
                       SIZE                       via the ACK_NUM field. The release granularity is
                                                  determined by the negotiated
                                                  CTRL_ACK_GRAIN_SIZE value (unit: flit).
                                                  Each bit corresponds to a flit quantity, which are
                                                  {128,64,32,16,8,4,2,1}.
           47:40       FLOW_CTRL_SIZE             Number of flits corresponding to a cell (the minimum unit
                                                  for credit-based flow control).
                                                  Each bit corresponds to a flit quantity, which are
                                                  {128,64,32,16,8,4,2,1}.
           39:24       VL_ENABLE                  Supports a maximum of 16 VLs enabled.
                                                  Bit 0 to bit 15 correspond to VL 0 to VL 15, respectively.
                                                  VL 0 SHALL be enabled.
                                                  1'b1: This VL is enabled.
                                                  1'b0: This VL is not enabled.
           23:16       Reserved                   Reserved. The sender sets this field to 0 by default, and
                                                  the receiver ignores this field.
           15:0        RETRY_BUF_DEPTH            Retry buffer depth, in flits.
                                                  This field does not require negotiation and is directly set
                                                  to the received value.
 1         159:112     Reserved                   Reserved. The sender sets this field to 0 by default, and
                                                  the receiver ignores this field.
           111:0       CTRL_CREDIT_GRAI           The Crd_Ack Block supports returning the credits of
                       N_SIZE[111:0]              each VL through the CRD_NUM field. The credit return
                                                  granularity of VL 0 to VL 13 is determined by the
                                                  negotiated CTRL_CREDIT_GRAIN_SIZE[111:0] value




unifiedbus.com                                                                                                  119
4 Data Link Layer



                                           Init Block
 Flit ID   Bit ID    Field              Description
                                        (unit: cell).
                                        Each byte corresponds to the credit return granularity of
                                        a VL, which are
                                        {CTRL_CREDIT_GRAIN_SIZE_VL13,CTRL_CREDIT_
                                        GRAIN_SIZE_VL12,…,CTRL_CREDIT_GRAIN_SIZE_V
                                        L0}.
                                        Each bit in a byte corresponds to a cell quantity, which
                                        are {128,64,32,16,8,4,2,1}.
 2         159:112   Reserved           Reserved. The sender sets this field to 0 by default, and
                                        the receiver ignores this field.

           111:16    DATA_CREDIT_GRA    A DLLDP supports returning the credits of a VL through
                     IN_SIZE[95:0]      the CRD field of the LPH/LBH. The credit return
                                        granularity of VL 0 to VL 11 is determined by the
                                        negotiated DATA_CREDIT_GRAIN_SIZE[95:0] value
                                        (unit: cell).
                                        Each byte corresponds to the credit return granularity of
                                        a VL, which are
                                        {DATA_CREDIT_GRAIN_SIZE_VL11,DATA_CREDIT_GR
                                        AIN_SIZE_VL10,…,DATA_CREDIT_GRAIN_SIZE_VL0}.
                                        Each bit in a byte corresponds to a cell quantity, which
                                        are {128,64,32,16,8,4,2,1}.

           15:0      CTRL_CREDIT_GRAI   The Crd_Ack Block supports returning the credits of
                     N_SIZE[127:112]    each VL through the CRD_NUM field. The credit return
                                        granularity of VL 14 and VL 15 is determined by the
                                        negotiated CTRL_CREDIT_GRAIN_SIZE[127:112]
                                        value (unit: cell).
                                        Each byte corresponds to the credit return granularity of
                                        a VL, which are
                                        {CTRL_CREDIT_GRAIN_SIZE_15,CTRL_CREDIT_GR
                                        AIN_SIZE_14}.
                                        Each bit in a byte corresponds to a cell quantity, which
                                        are {128,64,32,16,8,4,2,1}.

 3         111:40    Reserved           Reserved. The sender sets this field to 0 by default, and
                                        the receiver ignores this field.

           39:32     PACKET_MIN_INTE    Minimum interval allowed between two consecutive
                     RVAL               DLLDPs received by the receiver. The value of this field
                                        indicates the minimum interval between the current
                                        DLLDP (header flit included) and the next DLLDP
                                        (header flit excluded). Unit: flit.
                                        This field does not require negotiation and is directly set
                                        to the received value.

           31:0      DATA_CREDIT_GRA    A DLLDP supports returning the credits of a VL through
                     IN_SIZE[127:96]    the CRD field of the LPH/LBH. The credit return
                                        granularity of VL 12 to VL 15 is determined by the
                                        negotiated DATA_CREDIT_GRAIN_SIZE[127:96] value
                                        (unit: cell).
                                        Each byte corresponds to the credit return granularity of



unifiedbus.com                                                                                     120
4 Data Link Layer



                                                              Init Block
 Flit ID    Bit ID       Field                          Description
                                                        a VL, which are
                                                        {DATA_CREDIT_GRAIN_SIZE_VL15,DATA_CREDIT_
                                                        GRAIN_SIZE_VL14,DATA_CREDIT_GRAIN_SIZE_VL1
                                                        3,DATA_CREDIT_GRAIN_SIZE_VL12}.
                                                        Each bit in a byte corresponds to a cell quantity, which
                                                        are {128,64,32,16,8,4,2,1}.

 4:N-2      159:0        Reserved                       Reserved. The sender sets this field to 0 by default, and
                                                        the receiver ignores this field.
 N-1        159:32       Reserved                       Reserved. The sender sets this field to 0 by default, and
                                                        the receiver ignores this field.


Note: The initialization parameters defined in the protocol SHALL be sent to the peer link layer in the Init Block. It is not
allowed to send only part of the initialization parameters.

For details about the initialization procedure and auto-negotiation process of Init Blocks, see Section 4.4.


4.3.4 DLLCB/DLLDP Sending and Receiving Procedures

4.3.4.1 DLLCB/DLLDP Delimitation

Delimitation occurs at the DLLCB/DLLDP receiver. The physical layer submits the received data to the
data link layer in the unit of flit. After receiving the flits, the data link layer SHALL delimit
DLLCBs/DLLDPs. The delimitation process differs between CRC mode and non-CRC mode.




unifiedbus.com                                                                                                             121
4 Data Link Layer



Figure 4-35 shows the DLLCB/DLLDP delimitation process in CRC mode.




                              Figure 4-35 Delimitation in CRC mode




unifiedbus.com                                                        122
4 Data Link Layer



In this figure:

        ⚫   SOP: Start Of Packet, the first flit of a DLLDP
        ⚫   SOB: Start Of Block, the first flit of a DLLCB/DLLDB
        ⚫   EOP: End Of Packet, the last flit of a DLLDP
        ⚫   EOB: End Of Block, the last flit of a DLLCB/DLLDB

Note:

        ⚫   To ensure successful delimitation, the sender SHALL meet the following requirements:
            (1) DLLDBs from other DLLDPs cannot be inserted into DLLDBs within a DLLDP.
            (2) DLLCBs can only be inserted between DLLDBs.
        ⚫   When FEC decoding fails (with physical-layer FEC enabled) or CRC check fails, the data link
            layer initiates retransmission, instructing the peer end to resend this DLLDB; all
            DLLCBs/DLLDPs received before receiving the Retry_Ack Block, except Retry_Idle Blocks
            and Retry_Req Blocks, are discarded.
        ⚫   After the link is set up at the physical layer, the data link layer first initiates the retransmission
            procedure: the sender sends a retransmission request set until it receives a retransmission
            response set. This retransmission procedure is initiated to prevent DLLCB loss due to
            inconsistent link setup time at the physical layer, which could lead to link setup failure at the
            data link layer. There are no special requirements for this retransmission procedure. For
            details about the retransmission procedure and related sets, see Section 4.7.

Figure 4-36 shows the DLLCB/DLLDP delimitation process in non-CRC mode. As the blocks do not
include the CRC field in non-CRC mode, the retransmission triggering conditions differ. If FEC decoding
fails, the data link layer initiates retransmission and discards the flit corresponding to the current FEC
frame and all subsequent flits. Then it notifies the peer end to start retransmission from the flit
corresponding to the current FEC frame. Other DLLCBs/DLLDPs received before the retransmission
acknowledgment set is received are discarded. The notes are similar to those for the CRC mode. For
details about the retransmission acknowledgment set, see Section 4.7.3.4.




unifiedbus.com                                                                                                123
4 Data Link Layer




                                      Figure 4-36 Delimitation in non-CRC mode


4.3.4.2 Sending Procedure

At the sender, the data link layer encapsulates packets from the network layer as the payload of
DLLDPs. DLLDP encapsulation involves adding the header LPH/LBH, padding (optional), and tail
BCRC/END to the payload, followed by sequentially filling flits with the header, payload, padding
(optional), and tail. For details, see Section 4.3.2.

Flit filling rules are as follows: Start from the first flit and fill each flit in sequence until full. If the last flit cannot
be fully filled with 20 bytes using the payload, use padding set to 0 for any empty space. Figure 4-37 shows
how DLLDPs are sent in CRC mode.




unifiedbus.com                                                                                                             124
4 Data Link Layer




                           Figure 4-37 DLLDP sending procedure (CRC mode)

DLLCBs have a fixed format. For details, see Section 4.3.3. DLLCBs are generated by the data link
layer and delivered to the physical layer.


4.3.4.3 Receiving Procedure

Upon receiving DLLDPs and DLLCBs, the receiver processes them based on the configured mode:

      ⚫    In CRC mode, the receiver evaluates both the physical-layer FEC decoding status (if FEC is
           enabled) and the CRC check result at the data link layer. If either the FEC decoding or CRC
           check fails, the data link layer initiates the retransmission process.
      ⚫    In non-CRC mode, only the physical-layer FEC decoding status is assessed at the data link
           layer. If FEC decoding fails, the retransmission process is triggered accordingly.

After successful validation, the receiver identifies the header type (LCH, LPH, or LBH) from the
delimitation and length fields and parses it accordingly.

For a DLLDP, the receiver determines the payload boundaries from the PLENGTH field in the DLLDP,
discards the padding (if any), and sends the payload to the network layer. For a DLLCB, the data link
layer performs subsequent link management and control, and there is no need to send the block
(except Param_Exchg Block) to the network layer.


4.4 Initialization Auto-negotiation
Upon detecting link setup at the physical layer, the data link transitions from the DLL_Disabled state to
the DLL_Param_Init state for initialization. For details, see Section 4.2.

In the DLL_Param_Init state, the data link layer exchanges Init Blocks to complete the handshake,
exchange initialization parameters, and ensure continued communication. During auto-negotiation, both
ends of the link can send Init Blocks in any sequence upon entering the DLL_Param_Init state.

If Init Blocks are discarded due to bit errors during transmission, the data link layer can retransmit the
Init Blocks through the retransmission mechanism to ensure correct Init Block reception.




unifiedbus.com                                                                                           125
4 Data Link Layer



During initialization, the data link layer checks the capabilities of the peer data link layer through Init
Blocks. After negotiation, both data link layers use same working parameters and work in same mode.
Table 4-9 lists the negotiation rules.

                    Table 4-9 Auto-negotiation rules for initialization at the data link layers
                                                                          Negotiation Rule
 Field               Description
                                                                          (See the following example)
 DATA_CREDIT         Credit return granularity of VL 0 to VL 15 in        The negotiation result is
 _GRAIN_SIZE         the LPH/LBH field of the DLLDP header                determined by the smallest value in
                     (unit: cell).                                        the intersection of the credit return
                     Each byte corresponds to the credit return           granularities supported by both
                     granularity of a VL, which are                       ends.
                     {DATA_CREDIT_GRAIN_SIZE_VL
                     15,DATA_CREDIT_GRAIN_SIZE_VL14,…,
                     DATA_CREDIT_GRAIN_SIZE_VL0}.
                     Each bit corresponds to a cell quantity,
                     which are {128,64,32,16,8,4,2,1}.
 CTRL_CREDIT         Credit return granularity of VL 0 to VL 15 in        The negotiation result is
 _GRAIN_SIZE         Crd_Ack Blocks (unit: cell).                         determined by the smallest value in
                     Each byte corresponds to the credit return           the intersection of the credit return
                     granularity of a VL, which are                       granularities supported by both
                     {CTRL_CREDIT_GRAIN_SIZE_VL15,CTR                     ends.
                     L_CREDIT_GRAIN_SIZE_VL14,…,CTRL_C
                     REDIT_GRAIN_SIZE_VL0}.
                     Each bit corresponds to a cell quantity,
                     which are {128,64,32,16,8,4,2,1}.
 FEATURE_ID          Protocol version of the data link layer. Set         After negotiation, the lower protocol
                     the value to 1 for this specification.               version is adopted as the common
                                                                          operating mode for both ends.
 RXBUF_VL_S          Indicates whether the receive buffer                 If the peer receive buffer does not
 HARE                supports VL sharing.                                 support VL sharing, the local
                     1'b1: supported.                                     sender uses the credit exclusive
                                                                          mode for credit-based flow control.
                     1'b0: not supported.                                 If the peer receive buffer supports
                                                                          VL sharing, the local sender can
                                                                          use either the credit exclusive or
                                                                          sharing mode for credit-based flow
                                                                          control.
 DATA_ACK_G          ACK return granularity in the LPH/LBH (unit:         The negotiation result is
 RAIN_SIZE           flit).                                               determined by the smallest value in
                     Each bit corresponds to a flit quantity, which       the intersection of the ACK return
                     are {128,64,32,16,8,4,2,1}.                          granularities supported by both
                                                                          ends.
 CTRL_ACK_G          ACK return granularity in Crd_Ack Blocks             The negotiation result is
 RAIN_SIZE           (unit: flit).                                        determined by the smallest value in
                     Each bit in a byte corresponds to a flit             the intersection of the ACK return
                     quantity, which are {128,64,32,16,8,4,2,1}.          granularities supported by both
                                                                          ends.
 FLOW_CTRL_          Number of flits corresponding to a cell (the         The negotiation result is
                                                                          determined by the smallest value in



unifiedbus.com                                                                                                126
4 Data Link Layer



                                                                                    Negotiation Rule
 Field                  Description
                                                                                    (See the following example)
 SIZE                   minimum unit for credit-based flow control).                the intersection of the cell
                        Each bit corresponds to a flit quantity, which              granularities supported by both
                        are {128,64,32,16,8,4,2,1}.                                 ends.

 VL_ENABLE              Supports a maximum of 16 VLs enabled.                       The VLs supported at both ends
                        Bits 0 to 15 correspond to VLs 0 to 15,                     are numbered consecutively
                        respectively. VL 0 SHALL be enabled.                        starting from 0. The enabled VLs
                        1'b1: The VL can be used.                                   are the intersection of the
                                                                                    supported VLs at both ends.
                        1'b0: The VL cannot be used.


Before devices are delivered, device capabilities are recorded in the Data Link Capability register. For
details about the register definition, see Appendix D.6.2.1. The content of this register is read-only and
cannot be modified by users. During the initialization auto-negotiation between the two ends, the
working mode to be negotiated is recorded in the Data Link Configuration register. For details about the
register definition, see Appendix D.6.2.2. After the auto-negotiation is completed at both ends, the
capabilities to be enabled are recorded in the Data Link Status register. The Data Link Status register is
used to record the real-time link status. For details about the register definition, see Appendix D.6.2.3.
The content of this register is read-only and cannot be modified by users; it can only be updated and
maintained by the hardware in real time.

To ensure successful initialization auto-negotiation, the data link layer SHALL have the following
capabilities, which are supported by hardware by default and require no software configuration:

       ⚫     Credit return granularity for Crd_Ack Blocks: 1 cell
       ⚫     Credit return granularity for DLLDPs: 4 cells
       ⚫     ACK return granularity for Crd_Ack Blocks: 1 flit
       ⚫     ACK return granularity for DLLDPs: 32 flits
       ⚫     Processing a cell (the minimum unit for credit-based flow control) as 8 flits
       ⚫     DLLDP transmission through VL 0, that is, VL_ENABLE[0] = 1'b1

Example: negotiation

The following uses FLOW_CTRL_SIZE negotiation as an example. The FLOW_CTRL_SIZE granularity is set to 8 flits
by default. This value can be reconfigured by software as needed to suit specific requirements.

Assume that DL 0 is set to {32,16} and DL 1 is set to {64,32,16}. The negotiated value of FLOW_CTRL_SIZE is 16. If DL
0 is set to {32} and DL 1 is set to {16}, the negotiation fails. The default working mode is used, and the value of
FLOW_CTRL_SIZE is 8.

If initialization auto-negotiation of each field at the data link layer fails, the default working mode is as follows:

       1.    DATA_CREDIT_GRAIN_SIZE = 0x04040404040404040404040404040404 (In 16 VLs, the credit return
             granularity of each VL in a DLLDP is 4 cells.)




unifiedbus.com                                                                                                           127
4 Data Link Layer



      2.   CTRL_CREDIT_GRAIN_SIZE = 0x01010101010101010101010101010101 (In 16 VLs, the credit return
           granularity of each VL in a Crd_Ack Block is 1 cell.)

      3.   FEATURE_ID = 0x0001 (The value is 1 for this specification.)

      4.   RXBUF_VL_SHARE = 0x0 (The receive buffer does not support credit sharing.)

      5.   DATA_ACK_GRAIN_SIZE = 0x20 (The ACK return granularity of the DLLDP is 32 flits.)

      6.   CTRL_ACK_GRAIN_SIZE = 0x01 (The ACK return granularity of the Crd_Ack Block is 1 flit.)

      7.   FLOW_CTRL_SIZE = 0x08 (One credit is 8 flits, that is, one cell is 8 flits.)

      8.   VL_ENABLE = 0x1 (VL 0 is enabled, and other VLs are disabled.)



4.5 VL Mechanism

4.5.1 VL Introduction
VL is a mechanism for providing multiple logical communication channels over a single physical
channel. Each point-to-point link at the data link layer supports a maximum of 16 VLs. Credit-based flow
control is implemented based on VLs. All DLLDBs within a DLLDP are transmitted on the same VL.
Different DLLDPs may use different VLs. DLLDPs within the same VL are transmitted in a first-come,
first-served (FCFS) manner. The transmission order across different VLs is determined by the specific
scheduling algorithm implemented.

DLLCBs do not consume credits, and therefore no VLs need to be specified for transmitting DLLCBs.


4.5.2 VL ID
When a DLLDP is transmitted at the data link layer, an LPH.VL and an LBH.VL of the DLLDP are used
to represent VLs corresponding to the DLLDP.


4.6 Credit-based Flow Control Mechanism

4.6.1 Credit Initialization

4.6.1.1 Credit Introduction

The data link layer supports credit-based flow control. The receiver of each link allocates a certain
number of credits to the sender based on the receive buffer size and initialization parameters. Credit-
based flow control is implemented on the sender to prevent DLLDP loss due to buffer overflow at the
receiver. The basic unit of credit-based flow control is cell, where one cell corresponds to one or
multiple flits. The exact correspondence is negotiated during parameter initialization by both ends of the
link. For details, see Section 4.4.




unifiedbus.com                                                                                          128
4 Data Link Layer



Before transmitting DLLDPs on each link, the data link layer sends a Crd_Ack Block to notify the peer
end of its local receive buffer capacity. This process is completed in the DLL_Credit_Init state.

After initialization auto-negotiation is completed on each link of the data link layer, some or all VLs are
enabled. VL 0 is enabled by default, and whether to enable other VLs is determined based on the
initialization auto-negotiation result. Credits can be used in exclusive or sharing mode. Whether the
credit sharing mode is enabled is determined during initialization auto-negotiation. For the details about
initialization auto-negotiation, see Section 4.4


4.6.1.2 Credit Exclusive Mode

Before credit initialization, both ends complete an initialization process using the Init Block. During this
process, both ends negotiate the VLs to be enabled, the cell granularity, and the credit exclusive mode.
The local end determines the number of supported credits based on the receive buffer size and cell
granularity, and then allocates an exclusive credit to each enabled VL according to the management
plane's policy, ensuring each VL uses its own credit. Finally, both ends exchange initialized credits via
the Crd_Ack Block to finalize the initialization.

Example: credit exclusive mode

Assume that the local receive buffer is 1 MB. The initialization auto-negotiation result is as follows:

       ⚫   Nine VLs from VL 0 to VL 8 are enabled after the initialization auto-negotiation.
       ⚫   1 cell = 8 flits after the initialization auto-negotiation.
       ⚫   The local receive buffer space cannot be shared by VLs. That is, each VL independently occupies a dedicated
           portion of the receive buffer space.

Based on the preceding initialization auto-negotiation result, the total number of initialized credits SHALL be 6553 cells: 1
MB/(8 x 20 bytes); the calculation result is rounded down to prevent receive buffer overflow. The user allocates these
6553 cells to nine VLs based on the actual requirements, with initial credit values ranging from INIT_CRD0 to
INIT_CRD8. In principle, the total number of INIT_CRD0 + INIT_CRD1 +…+ INIT_CRD8 cannot exceed 6553 cells. The
specific allocation policy can be tailored to the actual scenario.

Upon credit return, each VL receives its respective credits, maintaining independent credits.


4.6.1.3 Credit Sharing Mode

During initialization auto-negotiation, the two ends of the link negotiate to use the credit sharing mode.
In this mode, initialization follows a process similar to credit exclusive mode. The difference is that in
credit sharing mode, all received credits are summed into the shared credit counter SHARE_CRD.

To avoid credit starvation, it is necessary to allocate exclusive credits to VLs in credit sharing mode.
That is, some credits from SHARE_CRD are allocated as exclusive credits to enabled VLs according to
the policies configured on the management plane. These exclusive credits cannot be used by other
VLs, and the number of exclusive credits is determined based on actual scenarios.

Once credit initialization is complete, any credits returned from the peer end are summed into
SHARE_CRD, after which the system verifies whether each VL's exclusive credits match the initially




unifiedbus.com                                                                                                           129
4 Data Link Layer



allocated amount. If a deficit is detected, the system replenishes credits according to a preconfigured
sequence, for example, setting a priority of replenishing credits for VLs.

Compared to credit exclusive mode, sharing credits among VLs enhances resource utilization of the
receive buffer. The sender can dynamically adjust the number of credits for each VL based on its traffic,
improving transmission performance.

Example: credit sharing mode

Assume that the local receive buffer is 1 MB. The initialization auto-negotiation result and management plane
configuration are as follows:

       ⚫   VL 0 and VL 1 are enabled after the initialization auto-negotiation.
       ⚫   1 cell = 8 flits after the initialization auto-negotiation.
       ⚫   The local end negotiates with the peer end to enable the credit sharing mode.
       ⚫   On the peer end, the exclusive credit quantity allocated to VL 0 and VL 1 each is set to 128 cells. The specific
           credit allocation can be designed based on the actual scenario.

Based on the preceding result, the total number of initialized credits is 6553 cells: 1 MB/(8 x 20 bytes). The peer end
sums all credits to the shared credit counter SHARE_CRD and allocates credits exclusively to VL 0 and VL 1. After the
initial credit allocation is complete, the values of the counters are as follows:

       ⚫   The value of the exclusive credit counter for VL 0 is 128.
       ⚫   The value of the exclusive credit counter for VL 1 is 128.
       ⚫   The SHARE_CRD value is 6297.

In the preceding example, when DLLDPs are sent, shared credits are used preferentially by each VL. If shared credits
are insufficient, the credits exclusively allocated to the VLs are utilized without waiting for returns of shared credits.

Assume that the remaining shared credits amount to 64 cells, while DLLDPs to be sent by VL 1 require 128 cells. Since
shared credits are insufficient, 64 cells from VL 1's exclusive credits SHALL be used to complete the allocation.

Upon credit return, all credits are summed into SHARE_CRD, after which the system verifies whether each VL has
sufficient exclusive credits, that is, whether the counter value is 128. If a deficit is detected, exclusive credits are
replenished accordingly. The sequence of replenishing depends on the actual scenario.



4.6.2 Credit-based Flow Control Process
Figure 4-38 shows the credit-based flow control process at the data link layer.




                                      Figure 4-38 Credit-based flow control process




unifiedbus.com                                                                                                               130
4 Data Link Layer



The credit-based flow control process (in credit exclusive mode) at the data link layer is as follows:

        1.   When DL 1 is in the DLL_Credit_Init state, the TX of DL 1 sends the Crd_Ack Block to
             allocate initial credits to each VL of DL 0. The total number of credits corresponds to the
             space size of the receive buffer.
        2.   DL 0 maintains a per-VL credit counter representing the peer's available receive buffer
             space. When the RX obtains a DLLCB or DLLDP that returns credits, the credit counter is
             incremented by the corresponding credit quantity. Conversely, when the TX sends a DLLDP,
             the credit counter is decremented by the number of credits consumed by that DLLDP. DL 0
             can transmit DLLDPs to DL 1 and write them into the receive buffers of DL 1's corresponding
             VLs only when sufficient credits are available for those VLs.
        3.   After reading the DLLDPs from the receive buffer, DL 1 releases the corresponding credits. It
             embeds the number of released credits into the DLLDP or Crd_Ack Block to be sent to DL 0,
             thereby returning the credits to the corresponding VLs of DL 0.
        4.   After receiving the released credits, DL 0 adds the credits to the credit counter of the
             corresponding VL.

Note:

        1.   The basic unit of the credit is cell: 1 cell = n x flits. The value of n is determined by the FLOW_CTRL_SIZE
             field in the Init Block. The value range of n is {1,2,4,8,16,32,64,128}.

        2.   The maximum number of credits supported by credit-based flow control is 65,535 cells. This number refers
             to the total number of credits that can be allocated to all enabled VLs. The number of actually used credits is
             determined based on the hardware capability and negotiation result.

        3.   The number of credits consumed by DLLDPs is calculated as follows: Number of flits in the DLLDP/Number
             of flits in one cell (rounded up). To prevent abnormal credit quantity, the calculation methods of consumed
             and returned credits SHALL be the same.

        4.   When credits are returned to the VLs corresponding to the sender through the CRD and CRD_VL fields in
             the LPH/LBH, the return granularity of the CRD is m x cells. The value of m is negotiated by the
             DATA_CREDIT_GRAIN_SIZE field in the Init Block. The value range of m is {1,2,4,8,16,32,64,128}.

        5.   When credits are returned to the VLs corresponding to the sender through the CRD_NUM[95:0] field of the
             Crd_Ack Block, the return granularity of the CRD is k x cells. The value of k is determined by the
             CTRL_CREDIT_GRAIN_SIZE field in the Init Block. The value range of k is {1,2,4,8,16,32,64,128}.

This credit-based flow control mechanism enables the sender to monitor the remaining available space
of the receive buffer at the receiver in real time, preventing receive buffer overflow. The receiver, in turn,
proactively applies backpressure regardless of link latency.


4.6.3 Credit Return Rules
Credits can be returned to the peer end through the LPH/LBH field of the DLLDP and Crd_Ack Blocks.
The return rules for the credit exclusive mode are consistent with those for the credit sharing mode. The
return rules are as follows:



unifiedbus.com                                                                                                          131
4 Data Link Layer



      1.   The receiver maintains a counter to record the number of credits pending return. Once its
           count reaches the return granularity, credits are sent to the peer end via the LPH/LBH fields
           of the DLLDPs, provided the local end has DLLDPs to send. If the CRD fields of multiple
           LPHs/LBHs in a DLLDP are set to 1, multiple credits are returned.
      2.   If the sender of the local end has no DLLDPs to transmit but has pending credits to return, it
           sends a Crd_Ack Block to the peer end.
      3.   When the number of credits pending return at the local end reaches a predefined threshold
           (configured per VL based on actual scenarios), backpressure SHALL be applied to the
           DLLDP send channel, effectively exerting backpressure on the network layer. At the same
           time, Crd_Ack Blocks SHALL be forcibly sent to promptly return credits to the peer end. This
           prevents the performance of the peer end from being affected when the local sender fails to
           return sufficient credits to the peer end via the LPH/LBH fields of the DLLDP. Additionally, to
           minimize the impact of sending Crd_Ack Blocks on transmission performance, the configured
           LPH/LBH credit return granularity SHALL meet the bandwidth line rate requirements during
           initial negotiation.


4.7 Bit Error Detection and Retransmission Mechanism

4.7.1 Retransmission Triggering Mode
To ensure reliable DLLCB/DLLDP transmission on links, the data link layer supports retransmission in
both non-CRC and CRC modes.

In CRC mode, the data link layer adds the BCRC field to blocks at the sender. This field contains the
CRC information of blocks. The sender backs up sent blocks (except Null Blocks and Retry Blocks) in
the retry buffer. Upon receiving a block, the receiver determines the physical-layer FEC decoding status
(if physical-layer FEC is enabled). If FEC decoding succeeds, it proceeds with CRC check. If FEC
decoding fails or CRC check fails, it issues a retransmission request, triggering the data link layer at the
sender to perform retransmission. For details about the CRC check process, see Section 4.7.2.

In non-CRC mode, upon receiving a block, the data link layer at the receiver detects the physical-layer
FEC decoding status. If FEC decoding fails, it issues a retransmission request, triggering the data link
layer at the sender to perform retransmission.


4.7.2 CRC Check
In CRC mode, the sender calculates the CRC for a DLLDB, and the result of the CRC calculation is
carried in the BCRC field. The receiver then calculates the CRC of the received DLLDB and performs a
comparison and verification against the BCRC.CRC30 field contained within the block.

BCRC consists of 2 information bits (bit[31]: reserved; bit[30]: ERROR_FLAG, indicating transmission
errors) and 30 bits of CRC30. The CRC polynomial is: x30 + x28 + x26 + x24 + x23 + x21 + x19 + x16 + x14 +
x11 + x9 + x7 + x6 + x4 + x2 + 1.




unifiedbus.com                                                                                          132
4 Data Link Layer



Where:

      ⚫     The initial value of CRC calculation is all 1s.
      ⚫     When calculating the CRC based on the DLLDB, the bit order follows Byte 0-Bit 7, then Byte
            0-Bit 6. For detailed information on the CRC bit order, see Figure 4-39.
      ⚫     The CRC calculation result does not need to be inverted.
      ⚫     The bit order of the CRC calculation result matches that of the CRC30 field, so no reordering
            is required.
      ⚫     CRC30 covers all the data before the CRC30 field in the DLLDB.




                                     Figure 4-39 Bit order in CRC calculation


4.7.3 Retransmission Mechanism

4.7.3.1 Overview

The data link layer backs up sent blocks to the retry buffer (see Section 4.7.3.2) at the sender. It
performs retransmissions upon CRC check errors or FEC decoding failures at the receiver. Utilizing the
Go-Back-N retransmission mechanism, it retransmits the first flit associated with the block where a
CRC error was detected or the frame that failed FEC decoding, along with all subsequent flits stored in
the retry buffer following that particular flit.

In the DLL_Param_Init state, the receiver obtains the retry buffer depth RETRY_BUF_DEPTH through
Init Blocks (see Section 4.3.3.9). Using this depth, the receiver calculates and maintains RcvPtr (see
Section 4.7.3.2.2), which indicates the position of the flit to be received by the local end in the retry
buffer of the peer end. Each flit corresponds to a unique number.

Throughout the retransmission process, retransmission is initiated by the receiver. The receiver's
processing flow, known as the receiver retransmission process, is governed by the retransmission
request state machine (see Section 4.7.3.3). The sender responds to the retransmission request by
retransmitting flits backed up in the retry buffer. This operation, known as the sender retransmission
process, is governed by the retransmission acknowledgment state machine (see Section 4.7.3.4).




unifiedbus.com                                                                                              133
4 Data Link Layer



4.7.3.2 Retry Buffer Management

4.7.3.2.1 Retry Buffer Number and Content

Retry buffers are buffers at the sender and are used to store flits that have been sent but have not been
acknowledged. The lowest address is numbered 0, the highest address is numbered
RETRY_BUF_DEPTH – 1, and any address in the space is represented as an offset relative to 0, in the
unit of flit.

When receiving a retransmission request, the sender resends the corresponding backup flits from the
retry buffer using the information provided in the request to ensure reliable transmission at the data
link layer.

Flits backed up in the retry buffer are from DLLDPs and DLLCBs (except Null Blocks and Retry Blocks).


4.7.3.2.2 Retry Buffer Space Management Parameters

The data link layer manages the retry buffer space using the following control parameters (unit: flit):

        ⚫       NumFreeBuf: free space of the retry buffer. After successfully receiving an ACK (returned
                through the ACK field of the LPH/LBH by the DLLDP or returned through the ACK_NUM
                field by the Crd_Ack Block), the local end calculates the number of flits to be released in the
                local retry buffer space (ReleaseSize) based on the ACK type and granularity. If
                NumFreeBuf + ReleaseSize ≤ RETRY_BUF_DEPTH, NumFreeBuf = NumFreeBuf +
                ReleaseSize. Otherwise, the ACK overflow handling is triggered. For details about overflow
                handling, see Section 4.8.2. When a block of SendSize flits attempts to be sent, the sending
                is allowed only if NumFreeBuf ≥ SendSize and NumFreeBuf = NumFreeBuf – SendSize is
                updated. When the local end successfully receives an ACK or backs up the block to the retry
                buffer, the local end verifies NumFreeBuf. If no overflow exception occurs and the sending
                conditions are met, the local end modifies the WrPtr and TailPtr parameters.
        ⚫       WrPtr: location where the latest sent flit is backed up to the retry buffer. When the local end
                sends a flit to be backed up, the flit is written to the WrPtr address of the retry buffer. If WrPtr
                + 1 == RETRY_BUF_DEPTH, WrPtr is reset to 0. Otherwise, WrPtr = WrPtr + 1 and the
                new flit is backed up.
        ⚫       TailPtr: start position of all flits in the retry buffer for which ACKs are to be returned. After
                receiving an ACK, the local end calculates the number of flits to be released (ReleaseSize)
                based on the ACK type and granularity. If TailPtr + ReleaseSize ≥ RETRY_BUF_DEPTH,
                TailPtr = TailPtr + ReleaseSize – RETRY_BUF_DEPTH. Otherwise, TailPtr = TailPtr +
                ReleaseSize.
        ⚫       RdPtr: location of the next flit pending retransmission in the retry buffer. When a
                retransmission request is received, RdPtr is set to the value of RcvPtr carried in the
                retransmission request. Each time a flit is read and sent, if RdPtr + 1 ==
                RETRY_BUF_DEPTH, RdPtr = 0. Otherwise, RdPtr == RdPtr + 1. When RdPtr == WrPtr,
                no data is available at the location specified by RdPtr, and retransmission will not occur.




unifiedbus.com                                                                                                      134
4 Data Link Layer



      ⚫    RcvPtr: location of the flit pending receiving by the block receiver in the retry buffer of the peer
           end. When the retransmission request state machine (Retry_Req_SM; see Section 4.7.3.3) is
           in the normal state: In CRC mode, the value of RcvPtr increases by ReceivedSize each time
           a DLLDB with ReceivedSize flits is received; In non-CRC mode, RcvPtr increases by 1 for
           each correct flit received and ReceivedSize == 1. If RcvPtr + ReceivedSize ≥
           RETRY_BUF_DEPTH, RcvPtr = RcvPtr + ReceivedSize – RETRY_BUF_DEPTH.
           Otherwise, RcvPtr = RcvPtr + ReceivedSize. If a CRC error or FEC decoding failure occurs,
           the block receiver notifies the peer end to retransmit the data according to the Go-Back-N
           mechanism from RcvPtr using the Retry_Req Block carrying RcvPtr.

RcvPtr is maintained by the retransmission initiator (data receiver). WrPtr, TailPtr, RdPtr, and
NumFreeBuf are maintained by the retransmission responder. When the link state machine enters the
DLL_Disabled state, the retry buffer space management parameters are initialized. The initial values of
RcvPtr, WrPtr, TailPtr, and RdPtr are all 0, and the initial value of NumFreeBuf is
RETRY_BUF_DEPTH.

Figure 4-40 shows retry buffer space management. Addr Number indicates a flit. RETRY_BUF_DEPTH
is N, WrPtr is N–2, and TailPtr is 2. The white part indicates the free space of the retry buffer, and the size
is NumFreeBuf. The gray part indicates the occupied space of the retry buffer.




                                Figure 4-40 Retry buffer space management




unifiedbus.com                                                                                              135
4 Data Link Layer



4.7.3.2.3 Retry Buffer Space Release

In CRC mode, if physical-layer FEC decoding for DLLDBs of a DLLDP is successful (with physical-layer
FEC enabled), the CRC check passes, and the DLLDBs are correctly received by the local end; or in
non-CRC mode, if physical-layer FEC decoding for flits in a DLLDP is successful and the flits are
correctly received by the local end, one of the following methods can be used to notify the peer end to
release the corresponding retry buffer space:

      ⚫    Transmitting ACKs together with DLLDPs: Set the LPH.ACK field of the DLLDP in the
           transmit direction of the local end or the LBH.ACK field of the DLLDB in the DLLDP to notify
           the peer end to release the retry buffer space of DATA_ACK_GRAIN_SIZE flits.
      ⚫    Using the ACK mechanism based on Crd_Ack Blocks: Send a Crd_Ack Block and use the
           ACK_NUM field of the block to instruct the peer end to release retry buffer space of
           ACK_NUM x CTRL_ACK_GRAIN_SIZE flits.


4.7.3.2.4 Retry Buffer Lockout Prevention

ACK-carrying blocks are backed up in the sender's retry buffer before transmission. This buffer space is
released only after the receiver receives the corresponding ACK-carrying blocks. Consequently, the
retry buffers at both the sender and receiver may become interlocked.

For instance, under high bit error rate conditions at the data link layer, both ends may be unable to
return ACKs promptly, preventing buffer release. As a result, the retry buffers at both ends become full,
blocking new packet transmissions. In this state, ACKs to be returned accumulate locally but cannot be
sent, and no ACK-carrying blocks are backed up in the retry buffer. This leads to mutual link lock at the
data link layer, halting communication.

To avoid this issue, a threshold is defined in the retry buffer to prioritize the sending of Crd_Ack
Blocks to prevent such interlocks between the two ends of the link. When the value of NumFreeBuf
of the retry buffer is less than the threshold, the transmission of DLLDPs and other DLLCBs is halted,
prioritizing the sending of the Crd_Ack Block to notify the peer to free up the retry buffer. This ensures
that an ACK-carrying Crd_Ack Block is always backed up in the retry buffer, thereby resolving the
interlock issue.


4.7.3.3 Retransmission Request State Machine (RETRY_REQ_SM)

When the CRC check or physical-layer FEC decoding for a received block fails in CRC mode, or
physical-layer FEC decoding for flits fails in non-CRC mode, the block receiver initiates a data link layer
retransmission request. The retransmission request state machine manages the retransmission process
at the local end. Figure 4-41 shows the retransmission request state machine.




unifiedbus.com                                                                                          136
4 Data Link Layer




                             Figure 4-41 Retransmission request state machine

The retransmission request state machine has five states, defined as follows:

      ⚫   NORMAL: normal state. In this state, blocks are sent and received normally. If a CRC check
          failure, FEC decoding failure, or physical layer retraining occurs, the state transition is
          triggered. (A physical layer retraining flag bit is provided to the data link layer. The data link
          layer enters the RETRAIN state based on the flag bit. For details, see Section 3.4.3.)
          In this state, the value of the NUM_RETRY counter is set to 0 to record the number of
          retransmission requests initiated before the physical layer retraining in the same
          retransmission event (the counter is cleared and re-counted after the physical layer
          retraining). The value of the NUM_PHY_REINIT counter is set to 0 to record the number of
          physical layer retraining times.
      ⚫   REQ: retransmission request set sending state. In this state, the system determines whether
          the conditions for entering the RETRAIN state are met. If the conditions are not met, the
          system sends a retransmission request set to the peer end. The requirements are as follows:
          (1) To ensure that the peer end correctly identifies the retransmission request, 1 Retry_Idle
                 Block and 32 Retry_Req Blocks (namely 1 Retry_Req_Set) SHALL be sent continuously.
                 Failure to do so may result in DLLDPs and retransmission requests being misidentified.
          (2) In this state, the data link layer supports only the following DLLCBs: Retry_Idle Block,
                 Retry_Req Block, and Retry_Ack Block. Other DLLCBs/DLLDPs are discarded.
          (3) The value of NUM_RETRY is increased by 1 each time the system enters the REQ
                 state. When the value of NUM_RETRY is equal to the value of
                 NUM_RETRY_THRESHOLD or the physical layer is being retrained, the state
                 transitions to RETRAIN and the value of NUM_RETRY is reset to 0.
      ⚫   WAIT: waiting for a retransmission acknowledgment. In this state, the local end waits for a
          retransmission acknowledgment set from the peer end. Pay attention to the following:




unifiedbus.com                                                                                             137
4 Data Link Layer



            (1) In this state, the data link layer supports only the following DLLCBs: Retry_Idle Block,
                 Retry_Req Block, and Retry_Ack Block. Other DLLCBs/DLLDPs are discarded.
            (2) In this state, a timeout counter is set. State transition to REQ is triggered when the timer
                 value exceeds the threshold. It is RECOMMENDED that the timeout counter threshold
                 be greater than twice the link delay and the value range from 1 μs to 10s.
      ⚫     RETRAIN: In this state, the data link layer determines whether the conditions for entering the
            ERROR state are met. If the conditions are not met, the data link layer sends a retrain
            command to the physical layer and waits until physical layer retraining is successful. If the
            physical layer does not respond to the retrain command for a long time, the physical layer
            reports LinkUp==1'b0, and the data link layer restores to the DLL_Disabled state.
            (1) Each time the data link layer enters the RETRAIN state, the value of the
                 NUM_PHY_REINIT counter is incremented by 1. When the value of NUM_PHY_REINIT
                 is equal to that of NUM_PHY_REINIT_THRESHOLD, the data link layer is switched to
                 the ERROR state and the value of NUM_PHY_REINIT is reset to 0.
            (2) In this state, the data link layer cannot send or receive blocks.
      ⚫     ERROR: In this state, the data link layer cannot send or receive blocks, and an error is
            reported. After a reset by UB Fabric Manager (UBFM), the retransmission request state
            machine returns to the NORMAL state.

Example: threshold setting

It is RECOMMENDED that NUM_RETRY_THRESHOLD be set to 15 and NUM_PHY_REINIT_THRESHOLD be set to 4.
Other values can be set based on the actual scenario.

The state transition rules are as follows:

      ⚫     Conditions for entering the NORMAL state:
            (1) The link is reset.
            (2) In the WAIT state, the local end receives retransmission acknowledgment sets from the
                 peer end.
      ⚫     Conditions for entering the REQ state:
            (1) In the NORMAL state, the CRC check for blocks or physical-layer FEC decoding for
                 flits fails.
            (2) In the WAIT state, the retransmission acknowledgment set times out.
            (3) In the RETRAIN state, the physical layer retraining is successful.
      ⚫     Conditions for entering the WAIT state:
            −   In the REQ state, the retransmission request set is sent.
      ⚫     Conditions for entering the RETRAIN state:
            (1) In the NORMAL state, the physical layer starts retraining.
            (2) In the REQ state, the retransmission counter NUM_RETRY ==
                 NUM_RETRY_THRESHOLD or the physical layer starts retraining.
            (3) In the WAIT state, the physical layer starts retraining.




unifiedbus.com                                                                                           138
4 Data Link Layer



      ⚫    Conditions for entering the ERROR state:
           −   In the RETRAIN state, the retraining counter NUM_PHY_REINIT ==
               NUM_PHY_REINIT_THRESHOLD.

The Retry Req Status field in the Data Link State Machine Status register indicates the state of the
retransmission request state machine. For details, see Appendix D.6.2.3.


4.7.3.4 Retransmission Acknowledgment State Machine (RETRY_ACK_SM)

After receiving a retransmission request, the sender's retransmission process starts. The
retransmission acknowledgment state machine sends retransmission acknowledgment sets and blocks
marked for retransmission. Figure 4-42 shows the state machine.




                        Figure 4-42 Retransmission acknowledgment state machine

The retransmission acknowledgment state machine has the following two states:

      ⚫    NORMAL: normal state. In this state, blocks are sent and received normally. If a
           retransmission request set is received, state transition is triggered.
      ⚫    ACK: retransmission acknowledgment set and block sending state. In this state, only
           retransmission acknowledgment sets and blocks marked for retransmission can be sent,
           while incoming blocks can still be received normally. To ensure that the peer end correctly
           identifies the retransmission acknowledgment sets, 1 Retry_Idle Block and 32 Retry_Ack
           Blocks (namely 1 Retry_Ack_Set) SHALL be sent continuously. Failure to do so may result in
           DLLDPs and retransmission acknowledgment sets being misidentified.

The state transition rules are as follows:

      ⚫    Conditions for entering the NORMAL state:
           (1) The link is reset.
           (2) In the ACK state, a Retry_Ack_Set and blocks marked for retransmission are sent.



unifiedbus.com                                                                                           139
4 Data Link Layer



      ⚫    Conditions for entering the ACK state:
           (1) In the NORMAL state, a Retry_Req_Set is received.
           (2) In the ACK state, a Retry_Req_Set is received from the peer end while the
                 corresponding block is being sent.

The Retry Ack Status field in the Data Link State Machine Status register indicates the state of the
retransmission acknowledgment state machine. For details, see Appendix D.6.2.3.


4.7.3.5 Retransmission Process

The complete retransmission process is implemented by the RETRY_ACK_SM at the block sender and
the RETRY_REQ_SM at the block receiver. Figure 4-43 and Figure 4-44 show the normal
retransmission process and Retry_Req_Set retransmission process upon timeout, respectively. The
CRC mode is used in this example.




                                Figure 4-43 Normal retransmission process

Figure 4-43 shows the normal retransmission process:

      1.   DL 0 sends DLLDBs 0 to n to DL 1 in sequence, and the RETRY_ACK_SM is in the
           NORMAL state.
      2.   After DLLDB 0 reaches DL 1, DL 1 fails to perform physical-layer FEC decoding (with
           physical-layer FEC decoding enabled) or CRC check on DLLDB 0. The RETRY_REQ_SM
           state machine of DL 1 transits from the NORMAL state to the REQ state. DLLDB 0 and
           subsequently received DLLDBs 1 to n are all discarded.
      3.   DL 1 sends a Retry_Req_Set and enters the WAIT state.




unifiedbus.com                                                                                         140
4 Data Link Layer



      4.   After receiving the Retry_Req_Set, DL 0 enters the ACK state, sends a Retry_Ack_Set,
           retransmits DLLDBs 0 to n, and then returns to the NORMAL state.
      5.   After receiving the Retry_Ack_Set, DL 1 returns to the NORMAL state.




                    Figure 4-44 Retry_Req_Set retransmission process upon timeout

Figure 4-44 shows the Retry_Req_Set retransmission process upon timeout:

      1.   DL 1 sends a Retry_Req_Set to enter the WAIT state (the previous procedure is the same as
           that in Figure 4-43) and starts the retransmission timeout counter.
      2.   DL 0 does not receive the Retry_Req_Set due to bit errors and continues to send packets in
           the NORMAL state.
      3.   DL 1 does not receive the Retry_Ack_Set after the retransmission timeout counter reaches
           the threshold. DL 1 changes from the WAIT state to the REQ state and resends the
           Retry_Req_Set.
      4.   DL 1 still does not receive the Retry_Ack_Set after sending the Retry_Req_Set for
           NUM_RETRY_THRESHOLD consecutive times and enters the RETRAIN state.
      5.   When DL 1 remains in the RETRAIN state for NUM_PHY_REINIT_THRESHOLD times and
           still does not receive the Retry_Ack_Set, it enters the ERROR state.




unifiedbus.com                                                                                    141
4 Data Link Layer



4.8 Exception Handling

4.8.1 Credit-related Exceptions
During the operation of the credit mechanism, the following exceptions SHALL trigger error reporting:

      ⚫      Receive Buffer Overflow: If the DLLDBs received by the data link layer cause the receive
             buffer at the receiver to overflow, this error SHALL be reported.
      ⚫      Flow Control Overflow: If the credit count exceeds its initialized value, indicating a credit
             overflow, this error SHALL be reported.
      ⚫      DL Protocol Error: Each link at the data link layer maintains a credit return timeout counter. If
             credits are not returned within the expected time window, a timeout occurs and this error
             SHALL be reported.

When any of the above exceptions occur, the data link layer cannot function properly. After error
reporting, it SHALL wait for the UBFM to reset and restart. For details about exception reporting and
handling, see Section 10.6.2.


4.8.2 Retransmission-related Exceptions
During the operation of the retransmission mechanism, the following exceptions SHALL trigger error
reporting:

      ⚫      DL Retry ACK Timeout: If the data link layer does not receive a Retry_Ack_Set within the
             expected time after initiating a Retry_Req_Set, the sender's wait times out and this error
             SHALL be reported.
      ⚫      DL Retry Rollover: If the data link layer fails to retransmit the same RcvPtr after
             NUM_RETRY_THRESHOLD attempts—indicating excessive retransmissions—this error
             SHALL be reported.
      ⚫      DL Retry Error: If retransmission continues to fail after NUM_RETRY_THRESHOLD x
             NUM_PHY_REINIT_THRESHOLD attempts, causing the retransmission request state
             machine to enter the ERROR state, this error SHALL be reported.
      ⚫      DL Protocol Error: If receiving an ACK causes the NumFreeBuf parameter of the retry buffer
             to overflow, this error SHALL be reported.

For the first two exceptions, the data link layer will attempt automatic retries, as described in Section
4.7. For the last two exceptions, the data link layer can no longer operate normally. After error reporting,
it SHALL wait for the UBFM to reset and restart. For details about fault reporting and handling, see
Section 10.6.2.




unifiedbus.com                                                                                               142
4 Data Link Layer



4.8.3 Error DLLDP
If the data link layer does not accumulate data when sending DLLDPs—i.e., it sends DLLDBs without
waiting for the complete DLLDP—to reduce sending or forwarding latency, an error may occur. For
example, after the initial DLLDBs of a DLLDP are sent to the physical layer, the data link layer may detect
a data read error (such as a memory ECC error). In this case, the sender cannot discard the DLLDP.

To solve this problem, the data link layer supports the function of marking the packet error in the
ERROR_FLAG field of the last flit of the DLLDP. The peer data link layer parses the packet as a normal
DLLDP and sends it to the upper layer. Finally, the packet is discarded in the position where the DLLDP
is complete.

Note that:

      ⚫      When packets with error flags are received, the data link layer processes them as normal
             DLLDPs without initiating retransmission—unless CRC errors are triggered by bit errors.
      ⚫      Issues caused by link-level bit errors are recovered through physical-layer FEC and data-
             link-layer CRC with retransmission support, preventing link bit errors from propagating to the
             upper layers.


4.8.4 Link Disconnection
After detecting a link disconnection, the physical layer reports LinkUp==1'b0 to the data link layer. After
receiving the link disconnection information, the data link layer performs the following operations:

      1.     The sender discards all data received from the upper layer.
      2.     If the DLLDP is not completely received at the receiver, the DLLDP that has been partially
             sent to the upper layer needs to be padded (payload set to 0) and BCRC.ERROR_FLAG or
             END.ERROR_FLAG SHALL be set.
      3.     The credit counter is cleared (see Section 4.6.2).
      4.     The WrPtr, TailPtr, RdPtr, and RcvPtr fields of the retry buffer are set to 0, and
             NumFreeBuf is set to the depth value of the retransmission buffer (see Section 4.7.3.2.2).
      5.     The data link state machine enters the DLL_Disabled state and waits for reinitialization.




unifiedbus.com                                                                                           143
