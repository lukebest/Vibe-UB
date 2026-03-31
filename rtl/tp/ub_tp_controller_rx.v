module ub_tp_controller_rx #(
    parameter PSN_BITS = 24,
    parameter REORDER_DEPTH = 32
)(
    input clk, rst_n,

    // NL Layer Interface (Network Layer → TP)
    input  [159:0] nl_rx_data,
    input        nl_rx_valid,
    input        nl_rx_sop,
    input        nl_rx_eop,
    output       nl_rx_ready,

    // TA Layer Interface (TP → Transaction Layer)
    output [159:0] tp_rx_data,
    output       tp_rx_valid,
    output       tp_rx_sop,
    output       tp_rx_eop,
    input        tp_rx_ready,

    // Feedback Interface (to TP Transmitter)
    output [PSN_BITS-1:0] tp_ack_psn,
    output               tp_ack_valid,
    output [PSN_BITS-1:0] tp_nak_psn,
    output               tp_nak_valid,

    // Status Outputs
    output [PSN_BITS-1:0] tp_rx_expected_psn,
    output               tp_rx_drop,
    output               tp_rx_dup
);

    ub_tp_receiver #(
        .PSN_BITS(PSN_BITS),
        .REORDER_DEPTH(REORDER_DEPTH)
    ) u_receiver (
        .clk(clk),
        .rst_n(rst_n),
        .nl_rx_data(nl_rx_data),
        .nl_rx_valid(nl_rx_valid),
        .nl_rx_sop(nl_rx_sop),
        .nl_rx_eop(nl_rx_eop),
        .nl_rx_ready(nl_rx_ready),
        .tp_rx_data(tp_rx_data),
        .tp_rx_valid(tp_rx_valid),
        .tp_rx_sop(tp_rx_sop),
        .tp_rx_eop(tp_rx_eop),
        .tp_rx_ready(tp_rx_ready),
        .tp_ack_psn(tp_ack_psn),
        .tp_ack_valid(tp_ack_valid),
        .tp_nak_psn(tp_nak_psn),
        .tp_nak_valid(tp_nak_valid),
        .tp_rx_expected_psn(tp_rx_expected_psn),
        .tp_rx_drop(tp_rx_drop),
        .tp_rx_dup(tp_rx_dup)
    );

endmodule

