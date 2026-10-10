// ub_mem_tlb_if_props — HOOKS bind properties (SPEC §10 obs ports).
// Not product RTL. Yosys-compatible clocked assert/cover (formal/cmn style).
// Check only when tb_mem_tlb_obs_lkup_v==1 (lookup request + 1).
//
// Bound signals are HOOKS ports only. Backdoor preloads can write duplicate
// tags, so the harness holds tb_test_mode=0.

module ub_mem_tlb_if_props (
  input  wire        core_clk,
  input  wire        rst_pyc,
  input  wire        tb_test_mode,
  input  wire        fill_valid,
  input  wire        fill_ready,
  input  wire [3:0]  fill_ent_idx,
  input  wire [19:0] fill_token_id,
  input  wire [35:0] fill_page,
  input  wire        lk_valid,
  input  wire        lk_ready,
  input  wire [3:0]  lk_ent_idx,
  input  wire [19:0] lk_token_id,
  input  wire [35:0] lk_page,
  input  wire        tb_mem_tlb_obs_lkup_v,
  input  wire [3:0]  tb_mem_tlb_obs_hit,
  input  wire [3:0]  tb_mem_tlb_obs_vld,
  input  wire [59:0] tb_mem_tlb_obs_tag_w0,
  input  wire [59:0] tb_mem_tlb_obs_tag_w1,
  input  wire [59:0] tb_mem_tlb_obs_tag_w2,
  input  wire [59:0] tb_mem_tlb_obs_tag_w3
);

  wire chk = !rst_pyc && tb_mem_tlb_obs_lkup_v;

  always @(posedge core_clk) begin
    if (chk) begin
      a_hit_onehot0: assert ($onehot0(tb_mem_tlb_obs_hit));
      a_hit0_implies_vld: assert (!tb_mem_tlb_obs_hit[0] || tb_mem_tlb_obs_vld[0]);
      a_hit1_implies_vld: assert (!tb_mem_tlb_obs_hit[1] || tb_mem_tlb_obs_vld[1]);
      a_hit2_implies_vld: assert (!tb_mem_tlb_obs_hit[2] || tb_mem_tlb_obs_vld[2]);
      a_hit3_implies_vld: assert (!tb_mem_tlb_obs_hit[3] || tb_mem_tlb_obs_vld[3]);
      a_tag_unique_01: assert (
        !(tb_mem_tlb_obs_vld[0] && tb_mem_tlb_obs_vld[1]) ||
        (tb_mem_tlb_obs_tag_w0 != tb_mem_tlb_obs_tag_w1)
      );
      a_tag_unique_02: assert (
        !(tb_mem_tlb_obs_vld[0] && tb_mem_tlb_obs_vld[2]) ||
        (tb_mem_tlb_obs_tag_w0 != tb_mem_tlb_obs_tag_w2)
      );
      a_tag_unique_03: assert (
        !(tb_mem_tlb_obs_vld[0] && tb_mem_tlb_obs_vld[3]) ||
        (tb_mem_tlb_obs_tag_w0 != tb_mem_tlb_obs_tag_w3)
      );
      a_tag_unique_12: assert (
        !(tb_mem_tlb_obs_vld[1] && tb_mem_tlb_obs_vld[2]) ||
        (tb_mem_tlb_obs_tag_w1 != tb_mem_tlb_obs_tag_w2)
      );
      a_tag_unique_13: assert (
        !(tb_mem_tlb_obs_vld[1] && tb_mem_tlb_obs_vld[3]) ||
        (tb_mem_tlb_obs_tag_w1 != tb_mem_tlb_obs_tag_w3)
      );
      a_tag_unique_23: assert (
        !(tb_mem_tlb_obs_vld[2] && tb_mem_tlb_obs_vld[3]) ||
        (tb_mem_tlb_obs_tag_w2 != tb_mem_tlb_obs_tag_w3)
      );
    end
  end

  always @(posedge core_clk) begin
    c_way0_hit: cover (chk && tb_mem_tlb_obs_hit[0]);
    c_way1_hit: cover (chk && tb_mem_tlb_obs_hit[1]);
    c_way2_hit: cover (chk && tb_mem_tlb_obs_hit[2]);
    c_way3_hit: cover (chk && tb_mem_tlb_obs_hit[3]);
    c_all_vld_lkup: cover (chk && (tb_mem_tlb_obs_vld == 4'b1111));
  end

  // Two consecutive accepted fills of the same tag, then a lookup hit.
  reg [1:0]  f_nfill;
  reg [3:0]  f_ent;
  reg [19:0] f_tok;
  reg [35:0] f_page;
  reg        f_lk_same;

  wire fill_acc = fill_valid && fill_ready && !rst_pyc;
  wire same_fill = (fill_ent_idx == f_ent) &&
                   (fill_token_id == f_tok) &&
                   (fill_page == f_page);
  wire lk_acc = lk_valid && lk_ready && !rst_pyc;
  wire same_lk = (lk_ent_idx == f_ent) &&
                 (lk_token_id == f_tok) &&
                 (lk_page == f_page);

  initial begin
    f_nfill   = 2'd0;
    f_ent     = 4'd0;
    f_tok     = 20'd0;
    f_page    = 36'd0;
    f_lk_same = 1'b0;
  end

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      f_nfill   <= 2'd0;
      f_lk_same <= 1'b0;
    end else begin
      if (fill_acc) begin
        if ((f_nfill == 2'd0) || !same_fill) begin
          f_nfill <= 2'd1;
          f_ent   <= fill_ent_idx;
          f_tok   <= fill_token_id;
          f_page  <= fill_page;
        end else if (f_nfill == 2'd1) begin
          f_nfill <= 2'd2;
        end
      end
      f_lk_same <= lk_acc && same_lk && (f_nfill == 2'd2);
    end
  end

  always @(posedge core_clk) begin
    c_two_fill_same_then_hit: cover (
      chk && f_lk_same && (|tb_mem_tlb_obs_hit)
    );
  end

  always @(*) begin
    a_mode_off: assume (tb_test_mode == 1'b0);
  end

endmodule
