// UVM Test: Basic loopback transmission test
`ifndef UB_TP_TEST_SV
`define UB_TP_TEST_SV

import uvm_pkg::*;
`include "uvm_macros.svh"

class ub_tp_loopback_test extends uvm_test;
  `uvm_component_utils(ub_tp_loopback_test)

  ub_tp_env             env;
  virtual ub_tp_intf    intf;

  integer error_count;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    env = ub_tp_env::type_id::create("env", this);
    if (!uvm_config_db#(virtual ub_tp_intf)::get(this, "", "intf", intf)) begin
      `uvm_fatal("TEST", "Failed to get interface from config db")
    end
    uvm_config_db#(virtual ub_tp_intf)::set(this, "env*", "intf", intf);
    error_count = 0;
  endfunction

  virtual task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    `uvm_info("TEST", "Starting loopback test", UVM_MEDIUM)

    // Initialize DUT inputs
    intf.ta_data    = 160'h0;
    intf.ta_valid   = 1'b0;
    intf.ta_sop     = 1'b0;
    intf.ta_eop     = 1'b0;
    intf.tp_rx_ready = 1'b1;

    // Wait for reset release
    repeat(4) @(posedge intf.clk);

    `uvm_info("TEST", "Sending test packet", UVM_MEDIUM)

    // Send test packet
    @(posedge intf.clk);
    intf.ta_data  = 160'h123456789ABCDEF0123456789ABCDEF;
    intf.ta_sop   = 1'b1;
    intf.ta_eop   = 1'b1;
    intf.ta_valid = 1'b1;

    @(posedge intf.clk);
    while (!intf.ta_ready) @(posedge intf.clk);
    intf.ta_valid = 1'b0;
    intf.ta_sop   = 1'b0;
    intf.ta_eop   = 1'b0;

    // Wait for reception with timeout
    fork
      begin
        wait(intf.tp_rx_valid);
        `uvm_info("TEST", $sformatf("Received packet: %h", intf.tp_rx_data), UVM_MEDIUM)
        // Check data - bits [71:24] should match
        if (intf.tp_rx_data[71:24] != 48'hef0123456789) begin
          `uvm_error("TEST", $sformatf("Data mismatch! Expected 48'hef0123456789, got %h", intf.tp_rx_data[71:24]))
          error_count++;
        end
        else begin
          `uvm_info("TEST", "Data check PASSED", UVM_MEDIUM)
        end
      end
      begin
        repeat(100) @(posedge intf.clk);
        `uvm_error("TEST", "Timeout waiting for packet reception")
        error_count++;
      end
    join_any

    // Wait a bit then finish
    repeat(20) @(posedge intf.clk);

    if (error_count == 0) begin
      `uvm_info("TEST", "*** TEST PASSED ***", UVM_MEDIUM)
    end
    else begin
      `uvm_error("TEST", $sformatf("*** TEST FAILED with %0d errors ***", error_count))
    end

    phase.drop_objection(this);
  endtask

endclass

`endif // UB_TP_TEST_SV
