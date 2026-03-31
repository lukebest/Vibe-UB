11 Security




11 Security


11.1 Overview

11.1.1 Security Model

11.1.1.1 Asset Protection Objectives

The UB protocol stack protects data assets accessed through it, including but not limited to the following:

      ⚫       Device identities, firmware, and accompanying software of UB processing units (UBPUs)
      ⚫       Memory-resident data
      ⚫       Data transmitted within UB
      ⚫       Sensitive data such as keys, access credentials, and parameters involved in each security
              function


11.1.1.2 Security Assumptions

UBPUs operate in a secure equipment room and are protected from physical attacks, including but not
limited to hardware insertion/removal and fault injection.

The UB Fabric Manager (UBFM) is trusted. Personnel responsible for device installation, deployment,
operation, and maintenance are authenticated and authorized. Administrative operations are performed
reliably, without malicious intent or privilege abuse resulting in incorrect configuration.

Attacks that degrade protocol availability or interrupt normal operations, such as denial-of-service (DoS)
attacks, resource exhaustion attacks, and UB Switch hijacking, are out of scope for this specification.

This specification covers the security of UB device interconnections. It does not cover security
mechanisms such as secure boot, hardware root of trust (RoT), and access control of the UBFM,
UBPUs, or UB Switches. Additionally, it excludes hardware and software designs or implementation
defects related to the UB protocol and devices.


11.1.1.3 TCB

The trusted computing base (TCB) components that require initial trust of users in the UB Domain
include the hardware-based RoT of UBPUs, the hardware security module (HSM), compute units in
trusted execution environments (TEEs), and the random numbers, root keys, and root certificates
preloaded on the compute units. If necessary, users can extend the TCB through mechanisms such as
measured boot during UB Domain operation.




unifiedbus.com                                                                                          362
11 Security



11.1.2 Security Threats
UB can protect against the following threats:

      ⚫       UBPU identity spoofing and firmware tampering or replacement: Attackers may use an
              untrusted UBPU to physically impersonate or replace a trusted UBPU, or tamper with the
              firmware of a trusted UBPU. Consequently, attacks can be propagated to other UBPUs over
              interconnection links.
      ⚫       Unauthorized access to memory or Jetty data: Attackers could access memory or Jetty
              data without authorization.
      ⚫       Packet eavesdropping, tampering, injection, replay, and forgery: Attackers may intercept
              communication links or compromise switches, routers, or links during inter-Entity
              communication across trusted domains. They may also exploit side channels to eavesdrop
              on, tamper with, inject, or replay packets transmitted between UBPUs. Additionally, attackers
              may impersonate source identities to forge communication data.
      ⚫       Unauthorized access to a TEE and inter-TEE communication data: Processes running
              outside TEEs may gain unauthorized access to sensitive data within a TEE or to
              communication data transmitted between TEEs.


11.1.3 Security Functions
UB provides the following security functions:

      ⚫       Device authentication: trusted measurement and security authentication for UBPUs
      ⚫       Resource partitioning: network partition identifiers (NPIs) at the network layer and UB
              partition identifiers (UPIs) at the transaction layer
      ⚫       Access control: authorized access for the memory and Jetties interconnected over UB
      ⚫       Data transmission security: encryption, decryption, and integrity verification of UB data
              flows to protect the confidentiality and integrity of packets
      ⚫       TEE extension: cross-device TEE extension for enhanced security

Table 11-1 describes the mapping of security functions to threats. Users can deploy security functions
based on their application scenarios and risk tolerance.

                                  Table 11-1 Mapping of security functions to threats
 Security Function                     Security Threat
 Device authentication                 UBPU replacement or tampering
 Resource partitioning                 Unauthenticated memory or Jetty data access
 Access control                        Unauthenticated memory or Jetty data access
 Data path protection                  Packet eavesdropping, tampering, injection, replay, or forgery
 TEE extension                         Unauthorized access to the TEE of a UBPU or to inter-TEE
                                       communication data across UBPUs




unifiedbus.com                                                                                            363
11 Security



11.2 Device Authentication

11.2.1 Application Scenarios
UB provides authentication for device access and interconnection. The authenticated content may
include hardware and software integrity measurement values as well as UBPU identities.

Device authentication is applicable to, but not limited to, the following scenarios:

      ⚫       A remote system administrator can authenticate UBPUs using the baseboard management
              controller (BMC) or the RoT of another platform without physical inspection.
      ⚫       During system operation or hot plugging, the UBFM or a system administrator needs to
              authenticate the UBPU and the corresponding firmware before allocating resources to the
              Entities of a UBPU.
      ⚫       Bidirectional identity authentication can be performed before Entities of different UBPUs
              communicate with each other.


