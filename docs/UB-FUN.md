8 Function Layer




8 Function Layer


8.1 Overview
The function layer is positioned above the transaction layer and implements various functions via the
transaction layer.

The UB function layer comprises programming models and advanced functions built upon these
models. Applications can directly call transaction-layer capabilities through programming models to
perform transaction operations or use advanced functions to simplify the development and improve
efficiency. Users can extend UB with custom programming models and functions.

The UB function layer offers two programming models: load/store synchronous access and unified
remote memory access (URMA) asynchronous access. Both programming models can be used to call
transaction-layer operations, including memory, message, maintenance, and management transactions.

For load/store synchronous access, transactions are initiated by processor instructions, and the UB
Controller—through the network on chip (NoC) of the UB processing unit (UBPU)—converts load/store
instructions into the appropriate transactions (e.g., Read, Write, or Atomic). For URMA asynchronous
access, applications can use APIs provided by Jetty abstraction to establish communication pairs,
submit transaction operations, and poll responses. The URMA programming model requires binding
Jetty to a transaction queue or alternative carriers to submit transactions.

The UB function layer provides three advanced functions, including unified remote procedure call
(URPC), multi-Entity coordination, and Entity management. URPC supports peer-to-peer access
between UBPUs via unified APIs, which leverage programming capabilities provided by load/store and
URMA programming models. Multi-Entity coordination achieves more efficient communication tasks,
such as fusion operations, collective communication operations, and global maintenance, by flexibly
combining transaction-layer mechanisms. Entity management utilizes transaction-layer capabilities to
enable local Entity discovery, pooled Entity registration, configuration management, interrupt and
message notification, communication and remote memory registration control, and virtualization.


8.2 Basic Concepts

8.2.1 Memory Segment

8.2.1.1 Creation/Deletion of Memory Segments

A memory segment is a contiguous address space with a specified size, identified by a UB memory
descriptor (UBMD) that includes the Entity identifier (EID), token ID, and UB address (UBA). The
memory provider application calls a memory allocation interface to create a memory segment of the
desired size and receives the UBMD needed to access it. Typically, the UB memory management unit




unifiedbus.com                                                                                        253
8 Function Layer



(UMMU) assigns physical memory for a memory segment at the time of creation. However, the memory
management system MAY adopt a delayed allocation strategy to allocate physical memory only when
the memory segment is accessed. Multiple memory segments may share a token ID, or each may have
a unique one.

The memory access initiator (user) submits transaction requests to the transaction layer, while the
memory segment provider (home) acts as the target, receiving and processing these memory
transactions from the initiator.

When the Home creates a memory segment, the UMMU configures both the memory address
translation table (MATT) and memory address permission table (MAPT) for the memory segment. For
details, see Section 9.4.

When the Home deletes a memory segment, it SHALL ensure that residual transaction-layer packets
associated with this memory segment within the UB network will not cause data inconsistency.
Therefore, before clearing UMMU entries, it is necessary to ensure that all related memory access
transactions have been completed.


8.2.1.2 Usage of Memory Segments

Before accessing a memory segment on the target, the initiator needs to retrieve information about the
segment from the target. For details, refer to Section 8.2.5.

The initiator can access the memory segment using one of the following methods:

      1.   The initiator maps the memory segment's address information into the local process's virtual
           address space, creating a mapped virtual address (MVA). This allows synchronous or
           asynchronous access to the memory space. For more information, see Section 7.4.
      2.   The initiator can request a memory segment without mapping it, enabling asynchronous
           memory access. For details, refer to Section 7.4.

When accessing a memory segment on the target, the initiator SHALL transmit the memory segment
information (including EID, token ID, and UBA) to the transaction layer, where such information is
encapsulated within a transaction-layer packet. If memory segment security protection is enabled, the
initiator SHALL include the token value in the transaction for validation. For details on access security,
see Section 8.2.4.


8.2.1.3 Memory Segment Access Methods

A target memory segment can be accessed in either of the following methods:

      1.   Memory start address and length
           If the initiator needs to access contiguous addresses within a memory segment, the initiator
           can specify the start address and access length. Whether address alignment is required
           depends on the specific transaction type (see Section 7.4). For example, a 4-byte Atomic
           transaction requires 4-byte address alignment.




unifiedbus.com                                                                                          254
8 Function Layer



      2.   ByteEnable
           If the initiator needs to update specific bytes within a memory segment, it can specify
           ByteEnable to indicate which bytes should be updated. This mechanism improves memory
           access efficiency by ensuring that only the bytes marked as valid are updated, while the
           remaining bytes stay unchanged. An example of this is the Write_with_be transaction.


8.2.2 Jetty

8.2.2.1 Jetty Overview

Jetty serves as URMA's basic abstraction, providing access to the transaction layer. Prior to initiating
message or memory transactions, applications need to invoke APIs to create Jetties, import target
Jetties, and import target memory segments. Each Jetty is assigned a unique identifier (Jetty ID) and
SHALL be associated with one or more transaction queues to convey and handle transactions. For
details, see Section 8.2.3.

