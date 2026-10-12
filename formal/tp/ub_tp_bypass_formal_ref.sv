// Formal-only synthesizable CFG9 bypass (tp_uarch §4.1). Not product RTL.
// Matches pycircuit/tp/ub_tp_bypass.py: 1-cycle registered slices,
// 1 outstanding op, no ICRC / RTP / CTP / GBN.

module ub_tp_bypass_formal_ref (
  input  wire         core_clk,
  input  wire         rst_pyc,
  input  wire [159:0] ta2tp_data,
  input  wire         ta2tp_valid,
  output wire         ta2tp_ready,
  input  wire         ta2tp_sop,
  input  wire         ta2tp_eop,
  input  wire         ta2tp_op_valid,
  output wire         ta2tp_op_ready,
  input  wire         ta2tp_bypass,
  input  wire [15:0]  ta2tp_dcna,
  output wire [159:0] tp2nw_data,
  output wire         tp2nw_valid,
  input  wire         tp2nw_ready,
  output wire         tp2nw_sop,
  output wire         tp2nw_eop,
  output wire         tp2nw_bypass,
  output wire [15:0]  tp2nw_dcna,
  output wire [3:0]   tp2nw_sl,
  output wire [2:0]   tp2nw_nlp,
  output wire [7:0]   tp2nw_lbf,
  output wire [1:0]   tp2nw_rt,
  output wire [15:0]  tp2nw_cci,
  input  wire [159:0] nw2tp_data,
  input  wire         nw2tp_valid,
  output wire         nw2tp_ready,
  input  wire         nw2tp_sop,
  input  wire         nw2tp_eop,
  input  wire         nw2tp_err,
  input  wire         nw2tp_flush,
  input  wire         nw_link_up,
  output wire [159:0] tp2ta_data,
  output wire         tp2ta_valid,
  input  wire         tp2ta_ready,
  output wire         tp2ta_sop,
  output wire         tp2ta_eop,
  output wire         tp2ta_err
);
  wire can_tx_env = nw_link_up & ~nw2tp_flush;

  reg        busy_q;
  reg        tx_valid_q;
  reg [159:0] tx_data_q;
  reg        tx_sop_q;
  reg        tx_eop_q;
  reg [15:0] dcna_q;
  reg        bypass_q;
  reg        rx_valid_q;
  reg [159:0] rx_data_q;
  reg        rx_sop_q;
  reg        rx_eop_q;
  reg        rx_err_q;

  wire op_ready_i = can_tx_env & ~busy_q;
  wire op_hs = ta2tp_op_valid & op_ready_i;
  wire allow_data = can_tx_env & (busy_q | op_hs);
  wire tx_vacate = tp2nw_ready | ~tx_valid_q;
  wire ta2tp_ready_i = tx_vacate & allow_data;
  wire data_hs = ta2tp_valid & ta2tp_ready_i;
  wire data_eop_hs = data_hs & ta2tp_eop;
  wire rx_vacate = tp2ta_ready | ~rx_valid_q;
  wire nw2tp_ready_i = rx_vacate;
  wire rx_hs = nw2tp_valid & nw2tp_ready_i;

  assign ta2tp_op_ready = op_ready_i;
  assign ta2tp_ready = ta2tp_ready_i;
  assign tp2nw_valid = tx_valid_q;
  assign tp2nw_data = tx_data_q;
  assign tp2nw_sop = tx_sop_q;
  assign tp2nw_eop = tx_eop_q;
  assign tp2nw_bypass = bypass_q;
  assign tp2nw_dcna = dcna_q;
  assign tp2nw_sl = 4'b0;
  assign tp2nw_nlp = 3'b0;
  assign tp2nw_lbf = 8'b0;
  assign tp2nw_rt = 2'b0;
  assign tp2nw_cci = 16'b0;
  assign nw2tp_ready = nw2tp_ready_i;
  assign tp2ta_valid = rx_valid_q;
  assign tp2ta_data = rx_data_q;
  assign tp2ta_sop = rx_sop_q;
  assign tp2ta_eop = rx_eop_q;
  assign tp2ta_err = rx_err_q;

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      busy_q     <= 1'b0;
      tx_valid_q <= 1'b0;
      tx_data_q  <= 160'b0;
      tx_sop_q   <= 1'b0;
      tx_eop_q   <= 1'b0;
      dcna_q     <= 16'b0;
      bypass_q   <= 1'b0;
      rx_valid_q <= 1'b0;
      rx_data_q  <= 160'b0;
      rx_sop_q   <= 1'b0;
      rx_eop_q   <= 1'b0;
      rx_err_q   <= 1'b0;
    end else begin
      busy_q <= op_hs | (busy_q & ~data_eop_hs);
      if (tx_vacate)
        tx_valid_q <= ta2tp_valid & allow_data;
      if (data_hs) begin
        tx_data_q <= ta2tp_data;
        tx_sop_q  <= ta2tp_sop;
        tx_eop_q  <= ta2tp_eop;
      end
      if (op_hs) begin
        dcna_q   <= ta2tp_dcna;
        bypass_q <= ta2tp_bypass;
      end
      if (rx_vacate)
        rx_valid_q <= nw2tp_valid;
      if (rx_hs) begin
        rx_data_q <= nw2tp_data;
        rx_sop_q  <= nw2tp_sop;
        rx_eop_q  <= nw2tp_eop;
        rx_err_q  <= nw2tp_err;
      end
    end
  end
endmodule
