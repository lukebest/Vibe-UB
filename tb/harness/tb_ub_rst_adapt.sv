// TB-only wrapper. Not product RTL. No tb_* (SPEC §10 / Xia).
`timescale 1ns / 1ps

module tb_ub_rst_adapt #(
  parameter integer PYC_RST_ACTIVE_HIGH = 1
) (
  input  wire core_clk,
  input  wire rst_n,
  input  wire rst_n_sync,
  output wire rst_pyc
);

`ifdef UB_RST_FIXED
  // pycc §2.2 netlist: polarity baked in, no Verilog parameter.
  ub_pyc_rst_adapt dut (
    .rst_n_sync(rst_n_sync),
    .rst_pyc(rst_pyc)
  );
`else
  ub_pyc_rst_adapt #(.PYC_RST_ACTIVE_HIGH(PYC_RST_ACTIVE_HIGH)) dut (
    .rst_n_sync(rst_n_sync),
    .rst_pyc(rst_pyc)
  );
`endif

endmodule