Jetties used for transaction sending/receiving can be classified into the following types:

      ⚫    Standard Jetty
           This Jetty type is bound to two transaction queues—send queue (SQ) for outgoing
           transactions and receive queue (RQ) for incoming transactions.
      ⚫    One-sided Jetty
           Unlike the standard Jetty, the one-sided Jetty can be bound exclusively to either an SQ or RQ,
           and is referred to as Jetty for sending (JFS) or Jetty for receiving (JFR), respectively. A one-
           sided Jetty is used in case of unidirectional communication only, which reduces memory
           consumption. The initiator uses JFS to post memory and message transaction requests, while
           the target uses JFR to process and place accepted message transactions. When the initiator
           uses a JFS to access a target memory segment, the target is not required to create a JFR.
      ⚫    Jetty group
           A Jetty group is a special type of Jetty and exists only on the target. A Jetty group is assigned
           a unique Jetty group ID. It contains multiple Jetties, which MAY be standard Jetties or JFRs,
           and needs to be bound to multiple RQs, that is, a RQ group. When sending transaction
           requests, the initiator only needs to specify a Jetty group instead of individual Jetties. After
           receiving the transaction requests, the target distributes them to different Jetties according to
           the scheduling policy, with the entire distribution process occurring without CPU intervention.
           Using the Jetty group type provides the following advantages:
           (1) It offloads request distribution from CPUs to other hardware, eliminating CPU overhead
                 for thread assignment.
           (2) It prevents cross-NUMA access by selecting a Jetty that has NUMA affinity with the
                 processing threads.
           When a Jetty group is utilized, the target chooses a specific Jetty or JFR based on the
           scheduling policy defined during Jetty group creation. The available policies include:




unifiedbus.com                                                                                                255
8 Function Layer



           (1) Hash-based selection using the Hint field provided by the initiator in the packet header
           (2) Round-robin distribution
           (3) Dynamic load balancing based on the RQ depth
           The following figure shows the Jetty group model.




                                        Figure 8-1 Jetty group model

The URMA asynchronous access programming model also provides the Jetty for completion (JFC),
Jetty for completion event (JFCE), and Jetty for asynchronous event (JFAE) to retrieve transaction
execution results or exception events.

A JFC is used to place the transaction completion notification of a specific Jetty and shall be bound to a
unique completion queue (CQ). After the transaction is complete, the transaction layer submits a
completion queue event (CQE) to the CQ as required to notify the transaction completion event and
convey the execution result. UB allows multiple Jetties to share one JFC. That is, the CQ can store the
completion notifications of multiple Jetties. Applications can retrieve the transaction completion status by
polling the JFC.

A JFCE is used to notify the user of the transaction completion status through an interrupt. It needs to be
bound to a JFC and a unique event queue (EQ) to carry event data. When the interrupt mechanism is
used for upward notification, the FCE flag MAY be delivered within a transaction request to trigger the
immediate generation of an event upon transaction completion. Alternatively, events MAY be produced by
methods such as using a timer or when a specified number of completion notifications has been reached.

A JFAE keeps asynchronous event reports. Users can acquire various exception events through the
JFAE, including Jetty, driver, and hardware exceptions. JFAE needs to be bound to an EQ.


8.2.2.2 Jetty Communication Relationships

Jetty communication operates in two models: many-to-many and one-to-one. Regardless of the
communication model, the initiator and target need to exchange Jetty information, such as the Jetty
type and Jetty ID. For details about the Jetty information exchange process, see Section 8.2.5.

      ⚫    Many-to-many communication
           There is no one-to-one binding relationship between initiator Jetties and target Jetties. An
           initiator Jetty can communicate with any target Jetty, and a target Jetty can receive



unifiedbus.com                                                                                            256
8 Function Layer



          transaction requests from any initiator Jetty. Many-to-many communication requires fewer
          Jetties and avoids Jetty resource waste. Because an initiator Jetty can communicate with
          any target Jetty, the initiator SHALL specify a target Jetty when issuing a transaction request.
          When the target Jetty returns a response, it SHALL carry the initiator Jetty information in the
          transaction response.
          Both standard Jetties and one-sided Jetties can use the many-to-many communication
          model. The model architecture is as follows:




                               Figure 8-2 Many-to-many Jetty communication

          The initiator's URMA asynchronous access process is defined as follows:
          (1) The initiator obtains the target Jetty information (including the Jetty type and Jetty ID)
                 and applies for the Jetty.
          (2) Since the initiator can send a transaction request to any target in this model, it SHALL
                 specify the target Jetty information in the transaction request.
          (3) Since the target can receive transactions from any initiator, it SHALL carry the initiator
                 Jetty information in the transaction response to facilitate initiator processing.
      ⚫   One-to-one communication
          There is a one-to-one binding relationship between initiator Jetties and target Jetties. An
          initiator Jetty only communicates with the bound target Jetty, and a target Jetty only receives
          transaction requests from the bound initiator Jetty.
          Only standard Jetties can use the one-to-one communication model. The model architecture
          is as follows:




                                 Figure 8-3 One-to-one Jetty communication

          The initiator's asynchronous access process is similar to that in many-to-many communication,
          but it restricts each initiator Jetty and target Jetty to interact with the bound Jetty only.




