module ub_tp_controller_tx #(
    parameter PSN_BITS = 24,
    parameter RETRANSMIT_DEPTH = 32,
    parameter MAX_RETRIES = 3
)(
    input clk, rst_n,

    // TA Layer Interface (Transaction Layer → TP)
    input  [159:0] ta_data,
    input        ta_valid,
    input        ta_sop,
    input        ta_eop,
    output       ta_ready,

    // NL Layer Interface (TP → Network Layer)
    output [159:0] tp_tx_data,
    output       tp_tx_valid,
    output       tp_tx_sop,
    output       tp_tx_eop,
    input        tp_tx_ready,

    // Feedback Interface (from TP Receiver)
    input  [PSN_BITS-1:0] tp_ack_psn,
    input                  tp_ack_valid,
    input  [PSN_BITS-1:0] tp_nak_psn,
    input                  tp_nak_valid,

    // Status Outputs
    output [PSN_BITS-1:0] tp_tx_psn,
    output               tp_tx_busy
);

    ub_tp_transmitter #(
        .PSN_BITS(PSN_BITS),
        .RETRANSMIT_DEPTH(RETRANSMIT_DEPTH),
        .MAX_RETRIES(MAX_RETRIES)
    ) u_transmitter (
        .clk(clk),
        .rst_n(rst_n),
        .ta_data(ta_data),
        .ta_valid(ta_valid),
        .ta_sop(ta_sop),
        .ta_eop(ta_eop),
        .ta_ready(ta_ready),
        .tp_tx_data(tp_tx_data),
        .tp_tx_valid(tp_tx_valid),
        .tp_tx_sop(tp_tx_sop),
        .tp_tx_eop(tp_tx_eop),
        .tp_tx_ready(tp_tx_ready),
        .tp_ack_psn(tp_ack_psn),
        .tp_ack_valid(tp_ack_valid),
        .tp_nak_psn(tp_nak_psn),
        .tp_nak_valid(tp_nak_valid),
        .tp_tx_psn(tp_tx_psn),
        .tp_tx_busy(tp_tx_busy)
    );

endmodule

