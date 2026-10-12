// Auxiliary walker-register invariants for k-induction.
// Assertions only — never assumed, never restrict design inputs.
// Sound (BMC-proven): one-hot FSM, registered len/tag constants,
// table-read request lives only in st_rd. Hierarchical refs to
// PRODUCT-instance registers (not desc_dec, no private bit-layout).
// Names RD_LEN_8B / RD_TAG_ZERO match the if_props mapping block.

module ub_mem_ptw_inv (
  input  wire       core_clk,
  input  wire       rst_pyc,
  input  wire       st_idle,
  input  wire       st_rd,
  input  wire       st_dec,
  input  wire       st_fill,
  input  wire       st_flt,
  input  wire       st_evt,
  input  wire       rd_valid_q,
  input  wire [7:0] rd_len_q,
  input  wire [3:0] rd_tag_q
);

  localparam integer RD_LEN_8B   = 8;
  localparam integer RD_TAG_ZERO = 0;

  wire chk = !rst_pyc;
  wire [2:0] st_sum = {2'b0, st_idle} + {2'b0, st_rd} + {2'b0, st_dec}
                    + {2'b0, st_fill} + {2'b0, st_flt} + {2'b0, st_evt};

  always @(posedge core_clk) begin
    if (chk) begin
      a_st_onehot:      assert (st_sum == 3'd1);
      a_rd_len_const:   assert (rd_len_q == RD_LEN_8B[7:0]);
      a_rd_tag_const:   assert (rd_tag_q == RD_TAG_ZERO[3:0]);
      a_rd_valid_in_rd: assert (!rd_valid_q || st_rd);
    end
  end

endmodule
