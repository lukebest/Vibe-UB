// GENERATED from pycircuit/common/ub_pyc_rst_adapt.py — do not edit.
// Reproduce: make emit
// SPEC §4.2 / CODING_STYLE §2. TEST_HOOKS=0 (no §10 hooks on this leaf).
// pyc_reg native polarity is active-high; invert rst_n_sync → rst_pyc.

module ub_pyc_rst_adapt #(
  parameter integer PYC_RST_ACTIVE_HIGH = 1
) (
  input  wire rst_n_sync,
  output wire rst_pyc
);

  generate
    if (PYC_RST_ACTIVE_HIGH != 0) begin : g_inv
      assign rst_pyc = ~rst_n_sync;
    end else begin : g_wire
      assign rst_pyc = rst_n_sync;
    end
  endgenerate

endmodule
