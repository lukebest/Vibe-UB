// Directed PRODUCT smoke for ub_mem_ptw.
// Walk success cases use tb/mem/ub_mem_ptw_desc_dec_tb_model.v (TB protocol
// in the 64-bit raw port). The public stub always reports translation fault,
// so success paths cannot come from the stub itself.

module ub_mem_ptw_smoke_tb;
  localparam integer KIND_INVALID = 0;
  localparam integer KIND_TABLE   = 1;
  localparam integer KIND_BLOCK   = 2;
  localparam integer KIND_PAGE    = 3;
  localparam integer ILL_NONE     = 0;
  localparam integer ILL_HW_AD    = 2;
  localparam integer ILL_RSVD     = 3;

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
  integer i;

  reg [63:0] mem_q [0:7];
  integer mem_n;
  integer mem_i;
  reg        rsp_pend;
  reg [63:0] rsp_raw;

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
      if (cycles > 4000) begin
        $display("FAIL: timeout");
        $finish;
      end
    end
  endtask

  function [63:0] pack_tb;
    input        v;
    input [1:0]  kind;
    input [35:0] addr;
    input [2:0]  idx;
    input [1:0]  ap;
    input        uxn;
    input        pxn;
    input        af;
    input        illegal;
    input [3:0]  cause;
    begin
      pack_tb = 64'b0;
      pack_tb[0] = v;
      pack_tb[2:1] = kind;
      pack_tb[38:3] = addr;
      pack_tb[41:39] = idx;
      pack_tb[43:42] = ap;
      pack_tb[44] = uxn;
      pack_tb[45] = pxn;
      pack_tb[46] = af;
      pack_tb[47] = illegal;
      pack_tb[51:48] = cause;
    end
  endfunction

  task mem_reset;
    begin
      mem_n = 0;
      mem_i = 0;
      rsp_pend = 1'b0;
      rsp_raw = 64'b0;
    end
  endtask

  task mem_push;
    input [63:0] raw;
    begin
      mem_q[mem_n] = raw;
      mem_n = mem_n + 1;
    end
  endtask

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      rd_rsp_valid <= 1'b0;
      rd_rsp_data <= 512'b0;
      rd_rsp_err <= 1'b0;
      rsp_pend <= 1'b0;
    end else begin
      if (rd_req_valid && rd_req_ready) begin
        rsp_pend <= 1'b1;
        if (mem_i < mem_n) begin
          rsp_raw <= mem_q[mem_i];
          mem_i <= mem_i + 1;
        end else begin
          rsp_raw <= 64'b0;
        end
      end
      if (rsp_pend && rd_rsp_ready) begin
        rd_rsp_valid <= 1'b1;
        rd_rsp_data <= {448'b0, rsp_raw};
        rd_rsp_err <= 1'b0;
        rsp_pend <= 1'b0;
      end else if (rd_rsp_valid && rd_rsp_ready) begin
        rd_rsp_valid <= 1'b0;
      end else if (!rd_rsp_ready) begin
        rd_rsp_valid <= rd_rsp_valid;
      end else begin
        rd_rsp_valid <= 1'b0;
      end
    end
  end

  task drive_idle;
    begin
      req_valid = 1'b0;
      req_ent_idx = 4'h1;
      req_token_id = 20'hABCDE;
      req_uba = 64'b0;
      ctx_matt_ba = 44'h0010_0000_000;
      ctx_ia_w = 6'd48;
      ctx_mattr0 = 32'h44556677;
      ctx_mattr1 = 32'h00112233;
      ctx_affd = 1'b0;
      ctx_matt_wd = 1'b0;
      rd_req_ready = 1'b1;
      fill_ready = 1'b1;
      flt_ready = 1'b1;
    end
  endtask

  task wait_done;
    integer guard;
    begin
      guard = 0;
      while (!fill_valid && !flt_valid && guard <= 80) begin
        tick;
        guard = guard + 1;
      end
      if (!fill_valid && !flt_valid) begin
        $display("FAIL: walk did not complete");
        errors = errors + 1;
      end
    end
  endtask

  task expect_fill;
    input [35:0] exp_page;
    input [35:0] exp_pfn;
    input [7:0]  exp_attr;
    input [1:0]  exp_ap;
    input        exp_uxn;
    input        exp_pxn;
    input        exp_af;
    begin
      wait_done;
      if (!fill_valid) begin
        $display("FAIL: expected fill, got flt xlat=%0d ill=%0d cause=%0d",
                 flt_xlat, flt_illegal, flt_ill_cause);
        errors = errors + 1;
      end else begin
        if (fill_page !== exp_page) begin
          $display("FAIL: fill_page %h != %h", fill_page, exp_page);
          errors = errors + 1;
        end
        if (fill_pfn !== exp_pfn) begin
          $display("FAIL: fill_pfn %h != %h", fill_pfn, exp_pfn);
          errors = errors + 1;
        end
        if (fill_attr !== exp_attr) begin
          $display("FAIL: fill_attr %h != %h", fill_attr, exp_attr);
          errors = errors + 1;
        end
        if (fill_ap !== exp_ap) begin
          $display("FAIL: fill_ap %h != %h", fill_ap, exp_ap);
          errors = errors + 1;
        end
        if (fill_uxn !== exp_uxn || fill_pxn !== exp_pxn || fill_af !== exp_af) begin
          $display("FAIL: fill flags uxn/pxn/af");
          errors = errors + 1;
        end
        if (fill_ent_idx !== 4'h1 || fill_token_id !== 20'hABCDE) begin
          $display("FAIL: fill tag mismatch");
          errors = errors + 1;
        end
        if (flt_valid) begin
          $display("FAIL: fill and fault together");
          errors = errors + 1;
        end
      end
      tick;
    end
  endtask

  task expect_fault;
    input        want_xlat;
    input        want_ill;
    input [3:0]  want_cause;
    begin
      wait_done;
      if (!flt_valid) begin
        $display("FAIL: expected fault, got fill pfn=%h", fill_pfn);
        errors = errors + 1;
      end else begin
        if (flt_xlat !== want_xlat) begin
          $display("FAIL: flt_xlat %0d != %0d", flt_xlat, want_xlat);
          errors = errors + 1;
        end
        if (flt_illegal !== want_ill) begin
          $display("FAIL: flt_illegal %0d != %0d", flt_illegal, want_ill);
          errors = errors + 1;
        end
        if (flt_ill_cause !== want_cause) begin
          $display("FAIL: flt_ill_cause %0d != %0d", flt_ill_cause, want_cause);
          errors = errors + 1;
        end
        if (fill_valid) begin
          $display("FAIL: fault also filled TLB");
          errors = errors + 1;
        end
      end
      tick;
    end
  endtask

  task start_walk;
    input [63:0] uba;
    input [5:0]  ia_w;
    begin
      while (!req_ready) tick;
      req_uba = uba;
      ctx_ia_w = ia_w;
      req_valid = 1'b1;
      tick;
      req_valid = 1'b0;
    end
  endtask

  initial begin
    errors = 0;
    cycles = 0;
    rst_pyc = 1'b1;
    rd_rsp_valid = 1'b0;
    rd_rsp_data = 512'b0;
    rd_rsp_err = 1'b0;
    drive_idle;
    mem_reset;
    repeat (4) tick;
    rst_pyc = 1'b0;
    repeat (4) tick;

    // L1 1 GB, first page in the block.
    mem_reset;
    mem_push(pack_tb(1'b1, KIND_BLOCK, 36'h0004_0000, 3'd2, 2'b10, 1'b1, 1'b0, 1'b1, 1'b0, ILL_NONE));
    start_walk({16'b0, 36'h0A00_0000, 12'h000}, 6'd39);
    expect_fill(36'h0A00_0000, {18'h001, 18'h00000}, 8'h55, 2'b10, 1'b1, 1'b0, 1'b1);
    $display("L1 first page ok");

    // L1 1 GB, last page in the block.
    mem_reset;
    mem_push(pack_tb(1'b1, KIND_BLOCK, 36'h0004_0000, 3'd2, 2'b10, 1'b1, 1'b0, 1'b1, 1'b0, ILL_NONE));
    start_walk({16'b0, 36'h0A03_FFFF, 12'hABC}, 6'd39);
    expect_fill(36'h0A03_FFFF, {18'h001, 18'h3FFFF}, 8'h55, 2'b10, 1'b1, 1'b0, 1'b1);
    $display("L1 last page ok");

    // L1 1 GB, random page.
    mem_reset;
    mem_push(pack_tb(1'b1, KIND_BLOCK, 36'h0004_0000, 3'd2, 2'b10, 1'b1, 1'b0, 1'b1, 1'b0, ILL_NONE));
    start_walk({16'b0, 36'h0A01_2345, 12'h010}, 6'd39);
    expect_fill(36'h0A01_2345, {18'h001, 18'h12345}, 8'h55, 2'b10, 1'b1, 1'b0, 1'b1);
    $display("L1 random page ok");

    // L2 2 MB block.
    mem_reset;
    mem_push(pack_tb(1'b1, KIND_BLOCK, 36'h0000_0200, 3'd2, 2'b10, 1'b1, 1'b0, 1'b1, 1'b0, ILL_NONE));
    start_walk({16'b0, 36'h0000_0055, 12'h000}, 6'd30);
    expect_fill(36'h0000_0055, {27'h000001, 9'h055}, 8'h55, 2'b10, 1'b1, 1'b0, 1'b1);
    $display("L2 block ok");

    // L3 page.
    mem_reset;
    mem_push(pack_tb(1'b1, KIND_PAGE, 36'h00AB_CDEF, 3'd2, 2'b10, 1'b1, 1'b0, 1'b1, 1'b0, ILL_NONE));
    start_walk({16'b0, 36'h0123_4000, 12'h000}, 6'd21);
    expect_fill(36'h0123_4000, 36'h00AB_CDEF, 8'h55, 2'b10, 1'b1, 1'b0, 1'b1);
    $display("L3 page ok");

    // Adjacent VAs across a 2 MB block boundary → different PAs.
    mem_reset;
    mem_push(pack_tb(1'b1, KIND_BLOCK, 36'h0000_0200, 3'd2, 2'b10, 1'b1, 1'b0, 1'b1, 1'b0, ILL_NONE));
    start_walk({16'b0, 36'h0000_01FF, 12'h000}, 6'd30);
    expect_fill(36'h0000_01FF, {27'h000001, 9'h1FF}, 8'h55, 2'b10, 1'b1, 1'b0, 1'b1);
    mem_reset;
    mem_push(pack_tb(1'b1, KIND_BLOCK, 36'h0000_0400, 3'd2, 2'b10, 1'b1, 1'b0, 1'b1, 1'b0, ILL_NONE));
    start_walk({16'b0, 36'h0000_0200, 12'h000}, 6'd30);
    expect_fill(36'h0000_0200, {27'h000002, 9'h000}, 8'h55, 2'b10, 1'b1, 1'b0, 1'b1);
    $display("adjacent VAs across block boundary ok");

    // Translation fault: no fill, no config-illegal.
    mem_reset;
    mem_push(pack_tb(1'b0, KIND_INVALID, 36'b0, 3'b0, 2'b0, 1'b0, 1'b0, 1'b0, 1'b0, ILL_NONE));
    start_walk({16'b0, 36'h0A00_0001, 12'h000}, 6'd39);
    expect_fault(1'b1, 1'b0, ILL_NONE);
    $display("translation fault ok");

    // Config-illegal: no fill, ill_cause forwarded.
    mem_reset;
    mem_push(pack_tb(1'b0, KIND_INVALID, 36'b0, 3'b0, 2'b0, 1'b0, 1'b0, 1'b0, 1'b1, ILL_HW_AD));
    start_walk({16'b0, 36'h0A00_0002, 12'h000}, 6'd39);
    expect_fault(1'b0, 1'b1, ILL_HW_AD);
    $display("config-illegal ok");

    if (errors == 0) begin
      $display("SMOKE PASS");
    end else begin
      $display("SMOKE FAIL errors=%0d", errors);
    end
    $finish;
  end
endmodule