11.2.2 Access Authentication
When a UBPU attempts to access the UB Domain, the UBFM SHALL verify its identity and trustworthiness.
Access is granted only if authentication is successful. UB supports three authentication approaches:

      ⚫       The UBFM authenticates the UBPU identity directly.
      ⚫       The UBFM authenticates device identity and trustworthiness based on the UBPU's measured
              boot capability, coordinating with a local or remote attestation server.
      ⚫       The administrator registers the device with the UBFM after verifying its identity and
              trustworthiness.

In the first approach, the UBFM sends an identity authentication challenge request to the UBPU, obtains
the digital certificate of the UBPU, and verifies the digital certificate to confirm the UBPU identity.

In the second approach, the UBFM may verify the UBPU, as well as the measurement values of its
firmware and accompanying software. During the authentication process, the UBFM initiates an
authentication request to obtain the UBPU integrity measurement report, UBPU identity certificate
chain, and measurement report signature. The UBFM verifies the measurement values in the
measurement report through the local or remote attestation mechanism and issues a credential signed
by the UBFM to those UBPUs that pass the authentication. When a UBPU exits the UB Domain, the
UBFM deregisters its credential.

Considering there may be a large number of UBPUs with the same firmware and software in the UB
Domain, the UBFM may simplify the authentication process, as illustrated in Figure 11-1.

      1.      When a UBPU starts, it generates the measurement values of its firmware and
              accompanying software. See step 1 in Figure 11-1.




unifiedbus.com                                                                                            364
11 Security



       2.     The UBFM sends an identity authentication challenge request to the UBPU. It then obtains
              the measurement report digest of the UBPU and the digital signature of the UBPU for the
              digest and challenge random number. See steps 2 and 3 in Figure 11-1.
       3.     After verifying the digital signature of the UBPU measurement report digest, the UBFM checks
              whether the measurement value corresponding to the digest is the same as the verified
              measurement value of the UBPU. If they are different, the UBFM obtains and submits the
              complete measurement report of the UBPU to the attestation server for comparison and
              verification. If the verification is successful, the UBFM issues the authentication credential
              signed by it to the UBPU. See steps 4.1, 5, 6, 7, 8, and 9.1 in Figure 11-1.
       4.     If the UBFM determines that the measurement report digest sent by the UBPU matches the
              previously verified measurement report, it may skip the process of obtaining and submitting
              the measurement report to the attestation server. Instead, it directly issues an authentication
              credential signed by it to the UBPU. See steps 4.2 and 9.2 in Figure 11-1.
       5.     Each UBFM instance may also generate a measurement report for the cluster managed by
              it. This cluster report consists of, but is not limited to, a list of UBPUs in the cluster and a
              measurement report corresponding to each unique UBPU. This enables users or
              administrators to verify the UBPUs in the cluster more quickly.

Note: For details about steps 2, 6, 7, and 8 in Figure 11-1, you can also refer to the DSP0274 Security Protocol and Data
Model (SPDM) Specification.




                                     Figure 11-1 Device access authentication

Some UBPUs may not support measured boot. In this case, UB allows the administrator to register the
device information with the UBFM after verifying the UBPU identity and the integrity of the
corresponding firmware, so that the UBPU can join the UB Domain. The UBFM issues a device
authentication credential digitally signed by it to the UBPU. When a UBPU exits the UB Domain or its
authentication credential becomes invalid, the UBFM deregisters the credential.



unifiedbus.com                                                                                                       365
11 Security



11.2.3 Interconnection Authentication
Bidirectional identity authentication is RECOMMENDED for communication between UBPUs. Inter-
device interconnection authentication can be performed based on device identities, such as digital
certificates. Optionally, authentication may also include verification of devices' integrity measurement
reports. In addition, devices' identity and trustworthiness can be verified using authentication credentials
digitally signed by the UBFM for UBPUs.


11.3 Resource Partitioning

11.3.1 Entity Partitioning
UB SHALL use UB partitions to isolate Entity partitions. Each UPI SHALL uniquely identify a group of
Entities within the UB Domain. They enable resource isolation at the Entity level to support secure
isolation of different service functions. For details about the UPI definition, see Section 10.3.2. For
details about the packet format for UPIs, see Appendix B.3

The UBFM SHALL manage UPIs and SHALL NOT allow any other component to modify them. It also
manages the security of the mappings between UPIs and the partitions to which the Entities belong,
ensuring that UPIs are correctly delivered to valid Entities. The TX side assembles the UPI fields of
packets based on the UPIs allocated by the UBFM. On the RX side, the hardware implementing the UB
protocol stack parses the UPIs in incoming packets and compares them with the UPIs configured by the
UBFM. If they match, the RX side processes the packets.

