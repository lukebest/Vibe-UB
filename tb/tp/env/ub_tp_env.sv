// UVM Environment for TP Loopback Test
`ifndef UB_TP_ENV_SV
`define UB_TP_ENV_SV

import uvm_pkg::*;
`include "uvm_macros.svh"

class ub_tp_env extends uvm_env;
  `uvm_component_utils(ub_tp_env)

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    `uvm_info("ENV", "Build phase completed", UVM_MEDIUM)
  endfunction

  virtual function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
  endfunction

endclass

`endif // UB_TP_ENV_SV