unifiedbus.com                                                                                             257
8 Function Layer



8.2.2.3 Jetty State Machine

The Jetty state machine operates through four states: Reset, Ready, Suspend, and Error. At any time
during its operation, an application may destroy the Jetty by invoking the Jetty destruction API. Figure 8-4
provides a visual representation of state transitions.




                                        Figure 8-4 Jetty state machine

      1.   Reset state
           A newly created Jetty SHALL enter the Reset state, where all associated resources are
           allocated and its attributes are initialized.
           A Jetty may enter the Reset state from any state. The application can activate a Jetty by
           invoking the Jetty modification API to transition it from Reset to Ready.
           Transaction-layer packets received in the Reset state are silently discarded. Work requests
           received in the Reset state trigger error completion.
      2.   Ready state
           Prior to entering the Ready state, a Jetty SHALL successfully complete its communication
           negotiation process.
           Transaction-layer packets received in the Ready state SHALL be executed normally. Work
           requests received in the Ready state SHALL be executed normally.
           If a recoverable transmission fault occurs, such as a failure in the transport channel, the Jetty
           transitions from the Ready state to the Suspend state. In the event of a severe transmission
           error, for instance, Jetty context corrupted, the Jetty will transition from the Ready state to the
           Error state.
      3.   Suspend state
           Jetties support configuring exception modes, which include "exception continue" and
           "exception suspend" options. The "exception continue" option indicates that a Jetty can
           continue functioning after an error occurs without requiring any user intervention. Conversely,
           the "exception suspend" option indicates that after an error, the Jetty requires manual
           intervention to resume its operation.



unifiedbus.com                                                                                            258
8 Function Layer



           If the exception mode is set to "exception continue", the state of the Jetty remains unchanged
           when a send queue element (SQE) exception is detected or an error response is received. An
           abnormal CQE about this SQE is reported, and subsequent SQEs can proceed as usual. In
           this mode, the Suspend state is bypassed in the Jetty state machine. The Jetty does not
           transition to the Suspend state, remaining in the Ready state even if such errors occur.
           If the exception mode is set to "exception suspend", when an SQE exception is detected or
           an error response is received, an abnormal CQE or asynchronous error is reported, and the
           Jetty transitions from the Ready state to the Suspend state. In the Suspend state, the Jetty
           pauses the processing of new work requests, awaits the completion of already distributed
           SQEs, and flushes the SQ after all CQEs are reported. Despite being suspended, the Jetty
           can still receive transaction-layer packets from the target. If the SQ is not completely flushed
           before a state transition, the Jetty will generate an error.
           −   Once the application has addressed the fault, the Jetty is restored. It then transitions
               from the Suspend state back to the Ready state, resuming normal sending and
               receiving operations.
           −   If the Jetty cannot recover or if the application forces an error, the Jetty transitions from
               the Suspend state to the Error state, becoming inoperable.
      4.   Error state
           When a Jetty enters the Error state, it stops SQE distribution and ceases to receive
           transaction-layer packets. Transaction-layer packets received in the Error state are silently
           discarded. Work requests received in the Error state trigger error completion.
           The application can recover a Jetty by invoking the Jetty modification API to transition it
           from Error to Reset. Before this state transition, all SQEs SHALL complete the reporting of
           error CQEs.


8.2.3 Transaction Queues
Transaction queues serve as the software–hardware interface of asynchronous access programming
models. In the URMA asynchronous access programming model, Jetties, JFCs, and JFCEs need to be
bound to transaction queues and provide direct access to those queues. Transaction queues operate in
first-in, first-out (FIFO) mode. Therefore, transactions in the same queue can be ordered, and
transactions in different queues do not have an order relationship.

Transaction queues are categorized into four types: send queue (SQ), receive queue (RQ), completion
queue (CQ), and event queue (EQ). The use of these queues is determined by the specific transaction
requests. For example, a memory transaction directly operates on the target memory segment and do
not require binding an RQ.

      1.   The SQ stores one or more user-submitted transaction requests, known as SQEs. Each SQ
           corresponds to an independent requester context identifier (RCID).
      2.   The RQ stores transactions to be processed by applications. It can contain one or more
           receive queue elements (RQEs); each RQE holds the context information required for




