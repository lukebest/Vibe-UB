// Independent expected 4 KB fill_pfn (contract §8 / Xia).
// Written in the formal harness from port-observed data only:
//   blk_base = ub_mem_ptw_desc_dec.desc_addr (public decoder port)
//   VA       = latched request uba
//   L1 1GB   = {blk_base[35:18], VA[29:12]}
//   L2 2MB   = {blk_base[35:9],  VA[20:12]}
// Does not reference leaf_pfn or any walker internal.

module ub_mem_ptw_blk_exp (
  input  wire        core_clk,
  input  wire        rst_pyc,
  input  wire        req_valid,
  input  wire        req_ready,
  input  wire [63:0] req_uba,
  input  wire        fill_valid,
  input  wire        fill_ready,
  input  wire [35:0] fill_pfn,
  input  wire        out_valid,
  input  wire [35:0] desc_addr,
  input  wire [1:0]  desc_kind,
  input  wire [1:0]  desc_lvl,
  output wire        l1_blk_fill,
  output wire        l2_blk_fill
);
  localparam [1:0] KIND_BLOCK = 2'd2;
  localparam [1:0] LVL_L1     = 2'd1;
  localparam [1:0] LVL_L2     = 2'd2;

  reg [35:0] f_blk_base;
  reg [63:0] f_va;
  reg [1:0]  f_kind;
  reg [1:0]  f_lvl;

  initial begin
    f_blk_base = 36'd0;
    f_va       = 64'd0;
    f_kind     = 2'd0;
    f_lvl      = 2'd0;
  end

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      f_blk_base <= 36'd0;
      f_va       <= 64'd0;
      f_kind     <= 2'd0;
      f_lvl      <= 2'd0;
    end else begin
      if (req_valid && req_ready)
        f_va <= req_uba;
      // Freeze on fill: decoder out_valid is $anyseq every cycle.
      if (out_valid && !fill_valid) begin
        f_blk_base <= desc_addr;
        f_kind     <= desc_kind;
        f_lvl      <= desc_lvl;
      end
    end
  end

  wire [35:0] exp_l1_pfn = {f_blk_base[35:18], f_va[29:12]};
  wire [35:0] exp_l2_pfn = {f_blk_base[35:9],  f_va[20:12]};

  assign l1_blk_fill = fill_valid && fill_ready &&
                       (f_kind == KIND_BLOCK) && (f_lvl == LVL_L1) &&
                       (fill_pfn == exp_l1_pfn);
  assign l2_blk_fill = fill_valid && fill_ready &&
                       (f_kind == KIND_BLOCK) && (f_lvl == LVL_L2) &&
                       (fill_pfn == exp_l2_pfn);
endmodule
