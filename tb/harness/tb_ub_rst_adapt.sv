// TB-only wrapper. Not product RTL.
`timescale 1ns / 1ps

module tb_ub_rst_adapt #(
  parameter integer PYC_RST_ACTIVE_HIGH = 1
) (
  input  wire core_clk,
  input  wire rst_n,
  input  wire rst_n_sync,
  output wire rst_pyc
`include "leaf_hook_ports.svh"
);

  ub_pyc_rst_adapt #(.PYC_RST_ACTIVE_HIGH(PYC_RST_ACTIVE_HIGH)) dut (
    .rst_n_sync(rst_n_sync),
    .rst_pyc(rst_pyc)
  );

`include "leaf_hook_body.svh"
endmodule
