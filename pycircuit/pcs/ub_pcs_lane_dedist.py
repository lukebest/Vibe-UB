"""ub_pcs_lane_dedist — inverse of ub_pcs_lane_dist (SPEC §2.4; UB-PHY §3.2.2.3 / §3.2.5)."""

from __future__ import annotations

from lib import params as P
from pcs.ub_pcs_lane_dist import _emit_lane

MODULE = "ub_pcs_lane_dedist"


def emit_verilog(
    *,
    num_lanes: int = P.NUM_LANES_DEFAULT,
    pma_w: int = P.PMA_W,
    sym_w: int = P.SYM_W,
) -> str:
    return _emit_lane(MODULE, dist=False, num_lanes=num_lanes, pma_w=pma_w, sym_w=sym_w)
