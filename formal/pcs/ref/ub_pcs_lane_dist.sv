// Verification formula reference. Not product RTL.
// SPEC §2.3 / §2.4 (UB-PHY §3.2.2.3): Lane<j,i> = CA<(NSYM-1)-i*N-j>
// Symbol 0 at LSB of the CA window and of each PMA word (SPEC §3.3).
// Combo, 0-cycle. Do not copy pycircuit/ or rtl/.
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
  localparam integer NSYM = NUM_LANES * SPL;

  genvar i, j;
  generate
    for (i = 0; i < SPL; i = i + 1) begin : g_i
      for (j = 0; j < NUM_LANES; j = j + 1) begin : g_j
        localparam integer SRC = (NSYM - 1) - i * NUM_LANES - j;
        assign data_out[j*PMA_W + i*SYM_W +: SYM_W] =
            data_in[SRC*SYM_W +: SYM_W];
      end
    end
  endgenerate

endmodule
