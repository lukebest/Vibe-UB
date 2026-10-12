// Negative fixture only: Lane<j,i> = CA<i*N+j> (not SPEC).
// Used to prove scripts/gate/equiv_ref.sh returns non-zero.
// Not a reference. Not product RTL.
`timescale 1ns / 1ps

module ub_pcs_lane_dist #(
  parameter integer NUM_LANES = 4,
  parameter integer PMA_W     = 32,
  parameter integer SYM_W     = 8
) (
  input  wire [NUM_LANES*PMA_W-1:0] data_in,
  output wire [NUM_LANES*PMA_W-1:0] data_out
);

  localparam integer SPL  = PMA_W / SYM_W;

  genvar i, j;
  generate
    for (i = 0; i < SPL; i = i + 1) begin : g_i
      for (j = 0; j < NUM_LANES; j = j + 1) begin : g_j
        localparam integer SRC = i * NUM_LANES + j;
        assign data_out[j*PMA_W + i*SYM_W +: SYM_W] =
            data_in[SRC*SYM_W +: SYM_W];
      end
    end
  endgenerate

endmodule
