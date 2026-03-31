9 Memory Management




9 Memory Management


9.1 Overview
To facilitate memory sharing across the UB processing units (UBPUs) on the UB and ensure legitimate
memory access, memory resources within the UB system should be efficiently managed (in terms of
allocation, authorization, and reclamation) so as to enable secure, dynamic, and effective utilization. For
this goal, the memory management function is designed around the following key features:

      ⚫    The UB memory descriptors (UBMDs), which are globally unified and used to describe
           memory segments within the UB system. The User can use memory segments based on the
           UBMDs through synchronous or asynchronous access aforesaid in the function layer.
      ⚫    A Home-User access model that is defined based on who manages and uses memory. The
           Home owns physical memory resources, while the User accesses the Home's memory or
           data based on the UBMDs.
      ⚫    The UB memory management unit (UMMU) that controls the memory access in the UB
           system. To this end, the UMMU implements, on the Home side, address mapping and
           access permission check for memory resources. The component MAY securely delegate
           permission check to unprivileged software.
      ⚫    The UB decoder, which serves as the portal for the User-side UBPUs to access the UBMDs
           within the UB system. On the User side, the UB decoder translates local addresses on the
           UBPUs into UBMDs as needed and transmits them to the Home.


9.2 Home-User Access Model
The Home-User access model is depicted in Figure 9-1. The model works as follows:

      1.   The User sends memory access requests which SHALL contain the UBMDs to the Home.
           The UBMDs carried in the memory access requests over the UB link MAY come from two
           main ways:
           −   The UB decoder gets the UBMDs from tables based on physical addresses (PAs), as
               detailed in Section 8.3.
           −   The UBMDs are provided by users through User-side programming interfaces, as detailed
               in Section 8.4.
      2.   The Home receives and processes the memory access requests. Specifically, the UMMU
           translates the UBMDs into target memory PAs and performs permission check.




unifiedbus.com                                                                                         274
9 Memory Management




                                       Figure 9-1 Home-User access model

* Note: On the User side, memory access requests do not need to carry Entity identifiers (EIDs). On the Home side,
UMMU processing is also procedurally simplified.



9.3 UBMD
The UBMD indexes a Home-side PA and consists of three main components: an EID, a TokenID, and a
UB address (UBA). The EID identifies the Entity to which the target memory belongs. The TokenID
identifies the UBA space to which the target memory belongs and the permission set of that UBA space.
The third component, the UBA, is a 64-bit virtual address provided by the Home to the User for
accessing the Home-side memory.

The UBA space consists of a set of UBAs that are mapped to the Home-side PA space. The memory
address translation table (MATT) stores the actual mappings between UBAs and PAs, while the
memory address permission table (MAPT) holds the mappings between the UBA space and the
permission set. Both address translation and permission check use the UBAs as indexes to look up the
MATT and MAPT, respectively, to obtain the PAs and permission information. This process is illustrated
in Figure 9-2.




unifiedbus.com                                                                                                       275
9 Memory Management




                    Figure 9-2 MATT and MAPT lookups using the UBA as the index


9.4 UMMU Functions and Working Process

9.4.1 General Requirements
Upon a memory access, the UMMU takes the UBMDs carried in access requests as inputs to obtain the
memory PA and permission information. Figure 9-3 depicts a block diagram of the components and
steps the UMMU requires to process memory accesses.

     1.   Configuration lookup: The UMMU looks up the target Entity configuration table (TECT) based
          on the EID to obtain the base address of the target context table (TCT);
     2.   Context lookup: The UMMU looks up the TCT based on the TokenID to obtain the MATT and
          MAPT base addresses;
     3.   Address translation: The UMMU looks up the MATT based on the UBA to obtain the target
          memory PA;
     4.   Permission check: The UMMU looks up the MAPT based on the UBA to obtain permission
          information of the target memory to determine whether the memory access is valid.




unifiedbus.com                                                                                   276
9 Memory Management




                             Figure 9-3 Memory access processing flowchart


9.4.2 Configuration Lookup and Context Lookup

9.4.2.1 Configuration Lookup

The UMMU is configured in the granularity of Home Entity. The configuration information of the Home
Entity is stored in the TECT. The TECT entry (TECTE) states the following information:

      ⚫   Status (enabled or disabled) of follow-up processes: including permission check, two-stage
          address translation, and event merged reporting;
      ⚫   Memory access attributes: memory attributes and memory attribute selection mechanism;
      ⚫   Information of context lookup and address translation;
      ⚫   Traffic monitoring identifiers.

Upon a memory access, the UMMU looks up the TECT based on the EID to find the corresponding
TECTE, as depicted in Figure 9-4.




                                      Figure 9-4 Configuration lookup

The TECTE data format is as illustrated in Figure 9-5, where the IMPL_DEF field is customized by
specific implementation.




unifiedbus.com                                                                                     277
9 Memory Management



     Offset 31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9                                                                                                                           8          7              6              5      4   3                        2    1   0




                                                                                                                                                                                                      MEM_ATTR_SEL
                                                                                                                                                   SECURE_SEL




                                                                                                                                                                                                                                        MEM_ATTR




                                                                                                                                                                                                                                                                                  ST_MODE
                              IMPL_DEF




                                                                                                                                                                         IMPL_DEF
                                                                                             MAPT_EN

                                                                                                             INST_SEL


                                                                                                                                  PRIV_SEL
                                                                                    EM_EN
      3~0                                                                                                                                                                                                                                                                                       V



      7~4                                             RSVD                                                                                                                                   S2_VMID[15:0]




                                                                                                                                                                                                                                                                                  TCT_NUM
                                                                                                                                                                                                                                               IMPL_DEF
     11~8                                                                        TCT_PTR[31:6]
                                                      TCT_STALL_EN
                                         TCT_MTM_EN
                   IMPL_DEF




                                                                              TCT_FMT
     15~12                                                           RSVD                                                                                             TCT_PTR[51:32]




                                                                                                                                                                                                                                                                  S_S2_TSZ NS_S2_TSZ
                                                                                                                                                                                               NS_S2_TG
                              IMPL_DEF




                                                                                                                                                                         IMPL_DEF IMPL_DEF




                                                                                                                                                                                                                         NS_S2_SL
                                                                                                       S2_AFFD




                                                                                                                                         S2_ENDI


                                                                                                                                                            S2_PAS
                                                                                                                    S2_HAF
                                                                                                                             S2_HDF
                                                                                    S2_FBR
                                                                                             S2_FBS


     19~16




                                                                                                                                                                                               S_S2_TG


                                                                                                                                                                                                                         S_S2_SL
     23~20   IMPL_DEF                                                               RSVD


     27~24                                                                              NS_S2_MATT[31:4]                                                                                                                                                                         RSVD
     31~28                    RSVD                                                                                                                                   NS_S2_MATT[51:32]
     35~32                                                                              S_S2_MATT[31:4]                                                                                                                                                                          RSVD
     39~36                    RSVD                                                                                                                                   S_S2_MATT[51:32]
     43~40                                                   MTMC_PTR[31:12]                                                                                                                                                    RSVD
     47~44                    RSVD                                                                                                                                   MTMC_PTR[51:32]
                                                      IMPL_DEF




     51~48         RSVD                                                     MTM_GP[7:0]                                                                                                      MTM_ID[15:0]


     55~52                                                                                                                   RSVD
     59~56                                                                                                                   RSVD
     63~60                                                                                                                   RSVD

                                                                            Figure 9-5 TECTE data format

