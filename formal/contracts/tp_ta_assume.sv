// TP↔TA contract assume — diagnostic task only (GATE-PRIVATE-PARENT-FREE).
`default_nettype none

module tp_ta_assume (
  input wire        core_clk,
  input wire        rst_n,
  input wire        ta2tp_op_valid,
  input wire        ta2tp_op_ready,
  input wire [7:0]  ta2tp_opcode,
  input wire [15:0] ta2tp_tassn,
  input wire        ta2tp_bypass,
  input wire [159:0] ta2tp_data,
  input wire        ta2tp_valid,
  input wire        ta2tp_ready,
  input wire        ta2tp_sop,
  input wire        ta2tp_eop,
  input wire        tp2ta_done,
  input wire        tp2ta_fail,
  input wire        nw2tp_flush,
  input wire        pending,
  input wire        compact
);
  am_done_fail: assume property (@(posedge core_clk) disable iff (!rst_n)
    !(tp2ta_done && tp2ta_fail));

  am_op_hold: assume property (@(posedge core_clk) disable iff (!rst_n)
    (ta2tp_op_valid && !ta2tp_op_ready) |=> (ta2tp_op_valid
      && ta2tp_opcode == $past(ta2tp_opcode)
      && ta2tp_tassn == $past(ta2tp_tassn)
      && ta2tp_bypass == $past(ta2tp_bypass)));

  am_data_hold: assume property (@(posedge core_clk) disable iff (!rst_n)
    (ta2tp_valid && !ta2tp_ready) |=> (ta2tp_valid
      && ta2tp_data == $past(ta2tp_data)
      && ta2tp_sop == $past(ta2tp_sop)
      && ta2tp_eop == $past(ta2tp_eop)));

  am_flush_clear: assume property (@(posedge core_clk) disable iff (!rst_n)
    nw2tp_flush |-> !pending);

  am_byp_cfg9: assume property (@(posedge core_clk) disable iff (!rst_n)
    (ta2tp_op_valid && ta2tp_bypass) |-> compact);
endmodule

bind tp_ta_harness tp_ta_assume u_tp_ta_assume (
  .core_clk       (core_clk),
  .rst_n          (rst_n),
  .ta2tp_op_valid (ta2tp_op_valid),
  .ta2tp_op_ready (ta2tp_op_ready),
  .ta2tp_opcode   (ta2tp_opcode),
  .ta2tp_tassn    (ta2tp_tassn),
  .ta2tp_bypass   (ta2tp_bypass),
  .ta2tp_data     (ta2tp_data),
  .ta2tp_valid    (ta2tp_valid),
  .ta2tp_ready    (ta2tp_ready),
  .ta2tp_sop      (ta2tp_sop),
  .ta2tp_eop      (ta2tp_eop),
  .tp2ta_done     (tp2ta_done),
  .tp2ta_fail     (tp2ta_fail),
  .nw2tp_flush    (nw2tp_flush),
  .pending        (pending),
  .compact        (compact)
);

`default_nettype wire
