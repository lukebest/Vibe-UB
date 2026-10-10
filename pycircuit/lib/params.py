"""M1 leaf identifiers. Only SPEC-closed values live here (SPEC §9 / §2.4 / §2.6).

OPEN items (PRBS23 taps, AMCTL.LID→seed map, LFSR power-on init) have
**no** product default in this file. Parent / selfcheck / lint must pass
them explicitly. See SPEC §13.2.
"""

from __future__ import annotations

# SPEC §9
PMA_W = 32
FLIT_W = 160
NUM_LANES_DEFAULT = 4  # bring-up target; RTL parameter to 8 (SPEC §9)
NUM_LANES_MAX = 8
PRECODE_EN = 0  # SPEC §9; PMA, not this batch
TEST_HOOKS = 0  # PRODUCT default; HOOKS emit uses test_hooks=True (SPEC §10: no ports)
F_CORE_HZ = 80_570_000  # ≈ 2.578125e9 / 32; SPEC §4.1 / §9

# PCS 8-bit stripe (SPEC §2.4 cites UB-PHY §3.2.2.3 Lane<j,i>=CA<(N-1)-i*LaneNum-j>; bit order SPEC §3.3)
SYM_W = 8

# Scrambler — closed widths only (SPEC §2.4 / §9)
SCR_W = 23
DATA_W_SCR = PMA_W  # per-lane instance; SPEC §2.4 / §9
AMCTL_LID_W = 4  # SPEC §2.4: 0–7 Lane0–7, 8=NULL, 9–15 reserved
SEED_MAP_SLOTS = 9  # lid 0..8 inclusive

# BCRC — closed by SPEC §2.6 / §9 / UB-DL §4.3.2.2.4 / §4.7.2
BCRC_W = 30
BCRC_POLY = 0x15A94AD5  # x^30 implicit; SPEC §2.6 / §9
BCRC_INIT = (1 << BCRC_W) - 1  # all-ones; SPEC §2.6
BCRC_WORD_W = 32
BCRC_BYTES = BCRC_WORD_W // 8  # last-flit field; not in the CRC (SPEC §2.6)
# TX ERROR_FLAG constant 0 (SPEC §7: no ECC, no nw_tx_err)