The meanings of fields in the TECTE data format are presented in Table 9-1.

                                                                                  Table 9-1 TECTE fields
 Field                        Bits                                    Description
 V                            1                                       Valid, indicating whether the current entry is valid.
                                                                      ● 1'b0: Invalid. In this case, all other fields in the entry are ignored;
                                                                      ● 1'b1: Valid.
                                                                      If the value of this field is 1'b0, the UMMU terminates the memory
                                                                      access, returns an error message to the User, and reports an event.
 ST_MODE                      3                                       Stage Mode, indicating whether Stage 1 and Stage 2 address
                                                                      translation is enabled or disabled.
                                                                      ● 3'b000~3'b100: Invalid. The UMMU returns an error message to
                                                                        the User, but does not record an event;
                                                                      ● 3'b101: Only Stage 1 address translation is enabled;
                                                                      ● 3'b110: Only Stage 2 address translation is enabled;




unifiedbus.com                                                                                                                                                                                                                                                                                      278
9 Memory Management



 Field            Bits   Description
                         ● 3'b111: Both Stage 1 and Stage 2 address translation is enabled.
                         If the UMMU does not support Stage 1 address translation, 3'b1x1 is
                         illegal.
                         If the UMMU does not support Stage 2 address translation, 3'b11x is
                         illegal.
                         If the UMMU does not support Stage 2 address translation in secure
                         state, 3'b11x for the TECTE in secure state is illegal.
 MEM_ATTR         4      Memory Attribute, indicating the memory attribute override value.
                         If the value of MEM_ATTR_SEL is 1'b1, the memory attribute
                         specified by this field is used for accessing the target memory upon
                         memory access requests.
                         Note: The specific bit meanings of this field are not defined in this protocol, and
                         the definition in the system architecture where the UMMU works applies.

 MEM_ATTR_SEL     1      Memory Attribute Select, indicating the selection mechanism of the
                         memory attribute.
                         ● 1'b0: The memory attribute provided by the memory access
                           request is used;
                         ● 1'b1: The attribute provided by TECTE.MEM_ATTR is used.

 SECURE_SEL       2      Secure Select, indicating the selection mechanism of the secure
                         attribute.
                         ● 2'b00~2'b01: The non-secure attribute provided by the memory
                           access request is used;
                         ● 2'b10~2'b11: The secure attribute is selected based on the value
                           configured for this field. The meanings of SECURE_SEL[0] are:
                            -     1'b0: Secure;
                            -     1'b1: Non-secure.

 PRIV_SEL         2      Privilege Select, indicating the selection mechanism of the
                         unprivileged/privileged attribute.
                         ● 2'b00~2'b01: The unprivileged/privileged attribute provided by the
                           memory access request is used;
                         ● 2'b10~2'b11: The unprivileged/privileged attribute is overwritten by
                           the value configured for this field. The meanings of PRIV_SEL[0]
                           are:
                            -     1'b0: Unprivileged;
                            -     1'b1: Privileged.
 INST_SEL         2      Instruction/Data Select, indicating the selection mechanism of the
                         instruction/data attribute.
                         ● 2'b00~2'b01: The data/instruction attribute provided by the
                           memory access request is used;
                         ● 2'b10~2'b11: The data/instruction attribute is overwritten by the
                           value configured for this field. The meanings of INST_SEL[0] are:
                            -     1'b0: Data;
                            -     1'b1: Instruction.




unifiedbus.com                                                                                             279
9 Memory Management



 Field            Bits   Description
 MAPT_EN          1      MAPT Enable, indicating the MAPT status (enabled or disabled) for
                         the TECTE, namely whether the MAPT is used for permission checks
                         for memory accesses indexed to the TECTE.
                         ● 1'b0: The MAPT is not used for permission checks. In this case,
                           the MAPT is disabled for any target context table entry (TCTE) in
                           the TCT;
                         ● 1'b1: The MAPT is used for permission checks. In this case, the
                           MAPT can be enabled independently for each TCTE in the TCT.
 EM_EN            1      Event Merge Enable, indicating the enablement status of event
                         merging.
                         ● 1'b0: Events are not merged;
                         ● 1'b1: Similar events are merged.
                         The UMMU can merge fault records of addresses, access types, and
                         TokenIDs that are of the same page granularity to reduce the use of
                         event queues.
 S2_VMID          16     Stage 2 Virtual Machine Identifier, identifying the virtual machine
                         corresponding to TLB entries.
 TCT_NUM          5      TCT Number, indicating the number of TCTEs pointed to by the
                         TCT_PTR field, which is specifically 2TCT_NUM.
                         ● If Stage 1 address translation is disabled, this field is ignored;
                         ● If Stage 1 address translation is enabled and the value of this field
                           is 0, or if the value of this field exceeds 0 and the TokenID
                           provided by a memory access exceeds the range specified by this
                           field, the UMMU terminates the memory access and reports an
                           event.
 TCT_PTR          46     TCT Pointer, indicating the location of the TCT information
                         corresponding to Stage 1 address translation. This field is
                         TCT_PTR[51:6] of the address pointer. The address is 64-byte
                         aligned by default.
                         ● If Stage 1 address translation is disabled, this field is ignored;
                         ● If Stage 2 address translation is enabled, this field should not
                           exceed the intermediate physical address size (IPAS) if it
                           indicates the intermediate physical address (IPA), and should not
                           exceed the physical address size (PAS) if it indicates the physical
                           address (PA).
 TCT_FMT          2      TCT Format, indicating the TCT format used when UMMU context
                         lookup is enabled.
                         ● 2'b00: Linear TCT, which is indexed by using
                           TokenID[TECTE.TCT_NUM-1:0];
                         ● 2'b01: Two-level TCT, where the L2 TCT has 64 entries;
                         ● 2'b10~2'b11: Reserved.
                         When multiple TokenIDs are supported and enabled, up to 2–220
                         TokenIDs are allowed.
                         If Stage 1 address translation is disabled, this field is ignored.
 TCT_STALL_EN     1      TCT Stall Enable, indicating whether to enable event reporting when




unifiedbus.com                                                                                  280
9 Memory Management



 Field            Bits   Description
                         the processor supports stall function.
                         ● 1'b0: Not enable;
                         ● 1'b1: Enable.

 TCT_MTM_EN       1      TCT Memory Traffic Monitoring Enable, indicating whether to enable
                         TCT memory traffic monitoring.
                         ● 1'b0: Not enable. The MTM_ID and MTM_GP fields of the
                           memory access request come from the TECT.MTM_ID and
                           TECT.MTM_GP fields;
                         ● 1'b1: Enable. The MTM_ID and MTM_GP fields of the memory
                           access request come from the TCT.MTM_ID and TCT.MTM_GP
                           fields.
 NS_S2_TSZ        6      Non-Secure Stage 2 Table Size, indicating the size of the IPA input
                         area in the non-secure Stage 2 address translation table.
                         Notes:
                         ⚫   The bit meanings of this field are not defined by this protocol, and the
                             definition in the system architecture applies.
                         ⚫   If Stage 2 address translation is disabled, this field is reserved.

 NS_S2_SL         2      Non-Secure Stage 2 Starting Level, indicating the starting level of the
                         non-secure Stage 2 address translation table.
                         Notes:
                         ⚫   The bit meanings of this field are not defined by this protocol, and the
                             definition in the system architecture applies.
                         ⚫   If Stage 2 address translation is disabled, this field is reserved.

 NS_S2_TG         2      Non-Secure Stage 2 Translation Granule, indicating the translation
                         granularity of the non-secure Stage 2 address translation table.
                         Notes:
                         ⚫   The bit meanings of this field are not defined by this protocol, and the
                             definition in the system architecture applies.
                         ⚫   If Stage 2 address translation is disabled, this field is reserved.

 S2_PAS           3      Stage 2 Physical Address Size, indicating the PA size output in Stage
                         2 address translation.
                         ● 3'b000: 32 bits;
                         ● 3'b101: 48 bits;
                         ● Others: Reserved.

 S2_ENDI          1      Stage 2 Endianness, indicating the endianness of the Stage 2
                         address translation table.
                         ● 1'b0: Little endian;
                         ● 1'b1: Big endian.
                         If Stage 2 address translation is disabled, this field is reserved.
 S2_HDF           1      Stage 2 Hardware Dirty Flag, indicating whether the hardware
                         automatically updates the Dirty flag in the Stage 2 address translation
                         table.
                         For details, see the description of the S2_HAF field below.