unifiedbus.com                                                                                             259
8 Function Layer



           processing the received transaction. Each RQ corresponds to an independent target context
           identifier (TCID). Multiple RQs can be grouped and assigned a unique target context group ID.
      3.   The CQ stores completions of processed transactions. It can contain one or more CQEs;
           each CQE holds the transaction execution status. The CQ operates together with the SQ
           and RQ, and the user can obtain the transaction execution status by polling the CQ.
      4.   The EQ stores event notifications and can notify the user of event processing via an interrupt
           mechanism.

When the transaction queues call transaction-layer capabilities, the RCID and TCID will be forwarded to
the transaction layer for packet encapsulation. This information is used to identify the transaction's
initiator or to deliver the transaction to the appropriate Jetty.


8.2.4 Access Security
Before sending a transaction request, the initiator SHALL obtain access credentials of the target Jetty or
memory segment in any of the following ways:

      1.   Retrieve the TCID and token value of the target Jetty from the initiator SQE.
      2.   Retrieve the token ID and token value of the memory segment from the initiator SQE.
      3.   Obtain the token ID and token value through the conversion results of the UB decoder.

For details about access validation, see Chapter 11.


8.2.5 Communication Management
The initiator and target needs to exchange information, such as memory segments and Jetty details.
This exchange MAY be performed through one of the methods listed below (or other methods).
Regardless of which method is used, a transport channel between physical nodes SHALL be
established before information exchange. Three methods are defined as follows:

      1.   Complete information exchange using UB Fabric Managers (UBFMs).
      2.   Utilize a known Jetty to retrieve memory segment information or Jetty information of the
           target, as shown in the following figure.




                                 Figure 8-5 Known Jetty communication flow




unifiedbus.com                                                                                           260
8 Function Layer



           Known Jetties are preconfigured target Jetties that are assigned a known Jetty ID by the
           target during creation. The initiator interacts with a known Jetty through a local Jetty. Each
           known Jetty is dedicated to a single process. If multiple target processes exist, they SHALL
           specify distinct Jetty IDs when creating known Jetties. The table below lists the reserved IDs
           for known Jetties.

                                           Table 8-1 Known Jetties
            Reserved Jetty ID       Usage Description
            0                       Transport-layer information exchange
            1                       Transaction-layer information exchange
            2                       Socket over UB
            3 to 31                 Reserved
            32 to 1023              User-defined


      3.   The initiator establishes TCP/IP connection with the target to retrieve target memory
           segment or Jetty information, as shown in the following figure.




                                  Figure 8-6 TCP/IP communication flow


8.2.6 Memory Borrowing and Sharing
Developers can build memory pools based on the UB transaction layer and function layer programming
models to increase the available memory capacity and bandwidth of a single node. UB's peer-to-peer
architecture allows each UBPU node in a memory pool to function as a memory borrower (accessing
memory from other nodes) or as a memory lender (providing memory for other nodes). These roles can
be dynamically switched, enabling memory to be flexibly allocated and released in response to service
requirements, thereby improving memory utilization.




unifiedbus.com                                                                                          261
8 Function Layer




                           Figure 8-7 Dynamic memory allocation and release

UB supports two memory pooling modes: memory borrowing and memory sharing.

      1.   In memory borrowing mode, the memory borrower can make use of memory from other
           nodes as its local memory. A borrowed memory segment is exclusively accessed by the
           memory borrower.
      2.   In memory sharing mode, a memory segment of the memory provider can be shared by
           multiple memory users.

The initiator MAY use the target memory in either of the following manners:

      1.   Cacheable: The initiator's memory access to the target provides the same cache coherence
           capabilities as local memory access.
      2.   Non-cacheable: The initiator's memory access to the target avoids cache coherence
           management issues to simplify the access path.




                                    Figure 8-8 Memory pooling manners




unifiedbus.com                                                                                   262
8 Function Layer



For applications that exhibit strong data locality, UB supports remote memory access in a cacheable
manner—caching data in the local cache—to reduce read latency and target load. Conversely, for
communication-intensive programs where remote memory access is used primarily for data exchange,
accessing remote memory in a non-cacheable manner can yield better performance.

Typically, the cacheable manner is used in memory borrowing scenarios where a memory segment is
accessed by a unique initiator, and thus no cache incoherence needs to be considered. In memory
sharing scenarios, both manners can be used. When cacheable access is used, cache coherence
between multiple nodes needs to be guaranteed because a memory segment is shared by the nodes.
UB provides an ownership mechanism to control read/write permissions on shared memory, ensuring
cross-node data coherence. This mechanism may be hardware-based or implemented in software.
Implementation details are outside the scope of this specification.

The following is a reference implementation of software and hardware co-designed cache coherence
when multiple nodes share memory in a cacheable manner:

The software defines the ownership concept to manage the ownership status of memory segments at
an arbitrary granularity. Each node maintains an independent local ownership state for a memory
segment, which can be:

      ⚫    Invalid: The local node cannot perform read or write operations on the memory.
      ⚫    Write: The local node can perform read and write operations on the memory.
      ⚫    Read: The local node can perform read operations on the memory.

