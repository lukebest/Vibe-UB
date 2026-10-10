// Verification formula reference. Not product RTL.
// SPEC §4.2: rst_n_sync (low) -> rst_pyc at pyc_reg native polarity.
// PYC_RST_ACTIVE_HIGH=1: invert. =0: wire. Combo, 0-cycle.
// Do not copy pycircuit/ or rtl/.
`timescale 1ns / 1ps

module ub_pyc_rst_adapt #(
  parameter integer PYC_RST_ACTIVE_HIGH = 1
) (
  input  wire rst_n_sync,
  output wire rst_pyc
);

  assign rst_pyc = PYC_RST_ACTIVE_HIGH ? ~rst_n_sync : rst_n_sync;

endmodule
