interface ub_tp_intf(input logic clk, input logic rst_n);

  // TA -> TP Transmitter
  logic [159:0] ta_data;
  logic         ta_valid;
  logic         ta_sop;
  logic         ta_eop;
  logic         ta_ready;

  // TP Transmitter -> NL Loopback
  logic [159:0] tp_tx_data;
  logic         tp_tx_valid;
  logic         tp_tx_sop;
  logic         tp_tx_eop;
  logic         tp_tx_ready;

  // NL -> TP Receiver
  logic [159:0] nl_rx_data;
  logic         nl_rx_valid;
  logic         nl_rx_sop;
  logic         nl_rx_eop;
  logic         nl_rx_ready;

  // TP Receiver -> TA
  logic [159:0] tp_rx_data;
  logic         tp_rx_valid;
  logic         tp_rx_sop;
  logic         tp_rx_eop;
  logic         tp_rx_ready;

  // Feedback: Receiver -> Transmitter
  logic [23:0]  tp_ack_psn;
  logic         tp_ack_valid;
  logic [23:0]  tp_nak_psn;
  logic         tp_nak_valid;

  // Status outputs
  logic [23:0]  tp_tx_psn;
  logic         tp_tx_busy;
  logic [23:0]  tp_rx_expected_psn;
  logic         tp_rx_drop;
  logic         tp_rx_dup;

  // Directions: from DUT wrapper (harness) perspective
  //  - input:  harness reads from interface (driven by test/DUT)
  //  - output: harness drives to interface (goes to test/DUT)
  modport tb (
    // DUT inputs: driven by test → harness reads from interface → input to harness
    input  ta_data, ta_valid, ta_sop, ta_eop, tp_rx_ready,
    // DUT outputs: driven by DUT → harness drives to interface → output from harness
    output ta_ready,
    output tp_tx_data, tp_tx_valid, tp_tx_sop, tp_tx_eop,
    output tp_rx_data, tp_rx_valid, tp_rx_sop, tp_rx_eop,
    output tp_ack_psn, tp_ack_valid, tp_nak_psn, tp_nak_valid,
    output tp_tx_psn, tp_tx_busy, tp_rx_expected_psn, tp_rx_drop, tp_rx_dup,
    // Loopback signals driven by harness itself → must be output
    output tp_tx_ready, nl_rx_data, nl_rx_valid, nl_rx_sop, nl_rx_eop,
    output nl_rx_ready,
    // Clock/reset
    input  clk, rst_n
  );

endinterface