Write ownership is exclusive: if one node holds write ownership, all others SHALL be in the invalid state.

The user needs to actively transition the ownership state based on memory read/write requirements to
ensure that software operations on the memory adhere to these ownership rules. Actions required for
ownership state transitions:

      ⚫    Write-to-invalid: Clean and invalidate cache. This operation ensures the modified data is
           written back to memory and the corresponding cache data is invalidated.
      ⚫    Write-to-read: Clean cache. This operation ensures the modified data is written back to
           memory while retaining the corresponding cache data to accelerate subsequent read
           operations.
      ⚫    Read-to-invalid: Invalidate cache. This operation ensures the corresponding cache data is
           invalidated and does not affect the in-memory data.
      ⚫    Others: No operation is required.




unifiedbus.com                                                                                          263
8 Function Layer




                                       Figure 8-9 Ownership state transition

Following the preceding procedure ensures the availability of shared memory.


8.2.7 Deadlock Avoidance

8.2.7.1 Overview

Semantic dependencies and resource dependencies exist within computing systems. If not handled
correctly, these dependencies can lead to deadlocks and cause the system to cease work. Given that
UB supports flexible combinations, its chip and software designers and developers should prioritize the
coupling dependencies between functions and identify potential deadlocks. UB provides system
principles and mechanisms for deadlock avoidance, while enabling designers to customize deadlock
avoidance mechanisms.

Memory access and message communication represent two core transactional actions in UB, each with
distinct deadlock causes and unique prevention strategies. This section details these two deadlock
avoidance methods and explains how they differ based on whether transactions involve memory
operations or message exchanges.


8.2.7.2 Deadlock Avoidance in Memory Access

UB provides memory and I/O access functions for various applications via a single physical port. These
functions can trigger secondary memory-related operations when accessing memory segments. If
procedural dependencies or circuit resource dependencies form between the primary operations and
the secondary operations during execution, system deadlocks may occur.

Note: Primary memory operations refer to memory operations directly initiated by a processor/accelerator through
instructions, such as bus read operations caused by load instructions. Secondary memory operations refer to necessary
operations triggered by primary memory operations to implement memory access, such as page fault handling and
UMMU processing for memory borrowing.




unifiedbus.com                                                                                                     264
8 Function Layer



The following are three typical deadlock scenarios for reference.

      ⚫   Memory pooling and borrowing
          UBPUs operate in peer-to-peer mode, and each UBPU assumes dual role of both memory
          borrower or memory lender to utilize each other's resources. An initiator's memory access to
          the target (pooled physical memory access in the figure below) is translated into local
          memory access on the target (local physical memory access in the figure below). When both
          UBPUs interact with each other, a deadlock dependency may be formed on the circuits
          implemented by UB.
          Example: Node A borrows memory from node B, and node B borrows memory from node A. If nodes A and B
          simultaneously update the peer's memory via a Writeback transaction, each node waits for the
          corresponding TAACK returned to complete the transaction. If the TAACK is blocked by a reverse Writeback
          transaction, the TAACK may fail to be returned, leading to initiator resource exhaustion and a deadlock.

      ⚫   Page table access
          When the UMMU performs address translation during memory access, a deadlock may
          occur if the UMMU page table entries reside in borrowed memory, as the operation to read
          the page table needs to go through the same port used for the memory access. Similarly, a
          deadlock may arise if the UMMU page table entries reside in local memory, as the page table
          read operation could trigger secondary access through the same port used for the original
          memory access.
          Example: Node A borrows memory from node B. When node A initiates a memory operation to node B, node
          B's UMMU page table is located in its local memory. If node B's page table read operation triggers a memory
          writeback access to node A while node A is waiting for node B to complete the original memory access, both
          nodes will be unable to complete their operations, resulting in a deadlock.
      ⚫   Page fault handling
          UB memory access supports dynamic memory management. If this function is enabled in the
          system, a page fault may occur along the memory access path. A UBPU needs to complete
          page fault handling to continue memory access. Page fault handling may raise secondary
          access to external storage (memory hierarchy swap in the figure below) or other UBPU's
          memory (pooled physical memory access in the figure). These secondary operations and the
          original access operation go through shared circuits, which may cause a system deadlock.
          Example: Node A accesses node B's memory. If a page fault occurs on node B during this access, node A's
          memory operation remains blocked until node B resolves the page fault. When node B migrates the page to
          deal with the page fault, the page fault traffic may be blocked by the memory access traffic of node A,
          causing a deadlock.

UB provides mechanisms such as request retry, virtual channel isolation, and various transaction types
for implementers to solve such problems. UB implementers can also address deadlock scenarios by
ensuring page table localization and eliminating dependencies on the unconditional completion of any
UB transaction.




