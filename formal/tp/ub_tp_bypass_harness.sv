// Standalone harness: formal-only ref + props. Not product RTL.
// DATA_W=8 stub. No $past assumes (keeps BMC SAT small). NW ready is
// low when the link is down.

module ub_tp_bypass_harness (
  input  wire        core_clk,
  input  wire        rst_pyc,
  input  wire [7:0]  ta2tp_data,
  input  wire        ta2tp_valid,
  input  wire        ta2tp_sop,
  input  wire        ta2tp_eop,
  input  wire        ta2tp_op_valid,
  input  wire        ta2tp_bypass,
  input  wire [15:0] ta2tp_dcna,
  input  wire        tp2nw_ready,
  input  wire [7:0]  nw2tp_data,
  input  wire        nw2tp_valid,
  input  wire        nw2tp_sop,
  input  wire        nw2tp_eop,
  input  wire        nw2tp_err,
  input  wire        nw2tp_flush,
  input  wire        nw_link_up,
  input  wire        tp2ta_ready
);
  wire        ta2tp_ready;
  wire        ta2tp_op_ready;
  wire [7:0]  tp2nw_data;
  wire        tp2nw_valid;
  wire        tp2nw_sop;
  wire        tp2nw_eop;
  wire        tp2nw_bypass;
  wire [15:0] tp2nw_dcna;
  wire [3:0]  tp2nw_sl;
  wire [2:0]  tp2nw_nlp;
  wire [7:0]  tp2nw_lbf;
  wire [1:0]  tp2nw_rt;
  wire [15:0] tp2nw_cci;
  wire        nw2tp_ready;
  wire [7:0]  tp2ta_data;
  wire        tp2ta_valid;
  wire        tp2ta_sop;
  wire        tp2ta_eop;
  wire        tp2ta_err;

  always @(*) begin
    if (!nw_link_up)
      assume (!tp2nw_ready);
  end

  ub_tp_bypass_formal_ref u_dut (
    .core_clk(core_clk),
    .rst_pyc(rst_pyc),
    .ta2tp_data(ta2tp_data),
    .ta2tp_valid(ta2tp_valid),
    .ta2tp_ready(ta2tp_ready),
    .ta2tp_sop(ta2tp_sop),
    .ta2tp_eop(ta2tp_eop),
    .ta2tp_op_valid(ta2tp_op_valid),
    .ta2tp_op_ready(ta2tp_op_ready),
    .ta2tp_bypass(ta2tp_bypass),
    .ta2tp_dcna(ta2tp_dcna),
    .tp2nw_data(tp2nw_data),
    .tp2nw_valid(tp2nw_valid),
    .tp2nw_ready(tp2nw_ready),
    .tp2nw_sop(tp2nw_sop),
    .tp2nw_eop(tp2nw_eop),
    .tp2nw_bypass(tp2nw_bypass),
    .tp2nw_dcna(tp2nw_dcna),
    .tp2nw_sl(tp2nw_sl),
    .tp2nw_nlp(tp2nw_nlp),
    .tp2nw_lbf(tp2nw_lbf),
    .tp2nw_rt(tp2nw_rt),
    .tp2nw_cci(tp2nw_cci),
    .nw2tp_data(nw2tp_data),
    .nw2tp_valid(nw2tp_valid),
    .nw2tp_ready(nw2tp_ready),
    .nw2tp_sop(nw2tp_sop),
    .nw2tp_eop(nw2tp_eop),
    .nw2tp_err(nw2tp_err),
    .nw2tp_flush(nw2tp_flush),
    .nw_link_up(nw_link_up),
    .tp2ta_data(tp2ta_data),
    .tp2ta_valid(tp2ta_valid),
    .tp2ta_ready(tp2ta_ready),
    .tp2ta_sop(tp2ta_sop),
    .tp2ta_eop(tp2ta_eop),
    .tp2ta_err(tp2ta_err)
  );

  ub_tp_bypass_if_props u_props (
    .core_clk(core_clk),
    .rst_pyc(rst_pyc),
    .ta2tp_data(ta2tp_data),
    .ta2tp_valid(ta2tp_valid),
    .ta2tp_ready(ta2tp_ready),
    .ta2tp_sop(ta2tp_sop),
    .ta2tp_eop(ta2tp_eop),
    .ta2tp_op_valid(ta2tp_op_valid),
    .ta2tp_op_ready(ta2tp_op_ready),
    .ta2tp_bypass(ta2tp_bypass),
    .ta2tp_dcna(ta2tp_dcna),
    .tp2nw_data(tp2nw_data),
    .tp2nw_valid(tp2nw_valid),
    .tp2nw_ready(tp2nw_ready),
    .tp2nw_sop(tp2nw_sop),
    .tp2nw_eop(tp2nw_eop),
    .tp2nw_bypass(tp2nw_bypass),
    .tp2nw_dcna(tp2nw_dcna),
    .tp2nw_sl(tp2nw_sl),
    .tp2nw_nlp(tp2nw_nlp),
    .tp2nw_lbf(tp2nw_lbf),
    .tp2nw_rt(tp2nw_rt),
    .tp2nw_cci(tp2nw_cci),
    .nw2tp_data(nw2tp_data),
    .nw2tp_valid(nw2tp_valid),
    .nw2tp_ready(nw2tp_ready),
    .nw2tp_sop(nw2tp_sop),
    .nw2tp_eop(nw2tp_eop),
    .nw2tp_err(nw2tp_err),
    .nw2tp_flush(nw2tp_flush),
    .nw_link_up(nw_link_up),
    .tp2ta_data(tp2ta_data),
    .tp2ta_valid(tp2ta_valid),
    .tp2ta_ready(tp2ta_ready),
    .tp2ta_sop(tp2ta_sop),
    .tp2ta_eop(tp2ta_eop),
    .tp2ta_err(tp2ta_err)
  );
endmodule
