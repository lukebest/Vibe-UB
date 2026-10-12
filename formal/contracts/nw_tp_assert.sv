// NW↔TP SVA bind (LAYER_CONTRACTS §2). Assert + cover only.
// Immediate asserts: Yosys 0.33 has no concurrent `assert property (@...)`.
// No assume (GATE-PRIVATE-PARENT-FREE / verif_gate.md §11).
// Unknowns in §2 (NLP→TAH code, RT slice, packet cap, RTPH rest) have
// no assertion.
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
  input wire [15:0] tp2nw_dcna,
  input wire [7:0]  tp2nw_lbf,
  input wire [1:0]  tp2nw_rt,
  input wire [15:0] tp2nw_cci,
  input wire        nw2tp_valid,
  input wire        nw2tp_ready,
  input wire [159:0] nw2tp_data,
  input wire        nw2tp_sop,
  input wire        nw2tp_eop,
  input wire        nw2tp_err,
  input wire        nw2tp_icrc_err,
  input wire        nw2tp_flush,
  input wire        nw2tp_drop,
  input wire        nw_link_up,
  input wire [3:0]  lph_cfg,
  input wire [23:0] psn,
  input wire [23:0] psn_n,
  input wire        rto_fire,
  input wire        ack_coal
);
  localparam integer FLIT_W = 160;
  localparam integer FLITS_PER_BEAT = 1;
  localparam integer SL_W = 4;
  localparam integer NLP_W = 3;
  localparam integer DCNA_W = 16;
  localparam integer LBF_W = 8;
  localparam integer RT_W = 2;
  localparam integer CCI_W = 16;
  localparam integer CFG_W = 4;
  localparam integer CFG_CTP = 6;
  localparam integer CFG_RTP = 7;
  localparam integer CFG_BYP = 9;
  localparam integer PSN_W = 24;
  localparam integer RTPH_BYTES = 16;
  localparam integer LPH_NTH_BYTES = 12;

  always @* begin
    a_flit_w: assert (FLIT_W == 160);
    a_flits_per_beat: assert (FLITS_PER_BEAT == 1);
    a_sl_w: assert (SL_W == 4);
    a_nlp_w: assert (NLP_W == 3);
    a_dcna_w: assert (DCNA_W == 16);
    a_lbf_w: assert (LBF_W == 8);
    a_rt_w: assert (RT_W == 2);
    a_cci_w: assert (CCI_W == 16);
    a_cfg_w: assert (CFG_W == 4);
    a_cfg_ctp: assert (CFG_CTP == 6);
    a_cfg_rtp: assert (CFG_RTP == 7);
    a_cfg_byp: assert (CFG_BYP == 9);
    a_psn_w: assert (PSN_W == 24);
    a_rtph: assert (RTPH_BYTES == 16);
    a_lph_nth: assert (LPH_NTH_BYTES == 12);
    a_psn_inc: assert (psn_n == (psn + 24'd1));
    a_dcna_port: assert ($bits(tp2nw_dcna) == 16);
    a_lbf_port: assert ($bits(tp2nw_lbf) == 8);
    a_rt_port: assert ($bits(tp2nw_rt) == 2);
    a_cci_port: assert ($bits(tp2nw_cci) == 16);
    a_data_port: assert ($bits(tp2nw_data) == 160);
    a_rx_data_port: assert ($bits(nw2tp_data) == 160);
  end

  reg        past_rst_n;
  reg        past_tx_v, past_tx_r, past_tx_sop, past_tx_eop, past_tx_byp;
  reg [159:0] past_tx_data;
  reg [3:0]  past_tx_sl;
  reg [2:0]  past_tx_nlp;
  reg [15:0] past_tx_dcna;
  reg [7:0]  past_tx_lbf;
  reg [1:0]  past_tx_rt;
  reg [15:0] past_tx_cci;
  reg        past_rx_v, past_rx_r, past_rx_sop, past_rx_eop;
  reg [159:0] past_rx_data;
  reg        tx_in_pkt;

  initial begin
    past_rst_n   = 1'b0;
    past_tx_v    = 1'b0;
    past_tx_r    = 1'b0;
    past_tx_data = 160'd0;
    past_tx_sop  = 1'b0;
    past_tx_eop  = 1'b0;
    past_tx_byp  = 1'b0;
    past_tx_sl   = 4'd0;
    past_tx_nlp  = 3'd0;
    past_tx_dcna = 16'd0;
    past_tx_lbf  = 8'd0;
    past_tx_rt   = 2'd0;
    past_tx_cci  = 16'd0;
    past_rx_v    = 1'b0;
    past_rx_r    = 1'b0;
    past_rx_data = 160'd0;
    past_rx_sop  = 1'b0;
    past_rx_eop  = 1'b0;
    tx_in_pkt    = 1'b0;
  end

  always @(posedge core_clk) begin
    past_rst_n   <= rst_n;
    past_tx_v    <= tp2nw_valid;
    past_tx_r    <= tp2nw_ready;
    past_tx_data <= tp2nw_data;
    past_tx_sop  <= tp2nw_sop;
    past_tx_eop  <= tp2nw_eop;
    past_tx_byp  <= tp2nw_bypass;
    past_tx_sl   <= tp2nw_sl;
    past_tx_nlp  <= tp2nw_nlp;
    past_tx_dcna <= tp2nw_dcna;
    past_tx_lbf  <= tp2nw_lbf;
    past_tx_rt   <= tp2nw_rt;
    past_tx_cci  <= tp2nw_cci;
    past_rx_v    <= nw2tp_valid;
    past_rx_r    <= nw2tp_ready;
    past_rx_data <= nw2tp_data;
    past_rx_sop  <= nw2tp_sop;
    past_rx_eop  <= nw2tp_eop;
    if (!rst_n)
      tx_in_pkt <= 1'b0;
    else if (tp2nw_valid && tp2nw_ready) begin
      if (tp2nw_sop && !tp2nw_eop)
        tx_in_pkt <= 1'b1;
      else if (tp2nw_eop)
        tx_in_pkt <= 1'b0;
    end
  end

  always @(posedge core_clk) begin
    if (rst_n) begin
      if (!nw_link_up)
        a_linkdown_no_tx: assert (!(tp2nw_valid && tp2nw_ready));
      if (nw2tp_err)
        a_err_eop: assert (nw2tp_valid && nw2tp_eop);
      if (nw2tp_icrc_err)
        a_icrc_eop: assert (nw2tp_valid && nw2tp_eop);
      if (lph_cfg == CFG_BYP[3:0])
        a_cfg9_no_icrc: assert (!nw2tp_icrc_err);
      if (tp2nw_valid && tp2nw_bypass)
        a_byp_cfg9: assert (lph_cfg == CFG_BYP[3:0]);
      if (nw2tp_flush)
        a_flush_no_new: assert (!tp2nw_valid);
      if (tx_in_pkt && tp2nw_valid && tp2nw_ready)
        a_no_insert: assert (!tp2nw_sop);
    end
    if (past_rst_n && past_tx_v && !past_tx_r) begin
      a_tx_hold_v: assert (tp2nw_valid);
      a_tx_hold_d: assert (tp2nw_data == past_tx_data);
      a_tx_hold_s: assert (tp2nw_sop == past_tx_sop);
      a_tx_hold_e: assert (tp2nw_eop == past_tx_eop);
      a_tx_hold_b: assert (tp2nw_bypass == past_tx_byp);
      a_tx_hold_sl: assert (tp2nw_sl == past_tx_sl);
      a_tx_hold_nlp: assert (tp2nw_nlp == past_tx_nlp);
      a_tx_hold_dcna: assert (tp2nw_dcna == past_tx_dcna);
      a_tx_hold_lbf: assert (tp2nw_lbf == past_tx_lbf);
      a_tx_hold_rt: assert (tp2nw_rt == past_tx_rt);
      a_tx_hold_cci: assert (tp2nw_cci == past_tx_cci);
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
    c_drop: cover (rst_n && nw2tp_drop);
    c_icrc_cfg7: cover (rst_n && nw2tp_icrc_err && nw2tp_valid && nw2tp_eop && (lph_cfg == CFG_RTP[3:0]));
    c_cfg9_no_icrc: cover (rst_n && tp2nw_bypass && (lph_cfg == CFG_BYP[3:0]) && !nw2tp_icrc_err);
    c_psn_wrap: cover (rst_n && psn == 24'hFFFFFF && psn_n == 24'h000000);
    c_rto: cover (rst_n && rto_fire);
    c_ack_coal: cover (rst_n && ack_coal);
  end
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
  .tp2nw_dcna    (tp2nw_dcna),
  .tp2nw_lbf     (tp2nw_lbf),
  .tp2nw_rt      (tp2nw_rt),
  .tp2nw_cci     (tp2nw_cci),
  .nw2tp_valid   (nw2tp_valid),
  .nw2tp_ready   (nw2tp_ready),
  .nw2tp_data    (nw2tp_data),
  .nw2tp_sop     (nw2tp_sop),
  .nw2tp_eop     (nw2tp_eop),
  .nw2tp_err     (nw2tp_err),
  .nw2tp_icrc_err(nw2tp_icrc_err),
  .nw2tp_flush   (nw2tp_flush),
  .nw2tp_drop    (nw2tp_drop),
  .nw_link_up    (nw_link_up),
  .lph_cfg       (lph_cfg),
  .psn           (psn),
  .psn_n         (psn_n),
  .rto_fire      (rto_fire),
  .ack_coal      (ack_coal)
);

`default_nettype wire
