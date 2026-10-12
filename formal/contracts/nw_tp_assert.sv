// NW↔TP SVA bind (LAYER_CONTRACTS §2). Assert + cover only.
// No assume (GATE-PRIVATE-PARENT-FREE / verif_gate.md §11).
`default_nettype none

module nw_tp_assert (
  input wire        core_clk,
  input wire        rst_n,
  input wire        tp2nw_valid,
  input wire        tp2nw_ready,
  input wire [159:0] tp2nw_data,
  input wire        tp2nw_sop,
  input wire        tp2nw_eop,
  input wire [3:0]  tp2nw_sl,
  input wire [2:0]  tp2nw_nlp,
  input wire        tp2nw_bypass,
  input wire        nw2tp_valid,
  input wire        nw2tp_ready,
  input wire [159:0] nw2tp_data,
  input wire        nw2tp_sop,
  input wire        nw2tp_eop,
  input wire        nw2tp_err,
  input wire        nw2tp_flush,
  input wire        nw_link_up,
  input wire [3:0]  lph_cfg,
  input wire [23:0] psn,
  input wire [23:0] psn_n,
  input wire [15:0] elapsed,
  input wire        timed_out,
  input wire        compact,
  input wire [4:0]  btah_bytes,
  input wire [4:0]  maetah_bytes
);
  localparam integer FLIT_W = 160;
  localparam integer CFG9 = 9;
  localparam integer RTPH_BYTES = 16;
  localparam integer LPH_NTH_BYTES = 12;
  localparam integer TIMEOUT_DEF = 323;

  // Widths / header lens (combinational; LAYER_CONTRACTS §2, UB-TP §6.2, UB-TA §7.2)
  always @* begin
    a_flit_w: assert (FLIT_W == 160);
    a_rtph: assert (RTPH_BYTES == 16);
    a_lph_nth: assert (LPH_NTH_BYTES == 12);
    a_timeout_def: assert (TIMEOUT_DEF == 323);
    a_cfg9_compact: assert (compact == (lph_cfg == CFG9[3:0]));
    a_btah_len: assert (compact ? (btah_bytes == 5'd4) : (btah_bytes == 5'd8));
    a_maetah_len: assert (compact ? (maetah_bytes == 5'd12) : (maetah_bytes == 5'd16));
    a_timeout_rel: assert (timed_out == (elapsed >= TIMEOUT_DEF[15:0]));
  end

  // Handshake hold (SPEC §3.1 / LAYER_CONTRACTS §2)
  a_tx_hold: assert property (@(posedge core_clk) disable iff (!rst_n)
    (tp2nw_valid && !tp2nw_ready) |=> (tp2nw_valid
      && tp2nw_data == $past(tp2nw_data)
      && tp2nw_sop == $past(tp2nw_sop)
      && tp2nw_eop == $past(tp2nw_eop)
      && tp2nw_bypass == $past(tp2nw_bypass)));

  a_rx_hold: assert property (@(posedge core_clk) disable iff (!rst_n)
    (nw2tp_valid && !nw2tp_ready) |=> (nw2tp_valid
      && nw2tp_data == $past(nw2tp_data)
      && nw2tp_sop == $past(nw2tp_sop)
      && nw2tp_eop == $past(nw2tp_eop)));

  // link down: no TX fire
  a_linkdown_no_tx: assert property (@(posedge core_clk) disable iff (!rst_n)
    !nw_link_up |-> !(tp2nw_valid && tp2nw_ready));

  // nw2tp_err only meaningful on valid&&eop — harness keeps err 0 unless eop
  a_err_eop: assert property (@(posedge core_clk) disable iff (!rst_n)
    nw2tp_err |-> (nw2tp_valid && nw2tp_eop));

  // bypass only with CFG9
  a_byp_cfg9: assert property (@(posedge core_clk) disable iff (!rst_n)
    (tp2nw_valid && tp2nw_bypass) |-> (lph_cfg == CFG9[3:0]));

  // PSN 24-bit wrap
  a_psn_inc: assert property (@(posedge core_clk) disable iff (!rst_n)
    psn_n == (psn + 24'd1));

  a_flush_no_new: assert property (@(posedge core_clk) disable iff (!rst_n)
    nw2tp_flush |-> !tp2nw_valid);

  // Covers — deepest intended ~cyc 14 (GATE-FORMAL-DEPTH rule 3)
  c_tx_sop_eop: cover property (@(posedge core_clk)
    rst_n && tp2nw_valid && tp2nw_ready && tp2nw_sop && tp2nw_eop && tp2nw_bypass);

  c_tx_hold: cover property (@(posedge core_clk)
    rst_n && tp2nw_valid && !tp2nw_ready);

  c_tx_two_beat: cover property (@(posedge core_clk)
    rst_n && tp2nw_valid && tp2nw_ready && tp2nw_eop && !tp2nw_sop);

  c_rx_fire: cover property (@(posedge core_clk)
    rst_n && nw2tp_valid && nw2tp_ready && nw2tp_sop && nw2tp_eop);

  c_link_down: cover property (@(posedge core_clk)
    rst_n && !nw_link_up && nw2tp_flush);

  c_timeout_322: cover property (@(posedge core_clk)
    rst_n && elapsed == 16'd322 && !timed_out);

  c_timeout_323: cover property (@(posedge core_clk)
    rst_n && elapsed == 16'd323 && timed_out);

  c_psn_wrap: cover property (@(posedge core_clk)
    rst_n && psn == 24'hFFFFFF && psn_n == 24'h000000);

  c_full_hdr: cover property (@(posedge core_clk)
    rst_n && !compact && btah_bytes == 5'd8 && maetah_bytes == 5'd16);

  // silence unused
  wire unused = |{tp2nw_sl, tp2nw_nlp, nw2tp_data};
endmodule

bind nw_tp_harness nw_tp_assert u_nw_tp_assert (
  .core_clk      (core_clk),
  .rst_n         (rst_n),
  .tp2nw_valid   (tp2nw_valid),
  .tp2nw_ready   (tp2nw_ready),
  .tp2nw_data    (tp2nw_data),
  .tp2nw_sop     (tp2nw_sop),
  .tp2nw_eop     (tp2nw_eop),
  .tp2nw_sl      (tp2nw_sl),
  .tp2nw_nlp     (tp2nw_nlp),
  .tp2nw_bypass  (tp2nw_bypass),
  .nw2tp_valid   (nw2tp_valid),
  .nw2tp_ready   (nw2tp_ready),
  .nw2tp_data    (nw2tp_data),
  .nw2tp_sop     (nw2tp_sop),
  .nw2tp_eop     (nw2tp_eop),
  .nw2tp_err     (nw2tp_err),
  .nw2tp_flush   (nw2tp_flush),
  .nw_link_up    (nw_link_up),
  .lph_cfg       (lph_cfg),
  .psn           (psn),
  .psn_n         (psn_n),
  .elapsed       (elapsed),
  .timed_out     (timed_out),
  .compact       (compact),
  .btah_bytes    (btah_bytes),
  .maetah_bytes  (maetah_bytes)
);

`default_nettype wire
