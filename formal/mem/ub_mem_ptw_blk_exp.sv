// Independent expected 4 KB fill_pfn (contract §8 / Xia).
// Written in the formal harness from port-observed data only:
//   blk_base = ub_mem_ptw_desc_dec.desc_addr (public decoder port)
//   VA       = fill_page (PRODUCT port: latched req page VA[47:12])
//   L1 1GB   = {blk_base[35:18], VA[29:12]} = {blk_base[35:18], fill_page[17:0]}
//   L2 2MB   = {blk_base[35:9],  VA[20:12]} = {blk_base[35:9],  fill_page[8:0]}
// Does not reference leaf_pfn or any walker internal.

module ub_mem_ptw_blk_exp (
  input  wire        core_clk,
  input  wire        rst_pyc,
  input  wire        fill_valid,
  input  wire        fill_ready,
  input  wire [35:0] fill_pfn,
  input  wire [35:0] fill_page,
  input  wire        out_valid,
  input  wire [35:0] desc_addr,
  input  wire [1:0]  desc_kind,
  input  wire [1:0]  desc_lvl,
  output wire        l1_blk_leaf,
  output wire        l2_blk_leaf,
  output wire        l1_pfn_ok,
  output wire        l2_pfn_ok,
  output wire        l1_blk_fill,
  output wire        l2_blk_fill
);
  // One mapping block (contract §8 / Xia). Covers and a_l*_blk_pfn share it.
  localparam [1:0] KIND_BLOCK    = 2'd2;
  localparam [1:0] LVL_L1        = 2'd1;
  localparam [1:0] LVL_L2        = 2'd2;
  localparam integer L1_BASE_LSB = 18;
  localparam integer L2_BASE_LSB = 9;
  localparam integer L1_PAGE_W   = 18;  // VA[29:12]
  localparam integer L2_PAGE_W   = 9;   // VA[20:12]

  reg [35:0] f_blk_base;
  reg [1:0]  f_kind;
  reg [1:0]  f_lvl;

  initial begin
    f_blk_base = 36'd0;
    f_kind     = 2'd0;
    f_lvl      = 2'd0;
  end

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      f_blk_base <= 36'd0;
      f_kind     <= 2'd0;
      f_lvl      <= 2'd0;
    end else if (out_valid && !fill_valid) begin
      // Freeze on fill: decoder out_valid is $anyseq every cycle.
      f_blk_base <= desc_addr;
      f_kind     <= desc_kind;
      f_lvl      <= desc_lvl;
    end
  end

  wire [35:0] exp_l1_pfn = {f_blk_base[35:L1_BASE_LSB], fill_page[L1_PAGE_W-1:0]};
  wire [35:0] exp_l2_pfn = {f_blk_base[35:L2_BASE_LSB], fill_page[L2_PAGE_W-1:0]};

  // Fill presented for an L1 1 GB / L2 2 MB block leaf (kind/lvl from
  // the decoder ports latched before fill). Issued = presented & ready.
  assign l1_blk_leaf = fill_valid &&
                       (f_kind == KIND_BLOCK) && (f_lvl == LVL_L1);
  assign l2_blk_leaf = fill_valid &&
                       (f_kind == KIND_BLOCK) && (f_lvl == LVL_L2);
  assign l1_pfn_ok   = (fill_pfn == exp_l1_pfn);
  assign l2_pfn_ok   = (fill_pfn == exp_l2_pfn);
  assign l1_blk_fill = l1_blk_leaf && fill_ready && l1_pfn_ok;
  assign l2_blk_fill = l2_blk_leaf && fill_ready && l2_pfn_ok;
endmodule
