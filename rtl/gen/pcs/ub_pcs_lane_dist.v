// GENERATED from pycircuit/pcs/ub_pcs_lane_dist.py — do not edit.
// Reproduce: make emit
// SPEC §2.4 / UB-PHY §3.2.2.3 / §3.2.5. TEST_HOOKS=0.
// 8-bit FEC symbols. symbol-major in → lane-major out (lane0 LSB). Combo, 0-cycle.

module ub_pcs_lane_dist #(
  parameter integer NUM_LANES = 4,
  parameter integer PMA_W     = 32,
  parameter integer SYM_W     = 8
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
      assign data_out[LANE*PMA_W + POS*SYM_W +: SYM_W] =
             data_in[s*SYM_W +: SYM_W];
    end
  endgenerate

endmodule
