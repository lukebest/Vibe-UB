"""ub_pcs_descrambler — same additive PRBS23 as ub_pcs_scrambler (SPEC §2.4; UB-PHY §3.2.3.2).

TX and RX rules are identical. OPEN taps / seed map / LFSR_INIT: see
``ub_pcs_scrambler`` — parent / selfcheck must pass them.
"""

from __future__ import annotations

from lib import params as P
from pcs.ub_pcs_scrambler import _emit_scramble_module

MODULE = "ub_pcs_descrambler"


def emit_verilog(
    *,
    data_w: int = P.DATA_W_SCR,
    scr_w: int = P.SCR_W,
    amctl_lid_w: int = P.AMCTL_LID_W,
    seed_slots: int = P.SEED_MAP_SLOTS,
) -> str:
    return _emit_scramble_module(
        MODULE,
        data_w=data_w,
        scr_w=scr_w,
        amctl_lid_w=amctl_lid_w,
        seed_slots=seed_slots,
    )