Note: UPI verification applies to data communication between Entities, but not to packets sent by the UBFM.



11.3.2 Network Partitioning
UB SHALL use NPIs to isolate network partitions. Each NPI is defined at the network layer and SHALL
be unique within the UB Domain. UB SHALL ensure that the NPI configuration is trusted to meet
various security requirements, including user isolation between physical devices, subnet isolation, and
switch isolation on the management plane. For details about the NPI definition and verification
mechanism, see Section 5.3.3.1.


11.4 Access Control

11.4.1 Application Scenarios
UB provides transaction-layer access control. Table 11-2 lists the application scenarios. UB controls
memory access based on the Memory Address Permission Table (MAPT) of the UB memory
management unit (UMMU) (see Section 9.4.4), which is independent of the Memory Address
Translation Table (MATT). It performs permission verification and address translation separately for
memory access, allowing access only if both operations succeed.




unifiedbus.com                                                                                                366
11 Security



                                     Table 11-2 Access control scenarios
 Application            Whether to Introduce                                                    Whether to
                                                       Access Credential ID
 Scenario               TokenValue                                                              Introduce UMMU
 Memory access          Optional                       TokenID                                  Yes
 Jetty access           Optional                       Target Jetty Context ID (TCID)           No


11.4.2 Working Principles
UB implements access control as follows, using memory access as an example:

       1.     When a User requests access to a specific memory segment at the Home, the Home SHALL
              authenticate the User and return a TokenID and a random number serving as the
              TokenValue.
       2.     The TokenID and TokenValue SHALL be included in the access request packets. The Home
              SHALL query the tables for the target memory address and TokenValue. If the verification
              succeeds, access is granted.

Note 1: The TokenValue random number can be obtained by reading the true or pseudo random number generator on
the UBPU. Based on the security threat analysis result of a specific service scenario, users can decide whether to use
cryptographic technologies to protect the confidentiality and integrity of the TokenValue.

Note 2: If a VM or application process restarts within a certain time window at the Home, expired packets may still reach
the destination resources and cause data errors. Appropriate measures SHALL be taken to prevent this situation. For
example, the Home can immediately update the TokenValue upon restart.

Note 3: The Home may issue the same TokenID and TokenValue to multiple Users accessing the same memory segment
with identical permissions. Users may share their TokenIDs, TokenValues, and memory segment information. For
example, once a User obtains access permission to a memory segment, the User may broadcast the TokenID and
segment information to others. Other Users who require access SHALL obtain the TokenValue from the original User,
optionally through encrypted transmission.

In the memory access scenario, the UMMU provides an E_bit alongside TokenValue-based access
control. Whether a User can access a memory segment at the Home is also restricted by E_bit
verification. For details about the E_bit verification rules, see Section 9.4.4.3.3.

At the UB Domain boundary, packets need to be filtered by IP address. For example, only packets
whose E_bit is 0 and that carry TokenValues are allowed to enter the UB Domain.


11.4.3 Permission Assignment
The key process for memory access control within UB is as follows:

       1.     A User requests access permission from the Home and the Home SHALL verify the User's
              identity. If the verification is successful, the Home SHALL register the User with the
              requested resources, obtain the TokenID, memory segment, segment permission, and
              (optional) TokenValue, and then securely transmit the obtained data to the User.




unifiedbus.com                                                                                                        367
11 Security



      2.      The User initiates memory access to the Home. The packet SHALL contain the TokenID,
              memory address, operation type information, and (optional) TokenValue. The Home SHALL
              use the UMMU to check whether a corresponding table entry exists for the TokenID, and
              compare the TokenValue field in the packet with the TokenValue stored in the page table
              entry. Based on the comparison result, the Home determines whether the User is permitted
              to access the target memory address.

The key process for Jetty access control within UB is as follows:

      1.      The initiator requests the TCID and TokenValue from the target. The target SHALL generate
              the requested data and securely transmit it to the initiator.
      2.      The initiator SHALL send a packet containing the TCID and TokenValue to the target. After
              receiving the packet, the target SHALL use the TCID to retrieve the TokenValue and
              compare this TokenValue with its stored TokenValue to verify the initiator's access
              permission.

Access control policies can be customized for specific service scenarios.

      ⚫       A TokenID or TCID is transmitted without a TokenValue. This policy provides the highest
              performance but carries a risk of unauthorized access.
      ⚫       A TokenID or TCID and its corresponding TokenValue are transmitted in plaintext. This policy
              is relatively secure, but intermediate network nodes may obtain the TokenValue without
              authorization.
      ⚫       A TokenID or TCID and its corresponding TokenValue are transmitted in encrypted form,
              while the payload remains in plaintext. This policy prevents intermediate network nodes from
              obtaining the TokenValue, but they can still view the payload content.
      ⚫       A TokenID or TCID and its corresponding TokenValue are transmitted in encrypted form, and
              the payload is also encrypted. This policy provides the highest level of security but incurs
              significant hardware overhead.


