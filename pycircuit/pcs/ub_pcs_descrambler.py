"""ub_pcs_descrambler — additive inverse of ub_pcs_scrambler (SPEC §2.4; UB-PHY §3.2.3.2).

Same LFSR / ports / latency as the scrambler (XOR is involutive).
"""

from __future__ import annotations

from lib import params as P
from pcs.ub_pcs_scrambler import _emit_scramble_module

MODULE = "ub_pcs_descrambler"


def emit_verilog(
    *,
    data_w: int = P.DATA_W_SCR,
    scr_w: int = P.SCR_W,
    scr_tap: int = P.SCR_TAP,
    lane_id_w: int = P.LANE_ID_W,
) -> str:
    return _emit_scramble_module(
        MODULE, data_w=data_w, scr_w=scr_w, scr_tap=scr_tap, lane_id_w=lane_id_w
    )
