// HOOKS-only walker auxiliaries (#55). Never assumed, never on PRODUCT.
// PRODUCT relies on PRODUCT ≡ HOOKS (obs ports are HOOKS-only outputs).
//
// Encoding table lives ONLY in SPEC §10 (UARCH §10 references it).
// #50 has not landed the table yet; values are the designer's #48
// posting (same as tb/mem/ub_mem_ptw_smoke_tb.v). One mapping
// block; properties use the names.
//
// Decoder ports are the public cut outputs (fully free $anyseq).
// Used only by the kind=0 → fault → idle cover.

module ub_mem_ptw_hooks_inv (
  input  wire        core_clk,
  input  wire        rst_pyc,
  input  wire [5:0]  tb_mem_ptw_obs_st,
  input  wire        tb_mem_ptw_obs_rd_pend,
  input  wire        dec_out_valid,
  input  wire        desc_v,
  input  wire [1:0]  desc_kind,
  input  wire        fill_valid
);

  // SPEC §10 walker obs_st encodings (cite SPEC §10; values from #48
  // until #50 writes the table). Pack is
  // {st_evt, st_flt, st_fill, st_dec, st_rd, st_idle}.
  // desc_kind values: contract §2 / params.py.
  localparam integer ST_W         = 6;
  localparam [5:0]   ST_IDLE      = 6'b000001;
  localparam [5:0]   ST_RD        = 6'b000010;  // table-read
  localparam [5:0]   ST_DEC       = 6'b000100;
  localparam [5:0]   ST_FILL      = 6'b001000;
  localparam [5:0]   ST_FLT       = 6'b010000;
  localparam [5:0]   ST_EVT       = 6'b100000;
  localparam [1:0]   KIND_INVALID = 2'd0;

  wire chk = !rst_pyc;

  // #48 98818fc: walker returns to a legal encoding for any decode
  // result. These two stay asserts-only on the free cut.
  always @(posedge core_clk) begin
    if (chk) begin
      // (a) state legal — obs_st is one of the SPEC §10 encodings.
      a_st_legal: assert (
        (tb_mem_ptw_obs_st == ST_IDLE) ||
        (tb_mem_ptw_obs_st == ST_RD)   ||
        (tb_mem_ptw_obs_st == ST_DEC)  ||
        (tb_mem_ptw_obs_st == ST_FILL) ||
        (tb_mem_ptw_obs_st == ST_FLT)  ||
        (tb_mem_ptw_obs_st == ST_EVT)
      );
      // (b) rd_pend implies the table-read encoding.
      a_rd_pend_st: assert (
        !tb_mem_ptw_obs_rd_pend || (tb_mem_ptw_obs_st == ST_RD)
      );
    end
  end

  // Decoder returns desc_v=1 & kind=0 while the walker is in ST_DEC;
  // walker then reaches ST_FLT and ST_IDLE with no fill_* in between.
  wire kind0_fire = chk &&
                    (tb_mem_ptw_obs_st == ST_DEC) &&
                    dec_out_valid &&
                    desc_v &&
                    (desc_kind == KIND_INVALID);

  reg f_kind0;
  reg f_kind0_flt;
  reg f_kind0_fill;

  initial begin
    f_kind0      = 1'b0;
    f_kind0_flt  = 1'b0;
    f_kind0_fill = 1'b0;
  end

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      f_kind0      <= 1'b0;
      f_kind0_flt  <= 1'b0;
      f_kind0_fill <= 1'b0;
    end else if (kind0_fire) begin
      f_kind0      <= 1'b1;
      f_kind0_flt  <= 1'b0;
      f_kind0_fill <= 1'b0;
    end else if (f_kind0) begin
      if (tb_mem_ptw_obs_st == ST_FLT)
        f_kind0_flt <= 1'b1;
      if (fill_valid)
        f_kind0_fill <= 1'b1;
    end
  end

  always @(posedge core_clk) begin
    c_kind0_flt_idle: cover (
      chk && f_kind0 && f_kind0_flt &&
      (tb_mem_ptw_obs_st == ST_IDLE) &&
      !f_kind0_fill && !fill_valid
    );
  end

endmodule
