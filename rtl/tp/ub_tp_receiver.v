module ub_tp_receiver #(
    parameter PSN_BITS = 24,
    parameter REORDER_DEPTH = 32
)(
    input clk, rst_n,

    // NL Layer Interface (Network Layer → TP Receiver)
    input  [159:0] nl_rx_data,
    input        nl_rx_valid,
    input        nl_rx_sop,
    input        nl_rx_eop,
    output reg   nl_rx_ready,

    // TA Layer Interface (TP Receiver → Transaction Layer)
    output reg [159:0] tp_rx_data,
    output reg       tp_rx_valid,
    output reg       tp_rx_sop,
    output reg       tp_rx_eop,
    input            tp_rx_ready,

    // Feedback Interface (TP Receiver → TP Transmitter)
    output reg [PSN_BITS-1:0] tp_ack_psn,
    output reg               tp_ack_valid,
    output reg [PSN_BITS-1:0] tp_nak_psn,
    output reg               tp_nak_valid,

    // Status Outputs
    output [PSN_BITS-1:0] tp_rx_expected_psn,
    output               tp_rx_drop,
    output               tp_rx_dup
);

    // === RTP Header Fields ===
    localparam RTPH_OPCODE_DATA = 8'h00;
    localparam RTPH_OPCODE_ACK = 8'h01;
    localparam RTPH_OPCODE_NAK = 8'h02;

    // === Reorder Buffer ===
    reg [159:0] reorder_buffer [0:REORDER_DEPTH-1];
    reg [PSN_BITS-1:0] buffer_psn [0:REORDER_DEPTH-1];
    reg buffer_valid [0:REORDER_DEPTH-1];
    reg buffer_sop [0:REORDER_DEPTH-1];
    reg buffer_eop [0:REORDER_DEPTH-1];

    // === PSN Management ===
    reg [PSN_BITS-1:0] expected_psn;
    reg [PSN_BITS-1:0] max_received_psn;

    // === State Machine ===
    localparam STATE_IDLE = 2'b00;
    localparam STATE_DELIVER = 2'b01;
    reg [1:0] state;

    // === Internal Signals ===
    reg [159:0] rx_data_reg;
    reg rx_valid_reg, rx_sop_reg, rx_eop_reg;
    reg nl_rx_ready_reg;
    reg tp_rx_drop_reg;
    reg tp_rx_dup_reg;

    // === Header Extraction ===
    wire [7:0] rx_tp_opcode = nl_rx_data[159:152];
    wire [PSN_BITS-1:0] rx_psn = nl_rx_data[PSN_BITS-1:0];

    // === Status Outputs ===
    assign tp_rx_expected_psn = expected_psn;
    assign tp_rx_drop = tp_rx_drop_reg;
    assign tp_rx_dup = tp_rx_dup_reg;

    // === Main Sequential Logic ===
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            expected_psn <= 0;
            max_received_psn <= 0;
            state <= STATE_IDLE;
            nl_rx_ready_reg <= 1;
            rx_valid_reg <= 0;
            rx_sop_reg <= 0;
            rx_eop_reg <= 0;
            tp_ack_valid <= 0;
            tp_nak_valid <= 0;
            tp_rx_drop_reg <= 0;
            tp_rx_dup_reg <= 0;
            for (int i = 0; i < REORDER_DEPTH; i++) begin
                buffer_valid[i] <= 0;
            end
        end else begin
            nl_rx_ready_reg <= 1;
            rx_valid_reg <= 0;
            tp_ack_valid <= 0;
            tp_nak_valid <= 0;
            tp_rx_drop_reg <= 0;
            tp_rx_dup_reg <= 0;

            case (state)
                STATE_IDLE: begin
                    if (nl_rx_valid && nl_rx_ready_reg) begin
                        if (rx_tp_opcode == RTPH_OPCODE_DATA) begin
                            // Data packet received
                            if (rx_psn == expected_psn) begin
                                // In order - deliver immediately
                                rx_data_reg[159:0] <= nl_rx_data[159:0];
                                rx_data_reg[71:PSN_BITS] <= nl_rx_data[71:PSN_BITS];
                                rx_valid_reg <= 1;
                                rx_sop_reg <= nl_rx_sop;
                                rx_eop_reg <= nl_rx_eop;

                                // Send ACK
                                tp_ack_psn <= rx_psn;
                                tp_ack_valid <= 1;

                                // Check reorder buffer for next packets
                                if (nl_rx_eop) begin
                                    expected_psn <= expected_psn + 1;
                                end
                                state <= STATE_DELIVER;
                            end else if (rx_psn > expected_psn) begin
                                // Out of order - store in reorder buffer
                                for (int i = 0; i < REORDER_DEPTH; i++) begin
                                    if (!buffer_valid[i]) begin
                                        reorder_buffer[i] <= nl_rx_data;
                                        buffer_psn[i] <= rx_psn;
                                        buffer_sop[i] <= nl_rx_sop;
                                        buffer_eop[i] <= nl_rx_eop;
                                        buffer_valid[i] <= 1;
                                    end
                                end

                                // Update max received PSN
                                if (rx_psn > max_received_psn) begin
                                    max_received_psn <= rx_psn;
                                end

                                // Send NAK for missing PSN
                                tp_nak_psn <= expected_psn;
                                tp_nak_valid <= 1;
                            end else begin
                                // PSN < expected - duplicate or delayed
                                tp_rx_dup_reg <= 1;
                            end
                        end
                    end else begin
                        // Check reorder buffer for expected PSN
                        for (int i = 0; i < REORDER_DEPTH; i++) begin
                            if (buffer_valid[i] && buffer_psn[i] == expected_psn) begin
                                // Found expected PSN in buffer
                                rx_data_reg[159:0] <= reorder_buffer[i][159:0];
                                rx_data_reg[71:PSN_BITS] <= reorder_buffer[i][71:PSN_BITS];
                                rx_valid_reg <= 1;
                                rx_sop_reg <= buffer_sop[i];
                                rx_eop_reg <= buffer_eop[i];

                                // Send ACK
                                tp_ack_psn <= buffer_psn[i];
                                tp_ack_valid <= 1;

                                buffer_valid[i] <= 0;

                                if (buffer_eop[i]) begin
                                    expected_psn <= expected_psn + 1;
                                end
                                state <= STATE_DELIVER;
                            end
                        end
                    end
                end

                STATE_DELIVER: begin
                    if (tp_rx_ready) begin
                        rx_valid_reg <= 0;
                        state <= STATE_IDLE;
                    end
                end

                default: begin
                    state <= STATE_IDLE;
                end
            endcase
        end
    end

    // === Output Assignments ===
    always_comb begin
        tp_rx_data = rx_data_reg;
        tp_rx_valid = rx_valid_reg;
        tp_rx_sop = rx_sop_reg;
        tp_rx_eop = rx_eop_reg;
        nl_rx_ready = nl_rx_ready_reg;
    end

endmodule

