module ub_tp_transmitter #(
    parameter PSN_BITS = 24,
    parameter RETRANSMIT_DEPTH = 32,
    parameter MAX_RETRIES = 3
)(
    input clk, rst_n,

    // TA Layer Interface (Transaction Layer → TP Transmitter)
    input  [159:0] ta_data,
    input        ta_valid,
    input        ta_sop,
    input        ta_eop,
    output reg   ta_ready,

    // NL Layer Interface (TP Transmitter → Network Layer)
    output reg [159:0] tp_tx_data,
    output reg       tp_tx_valid,
    output reg       tp_tx_sop,
    output reg       tp_tx_eop,
    input            tp_tx_ready,

    // Feedback Interface (TP Receiver → TP Transmitter)
    input  [PSN_BITS-1:0] tp_ack_psn,
    input                  tp_ack_valid,
    input  [PSN_BITS-1:0] tp_nak_psn,
    input                  tp_nak_valid,

    // Status Outputs
    output [PSN_BITS-1:0] tp_tx_psn,
    output               tp_tx_busy
);

    // === RTP Header Fields ===
    localparam RTPH_OPCODE_DATA = 8'h00;
    localparam RTPH_VERSION = 2'b00;

    // === Retransmission Buffer ===
    reg [159:0] retransmit_buffer [0:RETRANSMIT_DEPTH-1];
    reg [PSN_BITS-1:0] buffer_psn [0:RETRANSMIT_DEPTH-1];
    reg [1:0] retry_count [0:RETRANSMIT_DEPTH-1];
    reg buffer_valid [0:RETRANSMIT_DEPTH-1];
    reg [$clog2(RETRANSMIT_DEPTH)-1:0] buffer_wr_ptr;
    reg [$clog2(RETRANSMIT_DEPTH)-1:0] buffer_rd_ptr;

    // === PSN Management ===
    reg [PSN_BITS-1:0] current_psn;
    reg [PSN_BITS-1:0] acked_psn;

    // === State Machine ===
    localparam STATE_IDLE = 2'b00;
    localparam STATE_SEND = 2'b01;
    localparam STATE_RETRANSMIT = 2'b10;
    reg [1:0] state;

    // === Internal Signals ===
    reg [159:0] tx_data_reg;
    reg tx_valid_reg, tx_sop_reg, tx_eop_reg;
    reg ta_ready_reg;

    // === Status Outputs ===
    assign tp_tx_psn = current_psn;
    assign tp_tx_busy = (buffer_wr_ptr == buffer_rd_ptr - 1) || (state != STATE_IDLE);

    // === Main Sequential Logic ===
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            current_psn <= 0;
            acked_psn <= 0;
            buffer_wr_ptr <= 0;
            buffer_rd_ptr <= 0;
            state <= STATE_IDLE;
            ta_ready_reg <= 1;
            tx_valid_reg <= 0;
            tx_sop_reg <= 0;
            tx_eop_reg <= 0;
            for (int i = 0; i < RETRANSMIT_DEPTH; i++) begin
                buffer_valid[i] <= 0;
                retry_count[i] <= 0;
            end
        end else begin
            ta_ready_reg <= 1;
            tx_valid_reg <= 0;

            case (state)
                STATE_IDLE: begin
                    if (ta_valid && ta_ready_reg) begin
                        // Receive from TA layer, add RTPH and store in buffer
                        tx_data_reg[159:152] <= RTPH_OPCODE_DATA;
                        tx_data_reg[151:150] <= RTPH_VERSION;
                        tx_data_reg[149:148] <= 2'b00; // Padding
                        tx_data_reg[147:144] <= 4'h0; // NLP (placeholder)
                        tx_data_reg[143:120] <= 24'h0; // SrcTPN (placeholder)
                        tx_data_reg[119:96] <= 24'h0; // DstTPN (placeholder)
                        tx_data_reg[95:72] <= 24'h0; // Reserved
                        tx_data_reg[PSN_BITS-1:0] <= current_psn;
                        tx_data_reg[71:PSN_BITS] <= ta_data[71:PSN_BITS];

                        tx_valid_reg <= 1;
                        tx_sop_reg <= ta_sop;
                        tx_eop_reg <= ta_eop;

                        // Store in retransmission buffer
                        retransmit_buffer[buffer_wr_ptr] <= tx_data_reg;
                        buffer_psn[buffer_wr_ptr] <= current_psn;
                        buffer_valid[buffer_wr_ptr] <= 1;
                        retry_count[buffer_wr_ptr] <= 0;

                        if (ta_eop) begin
                            current_psn <= current_psn + 1;
                        end

                        buffer_wr_ptr <= buffer_wr_ptr + 1;
                        state <= STATE_SEND;
                    end else if (tp_nak_valid) begin
                        // NAK received, find and retransmit
                        state <= STATE_RETRANSMIT;
                        // Find packet in buffer with PSN = tp_nak_psn
                        for (int i = 0; i < RETRANSMIT_DEPTH; i++) begin
                            if (buffer_valid[i] && buffer_psn[i] == tp_nak_psn) begin
                                buffer_rd_ptr <= i;
                            end
                        end
                    end
                end

                STATE_SEND: begin
                    if (tp_tx_ready) begin
                        tx_valid_reg <= 0;
                        state <= STATE_IDLE;
                    end
                end

                STATE_RETRANSMIT: begin
                    if (buffer_valid[buffer_rd_ptr]) begin
                        tx_data_reg <= retransmit_buffer[buffer_rd_ptr];
                        tx_valid_reg <= 1;
                        retry_count[buffer_rd_ptr] <= retry_count[buffer_rd_ptr] + 1;
                        if (tp_tx_ready) begin
                            state <= STATE_IDLE;
                        end
                    end else begin
                        state <= STATE_IDLE;
                    end
                end

                default: begin
                    state <= STATE_IDLE;
                end
            endcase

            // Process ACKs - free acknowledged buffers
            if (tp_ack_valid) begin
                acked_psn <= tp_ack_psn;
                for (int i = 0; i < RETRANSMIT_DEPTH; i++) begin
                    if (buffer_valid[i] && buffer_psn[i] <= tp_ack_psn) begin
                        buffer_valid[i] <= 0;
                    end
                end
            end
        end
    end

    // === Output Assignments ===
    always_comb begin
        tp_tx_data = tx_data_reg;
        tp_tx_valid = tx_valid_reg;
        tp_tx_sop = tx_sop_reg;
        tp_tx_eop = tx_eop_reg;
        ta_ready = ta_ready_reg;
    end

endmodule

