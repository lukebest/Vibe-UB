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