unifiedbus.com                                                                                          281
9 Memory Management



 Field            Bits   Description
 S2_HAF           1      Stage 2 Hardware Access Flag, indicating whether the hardware
                         automatically updates the Access flag in the Stage 2 address
                         translation table.
                         The meanings of the {S2_HDF, S2_HAF} combination are:
                         ● 2'b00: Automatic flag update by hardware is disabled;
                         ● 2'b01: Access flag update by hardware is enabled;
                         ● 2'b10: Reserved;
                         ● 2'b11: Access and Dirty flag update by hardware is enabled.

 S2_AFFD          1      Stage 2 Access Flag Fault Disable, indicating whether to disable
                         Stage 2 Access flag fault reporting.
                         When automatic Access flag update by hardware is disabled, if the
                         value of MATTE.AF is 1'b0 for the accessed MATTE, the behavior is
                         as follows:
                         ● 1'b0: Access flag faults are reported. The processing behavior is
                           determined by TECTE.S2_FBS and TECTE.S2_FBR;
                         ● 1'b1: Access flag faults are not reported.
                         When the value of S2_HAF is 1'b1, this field is ignored.
                         If Stage 2 address translation is disabled, this field is reserved.
 S2_FBS           1      Stage 2 Fault Behavior Stall, indicating that the processing behavior
                         of a Stage 2 address translation fault is to stall the fault.
                         If Stage 2 address translation is disabled, this field is reserved.
 S2_FBR           1      Stage 2 Fault Behavior Record, indicating that the processing
                         behavior of a Stage 2 address translation fault is to record the fault.
                         If Stage 2 address translation is disabled, this field is reserved.
 S_S2_TSZ         6      Secure Stage 2 Table Size, indicating the size of the IPA input area
                         in the secure Stage 2 address translation table.
                         Notes:
                         ⚫   The bit meanings of this field are not defined by this protocol, and the
                             definition in the system architecture applies.
                         ⚫   If Stage 2 address translation is disabled, this field is reserved.

 S_S2_SL          2      Secure Stage 2 Starting Level, indicating the starting level of the
                         secure Stage 2 address translation table.
                         Notes:
                         ⚫   The bit meanings of this field are not defined by this protocol, and the
                             definition in the system architecture applies.
                         ⚫   If Stage 2 address translation is disabled, this field is reserved.

 S_S2_TG          2      Secure Stage 2 Translation Granule, indicating the translation
                         granularity of the secure Stage 2 address translation table.
                         Notes:
                         ⚫   The bit meanings of this field are not defined by this protocol, and the
                             definition in the system architecture applies.
                         ⚫   If Stage 2 address translation is disabled, this field is reserved.

 NS_S2_MATT       48     Non-Secure Stage 2 MATT, indicating the entry address of the non-
                         secure Stage 2 address translation table. This field is



unifiedbus.com                                                                                          282
9 Memory Management



 Field                 Bits      Description
                                 NS_S2_MATT[51:4]. The address is 16-byte aligned by default.
                                 If Stage 2 address translation is disabled, this field is reserved.
 S_S2_MATT             48        Secure Stage 2 MATT, indicating the entry address of the secure
                                 Stage 2 address translation table. This field is S_S2_MATT[51:4].
                                 The address is 16-byte aligned by default.
                                 If Stage 2 address translation is disabled, this field is reserved.
 MTMC_PTR              40        Memory Traffic Monitoring Context Pointer. This field is
                                 MTMC_PTR[51:12]. The address is 4-KB aligned by default.
 MTM_ID                16        Memory Traffic Monitoring ID
 MTM_GP                8         Memory Traffic Monitoring Group


9.4.2.2 Context Lookup

9.4.2.2.1 General Requirements

After obtaining the TECTE through configuration lookup, the UMMU proceeds to obtain the status
(enabled or disabled) of Stage 1 address translation for the corresponding Entity through the
ST_MODE field.

When Stage 1 address translation is enabled for the Entity, the UMMU looks up the TCT based on the
TokenID to obtain the context information of the accessed memory segment, including details about the
Stage 1 address translation process and the status (enabled or disabled) of permission check. The TCT
base address is recorded in the TECTE.TCT_Ptr field. The TCT can be a linear TCT or two-level TCT,
determined by the TECTE.TCT_FMT field.

When Stage 1 address translation is disabled for the Entity, the UMMU does not perform context
lookup.


9.4.2.2.2 Linear TCT

A linear TCT consists of several contiguous TCTEs and is indexed directly using the TokenID (as
presented in Figure 9-6).




                              Figure 9-6 Linear TCT organization and lookup




unifiedbus.com                                                                                         283
9 Memory Management



The TCTE data format is as illustrated in Figure 9-7.
     Offset 31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9                                                                      8        7         6   5   4       3         2       1                  0




                                                                                              MAPT_MODE

                                                                                                          IMPL_DEF




                                                                                                                                                             IMPL_DEF




                                                                                                                                                                                                         IMPL_DEF
                                                                             MAPT_EN
                                                                    MAC_EN




                                                                                                                                                                                GPAS
                                                                                       RTGS




                                                                                                                                             AFFD




                                                                                                                                                                                                  ENDI
                                                           E_Bit




                                                                                                                                 HAF
                                                                                                                                       HDF
                                                                                                                     FBR
                                                                                                                           FBS
      3~0                                 RSVD                                                                                                                                                                               V



      7~4                                         RSVD                                                                                         IMPL_DEF




                                                                                                                                                    MATTWD
     11~8                                         RSVD                                                               IMPL_DEF                                  TGS                          SZ


     15~12                              RSVD                       MTM_GP                                                                           MTM_ID
     19~16                                                            MATTBA[31:4]                                                                                                          IMPL_DEF
                IMPL_DEF




     23~20                 NS                    RSVD                                                                            MATTBA[51:32]




                                                                                                                                                                                                                MAPT_BB_MA
                                                                                                                                                                                       IMPL_DEF
     27~24                                                          MAPT_BBA[31:5]



     31~28 MAPT_BB_SZ                                    RSVD                                                                            MAPT_BBA[47:32]




                                                                                                                                                                                                                MAPT_BT_MA
                                                                                                                                                                                       IMPL_DEF
     35~32                                                          MAPT_BTA[31:5]
                           MAPT_BT_SZ
             RSVD




     39~36                                               RSVD                                                                            MAPT_BTA[47:32]



     43~40                                                                                MATTR0[31:0]
     47~44                                                                                MATTR1[31:0]
     51~48                                                                                   RSVD
     55~52                                                                                   RSVD
     59~56                                                                                   RSVD
     63~60                                                                                   RSVD

                                                           Figure 9-7 TCTE data format

