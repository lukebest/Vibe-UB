// SPEC §2.4 / UB-PHY §3.2.2.3 local pre-check (not pycc; non-gating).
// Lane<j,i> = CA<(NSYM-1) - i*NUM_LANES - j>
// symbol 0 / lane 0 at LSB (SPEC §3.3). Combo, 0-cycle.
module ub_pcs_lane_dist_spec #(
  parameter integer NUM_LANES = 4,
  parameter integer PMA_W     = 32,
  parameter integer SYM_W     = 8
) (
  input  [NUM_LANES*PMA_W-1:0] data_in,
  output [NUM_LANES*PMA_W-1:0] data_out
);
  localparam integer SYMS_PER_LANE = PMA_W / SYM_W;
  localparam integer NSYM          = NUM_LANES * SYMS_PER_LANE;
  genvar i, j;
  generate
    for (i = 0; i < SYMS_PER_LANE; i = i + 1) begin : g_pos
      for (j = 0; j < NUM_LANES; j = j + 1) begin : g_lane
        localparam integer SRC = (NSYM - 1) - i * NUM_LANES - j;
        assign data_out[j*PMA_W + i*SYM_W +: SYM_W] =
               data_in[SRC*SYM_W +: SYM_W];
      end
    end
  endgenerate
endmodule
