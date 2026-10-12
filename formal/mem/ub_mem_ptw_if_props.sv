// ub_mem_ptw_if_props — PRODUCT port properties (SPEC §14 Q-A08 / Q-C07).
// Yosys-compatible clocked assert / assume / cover (formal/mem/ub_mem_tlb
// style). Bound signals are PRODUCT netlist ports only.
//
// Environment (minimal, documented):
//   * rst_pyc is driven by the harness: high for 4 cycles (smoke / TLB
//     formal), then held low. Asserts and covers are gated by !rst_pyc.
//   * Input valid/ready legality only:
//       - req_valid && !req_ready → next cycle req_valid and the request
//         beat (req_* and ctx_*) stay.
//       - mem2host_rd_rsp_valid && !mem2host_rd_rsp_ready → next cycle
//         rsp valid and the rsp beat stay.
//     Ready-only inputs (mem2host_rd_ready, fill_ready, flt_ready,
//     evt_ready) are free. mem2host_rd_ready is NOT assumed high —
//     AP_TBLRD_REQ_HOLD (SPEC §14) would otherwise be vacuous.
//     No progress / fairness assumed.
//
// MATT_WD (Q-A08): ctx_matt_wd is sampled on the accept cycle
// (req_valid && req_ready). f_matt_pend tracks that request until the
// event handshake that ends it. During the in-flight window: no table
// read, no fill_valid, and the completing event is the first accepted
// event with evt_code == EVT_MATT_WD_MISS. evt_ready may stall; "exactly
// one" counts accepted event handshakes, not cycles of evt_valid.
//
// Decoder: after hierarchy the .sby deletes the inlined stub and
// splices ub_mem_ptw_desc_dec_cut.sv ($anyseq on every output). These
// properties do not read decode outputs; fill / block / page covers
// are reachable only because those outputs are unconstrained.