unifiedbus.com                                                                                                       265
8 Function Layer




                            Figure 8-10 Deadlock avoidance for memory operations


8.2.7.3 Deadlock Avoidance in Message Communication

Message communication utilizes queues. When queue resources are exhausted, message passing
halts. If queues on different UBPUs are connected such that the output of one queue feeds into the
input of another queue (head-to-tail), circular dependencies can form (see Figure 8-11), potentially
causing a deadlock.

Example: Node A and node B initiate Send transactions to each other. Because other nodes might also initiate requests
to nodes A and B, RQ resources may become insufficient (many-to-many Jetty communication model). In this situation,
nodes A and B will generate TAACKs with an RNR status. If both TAACKs are simultaneously blocked (e.g., the TAACK
from node A to B is blocked by a Send transaction from node B to A, and the TAACK from node B to A is blocked by
another Send transaction from node A to B), the exception TAACKs cannot be processed, resulting in a deadlock.

UB implementers can eliminate deadlock conditions from the system level through methods such as
reserving resources and allocating exclusive resources for message processing. In addition, UB
provides three basic mechanisms to help avoid message communication deadlocks. UB implementers
can select one or many of them as required.

      ⚫     Separating the transport layer and transaction layer
            During message transaction processing, insufficient resources in the transaction layer will not
            block the execution of the transport layer and lower layers. This prevents widespread
            backpressure because of localized resource shortages in the transaction layer.




unifiedbus.com                                                                                                     266
8 Function Layer



      ⚫    Initiator-side retry when receiving abnormal status
           The transaction layer returns different response statuses, enabling the initiator to retry or
           apply alternative policies, thereby avoiding deadlocks on circuits. When the UB transaction
           layer has insufficient resources and cannot return a TAACK, it can convey the abnormal
           transaction response via a transport-layer response packet.
      ⚫    Setting a timeout mechanism to release resources upon message communication failures
           The timeout mechanism detects message communication failures and notifies the
           application, which then performs further processing. The UB circuit remains unblocked.




                         Figure 8-11 Deadlock avoidance for message operations


8.3 Load/Store Synchronous Access
Load/store synchronous access in this specification refers to various operations directly issued by
processor instruction sets. Both the instruction set operations themselves and the secondary
transactions they generate are transmitted to the UB Controller via the NoC. The UB Controller then
translates them into various transaction-layer operations. UB does not restrict the instruction set
architecture; interoperability between different instruction sets' load/store behavior is achieved through
mapped basic operations of the UB transaction layer.

UB supports cross-layer coordination to achieve the optimal system performance. Therefore, for
different end-to-end deployment environment characteristics, the UB Controller can employ an
appropriate combination of transaction-layer and lower-layer features to complete tasks. For instance,
in scenarios with high network quality, such as within servers, racks, or small clusters, the transaction
operations of the load/store instructions use the TP bypass mode. This relies on data link layer
retransmission to ensure reliable transaction transmission, consuming no transport-layer resources,
thus reducing latency and optimizing bandwidth utilization. The UB Controller also supports extending
load/store instructions to the data center scope. In this case, the transport layer's TP channel provides
an independent, reliable end-to-end pipe for load/store synchronous access transactions.




unifiedbus.com                                                                                             267
8 Function Layer



UB allows instruction sets to utilize UB transactions as native components, such as many-to-many
message sending, message reception, event notification, ordered information passing, and global
synchronization, enabling efficient coordination across UBPUs.

In addition, when the transaction layer is invoked by using the load/store synchronous access model,
the ROI and ROL transaction service modes can be used (see Section 7.3.3).


8.4 URMA Asynchronous Access
Developers can use the URMA asynchronous access programming model to initiate transaction
operations towards the target via Jetty abstraction.

The URMA programming model may utilize the queue-based interface to receive and process
transaction requests submitted by Jetties. For details, see Section 8.2.3. Message queues are one of
the implementations of URMA asynchronous access. Other efficient interaction implementations can
also be used.

The following is the basic procedure for a developer to use Jetties to implement transaction functions:

      1.   Acquire the EID and create a URMA context.
      2.   Based on the URMA context, create Jetties, JFCs, and JFCEs, and establish a
           communication relationship. This includes importing target Jetties and memory segments,
           binding transaction queues, and specifying a transaction service mode.
      3.   Submit a transaction request to the SQ through Jetty APIs, and asynchronously wait for a
           transaction response.
      4.   The UB Controller schedules the transaction request and converts it into one or multiple
           transaction operations. The transaction request shall contain transaction semantic
           parameters, target information (memory segment or target RQ), order requirements,
           completion notification requirements, etc.
      5.   The transaction layer completes transaction operations based on the transaction type and
           requirements.
      6.   Upon completion of the transaction operations, the completion information is reported to the
           CQ. If an exception occurs during or after transaction processing, an event notification shall
           be generated and reported to the EQ.
      7.   The developer retrieves completion status either by polling the JFC (bound to a CQ) or by
           waiting for an interrupt via the JFCE. If an exception occurs, the developer performs
           exception handling as required.