11.4.4 Permission Invalidation
UB offers two methods for invalidating access permissions:

      ⚫       Group-grained invalidation
              Group-grained invalidation is initiated by the Home. The hardware and software components
              associated with the UMMU at the Home invalidate the TokenID and its corresponding
              TokenValue. Consequently, all Users in the permission group associated with the TokenID
              and TokenValue lose their access permissions.
      ⚫       User-grained invalidation
              User-grained invalidation is initiated by Users. It invalidates the access permissions of
              certain Users within a permission group and minimizes the impact on other Users whose
              permissions remain valid.




unifiedbus.com                                                                                               368
11 Security



            (1) Multiple Users obtain the Home memory access credential either by requesting it from
                   the Home or by receiving it from one another. The credential includes the TokenID and
                   TokenValue.
              (2) The Home updates the TokenValue and distributes the updated TokenValue to the
                   Users whose permissions remain valid, but not to those whose permissions have
                   become invalid.
              (3) The Home accepts only memory access requests with the updated TokenValue, denying
                   access to Users who do not have it.

Note: The permission invalidation process for Jetty access is similar to the one described above.

Figure 11-2 shows an example of invalidating User1's permission within the permission group.

       1.     At time point 1: User1, User2, and User3 successfully obtain TokenID1 and the active TokenValue (A-
              TokenValue) of the Home. Then User1, User2, and User3 use TokenID1 and A-TokenValue to access the
              destination memory at the Home. In addition to A-TokenValue, the Home maintains a backup TokenValue
              (B-TokenValue).

       2.     At time point 2: The Home sends B-TokenValue to User2 and User3. User2 and User3 then use B-
              TokenValue as their access credential. Since the Home does not send B-TokenValue to User1, the
              permission page table of the Home can verify both A-TokenValue and B-TokenValue in the transition phase,
              whose duration is determined by the Home. Memory access is allowed if the verification is successful. In a
              high-security service scenario, the Home may directly update the active access credential from A-
              TokenValue to B-TokenValue, send B-TokenValue only to User2 and User3, and update the backup access
              credential to C-TokenValue. Consequently, User1 immediately loses permission to access the Home.

       3.     At time point 3: After the transitional phase, the Home replaces A-TokenValue with B-TokenValue and
              generates C-TokenValue as the new backup. Subsequently, any access permission verification based on A-
              TokenValue fails, finalizing the invalidation of User1's permission.




unifiedbus.com                                                                                                        369
11 Security




                                        Figure 11-2 User-grained invalidation


11.5 Data Transmission Security

11.5.1 Application Scenarios
In scenarios where the data path is not trusted, to protect against security threats such as
eavesdropping, tampering, and malicious injection, a cryptography-based Confidentiality and Integrity
Protection (CIP) mechanism SHALL be enabled for packets transmitted over UB.

Note: An untrusted data path means that sensitive data transmitted along the end-to-end data path (covering physical
lines and intermediate switching and forwarding devices) on the data plane is vulnerable to local physical eavesdropping.
It also includes scenarios where malicious packet forwarding by switches or tampering with routing tables causes
packets to be redirected to unauthorized third parties.

The CIP mechanism ensures the security of packets transmitted along data paths at the transaction
layer, ensuring confidentiality and integrity and providing basic anti-replay protection.

The CIP mechanism protects only the data transmission between source and destination Entities. Other
types of data are secured using the built-in security mechanisms of UBPUs.




unifiedbus.com                                                                                                       370
11 Security



11.5.2 CIP Workflow

11.5.2.1 Channel Establishment

The major objective of the CIP mechanism is to protect transaction-layer packets on the data plane. To
achieve this, the mechanism requires establishing CIP channels on the control plane. CIP channel
establishment involves configuring keys for the source and destination Entities. For centralized CIP
channel establishment, the domain administrator can configure keys through either in-band or out-of-
band channels. For distributed CIP channel establishment, the Entities of the two communication
parties can negotiate a key directly. UB also supports user-defined methods to establish CIP channels.

Figure 11-3 shows centralized CIP channel establishment.




                               Figure 11-3 Centralized CIP channel establishment

       1.     The UBFM authenticates the identities of both the requester's and the responder's Entities.
              For details, see Section 11.2.2.
       2.     The UBFM performs handshake negotiation with both the requester's and the responder's
              Entities to determine the cipher suite.
       3.     The UBFM establishes secure sessions with both the requester's and the responder's
              Entities.
       4.     Based on the established secure sessions, the UBFM configures a CIP communication key
              for both the requester's and the responder's Entities, covering both transmission (TX) and
              reception (RX) directions.
       5.     The UBFM configures parameters for the Entities in both the RX (requester or responder)
              and TX (requester or responder) directions. Subsequently, the Entities may initiate CIP data
              communication.