The meanings of fields in the TCTE data format are presented in Table 9-2.

                                                                     Table 9-2 TCTE fields
 Field                                   Bits    Description
 V                                       1       Valid, indicating whether the current entry is valid.
                                                 ● 1'b0: Invalid;
                                                 ● 1'b1: Valid.
                                                 When the value of this field obtained through context lookup is 1'b0, the
                                                 UMMU terminates the memory access and reports an event.
 ENDI                                    1       Endianness of the Stage 1 address translation table and Stage 1
                                                 permission table.
                                                 ● 1'b0: Little endian;
                                                 ● 1'b1: Big endian.




unifiedbus.com                                                                                                                                                                                                                   284
9 Memory Management



 Field           Bits   Description
                        Note: If the value of TCTE.MATTWD is 1'b1, this field is reserved.

 GPAS            3      Guest Physical Address Size, indicating the size of the MATT and MAPT
                        base address (usually a PA).
                        ● 3'b000: 32 bits;
                        ● 3'b001: 36 bits;
                        ● 3'b010: 40 bits;
                        ● 3'b011: 42 bits;
                        ● 3'b100: 44 bits;
                        ● 3'b101: 48 bits;
                        ● 3'b110~3'b111: Reserved.
                        Note: After Stage 1 address translation is completed, this field is used to check the
                        output address range. If it is beyond this range, the UMMU reports an event. If
                        [51:eff_GPAS] is not 0, the UMMU reports an event, where eff_GPAS indicates the
                        actual bits of the field.

 AFFD            1      Access Flag Fault Disable, indicating whether to disable Stage 1 Access
                        flag fault reporting.
                        When automatic Access flag update by hardware is disabled, if the value
                        of MATTE.AF is 1'b0 for the accessed MATTE, the behavior is as follows:
                        ● 1'b0: Access flag faults are reported. The processing behavior is
                          determined by TCTE.FBS and TCTE.FBR;
                        ● 1'b1: Access flag faults are not reported.
                        Note: When the value of TCTE.HAF is 1'b1, this field is ignored.

 HDF             1      Hardware Dirty Flag, indicating whether the hardware automatically
                        updates the Dirty flag in the Stage 1 address translation table.
                        For details, see the description of the HAF field below.
 HAF             1      Hardware Access Flag, indicating whether the hardware automatically
                        updates the Access flag in the Stage 1 address translation table.
                        The meanings of the {HDF, HAF} combination are:
                        ● 2'b00: Automatic flag update by hardware is disabled;
                        ● 2'b01: Access flag update by hardware is enabled;
                        ● 2'b10: Reserved;
                        ● 2'b11: Access and Dirty flag update by hardware is enabled.

 FBS             1      Fault Behavior Stall, indicating that the processing behavior of a Stage 1
                        address translation fault is to stall the fault.
                        If the value of TECTE.TCT_STALL_EN is 1'b0, value 1 is illegal for this
                        field.
 FBR             1      Fault Behavior Record, indicating that the processing behavior of a Stage
                        1 address translation fault is to record the fault.
 MAPT_MODE       1      MAPT Mode, indicating the mode of the MAPT contained in the TCTE.
                        ● 1'b0: Single-entry MAPT;
                        ● 1'b1: Multi-level MAPT.




unifiedbus.com                                                                                                  285
9 Memory Management



 Field           Bits   Description
 RTGS            2      Range Table Granule Size. This field is valid in a multi-level MAPT and
                        indicates the maximum granularity that can be represented at the last
                        level of the MAPT.
                        ● 2'b00: Reserved;
                        ● 2'b01: 4 KB;
                        ● 2'b10: 2 MB;
                        ● 2'b11: Reserved.

 MAPT_EN         1      MAPT Enable, indicating the MAPT status (enabled or disabled) for the
                        TCTE, namely whether the MAPT is used for permission checks for
                        memory accesses indexed to the TCTE.
                        ● 1'b0: The MAPT is not used for permission checks;
                        ● 1'b1: The MAPT is used for permission checks.
                        Note: When the value of TECTE.MAPT_EN is 1'b0, this field is ignored.

 MAC_EN          1      MAC Enable, indicating the TokenValue check mode.
                        ● 1'b0: Nonce;
                        ● 1'b1: Reserved.

 E_Bit           1      Exclusive-Bit. For details about the check rules, see Section 9.4.4.3.3.
                        When the E-Bit check fails, the UMMU needs to report an event.
 SZ              6      Size, indicating the maximum bits of the UBA, which are calculated as
                        follows: 64 minus SZ.
                        Note: The valid range of this field is determined by the register and the system
                        architecture.

 TGS             2      Translation Granule Size, indicating the granularity of the address
                        translation table.
                        Note: The bit meanings of this field are not defined by this protocol, and the definition
                        in the system architecture applies.

 MATTWD          1      MATT Walk Disable, indicating whether to disable MATT-based address
                        translation.
                        ● 1'b0: The MATT is used for address translation;
                        ● 1'b1: The MATT is not used for address translation. In case of a
                          missed TLB match, the UMMU reports an event. In this case, the
                          TCTE.SZ, TCTE.TGS, and TCTE.MATTBA fields are ignored.
 MTM_ID          16     Memory Traffic Monitoring ID
                        When the value of TECTE.TCT_MTM_EN is 1'b0, this field is ignored.
 MTM_GP          8      Memory Traffic Monitoring Group
                        When the value of TECTE.TCT_MTM_EN is 1'b0, this field is ignored.
 MATTBA          48     MATT Base Address, bits [51:4]
                        When the value of TCTE.MATTWD is 1'b1, this field is ignored.
 NS              1      Non-Secure, indicating the memory non-secure attribute of the starting-
                        level translation table pointed to by the MATT being accessed.
                        ● 1'b0: Non-secure;




unifiedbus.com                                                                                                 286
9 Memory Management



 Field             Bits     Description
                            ● 1'b1: Secure.
                             Note: This field is used only when the secure TECTE is accessed. Otherwise, this
                             field is ignored.

 MAPT_BB_MA        2        MAPT Base Block Memory Attribute, indicating the memory attribute of
                            the MAPT base block, determined by the system.
 MAPT_BBA          43       MAPT Base Block Address, indicating bits [47:5] of the base address of
                            the MAPT base block.
                            The address range indicated by this field cannot exceed the range
                            defined by GPAS. Otherwise, the configuration is illegal and the UMMU
                            reports an event.
 MAPT_BB_SZ        4        MAPT Base Block Size, indicating the size of an MAPT base block, which
                            is specifically 4 KB × 2MAPT_BB_SZ. The value range is from 4'b0000 to
                            4'b1001.
                            When the value of TCTE.MAPT_MODE is 1'b0, this field is ignored.
 MAPT_BT_MA        2        MAPT Block Table Memory Attribute, indicating the memory attribute of
                            the MAPT block table, determined by the system.
 MAPT_BTA          43       MAPT Block Table Address, indicating bits [47:5] (the other bits being 0)
                            of the base address of the MAPT block table.
                            The address range indicated by this field cannot exceed the range
                            defined by GPAS. Otherwise, the configuration is illegal and the UMMU
                            reports an event.
 MAPT_BT_SZ        3        MAPT Block Table Size, indicating the size of an MAPT block table, which
                            is specifically 4 KB × 2MAPT_BT_SZ. The minimum size is 4 KB, and the
                            maximum size is 512 KB.
                            When the value of TCTE.MAPT_MODE is 1'b0, this field is ignored.
 MATTR0            32       Memory Attribute 0, indicating the attribute of the found page table. The
                            attribute is selected using the AttrIndx field in the address translation page
                            table.
                            Note: The specific bit meanings of this field are not defined in this protocol, and the
                            definition in the system architecture where the UMMU works applies.

 MATTR1            32       Memory Attribute 1, indicating the attribute of the found page table. The
                            attribute is selected using the AttrIndx field in the address translation page
                            table.
                            Note: The specific bit meanings of this field are not defined in this protocol, and the
                            definition in the system architecture where the UMMU works applies.



