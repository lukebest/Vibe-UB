"""Public project constants for PCS leaves. No spec codeword table."""

from __future__ import annotations

# SPEC §4.1 / §9
PMA_W = 32
NUM_LANES_RX = 8
FLIT_W = 160
SYM_W = 8
AMCTL_SYMS = 40
AMCTL_WORDS = AMCTL_SYMS // (PMA_W // SYM_W)  # 10

# SPEC §2.4: 0–7 = Lane0–Lane7; 8 = NULL
LID_W = 4
LID_NULL = 8

# docs/arch/pcs/contracts/ub_pcs_amctl_cw_dec.md §4 — project enums
CTRL_TYPE_W = 3
CTRL_FEC_CTRL = 0
CTRL_LW_SWITCH = 1
CTRL_EI = 2
CTRL_PERIOD_CTRL = 3
CTRL_REMOTE_LW_SWITCH = 4
CTRL_RSVD = 5
CTRL_NO_CMD = 6

CTRL_DETAIL_W = 4
DET_X0 = 0
DET_X1 = 1
DET_X2 = 2
DET_X4 = 3
DET_X8 = 4
DET_EEI = 5
DET_PERIOD0 = 6
DET_PERIOD1 = 7
DET_OPEN_FEC = 8
DET_CLOSE_FEC = 9
DET_RSVD = 10
DET_NO_CMD = 11

# Null Block field positions: public SPEC does not give bit indexes.
# CLENGTH width and zero-value are public (MODULE_INVENTORY / Xia 2026-10-12).
# LSB / block-type code are 未知 — parameters, listed as spec questions.
CLENGTH_W = 5
CLENGTH_NULL = 0
BLK_TYPE_W = 4
# Placeholders until Xia writes public bit indexes. Do not treat as spec values.
BLK_TYPE_LSB = 0
CLENGTH_LSB = 4
NULL_BLK_CODE = 0
