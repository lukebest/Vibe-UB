"""Shared compile-time widths for C-line structure leaves.

Named-signal widths follow docs/arch/mem/UARCH.md §4 / §5 / §10.
These are structure-leaf pack widths, not table-entry field layouts.
"""

from __future__ import annotations

# Default parameter set (SPEC §2.2: one fixed netlist, module name = leaf).
TLB_SETS = 64
TLB_WAYS = 4
SET_W = 6  # clog2(64)

ENT_IDX_W = 4
TOKEN_W = 20
PAGE_W = 36
TAG_W = ENT_IDX_W + TOKEN_W + PAGE_W  # 60

PFN_W = 36
ATTR_W = 8
AP_W = 2
DATA_W = PFN_W + ATTR_W + AP_W + 1 + 1 + 1  # 49: pfn, attr, ap, uxn, pxn, af
WORD_W = TAG_W + DATA_W  # 109

CMD_OP_W = 2
CMD_INV_ALL = 0
CMD_INV_COND = 1
CMD_SYNC = 2

ST_IDLE = 0
ST_FILL_CMP = 1
ST_FILL_WB = 2

INV_ST_IDLE = 0
INV_ST_ALL = 1
INV_ST_SCAN = 2
INV_ST_SYNC = 3
INV_ST_DONE = 4

# Walker / decoder (UARCH §4 / §5.6; contracts/ub_mem_ptw_desc_dec.md).
PA_W = 48
UBA_W = 64
MATT_BA_W = 44
IA_W = 6
RAW_W = 64
RD_DATA_W = 512
# SPEC §14 Q-C07 (D20): 8-bit byte count; legal RD_LEN_8B / 32 / 64.
RD_LEN_W = 8
RD_LEN_8B = 8
RD_LEN_32B = 32
RD_LEN_64B = 64
RD_TAG_W = 4
RD_TAG_ZERO = 0
# 512-bit beat holds eight 8 B descriptors; slot from address low bits.
DESC_SLOT_LSB = 3
DESC_SLOT_W = 3
DESC_ADDR_W = 36
DESC_KIND_W = 2
DESC_LVL_W = 2
ATTR_IDX_W = 3
ILL_CAUSE_W = 4
MATTR_W = 32

LVL_L0 = 0
LVL_L1 = 1
LVL_L2 = 2
LVL_L3 = 3

# desc_kind — contract YAML / README §4 item 4.
KIND_INVALID = 0
KIND_TABLE = 1
KIND_BLOCK = 2
KIND_PAGE = 3

# ill_cause — contracts/README.md §3.
ILL_NONE = 0
ILL_MAP_2MB = 1
ILL_HW_AD = 2
ILL_RSVD = 3
ILL_PTR_OOB = 4
ILL_STALL = 5
ILL_ENDIAN = 6
ILL_MAC = 7
ILL_MAPT_MULTI_BLK = 8
ILL_MAPT_OTHER_BLK = 9
ILL_S2 = 10
ILL_UNSUP = 11

# Walker event path (SPEC §14 Q-A08 (D20)). Code 0 is reserved, never emitted.
EVT_CODE_W = 4
EVT_MATT_WD_MISS = 1

# 4 KB granule walk index in the request address (UARCH §4).
VA_IDX_W = 9
VA_L0_LSB = 39
VA_L1_LSB = 30
VA_L2_LSB = 21
VA_L3_LSB = 12
PAGE_LSB = 12
L1_BLK_OFF_W = 30
L2_BLK_OFF_W = 21
L1_BLK_PAGE_W = L1_BLK_OFF_W - PAGE_LSB  # 18
L2_BLK_PAGE_W = L2_BLK_OFF_W - PAGE_LSB  # 9
DESC_OFF_W = 3
MATT_BA_PAD_W = 4
