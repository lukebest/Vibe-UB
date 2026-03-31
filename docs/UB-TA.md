7 Transaction Layer




7 Transaction Layer


7.1 Overview
The transaction layer is positioned above the transport layer and offers various transaction services and
transaction operations to the upper layer. It receives transaction operations from upper-layer programming
models—both load/store synchronous access and URMA asynchronous access—and collaborates with
the underlying protocol to execute and complete transaction operations between the initiator and the
target. To optimize transmission efficiency, the transaction layer introduces the compact packet headers to
be used together with transport (TP) bypass mode for some specific transaction operations, such as
memory read/write initiated by the load/store synchronous access programming model.




                                   Figure 7-1 Transaction layer overview

The transaction layer supports four types of transactions: memory transaction, message transaction,
maintenance transaction, and management transaction. Each transaction includes one or more
transaction operations, each uniquely identified by a transaction operation code (TAOpcode). For
details, see Section 7.4. A transaction operation consists of at least one transaction request and,
optionally, a corresponding response.

The transaction layer provides reliable and unreliable transaction service modes. For reliable services,
it relies on the underlying protocol to guarantee the reliable delivery of transaction-layer packets. It also
supports retries to handle some specific manageable transaction exceptions like resource shortages.
For unresolvable exceptions, the transaction layer SHALL report the transaction status to the upper
layer for handling. In contrast, the unreliable service mode does not depend on the lower layers for
reliability or retransmit failed transactions. When processing a sequence of transactions, the transaction
layer adopts various methods to ensure the required transaction ordering, including both the order of
execution and the order of completion.




unifiedbus.com                                                                                            207
7 Transaction Layer



Based on whether reliability and execution ordering are guaranteed, the transaction layer offers four
service modes for the upper layer to utilize: reliable and ordered by initiator (ROI), reliable and ordered
by target (ROT), reliable and ordered by lower layer (ROL), and unreliable and non-ordered (UNO). As
these service modes offers different reliability and ordering capabilities, they impose different
requirements on the underlying protocol. The relationship between the service modes and the required
underlying feature support is discussed in Section 7.3.4. For detailed information on the transaction
service modes applicable to each transaction operation, refer to Section 7.4.

To secure transaction operations, transactions MAY carry necessary credentials to verify access
permissions for both memory operations and message operations.

The UB transaction layer has the following key features:

            1.     Unified transaction operations for different programming models
            2.     Multiple transaction service modes to meet various requirements for transaction reliability
                   and ordering
            3.     Security mechanisms provided to ensure secure execution of transaction operations
            4.     Enhanced transmission efficiency for load/store synchronous access transactions through TP
                   bypass mode and a compact packet format


7.2 Transaction Headers

7.2.1 Basic Transaction Header (BTAH)
The BTAH SHALL be included in all transaction request packets. It is available in two formats: full and
compact.

Full BTAH format:

                   Byte0                                                          Byte1                                      Byte2               Byte3
 7          6 5 4 3           2     1       0       7       6           5 4 3                 2        1      0         7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                                                                              UD_Flag
                                                                        EE_bits

                                                                                      TV_EN
                                                                                              Poison
                                                                                                       RSVD
                                                        TAver




                 TAOpcode                                                                                                            INI_TASSN
                                                                        INI_RC_Type
 No_TAACK




                      MT_EN




                                                    RSVD
                                    Retry




                                                                E_bit
             ODR




                                            Alloc
                              FCE




                                                                                                                             INI_RC_ID



                                                                        Figure 7-2 Full BTAH format




unifiedbus.com                                                                                                                                           208
7 Transaction Layer



Compact BTAH format:

           Byte0                                  Byte1                                    Byte2               Byte3
 7 6 5 4 3 2 1 0 7 6 5 4 3                                  2        1      0         7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0




                                                                            UD_Flag
                                        EE_bits

                                                    TV_EN
                                                            Poison
                                                                     RSVD
                            TAver
         TAOpcode                                                                                  INI_TASSN


                                              Figure 7-3 Compact BTAH format

The following table describes BTAH fields.

                                                        Table 7-1 BTAH fields
                                                                                                        Field Description
 Field              Bit Width       Field Description (Full BTAH)
                                                                                                        (Compact BTAH)
 TAOpcode           8               Transaction operation code, that is, the                            Same as the column
                                    operation type of the current transaction. The                      to the left
                                    code can be:
                                    ●      0x0: Send
                                    ●      0x1: Send_with_immediate
                                    ●      0x2: reserved
                                    ●      0x3: Write
                                    ●      0x4: Write_with_immediate
                                    ●      0x5: Write_with_notify
                                    ●      0x6: Read
                                    ●      0x7: Atomic_compare_swap
                                    ●      0x8: Atomic_swap
                                    ●      0x9: Atomic_store
                                    ●      0xA: Atomic_load
                                    ●      0xB: Atomic_fetch_add
                                    ●      0xC: Atomic_fetch_sub
                                    ●      0xD: Atomic_fetch_and
                                    ●      0xE: Atomic_fetch_or
                                    ●      0xF: Atomic_fetch_xor
                                    ●      0x10: Management
                                    ●      0x11 to 0x13: See Section 7.2.2.
                                    ●      0x14: Write_with_be
                                    ●      0x15: Prefetch_tgt
                                    ●      0x16: reserved
                                    ●      0x17: Writeback
                                    ●      0x18: Writeback_with_be
                                    ●      Others: reserved
 TAver              2               Transaction protocol version. SHALL be set to                       Same as the column
                                    0 for the current protocol.                                         to the left
 EE_bits            2               Execution environment bits, identifying the                         Same as the column




unifiedbus.com                                                                                                              209
7 Transaction Layer



                                                                                    Field Description
 Field            Bit Width   Field Description (Full BTAH)
                                                                                    (Compact BTAH)
                              execution environment security attribute of the       to the left
                              transaction source.
                              ● 2'b00: reserved
                              ● 2'b01: non-TEE
                              ● 2'b10: reserved
                              ● 2'b11: TEE

 TV_EN            1           Specifies whether the Token Value Extended            Same as the column
                              Transaction Header (TVETAH) is included.              to the left
                              ● 1'b0: No TVETAH is included.
                              ● 1'b1: The TVETAH is included.

 Poison           1           Specifies whether the payload contains                Same as the column
                              poisoned data.                                        to the left
                              ● 1'b0: no
                              ● 1'b1: yes

 UD_Flag          1           Specifies whether the User Defined Extended           Same as the column
                              Transaction Header (UDETAH) is included.              to the left
                              ● 1'b0: No UDETAH is included.
                              ● 1'b1: The UDETAH is included.

 INI_TASSN        16          Initiator transaction segment sequence                Same as the column
                              number (TASSN), which is the unique                   to the left
                              identifier of a transaction.
                              When the target generates a transaction
                              response, it carries this field back to the
                              initiator, allowing the initiator to identify which
                              transaction is responded to. If the transaction
                              is segmented, each segment is assigned a
                              unique TASSN.
                              When compact transport (CTP) mode is in
                              use, each segment is assigned a TASSN and
                              contains a single packet.
 No_TAACK         1           Specifies whether to return the transaction           N/A
                              acknowledgement (TAACK). This field is valid
                              only when the CTP mode is in use.
                              ● 1'b0: TAACK return is requested.
                              ● 1'b1: TAACK return is not requested.

 ODR              3           Specifies ordering attributes of the transaction      N/A
                              request.
                              ODR[1:0] specifies the transaction execution
                              order (TEO).
                              ● 2'b00: no order (NO), indicating that this
                                transaction has no order requirement
                                relative to others.
                              ● 2'b01: relaxed order (RO), indicating that




unifiedbus.com                                                                                          210
7 Transaction Layer



                                                                                  Field Description
 Field            Bit Width   Field Description (Full BTAH)
                                                                                  (Compact BTAH)
                                 this transaction imposes order requirements
                                 relative to subsequent transactions with SO
                                 flag. Transactions with SO flag cannot be
                                 executed earlier than the preceding
                                 transactions with RO flag.
                              ● 2'b10: strong order (SO), indicating that this
                                transaction imposes order requirements
                                relative to preceding transactions with RO
                                or SO flag. This transaction cannot be
                                executed earlier than the preceding
                                transactions with RO or SO flag.
                              ● 2'b11: reserved
                              ODR[2] specifies the transaction completion
                              order (TCO).
                              ● 1'b0: No completion order required
                              ● 1'b1: Completion order required

 MT_EN            1           Specifies whether the Message Target                N/A
                              Extended Transaction Header (MTETAH) is
                              included.
                              ● 1'b0: No MTETAH included
                              ● 1'b1: MTETAH included

 FCE              1           Fast completion event. Used by the target to        N/A
                              specify whether to generate a completion
                              event when generating a completion queue
                              element (CQE).
                              ● 1'b0: Do not generate a completion event.
                              ● 1'b1: Generate a completion event.

 Retry            1           Specifies whether the request is a first try or a   N/A
                              retry.
                              ● 1'b0: first try
                              ● 1'b1: retry

 Alloc            1           Requests the target to allocate a sequence          N/A
                              context (SC) associated with an SCID. This
                              field is used only in the first packet in dynamic
                              ROT mode.
                              ● 1'b0: Do not allocate an SC.
                              ● 1'b1: Allocate an SC.

 E_bit            1           Exclusive bit, used for exclusive verification.     N/A
                              ● 1'b0: non-exclusive mode
                              ● 1'b1: exclusive mode

 INI_RC_Type      2           Context type used for sending this transaction      N/A
                              by the initiator.
                              ● 2'b00 and 2'b01: The initiator uses the




unifiedbus.com                                                                                        211
7 Transaction Layer



                                                                                        Field Description
 Field              Bit Width     Field Description (Full BTAH)
                                                                                        (Compact BTAH)
                                      send queue (SQ).
                                  ● 2'b10: The initiator uses target sequence
                                     context resources.
                                  ● 2'b11: reserved

 INI_RC_ID          20            Context identifier used for sending this              N/A
                                  transaction by the initiator.
                                  ● If INI_RC_Type equals 2'b00 or 2'b01, this
                                    field indicates the requester context identifier
                                    (RCID). When the target generates a
                                    transaction response, it carries this field
                                    back to the initiator, allowing the initiator to
                                    identify the correct SQ.
                                  ● If INI_RC_Type equals 2'b10, this field
                                    indicates the SCID. When the target
                                    generates a transaction response, it
                                    fetches the RCID from the SC and fills it in
                                    the Acknowledge Transaction Header
                                    (ATAH), allowing the initiator to identify the
                                    correct SQ.
                                  ● If the transaction is a resource
                                    management message, this field indicates
                                    a message queue identifier (its upper limit
                                    is subject to the implementation). When
                                    the target generates a transaction
                                    response, it carries this field back to the
                                    initiator, allowing the initiator to identify the
                                    correct message queue.


