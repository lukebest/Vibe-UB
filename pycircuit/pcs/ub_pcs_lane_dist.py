"""ub_pcs_lane_dist — 8-bit FEC symbol stripe across lanes (SPEC §2.4; UB-PHY §3.2.2.3 / §3.2.5).

Combo. ``data_in`` is symbol-major (symbol 0 at LSB). ``data_out`` is
lane-major (lane 0 at LSB, SPEC §3.2.4). ``NUM_LANES`` default 4, parameter
to 8. ``PMA_W`` default 32 (SPEC §9). ``SYM_W`` default 8.

No clock / reset (pure interconnect). No TEST_HOOKS.
"""

from __future__ import annotations

from lib import params as P

MODULE = "ub_pcs_lane_dist"


def emit_verilog(
    *,
    num_lanes: int = P.NUM_LANES_DEFAULT,
    pma_w: int = P.PMA_W,
    sym_w: int = P.SYM_W,
) -> str:
    return _emit_lane(MODULE, dist=True, num_lanes=num_lanes, pma_w=pma_w, sym_w=sym_w)


def _emit_lane(name: str, *, dist: bool, num_lanes: int, pma_w: int, sym_w: int) -> str:
    if pma_w % sym_w != 0:
        raise ValueError("PMA_W must be a multiple of SYM_W")
    if dist:
        assign = """      assign data_out[LANE*PMA_W + POS*SYM_W +: SYM_W] =
             data_in[s*SYM_W +: SYM_W];"""
        comment = "symbol-major in → lane-major out (lane0 LSB)"
    else:
        assign = """      assign data_out[s*SYM_W +: SYM_W] =
             data_in[LANE*PMA_W + POS*SYM_W +: SYM_W];"""
        comment = "lane-major in (lane0 LSB) → symbol-major out"
    return f"""// GENERATED from pycircuit/pcs/{name}.py — do not edit.
// Reproduce: make emit
// SPEC §2.4 / UB-PHY §3.2.2.3 / §3.2.5. TEST_HOOKS=0.
// 8-bit FEC symbols. {comment}. Combo, 0-cycle.

module {name} #(
  parameter integer NUM_LANES = {num_lanes},
  parameter integer PMA_W     = {pma_w},
  parameter integer SYM_W     = {sym_w}
) (
  input  wire [NUM_LANES*PMA_W-1:0] data_in,
  output wire [NUM_LANES*PMA_W-1:0] data_out
);

  localparam integer SYMS_PER_LANE = PMA_W / SYM_W;
  localparam integer NSYM          = NUM_LANES * SYMS_PER_LANE;

  genvar s;
  generate
    for (s = 0; s < NSYM; s = s + 1) begin : g_sym
      localparam integer LANE = s % NUM_LANES;
      localparam integer POS  = s / NUM_LANES;
{assign}
    end
  endgenerate

endmodule
"""
