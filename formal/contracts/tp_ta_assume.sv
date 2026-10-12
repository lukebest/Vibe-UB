// TP↔TA contract assume — diagnostic task only (GATE-PRIVATE-PARENT-FREE).
`default_nettype none

module tp_ta_assume (
  input wire        core_clk,
  input wire        rst_n,
  input wire        ta2tp_op_valid,
  input wire        ta2tp_op_ready,
  input wire [7:0]  ta2tp_opcode,
  input wire [15:0] ta2tp_tassn,
  input wire        ta2tp_bypass,
  input wire [15:0] ta2tp_dcna,
  input wire [159:0] ta2tp_data,
  input wire        ta2tp_valid,
  input wire        ta2tp_ready,
  input wire        ta2tp_sop,
  input wire        ta2tp_eop,
  input wire        tp2ta_done,
  input wire        tp2ta_fail,
  input wire        tp2ta_msn_valid,
  input wire        tp2ta_msn_ready,
  input wire [23:0] tp2ta_tpmsn,
  input wire        ta2tp_cmp_valid,
  input wire        ta2tp_cmp_ready,
  input wire [15:0] ta2tp_cmp_tassn,
  input wire        ta2tp_cmp_fail,
  input wire [7:0]  ta2tp_cmp_opcode,
  input wire        nw2tp_flush,
  input wire        pending,
  input wire        compact
);
  reg        past_rst_n;
  reg        past_op_v, past_op_r;
  reg [7:0]  past_opcode;
  reg [15:0] past_tassn;
  reg        past_byp;
  reg [15:0] past_dcna;
  reg        past_dv, past_dr, past_sop, past_eop;
  reg [159:0] past_data;
  reg        past_cmp_v, past_cmp_r, past_cmp_fail;
  reg [15:0] past_cmp_tassn;
  reg [7:0]  past_cmp_opcode;
  reg        past_msn_v, past_msn_r;
  reg [23:0] past_tpmsn;

  initial begin
    past_rst_n  = 1'b0;
    past_op_v   = 1'b0;
    past_op_r   = 1'b0;
    past_opcode = 8'd0;
    past_tassn  = 16'd0;
    past_byp    = 1'b0;
    past_dcna   = 16'd0;
    past_dv     = 1'b0;
    past_dr     = 1'b0;
    past_data   = 160'd0;
    past_sop    = 1'b0;
    past_eop    = 1'b0;
    past_cmp_v  = 1'b0;
    past_cmp_r  = 1'b0;
    past_cmp_fail = 1'b0;
    past_cmp_tassn = 16'd0;
    past_cmp_opcode = 8'd0;
    past_msn_v  = 1'b0;
    past_msn_r  = 1'b0;
    past_tpmsn  = 24'd0;
  end

  always @(posedge core_clk) begin
    past_rst_n  <= rst_n;
    past_op_v   <= ta2tp_op_valid;
    past_op_r   <= ta2tp_op_ready;
    past_opcode <= ta2tp_opcode;
    past_tassn  <= ta2tp_tassn;
    past_byp    <= ta2tp_bypass;
    past_dcna   <= ta2tp_dcna;
    past_dv     <= ta2tp_valid;
    past_dr     <= ta2tp_ready;
    past_data   <= ta2tp_data;
    past_sop    <= ta2tp_sop;
    past_eop    <= ta2tp_eop;
    past_cmp_v  <= ta2tp_cmp_valid;
    past_cmp_r  <= ta2tp_cmp_ready;
    past_cmp_fail <= ta2tp_cmp_fail;
    past_cmp_tassn <= ta2tp_cmp_tassn;
    past_cmp_opcode <= ta2tp_cmp_opcode;
    past_msn_v  <= tp2ta_msn_valid;
    past_msn_r  <= tp2ta_msn_ready;
    past_tpmsn  <= tp2ta_tpmsn;
  end

  always @(posedge core_clk) begin
    if (rst_n) begin
      am_done_fail: assume (!(tp2ta_done && tp2ta_fail));
      if (nw2tp_flush)
        am_flush_clear: assume (!pending);
      if (ta2tp_op_valid && ta2tp_bypass)
        am_byp_cfg9: assume (compact);
    end
    if (past_rst_n && past_op_v && !past_op_r) begin
      am_op_hold_v: assume (ta2tp_op_valid);
      am_op_hold_o: assume (ta2tp_opcode == past_opcode);
      am_op_hold_t: assume (ta2tp_tassn == past_tassn);
      am_op_hold_b: assume (ta2tp_bypass == past_byp);
      am_op_hold_dcna: assume (ta2tp_dcna == past_dcna);
    end
    if (past_rst_n && past_dv && !past_dr) begin
      am_data_hold_v: assume (ta2tp_valid);
      am_data_hold_d: assume (ta2tp_data == past_data);
      am_data_hold_s: assume (ta2tp_sop == past_sop);
      am_data_hold_e: assume (ta2tp_eop == past_eop);
    end
    if (past_rst_n && past_cmp_v && !past_cmp_r) begin
      am_cmp_hold_v: assume (ta2tp_cmp_valid);
      am_cmp_hold_t: assume (ta2tp_cmp_tassn == past_cmp_tassn);
      am_cmp_hold_f: assume (ta2tp_cmp_fail == past_cmp_fail);
      am_cmp_hold_o: assume (ta2tp_cmp_opcode == past_cmp_opcode);
    end
    if (past_rst_n && past_msn_v && !past_msn_r) begin
      am_msn_hold_v: assume (tp2ta_msn_valid);
      am_msn_hold_k: assume (tp2ta_tpmsn == past_tpmsn);
    end
  end
endmodule

bind tp_ta_harness tp_ta_assume u_tp_ta_assume (
  .core_clk         (core_clk),
  .rst_n            (rst_n),
  .ta2tp_op_valid   (ta2tp_op_valid),
  .ta2tp_op_ready   (ta2tp_op_ready),
  .ta2tp_opcode     (ta2tp_opcode),
  .ta2tp_tassn      (ta2tp_tassn),
  .ta2tp_bypass     (ta2tp_bypass),
  .ta2tp_dcna       (ta2tp_dcna),
  .ta2tp_data       (ta2tp_data),
  .ta2tp_valid      (ta2tp_valid),
  .ta2tp_ready      (ta2tp_ready),
  .ta2tp_sop        (ta2tp_sop),
  .ta2tp_eop        (ta2tp_eop),
  .tp2ta_done       (tp2ta_done),
  .tp2ta_fail       (tp2ta_fail),
  .tp2ta_msn_valid  (tp2ta_msn_valid),
  .tp2ta_msn_ready  (tp2ta_msn_ready),
  .tp2ta_tpmsn      (tp2ta_tpmsn),
  .ta2tp_cmp_valid  (ta2tp_cmp_valid),
  .ta2tp_cmp_ready  (ta2tp_cmp_ready),
  .ta2tp_cmp_tassn  (ta2tp_cmp_tassn),
  .ta2tp_cmp_fail   (ta2tp_cmp_fail),
  .ta2tp_cmp_opcode (ta2tp_cmp_opcode),
  .nw2tp_flush      (nw2tp_flush),
  .pending          (pending),
  .compact          (compact)
);

`default_nettype wire
