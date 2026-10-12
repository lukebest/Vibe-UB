// HOOKS-only walker auxiliaries (#55). Never assumed, never on PRODUCT.
// PRODUCT relies on PRODUCT ≡ HOOKS (obs ports are HOOKS-only outputs).
//
// Encoding table lives ONLY in SPEC §10 (UARCH §10 references it).
// #50 has not landed the table yet; values are the designer's #48
// posting (same as tb/mem/ub_mem_ptw_smoke_tb.v). One mapping
// block; properties use the names.
//
// State invariants read only tb_mem_ptw_obs_st /
// tb_mem_ptw_obs_rd_pend. Consistency asserts also use PRODUCT
// handshake ports. No decoder internals.

module ub_mem_ptw_hooks_inv (
  input  wire        core_clk,
  input  wire        rst_pyc,
  input  wire [5:0]  tb_mem_ptw_obs_st,
  input  wire        tb_mem_ptw_obs_rd_pend,
  input  wire        mem2host_rd_rsp_ready,
  input  wire        mem2host_rd_valid,
  input  wire        req_ready,
  input  wire        fill_valid,
  input  wire        flt_valid,
  input  wire        evt_valid
);

  // SPEC §10 walker obs_st encodings (cite SPEC §10; values from #48
  // until #50 writes the table). Pack is
  // {st_evt, st_flt, st_fill, st_dec, st_rd, st_idle}.
  localparam integer ST_W         = 6;
  localparam [5:0]   ST_IDLE      = 6'b000001;
  localparam [5:0]   ST_RD        = 6'b000010;  // table-read
  localparam [5:0]   ST_DEC       = 6'b000100;
  localparam [5:0]   ST_FILL      = 6'b001000;
  localparam [5:0]   ST_FLT       = 6'b010000;
  localparam [5:0]   ST_EVT       = 6'b100000;

  wire chk = !rst_pyc;

  // #48 98818fc: walker returns to a legal encoding for any decode
  // result. These stay asserts-only on the free cut.
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
      // (c) rd_valid_q and rd_sent are mutex in RTL (enter_rd sets
      // valid / clears sent; rd_accept clears valid / sets sent).
      // rsp_ready = st_rd & rd_sent (PRODUCT port). Induction CEX
      // started with both rd_pend and rsp_ready, then took an error
      // response into ST_FLT while holding rd_pend.
      a_rd_pend_mutex: assert (
        !tb_mem_ptw_obs_rd_pend || !mem2host_rd_rsp_ready
      );

      // obs_st is the one-hot pack of the same bits that drive the
      // PRODUCT handshake valids. Ties if_props trackers (f_matt_pend
      // → evt_valid, f_rd_outst → rsp_ready, …) to walker state.
      a_obs_rd_pend_eq: assert (tb_mem_ptw_obs_rd_pend == mem2host_rd_valid);
      a_obs_idle: assert ((tb_mem_ptw_obs_st == ST_IDLE) == req_ready);
      a_obs_fill: assert ((tb_mem_ptw_obs_st == ST_FILL) == fill_valid);
      a_obs_flt:  assert ((tb_mem_ptw_obs_st == ST_FLT)  == flt_valid);
      a_obs_evt:  assert ((tb_mem_ptw_obs_st == ST_EVT)  == evt_valid);
      a_obs_rd: assert (
        (tb_mem_ptw_obs_st != ST_RD) ||
        (!req_ready && !fill_valid && !flt_valid && !evt_valid)
      );
      a_obs_dec: assert (
        (tb_mem_ptw_obs_st != ST_DEC) ||
        (!req_ready && !fill_valid && !flt_valid && !evt_valid &&
         !tb_mem_ptw_obs_rd_pend && !mem2host_rd_rsp_ready)
      );
      a_obs_rsp_rd: assert (
        !mem2host_rd_rsp_ready || (tb_mem_ptw_obs_st == ST_RD)
      );
    end
  end

  // Observable catch-all: ST_DEC → ST_FLT → ST_IDLE with no fill
  // (covers desc_v=1 & kind=0 and any other free-cut fault).
  wire dec_fire = chk && (tb_mem_ptw_obs_st == ST_DEC);

  reg f_dec;
  reg f_dec_flt;
  reg f_dec_fill;

  initial begin
    f_dec      = 1'b0;
    f_dec_flt  = 1'b0;
    f_dec_fill = 1'b0;
  end

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      f_dec      <= 1'b0;
      f_dec_flt  <= 1'b0;
      f_dec_fill <= 1'b0;
    end else if (dec_fire) begin
      f_dec      <= 1'b1;
      f_dec_flt  <= 1'b0;
      f_dec_fill <= 1'b0;
    end else if (f_dec) begin
      if (tb_mem_ptw_obs_st == ST_FLT)
        f_dec_flt <= 1'b1;
      if (fill_valid)
        f_dec_fill <= 1'b1;
    end
  end

  always @(posedge core_clk) begin
    c_kind0_flt_idle: cover (
      chk && f_dec && f_dec_flt &&
      (tb_mem_ptw_obs_st == ST_IDLE) &&
      !f_dec_fill && !fill_valid
    );
  end

endmodule