Note: For details about steps 1 to 4, you can also refer to the DSP0274 SPDM Specification.




unifiedbus.com                                                                                             371
11 Security



Figure 11-4 shows distributed CIP channel establishment.




                                  Figure 11-4 Distributed CIP channel establishment

       1.     The requester's and responder's Entities authenticate each other to verify their identities. For
              details, see Section 11.2.3.
       2.     The requester's and responder's Entities perform a handshake to determine the cipher suite.
       3.     The requester's and responder's Entities establish a secure session.
       4.     The requester's and responder's Entities negotiate the CIP communication key based on the
              established secure session. After the negotiation is complete, the key is configured into the
              registers of both the requester's and responder's Entities in the TX and RX directions through
              the internal bus.
       5.     The Entities in both the RX (requester or responder) and TX directions configure necessary
              parameters through the internal bus to initiate CIP data communication.

Note: For details about steps 1 to 4, you can also refer to the DSP0274 SPDM Specification.


11.5.2.2 Parameter Value Rules

When the cryptographic algorithm AES-GCM or SM4-GCM is used, it SHALL comply with the NIST SP
800-38D or GM/T 0002-2012 standard. Both algorithms contain three key parameters with reference
configurations as follows:

       ⚫      Additional authenticated data (AAD): information that is authenticated but not encrypted,
              ensuring its integrity and origin authenticity. Recommended inputs include partial or full
              content of CIP packet headers, UPIs, or transaction-layer packet headers.
       ⚫      Plaintext data: sensitive information in transaction-layer packet headers and payload plaintext.
       ⚫      Initialization vector (IV): typically a 96-bit random number. It ensures that a different key
              stream is generated for each encryption, so that encrypting the same plaintext with the same
              key produces different ciphertexts.




unifiedbus.com                                                                                                372
11 Security



11.5.2.3 Extension Packet Headers

To support the CIP mechanism, the UB protocol stack SHALL append a CIP security extension header
to each packet. This extension header includes the following fields:

      ⚫       CIP ID: It is an index representing a CIP policy within a local Entity. The RX side indexes the
              CIP policy information based on a 128-bit or 20-bit DEID. The CIP ID serves as an additional
              index to retrieve the specific policy information indicated by the CIP packet. This policy
              information includes the encryption status, algorithm in use, fields involved in calculation and
              verification, key information, and IV information.

              Note: In a large cluster with numerous CIP communication flows, the RX side may further establish a multi-
              layer index based on the SEID alone or both the SEID and DEID to retrieve the CIP context, including the
              encryption status and algorithm in use. This design supports coexistence of more CIP communication flows.

      ⚫       SN: When CIP is enabled, the TX side generates an SN for each packet.
      ⚫       NLP: It is the next header in the packet, which is 4 bits long.
              (1) CIPH.NLP==4'b0000: This value indicates that the header includes a 32-bit UPI, a 128-
                   bit SEID, a 128-bit DEID, and a TAH.
              (2) CIPH.NLP==4'b0001: This value indicates that the header includes a 16-bit UPI, a 20-bit
                   SEID, a 20-bit DEID, and a TAH.
              (3) CIPH.NLP==4'b0010: This value indicates that the header includes a TAH but not a UPI,
                   SEID, or DEID.
              (4) Others: RSVD.
      ⚫       RSVD: This is a reserved field.


11.5.2.4 Verification Method

When CIP is enabled, packets carry the integrity check value (ICV) field. The ICV is calculated using
the cryptographic algorithm preconfigured in the CIP control register. The message authentication code
(MAC) value of the fields from the CIP header to the payload in the packet is then calculated. If the
cryptographic algorithm AES-256-GCM or SM4-128-GCM is used, the ICV length is 96 bits. It is
RECOMMENDED to use the lower 96 bits of the MAC value as the ICV. UB supports a user-defined
cryptographic algorithm suite. If the cryptographic algorithm is not AES-256-GCM or SM4-128-GCM,
the ICV bit length is determined by the chosen algorithm and is generally an integer multiple of 32 bits.

Transaction-layer packets are released and subsequent operations are performed only upon successful
ICV verification. The RX side SHALL NOT release transaction-layer packets until it has received all
packets for which the ICV is calculated and successfully verified. Therefore, the RX side SHALL cache
at least the current transaction-layer messages to prevent data loss. If the verification fails, the system
should immediately abort operations requested by the packets to preserve security integrity.