The following table lists packet formats used by different transaction operations.

                   Table 7-2 Mapping between transaction operations and packet formats
 Transaction Type           TAOpcode         Transaction Subtype          Packet Format
 Memory          Write      0x3              Write                        BTAH, [UDETAH], MAETAH,
 transaction                                                              [TVETAH], Payload
                            0x5              Write_with_notify            BTAH, [UDETAH], MAETAH,
                                                                          NTFETAH, [TVETAH], Payload
                            0x14             Write_with_be                BTAH, [UDETAH], MAETAH,
                                                                          [TVETAH], BEETAH, Payload
                            0x17             Writeback                    BTAH, [UDETAH], MAETAH,
                                                                          [TVETAH], Payload
                            0x18             Writeback_with_be            BTAH, [UDETAH], MAETAH,
                                                                          [TVETAH], BEETAH, Payload
                 Read       0x6              Read                         BTAH, [UDETAH], [TAIDETAH],
                                                                          [OFSTETAH], MAETAH,
                                                                          [TVETAH]




unifiedbus.com                                                                                              212
7 Transaction Layer



 Transaction Type              TAOpcode          Transaction Subtype           Packet Format
                 Atomic        0x7               Atomic_compare_swap
                               0x8               Atomic_swap
                               0x9               Atomic_store
                               0xA               Atomic_load
                                                                               BTAH, [UDETAH], [TAIDETAH],
                               0xB               Atomic_fetch_add
                                                                               MAETAH, [TVETAH], Payload
                               0xC               Atomic_fetch_sub
                               0xD               Atomic_fetch_and
                               0xE               Atomic_fetch_or
                               0xF               Atomic_fetch_xor

 Message transaction           0x0               Send                          BTAH, [UDETAH], MTETAH,
                                                                               OFSTETAH, [TVETAH], Payload
                               0x1               Send_with_immediate           BTAH, [UDETAH], MTETAH,
                                                                               OFSTETAH, IMMETAH,
                                                                               [TVETAH], Payload
                               0x4               Write_with_immediate          BTAH, [UDETAH], MTETAH,
                                                                               MAETAH, IMMETAH, [TVETAH],
                                                                               Payload
 Maintenance                   0x15              Prefetch_tgt                  BTAH, [UDETAH], MAETAH
 transaction
 Management                    0x10              Management                    BTAH, [UDETAH], MGMTETAH,
 transaction                                                                   Payload
 Other                         Reserved


Note: Packet headers in square brackets [ ] are optional. For details about whether to include such headers, see Section
7.4.



7.2.2 Acknowledge Transaction Header (ATAH)
The ATAH SHALL be included in all transaction response packets. It is available in two formats: full and
compact. The format of the ATAH SHALL align with the format of the BTAH, requiring either the full or
compact format for both.

Full ATAH format:




unifiedbus.com                                                                                                      213
7 Transaction Layer




          Byte0                                       Byte1                                            Byte2                   Byte3

7 6 5 4 3 2 1 0 7 6 5                          4               3           2                 1 0 7 6 5 4 3 2 1 0 7              6 5 4 3 2 1 0




                                                                               Poison
                                        RSVD




                                                                                              RSVD
                        TAver




                                                                   SV
     TAOpcode                                                                                                     INI_TASSN




                                        INI_RC_Type
                        RSVD



RSPST RSPINFO                                                                                             INI_RC_ID



                                                                   Figure 7-4 Full ATAH format

Compact ATAH format:

           Byte0                                               Byte1                                      Byte2                   Byte3

 7 6 5 4 3 2 1 0 7 6 5 4                                            3             2           1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                                                    Poison
                                                      Status

                                                                        RSVD



                                                                                                RSVD
                                TAver




         TAOpcode                                                                                                 INI_TASSN


                                                           Figure 7-5 Compact ATAH format

The following table describes ATAH fields.

                                                                          Table 7-3 ATAH fields
                                                                                                                      Field Description
 Field              Bit Width                 Field Description (Full ATAH)
                                                                                                                      (Compact ATAH)
 TAOpcode           8                         Response type of the current transaction.                               Same as the column to
                                              The type can be:                                                        the left
                                              ● 0x11: TAACK
                                              ● 0x12: Read_response
                                              ● 0x13: Atomic_response

 TAver              2                         Transaction protocol version. SHALL be                                  Same as the column to
                                              set to 0 for the current protocol.                                      the left
 Status             2                         Reserved                                                                Remote authentication
                                                                                                                      result. The code can be:
                                                                                                                      ● 2'b00: The remote
                                                                                                                        authentication
                                                                                                                        succeeds, and the data
                                                                                                                        read/write operations
                                                                                                                        are correctly
                                                                                                                        completed.
                                                                                                                      ● 2'b01: The remote




unifiedbus.com                                                                                                                                   214
7 Transaction Layer



                                                                              Field Description
 Field            Bit Width   Field Description (Full ATAH)
                                                                              (Compact ATAH)
                                                                                authentication fails.
                                                                              ● Others: reserved

 SV               1           SCID validity flag.                             Reserved
                              Indicates whether allocation of target
                              SCID succeeded. In case of success, this
                              bit is set to 1 and INI_TASSN carries the
                              valid SCID. This bit is utilized in dynamic
                              ROT mode only.
 Poison           1           Poisoned data flag. Only valid when the         Same as the column to
                              response carries payload.                       the left
                              ● 1'b0: No poisoned data in payload.
                              ● 1'b1: Poisoned data exists in payload.

 INI_TASSN        16          Initiator TASSN.                                TASSN assigned by the
                              ● If SV is 0, this field indicates the          initiator to the
                                                                              correspondent transaction
                                TASSN assigned by the initiator to the
                                                                              request
                                correspondent transaction request.
                              ● If SV is 1, this field indicates the target
                                SCID allocated in ROT mode.
 RSPST            3           Transaction response status, which is           N/A
                              used together with RSPINFO. The status
                              can be:
                              ● 3'b000: Successful Completion (SC)
                              ● 3'b001: Receiver Not Ready (RNR). It
                                indicates a transaction execution error
                                due to insufficient receive resources
                                on the target. In this case, RSPINFO
                                indicates RNR_Timer.
                              ● 3'b010: Page Fault. It indicates a
                                transaction execution error due to
                                page faults on the target. In this case,
                                RSPINFO indicates RNR_Timer. The
                                implementation may choose to handle
                                page faults using either of the
                                following methods:
                                 Method 1: The target sends an
                                 abnormal TAACK to the initiator
                                 requesting retransmission before the
                                 page fault handling is complete. In this
                                 method, RNR_Timer is typically set to
                                 a value greater than 0.
                                 Method 2: The target sends an
                                 abnormal TAACK to the initiator
                                 requesting retransmission after the
                                 page fault handling has been
                                 completed. For this method,
                                 RNR_Timer is set to 0.




unifiedbus.com                                                                                          215
7 Transaction Layer



                                                                               Field Description
 Field            Bit Width   Field Description (Full ATAH)
                                                                               (Compact ATAH)
                              ● 3'b011: Completer Error
                              ● 3'b101: The packet data is correctly
                                received, but not placed into the final
                                memory location.
                              ● Others: reserved
                              Note: 3'b000 and 3'b101 differ in that 3'b000
                              indicates the payload has been written into
                              memory, while 3'b101 indicates the payload has
                              been handed over to the medium controller,
                              such as the memory controller, but whether the
                              payload is written into the medium is not
                              guaranteed.

 RSPINFO          5           Transaction response information,                N/A
                              encoded as follows:
                              ● If RSPST equals 3'b000 or 3'b101,
                                this field indicates the number of
                                aggregated TAACKs. If the value is 0,
                                this TAACK does not include any other
                                TAACKs. A non-zero value represents
                                the count of additional TAACKs
                                aggregated within this TAACK.
                              ● If RSPST equals 3'b001 or 3'b010:
                                This field indicates the RNR_Timer
                                code, where the RNR timeout is
                                calculated as: RNR_Timeout = 2 μs ×
                                2^RNR_Timer. The valid code range
                                of RNR_Timer is [0, 19]. Other codes
                                are reserved.
                              ● If RSPST is 3'b011, this field indicates
                                that an error response is returned. The
                                error type can be:
                                 - 5'b00001: Unsupported Request
                                 - 5'b00010: Remote Abort
                              ● Others: reserved

 INI_RC_Type      2           Context type used for sending this               N/A
                              transaction by the initiator.
                              ● 2'b00 and 2'b01: The initiator uses the
                                SQ.
                              ● 2'b10: The initiator uses target SC
                                resources.
                              ● 2'b11: reserved

 INI_RC_ID        20          Context identifier used for sending this               N/A
                              transaction by the initiator.
                              ● If INI_RC_Type equals 2'b00 or 2'b01,
                                this field indicates the RCID. When the
                                target generates a transaction
                                response, it carries this field back to




unifiedbus.com                                                                                     216
7 Transaction Layer



                                                                                        Field Description
 Field               Bit Width       Field Description (Full ATAH)
                                                                                        (Compact ATAH)
                                        the initiator, allowing the initiator to
                                        identify the correct SQ.
                                     ● If INI_RC_Type equals 2'b10, this field
                                       indicates the SCID. When the target
                                       generates a transaction response, it
                                       fetches the RCID from the SC and fills
                                       it in the ATAH, allowing the initiator to
                                       identify the correct SQ.


The following table lists packet formats used by different transaction responses.

                     Table 7-4 Mapping between transaction responses and packet formats
 TAOpcode          Transaction Response            Packet Format
 0x11              Transaction_ACK                 ATAH
 0x12              Read_response                   ATAH, [TAIDETAH], [OFSTETAH], Payload
 0x13              Atomic_response                 ATAH, [TAIDETAH], [Payload]


Note: Packet headers in square brackets [ ] are optional. For details about whether to include such headers,
see Section 7.4.



7.2.3 Memory Access Extended Transaction Header (MAETAH)
The MAETAH carries required information to access the target memory segment (see Section 8.2.1),
including the address, data length, and token ID. It is available in two formats: full and compact.

Full MAETAH format:

           Byte0                          Byte1                         Byte2                         Byte3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                   Address[63:32]
                                                    Address[31:0]
   RSVD                                     TokenID[19:0]                                             RSVD
                                                        Length
                                          Figure 7-6 Full MAETAH format




unifiedbus.com                                                                                                 217
7 Transaction Layer



Compact MAETAH format:

          Byte0                  Byte1                    Byte2                                     Byte3
7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7                               6   5               4   3    2    1 0
                                             Address[63:32]




                                                                                    Affinity_hint




                                                                                                                 Length
                                                                                                        SO
                                 Address[31:6]



                 RSVD                                           TokenID[19:0]
                                 Figure 7-7 Compact MAETAH format

