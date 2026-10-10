// TB-only wrapper. Not product RTL.
`timescale 1ns / 1ps

module tb_ub_rst_sync (
  input  wire core_clk,
  input  wire rst_n,
  output wire rst_n_sync
`include "leaf_hook_ports.svh"
);

  ub_rst_sync dut (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .rst_n_sync(rst_n_sync)
  );

`include "leaf_hook_body.svh"
endmodule