Verification on the RX side proceeds as follows:

      ⚫       The UPI in the CIP packet is compared with the local UPI. If they do not match, further
              calculations are aborted.




unifiedbus.com                                                                                                       373
11 Security



      ⚫       The CIP register of the Entity is indexed. If CIP is disabled for the Entity, CIP verification is
              not performed. Otherwise, the policy information is obtained based on the control register
              indexed using the CIP ID. This policy information includes the encryption status, algorithm in
              use, IV information, key information, CIP verification method, and CIP protection scope.
      ⚫       MAC calculation and verification are performed based on the policy information. Once
              verification succeeds, the ciphertext field in the CIP packet is decrypted, and subsequent
              operations proceed.


11.5.2.5 Error Handling

The RX side pre-processes received CIP packets, which may involve the following cases:

      ⚫       If the ICV is verified, transaction-layer packets are released and the associated operation
              is executed.
      ⚫       If the ICV field is received when CIP is disabled, transaction-layer packets are discarded.
      ⚫       If the ICV field is not received as expected, transaction-layer packets are discarded.
      ⚫       If other errors occur, transaction-layer packets are discarded.


11.5.2.6 Key Update

A CIP communication key has a limited lifecycle. The key update interval can be determined by the
actual encrypted packet throughput of the CIP channel. The key can be configured using the UBFM or
updated according to the negotiated key update policy to ensure its security.


11.6 TEE Extension

11.6.1 Application Scenarios
A TEE is a secure environment established through hardware resource isolation. Its memory space and
registers are inaccessible to OS, hypervisor, and other processes outside the TEE. Trusted attestation
and cryptographic technologies safeguard the confidentiality and integrity of the code and data loaded
in the TEE.

As compute-intensive applications such as foundation model training and inference continue evolving,
TEEs are scaling from single-processor to multi-processor setups, and even to interconnected compute
clusters. This section describes how UB enables secure and efficient data flow between TEEs on
different UBPUs, thereby extending TEEs. It covers fundamental concepts and models, core functions,
and interaction workflows.




unifiedbus.com                                                                                                374
11 Security



11.6.2 Interconnection Models

11.6.2.1 Components

Figure 11-5 shows a model of TEE extension across UBPUs within a UB Domain. In this model, UBPUs
are classified into Users and Homes based on their roles in resource access. Users send access
requests while Homes respond to them.




                                       Figure 11-5 TEE extension model

This interconnection model consists of the following components:

      ⚫       Trusted Entity Instance in User (UTEI): A UTEI SHALL be protected by the User-side TEE.
              It MAY be the entire TEE or a trusted virtual machine (VM) or a process that uses the Entity
              in the TEE. A UTEI initiates a TEE extension request by sending a TEE extension packet to
              an HTEI of a remote Home. This enables cross-UBPU resource access, but the UTEI SHALL
              access only the target HTEI—unless a trusted connection is also established with others.
      ⚫       Trusted Entity Instance in Home (HTEI): An HTEI SHALL be protected by the Home-side
              TEE. It MAY be the entire TEE or a trusted VM or a process that uses the Entity in the TEE.
              An HTEI receives and responds to a TEE extension packet sent by the local UTEI, and
              establishes a trusted connection with a UTEI of the remote User. This enables cross-UBPU
              resource access, but the HTEI SHALL access only the target UTEI—unless a trusted
              connection is also established with others.
      ⚫       Trusted execution environment Manager in User (UTM): The UTM constitutes the User-
              side TCB for TEE extension. It manages the trustworthiness of UTEIs and enforces security
              policies such as key and certificate management, trusted measurement, and UTEI isolation.




unifiedbus.com                                                                                           375
11 Security



              It also offers security service interfaces to the UBFM, including interfaces for retrieving UTEI
              measurement reports and granting or revoking access to computing resources.
      ⚫       Trusted execution environment Manager in Home (HTM): The HTM SHALL serve as the
              TCB necessary for implementing Home-side TEE extension. It SHALL manage the
              trustworthiness of HTEIs and enforce security policies such as key and certificate
              management, trusted measurement, and HTEI isolation. It SHALL also offer trusted
              interfaces to the UBFM, including interfaces for managing the HTEI security status, retrieving
              HTEI measurement reports, and granting or revoking access to computing resources.
      ⚫       TEE extension component: This component SHALL run within the UB Controller and UMMU
              to support TEE and EE_bits extensions. The component enables secure communication
              between UTEIs and HTEIs. It SHALL enforce security controls on packets transmitted and
              received by UBPUs based on the security policies provided by the UBFM. These security
              enforcements SHALL NOT be disabled or bypassed by the UTM or HTM on UBPUs.
      ⚫       UBFM: The UBFM SHALL manage device interconnections and resources in the UB
              Domain, and configure the security status of all Entities within the UB Domain.
      ⚫       OS: The generic OS on UBPUs allocates system resources to the Entity instances outside
              the TEE, and loads and schedules those system resources.
      ⚫       Normal Entity Instance (EI): A normal EI runs outside the TEE of a UBPU.

