// GENERATED from pycircuit/pcs/ub_pcs_lane_dedist.py — do not edit.
// Reproduce: make emit
// SPEC §2.4 / §3.3 / UB-PHY §3.2.2.3 / §3.2.5. TEST_HOOKS=1
// (SPEC §10 lists no hook ports on this leaf).
// 8-bit FEC symbols. inverse of ub_pcs_lane_dist (UB-PHY §3.2.2.3); symbol0 / lane0 at LSB (SPEC §3.3). Combo, 0-cycle.

module ub_pcs_lane_dedist #(
  parameter integer NUM_LANES = 4,
  parameter integer PMA_W     = 32,
  parameter integer SYM_W     = 8
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
        assign data_out[SRC*SYM_W +: SYM_W] =
               data_in[j*PMA_W + i*SYM_W +: SYM_W];
      end
    end
  endgenerate

endmodule
