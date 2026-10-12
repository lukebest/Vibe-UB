// TP↔TA SVA bind (LAYER_CONTRACTS §3). Assert + cover only. No assume.
`default_nettype none

module tp_ta_assert (
  input wire        core_clk,
  input wire        rst_n,
  input wire        ta2tp_op_valid,
  input wire        ta2tp_op_ready,
  input wire [7:0]  ta2tp_opcode,
  input wire [15:0] ta2tp_tassn,
  input wire [1:0]  ta2tp_mode,
  input wire        ta2tp_bypass,
  input wire [159:0] ta2tp_data,
  input wire        ta2tp_valid,
  input wire        ta2tp_ready,
  input wire        ta2tp_sop,
  input wire        ta2tp_eop,
  input wire        tp2ta_done,
  input wire        tp2ta_fail,
  input wire [15:0] tp2ta_tassn,
  input wire        tp2ta_err,
  input wire        tp2ta_op_valid,
  input wire        tp2ta_op_ready,
  input wire        tp2ta_data_valid,
  input wire        tp2ta_data_ready,
  input wire        tp2ta_data_sop,
  input wire        tp2ta_data_eop,
  input wire        nw2tp_flush,
  input wire        nw_link_up,
  input wire        pending,
  input wire        done_fail_mutex,
  input wire        compact,
  input wire [3:0]  lph_cfg
);
  localparam integer FLIT_W = 160;
  localparam integer TASSN_W = 16;
  localparam integer CFG9 = 9;

  always @* begin
    a_flit_w: assert (FLIT_W == 160);
    a_tassn_w: assert (TASSN_W == 16);
    a_mutex_wire: assert (done_fail_mutex == !(tp2ta_done && tp2ta_fail));
    a_compact: assert (compact == (lph_cfg == CFG9[3:0]));
  end

  a_done_fail_mutex: assert property (@(posedge core_clk) disable iff (!rst_n)
    !(tp2ta_done && tp2ta_fail));

  a_term_pulse: assert property (@(posedge core_clk) disable iff (!rst_n)
    (tp2ta_done || tp2ta_fail) |-> done_fail_mutex);

  a_op_hold: assert property (@(posedge core_clk) disable iff (!rst_n)
    (ta2tp_op_valid && !ta2tp_op_ready) |=> (ta2tp_op_valid
      && ta2tp_opcode == $past(ta2tp_opcode)
      && ta2tp_tassn == $past(ta2tp_tassn)
      && ta2tp_bypass == $past(ta2tp_bypass)));

  a_data_hold: assert property (@(posedge core_clk) disable iff (!rst_n)
    (ta2tp_valid && !ta2tp_ready) |=> (ta2tp_valid
      && ta2tp_data == $past(ta2tp_data)
      && ta2tp_sop == $past(ta2tp_sop)
      && ta2tp_eop == $past(ta2tp_eop)));

  a_flush_clear: assert property (@(posedge core_clk) disable iff (!rst_n)
    nw2tp_flush |-> !pending);

  a_err_with_term: assert property (@(posedge core_clk) disable iff (!rst_n)
    tp2ta_err |-> (tp2ta_done || tp2ta_fail));

  a_bypass_cfg9: assert property (@(posedge core_clk) disable iff (!rst_n)
    (ta2tp_op_valid && ta2tp_bypass) |-> compact);

  c_submit_byp: cover property (@(posedge core_clk)
    rst_n && ta2tp_op_valid && ta2tp_op_ready && ta2tp_bypass && compact);

  c_op_hold: cover property (@(posedge core_clk)
    rst_n && ta2tp_op_valid && !ta2tp_op_ready);

  c_payload: cover property (@(posedge core_clk)
    rst_n && ta2tp_valid && ta2tp_ready && ta2tp_sop && ta2tp_eop);

  c_done: cover property (@(posedge core_clk)
    rst_n && tp2ta_done && !tp2ta_fail);

  c_fail: cover property (@(posedge core_clk)
    rst_n && tp2ta_fail && !tp2ta_done);

  c_deliver: cover property (@(posedge core_clk)
    rst_n && tp2ta_op_valid && tp2ta_op_ready);

  c_deliver_data: cover property (@(posedge core_clk)
    rst_n && tp2ta_data_valid && tp2ta_data_ready && tp2ta_data_sop && tp2ta_data_eop);

  c_flush_empty: cover property (@(posedge core_clk)
    rst_n && nw2tp_flush && !pending && !nw_link_up);

  c_full_cfg: cover property (@(posedge core_clk)
    rst_n && !compact && ta2tp_op_valid && !ta2tp_bypass);

  wire unused = |{ta2tp_mode, lph_cfg};
endmodule

bind tp_ta_harness tp_ta_assert u_tp_ta_assert (
  .core_clk          (core_clk),
  .rst_n             (rst_n),
  .ta2tp_op_valid    (ta2tp_op_valid),
  .ta2tp_op_ready    (ta2tp_op_ready),
  .ta2tp_opcode      (ta2tp_opcode),
  .ta2tp_tassn       (ta2tp_tassn),
  .ta2tp_mode        (ta2tp_mode),
  .ta2tp_bypass      (ta2tp_bypass),
  .ta2tp_data        (ta2tp_data),
  .ta2tp_valid       (ta2tp_valid),
  .ta2tp_ready       (ta2tp_ready),
  .ta2tp_sop         (ta2tp_sop),
  .ta2tp_eop         (ta2tp_eop),
  .tp2ta_done        (tp2ta_done),
  .tp2ta_fail        (tp2ta_fail),
  .tp2ta_tassn       (tp2ta_tassn),
  .tp2ta_err         (tp2ta_err),
  .tp2ta_op_valid    (tp2ta_op_valid),
  .tp2ta_op_ready    (tp2ta_op_ready),
  .tp2ta_data_valid  (tp2ta_data_valid),
  .tp2ta_data_ready  (tp2ta_data_ready),
  .tp2ta_data_sop    (tp2ta_data_sop),
  .tp2ta_data_eop    (tp2ta_data_eop),
  .nw2tp_flush       (nw2tp_flush),
  .nw_link_up        (nw_link_up),
  .pending           (pending),
  .done_fail_mutex   (done_fail_mutex),
  .compact           (compact),
  .lph_cfg           (lph_cfg)
);

`default_nettype wire
