"""M1 leaf defaults. SPEC §9 identifiers kept as UPPER_SNAKE.

Values that the in-repo SPEC does not pin (polynomial, seed, BCRC width)
are parameters. Defaults follow lukebest/Vibe-UB-Switch (D9) and are listed
under Open questions for Xia — they are not invented as closed SPEC text.
"""

from __future__ import annotations

# SPEC §9
PMA_W = 32
FLIT_W = 160
NUM_LANES_DEFAULT = 4
NUM_LANES_MAX = 8
PRECODE_EN = 0
TEST_HOOKS = 0
F_CORE_HZ = 80_570_000  # ≈ 2.578125e9 / 32

# PCS symbol stripe (SPEC §2.4, UB-PHY §3.2.2.3)
SYM_W = 8

# Scrambler (UB-PHY §3.2.2.4). Default algorithm from Vibe-UB-Switch.
# DATA_W default = PMA_W (per-lane word after 8-bit dist). Not pinned in SPEC.
SCR_W = 23
SCR_TAP = 17  # feedback s[SCR_W-1] ^ s[SCR_TAP]  → x^23 + x^18 + 1
LANE_ID_W = 3  # parameterized to x8
DATA_W_SCR = PMA_W

# BCRC (UB-DL §4.3.2.2). Default CRC30 from Vibe-UB-Switch AS-0.1 §12.
# x^30+x^28+x^26+x^24+x^23+x^21+x^19+x^16+x^14+x^11+x^9+x^7+x^6+x^4+x^2+1
BCRC_W = 30
BCRC_POLY = 0x15A94AD5
BCRC_INIT = (1 << BCRC_W) - 1
BCRC_WORD_W = 32
