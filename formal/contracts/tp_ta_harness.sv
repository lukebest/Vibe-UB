// TP↔TA contract harness (LAYER_CONTRACTS §3). No product RTL.
// Closed legal-traffic FSM; default sby tasks need no assume.
`default_nettype none

module tp_ta_harness (
  input wire core_clk
);
  localparam integer FLIT_W = 160;
  localparam integer TASSN_W = 16;
  localparam integer CFG9 = 9;

  reg [4:0] cyc;
  wire rst_n = (cyc != 5'd0);

  always @(posedge core_clk) begin
    if (cyc != 5'd31)
      cyc <= cyc + 5'd1;
  end

  reg                ta2tp_op_valid;
  reg                ta2tp_op_ready;
  reg [7:0]          ta2tp_opcode;
  reg [TASSN_W-1:0]  ta2tp_tassn;
  reg [1:0]          ta2tp_mode;
  reg                ta2tp_bypass;
  reg [FLIT_W-1:0]   ta2tp_data;
  reg                ta2tp_valid;
  reg                ta2tp_ready;
  reg                ta2tp_sop;
  reg                ta2tp_eop;
  reg                tp2ta_done;
  reg                tp2ta_fail;
  reg [TASSN_W-1:0]  tp2ta_tassn;
  reg                tp2ta_err;
  reg                tp2ta_op_valid;
  reg                tp2ta_op_ready;
  reg [7:0]          tp2ta_opcode;
  reg [TASSN_W-1:0]  tp2ta_op_tassn;
  reg [1:0]          tp2ta_op_mode;
  reg                tp2ta_op_bypass;
  reg [FLIT_W-1:0]   tp2ta_data;
  reg                tp2ta_data_valid;
  reg                tp2ta_data_ready;
  reg                tp2ta_data_sop;
  reg                tp2ta_data_eop;
  reg                nw2tp_flush;
  reg                nw_link_up;
  reg [3:0]          lph_cfg;
  reg                pending;

  wire done_fail_mutex = !(tp2ta_done && tp2ta_fail);
  wire compact = (lph_cfg == CFG9[3:0]);

  always @(posedge core_clk) begin
    if (!rst_n) begin
      ta2tp_op_valid    <= 1'b0;
      ta2tp_op_ready    <= 1'b1;
      ta2tp_opcode      <= 8'd0;
      ta2tp_tassn       <= {TASSN_W{1'b0}};
      ta2tp_mode        <= 2'd0;
      ta2tp_bypass      <= 1'b0;
      ta2tp_data        <= {FLIT_W{1'b0}};
      ta2tp_valid       <= 1'b0;
      ta2tp_ready       <= 1'b1;
      ta2tp_sop         <= 1'b0;
      ta2tp_eop         <= 1'b0;
      tp2ta_done        <= 1'b0;
      tp2ta_fail        <= 1'b0;
      tp2ta_tassn       <= {TASSN_W{1'b0}};
      tp2ta_err         <= 1'b0;
      tp2ta_op_valid    <= 1'b0;
      tp2ta_op_ready    <= 1'b1;
      tp2ta_opcode      <= 8'd0;
      tp2ta_op_tassn    <= {TASSN_W{1'b0}};
      tp2ta_op_mode     <= 2'd0;
      tp2ta_op_bypass   <= 1'b0;
      tp2ta_data        <= {FLIT_W{1'b0}};
      tp2ta_data_valid  <= 1'b0;
      tp2ta_data_ready  <= 1'b1;
      tp2ta_data_sop    <= 1'b0;
      tp2ta_data_eop    <= 1'b0;
      nw2tp_flush       <= 1'b0;
      nw_link_up        <= 1'b1;
      lph_cfg           <= CFG9[3:0];
      pending           <= 1'b0;
    end else begin
      tp2ta_done <= 1'b0;
      tp2ta_fail <= 1'b0;
      tp2ta_err  <= 1'b0;
      case (cyc)
        5'd1: begin
          ta2tp_op_ready   <= 1'b1;
          ta2tp_ready      <= 1'b1;
          tp2ta_op_ready   <= 1'b1;
          tp2ta_data_ready <= 1'b1;
          nw_link_up       <= 1'b1;
          lph_cfg          <= CFG9[3:0];
        end
        5'd2: begin
          // submit bypass op (CFG9)
          ta2tp_op_valid <= 1'b1;
          ta2tp_opcode   <= 8'h10;
          ta2tp_tassn    <= 16'h0001;
          ta2tp_mode     <= 2'd0;
          ta2tp_bypass   <= 1'b1;
          pending        <= 1'b1;
        end
        5'd3: begin
          ta2tp_op_valid <= 1'b0;
          ta2tp_valid    <= 1'b1;
          ta2tp_data     <= {{(FLIT_W-8){1'b0}}, 8'h55};
          ta2tp_sop      <= 1'b1;
          ta2tp_eop      <= 1'b1;
        end
        5'd4: begin
          ta2tp_valid    <= 1'b0;
          ta2tp_sop      <= 1'b0;
          ta2tp_eop      <= 1'b0;
          tp2ta_done     <= 1'b1;
          tp2ta_tassn    <= 16'h0001;
          pending        <= 1'b0;
        end
        5'd5: begin
          // hold op valid
          ta2tp_op_valid <= 1'b1;
          ta2tp_op_ready <= 1'b0;
          ta2tp_opcode   <= 8'h11;
          ta2tp_tassn    <= 16'h0002;
          ta2tp_bypass   <= 1'b1;
        end
        5'd6: begin
          ta2tp_op_ready <= 1'b1;
          pending        <= 1'b1;
        end
        5'd7: begin
          ta2tp_op_valid <= 1'b0;
          tp2ta_fail     <= 1'b1;
          tp2ta_tassn    <= 16'h0002;
          pending        <= 1'b0;
        end
        5'd8: begin
          // deliver to target TA
          tp2ta_op_valid  <= 1'b1;
          tp2ta_opcode    <= 8'h10;
          tp2ta_op_tassn  <= 16'h0003;
          tp2ta_op_mode   <= 2'd0;
          tp2ta_op_bypass <= 1'b1;
        end
        5'd9: begin
          tp2ta_op_valid   <= 1'b0;
          tp2ta_data_valid <= 1'b1;
          tp2ta_data       <= {{(FLIT_W-8){1'b0}}, 8'h66};
          tp2ta_data_sop   <= 1'b1;
          tp2ta_data_eop   <= 1'b1;
        end
        5'd10: begin
          tp2ta_data_valid <= 1'b0;
          tp2ta_data_sop   <= 1'b0;
          tp2ta_data_eop   <= 1'b0;
        end
        5'd11: begin
          // flush with no leftover pending
          nw2tp_flush    <= 1'b1;
          nw_link_up     <= 1'b0;
          ta2tp_op_valid <= 1'b0;
          ta2tp_valid    <= 1'b0;
          pending        <= 1'b0;
        end
        5'd12: begin
          nw2tp_flush <= 1'b0;
          nw_link_up  <= 1'b1;
          lph_cfg     <= 4'd6;
        end
        5'd13: begin
          // non-CFG9 full-header path, still bypass=0
          ta2tp_op_valid <= 1'b1;
          ta2tp_opcode   <= 8'h20;
          ta2tp_tassn    <= 16'hABCD;
          ta2tp_bypass   <= 1'b0;
          pending        <= 1'b1;
        end
        5'd14: begin
          ta2tp_op_valid <= 1'b0;
          tp2ta_done     <= 1'b1;
          tp2ta_tassn    <= 16'hABCD;
          pending        <= 1'b0;
        end
        default: begin
          ta2tp_op_valid   <= 1'b0;
          ta2tp_valid      <= 1'b0;
          tp2ta_op_valid   <= 1'b0;
          tp2ta_data_valid <= 1'b0;
        end
      endcase
    end
  end
endmodule

`default_nettype wire
