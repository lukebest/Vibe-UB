// Spec-gold for Yosys equiv only (not a product DUT).
// Same formula as tb/models UbPcsLaneDist and the pyCircuit leaf:
//   Lane<j,i> = CA<(NSYM-1) - i*NUM_LANES - j>
// CA[0] / Lane0 / slot0 at LSB.

module ub_pcs_lane_dist_spec #(
  parameter integer NUM_LANES = 4,
  parameter integer PMA_W     = 32,
  parameter integer SYM_W     = 8
) (
  input  wire [NUM_LANES*PMA_W-1:0] data_in,
  output wire [NUM_LANES*PMA_W-1:0] data_out
);

  localparam integer SYMS_PER_LANE = PMA_W / SYM_W;
  localparam integer NSYM          = NUM_LANES * SYMS_PER_LANE;

  genvar j, i;
  generate
    for (j = 0; j < NUM_LANES; j = j + 1) begin : g_lane
      for (i = 0; i < SYMS_PER_LANE; i = i + 1) begin : g_sym
        localparam integer CA = (NSYM - 1) - i * NUM_LANES - j;
        assign data_out[j*PMA_W + i*SYM_W +: SYM_W] =
               data_in[CA*SYM_W +: SYM_W];
      end
    end
  endgenerate

endmodule
