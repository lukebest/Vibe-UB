"""Elaboration-only tokens for OPEN SPEC §13 scrambler items.

These are **not** product defaults and **not** authoritative. They exist
so Verilog / Verilator / Yosys / the Python golden can elaborate.

Forbidden to reuse old PR #5 / Switch numbers (tap 17, seed ``2'b01``,
``{prefix=1, lane_id, 2'b01}``). Parent RTL, ``selfcheck.py``, and
``make lint`` / ``make synth`` must pass explicit overrides. Generated
``.v`` syntax stubs are all-zero (not a meaningful PRBS).
"""

from __future__ import annotations

from lib import params as P

# bit 1 only — not tap 17
ELAB_SCR_TAPS = 0x2
# not 2'b01
ELAB_LFSR_INIT = 0x5


def elab_seed_map(
    *,
    scr_w: int = P.SCR_W,
    slots: int = P.SEED_MAP_SLOTS,
) -> int:
    """lid slot k holds (k+3). Not the old {1, lane_id, 2'b01} packing."""
    acc = 0
    for lid in range(slots):
        acc |= (lid + 3) << (scr_w * lid)
    return acc


def seed_map_w(*, scr_w: int = P.SCR_W, slots: int = P.SEED_MAP_SLOTS) -> int:
    return scr_w * slots


def verilator_gflags() -> str:
    bits = seed_map_w()
    sm = elab_seed_map()
    return (
        f"-GSCR_TAPS={P.SCR_W}'h{ELAB_SCR_TAPS:x} "
        f"-GLFSR_INIT={P.SCR_W}'h{ELAB_LFSR_INIT:x} "
        f"-GSEED_MAP={bits}'h{sm:x}"
    )


def yosys_chparam_cmd() -> str:
    bits = seed_map_w()
    sm = elab_seed_map()
    return (
        f"chparam -set SCR_TAPS {P.SCR_W}'h{ELAB_SCR_TAPS:x} "
        f"-set LFSR_INIT {P.SCR_W}'h{ELAB_LFSR_INIT:x} "
        f"-set SEED_MAP {bits}'h{sm:x}"
    )