The following table describes MAETAH fields.

                                         Table 7-5 MAETAH fields
                                                                      Field Description (Compact
 Field            Bit Width   Field Description (Full MAETAH)
                                                                      MAETAH)
 Address          64          Address of the first data byte of the   Same as the column to the left.
                              target memory segment to be             The lower six bits are 0.
                              accessed by this packet.
                              For an Atomic transaction, the
                              address of atomic operands SHALL
                              be aligned. For example, the
                              address of a 4-byte Atomic
                              transaction shall be 4-byte aligned.
 TokenID          20          Token ID, which is used to identify     Same as the column to the left
                              the target memory segment.
 Affinity_hint    2           N/A                                     Affinity of target data access or
                                                                      processing
 SO               1           N/A                                     Execution order flag.
                                                                      ● 1'b0: RO. This transaction
                                                                        blocks subsequent
                                                                        transactions with SO flag.
                                                                      ● 1b'1: SO. This transaction
                                                                        waits for the execution of
                                                                        preceding transactions with
                                                                        SO or RO flag.
 Length           32/3        Length of data to be accessed in        Length of data to be accessed in
                              the target memory. If a transaction     the target memory, which is
                              is segmented, this field identifies     calculated as 64 bytes ×
                              the total data length in the memory     (2^Length). If the field value is 0,
                              segment to be accessed by a             the data length is 64 bytes; if the
                              single transaction segment.             field value is 7, the data length is
                                                                      8,192 bytes.




unifiedbus.com                                                                                                            218
7 Transaction Layer



7.2.4 Message Target Extended Transaction Header (MTETAH)
The MTETAH carries transaction receive queue (RQ) information for the target to process a message
transaction (see Section 8.2.3), that is, the target context identifier (TCID) to which the message is
directed on the target. If this header is included, BTAH.MT_EN SHALL be set to 1.

MTETAH format:

         Byte0                          Byte1                        Byte2                     Byte3
7 6 5 4 3 2 1 0 7              6    5     4     3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                   TGT_TC_
          Hint             RSVD                                         TGT_TC_ID
                                     Type
                                         Figure 7-8 MTETAH format

The following table describes MTETAH fields.

                                          Table 7-6 MTETAH fields
 Field                Bit Width    Field Description
 Hint                 8            Only valid when TGT_TC_Type is set to target context group. The
                                   hint is used to distribute loads across multiple RQs for load
                                   balancing.
 TGT_TC_Type          2            Target context (TC) type.
                                   ● 2'b00 or 2'b01: TC
                                   ● 2'b10: TC group
                                   ● 2'b11: reserved

 TGT_TC_ID            20           Target context identifier. It identifies an RQ or RQ group.


7.2.5 Token Value Extended Transaction Header (TVETAH)
The TVETAH carries the token value for security verification on the target (see Section 8.2.4). It SHALL
be included only when security verification is enabled. If this header is included, BTAH.TV_EN SHALL
be set to 1.

For Send and Send_with_immediate transaction requests, this field is used for security verification of
the Jetty, Jetty for receiving (JFR), or Jetty group (see Section 8.2.2). The token value carried by this
header is checked against the token value that can be retrieved from the target using the TCID included
in the MTETAH. If the data length is 0, the Jetty, JFR, or Jetty group still requires security verification.

For Read, Atomic, and Write transaction requests, this field is used for security verification of memory
segments on the target. The token value carried by this header is checked against the token value that
can be retrieved from the target using the TokenID included in the MAETAH. If the data length is 0,
accessing the target memory segment does not require security verification.

TVETAH format:




unifiedbus.com                                                                                             219
7 Transaction Layer



          Byte0                         Byte1                      Byte2                      Byte3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                TokenValue[31:0]
                                          Figure 7-9 TVETAH format

The following table describes the TVETAH field.

                                            Table 7-7 TVETAH field
 Field                Bit Width    Field Description
 TokenValue           32           Used for security verification on the target. The access object can be a
                                   memory segment or a target Jetty/JFR/Jetty group.


7.2.6 Task ID Extended Transaction Header (TAIDETAH)
The TAIDETAH carries task ID information for the initiator to identify the corresponding transaction.

TAIDETAH format:

          Byte0                         Byte1                      Byte2                     Byte3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                           RSVD                                                 TAID
                                         Figure 7-10 TAIDETAH format

The following table describes the TAIDETAH field.

                                           Table 7-8 TAIDETAH field
 Field           Bit Width        Field Description
 TAID            16               Task ID. This field is copied from the transaction request to the
                                  transaction response and allows the initiator to retrieve the information
                                  required to place response data.


7.2.7 Offset Extended Transaction Header (OFSTETAH)
The OFSTETAH carries the offset of the first data byte carried by a packet with respect to the first data
byte of the transaction. It is applicable to multi-packet transaction.

OFSTETAH format:

          Byte0                         Byte1                      Byte2                     Byte3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
          RSVD                                                     Offset
                                        Figure 7-11 OFSTETAH format

The following table describes the OFSTETAH field.




unifiedbus.com                                                                                            220
7 Transaction Layer



                                       Table 7-9 OFSTETAH field
 Field     Bit Width    Field Description
 Offset    24           Offset of the packet among multiple packets in the transaction layer, with a
                        granularity of 1 KB. The first packet has an offset of 0, and subsequent
                        packets have their offset incremented with 1 KB granularity. For example, if
                        the first packet carries N KB payload, the offset of the second packet is N.
                        For a Send transaction, the target uses it to determine the offset of this
                        packet in data buffer referred to by the receive queue element (RQE). In
                        CTP mode, the length of a Send transaction is limited to one packet, and this
                        field is reserved.
                        For a Read transaction, the initiator uses it to determine the offset of this
                        read response in data buffer referred to by the send queue element (SQE).


7.2.8 Immediate Extended Transaction Header (IMMETAH)
The IMMETAH carries immediate data to be placed in the CQE on the target. Send_with_immediate
and Write_with_immediate transactions SHALL include this extended header.

IMMETAH format:

          Byte0                   Byte1                       Byte2                     Byte3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                        Immediate_Data[63:32]
                                        Immediate_Data[31:0]
                                        Immediate_TokenValue
                                             Msg_Length
                                    Figure 7-12 IMMETAH format

The following table describes IMMETAH fields.

                                    Table 7-10 IMMETAH fields
 Field                     Bit Width      Field Description
 Immediate_Data            64             Immediate data, which is stored in the CQE and reported to
                                          the user when the target generates a completion
                                          notification. The immediate data length is fixed at 8 bytes.
 Immediate_TokenValue      32             The token value of this field is checked against the token
                                          value that can be retrieved from the target using the
                                          corresponding Jetty context. This field is valid only for
                                          Write_with_immediate transactions and is reserved for other
                                          operations.
 Msg_Length                32             Total length of a Write transaction. This field is used by the
                                          target to report a CQE. This field is valid only for
                                          Write_with_immediate transactions and is reserved for other
                                          operations.




unifiedbus.com                                                                                       221
7 Transaction Layer



7.2.9 Notify Extended Transaction Header (NTFETAH)
The NTFETAH carries information required to place notification data on the target, including notification
data, memory address, and access credentials. Write_with_notify transactions SHALL include this
extended header.

NTFETAH format:

           Byte0                     Byte1                        Byte2                          Byte3
 7 6 5 4 3         2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                              Address[63:32]
                                               Address[31:0]
    RSVD                            Notify_TokenID[19:0]                                        RSVD
                                             Notify_TokenValue
                                             Notify_Data[63:32]
                                             Notify_Data[31:0]
                                      Figure 7-13 NTFETAH format

The following table describes NTFETAH fields.

                                       Table 7-11 NTFETAH field
 Field                  Bit Width     Field Description
 Address                64            Address of the first data byte of the target memory segment
                                      where the notification data is to be written.
 Notify_TokenID         20            Token ID, which is the index used for accessing the memory
                                      segment where notification data is to be written.
 Notify_TokenValue      32            Token value used for permission verification of memory access.
                                      Note 1: If BTAH.TV_EN is 1, the packet header carries two token values.
                                      The one carried in the TVETAH is used to verify memory segment access
                                      permissions of the MAETAH, and the one carried in the NTFETAH is used
                                      to verify permissions of writing notification data into the memory segment.
                                      Note 2: If BTAH.TV_EN is 0, NTFETAH.Notify_TokenValue is reserved.

 Notify_Data            64            Notification data. The valid data length is fixed at 8 bytes.


7.2.10 Byte Enable Extended Transaction Header (BEETAH)
The BEETAH indicates the byte enable (BE) status of the payload. Write_with_be and
Writeback_with_be transactions SHALL include this extended header.




unifiedbus.com                                                                                                 222
7 Transaction Layer



BEETAH format (8 bytes for example):

            Byte0                    Byte1                       Byte2                      Byte3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                 BE[63:32]
                                                  BE[31:0]
                                   Figure 7-14 BEETAH format (8 bytes)

The following table describes the BEETAH field.

                                         Table 7-12 BEETAH field
 Field        Bit Width       Field Description
 BE           64 to 1024      Byte enable flag. BE[n] indicates whether the N-th byte of the payload in
                              the network transmission byte order of the packet is valid. Value 1
                              indicates valid, and value 0 indicates invalid.
                              BE supports 64/128/256/512/1024 bits, corresponding to the
                              64/128/256/512/1024-byte payload length of Write_with_be and
                              Writeback_with_be transactions, respectively.


7.2.11 User Defined Extended Transaction Header (UDETAH)
Content carried by the UDETAH is defined by vendors, with a length of 4 bytes. The BTAH.UD_Flag
field specifies whether the UDETAH is included.

            Byte0                    Byte1                       Byte2                      Byte3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
                                                  UD[31:0]
                                       Figure 7-15 UDETAH format


7.2.12 Management Extended Transaction Header (MGMTETAH)
Management transactions SHALL include this extended header. For the packet format, see Section
10.4.3.3.


7.3 Transaction Services

7.3.1 Transaction Reliability

7.3.1.1 Reliable Transaction

For reliable transaction services, after the initiator sends a transaction request, the target needs to
return a transaction response, containing the transaction execution status such as success, exception,
or other.




unifiedbus.com                                                                                            223
7 Transaction Layer



Figure 7-16 shows the interaction process of reliable transaction.




                                Figure 7-16 Reliable transaction interaction

