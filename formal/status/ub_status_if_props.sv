// ub_status_if_props — property-only STATUS / PARAM reserved encodings.
// SPEC §6.3, §6.4, §9; REGMAP §2.1 / §2.2. Bind on CSR STATUS / PARAM_PHY.
// RTL must never produce reserved values (TB assert; no waiver).

module ub_status_if_props (
  input wire       core_clk,
  input wire       rst_n,
  input wire [2:0] retry_req_st,
  input wire [1:0] retry_ack_st,
  input wire [3:0] num_lanes_tx,
  input wire [3:0] num_lanes_rx
);

  function automatic lanes_ok(input [3:0] n);
    lanes_ok = (n == 4'd1) || (n == 4'd2) || (n == 4'd4) || (n == 4'd8);
  endfunction

  // SPEC §6.3 / REGMAP §2.1: RETRY_REQ_ST 0..4 legal; 5–7 reserved, never produced.
  a_retry_req_st_legal: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    retry_req_st <= 3'd4
  );

  // SPEC §6.4 / REGMAP §2.1: RETRY_ACK_ST 0..1 legal; 2–3 reserved, never produced.
  a_retry_ack_st_legal: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    retry_ack_st <= 2'd1
  );

  // SPEC §9 / REGMAP §2.2: NUM_LANES_* binary count; legal {1,2,4,8}.
  a_num_lanes_tx_legal: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    lanes_ok(num_lanes_tx)
  );
  a_num_lanes_rx_legal: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    lanes_ok(num_lanes_rx)
  );

  c_req_normal:  cover property (@(posedge core_clk) rst_n && (retry_req_st == 3'd0));
  c_req_req:     cover property (@(posedge core_clk) rst_n && (retry_req_st == 3'd1));
  c_req_wait:    cover property (@(posedge core_clk) rst_n && (retry_req_st == 3'd2));
  c_req_retrain: cover property (@(posedge core_clk) rst_n && (retry_req_st == 3'd3));
  c_req_error:   cover property (@(posedge core_clk) rst_n && (retry_req_st == 3'd4));
  c_ack_normal:  cover property (@(posedge core_clk) rst_n && (retry_ack_st == 2'd0));
  c_ack_ack:     cover property (@(posedge core_clk) rst_n && (retry_ack_st == 2'd1));
  c_lanes_1:     cover property (@(posedge core_clk) rst_n && (num_lanes_tx == 4'd1) && (num_lanes_rx == 4'd1));
  c_lanes_2:     cover property (@(posedge core_clk) rst_n && (num_lanes_tx == 4'd2));
  c_lanes_4:     cover property (@(posedge core_clk) rst_n && (num_lanes_tx == 4'd4));
  c_lanes_8:     cover property (@(posedge core_clk) rst_n && (num_lanes_tx == 4'd8));

endmodule
