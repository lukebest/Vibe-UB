// HOOKS harness: rtl/mem/hooks/ub_mem_ptw.v + PRODUCT port props +
// HOOKS-only obs auxiliaries. Same reset as the PRODUCT harness.

module ub_mem_ptw_hooks_harness (
  input  wire        core_clk,
  input  wire        req_valid,
  input  wire [3:0]  req_ent_idx,
  input  wire [19:0] req_token_id,
  input  wire [63:0] req_uba,
  input  wire [43:0] ctx_matt_ba,
  input  wire [5:0]  ctx_ia_w,
  input  wire [31:0] ctx_mattr0,
  input  wire [31:0] ctx_mattr1,
  input  wire        ctx_affd,
  input  wire        ctx_matt_wd,
  input  wire        mem2host_rd_ready,
  input  wire        mem2host_rd_rsp_valid,
  input  wire [511:0] mem2host_rd_rsp_data,
  input  wire [3:0]  mem2host_rd_rsp_tag,
  input  wire        mem2host_rd_rsp_err,
  input  wire        fill_ready,
  input  wire        flt_ready,
  input  wire        evt_ready
);

  reg [2:0] f_rst_cnt;
  initial f_rst_cnt = 3'd0;
  always @(posedge core_clk) begin
    if (f_rst_cnt < 3'd4)
      f_rst_cnt <= f_rst_cnt + 3'd1;
  end
  wire rst_pyc = (f_rst_cnt < 3'd4);

  wire        req_ready;
  wire        mem2host_rd_valid;
  wire [47:0] mem2host_rd_addr;
  wire [7:0]  mem2host_rd_len;
  wire [3:0]  mem2host_rd_tag;
  wire        mem2host_rd_rsp_ready;
  wire        fill_valid;
  wire [3:0]  fill_ent_idx;
  wire [19:0] fill_token_id;
  wire [35:0] fill_page;
  wire [35:0] fill_pfn;
  wire [7:0]  fill_attr;
  wire [1:0]  fill_ap;
  wire        fill_uxn;
  wire        fill_pxn;
  wire        fill_af;
  wire        flt_valid;
  wire        flt_xlat;
  wire        flt_illegal;
  wire [3:0]  flt_ill_cause;
  wire        flt_rd_err;
  wire        flt_af;
  wire        evt_valid;
  wire [3:0]  evt_code;
  wire        busy;
  wire [5:0]  tb_mem_ptw_obs_st;
  wire        tb_mem_ptw_obs_rd_pend;

  ub_mem_ptw u_dut (
    .core_clk(core_clk),
    .rst_pyc(rst_pyc),
    .req_valid(req_valid),
    .req_ent_idx(req_ent_idx),
    .req_token_id(req_token_id),
    .req_uba(req_uba),
    .ctx_matt_ba(ctx_matt_ba),
    .ctx_ia_w(ctx_ia_w),
    .ctx_mattr0(ctx_mattr0),
    .ctx_mattr1(ctx_mattr1),
    .ctx_affd(ctx_affd),
    .ctx_matt_wd(ctx_matt_wd),
    .mem2host_rd_ready(mem2host_rd_ready),
    .mem2host_rd_rsp_valid(mem2host_rd_rsp_valid),
    .mem2host_rd_rsp_data(mem2host_rd_rsp_data),
    .mem2host_rd_rsp_tag(mem2host_rd_rsp_tag),
    .mem2host_rd_rsp_err(mem2host_rd_rsp_err),
    .fill_ready(fill_ready),
    .flt_ready(flt_ready),
    .evt_ready(evt_ready),
    .req_ready(req_ready),
    .mem2host_rd_valid(mem2host_rd_valid),
    .mem2host_rd_addr(mem2host_rd_addr),
    .mem2host_rd_len(mem2host_rd_len),
    .mem2host_rd_tag(mem2host_rd_tag),
    .mem2host_rd_rsp_ready(mem2host_rd_rsp_ready),
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
    .flt_valid(flt_valid),
    .flt_xlat(flt_xlat),
    .flt_illegal(flt_illegal),
    .flt_ill_cause(flt_ill_cause),
    .flt_rd_err(flt_rd_err),
    .flt_af(flt_af),
    .evt_valid(evt_valid),
    .evt_code(evt_code),
    .busy(busy),
    .tb_mem_ptw_obs_st(tb_mem_ptw_obs_st),
    .tb_mem_ptw_obs_rd_pend(tb_mem_ptw_obs_rd_pend)
  );

  ub_mem_ptw_if_props u_props (
    .core_clk(core_clk),
    .rst_pyc(rst_pyc),
    .req_valid(req_valid),
    .req_ready(req_ready),
    .req_ent_idx(req_ent_idx),
    .req_token_id(req_token_id),
    .req_uba(req_uba),
    .ctx_matt_ba(ctx_matt_ba),
    .ctx_ia_w(ctx_ia_w),
    .ctx_mattr0(ctx_mattr0),
    .ctx_mattr1(ctx_mattr1),
    .ctx_affd(ctx_affd),
    .ctx_matt_wd(ctx_matt_wd),
    .mem2host_rd_valid(mem2host_rd_valid),
    .mem2host_rd_ready(mem2host_rd_ready),
    .mem2host_rd_addr(mem2host_rd_addr),
    .mem2host_rd_len(mem2host_rd_len),
    .mem2host_rd_tag(mem2host_rd_tag),
    .mem2host_rd_rsp_valid(mem2host_rd_rsp_valid),
    .mem2host_rd_rsp_ready(mem2host_rd_rsp_ready),
    .mem2host_rd_rsp_data(mem2host_rd_rsp_data),
    .mem2host_rd_rsp_tag(mem2host_rd_rsp_tag),
    .mem2host_rd_rsp_err(mem2host_rd_rsp_err),
    .fill_valid(fill_valid),
    .fill_ready(fill_ready),
    .evt_valid(evt_valid),
    .evt_code(evt_code),
    .evt_ready(evt_ready)
  );

  // Yosys 0.33 treats dotted hierarchical refs as implicit undriven
  // wires. bind into ub_mem_ptw so the cut outputs are the local
  // pyc_instance_* nets (u_desc_dec.out_valid/desc_v/desc_kind).
  bind ub_mem_ptw ub_mem_ptw_hooks_inv u_hooks_inv (
    .core_clk(core_clk),
    .rst_pyc(rst_pyc),
    .tb_mem_ptw_obs_st(tb_mem_ptw_obs_st),
    .tb_mem_ptw_obs_rd_pend(tb_mem_ptw_obs_rd_pend),
    .dec_out_valid(pyc_instance_143),
    .desc_v(pyc_instance_144),
    .desc_kind(pyc_instance_145),
    .fill_valid(fill_valid)
  );

endmodule
