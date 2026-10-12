// contract_sha256: cecce26a25788bd351570b5d8e7fd47228d7526aa18ce994039f5a48df8e019e
// generated-by: scripts/gate/gen_private_stub.py
// formal-free cut: outputs are free inputs (anyseq)
module ub_mem_ptw_desc_dec (
  input core_clk,
  input rst_pyc,
  input in_valid,
  output in_ready,
  input [63:0] raw,
  input [1:0] desc_lvl,
  output out_valid,
  input out_ready,
  output desc_v,
  output [1:0] desc_kind,
  output [35:0] desc_addr,
  output [2:0] desc_attr_idx,
  output [1:0] desc_ap,
  output desc_uxn,
  output desc_pxn,
  output desc_af,
  output desc_illegal,
  output [3:0] desc_ill_cause
);
  (* anyseq *) logic in_ready_free;
  assign in_ready = in_ready_free;
  (* anyseq *) logic out_valid_free;
  assign out_valid = out_valid_free;
  (* anyseq *) logic desc_v_free;
  assign desc_v = desc_v_free;
  (* anyseq *) logic [1:0] desc_kind_free;
  assign desc_kind = desc_kind_free;
  (* anyseq *) logic [35:0] desc_addr_free;
  assign desc_addr = desc_addr_free;
  (* anyseq *) logic [2:0] desc_attr_idx_free;
  assign desc_attr_idx = desc_attr_idx_free;
  (* anyseq *) logic [1:0] desc_ap_free;
  assign desc_ap = desc_ap_free;
  (* anyseq *) logic desc_uxn_free;
  assign desc_uxn = desc_uxn_free;
  (* anyseq *) logic desc_pxn_free;
  assign desc_pxn = desc_pxn_free;
  (* anyseq *) logic desc_af_free;
  assign desc_af = desc_af_free;
  (* anyseq *) logic desc_illegal_free;
  assign desc_illegal = desc_illegal_free;
  (* anyseq *) logic [3:0] desc_ill_cause_free;
  assign desc_ill_cause = desc_ill_cause_free;
endmodule