Typically, a transaction operation comprises a transaction request and a transaction response. The
transaction layer SHALL support transaction segmentation, where a transaction is divided into multiple
transaction segments. Each segment of transaction request is assigned a unique TASSN and is
expected to receive a separate transaction response. The initiator considers the entire transaction
completed only after receiving responses for all transaction segments. Transaction segmentation
SHALL comply with the following constraints:

      1.   If reliable transport (RTP) mode is used in the transport layer, transaction segments can be
           submitted to different TP channels to prevent a large transaction from occupying a TP
           channel for a long time and causing congestion. The segmentation granularity is
           configurable. For example, a 1 MB Write memory transaction may be divided into multiple 64
           KB transaction segments. For details about whether transaction segmentation is supported
           for specific transaction types, see Section 7.4.
      2.   If CTP or TP bypass mode is used in the transport layer, one transaction segment
           corresponds to one packet, that is, each packet occupies a unique TASSN.

Transaction responses are classified into TAACK, read response, and atomic response. If the full
packet format is used, the transaction layer supports aggregation of normal TAACKs with contiguous
TASSNs between a given initiator-target pair. Multiple TAACKs are merged into a single TAACK that
carries the TASSN of the first TAACK in the group and a number of the subsequent TAACKs covered,
and this aggregated TAACK is returned to the initiator. When the initiator receives such an aggregated
TAACK, it treats all TAACKs in the covered range as received. For example, if the TAACK TASSN is N,
ATAH.RSPST is 3'b000 or 3'b101, and ATAH.RSPINFO is 9, the initiator considers that 10 transaction
TAACKs (from N to N+9) have been acknowledged. TAACK aggregation is not supported for abnormal
TAACKs, that is, responses of unsuccessfully executed transactions.

Generally, the target SHALL return a transaction response, excluding the following cases:

      1.   The target may carry a transaction response status in a transport-layer response packet,
           including the following cases:
           (1)   If RTP mode is used in the transport layer and the transaction service mode is ROL
                 (see Section 7.3.3.4), a transaction execution status may be carried in a transport-




unifiedbus.com                                                                                          224
7 Transaction Layer



                 layer response instead of an independent TAACK. In this scenario, TAACK
                 aggregation SHALL NOT be used.
           (2)   If RTP mode is used in the transport layer and the transaction service mode is ROI,
                 ROT, or ROL (see Section 7.3.3.2 to Section 7.3.3.4), and in case the transaction layer
                 cannot submit a transaction response due to lack of resources, the transaction
                 execution status may be carried in a transport-layer response. In this scenario,
                 transaction response aggregation SHALL NOT be used.
      2.   When CTP mode is used in the transport layer and the transaction service mode is ROL (see
           Section 7.3.3.4), the upper layer may request the transaction layer to set the
           BTAH.No_TAACK field in request packets to 1 to suppress TAACK returning from the target,
           thereby reducing the number of response packets. This method applies only to the network
           with extreme high quality and reliability.

The transaction layer SHALL support the following methods to ensure the reliable transaction services:

      1.   The underlying protocol ensures the transmission reliability of packets comprising transaction
           request or response.
      2.   The transaction layer and the upper layer ensure reliable transaction execution as follows:
           (1)   The transaction layer retransmits transactions for manageable exceptions, including
                 RNR and page faults (exception status carried in the ATAH). Figure 7-17 shows the
                 transaction retransmission process.




                              Figure 7-17 Reliable transaction retransmission

           (2)   For unresolvable exceptions, such as invalid memory length or failed permission
                 verification, the transaction layer does not perform retransmission. The initiator passes
                 the exception information to the upper layer, which is then responsible for exception
                 handling, including but not limited to clearing abnormal transactions and re-issuing
                 transaction requests. For details about transaction exceptions, see Section 10.6.2.




unifiedbus.com                                                                                          225
7 Transaction Layer



Note that the transaction layer SHALL NOT retransmit an abnormal transaction if retransmission could
lead to data inconsistency. For example, in the case of an Atomic transaction, if an RNR or a page fault
occurs during atomic response processing, the Atomic transaction shall not be retransmitted; instead,
the exception shall be reported. However, if an RNR or a page fault occurs during atomic request
processing, retransmitting the atomic request will not result in data inconsistency, and the atomic
request may be retransmitted.

Example: The initiator sends an Atomic_fetch_add request. After receiving the request, the target updates the data X at
the specified memory address to 1 and returns the initial value of X (0) to the initiator. A page fault occurs when the
target's atomic response attempts to update the initiator's memory. If the initiator retransmits the request, the target will
update X to 2 upon receipt and return X=1 as the response, leading to a service logic anomaly.


7.3.1.2 Unreliable Transaction

For unreliable transaction services, after transmitting a transaction request, the initiator assumes that the
transaction operation is completed and reports a completion event. The target does not need to return a
transaction response. Figure 7-18 shows the interaction process of unreliable transaction services.




                                     Figure 7-18 Unreliable transaction interaction

Under unreliable transaction services, the transaction layer neither provides transaction retransmission
functionality nor requires the underlying protocol to guarantee reliable transmission. The transaction
layer will report exception information to the upper layer for further processing. For details about
transaction exceptions, see Section 10.6.2.


7.3.2 Transaction Order

7.3.2.1 Transaction Order Concepts

Transaction order refers to the sequence relationship between transactions in the same transaction
queue (such as an SQ), and it includes the transaction execution order (TEO) and the transaction
completion order (TCO). Transaction order requirements are specified with different transaction order
flags, such as NO, RO, or SO. No ordering relationship is defined between transactions belonging to
different transaction queues.

Note: Order requirements are specified by the upper layer, and the transaction layer only applies order requirements.




unifiedbus.com                                                                                                             226
7 Transaction Layer



7.3.2.2 Transaction Execution Order

TEO refers to the execution sequence of transaction requests on the target, which is specified by
assigned TEO flags (see Section 7.2.1), including:

       1.   NO: The current transaction imposes no ordering constraint relative to others and can be
            executed in any order.
       2.   RO: The current transaction MAY be executed out of order. Its execution does not depend on
            other transactions and will block subsequent transactions marked as SO. That is, a transaction
            with the RO flag should be executed before subsequent transactions with the SO flag.
       3.   SO: The current transaction SHALL be executed in order. It SHALL wait until preceding
            transactions with the RO or SO flag are executed.

TEO can be implemented by the initiator, target, or in other methods. The transaction layer provides
various methods to ensure transaction ordering. For details, see Section 7.3.3.

In addition, the initiator MAY ensure the transaction ordering in other methods such as a fence or a
barrier, which is outside the scope of this specification. Such methods can be used together with TEO
flag-based mechanisms.

Transaction layer ordering example:

Table 7-13 illustrates a transaction queue containing transactions 0 to 4. Transaction 0 is marked as
RO, transaction 1 as SO, transaction 2 as NO, transaction 3 as NO (fence), and transaction 4 is as NO.
The initiator sends transactions starting from transaction 0.

Note: Fence is an ordering mechanism implemented by applications or processors. If a fence is enabled for a
transaction, the transaction will wait in the queue and block the sending of subsequent transactions until all its preceding
Read and Atomic transactions are executed and responses are received.

                                               Table 7-13 TEO example
 4: Read                  3: Write                 2: Read                  1: Write                 0: Write
 NO                       NO (fence)               NO                       SO                       RO


       1.   Transaction 0 marked as RO is directly sent to the target.
       2.   Transaction 1 marked as SO SHALL be executed after transaction 0 is completed. Two
            implementation options are presented below:
            (1)     Ordered by the initiator: The initiator SHALL NOT directly send the packet
                    corresponding to transaction 1. Due to the possibility of out-of-order execution, the
                    packet of transaction 1, even if being sent later, may arrive earlier than that of
                    transaction 0. Therefore, transaction 1 can be sent only after the transaction response
                    packet indicating that transaction 0 has been executed is received.
            (2)     Ordered by others: The initiator MAY directly send the packet corresponding to
                    transaction 1. When received on the target, the packet will be executed after the
                    execution of transaction 0 is completed.




unifiedbus.com                                                                                                          227
7 Transaction Layer



       3.   Transaction 2 marked as NO does not impose execution order requirements and is not
            blocked by the transaction marked as SO. It can be executed before transaction 1.
       4.   Transaction 3 marked as NO (fence) SHALL be sent only after the preceding Read
            transaction is executed. It blocks the following transaction 4.
       5.   Transaction 4 marked as NO does not impose execution order requirements. It is sent to the
            target after transaction 3 is sent. Transaction 4 may be completed before transaction 3.


7.3.2.3 Transaction Completion Order

TCO defines the sequence in which completion notifications are generated after transactions are
executed. It can be further classified into send completion order and receive completion order. It is used
only for transactions that generate completion notifications.

Note 1: Transaction service modes are only distinguished by implemented TEO method. However, the upper layer can
specify the TCO to ensure the ordering of completion notifications.

Note 2: The generation of a CQE by the initiator is determined at the time the upper layer submits a transaction request.
The target generates a CQE upon completing a transaction that consumes an RQE.

Send completion order is the sequence of generating completion notifications on the initiator. Two types
of send completion orders are provided:

       1.   In-order completion: The sequence in which completion notifications are generated is exactly
            the same as the sequence in which transactions are issued.
       2.   Out-of-order completion: The sequence in which completion notifications are generated may
            not be the same as the sequence in which transactions are issued.

Receive completion order is the sequence of generating completion notifications on the target. Two
types of receive completion orders are provided:

       1.   In-order completion: The sequence in which completion notifications are generated is exactly
            the same as the sequence in which transactions are sent.
       2.   Out-of-order completion: The sequence in which completion notifications are generated may
            not be the same as the sequence in which transactions are sent.

If in-order receive completion is required, the initiator shall include the appropriate TCO flag in the
transaction-layer packet header.


7.3.3 Transaction Service Modes

7.3.3.1 Overview

Transaction service modes include ROI, ROT, ROL, and UNO, classified based on whether the
transaction layer provides reliability and whether and how TEO is implemented. A transaction service
mode is selected by the upper layer according to application needs.

The characteristics of the four transaction service modes are as follows:



unifiedbus.com                                                                                                        228
7 Transaction Layer



      1.   ROI ensures reliable transaction execution. For transactions requiring execution ordering,
           the initiator SHALL wait to receive all responses from preceding dependent transactions
           before sending a new one.
      2.   ROT also ensures reliable transaction execution, whereas the target handles transaction
           ordering if required. This can save one round trip, but consumes additional resources to
           provide ordered execution.
      3.   ROL ensures reliable and ordered transaction execution, relying on the underlying protocol
           for transaction ordering.
      4.   UNO does not ensure reliable or ordered transaction execution.

Reliable transactions without order requirement can be transmitted and executed in any order, and ROI,
ROT, or ROL mode introduces no difference in this case.


7.3.3.2 ROI

ROI ensures a reliable service in which the initiator is responsible for enforcing the execution order of
transactions that have ordering dependencies. Although transaction-layer packets may be transmitted out
of order (such as with multipathing), the initiator SHALL NOT issue a new transaction marked with SO
before all prior transactions with order requirements (SO and RO) have been successfully completed.