9.4.2.2.3 Two-level TCT

When a two-level TCT is used, the relevant data structure is organized into level-1 TCT (L1 TCT) and
level-2 TCT (L2 TCT) according to the order of lookup by the UMMU. The L1 TCT consists of several
pointers to the L2 TCT.

The process of context lookup by the UMMU in a two-level TCT is as illustrated in Figure 9-8:

      1.   The UMMU uses TokenID[TCT_NUM-1:6] as the index to look up the L1 TCT to obtain the
           base address of the L2 TCT from the matched table entry (namely, L1 TCTE);



unifiedbus.com                                                                                                        287
9 Memory Management



      2.   The UMMU uses TokenID[5:0] as the index to look up the L2 TCT to obtain the context
           information from the matched table entry (namely, L2 TCTE).




                        Figure 9-8 Two-level TCT organization and hierarchical lookup

The L1 TCT descriptor data format is as illustrated in Figure 9-9.
Offset 31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5             4    3   2   1    0
 3~0                          L2TCTPtr[31:12]                                     RSVD                           V
 7~4                  RSVD                                        L2TCTPtr[51:32]

                                  Figure 9-9 L1 TCT descriptor data format

The meanings of fields in the L1 TCT descriptor data format are presented in Table 9-3.

                                     Table 9-3 L1 TCT descriptor fields
 Field             Bits              Description
 V                 1                 Valid, indicating whether the L1 TCTE is valid.
                                     ● 1'b0: Invalid. In this case, all other fields are ignored;
                                     ● 1'b1: Valid.

 L2TCTPtr          40                L2 TCT Pointer, indicating bits [51:12] of the base address of the L2
                                     TCT.
                                     If Stage 2 address translation is enabled, the value of this field
                                     should not exceed the IPAS. If Stage 2 address translation is
                                     disabled, the value of this field should not exceed the PAS.


The L2 TCT descriptor data format and field meanings are the same as those of the L1 TCT descriptor.


9.4.3 UMMU Address Translation
After configuration lookup and context lookup, the UMMU obtains the context information of the UBA
space. The UMMU translates the UBAs into PAs through address translation. Typically, in virtualization
scenarios, when the Home is a virtual machine, the UMMU supports two-stage address translation, as
illustrated in Figure 9-10.




unifiedbus.com                                                                                                  288
9 Memory Management




                        Figure 9-10 UMMU function flow in virtualization scenarios

The two stages of address translation could be enabled separately (as illustrated in Figure 9-11), where
the IPA is an intermediate PA translated from a UBA.

      ⚫    Stage 1 address translation: The UBA is translated into an IPA, with information related to
           Stage 1 address translation stored in the TCTE;
      ⚫    Stage 2 address translation: The IPA is translated into a PA, with information related to Stage
           2 address translation stored in the TECTE.




                           Figure 9-11 Stage 1 and Stage 2 address translation

The two-stage address translation process is as illustrated in Figure 9-12:

      1.   Through configuration lookup, the UMMU obtains the Stage 2 MATT base address and TCT
           base address from the TECTE. If both Stage 1 and Stage 2 address translation is enabled,
           the UMMU SHALL perform Stage 2 address translation on the TCT base address to
           translate the IPA into a PA. If only Stage 1 address translation is enabled, the UMMU skips
           Stage 2 address translation for the TCT. If only Stage 2 address translation is enabled, the
           UMMU skips context lookup;
      2.   Through context lookup, the UMMU obtains the Stage 1 MATT base address from the TCTE;
      3.   The UMMU performs Stage 1 address translation on the UBA, which may include multi-level
           lookups:
           (1)   Before starting level-x lookup, the UMMU needs to perform Stage 2 address
                 translation on the level-x MATT base address;



unifiedbus.com                                                                                           289
9 Memory Management



           (2)   After completing level-x lookup, the UMMU obtains the level-x MATT base address;
      4.   After completing the last level of Stage 1 address translation, the UMMU could obtain the
           IPA corresponding to the UBA; after completing the last level of Stage 2 address translation,
           the UMMU could obtain the PA corresponding to the UBA.




                               Figure 9-12 Two-stage address translation

The specific address translation process, data structures of the MATT at each level, and meanings of
related fields are defined by the architecture of the UBPU where the UMMU works.


9.4.4 UMMU Permission Check

9.4.4.1 General Requirements

The UMMU MAY perform permission check alongside address translation based on configurations.
After the configuration lookup and context lookup, if permission check is enabled for the accessed
Entity (indicated by TECTE.MAPT_EN), the UMMU could obtain the context information of the
permission space. The UMMU looks up the permission information of the corresponding memory in the
MAPT based on the UBAs and compares the acquired information with that carried in memory access
requests to determine whether the memory access successfully passes the permission check.

The MAPT can be either a single-entry MAPT or a multi-level MAPT, determined by
TCTE.MAPT_MODE. Specific storage formats and other related information can be found in the TCTE.

The UMMU permission table can be accessed directly by unprivileged software, but the operable MAPT
space is limited to an MAPT base block. For this MAPT base block, an MAPT base block address
(BBA) is assigned when the privileged software creates TCTEs, thereby isolating the permission table.




unifiedbus.com                                                                                         290
9 Memory Management



9.4.4.2 Permission Lookup

9.4.4.2.1 MAPT Storage Format

The MAPT is stored in one or more contiguous memory blocks (MAPT blocks). The TCTE stores
information such as the base address of the MAPT block that stores the L0 MAPT (MAPT base block).
The base address of the L0 MAPT is the base address of the MAPT base block.

If subsequent levels of MAPTs are also stored in the MAPT base block, they need to be located using
offsets, following this rule: Base address of Lx MAPT = TCTE.MAPT_BBA:5'b0 + L(x – 1)
MAPTE.Next_Level_Offset.

When only the MAPT base block is used for storage, the indexing method specific to MAPT levels is as
illustrated in Figure 9-13, and the corresponding permission lookup process is as illustrated in Figure 9-14.




            Figure 9-13 Level-specific MAPT indexing when only the MAPT base block is used




                  Figure 9-14 Permission lookup when only the MAPT base block is used



unifiedbus.com                                                                                             291
9 Memory Management



If the MAPT at each level needs to be stored in multiple MAPT blocks, the MAPT block table should be
used to record the information of the occupied MAPT blocks. The TCTE provides information such as
the base address of the MAPT block table. In this case, the base address of the L0 MAPT remains the
base address of the MAPT base block. Subsequent levels of MAPTs need to be located through their
respective memory base addresses and corresponding offsets, as follows:

      ⚫   If the value of L(x – 1) MAPTE.N is 1b'0, then:
          Lx MAPT base address = L(x – 1)_Block_BA + L(x – 1) MAPTE.Next_Level_Offset, where
          L(x – 1)_Block_BA is the base address of the MAPT block containing the L(x – 1) MAPT;
      ⚫   If the value of L(x – 1) MAPTE.N is 1b'1, then:
          Lx MAPT base address = Next_Block_BA + L(x – 1) MAPTE.Next_Level_Offset, where
          Next_Block_BA is the base address of the MAPT block containing the Lx MAPT and can be
          obtained from the MAPT base block using the L(x – 1) MAPTE.Next_Level_Index.

