// DUT Wrapper (Harness) - instantiates and connects TP Transmitter + Receiver
module ub_tp_dut_wrap #(
  parameter PSN_BITS        = 24,
  parameter RETRANSMIT_DEPTH = 32,
  parameter MAX_RETRIES      = 3,
  parameter REORDER_DEPTH    = 32
)(
  input  logic               clk,
  input  logic               rst_n,
  ub_tp_intf.tb             intf
);

  // Instantiate TP Transmitter
  ub_tp_transmitter #(
    .PSN_BITS(PSN_BITS),
    .RETRANSMIT_DEPTH(RETRANSMIT_DEPTH),
    .MAX_RETRIES(MAX_RETRIES)
  ) tx_dut (
    .clk(clk),
    .rst_n(rst_n),
    .ta_data(intf.ta_data),
    .ta_valid(intf.ta_valid),
    .ta_sop(intf.ta_sop),
    .ta_eop(intf.ta_eop),
    .ta_ready(intf.ta_ready),
    .tp_tx_data(intf.tp_tx_data),
    .tp_tx_valid(intf.tp_tx_valid),
    .tp_tx_sop(intf.tp_tx_sop),
    .tp_tx_eop(intf.tp_tx_eop),
    .tp_tx_ready(intf.tp_tx_ready),
    .tp_ack_psn(intf.tp_ack_psn),
    .tp_ack_valid(intf.tp_ack_valid),
    .tp_nak_psn(intf.tp_nak_psn),
    .tp_nak_valid(intf.tp_nak_valid),
    .tp_tx_psn(intf.tp_tx_psn),
    .tp_tx_busy(intf.tp_tx_busy)
  );

  // Instantiate TP Receiver
  ub_tp_receiver #(
    .PSN_BITS(PSN_BITS),
    .REORDER_DEPTH(REORDER_DEPTH)
  ) rx_dut (
    .clk(clk),
    .rst_n(rst_n),
    .nl_rx_data(intf.nl_rx_data),
    .nl_rx_valid(intf.nl_rx_valid),
    .nl_rx_sop(intf.nl_rx_sop),
    .nl_rx_eop(intf.nl_rx_eop),
    .nl_rx_ready(intf.nl_rx_ready),
    .tp_rx_data(intf.tp_rx_data),
    .tp_rx_valid(intf.tp_rx_valid),
    .tp_rx_sop(intf.tp_rx_sop),
    .tp_rx_eop(intf.tp_rx_eop),
    .tp_rx_ready(intf.tp_rx_ready),
    .tp_ack_psn(intf.tp_ack_psn),
    .tp_ack_valid(intf.tp_ack_valid),
    .tp_nak_psn(intf.tp_nak_psn),
    .tp_nak_valid(intf.tp_nak_valid),
    .tp_rx_expected_psn(intf.tp_rx_expected_psn),
    .tp_rx_drop(intf.tp_rx_drop),
    .tp_rx_dup(intf.tp_rx_dup)
  );

  // Loopback: TP Transmitter -> TP Receiver (internal loopback)
  always @(posedge clk) begin
    intf.nl_rx_valid <= intf.tp_tx_valid;
    intf.nl_rx_sop   <= intf.tp_tx_sop;
    intf.nl_rx_eop   <= intf.tp_tx_eop;
    intf.nl_rx_data  <= intf.tp_tx_data;
    intf.tp_tx_ready <= intf.nl_rx_ready;
  end

endmodule
