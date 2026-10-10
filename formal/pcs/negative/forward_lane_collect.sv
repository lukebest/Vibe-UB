// Negative fixture only: collect data_out is a rotate, not dist∘dedist identity.
// Used to prove scripts/gate/equiv_ref.sh returns non-zero.
// Not a reference. Not product RTL.
`timescale 1ns / 1ps

module ub_pcs_lane_collect #(
  parameter integer NUM_LANES = 4,
  parameter integer PMA_W     = 32,
  parameter integer SYM_W     = 8
) (
  input  wire [NUM_LANES*PMA_W-1:0] data_in,
  output wire [NUM_LANES*PMA_W-1:0] data_mid,
  output wire [NUM_LANES*PMA_W-1:0] data_out
);

  localparam integer W = NUM_LANES * PMA_W;
  assign data_mid = data_in;
  assign data_out = {data_in[7:0], data_in[W-1:8]};

endmodule