The coordination between the transaction layer and lower layers can be as follows:

      1.   If the transport layer uses RTP mode, the transaction layer can specify a transport channel
           group (TPG) or TP channels for each transaction, and the network layer MAY configure per-
           packet or per-flow load balancing.
      2.   If the transport layer uses CTP or TP bypass mode, per-packet load balancing is
           RECOMMENDED for the network layer.

Assume that the order flags of transactions 1, 2, and 3 are NO, RO, and SO, respectively. The
transaction interaction process in ROI mode is shown in the following figure.




unifiedbus.com                                                                                              229
7 Transaction Layer




                               Figure 7-19 Interaction process in ROI mode


7.3.3.3 ROT

ROT is a reliable service mode that supports out-of-order transmission of transaction-layer packets.
Unlike ROI mode, ROT requires the target to ensure transaction ordering. The initiator can send all
transactions regardless of their order flags to the target without waiting for their responses.

Assume that the order flags of transactions 1, 2, and 3 are NO, RO, and SO, respectively. The
transaction interaction process in ROT mode is shown in the following figure.




                               Figure 7-20 Interaction process in ROT mode



unifiedbus.com                                                                                         230
7 Transaction Layer



To determine whether a transaction can be executed, the target needs separate resources (sequence
context) to maintain information required to apply the TEO (such as TASSN and SO/RO/NO flags). After
receiving out-of-order transactions, the target ensures transaction ordering. The implementation details
are outside the scope of this specification. Two possible methods are as follows:

      1.   The target does not buffer transactions with order requirements upon receipt; instead, it
           discards them and sends abnormal TAACKs to the initiator to trigger retransmission. While
           this method is simple, it results in many retransmissions.
      2.   The target buffers transactions with the SO flag until all preceding transactions with SO and
           RO flags have been executed. This approach reduces retransmissions but requires more
           buffer space.

To reduce resource overheads, the initiator needs to apply for SC resources first. If SC resources are
allocated, the target can implement transaction ordering. Otherwise, the target does not have the
ordering capability and the transaction service falls back to another ordering mode. SC resources may
be provisioned by static configuration or dynamic allocation.

The following figure shows the process of dynamically applying for and using SC resources.




                           Figure 7-21 Dynamic resource application in ROT mode

      1.   To apply for SC resources, the BTAH.Alloc field in the transaction request packet SHALL be
           set to 1.
      2.   In the transaction response returned by the target, the ATAH.SV field can be 0 or 1. Value 0
           indicates a resource allocation failure, and the target does not provide the ordering
           capability; value 1 indicates a successful resource allocation, and the ATAH.INI_TASSN field
           indicates the ID of the allocated SC. If an SC is allocated, the target maps the SCID to the
           initiator's transaction sending context (RCID).
      3.   After the SCID is obtained, the initiator issues a transaction operation again. In the packet
           header, the BTAH.INI_RC_Type field SHALL be set to SC and BTAH.INI_RC_ID to the
           obtained SCID.




unifiedbus.com                                                                                             231
7 Transaction Layer



       4.   When the target returns a transaction response, ATAH.INI_RC_ID SHALL be set to the
            RCID corresponding to the SCID.

Note: If resources are statically allocated, steps 1 and 2 can be skipped. Other steps are the same.

ROT mode utilizes the transport and network layers similarly to ROI mode.


7.3.3.4 ROL

In ROL mode, the target relies on the underlying protocol to guarantee the TEO. Whether transactions
can be transmitted out of order depends on whether lower layers can guarantee transaction ordering.

To guarantee the TEO if required, the underlying protocol needs to ensure that transaction-layer
packets are received in order. Two alternative coordination methods between the transaction layer in
ROL mode and lower layers are defined:

       1.   If the transport layer uses RTP mode, the same TP channel needs to be specified for
            transactions with order requirements, and the network layer MAY configure per-packet or
            per-flow load balancing. When per-packet load balancing is used, transaction-layer packets
            can be transmitted out of order. The transport layer of the target delivers the packets to the
            upper layer in order.
       2.   If the transport layer uses CTP or TP bypass mode, the network layer SHALL use per-flow
            load balancing, that is, single-path transmission.

In addition, due to potential out-of-order delivery within the target's network on chip (NoC), the
underlying protocol SHALL ensure that preceding transactions with ordering relationships have been
processed before a new transaction is issued by the initiator to guarantee ordered execution. If the
underlying protocol lacks this capability, the transaction layer should cooperate to fulfill this function.

Assume that the order flags of transactions 1, 2, and 3 are NO, RO, and SO, respectively. The
transaction interaction process in ROL mode is shown in the following figure.




                                   Figure 7-22 Interaction process in ROL mode




unifiedbus.com                                                                                                232
7 Transaction Layer



7.3.3.5 UNO

UNO is an unreliable and unordered transaction service mode. It allows out-of-order transmission of
transaction-layer packets to the network.

In UNO mode, the transaction payload size SHALL NOT exceed the maximum transmission unit (MTU)
of the transport layer.

The UNO mode can work with the UTP, CTP, or TP bypass mode.


7.3.4 Coordination with Lower Layers
Transaction service reliability includes packet transmission reliability and transaction execution
reliability. Packet transmission reliability relies on the underlying protocol.

The transaction layer can provide the transaction ordering capability based on upper-layer
requirements. When ROI or ROT mode is used, transaction-layer packets can be transmitted through
multiple paths to fully utilize network bandwidth. Multipath transmission can be implemented by
specifying a TPG or multiple TP channels in the transport layer, configuring load balancing in the
network layer, or using both of them. For details, refer to Chapter 5 and Chapter 6. When transaction
ordering is delegated to lower layers (ROL mode), there are two cases:

       1.   If the transport layer uses RTP mode, the in-order processing capability of TP channels can
            be used to ensure transaction ordering by using the same TP channel for transactions with
            order requirements. In RTP mode, transaction-layer packets within one transaction can be
            transmitted out of order, and the target's transport layer restores the order.
       2.   If the transport layer uses CTP or TP bypass mode, the transport layer does not provide an
            ordering guarantee. Transactions with order requirements need to be transmitted through a
            single path. In this case, the multipath mode SHALL use per-flow load balancing.

The following table lists the coordination relationships between transaction service modes and the
transport, network, and data link layers for transactions with TEO requirements.

       Table 7-14 Coordination between the transaction layer and lower layers (with TEO requirements)
 Mode             Transport Layer                     Network Layer                  Data Link Layer
 ROI, ROT         RTP: Specify a TPG or               RT[0]: MAY be set to 0 or 1.   RECOMMENDED to
                  multiple TP channels.                                              provide reliability.
                  CTP/TP bypass: No need to           RT[0]: Value 1 is              SHALL provide
                  specify a TPG or TP channels.       RECOMMENDED.                   reliability.
                  UTP: Not allowed.                   /                              /
 ROL              RTP: Specify a single TP            RT[0]: MAY be set to 0 or 1.   RECOMMENDED to
                  channel.                                                           provide reliability.
                  CTP/TP bypass: No need to           RT[0]: SHALL be set to 0.      SHALL provide
                  specify a TPG or TP channels.                                      reliability.
                  UTP: Not allowed.                   /                              /




unifiedbus.com                                                                                          233
7 Transaction Layer



 Mode            Transport Layer                    Network Layer                    Data Link Layer
 UNO             CTP/TP bypass: No need to          RT[0]: MAY be set to 0 or 1.     No requirements.
                 specify a TPG or TP channels.
                 UTP: No need to specify a          RT[0]: MAY be set to 0 or 1.     No requirements.
                 TPG or TP channels.
                 RTP: Not recommended.              /                                /


The following table lists the coordination relationships between transaction service modes and the
transport, network, and data link layers for transactions without TEO requirements. By default, such
transactions can be transmitted through multiple paths and executed out of order.

     Table 7-15 Coordination between the transaction layer and lower layers (without TEO requirements)
 Mode                 Transport Layer                       Network Layer                Data Link Layer
 ROI, ROT, ROL        RTP: Specify a TPG or multiple        RT[0]: MAY be set to 0       RECOMMENDED
                      TP channels.                          or 1.                        to provide reliability.
                      CTP/TP bypass: No need to             RT[0]: Value 1 is            SHALL provide
                      specify a TPG or TP channels.         RECOMMENDED.                 reliability.
                      UTP: Not allowed.                     /                            /
 UNO                  CTP/TP bypass: No need to             RT[0]: MAY be set to 0       No requirements.
                      specify a TPG or TP channels.         or 1.
                      UTP: No TP channel.                   RT[0]: MAY be set to 0       No requirements.
                                                            or 1.
                      RTP: Not recommended.                 /                            /


7.4 Transaction Types

7.4.1 Overview
The transaction layer supports four types of transactions: memory, message, maintenance, and
management transactions.

      1.   The initiator can directly access target memory segments via memory transactions, such as
           Write, Read, and Atomic. For details, refer to Section 7.4.2.
      2.   The initiator can send messages to the target using message transactions like Send, and the
           target processes the messages. For details, refer to Section 7.4.3.
      3.   The initiator can update the target's operating status such as cache status using
           maintenance transactions. For details, refer to Section 7.4.4.
      4.   The initiator can perform device management and fault reporting through management
           transactions. For details, refer to Section 7.4.5.

Each transaction includes one or more transaction operations, each identified by a unique TAOpcode.
The transaction layer defines the interaction process and packet format for each transaction operation.




unifiedbus.com                                                                                               234
7 Transaction Layer



The transaction processing flow varies according to the transaction service mode and transport layer
mode in use. For example, the processing may differ in whether another transaction request cannot be
sent until a response is received, or whether multipathing is allowed. For details, see Section 7.4.2 to
Section 7.4.5. The set of supported transactions is not restricted by this specification and can be
expanded further based on application requirements for optimization.


7.4.2 Memory Transactions

7.4.2.1 Write Transactions

7.4.2.1.1 Write

The initiator issues a Write transaction to write local data to the specified memory segment on the
target. Write transactions are supported by the ROI, ROT, and ROL transaction service modes.

Figure 7-23 shows the processing sequence of the Write transaction.




                                 Figure 7-23 Write transaction processing flow

      1.   The initiator issues a Write transaction to the target. A single Write transaction can be sent in
           multiple packets. The following figure shows the transaction header format for each packet.
           For details, see Section 7.2.



           Specifically:
           −   BTAH.TAOpcode: SHALL be set to 0x3.
           −   BTAH.INI_TASSN: transaction segment sequence number. This field needs to be carried
               in the TAACK returned by the target. The initiator identifies which transaction request is
               responded to based on this field.
               Note: If the transport layer uses RTP mode, the Write transaction can be segmented, and the segment
               size can exceed a single packet. If the transport layer uses CTP or TP bypass mode, the Write
               transaction also supports segmentation, and one segment corresponds to a single packet.