Among the preceding components, the UTM or HTM configures the security status of Entities to enable
their access to UTEIs or HTEIs, and also configures the UMMU to translate TEE UB address spaces.
Secure interconnections can be established between UTEIs and HTEIs within the same UPI. Different
UPIs are RECOMMENDED for different services.


11.6.2.2 Security Model

TEE extension depends on the following prerequisites:

      ⚫       UBPUs are equipped with a hardware-based RoT and support measured boot.
      ⚫       A local or remote attestation server is deployed to store the baseline integrity measurement
              values for the firmware and OS of each UBPU.

TEE extension depends on the following security assumptions:

      ⚫       The hardware-based RoT and measured boot of UBPUs and UPIs are implemented correctly
              and protected against tampering.
      ⚫       The attestation server is trusted and the baseline attestation values stored on it for UBPUs
              are protected against tampering.
      ⚫       The UTM, HTM, UBFM, and TEE extension component are designed and implemented
              correctly and protected against unauthorized access or tampering.

TEE extension is designed to protect against the following security threats:

      ⚫       Identity spoofing, tampering, and replacement of UBPUs that host UTEIs or HTEIs
      ⚫       Tampering or replacement of UB Switches on UTEI and HTEI interconnection links




unifiedbus.com                                                                                             376
11 Security



      ⚫       Unauthorized access to UTEIs and HTEIs by components such as UBPU OSs and normal
              EIs running outside a TEE
      ⚫       Attempts to access data between UTEIs and/or HTEIs across different UPIs
      ⚫       Theft, replacement, or tampering of UTFEI and HTFEI communication data by attackers or
              O&M personnel

TEE extension is not designed to protect against the following security threats:

      ⚫       Attacks that compromise availability, such as malicious disabling of UTEIs or HTEIs and
              DoS attacks


11.6.2.3 Communication Modes

TEE extension can be implemented in basic or enhanced mode to address different security risks (see
Table 11-3). This choice depends on the device operating conditions and the acceptable level of
security risks.

      ⚫       Basic mode: This mode does not address physical link attacks and does not require
              enabling CIP. The UBFM, UTM, and HTM jointly configure policies for the TEE extension
              component on each UBPU. These policies enforce security controls over UB communication
              data flows and employ a trustworthiness verification mechanism to verify the trustworthiness
              of UTEIs and HTEIs.
      ⚫       Enhanced mode: This mode addresses more severe security threats, including physical link
              attacks and tampering or replacement of UBPUs or UB Switches. Compared to the basic
              mode, the enhanced mode uses CIP to ensure the confidentiality and integrity of UTEI and
              HTEI communication data, along with a trustworthiness verification mechanism to verify the
              trustworthiness of UTEIs and HTEIs.

                                        Table 11-3 Communication modes
                                                                                      Basic    Enhanced
 Security Threat                                             Defense Measure
                                                                                      Mode     Mode
 Tampering or replacement of UBPUs that host UTEIs           Trustworthiness          √        √
 or HTEIs                                                    verification
 Tampering or replacement of UB Switches on UTEI             Trustworthiness          √        √
 and HTEI interconnection links                              verification
 Unauthorized access to UTEIs and HTEIs by                   Security isolation       √        √
 components such as UBPU OSs and normal EIs                  using TEEs
 running outside a TEE
 Attempts to access data between UTEIs and/or HTEIs          Resource isolation       √        √
 across different UPIs                                       using UB partitions
 Theft, replacement, or tampering of UTEI and HTEI           Data path protection     ×        √
 communication data by attackers or O&M personnel            with CIP




unifiedbus.com                                                                                          377
11 Security



11.6.3 Communication Process

11.6.3.1 Basic Mode

