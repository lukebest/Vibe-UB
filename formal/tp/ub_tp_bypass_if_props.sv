// ub_tp_bypass_if_props — interface properties (LAYER_CONTRACTS §2 / §3).
// Formal-only. Bind on the leaf ports. Yosys-compatible clocked assert/cover.
// Wave-1 CFG9: no ICRC, no RTP/CTP/GBN.

module ub_tp_bypass_if_props (
  input  wire         core_clk,
  input  wire         rst_pyc,
  input  wire [159:0] ta2tp_data,
  input  wire         ta2tp_valid,
  input  wire         ta2tp_ready,
  input  wire         ta2tp_sop,
  input  wire         ta2tp_eop,
  input  wire         ta2tp_op_valid,
  input  wire         ta2tp_op_ready,
  input  wire         ta2tp_bypass,
  input  wire [15:0]  ta2tp_dcna,
  input  wire [159:0] tp2nw_data,
  input  wire         tp2nw_valid,
  input  wire         tp2nw_ready,
  input  wire         tp2nw_sop,
  input  wire         tp2nw_eop,
  input  wire         tp2nw_bypass,
  input  wire [15:0]  tp2nw_dcna,
  input  wire [3:0]   tp2nw_sl,
  input  wire [2:0]   tp2nw_nlp,
  input  wire [7:0]   tp2nw_lbf,
  input  wire [1:0]   tp2nw_rt,
  input  wire [15:0]  tp2nw_cci,
  input  wire [159:0] nw2tp_data,
  input  wire         nw2tp_valid,
  input  wire         nw2tp_ready,
  input  wire         nw2tp_sop,
  input  wire         nw2tp_eop,
  input  wire         nw2tp_err,
  input  wire         nw2tp_flush,
  input  wire         nw_link_up,
  input  wire [159:0] tp2ta_data,
  input  wire         tp2ta_valid,
  input  wire         tp2ta_ready,
  input  wire         tp2ta_sop,
  input  wire         tp2ta_eop,
  input  wire         tp2ta_err
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

    if (f_past_ok && !rst_pyc && $past(!rst_pyc)) begin
      if ($past(!nw_link_up | nw2tp_flush)) begin
        a_no_op_hs_down:  assert (!($past(ta2tp_op_valid) && $past(ta2tp_op_ready)));
        a_no_data_hs_down: assert (!($past(ta2tp_valid) && $past(ta2tp_ready)));
      end

      if ($past(ta2tp_valid && ta2tp_ready && !rst_pyc)) begin
        a_tx_delay: assert (tp2nw_valid);
        a_tx_data:  assert (tp2nw_data == $past(ta2tp_data));
        a_tx_sop:   assert (tp2nw_sop == $past(ta2tp_sop));
        a_tx_eop:   assert (tp2nw_eop == $past(ta2tp_eop));
      end

      if ($past(nw2tp_valid && nw2tp_ready && !rst_pyc)) begin
        a_rx_delay: assert (tp2ta_valid);
        a_rx_data:  assert (tp2ta_data == $past(nw2tp_data));
        a_rx_err:   assert (tp2ta_err == $past(nw2tp_err));
      end

      if (tp2nw_valid) begin
        a_sl_zero:  assert (tp2nw_sl == 4'b0);
        a_nlp_zero: assert (tp2nw_nlp == 3'b0);
        a_lbf_zero: assert (tp2nw_lbf == 8'b0);
        a_rt_zero:  assert (tp2nw_rt == 2'b0);
        a_cci_zero: assert (tp2nw_cci == 16'b0);
      end

      if ($past(tp2nw_valid && !tp2nw_ready && !rst_pyc)) begin
        a_tx_hold_v:    assert (tp2nw_valid);
        a_tx_hold_data: assert (tp2nw_data == $past(tp2nw_data));
        a_tx_hold_dcna: assert (tp2nw_dcna == $past(tp2nw_dcna));
      end
    end

    c_tx_single: cover (
      !rst_pyc && ta2tp_op_valid && ta2tp_op_ready && ta2tp_bypass
      && ta2tp_valid && ta2tp_ready && ta2tp_sop && ta2tp_eop
    );
    c_tx_present: cover (!rst_pyc && tp2nw_valid && tp2nw_ready && tp2nw_sop && tp2nw_eop);
    c_rx_err: cover (!rst_pyc && tp2ta_valid && tp2ta_ready && tp2ta_eop && tp2ta_err);
    c_tx_bp: cover (!rst_pyc && tp2nw_valid && !tp2nw_ready);
    c_link_down: cover (!rst_pyc && !nw_link_up);
    c_flush: cover (!rst_pyc && nw2tp_flush);
  end
endmodule
