// NW↔TP contract harness (LAYER_CONTRACTS §2). No product RTL.
// One initialized counter; all ports are combo of `cyc` so BMC/cover
// are deterministic without assume (GATE-PRIVATE-PARENT-FREE).
`default_nettype none

module nw_tp_harness (
  input wire core_clk
);
  localparam integer FLIT_W = 160;
  localparam integer CFG9 = 9;

  reg [4:0] cyc;
  initial cyc = 5'd0;
  always @(posedge core_clk) begin
    if (cyc != 5'd31)
      cyc <= cyc + 5'd1;
  end

  wire rst_n = (cyc != 5'd0);

  wire        tp2nw_valid  = (cyc == 5'd2) || (cyc == 5'd4) || (cyc == 5'd5)
                           || (cyc == 5'd6) || (cyc == 5'd15);
  wire        tp2nw_ready  = (cyc != 5'd4);
  wire [FLIT_W-1:0] tp2nw_data = (cyc == 5'd2)  ? {{(FLIT_W-8){1'b0}}, 8'hA5} :
                                 (cyc == 5'd4)  ? {{(FLIT_W-8){1'b0}}, 8'h11} :
                                 (cyc == 5'd5)  ? {{(FLIT_W-8){1'b0}}, 8'h11} :
                                 (cyc == 5'd6)  ? {{(FLIT_W-8){1'b0}}, 8'h22} :
                                 (cyc == 5'd15) ? {{(FLIT_W-8){1'b0}}, 8'h44} :
                                                 {FLIT_W{1'b0}};
  wire        tp2nw_sop    = (cyc == 5'd2) || (cyc == 5'd4) || (cyc == 5'd5) || (cyc == 5'd15);
  wire        tp2nw_eop    = (cyc == 5'd2) || (cyc == 5'd6) || (cyc == 5'd15);
  wire [3:0]  tp2nw_sl     = (cyc == 5'd4) || (cyc == 5'd5) || (cyc == 5'd6) ? 4'd1 : 4'd0;
  wire [2:0]  tp2nw_nlp    = (cyc == 5'd4) || (cyc == 5'd5) || (cyc == 5'd6) ? 3'd1 : 3'd0;
  wire        tp2nw_bypass = (cyc == 5'd2);

  wire        nw2tp_valid  = (cyc == 5'd8);
  wire        nw2tp_ready  = 1'b1;
  wire [FLIT_W-1:0] nw2tp_data = (cyc == 5'd8) ? {{(FLIT_W-8){1'b0}}, 8'h33} : {FLIT_W{1'b0}};
  wire        nw2tp_sop    = (cyc == 5'd8);
  wire        nw2tp_eop    = (cyc == 5'd8);
  wire        nw2tp_err    = 1'b0;
  wire        nw2tp_flush  = (cyc == 5'd10);
  wire        nw2tp_drop   = 1'b0;
  wire        nw_link_up   = (cyc != 5'd10);
  wire        nw2tp_icrc_err = 1'b0;

  wire [3:0]  lph_cfg      = (cyc >= 5'd11) ? 4'd6 : CFG9[3:0];
  wire        compact      = (lph_cfg == CFG9[3:0]);
  wire [4:0]  btah_bytes   = compact ? 5'd4 : 5'd8;
  wire [4:0]  maetah_bytes = compact ? 5'd12 : 5'd16;
  wire [23:0] psn          = (cyc == 5'd12) ? 24'hFFFFFE :
                             (cyc == 5'd13) ? 24'hFFFFFF :
                             (cyc == 5'd14) ? 24'h000000 : 24'd1;
  wire [23:0] psn_n        = psn + 24'd1;
  wire [15:0] elapsed      = (cyc == 5'd12) ? 16'd322 :
                             (cyc == 5'd13) ? 16'd323 : 16'd0;
  wire        timed_out    = (elapsed >= 16'd323);

  nw_tp_assert u_nw_tp_assert (
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
`ifdef CONTRACT_ASSUME
  nw_tp_assume u_nw_tp_assume (
    .core_clk     (core_clk),
    .rst_n        (rst_n),
    .tp2nw_valid  (tp2nw_valid),
    .tp2nw_ready  (tp2nw_ready),
    .tp2nw_data   (tp2nw_data),
    .tp2nw_sop    (tp2nw_sop),
    .tp2nw_eop    (tp2nw_eop),
    .tp2nw_bypass (tp2nw_bypass),
    .nw2tp_valid  (nw2tp_valid),
    .nw2tp_ready  (nw2tp_ready),
    .nw2tp_data   (nw2tp_data),
    .nw2tp_sop    (nw2tp_sop),
    .nw2tp_eop    (nw2tp_eop),
    .nw_link_up   (nw_link_up),
    .lph_cfg      (lph_cfg)
  );
`endif
endmodule

`default_nettype wire
