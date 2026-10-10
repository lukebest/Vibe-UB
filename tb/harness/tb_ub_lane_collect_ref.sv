// TB-only wrapper around the collect formula reference. Not product RTL.
`timescale 1ns / 1ps

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

  ub_pcs_lane_collect #(
    .NUM_LANES(NUM_LANES),
    .PMA_W(PMA_W),
    .SYM_W(SYM_W)
  ) dut (
    .data_in(data_in),
    .data_mid(data_mid),
    .data_out(data_out)
  );

  assign valid_out = rst_n & valid_in;

endmodule