module ub_mem_ptw_if_props (
  input  wire        core_clk,
  input  wire        rst_pyc,
  input  wire        req_valid,
  input  wire        req_ready,
  input  wire [3:0]  req_ent_idx,
  input  wire [19:0] req_token_id,
  input  wire [63:0] req_uba,
  input  wire [43:0] ctx_matt_ba,
  input  wire [5:0]  ctx_ia_w,
  input  wire [31:0] ctx_mattr0,
  input  wire [31:0] ctx_mattr1,
  input  wire        ctx_affd,
  input  wire        ctx_matt_wd,
  input  wire        mem2host_rd_valid,
  input  wire        mem2host_rd_ready,
  input  wire [47:0] mem2host_rd_addr,
  input  wire [7:0]  mem2host_rd_len,
  input  wire [3:0]  mem2host_rd_tag,
  input  wire        mem2host_rd_rsp_valid,
  input  wire        mem2host_rd_rsp_ready,
  input  wire [511:0] mem2host_rd_rsp_data,
  input  wire [3:0]  mem2host_rd_rsp_tag,
  input  wire        mem2host_rd_rsp_err,
  input  wire        fill_valid,
  input  wire        fill_ready,
  input  wire        flt_valid,
  input  wire        evt_valid,
  input  wire [3:0]  evt_code,
  input  wire        evt_ready,
  input  wire        busy
);

  // One mapping block. Names from RTL / UARCH (params.py, SPEC §14).
  localparam integer EVT_CODE_W       = 4;
  localparam integer EVT_MATT_WD_MISS = 1;
  localparam integer PA_W             = 48;
  localparam integer RD_LEN_W         = 8;
  localparam integer RD_LEN_8B        = 8;
  localparam integer RD_LEN_32B       = 32;
  localparam integer RD_LEN_64B       = 64;
  localparam integer RD_TAG_W         = 4;
  localparam integer RD_TAG_ZERO      = 0;

  wire chk = !rst_pyc;

  // ------------------------------------------------------------------
  // Input valid/ready hold (environment).
  // ------------------------------------------------------------------
  reg                f_req_hold;
  reg [3:0]          f_req_ent_q;
  reg [19:0]         f_req_tok_q;
  reg [63:0]         f_req_uba_q;
  reg [43:0]         f_ctx_ba_q;
  reg [5:0]          f_ctx_ia_q;
  reg [31:0]         f_ctx_m0_q;
  reg [31:0]         f_ctx_m1_q;
  reg                f_ctx_affd_q;
  reg                f_ctx_wd_q;
  reg                f_rsp_hold;
  reg [511:0]        f_rsp_data_q;
  reg [3:0]          f_rsp_tag_q;
  reg                f_rsp_err_q;

  initial begin
    f_req_hold    = 1'b0;
    f_req_ent_q   = 4'd0;
    f_req_tok_q   = 20'd0;
    f_req_uba_q   = 64'd0;
    f_ctx_ba_q    = 44'd0;
    f_ctx_ia_q    = 6'd0;
    f_ctx_m0_q    = 32'd0;
    f_ctx_m1_q    = 32'd0;
    f_ctx_affd_q  = 1'b0;
    f_ctx_wd_q    = 1'b0;
    f_rsp_hold    = 1'b0;
    f_rsp_data_q  = 512'd0;
    f_rsp_tag_q   = 4'd0;
    f_rsp_err_q   = 1'b0;
  end

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      f_req_hold <= 1'b0;
      f_rsp_hold <= 1'b0;
    end else begin
      f_req_hold <= req_valid && !req_ready;
      if (req_valid && !req_ready) begin
        f_req_ent_q  <= req_ent_idx;
        f_req_tok_q  <= req_token_id;
        f_req_uba_q  <= req_uba;
        f_ctx_ba_q   <= ctx_matt_ba;
        f_ctx_ia_q   <= ctx_ia_w;
        f_ctx_m0_q   <= ctx_mattr0;
        f_ctx_m1_q   <= ctx_mattr1;
        f_ctx_affd_q <= ctx_affd;
        f_ctx_wd_q   <= ctx_matt_wd;
      end
      f_rsp_hold <= mem2host_rd_rsp_valid && !mem2host_rd_rsp_ready;
      if (mem2host_rd_rsp_valid && !mem2host_rd_rsp_ready) begin
        f_rsp_data_q <= mem2host_rd_rsp_data;
        f_rsp_tag_q  <= mem2host_rd_rsp_tag;
        f_rsp_err_q  <= mem2host_rd_rsp_err;
      end
    end
  end

  always @(posedge core_clk) begin
    if (chk && f_req_hold) begin
      a_req_hold_valid: assume (req_valid);
      a_req_hold_ent:   assume (req_ent_idx == f_req_ent_q);
      a_req_hold_tok:   assume (req_token_id == f_req_tok_q);
      a_req_hold_uba:   assume (req_uba == f_req_uba_q);
      a_req_hold_ba:    assume (ctx_matt_ba == f_ctx_ba_q);
      a_req_hold_ia:    assume (ctx_ia_w == f_ctx_ia_q);
      a_req_hold_m0:    assume (ctx_mattr0 == f_ctx_m0_q);
      a_req_hold_m1:    assume (ctx_mattr1 == f_ctx_m1_q);
      a_req_hold_affd:  assume (ctx_affd == f_ctx_affd_q);
      a_req_hold_wd:    assume (ctx_matt_wd == f_ctx_wd_q);
    end
    if (chk && f_rsp_hold) begin
      a_rsp_hold_valid: assume (mem2host_rd_rsp_valid);
      a_rsp_hold_data:  assume (mem2host_rd_rsp_data == f_rsp_data_q);
      a_rsp_hold_tag:   assume (mem2host_rd_rsp_tag == f_rsp_tag_q);
      a_rsp_hold_err:   assume (mem2host_rd_rsp_err == f_rsp_err_q);
    end
  end

  // ------------------------------------------------------------------
  // (1) evt_valid |-> evt_code != reserved 0
  // (2) evt_valid && !evt_ready |=> evt_valid && $stable(evt_code)
  // ------------------------------------------------------------------
  reg                   f_evt_hold;
  reg [EVT_CODE_W-1:0]  f_evt_code_q;

  initial begin
    f_evt_hold   = 1'b0;
    f_evt_code_q = {EVT_CODE_W{1'b0}};
  end

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      f_evt_hold   <= 1'b0;
      f_evt_code_q <= {EVT_CODE_W{1'b0}};
    end else begin
      f_evt_hold   <= evt_valid && !evt_ready;
      f_evt_code_q <= evt_code;
    end
  end

  always @(posedge core_clk) begin
    if (chk && evt_valid) begin
      a_evt_code_nonzero: assert (evt_code != {EVT_CODE_W{1'b0}});
    end
    if (chk && f_evt_hold) begin
      a_evt_hold_valid: assert (evt_valid);
      a_evt_hold_code:  assert (evt_code == f_evt_code_q);
    end
  end

  // ------------------------------------------------------------------
  // (3) MATT_WD accept: no mem2host_rd_valid, no fill_valid, exactly
  //     one accepted event with evt_code == EVT_MATT_WD_MISS.
  // ------------------------------------------------------------------
  wire matt_acc = chk && req_valid && req_ready && ctx_matt_wd;
  wire matt_evt = chk && f_matt_pend && evt_valid && evt_ready;

  reg f_matt_pend;
  reg f_matt_evt_seen;

  initial begin
    f_matt_pend     = 1'b0;
    f_matt_evt_seen = 1'b0;
  end

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      f_matt_pend     <= 1'b0;
      f_matt_evt_seen <= 1'b0;
    end else if (matt_acc) begin
      f_matt_pend     <= 1'b1;
      f_matt_evt_seen <= 1'b0;
    end else if (f_matt_pend && evt_valid && evt_ready) begin
      f_matt_pend     <= 1'b0;
      f_matt_evt_seen <= 1'b1;
    end
  end

  wire matt_inflight = matt_acc || f_matt_pend;

  always @(posedge core_clk) begin
    if (chk && matt_inflight) begin
      a_matt_no_rd:   assert (!mem2host_rd_valid);
      a_matt_no_fill: assert (!fill_valid);
    end
    if (chk && matt_inflight && evt_valid) begin
      a_matt_evt_code: assert (evt_code == EVT_MATT_WD_MISS[EVT_CODE_W-1:0]);
    end
    // Completing handshake is the first (and only) accepted event.
    if (matt_evt) begin
      a_matt_one_evt: assert (!f_matt_evt_seen);
    end
  end

  // ------------------------------------------------------------------
  // (4) mem2host_rd_valid |-> len in {RD_LEN_8B, RD_LEN_32B, RD_LEN_64B}
  // (5) first-wave: len == RD_LEN_8B && tag == RD_TAG_ZERO
  // (6) at most one outstanding read (accepted, rsp not yet returned)
  // (7) AP_TBLRD_REQ_HOLD (SPEC §14 table-read interface):
  //     valid && !ready |=> valid and $stable(addr/len/tag).
  //     mem2host_rd_ready stays a free input.
  // ------------------------------------------------------------------
  reg f_rd_outst;
  reg f_rd_was_outst;
  reg f_rd_got_rsp;

  wire rd_acc = chk && mem2host_rd_valid && mem2host_rd_ready;
  wire rd_ret = chk && mem2host_rd_rsp_valid && mem2host_rd_rsp_ready;

  initial begin
    f_rd_outst     = 1'b0;
    f_rd_was_outst = 1'b0;
    f_rd_got_rsp   = 1'b0;
  end

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      f_rd_outst     <= 1'b0;
      f_rd_was_outst <= 1'b0;
      f_rd_got_rsp   <= 1'b0;
    end else begin
      if (rd_acc)
        f_rd_outst <= 1'b1;
      else if (rd_ret)
        f_rd_outst <= 1'b0;
      if (rd_acc)
        f_rd_was_outst <= 1'b1;
      if (f_rd_was_outst && rd_ret)
        f_rd_got_rsp <= 1'b1;
    end
  end

  always @(posedge core_clk) begin
    if (chk && mem2host_rd_valid) begin
      a_rd_len_legal: assert (
        (mem2host_rd_len == RD_LEN_8B[RD_LEN_W-1:0])  ||
        (mem2host_rd_len == RD_LEN_32B[RD_LEN_W-1:0]) ||
        (mem2host_rd_len == RD_LEN_64B[RD_LEN_W-1:0])
      );
      a_rd_first_wave: assert (
        (mem2host_rd_len == RD_LEN_8B[RD_LEN_W-1:0]) &&
        (mem2host_rd_tag == RD_TAG_ZERO[RD_TAG_W-1:0])
      );
      a_rd_one_outst: assert (!f_rd_outst);
    end
  end

  // AP_TBLRD_REQ_HOLD (SPEC §14 table-read interface):
  // mem2host_rd_valid && !mem2host_rd_ready |=>
  //   mem2host_rd_valid && $stable(mem2host_rd_addr) &&
  //   $stable(mem2host_rd_len) && $stable(mem2host_rd_tag)
  reg                 f_rd_req_hold;
  reg [PA_W-1:0]      f_rd_addr_q;
  reg [RD_LEN_W-1:0]  f_rd_len_q;
  reg [RD_TAG_W-1:0]  f_rd_tag_q;

  initial begin
    f_rd_req_hold = 1'b0;
    f_rd_addr_q   = {PA_W{1'b0}};
    f_rd_len_q    = {RD_LEN_W{1'b0}};
    f_rd_tag_q    = {RD_TAG_W{1'b0}};
  end

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      f_rd_req_hold <= 1'b0;
      f_rd_addr_q   <= {PA_W{1'b0}};
      f_rd_len_q    <= {RD_LEN_W{1'b0}};
      f_rd_tag_q    <= {RD_TAG_W{1'b0}};
    end else begin
      f_rd_req_hold <= mem2host_rd_valid && !mem2host_rd_ready;
      f_rd_addr_q   <= mem2host_rd_addr;
      f_rd_len_q    <= mem2host_rd_len;
      f_rd_tag_q    <= mem2host_rd_tag;
    end
  end

  always @(posedge core_clk) begin
    if (chk && f_rd_req_hold) begin
      AP_TBLRD_REQ_HOLD: assert (
        mem2host_rd_valid &&
        (mem2host_rd_addr == f_rd_addr_q) &&
        (mem2host_rd_len  == f_rd_len_q) &&
        (mem2host_rd_tag  == f_rd_tag_q)
      );
    end
  end

  // ------------------------------------------------------------------
  // Covers
  // ------------------------------------------------------------------
  always @(posedge core_clk) begin
    c_evt_fire:        cover (chk && evt_valid && evt_ready);
    c_matt_wd_done:    cover (matt_evt &&
                              (evt_code == EVT_MATT_WD_MISS[EVT_CODE_W-1:0]));
    c_rd_req_and_rsp:  cover (chk && f_rd_got_rsp);
    c_fill_issued:     cover (chk && fill_valid && fill_ready);
    // Backpressured request then accept (proves rd_ready is not stuck high).
    c_rd_bp_then_acc:  cover (chk && f_rd_req_hold &&
                              mem2host_rd_valid && mem2host_rd_ready);
  end

  // ------------------------------------------------------------------
  // Induction auxiliaries (asserts only; never assumed).
  // PRODUCT ports. RTL writes registered constants every cycle
  // (rd_len_q = RD_LEN_8B, rd_tag_q = RD_TAG_ZERO). The induction
  // CEX for AP_TBLRD_REQ_HOLD started with len != 8.
  // ------------------------------------------------------------------
  reg f_rd_valid_q;

  initial f_rd_valid_q = 1'b0;

  always @(posedge core_clk) begin
    if (rst_pyc)
      f_rd_valid_q <= 1'b0;
    else
      f_rd_valid_q <= mem2host_rd_valid;
  end

  always @(posedge core_clk) begin
    if (chk) begin
      a_rd_len_const: assert (mem2host_rd_len == RD_LEN_8B[RD_LEN_W-1:0]);
      a_rd_tag_const: assert (mem2host_rd_tag == RD_TAG_ZERO[RD_TAG_W-1:0]);

      // busy is ~idle; req_ready is idle.
      a_busy_nidle: assert (busy == !req_ready);

      // One-hot port image of the walker (idle / fill / flt / evt).
      // ST_RD / ST_DEC are the quiet-busy remainder.
      a_idle_excl: assert (
        !req_ready ||
        (!fill_valid && !flt_valid && !evt_valid &&
         !mem2host_rd_valid && !mem2host_rd_rsp_ready)
      );
      a_fill_excl: assert (
        !fill_valid ||
        (!req_ready && !flt_valid && !evt_valid &&
         !mem2host_rd_valid && !mem2host_rd_rsp_ready)
      );
      a_flt_excl: assert (
        !flt_valid ||
        (!req_ready && !fill_valid && !evt_valid &&
         !mem2host_rd_valid && !mem2host_rd_rsp_ready)
      );
      a_evt_excl: assert (
        !evt_valid ||
        (!req_ready && !fill_valid && !flt_valid &&
         !mem2host_rd_valid && !mem2host_rd_rsp_ready)
      );
      // rd_valid_q and rd_sent are mutex; rsp_ready = st_rd & rd_sent.
      a_rd_valid_excl: assert (
        !mem2host_rd_valid ||
        (!req_ready && !fill_valid && !flt_valid && !evt_valid &&
         !mem2host_rd_rsp_ready)
      );

      // f_matt_pend is set the cycle after a MATT_WD accept (to_evt_wd
      // → ST_EVT) and cleared on the completing event handshake.
      a_matt_pend_evt:    assert (!f_matt_pend || evt_valid);
      a_matt_pend_code:   assert (
        !f_matt_pend || (evt_code == EVT_MATT_WD_MISS[EVT_CODE_W-1:0])
      );
      a_matt_pend_nord:   assert (!f_matt_pend || !mem2host_rd_valid);
      a_matt_pend_nofill: assert (!f_matt_pend || !fill_valid);
      a_matt_pend_noflt:  assert (!f_matt_pend || !flt_valid);
      a_matt_pend_nidle:  assert (!f_matt_pend || !req_ready);
      a_matt_pend_seen:   assert (!(f_matt_pend && f_matt_evt_seen));

      // Outstanding table-read: accepted, waiting for rsp (ST_RD & rd_sent).
      a_rd_outst_nvald: assert (!f_rd_outst || !mem2host_rd_valid);
      a_rd_outst_rsp:   assert (!f_rd_outst || mem2host_rd_rsp_ready);

      // Last-cycle valid: addr/len/tag held (addr_q writes only on
      // do_req | to_next, both off while rd_valid).
      a_rd_addr_held: assert (!f_rd_valid_q ||
                              (mem2host_rd_addr == f_rd_addr_q));
      a_rd_len_held:  assert (!f_rd_valid_q ||
                              (mem2host_rd_len == f_rd_len_q));
      a_rd_tag_held:  assert (!f_rd_valid_q ||
                              (mem2host_rd_tag == f_rd_tag_q));
      a_rd_hold_valid: assert (!f_rd_req_hold || mem2host_rd_valid);
    end
  end

endmodule
