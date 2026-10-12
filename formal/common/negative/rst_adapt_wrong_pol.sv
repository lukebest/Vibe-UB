// Negative fixture only: polarity inverted vs PYC_RST_ACTIVE_HIGH=1 gold.
// Used to prove scripts/gate/equiv_ref.sh returns non-zero.
// Not a reference. Not product RTL.
`timescale 1ns / 1ps

module ub_pyc_rst_adapt #(
  parameter integer PYC_RST_ACTIVE_HIGH = 1
) (
  input  wire rst_n_sync,
  output wire rst_pyc
);

  // Deliberately wire instead of invert when the gold inverts.
  assign rst_pyc = rst_n_sync;

endmodule
