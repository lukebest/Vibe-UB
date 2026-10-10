// TB-only wrapper. Combo DUT + valid-only (SPEC §3.1). Not product RTL.
`timescale 1ns / 1ps

module tb_ub_lane_dedist #(
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
`include "leaf_hook_ports.svh"
);

  ub_pcs_lane_dedist #(
    .NUM_LANES(NUM_LANES),
    .PMA_W(PMA_W),
    .SYM_W(SYM_W)
  ) dut (
    .data_in(data_in),
    .data_out(data_out)
  );

  assign valid_out = rst_n & valid_in;

`include "leaf_hook_body.svh"
endmodule