The data format of the MAPT block table entry is as illustrated in Figure 9-15.
Offset 31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5              4   3 2 1    0
 3~0                                   MAPT_BA[31:5]                                                RSVD     V
 7~4     MAPT_BS                  RSVD                                  MAPT_BA[47:32]

                           Figure 9-15 Data format of the MAPT block table entry

The meanings of fields in the data format of the MAPT block table entry are presented in Table 9-4.

                                  Table 9-4 MAPT block table entry fields
 Field                Bits              Description
 V                    1                 Valid, indicating whether the current entry is valid.
                                        ● 1b'0: Invalid;
                                        ● 1b'1: Valid.
 MAPT_BA              43                MAPT Block Address, indicating bits [47:5] of the base address
                                        of the MAPT block.
 MAPT_BS              4                 MAPT Block Size, indicating the size of an MAPT block. The
                                        calculation formula is 4 KB × 2MAPT_BS.


When multiple MAPT blocks are used, the indexing method specific to MAPT levels is as illustrated in
Figure 9-16, and the corresponding permission lookup process is illustrated in Figure 9-17.




             Figure 9-16 Level-specific MAPT indexing when multiple MAPT blocks are used



unifiedbus.com                                                                                              292
9 Memory Management




                   Figure 9-17 Permission lookup when multiple MAPT blocks are used

The MAPT MAY be managed directly by unprivileged software. To ensure the permission table is
isolated, the physical memory for MAPT blocks SHALL be allocated by privileged software and mapped
to the virtual addresses of unprivileged software. This segment of memory will not be swapped out, so
access to the MAPT by unprivileged software will not trigger page faults. Additionally, access to an
MAPT block by unprivileged software SHALL NOT exceed the size of the MAPT block.


9.4.4.2.2 Single-Entry MAPT

For a single-entry MAPT, the UMMU can directly obtain the unique memory address permission table
entry (UMAPTE) through TCTE.MAPT_BBA. This entry contains a UBA range (indicated by the Base
and Limit fields). The UMMU SHALL determine whether the UBAs carried in memory access requests
fall within this range to decide whether to proceed with checking other permission information or
terminate the memory access (see Section 9.4.4.3.2). The permission lookup process for a single-entry
MAPT is as illustrated in Figure 9-18.




                         Figure 9-18 Permission lookup for a single-entry MAPT




unifiedbus.com                                                                                         293
9 Memory Management



The UMAPTE data format is as illustrated in Figure 9-19.




                                  Figure 9-19 UMAPTE data format

The meanings of fields in the UMAPTE data format are presented in Table 9-5.

                                      Table 9-5 UMAPTE fields
 Field               Bits            Description
 V                   1               Valid, indicating whether the UMAPTE is valid.
                                     ● 1'b0: Invalid;
                                     ● 1'b1: Valid.
                                     If the value of this field is 1'b0, the UMMU terminates the
                                     memory access, returns an error message to the User, and
                                     reports an event.
 E_Bit               1               Exclusive-Bit. For details about the check rules, see Section
                                     9.4.4.3.3.
                                     When the E-Bit check fails, the UMMU needs to report an event.
 Permission          6               Indicating the access types supported by the address range
                                     pointed to by the UMAPTE. The access types corresponding to
                                     the bits in this field are:
                                     ● Bit 0: Write;
                                     ● Bit 1: Read;
                                     ● Bit 2: Atomic operation;
                                     ● Bits [5:3]: Reserved.
                                     The bit meanings for each access type are:
                                     ● 1'b0: This type of access is not supported;
                                     ● 1'b1: This type of access is supported.

 Base                48              Indicates the start address of the address range corresponding
                                     to the UMAPTE.
 TOKEN_CHK           1               Token Check, indicating whether TokenValue check is required.
                                     ● 1'b0: Not required;
                                     ● 1'b1: Required;

 Limit               48              Indicates the upper limit of the address range corresponding to
                                     the UMAPTE.




unifiedbus.com                                                                                       294
9 Memory Management



 Field                   Bits           Description
 TokenVal0               32             Indicates the primary TokenValue to be checked.

 TokenVal1               32             Indicates the secondary TokenValue to be checked.


9.4.4.2.3 Multi-level MAPT

A multi-level MAPT supports two granularities—4 KB and 2 MB (determined by TCTE.RTGS). In the 4
KB granularity, a multi-level MAPT supports up to 4 levels; in the 2 MB granularity, a multi-level MAPT
supports up to 3 levels. The UMMU SHALL use the UBAs as indexes for permission lookups level by
level, with the table entry at each level containing a UBA range. By comparing this range with the UBAs
carried in memory access requests, the UMMU decides whether to check other permission information,
continue looking up the next-level MAPT, or terminate the memory access.

When a multi-level MAPT is used, the MAPT at each level is stored in one or more contiguous memory
blocks. The base address of the level-0 MAPT (L0 MAPT) can be obtained from the TCTE. The base
addresses of the remaining levels of MAPTs are calculated from the memory block information provided
in the previous-level MAPTE and the offset of the MAPT within that memory block.

In the example of 4 KB granularity, the permission lookup process of a multi-level MAPT is as illustrated
in Figure 9-20. Below, we detail the steps performed at each level:

      1.   The UMMU obtains the L0 MAPT base address from the TCTE (see TCTE.MAPT_BBA) and
           uses the UBA[47:39] as the index to obtain the corresponding L0 MAPTE, in the following
           steps:
           (1)      If the UBA falls within the UBA range of the L0 MAPTE, the UMMU will obtain other
                    permission information from the table entry and proceed with the permission check;
           (2)      If the UBA is beyond the UBA range of the L0 MAPTE and the L0 MAPTE contains
                    base address information of the L1 MAPT (determined by L0 MAPTE.T), the UMMU
                    will look up the L1 MAPT;
           (3)      If the UBA is beyond the UBA range of the L0 MAPTE and the L0 MAPTE does not
                    contain base address information of the L1 MAPT (determined by L0 MAPTE.T), the
                    permission check fails and the UMMU will terminate the memory access.
      2.   The UMMU obtains the L1 MAPT base address from the L0 MAPTE and uses the
           UBA[38:30] as the index to obtain the corresponding L1 MAPTE, in the following steps:
           (1)      If the UBA falls within the UBA range of the L1 MAPTE, the UMMU will obtain other
                    permission information from the table entry and proceed with the permission check;
           (2)      If the UBA is beyond the UBA range of the L1 MAPTE and the L1 MAPTE contains
                    base address information of the L2 MAPT (determined by L1 MAPTE.T), the UMMU
                    will look up the L2 MAPT;
           (3)      If the UBA is beyond the UBA range of the L1 MAPTE and the L1 MAPTE does not
                    contain base address information of the L2 MAPT (determined by L1 MAPTE.T), the
                    permission check fails and the UMMU will terminate the memory access.




