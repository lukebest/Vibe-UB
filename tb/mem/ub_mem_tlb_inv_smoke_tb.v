// Directed PRODUCT smoke: hit / miss / fill / overwrite / replace / bypass /
// inv-all / inv-cond. Uses the lint placeholder for ub_cmn_mem_1r1w_d64w109.
// Formal one-hot / no-duplicate assertions are owned by 验证-C (no formal/mem/).

`timescale 1ns/1ps

module ub_mem_tlb_inv_smoke_tb;
  localparam integer TAG_W = 60;
  localparam integer DATA_W = 49;
  localparam integer WORD_W = 109;

  reg         core_clk;
  reg         rst_pyc;

  reg         lk_valid;
  reg  [3:0]  lk_ent_idx;
  reg  [19:0] lk_token_id;
  reg  [35:0] lk_page;
  wire        lk_ready;
  wire        lk_rsp_valid;
  wire        lk_hit;
  wire [35:0] xlat_pfn;
  wire [7:0]  xlat_attr;
  wire [1:0]  xlat_ap;
  wire        xlat_uxn;
  wire        xlat_pxn;
  wire        xlat_af;

  reg         fill_valid;
  reg  [3:0]  fill_ent_idx;
  reg  [19:0] fill_token_id;
  reg  [35:0] fill_page;
  reg  [35:0] fill_pfn;
  reg  [7:0]  fill_attr;
  reg  [1:0]  fill_ap;
  reg         fill_uxn;
  reg         fill_pxn;
  reg         fill_af;
  wire        fill_ready;

  wire        inv2tlb_all_valid;
  wire        inv2tlb_all_ready;
  wire        inv2tlb_scan_valid;
  wire        inv2tlb_scan_ready;
  wire [5:0]  inv2tlb_scan_set;
  wire [3:0]  inv2tlb_scan_ent_idx;
  wire [19:0] inv2tlb_scan_token_id;
  wire        inv2tlb_scan_match_ent;
  wire        inv2tlb_scan_match_tok;
  wire        tlb2inv_scan_done;
  wire        tlb_busy;

  reg         cmd_valid;
  reg  [1:0]  cmd_op;
  reg  [3:0]  cmd_ent_idx;
  reg  [19:0] cmd_token_id;
  reg         cmd_match_ent;
  reg         cmd_match_tok;
  reg         done_ready;
  reg         miss_pend;
  wire        cmd_ready;
  wire        done_valid;
  wire        inv_busy;

  integer errors;
  integer cycles;

  ub_mem_tlb u_tlb (
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
    .busy(tlb_busy)
  );

  ub_mem_inv u_inv (
    .core_clk(core_clk),
    .rst_pyc(rst_pyc),
    .cmd_valid(cmd_valid),
    .cmd_op(cmd_op),
    .cmd_ent_idx(cmd_ent_idx),
    .cmd_token_id(cmd_token_id),
    .cmd_match_ent(cmd_match_ent),
    .cmd_match_tok(cmd_match_tok),
    .done_ready(done_ready),
    .miss_pend(miss_pend),
    .inv2tlb_all_ready(inv2tlb_all_ready),
    .inv2tlb_scan_ready(inv2tlb_scan_ready),
    .tlb2inv_scan_done(tlb2inv_scan_done),
    .cmd_ready(cmd_ready),
    .done_valid(done_valid),
    .inv2tlb_all_valid(inv2tlb_all_valid),
    .inv2tlb_scan_valid(inv2tlb_scan_valid),
    .inv2tlb_scan_set(inv2tlb_scan_set),
    .inv2tlb_scan_ent_idx(inv2tlb_scan_ent_idx),
    .inv2tlb_scan_token_id(inv2tlb_scan_token_id),
    .inv2tlb_scan_match_ent(inv2tlb_scan_match_ent),
    .inv2tlb_scan_match_tok(inv2tlb_scan_match_tok),
    .busy(inv_busy)
  );

  initial begin
    core_clk = 1'b0;
    forever #5 core_clk = ~core_clk;
  end

  task tick;
    begin
      @(posedge core_clk);
      cycles = cycles + 1;
      if (cycles > 20000) begin
        $display("TIMEOUT");
        errors = errors + 1;
        $finish;
      end
    end
  endtask

  task idle_bus;
    begin
      lk_valid = 1'b0;
      fill_valid = 1'b0;
      cmd_valid = 1'b0;
      lk_ent_idx = 4'h0;
      lk_token_id = 20'h0;
      lk_page = 36'h0;
      fill_ent_idx = 4'h0;
      fill_token_id = 20'h0;
      fill_page = 36'h0;
      fill_pfn = 36'h0;
      fill_attr = 8'h0;
      fill_ap = 2'h0;
      fill_uxn = 1'b0;
      fill_pxn = 1'b0;
      fill_af = 1'b0;
      cmd_op = 2'h0;
      cmd_ent_idx = 4'h0;
      cmd_token_id = 20'h0;
      cmd_match_ent = 1'b0;
      cmd_match_tok = 1'b0;
      done_ready = 1'b1;
      miss_pend = 1'b0;
    end
  endtask

  task wait_fill_ready;
    integer guard;
    begin
      guard = 0;
      while (!fill_ready) begin
        tick;
        guard = guard + 1;
        if (guard > 64) begin
          $display("FAIL: fill_ready timeout");
          errors = errors + 1;
          disable wait_fill_ready;
        end
      end
    end
  endtask

  task do_fill;
    input [3:0]  ent;
    input [19:0] tok;
    input [35:0] page;
    input [35:0] pfn;
    input [7:0]  attr;
    input [1:0]  ap;
    input        uxn;
    input        pxn;
    input        af;
    begin
      wait_fill_ready;
      fill_valid = 1'b1;
      fill_ent_idx = ent;
      fill_token_id = tok;
      fill_page = page;
      fill_pfn = pfn;
      fill_attr = attr;
      fill_ap = ap;
      fill_uxn = uxn;
      fill_pxn = pxn;
      fill_af = af;
      tick;
      fill_valid = 1'b0;
      // FILL_CMP then FILL_WB then IDLE (lookup may overlap FILL_WB).
      tick;
      tick;
      tick;
    end
  endtask

  task do_lookup;
    input [3:0]  ent;
    input [19:0] tok;
    input [35:0] page;
    output       hit;
    output [35:0] pfn;
    integer guard;
    begin
      guard = 0;
      while (!lk_ready) begin
        tick;
        guard = guard + 1;
        if (guard > 64) begin
          $display("FAIL: lk_ready timeout");
          errors = errors + 1;
          hit = 1'b0;
          pfn = 36'h0;
          disable do_lookup;
        end
      end
      lk_valid = 1'b1;
      lk_ent_idx = ent;
      lk_token_id = tok;
      lk_page = page;
      tick;
      lk_valid = 1'b0;
      if (!lk_rsp_valid) begin
        $display("FAIL: lookup response missing at request+1");
        errors = errors + 1;
      end
      hit = lk_hit;
      pfn = xlat_pfn;
    end
  endtask

  task expect_hit;
    input [3:0]  ent;
    input [19:0] tok;
    input [35:0] page;
    input [35:0] pfn_exp;
    input [7:0]  attr_exp;
    input [1:0]  ap_exp;
    input        uxn_exp;
    input        pxn_exp;
    input        af_exp;
    input [8*32-1:0] name;
    reg          hit;
    reg [35:0]   pfn;
    begin
      do_lookup(ent, tok, page, hit, pfn);
      if (!hit) begin
        $display("FAIL %0s: expected hit", name);
        errors = errors + 1;
      end else if (pfn !== pfn_exp) begin
        $display("FAIL %0s: pfn got %h exp %h", name, pfn, pfn_exp);
        errors = errors + 1;
      end else if (xlat_attr !== attr_exp || xlat_ap !== ap_exp ||
                   xlat_uxn !== uxn_exp || xlat_pxn !== pxn_exp ||
                   xlat_af !== af_exp) begin
        $display("FAIL %0s: xlat fields mismatch", name);
        errors = errors + 1;
      end else begin
        $display("PASS %0s", name);
      end
    end
  endtask

  task expect_miss;
    input [3:0]  ent;
    input [19:0] tok;
    input [35:0] page;
    input [8*32-1:0] name;
    reg          hit;
    reg [35:0]   pfn;
    begin
      do_lookup(ent, tok, page, hit, pfn);
      if (hit) begin
        $display("FAIL %0s: expected miss, pfn=%h", name, pfn);
        errors = errors + 1;
      end else begin
        $display("PASS %0s", name);
      end
    end
  endtask

  task do_cmd;
    input [1:0]  op;
    input [3:0]  ent;
    input [19:0] tok;
    input        me;
    input        mt;
    integer guard;
    begin
      guard = 0;
      while (!cmd_ready) begin
        tick;
        guard = guard + 1;
        if (guard > 64) begin
          $display("FAIL: cmd_ready timeout");
          errors = errors + 1;
          disable do_cmd;
        end
      end
      cmd_valid = 1'b1;
      cmd_op = op;
      cmd_ent_idx = ent;
      cmd_token_id = tok;
      cmd_match_ent = me;
      cmd_match_tok = mt;
      tick;
      cmd_valid = 1'b0;
      guard = 0;
      while (!done_valid) begin
        tick;
        guard = guard + 1;
        if (guard > 256) begin
          $display("FAIL: inv done timeout op=%0d", op);
          errors = errors + 1;
          disable do_cmd;
        end
      end
      tick;
    end
  endtask

  initial begin
    errors = 0;
    cycles = 0;
    rst_pyc = 1'b1;
    idle_bus;
    repeat (4) tick;
    rst_pyc = 1'b0;
    tick;

    // Miss after reset.
    expect_miss(4'h1, 20'h00011, 36'h0000_1000, "miss_reset");

    // Fill then hit.
    do_fill(4'h1, 20'h00011, 36'h0000_1000, 36'h00AA_0000, 8'h5A, 2'b10, 1'b1, 1'b0, 1'b1);
    expect_hit(4'h1, 20'h00011, 36'h0000_1000, 36'h00AA_0000, 8'h5A, 2'b10, 1'b1, 1'b0, 1'b1, "hit_after_fill");

    // Overwrite matching tag (no duplicate). New PFN must win.
    do_fill(4'h1, 20'h00011, 36'h0000_1000, 36'h00BB_0000, 8'hA5, 2'b01, 1'b0, 1'b1, 1'b0);
    expect_hit(4'h1, 20'h00011, 36'h0000_1000, 36'h00BB_0000, 8'hA5, 2'b01, 1'b0, 1'b1, 1'b0, "overwrite_same_tag");

    // Four ways in one set (page[5:0] ^ tok[5:0] shared), then a fifth replaces.
    do_fill(4'h2, 20'h00020, 36'h0000_2000, 36'h1000_0001, 8'h01, 2'b00, 1'b0, 1'b0, 1'b1);
    do_fill(4'h2, 20'h00020, 36'h0001_2000, 36'h1000_0002, 8'h02, 2'b00, 1'b0, 1'b0, 1'b1);
    do_fill(4'h2, 20'h00020, 36'h0002_2000, 36'h1000_0003, 8'h03, 2'b00, 1'b0, 1'b0, 1'b1);
    do_fill(4'h2, 20'h00020, 36'h0003_2000, 36'h1000_0004, 8'h04, 2'b00, 1'b0, 1'b0, 1'b1);
    expect_hit(4'h2, 20'h00020, 36'h0000_2000, 36'h1000_0001, 8'h01, 2'b00, 1'b0, 1'b0, 1'b1, "way0_before_replace");
    do_fill(4'h2, 20'h00020, 36'h0004_2000, 36'h1000_0005, 8'h05, 2'b00, 1'b0, 1'b0, 1'b1);
    expect_hit(4'h2, 20'h00020, 36'h0004_2000, 36'h1000_0005, 8'h05, 2'b00, 1'b0, 1'b0, 1'b1, "fifth_fill_hits");
    expect_miss(4'h2, 20'h00020, 36'h0000_2000, "replaced_way_miss");
    expect_hit(4'h2, 20'h00020, 36'h0001_2000, 36'h1000_0002, 8'h02, 2'b00, 1'b0, 1'b0, 1'b1, "way1_survives");

    // Bypass: accept lookup in FILL_WB (write + registered read same cycle).
    wait_fill_ready;
    fill_valid = 1'b1;
    fill_ent_idx = 4'h3;
    fill_token_id = 20'h00033;
    fill_page = 36'h0000_3000;
    fill_pfn = 36'h00CC_0000;
    fill_attr = 8'h11;
    fill_ap = 2'b11;
    fill_uxn = 1'b0;
    fill_pxn = 1'b0;
    fill_af = 1'b1;
    tick; // accept -> FILL_CMP
    fill_valid = 1'b0;
    tick; // FILL_CMP -> FILL_WB; lookup ready again
    if (!lk_ready) begin
      $display("FAIL bypass: lk_ready low in FILL_WB");
      errors = errors + 1;
    end
    lk_valid = 1'b1;
    lk_ent_idx = 4'h3;
    lk_token_id = 20'h00033;
    lk_page = 36'h0000_3000;
    tick; // FILL_WB write + lookup read; rsp next is this cycle? lk accepted this cycle
    lk_valid = 1'b0;
    // Response is request+1, which is this next posedge already happened...
    // The tick above sampled lk_rsp for the NEW lookup at the posedge where
    // lk_pend becomes 1. Need one more cycle? lk_pend is registered: accept
    // this posedge, rsp next posedge.
    if (!lk_rsp_valid || !lk_hit || xlat_pfn !== 36'h00CC_0000) begin
      // maybe need one more tick
      tick;
    end
    if (!lk_rsp_valid || !lk_hit || xlat_pfn !== 36'h00CC_0000) begin
      $display("FAIL bypass: hit=%0d pfn=%h", lk_hit, xlat_pfn);
      errors = errors + 1;
    end else begin
      $display("PASS bypass_fill_wb");
    end
    tick;

    // INV_ALL (op=0): one-cycle valid clear.
    do_cmd(2'd0, 4'h0, 20'h0, 1'b0, 1'b0);
    expect_miss(4'h1, 20'h00011, 36'h0000_1000, "inv_all_clears");
    expect_miss(4'h3, 20'h00033, 36'h0000_3000, "inv_all_clears_byp");

    // Refill two ENT_IDX values, then INV_COND on one ENT_IDX.
    do_fill(4'h4, 20'h00044, 36'h0000_4000, 36'h00D0_0000, 8'h20, 2'b00, 1'b0, 1'b0, 1'b1);
    do_fill(4'h5, 20'h00055, 36'h0000_5000, 36'h00E0_0000, 8'h21, 2'b00, 1'b0, 1'b0, 1'b1);
    do_cmd(2'd1, 4'h4, 20'h0, 1'b1, 1'b0);
    expect_miss(4'h4, 20'h00044, 36'h0000_4000, "inv_cond_ent4");
    expect_hit(4'h5, 20'h00055, 36'h0000_5000, 36'h00E0_0000, 8'h21, 2'b00, 1'b0, 1'b0, 1'b1, "inv_cond_spares_ent5");

    // SYNC (op=2) with miss_pend=0.
    do_cmd(2'd2, 4'h0, 20'h0, 1'b0, 1'b0);
    $display("PASS sync");

    if (errors == 0) begin
      $display("SMOKE PASS");
      $finish;
    end else begin
      $display("SMOKE FAIL errors=%0d", errors);
      $finish;
    end
  end
endmodule
