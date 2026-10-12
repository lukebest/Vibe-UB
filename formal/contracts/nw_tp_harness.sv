// NW↔TP contract harness (LAYER_CONTRACTS §2). No product RTL.
// One initialized counter; all ports are combo of `cyc` so BMC/cover
// are deterministic without assume (GATE-PRIVATE-PARENT-FREE).
`default_nettype none

module nw_tp_harness (
  input wire core_clk
);
  localparam integer FLIT_W = 160;
  localparam integer CFG_CTP = 6;
  localparam integer CFG_RTP = 7;
  localparam integer CFG_BYP = 9;

  reg [4:0] cyc;
  initial cyc = 5'd0;
  always @(posedge core_clk) begin
    if (cyc != 5'd31)
      cyc <= cyc + 5'd1;
  end

  wire rst_n = (cyc != 5'd0);

  wire        tp2nw_valid  = (cyc == 5'd2) || (cyc == 5'd4) || (cyc == 5'd5)
                           || (cyc == 5'd6) || (cyc == 5'd15);
  wire        tp2nw_ready  = (cyc != 5'd4) && (cyc != 5'd10);
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
  wire [15:0] tp2nw_dcna   = (cyc == 5'd4) || (cyc == 5'd5) || (cyc == 5'd6) ? 16'h00C0 : 16'h0001;
  wire [7:0]  tp2nw_lbf    = (cyc == 5'd4) || (cyc == 5'd5) || (cyc == 5'd6) ? 8'h5A : 8'h00;
  wire [1:0]  tp2nw_rt     = (cyc == 5'd4) || (cyc == 5'd5) || (cyc == 5'd6) ? 2'd1 : 2'd0;
  wire [15:0] tp2nw_cci    = (cyc == 5'd4) || (cyc == 5'd5) || (cyc == 5'd6) ? 16'h00A5 : 16'h0000;

  wire        nw2tp_valid  = (cyc == 5'd8) || (cyc == 5'd11);
  wire        nw2tp_ready  = 1'b1;
  wire [FLIT_W-1:0] nw2tp_data = (cyc == 5'd8)  ? {{(FLIT_W-8){1'b0}}, 8'h33} :
                                 (cyc == 5'd11) ? {{(FLIT_W-8){1'b0}}, 8'h77} :
                                                 {FLIT_W{1'b0}};
  wire        nw2tp_sop    = (cyc == 5'd8) || (cyc == 5'd11);
  wire        nw2tp_eop    = (cyc == 5'd8) || (cyc == 5'd11);
  wire        nw2tp_err    = 1'b0;
  wire        nw2tp_flush  = (cyc == 5'd10);
  wire        nw2tp_drop   = (cyc == 5'd9);
  wire        nw_link_up   = (cyc != 5'd10);
  wire        nw2tp_icrc_err = (cyc == 5'd11);

  wire [3:0]  lph_cfg      = (cyc == 5'd11) ? CFG_RTP[3:0] :
                             (cyc >= 5'd13) ? CFG_CTP[3:0] :
                                             CFG_BYP[3:0];
  wire [23:0] psn          = (cyc == 5'd12) ? 24'hFFFFFE :
                             (cyc == 5'd13) ? 24'hFFFFFF :
                             (cyc == 5'd14) ? 24'h000000 : 24'd1;
  wire [23:0] psn_n        = psn + 24'd1;
  wire        rto_fire     = (cyc == 5'd12);
  wire        ack_coal     = (cyc == 5'd13);

  nw_tp_assert u_nw_tp_assert (
    .core_clk       (core_clk),
    .rst_n          (rst_n),
    .tp2nw_valid    (tp2nw_valid),
    .tp2nw_ready    (tp2nw_ready),
    .tp2nw_data     (tp2nw_data),
    .tp2nw_sop      (tp2nw_sop),
    .tp2nw_eop      (tp2nw_eop),
    .tp2nw_sl       (tp2nw_sl),
    .tp2nw_nlp      (tp2nw_nlp),
    .tp2nw_bypass   (tp2nw_bypass),
    .tp2nw_dcna     (tp2nw_dcna),
    .tp2nw_lbf      (tp2nw_lbf),
    .tp2nw_rt       (tp2nw_rt),
    .tp2nw_cci      (tp2nw_cci),
    .nw2tp_valid    (nw2tp_valid),
    .nw2tp_ready    (nw2tp_ready),
    .nw2tp_data     (nw2tp_data),
    .nw2tp_sop      (nw2tp_sop),
    .nw2tp_eop      (nw2tp_eop),
    .nw2tp_err      (nw2tp_err),
    .nw2tp_icrc_err (nw2tp_icrc_err),
    .nw2tp_flush    (nw2tp_flush),
    .nw2tp_drop     (nw2tp_drop),
    .nw_link_up     (nw_link_up),
    .lph_cfg        (lph_cfg),
    .psn            (psn),
    .psn_n          (psn_n),
    .rto_fire       (rto_fire),
    .ack_coal       (ack_coal)
  );
`ifdef CONTRACT_ASSUME
  nw_tp_assume u_nw_tp_assume (
    .core_clk       (core_clk),
    .rst_n          (rst_n),
    .tp2nw_valid    (tp2nw_valid),
    .tp2nw_ready    (tp2nw_ready),
    .tp2nw_data     (tp2nw_data),
    .tp2nw_sop      (tp2nw_sop),
    .tp2nw_eop      (tp2nw_eop),
    .tp2nw_sl       (tp2nw_sl),
    .tp2nw_nlp      (tp2nw_nlp),
    .tp2nw_bypass   (tp2nw_bypass),
    .tp2nw_dcna     (tp2nw_dcna),
    .tp2nw_lbf      (tp2nw_lbf),
    .tp2nw_rt       (tp2nw_rt),
    .tp2nw_cci      (tp2nw_cci),
    .nw2tp_valid    (nw2tp_valid),
    .nw2tp_ready    (nw2tp_ready),
    .nw2tp_data     (nw2tp_data),
    .nw2tp_sop      (nw2tp_sop),
    .nw2tp_eop      (nw2tp_eop),
    .nw_link_up     (nw_link_up),
    .lph_cfg        (lph_cfg)
  );
`endif
endmodule

`default_nettype wire
