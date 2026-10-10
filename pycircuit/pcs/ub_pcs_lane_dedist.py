"""ub_pcs_lane_dedist — inverse of ub_pcs_lane_dist (SPEC §2.4).

Real pyCircuit API. Combo, 0-cycle.
Fixed variants (SPEC §2.2): ub_pcs_lane_dedist_x4, ub_pcs_lane_dedist_x8.
"""

from __future__ import annotations

from pycircuit import Circuit, module

from lib import params as P

LEAF = "ub_pcs_lane_dedist"
VARIANTS: dict[str, dict] = {
    "x4": {"num_lanes": 4, "pma_w": P.PMA_W, "sym_w": P.SYM_W},
    "x8": {"num_lanes": 8, "pma_w": P.PMA_W, "sym_w": P.SYM_W},
}


def _unstripe(m: Circuit, data_in, *, num_lanes: int, pma_w: int, sym_w: int):
    """Recover symbol-major data_out. m.cat is MSB-first."""
    syms_per_lane = pma_w // sym_w
    nsym = num_lanes * syms_per_lane
    pieces = []
    for src in range(nsym - 1, -1, -1):
        k = (nsym - 1) - src
        i = k // num_lanes
        j = k % num_lanes
        pieces.append(data_in.slice(lsb=j * pma_w + i * sym_w, width=sym_w))
    return m.cat(*pieces)


@module(name="ub_pcs_lane_dedist")
def build(
    m: Circuit,
    num_lanes: int = 4,
    pma_w: int = 32,
    sym_w: int = 8,
    test_hooks: int = 0,
) -> None:
    _ = int(test_hooks)
    num_lanes = int(num_lanes)
    pma_w = int(pma_w)
    sym_w = int(sym_w)
    nsym = num_lanes * (pma_w // sym_w)
    data_in = m.input("data_in", width=nsym * sym_w)
    m.output(
        "data_out",
        _unstripe(m, data_in, num_lanes=num_lanes, pma_w=pma_w, sym_w=sym_w),
    )


build.__pycircuit_name__ = "ub_pcs_lane_dedist"