unifiedbus.com                                                                                           295
9 Memory Management



      3.      The UMMU obtains the L2 MAPT base address from the L1 MAPTE and uses the
              UBA[29:21] as the index to obtain the corresponding L2 MAPTE, in the following steps:
              (1)            If the UBA falls within the UBA range of the L2 MAPTE, the UMMU will obtain other
                             permission information from the table entry and proceed with the permission check;
              (2)            If the UBA is beyond the UBA range of the L2 MAPTE and the L2 MAPTE contains
                             base address information of the L3 MAPT (determined by L2 MAPTE.T), the UMMU
                             will look up the L3 MAPT;
              (3)            If the UBA is beyond the UBA range of the L2 MAPTE and the L2 MAPTE does not
                             contain base address information of the L3 MAPT (determined by L2 MAPTE.T), the
                             permission check fails and the UMMU will terminate the memory access.
      4.      The UMMU obtains the L3 MAPT base address from the L2 MAPTE and uses the
              UBA[20:12] as the index to obtain the corresponding L3 MAPTE, in the following steps:
              (1)            If the UBA falls within the UBA range of the L3 MAPTE, the UMMU will obtain other
                             permission information from the table entry and proceed with the permission check;
              (2)            If the UBA is beyond the UBA range of the L3 MAPTE, the permission check fails and
                             the UMMU will terminate the memory access.




                                   Figure 9-20 Multi-level MAPT permission lookup in 4 KB granularity

The data formats of the MAPTE at various levels are as illustrated in Figure 9-21 to Figure 9-25. Among
them, the L2 MAPTE formats for 4 KB and 2 MB granularities are the same.
    Offset 31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9                        8     7   6   5    4   3       2   1   0
                                                                                                                             E_Bit




     3~0                                      Next_Level_Offset[19:0]                          RSVD   Permission                     N   T   V

      7~4                              Next_Level_Index[15:0]                           RSVD              Next_Level_Offset[29:20]
     11~8                                                                  Base[31:0]
            TOKEN_CHK


                        IMPL_DEF




    15~12                                                               RSVD                                            Base[38:32]



    19~16                                                                 Limit[31:0]
    23~20         IMPL_DEF                                              RSVD                                            Limit[38:32]
    27~24                                                                 TokenVal0
    31~28                                                                 TokenVal1

                                                     Figure 9-21 L0 MAPTE data format



unifiedbus.com                                                                                                                                   296
9 Memory Management



  Offset 31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9                            8     7     6   5       4    3      2      1   0




                                                                                                                                    E_Bit
   3~0                                      Next_Level_Offset[19:0]                       RSVD              Permission                      N      T   V

    7~4                              Next_Level_Index[15:0]                        RSVD                     Next_Level_Offset[29:20]
   11~8 RSVD                                                              Base[29:0]
           TOKEN_CHK


                         IMPL_DEF

  15~12                                                                        RSVD



  19~16 RSVD                                                              Limit[29:0]
  23~20 IMPL_DEF                                                                 RSVD
  27~24                                                                TokenVal0
  31~28                                                                TokenVal1

                                                     Figure 9-22 L1 MAPTE data format

   Offset 31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9                           8     7     6   5   4       3       2      1   0




                                                                                                                                    E_Bit
    3~0                                      Next_Level_Offset[19:0]                      RSVD          Permission                          N      T   V

    7~4                               Next_Level_Index[15:0]                       RSVD                     Next_Level_Offset[29:20]
   11~8                              RSVD                                                 Base[20:0]
             TOKEN_CHK


                          IMPL_DEF




   15~12                                                                       RSVD


   19~16                             RSVD                                                 Limit[20:0]
   23~20           IMPL_DEF                                                     RSVD
   27~24                                                               TokenVal0
   31~28                                                               TokenVal1

                                         Figure 9-23 L2 MAPTE data format in 4 KB granularity

  Offset 31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9                            8     7     6   5       4    3      2      1   0




                                                                                                                                            RSVD
                                                                                                                                    E_Bit
   3~0                                                   RSVD                                               Permission                             T   V

    7~4                                                                 RSVD
   11~8                              RSVD                                                 Base[20:0]
           TOKEN_CHK


                         IMPL_DEF




  15~12                                                                        RSVD



  19~16                              RSVD                                                 Limit[20:0]
  23~20          IMPL_DEF                                                       RSVD
  27~24                                                                TokenVal0
  31~28                                                                TokenVal1

                                         Figure 9-24 L2 MAPTE data format in 2 MB granularity

  Offset 31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9                            8     7     6   5       4    3      2      1   0
                                                                                                                                            RSVD
                                                                                                                                    E_Bit




   3~0                                                   RSVD                                               Permission                             T   V

    7~4                                                                 RSVD
   11~8                                              RSVD                                                         Base[11:0]
           TOKEN_CHK


                         IMPL_DEF




  15~12                                                                        RSVD


  19~16                                              RSVD                                                         Limit[11:0]
  23~20          IMPL_DEF                                                       RSVD
  27~24                                                                TokenVal0
  31~28                                                                TokenVal1

                                                     Figure 9-25 L3 MAPTE data format




unifiedbus.com                                                                                                                                             297
9 Memory Management



The meanings of fields in the MAPTE data format are presented in Table 9-6.

                      Table 9-6 MAPTE fields at each level in a multi-level MAPT
 Field               Bits       Description
 V                   1          Valid, indicating whether the MAPTE is valid.
                                ● 1'b0: Invalid;
                                ● 1'b1: Valid.
                                If the value of this field is 1'b0, the UMMU terminates the memory
                                access, returns an error message to the User, and reports an event.
 T                   1          Terminate, indicating whether the MAPTE contains base address
                                information of the next-level MAPT.
                                ● 1'b0: Contained;
                                ● 1'b1: Not contained.

 N                   1          Not same block, indicating whether the MAPT block where the next-
                                level MAPT resides is the same as that of the MAPTE.
                                ● 1'b0: Same;
                                ● 1'b1: Not same.

 E_Bit               1          Exclusive-Bit. For details about the check rules, see Section
                                9.4.4.3.3.
                                When the E-Bit check fails, an event needs to be reported.
 Permission          5          Indicating the access types supported by the address range pointed
                                to by the MAPTE. The access types corresponding to the bits in this
                                field are:
                                ● Bit 0: Write;
                                ● Bit 1: Read;
                                ● Bit 2: Atomic operation;
                                ● Bits [5:3]: Reserved.
                                The bit meanings for each access type are:
                                ● 1'b0: This type of access is not supported;
                                ● 1'b1: This type of access is supported.

 Next_Level_Offset   30         Indicating the offset of the next-level MAPT relative to the base
                                address of the MAPT block containing the next-level MAPT.
 Next_Level_Index    16         Indicating the index of the MAPT block containing the next-level
                                MAPT in the block table.
 TOKEN_CHK           1          Token Check, indicating whether TokenValue check is required.
                                ● 1'b0: Not required;
                                ● 1'b1: Required.

 Base                48         ● Base address of the permission address range in the range table
                                  (4 KB granularity):
                                   - Base[38:0] is valid in level-0 table lookup;
                                   - Base[29:0] is valid in level-1 table lookup;




unifiedbus.com                                                                                      298
9 Memory Management



 Field                    Bits   Description
                                    - Base[20:0] is valid in level-2 table lookup;
                                    - Base[11:0] is valid in level-3 table lookup;
                                 ● Base address of the permission address range in the range table
                                   (2 MB granularity):
                                    - Base[38:0] is valid in level-0 table lookup;
                                    - Base[29:0] is valid in level-1 table lookup;
                                    - Base[20:0] is valid in level-2 table lookup;
                                     No level-3 table lookup.

 Limit                    48     ● Limit address of the permission address range in the range table
                                   (4 KB granularity):
                                    - Limit[38:0] is valid in level-0 table lookup;
                                    - Limit[29:0] is valid in level-1 table lookup;
                                    - Limit[20:0] is valid in level-2 table lookup;
                                    - Limit[11:0] is valid in level-3 table lookup;
                                 ● Limit address of the permission address range in the range table
                                   (2 MB granularity):
                                    - Limit[38:0] is valid in level-0 table lookup;
                                    - Limit[29:0] is valid in level-1 table lookup;
                                    - Limit[20:0] is valid in level-2 table lookup;
                                 No level-3 table lookup.
 TokenVal0                32     Indicates the primary TokenValue to be checked.
 TokenVal1                32     Indicates the secondary TokenValue to be checked.


