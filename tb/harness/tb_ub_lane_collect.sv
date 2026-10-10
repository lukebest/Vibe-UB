// TB-only dist→dedist collect. No tb_* (SPEC §10 / Xia).
`timescale 1ns / 1ps

`ifndef UB_DIST_MODULE
`define UB_DIST_MODULE ub_pcs_lane_dist
`endif
`ifndef UB_DEDIST_MODULE
`define UB_DEDIST_MODULE ub_pcs_lane_dedist
`endif

module tb_ub_lane_collect #(
  parameter integer NUM_LANES = 4,
  parameter integer PMA_W     = 32,
  parameter integer SYM_W     = 8
) (
  input  wire                         core_clk,
  input  wire                         rst_n,
  input  wire [NUM_LANES*PMA_W-1:0]   data_in,
  input  wire                         valid_in,
  output wire [NUM_LANES*PMA_W-1:0]   data_mid,
  output wire [NUM_LANES*PMA_W-1:0]   data_out,
  output wire                         valid_out
);

`ifdef UB_LANE_FIXED
  `UB_DIST_MODULE u_dist (
    .data_in(data_in),
    .data_out(data_mid)
  );
  `UB_DEDIST_MODULE u_dedist (
    .data_in(data_mid),
    .data_out(data_out)
  );
`else
  `UB_DIST_MODULE #(
    .NUM_LANES(NUM_LANES),
    .PMA_W(PMA_W),
    .SYM_W(SYM_W)
  ) u_dist (
    .data_in(data_in),
    .data_out(data_mid)
  );
  `UB_DEDIST_MODULE #(
    .NUM_LANES(NUM_LANES),
    .PMA_W(PMA_W),
    .SYM_W(SYM_W)
  ) u_dedist (
    .data_in(data_mid),
    .data_out(data_out)
  );
`endif

  assign valid_out = rst_n & valid_in;

endmodule