The UB Controller calls transaction-layer operations based on the transaction request as follows:

      ⚫    For a memory transaction, the UB Controller sequentially schedules SQEs and converts
           them into memory operations (see Section 7.4.2). The transaction request needs to specify
           the transaction operation type (Read, Write, etc.), memory address to be accessed, length,
           and transaction execution order (TEO) requirements.




unifiedbus.com                                                                                         268
8 Function Layer



      ⚫    For a message transaction, the UB Controller sequentially schedules SQEs and issues
           message operations (see Section 7.4.3). The transaction request needs to specify the
           transaction type (Send or other), target RQ for processing the message transaction, and
           TEO or transaction completion order (TCO) requirements.
      ⚫    For a maintenance transaction, the transaction operation needs to specify memory
           information if the state can be updated via direct memory modification; otherwise, target RQ
           information needs to be specified if the state requires target processing.

If the URMA asynchronous access model is used, transaction service modes such as ROI, ROT, ROL,
and UNO may be utilized. However, not every request supports all four service modes. For details, see
Section 7.4.


8.5 URPC

8.5.1 Overview
The URPC protocol enables direct peer-to-peer function calls between any UBPUs, leveraging
capabilities provided by the UB transaction layer.

The functional roles and protocol workflow are detailed below.




                                    Figure 8-12 URPC functional roles

URPC defines three distinct functional roles with specific responsibilities:

      ⚫    Client: The initiator and caller of URPC, responsible for initiating specified remote function
           calls to the server.
      ⚫    Server: The receiver and dispatcher of URPC, responsible for receiving remote function calls
           from the client and assigning them to a worker for execution.
      ⚫    Worker: The executor of URPC. The worker triggers function execution and returns the result
           to the server which then forwards them to the client.




unifiedbus.com                                                                                              269
8 Function Layer



For clarity, the following related terms are further defined:

      ⚫    Caller: The application that initiates a remote procedure call based on the URPC protocol.
      ⚫    Callee: The implementer of the URPC function. This role MAY be combined with the worker
           role, depending on system requirements.

URPC messages facilitate information exchange between the client and server. They are categorized
by their role in the protocol workflow as follows:

      ⚫    URPC request: Sent from the client to the server to initiate a function call.
      ⚫    URPC acknowledgment: Returned from the server to the client, indicating argument transfer
           completion and triggering the client to release the argument memory space.
      ⚫    URPC response: Returned from the server to the client, indicating function execution
           completion with a returned result.

Each URPC request carries a unique ID used to specify a particular function within the server or worker
runtime context. Detailed format definitions for URPC messages and function fields are provided in
Appendix H.

Based on the aforementioned URPC functional roles and messages, the URPC protocol operates as
follows:

      ⚫    The caller invokes the client to initiate a remote function call.
      ⚫    The client sends a URPC request to the server, carrying a unique function ID and argument
           information.
      ⚫    Upon receiving the identifier and arguments, the server replies with a URPC
           acknowledgment to notify the client that the argument transfer is complete.
      ⚫    The server assigns the function to the worker for execution.
      ⚫    The worker invokes the callee to execute the corresponding function using the function ID.
           Upon function execution completion, the worker returns the result to the server, which sends
           it to the client via a URPC response.
      ⚫    The client receives the URPC response and delivers the remote function call result to the caller.

The following notes further supplement the URPC message handling process:

      ⚫    The client indicates whether a URPC acknowledgment is required.
      ⚫    The server MAY merge the URPC acknowledgment and response into a single message. If
           they are merged, the server returns the result to the client via a combined URPC
           acknowledgment and response message after function execution completes. This combined
           message notifies the client of argument transfer completion and returns the execution result.

The URPC protocol supports the following innovative features:

      ⚫    Peer-to-peer function calling: A function call can be initiated directly between any UBPUs.
      ⚫    Pass-by-reference: The worker initiates data transfer based on the argument reference,
           which is the address of the argument data.




unifiedbus.com                                                                                            270
8 Function Layer



8.5.2 Peer-to-Peer Function Calling




                          Figure 8-13 URPC protocol's peer-to-peer architecture

The client, server, and worker within the URPC protocol can be implemented as UBPU Entities based
on scenario requirements. By leveraging the peer-to-peer UB architecture, any client implemented on a
UBPU can initiate a remote function call by sending a URPC message directly to the server or worker
deployed on other UBPUs.

A typical application involves one UBPU (for example, an NPU) directly initiating a remote function call
to write data into the storage of another UBPU (for example, an SSU). This peer-to-peer model enables
direct transfer of AI training or inference data from the NPU to the SSU for storage execution.


