// TP↔TA SVA bind (LAYER_CONTRACTS §3). Assert + cover only. No assume.
// Immediate asserts for Yosys 0.33.
// Unknowns in §3 (mode encoding, op_len width, flush beats, TASSN cap,
// NAK codes, RSPST/RSPINFO) have no assertion.
`default_nettype none

module tp_ta_assert (
  input wire        core_clk,
  input wire        rst_n,
  input wire        ta2tp_op_valid,
  input wire        ta2tp_op_ready,
  input wire [7:0]  ta2tp_opcode,
  input wire [15:0] ta2tp_tassn,
  input wire [1:0]  ta2tp_mode,
  input wire        ta2tp_bypass,
  input wire [15:0] ta2tp_dcna,
  input wire [159:0] ta2tp_data,
  input wire        ta2tp_valid,
  input wire        ta2tp_ready,
  input wire        ta2tp_sop,
  input wire        ta2tp_eop,
  input wire        tp2ta_done,
  input wire        tp2ta_fail,
  input wire [15:0] tp2ta_tassn,
  input wire        tp2ta_err,
  input wire        tp2ta_msn_valid,
  input wire        tp2ta_msn_ready,
  input wire [23:0] tp2ta_tpmsn,
  input wire        ta2tp_cmp_valid,
  input wire        ta2tp_cmp_ready,
  input wire [15:0] ta2tp_cmp_tassn,
  input wire        ta2tp_cmp_fail,
  input wire [7:0]  ta2tp_cmp_opcode,
  input wire        tp2ta_op_valid,
  input wire        tp2ta_op_ready,
  input wire        tp2ta_data_valid,
  input wire        tp2ta_data_ready,
  input wire        tp2ta_data_sop,
  input wire        tp2ta_data_eop,
  input wire        nw2tp_flush,
  input wire        nw_link_up,
  input wire        pending,
  input wire        done_fail_mutex,
  input wire        compact,
  input wire [3:0]  lph_cfg
);
  localparam integer FLIT_W = 160;
  localparam integer TASSN_W = 16;
  localparam integer TPMSN_W = 24;
  localparam integer DCNA_W = 16;
  localparam integer OPCODE_W = 8;
  localparam integer CFG_BYP = 9;

  always @* begin
    a_flit_w: assert (FLIT_W == 160);
    a_tassn_w: assert (TASSN_W == 16);
    a_tpmsn_w: assert (TPMSN_W == 24);
    a_dcna_w: assert (DCNA_W == 16);
    a_opcode_w: assert (OPCODE_W == 8);
    a_mutex_wire: assert (done_fail_mutex == !(tp2ta_done && tp2ta_fail));
    a_compact: assert (compact == (lph_cfg == CFG_BYP[3:0]));
    a_data_port: assert ($bits(ta2tp_data) == 160);
    a_msn_port: assert ($bits(tp2ta_tpmsn) == 24);
    a_cmp_tassn_port: assert ($bits(ta2tp_cmp_tassn) == 16);
    a_cmp_op_port: assert ($bits(ta2tp_cmp_opcode) == 8);
  end

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
      a_done_fail_mutex: assert (!(tp2ta_done && tp2ta_fail));
      if (tp2ta_done || tp2ta_fail)
        a_term_pulse: assert (done_fail_mutex);
      if (nw2tp_flush)
        a_flush_clear: assert (!pending);
      if (tp2ta_err)
        a_err_with_term: assert (tp2ta_done || tp2ta_fail);
      if (ta2tp_op_valid && ta2tp_bypass)
        a_bypass_cfg9: assert (compact);
      if (tp2ta_msn_valid && tp2ta_msn_ready)
        a_msn_key: assert ($bits(tp2ta_tpmsn) == 24);
      if (ta2tp_cmp_valid && ta2tp_cmp_ready && ta2tp_cmp_fail)
        a_cmp_fail_mutex: assert (!(tp2ta_done && !tp2ta_fail));
    end
    if (past_rst_n && past_op_v && !past_op_r) begin
      a_op_hold_v: assert (ta2tp_op_valid);
      a_op_hold_o: assert (ta2tp_opcode == past_opcode);
      a_op_hold_t: assert (ta2tp_tassn == past_tassn);
      a_op_hold_b: assert (ta2tp_bypass == past_byp);
      a_op_hold_dcna: assert (ta2tp_dcna == past_dcna);
    end
    if (past_rst_n && past_dv && !past_dr) begin
      a_data_hold_v: assert (ta2tp_valid);
      a_data_hold_d: assert (ta2tp_data == past_data);
      a_data_hold_s: assert (ta2tp_sop == past_sop);
      a_data_hold_e: assert (ta2tp_eop == past_eop);
    end
    if (past_rst_n && past_cmp_v && !past_cmp_r) begin
      a_cmp_hold_v: assert (ta2tp_cmp_valid);
      a_cmp_hold_t: assert (ta2tp_cmp_tassn == past_cmp_tassn);
      a_cmp_hold_f: assert (ta2tp_cmp_fail == past_cmp_fail);
      a_cmp_hold_o: assert (ta2tp_cmp_opcode == past_cmp_opcode);
    end
    if (past_rst_n && past_msn_v && !past_msn_r) begin
      a_msn_hold_v: assert (tp2ta_msn_valid);
      a_msn_hold_k: assert (tp2ta_tpmsn == past_tpmsn);
    end
  end

  always @(posedge core_clk) begin
    c_submit_byp: cover (rst_n && ta2tp_op_valid && ta2tp_op_ready && ta2tp_bypass && compact);
    c_op_hold: cover (rst_n && ta2tp_op_valid && !ta2tp_op_ready);
    c_payload: cover (rst_n && ta2tp_valid && ta2tp_ready && ta2tp_sop && ta2tp_eop);
    c_done: cover (rst_n && tp2ta_done && !tp2ta_fail);
    c_fail: cover (rst_n && tp2ta_fail && !tp2ta_done);
    c_deliver: cover (rst_n && tp2ta_op_valid && tp2ta_op_ready);
    c_deliver_data: cover (rst_n && tp2ta_data_valid && tp2ta_data_ready && tp2ta_data_sop && tp2ta_data_eop);
    c_flush_empty: cover (rst_n && nw2tp_flush && !pending && !nw_link_up);
    c_full_cfg: cover (rst_n && !compact && ta2tp_op_valid && !ta2tp_bypass);
    c_msn: cover (rst_n && tp2ta_msn_valid && tp2ta_msn_ready);
    c_cmp_ok: cover (rst_n && ta2tp_cmp_valid && ta2tp_cmp_ready && !ta2tp_cmp_fail);
    c_cmp_fail: cover (rst_n && ta2tp_cmp_valid && ta2tp_cmp_ready && ta2tp_cmp_fail);
  end

  wire unused = |{ta2tp_mode, nw_link_up};
endmodule

bind tp_ta_harness tp_ta_assert u_tp_ta_assert (
  .core_clk          (core_clk),
  .rst_n             (rst_n),
  .ta2tp_op_valid    (ta2tp_op_valid),
  .ta2tp_op_ready    (ta2tp_op_ready),
  .ta2tp_opcode      (ta2tp_opcode),
  .ta2tp_tassn       (ta2tp_tassn),
  .ta2tp_mode        (ta2tp_mode),
  .ta2tp_bypass      (ta2tp_bypass),
  .ta2tp_dcna        (ta2tp_dcna),
  .ta2tp_data        (ta2tp_data),
  .ta2tp_valid       (ta2tp_valid),
  .ta2tp_ready       (ta2tp_ready),
  .ta2tp_sop         (ta2tp_sop),
  .ta2tp_eop         (ta2tp_eop),
  .tp2ta_done        (tp2ta_done),
  .tp2ta_fail        (tp2ta_fail),
  .tp2ta_tassn       (tp2ta_tassn),
  .tp2ta_err         (tp2ta_err),
  .tp2ta_msn_valid   (tp2ta_msn_valid),
  .tp2ta_msn_ready   (tp2ta_msn_ready),
  .tp2ta_tpmsn       (tp2ta_tpmsn),
  .ta2tp_cmp_valid   (ta2tp_cmp_valid),
  .ta2tp_cmp_ready   (ta2tp_cmp_ready),
  .ta2tp_cmp_tassn   (ta2tp_cmp_tassn),
  .ta2tp_cmp_fail    (ta2tp_cmp_fail),
  .ta2tp_cmp_opcode  (ta2tp_cmp_opcode),
  .tp2ta_op_valid    (tp2ta_op_valid),
  .tp2ta_op_ready    (tp2ta_op_ready),
  .tp2ta_data_valid  (tp2ta_data_valid),
  .tp2ta_data_ready  (tp2ta_data_ready),
  .tp2ta_data_sop    (tp2ta_data_sop),
  .tp2ta_data_eop    (tp2ta_data_eop),
  .nw2tp_flush       (nw2tp_flush),
  .nw_link_up        (nw_link_up),
  .pending           (pending),
  .done_fail_mutex   (done_fail_mutex),
  .compact           (compact),
  .lph_cfg           (lph_cfg)
);

`default_nettype wire