unifiedbus.com                                                                                                  235
7 Transaction Layer



           −   BTAH.UD_Flag: MAY be set to 0 or 1.
           −   BTAH.TV_EN: MAY be set to 0 or 1.
           −   MAETAH.Address: start memory address for storing the data carried by this packet on the
               target. If the data length of the Write transaction exceeds the MTU of the transport layer,
               the MAETAH.Address field of each packet SHALL be the access address of the previous
               packet plus the MTU size.
           −   MAETAH.Length: length of data written to the target memory.
           −   MAETAH.SO: MAY be set to 0 or 1. It is valid only in the compact packet format.
           −   If the full packet format is used, the packet header SHALL contain the following information:
               (1) BTAH.ODR: If there is no order requirement, this field SHALL be set to 3'b000.
                   Otherwise, it SHALL be set to 3'b001 or 3'b010.
               (2) BTAH.MT_EN: SHALL be set to 0.
               (3) BTAH.INI_RC_Type: initiator's transaction request context type. It SHALL be set to
                   2'b10 only when the transaction service mode is ROT and an SCID has been
                   allocated. Otherwise, it SHALL be set to 2'b00 or 2'b01.
               (4) BTAH.INI_RC_ID: requester context ID, which identifies the initiator's transaction request
                   context information. This field SHALL be echoed back when a TAACK is returned.
      2.   After receiving the Write packet, the target completes the transaction execution with the help of
           the UB memory management unit (UMMU) and returns a TAACK. If an exception occurs during
           transaction execution, exception information needs to be carried in the TAACK and returned to
           the initiator. TAACK is not necessary in some scenarios. For details, see Section 7.3.1.1.
           The following figure shows the TAACK packet header format. For details, see Section 7.2.



           Specifically:
           −   ATAH.TAOpcode: SHALL be set to 0x11.
           −   ATAH.INI_TASSN: SHALL be the same as that of INI_TASSN in the Write packet.
           −   ATAH.Status: MAY be set to 0 or 1. It is valid only in the compact packet format.
           −   If the full packet format is used, the packet header SHALL contain the following
               information:
               (1) ATAH.INI_RC_Type: SHALL be the same as that of BTAH.INI_RC_Type in the Write
                   packet.
               (2) ATAH.INI_RC_ID: SHALL be the same as that of BTAH.INI_RC_ID in the Write
                   packet.
               (3) ATAH.RSPST: transaction completion status, including exception information if
                   detected.
      3.   After receiving the TAACK, the initiator notifies the upper layer if the transaction response
           contains no exception. If the ATAH.Status or ATAH.RSPST field in the TAACK indicates
           abnormal transaction processing, the exception handling procedure starts. For details, see
           Section 7.3.1.1.



unifiedbus.com                                                                                             236
7 Transaction Layer



7.4.2.1.2 Write_with_notify

The initiator issues a Write_with_notify transaction to write local data to a specified memory segment on
the target and includes notification data in the final packet of the transaction. Notification data SHALL
be processed only after all Write packets of the transaction have been processed, and the notification
data is written into a separate memory segment. Write_with_notify transactions are supported by the
ROI, ROT, and ROL transaction service modes.

Notification data and Write data within the same transaction require in-order processing. The
transaction processing flow is determined by the transaction service mode in use. For details about the
coordination with lower layers, see Table 7-14.

For ROI mode, the Write_with_notify processing flow is as follows:




                        Figure 7-24 Write_with_notify transaction processing flow (ROI)

      1.   The initiator issues a Write_with_notify transaction. The packet format and field settings of
           Write packets are the same as those in the Write transaction. For details, see Section
           7.4.2.1.1.
      2.   After receiving a Write packet, the target updates the memory and returns a TAACK. If an
           exception occurs during transaction execution, the target carries exception information in the
           TAACK. The TAACK packet format and requirements are the same as those in the Write
           transaction. For details, see Section 7.4.2.1.1.
      3.   After receiving TAACK to all Write transaction data segments, the initiator sends the last
           transaction segment that SHALL carry notification data. In the received TAACKs, if the
           ATAH.Status or ATAH.RSPST field indicates a transaction processing exception, the
           exception handling procedure starts. For details, see Section 7.3.1.1. The format of the last
           packet is as follows. For details, see Section 7.2.




unifiedbus.com                                                                                          237
7 Transaction Layer




           Specifically:
           −   BTAH.TAOpcode: SHALL be set to 0x5.
           −   BTAH.UD_Flag: MAY be set to 0 or 1.
           −   BTAH.MT_EN: SHALL be set to 0.
           −   The NTFETAH SHALL be included, which contains the start address of the memory
               segment where notification data will be written, access credentials, and notification data.
      4.   After receiving the notification data, the target returns a TAACK. The TAACK packet format
           is the same as that in step 2.
      5.   The initiator receives the TAACK, and the transaction is complete. If the ATAH.Status or
           ATAH.RSPST field in the TAACK indicates a transaction processing exception, the exception
           handling procedure starts. For details, see Section 7.3.1.1.

For ROT mode, the Write_with_notify processing flow is as follows:




                      Figure 7-25 Write_with_notify transaction processing flow (ROT)

Unlike ROI mode, the target's transaction layer provides the ordering capability in ROT mode.
Notification data and Write data can be sent to the target, without waiting for all TAACKs of Write data.
Even if the target receives the notification data before all corresponding Write data, it SHALL defer
processing the notification until all associated Write data have been received and committed to memory.

For ROL mode, the Write_with_notify processing flow is as follows:




unifiedbus.com                                                                                          238
7 Transaction Layer




                      Figure 7-26 Write_with_notify transaction processing flow (ROL)

Differences between the transaction processing flow in this mode and that in ROI mode:

      1.   In ROL mode, the underlying protocol provides the ordering capability, and notification data
           and Write data can be sent to the target together. For details about the ordering manners,
           see Section 7.3.3.4.
      2.   After receiving transaction-layer packets, the target can carry TAACKs in transport-layer
           responses if the transport layer uses RTP mode. If the CTP mode is used, the upper layer
           can determine whether TAACKs are needed.


7.4.2.1.3 Write_with_be

The initiator issues a Write_with_be transaction to write local data to the specified memory segment on
the target. The transaction carries the BE field to specify which bytes in the payload are valid. Only valid
bytes are written to the target memory.

A Write_with_be transaction contains a single packet. The BE field can be 64/128/256/512/1024
bits, corresponding to the 64/128/256/512/1024-byte payload length of the Write_with_be
transaction respectively. Write_with_be transactions are supported by the ROI, ROT, and ROL
transaction service modes.

The processing flow for a Write_with_be transaction is identical to that of a standard Write transaction,
as described in Section 7.4.2.1.1.

The following figure shows the Write_with_be packet format. For details, see Section 7.2.



Specifically:

      1.   BTAH.TAOpcode: SHALL be set to 0x14.




unifiedbus.com                                                                                          239
7 Transaction Layer



      2.   BTAH.UD_Flag: MAY be set to 0 or 1.
      3.   BEETAH: The BE field SHALL be carried. Typically, it is NOT RECOMMENDED that the payload
           length exceed the bit width of the BEETAH. However, when the payload length does exceed the
           bit width, any payload data extending beyond the BE range is considered valid by default.


7.4.2.1.4 Writeback

The initiator issues a Writeback transaction to write data from its local cache to a specified memory segment
on the target. Writeback transactions are supported by the ROI and ROL transaction service modes.

A Writeback transaction contains only a single packet, and its processing flow is the same as that of a
Write transaction. The following figure shows the Writeback packet format. For details, see Section 7.2.



Specifically:

      1.   BTAH.TAOpcode: SHALL be set to 0x17.
      2.   BTAH.UD_Flag: MAY be set to 0 or 1.
      3.   BTAH.TV_EN: MAY be set to 0 or 1.

Compared with Write transactions, Writeback processing mandates non-blocking execution; specifically,
it SHALL NOT be blocked by common read or write operations, as this may lead to deadlocks.


7.4.2.1.5 Writeback_with_be

The initiator issues a Writeback_with_be transaction to write data in local cache to a specified memory
segment on the target. The transaction carries the BE field to specify which bytes in the payload are
valid. Only valid bytes are written to the target memory.

A Writeback_with_be transaction contains a single packet. The BE field can be 64/128/256/512/1024
bits, corresponding to the 64/128/256/512/1024-byte payload length of the Writeback_with_be
transaction respectively. Writeback_with_be transactions are supported by the ROI and ROL
transaction service modes.

The processing flow for a Writeback_with_be transaction is identical to that of a standard Write transaction.

The following figure shows the Writeback_with_be packet format. For details, see Section 7.2.



Specifically:

      1.   BTAH.TAOpcode: SHALL be set to 0x18.
      2.   BTAH.UD_Flag: MAY be set to 0 or 1.
      3.   BTAH.TV_EN: MAY be set to 0 or 1.
      4.   The BEETAH SHALL be included, which specifies valid bytes.

Writeback_with_be processing complies with the same principles as Writeback.



unifiedbus.com                                                                                             240
7 Transaction Layer



7.4.2.2 Read Transaction

The initiator issues a Read transaction to read data from a specified memory segment on the target to
the local memory. Read transactions are supported by the ROI, ROT, and ROL service modes, and
transaction segmentation is allowed for read requests only.

Figure 7-27 shows the Read transaction processing flow.




                                 Figure 7-27 Read transaction processing flow

      1.   The initiator sends a read request to the target. The following figure shows the transaction-
           layer request packet format. For details, see Section 7.2.



           Specifically:
           −   BTAH.TAOpcode: SHALL be set to 0x6.
           −   BTAH.INI_TASSN: transaction segment sequence number. This field needs to be included
               in the read response returned by the target. The initiator identifies which transaction
               request is responded to based on this field.

               Note: If the transport layer uses RTP mode, the Read transaction supports request segmentation. This
               field represents the sequence number of each request segment, and the response to a request segment
               may exceed one packet. If the transport layer uses CTP or TP bypass mode, the Read transaction also
               allows request segmentation, whereas a response is a packet. The Read transaction does not support
               read response segmentation; otherwise, an exception occurs when one read request TASSN
               corresponds to multiple read response TASSNs.

           −   BTAH.TV_EN: MAY be set to 0 or 1.
           −   MAETAH.Address: target memory address to be read from.
           −   MAETAH.Length: total length of the target memory data to be read.
           −   MAETAH.SO: MAY be set to 0 or 1. It is valid only in the compact packet format.
           −   If the full packet format is used, the packet header SHALL contain the following information:




