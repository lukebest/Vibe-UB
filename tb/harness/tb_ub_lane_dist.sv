// TB-only wrapper. Combo DUT + valid-only (SPEC §3.1). No tb_* (SPEC §10 / Xia).
// SPEC §2.2: instantiate ub_pcs_lane_dist_xN when that netlist exists; else parameterized.
`timescale 1ns / 1ps

`ifndef UB_DIST_MODULE
`define UB_DIST_MODULE ub_pcs_lane_dist
`endif

module tb_ub_lane_dist #(
  parameter integer NUM_LANES = 4,
  parameter integer PMA_W     = 32,
  parameter integer SYM_W     = 8
) (
  input  wire                         core_clk,
  input  wire                         rst_n,
  input  wire [NUM_LANES*PMA_W-1:0]   data_in,
  input  wire                         valid_in,
  output wire [NUM_LANES*PMA_W-1:0]   data_out,
  output wire                         valid_out
);

`ifdef UB_LANE_FIXED
  `UB_DIST_MODULE dut (
    .data_in(data_in),
    .data_out(data_out)
  );
`else
  `UB_DIST_MODULE #(
    .NUM_LANES(NUM_LANES),
    .PMA_W(PMA_W),
    .SYM_W(SYM_W)
  ) dut (
    .data_in(data_in),
    .data_out(data_out)
  );
`endif

  assign valid_out = rst_n & valid_in;

endmodule
