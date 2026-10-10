// Verification formula reference. Not product RTL.
// SPEC §2.3 / §2.4 composition: dist then dedist. No PRODUCT collect leaf.
// Combo, 0-cycle. Do not copy pycircuit/ or rtl/.
`timescale 1ns / 1ps

module ub_pcs_lane_collect #(
  parameter integer NUM_LANES = 4,
  parameter integer PMA_W     = 32,
  parameter integer SYM_W     = 8
) (
  input  wire [NUM_LANES*PMA_W-1:0] data_in,
  output wire [NUM_LANES*PMA_W-1:0] data_mid,
  output wire [NUM_LANES*PMA_W-1:0] data_out
);

  ub_pcs_lane_dist #(
    .NUM_LANES(NUM_LANES),
    .PMA_W(PMA_W),
    .SYM_W(SYM_W)
  ) u_dist (
    .data_in(data_in),
    .data_out(data_mid)
  );

  ub_pcs_lane_dedist #(
    .NUM_LANES(NUM_LANES),
    .PMA_W(PMA_W),
    .SYM_W(SYM_W)
  ) u_dedist (
    .data_in(data_mid),
    .data_out(data_out)
  );

endmodule
