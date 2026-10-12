// NW↔TP SVA bind (LAYER_CONTRACTS §2). Assert + cover only.
// Immediate asserts: Yosys 0.33 has no concurrent `assert property (@...)`.
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

  always @* begin
    a_flit_w: assert (FLIT_W == 160);
    a_rtph: assert (RTPH_BYTES == 16);
    a_lph_nth: assert (LPH_NTH_BYTES == 12);
    a_timeout_def: assert (TIMEOUT_DEF == 323);
    a_cfg9_compact: assert (compact == (lph_cfg == CFG9[3:0]));
    a_btah_len: assert (compact ? (btah_bytes == 5'd4) : (btah_bytes == 5'd8));
    a_maetah_len: assert (compact ? (maetah_bytes == 5'd12) : (maetah_bytes == 5'd16));
    a_timeout_rel: assert (timed_out == (elapsed >= TIMEOUT_DEF[15:0]));
    a_psn_inc: assert (psn_n == (psn + 24'd1));
  end

  reg        past_rst_n;
  reg        past_tx_v, past_tx_r, past_tx_sop, past_tx_eop, past_tx_byp;
  reg [159:0] past_tx_data;
  reg        past_rx_v, past_rx_r, past_rx_sop, past_rx_eop;
  reg [159:0] past_rx_data;

  initial begin
    past_rst_n   = 1'b0;
    past_tx_v    = 1'b0;
    past_tx_r    = 1'b0;
    past_tx_data = 160'd0;
    past_tx_sop  = 1'b0;
    past_tx_eop  = 1'b0;
    past_tx_byp  = 1'b0;
    past_rx_v    = 1'b0;
    past_rx_r    = 1'b0;
    past_rx_data = 160'd0;
    past_rx_sop  = 1'b0;
    past_rx_eop  = 1'b0;
  end

  always @(posedge core_clk) begin
    past_rst_n   <= rst_n;
    past_tx_v    <= tp2nw_valid;
    past_tx_r    <= tp2nw_ready;
    past_tx_data <= tp2nw_data;
    past_tx_sop  <= tp2nw_sop;
    past_tx_eop  <= tp2nw_eop;
    past_tx_byp  <= tp2nw_bypass;
    past_rx_v    <= nw2tp_valid;
    past_rx_r    <= nw2tp_ready;
    past_rx_data <= nw2tp_data;
    past_rx_sop  <= nw2tp_sop;
    past_rx_eop  <= nw2tp_eop;
  end

  always @(posedge core_clk) begin
    if (rst_n) begin
      if (!nw_link_up)
        a_linkdown_no_tx: assert (!(tp2nw_valid && tp2nw_ready));
      if (nw2tp_err)
        a_err_eop: assert (nw2tp_valid && nw2tp_eop);
      if (tp2nw_valid && tp2nw_bypass)
        a_byp_cfg9: assert (lph_cfg == CFG9[3:0]);
      if (nw2tp_flush)
        a_flush_no_new: assert (!tp2nw_valid);
    end
    if (past_rst_n && past_tx_v && !past_tx_r) begin
      a_tx_hold_v: assert (tp2nw_valid);
      a_tx_hold_d: assert (tp2nw_data == past_tx_data);
      a_tx_hold_s: assert (tp2nw_sop == past_tx_sop);
      a_tx_hold_e: assert (tp2nw_eop == past_tx_eop);
      a_tx_hold_b: assert (tp2nw_bypass == past_tx_byp);
    end
    if (past_rst_n && past_rx_v && !past_rx_r) begin
      a_rx_hold_v: assert (nw2tp_valid);
      a_rx_hold_d: assert (nw2tp_data == past_rx_data);
      a_rx_hold_s: assert (nw2tp_sop == past_rx_sop);
      a_rx_hold_e: assert (nw2tp_eop == past_rx_eop);
    end
  end

  always @(posedge core_clk) begin
    c_tx_sop_eop: cover (rst_n && tp2nw_valid && tp2nw_ready && tp2nw_sop && tp2nw_eop && tp2nw_bypass);
    c_tx_hold: cover (rst_n && tp2nw_valid && !tp2nw_ready);
    c_tx_two_beat: cover (rst_n && tp2nw_valid && tp2nw_ready && tp2nw_eop && !tp2nw_sop);
    c_rx_fire: cover (rst_n && nw2tp_valid && nw2tp_ready && nw2tp_sop && nw2tp_eop);
    c_link_down: cover (rst_n && !nw_link_up && nw2tp_flush);
    c_timeout_322: cover (rst_n && elapsed == 16'd322 && !timed_out);
    c_timeout_323: cover (rst_n && elapsed == 16'd323 && timed_out);
    c_psn_wrap: cover (rst_n && psn == 24'hFFFFFF && psn_n == 24'h000000);
    c_full_hdr: cover (rst_n && !compact && btah_bytes == 5'd8 && maetah_bytes == 5'd16);
  end

  wire unused = |{tp2nw_sl, tp2nw_nlp};
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
