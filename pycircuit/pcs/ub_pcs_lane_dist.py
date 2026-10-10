"""ub_pcs_lane_dist — 8-bit FEC symbol distribute (SPEC §2.4; UB-PHY §3.2.2.3 / §3.2.5).

Combo, 0-cycle (SPEC §5). Bit order closed in SPEC §3.3:
  PMA word: symbol 0 in the lowest byte; bit0 of each symbol is LSB.
  Multi-lane pack: lane0 at bus LSB (SPEC §3.2.4).

Mapping (SPEC §2.4 / §2.3 cite UB-PHY §3.2.2.3 CodecNum=1; applied to this
cycle's NSYM-symbol window; SPEC does not copy the table):
  Lane<j,i> = CA<(NSYM-1) - i*NUM_LANES - j>
  i = symbol time on the lane (0 = first-on-wire = LSB of the PMA word)
  j = lane index (0 at bus LSB)

``data_in`` is symbol-major (symbol 0 at LSB). ``data_out`` is lane-major
(lane 0 at LSB). ``NUM_LANES`` default 4 (bring-up; param to 8, SPEC §9).
``PMA_W`` default 32 (SPEC §9). ``SYM_W`` default 8.

dist/dedist are inverses. No clock / reset. No TEST_HOOKS.
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
        assign = """        assign data_out[j*PMA_W + i*SYM_W +: SYM_W] =
               data_in[SRC*SYM_W +: SYM_W];"""
        comment = (
            "UB-PHY §3.2.2.3: Lane<j,i>=CA<(NSYM-1)-i*NUM_LANES-j>; "
            "symbol0 / lane0 at LSB (SPEC §3.3)"
        )
    else:
        assign = """        assign data_out[SRC*SYM_W +: SYM_W] =
               data_in[j*PMA_W + i*SYM_W +: SYM_W];"""
        comment = (
            "inverse of ub_pcs_lane_dist (UB-PHY §3.2.2.3); "
            "symbol0 / lane0 at LSB (SPEC §3.3)"
        )
    return f"""// GENERATED from pycircuit/pcs/{name}.py — do not edit.
// Reproduce: make emit
// SPEC §2.4 / §3.3 / UB-PHY §3.2.2.3 / §3.2.5. TEST_HOOKS=0.
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

  genvar i, j;
  generate
    for (i = 0; i < SYMS_PER_LANE; i = i + 1) begin : g_pos
      for (j = 0; j < NUM_LANES; j = j + 1) begin : g_lane
        localparam integer SRC = (NSYM - 1) - i * NUM_LANES - j;
{assign}
      end
    end
  endgenerate

endmodule
"""
