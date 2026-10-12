// NW↔TP contract harness (LAYER_CONTRACTS §2). No product RTL.
// Closed legal-traffic FSM so cover/bmc/prove need no assume
// (GATE-PRIVATE-PARENT-FREE: assume lives only in assume_diag.sby).
`default_nettype none

module nw_tp_harness (
  input wire core_clk
);
  localparam integer FLIT_W = 160;
  localparam integer CFG9 = 9;
  localparam integer RTPH_BYTES = 16;
  localparam integer LPH_NTH_BYTES = 12;
  localparam integer PSN_W = 24;
  localparam integer TIMEOUT_DEF = 323;

  reg [4:0] cyc;
  wire rst_n = (cyc != 5'd0);

  always @(posedge core_clk) begin
    if (cyc != 5'd31)
      cyc <= cyc + 5'd1;
  end

  // LAYER_CONTRACTS §2 project ports
  reg                tp2nw_valid;
  reg                tp2nw_ready;
  reg [FLIT_W-1:0]   tp2nw_data;
  reg                tp2nw_sop;
  reg                tp2nw_eop;
  reg [3:0]          tp2nw_sl;
  reg [2:0]          tp2nw_nlp;
  reg                tp2nw_bypass;
  reg                nw2tp_valid;
  reg                nw2tp_ready;
  reg [FLIT_W-1:0]   nw2tp_data;
  reg                nw2tp_sop;
  reg                nw2tp_eop;
  reg                nw2tp_err;
  reg                nw2tp_flush;
  reg                nw2tp_drop;
  reg                nw_link_up;
  reg                nw2tp_icrc_err;
  reg [3:0]          lph_cfg;
  reg [23:0]         psn;
  reg [15:0]         elapsed;
  reg [4:0]          btah_bytes;
  reg [4:0]          maetah_bytes;

  wire timed_out = (elapsed >= TIMEOUT_DEF[15:0]);
  wire [23:0] psn_n = psn + 24'd1;
  wire compact = (lph_cfg == CFG9[3:0]);

  // Deterministic legal sequence (covers reachable by ~cyc 16).
  always @(posedge core_clk) begin
    if (!rst_n) begin
      tp2nw_valid     <= 1'b0;
      tp2nw_ready     <= 1'b1;
      tp2nw_data      <= {FLIT_W{1'b0}};
      tp2nw_sop       <= 1'b0;
      tp2nw_eop       <= 1'b0;
      tp2nw_sl        <= 4'd0;
      tp2nw_nlp       <= 3'd0;
      tp2nw_bypass    <= 1'b0;
      nw2tp_valid     <= 1'b0;
      nw2tp_ready     <= 1'b1;
      nw2tp_data      <= {FLIT_W{1'b0}};
      nw2tp_sop       <= 1'b0;
      nw2tp_eop       <= 1'b0;
      nw2tp_err       <= 1'b0;
      nw2tp_flush     <= 1'b0;
      nw2tp_drop      <= 1'b0;
      nw_link_up      <= 1'b1;
      nw2tp_icrc_err  <= 1'b0;
      lph_cfg         <= CFG9[3:0];
      psn             <= 24'd1;
      elapsed         <= 16'd0;
      btah_bytes      <= 5'd4;
      maetah_bytes    <= 5'd12;
    end else begin
      nw2tp_drop     <= 1'b0;
      nw2tp_icrc_err <= 1'b0;
      case (cyc)
        5'd1: begin
          tp2nw_ready  <= 1'b1;
          nw2tp_ready  <= 1'b1;
          nw_link_up   <= 1'b1;
          nw2tp_flush  <= 1'b0;
          lph_cfg      <= CFG9[3:0];
          btah_bytes   <= 5'd4;
          maetah_bytes <= 5'd12;
        end
        5'd2: begin
          // single-flit bypass TX (CFG9)
          tp2nw_valid  <= 1'b1;
          tp2nw_ready  <= 1'b1;
          tp2nw_data   <= {{(FLIT_W-8){1'b0}}, 8'hA5};
          tp2nw_sop    <= 1'b1;
          tp2nw_eop    <= 1'b1;
          tp2nw_sl     <= 4'd0;
          tp2nw_nlp    <= 3'd0;
          tp2nw_bypass <= 1'b1;
        end
        5'd3: begin
          tp2nw_valid  <= 1'b0;
          tp2nw_sop    <= 1'b0;
          tp2nw_eop    <= 1'b0;
          tp2nw_bypass <= 1'b0;
        end
        5'd4: begin
          // hold valid while ready=0 (handshake hold)
          tp2nw_valid  <= 1'b1;
          tp2nw_ready  <= 1'b0;
          tp2nw_data   <= {{(FLIT_W-8){1'b0}}, 8'h11};
          tp2nw_sop    <= 1'b1;
          tp2nw_eop    <= 1'b0;
          tp2nw_sl     <= 4'd1;
          tp2nw_nlp    <= 3'd1;
          tp2nw_bypass <= 1'b0;
        end
        5'd5: begin
          tp2nw_ready  <= 1'b1; // fire sop
        end
        5'd6: begin
          tp2nw_data   <= {{(FLIT_W-8){1'b0}}, 8'h22};
          tp2nw_sop    <= 1'b0;
          tp2nw_eop    <= 1'b1;
        end
        5'd7: begin
          tp2nw_valid  <= 1'b0;
          tp2nw_eop    <= 1'b0;
        end
        5'd8: begin
          nw2tp_valid  <= 1'b1;
          nw2tp_ready  <= 1'b1;
          nw2tp_data   <= {{(FLIT_W-8){1'b0}}, 8'h33};
          nw2tp_sop    <= 1'b1;
          nw2tp_eop    <= 1'b1;
          nw2tp_err    <= 1'b0;
        end
        5'd9: begin
          nw2tp_valid  <= 1'b0;
          nw2tp_sop    <= 1'b0;
          nw2tp_eop    <= 1'b0;
        end
        5'd10: begin
          nw_link_up   <= 1'b0;
          nw2tp_flush  <= 1'b1;
          tp2nw_valid  <= 1'b0;
          nw2tp_valid  <= 1'b0;
        end
        5'd11: begin
          nw_link_up   <= 1'b1;
          nw2tp_flush  <= 1'b0;
          lph_cfg      <= 4'd6;
          btah_bytes   <= 5'd8;
          maetah_bytes <= 5'd16;
        end
        5'd12: begin
          elapsed      <= 16'd322;
          psn          <= 24'hFFFFFE;
        end
        5'd13: begin
          elapsed      <= 16'd323;
          psn          <= 24'hFFFFFF;
        end
        5'd14: begin
          psn          <= 24'h000000; // wrap
          elapsed      <= 16'd0;
        end
        5'd15: begin
          tp2nw_valid  <= 1'b1;
          tp2nw_ready  <= 1'b1;
          tp2nw_data   <= {{(FLIT_W-8){1'b0}}, 8'h44};
          tp2nw_sop    <= 1'b1;
          tp2nw_eop    <= 1'b1;
          tp2nw_bypass <= 1'b0;
          lph_cfg      <= 4'd6;
        end
        default: begin
          tp2nw_valid  <= 1'b0;
          nw2tp_valid  <= 1'b0;
          tp2nw_sop    <= 1'b0;
          tp2nw_eop    <= 1'b0;
          nw2tp_sop    <= 1'b0;
          nw2tp_eop    <= 1'b0;
        end
      endcase
    end
  end
endmodule

`default_nettype wire
