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
  input wire        nw_link_up,
  input wire [3:0]  lph_cfg
);
  localparam integer CFG_BYP = 9;

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
  end

  always @(posedge core_clk) begin
    if (rst_n) begin
      if (!nw_link_up)
        am_linkdown: assume (!tp2nw_valid);
      if (tp2nw_valid && tp2nw_bypass)
        am_byp_cfg9: assume (lph_cfg == CFG_BYP[3:0]);
    end
    if (past_rst_n && past_tx_v && !past_tx_r) begin
      am_tx_hold_v: assume (tp2nw_valid);
      am_tx_hold_d: assume (tp2nw_data == past_tx_data);
      am_tx_hold_s: assume (tp2nw_sop == past_tx_sop);
      am_tx_hold_e: assume (tp2nw_eop == past_tx_eop);
      am_tx_hold_b: assume (tp2nw_bypass == past_tx_byp);
      am_tx_hold_sl: assume (tp2nw_sl == past_tx_sl);
      am_tx_hold_nlp: assume (tp2nw_nlp == past_tx_nlp);
      am_tx_hold_dcna: assume (tp2nw_dcna == past_tx_dcna);
      am_tx_hold_lbf: assume (tp2nw_lbf == past_tx_lbf);
      am_tx_hold_rt: assume (tp2nw_rt == past_tx_rt);
      am_tx_hold_cci: assume (tp2nw_cci == past_tx_cci);
    end
    if (past_rst_n && past_rx_v && !past_rx_r) begin
      am_rx_hold_v: assume (nw2tp_valid);
      am_rx_hold_d: assume (nw2tp_data == past_rx_data);
      am_rx_hold_s: assume (nw2tp_sop == past_rx_sop);
      am_rx_hold_e: assume (nw2tp_eop == past_rx_eop);
    end
  end
endmodule

bind nw_tp_harness nw_tp_assume u_nw_tp_assume (
  .core_clk     (core_clk),
  .rst_n        (rst_n),
  .tp2nw_valid  (tp2nw_valid),
  .tp2nw_ready  (tp2nw_ready),
  .tp2nw_data   (tp2nw_data),
  .tp2nw_sop    (tp2nw_sop),
  .tp2nw_eop    (tp2nw_eop),
  .tp2nw_sl     (tp2nw_sl),
  .tp2nw_nlp    (tp2nw_nlp),
  .tp2nw_bypass (tp2nw_bypass),
  .tp2nw_dcna   (tp2nw_dcna),
  .tp2nw_lbf    (tp2nw_lbf),
  .tp2nw_rt     (tp2nw_rt),
  .tp2nw_cci    (tp2nw_cci),
  .nw2tp_valid  (nw2tp_valid),
  .nw2tp_ready  (nw2tp_ready),
  .nw2tp_data   (nw2tp_data),
  .nw2tp_sop    (nw2tp_sop),
  .nw2tp_eop    (nw2tp_eop),
  .nw_link_up   (nw_link_up),
  .lph_cfg      (lph_cfg)
);

`default_nettype wire