unifiedbus.com                                                                                                   241
7 Transaction Layer



               (1) BTAH.ODR: If there is no order requirement, this field SHALL be set to 3'b000.
                   Otherwise, it SHALL be set to 3'b001 or 3'b010.
               (2) BTAH.MT_EN: SHALL be set to 0.
               (3) BTAH.INI_RC_Type: initiator's transaction request context type. It SHALL be set to
                   2'b10 only when the transaction service mode is ROT and an SCID has been
                   allocated. Otherwise, it SHALL be set to 2'b00 or 2'b01.
               (4) BTAH.INI_RC_ID: This field SHALL be included when the target returns a read
                   response.
           −   TAIDETAH.TAID: (optional) task ID. This field may be included within a read response.
           −   OFSTETAH.Offset: (optional) offset of the packet within the transaction-layer request.
               This field may be included when the target returns a read response, enabling the initiator
               to write the read response data to its local memory.
      2.   Upon receiving the read request, the target reads the memory and returns a read response.
           If an exception occurs when the memory is read, exception information needs to be carried
           in the read response and returned to the initiator. If the transport layer uses RTP mode, the
           target can return the transaction status through the transport layer if transaction-layer
           resources are insufficient.
           The following figure shows the read response packet format. For details, see Section 7.2.



           Specifically:
           −   ATAH.TAOpcode: SHALL be set to 0x12.
           −   ATAH.INI_TASSN: SHALL be the same as that of BTAH.INI_TASSN in the Read packet.
           −   ATAH.Status: MAY be set to 0 or 1.
           −   If the full packet format is used, the packet header SHALL contain the following
               information:
               (1) ATAH.INI_RC_Type: SHALL be the same as that of BTAH.INI_RC_Type in the Read
                   packet.
               (2) ATAH.INI_RC_ID: SHALL be the same as that of BTAH.INI_RC_ID field in the Read
                   packet.
               (3) ATAH.RSPST: transaction completion status.
           −   TAIDETAH.TAID: task ID. The value SHALL be the same as that of the TAIDETAH.TAID
               field in the Read packet, allowing the initiator to identify which read request or segment is
               responded to.
           −   OFSTETAH.Offset: SHALL be the same as that of OFSTETAH.Offset in the read request.
      3.   After the initiator receives the read response, the transaction is complete. In the received read
           response, if the ATAH.Status or ATAH.RSPST field indicates a Read transaction processing
           exception, the exception handling procedure starts. For details, see Section 7.3.1.1.




unifiedbus.com                                                                                           242
7 Transaction Layer



7.4.2.3 Atomic Transactions

7.4.2.3.1 Atomic Transaction Overview

The initiator issues Atomic transactions to perform atomic operations on data in specified target
memory segments, including read, write, calculation, and swap. After completing an atomic operation,
the target returns an atomic response to the initiator, carrying data requested by the initiator and
notifying the initiator of the transaction processing status, such as successful processing or exception.
The execution of an Atomic transaction SHALL guarantee atomicity and SHALL be performed only
once. An Atomic transaction contains a single packet and is supported by the ROI, ROT, and ROL
service modes.

Atomic transactions are further divided into the following subtypes:

      ⚫    Atomic_compare_swap
      ⚫    Atomic_swap
      ⚫    Atomic_load
      ⚫    Atomic_store
      ⚫    Atomic_fetch_add
      ⚫    Atomic_fetch_sub
      ⚫    Atomic_fetch_and
      ⚫    Atomic_fetch_or
      ⚫    Atomic_fetch_xor

Figure 7-28 shows the Atomic transaction processing flow (taking Atomic_load as an example; other
subtypes are similar).




                              Figure 7-28 Atomic transaction processing flow




unifiedbus.com                                                                                         243
7 Transaction Layer



7.4.2.3.2 Atomic Request

The initiator sends an atomic request to the target. The Payload field in the atomic request packet
includes operands required in the Atomic transaction. Two consecutive operands (operand 1 and
operand 2, identical in length) are included. If the atomic request requires only operand 1, operand 2 is
ignored by the target.

The following figure shows the transaction-layer request packet format. For details, see Section 7.2.



Specifically:

       ⚫   BTAH.TAOpcode: transaction subtype. The following table describes each transaction subtype.
                                 Table 7-16 Atomic transaction subtypes
 TAOpcode        Subtype              Transaction Behavior
 0x7             Atomic_compare       The initiator sends the swap data (operand 1) and compare data
                 _swap                (operand 2) to the target. The target compares operand 2 with
                                      data in the specified local memory. If operand 2 is the same as
                                      the local data, the target swaps the local data with operand 1;
                                      otherwise, it makes no swap. Additionally, the local data is
                                      returned to the initiator.
 0x8             Atomic_swap          The initiator sends the swap data (operand 1) to the target. The
                                      target swaps operand 1 with data in the specified local memory
                                      and returns the local data before the swap to the initiator.
 0x9             Atomic_store         The initiator sends data (operand 1) to the target. After
                                      calculation, the target updates the specified local memory and
                                      does not return original data before the calculation. The
                                      following subtypes (carried in the UDETAH) are supported:
                                      ● 0x0: ADD. Adds the operand to data in the specified local
                                        memory.
                                      ● 0x1: CLR. Performs a bitwise XOR of the operand and data
                                        in the specified local memory.
                                      ● 0x2: EOR. Performs a bitwise AND of the bitwise inverse of
                                        the operand and the data in the specified local memory.
                                      ● 0x3: SET. Performs a bitwise OR of the operand and data in
                                        the specified local memory.
                                      ● 0x4: SMAX. Compares the signed operand with data in the
                                        specified local memory and returns the larger value.
                                      ● 0x5: SMIN. Compares the signed operand with data in the
                                        specified local memory and returns the smaller value.
                                      ● 0x6: UMAX. Compares the unsigned operand with data in the
                                        specified local memory and returns the larger value.
                                      ● 0x7: UMIN. Compares the unsigned operand with data in the
                                        specified local memory and returns the smaller value.
 0xA             Atomic_load          The initiator sends data (operand 1) to the target. After
                                      calculation, the target updates the specified local memory and
                                      writes original data before the calculation to the specified




unifiedbus.com                                                                                          244
7 Transaction Layer



 TAOpcode        Subtype               Transaction Behavior
                                       memory on the initiator. The supported subtypes are the same
                                       as those of Atomic_store.
 0xB             Atomic_fetch_add      The initiator sends data (operand 1) to the target. The target
                                       adds data in the specified local memory to operand 1, writes the
                                       calculation result to the local memory, and returns data before
                                       calculation to the specified memory on the initiator.
 0xC             Atomic_fetch_sub      The initiator sends data (operand 1) to the target. The target
                                       subtracts operand 1 from data in the specified local memory,
                                       writes the calculation result to the local memory, and returns
                                       data before calculation to the specified memory on the initiator.
 0xD             Atomic_fetch_and      The initiator sends data (operand 1) to the target. The target
                                       performs a bitwise AND operation on operand 1 and data in the
                                       specified local memory, writes the calculation result to the local
                                       memory, and returns data before calculation to the specified
                                       memory on the initiator.
 0xE             Atomic_fetch_or       The initiator sends data (operand 1) to the target. The target
                                       performs a bitwise OR operation on operand 1 and data in the
                                       specified local memory, writes the calculation result to the local
                                       memory, and returns data before calculation to the specified
                                       memory on the initiator.
 0xF             Atomic_fetch_xor      The initiator sends data (operand 1) to the target. The target
                                       performs a bitwise XOR operation on operand 1 and data in the
                                       specified local memory, writes the calculation result to the local
                                       memory, and returns data before calculation to the specified
                                       memory on the initiator.


       ⚫   BTAH.INI_TASSN: transaction segment sequence number. This field needs to be carried in
           the response returned by the target so that the initiator can identify the transaction request
           that the response is associated with.
       ⚫   BTAH.UD_Flag: MAY be set to 0 or 1. When the transaction subtype is Atomic_load or
           Atomic_store, UDETAH[23:20] identifies the transaction subtype.
       ⚫   BTAH.TV_EN: MAY be set to 0 or 1.
       ⚫   MAETAH.Address: target memory address. For an Atomic transaction, the address of atomic
           operands SHALL be aligned. For example, the address of a 4-byte Atomic transaction shall
           be 4-byte aligned.
       ⚫   MAETAH.Length: atomic operand length, which can be 1, 2, 4, 8, 16, 32, or 64 bytes.
       ⚫   MAETAH.SO: MAY be set to 0 or 1. It is valid only in the compact packet format.
       ⚫   If the full packet format is used, the packet header SHALL contain the following information:
           (1)   BTAH.ODR: If there is no order requirement, this field SHALL be set to 3'b000.
                 Otherwise, it SHALL be set to 3'b001 or 3'b010.
           (2)   BTAH.MT_EN: SHALL be set to 0.
           (3)   BTAH.INI_RC_Type: initiator's transaction request context type. It SHALL be set to
                 2'b10 only when the transaction service mode is ROT and an SCID has been
                 allocated. Otherwise, it SHALL be set to 2'b00 or 2'b01.



unifiedbus.com                                                                                          245
7 Transaction Layer



           (4)     BTAH.INI_RC_ID: This field identifies the initiator's transaction request context
                   information. It SHALL be carried when a TAACK is returned.
      ⚫    The TAIDETAH can be used to carry the task ID for the initiator to search for the specific
           transaction. If the request contains the TAIDETAH, its atomic response should also carry
           this field.
      ⚫    The following table shows the Payload format (an Atomic_compare_swap request with an
           operand length of 8 bytes):
           Byte0                      Byte1                      Byte2                      Byte3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
      Operand1[7:0]              Operand1[15:8]            Operand1[23:16]            Operand1[31:24]
    Operand1[39:32]              Operand1[47:40]           Operand1[55:48]            Operand1[63:56]
      Operand2[7:0]              Operand2[15:8]            Operand2[23:16]            Operand2[31:24]
    Operand2[39:32]              Operand2[47:40]           Operand2[55:48]            Operand2[63:56]


7.4.2.3.3 Atomic Response

After receiving an atomic request, the target processes the request and returns an atomic response. If a
transaction processing exception occurs, exception information needs to be carried in the atomic
response packet header. If the transport layer uses RTP mode, the target can return transaction status
through the transport layer if transaction-layer resources are insufficient.

The following figure shows the atomic response packet format. For details, see Section 7.2.



Specifically:

      ⚫    ATAH.TAOpcode: SHALL be set to 0x13.
      ⚫    ATAH.INI_TASSN: SHALL be the same as that of BTAH.INI_TASSN in the atomic request
           packet.
      ⚫    ATAH.Status: This field carries target authentication results. It is valid only in the compact
           packet format.
      ⚫    If the full packet format is used, the packet header SHALL contain the following information:
           (1)     ATAH.INI_RC_ID: SHALL be the same as that of BTAH.INI_RC_ID in the atomic
                   request packet.
           (2)     ATAH.RSPST: transaction layer completion status.
      ⚫    TAIDETAH: SHALL be the same as that in the TAIDETAH of the request.

