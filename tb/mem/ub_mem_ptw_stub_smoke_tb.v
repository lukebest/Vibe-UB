// Smoke the public placeholder stub through ub_mem_ptw ports only.
// Stub outputs are translation-fault; walker must not fill.

module ub_mem_ptw_stub_smoke_tb;
  reg         core_clk;
  reg         rst_pyc;
  reg         req_valid;
  reg  [3:0]  req_ent_idx;
  reg  [19:0] req_token_id;
  reg  [63:0] req_uba;
  reg  [43:0] ctx_matt_ba;
  reg  [5:0]  ctx_ia_w;
  reg  [31:0] ctx_mattr0;
  reg  [31:0] ctx_mattr1;
  reg         ctx_affd;
  reg         ctx_matt_wd;
  reg         rd_req_ready;
  reg         rd_rsp_valid;
  reg  [511:0] rd_rsp_data;
  reg         rd_rsp_err;
  reg         fill_ready;
  reg         flt_ready;

  wire        req_ready;
  wire        rd_req_valid;
  wire [47:0] rd_req_addr;
  wire        rd_rsp_ready;
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
  wire        busy;

  integer errors;
  integer cycles;
  reg     rsp_pend;

  ub_mem_ptw u_ptw (
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
    .rd_req_ready(rd_req_ready),
    .rd_rsp_valid(rd_rsp_valid),
    .rd_rsp_data(rd_rsp_data),
    .rd_rsp_err(rd_rsp_err),
    .fill_ready(fill_ready),
    .flt_ready(flt_ready),
    .req_ready(req_ready),
    .rd_req_valid(rd_req_valid),
    .rd_req_addr(rd_req_addr),
    .rd_rsp_ready(rd_rsp_ready),
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
    .busy(busy)
  );

  initial begin
    core_clk = 1'b0;
    forever #5 core_clk = ~core_clk;
  end

  task tick;
    begin
      @(posedge core_clk);
      cycles = cycles + 1;
      if (cycles > 2000) begin
        $display("FAIL: timeout");
        $finish;
      end
    end
  endtask

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      rd_rsp_valid <= 1'b0;
      rd_rsp_data <= 512'hDEAD_BEEF;
      rd_rsp_err <= 1'b0;
      rsp_pend <= 1'b0;
    end else begin
      if (rd_req_valid && rd_req_ready)
        rsp_pend <= 1'b1;
      if (rsp_pend && rd_rsp_ready) begin
        rd_rsp_valid <= 1'b1;
        rd_rsp_data <= 512'hFFFF_FFFF_FFFF_FFFF;
        rsp_pend <= 1'b0;
      end else if (rd_rsp_valid && rd_rsp_ready) begin
        rd_rsp_valid <= 1'b0;
      end
    end
  end

  initial begin
    errors = 0;
    cycles = 0;
    rst_pyc = 1'b1;
    req_valid = 1'b0;
    req_ent_idx = 4'h2;
    req_token_id = 20'h1;
    req_uba = {16'b0, 36'h1000_0000, 12'h0};
    ctx_matt_ba = 44'h1;
    ctx_ia_w = 6'd48;
    ctx_mattr0 = 32'h0;
    ctx_mattr1 = 32'h0;
    ctx_affd = 1'b0;
    ctx_matt_wd = 1'b0;
    rd_req_ready = 1'b1;
    fill_ready = 1'b1;
    flt_ready = 1'b1;
    rd_rsp_valid = 1'b0;
    rd_rsp_data = 512'b0;
    rd_rsp_err = 1'b0;
    rsp_pend = 1'b0;
    repeat (4) tick;
    rst_pyc = 1'b0;
    repeat (4) tick;

    while (!req_ready) tick;
    req_valid = 1'b1;
    tick;
    req_valid = 1'b0;

    while (!fill_valid && !flt_valid) tick;

    if (fill_valid) begin
      $display("FAIL: stub path filled TLB");
      errors = errors + 1;
    end
    if (!flt_valid || !flt_xlat || flt_illegal || flt_ill_cause !== 4'd0) begin
      $display("FAIL: stub path fault flags xlat=%0d ill=%0d cause=%0d",
               flt_xlat, flt_illegal, flt_ill_cause);
      errors = errors + 1;
    end

    if (errors == 0)
      $display("STUB SMOKE PASS");
    else
      $display("STUB SMOKE FAIL errors=%0d", errors);
    $finish;
  end
endmodule
