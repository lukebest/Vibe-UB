// Diagnostic cut of ub_mem_ptw_desc_dec. Same $anyseq ports as
// ub_mem_ptw_desc_dec_cut.sv, plus assumes that restrict the output
// *combination* to the public contract
// docs/arch/mem/contracts/ub_mem_ptw_desc_dec.md §7.
//
// Used ONLY by the untagged `bmc_contract` task. Default cover/bmc/prove
// still splice the unconstrained cut. a_st_legal is not weakened.
// Handshake / latency / input-class APs (HS_*, LAT1, XCLASS, ILL_AD,
// ILL_PRI, AF, BLOCK) are not assumed — those need raw bits or timing.

module ub_mem_ptw_desc_dec (
  input  wire        core_clk,
  input  wire        rst_pyc,
  input  wire        in_valid,
  input  wire [63:0] raw,
  input  wire [1:0]  desc_lvl,
  input  wire        out_ready,
  output wire        in_ready,
  output wire        out_valid,
  output wire        desc_v,
  output wire [1:0]  desc_kind,
  output wire [35:0] desc_addr,
  output wire [2:0]  desc_attr_idx,
  output wire [1:0]  desc_ap,
  output wire        desc_uxn,
  output wire        desc_pxn,
  output wire        desc_af,
  output wire        desc_illegal,
  output wire [3:0]  desc_ill_cause
);
  // One mapping block. Values from the contract port table / §3 / §7
  // and pycircuit/mem/lib/params.py (KIND_*, ILL_NONE).
  localparam [1:0] KIND_INVALID = 2'd0;
  localparam [1:0] KIND_TABLE   = 2'd1;
  localparam [1:0] KIND_BLOCK   = 2'd2;
  localparam [1:0] KIND_PAGE    = 2'd3;
  localparam [3:0] ILL_NONE     = 4'd0;

  assign in_ready       = $anyseq;
  assign out_valid      = $anyseq;
  assign desc_v         = $anyseq;
  assign desc_kind      = $anyseq;
  assign desc_addr      = $anyseq;
  assign desc_attr_idx  = $anyseq;
  assign desc_ap        = $anyseq;
  assign desc_uxn       = $anyseq;
  assign desc_pxn       = $anyseq;
  assign desc_af        = $anyseq;
  assign desc_illegal   = $anyseq;
  assign desc_ill_cause = $anyseq;

  // Output-combination assumes. Applied every cycle (covers reset §6
  // and the out_valid beat that the walker samples as dec_fire).
  always @* begin
    // AP_PTW_ILL_EQ: desc_illegal == (desc_ill_cause != 0).
    assume (desc_illegal == (desc_ill_cause != ILL_NONE));

    // AP_PTW_ILL_ZERO: illegal beat ⇒ all other decode fields are 0.
    assume (
      !desc_illegal || (
        !desc_v &&
        (desc_kind == KIND_INVALID) &&
        (desc_addr == 36'd0) &&
        (desc_attr_idx == 3'd0) &&
        (desc_ap == 2'd0) &&
        !desc_uxn &&
        !desc_pxn &&
        !desc_af
      )
    );

    // AP_PTW_FAULT: translation-fault encoding
    // (desc_v=0, !illegal) ⇒ kind=invalid, ill_cause=ILL_NONE.
    assume (
      !(!desc_illegal && !desc_v) || (
        (desc_kind == KIND_INVALID) &&
        (desc_ill_cause == ILL_NONE)
      )
    );

    // AP_PTW_KIND: !illegal ⇒ kind ∈ {0,1,2,3}
    // (invalid / table / block / page). 2-bit field, written explicitly.
    assume (
      desc_illegal ||
      (desc_kind == KIND_INVALID) ||
      (desc_kind == KIND_TABLE) ||
      (desc_kind == KIND_BLOCK) ||
      (desc_kind == KIND_PAGE)
    );

    // AP_PTW_KIND_LVL (output half): a valid leaf/table result is
    // desc_v=1, !illegal, kind ∈ {table, block, page}. kind=invalid
    // with desc_v=1 is not a §3 cell (that cell is AP_PTW_FAULT).
    assume (
      !(desc_v && !desc_illegal) || (
        (desc_kind == KIND_TABLE) ||
        (desc_kind == KIND_BLOCK) ||
        (desc_kind == KIND_PAGE)
      )
    );
  end
endmodule
