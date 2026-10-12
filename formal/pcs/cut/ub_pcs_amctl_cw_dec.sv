// contract_sha256: 646c76d8c254cedafe0b1dbb2a9e826205e4e84d7692cdd62b0f3bc8f314eb1d
// generated-by: scripts/gate/gen_private_stub.py
// formal-free cut: outputs are free inputs (anyseq)
module ub_pcs_amctl_cw_dec (
  input core_clk,
  input rst_pyc,
  input [31:0] word,
  input word_vld,
  output end_hit,
  output amctl_vld,
  output end_ok,
  output [3:0] lid,
  output lid_ok,
  output [2:0] ctrl_type,
  output ctrl_type_ok,
  output [3:0] ctrl_detail,
  output ctrl_detail_ok
);
  (* anyseq *) logic end_hit_free;
  assign end_hit = end_hit_free;
  (* anyseq *) logic amctl_vld_free;
  assign amctl_vld = amctl_vld_free;
  (* anyseq *) logic end_ok_free;
  assign end_ok = end_ok_free;
  (* anyseq *) logic [3:0] lid_free;
  assign lid = lid_free;
  (* anyseq *) logic lid_ok_free;
  assign lid_ok = lid_ok_free;
  (* anyseq *) logic [2:0] ctrl_type_free;
  assign ctrl_type = ctrl_type_free;
  (* anyseq *) logic ctrl_type_ok_free;
  assign ctrl_type_ok = ctrl_type_ok_free;
  (* anyseq *) logic [3:0] ctrl_detail_free;
  assign ctrl_detail = ctrl_detail_free;
  (* anyseq *) logic ctrl_detail_ok_free;
  assign ctrl_detail_ok = ctrl_detail_ok_free;
endmodule
