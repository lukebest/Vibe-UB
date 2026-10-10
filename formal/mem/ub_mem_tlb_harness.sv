// Standalone harness: HOOKS ub_mem_tlb + props. Not product RTL.
// Functional inputs stay free. rst_pyc is high for 4 cycles then held
// low (same polarity / length as tb/mem smoke). tb_test_mode and every
// backdoor input are tied off.

module ub_mem_tlb_harness (
  input  wire        core_clk,
  input  wire        lk_valid,
  input  wire [3:0]  lk_ent_idx,
  input  wire [19:0] lk_token_id,
  input  wire [35:0] lk_page,
  input  wire        fill_valid,
  input  wire [3:0]  fill_ent_idx,
  input  wire [19:0] fill_token_id,
  input  wire [35:0] fill_page,
  input  wire [35:0] fill_pfn,
  input  wire [7:0]  fill_attr,
  input  wire [1:0]  fill_ap,
  input  wire        fill_uxn,
  input  wire        fill_pxn,
  input  wire        fill_af,
  input  wire        inv2tlb_all_valid,
  input  wire        inv2tlb_scan_valid,
  input  wire [5:0]  inv2tlb_scan_set,
  input  wire [3:0]  inv2tlb_scan_ent_idx,
  input  wire [19:0] inv2tlb_scan_token_id,
  input  wire        inv2tlb_scan_match_ent,
  input  wire        inv2tlb_scan_match_tok
);

  reg [2:0] f_rst_cnt;
  initial f_rst_cnt = 3'd0;
  always @(posedge core_clk) begin
    if (f_rst_cnt < 3'd4)
      f_rst_cnt <= f_rst_cnt + 3'd1;
  end
  wire rst_pyc = (f_rst_cnt < 3'd4);

  wire tb_test_mode = 1'b0;

  wire        lk_ready;
  wire        lk_rsp_valid;
  wire        lk_hit;
  wire [35:0] xlat_pfn;
  wire [7:0]  xlat_attr;
  wire [1:0]  xlat_ap;
  wire        xlat_uxn;
  wire        xlat_pxn;
  wire        xlat_af;
  wire        fill_ready;
  wire        inv2tlb_all_ready;
  wire        inv2tlb_scan_ready;
  wire        tlb2inv_scan_done;
  wire        busy;
  wire        tb_mem_tlb_obs_lkup_v;
  wire [3:0]  tb_mem_tlb_obs_hit;
  wire [3:0]  tb_mem_tlb_obs_vld;
  wire [59:0] tb_mem_tlb_obs_tag_w0;
  wire [59:0] tb_mem_tlb_obs_tag_w1;
  wire [59:0] tb_mem_tlb_obs_tag_w2;
  wire [59:0] tb_mem_tlb_obs_tag_w3;
  wire [108:0] tb_mem_tlb_w0_bd_rdata;
  wire [108:0] tb_mem_tlb_w1_bd_rdata;
  wire [108:0] tb_mem_tlb_w2_bd_rdata;
  wire [108:0] tb_mem_tlb_w3_bd_rdata;

  ub_mem_tlb u_dut (
    .core_clk(core_clk),
    .rst_pyc(rst_pyc),
    .lk_valid(lk_valid),
    .lk_ent_idx(lk_ent_idx),
    .lk_token_id(lk_token_id),
    .lk_page(lk_page),
    .fill_valid(fill_valid),
    .fill_ent_idx(fill_ent_idx),
    .fill_token_id(fill_token_id),
    .fill_page(fill_page),
    .fill_pfn(fill_pfn),
    .fill_attr(fill_attr),
    .fill_ap(fill_ap),
    .fill_uxn(fill_uxn),
    .fill_pxn(fill_pxn),
    .fill_af(fill_af),
    .inv2tlb_all_valid(inv2tlb_all_valid),
    .inv2tlb_scan_valid(inv2tlb_scan_valid),
    .inv2tlb_scan_set(inv2tlb_scan_set),
    .inv2tlb_scan_ent_idx(inv2tlb_scan_ent_idx),
    .inv2tlb_scan_token_id(inv2tlb_scan_token_id),
    .inv2tlb_scan_match_ent(inv2tlb_scan_match_ent),
    .inv2tlb_scan_match_tok(inv2tlb_scan_match_tok),
    .tb_test_mode(tb_test_mode),
    .tb_mem_tlb_w0_bd_we(1'b0),
    .tb_mem_tlb_w0_bd_addr(6'd0),
    .tb_mem_tlb_w0_bd_wdata(109'd0),
    .tb_mem_tlb_w0_bd_re(1'b0),
    .tb_mem_tlb_w0_bd_vld_we(1'b0),
    .tb_mem_tlb_w0_bd_vld_wdata(1'b0),
    .tb_mem_tlb_w1_bd_we(1'b0),
    .tb_mem_tlb_w1_bd_addr(6'd0),
    .tb_mem_tlb_w1_bd_wdata(109'd0),
    .tb_mem_tlb_w1_bd_re(1'b0),
    .tb_mem_tlb_w1_bd_vld_we(1'b0),
    .tb_mem_tlb_w1_bd_vld_wdata(1'b0),
    .tb_mem_tlb_w2_bd_we(1'b0),
    .tb_mem_tlb_w2_bd_addr(6'd0),
    .tb_mem_tlb_w2_bd_wdata(109'd0),
    .tb_mem_tlb_w2_bd_re(1'b0),
    .tb_mem_tlb_w2_bd_vld_we(1'b0),
    .tb_mem_tlb_w2_bd_vld_wdata(1'b0),
    .tb_mem_tlb_w3_bd_we(1'b0),
    .tb_mem_tlb_w3_bd_addr(6'd0),
    .tb_mem_tlb_w3_bd_wdata(109'd0),
    .tb_mem_tlb_w3_bd_re(1'b0),
    .tb_mem_tlb_w3_bd_vld_we(1'b0),
    .tb_mem_tlb_w3_bd_vld_wdata(1'b0),
    .lk_ready(lk_ready),
    .lk_rsp_valid(lk_rsp_valid),
    .lk_hit(lk_hit),
    .xlat_pfn(xlat_pfn),
    .xlat_attr(xlat_attr),
    .xlat_ap(xlat_ap),
    .xlat_uxn(xlat_uxn),
    .xlat_pxn(xlat_pxn),
    .xlat_af(xlat_af),
    .fill_ready(fill_ready),
    .inv2tlb_all_ready(inv2tlb_all_ready),
    .inv2tlb_scan_ready(inv2tlb_scan_ready),
    .tlb2inv_scan_done(tlb2inv_scan_done),
    .busy(busy),
    .tb_mem_tlb_obs_lkup_v(tb_mem_tlb_obs_lkup_v),
    .tb_mem_tlb_obs_hit(tb_mem_tlb_obs_hit),
    .tb_mem_tlb_obs_vld(tb_mem_tlb_obs_vld),
    .tb_mem_tlb_obs_tag_w0(tb_mem_tlb_obs_tag_w0),
    .tb_mem_tlb_obs_tag_w1(tb_mem_tlb_obs_tag_w1),
    .tb_mem_tlb_obs_tag_w2(tb_mem_tlb_obs_tag_w2),
    .tb_mem_tlb_obs_tag_w3(tb_mem_tlb_obs_tag_w3),
    .tb_mem_tlb_w0_bd_rdata(tb_mem_tlb_w0_bd_rdata),
    .tb_mem_tlb_w1_bd_rdata(tb_mem_tlb_w1_bd_rdata),
    .tb_mem_tlb_w2_bd_rdata(tb_mem_tlb_w2_bd_rdata),
    .tb_mem_tlb_w3_bd_rdata(tb_mem_tlb_w3_bd_rdata)
  );

  ub_mem_tlb_if_props u_props (
    .core_clk(core_clk),
    .rst_pyc(rst_pyc),
    .tb_test_mode(tb_test_mode),
    .fill_valid(fill_valid),
    .fill_ready(fill_ready),
    .fill_ent_idx(fill_ent_idx),
    .fill_token_id(fill_token_id),
    .fill_page(fill_page),
    .lk_valid(lk_valid),
    .lk_ready(lk_ready),
    .lk_ent_idx(lk_ent_idx),
    .lk_token_id(lk_token_id),
    .lk_page(lk_page),
    .tb_mem_tlb_obs_lkup_v(tb_mem_tlb_obs_lkup_v),
    .tb_mem_tlb_obs_hit(tb_mem_tlb_obs_hit),
    .tb_mem_tlb_obs_vld(tb_mem_tlb_obs_vld),
    .tb_mem_tlb_obs_tag_w0(tb_mem_tlb_obs_tag_w0),
    .tb_mem_tlb_obs_tag_w1(tb_mem_tlb_obs_tag_w1),
    .tb_mem_tlb_obs_tag_w2(tb_mem_tlb_obs_tag_w2),
    .tb_mem_tlb_obs_tag_w3(tb_mem_tlb_obs_tag_w3)
  );

endmodule