If the target receives an atomic request of a type other than Atomic_store, the atomic response needs
to include the payload. The payload contains original data used in the Atomic transaction. The data
length is the same as the operand length of the atomic request. The length can be 1, 2, 4, 8, 16, 32, or
64 bytes. The following table shows the payload layout using 8-byte original data as an example.




unifiedbus.com                                                                                              246
7 Transaction Layer



           Byte0                     Byte1                     Byte2                      Byte3
 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0 7 6 5 4 3 2 1 0
   Origin_data[63:56]         Origin_data[55:48]         Origin_data[47:40]         Origin_data[39:32]
   Origin_data[31:24]         Origin_data[23:16]         Origin_data[15:8]           Origin_data[7:0]


The transaction is considered complete upon receipt of the atomic response by the initiator. In the
received atomic response, if the ATAH.Status or ATAH.RSPST field indicates an Atomic transaction
processing exception, the exception handling procedure starts. For details, see Section 7.3.1.1.


7.4.3 Message Transactions

7.4.3.1 Send

The initiator uses Send transactions to send messages to the target. The target consumed RQEs,
which provide buffers to place incoming Send transaction packets. Send transactions are supported by
the ROI, ROT, ROL, and UNO service modes.

The length of a Send transaction SHALL meet the following requirements:

      1.   If the transport layer uses CTP or TP bypass mode, a Send transaction shall contain only a
           single packet. If the transport layer uses RTP mode, the length of a Send transaction is not
           limited; however, all packets of one transaction segment SHALL be transmitted over the
           same TP channel.
      2.   In the UNO transaction service mode, a Send transaction shall contain only a single packet.

Figure 7-29 shows the Send transaction processing flow.




                              Figure 7-29 Send transaction processing flow

      1.   The initiator issues a Send transaction to the target. The following figure shows the
           transaction-layer request packet format. For details, see Section 7.2.




unifiedbus.com                                                                                           247
7 Transaction Layer




           Specifically:
           −   BTAH.TAOpcode: SHALL be set to 0x0.
           −   BTAH.INI_TASSN: transaction segment sequence number. This field needs to be carried
               in the TAACK returned by the target. The initiator identifies which transaction request is
               responded to based on this field.
           −   BTAH.TV_EN: MAY be set to 0 or 1.
           −   BTAH.UD_Flag: MAY be set to 0 or 1.
           −   If the full packet format is used, the packet header SHALL contain the following
               information:
               (1)    BTAH.ODR: If there is no TEO requirement, BTAH.ODR[1:0] SHALL be set to
                      2'b00; on the other hand, BTAH.ODR[1:0] SHALL be set to 2'b01 or 2'b10. If there
                      is no TCO requirement, BTAH.ODR[2] SHALL be set to 0; on the other hand,
                      BTAH.ODR[2] SHALL be set to 1.
               (2)    BTAH.INI_RC_Type: This field SHALL be set to 2'b10 only when the transaction
                      service mode is ROT and an SCID has been allocated. Otherwise, it SHALL be set
                      to 2'b00 or 2'b01.
               (3)    BTAH.INI_RC_ID: requester context ID, which SHALL be carried when the target
                      returns a TAACK.
               (4)    BTAH.MT_EN: SHALL be set to 1b'1.
           −   MTETAH.TGT_TC_Type: MAY be set to a TC or TC group.
           −   MTETAH.TGT_TC_ID: target context ID.
           −   OFSTETAH.Offset: offset of the Send packet in the transaction-layer request, with a
               granularity of 1 KB. The first packet has an offset of 0, and subsequent packets have their
               offset incremented with 1 KB granularity. If the CTP mode is used, this field is reserved.
      2.   After receiving and processing all packets of a Send transaction, the target returns a TAACK.
           If an exception occurs during the processing, exception information needs to be carried in
           the TAACK and returned to the initiator. If the transaction service mode is ROI, ROT, or
           ROL, refer to Section 7.3.1.1 for special TAACK processing. If the transaction service mode
           is UNO, no TAACK is returned.
           The following figure shows the TAACK packet format. For details, see Section 7.2.



           (1) ATAH.TAOpcode: SHALL be set to 0x11.
           (2) ATAH.INI_TASSN: SHALL be the same as that of BTAH.INI_TASSN in the Send packet.
           (3) ATAH.INI_RC_Type: SHALL be the same as that of BTAH.INI_RC_Type in the Send
                 packet.
           (4) ATAH.INI_RC_ID: SHALL be the same as that of BTAH.INI_RC_ID in the Send packet.
           (5) ATAH.RSPST: transaction layer completion status.




unifiedbus.com                                                                                          248
7 Transaction Layer



      3.   The initiator receives the TAACK, and the transaction is complete. If the ATAH.Status or
           ATAH.RSPST field in the TAACK indicates a transaction processing exception, the exception
           handling procedure starts. For details, see Section 7.3.1.1.


7.4.3.2 Send_with_immediate

The initiator can send a message to the target using a Send_with_immediate transaction. The last
packet carries both the Sent data and immediate data. Immediate data SHALL be processed after all
Send packets within the transaction have been processed. Immediate data serves as notification
information (CQE) to promptly alert the target for processing.

Send_with_immediate transactions are supported by the ROI, ROT, ROL, and UNO transaction service
modes.

Similar to the Send transaction, if the transport layer uses CTP mode, a Send_with_immediate
transaction only contains a single packet. If the transport layer uses RTP mode, transaction
segmentation is not allowed. That is, all packets share the same TASSN and are transmitted through
the same TP channel, thereby ensuring ordering via the TP channel.

Figure 7-30 shows the processing flow of a Send_with_immediate transaction.




                       Figure 7-30 Send_with_immediate transaction processing flow

      1.   The initiator issues a Send_with_immediate transaction. If the transaction contains multiple
           packets, preceding packets are Send packets, and the last packet carries both the Send data
           and immediate data. If the transaction contains only a single packet, the packet carries both
           the Send data and immediate data.
           The format and field settings of a Send packet in the Send_with_immediate transaction are
           the same as those in the Send transaction. For details, see Section 7.4.3.1.
           The following figure shows the format of the last packet. For details, see Section 7.2.



           Specifically:




unifiedbus.com                                                                                        249
7 Transaction Layer



           (1) BTAH.TAOpcode: SHALL be set to 0x1.
           (2) BTAH.UD_Flag: MAY be set to 0 or 1.
           (3) The IMMETAH SHALL be included, which contains immediate data (8 bytes),
                 TokenValue, and Msg_length.
           (4) BTAH.MT_EN: SHALL be set to 1.
           (5) MTETAH.TGT_TC_ID: SHALL be set to the ID of the target context for processing
                 immediate data.
      2.   After receiving both Send data and immediate data, the target determines whether to return
           a TAACK based on scenario requirements (the decision criteria are identical to those for a
           Send transaction). The TAACK packet format is the same as that in the Send transaction.
           For details, see Section 7.4.3.1.
      3.   The initiator receives the TAACK, and the transaction is complete. If the ATAH.Status or
           ATAH.RSPST field in the TAACK indicates a transaction processing exception, the exception
           handling procedure starts. For details, see Section 7.3.1.1.


7.4.3.3 Write_with_immediate

The initiator writes local data to a specified memory segment on the target using the
Write_with_immediate transaction. The last packet SHALL carry both Write data and immediate data. In
contrast to the Send transaction, only the processing of the packet that carries immediate data
consumes an RQE on the target. Immediate data SHALL be processed after all packets within the
transaction have been processed, and is written directly into the CQE to notify the target.

Write_with_immediate transactions are supported by the ROI, ROT, and ROL transaction service modes.

The processing flow for Write_with_immediate in each transaction service mode is identical to that of
Write_with_notify, except for the packet format. For details, see Section 7.4.2.1.2. The immediate data
packet format (defined below) in Write_with_immediate is distinct from the notification data packet
format. For details, see Section 7.2.



Specifically:

      ⚫    BTAH.TAOpcode: SHALL be set to 0x4.
      ⚫    BTAH.ODR: If there is no TCO requirement, BTAH.ODR[2] SHALL be set to 0; on the other
           hand, BTAH.ODR[2] SHALL be set to 1.
      ⚫    BTAH.UD_Flag: MAY be set to 0 or 1.
      ⚫    BTAH.MT_EN: SHALL be set to 1.
      ⚫    The IMMETAH SHALL be included, which SHALL contain immediate data and address
           segment access credentials.




unifiedbus.com                                                                                        250
7 Transaction Layer



7.4.4 Maintenance Transaction

7.4.4.1 Prefetch_tgt

The initiator prefetches data on the target by issuing a Prefetch_tgt transaction to optimize latency of
the following Read transaction between the initiator and the target. A Prefetch_tgt transaction contains a
single packet and is supported by the UNO mode.

Figure 7-31 shows the Prefetch_tgt transaction processing flow.




                           Figure 7-31 Prefetch_tgt transaction processing flow

      1.   The initiator issues a Prefetch_tgt transaction to the target. The following figure shows the
           transaction-layer request packet format. For details, see Section 7.2.



           Specifically:
           (1)   BTAH.TAOpcode: SHALL be set to 0x15.
           (2)   BTAH.UD_Flag: MAY be set to 0 or 1.
           (3)   MAETAH.Address: target memory address to be prefetched.
      2.   After receiving the Prefetch_tgt transaction, the target determines whether to allow data
           prefetch and does not need to return a TAACK.
      3.   The initiator does not initiate Prefetch_tgt retry. If an exception is detected during
           communication, the initiator silently discards the transaction without reporting the exception.




unifiedbus.com                                                                                         251
7 Transaction Layer



7.4.5 Management Transaction

7.4.5.1 Management

The Management transaction carries management commands (see Section 10.4.3). Typically, it
imposes no reliability and order requirements, and thus uses the UNO mode.

Figure 7-32 shows the Management transaction processing flow.




                            Figure 7-32 Management transaction processing flow

The following figure shows the Management transaction packet format. For details, see Section 7.2.




Specifically:

      ⚫    BTAH.TAOpcode: SHALL be set to 0x10.
      ⚫    BTAH.TV_EN: SHALL be set to 0.
      ⚫    BTAH.INI_TASSN: message sequence number (MSN) of the request.
      ⚫    BTAH.INI_RC_ID: message queue index (its upper limit is subject to the implementation).
           When returning a response, the upper-layer management software SHALL carry this field to
           identify the transaction initiator.
      ⚫    MGMTETAH: For details, see Section 7.2.12.




unifiedbus.com                                                                                       252
