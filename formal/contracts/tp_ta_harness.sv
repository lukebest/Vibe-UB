// TP↔TA contract harness (LAYER_CONTRACTS §3). Combo-of-cyc, initialized.
`default_nettype none

module tp_ta_harness (
  input wire core_clk
);
  localparam integer FLIT_W = 160;
  localparam integer TASSN_W = 16;
  localparam integer CFG9 = 9;

  reg [4:0] cyc;
  initial cyc = 5'd0;
  always @(posedge core_clk) begin
    if (cyc != 5'd31)
      cyc <= cyc + 5'd1;
  end

  wire rst_n = (cyc != 5'd0);

  wire        ta2tp_op_valid = (cyc == 5'd2) || (cyc == 5'd5) || (cyc == 5'd6) || (cyc == 5'd13);
  wire        ta2tp_op_ready = (cyc != 5'd5);
  wire [7:0]  ta2tp_opcode   = (cyc == 5'd2) ? 8'h10 :
                               ((cyc == 5'd5) || (cyc == 5'd6)) ? 8'h11 :
                               (cyc == 5'd13) ? 8'h20 : 8'd0;
  wire [TASSN_W-1:0] ta2tp_tassn = (cyc == 5'd2) ? 16'h0001 :
                                   ((cyc == 5'd5) || (cyc == 5'd6)) ? 16'h0002 :
                                   (cyc == 5'd13) ? 16'hABCD : 16'd0;
  wire [1:0]  ta2tp_mode     = 2'd0;
  wire        ta2tp_bypass   = (cyc == 5'd13) ? 1'b0 : 1'b1;

  wire        ta2tp_valid    = (cyc == 5'd3);
  wire        ta2tp_ready    = 1'b1;
  wire [FLIT_W-1:0] ta2tp_data = (cyc == 5'd3) ? {{(FLIT_W-8){1'b0}}, 8'h55} : {FLIT_W{1'b0}};
  wire        ta2tp_sop      = (cyc == 5'd3);
  wire        ta2tp_eop      = (cyc == 5'd3);

  wire        tp2ta_done     = (cyc == 5'd4) || (cyc == 5'd14);
  wire        tp2ta_fail     = (cyc == 5'd7);
  wire [TASSN_W-1:0] tp2ta_tassn = (cyc == 5'd4) ? 16'h0001 :
                                   (cyc == 5'd7) ? 16'h0002 :
                                   (cyc == 5'd14) ? 16'hABCD : 16'd0;
  wire        tp2ta_err      = 1'b0;

  wire        tp2ta_op_valid = (cyc == 5'd8);
  wire        tp2ta_op_ready = 1'b1;
  wire [7:0]  tp2ta_opcode   = (cyc == 5'd8) ? 8'h10 : 8'd0;
  wire [TASSN_W-1:0] tp2ta_op_tassn = (cyc == 5'd8) ? 16'h0003 : 16'd0;
  wire [1:0]  tp2ta_op_mode  = 2'd0;
  wire        tp2ta_op_bypass = 1'b1;

  wire        tp2ta_data_valid = (cyc == 5'd9);
  wire        tp2ta_data_ready = 1'b1;
  wire [FLIT_W-1:0] tp2ta_data = (cyc == 5'd9) ? {{(FLIT_W-8){1'b0}}, 8'h66} : {FLIT_W{1'b0}};
  wire        tp2ta_data_sop = (cyc == 5'd9);
  wire        tp2ta_data_eop = (cyc == 5'd9);

  wire        nw2tp_flush    = (cyc == 5'd11);
  wire        nw_link_up     = (cyc != 5'd11);
  wire [3:0]  lph_cfg        = (cyc >= 5'd12) ? 4'd6 : CFG9[3:0];
  wire        compact        = (lph_cfg == CFG9[3:0]);
  wire        pending        = (cyc == 5'd2) || (cyc == 5'd3) || (cyc == 5'd5)
                              || (cyc == 5'd6) || (cyc == 5'd13);
  wire        done_fail_mutex = !(tp2ta_done && tp2ta_fail);

  tp_ta_assert u_tp_ta_assert (
    .core_clk          (core_clk),
    .rst_n             (rst_n),
    .ta2tp_op_valid    (ta2tp_op_valid),
    .ta2tp_op_ready    (ta2tp_op_ready),
    .ta2tp_opcode      (ta2tp_opcode),
    .ta2tp_tassn       (ta2tp_tassn),
    .ta2tp_mode        (ta2tp_mode),
    .ta2tp_bypass      (ta2tp_bypass),
    .ta2tp_data        (ta2tp_data),
    .ta2tp_valid       (ta2tp_valid),
    .ta2tp_ready       (ta2tp_ready),
    .ta2tp_sop         (ta2tp_sop),
    .ta2tp_eop         (ta2tp_eop),
    .tp2ta_done        (tp2ta_done),
    .tp2ta_fail        (tp2ta_fail),
    .tp2ta_tassn       (tp2ta_tassn),
    .tp2ta_err         (tp2ta_err),
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
`ifdef CONTRACT_ASSUME
  tp_ta_assume u_tp_ta_assume (
    .core_clk       (core_clk),
    .rst_n          (rst_n),
    .ta2tp_op_valid (ta2tp_op_valid),
    .ta2tp_op_ready (ta2tp_op_ready),
    .ta2tp_opcode   (ta2tp_opcode),
    .ta2tp_tassn    (ta2tp_tassn),
    .ta2tp_bypass   (ta2tp_bypass),
    .ta2tp_data     (ta2tp_data),
    .ta2tp_valid    (ta2tp_valid),
    .ta2tp_ready    (ta2tp_ready),
    .ta2tp_sop      (ta2tp_sop),
    .ta2tp_eop      (ta2tp_eop),
    .tp2ta_done     (tp2ta_done),
    .tp2ta_fail     (tp2ta_fail),
    .nw2tp_flush    (nw2tp_flush),
    .pending        (pending),
    .compact        (compact)
  );
`endif
endmodule

`default_nettype wire