8.5.3 Argument Transfer
The URPC protocol supports the following argument transfer methods.




                              Figure 8-14 URPC argument transfer methods

      ⚫   Pass-by-value (inline): The client merges the argument data and the URPC protocol header
          into a single URPC request, and sends it to the server.
      ⚫   Pass-by-value (external): The client merges the argument data address and the URPC
          protocol header into a single URPC request, and sends it to the server. Upon receiving this




unifiedbus.com                                                                                        271
8 Function Layer



           address, the server uses read or load operations to fetch the complete argument data from
           the client.
      ⚫    Pass-by-reference: The client merges the argument data address and the URPC protocol
           header into a single URPC request, and sends it to the server. The server forwards this
           address to the worker which uses read or load operations to fetch the complete argument
           data from the client.

Compared to both inline and external pass-by-value methods, pass-by-reference delegates the timing
control of argument transfer to the worker. This provides greater flexibility in coordinating argument
transfer with function execution.

Detailed features and application scenarios for all URPC argument transfer methods are provided below:

                                    Table 8-2 URPC argument transfer methods
 Argument
                         Features                                                 Application Scenario
 Transfer Method
 Pass-by-value           ● Argument data size is constrained by the               Small argument data
 (inline)                  maximum size limit of the URPC request.                size and sufficient
                                                                                  memory resources.
                         ● The argument data is encapsulated within the
                           URPC request; argument transfer requires only          Example: storage
                           half a round trip.                                     scenarios with data size
                                                                                  less than 40 KB
                         ● Argument data is transferred from the client to the
                           server, and then passed to the worker.
 Pass-by-value           ● Argument data size is not constrained by the           Large argument data
 (external)                maximum size limit of the URPC request.                size and insufficient
                                                                                  memory resources.
                         ● The server initiates argument transfer after
                           receiving the URPC request; argument transfer          Example: storage
                           requires 1.5 round trips.                              scenarios with data size
                                                                                  greater than 40 KB
                         ● Argument data is transferred from the client to the
                           server, and then passed to the worker.
                         ● The client releases the arguments' memory
                           resources once the worker begins function
                           execution after the server pulls the argument data.
 Pass-by-                ● Argument data size is not constrained by the           Situations where
 reference                 maximum size limit of the URPC request.                argument transfer and
                                                                                  function execution times
                         ● The worker initiates argument transfer after
                                                                                  are close.
                           function execution begins; argument transfer
                           requires 1.5 round trips.                              Example: AI training or
                                                                                  inference scenarios
                         ● Argument data is transferred directly from the         where data transfer
                           client to the worker. The timing of this transfer is   overlaps with NPU
                           subject to the worker's control.                       computation.
                         ● The client only releases the arguments' memory
                           resources after the worker executes the function
                           to fetch the argument data.




unifiedbus.com                                                                                            272
8 Function Layer



8.6 Multi-Entity Coordination
The UB unifies multiple UBPUs across key aspects, including transaction types, access control, transfer
modes, and resource access. This significantly enhances the efficiency of multi-UBPU coordination for
completing complex tasks.

Implementers of UB chips and software are empowered to flexibly define multi-Entity coordination by
integrating the underlying transaction layer mechanisms, ensuring operations are precisely tailored to
specific scenario requirements.

A coordination operation is initiated via a single function call. The UB framework then decomposes this
call and maps it to multiple underlying UB transactions which are ultimately executed across one or
more UBPUs.

Typical coordination operations include the following examples:

      ⚫    Fusion operation
           A fusion operation consolidates multiple discrete transactions into a unified operation. This
           approach allows a single operation to handle a higher volume of operands or implement
           more complex operation logic, effectively mitigating software synchronization overhead and
           single-threaded performance bottlenecks. Typical fusion operations include broadcast,
           multicast, task balancing, task scheduling, and compound data and synchronization
           operations across UBPUs.
      ⚫    Collective communication operation
           Collective communication is a classic paradigm in parallel computing. Collective
           communication operations are exposed as single function calls, which the UB decomposes
           into a set of coordinated, hardware-topology-tailored UB transactions. In a multi-UBPU
           parallel environment, the decomposed transactions are dynamically mapped to and executed
           in a coordinated manner on their respective UBPUs, thus minimizing data movement and
           significantly enhancing system synchronization efficiency.
      ⚫    Global maintenance operation
           A single function call enables system-level maintenance across multiple UBPUs, such as
           memory consistency maintenance, synchronized UMMU updates, and communication state
           management.

The UB function layer defines a framework for modular coordination operations, enabling the integration
of new scenario-specific designs into the UB architecture to enhance overall UB system performance.


8.7 Entity Management
A UBPU acts as a consumer of Entity resources. In addition to invoking the functions or services
provided by an Entity, the UBPU SHALL also implement associated Entity management capabilities.
This management scope includes local Entity discovery, pooled Entity registration, configuration
management, interrupt and message notification, communication and remote memory registration
control, and virtualization. For details, refer to Chapter 10.




unifiedbus.com                                                                                         273
