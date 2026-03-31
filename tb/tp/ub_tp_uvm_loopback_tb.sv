// Top-level UVM Testbench for TP Loopback
// Uses harness structure, all signals/modules visible in Verdi

`timescale 1ns/1ps

module ub_tp_uvm_loopback_tb;

  import uvm_pkg::*;
  `include "uvm_macros.svh"

  // Clock and reset
  reg clk;
  reg rst_n;

  // Interface
  ub_tp_intf intf(
    .clk(clk),
    .rst_n(rst_n)
  );

  // DUT Wrapper (Harness)
  ub_tp_dut_wrap dut_wrap(
    .clk(clk),
    .rst_n(rst_n),
    .intf(intf)
  );

  // Clock generation
  initial begin
    clk = 0;
    forever #5 clk = ~clk;
  end

  // Initialize reset
  initial begin
    rst_n = 0;
    #20 rst_n = 1;
  end

  // Dump waves for Verdi
  initial begin
    $dumpfile("ub_tp_uvm_loopback_tb.vcd");
    $dumpvars(0, ub_tp_uvm_loopback_tb);
  end

  // Start UVM
  initial begin
    // Pass interface to UVM config db
    uvm_config_db#(virtual ub_tp_intf)::set(null, "*", "intf", intf);
    run_test();
  end

endmodule