Figure 11-6 illustrates the interaction process of the TEE extension mechanism in basic mode, which
includes the four key steps:

      1.      Create EIs.
              UTEIs and HTEIs are allocated and managed using a resource authorization mechanism.
              The UBFM sends a request for allocating TEE resources, such as CPUs and memory. The
              UTM and HTM verify the request, and if approved, generate a UTEI or HTEI.
      2.      Configure security status.
              The UBFM uses the UTM and HTM to configure security policies for the TEE extension
              component. These configurations include the UTEI or HTEI security status, the UPI
              associated with the UTEI or HTEI, and EE_bits.
      3.      Verify UBPU trustworthiness.
              Verifying the trustworthiness of a UBPU SHALL rely on the hardware-based RoT and trusted
              measurement capabilities of the UBPU. The goal is to confirm the integrity of the firmware, OS,
              and TEE on the UBPU. The verifier sends a measurement challenge request to the UBPU,
              optionally including a random number to prevent replay attacks. In response to the request, the
              UBPU measures the information to be verified in the UBPU, and signs the measurement value
              based on the private key. After receiving the signed measurement value, the verifier compares
              it with the baseline value stored on the attestation server. If the values are the same, the UBPU
              firmware and TEE are as expected and subsequent tasks can proceed.
              The objects to be verified for the Users and Homes include at least the UBPU firmware
              (covering the device driver and the UTM or HTM), OS kernel, file systems, and UTEI or HTEI
              security status configurations.
              If the UB Switch is located on the link between the User and Home, its firmware information
              SHALL be verified.
              The verifier uses the UTM or HTM to verify the UTEI or HTEI trustworthiness. UTEI–HTEI
              communication is permitted only after successful verification. The packets sent by the UTEI
              or HTEI SHALL carry EE_bits.
      4.      Perform TEE extension.
              The TEE extension component SHALL enforce access controls on the communication
              packets based on security policies. This process relies on hardware extensions such as the
              UMMU and UB Decoder for EE_bits.
              Access control with EE_bits SHALL follow the procedure used by the UMMU to manage
              memory access. For details, see Section 9.4.




unifiedbus.com                                                                                             378
11 Security




                                        Figure 11-6 TEE extension process


11.6.3.2 Enhanced Mode

The enhanced mode needs to address physical attacks. Secure communication between TEEs involves
the following steps:

      1.      Create EIs.
              This step is the same as that in basic mode. For details, see step 1 of Section 11.6.3.1.
      2.      Change security status.
              This step is the same as that in basic mode. For details, see step 2 of Section 11.6.3.1.
      3.      Verify device trustworthiness.
              This step is the same as that in basic mode. For details, see step 3 of Section 11.6.3.1.
      4.      Perform TEE extension.
              Beyond the basic mode (see step 4 of Section 11.6.3.1), the UBFM distributes and
              configures keys for UBPUs, enables the CIP mechanism, and protects the confidentiality and
              integrity of UTEI and HTEI communication data. For details, see Section 11.5.2.1.


11.6.4 Memory Address Isolation
The TEE extension component SHALL append an EE_bits field (see Section 7.2.1) to packets and uses
EE_bits to isolate UB address spaces. EE_bits supports a maximum of 2 bits, allowing the creation of
four address spaces: one non-TEE UB address space, one TEE UB address space, and two reserved
address spaces.

To isolate the address spaces of Entities at different security states, the UB address spaces are divided
into two parts: non-TEE UB and TEE UB address spaces. See Figure 11-7.




unifiedbus.com                                                                                            379
11 Security




                                   Figure 11-7 UB address space isolation

Note that the distinction between non-TEE and TEE UB address spaces lies in EE_bits. At any time, a
UB address SHALL reside exclusively in either the non-TEE or the TEE address space.

Isolating UB address spaces involves the following protocol extensions:

      ⚫       The memory access packets sent by a User include EE_bits to indicate the security status of
              the execution environment where the originating process is running.
      ⚫       Upon receiving the packets, the Home selects the appropriate UMMU page table based on
              the EE_bits. The UMMU provides support for addressing TEE UB address spaces.


11.6.5 Configuration Process
Figure 11-8 illustrates a reference for configuring TEE extension in cloud computing scenarios. TEE
extension MAY be configured in five steps using the UBFM:




unifiedbus.com                                                                                        380
11 Security




                                  Figure 11-8 Reference configuration process

      1.      Create resources required by the User or Home and configure the interconnection channel
              between the User and Home.
      2.      Create a UTEI and an HTEI. Configure the UMMU and UB Decoder register page tables for
              the User and Home as well as the UTEI and HTEI security status. If the enhanced mode is
              used, configure a communication key for the UTEI and an HTEI by following instructions in
              Section 11.5.2.1.
      3.      The User sends a measurement challenge request to the TEE.
      4.      After obtaining the measurement values, the User sends them to the attestation server.
      5.      After the measurement values are verified, the service flow starts.




unifiedbus.com                                                                                         381
11 Security



This reference configuration process SHALL be adapted to specific service requirements while
maintaining its security and completeness. For example:

In step 3, the User MAY retrieve the UTEI and HTEI measurement values from the UBFM, provided that
secure channels have been established between the UBFM and the User, and between the UBFM and
the Home, respectively.

In step 4, the UTEI and HTEI MAY send the measurement values directly to the attestation server. After
verifying the measurement values, the attestation server returns the verification result to the User.




unifiedbus.com                                                                                          382
