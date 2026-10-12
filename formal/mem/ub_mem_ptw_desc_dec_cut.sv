// Formal cut of the private decoder leaf. Public ports only.
// Every output is $anyseq so properties must hold for ANY decode
// result. No descriptor bit-layout. This file is the only
// ub_mem_ptw_desc_dec definition the sby jobs read (never the
// PRODUCT stub, never a module from the walker file).

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
endmodule
