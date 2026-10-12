// ub_tp_bypass_if_props — basic interface properties (LAYER_CONTRACTS §2 / §3).
// Formal-only stub (DATA_W=8). Yosys-compatible clocked assert/cover.
// Wave-1 CFG9: no ICRC, no RTP/CTP/GBN.

module ub_tp_bypass_if_props (
  input  wire        core_clk,
  input  wire        rst_pyc,
  input  wire [7:0]  ta2tp_data,
  input  wire        ta2tp_valid,
  input  wire        ta2tp_ready,
  input  wire        ta2tp_sop,
  input  wire        ta2tp_eop,
  input  wire        ta2tp_op_valid,
  input  wire        ta2tp_op_ready,
  input  wire        ta2tp_bypass,
  input  wire [15:0] ta2tp_dcna,
  input  wire [7:0]  tp2nw_data,
  input  wire        tp2nw_valid,
  input  wire        tp2nw_ready,
  input  wire        tp2nw_sop,
  input  wire        tp2nw_eop,
  input  wire        tp2nw_bypass,
  input  wire [15:0] tp2nw_dcna,
  input  wire [3:0]  tp2nw_sl,
  input  wire [2:0]  tp2nw_nlp,
  input  wire [7:0]  tp2nw_lbf,
  input  wire [1:0]  tp2nw_rt,
  input  wire [15:0] tp2nw_cci,
  input  wire [7:0]  nw2tp_data,
  input  wire        nw2tp_valid,
  input  wire        nw2tp_ready,
  input  wire        nw2tp_sop,
  input  wire        nw2tp_eop,
  input  wire        nw2tp_err,
  input  wire        nw2tp_flush,
  input  wire        nw_link_up,
  input  wire [7:0]  tp2ta_data,
  input  wire        tp2ta_valid,
  input  wire        tp2ta_ready,
  input  wire        tp2ta_sop,
  input  wire        tp2ta_eop,
  input  wire        tp2ta_err
);
  reg f_past_ok;
  initial f_past_ok = 1'b0;
  always @(posedge core_clk)
    f_past_ok <= 1'b1;

  always @(posedge core_clk) begin
    if (f_past_ok && $past(rst_pyc)) begin
      a_tx_valid_rst: assert (!tp2nw_valid);
      a_rx_valid_rst: assert (!tp2ta_valid);
    end

    if (tp2nw_valid) begin
      a_sl_zero:  assert (tp2nw_sl == 4'b0);
      a_nlp_zero: assert (tp2nw_nlp == 3'b0);
      a_lbf_zero: assert (tp2nw_lbf == 8'b0);
      a_rt_zero:  assert (tp2nw_rt == 2'b0);
      a_cci_zero: assert (tp2nw_cci == 16'b0);
    end

    if (f_past_ok && !rst_pyc && $past(!rst_pyc)) begin
      if ($past(tp2nw_valid && !tp2nw_ready))
        a_tx_hold_v: assert (tp2nw_valid);
    end

    c_rst: cover (rst_pyc);
    c_tx_op: cover (!rst_pyc && ta2tp_op_valid && ta2tp_op_ready);
    c_tx_data: cover (!rst_pyc && ta2tp_valid && ta2tp_ready);
    c_tx_present: cover (!rst_pyc && tp2nw_valid && tp2nw_ready);
    c_rx_present: cover (!rst_pyc && tp2ta_valid && tp2ta_ready);
    c_tx_bp: cover (!rst_pyc && tp2nw_valid && !tp2nw_ready);
    c_link_down: cover (!rst_pyc && !nw_link_up);
    c_flush: cover (!rst_pyc && nw2tp_flush);
  end
endmodule
