// HOOKS-only walker auxiliaries (#55). Never assumed, never on PRODUCT.
// PRODUCT relies on PRODUCT ≡ HOOKS (obs ports are HOOKS-only outputs).
//
// Encoding table lives ONLY in SPEC §10 (UARCH §10 references it).
// #50 has not landed the table yet; values are the designer's #48
// a06758a posting (same as tb/mem/ub_mem_ptw_smoke_tb.v). One mapping
// block; properties use the names.

module ub_mem_ptw_hooks_inv (
  input  wire        core_clk,
  input  wire        rst_pyc,
  input  wire [5:0]  tb_mem_ptw_obs_st,
  input  wire        tb_mem_ptw_obs_rd_pend
);

  // SPEC §10 walker obs_st encodings (cite SPEC §10; values from #48
  // until #50 writes the table). Pack is
  // {st_evt, st_flt, st_fill, st_dec, st_rd, st_idle}.
  localparam integer ST_W    = 6;
  localparam [5:0]   ST_IDLE = 6'b000001;
  localparam [5:0]   ST_RD   = 6'b000010;  // table-read
  localparam [5:0]   ST_DEC  = 6'b000100;
  localparam [5:0]   ST_FILL = 6'b001000;
  localparam [5:0]   ST_FLT  = 6'b010000;
  localparam [5:0]   ST_EVT  = 6'b100000;

  wire chk = !rst_pyc;

  // Unconstrained BMC of a_st_legal FAILS at step 9 (obs_st=0):
  // cut fires desc_v=1, desc_kind=KIND_INVALID, !illegal — no
  // next-state arm. Not assumed away; not weakened. See
  // ub_mem_ptw_desc_dec_cut_contract.sv (bmc_contract).

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

endmodule
