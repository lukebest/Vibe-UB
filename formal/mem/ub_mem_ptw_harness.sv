// Standalone harness: PRODUCT ub_mem_ptw + port props.
// Functional inputs stay free. rst_pyc is high for 4 cycles then held
// low (same polarity / length as tb/mem/ub_mem_ptw_smoke_tb.v).
// Instantiates PRODUCT ports only — no tb_* , no internals.

module ub_mem_ptw_harness (
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
    .busy(busy)
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

  // Induction auxiliaries (asserts only). See ub_mem_ptw_inv.sv.
  ub_mem_ptw_inv u_inv (
    .core_clk(core_clk),
    .rst_pyc(rst_pyc),
    .st_idle(u_dut.st_idle),
    .st_rd(u_dut.st_rd),
    .st_dec(u_dut.st_dec),
    .st_fill(u_dut.st_fill),
    .st_flt(u_dut.st_flt),
    .st_evt(u_dut.st_evt),
    .rd_valid_q(u_dut.rd_valid_q),
    .rd_len_q(u_dut.rd_len_q),
    .rd_tag_q(u_dut.rd_tag_q)
  );

endmodule