9.4.4.3 Permission Comparison

9.4.4.3.1 General Requirements

For memory accesses processed by the UMMU, permission comparisons include:

         ⚫   TokenValue
         ⚫   Exclusive-Bit
         ⚫   Access type

In addition to the above, the UMMU SHALL also combine the permission check with the address
translation process to determine the permission check result of a memory access. In this section,
unless otherwise specified, the MAPTE refers to entries obtained by the UMMU after performing
permission lookups based on the memory access request.




unifiedbus.com                                                                                      299
9 Memory Management



9.4.4.3.2 TokenValue Check

The status (enabled or disabled) of TokenValue check is determined by MAPTE.TOKEN_CHK. The
MAPTE contains the primary and secondary TokenValue. If the TokenValue carried in a memory access
matches with either one of the two TokenValues in the MAPTE, the access passes the TokenValue
check; otherwise, the access fails to pass the TokenValue check (as illustrated in Figure 9-26).




                                            Figure 9-26 TokenValue check

Note: Generally, when the TokenValue in an MAPTE changes, the software sends an invalidation command to the
UMMU to prevent expired permission lookaside buffer (PLB) entries from affecting permission check correctness. With
Positive PLB, the UMMU performs additional permission lookups when the TokenValue check fails based on PLB entries,
in the interest of correctness. In addition, Positive PLB allows the software not to issue an invalidation command when
the TokenValue in the MAPTE changes. The pseudo codes are as follows:


         if (PLB matches) {
              Obtaining TokenValue;
              if (TokenValue matches)
                   TokenValue check is passed;
              else{
                   Invalidating PLB;
                   Obtaining the MAPTE through permission lookup;
                   if (TokenValue matches)
                        TokenValue check is passed;
                   else
                        Permission check fails;
              }
         }
         else{
              Obtaining the MAPTE through permission lookup;
        if (TokenValue matches)
             TokenValue check is passed;
        else
             Permission check fails;
    }



9.4.4.3.3 Exclusivity Check

Exclusive-Bit (E_Bit) of the target memory location is stored in both the TCTE and MAPTE, and is
compared with E_Bit carried in a memory access (Input.E_Bit) during the context lookup and
permission check processes, respectively.




unifiedbus.com                                                                                                        300
9 Memory Management



After the UMMU obtains the TCTE through context lookup, Input.E_Bit SHALL be checked according to
the following rules (as illustrated in Table 9-7):

      ⚫    If Input.E_Bit is 1'b1, or both Input.E_Bit and TCTE.E_Bit are 1'b0, the access passes the
           check, and the UMMU can proceed with address translation and permission check;
      ⚫    If Input.E_Bit is 1'b0 and TCTE.E_Bit is 1'b1, the access fails to pass the permission check
           and the UMMU needs to report an event.

                                    Table 9-7 TCTE exclusivity check rules
                                            TCTE.E_Bit==1'b0        TCTE.E_Bit==1'b1
                     Input.E_Bit==1'b0      Pass                    Deny
                     Input.E_Bit==1'b1      Pass                    Pass


After the UMMU obtains the MAPTE through permission check, Input.E_Bit SHALL be checked
according to the following rules (as illustrated in Table 9-8):

      ⚫    If Input.E_Bit is 1'b1, or both Input.E_Bit and MAPTE.E_Bit are 1'b0, the access passes the
           exclusivity check;
      ⚫    If Input.E_Bit is 1'b0 and MAPTE.E_Bit is 1'b1, the access fails to pass the permission check
           and the UMMU needs to report an event.

                                  Table 9-8 MAPTE exclusivity check rules
                                            MAPTE.E_Bit==1'b0       MAPTE.E_Bit==1'b1
                     Input.E_Bit==1'b0      Pass                    Deny
                     Input.E_Bit==1'b1      Pass                    Pass


9.4.4.3.4 Access Type Check

The access types include read, write, and atomic operation. The access type permission for the
accessed memory is indicated by the MAPTE.Permission field. If the corresponding bit in this field for a
memory access type is enabled, the access passes the check; otherwise, the access fails to pass the
permission check.


9.4.4.3.5 Permission Check Result Based on Address Translation

The UMMU considers both the relevant access permissions from the MATT acquired in the address
translation process and the permission check information before providing the final check result:

      ⚫    When the permission check related to an MAPTE fails, the UMMU terminates the memory
           access and reports an event related to the permission check;
      ⚫    When the permission check accompanying address translation fails, the UMMU terminates
           the memory access and reports an event related to address translation;
      ⚫    When both checks are passed, the memory access passes the permission check.




unifiedbus.com                                                                                          301
9 Memory Management



9.5 UB Decoder Functions and Processes

9.5.1 PA-to-UBMD Translation Process
The UB decoder takes PAs as its inputs and processes them to obtain the UBMDs identifying remote
memory.

The UB decoder performs PA-to-UBMD translation by looking up the UB decoder page table (page
table for short). The page table includes two levels of data formats: level-0 page table (L0 page table)
and level-1 page table (L1 page table).

An L0 page table may contain the following types of entries:

      ⚫    L0 page table entry (L0 PTE);
      ⚫    L0 page table range entry (L0 PTRE).

Assume the table lookup process entails 44-bit PAs, 8-byte L0 PTEs, and 64-byte L0 PTREs. When
looking up an L0 page table, the UB decoder uses the PA[43:35] as the index to obtain a 64-byte bulk
entry. Based on the bulk entry's Type field, it determines the actual type and performs specific
operations:

      ⚫    If the bulk entry consists of 8 L0 PTEs, the UB decoder uses the PA[34:32] as the index to
           select one L0 PTE (as illustrated in Figure 9-27).
      ⚫    If the bulk entry is an L0 PTRE (as illustrated in Figure 9-28), the UB decoder compares the
           address range included in the L0 PTRE with the PA. If Mem_Base <= PA[34:20] <=
           Mem_Limit, the PA falls within the address range corresponding to the L0 PTRE.




              Figure 9-27 UB decoder translation when an L0 PTE is found in an L0 page table




unifiedbus.com                                                                                         302
9 Memory Management




           Figure 9-28 UB decoder translation when an L0 PTRE is found in an L0 page table

Both the L0 PTE and L0 PTRE contain the base address of the L1 page table. In the following
scenarios, the UB decoder continues to look up the L1 page table.

      ⚫   When the L0 PTE is found in the L0 page table, the UB decoder uses the PA[31:20] to look
          up the L1 page table;
      ⚫   When the L0 PTRE is found in the L0 page table but does not fall into the corresponding
          address range, the UB decoder uses the PA[34:20] to look up the L1 page table.


9.5.2 UBA Calculation
The L0 PTRE or L1 PTE found by using the PA as the index contains the information required to initiate
memory accesses. The UBA is calculated from the UBA_BASE field and PA based on the following rule:

UBA = UBA_BASE:12'b0 + 29'b0:PA[34:0]




unifiedbus.com                                                                                      303
