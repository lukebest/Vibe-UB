// Directed HOOKS smoke for ub_mem_ptw.
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
  localparam integer EVT_CODE_W   = 4;
  localparam integer EVT_MATT_WD_MISS = 1;
  localparam integer RD_LEN_W     = 8;
  localparam integer RD_LEN_8B    = 8;
  localparam integer RD_TAG_W     = 4;
  localparam integer RD_TAG_ZERO  = 0;

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
  reg         mem2host_rd_ready;
  reg         mem2host_rd_rsp_valid;
  reg  [511:0] mem2host_rd_rsp_data;
  reg  [3:0]  mem2host_rd_rsp_tag;
  reg         mem2host_rd_rsp_err;
  reg         fill_ready;
  reg         flt_ready;
  reg         evt_ready;

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

  integer errors;
  integer cycles;
  integer saw_rd;
  integer evt_hs;
  integer evt_seen;
  integer fill_seen;
  integer rd_outstand;
  integer first_rd_lat;
  reg        prev_evt_valid;
  reg        prev_evt_ready;
  reg [3:0]  prev_evt_code;
  reg        prev_rd_valid;
  reg        prev_rd_ready;
  reg [47:0] prev_rd_addr;
  reg [7:0]  prev_rd_len;
  reg [3:0]  prev_rd_tag;

  reg [63:0] mem_q [0:7];
  integer mem_n;
  integer mem_i;
  reg        rsp_pend;
  reg [63:0] rsp_raw;
  reg [2:0]  rsp_slot;
  integer    force_slot;
  integer    use_force_slot;

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

  function automatic legal_obs_st;
    input [5:0] st;
    begin
      legal_obs_st = (st === 6'b000001)
                  || (st === 6'b000010)
                  || (st === 6'b000100)
                  || (st === 6'b001000)
                  || (st === 6'b010000)
                  || (st === 6'b100000);
    end
  endfunction

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

  function [511:0] beat_place;
    input [63:0] raw;
    input [2:0]  slot;
    integer k;
    begin
      beat_place = {8{64'hDEAD_BEEF_F00D_BAAD}};
      for (k = 0; k < 8; k = k + 1) begin
        if (k[2:0] == slot)
          beat_place[k*64 +: 64] = raw;
      end
    end
  endfunction

  task mem_reset;
    begin
      mem_n = 0;
      mem_i = 0;
      rsp_pend = 1'b0;
      rsp_raw = 64'b0;
      rsp_slot = 3'b0;
      use_force_slot = 0;
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
      mem2host_rd_rsp_valid <= 1'b0;
      mem2host_rd_rsp_data <= 512'b0;
      mem2host_rd_rsp_tag <= 4'b0;
      mem2host_rd_rsp_err <= 1'b0;
      rsp_pend <= 1'b0;
    end else begin
      if (mem2host_rd_valid && mem2host_rd_ready) begin
        saw_rd <= saw_rd + 1;
        if (mem2host_rd_len !== RD_LEN_8B[RD_LEN_W-1:0]) begin
          $display("FAIL: mem2host_rd_len %0d != RD_LEN_8B", mem2host_rd_len);
          errors = errors + 1;
        end
        if (mem2host_rd_tag !== RD_TAG_ZERO[RD_TAG_W-1:0]) begin
          $display("FAIL: mem2host_rd_tag %0d != RD_TAG_ZERO", mem2host_rd_tag);
          errors = errors + 1;
        end
        rsp_pend <= 1'b1;
        if (use_force_slot)
          rsp_slot <= force_slot[2:0];
        else
          rsp_slot <= mem2host_rd_addr[5:3];
        if (mem_i < mem_n) begin
          rsp_raw <= mem_q[mem_i];
          mem_i <= mem_i + 1;
        end else begin
          rsp_raw <= 64'b0;
        end
      end
      if (rsp_pend && mem2host_rd_rsp_ready) begin
        mem2host_rd_rsp_valid <= 1'b1;
        mem2host_rd_rsp_data <= beat_place(rsp_raw, rsp_slot);
        mem2host_rd_rsp_tag <= 4'd0;
        mem2host_rd_rsp_err <= 1'b0;
        rsp_pend <= 1'b0;
      end else if (mem2host_rd_rsp_valid && mem2host_rd_rsp_ready) begin
        mem2host_rd_rsp_valid <= 1'b0;
      end else if (!mem2host_rd_rsp_ready) begin
        mem2host_rd_rsp_valid <= mem2host_rd_rsp_valid;
      end else begin
        mem2host_rd_rsp_valid <= 1'b0;
      end
    end
  end

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      prev_evt_valid <= 1'b0;
      prev_evt_ready <= 1'b1;
      prev_evt_code <= {EVT_CODE_W{1'b0}};
      prev_rd_valid <= 1'b0;
      prev_rd_ready <= 1'b1;
      prev_rd_addr <= 48'b0;
      prev_rd_len <= {RD_LEN_W{1'b0}};
      prev_rd_tag <= {RD_TAG_W{1'b0}};
      rd_outstand <= 0;
      evt_hs <= 0;
    end else begin
      // (a) evt_valid && !evt_ready → next cycle evt_valid stays 1 and
      // evt_code is unchanged.
      if (prev_evt_valid && !prev_evt_ready) begin
        if (!evt_valid) begin
          $display("FAIL: evt_valid dropped under backpressure");
          errors = errors + 1;
        end
        if (evt_code !== prev_evt_code) begin
          $display("FAIL: evt_code changed under backpressure");
          errors = errors + 1;
        end
      end
      // (b) evt_valid implies evt_code != 0 (code 0 reserved).
      if (evt_valid && evt_code === {EVT_CODE_W{1'b0}}) begin
        $display("FAIL: evt_valid with reserved evt_code 0");
        errors = errors + 1;
      end
      // (d) whenever mem2host_rd_valid: len==RD_LEN_8B, tag==RD_TAG_ZERO;
      // at most one read outstanding (no new valid between accept and rsp).
      if (mem2host_rd_valid) begin
        if (mem2host_rd_len !== RD_LEN_8B[RD_LEN_W-1:0]) begin
          $display("FAIL: mem2host_rd_valid with len != RD_LEN_8B");
          errors = errors + 1;
        end
        if (mem2host_rd_tag !== RD_TAG_ZERO[RD_TAG_W-1:0]) begin
          $display("FAIL: mem2host_rd_valid with tag != RD_TAG_ZERO");
          errors = errors + 1;
        end
        if (rd_outstand != 0) begin
          $display("FAIL: second mem2host_rd_valid while outstanding");
          errors = errors + 1;
        end
      end
      // AP_TBLRD_REQ_HOLD: valid && !ready → next cycle valid stays 1
      // and addr/len/tag unchanged (SPEC §14 read-table interface).
      if (prev_rd_valid && !prev_rd_ready) begin
        if (!mem2host_rd_valid) begin
          $display("FAIL: AP_TBLRD_REQ_HOLD valid dropped under backpressure");
          errors = errors + 1;
        end
        if (mem2host_rd_addr !== prev_rd_addr) begin
          $display("FAIL: AP_TBLRD_REQ_HOLD addr changed under backpressure");
          errors = errors + 1;
        end
        if (mem2host_rd_len !== prev_rd_len) begin
          $display("FAIL: AP_TBLRD_REQ_HOLD len changed under backpressure");
          errors = errors + 1;
        end
        if (mem2host_rd_tag !== prev_rd_tag) begin
          $display("FAIL: AP_TBLRD_REQ_HOLD tag changed under backpressure");
          errors = errors + 1;
        end
      end
      if (mem2host_rd_valid && mem2host_rd_ready)
        rd_outstand <= 1;
      if (mem2host_rd_rsp_valid && mem2host_rd_rsp_ready)
        rd_outstand <= 0;
      if (evt_valid && evt_ready)
        evt_hs <= evt_hs + 1;
      prev_evt_valid <= evt_valid;
      prev_evt_ready <= evt_ready;
      prev_evt_code <= evt_code;
      prev_rd_valid <= mem2host_rd_valid;
      prev_rd_ready <= mem2host_rd_ready;
      prev_rd_addr <= mem2host_rd_addr;
      prev_rd_len <= mem2host_rd_len;
      prev_rd_tag <= mem2host_rd_tag;
      if (!legal_obs_st(tb_mem_ptw_obs_st)) begin
        $display("FAIL: tb_mem_ptw_obs_st illegal encoding %b", tb_mem_ptw_obs_st);
        errors = errors + 1;
      end
      if (tb_mem_ptw_obs_rd_pend !== mem2host_rd_valid) begin
        $display("FAIL: tb_mem_ptw_obs_rd_pend != mem2host_rd_valid");
        errors = errors + 1;
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
      mem2host_rd_ready = 1'b1;
      fill_ready = 1'b1;
      flt_ready = 1'b1;
      evt_ready = 1'b1;
    end
  endtask

  task wait_done;
    integer guard;
    begin
      guard = 0;
      while (!fill_valid && !flt_valid && !evt_valid && guard <= 80) begin
        tick;
        guard = guard + 1;
      end
      if (!fill_valid && !flt_valid && !evt_valid) begin
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
        $display("FAIL: expected fill, got flt xlat=%0d ill=%0d af=%0d evt=%0d",
                 flt_xlat, flt_illegal, flt_af, evt_valid);
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
          $display("FAIL: fill flags uxn/pxn/af got %0d/%0d/%0d",
                   fill_uxn, fill_pxn, fill_af);
          errors = errors + 1;
        end
        if (fill_ent_idx !== 4'h1 || fill_token_id !== 20'hABCDE) begin
          $display("FAIL: fill tag mismatch");
          errors = errors + 1;
        end
        if (flt_valid || evt_valid) begin
          $display("FAIL: fill with fault or event");
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
    input        want_af;
    begin
      wait_done;
      if (!flt_valid) begin
        $display("FAIL: expected fault, got fill=%0d evt=%0d pfn=%h",
                 fill_valid, evt_valid, fill_pfn);
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
        if (flt_af !== want_af) begin
          $display("FAIL: flt_af %0d != %0d", flt_af, want_af);
          errors = errors + 1;
        end
        if (fill_valid || evt_valid) begin
          $display("FAIL: fault also filled or raised event");
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

  task run_l3_page;
    input        af;
    input        affd;
    input [35:0] page;
    begin
      mem_reset;
      ctx_affd = affd;
      mem_push(pack_tb(1'b1, KIND_PAGE, 36'h00AB_CDEF, 3'd2, 2'b10, 1'b1, 1'b0,
                       af, 1'b0, ILL_NONE));
      start_walk({16'b0, page, 12'h000}, 6'd21);
    end
  endtask

  initial begin
    errors = 0;
    cycles = 0;
    saw_rd = 0;
    evt_hs = 0;
    evt_seen = 0;
    fill_seen = 0;
    rd_outstand = 0;
    first_rd_lat = 0;
    prev_evt_valid = 1'b0;
    prev_evt_ready = 1'b1;
    prev_evt_code = {EVT_CODE_W{1'b0}};
    prev_rd_valid = 1'b0;
    prev_rd_ready = 1'b1;
    prev_rd_addr = 48'b0;
    prev_rd_len = {RD_LEN_W{1'b0}};
    prev_rd_tag = {RD_TAG_W{1'b0}};
    rst_pyc = 1'b1;
    mem2host_rd_rsp_valid = 1'b0;
    mem2host_rd_rsp_data = 512'b0;
    mem2host_rd_rsp_tag = 4'b0;
    mem2host_rd_rsp_err = 1'b0;
    force_slot = 0;
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
    expect_fault(1'b1, 1'b0, ILL_NONE, 1'b0);
    $display("translation fault ok");

    // desc_v=1, kind=0: catch-all translation fault, no fill, back to idle.
    mem_reset;
    mem_push(pack_tb(1'b1, KIND_INVALID, 36'b0, 3'b0, 2'b0, 1'b0, 1'b0, 1'b0, 1'b0, ILL_NONE));
    start_walk({16'b0, 36'h0A00_0003, 12'h000}, 6'd39);
    expect_fault(1'b1, 1'b0, ILL_NONE, 1'b0);
    if (!req_ready) begin
      $display("FAIL: desc_v=1 kind=0 did not return to idle");
      errors = errors + 1;
    end
    $display("desc_v=1 kind=0 catch-all xlat fault ok");

    // Config-illegal: no fill, ill_cause forwarded.
    mem_reset;
    mem_push(pack_tb(1'b0, KIND_INVALID, 36'b0, 3'b0, 2'b0, 1'b0, 1'b0, 1'b0, 1'b1, ILL_HW_AD));
    start_walk({16'b0, 36'h0A00_0002, 12'h000}, 6'd39);
    expect_fault(1'b0, 1'b1, ILL_HW_AD, 1'b0);
    $display("config-illegal ok");

    // AF × AFFD.
    run_l3_page(1'b1, 1'b0, 36'h0123_4001);
    expect_fill(36'h0123_4001, 36'h00AB_CDEF, 8'h55, 2'b10, 1'b1, 1'b0, 1'b1);
    $display("AF=1 AFFD=0 fill ok");

    run_l3_page(1'b1, 1'b1, 36'h0123_4002);
    expect_fill(36'h0123_4002, 36'h00AB_CDEF, 8'h55, 2'b10, 1'b1, 1'b0, 1'b1);
    $display("AF=1 AFFD=1 fill ok");

    run_l3_page(1'b0, 1'b0, 36'h0123_4003);
    expect_fault(1'b0, 1'b0, ILL_NONE, 1'b1);
    $display("AF=0 AFFD=0 AF fault ok");

    run_l3_page(1'b0, 1'b1, 36'h0123_4004);
    expect_fill(36'h0123_4004, 36'h00AB_CDEF, 8'h55, 2'b10, 1'b1, 1'b0, 1'b0);
    $display("AF=0 AFFD=1 fill ok");
    ctx_affd = 1'b0;

    // 8 B select from the 512-bit beat at several low-address offsets.
    // L3 start: addr[5:3] follows page[2:0] when matt_ba[1:0]=0.
    begin : slot_walk
      integer s;
      for (s = 0; s < 8; s = s + 1) begin
        mem_reset;
        use_force_slot = 0;
        mem_push(pack_tb(1'b1, KIND_PAGE, 36'h00AB_CDEF, 3'd2, 2'b10, 1'b1, 1'b0,
                         1'b1, 1'b0, ILL_NONE));
        start_walk({16'b0, 36'h0100_0000 | {33'b0, s[2:0]}, 12'h000}, 6'd21);
        expect_fill(36'h0100_0000 | {33'b0, s[2:0]}, 36'h00AB_CDEF, 8'h55, 2'b10, 1'b1, 1'b0, 1'b1);
        $display("8B slot %0d ok", s);
      end
    end

    // AP_TBLRD_REQ_HOLD + first rd_valid 1 cycle after req accept.
    // Hold mem2host_rd_ready so the monitor sees valid/addr/len/tag hold.
    begin
      integer guard;
      integer lat;
      mem_reset;
      mem2host_rd_ready = 1'b0;
      first_rd_lat = 0;
      start_walk({16'b0, 36'h0123_4005, 12'h000}, 6'd21);
      lat = 1;
      guard = 0;
      while (!mem2host_rd_valid && guard <= 20) begin
        tick;
        lat = lat + 1;
        guard = guard + 1;
      end
      if (!mem2host_rd_valid) begin
        $display("FAIL: no table read after registered request");
        errors = errors + 1;
      end else begin
        first_rd_lat = lat;
        if (first_rd_lat != 1) begin
          $display("FAIL: first mem2host_rd_valid at +%0d (want +1)", first_rd_lat);
          errors = errors + 1;
        end
        repeat (3) tick;
        if (!mem2host_rd_valid) begin
          $display("FAIL: AP_TBLRD_REQ_HOLD valid dropped in hold window");
          errors = errors + 1;
        end
        mem2host_rd_ready = 1'b1;
        mem_push(pack_tb(1'b1, KIND_PAGE, 36'h00AB_CDEF, 3'd2, 2'b10, 1'b1, 1'b0,
                         1'b1, 1'b0, ILL_NONE));
        expect_fill(36'h0123_4005, 36'h00AB_CDEF, 8'h55, 2'b10, 1'b1, 1'b0, 1'b1);
        $display("AP_TBLRD_REQ_HOLD ok (first rd_valid +%0d)", first_rd_lat);
      end
      mem2host_rd_ready = 1'b1;
    end

    // (c) ctx_matt_wd=1 miss: no mem2host_rd_valid, no fill_valid,
    // exactly one event with evt_code == EVT_MATT_WD_MISS.
    // Hold evt_ready to exercise (a), then complete one handshake.
    begin
      integer guard;
      integer rd_before;
      integer hs_before;
      mem_reset;
      ctx_matt_wd = 1'b1;
      evt_ready = 1'b0;
      rd_before = saw_rd;
      hs_before = evt_hs;
      start_walk({16'b0, 36'h0A00_0008, 12'h000}, 6'd39);
      guard = 0;
      while (!evt_valid && guard <= 20) begin
        if (mem2host_rd_valid) begin
          $display("FAIL: MATT_WD issued table read");
          errors = errors + 1;
        end
        if (fill_valid) begin
          $display("FAIL: MATT_WD filled");
          errors = errors + 1;
        end
        tick;
        guard = guard + 1;
      end
      if (!evt_valid) begin
        $display("FAIL: MATT_WD produced no event");
        errors = errors + 1;
      end else begin
        if (evt_code !== EVT_MATT_WD_MISS[EVT_CODE_W-1:0]) begin
          $display("FAIL: evt_code != EVT_MATT_WD_MISS");
          errors = errors + 1;
        end
        if (fill_valid || flt_valid || mem2host_rd_valid) begin
          $display("FAIL: MATT_WD filled, faulted, or read");
          errors = errors + 1;
        end
        if (saw_rd !== rd_before) begin
          $display("FAIL: MATT_WD incremented table-read count");
          errors = errors + 1;
        end
        repeat (3) tick;
        if (!evt_valid || evt_code !== EVT_MATT_WD_MISS[EVT_CODE_W-1:0]) begin
          $display("FAIL: MATT_WD event did not hold");
          errors = errors + 1;
        end
        evt_ready = 1'b1;
        tick;
        if (evt_hs !== hs_before + 1) begin
          $display("FAIL: MATT_WD event count %0d", evt_hs - hs_before);
          errors = errors + 1;
        end
        tick;
        if (evt_valid) begin
          $display("FAIL: MATT_WD raised a second event");
          errors = errors + 1;
        end
      end
      evt_ready = 1'b1;
      ctx_matt_wd = 1'b0;
      $display("MATT_WD event ok");
    end

    if (errors == 0) begin
      $display("SMOKE PASS");
    end else begin
      $display("SMOKE FAIL errors=%0d", errors);
    end
    $finish;
  end
endmodule
