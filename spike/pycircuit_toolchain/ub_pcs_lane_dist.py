"""ub_pcs_lane_dist — combinational 8-bit FEC stripe (UB-PHY §3.2.2.3).

Real pyCircuit API (pyc4.0 / lukebest/pyCircuit@43cc5918). No f-string Verilog.

Mapping (CA[0] = lowest byte of data_in; lane0 at data_out LSB; slot 0 at lane LSB):
    Lane<j,i> = CA<(NSYM-1) - i*NUM_LANES - j>
    NSYM = NUM_LANES * (PMA_W / SYM_W)

JIT params elaborate fixed-width variants. pycc does not emit Verilog parameters.

Loops / ``m.cat(*list)`` live in a plain helper (Vibe-UB-Switch style). The
@module JIT forbids ``range(..., -1, -1)``, starred args, and ``x in ...``
(pinned ``jit.py`` PYC520 / undefined ``Vec``).
"""

from __future__ import annotations

from pycircuit import Circuit, module


def _stripe(m: Circuit, data_in, *, num_lanes: int, pma_w: int, sym_w: int):
    """Assemble data_out. ``m.cat`` is MSB-first."""
    syms_per_lane = pma_w // sym_w
    nsym = num_lanes * syms_per_lane
    pieces = []
    for j in range(num_lanes - 1, -1, -1):
        for i in range(syms_per_lane - 1, -1, -1):
            ca = (nsym - 1) - i * num_lanes - j
            pieces.append(data_in.slice(lsb=ca * sym_w, width=sym_w))
    return m.cat(*pieces)


@module(name="ub_pcs_lane_dist")
def build(
    m: Circuit,
    num_lanes: int = 4,
    pma_w: int = 32,
    sym_w: int = 8,
    test_hooks: int = 0,
) -> None:
    """Elaboration-time NUM_LANES / PMA_W / SYM_W / TEST_HOOKS.

    ``test_hooks`` is a JIT int (generate-time switch). A true Verilog
    ``parameter TEST_HOOKS`` is not emitted; pass ``--param test_hooks=1``
    to elaborate a different netlist. This leaf has no hook ports.
    """
    if int(pma_w) % int(sym_w) != 0:
        raise ValueError("PMA_W must be a multiple of SYM_W")
    num_lanes = int(num_lanes)
    pma_w = int(pma_w)
    sym_w = int(sym_w)
    test_hooks = int(test_hooks)
    # Avoid `x in ...` inside @module: pinned jit.py:1157 names undefined `Vec`
    # and raises PYC520. Compare against 0/1 instead.
    if test_hooks != 0 and test_hooks != 1:
        raise ValueError("test_hooks must be 0 or 1")
    if test_hooks != 0:
        raise ValueError("ub_pcs_lane_dist has no TEST_HOOKS ports")

    nsym = num_lanes * (pma_w // sym_w)
    data_in = m.input("data_in", width=nsym * sym_w)
    m.output(
        "data_out",
        _stripe(m, data_in, num_lanes=num_lanes, pma_w=pma_w, sym_w=sym_w),
    )


build.__pycircuit_name__ = "ub_pcs_lane_dist"
