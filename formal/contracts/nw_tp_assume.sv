// NW↔TP contract assume — diagnostic task only
// (GATE-PRIVATE-PARENT-FREE: not in default bmc/cover/prove).
`default_nettype none

module nw_tp_assume (
  input wire        core_clk,
  input wire        rst_n,
  input wire        tp2nw_valid,
  input wire        tp2nw_ready,
  input wire [159:0] tp2nw_data,
  input wire        tp2nw_sop,
  input wire        tp2nw_eop,
  input wire        tp2nw_bypass,
  input wire        nw2tp_valid,
  input wire        nw2tp_ready,
  input wire [159:0] nw2tp_data,
  input wire        nw2tp_sop,
  input wire        nw2tp_eop,
  input wire        nw_link_up,
  input wire [3:0]  lph_cfg
);
  localparam integer CFG9 = 9;

  am_tx_hold: assume property (@(posedge core_clk) disable iff (!rst_n)
    (tp2nw_valid && !tp2nw_ready) |=> (tp2nw_valid
      && tp2nw_data == $past(tp2nw_data)
      && tp2nw_sop == $past(tp2nw_sop)
      && tp2nw_eop == $past(tp2nw_eop)
      && tp2nw_bypass == $past(tp2nw_bypass)));

  am_rx_hold: assume property (@(posedge core_clk) disable iff (!rst_n)
    (nw2tp_valid && !nw2tp_ready) |=> (nw2tp_valid
      && nw2tp_data == $past(nw2tp_data)
      && nw2tp_sop == $past(nw2tp_sop)
      && nw2tp_eop == $past(nw2tp_eop)));

  am_linkdown: assume property (@(posedge core_clk) disable iff (!rst_n)
    !nw_link_up |-> !tp2nw_valid);

  am_byp_cfg9: assume property (@(posedge core_clk) disable iff (!rst_n)
    (tp2nw_valid && tp2nw_bypass) |-> (lph_cfg == CFG9[3:0]));
endmodule

bind nw_tp_harness nw_tp_assume u_nw_tp_assume (
  .core_clk     (core_clk),
  .rst_n        (rst_n),
  .tp2nw_valid  (tp2nw_valid),
  .tp2nw_ready  (tp2nw_ready),
  .tp2nw_data   (tp2nw_data),
  .tp2nw_sop    (tp2nw_sop),
  .tp2nw_eop    (tp2nw_eop),
  .tp2nw_bypass (tp2nw_bypass),
  .nw2tp_valid  (nw2tp_valid),
  .nw2tp_ready  (nw2tp_ready),
  .nw2tp_data   (nw2tp_data),
  .nw2tp_sop    (nw2tp_sop),
  .nw2tp_eop    (nw2tp_eop),
  .nw_link_up   (nw_link_up),
  .lph_cfg      (lph_cfg)
);

`default_nettype wire
